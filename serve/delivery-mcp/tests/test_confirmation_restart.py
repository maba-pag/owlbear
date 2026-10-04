"""N03-A restart replay of scoped answers given during a retained handoff (section 1.7 L row, D13, I10).

Each answer goes through the assembled MCP server; every restart goes through the default loader.
"""

# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mcp_types as types
import pytest
from mcp import Client
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
    DeliveryUserConfirmation,
)
from owlbear_delivery.evidence import resolve_confirmation
from owlbear_delivery.portfolio_application import DeliveryResultSubmission
from owlbear_delivery.runtime_models import _model_content
from owlbear_delivery.runtime_receipts import (
    _DeliveryBuilderHandoffChangeIntentHead,
    _DeliveryBuilderHandoffChangeIntentReceipt,
)
from owlbear_delivery_mcp.target_server import assemble_target_server

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
        unblock_condition="The user answers the confirmation question.",
        expected_evidence=("User confirmation",),
        locators=("TASK-002",),
        request=request,
        resume_commit=resume_commit,
    )


async def _accept(application: PortfolioApplication, change_id: str, request_id: str) -> None:
    runtime = application._runtimes[change_id]
    seen: list[types.ElicitRequestParams] = []

    async def accept(_context: object, params: types.ElicitRequestParams) -> types.ElicitResult:
        seen.append(params)
        return types.ElicitResult(action="accept", content={"decision": "passed"})

    arguments = {
        "change_id": change_id,
        "request_id": request_id,
        "expected_frontier_digest": hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        "resolution": {"selected_option_id": "passed", "provenance": "user-confirmed"},
    }
    async with Client(assemble_target_server(application), elicitation_callback=accept) as client:
        result = await client.call_tool("answer", arguments)
    assert not result.is_error, result.content
    assert len(seen) == 1


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


def _ledger(application: PortfolioApplication, change_id: str) -> bytes:
    frontier = json.loads(application._runtimes[change_id].frontier_bytes())
    return json.dumps(frontier.get("confirmations"), sort_keys=True).encode()


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
    application: PortfolioApplication, change_id: str, launch: DeliveryLaunchPackage, confirmation_id: str
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
            confirmation_id=confirmation_id,
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


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["builder", "planner"])
@pytest.mark.parametrize("lifecycle", ["none", "before", "after", "both"])
async def test_scoped_handoff_answer_survives_restart_and_restores_on_a_fresh_host(
    tmp_path: Path, route: str, lifecycle: str
) -> None:
    change_id = f"scoped-{route}-answer"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    pause = _builder_pause if route == "builder" else _planner_pause
    request, tasks = pause(restart, change_id, f"{route}-confirmation")
    if lifecycle in {"before", "both"}:
        _defer_and_resume(restart, change_id)
    published = _state_head(restart)

    answering = _healthy_restart(restart)
    await _accept(answering, change_id, request.request_id)
    (confirmation,) = answering._runtimes[change_id].confirmations()
    ledger = _ledger(answering, change_id)
    if lifecycle in {"after", "both"}:
        _defer_and_resume(restart, change_id)
    assert _state_head(restart) == published

    restarted = _healthy_restart(restart)
    assert _ledger(restarted, change_id) == ledger
    resolution = restarted._runtimes[change_id].show_binding("OUT-001").requests[-1].resolution
    assert resolution is not None
    assert resolution.confirmation_id == confirmation.confirmation_id

    if route == "planner":
        replan = _acquire_planner_after_pause(restarted, minutes=5)
        assert _ledger(_healthy_restart(restart), change_id) == ledger
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
    assert _ledger(resumed, change_id) == ledger

    submitted = resumed.submit_result(
        _human_confirmed_submission(resumed, change_id, launch, confirmation.confirmation_id)
    )
    assert submitted is not None
    assert _state_head(restart) != published
    snapshot = json.loads(_git(restart.remote, "show", f"{_STATE_BRANCH}:{restart.remote_snapshot_path}").encode())
    assert snapshot["schema_version"] == 3
    assert json.dumps(snapshot["frontier"]["confirmations"], sort_keys=True).encode() == ledger

    host = _fresh_host(restart, tmp_path)
    assert _ledger(host, change_id) == ledger
    restored = DeliveryFrontier.model_validate_json(host._runtimes[change_id].frontier_bytes(), strict=True)
    assert resolve_confirmation(restored, confirmation.confirmation_id) == confirmation
    assert any(
        result.result_id == "RESULT-CONFIRMED-001" for binding in restored.bindings for result in binding.results
    )


def _runtime_root(restart: _BuilderReturnRestartFixture) -> Path:
    return restart.fresh / ".owlbear/delivery/runtime"


def _change_files(restart: _BuilderReturnRestartFixture, change_id: str) -> dict[str, bytes]:
    root = _runtime_root(restart) / "changes" / change_id
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*.json"))}


def _rewrite_ledger(restart: _BuilderReturnRestartFixture, change_id: str, edit: Any) -> None:
    path = _runtime_root(restart) / "changes" / change_id / "frontier.json"
    frontier = json.loads(path.read_bytes())
    entries = edit(list(frontier["confirmations"]))
    if entries:
        frontier["confirmations"] = entries
    else:
        frontier.pop("confirmations")
    path.write_bytes((json.dumps(frontier, sort_keys=True, separators=(",", ":")) + "\n").encode())


def _unbound_entry(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bound = DeliveryUserConfirmation.model_validate_json(json.dumps(entries[-1]), strict=True)
    unbound = DeliveryUserConfirmation.create(
        change_id=bound.change_id,
        request=DeliveryRequest(
            request_id="never-asked",
            kind=DeliveryRequestKind.DECISION,
            outcome_id=bound.outcome_id,
            summary="A question no receipt binds.",
            options=(
                DeliveryRequestOption(option_id="passed", label="passed"),
                DeliveryRequestOption(option_id="failed", label="failed"),
            ),
            applies_to=bound.scope,
        ),
        decision=bound.decision,
        question_digest=bound.question_digest,
        generation_id="e" * 64,
        confirmed_at=bound.confirmed_at,
    )
    return [*entries, unbound.model_dump(mode="json")]


def _altered_entry(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entry = dict(entries[-1])
    digest = entry["question_digest"]
    entry["question_digest"] = ("0" if digest[0] != "0" else "1") + digest[1:]
    return [*entries[:-1], entry]


def _schema_one_receipt(restart: _BuilderReturnRestartFixture, change_id: str) -> None:
    root = _runtime_root(restart) / "changes" / change_id
    (path,) = (item for item in root.rglob("*.json") if "request-resolution" in item.parent.name)
    receipt = json.loads(path.read_bytes())
    receipt["schema_version"] = 1
    receipt.pop("confirmation")
    path.write_bytes((json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode())


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["builder", "planner"])
@pytest.mark.parametrize("tamper", ["unbound-entry", "missing-entry", "altered-entry", "schema-1-receipt"])
async def test_tampered_scoped_answer_replay_leaves_the_change_unavailable_and_unrehashed(
    tmp_path: Path, route: str, tamper: str
) -> None:
    change_id = f"tampered-{route}-answer"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    request, _tasks = (_builder_pause if route == "builder" else _planner_pause)(
        restart, change_id, f"{route}-confirmation"
    )
    await _accept(_healthy_restart(restart), change_id, request.request_id)
    assert len(_healthy_restart(restart)._runtimes[change_id].confirmations()) == 1
    if tamper == "unbound-entry":
        _rewrite_ledger(restart, change_id, _unbound_entry)
    elif tamper == "missing-entry":
        _rewrite_ledger(restart, change_id, lambda _entries: [])
    elif tamper == "altered-entry":
        _rewrite_ledger(restart, change_id, _altered_entry)
    else:
        _schema_one_receipt(restart, change_id)
    tampered = _change_files(restart, change_id)

    application = load_delivery_application(restart.config, workspace_root=restart.fresh)
    health = application.delivery_health()

    assert health.status.value == "attention"
    assert any(
        item.change_id == change_id and item.code == "remote-state-reconciliation-required"
        for item in health.diagnostics
    ), health.diagnostics
    assert application.acquire_frontier_work().launch_packages == ()
    assert _change_files(restart, change_id) == tampered


@pytest.mark.asyncio
async def test_two_scoped_planner_answers_replay_in_answer_order_and_a_reordered_ledger_is_refused(
    tmp_path: Path,
) -> None:
    change_id = "two-planner-answers"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    first, _tasks = _planner_pause(restart, change_id, "first-confirmation")
    await _accept(_healthy_restart(restart), change_id, first.request_id)
    planning = _healthy_restart(restart)
    launch = _acquire_planner_after_pause(planning, minutes=5)
    second = _scoped_request(planning, change_id, launch.outcome_id, "second-confirmation")
    planning.transition_delivery(change_id, _block(launch, second))
    await _accept(_healthy_restart(restart), change_id, second.request_id)

    restarted = _healthy_restart(restart)
    entries = restarted._runtimes[change_id].confirmations()
    assert [entry.request_id for entry in entries] == ["first-confirmation", "second-confirmation"]

    _rewrite_ledger(restart, change_id, lambda items: list(reversed(items)))
    tampered = _change_files(restart, change_id)
    health = load_delivery_application(restart.config, workspace_root=restart.fresh).delivery_health()

    assert health.status.value == "attention"
    assert any(
        item.change_id == change_id and item.code == "remote-state-reconciliation-required"
        for item in health.diagnostics
    ), health.diagnostics
    assert _change_files(restart, change_id) == tampered


def _rebuild_lifecycle_chain(
    restart: _BuilderReturnRestartFixture, change_id: str, entry: DeliveryUserConfirmation | None
) -> None:
    """Re-create every lifecycle receipt with valid identities, adding ``entry`` to both frontiers of each."""
    root = _runtime_root(restart) / "changes" / change_id / "builder-handoff-change-intent-receipts"
    (directory,) = root.iterdir()
    receipts = sorted(
        (
            _DeliveryBuilderHandoffChangeIntentReceipt.model_validate_json(path.read_bytes(), strict=True)
            for path in directory.glob("*.json")
            if path.name != "head.json"
        ),
        key=lambda item: item.sequence,
    )

    def anchored(frontier: DeliveryFrontier) -> DeliveryFrontier:
        return frontier if entry is None else frontier.model_copy(update={"confirmations": (entry,)})

    previous: str | None = None
    for receipt in receipts:
        rebuilt = _DeliveryBuilderHandoffChangeIntentReceipt.create(
            action=receipt.action,
            change_id=receipt.change_id,
            outcome_id=receipt.outcome_id,
            context=receipt.builder_handoff_context,
            sequence=receipt.sequence,
            previous_receipt_id=previous,
            before_frontier=anchored(receipt.before_frontier),
            after_frontier=anchored(receipt.after_frontier),
            deferral=receipt.deferral,
            abandonment=receipt.abandonment,
        )
        (directory / f"{receipt.receipt_id}.json").unlink()
        (directory / f"{rebuilt.receipt_id}.json").write_bytes(_model_content(rebuilt))
        previous = rebuilt.receipt_id
    head_path = directory / "head.json"
    head = _DeliveryBuilderHandoffChangeIntentHead.model_validate_json(head_path.read_bytes(), strict=True)
    head_path.write_bytes(_model_content(head.model_copy(update={"latest_receipt_id": previous})))


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["builder", "planner"])
async def test_lifecycle_receipts_anchored_before_the_answer_that_hold_its_entry_leave_the_change_unavailable(
    tmp_path: Path, route: str
) -> None:
    change_id = f"anchored-{route}-answer"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    request, _tasks = (_builder_pause if route == "builder" else _planner_pause)(
        restart, change_id, f"{route}-confirmation"
    )
    _defer_and_resume(restart, change_id)
    await _accept(_healthy_restart(restart), change_id, request.request_id)
    (entry,) = _healthy_restart(restart)._runtimes[change_id].confirmations()
    answered = _change_files(restart, change_id)
    assert sum("builder-handoff-change-intent-receipts" in name for name in answered) == 3

    # Control: the same rebuild without the entry reproduces every receipt byte for byte.
    _rebuild_lifecycle_chain(restart, change_id, None)
    assert _change_files(restart, change_id) == answered
    _rebuild_lifecycle_chain(restart, change_id, entry)
    tampered = _change_files(restart, change_id)
    assert tampered != answered

    application = load_delivery_application(restart.config, workspace_root=restart.fresh)
    health = application.delivery_health()

    assert health.status.value == "attention"
    assert any(
        item.change_id == change_id and item.code == "remote-state-reconciliation-required"
        for item in health.diagnostics
    ), health.diagnostics
    assert application.acquire_frontier_work().launch_packages == ()
    assert _change_files(restart, change_id) == tampered
