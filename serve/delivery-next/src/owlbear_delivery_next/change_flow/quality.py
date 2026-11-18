"""Change-wide configuration approvals, bound to protected content rather than a task's starting commit."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_quality.inspect import Protected, added, protected

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, StepKind
from owlbear_delivery_next.change_flow import exception_gate, worktree

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change


def git(at: Path, args: list[str]) -> str:
    """The Git runner the quality package reads commits through."""
    return worktree.git(at, *args)


def cause(digest: str, suppressions: str = "") -> str:
    """One cause across tasks and sessions for the exact protected before/after content."""
    return cause_key(ErrorKind.GATE, StepKind.BUILD, f"configuration-{digest}") + (
        f":suppressions-{suppressions}" if suppressions else ""
    )


def approved(c: Change, digest: str) -> bool:
    """An explicit Approve answer or an applied, owner-approved repair covers this digest only."""
    return any(
        (q.cause == cause(digest) or (q.cause or "").startswith(cause(digest) + ":suppressions-"))
        and q.answer is not None
        and q.answer.option == "approve"
        and q.answer.superseded_at is None
        for q in c.questions
    ) or any(r.approved_configuration == digest for r in c.repairs.done)


def current(c: Change, path: Path, commands: tuple[tuple[str, ...], ...] = ()) -> tuple[str, str, Protected | None]:
    """Compare HEAD with its merge-base with the Change's actual target, including merged target updates."""
    head = worktree.head(path)
    target = worktree.tracking(path, c.names.target)
    base = worktree.git(path, "merge-base", target, head).strip()
    return base, head, protected(git, path, base, head, commands=commands)


def check(c: Change, path: Path, commands: tuple[tuple[str, ...], ...] = (), *, folder: Path) -> list[str]:
    """Refuse unapproved configuration and suppressions, without lint's refusal allowance."""
    base, head, found = current(c, path, commands)
    if found is not None and not approved(c, found.digest):
        return [
            (
                f"configuration: {', '.join(found.paths)} changes lint, format, CI or hook configuration without the "
                "owner's approval. Call request_approval with why this change is needed, or take it back and commit."
            )
        ]
    items = exception_gate.pending(c, path, folder, (base, head))
    return exception_gate.errors(exception_gate.approved(c, folder, head, items))


def accept_repair(c: Change, path: Path, folder: Path, span: tuple[str, str]) -> None:
    """An owner-approved repair covers the copies its shown patch added that this Change has not accepted yet."""
    delta = {a.identity: a.count for a in added(git, path, *span)}
    base, head, _ = current(c, path)
    items = []
    for item in exception_gate.pending(c, path, folder, (base, head)):
        if delta.get(item["identity"], 0) > 0:  # never more receipts than the patch added
            delta[item["identity"]] -= 1
            items.append(item)
    if items:
        exception_gate.accept(c, folder, span[1], items)


def record_answers(c: Change, folder: Path, previous: Change) -> None:
    """Record an owner's suppression approval as soon as the answered question is persisted."""
    already = {q.id for q in previous.questions if q.answer and q.answer.option == "approve"}
    if not any(
        q.id not in already
        and q.cause
        and ":suppressions-" in q.cause
        and q.answer
        and q.answer.option == "approve"
        and q.answer.superseded_at is None
        for q in c.questions
    ):
        return
    path = Path(c.names.worktree)
    base, head, _ = current(c, path)
    exception_gate.approved(c, folder, head, exception_gate.pending(c, path, folder, (base, head)))
