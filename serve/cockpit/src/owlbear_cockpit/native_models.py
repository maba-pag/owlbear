"""Typed Cockpit response models for native change authority."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from owlbear_kanban import ChangeHealthFinding, ImpactClosure, JobRecord, ReceiptRecord, StoredJob

_DeliveryDigest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]


class NativeDiagnosticResponse(BaseModel):
    """Expose stable loader diagnostics without source filesystem paths."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    detail: str
    target: str | None = None


class JobAdminConflictResponse(BaseModel):
    """Expose one stable administrative conflict with current job authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    detail: str
    current_delivery_digest: str
    target: str
    lower_code: str | None = None
    current: StoredJob | None = None


class JobAdminConflictEnvelope(BaseModel):
    """Match FastAPI's HTTPException response wrapper."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    detail: JobAdminConflictResponse


class ChangeListEntryResponse(BaseModel):
    """Summarize one discoverable native change package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str
    state: Literal["loaded", "invalid"]
    delivery_digest: str | None = None
    diagnostics: tuple[NativeDiagnosticResponse, ...] = ()


class ChangeListResponse(BaseModel):
    """Contain identity-ordered native change summaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    changes: tuple[ChangeListEntryResponse, ...]


class ChangeDetailResponse(BaseModel):
    """Expose joined native authority for one admitted revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str
    delivery_digest: str
    intent: str
    design: str
    decisions: dict[str, Any]
    graph: dict[str, Any]


class ChangeGraphResponse(BaseModel):
    """Expose the delivery graph with current isolated node plans."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str
    delivery_digest: str
    graph: dict[str, Any]
    plans: dict[str, dict[str, Any]]


class JobDetailResponse(BaseModel):
    """Compose one immutable job with its authority-defined purpose."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job: JobRecord
    token: str
    title: str
    outcome: str
    acceptance: tuple[str, ...]
    modules: tuple[str, ...]
    interfaces: tuple[str, ...]
    proof: str


class InvalidationResponse(BaseModel):
    """Expose one persisted supersession and its affected closure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    invalidation_id: str
    supersession_receipt_id: str
    issued_at: str
    impact_closure: ImpactClosure
    affected_receipt_ids: tuple[str, ...]
    corrective_finding_ids: tuple[str, ...]
    corrective_job_ids: tuple[int, ...]
    receipt: ReceiptRecord


class ChangeHealthPageResponse(BaseModel):
    """Expose one bounded page of canonical change-health results."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: tuple[ChangeHealthFinding, ...]
    checked_paths: tuple[str, ...]
    next_cursor: str | None = None


class ResolveRequestBody(BaseModel):
    """Provide one strict native request-resolution identity."""

    model_config = ConfigDict(extra="forbid", strict=True)

    delivery_digest: _DeliveryDigest
    disposition: Literal["local", "material"]
    resolved_at: str = Field(min_length=1)
    resolved_by: str = Field(min_length=1)
    selected_option_id: str | None = None
    response: str | None = None
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _require_resolution_answer(self) -> ResolveRequestBody:
        if self.selected_option_id is None and not self.response:
            message = "a resolution needs a selected option or response"
            raise ValueError(message)
        return self


class ReleaseJobBody(BaseModel):
    """Provide one strict native claim-release identity."""

    model_config = ConfigDict(extra="forbid", strict=True)

    delivery_digest: _DeliveryDigest
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    released_at: str = Field(min_length=1)


class SetJobPriorityBody(BaseModel):
    """Provide one strict OCC-guarded native priority update."""

    model_config = ConfigDict(extra="forbid", strict=True)

    job_id: int
    delivery_digest: _DeliveryDigest
    expected_token: str = Field(min_length=1)
    priority: int
    updated_at: str = Field(min_length=1)


class CancelJobBody(BaseModel):
    """Provide one strict OCC-guarded native job cancellation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    job_id: int
    delivery_digest: _DeliveryDigest
    expected_token: str = Field(min_length=1)
    cancelled_at: str = Field(min_length=1)


__all__ = [
    "CancelJobBody",
    "ChangeDetailResponse",
    "ChangeGraphResponse",
    "ChangeHealthPageResponse",
    "ChangeListEntryResponse",
    "ChangeListResponse",
    "InvalidationResponse",
    "JobAdminConflictEnvelope",
    "JobAdminConflictResponse",
    "JobDetailResponse",
    "NativeDiagnosticResponse",
    "ReleaseJobBody",
    "ResolveRequestBody",
    "SetJobPriorityBody",
]
