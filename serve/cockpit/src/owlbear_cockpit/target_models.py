"""Typed HTTP models for the dormant target work-item API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_kanban.target_authority import Commitment, CompletionSummary, DesignReentryBriefing, SemanticUpdate
from owlbear_kanban.work_items import TaskProgress, WorkItemProjection, WorkItemStage


class _TargetHTTPModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AttentionCounts(_TargetHTTPModel):
    """Count portfolio cards by orthogonal attention state."""

    user: int = Field(ge=0)
    agent: int = Field(ge=0)
    waiting: int = Field(ge=0)
    none: int = Field(ge=0)


class WorkItemPortfolioResponse(_TargetHTTPModel):
    """Return mixed-change semantic cards and portfolio attention totals."""

    items: tuple[WorkItemProjection, ...]
    attention_counts: AttentionCounts


class WorkItemTraceLinks(_TargetHTTPModel):
    """Keep technical resources one explicit drill-down from semantic detail."""

    activity: str
    evidence: str
    requests: str


class WorkItemDetailResponse(_TargetHTTPModel):
    """Compose semantic authority, progress, correction history, and trace links."""

    card: WorkItemProjection
    authority_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    commitments: tuple[Commitment, ...]
    acceptance: tuple[str, ...]
    task_progress: tuple[TaskProgress, ...]
    correction_history: tuple[dict[str, object], ...]
    semantic_updates: tuple[SemanticUpdate, ...]
    completion_summary: CompletionSummary | None
    trace_links: WorkItemTraceLinks


class WorkItemTraceResponse(_TargetHTTPModel):
    """Return technical activity and evidence only from the trace resource."""

    activity: tuple[dict[str, object], ...]
    evidence: tuple[dict[str, object], ...]


class SemanticUpdatesResponse(_TargetHTTPModel):
    """Return non-blocking semantic revisions for one work item."""

    updates: tuple[SemanticUpdate, ...]


class CompletionSummaryResponse(_TargetHTTPModel):
    """Return the commitment-level completion summary when present."""

    completion_summary: CompletionSummary | None


class WorkItemRequestsResponse(_TargetHTTPModel):
    """Return requests scoped to one semantic work item."""

    requests: tuple[dict[str, object], ...]


class ResumeDesignResponse(_TargetHTTPModel):
    """Return persisted design context without mutating admitted authority."""

    work_item_id: str
    stage: Literal[WorkItemStage.DESIGN] = WorkItemStage.DESIGN
    briefing: DesignReentryBriefing


class CreateWorkItemRequestBody(_TargetHTTPModel):
    """Create one request beneath current semantic authority."""

    request_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    commitment_id: str = Field(min_length=1)
    task_id: str | None = None
    created_at: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class ResolveWorkItemRequestBody(_TargetHTTPModel):
    """Resolve one request while retaining its immutable semantic target."""

    resolved_at: str = Field(min_length=1)


class RecoverWorkItemBody(_TargetHTTPModel):
    """Identify one interrupted task and its recorded owner process."""

    job_id: int = Field(gt=0)
    attempt_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    claim_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    process_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    recovered_at: str = Field(min_length=1)


__all__ = [
    "AttentionCounts",
    "CompletionSummaryResponse",
    "CreateWorkItemRequestBody",
    "RecoverWorkItemBody",
    "ResolveWorkItemRequestBody",
    "ResumeDesignResponse",
    "SemanticUpdatesResponse",
    "WorkItemDetailResponse",
    "WorkItemPortfolioResponse",
    "WorkItemRequestsResponse",
    "WorkItemTraceLinks",
    "WorkItemTraceResponse",
]
