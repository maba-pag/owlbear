"""Pure Work Item projections over one immutable schema-v2 Delivery snapshot."""

from __future__ import annotations

import hashlib
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.delivery_runtime import (
    DeliveryBlock,
    DeliveryFrontier,
    DeliveryOperatorMove,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryReturnContext,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    parse_delivery_frontier,
)
from owlbear_delivery.target_contract import DeliveryCommitment, DeliveryContract, DeliveryOutcome


class WorkItemStage(StrEnum):
    """User-facing progress stages."""

    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
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
    CHANGE_PUBLICATION = "change-publication"


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
    FINALIZE = "finalize"
    RECONCILE_CHECKPOINT = "reconcile-checkpoint"
    MARK_READY = "mark-ready"
    OBSERVE_ACCEPTANCE = "observe-acceptance"
    START_ORCHESTRATION = "start-orchestration"


class WorkItemProgressKind(StrEnum):
    """Scope-specific progress category."""

    TASKS = "tasks"
    DESIGN_RETURN = "design-return"
    PLAN = "plan"
    PUBLICATION = "publication"


class WorkItemChangeLifecycle(StrEnum):
    """Change-level lifecycle shown by the portfolio group."""

    IN_DELIVERY = "in-delivery"
    FINALIZATION = "finalization"
    PUBLICATION = "publication"
    AWAITING_MERGE = "awaiting-merge"
    ACCEPTANCE = "acceptance"


class WorkItemPublicationPhase(StrEnum):
    """Durable Change publication phase derived from exact frontier receipts."""

    FINALIZATION_INVALIDATED = "finalization-invalidated"
    READY_FOR_FINALIZATION = "ready-for-finalization"
    CHECKPOINT_PENDING = "checkpoint-pending"
    PULL_REQUEST_DRAFT = "pull-request-draft"
    AWAITING_MERGE = "awaiting-merge"
    ACCEPTANCE_OBSERVED = "acceptance-observed"


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
    """One exact contract and frontier read for portfolio projection."""

    contract: DeliveryContract
    frontier: DeliveryFrontier
    version: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def capture(
        cls,
        contract: DeliveryContract,
        frontier_bytes: bytes,
    ) -> DeliveryPortfolioSnapshot:
        """Validate one frontier read and bind its exact content digest."""
        return cls(
            contract=contract,
            frontier=parse_delivery_frontier(frontier_bytes)[0],
            version=hashlib.sha256(frontier_bytes).hexdigest(),
        )

    @model_validator(mode="after")
    def _validate_bindings(self) -> DeliveryPortfolioSnapshot:
        contract_ids = tuple(outcome.outcome_id for outcome in self.contract.outcomes)
        binding_ids = tuple(binding.outcome_id for binding in self.frontier.bindings)
        if binding_ids != contract_ids:
            message = "Delivery snapshot bindings must match contract outcome order"
            raise ValueError(message)
        return self


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


class WorkItemPublicationView(_ProjectionModel):
    """Exact durable finalization, publication, and acceptance identities."""

    phase: WorkItemPublicationPhase
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finalized_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    published_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    pending_checkpoint_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    pending_checkpoint_triggers: tuple[str, ...] = ()
    invalidated_expected_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    invalidated_observed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    repository: str | None = None
    pull_request_number: int | None = Field(default=None, gt=0)
    pull_request_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    accepted_merge_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    merged_at: str | None = None


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
    publication: WorkItemPublicationView | None = None


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
            self._change_lifecycle()
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

    def publication_phase(self) -> WorkItemPublicationPhase:
        """Return the Change publication phase from the captured frontier."""
        return self._publication_phase()

    def show_view(self, item_key: str) -> WorkItemDetailView:
        """Return semantic and operator detail for one scope-qualified key."""
        card = next(item for item in self._cards if item.item_key == item_key)
        if card.scope == WorkItemScope.CHANGE_PUBLICATION:
            return WorkItemDetailView(
                snapshot_version=self._snapshot.version,
                change_title=self._snapshot.contract.title,
                card=card,
                promise="Publish the reviewed Change and observe its user-merged pull request.",
                operator_moves=self._snapshot.frontier.operator_moves,
                publication=self._publication_view(),
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
            return (*cards, self._publication_card())
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
        return WorkItemProgress(
            kind=WorkItemProgressKind.TASKS,
            label=f"{len(binding.results)} of {len(binding.tasks)} Delivery tasks reviewed",
            done=len(binding.results),
            total=len(binding.tasks),
        )

    def _publication_card(self) -> WorkItemCardView:
        phase = self._publication_phase()
        if phase == WorkItemPublicationPhase.FINALIZATION_INVALIDATED:
            needs, headline, next_actor = WorkItemNeed.NONE, "Finalization invalidated", WorkItemNextActor.AGENT
            next_step, progress = "Re-finalize the current Change head", "Head drift observed"
            action = WorkItemAction(
                kind=WorkItemActionKind.FINALIZE,
                label="Re-finalize Change",
                command=f"/finalize-change {self._snapshot.contract.change_id}",
            )
        elif phase == WorkItemPublicationPhase.READY_FOR_FINALIZATION:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = "Finalize the reviewed Change", "Ready for finalization"
            action = (
                WorkItemAction(
                    kind=WorkItemActionKind.FINALIZE,
                    label="Finalize Change",
                    command=f"/finalize-change {self._snapshot.contract.change_id}",
                )
                if self._finalization_action_available()
                else WorkItemAction()
            )
        elif phase == WorkItemPublicationPhase.CHECKPOINT_PENDING:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = "Reconcile the final checkpoint", "Checkpoint pending"
            action = WorkItemAction(kind=WorkItemActionKind.RECONCILE_CHECKPOINT, label="Publish checkpoint")
        elif phase == WorkItemPublicationPhase.PULL_REQUEST_DRAFT:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = "Mark the pull request ready", "Pull request is draft"
            action = WorkItemAction(kind=WorkItemActionKind.MARK_READY, label="Mark ready")
        elif phase == WorkItemPublicationPhase.AWAITING_MERGE:
            needs, headline, next_actor = WorkItemNeed.YOU, "Merge pull request in GitHub", WorkItemNextActor.YOU
            next_step, progress = headline, "Awaiting merge in GitHub"
            action = WorkItemAction(kind=WorkItemActionKind.OBSERVE_ACCEPTANCE, label="Check GitHub acceptance")
        else:
            needs, headline, next_actor = WorkItemNeed.NONE, None, WorkItemNextActor.AGENT
            next_step, progress = "Record accepted completion", "Merge observed"
            action = WorkItemAction(kind=WorkItemActionKind.OBSERVE_ACCEPTANCE, label="Complete accepted Change")
        activity = WorkItemActivity(
            state=WorkItemActivityState.IDLE if next_actor == WorkItemNextActor.YOU else WorkItemActivityState.READY
        )
        return WorkItemCardView(
            item_key="publication",
            work_item_id=self._snapshot.contract.change_id,
            change_id=self._snapshot.contract.change_id,
            scope=WorkItemScope.CHANGE_PUBLICATION,
            title="Change publication",
            stage=None,
            needs=needs,
            needs_headline=headline,
            next_actor=next_actor,
            next_step=next_step,
            activity=activity,
            progress=WorkItemProgress(kind=WorkItemProgressKind.PUBLICATION, label=progress),
            action=action,
        )

    def _finalization_action_available(self) -> bool:
        """Expose finalization while retaining hard runtime custody guards."""
        frontier = self._snapshot.frontier
        return (
            all(binding.stage == DeliveryStage.COMPLETED for binding in frontier.bindings)
            and all(binding.active_claim is None for binding in frontier.bindings)
            and frontier.integration_repair_claim is None
            and frontier.integration_completion is None
        )

    def _change_lifecycle(self) -> WorkItemChangeLifecycle:
        phase = self._publication_phase()
        if phase in {
            WorkItemPublicationPhase.FINALIZATION_INVALIDATED,
            WorkItemPublicationPhase.READY_FOR_FINALIZATION,
        }:
            return WorkItemChangeLifecycle.FINALIZATION
        if phase in {WorkItemPublicationPhase.CHECKPOINT_PENDING, WorkItemPublicationPhase.PULL_REQUEST_DRAFT}:
            return WorkItemChangeLifecycle.PUBLICATION
        if phase == WorkItemPublicationPhase.AWAITING_MERGE:
            return WorkItemChangeLifecycle.AWAITING_MERGE
        return WorkItemChangeLifecycle.ACCEPTANCE

    def _publication_phase(self) -> WorkItemPublicationPhase:
        frontier = self._snapshot.frontier
        if frontier.finalization_invalidation is not None:
            return WorkItemPublicationPhase.FINALIZATION_INVALIDATED
        if frontier.finalization is None:
            return WorkItemPublicationPhase.READY_FOR_FINALIZATION
        if frontier.pending_checkpoint is not None or frontier.published_head != frontier.finalization.exact_head:
            return WorkItemPublicationPhase.CHECKPOINT_PENDING
        if frontier.ready is None:
            return WorkItemPublicationPhase.PULL_REQUEST_DRAFT
        if frontier.merged_pull_request_latch is None:
            return WorkItemPublicationPhase.AWAITING_MERGE
        return WorkItemPublicationPhase.ACCEPTANCE_OBSERVED

    def _publication_view(self) -> WorkItemPublicationView:
        frontier = self._snapshot.frontier
        finalization = frontier.finalization
        pending = frontier.pending_checkpoint
        invalidation = frontier.finalization_invalidation
        ready = frontier.ready
        merged = frontier.merged_pull_request_latch
        return WorkItemPublicationView(
            phase=self._publication_phase(),
            finalization_id=finalization.finalization_id if finalization is not None else None,
            finalized_head=finalization.exact_head if finalization is not None else None,
            published_head=frontier.published_head,
            pending_checkpoint_head=pending.head if pending is not None else None,
            pending_checkpoint_triggers=tuple(trigger.kind.value for trigger in pending.triggers) if pending else (),
            invalidated_expected_head=invalidation.expected_head if invalidation is not None else None,
            invalidated_observed_head=invalidation.observed_head if invalidation is not None else None,
            repository=ready.repository if ready is not None else merged.repository if merged is not None else None,
            pull_request_number=ready.number if ready is not None else merged.number if merged is not None else None,
            pull_request_head=ready.head_sha if ready is not None else merged.head_sha if merged is not None else None,
            accepted_merge_commit=merged.accepted_merge_commit if merged is not None else None,
            merged_at=merged.merged_at.isoformat() if merged is not None else None,
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
            else "Publish the reviewed Change and observe its user-merged pull request.",
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
