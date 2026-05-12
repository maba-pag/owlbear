"""Git helpers for mcp-memory batch commit operations."""

from __future__ import annotations

import logging
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Sequence

_CURATION = "curation"
_REVIEW = "review"
_FRONTMATTER_PARTS = 3
_LOGGER = logging.getLogger(__name__)
_SESSION_TO_ACTOR = {
    _CURATION: "curator",
    _REVIEW: "reviewer",
}


def _git(repo_dir: Path, *args: str) -> str:
    """Run a git command and return stripped stdout."""
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        check=True,
        cwd=repo_dir,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    return result.stdout.strip()


def _state_from_file(file_path: Path) -> str | None:
    """Return entry state from frontmatter, or None for malformed files."""
    raw = file_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < _FRONTMATTER_PARTS:  # pragma: no cover
        return None
    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        _LOGGER.warning("Skipping malformed memory YAML in %s: %s", file_path, exc)
        return None
    if not isinstance(frontmatter, dict):  # pragma: no cover
        return None
    state = frontmatter.get("state")
    if isinstance(state, str):
        return state
    return None  # pragma: no cover


def commit_batch(memory_dir: Path, *, session_type: str) -> str:
    """Commit non-pending memory files in one batch and return commit SHA."""
    memory_dir = Path(memory_dir).resolve()
    if not memory_dir.exists():
        return ""

    if session_type not in _SESSION_TO_ACTOR:  # pragma: no cover
        msg = f"Unsupported session_type: {session_type}"
        raise ValueError(msg)

    repo_dir = Path(_git(memory_dir, "rev-parse", "--show-toplevel"))
    staged_paths: list[str] = []

    for file_path in sorted(memory_dir.glob("*.md")):
        state = _state_from_file(file_path)
        if state is None or state == "pending":
            continue
        rel_path = str(file_path.relative_to(repo_dir))
        _git(repo_dir, "add", "--", rel_path)
        staged_paths.append(rel_path)

    if not staged_paths:
        return ""

    diff_exit_code = subprocess.run(  # noqa: S603
        ["git", "diff", "--cached", "--quiet", "--", *staged_paths],  # noqa: S607
        cwd=repo_dir,
        stdin=subprocess.DEVNULL,
        check=False,
    ).returncode
    if diff_exit_code == 0:
        return ""

    actor = _SESSION_TO_ACTOR[session_type]
    message = f"chore: memory {session_type} batch (mcp-memory, {actor})"
    _git(repo_dir, "commit", "-m", message, "--", *staged_paths)
    return _git(repo_dir, "rev-parse", "HEAD")


def main(argv: Sequence[str] | None = None) -> int:
    """Run a state-aware memory batch commit from the command line."""
    parser = ArgumentParser(description="Commit reviewed OwlBear memory entries.")
    parser.add_argument("session_type", choices=sorted(_SESSION_TO_ACTOR))
    parser.add_argument(
        "--memory-dir",
        default=".owlbear/memory",
        help="memory markdown directory relative to the current workspace",
    )
    args = parser.parse_args(argv)

    try:
        commit_sha = commit_batch(Path(args.memory_dir), session_type=args.session_type)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        sys.stderr.write(f"error: {detail}\n")
        return exc.returncode or 1
    except ValueError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    if commit_sha:
        sys.stdout.write(f"{commit_sha}\n")
    else:
        sys.stdout.write("no memory changes to commit\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
