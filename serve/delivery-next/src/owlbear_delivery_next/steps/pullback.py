"""Pull-back: fast-forward the local target branch to the merged remote one, never touching local work."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.git.remote_git import run_remote_git
from owlbear_delivery_next.models import Pullback
from owlbear_delivery_next.steps import engine, worktree

if TYPE_CHECKING:
    from datetime import datetime

_IN_PROGRESS = ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD")


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=path, capture_output=True, text=True, check=False, timeout=120
    )


def _first(stderr: str | bytes) -> str:
    text = stderr.decode(errors="replace") if isinstance(stderr, bytes) else stderr
    return next((line.strip() for line in text.splitlines() if line.strip()), "git failed")


def checked_out(repo: Path, target: str) -> str | None:
    """The worktree that has *target* checked out, from ``git worktree list --porcelain``."""
    path = None
    for line in _git(repo, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif line == f"branch refs/heads/{target}":
            return path
    return None


def _rev(path: Path, ref: str) -> str | None:
    done = _git(path, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return done.stdout.strip() if done.returncode == 0 else None


def _submodules(path: Path, old: str | None, new: str | None) -> bool:
    """Whether a gitlink (mode 160000) changes between the local and the remote target."""
    if not old or not new or old == new:
        return False
    raw = _git(path, "diff", "--raw", "--no-renames", old, new).stdout.splitlines()
    return any("160000" in line.split("\t", 1)[0].split()[:2] for line in raw)


def _busy(wt: Path) -> str | None:
    """Why the checked-out worktree cannot be fast-forwarded safely, or None."""
    for name in _IN_PROGRESS:
        rel = _git(wt, "rev-parse", "--git-path", name).stdout.strip()
        if rel and (wt / rel).exists():
            return "in progress"
    if _git(wt, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        return "dirty"
    return None


def _update(repo: Path, target: str, wt: str | None) -> tuple[str, str]:
    """Bring local *target* up to ``origin/<target>``: ``(state, reason)``."""
    remote = f"origin/{target}"
    if wt is None:
        if _rev(repo, f"refs/heads/{target}") is None:
            return "updated", f"no local {target} branch; origin/{target} updated"
        done = run_remote_git(repo, ("fetch", "--quiet", "--no-tags", "origin", f"{target}:{target}"), kind="read")
        return ("updated", "") if done.returncode == 0 else ("behind", _first(done.stderr))
    path = Path(wt)
    if reason := _busy(path):
        return "behind", reason
    if not engine.contains(path, "HEAD", remote):
        return "behind", "diverged"
    if engine.contains(path, remote, "HEAD"):
        return "updated", "already up to date"
    done = _git(path, "merge", "--ff-only", "--no-autostash", "--no-overwrite-ignore", remote)
    return ("updated", "") if done.returncode == 0 else ("behind", _first(done.stderr))


def run(repo: Path, target: str, now: datetime) -> Pullback:
    """Fetch the target and fast-forward the local branch; never pull, stash, reset or merge with a commit."""
    try:
        engine.fetch(repo, target)
    except engine.RemoteGitFailed as exc:
        return Pullback(state="behind", reason=f"local {target} is behind: {_first(str(exc))}", at=now)
    wt = checked_out(repo, target)
    old, new = _rev(repo, f"refs/heads/{target}"), _rev(repo, f"origin/{target}")
    state, why = _update(repo, target, wt)
    if _submodules(repo, old, new):
        why = f"{why}; submodules changed" if why else "submodules changed"
    reason = f"local {target} is behind: {why}" if state == "behind" else why
    return Pullback(state=state, reason=reason, worktree=wt or "", at=now)
