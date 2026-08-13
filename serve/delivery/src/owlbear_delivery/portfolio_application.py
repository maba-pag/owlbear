"""Deterministic portfolio acquisition and bounded worker context."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.acceptance import (
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
)
from owlbear_delivery.change_publication import (
    ChangeBranchPublicationReceipt,
    ChangeBranchPublisher,
    PublishChangeBranch,
)
from owlbear_delivery.change_workspace import (
    ChangeCoordination,
    ChangeWorkspaceManager,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    WorkspaceRecoverySnapshot,
)
from owlbear_delivery.delivery_runtime import (
    ActivateDeliveryClaim,
    AdministrativeDeliveryMove,
    AdministrativeDeliveryMovePreview,
    AdministrativeDeliveryMoveResult,
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryChangeStage,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointTriggerKind,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryPendingCheckpoint,
    DeliveryPlanCandidate,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryRequestResolution,
    DeliveryResultCandidate,
    DeliveryReturnContext,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryTransition,
    DeliveryWorkerRole,
    FinalizeDeliveryChange,
    OutcomeAuthorityBinding,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    integration_attention_disposition,
)
from owlbear_delivery.draft_pull_request import (
    CreateOrReconcileDraftPullRequest,
    DraftPullRequestPublicationReceipt,
    DraftPullRequestPublisher,
    GeneratedPullRequestSummaryReceipt,
    MarkChangePullRequestReady,
    ObserveChangePublicationChecks,
    ObserveChangePublicationPullRequest,
    PublicationCheckObservationReceipt,
    PullRequestReadyReceipt,
    ReadChangePublicationCheckObservations,
    ReturnChangePullRequestToDraft,
    UpdateGeneratedPullRequestSummary,
)
from owlbear_delivery.portfolio_operating import (
    PortfolioGuidanceFacts,
    PortfolioOperatingView,
    PortfolioWorkReference,
    PortfolioWorkScope,
    derive_portfolio_guidance,
)
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCompilationResult,
    DeliveryOutcome,
    compile_delivery_contract,
)
from owlbear_delivery.work_items import (
    ChangeGroupView,
    DeliveryPortfolioSnapshot,
    WorkItemDetailView,
    WorkItemNeed,
    WorkItemProjector,
    WorkItemPublicationPhase,
    WorkItemScope,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery.completed_history import (
        CompletedChangePage,
        CompletedChangeRecord,
        CompletedHistoryCatalog,
    )
    from owlbear_delivery.design_package import (
        DesignCheckpointResult,
        DesignPackageResult,
        DesignPackageStore,
        VerifiedDesignPackage,
    )
    from owlbear_delivery.target_admission import (
        DeliveryAdmissionRequest,
        DeliveryAdmissionResult,
        DeliveryAuthorityRegistry,
    )
    from owlbear_delivery.work_items import WorkItemDetail, WorkItemProjection


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        message = "Delivery claim timestamps must include a timezone"
        raise ValueError(message)
    return parsed.astimezone(UTC)


_MAX_PULL_REQUEST_TITLE_LENGTH = 256


def _operating_scope(scope: WorkItemScope) -> PortfolioWorkScope:
    if scope == WorkItemScope.CHANGE_PUBLICATION:
        return PortfolioWorkScope.PUBLICATION
    return PortfolioWorkScope.OUTCOME


def _checkpoint_operation_id(kind: str, *parts: str) -> str:
    payload = json.dumps((kind, *parts), separators=(",", ":"))
    return f"checkpoint-{kind}-{hashlib.sha256(payload.encode()).hexdigest()}"


def _checkpoint_summary(
    pending: DeliveryPendingCheckpoint,
    head: str,
) -> str:
    lines = [f"Reviewed Delivery checkpoint `{head}`.", "", "Included boundaries:"]
    for trigger in pending.triggers:
        if trigger.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK:
            lines.append("- First promoted Task result")
        elif trigger.kind == DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME:
            lines.append(f"- Verified Outcome `{trigger.outcome_id}`")
        elif trigger.kind == DeliveryCheckpointTriggerKind.FINALIZATION:
            lines.append("- Finalized Change")
        else:
            lines.append("- Explicit publication request")
    return "\n".join(lines)


def _checkpoint_pull_request_title(runtime: DeliveryRuntime) -> str:
    printable = "".join(character if character.isprintable() else " " for character in runtime.contract.title)
    title = " ".join(printable.split()) or f"Delivery Change {runtime.contract.change_id}"
    if len(title) <= _MAX_PULL_REQUEST_TITLE_LENGTH:
        return title
    return f"{title[: _MAX_PULL_REQUEST_TITLE_LENGTH - 3]}..."


def _operator_claim(claim: DeliveryActiveClaim | None) -> DeliveryOperatorClaim | None:
    if claim is None:
        return None
    return DeliveryOperatorClaim(
        attempt_id=claim.attempt_id,
        claim_id=claim.claim_id,
        started_at=claim.started_at,
        worker_role=claim.worker_role,
        task_id=claim.task_id,
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


class DeliveryLaunchPackage(_ApplicationModel):
    """Bounded identity and source locators for one named worker invocation."""

    change_id: str = Field(min_length=1)
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    task_id: str | None = None
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


class DeliveryAcquisitionFailure(_ApplicationModel):
    """Bounded fail-closed preparation result, optionally tied to a started claim."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str | None = None
    claim_id: str | None = None
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    retry_condition: str = Field(min_length=1)


class DeliveryIntegrationAttentionStatus(_ApplicationModel):
    """One non-retryable Integration attention exposed by acquisition."""

    change_id: str = Field(min_length=1)
    code: DeliveryIntegrationAttentionCode
    disposition: DeliveryIntegrationAttentionDisposition
    retry_condition: str = Field(min_length=1)


class DeliveryAcquisitionResult(_ApplicationModel):
    """Launchable task claims plus typed attention from one refresh."""

    launch_packages: tuple[DeliveryLaunchPackage, ...]
    integration_attention: tuple[DeliveryIntegrationAttentionStatus, ...] = ()
    failures: tuple[DeliveryAcquisitionFailure, ...] = ()


class DeliveryPlanContext(_ApplicationModel):
    """Plan authority and current same-outcome successor context."""

    launch: DeliveryLaunchPackage
    outcome: DeliveryOutcome
    commitments: tuple[DeliveryCommitment, ...]
    requests: tuple[DeliveryRequest, ...]
    return_context: DeliveryReturnContext | None = None


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


class DeliveryFinalizationContext(_ApplicationModel):
    """Engine-resolved read context for exact Change finalization."""

    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_phase: WorkItemPublicationPhase
    ready_for_finalization: bool
    readiness_diagnostics: tuple[str, ...]
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finalized_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class DeliveryOperatorClaim(_ApplicationModel):
    """Bounded active-claim identity required for explicit operator recovery."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None


class DeliveryOperatorRecoveryAttention(_ApplicationModel):
    """Recovery evidence without workspace or Git custody internals."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    custody_retained: bool
    retry_condition: str = Field(min_length=1)


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
    integration_attention: DeliveryOperatorIntegrationAttention | None = None


class DeliveryClaimRecoveryStatus(StrEnum):
    """Observable disposition of one exact-claim recovery request."""

    RECOVERED = "recovered"
    ATTENTION = "attention"


class DeliveryClaimRecoveryResult(_ApplicationModel):
    """Recovered claim state or retained typed repair attention."""

    status: DeliveryClaimRecoveryStatus
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    preserved_ref: str | None = None
    attention: DeliveryRecoveryAttention | None = None

    @model_validator(mode="after")
    def _validate_disposition(self) -> DeliveryClaimRecoveryResult:
        if (self.status == DeliveryClaimRecoveryStatus.ATTENTION) != (self.attention is not None):
            message = "only retained recovery requires repair attention"
            raise ValueError(message)
        return self


class DeliveryIntegrationRepairRecoveryResult(_ApplicationModel):
    """Recovered exact Integration repair claim and preserved commit evidence."""

    status: Literal[DeliveryClaimRecoveryStatus.RECOVERED] = DeliveryClaimRecoveryStatus.RECOVERED
    change_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class PortfolioApplicationError(RuntimeError):
    """Portfolio preparation or scoped context validation failed closed."""

    code = "ERR_DELIVERY_PORTFOLIO"


class PortfolioReadView(_ApplicationModel):
    """Grouped work and operating facts derived from one portfolio capture."""

    groups: tuple[ChangeGroupView, ...]
    operating: PortfolioOperatingView


class DeliveryCheckpointReconciliationResult(_ApplicationModel):
    """One deterministic checkpoint reconciliation attempt and remaining queue state."""

    change_id: str = Field(min_length=1)
    attempted_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    branch_publication: ChangeBranchPublicationReceipt | None = None
    draft_pull_request: DraftPullRequestPublicationReceipt | None = None
    generated_summary: GeneratedPullRequestSummaryReceipt | None = None
    state: DeliveryCheckpointPublicationState
    reconciled: bool


class PortfolioApplicationConfig(_ApplicationModel):
    """Configured capacity, source root, and complete stage-role policy."""

    package_root: Path
    execution_capacity: int = Field(gt=0)
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
    change_branch_publisher: ChangeBranchPublisher | None = None
    draft_pull_request_publisher: DraftPullRequestPublisher | None = None


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
class _PreparedSource:
    package: VerifiedDesignPackage
    coordination: ChangeCoordination
    source_head: str


class PortfolioApplication:
    """Compose Delivery runtimes, source packages, and warm workspace custody."""

    def __init__(
        self,
        runtimes: Mapping[str, DeliveryRuntime],
        dependencies: PortfolioApplicationDependencies,
        config: PortfolioApplicationConfig,
        hooks: PortfolioApplicationHooks | None = None,
    ) -> None:
        if set(runtimes) != {runtime.contract.change_id for runtime in runtimes.values()}:
            message = "runtime mapping keys must match admitted change identities"
            raise ValueError(message)
        self._runtimes = dict(runtimes)
        self._target_root = dependencies.target_root.resolve()
        self._package_store = dependencies.package_store
        self._authority_registry = dependencies.authority_registry
        self._package_root = config.package_root.resolve()
        self._coordinator = dependencies.coordinator
        self._workspace_manager = dependencies.workspace_manager
        self._completed_history_catalog = dependencies.completed_history_catalog
        self._change_branch_publisher = dependencies.change_branch_publisher
        self._draft_pull_request_publisher = dependencies.draft_pull_request_publisher
        self._execution_capacity = config.execution_capacity
        self._policies = {policy.worker_role: policy for policy in config.role_policies}
        self._identity_factory = hooks.identity_factory if hooks else lambda: str(uuid.uuid4())
        self._clock = (
            hooks.clock
            if hooks
            else lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    def create_design_session(
        self,
        change_id: str,
        intent_bytes: bytes,
        design_bytes: bytes,
    ) -> DesignPackageResult:
        """Create or replay one exact authored Design package."""
        return self._package_store.create(change_id, intent_bytes, design_bytes)

    def observe_change_publication_checks(
        self,
        change_id: str,
    ) -> PublicationCheckObservationReceipt:
        """Observe provider checks at the exact durable published Change head."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        published_head = self._runtime(change_id).checkpoint_publication_state().published_head
        if published_head is None:
            message = "Change has no reconciled checkpoint publication"
            raise PortfolioApplicationError(message)
        return self._draft_pull_request_publisher.observe_checks(
            ObserveChangePublicationChecks(change_id=change_id, published_head=published_head)
        )

    def show_change_checkpoint_publication(self, change_id: str) -> DeliveryCheckpointPublicationState:
        """Return the durable checkpoint queue for one admitted Change."""
        return self._runtime(change_id).checkpoint_publication_state()

    def show_finalization_context(self, change_id: str) -> DeliveryFinalizationContext:
        """Return engine-resolved finalization context without changing Delivery state."""
        runtime = self._runtime(change_id)
        coordination = self._workspace_manager.show(change_id)
        try:
            change_head = self._workspace_manager.observed_change_head(change_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("finalization context could not resolve the managed Change head", exc)
        ready, diagnostics = runtime.finalization_readiness()
        finalization = runtime.finalization()
        if ready:
            try:
                self._workspace_manager.validate_finalization_head(
                    change_id,
                    change_head,
                    tuple(result.completed_commit for binding in runtime.bindings() for result in binding.results),
                )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                ready = False
                diagnostics = (str(exc),)
        return DeliveryFinalizationContext(
            change_id=change_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            change_head=change_head,
            reviewed_change_head=coordination.last_reviewed_commit,
            publication_phase=self._work_item_projector(runtime).publication_phase(),
            ready_for_finalization=ready,
            readiness_diagnostics=diagnostics,
            finalization_id=finalization.finalization_id if finalization is not None else None,
            finalized_head=finalization.exact_head if finalization is not None else None,
        )

    def finalize_change(
        self,
        change_id: str,
        request: FinalizeDeliveryChange,
    ) -> DeliveryFinalizationReceipt:
        """Finalize one exact clean reviewed Change head and queue its checkpoint."""
        runtime = self._runtime(change_id)
        existing = runtime.finalization()
        if existing is not None:
            if (
                existing.operation_id == request.operation_id
                and existing.exact_head == request.exact_head
                and existing.observations == request.observations
                and existing.review == request.review
            ):
                return existing
            self._fail(
                "Delivery Change is already finalized with different authority",
                ValueError("finalization request is not an exact replay"),
            )
        context = self.show_finalization_context(change_id)
        if not context.ready_for_finalization:
            self._fail(
                "finalization requires a ready exact Change context",
                ValueError("; ".join(context.readiness_diagnostics)),
            )
        if request.exact_head != context.change_head:
            self._fail(
                "finalization request does not match the current Change head",
                ValueError("Change head changed"),
            )
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            results = tuple(result for binding in runtime.bindings() for result in binding.results)
            self._workspace_manager.validate_finalization_head(
                change_id,
                request.exact_head,
                tuple(result.completed_commit for result in results),
            )
            return runtime.finalize_change(request, _timestamp(self._clock()))

    def mark_change_ready(
        self,
        change_id: str,
        request: MarkChangePullRequestReady,
    ) -> PullRequestReadyReceipt:
        """Mark the exact finalized and fully published Change pull request ready."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            finalization = runtime.finalization()
            publication = runtime.checkpoint_publication_state()
            if (
                finalization is None
                or request.change_id != change_id
                or request.finalization_id != finalization.finalization_id
                or request.exact_head != finalization.exact_head
            ):
                message = "pull-request ready request does not match current finalization authority"
                raise PortfolioApplicationError(message)
            if publication.published_head != finalization.exact_head or publication.pending_checkpoint is not None:
                message = "pull-request readiness requires the reconciled final checkpoint"
                raise PortfolioApplicationError(message)
            self._draft_pull_request_publisher.observe_checks(
                ObserveChangePublicationChecks(
                    change_id=change_id,
                    published_head=finalization.exact_head,
                )
            )
            receipt = self._draft_pull_request_publisher.mark_ready(request)
            return runtime.mark_awaiting_merge(receipt)

    def mark_current_change_ready(self, change_id: str) -> PullRequestReadyReceipt:
        """Mark the current exact finalization ready without caller-supplied authority."""
        finalization = self._runtime(change_id).finalization()
        if finalization is None:
            message = "pull-request readiness requires current finalization authority"
            raise PortfolioApplicationError(message)
        return self.mark_change_ready(
            change_id,
            MarkChangePullRequestReady(
                change_id=change_id,
                operation_id=f"ready-{finalization.finalization_id}",
                finalization_id=finalization.finalization_id,
                exact_head=finalization.exact_head,
            ),
        )

    def observe_acceptance(self, change_id: str) -> CompletionReceipt:
        """Complete one Change from a fresh exact merged-PR observation."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            existing = runtime.completion_receipt()
            if existing is not None:
                return existing
            finalization = runtime.finalization()
            ready = runtime.ready_receipt()
            publication = runtime.checkpoint_publication_state()
            if finalization is None or ready is None:
                message = "acceptance observation requires awaiting-merge authority"
                raise PortfolioApplicationError(message)
            if publication.published_head != finalization.exact_head or publication.pending_checkpoint is not None:
                message = "acceptance observation requires the reconciled final checkpoint"
                raise PortfolioApplicationError(message)
            observation = self._draft_pull_request_publisher.observe_pull_request(
                ObserveChangePublicationPullRequest(change_id=change_id)
            )
            if observation is None:
                message = "acceptance observation requires a bound pull request"
                raise PortfolioApplicationError(message)
            snapshot = observation.snapshot
            if (
                snapshot.repository != self._draft_pull_request_publisher.repository
                or snapshot.repository != ready.repository
                or snapshot.number != ready.number
                or snapshot.node_id != ready.node_id
                or snapshot.base_branch != self._draft_pull_request_publisher.target_branch
                or snapshot.head_sha != finalization.exact_head
                or snapshot.state != "closed"
                or not snapshot.merged
                or snapshot.merge_commit_sha is None
                or snapshot.merged_at is None
            ):
                message = "provider pull request does not satisfy acceptance authority"
                raise PortfolioApplicationError(message)
            latch = runtime.latch_merged_pull_request(observation)
            checks = self._draft_pull_request_publisher.read_check_observations(
                ReadChangePublicationCheckObservations(
                    change_id=change_id,
                    repository=latch.repository,
                    number=latch.number,
                    exact_commit=finalization.exact_head,
                )
            )
            receipt = CompletionReceipt.create(
                CompletionEvidence(
                    change_id=change_id,
                    finalization_receipt_id=finalization.finalization_id,
                    finalized_change_head=finalization.exact_head,
                    repository_identity=latch.repository,
                    pull_request_identity=CompletionPullRequestIdentity(
                        number=latch.number,
                        node_id=latch.node_id,
                    ),
                    accepted_target_ref=latch.base_branch,
                    accepted_merge_commit=latch.accepted_merge_commit,
                    merged_at=latch.merged_at,
                    acceptance_observation_id=latch.acceptance_observation_id,
                    check_observation_ids=tuple(item.observation_id for item in checks),
                    review_receipt_ids=(finalization.review.review_id,),
                    completed_at=_timestamp(self._clock()),
                )
            )
            return runtime.complete_change(receipt)

    def reconcile_finalization_head(
        self,
        change_id: str,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain or invalidate finalization from the engine-derived Change branch head."""
        runtime = self._runtime(change_id)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            if runtime.completion_receipt() is not None:
                return runtime.finalization()
            finalization = runtime.finalization()
            ready = runtime.ready_receipt()
            observation = (
                None
                if self._draft_pull_request_publisher is None
                else self._draft_pull_request_publisher.observe_pull_request(
                    ObserveChangePublicationPullRequest(change_id=change_id)
                )
            )
            observed_head = (
                self._workspace_manager.observed_change_head(change_id)
                if observation is None
                else observation.snapshot.head_sha
            )
            if (
                finalization is not None
                and ready is not None
                and observation is not None
                and observed_head != finalization.exact_head
            ):
                self._draft_pull_request_publisher.return_to_draft(
                    ReturnChangePullRequestToDraft(
                        change_id=change_id,
                        operation_id=f"return-draft-{ready.finalization_id}",
                        finalization_id=ready.finalization_id,
                        exact_head=observation.snapshot.head_sha,
                    )
                )
            result = runtime.reconcile_finalization_head(observed_head, _timestamp(self._clock()))
            if not isinstance(result, DeliveryFinalizationInvalidationReceipt) and observation is not None:
                runtime.reconcile_pull_request_draft_state(provider_draft=observation.snapshot.draft)
            return result

    def reconcile_change_checkpoint(self, change_id: str) -> DeliveryCheckpointReconciliationResult:
        """Reconcile one durable checkpoint without accepting caller-supplied external fences."""
        if self._change_branch_publisher is None or self._draft_pull_request_publisher is None:
            message = "checkpoint publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return self._reconcile_change_checkpoint(change_id, runtime)

    def _reconcile_change_checkpoint(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> DeliveryCheckpointReconciliationResult:
        initial = runtime.checkpoint_publication_state()
        pending = initial.pending_checkpoint
        if pending is None:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=True,
            )
        if pending.head is None:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=False,
            )

        head = pending.head
        summary = _checkpoint_summary(pending, head)
        pull_request_title = _checkpoint_pull_request_title(runtime)
        branch_request = PublishChangeBranch(
            change_id=change_id,
            expected_remote_head=initial.published_head,
            expected_published_head=head,
            operation_id=_checkpoint_operation_id(
                "branch",
                change_id,
                head,
            ),
        )
        branch_receipt = self._change_branch_publisher.publish(branch_request)
        if initial.published_head != head:
            state = runtime.record_checkpoint_branch_publication(initial, branch_receipt.published_head)
        else:
            state = runtime.checkpoint_publication_state()

        current = state.pending_checkpoint
        if current is None or current.head is None or not set(pending.triggers) <= set(current.triggers):
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=head,
                branch_publication=branch_receipt,
                state=state,
                reconciled=False,
            )

        first_checkpoint = any(
            trigger.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK for trigger in pending.triggers
        )
        draft_receipt = None
        if first_checkpoint:
            draft_receipt = self._draft_pull_request_publisher.publish(
                CreateOrReconcileDraftPullRequest(
                    change_id=change_id,
                    operation_id=_checkpoint_operation_id("pull-request", change_id, head, summary),
                    published_head=head,
                    title=pull_request_title,
                    generated_summary=summary,
                )
            )
        summary_receipt = self._draft_pull_request_publisher.update_generated_summary(
            UpdateGeneratedPullRequestSummary(
                change_id=change_id,
                operation_id=_checkpoint_operation_id("summary", change_id, head, summary),
                published_head=head,
                generated_summary=summary,
            )
        )
        state = runtime.acknowledge_checkpoint_publication(pending, head)
        return DeliveryCheckpointReconciliationResult(
            change_id=change_id,
            attempted_head=head,
            branch_publication=branch_receipt,
            draft_pull_request=draft_receipt,
            generated_summary=summary_receipt,
            state=state,
            reconciled=state.pending_checkpoint is None,
        )

    def read_design_session(self, change_id: str) -> VerifiedDesignPackage:
        """Return one verified authored Design package and its current identity."""
        return self._package_store.read_verified(change_id)

    def revise_design_session(
        self,
        change_id: str,
        expected_package_id: str,
        intent_bytes: bytes,
        design_bytes: bytes,
    ) -> VerifiedDesignPackage:
        """Replace authored Design bytes for one exact package identity."""
        return self._package_store.revise(change_id, expected_package_id, intent_bytes, design_bytes)

    def publish_design_checkpoint(self, change_id: str) -> DesignCheckpointResult:
        """Checkpoint one verified active package without touching product refs."""
        return self._package_store.checkpoint(change_id)

    def derive_delivery_contract(self, change_id: str) -> DeliveryCompilationResult:
        """Compile one verified package without publishing generated authority."""
        package = self._package_store.read_verified(change_id)
        return compile_delivery_contract(change_id, package.intent_bytes, package.design_bytes)

    def validate_delivery_contract(self, change_id: str) -> DeliveryCompilationResult:
        """Return deterministic compiler diagnostics for one verified package."""
        return self.derive_delivery_contract(change_id)

    def admit_delivery_change(self, request: DeliveryAdmissionRequest) -> DeliveryAdmissionResult:
        """Admit source-bound Delivery authority through the owning registry."""
        with self._coordinator.acquisition_lock():
            self._workspace_manager.validate_recovery(request.change_id, request.recovery_reviewed_head)
            result = self._authority_registry.admit(request)
            coordination = self._workspace_manager.create(
                request.change_id,
                recovery_reviewed_head=request.recovery_reviewed_head,
            )
            self._runtimes[request.change_id] = DeliveryRuntime(
                self._target_root,
                result.contract,
                workspace_manager=self._workspace_manager,
                migration_reviewed_head=coordination.last_reviewed_commit,
            )
            return result

    def publish_delivery_plan(
        self,
        change_id: str,
        request: PublishDeliveryPlan,
    ) -> DeliveryPlanCandidate:
        """Publish one validated Planning candidate through its exact runtime."""
        return self._runtime(change_id).publish_plan(request)

    def publish_delivery_result(
        self,
        change_id: str,
        request: PublishDeliveryResult,
    ) -> DeliveryResultCandidate:
        """Publish one validated Build result through its exact runtime."""
        return self._runtime(change_id).publish_result(request)

    def transition_delivery(
        self,
        change_id: str,
        request: DeliveryTransition,
    ) -> OutcomeAuthorityBinding:
        """Apply one validated mechanical transition through its exact runtime."""
        runtime = self._runtime(change_id)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return runtime.transition(request)

    def list_integration_attention(self) -> tuple[DeliveryIntegrationAttentionStatus, ...]:
        """List non-retryable Integration attention in stable identity order."""
        statuses = []
        for snapshot in self._portfolio_snapshots():
            attention = snapshot.frontier.integration_attention
            if (
                attention is None
                or snapshot.frontier.integration_repair_claim is not None
                or self._integration_attention_is_superseded(snapshot.contract.change_id, attention)
            ):
                continue
            disposition = integration_attention_disposition(attention.code)
            if disposition == DeliveryIntegrationAttentionDisposition.RETRYABLE:
                continue
            statuses.append(
                DeliveryIntegrationAttentionStatus(
                    change_id=snapshot.contract.change_id,
                    code=attention.code,
                    disposition=disposition,
                    retry_condition=attention.retry_condition,
                )
            )
        return tuple(statuses)

    def _integration_attention_is_superseded(
        self,
        change_id: str,
        attention: DeliveryIntegrationAttention,
    ) -> bool:
        try:
            context = self._workspace_manager.integration_context(change_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail(f"current Integration target is unavailable for {change_id}", exc)
        return attention.target_head != context.target_head

    def show_integration_attention(self, change_id: str) -> DeliveryIntegrationAttention | None:
        """Return current typed Integration attention without mutating runtime state."""
        return self._runtime(change_id).integration_attention()

    def list_work_items(self) -> tuple[WorkItemProjection, ...]:
        """List bounded work-item projections in stable portfolio order."""
        projections = []
        for snapshot in self._portfolio_snapshots():
            if self._snapshot_change_stage(snapshot) == DeliveryChangeStage.COMPLETED:
                continue
            projections.extend(WorkItemProjector(snapshot).list_items())
        return tuple(
            sorted(
                projections,
                key=lambda item: (
                    item.stage.value == "completed",
                    item.change_id,
                    item.work_item_id,
                ),
            )
        )

    def list_work_item_groups(self) -> tuple[ChangeGroupView, ...]:
        """List grouped Cockpit views from exact per-change snapshots."""
        return tuple(
            WorkItemProjector(snapshot).group_view()
            for snapshot in self._portfolio_snapshots()
            if self._snapshot_change_stage(snapshot) != DeliveryChangeStage.COMPLETED
        )

    def portfolio_read_view(self) -> PortfolioReadView:
        """Return grouped work and operating facts from one immutable capture."""
        snapshots = self._portfolio_snapshots()
        groups = tuple(
            WorkItemProjector(snapshot).group_view()
            for snapshot in snapshots
            if self._snapshot_change_stage(snapshot) != DeliveryChangeStage.COMPLETED
        )
        return PortfolioReadView(
            groups=groups,
            operating=self._portfolio_operating_view(snapshots, groups),
        )

    def portfolio_operating_view(self) -> PortfolioOperatingView:
        """Return portfolio-wide operating facts and advisory session guidance."""
        snapshots = self._portfolio_snapshots()
        groups = tuple(
            WorkItemProjector(snapshot).group_view()
            for snapshot in snapshots
            if self._snapshot_change_stage(snapshot) != DeliveryChangeStage.COMPLETED
        )
        return self._portfolio_operating_view(snapshots, groups)

    def _portfolio_operating_view(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
        groups: tuple[ChangeGroupView, ...],
    ) -> PortfolioOperatingView:
        runtime_ids = set(self._runtimes)
        draft_design_ids = tuple(
            package.change_id for package in self._package_store.list_verified() if package.change_id not in runtime_ids
        )
        design_required_ids = tuple(
            change_id
            for change_id, runtime in sorted(self._runtimes.items())
            if runtime.change_stage() == DeliveryChangeStage.DESIGN
        )
        claimed = self._claimed_work(snapshots)
        queued = self._queued_work(snapshots)
        interventions = tuple(
            PortfolioWorkReference(
                change_id=item.change_id,
                item_key=item.item_key,
                scope=_operating_scope(item.scope),
            )
            for group in groups
            for item in group.items
            if item.needs == WorkItemNeed.YOU
        )
        dependency_waits = tuple(
            PortfolioWorkReference(
                change_id=item.change_id,
                item_key=item.item_key,
                scope=_operating_scope(item.scope),
            )
            for group in groups
            for item in group.items
            if item.needs == WorkItemNeed.DEPENDENCY
        )
        unfinished_runtime_count = sum(
            self._snapshot_change_stage(snapshot) != DeliveryChangeStage.COMPLETED for snapshot in snapshots
        )
        unfinished_change_count = unfinished_runtime_count
        design_change_ids = tuple(dict.fromkeys((*draft_design_ids, *design_required_ids)))
        guidance = derive_portfolio_guidance(
            PortfolioGuidanceFacts(
                unfinished_change_count=unfinished_change_count,
                design_change_ids=design_change_ids,
                claimed=claimed,
                queued=queued,
                interventions=interventions,
                dependency_waits=dependency_waits,
            )
        )
        return PortfolioOperatingView(
            unfinished_change_count=unfinished_change_count,
            completed_change_count=len(self._runtimes) - unfinished_runtime_count,
            draft_design_change_ids=draft_design_ids,
            design_required_change_ids=design_required_ids,
            claimed=claimed,
            queued_for_orchestration=queued,
            interventions=interventions,
            dependency_waits=dependency_waits,
            guidance=guidance,
        )

    def _claimed_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        claimed = []
        for snapshot in snapshots:
            claimed.extend(
                PortfolioWorkReference(
                    change_id=snapshot.contract.change_id,
                    item_key=f"outcome:{binding.outcome_id}",
                    scope=PortfolioWorkScope.OUTCOME,
                )
                for binding in snapshot.frontier.bindings
                if binding.active_claim is not None
            )
        return tuple(claimed)

    def _queued_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        return self._queued_outcome_work(snapshots)

    def _queued_outcome_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        ranked = tuple(
            candidate for snapshot in snapshots if (candidate := self._queued_outcome_candidate(snapshot)) is not None
        )
        return tuple(item[4] for item in sorted(ranked, key=lambda item: item[:4]))

    def _queued_outcome_candidate(
        self,
        snapshot: DeliveryPortfolioSnapshot,
    ) -> tuple[int, int, int, str, PortfolioWorkReference] | None:
        if self._snapshot_change_stage(
            snapshot
        ) != DeliveryChangeStage.ACTIVE_DELIVERY or self._snapshot_has_active_claims(snapshot):
            return None
        completed = {
            binding.outcome_id for binding in snapshot.frontier.bindings if binding.stage == DeliveryStage.COMPLETED
        }
        bindings = {binding.outcome_id: binding for binding in snapshot.frontier.bindings}
        ranked = []
        for outcome_index, outcome in enumerate(snapshot.contract.outcomes):
            binding = bindings[outcome.outcome_id]
            if (
                binding.stage in {DeliveryStage.DESIGN, DeliveryStage.COMPLETED}
                or binding.active_claim is not None
                or (binding.block is not None and not binding.block.resolved)
                or not set(outcome.dependency_ids) <= completed
            ):
                continue
            task_index = self._snapshot_task_index(binding)
            if task_index is None:
                continue
            ranked.append(
                (
                    self._snapshot_dependency_depth(snapshot, outcome.outcome_id),
                    outcome_index,
                    task_index,
                    snapshot.contract.change_id,
                    PortfolioWorkReference(
                        change_id=snapshot.contract.change_id,
                        item_key=f"outcome:{outcome.outcome_id}",
                        scope=PortfolioWorkScope.OUTCOME,
                    ),
                )
            )
        return min(ranked, key=lambda item: item[:4]) if ranked else None

    @staticmethod
    def _snapshot_task_index(binding: OutcomeAuthorityBinding) -> int | None:
        if binding.stage != DeliveryStage.IMPLEMENTATION:
            return 0
        completed = {result.task_id for result in binding.results}
        task = next(
            (item for item in binding.tasks if item.task_id not in completed and set(item.dependency_ids) <= completed),
            None,
        )
        return binding.task_ids.index(task.task_id) if task is not None else None

    def show_work_item(self, change_id: str, work_item_id: str) -> WorkItemDetail:
        """Show bounded semantic detail from one exact change projector."""
        try:
            return self._work_item_projector(self._runtime(change_id)).show(work_item_id)
        except KeyError as exc:
            self._fail(f"work item is absent: {work_item_id}", exc)

    def show_work_item_view(self, change_id: str, item_key: str) -> WorkItemDetailView:
        """Show semantic and operator detail from one exact snapshot."""
        try:
            return self._work_item_projector(self._runtime(change_id)).show_view(item_key)
        except (KeyError, StopIteration) as exc:
            self._fail(f"work item is absent: {item_key}", exc)

    def show_operator_context(self, change_id: str, outcome_id: str) -> DeliveryOperatorContext:
        """Show current bounded operator state from one exact runtime binding."""
        runtime = self._runtime(change_id)
        if outcome_id == change_id:
            if runtime.change_stage() != DeliveryChangeStage.INTEGRATION:
                self._fail("change work item is not in Integration")
            return DeliveryOperatorContext(
                change_id=change_id,
                outcome_id=outcome_id,
                stage=DeliveryStage.COMPLETED,
                integration_attention=_operator_integration_attention(runtime.integration_attention()),
            )
        binding = runtime.show_binding(outcome_id)
        return DeliveryOperatorContext(
            change_id=change_id,
            outcome_id=outcome_id,
            stage=binding.stage,
            block=binding.block,
            requests=binding.requests,
            active_claim=_operator_claim(binding.active_claim),
            return_context=binding.return_context,
            recovery_attention=_operator_recovery_attention(binding.recovery_attention),
        )

    def resolve_request(
        self,
        change_id: str,
        request_id: str,
        resolution: DeliveryRequestResolution,
    ) -> DeliveryRequest:
        """Persist one request resolution by delegating to the owning runtime."""
        with self._coordinator.acquisition_lock():
            return self._runtime(change_id).resolve_request(request_id, resolution)

    def clear_block(
        self,
        change_id: str,
        outcome_id: str,
        block_id: str,
        operator_note: str,
        locators: tuple[str, ...],
    ) -> OutcomeAuthorityBinding:
        """Clear a requestless same-stage block with operator evidence via runtime."""
        with self._coordinator.acquisition_lock():
            return self._runtime(change_id).unblock(outcome_id, block_id, operator_note, locators)

    def administrative_move(
        self,
        change_id: str,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Delegate an authorized operator backward movement to the owning runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                return runtime.administrative_move(request)

    def preview_administrative_move(
        self,
        change_id: str,
        outcome_id: str,
        target: DeliveryStage,
    ) -> AdministrativeDeliveryMovePreview:
        """Preview one exact backward movement without mutating authority."""
        return self._runtime(change_id).preview_administrative_move(outcome_id, target)

    def _work_item_projector(self, runtime: DeliveryRuntime) -> WorkItemProjector:
        return WorkItemProjector(self._delivery_snapshot(runtime))

    def _portfolio_snapshots(self) -> tuple[DeliveryPortfolioSnapshot, ...]:
        return tuple(self._delivery_snapshot(runtime) for _change_id, runtime in sorted(self._runtimes.items()))

    def _delivery_snapshot(self, runtime: DeliveryRuntime) -> DeliveryPortfolioSnapshot:
        return DeliveryPortfolioSnapshot.capture(
            runtime.contract,
            runtime.frontier_bytes(),
        )

    @staticmethod
    def _snapshot_change_stage(snapshot: DeliveryPortfolioSnapshot) -> DeliveryChangeStage:
        if snapshot.frontier.change_completion is not None or snapshot.frontier.integration_result_id is not None:
            return DeliveryChangeStage.COMPLETED
        if snapshot.frontier.ready is not None:
            return DeliveryChangeStage.AWAITING_MERGE
        if snapshot.frontier.finalization is not None:
            return DeliveryChangeStage.FINALIZED
        stages = {binding.stage for binding in snapshot.frontier.bindings}
        if DeliveryStage.DESIGN in stages:
            return DeliveryChangeStage.DESIGN
        if stages == {DeliveryStage.COMPLETED} and snapshot.frontier.finalization_invalidation is None:
            return DeliveryChangeStage.INTEGRATION
        return DeliveryChangeStage.ACTIVE_DELIVERY

    @staticmethod
    def _snapshot_has_active_claims(snapshot: DeliveryPortfolioSnapshot) -> bool:
        return any(binding.active_claim is not None for binding in snapshot.frontier.bindings)

    @staticmethod
    def _snapshot_dependency_depth(snapshot: DeliveryPortfolioSnapshot, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in snapshot.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)

    def list_completed_changes(self, cursor: str | None = None, limit: int = 100) -> CompletedChangePage:
        """List one bounded page rebuilt from configured target history."""
        return self._completed_history().list(cursor, limit)

    def search_completed_changes(
        self,
        query: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> CompletedChangePage:
        """Search completed semantic summaries in configured target history."""
        return self._completed_history().search(query, cursor, limit)

    def show_completed_change(
        self,
        change_id: str,
        completion_id: str | None = None,
    ) -> CompletedChangeRecord:
        """Show one verified completed-history record by exact identity."""
        return self._completed_history().show(change_id, completion_id)

    def _completed_history(self) -> CompletedHistoryCatalog:
        if self._completed_history_catalog is None:
            self._fail("completed-history catalog dependency is not configured")
        return self._completed_history_catalog

    def acquire_frontier_work(self) -> DeliveryAcquisitionResult:
        """Start at most one ready claim per available execution slot."""
        with self._coordinator.acquisition_lock():
            for change_id in self._runtimes:
                self._workspace_manager.refresh_integration_target(change_id)
            occupied = sum(len(runtime.active_claims()) for runtime in self._runtimes.values())
            available = max(self._execution_capacity - occupied, 0)
            launches: list[DeliveryLaunchPackage] = []
            failures: list[DeliveryAcquisitionFailure] = []
            for candidate in self._candidates():
                if available == 0:
                    break
                if candidate.role == DeliveryWorkerRole.BUILDER and not self._coordinator.writer_capacity_available():
                    continue
                source = self._prepare_source(
                    candidate.change_id,
                    candidate.runtime,
                    candidate.binding.outcome_id,
                )
                if isinstance(source, DeliveryAcquisitionFailure):
                    failures.append(source)
                    continue
                launch = self._activate_candidate(candidate, source)
                available -= 1
                if isinstance(launch, DeliveryAcquisitionFailure):
                    failures.append(launch)
                    continue
                launches.append(launch)
            return DeliveryAcquisitionResult(
                launch_packages=tuple(launches),
                integration_attention=self.list_integration_attention(),
                failures=tuple(failures),
            )

    def show_plan_context(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryPlanContext:
        """Project exact same-outcome Planning authority for one active claim."""
        runtime = self._runtime(change_id)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        if binding.stage != DeliveryStage.PLANNING:
            self._fail("active claim is not Planning work")
        launch = self._current_launch(change_id, runtime, binding)
        outcome = self._outcome(runtime, outcome_id)
        return DeliveryPlanContext(
            launch=launch,
            outcome=outcome,
            commitments=self._commitments(runtime, outcome.commitment_ids),
            requests=binding.requests,
            return_context=binding.return_context,
        )

    def show_build_context(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryBuildContext:
        """Project exact task and predecessor authority for one active Build claim."""
        runtime = self._runtime(change_id)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_task_id is None:
            self._fail("active claim is not Build work")
        launch = self._current_launch(change_id, runtime, binding)
        task = next(item for item in binding.tasks if item.task_id == binding.active_task_id)
        predecessor_task_ids = set(task.dependency_ids)
        outcome = self._outcome(runtime, outcome_id)
        dependency_outcomes = set(outcome.dependency_ids)
        predecessor_results = tuple(
            result
            for candidate in runtime.contract.outcomes
            for result in runtime.show_binding(candidate.outcome_id).results
            if result.task_id in predecessor_task_ids or candidate.outcome_id in dependency_outcomes
        )
        return DeliveryBuildContext(
            launch=launch,
            task=task,
            task_digest=task.digest,
            commitments=self._commitments(runtime, task.commitment_ids),
            predecessor_results=predecessor_results,
            requests=binding.requests,
            return_context=binding.return_context,
            recovery_attention=binding.recovery_attention,
        )

    def recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryClaimRecoveryResult:
        """Remove one exact failed claim or retain deterministic Build repair attention."""
        with self._coordinator.acquisition_lock():
            return self._recover_claim(change_id, outcome_id, attempt_id, claim_id)

    def recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        """Restart and remove one exact failed Integration repair claim."""
        with self._coordinator.acquisition_lock():
            return self._recover_integration_repair_claim(change_id, attempt_id, claim_id)

    def _recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        runtime = self._runtime(change_id)
        runtime.require_integration_repair_claim(attempt_id, claim_id)
        snapshot = self._workspace_manager.recovery_snapshot(change_id, attempt_id)
        preserved_commit = snapshot.preserved_commit or snapshot.branch_head
        if snapshot.writer is not None:
            if not self._active_recovery_matches(snapshot, attempt_id, claim_id):
                self._fail("repair recovery does not match active writer custody")
            self._workspace_manager.restart(change_id, attempt_id, preserved_commit)
        elif not self._released_recovery_matches(snapshot):
            self._fail("released repair recovery does not match reviewed workspace state")
        runtime.remove_integration_repair_claim(attempt_id, claim_id)
        return DeliveryIntegrationRepairRecoveryResult(
            change_id=change_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            preserved_commit=preserved_commit,
        )

    def _recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryClaimRecoveryResult:
        runtime = self._runtime(change_id)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        claim = binding.active_claim
        if claim is None:
            self._fail("outcome has no active claim")
        if claim.worker_role != DeliveryWorkerRole.BUILDER:
            runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
            return self._recovered(change_id, outcome_id, attempt_id, claim_id)
        snapshot = self._workspace_manager.recovery_snapshot(change_id, attempt_id)
        if snapshot.writer is None:
            if self._released_recovery_matches(snapshot):
                runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
                return self._recovered(
                    change_id,
                    outcome_id,
                    attempt_id,
                    claim_id,
                    snapshot.preserved_commit,
                )
            return self._retain_recovery_attention(runtime, outcome_id, claim, snapshot)
        if not self._active_recovery_matches(snapshot, attempt_id, claim_id):
            return self._retain_recovery_attention(runtime, outcome_id, claim, snapshot)
        rejected_head = snapshot.preserved_commit or snapshot.branch_head
        self._workspace_manager.restart(change_id, attempt_id, rejected_head)
        runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
        return self._recovered(
            change_id,
            outcome_id,
            attempt_id,
            claim_id,
            rejected_head,
        )

    def _candidates(self) -> tuple[_Candidate, ...]:
        candidates = []
        for change_id, runtime in self._runtimes.items():
            if runtime.active_claims() or runtime.change_stage() != DeliveryChangeStage.ACTIVE_DELIVERY:
                continue
            claimable = set(runtime.claimable_outcome_ids())
            ranked = []
            for outcome_index, outcome in enumerate(runtime.contract.outcomes):
                if outcome.outcome_id not in claimable:
                    continue
                binding = runtime.show_binding(outcome.outcome_id)
                task_id = None
                task_index = 0
                if binding.stage == DeliveryStage.IMPLEMENTATION:
                    task_ids = runtime.claimable_task_ids(outcome.outcome_id)
                    if not task_ids:
                        continue
                    task_id = task_ids[0]
                    task_index = binding.task_ids.index(task_id)
                role = {
                    DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
                    DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
                }[binding.stage]
                ranked.append(
                    _Candidate(
                        sort_key=(
                            self._dependency_depth(runtime, outcome.outcome_id),
                            outcome_index,
                            task_index,
                            change_id,
                        ),
                        change_id=change_id,
                        runtime=runtime,
                        binding=binding,
                        task_id=task_id,
                        role=role,
                    )
                )
            if ranked:
                candidates.append(min(ranked, key=lambda item: item.sort_key))
        return tuple(sorted(candidates, key=lambda item: item.sort_key))

    def _prepare_source(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        outcome_id: str,
    ) -> _PreparedSource | DeliveryAcquisitionFailure:
        try:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            coordination = self._workspace_manager.show(change_id)
            source_head = self._workspace_manager.reviewed_source_head(change_id)
        except (OSError, RuntimeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id=outcome_id,
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Restore the admitted package and clean reviewed source boundary.",
            )
        return _PreparedSource(package, coordination, source_head)

    def _activate_candidate(
        self,
        candidate: _Candidate,
        source: _PreparedSource,
    ) -> DeliveryLaunchPackage | DeliveryAcquisitionFailure:
        claim = self._new_claim(candidate.role, candidate.task_id)
        candidate.runtime.activate_claim(ActivateDeliveryClaim(outcome_id=candidate.binding.outcome_id, claim=claim))
        writer = None
        if candidate.role == DeliveryWorkerRole.BUILDER:
            try:
                coordination = self._coordinator.acquire(
                    candidate.change_id,
                    ChangeWriter(
                        attempt_id=claim.attempt_id,
                        claim_id=claim.claim_id,
                        actor_id=claim.owner_id,
                        process_id=claim.process_id,
                        claimed_at=claim.started_at,
                        job_id=1,
                        kind="build",
                    ),
                )
            except CoordinationConflictError as exc:
                return DeliveryAcquisitionFailure(
                    change_id=candidate.change_id,
                    outcome_id=candidate.binding.outcome_id,
                    attempt_id=claim.attempt_id,
                    claim_id=claim.claim_id,
                    code=exc.code,
                    detail=str(exc),
                    retry_condition="Remove the exact failed claim after reconciling writer custody.",
                )
            writer = coordination.writer
        return self._launch_package(candidate, claim, source, writer)

    def _current_launch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        binding: OutcomeAuthorityBinding,
    ) -> DeliveryLaunchPackage:
        source = self._prepare_source(change_id, runtime, binding.outcome_id)
        if isinstance(source, DeliveryAcquisitionFailure):
            self._fail(source.detail)
        claim = binding.active_claim
        if claim is None:
            self._fail("outcome has no active claim")
        writer = source.coordination.writer if claim.worker_role == DeliveryWorkerRole.BUILDER else None
        candidate = _Candidate((0, 0, 0, change_id), change_id, runtime, binding, claim.task_id, claim.worker_role)
        return self._launch_package(candidate, claim, source, writer)

    def _launch_package(
        self,
        candidate: _Candidate,
        claim: DeliveryActiveClaim,
        source: _PreparedSource,
        writer: ChangeWriter | None,
    ) -> DeliveryLaunchPackage:
        return DeliveryLaunchPackage(
            change_id=candidate.change_id,
            authority_digest=candidate.runtime.authority_digest,
            outcome_id=candidate.binding.outcome_id,
            plan_scope_id=candidate.binding.plan_scope_id,
            task_id=candidate.task_id,
            claim=claim,
            policy=self._policies[candidate.role],
            package_id=source.package.package_id,
            package_root=self._package_root / candidate.change_id,
            worktree_path=source.coordination.worktree_path,
            branch=source.coordination.branch,
            source_head=source.source_head,
            integration_target=source.coordination.integration_target,
            last_reviewed_commit=source.coordination.last_reviewed_commit,
            writer=writer,
        )

    def _new_claim(self, role: DeliveryWorkerRole, task_id: str | None) -> DeliveryActiveClaim:
        return DeliveryActiveClaim(
            attempt_id=self._identity_factory(),
            claim_id=self._identity_factory(),
            owner_id=self._identity_factory(),
            process_id=self._identity_factory(),
            started_at=self._clock(),
            worker_role=role,
            task_id=task_id,
        )

    @staticmethod
    def _released_recovery_matches(snapshot: WorkspaceRecoverySnapshot) -> bool:
        return (
            snapshot.clean
            and snapshot.branch_head == snapshot.last_reviewed_commit
            and snapshot.worktree_head == snapshot.last_reviewed_commit
            and snapshot.worktree_branch == snapshot.branch
        )

    @staticmethod
    def _active_recovery_matches(
        snapshot: WorkspaceRecoverySnapshot,
        attempt_id: str,
        claim_id: str,
    ) -> bool:
        writer = snapshot.writer
        if (
            writer is None
            or writer.attempt_id != attempt_id
            or writer.claim_id != claim_id
            or not snapshot.reviewed_ancestor
            or not snapshot.preserved_reviewed_ancestor
        ):
            return False
        rejected_head = snapshot.preserved_commit or snapshot.branch_head
        if snapshot.branch_head not in {rejected_head, snapshot.last_reviewed_commit}:
            return False
        if snapshot.worktree_head is None:
            return snapshot.preserved_commit is not None and snapshot.worktree_branch is None
        return (
            snapshot.clean
            and snapshot.worktree_head == snapshot.branch_head
            and snapshot.worktree_branch == snapshot.branch
        )

    def _retain_recovery_attention(
        self,
        runtime: DeliveryRuntime,
        outcome_id: str,
        claim: DeliveryActiveClaim,
        snapshot: WorkspaceRecoverySnapshot,
    ) -> DeliveryClaimRecoveryResult:
        attention = DeliveryRecoveryAttention(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            reason=self._recovery_reason(snapshot, claim),
            worktree_path=str(snapshot.worktree_path),
            branch_head=snapshot.branch_head,
            worktree_head=snapshot.worktree_head,
            last_reviewed_commit=snapshot.last_reviewed_commit,
            writer_claim_id=snapshot.writer.claim_id if snapshot.writer is not None else None,
            custody_retained=snapshot.writer is not None,
            retry_condition="Restore a clean recorded worktree and reconcile exact writer custody.",
        )
        runtime.publish_recovery_attention(outcome_id, attention)
        return DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.ATTENTION,
            change_id=runtime.contract.change_id,
            outcome_id=outcome_id,
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            attention=attention,
        )

    @staticmethod
    def _recovery_reason(snapshot: WorkspaceRecoverySnapshot, claim: DeliveryActiveClaim) -> str:
        writer = snapshot.writer
        if writer is None:
            return "Build source is outside the reviewed boundary without writer custody."
        if writer.attempt_id != claim.attempt_id or writer.claim_id != claim.claim_id:
            return "Build claim does not match recorded writer custody."
        if not snapshot.clean:
            return "Build worktree contains uncommitted changes."
        if snapshot.worktree_branch != snapshot.branch or snapshot.worktree_head != snapshot.branch_head:
            return "Build worktree does not match its recorded branch head."
        if not snapshot.reviewed_ancestor:
            return "Build branch does not descend from its reviewed boundary."
        return "Build attempt history ref conflicts with the current branch head."

    @staticmethod
    def _recovered(
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        preserved_commit: str | None = None,
    ) -> DeliveryClaimRecoveryResult:
        return DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.RECOVERED,
            change_id=change_id,
            outcome_id=outcome_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            preserved_commit=preserved_commit,
            preserved_ref=(f"refs/owlbear/attempts/{change_id}/{attempt_id}" if preserved_commit is not None else None),
        )

    def _validate_package_authority(self, runtime: DeliveryRuntime, package: VerifiedDesignPackage) -> None:
        if hashlib.sha256(package.authority_bytes).hexdigest() != runtime.authority_digest:
            self._fail("active package authority does not match the Delivery runtime")
        source_digests = {binding.source_name: binding.sha256 for binding in runtime.contract.source_bindings}
        if source_digests != {
            "intent.md": package.manifest.intent_sha256,
            "design.md": package.manifest.design_sha256,
        }:
            self._fail("active package sources do not match admitted Delivery bindings")

    def _dependency_depth(self, runtime: DeliveryRuntime, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in runtime.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)

    def _runtime(self, change_id: str) -> DeliveryRuntime:
        try:
            return self._runtimes[change_id]
        except KeyError as exc:
            self._fail(f"Delivery runtime is absent: {change_id}", exc)

    def _checkpoint_lock_root(self, change_id: str) -> Path:
        return self._target_root / "publications/checkpoints/locks" / change_id

    @staticmethod
    def _outcome(runtime: DeliveryRuntime, outcome_id: str) -> DeliveryOutcome:
        return next(item for item in runtime.contract.outcomes if item.outcome_id == outcome_id)

    @staticmethod
    def _commitments(runtime: DeliveryRuntime, commitment_ids: tuple[str, ...]) -> tuple[DeliveryCommitment, ...]:
        selected = set(commitment_ids)
        return tuple(item for item in runtime.contract.commitments if item.commitment_id in selected)

    @staticmethod
    def _fail(message: str, cause: Exception | None = None) -> Never:
        raise PortfolioApplicationError(message) from cause


__all__ = [
    "DeliveryAcquisitionFailure",
    "DeliveryAcquisitionResult",
    "DeliveryBuildContext",
    "DeliveryClaimRecoveryResult",
    "DeliveryClaimRecoveryStatus",
    "DeliveryFinalizationContext",
    "DeliveryIntegrationAttentionStatus",
    "DeliveryLaunchPackage",
    "DeliveryPlanContext",
    "DeliveryRolePolicy",
    "PortfolioApplication",
    "PortfolioApplicationConfig",
    "PortfolioApplicationDependencies",
    "PortfolioApplicationError",
    "PortfolioApplicationHooks",
]
