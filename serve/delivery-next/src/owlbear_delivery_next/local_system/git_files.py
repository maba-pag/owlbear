"""Git facts of a local clone: one bounded command, the common git directory, tracked or not, local excludes."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Protocol

from owlbear_delivery_next.git.command_failure import failed, failure

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class Probe(Protocol):
    """One bounded command."""

    def __call__(self, argv: list[str], env: Mapping[str, str] | None = None, /) -> tuple[int, str]:
        """Its exit code and what it printed, or its whole failure; *env* replaces the process's environment."""


class GitInspectionError(RuntimeError):
    """Git could not establish whether a local file is tracked."""


def probe_in(cwd: Path) -> Probe:
    """Run one command in *cwd*, bounded: what it printed, or its whole failure; a missing program is exit 127."""

    def run(argv: list[str], env: Mapping[str, str] | None = None, /) -> tuple[int, str]:
        try:
            done = subprocess.run(  # noqa: S603
                argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=30, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, failure(exc)
        return done.returncode, failed(done) if done.returncode else (done.stdout + done.stderr).strip()

    return run


def git_common_dir(cwd: Path) -> Path:
    """Return the clone's common git directory; the same from every worktree."""
    git = shutil.which("git") or "git"
    out = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [git, "rev-parse", "--git-common-dir"], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()
    return (cwd / out).resolve()


def untracked(repo: Path, path: Path) -> bool:
    """Whether git reports *path* as not tracked; failed inspection never grants a write."""
    rel = path.relative_to(repo).as_posix()
    code, said = probe_in(repo)(["git", "ls-files", "--error-unmatch", "--", rel])
    if code not in {0, 1}:
        msg = f"{path} could not be checked for tracking in {repo}: {said}"
        raise GitInspectionError(msg)
    return code == 1


def exclude(repo: Path, path: Path) -> None:
    """Add *path* to the clone's local ``info/exclude`` once, keeping its other lines."""
    entry = "/" + path.relative_to(repo).as_posix()
    file = git_common_dir(repo) / "info" / "exclude"
    lines = file.read_text().splitlines() if file.exists() else []
    if entry not in lines:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("\n".join([*lines, entry]) + "\n")
