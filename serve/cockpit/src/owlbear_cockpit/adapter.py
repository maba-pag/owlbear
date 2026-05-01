"""Cockpit engine adapter — thin wrappers over allowed KanbanEngine read methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from owlbear_kanban import KanbanEngine

__all__ = ["valid_transitions"]


def valid_transitions(engine: KanbanEngine, status: str) -> Any:  # noqa: ANN401
    """Delegate to KanbanEngine.valid_transitions."""
    return engine.valid_transitions(status)
