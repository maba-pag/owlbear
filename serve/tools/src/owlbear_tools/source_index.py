"""Shared filesystem and rendering helpers for source indexes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

EXCLUDED_PATHS: frozenset[Path] = frozenset(
    Path(path)
    for path in [
        ".owlbear/scratch",
        ".owlbear/research",
        ".owlbear/kanban",
        ".owlbear/briefs",
        ".owlbear/sources",
        ".owlbear/memory",
        "store",
        "tests",
        "megalinter-reports",
    ]
)

EXCLUDED_NAMES: frozenset[str] = frozenset(
    {
        "node_modules",
        ".git",
        ".venv",
        ".pytest_cache",
        "__pycache__",
        "coverage",
        "dist",
        "build",
        "generated",
        "public",
        "tests",
        "__tests__",
        "vendor",
    }
)

_TEST_MARKERS: tuple[str, ...] = (".test.", ".spec.")


def _is_excluded_dir(path: Path, root: Path) -> bool:
    """Return whether a directory is excluded from generated indexes."""
    try:
        relative = path.relative_to(root)
    except ValueError:  # pragma: no cover - os.walk paths always descend from root
        return False
    return relative in EXCLUDED_PATHS or any(part in EXCLUDED_NAMES for part in relative.parts)


def collect_sources(root: Path, suffixes: Collection[str]) -> list[Path]:
    """Collect matching source files under *root* in deterministic order."""
    sources: list[Path] = []
    for dirpath_text, dirnames, filenames in os.walk(root, topdown=True):
        dirpath = Path(dirpath_text)
        dirnames[:] = sorted(name for name in dirnames if not _is_excluded_dir(dirpath / name, root))
        sources.extend(
            dirpath / name
            for name in sorted(filenames)
            if Path(name).suffix in suffixes
            and not any(marker in name for marker in _TEST_MARKERS)
            and not name.startswith("test_")
            and not Path(name).stem.endswith("_test")
        )
    return sources


def clean_line(text: str) -> str:
    """Collapse source text into one stable Markdown-friendly line."""
    return " ".join(text.strip().rstrip(";{").split())
