"""N12-C: a user grant lifts a pre-N12 exhausted Builder return to Planning (I6, I7)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from serve.delivery.tests.test_delivery_state import (
    _acquire_planner_after_pause,
    _answer_planner_return_pause,
    _builder_return_restart_fixture,
    _BuilderReturnRestartFixture,
    _change_intent,
    _exhaust_default_loader_planning_return,
    _healthy_restart,
    _planner_return_pause,
    _promote_corrected_plan,
)

from owlbear_delivery import (
    AdvanceDelivery,
    DeliveryAnswer,
    DeliveryAnswerKind,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeIntentKind,
    DeliveryFrontier,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PublishDeliveryPlan,
    RetryDelivery,
    runtime_settlement,
)
from owlbear_delivery.delivery_application_loader import load_delivery_application
from owlbear_delivery.delivery_runtime import _model_content
from owlbear_delivery.recovery import RetryStopCode
from owlbear_delivery.runtime_models import DeliveryConfirmationError
from owlbear_delivery.runtime_support import _builder_attempt_grant_receipt_path
from owlbear_delivery.work_items import WorkItemActionKind, WorkItemNextActor

_CHANGE_ID = "legacy-planning-grant"


def _legacy_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[_BuilderReturnRestartFixture, OutcomeAuthorityBinding]:
    """Settle the pre-N12 incident shape, then run the current release over it."""
    refunds = runtime_settlement._refunds_planning_return  # noqa: SLF001
    restart = _builder_return_restart_fixture(tmp_path, _CHANGE_ID)
    settled = _exhaust_default_loader_planning_return(restart, _CHANGE_ID, monkeypatch)
    monkeypatch.setattr(runtime_settlement, "_refunds_planning_return", refunds)
    return restart, settled


def _grant(application: PortfolioApplication, block_id: str, *, allow_user_only: bool = True) -> object:
    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001
    return application.answer(
        DeliveryAnswer(
            change_id=_CHANGE_ID,
            kind=DeliveryAnswerKind.GRANT_ATTEMPT,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            outcome_id="OUT-001",
            block_id=block_id,
        ),
        allow_user_only=allow_user_only,
    )


def _settle_builder_retry(application: PortfolioApplication) -> OutcomeAuthorityBinding:
    launch = application.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.BUILDER
    return application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=_CHANGE_ID,
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            attempt_id=launch.claim.attempt_id,
            task_id=launch.task_id,
            expected_last_reviewed_commit=launch.last_reviewed_commit,
            disposition="normal-return",
            request=RetryDelivery(
                action="retry",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                attempt_id=launch.claim.attempt_id,
                abandoned_commit=launch.source_head,
                failure_code="builder-failed",
            ),
        ),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )


def test_legacy_exhausted_planning_return_is_granted_once_and_continues_across_restarts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    restart, settled = _legacy_exhaustion(tmp_path, monkeypatch)
    assert settled.block is not None
    block_id = settled.block.block_id
    application = _healthy_restart(restart)
    # The live Change was Paused and Resumed before the grant; those receipts anchor on the exhausted row.
    _change_intent(application, _CHANGE_ID, DeliveryChangeIntentKind.DEFER, "Hold before the grant.")
    _change_intent(_healthy_restart(restart), _CHANGE_ID, DeliveryChangeIntentKind.RESUME)
    application = _healthy_restart(restart)
    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001

    view = application.show_work_item_view(_CHANGE_ID, "outcome:OUT-001")
    assert view.card.action.kind is WorkItemActionKind.GRANT_ATTEMPT
    assert view.readiness is not None
    assert view.readiness.reason_code == "retry-exhausted"
    assert view.readiness.next_actor is WorkItemNextActor.YOU
    before = runtime.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError):
        application.clear_block(_CHANGE_ID, "OUT-001", block_id, "Operator verified.", ("TASK-002",))
    with pytest.raises(DeliveryConfirmationError, match="only by the user in Cockpit"):
        _grant(application, block_id, allow_user_only=False)
    assert runtime.frontier_bytes() == before

    _grant(application, block_id)

    granted = runtime.show_binding("OUT-001")
    assert granted == settled.model_copy(
        update={
            "block": settled.block.model_copy(
                update={
                    "resolution_note": "The user granted one more Builder attempt.",
                    "resolution_locators": (settled.builder_handoff_context.settlement_id,),
                }
            )
        }
    )
    episode = runtime.retry_ledger().episode_for_attempt(settled.builder_handoff_context.attempt_id)
    assert episode is not None
    assert (episode.granted_attempts, episode.stop_code) == (1, None)
    assert _healthy_restart(restart)._runtimes[_CHANGE_ID].show_binding("OUT-001") == granted  # noqa: SLF001

    _promote_corrected_plan(restart, _CHANGE_ID, "Implement the clarified task")
    application = _healthy_restart(restart)
    promoted = application._runtimes[_CHANGE_ID].show_binding("OUT-001")  # noqa: SLF001
    assert promoted.stage is DeliveryStage.IMPLEMENTATION
    assert promoted.builder_handoff_context is not None
    assert promoted.builder_handoff_context.route == "same-task"

    exhausted_again = _settle_builder_retry(application)

    assert exhausted_again.block is not None
    assert exhausted_again.block.block_id.startswith("builder-attempt-limit-")
    application = _healthy_restart(restart)
    assert application.acquire_frontier_work().launch_packages == ()
    ledger = application._runtimes[_CHANGE_ID].retry_ledger()  # noqa: SLF001
    episode = ledger.episode_for_attempt(settled.builder_handoff_context.attempt_id)
    assert episode is not None
    assert (episode.total_attempts, episode.granted_attempts) == (4, 1)
    assert episode.stop_code is RetryStopCode.EXHAUSTED


@pytest.mark.parametrize("tamper", ["missing-receipt", "unresolved-block"])
def test_default_loader_refuses_a_legacy_grant_without_its_exact_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    restart, settled = _legacy_exhaustion(tmp_path, monkeypatch)
    assert settled.block is not None
    assert settled.builder_handoff_context is not None
    _grant(_healthy_restart(restart), settled.block.block_id)
    runtime_root = restart.fresh / ".owlbear/delivery/runtime"
    if tamper == "missing-receipt":
        _builder_attempt_grant_receipt_path(runtime_root, _CHANGE_ID, settled.builder_handoff_context).unlink()
    else:
        frontier_path = runtime_root / "changes" / _CHANGE_ID / "frontier.json"
        frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        frontier_path.write_bytes(_model_content(frontier.model_copy(update={"bindings": (settled,)})))

    health = load_delivery_application(restart.config, workspace_root=restart.fresh).delivery_health()

    assert health.status.value == "attention"
    assert [item.change_id for item in health.diagnostics] == [_CHANGE_ID]


@pytest.mark.parametrize("request_bearing", [True, False])
def test_planner_pause_after_a_legacy_grant_survives_restart_and_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, request_bearing: bool
) -> None:
    restart, settled = _legacy_exhaustion(tmp_path, monkeypatch)
    assert settled.block is not None
    _grant(_healthy_restart(restart), settled.block.block_id)
    application = _healthy_restart(restart)
    planner = application.acquire_frontier_work().launch_packages[0]
    assert planner.claim.worker_role is DeliveryWorkerRole.PLANNER
    pause = _planner_return_pause(planner.outcome_id, planner.claim.claim_id, request_bearing=request_bearing)
    application.transition_delivery(_CHANGE_ID, pause)
    _answer_planner_return_pause(_healthy_restart(restart), _CHANGE_ID, pause)

    answered = _healthy_restart(restart)._runtimes[_CHANGE_ID].show_binding("OUT-001")  # noqa: SLF001
    assert answered.block is not None
    assert answered.block.resolved
    assert answered.return_context == settled.return_context
    application = _healthy_restart(restart)
    planner = _acquire_planner_after_pause(application, minutes=5)
    revised = restart.original_task.model_copy(update={"title": "Implement the narrowed task"})
    candidate = application.publish_delivery_plan(
        _CHANGE_ID,
        PublishDeliveryPlan(
            outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, tasks=(restart.completed_task, revised)
        ),
    )
    _healthy_restart(restart)
    application.transition_delivery(
        _CHANGE_ID,
        AdvanceDelivery(
            action="advance", outcome_id=planner.outcome_id, claim_id=planner.claim.claim_id, output=candidate.output
        ),
    )

    promoted = _healthy_restart(restart)._runtimes[_CHANGE_ID].show_binding("OUT-001")  # noqa: SLF001
    assert promoted.stage is DeliveryStage.IMPLEMENTATION
    assert promoted.tasks[-1] == revised
    assert promoted.builder_handoff_context is not None
    assert promoted.builder_handoff_context.route == "same-task"
