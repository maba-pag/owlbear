"""Mechanical schema-v2 Delivery state and worker-owned transitions."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from owlbear_kanban.runtime_transaction import ReplacementTransactionParticipant, RuntimeTransaction

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_kanban.target_contract import DeliveryContract


class DeliveryStage(StrEnum):
    """Canonical outcome progress stages."""

    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    ASSEMBLY = "assembly"
    COMPLETED = "completed"


class DeliveryChangeStage(StrEnum):
    """Change lifecycle derived from canonical outcome state."""

    DESIGN = "design"
    ACTIVE_DELIVERY = "active-delivery"
    INTEGRATION = "integration"
    COMPLETED = "completed"


class DeliveryOutputKind(StrEnum):
    """Minimal phase-output categories consumed by mechanical transitions."""

    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    ASSEMBLY = "assembly"
    COMPLETED = "completed"


class DeliveryRequestKind(StrEnum):
    """Bounded user request categories."""

    DECISION = "decision"
    ACTION = "action"


class _DeliveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryOutputReference(_DeliveryModel):
    """Claim-bound identity and digest of one separately published phase output."""

    output_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    stage: DeliveryStage
    kind: DeliveryOutputKind
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeliveryRequestOption(_DeliveryModel):
    """One bounded Decision Request option."""

    option_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class DeliveryRequestResolution(_DeliveryModel):
    """User-owned selected option, free-text answer, or both."""

    selected_option_id: str | None = None
    response_text: str | None = None

    @model_validator(mode="after")
    def _require_answer(self) -> DeliveryRequestResolution:
        if self.selected_option_id is None and (self.response_text is None or not self.response_text.strip()):
            message = "request resolution requires a selected option or response text"
            raise ValueError(message)
        return self


class DeliveryRequest(_DeliveryModel):
    """One bounded request retained because resumed work consumes its answer."""

    request_id: str = Field(min_length=1)
    kind: DeliveryRequestKind
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    summary: str = Field(min_length=1)
    options: tuple[DeliveryRequestOption, ...] = ()
    resolution: DeliveryRequestResolution | None = None

    @model_validator(mode="after")
    def _validate_options(self) -> DeliveryRequest:
        option_ids = tuple(option.option_id for option in self.options)
        if len(option_ids) != len(set(option_ids)):
            message = "request option identities must be unique"
            raise ValueError(message)
        if self.kind == DeliveryRequestKind.DECISION and not self.options:
            message = "Decision Requests require bounded options"
            raise ValueError(message)
        return self


class DeliveryBlock(_DeliveryModel):
    """Same-stage block and its durable clearing evidence."""

    block_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    unblock_condition: str = Field(min_length=1)
    expected_evidence: tuple[str, ...] = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    request_id: str | None = None
    resolution_note: str | None = None
    resolution_locators: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        """Return whether request or operator evidence cleared this block."""
        return self.resolution_note is not None


class DeliveryOperatorMove(_DeliveryModel):
    """One operator-directed backward movement and invalidated closure."""

    move_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    destination: DeliveryStage
    reason: str = Field(min_length=1)
    invalidated_outcome_ids: tuple[str, ...] = Field(min_length=1)


class OutcomeAuthorityBinding(_DeliveryModel):
    """Canonical state and identity bindings for one admitted outcome."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    stage: DeliveryStage = DeliveryStage.PLANNING
    assembly_required: bool = False
    task_ids: tuple[str, ...] = ()
    result_ids: tuple[str, ...] = ()
    active_claim_id: str | None = None
    output: DeliveryOutputReference | None = None
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()

    @model_validator(mode="after")
    def _validate_state(self) -> OutcomeAuthorityBinding:
        if self.stage == DeliveryStage.COMPLETED and self.active_claim_id is not None:
            message = "completed outcomes cannot carry an active claim"
            raise ValueError(message)
        request_ids = tuple(request.request_id for request in self.requests)
        if len(request_ids) != len(set(request_ids)):
            message = "Delivery request identities must be unique per outcome"
            raise ValueError(message)
        return self


class DeliveryFrontier(_DeliveryModel):
    """Canonical schema-v2 outcome state persisted beside Delivery authority."""

    schema_version: Literal[1] = 1
    bindings: tuple[OutcomeAuthorityBinding, ...]
    operator_moves: tuple[DeliveryOperatorMove, ...] = ()
    integration_result_id: str | None = None

    @model_validator(mode="after")
    def _validate_identities(self) -> DeliveryFrontier:
        outcome_ids = tuple(binding.outcome_id for binding in self.bindings)
        scope_ids = tuple(binding.plan_scope_id for binding in self.bindings)
        move_ids = tuple(move.move_id for move in self.operator_moves)
        if len(outcome_ids) != len(set(outcome_ids)) or len(scope_ids) != len(set(scope_ids)):
            message = "Delivery frontier identities must be unique"
            raise ValueError(message)
        if len(move_ids) != len(set(move_ids)):
            message = "Delivery operator move identities must be unique"
            raise ValueError(message)
        return self


class ActivateDeliveryClaim(_DeliveryModel):
    """Claim one dependency-ready outcome in its current stage."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)


class PublishDeliveryOutput(_DeliveryModel):
    """Publish one claim-scoped candidate output without moving stage."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    output: DeliveryOutputReference


class AdvanceDelivery(_DeliveryModel):
    """Advance after naming the required current-stage output."""

    action: Literal["advance"] = "advance"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    output: DeliveryOutputReference


class RetryDelivery(_DeliveryModel):
    """End a claim and leave its outcome in the same stage."""

    action: Literal["retry"] = "retry"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)


class ReturnDelivery(_DeliveryModel):
    """Return one claim to an allowed earlier stage with successor context."""

    action: Literal["return"] = "return"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    target: DeliveryStage
    reason: str = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)


class BlockDelivery(_DeliveryModel):
    """End one claim in place with an optional bounded user request."""

    action: Literal["block"] = "block"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    block_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    unblock_condition: str = Field(min_length=1)
    expected_evidence: tuple[str, ...] = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    request: DeliveryRequest | None = None


type DeliveryTransition = Annotated[
    AdvanceDelivery | RetryDelivery | ReturnDelivery | BlockDelivery,
    Field(discriminator="action"),
]
DELIVERY_TRANSITION_ADAPTER = TypeAdapter(DeliveryTransition)


class AdministrativeDeliveryMove(_DeliveryModel):
    """Authorized operator movement to one earlier canonical stage."""

    move_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage
    reason: str = Field(min_length=1)


class AdministrativeDeliveryMoveResult(_DeliveryModel):
    """Persisted operator movement and its invalidated dependent closure."""

    move: DeliveryOperatorMove
    invalidated_outcome_ids: tuple[str, ...]


class DeliveryRuntimeConflictError(RuntimeError):
    """A Delivery mutation is stale or violates canonical routing invariants."""

    code = "ERR_DELIVERY_RUNTIME_CONFLICT"


class DeliveryRuntimeReferenceError(ValueError):
    """A Delivery mutation references absent contract authority."""

    code = "ERR_DELIVERY_RUNTIME_REFERENCE"


_STAGE_ORDER = {
    DeliveryStage.DESIGN: 0,
    DeliveryStage.PLANNING: 1,
    DeliveryStage.IMPLEMENTATION: 2,
    DeliveryStage.ASSEMBLY: 3,
    DeliveryStage.COMPLETED: 4,
}
_RETURN_TARGETS = {
    DeliveryStage.PLANNING: {DeliveryStage.DESIGN},
    DeliveryStage.IMPLEMENTATION: {DeliveryStage.PLANNING, DeliveryStage.DESIGN},
    DeliveryStage.ASSEMBLY: {DeliveryStage.PLANNING, DeliveryStage.DESIGN},
}


class DeliveryRuntime:
    """Apply worker instructions and operator correction to one Delivery frontier."""

    def __init__(self, target_root: Path, contract: DeliveryContract) -> None:
        self._target_root = target_root.resolve()
        self._contract = contract
        self._frontier_path = self._target_root / "delivery" / "changes" / contract.change_id / "frontier.json"
        self._validate_frontier(self._read()[0])

    def frontier_bytes(self) -> bytes:
        """Return current canonical frontier bytes for OCC and failure proof."""
        return self._read()[1]

    def show_binding(self, outcome_id: str) -> OutcomeAuthorityBinding:
        """Return one current outcome binding."""
        return _find_binding(self._read()[0], outcome_id)

    def claimable_outcome_ids(self) -> tuple[str, ...]:
        """Return stable dependency-ready, unblocked, unclaimed outcome identities."""
        frontier, _content = self._read()
        completed = {binding.outcome_id for binding in frontier.bindings if binding.stage == DeliveryStage.COMPLETED}
        dependencies = {outcome.outcome_id: set(outcome.dependency_ids) for outcome in self._contract.outcomes}
        return tuple(
            binding.outcome_id
            for binding in frontier.bindings
            if binding.stage not in {DeliveryStage.DESIGN, DeliveryStage.COMPLETED}
            and binding.active_claim_id is None
            and (binding.block is None or binding.block.resolved)
            and dependencies[binding.outcome_id] <= completed
        )

    def change_stage(self) -> DeliveryChangeStage:
        """Derive change lifecycle from canonical outcome state."""
        frontier, _content = self._read()
        if frontier.integration_result_id is not None:
            return DeliveryChangeStage.COMPLETED
        stages = {binding.stage for binding in frontier.bindings}
        if DeliveryStage.DESIGN in stages:
            return DeliveryChangeStage.DESIGN
        if stages == {DeliveryStage.COMPLETED}:
            return DeliveryChangeStage.INTEGRATION
        return DeliveryChangeStage.ACTIVE_DELIVERY

    def activate_claim(self, request: ActivateDeliveryClaim) -> OutcomeAuthorityBinding:
        """Bind one fresh claim to a currently claimable outcome."""
        frontier, previous = self._read()
        binding = _find_binding(frontier, request.outcome_id)
        if request.outcome_id not in self.claimable_outcome_ids():
            _conflict("outcome is not claimable")
        if any(item.active_claim_id == request.claim_id for item in frontier.bindings):
            _conflict("active claim identity already exists")
        claimed = binding.model_copy(update={"active_claim_id": request.claim_id, "output": None})
        self._replace(previous, _replace_binding(frontier, binding, claimed))
        return claimed

    def publish_output(self, request: PublishDeliveryOutput) -> DeliveryOutputReference:
        """Persist one exact active-claim output without changing stage."""
        frontier, previous = self._read()
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

    def transition(self, request: DeliveryTransition) -> OutcomeAuthorityBinding:
        """Apply one worker-owned mechanical transition instruction."""
        frontier, previous = self._read()
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if isinstance(request, AdvanceDelivery):
            updated = self._advance(binding, request)
        elif isinstance(request, RetryDelivery):
            updated = binding.model_copy(update={"active_claim_id": None, "output": None})
        elif isinstance(request, ReturnDelivery):
            updated = self._return(binding, request)
        else:
            updated = self._block(binding, request)
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return updated

    def resolve_request(
        self,
        request_id: str,
        resolution: DeliveryRequestResolution,
    ) -> DeliveryRequest:
        """Persist one user answer and clear its same-stage block."""
        frontier, previous = self._read()
        binding, request = _find_request(frontier, request_id)
        if request.resolution is not None:
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
        self._replace(previous, _replace_binding(frontier, binding, updated))
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
        binding = _find_binding(frontier, outcome_id)
        block = binding.block
        if block is None or block.block_id != block_id or block.request_id is not None or block.resolved:
            _conflict("requestless block is not clearable")
        cleared = block.model_copy(update={"resolution_note": operator_note, "resolution_locators": locators})
        updated = binding.model_copy(update={"block": cleared})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return updated

    def administrative_move(
        self,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Move backward and invalidate the completed dependent closure."""
        frontier, previous = self._read()
        binding = _find_binding(frontier, request.outcome_id)
        if _STAGE_ORDER[request.target] >= _STAGE_ORDER[binding.stage]:
            _conflict("administrative movement must target an earlier stage")
        invalidated = _completed_dependent_closure(self._contract, frontier, request.outcome_id)
        updated_bindings = tuple(
            _reset_binding(item, request.target if item.outcome_id == request.outcome_id else DeliveryStage.PLANNING)
            if item.outcome_id in invalidated
            else item
            for item in frontier.bindings
        )
        ordered = tuple(item.outcome_id for item in frontier.bindings if item.outcome_id in invalidated)
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
            update={"bindings": updated_bindings, "operator_moves": (*frontier.operator_moves, move)}
        )
        self._replace(previous, updated)
        return AdministrativeDeliveryMoveResult(move=move, invalidated_outcome_ids=ordered)

    def _advance(
        self,
        binding: OutcomeAuthorityBinding,
        request: AdvanceDelivery,
    ) -> OutcomeAuthorityBinding:
        if binding.output != request.output:
            _conflict("advance output does not match the published claim output")
        if binding.stage == DeliveryStage.PLANNING:
            destination = DeliveryStage.IMPLEMENTATION
        elif binding.stage == DeliveryStage.IMPLEMENTATION:
            destination = DeliveryStage.ASSEMBLY if binding.assembly_required else DeliveryStage.COMPLETED
        elif binding.stage == DeliveryStage.ASSEMBLY:
            destination = DeliveryStage.COMPLETED
        else:
            _conflict("current stage cannot advance")
        return binding.model_copy(update={"stage": destination, "active_claim_id": None})

    def _return(
        self,
        binding: OutcomeAuthorityBinding,
        request: ReturnDelivery,
    ) -> OutcomeAuthorityBinding:
        if request.target not in _RETURN_TARGETS.get(binding.stage, set()):
            _conflict("return target is not allowed from the current stage")
        return _reset_binding(binding, request.target)

    def _block(
        self,
        binding: OutcomeAuthorityBinding,
        request: BlockDelivery,
    ) -> OutcomeAuthorityBinding:
        if request.request is not None and request.request.outcome_id != binding.outcome_id:
            _reference("block request belongs to another outcome")
        block = DeliveryBlock(
            block_id=request.block_id,
            reason=request.reason,
            unblock_condition=request.unblock_condition,
            expected_evidence=request.expected_evidence,
            locators=request.locators,
            request_id=request.request.request_id if request.request is not None else None,
        )
        requests = (*binding.requests, request.request) if request.request is not None else binding.requests
        return binding.model_copy(update={"active_claim_id": None, "block": block, "requests": requests})

    def _read(self) -> tuple[DeliveryFrontier, bytes]:
        RuntimeTransaction.recover_all(self._target_root)
        try:
            content = self._frontier_path.read_bytes()
            return DeliveryFrontier.model_validate_json(content), content
        except (OSError, ValueError) as exc:
            message = f"Delivery frontier is missing or invalid: {self._contract.change_id}"
            raise DeliveryRuntimeReferenceError(message) from exc

    def _replace(self, previous: bytes, frontier: DeliveryFrontier) -> None:
        replacement = _model_content(frontier)
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        transaction_id = hashlib.sha256(previous + replacement).hexdigest()
        RuntimeTransaction(self._target_root, f"delivery-runtime-{transaction_id}", (participant,)).commit()

    def _validate_frontier(self, frontier: DeliveryFrontier) -> None:
        expected = tuple((scope.outcome_id, scope.scope_id) for scope in self._contract.plan_scopes)
        actual = tuple((binding.outcome_id, binding.plan_scope_id) for binding in frontier.bindings)
        if actual != expected:
            _reference("Delivery frontier does not match its admitted contract")


def _find_binding(frontier: DeliveryFrontier, outcome_id: str) -> OutcomeAuthorityBinding:
    try:
        return next(binding for binding in frontier.bindings if binding.outcome_id == outcome_id)
    except StopIteration as exc:
        _reference(f"Delivery outcome is absent: {outcome_id}", exc)


def _find_request(frontier: DeliveryFrontier, request_id: str) -> tuple[OutcomeAuthorityBinding, DeliveryRequest]:
    matches = [
        (binding, request)
        for binding in frontier.bindings
        for request in binding.requests
        if request.request_id == request_id
    ]
    if len(matches) != 1:
        _reference(f"Delivery request is absent or ambiguous: {request_id}")
    return matches[0]


def _replace_binding(
    frontier: DeliveryFrontier,
    previous: OutcomeAuthorityBinding,
    replacement: OutcomeAuthorityBinding,
) -> DeliveryFrontier:
    return frontier.model_copy(
        update={"bindings": tuple(replacement if item == previous else item for item in frontier.bindings)}
    )


def _require_claim(binding: OutcomeAuthorityBinding, claim_id: str) -> None:
    if binding.active_claim_id != claim_id:
        _conflict("transition does not match the active claim")


def _reset_binding(binding: OutcomeAuthorityBinding, stage: DeliveryStage) -> OutcomeAuthorityBinding:
    return binding.model_copy(
        update={
            "stage": stage,
            "assembly_required": False,
            "task_ids": (),
            "result_ids": (),
            "active_claim_id": None,
            "output": None,
            "block": None,
        }
    )


def _completed_dependent_closure(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    outcome_id: str,
) -> set[str]:
    bindings = {binding.outcome_id: binding for binding in frontier.bindings}
    invalidated = {outcome_id}
    while True:
        expanded = invalidated | {
            outcome.outcome_id
            for outcome in contract.outcomes
            if bindings[outcome.outcome_id].stage == DeliveryStage.COMPLETED
            if set(outcome.dependency_ids) & invalidated
        }
        if expanded == invalidated:
            return invalidated
        invalidated = expanded


def _model_content(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _conflict(message: str) -> None:
    raise DeliveryRuntimeConflictError(message)


def _reference(message: str, cause: Exception | None = None) -> None:
    if cause is None:
        raise DeliveryRuntimeReferenceError(message)
    raise DeliveryRuntimeReferenceError(message) from cause


__all__ = [
    "DELIVERY_TRANSITION_ADAPTER",
    "ActivateDeliveryClaim",
    "AdministrativeDeliveryMove",
    "AdministrativeDeliveryMoveResult",
    "AdvanceDelivery",
    "BlockDelivery",
    "DeliveryBlock",
    "DeliveryChangeStage",
    "DeliveryFrontier",
    "DeliveryOperatorMove",
    "DeliveryOutputKind",
    "DeliveryOutputReference",
    "DeliveryRequest",
    "DeliveryRequestKind",
    "DeliveryRequestOption",
    "DeliveryRequestResolution",
    "DeliveryRuntime",
    "DeliveryRuntimeConflictError",
    "DeliveryRuntimeReferenceError",
    "DeliveryStage",
    "OutcomeAuthorityBinding",
    "PublishDeliveryOutput",
    "RetryDelivery",
    "ReturnDelivery",
]
