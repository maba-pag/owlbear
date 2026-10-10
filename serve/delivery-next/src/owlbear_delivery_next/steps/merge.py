"""Merge: an automatic gate at the exact PR head, re-checked under a per-target lock, then a guarded merge (TD-15)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import loop, profile
from owlbear_delivery_next.github import merge_offer
from owlbear_delivery_next.github.merge_offer import Block
from owlbear_delivery_next.github.provider import MergeMethod, MergeRequest, MergeStatus, Refusal
from owlbear_delivery_next.loop import StepResult, cause_key
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind, Waiting
from owlbear_delivery_next.steps import check, engine, follow, publish

if TYPE_CHECKING:
    from owlbear_delivery_next.github.merge_offer import Decision
    from owlbear_delivery_next.github.provider import CiState, MergeResult, PullRequest, Rules
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.steps.engine import Ctx

M = StepKind.MERGE
_ASSISTED = {Block.RULES_UNKNOWN, Block.NO_PERMISSION, Block.METHOD_NOT_ALLOWED, Block.WRONG_BASE, Block.PROTECTION}


def checks(state: CiState) -> list[dict[str, str]]:
    """The expected checks at the offered head, for the merge dialog."""
    rows = [(n, "passed") for n in state.passed] + [(c.name, "failed") for c in state.failed]
    rows += [(n, "running") for n in state.running] + [(n, "not started") for n in state.missing]
    return [{"name": n, "state": s} for n, s in rows]


def visual_ok(ctx: Ctx, c: Change, head: str) -> bool:  # noqa: ARG001 - hook for a later visual check
    """Visual acceptance of *head*; passes until a visual check exists."""
    return True


def offer(ctx: Ctx, c: Change, pr: PullRequest, state: CiState) -> StepResult:
    """Ask for consent to merge the PR's exact head; a consent for another head is void and the delta is shown."""
    old = c.consent.head if c.consent else None
    delta = ctx.gh.compare(ctx.repository, old, pr.head_sha) if old else ""
    method = profile.value(ctx.profile, profile.METHOD)
    fields = {"pr": pr.number, "url": pr.url, "head": pr.head_sha, "checks": checks(state), "method": method}
    ctx.log(c.slug, "merge-offer", **fields, void=old, delta=delta)
    text = f"approve merging {pr.head_sha[:7]}" + (f", changed since {old[:7]} ({delta})" if old else "")
    return engine.ask(M, text, loop.CONSENT)


def _review(ctx: Ctx, pr: PullRequest) -> StepResult | None:
    """Pending while GitHub waits for a required human review, naming the requested reviewers."""
    decision, reviewers = ctx.gh.review_request(ctx.repository, pr.number)
    if not merge_offer.review_required(decision):
        return None
    return _waiting_review(ctx, reviewers)


def _waiting_review(ctx: Ctx, reviewers: tuple[str, ...]) -> StepResult:
    return engine.pending(Waiting.REVIEWER, f"waiting for review by {', '.join(reviewers) or 'a reviewer'}", ctx.poll())


def _blocked(  # noqa: PLR0911 - one exit per block reason
    ctx: Ctx, c: Change, pr: PullRequest, state: CiState, decision: Decision
) -> tuple[Change, StepResult]:
    block, detail = decision.block, decision.detail
    match block:
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
            return c, engine.pending(Waiting.GITHUB, f"PR #{pr.number} marked ready again", ctx.poll())
        case Block.QUEUE:
            text = f"merge PR #{pr.number} in GitHub ({detail})"
            return c, engine.pending(Waiting.OWNER_ACTION, text, None, who="you")
        case b if b in _ASSISTED:
            text = f"merge PR #{pr.number} in GitHub ({b}: {detail or 'not supported here'})"
            return c, engine.pending(Waiting.OWNER_ACTION, text, None, who="you")
        case _:
            reason = f"GitHub is still computing whether PR #{pr.number} can merge"
            return c, engine.pending(Waiting.GITHUB, reason, ctx.poll())


def gate(  # noqa: PLR0911 - one exit per condition
    ctx: Ctx, c: Change, pr: PullRequest, rules: Rules
) -> tuple[Change, StepResult | None]:
    """Every merge condition at the PR's exact head; the first unmet one is the exit, None when it may merge."""
    path, target = Path(c.names.worktree), c.names.target
    if not publish.reviewed(c, path, pr.head_sha):
        reason = f"no valid final review of {pr.head_sha[:7]}"
        return c, StepResult(
            exit=Exit.BACK, back_to=StepKind.PUBLISH, cause=cause_key(ErrorKind.GATE, M, "review"), reason=reason
        )
    if (person := loop.next_check(c, check.declared(c))) is not None:
        reason = f"{person.id} needs your result again"
        return c, StepResult(
            exit=Exit.BACK, back_to=StepKind.FOLLOW, cause=cause_key(ErrorKind.GATE, M, person.id), reason=reason
        )
    c, held = follow.conversation(ctx, c, pr, M)  # open items, replies or resolutions hold the merge
    if held is not None:
        return c, held
    engine.fetch(path, target)
    if not engine.contains(path, f"origin/{target}"):
        return c, engine.integrate(c, M, f"origin/{target}")  # whatever GitHub's mergeable state says
    state = follow.ci(ctx, pr)
    c = follow.episode(ctx, c, pr.head_sha, state)
    decision = merge_offer.decide(
        pr,
        target=target,
        ci=state,
        rules=rules,
        rules_confirmed=profile.known(ctx.profile, profile.RULES),
        method=MergeMethod(profile.value(ctx.profile, profile.METHOD, "merge")),
        methods=tuple(MergeMethod(m.strip()) for m in profile.names(ctx.profile, profile.METHODS)),
        can_push=profile.value(ctx.profile, profile.PUSH) == "yes",
    )
    if decision.block in {None, Block.PROTECTION} and (held := _review(ctx, pr)) is not None:
        return c, held
    if decision.block is not None:
        return _blocked(ctx, c, pr, state, decision)
    if not visual_ok(ctx, c, pr.head_sha):
        return c, engine.pending(Waiting.PERSON_CHECK, f"visual check of {pr.head_sha[:7]}", ctx.poll())
    asking = profile.value(ctx.profile, profile.ASK) == "yes"
    if asking and merge_offer.consent(c.consent.head if c.consent else None, pr.head_sha) != "valid":
        return c, offer(ctx, c, pr, state)
    return c, None


def _readback(ctx: Ctx, c: Change, req: MergeRequest, result: MergeResult) -> StepResult:
    number, head = req.number, req.expected_head_sha
    pr = ctx.gh.read_pull_request(ctx.repository, number)
    match merge_offer.readback(pr, head):
        case "applied":
            sha = pr.merge_commit_sha or result.sha or ""
            method = profile.value(ctx.profile, profile.METHOD)
            ctx.log(c.slug, "merged", pr=number, head=head, sha=sha, method=method)
            return StepResult(exit=Exit.DONE, reason=f"merged PR #{number} as {sha[:7]} ({method})")
        case "not-applied":  # confirmed absence: the next attempt sends the merge again
            reason = f"merge of {head[:7]} not applied: {result.message or result.status}"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.NETWORK, M, "merge"), reason=reason)
        case _:
            reason = f"PR #{number} moved during the merge"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.CONFLICT, M, "head"), reason=reason)


def submit(ctx: Ctx, c: Change, pr: PullRequest) -> StepResult:
    """Send the merge with ``sha`` = the gated head and the profile's method, then read the PR back."""
    method = MergeMethod(profile.value(ctx.profile, profile.METHOD))
    req = MergeRequest(repository=ctx.repository, number=pr.number, expected_head_sha=pr.head_sha, method=method)
    result = ctx.gh.request_merge(req)
    ctx.log(c.slug, "merge-request", pr=pr.number, head=pr.head_sha, status=result.status, message=result.message)
    match result.status:
        case MergeStatus.REFUSED if result.refusal == Refusal.HEAD_CHANGED:
            reason = "the PR head changed since the gate"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.CONFLICT, M, "head"), reason=reason)
        case MergeStatus.REFUSED if merge_offer.review_required(None, result.message):
            return _waiting_review(ctx, ctx.gh.review_request(ctx.repository, pr.number)[1])
        case MergeStatus.REFUSED if result.refusal == Refusal.NOT_MERGEABLE:
            reason = f"GitHub refused: {result.message or 'not mergeable'}"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.GATE, M, "mergeable"), reason=reason)
        case MergeStatus.REFUSED:
            text = f"merge PR #{pr.number} in GitHub: {result.message or result.refusal}"
            return engine.pending(Waiting.OWNER_ACTION, text, None, who="you")
        case _:
            return _readback(ctx, c, req, result)


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:  # noqa: PLR0911 - each read may end the step
    """Gate the head, then hold the target's merge lock, re-read everything, gate again and merge that head."""
    asked, rules = engine.rules_changed(ctx, c)
    if asked is not None:
        return c, asked
    number, target = c.names.pr or 0, c.names.target
    pr = ctx.gh.read_pull_request(ctx.repository, number)
    if pr.merged:
        return c, StepResult(exit=Exit.DONE, reason=f"PR #{pr.number} was merged in GitHub")
    c, held = gate(ctx, c, pr, rules)
    if held is not None:
        return c, held
    with ctx.store.merge_lock(target) as locked:
        if not locked:
            return c, engine.pending(
                Waiting.GITHUB, f"another Change is merging into {target}", ctx.poll(), who="delivery"
            )
        pr = ctx.gh.read_pull_request(ctx.repository, number)  # everything is read again under the lock
        if pr.merged:
            return c, StepResult(exit=Exit.DONE, reason=f"PR #{pr.number} was merged in GitHub")
        c, held = gate(ctx, c, pr, rules)
        if held is not None:
            return c, held
        return c, submit(ctx, c, pr)
