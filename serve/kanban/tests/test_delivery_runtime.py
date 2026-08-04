from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from owlbear_kanban import (
    DELIVERY_TRANSITION_ADAPTER,
    ActivateDeliveryClaim,
    AdministrativeDeliveryMove,
    AdvanceDelivery,
    BlockDelivery,
    DeliveryChangeStage,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryOutcome,
    DeliveryOutputKind,
    DeliveryOutputReference,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    OutcomeAuthorityBinding,
    PublishDeliveryOutput,
    RetryDelivery,
    ReturnDelivery,
)


def _contract() -> DeliveryContract:
    outcomes = (
        DeliveryOutcome(
            outcome_id="OUT-001",
            title="Foundation",
            promise="Deliver the foundation.",
            acceptance=("Foundation is observable.",),
            commitment_ids=(),
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
        DeliveryOutcome(
            outcome_id="OUT-003",
            title="Independent",
            promise="Deliver the independent result.",
            acceptance=("Independent result is observable.",),
            commitment_ids=(),
            dependency_ids=(),
        ),
    )
    return DeliveryContract(
        change_id="delivery-runtime",
        title="Delivery runtime",
        commitments=(),
        outcomes=outcomes,
        plan_scopes=tuple(
            DeliveryPlanScope(scope_id=f"SCOPE-{index:03}", outcome_id=outcome.outcome_id)
            for index, outcome in enumerate(outcomes, start=1)
        ),
        source_bindings=(
            {"source_name": "intent.md", "sha256": "a" * 64},
            {"source_name": "design.md", "sha256": "b" * 64},
        ),
    )


def _canonical(model: DeliveryFrontier) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _runtime(
    tmp_path: Path,
    *,
    stages: tuple[DeliveryStage, DeliveryStage, DeliveryStage] = (
        DeliveryStage.PLANNING,
        DeliveryStage.PLANNING,
        DeliveryStage.PLANNING,
    ),
    assembly_required: bool = False,
) -> DeliveryRuntime:
    frontier = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index:03}",
                plan_scope_id=f"SCOPE-{index:03}",
                stage=stage,
                assembly_required=assembly_required if index == 1 else False,
                task_ids=(f"TASK-{index:03}",) if stage not in {DeliveryStage.DESIGN, DeliveryStage.PLANNING} else (),
                result_ids=(f"RESULT-{index:03}",)
                if stage in {DeliveryStage.ASSEMBLY, DeliveryStage.COMPLETED}
                else (),
            )
            for index, stage in enumerate(stages, start=1)
        )
    )
    path = tmp_path / "delivery/changes/delivery-runtime/frontier.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(_canonical(frontier))
    return DeliveryRuntime(tmp_path, _contract())


def _output(claim_id: str, stage: DeliveryStage) -> DeliveryOutputReference:
    return DeliveryOutputReference(
        output_id=f"output-{stage.value}",
        claim_id=claim_id,
        stage=stage,
        kind=DeliveryOutputKind(stage.value),
        digest="c" * 64,
    )


def _claim_with_output(runtime: DeliveryRuntime, outcome_id: str, claim_id: str) -> DeliveryOutputReference:
    claimed = runtime.activate_claim(ActivateDeliveryClaim(outcome_id=outcome_id, claim_id=claim_id))
    output = _output(claim_id, claimed.stage)
    runtime.publish_output(PublishDeliveryOutput(outcome_id=outcome_id, claim_id=claim_id, output=output))
    return output


@pytest.mark.parametrize(
    ("stage", "transition", "expected_stage"),
    [
        (DeliveryStage.PLANNING, "advance", DeliveryStage.IMPLEMENTATION),
        (DeliveryStage.IMPLEMENTATION, "retry", DeliveryStage.IMPLEMENTATION),
        (DeliveryStage.IMPLEMENTATION, "return", DeliveryStage.PLANNING),
        (DeliveryStage.ASSEMBLY, "block", DeliveryStage.ASSEMBLY),
    ],
)
def test_worker_transition_routes_canonical_stage_and_rejects_stale_or_review_input(
    tmp_path: Path,
    stage: DeliveryStage,
    transition: str,
    expected_stage: DeliveryStage,
) -> None:
    runtime = _runtime(tmp_path, stages=(stage, DeliveryStage.PLANNING, DeliveryStage.PLANNING))
    output = _claim_with_output(runtime, "OUT-001", "claim-001")

    request = {
        "advance": AdvanceDelivery(outcome_id="OUT-001", claim_id="claim-001", output=output),
        "retry": RetryDelivery(outcome_id="OUT-001", claim_id="claim-001"),
        "return": ReturnDelivery(
            outcome_id="OUT-001",
            claim_id="claim-001",
            target=DeliveryStage.PLANNING,
            reason="The task authority needs revision.",
            locators=("TASK-001",),
        ),
        "block": BlockDelivery(
            outcome_id="OUT-001",
            claim_id="claim-001",
            block_id="block-001",
            reason="External evidence is unavailable.",
            unblock_condition="The evidence is supplied.",
            expected_evidence=("External result",),
            locators=("RESULT-001",),
        ),
    }[transition]
    result = runtime.transition(request)

    assert result.stage == expected_stage
    before = runtime.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="active claim"):
        runtime.transition(request)
    assert runtime.frontier_bytes() == before
    with pytest.raises(ValidationError):
        DELIVERY_TRANSITION_ADAPTER.validate_python(
            {
                "action": "advance",
                "outcome_id": "OUT-001",
                "claim_id": "claim-002",
                "output": _output("claim-002", expected_stage).model_dump(mode="json"),
                "reviewer_id": "reviewer-001",
                "disposition": "acceptable",
            }
        )
    assert runtime.frontier_bytes() == before


def test_implementation_advance_uses_required_output_and_assembly_signal(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.IMPLEMENTATION, DeliveryStage.PLANNING, DeliveryStage.PLANNING),
        assembly_required=True,
    )
    output = _claim_with_output(runtime, "OUT-001", "claim-001")

    with pytest.raises(DeliveryRuntimeConflictError, match="output"):
        runtime.transition(
            AdvanceDelivery(
                outcome_id="OUT-001",
                claim_id="claim-001",
                output=output.model_copy(update={"digest": "d" * 64}),
            )
        )

    assert runtime.transition(AdvanceDelivery(outcome_id="OUT-001", claim_id="claim-001", output=output)).stage == (
        DeliveryStage.ASSEMBLY
    )


def test_request_resolution_and_requestless_unblock_preserve_stage_and_answer(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.activate_claim(ActivateDeliveryClaim(outcome_id="OUT-001", claim_id="claim-001"))
    request = DeliveryRequest(
        request_id="request-001",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the bounded source.",
        options=(
            DeliveryRequestOption(option_id="local", label="Use local source"),
            DeliveryRequestOption(option_id="remote", label="Use remote source"),
        ),
    )
    runtime.transition(
        BlockDelivery(
            outcome_id="OUT-001",
            claim_id="claim-001",
            block_id="block-001",
            reason="A bounded decision is required.",
            unblock_condition="The source is selected.",
            expected_evidence=("Selected source",),
            locators=("COM-001",),
            request=request,
        )
    )

    resolved = runtime.resolve_request(
        "request-001",
        DeliveryRequestResolution(selected_option_id="local", response_text="Use the checked-in copy."),
    )

    assert resolved.resolution is not None
    assert resolved.resolution.selected_option_id == "local"
    assert resolved.resolution.response_text == "Use the checked-in copy."
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.claimable_outcome_ids() == ("OUT-001", "OUT-003")

    runtime.activate_claim(ActivateDeliveryClaim(outcome_id="OUT-003", claim_id="claim-003"))
    runtime.transition(
        BlockDelivery(
            outcome_id="OUT-003",
            claim_id="claim-003",
            block_id="block-003",
            reason="Manual verification is pending.",
            unblock_condition="Verification is recorded.",
            expected_evidence=("Verification locator",),
            locators=("RESULT-003",),
        )
    )
    runtime.unblock("OUT-003", "block-003", "Verification completed.", ("RESULT-003",))
    assert runtime.show_binding("OUT-003").stage == DeliveryStage.PLANNING
    assert "OUT-003" in runtime.claimable_outcome_ids()


def test_administrative_backward_move_invalidates_completed_dependents_only(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    assert runtime.change_stage() == DeliveryChangeStage.INTEGRATION

    result = runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-001",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="The foundation result was invalidated by operator evidence.",
        )
    )

    assert result.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-002").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-003").stage == DeliveryStage.COMPLETED
    assert runtime.show_binding("OUT-003").result_ids == ("RESULT-003",)
    assert runtime.change_stage() == DeliveryChangeStage.ACTIVE_DELIVERY
