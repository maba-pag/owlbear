"""Hide the OwlBear agent workspace from Git through the repository's local exclude file."""

from __future__ import annotations

import subprocess
from pathlib import Path

BLOCK_BEGIN = "# OwlBear agent workspace (setup/init.py) /{scope} — begin"
BLOCK_END = "# OwlBear agent workspace (setup/init.py) /{scope} — end"
OWNED = ".owlbear"  # the only created directory excluded whole: everything below it is OwlBear's
_SPECIAL = set("\\*?[]")

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


def markers(prefix: str) -> tuple[str, str]:
    """Return the begin and end lines of the block of the installation at *prefix*."""
    return BLOCK_BEGIN.format(scope=prefix), BLOCK_END.format(scope=prefix)


def literal(path: str) -> str:
    """Escape a literal path so Git's ignore syntax reads no wildcard, comment or negation in it."""
    escaped = "".join(f"\\{char}" if char in _SPECIAL else char for char in path)
    if escaped[:1] in {"#", "!"}:
        escaped = f"\\{escaped}"
    stripped = escaped.rstrip(" ")
    return stripped + "\\ " * (len(escaped) - len(stripped))


def exclude_lines(prefix: str, created_dirs: set[str], created_files: set[str]) -> list[str]:
    """Return anchored exclude patterns: each created file, `.owlbear/` whole when created, runtime files."""
    base = literal(prefix)
    owned = OWNED in created_dirs
    lines = [f"/{base}{OWNED}/"] if owned else []
    lines += [
        f"/{base}{literal(path)}"
        for path in sorted(created_files)
        if not (owned and (path == OWNED or path.startswith(f"{OWNED}/")))
    ]
    if not owned:
        lines.extend(_runtime_line(base, pattern) for pattern in _RUNTIME_PATTERNS)
    return lines


def _runtime_line(base: str, pattern: str) -> str:
    """Anchor one runtime pattern below the project's .owlbear/ directory."""
    negation, body = ("!", pattern[1:]) if pattern.startswith("!") else ("", pattern)
    return f"{negation}/{base}{OWNED}/{body}"


def _split_block(text: str, prefix: str) -> tuple[str, list[str] | None, str]:
    """Split exclude text into before, this installation's block lines (None if absent), and after."""
    begin, end_marker = markers(prefix)
    lines = text.splitlines(keepends=True)
    stripped = [line.rstrip("\r\n") for line in lines]
    if begin not in stripped:
        return text, None, ""
    start = stripped.index(begin)
    end = stripped.index(end_marker, start) if end_marker in stripped[start:] else len(lines)
    return "".join(lines[:start]), stripped[start + 1 : end], "".join(lines[end + 1 :])


def write_block(exclude_path: Path, prefix: str, lines: list[str], previous: list[str] | None) -> None:
    """Replace or append this installation's block, keeping lines the owner added to it since *previous*."""
    current = exclude_path.read_text(encoding="utf-8") if exclude_path.is_file() else ""
    before, existing, after = _split_block(current, prefix)
    added = [line for line in existing or [] if line not in (previous or lines) and line not in lines]
    rest = before + after
    if rest and not rest.endswith("\n"):
        rest += "\n"
    body = [*lines, *added]
    block = "".join(f"{line}\n" for line in (markers(prefix)[0], *body, markers(prefix)[1])) if body else ""
    updated = rest + block
    if updated != current:
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        exclude_path.write_text(updated, encoding="utf-8")


def remove_block(exclude_path: Path, prefix: str, recorded: list[str], *, dry_run: bool) -> str | None:
    """Remove this installation's block when it still holds *recorded*; return the action taken."""
    if not exclude_path.is_file():
        return None
    current = exclude_path.read_text(encoding="utf-8")
    before, block, after = _split_block(current, prefix)
    if block is None:
        return None
    if block != recorded:
        return "preserve"
    if dry_run:
        return "would remove"
    exclude_path.write_text(before + after, encoding="utf-8")
    return "removed"
