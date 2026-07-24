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
    archival_reason: str | None = None
    parent: int | None = None
    search: str | None = None
    sort: str | None = None
    unclaimed: bool = False
    limit: int = 0
    reverse: bool = False
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
            or self.archival_reason is not None
            or self.parent is not None
            or self.search is not None
            or self.unclaimed
            or self.blocked is not None
        ):
            msg = "ids cannot be combined with other filter parameters"
            raise ValueError(msg)
        return self


class ShowTaskParams(MCPParamsBase):
    """Input schema for show_task."""

    id: int
    section: str | None = None


class PickTasksParams(MCPParamsBase):
    """Input schema for pick_tasks."""

    wave_size: int | None = None
    max_waves: int = 3


class PickJobsParams(MCPParamsBase):
    change_id: str = Field(min_length=1)
    candidate_revision: str = Field(min_length=1)
    wave_size: int = Field(gt=0)


class StartJobParams(MCPParamsBase):
    change_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    claimed_at: str = Field(min_length=1)
    candidate_revision: str = Field(min_length=1)


class FinishJobParams(MCPParamsBase):
    change_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    finished_at: str = Field(min_length=1)
    receipt_id: str = Field(min_length=1)
    code_revision: str = Field(min_length=1)
    evidence: dict[str, object]
    evidence_ids: tuple[str, ...] = ()
    impact_closure: dict[str, object] | None = None


class FinishShapeParams(FinishJobParams):
    node_plan: dict[str, object]
    build_job_ids: tuple[int, ...]
    accept_job_id: int = Field(gt=0)


class ReleaseJobParams(MCPParamsBase):
    change_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    released_at: str = Field(min_length=1)


class RecoverExpiredClaimsParams(MCPParamsBase):
    change_id: str = Field(min_length=1)
    recovered_at: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)


class CreateTaskParams(MCPParamsBase):
    """Input schema for create_task."""

    title: str
    body: str = ""
    priority: str = "needed"
    tags: list[str] | None = None
    parent: int | None = None
    depends_on: list[int] | None = None


class EditTaskParams(MCPParamsBase):
    """Input schema for edit_task."""

    id: int
    title: str | None = None
    body: str | None = None
    append_body: str | None = None
    timestamp: bool = False
    priority: str | None = None
    parent: int | None = None
    add_dep: list[int] | None = None
    remove_dep: list[int] | None = None
    add_tag: list[str] | None = None
    remove_tag: list[str] | None = None
    block_reason: str | None = None
    archival_reason: str | None = None
    archival_refs: list[int] | None = None


class MoveTaskParams(MCPParamsBase):
    """Input schema for move_task."""

    id: int
    status: str
    archival_reason: str | None = None
    archival_refs: list[int] | None = None


class StartWorkParams(MCPParamsBase):
    """Input schema for start_work."""

    id: int


class EndWorkParams(MCPParamsBase):
    """Input schema for end_work."""

    id: int
    outcome: Literal["success", "fail", "reject", "release", "block"] = "success"
    move_to: str | None = None
    note: str | None = None
    archival_reason: str | None = None
    archival_refs: list[int] | None = None
    block_reason: str | None = None


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

    @model_validator(mode="before")
    @classmethod
    def _coerce_claimed(cls, data: dict[str, object]) -> dict[str, object]:
        """Convert kanban-md's claimed_by string to a boolean claimed flag."""
        if isinstance(data, dict) and "claimed_by" in data:
            data["claimed"] = data.pop("claimed_by") is not None
        return data
