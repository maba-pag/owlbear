from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from owlbear_delivery.delivery_runtime import (
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryChangeDisposition,
    DeliveryChangeDispositionKind,
    DeliveryChangeAbandonment,
    DeliveryChangeDeferral,
    DeliveryChangePublicationIdentity,
    DeliveryChangeStage,
    DeliveryFrontier,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFinalization,
    DeliveryFinalizationInvalidation,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryMergedPullRequestLatch,
    DeliveryPendingCheckpoint,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOperatorMove,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryReturnContext,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.draft_pull_request import PullRequestReadyReceipt
from owlbear_delivery.change_workspace import ChangeTargetSyncReceipt
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryOutcome,
    DeliveryPlanScope,
)
from owlbear_delivery.work_items import (
    DeliveryPortfolioSnapshot,
    WorkItemActionKind,
    WorkItemActivityState,
    WorkItemAttention,
    WorkItemNeed,
    WorkItemNextActor,
    WorkItemPublicationPhase,
    WorkItemProjector,
    WorkItemStage,
)


def _contract() -> DeliveryContract:
    return DeliveryContract(
        change_id="portfolio-change",
        title="Portfolio Change",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.PROTECTED_REQUEST,
                provenance="user request",
                statement="Keep user attention scoped.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="Foundation",
                promise="Deliver the foundation.",
                acceptance=("Foundation is observable.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
            DeliveryOutcome(
                outcome_id="OUT-002",
                title="Dependent",
                promise="Deliver the dependent result.",
                acceptance=("Dependent result is observable.",),
                commitment_ids=(),
                dependency_ids=("OUT-001",),
            ),
        ),
        plan_scopes=(
            DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),
            DeliveryPlanScope(scope_id="SCOPE-002", outcome_id="OUT-002"),
        ),
        source_bindings=(
            {"source_name": "intent.md", "sha256": "a" * 64},
            {"source_name": "design.md", "sha256": "b" * 64},
        ),
    )


def _task(outcome_id: str, index: int) -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id=f"TASK-{index:03}",
        outcome_id=outcome_id,
        plan_scope_id=outcome_id.replace("OUT", "SCOPE"),
        title=f"Build {outcome_id}",
        result=f"Reviewed {outcome_id} result.",
        commitment_ids=(),
        dependency_ids=(),
        required_outputs=("Reviewed source commit",),
        maintained_surfaces=("serve/delivery/",),
        constraints=("Keep the result bounded.",),
        exclusions=("Do not change unrelated packages.",),
        acceptance_observations=(f"{outcome_id} is observable.",),
        proof_boundaries=("Focused Delivery test",),
    )


def _task_result(
    result_id: str,
    change_id: str,
    authority_digest: str,
    task: DeliveryTaskDefinition,
    completed_commit: str,
) -> DeliveryTaskResult:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=task.task_id,
            exact_commit=completed_commit,
            observation_kind="pytest",
            command_or_procedure="work-item fixture validation",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=completed_commit,
            author_id="Work item test author",
            reviewer_id="Work item test reviewer",
            evidence=("The exact fixture commit satisfies task authority.",),
            reviewed_at=observed_at,
        )
    )
    return DeliveryTaskResult(
        result_id=result_id,
        change_id=change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
        observations=(observation,),
        review=review,
    )


def _binding(
    outcome_id: str,
    stage: DeliveryStage,
    *,
    requests: tuple[DeliveryRequest, ...] = (),
    block: DeliveryBlock | None = None,
    claim: DeliveryActiveClaim | None = None,
) -> OutcomeAuthorityBinding:
    index = int(outcome_id[-3:])
    task = _task(outcome_id, index)
    tasks = () if stage in {DeliveryStage.DESIGN, DeliveryStage.PLANNING} else (task,)
    results = (
        (
            _task_result(
                f"RESULT-{index:03}",
                "portfolio-change",
                "c" * 64,
                task,
                f"{index}" * 40,
            ),
        )
        if stage == DeliveryStage.COMPLETED
        else ()
    )
    return OutcomeAuthorityBinding(
        outcome_id=outcome_id,
        plan_scope_id=outcome_id.replace("OUT", "SCOPE"),
        stage=stage,
        tasks=tasks,
        results=results,
        active_claim=claim,
        requests=requests,
        block=block,
    )


def _snapshot(
    bindings: tuple[OutcomeAuthorityBinding, OutcomeAuthorityBinding],
    *,
    operator_moves: tuple[DeliveryOperatorMove, ...] = (),
    frontier_updates: dict[str, object] | None = None,
) -> DeliveryPortfolioSnapshot:
    frontier = DeliveryFrontier(
        bindings=bindings,
        operator_moves=operator_moves,
    )
    if frontier_updates:
        frontier = frontier.model_copy(update=frontier_updates)
    content = (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    return DeliveryPortfolioSnapshot.capture(
        _contract(),
        content,
    )


def _finalization(exact_head: str = "3" * 40) -> DeliveryFinalizationReceipt:
    observed_at = datetime(2026, 8, 11, 13, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id="portfolio-change",
            task_or_finalization_id="finalize-portfolio-change",
            exact_commit=exact_head,
            observation_kind="pytest",
            command_or_procedure="work-item finalization validation",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=exact_head,
            author_id="Work item finalization author",
            reviewer_id="Work item finalization reviewer",
            evidence=("The exact Change head satisfies finalization authority.",),
            reviewed_at=observed_at,
        )
    )
    return DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            operation_id="finalize-portfolio-change",
            change_id="portfolio-change",
            exact_head=exact_head,
            authority_digest="c" * 64,
            result_digests=("d" * 64,),
            observations=(observation,),
            review=review,
            finalized_at=observed_at,
        )
    )


def _ready(finalization: DeliveryFinalizationReceipt) -> PullRequestReadyReceipt:
    values = {
        "schema_version": 1,
        "operation_id": "ready-portfolio-change",
        "change_id": "portfolio-change",
        "finalization_id": finalization.finalization_id,
        "repository": "example/project",
        "number": 42,
        "node_id": "PR_portfolio_42",
        "head_sha": finalization.exact_head,
        "draft": False,
        "observed_at": datetime(2026, 8, 11, 14, tzinfo=UTC),
        "provider_evidence_digest": "e" * 64,
    }
    candidate = PullRequestReadyReceipt.model_construct(receipt_id="0" * 64, **values)
    receipt_id = hashlib.sha256(
        json.dumps(
            candidate.model_dump(mode="json", exclude={"receipt_id"}),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return PullRequestReadyReceipt(receipt_id=receipt_id, **values)


def test_design_return_is_user_owned_and_not_projected_as_planning() -> None:
    return_context = DeliveryReturnContext(
        target=DeliveryStage.DESIGN,
        reason="The accepted design authority changed.",
        locators=("design.md",),
    )
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.DESIGN).model_copy(update={"return_context": return_context}),
                _binding("OUT-002", DeliveryStage.IMPLEMENTATION),
            )
        )
    )

    card = projector.group_view().items[0]

    assert (card.stage, card.needs, card.activity.state, card.action.kind) == (
        WorkItemStage.DESIGN,
        WorkItemNeed.YOU,
        WorkItemActivityState.IDLE,
        WorkItemActionKind.NONE,
    )
    assert card.progress.label == "Returned to Design"
    detail = projector.show("OUT-001")
    assert detail.projection.attention == WorkItemAttention.USER
    assert detail.return_context == return_context
    assert projector.group_view().lifecycle == "in-delivery"


def test_work_item_activity_contract_has_no_legacy_repair_state() -> None:
    assert set(WorkItemActivityState) == {
        WorkItemActivityState.IDLE,
        WorkItemActivityState.READY,
        WorkItemActivityState.WORKING,
    }


def test_design_return_suppresses_preserved_request_action_until_readmission() -> None:
    request = DeliveryRequest(
        request_id="REQ-001",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the retained contract.",
        options=({"option_id": "keep", "label": "Keep it"},),
    )
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.DESIGN, requests=(request,)),
                _binding("OUT-002", DeliveryStage.PLANNING),
            )
        )
    )

    card = projector.group_view().items[0]

    assert card.needs_headline == "Re-admission required"
    assert card.action.kind == WorkItemActionKind.NONE


def test_detail_exposes_operator_directed_course_changes() -> None:
    move = DeliveryOperatorMove(
        move_id="move-one",
        outcome_id="OUT-001",
        destination=DeliveryStage.PLANNING,
        reason="The accepted scope changed.",
        invalidated_outcome_ids=("OUT-001", "OUT-002"),
    )
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.PLANNING),
                _binding("OUT-002", DeliveryStage.DESIGN),
            ),
            operator_moves=(move,),
        )
    )

    detail = projector.show_view("outcome:OUT-001")

    assert detail.operator_moves == (move,)


def test_request_and_requestless_block_share_need_but_keep_distinct_actions() -> None:
    request = DeliveryRequest(
        request_id="REQ-001",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the retained contract.",
        options=({"option_id": "keep", "label": "Keep it"},),
    )
    block = DeliveryBlock(
        block_id="BLOCK-002",
        reason="Operator evidence is missing.",
        unblock_condition="Record the evidence.",
        expected_evidence=("Evidence locator",),
        locators=("OUT-002",),
    )
    cards = (
        WorkItemProjector(
            _snapshot(
                (
                    _binding("OUT-001", DeliveryStage.PLANNING, requests=(request,)),
                    _binding("OUT-002", DeliveryStage.PLANNING, block=block),
                )
            )
        )
        .group_view()
        .items
    )

    assert [(card.needs, card.action.kind) for card in cards] == [
        (WorkItemNeed.YOU, WorkItemActionKind.ANSWER_REQUEST),
        (WorkItemNeed.YOU, WorkItemActionKind.CLEAR_BLOCK),
    ]


def test_dependency_and_active_claim_are_independent_axes() -> None:
    claim = DeliveryActiveClaim(
        attempt_id="attempt-001",
        claim_id="claim-001",
        owner_id="builder",
        process_id="process-001",
        started_at="2026-08-08T10:00:00Z",
        worker_role=DeliveryWorkerRole.BUILDER,
        task_id="TASK-001",
    )
    cards = (
        WorkItemProjector(
            _snapshot(
                (
                    _binding("OUT-001", DeliveryStage.IMPLEMENTATION, claim=claim),
                    _binding("OUT-002", DeliveryStage.PLANNING),
                )
            )
        )
        .group_view()
        .items
    )

    assert cards[0].activity.state == WorkItemActivityState.WORKING
    assert cards[0].needs == WorkItemNeed.NONE
    assert (cards[0].next_actor, cards[0].next_step) == (WorkItemNextActor.AGENT, "Work in progress")
    assert (cards[1].needs, cards[1].needs_headline) == (WorkItemNeed.DEPENDENCY, "Waiting on OUT-001")
    assert cards[1].next_actor == WorkItemNextActor.DEPENDENCY


def test_completed_outcome_progress_and_detail_contain_result_evidence() -> None:
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.COMPLETED),
                _binding("OUT-002", DeliveryStage.PLANNING),
            )
        )
    )

    card = projector.group_view().items[0]
    detail = projector.show_view("outcome:OUT-001")

    assert card.progress.label == "1 of 1 Delivery tasks reviewed"
    assert detail.acceptance == ("Foundation is observable.",)
    assert detail.commitments[0].statement == "Keep user attention scoped."
    assert detail.tasks[0].status == "reviewed"
    assert detail.tasks[0].completed_commit == "1" * 40


def test_completed_outcomes_project_ready_for_finalization() -> None:
    projector = WorkItemProjector(
        _snapshot((_binding("OUT-001", DeliveryStage.COMPLETED), _binding("OUT-002", DeliveryStage.COMPLETED)))
    )

    group = projector.group_view()
    card = group.items[-1]
    detail = projector.show_view("publication")

    assert group.lifecycle == "finalization"
    assert (card.scope, card.progress.label, card.action.kind) == (
        "change-publication",
        "Ready for finalization",
        WorkItemActionKind.FINALIZE,
    )
    assert card.action.label == "Finalize Change"
    assert card.action.command == "/finalize-change portfolio-change"
    assert detail.publication is not None
    assert detail.publication.phase == WorkItemPublicationPhase.READY_FOR_FINALIZATION


def test_target_sync_receipt_projects_without_receipt_only_fields() -> None:
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-portfolio-change",
        change_id="portfolio-change",
        integration_target="main",
        expected_target="1" * 40,
        target_head="1" * 40,
        change_head_before="2" * 40,
        merged_head="3" * 40,
        merge_commit=True,
    )
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.COMPLETED), _binding("OUT-002", DeliveryStage.COMPLETED)),
            frontier_updates={"target_sync_receipt": receipt},
        )
    )

    target_sync = projector.show_view("publication").publication

    assert target_sync is not None
    assert target_sync.target_sync is not None
    assert target_sync.target_sync.model_dump() == {
        "receipt_id": receipt.receipt_id,
        "operation_id": receipt.operation_id,
        "integration_target": receipt.integration_target,
        "expected_target": receipt.expected_target,
        "target_head": receipt.target_head,
        "change_head_before": receipt.change_head_before,
        "merged_head": receipt.merged_head,
        "merge_commit": receipt.merge_commit,
    }


def test_attention_only_completed_outcomes_still_project_finalize_action() -> None:
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.EXTERNAL_ACCEPTANCE_REQUIRED,
        change_id="portfolio-change",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="main",
        diagnostics=("provider acceptance is unavailable",),
        retry_condition="observe provider acceptance",
    )
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.COMPLETED), _binding("OUT-002", DeliveryStage.COMPLETED)),
            frontier_updates={"integration_attention": attention},
        )
    )

    card = projector.group_view().items[-1]

    assert card.action.kind == WorkItemActionKind.FINALIZE
    assert card.action.label == "Finalize Change"


def test_head_drift_projects_exact_finalization_invalidation() -> None:
    finalization = _finalization()
    invalidation = DeliveryFinalizationInvalidationReceipt.create(
        DeliveryFinalizationInvalidation(
            change_id="portfolio-change",
            finalization_id=finalization.finalization_id,
            expected_head=finalization.exact_head,
            observed_head="4" * 40,
            invalidated_at=datetime(2026, 8, 11, 15, tzinfo=UTC),
        )
    )
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.COMPLETED), _binding("OUT-002", DeliveryStage.COMPLETED)),
            frontier_updates={"finalization_invalidation": invalidation},
        )
    )

    card = projector.group_view().items[-1]
    detail = projector.show_view("publication")

    assert card.progress.label == "Head drift observed"
    assert card.action.kind == WorkItemActionKind.FINALIZE
    assert card.action.label == "Re-finalize Change"
    assert card.action.command == "/finalize-change portfolio-change"
    assert detail.publication is not None
    assert detail.publication.invalidated_expected_head == finalization.exact_head
    assert detail.publication.invalidated_observed_head == "4" * 40


def test_change_attention_projects_user_resolution_before_outcomes_complete() -> None:
    attention = DeliveryChangeDisposition.create(
        kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
        change_id="portfolio-change",
        entered_from=DeliveryChangeStage.BUILDING,
        recorded_at=datetime(2026, 8, 11, 16, tzinfo=UTC),
        diagnostics=("provider unavailable",),
    )
    publication = DeliveryChangePublicationIdentity(
        change_id="portfolio-change",
        repository="example/project",
        number=42,
        node_id="PR_portfolio_42",
        head_sha="3" * 40,
    )
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.PLANNING), _binding("OUT-002", DeliveryStage.PLANNING)),
            frontier_updates={
                "change_disposition": attention,
                "change_disposition_publication": publication,
            },
        )
    )

    card = projector.group_view().items[-1]
    detail = projector.show_view("publication")

    assert (card.needs, card.next_actor, card.action.kind, card.action.attention_id) == (
        WorkItemNeed.YOU,
        WorkItemNextActor.YOU,
        WorkItemActionKind.RESOLVE_ATTENTION,
        attention.disposition_id,
    )
    assert detail.publication is not None
    assert detail.publication.attention == attention
    assert (
        detail.publication.repository,
        detail.publication.pull_request_number,
        detail.publication.pull_request_head,
    ) == (
        publication.repository,
        publication.number,
        publication.head_sha,
    )


def test_finalization_projects_checkpoint_then_pull_request_draft() -> None:
    finalization = _finalization()
    bindings = (_binding("OUT-001", DeliveryStage.COMPLETED), _binding("OUT-002", DeliveryStage.COMPLETED))
    pending = DeliveryPendingCheckpoint(
        head=finalization.exact_head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FINALIZATION),),
    )
    checkpoint = WorkItemProjector(
        _snapshot(bindings, frontier_updates={"finalization": finalization, "pending_checkpoint": pending})
    )
    draft = WorkItemProjector(
        _snapshot(bindings, frontier_updates={"finalization": finalization, "published_head": finalization.exact_head})
    )

    assert checkpoint.group_view().lifecycle == "publication"
    assert checkpoint.group_view().items[-1].action.kind == WorkItemActionKind.RECONCILE_CHECKPOINT
    assert draft.group_view().items[-1].progress.label == "Pull request is draft"
    assert draft.group_view().items[-1].action.kind == WorkItemActionKind.MARK_READY


def test_deferred_change_projects_paused_outcomes_and_resume_action() -> None:
    deferral = DeliveryChangeDeferral.create(
        change_id="portfolio-change",
        prior_stage=DeliveryChangeStage.BUILDING,
        deferred_at=datetime(2026, 8, 11, 17, tzinfo=UTC),
        reason="Wait for user review",
    )
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.IMPLEMENTATION), _binding("OUT-002", DeliveryStage.PLANNING)),
            frontier_updates={"change_deferral": deferral},
        )
    )

    group = projector.group_view()

    assert group.lifecycle == "deferred"
    assert projector.publication_phase() == WorkItemPublicationPhase.DEFERRED
    assert all(item.activity.state == WorkItemActivityState.IDLE for item in group.items[:2])
    assert all(item.next_actor == WorkItemNextActor.NONE for item in group.items[:2])
    assert group.items[-1].action.kind == WorkItemActionKind.RESUME_CHANGE
    assert group.items[-1].action.command is None


def test_abandoned_change_projects_terminal_publication_without_action() -> None:
    abandonment = DeliveryChangeAbandonment.create(
        change_id="portfolio-change",
        prior_stage=DeliveryChangeStage.BUILDING,
        abandoned_at=datetime(2026, 8, 11, 17, tzinfo=UTC),
        reason="User stopped the Change",
    )
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.IMPLEMENTATION), _binding("OUT-002", DeliveryStage.PLANNING)),
            frontier_updates={"change_abandonment": abandonment},
        )
    )

    group = projector.group_view()

    assert group.lifecycle == "abandoned"
    assert projector.publication_phase() == WorkItemPublicationPhase.ABANDONED
    assert group.items[-1].next_step == "Change abandoned"
    assert group.items[-1].action.kind == WorkItemActionKind.NONE


def test_ready_pull_request_waits_for_user_merge_without_merge_control() -> None:
    finalization = _finalization()
    ready = _ready(finalization)
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.COMPLETED), _binding("OUT-002", DeliveryStage.COMPLETED)),
            frontier_updates={
                "finalization": finalization,
                "published_head": finalization.exact_head,
                "ready": ready,
            },
        )
    )

    card = projector.group_view().items[-1]
    detail = projector.show_view("publication")

    assert projector.group_view().lifecycle == "awaiting-merge"
    assert (card.needs, card.next_actor, card.action.kind) == (
        WorkItemNeed.YOU,
        WorkItemNextActor.YOU,
        WorkItemActionKind.OBSERVE_ACCEPTANCE,
    )
    assert card.action.label == "Check GitHub acceptance"
    assert detail.publication is not None
    assert detail.publication.pull_request_number == 42


def test_merged_latch_projects_distinct_finalized_and_accepted_heads() -> None:
    finalization = _finalization()
    ready = _ready(finalization)
    merged = DeliveryMergedPullRequestLatch(
        change_id="portfolio-change",
        finalization_id=finalization.finalization_id,
        ready_receipt_id=ready.receipt_id,
        acceptance_observation_id="5" * 64,
        provider_evidence_digest="6" * 64,
        repository=ready.repository,
        number=ready.number,
        node_id=ready.node_id,
        base_branch="main",
        head_sha=finalization.exact_head,
        accepted_merge_commit="7" * 40,
        merged_at=datetime(2026, 8, 11, 16, tzinfo=UTC),
    )
    projector = WorkItemProjector(
        _snapshot(
            (_binding("OUT-001", DeliveryStage.COMPLETED), _binding("OUT-002", DeliveryStage.COMPLETED)),
            frontier_updates={
                "finalization": finalization,
                "published_head": finalization.exact_head,
                "ready": ready,
                "merged_pull_request_latch": merged,
            },
        )
    )

    detail = projector.show_view("publication")

    assert projector.group_view().lifecycle == "acceptance"
    assert detail.publication is not None
    assert detail.publication.finalized_head == finalization.exact_head
    assert detail.publication.accepted_merge_commit == "7" * 40
    assert detail.publication.finalized_head != detail.publication.accepted_merge_commit
