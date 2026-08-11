from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any
from unittest.mock import patch

import pytest

from owlbear_delivery import (
    ChangeBranchPublisher,
    ChangeWriter,
    ChangeWorkspaceManager,
    CoordinationConflictError,
    PortfolioCoordinator,
    PublicationLease,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublishChangeBranch,
    WriterIdentity,
)
from owlbear_delivery.git_executable import resolve_git_executable


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (resolve_git_executable(), "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )


def _head(repository: Path, revision: str = "HEAD") -> str:
    return _git(repository, "rev-parse", "--verify", f"{revision}^{{commit}}").stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
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
    coordination = manager.create(change_id)
    (coordination.worktree_path / "product.txt").write_text("reviewed\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "reviewed change")
    reviewed = _head(coordination.worktree_path)
    manager.record_reviewed(change_id, reviewed)
    return coordination.worktree_path, reviewed


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
    _worktree, reviewed = _reviewed_change(manager, "publish-change")
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
    assert _head(repository) == initial
    assert _git(repository, "show-ref", "--verify", "--quiet", "refs/remotes/origin/main", check=False).returncode == 1
    assert (repository / "user.txt").read_text(encoding="utf-8") == "uncommitted user work\n"


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


def test_exact_lease_rejects_remote_advance_between_observation_and_push(tmp_path: Path) -> None:
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


def test_exact_empty_lease_rejects_remote_creation_between_observation_and_push(tmp_path: Path) -> None:
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


def test_exact_lease_rejects_remote_deletion_between_observation_and_push(tmp_path: Path) -> None:
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

    with (
        patch.object(publisher, "_push_exact_head", side_effect=delete_then_push),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(
                change_id="deleted-change",
                expected_remote_head=initial,
                operation_id="operation-delete-race",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert exc_info.value.retry_safe is True
    assert _git(remote, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 1
    assert _head(repository, f"refs/heads/{branch}") == reviewed


def test_replay_does_not_bypass_active_writer_ownership(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    worktree, reviewed = _reviewed_change(manager, "replay-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    request = PublishChangeBranch(
        change_id="replay-change",
        expected_remote_head=None,
        operation_id="operation-replay",
    )
    publisher.publish(request)
    advanced_target = _git(
        repository,
        "commit-tree",
        _git(repository, "mktree").stdout.strip(),
        "-p",
        initial,
        "-m",
        "advanced target",
    ).stdout.strip()
    _git(repository, "push", "origin", f"{advanced_target}:refs/heads/main")
    (worktree / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    coordinator.acquire("replay-change", _writer("replay-change"))

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(request)

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert _head(repository, "refs/heads/owlbear/change/replay-change") == reviewed


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


def test_replay_rejects_changed_inputs_for_same_operation_id(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "drift-change")
    publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=tmp_path / "operations",
    )
    publisher.publish(
        PublishChangeBranch(change_id="drift-change", expected_remote_head=None, operation_id="operation-drift")
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(
            PublishChangeBranch(
                change_id="drift-change",
                expected_remote_head=reviewed,
                operation_id="operation-drift",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert exc_info.value.retry_safe is False


def test_first_attempt_fetches_target_once_and_excludes_writer_until_push_completes(tmp_path: Path) -> None:
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
    original_fetch = publisher._fetch_target
    original_push = publisher._push_exact_head
    fetch_count = 0

    def counted_fetch(request: PublishChangeBranch) -> str:
        nonlocal fetch_count
        fetch_count += 1
        return original_fetch(request)

    def assert_reserved_then_push(operation: Any, request: PublishChangeBranch, attempt: Any) -> None:
        with pytest.raises(CoordinationConflictError, match="active writer"):
            coordinator.acquire("reserved-change", _writer("reserved-change"))
        original_push(operation, request, attempt)

    with (
        patch.object(publisher, "_fetch_target", side_effect=counted_fetch),
        patch.object(publisher, "_push_exact_head", side_effect=assert_reserved_then_push),
    ):
        publisher.publish(
            PublishChangeBranch(
                change_id="reserved-change",
                expected_remote_head=None,
                operation_id="operation-reserved",
            )
        )

    assert fetch_count == 1
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
        patch.object(publisher, "_fetch_target", side_effect=subprocess.TimeoutExpired(("git", "fetch"), 30)),
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
        patch.object(publisher, "_fetch_target", side_effect=RuntimeError("unexpected")),
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
    assert later_operations == ["rev-parse"]
