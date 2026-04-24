"""Pydantic response models for the cockpit read API."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TaskSummaryOut(BaseModel):
    """Summary projection of a task for list endpoints."""

    id: int
    title: str
    status: str
    priority: str
    tags: list[str] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    claimed: bool = False


class TaskDetailOut(BaseModel):
    """Full task detail for the single-task endpoint."""

    id: int
    title: str
    status: str
    priority: str
    body: str = ""
    updated: str
    created: str
    tags: list[str] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
    claimed: bool = False
    claimed_by: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_claimed(cls, data: object) -> object:
        """Derive claimed bool from claimed_at field."""
        if isinstance(data, dict):
            data = dict(data)
            claimed_at = data.get("claimed_at")
            data["claimed"] = claimed_at is not None
        return data


class BoardOut(BaseModel):
    """Board configuration response model."""

    statuses: list[dict]
    priorities: list[str]
    valid_transitions: dict[str, list[str]]


class SessionOut(BaseModel):
    """Work session response model."""

    task_id: int
    state: str
    agent: str = ""
    started_at: str = ""
    duration: float | None = None
    outcome: str | None = None


class TaskListOut(BaseModel):
    """Response model for GET /api/tasks."""

    tasks: list[TaskSummaryOut]
    mtime: int


class SessionListOut(BaseModel):
    """Response model for GET /api/sessions."""

    sessions: list[SessionOut]
