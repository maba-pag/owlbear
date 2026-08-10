"""Cockpit FastAPI dependency callables."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_memory.engine import MemoryEngine


def get_workspace_root() -> Path:
    """Return the active OwlBear workspace root."""
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.workspace_root


def get_memory_engine() -> MemoryEngine:
    """Return the MemoryEngine for the current request.

    In production, resolved from ``app.state.memory_engine`` via a lifespan
    handler in ``main.run``. In tests, replaced via
    ``app.dependency_overrides[get_memory_engine]``.
    """
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.memory_engine


def get_target_context() -> object:
    """Return the canonical Delivery Cockpit context."""
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.target_context


def get_ideas_path(workspace_root=Depends(get_workspace_root)) -> Path:  # noqa: ANN001, B008
    """Return the shared ideas markdown path in the active workspace."""
    return workspace_root / ".owlbear" / "ideas.md"
