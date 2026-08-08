from __future__ import annotations

import json

from owlbear_delivery.delivery_runtime import (
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryReturnContext,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
)
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
    WorkItemProjector,
    WorkItemStage,
    integration_conflict_paths,
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
            DeliveryTaskResult(
                result_id=f"RESULT-{index:03}",
                change_id="portfolio-change",
                authority_digest="c" * 64,
                task_id=task.task_id,
                task_digest=task.digest,
                completed_commit=f"{index}" * 40,
            ),
        )
        if stage in {DeliveryStage.ASSEMBLY, DeliveryStage.COMPLETED}
        else ()
    )
    return OutcomeAuthorityBinding(
        outcome_id=outcome_id,
        plan_scope_id=outcome_id.replace("OUT", "SCOPE"),
        stage=stage,
        assembly_required=stage == DeliveryStage.ASSEMBLY,
        tasks=tasks,
        results=results,
        active_claim=claim,
        requests=requests,
        block=block,
    )


def _snapshot(
    bindings: tuple[OutcomeAuthorityBinding, OutcomeAuthorityBinding],
    *,
    attention: DeliveryIntegrationAttention | None = None,
    repair_claim: DeliveryActiveClaim | None = None,
    target_head: str = "2" * 40,
) -> DeliveryPortfolioSnapshot:
    frontier = DeliveryFrontier(
        bindings=bindings,
        integration_attention=attention,
        integration_repair_claim=repair_claim,
    )
    content = (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    return DeliveryPortfolioSnapshot.capture(
        _contract(),
        content,
        integration_target="dev",
        target_head=target_head,
    )


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
    assert card.progress.label == "Returned to Design — re-admission required"
    detail = projector.show("OUT-001")
    assert detail.projection.attention == WorkItemAttention.USER
    assert detail.return_context == return_context
    assert projector.group_view().lifecycle == "in-delivery"


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


def test_assembly_uses_outcome_progress_and_detail_contains_result_evidence() -> None:
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.ASSEMBLY),
                _binding("OUT-002", DeliveryStage.PLANNING),
            )
        )
    )

    card = projector.group_view().items[0]
    detail = projector.show_view("outcome:OUT-001")

    assert card.progress.label == "Tasks reviewed — assembling"
    assert detail.acceptance == ("Foundation is observable.",)
    assert detail.commitments[0].statement == "Keep user attention scoped."
    assert detail.tasks[0].status == "reviewed"
    assert detail.tasks[0].completed_commit == "1" * 40


def test_target_movement_supersedes_attention_and_offers_retry() -> None:
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id="portfolio-change",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="dev",
        diagnostics=("CONFLICT (content): Merge conflict in file.py",),
        retry_condition="Admit a reviewed repair.",
    )
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.COMPLETED),
                _binding("OUT-002", DeliveryStage.COMPLETED),
            ),
            attention=attention,
            target_head="3" * 40,
        )
    )

    card = projector.group_view().items[-1]
    detail = projector.show_view("integration")

    assert card.progress.label == "Awaiting retry against current target"
    assert card.action.kind == WorkItemActionKind.RETRY_INTEGRATION
    assert (card.next_actor, card.next_step) == (
        WorkItemNextActor.AGENT_OR_YOU,
        "Retry against the current target",
    )
    assert detail.integration is not None
    assert detail.integration.superseded
    assert detail.integration.conflicted_paths == ("file.py",)
    assert detail.integration.retry_condition == (
        "Retry Integration against the current target head; the previous verdict is stale."
    )


def test_repair_activity_and_conflict_paths_use_retained_evidence() -> None:
    diagnostics = (
        "100644 " + "1" * 40 + " 1\tshare/agent.md",
        "100644 " + "2" * 40 + " 2\tshare/agent.md",
        "100644 " + "3" * 40 + " 3\tshare/agent.md",
        "CONFLICT (content): Merge conflict in share/agent.md",
    )
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id="portfolio-change",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="dev",
        diagnostics=diagnostics,
        retry_condition="Admit a reviewed repair.",
    )
    repair_claim = DeliveryActiveClaim(
        attempt_id="repair-attempt",
        claim_id="repair-claim",
        owner_id="repairer",
        process_id="repair-process",
        started_at="2026-08-08T10:00:00Z",
        worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
    )
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.COMPLETED),
                _binding("OUT-002", DeliveryStage.COMPLETED),
            ),
            attention=attention,
            repair_claim=repair_claim,
        )
    )

    card = projector.group_view().items[-1]
    detail = projector.show_view("integration")

    assert card.stage is None
    assert card.needs == WorkItemNeed.NONE
    assert card.needs_headline is None
    assert card.activity.state == WorkItemActivityState.REPAIRING
    assert card.action.kind == WorkItemActionKind.NONE
    assert detail.integration is not None
    assert detail.integration.conflicted_paths == ("share/agent.md",)
    assert integration_conflict_paths(("unparseable raw evidence",)) == ()
    assert integration_conflict_paths(("CONFLICT (content): Merge conflict in docs/a in b.md",)) == ("docs/a in b.md",)


def test_candidate_proof_failure_requires_operator_correction() -> None:
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.CANDIDATE_PROOF_FAILED,
        change_id="portfolio-change",
        change_head="1" * 40,
        target_head="2" * 40,
        integration_target="dev",
        diagnostics=("verification step timed out",),
        retry_condition="Resolve the condition, then retry.",
    )
    projector = WorkItemProjector(
        _snapshot(
            (
                _binding("OUT-001", DeliveryStage.COMPLETED),
                _binding("OUT-002", DeliveryStage.COMPLETED),
            ),
            attention=attention,
        )
    )

    card = projector.group_view().items[-1]

    assert card.needs == WorkItemNeed.YOU
    assert card.needs_headline == "Candidate verification failed"
    assert card.action.kind == WorkItemActionKind.NONE
