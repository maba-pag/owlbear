from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from owlbear_kanban.change_workspace import (
    ChangeWorkspaceManager,
    ChangeCoordination,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    PortfolioDispatcher,
    WriterIdentity,
)
from owlbear_kanban.target_authority import Outcome, PlanScopeKind, TargetAuthority, TaskPlanScope
from owlbear_kanban.target_runtime import TargetJob, TargetRuntime


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


def test_portfolio_grants_independent_changes_but_rejects_second_writer(tmp_path: Path) -> None:
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    coordinator.register(_coordination(tmp_path, "change-a"))
    coordinator.register(_coordination(tmp_path, "change-b"))
    dispatcher = PortfolioDispatcher(coordinator)

    grants = dispatcher.dispatch(
        {
            "change-a": _runtime(tmp_path / "runtime", "change-a", 1),
            "change-b": _runtime(tmp_path / "runtime", "change-b", 2),
        },
        {"change-a": _identity("change-a"), "change-b": _identity("change-b")},
    )

    assert tuple(grant.coordination.change_id for grant in grants) == ("change-a", "change-b")
    assert all(grant.coordination.writer is not None for grant in grants)
    with pytest.raises(CoordinationConflictError, match="active writer"):
        coordinator.acquire(
            "change-a",
            ChangeWriter(**_identity("change-a").model_dump(), job_id=3, kind="build"),
        )


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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
    return repository, initial


def _manager(tmp_path: Path, repository: Path, *, target: str = "release"):
    coordinator = PortfolioCoordinator(tmp_path / "state", capacity=2)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, target)
    return coordinator, manager


def _commit_file(worktree: Path, content: str, message: str) -> str:
    (worktree / "shared.txt").write_text(content, encoding="utf-8")
    _git(worktree, "add", "shared.txt")
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def test_restart_preserves_rejected_head_and_returns_to_reviewed_commit(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("restart-change")
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


def test_integration_uses_merge_commit_and_configured_target_cas(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path, target="release")
    _coordinator, manager = _manager(tmp_path, repository, target="release")
    coordination = manager.create("merge-change")
    reviewed = _commit_file(coordination.worktree_path, "reviewed\n", "reviewed task")
    manager.record_reviewed("merge-change", reviewed)

    result = manager.integrate("merge-change", (reviewed,))

    assert result.finding is None
    assert result.merge_commit is not None
    assert _git(repository, "rev-parse", "release") == result.merge_commit
    assert _git(repository, "rev-parse", "main") == initial
    assert len(_git(repository, "rev-list", "--parents", "-n", "1", result.merge_commit).split()) == 3
    _git(repository, "merge-base", "--is-ancestor", reviewed, result.merge_commit)
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == result.merge_commit


def test_integration_conflict_emits_finding_without_advancing_target(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("conflict-change")
    reviewed = _commit_file(coordination.worktree_path, "change\n", "change side")
    manager.record_reviewed("conflict-change", reviewed)
    target_worktree = tmp_path / "target-worktree"
    _git(repository, "worktree", "add", str(target_worktree), "release")
    target_head = _commit_file(target_worktree, "target\n", "target side")
    _git(repository, "worktree", "remove", str(target_worktree))

    result = manager.integrate("conflict-change", (reviewed,))

    assert result.merge_commit is None
    assert result.finding is not None
    assert result.finding.detail.startswith("Change and integration target conflict")
    assert _git(repository, "rev-parse", "release") == target_head
    finding_path = tmp_path / "state/target-runtime/integration-findings" / f"{result.finding.finding_id}.json"
    assert finding_path.is_file()

    authority = TargetAuthority(
        change_id="conflict-change",
        title="Conflict change",
        task_plan_scopes=(
            TaskPlanScope(
                scope_id="PLAN-001",
                kind=PlanScopeKind.CHANGE_ASSEMBLY,
                target_id="conflict-change",
                composition_claim="The conflicting pieces work together after resolution.",
            ),
        ),
    )
    runtime = TargetRuntime(authority, tmp_path / "assembly-runtime")
    runtime.materialize(
        (
            TargetJob(
                job_id=3,
                kind="assembly",
                change_id="conflict-change",
                authority_digest=runtime.authority_digest,
                work_item_id="conflict-change",
                plan_scope_id="PLAN-001",
                created_at="2026-08-02T00:00:03Z",
            ),
        )
    )

    grants = PortfolioDispatcher(coordinator).dispatch(
        {"conflict-change": runtime},
        {"conflict-change": _identity("conflict-change")},
    )

    assert len(grants) == 1
    assert grants[0].job.kind == "assembly"
