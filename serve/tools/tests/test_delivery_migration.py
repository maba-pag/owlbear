"""Behavioral tests for one-way Delivery state migration."""

# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery import (
    CapacityLedger,
    ChangeCoordination,
    DeliveryChangeAbandonment,
    DeliveryChangeStage,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryIntegrationCompletion,
    DeliveryOutcome,
    DeliveryPlanScope,
    DeliverySourceBinding,
    DeliveryStage,
    DeliveryStartupConfig,
    OutcomeAuthorityBinding,
    load_delivery_application,
)
from owlbear_tools import delivery_migration
from owlbear_tools.delivery_migration import (
    DeliveryStateMigrationError,
    apply_delivery_state_migration,
    plan_delivery_state_migration,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _canonical(model: object) -> bytes:
    payload = model.model_dump(mode="json")  # type: ignore[attr-defined]
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _contract(change_id: str) -> DeliveryContract:
    return DeliveryContract(
        change_id=change_id,
        title="Migrated Change",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="approved migration fixture",
                statement="Preserve exact Delivery authority.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="Migrated Outcome",
                promise="Retain the active Delivery outcome.",
                acceptance=("The migrated runtime loads.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            DeliverySourceBinding(source_name="intent.md", sha256=hashlib.sha256(b"intent\n").hexdigest()),
            DeliverySourceBinding(source_name="design.md", sha256=hashlib.sha256(b"design\n").hexdigest()),
        ),
    )


def _legacy_repository(tmp_path: Path) -> tuple[Path, Path, bytes]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Migration Test")
    _git(repository, "config", "user.email", "migration@example.invalid")
    (repository / "README.md").write_text("migration fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    head = _git(repository, "rev-parse", "HEAD")

    change_id = "change-a"
    legacy_worktree = repository / ".owlbear/worktrees" / change_id
    legacy_worktree.parent.mkdir(parents=True)
    _git(repository, "worktree", "add", "-b", f"owlbear/change/{change_id}", str(legacy_worktree), head)

    legacy_target = repository / ".owlbear/target"
    change_root = legacy_target / "delivery/changes" / change_id
    change_root.mkdir(parents=True)
    contract = _contract(change_id)
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.PLANNING,
            ),
        )
    )
    frontier_bytes = _canonical(frontier)
    (change_root / "admission.json").write_text("{}\n", encoding="utf-8")
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_bytes(frontier_bytes)

    target_runtime = legacy_target / "target-runtime"
    coordination_root = target_runtime / "coordination"
    coordination_root.mkdir(parents=True)
    coordination = ChangeCoordination(
        change_id=change_id,
        branch=f"owlbear/change/{change_id}",
        worktree_path=legacy_worktree,
        integration_target="main",
        target_head=head,
        last_reviewed_commit=head,
    )
    (coordination_root / f"{change_id}.json").write_bytes(_canonical(coordination))
    (target_runtime / "capacity.json").write_bytes(_canonical(CapacityLedger(capacity=1)))
    verification = target_runtime / "integration-verification"
    (verification / "requests").mkdir(parents=True)
    (verification / "receipts").mkdir()
    (verification / "requests/request.json").write_text('{"historical":true}\n', encoding="utf-8")
    (legacy_target / "manifest.json").write_text('{"schema_version":1}\n', encoding="utf-8")

    config = repository / ".owlbear/delivery/config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"schema_version":1,"integration_target":"main"}\n', encoding="utf-8")
    return repository, legacy_worktree, frontier_bytes


def _legacy_completion() -> DeliveryIntegrationCompletion:
    return DeliveryIntegrationCompletion(
        completion_id="a" * 64,
        candidate_id="b" * 64,
        package_id="c" * 64,
        target_commit="1" * 40,
        completion_path=".owlbear/completed/delivery-runtime.json",
    )


def _write_legacy_completion(repository: Path, completion: DeliveryIntegrationCompletion) -> bytes:
    path = repository / ".owlbear/target/delivery/changes/change-a/frontier.json"
    payload = json.loads(path.read_bytes())
    payload["schema_version"] = 15
    payload["integration_result_id"] = completion.completion_id
    payload["integration_completion"] = completion.model_dump(mode="json")
    content = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(content)
    return content


def test_migration_accepts_legacy_integration_completion_as_terminal(tmp_path: Path) -> None:
    repository, _legacy_worktree, _frontier_bytes = _legacy_repository(tmp_path)
    completion = _legacy_completion()
    legacy_bytes = _write_legacy_completion(repository, completion)

    plan = plan_delivery_state_migration(repository)

    assert plan.changes[0].legacy_completion == completion
    apply_delivery_state_migration(plan)

    assert (repository / ".owlbear/delivery/runtime/changes/change-a/frontier.json").read_bytes() == legacy_bytes


def test_migration_accepts_abandoned_change_as_terminal(tmp_path: Path) -> None:
    repository, _legacy_worktree, _frontier_bytes = _legacy_repository(tmp_path)
    frontier_path = repository / ".owlbear/target/delivery/changes/change-a/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
    abandonment = DeliveryChangeAbandonment.create(
        change_id="change-a",
        prior_stage=DeliveryChangeStage.BUILDING,
        abandoned_at=datetime(2026, 8, 12, tzinfo=UTC),
        reason="The Change is no longer required.",
    )
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"change_abandonment": abandonment})))

    coordination_path = repository / ".owlbear/target/target-runtime/coordination/change-a.json"
    coordination = ChangeCoordination.model_validate_json(coordination_path.read_bytes())
    coordination_path.write_bytes(_canonical(coordination.model_copy(update={"last_reviewed_commit": "0" * 40})))

    plan = plan_delivery_state_migration(repository)

    assert plan.changes[0].frontier.change_abandonment == abandonment


def test_migration_rejects_legacy_completion_identity_mismatch(tmp_path: Path) -> None:
    repository, legacy_worktree, _frontier_bytes = _legacy_repository(tmp_path)
    completion = _legacy_completion()
    _write_legacy_completion(repository, completion)
    path = repository / ".owlbear/target/delivery/changes/change-a/frontier.json"
    payload = json.loads(path.read_bytes())
    payload["integration_result_id"] = "d" * 64
    path.write_bytes((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())

    with pytest.raises(DeliveryStateMigrationError, match="completion identity differs"):
        plan_delivery_state_migration(repository)

    assert legacy_worktree.is_dir()


def test_migration_rejects_staged_legacy_completion_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository, legacy_worktree, _frontier_bytes = _legacy_repository(tmp_path)
    completion = _legacy_completion()
    _write_legacy_completion(repository, completion)
    plan = plan_delivery_state_migration(repository)
    original_stage = delivery_migration._stage_runtime

    def corrupt_stage(migration_plan: delivery_migration.DeliveryStateMigrationPlan, staging: Path) -> None:
        original_stage(migration_plan, staging)
        path = staging / "changes/change-a/frontier.json"
        payload = json.loads(path.read_bytes())
        payload["integration_completion"]["completion_path"] = "corrupted/completion.json"
        path.write_bytes((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())

    monkeypatch.setattr(delivery_migration, "_stage_runtime", corrupt_stage)

    with pytest.raises(DeliveryStateMigrationError, match="staged Delivery frontier changed"):
        apply_delivery_state_migration(plan)

    assert legacy_worktree.is_dir()
    assert not (repository / ".owlbear/delivery/runtime").exists()


def test_migration_moves_owned_worktree_and_preserves_runtime_and_archive(tmp_path: Path) -> None:
    repository, legacy_worktree, frontier_bytes = _legacy_repository(tmp_path)

    plan = plan_delivery_state_migration(repository)

    assert not plan.already_migrated
    assert tuple(change.change_id for change in plan.changes) == ("change-a",)
    assert legacy_worktree.exists()
    assert not (repository / ".owlbear/delivery/runtime").exists()

    apply_delivery_state_migration(plan)

    canonical_worktree = repository / ".owlbear/delivery/worktrees/change-a"
    runtime = repository / ".owlbear/delivery/runtime"
    archive = repository / ".owlbear/legacy/delivery-state-migration"
    assert canonical_worktree.is_dir()
    assert not legacy_worktree.exists()
    assert str(canonical_worktree) in _git(repository, "worktree", "list", "--porcelain")
    assert (runtime / "changes/change-a/frontier.json").read_bytes() == frontier_bytes
    coordination = ChangeCoordination.model_validate_json((runtime / "coordination/changes/change-a.json").read_bytes())
    assert coordination.worktree_path == canonical_worktree
    assert (runtime / "claims/integration-verification/requests/request.json").is_file()
    assert (archive / "target/manifest.json").is_file()
    assert (archive / "worktrees").is_dir()
    assert not (repository / ".owlbear/target").exists()
    assert not (repository / ".owlbear/worktrees").exists()

    application = load_delivery_application(
        DeliveryStartupConfig(
            schema_version=2,
            remote="origin",
            target_branch="main",
            github_repository="example/project",
        ),
        workspace_root=repository,
    )
    assert tuple(item.change_id for item in application.list_work_items()) == ("change-a",)
    assert plan_delivery_state_migration(repository).already_migrated


def test_migration_preserves_unowned_registered_worktree_outside_delivery_authority(tmp_path: Path) -> None:
    repository, _legacy_worktree, frontier_bytes = _legacy_repository(tmp_path)
    unowned = repository / ".owlbear/worktrees/unowned"
    _git(repository, "worktree", "add", "-b", "owlbear/feature/unowned", str(unowned), "HEAD")
    plan = plan_delivery_state_migration(repository)

    assert tuple(worktree.path for worktree in plan.preserved_worktrees) == (unowned.resolve(),)

    apply_delivery_state_migration(plan)

    preserved = repository / ".owlbear/scratch/delivery-state-migration-worktrees/unowned"
    assert preserved.is_dir()
    assert not unowned.exists()
    assert str(preserved) in _git(repository, "worktree", "list", "--porcelain")
    assert (repository / ".owlbear/delivery/runtime/changes/change-a/frontier.json").read_bytes() == frontier_bytes
    assert (repository / ".owlbear/delivery/worktrees/change-a").is_dir()


def test_migration_rolls_back_prior_worktree_move_after_later_move_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, legacy_worktree, frontier_bytes = _legacy_repository(tmp_path)
    unowned = repository / ".owlbear/worktrees/unowned"
    _git(repository, "worktree", "add", "-b", "owlbear/feature/unowned", str(unowned), "HEAD")
    plan = plan_delivery_state_migration(repository)
    registrations_before = _git(repository, "worktree", "list", "--porcelain")
    original_git = delivery_migration._git

    def fail_preserved_move(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        if arguments[:2] == ("worktree", "move") and arguments[2] == str(unowned.resolve()):
            detail = "injected worktree move failure"
            raise DeliveryStateMigrationError(detail)
        return original_git(root, *arguments, check=check)

    monkeypatch.setattr(delivery_migration, "_git", fail_preserved_move)  # type: ignore[attr-defined]

    with pytest.raises(DeliveryStateMigrationError, match="injected worktree move failure"):
        apply_delivery_state_migration(plan)

    assert legacy_worktree.is_dir()
    assert unowned.is_dir()
    assert (repository / ".owlbear/target/delivery/changes/change-a/frontier.json").read_bytes() == frontier_bytes
    assert not (repository / ".owlbear/delivery/runtime").exists()
    assert not (repository / ".owlbear/delivery/worktrees").exists()
    assert not (repository / ".owlbear/scratch/delivery-state-migration-worktrees").exists()
    assert _git(repository, "worktree", "list", "--porcelain") == registrations_before


def test_migration_recovery_removes_nested_preserved_worktree_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, legacy_worktree, _frontier_bytes = _legacy_repository(tmp_path)
    nested = repository / ".owlbear/worktrees/group/unowned"
    nested.parent.mkdir()
    _git(repository, "worktree", "add", "-b", "owlbear/feature/nested-unowned", str(nested), "HEAD")
    plan = plan_delivery_state_migration(repository)
    original_publish = delivery_migration._publish_migration

    def interrupt_after_publication(
        migration_plan: delivery_migration.DeliveryStateMigrationPlan, staging: Path
    ) -> None:
        original_publish(migration_plan, staging)
        raise KeyboardInterrupt

    monkeypatch.setattr(delivery_migration, "_publish_migration", interrupt_after_publication)
    with pytest.raises(KeyboardInterrupt):
        apply_delivery_state_migration(plan)

    monkeypatch.setattr(delivery_migration, "_publish_migration", original_publish)
    delivery_migration._recover_migration(repository)

    assert legacy_worktree.is_dir()
    assert nested.is_dir()
    assert not (repository / ".owlbear/scratch/delivery-state-migration-worktrees").exists()
    assert not (repository / ".owlbear/delivery/migration.json").exists()


def test_migration_revalidates_plan_before_first_mutation(tmp_path: Path) -> None:
    repository, legacy_worktree, frontier_bytes = _legacy_repository(tmp_path)
    plan = plan_delivery_state_migration(repository)
    (legacy_worktree / "new.txt").write_text("new authority\n", encoding="utf-8")
    _git(legacy_worktree, "add", "new.txt")
    _git(legacy_worktree, "commit", "-m", "advance after planning")

    with pytest.raises(DeliveryStateMigrationError, match="reviewed boundary"):
        apply_delivery_state_migration(plan)

    assert legacy_worktree.is_dir()
    assert (repository / ".owlbear/target/delivery/changes/change-a/frontier.json").read_bytes() == frontier_bytes
    assert not (repository / ".owlbear/delivery/migration.json").exists()
    assert not (repository / ".owlbear/delivery/runtime").exists()


def test_migration_recovers_abrupt_post_publication_interruption_on_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, legacy_worktree, frontier_bytes = _legacy_repository(tmp_path)
    plan = plan_delivery_state_migration(repository)
    original_publish = delivery_migration._publish_migration

    def interrupt_after_publication(
        migration_plan: delivery_migration.DeliveryStateMigrationPlan, staging: Path
    ) -> None:
        original_publish(migration_plan, staging)
        raise KeyboardInterrupt

    monkeypatch.setattr(delivery_migration, "_publish_migration", interrupt_after_publication)
    with pytest.raises(KeyboardInterrupt):
        apply_delivery_state_migration(plan)

    assert (repository / ".owlbear/delivery/migration.json").is_file()
    assert (repository / ".owlbear/delivery/runtime").is_dir()
    assert (repository / ".owlbear/legacy/delivery-state-migration/target").is_dir()
    assert not legacy_worktree.exists()

    monkeypatch.setattr(delivery_migration, "_publish_migration", original_publish)
    apply_delivery_state_migration(plan)

    canonical_worktree = repository / ".owlbear/delivery/worktrees/change-a"
    assert canonical_worktree.is_dir()
    assert (repository / ".owlbear/delivery/runtime/changes/change-a/frontier.json").read_bytes() == frontier_bytes
    assert (repository / ".owlbear/legacy/delivery-state-migration/target").is_dir()
    assert not (repository / ".owlbear/delivery/migration.json").exists()


def test_migration_rejects_registered_change_worktree_missing_from_disk(tmp_path: Path) -> None:
    repository, legacy_worktree, frontier_bytes = _legacy_repository(tmp_path)
    registrations_before = delivery_migration._registered_worktrees(repository)
    shutil.rmtree(legacy_worktree)

    with pytest.raises(DeliveryStateMigrationError, match="registered worktree is missing"):
        plan_delivery_state_migration(repository)

    assert (repository / ".owlbear/target/delivery/changes/change-a/frontier.json").read_bytes() == frontier_bytes
    assert not (repository / ".owlbear/delivery/migration.json").exists()
    assert not (repository / ".owlbear/delivery/runtime").exists()
    assert delivery_migration._registered_worktrees(repository) == registrations_before


def test_migration_rejects_nested_symlinked_retired_authority(tmp_path: Path) -> None:
    repository, legacy_worktree, _frontier_bytes = _legacy_repository(tmp_path)
    external = repository / "external.json"
    external.write_text('{"outside":true}\n', encoding="utf-8")
    nested_link = repository / ".owlbear/target/delivery/changes/change-a/external.json"
    nested_link.symlink_to(external)

    with pytest.raises(DeliveryStateMigrationError, match="contains a symlink"):
        plan_delivery_state_migration(repository)

    assert legacy_worktree.is_dir()
    assert nested_link.is_symlink()
    assert not (repository / ".owlbear/delivery/migration.json").exists()
    assert not (repository / ".owlbear/delivery/runtime").exists()
