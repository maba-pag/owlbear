"""Pydantic models for kanban-md task data at the MCP protocol boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MCPParamsBase(BaseModel):
    """Base model for MCP tool parameter schemas."""

    model_config = ConfigDict(extra="forbid")


class ListTasksParams(MCPParamsBase):
    """Input schema for list_tasks."""

    status: str | None = None
    tag: str | None = None
    priority: str | None = None
    search: str | None = None
    sort: str | None = None
    unclaimed: bool | None = None
    archived: bool | None = None
    limit: int | None = None
    reverse: bool | None = None
    blocked: bool | None = None
    ids: list[int] | None = None

    @model_validator(mode="after")
    def _validate_ids_exclusivity(self) -> ListTasksParams:
        """Enforce AC15: ids cannot be combined with other filter parameters."""
        if self.ids is None:
            return self
        if (
            self.status is not None
            or self.tag is not None
            or self.priority is not None
            or self.search is not None
            or self.unclaimed is not None
        ):
            msg = "ids cannot be combined with other filter parameters"
            raise ValueError(msg)
        return self


class ShowTaskParams(MCPParamsBase):
    """Input schema for show_task."""

    task_id: int
    section: str | None = None


class PickTasksParams(MCPParamsBase):
    """Input schema for pick_tasks."""

    limit: int = 25
    tag: str = ""


class CreateTaskParams(MCPParamsBase):
    """Input schema for create_task."""

    title: str
    body: str = ""
    depends_on: str = ""
    parent: int = 0
    priority: str = ""
    tags: str = ""


class EditTaskParams(MCPParamsBase):
    """Input schema for edit_task."""

    task_id: int
    body: str = ""
    block: str = ""
    unblock: bool = False
    add_tag: str = ""
    remove_tag: str = ""
    priority: str = ""
    append_body: str = ""
    timestamp: bool = False
    add_dep: str = ""
    remove_dep: str = ""
    parent: int = 0
    title: str = ""


class MoveTaskParams(MCPParamsBase):
    """Input schema for move_task."""

    task_id: int
    status: str


class StartWorkParams(MCPParamsBase):
    """Input schema for start_work."""

    task_id: int


class EndWorkParams(MCPParamsBase):
    """Input schema for end_work."""

    task_id: int
    note: str
    outcome: Literal["success", "fail", "block", "reject"] = "success"
    block_reason: str = ""
    move_to: str = "research"


class KanbanTask(BaseModel):
    """Represents a single kanban task as returned by kanban-md --json."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Guidance field (first — controls serialization order)
    guidance: list[str] = Field(default_factory=list)

    # Required fields
    id: int
    title: str
    status: str
    priority: str
    created: str
    updated: str

    # Optional fields
    claimed: bool = False
    tags: list[str] = Field(default_factory=list)
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    body: str | None = None
    file: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_claimed(cls, data: dict[str, object]) -> dict[str, object]:
        """Convert kanban-md's claimed_by string to a boolean claimed flag."""
        if isinstance(data, dict) and "claimed_by" in data:
            data["claimed"] = data.pop("claimed_by") is not None
        return data
