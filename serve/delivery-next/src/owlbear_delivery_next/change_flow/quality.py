"""Change-wide configuration approvals, bound to protected content rather than a task's starting commit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_quality.inspect import Protected, protected

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, StepKind
from owlbear_delivery_next.change_flow import worktree

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change


def git(at: Path, args: list[str]) -> str:
    """The Git runner the quality package reads commits through."""
    return worktree.git(at, *args)


def cause(digest: str) -> str:
    """One cause across tasks and sessions for the exact protected before/after content."""
    return cause_key(ErrorKind.GATE, StepKind.BUILD, f"configuration-{digest}")


def approved(c: Change, digest: str) -> bool:
    """An explicit Approve answer or an applied, owner-approved repair covers this digest only."""
    return any(
        q.cause == cause(digest)
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


def check(c: Change, path: Path, commands: tuple[tuple[str, ...], ...] = ()) -> list[str]:
    """Refuse unapproved configuration; this is never a lint refusal or subject to lint's allowance."""
    _, _, found = current(c, path, commands)
    if found is None or approved(c, found.digest):
        return []
    return [
        (
            f"configuration: {', '.join(found.paths)} changes lint, format, CI or hook configuration without the "
            "owner's approval. Call request_approval with why this change is needed, or take it back and commit."
        )
    ]
