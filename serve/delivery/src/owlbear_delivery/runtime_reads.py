"""Read-side runtime queries and transition, activation and repair validation."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from owlbear_delivery.acceptance import (
    CompletionReceipt,
    CompletionReceiptConflictError,
    CompletionReceiptStore,
)
from owlbear_delivery.change_workspace import (
    ChangeFinalizationAttention,
    ChangeWriter,
    PublicationLock,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    journal_path,
    read_record,
)
from owlbear_delivery.runtime_models import (
    _RETURN_TARGETS,
    ActivateDeliveryClaim,
    AdvanceDelivery,
    BlockDelivery,
    CompletedOutcomeRepairReceipt,
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryBuilderHandoffContext,
    DeliveryChangeDisposition,
    DeliveryChangeStage,
    DeliveryCheckpointPublicationState,
    DeliveryFrontier,
    DeliveryPendingStatePublication,
    DeliveryRecoveryAttention,
    DeliveryReturnContext,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    PrepareCompletedOutcomeRepair,
    RetryDelivery,
    ReturnDelivery,
    _CompletedOutcomeRepairLineage,
    _model_content,
    _reference,
    derive_change_stage,
    pause_mutation_class,
    retained_requests,
)
from owlbear_delivery.runtime_receipts import (
    AdministrativeDeliveryMovePreview,
)
from owlbear_delivery.runtime_support import (
    _administrative_move_closure,
    _completed_outcome_repair_id,
    _conflict,
    _declared_mutation,
    _find_binding,
    _require_target_sync_attention,
    _reset_binding,
    parse_stored_delivery_frontier,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    TransactionParticipant,
)

if TYPE_CHECKING:
    from owlbear_delivery.change_workspace import (
        ChangeWorkspaceManager,
    )


def _portable_projection(content: bytes) -> DeliveryFrontier:
    frontier = parse_stored_delivery_frontier(content)
    portable_bindings = tuple(
        binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
            }
        )
        for binding in frontier.bindings
    )
    return frontier.model_copy(update={"bindings": portable_bindings})


class _RuntimeReadsMixin:
    """Read-side runtime queries and transition, activation and repair validation."""

    def publication_base_digest(self, content: bytes) -> str:
        """Digest the portable projection that remote state can legitimately contain, at its stored version."""
        return hashlib.sha256(_model_content(_portable_projection(content))).hexdigest()

    def published_projection_digest(self, content: bytes) -> str:
        """Digest the stored projection after the drain of a checkpoint already published remotely."""
        projection = _portable_projection(content)
        pending = projection.pending_checkpoint
        if pending is not None and pending.head == projection.published_head:
            projection = projection.model_copy(update={"pending_checkpoint": None})
        return hashlib.sha256(_model_content(projection)).hexdigest()

    def finalization_readiness(self) -> tuple[bool, tuple[str, ...]]:
        """Return the same lifecycle readiness conditions enforced by finalization mutation."""
        frontier, _content = self._read()
        diagnostics: list[str] = []
        if frontier.finalization is not None:
            diagnostics.append("Delivery Change is already finalized")
        if frontier.change_completion is not None:
            diagnostics.append("Delivery Change is already completed")
        if any(binding.stage != DeliveryStage.COMPLETED for binding in frontier.bindings):
            diagnostics.append("every Outcome must be completed")
        if any(binding.active_claim is not None for binding in frontier.bindings):
            diagnostics.append("finalization cannot overlap an active Outcome claim")
        if frontier.integration_repair_claim is not None:
            diagnostics.append("finalization cannot overlap an Integration repair claim")
        if any(
            tuple(result.task_id for result in binding.results) != binding.task_ids for binding in frontier.bindings
        ):
            diagnostics.append("every Task result must be present in authority order")
        return not diagnostics, tuple(diagnostics)

    def checkpoint_publication_state(self) -> DeliveryCheckpointPublicationState:
        """Return the Change-level checkpoint queue without provider identity."""
        frontier, _content = self._read()
        return DeliveryCheckpointPublicationState(
            change_id=self._contract.change_id,
            published_head=frontier.published_head,
            pending_checkpoint=frontier.pending_checkpoint,
        )

    def validate_target_sync_conflict(
        self,
        expected_disposition_id: str,
        operation_id: str,
    ) -> DeliveryChangeDisposition:
        """Require one exact target-sync operation attention record."""
        frontier, _content = self._read()
        return _require_target_sync_attention(frontier, expected_disposition_id, operation_id)

    def completion_receipt(self) -> CompletionReceipt | None:
        """Return the exact terminal receipt while rejecting partial completion state."""
        frontier, _content = self._read()
        if frontier.change_completion is None:
            # A receipt here belongs to an earlier admission of the same Change ID.
            return None
        store = CompletionReceiptStore(self._target_root)
        try:
            record = store.read_bundle(self._contract.change_id)
        except CompletionReceiptConflictError:
            _conflict("terminal frontier state does not match its completion record")
        if record is None:
            _conflict("terminal frontier state does not match its completion record")
        stored = record.receipt
        display = record.display
        if (
            stored.completion_id != frontier.change_completion.completion_id
            or stored.completed_at != frontier.change_completion.completed_at
            or display.completion_id != stored.completion_id
            or display.title != self._contract.title
            or display.outcome_titles != tuple(outcome.title for outcome in self._contract.outcomes)
        ):
            _conflict("terminal frontier state does not match its completion record")
        return stored

    def _completed_outcome_repair_history(
        self,
        binding: OutcomeAuthorityBinding,
        existing: DeliveryTaskDefinition | None,
        repair_id: str,
        repair_task_id: str,
    ) -> tuple[CompletedOutcomeRepairReceipt | None, _CompletedOutcomeRepairLineage]:
        if existing is not None:
            try:
                persisted = CompletedOutcomeRepairReceipt.model_validate_json(
                    read_record(self._target_root, journal_path(self._contract.change_id, repair_id, "receipt"))
                )
            except (OSError, TypeError, ValueError) as exc:
                _reference("completed-outcome repair receipt is missing or invalid", exc)
            lineage = _CompletedOutcomeRepairLineage(
                persisted.previous_task_ids,
                persisted.previous_result_ids,
            )
            if (
                tuple(task.task_id for task in binding.tasks if task.task_id != repair_task_id)
                != lineage.previous_task_ids
                or tuple(result.result_id for result in binding.results if result.task_id in lineage.previous_task_ids)
                != lineage.previous_result_ids
            ):
                _conflict("completed-outcome repair receipt no longer matches its retained lineage")
            return persisted, lineage
        lineage = _CompletedOutcomeRepairLineage(
            binding.task_ids,
            tuple(result.result_id for result in binding.results),
        )
        return None, lineage

    @staticmethod
    def _completed_outcome_repair_task(
        source: DeliveryTaskDefinition,
        request: PrepareCompletedOutcomeRepair,
        repair_task_id: str,
        previous_task_ids: tuple[str, ...],
    ) -> DeliveryTaskDefinition:
        return DeliveryTaskDefinition(
            task_id=repair_task_id,
            outcome_id=source.outcome_id,
            plan_scope_id=source.plan_scope_id,
            title=f"Repair reproduced {request.defect_code}",
            result=(
                f"Correct the reproduced {request.finding_boundary} defect {request.defect_code}; "
                f"resume original action {request.original_action_id} only after the repair proof passes."
            ),
            commitment_ids=source.commitment_ids,
            dependency_ids=previous_task_ids,
            required_outputs=source.required_outputs,
            maintained_surfaces=source.maintained_surfaces,
            constraints=(
                *source.constraints,
                f"Use preserved workspace evidence {request.preservation_id}.",
            ),
            exclusions=source.exclusions,
            acceptance_observations=source.acceptance_observations,
            proof_boundaries=(
                *source.proof_boundaries,
                f"Repair episode {request.episode_id} attempt {request.attempt_id} must be independently reproven.",
            ),
        )

    @staticmethod
    def _completed_outcome_repair_replay(
        existing: DeliveryTaskDefinition | None,
        persisted: CompletedOutcomeRepairReceipt | None,
        repair: DeliveryTaskDefinition,
        receipt: CompletedOutcomeRepairReceipt,
    ) -> bool:
        if existing is None:
            return False
        if existing != repair:
            _conflict("completed-outcome repair publication conflicts with its episode identity")
        if persisted is None:
            _reference("completed-outcome repair receipt is missing or invalid")
        if persisted != receipt:
            _conflict("completed-outcome repair receipt conflicts with its episode identity")
        return True

    def has_completed_outcome_repair(self, request: PrepareCompletedOutcomeRepair) -> bool:
        """Return whether the exact engine-derived repair task is already present."""
        frontier, _previous = self._read()
        binding = _find_binding(frontier, request.outcome_id)
        source = next((task for task in binding.tasks if task.task_id == request.owning_task_id), None)
        if source is None:
            return False
        repair_id = _completed_outcome_repair_id(self._contract.change_id, request, source.digest)
        return any(task.task_id == f"repair-{repair_id}" for task in binding.tasks)

    def integration_repair_claim(self) -> DeliveryActiveClaim | None:
        """Return the current change-level Integration repair claim, if any."""
        return self._read()[0].integration_repair_claim

    def require_integration_repair_claim(self, attempt_id: str, claim_id: str) -> DeliveryActiveClaim:
        """Return the repair claim only when its exact execution identity remains active."""
        claim = self.integration_repair_claim()
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("execution identity does not match the active Integration repair claim")
        return claim

    def require_active_claim(
        self,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> OutcomeAuthorityBinding:
        """Return one binding only when its exact execution claim remains active."""
        binding = self.show_binding(outcome_id)
        claim = binding.active_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("execution identity does not match the active claim")
        return binding

    def claimable_outcome_ids(self) -> tuple[str, ...]:
        """Return stable dependency-ready, unblocked, unclaimed outcome identities."""
        frontier, _content = self._read()
        if derive_change_stage(frontier) != DeliveryChangeStage.BUILDING:
            return ()
        completed = {binding.outcome_id for binding in frontier.bindings if binding.stage == DeliveryStage.COMPLETED}
        dependencies = {outcome.outcome_id: set(outcome.dependency_ids) for outcome in self._contract.outcomes}
        planner_handoff_ids = {
            binding.outcome_id
            for binding in frontier.bindings
            if binding.builder_handoff_context is not None
            and binding.builder_handoff_context.route == "same-outcome-planner"
        }
        if len(planner_handoff_ids) > 1:
            return ()
        planner_handoff_id = next(iter(planner_handoff_ids), None)
        return tuple(
            binding.outcome_id
            for binding in frontier.bindings
            if binding.stage not in {DeliveryStage.DESIGN, DeliveryStage.COMPLETED}
            and binding.active_claim_id is None
            and (binding.block is None or binding.block.resolved)
            and (planner_handoff_id is None or binding.outcome_id == planner_handoff_id)
            and dependencies[binding.outcome_id] <= completed
        )

    def claimable_task_ids(self, outcome_id: str) -> tuple[str, ...]:
        """Return promoted tasks whose task dependencies have compact results."""
        if self.change_stage() != DeliveryChangeStage.BUILDING:
            return ()
        binding = self.show_binding(outcome_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_claim_id is not None:
            return ()
        completed = {result.task_id for result in binding.results}
        claimable = tuple(
            task.task_id
            for task in binding.tasks
            if task.task_id not in completed and set(task.dependency_ids) <= completed
        )
        handoff = binding.builder_handoff_context
        if handoff is None:
            return claimable
        return tuple(task_id for task_id in claimable if task_id == handoff.original_task_id)

    def _validate_builder_handoff_activation(
        self,
        request: ActivateDeliveryClaim,
        binding: OutcomeAuthorityBinding,
        participant: ReplacementTransactionParticipant | None,
        lock: PublicationLock | None,
    ) -> ReplacementTransactionParticipant | None:
        context = binding.builder_handoff_context
        if context is None:
            if participant is not None or lock is not None:
                _conflict("Builder handoff activation has no retained same-task authority")
            return None
        if context.route == "same-outcome-planner":
            return self._validate_planner_handoff_activation(request, binding, participant, lock, context)
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or context.route != "same-task"
            or context.outcome_id != request.outcome_id
            or context.original_task_id != request.task_id
        ):
            _conflict("Builder handoff activation requires its exact retained same-task authority")
        if participant is None or lock is None:
            _conflict("Builder handoff activation requires jointly prepared workspace consumption")
        if self._workspace_manager is None or type(lock) is not PublicationLock:
            _conflict("Builder handoff activation requires its active workspace publication lock")
        if type(participant) is not ReplacementTransactionParticipant:
            _conflict("Builder handoff activation requires a prepared workspace replacement")

        change_id = self._contract.change_id
        handoff = self._workspace_manager.show(change_id).builder_handoff
        if handoff is None or (
            handoff.change_id != change_id
            or handoff.settlement_id != context.settlement_id
            or handoff.original_task_id != context.original_task_id
            or handoff.original_writer.attempt_id != context.attempt_id
            or handoff.last_reviewed_commit != context.last_reviewed_commit
            or handoff.branch_head != context.branch_head
            or handoff.metadata_fingerprint != context.metadata_fingerprint
        ):
            _conflict("Builder handoff activation requires its exact retained workspace custody")

        claim = request.claim
        writer = ChangeWriter(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            actor_id=claim.owner_id,
            process_id=claim.process_id,
            claimed_at=claim.started_at,
            job_id=1,
            kind="build",
        )
        prepared = self._workspace_manager.prepare_builder_handoff_acquisition(
            change_id,
            writer,
            handoff,
            lock,
            task_id=context.original_task_id,
        )
        if (
            participant.root != prepared.root
            or participant.relative_path != prepared.relative_path
            or participant.expected_content != prepared.expected_content
            or participant.replacement_content != prepared.replacement_content
        ):
            _conflict("Builder handoff activation participant does not match the exact prepared workspace consumption")
        return prepared

    def _validate_planner_handoff_activation(
        self,
        request: ActivateDeliveryClaim,
        binding: OutcomeAuthorityBinding,
        participant: ReplacementTransactionParticipant | None,
        lock: PublicationLock | None,
        context: DeliveryBuilderHandoffContext,
    ) -> None:
        if (
            binding.stage != DeliveryStage.PLANNING
            or binding.return_context is None
            or binding.return_context.target != DeliveryStage.PLANNING
            or context.outcome_id != request.outcome_id
            or request.task_id is not None
            or request.claim.worker_role != DeliveryWorkerRole.PLANNER
            or participant is not None
        ):
            _conflict("Planner handoff activation requires its exact task-less Planning claim")
        manager = self._workspace_manager
        if manager is None or type(lock) is not PublicationLock:
            _conflict("Planner handoff activation requires its exact passive workspace custody fence")
        coordination = manager.show(self._contract.change_id)
        handoff = coordination.builder_handoff
        if handoff is None or (
            handoff.settlement_id != context.settlement_id
            or handoff.original_task_id != context.original_task_id
            or handoff.original_writer.attempt_id != context.attempt_id
            or handoff.last_reviewed_commit != context.last_reviewed_commit
            or handoff.branch_head != context.branch_head
            or handoff.metadata_fingerprint != context.metadata_fingerprint
            or coordination.writer != handoff.original_writer.model_copy(update={"kind": "handoff"})
        ):
            _conflict("Planner handoff activation requires its exact retained workspace custody")

    @staticmethod
    def _pending_transition_matches(
        pending_publication: DeliveryPendingStatePublication | None,
        previous: bytes,
        request_digest: str,
    ) -> bool:
        return (
            pending_publication is not None
            and pending_publication.frontier_digest == hashlib.sha256(previous).hexdigest()
            and pending_publication.transition_request_digest == request_digest
        )

    @staticmethod
    def _advanced_builder_handoff(
        binding: OutcomeAuthorityBinding,
        updated: OutcomeAuthorityBinding,
    ) -> OutcomeAuthorityBinding:
        context = binding.builder_handoff_context
        if context is None:
            return updated
        if binding.stage == DeliveryStage.PLANNING and context.route == "same-outcome-planner":
            if binding.candidate is None or updated.tasks != binding.candidate.tasks:
                _conflict("Planning handoff advance requires its exact published task-chain candidate")
            return updated.model_copy(
                update={"builder_handoff_context": context.model_copy(update={"route": "same-task"})}
            )
        if binding.stage == DeliveryStage.IMPLEMENTATION and context.route == "same-task":
            if binding.active_task_id != context.original_task_id:
                _conflict("Builder handoff can only be consumed by advancing its original task")
            return updated.model_copy(update={"builder_handoff_context": None})
        return _conflict("Builder handoff advance does not match its owning stage and route")

    def preview_administrative_move(
        self,
        outcome_id: str,
        target: DeliveryStage,
    ) -> AdministrativeDeliveryMovePreview:
        """Return the exact invalidation closure without mutating authority."""
        frontier, content = self._read()
        ordered = _administrative_move_closure(self._contract, frontier, outcome_id, target)
        self._require_no_handoff_in_administrative_closure(frontier, ordered)
        return AdministrativeDeliveryMovePreview(
            outcome_id=outcome_id,
            target=target,
            snapshot_version=hashlib.sha256(content).hexdigest(),
            invalidated_outcome_ids=ordered,
        )

    @staticmethod
    def _require_no_handoff_in_administrative_closure(frontier: DeliveryFrontier, outcome_ids: tuple[str, ...]) -> None:
        if any(
            binding.builder_handoff_context is not None and binding.outcome_id in outcome_ids
            for binding in frontier.bindings
        ):
            _conflict("administrative movement cannot orphan a preserved Builder handoff")

    def _advance(
        self,
        binding: OutcomeAuthorityBinding,
        request: AdvanceDelivery,
    ) -> OutcomeAuthorityBinding:
        if binding.output != request.output:
            _conflict("advance output does not match the published claim output")
        if binding.stage == DeliveryStage.PLANNING:
            if binding.candidate is None or binding.candidate.output != request.output:
                _conflict("Planning advance requires the published task-chain candidate")
            completed = {result.task_id for result in binding.results}
            destination = (
                DeliveryStage.COMPLETED
                if completed and completed == {task.task_id for task in binding.candidate.tasks}
                else DeliveryStage.IMPLEMENTATION
            )
            return binding.model_copy(
                update={
                    "stage": destination,
                    "tasks": binding.candidate.tasks,
                    "active_claim": None,
                    "output": None,
                    "candidate": None,
                    "return_context": None,
                    "recovery_attention": None,
                    "retry_diagnostic": None,
                    "block": None,
                    "requests": retained_requests(binding.requests),
                    "retry_fingerprint": None,
                    "retry_count": 0,
                }
            )
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            candidate = binding.result_candidate
            if candidate is None or candidate.output != request.output:
                _conflict("Implementation advance requires the published compact result")
            if any(result.task_id == candidate.result.task_id for result in binding.results):
                _conflict("promoted task already has a compact result")
            self._require_workspace().complete_reviewed(
                self._contract.change_id,
                request.claim_id,
                candidate.result.completed_commit,
            )
            results = (*binding.results, candidate.result)
            completed_tasks = {result.task_id for result in results}
            complete = completed_tasks == {task.task_id for task in binding.tasks}
            destination = DeliveryStage.COMPLETED if complete else DeliveryStage.IMPLEMENTATION
            return binding.model_copy(
                update={
                    "stage": destination,
                    "results": results,
                    "active_claim": None,
                    "output": None,
                    "result_candidate": None,
                    "return_context": None,
                    "recovery_attention": None,
                    "retry_diagnostic": None,
                    "block": None,
                    "requests": retained_requests(binding.requests),
                    "retry_fingerprint": None,
                    "retry_count": 0,
                }
            )
        return _conflict("current stage cannot advance")

    def _validate_retry_identity(
        self,
        binding: OutcomeAuthorityBinding,
        request: RetryDelivery,
        claim: DeliveryActiveClaim,
    ) -> None:
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.abandoned_commit is None or request.attempt_id is None:
                _conflict("Implementation retry requires attempt and abandoned-commit identity")
            if request.attempt_id != claim.attempt_id:
                _conflict("Implementation retry attempt does not match the active claim")
            manager = self._require_workspace()
            coordination = manager.show(self._contract.change_id)
            if coordination.writer is not None:
                manager.validate_writer_head(
                    self._contract.change_id,
                    request.claim_id,
                    request.abandoned_commit,
                )
                if coordination.writer.attempt_id != request.attempt_id:
                    _conflict("Implementation retry attempt does not own writer custody")
        elif request.abandoned_commit is not None or request.attempt_id is not None:
            _conflict("only Implementation retry accepts attempt commit identity")

    def _require_workspace(self) -> ChangeWorkspaceManager:
        if self._workspace_manager is None:
            _conflict("Implementation result transitions require workspace coordination")
        return self._workspace_manager

    def _validate_plan(
        self,
        binding: OutcomeAuthorityBinding,
        tasks: tuple[DeliveryTaskDefinition, ...],
    ) -> None:
        task_ids = tuple(task.task_id for task in tasks)
        if len(task_ids) != len(set(task_ids)):
            _conflict("Delivery task identities must be unique")
        self._validate_planner_return_plan(binding, tasks)
        outcome = next(item for item in self._contract.outcomes if item.outcome_id == binding.outcome_id)
        contract_commitments = set(outcome.commitment_ids)
        for task in tasks:
            if task.outcome_id != binding.outcome_id or task.plan_scope_id != binding.plan_scope_id:
                _reference("Delivery task belongs to another outcome or plan scope")
            if not set(task.commitment_ids) <= contract_commitments:
                _reference("Delivery task references an absent commitment")
            if not set(task.dependency_ids) <= set(task_ids) or task.task_id in task.dependency_ids:
                _reference("Delivery task dependency is absent or self-referential")
        ready = {task.task_id for task in tasks if not task.dependency_ids}
        visited = set(ready)
        while True:
            expanded = visited | {task.task_id for task in tasks if set(task.dependency_ids) <= visited}
            if expanded == visited:
                break
            visited = expanded
        if not ready or visited != set(task_ids):
            _conflict("Delivery task graph must be acyclic with at least one ready task")

    @staticmethod
    def _validate_planner_return_plan(
        binding: OutcomeAuthorityBinding,
        tasks: tuple[DeliveryTaskDefinition, ...],
    ) -> None:
        tasks_by_id = {task.task_id: task for task in tasks}
        completed_task_ids = {result.task_id for result in binding.results}
        if any(
            task.task_id not in tasks_by_id or _model_content(tasks_by_id[task.task_id]) != _model_content(task)
            for task in binding.tasks
            if task.task_id in completed_task_ids
        ):
            _conflict("Planning return must preserve completed task definitions and results")
        handoff = binding.builder_handoff_context
        if handoff is None or handoff.route != "same-outcome-planner":
            return
        original_task = tasks_by_id.get(handoff.original_task_id)
        if (
            original_task is None
            or original_task.task_id in completed_task_ids
            or original_task.commitment_ids != handoff.original_task_commitment_ids
            or original_task.maintained_surfaces != handoff.original_task_maintained_surfaces
        ):
            _conflict("Planning return must preserve the original task's maintained surfaces and commitments")
        if not set(original_task.dependency_ids) <= completed_task_ids:
            _conflict("Planning return must leave its original task claimable after advance")

    def _return(
        self,
        binding: OutcomeAuthorityBinding,
        request: ReturnDelivery,
    ) -> OutcomeAuthorityBinding:
        if request.target not in _RETURN_TARGETS.get(binding.stage, set()):
            _conflict("return target is not allowed from the current stage")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.preserved_commit is None or request.attempt_id is None:
                _conflict("Implementation return requires attempt and preserved-commit identity")
            self._require_builder_transition_exclusion(binding, request)
            manager = self._require_workspace()
            coordination = manager.show(self._contract.change_id)
            if coordination.writer is not None:
                manager.validate_writer_head(
                    self._contract.change_id,
                    request.claim_id,
                    request.preserved_commit,
                )
                if coordination.writer.attempt_id != request.attempt_id:
                    _conflict("Implementation return attempt does not own writer custody")
            context = DeliveryReturnContext(
                target=request.target,
                reason=request.reason,
                locators=request.locators,
                preserved_commit=request.preserved_commit,
                completed_boundary=coordination.last_reviewed_commit,
            )
            manager.restart(
                self._contract.change_id,
                request.attempt_id,
                request.preserved_commit,
            )
            if request.target == DeliveryStage.DESIGN:
                tasks: tuple[DeliveryTaskDefinition, ...] = ()
                results: tuple[DeliveryTaskResult, ...] = ()
            else:
                completed = {result.task_id for result in binding.results}
                tasks = tuple(task for task in binding.tasks if task.task_id in completed)
                results = binding.results
            return binding.model_copy(
                update={
                    "stage": request.target,
                    "tasks": tasks,
                    "results": results,
                    "active_claim": None,
                    "output": None,
                    "candidate": None,
                    "result_candidate": None,
                    "return_context": context,
                    "recovery_attention": None,
                    "retry_diagnostic": None,
                    "block": None,
                }
            )
        if binding.stage == DeliveryStage.PLANNING and request.source_boundary is None:
            _conflict("Planning return requires its admitted source boundary")
        context = DeliveryReturnContext(
            target=request.target,
            reason=request.reason,
            locators=request.locators,
            source_boundary=request.source_boundary,
        )
        returned = _reset_binding(binding, request.target)
        return returned.model_copy(
            update={
                "return_context": context,
                "retry_diagnostic": None,
                "requests": retained_requests(binding.requests),
            }
        )

    def _block(
        self,
        binding: OutcomeAuthorityBinding,
        request: BlockDelivery,
    ) -> OutcomeAuthorityBinding:
        if request.request is not None and request.request.outcome_id != binding.outcome_id:
            _reference("block request belongs to another outcome")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.request is None:
                _conflict("Implementation block requires a bounded user request")
            if request.resume_commit is None:
                _conflict("Implementation block requires a clean resume commit")
            self._require_builder_transition_exclusion(binding, request)
            claim = binding.active_claim
            if claim is None:
                _conflict("Implementation block requires an active claim")
            self._require_workspace().restart(
                self._contract.change_id,
                claim.attempt_id,
                request.resume_commit,
            )
        elif request.resume_commit is not None:
            _conflict("only Implementation block accepts a resume commit")
        block = DeliveryBlock(
            block_id=request.block_id,
            reason=request.reason,
            unblock_condition=request.unblock_condition,
            expected_evidence=request.expected_evidence,
            locators=request.locators,
            request_id=request.request.request_id if request.request is not None else None,
            resume_commit=request.resume_commit,
        )
        requests = (*binding.requests, request.request) if request.request is not None else binding.requests
        return binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "return_context": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
                "block": block,
                "requests": requests,
            }
        )

    def _require_builder_transition_exclusion(
        self, binding: OutcomeAuthorityBinding, request: BlockDelivery | ReturnDelivery
    ) -> None:
        claim = binding.active_claim
        if claim is None or claim.claim_id != request.claim_id:
            _conflict("diagnostic transition does not match the active Builder claim")
        if isinstance(request, ReturnDelivery) and request.attempt_id != claim.attempt_id:
            _conflict("diagnostic return does not match the active Builder attempt")
        snapshot = self._require_workspace().recovery_snapshot(self._contract.change_id, claim.attempt_id)
        if (
            snapshot.writer is None
            or snapshot.writer.claim_id != claim.claim_id
            or snapshot.writer.attempt_id != claim.attempt_id
        ):
            _conflict("diagnostic transition does not match Builder writer custody")
        submitted_commit = request.resume_commit if isinstance(request, BlockDelivery) else request.preserved_commit
        if submitted_commit != snapshot.branch_head:
            raise DeliveryWorkerExclusionRequiredError
        self.publish_recovery_attention(
            binding.outcome_id,
            DeliveryRecoveryAttention(
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                reason=request.reason,
                worktree_path=str(snapshot.worktree_path),
                branch_head=snapshot.branch_head,
                worktree_head=snapshot.worktree_head,
                last_reviewed_commit=snapshot.last_reviewed_commit,
                writer_claim_id=snapshot.writer.claim_id,
                custody_retained=True,
                retry_condition=(
                    "Diagnostic only: the current Builder retains custody. Host worker-exclusion evidence is missing; "
                    "no transition or restart is authorized. Resume requires verified exclusion through a supported "
                    "host recovery path, whose availability is not established by this diagnostic."
                ),
                diagnostic_transition=request,
            ),
        )
        raise DeliveryWorkerExclusionRequiredError

    def _change_intent_custody_participants(
        self,
        participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...],
        expected_finalization_attention: ChangeFinalizationAttention | None,
    ) -> tuple[TransactionParticipant | ReplacementTransactionParticipant, ...]:
        if self._workspace_manager is None:
            return participants
        operation = _declared_mutation()
        guard = self._workspace_manager.prepare_runtime_custody_guard(
            self._contract.change_id,
            expected_finalization_attention=expected_finalization_attention,
            operation=operation,
            mutation_class=pause_mutation_class(operation),
        )
        return (*participants, guard)

    def _pending_publication_participant(
        self,
        replacement: bytes,
        base_frontier_digest: str,
        transition_request_digest: str | None = None,
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        """Build the marker participant that tracks one exact local frontier replacement."""
        content = _model_content(
            DeliveryPendingStatePublication.pending(
                base_frontier_digest,
                hashlib.sha256(replacement).hexdigest(),
                transition_request_digest,
            )
        )
        relative_path = self._pending_publication_path.relative_to(self._target_root)
        if self._pending_publication_path.exists():
            return ReplacementTransactionParticipant(
                self._target_root,
                relative_path,
                self._pending_publication_path.read_bytes(),
                content,
            )
        return TransactionParticipant(self._target_root, relative_path, content)
