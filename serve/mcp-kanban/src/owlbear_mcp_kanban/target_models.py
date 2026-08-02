"""Protocol models for the target delivery MCP surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_kanban.change import ChangeId
from owlbear_kanban.target_runtime import RuntimeId
from owlbear_kanban.work_items import WorkItemProjection


class _TargetProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TargetDiagnostic(_TargetProtocolModel):
    """Stable transport failure with current semantic authority identity."""

    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    current_authority_identity: str = Field(min_length=1)
    retry_safe: bool


class WorkItemPage(_TargetProtocolModel):
    """One stable page from the global semantic work portfolio."""

    items: tuple[WorkItemProjection, ...]
    authority_identity: str = Field(min_length=1)
    next_cursor: str | None = None


class TargetCursor(_TargetProtocolModel):
    """Opaque cursor payload bound to one exact portfolio projection."""

    schema_version: Literal[1] = 1
    query_identity: str = Field(min_length=1)
    offset: int = Field(ge=0)


class TargetRequestParams(_TargetProtocolModel):
    """Validate one scoped target request at the MCP boundary."""

    request_id: RuntimeId
    change_id: ChangeId
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_item_id: str = Field(min_length=1)
    commitment_id: str = Field(min_length=1)
    task_id: str | None = None
    created_at: str = Field(min_length=1)
    summary: str = Field(min_length=1)


__all__ = [
    "TargetCursor",
    "TargetDiagnostic",
    "TargetRequestParams",
    "WorkItemPage",
]
