from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_delivery import (
    ChangeBranchPublisher,
    ChangePublicationError,
    ChangePublicationFailureCode,
    ChangeWorkspaceManager,
    PortfolioCoordinator,
    PublishChangeBranch,
)


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
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


def test_publishes_and_replays_exact_change_branch_without_mutating_target_or_user_checkout(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "publish-change")
    publisher = ChangeBranchPublisher(repository, coordinator, remote="origin", target_branch="main")
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
    publisher = ChangeBranchPublisher(repository, coordinator, remote="origin", target_branch="main")

    with pytest.raises(ChangePublicationError) as exc_info:
        publisher.publish(
            PublishChangeBranch(
                change_id="diverged-change",
                expected_remote_head=divergent,
                operation_id="operation-2",
            )
        )

    assert exc_info.value.code is ChangePublicationFailureCode.CONFLICT
    assert _head(remote, "refs/heads/owlbear/change/diverged-change") == divergent


def test_exact_lease_rejects_remote_advance_between_observation_and_push(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    coordinator, manager = _change_workspace(tmp_path, repository)
    _worktree, reviewed = _reviewed_change(manager, "raced-change")
    publisher = ChangeBranchPublisher(repository, coordinator, remote="origin", target_branch="main")
    original_push = publisher._push_exact_head
    competing = _git(
        repository, "commit-tree", _git(repository, "mktree").stdout.strip(), "-m", "competing"
    ).stdout.strip()

    def advance_then_push(
        branch: str, head: str, expected_remote_head: str | None, request: PublishChangeBranch
    ) -> None:
        _git(repository, "push", "origin", f"{competing}:refs/heads/{branch}")
        original_push(branch, head, expected_remote_head, request)

    with (
        patch.object(publisher, "_push_exact_head", side_effect=advance_then_push),
        pytest.raises(ChangePublicationError) as exc_info,
    ):
        publisher.publish(
            PublishChangeBranch(change_id="raced-change", expected_remote_head=None, operation_id="operation-3")
        )

    assert exc_info.value.code is ChangePublicationFailureCode.RESPONSE_UNKNOWN
    assert exc_info.value.retry_safe is False
    assert _head(remote, "refs/heads/owlbear/change/raced-change") == competing
    assert _head(repository, "refs/heads/owlbear/change/raced-change") == reviewed
