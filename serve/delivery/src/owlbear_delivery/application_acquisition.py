"""Work acquisition, continuation actions and candidate activation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from contextlib import ExitStack, contextmanager, suppress
from typing import TYPE_CHECKING

from owlbear_delivery.acceptance_criteria import DeliveryAcceptanceCriterion, acceptance_criteria
from owlbear_delivery.application_lifecycle import _ENGINE_DRAIN_MUTATIONS
from owlbear_delivery.application_models import (
    DeliveryAcquisitionFailure,
    DeliveryAcquisitionResult,
    DeliveryActionBusyError,
    DeliveryActionSelection,
    DeliveryBuildContext,
    DeliveryCapacityWaitingError,
    DeliveryClaimRecoveryResult,
    DeliveryClaimRecoveryStatus,
    DeliveryContinuationRequest,
    DeliveryContinuationResult,
    DeliveryEngineActionResult,
    DeliveryFinalizationLaunch,
    DeliveryLaunchPackage,
    DeliveryPlanContext,
    DeliveryRepairProposal,
    DeliveryRuntimeReconciliationError,
    ExecuteDeliveryChangeAction,
    PortfolioApplicationError,
    _Candidate,
    _PreEffectReadyObservationError,
    _PreparedSource,
)
from owlbear_delivery.application_support import (
    _checkpoint_error_detail,
    _checkpoint_retry_ready,
    _health_detail,
    _timestamp,
)
from owlbear_delivery.change_workspace import (
    BuilderHandoffSource,
    ChangeBuilderHandoff,
    ChangeContinuationAction,
    ChangeCoordination,
    ChangeFinalizationAttempt,
    ChangePauseRequestedError,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncStaleError,
    ChangeWriter,
    CoordinationConflictError,
    FinalizerAcquisition,
    PromoteExternalHead,
)
from owlbear_delivery.delivery_contract_discovery import (
    contract_fingerprint,
)
from owlbear_delivery.delivery_runtime import (
    ActivateDeliveryClaim,
    DeliveryAcceptanceWaitingError,
    DeliveryActionSelectionConflictError,
    DeliveryActiveClaim,
    DeliveryBuilderHandoffContext,
    DeliveryChangeStage,
    DeliveryCheckpointTriggerKind,
    DeliveryFinalizationReceipt,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    parse_delivery_frontier,
)
from owlbear_delivery.draft_pull_request import (
    MarkChangePullRequestReady,
    ObserveChangePublicationPullRequest,
    ReturnChangePullRequestToDraft,
)
from owlbear_delivery.evidence import evaluate_acceptance_evidence
from owlbear_delivery.finalization_reports import (
    FinalizationReportError,
    FinalizationReportStore,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RetryEpisodeKey,
    RetryFailureClass,
    RetryLedger,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    RetryReservation,
    RetryStopCode,
)
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.work_items import (
    DeliveryReadiness,
    DeliveryReadinessBasis,
    WorkItemActionKind,
    WorkItemCardView,
    WorkItemNextActor,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class _AcquisitionMixin:
    """Work acquisition, continuation actions and candidate activation."""

    def _recover_expired_claims(
        self,
    ) -> tuple[tuple[DeliveryClaimRecoveryResult, ...], tuple[DeliveryAcquisitionFailure, ...]]:
        cutoff = _timestamp(self._clock()) - self._claim_timeout
        recoveries: list[DeliveryClaimRecoveryResult] = []
        failures: list[DeliveryAcquisitionFailure] = []
        for change_id, runtime in sorted(self._runtimes.items()):
            try:
                active_claims = runtime.active_claims()
            except (OSError, RuntimeError, ValueError) as exc:
                self._runtime_reconciliation_errors.setdefault(
                    change_id,
                    _health_detail(
                        str(exc),
                        "Delivery claim state is unavailable and requires reconciliation.",
                    ),
                )
                continue
            for outcome_id, claim in active_claims:
                try:
                    if claim.continuation or _timestamp(claim.started_at) > cutoff:
                        continue
                    if claim.worker_role in {DeliveryWorkerRole.PLANNER, DeliveryWorkerRole.BUILDER}:
                        failures.append(
                            DeliveryAcquisitionFailure(
                                change_id=change_id,
                                outcome_id=outcome_id,
                                code=DeliveryWorkerExclusionRequiredError.code,
                                detail=str(DeliveryWorkerExclusionRequiredError()),
                                retry_condition=(
                                    "Automatic recovery is unavailable while host/worker evidence is missing. "
                                    "Resume awaits verified closure that excludes all descendants and tool jobs "
                                    "and records settlement."
                                ),
                            )
                        )
                        continue
                    recovered = self._recover_claim(
                        change_id,
                        outcome_id,
                        claim.attempt_id,
                        claim.claim_id,
                    )
                except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                    failures.append(
                        DeliveryAcquisitionFailure(
                            change_id=change_id,
                            outcome_id=outcome_id,
                            attempt_id=claim.attempt_id,
                            claim_id=claim.claim_id,
                            code=getattr(exc, "code", PortfolioApplicationError.code),
                            detail=str(exc) or "expired claim recovery failed",
                            retry_condition="Retry exact claim recovery after reconciling workspace custody.",
                        )
                    )
                else:
                    recoveries.append(recovered)
                    if recovered.status == DeliveryClaimRecoveryStatus.ATTENTION:
                        attention = recovered.attention
                        if attention is None:
                            self._fail("expired claim recovery returned incomplete attention")
                        failures.append(
                            DeliveryAcquisitionFailure(
                                change_id=change_id,
                                outcome_id=outcome_id,
                                attempt_id=claim.attempt_id,
                                claim_id=claim.claim_id,
                                code=PortfolioApplicationError.code,
                                detail=attention.reason,
                                retry_condition=attention.retry_condition,
                            )
                        )
        return tuple(recoveries), tuple(failures)

    def acquire_frontier_work(self) -> DeliveryAcquisitionResult:
        """Start at most one ready claim per available execution slot."""
        with self._coordinator.acquisition_lock():
            try:
                self._execution_occupancy()
            except DeliveryRuntimeReconciliationError as exc:
                return DeliveryAcquisitionResult(
                    launch_packages=(),
                    failures=(
                        DeliveryAcquisitionFailure(
                            change_id=exc.change_id or "portfolio",
                            outcome_id="OUT-000",
                            code=exc.code,
                            detail=str(exc),
                            retry_condition=(
                                "Restore readable custody before batch acquisition; preserve unknown writers."
                            ),
                        ),
                    ),
                )
            self._coordinator.recover_pending_transactions()
            self._reconcile_runtimes()
            pre_claim_snapshots = self._capture_portfolio_snapshots()
            stalled, stall_failures = self._settle_stalled_workers(
                tuple(sorted(self._runtimes)), checkpoint_locked=False
            )
            recoveries, recovery_failures = self._recover_expired_claims()
            failures = [*stall_failures, *recovery_failures]
            if stalled or recoveries or recovery_failures:
                self._reconcile_runtimes()
            pending_publication_failures = self._replay_pending_state_publications()
            failures.extend(pending_publication_failures)
            for paused_change_id in sorted(self._runtimes):
                self._try_convert_pause_request_if_requested(paused_change_id)
            occupied = self._execution_occupancy()
            available = max(self._execution_capacity - occupied, 0)
            integration_attention = self._integration_attention_statuses(pre_claim_snapshots)
            launches: list[DeliveryLaunchPackage] = []
            try:
                for candidate in self._candidates():
                    if available == 0:
                        break
                    source = self._prepare_source(
                        candidate,
                        allow_dirty=candidate.role is DeliveryWorkerRole.BUILDER,
                    )
                    if isinstance(source, DeliveryAcquisitionFailure):
                        failures.append(source)
                        continue
                    launch = self._activate_candidate(candidate, source, isolate_retry_accounting=True)
                    if isinstance(launch, DeliveryAcquisitionFailure):
                        failures.append(launch)
                        available = max(self._execution_capacity - self._execution_occupancy(), 0)
                        continue
                    available -= 1
                    launches.append(launch)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                failures.append(
                    DeliveryAcquisitionFailure(
                        change_id=getattr(exc, "change_id", None) or "portfolio",
                        outcome_id="OUT-000",
                        code=getattr(exc, "code", PortfolioApplicationError.code),
                        detail="Batch acquisition stopped because current custody could not be established.",
                        retry_condition="Preserve all existing claims and writers; diagnose custody before retry.",
                    )
                )
                return DeliveryAcquisitionResult(
                    launch_packages=tuple(launches),
                    integration_attention=integration_attention,
                    recoveries=recoveries,
                    failures=tuple(failures),
                    health_hint="Call delivery_health for current Delivery diagnostics.",
                )
            self._capture_portfolio_snapshots()
            return DeliveryAcquisitionResult(
                launch_packages=tuple(launches),
                integration_attention=integration_attention,
                recoveries=recoveries,
                failures=tuple(failures),
                health_hint=(
                    "Call delivery_health for current Delivery diagnostics."
                    if self._delivery_health_view().diagnostics
                    else None
                ),
            )

    def acquire_change_action(self, request: DeliveryContinuationRequest) -> DeliveryContinuationResult:
        """Continue one Change without recovering, dispatching, or claiming sibling work."""
        view = self.get_change(request.change_id)
        if view.kind == "unavailable":
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unavailable",
                reason_code=view.readiness.reason_code,
                readiness=view.readiness,
            )
        try:
            with (
                self._coordinator.acquisition_lock(),
                self._selected_action_checkpoint_lock(request.change_id),
            ):
                return self._acquire_change_action_locked(request, view.readiness)
        except DeliveryRuntimeReconciliationError as exc:
            action = view.continuation_action if exc.change_id == request.change_id else None
            reason = "engine-action-blocked" if action is not None else "execution-occupancy-unavailable"
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unavailable",
                reason_code=reason,
                readiness=self._with_engine_action_prompt(
                    request.change_id,
                    view.readiness.model_copy(
                        update={
                            "status": "unavailable",
                            "reason_code": reason,
                            "executable": False,
                            "action": None,
                        }
                    ),
                ),
                failure=DeliveryAcquisitionFailure(
                    change_id=request.change_id,
                    outcome_id="OUT-000",
                    attempt_id=action.operation_id if action is not None else None,
                    code=exc.code,
                    detail=str(exc),
                    retry_condition=(
                        "The original intent/result journal cannot be verified. The Delivery engine owner must "
                        "establish matching authoritative records and required custody before resume; do not "
                        "reconstruct or retry effects."
                        if action is not None
                        else "Restore readable custody through maintenance diagnosis; do not release unknown writers."
                    ),
                ),
            )
        except DeliveryActionBusyError, DeliveryWorkerExclusionRequiredError:
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="busy",
                reason_code="operation-in-progress",
                readiness=self.get_change(request.change_id).readiness,
            )

    def _acquire_change_action_locked(
        self, request: DeliveryContinuationRequest, observed: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        self._coordinator.recover_pending_transactions()
        runtime = self._runtimes.get(request.change_id)
        if runtime is not None:
            try:
                self._reconcile_retry_results(runtime)
            except FinalizationReportError:
                unavailable = observed.model_copy(
                    update={
                        "status": "unavailable",
                        "reason_code": "report-store-unavailable",
                        "checks_state": "unknown",
                        "executable": False,
                        "action": None,
                    }
                )
                return DeliveryContinuationResult(
                    change_id=request.change_id,
                    kind="unavailable",
                    reason_code="report-store-unavailable",
                    readiness=unavailable,
                )
            self._settle_stalled_workers((request.change_id,), checkpoint_locked=True)
            self._prepare_target_sync(request.change_id, runtime)
        replay = self._replay_continuation_action(request, observed)
        if replay is not None:
            return replay
        runtime = self._runtime(request.change_id, for_mutation=True, allow_finalizer=True)
        self._try_convert_pause_request(request.change_id, runtime)
        snapshot = self._delivery_snapshot(runtime, observe_publication=False)
        cards = self._read_projector(snapshot).group_view().items
        card = self._selected_change_card(snapshot, cards)
        readiness = card.readiness
        if readiness is None:
            self._fail("continuation readiness was not captured")

        stop = self._continuation_stop(request, runtime, readiness, repair=self._repair_proposal(snapshot))
        if stop is not None:
            return stop
        if readiness.executable and readiness.operation in {
            WorkItemActionKind.RECONCILE_CHECKPOINT,
            WorkItemActionKind.SYNC_TARGET,
            WorkItemActionKind.MARK_READY,
            WorkItemActionKind.OBSERVE_ACCEPTANCE,
        }:
            return self._acquire_engine_action(request, runtime, readiness)
        return self._acquire_continuation_worker(request, cards, readiness)

    def _acquire_continuation_worker(
        self, request: DeliveryContinuationRequest, cards: tuple[WorkItemCardView, ...], readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        candidate = self._continuation_candidate(request.change_id, cards)
        finalizer = readiness.executable and readiness.operation is WorkItemActionKind.FINALIZE
        role = "finalizer" if finalizer else candidate.role.value if candidate else None
        if role is None:
            kind = "human" if readiness.next_actor is WorkItemNextActor.YOU else "unsupported"
            if readiness.status in {"waiting", "running"}:
                kind = "waiting"
            return DeliveryContinuationResult(
                change_id=request.change_id, kind=kind, reason_code=readiness.reason_code, readiness=readiness
            )
        reason = None
        if role not in request.capabilities:
            reason = "host-capability-unavailable"
        elif self._execution_occupancy() >= self._execution_capacity:
            reason = "execution-capacity"
        if reason is not None:
            return DeliveryContinuationResult(
                change_id=request.change_id, kind="waiting", reason_code=reason, readiness=readiness
            )
        if finalizer:
            return self._launch_continuation_finalizer(request, readiness)
        return self._launch_continuation_candidate(request, readiness, candidate)

    def _continuation_candidate(self, change_id: str, cards: tuple[WorkItemCardView, ...]) -> _Candidate | None:
        candidate = next(iter(self._candidates(change_id)), None)
        if candidate is None:
            return None
        selected = next(item for item in cards if item.work_item_id == candidate.binding.outcome_id)
        return candidate if selected.readiness is not None and selected.readiness.executable else None

    @staticmethod
    def _continuation_operation_id(request: DeliveryContinuationRequest) -> str:
        payload = json.dumps(
            {"change_id": request.change_id, "basis": request.expected_basis.model_dump(mode="json")},
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"continue-{hashlib.sha256(payload.encode()).hexdigest()}"

    @staticmethod
    def _chat_reason(result: DeliveryEngineActionResult, readiness: DeliveryReadiness) -> str:
        """L2 (D5): a waiting acceptance result shows current readiness, not its persisted label."""
        return readiness.reason_code if result.kind == "waiting" else result.reason_code

    @staticmethod
    def _engine_action_matches_readiness(
        action: ChangeContinuationAction,
        basis: DeliveryReadinessBasis,
        readiness: DeliveryReadiness,
    ) -> bool:
        return (
            readiness.operation is not None
            and action.kind == readiness.operation.value
            and action.contract_digest == basis.contract_digest
            and action.frontier_digest == basis.frontier_digest
            and action.exact_head == basis.candidate_head
            and action.target_head == basis.target_head
        )

    def _replay_retained_continuation_action(
        self,
        request: DeliveryContinuationRequest,
        readiness: DeliveryReadiness,
        retained: ChangeContinuationAction,
        requested_operation_id: str,
    ) -> DeliveryContinuationResult | None:
        retained_request = ExecuteDeliveryChangeAction(
            change_id=request.change_id,
            operation_id=retained.operation_id,
        )
        original = self._read_engine_intent(retained_request)
        if original != retained.model_copy(update={"finished_at": None}):
            raise DeliveryRuntimeReconciliationError(request.change_id, "retained continuation intent differs")
        if retained.finished_at is None:
            if self._read_engine_result(retained_request) is not None:
                return None
            if not self._engine_action_matches_readiness(original, request.expected_basis, readiness):
                return None
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="acquired" if "engine" in request.capabilities else "waiting",
                reason_code=(
                    "engine-action-pending" if "engine" in request.capabilities else "host-capability-unavailable"
                ),
                readiness=readiness,
                engine_action=original if "engine" in request.capabilities else None,
            )
        result = self._read_engine_result(retained_request)
        if result is None:
            raise DeliveryRuntimeReconciliationError(request.change_id, "finished continuation result is missing")
        if result.kind == "blocked":
            if result.failure is None or not result.failure.pre_effect_retryable:
                raise DeliveryRuntimeReconciliationError(request.change_id, "finished continuation result is blocked")
            self._record_engine_attempt_result(original, result)
            return None
        if requested_operation_id != retained.operation_id or not self._engine_action_matches_readiness(
            original, request.expected_basis, readiness
        ):
            return None
        self._record_engine_attempt_result(original, result)
        kinds = {"completed": "reconciled", "waiting": "human", "stale": "stale"}
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind=kinds[result.kind],
            reason_code=self._chat_reason(result, readiness),
            readiness=readiness,
            engine_result=result,
            failure=result.failure,
        )

    def _replay_continuation_action(
        self, request: DeliveryContinuationRequest, readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult | None:
        operation_id = self._continuation_operation_id(request)
        path = self._coordinator.continuation_record_path(request.change_id, operation_id)
        execution = ExecuteDeliveryChangeAction(change_id=request.change_id, operation_id=operation_id)
        action = self._read_engine_intent(execution) if path.exists() else None
        retained = self._coordinator.show(request.change_id).continuation_action
        if retained is not None:
            replay = self._replay_retained_continuation_action(request, readiness, retained, operation_id)
            if replay is not None:
                return replay
            original = self._read_engine_intent(
                ExecuteDeliveryChangeAction(change_id=request.change_id, operation_id=retained.operation_id)
            )
        if action is None and retained is not None and retained.finished_at is None:
            action = original
        if action is None:
            return None
        result = self._read_engine_result(
            ExecuteDeliveryChangeAction(change_id=request.change_id, operation_id=action.operation_id)
        )
        if result is not None:
            self._record_engine_attempt_result(action, result)
            kinds = {"completed": "reconciled", "waiting": "human", "stale": "stale", "blocked": "unavailable"}
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind=kinds[result.kind],
                reason_code=self._chat_reason(result, readiness),
                readiness=readiness,
                engine_result=result,
                failure=result.failure,
            )
        if retained != action:
            raise DeliveryRuntimeReconciliationError(request.change_id, "original continuation result is missing")
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind="acquired" if "engine" in request.capabilities else "waiting",
            reason_code="engine-action-pending" if "engine" in request.capabilities else "host-capability-unavailable",
            readiness=readiness,
            engine_action=action if "engine" in request.capabilities else None,
        )

    def _acquire_engine_action(
        self, request: DeliveryContinuationRequest, runtime: DeliveryRuntime, readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        reason = None
        pending = runtime.checkpoint_publication_state().pending_checkpoint
        if "engine" not in request.capabilities:
            reason = "host-capability-unavailable"
        elif (
            self._draft_pull_request_publisher is None
            or readiness.basis.candidate_head is None
            or readiness.basis.target_head is None
            or (
                readiness.operation in {WorkItemActionKind.RECONCILE_CHECKPOINT, WorkItemActionKind.SYNC_TARGET}
                and self._change_branch_publisher is None
            )
        ):
            reason = "engine-owner-unavailable"
        elif (
            readiness.operation is WorkItemActionKind.RECONCILE_CHECKPOINT
            and pending is not None
            and (pending.head is None or not _checkpoint_retry_ready(pending, _timestamp(self._clock())))
        ):
            reason = "checkpoint-pending"
        elif self._execution_occupancy() >= self._execution_capacity:
            reason = "execution-capacity"
        if reason is not None:
            return DeliveryContinuationResult(
                change_id=request.change_id, kind="waiting", reason_code=reason, readiness=readiness
            )
        operation_id = self._continuation_operation_id(request)
        finalization = runtime.finalization()
        operation_id = self._retry_suffixed_engine_operation_id(runtime, readiness, operation_id, finalization)
        action = ChangeContinuationAction(
            operation_id=operation_id,
            change_id=request.change_id,
            kind=readiness.operation.value,
            contract_digest=readiness.basis.contract_digest,
            frontier_digest=readiness.basis.frontier_digest,
            exact_head=readiness.basis.candidate_head,
            target_head=readiness.basis.target_head,
            finalization_id=finalization.finalization_id if finalization else None,
            host_id=request.host_id,
            session_id=request.session_id,
            acquired_at=self._clock(),
        )
        attention_preflight = self._preflight_settled_attention_sync_acquisition(request, runtime, readiness, action)
        if attention_preflight is not None:
            return attention_preflight
        reservation = self._reserve_engine_attempt(runtime, readiness, operation_id)
        if reservation is not None and not reservation.allowed:
            retry_status = "waiting" if reservation.reason_code in {"retry-backoff", "acceptance-wait"} else "blocked"
            retry_readiness = self._with_engine_action_prompt(
                request.change_id,
                readiness.model_copy(
                    update={
                        "status": retry_status,
                        "reason_code": (
                            reservation.reason_code
                            if reservation.reason_code
                            in {"retry-backoff", "retry-exhausted", "acceptance-wait", "retry-containment"}
                            else "retry-exhausted"
                        ),
                        "executable": False,
                        "action": None,
                        "next_actor": (
                            WorkItemNextActor.NONE
                            if reservation.reason_code in {"retry-exhausted", "retry-containment"}
                            else readiness.next_actor
                        ),
                        "attempts": reservation.attempts,
                        "next_eligible_at": reservation.next_eligible_at,
                        "stop_reason": reservation.stop_code.value if reservation.stop_code is not None else None,
                    }
                ),
            )
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="waiting" if retry_readiness.status == "waiting" else "unsupported",
                reason_code=retry_readiness.reason_code,
                readiness=retry_readiness,
            )
        try:
            self._register_recovery_invocation(
                runtime, action.operation_id, action.operation_id, action.kind, action.exact_head
            )
            self._coordinator.acquire_continuation_action(action)
        except OSError, RuntimeError, subprocess.SubprocessError, ValueError:
            self._release_unpublished_engine_action(runtime, action)
            raise
        return DeliveryContinuationResult(
            change_id=request.change_id, kind="acquired", reason_code="ready", readiness=readiness, engine_action=action
        )

    def _retry_suffixed_engine_operation_id(
        self,
        runtime: DeliveryRuntime,
        readiness: DeliveryReadiness,
        operation_id: str,
        finalization: DeliveryFinalizationReceipt | None,
    ) -> str:
        if readiness.operation is None or readiness.basis.candidate_head is None:
            return operation_id
        key = RetryEpisodeKey.engine(
            runtime.contract.change_id,
            readiness.operation.value,
            readiness.basis.candidate_head,
            readiness.basis.target_head,
            finalization.finalization_id if finalization is not None else None,
        )
        episode = runtime.retry_ledger(clock=self._clock).episode(key)
        if episode is None or not episode.total_attempts:
            return operation_id
        seed = f"{operation_id}:{episode.total_attempts + 1}"
        return f"continue-{hashlib.sha256(seed.encode()).hexdigest()}"

    def _preflight_settled_attention_sync_acquisition(
        self,
        request: DeliveryContinuationRequest,
        runtime: DeliveryRuntime,
        readiness: DeliveryReadiness,
        action: ChangeContinuationAction,
    ) -> DeliveryContinuationResult | None:
        if action.kind != "sync-target" or not self._workspace_manager.show(request.change_id).finalization_attention:
            return None
        preflight = self._engine_action_preflight(action, runtime)
        if preflight is None:
            return None
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind="stale" if preflight.kind == "stale" else "unavailable",
            reason_code=preflight.reason_code,
            readiness=readiness,
            engine_result=preflight,
            failure=preflight.failure,
        )

    def _reserve_engine_attempt(
        self,
        runtime: DeliveryRuntime,
        readiness: DeliveryReadiness,
        attempt_id: str,
    ) -> RetryReservation | None:
        """Reserve a semantic engine attempt before continuation custody is published."""
        if readiness.operation is None or readiness.basis.candidate_head is None:
            return None
        finalization = runtime.finalization()
        key = RetryEpisodeKey.engine(
            runtime.contract.change_id,
            readiness.operation.value,
            readiness.basis.candidate_head,
            readiness.basis.target_head,
            finalization.finalization_id if finalization is not None else None,
        )
        failure_class = (
            RetryFailureClass.ACCEPTANCE
            if readiness.operation is WorkItemActionKind.OBSERVE_ACCEPTANCE
            else RetryFailureClass.TRANSIENT
            if readiness.operation in {WorkItemActionKind.MARK_READY, WorkItemActionKind.SYNC_TARGET}
            else RetryFailureClass.MECHANICAL
        )
        ledger = runtime.retry_ledger(clock=self._clock)
        return ledger.reserve(
            key,
            failure_class=failure_class,
            now=self._clock(),
            attempt_id=attempt_id,
            automatic=True,
            operation_alias=attempt_id,
        )

    def _record_engine_attempt_result(
        self,
        action: ChangeContinuationAction,
        result: DeliveryEngineActionResult,
    ) -> None:
        """Account for a known engine result; unknown effects remain outside retry policy."""
        key = RetryEpisodeKey.engine(
            action.change_id,
            action.kind,
            action.exact_head,
            action.target_head,
            action.finalization_id,
        )
        ledger = RetryLedger(self._target_root, action.change_id, clock=self._clock)
        episode = ledger.episode(key)
        if episode is None:
            return
        reservation = next((item for item in episode.attempt_ids if item == action.operation_id), None)
        if reservation is None:
            return
        if result.kind == "completed":
            ledger.record_accepted_progress(reservation, now=self._clock())
        elif result.kind == "waiting" or (
            result.kind == "blocked" and result.reason_code != "engine-action-interrupted"
        ):
            ledger.record_failure(
                reservation,
                failure_code=result.reason_code,
                failure_detail=(result.failure.detail if result.failure is not None else None),
                now=self._clock(),
            )
        elif result.kind == "stale" and not self._coordinator.continuation_start_recorded(action):
            ledger.record_failure(
                reservation,
                failure_code=result.reason_code,
                failure_detail="Engine preflight rejected stale readiness before owner dispatch.",
                now=self._clock(),
            )

    def _read_engine_intent(self, request: ExecuteDeliveryChangeAction) -> ChangeContinuationAction:
        path = self._coordinator.continuation_record_path(request.change_id, request.operation_id)
        try:
            action = ChangeContinuationAction.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(
                request.change_id, "original continuation intent is unavailable"
            ) from exc
        if (
            action.change_id != request.change_id
            or action.operation_id != request.operation_id
            or action.finished_at is not None
        ):
            raise DeliveryRuntimeReconciliationError(request.change_id, "original continuation intent identity differs")
        return action

    def _read_engine_result(self, request: ExecuteDeliveryChangeAction) -> DeliveryEngineActionResult | None:
        path = self._coordinator.continuation_record_path(request.change_id, request.operation_id, result=True)
        if not path.exists():
            return None
        try:
            result = DeliveryEngineActionResult.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(request.change_id, "continuation result is unreadable") from exc
        if result.action.operation_id != request.operation_id or result.action.change_id != request.change_id:
            raise DeliveryRuntimeReconciliationError(request.change_id, "continuation result identity differs")
        if self._read_engine_intent(request) != result.action:
            raise DeliveryRuntimeReconciliationError(request.change_id, "continuation result lacks its original intent")
        return result

    def _retained_target_sync_conflict(self, change_id: str) -> ChangeContinuationAction | None:
        """Return the unfinished engine sync whose exact recorded result is a preserved target conflict."""
        try:
            action = self._coordinator.show(change_id).continuation_action
            if action is None or action.finished_at is not None or action.kind != "sync-target":
                return None
            result = self._read_engine_result(
                ExecuteDeliveryChangeAction(change_id=change_id, operation_id=action.operation_id)
            )
        except OSError, RuntimeError, ValueError:
            return None
        if (
            result is None
            or result.kind != "blocked"
            or result.failure is None
            or result.failure.code != ChangeTargetSyncConflictError.code
        ):
            return None
        return action

    def execute_change_action(self, request: ExecuteDeliveryChangeAction) -> DeliveryEngineActionResult:
        """Execute the fixed retained owner once, or return its exact durable result."""
        with self._selected_action_checkpoint_lock(request.change_id):
            self._coordinator.recover_pending_transactions()
            existing = self._read_engine_result(request)
            if existing is not None:
                self._record_engine_attempt_result(existing.action, existing)
                return existing
            action = self._read_engine_intent(request)
            with self._coordinator.continuation_execution(action):
                result = self._execute_engine_action(action)
                self._coordinator.finish_continuation_action(
                    action,
                    (result.model_dump_json() + "\n").encode(),
                    self._clock(),
                    release=result.kind != "blocked"
                    or (result.failure is not None and result.failure.pre_effect_retryable),
                )
                self._record_engine_attempt_result(action, result)
            self._try_convert_pause_request(request.change_id)
            return result

    def _execute_engine_action(self, action: ChangeContinuationAction) -> DeliveryEngineActionResult:
        try:
            if self._coordinator.continuation_action_started(action):
                return self._engine_action_failure(
                    action, "engine-action-interrupted", "Original owner result is unknown."
                )
            runtime = self._runtime(action.change_id, for_mutation=True)
            preflight = self._engine_action_preflight(action, runtime)
            if preflight is not None:
                return preflight
            result = self._start_engine_owner(action)
        except ChangeTargetSyncStaleError:
            return DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
        except DeliveryAcceptanceWaitingError:
            return DeliveryEngineActionResult(action=action, kind="waiting", reason_code="merge-approval-required")
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            pre_effect_retryable = (
                action.kind == WorkItemActionKind.MARK_READY.value
                and isinstance(exc, _PreEffectReadyObservationError)
                and exc.retry_safe
            )
            return self._engine_action_failure(
                action,
                "engine-action-failed",
                str(exc),
                getattr(exc, "code", None),
                pre_effect_retryable=pre_effect_retryable,
            )
        else:
            return result

    def _start_engine_owner(self, action: ChangeContinuationAction) -> DeliveryEngineActionResult:
        """K3 start: a Pause-won start is stale with no marker or effect; a won start drains under its token."""
        try:
            started = self._coordinator.start_continuation_action(action)
        except ChangePauseRequestedError:
            return DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
        if not started:
            return self._engine_action_failure(action, "engine-action-interrupted", "Original owner result is unknown.")
        with self._owner_drain_authority(
            action.change_id,
            f"engine:{action.operation_id}",
            *_ENGINE_DRAIN_MUTATIONS[action.kind],
            publishes_checkpoint=action.kind in {"reconcile-checkpoint", "sync-target"},
        ):
            return self._invoke_engine_owner(action)

    def _settled_finalizer_sync_preflight(
        self,
        action: ChangeContinuationAction,
        runtime: DeliveryRuntime,
        workspace: tuple[ChangeCoordination, str, str, tuple[str, ...], str | None],
    ) -> bool | None:
        coordination = workspace[0]
        attention = coordination.finalization_attention
        attempt = coordination.finalization_attempt
        if (
            attention is None
            or action.kind != "sync-target"
            or action.finalization_id is not None
            or attempt is None
            or attempt.finished_at is None
            or action.exact_head != attempt.exact_head
            or action.target_head == attempt.target_head
        ):
            return None
        if action.contract_digest != attempt.contract_digest or action.frontier_digest != attempt.frontier_digest:
            return False
        try:
            reports = FinalizationReportStore(self._target_root, action.change_id).read()
            report = next(
                (item for item in reports.reports if item.request.attempt_key == attempt.writer.attempt_id), None
            )
            receipt = self._read_finalizer_settlement_receipt(action.change_id, attempt.writer.attempt_id)
            retry_attempt = runtime.retry_ledger(clock=self._clock).episode_for_attempt(attempt.writer.attempt_id)
        except FinalizationReportError, OSError, RuntimeError, ValueError:
            return False
        if report is None or receipt is None or retry_attempt is None:
            return False
        snapshot = self._delivery_snapshot(runtime, observe_publication=False)
        basis = DeliveryReadinessBasis(
            contract_digest=action.contract_digest,
            frontier_digest=action.frontier_digest,
            target_head=action.target_head,
        )
        reason = self._finalizer_attention_retry_reason(
            snapshot,
            basis,
            workspace,
            reports,
            receipt,
        )
        return reason == "settled-attention-target-drift"

    def _engine_action_preflight(
        self, action: ChangeContinuationAction, runtime: DeliveryRuntime
    ) -> DeliveryEngineActionResult | None:
        if runtime.active_claims() or runtime.integration_repair_claim() is not None:
            return self._engine_action_failure(action, "engine-action-failed", "An existing claim retains custody.")
        coordination, head, fingerprint, paths, reason = self._workspace_manager.capture_finalization_workspace(
            action.change_id,
            tuple(
                result.completed_commit
                for binding in parse_delivery_frontier(runtime.frontier_bytes())[0].bindings
                for result in binding.results
            ),
        )
        if reason not in {None, "workspace-dirty", "active-custody"} or (
            reason == "active-custody"
            and (coordination.finalization_attention is None or coordination.publication_lease is not None)
        ):
            return self._engine_action_failure(action, "engine-action-failed", reason)
        if (
            contract_fingerprint(runtime.contract) != action.contract_digest
            or hashlib.sha256(runtime.frontier_bytes()).hexdigest() != action.frontier_digest
            or head != action.exact_head
            # A sync target may be the provider head; the exact fetch in the sync owner verifies it (U3(a)).
            or (action.kind != "sync-target" and self._workspace_manager.observed_target_head() != action.target_head)
            or reason == "workspace-dirty"
        ):
            return DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
        attention_sync = self._settled_finalizer_sync_preflight(
            action,
            runtime,
            (coordination, head, fingerprint, paths, reason),
        )
        if attention_sync is False:
            return DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
        if reason == "active-custody" and attention_sync is not True:
            return self._engine_action_failure(action, "engine-action-failed", reason)
        return None

    @staticmethod
    def _engine_action_failure(
        action: ChangeContinuationAction,
        reason: str,
        detail: str,
        code: str | None = None,
        *,
        pre_effect_retryable: bool = False,
    ) -> DeliveryEngineActionResult:
        retry_condition = (
            "Preserve exact operation custody and owner journals. The authoritative result for this operation is "
            "unavailable; automatic recovery is unavailable while evidence is missing. Resume awaits verified "
            "host/worker closure and settlement; do not release custody, infer worker termination, or start a "
            "replacement."
            if reason == "engine-action-interrupted"
            else "The required-check read failed before the mark-ready owner write. The exact finalized head remains "
            "unchanged; the retry ledger permits only bounded attempts after backoff."
            if pre_effect_retryable
            else "Preserve exact operation custody and owner journals. Automatic retry is unavailable for this "
            "recorded failure; the responsible owner must resolve the reported condition before resume. Do not "
            "release custody, infer worker termination, or start a replacement."
        )
        return DeliveryEngineActionResult(
            action=action,
            kind="blocked",
            reason_code=reason,
            failure=DeliveryAcquisitionFailure(
                change_id=action.change_id,
                outcome_id="OUT-000",
                attempt_id=action.operation_id,
                code=code or "ERR_DELIVERY_ENGINE_ACTION_BLOCKED",
                detail=_checkpoint_error_detail(detail, "Engine operation did not complete."),
                retry_condition=retry_condition,
                pre_effect_retryable=pre_effect_retryable,
            ),
        )

    def _invoke_engine_owner(self, action: ChangeContinuationAction) -> DeliveryEngineActionResult:
        values = {}
        if action.kind == "reconcile-checkpoint":
            checkpoint = self.reconcile_change_checkpoint(action.change_id)
            snapshot = self._coordinator.show(action.change_id).design_package_snapshot
            if snapshot is not None and snapshot.previous_head == action.exact_head:
                values["checkpoint_snapshot"] = snapshot
            if not checkpoint.reconciled:
                return DeliveryEngineActionResult(
                    action=action,
                    kind="blocked",
                    reason_code="engine-action-incomplete",
                    checkpoint=checkpoint,
                    **values,
                )
            values["checkpoint"] = checkpoint
        elif action.kind == "sync-target":
            values["target_sync"] = self.sync_change_with_target(
                action.change_id, action.target_head, action.operation_id
            )
        elif action.kind == "mark-ready":
            values["ready"] = self.mark_change_ready(
                action.change_id,
                MarkChangePullRequestReady(
                    change_id=action.change_id,
                    operation_id=action.operation_id,
                    finalization_id=action.finalization_id,
                    exact_head=action.exact_head,
                ),
            )
        else:
            values["acceptance"] = self._observe_acceptance_once(
                action.change_id, self._runtime(action.change_id, for_mutation=True), attempt_id=action.operation_id
            )
        return DeliveryEngineActionResult(
            action=action, kind="completed", reason_code="engine-action-completed", **values
        )

    @contextmanager
    def _engine_checkpoint_lock(self, change_id: str) -> Iterator[None]:
        if self._coordinator.executing_continuation(change_id):
            yield
        else:
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                yield

    def _continuation_stop(
        self,
        request: DeliveryContinuationRequest,
        runtime: DeliveryRuntime,
        readiness: DeliveryReadiness,
        *,
        repair: DeliveryRepairProposal | None,
    ) -> DeliveryContinuationResult | None:
        failure = None
        coordination = self._workspace_manager.show(request.change_id)
        if coordination.pause_request is not None and readiness.status != "unavailable":
            # A Pause request refuses new work; the started owner drains and the request converts.
            kind, reason = "waiting", "change-paused"
        elif readiness.status == "unavailable" or readiness.reason_code in {
            "finalization-failed",
            "claim-custody-unreconciled",
        }:
            kind, reason = "unavailable", readiness.reason_code
        elif (
            runtime.active_claims()
            or runtime.integration_repair_claim()
            or self._writer_occupies_execution_slot(coordination, runtime)
        ):
            kind, reason = ("unsupported", "repair-required") if repair is not None else ("busy", "active-custody")
        elif coordination.publication_lease is not None:
            kind, reason = "unsupported", "publication-reconciliation-required"
        elif readiness.basis != request.expected_basis:
            kind, reason = "stale", "readiness-changed"
        elif runtime.change_stage() in {DeliveryChangeStage.COMPLETED, DeliveryChangeStage.ABANDONED}:
            kind, reason = "terminal", "change-terminal"
        elif runtime.change_stage() is DeliveryChangeStage.DEFERRED:
            kind, reason = "waiting", "change-paused"
        elif runtime.pending_state_publication() is not None:
            failures = self._replay_pending_state_publications(request.change_id)
            kind = "unavailable" if failures else "reconciled"
            failure = failures[0] if failures else None
            reason = "state-publication-failed" if failure else "state-publication-reconciled"
        elif readiness.reason_code == "review-repair" or readiness.operation in {
            WorkItemActionKind.RECOVER_CLAIM,
            WorkItemActionKind.RESOLVE_ATTENTION,
        }:
            kind, reason = "unsupported", "repair-required"
        else:
            return None
        return DeliveryContinuationResult(
            change_id=request.change_id, kind=kind, reason_code=reason, readiness=readiness, failure=failure
        )

    def _launch_continuation_finalizer(
        self, request: DeliveryContinuationRequest, readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        context = self.show_finalization_context(request.change_id)
        if context.readiness.basis != readiness.basis or not context.ready_for_finalization:
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="stale",
                reason_code="readiness-changed",
                readiness=context.readiness,
            )
        runtime = self._runtime(request.change_id)
        finalizer_attempt_id = self._identity_factory()
        retry_ledger = runtime.retry_ledger(clock=self._clock)
        coordination = self._workspace_manager.show(request.change_id)
        finalization = runtime.finalization()
        invalidation = runtime.finalization_invalidation()
        finalization_id, resume_attempt_id, retry_key = self._derive_finalization_retry_identity(
            request.change_id,
            finalization=finalization,
            invalidation=invalidation,
            coordination=coordination,
            retry_ledger=retry_ledger,
        )
        key = retry_key or RetryEpisodeKey.engine(
            request.change_id,
            WorkItemActionKind.FINALIZE.value,
            context.change_head,
            self._workspace_manager.observed_target_head(),
            finalization_id,
        )
        reservation = runtime.retry_ledger(clock=self._clock).reserve(
            key,
            failure_class=RetryFailureClass.MECHANICAL,
            now=self._clock(),
            attempt_id=finalizer_attempt_id,
            automatic=True,
            operation_alias=finalizer_attempt_id,
            resume_attempt_id=resume_attempt_id,
        )
        if not reservation.allowed:
            retry_status = "waiting" if reservation.reason_code in {"retry-backoff", "acceptance-wait"} else "blocked"
            retry_reason = (
                reservation.reason_code
                if reservation.reason_code
                in {"retry-backoff", "retry-exhausted", "acceptance-wait", "retry-containment"}
                else "retry-exhausted"
            )
            blocked = self._with_engine_action_prompt(
                request.change_id,
                readiness.model_copy(
                    update={
                        "status": retry_status,
                        "reason_code": retry_reason,
                        "executable": False,
                        "action": None,
                        "next_actor": (
                            WorkItemNextActor.NONE
                            if retry_reason in {"retry-exhausted", "retry-containment"}
                            else readiness.next_actor
                        ),
                        "attempts": reservation.attempts,
                        "next_eligible_at": reservation.next_eligible_at,
                        "stop_reason": reservation.stop_code.value if reservation.stop_code is not None else None,
                    }
                ),
            )
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unsupported",
                reason_code=blocked.reason_code,
                readiness=blocked,
            )
        attempt = ChangeFinalizationAttempt(
            writer=ChangeWriter(
                attempt_id=finalizer_attempt_id,
                claim_id=self._identity_factory(),
                actor_id=request.host_id,
                process_id=request.session_id,
                claimed_at=self._clock(),
                job_id=1,
                kind="finalize",
            ),
            contract_digest=readiness.basis.contract_digest,
            frontier_digest=readiness.basis.frontier_digest,
            exact_head=context.change_head,
            target_head=self._workspace_manager.observed_target_head(),
        )
        try:

            def register_invocation() -> None:
                self._register_recovery_invocation(
                    runtime,
                    attempt.writer.claim_id,
                    attempt.writer.attempt_id,
                    "finalizer",
                    attempt.exact_head,
                )
                self._publish_issuer(
                    request.change_id,
                    None,
                    attempt.writer.attempt_id,
                    attempt.writer.claim_id,
                    "finalizer",
                    attempt.writer.claimed_at,
                )

            self._workspace_manager.acquire(
                request.change_id,
                attempt.writer,
                finalizer=FinalizerAcquisition(
                    attempt=attempt,
                    expected_attention=coordination.finalization_attention,
                    expected_workspace_fingerprint=readiness.basis.workspace_fingerprint,
                    promoted_commits=tuple(
                        result.completed_commit for binding in runtime.bindings() for result in binding.results
                    ),
                    before_acquire=register_invocation,
                ),
            )
        except CoordinationConflictError:
            self._release_unpublished_finalizer(
                runtime,
                attempt,
                expected_finalization_attention=coordination.finalization_attention,
            )
            current = self.get_change(request.change_id).readiness
            if current.reason_code == "active-custody":
                kind, reason = "busy", "active-custody"
            elif current.reason_code in {
                "finalization-failed",
                "report-store-unavailable",
                "workspace-dirty",
                "workspace-inspection-failed",
                "workspace-preflight-failed",
            }:
                kind, reason = "unavailable", current.reason_code
            elif current.basis != request.expected_basis:
                kind, reason = "stale", "readiness-changed"
            else:
                kind, reason = "unavailable", "workspace-preflight-failed"
                current = current.model_copy(update={"status": "unavailable", "executable": False, "action": None})
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind=kind,
                reason_code=reason,
                readiness=current,
            )
        except OSError, RuntimeError, subprocess.SubprocessError, ValueError:
            self._release_unpublished_finalizer(
                runtime,
                attempt,
                expected_finalization_attention=coordination.finalization_attention,
            )
            raise
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind="acquired",
            reason_code="ready",
            readiness=readiness,
            finalization=DeliveryFinalizationLaunch(attempt=attempt, context=context),
        )

    def _launch_continuation_candidate(
        self, request: DeliveryContinuationRequest, readiness: DeliveryReadiness, candidate: _Candidate
    ) -> DeliveryContinuationResult:
        source = self._prepare_source(
            candidate,
            allow_dirty=candidate.role is DeliveryWorkerRole.BUILDER,
        )
        if isinstance(source, DeliveryAcquisitionFailure):
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unavailable",
                reason_code="source-unavailable",
                readiness=readiness,
                failure=source,
            )
        if (
            source.source_head != request.expected_basis.source_head
            and candidate.binding.builder_handoff_context is None
        ):
            return DeliveryContinuationResult(
                change_id=request.change_id, kind="stale", reason_code="source-head-changed", readiness=readiness
            )
        launch = self._activate_candidate(
            candidate,
            source,
            expected_frontier_digest=request.expected_basis.frontier_digest,
            host_identity=(request.host_id, request.session_id),
        )
        if isinstance(launch, DeliveryAcquisitionFailure):
            return self._continuation_launch_failure(candidate, readiness, launch)
        return DeliveryContinuationResult(
            change_id=request.change_id, kind="acquired", reason_code="ready", readiness=readiness, launch=launch
        )

    def _continuation_launch_failure(
        self, candidate: _Candidate, readiness: DeliveryReadiness, failure: DeliveryAcquisitionFailure
    ) -> DeliveryContinuationResult:
        try:
            snapshot = self._delivery_snapshot(candidate.runtime)
            cards = self._read_projector(snapshot).group_view().items
            current = self._selected_change_card(snapshot, cards).readiness
        except OSError, RuntimeError, ValueError:
            current = readiness
        if failure.code in {"ERR_DELIVERY_RETRY_EXHAUSTED", "ERR_DELIVERY_RETRY_BACKOFF"} and current.reason_code in {
            "retry-backoff",
            "retry-exhausted",
            "retry-containment",
        }:
            return DeliveryContinuationResult(
                change_id=candidate.change_id,
                kind="waiting" if current.status == "waiting" else "unsupported",
                reason_code=current.reason_code,
                readiness=current,
            )
        return DeliveryContinuationResult(
            change_id=candidate.change_id,
            kind="unavailable",
            reason_code="claim-activation-failed",
            readiness=self._with_engine_action_prompt(
                candidate.change_id,
                current.model_copy(
                    update={
                        "status": "blocked",
                        "reason_code": "claim-activation-failed",
                        "executable": False,
                        "action": None,
                    }
                ),
            ),
            failure=failure,
        )

    def acquire_actions(self, selection: DeliveryActionSelection | None = None) -> DeliveryAcquisitionResult:
        """Acquire a fenced selected action, or the explicitly requested portfolio batch."""
        if selection is None:
            return self.acquire_frontier_work()
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(selection.change_id),
        ):
            runtime = self._runtime(selection.change_id, for_mutation=True)
            self._try_convert_pause_request(selection.change_id, runtime)
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                return DeliveryAcquisitionResult(
                    launch_packages=(),
                    failures=(
                        DeliveryAcquisitionFailure(
                            change_id=selection.change_id,
                            outcome_id=selection.outcome_id,
                            code="ERR_DELIVERY_ACTION_ALREADY_ACTIVE",
                            detail=(
                                "The selected Change already has an active claim; "
                                "no worker was dispatched by this call."
                            ),
                            retry_condition=(
                                "Inspect get_change before continuing. The responsible worker owner must provide "
                                "closure or exclusion evidence before resume; do not redispatch or release its claim."
                            ),
                        ),
                    ),
                )
            if hashlib.sha256(runtime.frontier_bytes()).hexdigest() != selection.expected_frontier_digest:
                message = "selected action frontier changed; refresh the selection"
                raise DeliveryActionSelectionConflictError(message)
            failures = self._replay_pending_state_publications(selection.change_id)
            if failures:
                return DeliveryAcquisitionResult(launch_packages=(), failures=failures)
            candidate = next(
                iter(self._candidates(selection.change_id)),
                None,
            )
            if candidate is None:
                self._fail("selected Change has no currently claimable action")
            if (
                candidate.binding.outcome_id != selection.outcome_id
                or candidate.binding.stage != selection.expected_stage
                or candidate.task_id != selection.expected_task_id
            ):
                message = "selected action does not match the next eligible outcome, stage, and task"
                raise DeliveryActionSelectionConflictError(message)
            if self._execution_occupancy() >= self._execution_capacity:
                message = "selected action is waiting for execution capacity"
                raise DeliveryCapacityWaitingError(message)
            return self._acquire_selected_candidate(candidate, selection)

    @contextmanager
    def _selected_action_checkpoint_lock(self, change_id: str) -> Iterator[None]:
        with ExitStack() as stack:
            try:
                stack.enter_context(locked_roots((self._checkpoint_lock_root(change_id),), blocking=False))
            except BlockingIOError as exc:
                message = "selected Change has an operation in progress; retry after that operation finishes"
                raise DeliveryActionBusyError(message) from exc
            yield

    def _acquire_selected_candidate(
        self,
        candidate: _Candidate,
        selection: DeliveryActionSelection,
    ) -> DeliveryAcquisitionResult:
        source = self._prepare_source(
            candidate,
            allow_dirty=candidate.role is DeliveryWorkerRole.BUILDER,
        )
        if isinstance(source, DeliveryAcquisitionFailure):
            return DeliveryAcquisitionResult(launch_packages=(), failures=(source,))
        if source.source_head != selection.expected_source_head and candidate.binding.builder_handoff_context is None:
            message = "selected action source head changed; refresh the selection"
            raise DeliveryActionSelectionConflictError(message)
        if hashlib.sha256(candidate.runtime.frontier_bytes()).hexdigest() != selection.expected_frontier_digest:
            message = "selected action frontier changed during source preparation; refresh the selection"
            raise DeliveryActionSelectionConflictError(message)
        launch = self._activate_candidate(
            candidate,
            source,
            expected_frontier_digest=selection.expected_frontier_digest,
        )
        if isinstance(launch, DeliveryAcquisitionFailure):
            return DeliveryAcquisitionResult(launch_packages=(), failures=(launch,))
        return DeliveryAcquisitionResult(launch_packages=(launch,))

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
        completed = {result.task_id for result in binding.results}
        frontier = parse_delivery_frontier(runtime.frontier_bytes())[0].model_copy(update={"finalization": None})
        coverage = evaluate_acceptance_evidence(runtime.contract, frontier).criteria
        superseded_request_ids = self._superseded_request_ids(runtime, binding)
        return DeliveryPlanContext(
            launch=launch,
            outcome=outcome,
            commitments=self._commitments(runtime, outcome.commitment_ids),
            decisions=runtime.contract.applicable_decisions(outcome.commitment_ids, superseded_request_ids),
            requests=binding.requests,
            superseded_request_ids=superseded_request_ids,
            return_context=binding.return_context,
            acceptance=self._outcome_acceptance(runtime, outcome_id),
            retained_tasks=tuple(task for task in binding.tasks if task.task_id in completed),
            coverage=tuple(item for item in coverage if item.outcome_id == outcome_id),
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
        try:
            ledger = runtime.retry_ledger(clock=self._clock)
            episode = ledger.episode_for_attempt(attempt_id)
            prior_attempts = () if episode is None else ledger.attempt_history(episode, before_attempt_id=attempt_id)
        except (OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError) as exc:
            self._fail("Build retry history is unavailable", exc)
        if episode is not None and (
            episode.key.outcome_id != outcome_id
            or episode.key.action_kind != f"{DeliveryWorkerRole.BUILDER.value}-claim"
            or (
                episode.key.task_lineage != task.task_id
                and not any(alias.alias_kind == "task" and alias.value == task.task_id for alias in episode.aliases)
            )
        ):
            self._fail("Build retry history does not match the active claim")
        superseded_request_ids = self._superseded_request_ids(runtime, binding)
        return DeliveryBuildContext(
            launch=launch,
            task=task,
            task_digest=task.digest,
            commitments=self._commitments(runtime, task.commitment_ids),
            decisions=runtime.contract.applicable_decisions(outcome.commitment_ids, superseded_request_ids),
            predecessor_results=predecessor_results,
            requests=binding.requests,
            superseded_request_ids=superseded_request_ids,
            return_context=binding.return_context,
            recovery_attention=binding.recovery_attention,
            prior_attempts=prior_attempts,
            acceptance=self._outcome_acceptance(runtime, outcome_id),
        )

    @staticmethod
    def _superseded_request_ids(runtime: DeliveryRuntime, binding: OutcomeAuthorityBinding) -> tuple[str, ...]:
        superseded = runtime.contract.superseded_request_ids()
        return tuple(request.request_id for request in binding.requests if request.request_id in superseded)

    @staticmethod
    def _outcome_acceptance(runtime: DeliveryRuntime, outcome_id: str) -> tuple[DeliveryAcceptanceCriterion, ...]:
        return tuple(
            criterion for criterion in acceptance_criteria(runtime.contract) if criterion.outcome_id == outcome_id
        )

    @staticmethod
    def _candidate_authority(
        runtime: DeliveryRuntime,
        outcome_id: str,
        handoff_binding: OutcomeAuthorityBinding | None,
        handoff_task_id: str | None,
    ) -> tuple[OutcomeAuthorityBinding, str | None, int, DeliveryWorkerRole] | None:
        if handoff_binding is not None and outcome_id != handoff_binding.outcome_id:
            return None
        binding = handoff_binding if handoff_binding is not None else runtime.show_binding(outcome_id)
        task_id = None
        task_index = 0
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            task_ids = runtime.claimable_task_ids(outcome_id)
            if not task_ids:
                return None
            task_id = task_ids[0]
            if handoff_task_id is not None and task_id != handoff_task_id:
                return None
            task_index = binding.task_ids.index(task_id)
        role = {
            DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
            DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
        }[binding.stage]
        return binding, task_id, task_index, role

    def _candidates(self, selected_change_id: str | None = None) -> tuple[_Candidate, ...]:  # noqa: C901
        candidates = []
        for change_id, runtime in self._runtimes.items():
            if selected_change_id is not None and change_id != selected_change_id:
                continue
            if change_id in self._runtime_reconciliation_errors:
                continue
            try:
                pending_publication = runtime.pending_state_publication()
                coordination = self._workspace_manager.show(change_id)
                occupied = (
                    runtime.active_claims()
                    or runtime.change_stage() != DeliveryChangeStage.BUILDING
                    or self._writer_occupies_execution_slot(coordination, runtime)
                )
            except OSError, RuntimeError, ValueError:
                continue
            if pending_publication is not None or occupied or coordination.pause_request is not None:
                continue
            pending = runtime.checkpoint_publication_state().pending_checkpoint
            if pending is not None and any(
                trigger.kind == DeliveryCheckpointTriggerKind.ADMITTED_DESIGN for trigger in pending.triggers
            ):
                continue
            claimable = set(runtime.claimable_outcome_ids())
            handoff = coordination.builder_handoff
            handoff_binding: OutcomeAuthorityBinding | None = None
            handoff_task_id: str | None = None
            if handoff is not None:
                handoff_binding = self._claimable_handoff_binding(coordination, runtime, claimable)
                if handoff_binding is None:
                    continue
                handoff_task_id = handoff.original_task_id
            ranked = []
            for outcome_index, outcome in enumerate(runtime.contract.outcomes):
                if outcome.outcome_id not in claimable:
                    continue
                authority = self._candidate_authority(
                    runtime,
                    outcome.outcome_id,
                    handoff_binding,
                    handoff_task_id,
                )
                if authority is None:
                    continue
                binding, task_id, task_index, role = authority
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

    def _validate_planner_handoff_source(
        self,
        candidate: _Candidate,
        coordination: ChangeCoordination,
        handoff_context: DeliveryBuilderHandoffContext,
        handoff: ChangeBuilderHandoff,
    ) -> None:
        binding = candidate.binding
        claim = binding.active_claim
        settled_binding = (
            self._settled_builder_handoff_binding(coordination, candidate.runtime) if claim is None else None
        )
        context_identity = (
            binding.stage,
            handoff_context.route,
            handoff_context.outcome_id,
            handoff_context.original_task_id,
            candidate.task_id,
            coordination.writer,
        )
        expected_identity = (
            DeliveryStage.PLANNING,
            "same-outcome-planner",
            candidate.binding.outcome_id,
            handoff.original_task_id,
            None,
            handoff.original_writer.model_copy(update={"kind": "handoff"}),
        )
        claim_matches = (claim is None and settled_binding == binding) or (
            claim is not None and claim.worker_role is DeliveryWorkerRole.PLANNER and claim.task_id is None
        )
        if context_identity != expected_identity or not claim_matches:
            self._fail("Planning handoff authority does not match its exact returned outcome")

    def _validate_builder_handoff_source(
        self,
        candidate: _Candidate,
        coordination: ChangeCoordination,
        handoff_context: DeliveryBuilderHandoffContext,
        handoff: ChangeBuilderHandoff,
    ) -> None:
        settled_binding = self._settled_builder_handoff_binding(coordination, candidate.runtime)
        actual_identity = (
            candidate.role,
            settled_binding.outcome_id if settled_binding is not None else None,
            candidate.binding.active_claim,
            candidate.binding.stage,
            handoff_context.route,
            handoff_context.original_task_id,
            candidate.task_id,
        )
        expected_identity = (
            DeliveryWorkerRole.BUILDER,
            candidate.binding.outcome_id,
            None,
            DeliveryStage.IMPLEMENTATION,
            "same-task",
            handoff.original_task_id,
            handoff.original_task_id,
        )
        if actual_identity != expected_identity:
            self._fail("Builder handoff authority does not match its exact same-task retry")

    def _prepare_source(
        self,
        candidate: _Candidate,
        *,
        allow_dirty: bool = False,
    ) -> _PreparedSource | DeliveryAcquisitionFailure:
        change_id = candidate.change_id
        runtime = candidate.runtime
        outcome_id = candidate.binding.outcome_id
        worker_role = candidate.role
        task_id = candidate.task_id
        try:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            coordination = self._workspace_manager.show(change_id)
            binding = runtime.show_binding(outcome_id)
            handoff_context = binding.builder_handoff_context
            handoff = coordination.builder_handoff
            is_handoff_source = False
            if handoff_context is not None and handoff is not None:
                if worker_role is DeliveryWorkerRole.PLANNER:
                    self._validate_planner_handoff_source(candidate, coordination, handoff_context, handoff)
                else:
                    self._validate_builder_handoff_source(candidate, coordination, handoff_context, handoff)
                source_head = self._workspace_manager.source_head(
                    change_id,
                    require_clean=False,
                    builder_handoff_source=BuilderHandoffSource(
                        settlement_id=handoff_context.settlement_id,
                        original_task_id=handoff_context.original_task_id,
                        branch_head=handoff_context.branch_head,
                        last_reviewed_commit=handoff_context.last_reviewed_commit,
                        metadata_fingerprint=handoff_context.metadata_fingerprint,
                        retained_handoff=handoff,
                    ),
                )
                is_handoff_source = True
            elif handoff_context is not None:
                claim = binding.active_claim
                writer = coordination.writer
                if (
                    worker_role is not DeliveryWorkerRole.BUILDER
                    or binding.stage is not DeliveryStage.IMPLEMENTATION
                    or handoff_context.route != "same-task"
                    or handoff_context.outcome_id != outcome_id
                    or handoff_context.original_task_id != task_id
                    or claim is None
                    or claim.worker_role is not DeliveryWorkerRole.BUILDER
                    or claim.task_id != task_id
                    or writer is None
                    or writer.kind != "build"
                    or writer.attempt_id != claim.attempt_id
                    or writer.claim_id != claim.claim_id
                    or writer.actor_id != claim.owner_id
                    or writer.process_id != claim.process_id
                    or writer.claimed_at != claim.started_at
                ):
                    self._fail("active Builder handoff context does not match its exact successor claim")
                source_head = self._workspace_manager.source_head(
                    change_id,
                    require_clean=False,
                    builder_handoff_source=BuilderHandoffSource(
                        settlement_id=handoff_context.settlement_id,
                        original_task_id=handoff_context.original_task_id,
                        branch_head=handoff_context.branch_head,
                        last_reviewed_commit=handoff_context.last_reviewed_commit,
                        metadata_fingerprint=handoff_context.metadata_fingerprint,
                    ),
                )
                is_handoff_source = True
            else:
                source_head = self._workspace_manager.source_head(change_id, require_clean=not allow_dirty)
            adoption = coordination.external_head_adoption_receipt
            promotion = coordination.external_head_promotion_receipt
            if promotion != runtime.external_head_promotion_receipt():
                return DeliveryAcquisitionFailure(
                    change_id=change_id,
                    outcome_id=outcome_id,
                    code=PortfolioApplicationError.code,
                    detail="external Change head promotion is not reconciled to Delivery authority",
                    retry_condition="Replay the exact external Change head promotion operation.",
                )
            if (
                not is_handoff_source
                and source_head != coordination.last_reviewed_commit
                and (adoption is None or runtime.external_head_adoption_receipt() != adoption)
            ):
                return DeliveryAcquisitionFailure(
                    change_id=change_id,
                    outcome_id=outcome_id,
                    code=PortfolioApplicationError.code,
                    detail="external Change head adoption is not reconciled to Delivery authority",
                    retry_condition="Replay the exact external Change head adoption operation.",
                )
            if (
                worker_role == DeliveryWorkerRole.BUILDER
                and source_head != coordination.last_reviewed_commit
                and not is_handoff_source
            ):
                return DeliveryAcquisitionFailure(
                    change_id=change_id,
                    outcome_id=outcome_id,
                    code=PortfolioApplicationError.code,
                    detail="Builder authority requires explicit promotion of the adopted Change head",
                    retry_condition="Promote the exact adopted Change head before acquiring Build work.",
                )
        except (OSError, RuntimeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id=outcome_id,
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Restore the admitted package and clean reviewed source boundary.",
            )
        return _PreparedSource(package, coordination, source_head)

    def _promote_finalized_external_head(self, change_id: str, exact_head: str) -> None:
        try:
            runtime = self._runtime(change_id, for_mutation=True)
            coordination = self._workspace_manager.show(change_id)
            if (
                coordination.last_reviewed_commit == exact_head
                and coordination.external_head_promotion_receipt == runtime.external_head_promotion_receipt()
            ):
                return
            operation_id = f"finalization-{exact_head}"
            promotion = self._workspace_manager.promote_external_head(
                PromoteExternalHead(
                    change_id=change_id,
                    expected_head=exact_head,
                    operation_id=operation_id,
                ),
                provenance="finalization",
            )
            if promotion is not None:
                runtime.record_external_head_promotion(promotion, _timestamp(self._clock()))
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("finalization could not promote the reviewed adopted Change head", exc)

    def _return_publication_to_draft_before_head_change(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        operation_id: str,
        *,
        finalization_id: str | None = None,
    ) -> None:
        """Demote the bound provider pull request before its Change head moves."""
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        if finalization is None or ready is None:
            if finalization_id is None:
                return
            publication = runtime.change_disposition_publication()
            if publication is None:
                self._fail("Change head movement requires a bound publication identity")
            expected_finalization_id = finalization_id
            expected_repository = publication.repository
            expected_number = publication.number
            expected_node_id = publication.node_id
        else:
            expected_finalization_id = finalization.finalization_id
            expected_repository = ready.repository
            expected_number = ready.number
            expected_node_id = ready.node_id
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("Change head movement requires a configured publication provider")
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            self._fail("Change head movement requires a bound pull request")
        snapshot = observation.snapshot
        if (
            snapshot.repository != expected_repository
            or snapshot.number != expected_number
            or snapshot.node_id != expected_node_id
            or snapshot.base_branch != publisher.target_branch
            or snapshot.state != "open"
            or snapshot.merged
        ):
            self._fail("Change head movement requires an open bound pull request")
        if snapshot.draft:
            if finalization is not None and ready is not None:
                runtime.clear_ready_for_head_change(
                    finalization.finalization_id,
                    finalization.exact_head,
                )
            return
        publisher.return_to_draft(
            ReturnChangePullRequestToDraft(
                change_id=change_id,
                operation_id=f"return-draft-{operation_id}",
                finalization_id=expected_finalization_id,
                exact_head=snapshot.head_sha,
            )
        )
        if finalization is not None and ready is not None:
            runtime.clear_ready_for_head_change(
                finalization.finalization_id,
                finalization.exact_head,
            )

    @staticmethod
    def _require_fresh_target_sync_review(runtime: DeliveryRuntime) -> None:
        """Reject publication paths that still contain an unreviewed resolved target merge."""
        target_sync = runtime.target_sync_receipt()
        if target_sync is not None and target_sync.review_required and runtime.finalization() is None:
            message = "target synchronization resolution requires fresh finalization review"
            raise PortfolioApplicationError(message)

    def _activate_candidate(
        self,
        candidate: _Candidate,
        source: _PreparedSource,
        *,
        expected_frontier_digest: str | None = None,
        host_identity: tuple[str, str] | None = None,
        isolate_retry_accounting: bool = False,
    ) -> DeliveryLaunchPackage | DeliveryAcquisitionFailure:
        try:
            self._reconcile_retry_results_fail_closed(candidate.runtime)
        except (OSError, RuntimeError, ValueError) as exc:
            if not isolate_retry_accounting:
                raise
            return self._retry_accounting_unavailable(candidate, exc)
        claim = self._new_claim(candidate.role, candidate.task_id)
        if host_identity is not None:
            claim = claim.model_copy(
                update={"owner_id": host_identity[0], "process_id": host_identity[1], "continuation": True}
            )
        frontier_before = candidate.runtime.frontier_bytes()
        try:
            reservation = self._reserve_worker_attempt(candidate, source, claim.attempt_id, claim.claim_id)
        except (OSError, RuntimeError, ValueError) as exc:
            if not isolate_retry_accounting:
                raise
            return self._retry_accounting_unavailable(candidate, exc)
        if reservation is not None and not reservation.allowed:
            backoff = reservation.stop_code is RetryStopCode.BACKOFF
            return DeliveryAcquisitionFailure(
                change_id=candidate.change_id,
                outcome_id=candidate.binding.outcome_id,
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                code="ERR_DELIVERY_RETRY_BACKOFF" if backoff else "ERR_DELIVERY_RETRY_EXHAUSTED",
                detail=(
                    "Automatic worker repair is waiting for this semantic failure episode's durable backoff."
                    if backoff
                    else "Automatic worker repair is not eligible for this semantic failure episode."
                ),
                retry_condition=(
                    "Wait for the durable retry eligibility time; waiting does not create a new allowance."
                    if backoff
                    else "Wait for the durable retry eligibility time or record accepted progress for this exact "
                    "episode; do not create a new allowance by renaming the task or operation."
                ),
            )
        try:
            builder_writer = self._activate_candidate_claim(candidate, claim, source, expected_frontier_digest)
        except OSError, RuntimeError, subprocess.SubprocessError, ValueError:
            self._release_unpublished_worker_claim(candidate, claim, frontier_before, source.coordination)
            raise
        try:
            handoff = source.coordination.builder_handoff
            writer = self._acquire_candidate_writer(
                candidate,
                builder_writer,
                consumes_handoff=handoff is not None,
            )
            return self._launch_package(candidate, claim, source, writer)
        except (OSError, RuntimeError, ValueError) as exc:
            if reservation is not None and reservation.attempt_id is not None:
                with suppress(OSError, RuntimeError, ValueError):
                    candidate.runtime.retry_ledger(clock=self._clock).record_failure(
                        reservation,
                        failure_code=getattr(exc, "code", PortfolioApplicationError.code),
                        failure_detail=str(exc),
                        now=self._clock(),
                    )
            return DeliveryAcquisitionFailure(
                change_id=candidate.change_id,
                outcome_id=candidate.binding.outcome_id,
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc) or "worker launch preparation failed after claim activation",
                retry_condition=(
                    "Retain the exact claim and any writer custody. Automatic recovery is unavailable while "
                    "host/worker evidence is missing. Resume awaits verified closure that excludes all descendants "
                    "and tool jobs and records settlement. Do not redispatch, infer termination, or use caller "
                    "confirmation as recovery evidence."
                    if claim.continuation
                    else "Recover the exact failed claim after reconciling writer custody."
                ),
            )

    @staticmethod
    def _retry_accounting_unavailable(candidate: _Candidate, exc: Exception) -> DeliveryAcquisitionFailure:
        return DeliveryAcquisitionFailure(
            change_id=candidate.change_id,
            outcome_id=candidate.binding.outcome_id,
            code=getattr(exc, "code", PortfolioApplicationError.code),
            detail="Retry accounting for this Change is unavailable; no claim or writer was published.",
            retry_condition=(
                "Restore readable retry-ledger state for this Change before acquiring it again; "
                "independent Changes remain eligible."
            ),
        )

    def _activate_candidate_claim(
        self,
        candidate: _Candidate,
        claim: DeliveryActiveClaim,
        source: _PreparedSource,
        expected_frontier_digest: str | None,
    ) -> ChangeWriter | None:
        writer = (
            ChangeWriter(
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                actor_id=claim.owner_id,
                process_id=claim.process_id,
                claimed_at=claim.started_at,
                job_id=1,
                kind="build",
            )
            if candidate.role is DeliveryWorkerRole.BUILDER
            else None
        )
        activation = ActivateDeliveryClaim(
            outcome_id=candidate.binding.outcome_id,
            claim=claim,
            expected_frontier_digest=expected_frontier_digest,
        )
        handoff = source.coordination.builder_handoff
        if handoff is None:
            self._register_recovery_invocation(
                candidate.runtime,
                claim.claim_id,
                claim.attempt_id,
                "claim",
                source.source_head,
                candidate.binding.outcome_id,
            )
            self._publish_claim_issuer(candidate.change_id, candidate.binding.outcome_id, claim)
            candidate.runtime.activate_claim(activation)
            return writer
        if candidate.role is DeliveryWorkerRole.PLANNER:
            context = candidate.binding.builder_handoff_context
            if candidate.task_id is not None or context is None or context.route != "same-outcome-planner":
                self._fail("Planner handoff activation requires its exact task-less Planning claim")
            with self._coordinator.publication_lock(candidate.change_id) as lock:
                coordination = self._workspace_manager.show(candidate.change_id)
                binding = candidate.runtime.show_binding(candidate.binding.outcome_id)
                settled_binding = self._settled_builder_handoff_binding(coordination, candidate.runtime)
                if (
                    coordination.builder_handoff != handoff
                    or coordination.writer != handoff.original_writer.model_copy(update={"kind": "handoff"})
                    or binding.builder_handoff_context != context
                    or binding.stage != DeliveryStage.PLANNING
                    or binding.active_claim is not None
                    or settled_binding != binding
                ):
                    self._fail("Planning handoff changed before same-outcome claim activation")
                source_head = self._workspace_manager.source_head(
                    candidate.change_id,
                    require_clean=False,
                    builder_handoff_source=BuilderHandoffSource(
                        settlement_id=context.settlement_id,
                        original_task_id=context.original_task_id,
                        branch_head=context.branch_head,
                        last_reviewed_commit=context.last_reviewed_commit,
                        metadata_fingerprint=context.metadata_fingerprint,
                        retained_handoff=handoff,
                    ),
                )
                if source_head != source.source_head:
                    self._fail("Planning handoff source changed before claim activation")
                self._register_recovery_invocation(
                    candidate.runtime,
                    claim.claim_id,
                    claim.attempt_id,
                    "claim",
                    source.source_head,
                    candidate.binding.outcome_id,
                )
                self._publish_claim_issuer(candidate.change_id, candidate.binding.outcome_id, claim)
                candidate.runtime.activate_claim(activation, builder_handoff_lock=lock)
            return None
        if writer is None or candidate.task_id is None:
            self._fail("Builder handoff activation requires exact Builder writer and task authority")
        with self._coordinator.publication_lock(candidate.change_id) as lock:
            coordination = self._workspace_manager.show(candidate.change_id)
            binding = candidate.runtime.show_binding(candidate.binding.outcome_id)
            settled_binding = self._settled_builder_handoff_binding(coordination, candidate.runtime)
            if (
                coordination.builder_handoff != handoff
                or binding.builder_handoff_context != candidate.binding.builder_handoff_context
                or settled_binding is None
                or settled_binding.outcome_id != candidate.binding.outcome_id
                or candidate.task_id != handoff.original_task_id
            ):
                self._fail("Builder handoff changed before same-task claim activation")
            self._register_recovery_invocation(
                candidate.runtime,
                claim.claim_id,
                claim.attempt_id,
                "claim",
                source.source_head,
                candidate.binding.outcome_id,
            )
            participant = self._workspace_manager.prepare_builder_handoff_acquisition(
                candidate.change_id,
                writer,
                handoff,
                lock,
                task_id=candidate.task_id,
            )
            self._publish_claim_issuer(candidate.change_id, candidate.binding.outcome_id, claim)
            candidate.runtime.activate_claim(
                activation,
                builder_handoff_participant=participant,
                builder_handoff_lock=lock,
            )
        return writer

    def _acquire_candidate_writer(
        self,
        candidate: _Candidate,
        writer: ChangeWriter | None,
        *,
        consumes_handoff: bool,
    ) -> ChangeWriter | None:
        if candidate.role is not DeliveryWorkerRole.BUILDER:
            return None
        if writer is None:
            self._fail("Builder activation lost its exact workspace writer")
        if consumes_handoff:
            return self._coordinator.show(candidate.change_id).writer
        # The claim activated before any Pause is a K2 owner; its writer acquisition is its own start.
        with self._coordinator.drain_authority(
            candidate.change_id, f"claim:{writer.claim_id}", acquire=(writer.claim_id,)
        ):
            return self._coordinator.acquire(candidate.change_id, writer).writer

    def _try_convert_pause_request_if_requested(self, change_id: str) -> None:
        """Next-acquisition conversion point (K5) for one Change whose checkpoint lock is free."""
        try:
            if self._coordinator.pause_request(change_id) is None:
                return
            with locked_roots((self._checkpoint_lock_root(change_id),), blocking=False):
                self._try_convert_pause_request(change_id)
        except BlockingIOError, CoordinationConflictError:
            return
