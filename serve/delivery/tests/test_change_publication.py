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

import hashlib
import json
import os
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
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
    ChangeTargetSyncStaleError,
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
    change_publication,
    remote_git,
    workspace_target_sync,
)
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.remote_git import RemoteGitTimeout
from owlbear_delivery.storage_io import locked_roots


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        (resolve_git_executable(), "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )


def _head(repository: Path, revision: str = "HEAD") -> str:
    return _git(repository, "rev-parse", "--verify", f"{revision}^{{commit}}").stdout.strip()


def _git_ref_exists(repository: Path, reference: str) -> bool:
    return _git(repository, "show-ref", "--verify", "--quiet", reference, check=False).returncode == 0


def _private_target_ref(change_id: str, operation_id: str) -> str:
    key = hashlib.sha256(f"{change_id}\0{operation_id}".encode()).hexdigest()
    return f"refs/owlbear/target-sync/{key}"


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
    coordinator = PortfolioCoordinator(tmp_path / "state")
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


def test_observe_remote_head_reads_only_the_exact_change_branch(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    coordination = manager.ensure("observe-remote")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )

    assert publisher.observe_remote_head("observe-remote") is None
    _git(repository, "push", "origin", f"{initial}:refs/heads/{coordination.branch}")

    assert publisher.observe_remote_head("observe-remote") == initial


def _advance_remote_target(
    tmp_path: Path,
    remote: Path,
    *,
    product: str | None = None,
    repository_name: str = "target-repository",
    path: str = "target.txt",
) -> str:
    target_repository = tmp_path / repository_name
    _git(tmp_path, "clone", str(remote), str(target_repository))
    _git(target_repository, "config", "user.name", "Target User")
    _git(target_repository, "config", "user.email", "target@example.com")
    if product is not None:
        (target_repository / "product.txt").write_text(product, encoding="utf-8")
    else:
        (target_repository / path).write_text("target\n", encoding="utf-8")
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

    with patch.object(
        workspace_target_sync, "run_remote_git", wraps=workspace_target_sync.run_remote_git
    ) as remote_git:
        receipt = manager.sync_with_target(request)

    fetch_calls = [call for call in remote_git.call_args_list if call.args[1][0] == "fetch"]
    assert len(fetch_calls) == 1
    private_ref = _private_target_ref("sync-change", "sync-change-1")
    assert fetch_calls[0].args[1][-1] == f"+refs/heads/main:{private_ref}"
    assert fetch_calls[0].kwargs["kind"] == "read"
    assert not _git_ref_exists(repository, private_ref)

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

    with (
        patch.object(manager, "_run_git", wraps=manager._run_git) as run_git,
        patch.object(workspace_target_sync, "run_remote_git") as replay_remote_git,
    ):
        assert manager.sync_with_target(request) == receipt

    replay_remote_git.assert_not_called()
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


def _private_target_refs(repository: Path) -> dict[str, str]:
    output = _git(repository, "for-each-ref", "--format=%(refname) %(objectname)", "refs/owlbear/target-sync").stdout
    return dict(line.split(" ", 1) for line in output.splitlines())


@pytest.mark.parametrize("operation_id", ["sync..1", "sync.", "sync.lock"])
def test_target_sync_accepts_legal_but_ref_unsafe_operation_ids(tmp_path: Path, operation_id: str) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-ref-unsafe")
    target_head = _advance_remote_target(tmp_path, remote)
    private_ref = _private_target_ref("sync-ref-unsafe", operation_id)

    receipt = manager.sync_with_target(
        SyncChangeWithTarget(change_id="sync-ref-unsafe", expected_target=target_head, operation_id=operation_id)
    )

    assert _git(repository, "check-ref-format", f"refs/heads/{operation_id}", check=False).returncode != 0
    assert _git(repository, "check-ref-format", private_ref).returncode == 0
    assert receipt.operation_id == operation_id
    assert receipt.target_head == target_head
    assert _head(worktree) == receipt.merged_head
    assert coordinator.show("sync-ref-unsafe").target_sync_receipt == receipt
    assert _head(repository, "refs/remotes/origin/main") == target_head
    assert _private_target_refs(repository) == {}


def test_target_sync_rejects_a_private_head_that_differs_from_the_expected_target(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-stale-private")
    advanced = _advance_remote_target(tmp_path, remote)
    before = coordinator.show("sync-stale-private")
    real_runner = workspace_target_sync.run_remote_git
    observed: dict[str, str] = {}

    def fetch_then_observe(*arguments: Any, **options: Any) -> subprocess.CompletedProcess[bytes]:
        result = real_runner(*arguments, **options)
        observed["private"] = _head(repository, _private_target_ref("sync-stale-private", "sync-stale-private-1"))
        observed["shared"] = _head(repository, "refs/remotes/origin/main")
        return result

    with (
        patch.object(workspace_target_sync, "run_remote_git", side_effect=fetch_then_observe),
        pytest.raises(ChangeTargetSyncStaleError, match="target changed while it was fetched"),
    ):
        manager.sync_with_target(
            SyncChangeWithTarget(
                change_id="sync-stale-private",
                expected_target=initial,
                operation_id="sync-stale-private-1",
            )
        )

    assert observed == {"private": advanced, "shared": initial}
    assert _head(repository, "refs/remotes/origin/main") == initial
    assert manager.observed_target_head() == advanced
    assert _private_target_refs(repository) == {}
    assert coordinator.show("sync-stale-private") == before
    assert _head(worktree) == reviewed

    receipt = manager.sync_with_target(
        SyncChangeWithTarget(change_id="sync-stale-private", expected_target=advanced, operation_id="sync-stale-2")
    )

    assert receipt.target_head == advanced
    assert _head(repository, "refs/remotes/origin/main") == advanced
    assert manager.observed_target_head() == advanced
    assert _target_observation_refs(repository) == {}


def _target_observation_generations(repository: Path) -> dict[str, str]:
    output = _git(
        repository, "for-each-ref", "--format=%(refname) %(objectname)", "refs/owlbear/target-observation"
    ).stdout
    return dict(line.split(" ", 1) for line in output.splitlines())


def _target_observation_refs(repository: Path) -> dict[str, str]:
    """Map each observation base to its head, requiring at most one recording per base."""
    generations = _target_observation_generations(repository)
    by_base = {ref.rsplit("/", 1)[0]: head for ref, head in generations.items()}
    assert len(by_base) == len(generations)
    return by_base


def _target_observation_ref(base: str) -> str:
    key = hashlib.sha256(b"refs/remotes/origin/main").hexdigest()
    return f"refs/owlbear/target-observation/{key}/{base}"


def test_target_observation_yields_to_a_later_shared_ref_move(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    _reviewed_change(manager, "sync-observation")
    advanced = _advance_remote_target(tmp_path, remote)
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-observation", expected_target=initial, operation_id="sync-obs-1")
        )
    assert manager.observed_target_head() == advanced
    assert _target_observation_refs(repository) == {_target_observation_ref(initial): advanced}

    operator_head = _advance_remote_target(
        tmp_path, remote, product="operator\n", repository_name="operator-repository"
    )
    _git(repository, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main")

    assert manager.observed_target_head() == operator_head


@pytest.mark.parametrize("operator_move", ["fetch", "update-ref"])
def test_shared_ref_aba_revives_an_observation_only_as_a_self_correcting_hint(
    tmp_path: Path, operator_move: str
) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-aba")
    stale_head = _advance_remote_target(tmp_path, remote)
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-aba", expected_target=initial, operation_id="sync-aba-1")
        )
    assert manager.observed_target_head() == stale_head

    operator_head = _advance_remote_target(tmp_path, remote, product="operator\n", repository_name="operator")
    if operator_move == "fetch":
        _git(repository, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main")
    else:
        # Download the objects only; the operator then moves the shared ref by hand.
        _git(repository, "fetch", "--refmap=", "--no-write-fetch-head", "origin", "refs/heads/main")
        _git(repository, "update-ref", "refs/remotes/origin/main", operator_head, initial)
    assert manager.observed_target_head() == operator_head
    _git(remote, "update-ref", "refs/heads/main", initial)
    if operator_move == "fetch":
        _git(repository, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main")
    else:
        _git(repository, "update-ref", "refs/remotes/origin/main", initial, operator_head)

    # Accepted residual (N02 D7): a return to the exact base revives the hint. The exact fetch refuses
    # it without a merge, and that fetch, which started after the recording, replaces it.
    assert manager.observed_target_head() == stale_head
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-aba", expected_target=stale_head, operation_id="sync-aba-2")
        )
    assert _head(worktree) == reviewed
    assert _head(repository, "refs/remotes/origin/main") == initial
    assert _target_observation_refs(repository) == {}
    assert manager.observed_target_head() == initial
    _restarted_coordinator, restarted = _change_workspace(tmp_path, repository)
    assert restarted.observed_target_head() == initial


def test_target_observation_replacement_and_cleanup_never_select_a_superseded_head(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-replace")
    first = _advance_remote_target(tmp_path, remote)
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-replace", expected_target=initial, operation_id="sync-replace-1")
        )
    second = _advance_remote_target(tmp_path, remote, product="second\n", repository_name="second")
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-replace", expected_target=first, operation_id="sync-replace-2")
        )
    assert manager.observed_target_head() == second
    assert _target_observation_refs(repository) == {_target_observation_ref(initial): second}

    # An exact sync that leaves the shared ref in place still consumes the older observation.
    _git(remote, "update-ref", "refs/heads/main", initial)
    receipt = manager.sync_with_target(
        SyncChangeWithTarget(change_id="sync-replace", expected_target=initial, operation_id="sync-replace-3")
    )
    assert receipt.target_head == initial
    assert _head(worktree) == receipt.merged_head
    assert _head(repository, "refs/remotes/origin/main") == initial
    assert _target_observation_refs(repository) == {}
    assert manager.observed_target_head() == initial


def test_stale_fetch_overlapping_a_shared_ref_move_records_nothing(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "sync-race")
    _advance_remote_target(tmp_path, remote)
    real_runner = workspace_target_sync.run_remote_git

    def fetch_then_move_shared_ref(*arguments: Any, **options: Any) -> subprocess.CompletedProcess[bytes]:
        result = real_runner(*arguments, **options)
        _git(repository, "update-ref", "refs/remotes/origin/main", reviewed, initial)
        return result

    with (
        patch.object(workspace_target_sync, "run_remote_git", side_effect=fetch_then_move_shared_ref),
        pytest.raises(ChangeTargetSyncStaleError),
    ):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-race", expected_target=initial, operation_id="sync-race-1")
        )

    assert _target_observation_refs(repository) == {}
    assert manager.observed_target_head() == reviewed
    _git(repository, "update-ref", "refs/remotes/origin/main", initial, reviewed)
    assert manager.observed_target_head() == initial


def _nested_fetch(inner: Callable[[], None]) -> Callable[..., subprocess.CompletedProcess[bytes]]:
    """Run ``inner`` once, right after the first target fetch returns and before its result is applied."""
    real_runner = workspace_target_sync.run_remote_git
    pending = [inner]

    def runner(*arguments: Any, **options: Any) -> subprocess.CompletedProcess[bytes]:
        result = real_runner(*arguments, **options)
        if pending and arguments[1][0] == "fetch":
            pending.pop()()
        return result

    return runner


def test_overlapping_stale_fetches_keep_the_first_recorded_observation(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    _reviewed_change(manager, "race-one")
    _reviewed_change(manager, "race-two")
    _advance_remote_target(tmp_path, remote)
    later: dict[str, str] = {}

    def second_stale_sync() -> None:
        later["head"] = _advance_remote_target(tmp_path, remote, product="later\n", repository_name="later")
        with pytest.raises(ChangeTargetSyncStaleError):
            manager.sync_with_target(
                SyncChangeWithTarget(change_id="race-two", expected_target=initial, operation_id="race-two-1")
            )
        assert _target_observation_refs(repository) == {_target_observation_ref(initial): later["head"]}

    with (
        patch.object(workspace_target_sync, "run_remote_git", side_effect=_nested_fetch(second_stale_sync)),
        pytest.raises(ChangeTargetSyncStaleError),
    ):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="race-one", expected_target=initial, operation_id="race-one-1")
        )

    # The overlapping fetch that recorded first keeps its observation; nothing is torn or reverted.
    assert _target_observation_refs(repository) == {_target_observation_ref(initial): later["head"]}
    assert manager.observed_target_head() == later["head"]
    assert _head(repository, "refs/remotes/origin/main") == initial

    # A fetch that starts after the recording may replace it.
    newest = _advance_remote_target(tmp_path, remote, product="newest\n", repository_name="newest")
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="race-one", expected_target=initial, operation_id="race-one-2")
        )
    assert _target_observation_refs(repository) == {_target_observation_ref(initial): newest}
    assert manager.observed_target_head() == newest


def test_stale_fetch_snapshot_and_recording_take_the_target_sync_lock(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _reviewed_change(manager, "sync-locked")
    advanced = _advance_remote_target(tmp_path, remote)
    fetched = Event()
    locked = Event()
    real_runner = workspace_target_sync.run_remote_git
    lock_root = (coordinator.runtime_root / "coordination" / "target-sync-lock",)

    def signalling_runner(*arguments: Any, **options: Any) -> subprocess.CompletedProcess[bytes]:
        result = real_runner(*arguments, **options)
        fetched.set()
        assert locked.wait(timeout=10)
        return result

    request = SyncChangeWithTarget(change_id="sync-locked", expected_target=initial, operation_id="sync-locked-1")
    with (
        patch.object(workspace_target_sync, "run_remote_git", side_effect=signalling_runner),
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        with locked_roots(lock_root):
            running = executor.submit(manager.sync_with_target, request)
            # The fetch-start snapshot waits for the lock, so the fetch has not begun.
            assert not fetched.wait(timeout=0.3)
        assert fetched.wait(timeout=10)
        with locked_roots(lock_root):
            locked.set()
            time.sleep(0.3)
            assert not running.done()
            assert _target_observation_refs(repository) == {}
        with pytest.raises(ChangeTargetSyncStaleError):
            running.result(timeout=10)

    assert _target_observation_refs(repository) == {_target_observation_ref(initial): advanced}


def test_exact_sync_that_began_before_a_stale_recording_carries_the_observation(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "carry-exact")
    _reviewed_change(manager, "carry-stale")
    first = _advance_remote_target(tmp_path, remote)
    later: dict[str, str] = {}

    def stale_sync_during_exact_fetch() -> None:
        later["head"] = _advance_remote_target(tmp_path, remote, repository_name="later", path="later.txt")
        with pytest.raises(ChangeTargetSyncStaleError):
            manager.sync_with_target(
                SyncChangeWithTarget(change_id="carry-stale", expected_target=initial, operation_id="carry-stale-1")
            )

    with patch.object(
        workspace_target_sync, "run_remote_git", side_effect=_nested_fetch(stale_sync_during_exact_fetch)
    ):
        receipt = manager.sync_with_target(
            SyncChangeWithTarget(change_id="carry-exact", expected_target=first, operation_id="carry-exact-1")
        )

    # The older exact sync moves the shared ref but never discards the observation recorded after it began.
    assert receipt.target_head == first
    assert _head(worktree) == receipt.merged_head
    assert _head(repository, "refs/remotes/origin/main") == first
    assert _target_observation_refs(repository) == {_target_observation_ref(first): later["head"]}
    assert manager.observed_target_head() == later["head"]

    following = manager.sync_with_target(
        SyncChangeWithTarget(change_id="carry-exact", expected_target=later["head"], operation_id="carry-exact-2")
    )
    assert following.target_head == later["head"]
    assert coordinator.show("carry-exact").target_head == later["head"]
    assert _head(repository, "refs/remotes/origin/main") == later["head"]
    assert _target_observation_refs(repository) == {}


def test_exact_sync_keeps_a_newer_recording_of_the_same_head_after_a_rewind(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "same-head-exact")
    _reviewed_change(manager, "same-head-stale")
    rewound = _advance_remote_target(tmp_path, remote)
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="same-head-stale", expected_target=initial, operation_id="same-stale-1")
        )
    first = _target_observation_generations(repository)
    assert _target_observation_refs(repository) == {_target_observation_ref(initial): rewound}
    exact = _advance_remote_target(tmp_path, remote, repository_name="exact", path="exact.txt")
    recorded: dict[str, str] = {}

    def rewind_and_record_again() -> None:
        _git(remote, "update-ref", "refs/heads/main", rewound, exact)
        with pytest.raises(ChangeTargetSyncStaleError):
            manager.sync_with_target(
                SyncChangeWithTarget(change_id="same-head-stale", expected_target=exact, operation_id="same-stale-2")
            )
        recorded.update(_target_observation_generations(repository))

    with patch.object(workspace_target_sync, "run_remote_git", side_effect=_nested_fetch(rewind_and_record_again)):
        receipt = manager.sync_with_target(
            SyncChangeWithTarget(change_id="same-head-exact", expected_target=exact, operation_id="same-exact-1")
        )

    # The re-recording names the same head under the same base, yet it is a distinct, newer recording.
    assert sorted(recorded.values()) == sorted(first.values()) == [rewound]
    assert recorded.keys() != first.keys()
    assert receipt.target_head == exact
    assert _head(worktree) == receipt.merged_head
    assert _head(repository, "refs/remotes/origin/main") == exact
    assert _target_observation_refs(repository) == {_target_observation_ref(exact): rewound}
    assert manager.observed_target_head() == rewound


def test_overlapping_stale_fetch_yields_to_a_newer_recording_of_the_same_head(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    _reviewed_change(manager, "same-head-one")
    _reviewed_change(manager, "same-head-two")
    rewound = _advance_remote_target(tmp_path, remote)
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="same-head-two", expected_target=initial, operation_id="same-two-1")
        )
    first = _target_observation_generations(repository)
    newer = _advance_remote_target(tmp_path, remote, repository_name="newer", path="newer.txt")
    recorded: dict[str, str] = {}

    def rewind_then_record() -> None:
        _git(remote, "update-ref", "refs/heads/main", rewound, newer)
        with pytest.raises(ChangeTargetSyncStaleError):
            manager.sync_with_target(
                SyncChangeWithTarget(change_id="same-head-two", expected_target=initial, operation_id="same-two-2")
            )
        recorded.update(_target_observation_generations(repository))

    with (
        patch.object(workspace_target_sync, "run_remote_git", side_effect=_nested_fetch(rewind_then_record)),
        pytest.raises(ChangeTargetSyncStaleError),
    ):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="same-head-one", expected_target=initial, operation_id="same-one-1")
        )

    # The first fetch saw ``newer`` but a recording of the rewound head was made after it began, so it yields.
    assert recorded.keys() != first.keys()
    assert _target_observation_generations(repository) == recorded
    assert _target_observation_refs(repository) == {_target_observation_ref(initial): rewound}
    assert manager.observed_target_head() == rewound
    assert _head(repository, "refs/remotes/origin/main") == initial


def test_exact_sync_replans_its_ref_transaction_after_a_concurrent_shared_ref_move(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-replan")
    target_head = _advance_remote_target(tmp_path, remote)
    real_update_refs = manager._update_refs
    attempts: list[list[str]] = []

    def move_shared_ref_first(commands: list[str]) -> bool:
        if not attempts:
            _git(repository, "update-ref", "refs/remotes/origin/main", reviewed, initial)
        attempts.append(commands)
        return real_update_refs(commands)

    with patch.object(manager, "_update_refs", side_effect=move_shared_ref_first):
        receipt = manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-replan", expected_target=target_head, operation_id="sync-replan-1")
        )

    assert attempts == [
        [f"update refs/remotes/origin/main {target_head} {initial}"],
        [f"verify refs/remotes/origin/main {reviewed}"],
    ]
    assert _head(repository, "refs/remotes/origin/main") == reviewed
    assert receipt.target_head == target_head
    assert receipt.merged_head == _head(worktree)


_GIT_SHIM = """#!/bin/sh
printf '%s\\n' "$*" >> "{log}"
previous=
for argument in "$@"; do
  if [ "$previous" = reflog ] && [ "$argument" = write ]; then
    echo "git: 'reflog write' is unavailable in this Git" >&2
    exit 129
  fi
  if [ -e "{fail_marker}" ] && [ "$previous" = update-ref ] && [ "$argument" = --stdin ]; then
    echo "fatal: simulated ref transaction failure" >&2
    exit 128
  fi
  previous=$argument
done
exec "{real}" "$@"
"""


@pytest.fixture
def git_without_reflog_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Path, Path]]:
    """Put a Git on PATH that lacks ``reflog write`` (as Git 2.43 does) and logs every invocation."""
    shim_root = tmp_path / "git-shim"
    shim_root.mkdir()
    log = shim_root / "invocations.log"
    fail_marker = shim_root / "fail-update-ref-stdin"
    shim = shim_root / "git"
    shim.write_text(_GIT_SHIM.format(log=log, fail_marker=fail_marker, real=resolve_git_executable()))
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim_root}{os.pathsep}{os.environ['PATH']}")
    resolve_git_executable.cache_clear()
    assert resolve_git_executable() == str(shim)
    assert _git(tmp_path, "reflog", "write", "refs/heads/x", "0" * 40, "0" * 40, "m", check=False).returncode == 129
    log.unlink()
    try:
        yield log, fail_marker
    finally:
        monkeypatch.undo()
        resolve_git_executable.cache_clear()


def test_stale_then_exact_sync_progresses_without_reflog_write(
    tmp_path: Path, git_without_reflog_write: tuple[Path, Path]
) -> None:
    log, _fail_marker = git_without_reflog_write
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-old-git")
    advanced = _advance_remote_target(tmp_path, remote)

    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-old-git", expected_target=initial, operation_id="sync-old-git-1")
        )
    assert _head(repository, "refs/remotes/origin/main") == initial
    assert manager.observed_target_head() == advanced

    receipt = manager.sync_with_target(
        SyncChangeWithTarget(change_id="sync-old-git", expected_target=advanced, operation_id="sync-old-git-2")
    )
    assert receipt.target_head == advanced
    assert _head(worktree) == receipt.merged_head
    assert coordinator.show("sync-old-git").target_head == advanced
    assert _target_observation_refs(repository) == {}
    invocations = log.read_text().splitlines()
    assert any("update-ref --stdin" in line for line in invocations)
    assert not any(" reflog " in f" {line} " for line in invocations)


def test_unexplained_observation_failure_raises_instead_of_reporting_stale(
    tmp_path: Path, git_without_reflog_write: tuple[Path, Path]
) -> None:
    _log, fail_marker = git_without_reflog_write
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-unrecorded")
    _advance_remote_target(tmp_path, remote)
    fail_marker.touch()

    with pytest.raises(RuntimeError, match="newer target head could not be recorded") as raised:
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-unrecorded", expected_target=initial, operation_id="sync-unrec-1")
        )

    assert not isinstance(raised.value, ChangeTargetSyncStaleError)
    assert _head(repository, "refs/remotes/origin/main") == initial
    assert _target_observation_refs(repository) == {}
    assert _private_target_refs(repository) == {}
    assert _head(worktree) == reviewed


@pytest.mark.parametrize("remote_move", ["rewind", "advance"])
def test_failed_exact_sync_ref_transaction_raises_before_merging(
    tmp_path: Path, git_without_reflog_write: tuple[Path, Path], remote_move: str
) -> None:
    _log, fail_marker = git_without_reflog_write
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-unadvanced")
    stale_head = _advance_remote_target(tmp_path, remote)
    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-unadvanced", expected_target=initial, operation_id="sync-unadv-1")
        )
    if remote_move == "rewind":
        _git(remote, "update-ref", "refs/heads/main", initial)
        expected = initial
    else:
        expected = _advance_remote_target(tmp_path, remote, repository_name="advanced", path="advanced.txt")
    before = coordinator.show("sync-unadvanced")
    request = SyncChangeWithTarget(change_id="sync-unadvanced", expected_target=expected, operation_id="sync-unadv-2")
    fail_marker.touch()

    with pytest.raises(RuntimeError, match="engine target could not be advanced") as raised:
        manager.sync_with_target(request)

    assert not isinstance(raised.value, ChangeTargetSyncStaleError)
    assert _head(worktree) == reviewed
    assert coordinator.show("sync-unadvanced") == before
    assert _head(repository, "refs/remotes/origin/main") == initial
    assert manager.observed_target_head() == stale_head
    assert _private_target_refs(repository) == {}

    fail_marker.unlink()
    receipt = manager.sync_with_target(request)
    assert receipt.target_head == expected
    assert _head(worktree) == receipt.merged_head
    assert _head(repository, "refs/remotes/origin/main") == expected
    assert _target_observation_refs(repository) == {}
    assert manager.observed_target_head() == expected


def test_exact_sync_after_a_remote_rewind_rewinds_the_engine_target(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-rewind")
    abandoned = _advance_remote_target(tmp_path, remote)
    _git(repository, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main")
    _git(remote, "update-ref", "refs/heads/main", initial)
    replacement = _advance_remote_target(
        tmp_path, remote, product="reviewed\n", repository_name="replacement-repository"
    )
    assert replacement != abandoned
    assert manager.observed_target_head() == abandoned

    with pytest.raises(ChangeTargetSyncStaleError):
        manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-rewind", expected_target=abandoned, operation_id="sync-rewind-1")
        )
    assert _head(repository, "refs/remotes/origin/main") == abandoned
    assert manager.observed_target_head() == replacement

    receipt = manager.sync_with_target(
        SyncChangeWithTarget(change_id="sync-rewind", expected_target=replacement, operation_id="sync-rewind-2")
    )

    assert receipt.target_head == replacement
    assert _head(worktree) == receipt.merged_head
    assert coordinator.show("sync-rewind").target_head == replacement
    assert _head(repository, "refs/remotes/origin/main") == replacement
    assert manager.observed_target_head() == replacement
    assert _target_observation_refs(repository) == {}


def test_stale_shared_ref_cas_keeps_the_concurrent_value_and_an_exact_receipt(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-stale-cas")
    target_head = _advance_remote_target(tmp_path, remote)
    real_runner = workspace_target_sync.run_remote_git

    def fetch_then_move_shared_ref(*arguments: Any, **options: Any) -> subprocess.CompletedProcess[bytes]:
        result = real_runner(*arguments, **options)
        _git(repository, "update-ref", "refs/remotes/origin/main", reviewed)
        return result

    with patch.object(workspace_target_sync, "run_remote_git", side_effect=fetch_then_move_shared_ref):
        receipt = manager.sync_with_target(
            SyncChangeWithTarget(change_id="sync-stale-cas", expected_target=target_head, operation_id="sync-cas-1")
        )

    assert _head(repository, "refs/remotes/origin/main") == reviewed
    assert receipt.target_head == receipt.expected_target == target_head
    assert receipt.change_head_before == reviewed
    assert receipt.merged_head == _head(worktree)
    assert _git(repository, "merge-base", "--is-ancestor", target_head, receipt.merged_head).returncode == 0
    assert _private_target_refs(repository) == {}


def test_concurrent_changes_with_one_operation_id_use_distinct_private_refs_until_cas(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    worktrees = {change_id: _reviewed_change(manager, change_id) for change_id in ("sync-pair-a", "sync-pair-b")}
    target_head = _advance_remote_target(tmp_path, remote)
    observed: dict[str, object] = {}

    def observe_both_fetched() -> None:
        observed["private"] = _private_target_refs(repository)
        observed["shared"] = _head(repository, "refs/remotes/origin/main")

    both_fetched = threading.Barrier(2, action=observe_both_fetched, timeout=30)
    real_runner = workspace_target_sync.run_remote_git

    def fetch_then_wait(*arguments: Any, **options: Any) -> subprocess.CompletedProcess[bytes]:
        result = real_runner(*arguments, **options)
        both_fetched.wait()
        return result

    def sync(change_id: str):
        return manager.sync_with_target(
            SyncChangeWithTarget(change_id=change_id, expected_target=target_head, operation_id="sync-shared")
        )

    with (
        patch.object(workspace_target_sync, "run_remote_git", side_effect=fetch_then_wait),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        futures = {change_id: executor.submit(sync, change_id) for change_id in worktrees}
        receipts = {change_id: future.result(timeout=60) for change_id, future in futures.items()}

    expected_private = {_private_target_ref(change_id, "sync-shared"): target_head for change_id in worktrees}
    assert len(expected_private) == 2
    assert observed == {"private": expected_private, "shared": initial}
    for change_id, (worktree, reviewed) in worktrees.items():
        assert receipts[change_id].change_id == change_id
        assert receipts[change_id].operation_id == "sync-shared"
        assert receipts[change_id].target_head == target_head
        assert receipts[change_id].change_head_before == reviewed
        assert receipts[change_id].merged_head == _head(worktree)
    assert _head(repository, "refs/remotes/origin/main") == target_head
    assert _private_target_refs(repository) == {}


def test_slow_target_fetch_of_one_change_does_not_block_another_changes_merge(
    tmp_path: Path,
    ext_remote: Callable[[Path], Any],
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    _coordinator, manager = _change_workspace(tmp_path, repository)
    slow_worktree, _slow_reviewed = _reviewed_change(manager, "sync-slow")
    fast_worktree, _fast_reviewed = _reviewed_change(manager, "sync-fast")
    target_head = _advance_remote_target(tmp_path, remote)
    transport = ext_remote(remote)
    transport.use(repository)
    transport.modes("upload-pack", "gate", "pass")

    def sync(change_id: str):
        return manager.sync_with_target(
            SyncChangeWithTarget(change_id=change_id, expected_target=target_head, operation_id=f"{change_id}-1")
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        slow = executor.submit(sync, "sync-slow")
        try:
            transport.wait_blocked()
            fast_receipt = executor.submit(sync, "sync-fast").result(timeout=30)
            assert not slow.done()
        finally:
            transport.release()
        slow_receipt = slow.result(timeout=30)

    assert fast_receipt.merged_head == _head(fast_worktree)
    assert slow_receipt.merged_head == _head(slow_worktree)
    assert {fast_receipt.target_head, slow_receipt.target_head} == {target_head}


def test_hung_target_fetch_times_out_and_leaves_locks_and_refs_usable(
    tmp_path: Path,
    ext_remote: Callable[[Path], Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "sync-hung")
    target_head = _advance_remote_target(tmp_path, remote)
    transport = ext_remote(remote)
    transport.use(repository)
    transport.modes("upload-pack", "hang", "pass")
    monkeypatch.setattr(remote_git, "READ_TIMEOUT_SECONDS", 1.0)
    request = SyncChangeWithTarget(change_id="sync-hung", expected_target=target_head, operation_id="sync-hung-1")
    before = coordinator.show("sync-hung")

    started = time.monotonic()
    with pytest.raises(RemoteGitTimeout):
        manager.sync_with_target(request)

    assert time.monotonic() - started < 10
    transport.assert_exited("upload-pack")
    assert coordinator.show("sync-hung") == before
    assert _head(repository, "refs/remotes/origin/main") == initial
    assert _head(worktree) == reviewed
    with (
        locked_roots((coordinator.runtime_root / "coordination" / "target-sync-lock",), blocking=False),
        coordinator.publication_lock("sync-hung", blocking=False),
    ):
        pass
    receipt = manager.sync_with_target(request)
    assert receipt.target_head == target_head
    assert _private_target_refs(repository) == {}


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


def test_target_sync_conflict_replaces_stale_receipt_and_normalizes_legacy_pair(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, "sync-conflict-after-receipt")
    first_target = _advance_remote_target(tmp_path, remote)
    first_receipt = manager.sync_with_target(
        SyncChangeWithTarget(
            change_id="sync-conflict-after-receipt",
            expected_target=first_target,
            operation_id="sync-conflict-after-receipt-1",
        )
    )

    (worktree / "product.txt").write_text("source\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "advance Change source")
    manager.record_reviewed("sync-conflict-after-receipt", _head(worktree))
    second_target = _advance_remote_target(
        tmp_path,
        remote,
        product="target\n",
        repository_name="target-repository-2",
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(
            SyncChangeWithTarget(
                change_id="sync-conflict-after-receipt",
                expected_target=second_target,
                operation_id="sync-conflict-after-receipt-2",
            )
        )

    coordination_path = tmp_path / "state/coordination/changes/sync-conflict-after-receipt.json"
    stored = json.loads(coordination_path.read_text(encoding="utf-8"))
    assert stored["target_sync_receipt"] is None
    stored["target_sync_receipt"] = first_receipt.model_dump(mode="json")
    coordination_path.write_text(json.dumps(stored, sort_keys=True) + "\n", encoding="utf-8")

    loaded = coordinator.show("sync-conflict-after-receipt")
    assert loaded.target_sync_receipt is None
    assert loaded.target_sync_conflict is not None
    assert loaded.target_sync_conflict.target_head == second_target


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
    assert _git(worktree, "status", "--porcelain=v1").stdout == "M  product.txt\n"

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
    assert _git(worktree, "status", "--porcelain=v1", "--untracked-files=all").stdout == ""
    assert _git(worktree, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 128
    assert _head(repository, "refs/heads/main") != receipt.merged_head
    assert (repository / "product.txt").read_bytes() == user_checkout_before


@pytest.mark.parametrize("dirty_state", ["unstaged", "untracked"])
def test_resolve_target_sync_conflict_rejects_unstaged_or_untracked_content(
    tmp_path: Path,
    dirty_state: str,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, _reviewed = _reviewed_change(manager, f"sync-{dirty_state}")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    request = SyncChangeWithTarget(
        change_id=f"sync-{dirty_state}",
        expected_target=target_head,
        operation_id=f"sync-{dirty_state}-1",
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        manager.sync_with_target(request)

    (worktree / "product.txt").write_text("resolved\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    if dirty_state == "unstaged":
        (worktree / "product.txt").write_text("unstaged\n", encoding="utf-8")
    else:
        (worktree / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unstaged or untracked changes"):
        manager.resolve_target_sync_conflict(
            TargetSyncConflictRequest(
                change_id=f"sync-{dirty_state}",
                target_head=target_head,
                operation_id=f"sync-{dirty_state}-1",
            )
        )

    assert _head(worktree) == _reviewed
    assert _git(worktree, "rev-parse", "--verify", "MERGE_HEAD", check=False).returncode == 0
    assert coordinator.show(f"sync-{dirty_state}").target_sync_conflict is not None
    assert coordinator.show(f"sync-{dirty_state}").target_sync_receipt is None


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
        "remote-server-error",
        "policy-rejection",
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
        "remote-server-error": PublicationProviderFailureCode.UNAVAILABLE,
        "policy-rejection": PublicationProviderFailureCode.CONFLICT,
        "pre-write-timeout": PublicationProviderFailureCode.TIMEOUT,
        "post-write-timeout": PublicationProviderFailureCode.RESPONSE_UNKNOWN,
    }
    expected_retry_safety = {
        "provider-unavailable": True,
        "authentication-failure": False,
        "rate-limit": True,
        "remote-rejection": False,
        "remote-server-error": True,
        "policy-rejection": False,
        "pre-write-timeout": True,
        "post-write-timeout": False,
    }

    if incident in {
        "provider-unavailable",
        "authentication-failure",
        "rate-limit",
        "remote-rejection",
        "remote-server-error",
        "policy-rejection",
    }:
        original_run = publisher._run_git
        diagnostics = {
            "provider-unavailable": "provider unavailable",
            "authentication-failure": "Authentication failed",
            "rate-limit": "rate limit exceeded",
            "remote-rejection": "remote rejected",
            "remote-server-error": (
                "remote: Internal Server Error        \n"
                "remote: Request ID DEC8:238C1F:24CDBD1:238745E:6AC66161        \n"
                "error: failed to push some refs to 'https://github.com/example/repo.git'\n"
                f"!\t{'a' * 40}:refs/heads/owlbear/change/{change_id}\t[remote rejected] (Internal Server Error)\n"
            ),
            "policy-rejection": (
                "remote: error: GH013: Repository rule violations found for refs/heads/owlbear/change/x.\n"
                f"!\t{'a' * 40}:refs/heads/owlbear/change/{change_id}\t[remote rejected] (push declined due to "
                "repository rule violations)\n"
            ),
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


def test_hung_change_branch_push_reads_back_before_any_retry_and_kills_the_transport(
    tmp_path: Path,
    ext_remote: Callable[[Path], Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "hung-push-change")
    transport = ext_remote(remote)
    transport.use(repository)
    transport.modes("receive-pack", "hang", "pass")
    monkeypatch.setattr(change_publication, "_GIT_TIMEOUT_SECONDS", 1.0)
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = PublishChangeBranch(change_id="hung-push-change", operation_id="operation-hung-push")

    started = time.monotonic()
    with pytest.raises(PublicationProviderError) as raised:
        publisher.publish(request)

    assert time.monotonic() - started < 15
    assert raised.value.code is PublicationProviderFailureCode.TIMEOUT
    assert raised.value.retry_safe
    assert len(transport.pids("receive-pack")) == 1
    transport.assert_exited("receive-pack")
    branch_ref = "refs/heads/owlbear/change/hung-push-change"
    assert _git(remote, "show-ref", "--verify", "--quiet", branch_ref, check=False).returncode != 0
    assert coordinator.show("hung-push-change").publication_lease is None
    with coordinator.publication_lock("hung-push-change", blocking=False):
        pass

    receipt = publisher.publish(request)

    assert receipt.published_head == reviewed
    assert len(transport.pids("receive-pack")) == 2
    assert _head(remote, "refs/heads/owlbear/change/hung-push-change") == reviewed


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
