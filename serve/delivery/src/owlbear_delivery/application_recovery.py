"""Worker settlement, retry reconciliation, repair and claim recovery routes."""

from __future__ import annotations

import hashlib
import stat
import subprocess
from contextlib import ExitStack, suppress
from datetime import timedelta
from pathlib import Path, PurePosixPath
from typing import Literal

from owlbear_delivery.application_models import (
    DeliveryAcquisitionFailure,
    DeliveryActionBusyError,
    DeliveryClaimRecoveryResult,
    DeliveryIntegrationRepairRecoveryResult,
    DeliveryQuarantinedSnapshotRepairProposal,
    DeliveryQuarantinedSnapshotRepairReceipt,
    DeliveryRepairKind,
    DeliveryRepairProposal,
    DeliveryRepairResult,
    DeliveryRuntimeReconciliationError,
    DeliveryStateSnapshotRepairReceipt,
    DeliveryStrandedFrontierRepairReceipt,
    DeliveryTargetSyncRepairReceipt,
    DeliveryUnavailableChangeView,
    ExecuteDeliveryChangeAction,
    PortfolioApplicationError,
    _Candidate,
    _WorkerStall,
)
from owlbear_delivery.application_support import (
    _canonical_model_bytes,
    _checkpoint_operation_id,
    _timestamp,
)
from owlbear_delivery.change_workspace import (
    ChangeContinuationAction,
    ChangeCoordination,
    ChangeFinalizationAttempt,
    ChangeFinalizationAttention,
    OutOfBandHeadRecoveryReceipt,
    RecoverOutOfBandHead,
)
from owlbear_delivery.delivery_admission import DeliveryAdmissionReceipt
from owlbear_delivery.delivery_contract_discovery import (
    contract_fingerprint,
)
from owlbear_delivery.delivery_runtime import (
    BlockDelivery,
    DeliveryActiveClaim,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeStage,
    DeliveryEngineBuilderSettlement,
    DeliveryEnginePlanningSettlement,
    DeliveryFrontier,
    DeliveryPendingStatePublication,
    DeliveryPlanningRetrySettlement,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTransition,
    DeliveryWorkerRole,
    EngineWorkerDisposition,
    OutcomeAuthorityBinding,
    PrepareCompletedOutcomeRepair,
    parse_delivery_frontier,
    repair_missing_request_provenance,
)
from owlbear_delivery.draft_pull_request import (
    ObserveChangePublicationPullRequest,
)
from owlbear_delivery.finalization_reports import (
    FinalizationFailureCode,
    FinalizationReport,
    FinalizationReportError,
    FinalizationReportStore,
    FinalizerEngineSettlement,
    FinalizerSettlementReceipt,
    ReportFinalizationFailure,
    finalizer_settlement_outcome,
)
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthReason,
)
from owlbear_delivery.recovery import (
    MAX_RECOVERY_INTENTS,
    DeliveryWorkerExclusionRequiredError,
    RecoveryEvidence,
    RecoveryEvidenceReference,
    RecoveryIntent,
    RecoveryInvocation,
    RecoveryInvocationRequest,
    RecoveryReceipt,
    RetryAttempt,
    RetryFailureClass,
    RetryLedger,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    UnavailableRecoveryEvidenceProvider,
    digest,
    invocation_path,
    is_canonical_admitted_path,
    journal_path,
    publish_record,
    read_record,
    verify_evidence,
)
from owlbear_delivery.runtime_models import retained_requests
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionParticipant,
)
from owlbear_delivery.storage_io import locked_roots, state_is_read_only
from owlbear_delivery.work_items import (
    DeliveryPortfolioSnapshot,
    DeliveryProgress,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    WorkItemCardView,
    WorkItemNextActor,
)
from owlbear_delivery.worker_stall import (
    DeliveryClaimIssuer,
    DeliveryWorkerActiveError,
    claim_issuer_path,
    is_issuable_attempt_id,
)
from owlbear_delivery.workspace_models import recovery_authority_digest


class _RecoveryMixin:
    """Worker settlement, retry reconciliation, repair and claim recovery routes."""

    def _reconcile_retry_results(self, runtime: DeliveryRuntime) -> None:
        """Replay accounting only from owner receipts; absent evidence keeps reservations."""
        if state_is_read_only():
            return
        self._import_legacy_worker_budgets(runtime)
        ledger = runtime.retry_ledger(clock=self._clock)
        ledger.reconcile_owner_results()
        finalization = runtime.finalization()
        for attempt in ledger.pending_attempts():
            if attempt.key.outcome_id is not None:
                self._reconcile_worker_retry_receipt(runtime, ledger, attempt)
            elif (
                attempt.key.action_kind == "finalize"
                and finalization is not None
                and finalization.operation_id == attempt.attempt_id
                and finalization.exact_head == attempt.key.exact_head
            ):
                ledger.record_accepted_progress(attempt.attempt_id, now=finalization.finalized_at)
            elif attempt.attempt_id.startswith("continue-"):
                result = self._read_engine_result(
                    ExecuteDeliveryChangeAction(change_id=runtime.contract.change_id, operation_id=attempt.attempt_id)
                )
                if result is not None:
                    self._record_engine_attempt_result(result.action, result)
        reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read()
        for report in reports.reports:
            if any(report.request.attempt_key in episode.attempt_ids for episode in ledger.read().episodes):
                ledger.record_failure(
                    report.request.attempt_key, failure_code=report.request.code.value, now=report.observed_at
                )

    def _reconcile_retry_results_fail_closed(self, runtime: DeliveryRuntime) -> None:
        try:
            self._reconcile_retry_results(runtime)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(
                runtime.contract.change_id, "worker retry owner results are unavailable"
            ) from exc

    def _reconcile_worker_retry_receipt(
        self, runtime: DeliveryRuntime, ledger: RetryLedger, attempt: RetryAttempt
    ) -> None:
        """Recognize an original Builder receipt written before owner-result companions."""
        if attempt.operation_alias is None:
            return
        binding = runtime.show_binding(attempt.key.outcome_id)
        for result in binding.results:
            try:
                runtime.require_result_replay(binding.outcome_id, attempt.operation_alias, result)
            except DeliveryRuntimeConflictError, DeliveryRuntimeReferenceError:
                continue
            repair_binding = ledger.repair_binding_for_attempt(
                attempt.attempt_id,
                outcome_id=binding.outcome_id,
            )
            if repair_binding is None:
                ledger.record_accepted_progress(attempt.attempt_id, now=self._clock())
            return

    def _record_proven_unstarted_retry_release(
        self,
        runtime: DeliveryRuntime,
        attempt_id: str,
        *,
        refund: bool = False,
    ) -> None:
        owner_result = (
            Path("changes") / runtime.contract.change_id / "retry-ledger" / "owner-results" / f"{attempt_id}.json"
        )
        if not self._contained_record_is_absent(owner_result):
            return
        try:
            ledger = runtime.retry_ledger(clock=self._clock)
            if refund:
                ledger.record_pause(attempt_id, now=self._clock())
            else:
                ledger.record_failure(
                    attempt_id,
                    failure_code="owner-publication-failed-before-start",
                    now=self._clock(),
                )
        except OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError:
            return

    def _contained_record_is_absent(self, relative_path: Path) -> bool:
        try:
            read_record(self._target_root, relative_path)
        except FileNotFoundError:
            return True
        except OSError, RuntimeError, ValueError:
            return False
        return False

    def _release_unpublished_engine_action(self, runtime: DeliveryRuntime, action: ChangeContinuationAction) -> None:
        try:
            coordination = self._coordinator.show(action.change_id)
            retained = coordination.continuation_action
            if retained is not None and (retained.operation_id == action.operation_id or retained.finished_at is None):
                return
            finalization = coordination.finalization_attempt
            if (
                coordination.writer is not None
                or coordination.publication_lease is not None
                or (finalization is not None and finalization.finished_at is None)
                or runtime.active_claims()
                or runtime.integration_repair_claim() is not None
            ):
                return
            intent = self._coordinator.continuation_record_path(action.change_id, action.operation_id)
            records = (intent, intent.with_name("started.json"), intent.with_name("result.json"))
            if not all(self._contained_record_is_absent(path.relative_to(self._target_root)) for path in records):
                return
        except OSError, RuntimeError, ValueError:
            return
        self._record_proven_unstarted_retry_release(runtime, action.operation_id)

    def _release_unpublished_worker_claim(
        self,
        candidate: _Candidate,
        claim: DeliveryActiveClaim,
        frontier_before: bytes,
        prepared_coordination: ChangeCoordination,
    ) -> None:
        runtime = candidate.runtime
        try:
            coordination = self._coordinator.show(candidate.change_id)
            binding = runtime.show_binding(candidate.binding.outcome_id)
            finalization = coordination.finalization_attempt
            continuation = coordination.continuation_action
            handoff = prepared_coordination.builder_handoff
            if (
                runtime.frontier_bytes() != frontier_before
                or binding.active_claim is not None
                or runtime.active_claims()
                or runtime.integration_repair_claim() is not None
                or coordination.writer != prepared_coordination.writer
                or coordination.builder_handoff != handoff
                or coordination.publication_lease is not None
                or (finalization is not None and finalization.finished_at is None)
                or (continuation is not None and continuation.finished_at is None)
            ):
                return
            if handoff is not None:
                settled_binding = self._settled_builder_handoff_binding(coordination, runtime)
                context = binding.builder_handoff_context
                expected_writer = handoff.original_writer.model_copy(update={"kind": "handoff"})
                planner_handoff = (
                    candidate.role is DeliveryWorkerRole.PLANNER
                    and binding.stage == DeliveryStage.PLANNING
                    and context is not None
                    and context.route == "same-outcome-planner"
                    and candidate.task_id is None
                )
                builder_handoff = (
                    candidate.role is DeliveryWorkerRole.BUILDER
                    and binding.stage == DeliveryStage.IMPLEMENTATION
                    and context is not None
                    and context.route == "same-task"
                    and candidate.task_id == handoff.original_task_id
                )
                if (
                    prepared_coordination.writer != expected_writer
                    or coordination.writer != expected_writer
                    or settled_binding is None
                    or settled_binding != binding
                    or settled_binding.outcome_id != candidate.binding.outcome_id
                    or context is None
                    or context != candidate.binding.builder_handoff_context
                    or context.settlement_id != handoff.settlement_id
                    or context.original_task_id != handoff.original_task_id
                    or not (planner_handoff or builder_handoff)
                ):
                    return
        except OSError, RuntimeError, ValueError:
            return
        self._record_proven_unstarted_retry_release(
            runtime,
            claim.attempt_id,
            refund=prepared_coordination.builder_handoff is not None,
        )

    def _release_unpublished_finalizer(
        self,
        runtime: DeliveryRuntime,
        attempt: ChangeFinalizationAttempt,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> None:
        try:
            active_claims = runtime.active_claims()
            integration_repair_claim = runtime.integration_repair_claim()
            finalization = runtime.finalization()
            coordination = self._coordinator.show(runtime.contract.change_id)
            retained = coordination.finalization_attempt
            continuation = coordination.continuation_action
            attention_unchanged = (
                expected_finalization_attention is not None
                and coordination.finalization_attention == expected_finalization_attention
                and retained is not None
                and retained.finished_at is not None
                and retained.writer.attempt_id != attempt.writer.attempt_id
                and coordination.writer == retained.writer.model_copy(update={"kind": "finalization-attention"})
            )
            if (
                (coordination.writer is not None and not attention_unchanged)
                or coordination.publication_lease is not None
                or (
                    retained is not None
                    and (retained.writer.attempt_id == attempt.writer.attempt_id or retained.finished_at is None)
                )
                or (continuation is not None and continuation.finished_at is None)
                or active_claims
                or integration_repair_claim is not None
                or (finalization is not None and finalization.operation_id == attempt.writer.attempt_id)
            ):
                return
        except OSError, RuntimeError, ValueError:
            return
        self._record_proven_unstarted_retry_release(
            runtime,
            attempt.writer.attempt_id,
            refund=attention_unchanged,
        )

    def _import_legacy_worker_budgets(self, runtime: DeliveryRuntime) -> None:
        """Preserve historical failures before a mutation can clear binding metadata."""
        for binding in runtime.bindings():
            if not binding.retry_count or binding.stage not in {DeliveryStage.PLANNING, DeliveryStage.IMPLEMENTATION}:
                continue
            role = (
                DeliveryWorkerRole.BUILDER
                if binding.stage is DeliveryStage.IMPLEMENTATION
                else DeliveryWorkerRole.PLANNER
            )
            completed = {result.task_id for result in binding.results}
            task_id = (
                binding.active_task_id
                or next(
                    (
                        task.task_id
                        for task in binding.tasks
                        if task.task_id not in completed and set(task.dependency_ids) <= completed
                    ),
                    None,
                )
                if role is DeliveryWorkerRole.BUILDER
                else None
            )
            change_id = runtime.contract.change_id
            candidate = _Candidate((0, 0, 0, change_id), change_id, runtime, binding, task_id, role)
            key = self._worker_retry_key(candidate, self._workspace_manager.show(change_id).last_reviewed_commit)
            claim = binding.active_claim
            runtime.retry_ledger(clock=self._clock).import_legacy_failures(
                key,
                binding.retry_count,
                now=self._clock(),
                existing_attempt=(claim.attempt_id, claim.claim_id) if claim is not None else None,
            )

    def transition_delivery(
        self,
        change_id: str,
        request: DeliveryTransition,
    ) -> OutcomeAuthorityBinding:
        """Apply one validated mechanical transition through its exact runtime."""
        runtime = self._runtime(change_id, for_mutation=True)
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._worker_drain_authority(
                runtime,
                request.outcome_id,
                request.claim_id,
                replay_digest=hashlib.sha256(_canonical_model_bytes(request)).hexdigest(),
            ),
        ):
            binding = self._transition_delivery_locked(change_id, runtime, request)
            self._try_convert_pause_request(change_id, runtime)
            return binding

    def _transition_delivery_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        request: DeliveryTransition,
    ) -> OutcomeAuthorityBinding:
        self._import_legacy_worker_budgets(runtime)
        previous = runtime.frontier_bytes()
        binding = runtime.transition(request, retry_observed_at=self._clock())
        if isinstance(request, BlockDelivery) and request.request is not None and runtime.frontier_bytes() == previous:
            pending = runtime.pending_state_publication()
            request_digest = hashlib.sha256(_canonical_model_bytes(request)).hexdigest()
            if pending is None or pending.transition_request_digest != request_digest:
                return binding
        if request.action == "advance":
            self._record_worker_retry_success(runtime, request.outcome_id, request.claim_id)
        elif request.action in {"block", "return"}:
            with suppress(OSError, RuntimeError, ValueError):
                runtime.retry_ledger(clock=self._clock).reconcile_owner_results()
        self._publish_delivery_state(
            change_id,
            runtime,
            _checkpoint_operation_id("transition", change_id, request.outcome_id, request.claim_id),
        )
        return binding

    def settle_worker_invocation(
        self,
        settlement: DeliveryPlanningRetrySettlement | DeliveryBuilderInvocationSettlement,
        *,
        host_id: str | None = None,
        session_id: str | None = None,
    ) -> OutcomeAuthorityBinding:
        """Settle one ended Planner or Builder invocation through its exact owner receipt."""
        if type(settlement) not in {DeliveryPlanningRetrySettlement, DeliveryBuilderInvocationSettlement}:
            self._fail("worker settlement requires its typed caller-reported invocation envelope")
        change_id = settlement.change_id
        runtime = self._runtime(change_id, for_mutation=True)
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(change_id),
        ):
            claim = runtime.show_binding(settlement.outcome_id).active_claim
            worker_role = (
                DeliveryWorkerRole.PLANNER
                if isinstance(settlement, DeliveryPlanningRetrySettlement)
                else DeliveryWorkerRole.BUILDER
            )
            if (
                claim is not None
                and claim.claim_id == settlement.claim_id
                and claim.attempt_id == settlement.attempt_id
                and claim.worker_role is worker_role
                and claim.continuation
                and (host_id != claim.owner_id or session_id != claim.process_id)
            ):
                self._fail("worker continuation settlement does not match its active host and session binding")
            with self._worker_drain_authority(
                runtime,
                settlement.outcome_id,
                settlement.claim_id,
                replay_digest=hashlib.sha256(_canonical_model_bytes(settlement)).hexdigest(),
            ):
                binding = self._retry_pause_field_conflict(lambda: self._apply_worker_settlement(runtime, settlement))
            self._try_convert_pause_request(change_id, runtime)
            return binding

    def _apply_worker_settlement(
        self,
        runtime: DeliveryRuntime,
        settlement: DeliveryPlanningRetrySettlement | DeliveryBuilderInvocationSettlement,
    ) -> OutcomeAuthorityBinding:
        """Settle through the exact runtime owner and publish its state; callers hold the Change locks."""
        change_id = runtime.contract.change_id
        frontier_before = runtime.frontier_bytes()
        result = (
            runtime.settle_planning_retry(settlement, retry_observed_at=self._clock())
            if isinstance(settlement, DeliveryPlanningRetrySettlement)
            else runtime.settle_builder_invocation(settlement, retry_observed_at=self._clock())
        )
        frontier_after = runtime.frontier_bytes()
        settlement_digest = hashlib.sha256(_canonical_model_bytes(settlement)).hexdigest()
        if frontier_after != frontier_before:
            self._reconcile_retry_results_fail_closed(runtime)
        pending = runtime.pending_state_publication()
        if pending is not None:
            frontier_digest = hashlib.sha256(frontier_after).hexdigest()
            if pending.frontier_digest == frontier_digest and pending.transition_request_digest == settlement_digest:
                if frontier_after != frontier_before and self._delivery_state_publisher is not None:
                    settlement_kind = (
                        "builder-invocation-settlement"
                        if isinstance(settlement, DeliveryBuilderInvocationSettlement)
                        else "planning-retry-settlement"
                    )
                    self._publish_delivery_state(
                        change_id,
                        runtime,
                        _checkpoint_operation_id(
                            settlement_kind, change_id, settlement.outcome_id, settlement.claim_id
                        ),
                    )
                    failure = None
                else:
                    failure = self._replay_pending_state_publication(change_id, runtime)
                if failure is not None:
                    raise DeliveryRuntimeReconciliationError(change_id, failure.detail)
        return result

    def release_stuck_worker(
        self,
        change_id: str,
        outcome_id: str | None,
        attempt_id: str,
        claim_id: str,
    ) -> OutcomeAuthorityBinding | FinalizerSettlementReceipt:
        """Settle one exact active worker whose stopped invocation left its worktree quiet.

        ``outcome_id`` names a Planner or Builder claim; ``None`` names the Change's Finalizer attempt.
        """
        runtime = self._runtime(change_id, for_mutation=True, allow_finalizer=outcome_id is None)
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(change_id),
        ):
            if outcome_id is None:
                released = self._release_stuck_finalizer(runtime, attempt_id, claim_id)
                self._try_convert_pause_request(change_id, runtime)
                return released
            replay = runtime.engine_worker_settlement_replay(outcome_id, attempt_id, claim_id, "released-stuck")
            if replay is not None:
                result, envelope = replay
                # K2 release replay: finish the receipt's own pending publication before converting.
                with self._worker_drain_authority(
                    runtime,
                    outcome_id,
                    claim_id,
                    replay_digest=hashlib.sha256(_canonical_model_bytes(envelope)).hexdigest(),
                ):
                    self._apply_worker_settlement(runtime, envelope)
                self._try_convert_pause_request(change_id, runtime)
                return result
            claim = runtime.require_active_claim(outcome_id, attempt_id, claim_id).active_claim
            if claim is None or claim.worker_role not in {DeliveryWorkerRole.PLANNER, DeliveryWorkerRole.BUILDER}:
                self._fail("stuck-worker release supports only an active Planner or Builder claim")
            self._require_quiet_worktree(change_id, claim.started_at)
            envelope = self._engine_worker_envelope(runtime, outcome_id, claim, "released-stuck")
            with self._worker_drain_authority(
                runtime,
                outcome_id,
                claim_id,
                replay_digest=hashlib.sha256(_canonical_model_bytes(envelope)).hexdigest(),
            ):
                binding = self._apply_worker_settlement(runtime, envelope)
            self._try_convert_pause_request(change_id, runtime)
            return binding

    def _release_stuck_finalizer(
        self, runtime: DeliveryRuntime, attempt_id: str, claim_id: str
    ) -> FinalizerSettlementReceipt:
        change_id = runtime.contract.change_id
        prior = self._read_finalizer_settlement_receipt(change_id, attempt_id)
        if prior is not None:
            settlement = prior.settlement
            if (
                not isinstance(settlement, FinalizerEngineSettlement)
                or settlement.disposition != "released-stuck"
                or settlement.claim_id != claim_id
            ):
                self._raise_finalizer_settlement_conflict(
                    "Finalizer attempt is already settled with different authority"
                )
            self._reconcile_retry_results_fail_closed(runtime)
            return prior
        attempt = self._active_finalizer_writer_attempt(change_id)
        if attempt is None or attempt.writer.attempt_id != attempt_id or attempt.writer.claim_id != claim_id:
            self._raise_finalizer_settlement_conflict(
                "stuck-worker release does not match the active Finalizer attempt"
            )
        self._require_quiet_worktree(change_id, attempt.writer.claimed_at)
        return self._settle_stalled_finalizer(runtime, attempt, "released-stuck")

    def _require_quiet_worktree(self, change_id: str, issued_at: str) -> None:
        guard = self._worker_settlement_guard(change_id, issued_at)
        if not guard.quiet:
            raise DeliveryWorkerActiveError(guard.eligible_at, guard.active_processes)

    def _active_finalizer_writer_attempt(self, change_id: str) -> ChangeFinalizationAttempt | None:
        coordination = self._coordinator.show(change_id)
        attempt = coordination.finalization_attempt
        if (
            attempt is None
            or attempt.finished_at is not None
            or attempt.writer.kind != "finalize"
            or coordination.writer != attempt.writer
        ):
            return None
        return attempt

    def _settle_stalled_finalizer(
        self,
        runtime: DeliveryRuntime,
        attempt: ChangeFinalizationAttempt,
        disposition: EngineWorkerDisposition,
    ) -> FinalizerSettlementReceipt:
        """Settle one ended Finalizer as failed attention backed by its own or an engine-authored report."""
        change_id = runtime.contract.change_id
        with self._coordinator.publication_lock(change_id) as lock:
            self._coordinator.recover_pending_transactions()
            coordination = self._coordinator.show(change_id)
            if coordination.finalization_attempt != attempt or coordination.writer != attempt.writer:
                self._raise_finalizer_settlement_conflict("Finalizer attempt changed before its stalled settlement")
            report = self._stalled_finalizer_report(coordination, attempt)
            settlement = FinalizerEngineSettlement(
                change_id=change_id,
                attempt_id=attempt.writer.attempt_id,
                claim_id=attempt.writer.claim_id,
                expected_head=attempt.exact_head,
                expected_reviewed_base=coordination.last_reviewed_commit,
                report_id=report.report_id,
                disposition=disposition,
                outcome=finalizer_settlement_outcome(report.request.category),
                host_id=attempt.writer.actor_id,
                session_id=attempt.writer.process_id,
            )
            evidence = self._finalizer_settlement_evidence(runtime, settlement, coordination, attempt)
            receipt = self._publish_finalizer_settlement(runtime, settlement, attempt, evidence, lock)
        # Readiness requires the settled failure, not only its owner result, once attention exists.
        self._reconcile_retry_results_fail_closed(runtime)
        return receipt

    def _stalled_finalizer_report(
        self, coordination: ChangeCoordination, attempt: ChangeFinalizationAttempt
    ) -> FinalizationReport:
        store = FinalizationReportStore(self._target_root, coordination.change_id)
        snapshot = store.read()
        existing = next(
            (report for report in snapshot.reports if report.request.attempt_key == attempt.writer.attempt_id), None
        )
        if existing is not None:
            return existing
        request = ReportFinalizationFailure(
            change_id=coordination.change_id,
            expected_contract_digest=attempt.contract_digest,
            expected_frontier_digest=attempt.frontier_digest,
            expected_change_head=attempt.exact_head,
            expected_reviewed_head=coordination.last_reviewed_commit,
            expected_diagnostic_sequence=snapshot.sequence,
            attempt_key=attempt.writer.attempt_id,
            category="worker-ended",
            code=FinalizationFailureCode.FINALIZER_ENDED_WITHOUT_REPORT,
            checks_state="unknown",
        )
        return store.record(request, _timestamp(self._clock()), lambda: None)

    def _engine_worker_envelope(
        self,
        runtime: DeliveryRuntime,
        outcome_id: str,
        claim: DeliveryActiveClaim,
        disposition: EngineWorkerDisposition,
    ) -> DeliveryEnginePlanningSettlement | DeliveryEngineBuilderSettlement:
        change_id = runtime.contract.change_id
        if claim.worker_role is DeliveryWorkerRole.PLANNER:
            return DeliveryEnginePlanningSettlement(
                change_id=change_id,
                outcome_id=outcome_id,
                claim_id=claim.claim_id,
                attempt_id=claim.attempt_id,
                disposition=disposition,
            )
        if claim.task_id is None:
            self._fail("Builder worker settlement requires its exact task claim")
        return DeliveryEngineBuilderSettlement(
            change_id=change_id,
            outcome_id=outcome_id,
            claim_id=claim.claim_id,
            attempt_id=claim.attempt_id,
            task_id=claim.task_id,
            expected_last_reviewed_commit=self._workspace_manager.show(change_id).last_reviewed_commit,
            disposition=disposition,
        )

    def _worker_settlement_guard(self, change_id: str, issued_at: str) -> _WorkerStall:
        """Refuse settlement while leftover processes use the worktree or it changed within the quiet period."""
        try:
            issued_after = _timestamp(issued_at)
        except ValueError, OverflowError:
            # Without the claim's issue time, no process can be ruled out as its leftover.
            return _WorkerStall(eligible_at=None, quiet=False)
        try:
            roots = self._workspace_manager.worker_process_roots(change_id)
            before = self._workspace_manager.observe_worktree_activity(change_id)
            processes = self._worktree_process_probe.active_processes(roots, issued_after=issued_after)
            if processes:
                return _WorkerStall(eligible_at=None, quiet=False, active_processes=processes)
            # A write while processes were scanned must still count against the quiet period.
            newest = max(before, self._workspace_manager.observe_worktree_activity(change_id))
        except OSError, RuntimeError, subprocess.SubprocessError, ValueError:
            return _WorkerStall(eligible_at=None, quiet=False)
        eligible_at = newest + self._worker_quiet_period
        if eligible_at.microsecond:
            eligible_at = eligible_at.replace(microsecond=0) + timedelta(seconds=1)
        return _WorkerStall(eligible_at=eligible_at, quiet=_timestamp(self._clock()) >= eligible_at)

    def _publish_claim_issuer(self, change_id: str, outcome_id: str, claim: DeliveryActiveClaim) -> None:
        self._publish_issuer(
            change_id, outcome_id, claim.attempt_id, claim.claim_id, claim.worker_role.value, claim.started_at
        )

    def _publish_issuer(  # noqa: PLR0913, PLR0917 - one immutable issuer record binds each issued identity.
        self,
        change_id: str,
        outcome_id: str | None,
        attempt_id: str,
        claim_id: str,
        role: str,
        issued_at: str,
    ) -> None:
        """Bind one issued worker identity to this process's VS Code window, if known, before dispatch."""
        if not is_issuable_attempt_id(attempt_id):
            return
        issuer = DeliveryClaimIssuer(
            change_id=change_id,
            outcome_id=outcome_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            role=role,
            window=self._issuer_window,
            issued_at=issued_at,
        )
        publish_record(self._target_root, claim_issuer_path(change_id, attempt_id), issuer)

    def _read_claim_issuer(self, change_id: str, attempt_id: str) -> DeliveryClaimIssuer | None:
        if not is_issuable_attempt_id(attempt_id):
            return None
        try:
            content = read_record(self._target_root, claim_issuer_path(change_id, attempt_id))
        except FileNotFoundError:
            return None
        return DeliveryClaimIssuer.model_validate_json(content)

    def _worker_stall(self, change_id: str, outcome_id: str, claim: DeliveryActiveClaim) -> _WorkerStall | None:
        """Return stall evidence only when the claim's recorded issuing window process is gone."""
        if claim.worker_role not in {DeliveryWorkerRole.PLANNER, DeliveryWorkerRole.BUILDER}:
            return None
        return self._issuer_stall(change_id, outcome_id, claim.attempt_id, claim.claim_id, claim.worker_role.value)

    def _finalizer_stall(self, change_id: str) -> tuple[ChangeFinalizationAttempt, _WorkerStall] | None:
        attempt = self._active_finalizer_writer_attempt(change_id)
        if attempt is None:
            return None
        stall = self._issuer_stall(change_id, None, attempt.writer.attempt_id, attempt.writer.claim_id, "finalizer")
        return None if stall is None else (attempt, stall)

    def _issuer_stall(
        self,
        change_id: str,
        outcome_id: str | None,
        attempt_id: str,
        claim_id: str,
        role: str,
    ) -> _WorkerStall | None:
        issuer = self._read_claim_issuer(change_id, attempt_id)
        if issuer is None:
            return None
        if (issuer.change_id, issuer.outcome_id, issuer.claim_id, issuer.role) != (
            change_id,
            outcome_id,
            claim_id,
            role,
        ):
            self._fail("claim issuer record does not match its active worker")
        if issuer.window is None or self._window_liveness_probe.window_state(issuer.window) != "gone":
            return None
        return self._worker_settlement_guard(change_id, issuer.issued_at)

    def _observed_worker_stalls(self, snapshot: DeliveryPortfolioSnapshot) -> dict[str, _WorkerStall]:
        stalls: dict[str, _WorkerStall] = {}
        for binding in snapshot.frontier.bindings:
            claim = binding.active_claim
            if claim is None:
                continue
            try:
                stall = self._worker_stall(snapshot.contract.change_id, binding.outcome_id, claim)
            except OSError, RuntimeError, ValueError:
                continue
            if stall is not None:
                stalls[binding.outcome_id] = stall
        return stalls

    def _settle_stalled_workers(
        self,
        change_ids: tuple[str, ...],
        *,
        checkpoint_locked: bool,
    ) -> tuple[int, tuple[DeliveryAcquisitionFailure, ...]]:
        """Settle quiet claims whose issuing window is gone; each Change fails closed independently."""
        settled = 0
        failures: list[DeliveryAcquisitionFailure] = []
        for change_id in change_ids:
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                continue
            try:
                with ExitStack() as stack:
                    if not checkpoint_locked:
                        stack.enter_context(self._selected_action_checkpoint_lock(change_id))
                    for outcome_id, claim in runtime.active_claims():
                        stall = self._worker_stall(change_id, outcome_id, claim)
                        if stall is None or not stall.quiet:
                            continue
                        with self._worker_drain_authority(runtime, outcome_id, claim.claim_id):
                            self._apply_worker_settlement(
                                runtime, self._engine_worker_envelope(runtime, outcome_id, claim, "host-lost")
                            )
                        settled += 1
                    finalizer = self._finalizer_stall(change_id)
                    if finalizer is not None and finalizer[1].quiet:
                        self._settle_stalled_finalizer(runtime, finalizer[0], "host-lost")
                        settled += 1
                    self._try_convert_pause_request(change_id, runtime)
            except DeliveryActionBusyError:
                continue
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                failures.append(
                    DeliveryAcquisitionFailure(
                        change_id=change_id,
                        outcome_id="OUT-000",
                        code=getattr(exc, "code", PortfolioApplicationError.code),
                        detail="Worker stall evidence is unavailable; active claims and worktrees are unchanged.",
                        retry_condition=(
                            "Restore readable claim-issuer and worktree evidence, or release a stopped worker "
                            "explicitly once no process uses its worktree and it stays unchanged."
                        ),
                    )
                )
        return settled, tuple(failures)

    def repair_delivery_state_snapshot(
        self,
        change_id: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
    ) -> DeliveryStateSnapshotRepairReceipt:
        """Publish one explicitly confirmed local block successor over a stale snapshot."""
        if confirmed_repair is not True:
            self._fail("Delivery-state snapshot repair requires explicit confirmation")
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("Delivery-state snapshot repair requires a configured state publisher")
        self._reconcile_runtimes()
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            inventory = publisher.read_snapshot_inventory()
            snapshot = next((item for item in inventory.snapshots if item.change_id == change_id), None)
            if snapshot is None or inventory.remote_head is None:
                self._fail("Delivery-state snapshot repair requires the current remote snapshot")
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                runtime = DeliveryRuntime(
                    self._target_root,
                    snapshot.contract,
                    workspace_manager=self._workspace_manager,
                )
            diagnostics = tuple(
                diagnostic
                for diagnostic in self._startup_health_diagnostics
                if (
                    diagnostic.source == "remote-state"
                    and diagnostic.code == "remote-state-reconciliation-required"
                    and diagnostic.change_id == change_id
                    and diagnostic.reason is DeliveryHealthReason.LOCAL_FRONTIER_MISMATCH
                )
            )
            frontier_bytes = runtime.frontier_bytes()
            frontier = parse_delivery_frontier(frontier_bytes)[0]
            if not diagnostics:
                self._fail("Delivery-state snapshot repair diagnostic is absent or incompatible")
            if not self._is_repairable_frontier_successor(snapshot.frontier, frontier):
                self._fail("Delivery-state snapshot repair successor is outside the allowed block shape")
            publication = self._publish_delivery_state(
                change_id,
                runtime,
                operation_id,
                expected_remote_head=inventory.remote_head,
            )
            if publication is None:
                self._fail("Delivery-state snapshot repair did not produce a publication receipt")
            self._clear_remote_state_reconciliation(change_id)
            return DeliveryStateSnapshotRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                publication=publication,
                local_frontier_digest=hashlib.sha256(frontier_bytes).hexdigest(),
            )

    def repair_stranded_frontier(
        self,
        change_id: str,
        request_id: str,
        expected_frontier_digest: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
    ) -> DeliveryStrandedFrontierRepairReceipt:
        """Repair one confirmed legacy request-provenance defect with CAS fencing."""
        if confirmed_repair is not True:
            self._fail("stranded frontier repair requires explicit confirmation")
        frontier_path = self._target_root / "changes" / change_id / "frontier.json"
        history_relative = Path("changes") / change_id / "revisions" / expected_frontier_digest / "frontier.json"
        history_path = self._target_root / history_relative
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            try:
                current_bytes = frontier_path.read_bytes()
            except OSError as exc:
                self._fail("stranded frontier repair requires the current frontier", exc)
            current_digest = hashlib.sha256(current_bytes).hexdigest()
            if current_digest != expected_frontier_digest:
                if not history_path.is_file():
                    self._fail("Delivery frontier changed before stranded frontier repair")
                history_bytes = history_path.read_bytes()
                if hashlib.sha256(history_bytes).hexdigest() != expected_frontier_digest:
                    self._fail("stranded frontier repair history does not match the expected frontier")
                _frontier, repaired_bytes = repair_missing_request_provenance(history_bytes, request_id)
                if current_bytes != repaired_bytes:
                    self._fail("stranded frontier repair predecessor is not the expected repaired successor")
                return DeliveryStrandedFrontierRepairReceipt.create(
                    operation_id=operation_id,
                    change_id=change_id,
                    request_id=request_id,
                    previous_frontier_digest=expected_frontier_digest,
                    frontier_digest=hashlib.sha256(repaired_bytes).hexdigest(),
                    preserved_frontier_path=history_relative.as_posix(),
                )

            _frontier, repaired_bytes = repair_missing_request_provenance(current_bytes, request_id)
            if history_path.exists() and history_path.read_bytes() != current_bytes:
                self._fail("stranded frontier repair history already contains different evidence")
            participants: list[TransactionParticipant | ReplacementTransactionParticipant] = []
            if not history_path.exists():
                participants.append(TransactionParticipant(self._target_root, history_relative, current_bytes))
            participants.append(
                ReplacementTransactionParticipant(
                    self._target_root,
                    frontier_path.relative_to(self._target_root),
                    current_bytes,
                    repaired_bytes,
                )
            )
            pending_path = frontier_path.with_name("state-publication.json")
            pending_bytes = _canonical_model_bytes(
                DeliveryPendingStatePublication.pending(
                    expected_frontier_digest,
                    hashlib.sha256(repaired_bytes).hexdigest(),
                )
            )
            if pending_path.exists():
                participants.append(
                    ReplacementTransactionParticipant(
                        self._target_root,
                        pending_path.relative_to(self._target_root),
                        pending_path.read_bytes(),
                        pending_bytes,
                    )
                )
            else:
                participants.append(
                    TransactionParticipant(
                        self._target_root,
                        pending_path.relative_to(self._target_root),
                        pending_bytes,
                    )
                )
            RuntimeTransaction(
                self._target_root,
                f"delivery-stranded-frontier-repair-{change_id}-{expected_frontier_digest}",
                tuple(participants),
            ).commit()
            self._reconcile_runtimes()
            return DeliveryStrandedFrontierRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                request_id=request_id,
                previous_frontier_digest=expected_frontier_digest,
                frontier_digest=hashlib.sha256(repaired_bytes).hexdigest(),
                preserved_frontier_path=history_relative.as_posix(),
            )

    def propose_quarantined_delivery_state_snapshot_repair(
        self,
        change_id: str,
    ) -> DeliveryQuarantinedSnapshotRepairProposal:
        """Return exact fences for one known quarantined remote snapshot."""
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("quarantined snapshot repair requires a configured state publisher")
        inventory = publisher.read_snapshot_inventory()
        diagnostics = tuple(
            item
            for item in inventory.diagnostics
            if item.change_id == change_id
            and item.code in {"snapshot-invalid", "snapshot-identity-invalid"}
            and item.raw_digest is not None
        )
        if inventory.remote_head is None or len(diagnostics) != 1:
            self._fail("no uniquely repairable quarantined remote snapshot exists")
        diagnostic = diagnostics[0]
        if diagnostic.raw_digest is None:
            self._fail("quarantined remote snapshot has no raw-byte fence")
        return DeliveryQuarantinedSnapshotRepairProposal(
            change_id=change_id,
            diagnostic_code=diagnostic.code,
            expected_remote_head=inventory.remote_head,
            snapshot_digest=diagnostic.raw_digest,
            consequence="Replace the quarantined predecessor with a fresh snapshot from validated local authority.",
        )

    def repair_quarantined_delivery_state_snapshot(  # noqa: PLR0913 - repair binds each exact authority fence.
        self,
        change_id: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
        expected_remote_head: str,
        expected_snapshot_digest: str,
        expected_diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"],
    ) -> DeliveryQuarantinedSnapshotRepairReceipt:
        """Replace one known invalid remote snapshot from validated local authority."""
        if confirmed_repair is not True:
            self._fail("quarantined snapshot repair requires explicit confirmation")
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("quarantined snapshot repair requires a configured state publisher")
        self._reconcile_runtimes()
        with (
            self._coordinator.acquisition_lock(),
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, f"quarantine-repair:{operation_id}"),
        ):
            inventory = publisher.read_snapshot_inventory()
            diagnostic = next(
                (
                    item
                    for item in inventory.diagnostics
                    if item.change_id == change_id
                    and item.code == expected_diagnostic_code
                    and item.raw_digest == expected_snapshot_digest
                ),
                None,
            )
            if diagnostic is None and inventory.remote_head == expected_remote_head:
                self._fail("expected quarantined remote snapshot diagnostic is absent")
            change_diagnostics = tuple(item for item in self._startup_health_diagnostics if item.change_id == change_id)
            if len(change_diagnostics) != 1 or not (
                change_diagnostics[0].source == "remote-state"
                and change_diagnostics[0].code == expected_diagnostic_code
            ):
                self._fail("quarantined remote snapshot repair has unrelated Change diagnostics")
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                detail = self._runtime_reconciliation_errors.get(change_id)
                if detail is not None:
                    raise DeliveryRuntimeReconciliationError(change_id, detail)
                self._fail(f"Delivery runtime is absent: {change_id}")
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            admission_path = self._target_root / "changes" / change_id / "admission.json"
            admission = DeliveryAdmissionReceipt.model_validate_json(admission_path.read_bytes())
            publication = publisher.repair_quarantined_snapshot(
                change_id=change_id,
                package_id=package.package_id,
                coordination=self._workspace_manager.show(change_id),
                runtime=runtime,
                admission=admission,
                operation_id=operation_id,
                captured_at=_timestamp(self._clock()),
                expected_remote_head=expected_remote_head,
                expected_snapshot_digest=expected_snapshot_digest,
                expected_diagnostic_code=expected_diagnostic_code,
            )
            runtime.acknowledge_pending_publication(hashlib.sha256(runtime.frontier_bytes()).hexdigest())
            self._clear_remote_state_reconciliation(change_id)
            return DeliveryQuarantinedSnapshotRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                invalid_snapshot_digest=expected_snapshot_digest,
                expected_remote_head=expected_remote_head,
                publication=publication,
                diagnostic_code=expected_diagnostic_code,
            )

    def recover_out_of_band_head(  # noqa: C901, PLR0912, PLR0913 - recovery binds exact Delivery and Git fences.
        self,
        change_id: str,
        expected_reviewed_head: str,
        expected_remote_head: str,
        expected_branch_head: str,
        operation_id: str,
        *,
        confirmed_recovery: Literal[True],
    ) -> OutOfBandHeadRecoveryReceipt:
        """Preserve an out-of-band head and reconcile the reviewed Change checkpoint."""
        if confirmed_recovery is not True:
            self._fail("out-of-band head recovery requires explicit confirmation")
        if (
            self._change_branch_publisher is None
            or self._delivery_state_publisher is None
            or self._draft_pull_request_publisher is None
        ):
            self._fail("out-of-band head recovery requires configured checkpoint publishers")
        self._reconcile_runtimes()
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(
                change_id,
                f"out-of-band-recovery:{operation_id}",
                "queue_explicit_checkpoint",
                "capture_change_disposition",
                publishes_checkpoint=True,
            ),
        ):
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                self._fail("out-of-band head recovery requires an available Change runtime")
            diagnostic = next(
                (
                    item
                    for item in self._startup_health_diagnostics
                    if (
                        item.source == "remote-state"
                        and item.change_id == change_id
                        and item.code == "remote-state-reconciliation-required"
                        and item.reason is DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH
                        and item.expected_head == expected_reviewed_head
                        and item.observed_head == expected_remote_head
                    )
                ),
                None,
            )
            if diagnostic is None:
                self._fail("out-of-band head recovery diagnostic is absent or stale")
            checkpoint = runtime.checkpoint_publication_state()
            if checkpoint.published_head != expected_remote_head:
                self._fail("out-of-band head recovery remote checkpoint changed")
            coordination = self._workspace_manager.show(change_id)
            if coordination.last_reviewed_commit != expected_reviewed_head:
                self._fail("out-of-band head recovery reviewed boundary changed")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("out-of-band head recovery cannot overlap active Delivery work")
            if runtime.finalization() is not None or runtime.change_disposition() is not None:
                self._fail("out-of-band head recovery requires an unresolved nonterminal Change")
            if self._workspace_manager.observed_change_head(change_id) != expected_branch_head:
                self._fail("out-of-band head recovery branch head changed")
            try:
                observed_remote_head = self._change_branch_publisher.observe_remote_head(change_id)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("out-of-band Change head recovery could not observe the remote branch", exc)
            if observed_remote_head != expected_remote_head:
                self._fail("out-of-band Change head recovery remote branch changed")
            request = RecoverOutOfBandHead(
                change_id=change_id,
                expected_reviewed_head=expected_reviewed_head,
                expected_remote_head=expected_remote_head,
                expected_branch_head=expected_branch_head,
                operation_id=operation_id,
            )
            try:
                receipt = self._workspace_manager.recover_out_of_band_head(request)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("out-of-band Change head recovery could not complete", exc)
            runtime.queue_explicit_checkpoint(expected_reviewed_head)
            result = self._reconcile_change_checkpoint_with_failure_recording(change_id, runtime)
            if not result.reconciled:
                self._fail("out-of-band Change head recovery checkpoint remains unreconciled")
            self._clear_remote_state_reconciliation(change_id)
            return receipt

    def repair_target_sync_publication(  # noqa: PLR0913 - repair binds each exact remote and target identity.
        self,
        change_id: str,
        expected_remote_head: str,
        expected_merged_head: str,
        target_sync_operation_id: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
    ) -> DeliveryTargetSyncRepairReceipt:
        """Reconcile one quarantined target-sync head through Delivery-owned publication."""
        if confirmed_repair is not True:
            self._fail("target-sync publication repair requires explicit confirmation")
        if self._change_branch_publisher is None or self._delivery_state_publisher is None:
            self._fail("target-sync publication repair requires configured publishers")
        self._reconcile_runtimes()
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, f"target-sync-repair:{operation_id}", publishes_checkpoint=True),
        ):
            runtime = self._target_sync_repair_runtime(
                change_id,
                expected_remote_head,
                expected_merged_head,
                target_sync_operation_id,
            )
            branch_receipt = self._publish_target_sync_branch(change_id, runtime, expected_merged_head)
            if branch_receipt is None:
                self._fail("target-sync publication repair could not publish the Change branch")
            checkpoint = runtime.checkpoint_publication_state()
            pending = checkpoint.pending_checkpoint
            self._publish_delivery_state(change_id, runtime, f"target-sync-repair-{operation_id}")
            if pending is not None and runtime.checkpoint_publication_state().pending_checkpoint is not None:
                runtime.acknowledge_checkpoint_publication(pending, branch_receipt.published_head)
            self._clear_target_sync_reconciliation(change_id)
            target_sync = runtime.target_sync_receipt()
            if target_sync is None:
                self._fail("target-sync publication repair lost target-sync authority")
            return DeliveryTargetSyncRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                target_sync_operation_id=target_sync_operation_id,
                target_branch=target_sync.integration_target,
                target_head=target_sync.target_head,
                expected_remote_head=expected_remote_head,
                repaired_head=branch_receipt.published_head,
            )

    def _target_sync_repair_runtime(
        self,
        change_id: str,
        expected_remote_head: str,
        expected_merged_head: str,
        target_sync_operation_id: str,
    ) -> DeliveryRuntime:
        runtime = self._runtimes.get(change_id)
        if runtime is None:
            self._fail("target-sync publication repair requires an available Change runtime")
        reconciliation_error = self._runtime_reconciliation_errors.get(change_id)
        matching_diagnostics = tuple(
            diagnostic
            for diagnostic in self._startup_health_diagnostics
            if (
                diagnostic.source == "remote-state"
                and diagnostic.code == "remote-state-reconciliation-required"
                and diagnostic.change_id == change_id
                and (
                    diagnostic.reason is DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH
                    or diagnostic.reason is DeliveryHealthReason.LOCAL_FRONTIER_MISMATCH
                )
            )
        )
        if reconciliation_error is not None and not matching_diagnostics:
            self._fail("target-sync publication repair diagnostic is absent or incompatible")
        if any(
            diagnostic.source == "remote-state"
            and diagnostic.change_id == change_id
            and diagnostic.code == "remote-state-reconciliation-required"
            and diagnostic not in matching_diagnostics
            for diagnostic in self._startup_health_diagnostics
        ):
            self._fail("target-sync publication repair diagnostic is absent or incompatible")
        target_sync = runtime.target_sync_receipt()
        if (
            target_sync is None
            or not target_sync.review_required
            or target_sync.operation_id != target_sync_operation_id
            or target_sync.merged_head != expected_merged_head
        ):
            self._fail("target-sync publication repair does not match current target-sync authority")
        coordination = self._workspace_manager.show(change_id)
        checkpoint = runtime.checkpoint_publication_state()
        if (
            coordination.last_reviewed_commit != expected_merged_head
            or checkpoint.published_head not in {expected_remote_head, expected_merged_head}
            or checkpoint.pending_checkpoint is None
            or checkpoint.pending_checkpoint.head != expected_merged_head
            or runtime.finalization() is not None
            or runtime.change_disposition() is not None
            or runtime.active_claims()
            or runtime.integration_repair_claim() is not None
        ):
            self._fail("target-sync publication repair authority has changed")
        if self._workspace_manager.source_head(change_id) != expected_merged_head:
            self._fail("target-sync publication repair local head differs from the expected merge")
        return runtime

    @staticmethod
    def _is_repairable_frontier_successor(  # noqa: PLR0911
        snapshot: DeliveryFrontier,
        local: DeliveryFrontier,
    ) -> bool:
        """Accept only one local block/request addition over an exact remote frontier."""
        if (
            len(snapshot.bindings) != len(local.bindings)
            or any(binding.active_claim is not None for binding in local.bindings)
            or local.integration_repair_claim is not None
        ):
            return False
        changed = 0
        for snapshot_binding, local_binding in zip(snapshot.bindings, local.bindings, strict=True):
            if snapshot_binding.outcome_id != local_binding.outcome_id:
                return False
            if snapshot_binding == local_binding:
                continue
            prior = snapshot_binding.requests
            if (
                snapshot_binding.block is not None
                or prior != retained_requests(prior)
                or local_binding.block is None
                or local_binding.requests[: len(prior)] != prior
            ):
                return False
            added = local_binding.requests[len(prior) :]
            if local_binding.block.request_id is None:
                if added:
                    return False
            elif (
                len(added) != 1
                or added[0].request_id != local_binding.block.request_id
                or added[0].outcome_id != local_binding.outcome_id
            ):
                return False
            if local_binding.model_copy(update={"block": None, "requests": prior}) != snapshot_binding:
                return False
            changed += 1
        return changed == 1

    def _clear_target_sync_reconciliation(self, change_id: str) -> None:
        self._clear_remote_state_reconciliation(change_id)

    def _clear_remote_state_reconciliation(self, change_id: str) -> None:
        self._startup_health_diagnostics = tuple(
            diagnostic
            for diagnostic in self._startup_health_diagnostics
            if not (
                diagnostic.source == "remote-state"
                and diagnostic.change_id == change_id
                and diagnostic.code
                in {
                    "remote-state-reconciliation-required",
                    "snapshot-invalid",
                    "snapshot-identity-invalid",
                    "snapshot-path-identity-mismatch",
                    "snapshot-unreadable",
                }
            )
        )
        self._runtime_reconciliation_errors.pop(change_id, None)
        self._runtime_snapshots.pop(change_id, None)
        self._reconcile_runtimes()
        if change_id in self._runtime_reconciliation_errors:
            self._fail(
                "Delivery-state reconciliation completed with remaining Change errors: "
                f"{self._runtime_reconciliation_errors[change_id]}"
            )

    def _repair_proposal(self, snapshot: DeliveryPortfolioSnapshot) -> DeliveryRepairProposal | None:
        cutoff = _timestamp(self._clock()) - self._claim_timeout
        return next(
            (
                DeliveryRepairProposal.create(
                    kind=DeliveryRepairKind.CONFIRM_LOST_WORKER,
                    change_id=snapshot.contract.change_id,
                    outcome_id=binding.outcome_id,
                    attempt_id=claim.attempt_id,
                    claim_id=claim.claim_id,
                    expected_frontier_digest=snapshot.version,
                    summary="Recovery is contained pending verified owner evidence for the stale Builder invocation.",
                    consequence=(
                        "Custody and files remain unchanged. Resume awaits independently verified host/worker closure "
                        "or exclusion and settlement; caller confirmation, timeout, or a stop assertion cannot "
                        "authorize recovery."
                    ),
                )
                for binding in snapshot.frontier.bindings
                if (claim := binding.active_claim) is not None
                and not claim.continuation
                and claim.worker_role is DeliveryWorkerRole.BUILDER
                and _timestamp(claim.started_at) <= cutoff
            ),
            None,
        )

    def _selected_change_card(
        self, snapshot: DeliveryPortfolioSnapshot, cards: tuple[WorkItemCardView, ...]
    ) -> WorkItemCardView:
        contained = next(
            (card for card in cards if card.readiness and card.readiness.reason_code == "builder-transition-contained"),
            None,
        )
        if contained is not None:
            return contained
        proposal = self._repair_proposal(snapshot)
        if proposal is not None:
            return next(card for card in cards if card.work_item_id == proposal.outcome_id)
        return next((card for card in cards if card.item_key == "publication"), cards[0])

    def repair_change(
        self,
        change_id: str,
        proposal_id: str | None = None,
        *,
        confirmed_lost: bool = False,  # noqa: ARG002 - retained request shape is not evidence.
    ) -> DeliveryRepairResult:
        """Diagnose or apply one exact stale-Builder recovery proposal."""
        if proposal_id is not None:
            replay = self._completed_claim_recovery(change_id, proposal_id=proposal_id)
            if replay is not None:
                return DeliveryRepairResult(change_id=change_id, recovery=replay)
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=proposal_id is not None)
            frontier_bytes = runtime.frontier_bytes()
            digest = hashlib.sha256(frontier_bytes).hexdigest()
            proposal = self._repair_proposal(DeliveryPortfolioSnapshot.capture(runtime.contract, frontier_bytes))
            if proposal_id is None:
                return DeliveryRepairResult(change_id=change_id, proposal=proposal)
            if proposal is None or proposal.proposal_id != proposal_id:
                self._fail("repair proposal is stale or unavailable")
            if digest != proposal.expected_frontier_digest:
                self._fail("repair proposal frontier changed")
            if proposal.kind is not DeliveryRepairKind.CONFIRM_LOST_WORKER:
                self._fail("repair proposal kind is unsupported")
            recovery = self._recover_claim(
                change_id,
                proposal.outcome_id,
                proposal.attempt_id,
                proposal.claim_id,
            )
            return DeliveryRepairResult(change_id=change_id, recovery=recovery)

    def repair(
        self,
        change_id: str,
        proposal_id: str | None = None,
        *,
        confirmed_lost: bool = False,
    ) -> DeliveryRepairResult:
        """Diagnose or apply one high-level repair proposal."""
        return self.repair_change(change_id, proposal_id, confirmed_lost=confirmed_lost)

    def repair_completed_outcome(
        self,
        change_id: str,
        request: PrepareCompletedOutcomeRepair,
    ) -> OutcomeAuthorityBinding:
        """Apply the fenced engine-derived repair-task route for a completed outcome."""
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            runtime = self._runtime(change_id, for_mutation=True, allow_finalizer=True)
            if request.outcome_id not in {binding.outcome_id for binding in runtime.bindings()}:
                self._fail("completed-outcome repair references an unknown outcome")
            replay = runtime.has_completed_outcome_repair(request)
            if not replay:
                self._validate_completed_outcome_repair_request(change_id, runtime, request)
            binding = runtime.prepare_completed_outcome_repair(request)
            # A replay after the publication acknowledgment must not invoke the
            # provider again.  An unacknowledged local intent remains retryable.
            if not replay or runtime.pending_state_publication() is not None:
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id(
                        "completed-outcome-repair", change_id, request.outcome_id, request.attempt_id
                    ),
                )
            return binding

    def _validate_completed_outcome_repair_request(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        request: PrepareCompletedOutcomeRepair,
    ) -> None:
        """Require engine-owned failure evidence before reopening completed work."""
        coordination = self._workspace_manager.show(change_id)
        writer = coordination.writer
        attempt = coordination.finalization_attempt
        if runtime.active_claims() or runtime.integration_repair_claim() is not None:
            self._fail("completed-outcome repair cannot overlap another active Delivery claim")
        if (
            attempt is None
            or attempt.writer.attempt_id != request.original_action_id
            or writer is not None
            or attempt.finished_at is None
        ):
            self._fail("completed-outcome repair requires the matching failed finalizer record")
        try:
            reports = FinalizationReportStore(self._target_root, change_id).read().reports
            preservation = self._workspace_manager.verify_preservation(change_id, request.preservation_id)
        except (FinalizationReportError, OSError, RuntimeError, ValueError) as exc:
            self._fail("completed-outcome repair evidence is unavailable", exc)
        matching = tuple(report for report in reports if report.request.attempt_key == request.original_action_id)
        if not matching:
            self._fail("completed-outcome repair requires a recorded finalization failure")
        report = matching[-1]
        if (
            report.request.change_id != change_id
            or report.request.code.value != request.defect_code
            or report.request.expected_frontier_digest != request.expected_frontier_digest
            or report.request.expected_contract_digest != contract_fingerprint(runtime.contract)
            or report.request.expected_change_head != attempt.exact_head
        ):
            self._fail("completed-outcome repair defect is not derived from the finalization failure")
        if request.finding_boundary == "proof-procedure":
            self._validate_proof_procedure_repair(change_id, report)
        if request.finding_boundary == "implementation" and report.request.category == "proof-mutation":
            self._fail("implementation repair cannot consume a proof-procedure diagnostic")
        if preservation.preservation_id != request.preservation_id:
            self._fail("completed-outcome repair preservation identity is stale")
        if runtime.change_stage() is DeliveryChangeStage.COMPLETED:
            self._fail("completed-outcome repair requires a nonterminal Change")
        self._validate_completed_outcome_repair_retry(runtime, request)

    def _require_owner_proof_attempt(self, change_id: str, report: FinalizationReport) -> None:
        """Require owner evidence before classifying a mutation as procedure repair."""
        factory = getattr(self, "_proof_attempt_store_factory", None)
        if factory is None:
            self._fail("proof-procedure repair owner observation is unavailable")
        try:
            proof_store = factory(change_id)
            proof_attempts = proof_store.read()
        except (FinalizationReportError, OSError, RuntimeError, ValueError) as exc:
            self._fail("proof-procedure repair owner observation is unavailable", exc)
        matching_attempts = tuple(
            attempt
            for attempt in proof_attempts
            if (
                attempt.change_id == change_id
                and proof_store.is_current(attempt)
                and attempt.attempt_key == report.request.attempt_key
                and attempt.procedure_id == report.request.procedure_id
                and attempt.expected_contract_digest == report.request.expected_contract_digest
                and attempt.expected_frontier_digest == report.request.expected_frontier_digest
                and attempt.expected_change_head == report.request.expected_change_head
                and attempt.expected_reviewed_head == report.request.expected_reviewed_head
                and attempt.proof_fingerprint_before == report.request.proof_fingerprint_before
                and attempt.proof_fingerprint_after == report.request.proof_fingerprint_after
                and attempt.paths == report.request.paths
            )
        )
        if len(matching_attempts) != 1:
            self._fail("proof-procedure repair requires owner-observed proof attempt")

    def _validate_proof_procedure_repair(self, change_id: str, report: FinalizationReport) -> None:
        """Require a mutation report and current owner observation for procedure repair."""
        if report.request.category != "proof-mutation":
            self._fail("proof-procedure repair requires a proof-mutation diagnostic")
        self._require_owner_proof_attempt(change_id, report)

    def _validate_completed_outcome_repair_retry(
        self,
        runtime: DeliveryRuntime,
        request: PrepareCompletedOutcomeRepair,
    ) -> None:
        """Require a pending mechanical repair reservation for the failed finalizer episode."""
        try:
            ledger = runtime.retry_ledger(clock=self._clock)
            summary = ledger.read()
            pending = ledger.pending_attempts()
        except (OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError) as exc:
            self._fail("completed-outcome repair retry authority is unavailable", exc)
        episodes = tuple(episode for episode in summary.episodes if request.original_action_id in episode.attempt_ids)
        if len(episodes) != 1:
            self._fail("completed-outcome repair is not bound to one retry episode")
        episode = episodes[0]
        if (
            request.episode_id != episode.episode_id
            or episode.failure_class is not RetryFailureClass.MECHANICAL
            or digest(f"{request.original_action_id}:failed".encode()) not in episode.outcome_ids
        ):
            self._fail("completed-outcome repair does not match the failed retry episode")
        repair_attempts = tuple(item for item in pending if item.attempt_id == request.attempt_id)
        if (
            len(repair_attempts) != 1
            or repair_attempts[0].episode_id != episode.episode_id
            or repair_attempts[0].kind != "repair"
            or repair_attempts[0].failure_class is not RetryFailureClass.MECHANICAL
        ):
            self._fail("completed-outcome repair requires a pending mechanical retry reservation")

    def _unavailable_change(
        self, change_id: str, reason: Literal["runtime-unavailable", "coordination-unavailable"] = "runtime-unavailable"
    ) -> DeliveryUnavailableChangeView:
        observation = self._discovered_changes.get(change_id)
        runtime = self._runtimes.get(change_id)
        contract = (
            observation.contract if observation is not None else runtime.contract if runtime is not None else None
        )
        coordination_status = None
        if reason == "coordination-unavailable":
            try:
                if self._coordinator.find_registered(change_id) is None:
                    coordination_status = "missing"
            except OSError, RuntimeError, ValueError:
                coordination_status = "unreadable"
        return DeliveryUnavailableChangeView(
            change_id=change_id,
            title=contract.title if contract is not None else None,
            diagnostics=(reason,),
            coordination_status=coordination_status,
            readiness=DeliveryReadiness(
                status="unavailable",
                next_actor=WorkItemNextActor.NONE,
                reason_code=reason,
                checks_state="unknown",
                basis=DeliveryReadinessBasis(contract_digest=contract_fingerprint(contract) if contract else None),
                prompt=(
                    f"Do not release, retry, or redispatch Change {change_id}: canonical Delivery authority "
                    f"is unavailable ({reason}); checks are unknown. Preserve existing custody and journals. "
                    f"Use /repair-delivery Diagnose Change {change_id} read-only; preserve existing custody and "
                    "journals. This does not repair authority or prove host/worker closure; the responsible owner "
                    "must resolve the condition separately before Delivery rereads it."
                ),
                progress=DeliveryProgress(
                    situation="needs-attention",
                    headline="Delivery cannot read this Change's state; diagnose it before continuing.",
                    waiting_on="you",
                ),
            ),
        )

    def recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        *,
        confirmed_lost: bool = False,  # noqa: ARG002 - retained request shape is not evidence.
    ) -> DeliveryClaimRecoveryResult:
        """Reject assertion-only recovery without releasing an exact active claim."""
        replay = self._completed_claim_recovery(change_id, identity=(outcome_id, attempt_id, claim_id))
        if replay is not None:
            return replay
        with self._coordinator.acquisition_lock():
            return self._recover_claim(change_id, outcome_id, attempt_id, claim_id)

    def recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        """Reject legacy Integration recovery without verified worker exclusion."""
        with self._coordinator.acquisition_lock():
            return self._recover_integration_repair_claim(change_id, attempt_id, claim_id)

    def _recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        runtime = self._runtime(change_id, for_mutation=True)
        runtime.require_integration_repair_claim(attempt_id, claim_id)
        raise DeliveryWorkerExclusionRequiredError

    def _recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryClaimRecoveryResult:
        runtime = self._runtime(change_id, for_mutation=True)
        runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        raise DeliveryWorkerExclusionRequiredError

    def _register_recovery_invocation(  # noqa: PLR0913, PLR0917 - exact engine-issued custody and resource binding.
        self,
        runtime: DeliveryRuntime,
        owner_id: str,
        attempt_id: str,
        kind: str,
        exact_head: str,
        outcome_id: str | None = None,
    ) -> None:
        """Capture host provenance at issuance, before a claim can be dispatched."""
        if isinstance(self._recovery_evidence_provider, UnavailableRecoveryEvidenceProvider):
            return
        coordination = self._coordinator.show(runtime.contract.change_id)
        request = RecoveryInvocationRequest(
            change_id=runtime.contract.change_id,
            owner_id=owner_id,
            attempt_id=attempt_id,
            outcome_id=outcome_id,
            kind=kind,
            contract_digest=contract_fingerprint(runtime.contract),
            exact_head=exact_head,
            target_head=self._workspace_manager.observed_target_head(),
            branch=coordination.branch,
            worktree=str(coordination.worktree_path),
            repository=str(self._workspace_manager.repository),
            runtime_root=str(self._target_root),
            integration_target=coordination.integration_target,
            publication_repository=(
                self._draft_pull_request_publisher.repository
                if self._draft_pull_request_publisher is not None
                else None
            ),
        )
        invocation = self._recovery_evidence_provider.register(request)
        if invocation is None:
            return
        if not isinstance(invocation, RecoveryInvocation) or invocation.request != request:
            raise DeliveryWorkerExclusionRequiredError
        publish_record(self._target_root, invocation_path(request), invocation)

    def _propose_recovery(self, change_id: str) -> RecoveryIntent:
        """Internal owner path: capture exact custody, without waiting for host closure."""
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(change_id),
            self._coordinator.recovery_lock(change_id),
        ):
            intent = self._capture_recovery_intent(change_id)
            path = journal_path(change_id, intent.recovery_id, "intent")
            directory = self._target_root / path.parent.parent
            if (
                directory.exists()
                and len(tuple(directory.iterdir())) >= MAX_RECOVERY_INTENTS
                and not (self._target_root / path).exists()
            ):
                raise DeliveryWorkerExclusionRequiredError
            self._coordinator.record_recovery_intent(intent)
            return intent

    @staticmethod
    def _recovery_admitted_task(
        runtime: DeliveryRuntime,
        owner: ChangeContinuationAction | ChangeFinalizationAttempt | DeliveryActiveClaim,
        kind: str,
    ) -> DeliveryTaskDefinition | None:
        if kind != "clean-claim" or not isinstance(owner, DeliveryActiveClaim) or owner.task_id is None:
            return None
        binding = next((candidate for candidate in runtime.bindings() if candidate.active_claim == owner), None)
        if binding is None:
            raise DeliveryWorkerExclusionRequiredError
        task = next((candidate for candidate in binding.tasks if candidate.task_id == owner.task_id), None)
        if task is None:
            raise DeliveryWorkerExclusionRequiredError
        return task

    @staticmethod
    def _exact_task_scope_details(
        task: DeliveryTaskDefinition,
        worktree: Path,
        baseline_kinds: dict[str, str] | None = None,
    ) -> tuple[tuple[str, ...], dict[str, Literal["directory", "file", "missing"]]]:
        surfaces = tuple(task.maintained_surfaces)
        if len(surfaces) != len(set(surfaces)):
            raise DeliveryWorkerExclusionRequiredError
        if baseline_kinds is not None and (
            set(baseline_kinds) != set(surfaces)
            or any(kind not in {"directory", "file", "missing"} for kind in baseline_kinds.values())
        ):
            raise DeliveryWorkerExclusionRequiredError
        kinds: dict[str, Literal["directory", "file", "missing"]] = {}
        for surface in surfaces:
            path = PurePosixPath(surface)
            if not is_canonical_admitted_path(surface):
                raise DeliveryWorkerExclusionRequiredError
            candidate = worktree
            try:
                for part in path.parts:
                    candidate /= part
                    metadata = candidate.lstat()
                    if stat.S_ISLNK(metadata.st_mode):
                        raise DeliveryWorkerExclusionRequiredError
            except FileNotFoundError:
                baseline_kind = (baseline_kinds or {}).get(surface, "missing")
                kinds[surface] = baseline_kind
                continue
            except OSError as exc:
                raise DeliveryWorkerExclusionRequiredError from exc
            observed_kind = "directory" if stat.S_ISDIR(metadata.st_mode) else "file"
            baseline_kind = (baseline_kinds or {}).get(surface)
            if baseline_kind in {"directory", "file"} and observed_kind != baseline_kind:
                raise DeliveryWorkerExclusionRequiredError
            kinds[surface] = observed_kind
        return tuple(sorted(surfaces)), kinds

    @staticmethod
    def _scope_admits_path(
        worktree: Path,
        scope: str,
        path: str,
        *,
        scope_kind: Literal["directory", "file", "missing"] | None = None,
    ) -> bool:
        scope_parts = PurePosixPath(scope).parts
        path_parts = PurePosixPath(path).parts
        if path_parts == scope_parts:
            return True
        if len(path_parts) <= len(scope_parts) or path_parts[: len(scope_parts)] != scope_parts:
            return False
        if scope_kind is not None:
            return scope_kind == "directory"
        try:
            metadata = (worktree / PurePosixPath(scope)).lstat()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        if stat.S_ISLNK(metadata.st_mode):
            return False
        return stat.S_ISDIR(metadata.st_mode)

    def _capture_recovery_intent(self, change_id: str) -> RecoveryIntent:
        self._workspace_manager.require_preservation_environment()
        runtime = self._runtime(change_id)
        frontier = parse_delivery_frontier(runtime.frontier_bytes())[0]
        coordination = self._coordinator.show(change_id)
        owner, owner_id, kind, failure_id, effect_id = self._recovery_owner(runtime, coordination)
        admitted_task = self._recovery_admitted_task(runtime, owner, kind)
        coordination, head, _status, paths, reason = self._workspace_manager.capture_recovery_workspace_metadata(
            change_id, tuple(result.completed_commit for binding in frontier.bindings for result in binding.results)
        )
        # Recovery A never rewrites files, moves heads, repairs corruption, or interprets
        # unpromoted output as proof of a completed effect.
        if reason not in {None, "workspace-dirty"} or coordination.publication_lease is not None:
            raise DeliveryWorkerExclusionRequiredError
        baseline_kinds = (
            self._workspace_manager.baseline_scope_kinds(
                coordination.worktree_path,
                head,
                tuple(admitted_task.maintained_surfaces),
            )
            if admitted_task is not None and paths
            else None
        )
        scope_details = (
            self._exact_task_scope_details(admitted_task, coordination.worktree_path, baseline_kinds)
            if admitted_task is not None and paths
            else None
        )
        (
            admitted_task_id,
            admitted_task_digest,
            admitted_task_scope,
            admitted_paths,
        ) = self._recovery_admission_fields(
            admitted_task,
            paths,
            coordination.worktree_path,
            scope_details=scope_details,
        )
        if (
            scope_details is not None
            and self._exact_task_scope_details(admitted_task, coordination.worktree_path, baseline_kinds)
            != scope_details
        ):
            raise DeliveryWorkerExclusionRequiredError
        coordination, head, fingerprint, captured_paths, reason = self._workspace_manager.capture_recovery_workspace(
            change_id,
            tuple(result.completed_commit for binding in frontier.bindings for result in binding.results),
            expected_paths=paths,
            expected_scope_details=scope_details,
        )
        if captured_paths != paths or reason not in {None, "workspace-dirty"}:
            raise DeliveryWorkerExclusionRequiredError
        relative = Path("changes") / change_id / "invocations" / f"{digest(owner_id.encode())}.json"
        try:
            invocation = RecoveryInvocation.model_validate_json(read_record(self._target_root, relative))
        except (OSError, ValueError) as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        request = invocation.request
        if (
            request.change_id != change_id
            or request.owner_id != owner_id
            or request.contract_digest != contract_fingerprint(runtime.contract)
            or request.exact_head != head
            or request.target_head != self._workspace_manager.observed_target_head()
            or request.worktree != str(coordination.worktree_path)
            or request.branch != coordination.branch
            or request.repository != str(self._workspace_manager.repository)
            or request.runtime_root != str(self._target_root)
            or request.integration_target != coordination.integration_target
            or request.publication_repository
            != (
                self._draft_pull_request_publisher.repository
                if self._draft_pull_request_publisher is not None
                else None
            )
        ):
            raise DeliveryWorkerExclusionRequiredError
        expected_kind = {"clean-claim": "claim", "clean-finalizer": "finalizer", "ready-readback": "mark-ready"}[kind]
        expected_attempt = (
            owner.operation_id
            if kind == "ready-readback"
            else (owner.writer.attempt_id if kind == "clean-finalizer" else owner.attempt_id)
        )
        if request.kind != expected_kind or request.attempt_id != expected_attempt:
            raise DeliveryWorkerExclusionRequiredError
        if kind == "clean-claim":
            binding = runtime.require_active_claim(request.outcome_id, request.attempt_id, request.owner_id)
            if binding.active_claim != owner:
                raise DeliveryWorkerExclusionRequiredError
        proposal = self._repair_proposal(DeliveryPortfolioSnapshot.capture(runtime.contract, runtime.frontier_bytes()))
        result_digest = (
            self._recovery_ready_result_digest(change_id, request.owner_id) if kind == "ready-readback" else None
        )
        maintained_surfaces = tuple(
            sorted(
                {
                    surface
                    for binding in runtime.bindings()
                    for task in binding.tasks
                    for surface in task.maintained_surfaces
                }
            )
        )
        last_write_provenance = tuple(
            sorted(
                {
                    f"change-head:{head}",
                    f"frontier:{digest(runtime.frontier_bytes())}",
                    f"owner:{owner_id}",
                    f"attempt:{request.attempt_id}",
                    *(
                        f"result:{result.result_id}:{result.completed_commit}"
                        for binding in runtime.bindings()
                        for result in binding.results
                    ),
                }
            )
        )
        return RecoveryIntent(
            invocation=invocation,
            frontier_digest=digest(runtime.frontier_bytes()),
            coordination_digest=recovery_authority_digest(
                ChangeCoordination.model_validate_json(
                    self._coordinator.recovery_coordination_bytes(change_id, owner_id)
                )
            ),
            exact_head=head,
            target_head=request.target_head,
            workspace_fingerprint=fingerprint,
            owner_record=owner.model_dump_json(),
            failure_id=failure_id,
            effect_receipt_id=effect_id,
            kind=kind,
            proposal_id=proposal.proposal_id if proposal is not None else None,
            engine_result_digest=result_digest,
            maintained_surfaces=maintained_surfaces,
            last_write_provenance=last_write_provenance,
            admitted_task_id=admitted_task_id,
            admitted_task_digest=admitted_task_digest,
            admitted_task_scope=admitted_task_scope,
            admitted_paths=admitted_paths,
        )

    def _recovery_owner(
        self, runtime: DeliveryRuntime, coordination: ChangeCoordination
    ) -> tuple[
        ChangeContinuationAction | ChangeFinalizationAttempt | DeliveryActiveClaim, str, str, str | None, str | None
    ]:
        claims = runtime.active_claims()
        action = coordination.continuation_action
        if runtime.integration_repair_claim() is not None:
            raise DeliveryWorkerExclusionRequiredError
        if action is not None and action.finished_at is None:
            ready = runtime.ready_receipt()
            if (
                claims
                or coordination.writer is not None
                or action.kind != "mark-ready"
                or ready is None
                or ready.operation_id != action.operation_id
                or ready.finalization_id != action.finalization_id
                or ready.head_sha != action.exact_head
                or runtime.pending_state_publication() is not None
                or runtime.checkpoint_publication_state().pending_checkpoint is not None
            ):
                raise DeliveryWorkerExclusionRequiredError
            path = self._coordinator.continuation_record_path(action.change_id, action.operation_id)
            original = path.read_bytes()
            if (
                ChangeContinuationAction.model_validate_json(original) != action
                or path.with_name("started.json").read_bytes() != original
            ):
                raise DeliveryWorkerExclusionRequiredError
            return action, action.operation_id, "ready-readback", action.operation_id, ready.receipt_id
        attempt = coordination.finalization_attempt
        if coordination.writer is not None and coordination.writer.kind == "finalize":
            if claims or attempt is None or attempt.writer != coordination.writer or attempt.finished_at is not None:
                raise DeliveryWorkerExclusionRequiredError
            reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read().reports
            report = next((item for item in reports if item.request.attempt_key == attempt.writer.attempt_id), None)
            if report is None:
                raise DeliveryWorkerExclusionRequiredError
            return attempt, attempt.writer.claim_id, "clean-finalizer", report.report_id, None
        if len(claims) != 1:
            raise DeliveryWorkerExclusionRequiredError
        outcome_id, claim = claims[0]
        binding = runtime.show_binding(outcome_id)
        writer = coordination.writer
        if (
            binding.output is not None
            or binding.result_candidate is not None
            or binding.candidate is not None
            or (
                writer is not None
                and (
                    writer.claim_id != claim.claim_id or writer.attempt_id != claim.attempt_id or writer.kind != "build"
                )
            )
        ):
            raise DeliveryWorkerExclusionRequiredError
        return claim, claim.claim_id, "clean-claim", claim.attempt_id, None

    def _recovery_ready_result_digest(self, change_id: str, owner_id: str) -> str:
        result = self._read_engine_result(ExecuteDeliveryChangeAction(change_id=change_id, operation_id=owner_id))
        if result is not None and result.kind != "blocked":
            raise DeliveryWorkerExclusionRequiredError
        path = self._coordinator.continuation_record_path(change_id, owner_id, result=True)
        return digest(path.read_bytes() if result is not None else b"")

    def _complete_recovery(
        self, change_id: str, recovery_id: str, reference: RecoveryEvidenceReference
    ) -> RecoveryReceipt:
        """Verify outside locks, then CAS receipt and release in one runtime transaction."""
        intent_path = journal_path(change_id, recovery_id, "intent")
        intent = RecoveryIntent.model_validate_json(read_record(self._target_root, intent_path))
        if intent.recovery_id != recovery_id or intent.invocation.request.change_id != change_id:
            raise DeliveryWorkerExclusionRequiredError
        evidence = verify_evidence(self._recovery_evidence_provider, reference, intent)
        receipt_path = self._target_root / journal_path(change_id, recovery_id, "receipt")
        self._coordinator.recover_pending_transactions()
        if receipt_path.exists():
            return self._verified_recovery_replay(intent, evidence, receipt_path)
        observation_id = self._readback_recovery_ready(intent) if intent.kind == "ready-readback" else None
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(change_id),
            self._coordinator.recovery_lock(change_id),
        ):
            self._coordinator.recover_pending_transactions()
            if receipt_path.exists():
                return self._verified_recovery_replay(intent, evidence, receipt_path)
            self._coordinator.forget_verified_exclusion(recovery_id)
            if intent.admitted_task_id is None:
                self._require_legacy_recovery_clean(change_id)
            current_intent = self._capture_recovery_intent(change_id)
            if intent.admitted_task_id is None and current_intent.admitted_paths:
                raise DeliveryWorkerExclusionRequiredError
            if not intent.authority_matches(current_intent):
                raise DeliveryWorkerExclusionRequiredError
            evidence_path = journal_path(change_id, recovery_id, "evidence")
            if (self._target_root / evidence_path).exists():
                recorded = RecoveryEvidence.model_validate_json(read_record(self._target_root, evidence_path))
                self._require_revalidated_evidence(recorded, evidence)
                evidence = recorded
            publish_record(self._target_root, evidence_path, evidence)
            receipt = RecoveryReceipt(
                recovery_id=recovery_id,
                evidence=evidence,
                finished_at=self._clock(),
                owner_effect="ready-receipt-readback" if intent.kind == "ready-readback" else "no-workspace-effect",
                owner_observation_id=observation_id,
            )
            self._runtime(change_id).complete_recovery(intent, receipt)
            self._record_retry_release(self._runtime(change_id), attempt_id=intent.invocation.request.attempt_id)
            self._coordinator.record_verified_exclusion(recovery_id)
            self._try_convert_pause_request(change_id)
            return receipt

    def _require_legacy_recovery_clean(self, change_id: str) -> None:
        """Contain old journals to clean recovery until path admission exists."""
        runtime = self._runtime(change_id)
        frontier = parse_delivery_frontier(runtime.frontier_bytes())[0]
        _coordination, _head, status, paths, reason = self._workspace_manager.capture_recovery_workspace_metadata(
            change_id,
            tuple(result.completed_commit for binding in frontier.bindings for result in binding.results),
        )
        # A legacy journal has no persisted path authority.  The metadata
        # capture deliberately does not expose ignored paths, so retain the
        # stronger guard reason as well as the ordinary dirty inventory.
        if status or paths or reason is not None:
            raise DeliveryWorkerExclusionRequiredError

    def _verified_recovery_replay(
        self, intent: RecoveryIntent, evidence: RecoveryEvidence, path: Path
    ) -> RecoveryReceipt:
        receipt = RecoveryReceipt.model_validate_json(
            read_record(self._target_root, path.relative_to(self._target_root))
        )
        request = intent.invocation.request
        self._require_revalidated_evidence(receipt.evidence, evidence)
        runtime = self._runtime(request.change_id)
        coordination = self._coordinator.show(request.change_id)
        action = coordination.continuation_action
        writer = coordination.writer
        if (
            receipt.recovery_id != intent.recovery_id
            or receipt.owner_effect
            != ("ready-receipt-readback" if intent.kind == "ready-readback" else "no-workspace-effect")
            or any(claim.claim_id == request.owner_id for _, claim in runtime.active_claims())
            or coordination.recovery_owner_id == request.owner_id
            or (writer is not None and writer.claim_id == request.owner_id)
            or (action is not None and action.operation_id == request.owner_id and action.finished_at is None)
        ):
            raise DeliveryWorkerExclusionRequiredError
        self._coordinator.record_verified_exclusion(intent.recovery_id)
        self._record_retry_release(runtime, attempt_id=request.attempt_id)
        return receipt

    @staticmethod
    def _require_revalidated_evidence(recorded: RecoveryEvidence, current: RecoveryEvidence) -> None:
        if (
            recorded.model_copy(update={"status": current.status}) != current
            or recorded.status not in {"closed", "excluded"}
            or (recorded.status == "closed" and current.status != "closed")
        ):
            raise DeliveryWorkerExclusionRequiredError

    def _completed_claim_recovery(
        self, change_id: str, *, identity: tuple[str, str, str] | None = None, proposal_id: str | None = None
    ) -> DeliveryClaimRecoveryResult | None:
        """Public forms may only replay an independently verified completed exact receipt."""
        root = self._target_root / journal_path(change_id, "0" * 64, "intent").parent.parent
        self._coordinator.recover_pending_transactions()
        if not root.exists():
            return None
        paths = tuple(root.iterdir())
        if len(paths) > MAX_RECOVERY_INTENTS:
            raise DeliveryWorkerExclusionRequiredError
        for path in paths:
            receipt_path = self._target_root / journal_path(change_id, path.name, "receipt")
            if not receipt_path.exists():
                continue
            intent = RecoveryIntent.model_validate_json(
                read_record(self._target_root, journal_path(change_id, path.name, "intent"))
            )
            request = intent.invocation.request
            if (
                intent.kind != "clean-claim"
                or intent.recovery_id != path.name
                or request.change_id != change_id
                or (identity is not None and identity != (request.outcome_id, request.attempt_id, request.owner_id))
                or (proposal_id is not None and intent.proposal_id != proposal_id)
            ):
                continue
            receipt = RecoveryReceipt.model_validate_json(
                read_record(self._target_root, journal_path(change_id, path.name, "receipt"))
            )
            self._coordinator.forget_verified_exclusion(intent.recovery_id)
            evidence = verify_evidence(self._recovery_evidence_provider, receipt.evidence.reference, intent)
            self._verified_recovery_replay(intent, evidence, receipt_path)
            return self._recovered(change_id, request.outcome_id, request.attempt_id, request.owner_id)
        return None

    def _readback_recovery_ready(self, intent: RecoveryIntent) -> str:
        """Reconcile only a fully recorded ready effect; never invoke the mutation again."""
        change_id = intent.invocation.request.change_id
        publisher = self._draft_pull_request_publisher
        ready = self._runtime(change_id).ready_receipt()
        if publisher is None or ready is None or ready.receipt_id != intent.effect_receipt_id:
            raise DeliveryWorkerExclusionRequiredError
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            raise DeliveryWorkerExclusionRequiredError
        snapshot = observation.snapshot
        if (
            snapshot.repository != ready.repository
            or snapshot.number != ready.number
            or snapshot.node_id != ready.node_id
            or snapshot.head_sha != intent.exact_head
            or snapshot.base_branch != publisher.target_branch
            or snapshot.draft
            or snapshot.state != "open"
            or snapshot.merged
        ):
            raise DeliveryWorkerExclusionRequiredError
        return observation.observation_id
