"""Protocol models for the target delivery MCP surface."""

from __future__ import annotations

import json
from functools import partial
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from owlbear_delivery.change_workspace import ChangeWorktreeAttentionCode
from owlbear_delivery.delivery_application_loader import DeliveryStartupConfig
from owlbear_delivery.delivery_runtime import (
    DeliveryChangeStage,
    DeliveryOutputReference,
    DeliveryPlanCandidate,
    DeliveryResultCandidate,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryTransition,
    FinalizeDeliveryChange,
    PublishDeliveryPlan,
    PublishDeliveryResult,
)
from owlbear_delivery.draft_pull_request import MarkChangePullRequestReady
from owlbear_delivery.identities import ChangeId
from owlbear_delivery.portfolio_application import (
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryRetainedChangeWorktree,
    DeliveryRetainedWorktreeCleanupBlockReason,
)
from owlbear_delivery.target_admission import DeliveryAdmissionRequest


class _TargetProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryStartupDiagnostic(RuntimeError):
    """Structured fail-closed Delivery startup failure."""

    __slots__ = ("code", "detail", "field", "retry_safe")

    def __init__(self, code: str, detail: str, field: str) -> None:
        self.code = code
        self.detail = detail
        self.field = field
        self.retry_safe = False
        super().__init__(json.dumps(self.model_dump(), sort_keys=True))

    def model_dump(self) -> dict[str, str | bool]:
        """Return the stable diagnostic fields without rejected values."""
        return {
            "code": self.code,
            "detail": self.detail,
            "field": self.field,
            "retry_safe": self.retry_safe,
        }


class TargetDiagnostic(_TargetProtocolModel):
    """Stable transport failure with current semantic authority identity."""

    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    current_authority_identity: str = Field(min_length=1)
    retry_safe: bool


class EmptyParams(_TargetProtocolModel):
    """Validate an operation that accepts no parameters."""


class ChangeParams(_TargetProtocolModel):
    """Validate one exact Delivery change identity."""

    change_id: ChangeId


class ResolveChangeDispositionParams(ChangeParams):
    """Validate one exact Change attention identity for explicit resolution."""

    expected_disposition_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeferChangeParams(ChangeParams):
    """Validate one user-requested Change deferral."""

    reason: str = Field(min_length=1)


class AbandonChangeParams(ChangeParams):
    """Validate one user-requested terminal Change abandonment."""

    reason: str = Field(min_length=1)


class CleanupAbandonedChangeParams(ChangeParams):
    """Validate cleanup of one terminal abandoned Change worktree."""


class CleanupCompletedChangeParams(ChangeParams):
    """Validate cleanup of one completed Change worktree receipt."""

    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class RecoverChangeWorktreeParams(ChangeParams):
    """Validate explicit recovery of one Change worktree from reviewed authority."""

    confirmed_recovery: Literal[True]
    recovery_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class CreateDesignSessionParams(ChangeParams):
    """Validate authored Design source bytes."""

    intent_bytes: bytes
    design_bytes: bytes


class ReviseDesignSessionParams(CreateDesignSessionParams):
    """Validate one compare-and-swap authored Design revision."""

    expected_package_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkItemParams(ChangeParams):
    """Validate one exact work item within a Delivery change."""

    work_item_id: str = Field(min_length=1)


class ClaimContextParams(ChangeParams):
    """Validate one exact active Delivery claim."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)


class RepairClaimContextParams(ChangeParams):
    """Validate one exact active change-level Integration repair claim."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)


class AdmitDeliveryChangeParams(_TargetProtocolModel):
    """Validate source-bound Delivery admission."""

    request: DeliveryAdmissionRequest


class PublishDeliveryPlanParams(ChangeParams):
    """Validate one Planning publication."""

    request: PublishDeliveryPlan


class PublishDeliveryResultParams(ChangeParams):
    """Validate one Build result publication."""

    request: PublishDeliveryResult


class FinalizeDeliveryChangeParams(ChangeParams):
    """Validate one exact-head Change finalization request."""

    request: FinalizeDeliveryChange


class MarkChangeReadyParams(_TargetProtocolModel):
    """Validate one exact finalized pull-request ready transition."""

    request: MarkChangePullRequestReady


class SupersedePublicationParams(ChangeParams):
    """Validate one exact publication-attention supersession operation."""

    expected_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class DeliveryPlanPublication(_TargetProtocolModel):
    """Planning publication response with its transition-ready output reference."""

    candidate_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tasks: tuple[DeliveryTaskDefinition, ...]
    output: DeliveryOutputReference

    @classmethod
    def from_candidate(cls, candidate: DeliveryPlanCandidate) -> DeliveryPlanPublication:
        """Project one domain candidate into its complete MCP response."""
        return cls(**candidate.model_dump(), output=candidate.output)


class RetainedChangeWorktreeResponse(_TargetProtocolModel):
    """Strict MCP row for one retained Change worktree."""

    change_id: ChangeId
    worktree_path: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    branch_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    recovery_reviewed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    coordination_registered: bool
    git_registered: bool
    worktree_present: bool
    worktree_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    worktree_branch: str | None = None
    worktree_locked: bool = False
    worktree_prunable: bool = False
    worktree_bare: bool = False
    attention: tuple[ChangeWorktreeAttentionCode, ...] = ()
    lifecycle: DeliveryChangeStage | None = None
    orphan: bool
    cleanup_eligible: bool
    cleanup_blocked_reason: DeliveryRetainedWorktreeCleanupBlockReason | None = None

    @classmethod
    def from_projection(cls, projection: DeliveryRetainedChangeWorktree) -> RetainedChangeWorktreeResponse:
        """Convert one application projection into the transport contract."""
        values = projection.model_dump(mode="python")
        values["worktree_path"] = str(projection.worktree_path)
        return cls(**values)


class ChangeWorktreeCleanupResponse(_TargetProtocolModel):
    """Strict MCP receipt for one exact Change worktree cleanup."""

    cleanup_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: str = Field(min_length=1)
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(cls, receipt: DeliveryChangeWorktreeCleanup) -> ChangeWorktreeCleanupResponse:
        """Convert one application cleanup receipt into transport form."""
        return cls(
            cleanup_id=receipt.cleanup_id,
            change_id=receipt.change_id,
            branch=receipt.branch,
            worktree_path=str(receipt.worktree_path),
            branch_head=receipt.branch_head,
        )


class ChangeWorktreeRecoveryResponse(_TargetProtocolModel):
    """Strict MCP receipt for one exact Change worktree recovery."""

    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: str = Field(min_length=1)
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    recovery_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(cls, receipt: DeliveryChangeWorktreeRecovery) -> ChangeWorktreeRecoveryResponse:
        """Convert one application recovery receipt into transport form."""
        return cls(
            change_id=receipt.change_id,
            branch=receipt.branch,
            worktree_path=str(receipt.worktree_path),
            branch_head=receipt.branch_head,
            recovery_reviewed_head=receipt.recovery_reviewed_head,
        )


class DeliveryResultPublication(_TargetProtocolModel):
    """Build publication response with its transition-ready output reference."""

    candidate_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: DeliveryTaskResult
    output: DeliveryOutputReference

    @classmethod
    def from_candidate(cls, candidate: DeliveryResultCandidate) -> DeliveryResultPublication:
        """Project one domain candidate into its complete MCP response."""
        return cls(**candidate.model_dump(), output=candidate.output)


class TransitionDeliveryParams(ChangeParams):
    """Validate one worker-owned mechanical transition."""

    request: DeliveryTransition


class CompletedPageParams(_TargetProtocolModel):
    """Validate one bounded completed-history page request."""

    cursor: str | None = None
    limit: int = Field(default=100, gt=0, le=100)


class SearchCompletedParams(CompletedPageParams):
    """Validate one completed-history semantic search."""

    query: str = Field(min_length=1)


class ShowCompletedParams(ChangeParams):
    """Validate one exact completed Delivery record lookup."""

    completion_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def _parse_json_model[ModelT: BaseModel](model: type[ModelT], value: object) -> ModelT:
    """Parse MCP JSON arguments before strict Python-mode model validation."""
    if isinstance(value, model):
        return value
    return model.model_validate_json(json.dumps(value))


type AdmitDeliveryChangeRequest = Annotated[
    AdmitDeliveryChangeParams,
    BeforeValidator(partial(_parse_json_model, AdmitDeliveryChangeParams)),
]
type ChangeRequest = Annotated[ChangeParams, BeforeValidator(partial(_parse_json_model, ChangeParams))]
type DeferChangeRequest = Annotated[
    DeferChangeParams,
    BeforeValidator(partial(_parse_json_model, DeferChangeParams)),
]
type AbandonChangeRequest = Annotated[
    AbandonChangeParams,
    BeforeValidator(partial(_parse_json_model, AbandonChangeParams)),
]
type CleanupAbandonedChangeRequest = Annotated[
    CleanupAbandonedChangeParams,
    BeforeValidator(partial(_parse_json_model, CleanupAbandonedChangeParams)),
]
type CleanupCompletedChangeRequest = Annotated[
    CleanupCompletedChangeParams,
    BeforeValidator(partial(_parse_json_model, CleanupCompletedChangeParams)),
]
type RecoverChangeWorktreeRequest = Annotated[
    RecoverChangeWorktreeParams,
    BeforeValidator(partial(_parse_json_model, RecoverChangeWorktreeParams)),
]
type ClaimContextRequest = Annotated[
    ClaimContextParams,
    BeforeValidator(partial(_parse_json_model, ClaimContextParams)),
]
type CompletedPageRequest = Annotated[
    CompletedPageParams,
    BeforeValidator(partial(_parse_json_model, CompletedPageParams)),
]
type CreateDesignSessionRequest = Annotated[
    CreateDesignSessionParams,
    BeforeValidator(partial(_parse_json_model, CreateDesignSessionParams)),
]
type EmptyRequest = Annotated[EmptyParams, BeforeValidator(partial(_parse_json_model, EmptyParams))]
type FinalizeDeliveryChangeRequest = Annotated[
    FinalizeDeliveryChangeParams,
    BeforeValidator(partial(_parse_json_model, FinalizeDeliveryChangeParams)),
]
type MarkChangeReadyRequest = Annotated[
    MarkChangeReadyParams,
    BeforeValidator(partial(_parse_json_model, MarkChangeReadyParams)),
]
type SupersedePublicationRequest = Annotated[
    SupersedePublicationParams,
    BeforeValidator(partial(_parse_json_model, SupersedePublicationParams)),
]
type PublishDeliveryPlanRequest = Annotated[
    PublishDeliveryPlanParams,
    BeforeValidator(partial(_parse_json_model, PublishDeliveryPlanParams)),
]
type RepairClaimContextRequest = Annotated[
    RepairClaimContextParams,
    BeforeValidator(partial(_parse_json_model, RepairClaimContextParams)),
]
type PublishDeliveryResultRequest = Annotated[
    PublishDeliveryResultParams,
    BeforeValidator(partial(_parse_json_model, PublishDeliveryResultParams)),
]
type ReviseDesignSessionRequest = Annotated[
    ReviseDesignSessionParams,
    BeforeValidator(partial(_parse_json_model, ReviseDesignSessionParams)),
]
type ResolveChangeDispositionRequest = Annotated[
    ResolveChangeDispositionParams,
    BeforeValidator(partial(_parse_json_model, ResolveChangeDispositionParams)),
]
type SearchCompletedRequest = Annotated[
    SearchCompletedParams,
    BeforeValidator(partial(_parse_json_model, SearchCompletedParams)),
]
type ShowCompletedRequest = Annotated[
    ShowCompletedParams,
    BeforeValidator(partial(_parse_json_model, ShowCompletedParams)),
]
type TransitionDeliveryRequest = Annotated[
    TransitionDeliveryParams,
    BeforeValidator(partial(_parse_json_model, TransitionDeliveryParams)),
]
type WorkItemRequest = Annotated[WorkItemParams, BeforeValidator(partial(_parse_json_model, WorkItemParams))]


__all__ = [
    "AbandonChangeParams",
    "AbandonChangeRequest",
    "AdmitDeliveryChangeParams",
    "AdmitDeliveryChangeRequest",
    "ChangeParams",
    "ChangeRequest",
    "ChangeWorktreeCleanupResponse",
    "ChangeWorktreeRecoveryResponse",
    "ClaimContextParams",
    "ClaimContextRequest",
    "CleanupAbandonedChangeParams",
    "CleanupAbandonedChangeRequest",
    "CleanupCompletedChangeParams",
    "CleanupCompletedChangeRequest",
    "CompletedPageParams",
    "CompletedPageRequest",
    "CreateDesignSessionParams",
    "CreateDesignSessionRequest",
    "DeferChangeParams",
    "DeferChangeRequest",
    "DeliveryPlanPublication",
    "DeliveryResultPublication",
    "DeliveryStartupConfig",
    "DeliveryStartupDiagnostic",
    "EmptyParams",
    "EmptyRequest",
    "FinalizeDeliveryChangeParams",
    "FinalizeDeliveryChangeRequest",
    "MarkChangeReadyParams",
    "MarkChangeReadyRequest",
    "PublishDeliveryPlanParams",
    "PublishDeliveryPlanRequest",
    "PublishDeliveryResultParams",
    "PublishDeliveryResultRequest",
    "RecoverChangeWorktreeParams",
    "RecoverChangeWorktreeRequest",
    "RepairClaimContextParams",
    "RepairClaimContextRequest",
    "ResolveChangeDispositionParams",
    "ResolveChangeDispositionRequest",
    "RetainedChangeWorktreeResponse",
    "ReviseDesignSessionParams",
    "ReviseDesignSessionRequest",
    "SearchCompletedParams",
    "SearchCompletedRequest",
    "ShowCompletedParams",
    "ShowCompletedRequest",
    "SupersedePublicationParams",
    "SupersedePublicationRequest",
    "TargetDiagnostic",
    "TransitionDeliveryParams",
    "TransitionDeliveryRequest",
    "WorkItemParams",
    "WorkItemRequest",
]
