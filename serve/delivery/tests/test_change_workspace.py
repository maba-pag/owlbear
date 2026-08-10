from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch

import pytest

from owlbear_delivery.change_workspace import (
    CapacityLedger,
    ChangeWorkspaceManager,
    ChangeCoordination,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    WriterIdentity,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationCandidate,
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


def _commit_new_file(worktree: Path, name: str, content: str, message: str) -> str:
    (worktree / name).write_text(content, encoding="utf-8")
    _git(worktree, "add", name)
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def test_external_completion_proposal_preserves_dirty_checked_out_target(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("externally-merged")
    reviewed = _commit_new_file(coordination.worktree_path, "product.txt", "reviewed\n", "reviewed product")
    manager.record_reviewed(coordination.change_id, reviewed)
    _git(repository, "checkout", "release")
    _git(repository, "merge", "--ff-only", reviewed)
    target_head = _git(repository, "rev-parse", "release")
    (repository / "shared.txt").write_text("user work\n", encoding="utf-8")
    empty_tree = _git(repository, "mktree")
    candidate = DeliveryIntegrationCandidate(
        candidate_id="1" * 64,
        completion_id="2" * 64,
        change_id=coordination.change_id,
        package_id="3" * 64,
        authority_digest="4" * 64,
        runtime_digest="5" * 64,
        result_history_digest="6" * 64,
        reviewed_change_head=reviewed,
        integration_target="release",
        target_head=target_head,
        completion_path=".owlbear/completed/externally-merged",
        package_tree=empty_tree,
    )

    proposal = manager.prepare_external_completion_proposal(candidate)

    assert proposal.proposal_commit != target_head
    assert _git(repository, "rev-list", "--parents", "-n", "1", proposal.proposal_commit).split() == [
        proposal.proposal_commit,
        target_head,
    ]
    assert _git(repository, "rev-parse", "release") == target_head
    assert _git(repository, "rev-parse", "HEAD") == target_head
    assert (repository / "shared.txt").read_text(encoding="utf-8") == "user work\n"
    assert _git(repository, "status", "--porcelain") == "M shared.txt"


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
    ledger_path = state_root / "target-runtime/capacity.json"
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
    ledger_path = state_root / "target-runtime/capacity.json"
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


def test_restart_recovers_after_git_succeeds_before_writer_release(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("recover-restart")
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
    coordination = manager.create(f"restart-{interruption}")
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
    coordination = manager.create(f"restart-missing-{interruption}")
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
    merge_record = _git(repository, "rev-list", "--parents", "-n", "1", result.merge_commit).split()
    assert merge_record == [result.merge_commit, reviewed, initial]
    _git(repository, "merge-base", "--is-ancestor", reviewed, result.merge_commit)
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == result.merge_commit


def test_integration_retry_recovers_after_target_cas_before_coordination_update(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("recover-integration")
    reviewed = _commit_file(coordination.worktree_path, "reviewed\n", "reviewed task")
    manager.record_reviewed("recover-integration", reviewed)

    with (
        patch.object(coordinator, "update", side_effect=CoordinationConflictError("injected")),
        pytest.raises(CoordinationConflictError, match="injected"),
    ):
        manager.integrate("recover-integration", (reviewed,))

    target_after_interruption = _git(repository, "rev-parse", "release")
    recovered = manager.integrate("recover-integration", (reviewed,))

    assert recovered.merge_commit == target_after_interruption
    assert coordinator.show("recover-integration").target_head == target_after_interruption
    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == target_after_interruption


def test_integration_serializes_independent_managers(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator_a, manager_a = _manager(tmp_path, repository)
    coordinator_b = PortfolioCoordinator(tmp_path / "state", capacity=2)
    manager_b = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator_b, "release")
    coordination_a = manager_a.create("parallel-a")
    coordination_b = manager_b.create("parallel-b")
    reviewed_a = _commit_new_file(coordination_a.worktree_path, "a.txt", "a\n", "change a")
    reviewed_b = _commit_new_file(coordination_b.worktree_path, "b.txt", "b\n", "change b")
    manager_a.record_reviewed("parallel-a", reviewed_a)
    manager_b.record_reviewed("parallel-b", reviewed_b)
    first_entered = Event()
    release_first = Event()
    second_entered = Event()
    original_a = manager_a._integrate_locked
    original_b = manager_b._integrate_locked

    def hold_first(change_id: str, reviewed: tuple[str, ...]):
        first_entered.set()
        assert release_first.wait(timeout=2)
        return original_a(change_id, reviewed)

    def mark_second(change_id: str, reviewed: tuple[str, ...]):
        second_entered.set()
        return original_b(change_id, reviewed)

    with (
        patch.object(manager_a, "_integrate_locked", side_effect=hold_first),
        patch.object(manager_b, "_integrate_locked", side_effect=mark_second),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        first = executor.submit(manager_a.integrate, "parallel-a", (reviewed_a,))
        assert first_entered.wait(timeout=2)
        second = executor.submit(manager_b.integrate, "parallel-b", (reviewed_b,))
        assert not second_entered.wait(timeout=0.1)
        release_first.set()
        result_a = first.result(timeout=2)
        result_b = second.result(timeout=2)

    assert result_a.merge_commit is not None
    assert result_b.merge_commit == _git(repository, "rev-parse", "release")
    _git(repository, "merge-base", "--is-ancestor", reviewed_a, result_b.merge_commit)
    _git(repository, "merge-base", "--is-ancestor", reviewed_b, result_b.merge_commit)


def test_integration_reports_typed_target_cas_loss_and_retries(tmp_path: Path) -> None:
    repository, initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("cas-loss")
    reviewed = _commit_file(coordination.worktree_path, "reviewed\n", "reviewed task")
    manager.record_reviewed("cas-loss", reviewed)
    original_git = manager._git

    def reject_target_cas(*arguments: str, **kwargs) -> str:
        if arguments[:2] == ("update-ref", "refs/heads/release"):
            raise subprocess.CalledProcessError(1, arguments)
        return original_git(*arguments, **kwargs)

    with (
        patch.object(manager, "_git", side_effect=reject_target_cas),
        pytest.raises(CoordinationConflictError, match="target changed concurrently"),
    ):
        manager.integrate("cas-loss", (reviewed,))

    assert _git(repository, "rev-parse", "release") == initial
    recovered = manager.integrate("cas-loss", (reviewed,))
    assert recovered.merge_commit == _git(repository, "rev-parse", "release")


def test_integration_conflict_emits_finding_without_advancing_target(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    _coordinator, manager = _manager(tmp_path, repository)
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

    assert runtime.list_frontier()[0].kind == "assembly"


def test_repair_candidate_commits_conflict_paths_and_replays(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("repair-candidate")
    source_head = _commit_file(coordination.worktree_path, "change\n", "change side")
    manager.record_reviewed(coordination.change_id, source_head)
    target_worktree = tmp_path / "target-worktree"
    _git(repository, "worktree", "add", str(target_worktree), "release")
    target_head = _commit_file(target_worktree, "target\n", "target side")
    _git(repository, "worktree", "remove", str(target_worktree))
    manager.refresh_integration_target(coordination.change_id)
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="repair")
    coordinator.acquire(coordination.change_id, writer)
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id=coordination.change_id,
        change_head=source_head,
        target_head=target_head,
        integration_target="release",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed repair.",
    )
    (coordination.worktree_path / "shared.txt").write_text("target\n", encoding="utf-8")

    candidate = manager.create_integration_repair_candidate(attention, writer)
    replayed = manager.create_integration_repair_candidate(attention, writer)

    assert candidate == replayed
    assert candidate.changed_paths == ("shared.txt",)
    assert _git(repository, "rev-list", "--parents", "-n", "1", candidate.candidate_commit).split() == [
        candidate.candidate_commit,
        source_head,
        target_head,
    ]
    assert candidate.merged_tree == _git(repository, "rev-parse", f"{candidate.candidate_commit}^{{tree}}")
    assert _git(coordination.worktree_path, "status", "--porcelain") == ""
    assert _git(repository, "rev-parse", "release") == target_head


def test_repair_candidate_combines_same_line_resolution_and_target_content(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("repair-combined-line")
    source_head = _commit_file(coordination.worktree_path, "tools: [old, register]\n", "source tools")
    manager.record_reviewed(coordination.change_id, source_head)
    target_worktree = tmp_path / "target-worktree"
    _git(repository, "worktree", "add", str(target_worktree), "release")
    (target_worktree / "shared.txt").write_text("tools: [renamed]\n", encoding="utf-8")
    (target_worktree / "target-only.txt").write_text("target\n", encoding="utf-8")
    _git(target_worktree, "add", "shared.txt", "target-only.txt")
    _git(target_worktree, "commit", "-m", "rename tools")
    target_head = _git(repository, "rev-parse", "release")
    _git(repository, "worktree", "remove", str(target_worktree))
    manager.refresh_integration_target(coordination.change_id)
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="repair")
    coordinator.acquire(coordination.change_id, writer)
    attention = DeliveryIntegrationAttention(
        attention_id="e" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id=coordination.change_id,
        change_head=source_head,
        target_head=target_head,
        integration_target="release",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed repair.",
    )
    (coordination.worktree_path / "shared.txt").write_text(
        "tools: [renamed, register]\n",
        encoding="utf-8",
    )

    candidate = manager.create_integration_repair_candidate(attention, writer)

    assert _git(repository, "show", f"{candidate.candidate_commit}:shared.txt") == "tools: [renamed, register]"
    assert _git(repository, "show", f"{candidate.candidate_commit}:target-only.txt") == "target"


@pytest.mark.parametrize("interruption", ["candidate-commit", "branch-cas", "worktree-reset"])
def test_repair_candidate_replays_after_git_interruption(tmp_path: Path, interruption: str) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create(f"repair-candidate-{interruption}")
    source_head = _commit_file(coordination.worktree_path, "change\n", "change side")
    manager.record_reviewed(coordination.change_id, source_head)
    target_worktree = tmp_path / "target-worktree"
    _git(repository, "worktree", "add", str(target_worktree), "release")
    target_head = _commit_file(target_worktree, "target\n", "target side")
    _git(repository, "worktree", "remove", str(target_worktree))
    manager.refresh_integration_target(coordination.change_id)
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="repair")
    coordinator.acquire(coordination.change_id, writer)
    attention = DeliveryIntegrationAttention(
        attention_id="c" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id=coordination.change_id,
        change_head=source_head,
        target_head=target_head,
        integration_target="release",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed repair.",
    )
    (coordination.worktree_path / "shared.txt").write_text("target\n", encoding="utf-8")
    original_git = manager._git

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        checks = {
            "candidate-commit": arguments[:1] == ("commit-tree",),
            "branch-cas": arguments[:2] == ("update-ref", f"refs/heads/{coordination.branch}"),
            "worktree-reset": arguments[:2] == ("reset", "--hard"),
        }
        if checks[interruption]:
            message = "injected"
            raise RuntimeError(message)
        return result

    with patch.object(manager, "_git", side_effect=interrupt_after_git), pytest.raises(RuntimeError, match="injected"):
        manager.create_integration_repair_candidate(attention, writer)

    candidate = manager.create_integration_repair_candidate(attention, writer)

    assert _git(repository, "rev-parse", coordination.branch) == candidate.candidate_commit
    assert _git(coordination.worktree_path, "status", "--porcelain") == ""


def test_repair_candidate_rejects_changes_outside_conflict_paths(tmp_path: Path) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create("repair-candidate-scope")
    source_head = _commit_file(coordination.worktree_path, "change\n", "change side")
    manager.record_reviewed(coordination.change_id, source_head)
    target_worktree = tmp_path / "target-worktree"
    _git(repository, "worktree", "add", str(target_worktree), "release")
    target_head = _commit_file(target_worktree, "target\n", "target side")
    _git(repository, "worktree", "remove", str(target_worktree))
    manager.refresh_integration_target(coordination.change_id)
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="repair")
    coordinator.acquire(coordination.change_id, writer)
    attention = DeliveryIntegrationAttention(
        attention_id="b" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id=coordination.change_id,
        change_head=source_head,
        target_head=target_head,
        integration_target="release",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed repair.",
    )
    (coordination.worktree_path / "outside.txt").write_text("outside\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="only original conflict paths"):
        manager.create_integration_repair_candidate(attention, writer)

    assert _git(repository, "rev-parse", coordination.branch) == source_head


@pytest.mark.parametrize("guard", ["writer", "attention"])
def test_repair_candidate_rejects_stale_authority_before_git_mutation(tmp_path: Path, guard: str) -> None:
    repository, _initial = _repository(tmp_path)
    coordinator, manager = _manager(tmp_path, repository)
    coordination = manager.create(f"repair-candidate-{guard}")
    source_head = _commit_file(coordination.worktree_path, "change\n", "change side")
    manager.record_reviewed(coordination.change_id, source_head)
    target_worktree = tmp_path / "target-worktree"
    _git(repository, "worktree", "add", str(target_worktree), "release")
    target_head = _commit_file(target_worktree, "target\n", "target side")
    _git(repository, "worktree", "remove", str(target_worktree))
    manager.refresh_integration_target(coordination.change_id)
    writer = ChangeWriter(**_identity(coordination.change_id).model_dump(), job_id=1, kind="repair")
    coordinator.acquire(coordination.change_id, writer)
    attention = DeliveryIntegrationAttention(
        attention_id="d" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id=coordination.change_id,
        change_head=source_head,
        target_head=target_head,
        integration_target="release",
        diagnostics=("conflict",),
        retry_condition="Admit a reviewed repair.",
    )
    (coordination.worktree_path / "shared.txt").write_text("target\n", encoding="utf-8")
    supplied_writer = writer.model_copy(update={"actor_id": "another-builder"}) if guard == "writer" else writer
    supplied_attention = (
        attention.model_copy(update={"target_head": source_head}) if guard == "attention" else attention
    )
    expected = "exact repair writer custody" if guard == "writer" else "current attention"

    with pytest.raises(RuntimeError, match=expected):
        manager.create_integration_repair_candidate(supplied_attention, supplied_writer)

    assert _git(repository, "rev-parse", coordination.branch) == source_head
    assert _git(coordination.worktree_path, "status", "--porcelain") == "M shared.txt"
