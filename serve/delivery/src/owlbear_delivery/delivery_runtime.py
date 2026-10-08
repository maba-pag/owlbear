"""Mechanical Delivery state and worker-owned transitions."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionReceipt,
    CompletionReceiptBundle,
    CompletionReceiptConflictError,
    CompletionReceiptStore,
)
from owlbear_delivery.acceptance_criteria import acceptance_criteria
from owlbear_delivery.evidence import (
    DeliveryContextRefusal,
    DeliveryFinalizationSemantics,
    evaluate_acceptance_evidence,
    finalization_semantics_or_refusal,
    observation_gaps,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryIntent,
    RecoveryReceipt,
    RetryAttemptGrantError,
    RetryLedger,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    digest,
    encoded,
    journal_path,
)

# Consumer import surface kept at this module path.
from owlbear_delivery.runtime_models import (  # noqa: F401
    _FRONTIER_SCHEMA_VERSION,
    _NORMAL_CHANGE_MUTATIONS,
    _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION,
    CONFIRMATION_DECISIONS,
    DELIVERY_TRANSITION_ADAPTER,
    PROOF_VERDICTS,
    REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES,
    ActivateDeliveryClaim,
    AdvanceDelivery,
    BlockDelivery,
    CompletedOutcomeRepairReceipt,
    DeliveryAcceptanceAttentionReason,
    DeliveryAcceptanceEvidenceError,
    DeliveryAcceptanceWaitingError,
    DeliveryActionSelectionConflictError,
    DeliveryActiveClaim,
    DeliveryArtifactResult,
    DeliveryBlock,
    DeliveryBuilderHandoffContext,
    DeliveryChangeAbandonment,
    DeliveryChangeCompletion,
    DeliveryChangeDeferral,
    DeliveryChangeDisposition,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionConflictError,
    DeliveryChangeDispositionKind,
    DeliveryChangeDispositionResolution,
    DeliveryChangePublicationHistory,
    DeliveryChangePublicationIdentity,
    DeliveryChangeStage,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryCommandResult,
    DeliveryConfirmationError,
    DeliveryConfirmationScope,
    DeliveryEvidenceGap,
    DeliveryFinalization,
    DeliveryFinalizationInvalidation,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryLegacyObservation,
    DeliveryLegacyObservationReceipt,
    DeliveryManualProcedureResult,
    DeliveryMergedPullRequestLatch,
    DeliveryMissingResult,
    DeliveryObservation,
    DeliveryObservationEnvironment,
    DeliveryObservationReceipt,
    DeliveryOperatorMove,
    DeliveryOutputKind,
    DeliveryOutputReference,
    DeliveryPendingCheckpoint,
    DeliveryPendingStatePublication,
    DeliveryPlanCandidate,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryResultCandidate,
    DeliveryRetryDiagnostic,
    DeliveryReturnContext,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryTransition,
    DeliveryWaivedResult,
    DeliveryWorkerRole,
    EngineWorkerDisposition,
    FinalizeDeliveryChange,
    OutcomeAuthorityBinding,
    PrepareCompletedOutcomeRepair,
    PublishDeliveryOutput,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    RetryDelivery,
    ReturnDelivery,
    _model_content,
    _reference,
    derive_change_stage,
    integration_attention_disposition,
    is_change_terminal,
    pause_mutation_class,
)
from owlbear_delivery.runtime_reads import (
    _RuntimeReadsMixin,
)
from owlbear_delivery.runtime_receipts import (  # noqa: F401
    BUILDER_ATTEMPT_GRANT_NOTE,
    AdministrativeDeliveryMove,
    AdministrativeDeliveryMovePreview,
    AdministrativeDeliveryMoveResult,
    DeliveryBuilderInvocationSettlement,
    DeliveryEngineBuilderSettlement,
    DeliveryEnginePlanningSettlement,
    DeliveryPlanningRetrySettlement,
    _DeliveryBuilderAttemptGrantReceipt,
    _DeliveryBuilderHandoffChangeIntentHead,
    _DeliveryBuilderHandoffChangeIntentReceipt,
    _DeliveryBuilderInvocationSettlementReceipt,
    _DeliveryBuilderPlanPromotionReceipt,
    _DeliveryBuilderRequestResolutionReceipt,
    _DeliveryPlanningPauseReplay,
    _DeliveryPlanningRetrySettlementReceipt,
    builder_attempt_limit_block_id,
)
from owlbear_delivery.runtime_settlement import (
    _SettlementReplayMixin,
)
from owlbear_delivery.runtime_support import (  # noqa: F401
    _administrative_move_closure,
    _attention_conflict,
    _builder_attempt_grant_receipt_path,
    _checkpoint_with_head,
    _completed_outcome_repair_id,
    _conflict,
    _consume_declared_mutation,
    _declare_mutation,
    _find_binding,
    _find_request,
    _invalidate_finalization_checkpoint,
    _pull_request_identity,
    _queue_finalization_checkpoint,
    _queue_promoted_result_checkpoint,
    _read_builder_attempt_grant_receipt,
    _read_builder_handoff_change_intent_receipts,
    _read_builder_request_resolution_receipt,
    _replace_binding,
    _require_change_mutable,
    _require_claim,
    _require_no_active_change_claim,
    _require_no_review_repair,
    _require_target_sync_attention,
    _reset_binding,
    _target_sync_operation_id,
    invalidate_checkpoint_publication,
    is_acceptance_waiting_observation,
    normalize_frontier,
    parse_delivery_frontier,
    parse_stored_delivery_frontier,
    repair_missing_request_provenance,
    stored_frontier_version,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_delivery.storage_io import state_is_read_only
from owlbear_delivery.target_contract import contract_canonical_bytes

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery.change_workspace import (
        ChangeDesignPackageSnapshotReceipt,
        ChangeExternalHeadAdoptionReceipt,
        ChangeExternalHeadPromotionReceipt,
        ChangeFinalizationAttention,
        ChangeTargetSyncReceipt,
        ChangeWorkspaceManager,
        PublicationLock,
    )
    from owlbear_delivery.draft_pull_request import (
        PublicationPullRequestObservationReceipt,
        PullRequestReadyReceipt,
    )
    from owlbear_delivery.target_contract import DeliveryContract


_GUARD_RETRY_LIMIT = 8


def _is_portable(frontier: DeliveryFrontier) -> bool:
    return (
        not any(binding.active_claim is not None for binding in frontier.bindings)
        and not any(binding.builder_handoff_context is not None for binding in frontier.bindings)
        and frontier.integration_repair_claim is None
    )


def _deferral_lifecycle_refusal(
    frontier: DeliveryFrontier,
) -> Literal["change-inactive", "step-in-progress"] | None:
    """Read-only mirror of ``defer_change``'s lifecycle and claim guards, in the same order."""
    if frontier.change_deferral is not None:
        return "change-inactive"
    try:
        _require_change_mutable(frontier, "defer_change")
    except DeliveryRuntimeConflictError:
        return "change-inactive"
    finally:
        _consume_declared_mutation()
    if frontier.change_abandonment is not None or is_change_terminal(frontier):
        return "change-inactive"
    try:
        _require_no_active_change_claim(frontier, "Change Pause")
    except DeliveryRuntimeConflictError:
        return "step-in-progress"
    if derive_change_stage(frontier) in {DeliveryChangeStage.DEFERRED, DeliveryChangeStage.ABANDONED}:
        return "change-inactive"
    return None


def checkpoint_for_snapshot(frontier: DeliveryFrontier, snapshot_head: str) -> DeliveryFrontier:
    """Re-anchor a pending checkpoint to a package snapshot head, or queue an explicit one for it."""
    pending = frontier.pending_checkpoint
    if pending is not None:
        return frontier.model_copy(update={"pending_checkpoint": _checkpoint_with_head(pending, snapshot_head)})
    if frontier.published_head == snapshot_head:
        return frontier
    trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT)
    return frontier.model_copy(
        update={"pending_checkpoint": DeliveryPendingCheckpoint(head=snapshot_head, triggers=(trigger,))}
    )


class DeliveryRuntime(_SettlementReplayMixin, _RuntimeReadsMixin):
    """Apply worker instructions and operator correction to one Delivery frontier."""

    def __init__(
        self,
        runtime_root: Path,
        contract: DeliveryContract,
        *,
        workspace_manager: ChangeWorkspaceManager | None = None,
    ) -> None:
        self._target_root = runtime_root.resolve()
        if workspace_manager is not None and workspace_manager.runtime_root != self._target_root:
            _conflict("runtime and workspace coordination must share one transaction root")
        self._contract = contract
        self._workspace_manager = workspace_manager
        self._authority_digest = hashlib.sha256(contract_canonical_bytes(contract)).hexdigest()
        self._frontier_path = self._target_root / "changes" / contract.change_id / "frontier.json"
        self._pending_publication_path = self._frontier_path.with_name("state-publication.json")
        self._validate_frontier(self._read()[0])

    @property
    def authority_digest(self) -> str:
        """Return the canonical admitted contract digest bound into task results."""
        return self._authority_digest

    def retry_ledger(self, *, clock: Callable[[], datetime | str] | None = None) -> RetryLedger:
        """Return the Change-scoped durable retry authority."""
        return RetryLedger(self._target_root, self._contract.change_id, clock=clock)

    @property
    def contract(self) -> DeliveryContract:
        """Return immutable admitted authority for scoped context projection."""
        return self._contract

    def frontier_bytes(self) -> bytes:
        """Return current canonical frontier bytes for OCC and failure proof."""
        return self._read()[1]

    def pending_state_publication(self) -> DeliveryPendingStatePublication | None:
        """Return the unacknowledged local state publication intent, if any."""
        if not self._pending_publication_path.is_file():
            return None
        try:
            intent = DeliveryPendingStatePublication.model_validate_json(
                self._pending_publication_path.read_bytes(), strict=True
            )
        except OSError, TypeError, ValueError:
            _reference("Delivery state publication intent is invalid")
        return intent if intent.status == "pending" else None

    def acknowledge_pending_publication(self, frontier_digest: str) -> None:
        """Mark the matching local publication intent acknowledged after remote push."""
        if not self._pending_publication_path.is_file():
            return
        current_content = self._pending_publication_path.read_bytes()
        current = DeliveryPendingStatePublication.model_validate_json(current_content, strict=True)
        if current.status != "pending" or current.frontier_digest != frontier_digest:
            return
        replacement = _model_content(current.acknowledge())
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._pending_publication_path.relative_to(self._target_root),
            current_content,
            replacement,
        )
        RuntimeTransaction(
            self._target_root,
            f"delivery-state-ack-{frontier_digest}",
            (participant,),
        ).commit()

    def reanchor_pending_publication(self, base_frontier_digest: str) -> None:
        """Re-anchor a pending publication after a validated authority revision."""
        if not self._pending_publication_path.is_file():
            return
        current_content = self._pending_publication_path.read_bytes()
        current = DeliveryPendingStatePublication.model_validate_json(current_content, strict=True)
        frontier_content = self.frontier_bytes()
        frontier_digest = hashlib.sha256(frontier_content).hexdigest()
        if current.status != "pending" or current.frontier_digest == frontier_digest:
            return
        replacement = _model_content(
            DeliveryPendingStatePublication.pending(
                base_frontier_digest,
                frontier_digest,
                current.transition_request_digest,
            )
        )
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._pending_publication_path.relative_to(self._target_root),
            current_content,
            replacement,
        )
        RuntimeTransaction(
            self._target_root,
            f"delivery-state-reanchor-{frontier_digest}",
            (participant,),
        ).commit()

    def integration_attention(self) -> DeliveryIntegrationAttention | None:
        """Return current retryable Integration evidence, if any."""
        return self._read()[0].integration_attention

    def change_disposition(self) -> DeliveryChangeDisposition | None:
        """Return current Change-level attention evidence, if any."""
        return self._read()[0].change_disposition

    def change_disposition_publication(self) -> DeliveryChangePublicationIdentity | None:
        """Return the publication identity retained by current Change attention."""
        return self._read()[0].change_disposition_publication

    def change_disposition_resolution(self) -> DeliveryChangeDispositionResolution | None:
        """Return the most recent durable Change attention resolution receipt."""
        return self._read()[0].change_disposition_resolution

    def change_deferral(self) -> DeliveryChangeDeferral | None:
        """Return the current user-requested Change deferral, if any."""
        return self._read()[0].change_deferral

    def change_abandonment(self) -> DeliveryChangeAbandonment | None:
        """Return the terminal user-requested Change abandonment, if any."""
        return self._read()[0].change_abandonment

    def deferral_refusal(
        self, frontier: DeliveryFrontier
    ) -> Literal["change-inactive", "step-in-progress", "state-unavailable"] | None:
        """Evaluate ``defer_change``'s frontier refusals read-only; None means it would record a deferral."""
        refusal = _deferral_lifecycle_refusal(frontier)
        if refusal is not None:
            return refusal
        try:
            for binding in frontier.bindings:
                if binding.builder_handoff_context is not None:
                    self._builder_handoff_change_intent_chain(frontier, binding.builder_handoff_context, "defer")
        except DeliveryRuntimeConflictError, OSError, ValueError:
            return "state-unavailable"
        return None

    def defer_change(
        self,
        reason: str,
        deferred_at: datetime,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
        pause_request_clear: ReplacementTransactionParticipant | None = None,
    ) -> DeliveryChangeDeferral:
        """Pause one nonterminal Change while retaining its exact frontier and worktree.

        ``pause_request_clear`` converts a drained Pause request in this same transaction (K5).
        """
        frontier, previous = self._read()
        if frontier.change_deferral is not None:
            self._require_recorded_builder_handoff_change_intent(frontier)
            return frontier.change_deferral
        _require_change_mutable(frontier, "defer_change")
        if frontier.change_abandonment is not None or is_change_terminal(frontier):
            _conflict("terminal Delivery Change cannot be paused")
        _require_no_active_change_claim(frontier, "Change Pause")
        prior_stage = derive_change_stage(frontier)
        if prior_stage in {DeliveryChangeStage.DEFERRED, DeliveryChangeStage.ABANDONED}:
            _conflict("Change is not eligible for Pause")
        deferral = DeliveryChangeDeferral.create(
            change_id=self._contract.change_id,
            prior_stage=prior_stage,
            deferred_at=deferred_at,
            reason=reason,
        )
        replacement = frontier.model_copy(update={"change_deferral": deferral})
        participants = self._builder_handoff_change_intent_participants(
            frontier,
            replacement,
            "defer",
            deferral=deferral,
            previous=previous,
        )
        participants = (
            self._change_intent_custody_participants(participants, expected_finalization_attention)
            if pause_request_clear is None
            else (*participants, pause_request_clear)
        )
        self._replace(
            previous,
            replacement,
            additional_participants=participants,
            include_custody_guard=False,
        )
        return deferral

    def resume_change(
        self,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> DeliveryChangeDeferral:
        """Resume one exact deferred Change and return its preserved prior-state receipt."""
        frontier, previous = self._read()
        if frontier.change_abandonment is not None or is_change_terminal(frontier):
            _conflict("terminal Delivery Change cannot be resumed")
        _require_change_mutable(frontier, "resume_change")
        deferral = frontier.change_deferral
        if deferral is None:
            _conflict("Delivery Change is not paused")
        _require_no_active_change_claim(frontier, "Change resume")
        replacement = frontier.model_copy(update={"change_deferral": None})
        participants = self._builder_handoff_change_intent_participants(
            frontier,
            replacement,
            "resume",
            deferral=deferral,
            previous=previous,
        )
        participants = self._change_intent_custody_participants(participants, expected_finalization_attention)
        self._replace(
            previous,
            replacement,
            additional_participants=participants,
            include_custody_guard=False,
        )
        return deferral

    def abandon_change(
        self,
        reason: str,
        abandoned_at: datetime,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
        pause_request_clear: ReplacementTransactionParticipant | None = None,
    ) -> DeliveryChangeAbandonment:
        """Terminate one uncompleted Change without discarding its retained authority."""
        frontier, previous = self._read()
        if frontier.change_abandonment is not None:
            self._require_recorded_builder_handoff_change_intent(frontier)
            return frontier.change_abandonment
        if frontier.change_completion is not None:
            _conflict("completed Delivery Change cannot be abandoned")
        _require_change_mutable(frontier, "abandon_change")
        _require_no_active_change_claim(frontier, "Change abandonment")
        prior_stage = derive_change_stage(frontier)
        if prior_stage == DeliveryChangeStage.ABANDONED:
            _conflict("Change is not eligible for abandonment")
        abandonment = DeliveryChangeAbandonment.create(
            change_id=self._contract.change_id,
            prior_stage=prior_stage,
            abandoned_at=abandoned_at,
            reason=reason,
        )
        replacement = frontier.model_copy(
            update={
                "change_abandonment": abandonment,
                "change_deferral": None,
                "change_disposition": None,
                "change_disposition_publication": None,
                "pending_checkpoint": None,
                "ready": None,
                "merged_pull_request_latch": None,
                "integration_attention": None,
                "integration_repair_claim": None,
            }
        )
        participants = self._builder_handoff_change_intent_participants(
            frontier,
            replacement,
            "abandon",
            deferral=frontier.change_deferral,
            abandonment=abandonment,
            previous=previous,
        )
        participants = (
            self._change_intent_custody_participants(participants, expected_finalization_attention)
            if pause_request_clear is None
            else (*participants, pause_request_clear)
        )
        self._replace(
            previous,
            replacement,
            additional_participants=participants,
            include_custody_guard=False,
        )
        return abandonment

    def _capture_existing_change_disposition(
        self,
        frontier: DeliveryFrontier,
        existing: DeliveryChangeDisposition,
        disposition: DeliveryChangeDisposition,
        publication_identity: DeliveryChangePublicationIdentity | None,
    ) -> tuple[DeliveryChangeDisposition, DeliveryFrontier | None]:
        if not (
            existing.kind == disposition.kind
            and existing.change_id == disposition.change_id
            and existing.entered_from == disposition.entered_from
            and existing.diagnostics == disposition.diagnostics
            and existing.acceptance_reason == disposition.acceptance_reason
        ):
            _conflict("Delivery Change already has different attention authority")
        if publication_identity is None:
            return existing, None
        if publication_identity.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")
        current = frontier.change_disposition_publication
        if current is None:
            return (
                existing,
                frontier.model_copy(update={"change_disposition_publication": publication_identity}),
            )
        if current != publication_identity:
            _conflict("Delivery Change attention has different publication identity")
        return existing, None

    def capture_change_disposition(
        self,
        disposition: DeliveryChangeDisposition,
        *,
        clear_ready: bool = False,
        publication_identity: DeliveryChangePublicationIdentity | None = None,
    ) -> DeliveryChangeDisposition:
        """Persist one first-write-wins Change attention record."""
        frontier, previous = self._read()
        _declare_mutation("capture_change_disposition")
        existing = frontier.change_disposition
        if existing is not None:
            result, updated = self._capture_existing_change_disposition(
                frontier,
                existing,
                disposition,
                publication_identity,
            )
            if updated is not None:
                self._replace(previous, updated)
            return result
        if is_change_terminal(frontier):
            _conflict("completed Delivery Change cannot retain attention")
        _require_no_active_change_claim(frontier, "Change attention capture")
        if disposition.change_id != self._contract.change_id:
            _conflict("Change disposition does not match the admitted Change")
        if disposition.entered_from != derive_change_stage(frontier):
            _conflict("Change disposition does not match the current lifecycle stage")
        retained_publication = publication_identity
        if retained_publication is None and clear_ready:
            retained_publication = _pull_request_identity(frontier.ready)
        if retained_publication is not None and retained_publication.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")
        updated = frontier.model_copy(
            update={
                "change_disposition": disposition,
                "change_disposition_publication": retained_publication,
                "change_disposition_resolution": None,
                "ready": None if clear_ready else frontier.ready,
            }
        )
        self._replace(previous, updated)
        return disposition

    def resolve_change_disposition(
        self,
        expected_disposition_id: str,
        resolved_at: datetime,
    ) -> DeliveryChangeDispositionResolution:
        """Clear one exact Change attention record without restoring provider authority."""
        frontier, previous = self._read()
        _declare_mutation("resolve_change_disposition")
        current = frontier.change_disposition
        existing = frontier.change_disposition_resolution
        if current is None:
            if existing is not None and existing.disposition_id == expected_disposition_id:
                return existing
            _attention_conflict("Delivery Change attention is absent or already resolved")
        if current.disposition_id != expected_disposition_id:
            _attention_conflict("Delivery Change attention identity is stale")
        if _target_sync_operation_id(current) is not None:
            _attention_conflict("target synchronization requires an explicit conflict exit")
        _require_no_active_change_claim(frontier, "Change attention resolution")
        resolution = DeliveryChangeDispositionResolution.create(
            change_id=self._contract.change_id,
            disposition_id=current.disposition_id,
            resolved_at=resolved_at,
        )
        updated = frontier.model_copy(
            update={
                "change_disposition": None,
                "change_disposition_publication": None,
                "change_disposition_resolution": resolution,
            }
        )
        self._replace(previous, updated)
        return resolution

    def capture_publication_attention(
        self,
        recorded_at: datetime,
        diagnostics: tuple[str, ...],
        *,
        clear_ready: bool = False,
        publication_identity: DeliveryChangePublicationIdentity | None = None,
    ) -> DeliveryChangeDisposition:
        """Capture provider publication evidence that requires operator reconciliation."""
        return self.capture_change_disposition(
            DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
                change_id=self._contract.change_id,
                entered_from=self.change_stage(),
                recorded_at=recorded_at,
                diagnostics=diagnostics,
            ),
            clear_ready=clear_ready,
            publication_identity=publication_identity,
        )

    def capture_acceptance_attention(
        self,
        observation: PublicationPullRequestObservationReceipt,
        diagnostics: tuple[str, ...],
        *,
        reason: DeliveryAcceptanceAttentionReason = DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
    ) -> DeliveryChangeDisposition:
        """Capture one mismatched provider acceptance observation."""
        return self.capture_change_disposition(
            DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION,
                change_id=self._contract.change_id,
                entered_from=DeliveryChangeStage.AWAITING_MERGE,
                recorded_at=observation.observed_at,
                diagnostics=(*diagnostics, f"acceptance-observation:{observation.observation_id}"),
                acceptance_reason=reason,
            ),
            clear_ready=True,
            publication_identity=DeliveryChangePublicationIdentity(
                change_id=self._contract.change_id,
                repository=observation.snapshot.repository,
                number=observation.snapshot.number,
                node_id=observation.snapshot.node_id,
                head_sha=observation.snapshot.head_sha,
            ),
        )

    def record_publication_successor(
        self,
        predecessor: DeliveryChangePublicationIdentity,
        successor: DeliveryChangePublicationIdentity,
    ) -> DeliveryChangePublicationHistory:
        """Append one exact successor publication while retaining publication attention."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_publication_successor")
        _require_no_active_change_claim(frontier, "publication supersession")
        disposition = frontier.change_disposition
        if disposition is None or disposition.kind != DeliveryChangeDispositionKind.PUBLICATION_ATTENTION:
            _conflict("publication supersession requires current publication attention")
        if (
            predecessor.change_id != self._contract.change_id
            or successor.change_id != self._contract.change_id
            or frontier.change_disposition_publication != predecessor
        ):
            _conflict("publication supersession predecessor does not match current attention")
        if predecessor == successor:
            _conflict("publication supersession requires a distinct successor identity")
        history = frontier.change_publication_history or DeliveryChangePublicationHistory.create(predecessor)
        try:
            updated_history = history.append(predecessor, successor)
        except ValueError as exc:
            _conflict(str(exc))
        updated = frontier.model_copy(
            update={
                "change_disposition_publication": successor,
                "change_publication_history": updated_history,
            }
        )
        self._replace(previous, updated)
        return updated_history

    def record_publication_identity(
        self,
        publication: DeliveryChangePublicationIdentity,
    ) -> DeliveryChangePublicationHistory:
        """Record the first publication or refresh the exact head of the current PR."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_publication_identity")
        if publication.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")
        history = frontier.change_publication_history
        if history is None:
            updated_history = DeliveryChangePublicationHistory.create(publication)
        elif history.current == publication:
            return history
        else:
            try:
                updated_history = history.refresh_current(publication)
            except ValueError as exc:
                _conflict(str(exc))
        self._replace(previous, frontier.model_copy(update={"change_publication_history": updated_history}))
        return updated_history

    def show_binding(self, outcome_id: str) -> OutcomeAuthorityBinding:
        """Return one current outcome binding."""
        return _find_binding(self._read()[0], outcome_id)

    def bindings(self) -> tuple[OutcomeAuthorityBinding, ...]:
        """Return current outcome bindings in admitted authority order."""
        return self._read()[0].bindings

    def record_checkpoint_branch_publication(
        self,
        expected: DeliveryCheckpointPublicationState,
        published_head: str,
    ) -> DeliveryCheckpointPublicationState:
        """Record one exact reconciled remote head without draining its obligations."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_checkpoint_branch_publication")
        pending = expected.pending_checkpoint
        if (
            expected.change_id != self._contract.change_id
            or pending is None
            or pending.head != published_head
            or frontier.published_head != expected.published_head
        ):
            _conflict("checkpoint branch publication no longer matches the durable queue")
        updated = frontier.model_copy(update={"published_head": published_head})
        pending_publication = self.pending_state_publication()
        self._replace_content(
            previous,
            _model_content(updated),
            base_frontier_digest=(
                pending_publication.base_frontier_digest
                if pending_publication is not None
                else self.publication_base_digest(previous)
            ),
            transition_request_digest=(
                pending_publication.transition_request_digest if pending_publication is not None else None
            ),
        )
        return self.checkpoint_publication_state()

    def record_design_package_snapshot(
        self,
        expected: DeliveryCheckpointPublicationState,
        receipt: ChangeDesignPackageSnapshotReceipt,
    ) -> DeliveryCheckpointPublicationState:
        """Re-anchor the first checkpoint to its admitted package snapshot commit."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_design_package_snapshot")
        current = frontier.pending_checkpoint
        if current is not None and current.head == receipt.snapshot_head:
            return self.checkpoint_publication_state()
        if (
            expected.change_id != self._contract.change_id
            or expected.pending_checkpoint is None
            or current != expected.pending_checkpoint
            or frontier.published_head != expected.published_head
            or receipt.change_id != self._contract.change_id
            or (
                expected.pending_checkpoint.head is not None
                and receipt.previous_head != expected.pending_checkpoint.head
            )
        ):
            _conflict("Design package snapshot no longer matches the checkpoint queue")
        self._replace(previous, checkpoint_for_snapshot(frontier, receipt.snapshot_head))
        return self.checkpoint_publication_state()

    def queue_admitted_design_checkpoint(self, reviewed_head: str) -> DeliveryCheckpointPublicationState:
        """Queue the first remote checkpoint for an admitted Design package."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "queue_admitted_design_checkpoint")
        pending = frontier.pending_checkpoint
        trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.ADMITTED_DESIGN)
        if pending is not None:
            if pending.head != reviewed_head:
                _conflict("admitted Design checkpoint no longer matches the reviewed boundary")
            if trigger in pending.triggers:
                return self.checkpoint_publication_state()
            updated = frontier.model_copy(
                update={"pending_checkpoint": pending.model_copy(update={"triggers": (*pending.triggers, trigger)})}
            )
        elif frontier.published_head is not None:
            return self.checkpoint_publication_state()
        else:
            updated = frontier.model_copy(
                update={"pending_checkpoint": DeliveryPendingCheckpoint(head=reviewed_head, triggers=(trigger,))}
            )
        self._replace(previous, updated)
        return self.checkpoint_publication_state()

    def queue_explicit_checkpoint(self, reviewed_head: str) -> DeliveryCheckpointPublicationState:
        """Queue one explicit checkpoint for the current reviewed Change head."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "queue_explicit_checkpoint", allow_attention=True)
        _require_no_active_change_claim(frontier, "explicit checkpoint")
        trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT)
        pending = frontier.pending_checkpoint
        if pending is not None:
            if pending.head != reviewed_head:
                _conflict("explicit checkpoint no longer matches the reviewed boundary")
            if trigger in pending.triggers:
                return self.checkpoint_publication_state()
            updated = frontier.model_copy(
                update={"pending_checkpoint": pending.model_copy(update={"triggers": (*pending.triggers, trigger)})}
            )
        elif frontier.published_head == reviewed_head:
            return self.checkpoint_publication_state()
        else:
            updated = checkpoint_for_snapshot(frontier, reviewed_head)
        self._replace(previous, updated)
        return self.checkpoint_publication_state()

    def acknowledge_checkpoint_publication(
        self,
        expected: DeliveryPendingCheckpoint,
        published_head: str,
    ) -> DeliveryCheckpointPublicationState:
        """Drain reconciled obligations while retaining any newer local checkpoint."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "acknowledge_checkpoint_publication")
        current = frontier.pending_checkpoint
        if expected.head != published_head or frontier.published_head != published_head or current is None:
            _conflict("checkpoint acknowledgment no longer matches the published head")
        if current.head == published_head:
            retained = tuple(trigger for trigger in current.triggers if trigger not in expected.triggers)
        else:
            retained = tuple(
                trigger
                for trigger in current.triggers
                if not (
                    trigger in expected.triggers
                    and trigger.kind
                    in {
                        DeliveryCheckpointTriggerKind.ADMITTED_DESIGN,
                        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
                    }
                )
            )
        pending = current.model_copy(update={"triggers": retained}) if retained else None
        updated = frontier.model_copy(update={"pending_checkpoint": pending})
        if stored_frontier_version(previous) == _FRONTIER_SCHEMA_VERSION or not _is_portable(updated):
            self._replace_content(previous, _model_content(updated), record_pending_publication=False)
        else:
            # The 18 -> 19 representation change is a new portable state; its base is the drained
            # projection the remote snapshot already holds, so publication replay can match it.
            self._replace_content(
                previous,
                _model_content(updated),
                base_frontier_digest=self.published_projection_digest(previous),
            )
        return self.checkpoint_publication_state()

    def record_checkpoint_failure(
        self,
        expected: DeliveryPendingCheckpoint,
        attempted_at: datetime,
        error_code: str,
        error_detail: str,
    ) -> DeliveryCheckpointPublicationState:
        """Persist one failed checkpoint attempt without changing its obligation."""
        if attempted_at.tzinfo is None:
            message = "pending checkpoint failure timestamp must include a timezone"
            raise ValueError(message)
        if not error_code or not error_detail:
            message = "pending checkpoint failure requires an error code and detail"
            raise ValueError(message)
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_checkpoint_failure", allow_attention=True)
        current = frontier.pending_checkpoint
        if current is None or current != expected:
            _conflict("checkpoint failure no longer matches the durable queue")
        updated_pending = current.model_copy(
            update={
                "attempt_count": current.attempt_count + 1,
                "last_attempted_at": attempted_at,
                "last_error_code": error_code,
                "last_error_detail": error_detail,
            }
        )
        self._replace(previous, frontier.model_copy(update={"pending_checkpoint": updated_pending}))
        return self.checkpoint_publication_state()

    def finalization(self) -> DeliveryFinalizationReceipt | None:
        """Return current exact-head finalization authority, if any."""
        return self._read()[0].finalization

    def finalization_invalidation(self) -> DeliveryFinalizationInvalidationReceipt | None:
        """Return the latest durable finalization invalidation, if any."""
        return self._read()[0].finalization_invalidation

    def ready_receipt(self) -> PullRequestReadyReceipt | None:
        """Return durable authority that the exact finalized pull request is ready."""
        return self._read()[0].ready

    def publication_history(self) -> DeliveryChangePublicationHistory | None:
        """Return ordered provider publication identities for this Change."""
        return self._read()[0].change_publication_history

    def target_sync_receipt(self) -> ChangeTargetSyncReceipt | None:
        """Return the latest exact target synchronization receipt, if any."""
        return self._read()[0].target_sync_receipt

    def external_head_adoption_receipt(self) -> ChangeExternalHeadAdoptionReceipt | None:
        """Return the latest exact external Change-head adoption receipt, if any."""
        return self._read()[0].external_head_adoption_receipt

    def external_head_promotion_receipt(self) -> ChangeExternalHeadPromotionReceipt | None:
        """Return the latest exact external Change-head promotion receipt, if any."""
        return self._read()[0].external_head_promotion_receipt

    def merged_pull_request_latch(self) -> DeliveryMergedPullRequestLatch | None:
        """Return immutable first merged evidence for the bound pull request."""
        return self._read()[0].merged_pull_request_latch

    def mark_awaiting_merge(self, receipt: PullRequestReadyReceipt) -> PullRequestReadyReceipt:
        """Bind provider-observed ready state to the exact current finalization."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "mark_awaiting_merge")
        finalization = frontier.finalization
        if finalization is None:
            _conflict("pull-request ready state requires current finalization authority")
        if (
            receipt.change_id != self._contract.change_id
            or receipt.finalization_id != finalization.finalization_id
            or receipt.head_sha != finalization.exact_head
        ):
            _conflict("pull-request ready receipt does not match current finalization authority")
        publication = _pull_request_identity(receipt)
        history = frontier.change_publication_history
        if history is None:
            updated_history = DeliveryChangePublicationHistory.create(publication)
        elif (
            history.current.repository,
            history.current.number,
            history.current.node_id,
        ) == (
            publication.repository,
            publication.number,
            publication.node_id,
        ):
            try:
                updated_history = history.refresh_current(publication)
            except ValueError as exc:
                _conflict(str(exc))
        else:
            _conflict("pull-request ready receipt does not match the current publication")
        if frontier.ready is not None:
            if frontier.ready == receipt:
                if frontier.change_publication_history != updated_history:
                    self._replace(
                        previous,
                        frontier.model_copy(update={"change_publication_history": updated_history}),
                    )
                return receipt
            _conflict("Delivery Change is already awaiting merge with different authority")
        self._replace(
            previous,
            frontier.model_copy(update={"ready": receipt, "change_publication_history": updated_history}),
        )
        return receipt

    def clear_ready_for_head_change(
        self,
        finalization_id: str,
        exact_head: str,
    ) -> PullRequestReadyReceipt | None:
        """Clear local ready authority after its provider pull request returns to draft."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "clear_ready_for_head_change")
        finalization = frontier.finalization
        ready = frontier.ready
        if ready is None:
            return None
        if (
            finalization is None
            or finalization.finalization_id != finalization_id
            or finalization.exact_head != exact_head
            or ready.finalization_id != finalization_id
            or ready.head_sha != exact_head
        ):
            _conflict("ready authority does not match the head-change boundary")
        self._replace(previous, frontier.model_copy(update={"ready": None}))
        return ready

    def reconcile_pull_request_draft_state(
        self,
        *,
        provider_draft: bool,
        observed_at: datetime | None = None,
        observation_id: str | None = None,
    ) -> PullRequestReadyReceipt | None:
        """Retain ready authority only while the provider reports the PR ready."""
        frontier, _previous = self._read()
        _require_change_mutable(frontier, "reconcile_pull_request_draft_state")
        if frontier.ready is None or not provider_draft:
            return frontier.ready
        diagnostics = ((f"pull-request-observation:{observation_id}",) if observation_id is not None else ()) + (
            "provider pull request regressed to draft",
        )
        disposition = DeliveryChangeDisposition.create(
            kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
            change_id=self._contract.change_id,
            entered_from=derive_change_stage(frontier),
            recorded_at=observed_at or datetime.now(UTC),
            diagnostics=diagnostics,
        )
        self.capture_change_disposition(disposition, clear_ready=True)
        return None

    def latch_merged_pull_request(
        self,
        observation: PublicationPullRequestObservationReceipt,
    ) -> DeliveryMergedPullRequestLatch:
        """Persist the first exact merged tuple and reject later regression or drift."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "latch_merged_pull_request")
        finalization = frontier.finalization
        ready = frontier.ready
        snapshot = observation.snapshot
        if finalization is None or ready is None:
            _conflict("merged pull-request evidence requires awaiting-merge authority")
        if (
            observation.change_id != self._contract.change_id
            or ready.change_id != self._contract.change_id
            or ready.finalization_id != finalization.finalization_id
            or snapshot.repository != ready.repository
            or snapshot.number != ready.number
            or snapshot.node_id != ready.node_id
            or snapshot.head_sha != finalization.exact_head
            or snapshot.head_sha != ready.head_sha
        ):
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence does not match awaiting-merge authority",),
                reason=DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
            )
            _conflict("merged pull-request evidence does not match awaiting-merge authority")
        existing = frontier.merged_pull_request_latch
        if existing is not None and (
            snapshot.state != "closed"
            or not snapshot.merged
            or snapshot.merge_commit_sha is None
            or snapshot.merged_at is None
        ):
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence regressed from the immutable merged latch",),
                reason=DeliveryAcceptanceAttentionReason.LATCH_REGRESSION,
            )
            _conflict("provider acceptance evidence regressed from the immutable merged latch")
        if is_acceptance_waiting_observation(observation):
            message = "provider pull request is still open and unmerged"
            raise DeliveryAcceptanceWaitingError(message)
        if not snapshot.merged or snapshot.state != "closed":
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance observation is not merged and closed",),
                reason=DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED,
            )
            _conflict("acceptance observation does not report a merged pull request")
        if snapshot.merged_at is None or snapshot.merge_commit_sha is None:
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance observation is missing merge evidence",),
                reason=DeliveryAcceptanceAttentionReason.MERGE_EVIDENCE_MISSING,
            )
            _conflict("merged pull-request evidence is incomplete")
        candidate = DeliveryMergedPullRequestLatch(
            change_id=self._contract.change_id,
            finalization_id=finalization.finalization_id,
            ready_receipt_id=ready.receipt_id,
            acceptance_observation_id=observation.observation_id,
            provider_evidence_digest=observation.provider_evidence_digest,
            repository=snapshot.repository,
            number=snapshot.number,
            node_id=snapshot.node_id,
            base_branch=snapshot.base_branch,
            head_sha=snapshot.head_sha,
            accepted_merge_commit=snapshot.merge_commit_sha,
            merged_at=snapshot.merged_at,
        )
        if existing is not None:
            if (
                existing.repository,
                existing.number,
                existing.node_id,
                existing.base_branch,
                existing.head_sha,
                existing.accepted_merge_commit,
                existing.merged_at,
            ) == (
                candidate.repository,
                candidate.number,
                candidate.node_id,
                candidate.base_branch,
                candidate.head_sha,
                candidate.accepted_merge_commit,
                candidate.merged_at,
            ):
                return existing
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence conflicts with the immutable merged latch",),
                reason=DeliveryAcceptanceAttentionReason.LATCH_REGRESSION,
            )
            _conflict("merged pull-request evidence conflicts with the immutable latch")
        self._replace(previous, frontier.model_copy(update={"merged_pull_request_latch": candidate}))
        return candidate

    def complete_change(
        self,
        receipt: CompletionReceipt,
        *,
        additional_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...] = (),
    ) -> CompletionReceipt:
        """Atomically publish one terminal receipt and its minimal frontier projection."""
        frontier, previous = self._read()
        store = CompletionReceiptStore(self._target_root)
        try:
            existing_record = store.read_bundle(self._contract.change_id)
        except CompletionReceiptConflictError:
            _conflict("completion record exists with malformed authority")
        display = CompletionDisplayMetadata.create(
            change_id=self._contract.change_id,
            completion_id=receipt.completion_id,
            title=self._contract.title,
            outcome_titles=tuple(outcome.title for outcome in self._contract.outcomes),
            outcome_promises=tuple(outcome.promise for outcome in self._contract.outcomes),
        )
        if frontier.change_completion is not None:
            if (
                existing_record is not None
                and existing_record.receipt == receipt
                and existing_record.display == display
                and frontier.change_completion.completion_id == receipt.completion_id
            ):
                return receipt
            _conflict("Delivery Change is already completed with different authority")
        if existing_record is not None:
            _conflict("completion receipt exists without terminal frontier state")
        _require_change_mutable(frontier, "complete_change")
        finalization = frontier.finalization
        ready = frontier.ready
        latch = frontier.merged_pull_request_latch
        if finalization is None or ready is None or latch is None:
            _conflict("Delivery Change completion requires finalized awaiting-merge evidence")
        if (
            receipt.change_id != self._contract.change_id
            or receipt.finalization_receipt_id != finalization.finalization_id
            or receipt.finalized_change_head != finalization.exact_head
            or receipt.repository_identity != latch.repository
            or receipt.pull_request_identity.number != latch.number
            or receipt.pull_request_identity.node_id != latch.node_id
            or receipt.accepted_target_ref != latch.base_branch
            or receipt.accepted_merge_commit != latch.accepted_merge_commit
            or receipt.merged_at != latch.merged_at
            or receipt.acceptance_observation_id != latch.acceptance_observation_id
            or receipt.review_receipt_ids != (finalization.review.review_id,)
        ):
            _conflict("completion receipt does not match finalization and merged evidence")
        projection = DeliveryChangeCompletion(
            completion_id=receipt.completion_id,
            completed_at=receipt.completed_at,
        )
        replacement = _model_content(frontier.model_copy(update={"change_completion": projection}))
        completion_participant = store.participant(receipt)
        display_participant = store.display_participant(display)
        frontier_participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        pending_participant = self._pending_publication_participant(
            replacement,
            self.publication_base_digest(previous),
        )
        transaction_id = hashlib.sha256(
            completion_participant.content
            + display_participant.content
            + previous
            + replacement
            + b"".join(
                participant.content
                if isinstance(participant, TransactionParticipant)
                else participant.replacement_content
                for participant in additional_participants
            )
        ).hexdigest()
        RuntimeTransaction(
            self._target_root,
            f"delivery-completion-{transaction_id}",
            (
                completion_participant,
                display_participant,
                frontier_participant,
                pending_participant,
                *additional_participants,
            ),
        ).commit()
        return receipt

    def completion_bundle(self) -> CompletionReceiptBundle | None:
        """Return completion evidence only when this Change's frontier records its completion."""
        frontier, _previous = self._read()
        if frontier.change_completion is None:
            return None
        return CompletionReceiptStore(self._target_root).read_bundle(self._contract.change_id)

    def finalize_change(
        self,
        request: FinalizeDeliveryChange,
        finalized_at: datetime,
        *,
        additional_participants: tuple[ReplacementTransactionParticipant, ...] = (),
    ) -> DeliveryFinalizationReceipt:
        """Bind completed authority and final validation to one exact Change head."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "finalize_change")
        existing = frontier.finalization
        if existing is not None:
            if (
                existing.operation_id == request.operation_id
                and existing.exact_head == request.exact_head
                and existing.observations == request.observations
                and existing.review == request.review
            ):
                return existing
            _conflict("Delivery Change is already finalized with different authority")
        if any(binding.stage != DeliveryStage.COMPLETED for binding in frontier.bindings):
            _conflict("Delivery finalization requires every Outcome completed")
        invalidation = frontier.finalization_invalidation
        if (
            invalidation is not None
            and invalidation.reason == "review-repair"
            and request.exact_head == invalidation.expected_head
        ):
            _conflict("review repair requires a new Change commit before finalization")
        if any(binding.active_claim is not None for binding in frontier.bindings):
            _conflict("Delivery finalization cannot overlap an active Outcome claim")
        if frontier.integration_repair_claim is not None:
            _conflict("Delivery finalization cannot overlap an Integration repair claim")
        for binding in frontier.bindings:
            if tuple(result.task_id for result in binding.results) != binding.task_ids:
                _conflict("Delivery finalization requires every Task result in authority order")
        if any(observation.change_id != self._contract.change_id for observation in request.observations):
            _conflict("Delivery finalization observations do not match the Change")
        self._require_finalization_evidence(frontier, request)
        results = tuple(result for binding in frontier.bindings for result in binding.results)
        finalization = DeliveryFinalization(
            operation_id=request.operation_id,
            change_id=self._contract.change_id,
            exact_head=request.exact_head,
            authority_digest=self._authority_digest,
            result_digests=tuple(hashlib.sha256(_model_content(result)).hexdigest() for result in results),
            observations=request.observations,
            review=request.review,
            finalized_at=finalized_at,
        )
        receipt = DeliveryFinalizationReceipt.create(finalization)
        updated = _queue_finalization_checkpoint(
            frontier.model_copy(
                update={
                    "finalization": receipt,
                    "finalization_invalidation": None,
                    "ready": None,
                }
            ),
            request.exact_head,
        )
        replacement = _model_content(updated)
        frontier_participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        participant_content = b"".join(
            b"\0".join(
                (
                    str(participant.root.resolve()).encode(),
                    participant.relative_path.as_posix().encode(),
                    participant.expected_content,
                    participant.replacement_content,
                )
            )
            for participant in additional_participants
        )
        transaction_id = hashlib.sha256(previous + replacement + participant_content).hexdigest()
        RuntimeTransaction(
            self._target_root,
            f"delivery-finalization-{transaction_id}",
            (
                frontier_participant,
                self._pending_publication_participant(replacement, self.publication_base_digest(previous)),
                *additional_participants,
                *self.retry_ledger().owner_result_participants(request.operation_id, accepted=True, now=finalized_at),
            ),
        ).commit()
        return receipt

    def reconcile_finalization_head(
        self,
        observed_head: str,
        invalidated_at: datetime,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain exact finalization or invalidate it after observed Change-head drift."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "reconcile_finalization_head", allow_attention=True)
        finalization = frontier.finalization
        if finalization is None:
            invalidation = frontier.finalization_invalidation
            if invalidation is not None and invalidation.observed_head == observed_head:
                return invalidation
            return None
        if finalization.exact_head == observed_head:
            return finalization
        invalidation = DeliveryFinalizationInvalidationReceipt.create(
            DeliveryFinalizationInvalidation(
                change_id=self._contract.change_id,
                finalization_id=finalization.finalization_id,
                expected_head=finalization.exact_head,
                observed_head=observed_head,
                invalidated_at=invalidated_at,
            )
        )
        updated = frontier.model_copy(
            update={
                "finalization": None,
                "finalization_invalidation": invalidation,
                "ready": None,
                "pending_checkpoint": _invalidate_finalization_checkpoint(frontier.pending_checkpoint),
            }
        )
        self._replace(previous, updated)
        return invalidation

    def prepare_review_repair(
        self,
        expected_finalization_id: str,
        invalidated_at: datetime,
    ) -> DeliveryFinalizationInvalidationReceipt:
        """Invalidate current finalization before repairing external review feedback."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "prepare_review_repair", allow_attention=True)
        finalization = frontier.finalization
        existing = frontier.finalization_invalidation
        if finalization is None:
            if (
                existing is not None
                and existing.reason == "review-repair"
                and existing.finalization_id == expected_finalization_id
            ):
                return existing
            _conflict("review repair requires current finalization authority")
        if finalization.finalization_id != expected_finalization_id:
            _conflict("review repair finalization identity is stale")
        if frontier.merged_pull_request_latch is not None:
            _conflict("merged Change cannot be reopened for review repair")
        if frontier.change_disposition is not None:
            _conflict("review repair requires current Change attention resolution")
        invalidation = DeliveryFinalizationInvalidationReceipt.create(
            DeliveryFinalizationInvalidation(
                change_id=self._contract.change_id,
                finalization_id=finalization.finalization_id,
                expected_head=finalization.exact_head,
                observed_head=finalization.exact_head,
                reason="review-repair",
                invalidated_at=invalidated_at,
            )
        )
        updated = frontier.model_copy(
            update={
                "finalization": None,
                "finalization_invalidation": invalidation,
                "ready": None,
                "pending_checkpoint": _invalidate_finalization_checkpoint(frontier.pending_checkpoint),
            }
        )
        self._replace(previous, updated)
        return invalidation

    def prepare_completed_outcome_repair(
        self,
        request: PrepareCompletedOutcomeRepair,
    ) -> OutcomeAuthorityBinding:
        """Append one derived Builder repair task without erasing prior evidence."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "prepare_completed_outcome_repair", allow_attention=True)
        if frontier.finalization is not None or frontier.ready is not None:
            _conflict("completed-outcome repair requires no successful finalization authority")
        if frontier.merged_pull_request_latch is not None:
            _conflict("merged Change cannot be reopened for completed-outcome repair")
        if self._workspace_manager is None:
            _conflict("completed-outcome repair requires finalizer custody authority")
        binding = _find_binding(frontier, request.outcome_id)
        source = next((task for task in binding.tasks if task.task_id == request.owning_task_id), None)
        if source is None:
            _reference("completed-outcome repair task ownership is absent")
        repair_id = _completed_outcome_repair_id(self._contract.change_id, request, source.digest)
        repair_task_id = f"repair-{repair_id}"
        existing = next((task for task in binding.tasks if task.task_id == repair_task_id), None)
        persisted, lineage = self._completed_outcome_repair_history(
            binding,
            existing,
            repair_id,
            repair_task_id,
        )
        finished_at = persisted.finished_at if persisted is not None else datetime.now(UTC).isoformat()
        receipt = CompletedOutcomeRepairReceipt.create(
            self._contract.change_id,
            request,
            repair_task_id,
            lineage.previous_task_ids,
            lineage.previous_result_ids,
            finished_at,
        )
        repair_binding = self.retry_ledger().repair_binding_participant(
            original_attempt_id=request.original_action_id,
            repair_attempt_id=request.attempt_id,
            repair_task_id=repair_task_id,
            outcome_id=request.outcome_id,
            now=finished_at,
            allow_settled=existing is not None,
        )
        repair = self._completed_outcome_repair_task(source, request, repair_task_id, lineage.previous_task_ids)
        if self._completed_outcome_repair_replay(existing, persisted, repair, receipt):
            return binding
        if binding.stage != DeliveryStage.COMPLETED:
            _conflict("completed-outcome repair requires one completed owning outcome")
        if len(binding.results) != len(binding.tasks) or {result.task_id for result in binding.results} != set(
            binding.task_ids
        ):
            _conflict("completed-outcome repair requires all prior task results")
        if hashlib.sha256(previous).hexdigest() != request.expected_frontier_digest:
            _conflict("completed-outcome repair frontier changed")
        updated_binding = binding.model_copy(
            update={
                "stage": DeliveryStage.IMPLEMENTATION,
                "tasks": (*binding.tasks, repair),
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "recovery_attention": None,
                "return_context": None,
                "block": None,
                "retry_fingerprint": None,
                "retry_count": 0,
            }
        )
        additional_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...] = (
            TransactionParticipant(
                self._target_root,
                journal_path(self._contract.change_id, repair_id, "receipt"),
                encoded(receipt),
            ),
            repair_binding,
        )
        custody = self._workspace_manager.prepare_finalization_repair_release(
            self._contract.change_id,
            request.original_action_id,
            finished_at,
        )
        additional_participants = (*additional_participants, custody)
        if self._workspace_manager.show(self._contract.change_id).pause_request is not None:
            _conflict("Change pause requested")
        replacement = _replace_binding(frontier, binding, updated_binding)
        # The exact finalizer release is one of the participants below, so the
        # ordinary no-active-finalizer guard must not be added here.
        self._replace_content(
            previous,
            _model_content(replacement),
            additional_participants=additional_participants,
        )
        return updated_binding

    def record_target_sync(
        self,
        receipt: ChangeTargetSyncReceipt,
        synced_at: datetime,
    ) -> ChangeTargetSyncReceipt:
        """Persist one exact target-sync result and invalidate stale finalization authority."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_target_sync")
        _require_no_active_change_claim(frontier, "target synchronization")
        _require_no_review_repair(frontier, "target synchronization")
        if receipt.change_id != self._contract.change_id:
            _conflict("target synchronization receipt does not match the admitted Change")
        existing = frontier.target_sync_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("target synchronization operation has different receipt evidence")
            return existing
        updated = self._target_sync_update(frontier, receipt, synced_at)
        self._replace(previous, updated)
        return receipt

    def record_external_head_adoption(
        self,
        receipt: ChangeExternalHeadAdoptionReceipt,
        adopted_at: datetime,
    ) -> ChangeExternalHeadAdoptionReceipt:
        """Persist one adopted external head, invalidate stale finalization, and queue publication."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_external_head_adoption")
        _require_no_active_change_claim(frontier, "external Change head adoption")
        _require_no_review_repair(frontier, "external Change head adoption")
        if adopted_at.tzinfo is None:
            message = "external Change head adoption timestamp must include a timezone"
            raise ValueError(message)
        if receipt.change_id != self._contract.change_id:
            _conflict("external Change head adoption receipt does not match the admitted Change")
        existing = frontier.external_head_adoption_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("external Change head adoption operation has different receipt evidence")
            return existing
        updated = self._external_head_adoption_update(frontier, receipt, adopted_at)
        self._replace(previous, updated)
        return receipt

    def record_external_head_promotion(
        self,
        receipt: ChangeExternalHeadPromotionReceipt,
        promoted_at: datetime,
    ) -> ChangeExternalHeadPromotionReceipt:
        """Persist one exact external Change-head review admission."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_external_head_promotion")
        _require_no_active_change_claim(frontier, "external Change head promotion")
        _require_no_review_repair(frontier, "external Change head promotion")
        if promoted_at.tzinfo is None:
            message = "external Change head promotion timestamp must include a timezone"
            raise ValueError(message)
        if receipt.change_id != self._contract.change_id:
            _conflict("external Change head promotion receipt does not match the admitted Change")
        adoption = frontier.external_head_adoption_receipt
        if adoption is None or receipt.adoption_receipt_id != adoption.receipt_id:
            _conflict("external Change head promotion receipt does not match current adoption evidence")
        if receipt.promoted_head != adoption.adopted_head:
            _conflict("external Change head promotion receipt does not match the adopted head")
        existing = frontier.external_head_promotion_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("external Change head promotion operation has different receipt evidence")
            return existing
        updated = frontier.model_copy(update={"external_head_promotion_receipt": receipt})
        self._replace(previous, updated)
        return receipt

    def record_resolved_target_sync(
        self,
        receipt: ChangeTargetSyncReceipt,
        expected_disposition_id: str,
        operation_id: str,
        synced_at: datetime,
    ) -> ChangeTargetSyncReceipt:
        """Record one resolved merge while atomically clearing its exact attention."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_resolved_target_sync", allow_attention=True)
        _require_no_active_change_claim(frontier, "target synchronization resolution")
        _require_target_sync_attention(frontier, expected_disposition_id, operation_id)
        if receipt.change_id != self._contract.change_id:
            _conflict("target synchronization receipt does not match the admitted Change")
        existing = frontier.target_sync_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("target synchronization operation has different receipt evidence")
            return existing
        updated = self._target_sync_update(frontier, receipt, synced_at)
        resolution = DeliveryChangeDispositionResolution.create(
            change_id=self._contract.change_id,
            disposition_id=expected_disposition_id,
            resolved_at=synced_at,
        )
        updated = updated.model_copy(
            update={
                "change_disposition": None,
                "change_disposition_publication": None,
                "change_disposition_resolution": resolution,
            }
        )
        self._replace(previous, updated)
        return receipt

    def record_target_sync_abort(
        self,
        expected_disposition_id: str,
        operation_id: str,
        resolved_at: datetime,
    ) -> DeliveryChangeDispositionResolution:
        """Clear one exact target-sync attention after its workspace abort receipt exists."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_target_sync_abort", allow_attention=True)
        _require_target_sync_attention(frontier, expected_disposition_id, operation_id)
        _require_no_active_change_claim(frontier, "target synchronization abort")
        resolution = DeliveryChangeDispositionResolution.create(
            change_id=self._contract.change_id,
            disposition_id=expected_disposition_id,
            resolved_at=resolved_at,
        )
        updated = frontier.model_copy(
            update={
                "change_disposition": None,
                "change_disposition_publication": None,
                "change_disposition_resolution": resolution,
            }
        )
        self._replace(previous, updated)
        return resolution

    def _target_sync_update(
        self,
        frontier: DeliveryFrontier,
        receipt: ChangeTargetSyncReceipt,
        synced_at: datetime,
    ) -> DeliveryFrontier:
        if synced_at.tzinfo is None:
            message = "target synchronization timestamp must include a timezone"
            raise ValueError(message)
        finalization = frontier.finalization
        invalidation = frontier.finalization_invalidation
        ready = frontier.ready
        proof = frontier.target_sync_receipt
        if finalization is not None and finalization.exact_head != receipt.merged_head:
            invalidation = DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=self._contract.change_id,
                    finalization_id=finalization.finalization_id,
                    expected_head=finalization.exact_head,
                    observed_head=receipt.merged_head,
                    invalidated_at=synced_at,
                )
            )
            finalization = None
            ready = None
        elif finalization is not None and (proof is None or proof.target_head != receipt.target_head):
            # U3(a) strict proof: a new target needs fresh proof even when the Change head is unchanged.
            finalization = None
            ready = None

        pending = frontier.pending_checkpoint
        triggers = (
            ()
            if pending is None
            else tuple(
                trigger for trigger in pending.triggers if trigger.kind != DeliveryCheckpointTriggerKind.FINALIZATION
            )
        )
        explicit = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT)
        if explicit not in triggers:
            triggers = (*triggers, explicit)
        return frontier.model_copy(
            update={
                "target_sync_receipt": receipt,
                "finalization": finalization,
                "finalization_invalidation": invalidation,
                "ready": ready,
                "pending_checkpoint": _checkpoint_with_head(
                    pending,
                    receipt.merged_head,
                    triggers,
                ),
            }
        )

    def _external_head_adoption_update(
        self,
        frontier: DeliveryFrontier,
        receipt: ChangeExternalHeadAdoptionReceipt,
        adopted_at: datetime,
    ) -> DeliveryFrontier:
        finalization = frontier.finalization
        invalidation = frontier.finalization_invalidation
        ready = frontier.ready
        if finalization is not None and finalization.exact_head != receipt.adopted_head:
            invalidation = DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=self._contract.change_id,
                    finalization_id=finalization.finalization_id,
                    expected_head=finalization.exact_head,
                    observed_head=receipt.adopted_head,
                    invalidated_at=adopted_at,
                )
            )
            finalization = None
            ready = None

        pending = frontier.pending_checkpoint
        triggers = (
            ()
            if pending is None
            else tuple(
                trigger for trigger in pending.triggers if trigger.kind != DeliveryCheckpointTriggerKind.FINALIZATION
            )
        )
        explicit = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT)
        if explicit not in triggers:
            triggers = (*triggers, explicit)
        return frontier.model_copy(
            update={
                "external_head_adoption_receipt": receipt,
                "external_head_promotion_receipt": None,
                "finalization": finalization,
                "finalization_invalidation": invalidation,
                "ready": ready,
                "pending_checkpoint": _checkpoint_with_head(
                    pending,
                    receipt.adopted_head,
                    triggers,
                ),
            }
        )

    def capture_target_sync_conflict(
        self,
        operation_id: str,
        target_head: str,
        recorded_at: datetime,
        diagnostics: tuple[str, ...],
        *,
        publication_identity: DeliveryChangePublicationIdentity | None = None,
    ) -> DeliveryChangeDisposition:
        """Retain target-merge attention and invalidate authority exposed to the conflict."""
        frontier, previous = self._read()
        existing = frontier.change_disposition
        if existing is not None:
            _require_target_sync_attention(frontier, existing.disposition_id, operation_id)
            return existing
        _require_change_mutable(frontier, "capture_target_sync_conflict")
        _require_no_active_change_claim(frontier, "target synchronization attention capture")
        if recorded_at.tzinfo is None:
            message = "target synchronization attention timestamp must include a timezone"
            raise ValueError(message)
        if publication_identity is None and frontier.ready is not None:
            publication_identity = _pull_request_identity(frontier.ready)
        if publication_identity is not None and publication_identity.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")

        invalidation = frontier.finalization_invalidation
        if frontier.finalization is not None:
            if frontier.finalization.exact_head == target_head:
                _conflict("target synchronization conflict head must differ from finalized Change head")
            invalidation = DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=self._contract.change_id,
                    finalization_id=frontier.finalization.finalization_id,
                    expected_head=frontier.finalization.exact_head,
                    observed_head=target_head,
                    reason="target-sync-conflict",
                    invalidated_at=recorded_at,
                )
            )
        disposition = DeliveryChangeDisposition.create(
            kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
            change_id=self._contract.change_id,
            entered_from=self.change_stage(),
            recorded_at=recorded_at,
            diagnostics=(f"target-sync-operation:{operation_id}", *diagnostics),
        )
        updated = frontier.model_copy(
            update={
                "target_sync_receipt": None,
                "change_disposition": disposition,
                "change_disposition_publication": publication_identity,
                "change_disposition_resolution": None,
                "finalization": None,
                "finalization_invalidation": invalidation,
                "ready": None,
                "pending_checkpoint": _invalidate_finalization_checkpoint(frontier.pending_checkpoint),
            }
        )
        self._replace(previous, updated)
        return disposition

    def active_claims(self) -> tuple[tuple[str, DeliveryActiveClaim], ...]:
        """Return active claim identity keyed by outcome in authority order."""
        frontier, _content = self._read()
        return tuple(
            (binding.outcome_id, binding.active_claim)
            for binding in frontier.bindings
            if binding.active_claim is not None
        )

    def remove_integration_repair_claim(self, attempt_id: str, claim_id: str) -> DeliveryActiveClaim:
        """Validate identity but refuse unsupported Integration custody release."""
        frontier, _previous = self._read()
        _require_change_mutable(frontier, "remove_integration_repair_claim")
        claim = frontier.integration_repair_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("claim removal does not match the active Integration repair identity")
        raise DeliveryWorkerExclusionRequiredError

    def remove_active_claim(
        self,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> OutcomeAuthorityBinding:
        """Validate identity but refuse unsupported failed-claim custody release."""
        frontier, _previous = self._read()
        _require_change_mutable(frontier, "remove_active_claim")
        binding = _find_binding(frontier, outcome_id)
        claim = binding.active_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("claim removal does not match the active execution identity")
        raise DeliveryWorkerExclusionRequiredError

    def complete_recovery(self, intent: RecoveryIntent, receipt: RecoveryReceipt) -> None:
        """Atomically publish a verified recovery receipt and retire only its exact owner."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "complete_recovery")
        request = intent.invocation.request
        if request.change_id != self._contract.change_id or digest(previous) != intent.frontier_digest:
            raise DeliveryWorkerExclusionRequiredError
        replacement = frontier
        if intent.kind == "clean-claim":
            binding = self.require_active_claim(request.outcome_id, request.attempt_id, request.owner_id)
            if (
                binding.output is not None
                or binding.result_candidate is not None
                or binding.candidate is not None
                or binding.builder_handoff_context is not None
            ):
                raise DeliveryWorkerExclusionRequiredError
            replacement = _replace_binding(
                frontier,
                binding,
                binding.model_copy(update={"active_claim": None, "recovery_attention": None, "retry_diagnostic": None}),
            )
        elif any(binding.active_claim is not None for binding in frontier.bindings):
            raise DeliveryWorkerExclusionRequiredError
        if frontier.integration_repair_claim is not None:
            raise DeliveryWorkerExclusionRequiredError
        custody = self._require_workspace().prepare_recovery_release(intent, receipt)
        participants = (
            TransactionParticipant(
                self._target_root, journal_path(request.change_id, intent.recovery_id, "receipt"), encoded(receipt)
            ),
            custody,
        )
        # The exact custody replacement and completed receipt replace the ordinary no-change
        # guard. They cannot be split from this centrally admitted frontier mutation.
        portable = not any(binding.active_claim is not None for binding in replacement.bindings)
        portable = portable and not any(binding.builder_handoff_context is not None for binding in replacement.bindings)
        portable = portable and replacement.integration_repair_claim is None
        self._replace_content(
            previous,
            _model_content(replacement),
            record_pending_publication=portable
            and (replacement != frontier or _model_content(replacement) != previous),
            additional_participants=participants,
        )

    def publish_recovery_attention(
        self,
        outcome_id: str,
        attention: DeliveryRecoveryAttention,
    ) -> OutcomeAuthorityBinding:
        """Retain one exact active claim with deterministic operator repair evidence."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_recovery_attention")
        binding = _find_binding(frontier, outcome_id)
        claim = binding.active_claim
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or claim is None
            or claim.attempt_id != attention.attempt_id
            or claim.claim_id != attention.claim_id
        ):
            _conflict("recovery attention does not match an active Build claim")
        if binding.recovery_attention == attention:
            return binding
        updated = binding.model_copy(update={"recovery_attention": attention})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return updated

    def change_stage(self) -> DeliveryChangeStage:
        """Derive change lifecycle from canonical outcome state."""
        return derive_change_stage(self._read()[0])

    def activate_claim(
        self,
        request: ActivateDeliveryClaim,
        *,
        builder_handoff_participant: ReplacementTransactionParticipant | None = None,
        builder_handoff_lock: PublicationLock | None = None,
    ) -> OutcomeAuthorityBinding:
        """Bind one fresh claim to a currently claimable outcome."""
        frontier, previous = self._read()
        if (
            request.expected_frontier_digest is not None
            and hashlib.sha256(previous).hexdigest() != request.expected_frontier_digest
        ):
            message = "selected action frontier changed before claim activation"
            raise DeliveryActionSelectionConflictError(message)
        _require_change_mutable(frontier, "activate_claim")
        binding = _find_binding(frontier, request.outcome_id)
        if frontier.integration_repair_claim is not None:
            _conflict("outcome claims cannot overlap an active Integration repair claim")
        if request.outcome_id not in self.claimable_outcome_ids():
            _conflict("outcome is not claimable")
        if any(item.active_claim_id == request.claim_id for item in frontier.bindings):
            _conflict("active claim identity already exists")
        expected_role = {
            DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
            DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
        }.get(binding.stage)
        if request.claim.worker_role != expected_role:
            _conflict("claim worker role does not match the current Delivery stage")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.task_id not in self.claimable_task_ids(request.outcome_id):
                _conflict("implementation task is not claimable")
        elif request.task_id is not None:
            _conflict("only Implementation claims name a task")
        handoff_participant = self._validate_builder_handoff_activation(
            request,
            binding,
            builder_handoff_participant,
            builder_handoff_lock,
        )
        claimed = binding.model_copy(
            update={
                "active_claim": request.claim,
                "output": None,
                "result_candidate": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
            }
        )
        self._replace(
            previous,
            _replace_binding(frontier, binding, claimed),
            additional_participants=(handoff_participant,) if handoff_participant is not None else (),
            include_custody_guard=handoff_participant is None,
        )
        return claimed

    def publish_output(self, request: PublishDeliveryOutput) -> DeliveryOutputReference:
        """Persist one exact active-claim output without changing stage."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_output")
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if (
            request.output.claim_id != request.claim_id
            or request.output.stage != binding.stage
            or request.output.kind.value != binding.stage.value
        ):
            _conflict("output does not match the active claim and stage")
        updated = binding.model_copy(update={"output": request.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return request.output

    def publish_plan(self, request: PublishDeliveryPlan) -> DeliveryPlanCandidate:
        """Validate and persist one idempotent Planning candidate without movement."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_plan")
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if binding.stage != DeliveryStage.PLANNING:
            _conflict("task-chain publication requires Planning stage")
        self._validate_plan(binding, request.tasks)
        digest = hashlib.sha256(b"".join(_model_content(task) for task in request.tasks)).hexdigest()
        candidate = DeliveryPlanCandidate(
            candidate_id=f"plan-{digest}",
            claim_id=request.claim_id,
            digest=digest,
            tasks=request.tasks,
        )
        if binding.candidate == candidate:
            return candidate
        if binding.candidate is not None:
            _conflict("active claim already published another task-chain candidate")
        updated = binding.model_copy(update={"candidate": candidate, "output": candidate.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return candidate

    def publish_result(self, request: PublishDeliveryResult) -> DeliveryResultCandidate:
        """Validate and persist one idempotent compact result without movement."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_result")
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_task_id is None:
            _conflict("result publication requires an active Implementation task")
        task = next((item for item in binding.tasks if item.task_id == binding.active_task_id), None)
        if task is None:
            _reference("active Implementation task authority is absent")
        if (
            request.result.change_id != self._contract.change_id
            or request.result.authority_digest != self._authority_digest
            or request.result.task_id != task.task_id
            or request.result.task_digest != task.digest
        ):
            _conflict("compact result does not match promoted task authority")
        if request.result.review.review_mode == "finalization":
            _conflict("a task result review cannot use finalization mode")
        gaps = self._evidence_gaps(frontier, request.result.observations, binding.outcome_id)
        if gaps:
            raise DeliveryAcceptanceEvidenceError(gaps)
        digest = hashlib.sha256(_model_content(request.result)).hexdigest()
        candidate = DeliveryResultCandidate(
            candidate_id=f"result-{digest}",
            claim_id=request.claim_id,
            digest=digest,
            result=request.result,
        )
        if binding.result_candidate == candidate:
            return candidate
        if binding.result_candidate is not None:
            _conflict("active claim already published another result candidate")
        self._require_workspace().validate_writer_head(
            self._contract.change_id,
            request.claim_id,
            request.result.completed_commit,
        )
        updated = binding.model_copy(update={"result_candidate": candidate, "output": candidate.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return candidate

    def transition(
        self, request: DeliveryTransition, *, retry_observed_at: datetime | str | None = None
    ) -> OutcomeAuthorityBinding:
        """Apply one worker-owned mechanical transition instruction."""
        frontier, previous = self._read()
        request_digest = hashlib.sha256(_model_content(request)).hexdigest()
        replay_result = self._planning_pause_replay_result(request, request_digest)
        if replay_result is not None:
            return replay_result
        _require_change_mutable(frontier, "transition")
        binding = _find_binding(frontier, request.outcome_id)
        pending_publication = self.pending_state_publication()
        if self._pending_transition_matches(pending_publication, previous, request_digest):
            return binding
        _require_claim(binding, request.claim_id)
        if self._workspace_manager is not None:
            self._workspace_manager.prepare_runtime_custody_guard(
                self._contract.change_id, operation="transition", mutation_class="completion"
            )
        updated = self._transitioned_binding(binding, request)
        if isinstance(request, AdvanceDelivery) and binding.builder_handoff_context is not None:
            updated = self._advanced_builder_handoff(binding, updated)
        replacement = _replace_binding(frontier, binding, updated)
        result_participants = ()
        if isinstance(request, AdvanceDelivery) and binding.stage == DeliveryStage.IMPLEMENTATION:
            replacement = _queue_promoted_result_checkpoint(replacement, frontier, binding, updated)
            candidate = binding.result_candidate
            if candidate is None:
                _conflict("result promotion requires original claim custody")
            result_participants = (
                TransactionParticipant(
                    self._target_root,
                    self._result_receipt_path(binding.outcome_id, candidate.digest),
                    _model_content(candidate),
                ),
            )
        if (
            isinstance(request, AdvanceDelivery)
            and binding.stage == DeliveryStage.PLANNING
            and binding.builder_handoff_context is not None
            and binding.builder_handoff_context.route == "same-outcome-planner"
        ):
            promotion_receipt = _DeliveryBuilderPlanPromotionReceipt.create(
                change_id=self._contract.change_id,
                source_binding=binding,
                result_binding=updated,
            )
            result_participants = (
                *result_participants,
                self._builder_plan_promotion_receipt_participant(promotion_receipt),
            )
        if isinstance(request, (AdvanceDelivery, BlockDelivery, ReturnDelivery)) and binding.active_claim is not None:
            paused = (
                isinstance(request, BlockDelivery)
                and binding.stage == DeliveryStage.PLANNING
                and request.request is not None
            )
            result_participants = (
                *result_participants,
                *self.retry_ledger().owner_result_participants(
                    binding.active_claim.attempt_id,
                    accepted=isinstance(request, AdvanceDelivery),
                    accepted_progress=not paused,
                    paused=paused,
                    now=retry_observed_at or datetime.now(UTC),
                    failure_code="worker-returned" if isinstance(request, ReturnDelivery) else "worker-blocked",
                ),
            )
        result_participants = (
            *result_participants,
            *self._planning_pause_replay_participants(request, binding, updated, request_digest),
        )
        if isinstance(request, AdvanceDelivery):
            result_participants = (
                *result_participants,
                *self._repair_owner_result_participants(
                    binding,
                    retry_observed_at=retry_observed_at or datetime.now(UTC),
                ),
            )
        self._replace(
            previous, replacement, transition_request_digest=request_digest, additional_participants=result_participants
        )
        return _find_binding(replacement, request.outcome_id)

    def settle_planning_retry(
        self, envelope: DeliveryPlanningRetrySettlement, *, retry_observed_at: datetime | str | None = None
    ) -> OutcomeAuthorityBinding:
        """Settle one exact normally returned, completed-timeout, or ended-without-result Planner invocation."""
        envelope_type = type(envelope)
        if envelope_type not in {DeliveryPlanningRetrySettlement, DeliveryEnginePlanningSettlement}:
            _conflict("Planning retry settlement requires a typed completed-invocation envelope")
        try:
            envelope = envelope_type.model_validate_json(_model_content(envelope), strict=True)
        except TypeError, ValueError:
            _conflict("Planning retry settlement envelope is invalid")
        if envelope.change_id != self._contract.change_id:
            _conflict("Planning retry settlement belongs to another Change")

        frontier, previous = self._read()
        replay_result = self._planning_retry_settlement_replay_result(envelope)
        if replay_result is not None:
            return replay_result
        _require_change_mutable(frontier, "settle_planning_retry")
        binding = _find_binding(frontier, envelope.outcome_id)
        claim = binding.active_claim
        if binding.stage != DeliveryStage.PLANNING or claim is None:
            _conflict("Planning retry settlement requires an active Planner claim")
        if claim.claim_id != envelope.claim_id or claim.attempt_id != envelope.attempt_id:
            _conflict("Planning retry settlement does not match the active claim and attempt")
        if claim.worker_role != DeliveryWorkerRole.PLANNER or claim.task_id is not None:
            _conflict("Planning retry settlement cannot accept a Builder task")

        if envelope.disposition == "normal-return":
            request = envelope.request
            if request is None:
                _conflict("normal Planner retry settlement requires its unchanged RetryDelivery")
            self._validate_retry_identity(binding, request, claim)
            failure_code = request.failure_code
        else:
            failure_code = REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES[envelope.disposition]

        result = binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
            }
        )
        receipt = _DeliveryPlanningRetrySettlementReceipt(envelope=envelope, result=result)
        participants = (
            *self.retry_ledger().owner_result_participants(
                claim.attempt_id,
                accepted=False,
                accepted_progress=True,
                failure_code=failure_code,
                now=retry_observed_at or datetime.now(UTC),
            ),
            self._planning_retry_settlement_participant(receipt),
        )
        self._replace(
            previous,
            _replace_binding(frontier, binding, result),
            transition_request_digest=hashlib.sha256(_model_content(envelope)).hexdigest(),
            additional_participants=participants,
        )
        return result

    def settle_builder_invocation(
        self,
        envelope: DeliveryBuilderInvocationSettlement,
        *,
        retry_observed_at: datetime | str | None = None,
    ) -> OutcomeAuthorityBinding:
        """Settle one exact Builder invocation without rewriting its registered worktree."""
        envelope_type = type(envelope)
        if envelope_type not in {DeliveryBuilderInvocationSettlement, DeliveryEngineBuilderSettlement}:
            _conflict("Builder invocation settlement requires a typed completed-invocation envelope")
        try:
            envelope = envelope_type.model_validate_json(_model_content(envelope), strict=True)
        except TypeError, ValueError:
            _conflict("Builder invocation settlement envelope is invalid")
        if envelope.change_id != self._contract.change_id:
            _conflict("Builder invocation settlement belongs to another Change")
        manager = self._require_workspace()
        with manager._coordinator.publication_lock(envelope.change_id) as lock:  # noqa: SLF001
            frontier, previous = self._read()
            replay_result = self._builder_invocation_settlement_replay_result(envelope)
            if replay_result is not None:
                return replay_result
            _require_change_mutable(frontier, "settle_builder_invocation")
            binding = _find_binding(frontier, envelope.outcome_id)
            claim, prepared = self._prepare_builder_invocation_handoff(binding, envelope, manager, lock)
            ledger, episode = self._builder_invocation_retry_episode(envelope)
            settlement_id = hashlib.sha256(_model_content(envelope)).hexdigest()
            original_task = next((task for task in binding.tasks if task.task_id == envelope.task_id), None)
            if original_task is None:
                _reference("Builder invocation settlement task authority is absent")
            context = DeliveryBuilderHandoffContext(
                settlement_id=settlement_id,
                original_task_id=envelope.task_id,
                outcome_id=envelope.outcome_id,
                attempt_id=envelope.attempt_id,
                last_reviewed_commit=envelope.expected_last_reviewed_commit,
                branch_head=prepared.metadata.branch_head,
                metadata_fingerprint=prepared.metadata.fingerprint,
                route=(
                    "same-outcome-design"
                    if isinstance(envelope.request, ReturnDelivery) and envelope.request.target == DeliveryStage.DESIGN
                    else "same-outcome-planner"
                    if isinstance(envelope.request, ReturnDelivery)
                    else "same-task"
                ),
                original_task_commitment_ids=original_task.commitment_ids,
                original_task_maintained_surfaces=original_task.maintained_surfaces,
            )
            result, paused, failure_code = self._builder_invocation_settled_binding(
                binding, envelope, context, episode, ledger
            )
            receipt = _DeliveryBuilderInvocationSettlementReceipt(
                settlement_id=settlement_id,
                envelope=envelope,
                handoff_context=context,
                result=result,
            )
            participants = (
                *ledger.owner_result_participants(
                    claim.attempt_id,
                    accepted=False,
                    accepted_progress=not paused,
                    paused=paused,
                    failure_code=failure_code,
                    now=retry_observed_at or datetime.now(UTC),
                ),
                self._builder_invocation_settlement_participant(receipt),
                prepared.participant,
            )
            replacement = _replace_binding(frontier, binding, result)
            portable = not any(item.active_claim is not None for item in replacement.bindings)
            portable = portable and not any(item.builder_handoff_context is not None for item in replacement.bindings)
            portable = portable and replacement.integration_repair_claim is None
            self._replace_content(
                previous,
                _model_content(replacement),
                record_pending_publication=portable,
                transition_request_digest=settlement_id,
                additional_participants=participants,
            )
            return result

    def release_design_return(self) -> OutcomeAuthorityBinding:
        """Preserve and release one retained Design-return handoff into a plain Design return (N04 §1.7)."""
        manager = self._require_workspace()
        with manager._coordinator.publication_lock(self._contract.change_id) as lock:  # noqa: SLF001
            frontier, previous = self._read()
            _require_change_mutable(frontier, "release_design_return")
            _require_no_active_change_claim(frontier, "Design return release")
            binding = next((item for item in frontier.bindings if item.builder_handoff_context is not None), None)
            context = binding.builder_handoff_context if binding is not None else None
            handoff = manager.show(self._contract.change_id).builder_handoff
            if (
                binding is None
                or context is None
                or context.route != "same-outcome-design"
                or handoff is None
                or handoff.settlement_id != context.settlement_id
                or handoff.branch_head != context.branch_head
                or handoff.metadata_fingerprint != context.metadata_fingerprint
            ):
                _conflict("Design return release requires one exact retained Design-route handoff")
            participant = manager.release_design_return(self._contract.change_id, handoff, lock)
            # A Design return declares the outcome's Design wrong: its tasks and results go, as in a claim-held return.
            released = binding.model_copy(
                update={"tasks": (), "results": (), "builder_handoff_context": None, "block": None}
            )
            # The handoff was never published; the remote still holds the last acknowledged state.
            marker = (
                DeliveryPendingStatePublication.model_validate_json(
                    self._pending_publication_path.read_bytes(), strict=True
                )
                if self._pending_publication_path.is_file()
                else None
            )
            base = (
                self.publication_base_digest(previous)
                if marker is None
                else marker.frontier_digest
                if marker.status == "acknowledged"
                else marker.base_frontier_digest
            )
            self._replace_content(
                previous,
                _model_content(_replace_binding(frontier, binding, released)),
                base_frontier_digest=base,
                additional_participants=(participant,),
            )
            return released

    def resolve_request(
        self,
        request_id: str,
        resolution: DeliveryRequestResolution,
    ) -> DeliveryRequest:
        """Persist one user answer and clear its same-stage block."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "resolve_request")
        binding, request = _find_request(frontier, request_id)
        _require_no_active_change_claim(frontier, "request resolution")
        handoff_retained = any(item.builder_handoff_context is not None for item in frontier.bindings)
        if handoff_retained and (
            binding.builder_handoff_context is None
            or binding.builder_handoff_context.route not in {"same-task", "same-outcome-planner"}
            or binding.block is None
            or binding.block.request_id != request_id
        ):
            _conflict("request resolution cannot mutate outside the exact retained Builder handoff")
        if request.kind is DeliveryRequestKind.DECISION and resolution.selected_option_id is None:
            _reference("Decision requests require a selected option")
        if request.resolution is not None:
            if request.resolution == resolution:
                return request
            _conflict("request is already resolved")
        if resolution.selected_option_id is not None and resolution.selected_option_id not in {
            option.option_id for option in request.options
        }:
            _reference("selected request option is absent")
        resolved = request.model_copy(update={"resolution": resolution})
        requests = tuple(resolved if item == request else item for item in binding.requests)
        block = binding.block
        if block is None or block.request_id != request_id:
            _conflict("request does not own the current block")
        cleared = block.model_copy(
            update={
                "resolution_note": resolution.response_text or resolution.selected_option_id,
                "resolution_locators": (request_id,),
            }
        )
        updated = binding.model_copy(update={"requests": requests, "block": cleared})
        receipt_participant = self._builder_request_resolution_receipt_participant(
            binding,
            request,
            resolved,
            cleared,
        )
        if receipt_participant is None and handoff_retained:
            return_context = self._planner_handoff_pause_return_context(binding)
            if return_context is None:
                _conflict("request resolution lacks the exact retained Builder handoff receipt")
            updated = updated.model_copy(update={"return_context": return_context})
        self._replace(
            previous,
            _replace_binding(frontier, binding, updated),
            additional_participants=(receipt_participant,) if receipt_participant is not None else (),
        )
        return resolved

    def unblock(
        self,
        outcome_id: str,
        block_id: str,
        operator_note: str,
        locators: tuple[str, ...],
    ) -> OutcomeAuthorityBinding:
        """Clear a requestless same-stage block with operator evidence."""
        if not operator_note or not locators:
            message = "requestless unblock requires an operator note and locators"
            raise ValueError(message)
        frontier, previous = self._read()
        _require_change_mutable(frontier, "unblock")
        binding = _find_binding(frontier, outcome_id)
        handoff_retained = any(item.builder_handoff_context is not None for item in frontier.bindings)
        if handoff_retained and (
            binding.builder_handoff_context is None or binding.builder_handoff_context.route != "same-outcome-planner"
        ):
            _conflict("requestless unblock cannot mutate while a Builder handoff is retained")
        block = binding.block
        if block is None or block.block_id != block_id or block.request_id is not None:
            _conflict("requestless block is not clearable")
        _require_no_active_change_claim(frontier, "requestless block resolution")
        if block.resolved:
            if block.resolution_note == operator_note and block.resolution_locators == locators:
                return binding
            _conflict("requestless block is not clearable")
        cleared = block.model_copy(update={"resolution_note": operator_note, "resolution_locators": locators})
        updated = binding.model_copy(update={"block": cleared})
        if handoff_retained:
            return_context = self._planner_handoff_pause_return_context(binding)
            if return_context is None:
                _conflict("requestless unblock cannot mutate while a Builder handoff is retained")
            updated = updated.model_copy(update={"return_context": return_context})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return updated

    def grant_builder_attempt(
        self,
        outcome_id: str,
        block_id: str,
        *,
        now: datetime | str | None = None,
    ) -> OutcomeAuthorityBinding:
        """Fund one more same-task Builder attempt after its exact retry episode was exhausted.

        The frontier, retry ledger and grant receipt commit in one transaction; retry history
        is preserved and a later exhaustion needs another grant.
        """
        frontier, previous = self._read()
        _require_change_mutable(frontier, "grant_builder_attempt")
        binding = _find_binding(frontier, outcome_id)
        context = binding.builder_handoff_context
        block = binding.block
        if (
            context is None
            or context.route != "same-task"
            or binding.stage != DeliveryStage.IMPLEMENTATION
            or block is None
            or block.block_id != block_id
            or block_id != builder_attempt_limit_block_id(context)
            or block.request_id is not None
        ):
            _conflict("attempt grant requires the exact exhausted same-task Builder block")
        if block.resolved:
            receipt = _read_builder_attempt_grant_receipt(self._target_root, self._contract.change_id, context)
            if receipt is not None and receipt.updated_block == block:
                return binding
            _conflict("Builder attempt-limit block is already resolved")
        _require_no_active_change_claim(frontier, "Builder attempt grant")
        settlement = self._read_builder_invocation_settlement_receipt(context)
        if (
            settlement.handoff_context != context
            or settlement.result != binding
            or settlement.envelope.change_id != self._contract.change_id
        ):
            _conflict("attempt grant does not match its exact Builder settlement")
        try:
            ledger_participant, episode = self.retry_ledger().prepare_attempt_grant(context.attempt_id, now=now)
        except (RetryAttemptGrantError, RetryLedgerConflictError, RetryLedgerCorruptError) as exc:
            message = "attempt grant requires the exact exhausted Builder retry episode"
            raise DeliveryRuntimeConflictError(message) from exc
        updated_block = block.model_copy(
            update={
                "resolution_note": BUILDER_ATTEMPT_GRANT_NOTE,
                "resolution_locators": (context.settlement_id,),
            }
        )
        receipt = _DeliveryBuilderAttemptGrantReceipt(
            change_id=self._contract.change_id,
            outcome_id=outcome_id,
            settlement_id=context.settlement_id,
            attempt_id=context.attempt_id,
            episode_id=episode.episode_id,
            granted_attempts=episode.granted_attempts,
            builder_handoff_context=context,
            granted_block=block,
            updated_block=updated_block,
        )
        receipt_path = _builder_attempt_grant_receipt_path(self._target_root, self._contract.change_id, context)
        if any(
            path.is_symlink()
            for path in (self._target_root / "changes", self._frontier_path.parent, receipt_path.parent, receipt_path)
        ):
            _reference("Builder attempt grant receipt path is unsafe")
        updated = binding.model_copy(update={"block": updated_block})
        self._replace(
            previous,
            _replace_binding(frontier, binding, updated),
            additional_participants=(
                TransactionParticipant(
                    self._target_root,
                    receipt_path.relative_to(self._target_root),
                    _model_content(receipt),
                ),
                ledger_participant,
            ),
        )
        return updated

    def administrative_move(
        self,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Move backward and invalidate the completed dependent closure."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "administrative_move")
        _require_no_active_change_claim(frontier, "administrative movement")
        if frontier.finalization is not None:
            _conflict("administrative movement cannot cross finalized Change authority")
        if hashlib.sha256(previous).hexdigest() != request.expected_version:
            _conflict("administrative movement preview is stale")
        ordered = _administrative_move_closure(self._contract, frontier, request.outcome_id, request.target)
        self._require_no_handoff_in_administrative_closure(frontier, ordered)
        invalidated = set(ordered)
        updated_bindings = tuple(
            _reset_binding(item, request.target if item.outcome_id == request.outcome_id else DeliveryStage.PLANNING)
            if item.outcome_id in invalidated
            else item
            for item in frontier.bindings
        )
        move = DeliveryOperatorMove(
            move_id=request.move_id,
            outcome_id=request.outcome_id,
            destination=request.target,
            reason=request.reason,
            invalidated_outcome_ids=ordered,
        )
        if any(item.move_id == move.move_id for item in frontier.operator_moves):
            _conflict("operator move identity already exists")
        updated = frontier.model_copy(
            update={
                "bindings": updated_bindings,
                "operator_moves": (*frontier.operator_moves, move),
                "integration_attention": None,
                "pending_checkpoint": invalidate_checkpoint_publication(
                    frontier.pending_checkpoint,
                    invalidated,
                ),
            }
        )
        self._replace(previous, updated)
        return AdministrativeDeliveryMoveResult(move=move, invalidated_outcome_ids=ordered)

    def _retry(
        self,
        binding: OutcomeAuthorityBinding,
        request: RetryDelivery,
    ) -> OutcomeAuthorityBinding:
        claim = binding.active_claim
        if claim is None:
            _conflict("retry requires an active claim")
        self._validate_retry_identity(binding, request, claim)
        diagnostic = DeliveryRetryDiagnostic(attempt_id=claim.attempt_id, transition=request)
        frontier, previous = self._read()
        _require_change_mutable(frontier, "_retry")
        current = _find_binding(frontier, binding.outcome_id)
        if current != binding:
            _conflict("active claim changed before retry diagnostic persistence")
        if current.retry_diagnostic is not None:
            if current.retry_diagnostic == diagnostic:
                raise DeliveryWorkerExclusionRequiredError
            _conflict("active claim already has a different refused retry diagnostic")
        updated = current.model_copy(update={"retry_diagnostic": diagnostic})
        self._replace(previous, _replace_binding(frontier, current, updated))
        raise DeliveryWorkerExclusionRequiredError

    def _read(self) -> tuple[DeliveryFrontier, bytes]:
        RuntimeTransaction.recover_all(self._target_root)
        try:
            content = self._frontier_path.read_bytes()
            frontier, stored = parse_delivery_frontier(content)
            self._validate_frontier(frontier)
            version = stored_frontier_version(content)
            if stored != content and version == _FRONTIER_SCHEMA_VERSION and not state_is_read_only():
                self._replace_content(content, stored, record_pending_publication=False)
        except (OSError, TypeError, ValueError) as exc:
            message = f"Delivery frontier is missing or invalid: {self._contract.change_id}"
            raise DeliveryRuntimeReferenceError(message) from exc
        if version not in {_READABLE_LEGACY_FRONTIER_SCHEMA_VERSION, _FRONTIER_SCHEMA_VERSION}:
            message = f"Delivery frontier needs its registered fenced migration: {self._contract.change_id}"
            raise DeliveryRuntimeReferenceError(message)
        return frontier, stored

    def _replace(
        self,
        previous: bytes,
        frontier: DeliveryFrontier,
        *,
        transition_request_digest: str | None = None,
        additional_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...] = (),
        include_custody_guard: bool = True,
    ) -> None:
        operation = _consume_declared_mutation()
        guarded = self._workspace_manager is not None and include_custody_guard
        portable = not any(binding.active_claim is not None for binding in frontier.bindings)
        portable = portable and not any(binding.builder_handoff_context is not None for binding in frontier.bindings)
        portable = portable and frontier.integration_repair_claim is None
        for attempt in range(_GUARD_RETRY_LIMIT):
            participants = additional_participants
            if guarded and self._workspace_manager is not None:
                guard = self._workspace_manager.prepare_runtime_custody_guard(
                    self._contract.change_id,
                    operation=operation,
                    mutation_class=pause_mutation_class(operation),
                )
                participants = (*participants, guard)
            try:
                self._replace_content(
                    previous,
                    _model_content(frontier),
                    transition_request_digest=transition_request_digest if portable else None,
                    record_pending_publication=portable,
                    additional_participants=participants,
                )
            except TransactionConflictError:
                # K6: a concurrent Pause write changes only coordination; re-prepare the guard and retry.
                if not guarded or attempt == _GUARD_RETRY_LIMIT - 1 or self._frontier_path.read_bytes() != previous:
                    raise
                continue
            return

    def _replace_content(  # noqa: PLR0913 - one transaction binds state, publication intent, and immutable receipts.
        self,
        previous: bytes,
        replacement: bytes,
        *,
        record_pending_publication: bool = True,
        transition_request_digest: str | None = None,
        base_frontier_digest: str | None = None,
        additional_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...] = (),
    ) -> None:
        """Transactionally replace frontier bytes and its local publication intent."""
        _consume_declared_mutation()
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = [
            participant,
            *additional_participants,
        ]
        if record_pending_publication:
            participants.append(
                self._pending_publication_participant(
                    replacement,
                    base_frontier_digest or self.publication_base_digest(previous),
                    transition_request_digest,
                )
            )
        transaction_id = hashlib.sha256(previous + replacement).hexdigest()
        RuntimeTransaction(self._target_root, f"delivery-runtime-{transaction_id}", tuple(participants)).commit()

    def _evidence_gaps(
        self,
        frontier: DeliveryFrontier,
        observations: tuple[DeliveryLegacyObservationReceipt | DeliveryObservationReceipt, ...],
        outcome_id: str | None,
        *,
        finalization: bool = False,
    ) -> tuple[DeliveryEvidenceGap, ...]:
        """Return why submitted records are not admissible evidence (section 1.6 of the N03 plan)."""
        criteria = acceptance_criteria(self._contract)
        gaps: list[DeliveryEvidenceGap] = []
        for observation in observations:
            gaps.extend(observation_gaps(observation, frontier, criteria, outcome_id))
            if isinstance(observation, DeliveryObservationReceipt) and (
                observation.verdict == "failed" or (finalization and observation.verdict == "missing")
            ):
                gaps.append(DeliveryEvidenceGap(observation_id=observation.observation_id, reason=observation.verdict))
        return tuple(gaps)

    def finalization_diff_base(self, frontier: DeliveryFrontier | None = None) -> str | None:
        """Return the engine-derived diff base: the latest target sync, else the publication base."""
        frontier = self._read()[0] if frontier is None else frontier
        if frontier.target_sync_receipt is not None:
            return frontier.target_sync_receipt.target_head
        if self._workspace_manager is None:
            return None
        return self._workspace_manager.show(self._contract.change_id).publication_base_head

    def finalization_semantics(
        self,
        change_head: str | None,
    ) -> DeliveryFinalizationSemantics | DeliveryContextRefusal:
        """Return the complete finalization semantics for one head, or its typed refusal (D12)."""
        frontier = self._read()[0]
        return finalization_semantics_or_refusal(
            self._contract,
            frontier.model_copy(update={"finalization": None}),
            contract_digest=self._authority_digest,
            change_head=change_head,
            diff_base=self.finalization_diff_base(frontier),
        )

    def _require_finalization_evidence(self, frontier: DeliveryFrontier, request: FinalizeDeliveryChange) -> None:
        """Refuse finalization unless records, review basis and coverage all hold (section 1.6 of the N03 plan)."""
        gaps = [
            *self._evidence_gaps(frontier, request.observations, None, finalization=True),
            *self._finalization_review_gaps(frontier, request),
            *evaluate_acceptance_evidence(self._contract, frontier, request.observations).gaps,
        ]
        if gaps:
            raise DeliveryAcceptanceEvidenceError(tuple(gaps))

    def _finalization_review_gaps(
        self,
        frontier: DeliveryFrontier,
        request: FinalizeDeliveryChange,
    ) -> tuple[DeliveryEvidenceGap, ...]:
        review = request.review
        gaps: list[DeliveryEvidenceGap] = []
        semantics = finalization_semantics_or_refusal(
            self._contract,
            frontier,
            contract_digest=self._authority_digest,
            change_head=request.exact_head,
            diff_base=self.finalization_diff_base(frontier),
        )
        if isinstance(semantics, DeliveryContextRefusal):
            gaps.append(DeliveryEvidenceGap(reason=semantics.code))
        elif review.review_mode != "finalization" or review.basis_digest is None:
            gaps.append(DeliveryEvidenceGap(reason="review-basis-missing"))
        elif review.basis_digest != semantics.basis_digest:
            gaps.append(DeliveryEvidenceGap(reason="review-basis-stale"))
        if review.review_mode == "finalization" and review.observation_ids != tuple(
            observation.observation_id for observation in request.observations
        ):
            gaps.append(DeliveryEvidenceGap(reason="review-observations-mismatch"))
        return tuple(gaps)

    def _validate_frontier(self, frontier: DeliveryFrontier) -> None:
        expected = tuple((scope.outcome_id, scope.scope_id) for scope in self._contract.plan_scopes)
        actual = tuple((binding.outcome_id, binding.plan_scope_id) for binding in frontier.bindings)
        if actual != expected:
            _reference("Delivery frontier does not match its admitted contract")
        resolution = frontier.change_disposition_resolution
        if resolution is not None and resolution.change_id != self._contract.change_id:
            _reference("Delivery Change attention resolution does not match its admitted Change")
        history = frontier.change_publication_history
        if history is not None and history.change_id != self._contract.change_id:
            _reference("Delivery publication history does not match its admitted Change")
        target_sync = frontier.target_sync_receipt
        if target_sync is not None and target_sync.change_id != self._contract.change_id:
            _reference("Delivery target synchronization receipt does not match its admitted Change")
        adoption = frontier.external_head_adoption_receipt
        if adoption is not None and adoption.change_id != self._contract.change_id:
            _reference("Delivery external Change-head adoption receipt does not match its admitted Change")
        promotion = frontier.external_head_promotion_receipt
        if promotion is not None and (
            promotion.change_id != self._contract.change_id
            or adoption is None
            or promotion.adoption_receipt_id != adoption.receipt_id
            or promotion.promoted_head != adoption.adopted_head
        ):
            _reference("Delivery external Change-head promotion receipt does not match its adoption evidence")
        for receipt in (frontier.change_deferral, frontier.change_abandonment):
            if receipt is not None and receipt.change_id != self._contract.change_id:
                _reference("Delivery Change lifecycle receipt does not match its admitted Change")


__all__ = [
    "DELIVERY_TRANSITION_ADAPTER",
    "ActivateDeliveryClaim",
    "AdministrativeDeliveryMove",
    "AdministrativeDeliveryMoveResult",
    "AdvanceDelivery",
    "BlockDelivery",
    "CompletedOutcomeRepairReceipt",
    "DeliveryAcceptanceAttentionReason",
    "DeliveryAcceptanceEvidenceError",
    "DeliveryAcceptanceWaitingError",
    "DeliveryBlock",
    "DeliveryBuilderInvocationSettlement",
    "DeliveryChangeAbandonment",
    "DeliveryChangeCompletion",
    "DeliveryChangeDeferral",
    "DeliveryChangeDisposition",
    "DeliveryChangeDispositionBusyError",
    "DeliveryChangeDispositionConflictError",
    "DeliveryChangeDispositionKind",
    "DeliveryChangeDispositionResolution",
    "DeliveryChangePublicationHistory",
    "DeliveryChangePublicationIdentity",
    "DeliveryChangeStage",
    "DeliveryCheckpointPublicationState",
    "DeliveryCheckpointTrigger",
    "DeliveryCheckpointTriggerKind",
    "DeliveryConfirmationError",
    "DeliveryConfirmationScope",
    "DeliveryEvidenceGap",
    "DeliveryFinalization",
    "DeliveryFinalizationInvalidation",
    "DeliveryFinalizationInvalidationReceipt",
    "DeliveryFinalizationReceipt",
    "DeliveryFrontier",
    "DeliveryIntegrationAttention",
    "DeliveryIntegrationAttentionCode",
    "DeliveryLegacyObservation",
    "DeliveryLegacyObservationReceipt",
    "DeliveryMergedPullRequestLatch",
    "DeliveryObservation",
    "DeliveryObservationReceipt",
    "DeliveryOperatorMove",
    "DeliveryOutputKind",
    "DeliveryOutputReference",
    "DeliveryPendingCheckpoint",
    "DeliveryPendingStatePublication",
    "DeliveryPlanningRetrySettlement",
    "DeliveryRequest",
    "DeliveryRequestKind",
    "DeliveryRequestOption",
    "DeliveryRequestResolution",
    "DeliveryResultCandidate",
    "DeliveryReturnContext",
    "DeliveryReview",
    "DeliveryReviewReceipt",
    "DeliveryRuntime",
    "DeliveryRuntimeConflictError",
    "DeliveryRuntimeReferenceError",
    "DeliveryStage",
    "DeliveryTaskDefinition",
    "DeliveryTaskResult",
    "FinalizeDeliveryChange",
    "OutcomeAuthorityBinding",
    "PrepareCompletedOutcomeRepair",
    "PublishDeliveryOutput",
    "PublishDeliveryPlan",
    "PublishDeliveryResult",
    "RetryDelivery",
    "ReturnDelivery",
    "derive_change_stage",
    "invalidate_checkpoint_publication",
    "is_acceptance_waiting_observation",
    "is_change_terminal",
    "normalize_frontier",
    "parse_delivery_frontier",
    "parse_stored_delivery_frontier",
    "repair_missing_request_provenance",
]
