"""OwlBear kanban engine package.

Exports the transport-free kanban engine, its public models, error
classes, and the dispatch selector (pick_dispatchable).
"""

from __future__ import annotations

from owlbear_kanban.agent_view import AgentView
from owlbear_kanban.dispatch import pick_dispatchable
from owlbear_kanban.engine import KanbanEngine, WorkSession
from owlbear_kanban.errors import (
    ConcurrencyError,
    CorruptionError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import BoardConfig, Task, TaskSummary

__all__ = [
    "AgentView",
    "BoardConfig",
    "ConcurrencyError",
    "CorruptionError",
    "KanbanEngine",
    "NotFoundError",
    "Task",
    "TaskSummary",
    "ValidationError",
    "WorkSession",
    "pick_dispatchable",
]
