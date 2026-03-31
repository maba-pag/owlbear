"""Pydantic models for kanban-md task data at the MCP protocol boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KanbanTask(BaseModel):
    """Represents a single kanban task as returned by kanban-md --json."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Required fields
    id: int
    title: str
    status: str
    priority: str
    created: str
    updated: str
    class_: str = Field(alias="class")

    # Optional fields
    started: str | None = None
    completed: str | None = None
    assignee: str | None = None
    claimed_by: str | None = None
    claimed_at: str | None = None
    tags: list[str] = Field(default_factory=list)
    due: str | None = None
    estimate: str | None = None
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    body: str | None = None
    file: str | None = None
