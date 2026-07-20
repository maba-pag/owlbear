"""Commit explicitly owned paths without disturbing an existing Git index."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class CommitOwnedError(RuntimeError):
    """Raised when a scoped commit cannot be completed safely."""

    def __init__(self, detail: str) -> None:
        """Format a failure detail for the command-line caller."""
        super().__init__(detail)


def _git(
    cwd: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
        env=env,
        input=input_text,
    )


def _relative_paths(cwd: Path, paths: Sequence[str]) -> list[str]:
    if not paths:
        detail = "At least one owned path is required."
        raise CommitOwnedError(detail)

    relative_paths: list[str] = []
    for path in paths:
        candidate = Path(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            detail = f"Paths must be workspace-relative: {path}"
            raise CommitOwnedError(detail)
        resolved = (cwd / candidate).resolve()
        try:
            resolved.relative_to(cwd.resolve())
        except ValueError as error:
            detail = f"Path escapes the workspace: {path}"
            raise CommitOwnedError(detail) from error
        relative_paths.append(candidate.as_posix())
    return relative_paths


def _staged_paths(cwd: Path, paths: Sequence[str]) -> list[str]:
    result = _git(cwd, "diff", "--cached", "--name-only", "--", *paths)
    return [path for path in result.stdout.splitlines() if path]


def _commit_staged_paths(*, cwd: Path, message: str, owned_paths: list[str]) -> str:
    initially_staged = _staged_paths(cwd, owned_paths)
    missing = sorted(set(owned_paths) - set(initially_staged))
    if missing:
        joined = ", ".join(missing)
        detail = f"Recovery paths must already have staged changes: {joined}"
        raise CommitOwnedError(detail)

    patch = _git(cwd, "diff", "--cached", "--binary", "--", *owned_paths).stdout
    fd, temporary_index = tempfile.mkstemp(prefix="commit-owned-index-")
    os.close(fd)
    Path(temporary_index).unlink()
    recovery_env = {**os.environ, "GIT_INDEX_FILE": temporary_index}
    try:
        _git(cwd, "read-tree", "HEAD", env=recovery_env)
        _git(cwd, "apply", "--cached", "--binary", "-", env=recovery_env, input_text=patch)
        try:
            _git(cwd, "commit", "-m", message, env=recovery_env)
        except subprocess.CalledProcessError as error:
            details = error.stderr.strip() or error.stdout.strip() or "git commit failed"
            detail = f"Staged recovery commit failed; index was preserved: {details}"
            raise CommitOwnedError(detail) from error
    finally:
        Path(temporary_index).unlink(missing_ok=True)

    remaining = _staged_paths(cwd, owned_paths)
    if remaining:
        joined = ", ".join(remaining)
        detail = f"Recovery commit succeeded but owned paths remain staged: {joined}"
        raise CommitOwnedError(detail)
    return _git(cwd, "rev-parse", "HEAD").stdout.strip()


def commit_owned_paths(*, cwd: Path, message: str, paths: Sequence[str], staged: bool = False) -> str:
    """Stage and commit only owned paths, restoring their index state on failure."""
    if not message.strip():
        detail = "A commit message is required."
        raise CommitOwnedError(detail)

    owned_paths = _relative_paths(cwd, paths)
    if staged:
        return _commit_staged_paths(cwd=cwd, message=message, owned_paths=owned_paths)

    initially_staged = _staged_paths(cwd, owned_paths)
    if initially_staged:
        joined = ", ".join(initially_staged)
        detail = f"Owned paths already have staged changes: {joined}"
        raise CommitOwnedError(detail)

    _git(cwd, "add", "--", *owned_paths)
    staged = _staged_paths(cwd, owned_paths)
    if not staged:
        detail = "None of the owned paths has changes to commit."
        raise CommitOwnedError(detail)

    try:
        _git(cwd, "commit", "--only", "-m", message, "--", *owned_paths)
    except subprocess.CalledProcessError as error:
        _git(cwd, "reset", "HEAD", "--", *owned_paths)
        details = error.stderr.strip() or error.stdout.strip() or "git commit failed"
        detail = f"Commit failed; owned paths were unstaged: {details}"
        raise CommitOwnedError(detail) from error

    remaining = _staged_paths(cwd, owned_paths)
    if remaining:
        joined = ", ".join(remaining)
        detail = f"Commit succeeded but owned paths remain staged: {joined}"
        raise CommitOwnedError(detail)
    return _git(cwd, "rev-parse", "HEAD").stdout.strip()


def main() -> None:
    """Run the ``commit-owned`` command."""
    parser = argparse.ArgumentParser(
        description="Commit explicit task-owned paths without disturbing unrelated staged changes."
    )
    parser.add_argument("-m", "--message", required=True, help="Commit message")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Recovery mode: commit the existing staged snapshot of every named path",
    )
    parser.add_argument("paths", nargs="+", help="Workspace-relative task-owned paths")
    args = parser.parse_args()

    try:
        commit = commit_owned_paths(cwd=Path.cwd(), message=args.message, paths=args.paths, staged=args.staged)
    except CommitOwnedError as error:
        sys.stderr.write(f"commit-owned: {error}\n")
        raise SystemExit(1) from error
    else:
        sys.stdout.write(f"Committed {commit}\n")


if __name__ == "__main__":
    main()
