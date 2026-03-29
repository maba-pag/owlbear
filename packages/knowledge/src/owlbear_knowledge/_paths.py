"""Workspace path sandboxing utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def sandbox_path(root: Path, path: Path | str) -> Path:
    """Resolve *path* safely under *root*, rejecting escape attempts.

    Args:
        root: The directory that all resolved paths must remain within.
        path: A relative or absolute path to resolve.

    Returns:
        The resolved absolute path.

    Raises:
        PermissionError: If *path* contains a null byte or resolves outside *root*.
    """
    path_str = str(path)
    if "\x00" in path_str:
        msg = f"Path contains null byte: {path!r}"
        raise PermissionError(msg)

    resolved = (root / path).resolve()
    root_resolved = root.resolve()

    if not str(resolved).startswith(str(root_resolved)):
        msg = f"Path {path!r} resolves outside root {root!r}: {resolved}"
        raise PermissionError(msg)

    return resolved
