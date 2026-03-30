"""Pydantic data models for the OwlBear planner."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class Task(BaseModel):
    """A kanban task as returned by kanban-md list --json."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int
    title: str
    status: str
    priority: str
    created: datetime
    updated: datetime
    started: datetime | None = None
    completed: datetime | None = None
    tags: list[str]
    depends_on: list[int]
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    task_class: str = Field(alias="class")
    body: str
    file: str


class DispatchEntry(BaseModel):
    """A single agent dispatch entry in a dispatch plan."""

    model_config = ConfigDict(frozen=True)

    task_id: int
    agent: str
    target_status: str
    retry_hint: str = ""


class DispatchPlan(BaseModel):
    """A collection of dispatch entries to be executed."""

    model_config = ConfigDict(frozen=True)

    entries: list[DispatchEntry]


task_list_adapter: TypeAdapter[list[Task]] = TypeAdapter(list[Task])
