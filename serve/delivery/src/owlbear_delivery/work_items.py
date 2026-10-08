"""Pure Work Item projections over one immutable schema-v2 Delivery snapshot."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.delivery_contract_discovery import contract_fingerprint
from owlbear_delivery.delivery_runtime import (
    BlockDelivery,
    DeliveryAcceptanceAttentionReason,
    DeliveryBlock,
    DeliveryChangeDisposition,
    DeliveryChangeDispositionKind,
    DeliveryFrontier,
    DeliveryOperatorMove,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryRetryDiagnostic,
    DeliveryReturnContext,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    ReturnDelivery,
    parse_delivery_frontier,
)
from owlbear_delivery.draft_pull_request import PublicationPullRequestObservationReceipt
from owlbear_delivery.evidence import DeliveryEvidenceProjection, build_evidence_projection
from owlbear_delivery.finalization_reports import FinalizationAttempt
from owlbear_delivery.merge_offer import MergeBlock, MergeBlockReason, MergeFacts, MergeOffer
from owlbear_delivery.recovery import MAX_RETRY_HISTORY_ATTEMPTS, DeliveryRetryAttemptView
from owlbear_delivery.runtime_receipts import is_builder_attempt_grant_block, is_builder_return_limit
from owlbear_delivery.target_contract import DeliveryCommitment, DeliveryContract, DeliveryDecision, DeliveryOutcome


class WorkItemStage(StrEnum):
    """User-facing progress stages."""

    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    COMPLETED = "completed"


class WorkItemScope(StrEnum):
    """Production Work Item scopes."""

    OUTCOME = "outcome"
    CHANGE_PUBLICATION = "change-publication"


class WorkItemNeed(StrEnum):
    """Condition requiring intervention or blocking progress."""

    YOU = "you"
    DEPENDENCY = "dependency"
    NONE = "none"


class WorkItemNextActor(StrEnum):
    """Who or what is expected to advance one work item next."""

    YOU = "you"
    AGENT = "agent"
    DEPENDENCY = "dependency"
    NONE = "none"


class WorkItemActivityState(StrEnum):
    """Current execution state independent from Needs."""

    IDLE = "idle"
    READY = "ready"
    WORKING = "working"


class WorkItemActionKind(StrEnum):
    """Typed operator action available from one Work Item."""

    NONE = "none"
    RESUME_DESIGN = "resume-design"
    ANSWER_REQUEST = "answer-request"
    CLEAR_BLOCK = "clear-block"
    GRANT_ATTEMPT = "grant-attempt"
    RECOVER_CLAIM = "recover-claim"
    FINALIZE = "finalize"
    RECONCILE_CHECKPOINT = "reconcile-checkpoint"
    SYNC_TARGET = "sync-target"
    MARK_READY = "mark-ready"
    OBSERVE_ACCEPTANCE = "observe-acceptance"
    RESOLVE_ATTENTION = "resolve-attention"
    ADOPT_EXTERNAL_HEAD = "adopt-external-head"
    RESUME_CHANGE = "resume-change"
    START_ORCHESTRATION = "start-orchestration"


class WorkItemProgressKind(StrEnum):
    """Scope-specific progress category."""

    TASKS = "tasks"
    DESIGN_RETURN = "design-return"
    PLAN = "plan"
    PUBLICATION = "publication"


class WorkItemChangeLifecycle(StrEnum):
    """Change-level lifecycle shown by the portfolio group."""

    IN_DELIVERY = "in-delivery"
    FINALIZATION = "finalization"
    PUBLICATION = "publication"
    AWAITING_MERGE = "awaiting-merge"
    ACCEPTANCE = "acceptance"
    DEFERRED = "deferred"
    ABANDONED = "abandoned"


class WorkItemPublicationPhase(StrEnum):
    """Durable Change publication phase derived from exact frontier receipts."""

    FINALIZATION_INVALIDATED = "finalization-invalidated"
    REVIEW_REPAIR = "review-repair"
    READY_FOR_FINALIZATION = "ready-for-finalization"
    CHECKPOINT_PENDING = "checkpoint-pending"
    PULL_REQUEST_DRAFT = "pull-request-draft"
    AWAITING_MERGE = "awaiting-merge"
    ACCEPTANCE_OBSERVED = "acceptance-observed"
    DEFERRED = "deferred"
    ABANDONED = "abandoned"


def resolve_publication_phase(frontier: DeliveryFrontier) -> WorkItemPublicationPhase:  # noqa: C901
    """Resolve publication phase from captured authority without inspecting a workspace."""
    if frontier.change_abandonment is not None:
        phase = WorkItemPublicationPhase.ABANDONED
    elif frontier.change_deferral is not None:
        phase = WorkItemPublicationPhase.DEFERRED
    elif (
        frontier.finalization_invalidation is not None and frontier.finalization_invalidation.reason == "review-repair"
    ):
        phase = WorkItemPublicationPhase.REVIEW_REPAIR
    elif frontier.finalization_invalidation is not None:
        phase = WorkItemPublicationPhase.FINALIZATION_INVALIDATED
    elif (
        frontier.target_sync_receipt is not None
        and frontier.target_sync_receipt.review_required
        and frontier.finalization is None
    ):
        phase = WorkItemPublicationPhase.READY_FOR_FINALIZATION
    elif frontier.pending_checkpoint is not None:
        phase = WorkItemPublicationPhase.CHECKPOINT_PENDING
    elif frontier.finalization is None:
        phase = WorkItemPublicationPhase.READY_FOR_FINALIZATION
    elif frontier.pending_checkpoint is not None or frontier.published_head != frontier.finalization.exact_head:
        phase = WorkItemPublicationPhase.CHECKPOINT_PENDING
    elif frontier.ready is None:
        phase = WorkItemPublicationPhase.PULL_REQUEST_DRAFT
    elif frontier.merged_pull_request_latch is None:
        phase = WorkItemPublicationPhase.AWAITING_MERGE
    else:
        phase = WorkItemPublicationPhase.ACCEPTANCE_OBSERVED
    return phase


class _ProjectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WorkItemProjection(_ProjectionModel):
    """One durable semantic identity with derived operational state."""

    work_item_id: str
    change_id: str
    scope: str
    title: str
    promise: str
    stage: WorkItemStage
    dependency_ready: bool
    commitment_ids: tuple[str, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    task_count: int = 0
    reviewed_task_count: int = 0
    next_action: str


class WorkItemDetail(_ProjectionModel):
    """Semantic detail kept one drill-down from the portfolio."""

    projection: WorkItemProjection
    acceptance: tuple[str, ...] = ()
    return_context: DeliveryReturnContext | None = None


class DeliveryPortfolioSnapshot(_ProjectionModel):
    """One exact contract and frontier read for portfolio projection."""

    contract: DeliveryContract
    frontier: DeliveryFrontier
    version: str = Field(pattern=r"^[0-9a-f]{64}$")
    publication_observation: PublicationPullRequestObservationReceipt | None = None
    # The last read of the published pull request failed, unlike "no publication" (D8).
    publication_unavailable: bool = False
    merge_facts: MergeFacts | None = None

    @classmethod
    def capture(
        cls,
        contract: DeliveryContract,
        frontier_bytes: bytes,
        publication_observation: PublicationPullRequestObservationReceipt | None = None,
        merge_facts: MergeFacts | None = None,
        *,
        publication_unavailable: bool = False,
    ) -> DeliveryPortfolioSnapshot:
        """Validate one frontier read and bind its exact content digest."""
        return cls(
            contract=contract,
            frontier=parse_delivery_frontier(frontier_bytes)[0],
            version=hashlib.sha256(frontier_bytes).hexdigest(),
            publication_observation=publication_observation,
            publication_unavailable=publication_unavailable,
            merge_facts=merge_facts,
        )

    @model_validator(mode="after")
    def _validate_bindings(self) -> DeliveryPortfolioSnapshot:
        contract_ids = tuple(outcome.outcome_id for outcome in self.contract.outcomes)
        binding_ids = tuple(binding.outcome_id for binding in self.frontier.bindings)
        if binding_ids != contract_ids:
            message = "Delivery snapshot bindings must match contract outcome order"
            raise ValueError(message)
        if (
            self.publication_observation is not None
            and self.publication_observation.change_id != self.contract.change_id
        ):
            message = "Delivery publication observation must match the contract Change"
            raise ValueError(message)
        return self


class WorkItemActivity(_ProjectionModel):
    """Bounded execution state shown independently from Needs and Action."""

    state: WorkItemActivityState
    worker_role: DeliveryWorkerRole | None = None
    started_at: str | None = None
    task_id: str | None = None


class WorkItemAction(_ProjectionModel):
    """One typed user action, if current authority permits it."""

    kind: WorkItemActionKind = WorkItemActionKind.NONE
    label: str | None = None
    command: str | None = None
    attention_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    expected_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    adopted_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class DeliveryReadinessBasis(_ProjectionModel):
    """Only trusted authority and workspace facts from one response capture."""

    contract_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    target_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    continuation_id: str | None = Field(default=None, pattern=r"^continue-[0-9a-f]{64}$")
    candidate_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    workspace_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    diagnostic_sequence: int | None = Field(default=None, ge=0)


DeliveryReadinessReason = Literal[
    "ready",
    "design-attention",
    "active-custody",
    "builder-transition-contained",
    "retry-transition-contained",
    "finalization-failed",
    "claim-activation-failed",
    "coordination-unavailable",
    "execution-occupancy-unavailable",
    "engine-action-pending",
    "engine-action-blocked",
    "engine-action-interrupted",
    "engine-action-failed",
    "engine-action-incomplete",
    "target-sync-required",
    "claim-custody-unreconciled",
    "runtime-unavailable",
    "dependency-wait",
    "request-action",
    "change-paused",
    "change-terminal",
    "outcome-complete",
    "task-incomplete",
    "workspace-inspection-failed",
    "workspace-dirty",
    "workspace-preflight-failed",
    "settled-attention-target-drift",
    "review-repair",
    "publication-wait",
    "checkpoint-pending",
    "report-store-unavailable",
    "retry-backoff",
    "retry-exhausted",
    "acceptance-wait",
    "retry-containment",
    "retry-ledger-unavailable",
    "worker-stall-wait",
    "merge-approval-required",
    "merge-checking",
    "merge-blocked",
    "checks-running",
    "provider-unavailable",
    "merge-in-progress",
    "merge-response-unknown",
]

DeliverySituation = Literal[
    "with-agent",
    "ready-for-next-step",
    "your-decision",
    "waiting-on-github",
    "waiting-on-delivery",
    "waiting-on-dependency",
    "retrying-automatically",
    "needs-attention",
    "pausing",
    "paused",
    "abandoned",
    "done",
]
DeliveryWaitingOn = Literal["you", "agent", "delivery", "github", "outcome", "change", "none"]
TargetSyncAvailability = Literal["required", "optional", "unavailable", "unnecessary"]


class DeliveryProgress(_ProjectionModel):
    """The one user-facing situation Delivery derives from final readiness; Cockpit reconstructs nothing."""

    situation: DeliverySituation
    headline: str = Field(min_length=1)
    waiting_on: DeliveryWaitingOn
    waiting_on_id: str | None = None
    since: str | None = None
    next_eligible_at: str | None = None
    # Change publication scope only: whether merging the latest target into the Change is offered.
    target_sync: TargetSyncAvailability | None = None


DeliveryIssuerState = Literal["alive", "gone", "unknown"]

ChangePauseUnavailableReason = Literal[
    "finalizer-custody",
    "step-in-progress",
    "recovery-required",
    "state-unavailable",
    "change-inactive",
    "pause-requested",
]


def _require_pause_consistency(available: bool, reason: ChangePauseUnavailableReason | None) -> None:  # noqa: FBT001
    if available != (reason is None):
        message = "Pause availability requires exactly one unavailable reason when Pause is refused"
        raise ValueError(message)


class MergeAttemptSummary(_ProjectionModel):
    """The one unsettled merge approval of a Change, with the pull request to check in GitHub (1.13)."""

    approval_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: Literal["intent", "released", "pending"]
    approved_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    pr_url: str = Field(min_length=1)
    released_at: str | None = None


class DeliveryReadiness(_ProjectionModel):
    """Application-owned eligibility for one supported action at a captured basis."""

    status: Literal["ready", "running", "waiting", "blocked", "unavailable", "complete"]
    operation: WorkItemActionKind | None = None
    executable: bool = False
    next_actor: WorkItemNextActor
    reason_code: DeliveryReadinessReason
    checks_state: Literal["not-run", "failed", "passed", "unknown"] = "not-run"
    basis: DeliveryReadinessBasis
    action: WorkItemAction | None = None
    last_attempt: FinalizationAttempt | None = None
    attempts: int = Field(default=0, ge=0)
    next_eligible_at: str | None = None
    stop_reason: str | None = None
    retry_history: tuple[DeliveryRetryAttemptView, ...] = Field(default=(), max_length=MAX_RETRY_HISTORY_ATTEMPTS)
    prompt: str | None = None
    progress: DeliveryProgress | None = None
    merge_offer: MergeOffer | None = None
    merge_block: MergeBlock | None = None
    merge_attempt: MergeAttemptSummary | None = None

    @model_validator(mode="after")
    def _validate_action(self) -> DeliveryReadiness:
        if self.executable != (self.action is not None):
            msg = "executable readiness requires exactly one supported action"
            raise ValueError(msg)
        if self.action is not None and (
            self.action.kind is WorkItemActionKind.NONE or self.action.kind != self.operation
        ):
            msg = "readiness action must match its supported operation"
            raise ValueError(msg)
        if self.executable and self.status != "ready":
            msg = "only ready operations can be executable"
            raise ValueError(msg)
        return self


class WorkItemProgress(_ProjectionModel):
    """Scope-applicable progress with an explicit noun."""

    kind: WorkItemProgressKind
    label: str = Field(min_length=1)
    done: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)


class WorkItemCardView(_ProjectionModel):
    """One dense portfolio row derived from a Delivery snapshot."""

    item_key: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    scope: WorkItemScope
    title: str = Field(min_length=1)
    stage: WorkItemStage | None
    publication_phase: WorkItemPublicationPhase | None = None
    needs: WorkItemNeed
    needs_headline: str | None = None
    next_actor: WorkItemNextActor
    next_step: str = Field(min_length=1)
    activity: WorkItemActivity
    progress: WorkItemProgress
    action: WorkItemAction
    readiness: DeliveryReadiness | None = None


class ChangeGroupView(_ProjectionModel):
    """One Change grouping and its admitted current Work Items."""

    change_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: WorkItemChangeLifecycle
    outcome_total: int = Field(ge=1)
    outcome_completed: int = Field(ge=0)
    items: tuple[WorkItemCardView, ...]
    progress: DeliveryProgress | None = None
    pause_available: bool = False
    pause_unavailable_reason: ChangePauseUnavailableReason | None = "state-unavailable"
    pause_requested: bool = False

    @model_validator(mode="after")
    def _validate_pause(self) -> ChangeGroupView:
        _require_pause_consistency(self.pause_available, self.pause_unavailable_reason)
        return self


class WorkItemClaimView(_ProjectionModel):
    """Exact claim identity and routing provenance, not authentication or liveness."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    continuation: bool
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None


class WorkItemHeldFinalizerView(_ProjectionModel):
    """Exact unfinished Finalizer attempt identity holding Change custody, not evidence that it still runs."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)


class WorkItemRecoveryView(_ProjectionModel):
    """Bounded recovery state without workspace custody paths."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    custody_retained: bool
    retry_condition: str = Field(min_length=1)
    diagnostic_transition: Annotated[BlockDelivery | ReturnDelivery, Field(discriminator="action")] | None = None


class WorkItemDependencyView(_ProjectionModel):
    """Named dependency and its current stage."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    title: str = Field(min_length=1)
    stage: WorkItemStage


class WorkItemTaskEvidence(_ProjectionModel):
    """Bounded task authority and reviewed result evidence."""

    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    result: str = Field(min_length=1)
    status: str = Field(pattern=r"^(pending|active|reviewed)$")
    completed_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    acceptance_observations: tuple[str, ...]
    proof_boundaries: tuple[str, ...]


class WorkItemWorktreeCleanupView(_ProjectionModel):
    """Bounded cleanup eligibility without exposing workspace custody details."""

    eligible: bool
    blocked_reason: str | None = None
    completion_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class WorkItemWorktreeRecoveryView(_ProjectionModel):
    """Bounded recovery authority for one missing Change worktree."""

    eligible: bool
    blocked_reason: str | None = None
    recovery_reviewed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class WorkItemTargetSyncView(_ProjectionModel):
    """Latest exact target synchronization evidence for the publication view."""

    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_commit: bool
    review_required: bool = False


class WorkItemTargetSyncConflictView(_ProjectionModel):
    """Exact preserved target-sync conflict identity for operator exits."""

    conflict_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    conflict_paths: tuple[str, ...] = ()


class WorkItemPublicationGenerationView(_ProjectionModel):
    """One ordered provider publication identity without provider receipt state."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class WorkItemPublicationView(_ProjectionModel):
    """Exact durable finalization, publication, and acceptance identities."""

    phase: WorkItemPublicationPhase
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finalized_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    ready_for_finalization: bool | None = None
    readiness_diagnostics: tuple[str, ...] = ()
    published_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    pending_checkpoint_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    pending_checkpoint_triggers: tuple[str, ...] = ()
    pending_checkpoint_attempt_count: int = Field(default=0, ge=0)
    pending_checkpoint_last_attempted_at: str | None = None
    pending_checkpoint_error_code: str | None = None
    pending_checkpoint_error_detail: str | None = None
    invalidated_expected_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    invalidated_observed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    repository: str | None = None
    pull_request_number: int | None = Field(default=None, gt=0)
    pull_request_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    mergeable: bool | None = None
    merge_state_status: str | None = Field(default=None, min_length=1)
    mergeability_observed_at: str | None = None
    accepted_merge_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    merged_at: str | None = None
    publication_generations: tuple[WorkItemPublicationGenerationView, ...] = ()
    attention: DeliveryChangeDisposition | None = None
    target_sync: WorkItemTargetSyncView | None = None
    target_sync_conflict: WorkItemTargetSyncConflictView | None = None
    worktree_cleanup: WorkItemWorktreeCleanupView | None = None
    worktree_recovery: WorkItemWorktreeRecoveryView | None = None


class WorkItemDetailView(_ProjectionModel):
    """Semantic and operator detail from the same portfolio snapshot."""

    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_title: str = Field(min_length=1)
    card: WorkItemCardView
    promise: str = Field(min_length=1)
    acceptance: tuple[str, ...] = ()
    commitments: tuple[DeliveryCommitment, ...] = ()
    decisions: tuple[DeliveryDecision, ...] = ()
    dependencies: tuple[WorkItemDependencyView, ...] = ()
    tasks: tuple[WorkItemTaskEvidence, ...] = ()
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()
    superseded_request_ids: tuple[str, ...] = ()
    active_claim: WorkItemClaimView | None = None
    held_finalizer: WorkItemHeldFinalizerView | None = None
    return_context: DeliveryReturnContext | None = None
    operator_moves: tuple[DeliveryOperatorMove, ...] = ()
    recovery_attention: WorkItemRecoveryView | None = None
    retry_diagnostic: DeliveryRetryDiagnostic | None = None
    publication: WorkItemPublicationView | None = None
    readiness: DeliveryReadiness | None = None
    change_progress: DeliveryProgress | None = None
    abandon_available: bool = False
    pause_available: bool = False
    pause_unavailable_reason: ChangePauseUnavailableReason | None = "state-unavailable"
    evidence: DeliveryEvidenceProjection | None = None
    revision_prompt: str | None = None

    @model_validator(mode="after")
    def _validate_pause(self) -> WorkItemDetailView:
        _require_pause_consistency(self.pause_available, self.pause_unavailable_reason)
        return self


_START_VERBS: dict[WorkItemActionKind, str] = {
    WorkItemActionKind.START_ORCHESTRATION: "continue this Change",
    WorkItemActionKind.FINALIZE: "finalize this Change",
    WorkItemActionKind.RECONCILE_CHECKPOINT: "publish the pending checkpoint",
    WorkItemActionKind.SYNC_TARGET: (
        "merge the latest target into this Change; a conflict stops there for you to resolve"
    ),
    WorkItemActionKind.MARK_READY: "mark the pull request ready",
    WorkItemActionKind.OBSERVE_ACCEPTANCE: "check the merge",
}
# One plain sentence per condition Delivery cannot continue from on its own; Details keep the specifics.
_ATTENTION_HEADLINES: dict[str, str] = {
    "builder-transition-contained": "A Builder handoff was refused and its custody is kept; inspect the Change.",
    "retry-transition-contained": "A worker retry was refused and its claim is kept; inspect the Change.",
    "finalization-failed": "Finalization failed and its custody is kept; inspect the Change.",
    "claim-activation-failed": "Delivery could not start the selected step; inspect the Change.",
    "coordination-unavailable": "Delivery cannot read who holds this Change; inspect the Change.",
    "execution-occupancy-unavailable": "Delivery cannot read which steps are running; inspect the Change.",
    "engine-action-blocked": "A retained Delivery step has records that cannot be verified; inspect the Change.",
    "engine-action-interrupted": "A Delivery step stopped without a recorded result; inspect the Change.",
    "engine-action-failed": "A Delivery step failed; inspect the Change.",
    "engine-action-incomplete": "A Delivery step left an unfinished checkpoint; inspect the Change.",
    "claim-custody-unreconciled": "A Builder claim's custody is unreconciled; inspect the Change.",
    "runtime-unavailable": "Delivery cannot read this Change; inspect the Change.",
    "workspace-inspection-failed": "Delivery cannot inspect this Change's worktree.",
    "workspace-dirty": "This Change's worktree has local changes; commit or remove them.",
    "workspace-preflight-failed": "This Change's worktree did not pass its preflight check.",
    "report-store-unavailable": "Delivery cannot read this Change's finalization reports.",
    "retry-exhausted": "Automatic retries are used up; inspect the Change to decide how to continue.",
    "retry-containment": "A previous attempt has no recorded outcome; inspect the Change.",
    "retry-ledger-unavailable": "Delivery cannot read its retry records; inspect the Change.",
    "settled-attention-target-drift": "The target moved after a failed verification; inspect the Change.",
    "merge-blocked": "GitHub reports the pull request cannot merge; open it to check.",
}
_ATTEMPT_GRANT_HEADLINE = "Automatic Builder retries are used up; grant one more attempt or inspect the Change."


def _is_attempt_grant(card: WorkItemCardView, readiness: DeliveryReadiness) -> bool:
    """Return whether exhausted Builder readiness offers the user-only attempt grant on this card."""
    return (
        readiness.reason_code == "retry-exhausted"
        and readiness.next_actor is WorkItemNextActor.YOU
        and card.action.kind is WorkItemActionKind.GRANT_ATTEMPT
    )


_GITHUB_WAITS: dict[str, str] = {
    "checks-running": "Required checks are running in GitHub.",
    "merge-checking": "GitHub is working out whether the pull request can merge.",
    "provider-unavailable": "GitHub could not be read; Delivery reads it again shortly.",
    "merge-in-progress": "GitHub is merging the pull request.",
}
# Awaiting-merge waits keep the card's merge-status check so Cockpit still observes a manual merge.
_MERGE_WAIT_REASONS = frozenset(
    {
        "merge-approval-required",
        "merge-checking",
        "merge-blocked",
        "checks-running",
        "provider-unavailable",
        "acceptance-wait",
        "merge-in-progress",
        "merge-response-unknown",
    }
)
# Blocks only Delivery's own merge has; the user can still merge in GitHub.
_MERGE_IN_GITHUB_BLOCKS = frozenset(
    {
        MergeBlockReason.CAPABILITY_UNAVAILABLE,
        MergeBlockReason.QUEUE_REQUIRED,
        MergeBlockReason.STACKED,
        MergeBlockReason.METHOD_NOT_ALLOWED,
    }
)
_MERGE_BLOCK_STEPS: dict[MergeBlockReason, str] = {
    MergeBlockReason.CONFLICTS: "The pull request has merge conflicts; synchronize the target before merging.",
    MergeBlockReason.BEHIND: "The pull request is behind its target; synchronize the target before merging.",
    MergeBlockReason.PROTECTION: "Branch protection blocks the merge; resolve it in GitHub, then merge there.",
    MergeBlockReason.DRAFT: "The pull request is a draft in GitHub; mark it ready there or merge in GitHub.",
    MergeBlockReason.CLOSED: "The pull request is closed in GitHub.",
    MergeBlockReason.CHECKS_FAILED: "Required checks failed; fix them, then merge in GitHub.",
    MergeBlockReason.QUEUE_REQUIRED: "The target only accepts queued merges; merge in GitHub.",
    MergeBlockReason.STACKED: "The pull request is part of a stack; merge in GitHub.",
    MergeBlockReason.WRONG_BASE: "The pull request targets another base branch; merge in GitHub or retarget it.",
    MergeBlockReason.CAPABILITY_UNAVAILABLE: "Delivery cannot merge here; merge the pull request in GitHub.",
    MergeBlockReason.METHOD_NOT_ALLOWED: "The repository disallows merge commits; merge in GitHub.",
}


_SYNC_BLOCKS = frozenset({MergeBlockReason.CONFLICTS, MergeBlockReason.BEHIND})
_SETTLED_PHASES = frozenset(
    {
        WorkItemPublicationPhase.DEFERRED,
        WorkItemPublicationPhase.ABANDONED,
        WorkItemPublicationPhase.ACCEPTANCE_OBSERVED,
    }
)
_SYNC_HELD_SITUATIONS = frozenset({"with-agent", "pausing", "needs-attention", "waiting-on-delivery"})


def _progress(
    situation: DeliverySituation, headline: str, waiting_on: DeliveryWaitingOn, **fields: str | None
) -> DeliveryProgress:
    return DeliveryProgress(situation=situation, headline=headline, waiting_on=waiting_on, **fields)


def derive_delivery_progress(  # noqa: PLR0913 - each keyword is one piece of read-only evidence.
    readiness: DeliveryReadiness,
    card: WorkItemCardView,
    frontier: DeliveryFrontier,
    *,
    issuer_state: DeliveryIssuerState | None = None,
    holder: str | None = None,
    at_capacity: bool = False,
    pause_requested: bool = False,
    pause_drained: bool = False,
    merged_unrecorded: bool = False,
    dependency_id: str | None = None,
    request: DeliveryRequest | None = None,
    sync_conflict_paths: tuple[str, ...] | None = None,
    aborted_sync_target: str | None = None,
) -> DeliveryProgress:
    """Map one final readiness and supplied evidence to its single user-facing situation (R3-R6).

    ``issuer_state`` is the claim-issuing window evidence for running Planner, Builder or Finalizer custody,
    and ``holder`` names that role. ``at_capacity`` reports that other Changes fill the execution capacity.
    ``pause_requested`` and ``pause_drained`` report a Pause request and whether its custody has drained (M3).
    ``merged_unrecorded`` reports a pull request GitHub merged whose completion Delivery has not recorded yet.
    ``dependency_id`` names the first incomplete Outcome a dependent Outcome waits on, and ``request`` is the
    card's open request, absent when a block stops the step.
    ``sync_conflict_paths`` is the preserved target-merge conflict, when one is retained, and
    ``aborted_sync_target`` the target head whose merge the user last aborted.
    No situation claims that work is running: custody is only "with an agent".
    """
    publication = card.scope is WorkItemScope.CHANGE_PUBLICATION
    conflict = sync_conflict_paths if publication or readiness.reason_code == "engine-action-failed" else None
    progress = (
        _lifecycle_progress(readiness, frontier, pause_requested=pause_requested, pause_drained=pause_drained)
        or _custody_progress(readiness, card, issuer_state, holder)
        or _sync_conflict_progress(conflict)
        or _merge_progress(readiness, card, frontier, merged_unrecorded=merged_unrecorded)
        or _step_progress(readiness, card, at_capacity=at_capacity, dependency_id=dependency_id, request=request)
    )
    if not publication:
        return progress
    if _repeats_aborted_sync(readiness, progress, aborted_sync_target):
        when = " once the retry time passes" if progress.next_eligible_at is not None else ""
        progress = progress.model_copy(update={"headline": _ABORTED_SYNC_HEADLINE.format(when=when)})
    availability = (
        "unavailable"
        if sync_conflict_paths is not None and progress.situation not in {"done", "abandoned", "paused"}
        else _target_sync_availability(readiness, card, progress)
    )
    return progress.model_copy(update={"target_sync": availability})


_ABORTED_SYNC_HEADLINE = (
    "You aborted merging this target; running the prompt{when} merges it again and keeps any conflict "
    "for you to resolve."
)


def _sync_conflict_progress(paths: tuple[str, ...] | None) -> DeliveryProgress | None:
    """A preserved target-merge conflict has one route: /resolve-target-conflict resolves or aborts it."""
    if paths is None:
        return None
    where = f" in {paths[0]}" if len(paths) == 1 else f" in {len(paths)} files" if paths else ""
    return _progress(
        "ready-for-next-step",
        f"Merging the latest target stopped on a conflict{where}; resolve it with /resolve-target-conflict.",
        "you",
    )


def _repeats_aborted_sync(readiness: DeliveryReadiness, progress: DeliveryProgress, aborted: str | None) -> bool:
    """The offered sync merges the same target the user just aborted."""
    return (
        aborted is not None
        and progress.situation == "ready-for-next-step"
        and readiness.basis.target_head == aborted
        and (
            readiness.reason_code == "target-sync-required"
            or (
                readiness.operation is WorkItemActionKind.SYNC_TARGET
                and (readiness.executable or readiness.reason_code == "retry-backoff")
            )
        )
    )


def _lifecycle_progress(
    readiness: DeliveryReadiness, frontier: DeliveryFrontier, *, pause_requested: bool, pause_drained: bool
) -> DeliveryProgress | None:
    if frontier.change_completion is not None:
        return _progress("done", "This Change is done.", "none")
    if frontier.change_abandonment is not None:
        return _progress("abandoned", "This Change was abandoned.", "none")
    if readiness.status == "complete":
        return _progress("done", "This Outcome is complete.", "none")
    if frontier.change_deferral is not None or pause_drained:
        return _progress("paused", "Paused. Resume the Change to continue.", "you")
    if pause_requested and (readiness.status == "running" or readiness.reason_code == "change-paused"):
        return _progress("pausing", "Pause requested; the current step finishes first.", "agent")
    return None


def _worker_stall_progress(readiness: DeliveryReadiness) -> DeliveryProgress:
    if readiness.next_eligible_at is None:
        return _progress(
            "waiting-on-delivery",
            "The VS Code window running this worker closed; Delivery waits for its processes to stop.",
            "delivery",
        )
    return _progress(
        "ready-for-next-step",
        "The VS Code window running this worker closed; run the prompt in Copilot Chat to restart the step.",
        "you",
        next_eligible_at=readiness.next_eligible_at,
    )


def _custody_progress(
    readiness: DeliveryReadiness,
    card: WorkItemCardView,
    issuer_state: DeliveryIssuerState | None,
    holder: str | None,
) -> DeliveryProgress | None:
    if readiness.reason_code == "engine-action-pending":
        return _progress("ready-for-next-step", "Run the prompt in Copilot Chat to resume the retained step.", "you")
    if readiness.reason_code == "worker-stall-wait":
        return _worker_stall_progress(readiness)
    if readiness.status != "running":
        return None
    if issuer_state == "gone":
        return _progress(
            "ready-for-next-step",
            "The VS Code window holding this step closed; run the prompt in Copilot Chat to resume it.",
            "you",
        )
    if issuer_state == "unknown":
        return _progress(
            "needs-attention", "Delivery cannot tell whether the agent holding this step is still running.", "you"
        )
    role = card.activity.worker_role
    name = holder or (role.value.capitalize() if role is not None else "An agent")
    return _progress("with-agent", f"{name} holds this step.", "agent", since=card.activity.started_at)


def _merge_progress(  # noqa: PLR0911 - one return per merge situation.
    readiness: DeliveryReadiness, card: WorkItemCardView, frontier: DeliveryFrontier, *, merged_unrecorded: bool
) -> DeliveryProgress | None:
    reason = readiness.reason_code
    since = readiness.merge_attempt.released_at if readiness.merge_attempt is not None else None
    if merged_unrecorded:
        return _progress("waiting-on-delivery", "Merged in GitHub. Delivery is recording the result.", "delivery")
    block = readiness.merge_block
    if block is not None:
        step = _MERGE_BLOCK_STEPS[block.reason]
        if block.reason in _MERGE_IN_GITHUB_BLOCKS:
            return _progress("your-decision", step, "you")
        return _progress("ready-for-next-step" if block.reason in _SYNC_BLOCKS else "needs-attention", step, "you")
    if reason == "merge-approval-required":
        offer = readiness.merge_offer
        target = f" into {offer.base_branch}" if offer is not None else ""
        return _progress("your-decision", f"Ready to merge{target}. Approve here or merge in GitHub.", "you")
    if reason in _GITHUB_WAITS:
        return _progress("waiting-on-github", _GITHUB_WAITS[reason], "github", since=since)
    if reason == "merge-response-unknown":
        return _progress(
            "needs-attention",
            "GitHub has not confirmed the merge for 10 minutes; open the pull request to check.",
            "you",
            since=since,
        )
    if reason == "target-sync-required":
        return _progress(
            "ready-for-next-step",
            f"Run the prompt in Copilot Chat to {_START_VERBS[WorkItemActionKind.SYNC_TARGET]}.",
            "you",
        )
    return _awaiting_merge_progress(readiness, card, frontier)


def _awaiting_merge_progress(
    readiness: DeliveryReadiness, card: WorkItemCardView, frontier: DeliveryFrontier
) -> DeliveryProgress | None:
    reason = readiness.reason_code
    awaiting_merge = (
        card.publication_phase is WorkItemPublicationPhase.AWAITING_MERGE
        and frontier.change_disposition is None
        and card.action.kind is WorkItemActionKind.OBSERVE_ACCEPTANCE
        and reason in {"ready", "request-action"}
    )
    if not awaiting_merge and reason != "acceptance-wait":
        return None
    if card.action.command is not None:
        return _progress(
            "ready-for-next-step", "Run the prompt in Copilot Chat to resolve the conflict with the target.", "you"
        )
    if reason == "acceptance-wait":
        return _progress("your-decision", "Merge the pull request in GitHub, then Check again.", "you")
    return _progress("your-decision", "Merge the pull request in GitHub; Delivery records the result.", "you")


def _step_progress(  # noqa: C901, PLR0911, PLR0912 - one return per readiness reason group.
    readiness: DeliveryReadiness,
    card: WorkItemCardView,
    *,
    at_capacity: bool,
    dependency_id: str | None,
    request: DeliveryRequest | None,
) -> DeliveryProgress:
    reason = readiness.reason_code
    if reason == "request-action":
        return _request_progress(request)
    if reason == "design-attention":
        return _progress("your-decision", "Review the returned Design and decide how to continue.", "you")
    if reason == "retry-backoff":
        return _retry_progress(readiness)
    if reason == "checkpoint-pending" and not readiness.executable:
        return _progress("waiting-on-delivery", "Delivery is publishing the pending checkpoint.", "delivery")
    if readiness.executable and readiness.action is not None:
        if readiness.next_actor is WorkItemNextActor.AGENT and at_capacity:
            return _progress(
                "waiting-on-dependency",
                "Other Changes use every execution slot; this Change continues when one frees up.",
                "change",
            )
        if readiness.next_actor is WorkItemNextActor.AGENT:
            verb = _START_VERBS.get(readiness.action.kind, "continue")
            return _progress("ready-for-next-step", f"Run the prompt in Copilot Chat to {verb}.", "you")
        return _progress("ready-for-next-step", f"Next: {readiness.action.label or 'continue'}.", "you")
    if reason == "review-repair":
        return _progress(
            "ready-for-next-step", "Review asked for changes; run the prompt in Copilot Chat to repair them.", "you"
        )
    if reason == "dependency-wait":
        headline = f"Waiting for {dependency_id} to complete." if dependency_id else "Waiting for another Outcome."
        return _progress("waiting-on-dependency", headline, "outcome", waiting_on_id=dependency_id)
    if reason in {"publication-wait", "task-incomplete"}:
        # No operation exists on this card yet; another scope of the same Change holds the next step.
        if card.scope is WorkItemScope.CHANGE_PUBLICATION:
            return _progress("waiting-on-dependency", "Waiting for this Change's Outcomes to complete.", "outcome")
        return _progress("waiting-on-dependency", "Waiting for this Change's current step to finish.", "change")
    if reason == "change-paused":
        return _progress("paused", "Paused. Resume the Change to continue.", "you")
    if _is_attempt_grant(card, readiness):
        return _progress("your-decision", _ATTEMPT_GRANT_HEADLINE, "you")
    return _progress(
        "needs-attention",
        _ATTENTION_HEADLINES.get(reason, "Delivery cannot continue this step on its own; inspect the Change."),
        "you",
    )


def _retry_progress(readiness: DeliveryReadiness) -> DeliveryProgress:
    if readiness.operation is WorkItemActionKind.OBSERVE_ACCEPTANCE:
        return _progress(
            "retrying-automatically",
            "Delivery checks GitHub again automatically.",
            "delivery",
            next_eligible_at=readiness.next_eligible_at,
        )
    return _progress(
        "ready-for-next-step",
        "The last attempt failed; run the prompt in Copilot Chat again once the retry time passes.",
        "you",
        next_eligible_at=readiness.next_eligible_at,
    )


def _request_progress(request: DeliveryRequest | None) -> DeliveryProgress:
    """Decision requests are choices; action requests and blocks are things to fix (D5)."""
    if request is None:
        return _progress("needs-attention", "A block stops this step; add the evidence it asks for.", "you")
    if request.kind.value == "decision":
        return _progress("your-decision", f"Decide: {request.summary}", "you")
    return _progress("needs-attention", f"Action needed: {request.summary}", "you")


def _target_sync_availability(
    readiness: DeliveryReadiness, card: WorkItemCardView, progress: DeliveryProgress
) -> TargetSyncAvailability:
    """U3 and owner guards: required to continue, optional after a moved target, else not offered."""
    if progress.situation in {"done", "abandoned", "paused"} or card.publication_phase in _SETTLED_PHASES:
        return "unnecessary"
    if (
        readiness.merge_attempt is not None
        or progress.situation in _SYNC_HELD_SITUATIONS
        or readiness.reason_code == "review-repair"
    ):
        return "unavailable"
    block = readiness.merge_block
    if (
        readiness.reason_code == "target-sync-required"
        or (readiness.executable and readiness.operation is WorkItemActionKind.SYNC_TARGET)
        or (block is not None and block.reason in _SYNC_BLOCKS)
    ):
        return "required"
    offer = readiness.merge_offer
    if offer is not None and offer.proof.proof_target != offer.target_head:
        return "optional"
    return "unnecessary"


class WorkItemProjector:
    """Derive MCP and Cockpit views from one immutable Delivery snapshot."""

    def __init__(  # noqa: PLR0913 - one immutable projection binds each readiness overlay input.
        self,
        snapshot: DeliveryPortfolioSnapshot,
        readiness: tuple[DeliveryReadiness, ...] = (),
        *,
        readiness_guidance: tuple[str | None, ...] = (),
        change_progress: DeliveryProgress | None = None,
        pause_unavailable_reason: ChangePauseUnavailableReason | None = "state-unavailable",
        pause_requested: bool = False,
        held_finalizer: WorkItemHeldFinalizerView | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._change_progress = change_progress
        self._pause_unavailable_reason = pause_unavailable_reason
        self._pause_requested = pause_requested
        self._held_finalizer = held_finalizer
        self._outcomes = {item.outcome_id: item for item in snapshot.contract.outcomes}
        self._bindings = {item.outcome_id: item for item in snapshot.frontier.bindings}
        self._cards = self._project_cards()
        if readiness:
            guidance = readiness_guidance or (None,) * len(readiness)
            retained_reasons = {
                "engine-action-pending",
                "engine-action-interrupted",
                "engine-action-failed",
                "engine-action-incomplete",
                "engine-action-blocked",
                "retry-exhausted",
                "retry-containment",
                "settled-attention-target-drift",
            }
            readiness_fallbacks = {
                "workspace-dirty": "Managed workspace preflight is blocked by local changes.",
                "workspace-inspection-failed": "Managed workspace readiness could not be observed.",
                "workspace-preflight-failed": "Managed workspace preflight did not pass.",
                "settled-attention-target-drift": (
                    "Settled Finalizer attention targets an earlier base; preserve its report, receipt, and retry "
                    "history pending owner direction."
                ),
                "active-custody": "An active operation retains Change custody.",
                "engine-action-pending": (
                    "The Delivery engine owner retains an unstarted exact operation; no failure or closure "
                    "evidence exists. Resume the exact operation only through its owner."
                ),
                "engine-action-interrupted": (
                    "The Delivery engine owner has no exact authoritative result/readback. Preserve custody and "
                    "journals; verified host/worker closure and settlement of all descendant writers and jobs is "
                    "required before resume; do not retry or infer termination."
                ),
                "engine-action-failed": (
                    "The Delivery engine owner has a recorded failure; its exact authoritative result/readback is "
                    "retained. Preserve custody and journals; the engine owner must resolve this condition before "
                    "resume; do not retry or release custody."
                ),
                "engine-action-incomplete": (
                    "The Delivery checkpoint owner must resolve the recorded checkpoint condition before the exact "
                    "operation can resume; preserve custody and journals; do not retry."
                ),
                "engine-action-blocked": (
                    "The original intent/start/result journals cannot be verified. The Delivery engine owner must "
                    "establish matching authoritative records and custody before resume; do not reconstruct or retry."
                ),
                "coordination-unavailable": "Change custody cannot be read; preserve state for diagnosis.",
                "claim-custody-unreconciled": (
                    "The exact Build claim has unreconciled writer custody. Preserve it; automatic recovery is "
                    "unavailable while host/worker evidence is missing. Resume awaits verified closure that excludes "
                    "all descendants and tool jobs and records settlement."
                ),
                "finalization-failed": (
                    "Finalization failed with custody retained. The authoritative result for this operation is "
                    "unavailable; automatic recovery is unavailable while host/worker evidence is missing. Resume "
                    "awaits verified closure evidence for this invocation that excludes all descendants and tool "
                    "jobs and records settlement. Diagnostic retirement cannot release custody or authorize retry."
                ),
                "review-repair": "Review repair requires a new Change commit before verification.",
                "retry-backoff": "Automatic recovery is waiting for its next eligible time.",
                "retry-exhausted": "Automatic retries are exhausted; Delivery offers no action to reset this budget.",
                "acceptance-wait": "Acceptance remains unchanged; observe later without repeating the effect.",
                "retry-containment": (
                    "A prior attempt has no authoritative outcome. Preserve custody; no caller action can retry or "
                    "release it."
                ),
                "retry-ledger-unavailable": "Retry authority could not be read; preserve state before continuing.",
                "worker-stall-wait": (
                    "The VS Code window that issued this worker claim has closed. Delivery settles the claim as "
                    "a failed attempt once no process uses its worktree and it stays unchanged for the quiet "
                    "period; preserve the worktree."
                ),
                "merge-approval-required": (
                    "Approve the merge in Cockpit, or merge the pull request in GitHub; Delivery records completion "
                    "afterward."
                ),
                "merge-checking": "GitHub is still computing mergeability; Delivery reads it again shortly.",
                "checks-running": "Required checks are still running; merge in GitHub once they pass.",
                "provider-unavailable": "GitHub could not be read; Delivery reads it again shortly.",
                "merge-in-progress": "GitHub is merging the pull request; Delivery records the result shortly.",
                "merge-response-unknown": (
                    "GitHub has not confirmed this merge. It may still run. Check the PR in GitHub: merge it there, "
                    "Check again, or Pause or Abandon the Change."
                ),
            }
            overlaid = tuple(
                card.model_copy(
                    update={
                        "readiness": decision,
                        "action": (
                            decision.action
                            if decision.action is not None
                            else card.action
                            if _is_attempt_grant(card, decision)
                            else card.action
                            if (
                                decision.reason_code == "design-attention"
                                and card.action.kind is WorkItemActionKind.RESUME_DESIGN
                            )
                            else card.action.model_copy(update={"label": "Check again"})
                            if (
                                decision.reason_code == "merge-response-unknown"
                                and card.action.kind is WorkItemActionKind.OBSERVE_ACCEPTANCE
                            )
                            else card.action
                            if (
                                decision.reason_code in _MERGE_WAIT_REASONS
                                and card.publication_phase is WorkItemPublicationPhase.AWAITING_MERGE
                                and card.action.kind is WorkItemActionKind.OBSERVE_ACCEPTANCE
                            )
                            else WorkItemAction()
                        ),
                        "next_actor": decision.next_actor,
                        "needs": (
                            card.needs
                            if _is_attempt_grant(card, decision)
                            else WorkItemNeed.NONE
                            if decision.reason_code in retained_reasons
                            else card.needs
                        ),
                        "needs_headline": (
                            _ATTEMPT_GRANT_HEADLINE
                            if _is_attempt_grant(card, decision)
                            else guidance_item or readiness_fallbacks.get(decision.reason_code, card.needs_headline)
                            if decision.reason_code in retained_reasons
                            else card.needs_headline
                        ),
                        "next_step": self._readiness_next_step(
                            card,
                            decision,
                            guidance_item,
                            readiness_fallbacks.get(decision.reason_code, card.next_step),
                        ),
                    }
                )
                for card, decision, guidance_item in zip(self._cards, readiness, guidance, strict=True)
            )
            self._cards = tuple(
                self._with_readiness_ownership(card, updated)
                for card, updated in zip(self._cards, overlaid, strict=True)
            )
        self._items = {card.work_item_id: self._compatibility_projection(card) for card in self._cards}

    def _with_readiness_ownership(self, card: WorkItemCardView, updated: WorkItemCardView) -> WorkItemCardView:
        """Drop the awaiting-merge card's phase-default user ownership when readiness names another owner."""
        readiness = updated.readiness
        if (
            readiness is None
            or readiness.next_actor is WorkItemNextActor.YOU
            or updated.needs is not WorkItemNeed.YOU
            or card.publication_phase is not WorkItemPublicationPhase.AWAITING_MERGE
            or card.action.kind is not WorkItemActionKind.OBSERVE_ACCEPTANCE
            or card.action.command is not None
            or self._snapshot.frontier.change_disposition is not None
        ):
            return updated
        agent_step = readiness.next_actor is WorkItemNextActor.AGENT and readiness.executable
        sync_step = agent_step and readiness.operation is WorkItemActionKind.SYNC_TARGET
        return updated.model_copy(
            update={
                "needs": WorkItemNeed.NONE,
                "needs_headline": None,
                "activity": WorkItemActivity(
                    state=WorkItemActivityState.READY if agent_step else WorkItemActivityState.IDLE
                ),
                "progress": (
                    updated.progress.model_copy(update={"label": "Target sync needed"})
                    if sync_step
                    else updated.progress
                ),
            }
        )

    @staticmethod
    def _readiness_next_step(
        card: WorkItemCardView,
        readiness: DeliveryReadiness,
        guidance: str | None,
        fallback: str,
    ) -> str:
        if guidance is not None:
            return guidance
        if readiness.merge_block is not None:
            return _MERGE_BLOCK_STEPS[readiness.merge_block.reason]
        offer = readiness.merge_offer
        if offer is not None and offer.proof.proof_target != offer.target_head:
            return (
                f"Proven against {offer.base_branch} at {offer.proof.proof_target[:12]}; {offer.base_branch} is now "
                f"at {offer.target_head[:12]}. Approve the merge in Cockpit, or merge the pull request in GitHub; "
                "Delivery records completion afterward."
            )
        if (
            readiness.reason_code == "target-sync-required"
            and card.publication_phase is WorkItemPublicationPhase.AWAITING_MERGE
        ):
            return "Delivery has no recorded proof target; synchronize the target and re-finalize before merging."
        if readiness.reason_code == "retry-exhausted":
            grant = _is_attempt_grant(card, readiness)
            owner = (
                "Builder"
                if card.scope is WorkItemScope.OUTCOME and (card.stage is WorkItemStage.IMPLEMENTATION or grant)
                else "Planner"
                if card.scope is WorkItemScope.OUTCOME
                else "Delivery"
            )
            remedy = (
                "Use Grant one more attempt in Cockpit to fund exactly one more Builder attempt, or inspect this "
                f"Change read-only with /inspect-change {card.change_id} first."
                if grant
                else f"Orchestrator can inspect this Change read-only with /inspect-change {card.change_id}; any "
                "new attempt requires approved current authority."
            )
            return f"{owner} retry budget is exhausted after {readiness.attempts} attempts. {remedy}"
        return fallback

    def list_items(self) -> tuple[WorkItemProjection, ...]:
        """Return MCP-compatible projections in snapshot order."""
        return tuple(self._items[card.work_item_id] for card in self._cards)

    def show(self, work_item_id: str) -> WorkItemDetail:
        """Return semantic detail for one projected identity."""
        projection = self._items[work_item_id]
        outcome = self._outcomes.get(work_item_id)
        return WorkItemDetail(
            projection=projection,
            acceptance=outcome.acceptance if outcome is not None else (),
            return_context=self._bindings[work_item_id].return_context if outcome is not None else None,
        )

    def group_view(self) -> ChangeGroupView:
        """Return one grouped Cockpit portfolio view."""
        completed = sum(binding.stage == DeliveryStage.COMPLETED for binding in self._snapshot.frontier.bindings)
        lifecycle = (
            self._change_lifecycle()
            if (
                completed == len(self._snapshot.frontier.bindings)
                or self._snapshot.frontier.change_disposition is not None
                or self._snapshot.frontier.change_deferral is not None
                or self._snapshot.frontier.change_abandonment is not None
            )
            else WorkItemChangeLifecycle.IN_DELIVERY
        )
        return ChangeGroupView(
            change_id=self._snapshot.contract.change_id,
            title=self._snapshot.contract.title,
            snapshot_version=self._snapshot.version,
            lifecycle=lifecycle,
            outcome_total=len(self._snapshot.contract.outcomes),
            outcome_completed=completed,
            items=self._cards,
            progress=self._change_progress,
            pause_available=self._pause_unavailable_reason is None,
            pause_unavailable_reason=self._pause_unavailable_reason,
            pause_requested=self._pause_requested,
        )

    def publication_phase(self) -> WorkItemPublicationPhase:
        """Return the Change publication phase from the captured frontier."""
        return self._publication_phase()

    def evidence(self, outcome_id: str | None = None) -> DeliveryEvidenceProjection:
        """Return the evidence projection of the whole Change or one outcome."""
        return build_evidence_projection(
            self._snapshot.contract,
            self._snapshot.frontier,
            contract_digest=contract_fingerprint(self._snapshot.contract),
            frontier_digest=self._snapshot.version,
            outcome_id=outcome_id,
        )

    def show_view(self, item_key: str) -> WorkItemDetailView:
        """Return semantic and operator detail for one scope-qualified key."""
        card = next(item for item in self._cards if item.item_key == item_key)
        frontier = self._snapshot.frontier
        abandon_available = frontier.change_completion is None and frontier.change_abandonment is None
        if card.scope == WorkItemScope.CHANGE_PUBLICATION:
            return WorkItemDetailView(
                snapshot_version=self._snapshot.version,
                change_title=self._snapshot.contract.title,
                card=card,
                promise="Publish the reviewed Change and observe its user-merged pull request.",
                decisions=self._snapshot.contract.decisions,
                held_finalizer=self._held_finalizer,
                operator_moves=self._snapshot.frontier.operator_moves,
                publication=self._publication_view(),
                readiness=card.readiness,
                change_progress=self._change_progress,
                abandon_available=abandon_available,
                pause_available=self._pause_unavailable_reason is None,
                pause_unavailable_reason=self._pause_unavailable_reason,
                evidence=self.evidence(),
                revision_prompt=self._revision_prompt(),
            )
        outcome_id = card.work_item_id
        outcome = self._outcomes[outcome_id]
        binding = self._bindings[outcome_id]
        commitments = tuple(
            item for item in self._snapshot.contract.commitments if item.commitment_id in outcome.commitment_ids
        )
        superseded = self._snapshot.contract.superseded_request_ids()
        superseded_request_ids = tuple(item.request_id for item in binding.requests if item.request_id in superseded)
        return WorkItemDetailView(
            snapshot_version=self._snapshot.version,
            change_title=self._snapshot.contract.title,
            card=card,
            promise=outcome.promise,
            acceptance=outcome.acceptance,
            commitments=commitments,
            decisions=self._snapshot.contract.applicable_decisions(outcome.commitment_ids, superseded_request_ids),
            dependencies=tuple(self._dependency_view(identity) for identity in outcome.dependency_ids),
            tasks=self._task_evidence(binding),
            block=binding.block,
            requests=binding.requests,
            superseded_request_ids=superseded_request_ids,
            active_claim=self._claim_view(binding),
            return_context=binding.return_context,
            operator_moves=self._snapshot.frontier.operator_moves,
            recovery_attention=self._recovery_view(binding.recovery_attention),
            retry_diagnostic=binding.retry_diagnostic,
            readiness=card.readiness,
            change_progress=self._change_progress,
            abandon_available=abandon_available,
            pause_available=self._pause_unavailable_reason is None,
            pause_unavailable_reason=self._pause_unavailable_reason,
            evidence=self.evidence(outcome_id),
            revision_prompt=self._revision_prompt(),
        )

    def _revision_prompt(self) -> str | None:
        """Return the Designer prompt for a requirement change; terminal and merged Changes need a successor."""
        frontier = self._snapshot.frontier
        if (
            frontier.change_completion is not None
            or frontier.change_abandonment is not None
            or frontier.merged_pull_request_latch is not None
        ):
            return None
        return f"/design {self._snapshot.contract.change_id} Change requirements:"

    def _project_cards(self) -> tuple[WorkItemCardView, ...]:
        cards = tuple(
            self._outcome_card(outcome, self._bindings[outcome.outcome_id])
            for outcome in self._snapshot.contract.outcomes
        )
        frontier = self._snapshot.frontier
        if (
            all(binding.stage == DeliveryStage.COMPLETED for binding in frontier.bindings)
            or frontier.pending_checkpoint is not None
            or frontier.change_disposition is not None
            or frontier.change_deferral is not None
            or frontier.change_abandonment is not None
        ):
            return (*cards, self._publication_card())
        return cards

    def _outcome_card(self, outcome: DeliveryOutcome, binding: OutcomeAuthorityBinding) -> WorkItemCardView:
        paused = self._snapshot.frontier.change_deferral is not None
        abandoned = self._snapshot.frontier.change_abandonment is not None
        if paused or abandoned:
            needs = WorkItemNeed.NONE
            headline = "Change paused" if paused else "Change abandoned"
            next_actor = WorkItemNextActor.NONE
            next_step = headline
            activity = WorkItemActivity(state=WorkItemActivityState.IDLE)
            progress = WorkItemProgress(kind=WorkItemProgressKind.TASKS, label=headline)
            action = WorkItemAction()
        else:
            needs, headline = self._outcome_needs(outcome, binding)
            next_actor, next_step = self._outcome_next(binding, needs, headline)
            activity = self._outcome_activity(binding, needs)
            progress = self._outcome_progress(binding)
            action = self._outcome_action(binding, self._snapshot.contract.change_id)
        return WorkItemCardView(
            item_key=f"outcome:{outcome.outcome_id}",
            work_item_id=outcome.outcome_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.OUTCOME,
            title=outcome.title,
            stage=WorkItemStage(binding.stage.value),
            needs=needs,
            needs_headline=headline,
            next_actor=next_actor,
            next_step=next_step,
            activity=activity,
            progress=progress,
            action=action,
        )

    def _outcome_needs(
        self,
        outcome: DeliveryOutcome,
        binding: OutcomeAuthorityBinding,
    ) -> tuple[WorkItemNeed, str | None]:
        if binding.stage == DeliveryStage.DESIGN:
            return WorkItemNeed.YOU, "Designer attention required before re-admission"
        if binding.retry_diagnostic is not None:
            return WorkItemNeed.NONE, "Retry refused; host worker-exclusion evidence required"
        pending_request = next((item for item in binding.requests if item.resolution is None), None)
        if pending_request is not None or (binding.block is not None and not binding.block.resolved):
            if pending_request is not None:
                headline = "Decision required" if pending_request.kind.value == "decision" else "Action required"
            else:
                headline = "Block requires evidence"
            return WorkItemNeed.YOU, headline
        if binding.recovery_attention is not None:
            return (
                (WorkItemNeed.NONE, "Builder transition contained; host exclusion required")
                if binding.recovery_attention.diagnostic_transition is not None
                else (WorkItemNeed.YOU, "Claim recovery required")
            )
        incomplete = tuple(
            identity for identity in outcome.dependency_ids if self._bindings[identity].stage != DeliveryStage.COMPLETED
        )
        if incomplete:
            return WorkItemNeed.DEPENDENCY, f"Waiting on {', '.join(incomplete)}"
        return WorkItemNeed.NONE, None

    @staticmethod
    def _outcome_next(
        binding: OutcomeAuthorityBinding,
        needs: WorkItemNeed,
        headline: str | None,
    ) -> tuple[WorkItemNextActor, str]:
        retry = binding.retry_diagnostic
        attention = binding.recovery_attention
        if retry is not None:
            claim = binding.active_claim
            owner = claim.owner_id if claim is not None else retry.transition.claim_id
            next_step = f"Retry {retry.transition.failure_code} refused; claim owner {owner} remains active"
        elif attention is not None and attention.diagnostic_transition is not None:
            claim = binding.active_claim
            owner = claim.owner_id if claim is not None else attention.claim_id
            next_step = f"Builder owner {owner}: {attention.reason} {attention.retry_condition}"
        else:
            next_step = None
        if next_step is not None:
            actor = WorkItemNextActor.NONE if retry is not None else WorkItemNextActor.AGENT
            return actor, next_step
        if needs == WorkItemNeed.YOU:
            return WorkItemNextActor.YOU, headline or "Your attention is required"
        if needs == WorkItemNeed.DEPENDENCY:
            return WorkItemNextActor.DEPENDENCY, headline or "Waiting on another Outcome"
        if binding.active_claim is not None:
            return WorkItemNextActor.AGENT, f"Claimed by {binding.active_claim.worker_role.value.capitalize()}"
        if binding.stage == DeliveryStage.COMPLETED:
            return WorkItemNextActor.NONE, "Complete — no action needed"
        return WorkItemNextActor.AGENT, "Run the continuation prompt in Copilot Chat"

    @staticmethod
    def _outcome_activity(binding: OutcomeAuthorityBinding, needs: WorkItemNeed) -> WorkItemActivity:
        claim = binding.active_claim
        if binding.retry_diagnostic is not None:
            return WorkItemActivity(state=WorkItemActivityState.IDLE)
        if binding.recovery_attention is not None and binding.recovery_attention.diagnostic_transition is not None:
            return WorkItemActivity(state=WorkItemActivityState.IDLE)
        if claim is not None:
            return WorkItemActivity(
                state=WorkItemActivityState.WORKING,
                worker_role=claim.worker_role,
                started_at=claim.started_at,
                task_id=claim.task_id,
            )
        if binding.stage == DeliveryStage.COMPLETED or needs != WorkItemNeed.NONE:
            return WorkItemActivity(state=WorkItemActivityState.IDLE)
        return WorkItemActivity(state=WorkItemActivityState.READY)

    @staticmethod
    def _outcome_action(binding: OutcomeAuthorityBinding, change_id: str) -> WorkItemAction:
        if binding.retry_diagnostic is not None or (
            binding.recovery_attention is not None and binding.recovery_attention.diagnostic_transition is not None
        ):
            return WorkItemAction()
        if binding.stage == DeliveryStage.DESIGN or is_builder_return_limit(binding):
            # A Builder return limit is lifted only by a preserving Design revision (N12 I5).
            return WorkItemAction(
                kind=WorkItemActionKind.RESUME_DESIGN,
                label="Resume Design" if binding.stage == DeliveryStage.DESIGN else "Revise Design",
                command=f"/design {change_id}",
            )
        pending_request = next((item for item in binding.requests if item.resolution is None), None)
        if pending_request is not None:
            return WorkItemAction(kind=WorkItemActionKind.ANSWER_REQUEST, label="Answer request")
        if binding.block is not None and not binding.block.resolved and binding.block.request_id is None:
            return (
                WorkItemAction(kind=WorkItemActionKind.GRANT_ATTEMPT, label="Grant one more attempt")
                if is_builder_attempt_grant_block(binding)
                else WorkItemAction(kind=WorkItemActionKind.CLEAR_BLOCK, label="Clear block")
            )
        if binding.recovery_attention is not None:
            return WorkItemAction(kind=WorkItemActionKind.RECOVER_CLAIM, label="Recover claim")
        return WorkItemAction()

    @staticmethod
    def _outcome_progress(binding: OutcomeAuthorityBinding) -> WorkItemProgress:
        if binding.stage == DeliveryStage.DESIGN:
            return WorkItemProgress(
                kind=WorkItemProgressKind.DESIGN_RETURN,
                label="Returned to Design",
            )
        if binding.stage == DeliveryStage.PLANNING:
            return WorkItemProgress(kind=WorkItemProgressKind.PLAN, label="Task plan not published")
        return WorkItemProgress(
            kind=WorkItemProgressKind.TASKS,
            label=f"{len(binding.results)} of {len(binding.tasks)} Delivery tasks reviewed",
            done=len(binding.results),
            total=len(binding.tasks),
        )

    def _publication_card(self) -> WorkItemCardView:
        if self._snapshot.frontier.change_abandonment is not None:
            return WorkItemCardView(
                item_key="publication",
                work_item_id=self._snapshot.contract.change_id,
                change_id=self._snapshot.contract.change_id,
                scope=WorkItemScope.CHANGE_PUBLICATION,
                title="Change publication",
                stage=None,
                publication_phase=self._publication_phase(),
                needs=WorkItemNeed.NONE,
                next_actor=WorkItemNextActor.NONE,
                next_step="Change abandoned",
                activity=WorkItemActivity(state=WorkItemActivityState.IDLE),
                progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label="Change abandoned"),
                action=WorkItemAction(),
            )
        if self._snapshot.frontier.change_deferral is not None:
            return WorkItemCardView(
                item_key="publication",
                work_item_id=self._snapshot.contract.change_id,
                change_id=self._snapshot.contract.change_id,
                scope=WorkItemScope.CHANGE_PUBLICATION,
                title="Change publication",
                stage=None,
                publication_phase=self._publication_phase(),
                needs=WorkItemNeed.YOU,
                needs_headline="Change is paused",
                next_actor=WorkItemNextActor.YOU,
                next_step="Resume the paused Change",
                activity=WorkItemActivity(state=WorkItemActivityState.IDLE),
                progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label="Change paused"),
                action=WorkItemAction(
                    kind=WorkItemActionKind.RESUME_CHANGE,
                    label="Resume Change",
                ),
            )
        disposition = self._snapshot.frontier.change_disposition
        if disposition is not None:
            return self._attention_card(disposition)
        phase = self._publication_phase()
        if phase == WorkItemPublicationPhase.REVIEW_REPAIR:
            needs, headline, next_actor = WorkItemNeed.YOU, "Review feedback needs attention", WorkItemNextActor.YOU
            next_step, progress = "Address pull-request feedback before re-finalization", "Review repair in progress"
            action = WorkItemAction(
                kind=WorkItemActionKind.NONE,
                label="Address pull-request feedback",
                command=f"/address-pr-feedback {self._snapshot.contract.change_id}",
            )
        elif phase == WorkItemPublicationPhase.FINALIZATION_INVALIDATED:
            needs, headline, next_actor = WorkItemNeed.NONE, "Finalization invalidated", WorkItemNextActor.AGENT
            next_step, progress = "Re-finalize the current Change head", "Head drift observed"
            action = WorkItemAction(kind=WorkItemActionKind.FINALIZE, label="Re-finalize Change")
        elif phase == WorkItemPublicationPhase.READY_FOR_FINALIZATION:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = "Finalize the reviewed Change", "Ready for finalization"
            action = (
                WorkItemAction(kind=WorkItemActionKind.FINALIZE, label="Finalize Change")
                if self._finalization_action_available()
                else WorkItemAction()
            )
        elif phase == WorkItemPublicationPhase.CHECKPOINT_PENDING:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = "Reconcile the final checkpoint", "Checkpoint pending"
            action = WorkItemAction(kind=WorkItemActionKind.RECONCILE_CHECKPOINT, label="Publish checkpoint")
        elif phase == WorkItemPublicationPhase.PULL_REQUEST_DRAFT:
            return self._draft_publication_card(phase)
        elif phase == WorkItemPublicationPhase.AWAITING_MERGE:
            needs, headline, next_actor, next_step, progress, action = self._awaiting_merge_state()
        else:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = "Record accepted completion", "Merge observed"
            action = WorkItemAction(kind=WorkItemActionKind.OBSERVE_ACCEPTANCE, label="Complete accepted Change")
        activity = WorkItemActivity(
            state=WorkItemActivityState.IDLE if next_actor == WorkItemNextActor.YOU else WorkItemActivityState.READY
        )
        return WorkItemCardView(
            item_key="publication",
            work_item_id=self._snapshot.contract.change_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.CHANGE_PUBLICATION,
            title="Change publication",
            stage=None,
            publication_phase=phase,
            needs=needs,
            needs_headline=headline,
            next_actor=next_actor,
            next_step=next_step,
            activity=activity,
            progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label=progress),
            action=action,
        )

    def _awaiting_merge_state(
        self,
    ) -> tuple[WorkItemNeed, str | None, WorkItemNextActor, str, str, WorkItemAction]:
        mergeability = self._current_publication_observation()
        if mergeability is not None and mergeability.mergeable is False:
            return (
                WorkItemNeed.YOU,
                "Pull request has merge conflicts",
                WorkItemNextActor.YOU,
                "Resolve pull-request conflicts before continuing",
                "Pull request conflicts detected",
                WorkItemAction(
                    kind=WorkItemActionKind.OBSERVE_ACCEPTANCE,
                    label="Check merge status",
                    command=f"/resolve-target-conflict {self._snapshot.contract.change_id}",
                ),
            )
        return (
            WorkItemNeed.YOU,
            "Merge pull request in GitHub",
            WorkItemNextActor.YOU,
            "Merge pull request in GitHub",
            "Awaiting merge in GitHub",
            WorkItemAction(kind=WorkItemActionKind.OBSERVE_ACCEPTANCE, label="Check merge status"),
        )

    def _draft_publication_card(self, phase: WorkItemPublicationPhase) -> WorkItemCardView:
        mergeability = self._current_publication_observation()
        if self._publication_head_requires_reconciliation():
            needs, headline, next_actor = (
                WorkItemNeed.YOU,
                "Pull request head differs from finalized Change",
                WorkItemNextActor.YOU,
            )
            next_step, progress = (
                "Review the current pull-request head before continuing",
                "Publication head needs reconciliation",
            )
            action = WorkItemAction()
        elif mergeability is not None and mergeability.mergeable is False:
            needs, headline, next_actor = (
                WorkItemNeed.YOU,
                "Pull request has merge conflicts",
                WorkItemNextActor.YOU,
            )
            next_step, progress = (
                "Resolve pull-request conflicts before making it ready",
                "Pull request conflicts detected",
            )
            action = WorkItemAction(
                kind=WorkItemActionKind.MARK_READY,
                label="Make PR ready for review",
                command=f"/resolve-target-conflict {self._snapshot.contract.change_id}",
            )
        else:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = (
                "Mark the pull request ready through Delivery",
                "Delivery ready state not recorded",
            )
            action = WorkItemAction(
                kind=WorkItemActionKind.MARK_READY,
                label="Make PR ready for review",
            )
        activity = WorkItemActivity(
            state=WorkItemActivityState.IDLE if next_actor == WorkItemNextActor.YOU else WorkItemActivityState.READY
        )
        return WorkItemCardView(
            item_key="publication",
            work_item_id=self._snapshot.contract.change_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.CHANGE_PUBLICATION,
            title="Change publication",
            stage=None,
            publication_phase=phase,
            needs=needs,
            needs_headline=headline,
            next_actor=next_actor,
            next_step=next_step,
            activity=activity,
            progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label=progress),
            action=action,
        )

    def _attention_card(self, disposition: DeliveryChangeDisposition) -> WorkItemCardView:
        if disposition.kind == DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION:
            head_move = self._head_move_attention_card(disposition)
            if head_move is not None:
                return head_move
            return self._prompt_attention_card(disposition, "Acceptance attention")
        if any(diagnostic.startswith("required-publication-check-failure") for diagnostic in disposition.diagnostics):
            return self._prompt_attention_card(
                disposition,
                "Publication attention",
                headline="Required publication checks need reconciliation",
                next_step="Re-observe checks before resolving publication attention",
            )
        if "publication-baseline-unavailable" in disposition.diagnostics:
            return self._prompt_attention_card(
                disposition,
                "Publication attention",
                headline="Publication baseline recovery is required",
                next_step="Use the attention workflow to recover the publication baseline",
            )
        if any(diagnostic.startswith("target-sync-operation:") for diagnostic in disposition.diagnostics):
            return self._prompt_attention_card(
                disposition,
                "Target sync conflict",
                headline="Target merge conflict needs resolution",
                next_step="Resolve the target merge conflict before continuing",
                command=f"/resolve-target-conflict {self._snapshot.contract.change_id}",
            )
        label = "Resolve publication attention"
        return WorkItemCardView(
            item_key="publication",
            work_item_id=self._snapshot.contract.change_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.CHANGE_PUBLICATION,
            title="Change publication",
            stage=None,
            publication_phase=self._publication_phase(),
            needs=WorkItemNeed.YOU,
            needs_headline="Change attention requires resolution",
            next_actor=WorkItemNextActor.YOU,
            next_step=label,
            activity=WorkItemActivity(state=WorkItemActivityState.IDLE),
            progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label=label),
            action=WorkItemAction(
                kind=WorkItemActionKind.RESOLVE_ATTENTION,
                label=label,
                attention_id=disposition.disposition_id,
            ),
        )

    def _head_move_attention_card(self, disposition: DeliveryChangeDisposition) -> WorkItemCardView | None:
        if disposition.acceptance_reason != DeliveryAcceptanceAttentionReason.HEAD_MOVED:
            return None
        invalidation = self._snapshot.frontier.finalization_invalidation
        publication = self._snapshot.frontier.change_disposition_publication
        if invalidation is None or publication is None:
            return None
        return WorkItemCardView(
            item_key="publication",
            work_item_id=self._snapshot.contract.change_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.CHANGE_PUBLICATION,
            title="Change publication",
            stage=None,
            publication_phase=self._publication_phase(),
            needs=WorkItemNeed.YOU,
            needs_headline="Pull request head changed",
            next_actor=WorkItemNextActor.YOU,
            next_step="Adopt the changed pull-request head before re-finalization",
            activity=WorkItemActivity(state=WorkItemActivityState.IDLE),
            progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label="Acceptance attention"),
            action=WorkItemAction(
                kind=WorkItemActionKind.ADOPT_EXTERNAL_HEAD,
                label="Adopt changed PR head",
                attention_id=disposition.disposition_id,
                expected_head=invalidation.expected_head,
                adopted_head=publication.head_sha,
            ),
        )

    def _prompt_attention_card(
        self,
        disposition: DeliveryChangeDisposition,
        label: str,
        *,
        headline: str = "Change attention requires resolution",
        next_step: str = "Use the exact attention recovery route",
        command: str | None = None,
    ) -> WorkItemCardView:
        return WorkItemCardView(
            item_key="publication",
            work_item_id=self._snapshot.contract.change_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.CHANGE_PUBLICATION,
            title="Change publication",
            stage=None,
            publication_phase=self._publication_phase(),
            needs=WorkItemNeed.YOU,
            needs_headline=headline,
            next_actor=WorkItemNextActor.YOU,
            next_step=next_step,
            activity=WorkItemActivity(state=WorkItemActivityState.IDLE),
            progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label=label),
            action=WorkItemAction(
                kind=WorkItemActionKind.RESOLVE_ATTENTION,
                label=f"Resolve {label.casefold()}",
                command=command
                or f"/resolve-delivery-attention {self._snapshot.contract.change_id} {disposition.disposition_id}",
                attention_id=disposition.disposition_id,
            ),
        )

    def _finalization_action_available(self) -> bool:
        """Expose finalization while retaining hard runtime custody guards."""
        frontier = self._snapshot.frontier
        return (
            all(binding.stage == DeliveryStage.COMPLETED for binding in frontier.bindings)
            and all(binding.active_claim is None for binding in frontier.bindings)
            and frontier.integration_repair_claim is None
        )

    def _publication_head_requires_reconciliation(self) -> bool:
        """Return whether the current publication head cannot satisfy finalization authority."""
        frontier = self._snapshot.frontier
        history = frontier.change_publication_history
        finalization = frontier.finalization
        return history is not None and finalization is not None and history.current.head_sha != finalization.exact_head

    def _current_publication_observation(self) -> PublicationPullRequestObservationReceipt | None:
        observation = self._snapshot.publication_observation
        frontier = self._snapshot.frontier
        history = frontier.change_publication_history
        published_head = frontier.published_head
        if observation is None or history is None or published_head is None:
            return None
        publication = history.current
        snapshot = observation.snapshot
        if (
            observation.change_id != self._snapshot.contract.change_id
            or publication.head_sha != published_head
            or snapshot.repository != publication.repository
            or snapshot.number != publication.number
            or snapshot.node_id != publication.node_id
            or snapshot.head_sha != published_head
            or snapshot.state != "open"
            or snapshot.merged
        ):
            return None
        return observation

    def _change_lifecycle(self) -> WorkItemChangeLifecycle:
        frontier = self._snapshot.frontier
        if frontier.change_abandonment is not None:
            lifecycle = WorkItemChangeLifecycle.ABANDONED
        elif frontier.change_deferral is not None:
            lifecycle = WorkItemChangeLifecycle.DEFERRED
        else:
            disposition = frontier.change_disposition
            if disposition is not None:
                lifecycle = (
                    WorkItemChangeLifecycle.PUBLICATION
                    if disposition.kind == DeliveryChangeDispositionKind.PUBLICATION_ATTENTION
                    else WorkItemChangeLifecycle.ACCEPTANCE
                )
            else:
                phase = self._publication_phase()
                if phase in {
                    WorkItemPublicationPhase.FINALIZATION_INVALIDATED,
                    WorkItemPublicationPhase.REVIEW_REPAIR,
                    WorkItemPublicationPhase.READY_FOR_FINALIZATION,
                }:
                    lifecycle = WorkItemChangeLifecycle.FINALIZATION
                elif phase in {
                    WorkItemPublicationPhase.CHECKPOINT_PENDING,
                    WorkItemPublicationPhase.PULL_REQUEST_DRAFT,
                }:
                    lifecycle = WorkItemChangeLifecycle.PUBLICATION
                elif phase == WorkItemPublicationPhase.AWAITING_MERGE:
                    lifecycle = WorkItemChangeLifecycle.AWAITING_MERGE
                else:
                    lifecycle = WorkItemChangeLifecycle.ACCEPTANCE
        return lifecycle

    def _publication_phase(self) -> WorkItemPublicationPhase:
        return resolve_publication_phase(self._snapshot.frontier)

    def _publication_view(self) -> WorkItemPublicationView:
        frontier = self._snapshot.frontier
        finalization = frontier.finalization
        pending = frontier.pending_checkpoint
        invalidation = frontier.finalization_invalidation
        ready = frontier.ready
        attention_publication = frontier.change_disposition_publication
        merged = frontier.merged_pull_request_latch
        publication_history = frontier.change_publication_history
        publication_identity = (
            ready
            or merged
            or attention_publication
            or (publication_history.current if publication_history is not None else None)
        )
        publication_observation = self._current_publication_observation()
        target_sync = frontier.target_sync_receipt
        return WorkItemPublicationView(
            phase=self._publication_phase(),
            finalization_id=finalization.finalization_id if finalization is not None else None,
            finalized_head=finalization.exact_head if finalization is not None else None,
            published_head=frontier.published_head,
            pending_checkpoint_head=pending.head if pending is not None else None,
            pending_checkpoint_triggers=tuple(trigger.kind.value for trigger in pending.triggers) if pending else (),
            pending_checkpoint_attempt_count=pending.attempt_count if pending is not None else 0,
            pending_checkpoint_last_attempted_at=(
                pending.last_attempted_at.isoformat() if pending is not None and pending.last_attempted_at else None
            ),
            pending_checkpoint_error_code=pending.last_error_code if pending is not None else None,
            pending_checkpoint_error_detail=pending.last_error_detail if pending is not None else None,
            invalidated_expected_head=invalidation.expected_head if invalidation is not None else None,
            invalidated_observed_head=invalidation.observed_head if invalidation is not None else None,
            repository=publication_identity.repository if publication_identity is not None else None,
            pull_request_number=publication_identity.number if publication_identity is not None else None,
            pull_request_head=publication_identity.head_sha if publication_identity is not None else None,
            mergeable=publication_observation.mergeable if publication_observation is not None else None,
            merge_state_status=(
                publication_observation.merge_state_status if publication_observation is not None else None
            ),
            mergeability_observed_at=(
                publication_observation.observed_at.isoformat() if publication_observation is not None else None
            ),
            accepted_merge_commit=merged.accepted_merge_commit if merged is not None else None,
            merged_at=merged.merged_at.isoformat() if merged is not None else None,
            publication_generations=(
                tuple(
                    WorkItemPublicationGenerationView(
                        repository=publication.repository,
                        number=publication.number,
                        node_id=publication.node_id,
                        head_sha=publication.head_sha,
                    )
                    for publication in publication_history.publications
                )
                if publication_history is not None
                else ()
            ),
            attention=frontier.change_disposition,
            target_sync=(
                WorkItemTargetSyncView(
                    receipt_id=target_sync.receipt_id,
                    operation_id=target_sync.operation_id,
                    target_branch=target_sync.integration_target,
                    expected_target=target_sync.expected_target,
                    target_head=target_sync.target_head,
                    change_head_before=target_sync.change_head_before,
                    merged_head=target_sync.merged_head,
                    merge_commit=target_sync.merge_commit,
                    review_required=target_sync.review_required,
                )
                if target_sync is not None
                else None
            ),
        )

    def _compatibility_projection(self, card: WorkItemCardView) -> WorkItemProjection:
        outcome = self._outcomes.get(card.work_item_id)
        binding = self._bindings.get(card.work_item_id)
        return WorkItemProjection(
            work_item_id=card.work_item_id,
            change_id=card.change_id,
            scope=card.scope.value,
            title=outcome.title if outcome is not None else self._snapshot.contract.title,
            promise=outcome.promise
            if outcome is not None
            else "Publish the reviewed Change and observe its user-merged pull request.",
            stage=card.stage or WorkItemStage.COMPLETED,
            dependency_ready=card.needs != WorkItemNeed.DEPENDENCY,
            commitment_ids=outcome.commitment_ids if outcome is not None else (),
            dependency_ids=outcome.dependency_ids if outcome is not None else (),
            task_count=len(binding.tasks) if binding is not None else 0,
            reviewed_task_count=len(binding.results) if binding is not None else 0,
            next_action=(
                card.next_step
                if card.readiness is not None
                and card.readiness.reason_code
                in {
                    "builder-transition-contained",
                    "engine-action-pending",
                    "engine-action-interrupted",
                    "engine-action-failed",
                    "engine-action-incomplete",
                    "engine-action-blocked",
                }
                else card.action.label or card.needs_headline or card.progress.label
            ),
        )

    def _dependency_view(self, outcome_id: str) -> WorkItemDependencyView:
        return WorkItemDependencyView(
            outcome_id=outcome_id,
            title=self._outcomes[outcome_id].title,
            stage=WorkItemStage(self._bindings[outcome_id].stage.value),
        )

    @staticmethod
    def _claim_view(binding: OutcomeAuthorityBinding) -> WorkItemClaimView | None:
        claim = binding.active_claim
        if claim is None:
            return None
        return WorkItemClaimView(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            owner_id=claim.owner_id,
            process_id=claim.process_id,
            continuation=claim.continuation,
            started_at=claim.started_at,
            worker_role=claim.worker_role,
            task_id=claim.task_id,
        )

    @staticmethod
    def _recovery_view(attention: DeliveryRecoveryAttention | None) -> WorkItemRecoveryView | None:
        if attention is None:
            return None
        return WorkItemRecoveryView(
            attempt_id=attention.attempt_id,
            claim_id=attention.claim_id,
            reason=attention.reason,
            custody_retained=attention.custody_retained,
            retry_condition=attention.retry_condition,
            diagnostic_transition=attention.diagnostic_transition,
        )

    @staticmethod
    def _task_evidence(binding: OutcomeAuthorityBinding) -> tuple[WorkItemTaskEvidence, ...]:
        results = {item.task_id: item for item in binding.results}
        active_task_id = binding.active_claim.task_id if binding.active_claim is not None else None
        return tuple(
            WorkItemTaskEvidence(
                task_id=task.task_id,
                title=task.title,
                result=task.result,
                status=(
                    "reviewed" if task.task_id in results else "active" if task.task_id == active_task_id else "pending"
                ),
                completed_commit=results[task.task_id].completed_commit if task.task_id in results else None,
                acceptance_observations=task.acceptance_observations,
                proof_boundaries=task.proof_boundaries,
            )
            for task in binding.tasks
        )
