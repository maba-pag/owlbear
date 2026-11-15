"""Detached audit worktrees, shared-Git inspection and lease-aware removal."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.workflow_steps import disposable, engine
from owlbear_delivery_next.workflow_steps.disposable import _refs, _shared

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from owlbear_delivery_next.github.account import Access
    from owlbear_delivery_next.local_system.maintenance import Maintenance


def pin(repo: Path, branch: str, access: Access) -> str:
    """Fetch the selected branch and resolve the fetched commit, without moving the clone."""
    engine.fetch(repo, branch, access)
    return worktree.git(repo, "rev-parse", "--verify", f"refs/remotes/origin/{branch}^{{commit}}").strip()


@contextmanager
def opened(maintenance: Maintenance, repo: Path, commit: str) -> Iterator[disposable.Copy]:
    """Keep the entire root when a session's processes are not confirmed gone."""
    with maintenance.workspace("owlbear-audit-") as root:
        at = root / "repo"
        worktree.git(repo, "worktree", "add", "--quiet", "--detach", str(at), commit)
        try:
            yield disposable.Copy(repo, at, _refs(repo), _shared(repo))
        finally:
            if not maintenance.retained(str(root)):
                worktree.git(repo, "worktree", "remove", "--force", str(at))
                worktree.git(repo, "worktree", "prune")


def inspect(copy: disposable.Copy, expected: str) -> None:
    """Void a result after any shared-Git mutation; restore nothing."""
    changed = [*disposable.tampered(copy), *disposable.changed(copy)]
    if worktree.git(copy.path, "rev-parse", "HEAD").strip() != expected:
        changed.append("the audit worktree no longer holds the pinned commit")
    if dirty := worktree.git(copy.path, "status", "--porcelain", "--untracked-files=all").strip():
        changed.append(f"the audit worktree was edited:\n{dirty}")
    if changed:
        msg = "the audit changed shared Git state; nothing was published:\n" + "\n".join(changed)
        raise RuntimeError(msg)


def target(copy: disposable.Copy, ref: str) -> str:
    """Resolve the note-requested target in the clone, then move only the detached audit worktree."""
    commit = worktree.git(copy.source, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").strip()
    worktree.git(copy.path, "checkout", "--quiet", "--detach", commit)
    return commit
