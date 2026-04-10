"""Engine-internal Pydantic models for the native kanban engine.

BoardConfig — schema for .owlbear/kanban/config.yml
TaskRecord  — schema for task file frontmatter + markdown body

These are distinct from the MCP-boundary KanbanTask in models.py.
Timestamps are stored as plain strings to avoid Go nanosecond → Python
microsecond precision drift on round-trips.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class TaskRecord(BaseModel):
    """Schema for a kanban task file — frontmatter fields plus markdown body.

    Timestamp fields (created, updated, claimed_at) are stored as ``str``
    to avoid Go 7-digit nanosecond → Python 6-digit microsecond truncation.

    Unknown YAML frontmatter keys (e.g. ``class``, ``started``,
    ``completed``) are preserved via extra='allow'.
    """

    model_config = ConfigDict(extra="allow")

    # Required fields
    id: int
    title: str
    status: str
    priority: str
    created: str
    updated: str
    body: str = ""

    # Optional fields
    tags: list[str] = Field(default_factory=list)
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    claimed_by: str | None = None
    claimed_at: str | None = None
