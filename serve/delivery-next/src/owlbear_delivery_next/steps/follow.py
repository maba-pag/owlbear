"""Follow: CI and review comments on the PR's current head against the profile's declared and required checks."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next import loop, profile
from owlbear_delivery_next.github.provider import classify_checks
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind, Stop, Waiting
from owlbear_delivery_next.steps import check, engine

if TYPE_CHECKING:
    from owlbear_delivery_next.github.provider import CiState, PullRequest
    from owlbear_delivery_next.models import Change
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


def _published(ctx: Ctx, c: Change, head: str) -> datetime:
    at = [str(e["at"]) for e in ctx.events(c.slug, "publish") if e.get("head") == head]
    return datetime.fromisoformat(at[-1]) if at else ctx.now


def missing(ctx: Ctx, c: Change, pr: PullRequest, state: CiState) -> tuple[Change, StepResult]:
    """P10: a declared or required check that never starts is pending, then the owner's action; never passed."""
    names = ", ".join(state.missing)
    cause = MISSING + names
    window = timedelta(seconds=int(profile.value(ctx.profile, profile.WINDOW, "300")))
    if ctx.now - _published(ctx, c, pr.head_sha) < window:
        return c, engine.pending(Waiting.CHECK_START, f"waiting for {names} to start", ctx.poll())
    asked = next((q for q in c.questions if q.cause == cause and q.answer and not q.effect_observed_at), None)
    if asked is None:
        text = f"{names} never started on PR #{pr.number}: start or approve its workflow run in GitHub"
        return c, engine.ask(F, text, cause, engine.continue_or_pause(F))
    c, within = loop.charge(c, cause, ctx.now)
    if within:
        return c, engine.pending(Waiting.OWNER_ACTION, f"waiting for {names} to start after your action", ctx.poll())
    action = f"Start {names} for PR #{pr.number} in GitHub"
    stop = Stop(kind=ErrorKind.GATE, reason=f"{names} never started", action=action, resume="It starts", at=ctx.now)
    return c, StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:  # noqa: PLR0911 - one exit per observation
    """Observe the PR's checks and review threads and route each to its exit."""
    if c.names.pr is None:
        reason = "no pull request is recorded for this Change"
        stop = Stop(
            kind=ErrorKind.STATE, reason=reason, action="Restore the previous state", resume="State loads", at=ctx.now
        )
        return c, StepResult(exit=Exit.STOP, reason=reason, stop=stop)
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr)
    if pr.state != "open":
        return c, engine.pending(Waiting.CI, f"PR #{pr.number} is {'merged' if pr.merged else 'closed'}", ctx.poll())
    state = ci(ctx, pr)
    if state.failed:
        return c, fix_ci(ctx, c, state, F)
    done = {t.id for t in c.plan.tasks} if c.plan else set()
    for thread in ctx.gh.read_comments(ctx.repository, pr.number):
        if f"pr-{thread.id}" not in done:
            title = f"Address the review comment {thread.id}" + (f" on {thread.path}" if thread.path else "")
            fix = engine.task(c, title, "pr-feedback", f"{thread.body}\n{thread.url or ''}", f"pr-{thread.id}")
            return c, engine.back(ErrorKind.REVIEW, F, thread.id, f"fixing review comment {thread.id}", fix)
    for q in c.questions:
        if q.cause and q.cause.startswith(MISSING) and q.answer and not q.effect_observed_at and not state.missing:
            c = loop.effect_observed(c, q.id, ctx.now)
    if state.missing and not state.running:
        return missing(ctx, c, pr, state)
    if state.running or state.missing:
        return c, waiting(state, ctx)
    paths = check.declared(c)
    ctx.log(c.slug, "ci", head=pr.head_sha, passed=list(state.passed), ignored=list(state.ignored))
    return c, StepResult(exit=Exit.DONE, reason=f"CI passed: {', '.join(state.passed)}", paths=paths)
