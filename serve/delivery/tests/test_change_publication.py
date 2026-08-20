"""Publication and target-sync proofs for user checkout state and Delivery surfaces.

The matrix covers clean, modified, staged, untracked, conflicted, detached,
mid-merge, and mid-rebase user checkouts through managed target synchronization,
publication, and cleanup. Provider failures and pre-write timeouts are retried
through the same states. Extended Git operation markers are exercised through
publication and cleanup. Conflicts in the managed Change worktree remain a
separate state from conflicts in the user checkout. A post-write timeout is a
response-unknown outcome rather than a retry-safe incident.
"""

# ruff: noqa: SLF001

from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any
from unittest.mock import patch

import pytest

from owlbear_delivery import (
    ChangeBranchPublisher,
    ChangeBranchSupersessionReceipt,
    ChangeTargetSyncConflictError,
    ChangeWorkspaceManager,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    PublicationLease,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublishChangeBranch,
    SupersedeChangeBranch,
    SyncChangeWithTarget,
    TargetSyncConflictRequest,
    WriterIdentity,
)
from owlbear_delivery.git_executable import resolve_git_executable


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        (resolve_git_executable(), "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )


def _head(repository: Path, revision: str = "HEAD") -> str:
    return _git(repository, "rev-parse", "--verify", f"{revision}^{{commit}}").stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Test User")
    _git(repository, "config", "user.email", "test@example.com")
    (repository / "product.txt").write_text("base\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "initial")
    initial = _head(repository)
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    _git(repository, "fetch", "origin", "refs/heads/main:refs/remotes/origin/main")
    return repository, remote, initial


def _change_workspace(tmp_path: Path, repository: Path) -> tuple[PortfolioCoordinator, ChangeWorkspaceManager]:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    manager = ChangeWorkspaceManager(
        repository,
        tmp_path / "worktrees",
        coordinator,
        "refs/remotes/origin/main",
    )
    return coordinator, manager


def _reviewed_change(manager: ChangeWorkspaceManager, change_id: str) -> tuple[Path, str]:
    coordination = manager.ensure(change_id)
    (coordination.worktree_path / "product.txt").write_text("reviewed\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "reviewed change")
    reviewed = _head(coordination.worktree_path)
    manager.record_reviewed(change_id, reviewed)
    return coordination.worktree_path, reviewed


def _advance_remote_target(tmp_path: Path, remote: Path, *, product: str | None = None) -> str:
    target_repository = tmp_path / "target-repository"
    _git(tmp_path, "clone", str(remote), str(target_repository))
    _git(target_repository, "config", "user.name", "Target User")
    _git(target_repository, "config", "user.email", "target@example.com")
    if product is not None:
        (target_repository / "product.txt").write_text(product, encoding="utf-8")
    else:
        (target_repository / "target.txt").write_text("target\n", encoding="utf-8")
    _git(target_repository, "add", ".")
    _git(target_repository, "commit", "-m", "advance target")
    _git(target_repository, "push", "origin", "HEAD:refs/heads/main")
    return _head(target_repository)


def test_bare_repository_operations_are_isolated_from_host_git_configuration(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))

    hardened_config = tmp_path / "hardened.gitconfig"
    hardened_config.write_text("[safe]\n\tbareRepository = explicit\n", encoding="utf-8")

    hardened = subprocess.run(  # noqa: S603
        (resolve_git_executable(), "-C", str(remote), "rev-parse", "--git-dir"),
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": str(hardened_config)},
    )
    assert hardened.returncode == 128, hardened.stderr

    result = _git(remote, "rev-parse", "--git-dir", check=False)

    assert result.returncode == 0, result.stderr


_USER_CHECKOUT_STATES = (
    "clean",
    "modified",
    "staged",
    "untracked",
    "conflicted",
    "detached",
    "mid-merge",
    "mid-rebase",
)

_EXTENDED_USER_CHECKOUT_STATES = (
    "mid-cherry-pick",
    "mid-revert",
    "mid-bisect",
    "mid-rebase-apply",
)

_OPERATION_STATE_MARKERS = {
    "mid-merge": "MERGE_HEAD",
    "mid-rebase": "rebase-merge",
    "mid-rebase-apply": "rebase-apply",
    "mid-cherry-pick": "CHERRY_PICK_HEAD",
    "mid-revert": "REVERT_HEAD",
    "mid-bisect": "BISECT_LOG",
}


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_publication_and_cleanup_preserve_user_checkout_states(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    repository, remote, initial = _repository(tmp_path)
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    change_id = f"preserve-{user_state}"
    allowed_refs = (
        f"refs/heads/owlbear/change/{change_id}",
        f"refs/remotes/origin/owlbear/change/{change_id}",
    )

    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, change_id)
    before = user_checkout_snapshot(repository, allowed_refs)
    if user_state in _OPERATION_STATE_MARKERS:
        assert dict(before.operation_state)[_OPERATION_STATE_MARKERS[user_state]]
    if user_state == "conflicted":
        assert not dict(before.operation_state)["MERGE_HEAD"]

    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    receipt = publisher.publish(
        PublishChangeBranch(change_id=change_id, expected_remote_head=None, operation_id=f"{change_id}-publish")
    )
    replayed = publisher.publish(
        PublishChangeBranch(change_id=change_id, expected_remote_head=None, operation_id=f"{change_id}-publish")
    )
    cleanup = manager.cleanup(change_id)
    cleanup_replayed = manager.cleanup(change_id)

    assert receipt.published_head == reviewed
    assert replayed == receipt
    assert cleanup.branch_head == reviewed
    assert cleanup_replayed == cleanup
    assert _head(remote, f"refs/heads/owlbear/change/{change_id}") == reviewed
    assert _head(repository, "refs/remotes/origin/main") == initial
    before.assert_unchanged(repository)


@pytest.mark.parametrize("user_state", _EXTENDED_USER_CHECKOUT_STATES)
def test_publication_and_cleanup_preserve_extended_operation_markers(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    repository, remote, initial = _repository(tmp_path)
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    change_id = f"preserve-{user_state}"
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, change_id)
    before = user_checkout_snapshot(
        repository,
        (
            f"refs/heads/owlbear/change/{change_id}",
            f"refs/remotes/origin/owlbear/change/{change_id}",
        ),
    )
    assert dict(before.operation_state)[_OPERATION_STATE_MARKERS[user_state]]
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = PublishChangeBranch(
        change_id=change_id,
        expected_remote_head=None,
        operation_id=f"{change_id}-publish",
    )

    receipt = publisher.publish(request)
    assert publisher.publish(request) == receipt
    cleanup = manager.cleanup(change_id)

    assert receipt.published_head == reviewed
    assert cleanup.branch_head == reviewed
    assert _head(remote, f"refs/heads/owlbear/change/{change_id}") == reviewed
    assert _head(repository, "refs/remotes/origin/main") == initial
    before.assert_unchanged(repository)


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_syncs_exact_fetched_target_in_managed_worktree_and_replays_without_ref_pollution(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    local_target_head = _head(repository, "refs/heads/main")
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-change")
    target_head = _advance_remote_target(tmp_path, remote)
    request = SyncChangeWithTarget(
        change_id="sync-change",
        expected_target=target_head,
        operation_id="sync-change-1",
    )
    before = user_checkout_snapshot(
        repository,
        (
            "refs/heads/owlbear/change/sync-change",
            "refs/remotes/origin/owlbear/change/sync-change",
            "refs/remotes/origin/main",
        ),
    )

    with patch.object(manager, "_run_git", wraps=manager._run_git) as run_git:
        receipt = manager.sync_with_target(request)

    fetch_calls = [call for call in run_git.call_args_list if call.args and call.args[0] == "fetch"]
    assert len(fetch_calls) == 1
    assert fetch_calls[0].args[-1] == "refs/heads/main:refs/remotes/origin/main"

    assert receipt.change_id == "sync-change"
    assert receipt.expected_target == target_head
    assert receipt.target_head == target_head
    assert receipt.change_head_before != receipt.merged_head
    assert receipt.merge_commit
    assert _head(worktree) == receipt.merged_head
    assert _head(repository, "refs/remotes/origin/main") == target_head
    assert _head(repository, "refs/heads/main") == local_target_head
    before.assert_unchanged(repository)
    assert _coordinator.show("sync-change").last_reviewed_commit == receipt.merged_head
    assert _coordinator.show("sync-change").publication_base_head == _initial
    assert manager.reviewed_source_head("sync-change") == receipt.merged_head
    manager.validate_finalization_head("sync-change", receipt.merged_head, ())

    with patch.object(manager, "_run_git", wraps=manager._run_git) as run_git:
        assert manager.sync_with_target(request) == receipt

    assert not any(call.args and call.args[0] in {"fetch", "merge"} for call in run_git.call_args_list)


def test_fast_forward_target_sync_advances_the_reviewed_boundary(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    coordination = manager.ensure("sync-fast-forward")
    target_head = _advance_remote_target(tmp_path, remote)
    request = SyncChangeWithTarget(
        change_id="sync-fast-forward",
        expected_target=target_head,
        operation_id="sync-fast-forward-1",
    )

    receipt = manager.sync_with_target(request)

    assert receipt.change_head_before == initial
    assert receipt.target_head == target_head
    assert receipt.merged_head == target_head
    assert not receipt.merge_commit
    assert coordinator.show("sync-fast-forward").last_reviewed_commit == target_head
    assert coordinator.show("sync-fast-forward").publication_base_head == initial
    assert manager.reviewed_source_head("sync-fast-forward") == target_head
    assert _head(coordination.worktree_path) == target_head


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_sync_conflict_preserves_merge_state_and_user_checkout(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    repository, remote, initial = _repository(tmp_path)
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    local_target_head = _head(repository, "refs/heads/main")
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-conflict")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    request = SyncChangeWithTarget(
        change_id="sync-conflict",
        expected_target=target_head,
        operation_id="sync-conflict-1",
    )
    before = user_checkout_snapshot(
        repository,
        (
            "refs/heads/owlbear/change/sync-conflict",
            "refs/remotes/origin/owlbear/change/sync-conflict",
            "refs/remotes/origin/main",
        ),
    )

    with pytest.raises(ChangeTargetSyncConflictError) as raised:
        manager.sync_with_target(request)

    assert raised.value.conflict_paths == ("product.txt",)
    merge_head = Path(_git(worktree, "rev-parse", "--git-path", "MERGE_HEAD").stdout.strip())
    assert merge_head.exists()
    assert b"<<<<<<<" in (worktree / "product.txt").read_bytes()
    assert _head(repository, "refs/heads/main") == local_target_head
    assert _head(repository, "refs/remotes/origin/main") == target_head
    assert coordinator.show("sync-conflict").target_head == initial
    assert coordinator.show("sync-conflict").publication_base_head == initial
    assert coordinator.show("sync-conflict").last_reviewed_commit == reviewed
    assert coordinator.show("sync-conflict").target_sync_receipt is None
    before.assert_unchanged(repository)


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_abort_target_sync_conflict_replays_and_restores_reviewed_boundary(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    local_target_head = _head(repository, "refs/heads/main")
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-abort")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    request = SyncChangeWithTarget(
        change_id="sync-abort",
        expected_target=target_head,
        operation_id="sync-abort-1",
    )
    before = user_checkout_snapshot(
        repository,
        (
            "refs/heads/owlbear/change/sync-abort",
            "refs/remotes/origin/owlbear/change/sync-abort",
            "refs/remotes/origin/main",
        ),
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(request)

    exit_request = TargetSyncConflictRequest(
        change_id="sync-abort",
        target_head=target_head,
        operation_id="sync-abort-1",
    )
    receipt = manager.abort_target_sync_conflict(exit_request)
    replayed = manager.abort_target_sync_conflict(exit_request)

    assert replayed == receipt
    assert receipt.restored_head == reviewed
    assert _head(worktree) == reviewed
    assert _git(worktree, "status", "--porcelain").stdout == ""
    assert _git(worktree, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 128
    assert _head(repository, "refs/heads/main") == local_target_head
    assert _head(repository, "refs/remotes/origin/main") == target_head
    before.assert_unchanged(repository)
    assert coordinator.show("sync-abort").target_sync_conflict is None
    assert coordinator.show("sync-abort").target_sync_abort_receipt == receipt
    assert coordinator.show("sync-abort").publication_base_head == _initial


def test_abort_target_sync_conflict_replays_after_abort_before_receipt_persistence(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-abort-crash")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    request = SyncChangeWithTarget(
        change_id="sync-abort-crash",
        expected_target=target_head,
        operation_id="sync-abort-crash-1",
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(request)
    exit_request = TargetSyncConflictRequest(
        change_id="sync-abort-crash",
        target_head=target_head,
        operation_id="sync-abort-crash-1",
    )
    original_update = coordinator.update
    with (
        patch.object(coordinator, "update", side_effect=RuntimeError("simulated crash")),
        pytest.raises(RuntimeError, match="simulated crash"),
    ):
        manager.abort_target_sync_conflict(exit_request)

    assert _head(worktree) == reviewed
    assert _git(worktree, "status", "--porcelain").stdout == ""
    assert coordinator.show("sync-abort-crash").target_sync_conflict is not None
    with patch.object(coordinator, "update", original_update):
        receipt = manager.abort_target_sync_conflict(exit_request)

    assert receipt.restored_head == reviewed
    assert coordinator.show("sync-abort-crash").target_sync_conflict is None


def test_resolve_target_sync_conflict_replays_after_commit_before_receipt_persistence(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-resolve-crash")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    request = SyncChangeWithTarget(
        change_id="sync-resolve-crash",
        expected_target=target_head,
        operation_id="sync-resolve-crash-1",
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(request)
    (worktree / "product.txt").write_text("resolved\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    exit_request = TargetSyncConflictRequest(
        change_id="sync-resolve-crash",
        target_head=target_head,
        operation_id="sync-resolve-crash-1",
    )
    original_update = coordinator.update
    with (
        patch.object(coordinator, "update", side_effect=RuntimeError("simulated crash")),
        pytest.raises(RuntimeError, match="simulated crash"),
    ):
        manager.resolve_target_sync_conflict(exit_request)

    assert _head(worktree) != reviewed
    assert _git(worktree, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 128
    assert coordinator.show("sync-resolve-crash").target_sync_conflict is not None
    with patch.object(coordinator, "update", original_update):
        receipt = manager.resolve_target_sync_conflict(exit_request)

    assert receipt.change_head_before == reviewed
    assert receipt.target_head == target_head
    assert coordinator.show("sync-resolve-crash").target_sync_receipt == receipt


def test_resolve_target_sync_conflict_rejects_unresolved_paths_without_mutation(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-unresolved")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    request = SyncChangeWithTarget(
        change_id="sync-unresolved",
        expected_target=target_head,
        operation_id="sync-unresolved-1",
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(request)

    with pytest.raises(RuntimeError, match="still has unresolved paths"):
        manager.resolve_target_sync_conflict(
            TargetSyncConflictRequest(
                change_id="sync-unresolved",
                target_head=target_head,
                operation_id="sync-unresolved-1",
            )
        )

    assert _git(worktree, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 0
    assert coordinator.show("sync-unresolved").target_sync_conflict is not None
    assert coordinator.show("sync-unresolved").target_sync_receipt is None


def test_target_sync_conflict_exit_rejects_mismatched_operation_without_mutation(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-mismatch")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(
            SyncChangeWithTarget(
                change_id="sync-mismatch",
                expected_target=target_head,
                operation_id="sync-mismatch-1",
            )
        )

    with pytest.raises(CoordinationConflictError, match="conflict identity"):
        manager.abort_target_sync_conflict(
            TargetSyncConflictRequest(
                change_id="sync-mismatch",
                target_head=target_head,
                operation_id="different-operation",
            )
        )

    assert _git(worktree, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 0
    assert coordinator.show("sync-mismatch").target_sync_abort_receipt is None

    with pytest.raises(CoordinationConflictError, match="conflict identity"):
        manager.resolve_target_sync_conflict(
            TargetSyncConflictRequest(
                change_id="sync-mismatch",
                target_head="0" * 40,
                operation_id="sync-mismatch-1",
            )
        )

    assert _git(worktree, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 0
    assert coordinator.show("sync-mismatch").target_sync_receipt is None


def test_resolve_target_sync_conflict_records_exact_merge_and_replays(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-resolve")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    request = SyncChangeWithTarget(
        change_id="sync-resolve",
        expected_target=target_head,
        operation_id="sync-resolve-1",
    )
    user_checkout_before = (repository / "product.txt").read_bytes()

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(request)
    (worktree / "product.txt").write_text("resolved\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")

    exit_request = TargetSyncConflictRequest(
        change_id="sync-resolve",
        target_head=target_head,
        operation_id="sync-resolve-1",
    )
    receipt = manager.resolve_target_sync_conflict(exit_request)
    replayed = manager.resolve_target_sync_conflict(exit_request)
    parents = _git(worktree, "rev-list", "--parents", "-n", "1", receipt.merged_head).stdout.split()

    assert replayed == receipt
    assert receipt.change_head_before == reviewed
    assert receipt.target_head == target_head
    assert receipt.merge_commit
    assert parents[1:] == [reviewed, target_head]
    assert coordinator.show("sync-resolve").target_sync_conflict is None
    assert coordinator.show("sync-resolve").target_sync_receipt == receipt
    assert coordinator.show("sync-resolve").publication_base_head == initial
    assert manager.reviewed_source_head("sync-resolve") == receipt.merged_head
    assert _head(repository, "refs/heads/main") != receipt.merged_head
    assert (repository / "product.txt").read_bytes() == user_checkout_before


def _writer(change_id: str) -> ChangeWriter:
    identity = WriterIdentity(
        attempt_id=f"attempt-{change_id}",
        claim_id=f"claim-{change_id}",
        actor_id="builder",
        process_id=f"process-{change_id}",
        claimed_at="2026-08-02T00:01:00Z",
    )
    return ChangeWriter(**identity.model_dump(), job_id=1, kind="build")


def test_publishes_and_replays_exact_change_branch_without_mutating_target_or_user_checkout(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "publish-change")
    worktree_status = _git(worktree, "status", "--porcelain").stdout
    _git(repository, "branch", "release", initial)
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    _git(repository, "update-ref", "-d", "refs/remotes/origin/main")
    (repository / "user.txt").write_text("uncommitted user work\n", encoding="utf-8")

    receipt = publisher.publish(
        PublishChangeBranch(change_id="publish-change", expected_remote_head=None, operation_id="operation-1")
    )
    replayed = publisher.publish(
        PublishChangeBranch(change_id="publish-change", expected_remote_head=None, operation_id="operation-1")
    )

    assert receipt.published_head == reviewed
    assert receipt.expected_remote_head is None
    assert replayed == receipt
    assert _head(remote, "refs/heads/owlbear/change/publish-change") == reviewed
    assert _head(remote, "refs/heads/main") == initial
    assert _head(repository, "refs/heads/main") == initial
    assert _head(repository, "refs/heads/release") == initial
    assert _head(repository) == initial
    assert _git(repository, "show-ref", "--verify", "--quiet", "refs/remotes/origin/main", check=False).returncode == 1
    assert (repository / "user.txt").read_text(encoding="utf-8") == "uncommitted user work\n"
    assert _head(worktree) == reviewed
    assert _git(worktree, "status", "--porcelain").stdout == worktree_status


def test_supersedes_published_change_without_rewriting_predecessor(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, superseding = _reviewed_change(manager, "successor-change")
    predecessor_branch = "owlbear/change/successor-change"
    _git(repository, "push", "origin", f"{initial}:refs/heads/{predecessor_branch}")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = SupersedeChangeBranch(
        change_id="successor-change",
        expected_published_branch=predecessor_branch,
        expected_published_head=initial,
        superseding_head=superseding,
        operation_id="supersede-1",
    )

    receipt = publisher.supersede(request)
    replayed = publisher.supersede(request)

    assert isinstance(receipt, ChangeBranchSupersessionReceipt)
    assert replayed == receipt
    assert receipt.predecessor_branch == predecessor_branch
    assert receipt.predecessor_head == initial
    assert receipt.successor_branch == f"{predecessor_branch}+s1"
    assert receipt.superseding_head == superseding
    assert _head(remote, f"refs/heads/{predecessor_branch}") == initial
    assert _head(remote, f"refs/heads/{predecessor_branch}+s1") == superseding
    assert (
        _git(
            repository, "show-ref", "--verify", "--quiet", f"refs/heads/{predecessor_branch}+s1", check=False
        ).returncode
        == 1
    )
    assert _head(repository, f"refs/heads/{predecessor_branch}") == superseding
    assert coordinator.show("successor-change").publication_lease is None


def test_supersession_allocates_after_existing_successor_refs(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, superseding = _reviewed_change(manager, "successor-index")
    predecessor_branch = "owlbear/change/successor-index"
    _git(repository, "push", "origin", f"{initial}:refs/heads/{predecessor_branch}")
    _git(repository, "push", "origin", f"{initial}:refs/heads/{predecessor_branch}+s1")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    receipt = publisher.supersede(
        SupersedeChangeBranch(
            change_id="successor-index",
            expected_published_branch=predecessor_branch,
            expected_published_head=initial,
            superseding_head=superseding,
            operation_id="supersede-index",
        )
    )

    assert receipt.successor_branch == f"{predecessor_branch}+s2"
    assert _head(remote, f"refs/heads/{predecessor_branch}+s1") == initial
    assert _head(remote, f"refs/heads/{predecessor_branch}+s2") == superseding


def test_successor_allocation_ignores_other_change_refs(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, superseding = _reviewed_change(manager, "foo")
    predecessor_branch = "owlbear/change/foo"
    _git(repository, "push", "origin", f"{initial}:refs/heads/{predecessor_branch}")
    _git(repository, "push", "origin", f"{initial}:refs/heads/owlbear/change/foo-session")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    receipt = publisher.supersede(
        SupersedeChangeBranch(
            change_id="foo",
            expected_published_branch=predecessor_branch,
            expected_published_head=initial,
            superseding_head=superseding,
            operation_id="supersede-sibling",
        )
    )

    assert receipt.successor_branch == f"{predecessor_branch}+s1"


def test_supersedes_an_existing_successor_history_chain(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, first_superseding = _reviewed_change(manager, "chained-change")
    predecessor_branch = "owlbear/change/chained-change"
    _git(repository, "push", "origin", f"{initial}:refs/heads/{predecessor_branch}")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    first_receipt = publisher.supersede(
        SupersedeChangeBranch(
            change_id="chained-change",
            expected_published_branch=predecessor_branch,
            expected_published_head=initial,
            superseding_head=first_superseding,
            operation_id="supersede-chain-1",
        )
    )
    (worktree / "product.txt").write_text("second superseding review\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "second superseding review")
    second_superseding = _head(worktree)
    manager.record_reviewed("chained-change", second_superseding)

    second_receipt = publisher.supersede(
        SupersedeChangeBranch(
            change_id="chained-change",
            expected_published_branch=first_receipt.successor_branch,
            expected_published_head=first_superseding,
            superseding_head=second_superseding,
            operation_id="supersede-chain-2",
        )
    )

    assert second_receipt.successor_branch == f"{predecessor_branch}+s2"
    assert _head(remote, first_receipt.successor_branch) == first_superseding
    assert _head(remote, second_receipt.successor_branch) == second_superseding


def test_rejects_noop_supersession(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "noop-change")
    predecessor_branch = "owlbear/change/noop-change"
    _git(repository, "push", "origin", f"{reviewed}:refs/heads/{predecessor_branch}")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with pytest.raises(PublicationProviderError) as error:
        publisher.supersede(
            SupersedeChangeBranch(
                change_id="noop-change",
                expected_published_branch=predecessor_branch,
                expected_published_head=reviewed,
                superseding_head=reviewed,
                operation_id="supersede-noop",
            )
        )

    assert error.value.code == PublicationProviderFailureCode.CONFLICT
    assert (
        _git(
            remote,
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/heads/{predecessor_branch}+s1",
            check=False,
        ).returncode
        == 1
    )


def test_rejects_foreign_predecessor_branch(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, superseding = _reviewed_change(manager, "current-change")
    _git(repository, "push", "origin", f"{initial}:refs/heads/owlbear/change/other-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with pytest.raises(PublicationProviderError) as error:
        publisher.supersede(
            SupersedeChangeBranch(
                change_id="current-change",
                expected_published_branch="owlbear/change/other-change",
                expected_published_head=initial,
                superseding_head=superseding,
                operation_id="supersede-foreign",
            )
        )

    assert error.value.code == PublicationProviderFailureCode.CONFLICT
    assert (
        _git(
            remote,
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/owlbear/change/current-change+s1",
            check=False,
        ).returncode
        == 1
    )


def test_adopts_exact_reviewed_remote_head_when_durable_head_is_missing(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "migrated-change")
    _git(repository, "push", "origin", f"{reviewed}:refs/heads/owlbear/change/migrated-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with patch.object(publisher, "_push_exact_head", side_effect=AssertionError("unexpected push")):
        receipt = publisher.publish(
            PublishChangeBranch(
                change_id="migrated-change",
                expected_remote_head=None,
                expected_published_head=reviewed,
                operation_id="migration-recovery",
            )
        )

    assert receipt.published_head == reviewed
    assert receipt.expected_remote_head is None
    assert _head(remote, "refs/heads/owlbear/change/migrated-change") == reviewed


def test_adopts_exact_reviewed_remote_head_after_lost_push_response(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "lost-push-change")
    _git(repository, "push", "origin", f"{reviewed}:refs/heads/owlbear/change/lost-push-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with patch.object(publisher, "_push_exact_head", side_effect=AssertionError("unexpected push")):
        receipt = publisher.publish(
            PublishChangeBranch(
                change_id="lost-push-change",
                expected_remote_head=initial,
                expected_published_head=reviewed,
                operation_id="lost-push-response",
            )
        )

    assert receipt.published_head == reviewed
    assert receipt.expected_remote_head == initial
    assert _head(remote, "refs/heads/owlbear/change/lost-push-change") == reviewed


def test_fast_forwards_observed_ancestor_when_durable_head_is_missing(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, first_reviewed = _reviewed_change(manager, "recovered-change")
    _git(repository, "push", "origin", f"{first_reviewed}:refs/heads/owlbear/change/recovered-change")
    (worktree / "product.txt").write_text("second reviewed\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "second reviewed change")
    second_reviewed = _head(worktree)
    manager.record_reviewed("recovered-change", second_reviewed)
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    receipt = publisher.publish(
        PublishChangeBranch(
            change_id="recovered-change",
            expected_remote_head=None,
            expected_published_head=second_reviewed,
            operation_id="lost-local-recording-recovery",
        )
    )

    assert receipt.published_head == second_reviewed
    assert receipt.expected_remote_head is None
    assert _head(remote, "refs/heads/owlbear/change/recovered-change") == second_reviewed


def test_recovers_unrecorded_remote_advance_between_durable_and_reviewed_heads(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, first_reviewed = _reviewed_change(manager, "intermediate-change")
    _git(repository, "push", "origin", f"{first_reviewed}:refs/heads/owlbear/change/intermediate-change")
    (worktree / "product.txt").write_text("second reviewed\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "second reviewed change")
    second_reviewed = _head(worktree)
    manager.record_reviewed("intermediate-change", second_reviewed)
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    receipt = publisher.publish(
        PublishChangeBranch(
            change_id="intermediate-change",
            expected_remote_head=initial,
            expected_published_head=second_reviewed,
            operation_id="unrecorded-intermediate-advance",
        )
    )

    assert receipt.published_head == second_reviewed
    assert receipt.expected_remote_head == initial
    assert _head(remote, "refs/heads/owlbear/change/intermediate-change") == second_reviewed


def test_rejects_reviewed_head_drift_before_remote_publication(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "drifted-checkpoint")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(
            PublishChangeBranch(
                change_id="drifted-checkpoint",
                expected_remote_head=None,
                expected_published_head="f" * 40,
                operation_id="stale-checkpoint",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert _head(repository, "refs/heads/owlbear/change/drifted-checkpoint") == reviewed
    assert (
        _git(
            remote,
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/owlbear/change/drifted-checkpoint",
            check=False,
        ).returncode
        == 1
    )


def test_rejects_divergent_remote_change_branch_without_rewriting_it(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "diverged-change")
    divergent = _git(
        repository, "commit-tree", _git(repository, "mktree").stdout.strip(), "-m", "divergent"
    ).stdout.strip()
    _git(repository, "push", "origin", f"{divergent}:refs/heads/owlbear/change/diverged-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(
            PublishChangeBranch(
                change_id="diverged-change",
                expected_remote_head=divergent,
                operation_id="operation-2",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert _head(remote, "refs/heads/owlbear/change/diverged-change") == divergent
    assert coordinator.show("diverged-change").publication_lease is None


def test_rejects_remote_only_divergent_change_head_as_permanent_conflict(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "remote-diverged-change")
    _git(remote, "config", "user.name", "Remote Test User")
    _git(remote, "config", "user.email", "remote@example.com")
    divergent = _git(
        remote,
        "commit-tree",
        _git(remote, "mktree").stdout.strip(),
        "-m",
        "remote-only divergent",
    ).stdout.strip()
    _git(remote, "update-ref", "refs/heads/owlbear/change/remote-diverged-change", divergent)
    assert _git(repository, "cat-file", "-e", f"{divergent}^{{commit}}", check=False).returncode != 0
    fetch_head = Path(_git(repository, "rev-parse", "--git-path", "FETCH_HEAD").stdout.strip())
    fetch_head_before = fetch_head.read_bytes() if fetch_head.exists() else None
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(
            PublishChangeBranch(
                change_id="remote-diverged-change",
                expected_remote_head=None,
                operation_id="remote-divergence",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert not exc_info.value.retry_safe
    assert _head(remote, "refs/heads/owlbear/change/remote-diverged-change") == divergent
    assert (fetch_head.read_bytes() if fetch_head.exists() else None) == fetch_head_before
    assert (
        _git(
            repository,
            "show-ref",
            "--verify",
            "--quiet",
            "refs/remotes/origin/owlbear/change/remote-diverged-change",
            check=False,
        ).returncode
        == 1
    )
    assert coordinator.show("remote-diverged-change").publication_lease is None


def test_remote_change_branch_deletion_during_fetch_is_retryable_conflict(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "deleted-during-fetch")
    _git(remote, "config", "user.name", "Remote Test User")
    _git(remote, "config", "user.email", "remote@example.com")
    divergent = _git(
        remote,
        "commit-tree",
        _git(remote, "mktree").stdout.strip(),
        "-m",
        "deleted remote head",
    ).stdout.strip()
    branch_ref = "refs/heads/owlbear/change/deleted-during-fetch"
    _git(remote, "update-ref", branch_ref, divergent)
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_run_git = publisher._run_git

    def delete_before_fetch(*arguments: str):
        if arguments[0] == "fetch" and arguments[-1] == branch_ref:
            _git(remote, "update-ref", "-d", branch_ref)
        return original_run_git(*arguments)

    with (
        patch.object(publisher, "_run_git", side_effect=delete_before_fetch),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(
                change_id="deleted-during-fetch",
                expected_remote_head=None,
                operation_id="deleted-during-fetch",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert exc_info.value.retry_safe
    assert coordinator.show("deleted-during-fetch").publication_lease is None


def test_fast_forward_push_rejects_divergent_remote_advance(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "raced-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_push = publisher._push_exact_head
    competing = _git(
        repository, "commit-tree", _git(repository, "mktree").stdout.strip(), "-m", "competing"
    ).stdout.strip()

    def advance_then_push(operation: Any, request: PublishChangeBranch, attempt: Any) -> None:
        _git(repository, "push", "origin", f"{competing}:refs/heads/{operation.branch}")
        original_push(operation, request, attempt)

    with (
        patch.object(publisher, "_push_exact_head", side_effect=advance_then_push),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(change_id="raced-change", expected_remote_head=None, operation_id="operation-3")
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert exc_info.value.retry_safe is True
    assert _head(remote, "refs/heads/owlbear/change/raced-change") == competing
    assert _head(repository, "refs/heads/owlbear/change/raced-change") == reviewed
    assert coordinator.show("raced-change").publication_lease is None


def test_fast_forward_push_rejects_divergent_remote_creation(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "created-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_push = publisher._push_exact_head
    competing = _git(
        repository, "commit-tree", _git(repository, "mktree").stdout.strip(), "-m", "competing"
    ).stdout.strip()

    def create_then_push(operation: Any, request: PublishChangeBranch, attempt: Any) -> None:
        _git(repository, "push", "origin", f"{competing}:refs/heads/{operation.branch}")
        original_push(operation, request, attempt)

    with (
        patch.object(publisher, "_push_exact_head", side_effect=create_then_push),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(change_id="created-change", expected_remote_head=None, operation_id="operation-create")
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert exc_info.value.retry_safe is True
    assert _head(remote, "refs/heads/owlbear/change/created-change") == competing
    assert _head(repository, "refs/heads/owlbear/change/created-change") == reviewed


def test_fast_forwards_existing_remote_change_branch_from_exact_expected_head(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "update-change")
    _git(repository, "push", "origin", f"{initial}:refs/heads/owlbear/change/update-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    receipt = publisher.publish(
        PublishChangeBranch(
            change_id="update-change",
            expected_remote_head=initial,
            operation_id="operation-update",
        )
    )

    assert receipt.expected_remote_head == initial
    assert receipt.published_head == reviewed
    assert _head(remote, "refs/heads/owlbear/change/update-change") == reviewed
    assert _head(remote, "refs/heads/main") == initial


def test_fast_forward_push_admits_concurrent_ancestor_advance(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, intermediate = _reviewed_change(manager, "ancestor-race-change")
    (worktree / "product.txt").write_text("reviewed successor\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "reviewed successor")
    reviewed = _head(worktree)
    manager.record_reviewed("ancestor-race-change", reviewed)
    branch = "owlbear/change/ancestor-race-change"
    _git(repository, "push", "origin", f"{initial}:refs/heads/{branch}")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_push = publisher._push_exact_head

    def advance_then_push(operation: Any, request: PublishChangeBranch, attempt: Any) -> None:
        _git(repository, "push", "origin", f"{intermediate}:refs/heads/{operation.branch}")
        original_push(operation, request, attempt)

    with patch.object(publisher, "_push_exact_head", side_effect=advance_then_push):
        receipt = publisher.publish(
            PublishChangeBranch(
                change_id="ancestor-race-change",
                expected_remote_head=initial,
                operation_id="operation-ancestor-race",
            )
        )

    assert receipt.published_head == reviewed
    assert _head(remote, f"refs/heads/{branch}") == reviewed


def test_fast_forward_push_recreates_deleted_remote_at_exact_reviewed_head(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "deleted-change")
    branch = "owlbear/change/deleted-change"
    _git(repository, "push", "origin", f"{initial}:refs/heads/{branch}")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_push = publisher._push_exact_head

    def delete_then_push(operation: Any, request: PublishChangeBranch, attempt: Any) -> None:
        _git(repository, "push", "origin", f":refs/heads/{operation.branch}")
        original_push(operation, request, attempt)

    with patch.object(publisher, "_push_exact_head", side_effect=delete_then_push):
        receipt = publisher.publish(
            PublishChangeBranch(
                change_id="deleted-change",
                expected_remote_head=initial,
                operation_id="operation-delete-race",
            )
        )

    assert receipt.published_head == reviewed
    assert _head(remote, f"refs/heads/{branch}") == reviewed
    assert _head(repository, f"refs/heads/{branch}") == reviewed


def test_replay_rejects_receipt_after_reviewed_boundary_advances(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "superseded-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = PublishChangeBranch(
        change_id="superseded-change",
        expected_remote_head=None,
        operation_id="operation-superseded",
    )
    publisher.publish(request)
    (worktree / "product.txt").write_text("superseded\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "superseding review")
    manager.record_reviewed("superseded-change", _head(worktree))

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(request)

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT


def test_first_attempt_excludes_writer_until_push_completes(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "reserved-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_push = publisher._push_exact_head

    def assert_reserved_then_push(operation: Any, request: PublishChangeBranch, attempt: Any) -> None:
        with pytest.raises(CoordinationConflictError, match="active writer"):
            coordinator.acquire("reserved-change", _writer("reserved-change"))
        original_push(operation, request, attempt)

    with patch.object(publisher, "_push_exact_head", side_effect=assert_reserved_then_push):
        publisher.publish(
            PublishChangeBranch(
                change_id="reserved-change",
                expected_remote_head=None,
                operation_id="operation-reserved",
            )
        )

    assert coordinator.show("reserved-change").publication_lease is None


def test_same_operation_concurrent_publisher_conflicts_without_releasing_owner(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "concurrent-change")
    owner = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    contender = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = PublishChangeBranch(
        change_id="concurrent-change",
        expected_remote_head=None,
        operation_id="operation-concurrent",
    )
    push_entered = Event()
    allow_push = Event()
    original_push = owner._push_exact_head

    def paused_push(operation: Any, publish_request: PublishChangeBranch, attempt: Any) -> None:
        push_entered.set()
        assert allow_push.wait(timeout=5)
        original_push(operation, publish_request, attempt)

    with patch.object(owner, "_push_exact_head", side_effect=paused_push), ThreadPoolExecutor() as executor:
        owner_result = executor.submit(owner.publish, request)
        assert push_entered.wait(timeout=5)
        retained = coordinator.show("concurrent-change").publication_lease
        assert retained is not None

        with pytest.raises(PublicationProviderError) as exc_info:
            contender.publish(request)

        assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
        assert exc_info.value.retry_safe is True
        assert coordinator.show("concurrent-change").publication_lease == retained
        allow_push.set()
        receipt = owner_result.result(timeout=5)

    assert receipt.published_head == reviewed
    assert coordinator.show("concurrent-change").publication_lease is None


def test_pre_push_timeout_releases_reservation_for_new_operation(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "timeout-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with (
        patch.object(publisher, "_remote_head", side_effect=subprocess.TimeoutExpired(("git", "ls-remote"), 30)),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(change_id="timeout-change", expected_remote_head=None, operation_id="operation-timeout")
        )

    assert exc_info.value.code is PublicationProviderFailureCode.TIMEOUT
    assert exc_info.value.retry_safe is True
    assert coordinator.show("timeout-change").publication_lease is None
    with coordinator.publication_lock("timeout-change") as lock:
        assert (
            coordinator.reserve_publication(
                "timeout-change",
                PublicationLease(
                    operation_id="operation-after-timeout",
                    owner_id="owner-after-timeout",
                    expires_at="2026-08-02T00:10:00Z",
                ),
                lock,
                now="2026-08-02T00:00:00Z",
            ).publication_lease
            is not None
        )


@pytest.mark.parametrize(
    "incident",
    [
        "provider-unavailable",
        "authentication-failure",
        "rate-limit",
        "remote-rejection",
        "pre-write-timeout",
        "post-write-timeout",
    ],
)
@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_publication_incidents_preserve_checkout_and_classify_exact_operation(  # noqa: PLR0913, PLR0917
    tmp_path: Path,
    incident: str,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    coordinator, manager = _change_workspace(tmp_path, repository)
    change_id = f"incident-{user_state}-{incident}"
    _worktree, reviewed = _reviewed_change(manager, change_id)
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = PublishChangeBranch(
        change_id=change_id,
        expected_remote_head=None,
        operation_id=f"operation-{incident}",
    )
    before = user_checkout_snapshot(
        repository,
        (
            f"refs/heads/owlbear/change/{change_id}",
            f"refs/remotes/origin/owlbear/change/{change_id}",
        ),
    )

    expected_codes = {
        "provider-unavailable": PublicationProviderFailureCode.UNAVAILABLE,
        "authentication-failure": PublicationProviderFailureCode.AUTHENTICATION_REQUIRED,
        "rate-limit": PublicationProviderFailureCode.RATE_LIMITED,
        "remote-rejection": PublicationProviderFailureCode.CONFLICT,
        "pre-write-timeout": PublicationProviderFailureCode.TIMEOUT,
        "post-write-timeout": PublicationProviderFailureCode.RESPONSE_UNKNOWN,
    }
    expected_retry_safety = {
        "provider-unavailable": True,
        "authentication-failure": False,
        "rate-limit": True,
        "remote-rejection": False,
        "pre-write-timeout": True,
        "post-write-timeout": False,
    }

    if incident in {
        "provider-unavailable",
        "authentication-failure",
        "rate-limit",
        "remote-rejection",
    }:
        original_run = publisher._run_git
        diagnostics = {
            "provider-unavailable": "provider unavailable",
            "authentication-failure": "Authentication failed",
            "rate-limit": "rate limit exceeded",
            "remote-rejection": "remote rejected",
        }

        def reject_push(*arguments: str) -> subprocess.CompletedProcess[bytes]:
            if arguments[0] == "push":
                return subprocess.CompletedProcess(
                    arguments,
                    1,
                    stdout=b"",
                    stderr=diagnostics[incident].encode(),
                )
            return original_run(*arguments)

        with (
            patch.object(publisher, "_run_git", side_effect=reject_push),
            pytest.raises(PublicationProviderError) as exc_info,
        ):
            publisher.publish(request)
    elif incident == "pre-write-timeout":
        with (
            patch.object(
                publisher,
                "_remote_head",
                side_effect=subprocess.TimeoutExpired(("git", "ls-remote"), 30),
            ),
            pytest.raises(PublicationProviderError) as exc_info,
        ):
            publisher.publish(request)
    else:
        with (
            patch.object(
                publisher,
                "_push_exact_head",
                side_effect=subprocess.TimeoutExpired(("git", "push"), 30),
            ),
            pytest.raises(PublicationProviderError) as exc_info,
        ):
            publisher.publish(request)

    assert exc_info.value.code is expected_codes[incident]
    assert exc_info.value.retry_safe is expected_retry_safety[incident]

    before.assert_unchanged(repository)
    if incident == "post-write-timeout":
        assert coordinator.show(change_id).publication_lease is not None
        return

    receipt = publisher.publish(request)
    assert receipt.published_head == reviewed
    assert publisher.publish(request) == receipt
    before.assert_unchanged(repository)


def test_unexpected_pre_write_failure_releases_lease(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "unexpected-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with (
        patch.object(publisher, "_remote_head", side_effect=RuntimeError("unexpected")),
        pytest.raises(RuntimeError, match="unexpected"),
    ):
        publisher.publish(
            PublishChangeBranch(
                change_id="unexpected-change",
                expected_remote_head=None,
                operation_id="operation-unexpected",
            )
        )

    assert coordinator.show("unexpected-change").publication_lease is None


def test_failed_push_with_unchanged_remote_is_retryable_and_releases_lease(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "failed-push-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_run = publisher._run_git

    def reject_push(*arguments: str) -> subprocess.CompletedProcess[bytes]:
        if arguments[0] == "push":
            return subprocess.CompletedProcess(arguments, 1, stdout=b"", stderr=b"rejected")
        return original_run(*arguments)

    with (
        patch.object(publisher, "_run_git", side_effect=reject_push),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(
                change_id="failed-push-change",
                expected_remote_head=None,
                operation_id="operation-failed-push",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    assert exc_info.value.retry_safe is True
    assert coordinator.show("failed-push-change").publication_lease is None


def test_failed_push_replays_after_unrelated_target_advance(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "target-advance-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_run = publisher._run_git

    def reject_push(*arguments: str) -> subprocess.CompletedProcess[bytes]:
        if arguments[0] == "push":
            return subprocess.CompletedProcess(arguments, 1, stdout=b"", stderr=b"rejected")
        return original_run(*arguments)

    request = PublishChangeBranch(
        change_id="target-advance-change",
        expected_remote_head=None,
        expected_published_head=reviewed,
        operation_id="target-advance-replay",
    )
    with (
        patch.object(publisher, "_run_git", side_effect=reject_push),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(request)

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    assert exc_info.value.retry_safe
    unrelated_target = _git(
        repository,
        "commit-tree",
        _git(repository, "rev-parse", f"{initial}^{{tree}}").stdout.strip(),
        "-p",
        initial,
        "-m",
        "unrelated target advance",
    ).stdout.strip()
    _git(repository, "push", "origin", f"{unrelated_target}:refs/heads/main")

    receipt = publisher.publish(request)

    assert receipt.published_head == reviewed
    assert _head(remote, "refs/heads/owlbear/change/target-advance-change") == reviewed


def test_published_operation_replays_with_active_writer(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "writer-replay-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = PublishChangeBranch(
        change_id="writer-replay-change",
        expected_remote_head=None,
        expected_published_head=reviewed,
        operation_id="writer-replay",
    )
    receipt = publisher.publish(request)
    coordinator.acquire("writer-replay-change", _writer("writer-replay-change"))

    replayed = publisher.publish(request.model_copy(update={"expected_remote_head": reviewed}))

    assert replayed == receipt


def test_authentication_failed_push_is_terminal_and_releases_reservation(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "auth-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_run = publisher._run_git

    def reject_authentication(*arguments: str) -> subprocess.CompletedProcess[bytes]:
        if arguments[0] == "push":
            return subprocess.CompletedProcess(arguments, 128, stdout=b"", stderr=b"Authentication failed")
        return original_run(*arguments)

    with (
        patch.object(publisher, "_run_git", side_effect=reject_authentication),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(change_id="auth-change", expected_remote_head=None, operation_id="operation-auth")
        )

    assert exc_info.value.code is PublicationProviderFailureCode.AUTHENTICATION_REQUIRED
    assert exc_info.value.retry_safe is False
    assert coordinator.show("auth-change").publication_lease is None


def test_push_timeout_after_remote_applies_returns_receipt_and_releases_reservation(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "lost-response-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_run = publisher._run_git

    def push_then_timeout(*arguments: str) -> subprocess.CompletedProcess[bytes]:
        if arguments[0] == "push":
            completed = original_run(*arguments)
            assert completed.returncode == 0
            raise subprocess.TimeoutExpired(arguments, 30)
        return original_run(*arguments)

    with patch.object(publisher, "_run_git", side_effect=push_then_timeout):
        receipt = publisher.publish(
            PublishChangeBranch(
                change_id="lost-response-change",
                expected_remote_head=None,
                operation_id="operation-lost-response",
            )
        )

    assert receipt.published_head == reviewed
    assert _head(remote, "refs/heads/owlbear/change/lost-response-change") == reviewed
    assert coordinator.show("lost-response-change").publication_lease is None


def test_rejects_dirty_change_worktree_before_creating_remote_branch(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "dirty-change")
    (worktree / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(
            PublishChangeBranch(change_id="dirty-change", expected_remote_head=None, operation_id="operation-dirty")
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert (
        _git(
            remote,
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/owlbear/change/dirty-change",
            check=False,
        ).returncode
        == 1
    )


def test_rejects_active_writer_before_creating_remote_branch(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "active-change")
    coordinator.acquire("active-change", _writer("active-change"))
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(
            PublishChangeBranch(change_id="active-change", expected_remote_head=None, operation_id="operation-active")
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert (
        _git(
            remote,
            "show-ref",
            "--verify",
            "--quiet",
            "refs/heads/owlbear/change/active-change",
            check=False,
        ).returncode
        == 1
    )


def test_rejects_option_shaped_remote_head_before_any_later_git_operation(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, _reviewed = _reviewed_change(manager, "hostile-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    original_run = publisher._run_git
    later_operations: list[str] = []

    def hostile_ls_remote(*arguments: str) -> subprocess.CompletedProcess[bytes]:
        if arguments[0] == "ls-remote":
            return subprocess.CompletedProcess(
                arguments,
                0,
                stdout=b"--upload-pack=/tmp/payload\trefs/heads/main\n",
                stderr=b"",
            )
        later_operations.append(arguments[0])
        return original_run(*arguments)

    with (
        patch.object(publisher, "_run_git", side_effect=hostile_ls_remote),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(
                change_id="hostile-change",
                expected_remote_head=None,
                operation_id="operation-hostile",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert "fetch" not in later_operations
    assert "push" not in later_operations
