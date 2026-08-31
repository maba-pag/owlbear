from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_delivery.change_workspace import (
    AdoptExternalHead,
    BlockedImplementationRecoveryReceipt,
    CapacityConfigurationConflictError,
    CapacityLedger,
    CapacityLedgerConflictError,
    ChangeCoordination,
    ChangeDesignPackageSnapshotReceipt,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeWorkspaceManager,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    PromoteExternalHead,
    PublicationBaselineUnavailableError,
    PublicationLease,
    RecoverBlockedImplementation,
    SyncChangeWithTarget,
    WriterIdentity,
)
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant
from owlbear_delivery.target_authority import Outcome, PlanScopeKind, TargetAuthority, TaskPlanScope
from owlbear_delivery.target_runtime import TargetJob, TargetRuntime


def _runtime(root: Path, change_id: str, job_id: int) -> TargetRuntime:
    authority = TargetAuthority(
        change_id=change_id,
        title=f"Change {change_id}",
        outcomes=(
            Outcome(
                outcome_id="OUT-001",
                title="Outcome",
                promise="Deliver the outcome",
                acceptance=("The outcome is observable",),
            ),
        ),
        task_plan_scopes=(TaskPlanScope(scope_id="PLAN-001", kind=PlanScopeKind.OUTCOME, target_id="OUT-001"),),
    )
    runtime = TargetRuntime(authority, root / change_id)
    runtime.materialize(
        (
            TargetJob(
                job_id=job_id,
                kind="plan",
                change_id=change_id,
                authority_digest=runtime.authority_digest,
                work_item_id="OUT-001",
                plan_scope_id="PLAN-001",
                created_at=f"2026-08-02T00:00:0{job_id}Z",
            ),
        )
    )
    return runtime


def _coordination(root: Path, change_id: str) -> ChangeCoordination:
    return ChangeCoordination(
        change_id=change_id,
        branch=f"owlbear/change/{change_id}",
        worktree_path=root / "worktrees" / change_id,
        integration_target="main",
        target_head="a" * 40,
        last_reviewed_commit="a" * 40,
    )


def _identity(change_id: str) -> WriterIdentity:
    return WriterIdentity(
        attempt_id=f"attempt-{change_id}",
        claim_id=f"claim-{change_id}",
        actor_id="builder",
        process_id=f"process-{change_id}",
        claimed_at="2026-08-02T00:01:00Z",
    )


def test_portfolio_coordinates_independent_changes_but_rejects_second_writer(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    coordinator.register(_coordination(tmp_path, "change-a"))
    coordinator.register(_coordination(tmp_path, "change-b"))
    first = coordinator.acquire(
        "change-a",
        ChangeWriter(**_identity("change-a").model_dump(), job_id=1, kind="build"),
    )
    second = coordinator.acquire(
        "change-b",
        ChangeWriter(**_identity("change-b").model_dump(), job_id=2, kind="build"),
    )

    assert first.writer is not None
    assert second.writer is not None
    with pytest.raises(CoordinationConflictError, match="active writer"):
        coordinator.acquire(
            "change-a",
            ChangeWriter(**_identity("change-a").model_dump(), job_id=3, kind="build"),
        )


def test_coordinator_migrates_legacy_coordination_directory(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    legacy_root = state_root / "claims/changes"
    legacy_root.mkdir(parents=True)
    coordination = _coordination(tmp_path, "legacy-coordination")
    (legacy_root / "legacy-coordination.json").write_bytes(coordination.model_dump_json().encode())

    coordinator = PortfolioCoordinator(state_root, capacity=1)

    assert coordinator.show("legacy-coordination") == coordination
    assert (state_root / "coordination/changes/legacy-coordination.json").is_file()
    assert not legacy_root.exists()


def test_coordinator_rejects_both_coordination_directories(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    (state_root / "coordination/changes").mkdir(parents=True)
    (state_root / "claims/changes").mkdir(parents=True)

    with pytest.raises(CoordinationConflictError, match="both coordination directories"):
        PortfolioCoordinator(state_root, capacity=1)


def test_publication_reservation_excludes_writers_and_boundary_updates(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    coordinator.register(_coordination(tmp_path, "publish-change"))
    now = datetime.now(UTC)

    with coordinator.publication_lock("publish-change") as lock:
        reserved = coordinator.reserve_publication(
            "publish-change",
            PublicationLease(
                operation_id="operation-1",
                owner_id="owner-1",
                expires_at=(now + timedelta(minutes=10)).isoformat(),
            ),
            lock,
            now=now.isoformat(),
        )

    assert reserved.publication_lease is not None
    assert reserved.publication_lease.operation_id == "operation-1"
    with pytest.raises(CoordinationConflictError, match="active writer"):
        coordinator.acquire(
            "publish-change",
            ChangeWriter(**_identity("publish-change").model_dump(), job_id=1, kind="build"),
        )
    with pytest.raises(CoordinationConflictError, match="reserved publication boundary"):
        coordinator.update(reserved.model_copy(update={"target_head": "b" * 40}))
    with coordinator.publication_lock("publish-change") as lock:
        with pytest.raises(CoordinationConflictError, match="does not own"):
            coordinator.release_publication("publish-change", "operation-1", "owner-2", lock)
        released = coordinator.release_publication("publish-change", "operation-1", "owner-1", lock)

    assert released.publication_lease is None
    with pytest.raises(ValueError, match="active publication lock"):
        coordinator.release_publication("publish-change", "operation-1", "owner-1", lock)


def test_publication_locks_allow_independent_changes_concurrently(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    coordinator.register(_coordination(tmp_path, "change-a"))
    coordinator.register(_coordination(tmp_path, "change-b"))

    with (
        coordinator.publication_lock("change-a", blocking=False),
        coordinator.publication_lock("change-b", blocking=False),
    ):
        pass


def test_publication_lease_rejects_concurrent_owner_and_allows_expired_takeover(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    coordinator.register(_coordination(tmp_path, "lease-change"))
    with coordinator.publication_lock("lease-change") as lock:
        coordinator.reserve_publication(
            "lease-change",
            PublicationLease(
                operation_id="operation-1",
                owner_id="owner-1",
                expires_at="2026-08-02T00:10:00Z",
            ),
            lock,
            now="2026-08-02T00:00:00Z",
        )
        with pytest.raises(CoordinationConflictError, match="active ownership"):
            coordinator.reserve_publication(
                "lease-change",
                PublicationLease(
                    operation_id="operation-1",
                    owner_id="owner-2",
                    expires_at="2026-08-02T00:15:00Z",
                ),
                lock,
                now="2026-08-02T00:05:00Z",
            )
        recovered = coordinator.reserve_publication(
            "lease-change",
            PublicationLease(
                operation_id="operation-2",
                owner_id="owner-2",
                expires_at="2026-08-02T00:21:00Z",
            ),
            lock,
            now="2026-08-02T00:11:00Z",
        )

    assert recovered.publication_lease is not None
    assert recovered.publication_lease.operation_id == "operation-2"
    assert recovered.publication_lease.owner_id == "owner-2"
    with (
        coordinator.publication_lock("lease-change") as lock,
        pytest.raises(CoordinationConflictError, match="does not own"),
    ):
        coordinator.release_publication("lease-change", "operation-1", "owner-1", lock)


def test_writer_acquisition_recovers_expired_publication_lease(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    coordinator.register(_coordination(tmp_path, "expired-change"))
    with coordinator.publication_lock("expired-change") as lock:
        coordinator.reserve_publication(
            "expired-change",
            PublicationLease(
                operation_id="operation-expired",
                owner_id="owner-expired",
                expires_at="2020-08-02T00:10:00Z",
            ),
            lock,
            now="2020-08-02T00:00:00Z",
        )

    acquired = coordinator.acquire(
        "expired-change",
        ChangeWriter(**_identity("expired-change").model_dump(), job_id=1, kind="build"),
    )

    assert acquired.writer is not None
    assert acquired.publication_lease is None


def test_retired_scalar_publication_reservation_loads_as_abandoned(tmp_path: Path) -> None:
    payload = _coordination(tmp_path, "retired-change").model_dump(mode="json")
    payload["publication_operation_id"] = "operation-retired"
    payload["publication_expires_at"] = "2099-08-02T00:10:00Z"
    payload.pop("publication_base_head")

    coordination = ChangeCoordination.model_validate_json(json.dumps(payload))

    assert coordination.publication_lease is None
    assert coordination.publication_base_head is None


def test_publication_lease_duration_is_bounded(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    coordinator.register(_coordination(tmp_path, "bounded-change"))

    with (
        coordinator.publication_lock("bounded-change") as lock,
        pytest.raises(ValueError, match="maximum duration"),
    ):
        coordinator.reserve_publication(
            "bounded-change",
            PublicationLease(
                operation_id="operation-bounded",
                owner_id="owner-bounded",
                expires_at="2026-08-02T00:10:01Z",
            ),
            lock,
            now="2026-08-02T00:00:00Z",
        )


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_ref_exists(repository: Path, reference: str) -> bool:
    return (
        subprocess.run(  # noqa: S603
            ("git", "-C", str(repository), "rev-parse", "--verify", reference),  # noqa: S607
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _repository(tmp_path: Path, *, target: str = "release") -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Test User")
    _git(repository, "config", "user.email", "test@example.com")
    (repository / "shared.txt").write_text("base\n", encoding="utf-8")
    _git(repository, "add", "shared.txt")
    _git(repository, "commit", "-m", "initial")
    initial = _git(repository, "rev-parse", "HEAD")
    _git(repository, "branch", target, initial)
    _git(repository, "update-ref", f"refs/remotes/origin/{target}", initial)
    return repository, initial


def _manager(tmp_path: Path, repository: Path, *, target: str = "release", remote: str = "origin"):
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, target, remote=remote)
    return coordinator, manager


def _workspace_bytes(repository: Path, state_root: Path) -> tuple[str, str, tuple[tuple[str, bytes], ...]]:
    state_files = tuple(
        sorted(
            (str(path.relative_to(state_root)), path.read_bytes()) for path in state_root.rglob("*") if path.is_file()
        )
    )
    return (
        _git(repository, "show-ref"),
        _git(repository, "worktree", "list", "--porcelain"),
        state_files,
    )


def test_snapshot_design_package_commits_managed_change_worktree_only(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("snapshot-change")
    package_files = {
        "authority.json": b'{"authority":true}\n',
        "design.md": b"# Design\n",
        "intent.md": b"# Intent\n",
        "manifest.json": b'{"manifest":true}\n',
    }
    before_status = _git(repository, "status", "--porcelain")

    receipt = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        package_files,
        "snapshot-operation",
    )
    replayed = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        package_files,
        "snapshot-operation",
    )

    assert isinstance(receipt, ChangeDesignPackageSnapshotReceipt)
    assert replayed == receipt
    assert receipt.previous_head == initial
    assert receipt.snapshot_head != initial
    assert coordinator.show(coordination.change_id).last_reviewed_commit == receipt.snapshot_head
    assert manager.source_head(coordination.change_id) == receipt.snapshot_head
    assert _git(repository, "rev-parse", "HEAD") == initial
    assert _git(repository, "status", "--porcelain") == before_status
    relative_paths = tuple(f".owlbear/delivery/packages/{coordination.change_id}/{name}" for name in package_files)
    assert (
        tuple(
            _git(
                coordination.worktree_path,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                receipt.snapshot_head,
            ).splitlines()
        )
        == relative_paths
    )
    for name, relative_path in zip(package_files, relative_paths, strict=True):
        assert _git(
            coordination.worktree_path, "show", f"{receipt.snapshot_head}:{relative_path}"
        ).encode() == package_files[name].rstrip(b"\n")


def test_snapshot_design_package_replays_after_commit_before_receipt(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("snapshot-replay")
    package_files = {
        "authority.json": b'{"authority":true}\n',
        "design.md": b"# Design\n",
        "intent.md": b"# Intent\n",
        "manifest.json": b'{"manifest":true}\n',
    }
    original_update = coordinator.update
    update_count = 0
    failure_message = "simulated receipt failure"

    def fail_receipt_update(updated: ChangeCoordination, *, lock=None) -> ChangeCoordination:
        nonlocal update_count
        update_count += 1
        if update_count == 2:
            raise RuntimeError(failure_message)
        return original_update(updated, lock=lock)

    with (
        patch.object(coordinator, "update", side_effect=fail_receipt_update),
        pytest.raises(RuntimeError, match=failure_message),
    ):
        manager.snapshot_design_package(
            coordination.change_id,
            "a" * 64,
            package_files,
            "snapshot-replay-operation",
        )

    interrupted = coordinator.show(coordination.change_id)
    assert interrupted.design_package_snapshot_intent is not None
    assert interrupted.design_package_snapshot is None
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") != initial
    assert _git(coordination.worktree_path, "status", "--porcelain") == ""

    receipt = manager.snapshot_design_package(
        coordination.change_id,
        "a" * 64,
        package_files,
        "snapshot-replay-operation",
    )

    assert receipt.snapshot_head == _git(coordination.worktree_path, "rev-parse", "HEAD")
    assert coordinator.show(coordination.change_id).design_package_snapshot == receipt
    assert coordinator.show(coordination.change_id).design_package_snapshot_intent is None
    assert receipt.previous_head == initial


def test_list_retained_worktrees_is_sorted_and_batches_git_reads(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    first = manager.ensure("change-b")
    second = manager.ensure("change-a")
    _git(repository, "update-ref", "refs/heads/owlbear/change/nested-only/s1", initial)
    before_coordination = tuple(
        sorted((path.name, path.read_bytes()) for path in (tmp_path / "state/coordination/changes").iterdir())
    )
    before_worktrees = _git(repository, "worktree", "list", "--porcelain")
    original_run_git = manager._run_git  # noqa: SLF001

    with patch.object(manager, "_run_git", wraps=original_run_git) as run_git:
        retained = manager.list_retained()

    assert [item.change_id for item in retained] == ["change-a", "change-b"]
    assert all(item.coordination_registered and item.git_registered and item.worktree_present for item in retained)
    assert retained[0].worktree_path == second.worktree_path.resolve()
    assert retained[1].worktree_path == first.worktree_path.resolve()
    assert retained[0].branch_head == initial
    assert retained[0].worktree_head == initial
    assert retained[0].worktree_branch == "owlbear/change/change-a"
    assert all("/s1" not in item.branch for item in retained)
    assert [call.args[:3] for call in run_git.call_args_list] == [
        ("worktree", "list", "--porcelain"),
        ("for-each-ref", "--format=%(refname)%00%(objectname)", "refs/heads/owlbear/change"),
        ("--no-optional-locks", "status", "--porcelain=v1"),
        ("--no-optional-locks", "status", "--porcelain=v1"),
    ]
    assert before_worktrees == _git(repository, "worktree", "list", "--porcelain")
    assert before_coordination == tuple(
        sorted((path.name, path.read_bytes()) for path in (tmp_path / "state/coordination/changes").iterdir())
    )


@pytest.mark.parametrize("remote", ["origin", "upstream"])
def test_ensure_bases_new_changes_on_remote_tracking_target(tmp_path: Path, remote: str) -> None:
    repository, initial = _repository(tmp_path)
    if remote != "origin":
        _git(repository, "update-ref", f"refs/remotes/{remote}/release", initial)
    (repository / "shared.txt").write_text("local-only\n", encoding="utf-8")
    _git(repository, "add", "shared.txt")
    _git(repository, "commit", "-m", "advance local target")
    _git(repository, "update-ref", "refs/heads/release", "HEAD")
    local_target_head = _git(repository, "rev-parse", "refs/heads/release")
    _coordinator, manager = _manager(tmp_path, repository, remote=remote)

    coordination = manager.ensure(f"remote-target-{remote}")

    assert local_target_head != initial
    assert coordination.target_head == initial
    assert coordination.publication_base_head == initial
    assert _git(repository, "rev-parse", coordination.branch) == initial


def test_refresh_target_does_not_advance_publication_baseline(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("refresh-baseline")
    (repository / "target.txt").write_text("target\n", encoding="utf-8")
    _git(repository, "add", "target.txt")
    _git(repository, "commit", "-m", "advance target")
    advanced_target = _git(repository, "rev-parse", "HEAD")
    _git(repository, "update-ref", "refs/remotes/origin/release", advanced_target)

    refreshed = manager.refresh_integration_target(coordination.change_id)

    assert refreshed.target_head == advanced_target
    assert refreshed.publication_base_head == initial


def test_legacy_publication_baseline_recovers_once_and_replays(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("legacy-baseline")
    (coordination.worktree_path / "workflow.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "workflow.txt")
    _git(coordination.worktree_path, "commit", "-m", "reviewed Change")
    reviewed_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (tmp_path / "state/coordination/changes/legacy-baseline.json").write_text(json.dumps(payload), encoding="utf-8")
    coordinator.update(
        coordination.model_copy(update={"last_reviewed_commit": reviewed_head, "publication_base_head": None})
    )

    receipt = manager.recover_publication_baseline(
        coordination.change_id,
        reviewed_head,
        initial,
        "recover-baseline",
    )
    replayed = manager.recover_publication_baseline(
        coordination.change_id,
        reviewed_head,
        initial,
        "recover-baseline",
    )

    assert replayed == receipt
    recovered = coordinator.show(coordination.change_id)
    assert recovered.publication_base_head == initial
    assert recovered.publication_baseline_recovery == receipt
    with pytest.raises(CoordinationConflictError, match="different authority"):
        manager.recover_publication_baseline(coordination.change_id, reviewed_head, initial, "other-operation")


def test_released_blocked_implementation_recovery_preserves_and_reanchors_candidate(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("blocked-recovery")
    candidate = _commit_new_file(
        coordination.worktree_path,
        "candidate.txt",
        "preserve this candidate\n",
        "preserve blocked candidate",
    )
    request = RecoverBlockedImplementation(
        change_id=coordination.change_id,
        outcome_id="OUT-001",
        expected_resume_commit=candidate,
        expected_reviewed_head=initial,
        operation_id="recover-blocked-candidate",
    )

    receipt = manager.recover_blocked_implementation(request)
    replayed = manager.recover_blocked_implementation(request)

    assert isinstance(receipt, BlockedImplementationRecoveryReceipt)
    assert replayed == receipt
    assert receipt.preserved_commit == candidate
    assert receipt.reviewed_head == initial
    assert _git(repository, "rev-parse", coordination.branch) == initial
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == initial
    assert _git(repository, "rev-parse", receipt.preserved_ref) == candidate
    recovered = coordinator.show(coordination.change_id)
    assert "blocked_implementation_recovery" not in recovered.model_dump(mode="json")

    with pytest.raises(CoordinationConflictError, match="candidate was not preserved"):
        manager.recover_blocked_implementation(request.model_copy(update={"operation_id": "other-operation"}))


@pytest.mark.parametrize("custody", ["writer", "publication lease"])
def test_publication_baseline_recovery_requires_idle_change(tmp_path: Path, custody: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"busy-{custody.replace(' ', '-')}")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (tmp_path / f"state/coordination/changes/{coordination.change_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    if custody == "writer":
        coordinator.acquire(
            coordination.change_id,
            ChangeWriter(
                **_identity(coordination.change_id).model_dump(),
                job_id=1,
                kind="build",
            ),
        )
    else:
        with coordinator.publication_lock(coordination.change_id) as lock:
            coordinator.reserve_publication(
                coordination.change_id,
                PublicationLease(
                    operation_id="busy-lease",
                    owner_id="busy-owner",
                    expires_at="2026-08-02T00:10:00Z",
                ),
                lock,
                now="2026-08-02T00:00:00Z",
            )

    with pytest.raises(CoordinationConflictError, match="idle Change"):
        manager.recover_publication_baseline(coordination.change_id, initial, initial, "recover-busy")


@pytest.mark.parametrize("baseline_kind", ["missing", "non-ancestor"])
def test_publication_baseline_recovery_rejects_unusable_baseline(tmp_path: Path, baseline_kind: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"invalid-{baseline_kind}")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (tmp_path / f"state/coordination/changes/{coordination.change_id}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    baseline = "f" * 40
    if baseline_kind == "non-ancestor":
        baseline = _git(repository, "commit-tree", f"{initial}^{{tree}}", "-m", "unrelated baseline")

    with pytest.raises(PublicationBaselineUnavailableError):
        manager.recover_publication_baseline(coordination.change_id, initial, baseline, f"recover-{baseline_kind}")

    recovered = coordinator.show(coordination.change_id)
    assert recovered.publication_base_head is None
    assert recovered.publication_baseline_recovery is None


def test_generic_update_cannot_replace_or_erase_known_publication_baseline(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("immutable-baseline")

    with pytest.raises(CoordinationConflictError, match="explicit recovery"):
        coordinator.update(coordination.model_copy(update={"publication_base_head": None}))
    with pytest.raises(CoordinationConflictError, match="explicit recovery"):
        coordinator.update(coordination.model_copy(update={"publication_base_head": "b" * 40}))

    assert coordinator.show(coordination.change_id).publication_base_head == initial


def test_legacy_publication_summary_fails_closed_without_baseline(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("unknown-baseline")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (repository / "target.txt").write_text("target\n", encoding="utf-8")
    _git(repository, "add", "target.txt")
    _git(repository, "commit", "-m", "advance target")
    target_head = _git(repository, "rev-parse", "HEAD")
    payload["target_head"] = target_head
    (tmp_path / "state/coordination/changes/unknown-baseline.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PublicationBaselineUnavailableError, match="explicitly known baseline"):
        manager.repository_automation_paths(coordination.change_id, initial)


def test_repository_automation_paths_reports_changed_workflow_and_action_files(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    (repository / ".github/workflows").mkdir(parents=True)
    (repository / ".github/workflows/old.yml").write_text("name: old\n", encoding="utf-8")
    (repository / "action.yml").write_text("name: root\n", encoding="utf-8")
    (repository / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "seed automation")
    baseline = _git(repository, "rev-parse", "HEAD")
    _git(repository, "branch", "-f", "release", baseline)
    _git(repository, "update-ref", "refs/remotes/origin/release", baseline)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("automation-paths")

    worktree = coordination.worktree_path
    _git(worktree, "mv", ".github/workflows/old.yml", ".github/workflows/new.yml")
    _git(worktree, "rm", "action.yml")
    (worktree / ".github/workflows/created.yaml").write_text("name: created\n", encoding="utf-8")
    (worktree / "nested").mkdir()
    (worktree / "nested/action.yaml").write_text("name: nested\n", encoding="utf-8")
    (worktree / "ignored.txt").write_text("changed\n", encoding="utf-8")
    _git(worktree, "add", ".")
    _git(worktree, "commit", "-m", "change automation")
    exact_head = _git(worktree, "rev-parse", "HEAD")

    assert manager.repository_automation_paths(coordination.change_id, exact_head) == (
        ".github/workflows/created.yaml",
        ".github/workflows/new.yml",
        ".github/workflows/old.yml",
        "action.yml",
        "nested/action.yaml",
    )


def test_list_retained_worktrees_returns_empty_without_coordination_store(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=1)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "release")
    assert coordinator.list_registered() == ()
    assert manager.list_retained() == ()


def test_cleanup_removes_exact_worktree_keeps_branch_and_replays_receipt(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("cleanup-change")

    receipt = manager.cleanup(coordination.change_id)

    assert receipt.change_id == coordination.change_id
    assert receipt.branch_head == initial
    assert receipt.worktree_path == coordination.worktree_path.resolve()
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(repository, coordination.branch)
    assert _git(repository, "rev-parse", coordination.branch) == initial
    assert coordinator.show(coordination.change_id).worktree_cleanup == receipt
    assert manager.cleanup(coordination.change_id) == receipt
    assert manager.list_retained() == ()


def test_cleanup_refuses_dirty_worktree_without_discarding_content(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("dirty-cleanup")
    dirty_file = coordination.worktree_path / "uncommitted.txt"
    dirty_file.write_text("preserve me\n", encoding="utf-8")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.WORKTREE_DIRTY in raised.value.attention
    assert dirty_file.read_text(encoding="utf-8") == "preserve me\n"
    assert coordination.worktree_path.exists()
    assert coordinator.show(coordination.change_id).worktree_cleanup is None


def test_restart_refuses_dirty_worktree_before_creating_attempt_ref(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("dirty-restart")
    writer = ChangeWriter(
        **_identity(coordination.change_id).model_dump(),
        job_id=1,
        kind="build",
    )
    coordinator.acquire(coordination.change_id, writer)
    dirty_file = coordination.worktree_path / "uncommitted.txt"
    dirty_file.write_text("preserve me\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="clean committed change worktree"):
        manager.restart(coordination.change_id, writer.attempt_id, initial)

    assert dirty_file.read_text(encoding="utf-8") == "preserve me\n"
    assert not _git_ref_exists(
        repository,
        f"refs/owlbear/attempts/{coordination.change_id}/{writer.attempt_id}",
    )
    assert coordinator.show(coordination.change_id).writer == writer


def test_quarantine_dirty_worktree_preserves_all_nonignored_bytes_and_environment(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    (repository / ".gitignore").write_text(".venv/\nnode_modules/\ndist/\n", encoding="utf-8")
    (repository / "deleted.txt").write_text("delete me\n", encoding="utf-8")
    (repository / "rename-source.txt").write_text("rename me\n", encoding="utf-8")
    _git(repository, "add", ".gitignore", "deleted.txt", "rename-source.txt")
    _git(repository, "commit", "-m", "seed quarantine boundaries")
    base_head = _git(repository, "rev-parse", "HEAD")
    _git(repository, "branch", "-f", "release", base_head)
    _git(repository, "update-ref", "refs/remotes/origin/release", base_head)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-change")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    worktree = coordination.worktree_path
    (worktree / "shared.txt").write_bytes(b"staged binary\x00\xff")
    _git(worktree, "add", "shared.txt")
    (worktree / "new.txt").write_bytes(b"untracked binary\x00\xfe")
    _git(worktree, "mv", "rename-source.txt", "rename-target.txt")
    (worktree / "deleted.txt").unlink()
    (worktree / "uv.lock").write_bytes(b"lock\x00\xff")
    for directory in (".venv", "node_modules", "dist"):
        path = worktree / directory
        path.mkdir()
        (path / "keep.bin").write_bytes(b"ignored environment")

    receipt = manager.quarantine_dirty_worktree(
        coordination.change_id,
        writer.attempt_id,
        writer.claim_id,
        "quarantine-operation",
    )

    assert receipt.base_head == _git(repository, "rev-parse", coordination.branch)
    assert receipt.quarantine_ref == f"refs/owlbear/quarantine/{coordination.change_id}/{writer.attempt_id}"
    assert receipt.paths == tuple(sorted(receipt.paths))
    assert set(receipt.paths) == {
        "deleted.txt",
        "new.txt",
        "rename-source.txt",
        "rename-target.txt",
        "shared.txt",
        "uv.lock",
    }
    assert _git(worktree, "status", "--porcelain") == ""
    assert _git(worktree, "rev-parse", "HEAD") == base_head
    assert (worktree / "shared.txt").read_bytes() == b"base\n"
    assert not (worktree / "new.txt").exists()
    assert (worktree / "rename-source.txt").read_text(encoding="utf-8") == "rename me\n"
    assert not (worktree / "rename-target.txt").exists()
    assert (worktree / "deleted.txt").exists()
    for directory in (".venv", "node_modules", "dist"):
        assert (worktree / directory / "keep.bin").read_bytes() == b"ignored environment"
    assert _git(repository, "rev-parse", receipt.quarantine_ref) == receipt.quarantine_commit
    assert (
        subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            ("git", "-C", str(repository), "show", f"{receipt.quarantine_commit}:shared.txt"),  # noqa: S607
            check=True,
            capture_output=True,
        ).stdout
        == b"staged binary\x00\xff"
    )
    assert (
        subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            ("git", "-C", str(repository), "show", f"{receipt.quarantine_commit}:uv.lock"),  # noqa: S607
            check=True,
            capture_output=True,
        ).stdout
        == b"lock\x00\xff"
    )


def test_quarantine_replays_after_receipt_persistence_failure(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-replay")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    dirty_file = coordination.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"preserve\x00\xff")

    with (
        patch.object(coordinator, "update", side_effect=CoordinationConflictError("injected receipt failure")),
        pytest.raises(CoordinationConflictError, match="injected receipt failure"),
    ):
        manager.quarantine_dirty_worktree(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-replay-operation",
        )

    quarantine_ref = f"refs/owlbear/quarantine/{coordination.change_id}/{writer.attempt_id}"
    assert _git_ref_exists(repository, quarantine_ref)
    assert coordinator.show(coordination.change_id).dirty_worktree_quarantine is None
    assert dirty_file.read_bytes() == b"preserve\x00\xff"

    receipt = manager.quarantine_dirty_worktree(
        coordination.change_id,
        writer.attempt_id,
        writer.claim_id,
        "quarantine-replay-operation",
    )

    assert receipt.quarantine_ref == quarantine_ref
    assert coordinator.show(coordination.change_id).dirty_worktree_quarantine == receipt
    assert dirty_file.exists() is False
    assert _git(coordination.worktree_path, "status", "--porcelain") == ""


def test_quarantine_replay_rejects_changed_bytes_after_preservation(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-drift")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    dirty_file = coordination.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"first\x00\xff")

    with (
        patch.object(coordinator, "update", side_effect=CoordinationConflictError("injected receipt failure")),
        pytest.raises(CoordinationConflictError, match="injected receipt failure"),
    ):
        manager.quarantine_dirty_worktree(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-drift-operation",
        )

    dirty_file.write_bytes(b"newer\x00\xfe")

    with pytest.raises(RuntimeError, match="changed after quarantine preservation"):
        manager.quarantine_dirty_worktree(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-drift-operation",
        )

    assert dirty_file.read_bytes() == b"newer\x00\xfe"
    assert coordinator.show(coordination.change_id).writer == writer
    assert coordinator.show(coordination.change_id).dirty_worktree_quarantine is None
    assert _git(coordination.worktree_path, "status", "--porcelain")


def test_quarantine_verifies_after_restart_moves_branch_to_reviewed_head(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("quarantine-restart-replay")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    dirty_file = coordination.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"preserve\x00\xff")

    receipt = manager.quarantine_dirty_worktree(
        coordination.change_id,
        writer.attempt_id,
        writer.claim_id,
        "quarantine-restart-replay-operation",
    )
    manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert _git(repository, "rev-parse", coordination.branch) == initial
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == initial
    assert (
        manager.verify_dirty_worktree_quarantine(
            coordination.change_id,
            writer.attempt_id,
            writer.claim_id,
            "quarantine-restart-replay-operation",
        )
        == receipt
    )


def test_cleanup_replays_persisted_intent_after_receipt_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("interrupted-cleanup")
    original_update = coordinator.update
    update_count = 0
    failure_message = "simulated cleanup receipt write failure"

    def fail_receipt_update(updated: ChangeCoordination) -> ChangeCoordination:
        nonlocal update_count
        update_count += 1
        if update_count == 2:
            raise CoordinationConflictError(failure_message)
        return original_update(updated)

    monkeypatch.setattr(coordinator, "update", fail_receipt_update)

    with pytest.raises(CoordinationConflictError, match=failure_message):
        manager.cleanup(coordination.change_id)

    interrupted = coordinator.show(coordination.change_id)
    assert interrupted.worktree_cleanup_intent is not None
    assert interrupted.worktree_cleanup is None
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(repository, coordination.branch)
    assert _git(repository, "rev-parse", coordination.branch) == initial
    with pytest.raises(CoordinationConflictError, match="change already has an active writer"):
        coordinator.acquire(
            coordination.change_id,
            ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build"),
        )

    monkeypatch.setattr(coordinator, "update", original_update)
    receipt = manager.cleanup(coordination.change_id)

    assert receipt.branch_head == initial
    assert coordinator.show(coordination.change_id).worktree_cleanup == receipt
    assert coordinator.show(coordination.change_id).worktree_cleanup_intent is None
    assert manager.cleanup(coordination.change_id) == receipt


def test_cleanup_refuses_missing_worktree_without_recording_cleanup(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("missing-cleanup")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in raised.value.attention
    assert ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING in raised.value.attention
    assert coordinator.show(coordination.change_id).worktree_cleanup is None


def test_cleanup_refuses_registration_for_another_branch_or_path(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    _, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("ambiguous-cleanup")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    alternate = tmp_path / "alternate-worktree"
    _git(repository, "worktree", "add", str(alternate), coordination.branch)

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in raised.value.attention
    assert ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS in raised.value.attention
    assert alternate.exists()


def test_cleanup_refuses_unexpected_worktree_filesystem_state(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("file-cleanup")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    coordination.worktree_path.write_text("not a worktree\n", encoding="utf-8")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.cleanup(coordination.change_id)

    assert ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE in raised.value.attention
    assert coordination.worktree_path.read_text(encoding="utf-8") == "not a worktree\n"


def test_list_registered_ignores_runtime_transaction_temp_files(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    manager.ensure("stable-change")
    coordination_root = tmp_path / "state/coordination/changes"
    (coordination_root / ".tmp-deadbeef-stable-change.json").write_text("not json", encoding="utf-8")

    assert [item.change_id for item in coordinator.list_registered()] == ["stable-change"]


def test_list_registered_rejects_malformed_or_misnamed_records(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    manager.ensure("valid-change")
    coordination_root = tmp_path / "state/coordination/changes"
    (coordination_root / "broken.json").write_text("{", encoding="utf-8")

    with pytest.raises(CoordinationConflictError, match="record is invalid"):
        coordinator.list_registered()

    (coordination_root / "broken.json").unlink()
    payload = _coordination(tmp_path, "valid-change").model_dump(mode="json")
    (coordination_root / "wrong-name.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CoordinationConflictError, match="identity is invalid"):
        coordinator.list_registered()


def test_ensure_replays_a_healthy_change_worktree(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    first = manager.ensure("healthy-replay")

    replayed = manager.ensure("healthy-replay", recovery_reviewed_head=first.last_reviewed_commit)

    assert replayed == first


def test_ensure_rejects_invalid_change_id_before_git_access(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    before = _workspace_bytes(repository, tmp_path / "state")
    with (
        patch.object(manager, "_git", wraps=manager._git) as git,  # noqa: SLF001
        pytest.raises(ValueError, match="safe worktree identity"),
    ):
        manager.ensure("../invalid")

    assert git.call_count == 0
    assert _workspace_bytes(repository, tmp_path / "state") == before


@pytest.mark.parametrize("missing_state", ["directory", "registration"])
def test_ensure_refuses_missing_worktree_state_without_writes(tmp_path: Path, missing_state: str) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"missing-{missing_state}")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    if missing_state == "registration":
        coordination.worktree_path.mkdir(parents=True)
        (coordination.worktree_path / "preserved.txt").write_text("preserve\n", encoding="utf-8")
    before = _workspace_bytes(repository, tmp_path / "state")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.ensure(coordination.change_id, recovery_reviewed_head=coordination.last_reviewed_commit)

    assert (
        ChangeWorktreeAttentionCode.WORKTREE_MISSING
        if missing_state == "directory"
        else ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING
    ) in raised.value.attention
    assert _workspace_bytes(repository, tmp_path / "state") == before
    if missing_state == "registration":
        assert (coordination.worktree_path / "preserved.txt").read_text(encoding="utf-8") == "preserve\n"


def test_recover_recreates_missing_worktree_from_exact_reviewed_head(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("recoverable-change")
    shutil.rmtree(coordination.worktree_path)

    recovered = manager.recover(coordination.change_id, coordination.last_reviewed_commit)

    assert recovered == coordination
    assert recovered.worktree_path.is_dir()
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == coordination.last_reviewed_commit
    assert _git(repository, "worktree", "list", "--porcelain").count(str(recovered.worktree_path)) == 1
    assert coordinator.show(coordination.change_id) == coordination


def test_recover_rejects_unregistered_worktree_without_discarding_content(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("preserved-recovery")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    coordination.worktree_path.mkdir(parents=True)
    preserved = coordination.worktree_path / "preserved.txt"
    preserved.write_text("preserve\n", encoding="utf-8")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.recover(coordination.change_id, coordination.last_reviewed_commit)

    assert ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING in raised.value.attention
    assert preserved.read_text(encoding="utf-8") == "preserve\n"


def test_recover_requires_the_registered_reviewed_head(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("exact-recovery")
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="recovery reviewed head differs"):
        manager.recover(coordination.change_id, "a" * 40)

    assert not coordination.worktree_path.exists()


def test_recover_rejects_branch_registered_at_a_foreign_path(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("foreign-recovery")
    _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    foreign_path = tmp_path / "foreign-worktree"
    _git(repository, "worktree", "add", str(foreign_path), coordination.branch)

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.recover(coordination.change_id, coordination.last_reviewed_commit)

    assert ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS in raised.value.attention
    assert foreign_path.is_dir()
    assert not coordination.worktree_path.exists()


def test_ensure_preserves_dirty_change_worktree(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("dirty-replay")
    dirty_file = coordination.worktree_path / "dirty.txt"
    dirty_file.write_text("uncommitted\n", encoding="utf-8")
    before = _workspace_bytes(repository, tmp_path / "state")

    replayed = manager.ensure(coordination.change_id)

    assert replayed == coordination
    assert dirty_file.read_text(encoding="utf-8") == "uncommitted\n"
    assert _workspace_bytes(repository, tmp_path / "state") == before


def test_ensure_refuses_coordination_path_mismatch_without_writes(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("path-mismatch")
    mismatched = coordination.model_copy(update={"worktree_path": tmp_path / "elsewhere" / "path-mismatch"})
    coordinator.update(mismatched)
    before = _workspace_bytes(repository, tmp_path / "state")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        manager.ensure(coordination.change_id)

    assert ChangeWorktreeAttentionCode.COORDINATION_PATH_MISMATCH in raised.value.attention
    assert _workspace_bytes(repository, tmp_path / "state") == before


@pytest.mark.parametrize(
    ("mutation", "expected_attention"),
    [
        ("missing-directory", ChangeWorktreeAttentionCode.WORKTREE_MISSING),
        ("missing-registration", ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING),
        ("missing-branch", ChangeWorktreeAttentionCode.BRANCH_MISSING),
        ("detached", ChangeWorktreeAttentionCode.DETACHED),
        ("branch-mismatch", ChangeWorktreeAttentionCode.BRANCH_MISMATCH),
    ],
)
def test_list_retained_worktrees_reports_independent_degraded_facts(
    tmp_path: Path,
    mutation: str,
    expected_attention: ChangeWorktreeAttentionCode,
) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"degraded-{mutation}")
    if mutation == "missing-directory":
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
    elif mutation == "missing-registration":
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
        coordination.worktree_path.mkdir(parents=True)
    elif mutation == "missing-branch":
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))
        if _git_ref_exists(repository, coordination.branch):
            _git(repository, "update-ref", "-d", f"refs/heads/{coordination.branch}")
    elif mutation == "detached":
        _git(coordination.worktree_path, "checkout", "--detach", "HEAD")
    elif mutation == "branch-mismatch":
        _git(coordination.worktree_path, "checkout", "-b", f"other-{mutation}")

    retained = manager.list_retained()
    row = next(item for item in retained if item.change_id == coordination.change_id)

    assert expected_attention in row.attention
    assert row.coordination_registered
    assert row.worktree_present is (mutation not in {"missing-directory", "missing-branch"})
    assert row.git_registered is (mutation not in {"missing-directory", "missing-registration", "missing-branch"})


def test_list_retained_worktrees_reports_orphaned_registration(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("orphaned-change")
    (tmp_path / "state/coordination/changes/orphaned-change.json").unlink()

    row = next(item for item in manager.list_retained() if item.change_id == coordination.change_id)

    assert row.coordination_registered is False
    assert row.git_registered is True
    assert row.worktree_present is True
    assert ChangeWorktreeAttentionCode.COORDINATION_MISSING in row.attention


def _commit_file(worktree: Path, content: str, message: str) -> str:
    (worktree / "shared.txt").write_text(content, encoding="utf-8")
    _git(worktree, "add", "shared.txt")
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def _commit_new_file(worktree: Path, name: str, content: str, message: str) -> str:
    (worktree / name).write_text(content, encoding="utf-8")
    _git(worktree, "add", name)
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def _publish_external_change_head(
    tmp_path: Path,
    repository: Path,
    branch: str,
    base_head: str,
    *,
    filename: str = "external.txt",
) -> tuple[Path, str]:
    remote = tmp_path / "external-remote.git"
    _git(tmp_path, "init", "--bare", "-b", branch, str(remote))
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", f"{base_head}:refs/heads/{branch}")
    external = tmp_path / "external-repository"
    _git(tmp_path, "clone", str(remote), str(external))
    _git(external, "checkout", "-b", "external", base_head)
    _git(external, "config", "user.name", "External User")
    _git(external, "config", "user.email", "external@example.com")
    adopted = _commit_new_file(external, filename, "external\n", "external Change update")
    _git(external, "push", "origin", f"{adopted}:refs/heads/{branch}")
    return remote, adopted


def test_adopt_external_head_fast_forwards_managed_worktree_and_preserves_review_authority(
    tmp_path: Path,
) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("adoptable-change")
    remote, adopted = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
    )

    receipt = manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-external-change",
        )
    )

    assert isinstance(receipt, ChangeExternalHeadAdoptionReceipt)
    assert receipt.expected_head == initial
    assert receipt.adopted_head == adopted
    assert _git(repository, "rev-parse", coordination.branch) == adopted
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == adopted
    assert coordinator.show(coordination.change_id).last_reviewed_commit == initial
    with pytest.raises(RuntimeError, match="reviewed source boundary"):
        manager.reviewed_source_head(coordination.change_id)
    assert manager.source_head(coordination.change_id) == adopted
    promoted = manager.promote_external_head(
        PromoteExternalHead(
            change_id=coordination.change_id,
            expected_head=adopted,
            operation_id="promote-external-change",
        )
    )
    assert isinstance(promoted, ChangeExternalHeadPromotionReceipt)
    assert promoted.promoted_head == adopted
    assert coordinator.show(coordination.change_id).last_reviewed_commit == adopted
    assert manager.reviewed_source_head(coordination.change_id) == adopted
    assert (
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head=adopted,
                operation_id="adopt-external-change",
            )
        )
        == receipt
    )
    assert _git(remote, "rev-parse", f"refs/heads/{coordination.branch}") == adopted


def test_adopt_external_head_rejects_divergent_remote_without_branch_mutation(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("divergent-adoption")
    local_descendant = _commit_new_file(coordination.worktree_path, "local.txt", "local\n", "local change")
    manager.record_reviewed(coordination.change_id, local_descendant)
    _git(coordination.worktree_path, "checkout", coordination.branch)
    divergent_base = _git(repository, "rev-parse", "release")
    assert divergent_base == initial
    _remote, divergent = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
        filename="divergent.txt",
    )
    before = coordinator.show(coordination.change_id)

    with pytest.raises(RuntimeError, match="not a descendant"):
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=local_descendant,
                adopted_head=divergent,
                operation_id="reject-divergent-adoption",
            )
        )

    assert _git(repository, "rev-parse", coordination.branch) == local_descendant
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == local_descendant
    after = coordinator.show(coordination.change_id)
    assert after == before


def test_adopt_external_head_replays_after_crash_between_fast_forward_and_receipt(
    tmp_path: Path,
) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("crash-replay-adoption")
    _remote, adopted = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
    )
    request = AdoptExternalHead(
        change_id=coordination.change_id,
        expected_head=initial,
        adopted_head=adopted,
        operation_id="crash-replay-adoption",
    )

    with (
        patch.object(manager, "_complete_external_head_adoption", side_effect=RuntimeError("simulated crash")),
        pytest.raises(RuntimeError, match="simulated crash"),
    ):
        manager.adopt_external_head(request)

    interrupted = coordinator.show(coordination.change_id)
    assert interrupted.external_head_adoption_intent is not None
    assert interrupted.external_head_adoption_receipt is None
    assert _git(repository, "rev-parse", coordination.branch) == adopted
    assert manager.adopt_external_head(request).adopted_head == adopted
    assert coordinator.show(coordination.change_id).external_head_adoption_intent is None


def test_target_sync_rejects_an_unreviewed_adopted_head(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("adopted-target-sync")
    _remote, adopted = _publish_external_change_head(
        tmp_path,
        repository,
        coordination.branch,
        initial,
    )
    manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-before-target-sync",
        )
    )
    before = coordinator.show(coordination.change_id)

    with pytest.raises(CoordinationConflictError, match="reviewed Change head"):
        manager.sync_with_target(
            SyncChangeWithTarget(
                change_id=coordination.change_id,
                expected_target="a" * 40,
                operation_id="target-sync-after-adoption",
            )
        )

    assert coordinator.show(coordination.change_id) == before
    assert _git(repository, "rev-parse", coordination.branch) == adopted


def test_adopt_external_head_rejects_active_writer_and_dirty_worktree(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("blocked-adoption")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)

    with pytest.raises(CoordinationConflictError, match="active writer"):
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head="b" * 40,
                operation_id="blocked-by-writer",
            )
        )

    coordinator.release(coordination.change_id, writer.claim_id)
    (coordination.worktree_path / "dirty.txt").write_text("preserve\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not clean"):
        manager.adopt_external_head(
            AdoptExternalHead(
                change_id=coordination.change_id,
                expected_head=initial,
                adopted_head="b" * 40,
                operation_id="blocked-by-dirty-worktree",
            )
        )
    assert _git(repository, "rev-parse", coordination.branch) == initial
    assert coordinator.show(coordination.change_id).external_head_adoption_receipt is None


def test_restart_rejects_reset_across_unpromoted_external_head(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("restart-adopted-change")
    _remote, adopted = _publish_external_change_head(tmp_path, repository, coordination.branch, initial)
    manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-before-restart",
        )
    )
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)

    with pytest.raises(CoordinationConflictError, match="unpromoted external Change head"):
        manager.restart(coordination.change_id, writer.attempt_id, adopted)

    assert _git(repository, "rev-parse", coordination.branch) == adopted
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == adopted
    assert coordinator.show(coordination.change_id).writer == writer


def test_restart_accepts_promoted_adoption_after_reviewed_descendant_and_replays(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("restart-promoted-adoption")
    _remote, adopted = _publish_external_change_head(tmp_path, repository, coordination.branch, initial)
    manager.adopt_external_head(
        AdoptExternalHead(
            change_id=coordination.change_id,
            expected_head=initial,
            adopted_head=adopted,
            operation_id="adopt-before-promoted-restart",
        )
    )
    promoted = manager.promote_external_head(
        PromoteExternalHead(
            change_id=coordination.change_id,
            expected_head=adopted,
            operation_id="promote-before-restart",
        )
    )
    reviewed = _commit_new_file(coordination.worktree_path, "reviewed.txt", "reviewed\n", "reviewed descendant")
    manager.record_reviewed(coordination.change_id, reviewed)
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    attempt_ref = f"refs/owlbear/attempts/{coordination.change_id}/{writer.attempt_id}"

    restarted = manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert promoted is not None
    assert _git(repository, "rev-parse", attempt_ref) == rejected
    assert _git(repository, "rev-parse", coordination.branch) == reviewed
    assert _git(restarted.worktree_path, "rev-parse", "HEAD") == reviewed
    assert restarted.last_reviewed_commit == reviewed
    assert restarted.writer is None
    assert CapacityLedger.model_validate_json((tmp_path / "state/capacity-ledger.json").read_bytes()).change_ids == ()

    replayed = manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert replayed == restarted


def test_record_reviewed_rejects_backward_boundary(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("monotonic-review")
    reviewed = _commit_new_file(coordination.worktree_path, "reviewed.txt", "reviewed\n", "reviewed")
    manager.record_reviewed(coordination.change_id, reviewed)

    with pytest.raises(RuntimeError, match="not an ancestor"):
        manager.record_reviewed(coordination.change_id, initial)

    assert coordinator.show(coordination.change_id).last_reviewed_commit == reviewed


def test_finalization_rejects_divergent_promoted_task_history(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("divergent-tasks")
    first = _commit_new_file(coordination.worktree_path, "first.txt", "first\n", "first task")
    _git(coordination.worktree_path, "checkout", "-b", "divergent-task", initial)
    second = _commit_new_file(coordination.worktree_path, "second.txt", "second\n", "second task")
    _git(coordination.worktree_path, "checkout", coordination.branch)
    _git(coordination.worktree_path, "merge", "--no-ff", "divergent-task", "-m", "merge divergent tasks")
    exact_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    manager.record_reviewed(coordination.change_id, exact_head)

    with pytest.raises(RuntimeError, match="not an ancestor"):
        manager.validate_finalization_head(coordination.change_id, exact_head, (first, second))


def test_workspace_recovery_requires_and_preserves_exact_reviewed_head(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root, capacity=2)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "release")
    coordination = manager.ensure("recovered-change")
    reviewed = _commit_new_file(coordination.worktree_path, "product.txt", "reviewed\n", "reviewed product")
    manager.record_reviewed(coordination.change_id, reviewed)
    (state_root / "coordination/changes/recovered-change.json").unlink()
    recovered_manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "release")

    with pytest.raises(CoordinationConflictError, match="exact recovery reviewed head"):
        recovered_manager.ensure("recovered-change")

    recovered = recovered_manager.ensure("recovered-change", recovery_reviewed_head=reviewed)

    assert recovered.last_reviewed_commit == reviewed
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == reviewed


def test_coordinator_recovers_pending_runtime_transaction(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    participant = TransactionParticipant(state_root, Path("target-runtime/recovered.json"), b"{}\n")

    def interrupt(stage: str) -> None:
        if stage == "before-publication":
            message = "injected"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="injected"):
        RuntimeTransaction(state_root, "pending-portfolio", (participant,)).commit(failure=interrupt)

    PortfolioCoordinator(state_root, capacity=1)

    assert (state_root / "target-runtime/recovered.json").read_bytes() == b"{}\n"
    assert not (state_root / "transactions/pending-portfolio.yaml").exists()


def test_coordinator_reconfigures_capacity_when_active_holders_fit(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    legacy_ledger_path = state_root / "capacity.json"
    ledger_path = state_root / "capacity-ledger.json"
    ledger_path.parent.mkdir(parents=True)
    legacy_ledger_path.write_text(
        CapacityLedger(capacity=4, change_ids=("change-a",)).model_dump_json(),
        encoding="utf-8",
    )

    PortfolioCoordinator(state_root, capacity=1)

    assert CapacityLedger.model_validate_json(ledger_path.read_bytes()) == CapacityLedger(
        capacity=1,
        change_ids=("change-a",),
    )
    assert not legacy_ledger_path.exists()


@pytest.mark.parametrize("transaction_id", ["initialize-capacity", "reconfigure-capacity"])
def test_coordinator_translates_capacity_ledger_conflict(
    tmp_path: Path,
    transaction_id: str,
) -> None:
    state_root = tmp_path / "state"
    ledger_path = state_root / "capacity-ledger.json"
    if transaction_id == "reconfigure-capacity":
        state_root.mkdir(parents=True)
        ledger_path.write_text(CapacityLedger(capacity=2).model_dump_json(), encoding="utf-8")

    original_commit = PortfolioCoordinator._commit  # noqa: SLF001

    def race(
        coordinator: PortfolioCoordinator,
        candidate_transaction_id: str,
        participants: tuple[object, ...],
    ) -> None:
        if candidate_transaction_id == transaction_id:
            ledger_path.write_text(CapacityLedger(capacity=3).model_dump_json(), encoding="utf-8")
        original_commit(coordinator, candidate_transaction_id, participants)  # type: ignore[arg-type]

    with (
        patch.object(PortfolioCoordinator, "_commit", new=race),
        pytest.raises(CapacityLedgerConflictError) as exc_info,
    ):
        PortfolioCoordinator(state_root, capacity=1)

    assert isinstance(exc_info.value, CoordinationConflictError)
    assert not isinstance(exc_info.value, CapacityConfigurationConflictError)
    assert str(exc_info.value) == "host capacity ledger changed concurrently"


def test_coordinator_rejects_capacity_below_active_holders(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    ledger_path = state_root / "capacity-ledger.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        CapacityLedger(capacity=4, change_ids=("change-a", "change-b")).model_dump_json(),
        encoding="utf-8",
    )

    with pytest.raises(CoordinationConflictError, match="active writers exceed configured writer capacity"):
        PortfolioCoordinator(state_root, capacity=1)

    assert CapacityLedger.model_validate_json(ledger_path.read_bytes()).capacity == 4


def test_restart_preserves_rejected_head_and_returns_to_reviewed_commit(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("restart-change")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    coordinator.acquire(
        "restart-change",
        ChangeWriter(**_identity("restart-change").model_dump(), job_id=1, kind="build"),
    )

    restarted = manager.restart("restart-change", "attempt-restart-change", rejected)

    assert _git(repository, "rev-parse", "refs/owlbear/attempts/restart-change/attempt-restart-change") == rejected
    assert _git(repository, "rev-parse", restarted.branch) == initial
    assert _git(restarted.worktree_path, "rev-parse", "HEAD") == initial
    assert restarted.writer is None


def test_restart_recovers_after_git_succeeds_before_writer_release(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure("recover-restart")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    coordinator.acquire(
        "recover-restart",
        ChangeWriter(**_identity("recover-restart").model_dump(), job_id=1, kind="build"),
    )
    original_release = coordinator.release

    with (
        patch.object(coordinator, "release", side_effect=CoordinationConflictError("injected")),
        pytest.raises(CoordinationConflictError, match="injected"),
    ):
        manager.restart("recover-restart", "attempt-recover-restart", rejected)

    recovered = manager.restart("recover-restart", "attempt-recover-restart", rejected)

    assert _git(repository, "rev-parse", "refs/owlbear/attempts/recover-restart/attempt-recover-restart") == rejected
    assert _git(repository, "rev-parse", recovered.branch) == initial
    assert recovered.writer is None
    assert original_release("recover-restart", "claim-recover-restart") == recovered


@pytest.mark.parametrize("interruption", ["attempt-ref", "worktree-reset"])
def test_restart_recovers_from_each_git_interruption(tmp_path: Path, interruption: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"restart-{interruption}")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    coordinator.acquire(
        coordination.change_id,
        ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build"),
    )
    original_git = manager._git  # noqa: SLF001

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        if _restart_stage(arguments, coordination, interruption):
            message = "injected"
            raise RuntimeError(message)
        return result

    with (
        patch.object(manager, "_git", side_effect=interrupt_after_git),
        pytest.raises(RuntimeError, match="injected"),
    ):
        manager.restart(coordination.change_id, _identity(coordination.change_id).attempt_id, rejected)

    recovered = manager.restart(coordination.change_id, _identity(coordination.change_id).attempt_id, rejected)

    assert _git(repository, "rev-parse", recovered.branch) == initial
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == initial
    assert recovered.last_reviewed_commit == initial
    assert recovered.writer is None


def _restart_stage(
    arguments: tuple[str, ...],
    coordination: ChangeCoordination,
    interruption: str,
) -> bool:
    checks = {
        "attempt-ref": arguments[:2]
        == ("update-ref", f"refs/owlbear/attempts/{coordination.change_id}/attempt-{coordination.change_id}"),
        "worktree-reset": arguments[:2] == ("reset", "--hard"),
    }
    return checks[interruption]


@pytest.mark.parametrize("interruption", ["branch-reset", "worktree-add"])
def test_restart_recovers_missing_worktree_at_each_git_interruption(tmp_path: Path, interruption: str) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.ensure(f"restart-missing-{interruption}")
    rejected = _commit_file(coordination.worktree_path, "rejected\n", "rejected attempt")
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="build")
    coordinator.acquire(coordination.change_id, writer)
    _git(repository, "worktree", "remove", str(coordination.worktree_path))
    original_git = manager._git  # noqa: SLF001

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        checks = {
            "branch-reset": arguments[:2] == ("update-ref", f"refs/heads/{coordination.branch}"),
            "worktree-add": arguments[:2] == ("worktree", "add"),
        }
        if checks[interruption]:
            message = "injected"
            raise RuntimeError(message)
        return result

    with (
        patch.object(manager, "_git", side_effect=interrupt_after_git),
        pytest.raises(RuntimeError, match="injected"),
    ):
        manager.restart(coordination.change_id, writer.attempt_id, rejected)

    recovered = manager.restart(coordination.change_id, writer.attempt_id, rejected)

    assert _git(repository, "rev-parse", recovered.branch) == initial
    assert _git(recovered.worktree_path, "rev-parse", "HEAD") == initial
    assert recovered.writer is None
