"""Pure work-item projections over target semantic authority and evidence."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.target_authority import (
    AuthorityStatus,
    DesignReentryBriefing,
    Outcome,
    PlanScopeKind,
    TargetAuthority,
    TaskPlanScope,
)


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
    REPAIR = "repair"
    NONE = "none"


class WorkItemIntegrationDisposition(StrEnum):
    """Projected operational state for change-level Integration."""

    READY = "ready"
    RETRYABLE = "retryable"
    REPAIR_REQUIRED = "repair-required"
    OPERATOR_REQUIRED = "operator-required"


class _ProjectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TaskProgress(_ProjectionModel):
    """Reviewed task progress for one accepted plan scope."""

    scope_id: str = Field(min_length=1)
    task_count: int = Field(ge=0)
    reviewed_task_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_reviewed_count(self) -> TaskProgress:
        if self.reviewed_task_count > self.task_count:
            msg = "reviewed task count cannot exceed task count"
            raise ValueError(msg)
        return self


class WorkItemIntegrationState(_ProjectionModel):
    """Bounded Integration state supplied by the owning runtime."""

    disposition: WorkItemIntegrationDisposition
    code: str | None = None

    @model_validator(mode="after")
    def _validate_code(self) -> WorkItemIntegrationState:
        if (self.disposition == WorkItemIntegrationDisposition.READY) != (self.code is None):
            msg = "only ready Integration omits an attention code"
            raise ValueError(msg)
        return self


class WorkItemEvidence(_ProjectionModel):
    """Read-side contract written by the target runtime in T2."""

    planned_scope_ids: tuple[str, ...] = ()
    task_progress: tuple[TaskProgress, ...] = ()
    completed_assembly_scope_ids: tuple[str, ...] = ()
    pending_request_work_item_ids: tuple[str, ...] = ()
    design_reentry_briefings: tuple[DesignReentryBriefing, ...] = ()
    integration: WorkItemIntegrationState | None = None

    @model_validator(mode="after")
    def _validate_unique_progress(self) -> WorkItemEvidence:
        scope_ids = tuple(item.scope_id for item in self.task_progress)
        if len(scope_ids) != len(set(scope_ids)):
            msg = "task progress scope identities must be unique"
            raise ValueError(msg)
        return self


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
    replacement_ids: tuple[str, ...] = ()
    task_count: int = 0
    reviewed_task_count: int = 0
    next_action: str


class WorkItemDetail(_ProjectionModel):
    """Semantic detail kept one drill-down from the portfolio."""

    projection: WorkItemProjection
    acceptance: tuple[str, ...] = ()
    briefing: DesignReentryBriefing | None = None


class WorkItemProjector:
    """Derive portfolio and semantic detail without mutating authority."""

    def __init__(self, authority: TargetAuthority, evidence: WorkItemEvidence) -> None:
        self._authority = authority
        self._evidence = evidence
        self._scopes = {scope.target_id: scope for scope in authority.task_plan_scopes}
        self._progress = {item.scope_id: item for item in evidence.task_progress}
        # A runtime briefing describes a later failure than the admitted one, so it wins.
        self._briefings = {
            item.work_item_id: item for item in (*authority.design_reentries, *evidence.design_reentry_briefings)
        }
        self._items = self._project_items()

    def list_items(self) -> tuple[WorkItemProjection, ...]:
        """Return active items first and retained historical identities last."""
        return tuple(
            sorted(
                self._items.values(),
                key=lambda item: (item.stage == WorkItemStage.COMPLETED, item.work_item_id),
            )
        )

    def show(self, work_item_id: str) -> WorkItemDetail:
        """Return semantic detail for one projected identity."""
        projection = self._items[work_item_id]
        outcome = next((item for item in self._authority.outcomes if item.outcome_id == work_item_id), None)
        return WorkItemDetail(
            projection=projection,
            acceptance=outcome.acceptance if outcome is not None else (),
            briefing=self._briefings.get(work_item_id),
        )

    def _project_items(self) -> dict[str, WorkItemProjection]:
        if not self._authority.outcomes:
            return {self._authority.change_id: self._project_change_design()}
        items = {outcome.outcome_id: self._project_outcome(outcome) for outcome in self._authority.outcomes}
        change_scope = next(
            (scope for scope in self._authority.task_plan_scopes if scope.kind == PlanScopeKind.CHANGE_ASSEMBLY),
            None,
        )
        if change_scope is not None:
            items[self._authority.change_id] = self._project_change_assembly(change_scope)
        if self._evidence.integration is not None:
            items[self._authority.change_id] = self._project_change_integration(self._evidence.integration)
        return self._apply_dependency_state(items)

    def _project_change_design(self) -> WorkItemProjection:
        briefing = self._briefings.get(self._authority.change_id)
        return WorkItemProjection(
            work_item_id=self._authority.change_id,
            change_id=self._authority.change_id,
            scope="change",
            title=self._authority.title,
            promise=self._authority.title,
            stage=WorkItemStage.DESIGN,
            attention=WorkItemAttention.USER if briefing is not None else WorkItemAttention.NONE,
            dependency_ready=False,
            next_action="Resume design",
        )

    def _project_outcome(self, outcome: Outcome) -> WorkItemProjection:
        scope = self._scopes.get(outcome.outcome_id)
        projected_scope = scope
        if outcome.status != AuthorityStatus.ACTIVE:
            stage, attention, projected_scope = WorkItemStage.COMPLETED, WorkItemAttention.NONE, None
        elif outcome.outcome_id in self._briefings:
            stage, attention, projected_scope = WorkItemStage.DESIGN, WorkItemAttention.USER, None
        elif scope is None or scope.scope_id not in self._evidence.planned_scope_ids:
            stage, attention = WorkItemStage.PLANNING, WorkItemAttention.AGENT
        else:
            progress = self._progress.get(
                scope.scope_id,
                TaskProgress(scope_id=scope.scope_id, task_count=0, reviewed_task_count=0),
            )
            if progress.reviewed_task_count < progress.task_count:
                stage, attention = WorkItemStage.IMPLEMENTATION, WorkItemAttention.AGENT
            elif scope.composition_claim and scope.scope_id not in self._evidence.completed_assembly_scope_ids:
                stage, attention = WorkItemStage.ASSEMBLY, WorkItemAttention.AGENT
            else:
                stage, attention = WorkItemStage.COMPLETED, WorkItemAttention.NONE
        if outcome.outcome_id in self._evidence.pending_request_work_item_ids and stage != WorkItemStage.COMPLETED:
            attention = WorkItemAttention.USER
        return self._projection(outcome, stage, attention, projected_scope)

    def _projection(
        self,
        outcome: Outcome,
        stage: WorkItemStage,
        attention: WorkItemAttention,
        scope: TaskPlanScope | None,
    ) -> WorkItemProjection:
        progress = self._progress.get(scope.scope_id) if scope is not None else None
        return WorkItemProjection(
            work_item_id=outcome.outcome_id,
            change_id=self._authority.change_id,
            scope="outcome",
            title=outcome.title,
            promise=outcome.promise,
            stage=stage,
            attention=attention,
            dependency_ready=attention != WorkItemAttention.USER,
            commitment_ids=outcome.commitment_ids,
            dependency_ids=outcome.dependency_ids,
            replacement_ids=outcome.superseded_by,
            task_count=progress.task_count if progress is not None else 0,
            reviewed_task_count=progress.reviewed_task_count if progress is not None else 0,
            next_action=_next_action(stage, attention),
        )

    def _project_change_assembly(self, scope: TaskPlanScope) -> WorkItemProjection:
        planned = scope.scope_id in self._evidence.planned_scope_ids
        progress = self._progress.get(scope.scope_id)
        stage = WorkItemStage.PLANNING
        if planned and progress is not None and progress.reviewed_task_count < progress.task_count:
            stage = WorkItemStage.IMPLEMENTATION
        elif planned and scope.scope_id not in self._evidence.completed_assembly_scope_ids:
            stage = WorkItemStage.ASSEMBLY
        elif planned:
            stage = WorkItemStage.COMPLETED
        return WorkItemProjection(
            work_item_id=self._authority.change_id,
            change_id=self._authority.change_id,
            scope="change-assembly",
            title=self._authority.title,
            promise=scope.composition_claim or self._authority.title,
            stage=stage,
            attention=WorkItemAttention.NONE if stage == WorkItemStage.COMPLETED else WorkItemAttention.AGENT,
            dependency_ready=True,
            task_count=progress.task_count if progress is not None else 0,
            reviewed_task_count=progress.reviewed_task_count if progress is not None else 0,
            next_action=_next_action(stage, WorkItemAttention.AGENT),
        )

    def _project_change_integration(self, state: WorkItemIntegrationState) -> WorkItemProjection:
        attention = {
            WorkItemIntegrationDisposition.READY: WorkItemAttention.AGENT,
            WorkItemIntegrationDisposition.RETRYABLE: WorkItemAttention.AGENT,
            WorkItemIntegrationDisposition.REPAIR_REQUIRED: WorkItemAttention.REPAIR,
            WorkItemIntegrationDisposition.OPERATOR_REQUIRED: WorkItemAttention.USER,
        }[state.disposition]
        next_action = {
            WorkItemIntegrationDisposition.READY: "Integrate reviewed change",
            WorkItemIntegrationDisposition.RETRYABLE: "Retry Integration",
            WorkItemIntegrationDisposition.REPAIR_REQUIRED: "Run reviewed Integration repair",
            WorkItemIntegrationDisposition.OPERATOR_REQUIRED: "Resolve Integration attention",
        }[state.disposition]
        return WorkItemProjection(
            work_item_id=self._authority.change_id,
            change_id=self._authority.change_id,
            scope="change-integration",
            title=self._authority.title,
            promise="Publish the reviewed change and completed history to the Integration target.",
            stage=WorkItemStage.COMPLETED,
            attention=attention,
            dependency_ready=True,
            next_action=next_action,
        )

    @staticmethod
    def _apply_dependency_state(items: dict[str, WorkItemProjection]) -> dict[str, WorkItemProjection]:
        result = dict(items)
        for identity, item in items.items():
            if item.stage == WorkItemStage.COMPLETED or not item.dependency_ids:
                continue
            ready = all(items[dependency].stage == WorkItemStage.COMPLETED for dependency in item.dependency_ids)
            if not ready and item.attention != WorkItemAttention.USER:
                result[identity] = item.model_copy(
                    update={
                        "attention": WorkItemAttention.WAITING,
                        "dependency_ready": False,
                        "next_action": "Inspect progress",
                    }
                )
        return result


def _next_action(stage: WorkItemStage, attention: WorkItemAttention) -> str:
    if attention == WorkItemAttention.USER:
        return "Resume design" if stage == WorkItemStage.DESIGN else "Respond to request"
    if stage == WorkItemStage.COMPLETED:
        return "View result"
    return "Inspect progress"
