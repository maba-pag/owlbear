"""Cockpit FastAPI dependency callables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_kanban import KanbanEngine


def get_engine() -> KanbanEngine:
    """Return the KanbanEngine for the current request.

    In production, resolved from ``app.state.engine`` via a lifespan handler.
    In tests, replaced via ``app.dependency_overrides[get_engine]``.

    The import of ``owlbear_cockpit.main`` is deferred to call time to avoid
    a circular import (main → routes.read → deps → main at module load time).
    """
    import owlbear_cockpit.main as _main  # noqa: PLC0415

    return _main.app.state.engine
