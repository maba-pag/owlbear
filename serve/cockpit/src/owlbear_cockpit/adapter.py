"""Cockpit engine adapter — thin wrappers over allowed KanbanEngine read methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from owlbear_kanban import KanbanEngine

__all__ = ["board_config", "list_sessions", "list_tasks", "show_task", "valid_transitions"]


def list_tasks(engine: KanbanEngine, **kwargs: Any) -> Any:  # noqa: ANN401
    """Delegate to KanbanEngine.list_tasks."""
    return engine.list_tasks(**kwargs)


def show_task(engine: KanbanEngine, task_id: str) -> Any:  # noqa: ANN401
    """Delegate to KanbanEngine.show_task."""
    return engine.show_task(task_id)


def board_config(engine: KanbanEngine) -> Any:  # noqa: ANN401
    """Delegate to KanbanEngine.board_config."""
    return engine.board_config()


def valid_transitions(engine: KanbanEngine, status: str) -> Any:  # noqa: ANN401
    """Delegate to KanbanEngine.valid_transitions."""
    return engine.valid_transitions(status)


def list_sessions(engine: KanbanEngine, **kwargs: Any) -> Any:  # noqa: ANN401
    """Delegate to KanbanEngine.list_sessions."""
    return engine.list_sessions(**kwargs)
