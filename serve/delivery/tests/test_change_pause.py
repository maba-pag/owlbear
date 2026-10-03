"""N09-A2 Pause drains active work: assembled K1-K8 scenarios and falsifiers F1-F10 (plan §1.11, §3.3)."""

# Assembled races inject at the coordinator and runtime seams they exercise.
# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from serve.delivery.tests.test_change_workspace import _preservation_workspace
from serve.delivery.tests.test_portfolio_application import (
    _acquire_planning_claim,
    _attach_engine_publication,
    _awaiting_acceptance_fixture,
    _continuation_request,
    _engine_action,
    _execute_engine,
    _failure_request,
    _finalization_request,
    _finalizer_settlement,
    _git,
    _portfolio,
    _reopen_portfolio,
    _set_checkpoint,
    _task_result,
)
from serve.delivery.tests.test_recovery import _host
from serve.delivery.tests.test_worker_stall import _HOST, _iso, _real_now, _stall_portfolio

from owlbear_delivery import (
    ChangePauseRequest,
    ChangePauseRequestedError,
    DeliveryAdmissionReceipt,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryPendingCheckpoint,
    DeliveryPlanningRetrySettlement,
    DeliveryResultSubmission,
    DeliveryStage,
    FinalizationReport,
    FinalizerSettlementReceipt,
    MarkChangePullRequestReady,
    PortfolioApplicationError,
)
from owlbear_delivery.application_publication import _direct_operation
from owlbear_delivery.application_support import _checkpoint_operation_id
from owlbear_delivery.change_publication import ChangeBranchPublisher
from owlbear_delivery.delivery_runtime import DeliveryRuntime
from owlbear_delivery.delivery_state import DeliveryStatePublisher
from owlbear_delivery.draft_pull_request import DraftPullRequestPublisher
from owlbear_delivery.runtime_models import (
    _DISPOSITION_MUTATIONS,
    _NORMAL_CHANGE_MUTATIONS,
    _PAUSE_COMPLETION_MUTATIONS,
    _PAUSE_GATED_MUTATIONS,
    _PAUSE_OWNER_DRAIN_MUTATIONS,
    pause_mutation_class,
)
from owlbear_delivery.state_migration import coordination_1_to_2
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.workspace_models import (
    ChangeCoordination,
    ChangeDirectOperation,
    recovery_authority_content,
    recovery_authority_digest,
)

_REASON = "Pause for review"


class _Crash(BaseException):
    """Simulated process death at a barrier: no exception handler records it."""


def _digest(runtime) -> str:
    return hashlib.sha256(runtime.frontier_bytes()).hexdigest()


def _pause(application, change_id: str = "change-a", reason: str = _REASON, digest: str | None = None):
    runtime = application._runtimes[change_id]
    return application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=digest or _digest(runtime),
            reason=reason,
        )
    )


def _resume(application, change_id: str = "change-a"):
    return application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=DeliveryChangeIntentKind.RESUME,
            expected_frontier_digest=_digest(application._runtimes[change_id]),
        )
    )


def _checkpoint_lock(application, change_id: str = "change-a"):
    return locked_roots((application._checkpoint_lock_root(change_id),))


def _pause_held(application, change_id: str = "change-a") -> ChangePauseRequest:
    """Record a request while the Change checkpoint lock is busy, so K1 cannot convert yet."""
    with _checkpoint_lock(application, change_id):
        result = _pause(application, change_id)
    assert isinstance(result.receipt, ChangePauseRequest)
    return result.receipt


def _paused(application, change_id: str = "change-a") -> bool:
    runtime = application._runtimes[change_id]
    return runtime.change_deferral() is not None and application._coordinator.pause_request(change_id) is None


def _builder_submission(application, launch) -> DeliveryResultSubmission:
    runtime = application._runtimes["change-a"]
    _git(launch.worktree_path, "commit", "--allow-empty", "-m", "complete task")
    return DeliveryResultSubmission(
        change_id="change-a",
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        result=_task_result(
            "pause-builder-result",
            "change-a",
            runtime.authority_digest,
            runtime.show_binding(launch.outcome_id).tasks[0],
            _git(launch.worktree_path, "rev-parse", "HEAD"),
        ),
    )


# §3.3 first check / K1+K5: Builder drains, its result is accepted, then the Change pauses.
def test_pause_under_builder_drains_result_then_converts_and_resumes(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    runtime = runtimes["change-a"]
    launch = application.acquire_change_action(_continuation_request(application)).launch
    assert launch is not None
    frontier = runtime.frontier_bytes()

    paused = _pause(application)

    assert isinstance(paused.receipt, ChangePauseRequest)
    assert runtime.frontier_bytes() == frontier
    assert runtime.change_deferral() is None
    view = application.get_change("change-a")
    assert view.pause_requested is True
    assert application.acquire_change_action(_continuation_request(application)).launch is None
    assert coordinator.show("change-a").writer is not None

    submitted = application.submit_result(_builder_submission(application, launch))

    assert submitted is not None
    assert runtime.show_binding(launch.outcome_id).tasks[0].task_id == launch.task_id
    assert _paused(application)
    assert coordinator.show("change-a").writer is None
    assert application.get_change("change-a").pause_requested is False
    _resume(application)
    assert runtime.change_deferral() is None


# §3.3: a Planner that ends without a result settles (owner completion) and the request converts.
def test_pause_under_planner_converts_after_ended_without_result_settlement(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    claim = _acquire_planning_claim(application)
    assert isinstance(_pause(application).receipt, ChangePauseRequest)

    settled = application.settle_worker_invocation(
        DeliveryPlanningRetrySettlement(
            change_id="change-a",
            outcome_id="OUT-001",
            claim_id=claim.claim_id,
            attempt_id=claim.attempt_id,
            disposition="ended-without-result",
        ),
        host_id=claim.owner_id,
        session_id=claim.process_id,
    )

    assert settled.active_claim is None
    assert runtimes["change-a"].active_claims() == ()
    assert _paused(application)


# K1: a quiescent Change converts at once; a second identical Pause replays the deferral.
def test_quiescent_pause_converts_immediately_and_replays(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})

    first = _pause(application)
    again = _pause(application)

    assert first.receipt == runtimes["change-a"].change_deferral()
    assert again.receipt == first.receipt
    assert _paused(application)
    with pytest.raises(PortfolioApplicationError, match="another reason"):
        _pause(application, reason="Different reason")


# K1 Resume of a request clears it before any deferral exists.
def test_resume_clears_an_unconverted_request(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    request = _pause_held(application)

    resumed = _resume(application)

    assert resumed.receipt == request
    assert coordinator.pause_request("change-a") is None
    assert runtimes["change-a"].change_deferral() is None
    assert application.acquire_change_action(_continuation_request(application)).launch is not None


# F1: an owner's coordination write between Validate and Record must not fail Pause or the owner.
def test_f1_owner_coordination_write_inside_pause_window_retries(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    commit = coordinator._commit
    injected: list[str] = []

    def interleave(name, participants):
        if name.startswith("pause-request-") and not injected:
            injected.append(name)
            current = coordinator.show("change-a")
            coordinator.update(current.model_copy(update={"target_head": "b" * 40}))
        return commit(name, participants)

    with patch.object(coordinator, "_commit", side_effect=interleave):
        result = _pause(application)

    assert injected
    assert coordinator.show("change-a").target_head == "b" * 40
    assert result.receipt == application._runtimes["change-a"].change_deferral()
    assert _paused(application)


# F2: a frontier write inside the window refuses Pause with the frontier conflict; nothing is recorded.
def test_f2_frontier_write_inside_pause_window_refuses_then_retry_persists(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    commit = coordinator._commit
    injected: list[str] = []

    def interleave(name, participants):
        if name.startswith("pause-request-") and not injected:
            injected.append(name)
            runtime.queue_explicit_checkpoint(head)
        return commit(name, participants)

    stale = _digest(runtime)
    with (
        patch.object(coordinator, "_commit", side_effect=interleave),
        pytest.raises(PortfolioApplicationError, match="Change intent frontier changed"),
    ):
        _pause(application, digest=stale)

    assert coordinator.pause_request("change-a") is None
    assert runtime.change_deferral() is None
    assert _digest(runtime) != stale
    _pause(application)
    assert _paused(application)


# F3: Pause while another call holds the acquisition lock returns at once; the next acquisition converts.
def test_f3_pause_never_waits_for_the_acquisition_lock(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})

    with coordinator.acquisition_lock():
        result = _pause(application)

    assert isinstance(result.receipt, ChangePauseRequest)
    assert runtimes["change-a"].change_deferral() is None
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.launch is None
    assert _paused(application)


# F4/K6: an owner holding the checkpoint and publication locks writes from a stale view; the request survives.
def test_f4_owner_write_under_held_locks_keeps_the_request(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})

    with _checkpoint_lock(application), coordinator.publication_lock("change-a") as lock:
        captured = coordinator.show("change-a")
        result = _pause(application)
        assert isinstance(result.receipt, ChangePauseRequest)
        updated = coordinator.update(captured.model_copy(update={"target_head": "c" * 40}), lock=lock)

    assert updated.pause_request == result.receipt
    assert coordinator.show("change-a").pause_request == result.receipt
    assert coordinator.show("change-a").target_head == "c" * 40
    application.acquire_change_action(_continuation_request(application))
    assert _paused(application)


# F5: a pending engine action whose start loses to Pause writes no started marker and releases custody.
def test_f5_pending_engine_action_loses_to_pause_without_effect(tmp_path: Path) -> None:
    application, runtime, provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    action = _engine_action(application)
    provider.reset_mock()

    assert isinstance(_pause(application).receipt, ChangePauseRequest)
    result = _execute_engine(application, action)

    assert (result.kind, result.reason_code) == ("stale", "readiness-changed")
    assert not application._coordinator.continuation_start_recorded(action)
    assert application._coordinator.show("change-a").continuation_action.finished_at is not None
    provider.set_pull_request_draft_state.assert_not_called()
    assert runtime.ready_receipt() is None
    assert _paused(application)


# F6 (direct): a mark-ready that started before Pause replays to completion; Pause then converts.
def test_f6_started_direct_mark_ready_replays_under_request(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    finalization = runtime.finalization()
    request = MarkChangePullRequestReady(
        change_id="change-a",
        operation_id="ready-change-a",
        finalization_id=finalization.finalization_id,
        exact_head=exact_head,
    )
    direct = _direct_operation("change-a", "mark-ready", request.operation_id, request.finalization_id, exact_head)
    assert application._coordinator.start_direct_operation(direct) is True
    _pause_held(application)

    ready = application.mark_change_ready("change-a", request)

    assert ready.head_sha == exact_head
    assert application._coordinator.direct_operation_state(direct) == "finished"
    provider.set_pull_request_draft_state.assert_called()
    assert _paused(application)


# F9 (direct): a new direct start under a request is refused before any marker or provider effect.
def test_f9_new_direct_mark_ready_is_refused_under_request(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    request = MarkChangePullRequestReady(
        change_id="change-a",
        operation_id="ready-change-a",
        finalization_id=runtime.finalization().finalization_id,
        exact_head=exact_head,
    )
    _pause_held(application)
    provider.reset_mock()

    with pytest.raises(ChangePauseRequestedError):
        application.mark_change_ready("change-a", request)

    marker_root = application._coordinator.runtime_root / "changes/change-a/action-receipts"
    assert not list(marker_root.glob("direct-*"))
    provider.set_pull_request_draft_state.assert_not_called()
    provider.observe_checks.assert_not_called()
    assert runtime.ready_receipt() is None
    assert application._coordinator.pause_request("change-a") is not None


# §3.3 negative: new operator and engine-free starts refuse before any effect while a request exists.
def test_new_work_entries_refuse_under_request_without_effect(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, state_root = _awaiting_acceptance_fixture(tmp_path)
    _pause_held(application)
    provider.reset_mock()
    coordination_path = state_root / "coordination/changes/change-a.json"
    before = (runtime.frontier_bytes(), coordination_path.read_bytes())
    calls = {
        "observe_acceptance": lambda: application.observe_acceptance("change-a"),
        "adopt_external_head": lambda: application.adopt_external_head("change-a", exact_head, "e" * 40, "adopt-1"),
        "promote_external_head": lambda: application.promote_external_head("change-a", exact_head, "promote-1"),
    }

    for name, call in calls.items():
        with pytest.raises(ChangePauseRequestedError):
            call()
        assert (runtime.frontier_bytes(), coordination_path.read_bytes()) == before, name

    provider.read_pull_request.assert_not_called()
    assert application._coordinator.pause_request("change-a") is not None


# §3.3 negative: a pause-gated runtime write (explicit checkpoint) refuses under a request with no write.
def test_explicit_checkpoint_refuses_under_request(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    _pause_held(application)
    before = runtime.frontier_bytes()

    with pytest.raises(ChangePauseRequestedError):
        runtime.queue_explicit_checkpoint(head)

    assert runtime.frontier_bytes() == before


# F6 (acceptance): Pause injected inside the provider read; the owner completes the Change and clears the request.
def test_f6_acceptance_owner_completes_and_clears_a_mid_flight_request(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    merged = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "d" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    recorded: list[object] = []

    def read_then_pause(_repository, _number):
        if not recorded:
            recorded.append(_pause(application).receipt)
        return merged

    provider.read_pull_request.side_effect = read_then_pause

    application.observe_acceptance("change-a")

    assert recorded
    assert isinstance(recorded[0], ChangePauseRequest)
    assert runtime.completion_receipt() is not None
    assert application._coordinator.pause_request("change-a") is None
    assert runtime.change_deferral() is None


# F9: tokens permit only their own Change and named owner-drain operations; nothing else passes.
def test_f9_drain_tokens_are_exact_and_never_grant_new_starts(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}
    )
    _pause_held(application)

    def guard(operation: str, mutation_class: str = "owner-drain") -> None:
        coordinator.prepare_runtime_custody_guard("change-a", operation=operation, mutation_class=mutation_class)

    with pytest.raises(ChangePauseRequestedError):
        guard("record_target_sync")
    guard("complete_change", "completion")
    with coordinator.drain_authority("change-a", "sync-target:op", mutation=("record_target_sync",)):
        guard("record_target_sync")
        with pytest.raises(ChangePauseRequestedError):
            guard("mark_awaiting_merge")
        with pytest.raises(ChangePauseRequestedError):
            guard("record_target_sync", "pause-gated")
        with pytest.raises(ChangePauseRequestedError):
            coordinator.require_pause_permits("change-a", "acquire", "claim-1")
    with (
        coordinator.drain_authority("change-b", "sync-target:op", mutation=("record_target_sync",)),
        pytest.raises(ChangePauseRequestedError),
    ):
        guard("record_target_sync")
    coordinator.prepare_runtime_custody_guard("change-b", operation="record_target_sync", mutation_class="pause-gated")
    direct = ChangeDirectOperation(
        change_id="change-a", kind="sync-target", operation_id="sync-1", request_digest="e" * 64
    )
    with pytest.raises(ChangePauseRequestedError):
        coordinator.start_direct_operation(direct)
    assert coordinator.direct_operation_state(direct) == "absent"
    with pytest.raises(ChangePauseRequestedError):
        coordinator.prepare_pause_fence("change-a", "provider", "anything")


# F10: a crash after Record shows only the request; the next acquisition converts; never both.
def test_f10_restart_after_record_shows_request_then_converts(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    request = _pause_held(application)

    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)

    assert coordinator.pause_request("change-a") == request
    assert reopened._runtimes["change-a"].change_deferral() is None
    assert reopened.get_change("change-a").pause_requested is True
    assert reopened.acquire_change_action(_continuation_request(reopened)).launch is None
    assert reopened._runtimes["change-a"].change_deferral() is not None
    assert coordinator.pause_request("change-a") is None


# F10: a crash after conversion but before publication keeps only the deferral.
def test_f10_restart_after_conversion_shows_only_the_deferral(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})

    with patch.object(type(application), "_publish_delivery_state", side_effect=OSError("crash before publish")):
        result = _pause(application)

    assert result.receipt == runtimes["change-a"].change_deferral()
    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    assert coordinator.pause_request("change-a") is None
    assert reopened._runtimes["change-a"].change_deferral() == result.receipt


# K6: a Pause landing inside an owner's runtime transaction is retried, never failing the owner.
def test_k6_runtime_guard_conflict_from_pause_is_retried(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    runtime = runtimes["change-a"]
    launch = application.acquire_change_action(_continuation_request(application)).launch
    submission = _builder_submission(application, launch)
    prepare = coordinator.prepare_runtime_custody_guard
    injected: list[ChangePauseRequest] = []

    def guard_then_pause(change_id, **kwargs):
        participant = prepare(change_id, **kwargs)
        if not injected:
            request = ChangePauseRequest.create(
                change_id="change-a", reason=_REASON, requested_at="2026-08-04T00:00:00Z"
            )
            injected.append(coordinator.record_pause_request(request, _digest(runtime)))
        return participant

    with patch.object(coordinator, "prepare_runtime_custody_guard", side_effect=guard_then_pause):
        application.submit_result(submission)

    assert injected
    assert runtime.active_claims() == ()
    assert _paused(application)


# Direct markers: identity, digest binding, finish-requires-start, idempotent replay (K2 direct row).
def test_direct_operation_markers_are_exact_and_replayable(tmp_path: Path) -> None:
    _application, _runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    direct = ChangeDirectOperation(
        change_id="change-a", kind="mark-ready", operation_id="ready-1", request_digest="a" * 64
    )
    with pytest.raises(Exception, match="matching start marker"):
        coordinator.finish_direct_operation(direct)

    assert coordinator.start_direct_operation(direct) is True
    assert coordinator.start_direct_operation(direct) is False
    assert coordinator.direct_operation_path(direct).parent.name == direct.marker_name
    with pytest.raises(Exception, match="another request"):
        coordinator.start_direct_operation(direct.model_copy(update={"request_digest": "b" * 64}))
    coordinator.finish_direct_operation(direct)
    coordinator.finish_direct_operation(direct)
    assert coordinator.direct_operation_state(direct) == "finished"


# K4: Pause writes never change the recovery authority digest; v1 records migrate with the same digest.
def test_k4_recovery_digest_ignores_pause_and_survives_migration(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    before = coordinator.recovery_authority_digest("change-a")
    request = _pause_held(application)

    assert coordinator.pause_request("change-a") == request
    assert coordinator.recovery_authority_digest("change-a") == before
    v2 = (state_root / "coordination/changes/change-a.json").read_bytes()
    current = ChangeCoordination.model_validate_json(v2)
    v1 = recovery_authority_content(current.model_copy(update={"pause_request": None}))
    assert json.loads(v1)["schema_version"] == 1
    assert hashlib.sha256(v1).hexdigest() == before

    migrated = coordination_1_to_2(v1)

    record = ChangeCoordination.model_validate_json(migrated, strict=True)
    assert record.schema_version == 2
    assert record.pause_request is None
    assert recovery_authority_digest(record) == hashlib.sha256(v1).hexdigest()
    with pytest.raises(ValueError, match="schema-1"):
        coordination_1_to_2(migrated)


# K7: every runtime mutation is classified exactly once; the default class is pause-gated.
def test_k7_registry_classifies_runtime_mutations_exactly_once() -> None:
    assert not _PAUSE_COMPLETION_MUTATIONS & _PAUSE_OWNER_DRAIN_MUTATIONS
    assert not _PAUSE_GATED_MUTATIONS & (_PAUSE_COMPLETION_MUTATIONS | _PAUSE_OWNER_DRAIN_MUTATIONS)
    assert (
        _PAUSE_COMPLETION_MUTATIONS | _PAUSE_OWNER_DRAIN_MUTATIONS | _PAUSE_GATED_MUTATIONS
        == _NORMAL_CHANGE_MUTATIONS | _DISPOSITION_MUTATIONS
    )
    for name in _PAUSE_COMPLETION_MUTATIONS:
        assert pause_mutation_class(name) == "completion"
    for name in _PAUSE_OWNER_DRAIN_MUTATIONS:
        assert pause_mutation_class(name) == "owner-drain"
    for name in _PAUSE_GATED_MUTATIONS:
        assert pause_mutation_class(name) == "pause-gated"
    assert pause_mutation_class("unregistered-mutation") == "pause-gated"


def _attach_publishers(application, tmp_path: Path, provider) -> None:
    """Reattach the production publishers after a restart; only the provider is a fake."""
    repository = application._workspace_manager.repository
    application._change_branch_publisher = ChangeBranchPublisher(
        repository,
        application._coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "branch-operations",
    )
    application._draft_pull_request_publisher = DraftPullRequestPublisher(
        provider, repository="example/project", target_branch="main", state_root=tmp_path / "pull-requests"
    )
    application._delivery_state_publisher = DeliveryStatePublisher(
        repository, remote="origin", state_branch="owlbear/delivery-state"
    )


def _remote_branch(remote: Path, change_id: str = "change-a") -> str | None:
    refs = _git(remote, "for-each-ref", "--format=%(objectname)", f"refs/heads/owlbear/change/{change_id}")
    return refs or None


def _assert_foreign_starts_refused(coordinator, change_id: str = "change-a") -> None:
    """Inside any held drain token: a target sync, mark-ready, adoption or other reservation stays refused."""
    for kind in ("sync-target", "mark-ready"):
        direct = ChangeDirectOperation(
            change_id=change_id, kind=kind, operation_id=f"foreign-{kind}", request_digest="f" * 64
        )
        with pytest.raises(ChangePauseRequestedError):
            coordinator.start_direct_operation(direct)
        assert coordinator.direct_operation_state(direct) == "absent"
    with pytest.raises(ChangePauseRequestedError):
        coordinator.start_pause_fenced(change_id, "adopt:foreign")
    with pytest.raises(ChangePauseRequestedError):
        coordinator.require_pause_permits(change_id, "reserve", _checkpoint_operation_id("branch", change_id, "e" * 40))
    for operation in ("record_target_sync", "mark_awaiting_merge"):
        with pytest.raises(ChangePauseRequestedError):
            coordinator.prepare_runtime_custody_guard(change_id, operation=operation, mutation_class="owner-drain")


# §3.3 Finalizer row: a Finalizer attempt drains through finalize_change, then the request converts.
def test_pause_under_finalizer_drains_through_finalize_change(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt

    assert isinstance(_pause(application).receipt, ChangePauseRequest)
    assert application.acquire_change_action(_continuation_request(application)).kind != "acquired"
    receipt = application.finalize_change(
        "change-a", _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id)
    )

    assert runtimes["change-a"].finalization() == receipt
    assert coordinator.show("change-a").writer is None
    assert _paused(application)
    _resume(application)
    assert runtimes["change-a"].finalization() == receipt


# §3.3 Finalizer row: a normally returned Finalizer reports, settles, and the request converts.
def test_pause_under_finalizer_drains_through_report_and_settlement(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    attempt = application.acquire_change_action(_continuation_request(application)).finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    assert isinstance(report, FinalizationReport)

    assert isinstance(_pause(application).receipt, ChangePauseRequest)
    settled = application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))

    assert isinstance(settled, FinalizerSettlementReceipt)
    assert coordinator.show("change-a").writer.kind == "finalization-attention"
    assert _paused(application)


# §3.3: a host-lost settlement by the stall sweep is the claim's drain point.
def test_pause_under_planner_converts_after_host_lost_settlement(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, _state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    _acquire_planning_claim(application)
    assert isinstance(_pause(application).receipt, ChangePauseRequest)
    probe.states[_HOST] = "gone"
    now[0] = _iso(start + timedelta(minutes=30))

    result = application.acquire_frontier_work()

    assert result.launch_packages == ()
    assert runtimes["change-a"].active_claims() == ()
    assert _paused(application)


# §3.3: a user-confirmed release_stuck_worker settles the claim under its drain token and converts.
def test_pause_under_planner_converts_after_release_stuck_worker(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    assert isinstance(_pause(application).receipt, ChangePauseRequest)
    now[0] = _iso(start + timedelta(minutes=10))

    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert settled.active_claim is None
    assert runtimes["change-a"].active_claims() == ()
    assert _paused(application)


# K3 (operator entries): Pause committed before the start fence refuses it before any provider or runtime effect.
def test_operator_start_lost_to_pause_has_no_effect(tmp_path: Path) -> None:
    application, runtime, provider, _state, _exact_head, state_root = _awaiting_acceptance_fixture(tmp_path)
    coordinator = application._coordinator
    commit = coordinator._commit
    injected: list[ChangePauseRequest] = []

    def pause_inside_fence(name, participants):
        if name.startswith("operator-start-") and not injected:
            request = ChangePauseRequest.create(
                change_id="change-a", reason=_REASON, requested_at="2026-08-04T00:00:00Z"
            )
            injected.append(coordinator.record_pause_request(request, _digest(runtime)))
        return commit(name, participants)

    provider.reset_mock()
    before = (runtime.frontier_bytes(), (state_root / "coordination/changes/change-a.json").read_bytes())
    with patch.object(coordinator, "_commit", side_effect=pause_inside_fence):
        for call in (
            lambda: application.prepare_review_repair("change-a"),
            lambda: application.reconcile_finalization_head("change-a"),
        ):
            with pytest.raises(ChangePauseRequestedError):
                call()

    assert injected
    assert runtime.frontier_bytes() == before[0]
    assert coordinator.pause_request("change-a") == injected[0]
    provider.read_pull_request.assert_not_called()
    provider.set_pull_request_draft_state.assert_not_called()
    assert runtime.ready_receipt() is not None


# K3 + K2 (operator entries): a Pause landing after the start finds a started owner; its own writes drain.
def test_operator_review_repair_started_before_pause_finishes_then_converts(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    draft = provider.set_pull_request_draft_state.side_effect
    recorded: list[object] = []

    def return_to_draft_then_pause(request):
        recorded.append(_pause(application).receipt)
        return draft(request)

    provider.set_pull_request_draft_state.side_effect = return_to_draft_then_pause

    invalidation = application.prepare_review_repair("change-a")

    assert isinstance(recorded[0], ChangePauseRequest)
    assert invalidation.reason == "review-repair"
    assert invalidation.expected_head == exact_head
    assert state["pull_request"].draft is True
    assert runtime.finalization() is None
    assert _paused(application)


# K3 + K2 (operator entries): a standalone finalization-head reconciliation started before Pause finishes.
def test_operator_finalization_head_reconciliation_started_before_pause_finishes(tmp_path: Path) -> None:
    application, _runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    recorded: list[object] = []

    def read_then_pause(_repository, _number):
        if not recorded:
            recorded.append(_pause(application).receipt)
        return state["pull_request"]

    provider.read_pull_request.side_effect = read_then_pause

    result = application.reconcile_finalization_head("change-a")

    assert isinstance(recorded[0], ChangePauseRequest)
    assert result is not None
    assert result.exact_head == exact_head
    assert _paused(application)


# §3.3 Builder drain with publication: the claim token reserves and pushes only its queued checkpoint head.
def test_builder_drain_publishes_its_checkpoint_and_refuses_foreign_starts_inside_its_token(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    runtime = runtimes["change-a"]
    _provider, remote = _attach_engine_publication(application, tmp_path)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    assert isinstance(_pause(application).receipt, ChangePauseRequest)
    publisher = application._change_branch_publisher
    publish = publisher.publish
    inside: list[str] = []

    def publish_inside_token(request):
        _assert_foreign_starts_refused(coordinator)
        inside.append(request.expected_published_head)
        return publish(request)

    submission = _builder_submission(application, launch)
    with patch.object(publisher, "publish", side_effect=publish_inside_token):
        application.submit_result(submission)

    head = submission.result.completed_commit
    assert inside == [head]
    assert _remote_branch(remote) == head
    assert runtime.checkpoint_publication_state().published_head == head
    assert runtime.pending_state_publication() is None
    assert coordinator.show("change-a").publication_lease is None
    assert _paused(application)


def _target_remote(application, tmp_path: Path) -> str:
    """Attach a local target remote with one commit ahead of the Change base; return that target head."""
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    clone = tmp_path / "target-clone"
    _git(tmp_path, "clone", str(remote), str(clone))
    _git(clone, "config", "user.name", "Target")
    _git(clone, "config", "user.email", "target@example.invalid")
    (clone / "target.txt").write_text("target edit\n", encoding="utf-8")
    _git(clone, "add", "target.txt")
    _git(clone, "commit", "-m", "target edit")
    _git(clone, "push", "origin", "HEAD:main")
    return _git(clone, "rev-parse", "HEAD")


# F6 (direct sync): the started direct owner finishes record_target_sync after Pause; its marker finishes.
def test_f6_started_direct_sync_records_after_pause_and_finishes_its_marker(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    target = _target_remote(application, tmp_path)
    record = DeliveryRuntime.record_target_sync
    recorded: list[object] = []

    def pause_then_record(runtime, receipt, recorded_at):
        recorded.append(_pause(application).receipt)
        return record(runtime, receipt, recorded_at)

    with patch.object(DeliveryRuntime, "record_target_sync", pause_then_record):
        receipt = application.sync_change_with_target("change-a", target, "sync-under-pause")

    direct = _direct_operation("change-a", "sync-target", "sync-under-pause", target)
    assert isinstance(recorded[0], ChangePauseRequest)
    assert coordinator.direct_operation_state(direct) == "finished"
    assert runtimes["change-a"].target_sync_receipt() == receipt
    assert coordinator.show("change-a").last_reviewed_commit == receipt.merged_head
    assert _paused(application)


# §1.6 direct sync lost to Pause: no marker, fetch, merge or runtime write.
def test_direct_sync_start_lost_to_pause_has_no_effect(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    target = _target_remote(application, tmp_path)
    _pause_held(application)
    coordination = coordinator.show("change-a")
    repository = application._workspace_manager.repository
    before = (
        runtimes["change-a"].frontier_bytes(),
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        _git(repository, "for-each-ref", "--format=%(refname) %(objectname)"),
        _git(coordination.worktree_path, "status", "--porcelain=v1"),
    )

    with pytest.raises(ChangePauseRequestedError, match="Change pause requested"):
        application.sync_change_with_target("change-a", target, "sync-lost")

    direct = _direct_operation("change-a", "sync-target", "sync-lost", target)
    assert coordinator.direct_operation_state(direct) == "absent"
    assert (
        runtimes["change-a"].frontier_bytes(),
        (state_root / "coordination/changes/change-a.json").read_bytes(),
        _git(repository, "for-each-ref", "--format=%(refname) %(objectname)"),
        _git(coordination.worktree_path, "status", "--porcelain=v1"),
    ) == before


def _seed_remote_snapshot(application, change_id: str = "change-a") -> None:
    """Publish the current frontier as the remote state snapshot without touching the checkpoint queue."""
    package = application._package_store.read_verified(change_id)
    admission_path = application._target_root / "changes" / change_id / "admission.json"
    application._delivery_state_publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=application._workspace_manager.show(change_id),
        runtime=application._runtimes[change_id],
        admission=DeliveryAdmissionReceipt.model_validate_json(admission_path.read_bytes()),
        operation_id="seed-state",
        captured_at=datetime(2026, 8, 4, tzinfo=UTC),
    )


def _first_task_checkpoint(tmp_path: Path):
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    _set_checkpoint(
        runtime,
        state_root,
        DeliveryPendingCheckpoint(
            head=head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    provider, remote = _attach_engine_publication(application, tmp_path)
    _seed_remote_snapshot(application)
    return application, runtimes, state_root, provider, remote


def _assert_snapshot_heads_agree(application, remote: Path) -> None:
    coordination = application._coordinator.show("change-a")
    state = application._runtimes["change-a"].checkpoint_publication_state()
    snapshot = coordination.design_package_snapshot
    assert snapshot is not None
    assert coordination.last_reviewed_commit == snapshot.snapshot_head
    assert state.published_head == snapshot.snapshot_head
    assert state.pending_checkpoint is None or state.pending_checkpoint.head == snapshot.snapshot_head
    assert _remote_branch(remote) == snapshot.snapshot_head


# F6 snapshot: Pause after the snapshot commit; the started snapshot owner anchors, publishes, then converts.
def test_f6_first_task_snapshot_started_before_pause_publishes_then_converts(tmp_path: Path) -> None:
    application, _runtimes, _state_root, provider, remote = _first_task_checkpoint(tmp_path)
    anchor = DeliveryRuntime.record_design_package_snapshot
    recorded: list[object] = []

    def pause_then_anchor(runtime, checkpoint, snapshot):
        recorded.append(_pause(application).receipt)
        _assert_foreign_starts_refused(application._coordinator)
        return anchor(runtime, checkpoint, snapshot)

    with patch.object(DeliveryRuntime, "record_design_package_snapshot", pause_then_anchor):
        result = application.reconcile_change_checkpoint("change-a")

    assert isinstance(recorded[0], ChangePauseRequest)
    assert result.reconciled
    assert provider.create_calls == 1
    assert _paused(application)
    _assert_snapshot_heads_agree(application, remote)


# F6 snapshot handoff: crash after re-anchoring, before the lease; every conversion waits for the replay.
@pytest.mark.parametrize("replay", ["supervisor", "acquisition"])
def test_f6_snapshot_handoff_blocks_conversion_until_its_replay_publishes(tmp_path: Path, replay: str) -> None:
    application, runtimes, state_root, provider, remote = _first_task_checkpoint(tmp_path)
    with (
        patch.object(type(application), "_publish_checkpoint_branch", side_effect=_Crash),
        pytest.raises(_Crash),
    ):
        application.reconcile_change_checkpoint("change-a")
    snapshot = application._coordinator.show("change-a").design_package_snapshot
    pending = runtimes["change-a"].checkpoint_publication_state().pending_checkpoint
    assert pending.head == snapshot.snapshot_head
    assert runtimes["change-a"].pending_state_publication() is not None
    assert _remote_branch(remote) is None

    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    _attach_publishers(reopened, tmp_path, provider)
    assert isinstance(_pause(reopened).receipt, ChangePauseRequest)
    assert reopened._convert_pause_request_unlocked("change-a") is None
    publisher = reopened._change_branch_publisher
    publish = publisher.publish
    raced: list[object] = []

    def publish_while_racing(request):
        raced.append(_pause(reopened).receipt)
        raced.append(reopened._convert_pause_request_unlocked("change-a"))
        _assert_foreign_starts_refused(coordinator)
        return publish(request)

    with patch.object(publisher, "publish", side_effect=publish_while_racing):
        if replay == "supervisor":
            reopened.reconcile_pending_checkpoints()
        else:
            reopened.acquire_frontier_work()

    assert isinstance(raced[0], ChangePauseRequest)
    assert raced[1] is None
    assert reopened._runtimes["change-a"].change_deferral() is not None
    assert coordinator.pause_request("change-a") is None
    _assert_snapshot_heads_agree(reopened, remote)


# F6 handoff fast path: a crash after the push and lease release replays from the stored receipt.
def test_f6_snapshot_handoff_fast_path_replays_without_a_lease_and_converts(tmp_path: Path) -> None:
    application, runtimes, state_root, provider, remote = _first_task_checkpoint(tmp_path)
    record = DeliveryRuntime.record_checkpoint_branch_publication
    crashed: list[str] = []

    def crash_before_recording(runtime, checkpoint, published_head):
        if not crashed:
            crashed.append(published_head)
            raise _Crash
        return record(runtime, checkpoint, published_head)

    with (
        patch.object(DeliveryRuntime, "record_checkpoint_branch_publication", crash_before_recording),
        pytest.raises(_Crash),
    ):
        application.reconcile_change_checkpoint("change-a")
    snapshot = application._coordinator.show("change-a").design_package_snapshot
    assert _remote_branch(remote) == snapshot.snapshot_head == crashed[0]
    assert application._coordinator.show("change-a").publication_lease is None

    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    _attach_publishers(reopened, tmp_path, provider)
    assert isinstance(_pause(reopened).receipt, ChangePauseRequest)
    draft = reopened._draft_pull_request_publisher
    publish_draft = draft.publish
    reservations: list[str] = []
    reserve = coordinator.reserve_publication

    def counted_reserve(change_id, lease, lock, *, now):
        reservations.append(lease.operation_id)
        return reserve(change_id, lease, lock, now=now)

    def draft_inside_handoff(request):
        _assert_foreign_starts_refused(coordinator)
        return publish_draft(request)

    with (
        patch.object(coordinator, "reserve_publication", side_effect=counted_reserve),
        patch.object(draft, "publish", side_effect=draft_inside_handoff),
    ):
        result = reopened.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert reservations == []
    assert reopened._runtimes["change-a"].change_deferral() is not None
    assert coordinator.pause_request("change-a") is None
    _assert_snapshot_heads_agree(reopened, remote)


# F9 (snapshot): a snapshot token never continues another snapshot, package or head.
def test_f9_snapshot_token_refuses_another_snapshot_identity(tmp_path: Path) -> None:
    application, runtimes, _state_root, _provider, _remote = _first_task_checkpoint(tmp_path)
    coordinator = application._coordinator
    _pause_held(application)
    receipt = ChangeCoordination.model_validate_json(
        (coordinator.runtime_root / "coordination/changes/change-a.json").read_bytes()
    ).design_package_snapshot
    assert receipt is None
    with coordinator.drain_authority("change-a", "snapshot:other", snapshot=("op:pkg:head",)) as authority:
        assert not authority.allows("snapshot", "op:pkg:other-head")
        with pytest.raises(ChangePauseRequestedError):
            coordinator.require_pause_permits(
                "change-a", "reserve", _checkpoint_operation_id("branch", "change-a", "a" * 40)
            )
    result = application.reconcile_change_checkpoint("change-a")
    assert result.reconciled is False
    assert result.error_code == ChangePauseRequestedError.code
    assert coordinator.show("change-a").design_package_snapshot_intent is None
    assert runtimes["change-a"].checkpoint_publication_state().pending_checkpoint.last_error_code is None


# F8 (Builder replay): crash after transition, before the push; the identical replay is bound to its pending intent.
def test_f8_builder_result_replay_publishes_only_its_bound_checkpoint_then_converts(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    provider, remote = _attach_engine_publication(application, tmp_path)
    launch = application.acquire_change_action(_continuation_request(application)).launch
    submission = _builder_submission(application, launch)
    with patch.object(application._change_branch_publisher, "publish", side_effect=_Crash), pytest.raises(_Crash):
        application.submit_result(submission)
    pending = runtimes["change-a"].pending_state_publication()
    assert pending is not None
    assert pending.transition_request_digest is not None
    assert _remote_branch(remote) is None

    reopened, coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    _attach_publishers(reopened, tmp_path, provider)
    _pause_held(reopened)
    changed = submission.model_copy(
        update={"result": submission.result.model_copy(update={"result_id": "pause-builder-result-changed"})}
    )
    with pytest.raises((PortfolioApplicationError, RuntimeError)):
        reopened.submit_result(changed)
    assert _remote_branch(remote) is None
    assert reopened._runtimes["change-a"].pending_state_publication() == pending
    publisher = reopened._change_branch_publisher
    publish = publisher.publish

    def publish_inside_replay(request):
        _assert_foreign_starts_refused(coordinator)
        return publish(request)

    with patch.object(publisher, "publish", side_effect=publish_inside_replay):
        reopened.submit_result(submission)

    head = submission.result.completed_commit
    assert _remote_branch(remote) == head
    assert reopened._runtimes["change-a"].checkpoint_publication_state().published_head == head
    assert _paused(reopened)


# F8 (Planner settlement replay): crash after the settlement receipt, before state publication.
def test_f8_planner_settlement_replay_publishes_then_converts(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING})
    provider, remote = _attach_engine_publication(application, tmp_path)
    _seed_remote_snapshot(application)
    claim = _acquire_planning_claim(application)
    settlement = DeliveryPlanningRetrySettlement(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        attempt_id=claim.attempt_id,
        disposition="ended-without-result",
    )
    with (
        patch.object(application._delivery_state_publisher, "publish", side_effect=_Crash),
        pytest.raises(_Crash),
    ):
        application.settle_worker_invocation(settlement, host_id=claim.owner_id, session_id=claim.process_id)
    assert runtimes["change-a"].active_claims() == ()
    assert runtimes["change-a"].pending_state_publication() is not None

    reopened, _coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    _attach_publishers(reopened, tmp_path, provider)
    _pause_held(reopened)
    reopened.settle_worker_invocation(settlement, host_id=claim.owner_id, session_id=claim.process_id)

    assert reopened._runtimes["change-a"].pending_state_publication() is None
    assert _git(remote, "for-each-ref", "--format=%(refname)", "refs/heads/owlbear/delivery-state")
    assert _paused(reopened)


# G10 / K4: a journal whose digest equals the v1 bytes completes after coordination-1-to-2 and Pause.
def test_k4_v1_issued_recovery_journal_completes_after_migration(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION})
    host = _host(application)
    application.acquire_change_action(_continuation_request(application))
    intent = application._propose_recovery("change-a")
    path = state_root / "coordination/changes/change-a.json"
    v1 = recovery_authority_content(coordinator.show("change-a"))
    assert json.loads(v1)["schema_version"] == 1
    assert hashlib.sha256(v1).hexdigest() == intent.coordination_digest
    path.write_bytes(v1)
    path.write_bytes(coordination_1_to_2(v1))

    reopened, reopened_coordinator, _manager = _reopen_portfolio(tmp_path, state_root, runtimes)
    reopened._recovery_evidence_provider = host
    _pause_held(reopened)
    receipt = reopened._complete_recovery("change-a", intent.recovery_id, host.seal(intent))

    assert receipt.recovery_id == intent.recovery_id
    assert reopened._runtimes["change-a"].active_claims() == ()
    assert reopened_coordinator.show("change-a").recovery_owner_id is None
    assert _paused(reopened)


# G10 / K4: a preservation receipt bound to v1 bytes verifies after migration and with a Pause request.
def test_k4_v1_preservation_receipt_verifies_after_migration_and_pause(tmp_path: Path) -> None:
    coordinator, manager, coordination, intent = _preservation_workspace(tmp_path)
    change_id = coordination.change_id
    (coordination.worktree_path / "shared.txt").write_bytes(b"dirty preservation\n")
    preservation = manager.capture_preservation(change_id, intent.recovery_id)
    path = coordinator.runtime_root / "coordination" / "changes" / f"{change_id}.json"
    v1 = recovery_authority_content(coordinator.show(change_id))
    assert hashlib.sha256(v1).hexdigest() == preservation.coordination_digest
    path.write_bytes(coordination_1_to_2(v1))
    frontier = (coordinator.runtime_root / "changes" / change_id / "frontier.json").read_bytes()
    coordinator.record_pause_request(
        ChangePauseRequest.create(change_id=change_id, reason=_REASON, requested_at="2026-08-04T00:00:00Z"),
        hashlib.sha256(frontier).hexdigest(),
    )

    assert manager.verify_preservation(change_id, preservation.preservation_id) == preservation
