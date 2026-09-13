"""Protocol models for the target delivery MCP surface."""

from __future__ import annotations

import json
from functools import partial
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from owlbear_delivery.change_publication import ChangeBranchSupersessionReceipt
from owlbear_delivery.change_workspace import (
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncReceipt,
    ChangeWorktreeAttentionCode,
    OutOfBandHeadRecoveryReceipt,
    PublicationBaselineRecoveryReceipt,
)
from owlbear_delivery.delivery_admission import DeliveryAdmissionRequest
from owlbear_delivery.delivery_application_loader import DeliveryStartupConfig
from owlbear_delivery.delivery_runtime import (
    AdministrativeDeliveryMovePreview,
    AdministrativeDeliveryMoveResult,
    DeliveryBlock,
    DeliveryChangeAbandonment,
    DeliveryChangeDeferral,
    DeliveryChangeDispositionResolution,
    DeliveryChangePublicationHistory,
    DeliveryChangeStage,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryOperatorMove,
    DeliveryOutputReference,
    DeliveryPlanCandidate,
    DeliveryRequest,
    DeliveryRequestResolution,
    DeliveryReturnContext,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryTransition,
    DeliveryWorkerRole,
    FinalizeDeliveryChange,
    OutcomeAuthorityBinding,
    PublishDeliveryPlan,
)
from owlbear_delivery.design_package import DesignPackageManifest, DesignPackageResult
from owlbear_delivery.draft_pull_request import DraftPullRequestSupersessionReceipt, MarkChangePullRequestReady
from owlbear_delivery.identities import ChangeId
from owlbear_delivery.portfolio_application import (
    DeliveryActionSelection,
    DeliveryAnswerKind,
    DeliveryChangeIntentKind,
    DeliveryChangeIntentResult,
    DeliveryChangePublicationSupersessionReceipt,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryOperatorContext,
    DeliveryQuarantinedSnapshotRepairProposal,
    DeliveryQuarantinedSnapshotRepairReceipt,
    DeliveryResultSubmissionResult,
    DeliveryRetainedChangeWorktree,
    DeliveryRetainedWorktreeCleanupBlockReason,
    DeliveryStateSnapshotRepairReceipt,
    DeliveryStrandedFrontierRepairReceipt,
    DeliveryTargetSyncRepairReceipt,
)
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthHeadRelation,
    DeliveryHealthReason,
    DeliveryHealthResolution,
    DeliveryHealthStatus,
    DeliveryHealthView,
)


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


class DeliveryHealthDiagnosticResponse(_TargetProtocolModel):
    """Bounded MCP diagnostic for Delivery state excluded from authority."""

    source: str = Field(min_length=1)
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1, max_length=240)
    change_id: str | None = Field(default=None, min_length=1)
    path: str | None = Field(default=None, min_length=1)
    retry_safe: bool
    reason: DeliveryHealthReason
    resolution: DeliveryHealthResolution
    expected_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    observed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    observed_local_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    head_relation: DeliveryHealthHeadRelation | None = None


class DeliveryHealthResponse(_TargetProtocolModel):
    """Current Delivery health and quarantined-state diagnostics."""

    status: DeliveryHealthStatus
    diagnostics: tuple[DeliveryHealthDiagnosticResponse, ...] = ()

    @classmethod
    def from_view(cls, view: DeliveryHealthView) -> DeliveryHealthResponse:
        """Project the shared Delivery health view into the MCP contract."""
        return cls(
            status=view.status,
            diagnostics=tuple(
                DeliveryHealthDiagnosticResponse(**diagnostic.model_dump()) for diagnostic in view.diagnostics
            ),
        )


class EmptyParams(_TargetProtocolModel):
    """Validate an operation that accepts no parameters."""


class AcquireActionsParams(_TargetProtocolModel):
    """Select one fenced action or explicitly request portfolio acquisition."""

    selection: DeliveryActionSelection | None = None


class ChangeParams(_TargetProtocolModel):
    """Validate one exact Delivery change identity."""

    change_id: ChangeId


class AnswerParams(ChangeParams):
    """Validate one version-bound request or requestless-block answer."""

    kind: DeliveryAnswerKind = DeliveryAnswerKind.REQUEST
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_id: str | None = None
    resolution: DeliveryRequestResolution | None = None
    outcome_id: str | None = Field(default=None, pattern=r"^OUT-[0-9]{3}$")
    block_id: str | None = None
    operator_note: str | None = None
    locators: tuple[str, ...] = ()
    expected_disposition_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_target(self) -> AnswerParams:
        if self.kind is DeliveryAnswerKind.REQUEST:
            if self.request_id is None or self.resolution is None:
                message = "request answers require request identity and resolution"
                raise ValueError(message)
            if any((self.outcome_id, self.block_id, self.operator_note, self.expected_disposition_id)) or self.locators:
                message = "request answers cannot include block evidence"
                raise ValueError(message)
        elif self.kind is DeliveryAnswerKind.BLOCK:
            if (
                self.outcome_id is None
                or self.block_id is None
                or self.operator_note is None
                or not self.operator_note.strip()
                or not self.locators
            ):
                message = "block answers require outcome, block, note, and locators"
                raise ValueError(message)
            if self.request_id is not None or self.resolution is not None or self.expected_disposition_id is not None:
                message = "block answers cannot include request resolution"
                raise ValueError(message)
        else:
            if self.expected_disposition_id is None:
                message = "disposition answers require an expected disposition identity"
                raise ValueError(message)
            if any((self.request_id, self.outcome_id, self.block_id, self.operator_note)) or self.locators:
                message = "disposition answers cannot include request or block evidence"
                raise ValueError(message)
        return self


class PutDesignParams(ChangeParams):
    """Validate one create-or-CAS-revise authored Design request."""

    intent_bytes: bytes
    design_bytes: bytes
    expected_package_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class SetChangeIntentParams(ChangeParams):
    """Validate one version-bound pause, resume, or abandon intent."""

    kind: DeliveryChangeIntentKind
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_reason(self) -> SetChangeIntentParams:
        if self.kind is DeliveryChangeIntentKind.RESUME:
            if self.reason is not None:
                message = "resume intent does not accept a reason"
                raise ValueError(message)
        elif self.reason is None or not self.reason.strip():
            message = "defer and abandon intents require a reason"
            raise ValueError(message)
        return self


class CleanupAbandonedChangeParams(ChangeParams):
    """Validate cleanup of one terminal abandoned Change worktree."""


class CleanupAbandonedTargetSyncParams(ChangeParams):
    """Validate explicit discard of an abandoned target-sync conflict before cleanup."""

    confirmed_discard: Literal[True]
    expected_target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class CleanupCompletedChangeParams(ChangeParams):
    """Validate cleanup of one completed Change worktree receipt."""

    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class RecoverChangeWorktreeParams(ChangeParams):
    """Validate explicit recovery of one Change worktree from reviewed authority."""

    confirmed_recovery: Literal[True]
    recovery_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class RecoverPublicationBaselineParams(ChangeParams):
    """Validate explicit recovery of one unknown publication baseline."""

    confirmed_recovery: Literal[True]
    expected_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


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


class WorkItemViewParams(ChangeParams):
    """Validate one exact detailed Work Item view."""

    item_key: str = Field(min_length=1)


class OperatorContextParams(ChangeParams):
    """Validate one exact outcome or Change operator context."""

    outcome_id: str = Field(min_length=1)


class RepairChangeParams(ChangeParams):
    """Validate one high-level repair diagnosis or proposal application."""

    proposal_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    confirmed_lost: bool = False


class PreviewAdministrativeMoveParams(ChangeParams):
    """Validate one read-only administrative movement preview."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage


class ClaimContextParams(ChangeParams):
    """Validate one exact active Delivery claim."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)


class RecoverClaimParams(ClaimContextParams):
    """Validate explicit lost-worker confirmation for claim recovery."""

    confirmed_lost: Literal[True]


class RepairClaimContextParams(ChangeParams):
    """Validate one exact active change-level Integration repair claim."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)


class PublishDeliveryPlanParams(ChangeParams):
    """Validate one Planning publication."""

    plan: PublishDeliveryPlan


class SubmitResultParams(ChangeParams):
    """Validate one claim-bound Builder result submission and promotion."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result: DeliveryTaskResult


class FinalizeDeliveryChangeParams(ChangeParams):
    """Validate one exact-head Change finalization request."""

    finalization: FinalizeDeliveryChange


class AdministrativeMoveParams(ChangeParams):
    """Validate one exact operator-directed backward movement."""

    move_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage
    reason: str = Field(min_length=1)
    expected_version: str = Field(pattern=r"^[0-9a-f]{64}$")


class SupersedePublicationParams(ChangeParams):
    """Validate one exact publication-attention supersession operation."""

    expected_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class TargetSyncParams(ChangeParams):
    """Validate one exact target synchronization operation."""

    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ExternalHeadAdoptionParams(ChangeParams):
    """Validate one exact external Change-head adoption operation."""

    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    adopted_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ExternalHeadPromotionParams(ChangeParams):
    """Validate one exact external Change-head promotion operation."""

    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class TargetSyncConflictParams(ChangeParams):
    """Validate one exact preserved target-sync conflict exit."""

    expected_disposition_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RepairTargetSyncPublicationParams(ChangeParams):
    """Validate explicit repair of one quarantined target-sync publication."""

    confirmed_repair: Literal[True]
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_merged_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_sync_operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RepairDeliveryStateSnapshotParams(ChangeParams):
    """Validate explicit repair of one quarantined local Delivery frontier."""

    confirmed_repair: Literal[True]
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RepairStrandedFrontierParams(ChangeParams):
    """Validate explicit repair of one missing request-provenance defect."""

    confirmed_repair: Literal[True]
    request_id: str = Field(min_length=1)
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RepairQuarantinedDeliveryStateSnapshotParams(ChangeParams):
    """Validate explicit repair of one quarantined remote Delivery snapshot."""

    confirmed_repair: Literal[True]
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"]
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RecoverOutOfBandHeadParams(ChangeParams):
    """Validate explicit recovery of one out-of-band Change head."""

    confirmed_recovery: Literal[True]
    expected_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
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


class ChangePublicationBaselineRecoveryResponse(_TargetProtocolModel):
    """Strict MCP receipt for one explicit publication baseline recovery."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    expected_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_base_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(
        cls,
        receipt: PublicationBaselineRecoveryReceipt,
    ) -> ChangePublicationBaselineRecoveryResponse:
        """Convert one domain recovery receipt into transport form."""
        return cls(**receipt.model_dump())


class DeliveryOperatorClaimResponse(_TargetProtocolModel):
    """Bounded active-claim identity for operator diagnostics."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None


class DeliveryOperatorRecoveryAttentionResponse(_TargetProtocolModel):
    """Bounded recovery evidence for operator diagnostics."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    custody_retained: bool
    retry_condition: str = Field(min_length=1)


class DeliveryOperatorIntegrationAttentionResponse(_TargetProtocolModel):
    """Bounded Integration attention for operator diagnostics."""

    code: DeliveryIntegrationAttentionCode
    disposition: DeliveryIntegrationAttentionDisposition
    diagnostics: tuple[str, ...] = Field(min_length=1)
    retry_condition: str = Field(min_length=1)


class DeliveryOperatorContextResponse(_TargetProtocolModel):
    """MCP projection of one bounded operator context."""

    change_id: ChangeId
    outcome_id: str = Field(min_length=1)
    stage: DeliveryStage
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()
    active_claim: DeliveryOperatorClaimResponse | None = None
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryOperatorRecoveryAttentionResponse | None = None
    integration_attention: DeliveryOperatorIntegrationAttentionResponse | None = None

    @classmethod
    def from_context(cls, context: DeliveryOperatorContext) -> DeliveryOperatorContextResponse:
        """Project application diagnostics without exposing frontier bindings."""
        active_claim = context.active_claim
        recovery_attention = context.recovery_attention
        integration_attention = context.integration_attention
        return cls(
            change_id=context.change_id,
            outcome_id=context.outcome_id,
            stage=context.stage,
            block=context.block,
            requests=context.requests,
            active_claim=(
                DeliveryOperatorClaimResponse(
                    attempt_id=active_claim.attempt_id,
                    claim_id=active_claim.claim_id,
                    started_at=active_claim.started_at,
                    worker_role=active_claim.worker_role,
                    task_id=active_claim.task_id,
                )
                if active_claim is not None
                else None
            ),
            return_context=context.return_context,
            recovery_attention=(
                DeliveryOperatorRecoveryAttentionResponse(
                    attempt_id=recovery_attention.attempt_id,
                    claim_id=recovery_attention.claim_id,
                    reason=recovery_attention.reason,
                    custody_retained=recovery_attention.custody_retained,
                    retry_condition=recovery_attention.retry_condition,
                )
                if recovery_attention is not None
                else None
            ),
            integration_attention=(
                DeliveryOperatorIntegrationAttentionResponse(
                    code=integration_attention.code,
                    disposition=integration_attention.disposition,
                    diagnostics=integration_attention.diagnostics,
                    retry_condition=integration_attention.retry_condition,
                )
                if integration_attention is not None
                else None
            ),
        )


class ResolvedDeliveryRequestResponse(_TargetProtocolModel):
    """Bounded response for one persisted request resolution."""

    change_id: ChangeId
    request: DeliveryRequest


class DeliveryAnswerResponse(_TargetProtocolModel):
    """Bounded response for one version-bound request answer."""

    change_id: ChangeId
    kind: DeliveryAnswerKind
    request: DeliveryRequest | None = None
    binding: OutcomeAuthorityBinding | None = None
    disposition: DeliveryChangeDispositionResolution | None = None
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_result(self) -> DeliveryAnswerResponse:
        if self.kind is DeliveryAnswerKind.REQUEST and self.request is None:
            message = "request answer responses require the resolved request"
            raise ValueError(message)
        if self.kind is DeliveryAnswerKind.BLOCK and self.binding is None:
            message = "block answer responses require the cleared binding"
            raise ValueError(message)
        if self.kind is DeliveryAnswerKind.DISPOSITION and self.disposition is None:
            message = "disposition answer responses require the resolution receipt"
            raise ValueError(message)
        return self


class PutDesignResponse(_TargetProtocolModel):
    """Bounded response for one authored Design package write or replay."""

    change_id: ChangeId
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_root: str = Field(min_length=1)
    manifest: DesignPackageManifest
    replayed: bool

    @classmethod
    def from_result(cls, result: DesignPackageResult) -> PutDesignResponse:
        """Project one core Design package result into the strict MCP response."""
        return cls(
            change_id=result.change_id,
            package_id=result.package_id,
            package_root=str(result.package_root),
            manifest=result.manifest,
            replayed=result.replayed,
        )


class SetChangeIntentResponse(_TargetProtocolModel):
    """Bounded response for one applied Change lifecycle intent."""

    change_id: ChangeId
    kind: DeliveryChangeIntentKind
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt: DeliveryChangeDeferral | DeliveryChangeAbandonment

    @classmethod
    def from_result(cls, result: DeliveryChangeIntentResult) -> SetChangeIntentResponse:
        """Project one core intent result into the strict MCP response."""
        return cls(
            change_id=result.change_id,
            kind=result.kind,
            frontier_digest=result.frontier_digest,
            receipt=result.receipt,
        )


class SubmitResultResponse(_TargetProtocolModel):
    """Bounded response for one promoted Builder result."""

    kind: Literal["submitted"] = "submitted"
    change_id: ChangeId
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result_id: str = Field(min_length=1)
    binding: OutcomeAuthorityBinding

    @classmethod
    def from_result(cls, result: DeliveryResultSubmissionResult) -> SubmitResultResponse:
        """Project one core submission result into the strict MCP response."""
        return cls(
            kind=result.kind,
            change_id=result.change_id,
            outcome_id=result.outcome_id,
            claim_id=result.claim_id,
            result_id=result.result_id,
            binding=result.binding,
        )


class ClearedDeliveryBlockResponse(_TargetProtocolModel):
    """Bounded response for one cleared requestless block."""

    change_id: ChangeId
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    block: DeliveryBlock


class AdministrativeMovePreviewResponse(_TargetProtocolModel):
    """Read-only invalidation preview bound to one frontier version."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage
    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    invalidated_outcome_ids: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def from_preview(cls, preview: AdministrativeDeliveryMovePreview) -> AdministrativeMovePreviewResponse:
        """Project one domain preview into the MCP contract."""
        return cls(**preview.model_dump())


class AdministrativeMoveResponse(_TargetProtocolModel):
    """Persisted operator movement and its invalidated dependent closure."""

    move: DeliveryOperatorMove
    invalidated_outcome_ids: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def from_result(cls, result: AdministrativeDeliveryMoveResult) -> AdministrativeMoveResponse:
        """Project one domain movement result into the MCP contract."""
        return cls(**result.model_dump())


class DeliveryPublicationSupersessionResponse(_TargetProtocolModel):
    """MCP response for one application-bound publication successor."""

    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    predecessor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_supersession: ChangeBranchSupersessionReceipt
    provider_supersession: DraftPullRequestSupersessionReceipt
    publication_history: DeliveryChangePublicationHistory

    @classmethod
    def from_receipt(
        cls,
        receipt: DeliveryChangePublicationSupersessionReceipt,
    ) -> DeliveryPublicationSupersessionResponse:
        """Project one application receipt into the MCP response contract."""
        return cls(
            receipt_id=receipt.receipt_id,
            operation_id=receipt.operation_id,
            change_id=receipt.change_id,
            predecessor_publication_id=receipt.predecessor_publication_id,
            successor_publication_id=receipt.successor_publication_id,
            git_supersession=receipt.git_supersession,
            provider_supersession=receipt.provider_supersession,
            publication_history=receipt.publication_history,
        )


class ChangeTargetSyncResponse(_TargetProtocolModel):
    """MCP response for one exact target synchronization receipt."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    target_branch: str = Field(min_length=1)
    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_commit: bool
    review_required: bool = False

    @classmethod
    def from_receipt(cls, receipt: ChangeTargetSyncReceipt) -> ChangeTargetSyncResponse:
        """Project one domain sync receipt into the transport contract."""
        return cls(
            receipt_id=receipt.receipt_id,
            operation_id=receipt.operation_id,
            change_id=receipt.change_id,
            target_branch=receipt.integration_target,
            expected_target=receipt.expected_target,
            target_head=receipt.target_head,
            change_head_before=receipt.change_head_before,
            merged_head=receipt.merged_head,
            merge_commit=receipt.merge_commit,
            review_required=receipt.review_required,
        )


class TargetSyncPublicationRepairResponse(_TargetProtocolModel):
    """MCP response for one exact target-sync publication repair."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    target_sync_operation_id: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    repaired_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    review_required: Literal[True]

    @classmethod
    def from_receipt(
        cls,
        receipt: DeliveryTargetSyncRepairReceipt,
    ) -> TargetSyncPublicationRepairResponse:
        """Project one target-sync repair receipt into the MCP contract."""
        return cls(**receipt.model_dump())


class DeliveryStateSnapshotRepairResponse(_TargetProtocolModel):
    """MCP response for one exact Delivery-state frontier repair."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    local_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_receipt(
        cls,
        receipt: DeliveryStateSnapshotRepairReceipt,
    ) -> DeliveryStateSnapshotRepairResponse:
        """Project one Delivery-state repair receipt into the MCP contract."""
        return cls(**receipt.model_dump())


class QuarantinedSnapshotRepairProposalResponse(_TargetProtocolModel):
    """MCP proposal for one exact quarantined remote snapshot repair."""

    change_id: ChangeId
    diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"]
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requires_confirmation: Literal[True] = True
    consequence: str = Field(min_length=1)

    @classmethod
    def from_proposal(
        cls,
        proposal: DeliveryQuarantinedSnapshotRepairProposal,
    ) -> QuarantinedSnapshotRepairProposalResponse:
        """Project one core repair proposal into the strict MCP contract."""
        return cls(**proposal.model_dump())


class QuarantinedSnapshotRepairResponse(_TargetProtocolModel):
    """MCP receipt for one exact quarantined remote snapshot repair."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    invalid_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"]

    @classmethod
    def from_receipt(
        cls,
        receipt: DeliveryQuarantinedSnapshotRepairReceipt,
    ) -> QuarantinedSnapshotRepairResponse:
        """Project one core quarantined-snapshot repair receipt."""
        return cls(**receipt.model_dump())


class StrandedFrontierRepairResponse(_TargetProtocolModel):
    """MCP receipt for one exact local frontier provenance repair."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    request_id: str = Field(min_length=1)
    previous_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    preserved_frontier_path: str = Field(min_length=1)

    @classmethod
    def from_receipt(
        cls,
        receipt: DeliveryStrandedFrontierRepairReceipt,
    ) -> StrandedFrontierRepairResponse:
        """Project one core stranded-frontier repair receipt."""
        return cls(**receipt.model_dump())


class OutOfBandHeadRecoveryResponse(_TargetProtocolModel):
    """MCP response for one preserved out-of-band Change head recovery."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: str = Field(min_length=1)
    expected_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    observed_branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    preserved_ref: str = Field(min_length=1)
    preserved_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    restored_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(cls, receipt: OutOfBandHeadRecoveryReceipt) -> OutOfBandHeadRecoveryResponse:
        """Project one out-of-band recovery receipt into the transport contract."""
        return cls(
            **receipt.model_dump(mode="json", exclude={"worktree_path"}),
            worktree_path=str(receipt.worktree_path),
        )


class ChangeExternalHeadAdoptionResponse(_TargetProtocolModel):
    """MCP response for one exact external Change-head adoption or observation receipt."""

    schema_version: int = 2
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    branch: str = Field(min_length=1)
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    adopted_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    provenance: Literal["fast-forward", "observed"]

    @classmethod
    def from_receipt(cls, receipt: ChangeExternalHeadAdoptionReceipt) -> ChangeExternalHeadAdoptionResponse:
        """Project one domain adoption receipt into the transport contract."""
        return cls(
            receipt_id=receipt.receipt_id,
            operation_id=receipt.operation_id,
            change_id=receipt.change_id,
            branch=receipt.branch,
            expected_head=receipt.expected_head,
            adopted_head=receipt.adopted_head,
            provenance=receipt.provenance,
        )


class ChangeExternalHeadPromotionResponse(_TargetProtocolModel):
    """MCP response for one exact external Change-head promotion receipt."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    branch: str = Field(min_length=1)
    adoption_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    promoted_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    provenance: Literal["explicit", "finalization"]

    @classmethod
    def from_receipt(cls, receipt: ChangeExternalHeadPromotionReceipt) -> ChangeExternalHeadPromotionResponse:
        """Project one domain promotion receipt into the transport contract."""
        return cls(**receipt.model_dump())


class ChangeTargetSyncAbortResponse(_TargetProtocolModel):
    """MCP response for one exact target-sync abort receipt."""

    schema_version: int = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    restored_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(cls, receipt: ChangeTargetSyncAbortReceipt) -> ChangeTargetSyncAbortResponse:
        """Project one domain abort receipt into the transport contract."""
        return cls(**receipt.model_dump())


class TransitionDeliveryParams(ChangeParams):
    """Validate one worker-owned mechanical transition."""

    transition: DeliveryTransition


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
    DeliveryAdmissionRequest,
    BeforeValidator(partial(_parse_json_model, DeliveryAdmissionRequest)),
]
type ChangeRequest = Annotated[ChangeParams, BeforeValidator(partial(_parse_json_model, ChangeParams))]
type AnswerRequest = Annotated[AnswerParams, BeforeValidator(partial(_parse_json_model, AnswerParams))]
type PutDesignRequest = Annotated[
    PutDesignParams,
    BeforeValidator(partial(_parse_json_model, PutDesignParams)),
]
type SetChangeIntentRequest = Annotated[
    SetChangeIntentParams,
    BeforeValidator(partial(_parse_json_model, SetChangeIntentParams)),
]
type SubmitResultRequest = Annotated[
    SubmitResultParams,
    BeforeValidator(partial(_parse_json_model, SubmitResultParams)),
]
type OperatorContextRequest = Annotated[
    OperatorContextParams,
    BeforeValidator(partial(_parse_json_model, OperatorContextParams)),
]
type RepairChangeRequest = Annotated[
    RepairChangeParams,
    BeforeValidator(partial(_parse_json_model, RepairChangeParams)),
]
type PreviewAdministrativeMoveRequest = Annotated[
    PreviewAdministrativeMoveParams,
    BeforeValidator(partial(_parse_json_model, PreviewAdministrativeMoveParams)),
]
type AdministrativeMoveRequest = Annotated[
    AdministrativeMoveParams,
    BeforeValidator(partial(_parse_json_model, AdministrativeMoveParams)),
]
type CleanupAbandonedChangeRequest = Annotated[
    CleanupAbandonedChangeParams,
    BeforeValidator(partial(_parse_json_model, CleanupAbandonedChangeParams)),
]
type CleanupAbandonedTargetSyncRequest = Annotated[
    CleanupAbandonedTargetSyncParams,
    BeforeValidator(partial(_parse_json_model, CleanupAbandonedTargetSyncParams)),
]
type CleanupCompletedChangeRequest = Annotated[
    CleanupCompletedChangeParams,
    BeforeValidator(partial(_parse_json_model, CleanupCompletedChangeParams)),
]
type RecoverChangeWorktreeRequest = Annotated[
    RecoverChangeWorktreeParams,
    BeforeValidator(partial(_parse_json_model, RecoverChangeWorktreeParams)),
]
type RecoverPublicationBaselineRequest = Annotated[
    RecoverPublicationBaselineParams,
    BeforeValidator(partial(_parse_json_model, RecoverPublicationBaselineParams)),
]
type ClaimContextRequest = Annotated[
    ClaimContextParams,
    BeforeValidator(partial(_parse_json_model, ClaimContextParams)),
]
type RecoverClaimRequest = Annotated[
    RecoverClaimParams,
    BeforeValidator(partial(_parse_json_model, RecoverClaimParams)),
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
type AcquireActionsRequest = Annotated[
    AcquireActionsParams,
    BeforeValidator(partial(_parse_json_model, AcquireActionsParams)),
]
type FinalizeDeliveryChangeRequest = Annotated[
    FinalizeDeliveryChangeParams,
    BeforeValidator(partial(_parse_json_model, FinalizeDeliveryChangeParams)),
]
type MarkChangeReadyRequest = Annotated[
    MarkChangePullRequestReady,
    BeforeValidator(partial(_parse_json_model, MarkChangePullRequestReady)),
]
type SupersedePublicationRequest = Annotated[
    SupersedePublicationParams,
    BeforeValidator(partial(_parse_json_model, SupersedePublicationParams)),
]
type TargetSyncRequest = Annotated[
    TargetSyncParams,
    BeforeValidator(partial(_parse_json_model, TargetSyncParams)),
]
type ExternalHeadAdoptionRequest = Annotated[
    ExternalHeadAdoptionParams,
    BeforeValidator(partial(_parse_json_model, ExternalHeadAdoptionParams)),
]
type ExternalHeadPromotionRequest = Annotated[
    ExternalHeadPromotionParams,
    BeforeValidator(partial(_parse_json_model, ExternalHeadPromotionParams)),
]
type TargetSyncConflictRequest = Annotated[
    TargetSyncConflictParams,
    BeforeValidator(partial(_parse_json_model, TargetSyncConflictParams)),
]
type RepairTargetSyncPublicationRequest = Annotated[
    RepairTargetSyncPublicationParams,
    BeforeValidator(partial(_parse_json_model, RepairTargetSyncPublicationParams)),
]
type RepairDeliveryStateSnapshotRequest = Annotated[
    RepairDeliveryStateSnapshotParams,
    BeforeValidator(partial(_parse_json_model, RepairDeliveryStateSnapshotParams)),
]
type RepairQuarantinedDeliveryStateSnapshotRequest = Annotated[
    RepairQuarantinedDeliveryStateSnapshotParams,
    BeforeValidator(partial(_parse_json_model, RepairQuarantinedDeliveryStateSnapshotParams)),
]
type RepairStrandedFrontierRequest = Annotated[
    RepairStrandedFrontierParams,
    BeforeValidator(partial(_parse_json_model, RepairStrandedFrontierParams)),
]
type RecoverOutOfBandHeadRequest = Annotated[
    RecoverOutOfBandHeadParams,
    BeforeValidator(partial(_parse_json_model, RecoverOutOfBandHeadParams)),
]
type PublishDeliveryPlanRequest = Annotated[
    PublishDeliveryPlanParams,
    BeforeValidator(partial(_parse_json_model, PublishDeliveryPlanParams)),
]
type RepairClaimContextRequest = Annotated[
    RepairClaimContextParams,
    BeforeValidator(partial(_parse_json_model, RepairClaimContextParams)),
]
type ReviseDesignSessionRequest = Annotated[
    ReviseDesignSessionParams,
    BeforeValidator(partial(_parse_json_model, ReviseDesignSessionParams)),
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
type WorkItemViewRequest = Annotated[
    WorkItemViewParams,
    BeforeValidator(partial(_parse_json_model, WorkItemViewParams)),
]


__all__ = [
    "AcquireActionsParams",
    "AcquireActionsRequest",
    "AdministrativeMoveParams",
    "AdministrativeMovePreviewResponse",
    "AdministrativeMoveRequest",
    "AdministrativeMoveResponse",
    "AdmitDeliveryChangeRequest",
    "AnswerParams",
    "AnswerRequest",
    "ChangeExternalHeadAdoptionResponse",
    "ChangeExternalHeadPromotionResponse",
    "ChangeParams",
    "ChangeRequest",
    "ChangeTargetSyncAbortResponse",
    "ChangeTargetSyncResponse",
    "ChangeWorktreeCleanupResponse",
    "ChangeWorktreeRecoveryResponse",
    "ClaimContextParams",
    "ClaimContextRequest",
    "CleanupAbandonedChangeParams",
    "CleanupAbandonedChangeRequest",
    "CleanupAbandonedTargetSyncParams",
    "CleanupAbandonedTargetSyncRequest",
    "CleanupCompletedChangeParams",
    "CleanupCompletedChangeRequest",
    "CompletedPageParams",
    "CompletedPageRequest",
    "CreateDesignSessionParams",
    "CreateDesignSessionRequest",
    "DeliveryAnswerResponse",
    "DeliveryHealthDiagnosticResponse",
    "DeliveryHealthResponse",
    "DeliveryOperatorClaimResponse",
    "DeliveryOperatorContextResponse",
    "DeliveryOperatorIntegrationAttentionResponse",
    "DeliveryOperatorRecoveryAttentionResponse",
    "DeliveryPlanPublication",
    "DeliveryPublicationSupersessionResponse",
    "DeliveryStartupConfig",
    "DeliveryStartupDiagnostic",
    "DeliveryStateSnapshotRepairResponse",
    "EmptyParams",
    "EmptyRequest",
    "ExternalHeadAdoptionParams",
    "ExternalHeadAdoptionRequest",
    "ExternalHeadPromotionParams",
    "ExternalHeadPromotionRequest",
    "FinalizeDeliveryChangeParams",
    "FinalizeDeliveryChangeRequest",
    "MarkChangeReadyRequest",
    "OperatorContextParams",
    "OperatorContextRequest",
    "OutOfBandHeadRecoveryResponse",
    "PreviewAdministrativeMoveParams",
    "PreviewAdministrativeMoveRequest",
    "PublishDeliveryPlanParams",
    "PublishDeliveryPlanRequest",
    "PutDesignParams",
    "PutDesignRequest",
    "PutDesignResponse",
    "QuarantinedSnapshotRepairProposalResponse",
    "QuarantinedSnapshotRepairResponse",
    "RecoverChangeWorktreeParams",
    "RecoverChangeWorktreeRequest",
    "RecoverClaimParams",
    "RecoverClaimRequest",
    "RecoverOutOfBandHeadParams",
    "RecoverOutOfBandHeadRequest",
    "RecoverPublicationBaselineParams",
    "RecoverPublicationBaselineRequest",
    "RepairChangeParams",
    "RepairChangeRequest",
    "RepairClaimContextParams",
    "RepairClaimContextRequest",
    "RepairDeliveryStateSnapshotParams",
    "RepairDeliveryStateSnapshotRequest",
    "RepairQuarantinedDeliveryStateSnapshotParams",
    "RepairStrandedFrontierParams",
    "RepairTargetSyncPublicationParams",
    "RepairTargetSyncPublicationRequest",
    "RetainedChangeWorktreeResponse",
    "ReviseDesignSessionParams",
    "ReviseDesignSessionRequest",
    "SearchCompletedParams",
    "SearchCompletedRequest",
    "SetChangeIntentParams",
    "SetChangeIntentRequest",
    "SetChangeIntentResponse",
    "ShowCompletedParams",
    "ShowCompletedRequest",
    "StrandedFrontierRepairResponse",
    "SupersedePublicationParams",
    "SupersedePublicationRequest",
    "TargetDiagnostic",
    "TargetSyncConflictParams",
    "TargetSyncConflictRequest",
    "TargetSyncParams",
    "TargetSyncPublicationRepairResponse",
    "TargetSyncRequest",
    "TransitionDeliveryParams",
    "TransitionDeliveryRequest",
    "WorkItemParams",
    "WorkItemRequest",
    "WorkItemViewParams",
    "WorkItemViewRequest",
]
