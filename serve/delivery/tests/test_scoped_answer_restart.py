"""N03-A restart replay of a person-only check the user answered in Cockpit during a retained handoff.

The answer goes through the application with Cockpit's user-only permission; every restart goes through
the default loader.
"""

# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from serve.delivery.tests.test_delivery_state import (
    _acquire_planner_after_pause,
    _builder_return_restart_fixture,
    _BuilderReturnRestartFixture,
    _git,
    _healthy_restart,
    _settle_default_loader_planning_return,
)

from owlbear_delivery import (
    AdvanceDelivery,
    BlockDelivery,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryFrontier,
    DeliveryLaunchPackage,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    PortfolioApplication,
    PublishDeliveryPlan,
)
from owlbear_delivery.acceptance_criteria import acceptance_criteria
from owlbear_delivery.delivery_application_loader import load_delivery_application
from owlbear_delivery.delivery_runtime import (
    DeliveryConfirmationScope,
    DeliveryManualProcedureResult,
    DeliveryRequestResolution,
)
from owlbear_delivery.evidence import evaluate_acceptance_evidence
from owlbear_delivery.portfolio_application import DeliveryAnswer, DeliveryAnswerKind, DeliveryResultSubmission

_PROCEDURE = "manual browser check"
_STATE_BRANCH = "refs/heads/owlbear/delivery-state"


def _scoped_request(application: PortfolioApplication, change_id: str, outcome_id: str, request_id: str) -> Any:
    criteria = acceptance_criteria(application._runtimes[change_id].contract)
    return DeliveryRequest(
        request_id=request_id,
        kind=DeliveryRequestKind.DECISION,
        outcome_id=outcome_id,
        summary="Confirm the human check of the persisted state.",
        options=(
            DeliveryRequestOption(option_id="passed", label="passed"),
            DeliveryRequestOption(option_id="failed", label="failed"),
        ),
        applies_to=DeliveryConfirmationScope(
            kind="confirm-check", acceptance=tuple(item.ref for item in criteria), procedure=_PROCEDURE
        ),
    )


def _block(launch: DeliveryLaunchPackage, request: DeliveryRequest, resume_commit: str | None = None) -> BlockDelivery:
    return BlockDelivery(
        action="block",
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        block_id=f"{request.request_id}-block",
        reason="Only the user can confirm the check.",
        unblock_condition="The user answers the request in Cockpit.",
        expected_evidence=("User confirmation",),
        locators=("TASK-002",),
        request=request,
        resume_commit=resume_commit,
    )


def _answer_in_cockpit(application: PortfolioApplication, change_id: str, request_id: str) -> None:
    runtime = application._runtimes[change_id]
    application.answer(
        DeliveryAnswer(
            change_id=change_id,
            kind=DeliveryAnswerKind.REQUEST,
            request_id=request_id,
            resolution=DeliveryRequestResolution(selected_option_id="passed"),
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        ),
        allow_user_only=True,
    )


def _intent(application: PortfolioApplication, change_id: str, kind: DeliveryChangeIntentKind) -> None:
    runtime = application._runtimes[change_id]
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=kind,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            reason="Hold for review" if kind is DeliveryChangeIntentKind.DEFER else None,
        )
    )


def _defer_and_resume(restart: _BuilderReturnRestartFixture, change_id: str) -> None:
    _intent(_healthy_restart(restart), change_id, DeliveryChangeIntentKind.DEFER)
    _intent(_healthy_restart(restart), change_id, DeliveryChangeIntentKind.RESUME)


def _answered(application: PortfolioApplication, change_id: str, request_id: str) -> DeliveryRequest:
    binding = application._runtimes[change_id].show_binding("OUT-001")
    return next(item for item in binding.requests if item.request_id == request_id)


def _state_head(restart: _BuilderReturnRestartFixture) -> str:
    return _git(restart.remote, "rev-parse", _STATE_BRANCH)


def _fresh_host(restart: _BuilderReturnRestartFixture, tmp_path: Path) -> PortfolioApplication:
    host = tmp_path / "fresh-host"
    _git(tmp_path, "clone", str(restart.remote), str(host))
    _git(host, "config", "url." + str(restart.remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(host, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(host, "config", "user.name", "Delivery State Test")
    _git(host, "config", "user.email", "delivery-state@example.invalid")
    application = load_delivery_application(restart.config, workspace_root=host)
    health = application.delivery_health()
    assert health.status.value == "healthy", health.diagnostics
    return application


def _human_confirmed_submission(
    application: PortfolioApplication, change_id: str, launch: DeliveryLaunchPackage, request_id: str
) -> DeliveryResultSubmission:
    runtime = application._runtimes[change_id]
    _git(launch.worktree_path, "commit", "--allow-empty", "-m", "complete the confirmed task")
    commit = _git(launch.worktree_path, "rev-parse", "HEAD")
    task = next(item for item in runtime.show_binding(launch.outcome_id).tasks if item.task_id == launch.task_id)
    observed_at = datetime(2026, 10, 4, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=task.task_id,
            exact_commit=commit,
            observation_kind="manual-browser-check",
            procedure=_PROCEDURE,
            result=DeliveryManualProcedureResult(assessment="passed"),
            covers=tuple(item.ref for item in acceptance_criteria(runtime.contract)),
            provenance="human-confirmed",
            request_id=request_id,
            observer_or_runner_identity="user",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="task",
            exact_commit=commit,
            author_id="Builder",
            reviewer_id="build-reviewer",
            evidence=("The confirmed check covers the persisted state.",),
            reviewed_at=observed_at,
        )
    )
    return DeliveryResultSubmission(
        change_id=change_id,
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        result=DeliveryTaskResult(
            result_id="RESULT-CONFIRMED-001",
            change_id=change_id,
            authority_digest=runtime.authority_digest,
            task_id=task.task_id,
            task_digest=task.digest,
            completed_commit=commit,
            observations=(observation,),
            review=review,
        ),
    )


def _committer_identity(restart: _BuilderReturnRestartFixture) -> None:
    """Configure the fresh clone's committer; CI provides no global Git identity."""
    _git(restart.fresh, "config", "user.name", "Delivery State Test")
    _git(restart.fresh, "config", "user.email", "delivery-state@example.invalid")


def _builder_pause(
    restart: _BuilderReturnRestartFixture, change_id: str, request_id: str
) -> tuple[DeliveryRequest, Any]:
    application = restart.application
    _committer_identity(restart)
    launch = application.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.BUILDER
    (launch.worktree_path / "paused.txt").write_text("preserved Builder work\n", encoding="utf-8")
    _git(launch.worktree_path, "add", "paused.txt")
    _git(launch.worktree_path, "commit", "-m", "preserve Builder work")
    request = _scoped_request(application, change_id, launch.outcome_id, request_id)
    paused = application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            attempt_id=launch.claim.attempt_id,
            task_id=launch.task_id,
            expected_last_reviewed_commit=launch.last_reviewed_commit,
            disposition="normal-return",
            request=_block(launch, request, _git(launch.worktree_path, "rev-parse", "HEAD")),
        ),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )
    assert paused.builder_handoff_context is not None
    assert paused.builder_handoff_context.route == "same-task"
    return request, paused.tasks


def _planner_pause(
    restart: _BuilderReturnRestartFixture, change_id: str, request_id: str
) -> tuple[DeliveryRequest, Any]:
    _committer_identity(restart)
    settled = _settle_default_loader_planning_return(restart, change_id)
    assert settled.builder_handoff_context is not None
    application = _healthy_restart(restart)
    launch = application.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.PLANNER
    request = _scoped_request(application, change_id, launch.outcome_id, request_id)
    blocked = application.transition_delivery(change_id, _block(launch, request))
    assert blocked.builder_handoff_context is not None
    return request, settled.tasks


@pytest.mark.parametrize("route", ["builder", "planner"])
@pytest.mark.parametrize("lifecycle", ["none", "both"])
def test_cockpit_answer_to_a_scoped_handoff_request_survives_restart_and_restores_on_a_fresh_host(
    tmp_path: Path, route: str, lifecycle: str
) -> None:
    change_id = f"scoped-{route}-answer"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    pause = _builder_pause if route == "builder" else _planner_pause
    request, tasks = pause(restart, change_id, f"{route}-confirmation")
    if lifecycle == "both":
        _defer_and_resume(restart, change_id)
    published = _state_head(restart)

    answering = _healthy_restart(restart)
    _answer_in_cockpit(answering, change_id, request.request_id)
    answered = _answered(answering, change_id, request.request_id)
    assert answered.resolution == DeliveryRequestResolution(selected_option_id="passed")
    if lifecycle == "both":
        _defer_and_resume(restart, change_id)
    assert _state_head(restart) == published

    restarted = _healthy_restart(restart)
    assert _answered(restarted, change_id, request.request_id) == answered

    if route == "planner":
        replan = _acquire_planner_after_pause(restarted, minutes=5)
        planning = _healthy_restart(restart)
        candidate = planning.publish_delivery_plan(
            change_id,
            PublishDeliveryPlan(outcome_id=replan.outcome_id, claim_id=replan.claim.claim_id, tasks=tasks),
        )
        _healthy_restart(restart).transition_delivery(
            change_id,
            AdvanceDelivery(
                action="advance", outcome_id=replan.outcome_id, claim_id=replan.claim.claim_id, output=candidate.output
            ),
        )
    building = _healthy_restart(restart)
    launch = building.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.BUILDER
    assert launch.task_id == restart.original_task.task_id
    resumed = _healthy_restart(restart)

    submitted = resumed.submit_result(_human_confirmed_submission(resumed, change_id, launch, request.request_id))
    assert submitted is not None
    assert _state_head(restart) != published
    snapshot = json.loads(_git(restart.remote, "show", f"{_STATE_BRANCH}:{restart.remote_snapshot_path}").encode())
    assert snapshot["schema_version"] == 3

    host = _fresh_host(restart, tmp_path)
    restored = DeliveryFrontier.model_validate_json(host._runtimes[change_id].frontier_bytes(), strict=True)
    assert any(item == answered for binding in restored.bindings for item in binding.requests)
    assert any(
        result.result_id == "RESULT-CONFIRMED-001" for binding in restored.bindings for result in binding.results
    )
    coverage = evaluate_acceptance_evidence(host._runtimes[change_id].contract, restored)
    assert {item.status for item in coverage.criteria if item.outcome_id == "OUT-001"} == {"covered"}
