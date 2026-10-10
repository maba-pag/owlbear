"""The Change worktree under the user data root, its install commands and its observed state (D4 §3.2)."""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.tools import Worktree

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.models import Profile

INSTALL_TIMEOUT = 900
_GIT = shutil.which("git") or "git"


def git(cwd: Path, *args: str) -> str:
    """Run one Git command and return its standard output unchanged."""
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [_GIT, *args], cwd=cwd, capture_output=True, text=True, check=True
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


@dataclass(frozen=True)
class Install:
    """One install command run for a package of the task."""

    package: str
    command: str
    exit_code: int
    tail: str


def installs(profile: Profile, scope: Sequence[str]) -> list[tuple[str, str]]:
    """Return ``(package, command)`` for each known install entry whose package holds a scope path."""
    found = []
    for key, entry in profile.entries.items():
        package = key.removeprefix("install:")
        if key == package or entry.state != "known":
            continue
        prefix = package.strip("/") + "/"
        if package in {"", "."} or any(p.strip("/") == package.strip("/") or p.startswith(prefix) for p in scope):
            found.append((package, entry.value))
    return found


def install(path: Path, profile: Profile, scope: Sequence[str]) -> list[Install]:
    """Run the install commands for the task's packages; stop at the first failure."""
    done = []
    for package, command in installs(profile, scope):
        try:
            run = subprocess.run(  # noqa: S603 - command from the confirmed profile, no shell.
                shlex.split(command),
                cwd=path / package,
                capture_output=True,
                text=True,
                timeout=INSTALL_TIMEOUT,
                check=False,
            )
            code, tail = run.returncode, (run.stdout + run.stderr)[-400:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, tail = -1, type(exc).__name__
        done.append(Install(package, command, code, tail))
        if code != 0:
            break
    return done


def observe(path: Path, target: str) -> Worktree:
    """Read the worktree's head, its base on *target*, uncommitted paths and paths changed since the base."""
    head = git(path, "rev-parse", "HEAD").strip()
    base = git(path, "merge-base", "HEAD", target).strip()
    status = git(path, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    changed = git(path, "diff", "--name-only", f"{base}..HEAD").splitlines()
    return Worktree(head=head, base=base, dirty=tuple(line[3:] for line in status), changed=tuple(changed))
