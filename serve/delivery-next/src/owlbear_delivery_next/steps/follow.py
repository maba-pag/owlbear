"""Follow: CI and review comments on the PR's current head against the profile's declared and required checks."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next import loop, profile
from owlbear_delivery_next.github.provider import ProviderError, classify_checks
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import Episode, ErrorKind, Exit, StepKind, Stop, Waiting
from owlbear_delivery_next.steps import check, engine

if TYPE_CHECKING:
    from owlbear_delivery_next.github.provider import CiState, PullRequest
    from owlbear_delivery_next.models import Change, Question
    from owlbear_delivery_next.steps.engine import Ctx

F = StepKind.FOLLOW
MISSING = "gate:follow:missing:"


def ci(ctx: Ctx, pr: PullRequest) -> CiState:
    """Classify the checks at the PR head against the declared CI and the required checks."""
    checks = ctx.gh.observe_checks(ctx.repository, pr.number, pr.head_sha)
    declared = profile.names(ctx.profile, profile.DECLARED)
    return classify_checks(checks, declared, profile.names(ctx.profile, profile.REQUIRED))


def fix_ci(ctx: Ctx, c: Change, state: CiState, step: StepKind) -> StepResult:
    """Back to build with a fix task carrying the failing check's log tail; counted per check (bounded)."""
    failed = state.failed[0]
    log = ctx.gh.job_log(ctx.repository, failed.job_id) if failed.job_id else ""
    detail = f"CI check `{failed.name}` failed ({failed.conclusion}); {failed.url or ''}\n{log}"
    fix = engine.task(c, f"Fix the failing CI check {failed.name}", "ci", detail)
    return engine.back(ErrorKind.CHECKS, step, failed.name, f"fixing {failed.name}: CI failed", fix)


def waiting(state: CiState, ctx: Ctx) -> StepResult:
    """Pending while expected checks run; the status shows the count and when it was observed."""
    reason = f"{len(state.running) + len(state.missing)} of {state.expected} checks running"
    return engine.pending(Waiting.CI, reason, ctx.poll())


def episode(ctx: Ctx, c: Change, head: str, state: CiState) -> Change:
    """P10: keep when checks were first seen missing at *head*; once none is missing, an owner action took effect."""
    if state.missing:
        if c.missing is None or c.missing.head != head:
            c.missing = Episode(head=head, since=ctx.now)
        return c
    c.missing = None
    for q in c.questions:
        if q.cause and q.cause.startswith(MISSING) and q.answer and not q.effect_observed_at:
            c = loop.effect_observed(c, q.id, ctx.now)
    return c


def missing(ctx: Ctx, c: Change, pr: PullRequest, state: CiState, step: StepKind = F) -> tuple[Change, StepResult]:
    """P10: a declared or required check that never starts is pending, then the owner's action; never passed."""
    names = ", ".join(state.missing)
    cause = MISSING + names
    window = timedelta(seconds=int(profile.value(ctx.profile, profile.WINDOW, "300")))
    since = c.missing.since if c.missing and c.missing.head == pr.head_sha else ctx.now
    if ctx.now - since < window:
        return c, engine.pending(Waiting.CHECK_START, f"waiting for {names} to start", ctx.poll())
    asked = next((q for q in c.questions if q.cause == cause and q.answer and not q.effect_observed_at), None)
    if asked is None:
        text = f"{names} never started on PR #{pr.number}: start or approve its workflow run in GitHub"
        return c, engine.ask(step, text, cause, engine.continue_or_pause(step))
    c, within = loop.charge(c, cause, ctx.now)
    if within:
        return c, engine.pending(Waiting.OWNER_ACTION, f"waiting for {names} to start after your action", ctx.poll())
    action = f"Start {names} for PR #{pr.number} in GitHub"
    stop = Stop(kind=ErrorKind.GATE, reason=f"{names} never started", action=action, resume="It starts", at=ctx.now)
    return c, StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)


def _reopening(c: Change) -> Question | None:
    return next(
        (
            q
            for q in c.questions
            if q.cause == loop.PR_CLOSED and q.answer and q.answer.option == "reopen" and not q.effect_observed_at
        ),
        None,
    )


def reopen(ctx: Ctx, c: Change, pr: PullRequest) -> tuple[Change, PullRequest, StepResult | None]:
    """M4 reopen: reopen the closed PR when the profile can push, else ask the owner; continue once it is open."""
    q = _reopening(c)
    if q and pr.state != "open" and not pr.merged and profile.value(ctx.profile, profile.PUSH) == "yes":
        try:
            ctx.gh.reopen_pull_request(ctx.repository, pr.number)
        except ProviderError as exc:  # GitHub refuses, e.g. a deleted branch: the owner gets the action
            ctx.log(c.slug, "reopen", pr=pr.number, error=str(exc)[:200])
        pr = ctx.gh.read_pull_request(ctx.repository, pr.number)
    if pr.state == "open":
        return (loop.effect_observed(c, q.id, ctx.now) if q else c), pr, None
    if q is None or pr.merged:
        reason = f"PR #{pr.number} is {'merged' if pr.merged else 'closed'}"
        return c, pr, engine.pending(Waiting.CI, reason, ctx.poll())
    text = f"Reopen PR #{pr.number} in GitHub ({pr.url}: Reopen pull request), then continue"
    return c, pr, engine.ask(F, text, loop.cause_key(ErrorKind.GATE, F, "reopen"), engine.continue_or_pause(F))


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:  # noqa: PLR0911 - one exit per observation
    """Observe the PR's checks and review threads and route each to its exit."""
    if c.names.pr is None:
        reason = "no pull request is recorded for this Change"
        stop = Stop(
            kind=ErrorKind.STATE, reason=reason, action="Restore the previous state", resume="State loads", at=ctx.now
        )
        return c, StepResult(exit=Exit.STOP, reason=reason, stop=stop)
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr)
    c, pr, held = reopen(ctx, c, pr)
    if held is not None:
        return c, held
    state = ci(ctx, pr)
    c = episode(ctx, c, pr.head_sha, state)
    if state.failed:
        return c, fix_ci(ctx, c, state, F)
    done = {t.id for t in c.plan.tasks} if c.plan else set()
    for thread in ctx.gh.read_comments(ctx.repository, pr.number):
        if f"pr-{thread.id}" not in done:
            title = f"Address the review comment {thread.id}" + (f" on {thread.path}" if thread.path else "")
            fix = engine.task(c, title, "pr-feedback", f"{thread.body}\n{thread.url or ''}", f"pr-{thread.id}")
            return c, engine.back(ErrorKind.REVIEW, F, thread.id, f"fixing review comment {thread.id}", fix)
    if state.missing and not state.running:
        return missing(ctx, c, pr, state)
    if state.running or state.missing:
        return c, waiting(state, ctx)
    paths = check.declared(c)
    ctx.log(c.slug, "ci", head=pr.head_sha, passed=list(state.passed), ignored=list(state.ignored))
    return c, StepResult(exit=Exit.DONE, reason=f"CI passed: {', '.join(state.passed)}", paths=paths)
