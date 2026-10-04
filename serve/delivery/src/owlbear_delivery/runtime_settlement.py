"""Worker-settlement replay participants and builder-handoff receipt chains."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RetryEpisodeSummary,
    RetryFailureClass,
    RetryLedger,
    journal_path,
    read_record,
)
from owlbear_delivery.runtime_models import (
    _MAX_BUILDER_HANDOFF_CHANGE_INTENTS,
    _MAX_COMPLETED_REPAIR_RECEIPTS,
    _SHA256_HEX_LENGTH,
    REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES,
    AdvanceDelivery,
    BlockDelivery,
    CompletedOutcomeRepairReceipt,
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryBuilderHandoffContext,
    DeliveryChangeAbandonment,
    DeliveryChangeDeferral,
    DeliveryFrontier,
    DeliveryRequest,
    DeliveryResultCandidate,
    DeliveryReturnContext,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DeliveryTaskResult,
    DeliveryTransition,
    DeliveryWorkerRole,
    EngineWorkerDisposition,
    OutcomeAuthorityBinding,
    RetryDelivery,
    ReturnDelivery,
    _DeliveryModel,
    _model_content,
    _reference,
)
from owlbear_delivery.runtime_receipts import (
    DeliveryBuilderInvocationSettlement,
    DeliveryEngineBuilderSettlement,
    DeliveryEnginePlanningSettlement,
    DeliveryPlanningRetrySettlement,
    _BuilderHandoffChangeIntentMutation,
    _DeliveryBuilderHandoffChangeIntentHead,
    _DeliveryBuilderHandoffChangeIntentReceipt,
    _DeliveryBuilderInvocationSettlementReceipt,
    _DeliveryBuilderPlanPromotionReceipt,
    _DeliveryBuilderRequestResolutionReceipt,
    _DeliveryPlanningPauseReplay,
    _DeliveryPlanningRetrySettlementReceipt,
)
from owlbear_delivery.runtime_support import (
    _builder_handoff_change_intent_directory,
    _builder_handoff_change_intent_head_path,
    _builder_request_resolution_receipt_path,
    _conflict,
    _read_builder_handoff_change_intent_receipts,
    parse_stored_delivery_frontier,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    TransactionParticipant,
)

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery.change_workspace import (
        ChangeWorkspaceManager,
        PreparedBuilderHandoff,
        PublicationLock,
    )


class _SettlementReplayMixin:
    """Worker-settlement replay participants and builder-handoff receipt chains."""

    def _transitioned_binding(
        self,
        binding: OutcomeAuthorityBinding,
        request: DeliveryTransition,
    ) -> OutcomeAuthorityBinding:
        if isinstance(request, AdvanceDelivery):
            return self._advance(binding, request)
        if isinstance(request, RetryDelivery):
            return self._retry(binding, request)
        if isinstance(request, ReturnDelivery):
            return self._return(binding, request)
        return self._block(binding, request)

    def _repair_owner_result_participants(
        self,
        binding: OutcomeAuthorityBinding,
        *,
        retry_observed_at: datetime | str,
    ) -> tuple[TransactionParticipant, ...]:
        """Publish exact completed-repair accounting only with its accepted task result."""
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_claim is None:
            return ()
        task_id = binding.active_claim.task_id
        candidate = binding.result_candidate
        if task_id is None or candidate is None or candidate.result.task_id != task_id:
            return ()
        ledger = self.retry_ledger()
        bindings = tuple(
            item
            for item in ledger.repair_bindings()
            if item.outcome_id == binding.outcome_id and item.repair_task_id == task_id
        )
        if not bindings:
            return ()
        if len(bindings) != 1:
            msg = "completed-outcome repair has multiple retry bindings"
            raise DeliveryRuntimeConflictError(msg)
        repair_binding = bindings[0]
        receipt = self._completed_outcome_repair_receipt(binding.outcome_id, task_id)
        if (
            receipt is None
            or receipt.episode_id != repair_binding.episode_id
            or receipt.attempt_id != repair_binding.repair_attempt_id
            or receipt.outcome_id != repair_binding.outcome_id
            or receipt.repair_task_id != repair_binding.repair_task_id
        ):
            msg = "completed-outcome repair receipt identity is unavailable"
            raise DeliveryRuntimeReferenceError(msg)
        return ledger.owner_result_participants(
            receipt.attempt_id,
            accepted=True,
            accepted_progress=False,
            repair_outcome_id=receipt.outcome_id,
            repair_task_id=receipt.repair_task_id,
            completed_commit=candidate.result.completed_commit,
            now=retry_observed_at,
        )

    def _completed_outcome_repair_receipt(
        self,
        outcome_id: str,
        repair_task_id: str,
    ) -> CompletedOutcomeRepairReceipt | None:
        """Find one validated repair receipt without deriving authority from a task name."""
        base = self._target_root / "changes" / self._contract.change_id / "recovery-receipts"
        try:
            entries = tuple(sorted(base.iterdir(), key=lambda item: item.name))
        except FileNotFoundError:
            return None
        except OSError as exc:
            msg = "completed-outcome repair receipt inventory is unavailable"
            raise DeliveryRuntimeReferenceError(msg) from exc
        if len(entries) > _MAX_COMPLETED_REPAIR_RECEIPTS:
            msg = "completed-outcome repair receipt inventory exceeds its bound"
            raise DeliveryRuntimeReferenceError(msg)
        matches: list[CompletedOutcomeRepairReceipt] = []
        for entry in entries:
            receipt = self._completed_outcome_repair_receipt_entry(entry, outcome_id, repair_task_id)
            if receipt is not None:
                matches.append(receipt)
        if len(matches) > 1:
            msg = "completed-outcome repair has multiple matching receipts"
            raise DeliveryRuntimeConflictError(msg)
        return matches[0] if matches else None

    def _completed_outcome_repair_receipt_entry(
        self,
        entry: Path,
        outcome_id: str,
        repair_task_id: str,
    ) -> CompletedOutcomeRepairReceipt | None:
        try:
            entry_mode = entry.lstat().st_mode
        except OSError:
            entry_mode = None
        if entry_mode is None or not stat.S_ISDIR(entry_mode):
            return None
        if len(entry.name) != _SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in entry.name
        ):
            return None
        try:
            content = read_record(
                self._target_root,
                journal_path(self._contract.change_id, entry.name, "receipt"),
            )
        except FileNotFoundError:
            return None
        except (OSError, DeliveryWorkerExclusionRequiredError) as exc:
            msg = "completed-outcome repair receipt is unavailable"
            raise DeliveryRuntimeReferenceError(msg) from exc
        try:
            receipt = CompletedOutcomeRepairReceipt.model_validate_json(content)
        except (TypeError, ValueError) as exc:
            try:
                payload = json.loads(content)
            except TypeError, ValueError, json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and "repair_task_id" in payload:
                msg = "completed-outcome repair receipt is malformed"
                raise DeliveryRuntimeReferenceError(msg) from exc
            return None
        if (
            receipt.change_id == self._contract.change_id
            and receipt.outcome_id == outcome_id
            and receipt.repair_task_id == repair_task_id
        ):
            return receipt
        return None

    def require_result_replay(
        self, outcome_id: str, claim_id: str, result: DeliveryTaskResult
    ) -> DeliveryResultCandidate:
        """Require and return the immutable original claim receipt before replaying a promoted result."""
        binding = self.show_binding(outcome_id)
        if result not in binding.results:
            _conflict("result replay requires current promoted authority")
        digest = hashlib.sha256(_model_content(result)).hexdigest()
        path = self._target_root / self._result_receipt_path(binding.outcome_id, digest)
        try:
            receipt = DeliveryResultCandidate.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as exc:
            _reference("original result claim receipt is unavailable", exc)
        if receipt != DeliveryResultCandidate(
            candidate_id=f"result-{digest}", claim_id=claim_id, digest=digest, result=result
        ):
            _conflict("submitted result replay does not match original claim custody")
        return receipt

    def _result_receipt_path(self, outcome_id: str, digest: str) -> Path:
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "result-receipts"
            / outcome_id
            / f"{digest}.json"
        )

    def _planning_pause_replay_result(
        self,
        request: DeliveryTransition,
        request_digest: str,
    ) -> OutcomeAuthorityBinding | None:
        if not isinstance(request, BlockDelivery) or request.request is None:
            return None
        relative_path = self._planning_pause_replay_path(request.outcome_id, request_digest)
        path = self._target_root / relative_path
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            _reference("Planning pause replay receipt is unavailable", exc)
        try:
            receipt = _DeliveryPlanningPauseReplay.model_validate_json(content, strict=True)
        except (TypeError, ValueError) as exc:
            _reference("Planning pause replay receipt is invalid", exc)
        if (
            receipt.change_id != self._contract.change_id
            or receipt.outcome_id != request.outcome_id
            or receipt.claim_id != request.claim_id
            or receipt.request_digest != request_digest
            or receipt.request != request
        ):
            _reference("Planning pause replay receipt does not match its original request")
        return receipt.result

    def _planning_retry_settlement_replay_result(
        self,
        envelope: DeliveryPlanningRetrySettlement,
    ) -> OutcomeAuthorityBinding | None:
        path = self._target_root / self._planning_retry_settlement_path(envelope)
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            _reference("Planning retry settlement receipt is unavailable", exc)
        try:
            receipt = _DeliveryPlanningRetrySettlementReceipt.model_validate_json(content, strict=True)
        except (TypeError, ValueError) as exc:
            _reference("Planning retry settlement receipt is invalid", exc)
        if receipt.envelope != envelope:
            _conflict("Planning retry settlement conflicts with the immutable attempt receipt")
        return receipt.result

    def _planning_retry_settlement_participant(
        self,
        receipt: _DeliveryPlanningRetrySettlementReceipt,
    ) -> TransactionParticipant:
        return TransactionParticipant(
            self._target_root,
            self._planning_retry_settlement_path(receipt.envelope),
            _model_content(receipt),
        )

    def _planning_retry_settlement_path(self, envelope: DeliveryPlanningRetrySettlement) -> Path:
        attempt_digest = hashlib.sha256(envelope.attempt_id.encode("utf-8")).hexdigest()
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "planning-retry-receipts"
            / envelope.outcome_id
            / f"{attempt_digest}.json"
        )

    def engine_worker_settlement_replay(
        self,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        disposition: EngineWorkerDisposition,
    ) -> tuple[OutcomeAuthorityBinding, DeliveryEnginePlanningSettlement | DeliveryEngineBuilderSettlement] | None:
        """Return the immutable result and envelope of one exact engine-settled worker attempt, if any."""
        if re.fullmatch(r"OUT-[0-9]{3}", outcome_id) is None:
            return None
        attempt_digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        receipts: tuple[tuple[Path, type[_DeliveryModel]], ...] = (
            (
                self._frontier_path.parent / "planning-retry-receipts" / outcome_id / f"{attempt_digest}.json",
                _DeliveryPlanningRetrySettlementReceipt,
            ),
            (
                self._target_root / self._builder_invocation_settlement_path(attempt_id),
                _DeliveryBuilderInvocationSettlementReceipt,
            ),
        )
        for path, receipt_type in receipts:
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                continue
            except OSError as exc:
                _reference("worker settlement receipt is unavailable", exc)
            try:
                receipt = receipt_type.model_validate_json(content, strict=True)
            except (TypeError, ValueError) as exc:
                _reference("worker settlement receipt is invalid", exc)
            envelope = receipt.envelope
            if (
                isinstance(envelope, (DeliveryEnginePlanningSettlement, DeliveryEngineBuilderSettlement))
                and envelope.outcome_id == outcome_id
                and envelope.claim_id == claim_id
                and envelope.disposition == disposition
            ):
                return receipt.result, envelope
            _conflict("worker attempt is already settled with different authority")
        return None

    def _prepare_builder_invocation_handoff(
        self,
        binding: OutcomeAuthorityBinding,
        envelope: DeliveryBuilderInvocationSettlement,
        manager: ChangeWorkspaceManager,
        lock: PublicationLock,
    ) -> tuple[DeliveryActiveClaim, PreparedBuilderHandoff]:
        claim = binding.active_claim
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or claim is None
            or claim.worker_role != DeliveryWorkerRole.BUILDER
            or claim.claim_id != envelope.claim_id
            or claim.attempt_id != envelope.attempt_id
            or claim.task_id != envelope.task_id
            or not any(task.task_id == envelope.task_id for task in binding.tasks)
        ):
            _conflict("Builder invocation settlement does not match the active task claim")
        coordination = manager.show(envelope.change_id)
        writer = coordination.writer
        if (
            writer is None
            or writer.kind != "build"
            or writer.claim_id != claim.claim_id
            or writer.attempt_id != claim.attempt_id
            or coordination.last_reviewed_commit != envelope.expected_last_reviewed_commit
        ):
            _conflict("Builder invocation settlement does not match exact Change workspace custody")
        settlement_id = hashlib.sha256(_model_content(envelope)).hexdigest()
        prepared = manager.prepare_builder_handoff(
            envelope.change_id,
            writer,
            settlement_id,
            envelope.task_id,
            lock,
        )
        metadata = prepared.metadata
        if (
            metadata.change_id != envelope.change_id
            or metadata.branch != coordination.branch
            or metadata.worktree_path != coordination.worktree_path
            or metadata.last_reviewed_commit != envelope.expected_last_reviewed_commit
            or metadata.registration.path != metadata.worktree_path
            or metadata.registration.branch != metadata.branch
            or metadata.registration.head != metadata.branch_head
        ):
            _conflict("Builder handoff metadata does not match its registered branch and reviewed boundary")
        request = envelope.request
        if isinstance(request, RetryDelivery) and request.abandoned_commit != metadata.branch_head:
            _conflict("Builder retry commit does not match the registered branch head")
        if isinstance(request, BlockDelivery) and request.resume_commit != metadata.branch_head:
            _conflict("Builder block commit does not match the registered branch head")
        if isinstance(request, ReturnDelivery) and request.preserved_commit != metadata.branch_head:
            _conflict("Builder return commit does not match the registered branch head")
        self._validate_builder_result_candidate(binding, claim, envelope.task_id)
        return claim, prepared

    @staticmethod
    def _validate_builder_result_candidate(
        binding: OutcomeAuthorityBinding,
        claim: DeliveryActiveClaim,
        task_id: str,
    ) -> None:
        candidate = binding.result_candidate
        if candidate is None:
            return
        if candidate.claim_id != claim.claim_id or candidate.result.task_id != task_id:
            _conflict("published Builder result candidate does not match its active task claim")
        accepted = next((result for result in binding.results if result.task_id == candidate.result.task_id), None)
        if accepted is not None and accepted != candidate.result:
            _conflict("published Builder result candidate conflicts with its accepted result")

    def _builder_invocation_retry_episode(
        self,
        envelope: DeliveryBuilderInvocationSettlement,
    ) -> tuple[RetryLedger, RetryEpisodeSummary]:
        ledger = self.retry_ledger()
        episode = ledger.episode_for_attempt(envelope.attempt_id)
        if episode is None:
            _conflict("Builder invocation settlement requires its exact reserved retry episode")
        key = episode.key
        reviewed_head_matches = key.exact_head == envelope.expected_last_reviewed_commit or any(
            alias.alias_kind == "commit" and alias.value == envelope.expected_last_reviewed_commit
            for alias in episode.aliases
        )
        if (
            episode.failure_class != RetryFailureClass.MECHANICAL
            or key.change_id != envelope.change_id
            or key.action_kind != "builder-claim"
            or not reviewed_head_matches
            or key.contract_digest != self._authority_digest
            or key.outcome_id != envelope.outcome_id
            or key.task_lineage != envelope.task_id
            or key.procedure_class != DeliveryWorkerRole.BUILDER.value
            or envelope.attempt_id not in episode.attempt_ids
        ):
            _conflict("Builder invocation settlement retry episode does not match its exact task authority")
        owner_result_path = (
            self._target_root
            / "changes"
            / envelope.change_id
            / "retry-ledger"
            / "owner-results"
            / f"{envelope.attempt_id}.json"
        )
        if owner_result_path.exists():
            _conflict("Builder invocation settlement already has an owner result without its exact receipt")
        return ledger, episode

    def _builder_invocation_settled_binding(
        self,
        binding: OutcomeAuthorityBinding,
        envelope: DeliveryBuilderInvocationSettlement,
        context: DeliveryBuilderHandoffContext,
        episode: RetryEpisodeSummary,
        ledger: RetryLedger,
    ) -> tuple[OutcomeAuthorityBinding, bool, str]:
        request = envelope.request
        paused = isinstance(request, BlockDelivery)
        requestless_code = REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES.get(envelope.disposition)
        failure_code = (
            requestless_code
            if requestless_code is not None
            else "worker-blocked"
            if paused
            else "worker-returned"
            if isinstance(request, ReturnDelivery)
            else request.failure_code
        )
        exhausted = not paused and episode.total_attempts >= ledger.mechanical_repairs + 1
        if requestless_code is not None or isinstance(request, RetryDelivery):
            result = self._builder_retry_settled_binding(binding, context, envelope, exhausted=exhausted)
        elif isinstance(request, BlockDelivery):
            result = self._builder_pause_settled_binding(binding, context, request)
        elif isinstance(request, ReturnDelivery):
            result = self._builder_return_settled_binding(binding, context, request, exhausted=exhausted)
        else:
            _conflict("Builder invocation settlement has no supported completed disposition")
        return result, paused, failure_code

    @staticmethod
    def _builder_retry_settled_binding(
        binding: OutcomeAuthorityBinding,
        context: DeliveryBuilderHandoffContext,
        envelope: DeliveryBuilderInvocationSettlement,
        *,
        exhausted: bool,
    ) -> OutcomeAuthorityBinding:
        updates = {
            "active_claim": None,
            "output": None,
            "candidate": None,
            "result_candidate": None,
            "return_context": None,
            "builder_handoff_context": context,
            "recovery_attention": None,
            "retry_diagnostic": None,
            "block": None,
        }
        if exhausted:
            updates["block"] = DeliveryBlock(
                block_id=f"builder-attempt-limit-{context.settlement_id}",
                reason="The Builder retry episode reached its three-attempt limit.",
                unblock_condition="Use a supported operator disposition without resetting this retry episode.",
                expected_evidence=("An exact operator disposition for the retained Builder task.",),
                locators=(envelope.task_id,),
            )
        return binding.model_copy(update=updates)

    @staticmethod
    def _builder_pause_settled_binding(
        binding: OutcomeAuthorityBinding,
        context: DeliveryBuilderHandoffContext,
        request: BlockDelivery,
    ) -> OutcomeAuthorityBinding:
        delivery_request = request.request
        if delivery_request is None or any(
            existing.request_id == delivery_request.request_id for existing in binding.requests
        ):
            _conflict("Builder pause request is absent or already active")
        block = DeliveryBlock(
            block_id=request.block_id,
            reason=request.reason,
            unblock_condition=request.unblock_condition,
            expected_evidence=request.expected_evidence,
            locators=request.locators,
            request_id=delivery_request.request_id,
            resume_commit=request.resume_commit,
        )
        return binding.model_copy(
            update={
                "active_claim": None,
                "builder_handoff_context": context,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
                "return_context": None,
                "block": block,
                "requests": (*binding.requests, delivery_request),
            }
        )

    @staticmethod
    def _builder_return_settled_binding(
        binding: OutcomeAuthorityBinding,
        context: DeliveryBuilderHandoffContext,
        request: ReturnDelivery,
        *,
        exhausted: bool,
    ) -> OutcomeAuthorityBinding:
        if request.target not in {DeliveryStage.PLANNING, DeliveryStage.DESIGN}:
            _conflict("Builder return target has no supported workspace owner route")
        block = (
            DeliveryBlock(
                block_id=f"builder-{request.target.value}-route-{context.settlement_id}",
                reason="The Builder retry episode reached its three-attempt limit.",
                unblock_condition="The retry episode is eligible to continue.",
                expected_evidence=("A retry episode below its attempt limit.",),
                locators=request.locators,
            )
            if exhausted
            else None
        )
        return binding.model_copy(
            update={
                "stage": request.target,
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "builder_handoff_context": context,
                "recovery_attention": None,
                "retry_diagnostic": None,
                "return_context": DeliveryReturnContext(
                    target=request.target,
                    reason=request.reason,
                    locators=request.locators,
                    preserved_commit=request.preserved_commit,
                    completed_boundary=context.last_reviewed_commit,
                ),
                "block": block,
            }
        )

    def _builder_invocation_settlement_replay_result(
        self,
        envelope: DeliveryBuilderInvocationSettlement,
    ) -> OutcomeAuthorityBinding | None:
        path = self._target_root / self._builder_invocation_settlement_path(envelope.attempt_id)
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            _reference("Builder invocation settlement receipt is unavailable", exc)
        try:
            receipt = _DeliveryBuilderInvocationSettlementReceipt.model_validate_json(content, strict=True)
        except (TypeError, ValueError) as exc:
            _reference("Builder invocation settlement receipt is invalid", exc)
        if receipt.envelope != envelope:
            _conflict("Builder invocation settlement conflicts with the immutable attempt receipt")
        return receipt.result

    def _builder_invocation_settlement_participant(
        self,
        receipt: _DeliveryBuilderInvocationSettlementReceipt,
    ) -> TransactionParticipant:
        return TransactionParticipant(
            self._target_root,
            self._builder_invocation_settlement_path(receipt.envelope.attempt_id),
            _model_content(receipt),
        )

    def _builder_plan_promotion_receipt_participant(
        self,
        receipt: _DeliveryBuilderPlanPromotionReceipt,
    ) -> TransactionParticipant:
        return TransactionParticipant(
            self._target_root,
            self._builder_plan_promotion_receipt_path(receipt.settlement_id),
            _model_content(receipt),
        )

    def _builder_plan_promotion_receipt_path(self, settlement_id: str) -> Path:
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "builder-plan-promotion-receipts"
            / f"{settlement_id}.json"
        )

    def _builder_invocation_settlement_path(self, attempt_id: str) -> Path:
        attempt_digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "builder-invocation-receipts"
            / f"{attempt_digest}.json"
        )

    def _builder_request_resolution_receipt_participant(
        self,
        binding: OutcomeAuthorityBinding,
        request: DeliveryRequest,
        resolved_request: DeliveryRequest,
        updated_block: DeliveryBlock,
    ) -> TransactionParticipant | None:
        context = binding.builder_handoff_context
        block = binding.block
        if context is None or context.route != "same-task":
            return None
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or context.original_task_id not in binding.task_ids
            or block is None
            or block.request_id != request.request_id
        ):
            return None

        settlement_receipt = self._read_builder_invocation_settlement_receipt(context)
        original_block = settlement_receipt.envelope.request
        if not isinstance(original_block, BlockDelivery) or original_block.request is None:
            _conflict("Builder request resolution does not match an exact same-task pause")
        expected_block = DeliveryBlock(
            block_id=original_block.block_id,
            reason=original_block.reason,
            unblock_condition=original_block.unblock_condition,
            expected_evidence=original_block.expected_evidence,
            locators=original_block.locators,
            request_id=original_block.request.request_id,
            resume_commit=original_block.resume_commit,
        )
        if not (
            settlement_receipt.handoff_context == context
            and settlement_receipt.result == binding
            and settlement_receipt.envelope.change_id == self._contract.change_id
            and settlement_receipt.envelope.outcome_id == binding.outcome_id
            and settlement_receipt.envelope.task_id == context.original_task_id
            and original_block.request == request
            and expected_block == block
            and request.outcome_id == binding.outcome_id
        ):
            _conflict("Builder request resolution does not match its exact same-task pause")

        receipt = _DeliveryBuilderRequestResolutionReceipt(
            change_id=self._contract.change_id,
            outcome_id=binding.outcome_id,
            request_id=request.request_id,
            settlement_id=context.settlement_id,
            builder_handoff_context=context,
            resolved_request=resolved_request,
            updated_block=updated_block,
        )
        receipt_path = _builder_request_resolution_receipt_path(
            self._target_root,
            self._contract.change_id,
            context,
        )
        receipt_directory = receipt_path.parent
        if any(
            path.is_symlink()
            for path in (self._target_root / "changes", self._frontier_path.parent, receipt_directory, receipt_path)
        ):
            _reference("Builder request resolution receipt path is unsafe")
        return TransactionParticipant(
            self._target_root,
            receipt_path.relative_to(self._target_root),
            _model_content(receipt),
        )

    def _read_builder_invocation_settlement_receipt(
        self,
        context: DeliveryBuilderHandoffContext,
    ) -> _DeliveryBuilderInvocationSettlementReceipt:
        settlement_path = self._target_root / self._builder_invocation_settlement_path(context.attempt_id)
        settlement_directory = settlement_path.parent
        if any(
            path.is_symlink()
            for path in (
                self._target_root / "changes",
                self._frontier_path.parent,
                settlement_directory,
                settlement_path,
            )
        ):
            _reference("Builder invocation settlement receipt path is unsafe")
        try:
            settlement_content = settlement_path.read_bytes()
        except OSError as exc:
            _reference("Builder invocation settlement receipt is unavailable", exc)
        try:
            receipt = _DeliveryBuilderInvocationSettlementReceipt.model_validate_json(
                settlement_content,
                strict=True,
            )
        except (TypeError, ValueError) as exc:
            _reference("Builder invocation settlement receipt is invalid", exc)
        return receipt

    def _planner_handoff_pause_return_context(
        self,
        binding: OutcomeAuthorityBinding,
    ) -> DeliveryReturnContext | None:
        """Return the retained Planning return context for one exact Planner pause on a Builder return."""
        context = binding.builder_handoff_context
        block = binding.block
        if (
            context is None
            or context.route != "same-outcome-planner"
            or binding.stage != DeliveryStage.PLANNING
            or binding.active_claim is not None
            or block is None
        ):
            return None
        settlement = self._read_builder_invocation_settlement_receipt(context)
        returned = settlement.envelope.request
        if not (
            isinstance(returned, ReturnDelivery)
            and returned.target == DeliveryStage.PLANNING
            and settlement.handoff_context == context
            and settlement.envelope.change_id == self._contract.change_id
            and settlement.result.block is None
            and settlement.result.return_context is not None
            and settlement.result.tasks == binding.tasks
            and settlement.result.results == binding.results
        ):
            return None
        if block.request_id is not None and not self._planning_pause_receipt_matches(binding):
            return None
        return settlement.result.return_context

    def _planning_pause_receipt_matches(self, binding: OutcomeAuthorityBinding) -> bool:
        directory = self._target_root / self._planning_pause_replay_path(binding.outcome_id, "0" * 64).parent
        if any(
            path.is_symlink()
            for path in (self._target_root / "changes", self._frontier_path.parent, directory.parent, directory)
        ):
            _reference("Planning pause replay receipt path is unsafe")
        if not directory.is_dir():
            return False
        for path in sorted(directory.glob("*.json")):
            if path.is_symlink():
                _reference("Planning pause replay receipt path is unsafe")
            try:
                receipt = _DeliveryPlanningPauseReplay.model_validate_json(path.read_bytes(), strict=True)
            except (OSError, TypeError, ValueError) as exc:
                _reference("Planning pause replay receipt is invalid", exc)
            if (
                receipt.change_id == self._contract.change_id
                and path.name == f"{receipt.request_digest}.json"
                and receipt.result == binding
            ):
                return True
        return False

    def _require_recorded_builder_handoff_change_intent(self, frontier: DeliveryFrontier) -> None:
        for binding in frontier.bindings:
            context = binding.builder_handoff_context
            if context is None:
                continue
            receipts = _read_builder_handoff_change_intent_receipts(
                self._target_root,
                self._contract.change_id,
                context,
            )
            if not receipts or (
                receipts[-1].after_frontier.change_deferral != frontier.change_deferral
                or receipts[-1].after_frontier.change_abandonment != frontier.change_abandonment
            ):
                _conflict("retained Builder handoff lifecycle intent has no matching receipt")

    def _builder_handoff_change_intent_participants(  # noqa: PLR0913
        self,
        before: DeliveryFrontier,
        after: DeliveryFrontier,
        action: Literal["defer", "resume", "abandon"],
        *,
        deferral: DeliveryChangeDeferral | None = None,
        abandonment: DeliveryChangeAbandonment | None = None,
        previous: bytes | None = None,
    ) -> tuple[TransactionParticipant | ReplacementTransactionParticipant, ...]:
        handoffs = tuple(binding for binding in before.bindings if binding.builder_handoff_context is not None)
        if not handoffs:
            return ()
        if (
            any(binding.active_claim is not None for binding in before.bindings)
            or before.integration_repair_claim is not None
        ):
            _conflict("Builder handoff lifecycle intent cannot overlap an active mutation claim")

        # The receipt binds the stored model at its stored version (an 18 stays 18) and its committed digest.
        stored_before = parse_stored_delivery_frontier(previous) if previous is not None else before
        mutation = _BuilderHandoffChangeIntentMutation(stored_before, after, action, deferral, abandonment)
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = []
        for binding in handoffs:
            context = binding.builder_handoff_context
            if context is None:
                continue
            receipts = self._builder_handoff_change_intent_chain(before, context, action)
            receipt, head = self._new_builder_handoff_change_intent_receipt(
                binding,
                mutation,
                receipts,
            )
            participants.extend(self._builder_handoff_change_intent_storage(receipt, head, context, receipts))
        return tuple(participants)

    def _builder_handoff_change_intent_chain(
        self,
        before: DeliveryFrontier,
        context: DeliveryBuilderHandoffContext,
        action: Literal["defer", "resume", "abandon"],
    ) -> tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...]:
        receipts = _read_builder_handoff_change_intent_receipts(self._target_root, self._contract.change_id, context)
        if receipts:
            latest = receipts[-1].after_frontier
            if (
                latest.change_deferral != before.change_deferral
                or latest.change_abandonment != before.change_abandonment
            ):
                _conflict("Builder handoff lifecycle flags do not match the recorded receipt chain")
        elif before.change_deferral is not None or before.change_abandonment is not None:
            _conflict("Builder handoff lifecycle flags are missing their receipt chain")
        if len(receipts) > _MAX_BUILDER_HANDOFF_CHANGE_INTENTS or (
            len(receipts) == _MAX_BUILDER_HANDOFF_CHANGE_INTENTS and action != "abandon"
        ):
            _conflict("Builder handoff change-intent receipt chain is exhausted")
        return receipts

    def _new_builder_handoff_change_intent_receipt(
        self,
        binding: OutcomeAuthorityBinding,
        mutation: _BuilderHandoffChangeIntentMutation,
        receipts: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    ) -> tuple[_DeliveryBuilderHandoffChangeIntentReceipt, _DeliveryBuilderHandoffChangeIntentHead]:
        context = binding.builder_handoff_context
        if context is None:
            _conflict("Builder handoff change-intent receipt requires retained context")
        try:
            receipt = _DeliveryBuilderHandoffChangeIntentReceipt.create(
                action=mutation.action,
                change_id=self._contract.change_id,
                outcome_id=binding.outcome_id,
                context=context,
                sequence=len(receipts) + 1,
                previous_receipt_id=receipts[-1].receipt_id if receipts else None,
                before_frontier=mutation.before,
                after_frontier=mutation.after,
                deferral=mutation.deferral,
                abandonment=mutation.abandonment,
            )
            head = _DeliveryBuilderHandoffChangeIntentHead(
                change_id=self._contract.change_id,
                outcome_id=binding.outcome_id,
                settlement_id=context.settlement_id,
                builder_handoff_context=context,
                latest_receipt_id=receipt.receipt_id,
                sequence=receipt.sequence,
            )
        except TypeError, ValueError:
            _conflict("Builder handoff lifecycle intent cannot prove an exact supported frontier delta")
        return receipt, head

    def _builder_handoff_change_intent_storage(
        self,
        receipt: _DeliveryBuilderHandoffChangeIntentReceipt,
        head: _DeliveryBuilderHandoffChangeIntentHead,
        context: DeliveryBuilderHandoffContext,
        receipts: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    ) -> tuple[TransactionParticipant | ReplacementTransactionParticipant, ...]:
        directory = _builder_handoff_change_intent_directory(self._target_root, self._contract.change_id, context)
        receipt_path = directory / f"{receipt.receipt_id}.json"
        head_path = _builder_handoff_change_intent_head_path(self._target_root, self._contract.change_id, context)
        if any(
            path.is_symlink()
            for path in (
                self._target_root / "changes",
                self._frontier_path.parent,
                directory,
                receipt_path,
                head_path,
            )
        ):
            _reference("Builder handoff change-intent receipt path is unsafe")
        if receipt_path.exists():
            _reference("Builder handoff change-intent receipt path already exists")
        return (
            TransactionParticipant(
                self._target_root,
                receipt_path.relative_to(self._target_root),
                _model_content(receipt),
            ),
            self._builder_handoff_change_intent_head_participant(head_path, head, context, receipts),
        )

    def _builder_handoff_change_intent_head_participant(
        self,
        head_path: Path,
        head: _DeliveryBuilderHandoffChangeIntentHead,
        context: DeliveryBuilderHandoffContext,
        receipts: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        head_content = _model_content(head)
        if not head_path.exists():
            if receipts:
                _reference("Builder handoff change-intent head is unavailable")
            return TransactionParticipant(
                self._target_root,
                head_path.relative_to(self._target_root),
                head_content,
            )
        try:
            previous_head_content = head_path.read_bytes()
            previous_head = _DeliveryBuilderHandoffChangeIntentHead.model_validate_json(
                previous_head_content,
                strict=True,
            )
        except (OSError, TypeError, ValueError) as exc:
            _reference("Builder handoff change-intent head is invalid", exc)
        if not receipts or (
            previous_head_content != _model_content(previous_head)
            or previous_head.change_id != self._contract.change_id
            or previous_head.outcome_id != head.outcome_id
            or previous_head.builder_handoff_context != context
            or previous_head.latest_receipt_id != receipts[-1].receipt_id
            or previous_head.sequence != len(receipts)
        ):
            _reference("Builder handoff change-intent head does not match its receipt chain")
        return ReplacementTransactionParticipant(
            self._target_root,
            head_path.relative_to(self._target_root),
            previous_head_content,
            head_content,
        )

    def _planning_pause_replay_participant(
        self,
        request: BlockDelivery,
        result: OutcomeAuthorityBinding,
        request_digest: str,
    ) -> TransactionParticipant:
        receipt = _DeliveryPlanningPauseReplay(
            change_id=self._contract.change_id,
            outcome_id=request.outcome_id,
            claim_id=request.claim_id,
            request_digest=request_digest,
            request=request,
            result=result,
        )
        return TransactionParticipant(
            self._target_root,
            self._planning_pause_replay_path(request.outcome_id, request_digest),
            _model_content(receipt),
        )

    def _planning_pause_replay_participants(
        self,
        request: DeliveryTransition,
        binding: OutcomeAuthorityBinding,
        result: OutcomeAuthorityBinding,
        request_digest: str,
    ) -> tuple[TransactionParticipant, ...]:
        if not isinstance(request, BlockDelivery) or binding.stage != DeliveryStage.PLANNING or request.request is None:
            return ()
        return (self._planning_pause_replay_participant(request, result, request_digest),)

    def _planning_pause_replay_path(self, outcome_id: str, request_digest: str) -> Path:
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "planning-pause-receipts"
            / outcome_id
            / f"{request_digest}.json"
        )
