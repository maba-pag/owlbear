from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_delivery.change_workspace import (
    CapacityLedger,
    ChangeWorkspaceManager,
    ChangeCoordination,
    ChangeWorktreeAttentionError,
    ChangeWorktreeAttentionCode,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    PublicationLease,
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

    coordination = ChangeCoordination.model_validate_json(json.dumps(payload))

    assert coordination.publication_lease is None


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
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_ref_exists(repository: Path, reference: str) -> bool:
    return (
        subprocess.run(
            ("git", "-C", str(repository), "rev-parse", "--verify", reference),
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


def test_list_retained_worktrees_is_sorted_and_batches_git_reads(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    first = manager.ensure("change-b")
    second = manager.ensure("change-a")
    _git(repository, "update-ref", "refs/heads/owlbear/change/nested-only/s1", initial)
    before_coordination = tuple(
        sorted((path.name, path.read_bytes()) for path in (tmp_path / "state/claims/changes").iterdir())
    )
    before_worktrees = _git(repository, "worktree", "list", "--porcelain")
    original_run_git = manager._run_git

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
        sorted((path.name, path.read_bytes()) for path in (tmp_path / "state/claims/changes").iterdir())
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
    assert _git(repository, "rev-parse", coordination.branch) == initial


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
    coordination_root = tmp_path / "state/claims/changes"
    (coordination_root / ".tmp-deadbeef-stable-change.json").write_text("not json", encoding="utf-8")

    assert [item.change_id for item in coordinator.list_registered()] == ["stable-change"]


def test_list_registered_rejects_malformed_or_misnamed_records(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    manager.ensure("valid-change")
    coordination_root = tmp_path / "state/claims/changes"
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
        patch.object(manager, "_git", wraps=manager._git) as git,
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
    (tmp_path / "state/claims/changes/orphaned-change.json").unlink()

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
    (state_root / "claims/changes/recovered-change.json").unlink()
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
    assert not (state_root / ".runtime-transactions/pending-portfolio.yaml").exists()


def test_coordinator_reconfigures_capacity_when_active_holders_fit(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    ledger_path = state_root / "capacity.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        CapacityLedger(capacity=4, change_ids=("change-a",)).model_dump_json(),
        encoding="utf-8",
    )

    PortfolioCoordinator(state_root, capacity=1)

    assert CapacityLedger.model_validate_json(ledger_path.read_bytes()) == CapacityLedger(
        capacity=1,
        change_ids=("change-a",),
    )


def test_coordinator_rejects_capacity_below_active_holders(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    ledger_path = state_root / "capacity.json"
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
    original_git = manager._git

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
    original_git = manager._git

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
