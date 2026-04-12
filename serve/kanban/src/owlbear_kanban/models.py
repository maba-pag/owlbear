"""Engine-internal Pydantic models for the native kanban engine.

BoardConfig  — schema for .owlbear/kanban/config.yml
Task         — schema for task file frontmatter + markdown body
TaskSummary  — lightweight projection for list_tasks() results

Timestamps are stored as plain strings to avoid Go nanosecond → Python
microsecond precision drift on round-trips.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class Task(BaseModel):
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



class TaskSummary(BaseModel):
    """Lightweight task summary for list operations.

    Excludes ``body``, ``claimed_by``, ``created``, and ``updated`` from the
    full :class:`Task` schema.  ``claimed_by`` is coerced to a boolean
    ``claimed`` field; temporal fields are silently dropped via
    ``extra="ignore"``.  Dict-style read access (``summary["field"]``) is
    supported for MCP serialisation consumers.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    status: str
    priority: str
    tags: list[str] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    claimed: bool = False
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_claimed(cls, data: object) -> object:
        """Convert claimed_by string to a boolean claimed flag."""
        if isinstance(data, dict) and "claimed_by" in data:
            data = dict(data)
            data["claimed"] = data.pop("claimed_by") is not None
        return data

    def __getitem__(self, key: str) -> object:
        """Allow dict-style read access for MCP serialisation consumers."""
        return getattr(self, key)
