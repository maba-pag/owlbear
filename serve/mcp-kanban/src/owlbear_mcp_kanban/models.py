"""Pydantic models for native delivery data at the MCP protocol boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MCPParamsBase(BaseModel):
    """Base model for MCP tool parameter schemas."""

    model_config = ConfigDict(extra="forbid")


class PickJobsParams(MCPParamsBase):
    """Validate MCP inputs for planning native dispatch waves."""

    change_id: str = Field(min_length=1)
    candidate_revision: str = Field(min_length=1)
    wave_size: int = Field(gt=0)


class StartJobParams(MCPParamsBase):
    """Validate MCP inputs for claiming one native job."""

    change_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    claimed_at: str = Field(min_length=1)
    candidate_revision: str = Field(min_length=1)


class FinishJobParams(MCPParamsBase):
    """Validate MCP inputs for completing a native job with receipt evidence."""

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


class FinishPlanParams(FinishJobParams):
    """Validate plan completion inputs and downstream job identities."""

    node_plan: dict[str, object]
    build_job_ids: tuple[int, ...]
    accept_job_id: int = Field(gt=0)


class FinishAcceptParams(FinishJobParams):
    """Validate accept completion reconciliation-plan identities."""

    reconciliation_plan_job_ids: tuple[int, ...]


class ReleaseJobParams(MCPParamsBase):
    """Validate MCP inputs for releasing one active native job claim."""

    change_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    released_at: str = Field(min_length=1)


class RecoverExpiredClaimsParams(MCPParamsBase):
    """Validate MCP inputs for an expired-claim recovery pass."""

    change_id: str = Field(min_length=1)
    recovered_at: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)


class ListJobsParams(MCPParamsBase):
    """Validate MCP inputs for listing native jobs."""

    change_id: str = Field(min_length=1)
    candidate_revision: str = Field(min_length=1)
    cursor: str | None = None
    limit: int = Field(default=100, gt=0)


class ShowJobParams(MCPParamsBase):
    """Validate MCP inputs for showing one native job."""

    change_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)


class ListAttemptsParams(MCPParamsBase):
    """Validate MCP inputs for listing attempt history."""

    change_id: str = Field(min_length=1)
    cursor: str | None = None
    limit: int = Field(default=100, gt=0)


class ListActivityParams(MCPParamsBase):
    """Validate MCP inputs for listing runtime activity history."""

    change_id: str = Field(min_length=1)
    cursor: str | None = None
    limit: int = Field(default=100, gt=0)


class ShowReceiptParams(MCPParamsBase):
    """Validate MCP inputs for showing one immutable receipt."""

    change_id: str = Field(min_length=1)
    receipt_id: str = Field(min_length=1)


class WorkHealthParams(MCPParamsBase):
    """Validate MCP inputs for native work health checks."""

    change_id: str = Field(min_length=1)
    cursor: str | None = None
    limit: int = Field(default=100, gt=0)
