from __future__ import annotations

from owlbear_kanban.target_authority import (
    AuthorityStatus,
    Commitment,
    CommitmentClass,
    CompletionSummary,
    DesignReentryBriefing,
    Outcome,
    PlanScopeKind,
    SemanticUpdate,
    TargetAuthority,
    TaskPlanScope,
)
from owlbear_kanban.work_items import (
    TaskProgress,
    WorkItemAttention,
    WorkItemEvidence,
    WorkItemProjector,
    WorkItemStage,
)


def _commitments() -> tuple[Commitment, ...]:
    return (
        Commitment(
            commitment_id="COM-001",
            commitment_class=CommitmentClass.PROTECTED_REQUEST,
            provenance="user request",
            statement="Keep user attention scoped.",
        ),
        Commitment(
            commitment_id="COM-002",
            commitment_class=CommitmentClass.AGREED_PATH,
            provenance="accepted agent recommendation",
            statement="Use a dense portfolio.",
        ),
    )


def _outcome(identity: str, *, dependencies: tuple[str, ...] = ()) -> Outcome:
    return Outcome(
        outcome_id=identity,
        title=f"Outcome {identity}",
        promise=f"Promise {identity}",
        acceptance=(f"Observe {identity}",),
        commitment_ids=("COM-001",),
        dependency_ids=dependencies,
    )


def _scope(identity: str, target: str, *, composition_claim: str | None = None) -> TaskPlanScope:
    return TaskPlanScope(
        scope_id=identity,
        kind=PlanScopeKind.OUTCOME,
        target_id=target,
        composition_claim=composition_claim,
    )


def test_superseded_outcome_identity_and_replacements_remain_projectable() -> None:
    old = _outcome("OUT-001").model_copy(
        update={"status": AuthorityStatus.SUPERSEDED, "superseded_by": ("OUT-002", "OUT-003")}
    )
    authority = TargetAuthority(
        change_id="portfolio-change",
        title="Portfolio change",
        commitments=_commitments(),
        outcomes=(old, _outcome("OUT-002"), _outcome("OUT-003")),
    )

    items = {item.work_item_id: item for item in WorkItemProjector(authority, WorkItemEvidence()).list_items()}

    assert items["OUT-001"].stage == WorkItemStage.COMPLETED
    assert items["OUT-001"].replacement_ids == ("OUT-002", "OUT-003")
    assert items["OUT-002"].stage == WorkItemStage.PLANNING
    assert items["OUT-003"].stage == WorkItemStage.PLANNING


def test_planning_request_preserves_stage_and_true_dependents_wait() -> None:
    authority = TargetAuthority(
        change_id="scoped-change",
        title="Scoped change",
        commitments=_commitments(),
        outcomes=(
            _outcome("OUT-001"),
            _outcome("OUT-002"),
            _outcome("OUT-003", dependencies=("OUT-001",)),
        ),
    )
    evidence = WorkItemEvidence(pending_request_work_item_ids=("OUT-001",))

    items = {item.work_item_id: item for item in WorkItemProjector(authority, evidence).list_items()}

    assert (items["OUT-001"].stage, items["OUT-001"].attention, items["OUT-001"].next_action) == (
        WorkItemStage.PLANNING,
        WorkItemAttention.USER,
        "Respond to request",
    )
    assert (items["OUT-002"].stage, items["OUT-002"].attention, items["OUT-002"].dependency_ready) == (
        WorkItemStage.PLANNING,
        WorkItemAttention.AGENT,
        True,
    )
    assert (items["OUT-003"].attention, items["OUT-003"].dependency_ready) == (
        WorkItemAttention.WAITING,
        False,
    )


def test_implementation_request_preserves_stage_and_progress() -> None:
    authority = TargetAuthority(
        change_id="implementation-change",
        title="Implementation change",
        commitments=_commitments(),
        outcomes=(_outcome("OUT-001"),),
        task_plan_scopes=(_scope("PLAN-001", "OUT-001"),),
    )
    evidence = WorkItemEvidence(
        planned_scope_ids=("PLAN-001",),
        task_progress=(TaskProgress(scope_id="PLAN-001", task_count=2, reviewed_task_count=1),),
        pending_request_work_item_ids=("OUT-001",),
    )

    projection = WorkItemProjector(authority, evidence).show("OUT-001").projection

    assert (projection.stage, projection.attention, projection.next_action) == (
        WorkItemStage.IMPLEMENTATION,
        WorkItemAttention.USER,
        "Respond to request",
    )
    assert (projection.task_count, projection.reviewed_task_count) == (2, 1)


def test_reviewed_tasks_close_directly_or_enter_declared_assembly() -> None:
    authority = TargetAuthority(
        change_id="assembly-change",
        title="Assembly change",
        commitments=_commitments(),
        outcomes=(_outcome("OUT-001"), _outcome("OUT-002")),
        task_plan_scopes=(
            _scope("PLAN-001", "OUT-001"),
            _scope("PLAN-002", "OUT-002", composition_claim="Pieces work together."),
        ),
    )
    evidence = WorkItemEvidence(
        planned_scope_ids=("PLAN-001", "PLAN-002"),
        task_progress=(
            TaskProgress(scope_id="PLAN-001", task_count=1, reviewed_task_count=1),
            TaskProgress(scope_id="PLAN-002", task_count=2, reviewed_task_count=2),
        ),
    )

    items = {item.work_item_id: item for item in WorkItemProjector(authority, evidence).list_items()}

    assert items["OUT-001"].stage == WorkItemStage.COMPLETED
    assert items["OUT-002"].stage == WorkItemStage.ASSEMBLY


def test_semantic_updates_completion_and_design_briefing_are_read_side_records() -> None:
    briefing = DesignReentryBriefing(
        work_item_id="OUT-001",
        failed_claim="The current evidence no longer proves isolation.",
        affected_commitment_ids=("COM-001",),
        evidence=("Two changes shared one writer lock.",),
        blocked_work_item_ids=("OUT-001",),
        continuing_work_item_ids=("OUT-002",),
        resume_condition="Admit revised isolation authority.",
    )
    update = SemanticUpdate(
        update_id="UPD-001",
        work_item_id="OUT-002",
        rationale="A denser layout preserves the reviewed meaning.",
        changed_commitment_ids=("COM-002",),
    )
    summary = CompletionSummary(
        work_item_id="OUT-002",
        satisfied_commitment_ids=("COM-001",),
        accepted_deviations=("Used a merge commit for integration.",),
        known_limits=("Per-task worktrees remain deferred.",),
    )
    authority = TargetAuthority(
        change_id="briefing-change",
        title="Briefing change",
        commitments=_commitments(),
        outcomes=(_outcome("OUT-001"), _outcome("OUT-002")),
        design_reentries=(briefing,),
        semantic_updates=(update,),
        completion_summaries=(summary,),
    )
    # projectors no longer expose semantic update / completion summary queries
    projector = WorkItemProjector(authority, WorkItemEvidence())

    assert projector.show("OUT-001").briefing == briefing
    assert projector.show("OUT-001").projection.stage == WorkItemStage.DESIGN
    # persisted authority fields must contain the semantic update and completion summary
    assert tuple(item for item in authority.semantic_updates if item.work_item_id == "OUT-002") == (update,)
    assert next((item for item in authority.completion_summaries if item.work_item_id == "OUT-002"), None) == summary
