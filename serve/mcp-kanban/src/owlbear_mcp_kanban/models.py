"""Pydantic models for native delivery data at the MCP protocol boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_kanban import Finding


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


class CorrectiveJobParams(MCPParamsBase):
    """Validate one minimum corrective job at the MCP boundary."""

    kind: Literal["plan", "build"]
    target_node_id: str = Field(min_length=1)
    packet_id: str | None = Field(default=None, pattern=r"^DN-[0-9]{3}-PK-[0-9]{3}$")
    through_plan_correction: bool = False

    @model_validator(mode="after")
    def _validate_packet_authority(self) -> CorrectiveJobParams:
        if self.kind == "build" and self.packet_id is None:
            message = "corrective build plans require packet identity"
            raise ValueError(message)
        if self.kind == "plan" and self.packet_id is not None:
            message = "corrective plan jobs forbid packet identity"
            raise ValueError(message)
        return self


class CorrectiveRouteParams(MCPParamsBase):
    """Validate one typed corrective route at the MCP boundary."""

    finding_id: str = Field(min_length=1)
    finding_class: Literal[
        "implementation-defect",
        "unforeseeable-discovery",
        "planning-omission",
        "scope-change",
    ]
    route: Literal[
        "build-repair",
        "node-plan-revision",
        "design-reentry",
        "node-integration-repair",
        "affected-node-correction",
    ]
    packet_id: str | None = Field(default=None, pattern=r"^DN-[0-9]{3}-PK-[0-9]{3}$")
    design_reentry: bool = False
    jobs: tuple[CorrectiveJobParams, ...] = ()

    @model_validator(mode="after")
    def _validate_packet_authority(self) -> CorrectiveRouteParams:
        build_packet_ids = tuple(job.packet_id for job in self.jobs if job.kind == "build")
        if self.route == "build-repair" and self.packet_id is None:
            message = "build repair routes require packet identity"
            raise ValueError(message)
        if build_packet_ids and any(item != self.packet_id for item in build_packet_ids):
            message = "corrective route packet identity must match its build plans"
            raise ValueError(message)
        if self.route != "build-repair" and self.packet_id is not None:
            message = "corrective routes without build plans forbid packet identity"
            raise ValueError(message)
        return self


class InvalidationParams(MCPParamsBase):
    """Validate supersession and minimum corrective work at the MCP boundary."""

    invalidation_id: str = Field(min_length=1)
    supersession_receipt_id: str = Field(min_length=1)
    invalidated_receipt_ids: tuple[str, ...] = Field(min_length=1)
    routes: tuple[CorrectiveRouteParams, ...] = Field(min_length=1)
    corrective_job_ids: tuple[int, ...]
    issued_at: str = Field(min_length=1)
    code_revision: str = Field(min_length=1)
    priority: int = 0


class RejectAcceptParams(MCPParamsBase):
    """Validate accept rejection and corrective publication inputs."""

    change_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    rejected_at: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    evidence_ids: tuple[str, ...]
    findings: tuple[Finding, ...] = Field(min_length=1)
    invalidation: InvalidationParams


class RejectAuditParams(RejectAcceptParams):
    """Validate audit rejection and corrective publication inputs."""


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


class ListFindingsParams(MCPParamsBase):
    """Validate MCP inputs for listing corrective findings."""

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


class ShowFindingParams(MCPParamsBase):
    """Validate MCP inputs for showing one immutable finding."""

    change_id: str = Field(min_length=1)
    finding_id: str = Field(min_length=1)


class WorkHealthParams(MCPParamsBase):
    """Validate MCP inputs for native work health checks."""

    change_id: str = Field(min_length=1)
    cursor: str | None = None
    limit: int = Field(default=100, gt=0)
