"""Follow: CI and review comments on the PR's current head against the profile's declared and required checks."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import loop, profile
from owlbear_delivery_next.github.provider import ProviderError, classify_checks
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import Episode, ErrorKind, Exit, Response, StepKind, Stop, Waiting
from owlbear_delivery_next.steps import check, engine
from owlbear_delivery_next.steps import conversation as conv

if TYPE_CHECKING:
    from owlbear_delivery_next.github.provider import CiState, ConversationItem, PullRequest
    from owlbear_delivery_next.models import Change, Question, Task
    from owlbear_delivery_next.steps.engine import Ctx

F = StepKind.FOLLOW
MISSING = "gate:follow:missing:"
REPOSTS = 3


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


def _published(c: Change, pr: PullRequest) -> conv.Published:
    """Whether a fix commit is an ancestor of the PR head; the head branch is fetched at most once."""
    path, fetched = Path(c.names.worktree), []

    def check(commit: str) -> bool:
        if commit == pr.head_sha:
            return True
        if not fetched:
            engine.fetch(path, pr.head_branch)
            fetched.append(pr.head_branch)
        return engine.contains(path, commit, pr.head_sha)

    return check


def _post(  # noqa: PLR0913 - one reply names the PR, its item, its response and its task
    ctx: Ctx, c: Change, pr: PullRequest, item: ConversationItem, *, r: Response, task: str
) -> str:
    """Post one reply for *task*; the caller looked for an earlier one carrying the same marker first."""
    body = conv.reply_body(r, pr.head_sha, conv.marker(c.slug, item.id, task))
    reply_id = ctx.gh.post_reply(ctx.repository, pr.number, item, body)
    ctx.log(c.slug, "reply", item=item.id, task=task, reply=reply_id)
    return reply_id


def _reply(  # noqa: PLR0913 - one reply needs the PR, the task, its response and the conversation read
    ctx: Ctx,
    c: Change,
    pr: PullRequest,
    task: Task,
    r: Response,
    *,
    items: tuple[ConversationItem, ...],
    step: StepKind,
) -> tuple[Change, StepResult | None]:
    """P12: post one handled item's reply once; a fix not in the PR head is published first, or reopens the item."""
    ref = task.item
    assert ref  # noqa: S101 - only pending conversation tasks reach here
    item = next((i for i in items if i.id == ref.id), None)
    if item is None or r.how == "no-action":
        return conv.record(c, task, r, ctx.now), None
    if r.how == "fixed" and r.commit and not _published(c, pr)(r.commit):
        if not engine.contains(Path(c.names.worktree), r.commit):
            return conv.record(c, task, r, ctx.now), None  # the fix is gone: the item opens again with a new task
        cause = loop.cause_key(ErrorKind.GATE, step, "unpublished")
        reason = f"publishing the fix {r.commit[:7]} for {ref.url or ref.id}"
        return c, StepResult(exit=Exit.BACK, back_to=StepKind.PUBLISH, cause=cause, reason=reason)
    reply_id = conv.posted(items, ref.id, conv.marker(c.slug, ref.id, task.id), ctx.gh.viewer)
    return conv.record(c, task, r, ctx.now, reply_id or _post(ctx, c, pr, item, r=r, task=task.id)), None


def _repost(  # noqa: PLR0913 - one repost needs the PR, the item's state and the conversation read
    ctx: Ctx, c: Change, pr: PullRequest, s: conv.State, *, items: tuple[ConversationItem, ...], step: StepKind
) -> tuple[Change, StepResult | None]:
    """P13: adopt a replay of a deleted reply, else repost it; after ``REPOSTS`` reposts the owner decides."""
    assert s.rec  # noqa: S101 - only handled items reach here
    task = s.rec.task
    mark = conv.marker(c.slug, s.item.id, task)
    rec = next(h for h in c.handled if h.task == task)
    if replay := conv.posted(items, s.item.id, mark, ctx.gh.viewer):
        rec.reply_id = replay
        return c, None
    if rec.reposts >= REPOSTS:
        cause = loop.cause_key(ErrorKind.GATE, step, f"repost:{s.item.id}")
        asked = next((q for q in c.questions if q.cause == cause and q.answer and not q.effect_observed_at), None)
        if asked is None:
            where = s.item.url or s.item.id
            text = f"Delivery's reply on {where} keeps disappearing; reply manually or let Delivery post again"
            return c, engine.ask(step, text, cause, engine.continue_or_pause(step))
        c = loop.effect_observed(c, asked.id, ctx.now)
        rec = next(h for h in c.handled if h.task == task)
        rec.reposts = 0
    rec.reposts += 1
    rec.reply_id = _post(ctx, c, pr, s.item, r=Response(how=rec.how, text=rec.text, commit=rec.commit), task=task)
    return c, None


def _settle(
    ctx: Ctx, c: Change, s: conv.State, *, items: tuple[ConversationItem, ...], step: StepKind
) -> tuple[Change, StepResult | None]:
    """P13: observe a resolution, retry an unfinished one within budget; a reply not yet visible holds the merge."""
    assert s.rec  # noqa: S101 - only handled items reach here
    rec = next(h for h in c.handled if h.task == s.rec.task)  # an earlier charge copied the Change
    s = replace(s, rec=rec)
    where = s.item.url or s.item.id
    if conv.reply_missing(s, items):
        return c, engine.pending(Waiting.GITHUB, f"waiting for Delivery's reply on {where}", ctx.poll())
    if s.item.kind == "thread" and s.item.resolved:
        rec.resolved = True
    if not conv.unresolved(s):
        return c, None
    cause = loop.cause_key(ErrorKind.GATE, step, f"resolve:{s.item.id}")
    c, within = loop.charge(c, cause, ctx.now)
    if within:
        if ctx.gh.resolve_thread(s.item.id):
            next(h for h in c.handled if h.task == rec.task).resolved = True
            return c, None
        return c, engine.pending(Waiting.GITHUB, f"waiting for GitHub to show {where} resolved", ctx.poll())
    text = f"Resolving the review thread {where} did not take effect: resolve it in GitHub"
    return c, engine.ask(step, text, cause, engine.continue_or_pause(step))


def _open(c: Change, s: conv.State, step: StepKind) -> StepResult:
    """Back to build with the item version's unfinished task, or a new one."""
    reason = f"responding to {s.item.url or s.item.id}"
    todo = next((t for t in conv.group(c, s.task) if not t.done), None)
    if todo is None:
        todo = engine.task(c, conv.summary(s.item), "pr-feedback", f"{s.item.body}\n\n{s.item.url}", s.task)
        todo.item = conv.ref(s)
    return engine.back(ErrorKind.REVIEW, step, s.item.id, reason, todo)


def conversation(ctx: Ctx, c: Change, pr: PullRequest, step: StepKind) -> tuple[Change, StepResult | None]:
    """P3: pending replies, reposts of deleted ones, then resolutions and the first open item.

    Every post is followed by a fresh read: resolutions and the result use only the latest one.
    """
    items = ctx.gh.read_conversation(ctx.repository, pr.number)
    for task, r in conv.pending(c):
        c, held = _reply(ctx, c, pr, task, r, items=items, step=step)
        if held is not None:
            return c, held
        items = ctx.gh.read_conversation(ctx.repository, pr.number)
    published = _published(c, pr)
    found = conv.states(c, items, ctx.gh.viewer, published)
    missing = [s for s in found if conv.reply_missing(s, items)]
    for s in missing:
        c, held = _repost(ctx, c, pr, s, items=items, step=step)
        if held is not None:
            return c, held
    if missing:
        items = ctx.gh.read_conversation(ctx.repository, pr.number)
        found = conv.states(c, items, ctx.gh.viewer, published)
    for s in found:
        if s.rec is not None:
            c, held = _settle(ctx, c, s, items=items, step=step)
            if held is not None:
                return c, held
    opened = next((s for s in found if s.rec is None), None)
    return c, None if opened is None else _open(c, opened, step)


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
    c, held = conversation(ctx, c, pr, F)
    if held is not None:
        return c, held
    if state.missing and not state.running:
        return missing(ctx, c, pr, state)
    if state.running or state.missing:
        return c, waiting(state, ctx)
    paths = check.declared(c)
    ctx.log(c.slug, "ci", head=pr.head_sha, passed=list(state.passed), ignored=list(state.ignored))
    reason = f"CI passed: {', '.join(state.passed)}"
    return c, StepResult(exit=Exit.DONE, reason=reason, paths=paths, head=pr.head_sha)
