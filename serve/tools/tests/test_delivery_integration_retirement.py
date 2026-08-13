from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from owlbear_delivery.change_workspace import CapacityLedger, ChangeCoordination
from owlbear_delivery.completed_history import CompletedHistoryCatalog
from owlbear_delivery.delivery_runtime import DeliveryTaskDefinition
from owlbear_delivery.design_package import CompletionPackageManifest, DesignPackageManifest
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryOutcome,
    DeliveryPlanScope,
    DeliverySourceBinding,
)
from owlbear_tools import delivery_integration_retirement
from owlbear_tools.delivery_integration_retirement import (
    DeliveryIntegrationRetirementError,
    apply_delivery_integration_retirement,
    plan_delivery_integration_retirement,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _canonical(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")  # type: ignore[attr-defined]
    return f"{json.dumps(value, sort_keys=True, separators=(',', ':'))}\n".encode()


def _contract(change_id: str, intent: bytes, design: bytes) -> DeliveryContract:
    return DeliveryContract(
        change_id=change_id,
        title="Retained completion",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="retirement fixture",
                statement="Keep the historical record queryable.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="Retain history",
                promise="Retire mutable terminal state without losing history.",
                acceptance=("The historical catalog remains unchanged.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            DeliverySourceBinding(source_name="intent.md", sha256=hashlib.sha256(intent).hexdigest()),
            DeliverySourceBinding(source_name="design.md", sha256=hashlib.sha256(design).hexdigest()),
        ),
    )


def _task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Retire terminal state",
        result="Remove mutable Integration carriers.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Retired state",),
        maintained_surfaces=("delivery_integration_retirement.py",),
        constraints=("Keep the legacy package.",),
        exclusions=("Do not remove Git history.",),
        acceptance_observations=("The catalog still returns the record.",),
        proof_boundaries=("CompletedHistoryCatalog",),
    )


def _package_files(
    change_id: str,
    baseline: str,
    target_branch: str,
) -> tuple[dict[str, bytes], CompletionPackageManifest, DeliveryTaskDefinition]:
    intent = f"intent {change_id}\n".encode()
    design = f"design {change_id}\n".encode()
    contract = _contract(change_id, intent, design)
    authority = _canonical(contract)
    authority_digest = hashlib.sha256(authority).hexdigest()
    task = _task()
    legacy_result = {
        "authority_digest": authority_digest,
        "change_id": change_id,
        "completed_commit": baseline,
        "result_id": "RESULT-TASK-001",
        "task_digest": task.digest,
        "task_id": task.task_id,
    }
    binding = {
        "active_claim": None,
        "assembly_required": False,
        "block": None,
        "candidate": None,
        "outcome_id": task.outcome_id,
        "output": None,
        "plan_scope_id": task.plan_scope_id,
        "recovery_attention": None,
        "requests": [],
        "result_candidate": None,
        "results": [legacy_result],
        "return_context": None,
        "stage": "completed",
        "tasks": [task.model_dump(mode="json")],
    }
    legacy_runtime = {
        "bindings": [binding],
        "integration_attention": None,
        "integration_completion": None,
        "integration_repair_claim": None,
        "integration_result_id": None,
        "operator_moves": [],
        "schema_version": 1,
    }
    results = _canonical([legacy_result])
    runtime = _canonical(legacy_runtime)
    package = DesignPackageManifest.from_content(change_id, intent, design, authority)
    completion = CompletionPackageManifest(
        change_id=change_id,
        package_id=hashlib.sha256(package.canonical_bytes()).hexdigest(),
        authority_digest=authority_digest,
        runtime_sha256=hashlib.sha256(runtime).hexdigest(),
        result_history_sha256=hashlib.sha256(results).hexdigest(),
        reviewed_change_head=baseline,
        integration_target=target_branch,
        completion_path=f".owlbear/completed/{change_id}",
    )
    files = {
        "authority.json": authority,
        "completion.json": completion.canonical_bytes(),
        "design.md": design,
        "intent.md": intent,
        "manifest.json": package.canonical_bytes(),
        "results.json": results,
        "runtime.json": runtime,
    }
    return files, completion, task


def _fixture(tmp_path: Path, *, with_worktree: bool = False) -> tuple[Path, dict[str, str], Path, Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "dev")
    _git(repository, "config", "user.name", "Retirement Test")
    _git(repository, "config", "user.email", "retirement@example.invalid")
    (repository / "README.md").write_text("retirement fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "baseline")
    baseline = _git(repository, "rev-parse", "HEAD")
    change_id = "change-a"
    branch = f"owlbear/change/{change_id}"
    _git(repository, "branch", branch, baseline)
    package_root = repository / ".owlbear/completed" / change_id
    package_root.mkdir(parents=True)
    files, completion, _task = _package_files(change_id, baseline, "dev")
    for name, content in files.items():
        (package_root / name).write_bytes(content)
    _git(repository, "add", ".owlbear/completed")
    _git(repository, "commit", "-m", "publish legacy completion")
    package_commit = _git(repository, "rev-parse", "HEAD")
    legacy_root = repository / ".owlbear/legacy"
    legacy_root.mkdir()
    (repository / ".owlbear/completed").rename(legacy_root / "completed")
    _git(repository, "add", "-A", ".owlbear/completed", ".owlbear/legacy/completed")
    _git(repository, "commit", "-m", "move completion into legacy history")
    target_commit = _git(repository, "rev-parse", "HEAD")
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "update-ref", "refs/remotes/origin/dev", target_commit)

    delivery_root = repository / ".owlbear/delivery"
    (delivery_root / "runtime/changes" / change_id).mkdir(parents=True)
    (delivery_root / "runtime/claims/changes").mkdir(parents=True)
    (delivery_root / "runtime/claims").mkdir(exist_ok=True)
    (delivery_root / "runtime/capacity.json").write_bytes(_canonical(CapacityLedger(capacity=1)))
    (delivery_root / "config.json").write_text(
        '{"schema_version":2,"remote":"origin","target_branch":"dev","github_repository":"example/project"}\n',
        encoding="utf-8",
    )
    archive = repository / ".owlbear/legacy/delivery-state-migration/target"
    archive.mkdir(parents=True)
    completion_payload = {
        "candidate_id": hashlib.sha256(b"candidate").hexdigest(),
        "completion_id": completion.completion_id,
        "package_id": completion.package_id,
        "target_commit": package_commit,
        "completion_path": completion.completion_path,
    }
    current_binding = dict(json.loads(files["runtime.json"]))["bindings"][0]
    current_binding.pop("assembly_required")
    current_frontier = {
        "bindings": [current_binding],
        "integration_attention": None,
        "integration_completion": completion_payload,
        "integration_repair_claim": None,
        "integration_result_id": completion.completion_id,
        "operator_moves": [],
        "schema_version": 3,
    }
    (delivery_root / "runtime/changes" / change_id / "frontier.json").write_bytes(_canonical(current_frontier))
    contract = _contract(change_id, f"intent {change_id}\n".encode(), f"design {change_id}\n".encode())
    (delivery_root / "runtime/changes" / change_id / "contract.json").write_bytes(_canonical(contract))
    coordination = ChangeCoordination(
        change_id=change_id,
        branch=branch,
        worktree_path=delivery_root / "worktrees" / change_id,
        integration_target="dev",
        target_head=target_commit,
        last_reviewed_commit=baseline,
    )
    (delivery_root / "runtime/claims/changes" / f"{change_id}.json").write_bytes(_canonical(coordination))
    if with_worktree:
        _git(repository, "worktree", "add", str(coordination.worktree_path), branch)
    return (
        repository,
        {"baseline": baseline, "package": package_commit, "target": target_commit},
        delivery_root,
        archive,
        Path(branch),
    )


def test_retirement_plans_legacy_frontier_and_preserves_catalog_snapshot(tmp_path: Path) -> None:
    repository, commits, delivery_root, _archive, _branch = _fixture(tmp_path)
    catalog = CompletedHistoryCatalog(repository, "dev", "refs/remotes/origin/dev", delivery_root / "runtime")
    before = catalog.list()
    frontier_before = (delivery_root / "runtime/changes/change-a/frontier.json").read_bytes()

    plan = plan_delivery_integration_retirement(repository)

    assert not plan.already_retired
    assert tuple(change.change_id for change in plan.changes) == ("change-a",)
    assert plan.target_commit == commits["target"]
    assert plan.changes[0].worktree is None
    assert (delivery_root / "runtime/changes/change-a/frontier.json").read_bytes() == frontier_before
    assert catalog.list() == before


def test_retirement_ignores_completionless_legacy_frontier(tmp_path: Path) -> None:
    repository, _commits, delivery_root, _archive, _branch = _fixture(tmp_path)
    frontier_path = delivery_root / "runtime/changes/change-a/frontier.json"
    frontier = json.loads(frontier_path.read_bytes())
    frontier["integration_completion"] = None
    frontier["integration_result_id"] = None
    frontier_path.write_bytes(_canonical(frontier))

    plan = plan_delivery_integration_retirement(repository)

    assert plan.already_retired
    assert plan.changes == ()


def test_retirement_apply_on_empty_workspace_is_idempotent(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()

    plan = plan_delivery_integration_retirement(repository)

    apply_delivery_integration_retirement(plan)

    assert plan.already_retired
    assert plan_delivery_integration_retirement(repository).already_retired
    assert not (repository / ".owlbear").exists()


def test_retirement_rejects_target_drift_between_plan_and_apply(tmp_path: Path) -> None:
    repository, commits, delivery_root, _archive, _branch = _fixture(tmp_path)
    plan = plan_delivery_integration_retirement(repository)
    (repository / "README.md").write_text("target moved\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "move target")
    moved_target = _git(repository, "rev-parse", "HEAD")
    _git(repository, "update-ref", "refs/remotes/origin/dev", moved_target)

    with pytest.raises(DeliveryIntegrationRetirementError, match="target differs"):
        apply_delivery_integration_retirement(plan)

    assert _git(repository, "rev-parse", "refs/remotes/origin/dev") == moved_target
    assert (delivery_root / "runtime/changes/change-a/frontier.json").is_file()
    assert commits["target"] != moved_target


def test_retirement_rejects_change_set_drift_between_plan_and_apply(tmp_path: Path) -> None:
    repository, _commits, delivery_root, _archive, _branch = _fixture(tmp_path)
    plan = plan_delivery_integration_retirement(repository)
    altered_plan = replace(plan, changes=(), already_retired=True)

    with pytest.raises(DeliveryIntegrationRetirementError, match="Change set differs"):
        apply_delivery_integration_retirement(altered_plan)

    assert (delivery_root / "runtime/changes/change-a/frontier.json").is_file()


@pytest.mark.parametrize("worktree_mode", ["absent", "present"])
def test_retirement_applies_exact_cleanup_and_retains_git_history(tmp_path: Path, worktree_mode: str) -> None:
    repository, commits, delivery_root, _archive, _branch = _fixture(tmp_path, with_worktree=worktree_mode == "present")
    plan = plan_delivery_integration_retirement(repository)

    apply_delivery_integration_retirement(plan)

    assert not (delivery_root / "runtime/changes/change-a").exists()
    assert not (delivery_root / "runtime/claims/changes/change-a.json").exists()
    assert not (delivery_root / "runtime/claims/publication-locks/change-a").exists()
    assert not (repository / ".owlbear/delivery/integration-retirement.json").exists()
    assert not (repository / ".owlbear/scratch/delivery-integration-retirement").exists()
    assert not (delivery_root / "worktrees" / "change-a").exists()
    assert _git(repository, "rev-parse", "refs/remotes/origin/dev") == commits["target"]
    assert _git(repository, "rev-parse", "refs/heads/owlbear/change/change-a") == commits["baseline"]
    records = CompletedHistoryCatalog(repository, "dev", "refs/remotes/origin/dev", delivery_root / "runtime").list()
    assert tuple(record.change_id for record in records.records) == ("change-a",)


def test_retirement_recovers_staged_state_after_removal_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, commits, delivery_root, _archive, _branch = _fixture(tmp_path, with_worktree=True)
    plan = plan_delivery_integration_retirement(repository)

    def fail_removal(_journal: object) -> None:
        message = "injected retirement failure"
        raise DeliveryIntegrationRetirementError(message)

    monkeypatch.setattr(delivery_integration_retirement, "_remove_publication_locks", fail_removal)

    with pytest.raises(DeliveryIntegrationRetirementError, match="injected retirement failure"):
        apply_delivery_integration_retirement(plan)

    assert (delivery_root / "runtime/changes/change-a/frontier.json").is_file()
    assert (delivery_root / "runtime/claims/changes/change-a.json").is_file()
    worktree = delivery_root / "worktrees" / "change-a"
    assert worktree.is_dir()
    assert _git(worktree, "rev-parse", "HEAD") == commits["baseline"]
    assert not (repository / ".owlbear/delivery/integration-retirement.json").exists()
    assert not (repository / ".owlbear/scratch/delivery-integration-retirement").exists()


def test_retirement_rejects_forged_journal_lock_path(tmp_path: Path) -> None:
    repository, _commits, _delivery_root, _archive, _branch = _fixture(tmp_path)
    plan = plan_delivery_integration_retirement(repository)
    staging_root = repository / ".owlbear/scratch/delivery-integration-retirement/operation"
    journal = delivery_integration_retirement._journal_for_plan(plan, staging_root)
    forged_change = journal.changes[0].model_copy(update={"publication_lock_path": tmp_path / "outside-lock"})
    forged = journal.model_copy(update={"changes": (forged_change,)})
    journal_path = repository / ".owlbear/delivery/integration-retirement.json"
    journal_path.write_text(forged.model_dump_json() + "\n", encoding="utf-8")

    with pytest.raises(DeliveryIntegrationRetirementError, match="journal path identity"):
        delivery_integration_retirement._retirement_lock_roots(repository)

    assert not (tmp_path / "outside-lock").exists()


def test_retirement_rejects_forged_journal_worktree_path_before_write(tmp_path: Path) -> None:
    repository, _commits, _delivery_root, _archive, _branch = _fixture(tmp_path)
    plan = plan_delivery_integration_retirement(repository)
    staging_root = repository / ".owlbear/scratch/delivery-integration-retirement/operation"
    journal = delivery_integration_retirement._journal_for_plan(plan, staging_root)
    forged_change = journal.changes[0].model_copy(
        update={
            "worktree_path": tmp_path / "outside-worktree",
            "branch": "owlbear/change/change-a",
            "worktree_head": "0" * 40,
        }
    )
    forged = journal.model_copy(update={"changes": (forged_change,)})

    with pytest.raises(DeliveryIntegrationRetirementError, match="worktree path is unsafe"):
        delivery_integration_retirement._write_journal(forged)

    assert not (repository / ".owlbear/delivery/integration-retirement.json").exists()


def test_retirement_replays_cleanup_phase_after_staging_cleanup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _commits, delivery_root, _archive, _branch = _fixture(tmp_path)
    plan = plan_delivery_integration_retirement(repository)
    original_rmtree = delivery_integration_retirement.shutil.rmtree
    staging_root: Path | None = None

    def fail_cleanup(path: str | Path, *args: object, **kwargs: object) -> None:
        if staging_root is not None and Path(path).is_relative_to(staging_root):
            message = "injected staging cleanup failure"
            raise OSError(message)
        original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(delivery_integration_retirement.shutil, "rmtree", fail_cleanup)
    staging_root = repository / ".owlbear/scratch/delivery-integration-retirement"
    with pytest.raises(DeliveryIntegrationRetirementError, match="staging cleanup failed"):
        apply_delivery_integration_retirement(plan)

    journal_path = repository / ".owlbear/delivery/integration-retirement.json"
    assert journal_path.is_file()
    assert json.loads(journal_path.read_text(encoding="utf-8"))["phase"] == "cleanup"
    assert not (delivery_root / "runtime/changes/change-a").exists()

    monkeypatch.setattr(delivery_integration_retirement.shutil, "rmtree", original_rmtree)
    apply_delivery_integration_retirement(plan)

    assert not journal_path.exists()
    assert not staging_root.exists()
    assert not (delivery_root / "claims/publication-locks/change-a").exists()
