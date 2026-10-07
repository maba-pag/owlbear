"""Delivery application request, result, view and error models."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.acceptance import (
    CompletionReceipt,
)
from owlbear_delivery.acceptance_criteria import DeliveryAcceptanceCriterion
from owlbear_delivery.application_support import (
    _publication_identity,
)
from owlbear_delivery.change_publication import (
    ChangeBranchPublicationReceipt,
    ChangeBranchPublisher,
    ChangeBranchSupersessionReceipt,
)
from owlbear_delivery.change_workspace import (
    ChangeContinuationAction,
    ChangeCoordination,
    ChangeDesignPackageSnapshotReceipt,
    ChangeFinalizationAttempt,
    ChangePauseRequest,
    ChangeTargetSyncReceipt,
    ChangeWorkspaceManager,
    ChangeWorktreeAttentionCode,
    ChangeWriter,
    PortfolioCoordinator,
)
from owlbear_delivery.delivery_runtime import (
    BlockDelivery,
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryBuilderHandoffContext,
    DeliveryChangeAbandonment,
    DeliveryChangeDeferral,
    DeliveryChangeDispositionResolution,
    DeliveryChangePublicationHistory,
    DeliveryChangeStage,
    DeliveryCheckpointPublicationState,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryPendingCheckpoint,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryRequestResolution,
    DeliveryRetryDiagnostic,
    DeliveryReturnContext,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    ReturnDelivery,
    integration_attention_disposition,
)
from owlbear_delivery.draft_pull_request import (
    DraftPullRequestPublicationReceipt,
    DraftPullRequestPublisher,
    DraftPullRequestSupersessionReceipt,
    GeneratedPullRequestSummaryReceipt,
    PullRequestReadyReceipt,
)
from owlbear_delivery.evidence import (
    DeliveryContextRefusal,
    DeliveryCriterionCoverage,
    DeliveryEvidenceProjection,
    DeliveryFinalizationSemantics,
)
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
    DeliveryHealthStatus,
    DeliveryHealthView,
    PortfolioOperatingView,
)
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
)
from owlbear_delivery.recovery import (
    MAX_RETRY_HISTORY_ATTEMPTS,
    DeliveryRetryAttemptView,
    RecoveryEvidenceProvider,
    UnavailableRecoveryEvidenceProvider,
)
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryOutcome,
)
from owlbear_delivery.work_items import (
    ChangeGroupView,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    DeliveryReadinessReason,
    WorkItemCardView,
    WorkItemClaimView,
    WorkItemDetailView,
    WorkItemPublicationPhase,
    WorkItemRecoveryView,
)
from owlbear_delivery.worker_stall import (
    DEFAULT_WORKER_QUIET_PERIOD,
    describe_active_processes,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime, timedelta

    from owlbear_delivery.completed_history import (
        CompletedHistoryCatalog,
    )
    from owlbear_delivery.delivery_admission import (
        DeliveryAuthorityRegistry,
    )
    from owlbear_delivery.delivery_state import DeliveryStatePublicationReceipt, DeliveryStatePublisher
    from owlbear_delivery.design_package import (
        DesignPackageStore,
        VerifiedDesignPackage,
    )
    from owlbear_delivery.finalization_reports import (
        ProofAttemptStore,
    )
    from owlbear_delivery.worker_stall import WindowHostIdentity, WindowLivenessProbe, WorktreeProcessProbe


def _worker_stall_prompt(change_id: str, stall: _WorkerStall) -> str:
    if stall.active_processes:
        verb = "is" if len(stall.active_processes) == 1 else "are"
        wait = (
            f"{describe_active_processes(stall.active_processes)} {verb} still active in its worktree. Delivery "
            "settles the claim as a failed attempt during a later acquisition once they exit and the worktree stays "
            "unchanged for the quiet period"
        )
    elif stall.eligible_at is not None:
        wait = (
            "Delivery settles the claim as a failed attempt during the next acquisition after its worktree stays "
            "unchanged until next_eligible_at"
        )
    else:
        wait = (
            "Its worktree or processes cannot be observed safely. Delivery settles the claim as a failed attempt "
            "once they can be observed and the worktree stays unchanged for the quiet period"
        )
    return (
        f"/continue-change {change_id} The VS Code window that issued the active worker claim has closed. {wait}; "
        "do not edit the worktree or dispatch a replacement before then."
    )


def _held_finalizer_prompt(change_id: str) -> str:
    return (
        f"/continue-change {change_id} A Finalizer attempt holds this Change. If that exact Finalizer chat has "
        "stopped, confirm it when the continuation asks, or use Release in Cockpit; Delivery records a failed "
        "attempt once no process uses the worktree and it stays unchanged. While it may still run, do not edit "
        "the worktree or dispatch a replacement."
    )


def _target_sync_conflict_prompt(change_id: str) -> str:
    return (
        f"/resolve-target-conflict {change_id} Target synchronization stopped on a merge conflict that the "
        "Change worktree preserves. Resolve it there and record it with Delivery, or abort it; either exit "
        "releases the retained engine action. Do not edit Delivery state or start another synchronization."
    )


def _operator_claim(claim: DeliveryActiveClaim | None) -> DeliveryOperatorClaim | None:
    if claim is None:
        return None
    return DeliveryOperatorClaim(
        attempt_id=claim.attempt_id,
        claim_id=claim.claim_id,
        started_at=claim.started_at,
        worker_role=claim.worker_role,
        task_id=claim.task_id,
        owner_id=claim.owner_id,
    )


def _operator_recovery_attention(
    attention: DeliveryRecoveryAttention | None,
) -> DeliveryOperatorRecoveryAttention | None:
    if attention is None:
        return None
    return DeliveryOperatorRecoveryAttention(
        attempt_id=attention.attempt_id,
        claim_id=attention.claim_id,
        reason=attention.reason,
        custody_retained=attention.custody_retained,
        retry_condition=attention.retry_condition,
        diagnostic_transition=attention.diagnostic_transition,
    )


def _operator_integration_attention(
    attention: DeliveryIntegrationAttention | None,
) -> DeliveryOperatorIntegrationAttention | None:
    if attention is None:
        return None
    return DeliveryOperatorIntegrationAttention(
        code=attention.code,
        disposition=integration_attention_disposition(attention.code),
        diagnostics=attention.diagnostics,
        retry_condition=attention.retry_condition,
    )


class _ApplicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryRolePolicy(_ApplicationModel):
    """Worker and reviewer agents for one mechanical stage role."""

    worker_role: DeliveryWorkerRole
    worker_agent: str = Field(min_length=1)
    reviewer_agent: str = Field(min_length=1)


class DeliveryActionSelection(_ApplicationModel):
    """Fence one explicitly selected next Planner or Builder action."""

    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    expected_stage: Literal[DeliveryStage.PLANNING, DeliveryStage.IMPLEMENTATION]
    expected_task_id: str | None = Field(default=None, min_length=1)
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_source_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def _validate_task_selection(self) -> DeliveryActionSelection:
        if (self.expected_stage == DeliveryStage.IMPLEMENTATION) != (self.expected_task_id is not None):
            message = "only an Implementation selection requires the expected next task identity"
            raise ValueError(message)
        return self


class DeliveryLaunchPackage(_ApplicationModel):
    """Bounded identity and source locators for one named worker invocation."""

    change_id: str = Field(min_length=1)
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    task_id: str | None = None
    builder_handoff_context: DeliveryBuilderHandoffContext | None = None
    claim: DeliveryActiveClaim
    policy: DeliveryRolePolicy
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_root: Path
    worktree_path: Path
    branch: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer: ChangeWriter | None = None

    @model_validator(mode="after")
    def _validate_role_custody(self) -> DeliveryLaunchPackage:
        if self.policy.worker_role != self.claim.worker_role or self.task_id != self.claim.task_id:
            message = "launch policy and task identity must match the active claim"
            raise ValueError(message)
        if self.builder_handoff_context is not None:
            context = self.builder_handoff_context
            planner_handoff = (
                self.policy.worker_role == DeliveryWorkerRole.PLANNER
                and context.route == "same-outcome-planner"
                and self.task_id is None
                and self.writer is None
            )
            builder_handoff = (
                self.policy.worker_role == DeliveryWorkerRole.BUILDER
                and context.route == "same-task"
                and context.original_task_id == self.task_id
            )
            if context.outcome_id != self.outcome_id or not (planner_handoff or builder_handoff):
                message = "launch Builder handoff context must match its exact outcome and worker route"
                raise ValueError(message)
        if (self.claim.worker_role == DeliveryWorkerRole.BUILDER) != (self.writer is not None):
            message = "only Build launch packages carry writer custody"
            raise ValueError(message)
        if self.writer is not None and (
            self.writer.attempt_id != self.claim.attempt_id
            or self.writer.claim_id != self.claim.claim_id
            or self.writer.actor_id != self.claim.owner_id
            or self.writer.process_id != self.claim.process_id
        ):
            message = "writer custody must match the active claim"
            raise ValueError(message)
        return self


class DeliveryContinuationRequest(_ApplicationModel):
    """Acquire at most one supported action from an observed Change view."""

    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    expected_basis: DeliveryReadinessBasis
    capabilities: tuple[Literal["planner", "builder", "finalizer", "engine"], ...]
    host_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _validate_basis(self) -> DeliveryContinuationRequest:
        if self.expected_basis.contract_digest is None or self.expected_basis.frontier_digest is None:
            message = "continuation requires an observed contract and frontier"
            raise ValueError(message)
        if len(set(self.capabilities)) != len(self.capabilities):
            message = "continuation capabilities must be unique"
            raise ValueError(message)
        return self


DeliveryContinuationReason = (
    DeliveryReadinessReason
    | Literal[
        "host-capability-unavailable",
        "execution-capacity",
        "execution-occupancy-unavailable",
        "source-head-changed",
        "state-publication-reconciled",
        "state-publication-failed",
        "operation-in-progress",
        "publication-reconciliation-required",
        "readiness-changed",
        "source-unavailable",
        "repair-required",
        "engine-action-completed",
        "engine-action-incomplete",
        "engine-action-failed",
        "engine-action-interrupted",
        "engine-owner-unavailable",
        "merge-approval-required",
    ]
)


class DeliveryContinuationResult(_ApplicationModel):
    """One launch or a non-dispatching disposition; never a portfolio batch."""

    change_id: str = Field(min_length=1)
    kind: Literal[
        "acquired", "reconciled", "busy", "stale", "waiting", "human", "unsupported", "unavailable", "terminal"
    ]
    reason_code: DeliveryContinuationReason
    readiness: DeliveryReadiness
    failure: DeliveryAcquisitionFailure | None = None
    launch: DeliveryLaunchPackage | None = None
    finalization: DeliveryFinalizationLaunch | None = None
    engine_action: ChangeContinuationAction | None = None
    engine_result: DeliveryEngineActionResult | None = None

    @model_validator(mode="after")
    def _validate_launch(self) -> DeliveryContinuationResult:
        launches = sum(item is not None for item in (self.launch, self.finalization, self.engine_action))
        if launches != (1 if self.kind == "acquired" else 0):
            message = "only acquired continuation results carry a launch"
            raise ValueError(message)
        if self.launch is not None and self.launch.change_id != self.change_id:
            message = "continuation launch must belong to the selected Change"
            raise ValueError(message)
        if self.finalization is not None and self.finalization.context.change_id != self.change_id:
            message = "finalization launch must belong to the selected Change"
            raise ValueError(message)
        if self.failure is not None and (self.kind != "unavailable" or self.failure.change_id != self.change_id):
            message = "continuation failure requires an unavailable result for the selected Change"
            raise ValueError(message)
        if self.engine_action is not None and (
            self.engine_action.change_id != self.change_id or self.engine_action.finished_at is not None
        ):
            message = "engine action must belong to the selected Change"
            raise ValueError(message)
        if self.engine_result is not None and (
            self.engine_result.action.change_id != self.change_id or self.kind == "acquired"
        ):
            message = "engine result must belong to a non-acquired selected Change response"
            raise ValueError(message)
        if self.engine_result is not None:
            kinds = {"completed": "reconciled", "waiting": "human", "stale": "stale", "blocked": "unavailable"}
            # L2 (D5): a waiting acceptance result reports current readiness, not its persisted label.
            reason = (
                self.readiness.reason_code if self.engine_result.kind == "waiting" else self.engine_result.reason_code
            )
            if (
                self.kind != kinds[self.engine_result.kind]
                or self.reason_code != reason
                or self.failure != self.engine_result.failure
            ):
                message = "continuation must preserve the exact engine disposition and failure"
                raise ValueError(message)
        return self


class DeliveryAcquisitionFailure(_ApplicationModel):
    """Bounded fail-closed preparation result, optionally tied to a started claim."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str | None = None
    claim_id: str | None = None
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    retry_condition: str = Field(min_length=1)
    pre_effect_retryable: bool = False


class DeliveryIntegrationAttentionStatus(_ApplicationModel):
    """One non-retryable Integration attention exposed by acquisition."""

    change_id: str = Field(min_length=1)
    code: DeliveryIntegrationAttentionCode
    disposition: DeliveryIntegrationAttentionDisposition
    retry_condition: str = Field(min_length=1)


class DeliveryClaimRecoveryStatus(StrEnum):
    """Observable disposition of one exact-claim recovery request."""

    RECOVERED = "recovered"
    ATTENTION = "attention"


class DeliveryClaimRecoveryResult(_ApplicationModel):
    """Recovered claim state, isolated preservation evidence, or retained repair attention."""

    status: DeliveryClaimRecoveryStatus
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    preserved_ref: str | None = None
    quarantine_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    quarantine_ref: str | None = None
    attention: DeliveryRecoveryAttention | None = None

    @model_validator(mode="after")
    def _validate_disposition(self) -> DeliveryClaimRecoveryResult:
        if (self.status == DeliveryClaimRecoveryStatus.ATTENTION) != (self.attention is not None):
            message = "only retained recovery requires repair attention"
            raise ValueError(message)
        if (self.quarantine_commit is None) != (self.quarantine_ref is None):
            message = "quarantine recovery evidence requires both commit and ref"
            raise ValueError(message)
        return self


class DeliveryRepairKind(StrEnum):
    """High-level repair proposal categories exposed by the application facade."""

    CONFIRM_LOST_WORKER = "confirm-lost-worker"


class DeliveryRepairProposal(_ApplicationModel):
    """One versioned repair choice that can be applied without caller-selected internals."""

    proposal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: DeliveryRepairKind
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary: str = Field(min_length=1)
    consequence: str = Field(min_length=1)

    @classmethod
    def create(  # noqa: PLR0913 - proposal identity binds each exact repair input.
        cls,
        *,
        kind: DeliveryRepairKind,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        expected_frontier_digest: str,
        summary: str,
        consequence: str,
    ) -> DeliveryRepairProposal:
        """Create a stable proposal identity from the exact repair evidence."""
        values = {
            "kind": kind,
            "change_id": change_id,
            "outcome_id": outcome_id,
            "attempt_id": attempt_id,
            "claim_id": claim_id,
            "expected_frontier_digest": expected_frontier_digest,
            "summary": summary,
            "consequence": consequence,
        }
        proposal_id = hashlib.sha256(
            json.dumps(
                {key: value.value if isinstance(value, StrEnum) else value for key, value in values.items()},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return cls(proposal_id=proposal_id, **values)


class DeliveryRepairResult(_ApplicationModel):
    """One repair diagnosis or the exact recovery result of an applied proposal."""

    change_id: str = Field(min_length=1)
    proposal: DeliveryRepairProposal | None = None
    recovery: DeliveryClaimRecoveryResult | None = None

    @model_validator(mode="after")
    def _validate_result(self) -> DeliveryRepairResult:
        if self.proposal is None and self.recovery is None:
            return self
        if self.proposal is not None and self.recovery is not None:
            message = "repair result cannot contain both proposal and recovery"
            raise ValueError(message)
        if self.proposal is not None and self.proposal.change_id != self.change_id:
            message = "repair proposal does not match its Change"
            raise ValueError(message)
        if self.recovery is not None and self.recovery.change_id != self.change_id:
            message = "repair recovery does not match its Change"
            raise ValueError(message)
        return self


class DeliveryUnresolvedOutcome(_ApplicationModel):
    """Bounded unresolved outcome evidence retained alongside Change detail."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    card: WorkItemCardView
    requests: tuple[DeliveryRequest, ...] = ()
    block: DeliveryBlock | None = None
    active_claim: WorkItemClaimView | None = None
    recovery_attention: WorkItemRecoveryView | None = None
    builder_handoff: DeliveryBuilderHandoffContext | None = None


class DeliveryChangeView(_ApplicationModel):
    """One coherent semantic, health, and repair view for a Delivery Change."""

    change_id: str = Field(min_length=1)
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    detail: WorkItemDetailView
    health: DeliveryHealthView
    repair: DeliveryRepairResult | None = None
    unresolved_outcomes: tuple[DeliveryUnresolvedOutcome, ...] = ()
    kind: Literal["available"] = "available"
    readiness: DeliveryReadiness
    finalization_attempt: ChangeFinalizationAttempt | None = None
    continuation_action: ChangeContinuationAction | None = None
    pause_requested: bool = False
    evidence: DeliveryEvidenceProjection | None = None


class DeliveryUnavailableChangeView(_ApplicationModel):
    """Known Change whose canonical runtime authority could not be composed."""

    kind: Literal["unavailable"] = "unavailable"
    change_id: str = Field(min_length=1)
    title: str | None = None
    diagnostics: tuple[Literal["runtime-unavailable", "coordination-unavailable"], ...] = ("runtime-unavailable",)
    coordination_status: Literal["missing", "unreadable"] | None = None
    readiness: DeliveryReadiness


class _FinalizationReadUnavailableError(RuntimeError):
    def __init__(self, readiness: DeliveryReadiness) -> None:
        self.readiness = readiness
        super().__init__(readiness.reason_code)


class DeliveryResultSubmission(_ApplicationModel):
    """One claim-bound Builder result submitted for publication and promotion."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result: DeliveryTaskResult


class DeliveryResultSubmissionResult(_ApplicationModel):
    """The promoted Builder result and its current runtime binding."""

    kind: Literal["submitted"] = "submitted"
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result_id: str = Field(min_length=1)
    binding: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_binding(self) -> DeliveryResultSubmissionResult:
        if self.binding.outcome_id != self.outcome_id:
            message = "submitted result binding does not match its Outcome"
            raise ValueError(message)
        return self


class DeliveryDesignPut(_ApplicationModel):
    """One create-or-CAS-revise request for authored Design bytes."""

    change_id: str = Field(min_length=1)
    intent_bytes: bytes
    design_bytes: bytes
    expected_package_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class DeliveryChangeIntentKind(StrEnum):
    """User-directed Change lifecycle intent categories."""

    DEFER = "defer"
    RESUME = "resume"
    ABANDON = "abandon"


class DeliveryChangeIntent(_ApplicationModel):
    """One version-bound request to pause, resume, or abandon a Change."""

    change_id: str = Field(min_length=1)
    kind: DeliveryChangeIntentKind
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_reason(self) -> DeliveryChangeIntent:
        if self.kind is DeliveryChangeIntentKind.RESUME:
            if self.reason is not None:
                message = "resume intent does not accept a reason"
                raise ValueError(message)
        elif self.reason is None or not self.reason.strip():
            message = "defer and abandon intents require a reason"
            raise ValueError(message)
        return self


class DeliveryChangeIntentResult(_ApplicationModel):
    """The applied Change intent receipt and resulting frontier version."""

    change_id: str = Field(min_length=1)
    kind: DeliveryChangeIntentKind
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt: DeliveryChangeDeferral | DeliveryChangeAbandonment | ChangePauseRequest

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryChangeIntentResult:
        if self.receipt.change_id != self.change_id:
            message = "Change intent receipt does not match its Change"
            raise ValueError(message)
        if self.kind is DeliveryChangeIntentKind.ABANDON and not isinstance(self.receipt, DeliveryChangeAbandonment):
            message = "abandon intent requires an abandonment receipt"
            raise ValueError(message)
        if self.kind is not DeliveryChangeIntentKind.ABANDON and not isinstance(
            self.receipt, DeliveryChangeDeferral | ChangePauseRequest
        ):
            message = "defer or resume intent requires a deferral receipt or Pause request"
            raise ValueError(message)
        return self


class DeliveryAnswerKind(StrEnum):
    """High-level user answer targets currently supported by Delivery."""

    REQUEST = "request"
    BLOCK = "block"
    DISPOSITION = "disposition"


class DeliveryAnswer(_ApplicationModel):
    """One version-bound answer to a retained request or requestless block."""

    change_id: str = Field(min_length=1)
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
    def _validate_target(self) -> DeliveryAnswer:
        if self.kind is DeliveryAnswerKind.REQUEST:
            if self.request_id is None or self.resolution is None:
                message = "request answers require request identity and resolution"
                raise ValueError(message)
            if any((self.outcome_id, self.block_id, self.operator_note)) or self.locators:
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
            if self.request_id is not None or self.resolution is not None:
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


class DeliveryAnswerResult(_ApplicationModel):
    """The answered authority and frontier version after an accepted answer."""

    change_id: str = Field(min_length=1)
    kind: DeliveryAnswerKind
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: DeliveryRequest | None = None
    binding: OutcomeAuthorityBinding | None = None
    disposition: DeliveryChangeDispositionResolution | None = None

    @model_validator(mode="after")
    def _validate_result(self) -> DeliveryAnswerResult:
        if self.kind is DeliveryAnswerKind.REQUEST and self.request is None:
            message = "request answer results require the resolved request"
            raise ValueError(message)
        if self.kind is DeliveryAnswerKind.BLOCK and self.binding is None:
            message = "block answer results require the cleared binding"
            raise ValueError(message)
        if self.kind is DeliveryAnswerKind.DISPOSITION and self.disposition is None:
            message = "disposition answer results require the resolution receipt"
            raise ValueError(message)
        return self


class DeliveryAcquisitionResult(_ApplicationModel):
    """Launchable task claims plus typed attention from one refresh."""

    launch_packages: tuple[DeliveryLaunchPackage, ...]
    integration_attention: tuple[DeliveryIntegrationAttentionStatus, ...] = ()
    recoveries: tuple[DeliveryClaimRecoveryResult, ...] = ()
    failures: tuple[DeliveryAcquisitionFailure, ...] = ()
    health_hint: str | None = Field(default=None, max_length=240)


class DeliveryPlanContext(_ApplicationModel):
    """Plan authority and current same-outcome successor context."""

    launch: DeliveryLaunchPackage
    outcome: DeliveryOutcome
    commitments: tuple[DeliveryCommitment, ...]
    requests: tuple[DeliveryRequest, ...]
    return_context: DeliveryReturnContext | None = None
    acceptance: tuple[DeliveryAcceptanceCriterion, ...] = ()
    # A published plan must repeat these completed task definitions unchanged.
    retained_tasks: tuple[DeliveryTaskDefinition, ...] = ()
    coverage: tuple[DeliveryCriterionCoverage, ...] = ()


class DeliveryBuildContext(_ApplicationModel):
    """Build authority, predecessor results, and current source coordination."""

    launch: DeliveryLaunchPackage
    task: DeliveryTaskDefinition
    task_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    commitments: tuple[DeliveryCommitment, ...]
    predecessor_results: tuple[DeliveryTaskResult, ...]
    requests: tuple[DeliveryRequest, ...]
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryRecoveryAttention | None = None
    prior_attempts: tuple[DeliveryRetryAttemptView, ...] = Field(default=(), max_length=MAX_RETRY_HISTORY_ATTEMPTS)
    acceptance: tuple[DeliveryAcceptanceCriterion, ...] = ()


class DeliveryFinalizationContext(_ApplicationModel):
    """Engine-resolved read context for exact Change finalization."""

    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    change_head: str | None = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_phase: WorkItemPublicationPhase
    ready_for_finalization: bool
    readiness_diagnostics: tuple[str, ...]
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finalized_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    finalization_invalidation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    readiness: DeliveryReadiness
    semantics: DeliveryFinalizationSemantics | None = Field(default=None, exclude_if=lambda value: value is None)
    semantics_refusal: DeliveryContextRefusal | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def _validate_semantics(self) -> DeliveryFinalizationContext:
        if self.semantics is not None and self.semantics_refusal is not None:
            message = "finalization context holds complete semantics or their refusal, never both"
            raise ValueError(message)
        return self


class DeliveryFinalizationLaunch(_ApplicationModel):
    """Finalizer handoff; use the attempt identity as the finalization operation ID."""

    attempt: ChangeFinalizationAttempt
    context: DeliveryFinalizationContext


class DeliveryRetainedWorktreeCleanupBlockReason(StrEnum):
    """Why one retained Change worktree cannot yet be cleaned up."""

    ORPHAN = "orphan"
    COMPLETION_STATE_INCONSISTENT = "completion-state-inconsistent"
    NONTERMINAL = "nonterminal"
    ACTIVE_WRITER = "active-writer"
    ACTIVE_PUBLICATION_LEASE = "active-publication-lease"
    WORKTREE_ATTENTION = "worktree-attention"


class DeliveryRetainedChangeWorktree(_ApplicationModel):
    """Bounded retained-worktree inventory row for Delivery consumers."""

    change_id: str = Field(min_length=1)
    worktree_path: Path
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


class DeliveryChangeWorktreeCleanup(_ApplicationModel):
    """Application receipt for one exact managed Change worktree cleanup."""

    cleanup_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class DeliveryChangeWorktreeRecovery(_ApplicationModel):
    """Application receipt for one exact managed Change worktree recovery."""

    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    recovery_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class DeliveryOperatorClaim(_ApplicationModel):
    """Bounded active-claim identity required for explicit operator recovery."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None
    owner_id: str | None = None


class DeliveryOperatorRecoveryAttention(_ApplicationModel):
    """Recovery evidence without workspace or Git custody internals."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    custody_retained: bool
    retry_condition: str = Field(min_length=1)
    diagnostic_transition: Annotated[BlockDelivery | ReturnDelivery, Field(discriminator="action")] | None = None


class DeliveryOperatorIntegrationAttention(_ApplicationModel):
    """Integration attention without raw Git boundary identities."""

    code: DeliveryIntegrationAttentionCode
    disposition: DeliveryIntegrationAttentionDisposition
    diagnostics: tuple[str, ...] = Field(min_length=1)
    retry_condition: str = Field(min_length=1)


class DeliveryOperatorContext(_ApplicationModel):
    """Current bounded state consumed by user-owned Delivery controls."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(min_length=1)
    stage: DeliveryStage
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()
    active_claim: DeliveryOperatorClaim | None = None
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryOperatorRecoveryAttention | None = None
    retry_diagnostic: DeliveryRetryDiagnostic | None = None
    integration_attention: DeliveryOperatorIntegrationAttention | None = None
    evidence: DeliveryEvidenceProjection | None = None


class DeliveryIntegrationRepairRecoveryResult(_ApplicationModel):
    """Recovered exact Integration repair claim and preserved commit evidence."""

    status: Literal[DeliveryClaimRecoveryStatus.RECOVERED] = DeliveryClaimRecoveryStatus.RECOVERED
    change_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class DeliveryTargetSyncRepairReceipt(_ApplicationModel):
    """Evidence that one target-sync head and its portable state were reconciled."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    target_sync_operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    target_branch: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    repaired_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    review_required: Literal[True] = True

    @classmethod
    def create(  # noqa: PLR0913 - receipt identity binds each exact repair input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        target_sync_operation_id: str,
        target_branch: str,
        target_head: str,
        expected_remote_head: str,
        repaired_head: str,
    ) -> DeliveryTargetSyncRepairReceipt:
        """Create deterministic evidence for one target-sync publication repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "target_sync_operation_id": target_sync_operation_id,
            "target_branch": target_branch,
            "target_head": target_head,
            "expected_remote_head": expected_remote_head,
            "repaired_head": repaired_head,
            "review_required": True,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryTargetSyncRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "target-sync publication repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryStateSnapshotRepairReceipt(_ApplicationModel):
    """Evidence that one quarantined local frontier successor was published."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    local_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        change_id: str,
        publication: DeliveryStatePublicationReceipt,
        local_frontier_digest: str,
    ) -> DeliveryStateSnapshotRepairReceipt:
        """Create deterministic evidence for one local frontier repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "snapshot_id": publication.snapshot_id,
            "published_head": publication.published_head,
            "local_frontier_digest": local_frontier_digest,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryStateSnapshotRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "Delivery-state snapshot repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryStrandedFrontierRepairReceipt(_ApplicationModel):
    """Evidence that one confirmed legacy request-provenance defect was repaired."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    previous_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    preserved_frontier_path: str = Field(min_length=1)

    @classmethod
    def create(  # noqa: PLR0913 - receipt identity binds each exact repair input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        request_id: str,
        previous_frontier_digest: str,
        frontier_digest: str,
        preserved_frontier_path: str,
    ) -> DeliveryStrandedFrontierRepairReceipt:
        """Create deterministic evidence for one frontier repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "request_id": request_id,
            "previous_frontier_digest": previous_frontier_digest,
            "frontier_digest": frontier_digest,
            "preserved_frontier_path": preserved_frontier_path,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryStrandedFrontierRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "stranded frontier repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryQuarantinedSnapshotRepairReceipt(_ApplicationModel):
    """Evidence that one quarantined remote snapshot was replaced under CAS."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    invalid_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"]

    @classmethod
    def create(  # noqa: PLR0913 - receipt identity binds each exact repair input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        invalid_snapshot_digest: str,
        expected_remote_head: str,
        publication: DeliveryStatePublicationReceipt,
        diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"],
    ) -> DeliveryQuarantinedSnapshotRepairReceipt:
        """Create deterministic evidence for one remote snapshot repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "invalid_snapshot_digest": invalid_snapshot_digest,
            "expected_remote_head": expected_remote_head,
            "snapshot_id": publication.snapshot_id,
            "published_head": publication.published_head,
            "diagnostic_code": diagnostic_code,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryQuarantinedSnapshotRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "quarantined snapshot repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryQuarantinedSnapshotRepairProposal(_ApplicationModel):
    """Typed confirmation boundary for one known invalid remote snapshot."""

    change_id: str = Field(min_length=1)
    diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"]
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requires_confirmation: Literal[True] = True
    consequence: str = Field(min_length=1)


class PortfolioApplicationError(RuntimeError):
    """Portfolio preparation or scoped context validation failed closed."""

    code = "ERR_DELIVERY_PORTFOLIO"


class _PreEffectReadyObservationError(PublicationProviderError):
    """Retry-safe provider read failure before the mark-ready write boundary."""

    __slots__ = ()


class DeliveryCapacityWaitingError(DeliveryRuntimeConflictError):
    """Selected work can be retried when shared execution capacity is available."""

    code = "ERR_DELIVERY_CAPACITY_WAITING"


class DeliveryActionBusyError(DeliveryRuntimeConflictError):
    """A selected Change is temporarily locked by another operation."""

    code = "ERR_DELIVERY_ACTION_BUSY"


class DeliveryRuntimeReconciliationError(DeliveryRuntimeConflictError):
    """A runtime map entry changed or became unreadable during a read-side reconciliation."""

    code = "ERR_DELIVERY_RUNTIME_RECONCILIATION"
    retry_safe = True

    def __init__(self, change_id: str | None, detail: str) -> None:
        self.change_id = change_id
        target = f" for {change_id}" if change_id is not None else ""
        super().__init__(f"Delivery runtime reconciliation is required{target}: {detail}")


class RequiredPublicationChecksFailedError(PortfolioApplicationError):
    """A ready transition retained attention for failing provider-required checks."""

    code = "ERR_DELIVERY_REQUIRED_CHECKS_FAILED"

    def __init__(self, *, exact_head: str, observation_id: str, disposition_id: str) -> None:
        self.exact_head = exact_head
        self.observation_id = observation_id
        self.disposition_id = disposition_id
        super().__init__(
            f"required publication checks failed for exact head {exact_head}; "
            f"attention {disposition_id} retained from observation {observation_id}"
        )


class PortfolioReadView(_ApplicationModel):
    """Grouped work and operating facts derived from one portfolio capture."""

    groups: tuple[ChangeGroupView, ...]
    operating: PortfolioOperatingView
    health: DeliveryHealthView = DeliveryHealthView(status=DeliveryHealthStatus.HEALTHY)
    unavailable_changes: tuple[DeliveryUnavailableChangeView, ...] = ()


class DeliveryCheckpointReconciliationResult(_ApplicationModel):
    """One deterministic checkpoint reconciliation attempt and remaining queue state."""

    change_id: str = Field(min_length=1)
    attempted_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    branch_publication: ChangeBranchPublicationReceipt | None = None
    draft_pull_request: DraftPullRequestPublicationReceipt | None = None
    generated_summary: GeneratedPullRequestSummaryReceipt | None = None
    state: DeliveryCheckpointPublicationState
    reconciled: bool
    error_code: str | None = Field(default=None, min_length=1)
    error_detail: str | None = Field(default=None, min_length=1)


class ExecuteDeliveryChangeAction(_ApplicationModel):
    """Invoke only the engine-owned operation already selected for this Change."""

    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    operation_id: str = Field(pattern=r"^continue-[0-9a-f]{64}$")


class DeliveryEngineActionResult(_ApplicationModel):
    """Exact retained owner result; blocked effects never release custody."""

    action: ChangeContinuationAction
    kind: Literal["completed", "waiting", "stale", "blocked"]
    reason_code: Literal[
        "engine-action-completed",
        "engine-action-incomplete",
        "engine-action-failed",
        "engine-action-interrupted",
        "readiness-changed",
        "merge-approval-required",
    ]
    failure: DeliveryAcquisitionFailure | None = None
    checkpoint: DeliveryCheckpointReconciliationResult | None = None
    checkpoint_snapshot: ChangeDesignPackageSnapshotReceipt | None = None
    target_sync: ChangeTargetSyncReceipt | None = None
    ready: PullRequestReadyReceipt | None = None
    acceptance: CompletionReceipt | None = None

    @model_validator(mode="after")
    def _validate_owner_result(self) -> DeliveryEngineActionResult:
        if self.action.finished_at is not None:
            message = "engine result must bind the original acquired action"
            raise ValueError(message)
        kinds = {
            "engine-action-completed": "completed",
            "engine-action-incomplete": "blocked",
            "engine-action-failed": "blocked",
            "engine-action-interrupted": "blocked",
            "readiness-changed": "stale",
            "merge-approval-required": "waiting",
        }
        if self.kind != kinds[self.reason_code]:
            message = "engine disposition must match its reason"
            raise ValueError(message)
        receipts = {
            "reconcile-checkpoint": self.checkpoint,
            "sync-target": self.target_sync,
            "mark-ready": self.ready,
            "observe-acceptance": self.acceptance,
        }
        if any(value is not None and key != self.action.kind for key, value in receipts.items()):
            message = "engine result must match its fixed owner"
            raise ValueError(message)
        receipt = receipts[self.action.kind]
        if self.kind == "completed" and (receipt is None or (self.checkpoint and not self.checkpoint.reconciled)):
            message = "completed engine action requires a successful exact owner receipt"
            raise ValueError(message)
        if receipt is not None and receipt.change_id != self.action.change_id:
            message = "engine receipt must match the selected Change"
            raise ValueError(message)
        if self.kind == "waiting" and self.action.kind != "observe-acceptance":
            message = "only acceptance observation can wait for merge approval"
            raise ValueError(message)
        if self.kind in {"waiting", "stale"} and receipt is not None:
            message = "unexecuted engine action cannot carry a successful receipt"
            raise ValueError(message)
        if self.reason_code == "engine-action-incomplete" and (self.checkpoint is None or self.checkpoint.reconciled):
            message = "incomplete engine action requires its pending checkpoint evidence"
            raise ValueError(message)
        self._validate_failure()
        self._validate_exact_receipts()
        return self

    def _validate_failure(self) -> None:
        if self.failure is not None and (
            self.kind != "blocked"
            or self.failure.change_id != self.action.change_id
            or self.failure.attempt_id != self.action.operation_id
        ):
            message = "engine failure must retain the blocked Change identity"
            raise ValueError(message)
        if self.reason_code in {"engine-action-failed", "engine-action-interrupted"} and self.failure is None:
            message = "failed engine action requires its retained failure"
            raise ValueError(message)
        if (
            self.failure is not None
            and self.failure.pre_effect_retryable
            and (self.action.kind != "mark-ready" or self.reason_code != "engine-action-failed")
        ):
            message = "pre-effect retry is limited to failed mark-ready read observations"
            raise ValueError(message)

    def _validate_exact_receipts(self) -> None:
        self._validate_checkpoint_receipt()
        if self.target_sync is not None and (
            self.target_sync.operation_id != self.action.operation_id
            or self.target_sync.expected_target != self.action.target_head
            or self.target_sync.change_head_before != self.action.exact_head
        ):
            message = "target sync result differs from the exact action"
            raise ValueError(message)
        if self.ready is not None and (
            self.ready.operation_id != self.action.operation_id
            or self.ready.head_sha != self.action.exact_head
            or self.ready.finalization_id != self.action.finalization_id
        ):
            message = "ready result differs from the exact action"
            raise ValueError(message)
        if self.acceptance is not None and (
            self.acceptance.finalized_change_head != self.action.exact_head
            or self.acceptance.finalization_receipt_id != self.action.finalization_id
        ):
            message = "acceptance result differs from the exact action"
            raise ValueError(message)

    def _validate_checkpoint_receipt(self) -> None:
        head = self.action.exact_head
        snapshot = self.checkpoint_snapshot
        if snapshot is not None:
            if self.checkpoint is None or snapshot.change_id != self.action.change_id or snapshot.previous_head != head:
                message = "checkpoint snapshot differs from the exact action"
                raise ValueError(message)
            head = snapshot.snapshot_head
        checkpoint = self.checkpoint
        if checkpoint is None:
            return
        if checkpoint.attempted_head not in {None, head}:
            message = "checkpoint result differs from the exact action"
            raise ValueError(message)
        if self.kind == "completed" and (
            checkpoint.state.published_head != head
            or checkpoint.state.change_id != self.action.change_id
            or checkpoint.state.pending_checkpoint is not None
            or checkpoint.branch_publication is None
            or checkpoint.generated_summary is None
            or checkpoint.branch_publication.published_head != head
            or checkpoint.generated_summary.head_sha != head
            or checkpoint.branch_publication.change_id != self.action.change_id
            or checkpoint.generated_summary.change_id != self.action.change_id
            or (
                checkpoint.draft_pull_request is not None
                and (
                    checkpoint.draft_pull_request.head_sha != head
                    or checkpoint.draft_pull_request.change_id != self.action.change_id
                )
            )
        ):
            message = "checkpoint result differs from the exact action or lacks observed publication receipts"
            raise ValueError(message)


class DeliveryAcceptanceReconciliationStatus(StrEnum):
    """Bounded outcome of one provider acceptance reconciliation attempt."""

    COMPLETED = "completed"
    WAITING = "waiting"
    HEAD_MOVED = "head-moved"
    ATTENTION = "attention"
    PROVIDER_UNAVAILABLE = "provider-unavailable"
    SKIPPED = "skipped"


class DeliveryAcceptanceReconciliationOutcome(_ApplicationModel):
    """Per-Change result that keeps a polling batch isolated."""

    change_id: str = Field(min_length=1)
    status: DeliveryAcceptanceReconciliationStatus
    code: str | None = Field(default=None, min_length=1)
    detail: str | None = Field(default=None, min_length=1)
    completion_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class _AcceptanceReconciliationCursor(_ApplicationModel):
    """Persisted next starting Change for bounded acceptance polling."""

    schema_version: Literal[1] = 1
    next_change_id: str | None = Field(default=None, min_length=1)


class DeliveryChangePublicationSupersessionReceipt(_ApplicationModel):
    """Bind one Git successor publication to its provider and runtime evidence."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    predecessor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_supersession: ChangeBranchSupersessionReceipt
    provider_supersession: DraftPullRequestSupersessionReceipt
    publication_history: DeliveryChangePublicationHistory

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        predecessor_publication_id: str,
        git_supersession: ChangeBranchSupersessionReceipt,
        provider_supersession: DraftPullRequestSupersessionReceipt,
        publication_history: DeliveryChangePublicationHistory,
    ) -> DeliveryChangePublicationSupersessionReceipt:
        """Create one content-addressed application supersession receipt."""
        change_id = provider_supersession.change_id
        payload = {
            "schema_version": 1,
            "operation_id": operation_id,
            "change_id": change_id,
            "predecessor_publication_id": predecessor_publication_id,
            "successor_publication_id": provider_supersession.successor_receipt_id,
            "git_supersession": git_supersession,
            "provider_supersession": provider_supersession,
            "publication_history": publication_history,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **payload)
        digest = hashlib.sha256(
            json.dumps(
                candidate.model_dump(mode="json", exclude={"receipt_id"}),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return cls(receipt_id=digest, **payload)

    @model_validator(mode="after")
    def _validate_binding(self) -> DeliveryChangePublicationSupersessionReceipt:
        git = self.git_supersession
        provider = self.provider_supersession
        if (
            git.operation_id != self.operation_id
            or git.change_id != self.change_id
            or provider.operation_id != self.operation_id
            or provider.change_id != self.change_id
            or provider.predecessor_receipt_id != self.predecessor_publication_id
            or provider.successor_receipt_id != self.successor_publication_id
            or git.predecessor_branch != provider.predecessor_branch
            or git.predecessor_head != provider.predecessor_head
            or git.successor_branch != provider.successor_branch
            or git.superseding_head != provider.superseding_head
        ):
            message = "publication supersession receipts do not share one exact successor"
            raise ValueError(message)
        if self.publication_history.current != _publication_identity(provider.successor_publication):
            message = "publication supersession history does not end at the provider successor"
            raise ValueError(message)
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != digest:
            message = "publication supersession receipt identity is invalid"
            raise ValueError(message)
        return self


class PortfolioApplicationConfig(_ApplicationModel):
    """Configured capacity, claim timeout, source root, and stage-role policy."""

    package_root: Path
    execution_capacity: int = Field(gt=0)
    claim_timeout_seconds: int = Field(default=60 * 60, gt=0)
    role_policies: tuple[DeliveryRolePolicy, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def _validate_roles(self) -> PortfolioApplicationConfig:
        roles = tuple(policy.worker_role for policy in self.role_policies)
        expected = {DeliveryWorkerRole.PLANNER, DeliveryWorkerRole.BUILDER}
        if set(roles) != expected or len(roles) != len(set(roles)):
            message = "role policy must define each live worker role once"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class PortfolioApplicationDependencies:
    """Existing state owners composed by the portfolio application service."""

    target_root: Path
    package_store: DesignPackageStore
    authority_registry: DeliveryAuthorityRegistry
    coordinator: PortfolioCoordinator
    workspace_manager: ChangeWorkspaceManager
    completed_history_catalog: CompletedHistoryCatalog | None = None
    delivery_state_publisher: DeliveryStatePublisher | None = None
    change_branch_publisher: ChangeBranchPublisher | None = None
    draft_pull_request_publisher: DraftPullRequestPublisher | None = None
    health_diagnostics: tuple[DeliveryHealthDiagnostic, ...] = ()
    recovery_evidence_provider: RecoveryEvidenceProvider = field(default_factory=UnavailableRecoveryEvidenceProvider)
    proof_attempt_store_factory: Callable[[str], ProofAttemptStore] | None = None
    issuer_window: WindowHostIdentity | None = None
    window_liveness_probe: WindowLivenessProbe | None = None
    worktree_process_probe: WorktreeProcessProbe | None = None
    worker_quiet_period: timedelta = DEFAULT_WORKER_QUIET_PERIOD


@dataclass(frozen=True)
class PortfolioApplicationHooks:
    """Nondeterministic identity and clock sources replaced only below public proof."""

    identity_factory: Callable[[], str]
    clock: Callable[[], str]


@dataclass(frozen=True)
class _Candidate:
    sort_key: tuple[int, int, int, str]
    change_id: str
    runtime: DeliveryRuntime
    binding: OutcomeAuthorityBinding
    task_id: str | None
    role: DeliveryWorkerRole


@dataclass(frozen=True)
class _WorkerStall:
    eligible_at: datetime | None
    quiet: bool
    active_processes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _PreparedSource:
    package: VerifiedDesignPackage
    coordination: ChangeCoordination
    source_head: str


@dataclass(frozen=True)
class _PreparedCheckpointHead:
    state: DeliveryCheckpointPublicationState
    pending: DeliveryPendingCheckpoint
    head: str
    first_checkpoint: bool
    finalization_invalidated: bool = False


@dataclass(frozen=True)
class _SupersessionPublishContext:
    change_id: str
    expected_publication_id: str
    operation_id: str
    predecessor: DraftPullRequestPublicationReceipt
    superseding_head: str
    target_branch: str


@dataclass(frozen=True)
class _AcceptanceReconciliationAuthority:
    exact_head: str
    ready: PullRequestReadyReceipt
    target_branch: str


@dataclass(frozen=True)
class _ReviewRepairAuthority:
    invalidation: DeliveryFinalizationInvalidationReceipt | None
    expected_finalization_id: str
    expected_head: str
    repository: str
    number: int
    node_id: str


# Forward references resolve only now; incomplete models fail bare serialization in adapters.
DeliveryContinuationResult.model_rebuild()
