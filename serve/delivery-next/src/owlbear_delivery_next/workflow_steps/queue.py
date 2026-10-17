"""Merging through a GitHub merge queue (TD-226): enqueue once, follow, handle removals, leave before moving on.

GitHub's queue state is read on every pass and never stored (DR5): ``Change.queue`` is Delivery's own attempt and
``Change.queue_seen`` the last removal it handled. Live facts (2026-10-17, porsche-code/brief-layover): an entry's
head commit is the merge group's commit once it is built; a removal's ``before`` is that group's commit; the
reasons seen were ``merged``, ``failed_checks``, ``checks_timed_out`` and ``manual``; a second enqueue is refused
as "already in the queue" and a stale expected head is refused.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import (
    ErrorKind,
    Exit,
    Option,
    QueueClaim,
    Score,
    StepKind,
    Waiting,
)
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.github.provider import SUCCESS, EnqueueStatus, ProviderError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.workflow_steps import engine

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.github.provider import Provider, PullRequest, QueueEvent, QueueState, Rules
    from owlbear_delivery_next.state_store.store import Store
    from owlbear_delivery_next.workflow_steps.engine import Ctx

    type Gate = Callable[[Ctx, Change, PullRequest, Rules], tuple[Change, StepResult | None]]
    type Leave = Callable[[Change, Change], Change | None]

M = StepKind.MERGE
QUIET = 3  # passes without evidence of an enqueue before the owner is asked
SKEW = timedelta(minutes=2)  # GitHub's clock against the host's, for a claim timed by the host
UNSEEN = cause_key(ErrorKind.GATE, M, "queue-unseen")
TIMED_OUT = cause_key(ErrorKind.GATE, M, "queue-timed-out")
REMOVED = cause_key(ErrorKind.GATE, M, "queue-removed")
AGAIN = Option(id="again", label="Enqueue it again", next=M)
PAUSE = Option(id="pause", label="Pause", next="pause")


def _seen(c: Change, q: QueueState, until: datetime | None = None) -> None:
    """Count the removals GitHub shows now (or those up to *until*) as handled: an attempt starts from here."""
    if q.removed and (until is None or q.removed.at <= until):
        c.queue_seen = q.removed.id


def _owner_cleared(c: Change, now: datetime) -> None:
    """The owner's "enqueue again" ends an attempt that never showed up."""
    for q in c.questions:
        if q.cause == UNSEEN and q.answer and q.answer.option == AGAIN.id and not q.effect_observed_at:
            c.queue, q.effect_observed_at = None, now


def _merged(ctx: Ctx, c: Change, pr: PullRequest) -> StepResult:
    c.queue = None
    done = ctx.gh.read_pull_request(ctx.repository, pr.number)
    sha = done.merge_commit_sha or ""
    ctx.log(c.slug, "merged", pr=pr.number, head=pr.head_sha, sha=sha, method="queue")
    return StepResult(exit=Exit.DONE, reason=f"merged PR #{pr.number} through the merge queue as {sha[:7]}")


def _group_fix(ctx: Ctx, c: Change, pr: PullRequest, r: QueueEvent) -> StepResult:
    """A fix task with the failing job's log of the very group this removal ended (bound by its commit)."""
    try:
        runs = ctx.gh.group_runs(ctx.repository, r.before) if r.before else ()
        failed = [x for x in runs if x.conclusion and x.conclusion not in SUCCESS]
        log = ctx.gh.group_log(ctx.repository, failed[0].id) if failed else ""
    except ProviderError:
        failed, log = [], ""
    group = f"group {r.before[:7]}" if r.before else "a group"
    where = f"PR #{pr.number} merged with {c.names.target} and any PRs queued ahead ({group})"
    detail = f"The merge queue's required checks failed on {where}.\n{log}"
    if not log:
        detail = f"The merge queue's required checks failed on {where}; the failing run could not be read."
    fix = engine.task(c, "Fix the check that failed in the merge queue", "ci", detail)
    result = engine.back(ErrorKind.CHECKS, M, "merge-queue", "fixing the merge queue's failed checks", fix)
    names = sorted({x.name or "merge-queue" for x in failed}) or ["merge-queue"]
    return result.model_copy(update={"score": Score(failing=len(names), findings=names)})  # fewer is progress


def _removed(ctx: Ctx, c: Change, pr: PullRequest, r: QueueEvent) -> StepResult:
    """One removal, handled once: ``queue_seen`` advances in the write that records this step's result."""
    ctx.log(c.slug, "queue-removed", pr=pr.number, reason=r.reason, group=r.before, actor=r.actor)
    if r.reason == "failed_checks":
        result = _group_fix(ctx, c, pr, r)
    elif r.reason == "checks_timed_out":
        text = (
            f"The merge queue took PR #{pr.number} out: its required checks never reported on the merge group "
            "(usually a workflow without `merge_group:`). Fix the workflow, then enqueue it again"
        )
        result = engine.ask(M, text, TIMED_OUT, [AGAIN, PAUSE])
    elif "conflict" in r.reason:
        result = engine.integrate(c, M, f"origin/{c.names.target}")
    else:
        who = f" by {r.actor}" if r.actor else ""
        text = f"PR #{pr.number} was taken out of the merge queue ({r.reason or 'no reason given'}{who})"
        result = engine.ask(M, f"{text}: enqueue it again or pause", REMOVED, [AGAIN, PAUSE])
    c.queue, c.queue_seen = None, r.id
    return result


def _leave(ctx: Ctx, c: Change, pr: PullRequest, held: StepResult) -> tuple[Change, StepResult]:
    """A gate that fails while the PR is queued takes it out first, then routes as the gate says."""
    try:
        ctx.gh.dequeue(pr)
        q = ctx.gh.read_queue(ctx.repository, pr.number)
    except ProviderError as exc:
        return c, engine.pending(Waiting.GITHUB, f"taking PR #{pr.number} out of the merge queue ({exc})", ctx.poll())
    if q.merged:
        return c, _merged(ctx, c, pr)
    if q.entry is not None:
        return c, engine.pending(Waiting.GITHUB, f"taking PR #{pr.number} out of the merge queue", ctx.poll())
    c.queue = None
    _seen(c, q)
    ctx.log(c.slug, "queue-left", pr=pr.number, reason=held.reason)
    return c, held


def hold(ctx: Ctx, c: Change, held: StepResult) -> tuple[Change, StepResult]:
    """A question the merge step asks before reading the queue (a rules change): a queued PR is taken out first."""
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr or 0)
    q = ctx.gh.read_queue(ctx.repository, pr.number)
    if q.merged:
        return c, _merged(ctx, c, pr)
    return (c, held) if q.entry is None else _leave(ctx, c, pr, held)


def _enqueue(ctx: Ctx, c: Change, pr: PullRequest, q: QueueState) -> StepResult:
    """Write the claim, then send once; only a definite answer settles it (``expectedHeadOid`` guards the head)."""
    c.queue = QueueClaim(head=pr.head_sha, at=ctx.now)
    _seen(c, q)
    ctx.store.write(ctx.lock, c)  # the claim outlives a crash between the send and the step's own write
    result = ctx.gh.enqueue(pr, pr.head_sha)
    ctx.log(c.slug, "merge-enqueue", pr=pr.number, head=pr.head_sha, status=result.status, message=result.message)
    message = result.message or ""
    if result.status == EnqueueStatus.ENQUEUED or "already in the queue" in message:
        c.queue.settled = True
        return engine.pending(Waiting.GITHUB, f"PR #{pr.number} added to the merge queue", ctx.poll())
    if result.status == EnqueueStatus.UNKNOWN:
        return engine.pending(Waiting.GITHUB, f"waiting for GitHub to show PR #{pr.number} queued", ctx.poll())
    c.queue = None
    if "head oid does not match" in message:
        cause = cause_key(ErrorKind.CONFLICT, M, "head")
        return StepResult(exit=Exit.RETRY, cause=cause, reason="the PR head changed since the gate")
    text = f"add PR #{pr.number} to the merge queue in GitHub: {message}"
    return engine.pending(Waiting.OWNER_ACTION, text, None, who="you")


def _relevant(c: Change, q: QueueState) -> QueueEvent | None:
    """A removal of this attempt not handled yet; earlier removals, and any without an attempt, are not its own."""
    r, claim = q.removed, c.queue
    if claim is None or r is None or r.id == c.queue_seen or r.reason == "merged" or r.at < claim.at - SKEW:
        return None
    return r


def _queued(  # noqa: PLR0913, PLR0917 - the merge step's own inputs and this pass's read
    ctx: Ctx, c: Change, pr: PullRequest, rules: Rules, gate: Gate, q: QueueState
) -> tuple[Change, StepResult]:
    """The PR is queued: adopt a person's entry, keep gating, and take it out when a gate fails (design §3.3)."""
    e = q.entry
    if c.queue is None:  # a person enqueued it: Delivery follows it under the same gate
        c.queue = QueueClaim(head=pr.head_sha, at=e.enqueued_at if e else ctx.now, settled=True, adopted=True)
        _seen(c, q, e.enqueued_at if e else None)  # a removal after this entry stays to be handled
        ctx.log(c.slug, "queue-adopted", pr=pr.number, head=pr.head_sha)
    c.queue.settled, c.queue.quiet = True, 0
    c, held = gate(ctx, c, pr, rules)
    if held is not None:
        return _leave(ctx, c, pr, held)
    where = f"position {e.position}, {e.state.lower().replace('_', ' ')}" if e else "queued"
    return c, engine.pending(Waiting.GITHUB, f"PR #{pr.number} in the merge queue: {where}", ctx.poll())


def _untraced(ctx: Ctx, c: Change, pr: PullRequest) -> StepResult:
    """An attempt GitHub shows no trace of yet: never sent again without the owner."""
    claim = c.queue
    if claim is not None:
        claim.quiet += 1
        if claim.quiet >= QUIET:
            text = f"GitHub shows no trace of PR #{pr.number} in the merge queue after Delivery added it"
            return engine.ask(M, f"{text}: enqueue it again or pause", UNSEEN, [AGAIN, PAUSE])
    return engine.pending(Waiting.GITHUB, f"waiting for GitHub to show PR #{pr.number} queued", ctx.poll())


def _locked(ctx: Ctx, c: Change, pr: PullRequest, rules: Rules, gate: Gate) -> tuple[Change, StepResult]:
    """Under the target's merge lock everything is read and gated again; only then is the PR enqueued."""
    with ctx.store.merge_lock(c.names.target) as locked:
        if not locked:
            text = f"another Change is merging into {c.names.target}"
            return c, engine.pending(Waiting.GITHUB, text, ctx.poll(), who="delivery")
        pr = ctx.gh.read_pull_request(ctx.repository, pr.number)
        if pr.merged:
            return c, _merged(ctx, c, pr)
        c, held = gate(ctx, c, pr, rules)
        if held is not None:
            return c, held
        q = ctx.gh.read_queue(ctx.repository, pr.number)
        if q.merged:
            return c, _merged(ctx, c, pr)
        if q.entry is not None:  # queued meanwhile by someone else: follow it, never send a second time
            return _queued(ctx, c, pr, rules, gate, q)
        return c, _enqueue(ctx, c, pr, q)


def run(ctx: Ctx, c: Change, pr: PullRequest, rules: Rules, gate: Gate) -> tuple[Change, StepResult]:  # noqa: PLR0911
    """One pass of the merge step on a queue-required target (design §3.4)."""
    _owner_cleared(c, ctx.now)
    q = ctx.gh.read_queue(ctx.repository, pr.number)
    if q.merged:
        return c, _merged(ctx, c, pr)
    if (r := _relevant(c, q)) is not None:
        if q.entry is not None:  # removed after this attempt, yet queued: GitHub's reads disagree for now
            return c, engine.pending(Waiting.GITHUB, f"reading PR #{pr.number}'s merge queue again", ctx.poll())
        return c, _removed(ctx, c, pr, r)
    if q.entry is not None:
        return _queued(ctx, c, pr, rules, gate, q)
    if c.queue is not None:
        return c, _untraced(ctx, c, pr)
    c, held = gate(ctx, c, pr, rules)
    if held is not None:
        return c, held
    return _locked(ctx, c, pr, rules, gate)


def leaving(before: Change, after: Change) -> bool:
    """Whether folding the inbox moves a Change off its merge step, pauses it or abandons it."""
    if before.step.kind != M:
        return False
    paused = after.intent.paused_at is not None and before.intent.paused_at is None
    abandoned = after.intent.abandoned_at is not None and before.intent.abandoned_at is None
    return after.step.kind != M or paused or abandoned


def _resolved(before: Change, after: Change) -> bool:
    """The owner answered, in this fold, the question about an attempt GitHub showed no trace of."""
    open_ids = {q.id for q in before.questions if q.cause == UNSEEN and q.answer is None}
    return any(q.id in open_ids and q.answer is not None for q in after.questions)


def barrier(store: Store, repo: Path) -> Leave:
    """The pre-fold step both fold callers use: a queued PR is taken out before an action leaves the merge step.

    Returns the folded Change to write, or None to keep the inbox items waiting for the next pass. An attempt
    ends only by a removal after it, a dequeue read back, the merge, or the owner's answer (design §3.4).
    """

    def leave(before: Change, after: Change) -> Change | None:  # noqa: PLR0911 - one exit per observation
        prof = store.read_profile()
        queued = before.queue is not None or bool(prof and profile.value(prof, profile.QUEUE) == "yes")
        if not (queued and leaving(before, after) and before.names.pr and prof):
            return after
        gh: Provider = profile.provider(prof, repo)
        repository = profile.value(prof, profile.REPO)
        try:
            q = gh.read_queue(repository, before.names.pr)
            if q.merged:  # the action waits until the fold itself observes the merge and ends the Change
                return after if after.step.kind == StepKind.CLEANUP and after.step.mode != "abandon" else None
            if q.entry is None:
                if before.queue is not None and _relevant(before, q) is None and not _resolved(before, after):
                    return None  # an attempt without a trace may still appear in the queue
                after.queue = None
                _seen(after, q)
                return after
            gh.dequeue(gh.read_pull_request(repository, before.names.pr))
            q = gh.read_queue(repository, before.names.pr)
        except ProviderError:
            return None
        if q.entry is not None or q.merged:
            return None
        after.queue = None
        _seen(after, q)
        return after

    return leave
