"""OwlBear kanban engine package.

Exports the transport-free kanban engine, its public models, and the
dispatch selector (pick_dispatchable).
"""

from __future__ import annotations

from owlbear_kanban.dispatch import pick_dispatchable
from owlbear_kanban.engine import KanbanEngine, WorkSession
from owlbear_kanban.models import BoardConfig, Task, TaskSummary

__all__ = [
    "BoardConfig",
    "KanbanEngine",
    "Task",
    "TaskSummary",
    "WorkSession",
    "pick_dispatchable",
]
