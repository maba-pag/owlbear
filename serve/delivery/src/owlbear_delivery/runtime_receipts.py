"""Worker settlement models, private settlement receipts and administrative-move models."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from owlbear_delivery.runtime_models import (
    _BUILDER_HANDOFF_CHANGE_INTENT_FRONTIER_FIELDS,
    _FRONTIER_SCHEMA_VERSION,
    _MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS,
    _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION,
    REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES,
    BlockDelivery,
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryBuilderHandoffContext,
    DeliveryChangeAbandonment,
    DeliveryChangeDeferral,
    DeliveryFrontier,
    DeliveryOperatorMove,
    DeliveryPlanCandidate,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryStage,
    DeliveryWorkerRole,
    EngineWorkerDisposition,
    OutcomeAuthorityBinding,
    RetryDelivery,
    ReturnDelivery,
    _DeliveryModel,
    _model_content,
    _normalize_frontier,
    _receipt_digest,
    binding_has_n03_content,
    derive_change_stage,
    retained_requests,
)


def _require_legacy_content(
    schema_version: int,
    bindings: tuple[OutcomeAuthorityBinding, ...],
    request: DeliveryRequest | None = None,
) -> None:
    """Reject N03 content inside a schema-1 receipt (I2); writers emit schema 2 only."""
    if schema_version != 1:
        return
    if any(binding_has_n03_content(binding) for binding in bindings) or (
        request is not None and request.has_n03_content
    ):
        message = "schema-1 Delivery receipt cannot carry schema-2 evidence or scoped requests"
        raise ValueError(message)


class DeliveryPlanningRetrySettlement(_DeliveryModel):
    """Trusted Orchestrator report for one ended Planner retry invocation."""

    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    disposition: Literal["normal-return", "completed-timeout", "ended-without-result"]
    request: RetryDelivery | None = None

    @model_validator(mode="after")
    def _validate_completed_invocation(self) -> DeliveryPlanningRetrySettlement:
        if self.disposition == "normal-return":
            if self.request is None:
                message = "normal Planner retry settlement requires its unchanged RetryDelivery"
                raise ValueError(message)
            if self.request.outcome_id != self.outcome_id or self.request.claim_id != self.claim_id:
                message = "Planner retry request does not match its settlement identity"
                raise ValueError(message)
            if self.request.failure_code in REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES.values():
                message = f"{self.request.failure_code} is reserved for request-less Planner settlements"
                raise ValueError(message)
        elif self.request is not None:
            message = f"{self.disposition} Planner settlement cannot carry an inner request"
            raise ValueError(message)
        return self


class DeliveryBuilderInvocationSettlement(_DeliveryModel):
    """Trusted Orchestrator report for one ended Builder invocation."""

    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    task_id: str = Field(min_length=1, max_length=256)
    expected_last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    disposition: Literal["normal-return", "completed-timeout", "ended-without-result"]
    request: RetryDelivery | BlockDelivery | ReturnDelivery | None = None

    @model_validator(mode="after")
    def _validate_completed_invocation(self) -> DeliveryBuilderInvocationSettlement:
        if self.disposition == "normal-return":
            self._validate_normal_return()
        elif self.request is not None:
            message = f"{self.disposition} Builder settlement cannot carry an inner request"
            raise ValueError(message)
        return self

    def _validate_normal_return(self) -> None:
        request = self.request
        if request is None:
            message = "normal Builder settlement requires its unchanged RetryDelivery, BlockDelivery, or ReturnDelivery"
            raise ValueError(message)
        if request.outcome_id != self.outcome_id or request.claim_id != self.claim_id:
            message = "Builder settlement request does not match its outcome and claim"
            raise ValueError(message)
        if isinstance(request, RetryDelivery):
            if request.failure_code in REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES.values():
                message = f"{request.failure_code} is reserved for request-less Builder settlements"
                raise ValueError(message)
            if request.attempt_id != self.attempt_id:
                message = "Builder retry request does not match its attempt"
                raise ValueError(message)
        elif isinstance(request, BlockDelivery):
            if request.request is None or request.request.resolution is not None:
                message = "Builder block settlement requires an unanswered bounded user request"
                raise ValueError(message)
            if request.request.outcome_id != self.outcome_id:
                message = "Builder block request does not match its outcome"
                raise ValueError(message)
        elif request.attempt_id != self.attempt_id:
            message = "Builder return request does not match its attempt"
            raise ValueError(message)


class DeliveryEnginePlanningSettlement(DeliveryPlanningRetrySettlement):
    """Engine-authored end of one Planner invocation whose worker can no longer progress."""

    disposition: EngineWorkerDisposition  # type: ignore[assignment]


class DeliveryEngineBuilderSettlement(DeliveryBuilderInvocationSettlement):
    """Engine-authored end of one Builder invocation whose worker can no longer progress."""

    disposition: EngineWorkerDisposition  # type: ignore[assignment]


class _DeliveryPlanningRetrySettlementReceipt(_DeliveryModel):
    """Immutable result for replaying one exact completed Planner retry invocation."""

    schema_version: Literal[1, 2] = 2
    envelope: DeliveryEnginePlanningSettlement | DeliveryPlanningRetrySettlement
    result: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryPlanningRetrySettlementReceipt:
        _require_legacy_content(self.schema_version, (self.result,))
        if (
            self.result.outcome_id != self.envelope.outcome_id
            or self.result.stage != DeliveryStage.PLANNING
            or self.result.active_claim is not None
        ):
            message = "Planning retry settlement receipt result does not match its completed claim"
            raise ValueError(message)
        return self


class _DeliveryBuilderInvocationSettlementReceipt(_DeliveryModel):
    """Immutable result for replaying one exact completed Builder invocation."""

    schema_version: Literal[1, 2] = 2
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    envelope: DeliveryEngineBuilderSettlement | DeliveryBuilderInvocationSettlement
    handoff_context: DeliveryBuilderHandoffContext
    result: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderInvocationSettlementReceipt:
        envelope_request = self.envelope.request
        _require_legacy_content(
            self.schema_version,
            (self.result,),
            envelope_request.request if isinstance(envelope_request, BlockDelivery) else None,
        )
        context = self.handoff_context
        if (
            self.settlement_id != hashlib.sha256(_model_content(self.envelope)).hexdigest()
            or context.settlement_id != self.settlement_id
            or context.outcome_id != self.envelope.outcome_id
            or context.original_task_id != self.envelope.task_id
            or context.attempt_id != self.envelope.attempt_id
            or context.last_reviewed_commit != self.envelope.expected_last_reviewed_commit
            or self.result.outcome_id != self.envelope.outcome_id
            or self.result.active_claim is not None
            or self.result.builder_handoff_context != context
        ):
            message = "Builder invocation settlement receipt does not match its exact handoff"
            raise ValueError(message)
        expected_stage = (
            DeliveryStage.PLANNING
            if context.route == "same-outcome-planner"
            else DeliveryStage.DESIGN
            if context.route == "same-outcome-design"
            else DeliveryStage.IMPLEMENTATION
        )
        if self.result.stage != expected_stage:
            message = "Builder invocation settlement receipt has an incompatible route stage"
            raise ValueError(message)
        return self


class _DeliveryBuilderPlanPromotionReceipt(_DeliveryModel):
    """Immutable proof that one retained Builder return was promoted through Planning."""

    schema_version: Literal[1, 2] = 2
    promotion_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    planner_claim: DeliveryActiveClaim
    source_binding: OutcomeAuthorityBinding
    candidate: DeliveryPlanCandidate
    result_binding: OutcomeAuthorityBinding

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        source_binding: OutcomeAuthorityBinding,
        result_binding: OutcomeAuthorityBinding,
    ) -> _DeliveryBuilderPlanPromotionReceipt:
        """Create one exact receipt from the published Planner candidate and its successor."""
        context = source_binding.builder_handoff_context
        planner_claim = source_binding.active_claim
        candidate = source_binding.candidate
        if context is None or planner_claim is None or candidate is None:
            message = "Builder return promotion requires its exact Planning handoff, claim, and candidate"
            raise ValueError(message)
        values = {
            "change_id": change_id,
            "outcome_id": context.outcome_id,
            "settlement_id": context.settlement_id,
            "planner_claim": planner_claim,
            "source_binding": source_binding,
            "candidate": candidate,
            "result_binding": result_binding,
        }
        receipt = cls.model_construct(promotion_id="0" * 64, schema_version=2, **values)
        return cls(promotion_id=_receipt_digest(receipt, "promotion_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderPlanPromotionReceipt:
        _require_legacy_content(self.schema_version, (self.source_binding, self.result_binding))
        self._validate_identity()
        self._validate_task_lineage()
        self._validate_successor()
        if self.promotion_id != _receipt_digest(self, "promotion_id"):
            message = "Builder plan promotion receipt identity is invalid"
            raise ValueError(message)
        return self

    def _validate_identity(self) -> None:
        source = self.source_binding
        context = source.builder_handoff_context
        candidate = self.candidate
        task_chain_digest = hashlib.sha256(b"".join(_model_content(task) for task in candidate.tasks)).hexdigest()
        if (
            context is None
            or context.route != "same-outcome-planner"
            or context.outcome_id != self.outcome_id
            or context.settlement_id != self.settlement_id
            or source.outcome_id != self.outcome_id
            or source.stage != DeliveryStage.PLANNING
            or source.active_claim != self.planner_claim
            or self.planner_claim.worker_role != DeliveryWorkerRole.PLANNER
            or self.planner_claim.task_id is not None
            or source.result_candidate is not None
            or source.candidate != candidate
            or candidate.claim_id != self.planner_claim.claim_id
            or candidate.digest != task_chain_digest
            or candidate.candidate_id != f"plan-{task_chain_digest}"
            or source.output != candidate.output
        ):
            message = "Builder plan promotion receipt does not bind its exact Planner candidate"
            raise ValueError(message)

    def _validate_task_lineage(self) -> None:
        source = self.source_binding
        context = source.builder_handoff_context
        candidate_tasks = {task.task_id: task for task in self.candidate.tasks}
        source_tasks = {task.task_id: task for task in source.tasks}
        completed_task_ids = {result.task_id for result in source.results}
        original_task = candidate_tasks.get(context.original_task_id)
        if (
            len(candidate_tasks) != len(self.candidate.tasks)
            or any(
                task.outcome_id != self.outcome_id or task.plan_scope_id != source.plan_scope_id
                for task in self.candidate.tasks
            )
            or any(
                task_id not in candidate_tasks or candidate_tasks[task_id] != source_tasks.get(task_id)
                for task_id in completed_task_ids
            )
            or original_task is None
            or context.original_task_id in completed_task_ids
            or original_task.commitment_ids != context.original_task_commitment_ids
            or original_task.maintained_surfaces != context.original_task_maintained_surfaces
            or not set(original_task.dependency_ids) <= completed_task_ids
        ):
            message = "Builder plan promotion receipt changes completed or original task lineage"
            raise ValueError(message)

    def _validate_successor(self) -> None:
        context = self.source_binding.builder_handoff_context
        expected = self.source_binding.model_copy(
            update={
                "stage": DeliveryStage.IMPLEMENTATION,
                "tasks": self.candidate.tasks,
                "active_claim": None,
                "output": None,
                "candidate": None,
                "return_context": None,
                "builder_handoff_context": context.model_copy(update={"route": "same-task"}),
                "recovery_attention": None,
                "retry_diagnostic": None,
                "block": None,
                "requests": retained_requests(self.source_binding.requests),
                "retry_fingerprint": None,
                "retry_count": 0,
            }
        )
        if self.result_binding != expected or self.result_binding.results != self.source_binding.results:
            message = "Builder plan promotion receipt does not bind its exact same-task successor"
            raise ValueError(message)


class _DeliveryBuilderRequestResolutionReceipt(_DeliveryModel):
    """Immutable user answer bound to one exact local Builder pause."""

    schema_version: Literal[1, 2] = 2
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    request_id: str = Field(min_length=1)
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    builder_handoff_context: DeliveryBuilderHandoffContext
    resolved_request: DeliveryRequest
    updated_block: DeliveryBlock

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderRequestResolutionReceipt:
        _require_legacy_content(self.schema_version, (), self.resolved_request)
        context = self.builder_handoff_context
        resolution = self.resolved_request.resolution
        expected_note = None if resolution is None else resolution.response_text or resolution.selected_option_id
        if (
            context.route != "same-task"
            or context.outcome_id != self.outcome_id
            or context.settlement_id != self.settlement_id
            or self.resolved_request.request_id != self.request_id
            or self.resolved_request.outcome_id != self.outcome_id
            or resolution is None
            or (
                self.resolved_request.kind is DeliveryRequestKind.DECISION
                and (
                    resolution.selected_option_id is None
                    or resolution.selected_option_id
                    not in {option.option_id for option in self.resolved_request.options}
                )
            )
            or self.updated_block.request_id != self.request_id
            or not self.updated_block.resolved
            or self.updated_block.resolution_note != expected_note
            or self.updated_block.resolution_locators != (self.request_id,)
        ):
            message = "Builder request resolution receipt does not match its exact handoff"
            raise ValueError(message)
        return self


class _DeliveryBuilderHandoffChangeIntentReceipt(_DeliveryModel):
    """Immutable proof of one supported lifecycle intent during a retained Builder handoff."""

    schema_version: Literal[1, 2] = 2
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: Literal["defer", "resume", "abandon"]
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    builder_handoff_context: DeliveryBuilderHandoffContext
    sequence: int = Field(ge=1, le=_MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS)
    previous_receipt_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    before_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    before_frontier: DeliveryFrontier
    after_frontier: DeliveryFrontier
    deferral: DeliveryChangeDeferral | None = None
    abandonment: DeliveryChangeAbandonment | None = None

    @classmethod
    def create(  # noqa: PLR0913 - the receipt binds the exact typed transition and its frontier boundary.
        cls,
        *,
        action: Literal["defer", "resume", "abandon"],
        change_id: str,
        outcome_id: str,
        context: DeliveryBuilderHandoffContext,
        sequence: int,
        previous_receipt_id: str | None,
        before_frontier: DeliveryFrontier,
        after_frontier: DeliveryFrontier,
        deferral: DeliveryChangeDeferral | None,
        abandonment: DeliveryChangeAbandonment | None,
    ) -> _DeliveryBuilderHandoffChangeIntentReceipt:
        """Create one receipt from exact before/after typed frontier state."""
        values = {
            "action": action,
            "change_id": change_id,
            "outcome_id": outcome_id,
            "settlement_id": context.settlement_id,
            "builder_handoff_context": context,
            "sequence": sequence,
            "previous_receipt_id": previous_receipt_id,
            "before_frontier_digest": hashlib.sha256(_model_content(before_frontier)).hexdigest(),
            "after_frontier_digest": hashlib.sha256(_model_content(after_frontier)).hexdigest(),
            "before_frontier": before_frontier,
            "after_frontier": after_frontier,
            "deferral": deferral,
            "abandonment": abandonment,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=2, **values)
        return cls(receipt_id=_receipt_digest(candidate, "receipt_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderHandoffChangeIntentReceipt:
        self._validate_versions()
        self._validate_identity()
        self._validate_bound_frontiers()
        self._validate_action(self._changed_frontier_fields())
        if self.receipt_id != _receipt_digest(self, "receipt_id"):
            message = "Builder handoff change-intent receipt identity is invalid"
            raise ValueError(message)
        return self

    def _validate_identity(self) -> None:
        if (
            self.settlement_id != self.builder_handoff_context.settlement_id
            or self.outcome_id != self.builder_handoff_context.outcome_id
            or (self.sequence == 1) != (self.previous_receipt_id is None)
            or self.before_frontier_digest != hashlib.sha256(_model_content(self.before_frontier)).hexdigest()
            or self.after_frontier_digest != hashlib.sha256(_model_content(self.after_frontier)).hexdigest()
        ):
            message = "Builder handoff change-intent receipt identity is invalid"
            raise ValueError(message)

    def _validate_bound_frontiers(self) -> None:
        for frontier in (self.before_frontier, self.after_frontier):
            if any(binding.active_claim is not None for binding in frontier.bindings):
                message = "Builder handoff change-intent receipt cannot overlap an active claim"
                raise ValueError(message)
            if frontier.integration_repair_claim is not None:
                message = "Builder handoff change-intent receipt cannot overlap an active Integration claim"
                raise ValueError(message)
            matches = [binding for binding in frontier.bindings if binding.outcome_id == self.outcome_id]
            if len(matches) != 1 or matches[0].builder_handoff_context != self.builder_handoff_context:
                message = "Builder handoff change-intent receipt does not bind its retained context"
                raise ValueError(message)

    def _validate_versions(self) -> None:
        before, after = self.before_frontier.schema_version, self.after_frontier.schema_version
        legacy = _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION
        if (self.schema_version == 1 and (before, after) != (legacy, legacy)) or (
            self.schema_version != 1 and after != _FRONTIER_SCHEMA_VERSION
        ):
            message = "Builder handoff change-intent receipt frontiers do not match its schema"
            raise ValueError(message)

    def _changed_frontier_fields(self) -> set[str]:
        before, after = _normalize_frontier(self.before_frontier), _normalize_frontier(self.after_frontier)
        return {
            field_name
            for field_name in DeliveryFrontier.model_fields
            if getattr(before, field_name) != getattr(after, field_name)
        }

    def _validate_action(self, changed_fields: set[str]) -> None:
        if not changed_fields <= _BUILDER_HANDOFF_CHANGE_INTENT_FRONTIER_FIELDS:
            message = "Builder handoff change-intent receipt changes unsupported frontier fields"
            raise ValueError(message)
        if self.action == "defer":
            self._validate_deferral(changed_fields)
        elif self.action == "resume":
            self._validate_resume(changed_fields)
        else:
            self._validate_abandonment(changed_fields)

    def _validate_deferral(self, changed_fields: set[str]) -> None:
        deferral = self.after_frontier.change_deferral
        if (
            self.before_frontier.change_deferral is not None
            or self.before_frontier.change_abandonment is not None
            or deferral is None
            or self.deferral != deferral
            or self.abandonment is not None
            or deferral.change_id != self.change_id
            or deferral.prior_stage != derive_change_stage(self.before_frontier)
            or changed_fields != {"change_deferral"}
        ):
            message = "Builder handoff deferral receipt does not match its exact typed transition"
            raise ValueError(message)

    def _validate_resume(self, changed_fields: set[str]) -> None:
        deferral = self.before_frontier.change_deferral
        if (
            deferral is None
            or self.before_frontier.change_abandonment is not None
            or self.after_frontier.change_deferral is not None
            or self.after_frontier.change_abandonment is not None
            or self.deferral != deferral
            or self.abandonment is not None
            or deferral.change_id != self.change_id
            or changed_fields != {"change_deferral"}
        ):
            message = "Builder handoff resume receipt does not remove its exact typed deferral"
            raise ValueError(message)

    def _validate_abandonment(self, changed_fields: set[str]) -> None:
        abandonment = self.after_frontier.change_abandonment
        expected_changed_fields = {"change_abandonment"}
        if self.before_frontier.change_deferral is not None:
            expected_changed_fields.add("change_deferral")
        if self.before_frontier.pending_checkpoint is not None:
            expected_changed_fields.add("pending_checkpoint")
        if (
            self.before_frontier.change_abandonment is not None
            or self.before_frontier.change_completion is not None
            or abandonment is None
            or self.abandonment != abandonment
            or self.deferral != self.before_frontier.change_deferral
            or self.after_frontier.change_deferral is not None
            or self.after_frontier.pending_checkpoint is not None
            or abandonment.change_id != self.change_id
            or abandonment.prior_stage != derive_change_stage(self.before_frontier)
            or changed_fields != expected_changed_fields
        ):
            message = "Builder handoff abandonment receipt does not match its exact typed transition"
            raise ValueError(message)


class _DeliveryBuilderHandoffChangeIntentHead(_DeliveryModel):
    """CAS-updated reference to the latest immutable handoff intent receipt."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    builder_handoff_context: DeliveryBuilderHandoffContext
    latest_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    sequence: int = Field(ge=1, le=_MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS)

    @model_validator(mode="after")
    def _validate_head(self) -> _DeliveryBuilderHandoffChangeIntentHead:
        if (
            self.settlement_id != self.builder_handoff_context.settlement_id
            or self.outcome_id != self.builder_handoff_context.outcome_id
        ):
            message = "Builder handoff change-intent head identity is invalid"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class _BuilderHandoffChangeIntentMutation:
    before: DeliveryFrontier
    after: DeliveryFrontier
    action: Literal["defer", "resume", "abandon"]
    deferral: DeliveryChangeDeferral | None
    abandonment: DeliveryChangeAbandonment | None


class _DeliveryPlanningPauseReplay(_DeliveryModel):
    """Immutable result for replaying one exact request-bearing Planning pause."""

    schema_version: Literal[1, 2] = 2
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: BlockDelivery
    result: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_replay(self) -> _DeliveryPlanningPauseReplay:
        _require_legacy_content(self.schema_version, (self.result,), self.request.request)
        delivery_request = self.request.request
        block = self.result.block
        if delivery_request is None:
            message = "Planning pause replay requires its original bounded request"
            raise ValueError(message)
        if (
            self.request_digest != hashlib.sha256(_model_content(self.request)).hexdigest()
            or self.request.outcome_id != self.outcome_id
            or self.request.claim_id != self.claim_id
            or delivery_request.outcome_id != self.outcome_id
            or self.result.outcome_id != self.outcome_id
            or self.result.stage != DeliveryStage.PLANNING
            or self.result.active_claim is not None
            or block is None
            or block.block_id != self.request.block_id
            or block.reason != self.request.reason
            or block.unblock_condition != self.request.unblock_condition
            or block.expected_evidence != self.request.expected_evidence
            or block.locators != self.request.locators
            or block.request_id != delivery_request.request_id
            or block.resume_commit != self.request.resume_commit
            or not self.result.requests
            or self.result.requests[-1] != delivery_request
        ):
            message = "Planning pause replay receipt does not bind its original transition"
            raise ValueError(message)
        return self


def parse_planning_pause_receipt(content: bytes) -> _DeliveryPlanningPauseReplay:
    """Registered reader for schema-1 Planning pause receipts; the widened model validates them unchanged."""
    return _DeliveryPlanningPauseReplay.model_validate_json(content, strict=True)


def parse_planning_retry_receipt(content: bytes) -> _DeliveryPlanningRetrySettlementReceipt:
    """Registered reader for schema-1 Planning retry receipts."""
    return _DeliveryPlanningRetrySettlementReceipt.model_validate_json(content, strict=True)


def parse_builder_invocation_receipt(content: bytes) -> _DeliveryBuilderInvocationSettlementReceipt:
    """Registered reader for schema-1 Builder invocation receipts."""
    return _DeliveryBuilderInvocationSettlementReceipt.model_validate_json(content, strict=True)


def parse_builder_plan_promotion_receipt(content: bytes) -> _DeliveryBuilderPlanPromotionReceipt:
    """Registered reader for schema-1 Builder plan promotion receipts."""
    return _DeliveryBuilderPlanPromotionReceipt.model_validate_json(content, strict=True)


def parse_builder_request_resolution_receipt(content: bytes) -> _DeliveryBuilderRequestResolutionReceipt:
    """Registered reader for schema-1 request resolution receipts."""
    return _DeliveryBuilderRequestResolutionReceipt.model_validate_json(content, strict=True)


def parse_builder_handoff_change_intent_receipt(content: bytes) -> _DeliveryBuilderHandoffChangeIntentReceipt:
    """Registered reader for schema-1 handoff change-intent receipts."""
    return _DeliveryBuilderHandoffChangeIntentReceipt.model_validate_json(content, strict=True)


class AdministrativeDeliveryMove(_DeliveryModel):
    """Authorized operator movement to one earlier canonical stage."""

    move_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage
    reason: str = Field(min_length=1)
    expected_version: str = Field(pattern=r"^[0-9a-f]{64}$")


class AdministrativeDeliveryMovePreview(_DeliveryModel):
    """Exact invalidation closure bound to one frontier version."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage
    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    invalidated_outcome_ids: tuple[str, ...] = Field(min_length=1)


class AdministrativeDeliveryMoveResult(_DeliveryModel):
    """Persisted operator movement and its invalidated dependent closure."""

    move: DeliveryOperatorMove
    invalidated_outcome_ids: tuple[str, ...]
