"""Pure Work Item projections over one immutable schema-v2 Delivery snapshot."""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.delivery_runtime import (
    DeliveryBlock,
    DeliveryFrontier,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryOperatorMove,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryReturnContext,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    integration_attention_disposition,
)
from owlbear_delivery.target_contract import DeliveryCommitment, DeliveryContract, DeliveryOutcome


class WorkItemStage(StrEnum):
    """User-facing progress stages."""

    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    ASSEMBLY = "assembly"
    COMPLETED = "completed"


class WorkItemAttention(StrEnum):
    """Orthogonal attention state for one work item."""

    USER = "user"
    AGENT = "agent"
    WAITING = "waiting"
    NONE = "none"


class WorkItemScope(StrEnum):
    """Production Work Item scopes."""

    OUTCOME = "outcome"
    CHANGE_INTEGRATION = "change-integration"


class WorkItemNeed(StrEnum):
    """Condition requiring intervention or blocking progress."""

    YOU = "you"
    DEPENDENCY = "dependency"
    NONE = "none"


class WorkItemNextActor(StrEnum):
    """Who or what is expected to advance one work item next."""

    YOU = "you"
    AGENT = "agent"
    DEPENDENCY = "dependency"
    NONE = "none"


class WorkItemActivityState(StrEnum):
    """Current execution state independent from Needs."""

    IDLE = "idle"
    READY = "ready"
    WORKING = "working"
    REPAIRING = "repairing"


class WorkItemActionKind(StrEnum):
    """Typed operator action available from one Work Item."""

    NONE = "none"
    ANSWER_REQUEST = "answer-request"
    CLEAR_BLOCK = "clear-block"
    RECOVER_CLAIM = "recover-claim"
    INTEGRATE_CHANGE = "integrate-change"
    RETRY_INTEGRATION = "retry-integration"
    START_ORCHESTRATION = "start-orchestration"


class WorkItemProgressKind(StrEnum):
    """Scope-specific progress category."""

    TASKS = "tasks"
    ASSEMBLY = "assembly"
    DESIGN_RETURN = "design-return"
    PLAN = "plan"
    INTEGRATION = "integration"


class WorkItemChangeLifecycle(StrEnum):
    """Change-level lifecycle shown by the portfolio group."""

    IN_DELIVERY = "in-delivery"
    INTEGRATION = "integration"


class _ProjectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WorkItemProjection(_ProjectionModel):
    """One durable semantic identity with derived operational state."""

    work_item_id: str
    change_id: str
    scope: str
    title: str
    promise: str
    stage: WorkItemStage
    attention: WorkItemAttention
    dependency_ready: bool
    commitment_ids: tuple[str, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    task_count: int = 0
    reviewed_task_count: int = 0
    next_action: str


class WorkItemDetail(_ProjectionModel):
    """Semantic detail kept one drill-down from the portfolio."""

    projection: WorkItemProjection
    acceptance: tuple[str, ...] = ()
    return_context: DeliveryReturnContext | None = None


class DeliveryPortfolioSnapshot(_ProjectionModel):
    """One exact contract/frontier read and current Integration target identity."""

    contract: DeliveryContract
    frontier: DeliveryFrontier
    version: str = Field(pattern=r"^[0-9a-f]{64}$")
    integration_target: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def capture(
        cls,
        contract: DeliveryContract,
        frontier_bytes: bytes,
        *,
        integration_target: str,
        target_head: str,
    ) -> DeliveryPortfolioSnapshot:
        """Validate one frontier read and bind its exact content digest."""
        return cls(
            contract=contract,
            frontier=DeliveryFrontier.model_validate_json(frontier_bytes),
            version=hashlib.sha256(frontier_bytes).hexdigest(),
            integration_target=integration_target,
            target_head=target_head,
        )

    @model_validator(mode="after")
    def _validate_bindings(self) -> DeliveryPortfolioSnapshot:
        contract_ids = tuple(outcome.outcome_id for outcome in self.contract.outcomes)
        binding_ids = tuple(binding.outcome_id for binding in self.frontier.bindings)
        if binding_ids != contract_ids:
            message = "Delivery snapshot bindings must match contract outcome order"
            raise ValueError(message)
        return self

    @property
    def integration_attention_superseded(self) -> bool:
        """Return whether retained attention names an older target head."""
        attention = self.frontier.integration_attention
        return attention is not None and attention.target_head != self.target_head


class WorkItemActivity(_ProjectionModel):
    """Bounded execution state shown independently from Needs and Action."""

    state: WorkItemActivityState
    worker_role: DeliveryWorkerRole | None = None
    started_at: str | None = None
    task_id: str | None = None


class WorkItemAction(_ProjectionModel):
    """One typed user action, if current authority permits it."""

    kind: WorkItemActionKind = WorkItemActionKind.NONE
    label: str | None = None
    command: str | None = None


class WorkItemProgress(_ProjectionModel):
    """Scope-applicable progress with an explicit noun."""

    kind: WorkItemProgressKind
    label: str = Field(min_length=1)
    done: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)


class WorkItemIntegrationAttentionRef(_ProjectionModel):
    """Bounded identity and route for one retained Integration attention."""

    attention_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    code: DeliveryIntegrationAttentionCode
    disposition: DeliveryIntegrationAttentionDisposition
    superseded: bool


class WorkItemCardView(_ProjectionModel):
    """One dense portfolio row derived from a Delivery snapshot."""

    item_key: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    scope: WorkItemScope
    title: str = Field(min_length=1)
    stage: WorkItemStage | None
    needs: WorkItemNeed
    needs_headline: str | None = None
    next_actor: WorkItemNextActor
    next_step: str = Field(min_length=1)
    activity: WorkItemActivity
    progress: WorkItemProgress
    action: WorkItemAction
    integration_attention: WorkItemIntegrationAttentionRef | None = None


class ChangeGroupView(_ProjectionModel):
    """One Change grouping and its admitted current Work Items."""

    change_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: WorkItemChangeLifecycle
    outcome_total: int = Field(ge=1)
    outcome_completed: int = Field(ge=0)
    items: tuple[WorkItemCardView, ...]


class WorkItemClaimView(_ProjectionModel):
    """Bounded active-claim identity without process or owner internals."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None


class WorkItemRecoveryView(_ProjectionModel):
    """Bounded recovery state without workspace custody paths."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    custody_retained: bool
    retry_condition: str = Field(min_length=1)


class WorkItemDependencyView(_ProjectionModel):
    """Named dependency and its current stage."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    title: str = Field(min_length=1)
    stage: WorkItemStage


class WorkItemTaskEvidence(_ProjectionModel):
    """Bounded task authority and reviewed result evidence."""

    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    result: str = Field(min_length=1)
    status: str = Field(pattern=r"^(pending|active|reviewed)$")
    completed_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    acceptance_observations: tuple[str, ...]
    proof_boundaries: tuple[str, ...]


class WorkItemIntegrationView(_ProjectionModel):
    """Human-legible Integration state with retained exact diagnostics."""

    attention_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    code: DeliveryIntegrationAttentionCode | None = None
    disposition: DeliveryIntegrationAttentionDisposition | None = None
    headline: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    conflicted_paths: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    retry_condition: str | None = None
    superseded: bool = False
    repair_active: bool = False


class WorkItemDetailView(_ProjectionModel):
    """Semantic and operator detail from the same portfolio snapshot."""

    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_title: str = Field(min_length=1)
    card: WorkItemCardView
    promise: str = Field(min_length=1)
    acceptance: tuple[str, ...] = ()
    commitments: tuple[DeliveryCommitment, ...] = ()
    dependencies: tuple[WorkItemDependencyView, ...] = ()
    tasks: tuple[WorkItemTaskEvidence, ...] = ()
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()
    active_claim: WorkItemClaimView | None = None
    return_context: DeliveryReturnContext | None = None
    operator_moves: tuple[DeliveryOperatorMove, ...] = ()
    recovery_attention: WorkItemRecoveryView | None = None
    integration: WorkItemIntegrationView | None = None


_CONFLICT_PATH = re.compile(r"^CONFLICT \([^)]*\): .*? in (?P<path>.+)$")
_STAGE_PATH = re.compile(r"^[0-7]{6} [0-9a-f]{40} [123]\t(?P<path>.+)$")


def integration_conflict_paths(diagnostics: tuple[str, ...]) -> tuple[str, ...]:
    """Parse retained merge-tree diagnostics without executing Git."""
    preferred = tuple(match.group("path") for line in diagnostics if (match := _CONFLICT_PATH.match(line)) is not None)
    candidates = preferred or tuple(
        match.group("path") for line in diagnostics if (match := _STAGE_PATH.match(line)) is not None
    )
    return tuple(dict.fromkeys(candidates))


class WorkItemProjector:
    """Derive MCP and Cockpit views from one immutable Delivery snapshot."""

    def __init__(self, snapshot: DeliveryPortfolioSnapshot) -> None:
        self._snapshot = snapshot
        self._outcomes = {item.outcome_id: item for item in snapshot.contract.outcomes}
        self._bindings = {item.outcome_id: item for item in snapshot.frontier.bindings}
        self._cards = self._project_cards()
        self._items = {card.work_item_id: self._compatibility_projection(card) for card in self._cards}

    def list_items(self) -> tuple[WorkItemProjection, ...]:
        """Return MCP-compatible projections in snapshot order."""
        return tuple(self._items[card.work_item_id] for card in self._cards)

    def show(self, work_item_id: str) -> WorkItemDetail:
        """Return semantic detail for one projected identity."""
        projection = self._items[work_item_id]
        outcome = self._outcomes.get(work_item_id)
        return WorkItemDetail(
            projection=projection,
            acceptance=outcome.acceptance if outcome is not None else (),
            return_context=self._bindings[work_item_id].return_context if outcome is not None else None,
        )

    def group_view(self) -> ChangeGroupView:
        """Return one grouped Cockpit portfolio view."""
        completed = sum(binding.stage == DeliveryStage.COMPLETED for binding in self._snapshot.frontier.bindings)
        lifecycle = (
            WorkItemChangeLifecycle.INTEGRATION
            if completed == len(self._snapshot.frontier.bindings)
            else WorkItemChangeLifecycle.IN_DELIVERY
        )
        return ChangeGroupView(
            change_id=self._snapshot.contract.change_id,
            title=self._snapshot.contract.title,
            snapshot_version=self._snapshot.version,
            lifecycle=lifecycle,
            outcome_total=len(self._snapshot.contract.outcomes),
            outcome_completed=completed,
            items=self._cards,
        )

    def show_view(self, item_key: str) -> WorkItemDetailView:
        """Return semantic and operator detail for one scope-qualified key."""
        card = next(item for item in self._cards if item.item_key == item_key)
        if card.scope == WorkItemScope.CHANGE_INTEGRATION:
            return WorkItemDetailView(
                snapshot_version=self._snapshot.version,
                change_title=self._snapshot.contract.title,
                card=card,
                promise="Publish the reviewed change and completed history to the Integration target.",
                operator_moves=self._snapshot.frontier.operator_moves,
                integration=self._integration_view(),
            )
        outcome_id = card.work_item_id
        outcome = self._outcomes[outcome_id]
        binding = self._bindings[outcome_id]
        return WorkItemDetailView(
            snapshot_version=self._snapshot.version,
            change_title=self._snapshot.contract.title,
            card=card,
            promise=outcome.promise,
            acceptance=outcome.acceptance,
            commitments=tuple(
                item for item in self._snapshot.contract.commitments if item.commitment_id in outcome.commitment_ids
            ),
            dependencies=tuple(self._dependency_view(identity) for identity in outcome.dependency_ids),
            tasks=self._task_evidence(binding),
            block=binding.block,
            requests=binding.requests,
            active_claim=self._claim_view(binding),
            return_context=binding.return_context,
            operator_moves=self._snapshot.frontier.operator_moves,
            recovery_attention=self._recovery_view(binding.recovery_attention),
        )

    def _project_cards(self) -> tuple[WorkItemCardView, ...]:
        cards = tuple(
            self._outcome_card(outcome, self._bindings[outcome.outcome_id])
            for outcome in self._snapshot.contract.outcomes
        )
        if all(binding.stage == DeliveryStage.COMPLETED for binding in self._snapshot.frontier.bindings):
            return (*cards, self._integration_card())
        return cards

    def _outcome_card(self, outcome: DeliveryOutcome, binding: OutcomeAuthorityBinding) -> WorkItemCardView:
        needs, headline = self._outcome_needs(outcome, binding)
        next_actor, next_step = self._outcome_next(binding, needs, headline)
        return WorkItemCardView(
            item_key=f"outcome:{outcome.outcome_id}",
            work_item_id=outcome.outcome_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.OUTCOME,
            title=outcome.title,
            stage=WorkItemStage(binding.stage.value),
            needs=needs,
            needs_headline=headline,
            next_actor=next_actor,
            next_step=next_step,
            activity=self._outcome_activity(binding, needs),
            progress=self._outcome_progress(binding),
            action=self._outcome_action(binding),
        )

    def _outcome_needs(
        self,
        outcome: DeliveryOutcome,
        binding: OutcomeAuthorityBinding,
    ) -> tuple[WorkItemNeed, str | None]:
        if binding.stage == DeliveryStage.DESIGN:
            return WorkItemNeed.YOU, "Re-admission required"
        pending_request = next((item for item in binding.requests if item.resolution is None), None)
        if pending_request is not None:
            headline = "Decision required" if pending_request.kind.value == "decision" else "Action required"
            return WorkItemNeed.YOU, headline
        if binding.block is not None and not binding.block.resolved:
            return WorkItemNeed.YOU, "Block requires evidence"
        if binding.recovery_attention is not None:
            return WorkItemNeed.YOU, "Claim recovery required"
        incomplete = tuple(
            identity for identity in outcome.dependency_ids if self._bindings[identity].stage != DeliveryStage.COMPLETED
        )
        if incomplete:
            return WorkItemNeed.DEPENDENCY, f"Waiting on {', '.join(incomplete)}"
        return WorkItemNeed.NONE, None

    @staticmethod
    def _outcome_next(
        binding: OutcomeAuthorityBinding,
        needs: WorkItemNeed,
        headline: str | None,
    ) -> tuple[WorkItemNextActor, str]:
        if needs == WorkItemNeed.YOU:
            return WorkItemNextActor.YOU, headline or "Your attention is required"
        if needs == WorkItemNeed.DEPENDENCY:
            return WorkItemNextActor.DEPENDENCY, headline or "Waiting on another Outcome"
        if binding.active_claim is not None:
            return WorkItemNextActor.AGENT, "Work in progress"
        if binding.stage == DeliveryStage.COMPLETED:
            return WorkItemNextActor.NONE, "Complete — no action needed"
        return WorkItemNextActor.AGENT, "Ready for Orchestration"

    @staticmethod
    def _outcome_activity(binding: OutcomeAuthorityBinding, needs: WorkItemNeed) -> WorkItemActivity:
        claim = binding.active_claim
        if claim is not None:
            return WorkItemActivity(
                state=WorkItemActivityState.WORKING,
                worker_role=claim.worker_role,
                started_at=claim.started_at,
                task_id=claim.task_id,
            )
        if binding.stage == DeliveryStage.COMPLETED or needs != WorkItemNeed.NONE:
            return WorkItemActivity(state=WorkItemActivityState.IDLE)
        return WorkItemActivity(state=WorkItemActivityState.READY)

    @staticmethod
    def _outcome_action(binding: OutcomeAuthorityBinding) -> WorkItemAction:
        if binding.stage == DeliveryStage.DESIGN:
            return WorkItemAction()
        pending_request = next((item for item in binding.requests if item.resolution is None), None)
        if pending_request is not None:
            return WorkItemAction(kind=WorkItemActionKind.ANSWER_REQUEST, label="Answer request")
        if binding.block is not None and not binding.block.resolved and binding.block.request_id is None:
            return WorkItemAction(kind=WorkItemActionKind.CLEAR_BLOCK, label="Clear block")
        if binding.recovery_attention is not None:
            return WorkItemAction(kind=WorkItemActionKind.RECOVER_CLAIM, label="Recover claim")
        return WorkItemAction()

    @staticmethod
    def _outcome_progress(binding: OutcomeAuthorityBinding) -> WorkItemProgress:
        if binding.stage == DeliveryStage.DESIGN:
            return WorkItemProgress(
                kind=WorkItemProgressKind.DESIGN_RETURN,
                label="Returned to Design",
            )
        if binding.stage == DeliveryStage.PLANNING:
            return WorkItemProgress(kind=WorkItemProgressKind.PLAN, label="Task plan not published")
        if binding.stage == DeliveryStage.ASSEMBLY:
            return WorkItemProgress(
                kind=WorkItemProgressKind.ASSEMBLY,
                label="Tasks reviewed — assembling",
                done=len(binding.results),
                total=len(binding.tasks),
            )
        return WorkItemProgress(
            kind=WorkItemProgressKind.TASKS,
            label=f"{len(binding.results)} of {len(binding.tasks)} Delivery tasks reviewed",
            done=len(binding.results),
            total=len(binding.tasks),
        )

    def _integration_card(self) -> WorkItemCardView:
        attention = self._snapshot.frontier.integration_attention
        superseded = self._snapshot.integration_attention_superseded
        repair_active = self._snapshot.frontier.integration_repair_claim is not None
        if repair_active:
            needs, headline = WorkItemNeed.NONE, None
            next_actor = WorkItemNextActor.AGENT
            next_step = "Integration repair in progress"
            activity = WorkItemActivity(
                state=WorkItemActivityState.REPAIRING,
                worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
                started_at=self._snapshot.frontier.integration_repair_claim.started_at,
            )
            action = WorkItemAction()
            progress = "Repair in progress"
        elif superseded:
            needs, headline = WorkItemNeed.NONE, "Integration target moved"
            next_actor = WorkItemNextActor.AGENT
            next_step = "Retry against the current target"
            activity = WorkItemActivity(state=WorkItemActivityState.READY)
            action = WorkItemAction(kind=WorkItemActionKind.RETRY_INTEGRATION, label="Retry Integration")
            progress = "Awaiting retry against current target"
        elif attention is None:
            needs, headline = WorkItemNeed.NONE, None
            next_actor = WorkItemNextActor.AGENT
            next_step = "Integrate the reviewed Change"
            activity = WorkItemActivity(state=WorkItemActivityState.READY)
            action = WorkItemAction(kind=WorkItemActionKind.INTEGRATE_CHANGE, label="Integrate Change")
            progress = "Not attempted"
        else:
            disposition = integration_attention_disposition(attention.code)
            if disposition == DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED:
                needs, headline = WorkItemNeed.NONE, None
                next_actor = WorkItemNextActor.AGENT
                next_step = "Run a reviewed Integration repair"
                activity = WorkItemActivity(
                    state=WorkItemActivityState.READY,
                    worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
                )
                action = WorkItemAction(
                    kind=WorkItemActionKind.START_ORCHESTRATION,
                    label="Run Orchestration",
                    command="/orchestrate",
                )
                progress = "Merge conflict"
            elif disposition == DeliveryIntegrationAttentionDisposition.RETRYABLE:
                needs, headline = WorkItemNeed.NONE, "Integration retry available"
                next_actor = WorkItemNextActor.AGENT
                next_step = "Retry against the current target"
                activity = WorkItemActivity(state=WorkItemActivityState.READY)
                action = WorkItemAction(kind=WorkItemActionKind.RETRY_INTEGRATION, label="Retry Integration")
                progress = "Awaiting retry against current target"
            else:
                needs, headline = WorkItemNeed.YOU, _integration_headline(attention.code)
                next_actor = WorkItemNextActor.YOU
                next_step = headline
                activity = WorkItemActivity(state=WorkItemActivityState.IDLE)
                action = WorkItemAction()
                progress = "Attempt failed"
        return WorkItemCardView(
            item_key="integration",
            work_item_id=self._snapshot.contract.change_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.CHANGE_INTEGRATION,
            title="Integration",
            stage=None,
            needs=needs,
            needs_headline=headline,
            next_actor=next_actor,
            next_step=next_step,
            activity=activity,
            progress=WorkItemProgress(kind=WorkItemProgressKind.INTEGRATION, label=progress),
            action=action,
            integration_attention=(
                WorkItemIntegrationAttentionRef(
                    attention_id=attention.attention_id,
                    code=attention.code,
                    disposition=integration_attention_disposition(attention.code),
                    superseded=superseded,
                )
                if attention is not None
                else None
            ),
        )

    def _compatibility_projection(self, card: WorkItemCardView) -> WorkItemProjection:
        outcome = self._outcomes.get(card.work_item_id)
        binding = self._bindings.get(card.work_item_id)
        attention = {
            WorkItemNeed.YOU: WorkItemAttention.USER,
            WorkItemNeed.DEPENDENCY: WorkItemAttention.WAITING,
            WorkItemNeed.NONE: WorkItemAttention.AGENT
            if card.activity.state
            in {
                WorkItemActivityState.READY,
                WorkItemActivityState.WORKING,
                WorkItemActivityState.REPAIRING,
            }
            else WorkItemAttention.NONE,
        }[card.needs]
        return WorkItemProjection(
            work_item_id=card.work_item_id,
            change_id=card.change_id,
            scope=card.scope.value,
            title=outcome.title if outcome is not None else self._snapshot.contract.title,
            promise=outcome.promise
            if outcome is not None
            else "Publish the reviewed change and completed history to the Integration target.",
            stage=card.stage or WorkItemStage.COMPLETED,
            attention=attention,
            dependency_ready=card.needs != WorkItemNeed.DEPENDENCY,
            commitment_ids=outcome.commitment_ids if outcome is not None else (),
            dependency_ids=outcome.dependency_ids if outcome is not None else (),
            task_count=len(binding.tasks) if binding is not None else 0,
            reviewed_task_count=len(binding.results) if binding is not None else 0,
            next_action=card.action.label or card.needs_headline or card.progress.label,
        )

    def _dependency_view(self, outcome_id: str) -> WorkItemDependencyView:
        return WorkItemDependencyView(
            outcome_id=outcome_id,
            title=self._outcomes[outcome_id].title,
            stage=WorkItemStage(self._bindings[outcome_id].stage.value),
        )

    @staticmethod
    def _claim_view(binding: OutcomeAuthorityBinding) -> WorkItemClaimView | None:
        claim = binding.active_claim
        if claim is None:
            return None
        return WorkItemClaimView(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            started_at=claim.started_at,
            worker_role=claim.worker_role,
            task_id=claim.task_id,
        )

    @staticmethod
    def _recovery_view(attention: DeliveryRecoveryAttention | None) -> WorkItemRecoveryView | None:
        if attention is None:
            return None
        return WorkItemRecoveryView(
            attempt_id=attention.attempt_id,
            claim_id=attention.claim_id,
            reason=attention.reason,
            custody_retained=attention.custody_retained,
            retry_condition=attention.retry_condition,
        )

    @staticmethod
    def _task_evidence(binding: OutcomeAuthorityBinding) -> tuple[WorkItemTaskEvidence, ...]:
        results = {item.task_id: item for item in binding.results}
        active_task_id = binding.active_claim.task_id if binding.active_claim is not None else None
        return tuple(
            WorkItemTaskEvidence(
                task_id=task.task_id,
                title=task.title,
                result=task.result,
                status=(
                    "reviewed" if task.task_id in results else "active" if task.task_id == active_task_id else "pending"
                ),
                completed_commit=results[task.task_id].completed_commit if task.task_id in results else None,
                acceptance_observations=task.acceptance_observations,
                proof_boundaries=task.proof_boundaries,
            )
            for task in binding.tasks
        )

    def _integration_view(self) -> WorkItemIntegrationView:
        attention = self._snapshot.frontier.integration_attention
        repair_active = self._snapshot.frontier.integration_repair_claim is not None
        if attention is None:
            return WorkItemIntegrationView(
                headline="Ready to integrate",
                explanation=(
                    f"Every Outcome is complete and the Change can publish to {self._snapshot.integration_target}."
                ),
            )
        superseded = self._snapshot.integration_attention_superseded
        paths = integration_conflict_paths(attention.diagnostics)
        disposition = integration_attention_disposition(attention.code)
        headline = "Integration target moved" if superseded else _integration_headline(attention.code)
        explanation = (
            "The Integration target changed after the previous attempt."
            if superseded
            else (
                f"{len(paths)} conflicting files require a reviewed repair."
                if disposition == DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED and paths
                else "Integration is ready to retry against the current target."
                if disposition == DeliveryIntegrationAttentionDisposition.RETRYABLE
                else "Integration retained evidence that requires your review."
            )
        )
        return WorkItemIntegrationView(
            attention_id=attention.attention_id,
            code=attention.code,
            disposition=disposition,
            headline=headline,
            explanation=explanation,
            conflicted_paths=paths,
            diagnostics=attention.diagnostics,
            retry_condition=(
                "Retry Integration against the current target head; the previous verdict is stale."
                if superseded
                else attention.retry_condition
            ),
            superseded=superseded,
            repair_active=repair_active,
        )


def _integration_headline(code: DeliveryIntegrationAttentionCode) -> str:
    return {
        DeliveryIntegrationAttentionCode.MERGE_CONFLICT: "Merge conflict",
        DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY: "Authority revision required",
        DeliveryIntegrationAttentionCode.TARGET_CAS_LOST: "Integration retry available",
        DeliveryIntegrationAttentionCode.REVISION_PENDING: "Revision pending",
        DeliveryIntegrationAttentionCode.TARGET_IDENTITY_MISMATCH: "Target identity changed",
        DeliveryIntegrationAttentionCode.PACKAGE_MUTATED: "Delivery package changed",
        DeliveryIntegrationAttentionCode.COMPLETED_HISTORY_MUTATED: "Completed history changed",
        DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH: "Reviewed boundary changed",
        DeliveryIntegrationAttentionCode.REVIEWED_WORKTREE_DIRTY: "Reviewed worktree has uncommitted changes",
        DeliveryIntegrationAttentionCode.CANDIDATE_PROOF_FAILED: "Candidate verification failed",
    }[code]
