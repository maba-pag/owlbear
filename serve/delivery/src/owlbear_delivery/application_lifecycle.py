"""Finalization, finalizer settlement, Change intents and worktree cleanup."""

from __future__ import annotations

import hashlib
import subprocess
import time
from contextlib import ExitStack, contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from owlbear_delivery.application_models import (
    DeliveryActionBusyError,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryFinalizationContext,
    DeliveryRetainedChangeWorktree,
    PortfolioApplicationError,
    _FinalizationReadUnavailableError,
)
from owlbear_delivery.application_support import (
    _ATTENTION_RESOLUTION_LOCK_RETRY_SECONDS,
    _ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS,
    _canonical_model_bytes,
    _logger,
    _timestamp,
)
from owlbear_delivery.change_workspace import (
    ChangeCoordination,
    ChangeFinalizationAttempt,
    ChangeFinalizationAttention,
    ChangeWorktreeAttentionError,
    CoordinationConflictError,
    PublicationBaselineRecoveryReceipt,
    PublicationLock,
    TargetSyncConflictRequest,
)
from owlbear_delivery.delivery_contract_discovery import (
    contract_fingerprint,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryActionSelectionConflictError,
    DeliveryChangeAbandonment,
    DeliveryChangeDeferral,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionResolution,
    DeliveryChangeStage,
    DeliveryCheckpointPublicationState,
    DeliveryFinalizationReceipt,
    DeliveryRuntime,
    FinalizeDeliveryChange,
)
from owlbear_delivery.finalization_reports import (
    ENGINE_FINALIZATION_CATEGORIES,
    FinalizationReport,
    FinalizationReportError,
    FinalizationReportStore,
    FinalizerSettlement,
    FinalizerSettlementReceipt,
    FinalizerWorkspaceObservation,
    ReportFinalizationFailure,
    finalizer_settlement_outcome,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    read_record,
)
from owlbear_delivery.runtime_transaction import (
    RuntimeTransaction,
    TransactionParticipant,
)
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.work_items import (
    DeliveryReadiness,
    DeliveryReadinessBasis,
    WorkItemActionKind,
    WorkItemNextActor,
    resolve_publication_phase,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class _LifecycleMixin:
    """Finalization, finalizer settlement, Change intents and worktree cleanup."""

    def show_change_checkpoint_publication(self, change_id: str) -> DeliveryCheckpointPublicationState:
        """Return the durable checkpoint queue for one admitted Change."""
        return self._runtime(change_id).checkpoint_publication_state()

    def list_retained_change_worktrees(self) -> tuple[DeliveryRetainedChangeWorktree, ...]:
        """List retained Change worktrees and exact cleanup eligibility facts."""
        self._reconcile_runtimes()
        return tuple(self._retained_change_worktree_view(item) for item in self._workspace_manager.list_retained())

    def recover_change_worktree(
        self,
        change_id: str,
        recovery_reviewed_head: str,
        *,
        confirmed_recovery: Literal[True],
    ) -> DeliveryChangeWorktreeRecovery:
        """Recreate one missing Change worktree from explicit reviewed authority."""
        if confirmed_recovery is not True:
            self._fail("Change worktree recovery requires explicit confirmation")
        runtime = self._runtime(change_id, for_mutation=True, allow_finalizer=True)
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                raise DeliveryWorkerExclusionRequiredError
            try:
                coordination = self._workspace_manager.recover(change_id, recovery_reviewed_head)
                branch_head = self._workspace_manager.observed_change_head(change_id)
            except ChangeWorktreeAttentionError:
                raise
            except CoordinationConflictError:
                raise
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("Change worktree recovery could not complete", exc)
        return DeliveryChangeWorktreeRecovery(
            change_id=coordination.change_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            branch_head=branch_head,
            recovery_reviewed_head=recovery_reviewed_head,
        )

    def cleanup_change_worktree(
        self,
        change_id: str,
        expected_completion_id: str | None = None,
    ) -> DeliveryChangeWorktreeCleanup:
        """Clean one terminal Change worktree after exact lifecycle validation."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return self._cleanup_change_worktree_locked(change_id, runtime, expected_completion_id)

    def _cleanup_change_worktree_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        expected_completion_id: str | None = None,
    ) -> DeliveryChangeWorktreeCleanup:
        """Clean one terminal Change worktree while its checkpoint lock is held."""
        lifecycle = runtime.change_stage()
        completion = runtime.completion_receipt()
        completed = lifecycle == DeliveryChangeStage.COMPLETED and completion is not None
        if lifecycle != DeliveryChangeStage.ABANDONED and not completed:
            self._fail("Change worktree cleanup requires an abandoned or completed Change")
        if expected_completion_id is not None and (not completed or completion.completion_id != expected_completion_id):
            self._fail("completed Change worktree cleanup requires the exact completion receipt")
        try:
            receipt = self._workspace_manager.cleanup(change_id)
        except ChangeWorktreeAttentionError:
            raise
        except CoordinationConflictError:
            raise
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("Change worktree cleanup could not complete", exc)
        return DeliveryChangeWorktreeCleanup(
            cleanup_id=receipt.cleanup_id,
            change_id=receipt.change_id,
            branch=receipt.branch,
            worktree_path=receipt.worktree_path,
            branch_head=receipt.branch_head,
        )

    def cleanup_abandoned_change_worktree(self, change_id: str) -> DeliveryChangeWorktreeCleanup:
        """Clean one abandoned Change worktree without reopening its terminal state."""
        runtime = self._runtime(change_id, for_mutation=True)
        if runtime.change_stage() != DeliveryChangeStage.ABANDONED:
            self._fail("abandoned Change worktree cleanup requires an abandoned Change")
        return self.cleanup_change_worktree(change_id)

    def cleanup_abandoned_change_worktree_after_target_sync_discard(
        self,
        change_id: str,
        *,
        confirmed_discard: Literal[True],
        expected_target_head: str,
        expected_operation_id: str,
    ) -> DeliveryChangeWorktreeCleanup:
        """Discard one abandoned target merge and then clean its exact Change worktree."""
        if confirmed_discard is not True:
            self._fail("discarding an abandoned target synchronization conflict requires explicit confirmation")
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            if runtime.change_stage() != DeliveryChangeStage.ABANDONED:
                self._fail("abandoned target synchronization conflict cleanup requires an abandoned Change")
            coordination = self._workspace_manager.show(change_id)
            self._discard_abandoned_target_sync_conflict(
                change_id,
                coordination,
                expected_target_head,
                expected_operation_id,
            )
            return self._cleanup_change_worktree_locked(change_id, runtime)

    def _discard_abandoned_target_sync_conflict(
        self,
        change_id: str,
        coordination: ChangeCoordination,
        expected_target_head: str,
        expected_operation_id: str,
    ) -> None:
        conflict = coordination.target_sync_conflict
        if conflict is None:
            return
        if conflict.target_head != expected_target_head or conflict.operation_id != expected_operation_id:
            self._fail("abandoned target synchronization conflict evidence is stale")
        retained = next(
            (item for item in self._workspace_manager.list_retained() if item.change_id == change_id),
            None,
        )
        if retained is None:
            self._fail("abandoned target synchronization conflict worktree is not registered")
        if not retained.worktree_present or not retained.git_registered:
            try:
                coordination = self._workspace_manager.recover(
                    change_id,
                    coordination.last_reviewed_commit,
                )
            except ChangeWorktreeAttentionError:
                raise
            except CoordinationConflictError:
                raise
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("abandoned target synchronization conflict worktree could not be recovered", exc)
        try:
            self._workspace_manager.abort_target_sync_conflict(
                TargetSyncConflictRequest(
                    change_id=change_id,
                    target_head=conflict.target_head,
                    operation_id=conflict.operation_id,
                )
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("abandoned target synchronization conflict could not be discarded", exc)

    def cleanup_completed_change_worktree(
        self,
        change_id: str,
        completion_id: str,
    ) -> DeliveryChangeWorktreeCleanup:
        """Clean one completed Change worktree after matching its durable receipt."""
        return self.cleanup_change_worktree(change_id, expected_completion_id=completion_id)

    def show_finalization_context(self, change_id: str) -> DeliveryFinalizationContext:
        """Return engine-resolved finalization context without changing Delivery state."""
        runtime = self._runtime(change_id)
        snapshot = self._delivery_snapshot(runtime)
        projector = self._read_projector(snapshot)
        cards = projector.group_view().items
        card = next((item for item in cards if item.item_key == "publication"), cards[0])
        readiness = card.readiness
        if readiness is None:
            self._fail("finalization readiness was not captured")
        coordination = self._workspace_manager.show(change_id)
        finalization = snapshot.frontier.finalization
        invalidation = snapshot.frontier.finalization_invalidation
        ready = readiness.executable and readiness.operation is WorkItemActionKind.FINALIZE
        return DeliveryFinalizationContext(
            change_id=change_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            change_head=readiness.basis.candidate_head,
            reviewed_change_head=coordination.last_reviewed_commit,
            publication_phase=resolve_publication_phase(snapshot.frontier),
            ready_for_finalization=ready,
            readiness_diagnostics=() if ready else (readiness.reason_code,),
            finalization_id=finalization.finalization_id if finalization is not None else None,
            finalized_head=finalization.exact_head if finalization is not None else None,
            finalization_invalidation_id=invalidation.invalidation_id if invalidation is not None else None,
            readiness=readiness,
        )

    def finalize_change(
        self,
        change_id: str,
        request: FinalizeDeliveryChange,
    ) -> DeliveryFinalizationReceipt:
        """Finalize one exact clean reviewed Change head and queue its checkpoint."""
        runtime = self._runtime(change_id, for_mutation=True, allow_finalizer=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return self._finalize_change_locked(change_id, runtime, request)

    def _finalize_change_locked(
        self, change_id: str, runtime: DeliveryRuntime, request: FinalizeDeliveryChange
    ) -> DeliveryFinalizationReceipt:
        existing = runtime.finalization()
        if existing is not None:
            if (
                existing.operation_id == request.operation_id
                and existing.exact_head == request.exact_head
                and existing.observations == request.observations
                and existing.review == request.review
            ):
                self._record_finalization_retry_success(runtime, request.operation_id)
                self._promote_finalized_external_head(change_id, existing.exact_head)
                self._retire_finalization_report(runtime, existing.exact_head)
                return existing
            self._fail(
                "Delivery Change is already finalized with different authority",
                ValueError("finalization request is not an exact replay"),
            )
        if runtime.change_disposition() is not None:
            self._fail("finalization requires current Change attention resolution")
        attempt = self._workspace_manager.show(change_id).finalization_attempt
        reports = FinalizationReportStore(self._target_root, change_id).read()
        if any(report.request.attempt_key == request.operation_id for report in reports.reports):
            message = "failed finalization attempt cannot submit success after retirement"
            raise DeliveryActionBusyError(message)
        active = attempt is not None and attempt.finished_at is None
        if active:
            self._require_finalization_attempt(runtime, request, attempt)
        context = self.show_finalization_context(change_id)
        if not active and not context.ready_for_finalization:
            self._fail(
                "finalization requires a ready exact Change context",
                ValueError("; ".join(context.readiness_diagnostics)),
            )
        if request.exact_head != context.change_head:
            self._fail(
                "finalization request does not match the current Change head",
                ValueError("Change head changed"),
            )
        results = tuple(result for binding in runtime.bindings() for result in binding.results)
        with self._coordinator.publication_lock(change_id) as publication_lock:
            boundary_participant = self._workspace_manager.prepare_finalization_boundary(
                change_id,
                request.exact_head,
                tuple(result.completed_commit for result in results),
                publication_lock,
                completion=(request.operation_id, self._clock()),
            )
            additional_participants = () if boundary_participant is None else (boundary_participant,)
            finalization = runtime.finalize_change(
                request,
                _timestamp(self._clock()),
                additional_participants=additional_participants,
            )
        self._record_finalization_retry_success(runtime, request.operation_id)
        self._promote_finalized_external_head(change_id, finalization.exact_head)
        self._retire_finalization_report(runtime, finalization.exact_head)
        return finalization

    def _record_finalization_retry_success(self, runtime: DeliveryRuntime, attempt_id: str) -> None:
        """Close a reserved finalizer attempt after its durable receipt is published."""
        with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
            runtime.retry_ledger(clock=self._clock).record_accepted_progress(attempt_id, now=self._clock())

    def _record_worker_retry_success(self, runtime: DeliveryRuntime, outcome_id: str, claim_id: str) -> None:
        """Close a reserved worker attempt after its claim-scoped output is accepted."""
        with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
            binding = runtime.show_binding(outcome_id)
            claim = binding.active_claim
            ledger = runtime.retry_ledger(clock=self._clock)
            attempt_id = (
                claim.attempt_id
                if claim is not None and claim.claim_id == claim_id
                else ledger.attempt_for_operation(claim_id)
            )
            if attempt_id is not None:
                repair_binding = ledger.repair_binding_for_attempt(attempt_id, outcome_id=outcome_id)
                if repair_binding is None:
                    ledger.record_accepted_progress(attempt_id, now=self._clock())

    def _record_retry_release(
        self,
        runtime: DeliveryRuntime,
        *,
        attempt_id: str | None = None,
        outcome_id: str | None = None,
    ) -> None:
        """Release verified custody without resetting the affected retry budget."""
        if attempt_id is None and outcome_id is None:
            return
        with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
            ledger = runtime.retry_ledger(clock=self._clock)
            if attempt_id is not None:
                reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read()
                report = next(
                    (item for item in reports.reports if item.request.attempt_key == attempt_id),
                    None,
                )
                if report is not None:
                    ledger.record_failure(
                        attempt_id,
                        failure_code=report.request.code.value,
                        failure_detail=report.summary,
                        now=report.observed_at,
                    )
                ledger.record_recovery_release(attempt_id, now=self._clock())
            elif outcome_id is not None:
                ledger.record_recovery_release_for_outcome(outcome_id, now=self._clock())

    def _require_finalization_attempt(
        self, runtime: DeliveryRuntime, request: FinalizeDeliveryChange, attempt: ChangeFinalizationAttempt
    ) -> None:
        if (
            request.operation_id != attempt.writer.attempt_id
            or request.exact_head != attempt.exact_head
            or hashlib.sha256(runtime.frontier_bytes()).hexdigest() != attempt.frontier_digest
            or contract_fingerprint(runtime.contract) != attempt.contract_digest
        ):
            message = "finalization attempt does not match current authority"
            raise DeliveryActionSelectionConflictError(message)
        reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read()
        if any(report.request.attempt_key == request.operation_id for report in reports.reports):
            message = "failed finalization retains custody pending supported recovery"
            raise DeliveryActionBusyError(message)

    def _retire_finalization_report(self, runtime: DeliveryRuntime, exact_head: str) -> None:
        try:
            FinalizationReportStore(self._target_root, runtime.contract.change_id).retire(
                exact_head, contract_fingerprint(runtime.contract)
            )
        except FinalizationReportError:
            _logger.warning("Successful finalization retained a diagnostic pointer: report-store-unavailable")

    def report_finalization_failure(
        self,
        request: ReportFinalizationFailure,
    ) -> FinalizationReport | DeliveryReadiness:
        """Persist structural diagnostics without granting lifecycle or proof authority."""
        if request.category in ENGINE_FINALIZATION_CATEGORIES:
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        with locked_roots((self._checkpoint_lock_root(request.change_id),)):
            with self._coordinator.recovery_lock(request.change_id):
                report_store = FinalizationReportStore(self._target_root, request.change_id)
                attention = self._workspace_manager.show(request.change_id).finalization_attention
                if attention is not None:
                    attention_report = next(
                        (item for item in report_store.read().reports if item.report_id == attention.report_id),
                        None,
                    )
                    if attention_report is None or attention_report.request != request:
                        msg = "diagnostic-conflict"
                        raise FinalizationReportError(msg)
                try:
                    report = report_store.record(
                        request,
                        _timestamp(self._clock()),
                        lambda: self._validate_finalization_report_basis(request),
                    )
                except _FinalizationReadUnavailableError as exc:
                    return exc.readiness
            if isinstance(report, FinalizationReport):
                with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
                    self._runtime(request.change_id).retry_ledger(clock=self._clock).record_failure(
                        request.attempt_key,
                        failure_code=request.code.value,
                        failure_detail=report.summary,
                        now=report.observed_at,
                    )
            return report

    @staticmethod
    def _finalizer_settlement_receipt_path(change_id: str, attempt_id: str) -> Path:
        attempt_digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        return Path("finalizer-settlements") / change_id / f"{attempt_digest}.json"

    @staticmethod
    def _raise_finalizer_settlement_conflict(
        message: str,
        cause: BaseException | None = None,
    ) -> Never:
        error = DeliveryActionSelectionConflictError(message)
        if cause is None:
            raise error
        raise error from cause

    def _read_finalizer_settlement_receipt(
        self,
        change_id: str,
        attempt_id: str,
    ) -> FinalizerSettlementReceipt | None:
        relative_path = self._finalizer_settlement_receipt_path(change_id, attempt_id)
        try:
            content = read_record(self._target_root, relative_path)
        except FileNotFoundError:
            return None
        receipt = FinalizerSettlementReceipt.model_validate_json(content, strict=True)
        if receipt.settlement.change_id != change_id or receipt.settlement.attempt_id != attempt_id:
            self._raise_finalizer_settlement_conflict("Finalizer settlement receipt identity is invalid")
        return receipt

    @staticmethod
    def _finalizer_attention_matches_receipt(
        coordination: ChangeCoordination,
        receipt: FinalizerSettlementReceipt | None,
    ) -> bool:
        attention = coordination.finalization_attention
        attempt = coordination.finalization_attempt
        writer = coordination.writer
        if attention is None or attempt is None or writer is None or receipt is None:
            return False
        settlement = receipt.settlement
        return (
            receipt.receipt_id == attention.receipt_id
            and settlement.attempt_id == attempt.writer.attempt_id == attention.attempt_id
            and settlement.claim_id == attempt.writer.claim_id
            and settlement.host_id == attempt.writer.actor_id
            and settlement.session_id == attempt.writer.process_id
            and settlement.report_id == attention.report_id
            and settlement.outcome == attention.outcome
            and settlement.expected_head == attempt.exact_head == attention.expected_head
            and settlement.expected_reviewed_base == attention.expected_reviewed_base
            and receipt.finished_at.isoformat().replace("+00:00", "Z") == attention.finished_at
            and receipt.workspace.head == attention.workspace_head
            and receipt.workspace.fingerprint == attention.workspace_fingerprint
            and receipt.workspace.paths == attention.workspace_paths
            and writer == attempt.writer.model_copy(update={"kind": "finalization-attention"})
        )

    def settle_finalizer_invocation(
        self,
        settlement: FinalizerSettlement,
    ) -> FinalizerSettlementReceipt | DeliveryFinalizationReceipt:
        """Settle only one normally returned Finalizer failure backed by its exact current report."""
        settlement = self._validate_finalizer_settlement_envelope(settlement)
        runtime = self._runtime(settlement.change_id, for_mutation=True, allow_finalizer=True)
        with self._coordinator.publication_lock(settlement.change_id) as lock:
            self._coordinator.recover_pending_transactions()
            prior = self._read_finalizer_settlement_receipt(settlement.change_id, settlement.attempt_id)
            if prior is not None:
                if prior.settlement != settlement:
                    self._raise_finalizer_settlement_conflict(
                        "Finalizer settlement conflicts with its immutable receipt"
                    )
                return prior
            finalization = self._already_finalized_settlement(runtime, settlement)
            if finalization is not None:
                return finalization
            coordination, attempt = self._active_finalizer_attempt(settlement)
            evidence = self._finalizer_settlement_evidence(runtime, settlement, coordination, attempt)
            return self._publish_finalizer_settlement(runtime, settlement, attempt, evidence, lock)

    def _validate_finalizer_settlement_envelope(self, settlement: FinalizerSettlement) -> FinalizerSettlement:
        if not isinstance(settlement, FinalizerSettlement):
            self._raise_finalizer_settlement_conflict("Finalizer settlement requires its typed normal-return envelope")
        try:
            return FinalizerSettlement.model_validate_json(_canonical_model_bytes(settlement), strict=True)
        except (TypeError, ValueError) as exc:
            self._raise_finalizer_settlement_conflict("Finalizer settlement envelope is invalid", exc)

    def _already_finalized_settlement(
        self,
        runtime: DeliveryRuntime,
        settlement: FinalizerSettlement,
    ) -> DeliveryFinalizationReceipt | None:
        finalization = runtime.finalization()
        if finalization is None:
            return None
        coordination = self._coordinator.show(settlement.change_id)
        attempt = coordination.finalization_attempt
        if (
            finalization.operation_id == settlement.attempt_id
            and finalization.exact_head == settlement.expected_head
            and coordination.writer is None
            and attempt is not None
            and attempt.finished_at is not None
            and attempt.writer.attempt_id == settlement.attempt_id
            and attempt.writer.claim_id == settlement.claim_id
            and attempt.writer.actor_id == settlement.host_id
            and attempt.writer.process_id == settlement.session_id
            and attempt.exact_head == settlement.expected_head
        ):
            return finalization
        self._raise_finalizer_settlement_conflict("Change is already finalized with different authority")
        return None

    def _active_finalizer_attempt(
        self,
        settlement: FinalizerSettlement,
    ) -> tuple[ChangeCoordination, ChangeFinalizationAttempt]:
        coordination = self._coordinator.show(settlement.change_id)
        attempt = coordination.finalization_attempt
        if (
            attempt is None
            or attempt.finished_at is not None
            or coordination.writer != attempt.writer
            or attempt.writer.kind != "finalize"
            or attempt.writer.attempt_id != settlement.attempt_id
            or attempt.writer.claim_id != settlement.claim_id
            or attempt.writer.actor_id != settlement.host_id
            or attempt.writer.process_id != settlement.session_id
            or attempt.exact_head != settlement.expected_head
            or coordination.last_reviewed_commit != settlement.expected_reviewed_base
        ):
            self._raise_finalizer_settlement_conflict("Finalizer settlement does not match its exact active attempt")
        return coordination, attempt

    def _finalizer_settlement_evidence(
        self,
        runtime: DeliveryRuntime,
        settlement: FinalizerSettlement,
        coordination: ChangeCoordination,
        attempt: ChangeFinalizationAttempt,
    ) -> tuple[FinalizationReport, FinalizerWorkspaceObservation]:
        snapshot = self._delivery_snapshot(runtime)
        if (
            contract_fingerprint(snapshot.contract) != attempt.contract_digest
            or snapshot.version != attempt.frontier_digest
        ):
            self._raise_finalizer_settlement_conflict("Finalizer settlement basis is no longer current")

        report_snapshot = FinalizationReportStore(self._target_root, settlement.change_id).read()
        report = next((item for item in report_snapshot.reports if item.report_id == settlement.report_id), None)
        if report is None or report_snapshot.current_report_id != settlement.report_id:
            self._raise_finalizer_settlement_conflict("Finalizer settlement requires its exact current report")
        request = report.request
        expected_outcome = finalizer_settlement_outcome(request.category)
        if (
            request.change_id != settlement.change_id
            or request.attempt_key != settlement.attempt_id
            or request.expected_change_head != settlement.expected_head
            or request.expected_reviewed_head != settlement.expected_reviewed_base
            or request.expected_contract_digest != attempt.contract_digest
            or request.expected_frontier_digest != attempt.frontier_digest
            or settlement.outcome != expected_outcome
        ):
            self._raise_finalizer_settlement_conflict("Finalizer settlement does not match its stored report")

        observed, head, fingerprint, paths, _reason = self._workspace_manager.capture_finalization_workspace(
            settlement.change_id,
            tuple(result.completed_commit for binding in snapshot.frontier.bindings for result in binding.results),
        )
        if observed != coordination or head != settlement.expected_head:
            self._raise_finalizer_settlement_conflict("Finalizer workspace changed before settlement")
        if request.category == "custody-preflight" and request.expected_workspace_fingerprint != fingerprint:
            self._raise_finalizer_settlement_conflict("Finalizer custody report no longer matches the workspace")
        if request.category == "proof-mutation" and request.proof_fingerprint_after != fingerprint:
            self._raise_finalizer_settlement_conflict("Finalizer proof-mutation report no longer matches the workspace")
        return report, FinalizerWorkspaceObservation(head=head, fingerprint=fingerprint, paths=paths)

    def _publish_finalizer_settlement(
        self,
        runtime: DeliveryRuntime,
        settlement: FinalizerSettlement,
        attempt: ChangeFinalizationAttempt,
        evidence: tuple[FinalizationReport, FinalizerWorkspaceObservation],
        lock: PublicationLock,
    ) -> FinalizerSettlementReceipt:
        report, workspace = evidence
        finished_at = _timestamp(self._clock())
        finished_at_text = finished_at.isoformat().replace("+00:00", "Z")
        receipt = FinalizerSettlementReceipt.create(
            settlement=settlement,
            report=report,
            finished_at=finished_at,
            workspace=workspace,
        )
        attention = ChangeFinalizationAttention(
            change_id=settlement.change_id,
            receipt_id=receipt.receipt_id,
            attempt_id=settlement.attempt_id,
            report_id=report.report_id,
            outcome=settlement.outcome,
            expected_head=settlement.expected_head,
            expected_reviewed_base=settlement.expected_reviewed_base,
            finished_at=finished_at_text,
            workspace_head=workspace.head,
            workspace_fingerprint=workspace.fingerprint,
            workspace_paths=workspace.paths,
        )
        coordination_participant = self._coordinator.prepare_finalization_attention(
            settlement.change_id, attempt.writer, attention, lock
        )
        owner_result_participants = runtime.retry_ledger(clock=self._clock).owner_result_participants(
            settlement.attempt_id,
            accepted=False,
            failure_code=report.request.code.value,
            now=report.observed_at,
        )
        if len(owner_result_participants) != 1:
            self._raise_finalizer_settlement_conflict("Finalizer retry owner evidence is unavailable")
        receipt_participant = TransactionParticipant(
            self._target_root,
            self._finalizer_settlement_receipt_path(settlement.change_id, settlement.attempt_id),
            _canonical_model_bytes(receipt),
        )
        RuntimeTransaction(
            self._target_root,
            f"finalizer-settlement-{receipt.receipt_id}",
            (receipt_participant, *owner_result_participants, coordination_participant),
        ).commit()
        return receipt

    def _validate_finalization_report_basis(self, request: ReportFinalizationFailure) -> None:
        self._reconcile_runtimes()
        observation = self._discovered_changes.get(request.change_id)
        if observation is not None and not observation.actionable_runtime:
            raise _FinalizationReadUnavailableError(self._unavailable_change(request.change_id).readiness)
        runtime = self._runtime(request.change_id)
        coordination = self._workspace_manager.show(request.change_id)
        if coordination.finalization_attention is not None:
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        attempt = coordination.finalization_attempt
        if attempt is not None and attempt.finished_at is None and request.attempt_key != attempt.writer.attempt_id:
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        snapshot = self._delivery_snapshot(runtime)
        basis = DeliveryReadinessBasis(
            contract_digest=contract_fingerprint(snapshot.contract), frontier_digest=snapshot.version
        )
        try:
            coordination, head, fingerprint, paths, reason = self._workspace_manager.capture_finalization_workspace(
                request.change_id,
                tuple(result.completed_commit for binding in snapshot.frontier.bindings for result in binding.results),
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            raise _FinalizationReadUnavailableError(
                DeliveryReadiness(
                    status="unavailable",
                    next_actor=WorkItemNextActor.NONE,
                    reason_code="workspace-inspection-failed",
                    basis=basis,
                )
            ) from exc
        if (
            request.expected_contract_digest != basis.contract_digest
            or request.expected_frontier_digest != basis.frontier_digest
            or request.expected_change_head != head
            or request.expected_reviewed_head != coordination.last_reviewed_commit
        ):
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        if request.category == "custody-preflight" and (
            request.expected_workspace_fingerprint != fingerprint
            or not set(request.paths) <= set(paths)
            or (request.code.value == "workspace-dirty" and not paths)
            or (request.code.value == "workspace-preflight-failed" and reason is None)
        ):
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        if request.category == "proof-mutation" and (
            (
                request.expected_workspace_fingerprint is not None
                and request.expected_workspace_fingerprint != request.proof_fingerprint_before
            )
            or request.proof_fingerprint_after != fingerprint
            or not set(request.paths) <= set(paths)
        ):
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)

    def resolve_change_disposition(
        self,
        change_id: str,
        expected_disposition_id: str,
    ) -> DeliveryChangeDispositionResolution:
        """Resolve one exact Change attention record without recreating provider authority."""
        runtime = self._runtime(change_id, for_mutation=True)
        with self._attention_resolution_lock(change_id):
            resolution = runtime.resolve_change_disposition(expected_disposition_id, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"attention-resolution-{resolution.resolution_id}")
            return resolution

    @contextmanager
    def _attention_resolution_lock(self, change_id: str) -> Iterator[None]:
        """Bound checkpoint contention for disposition resolution."""
        deadline = time.monotonic() + _ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS
        with ExitStack() as stack:
            while True:
                try:
                    stack.enter_context(locked_roots((self._checkpoint_lock_root(change_id),), blocking=False))
                except BlockingIOError as exc:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        message = (
                            "Change attention resolution is already in progress; "
                            "retry after the active mutation finishes"
                        )
                        raise DeliveryChangeDispositionBusyError(message) from exc
                    time.sleep(min(_ATTENTION_RESOLUTION_LOCK_RETRY_SECONDS, remaining))
                else:
                    break
            yield

    def recover_publication_baseline(
        self,
        change_id: str,
        expected_change_head: str,
        publication_base_head: str,
        operation_id: str,
        *,
        confirmed_recovery: bool = False,
    ) -> PublicationBaselineRecoveryReceipt:
        """Recover one unknown publication baseline after explicit operator confirmation."""
        if not confirmed_recovery:
            message = "publication baseline recovery requires explicit confirmation"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                message = "publication baseline recovery cannot overlap an active claim"
                raise PortfolioApplicationError(message)
            return self._workspace_manager.recover_publication_baseline(
                change_id,
                expected_change_head,
                publication_base_head,
                operation_id,
            )

    def defer_change(self, change_id: str, reason: str) -> DeliveryChangeDeferral:
        """Retain one nonterminal Change and pause its claimable frontier."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            deferral = runtime.defer_change(reason, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"deferral-{deferral.deferral_id}")
            return deferral

    def resume_change(self, change_id: str) -> DeliveryChangeDeferral:
        """Resume one exact deferred Change from its retained prior state."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            deferral = runtime.resume_change()
            self._publish_delivery_state(change_id, runtime, f"resume-{deferral.deferral_id}")
            return deferral

    def abandon_change(self, change_id: str, reason: str) -> DeliveryChangeAbandonment:
        """Record one terminal user abandonment without mutating the user checkout."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            abandonment = runtime.abandon_change(reason, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"abandonment-{abandonment.abandonment_id}")
            return abandonment
