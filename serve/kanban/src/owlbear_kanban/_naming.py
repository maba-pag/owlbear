"""Path containment safety for native authority files."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def validate_path_containment(tasks_dir: Path, path: Path) -> None:
    """Raise if *path* is not safely contained within *tasks_dir*."""
    if "\x00" in str(path):
        msg = "Path contains null byte"
        raise ValueError(msg)

    resolved_dir = tasks_dir.resolve()
    resolved_path = path.resolve()

    if resolved_path == resolved_dir:
        msg = f"Path must be a file inside tasks_dir, not tasks_dir itself: {path}"
        raise ValueError(msg)

    try:
        resolved_path.relative_to(resolved_dir)
    except ValueError:
        msg = f"Path is outside tasks_dir '{tasks_dir}': {path}"
        raise PermissionError(msg) from None
