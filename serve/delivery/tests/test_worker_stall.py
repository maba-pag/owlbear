# ruff: noqa: SLF001

from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from serve.delivery.tests.test_portfolio_application import (
    _acquire_planning_claim,
    _builder_retry_history,
    _continuation_request,
    _finalization_request,
    _git,
    _policies,
    _portfolio,
    _requestless_builder_settlement,
    _task_result,
    _workspace_content_snapshot,
)

from owlbear_delivery import (
    CompletedHistoryCatalog,
    DeliveryActionSelectionConflictError,
    DeliveryBuilderInvocationSettlement,
    DeliveryPlanningRetrySettlement,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    FinalizationReportError,
    FinalizerSettlementReceipt,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationError,
    PortfolioApplicationHooks,
    PublishDeliveryResult,
    RetryDelivery,
    change_workspace,
)
from owlbear_delivery.delivery_runtime import DeliveryEngineBuilderSettlement, DeliveryEnginePlanningSettlement
from owlbear_delivery.diagnostics import DeliveryFailureCategory, classify_delivery_failure
from owlbear_delivery.finalization_reports import (
    FinalizationFailureCode,
    FinalizerEngineSettlement,
    ReportFinalizationFailure,
)
from owlbear_delivery.portfolio_application import DeliveryActionBusyError
from owlbear_delivery.recovery import RetryLedger
from owlbear_delivery.worker_stall import (
    DeliveryHostInstance,
    DeliveryWorkerActiveError,
    HostLockLivenessProbe,
)

_HOST = "a" * 32
_QUIET = timedelta(minutes=2)


@dataclass(frozen=True)
class _Host:
    instance_id: str = _HOST


class _Probe:
    def __init__(self) -> None:
        self.states: dict[str, str] = {}

    def host_state(self, instance_id: str) -> str:
        return self.states.get(instance_id, "alive")


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _real_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _stall_portfolio(
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    now: list[str],
    *,
    host: _Host | None = None,
    capacity: int = 3,
):
    base, runtimes, coordinator, state_root = _portfolio(
        tmp_path, stages, execution_capacity=capacity, clock=lambda: now[0]
    )
    probe = _Probe()
    identities = (f"stall-{index:03}" for index in itertools.count(1))
    application = PortfolioApplication(
        dict(reversed(tuple(runtimes.items()))),
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=base._package_store,
            authority_registry=base._authority_registry,
            coordinator=coordinator,
            workspace_manager=base._workspace_manager,
            completed_history_catalog=CompletedHistoryCatalog(state_root),
            host_instance=host if host is not None else _Host(),
            host_liveness_probe=probe,
            worker_quiet_period=_QUIET,
        ),
        PortfolioApplicationConfig(
            package_root=tmp_path / "packages",
            execution_capacity=capacity,
            role_policies=_policies(),
        ),
        PortfolioApplicationHooks(identity_factory=lambda: next(identities), clock=lambda: now[0]),
    )
    return application, runtimes, coordinator, state_root, probe


def _owner_failure_code(state_root: Path, change_id: str, attempt_id: str) -> str:
    path = state_root / "changes" / change_id / "retry-ledger/owner-results" / f"{attempt_id}.json"
    return json.loads(path.read_bytes())["failure_code"]


def _issuer_path(state_root: Path, change_id: str, attempt_id: str) -> Path:
    return state_root / "changes" / change_id / "claim-issuers" / f"{attempt_id}.json"


def _builder_with_workspace_changes(tmp_path: Path, now: list[str]):
    application, runtimes, coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, now, capacity=1
    )
    acquired = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert acquired.launch is not None, acquired
    launch = acquired.launch
    worktree = launch.worktree_path
    (worktree / "committed.txt").write_text("committed Builder work\n", encoding="utf-8")
    _git(worktree, "add", "committed.txt")
    _git(worktree, "commit", "-m", "preserve Builder commit")
    branch_head = _git(worktree, "rev-parse", "HEAD")
    (worktree / "product.txt").write_text("staged Builder work\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    (worktree / "product.txt").write_text("unstaged Builder work\n", encoding="utf-8")
    (worktree / "untracked.txt").write_text("untracked Builder work\n", encoding="utf-8")
    return application, runtimes["change-a"], coordinator, state_root, probe, launch, branch_head


_HIDDEN_ACTIVITY = ("ignored-file", "deleted-nested-untracked", "ignored-directory-entry", "deleted-ignored-entry")


def _hidden_activity(worktree: Path, scenario: str, touched: datetime) -> Path:
    """Create worktree activity that `git status --ignored=no` cannot attribute to a listed path."""
    (worktree / ".gitignore").write_text("*.log\nbuild/\n", encoding="utf-8")
    if scenario == "ignored-file":
        target = worktree / "debug.log"
        target.write_text("recent ignored output\n", encoding="utf-8")
    elif scenario == "ignored-directory-entry":
        target = worktree / "build"
        target.mkdir()
        (target / "artifact.bin").write_bytes(b"artifact")
    elif scenario == "deleted-ignored-entry":
        target = worktree / "build"
        target.mkdir()
        (target / "gone.txt").write_text("deleted\n", encoding="utf-8")
        (target / "gone.txt").unlink()
    else:
        target = worktree / "work" / "nested"
        target.mkdir(parents=True)
        (target / "keep.txt").write_text("kept\n", encoding="utf-8")
        (target / "gone.txt").write_text("deleted\n", encoding="utf-8")
        (target / "gone.txt").unlink()
    if scenario != "deleted-nested-untracked":
        _git(worktree, "check-ignore", "-q", str(target.relative_to(worktree)))
    os.utime(target, (touched.timestamp(), touched.timestamp()))
    return target


_IGNORED_CONTENT = {"__pycache__/x.pyc": b"cache", ".venv/lib/x": b"environment"}


def _add_ignored_content(worktree: Path) -> None:
    (worktree / ".gitignore").write_text("__pycache__/\n.venv/\n.ruff_cache/\n", encoding="utf-8")
    for relative, content in _IGNORED_CONTENT.items():
        target = worktree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        _git(worktree, "check-ignore", "-q", relative)


def _churn_ignored_content(worktree: Path) -> None:
    (worktree / "__pycache__" / "x.pyc").write_bytes(b"rewritten cache")
    (worktree / "__pycache__" / "y.pyc").write_bytes(b"new cache")
    (worktree / ".ruff_cache").mkdir()
    (worktree / ".ruff_cache" / "state").write_bytes(b"lint cache")
    (worktree / ".venv" / "lib" / "x").unlink()


def test_host_lock_tracks_real_subprocess_lifetime(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        "from owlbear_delivery.worker_stall import DeliveryHostInstance\n"
        "host = DeliveryHostInstance.acquire(Path(sys.argv[1]))\n"
        "print(host.instance_id, flush=True)\n"
        "sys.stdin.read()\n"
    )
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    process = subprocess.Popen(  # noqa: S603 - fixed interpreter and inline script.
        (sys.executable, "-c", script, str(runtime_root)),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=environment,
        text=True,
    )
    try:
        assert process.stdout is not None
        instance_id = process.stdout.readline().strip()
        probe = HostLockLivenessProbe(runtime_root)
        assert probe.host_state(instance_id) == "alive"
        assert probe.host_state(instance_id) == "alive"
    finally:
        assert process.stdin is not None
        process.stdin.close()
        process.wait(timeout=30)
    assert probe.host_state(instance_id) == "lost"
    assert probe.host_state("b" * 32) == "unknown"
    assert probe.host_state("../escape") == "unknown"

    own = DeliveryHostInstance.acquire(runtime_root)
    try:
        assert probe.host_state(own.instance_id) == "alive"
    finally:
        own.close()
    assert probe.host_state(own.instance_id) == "lost"


@pytest.mark.parametrize("ignored_content", ["no-ignored", "ignored-caches"])
def test_host_lost_quiet_builder_settles_and_resumes_same_task_with_preserved_work(
    tmp_path: Path, ignored_content: str
) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, state_root, probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    if ignored_content == "ignored-caches":
        _add_ignored_content(launch.worktree_path)
    issuer = json.loads(_issuer_path(state_root, "change-a", launch.claim.attempt_id).read_bytes())
    assert issuer == {
        "schema_version": 1,
        "change_id": "change-a",
        "outcome_id": launch.outcome_id,
        "attempt_id": launch.claim.attempt_id,
        "claim_id": launch.claim.claim_id,
        "role": "builder",
        "issuer_instance": _HOST,
        "issued_at": launch.claim.started_at,
    }
    before_workspace = _workspace_content_snapshot(launch.worktree_path)
    probe.states[_HOST] = "lost"
    now[0] = _iso(start + timedelta(minutes=10))

    application.acquire_change_action(_continuation_request(application, "change-a"))

    settled = runtime.show_binding(launch.outcome_id)
    assert settled.active_claim is None
    assert settled.block is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-task"
    assert settled.builder_handoff_context.branch_head == branch_head
    assert coordinator.show("change-a").builder_handoff is not None
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace
    assert _owner_failure_code(state_root, "change-a", launch.claim.attempt_id) == "worker-host-lost"
    late_result = _task_result(
        "RESULT-LATE-HOST-LOST",
        "change-a",
        runtime.authority_digest,
        settled.tasks[0],
        branch_head,
    )
    with pytest.raises(DeliveryRuntimeConflictError):
        runtime.publish_result(
            PublishDeliveryResult(outcome_id=launch.outcome_id, claim_id=launch.claim.claim_id, result=late_result)
        )
    with pytest.raises(DeliveryRuntimeConflictError):
        application.settle_worker_invocation(
            DeliveryBuilderInvocationSettlement(
                change_id="change-a",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                attempt_id=launch.claim.attempt_id,
                task_id=launch.task_id,
                expected_last_reviewed_commit=launch.last_reviewed_commit,
                disposition="ended-without-result",
            ),
            host_id=launch.claim.owner_id,
            session_id=launch.claim.process_id,
        )

    probe.states[_HOST] = "alive"
    now[0] = _iso(start + timedelta(hours=2))
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None, resumed_result
    resumed = resumed_result.launch
    assert resumed.claim.task_id == launch.task_id
    assert resumed.claim.attempt_id != launch.claim.attempt_id
    assert resumed.builder_handoff_context == settled.builder_handoff_context
    assert _workspace_content_snapshot(resumed.worktree_path) == before_workspace
    context = application.show_build_context(
        resumed.change_id, resumed.outcome_id, resumed.claim.attempt_id, resumed.claim.claim_id
    )
    assert _builder_retry_history(context.prior_attempts) == [(1, "original", "failed", "worker-host-lost")]


def test_host_lost_recent_worktree_change_waits_until_exact_quiet_boundary(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    worktree = application._workspace_manager.show("change-a").worktree_path
    touched = start + timedelta(minutes=5)
    activity = worktree / "planner-notes.txt"
    activity.write_text("recent\n", encoding="utf-8")
    os.utime(activity, (touched.timestamp(), touched.timestamp()))
    probe.states[_HOST] = "lost"
    eligible = touched + _QUIET
    now[0] = _iso(eligible - timedelta(seconds=1))
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()

    result = application.acquire_frontier_work()

    assert result.launch_packages == ()
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    for readiness in (
        application.get_change("change-a").readiness,
        application.show_work_item_view("change-a", "outcome:OUT-001").readiness,
    ):
        assert readiness is not None
        assert readiness.status == "waiting"
        assert readiness.reason_code == "worker-stall-wait"
        assert readiness.executable is False
        assert readiness.next_eligible_at == _iso(eligible)
    application.acquire_change_action(_continuation_request(application, "change-a"))
    assert runtime.frontier_bytes() == frontier_before

    now[0] = _iso(eligible)
    application.acquire_frontier_work()

    assert runtime.show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


@pytest.mark.parametrize("case", ["live-host", "unknown-host", "no-issuer-record"])
def test_stall_sweep_leaves_claims_without_host_loss_evidence(tmp_path: Path, case: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    if case == "unknown-host":
        probe.states[_HOST] = "unknown"
    elif case == "no-issuer-record":
        _issuer_path(state_root, "change-a", claim.attempt_id).unlink()
        probe.states[_HOST] = "lost"
    now[0] = _iso(start + timedelta(minutes=30))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()

    application.acquire_frontier_work()
    application.acquire_change_action(_continuation_request(application, "change-a"))

    assert runtime.frontier_bytes() == frontier_before
    readiness = application.show_work_item_view("change-a", "outcome:OUT-001").readiness
    assert readiness is not None
    assert readiness.status == "running"
    assert readiness.reason_code == "active-custody"


def test_stall_sweep_isolates_an_unreadable_issuer_record_to_its_change(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}, now
    )
    launches = {launch.change_id: launch for launch in application.acquire_frontier_work().launch_packages}
    assert set(launches) == {"change-a", "change-b"}
    _issuer_path(state_root, "change-a", launches["change-a"].claim.attempt_id).write_bytes(b"{not-json")
    probe.states[_HOST] = "lost"
    now[0] = _iso(start + timedelta(minutes=30))
    blocked_before = runtimes["change-a"].frontier_bytes()

    result = application.acquire_frontier_work()

    assert runtimes["change-a"].frontier_bytes() == blocked_before
    assert runtimes["change-b"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-b", launches["change-b"].claim.attempt_id) == "worker-host-lost"
    assert any(failure.change_id == "change-a" for failure in result.failures)


def test_release_stuck_worker_settles_quiet_planner_and_replays(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    now[0] = _iso(start + timedelta(minutes=10))

    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert settled.active_claim is None
    assert runtimes["change-a"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-released-stuck"
    frontier = runtimes["change-a"].frontier_bytes()
    assert application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id) == settled
    assert runtimes["change-a"].frontier_bytes() == frontier
    with pytest.raises(DeliveryRuntimeConflictError):
        application.settle_worker_invocation(
            DeliveryPlanningRetrySettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id=claim.claim_id,
                attempt_id=claim.attempt_id,
                disposition="ended-without-result",
            )
        )


def test_release_stuck_worker_refuses_active_worktree_without_mutation(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, _state_root, _probe, launch, _head = _builder_with_workspace_changes(
        tmp_path, now
    )
    touched = start + timedelta(minutes=5)
    os.utime(launch.worktree_path / "untracked.txt", (touched.timestamp(), touched.timestamp()))
    now[0] = _iso(touched + timedelta(seconds=30))
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    coordination_before = coordinator.show("change-a")
    workspace_before = _workspace_content_snapshot(launch.worktree_path)

    with pytest.raises(DeliveryWorkerActiveError) as raised:
        application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    assert raised.value.code == "ERR_DELIVERY_WORKER_ACTIVE"
    assert raised.value.retry_after == touched + _QUIET
    assert "unchanged" in str(raised.value)
    assert _iso(touched + _QUIET) in str(raised.value)
    classification = classify_delivery_failure(raised.value)
    assert classification is not None
    assert classification.code == "ERR_DELIVERY_WORKER_ACTIVE"
    assert classification.category is DeliveryFailureCategory.CONFLICT
    assert classification.retry_safe is True
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    assert coordinator.show("change-a") == coordination_before
    assert _workspace_content_snapshot(launch.worktree_path) == workspace_before


@pytest.mark.parametrize("scenario", _HIDDEN_ACTIVITY)
def test_release_stuck_worker_refuses_recent_activity_hidden_from_status(tmp_path: Path, scenario: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, _state_root, _probe, launch, _head = _builder_with_workspace_changes(
        tmp_path, now
    )
    touched = start + timedelta(minutes=5)
    target = _hidden_activity(launch.worktree_path, scenario, touched)
    now[0] = _iso(touched + timedelta(seconds=30))
    target_times = target.lstat().st_mtime_ns, target.lstat().st_ctime_ns
    before = (
        runtime.frontier_bytes(),
        runtime.retry_ledger().read(),
        coordinator.show("change-a"),
        _workspace_content_snapshot(launch.worktree_path),
    )

    with pytest.raises(DeliveryWorkerActiveError) as raised:
        application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    assert raised.value.code == "ERR_DELIVERY_WORKER_ACTIVE"
    assert raised.value.retry_after == touched + _QUIET
    assert (target.lstat().st_mtime_ns, target.lstat().st_ctime_ns) == target_times
    assert (
        runtime.frontier_bytes(),
        runtime.retry_ledger().read(),
        coordinator.show("change-a"),
        _workspace_content_snapshot(launch.worktree_path),
    ) == before


@pytest.mark.parametrize("scenario", _HIDDEN_ACTIVITY)
def test_release_stuck_worker_settles_planner_once_hidden_activity_is_quiet(tmp_path: Path, scenario: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    touched = start + timedelta(minutes=5)
    _hidden_activity(application._workspace_manager.show("change-a").worktree_path, scenario, touched)
    now[0] = _iso(touched + _QUIET - timedelta(seconds=1))
    with pytest.raises(DeliveryWorkerActiveError):
        application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
    now[0] = _iso(touched + _QUIET)

    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert settled.active_claim is None
    assert runtimes["change-a"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-released-stuck"


def test_release_stuck_worker_hands_off_builder_once_deleted_nested_path_is_quiet(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, _coordinator, state_root, _probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    touched = start + timedelta(minutes=5)
    _hidden_activity(launch.worktree_path, "deleted-nested-untracked", touched)
    now[0] = _iso(touched + _QUIET)

    application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    settled = runtime.show_binding(launch.outcome_id)
    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-task"
    assert settled.builder_handoff_context.branch_head == branch_head
    assert _owner_failure_code(state_root, "change-a", launch.claim.attempt_id) == "worker-released-stuck"


@pytest.mark.parametrize("bound", ["entries", "time"])
def test_release_stuck_worker_refuses_when_activity_walk_exceeds_its_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: str
) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    worktree = application._workspace_manager.show("change-a").worktree_path
    (worktree / "build").mkdir()
    (worktree / "build" / "old.bin").write_bytes(b"old")
    now[0] = _iso(start + timedelta(minutes=10))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    if bound == "entries":
        monkeypatch.setattr(change_workspace, "_ACTIVITY_WALK_MAX_ENTRIES", 1)
    else:
        monkeypatch.setattr(change_workspace, "_ACTIVITY_WALK_SECONDS", 0.0)

    with pytest.raises(DeliveryWorkerActiveError) as raised:
        application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert raised.value.retry_after is None
    assert runtime.frontier_bytes() == frontier_before
    assert runtime.retry_ledger().read() == ledger_before
    monkeypatch.undo()
    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)
    assert settled.active_claim is None


def test_host_lost_waits_for_deletion_inside_ignored_directory(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    worktree = application._workspace_manager.show("change-a").worktree_path
    touched = start + timedelta(minutes=5)
    _hidden_activity(worktree, "deleted-ignored-entry", touched)
    probe.states[_HOST] = "lost"
    now[0] = _iso(touched + timedelta(seconds=30))
    frontier_before = runtime.frontier_bytes()

    assert application.acquire_frontier_work().launch_packages == ()

    assert runtime.frontier_bytes() == frontier_before
    readiness = application.show_work_item_view("change-a", "outcome:OUT-001").readiness
    assert readiness is not None
    assert readiness.reason_code == "worker-stall-wait"
    assert readiness.next_eligible_at == _iso(touched + _QUIET)

    now[0] = _iso(touched + _QUIET)
    application.acquire_frontier_work()

    assert runtime.show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-host-lost"


def test_ended_builder_with_ignored_content_resumes_same_task_despite_cache_churn(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, _runtime, coordinator, _state_root, _probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    _add_ignored_content(launch.worktree_path)
    before_workspace = _workspace_content_snapshot(launch.worktree_path)

    settled = application.settle_worker_invocation(
        _requestless_builder_settlement(launch, "ended-without-result"),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )

    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-task"
    assert settled.builder_handoff_context.branch_head == branch_head
    assert coordinator.show("change-a").builder_handoff is not None
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace
    waiting = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert waiting.launch is None
    assert waiting.reason_code == "retry-backoff"
    _churn_ignored_content(launch.worktree_path)
    after_churn = _workspace_content_snapshot(launch.worktree_path)

    now[0] = _iso(start + timedelta(hours=1))
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))

    assert resumed_result.launch is not None, resumed_result
    resumed = resumed_result.launch
    assert resumed.claim.task_id == launch.task_id
    assert resumed.claim.attempt_id != launch.claim.attempt_id
    assert resumed.builder_handoff_context == settled.builder_handoff_context
    assert _workspace_content_snapshot(resumed.worktree_path) == after_churn
    assert (resumed.worktree_path / ".ruff_cache" / "state").read_bytes() == b"lint cache"


def _drift_handoff_workspace(worktree: Path, drift: str) -> None:
    if drift == "tracked":
        (worktree / "committed.txt").write_text("drifted tracked work\n", encoding="utf-8")
    elif drift == "untracked":
        (worktree / "post-handoff.txt").write_text("drifted untracked work\n", encoding="utf-8")
    elif drift == "staged":
        _git(worktree, "add", "untracked.txt")
    else:
        (worktree / "committed.txt").write_text("drifted committed work\n", encoding="utf-8")
        _git(worktree, "commit", "-m", "drift head", "--", "committed.txt")


@pytest.mark.parametrize("drift", ["tracked", "untracked", "staged", "head"])
def test_builder_handoff_with_ignored_churn_still_refuses_preserved_work_drift(tmp_path: Path, drift: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, coordinator, _state_root, _probe, launch, _branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    _add_ignored_content(launch.worktree_path)
    application.settle_worker_invocation(
        _requestless_builder_settlement(launch, "ended-without-result"),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )
    handoff = coordinator.show("change-a").builder_handoff
    assert handoff is not None
    _churn_ignored_content(launch.worktree_path)
    _drift_handoff_workspace(launch.worktree_path, drift)
    drifted = _workspace_content_snapshot(launch.worktree_path)
    now[0] = _iso(start + timedelta(hours=1))

    result = application.acquire_change_action(_continuation_request(application, "change-a"))

    assert result.launch is None, result
    assert result.kind == "unavailable", result
    assert runtime.active_claims() == ()
    assert coordinator.show("change-a").builder_handoff == handoff
    assert _workspace_content_snapshot(launch.worktree_path) == drifted


def test_release_stuck_builder_with_ignored_content_hands_off_and_resumes(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, _coordinator, state_root, _probe, launch, branch_head = _builder_with_workspace_changes(
        tmp_path, now
    )
    _add_ignored_content(launch.worktree_path)
    before_workspace = _workspace_content_snapshot(launch.worktree_path)
    now[0] = _iso(start + timedelta(minutes=10))

    application.release_stuck_worker("change-a", launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id)

    settled = runtime.show_binding(launch.outcome_id)
    assert settled.active_claim is None
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.branch_head == branch_head
    assert _owner_failure_code(state_root, "change-a", launch.claim.attempt_id) == "worker-released-stuck"
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace
    now[0] = _iso(start + timedelta(hours=2))
    resumed_result = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert resumed_result.launch is not None, resumed_result
    assert resumed_result.launch.claim.task_id == launch.task_id
    assert _workspace_content_snapshot(launch.worktree_path) == before_workspace


def test_activity_ignores_deep_writes_inside_ignored_directories(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, _runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    manager = application._workspace_manager
    worktree = manager.show("change-a").worktree_path
    (worktree / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    deep = worktree / ".venv" / "lib" / "site-packages" / "pkg" / "x.py"
    deep.parent.mkdir(parents=True)
    deep.write_text("cache\n", encoding="utf-8")
    touched = start + timedelta(minutes=5)
    os.utime(deep, (touched.timestamp(), touched.timestamp()))

    # Documented limitation: tool caches and environments below an ignored directory are not observed.
    assert manager.observe_worktree_activity("change-a") < touched


def test_activity_observes_large_ignored_tree_within_entry_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    worktree = application._workspace_manager.show("change-a").worktree_path
    (worktree / ".gitignore").write_text("build/\n", encoding="utf-8")
    (worktree / "build").mkdir()
    for index in range(5_000):
        (worktree / "build" / f"{index}.bin").write_bytes(b"x")
    monkeypatch.setattr(change_workspace, "_ACTIVITY_WALK_MAX_ENTRIES", 1_000)
    now[0] = _iso(start + timedelta(minutes=10))

    settled = application.release_stuck_worker("change-a", "OUT-001", claim.attempt_id, claim.claim_id)

    assert settled.active_claim is None
    assert runtimes["change-a"].show_binding("OUT-001").active_claim is None
    assert _owner_failure_code(state_root, "change-a", claim.attempt_id) == "worker-released-stuck"


def test_release_stuck_worker_requires_exact_active_identity(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    now[0] = _iso(start + timedelta(minutes=10))
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()
    ledger_before = runtime.retry_ledger().read()
    for outcome_id, attempt_id, claim_id in (
        ("OUT-001", "foreign-attempt", claim.claim_id),
        ("OUT-001", claim.attempt_id, "foreign-claim"),
        ("OUT-002", claim.attempt_id, claim.claim_id),
    ):
        with pytest.raises((DeliveryRuntimeConflictError, PortfolioApplicationError, KeyError, ValueError)):
            application.release_stuck_worker("change-a", outcome_id, attempt_id, claim_id)
        assert runtime.frontier_bytes() == frontier_before
        assert runtime.retry_ledger().read() == ledger_before


def test_callers_cannot_submit_engine_worker_dispositions(tmp_path: Path) -> None:
    for disposition in ("host-lost", "released-stuck"):
        with pytest.raises(ValidationError):
            DeliveryPlanningRetrySettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id="claim",
                attempt_id="attempt",
                disposition=disposition,
            )
        with pytest.raises(ValidationError):
            DeliveryBuilderInvocationSettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id="claim",
                attempt_id="attempt",
                task_id="TASK-001",
                expected_last_reviewed_commit="a" * 40,
                disposition=disposition,
            )
    for failure_code in ("worker-host-lost", "worker-released-stuck"):
        with pytest.raises(ValidationError):
            DeliveryPlanningRetrySettlement(
                change_id="change-a",
                outcome_id="OUT-001",
                claim_id="claim",
                attempt_id="attempt",
                disposition="normal-return",
                request=RetryDelivery(
                    action="retry", outcome_id="OUT-001", claim_id="claim", failure_code=failure_code
                ),
            )

    now = [_iso(_real_now() + timedelta(minutes=10))]
    application, runtimes, _coordinator, _state_root, _probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    claim = _acquire_planning_claim(application)
    runtime = runtimes["change-a"]
    frontier_before = runtime.frontier_bytes()
    forged = DeliveryEnginePlanningSettlement(
        change_id="change-a",
        outcome_id="OUT-001",
        claim_id=claim.claim_id,
        attempt_id=claim.attempt_id,
        disposition="host-lost",
    )
    with pytest.raises(PortfolioApplicationError):
        application.settle_worker_invocation(forged, host_id=claim.owner_id, session_id=claim.process_id)
    assert runtime.frontier_bytes() == frontier_before
    assert DeliveryEngineBuilderSettlement.model_fields["disposition"].annotation is not None


def test_engine_and_caller_worker_endings_share_one_exhausting_builder_episode(tmp_path: Path) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, runtime, _coordinator, state_root, probe, launch, _head = _builder_with_workspace_changes(
        tmp_path, now
    )
    workspace = _workspace_content_snapshot(launch.worktree_path)
    attempt_ids = [launch.claim.attempt_id]

    probe.states[_HOST] = "lost"
    now[0] = _iso(start + timedelta(minutes=10))
    application.acquire_frontier_work()
    assert runtime.show_binding(launch.outcome_id).active_claim is None
    probe.states[_HOST] = "alive"

    now[0] = _iso(start + timedelta(hours=2))
    second = application.acquire_change_action(_continuation_request(application, "change-a")).launch
    assert second is not None
    attempt_ids.append(second.claim.attempt_id)
    application.release_stuck_worker("change-a", second.outcome_id, second.claim.attempt_id, second.claim.claim_id)

    now[0] = _iso(start + timedelta(hours=4))
    third = application.acquire_change_action(_continuation_request(application, "change-a")).launch
    assert third is not None
    attempt_ids.append(third.claim.attempt_id)
    application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=third.change_id,
            outcome_id=third.outcome_id,
            claim_id=third.claim.claim_id,
            attempt_id=third.claim.attempt_id,
            task_id=third.task_id,
            expected_last_reviewed_commit=third.last_reviewed_commit,
            disposition="normal-return",
            request=RetryDelivery(
                action="retry",
                outcome_id=third.outcome_id,
                claim_id=third.claim.claim_id,
                attempt_id=third.claim.attempt_id,
                abandoned_commit=_git(third.worktree_path, "rev-parse", "HEAD"),
                failure_code="builder-failed",
            ),
        ),
        host_id=third.claim.owner_id,
        session_id=third.claim.process_id,
    )

    assert _workspace_content_snapshot(launch.worktree_path) == workspace
    binding = runtime.show_binding(launch.outcome_id)
    assert binding.block is not None
    assert "three-attempt limit" in binding.block.reason
    episodes = runtime.retry_ledger().read().episodes
    assert len(episodes) == 1
    assert episodes[0].total_attempts == 3
    assert episodes[0].attempt_ids == tuple(attempt_ids)
    assert [_owner_failure_code(state_root, "change-a", attempt) for attempt in attempt_ids] == [
        "worker-host-lost",
        "worker-released-stuck",
        "builder-failed",
    ]
    now[0] = _iso(start + timedelta(hours=8))
    assert application.acquire_change_action(_continuation_request(application, "change-a")).launch is None
    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    assert view.readiness is not None
    assert view.readiness.reason_code == "retry-exhausted"


@pytest.mark.parametrize("mode", ["host-lost", "released-stuck"])
def test_ended_finalizer_settles_as_reported_attention_and_retries_under_one_budget(tmp_path: Path, mode: str) -> None:
    start = _real_now()
    now = [_iso(start)]
    application, _runtimes, coordinator, state_root, probe = _stall_portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED}, now
    )
    first = application.acquire_change_action(_continuation_request(application))
    assert first.finalization is not None
    attempt = first.finalization.attempt
    issuer = json.loads(_issuer_path(state_root, "change-a", attempt.writer.attempt_id).read_bytes())
    assert (issuer["role"], issuer["outcome_id"], issuer["claim_id"]) == ("finalizer", None, attempt.writer.claim_id)
    forged_report = ReportFinalizationFailure(
        change_id="change-a",
        expected_contract_digest=attempt.contract_digest,
        expected_frontier_digest=attempt.frontier_digest,
        expected_change_head=attempt.exact_head,
        expected_reviewed_head=coordinator.show("change-a").last_reviewed_commit,
        expected_diagnostic_sequence=0,
        attempt_key=attempt.writer.attempt_id,
        category="worker-ended",
        code=FinalizationFailureCode.FINALIZER_ENDED_WITHOUT_REPORT,
        checks_state="unknown",
    )
    with pytest.raises(FinalizationReportError):
        application.report_finalization_failure(forged_report)
    with pytest.raises(ValidationError):
        ReportFinalizationFailure.model_validate_json(
            json.dumps({**forged_report.model_dump(mode="json"), "checks_state": "failed"})
        )
    now[0] = _iso(start + timedelta(minutes=10))

    if mode == "host-lost":
        probe.states[_HOST] = "lost"
        application.acquire_frontier_work()
        probe.states[_HOST] = "alive"
    else:
        released = application.release_stuck_worker(
            "change-a", None, attempt.writer.attempt_id, attempt.writer.claim_id
        )
        assert isinstance(released, FinalizerSettlementReceipt)
        assert (
            application.release_stuck_worker("change-a", None, attempt.writer.attempt_id, attempt.writer.claim_id)
            == released
        )

    receipt = application._read_finalizer_settlement_receipt("change-a", attempt.writer.attempt_id)
    assert receipt is not None
    assert isinstance(receipt.settlement, FinalizerEngineSettlement)
    assert receipt.settlement.disposition == mode
    assert receipt.settlement.outcome == "ended-without-report"
    request = receipt.report.request
    assert (request.category, request.code, request.checks_state) == (
        "worker-ended",
        FinalizationFailureCode.FINALIZER_ENDED_WITHOUT_REPORT,
        "unknown",
    )
    attention = coordinator.show("change-a").finalization_attention
    assert attention is not None
    assert attention.outcome == "ended-without-report"
    assert _owner_failure_code(state_root, "change-a", attempt.writer.attempt_id) == "finalizer-ended-without-report"
    with pytest.raises(DeliveryActionBusyError):
        application.finalize_change(
            "change-a",
            _finalization_request("change-a", attempt.exact_head, attempt.writer.attempt_id),
        )
    with pytest.raises(DeliveryActionSelectionConflictError):
        application.settle_finalizer_invocation(receipt.settlement)

    now[0] = _iso(start + timedelta(hours=2))
    retry = application.acquire_change_action(
        _continuation_request(application, host_id="retry-host", session_id="retry-session")
    )
    assert retry.kind == "acquired", retry
    assert retry.finalization is not None
    second = retry.finalization.attempt
    assert second.writer.attempt_id != attempt.writer.attempt_id
    assert second.exact_head == attempt.exact_head
    episodes = RetryLedger(state_root, "change-a").read().episodes
    assert len(episodes) == 1
    assert episodes[0].total_attempts == 2
    assert {attempt.writer.attempt_id, second.writer.attempt_id} <= set(episodes[0].attempt_ids)
