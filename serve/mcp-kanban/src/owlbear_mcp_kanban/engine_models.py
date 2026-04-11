"""Engine-internal Pydantic models for the native kanban engine.

BoardConfig — schema for .owlbear/kanban/config.yml
Task        — re-exported from owlbear_kanban.models (canonical source)
TaskRecord  — backward-compatibility alias for Task

Task and TaskRecord are re-exported from owlbear_kanban.models so that
isinstance checks against instances returned by KanbanEngine work correctly
— there is a single class object rather than two identical-but-distinct types.

Scheduled for removal by #832 (migrate all callers to owlbear_kanban.models).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from owlbear_kanban.models import Task, TaskRecord

__all__ = [
    "BoardConfig",
    "BoardDefaults",
    "BoardInfo",
    "Task",
    "TaskRecord",
]


class BoardInfo(BaseModel):
    """Board identity sub-section of config.yml (board.name, etc.)."""

    model_config = ConfigDict(extra="allow")

    name: str


class BoardDefaults(BaseModel):
    """Default-values sub-section of config.yml.

    Unknown keys (e.g. ``class``) are preserved via extra='allow' so that
    round-trips do not lose non-standard vendor fields.
    """

    model_config = ConfigDict(extra="allow")

    status: str
    priority: str


class BoardConfig(BaseModel):
    """Schema for .owlbear/kanban/config.yml.

    All unknown/vendor fields (e.g. ``tui``, extra_vendor_field) are
    preserved through parse → dump round-trips via extra='allow'.
    """

    model_config = ConfigDict(extra="allow")

    version: int
    board: BoardInfo
    tasks_dir: str
    statuses: list[dict[str, Any]]
    priorities: list[str]
    defaults: BoardDefaults
    next_id: int
    claim_timeout: str
