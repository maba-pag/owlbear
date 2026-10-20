"""Hide the OwlBear agent workspace from Git through the repository's local exclude file."""

from __future__ import annotations

import subprocess
from pathlib import Path

BLOCK_BEGIN = "# OwlBear agent workspace (setup/init.py) — begin"
BLOCK_END = "# OwlBear agent workspace (setup/init.py) — end"

# OwlBear runtime files below a project-owned .owlbear/ directory.
_RUNTIME_PATTERNS = (
    "scratch/*",
    "!scratch/.gitkeep",
    "!scratch/.instructions.md",
    "skills/pds-knowledge-*",
    "knowledge/*.db",
    "knowledge/vectors/",
    "memory/*.db",
    "**/*.db-shm",
    "**/*.db-wal",
    "delivery/runtime/*",
    "delivery/worktrees/",
    "worktrees/",
    "delivery-migrations/",
    "controller/",
    "**/.storage.lock",
    "kanban/activity.jsonl",
)


def _git(target_dir: Path, *arguments: str) -> subprocess.CompletedProcess[str] | None:
    """Run one read-only Git query in *target_dir*, or return None without Git."""
    try:
        return subprocess.run(  # noqa: S603 - fixed git subcommands with target-relative paths
            ["git", *arguments],  # noqa: S607
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None


def locate(target_dir: Path) -> tuple[Path, str] | None:
    """Return the local exclude file and the target's prefix in its repository."""
    completed = _git(target_dir, "rev-parse", "--show-prefix", "--git-path", "info/exclude")
    if completed is None or completed.returncode != 0:
        return None
    lines = completed.stdout.splitlines()
    if len(lines) != 2:  # noqa: PLR2004
        return None
    prefix, exclude = lines
    exclude_path = Path(exclude)
    return (exclude_path if exclude_path.is_absolute() else target_dir / exclude_path).resolve(), prefix


def tracked_paths(target_dir: Path, relatives: list[str]) -> set[str]:
    """Return which of *relatives* (posix, relative to the target) Git tracks."""
    if not relatives:
        return set()
    completed = _git(target_dir, "ls-files", "-z", "--", *relatives)
    if completed is None or completed.returncode != 0:
        return set()
    return {path for path in completed.stdout.split("\0") if path}


def exclude_lines(prefix: str, created_dirs: set[str], created_files: set[str]) -> list[str]:
    """Return anchored exclude patterns for the top-most created paths and runtime files."""
    created = {(path, True) for path in created_dirs} | {(path, False) for path in created_files}
    lines = [
        f"/{prefix}{path}/" if is_dir else f"/{prefix}{path}"
        for path, is_dir in sorted(created)
        if not any(parent.as_posix() in created_dirs for parent in Path(path).parents)
    ]
    if ".owlbear" not in created_dirs:
        lines.extend(_runtime_line(prefix, pattern) for pattern in _RUNTIME_PATTERNS)
    return lines


def _runtime_line(prefix: str, pattern: str) -> str:
    """Anchor one runtime pattern below the project's .owlbear/ directory."""
    negation, body = ("!", pattern[1:]) if pattern.startswith("!") else ("", pattern)
    return f"{negation}/{prefix}.owlbear/{body}"


def _split_block(text: str) -> tuple[str, list[str] | None, str]:
    """Split exclude text into before, the OwlBear block's lines (None if absent), and after."""
    lines = text.splitlines(keepends=True)
    stripped = [line.rstrip("\r\n") for line in lines]
    if BLOCK_BEGIN not in stripped:
        return text, None, ""
    start = stripped.index(BLOCK_BEGIN)
    end = stripped.index(BLOCK_END, start) if BLOCK_END in stripped[start:] else len(lines)
    return "".join(lines[:start]), stripped[start + 1 : end], "".join(lines[end + 1 :])


def write_block(exclude_path: Path, lines: list[str]) -> None:
    """Replace or append the one OwlBear block in the local exclude file."""
    current = exclude_path.read_text(encoding="utf-8") if exclude_path.is_file() else ""
    before, _, after = _split_block(current)
    rest = before + after
    if rest and not rest.endswith("\n"):
        rest += "\n"
    block = "".join(f"{line}\n" for line in (BLOCK_BEGIN, *lines, BLOCK_END)) if lines else ""
    updated = rest + block
    if updated != current:
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        exclude_path.write_text(updated, encoding="utf-8")


def remove_block(exclude_path: Path, recorded: list[str], *, dry_run: bool) -> str | None:
    """Remove the OwlBear block when it still holds *recorded*; return the action taken."""
    if not exclude_path.is_file():
        return None
    current = exclude_path.read_text(encoding="utf-8")
    before, block, after = _split_block(current)
    if block is None:
        return None
    if block != recorded:
        return "preserve"
    if dry_run:
        return "would remove"
    exclude_path.write_text(before + after, encoding="utf-8")
    return "removed"
