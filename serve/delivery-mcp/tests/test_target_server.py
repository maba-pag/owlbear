"""Contract tests for the live Delivery MCPServer assembly and startup."""

from __future__ import annotations

import asyncio
import builtins
import hashlib
import io
import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest
from mcp import Client
from pydantic import BaseModel, ConfigDict, ValidationError
from serve.delivery.tests.confirmation_support import (
    EVIDENCE_STATUSES,
    WAIVER_REQUEST_ID,
    evidence_projection_case,
    extra_waiver_ids,
)
from serve.delivery.tests.test_delivery_progress import _complete_first_outcome, _progress_portfolio
from serve.delivery.tests.test_portfolio_application import (
    _FIRST_BUILDER_RETRY_REASON,
    _THIRD_BUILDER_RETRY_REASON,
    _assert_checkpoint_branch_operation,
    _assert_loader_observation_only,
    _assert_loader_retry_recording,
    _awaiting_acceptance_fixture,
    _builder_retry_handoff_setup,
    _canonical,
    _continuation_request,
    _engine_action,
    _exhaust_builder_retry_with_distinct_codes,
    _failure_request,
    _loader_activation_state_snapshot,
    _loader_composed_engine_fixture,
    _loader_engine_state_snapshot,
    _loader_registered_engine_action_fixture,
    _make_provider_readback_unavailable,
    _portfolio,
    _seed_loader_composed_completed_change,
    _startup_config,
    _workspace_content_snapshot,
    _workspace_mutation_snapshot,
    acceptance_budget_case,
)
from serve.delivery.tests.test_recovery import (
    absent_host_process_case,
    completed_recovery_restart_case,
    recovery_case,
    recovery_effect_snapshot,
    recovery_journal_snapshot,
)
from serve.delivery.tests.test_worker_stall import _HOST as _PROGRESS_HOST
from serve.delivery.tests.test_worker_stall import _iso as _progress_iso
from serve.delivery.tests.test_worker_stall import _real_now as _progress_now

import owlbear_delivery_mcp.__main__ as live_main
import owlbear_delivery_mcp.server as live_server
from owlbear_delivery import (
    AdministrativeDeliveryMove,
    ChangeContinuationAction,
    ChangeCoordination,
    DeliveryAdmissionReceipt,
    DeliveryAnswerKind,
    DeliveryBuilderInvocationSettlement,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContinuationRequest,
    DeliveryContinuationResult,
    DeliveryContract,
    DeliveryEngineActionResult,
    DeliveryFrontier,
    DeliveryOutcome,
    DeliveryPlanningRetrySettlement,
    DeliveryPlanScope,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    DeliverySourceBinding,
    DeliveryStage,
    DesignPackageStore,
    ExecuteDeliveryChangeAction,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    RetryDelivery,
    WindowHostIdentity,
)
from owlbear_delivery.application_support import _checkpoint_summary
from owlbear_delivery.change_workspace import ChangeTargetSyncReceipt
from owlbear_delivery.delivery_application_loader import (
    DeliveryStateVersionError,
)
from owlbear_delivery.delivery_application_loader import (
    load_delivery_application as load_core_delivery_application,
)
from owlbear_delivery.delivery_contract_discovery import contract_fingerprint
from owlbear_delivery.delivery_runtime import (
    BlockDelivery,
    DeliveryCommandResult,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryResultCandidate,
    DeliveryReview,
    DeliveryReviewReceipt,
    PublishDeliveryResult,
)
from owlbear_delivery.finalization_reports import FinalizationFailureCode, FinalizationReportStore
from owlbear_delivery.portfolio_operating import DeliveryHealthStatus, DeliveryHealthView
from owlbear_delivery.recovery import DeliveryWorkerExclusionRequiredError
from owlbear_delivery.state_formats import format_marker_bytes
from owlbear_delivery.storage_io import ControllerFencedError, acquire_controller_lock, locked_roots
from owlbear_delivery.work_items import WorkItemNextActor
from owlbear_delivery_github import GitHubCliPublicationProvider
from owlbear_delivery_mcp.server import (
    app_lifespan,
    load_delivery_application,
    load_delivery_config,
    mcp,
)
from owlbear_delivery_mcp.target_models import AnswerParams, DeliveryStartupDiagnostic
from owlbear_delivery_mcp.target_server import TargetMCPAdapter, assemble_target_server


@pytest.mark.asyncio
async def test_registered_direct_mark_ready_lost_to_pause_is_a_typed_no_effect_refusal(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    finalization = runtime.finalization()
    async with Client(assemble_target_server(application)) as client:
        # The busy checkpoint lock keeps K1 from converting, so the request itself refuses the direct start.
        with locked_roots((application._checkpoint_lock_root("change-a"),)):  # noqa: SLF001
            requested = await client.call_tool(
                "set_change_intent",
                {
                    "change_id": "change-a",
                    "kind": "defer",
                    "expected_frontier_digest": hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                    "reason": "Hold for review",
                },
            )
        provider.reset_mock()
        before = runtime.frontier_bytes()
        refused = await client.call_tool(
            "mark_change_ready",
            {
                "change_id": "change-a",
                "operation_id": "ready-under-pause",
                "finalization_id": finalization.finalization_id,
                "exact_head": exact_head,
            },
        )

    assert not requested.is_error
    assert requested.structured_content["receipt"]["reason"] == "Hold for review"
    assert "deferral_id" not in requested.structured_content["receipt"]
    assert refused.is_error
    diagnostic = _registered_diagnostic(refused)
    assert diagnostic["code"] == "ERR_DELIVERY_CHANGE_PAUSE_REQUESTED"
    assert diagnostic["detail"] == "Change pause requested"
    assert diagnostic["retry_safe"] is True
    assert not list((state_root / "changes/change-a/action-receipts").glob("direct-*"))
    provider.observe_checks.assert_not_called()
    provider.set_pull_request_draft_state.assert_not_called()
    assert runtime.frontier_bytes() == before
    assert runtime.ready_receipt() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("exhausted", [False, True])
async def test_registered_explicit_acceptance_reads_once_per_invocation(tmp_path: Path, *, exhausted: bool) -> None:
    application, provider, ledger, restart = acceptance_budget_case(tmp_path, exhausted=exhausted)
    calls = provider.read_pull_request.call_count
    async with Client(assemble_target_server(application)) as client:
        first = await client.call_tool("observe_acceptance", {"change_id": "change-a"})
    async with Client(assemble_target_server(restart())) as client:
        second = await client.call_tool("observe_acceptance", {"change_id": "change-a"})
    assert first.is_error
    assert second.is_error
    assert "ERR_DELIVERY_ACCEPTANCE_WAITING" in first.content[0].text
    assert ("still open and unmerged" if exhausted else "retry-backoff") in second.content[0].text
    assert provider.read_pull_request.call_count == calls + 2 * int(exhausted)
    episode = ledger.read().episodes[0]
    assert (episode.total_attempts, episode.explicit_observations, episode.reset_count) == (
        (3, 2, 0) if exhausted else (1, 0, 0)
    )


@pytest.mark.asyncio
async def test_registered_get_change_exposes_exhausted_builder_retry_history(tmp_path: Path) -> None:
    application, runtime, _contexts = _exhaust_builder_retry_with_distinct_codes(tmp_path)
    ledger_before = runtime.retry_ledger().read()

    async with Client(assemble_target_server(application)) as client:
        result = await client.call_tool("get_change", {"change_id": "change-a"})

    assert not result.is_error
    payload = result.structured_content
    assert payload is not None
    exhausted = next(item for item in payload["unresolved_outcomes"] if item["outcome_id"] == "OUT-001")
    readiness = exhausted["card"]["readiness"]
    assert readiness["reason_code"] == "retry-exhausted"
    assert readiness["next_actor"] == "you"
    assert exhausted["card"]["action"]["kind"] == "grant-attempt"
    assert readiness["retry_history"] == [
        {
            "ordinal": 1,
            "kind": "original",
            "status": "failed",
            "failure_code": "builder-failed",
            "observed_at": "2026-08-04T00:00:00Z",
            "reason": _FIRST_BUILDER_RETRY_REASON,
        },
        {
            "ordinal": 2,
            "kind": "repair",
            "status": "failed",
            "failure_code": "worker-timeout",
            "observed_at": "2026-08-04T01:00:00Z",
        },
        {
            "ordinal": 3,
            "kind": "repair",
            "status": "failed",
            "failure_code": "builder-review-failed",
            "observed_at": "2026-08-04T02:00:00Z",
            "reason": _THIRD_BUILDER_RETRY_REASON,
        },
    ]
    assert runtime.retry_ledger().read() == ledger_before


@pytest.mark.asyncio
async def test_registered_answer_refuses_the_user_only_attempt_grant(tmp_path: Path) -> None:
    application, runtime, _contexts = _exhaust_builder_retry_with_distinct_codes(tmp_path)
    block = runtime.show_binding("OUT-001").block
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()

    async with Client(assemble_target_server(application)) as client:
        result = await client.call_tool(
            "answer",
            {
                "change_id": "change-a",
                "kind": "grant-attempt",
                "expected_frontier_digest": hashlib.sha256(frontier_before).hexdigest(),
                "outcome_id": "OUT-001",
                "block_id": block.block_id,
            },
        )
        episode_grant = await client.call_tool(
            "answer",
            {
                "change_id": "change-a",
                "kind": "grant-attempt",
                "expected_frontier_digest": hashlib.sha256(frontier_before).hexdigest(),
                "attempt_id": ledger_before.episodes[0].attempt_ids[-1],
            },
        )

    assert result.is_error
    assert "ERR_TARGET_PARAM_VALIDATION" in result.content[0].text
    assert episode_grant.is_error
    assert "ERR_TARGET_PARAM_VALIDATION" in episode_grant.content[0].text
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    with pytest.raises(ValidationError, match="granted only by the user in Cockpit"):
        AnswerParams(
            change_id="change-a",
            kind=DeliveryAnswerKind.GRANT_ATTEMPT,
            expected_frontier_digest=hashlib.sha256(frontier_before).hexdigest(),
            outcome_id="OUT-001",
            block_id=block.block_id,
        )


def _evidence_statuses(projection: dict[str, Any]) -> dict[str, str]:
    return {item["acceptance_id"]: item["status"] for item in projection["criteria"]}


@pytest.mark.asyncio
async def test_registered_evidence_projection_agrees_across_reads_and_names_waivers(tmp_path: Path) -> None:
    application, runtime, state_root = evidence_projection_case(tmp_path)

    def state_tree() -> dict[str, bytes]:
        return {str(path): path.read_bytes() for path in sorted(state_root.rglob("*")) if path.is_file()}

    before = state_tree()
    change = application.get_change("change-a")
    async with Client(assemble_target_server(application)) as client:
        registered = (await client.call_tool("get_change", {"change_id": "change-a"})).structured_content
        context = await client.call_tool("show_operator_context", {"change_id": "change-a", "outcome_id": "OUT-001"})
    summary = _checkpoint_summary(runtime, SimpleNamespace(intent_bytes=b""), None, "1" * 40, ())

    assert state_tree() == before
    assert change.evidence is not None
    assert _evidence_statuses(change.evidence.model_dump(mode="json")) == EVIDENCE_STATUSES
    assert registered["evidence"] == change.evidence.model_dump(mode="json")
    assert not context.is_error
    outcome = context.structured_content["evidence"]
    assert _evidence_statuses(outcome) == {key: value for key, value in EVIDENCE_STATUSES.items() if key != "AC-005"}
    missing = next(item for item in outcome["criteria"] if item["acceptance_id"] == "AC-002")
    assert (missing["evidence"][0]["verdict"], missing["evidence"][0]["owner"]) == ("missing", "assisted-check")
    assert f"Waived by the user, `AC-003`: The launch has a manual sign-off. (request {WAIVER_REQUEST_ID})" in summary
    assert "`AC-001`" not in summary
    (tmp_path / "many").mkdir()
    _application, many_runtime, _state_root = evidence_projection_case(tmp_path / "many", waived_count=25)
    many = _checkpoint_summary(many_runtime, SimpleNamespace(intent_bytes=b""), None, "1" * 40, ())
    assert all(f"`{item}`" in many for item in ("AC-003", *extra_waiver_ids(24)))
    assert f"`{extra_waiver_ids(24)[-1]}` (request {WAIVER_REQUEST_ID})" in many
    assert "omitted" not in many


@pytest.mark.asyncio
async def test_registered_change_reads_carry_progress_and_change_activity(tmp_path: Path) -> None:
    now = [_progress_iso(_progress_now())]
    application, runtimes, _coordinator, state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, now, include_independent=True
    )
    _complete_first_outcome(application, runtimes["change-a"], state_root)

    async with Client(assemble_target_server(application)) as client:
        ready = (await client.call_tool("get_change", {"change_id": "change-a"})).structured_content
        assert application.acquire_change_action(_continuation_request(application)).launch is not None
        probe.states[_PROGRESS_HOST] = "unknown"
        held = (await client.call_tool("get_change", {"change_id": "change-a"})).structured_content
        listed = (await client.call_tool("list_changes", {})).structured_content

    assert "progress" in ready["readiness"]
    assert "change_progress" in ready["detail"]
    assert ready["detail"]["card"]["work_item_id"] == "OUT-001"
    assert ready["detail"]["card"]["readiness"]["progress"]["situation"] == "done"
    assert ready["detail"]["change_progress"]["situation"] == "ready-for-next-step"
    assert (ready["detail"]["pause_available"], ready["detail"]["pause_unavailable_reason"]) == (True, None)
    assert held["detail"]["change_progress"]["situation"] == "needs-attention"
    # N09-A2: Pause is admissible under custody; the request drains the running step first.
    assert (held["detail"]["pause_available"], held["detail"]["pause_unavailable_reason"]) == (True, None)
    held_card = next(item for item in held["unresolved_outcomes"] if item["outcome_id"] == "OUT-002")["card"]
    assert (held_card["readiness"]["progress"]["situation"], held_card["next_step"]) == (
        "needs-attention",
        "Claimed by Builder",
    )
    (group,) = listed["groups"]
    assert group["progress"]["situation"] == "needs-attention"
    assert (group["pause_available"], group["pause_unavailable_reason"]) == (True, None)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["planner", "builder", "integration", "proposal"])
async def test_registered_recovery_exclusion_required(tmp_path: Path, kind: str) -> None:
    application, operation, request, unchanged = recovery_case(tmp_path, kind)
    async with Client(assemble_target_server(application)) as client:
        diagnosis = await client.call_tool("repair", {"change_id": "change-a"})
        assert not diagnosis.is_error
        result = await client.call_tool(operation, request)
    assert result.is_error
    _prefix, marker, content = result.content[0].text.partition("{")
    assert marker, result.content[0].text
    diagnostic = json.loads(marker + content)
    assert diagnostic["code"] == DeliveryWorkerExclusionRequiredError.code
    assert diagnostic["retry_safe"] is False
    assert diagnostic["current_authority_identity"] == "change-a"
    assert "Custody and files are unchanged" in diagnostic["detail"]
    unchanged()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["claim", "proposal"])
async def test_registered_verified_completed_recovery_replay(tmp_path: Path, kind: str) -> None:
    application, operation, request, unchanged, host = completed_recovery_restart_case(tmp_path, kind)
    journals = recovery_journal_snapshot(application, "change-a")
    verifications = host.verifications
    async with Client(assemble_target_server(application)) as client:
        first_read = await client.call_tool("get_change", {"change_id": "change-a"})
        repeated_read = await client.call_tool("get_change", {"change_id": "change-a"})
        assert not first_read.is_error
        assert first_read.structured_content == repeated_read.structured_content
        assert recovery_journal_snapshot(application, "change-a") == journals
        assert host.verifications == verifications
        first_replay = await client.call_tool(operation, request)
        second_replay = await client.call_tool(operation, request)
    assert not first_replay.is_error
    assert not second_replay.is_error
    first_payload = json.loads(first_replay.content[0].text)
    second_payload = json.loads(second_replay.content[0].text)
    assert first_payload == second_payload
    recovered = first_payload["recovery"] if kind == "proposal" else first_payload
    assert recovered["status"] == "recovered"
    assert host.verifications == verifications + 2
    assert recovery_journal_snapshot(application, "change-a") == journals
    unchanged()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["claim", "proposal"])
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("preservation_paths", ["../../outside"]),
        ("commands", ["terminate-worker"]),
        ("budget", {"attempts": 999}),
        ("effect_receipt", {"verified": True}),
        ("stop_assertion", {"all_descendants_stopped": True}),
    ],
)
async def test_registered_recovery_rejects_caller_authored_evidence_fields(
    tmp_path: Path,
    kind: str,
    field: str,
    value: object,
) -> None:
    application, operation, request, unchanged, host = completed_recovery_restart_case(tmp_path, kind)
    before = recovery_effect_snapshot(application)
    verifications = host.verifications
    forged = {**request, field: value}
    async with Client(assemble_target_server(application)) as client:
        result = await client.call_tool(operation, forged)
    assert result.is_error
    diagnostic = {
        "code": "ERR_TARGET_PARAM_VALIDATION",
        "detail": "Invalid tool arguments. Check the tool input schema.",
        "current_authority_identity": "portfolio",
        "retry_safe": False,
    }
    assert len(result.content) == 1
    assert result.content[0].text == (
        f"Error executing tool {operation}: " + json.dumps(diagnostic, separators=(",", ":"))
    )
    assert result.structured_content is None
    assert host.verifications == verifications
    assert recovery_effect_snapshot(application) == before
    unchanged()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["claim", "proposal"])
async def test_registered_recovery_rejects_stale_claim_or_proposal_identity(
    tmp_path: Path,
    kind: str,
) -> None:
    application, operation, request, unchanged = recovery_case(tmp_path, kind)
    stale = dict(request)
    if kind == "proposal":
        stale["proposal_id"] = "0" * 64
    else:
        stale["attempt_id"] = "stale-attempt"
    async with Client(assemble_target_server(application)) as client:
        result = await client.call_tool(operation, stale)
    assert result.is_error
    unchanged()


@pytest.mark.asyncio
async def test_registered_absent_host_still_writing_descendant_stays_contained_across_restarts(
    tmp_path: Path,
) -> None:
    application, host, _worker, launch, restart, snapshot, signal = absent_host_process_case(tmp_path)

    async def assert_contained(candidate) -> tuple[object, ...]:
        before = snapshot(candidate)
        async with Client(assemble_target_server(candidate)) as client:
            first = await client.call_tool("get_change", {"change_id": "change-a"})
            repeated = await client.call_tool("get_change", {"change_id": "change-a"})
            assert not first.is_error
            assert first.structured_content == repeated.structured_content
            assert first.structured_content is not None
            readiness = first.structured_content["readiness"]
            assert readiness["executable"] is False
            diagnosis = await client.call_tool("repair", {"change_id": "change-a"})
            assert not diagnosis.is_error
            assert diagnosis.structured_content is not None
            proposal = diagnosis.structured_content["proposal"]
            assert proposal is not None
            assert "contained pending verified owner evidence" in proposal["summary"]
            assert "Custody and files remain unchanged" in proposal["consequence"]
            refusal = await client.call_tool(
                "repair",
                {"change_id": "change-a", "proposal_id": proposal["proposal_id"]},
            )
            assert refusal.is_error
            assert DeliveryWorkerExclusionRequiredError.code in refusal.content[0].text
            assert "Custody and files are unchanged" in refusal.content[0].text
            claim_refusal = await client.call_tool(
                "recover_claim",
                {
                    "change_id": "change-a",
                    "outcome_id": "OUT-001",
                    "attempt_id": launch.claim.attempt_id,
                    "claim_id": launch.claim.claim_id,
                    "confirmed_lost": True,
                },
            )
            assert claim_refusal.is_error
            assert DeliveryWorkerExclusionRequiredError.code in claim_refusal.content[0].text
            acquired = await client.call_tool(
                "acquire_change_action",
                {
                    "change_id": "change-a",
                    "expected_basis": readiness["basis"],
                    "capabilities": ["builder"],
                    "host_id": "synthetic-host",
                    "session_id": "absent-host-recovery",
                },
            )
            assert not acquired.is_error
            assert acquired.structured_content is not None
            assert acquired.structured_content["kind"] == "unsupported"
            assert acquired.structured_content["reason_code"] == "repair-required"
            assert acquired.structured_content["readiness"]["reason_code"] == "active-custody"
            assert acquired.structured_content["engine_action"] is None
        assert host.verifications == 0
        assert launch.claim.claim_id not in host.closed
        assert snapshot(candidate) == before
        return before

    try:
        first_snapshot = await assert_contained(application)
        signal("write-next", b"late old write after restart\n")
        after_signaled_write = snapshot(application)
        assert after_signaled_write[:3] == first_snapshot[:3]
        assert after_signaled_write[3] != first_snapshot[3]
        assert after_signaled_write[4:] == first_snapshot[4:]
        restarted = restart()
        assert snapshot(restarted) == after_signaled_write
        await assert_contained(restarted)
    finally:
        host.close(launch.claim.claim_id)


@pytest.mark.asyncio
async def test_registered_default_loader_replays_engine_action(tmp_path: Path) -> None:
    """The registered boundary executes and replays a loader-composed engine action."""
    repository_root, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    async with Client(assemble_target_server(application)) as client:
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
        assert not acquired.is_error
        assert acquired.structured_content is not None
        action = acquired.structured_content["engine_action"]
        executed = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action["operation_id"]},
        )
        replayed = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action["operation_id"]},
        )
    runtime = application._runtimes["change-a"]  # noqa: SLF001
    workspace_before_restart = _workspace_mutation_snapshot(
        application._coordinator.show("change-a").worktree_path  # noqa: SLF001
    )
    frontier_before_restart = runtime.frontier_bytes()
    ledger_before_restart = runtime.retry_ledger().read()
    coordination_before_restart = (
        application._coordinator.runtime_root  # noqa: SLF001
        / "coordination/changes/change-a.json"
    ).read_bytes()
    remote_refs_before_restart = _remote_refs(remote)
    calls_after_first_execution = provider.draft_state_calls
    _git(repository_root, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository_root, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository_root,
        publication_provider=provider,
    )
    async with Client(assemble_target_server(reloaded)) as client:
        restarted = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action["operation_id"]},
        )
    assert acquired.structured_content["kind"] == "acquired"
    assert action["kind"] == "mark-ready"
    assert not executed.is_error
    assert not replayed.is_error
    assert executed.structured_content == replayed.structured_content
    assert executed.structured_content is not None
    assert executed.structured_content["kind"] == "completed"
    assert not restarted.is_error
    assert restarted.structured_content == executed.structured_content
    assert provider.draft_state_calls == calls_after_first_execution == 1
    assert reloaded._runtimes["change-a"].frontier_bytes() == frontier_before_restart  # noqa: SLF001
    assert reloaded._runtimes["change-a"].retry_ledger().read() == ledger_before_restart  # noqa: SLF001
    assert (
        reloaded._coordinator.runtime_root  # noqa: SLF001
        / "coordination/changes/change-a.json"
    ).read_bytes() == coordination_before_restart
    assert (
        _workspace_mutation_snapshot(
            reloaded._coordinator.show("change-a").worktree_path  # noqa: SLF001
        )
        == workspace_before_restart
    )
    assert _remote_refs(remote) == remote_refs_before_restart


@pytest.mark.asyncio
async def test_registered_loader_contains_unavailable_provider_readback_without_repeating_effects(
    tmp_path: Path,
) -> None:
    _repository, runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-b").readiness.basis.model_dump(mode="json")
    async with Client(assemble_target_server(application)) as client:
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-b",
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "readback-session",
            },
        )
    assert not acquired.is_error
    assert acquired.structured_content is not None
    action = acquired.structured_content["engine_action"]
    assert action["kind"] == "mark-ready"
    _make_provider_readback_unavailable(provider, 8)
    provider.read_pull_request = Mock(wraps=provider.read_pull_request)
    provider.observe_checks = Mock(wraps=provider.observe_checks)
    async with Client(assemble_target_server(application)) as client:
        failed = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-b", "operation_id": action["operation_id"]},
        )
    assert not failed.is_error
    assert failed.structured_content is not None
    assert failed.structured_content["kind"] == "blocked"
    assert failed.structured_content["reason_code"] == "engine-action-failed"
    assert "provider readback unavailable" in failed.structured_content["failure"]["detail"]
    assert "release custody" in failed.structured_content["failure"]["retry_condition"]
    assert provider.draft_state_calls == 1

    after_containment = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-b",
        operation_id=action["operation_id"],
    )
    async with Client(assemble_target_server(application)) as client:
        first = await client.call_tool("get_change", {"change_id": "change-b"})
        second = await client.call_tool("get_change", {"change_id": "change-b"})
        listed = await client.call_tool("list_work_items", {})
    assert first.structured_content == second.structured_content
    assert first.structured_content is not None
    assert first.structured_content["readiness"]["reason_code"] == "engine-action-failed"
    assert first.structured_content["readiness"]["prompt"].startswith("/repair-delivery")
    assert not listed.is_error
    after_reads = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-b",
        operation_id=action["operation_id"],
    )
    _assert_loader_observation_only(after_containment, after_reads)
    assert provider.draft_state_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("journal_state", ["invalid-intent", "mismatched-intent", "invalid-result"])
async def test_registered_loader_contains_malformed_engine_journals_without_effects(
    tmp_path: Path,
    journal_state: str,
) -> None:
    repository, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    action = _engine_action(application, "change-a")
    intent_path = application._coordinator.continuation_record_path(  # noqa: SLF001
        "change-a", action.operation_id
    )
    result_path = intent_path.with_name("result.json")
    if journal_state == "invalid-intent":
        intent_path.write_bytes(b"{")
    elif journal_state == "mismatched-intent":
        intent_path.write_bytes(_canonical(action.model_copy(update={"session_id": "foreign-session"})))
    else:
        result_path.mkdir()
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    provider.read_pull_request = Mock(wraps=provider.read_pull_request)
    provider.observe_checks = Mock(wraps=provider.observe_checks)
    before = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=reloaded._coordinator.runtime_root,  # noqa: SLF001
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    async with Client(assemble_target_server(reloaded)) as client:
        detail = await client.call_tool("get_change", {"change_id": "change-a"})
        repeated = await client.call_tool("get_change", {"change_id": "change-a"})
        assert detail.structured_content == repeated.structured_content
        assert detail.structured_content is not None
        readiness = detail.structured_content["readiness"]
        assert readiness["reason_code"] == "engine-action-blocked"
        assert readiness["executable"] is False
        assert readiness["action"] is None
        assert readiness["prompt"].startswith("/repair-delivery")
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": readiness["basis"],
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "must-not-retry",
            },
        )
    assert not acquired.is_error
    assert acquired.structured_content is not None
    assert acquired.structured_content["engine_action"] is None
    after = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=reloaded._coordinator.runtime_root,  # noqa: SLF001
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    _assert_loader_observation_only(before, after)
    assert provider.draft_state_calls == 0
    if journal_state == "invalid-result":
        assert not tuple(result_path.iterdir())
    assert result_path.is_dir() is (journal_state == "invalid-result")


@pytest.mark.asyncio
async def test_registered_default_loader_contains_unknown_result_after_restart(tmp_path: Path) -> None:
    """A registered execution crash is contained by the fresh default loader."""
    repository_root, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    async with Client(assemble_target_server(application)) as client:
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert not acquired.is_error
    assert acquired.structured_content is not None
    action = acquired.structured_content["engine_action"]
    assert action["kind"] == "mark-ready"

    provider.lose_draft_state_response = False
    original_finish = application._coordinator.finish_continuation_action  # noqa: SLF001
    failure_message = "injected result publication crash"

    def crash_at_result_publication(
        action_record: ChangeContinuationAction,
        result: DeliveryEngineActionResult,
        finished_at: object,
        *,
        release: bool,
    ) -> None:
        if action_record.operation_id == action["operation_id"]:
            raise RuntimeError(failure_message)
        return original_finish(action_record, result, finished_at, release=release)

    with patch.object(
        application._coordinator,  # noqa: SLF001
        "finish_continuation_action",
        crash_at_result_publication,
    ):
        async with Client(assemble_target_server(application)) as client:
            failed = await client.call_tool(
                "execute_change_action",
                {"change_id": "change-a", "operation_id": action["operation_id"]},
            )
    assert failed.is_error

    runtime = application._runtimes["change-a"]  # noqa: SLF001
    workspace_before_containment = _workspace_mutation_snapshot(
        application._coordinator.show("change-a").worktree_path  # noqa: SLF001
    )
    frontier_before_containment = runtime.frontier_bytes()
    ledger_before_containment = runtime.retry_ledger().read()
    coordination_before_containment = (
        application._coordinator.runtime_root  # noqa: SLF001
        / "coordination/changes/change-a.json"
    ).read_bytes()
    remote_refs_before_containment = _remote_refs(remote)
    _git(repository_root, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository_root, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository_root,
        publication_provider=provider,
    )
    async with Client(assemble_target_server(reloaded)) as client:
        contained = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action["operation_id"]},
        )
    assert not contained.is_error
    assert contained.structured_content is not None
    assert contained.structured_content["kind"] == "blocked"
    assert contained.structured_content["reason_code"] == "engine-action-interrupted"
    assert provider.draft_state_calls == 1
    assert reloaded._runtimes["change-a"].frontier_bytes() == frontier_before_containment  # noqa: SLF001
    assert reloaded._runtimes["change-a"].retry_ledger().read() == ledger_before_containment  # noqa: SLF001
    assert (
        _workspace_mutation_snapshot(
            reloaded._coordinator.show("change-a").worktree_path  # noqa: SLF001
        )
        == workspace_before_containment
    )
    assert (
        reloaded._coordinator.runtime_root  # noqa: SLF001
        / "coordination/changes/change-a.json"
    ).read_bytes() == coordination_before_containment
    retained = reloaded._coordinator.show("change-a").continuation_action  # noqa: SLF001
    assert retained is not None
    assert retained.operation_id == action["operation_id"]
    assert retained.finished_at is None
    assert _remote_refs(remote) == remote_refs_before_containment


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_kind",
    [
        "reconcile-checkpoint",
        "sync-target",
        pytest.param("observe-acceptance", marks=pytest.mark.timeout(60)),
    ],
)
async def test_registered_loader_replays_and_contains_interrupted_engine_rows(  # noqa: PLR0915
    tmp_path: Path,
    action_kind: str,
) -> None:
    """Every non-mark-ready owner row preserves exact effects across the registered boundary."""
    repository, runtime_root, remote, provider, application = _loader_registered_engine_action_fixture(
        tmp_path,
        action_kind,  # type: ignore[arg-type]
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    if action_kind == "observe-acceptance":
        async with Client(assemble_target_server(application)) as client:
            prepared = await client.call_tool(
                "acquire_change_action",
                {
                    "change_id": "change-a",
                    "expected_basis": basis,
                    "capabilities": ["planner", "builder", "finalizer", "engine"],
                    "host_id": "synthetic-host",
                    "session_id": "preparation-session",
                },
            )
            assert not prepared.is_error
            assert prepared.structured_content is not None
            prepared_action = ChangeContinuationAction.model_validate(prepared.structured_content["engine_action"])
            assert prepared_action.kind == "mark-ready"
            prepared_result = await client.call_tool(
                "execute_change_action",
                {
                    "change_id": "change-a",
                    "operation_id": prepared_action.operation_id,
                },
            )
        assert not prepared_result.is_error
        assert prepared_result.structured_content["kind"] == "completed", prepared_result.structured_content
        provider.pull_requests[0] = provider.pull_requests[0].model_copy(
            update={
                "state": "closed",
                "merged": True,
                "merge_commit_sha": prepared_action.exact_head,
                "merged_at": datetime(2026, 8, 4, tzinfo=UTC),
            }
        )
        application._publication_observation_cache.clear()  # noqa: SLF001
        basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    runtime = application._runtimes["change-a"]  # noqa: SLF001
    sibling_frontier = application._runtimes["change-c"].frontier_bytes()  # noqa: SLF001
    sibling_publication = application._runtimes["change-c"].checkpoint_publication_state()  # noqa: SLF001

    async with Client(assemble_target_server(application)) as client:
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": basis,
                "capabilities": ["planner", "builder", "finalizer", "engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
        assert not acquired.is_error
        assert acquired.structured_content is not None
        registered_action = acquired.structured_content["engine_action"]
        action = ChangeContinuationAction.model_validate(registered_action)
        assert action.kind == action_kind
        before_owner_execution = _loader_engine_state_snapshot(
            application,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        executed = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action.operation_id},
        )
        before_immediate_replay = _loader_engine_state_snapshot(
            application,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        replayed = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action.operation_id},
        )
    after_immediate_replay = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    assert not executed.is_error
    assert not replayed.is_error
    assert executed.structured_content == replayed.structured_content
    assert executed.structured_content["kind"] == "completed", executed.structured_content
    assert after_immediate_replay == before_immediate_replay
    assert after_immediate_replay["provider_mutations"] == before_immediate_replay["provider_mutations"]
    assert after_immediate_replay["provider_reads"] == before_immediate_replay["provider_reads"]
    engine_result = executed.structured_content
    operation_journal = before_immediate_replay["continuation_operation_journal"]
    assert operation_journal["intent"]
    assert operation_journal["started"]
    assert operation_journal["result"]
    completed_record = json.loads(operation_journal["result"])
    assert completed_record["kind"] == "completed"
    assert completed_record["action"]["operation_id"] == action.operation_id
    if action_kind in {"reconcile-checkpoint", "sync-target"}:
        published_head = (
            action.exact_head if action_kind == "reconcile-checkpoint" else engine_result["target_sync"]["merged_head"]
        )
        _assert_checkpoint_branch_operation(
            before_owner_execution,
            before_immediate_replay,
            change_id=action.change_id,
            published_head=published_head,
            expected_remote_head=before_owner_execution["checkpoint_publication"].published_head,
        )
    else:
        assert any(
            path.startswith(f"{action.change_id}/") and path != f"{action.change_id}/display.json" and content
            for path, content in before_immediate_replay["completion_journal"]
        )
    assert engine_result["action"]["operation_id"] == action.operation_id
    assert engine_result["action"]["kind"] == action.kind
    if action_kind == "reconcile-checkpoint":
        checkpoint = engine_result["checkpoint"]
        assert checkpoint["change_id"] == action.change_id
        assert checkpoint["attempted_head"] == action.exact_head
        assert checkpoint["reconciled"] is True
    elif action_kind == "sync-target":
        target_sync = engine_result["target_sync"]
        assert target_sync["change_id"] == action.change_id
        assert target_sync["expected_target"] == action.target_head
        assert target_sync["target_head"] == action.target_head
        assert target_sync["merged_head"]
    else:
        acceptance = engine_result["acceptance"]
        assert acceptance["completion_id"]
        assert acceptance["acceptance_observation_id"]
    effects_after_completion = (
        provider.create_calls,
        provider.update_calls,
        provider.draft_state_calls,
    )
    frontier_after_completion = runtime.frontier_bytes()
    retry_after_completion = runtime.retry_ledger().read()
    workspace_after_completion = _workspace_mutation_snapshot(
        application._coordinator.show("change-a").worktree_path  # noqa: SLF001
    )
    remote_after_completion = _remote_refs(remote)

    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    after_loader_before_replay = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    assert after_loader_before_replay == after_immediate_replay
    async with Client(assemble_target_server(reloaded)) as client:
        restarted = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action.operation_id},
        )
    after_loader_replay = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    assert not restarted.is_error
    assert restarted.structured_content == executed.structured_content
    assert after_loader_replay == after_loader_before_replay
    retained = reloaded.get_change("change-a").continuation_action
    assert retained is not None
    assert retained.model_copy(update={"finished_at": None}) == action
    assert (
        provider.create_calls,
        provider.update_calls,
        provider.draft_state_calls,
    ) == effects_after_completion
    assert reloaded._runtimes["change-a"].frontier_bytes() == frontier_after_completion  # noqa: SLF001
    assert reloaded._runtimes["change-a"].retry_ledger().read() == retry_after_completion  # noqa: SLF001
    assert (
        _workspace_mutation_snapshot(
            reloaded._coordinator.show("change-a").worktree_path  # noqa: SLF001
        )
        == workspace_after_completion
    )
    assert _remote_refs(remote) == remote_after_completion
    assert reloaded._runtimes["change-c"].frontier_bytes() == sibling_frontier  # noqa: SLF001
    assert reloaded._runtimes["change-c"].checkpoint_publication_state() == sibling_publication  # noqa: SLF001
    if action_kind != "observe-acceptance":
        next_basis = reloaded.get_change("change-a").readiness.basis.model_dump(mode="json")
        async with Client(assemble_target_server(reloaded)) as client:
            next_acquired = await client.call_tool(
                "acquire_change_action",
                {
                    "change_id": "change-a",
                    "expected_basis": next_basis,
                    "capabilities": ["planner", "builder", "finalizer", "engine"],
                    "host_id": "synthetic-host",
                    "session_id": "fresh-session",
                },
            )
        assert not next_acquired.is_error
        assert next_acquired.structured_content is not None
        assert next_acquired.structured_content["kind"] == "acquired"
        next_engine_action = next_acquired.structured_content["engine_action"]
        if next_engine_action is not None:
            next_action = ChangeContinuationAction.model_validate(next_engine_action)
            assert next_action.change_id == action.change_id
            assert next_action.operation_id != action.operation_id
        else:
            next_finalization = next_acquired.structured_content["finalization"]
            next_launch = next_acquired.structured_content["launch"]
            assert next_finalization is not None or next_launch is not None
            next_owner_id = (
                next_finalization["attempt"]["writer"]["attempt_id"]
                if next_finalization is not None
                else next_launch["claim"]["attempt_id"]
            )
            assert next_owner_id != action.operation_id

    # A fresh action on an independent Change remains acquireable after replay.
    sibling = reloaded.get_change("change-c")
    sibling_basis = sibling.readiness.basis.model_dump(mode="json")
    async with Client(assemble_target_server(reloaded)) as client:
        subsequent = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-c",
                "expected_basis": sibling_basis,
                "capabilities": ["planner", "builder", "finalizer", "engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert not subsequent.is_error
    assert subsequent.structured_content is not None
    assert subsequent.structured_content["kind"] == "acquired"


@pytest.mark.asyncio
@pytest.mark.parametrize("action_kind", ["reconcile-checkpoint", "sync-target", "observe-acceptance"])
async def test_registered_loader_contains_unknown_custody_without_repeating_effects(  # noqa: PLR0915
    tmp_path: Path,
    action_kind: str,
) -> None:
    """A result-publication interruption remains blocked and retains its exact action."""
    repository, runtime_root, remote, provider, application = _loader_registered_engine_action_fixture(
        tmp_path,
        action_kind,  # type: ignore[arg-type]
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    if action_kind == "observe-acceptance":
        async with Client(assemble_target_server(application)) as client:
            prepared = await client.call_tool(
                "acquire_change_action",
                {
                    "change_id": "change-a",
                    "expected_basis": basis,
                    "capabilities": ["planner", "builder", "finalizer", "engine"],
                    "host_id": "synthetic-host",
                    "session_id": "preparation-session",
                },
            )
            assert not prepared.is_error
            assert prepared.structured_content is not None
            prepared_action = ChangeContinuationAction.model_validate(prepared.structured_content["engine_action"])
            assert prepared_action.kind == "mark-ready"
            prepared_result = await client.call_tool(
                "execute_change_action",
                {
                    "change_id": "change-a",
                    "operation_id": prepared_action.operation_id,
                },
            )
        assert not prepared_result.is_error
        assert prepared_result.structured_content["kind"] == "completed"
        provider.pull_requests[0] = provider.pull_requests[0].model_copy(
            update={
                "state": "closed",
                "merged": True,
                "merge_commit_sha": prepared_action.exact_head,
                "merged_at": datetime(2026, 8, 4, tzinfo=UTC),
            }
        )
        application._publication_observation_cache.clear()  # noqa: SLF001
        basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    sibling_frontier = application._runtimes["change-c"].frontier_bytes()  # noqa: SLF001
    sibling_publication = application._runtimes["change-c"].checkpoint_publication_state()  # noqa: SLF001
    async with Client(assemble_target_server(application)) as client:
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": basis,
                "capabilities": ["planner", "builder", "finalizer", "engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert not acquired.is_error
    assert acquired.structured_content is not None
    action = ChangeContinuationAction.model_validate(acquired.structured_content["engine_action"])
    assert action.kind == action_kind
    original_finish = application._coordinator.finish_continuation_action  # noqa: SLF001
    failure_message = "registered result publication interruption"
    provider.read_pull_request = Mock(wraps=provider.read_pull_request)
    provider.observe_checks = Mock(wraps=provider.observe_checks)
    before_owner_execution = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )

    def interrupt_finish(action_record, result, finished_at, *, release):
        if action_record.operation_id == action.operation_id:
            raise RuntimeError(failure_message)
        return original_finish(action_record, result, finished_at, release=release)

    with patch.object(
        application._coordinator,  # noqa: SLF001
        "finish_continuation_action",
        interrupt_finish,
    ):
        async with Client(assemble_target_server(application)) as client:
            failed = await client.call_tool(
                "execute_change_action",
                {"change_id": "change-a", "operation_id": action.operation_id},
            )
    assert failed.is_error
    before_reload = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    operation_journal_before_reload = before_reload["continuation_operation_journal"]
    assert operation_journal_before_reload["intent"]
    assert operation_journal_before_reload["started"]
    assert operation_journal_before_reload["result"] is None
    assert any(action.operation_id in episode.attempt_ids for episode in before_reload["retry_ledger"].episodes)
    if action_kind in {"reconcile-checkpoint", "sync-target"}:
        if action_kind == "reconcile-checkpoint":
            published_head = action.exact_head
        else:
            target_sync = application._runtimes["change-a"].target_sync_receipt()  # noqa: SLF001
            assert target_sync is not None
            published_head = target_sync.merged_head
        _assert_checkpoint_branch_operation(
            before_owner_execution,
            before_reload,
            change_id=action.change_id,
            published_head=published_head,
            expected_remote_head=before_owner_execution["checkpoint_publication"].published_head,
        )
    else:
        assert any(
            path.startswith(f"{action.change_id}/") and path != f"{action.change_id}/display.json" and content
            for path, content in before_reload["completion_journal"]
        )
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    after_loader = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    expected_after_loader = dict(before_reload)
    if action_kind == "observe-acceptance":
        _assert_loader_retry_recording(
            before_reload,
            after_loader,
            action_id=action.operation_id,
            accepted_progress=True,
        )
        expected_after_loader["retry_ledger"] = after_loader["retry_ledger"]
        expected_after_loader["retry_journal"] = after_loader["retry_journal"]
    else:
        _assert_loader_retry_recording(
            before_reload,
            after_loader,
            action_id=action.operation_id,
            accepted_progress=False,
        )
    assert after_loader == expected_after_loader
    async with Client(assemble_target_server(reloaded)) as client:
        before_containment = _loader_engine_state_snapshot(
            reloaded,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        _assert_loader_observation_only(after_loader, before_containment)
        contained = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action.operation_id},
        )
        assert not contained.is_error
        assert contained.structured_content is not None
        assert contained.structured_content["kind"] == "blocked"
        assert contained.structured_content["reason_code"] == "engine-action-interrupted"
        after_containment = _loader_engine_state_snapshot(
            reloaded,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        contained_replay = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": action.operation_id},
        )
        after_replay_execution = _loader_engine_state_snapshot(
            reloaded,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        guidance = await client.call_tool("get_change", {"change_id": "change-a"})
        listed = await client.call_tool("list_work_items", {})
        shown = await client.call_tool(
            "show_work_item",
            {"change_id": "change-a", "work_item_id": "change-a"},
        )
        repeated_guidance = await client.call_tool("get_change", {"change_id": "change-a"})
        repeated_listed = await client.call_tool("list_work_items", {})
        repeated_shown = await client.call_tool(
            "show_work_item",
            {"change_id": "change-a", "work_item_id": "change-a"},
        )
    operation_journal_after_containment = after_containment["continuation_operation_journal"]
    assert operation_journal_after_containment["intent"] == operation_journal_before_reload["intent"]
    assert operation_journal_after_containment["started"] == operation_journal_before_reload["started"]
    assert operation_journal_after_containment["result"]
    containment_record = json.loads(operation_journal_after_containment["result"])
    assert containment_record["kind"] == "blocked"
    assert containment_record["reason_code"] == "engine-action-interrupted"
    assert containment_record["action"]["operation_id"] == action.operation_id
    expected_containment = dict(before_containment)
    expected_containment["continuation_operation_journal"] = operation_journal_after_containment
    assert after_containment == expected_containment
    assert after_containment["retry_ledger"] == before_containment["retry_ledger"]
    assert after_replay_execution == after_containment
    assert contained_replay.structured_content == contained.structured_content
    assert not guidance.is_error
    assert not listed.is_error
    assert not shown.is_error
    assert guidance.structured_content
    assert listed.structured_content
    assert shown.structured_content
    assert guidance.structured_content["change_id"] == "change-a"
    assert listed.structured_content["result"]
    assert shown.structured_content["projection"]["change_id"] == "change-a"
    assert shown.structured_content["projection"]["work_item_id"] == "change-a"
    assert guidance.structured_content["continuation_action"]["operation_id"] == action.operation_id
    assert guidance.structured_content["continuation_action"]["kind"] == action.kind
    readiness = guidance.structured_content["readiness"]
    assert readiness["reason_code"] == "engine-action-interrupted"
    assert readiness["status"] == "blocked"
    assert readiness["checks_state"] == reloaded.get_change("change-a").readiness.checks_state
    assert readiness["executable"] is False
    assert readiness["action"] is None
    assert readiness["prompt"] == (
        "/continue-change change-a only after the Delivery engine owner verifies host/worker closure and settles "
        "all descendant writers and jobs; preserve custody and journals, and do not retry or infer termination."
    )
    next_step = shown.structured_content["projection"]["next_action"]
    assert "Delivery engine owner" in next_step
    assert "Preserve custody and journals" in next_step
    assert "all descendant writers and jobs" in next_step
    assert "do not retry" in next_step
    assert guidance.structured_content["detail"]["card"]["next_actor"] == "agent"
    assert guidance.structured_content == repeated_guidance.structured_content
    assert listed.structured_content == repeated_listed.structured_content
    assert shown.structured_content == repeated_shown.structured_content
    assert reloaded.get_change("change-a").continuation_action == action
    assert reloaded.get_change("change-a").continuation_action.finished_at is None
    assert reloaded._runtimes["change-c"].frontier_bytes() == sibling_frontier  # noqa: SLF001
    assert reloaded._runtimes["change-c"].checkpoint_publication_state() == sibling_publication  # noqa: SLF001
    after_read_only_views = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    _assert_loader_observation_only(after_containment, after_read_only_views)


@pytest.mark.asyncio
async def test_registered_default_loader_contains_failed_finalizer_before_checks(tmp_path: Path) -> None:
    _repository, _runtime_root, _remote, _provider, application = _loader_registered_engine_action_fixture(
        tmp_path, "sync-target"
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    async with Client(assemble_target_server(application)) as client:
        synchronized = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "sync-session",
            },
        )
        assert not synchronized.is_error
        assert synchronized.structured_content is not None
        sync_action = synchronized.structured_content["engine_action"]
        assert sync_action is not None
        assert sync_action["kind"] == "sync-target"
        executed_sync = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": sync_action["operation_id"]},
        )
        assert not executed_sync.is_error
        basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": basis,
                "capabilities": ["finalizer"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
        assert not acquired.is_error
        assert acquired.structured_content is not None
        finalization = acquired.structured_content["finalization"]
        assert finalization is not None, acquired.structured_content
        (application._coordinator.show("change-a").worktree_path / "product.txt").write_text(  # noqa: SLF001
            "dirty before checks\n"
        )
        finalization_basis = application.show_finalization_context("change-a").readiness.basis
        failure = _failure_request(
            application,
            attempt_key=finalization["attempt"]["writer"]["attempt_id"],
            category="custody-preflight",
            code=FinalizationFailureCode.WORKSPACE_DIRTY,
            checks_state="not-run",
            expected_workspace_fingerprint=finalization_basis.workspace_fingerprint,
            paths=("product.txt",),
        )
        retry_now = datetime.now(UTC).isoformat()
        application._clock = lambda: retry_now  # noqa: SLF001
        reported = await client.call_tool(
            "report_finalization_failure",
            failure.model_dump(mode="json"),
        )
        assert not reported.is_error
        assert reported.structured_content is not None
        assert reported.structured_content["request"]["checks_state"] == "not-run"
        assert reported.structured_content["request"]["code"] == "workspace-dirty"
        conflicting = await client.call_tool(
            "report_finalization_failure",
            failure.model_copy(update={"checks_state": "unknown"}).model_dump(mode="json"),
        )
        current_basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
        stopped = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": current_basis,
                "capabilities": ["finalizer"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session-2",
            },
        )
    assert not stopped.is_error
    assert conflicting.is_error
    assert (_registered_diagnostic(conflicting)["code"], _registered_diagnostic(conflicting)["retry_safe"]) == (
        "diagnostic-conflict",
        False,
    )
    assert stopped.structured_content is not None
    assert stopped.structured_content["kind"] == "busy", stopped.structured_content
    assert stopped.structured_content["reason_code"] == "active-custody"
    assert stopped.structured_content["readiness"]["checks_state"] == "not-run"
    assert stopped.structured_content["finalization"] is None
    assert application._coordinator.show("change-a").writer is not None  # noqa: SLF001


@pytest.mark.asyncio
@pytest.mark.parametrize("writer_recorded", [False, True])
async def test_registered_default_loader_contains_failed_claim_activation(  # noqa: PLR0915 - verify persisted activation and independent restart progress.
    tmp_path: Path,
    *,
    writer_recorded: bool,
) -> None:
    repository, _runtime_root = _seed_loader_composed_completed_change(
        tmp_path,
        (("change-a", DeliveryStage.IMPLEMENTATION), ("change-b", DeliveryStage.IMPLEMENTATION)),
    )
    application = load_core_delivery_application(_startup_config(), workspace_root=repository)
    coordinator = application._coordinator  # noqa: SLF001
    acquire = coordinator.acquire

    def fail(change_id: str, writer: object, **kwargs: object) -> None:
        if writer_recorded:
            acquire(change_id, writer, **kwargs)
        failure_message = "injected writer persistence failure"
        raise OSError(failure_message)

    with patch.object(coordinator, "acquire", fail):
        basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
        async with Client(assemble_target_server(application)) as client:
            result = await client.call_tool(
                "acquire_change_action",
                {
                    "change_id": "change-a",
                    "expected_basis": basis,
                    "capabilities": ["builder"],
                    "host_id": "synthetic-host",
                    "session_id": "synthetic-session",
                },
            )
    assert not result.is_error
    assert result.structured_content is not None
    assert result.structured_content["kind"] == "unavailable"
    assert result.structured_content["reason_code"] == "claim-activation-failed"
    assert result.structured_content["launch"] is None
    assert result.structured_content["readiness"]["prompt"].startswith("/repair-delivery")
    assert "read-only" in result.structured_content["readiness"]["prompt"]
    assert result.structured_content["failure"]["claim_id"]
    assert result.structured_content["failure"]["attempt_id"]
    assert (coordinator.show("change-a").writer is not None) is writer_recorded

    failure = result.structured_content["failure"]
    failed_claim = application._runtimes["change-a"].show_binding("OUT-001").active_claim  # noqa: SLF001
    failed_episode = application._runtimes["change-a"].retry_ledger().read().episodes[0]  # noqa: SLF001
    assert failed_claim is not None
    assert (failed_claim.claim_id, failed_claim.attempt_id) == (failure["claim_id"], failure["attempt_id"])
    assert failed_episode.attempt_ids == (failed_claim.attempt_id,)
    before_reload = _loader_activation_state_snapshot(application)
    reloaded = load_core_delivery_application(_startup_config(), workspace_root=repository)
    assert _loader_activation_state_snapshot(reloaded) == before_reload
    reloaded_coordinator = reloaded._coordinator  # noqa: SLF001
    reloaded_runtime = reloaded._runtimes["change-a"]  # noqa: SLF001
    assert reloaded_runtime.show_binding("OUT-001").active_claim == failed_claim
    assert reloaded_runtime.retry_ledger().read().episodes == (failed_episode,)
    assert (reloaded_coordinator.show("change-a").writer is not None) is writer_recorded
    coordination_path = reloaded_coordinator.runtime_root / "coordination/changes/change-a.json"
    coordination_before = coordination_path.read_bytes()
    async with Client(assemble_target_server(reloaded)) as client:
        first_read = await client.call_tool("get_change", {"change_id": "change-a"})
        second_read = await client.call_tool("get_change", {"change_id": "change-a"})
        assert first_read.structured_content == second_read.structured_content
        assert first_read.structured_content is not None
        assert first_read.structured_content["readiness"]["executable"] is False
        assert first_read.structured_content["readiness"]["prompt"].startswith("/repair-delivery")
        assert "dispatch a replacement" in first_read.structured_content["readiness"]["prompt"]
        blocked = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": first_read.structured_content["readiness"]["basis"],
                "capabilities": ["builder"],
                "host_id": "synthetic-host",
                "session_id": "retry-after-restart",
            },
        )
    after_refusal = _loader_activation_state_snapshot(reloaded)
    assert after_refusal == before_reload
    async with Client(assemble_target_server(reloaded)) as client:
        sibling_read = await client.call_tool("get_change", {"change_id": "change-b"})
        assert sibling_read.structured_content is not None
        sibling = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-b",
                "expected_basis": sibling_read.structured_content["readiness"]["basis"],
                "capabilities": ["builder"],
                "host_id": "synthetic-host",
                "session_id": "sibling-after-restart",
            },
        )
    assert blocked.structured_content is not None
    assert blocked.structured_content["launch"] is None
    assert blocked.structured_content["reason_code"] == (
        "active-custody" if writer_recorded else "claim-custody-unreconciled"
    )
    assert coordination_path.read_bytes() == coordination_before
    assert reloaded_runtime.show_binding("OUT-001").active_claim == failed_claim
    assert reloaded_runtime.retry_ledger().read().episodes == (failed_episode,)
    assert not sibling.is_error
    assert sibling.structured_content is not None
    assert sibling.structured_content["kind"] == "acquired"
    assert sibling.structured_content["launch"] is not None
    assert reloaded._runtimes["change-b"].show_binding("OUT-001").active_claim is not None  # noqa: SLF001
    after_sibling_progress = _loader_activation_state_snapshot(reloaded)
    before_changes = before_reload["changes"]
    after_changes = after_sibling_progress["changes"]
    assert after_changes["change-a"] == before_changes["change-a"]
    assert after_changes["change-b"]["frontier"] != before_changes["change-b"]["frontier"]
    assert after_changes["change-b"]["workspace"] == before_changes["change-b"]["workspace"]
    assert after_sibling_progress["repository_refs"] == before_reload["repository_refs"]


@pytest.mark.asyncio
async def test_registered_default_loader_rejects_stale_basis_without_acquisition(tmp_path: Path) -> None:
    _repository, _runtime_root, _remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    stale_basis = {**basis, "frontier_digest": "0" * 64}
    async with Client(assemble_target_server(application)) as client:
        result = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": stale_basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert not result.is_error
    assert result.structured_content is not None
    assert result.structured_content["kind"] == "stale"
    assert result.structured_content["reason_code"] == "readiness-changed"
    assert result.structured_content["launch"] is None
    assert provider.draft_state_calls == 0


@pytest.mark.asyncio
async def test_registered_default_loader_reports_unavailable_custody(tmp_path: Path) -> None:
    repository, _runtime_root, _remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    coordination = application._coordinator.runtime_root / "coordination/changes/change-a.json"  # noqa: SLF001
    coordination.write_bytes(b"{")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{_remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    async with Client(assemble_target_server(reloaded)) as client:
        detail = await client.call_tool("get_change", {"change_id": "change-a"})
        result = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": {"contract_digest": "a" * 64, "frontier_digest": "b" * 64},
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert not result.is_error
    assert result.structured_content is not None
    assert result.structured_content["kind"] == "unavailable"
    assert result.structured_content["reason_code"] == "coordination-unavailable"
    assert result.structured_content["engine_action"] is None
    assert detail.structured_content is not None
    readiness = detail.structured_content["readiness"]
    assert readiness["status"] == "unavailable"
    assert readiness["checks_state"] == "unknown"
    assert readiness["prompt"] == (
        "Do not release, retry, or redispatch Change change-a: canonical Delivery authority is unavailable "
        "(coordination-unavailable); checks are unknown. Preserve existing custody and journals. Use "
        "/repair-delivery Diagnose Change change-a read-only; preserve existing custody and journals. This does "
        "not repair authority or prove host/worker closure; the responsible owner must resolve the condition "
        "separately before Delivery rereads it."
    )
    assert provider.draft_state_calls == 0


DELIVERY_TOOLS = {
    "create_design_session",
    "put_design",
    "read_design_session",
    "revise_design_session",
    "publish_design_checkpoint",
    "derive_delivery_contract",
    "admit_delivery_change",
    "admit_change",
    "list_work_items",
    "list_changes",
    "get_change",
    "answer",
    "set_change_intent",
    "delivery_health",
    "propose_quarantined_delivery_state_snapshot_repair",
    "repair_delivery_state_snapshot",
    "repair_quarantined_delivery_state_snapshot",
    "repair_stranded_frontier",
    "recover_out_of_band_head",
    "repair_target_sync_publication",
    "list_retained_change_worktrees",
    "show_work_item",
    "show_work_item_view",
    "show_operator_context",
    "repair",
    "preview_administrative_move",
    "administrative_move",
    "acquire_actions",
    "acquire_change_action",
    "execute_change_action",
    "show_plan_context",
    "show_build_context",
    "show_finalization_context",
    "derive_evidence_receipts",
    "report_finalization_failure",
    "publish_delivery_plan",
    "submit_result",
    "finalize_change",
    "mark_change_ready",
    "prepare_review_repair",
    "reconcile_finalization_head",
    "reconcile_change_checkpoint",
    "sync_change_with_target",
    "adopt_external_head",
    "promote_external_head",
    "abort_target_sync_conflict",
    "resolve_target_sync_conflict",
    "supersede_publication",
    "observe_change_publication_checks",
    "observe_acceptance",
    "cleanup_abandoned_change_worktree",
    "cleanup_abandoned_change_worktree_after_target_sync_discard",
    "cleanup_completed_change_worktree",
    "recover_change_worktree",
    "recover_publication_baseline",
    "transition_delivery",
    "settle_worker_invocation",
    "release_stuck_worker",
    "recover_claim",
    "recover_integration_repair_claim",
    "show_integration_attention",
    "list_completed_changes",
    "search_completed_changes",
    "show_completed_change",
}
READ_TOOLS = {
    "read_design_session",
    "derive_delivery_contract",
    "list_work_items",
    "list_changes",
    "get_change",
    "delivery_health",
    "propose_quarantined_delivery_state_snapshot_repair",
    "list_retained_change_worktrees",
    "show_work_item",
    "show_work_item_view",
    "show_operator_context",
    "preview_administrative_move",
    "show_plan_context",
    "show_build_context",
    "show_finalization_context",
    "derive_evidence_receipts",
    "show_integration_attention",
    "observe_change_publication_checks",
    "list_completed_changes",
    "search_completed_changes",
    "show_completed_change",
}
EXCLUDED_TOOLS = {
    "show_change",
    "validate_change",
    "create_request",
    "unblock_delivery",
    "list_semantic_updates",
    "list_work_item_activity",
    "show_completion_summary",
    "respond_to_review",
    "arbitrate_attempt",
    "recover_interrupted_task",
    "start_job",
    "finish_plan",
    "finish_build",
    "finish_assembly",
    "return_delivery",
    "list_frontier",
    "show_job",
    "show_attempt",
    "show_receipt",
}


class _Result(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    operation: str


class _RecordingApplication:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        def operation(*_args: object, **_kwargs: object) -> object:
            self.calls.append(name)
            return () if name == "list_work_items" else _Result(operation=name)

        return operation


CONTINUATION_ID = f"continue-{'c' * 64}"


def _continuation_action() -> ChangeContinuationAction:
    return ChangeContinuationAction(
        operation_id=CONTINUATION_ID,
        change_id="change-a",
        kind="sync-target",
        contract_digest="a" * 64,
        frontier_digest="a" * 64,
        exact_head="b" * 40,
        target_head="c" * 40,
        host_id="host",
        session_id="session",
        acquired_at="2026-09-13T00:00:00Z",
    )


def _continuation_readiness(reason: str) -> DeliveryReadiness:
    return DeliveryReadiness(
        status="ready",
        next_actor=WorkItemNextActor.AGENT,
        reason_code=reason,  # type: ignore[arg-type]
        basis=DeliveryReadinessBasis(
            contract_digest="a" * 64,
            frontier_digest="a" * 64,
            source_head="b" * 40,
            target_head="c" * 40,
            continuation_id=CONTINUATION_ID,
        ),
    )


# Non-acquired dispositions the transport must forward unchanged, keyed by selected Change.
_CONTINUATION_DISPOSITIONS = {
    "change-waiting": ("waiting", "host-capability-unavailable", "ready"),
    "change-stale": ("stale", "readiness-changed", "target-sync-required"),
    "change-human": ("human", "merge-approval-required", "publication-wait"),
    "change-busy": ("busy", "operation-in-progress", "active-custody"),
}


class _ContinuationApplication(_RecordingApplication):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[object] = []

    def acquire_change_action(self, request: DeliveryContinuationRequest) -> DeliveryContinuationResult:
        self.calls.append("acquire_change_action")
        self.requests.append(request)
        disposition = _CONTINUATION_DISPOSITIONS.get(request.change_id)
        if disposition is not None:
            kind, reason, readiness_reason = disposition
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind=kind,  # type: ignore[arg-type]
                reason_code=reason,  # type: ignore[arg-type]
                readiness=_continuation_readiness(readiness_reason),
            )
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind="acquired",
            reason_code="ready",
            readiness=_continuation_readiness("target-sync-required"),
            engine_action=_continuation_action(),
        )

    def execute_change_action(self, request: ExecuteDeliveryChangeAction) -> DeliveryEngineActionResult:
        self.calls.append("execute_change_action")
        self.requests.append(request)
        return DeliveryEngineActionResult(
            action=_continuation_action(),
            kind="completed",
            reason_code="engine-action-completed",
            target_sync=ChangeTargetSyncReceipt.create(
                operation_id=CONTINUATION_ID,
                change_id=request.change_id,
                integration_target="main",
                expected_target="c" * 40,
                target_head="c" * 40,
                change_head_before="b" * 40,
                merged_head="d" * 40,
                merge_commit=True,
            ),
        )


class _PublicationApplication(_RecordingApplication):
    def __init__(self) -> None:
        super().__init__()
        self.transition: object | None = None

    def publish_delivery_result(self, _change_id: str, request: object) -> DeliveryResultCandidate:
        self.calls.append("publish_delivery_result")
        assert isinstance(request, PublishDeliveryResult)
        return DeliveryResultCandidate(
            candidate_id="result-" + "d" * 64,
            claim_id="claim-1",
            digest="d" * 64,
            result=request.result,
        )

    def transition_delivery(self, _change_id: str, request: object) -> _Result:
        self.calls.append("transition_delivery")
        self.transition = request
        return _Result(operation="transition_delivery")


class _BlockingAcceptanceApplication(_RecordingApplication):
    def __init__(self, started: threading.Event, release: threading.Event) -> None:
        super().__init__()
        self._started = started
        self._release = release

    def observe_acceptance(self, _change_id: str) -> _Result:
        self._started.set()
        self._release.wait(timeout=2)
        return _Result(operation="observe_acceptance")


class _BlockingFoundationalApplication(_RecordingApplication):
    def __init__(self, operation_name: str, started: threading.Event, release: threading.Event) -> None:
        super().__init__()
        self._operation_name = operation_name
        self._started = started
        self._release = release
        self.completed = threading.Event()
        self.mutation_count = 0
        self.health_observations: list[int] = []

    def _run_foundational_operation(self) -> _Result:
        self.calls.append(self._operation_name)
        self._started.set()
        self._release.wait(timeout=2)
        self.mutation_count += 1
        self.completed.set()
        return _Result(operation=self._operation_name)

    def admit_delivery_change(self, _request: object) -> _Result:
        return self._run_foundational_operation()

    def acquire_actions(self) -> _Result:
        return self._run_foundational_operation()

    def delivery_health(self) -> DeliveryHealthView:
        self.calls.append("delivery_health")
        self.health_observations.append(self.mutation_count)
        return DeliveryHealthView(status=DeliveryHealthStatus.HEALTHY)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _remote_refs(repository: Path) -> str:
    result = subprocess.run(  # noqa: S603
        (  # noqa: S607
            "git",
            "-c",
            "safe.bareRepository=all",
            "-C",
            str(repository),
            "for-each-ref",
            "--format=%(refname) %(objectname)",
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    return f"{result.returncode}\n{result.stdout}\n{result.stderr}"


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Delivery Startup Test")
    _git(repository, "config", "user.email", "delivery-startup@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repository


def _config() -> dict[str, object]:
    return {
        "schema_version": 2,
        "remote": "origin",
        "target_branch": "main",
        "github_repository": "example/project",
    }


def _write_config(path: Path, content: dict[str, object]) -> None:
    path.write_text(json.dumps(content), encoding="utf-8")


def _write_delivery_state(runtime_root: Path, repository: Path) -> None:
    digest = hashlib.sha256(b"source").hexdigest()
    contract = DeliveryContract(
        change_id="change-a",
        title="Assembled projection",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="assembled MCP test",
                statement="Project current Delivery state.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="Observe transitions",
                promise="Registered tools return current stage.",
                acceptance=("The stage changes without server reload.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            DeliverySourceBinding(source_name="intent.md", sha256=digest),
            DeliverySourceBinding(source_name="design.md", sha256=digest),
        ),
    )
    package_store = DesignPackageStore(repository / ".owlbear/delivery/packages", repository)
    package = package_store.create("change-a", b"source", b"source")
    package_store.publish_contract(
        "change-a",
        package.package_id,
        (json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode(),
        lambda *_content: None,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
            ),
        ),
    )
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    change_root.joinpath("contract.json").write_text(contract.model_dump_json(), encoding="utf-8")
    change_root.joinpath("frontier.json").write_text(frontier.model_dump_json(), encoding="utf-8")
    target_head = subprocess.run(  # noqa: S603
        ["git", "-C", str(repository), "rev-parse", "main"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    receipt_payload = {
        "schema_version": 1,
        "change_id": contract.change_id,
        "contract_digest": contract_fingerprint(contract),
        "source_bindings_digest": hashlib.sha256(
            json.dumps(
                [binding.model_dump(mode="json") for binding in contract.source_bindings],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "integration_target": "main",
        "checkpoint_commit": target_head,
        "frontier_ids": tuple(binding.plan_scope_id for binding in frontier.bindings),
    }
    receipt_payload["receipt_id"] = hashlib.sha256(
        json.dumps(receipt_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    change_root.joinpath("admission.json").write_text(
        DeliveryAdmissionReceipt.model_validate(receipt_payload).model_dump_json(),
        encoding="utf-8",
    )
    coordination_root = runtime_root / "coordination/changes"
    coordination_root.mkdir(parents=True)
    coordination_root.joinpath("change-a.json").write_text(
        ChangeCoordination(
            change_id="change-a",
            branch="main",
            worktree_path=repository,
            integration_target="main",
            target_head=target_head,
            last_reviewed_commit=target_head,
        ).model_dump_json(),
        encoding="utf-8",
    )
    runtime_root.joinpath("format.json").write_bytes(format_marker_bytes())


@pytest.mark.asyncio
async def test_live_registry_is_exact_and_annotated_from_assembled_tools() -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    assert set(tools) == DELIVERY_TOOLS
    assert set(tools).isdisjoint(EXCLUDED_TOOLS)
    # N05 D14: only the user approves a merge, in Cockpit; no agent tool approves or merges.
    assert not [name for name in tools if "approve" in name or "merge" in name]
    for name, tool in tools.items():
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is (name in READ_TOOLS)
        assert tool.annotations.idempotent_hint is (
            name
            not in {
                "acquire_actions",
                "acquire_change_action",
                "resolve_request",
                "clear_block",
                "administrative_move",
                "repair",
                "set_change_intent",
            }
        )
        assert tool.annotations.destructive_hint is (
            name
            in {
                "cleanup_abandoned_change_worktree",
                "cleanup_abandoned_change_worktree_after_target_sync_discard",
                "cleanup_completed_change_worktree",
            }
        )
        assert "request" not in tool.input_schema.get("properties", {})
        assert tool.input_schema["additionalProperties"] is False


@pytest.mark.asyncio
async def test_registered_tool_invokes_strict_adapter_once() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        result = await client.call_tool("list_work_items", {})

    assert set(tools) == DELIVERY_TOOLS
    assert result.structured_content == {"result": []}
    assert application.calls == ["list_work_items"]


@pytest.mark.asyncio
async def test_registered_derive_evidence_receipts_returns_canonical_receipts_without_delivery_state() -> None:
    application = _RecordingApplication()
    observed_at = datetime(2026, 10, 6, 12, tzinfo=UTC)
    observation = DeliveryObservation(
        change_id="change-a",
        task_or_finalization_id="finalize-one",
        exact_commit="b" * 40,
        observation_kind="pytest",
        procedure="maintained check",
        result=DeliveryCommandResult(exit_status=0),
        observer_or_runner_identity="finalizer",
        observed_at=observed_at,
    )
    receipt = DeliveryObservationReceipt.create(observation)
    review = DeliveryReview(
        review_mode="finalization",
        basis_digest="e" * 64,
        observation_ids=(receipt.observation_id,),
        exact_commit="b" * 40,
        author_id="finalizer",
        reviewer_id="build-reviewer",
        evidence=("The exact head satisfies finalization authority.",),
        reviewed_at=observed_at,
    )
    carried_only = review.model_copy(update={"observation_ids": ()})
    refusals = (
        {},
        {"review": review.model_copy(update={"reviewer_id": "finalizer"}).model_dump(mode="json")},
        {
            "observations": [
                observation.model_copy(update={"observed_at": observed_at.replace(tzinfo=None)}).model_dump(mode="json")
            ]
        },
    )

    async with Client(assemble_target_server(application)) as client:  # type: ignore[arg-type]
        tool = {tool.name: tool for tool in (await client.list_tools()).tools}["derive_evidence_receipts"]
        observations = await client.call_tool(
            "derive_evidence_receipts", {"observations": [observation.model_dump(mode="json")]}
        )
        reviewed = await client.call_tool("derive_evidence_receipts", {"review": review.model_dump(mode="json")})
        carried = await client.call_tool("derive_evidence_receipts", {"review": carried_only.model_dump(mode="json")})
        refused = [await client.call_tool("derive_evidence_receipts", arguments) for arguments in refusals]

    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is True
    assert observations.structured_content == {"observations": [receipt.model_dump(mode="json")], "review": None}
    assert reviewed.structured_content == {
        "observations": [],
        "review": DeliveryReviewReceipt.create(review).model_dump(mode="json"),
    }
    assert carried.structured_content == {
        "observations": [],
        "review": DeliveryReviewReceipt.create(carried_only).model_dump(mode="json"),
    }
    for result in refused:
        assert result.is_error
        assert result.structured_content is None
        assert _registered_diagnostic(result)["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert application.calls == []


@pytest.mark.asyncio
async def test_registered_planner_retry_settlement_has_exact_client_contract(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    launch = application.acquire_actions().launch_packages[0]
    settlement = DeliveryPlanningRetrySettlement(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=launch.claim.claim_id,
        attempt_id=launch.claim.attempt_id,
        disposition="normal-return",
        request=RetryDelivery(
            action="retry",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            failure_code="worker-retry",
        ),
    )
    server = assemble_target_server(application)

    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        result = await client.call_tool(
            "settle_worker_invocation",
            {"settlement": settlement.model_dump(mode="json")},
        )

    tool = tools["settle_worker_invocation"]
    assert set(tool.input_schema["properties"]) == {"settlement", "host_id", "session_id"}
    assert tool.input_schema["additionalProperties"] is False
    settlement_schema = tool.input_schema["properties"]["settlement"]
    settlement_refs = {item["$ref"].rsplit("/", 1)[-1] for item in settlement_schema["anyOf"]}
    assert settlement_refs == {
        "DeliveryPlanningRetrySettlement",
        "DeliveryBuilderInvocationSettlement",
        "FinalizerSettlement",
    }
    definitions = tool.input_schema["$defs"]
    builder_schema = definitions["DeliveryBuilderInvocationSettlement"]
    assert {
        "change_id",
        "outcome_id",
        "claim_id",
        "attempt_id",
        "task_id",
        "expected_last_reviewed_commit",
        "disposition",
    } <= set(builder_schema["required"])
    assert {"release", "elapsed_time", "confirmed_lost"}.isdisjoint(builder_schema["properties"])
    finalizer_schema = definitions["FinalizerSettlement"]
    assert {
        "change_id",
        "attempt_id",
        "claim_id",
        "expected_head",
        "expected_reviewed_base",
        "report_id",
        "disposition",
        "outcome",
        "host_id",
        "session_id",
    } <= set(finalizer_schema["required"])
    assert {"release", "elapsed_time", "confirmed_lost"}.isdisjoint(finalizer_schema["properties"])
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.destructive_hint is False
    assert not result.is_error
    assert result.structured_content == runtimes["change-a"].show_binding("OUT-001").model_dump(mode="json")
    assert runtimes["change-a"].active_claims() == ()


@pytest.mark.asyncio
async def test_registered_settlement_accepts_ended_without_result_only_without_request(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    launch = application.acquire_actions().launch_packages[0]
    runtime = runtimes["change-a"]
    settlement = {
        "change_id": "change-a",
        "outcome_id": "OUT-001",
        "claim_id": launch.claim.claim_id,
        "attempt_id": launch.claim.attempt_id,
        "disposition": "ended-without-result",
    }
    with_request = {
        **settlement,
        "request": {"action": "retry", "outcome_id": "OUT-001", "claim_id": launch.claim.claim_id},
    }
    owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{launch.claim.attempt_id}.json"
    before = (runtime.frontier_bytes(), runtime.retry_ledger().read())

    async with Client(assemble_target_server(application)) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        refused = await client.call_tool("settle_worker_invocation", {"settlement": with_request})
        assert refused.is_error
        assert (runtime.frontier_bytes(), runtime.retry_ledger().read()) == before
        assert runtime.show_binding("OUT-001").active_claim == launch.claim
        assert not owner_result.exists()
        settled = await client.call_tool("settle_worker_invocation", {"settlement": settlement})

    definitions = tools["settle_worker_invocation"].input_schema["$defs"]
    for name in ("DeliveryPlanningRetrySettlement", "DeliveryBuilderInvocationSettlement"):
        assert "ended-without-result" in definitions[name]["properties"]["disposition"]["enum"]
        assert "request" not in definitions[name]["required"]
    assert definitions["FinalizerSettlement"]["properties"]["disposition"]["const"] == "normal-return"
    assert not settled.is_error
    assert runtime.active_claims() == ()
    assert json.loads(owner_result.read_bytes())["failure_code"] == "worker-ended-without-result"


def _stall_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _registered_diagnostic(result: Any) -> dict[str, object]:
    _prefix, marker, content = result.content[0].text.partition("{")
    assert marker, result.content[0].text
    return json.loads(marker + content)


def _stall_planning_case(tmp_path: Path) -> tuple[PortfolioApplication, Any, Any, Path, Any, datetime, list[str]]:
    start = datetime.now(UTC).replace(microsecond=0)
    now = [_stall_iso(start)]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, clock=lambda: now[0]
    )
    launch = application.acquire_actions().launch_packages[0]
    return application, runtimes["change-a"], coordinator, state_root, launch, start, now


@pytest.mark.asyncio
async def test_registered_release_stuck_worker_settles_quiet_planner_and_replays(tmp_path: Path) -> None:
    application, runtime, _coordinator, state_root, launch, start, now = _stall_planning_case(tmp_path)
    request = {
        "change_id": "change-a",
        "outcome_id": "OUT-001",
        "attempt_id": launch.claim.attempt_id,
        "claim_id": launch.claim.claim_id,
    }
    owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{launch.claim.attempt_id}.json"
    now[0] = _stall_iso(start + timedelta(minutes=10))

    async with Client(assemble_target_server(application)) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        released = await client.call_tool("release_stuck_worker", request)
        frontier = runtime.frontier_bytes()
        replayed = await client.call_tool("release_stuck_worker", request)

    tool = tools["release_stuck_worker"]
    assert set(tool.input_schema["properties"]) == {"change_id", "outcome_id", "attempt_id", "claim_id"}
    assert set(tool.input_schema["required"]) == {"change_id", "attempt_id", "claim_id"}
    assert tool.input_schema["additionalProperties"] is False
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is False
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.destructive_hint is False
    assert not released.is_error
    assert released.structured_content == runtime.show_binding("OUT-001").model_dump(mode="json")
    assert released.structured_content["active_claim"] is None
    assert json.loads(owner_result.read_bytes())["failure_code"] == "worker-released-stuck"
    assert not replayed.is_error
    assert replayed.structured_content == released.structured_content
    assert runtime.frontier_bytes() == frontier


@pytest.mark.asyncio
async def test_registered_release_stuck_worker_refuses_recent_worktree_activity_without_mutation(
    tmp_path: Path,
) -> None:
    application, runtime, coordinator, state_root, launch, start, now = _stall_planning_case(tmp_path)
    worktree = launch.worktree_path
    touched = start + timedelta(minutes=5)
    activity = worktree / "planner-notes.txt"
    activity.write_text("recent\n", encoding="utf-8")
    os.utime(activity, (touched.timestamp(), touched.timestamp()))
    now[0] = _stall_iso(touched + timedelta(seconds=10))
    owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{launch.claim.attempt_id}.json"
    before = (runtime.frontier_bytes(), runtime.retry_ledger().read(), coordinator.show("change-a"))

    async with Client(assemble_target_server(application)) as client:
        refused = await client.call_tool(
            "release_stuck_worker",
            {
                "change_id": "change-a",
                "outcome_id": "OUT-001",
                "attempt_id": launch.claim.attempt_id,
                "claim_id": launch.claim.claim_id,
            },
        )

    assert refused.is_error
    assert refused.structured_content is None
    diagnostic = _registered_diagnostic(refused)
    assert diagnostic["code"] == "ERR_DELIVERY_WORKER_ACTIVE"
    assert diagnostic["retry_safe"] is True
    assert diagnostic["current_authority_identity"] == "change-a"
    assert f"Retry at or after {_stall_iso(touched + timedelta(seconds=30))}" in diagnostic["detail"]
    assert (runtime.frontier_bytes(), runtime.retry_ledger().read(), coordinator.show("change-a")) == before
    assert runtime.show_binding("OUT-001").active_claim == launch.claim
    assert not owner_result.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_update",
    [
        {"outcome_id": "OUT-1"},
        {"attempt_id": ""},
        {"confirmed_lost": True},
        {"elapsed_time": 600},
    ],
)
async def test_registered_release_stuck_worker_sanitizes_invalid_arguments_before_effects(
    tmp_path: Path,
    request_update: dict[str, object],
) -> None:
    application, runtime, _coordinator, _state_root, launch, start, now = _stall_planning_case(tmp_path)
    now[0] = _stall_iso(start + timedelta(minutes=10))
    request = {
        "change_id": "change-a",
        "outcome_id": "OUT-001",
        "attempt_id": launch.claim.attempt_id,
        "claim_id": launch.claim.claim_id,
        **request_update,
    }
    frontier = runtime.frontier_bytes()

    async with Client(assemble_target_server(application)) as client:
        refused = await client.call_tool("release_stuck_worker", request)

    assert refused.is_error
    assert refused.content[0].text == "Error executing tool release_stuck_worker: " + json.dumps(
        {
            "code": "ERR_TARGET_PARAM_VALIDATION",
            "detail": "Invalid tool arguments. Check the tool input schema.",
            "current_authority_identity": "portfolio",
            "retry_safe": False,
        },
        separators=(",", ":"),
    )
    assert runtime.frontier_bytes() == frontier
    assert runtime.show_binding("OUT-001").active_claim == launch.claim


@pytest.mark.asyncio
@pytest.mark.parametrize("disposition", ["host-lost", "released-stuck"])
async def test_registered_settlement_rejects_engine_worker_dispositions(tmp_path: Path, disposition: str) -> None:
    application, runtime, _coordinator, state_root, launch, start, now = _stall_planning_case(tmp_path)
    now[0] = _stall_iso(start + timedelta(minutes=10))
    identity = {"change_id": "change-a", "claim_id": launch.claim.claim_id, "attempt_id": launch.claim.attempt_id}
    settlements = (
        {**identity, "outcome_id": "OUT-001", "disposition": disposition},
        {
            **identity,
            "outcome_id": "OUT-001",
            "task_id": "TASK-001",
            "expected_last_reviewed_commit": "a" * 40,
            "disposition": disposition,
        },
        {
            **identity,
            "expected_head": "a" * 40,
            "expected_reviewed_base": "a" * 40,
            "report_id": "b" * 64,
            "disposition": disposition,
            "outcome": "ended-without-report",
            "host_id": "host",
            "session_id": "session",
        },
    )
    owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{launch.claim.attempt_id}.json"
    before = (runtime.frontier_bytes(), runtime.retry_ledger().read())

    async with Client(assemble_target_server(application)) as client:
        tool = {tool.name: tool for tool in (await client.list_tools()).tools}["settle_worker_invocation"]
        results = [
            await client.call_tool("settle_worker_invocation", {"settlement": settlement}) for settlement in settlements
        ]

    for result in results:
        assert result.is_error
        assert _registered_diagnostic(result)["code"] == "ERR_TARGET_PARAM_VALIDATION"
    definitions = tool.input_schema["$defs"]
    for name in ("DeliveryPlanningRetrySettlement", "DeliveryBuilderInvocationSettlement"):
        assert disposition not in definitions[name]["properties"]["disposition"]["enum"]
    assert (runtime.frontier_bytes(), runtime.retry_ledger().read()) == before
    assert runtime.show_binding("OUT-001").active_claim == launch.claim
    assert not owner_result.exists()


async def _acquire_registered_change_action(client: Any, change_id: str, capabilities: list[str]) -> Any:
    observed = await client.call_tool("get_change", {"change_id": change_id})
    assert not observed.is_error
    assert observed.structured_content is not None
    return await client.call_tool(
        "acquire_change_action",
        {
            "change_id": change_id,
            "expected_basis": observed.structured_content["readiness"]["basis"],
            "capabilities": capabilities,
            "host_id": "host-a",
            "session_id": "session-a",
        },
    )


async def _issue_registered_finalizer_failure(
    client: Any,
    application: PortfolioApplication,
    category: str,
    code: FinalizationFailureCode,
    checks_state: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    acquired = await _acquire_registered_change_action(client, "change-a", ["finalizer"])
    assert not acquired.is_error
    assert acquired.structured_content is not None
    finalization = acquired.structured_content["finalization"]
    assert finalization is not None
    writer = finalization["attempt"]["writer"]
    report_fields: dict[str, object] = {"category": category, "code": code, "checks_state": checks_state}
    if category == "custody-preflight":
        report_fields["expected_workspace_fingerprint"] = finalization["context"]["readiness"]["basis"][
            "workspace_fingerprint"
        ]
    reported = await client.call_tool(
        "report_finalization_failure",
        _failure_request(application, attempt_key=writer["attempt_id"], **report_fields).model_dump(mode="json"),
    )
    assert not reported.is_error
    assert reported.structured_content is not None
    report = reported.structured_content
    assert report["request"]["code"] == code.value
    assert report["request"]["checks_state"] == checks_state
    return finalization, report


def _finalizer_settlement_request(
    finalization: dict[str, Any], report: dict[str, Any], outcome: str
) -> dict[str, object]:
    attempt = finalization["attempt"]
    writer = attempt["writer"]
    return {
        "change_id": finalization["context"]["change_id"],
        "attempt_id": writer["attempt_id"],
        "claim_id": writer["claim_id"],
        "expected_head": attempt["exact_head"],
        "expected_reviewed_base": finalization["context"]["reviewed_change_head"],
        "report_id": report["report_id"],
        "disposition": "normal-return",
        "outcome": outcome,
        "host_id": writer["actor_id"],
        "session_id": writer["process_id"],
    }


async def _assert_invalid_finalizer_settlements_are_read_only(
    client: Any,
    application: PortfolioApplication,
    state_root: Path,
    settlement: dict[str, object],
) -> None:
    report_store = FinalizationReportStore(state_root, "change-a")
    before_state = _loader_activation_state_snapshot(application)
    before_reports = report_store.read()
    report_id = settlement["report_id"]
    forged_report = "0" * 64 if report_id != "0" * 64 else "f" * 64
    invalid_calls = (
        ({"settlement": {**settlement, "report_id": forged_report}}, (forged_report,)),
        ({"settlement": {**settlement, "host_id": "foreign-host"}}, ("foreign-host",)),
        (
            {"settlement": {**settlement, "private_value": "synthetic-private-token"}},
            ("synthetic-private-token",),
        ),
        ({"settlement": settlement, "host_id": "outer-host-shadow"}, ("outer-host-shadow",)),
    )
    for arguments, rejected_values in invalid_calls:
        refused = await client.call_tool("settle_worker_invocation", arguments)
        assert refused.is_error
        assert all(value not in refused.content[0].text for value in rejected_values)
        assert _loader_activation_state_snapshot(application) == before_state
        assert report_store.read() == before_reports
        receipt_path = (
            state_root
            / "finalizer-settlements/change-a"
            / (f"{hashlib.sha256(str(settlement['attempt_id']).encode('utf-8')).hexdigest()}.json")
        )
        assert not receipt_path.exists()


def _assert_finalizer_workspace_and_report_unchanged(
    application: PortfolioApplication,
    report_store: FinalizationReportStore,
    before_state: dict[str, Any],
    before_reports: Any,
) -> None:
    after_state = _loader_activation_state_snapshot(application)
    assert after_state["repository_refs"] == before_state["repository_refs"]
    before_workspaces = {change_id: state["workspace"] for change_id, state in before_state["changes"].items()}
    after_workspaces = {change_id: state["workspace"] for change_id, state in after_state["changes"].items()}
    assert after_workspaces == before_workspaces
    assert report_store.read() == before_reports


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("category", "code", "checks_state", "expected_outcome"),
    [
        ("maintained-check", FinalizationFailureCode.MAINTAINED_CHECK_FAILED, "failed", "proof-failed"),
        ("custody-preflight", FinalizationFailureCode.WORKSPACE_PREFLIGHT_FAILED, "not-run", "proof-failed"),
        ("independent-review", FinalizationFailureCode.INDEPENDENT_REVIEW_FAILED, "failed", "review-failed"),
    ],
)
async def test_registered_finalizer_failure_settlement_releases_capacity_with_exact_report(
    tmp_path: Path,
    category: str,
    code: FinalizationFailureCode,
    checks_state: str,
    expected_outcome: str,
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
    )
    report_store = FinalizationReportStore(state_root, "change-a")
    async with Client(assemble_target_server(application)) as client:
        finalization, report = await _issue_registered_finalizer_failure(
            client, application, category, code, checks_state
        )
        settlement = _finalizer_settlement_request(finalization, report, expected_outcome)
        waiting = await _acquire_registered_change_action(client, "change-b", ["planner"])
        assert not waiting.is_error
        assert waiting.structured_content["kind"] == "waiting"
        assert waiting.structured_content["reason_code"] == "execution-capacity"

        before_state = _loader_activation_state_snapshot(application)
        before_reports = report_store.read()
        settled = await client.call_tool("settle_worker_invocation", {"settlement": settlement})
        assert not settled.is_error, settled.content[0].text
        receipt = settled.structured_content
        assert receipt is not None
        assert receipt["settlement"] == settlement
        assert receipt["report"]["report_id"] == report["report_id"]
        assert receipt["report"]["request"]["checks_state"] == checks_state

        coordination = coordinator.show("change-a")
        attention = coordination.finalization_attention
        assert attention is not None
        assert attention.receipt_id == receipt["receipt_id"]
        assert attention.report_id == report["report_id"]
        assert coordination.writer.kind == "finalization-attention"
        assert coordination.finalization_attempt.writer.attempt_id == settlement["attempt_id"]
        assert coordination.finalization_attempt.finished_at == receipt["finished_at"]
        assert runtimes["change-a"].finalization() is None

        _assert_finalizer_workspace_and_report_unchanged(application, report_store, before_state, before_reports)
        assert len(before_reports.reports) == 1
        owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{settlement['attempt_id']}.json"
        owner_result_bytes = owner_result.read_bytes()
        assert json.loads(owner_result_bytes)["observed_at"] == report["observed_at"]

        replayed = await client.call_tool("settle_worker_invocation", {"settlement": settlement})
        assert not replayed.is_error
        assert replayed.structured_content == receipt
        assert owner_result.read_bytes() == owner_result_bytes
        next_change = await _acquire_registered_change_action(client, "change-b", ["planner"])

    assert not next_change.is_error
    assert next_change.structured_content["kind"] == "acquired"
    assert next_change.structured_content["launch"]["change_id"] == "change-b"


@pytest.mark.asyncio
async def test_registered_finalizer_settlement_rejects_invalid_identity_and_schema_before_effects(
    tmp_path: Path,
) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
    )
    async with Client(assemble_target_server(application)) as client:
        finalization, report = await _issue_registered_finalizer_failure(
            client,
            application,
            "maintained-check",
            FinalizationFailureCode.MAINTAINED_CHECK_FAILED,
            "failed",
        )
        settlement = _finalizer_settlement_request(finalization, report, "proof-failed")
        await _assert_invalid_finalizer_settlements_are_read_only(client, application, state_root, settlement)
        waiting = await _acquire_registered_change_action(client, "change-b", ["planner"])

    assert not waiting.is_error
    assert waiting.structured_content["kind"] == "waiting"
    assert waiting.structured_content["reason_code"] == "execution-capacity"


@pytest.mark.asyncio
async def test_registered_builder_retry_settlement_reacquires_same_task_and_preserves_dirty_workspace(
    tmp_path: Path,
) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, _state_root, first, _branch_head, before_workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    assert isinstance(settlement, DeliveryBuilderInvocationSettlement)

    async with Client(assemble_target_server(application)) as client:
        settled = await client.call_tool(
            "settle_worker_invocation",
            {
                "settlement": settlement.model_dump(mode="json"),
                "host_id": first.claim.owner_id,
                "session_id": first.claim.process_id,
            },
        )
        assert not settled.is_error
        assert settled.structured_content is not None
        handoff = settled.structured_content["builder_handoff_context"]
        assert handoff["original_task_id"] == first.task_id
        assert handoff["route"] == "same-task"
        assert handoff["last_reviewed_commit"] == first.last_reviewed_commit
        serialized = json.dumps(settled.structured_content, sort_keys=True)
        assert len(json.dumps(handoff, sort_keys=True)) < 1024
        assert all(
            content not in serialized
            for content in (
                "committed Builder work",
                "staged Builder work",
                "unstaged Builder work",
                "untracked Builder work",
            )
        )
        assert runtime.active_claims() == ()
        assert coordinator.show("change-a").builder_handoff is not None
        assert _workspace_content_snapshot(first.worktree_path) == before_workspace

        now[0] = "2026-08-04T01:00:00Z"
        resumed = None
        for _ in range(3):
            request = _continuation_request(application, "change-a")
            resumed = await client.call_tool("acquire_change_action", request.model_dump(mode="json"))
            if resumed.structured_content is None or resumed.structured_content["kind"] != "reconciled":
                break

    assert resumed is not None
    assert not resumed.is_error
    assert resumed.structured_content is not None
    assert resumed.structured_content["kind"] == "acquired"
    launch = resumed.structured_content["launch"]
    assert launch["task_id"] == first.task_id
    assert launch["claim"]["task_id"] == first.task_id
    assert launch["claim"]["attempt_id"] != first.claim.attempt_id
    assert launch["claim"]["claim_id"] != first.claim.claim_id
    assert launch["builder_handoff_context"] == handoff
    assert coordinator.show("change-a").builder_handoff is None
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace


@pytest.mark.asyncio
async def test_registered_builder_block_request_releases_capacity_without_resuming_claim(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, _state_root, first, branch_head, before_workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    request = DeliveryRequest(
        request_id="builder-pause-decision",
        kind=DeliveryRequestKind.DECISION,
        outcome_id=first.outcome_id,
        summary="Choose whether this Builder task may resume.",
        options=(DeliveryRequestOption(option_id="resume", label="Resume"),),
    )
    block = BlockDelivery(
        action="block",
        outcome_id=first.outcome_id,
        claim_id=first.claim.claim_id,
        block_id="builder-pause",
        reason="The Builder needs a user decision.",
        unblock_condition="The user decision is recorded.",
        expected_evidence=("A confirmed decision.",),
        locators=(first.task_id,),
        resume_commit=branch_head,
        request=request,
    )
    settlement = settlement.model_copy(update={"request": block})

    async with Client(assemble_target_server(application)) as client:
        paused = await client.call_tool(
            "settle_worker_invocation",
            {
                "settlement": settlement.model_dump(mode="json"),
                "host_id": first.claim.owner_id,
                "session_id": first.claim.process_id,
            },
        )
        assert not paused.is_error
        assert paused.structured_content is not None
        assert paused.structured_content["active_claim"] is None
        assert paused.structured_content["requests"][0]["request_id"] == request.request_id
        assert paused.structured_content["requests"][0]["resolution"] is None
        assert paused.structured_content["block"]["resolution_note"] is None
        assert runtime.active_claims() == ()
        assert coordinator.show("change-a").builder_handoff is not None
        assert _workspace_content_snapshot(first.worktree_path) == before_workspace

        sibling_request = _continuation_request(application, "change-b")
        sibling = await client.call_tool("acquire_change_action", sibling_request.model_dump(mode="json"))

    assert not sibling.is_error
    assert sibling.structured_content is not None
    assert sibling.structured_content["kind"] == "acquired"
    assert sibling.structured_content["launch"]["change_id"] == "change-b"
    assert sibling.structured_content["launch"]["claim"]["worker_role"] == "planner"
    assert runtime.active_claims() == ()
    assert _workspace_content_snapshot(first.worktree_path) == before_workspace


@pytest.mark.asyncio
async def test_registered_builder_settlement_rejects_invalid_envelopes_without_mutation(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, state_root, first, _branch_head, _workspace, settlement = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    coordination_path = state_root / "coordination/changes/change-a.json"
    before = (
        runtime.frontier_bytes(),
        runtime.retry_ledger().read(),
        coordinator.show("change-a"),
        coordination_path.read_bytes(),
        _workspace_content_snapshot(first.worktree_path),
    )
    base = settlement.model_dump(mode="json")
    foreign_task = {**base, "task_id": "TASK-FOREIGN"}
    foreign_attempt = {**base, "attempt_id": "foreign-attempt"}
    foreign_reviewed_base = {**base, "expected_last_reviewed_commit": "a" * 40}
    invalid_calls = [
        (base, "foreign-host", first.claim.process_id),
        (base, first.claim.owner_id, "foreign-session"),
        (foreign_task, first.claim.owner_id, first.claim.process_id),
        (foreign_attempt, first.claim.owner_id, first.claim.process_id),
        (foreign_reviewed_base, first.claim.owner_id, first.claim.process_id),
        *(
            ({**base, field: value}, first.claim.owner_id, first.claim.process_id)
            for field, value in (
                ("private_value", "must-not-appear"),
                ("release", True),
                ("elapsed_time", 1.0),
                ("confirmed_lost", True),
            )
        ),
    ]

    async with Client(assemble_target_server(application)) as client:
        for envelope, host_id, session_id in invalid_calls:
            result = await client.call_tool(
                "settle_worker_invocation",
                {"settlement": envelope, "host_id": host_id, "session_id": session_id},
            )
            assert result.is_error
            assert "must-not-appear" not in result.content[0].text
            assert (
                runtime.frontier_bytes(),
                runtime.retry_ledger().read(),
                coordinator.show("change-a"),
                coordination_path.read_bytes(),
                _workspace_content_snapshot(first.worktree_path),
            ) == before


@pytest.mark.asyncio
async def test_registered_planner_settlement_preserves_wrong_continuation_identity(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    acquired = application.acquire_change_action(
        DeliveryContinuationRequest(
            change_id="change-a",
            expected_basis=application.get_change("change-a").readiness.basis,
            capabilities=("planner",),
            host_id="host-a",
            session_id="session-a",
        )
    )
    assert acquired.launch is not None
    claim = acquired.launch.claim
    settlement = DeliveryPlanningRetrySettlement(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        attempt_id=claim.attempt_id,
        disposition="normal-return",
        request=RetryDelivery(action="retry", outcome_id="OUT-001", claim_id=claim.claim_id),
    )
    runtime = runtimes["change-a"]
    frontier = runtime.frontier_bytes()
    accounting = runtime.retry_ledger().read()
    owner_result = state_root / "changes/change-a/retry-ledger/owner-results" / f"{claim.attempt_id}.json"
    async with Client(assemble_target_server(application)) as client:
        refused = await client.call_tool(
            "settle_worker_invocation",
            {"settlement": settlement.model_dump(mode="json"), "host_id": "host-a", "session_id": "session-b"},
        )
        assert refused.is_error
        assert runtime.frontier_bytes() == frontier
        assert runtime.retry_ledger().read() == accounting
        assert runtime.show_binding("OUT-001").active_claim == claim
        assert not owner_result.exists()
        settled = await client.call_tool(
            "settle_worker_invocation",
            {"settlement": settlement.model_dump(mode="json"), "host_id": "host-a", "session_id": "session-a"},
        )
    assert not settled.is_error
    assert runtime.active_claims() == ()
    assert owner_result.exists()


@pytest.mark.asyncio
async def test_registered_planner_settlement_rejects_unknown_fields_before_delegation() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    settlement = {
        "change_id": "change-a",
        "outcome_id": "OUT-001",
        "claim_id": "claim",
        "attempt_id": "attempt",
        "disposition": "normal-return",
        "request": {
            "action": "retry",
            "outcome_id": "OUT-001",
            "claim_id": "claim",
            "failure_code": "worker-retry",
        },
        "private_value": "must-not-appear",
    }

    async with Client(server) as client:
        result = await client.call_tool("settle_worker_invocation", {"settlement": settlement})

    assert result.is_error
    assert application.calls == []
    assert result.content[0].text == (
        "Error executing tool settle_worker_invocation: "
        + json.dumps(
            {
                "code": "ERR_TARGET_PARAM_VALIDATION",
                "detail": "Invalid tool arguments. Check the tool input schema.",
                "current_authority_identity": "portfolio",
                "retry_safe": False,
            },
            separators=(",", ":"),
        )
    )
    assert "must-not-appear" not in result.content[0].text


@pytest.mark.asyncio
async def test_registered_finalization_failure_schema_exposes_proof_diagnostics() -> None:
    server = assemble_target_server(_RecordingApplication())  # type: ignore[arg-type]

    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    schema = tools["report_finalization_failure"].input_schema
    properties = schema["properties"]
    assert set(properties) >= {
        "procedure_id",
        "proof_fingerprint_before",
        "proof_fingerprint_after",
    }
    assert "proof-mutation" in properties["category"]["enum"]
    assert "proof-mutated-worktree" in schema["$defs"]["FinalizationFailureCode"]["enum"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("list_work_items", {"unexpected": True}),
        (
            "repair",
            {
                "change_id": "change-a",
                "proposal_id": "a" * 64,
                "preservation_paths": ["synthetic-private-token"],
            },
        ),
        ("repair", {"change_id": ["/synthetic/private/path", "synthetic-private-token"]}),
        ("repair", {"change_id": "/synthetic/private/path"}),
        ("repair", {"change_id": "change-a", "confirmed_lost": "synthetic-private-token"}),
        ("acquire_actions", {"selection": "synthetic-private-token"}),
        (
            "acquire_actions",
            {
                "selection": {
                    "change_id": "change-a",
                    "outcome_id": "OUT-001",
                    "expected_stage": "synthetic-private-token",
                    "expected_frontier_digest": "a" * 64,
                    "expected_source_head": "b" * 40,
                },
            },
        ),
        (
            "acquire_actions",
            {
                "selection": {
                    "change_id": "change-a",
                    "outcome_id": "OUT-001",
                    "expected_stage": "planning",
                    "expected_frontier_digest": "a" * 64,
                    "expected_source_head": "b" * 40,
                    "/synthetic/private/path": "synthetic-private-token",
                },
            },
        ),
    ],
)
async def test_registered_validation_rejects_private_arguments_before_delegation(
    tool_name: str,
    arguments: dict[str, object],
) -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error
    assert application.calls == []
    diagnostic = {
        "code": "ERR_TARGET_PARAM_VALIDATION",
        "detail": "Invalid tool arguments. Check the tool input schema.",
        "current_authority_identity": "portfolio",
        "retry_safe": False,
    }
    assert len(result.content) == 1
    assert result.content[0].text == (
        f"Error executing tool {tool_name}: " + json.dumps(diagnostic, separators=(",", ":"))
    )
    assert result.structured_content is None


@pytest.mark.asyncio
async def test_registered_model_validation_hides_cross_field_input_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    sdk_logger = logging.getLogger("mcp.server.mcpserver.server")
    caplog.set_level(logging.ERROR, logger=sdk_logger.name)
    sdk_logger.addHandler(caplog.handler)
    try:
        async with Client(server) as client:
            result = await client.call_tool(
                "set_change_intent",
                {
                    "change_id": "change-a",
                    "kind": "resume",
                    "expected_frontier_digest": "a" * 64,
                    "reason": "secret42",
                },
            )
    finally:
        sdk_logger.removeHandler(caplog.handler)

    diagnostic = {
        "code": "ERR_TARGET_PARAM_VALIDATION",
        "detail": "Invalid tool arguments. Check the tool input schema.",
        "current_authority_identity": "portfolio",
        "retry_safe": False,
    }
    assert result.is_error
    assert application.calls == []
    assert len(result.content) == 1
    assert result.content[0].text == (
        "Error executing tool set_change_intent: " + json.dumps(diagnostic, separators=(",", ":"))
    )
    assert result.structured_content is None
    assert "secret42" not in result.content[0].text
    assert "secret42" not in caplog.text
    assert "Traceback (most recent call last)" not in caplog.text


@pytest.mark.asyncio
async def test_registered_continuation_forwards_exact_change_and_engine_operation() -> None:
    application = _ContinuationApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    basis = {
        "contract_digest": "a" * 64,
        "frontier_digest": "a" * 64,
        "source_head": "b" * 40,
        "target_head": None,
        "continuation_id": None,
    }

    async with Client(server) as client:
        acquired = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "host",
                "session_id": "session",
            },
        )
        executed = await client.call_tool(
            "execute_change_action",
            {"change_id": "change-a", "operation_id": CONTINUATION_ID},
        )

    assert not acquired.is_error
    assert not executed.is_error
    assert acquired.structured_content is not None
    assert acquired.structured_content["kind"] == "acquired"
    assert acquired.structured_content["engine_action"]["operation_id"] == CONTINUATION_ID
    assert acquired.structured_content["readiness"]["basis"]["continuation_id"] == CONTINUATION_ID
    assert executed.structured_content is not None
    assert executed.structured_content["kind"] == "completed"
    assert executed.structured_content["action"]["operation_id"] == CONTINUATION_ID
    assert application.calls == ["acquire_change_action", "execute_change_action"]
    request, execution = application.requests
    assert isinstance(request, DeliveryContinuationRequest)
    assert request.change_id == "change-a"
    assert request.capabilities == ("engine",)
    assert request.expected_basis.target_head is None
    assert request.expected_basis.continuation_id is None
    assert isinstance(execution, ExecuteDeliveryChangeAction)
    assert execution.operation_id == CONTINUATION_ID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("change_id", "kind", "reason_code"),
    [
        ("change-waiting", "waiting", "host-capability-unavailable"),
        ("change-stale", "stale", "readiness-changed"),
        ("change-human", "human", "merge-approval-required"),
        ("change-busy", "busy", "operation-in-progress"),
    ],
)
async def test_registered_continuation_forwards_non_acquired_envelopes_without_a_retry_loop(
    change_id: str,
    kind: str,
    reason_code: str,
) -> None:
    application = _ContinuationApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    basis = {"contract_digest": "a" * 64, "frontier_digest": "a" * 64}

    async with Client(server) as client:
        result = await client.call_tool(
            "acquire_change_action",
            {
                "change_id": change_id,
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "host",
                "session_id": "session",
            },
        )

    assert not result.is_error
    payload = result.structured_content
    assert payload is not None
    assert payload["kind"] == kind
    assert payload["reason_code"] == reason_code
    assert payload["launch"] is None
    assert payload["finalization"] is None
    assert payload["engine_action"] is None
    assert payload["engine_result"] is None
    assert payload["failure"] is None
    assert payload["readiness"]["basis"]["continuation_id"] == CONTINUATION_ID
    assert application.calls == ["acquire_change_action"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("acquire_change_action", {"change_id": "change-a", "capabilities": ["engine"]}),
        (
            "acquire_change_action",
            {
                "change_id": "change-a",
                "expected_basis": {"contract_digest": "a" * 64},
                "capabilities": [],
                "host_id": "host",
                "session_id": "session",
            },
        ),
        ("execute_change_action", {"change_id": "change-a", "operation_id": "not-a-continuation"}),
        (
            "execute_change_action",
            {"change_id": "change-a", "operation_id": CONTINUATION_ID, "confirmed_success": True},
        ),
        (
            "execute_change_action",
            {"change_id": "change-a", "operation_id": CONTINUATION_ID, "commands": ["git status"]},
        ),
        (
            "execute_change_action",
            {"change_id": "change-a", "operation_id": CONTINUATION_ID, "budget": 1},
        ),
        (
            "execute_change_action",
            {"change_id": "change-a", "operation_id": CONTINUATION_ID, "receipt": {"success": True}},
        ),
        (
            "execute_change_action",
            {"change_id": "change-a", "operation_id": CONTINUATION_ID, "stop_assertion": True},
        ),
    ],
)
async def test_registered_continuation_rejects_invalid_or_caller_authored_effects(
    tool_name: str,
    arguments: dict[str, object],
) -> None:
    application = _ContinuationApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error
    assert application.calls == []


@pytest.mark.asyncio
async def test_registered_acquisition_rejects_incomplete_selection_without_delegation() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        result = await client.call_tool("acquire_actions", {"selection": {"change_id": "change-a"}})

    assert result.is_error
    assert application.calls == []


@pytest.mark.asyncio
async def test_registered_acquisition_accepts_selected_planning_request() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        result = await client.call_tool(
            "acquire_actions",
            {
                "selection": {
                    "change_id": "change-a",
                    "outcome_id": "OUT-001",
                    "expected_stage": "planning",
                    "expected_frontier_digest": "a" * 64,
                    "expected_source_head": "b" * 40,
                },
            },
        )

    assert not result.is_error
    assert result.structured_content == {"operation": "acquire_actions"}
    assert application.calls == ["acquire_actions"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"expected_stage": "completed"},
        {"expected_stage": "implementation"},
        {"expected_task_id": "TASK-001"},
        {"unknown": "value"},
        {"expected_frontier_digest": "wrong"},
    ],
)
async def test_registered_acquisition_rejects_invalid_selection(changes: dict[str, object]) -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    selection = {
        "change_id": "change-a",
        "outcome_id": "OUT-001",
        "expected_stage": "planning",
        "expected_frontier_digest": "a" * 64,
        "expected_source_head": "b" * 40,
        **changes,
    }

    async with Client(server) as client:
        result = await client.call_tool("acquire_actions", {"selection": selection})

    assert result.is_error
    assert application.calls == []


@pytest.mark.asyncio
async def test_registered_acquisition_accepts_selected_builder_request() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        result = await client.call_tool(
            "acquire_actions",
            {
                "selection": {
                    "change_id": "change-a",
                    "outcome_id": "OUT-001",
                    "expected_stage": "implementation",
                    "expected_task_id": "TASK-001",
                    "expected_frontier_digest": "a" * 64,
                    "expected_source_head": "b" * 40,
                },
            },
        )

    assert not result.is_error
    assert application.calls == ["acquire_actions"]


@pytest.mark.asyncio
async def test_work_item_view_tool_delegates_exact_publication_key() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        result = await client.call_tool(
            "show_work_item_view",
            {"change_id": "change-a", "item_key": "publication"},
        )

    assert result.structured_content == {"operation": "show_work_item_view"}
    assert application.calls == ["show_work_item_view"]


@pytest.mark.asyncio
async def test_registered_review_repair_tool_invokes_strict_adapter_once() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        result = await client.call_tool("prepare_review_repair", {"change_id": "change-a"})

    assert result.structured_content == {"operation": "prepare_review_repair"}
    assert application.calls == ["prepare_review_repair"]


@pytest.mark.asyncio
async def test_target_sync_conflict_tools_have_exact_contract() -> None:
    application = _PublicationApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    conflict_request = tools["abort_target_sync_conflict"].input_schema
    assert set(conflict_request["properties"]) == {
        "change_id",
        "expected_disposition_id",
        "target_head",
        "operation_id",
    }
    assert {
        "receipt_id",
        "operation_id",
        "change_id",
        "target_head",
        "restored_head",
    } <= set(tools["abort_target_sync_conflict"].output_schema["required"])
    assert {
        "receipt_id",
        "operation_id",
        "change_id",
        "target_branch",
        "expected_target",
        "target_head",
        "change_head_before",
        "merged_head",
        "merge_commit",
    } <= set(tools["resolve_target_sync_conflict"].output_schema["required"])
    assert "integration_target" not in tools["resolve_target_sync_conflict"].output_schema["properties"]
    repair_request = tools["repair_target_sync_publication"].input_schema
    assert set(repair_request["properties"]) == {
        "change_id",
        "confirmed_repair",
        "expected_remote_head",
        "expected_merged_head",
        "target_sync_operation_id",
        "operation_id",
    }
    assert {
        "receipt_id",
        "operation_id",
        "change_id",
        "target_sync_operation_id",
        "target_branch",
        "target_head",
        "expected_remote_head",
        "repaired_head",
        "review_required",
    } <= set(tools["repair_target_sync_publication"].output_schema["required"])


@pytest.mark.asyncio
async def test_stale_writer_capacity_fails_with_extra_forbidden_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    config_path = repository / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    _write_config(config_path, _config())
    host_path = repository / ".owlbear/delivery/runtime/host.json"
    host_path.parent.mkdir(parents=True)
    host_path.write_text('{"schema_version": 1, "writer_capacity": 1}', encoding="utf-8")
    monkeypatch.chdir(repository)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    diagnostic = exc_info.value
    assert diagnostic.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert diagnostic.field == "writer_capacity"
    assert diagnostic.retry_safe is False
    assert "host.json" in diagnostic.detail
    assert isinstance(diagnostic.__cause__, Exception)
    assert isinstance(diagnostic.__cause__.__cause__, ValidationError)
    assert diagnostic.__cause__.__cause__.errors()[0]["type"] == "extra_forbidden"
    assert not (repository / ".owlbear/delivery/target").exists()


@pytest.mark.asyncio
async def test_external_head_adoption_tool_has_exact_contract() -> None:
    application = _PublicationApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    adoption_schema = tools["adopt_external_head"].input_schema
    adoption_request = adoption_schema
    assert set(adoption_request["properties"]) == {"change_id", "expected_head", "adopted_head", "operation_id"}
    assert {
        "receipt_id",
        "operation_id",
        "change_id",
        "branch",
        "expected_head",
        "adopted_head",
        "provenance",
    } <= set(tools["adopt_external_head"].output_schema["required"])


@pytest.mark.asyncio
async def test_external_head_promotion_tool_has_exact_contract() -> None:
    application = _PublicationApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]

    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    promotion_schema = tools["promote_external_head"].input_schema
    promotion_request = promotion_schema
    assert set(promotion_request["properties"]) == {"change_id", "expected_head", "operation_id"}
    assert {
        "receipt_id",
        "operation_id",
        "change_id",
        "branch",
        "adoption_receipt_id",
        "promoted_head",
        "provenance",
    } <= set(tools["promote_external_head"].output_schema["required"])


@pytest.mark.asyncio
async def test_acceptance_observation_yields_the_mcp_event_loop() -> None:
    started = threading.Event()
    release = threading.Event()
    fallback_release = threading.Timer(1, release.set)
    fallback_release.start()
    adapter = TargetMCPAdapter(_BlockingAcceptanceApplication(started, release))  # type: ignore[arg-type]
    launched_at = time.monotonic()

    task = asyncio.create_task(adapter.observe_acceptance({"change_id": "change-a"}))
    assert await asyncio.to_thread(started.wait, 2)
    elapsed = time.monotonic() - launched_at
    release.set()
    result = await task
    fallback_release.cancel()

    assert elapsed < 0.5
    assert result == {"operation": "observe_acceptance"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation_name", "payload"),
    [
        (
            "admit_delivery_change",
            {"change_id": "change-a", "expected_package_id": "a" * 64, "active_claim_ids": []},
        ),
        ("acquire_actions", {}),
    ],
)
async def test_foundational_operations_yield_to_independent_health_requests(
    operation_name: str,
    payload: dict[str, object],
) -> None:
    started = threading.Event()
    release = threading.Event()
    application = _BlockingFoundationalApplication(operation_name, started, release)
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]

    task = asyncio.create_task(getattr(adapter, operation_name)(payload))
    assert await asyncio.to_thread(started.wait, 2)
    try:
        health = await asyncio.wait_for(adapter.delivery_health({}), timeout=0.5)
    finally:
        release.set()
    result = await task

    assert health.status is DeliveryHealthStatus.HEALTHY
    assert result == {"operation": operation_name}
    assert application.calls == [operation_name, "delivery_health"]


@pytest.mark.asyncio
async def test_cancelled_admission_is_reconciled_without_a_blind_retry() -> None:
    started = threading.Event()
    release = threading.Event()
    application = _BlockingFoundationalApplication("admit_delivery_change", started, release)
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]
    request = {"change_id": "change-a", "expected_package_id": "a" * 64, "active_claim_ids": []}

    task = asyncio.create_task(adapter.admit_delivery_change(request))
    assert await asyncio.to_thread(started.wait, 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    release.set()
    assert await asyncio.to_thread(application.completed.wait, 2)
    health = await adapter.delivery_health({})

    assert health.status is DeliveryHealthStatus.HEALTHY
    assert application.health_observations == [1]
    assert application.mutation_count == 1
    assert application.calls == ["admit_delivery_change", "delivery_health"]


MISSING_FIELDS = [
    ("schema_version",),
    ("remote",),
    ("target_branch",),
    ("github_repository",),
]


@pytest.mark.parametrize("field_path", MISSING_FIELDS)
def test_missing_required_config_fails_unconfigured_before_state_creation(
    tmp_path: Path,
    field_path: tuple[str, ...],
) -> None:
    content = _config()
    parent = content
    for key in field_path[:-1]:
        parent = parent[key]  # type: ignore[assignment,index]
    del parent[field_path[-1]]  # type: ignore[arg-type,index]
    path = tmp_path / "delivery.json"
    _write_config(path, content)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_config(path)

    diagnostic = exc_info.value
    assert diagnostic.code == "ERR_DELIVERY_STARTUP_UNCONFIGURED"
    assert diagnostic.field == ".".join(field_path)
    assert diagnostic.retry_safe is False
    assert not (tmp_path / "target").exists()


@pytest.mark.asyncio
async def test_missing_canonical_config_fails_before_state_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_UNCONFIGURED"
    assert exc_info.value.field == ".owlbear/delivery/config.json"
    assert not (tmp_path / ".owlbear/target").exists()


@pytest.mark.parametrize(
    ("mutation", "field"),
    [
        (lambda content, _tmp: content.update(remote=""), "remote"),
        (lambda content, _tmp: content.update(target_branch=""), "target_branch"),
        (lambda content, _tmp: content.update(github_repository="invalid"), "github_repository"),
        (lambda content, _tmp: content.update(execution_capacity=2), "execution_capacity"),
    ],
)
def test_invalid_config_fails_before_state_creation(
    tmp_path: Path,
    mutation: Any,
    field: str,
) -> None:
    content = _config()
    mutation(content, tmp_path)
    path = tmp_path / "delivery.json"
    _write_config(path, content)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_config(path)

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert exc_info.value.field == field
    assert exc_info.value.retry_safe is False
    assert not (tmp_path / "target").exists()


def test_malformed_json_fails_invalid_without_exposing_content(tmp_path: Path) -> None:
    path = tmp_path / "delivery.json"
    path.write_text('{"secret": "do-not-report"', encoding="utf-8")

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_config(path)

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert exc_info.value.field == ".owlbear/delivery/config.json"
    assert "do-not-report" not in str(exc_info.value)


def test_invalid_target_branch_fails_before_owner_state_mutation(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    content = _config()
    content["target_branch"] = "bad target"
    path = tmp_path / "delivery.json"
    _write_config(path, content)
    config = load_delivery_config(path)
    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_application(config, repository)

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert exc_info.value.field == "target_branch"
    assert not (tmp_path / "target").exists()


def test_startup_uses_remote_tracking_target_without_local_target_branch(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _git(repository, "checkout", "--detach", "HEAD")
    _git(repository, "branch", "-D", "main")
    path = tmp_path / "delivery.json"
    _write_config(path, _config())

    application = load_delivery_application(load_delivery_config(path), repository)

    assert isinstance(application, PortfolioApplication)


def test_missing_remote_tracking_target_fails_before_owner_state_mutation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _git(repository, "update-ref", "-d", "refs/remotes/origin/main")
    path = tmp_path / "delivery.json"
    _write_config(path, _config())

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_application(load_delivery_config(path), repository)

    assert exc_info.value.field == "target_branch"
    assert not (tmp_path / "target").exists()


def test_github_repository_mismatch_fails_before_owner_state_mutation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    content = _config()
    content["github_repository"] = "other/project"
    path = tmp_path / "delivery.json"
    _write_config(path, content)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_application(load_delivery_config(path), repository)

    assert exc_info.value.field == "github_repository"
    assert not (tmp_path / "target").exists()


@pytest.mark.asyncio
async def test_complete_config_constructs_application_before_lifespan_yield(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    _write_config(path, _config())
    monkeypatch.chdir(repository)
    async with app_lifespan(mcp) as context:
        tools = {tool.name: tool for tool in await mcp.list_tools()}
        assert isinstance(context.application, PortfolioApplication)
        assert context.application._issuer_window == WindowHostIdentity.capture()  # noqa: SLF001
        assert set(tools) == DELIVERY_TOOLS
        assert not (repository / ".owlbear/delivery/runtime/capacity.json").exists()

    with pytest.raises(RuntimeError, match="outside server lifespan"):
        live_server._live_application()  # noqa: SLF001


@pytest.mark.parametrize(
    ("version", "refusal"),
    [(3, "state-newer-than-controller"), (1, "state-version-unknown")],
)
def test_unsupported_config_version_is_refused_before_typed_parse(tmp_path: Path, version: int, refusal: str) -> None:
    content = {**_config(), "schema_version": version, "future_field": True}
    path = tmp_path / "delivery.json"
    _write_config(path, content)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_config(path)

    assert exc_info.value.code == "ERR_DELIVERY_STATE_VERSION"
    assert exc_info.value.field == "state_version"
    assert exc_info.value.detail.startswith(refusal)
    assert exc_info.value.__cause__ is not None
    assert not isinstance(exc_info.value.__cause__, ValidationError)


@pytest.mark.asyncio
async def test_lifespan_refuses_newer_state_with_typed_detail_and_releases_the_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    _write_config(path, _config())
    frontier = repository / ".owlbear/delivery/runtime/changes/change-a/frontier.json"
    frontier.parent.mkdir(parents=True)
    frontier.write_text('{"schema_version": 20, "bindings": []}', encoding="utf-8")
    monkeypatch.chdir(repository)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    assert exc_info.value.code == "ERR_DELIVERY_STATE_VERSION"
    assert exc_info.value.field == "state_version"
    assert exc_info.value.detail.startswith("state-newer-than-controller")
    assert "runtime/changes/change-a/frontier.json" in exc_info.value.detail
    acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True).release()


def test_entry_point_prints_one_refusal_line_for_newer_state_format(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    _write_config(path, _config())
    runtime_root = repository / ".owlbear/delivery/runtime"
    runtime_root.mkdir()
    runtime_root.joinpath("format.json").write_bytes(format_marker_bytes(5))

    completed = subprocess.run(
        (sys.executable, "-m", "owlbear_delivery_mcp"),
        cwd=repository,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode == 1
    lines = completed.stderr.splitlines()
    assert len(lines) == 1, completed.stderr
    assert lines[0].startswith(
        "Delivery MCP refused to start: ERR_DELIVERY_STATE_VERSION: state-newer-than-controller: "
    )
    assert lines[0].endswith("(field=state_version, retry_safe=false)")
    assert "Traceback" not in completed.stderr
    assert completed.stdout == ""


def test_entry_point_escapes_line_breaks_in_diagnostic_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    diagnostic = DeliveryStartupDiagnostic("ERR_DELIVERY_STARTUP_INVALID", "bad\r\nkey", "unexpected\nconfiguration")
    failure = ExceptionGroup("unhandled errors in a TaskGroup", [diagnostic])

    def _run() -> None:
        raise failure

    monkeypatch.setattr(live_main.mcp, "run", _run)

    with pytest.raises(SystemExit) as exc_info:
        live_main.main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert captured.out == ""
    assert captured.err == (
        "Delivery MCP refused to start: ERR_DELIVERY_STARTUP_INVALID: bad\\r\\nkey "
        "(field=unexpected\\nconfiguration, retry_safe=false)\n"
    )


def test_entry_point_keeps_non_diagnostic_startup_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    diagnostic = DeliveryStartupDiagnostic("ERR_DELIVERY_STARTUP_INVALID", "invalid", "remote")
    failure = ExceptionGroup("unhandled errors in a TaskGroup", [diagnostic, OSError("broken pipe")])

    def _run() -> None:
        raise failure

    monkeypatch.setattr(live_main.mcp, "run", _run)

    with pytest.raises(ExceptionGroup) as exc_info:
        live_main.main()

    assert exc_info.value is failure


@pytest.mark.asyncio
async def test_lifespan_translates_the_gate_refusal_of_a_version_less_config_to_unconfigured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    content = _config()
    del content["schema_version"]
    _write_config(path, content)
    monkeypatch.chdir(repository)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_UNCONFIGURED"
    assert exc_info.value.field == "schema_version"
    assert isinstance(exc_info.value.__cause__, DeliveryStateVersionError)
    assert exc_info.value.__cause__.code == "state-version-unknown"
    acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True).release()


@pytest.mark.asyncio
async def test_lifespan_is_fenced_by_an_exclusive_holder_and_releases_its_lock_on_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    _write_config(path, _config())
    runtime_root = repository / ".owlbear/delivery/runtime"
    monkeypatch.chdir(repository)
    holder = acquire_controller_lock(runtime_root, exclusive=True)
    try:
        with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
            async with app_lifespan(mcp):
                pass
    finally:
        holder.release()

    async with app_lifespan(mcp):
        with pytest.raises(ControllerFencedError):
            acquire_controller_lock(runtime_root, exclusive=True)

    assert exc_info.value.code == "ERR_DELIVERY_CONTROLLER_FENCED"
    assert exc_info.value.field == "controller_lock"
    acquire_controller_lock(runtime_root, exclusive=True).release()


@pytest.mark.asyncio
async def test_lifespan_refuses_an_applied_but_unverified_migration_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    _write_config(path, _config())
    runtime_root = repository / ".owlbear/delivery/runtime"
    migration_id = "c" * 64
    journal = runtime_root / "migrations" / migration_id / "journal.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({"schema_version": 1, "migration_id": migration_id, "state": "applied"}), "utf-8")
    runtime_root.joinpath("format.json").write_bytes(format_marker_bytes())
    monkeypatch.chdir(repository)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    assert exc_info.value.code == "ERR_DELIVERY_STATE_VERSION"
    assert exc_info.value.detail.startswith("state-migration-incomplete")
    acquire_controller_lock(runtime_root, exclusive=True).release()


@pytest.mark.asyncio
async def test_lifespan_refuses_checkout_code_on_a_pinned_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    _write_config(path, _config())
    pin = repository / ".owlbear/controller/pin.json"
    pin.parent.mkdir(parents=True)
    pin.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "commit": "a" * 40,
                "previous": None,
                "release_sha256": "f" * 64,
            }
        ),
        "utf-8",
    )
    monkeypatch.chdir(repository)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    assert exc_info.value.code == "ERR_DELIVERY_STATE_VERSION"
    assert exc_info.value.detail.startswith("controller-not-pinned")
    assert ".owlbear/controller/bin/delivery-mcp" in exc_info.value.detail
    assert not (repository / ".owlbear/delivery/runtime/format.json").exists()
    acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True).release()


def _spy_config_opens(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every open of a ``config.json`` path through the os, io and builtin open functions."""
    opened: list[str] = []
    for module, name in ((os, "open"), (io, "open"), (builtins, "open")):
        original = getattr(module, name)

        def spy(path: object, *args: object, _original: Any = original, **kwargs: object) -> object:
            if isinstance(path, str | os.PathLike) and os.fspath(path).endswith("config.json"):
                opened.append(os.fspath(path))
            return _original(path, *args, **kwargs)

        monkeypatch.setattr(module, name, spy)
    return opened


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [json.dumps({**_config(), "schema_version": 3, "future_field": True}), '{"schema_version": 2, "remote": '],
    ids=["newer", "malformed"],
)
async def test_lifespan_fence_wins_before_the_configuration_is_opened(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")
    monkeypatch.chdir(repository)
    holder = acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True)
    try:
        with pytest.MonkeyPatch.context() as spy_patch:
            opened = _spy_config_opens(spy_patch)
            with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
                async with app_lifespan(mcp):
                    pass
    finally:
        holder.release()

    assert exc_info.value.code == "ERR_DELIVERY_CONTROLLER_FENCED"
    assert opened == []
    assert path.read_text(encoding="utf-8") == content


def test_mcp_startup_delegates_owner_construction_to_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = tmp_path / "delivery.json"
    _write_config(path, _config())
    config = load_delivery_config(path)
    application = object()
    window = WindowHostIdentity(pid=4242, create_time=1_700_000_000.5, name="Code Helper (Plugin)")
    calls: list[tuple[object, Path, object, object]] = []

    def load_core(
        candidate: object, *, workspace_root: Path, publication_provider: object, issuer_host: object
    ) -> object:
        calls.append((candidate, workspace_root, publication_provider, issuer_host))
        return application

    monkeypatch.setattr(live_server, "load_core_delivery_application", load_core)
    monkeypatch.setattr(live_server.WindowHostIdentity, "capture", classmethod(lambda _cls: window))

    assert load_delivery_application(config, repository) is application
    assert len(calls) == 1
    assert calls[0][:2] == (config, repository)
    assert isinstance(calls[0][2], GitHubCliPublicationProvider)
    assert calls[0][3] is window


@pytest.mark.asyncio
async def test_assembled_work_item_tools_observe_runtime_transition(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    _write_delivery_state(runtime_root, repository)
    path = tmp_path / "delivery.json"
    _write_config(path, _config())
    config = load_delivery_config(path)
    application = load_delivery_application(config, repository)
    application._delivery_state_publisher = None  # noqa: SLF001 - this projection test has no remote state branch.
    server = assemble_target_server(application)
    async with Client(server) as client:
        before = await client.call_tool(
            "show_work_item",
            {"change_id": "change-a", "work_item_id": "OUT-001"},
        )
        application.administrative_move(
            "change-a",
            AdministrativeDeliveryMove(
                move_id="move-001",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="Operator evidence invalidated the result.",
                expected_version=application.preview_administrative_move(
                    "change-a",
                    "OUT-001",
                    DeliveryStage.PLANNING,
                ).snapshot_version,
            ),
        )
        listed = await client.call_tool("list_work_items", {})
        after = await client.call_tool(
            "show_work_item",
            {"change_id": "change-a", "work_item_id": "OUT-001"},
        )

    assert before.structured_content is not None
    assert listed.structured_content is not None
    assert after.structured_content is not None
    assert before.structured_content["projection"]["stage"] == "completed"
    assert listed.structured_content["result"][0]["stage"] == "planning"
    assert after.structured_content["projection"]["stage"] == "planning"
