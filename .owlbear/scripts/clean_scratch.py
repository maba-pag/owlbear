"""Clean up stale files from the .owlbear/scratch directory.

Removes files whose mtime is strictly older than 30 days.
Protected files (.gitkeep, .instructions.md) are never deleted.

Invocation
----------
    python .owlbear/scripts/clean_scratch.py [--scratch-dir PATH] [--dry-run]

Exit codes
----------
    0 — success (dry-run or normal run completed)
    1 — unexpected error
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_THIRTY_DAYS_SECONDS = 30 * 24 * 60 * 60
_PROTECTED_NAMES = frozenset({".gitkeep", ".instructions.md"})
_DEFAULT_SCRATCH = Path(__file__).parent.parent / "scratch"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean stale files from scratch directory.")
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=_DEFAULT_SCRATCH,
        help="Directory to clean (default: .owlbear/scratch).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without deleting anything.",
    )
    return parser.parse_args(argv)


def _is_protected(path: Path) -> bool:
    return path.name in _PROTECTED_NAMES


def _is_stale(path: Path, now: float) -> bool:
    """Return True if the file's mtime is strictly older than 30 days.

    Age is truncated to whole seconds so that a file set to exactly
    30 days ago (boundary case) is preserved, not deleted.
    """
    age = int(now - path.stat().st_mtime)
    return age > _THIRTY_DAYS_SECONDS


def run(scratch_dir: Path, *, dry_run: bool) -> int:
    """Execute the cleanup and print a summary. Returns exit code."""
    now = time.time()
    deleted = 0
    preserved = 0

    for file in sorted(scratch_dir.rglob("*")):
        if not file.is_file():
            continue
        if _is_protected(file):
            preserved += 1
            continue
        if _is_stale(file, now):
            if dry_run:
                print(f"[dry-run] would delete: {file.name}")
            else:
                file.unlink()
            deleted += 1
        else:
            preserved += 1

    if dry_run:
        print(f"Dry-run complete: {deleted} would be deleted, {preserved} preserved.")
    else:
        print(f"Deleted: {deleted}, Preserved: {preserved}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse cleanup options and remove stale files from the selected scratch directory."""
    args = _parse_args(argv)
    scratch_dir: Path = args.scratch_dir

    if not scratch_dir.exists():
        print(f"Error: scratch directory does not exist: {scratch_dir}", file=sys.stderr)
        return 1

    return run(scratch_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
