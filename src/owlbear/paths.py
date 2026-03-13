"""Shared path-sandboxing utility.

This is a **leaf module** — it must not import from ``owlbear.core``,
``owlbear.tools``, ``owlbear.memory``, or ``owlbear.agents``.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["sandbox_path"]


def sandbox_path(root: Path, user_path: str | Path) -> Path:
    """Resolve *user_path* against *root* with a traversal guard.

    Returns the resolved absolute :class:`~pathlib.Path`.

    Raises:
        PermissionError: If *user_path* contains null bytes or resolves
            outside *root*.
    """
    raw = str(user_path)

    if "\x00" in raw:
        msg = f"Path outside workspace: {raw!r}"
        raise PermissionError(msg)

    candidate = Path(raw)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()

    if not resolved.is_relative_to(root.resolve()):
        msg = f"Path outside workspace: {raw}"
        raise PermissionError(msg)

    return resolved
