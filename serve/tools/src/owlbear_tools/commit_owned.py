"""Commit explicitly owned paths without disturbing an existing Git index."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class CommitOwnedError(RuntimeError):
    """Raised when a scoped commit cannot be completed safely."""

    def __init__(self, detail: str) -> None:
        """Format a failure detail for the command-line caller."""
        super().__init__(detail)


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
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


def commit_owned_paths(*, cwd: Path, message: str, paths: Sequence[str]) -> str:
    """Stage and commit only owned paths, restoring their index state on failure."""
    if not message.strip():
        detail = "A commit message is required."
        raise CommitOwnedError(detail)

    owned_paths = _relative_paths(cwd, paths)
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
    parser.add_argument("paths", nargs="+", help="Workspace-relative task-owned paths")
    args = parser.parse_args()

    try:
        commit = commit_owned_paths(cwd=Path.cwd(), message=args.message, paths=args.paths)
    except CommitOwnedError as error:
        sys.stderr.write(f"commit-owned: {error}\n")
        raise SystemExit(1) from error
    else:
        sys.stdout.write(f"Committed {commit}\n")


if __name__ == "__main__":
    main()
