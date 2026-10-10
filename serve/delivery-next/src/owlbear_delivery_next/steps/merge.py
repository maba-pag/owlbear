"""Merge: consent bound to the exact head, rules re-read, direct merge guarded by ``sha``, then readback (D3, D4)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import loop, profile
from owlbear_delivery_next.github import merge_offer
from owlbear_delivery_next.github.merge_offer import Block
from owlbear_delivery_next.github.provider import MergeMethod, MergeRequest, MergeStatus, Refusal
from owlbear_delivery_next.loop import StepResult, cause_key
from owlbear_delivery_next.models import ErrorKind, Exit, Option, StepKind, Waiting
from owlbear_delivery_next.steps import engine, follow

if TYPE_CHECKING:
    from owlbear_delivery_next.github.provider import CiState, MergeResult, PullRequest
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.steps.engine import Ctx

M = StepKind.MERGE
_ASSISTED = {Block.RULES_UNKNOWN, Block.NO_PERMISSION, Block.METHOD_NOT_ALLOWED, Block.WRONG_BASE, Block.PROTECTION}


def checks(state: CiState) -> list[dict[str, str]]:
    """The expected checks at the offered head, for the merge dialog."""
    rows = [(n, "passed") for n in state.passed] + [(c.name, "failed") for c in state.failed]
    rows += [(n, "running") for n in state.running] + [(n, "not started") for n in state.missing]
    return [{"name": n, "state": s} for n, s in rows]


def offer(ctx: Ctx, c: Change, pr: PullRequest, state: CiState) -> StepResult:
    """Ask for consent to merge the PR's exact head; a consent for another head is void and the delta is shown."""
    old = c.consent.head if c.consent else None
    delta = ctx.gh.compare(ctx.repository, old, pr.head_sha) if old else ""
    method = profile.value(ctx.profile, profile.METHOD)
    fields = {"pr": pr.number, "url": pr.url, "head": pr.head_sha, "checks": checks(state), "method": method}
    ctx.log(c.slug, "merge-offer", **fields, void=old, delta=delta)
    text = f"approve merging {pr.head_sha[:7]}" + (f", changed since {old[:7]} ({delta})" if old else "")
    return engine.ask(M, text, loop.CONSENT)


def _readback(ctx: Ctx, c: Change, req: MergeRequest, result: MergeResult) -> StepResult:
    number, head = req.number, req.expected_head_sha
    pr = ctx.gh.read_pull_request(ctx.repository, number)
    match merge_offer.readback(pr, head):
        case "applied":
            sha = pr.merge_commit_sha or result.sha or ""
            method = profile.value(ctx.profile, profile.METHOD)
            ctx.log(c.slug, "merged", pr=number, head=head, sha=sha, method=method)
            return StepResult(exit=Exit.DONE, reason=f"merged PR #{number} as {sha[:7]} ({method})")
        case "not-applied" if req.queue:  # an open PR is not absence from the queue; the next run observes it
            return engine.pending(Waiting.MERGE_QUEUE, f"observing the merge queue for PR #{number}", ctx.poll())
        case "not-applied":  # confirmed absence: the next attempt sends the merge again
            reason = f"merge of {head[:7]} not applied: {result.message or result.status}"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.NETWORK, M, "merge"), reason=reason)
        case _:
            reason = f"PR #{number} moved during the merge"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.CONFLICT, M, "head"), reason=reason)


def submit(ctx: Ctx, c: Change, pr: PullRequest, *, queue: bool) -> StepResult:
    """Send the merge with ``sha`` = the consented head and the profile's method, then read the PR back."""
    head = c.consent.head if c.consent else pr.head_sha
    method = MergeMethod(profile.value(ctx.profile, profile.METHOD))
    req = MergeRequest(repository=ctx.repository, number=pr.number, expected_head_sha=head, method=method, queue=queue)
    if queue and c.consent:
        c.consent.queued_at = ctx.now
        ctx.store.write(ctx.lock, c)  # durable before the send: a lost response is observed in the queue, not resent
    result = ctx.gh.request_merge(req)
    ctx.log(c.slug, "merge-request", pr=pr.number, head=head, status=result.status, message=result.message)
    if result.status == MergeStatus.REFUSED and c.consent:
        c.consent.queued_at = None
    match result.status:
        case MergeStatus.ENQUEUED | MergeStatus.PENDING:
            return engine.pending(Waiting.MERGE_QUEUE, f"PR #{pr.number} is in the merge queue", ctx.poll())
        case MergeStatus.REFUSED if result.refusal == Refusal.HEAD_CHANGED:
            reason = "the PR head changed; consent is void"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.CONFLICT, M, "head"), reason=reason)
        case MergeStatus.REFUSED if result.refusal == Refusal.NOT_MERGEABLE:
            reason = f"GitHub refused: {result.message or 'not mergeable'}"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.GATE, M, "mergeable"), reason=reason)
        case MergeStatus.REFUSED:
            text = f"merge PR #{pr.number} in GitHub: {result.message or result.refusal}"
            return engine.pending(Waiting.OWNER_ACTION, text, None, who="you")
        case _:
            return _readback(ctx, c, req, result)


def queued(ctx: Ctx, c: Change, pr: PullRequest) -> StepResult | None:
    """M3: observe queue membership before any resubmission; a removal routes its cause or asks with its reason."""
    if c.consent is None or c.consent.queued_at is None:
        return None
    entry = ctx.gh.read_queue(ctx.repository, pr.number)
    state = merge_offer.queue_state(entry, c.consent.queued_at)
    ctx.log(c.slug, "merge-queue", pr=pr.number, state=state, reason=entry.reason)
    if state == "queued":
        return engine.pending(Waiting.MERGE_QUEUE, f"PR #{pr.number} is in the merge queue", ctx.poll())
    c.consent.queued_at = None
    if state == "absent":
        return None  # confirmed: the submission never entered the queue, so it is sent again
    reason = entry.reason or "no reason given"
    match merge_offer.removal(entry.reason):
        case "conflict":
            engine.fetch(Path(c.names.worktree), c.names.target)
            return engine.integrate(c, M, f"origin/{c.names.target}", reason)
        case "ci":
            fix = engine.task(c, "Fix the check that removed the PR from the merge queue", "ci", reason)
            return engine.back(ErrorKind.CHECKS, M, "merge-queue", f"removed from the merge queue: {reason}", fix)
        case _:
            options = [
                Option(id="again", label="Submit it to the merge queue again", next=M),
                Option(id="pause", label="Pause", next="pause"),
            ]
            text = f"PR #{pr.number} was removed from the merge queue: {reason}"
            return engine.ask(M, text, cause_key(ErrorKind.GATE, M, "queue-removed"), options)


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:  # noqa: C901, PLR0911, PLR0912 - one exit per block reason
    """Queue first, then the target, consent, green checks and mergeability at that head, then the guarded merge."""
    asked, rules = engine.rules_changed(ctx, c)
    if asked is not None:
        return c, asked
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr or 0)
    if pr.merged:
        return c, StepResult(exit=Exit.DONE, reason=f"PR #{pr.number} was merged in GitHub")
    if (held := queued(ctx, c, pr)) is not None:
        return c, held
    if (fix := follow.feedback(ctx, c, pr, M)) is not None:  # a comment after CI passed, consented or not
        return c, fix
    engine.fetch(Path(c.names.worktree), c.names.target)
    if not engine.contains(Path(c.names.worktree), f"origin/{c.names.target}"):
        return c, engine.integrate(c, M, f"origin/{c.names.target}")  # whatever GitHub's mergeable state says
    state = follow.ci(ctx, pr)
    c = follow.episode(ctx, c, pr.head_sha, state)
    if merge_offer.consent(c.consent.head if c.consent else None, pr.head_sha) != "valid":
        return c, offer(ctx, c, pr, state)
    decision = merge_offer.decide(
        pr,
        target=c.names.target,
        ci=state,
        rules=rules,
        rules_confirmed=profile.known(ctx.profile, profile.RULES),
        method=MergeMethod(profile.value(ctx.profile, profile.METHOD, "merge")),
        methods=tuple(MergeMethod(m.strip()) for m in profile.names(ctx.profile, profile.METHODS)),
        can_push=profile.value(ctx.profile, profile.PUSH) == "yes",
    )
    match decision.block:
        case None:
            return c, submit(ctx, c, pr, queue=decision.action == "queue")
        case Block.CHECKS_FAILED:
            return c, follow.fix_ci(ctx, c, state, M)
        case Block.CHECKS_RUNNING if state.missing and not state.running:
            return follow.missing(ctx, c, pr, state, M)
        case Block.CHECKS_RUNNING:
            return c, follow.waiting(state, ctx)
        case Block.CONFLICTS | Block.BEHIND:
            return c, engine.integrate(c, M, f"origin/{c.names.target}")
        case Block.DRAFT:
            ctx.gh.mark_ready(pr)
            return c, engine.pending(Waiting.MERGE_QUEUE, f"PR #{pr.number} marked ready again", ctx.poll())
        case block if block in _ASSISTED:
            text = f"merge PR #{pr.number} in GitHub ({block}: {decision.detail or 'not supported here'})"
            return c, engine.pending(Waiting.OWNER_ACTION, text, None, who="you")
        case _:
            reason = f"GitHub is still computing whether PR #{pr.number} can merge"
            return c, engine.pending(Waiting.MERGE_QUEUE, reason, ctx.poll())
