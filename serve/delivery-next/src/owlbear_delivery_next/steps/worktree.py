"""The Change worktree under the user data root, its packages' install commands and its observed state (D4 §3.2)."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.tools import Worktree

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.models import Profile

_GIT = shutil.which("git") or "git"


def git(cwd: Path, *args: str) -> str:
    """Run one Git command, bounded so a hung Git cannot stall a step, and return its standard output."""
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [_GIT, *args], cwd=cwd, capture_output=True, text=True, check=True, timeout=60
    ).stdout


def data_root() -> Path:
    """Return the one user data root that holds every worktree, so folder trust is granted once (P8)."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "OwlBear" / "worktrees"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "owlbear" / "worktrees"


def path_for(common_dir: Path, slug: str) -> Path:
    """Return the worktree path, keyed by repository name and a short hash of the common git directory."""
    key = hashlib.sha256(str(common_dir).encode()).hexdigest()[:8]
    return data_root() / f"{common_dir.parent.name}-{key}" / slug


def ensure(repo: Path, common_dir: Path, slug: str, branch: str, target: str) -> Path:
    """Return the Change worktree, creating it and its branch from *target* when absent."""
    path = path_for(common_dir, slug)
    if (path / ".git").exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "prune")
    exists = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [_GIT, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=repo, capture_output=True, check=False
    )
    args = [str(path), branch] if exists.returncode == 0 else ["-b", branch, str(path), target]
    git(repo, "worktree", "add", *args)
    return path


def allowed(profile: Profile, kind: str) -> list[str]:
    """Return the profile's extra shell commands for one step kind; for ``check`` they are the launch commands."""
    extra = profile.entries.get(f"allow:{kind}")
    return extra.value.split("\n") if extra else []


def installs(profile: Profile, scope: Sequence[str]) -> list[tuple[str, str]]:
    """Return ``(package, command)`` per known install entry holding a scope path; the Builder runs them (DR3)."""
    found = []
    for key, entry in profile.entries.items():
        package = key.removeprefix("install:")
        if key == package or entry.state != "known":
            continue
        prefix = package.strip("/") + "/"
        if package in {"", "."} or any(p.strip("/") == package.strip("/") or p.startswith(prefix) for p in scope):
            found.append((package, entry.value))
    return found


def observe(path: Path, target: str) -> Worktree:
    """Read the worktree's head, its base on *target*, uncommitted paths and paths changed since the base."""
    head = git(path, "rev-parse", "HEAD").strip()
    base = git(path, "merge-base", "HEAD", target).strip()
    status = git(path, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    changed = git(path, "diff", "--name-only", f"{base}..HEAD").splitlines()
    return Worktree(head=head, base=base, dirty=tuple(line[3:] for line in status), changed=tuple(changed))


def fingerprints(path: Path, paths: Sequence[str]) -> dict[str, str]:
    """Return the object id at HEAD of each existing path, the review input that voids a verdict when it changes."""
    inside = [p for p in paths[:200] if (path / p).resolve().is_relative_to(path.resolve())]
    lines = git(path, "ls-tree", "HEAD", "--", *inside).splitlines() if inside else []
    return {line.split("\t", 1)[1]: line.split()[2] for line in lines}
