"""Advisory scan for unresolved documentation TODO markers."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from owlbear_tools.commands import command_footer

_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "dist",
        "__pycache__",
        "build",
        "megalinter-reports",
        "test-results",
        "scratch",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "coverage",
        "htmlcov",
        "playwright-report",
    }
)
_EXCLUDED_RELATIVE_DIRS = frozenset(
    {
        ".owlbear/completed",
        ".owlbear/delivery/packages",
        ".owlbear/delivery/runtime",
        ".owlbear/kanban/archive",
        ".owlbear/legacy",
        ".owlbear/memory",
        ".owlbear/research",
        ".owlbear/sources",
        ".owlbear/target",
        "serve/cockpit/web/public/porsche-design-system",
    }
)
_TODO_RE = re.compile(r"^> \*\*TODO:\*\*")
_TODO_EXAMPLE_RE = re.compile(r"^> \*\*TODO:\*\* \{category\} — \{description\} \[#\{[^{}]+\}\]$")


def run_todo(root: Path = Path()) -> int:
    """Scan a workspace for concrete TODO markers and print an advisory report."""
    hits: list[str] = []
    _walk_todo(root, hits)
    if hits:
        print(f"\033[1;33m\u26a0 {len(hits)} TODO marker(s):\033[0m")  # noqa: T201
        for hit in hits:
            print(f"  {hit}")  # noqa: T201
    else:
        print("\033[32m\u2713 No TODO markers found\033[0m")  # noqa: T201
    return 0


def todo_check() -> None:
    """Scan for concrete TODO markers as an advisory check."""
    parser = argparse.ArgumentParser(prog="todo")
    parser.parse_args()
    rc = run_todo()
    if not os.environ.get("PRE_COMMIT"):
        sys.stderr.write(command_footer() + "\n")
    raise SystemExit(rc)


def _walk_todo(root: Path, hits: list[str]) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            directory
            for directory in dirnames
            if (
                directory not in _SKIP_DIRS
                and not directory.endswith(".egg-info")
                and not _is_nested_repository(current / directory)
                and not (current / directory).is_symlink()
                and not _is_excluded_path(current / directory, root)
            )
        ]
        for filename in filenames:
            path = current / filename
            if not path.is_symlink() and not _is_excluded_path(path, root):
                _scan_todo(str(path), hits)


def _is_nested_repository(path: Path) -> bool:
    """Return whether a child directory is a separately rooted Git checkout."""
    return (path / ".git").is_file() or (path / ".git").is_dir()


def _is_excluded_path(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return False
    return any(relative == excluded or relative.startswith(f"{excluded}/") for excluded in _EXCLUDED_RELATIVE_DIRS)


def _scan_todo(path: str, hits: list[str]) -> None:
    try:
        file_hits: list[str] = []
        with Path(path).open("rb") as handle:
            for line_number, raw_line in enumerate(handle, 1):
                if b"\0" in raw_line:
                    return
                marker = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if _TODO_RE.match(marker) and not _TODO_EXAMPLE_RE.fullmatch(marker):
                    file_hits.append(f"{path}:{line_number}: {marker}")
        hits.extend(file_hits)
    except OSError:
        pass
