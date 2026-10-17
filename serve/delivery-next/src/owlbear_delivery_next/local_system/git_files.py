"""Git facts of a local clone: one bounded command, the common git directory, tracked or not, local excludes."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

type Probe = Callable[[list[str]], tuple[int, str]]


def probe_in(cwd: Path) -> Probe:
    """Run one command in *cwd*, bounded; a missing program is exit 127."""

    def run(argv: list[str]) -> tuple[int, str]:
        try:
            done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=30, check=False)  # noqa: S603
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)
        return done.returncode, (done.stdout + done.stderr).strip()

    return run


def git_common_dir(cwd: Path) -> Path:
    """Return the clone's common git directory; the same from every worktree."""
    git = shutil.which("git") or "git"
    out = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [git, "rev-parse", "--git-common-dir"], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()
    return (cwd / out).resolve()


def untracked(repo: Path, path: Path) -> bool:
    """Whether git reports *path* as not tracked; any other answer counts as tracked."""
    rel = path.relative_to(repo).as_posix()
    return probe_in(repo)(["git", "ls-files", "--error-unmatch", "--", rel])[0] == 1


def exclude(repo: Path, path: Path) -> None:
    """Add *path* to the clone's local ``info/exclude`` once, keeping its other lines."""
    entry = "/" + path.relative_to(repo).as_posix()
    file = git_common_dir(repo) / "info" / "exclude"
    lines = file.read_text().splitlines() if file.exists() else []
    if entry not in lines:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("\n".join([*lines, entry]) + "\n")
