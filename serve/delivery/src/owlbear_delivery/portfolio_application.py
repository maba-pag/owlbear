"""Deterministic portfolio acquisition and bounded worker context."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import uuid
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import TYPE_CHECKING, Literal, Never

from owlbear_delivery.acceptance import (
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
)
from owlbear_delivery.application_acquisition import (
    _AcquisitionMixin,
)
from owlbear_delivery.application_lifecycle import (
    _ACCEPTANCE_DRAIN_MUTATIONS,
    _LifecycleMixin,
)
from owlbear_delivery.application_merge import _MergeMixin

# Consumer import surface kept at this module path.
from owlbear_delivery.application_models import (  # noqa: F401
    DeliveryAcceptanceReconciliationOutcome,
    DeliveryAcceptanceReconciliationStatus,
    DeliveryAcquisitionFailure,
    DeliveryAcquisitionResult,
    DeliveryActionBusyError,
    DeliveryActionSelection,
    DeliveryAnswer,
    DeliveryAnswerKind,
    DeliveryAnswerResult,
    DeliveryBuildContext,
    DeliveryCapacityWaitingError,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryChangeIntentResult,
    DeliveryChangePublicationSupersessionReceipt,
    DeliveryChangeView,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryCheckpointReconciliationResult,
    DeliveryClaimRecoveryResult,
    DeliveryClaimRecoveryStatus,
    DeliveryContinuationReason,
    DeliveryContinuationRequest,
    DeliveryContinuationResult,
    DeliveryDesignPut,
    DeliveryEngineActionResult,
    DeliveryFinalizationContext,
    DeliveryFinalizationLaunch,
    DeliveryIntegrationAttentionStatus,
    DeliveryIntegrationRepairRecoveryResult,
    DeliveryLaunchPackage,
    DeliveryOperatorClaim,
    DeliveryOperatorContext,
    DeliveryOperatorIntegrationAttention,
    DeliveryOperatorRecoveryAttention,
    DeliveryPlanContext,
    DeliveryQuarantinedSnapshotRepairProposal,
    DeliveryQuarantinedSnapshotRepairReceipt,
    DeliveryRepairResult,
    DeliveryResultSubmission,
    DeliveryResultSubmissionResult,
    DeliveryRetainedChangeWorktree,
    DeliveryRetainedWorktreeCleanupBlockReason,
    DeliveryRolePolicy,
    DeliveryRuntimeReconciliationError,
    DeliveryStateSnapshotRepairReceipt,
    DeliveryStrandedFrontierRepairReceipt,
    DeliveryTargetSyncRepairReceipt,
    DeliveryUnavailableChangeView,
    DeliveryUnresolvedOutcome,
    ExecuteDeliveryChangeAction,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationError,
    PortfolioApplicationHooks,
    PortfolioReadView,
    RequiredPublicationChecksFailedError,
    _AcceptanceReconciliationAuthority,
    _AcceptanceReconciliationCursor,
    _Candidate,
    _PreparedSource,
)
from owlbear_delivery.application_publication import (
    _PublicationMixin,
)
from owlbear_delivery.application_readiness import (
    _ReadinessViewsMixin,
)
from owlbear_delivery.application_recovery import (
    _RecoveryMixin,
)
from owlbear_delivery.application_support import (  # noqa: F401
    _ACCEPTANCE_RECONCILIATION_CURSOR_FILE,
    _MAX_ACCEPTANCE_RECONCILIATION_CHANGES,
    _PUBLICATION_OBSERVATION_CACHE_SECONDS,
    _canonical_model_bytes,
    _checkpoint_operation_id,
    _health_detail,
    _logger,
    _required_check_diagnostics,
    _timestamp,
)
from owlbear_delivery.change_workspace import (
    ChangeExternalHeadPromotionReceipt,
    ChangePauseRequest,
    ChangePauseRequestedError,
    ChangeWriter,
    CoordinationConflictError,
    DesignReturnWorkspaceError,
    WorkspaceRecoverySnapshot,
)
from owlbear_delivery.delivery_admission import (
    DeliveryAdmissionConflictError,
    DeliveryAdmissionReceipt,
    DeliveryRevisionError,
    DeliveryRevisionReason,
)
from owlbear_delivery.delivery_contract_discovery import (
    DeliveryChangeObservation,
    DeliveryDiscoveryRootError,
    contract_fingerprint,
    discover_persisted_changes,
)
from owlbear_delivery.delivery_runtime import (
    AdvanceDelivery,
    DeliveryAcceptanceAttentionReason,
    DeliveryAcceptanceWaitingError,
    DeliveryActiveClaim,
    DeliveryChangeDeferral,
    DeliveryChangeStage,
    DeliveryConfirmationError,
    DeliveryMergedPullRequestLatch,
    DeliveryPlanCandidate,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryResultCandidate,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryTaskDefinition,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    is_acceptance_waiting_observation,
    parse_delivery_frontier,
)
from owlbear_delivery.design_package import DesignPackageResult
from owlbear_delivery.draft_pull_request import (
    ObserveChangePublicationPullRequest,
    PublicationPullRequestObservationReceipt,
    PullRequestReadyReceipt,
    ReadChangePublicationCheckObservations,
)
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
    PublicationPullRequest,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RetryEpisodeKey,
    RetryFailureClass,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    RetryReservation,
    RetryStopCode,
    is_canonical_admitted_path,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots, state_is_read_only
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCompilationResult,
    DeliveryOutcome,
    compile_delivery_contract,
)
from owlbear_delivery.work_items import (  # noqa: F401
    DeliveryPortfolioSnapshot,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    WorkItemScope,
)
from owlbear_delivery.worker_stall import (
    ProcessTableWorktreeProbe,
    ProcessWindowLivenessProbe,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

    from owlbear_delivery.completed_history import (
        CompletedChangePage,
        CompletedChangeRecord,
        CompletedHistoryCatalog,
    )
    from owlbear_delivery.delivery_admission import (
        DeliveryAdmissionRequest,
        DeliveryAdmissionResult,
    )
    from owlbear_delivery.delivery_state import DeliveryStatePublicationReceipt
    from owlbear_delivery.design_package import (
        DesignCheckpointResult,
        VerifiedDesignPackage,
    )
    from owlbear_delivery.merge_offer import MergeFacts
    from owlbear_delivery.workspace_coordination import DrainAuthority


class PortfolioApplication(
    _ReadinessViewsMixin, _AcquisitionMixin, _PublicationMixin, _LifecycleMixin, _RecoveryMixin, _MergeMixin
):
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
        self._runtime_reconciliation_lock = Lock()
        self._runtimes = dict(runtimes)
        self._discovered_changes: dict[str, DeliveryChangeObservation] = {}
        self._runtime_reconciliation_errors: dict[str, str] = {}
        self._runtime_snapshots: dict[str, DeliveryPortfolioSnapshot] = {}
        self._publication_observation_cache: dict[
            str,
            tuple[float, str, PublicationPullRequestObservationReceipt | Literal["provider-unavailable"] | None],
        ] = {}
        self._merge_facts_cache: dict[str, tuple[float, str, MergeFacts]] = {}
        self._completed_cleanup_swept: set[str] = set()
        self._acceptance_reconciliation_cursor: str | None = None
        self._has_reconciled_runtimes = False
        self._target_root = dependencies.target_root.resolve()
        self._package_store = dependencies.package_store
        self._authority_registry = dependencies.authority_registry
        self._package_root = config.package_root.resolve()
        self._coordinator = dependencies.coordinator
        self._workspace_manager = dependencies.workspace_manager
        self._completed_history_catalog = dependencies.completed_history_catalog
        self._delivery_state_publisher = dependencies.delivery_state_publisher
        self._change_branch_publisher = dependencies.change_branch_publisher
        self._draft_pull_request_publisher = dependencies.draft_pull_request_publisher
        self._startup_health_diagnostics = dependencies.health_diagnostics
        self._recovery_evidence_provider = dependencies.recovery_evidence_provider
        self._proof_attempt_store_factory = dependencies.proof_attempt_store_factory
        self._issuer_window = dependencies.issuer_window
        self._window_liveness_probe = dependencies.window_liveness_probe or ProcessWindowLivenessProbe()
        self._worktree_process_probe = dependencies.worktree_process_probe or ProcessTableWorktreeProbe()
        self._worker_quiet_period = dependencies.worker_quiet_period
        self._execution_capacity = config.execution_capacity
        self._claim_timeout = timedelta(seconds=config.claim_timeout_seconds)
        self._policies = {policy.worker_role: policy for policy in config.role_policies}
        self._identity_factory = hooks.identity_factory if hooks else lambda: str(uuid.uuid4())
        self._clock = (
            hooks.clock
            if hooks
            else lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
        for runtime in () if state_is_read_only() else self._runtimes.values():
            try:
                with locked_roots((self._checkpoint_lock_root(runtime.contract.change_id),), blocking=False):
                    self._reconcile_retry_results(runtime)
            except OSError, RuntimeError, ValueError:
                _logger.warning("Retry accounting remains contained for %s", runtime.contract.change_id)

    def create_design_session(
        self,
        change_id: str,
        intent_bytes: bytes,
        design_bytes: bytes,
    ) -> DesignPackageResult:
        """Create or replay one exact authored Design package."""
        return self._package_store.create(change_id, intent_bytes, design_bytes)

    def put_design(self, design: DeliveryDesignPut) -> DesignPackageResult:
        """Create or CAS-revise one exact authored Design package."""
        if design.expected_package_id is None:
            return self._package_store.create(design.change_id, design.intent_bytes, design.design_bytes)
        revised = self.revise_design_session(
            design.change_id,
            design.expected_package_id,
            design.intent_bytes,
            design.design_bytes,
        )
        return DesignPackageResult(
            change_id=revised.change_id,
            package_id=revised.package_id,
            package_root=self._package_root / design.change_id,
            manifest=revised.manifest,
            replayed=False,
        )

    def reconcile_awaiting_acceptance(
        self,
        change_ids: tuple[str, ...] | None = None,
        *,
        limit: int = _MAX_ACCEPTANCE_RECONCILIATION_CHANGES,
    ) -> tuple[DeliveryAcceptanceReconciliationOutcome, ...]:
        """Reconcile a bounded set of observed awaiting-merge Changes."""
        self._reconcile_runtimes()
        if limit < 1:
            message = "acceptance reconciliation limit must be positive"
            raise ValueError(message)
        effective_limit = min(limit, _MAX_ACCEPTANCE_RECONCILIATION_CHANGES)
        requested = None if change_ids is None else frozenset(change_ids)
        all_eligible = tuple(
            change_id
            for change_id, runtime in sorted(self._runtimes.items())
            if self._is_acceptance_reconciliation_eligible(runtime)
        )
        eligible = (
            all_eligible
            if requested is None
            else tuple(change_id for change_id in all_eligible if change_id in requested)
        )
        if not eligible:
            return ()
        selected = self._select_acceptance_reconciliation_changes(
            all_eligible,
            effective_limit,
            requested=requested,
        )
        selected_ids = frozenset(selected)
        outcomes = [self._reconcile_awaiting_acceptance_change(change_id) for change_id in selected]
        outcomes.extend(
            DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_LIMIT",
                detail="Acceptance reconciliation batch limit reached.",
            )
            for change_id in eligible
            if change_id not in selected_ids
        )
        return tuple(outcomes)

    def _select_acceptance_reconciliation_changes(
        self,
        eligible: tuple[str, ...],
        limit: int,
        *,
        requested: frozenset[str] | None,
    ) -> tuple[str, ...]:
        """Reserve a fair bounded batch and persist its next starting Change."""
        if not eligible:
            return ()
        cursor_root = self._target_root / "claims" / "acceptance-reconciliation"
        cursor = self._acceptance_reconciliation_cursor
        try:
            with locked_roots((cursor_root,)):
                with suppress(OSError, ValueError):
                    cursor = _AcceptanceReconciliationCursor.model_validate_json(
                        (cursor_root / _ACCEPTANCE_RECONCILIATION_CURSOR_FILE).read_bytes()
                    ).next_change_id
                selected, next_cursor = self._rotate_acceptance_reconciliation_batch(
                    eligible,
                    limit,
                    cursor,
                    requested=requested,
                )
                atomic_write(
                    cursor_root / _ACCEPTANCE_RECONCILIATION_CURSOR_FILE,
                    json.dumps(
                        _AcceptanceReconciliationCursor(next_change_id=next_cursor).model_dump(
                            mode="json",
                        ),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n",
                )
        except OSError, ValueError:
            selected, next_cursor = self._rotate_acceptance_reconciliation_batch(
                eligible,
                limit,
                self._acceptance_reconciliation_cursor,
                requested=requested,
            )
        self._acceptance_reconciliation_cursor = next_cursor
        return selected

    @staticmethod
    def _rotate_acceptance_reconciliation_batch(
        eligible: tuple[str, ...],
        limit: int,
        cursor: str | None,
        *,
        requested: frozenset[str] | None,
    ) -> tuple[tuple[str, ...], str]:
        """Return one wrapped batch and the deterministic cursor after it."""
        start = (
            0
            if cursor is None
            else next(
                (index for index, change_id in enumerate(eligible) if change_id >= cursor),
                0,
            )
        )
        ordered = tuple(eligible[(start + offset) % len(eligible)] for offset in range(len(eligible)))
        selected = tuple(change_id for change_id in ordered if requested is None or change_id in requested)[:limit]
        eligible_ids = frozenset(eligible)
        requested_eligible_ids = frozenset(
            change_id for change_id in eligible if requested is not None and change_id in requested
        )
        if requested is not None and requested_eligible_ids != eligible_ids:
            return selected, ordered[0]
        selected_ids = frozenset(selected)
        next_cursor = next(
            (change_id for change_id in ordered if change_id not in selected_ids),
            ordered[0],
        )
        return selected, next_cursor

    @staticmethod
    def _is_acceptance_reconciliation_eligible(runtime: DeliveryRuntime) -> bool:
        """Select only live awaiting-merge Changes without competing custody."""
        return runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE and not runtime.active_claims()

    def _reconcile_awaiting_acceptance_change(  # noqa: C901, PLR0911 - one outcome per reconciliation exit.
        self,
        change_id: str,
    ) -> DeliveryAcceptanceReconciliationOutcome:
        runtime = self._runtime(change_id, for_mutation=True)
        try:
            with locked_roots((self._checkpoint_lock_root(change_id),), blocking=False):
                if not self._is_acceptance_reconciliation_eligible(runtime):
                    return self._reconciliation_skipped_outcome(change_id, "Change is no longer awaiting merge.")
                if self._coordinator.pause_request(change_id) is not None:
                    self._try_convert_pause_request(change_id, runtime)
                    return self._reconciliation_skipped_outcome(change_id, "Change pause requested.")
                reservation = self._reserve_acceptance_observation(runtime, explicit=False)
                if not reservation.allowed:
                    return DeliveryAcceptanceReconciliationOutcome(
                        change_id=change_id,
                        status=DeliveryAcceptanceReconciliationStatus.WAITING,
                        code=reservation.reason_code,
                        detail="Acceptance observation is waiting for its durable retry policy.",
                    )
                try:
                    with self._owner_drain_authority(
                        change_id, f"acceptance:{reservation.attempt_id}", *_ACCEPTANCE_DRAIN_MUTATIONS
                    ):
                        outcome = self._reconcile_awaiting_acceptance_locked(change_id, runtime, reservation.attempt_id)
                except PublicationProviderError as exc:
                    runtime.retry_ledger(clock=self._clock).record_failure(
                        reservation, failure_code=exc.code.value, now=self._clock()
                    )
                    raise
                except PortfolioApplicationError as exc:
                    outcome = DeliveryAcceptanceReconciliationOutcome(
                        change_id=change_id,
                        status=(
                            DeliveryAcceptanceReconciliationStatus.ATTENTION
                            if runtime.change_disposition() is not None
                            else DeliveryAcceptanceReconciliationStatus.SKIPPED
                        ),
                        code=exc.code,
                        detail=str(exc),
                    )
                ledger = runtime.retry_ledger(clock=self._clock)
                if outcome is not None and outcome.status is DeliveryAcceptanceReconciliationStatus.COMPLETED:
                    ledger.record_accepted_progress(reservation, now=self._clock())
                else:
                    ledger.record_failure(reservation, failure_code="acceptance-wait", now=self._clock())
                    self._try_convert_pause_request(change_id, runtime)
        except BlockingIOError:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_BUSY",
                detail="Change reconciliation is already in progress.",
            )
        except PublicationProviderError as exc:
            return self._provider_unavailable_outcome(change_id, exc)
        except (
            DeliveryRuntimeConflictError,
            ChangePauseRequestedError,
            RetryLedgerConflictError,
            RetryLedgerCorruptError,
            OSError,
            ValueError,
        ) as exc:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_STATE_CHANGED",
                detail=str(exc) or "Change state changed during reconciliation.",
            )
        result = outcome
        disposition = runtime.change_disposition()
        if disposition is not None:
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{disposition.disposition_id}",
            )
        return result

    def _reconcile_awaiting_acceptance_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        attempt_id: str,
    ) -> DeliveryAcceptanceReconciliationOutcome:
        """Read one provider snapshot while holding only the Change checkpoint lock."""
        if not self._is_acceptance_reconciliation_eligible(runtime):
            return self._reconciliation_skipped_outcome(change_id, "Change is no longer awaiting merge.")
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.PROVIDER_UNAVAILABLE,
                code="ERR_DELIVERY_PROVIDER_NOT_CONFIGURED",
                detail="Draft pull-request publication is not configured.",
            )
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        if finalization is None or ready is None:
            return self._reconciliation_skipped_outcome(change_id, "Awaiting-merge authority is incomplete.")
        self._settle_merge_for_acceptance(change_id)
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            return self._reconciliation_skipped_outcome(
                change_id,
                "No bound pull-request publication was found.",
                code="ERR_DELIVERY_PUBLICATION_MISSING",
            )
        if self._settle_for_acceptance_read(change_id, runtime, observation):
            outcome = self._classify_acceptance_observation(
                change_id,
                runtime,
                observation,
                _AcceptanceReconciliationAuthority(
                    exact_head=finalization.exact_head,
                    ready=ready,
                    target_branch=publisher.target_branch,
                ),
            )
        else:
            outcome = DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.WAITING,
                detail="The merge request is not settled yet.",
            )
        if outcome is not None:
            return outcome
        receipt = self._observe_acceptance_once(change_id, runtime, attempt_id=attempt_id, observation=observation)
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=DeliveryAcceptanceReconciliationStatus.COMPLETED,
            completion_id=receipt.completion_id,
        )

    @staticmethod
    def _reconciliation_skipped_outcome(
        change_id: str,
        detail: str,
        *,
        code: str = "ERR_DELIVERY_RECONCILIATION_STATE_CHANGED",
    ) -> DeliveryAcceptanceReconciliationOutcome:
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
            code=code,
            detail=detail,
        )

    def _classify_acceptance_observation(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        observation: PublicationPullRequestObservationReceipt,
        authority: _AcceptanceReconciliationAuthority,
    ) -> DeliveryAcceptanceReconciliationOutcome | None:
        snapshot = observation.snapshot
        if self._acceptance_reconciliation_authority_matches(
            snapshot, authority.exact_head, authority.ready, authority.target_branch
        ):
            self._remember_acceptance_observation(observation)
        if snapshot.state == "open" and not snapshot.merged:
            if snapshot.head_sha == authority.exact_head:
                return DeliveryAcceptanceReconciliationOutcome(
                    change_id=change_id,
                    status=DeliveryAcceptanceReconciliationStatus.WAITING,
                    detail="The pull request is open and not merged.",
                )
            self._reconcile_finalization_head_locked(
                change_id,
                runtime,
                observation=observation,
                acceptance_reason=DeliveryAcceptanceAttentionReason.HEAD_MOVED,
            )
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.HEAD_MOVED,
                code="ERR_DELIVERY_ACCEPTANCE_HEAD_MOVED",
                detail=(
                    "The open pull request head differed from the finalized Change head; finalization was invalidated."
                ),
            )
        if snapshot.state == "closed" and not snapshot.merged:
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request is closed without a merge",),
                reason=DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED,
            )
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.ATTENTION,
                code="ERR_DELIVERY_ACCEPTANCE_ATTENTION",
                detail="The provider pull request is closed without a merge.",
            )
        if not self._acceptance_reconciliation_authority_matches(
            snapshot,
            authority.exact_head,
            authority.ready,
            authority.target_branch,
        ):
            runtime.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence does not match awaiting-merge authority",),
                reason=DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
            )
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.ATTENTION,
                code="ERR_DELIVERY_ACCEPTANCE_ATTENTION",
                detail="Provider acceptance evidence does not match the finalized Change.",
            )
        return None

    @staticmethod
    def _acceptance_reconciliation_authority_matches(
        snapshot: PublicationPullRequest,
        exact_head: str,
        ready: PullRequestReadyReceipt,
        target_branch: str,
    ) -> bool:
        return (
            snapshot.repository == ready.repository
            and snapshot.number == ready.number
            and snapshot.node_id == ready.node_id
            and snapshot.base_branch == target_branch
            and snapshot.head_sha == ready.head_sha == exact_head
        )

    def _remember_acceptance_observation(self, observation: PublicationPullRequestObservationReceipt) -> None:
        self._publication_observation_cache[observation.change_id] = (
            time.monotonic() + _PUBLICATION_OBSERVATION_CACHE_SECONDS,
            observation.snapshot.head_sha,
            observation,
        )

    @staticmethod
    def _provider_unavailable_outcome(
        change_id: str,
        error: PublicationProviderError,
    ) -> DeliveryAcceptanceReconciliationOutcome:
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=DeliveryAcceptanceReconciliationStatus.PROVIDER_UNAVAILABLE,
            code=error.code.value,
            detail=str(error) or error.code.value,
        )

    def observe_acceptance(self, change_id: str) -> CompletionReceipt:
        """Explicitly observe once, including one bounded read after automatic waiting."""
        runtime = self._runtime(change_id, for_mutation=True)
        with self._engine_checkpoint_lock(change_id):
            existing = runtime.completion_receipt()
            if existing is not None:
                self._publish_delivery_state(change_id, runtime, f"acceptance-{existing.completion_id}")
                return existing
            reservation = self._reserve_acceptance_observation(runtime, explicit=True)
            if not reservation.allowed:
                raise DeliveryAcceptanceWaitingError(reservation.reason_code)
            with self._owner_drain_authority(
                change_id,
                f"acceptance:{reservation.attempt_id}",
                *_ACCEPTANCE_DRAIN_MUTATIONS,
            ):
                try:
                    receipt = self._observe_acceptance_once(change_id, runtime, attempt_id=reservation.attempt_id)
                except (DeliveryAcceptanceWaitingError, PublicationProviderError, PortfolioApplicationError) as exc:
                    runtime.retry_ledger(clock=self._clock).record_failure(
                        reservation, failure_code=getattr(exc, "code", "acceptance-wait"), now=self._clock()
                    )
                    self._try_convert_pause_request(change_id, runtime)
                    raise
                runtime.retry_ledger(clock=self._clock).record_accepted_progress(reservation, now=self._clock())
            return receipt

    def _reserve_acceptance_observation(self, runtime: DeliveryRuntime, *, explicit: bool) -> RetryReservation:
        if runtime.change_disposition() is not None:
            message = "Delivery Change requires attention resolution before acceptance observation"
            raise PortfolioApplicationError(message)
        finalization = runtime.finalization()
        if finalization is None or runtime.ready_receipt() is None:
            message = "acceptance observation requires awaiting-merge authority"
            raise PortfolioApplicationError(message)
        change_id = runtime.contract.change_id
        key = RetryEpisodeKey.engine(
            change_id,
            "observe-acceptance",
            finalization.exact_head,
            self._workspace_manager.observed_target_head(),
            finalization.finalization_id,
        )
        ledger = runtime.retry_ledger(clock=self._clock)
        episode = ledger.episode(key)
        try:
            return ledger.reserve(
                key,
                failure_class=RetryFailureClass.ACCEPTANCE,
                now=self._clock(),
                automatic=not (explicit and episode is not None and episode.stop_code is RetryStopCode.ACCEPTANCE_WAIT),
                fence=self._coordinator.prepare_pause_fence(change_id, "provider", "observe-acceptance"),
            )
        except RetryLedgerConflictError:
            self._coordinator.require_pause_permits(change_id, "provider", "observe-acceptance")
            raise

    def _observe_acceptance_once(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        *,
        attempt_id: str,
        observation: PublicationPullRequestObservationReceipt | None = None,
    ) -> CompletionReceipt:
        """Apply one already-reserved observation under the Change checkpoint lock."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        existing = runtime.completion_receipt()
        if existing is not None:
            self._publish_delivery_state(change_id, runtime, f"acceptance-{existing.completion_id}")
            return existing
        if runtime.change_disposition() is not None:
            message = "Delivery Change requires attention resolution before acceptance observation"
            raise PortfolioApplicationError(message)
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        publication = runtime.checkpoint_publication_state()
        if finalization is None or ready is None:
            message = "acceptance observation requires awaiting-merge authority"
            raise PortfolioApplicationError(message)
        if publication.published_head != finalization.exact_head or publication.pending_checkpoint is not None:
            message = "acceptance observation requires the reconciled final checkpoint"
            raise PortfolioApplicationError(message)
        if observation is None:
            self._settle_merge_for_acceptance(change_id)
            observation = self._draft_pull_request_publisher.observe_pull_request(
                ObserveChangePublicationPullRequest(change_id=change_id)
            )
            if observation is not None and not self._settle_for_acceptance_read(change_id, runtime, observation):
                message = "the merge request is not settled yet"
                raise DeliveryAcceptanceWaitingError(message)
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
        ):
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request does not satisfy acceptance authority",),
                reason=DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
            )
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{observation.observation_id}",
            )
            message = "provider pull request does not satisfy acceptance authority"
            raise PortfolioApplicationError(message)
        self._remember_acceptance_observation(observation)
        latch = self._latch_acceptance_observation(change_id, runtime, observation)
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
        completed = self._retry_pause_field_conflict(
            lambda: runtime.complete_change(
                receipt,
                additional_participants=(
                    *runtime.retry_ledger(clock=self._clock).owner_result_participants(
                        attempt_id, accepted=True, now=receipt.completed_at
                    ),
                    self._pause_completion_participant(change_id),
                ),
            )
        )
        self._publish_delivery_state(change_id, runtime, f"acceptance-{receipt.completion_id}")
        self._cleanup_completed_worktree_best_effort(change_id, runtime, completed.completion_id)
        return completed

    def _latch_acceptance_observation(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        observation: PublicationPullRequestObservationReceipt,
    ) -> DeliveryMergedPullRequestLatch:
        """Route one fresh provider observation through the immutable merge latch."""
        if runtime.merged_pull_request_latch() is not None:
            try:
                return runtime.latch_merged_pull_request(observation)
            except DeliveryRuntimeConflictError as exc:
                self._publish_attention_best_effort(
                    change_id,
                    runtime,
                    f"acceptance-attention-{observation.observation_id}",
                )
                message = "provider acceptance evidence regressed from the established merged observation"
                raise PortfolioApplicationError(message) from exc
        if is_acceptance_waiting_observation(observation):
            message = "provider pull request is still open and unmerged"
            raise DeliveryAcceptanceWaitingError(message)
        snapshot = observation.snapshot
        if snapshot.state != "closed" or not snapshot.merged:
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request does not satisfy acceptance authority",),
                reason=DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED,
            )
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{observation.observation_id}",
            )
            message = "provider pull request does not satisfy acceptance authority"
            raise PortfolioApplicationError(message)
        if snapshot.merge_commit_sha is None or snapshot.merged_at is None:
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request is missing merge evidence",),
                reason=DeliveryAcceptanceAttentionReason.MERGE_EVIDENCE_MISSING,
            )
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{observation.observation_id}",
            )
            message = "provider pull request does not satisfy acceptance authority"
            raise PortfolioApplicationError(message)
        return runtime.latch_merged_pull_request(observation)

    def _publish_attention_best_effort(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        operation_id: str,
    ) -> None:
        try:
            self._publish_delivery_state(change_id, runtime, operation_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            _logger.warning(
                "Delivery attention publication failed for Change %s (%s): %s",
                change_id,
                operation_id,
                exc,
            )
            return

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
        self._reconcile_runtimes()
        runtime = self._runtimes.get(change_id)
        if runtime is not None and self._require_revision_allowed(
            change_id, runtime, activation=False, allow_design_return=True
        ):
            try:
                runtime.release_design_return()
            except DesignReturnWorkspaceError as exc:
                raise DeliveryRevisionError(exc.reason, str(exc)) from exc
        if runtime is not None:
            self._require_revision_allowed(change_id, runtime, activation=False)
            # Package replacement clears its authority, after which a pending state publication can never publish.
            self._replay_pending_state_publications(change_id)
            if runtime.pending_state_publication() is not None:
                refusal: tuple[DeliveryRevisionReason, str] = (
                    "publication-pending",
                    "the Delivery state is not published yet; retry once publication succeeds",
                )
                raise DeliveryRevisionError(*refusal)
        return self._package_store.revise(change_id, expected_package_id, intent_bytes, design_bytes)

    def _require_revision_allowed(
        self, change_id: str, runtime: DeliveryRuntime, *, activation: bool, allow_design_return: bool = False
    ) -> bool:
        """Refuse a requirement revision unless the admitted Change is paused, quiescent and nonterminal (I1).

        With ``allow_design_return`` a retained Design-route handoff is accepted; returns whether one is retained.
        """
        frontier = parse_delivery_frontier(runtime.frontier_bytes())[0]
        coordination = self._coordinator.show(change_id)
        action = coordination.continuation_action
        design_return = allow_design_return and any(
            binding.builder_handoff_context is not None
            and binding.builder_handoff_context.route == "same-outcome-design"
            for binding in frontier.bindings
        )
        refusal: tuple[DeliveryRevisionReason, str] | None = None
        if frontier.change_completion is not None or frontier.change_abandonment is not None:
            refusal = ("change-terminal", "a terminal Change is immutable; start a successor Change")
        elif frontier.merged_pull_request_latch is not None:
            refusal = ("change-merged", "the Change pull request is merged; start a successor Change")
        elif frontier.finalization is not None or frontier.ready is not None:
            refusal = ("change-finalized", "run prepare_review_repair, then Pause the Change")
        elif coordination.pause_request is not None:
            refusal = ("pause-pending", "wait until the Pause request becomes a deferral")
        elif frontier.change_deferral is None:
            refusal = ("change-not-paused", "Pause the Change before revising its requirements")
        elif frontier.change_disposition is not None:
            refusal = ("change-attention", "resolve the Change attention first")
        elif (
            any(binding.active_claim is not None for binding in frontier.bindings)
            or (
                not design_return
                and (
                    any(binding.builder_handoff_context is not None for binding in frontier.bindings)
                    or coordination.writer is not None
                    or coordination.builder_handoff is not None
                )
            )
            or frontier.integration_repair_claim is not None
            or (action is not None and action.finished_at is None)
            or (not activation and coordination.design_package_snapshot_intent is not None)
        ):
            refusal = ("custody-retained", "the Change retains worker, handoff or snapshot custody")
        elif activation and runtime.pending_state_publication() is not None:
            refusal = ("publication-pending", "the current Delivery state is not published yet")
        if refusal is not None:
            raise DeliveryRevisionError(*refusal)
        return design_return

    def publish_design_checkpoint(self, change_id: str) -> DesignCheckpointResult:
        """Checkpoint one verified active package without touching product refs."""
        return self._package_store.checkpoint(change_id)

    def derive_delivery_contract(self, change_id: str) -> DeliveryCompilationResult:
        """Compile one verified package without publishing generated authority."""
        package = self._package_store.read_verified(change_id)
        return compile_delivery_contract(change_id, package.intent_bytes, package.design_bytes)

    def admit_delivery_change(self, request: DeliveryAdmissionRequest) -> DeliveryAdmissionResult:
        """Admit source-bound Delivery authority through the owning registry."""
        self._reconcile_runtimes()
        runtime = self._runtimes.get(request.change_id)
        if runtime is not None and self._revision_pending(request.change_id, runtime):
            return self._activate_revision(request, runtime)
        with self._coordinator.acquisition_lock():
            runtime = self._runtimes.get(request.change_id)
            if runtime is not None:
                coordination = self._coordinator.find_registered(request.change_id)
                if (
                    coordination is not None
                    and (coordination.builder_handoff is not None or coordination.writer is not None)
                ) or any(binding.builder_handoff_context is not None for binding in runtime.bindings()):
                    message = "retained handoff or writer blocks admission"
                    raise DeliveryAdmissionConflictError(message)
            self._workspace_manager.validate_recovery(request.change_id, request.recovery_reviewed_head)
            result = self._authority_registry.admit(request)
            self._workspace_manager.ensure(
                request.change_id,
                recovery_reviewed_head=request.recovery_reviewed_head,
            )
            runtime = DeliveryRuntime(
                self._target_root,
                result.contract,
                workspace_manager=self._workspace_manager,
            )
            with self._runtime_reconciliation_lock:
                self._runtimes = {**self._runtimes, request.change_id: runtime}
            package = self._package_store.read_verified(request.change_id)
            self._validate_package_authority(runtime, package)
            snapshot = self._workspace_manager.snapshot_design_package(
                request.change_id,
                package.package_id,
                {
                    "authority.json": package.authority_bytes,
                    "design.md": package.design_bytes,
                    "intent.md": package.intent_bytes,
                    "manifest.json": package.manifest.canonical_bytes(),
                },
                _checkpoint_operation_id("package", request.change_id, package.package_id),
                request.expected_design_package_snapshot_receipt_id,
            )
            checkpoint = runtime.checkpoint_publication_state()
            if checkpoint.pending_checkpoint is not None:
                runtime.record_design_package_snapshot(checkpoint, snapshot)
            elif checkpoint.published_head is not None and checkpoint.published_head != snapshot.snapshot_head:
                runtime.queue_explicit_checkpoint(snapshot.snapshot_head)
            else:
                runtime.queue_admitted_design_checkpoint(snapshot.snapshot_head)
            if self._change_branch_publisher is not None and self._draft_pull_request_publisher is not None:
                self._reconcile_change_checkpoint(request.change_id, runtime)
            self._reconcile_runtimes()
            return result.model_copy(update={"frontier": parse_delivery_frontier(runtime.frontier_bytes())[0]})

    def _revision_pending(self, change_id: str, runtime: DeliveryRuntime) -> bool:
        """Return whether the active package differs from the admitted authority or its branch snapshot."""
        coordination = self._coordinator.find_registered(change_id)
        if coordination is None:
            return False
        package = self._package_store.read_verified(change_id)
        compiled = compile_delivery_contract(change_id, package.intent_bytes, package.design_bytes)
        snapshot = coordination.design_package_snapshot
        return (compiled.digest is not None and compiled.digest != runtime.authority_digest) or (
            snapshot is not None
            and (snapshot.package_id != package.package_id or coordination.design_package_snapshot_intent is not None)
        )

    def _activate_revision(
        self, request: DeliveryAdmissionRequest, runtime: DeliveryRuntime
    ) -> DeliveryAdmissionResult:
        """§1.5: publish the contract, snapshot on the reviewed head, then one authority transaction."""
        change_id = request.change_id
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            self._replay_pending_state_publications(change_id)
            self._require_revision_allowed(change_id, runtime, activation=True)
            coordination = self._coordinator.show(change_id)
            if request.expected_frontier_digest is None:
                message = "requirement revision requires the expected frontier digest"
                raise DeliveryAdmissionConflictError(message)
            if coordination.design_package_snapshot_intent is None:
                try:
                    self._workspace_manager.reviewed_source_head(change_id)
                except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                    moved = DeliveryRevisionError(
                        "reviewed-head-moved", "the Change branch or worktree differs from its reviewed head"
                    )
                    raise moved from exc
            result = self._authority_registry.activate_revision(
                request,
                snapshot=lambda: self._revision_snapshot_head(request),
                base_frontier_digest=runtime.published_projection_digest(runtime.frontier_bytes()),
            )
            runtime = DeliveryRuntime(self._target_root, result.contract, workspace_manager=self._workspace_manager)
            with self._runtime_reconciliation_lock:
                self._runtimes = {**self._runtimes, change_id: runtime}
            try:
                if self._change_branch_publisher is not None and self._draft_pull_request_publisher is not None:
                    self._reconcile_change_checkpoint(change_id, runtime)
                else:
                    self._publish_delivery_state(
                        change_id, runtime, _checkpoint_operation_id("revision", change_id, result.contract_digest)
                    )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                _logger.warning("Revised Change %s kept its state publication pending: %s", change_id, exc)
        self._reconcile_runtimes()
        return result.model_copy(update={"frontier": parse_delivery_frontier(runtime.frontier_bytes())[0]})

    def _revision_snapshot_head(self, request: DeliveryAdmissionRequest) -> str:
        """Return the reviewed head carrying the active package, committing a snapshot when it differs."""
        package = self._package_store.read_verified(request.change_id)
        coordination = self._coordinator.show(request.change_id)
        receipt = coordination.design_package_snapshot
        if (
            coordination.design_package_snapshot_intent is None
            and receipt is not None
            and receipt.package_id == package.package_id
        ):
            return coordination.last_reviewed_commit
        return self._workspace_manager.snapshot_design_package(
            request.change_id,
            package.package_id,
            {
                "authority.json": package.authority_bytes,
                "design.md": package.design_bytes,
                "intent.md": package.intent_bytes,
                "manifest.json": package.manifest.canonical_bytes(),
            },
            _checkpoint_operation_id("package", request.change_id, package.package_id),
            request.expected_design_package_snapshot_receipt_id
            or (receipt.receipt_id if receipt is not None else None),
        ).snapshot_head

    def admit_change(self, request: DeliveryAdmissionRequest) -> DeliveryAdmissionResult:
        """Admit one exact approved Design version as executable Delivery authority."""
        return self.admit_delivery_change(request)

    def publish_delivery_plan(
        self,
        change_id: str,
        request: PublishDeliveryPlan,
    ) -> DeliveryPlanCandidate:
        """Publish one validated Planning candidate through its exact runtime."""
        runtime = self._runtime(change_id, for_mutation=True)
        return runtime.publish_plan(request)

    def publish_delivery_result(
        self,
        change_id: str,
        request: PublishDeliveryResult,
    ) -> DeliveryResultCandidate:
        """Publish one validated Build result through its exact runtime."""
        runtime = self._runtime(change_id, for_mutation=True)
        return runtime.publish_result(request)

    def _reconcile_runtimes(self) -> None:
        with self._runtime_reconciliation_lock:
            previous_runtimes = self._runtimes
            initial_reconciliation = not self._has_reconciled_runtimes
        reconciled, observations, reconciliation_errors = self._reconcile_runtime_snapshot(
            previous_runtimes,
            initial_reconciliation=initial_reconciliation,
        )
        self._publish_reconciled_runtimes(
            previous_runtimes,
            reconciled,
            observations,
            reconciliation_errors,
        )

    def _reconcile_runtime_snapshot(
        self,
        previous_runtimes: dict[str, DeliveryRuntime],
        *,
        initial_reconciliation: bool,
    ) -> tuple[
        dict[str, DeliveryRuntime],
        dict[str, DeliveryChangeObservation],
        dict[str, str],
    ]:
        try:
            discovered = discover_persisted_changes(self._target_root)
        except DeliveryDiscoveryRootError as exc:
            raise DeliveryRuntimeReconciliationError(None, exc.detail) from exc

        observations = {observation.change_id: observation for observation in discovered}
        reconciled: dict[str, DeliveryRuntime] = {}
        reconciliation_errors = {
            diagnostic.change_id: f"{diagnostic.code}: {diagnostic.detail}"
            for diagnostic in self._startup_health_diagnostics
            if diagnostic.change_id is not None
        }

        for change_id, runtime in previous_runtimes.items():
            observation = observations.get(change_id)
            if observation is None:
                continue
            reconciled_runtime, error = self._reconcile_existing_runtime(
                runtime,
                observation,
                initial_reconciliation=initial_reconciliation,
            )
            if reconciled_runtime is not None:
                reconciled[change_id] = reconciled_runtime
            if error is not None and change_id not in reconciliation_errors:
                reconciliation_errors[change_id] = error

        for change_id, observation in observations.items():
            if change_id in reconciled:
                continue
            runtime, error = self._reconcile_new_runtime(observation)
            if runtime is not None:
                reconciled[change_id] = runtime
            if error is not None and change_id not in reconciliation_errors:
                reconciliation_errors[change_id] = error

        return reconciled, observations, reconciliation_errors

    def _publish_reconciled_runtimes(
        self,
        previous_runtimes: dict[str, DeliveryRuntime],
        reconciled: dict[str, DeliveryRuntime],
        observations: dict[str, DeliveryChangeObservation],
        reconciliation_errors: dict[str, str],
    ) -> None:
        with self._runtime_reconciliation_lock:
            current_runtimes = self._runtimes
            if current_runtimes is not previous_runtimes:
                for change_id in previous_runtimes.keys() - current_runtimes.keys():
                    reconciled.pop(change_id, None)
                reconciled.update(
                    {
                        change_id: runtime
                        for change_id, runtime in current_runtimes.items()
                        if previous_runtimes.get(change_id) is not runtime
                    }
                )
            self._runtimes = reconciled
            self._discovered_changes = observations
            self._runtime_reconciliation_errors = reconciliation_errors
            self._has_reconciled_runtimes = True

    def _reconcile_existing_runtime(
        self,
        runtime: DeliveryRuntime,
        observation: DeliveryChangeObservation,
        *,
        initial_reconciliation: bool,
    ) -> tuple[DeliveryRuntime | None, str | None]:
        active = self._runtime_has_active_work(runtime)
        reconciled_runtime: DeliveryRuntime | None = runtime
        error: str | None = None
        if not observation.admitted:
            if self._retain_unadmitted_runtime(
                observation,
                active=active,
                initial_reconciliation=initial_reconciliation,
            ):
                error = self._observation_detail(observation)
            else:
                reconciled_runtime = None
        elif not observation.actionable_runtime or observation.contract is None:
            error = self._observation_detail(observation)
        elif observation.contract_fingerprint != contract_fingerprint(runtime.contract):
            if active:
                error = "persisted contract fingerprint differs from runtime authority"
            else:
                try:
                    reconciled_runtime = self._compose_runtime(observation)
                except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                    error = str(exc) or "replacement runtime is unavailable"
        return reconciled_runtime, error

    @staticmethod
    def _retain_unadmitted_runtime(
        observation: DeliveryChangeObservation,
        *,
        active: bool,
        initial_reconciliation: bool,
    ) -> bool:
        return (
            active
            or not initial_reconciliation
            or (
                initial_reconciliation
                and observation.frontier is not None
                and any(binding.results for binding in observation.frontier.bindings)
            )
        )

    def _reconcile_new_runtime(
        self,
        observation: DeliveryChangeObservation,
    ) -> tuple[DeliveryRuntime | None, str | None]:
        if not observation.admitted or not observation.actionable_runtime or observation.contract is None:
            if observation.admitted and not observation.actionable_runtime:
                return None, self._observation_detail(observation)
            return None, None
        try:
            return self._compose_runtime(observation), None
        except (OSError, RuntimeError, ValueError) as exc:
            return None, _health_detail(str(exc), "runtime is unavailable")

    def _compose_runtime(self, observation: DeliveryChangeObservation) -> DeliveryRuntime:
        if observation.contract is None:
            self._fail("reconciled Change contract is unavailable")
        return DeliveryRuntime(
            self._target_root,
            observation.contract,
            workspace_manager=self._workspace_manager,
        )

    @staticmethod
    def _runtime_has_active_work(runtime: DeliveryRuntime) -> bool:
        try:
            return bool(runtime.active_claims()) or runtime.integration_repair_claim() is not None
        except OSError, RuntimeError, ValueError:
            return True

    @staticmethod
    def _observation_detail(observation: DeliveryChangeObservation) -> str:
        code = observation.diagnostic_code
        detail = observation.diagnostic_detail or "persisted Change authority is unavailable"
        return f"{code}: {detail}" if code is not None else detail

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

    def get_change(self, change_id: str) -> DeliveryChangeView | DeliveryUnavailableChangeView:
        """Return one coherent Change view without requiring caller-side projection joins."""
        self._reconcile_runtimes()
        observation = self._discovered_changes.get(change_id)
        if observation is not None and (not observation.actionable_runtime or change_id not in self._runtimes):
            return self._unavailable_change(change_id)
        runtime = self._runtime(change_id)
        try:
            coordination = self._workspace_manager.show(change_id)
        except OSError, RuntimeError, ValueError:
            return self._unavailable_change(change_id, "coordination-unavailable")
        snapshot = self._delivery_snapshot(runtime)
        proposal = self._repair_proposal(snapshot)
        projector = self._read_projector(snapshot)
        frontier_digest = snapshot.version
        items = projector.group_view().items
        if not items:
            self._fail(f"Change has no projected work items: {change_id}")
        item_key = self._selected_change_card(snapshot, items).item_key
        detail = self._captured_detail(runtime, projector, item_key)
        health = self._delivery_health_view(scoped_change_id=change_id, inspect_workspaces=False)
        unresolved_outcomes = tuple(
            DeliveryUnresolvedOutcome(
                outcome_id=outcome_detail.card.work_item_id,
                card=outcome_detail.card,
                requests=tuple(request for request in outcome_detail.requests if request.resolution is None),
                block=outcome_detail.block if outcome_detail.block and not outcome_detail.block.resolved else None,
                active_claim=outcome_detail.active_claim,
                recovery_attention=outcome_detail.recovery_attention,
            )
            for card in items
            if card.scope is WorkItemScope.OUTCOME
            for outcome_detail in (projector.show_view(card.item_key),)
            if (
                any(request.resolution is None for request in outcome_detail.requests)
                or (outcome_detail.block is not None and not outcome_detail.block.resolved)
                or outcome_detail.active_claim is not None
                or outcome_detail.recovery_attention is not None
            )
        )
        return DeliveryChangeView(
            change_id=change_id,
            finalization_attempt=coordination.finalization_attempt,
            continuation_action=coordination.continuation_action,
            frontier_digest=frontier_digest,
            detail=detail,
            health=health,
            repair=DeliveryRepairResult(change_id=change_id, proposal=proposal) if proposal is not None else None,
            unresolved_outcomes=unresolved_outcomes,
            readiness=detail.readiness,
            pause_requested=coordination.pause_request is not None,
            evidence=projector.evidence(),
        )

    def set_change_intent(self, intent: DeliveryChangeIntent) -> DeliveryChangeIntentResult:
        """Apply one version-bound user lifecycle intent through the owning runtime."""
        if intent.kind is DeliveryChangeIntentKind.DEFER:
            return self._admit_pause(intent)
        if (
            intent.kind is DeliveryChangeIntentKind.RESUME
            and self._coordinator.find_registered(intent.change_id) is not None
            and self._coordinator.pause_request(intent.change_id) is not None
        ):
            return self._admit_pause(intent)
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(intent.change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(intent.change_id),)):
                attention = self._workspace_manager.show(intent.change_id).finalization_attention
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
                if current_digest != intent.expected_frontier_digest:
                    if intent.kind is DeliveryChangeIntentKind.ABANDON:
                        receipt = runtime.change_abandonment()
                        if receipt is not None and receipt.reason == intent.reason:
                            return DeliveryChangeIntentResult(
                                change_id=intent.change_id,
                                kind=intent.kind,
                                frontier_digest=current_digest,
                                receipt=receipt,
                            )
                    self._fail("Change intent frontier changed")
                if intent.kind is DeliveryChangeIntentKind.RESUME:
                    receipt = runtime.resume_change(expected_finalization_attention=attention)
                else:
                    if intent.reason is None:
                        self._fail("abandon intent requires a reason")
                    receipt = runtime.abandon_change(
                        intent.reason,
                        _timestamp(self._clock()),
                        expected_finalization_attention=attention,
                        pause_request_clear=self._pause_request_clear(intent.change_id),
                    )
                self._publish_delivery_state(
                    intent.change_id,
                    runtime,
                    _checkpoint_operation_id(intent.kind.value, intent.change_id, receipt.model_dump_json()),
                )
                return DeliveryChangeIntentResult(
                    change_id=intent.change_id,
                    kind=intent.kind,
                    frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                    receipt=receipt,
                )

    def _admit_pause(self, intent: DeliveryChangeIntent) -> DeliveryChangeIntentResult:
        """§1.11 K1: record or clear a Pause request without any Change lock, then try to convert."""
        runtime = self._pause_runtime(intent.change_id)
        try:
            self._workspace_manager.show(intent.change_id)
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(intent.change_id, str(exc)) from exc
        current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
        if runtime.change_abandonment() is not None or runtime.completion_receipt() is not None:
            self._fail("terminal Delivery Change cannot be paused or resumed")
        if intent.kind is DeliveryChangeIntentKind.RESUME:
            return self._clear_unconverted_pause(intent, current_digest)
        if intent.reason is None:
            self._fail("defer intent requires a reason")
        deferral = runtime.change_deferral()
        if deferral is not None:
            if deferral.reason != intent.reason:
                if current_digest != intent.expected_frontier_digest:
                    self._fail("Change intent frontier changed")
                self._fail("Delivery Change is already paused with another reason")
            return DeliveryChangeIntentResult(
                change_id=intent.change_id, kind=intent.kind, frontier_digest=current_digest, receipt=deferral
            )
        request = ChangePauseRequest.create(
            change_id=intent.change_id,
            reason=intent.reason,
            requested_at=_timestamp(self._clock()).isoformat(),
        )
        existing = self._coordinator.pause_request(intent.change_id)
        if existing is None and current_digest != intent.expected_frontier_digest:
            self._fail("Change intent frontier changed")
        try:
            recorded = self._workspace_manager.record_pause_request(request, intent.expected_frontier_digest)
        except CoordinationConflictError as exc:
            self._fail(str(exc), exc)
        converted = self._convert_pause_request_unlocked(intent.change_id)
        receipt: DeliveryChangeDeferral | ChangePauseRequest = converted if converted is not None else recorded
        return DeliveryChangeIntentResult(
            change_id=intent.change_id,
            kind=intent.kind,
            frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            receipt=receipt,
        )

    def _pause_runtime(self, change_id: str) -> DeliveryRuntime:
        """K1 Validate reads without the mutation guard, but never admits Pause on an unreconciled runtime."""
        runtime = self._runtime(change_id)
        detail = self._runtime_reconciliation_errors.get(change_id)
        if detail is not None:
            raise DeliveryRuntimeReconciliationError(change_id, detail)
        return runtime

    def _clear_unconverted_pause(self, intent: DeliveryChangeIntent, current_digest: str) -> DeliveryChangeIntentResult:
        """K1 Resume of a draining request: clear it through its frontier-bound transaction."""
        try:
            cleared = self._workspace_manager.clear_pause_request(intent.change_id, intent.expected_frontier_digest)
        except CoordinationConflictError as exc:
            self._fail(str(exc), exc)
        if cleared is None:
            self._fail("Delivery Change is not paused")
        return DeliveryChangeIntentResult(
            change_id=intent.change_id, kind=intent.kind, frontier_digest=current_digest, receipt=cleared
        )

    def submit_result(self, submission: DeliveryResultSubmission) -> DeliveryResultSubmissionResult:
        """Publish and promote one exact Builder result as one claim-bound operation."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(submission.change_id, for_mutation=True)
            with (
                locked_roots((self._checkpoint_lock_root(submission.change_id),)),
                self._worker_drain_authority(
                    runtime,
                    submission.outcome_id,
                    submission.claim_id,
                    replay_digest=self._result_replay_transition_digest(runtime, submission),
                ),
            ):
                result = self._submit_result_locked(runtime, submission)
                self._try_convert_pause_request(submission.change_id, runtime)
                return result

    @contextmanager
    def _worker_drain_authority(
        self, runtime: DeliveryRuntime, outcome_id: str, claim_id: str, *, replay_digest: str | None = None
    ) -> Iterator[DrainAuthority]:
        """K2 claim/settlement owner token: a live claim, or a replay bound only to its own request digest.

        ``replay_digest`` is derived from the replaying owner's own durable authority, never from the pending
        intent; without it a replay token permits no state publication.
        """
        change_id = runtime.contract.change_id
        claim = runtime.show_binding(outcome_id).active_claim
        live = claim is not None and claim.claim_id == claim_id
        with self._owner_drain_authority(
            change_id,
            f"claim:{claim_id}",
            bound=None if live else replay_digest,
            publishes_checkpoint=True,
        ) as authority:
            if not live:
                authority.permits.setdefault("state", set())
            yield authority

    @staticmethod
    def _result_replay_transition_digest(runtime: DeliveryRuntime, submission: DeliveryResultSubmission) -> str | None:
        """K2 ``submit_result`` replay: digest of the internal advance rebuilt from the immutable result receipt."""
        binding = runtime.show_binding(submission.outcome_id)
        claim = binding.active_claim
        if claim is not None and claim.claim_id == submission.claim_id:
            return None
        if not any(item == submission.result for item in binding.results):
            return None
        receipt = runtime.require_result_replay(submission.outcome_id, submission.claim_id, submission.result)
        advance = AdvanceDelivery(
            action="advance",
            outcome_id=submission.outcome_id,
            claim_id=submission.claim_id,
            output=receipt.output,
        )
        return hashlib.sha256(_canonical_model_bytes(advance)).hexdigest()

    def _submit_result_locked(
        self, runtime: DeliveryRuntime, submission: DeliveryResultSubmission
    ) -> DeliveryResultSubmissionResult:
        self._import_legacy_worker_budgets(runtime)
        binding = runtime.show_binding(submission.outcome_id)
        operation_id = _checkpoint_operation_id(
            "submit-result",
            submission.change_id,
            submission.outcome_id,
            submission.result.result_id,
        )
        existing = next(
            (item for item in binding.results if item.task_id == submission.result.task_id),
            None,
        )
        if existing is not None:
            if existing != submission.result or (
                binding.active_claim is not None and binding.active_claim.task_id == submission.result.task_id
            ):
                self._fail("submitted result conflicts with current Outcome authority")
            runtime.require_result_replay(submission.outcome_id, submission.claim_id, submission.result)
            self._record_worker_retry_success(runtime, submission.outcome_id, submission.claim_id)
            if runtime.pending_state_publication() is not None:
                self._publish_delivery_state(submission.change_id, runtime, operation_id)
            return DeliveryResultSubmissionResult(
                change_id=submission.change_id,
                outcome_id=submission.outcome_id,
                claim_id=submission.claim_id,
                result_id=submission.result.result_id,
                binding=binding,
            )
        candidate = runtime.publish_result(
            PublishDeliveryResult(
                outcome_id=submission.outcome_id,
                claim_id=submission.claim_id,
                result=submission.result,
            )
        )
        binding = runtime.transition(
            AdvanceDelivery(
                action="advance",
                outcome_id=submission.outcome_id,
                claim_id=submission.claim_id,
                output=candidate.output,
            ),
            retry_observed_at=self._clock(),
        )
        self._record_worker_retry_success(runtime, submission.outcome_id, submission.claim_id)
        self._publish_delivery_state(submission.change_id, runtime, operation_id)
        return DeliveryResultSubmissionResult(
            change_id=submission.change_id,
            outcome_id=submission.outcome_id,
            claim_id=submission.claim_id,
            result_id=submission.result.result_id,
            binding=binding,
        )

    def answer(  # noqa: C901, PLR0911
        self,
        answer: DeliveryAnswer,
        *,
        allow_user_only: bool = False,
    ) -> DeliveryAnswerResult:
        """Apply one version-bound request answer or requestless block evidence.

        A waiver or person-only confirmation (a request scoped to acceptance criteria) is answered only
        by the user in Cockpit, which passes ``allow_user_only``; agents' tools never do.
        """
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(answer.change_id, for_mutation=True)
            checkpoint_lock = (
                self._attention_resolution_lock(answer.change_id)
                if answer.kind is DeliveryAnswerKind.DISPOSITION
                else locked_roots((self._checkpoint_lock_root(answer.change_id),))
            )
            with checkpoint_lock:
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
                if answer.kind is DeliveryAnswerKind.REQUEST:
                    current = self._request(runtime, answer.request_id)
                    if current.applies_to is not None and not allow_user_only:
                        message = "a waiver or person-only confirmation request is answered by the user in Cockpit"
                        raise DeliveryConfirmationError(message)
                    if current.kind is DeliveryRequestKind.DECISION and (
                        answer.resolution.selected_option_id is None or answer.resolution.response_text is not None
                    ):
                        self._fail("Decision answers require exactly one selected option")
                    if current_digest != answer.expected_frontier_digest:
                        if current.resolution == answer.resolution:
                            return DeliveryAnswerResult(
                                change_id=answer.change_id,
                                kind=answer.kind,
                                request=current,
                                frontier_digest=current_digest,
                            )
                        self._fail("answer frontier changed")
                    resolved = runtime.resolve_request(answer.request_id, answer.resolution)
                    self._publish_delivery_state(
                        answer.change_id,
                        runtime,
                        _checkpoint_operation_id("request-answer", answer.change_id, answer.request_id),
                    )
                    return DeliveryAnswerResult(
                        change_id=answer.change_id,
                        kind=answer.kind,
                        request=resolved,
                        frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                    )

                if answer.kind is DeliveryAnswerKind.BLOCK:
                    binding = runtime.show_binding(answer.outcome_id)
                    block = binding.block
                    if current_digest != answer.expected_frontier_digest:
                        if (
                            block is not None
                            and block.resolved
                            and block.resolution_note == answer.operator_note
                            and block.resolution_locators == answer.locators
                        ):
                            return DeliveryAnswerResult(
                                change_id=answer.change_id,
                                kind=answer.kind,
                                binding=binding,
                                frontier_digest=current_digest,
                            )
                        self._fail("answer frontier changed")
                    cleared = runtime.unblock(
                        answer.outcome_id,
                        answer.block_id,
                        answer.operator_note,
                        answer.locators,
                    )
                    self._publish_delivery_state(
                        answer.change_id,
                        runtime,
                        _checkpoint_operation_id("block-answer", answer.change_id, answer.outcome_id, answer.block_id),
                    )
                    return DeliveryAnswerResult(
                        change_id=answer.change_id,
                        kind=answer.kind,
                        binding=cleared,
                        frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                    )

                disposition = runtime.change_disposition()
                resolution = runtime.change_disposition_resolution()
                if current_digest != answer.expected_frontier_digest:
                    if resolution is not None and resolution.disposition_id == answer.expected_disposition_id:
                        return DeliveryAnswerResult(
                            change_id=answer.change_id,
                            kind=answer.kind,
                            disposition=resolution,
                            frontier_digest=current_digest,
                        )
                    self._fail("answer frontier changed")
                if disposition is None and resolution is not None:
                    if resolution.disposition_id != answer.expected_disposition_id:
                        self._fail("answer disposition is stale")
                    return DeliveryAnswerResult(
                        change_id=answer.change_id,
                        kind=answer.kind,
                        disposition=resolution,
                        frontier_digest=current_digest,
                    )
                resolved = runtime.resolve_change_disposition(
                    answer.expected_disposition_id,
                    _timestamp(self._clock()),
                )
                self._publish_delivery_state(
                    answer.change_id,
                    runtime,
                    f"attention-resolution-{resolved.resolution_id}",
                )
                return DeliveryAnswerResult(
                    change_id=answer.change_id,
                    kind=answer.kind,
                    disposition=resolved,
                    frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                )

    @staticmethod
    def _exact_task_scope(task: DeliveryTaskDefinition, worktree: Path) -> tuple[str, ...]:
        scope, _kinds = PortfolioApplication._exact_task_scope_details(task, worktree)
        return scope

    @staticmethod
    def _recovery_admission_fields(
        task: DeliveryTaskDefinition | None,
        paths: tuple[str, ...],
        worktree: Path,
        *,
        scope_details: tuple[tuple[str, ...], dict[str, Literal["directory", "file", "missing"]]] | None = None,
    ) -> tuple[str | None, str | None, tuple[str, ...], tuple[str, ...]]:
        if task is None:
            if paths:
                raise DeliveryWorkerExclusionRequiredError
            return None, None, (), ()
        if any(not is_canonical_admitted_path(path) for path in paths):
            raise DeliveryWorkerExclusionRequiredError
        if not paths:
            # Clean Recovery-A carries no path authority; unsupported task-scope
            # descriptors remain a dirty-admission concern only.
            return None, None, (), ()
        scope, scope_kinds = scope_details or PortfolioApplication._exact_task_scope_details(task, worktree)
        admitted_paths = tuple(sorted(paths))
        if any(
            not any(
                PortfolioApplication._scope_admits_path(
                    worktree,
                    candidate,
                    path,
                    scope_kind=scope_kinds[candidate],
                )
                for candidate in scope
            )
            for path in admitted_paths
        ):
            raise DeliveryWorkerExclusionRequiredError
        return task.task_id, task.digest, scope, admitted_paths

    def _reserve_worker_attempt(
        self,
        candidate: _Candidate,
        source: _PreparedSource,
        attempt_id: str,
        claim_id: str,
    ) -> RetryReservation | None:
        """Reserve worker/check repair before publishing a claim or writer."""
        key = self._worker_retry_key(candidate, source.coordination.last_reviewed_commit)
        ledger = candidate.runtime.retry_ledger(clock=self._clock)
        ledger.import_legacy_failures(key, candidate.binding.retry_count, now=self._clock())
        return ledger.reserve(
            key,
            failure_class=RetryFailureClass.MECHANICAL,
            now=self._clock(),
            attempt_id=attempt_id,
            automatic=True,
            operation_alias=claim_id,
        )

    @staticmethod
    def _worker_retry_key(candidate: _Candidate, source_head: str) -> RetryEpisodeKey:
        original_candidate = (
            candidate.binding.candidate.digest
            if candidate.binding.candidate is not None
            else candidate.binding.result_candidate.digest
            if candidate.binding.result_candidate is not None
            else candidate.binding.outcome_id
        )
        return RetryEpisodeKey.worker(
            candidate.change_id,
            f"{candidate.role.value}-claim",
            source_head,
            contract_digest=contract_fingerprint(candidate.runtime.contract),
            outcome_id=candidate.binding.outcome_id,
            task_lineage=candidate.task_id or candidate.binding.outcome_id,
            procedure_class=candidate.role.value,
            original_candidate=original_candidate,
        )

    def _current_launch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        binding: OutcomeAuthorityBinding,
    ) -> DeliveryLaunchPackage:
        claim = binding.active_claim
        if claim is None:
            self._fail("outcome has no active claim")
        candidate = _Candidate((0, 0, 0, change_id), change_id, runtime, binding, claim.task_id, claim.worker_role)
        source = self._prepare_source(candidate, allow_dirty=claim.worker_role is DeliveryWorkerRole.BUILDER)
        if isinstance(source, DeliveryAcquisitionFailure):
            self._fail(source.detail)
        writer = source.coordination.writer if claim.worker_role == DeliveryWorkerRole.BUILDER else None
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
            builder_handoff_context=candidate.binding.builder_handoff_context,
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
        return snapshot.worktree_head == snapshot.branch_head and snapshot.worktree_branch == snapshot.branch

    def _retain_recovery_attention(  # noqa: PLR0913 - recovery attention binds exact claim and workspace evidence.
        self,
        runtime: DeliveryRuntime,
        outcome_id: str,
        claim: DeliveryActiveClaim,
        snapshot: WorkspaceRecoverySnapshot,
        *,
        reason: str | None = None,
        retry_condition: str = "Restore a clean recorded worktree and reconcile exact writer custody.",
    ) -> DeliveryClaimRecoveryResult:
        attention = DeliveryRecoveryAttention(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            reason=reason or self._recovery_reason(snapshot, claim),
            worktree_path=str(snapshot.worktree_path),
            branch_head=snapshot.branch_head,
            worktree_head=snapshot.worktree_head,
            last_reviewed_commit=snapshot.last_reviewed_commit,
            writer_claim_id=snapshot.writer.claim_id if snapshot.writer is not None else None,
            custody_retained=snapshot.writer is not None,
            retry_condition=retry_condition,
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
    def _recovered(  # noqa: PLR0913 - recovery result binds exact claim and preservation evidence.
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        preserved_commit: str | None = None,
        *,
        quarantine_commit: str | None = None,
        quarantine_ref: str | None = None,
    ) -> DeliveryClaimRecoveryResult:
        return DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.RECOVERED,
            change_id=change_id,
            outcome_id=outcome_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            preserved_commit=preserved_commit,
            preserved_ref=(f"refs/owlbear/attempts/{change_id}/{attempt_id}" if preserved_commit is not None else None),
            quarantine_commit=quarantine_commit,
            quarantine_ref=quarantine_ref,
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

    def _publish_delivery_state(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        operation_id: str,
        *,
        expected_remote_head: str | None = None,
    ) -> DeliveryStatePublicationReceipt | None:
        if self._delivery_state_publisher is None or any(
            binding.builder_handoff_context is not None for binding in runtime.bindings()
        ):
            return None
        self._require_publication_drain(change_id, runtime)
        checkpoint = runtime.checkpoint_publication_state()
        pending = checkpoint.pending_checkpoint
        if pending is not None and pending.head is not None and checkpoint.published_head != pending.head:
            branch_receipt = self._publish_checkpoint_branch(change_id, checkpoint, pending.head)
            runtime.record_checkpoint_branch_publication(checkpoint, branch_receipt.published_head)
        package = self._package_store.read_verified(change_id)
        self._validate_package_authority(runtime, package)
        admission_path = self._target_root / "changes" / change_id / "admission.json"
        admission = DeliveryAdmissionReceipt.model_validate_json(admission_path.read_bytes())
        publication = self._delivery_state_publisher.publish(
            change_id=change_id,
            package_id=package.package_id,
            coordination=self._workspace_manager.show(change_id),
            runtime=runtime,
            admission=admission,
            operation_id=operation_id,
            captured_at=_timestamp(self._clock()),
            expected_remote_head=expected_remote_head,
        )
        runtime.acknowledge_pending_publication(hashlib.sha256(runtime.frontier_bytes()).hexdigest())
        return publication

    def _dependency_depth(self, runtime: DeliveryRuntime, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in runtime.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)

    def _runtime(self, change_id: str, *, for_mutation: bool = False, allow_finalizer: bool = False) -> DeliveryRuntime:
        self._reconcile_runtimes()
        try:
            runtime = self._runtimes[change_id]
        except KeyError as exc:
            detail = self._runtime_reconciliation_errors.get(change_id)
            if detail is not None:
                raise DeliveryRuntimeReconciliationError(change_id, detail) from exc
            self._fail(f"Delivery runtime is absent: {change_id}", exc)
        if for_mutation:
            detail = self._runtime_reconciliation_errors.get(change_id)
            if detail is not None:
                raise DeliveryRuntimeReconciliationError(change_id, detail)
            try:
                coordination = self._workspace_manager.show(change_id)
            except (OSError, RuntimeError, ValueError) as exc:
                raise DeliveryRuntimeReconciliationError(change_id, str(exc)) from exc
            self._coordinator.require_no_pending_recovery(change_id)
            action = coordination.continuation_action
            if (
                action is not None
                and action.finished_at is None
                and not self._coordinator.executing_continuation(change_id)
            ):
                message = f"selected Change retains engine action custody: {action.operation_id}"
                raise DeliveryActionBusyError(message)
            writer = coordination.writer
            if not allow_finalizer and writer is not None and writer.kind == "finalize":
                message = "selected Change retains active finalizer custody"
                raise DeliveryActionBusyError(message)
        return runtime

    def _require_target_sync_change_mutable(self, runtime: DeliveryRuntime) -> None:
        if runtime.change_stage() in {
            DeliveryChangeStage.DEFERRED,
            DeliveryChangeStage.ABANDONED,
            DeliveryChangeStage.COMPLETED,
        }:
            self._fail("target synchronization requires a mutable Change")

    def _require_external_head_adoption_change_mutable(self, runtime: DeliveryRuntime) -> None:
        if runtime.change_stage() in {
            DeliveryChangeStage.DEFERRED,
            DeliveryChangeStage.ABANDONED,
            DeliveryChangeStage.COMPLETED,
        }:
            self._fail("external Change head adoption requires a mutable Change")

    def _require_external_head_promotion_change_mutable(self, runtime: DeliveryRuntime) -> None:
        if (
            runtime.change_stage()
            in {
                DeliveryChangeStage.DEFERRED,
                DeliveryChangeStage.ABANDONED,
                DeliveryChangeStage.COMPLETED,
            }
            or runtime.finalization() is not None
        ):
            self._fail("external Change head promotion requires a pre-finalization mutable Change")

    def _checkpoint_lock_root(self, change_id: str) -> Path:
        return self._target_root / "publications/checkpoints/locks" / change_id

    @staticmethod
    def _outcome(runtime: DeliveryRuntime, outcome_id: str) -> DeliveryOutcome:
        return next(item for item in runtime.contract.outcomes if item.outcome_id == outcome_id)

    @staticmethod
    def _request(runtime: DeliveryRuntime, request_id: str) -> DeliveryRequest:
        matches = tuple(
            request
            for outcome in runtime.contract.outcomes
            for request in runtime.show_binding(outcome.outcome_id).requests
            if request.request_id == request_id
        )
        if len(matches) != 1:
            message = f"Delivery request is absent or ambiguous: {request_id}"
            raise PortfolioApplicationError(message)
        return matches[0]

    @staticmethod
    def _commitments(runtime: DeliveryRuntime, commitment_ids: tuple[str, ...]) -> tuple[DeliveryCommitment, ...]:
        selected = set(commitment_ids)
        return tuple(item for item in runtime.contract.commitments if item.commitment_id in selected)

    @staticmethod
    def _fail(message: str, cause: Exception | None = None) -> Never:
        raise PortfolioApplicationError(message) from cause


__all__ = [
    "ChangeExternalHeadPromotionReceipt",
    "DeliveryAcceptanceReconciliationOutcome",
    "DeliveryAcceptanceReconciliationStatus",
    "DeliveryAcquisitionFailure",
    "DeliveryAcquisitionResult",
    "DeliveryActionBusyError",
    "DeliveryActionSelection",
    "DeliveryBuildContext",
    "DeliveryCapacityWaitingError",
    "DeliveryClaimRecoveryResult",
    "DeliveryClaimRecoveryStatus",
    "DeliveryFinalizationContext",
    "DeliveryIntegrationAttentionStatus",
    "DeliveryLaunchPackage",
    "DeliveryPlanContext",
    "DeliveryRolePolicy",
    "DeliveryRuntimeReconciliationError",
    "PortfolioApplication",
    "PortfolioApplicationConfig",
    "PortfolioApplicationDependencies",
    "PortfolioApplicationError",
    "PortfolioApplicationHooks",
]
