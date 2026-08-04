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

    from owlbear_kanban.change_workspace import ChangeWorkspaceManager
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


class DeliveryWorkerRole(StrEnum):
    """Worker role selected mechanically from one canonical Delivery stage."""

    PLANNER = "planner"
    BUILDER = "builder"
    ASSEMBLY_REVIEWER = "assembly-reviewer"


class _DeliveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryOutputReference(_DeliveryModel):
    """Claim-bound identity and digest of one separately published phase output."""

    output_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    stage: DeliveryStage
    kind: DeliveryOutputKind
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeliveryTaskDefinition(_DeliveryModel):
    """Immutable executable authority for one bounded implementation result."""

    task_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    title: str = Field(min_length=1)
    result: str = Field(min_length=1)
    commitment_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    required_outputs: tuple[str, ...] = Field(min_length=1)
    maintained_surfaces: tuple[str, ...] = Field(min_length=1)
    constraints: tuple[str, ...]
    exclusions: tuple[str, ...]
    acceptance_observations: tuple[str, ...] = Field(min_length=1)
    proof_boundaries: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_references(self) -> DeliveryTaskDefinition:
        for references in (self.commitment_ids, self.dependency_ids):
            if len(references) != len(set(references)):
                message = "Delivery task references must be unique"
                raise ValueError(message)
        return self

    @property
    def digest(self) -> str:
        """Return the canonical immutable task-definition digest."""
        return hashlib.sha256(_model_content(self)).hexdigest()


class DeliveryPlanCandidate(_DeliveryModel):
    """One unpromoted claim-scoped canonical task chain."""

    candidate_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tasks: tuple[DeliveryTaskDefinition, ...] = Field(min_length=1)

    @property
    def output(self) -> DeliveryOutputReference:
        """Return the phase-output reference required for promotion."""
        return DeliveryOutputReference(
            output_id=self.candidate_id,
            claim_id=self.claim_id,
            stage=DeliveryStage.PLANNING,
            kind=DeliveryOutputKind.PLANNING,
            digest=self.digest,
        )


class DeliveryTaskResult(_DeliveryModel):
    """Compact immutable binding from promoted task authority to one exact commit."""

    result_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(min_length=1)
    task_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")


class DeliveryResultCandidate(_DeliveryModel):
    """One unpromoted claim-scoped compact implementation result."""

    candidate_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: DeliveryTaskResult

    @property
    def output(self) -> DeliveryOutputReference:
        """Return the phase-output reference required for result promotion."""
        return DeliveryOutputReference(
            output_id=self.candidate_id,
            claim_id=self.claim_id,
            stage=DeliveryStage.IMPLEMENTATION,
            kind=DeliveryOutputKind.IMPLEMENTATION,
            digest=self.digest,
        )


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
    resume_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")

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


class DeliveryReturnContext(_DeliveryModel):
    """Exact earlier-stage context consumed by the next owning cycle."""

    target: DeliveryStage
    reason: str = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    completed_boundary: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    source_boundary: str | None = None


class DeliveryRecoveryAttention(_DeliveryModel):
    """Operator-consumed evidence for one Build claim that cannot be removed safely."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    worktree_path: str = Field(min_length=1)
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    worktree_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer_claim_id: str | None = None
    custody_retained: bool
    retry_condition: str = Field(min_length=1)


class DeliveryActiveClaim(_DeliveryModel):
    """Recoverable execution identity for one active outcome claim."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None


class OutcomeAuthorityBinding(_DeliveryModel):
    """Canonical state and identity bindings for one admitted outcome."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    stage: DeliveryStage = DeliveryStage.PLANNING
    assembly_required: bool = False
    tasks: tuple[DeliveryTaskDefinition, ...] = ()
    results: tuple[DeliveryTaskResult, ...] = ()
    active_claim: DeliveryActiveClaim | None = None
    output: DeliveryOutputReference | None = None
    candidate: DeliveryPlanCandidate | None = None
    result_candidate: DeliveryResultCandidate | None = None
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryRecoveryAttention | None = None
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()

    @model_validator(mode="after")
    def _validate_state(self) -> OutcomeAuthorityBinding:
        if self.stage == DeliveryStage.COMPLETED and self.active_claim is not None:
            message = "completed outcomes cannot carry an active claim"
            raise ValueError(message)
        self._validate_active_claim()
        self._validate_recovery_attention()
        request_ids = tuple(request.request_id for request in self.requests)
        if len(request_ids) != len(set(request_ids)):
            message = "Delivery request identities must be unique per outcome"
            raise ValueError(message)
        task_ids = self.task_ids
        result_ids = self.result_ids
        if len(task_ids) != len(set(task_ids)) or len(result_ids) != len(set(result_ids)):
            message = "Delivery task and result identities must be unique per outcome"
            raise ValueError(message)
        if not {result.task_id for result in self.results} <= set(task_ids):
            message = "Delivery results must bind promoted task authority"
            raise ValueError(message)
        return self

    def _validate_active_claim(self) -> None:
        if self.active_claim is None:
            return
        expected_role = {
            DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
            DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
            DeliveryStage.ASSEMBLY: DeliveryWorkerRole.ASSEMBLY_REVIEWER,
        }.get(self.stage)
        if self.active_claim.worker_role != expected_role:
            message = "active claim worker role does not match its Delivery stage"
            raise ValueError(message)
        if self.stage == DeliveryStage.IMPLEMENTATION:
            if self.active_claim.task_id not in self.task_ids:
                message = "active Build claim must name promoted task authority"
                raise ValueError(message)
        elif self.active_claim.task_id is not None:
            message = "only active Build claims name task authority"
            raise ValueError(message)

    def _validate_recovery_attention(self) -> None:
        if self.recovery_attention is None:
            return
        if (
            self.active_claim is None
            or self.recovery_attention.attempt_id != self.active_claim.attempt_id
            or self.recovery_attention.claim_id != self.active_claim.claim_id
        ):
            message = "recovery attention must bind the current active claim"
            raise ValueError(message)

    @property
    def task_ids(self) -> tuple[str, ...]:
        """Project promoted task identities from their single typed authority."""
        return tuple(task.task_id for task in self.tasks)

    @property
    def result_ids(self) -> tuple[str, ...]:
        """Project compact result identities from their single typed authority."""
        return tuple(result.result_id for result in self.results)

    @property
    def active_claim_id(self) -> str | None:
        """Project the current claim identity without persisting a duplicate scalar."""
        return self.active_claim.claim_id if self.active_claim is not None else None

    @property
    def active_task_id(self) -> str | None:
        """Project the current task identity from its active claim."""
        return self.active_claim.task_id if self.active_claim is not None else None


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
    claim: DeliveryActiveClaim

    @property
    def claim_id(self) -> str:
        """Return the nested claim identity used by transition requests."""
        return self.claim.claim_id

    @property
    def task_id(self) -> str | None:
        """Return the nested task identity used by Build selection."""
        return self.claim.task_id


class PublishDeliveryOutput(_DeliveryModel):
    """Publish one claim-scoped candidate output without moving stage."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    output: DeliveryOutputReference


class PublishDeliveryPlan(_DeliveryModel):
    """Publish one complete claim-scoped task-chain candidate."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    tasks: tuple[DeliveryTaskDefinition, ...] = Field(min_length=1)


class PublishDeliveryResult(_DeliveryModel):
    """Publish one compact claim-scoped implementation result."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result: DeliveryTaskResult


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
    abandoned_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    attempt_id: str | None = None


class ReturnDelivery(_DeliveryModel):
    """Return one claim to an allowed earlier stage with successor context."""

    action: Literal["return"] = "return"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    target: DeliveryStage
    reason: str = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    attempt_id: str | None = None
    source_boundary: str | None = None


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
    resume_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


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

    def __init__(
        self,
        target_root: Path,
        contract: DeliveryContract,
        *,
        workspace_manager: ChangeWorkspaceManager | None = None,
    ) -> None:
        self._target_root = target_root.resolve()
        self._contract = contract
        self._workspace_manager = workspace_manager
        self._authority_digest = hashlib.sha256(_model_content(contract)).hexdigest()
        self._frontier_path = self._target_root / "delivery" / "changes" / contract.change_id / "frontier.json"
        self._validate_frontier(self._read()[0])

    @property
    def authority_digest(self) -> str:
        """Return the canonical admitted contract digest bound into task results."""
        return self._authority_digest

    @property
    def contract(self) -> DeliveryContract:
        """Return immutable admitted authority for scoped context projection."""
        return self._contract

    def frontier_bytes(self) -> bytes:
        """Return current canonical frontier bytes for OCC and failure proof."""
        return self._read()[1]

    def show_binding(self, outcome_id: str) -> OutcomeAuthorityBinding:
        """Return one current outcome binding."""
        return _find_binding(self._read()[0], outcome_id)

    def active_claims(self) -> tuple[tuple[str, DeliveryActiveClaim], ...]:
        """Return active claim identity keyed by outcome in authority order."""
        frontier, _content = self._read()
        return tuple(
            (binding.outcome_id, binding.active_claim)
            for binding in frontier.bindings
            if binding.active_claim is not None
        )

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

    def remove_active_claim(
        self,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> OutcomeAuthorityBinding:
        """Remove one exact failed claim without changing its canonical stage authority."""
        frontier, previous = self._read()
        binding = _find_binding(frontier, outcome_id)
        claim = binding.active_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("claim removal does not match the active execution identity")
        recovered = binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "recovery_attention": None,
            }
        )
        self._replace(previous, _replace_binding(frontier, binding, recovered))
        return recovered

    def publish_recovery_attention(
        self,
        outcome_id: str,
        attention: DeliveryRecoveryAttention,
    ) -> OutcomeAuthorityBinding:
        """Retain one exact active claim with deterministic operator repair evidence."""
        frontier, previous = self._read()
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

    def claimable_task_ids(self, outcome_id: str) -> tuple[str, ...]:
        """Return promoted tasks whose task dependencies have compact results."""
        binding = self.show_binding(outcome_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_claim_id is not None:
            return ()
        completed = {result.task_id for result in binding.results}
        return tuple(
            task.task_id
            for task in binding.tasks
            if task.task_id not in completed and set(task.dependency_ids) <= completed
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
        expected_role = {
            DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
            DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
            DeliveryStage.ASSEMBLY: DeliveryWorkerRole.ASSEMBLY_REVIEWER,
        }.get(binding.stage)
        if request.claim.worker_role != expected_role:
            _conflict("claim worker role does not match the current Delivery stage")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.task_id not in self.claimable_task_ids(request.outcome_id):
                _conflict("implementation task is not claimable")
        elif request.task_id is not None:
            _conflict("only Implementation claims name a task")
        claimed = binding.model_copy(
            update={
                "active_claim": request.claim,
                "output": None,
                "result_candidate": None,
                "recovery_attention": None,
            }
        )
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

    def publish_plan(self, request: PublishDeliveryPlan) -> DeliveryPlanCandidate:
        """Validate and persist one idempotent Planning candidate without movement."""
        frontier, previous = self._read()
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
        self._require_workspace().validate_writer_head(
            self._contract.change_id,
            request.claim_id,
            request.result.completed_commit,
        )
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
        updated = binding.model_copy(update={"result_candidate": candidate, "output": candidate.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return candidate

    def transition(self, request: DeliveryTransition) -> OutcomeAuthorityBinding:
        """Apply one worker-owned mechanical transition instruction."""
        frontier, previous = self._read()
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if isinstance(request, AdvanceDelivery):
            updated = self._advance(binding, request)
        elif isinstance(request, RetryDelivery):
            updated = self._retry(binding, request)
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
            if binding.candidate is None or binding.candidate.output != request.output:
                _conflict("Planning advance requires the published task-chain candidate")
            return binding.model_copy(
                update={
                    "stage": destination,
                    "tasks": binding.candidate.tasks,
                    "active_claim": None,
                    "output": None,
                    "candidate": None,
                    "return_context": None,
                    "recovery_attention": None,
                    "block": None,
                    "requests": (),
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
            destination = (
                (DeliveryStage.ASSEMBLY if binding.assembly_required else DeliveryStage.COMPLETED)
                if complete
                else DeliveryStage.IMPLEMENTATION
            )
            return binding.model_copy(
                update={
                    "stage": destination,
                    "results": results,
                    "active_claim": None,
                    "output": None,
                    "result_candidate": None,
                    "return_context": None,
                    "recovery_attention": None,
                    "block": None,
                    "requests": (),
                }
            )
        if binding.stage == DeliveryStage.ASSEMBLY:
            destination = DeliveryStage.COMPLETED
        else:
            _conflict("current stage cannot advance")
        return binding.model_copy(
            update={
                "stage": destination,
                "active_claim": None,
                "recovery_attention": None,
            }
        )

    def _retry(
        self,
        binding: OutcomeAuthorityBinding,
        request: RetryDelivery,
    ) -> OutcomeAuthorityBinding:
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.abandoned_commit is None or request.attempt_id is None:
                _conflict("Implementation retry requires attempt and abandoned-commit identity")
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
            manager.restart(
                self._contract.change_id,
                request.attempt_id,
                request.abandoned_commit,
            )
        elif request.abandoned_commit is not None or request.attempt_id is not None:
            _conflict("only Implementation retry accepts attempt commit identity")
        return binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "return_context": None,
                "recovery_attention": None,
            }
        )

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
        return returned.model_copy(update={"return_context": context})

    def _block(
        self,
        binding: OutcomeAuthorityBinding,
        request: BlockDelivery,
    ) -> OutcomeAuthorityBinding:
        if request.request is not None and request.request.outcome_id != binding.outcome_id:
            _reference("block request belongs to another outcome")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.resume_commit is None:
                _conflict("Implementation block requires a clean resume commit")
            self._require_workspace().release_writer_at_head(
                self._contract.change_id,
                request.claim_id,
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
                "block": block,
                "requests": requests,
            }
        )

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
            "tasks": (),
            "results": (),
            "active_claim": None,
            "output": None,
            "candidate": None,
            "result_candidate": None,
            "return_context": None,
            "recovery_attention": None,
            "block": None,
            "requests": (),
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
    "DeliveryResultCandidate",
    "DeliveryReturnContext",
    "DeliveryRuntime",
    "DeliveryRuntimeConflictError",
    "DeliveryRuntimeReferenceError",
    "DeliveryStage",
    "DeliveryTaskDefinition",
    "DeliveryTaskResult",
    "OutcomeAuthorityBinding",
    "PublishDeliveryOutput",
    "PublishDeliveryPlan",
    "PublishDeliveryResult",
    "RetryDelivery",
    "ReturnDelivery",
]
