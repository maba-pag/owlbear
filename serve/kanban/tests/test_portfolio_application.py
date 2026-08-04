from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import (
    CapacityLedger,
    ChangeWorkspaceManager,
    ChangeWriter,
    CoordinationConflictError,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryClaimRecoveryStatus,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationCandidate,
    DeliveryIntegrationRepair,
    DeliveryIntegrationRepairReview,
    DeliveryOutcome,
    DeliveryPlanScope,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    DesignPackageManifest,
    DesignPackageStore,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationHooks,
    PortfolioCoordinator,
    RetryDelivery,
)
from owlbear_kanban.runtime_transaction import RuntimeTransaction


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _canonical(model) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _contract(change_id: str, intent: bytes, design: bytes) -> DeliveryContract:
    return DeliveryContract(
        change_id=change_id,
        title=f"Delivery {change_id}",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="accepted design",
                statement="Keep acquisition deterministic.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="Acquire work",
                promise="Return one bounded launch package.",
                acceptance=("The launch is observable.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            {"source_name": "intent.md", "sha256": hashlib.sha256(intent).hexdigest()},
            {"source_name": "design.md", "sha256": hashlib.sha256(design).hexdigest()},
        ),
    )


def _task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Implement acquisition",
        result="One transport-free acquisition service.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Bounded launch package",),
        maintained_surfaces=("serve/kanban/src/owlbear_kanban/portfolio_application.py",),
        constraints=("Separate execution and writer capacity.",),
        exclusions=("Do not expose portfolio inventory.",),
        acceptance_observations=("The public acquisition result names the active claim.",),
        proof_boundaries=("PortfolioApplication.acquire_frontier_work",),
    )


def _runtime(
    state_root: Path,
    contract: DeliveryContract,
    manager: ChangeWorkspaceManager,
    stage: DeliveryStage,
    completed_commit: str,
) -> DeliveryRuntime:
    task = _task()
    authority_digest = hashlib.sha256(_canonical(contract)).hexdigest()
    has_task = stage in {DeliveryStage.IMPLEMENTATION, DeliveryStage.ASSEMBLY, DeliveryStage.COMPLETED}
    has_result = stage in {DeliveryStage.ASSEMBLY, DeliveryStage.COMPLETED}
    result = DeliveryTaskResult(
        result_id="RESULT-001",
        change_id=contract.change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=stage,
                assembly_required=stage == DeliveryStage.ASSEMBLY,
                tasks=(task,) if has_task else (),
                results=(result,) if has_result else (),
            ),
        )
    )
    path = state_root / "delivery" / "changes" / contract.change_id / "frontier.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(_canonical(frontier))
    return DeliveryRuntime(state_root, contract, workspace_manager=manager)


def _policies() -> tuple[DeliveryRolePolicy, ...]:
    return (
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.PLANNER,
            worker_agent="planner",
            worker_model="planning-model",
            reviewer_agent="planner-challenger",
            reviewer_model="review-model",
        ),
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.BUILDER,
            worker_agent="builder",
            worker_model="build-model",
            reviewer_agent="build-reviewer",
            reviewer_model="review-model",
        ),
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.ASSEMBLY_REVIEWER,
            worker_agent="build-reviewer",
            worker_model="review-model",
        ),
    )


def _portfolio(
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    *,
    writer_capacity: int = 1,
    candidate_proof: Callable[[DeliveryIntegrationCandidate, str], tuple[str, ...]] | None = None,
):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Portfolio Test")
    _git(repository, "config", "user.email", "portfolio@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    state_root = tmp_path / "state"
    package_root = tmp_path / "packages"
    coordinator = PortfolioCoordinator(state_root, capacity=writer_capacity)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    store = DesignPackageStore(package_root, repository)
    runtimes = {}
    for change_id, stage in stages.items():
        intent = f"intent prose sentinel {change_id}\n".encode()
        design = f"design prose sentinel {change_id}\n".encode()
        contract = _contract(change_id, intent, design)
        package = store.create(change_id, intent, design)
        store.publish_contract(change_id, package.package_id, _canonical(contract), lambda *_content: None)
        coordination = manager.create(change_id)
        runtimes[change_id] = _runtime(state_root, contract, manager, stage, coordination.last_reviewed_commit)
    identities = (f"identity-{index:03}" for index in itertools.count(1))
    application = PortfolioApplication(
        dict(reversed(tuple(runtimes.items()))),
        PortfolioApplicationDependencies(
            store,
            coordinator,
            manager,
            candidate_proof or (lambda _candidate, _commit: ("candidate proof dependency is not configured",)),
        ),
        PortfolioApplicationConfig(
            package_root=package_root,
            execution_capacity=3,
            role_policies=_policies(),
        ),
        PortfolioApplicationHooks(
            identity_factory=lambda: next(identities),
            clock=lambda: "2026-08-04T00:00:00Z",
        ),
    )
    return application, runtimes, coordinator, state_root


def _review_product_change(coordinator: PortfolioCoordinator, change_id: str, content: str) -> tuple[str, str]:
    coordination = coordinator.show(change_id)
    target_head = _git(coordination.worktree_path, "rev-parse", coordination.integration_target)
    (coordination.worktree_path / "product.txt").write_text(content, encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", f"reviewed {change_id}")
    reviewed = _git(coordination.worktree_path, "rev-parse", "HEAD")
    coordinator.update(coordination.model_copy(update={"last_reviewed_commit": reviewed}))
    return target_head, reviewed


def _prepare_reviewed_integration_repair(tmp_path: Path):
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    target_head = _git(repository, "rev-parse", "main")
    failed = application.integrate_ready_change("change-a")
    assert failed.attention is not None
    worktree = coordinator.show("change-a").worktree_path
    (worktree / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "resolve Integration conflict")
    repair_commit = _git(worktree, "rev-parse", "HEAD")
    repair = DeliveryIntegrationRepair(
        attention_id=failed.attention.attention_id,
        change_id="change-a",
        integration_target="main",
        prior_change_head=reviewed,
        prior_target_head=target_head,
        reviewed_repair_commit=repair_commit,
        owner_id="repair-builder",
        review=DeliveryIntegrationRepairReview(
            review_id="repair-review-001",
            reviewer_id="independent-reviewer",
            candidate_commit=repair_commit,
        ),
    )
    return application, runtimes, coordinator, state_root, repair


def _with_reviewed_commit(repair: DeliveryIntegrationRepair, commit: str) -> DeliveryIntegrationRepair:
    return repair.model_copy(
        update={
            "reviewed_repair_commit": commit,
            "review": repair.review.model_copy(update={"candidate_commit": commit}),
        }
    )


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _invalid_integration_repair(
    invalid_case: str,
    repair: DeliveryIntegrationRepair,
    worktree: Path,
) -> DeliveryIntegrationRepair:
    identity_updates = {
        "stale-attention": {"attention_id": "0" * 64},
        "change-identity": {"change_id": "change-b"},
        "target-identity": {"integration_target": "other-target"},
        "stale-change-head": {"prior_change_head": "0" * 40},
        "stale-target-head": {"prior_target_head": "0" * 40},
    }
    if invalid_case in identity_updates:
        return repair.model_copy(update=identity_updates[invalid_case])
    if invalid_case == "multi-commit":
        (worktree / "second.txt").write_text("second\n", encoding="utf-8")
        _git(worktree, "add", "second.txt")
        _git(worktree, "commit", "-m", "second repair commit")
        return _with_reviewed_commit(repair, _git(worktree, "rev-parse", "HEAD"))
    if invalid_case == "non-child":
        _git(worktree, "reset", "--hard", repair.prior_target_head)
        (worktree / "non-child.txt").write_text("non-child\n", encoding="utf-8")
        _git(worktree, "add", "non-child.txt")
        _git(worktree, "commit", "-m", "unrelated repair ancestry")
        return _with_reviewed_commit(repair, _git(worktree, "rev-parse", "HEAD"))
    if invalid_case == "dirty-worktree":
        (worktree / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    elif invalid_case == "detached-worktree":
        _git(worktree, "checkout", "--detach", repair.reviewed_repair_commit)
    elif invalid_case == "branch-head-mismatch":
        (worktree / "later.txt").write_text("later\n", encoding="utf-8")
        _git(worktree, "add", "later.txt")
        _git(worktree, "commit", "-m", "move branch after review")
    elif invalid_case in {"completed-history", "non-conflict-path"}:
        _git(worktree, "reset", "--hard", repair.prior_change_head)
        (worktree / "product.txt").write_text("target side\n", encoding="utf-8")
        extra = (
            worktree / ".owlbear/completed/change-z/results.json"
            if invalid_case == "completed-history"
            else worktree / "unrelated.txt"
        )
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("changed\n", encoding="utf-8")
        _git(worktree, "add", "product.txt", str(extra))
        _git(worktree, "commit", "-m", f"invalid {invalid_case} repair")
        return _with_reviewed_commit(repair, _git(worktree, "rev-parse", "HEAD"))
    return repair


def test_acquisition_returns_bounded_stage_packages_and_unclaimed_integration(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-d": DeliveryStage.COMPLETED,
            "change-c": DeliveryStage.ASSEMBLY,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-a": DeliveryStage.PLANNING,
        },
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == (
        "change-a",
        "change-b",
        "change-c",
    )
    assert tuple(package.claim.worker_role for package in acquired.launch_packages) == tuple(DeliveryWorkerRole)
    assert acquired.integration_ready_change_ids == ("change-d",)
    assert acquired.failures == ()
    assert runtimes["change-d"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-b").writer is not None
    assert coordinator.show("change-c").writer is None
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ("change-b",)

    plan_package, build_package, assembly_package = acquired.launch_packages
    plan_context = application.show_plan_context(
        plan_package.change_id,
        plan_package.outcome_id,
        plan_package.claim.attempt_id,
        plan_package.claim.claim_id,
    )
    build_context = application.show_build_context(
        build_package.change_id,
        build_package.outcome_id,
        build_package.claim.attempt_id,
        build_package.claim.claim_id,
    )
    assert plan_context.outcome.outcome_id == "OUT-001"
    assert build_context.task.task_id == "TASK-001"
    assert assembly_package.writer is None
    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        application.show_plan_context(
            plan_package.change_id,
            plan_package.outcome_id,
            "stale-attempt",
            plan_package.claim.claim_id,
        )
    serialized = "".join(json.dumps(model.model_dump(mode="json")) for model in (acquired, plan_context, build_context))
    for residue in ("intent prose sentinel", "design prose sentinel", '"reviews"', '"receipts"'):
        assert residue not in serialized.lower()


def test_writer_failure_leaves_started_exact_claim_without_false_launch(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.PLANNING,
        },
    )
    (tmp_path / "packages/change-b/intent.md").write_text("mutated source\n", encoding="utf-8")

    with patch.object(coordinator, "acquire", side_effect=CoordinationConflictError("injected writer failure")):
        acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert len(acquired.failures) == 2
    failure = acquired.failures[0]
    active = runtimes["change-a"].active_claims()
    assert active[0][1].attempt_id == failure.attempt_id
    assert active[0][1].claim_id == failure.claim_id
    assert runtimes["change-b"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    recovered = application.recover_claim(
        "change-a",
        "OUT-001",
        failure.attempt_id,
        failure.claim_id,
    )
    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert runtimes["change-a"].active_claims() == ()
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ()


def test_writer_capacity_skips_blocked_build_but_launches_read_only_work(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.PLANNING,
        },
        writer_capacity=1,
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == ("change-a", "change-c")
    assert acquired.failures == ()
    assert runtimes["change-b"].active_claims() == ()
    assert coordinator.show("change-b").writer is None
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING, DeliveryStage.ASSEMBLY])
def test_read_only_claim_recovery_removes_only_exact_runtime_claim(tmp_path: Path, stage: DeliveryStage) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": stage})
    package = application.acquire_frontier_work().launch_packages[0]

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.preserved_commit is None
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ()


def test_clean_build_recovery_replays_after_workspace_reset(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    worktree = package.worktree_path
    (worktree / "product.txt").write_text("attempt\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "attempt commit")
    attempt_commit = _git(worktree, "rev-parse", "HEAD")

    with (
        patch.object(runtimes["change-a"], "remove_active_claim", side_effect=RuntimeError("injected after reset")),
        pytest.raises(RuntimeError, match="injected"),
    ):
        application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    assert _git(worktree, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert coordinator.show("change-a").writer is None
    assert (
        _git(
            worktree,
            "rev-parse",
            f"refs/owlbear/attempts/change-a/{package.claim.attempt_id}",
        )
        == attempt_commit
    )

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.preserved_commit == attempt_commit
    assert runtimes["change-a"].active_claims() == ()
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ()
    with pytest.raises(DeliveryRuntimeConflictError, match="active claim"):
        runtimes["change-a"].transition(RetryDelivery(outcome_id="OUT-001", claim_id=package.claim.claim_id))


@pytest.mark.parametrize("interruption", ["attempt-ref", "worktree-remove", "branch-reset", "worktree-add"])
def test_clean_build_recovery_replays_each_workspace_interruption(tmp_path: Path, interruption: str) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    product = package.worktree_path / "product.txt"
    product.write_text("attempt\n", encoding="utf-8")
    _git(package.worktree_path, "add", "product.txt")
    _git(package.worktree_path, "commit", "-m", "attempt commit")
    rejected = _git(package.worktree_path, "rev-parse", "HEAD")
    manager = application._workspace_manager
    original_git = manager._git

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        checks = {
            "attempt-ref": arguments[:2]
            == ("update-ref", f"refs/owlbear/attempts/change-a/{package.claim.attempt_id}"),
            "worktree-remove": arguments[:2] == ("worktree", "remove"),
            "branch-reset": arguments[:2] == ("update-ref", f"refs/heads/{package.branch}"),
            "worktree-add": arguments[:2] == ("worktree", "add"),
        }
        if checks[interruption]:
            message = "injected workspace interruption"
            raise RuntimeError(message)
        return result

    with (
        patch.object(manager, "_git", side_effect=interrupt_after_git),
        pytest.raises(RuntimeError, match="injected workspace interruption"),
    ):
        application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.preserved_commit == rejected
    assert _git(package.worktree_path, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ()


def test_dirty_build_recovery_retains_bytes_claim_custody_and_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    product = package.worktree_path / "product.txt"
    product.write_text("uncommitted attempt\n", encoding="utf-8")
    branch_head = _git(package.worktree_path, "rev-parse", "HEAD")

    retained = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert retained.status == DeliveryClaimRecoveryStatus.ATTENTION
    assert retained.attention is not None
    assert retained.attention.custody_retained
    assert retained.attention.branch_head == branch_head
    assert product.read_text(encoding="utf-8") == "uncommitted attempt\n"
    assert runtimes["change-a"].active_claims()[0][1] == package.claim
    assert runtimes["change-a"].show_binding("OUT-001").recovery_attention == retained.attention
    assert coordinator.show("change-a").writer == package.writer
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


def test_mismatched_build_custody_retains_current_writer_and_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    coordinator.release("change-a", package.claim.claim_id)
    mismatched = ChangeWriter(
        attempt_id="other-attempt",
        claim_id="other-claim",
        actor_id="other-owner",
        process_id="other-process",
        claimed_at="2026-08-04T00:01:00Z",
        job_id=2,
        kind="build",
    )
    coordinator.acquire("change-a", mismatched)

    retained = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert retained.status == DeliveryClaimRecoveryStatus.ATTENTION
    assert retained.attention is not None
    assert retained.attention.writer_claim_id == mismatched.claim_id
    assert runtimes["change-a"].active_claims()[0][1] == package.claim
    assert coordinator.show("change-a").writer == mismatched
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


def test_integration_publishes_product_and_package_once_then_replays_cleanup(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    target_before, reviewed = _review_product_change(coordinator, "change-a", "reviewed product\n")
    active_root = tmp_path / "packages/change-a"
    active_bytes = {path.name: path.read_bytes() for path in active_root.iterdir()}
    worktree_path = coordinator.show("change-a").worktree_path

    published = application.integrate_ready_change("change-a")

    assert published.completion is not None
    target_commit = published.completion.target_commit
    assert _git(tmp_path / "repository", "rev-parse", "main") == target_commit
    assert _git(tmp_path / "repository", "show", f"{target_commit}:product.txt") == "reviewed product"
    assert _git(tmp_path / "repository", "rev-list", "--parents", "-n", "1", target_commit).split() == [
        target_commit,
        target_before,
        reviewed,
    ]
    completion_root = ".owlbear/completed/change-a"
    completed_names = _git(
        tmp_path / "repository",
        "ls-tree",
        "--name-only",
        f"{target_commit}:{completion_root}",
    ).split()
    assert set(completed_names) == {
        "authority.json",
        "completion.json",
        "design.md",
        "intent.md",
        "manifest.json",
        "results.json",
        "runtime.json",
    }
    assert runtimes["change-a"].change_stage().value == "completed"
    assert not (tmp_path / "packages/change-a").exists()
    assert not coordinator.show("change-a").worktree_path.exists()

    active_root.mkdir()
    for name, content in active_bytes.items():
        (active_root / name).write_bytes(content)
    _git(tmp_path / "repository", "worktree", "add", str(worktree_path), coordinator.show("change-a").branch)

    replayed = application.integrate_ready_change("change-a")

    assert replayed.replayed
    assert replayed.completion == published.completion
    assert _git(tmp_path / "repository", "rev-parse", "main") == target_commit
    assert not active_root.exists()
    assert not worktree_path.exists()


def test_integration_proof_failure_retains_heads_and_publishes_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    target_before, reviewed = _review_product_change(coordinator, "change-a", "reviewed product\n")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.CANDIDATE_PROOF_FAILED
    assert failed.attention.change_head == reviewed
    assert failed.attention.target_head == target_before
    assert _git(tmp_path / "repository", "rev-parse", "main") == target_before
    assert _git(tmp_path / "repository", "rev-parse", coordinator.show("change-a").branch) == reviewed
    assert runtimes["change-a"].change_stage().value == "integration"
    assert (tmp_path / "packages/change-a").is_dir()
    assert not _git(coordinator.show("change-a").worktree_path, "status", "--porcelain")


def test_integration_target_identity_mismatch_is_typed_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")
    _git(repository, "branch", "other-target", target_head)
    coordination = coordinator.show("change-a")
    coordinator.update(coordination.model_copy(update={"integration_target": "other-target"}))

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.TARGET_IDENTITY_MISMATCH
    assert _git(repository, "rev-parse", "main") == target_head
    assert _git(repository, "rev-parse", "other-target") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"


def test_semantic_only_integration_preserves_product_and_sibling_completed_tree(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    first = application.integrate_ready_change("change-a")
    assert first.completion is not None
    first_commit = first.completion.target_commit
    product_blob = _git(repository, "rev-parse", f"{first_commit}:product.txt")
    sibling_tree = _git(repository, "rev-parse", f"{first_commit}:.owlbear/completed/change-a")

    second = application.integrate_ready_change("change-b")

    assert second.completion is not None
    second_commit = second.completion.target_commit
    assert _git(repository, "rev-parse", f"{second_commit}:product.txt") == product_blob
    assert _git(repository, "rev-parse", f"{second_commit}:.owlbear/completed/change-a") == sibling_tree
    assert _git(repository, "rev-parse", f"{second_commit}:.owlbear/completed/change-b")


def test_integration_rejects_reviewed_sibling_completed_history_mutation(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    sibling = application.integrate_ready_change("change-b")
    assert sibling.completion is not None
    target_head = sibling.completion.target_commit
    coordination = coordinator.show("change-a")
    _git(coordination.worktree_path, "reset", "--hard", target_head)
    sibling_completion = coordination.worktree_path / ".owlbear/completed/change-b/completion.json"
    sibling_completion.write_text('{"mutated":true}\n', encoding="utf-8")
    _git(coordination.worktree_path, "add", str(sibling_completion))
    _git(coordination.worktree_path, "commit", "-m", "mutate sibling completion")
    reviewed = _git(coordination.worktree_path, "rev-parse", "HEAD")
    coordinator.update(coordination.model_copy(update={"last_reviewed_commit": reviewed}))
    completed_binding = runtimes["change-a"].show_binding("OUT-001")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.COMPLETED_HISTORY_MUTATED
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].show_binding("OUT-001") == completed_binding
    assert runtimes["change-a"].change_stage().value == "integration"
    assert (tmp_path / "packages/change-a").is_dir()


def test_integration_merge_conflict_retains_clean_heads_and_typed_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    target_head = _git(repository, "rev-parse", "main")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.MERGE_CONFLICT
    assert failed.attention.change_head == reviewed
    assert failed.attention.target_head == target_head
    assert _git(repository, "rev-parse", "main") == target_head
    assert _git(repository, "rev-parse", coordinator.show("change-a").branch) == reviewed
    assert not _git(coordinator.show("change-a").worktree_path, "status", "--porcelain")
    assert runtimes["change-a"].change_stage().value == "integration"


def test_reviewed_integration_repair_advances_boundary_and_retries_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root, repair = _prepare_reviewed_integration_repair(tmp_path)
    repository = tmp_path / "repository"
    target_head = repair.prior_target_head
    repair_commit = repair.reviewed_repair_commit
    package_bytes = {path.name: path.read_bytes() for path in (tmp_path / "packages/change-a").iterdir()}
    completed_binding = runtimes["change-a"].show_binding("OUT-001")

    admitted = application.admit_reviewed_integration_repair(repair)

    assert admitted == repair
    assert coordinator.show("change-a").last_reviewed_commit == repair_commit
    assert runtimes["change-a"].integration_attention() is None
    assert runtimes["change-a"].change_stage().value == "integration"
    assert runtimes["change-a"].show_binding("OUT-001") == completed_binding
    assert _git(repository, "rev-parse", "main") == target_head
    assert {path.name: path.read_bytes() for path in (tmp_path / "packages/change-a").iterdir()} == package_bytes

    retried = application.integrate_ready_change("change-a")

    assert retried.completion is not None
    assert _git(repository, "show", f"{retried.completion.target_commit}:product.txt") == "target side"


@pytest.mark.parametrize(
    "invalid_case",
    [
        "stale-attention",
        "change-identity",
        "target-identity",
        "stale-change-head",
        "stale-target-head",
        "multi-commit",
        "non-child",
        "dirty-worktree",
        "detached-worktree",
        "branch-head-mismatch",
        "completed-history",
        "non-conflict-path",
    ],
)
def test_reviewed_integration_repair_rejection_preserves_all_state(
    tmp_path: Path,
    invalid_case: str,
) -> None:
    application, runtimes, coordinator, state_root, repair = _prepare_reviewed_integration_repair(tmp_path)
    coordination = coordinator.show("change-a")
    worktree = coordination.worktree_path
    repository = tmp_path / "repository"
    repair = _invalid_integration_repair(invalid_case, repair, worktree)

    coordination_path = state_root / "target-runtime/coordination/change-a.json"
    frontier_path = state_root / "delivery/changes/change-a/frontier.json"
    package_root = tmp_path / "packages/change-a"
    persisted_before = (coordination_path.read_bytes(), frontier_path.read_bytes())
    refs_before = (
        _git(repository, "rev-parse", "main"),
        _git(repository, "rev-parse", coordination.branch),
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain"),
    )
    package_before = _file_bytes(package_root)
    binding_before = runtimes["change-a"].show_binding("OUT-001")
    attention_before = runtimes["change-a"].integration_attention()

    with pytest.raises(RuntimeError):
        application.admit_reviewed_integration_repair(repair)

    assert (coordination_path.read_bytes(), frontier_path.read_bytes()) == persisted_before
    assert (
        _git(repository, "rev-parse", "main"),
        _git(repository, "rev-parse", coordination.branch),
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain"),
    ) == refs_before
    assert _file_bytes(package_root) == package_before
    assert runtimes["change-a"].show_binding("OUT-001") == binding_before
    assert runtimes["change-a"].integration_attention() == attention_before


@pytest.mark.parametrize("invalid_review", ["missing", "commit-mismatch", "not-independent"])
def test_integration_repair_requires_exact_independent_review_binding(invalid_review: str) -> None:
    payload = {
        "attention_id": "a" * 64,
        "change_id": "change-a",
        "integration_target": "main",
        "prior_change_head": "b" * 40,
        "prior_target_head": "c" * 40,
        "reviewed_repair_commit": "d" * 40,
        "owner_id": "repair-builder",
        "review": {
            "review_id": "review-001",
            "reviewer_id": "independent-reviewer",
            "candidate_commit": "d" * 40,
        },
    }
    if invalid_review == "missing":
        payload.pop("review")
    elif invalid_review == "commit-mismatch":
        payload["review"]["candidate_commit"] = "e" * 40
    else:
        payload["review"]["reviewer_id"] = payload["owner_id"]

    with pytest.raises(ValueError):
        DeliveryIntegrationRepair.model_validate(payload)


def test_interrupted_integration_repair_admission_converges_before_retry(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root, repair = _prepare_reviewed_integration_repair(tmp_path)
    repository = tmp_path / "repository"
    package_root = tmp_path / "packages/change-a"
    package_before = _file_bytes(package_root)
    original_commit = RuntimeTransaction.commit

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            message = "interrupted repair admission"
            raise RuntimeError(message)

    def commit_with_interruption(transaction: RuntimeTransaction) -> None:
        original_commit(transaction, failure=interrupt)

    with (
        patch.object(RuntimeTransaction, "commit", commit_with_interruption),
        pytest.raises(
            RuntimeError,
            match="interrupted repair admission",
        ),
    ):
        application.admit_reviewed_integration_repair(repair)

    assert coordinator.show("change-a").last_reviewed_commit == repair.reviewed_repair_commit
    assert runtimes["change-a"].integration_attention() is None
    assert _git(repository, "rev-parse", "main") == repair.prior_target_head
    assert _file_bytes(package_root) == package_before

    retried = application.integrate_ready_change("change-a")

    assert retried.completion is not None


def test_integration_target_cas_loss_publishes_attention_without_own_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    concurrent_head = ""

    def advance_target(_candidate: DeliveryIntegrationCandidate, _commit: str) -> tuple[str, ...]:
        nonlocal concurrent_head
        (repository / "concurrent.txt").write_text("concurrent\n", encoding="utf-8")
        _git(repository, "add", "concurrent.txt")
        _git(repository, "commit", "-m", "concurrent target")
        concurrent_head = _git(repository, "rev-parse", "HEAD")
        return ()

    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=advance_target,
    )
    target_before, reviewed = _review_product_change(coordinator, "change-a", "reviewed product\n")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.TARGET_CAS_LOST
    assert failed.attention.target_head == target_before
    assert _git(repository, "rev-parse", "main") == concurrent_head
    assert _git(repository, "rev-parse", coordinator.show("change-a").branch) == reviewed
    assert runtimes["change-a"].change_stage().value == "integration"
    assert (tmp_path / "packages/change-a").is_dir()


def test_integration_rejects_revision_pending_and_source_mutation_before_visibility(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")
    package_root = tmp_path / "packages/change-a"
    intent_bytes = (package_root / "intent.md").read_bytes()
    design_bytes = (package_root / "design.md").read_bytes()
    authority_bytes = (package_root / "authority.json").read_bytes()
    revised_authority = b'{"revision":"pending"}\n'
    (package_root / "authority.json").write_bytes(revised_authority)
    pending_manifest = DesignPackageManifest.from_content(
        "change-a",
        intent_bytes,
        design_bytes,
        revised_authority,
    )
    (package_root / "manifest.json").write_bytes(pending_manifest.canonical_bytes())

    revision_pending = application.integrate_ready_change("change-a")

    assert revision_pending.attention is not None
    assert revision_pending.attention.code == DeliveryIntegrationAttentionCode.REVISION_PENDING
    assert _git(repository, "rev-parse", "main") == target_head

    changed_intent = b"changed intent\n"
    (package_root / "authority.json").write_bytes(authority_bytes)
    (package_root / "intent.md").write_bytes(changed_intent)
    mutated_manifest = DesignPackageManifest.from_content(
        "change-a",
        changed_intent,
        design_bytes,
        authority_bytes,
    )
    (package_root / "manifest.json").write_bytes(mutated_manifest.canonical_bytes())

    source_mutated = application.integrate_ready_change("change-a")

    assert source_mutated.attention is not None
    assert source_mutated.attention.code == DeliveryIntegrationAttentionCode.PACKAGE_MUTATED
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"


def test_integration_revalidates_package_after_candidate_proof_before_target_cas(tmp_path: Path) -> None:
    package_root = tmp_path / "packages/change-a"

    def mutate_package(_candidate: DeliveryIntegrationCandidate, _commit: str) -> tuple[str, ...]:
        (package_root / "design.md").write_text("mutated during proof\n", encoding="utf-8")
        return ()

    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=mutate_package,
    )
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.PACKAGE_MUTATED
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"


def test_integration_revalidates_reviewed_branch_after_candidate_proof(tmp_path: Path) -> None:
    worktree: Path | None = None

    def advance_change(_candidate: DeliveryIntegrationCandidate, _commit: str) -> tuple[str, ...]:
        assert worktree is not None
        (worktree / "late.txt").write_text("late change\n", encoding="utf-8")
        _git(worktree, "add", "late.txt")
        _git(worktree, "commit", "-m", "unreviewed late change")
        return ()

    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=advance_change,
    )
    worktree = coordinator.show("change-a").worktree_path
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"
