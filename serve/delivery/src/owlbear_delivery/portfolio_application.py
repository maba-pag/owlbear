"""Deterministic portfolio acquisition and bounded worker context."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.change_workspace import (
    AtomicIntegrationPreparation,
    AtomicIntegrationResult,
    ChangeCoordination,
    ChangeWorkspaceManager,
    ChangeWriter,
    CoordinationConflictError,
    ExternalCompletionProposal,
    IntegrationContext,
    IntegrationRepairCandidate,
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
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryIntegrationCandidate,
    DeliveryIntegrationCompletion,
    DeliveryIntegrationRepair,
    DeliveryIntegrationRepairAuthorityAttention,
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
    OutcomeAuthorityBinding,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    integration_attention_disposition,
)
from owlbear_delivery.design_package import (
    CompletionCapture,
    CompletionPackageSnapshot,
    DesignCheckpointResult,
    DesignPackageConflictError,
    DesignPackageResult,
)
from owlbear_delivery.portfolio_operating import (
    PortfolioGuidanceFacts,
    PortfolioOperatingView,
    PortfolioWorkReference,
    PortfolioWorkScope,
    derive_portfolio_guidance,
)
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
    WorkItemScope,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery.change_publication import (
        ChangeBranchPublicationReceipt,
        ChangeBranchPublisher,
        PublishChangeBranch,
    )
    from owlbear_delivery.completed_history import (
        CompletedChangePage,
        CompletedChangeRecord,
        CompletedHistoryCatalog,
    )
    from owlbear_delivery.design_package import DesignPackageStore, VerifiedDesignPackage
    from owlbear_delivery.draft_pull_request import (
        CreateOrReconcileDraftPullRequest,
        DraftPullRequestPublicationReceipt,
        DraftPullRequestPublisher,
        GeneratedPullRequestSummaryReceipt,
        ObserveChangePublicationChecks,
        UpdateGeneratedPullRequestSummary,
    )
    from owlbear_delivery.integration_verification import IntegrationVerificationReceipt, IntegrationVerifier
    from owlbear_delivery.publication_provider import PublicationCheckSnapshot
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


_COMPLETED_ROOT = ".owlbear/completed"
_PROVIDER_ACCEPTANCE_REQUIRED = (
    "local target ancestry is not provider acceptance evidence; completion requires an observed merged pull request"
)


def _operating_scope(scope: WorkItemScope) -> PortfolioWorkScope:
    if scope == WorkItemScope.CHANGE_INTEGRATION:
        return PortfolioWorkScope.INTEGRATION
    return PortfolioWorkScope.OUTCOME


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


class DeliveryIntegrationRepairLaunchPackage(_ApplicationModel):
    """Bounded change-level launch for one claimed Integration repair."""

    change_id: str = Field(min_length=1)
    claim: DeliveryActiveClaim
    policy: DeliveryRolePolicy
    attention: DeliveryIntegrationAttention
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_root: Path
    worktree_path: Path
    branch: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer: ChangeWriter

    @model_validator(mode="after")
    def _validate_repair_custody(self) -> DeliveryIntegrationRepairLaunchPackage:
        if (
            self.claim.worker_role != DeliveryWorkerRole.INTEGRATION_REPAIRER
            or self.policy.worker_role != self.claim.worker_role
            or self.writer.kind != "repair"
            or self.writer.attempt_id != self.claim.attempt_id
            or self.writer.claim_id != self.claim.claim_id
            or self.writer.actor_id != self.claim.owner_id
            or self.writer.process_id != self.claim.process_id
        ):
            message = "repair launch policy and writer custody must match the active claim"
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


class DeliveryIntegrationRepairAcquisitionFailure(_ApplicationModel):
    """Fail-closed preparation result for one change-level repair claim."""

    change_id: str = Field(min_length=1)
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
    """Launchable claims and unclaimed Integration-ready changes from one refresh."""

    launch_packages: tuple[DeliveryLaunchPackage, ...]
    repair_launch_packages: tuple[DeliveryIntegrationRepairLaunchPackage, ...] = ()
    integration_ready_change_ids: tuple[str, ...]
    integration_attention: tuple[DeliveryIntegrationAttentionStatus, ...] = ()
    failures: tuple[DeliveryAcquisitionFailure, ...] = ()
    repair_failures: tuple[DeliveryIntegrationRepairAcquisitionFailure, ...] = ()
    recoveries: tuple[DeliveryClaimRecoveryResult, ...] = ()
    repair_recoveries: tuple[DeliveryIntegrationRepairRecoveryResult, ...] = ()


class DeliveryExpiredClaimRecoveries(_ApplicationModel):
    """Exact recovery results for claims whose execution lease elapsed."""

    recoveries: tuple[DeliveryClaimRecoveryResult, ...] = ()
    repair_recoveries: tuple[DeliveryIntegrationRepairRecoveryResult, ...] = ()


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


class DeliveryIntegrationRepairContext(_ApplicationModel):
    """Current claim-bound source and conflict authority for Integration repair."""

    launch: DeliveryIntegrationRepairLaunchPackage


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


class DeliveryIntegrationResult(_ApplicationModel):
    """One committed atomic publication or retained typed Integration attention."""

    change_id: str = Field(min_length=1)
    candidate: DeliveryIntegrationCandidate | None = None
    completion: DeliveryIntegrationCompletion | None = None
    attention: DeliveryIntegrationAttention | None = None
    replayed: bool = False

    @model_validator(mode="after")
    def _validate_disposition(self) -> DeliveryIntegrationResult:
        if (self.completion is None) == (self.attention is None):
            message = "Integration result requires completion or attention"
            raise ValueError(message)
        if self.attention is not None and self.replayed:
            message = "Integration attention cannot be a completed replay"
            raise ValueError(message)
        return self


class ExternalCompletionResult(_ApplicationModel):
    """One detached completion proposal, acknowledged completion, or typed attention."""

    change_id: str = Field(min_length=1)
    proposal: ExternalCompletionProposal | None = None
    completion: DeliveryIntegrationCompletion | None = None
    attention: DeliveryIntegrationAttention | None = None
    replayed: bool = False

    @model_validator(mode="after")
    def _validate_disposition(self) -> ExternalCompletionResult:
        dispositions = (self.proposal, self.completion, self.attention)
        if sum(disposition is not None for disposition in dispositions) != 1:
            message = "external completion requires one proposal, completion, or attention"
            raise ValueError(message)
        if self.completion is None and self.replayed:
            message = "only external completion acknowledgment can replay"
            raise ValueError(message)
        return self


class PortfolioApplicationError(RuntimeError):
    """Portfolio preparation or scoped context validation failed closed."""

    code = "ERR_DELIVERY_PORTFOLIO"


class PortfolioReadView(_ApplicationModel):
    """Grouped work and operating facts derived from one portfolio capture."""

    groups: tuple[ChangeGroupView, ...]
    operating: PortfolioOperatingView


class PortfolioApplicationConfig(_ApplicationModel):
    """Configured capacity, source root, and complete stage-role policy."""

    package_root: Path
    execution_capacity: int = Field(gt=0)
    role_policies: tuple[DeliveryRolePolicy, ...] = Field(min_length=3, max_length=3)
    claim_ttl_seconds: int = Field(default=30 * 60, gt=0)

    @model_validator(mode="after")
    def _validate_roles(self) -> PortfolioApplicationConfig:
        roles = tuple(policy.worker_role for policy in self.role_policies)
        if set(roles) != set(DeliveryWorkerRole) or len(roles) != len(set(roles)):
            message = "role policy must define each worker role once"
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
    integration_verifier: IntegrationVerifier
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


@dataclass(frozen=True)
class _PreparedIntegration:
    context: IntegrationContext
    capture: CompletionCapture
    snapshot: CompletionPackageSnapshot
    candidate: DeliveryIntegrationCandidate
    preparation: AtomicIntegrationPreparation


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
        self._integration_verifier = dependencies.integration_verifier
        self._completed_history_catalog = dependencies.completed_history_catalog
        self._change_branch_publisher = dependencies.change_branch_publisher
        self._draft_pull_request_publisher = dependencies.draft_pull_request_publisher
        self._execution_capacity = config.execution_capacity
        self._claim_ttl = timedelta(seconds=config.claim_ttl_seconds)
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

    def publish_change_branch(self, request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
        """Publish or reconcile one exact reviewed Change branch checkpoint."""
        if self._change_branch_publisher is None:
            message = "Change branch publication is not configured"
            raise PortfolioApplicationError(message)
        return self._change_branch_publisher.publish(request)

    def create_or_reconcile_draft_pull_request(
        self,
        request: CreateOrReconcileDraftPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        """Create or recover the unique draft PR for one first checkpoint."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        return self._draft_pull_request_publisher.publish(request)

    def update_generated_pull_request_summary(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt:
        """Replace or reconcile OwlBear's generated block for one published Change."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        return self._draft_pull_request_publisher.update_generated_summary(request)

    def observe_change_publication_checks(
        self,
        request: ObserveChangePublicationChecks,
    ) -> PublicationCheckSnapshot:
        """Observe provider checks for one Change-bound published head."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        return self._draft_pull_request_publisher.observe_checks(request)

    def show_change_checkpoint_publication(self, change_id: str) -> DeliveryCheckpointPublicationState:
        """Return the durable checkpoint queue for one admitted Change."""
        return self._runtime(change_id).checkpoint_publication_state()

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
            result = self._authority_registry.admit(request)
            self._workspace_manager.create(request.change_id)
            self._runtimes[request.change_id] = DeliveryRuntime(
                self._target_root,
                result.contract,
                workspace_manager=self._workspace_manager,
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
        return self._runtime(change_id).transition(request)

    def list_integration_ready_changes(self) -> tuple[str, ...]:
        """List unclaimed Integration changes that are ready or safe to retry."""
        return self._integration_ready_change_ids(self._portfolio_snapshots())

    def _integration_ready_change_ids(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[str, ...]:
        ready = []
        for snapshot in snapshots:
            attention = snapshot.frontier.integration_attention
            if (
                self._snapshot_change_stage(snapshot) == DeliveryChangeStage.INTEGRATION
                and not self._snapshot_has_active_claims(snapshot)
                and (
                    attention is None
                    or snapshot.integration_attention_superseded
                    or integration_attention_disposition(attention.code)
                    == DeliveryIntegrationAttentionDisposition.RETRYABLE
                )
            ):
                ready.append(snapshot.contract.change_id)
        return tuple(ready)

    def list_integration_attention(self) -> tuple[DeliveryIntegrationAttentionStatus, ...]:
        """List non-retryable Integration attention in stable identity order."""
        statuses = []
        for snapshot in self._portfolio_snapshots():
            attention = snapshot.frontier.integration_attention
            if (
                attention is None
                or snapshot.frontier.integration_repair_claim is not None
                or snapshot.integration_attention_superseded
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
            if snapshot.frontier.integration_repair_claim is not None:
                claimed.append(
                    PortfolioWorkReference(
                        change_id=snapshot.contract.change_id,
                        item_key="integration",
                        scope=PortfolioWorkScope.INTEGRATION,
                    )
                )
        return tuple(claimed)

    def _queued_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        queued = list(self._queued_outcome_work(snapshots))
        integration_ids = tuple(
            dict.fromkeys(
                (
                    *self._integration_ready_change_ids(snapshots),
                    *self._repair_candidate_ids(snapshots),
                )
            )
        )
        queued.extend(
            PortfolioWorkReference(
                change_id=change_id,
                item_key="integration",
                scope=PortfolioWorkScope.INTEGRATION,
            )
            for change_id in integration_ids
        )
        return tuple(queued)

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
            return self._runtime(change_id).administrative_move(request)

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
        change_id = runtime.contract.change_id
        coordination = self._workspace_manager.show(change_id)
        frontier_bytes = runtime.frontier_bytes()
        snapshot = DeliveryPortfolioSnapshot.capture(
            runtime.contract,
            frontier_bytes,
            integration_target=coordination.integration_target,
            target_head=coordination.target_head,
        )
        if self._snapshot_change_stage(snapshot) != DeliveryChangeStage.INTEGRATION:
            return snapshot
        try:
            context = self._workspace_manager.integration_context(change_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail(f"current Integration target is unavailable for {change_id}", exc)
        return DeliveryPortfolioSnapshot.capture(
            runtime.contract,
            frontier_bytes,
            integration_target=context.integration_target,
            target_head=context.target_head,
        )

    @staticmethod
    def _snapshot_change_stage(snapshot: DeliveryPortfolioSnapshot) -> DeliveryChangeStage:
        if snapshot.frontier.integration_result_id is not None:
            return DeliveryChangeStage.COMPLETED
        stages = {binding.stage for binding in snapshot.frontier.bindings}
        if DeliveryStage.DESIGN in stages:
            return DeliveryChangeStage.DESIGN
        if stages == {DeliveryStage.COMPLETED}:
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
        """Recover interrupted claims, then start at most one ready claim."""
        with self._coordinator.acquisition_lock():
            for change_id in self._runtimes:
                self._workspace_manager.refresh_integration_target(change_id)
            recoveries = self._recover_active_claims()
            repair_recoveries = self._recover_active_repair_claims()
            integration_ready = self.list_integration_ready_changes()
            occupied = sum(
                len(runtime.active_claims()) + int(runtime.integration_repair_claim() is not None)
                for runtime in self._runtimes.values()
            )
            available = max(self._execution_capacity - occupied, 0)
            launches: list[DeliveryLaunchPackage] = []
            repair_launches: list[DeliveryIntegrationRepairLaunchPackage] = []
            failures: list[DeliveryAcquisitionFailure] = []
            repair_failures: list[DeliveryIntegrationRepairAcquisitionFailure] = []
            for change_id in self._repair_candidates():
                if available == 0 or not self._coordinator.writer_capacity_available():
                    break
                launch = self._activate_repair_candidate(change_id)
                available -= 1
                if isinstance(launch, DeliveryIntegrationRepairAcquisitionFailure):
                    repair_failures.append(launch)
                    continue
                repair_launches.append(launch)
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
                repair_launch_packages=tuple(repair_launches),
                integration_ready_change_ids=integration_ready,
                integration_attention=self.list_integration_attention(),
                failures=tuple(failures),
                repair_failures=tuple(repair_failures),
                recoveries=recoveries,
                repair_recoveries=repair_recoveries,
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

    def show_integration_repair_context(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairContext:
        """Project exact current attention and writer custody for one repair claim."""
        runtime = self._runtime(change_id)
        claim = runtime.require_integration_repair_claim(attempt_id, claim_id)
        return DeliveryIntegrationRepairContext(launch=self._current_repair_launch(change_id, runtime, claim))

    def create_integration_repair_candidate(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> IntegrationRepairCandidate:
        """Create and prove one exact candidate under active repair custody."""
        with self._coordinator.integration_lock():
            runtime = self._runtime(change_id)
            claim = runtime.require_integration_repair_claim(attempt_id, claim_id)
            attention = runtime.integration_attention()
            coordination = self._coordinator.show(change_id)
            writer = coordination.writer
            if attention is None:
                self._fail("repair claim has no current Integration attention")
            if writer is None or (
                writer.kind != "repair"
                or writer.attempt_id != claim.attempt_id
                or writer.claim_id != claim.claim_id
                or writer.actor_id != claim.owner_id
                or writer.process_id != claim.process_id
            ):
                self._fail("repair candidate requires exact active writer custody")
            return self._workspace_manager.create_integration_repair_candidate(
                attention,
                writer,
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

    def recover_expired_claims(self) -> DeliveryExpiredClaimRecoveries:
        """Recover claims whose fixed execution lease has elapsed."""
        with self._coordinator.acquisition_lock():
            cutoff = _timestamp(self._clock()) - self._claim_ttl
            recoveries = tuple(
                self._recover_claim(change_id, outcome_id, claim.attempt_id, claim.claim_id)
                for change_id, runtime in sorted(self._runtimes.items())
                for outcome_id, claim in runtime.active_claims()
                if _timestamp(claim.started_at) <= cutoff
            )
            repair_recoveries = tuple(
                self._recover_integration_repair_claim(change_id, claim.attempt_id, claim.claim_id)
                for change_id, runtime in sorted(self._runtimes.items())
                for claim in (runtime.integration_repair_claim(),)
                if claim is not None and _timestamp(claim.started_at) <= cutoff
            )
            return DeliveryExpiredClaimRecoveries(
                recoveries=recoveries,
                repair_recoveries=repair_recoveries,
            )

    def recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        """Restart and remove one exact failed Integration repair claim."""
        with self._coordinator.acquisition_lock():
            return self._recover_integration_repair_claim(change_id, attempt_id, claim_id)

    def _recover_active_claims(self) -> tuple[DeliveryClaimRecoveryResult, ...]:
        return tuple(
            self._recover_claim(change_id, outcome_id, claim.attempt_id, claim.claim_id)
            for change_id, runtime in sorted(self._runtimes.items())
            for outcome_id, claim in runtime.active_claims()
        )

    def _recover_active_repair_claims(self) -> tuple[DeliveryIntegrationRepairRecoveryResult, ...]:
        return tuple(
            self._recover_integration_repair_claim(change_id, claim.attempt_id, claim.claim_id)
            for change_id, runtime in sorted(self._runtimes.items())
            for claim in (runtime.integration_repair_claim(),)
            if claim is not None
        )

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

    def integrate_ready_change(self, change_id: str) -> DeliveryIntegrationResult:
        """Validate one reviewed candidate and retain external-acceptance attention."""
        with self._coordinator.integration_lock():
            runtime = self._runtime(change_id)
            self._workspace_manager.refresh_integration_target(change_id)
            context = self._workspace_manager.integration_context(change_id)
            existing = runtime.integration_completion()
            if existing is not None:
                self._workspace_manager.discard_stale_integration_candidate(change_id)
                self._cleanup_integration(change_id, existing)
                return DeliveryIntegrationResult(
                    change_id=change_id,
                    completion=existing,
                    replayed=True,
                )
            if runtime.change_stage() != DeliveryChangeStage.INTEGRATION:
                self._fail("change is not ready for Integration")
            prepared = self._capture_ready_integration(change_id, runtime, context)
            if isinstance(prepared, DeliveryIntegrationResult):
                return prepared
            if prepared.preparation.result is not None:
                self._workspace_manager.discard_stale_integration_candidate(change_id)
                return self._revalidate_for_external_acceptance(runtime, context, prepared)

        receipt = self._integration_verifier.verify(prepared.candidate, prepared.preparation)

        with self._coordinator.integration_lock():
            runtime = self._runtime(change_id)
            existing = runtime.integration_completion()
            if existing is not None:
                self._workspace_manager.discard_stale_integration_candidate(change_id)
                self._cleanup_integration(change_id, existing)
                return DeliveryIntegrationResult(change_id=change_id, completion=existing, replayed=True)
            # Evidence stays bound to the heads that produced the receipt; publication revalidates current heads.
            if not receipt.passed:
                result = self._integration_attention(
                    runtime,
                    prepared.context,
                    DeliveryIntegrationAttentionCode.CANDIDATE_PROOF_FAILED,
                    self._verification_diagnostics(receipt),
                    candidate=prepared.candidate,
                )
            else:
                result = self._publish_verified_integration(runtime, prepared.context, prepared)
            self._workspace_manager.discard_integration_candidate(prepared.preparation)
            if result.completion is not None:
                self._cleanup_integration(change_id, result.completion)
            return result

    def prepare_external_completion(self, change_id: str) -> ExternalCompletionResult:
        """Prepare a detached proposal without inferring acceptance from local Git state."""
        with self._coordinator.integration_lock():
            runtime = self._runtime(change_id)
            self._workspace_manager.refresh_integration_target(change_id)
            context = self._workspace_manager.integration_context(change_id)
            existing = runtime.integration_completion()
            if existing is not None:
                self._cleanup_integration(change_id, existing)
                return ExternalCompletionResult(change_id=change_id, completion=existing, replayed=True)
            if runtime.change_stage() != DeliveryChangeStage.INTEGRATION:
                self._fail("change is not ready for Integration")
            captured = self._capture_ready_integration(change_id, runtime, context)
            if isinstance(captured, DeliveryIntegrationResult):
                return ExternalCompletionResult(change_id=change_id, attention=captured.attention)
            prepared = self._workspace_manager.prepare_external_completion_proposal(captured.candidate)
            self._workspace_manager.discard_integration_candidate(captured.preparation)
            if isinstance(prepared, AtomicIntegrationResult):
                if prepared.target_commit is None:
                    failed = self._integration_attention(
                        runtime,
                        context,
                        prepared.code,
                        prepared.diagnostics,
                        candidate=captured.candidate,
                    )
                    return ExternalCompletionResult(change_id=change_id, attention=failed.attention)
                waiting = self._integration_attention(
                    runtime,
                    context,
                    DeliveryIntegrationAttentionCode.EXTERNAL_ACCEPTANCE_REQUIRED,
                    (_PROVIDER_ACCEPTANCE_REQUIRED,),
                    candidate=captured.candidate,
                )
                return ExternalCompletionResult(change_id=change_id, attention=waiting.attention)
            return ExternalCompletionResult(change_id=change_id, proposal=prepared)

    def admit_reviewed_integration_repair(
        self,
        attempt_id: str,
        claim_id: str,
        repair: DeliveryIntegrationRepair,
    ) -> DeliveryIntegrationRepair:
        """Admit one independently reviewed additive repair for current Integration attention."""
        with self._coordinator.integration_lock():
            runtime = self._runtime(repair.change_id)
            claim = runtime.require_integration_repair_claim(attempt_id, claim_id)
            if repair.owner_id != claim.owner_id:
                self._fail("Integration repair owner does not match the active claim")
            runtime_replacement = runtime.integration_repair_replacement(repair)
            workspace_replacements = self._workspace_manager.integration_repair_replacement(repair, claim_id)
            self._coordinator.admit_integration_repair(
                repair,
                (*workspace_replacements, runtime_replacement),
            )
            return repair

    def publish_integration_repair_authority_attention(
        self,
        attempt_id: str,
        claim_id: str,
        request: DeliveryIntegrationRepairAuthorityAttention,
    ) -> DeliveryIntegrationAttention:
        """End one repair claim that cannot preserve its admitted authority."""
        with self._coordinator.integration_lock():
            runtime = self._runtime(request.change_id)
            runtime.require_integration_repair_claim(attempt_id, claim_id)
            attention, runtime_replacement = runtime.integration_repair_authority_replacement(
                request,
                attempt_id,
                claim_id,
            )
            workspace_replacements = self._workspace_manager.integration_repair_authority_replacements(
                request,
                claim_id,
            )
            self._coordinator.admit_integration_repair(
                request,
                (*workspace_replacements, runtime_replacement),
            )
            return attention

    def _capture_ready_integration(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        context: IntegrationContext,
    ) -> DeliveryIntegrationResult | _PreparedIntegration:
        try:
            package = self._package_store.read_verified(change_id)
            attention_code = self._package_attention_code(runtime, package)
            if attention_code is not None:
                return self._integration_attention(
                    runtime,
                    context,
                    attention_code,
                    ("active package does not match admitted completed Delivery authority",),
                )
            runtime_bytes, result_history_bytes = runtime.completion_capture_bytes()
            capture = CompletionCapture(
                change_id=change_id,
                expected_package_id=package.package_id,
                authority_digest=runtime.authority_digest,
                runtime_bytes=runtime_bytes,
                result_history_bytes=result_history_bytes,
                reviewed_change_head=context.reviewed_change_head,
                integration_target=context.integration_target,
                completion_path=f"{_COMPLETED_ROOT}/{change_id}",
            )
            return self._package_store.capture_completion(
                capture,
                validation_callback=lambda snapshot: self._prepare_integration_snapshot(
                    runtime,
                    context,
                    capture,
                    snapshot,
                ),
                publication_callback=lambda prepared: prepared,
            )
        except DesignPackageConflictError as exc:
            return self._integration_attention(
                runtime,
                context,
                DeliveryIntegrationAttentionCode.PACKAGE_MUTATED,
                (str(exc),),
            )

    def _prepare_integration_snapshot(
        self,
        runtime: DeliveryRuntime,
        context: IntegrationContext,
        capture: CompletionCapture,
        snapshot: CompletionPackageSnapshot,
    ) -> _PreparedIntegration:
        candidate = self._integration_candidate(runtime, context, snapshot)
        preparation = self._workspace_manager.prepare_integration_candidate(candidate)
        return _PreparedIntegration(context, capture, snapshot, candidate, preparation)

    def _publish_verified_integration(
        self,
        runtime: DeliveryRuntime,
        context: IntegrationContext,
        prepared: _PreparedIntegration,
    ) -> DeliveryIntegrationResult:
        runtime_bytes, result_history_bytes = runtime.completion_capture_bytes()
        if (
            runtime_bytes != prepared.capture.runtime_bytes
            or result_history_bytes != prepared.capture.result_history_bytes
        ):
            return self._integration_attention(
                runtime,
                context,
                DeliveryIntegrationAttentionCode.PACKAGE_MUTATED,
                ("Delivery runtime changed during candidate verification",),
                candidate=prepared.candidate,
            )
        try:
            return self._package_store.capture_completion(
                prepared.capture,
                validation_callback=lambda snapshot: self._require_verified_snapshot(prepared, snapshot),
                publication_callback=lambda verified: self._revalidate_for_external_acceptance(
                    runtime,
                    context,
                    verified,
                ),
            )
        except DesignPackageConflictError as exc:
            return self._integration_attention(
                runtime,
                context,
                DeliveryIntegrationAttentionCode.PACKAGE_MUTATED,
                (str(exc),),
                candidate=prepared.candidate,
            )

    def _revalidate_for_external_acceptance(
        self,
        runtime: DeliveryRuntime,
        context: IntegrationContext,
        prepared: _PreparedIntegration,
    ) -> DeliveryIntegrationResult:
        invalid = self._workspace_manager.validate_prepared_integration(prepared.preparation)
        if invalid is not None:
            if invalid.code is None:
                return self._integration_attention(
                    runtime,
                    context,
                    DeliveryIntegrationAttentionCode.EXTERNAL_ACCEPTANCE_REQUIRED,
                    (_PROVIDER_ACCEPTANCE_REQUIRED,),
                    candidate=prepared.candidate,
                )
            return self._integration_attention(
                runtime,
                context,
                invalid.code,
                invalid.diagnostics,
                candidate=prepared.candidate,
            )
        return self._integration_attention(
            runtime,
            context,
            DeliveryIntegrationAttentionCode.EXTERNAL_ACCEPTANCE_REQUIRED,
            ("local target publication is disabled; completion requires externally observed acceptance",),
            candidate=prepared.candidate,
        )

    @staticmethod
    def _require_verified_snapshot(
        prepared: _PreparedIntegration,
        snapshot: CompletionPackageSnapshot,
    ) -> _PreparedIntegration:
        if snapshot != prepared.snapshot:
            message = "completion package identity changed during candidate verification"
            raise DesignPackageConflictError(message)
        return prepared

    @staticmethod
    def _verification_diagnostics(receipt: IntegrationVerificationReceipt) -> tuple[str, ...]:
        diagnostics = [f"verification {receipt.status.value}", *receipt.diagnostics]
        for step in receipt.steps:
            diagnostics.append(f"step {step.step_id}: {step.status.value}")
            if step.stderr:
                diagnostics.append(step.stderr[:1_024])
            elif step.stdout and step.status.value != "passed":
                diagnostics.append(step.stdout[:1_024])
        return tuple(diagnostics[:16])

    def _integration_candidate(
        self,
        runtime: DeliveryRuntime,
        context: IntegrationContext,
        snapshot: CompletionPackageSnapshot,
    ) -> DeliveryIntegrationCandidate:
        payload = {
            "completion_id": snapshot.completion_id,
            "package_id": snapshot.package_id,
            "package_tree": snapshot.package_tree,
            "reviewed_change_head": context.reviewed_change_head,
            "integration_target": context.integration_target,
        }
        candidate_id = hashlib.sha256(_canonical(payload)).hexdigest()
        return DeliveryIntegrationCandidate(
            candidate_id=candidate_id,
            completion_id=snapshot.completion_id,
            change_id=runtime.contract.change_id,
            package_id=snapshot.package_id,
            authority_digest=runtime.authority_digest,
            runtime_digest=snapshot.manifest.runtime_sha256,
            result_history_digest=snapshot.manifest.result_history_sha256,
            reviewed_change_head=context.reviewed_change_head,
            integration_target=context.integration_target,
            target_head=context.target_head,
            completion_path=snapshot.manifest.completion_path,
            package_tree=snapshot.package_tree,
        )

    def _integration_attention(
        self,
        runtime: DeliveryRuntime,
        context: IntegrationContext,
        code: DeliveryIntegrationAttentionCode,
        diagnostics: tuple[str, ...],
        *,
        candidate: DeliveryIntegrationCandidate | None = None,
    ) -> DeliveryIntegrationResult:
        payload = {
            "code": code.value,
            "change_id": runtime.contract.change_id,
            "change_head": context.change_head,
            "target_head": context.target_head,
            "integration_target": context.integration_target,
            "diagnostics": diagnostics,
        }
        attention = DeliveryIntegrationAttention(
            attention_id=hashlib.sha256(_canonical(payload)).hexdigest(),
            code=code,
            change_id=runtime.contract.change_id,
            change_head=context.change_head,
            target_head=context.target_head,
            integration_target=context.integration_target,
            diagnostics=diagnostics,
            retry_condition=_integration_retry_condition(code),
        )
        runtime.publish_integration_attention(attention)
        return DeliveryIntegrationResult(
            change_id=runtime.contract.change_id,
            candidate=candidate,
            attention=attention,
        )

    def _cleanup_integration(
        self,
        change_id: str,
        completion: DeliveryIntegrationCompletion,
    ) -> None:
        self._package_store.cleanup_completed(change_id, completion.package_id)
        self._workspace_manager.cleanup_integrated_worktree(
            change_id,
            completion.completion_path,
            completion.completion_id,
        )

    @staticmethod
    def _package_attention_code(
        runtime: DeliveryRuntime,
        package: VerifiedDesignPackage,
    ) -> DeliveryIntegrationAttentionCode | None:
        if hashlib.sha256(package.authority_bytes).hexdigest() != runtime.authority_digest:
            return DeliveryIntegrationAttentionCode.REVISION_PENDING
        source_digests = {binding.source_name: binding.sha256 for binding in runtime.contract.source_bindings}
        if source_digests != {
            "intent.md": package.manifest.intent_sha256,
            "design.md": package.manifest.design_sha256,
        }:
            return DeliveryIntegrationAttentionCode.PACKAGE_MUTATED
        return None

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

    def _repair_candidates(self) -> tuple[str, ...]:
        return self._repair_candidate_ids(self._portfolio_snapshots())

    def _repair_candidate_ids(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[str, ...]:
        candidates = []
        for snapshot in snapshots:
            attention = snapshot.frontier.integration_attention
            if (
                self._snapshot_change_stage(snapshot) != DeliveryChangeStage.INTEGRATION
                or self._snapshot_has_active_claims(snapshot)
                or snapshot.frontier.integration_repair_claim is not None
                or attention is None
                or integration_attention_disposition(attention.code)
                != DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED
                or snapshot.integration_attention_superseded
            ):
                continue
            candidates.append(snapshot.contract.change_id)
        return tuple(candidates)

    def _prepare_repair_source(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> _PreparedSource | DeliveryIntegrationRepairAcquisitionFailure:
        try:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            coordination = self._workspace_manager.show(change_id)
            source_head = self._workspace_manager.reviewed_source_head(change_id)
        except (OSError, RuntimeError, ValueError) as exc:
            return DeliveryIntegrationRepairAcquisitionFailure(
                change_id=change_id,
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Restore the admitted package and clean reviewed repair boundary.",
            )
        return _PreparedSource(package, coordination, source_head)

    def _activate_repair_candidate(
        self,
        change_id: str,
    ) -> DeliveryIntegrationRepairLaunchPackage | DeliveryIntegrationRepairAcquisitionFailure:
        runtime = self._runtime(change_id)
        source = self._prepare_repair_source(change_id, runtime)
        if isinstance(source, DeliveryIntegrationRepairAcquisitionFailure):
            return source
        claim = self._new_claim(DeliveryWorkerRole.INTEGRATION_REPAIRER, None)
        runtime.activate_integration_repair_claim(claim)
        try:
            coordination = self._coordinator.acquire(
                change_id,
                ChangeWriter(
                    attempt_id=claim.attempt_id,
                    claim_id=claim.claim_id,
                    actor_id=claim.owner_id,
                    process_id=claim.process_id,
                    claimed_at=claim.started_at,
                    job_id=1,
                    kind="repair",
                ),
            )
        except CoordinationConflictError as exc:
            return DeliveryIntegrationRepairAcquisitionFailure(
                change_id=change_id,
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                code=exc.code,
                detail=str(exc),
                retry_condition="Recover the exact failed repair claim after reconciling writer custody.",
            )
        if coordination.writer is None:
            self._fail("repair writer acquisition did not publish custody")
        return self._repair_launch_package(change_id, runtime, claim, source, coordination.writer)

    def _current_repair_launch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        claim: DeliveryActiveClaim,
    ) -> DeliveryIntegrationRepairLaunchPackage:
        source = self._prepare_repair_source(change_id, runtime)
        if isinstance(source, DeliveryIntegrationRepairAcquisitionFailure):
            self._fail(source.detail)
        writer = source.coordination.writer
        if writer is None:
            self._fail("repair claim has no writer custody")
        return self._repair_launch_package(change_id, runtime, claim, source, writer)

    def _repair_launch_package(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        claim: DeliveryActiveClaim,
        source: _PreparedSource,
        writer: ChangeWriter,
    ) -> DeliveryIntegrationRepairLaunchPackage:
        attention = runtime.integration_attention()
        if attention is None:
            self._fail("repair claim has no current Integration attention")
        return DeliveryIntegrationRepairLaunchPackage(
            change_id=change_id,
            claim=claim,
            policy=self._policies[DeliveryWorkerRole.INTEGRATION_REPAIRER],
            attention=attention,
            package_id=source.package.package_id,
            package_root=self._package_root / change_id,
            worktree_path=source.coordination.worktree_path,
            branch=source.coordination.branch,
            source_head=source.source_head,
            integration_target=source.coordination.integration_target,
            last_reviewed_commit=source.coordination.last_reviewed_commit,
            writer=writer,
        )

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


def _canonical(payload: object) -> bytes:
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()


def _integration_retry_condition(code: DeliveryIntegrationAttentionCode) -> str:
    if code == DeliveryIntegrationAttentionCode.EXTERNAL_ACCEPTANCE_REQUIRED:
        return "Publish the reviewed Change through the provider and observe external acceptance."
    if code == DeliveryIntegrationAttentionCode.CANDIDATE_PROOF_FAILED:
        return (
            "Correct the Integration profile or failing candidate verification step, "
            "then re-run Integration through Delivery orchestration."
        )
    disposition = integration_attention_disposition(code)
    if disposition == DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED:
        return "Admit a reviewed Integration repair for this attention, then retry Integration."
    if disposition == DeliveryIntegrationAttentionDisposition.RETRYABLE:
        return "Retry Integration against the current target head."
    return "Resolve the reported Integration condition, then retry this exact change."


__all__ = [
    "DeliveryAcquisitionFailure",
    "DeliveryAcquisitionResult",
    "DeliveryBuildContext",
    "DeliveryClaimRecoveryResult",
    "DeliveryClaimRecoveryStatus",
    "DeliveryIntegrationAttentionStatus",
    "DeliveryIntegrationResult",
    "DeliveryLaunchPackage",
    "DeliveryPlanContext",
    "DeliveryRolePolicy",
    "ExternalCompletionResult",
    "PortfolioApplication",
    "PortfolioApplicationConfig",
    "PortfolioApplicationDependencies",
    "PortfolioApplicationError",
    "PortfolioApplicationHooks",
]
