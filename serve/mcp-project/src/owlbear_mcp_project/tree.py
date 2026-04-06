"""Directory tree helper for the mcp-project package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["build_tree"]

_DEFAULT_EXCLUDE: frozenset[str] = frozenset({
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    ".mypy_cache",
})


def _iter_children(
    path: Path, hidden: frozenset[str],
) -> list[Path]:
    """Return sorted, filtered children of *path*."""
    try:
        items = sorted(path.iterdir(), key=lambda p: p.name)
    except (PermissionError, OSError):
        return []
    return [item for item in items if item.name not in hidden]


def build_tree(
    root: Path,
    max_depth: int = 3,
    exclude: set[str] | None = None,
) -> str:
    """Return an indented directory tree string.

    Args:
        root: Directory to walk.
        max_depth: Maximum depth of traversal. Content inside directories
            deeper than *max_depth* is excluded.
        exclude: Set of directory/file names to hide. ``None`` means no
            exclusions.
    """
    hidden = frozenset(exclude) if exclude is not None else frozenset()
    lines: list[str] = []

    def _walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        for item in _iter_children(path, hidden):
            indent = "  " * (depth - 1)
            suffix = "/" if item.is_dir() else ""
            lines.append(f"{indent}{item.name}{suffix}")
            if item.is_dir():
                if depth < max_depth:
                    _walk(item, depth + 1)
                elif max_depth > 1:
                    _append_leaf_files(item, depth + 1, hidden, lines)

    _walk(root, depth=1)
    return "\n".join(lines)


def _append_leaf_files(
    path: Path,
    depth: int,
    hidden: frozenset[str],
    lines: list[str],
) -> None:
    """Append only non-directory children of *path* to *lines*."""
    for item in _iter_children(path, hidden):
        if not item.is_dir():
            indent = "  " * (depth - 1)
            lines.append(f"{indent}{item.name}")
