"""Publish: integrate check, push the Change branch with hooks, create or reuse the PR and mark it ready (D3)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import profile
from owlbear_delivery_next.evidence import review_valid
from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.git.remote_git import (
    RemoteGitWriteUnknown,
    classify_write_readback,
    read_remote_ref,
    run_remote_git,
)
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind
from owlbear_delivery_next.steps import engine, worktree

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from owlbear_delivery_next.github.provider import PullRequest
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.setup import Check
    from owlbear_delivery_next.steps.engine import Ctx

P = StepKind.PUBLISH
_PUSH_FAILED = 1  # git push exits 1 when a hook or the remote refuses; transport and auth failures exit 128


def hook_rejected(returncode: int | None, stderr: bytes, *, hook: bool) -> bool:
    """Whether a push that read back as not applied was refused by the local pre-push hook, even a silent one."""
    return hook and returncode == _PUSH_FAILED and b"rejected]" not in stderr


def push(path: Path, c: Change, head: str) -> StepResult | None:  # noqa: PLR0911 - one exit per readback
    """Push HEAD to the Change branch, never forced and with hooks; an unknown result is read back first.

    Only a readback that confirms absence replays the push, once, or names a rejecting pre-push hook;
    a moved remote branch is integrated.
    """
    ref = f"refs/heads/{c.names.branch}"
    before = read_remote_ref(path, "origin", ref)
    if before == head:
        return None
    if before and not engine.contains(path, before, head):
        engine.fetch(path, c.names.branch)
        return engine.integrate(c, P, f"origin/{c.names.branch}")
    for _ in range(2):
        try:
            run_remote_git(path, ("push", "--quiet", "origin", f"{head}:{ref}"), kind="write")
        except RemoteGitWriteUnknown as exc:
            match classify_write_readback(read_remote_ref(path, "origin", ref), intended=head, expected_old=before):
                case "applied":
                    return None
                case "conflict":
                    engine.fetch(path, c.names.branch)
                    return engine.integrate(c, P, f"origin/{c.names.branch}")
                case "not-applied" if exc.result and hook_rejected(
                    exc.result.returncode, exc.result.stderr, hook=profile.pre_push_hook(path)[0]
                ):
                    out = exc.result.stderr.decode(errors="replace").strip()
                    detail = f"{out}\nRun the hook without pushing: git push --dry-run origin HEAD:{ref}"
                    fix = engine.task(c, "Make the pre-push hook pass, then commit", "review", detail)
                    return engine.back(ErrorKind.COMMIT_POLICY, P, "pre-push", "pre-push hook rejected the push", fix)
                case "not-applied":
                    continue
        else:
            return None
    reason = "the push did not reach GitHub"
    return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.NETWORK, P, "push"), reason=reason)


def _body(c: Change) -> str:
    criteria = "\n".join(f"- {k.id}: {k.text}" for k in c.brief.criteria)
    return f"{c.brief.outcome}\n\n## Acceptance criteria\n{criteria}\n\nOpened by OwlBear Delivery for `{c.slug}`."


def pull_request(ctx: Ctx, c: Change, head: str) -> PullRequest | None:
    """Find the open PR of the branch or create a draft; an unknown create is read back, never repeated blindly."""
    repo, branch, target = ctx.repository, c.names.branch, c.names.target
    pr = ctx.gh.find_pull_request(repo, branch, target)
    if pr is None:
        title = c.brief.title or (c.plan.tasks[0].title if c.plan and c.plan.tasks else c.slug)
        try:
            pr = ctx.gh.create_pull_request(repo, branch, target, title[:200], _body(c))
        except ProviderError as exc:
            if exc.retry_safe:
                raise
            pr = ctx.gh.find_pull_request(repo, branch, target)
    if pr and pr.draft and pr.head_sha == head:
        try:
            ctx.gh.mark_ready(pr)
        except ProviderError as exc:
            if exc.retry_safe:
                raise
        pr = ctx.gh.read_pull_request(repo, pr.number)
    return pr


def reviewed(c: Change, path: Path, head: str) -> bool:
    """Whether the last final review passed and still holds for *head* (P5, F3).

    It holds on its own commit, on an identical tree, or when every path that differs between the reviewed
    tree and *head*'s tree, a target merge's included, is one the review covered with unchanged fingerprints.
    """
    final = next((v for v in reversed(c.reviews) if v.task is None), None)
    if final is None or (final.commit != head and not final.tree):
        return False  # carrying a review to another head needs its engine-recorded tree and coverage
    candidate = worktree.tree(path, head)
    if final.tree == candidate:
        return review_valid(c, final, final.inputs.paths)  # identical content: only the criteria can have moved
    changed = worktree.between(path, final.tree, candidate) if final.tree else None
    return review_valid(c, final, worktree.fingerprints(path, list(final.inputs.paths), head), changed=changed)


def gate(checks: Sequence[Check], now: datetime) -> StepResult | None:
    """DR2 before publishing: the first failed readiness fact becomes its exit, carrying its one fix."""
    first = next((c for c in checks if not c.ok), None)
    if first is None:
        return None
    reason = f"{first.name}: {first.detail} · {first.fix}"
    if first.name == "network":  # an environment episode like any other offline retry: asks only after a day
        cause = cause_key(ErrorKind.NETWORK, P, "readiness")
        return StepResult(exit=Exit.RETRY, cause=cause, reason=reason, wake_at=now + timedelta(minutes=1))
    kind = {"github sign-in": ErrorKind.AUTH, "repository": ErrorKind.POLICY}.get(first.name, ErrorKind.TOOLING)
    return engine.ask(P, reason, cause_key(kind, P, first.name), engine.continue_or_pause(P))


def run(ctx: Ctx, c: Change) -> tuple[Change, StepResult]:
    """Publish the final-reviewed head; a moved target first gets an integration Builder task."""
    path, target = Path(c.names.worktree), c.names.target
    if (asked := engine.rules_changed(ctx, c)[0]) is not None:
        return c, asked
    engine.fetch(path, target)
    if not engine.contains(path, f"origin/{target}"):
        return c, engine.integrate(c, P, f"origin/{target}")
    head = engine.head(path)
    if not reviewed(c, path, head):
        cause, reason = cause_key(ErrorKind.GATE, P, "unreviewed"), f"no valid final review of {head[:7]}"
        return c, StepResult(exit=Exit.BACK, back_to=StepKind.REVIEW, cause=cause, reason=reason)
    if (r := push(path, c, head)) is not None:
        return c, r
    pr = pull_request(ctx, c, head)
    if pr is None or pr.draft or pr.head_sha != head:
        state = "absent" if pr is None else "a draft" if pr.draft else f"at {pr.head_sha[:7]}"
        reason = f"the PR is {state} after publishing {head[:7]}"
        return c, StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.NETWORK, P, "pr"), reason=reason)
    c.names.pr = pr.number
    ctx.log(c.slug, "publish", pr=pr.number, head=head, url=pr.url)
    return c, StepResult(exit=Exit.DONE, reason=f"PR #{pr.number} ready at {head[:7]}")
