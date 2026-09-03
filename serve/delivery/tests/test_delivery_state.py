from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_delivery import (
    ChangeExternalHeadAdoptionReceipt,
    ChangeTargetSyncReceipt,
    DeliveryAcceptanceAttentionReason,
    DeliveryActiveClaim,
    DeliveryAdmissionReceipt,
    DeliveryChangeCompletion,
    DeliveryChangeDisposition,
    DeliveryChangeDispositionKind,
    DeliveryChangeStage,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryFinalization,
    DeliveryFinalizationInvalidation,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryHealthDiagnostic,
    DeliveryMergedPullRequestLatch,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOutcome,
    DeliveryPlanScope,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryStateConflictError,
    DeliveryStatePublicationError,
    DeliveryStatePublisher,
    DeliveryStateRepairReceipt,
    DeliveryStateResponseUnknownError,
    DeliveryStateSnapshot,
    DeliveryWorkerRole,
    DesignPackageStore,
    OutcomeAuthorityBinding,
    PortfolioCoordinator,
)
from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
)
from owlbear_delivery.change_workspace import ChangeWorkspaceManager
from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    _can_defer_remote_state_reconciliation,
    _composed_runtimes,
    _DeferredRemoteStateReconciliationError,
    _fetch_snapshot_change_head,
    _is_unpublished_acceptance_attention_successor,
    _load_contracts,
    load_delivery_application,
)
from owlbear_delivery.draft_pull_request import PullRequestReadyReceipt
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.target_contract import DeliverySourceBinding

_GIT = resolve_git_executable()


def _git(repository: Path, *arguments: str, check: bool = True) -> str:
    result = subprocess.run(  # noqa: S603
        (_GIT, "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Delivery State Test")
    _git(repository, "config", "user.email", "delivery-state@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    initial = _git(repository, "rev-parse", "HEAD")
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    _git(repository, "fetch", "origin", "refs/heads/main:refs/remotes/origin/main")
    return repository, remote, initial


def _contract(change_id: str) -> tuple[DeliveryContract, bytes, bytes]:
    intent = f"# Intent {change_id}\n".encode()
    design = f"# Design {change_id}\n".encode()
    contract = DeliveryContract(
        change_id=change_id,
        title=f"Delivery {change_id}",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="test",
                statement="Preserve state.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="State",
                promise="Persist state.",
                acceptance=("State persists.",),
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
    return contract, intent, design


def _runtime(
    tmp_path: Path,
    repository: Path,
    change_id: str,
    contract: DeliveryContract,
) -> tuple[DeliveryRuntime, ChangeWorkspaceManager, Path]:
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
            ),
        ),
    )
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    return DeliveryRuntime(state_root, contract, workspace_manager=manager), manager, coordination.worktree_path


def _publish(  # noqa: PLR0913, PLR0917 - helper binds the exact publisher inputs.
    publisher: DeliveryStatePublisher,
    runtime: DeliveryRuntime,
    manager: ChangeWorkspaceManager,
    change_id: str,
    package_id: str,
    operation_id: str,
    *,
    expected_remote_head: str | None = None,
):
    admission = _admission(runtime, manager, change_id)
    return publisher.publish(
        change_id=change_id,
        package_id=package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=admission,
        operation_id=operation_id,
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
        expected_remote_head=expected_remote_head,
    )


def _admission(runtime: DeliveryRuntime, manager: ChangeWorkspaceManager, change_id: str) -> DeliveryAdmissionReceipt:
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    contract_bytes = (
        json.dumps(runtime.contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    source_bindings = [item.model_dump(mode="json") for item in runtime.contract.source_bindings]
    admission_values = {
        "schema_version": 1,
        "change_id": change_id,
        "contract_digest": hashlib.sha256(contract_bytes).hexdigest(),
        "source_bindings_digest": hashlib.sha256(
            json.dumps(source_bindings, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "integration_target": manager.show(change_id).integration_target,
        "checkpoint_commit": manager.show(change_id).last_reviewed_commit,
        "frontier_ids": tuple(binding.plan_scope_id for binding in frontier.bindings),
    }
    return DeliveryAdmissionReceipt(
        receipt_id=hashlib.sha256(
            json.dumps(admission_values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        **admission_values,
    )


def _startup_config() -> DeliveryStartupConfig:
    return DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
    )


def _snapshot(
    runtime: DeliveryRuntime,
    manager: ChangeWorkspaceManager,
    change_id: str,
) -> DeliveryStateSnapshot:
    return DeliveryStateSnapshot.create(
        operation_id=f"snapshot-{change_id}",
        change_id=change_id,
        package_id="f" * 64,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        sequence=1,
        parent_snapshot_id=None,
        base_head=None,
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )


def _canonical_payload(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _legacy_nested_receipt(receipt: object, removed_field: str) -> dict[str, object]:
    payload = receipt.model_dump(mode="json")
    payload["schema_version"] = 1
    payload.pop(removed_field)
    payload["receipt_id"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in payload.items() if key != "receipt_id"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return payload


def _publish_raw_snapshot(
    publisher: DeliveryStatePublisher,
    base: str,
    payload: dict[str, object],
) -> str:
    candidate = DeliveryStateSnapshot.model_construct(**payload)
    commit = publisher._commit_snapshot(base, candidate)  # noqa: SLF001
    publisher._push_snapshot(commit, base)  # noqa: SLF001
    return commit


def _legacy_target_sync_receipt(coordination: object) -> ChangeTargetSyncReceipt:
    return ChangeTargetSyncReceipt.create(
        operation_id="legacy-target-sync",
        change_id=coordination.change_id,
        integration_target=coordination.integration_target,
        expected_target="a" * 40,
        target_head="a" * 40,
        change_head_before=coordination.last_reviewed_commit,
        merged_head="b" * 40,
        merge_commit=True,
    )


def _commit_descendant(worktree: Path, filename: str, message: str) -> str:
    (worktree / filename).write_text(f"{message}\n", encoding="utf-8")
    _git(worktree, "add", filename)
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def test_loader_quarantines_repairable_frontier_without_remote_diagnostic(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    state_root = tmp_path / "state"

    healthy_contract, _healthy_intent, _healthy_design = _contract("healthy-sibling")
    healthy_runtime, healthy_manager, _healthy_worktree = _runtime(
        tmp_path,
        repository,
        "healthy-sibling",
        healthy_contract,
    )
    healthy_root = state_root / "changes/healthy-sibling"
    healthy_root.joinpath("contract.json").write_bytes(_canonical_payload(healthy_contract.model_dump(mode="json")))
    healthy_root.joinpath("admission.json").write_bytes(
        _canonical_payload(_admission(healthy_runtime, healthy_manager, "healthy-sibling").model_dump(mode="json"))
    )

    repair_contract, _repair_intent, _repair_design = _contract("offline-repair")
    repair_runtime, repair_manager, _repair_worktree = _runtime(
        tmp_path,
        repository,
        "offline-repair",
        repair_contract,
    )
    repair_coordination = repair_manager.show("offline-repair")
    current_frontier = DeliveryFrontier.model_validate_json(repair_runtime.frontier_bytes()).model_copy(
        update={"target_sync_receipt": _legacy_target_sync_receipt(repair_coordination)}
    )
    frontier_path = state_root / "changes/offline-repair/frontier.json"
    frontier_path.write_bytes(_canonical_payload(current_frontier.model_dump(mode="json")))
    repair_runtime = DeliveryRuntime(state_root, repair_contract, workspace_manager=repair_manager)
    repair_root = state_root / "changes/offline-repair"
    repair_root.joinpath("contract.json").write_bytes(_canonical_payload(repair_contract.model_dump(mode="json")))
    repair_root.joinpath("admission.json").write_bytes(
        _canonical_payload(_admission(repair_runtime, repair_manager, "offline-repair").model_dump(mode="json"))
    )
    legacy_frontier = current_frontier.model_dump(mode="json")
    legacy_frontier["target_sync_receipt"] = _legacy_nested_receipt(
        current_frontier.target_sync_receipt,
        "review_required",
    )
    frontier_path.write_bytes(_canonical_payload(legacy_frontier))

    contracts, diagnostics = _load_contracts(state_root)

    assert "healthy-sibling" in contracts
    assert "offline-repair" not in contracts
    diagnostic = next(item for item in diagnostics if item.change_id == "offline-repair")
    assert diagnostic.repairable is False
    assert diagnostic.remote_head is None
    assert "remote state must be reachable" in diagnostic.detail

    remote_diagnostic = DeliveryHealthDiagnostic(
        source="remote-state",
        code="snapshot-identity-invalid",
        detail="Remote Delivery snapshot identity is invalid.",
        change_id="offline-repair",
        path=".owlbear/delivery/state/offline-repair/snapshot.json",
        remote_head="a" * 40,
        repairable=True,
    )
    repaired_contracts, repaired_diagnostics = _load_contracts(state_root, (remote_diagnostic,))

    assert "offline-repair" in repaired_contracts
    local_diagnostic = next(item for item in repaired_diagnostics if item.change_id == "offline-repair")
    assert local_diagnostic.repairable is True
    assert local_diagnostic.remote_head == "a" * 40


@pytest.mark.parametrize("receipt_kind", ["target-sync", "external-head-adoption"])
def test_state_publisher_repairs_legacy_nested_receipt_snapshot(
    tmp_path: Path,
    receipt_kind: str,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = f"state-repair-{receipt_kind}"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    coordination = manager.show(change_id)
    if receipt_kind == "target-sync":
        field_name = "target_sync_receipt"
        removed_field = "review_required"
        receipt = _legacy_target_sync_receipt(coordination)
    else:
        field_name = "external_head_adoption_receipt"
        removed_field = "provenance"
        receipt = ChangeExternalHeadAdoptionReceipt.create(
            operation_id="legacy-adoption",
            change_id=change_id,
            branch=coordination.branch,
            expected_head="a" * 40,
            adopted_head="b" * 40,
        )
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes()).model_copy(update={field_name: receipt})
    frontier_path = tmp_path / "state" / "changes" / change_id / "frontier.json"
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(tmp_path / "state", contract, workspace_manager=manager)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    initial = _publish(publisher, runtime, manager, change_id, "e" * 64, f"{change_id}-initial")
    valid = publisher.read_snapshot(change_id)
    assert valid is not None
    payload = valid.model_dump(mode="json")
    payload["frontier"][field_name] = _legacy_nested_receipt(receipt, removed_field)
    payload["snapshot_id"] = ""
    payload["snapshot_id"] = hashlib.sha256(_canonical_payload(payload)).hexdigest()
    invalid_snapshot_id = payload["snapshot_id"]
    invalid_commit = _publish_raw_snapshot(publisher, initial.published_head, payload)

    inventory = publisher.read_snapshot_inventory()
    diagnostic = next(item for item in inventory.diagnostics if item.change_id == change_id)
    assert diagnostic.repairable is True

    repaired = publisher.repair_snapshot(
        change_id=change_id,
        package_id="e" * 64,
        coordination=coordination,
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id=f"{change_id}-repair",
        captured_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
        expected_remote_head=invalid_commit,
    )

    restored = publisher.read_snapshot(change_id)
    assert restored is not None
    assert repaired.previous_snapshot_id == invalid_snapshot_id
    assert repaired.repaired_snapshot_id == restored.snapshot_id
    assert restored.sequence == valid.sequence + 1
    assert restored.parent_snapshot_id == invalid_snapshot_id
    assert getattr(restored.frontier, field_name).schema_version == 2
    assert publisher.read_snapshot_inventory().diagnostics == ()


def _seed_loader_change(
    state_root: Path,
    manager: ChangeWorkspaceManager,
    store: DesignPackageStore,
    change_id: str,
    *,
    target_sync: bool,
) -> tuple[DeliveryRuntime, str]:
    contract, intent, design = _contract(change_id)
    package = store.create(change_id, intent, design)
    published_package = store.publish_contract(
        change_id,
        package.package_id,
        _canonical_payload(contract.model_dump(mode="json")),
        lambda *_content: None,
    )
    coordination = manager.ensure(change_id)
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    if target_sync:
        frontier = frontier.model_copy(update={"target_sync_receipt": _legacy_target_sync_receipt(coordination)})
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    change_root = state_root / "changes" / change_id
    change_root.joinpath("contract.json").write_bytes(_canonical_payload(contract.model_dump(mode="json")))
    change_root.joinpath("admission.json").write_bytes(
        _canonical_payload(_admission(runtime, manager, change_id).model_dump(mode="json"))
    )
    return runtime, published_package.package_id


def test_loader_starts_with_local_repair_attention_when_remote_state_is_unavailable(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    package_root = repository / ".owlbear/delivery/packages"
    worktree_root = repository / ".owlbear/delivery/worktrees"
    runtime_root.mkdir(parents=True)
    coordinator = PortfolioCoordinator(runtime_root)
    manager = ChangeWorkspaceManager(repository, worktree_root, coordinator, "main", "origin")
    store = DesignPackageStore(package_root, repository, transaction_root=runtime_root)
    _offline_runtime, _offline_package_id = _seed_loader_change(
        runtime_root,
        manager,
        store,
        "offline-repair",
        target_sync=True,
    )
    offline_frontier_path = runtime_root / "changes/offline-repair/frontier.json"
    offline_frontier = json.loads(offline_frontier_path.read_bytes())
    offline_current_frontier = DeliveryFrontier.model_validate_json(_offline_runtime.frontier_bytes())
    offline_frontier["target_sync_receipt"] = _legacy_nested_receipt(
        offline_current_frontier.target_sync_receipt,
        "review_required",
    )
    offline_frontier_path.write_bytes(_canonical_payload(offline_frontier))
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )

    with patch.object(
        DeliveryStatePublisher,
        "read_snapshot_inventory",
        side_effect=DeliveryStatePublicationError("remote state is unavailable", retry_safe=True),
    ):
        application = load_delivery_application(config, workspace_root=repository)

    health = application.delivery_health()
    assert any(item.source == "remote-state" and item.code == "remote-state-unavailable" for item in health.diagnostics)
    local_diagnostic = next(item for item in health.diagnostics if item.change_id == "offline-repair")
    assert local_diagnostic.code == "frontier-migration-required"
    assert local_diagnostic.repairable is False
    assert "remote state must be reachable" in local_diagnostic.detail
    assert application.list_work_items() == ()


def test_loader_health_evidence_repairs_invalid_remote_snapshot_with_sibling_preserved(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    package_root = repository / ".owlbear/delivery/packages"
    worktree_root = repository / ".owlbear/delivery/worktrees"
    runtime_root.mkdir(parents=True)
    coordinator = PortfolioCoordinator(runtime_root)
    manager = ChangeWorkspaceManager(repository, worktree_root, coordinator, "main", "origin")
    store = DesignPackageStore(package_root, repository, transaction_root=runtime_root)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    repair_runtime, repair_package_id = _seed_loader_change(
        runtime_root,
        manager,
        store,
        "repairable-change",
        target_sync=True,
    )
    sibling_runtime, sibling_package_id = _seed_loader_change(
        runtime_root,
        manager,
        store,
        "healthy-sibling",
        target_sync=False,
    )

    _publish(
        publisher,
        repair_runtime,
        manager,
        "repairable-change",
        repair_package_id,
        "repairable-change-initial",
    )
    sibling_initial = _publish(
        publisher,
        sibling_runtime,
        manager,
        "healthy-sibling",
        sibling_package_id,
        "healthy-sibling-initial",
    )
    valid = publisher.read_snapshot("repairable-change")
    assert valid is not None
    assert valid.frontier.target_sync_receipt is not None
    payload = valid.model_dump(mode="json")
    payload["frontier"]["target_sync_receipt"] = _legacy_nested_receipt(
        valid.frontier.target_sync_receipt,
        "review_required",
    )
    payload["snapshot_id"] = ""
    payload["snapshot_id"] = hashlib.sha256(_canonical_payload(payload)).hexdigest()
    invalid_commit = _publish_raw_snapshot(publisher, sibling_initial.published_head, payload)
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    local_frontier_path = runtime_root / "changes/repairable-change/frontier.json"
    local_frontier = json.loads(local_frontier_path.read_bytes())
    local_frontier["target_sync_receipt"] = _legacy_nested_receipt(
        valid.frontier.target_sync_receipt,
        "review_required",
    )
    local_frontier_path.write_bytes(_canonical_payload(local_frontier))
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )

    application = load_delivery_application(config, workspace_root=repository)
    health = application.delivery_health()
    diagnostic = next(
        item for item in health.diagnostics if item.source == "remote-state" and item.change_id == "repairable-change"
    )
    assert diagnostic.repairable is True
    assert diagnostic.remote_head == invalid_commit
    assert {item.change_id for item in application.list_work_items()} == {"healthy-sibling"}

    receipt = application.repair_delivery_state(
        "repairable-change",
        diagnostic.code,
        diagnostic.remote_head,
        "repairable-change-repair",
        confirmed_repair=True,
    )

    assert receipt.expected_remote_head == invalid_commit
    assert not any(item.change_id == "repairable-change" for item in application.delivery_health().diagnostics)
    assert {item.change_id for item in application.list_work_items()} == {
        "healthy-sibling",
        "repairable-change",
    }


def test_state_publisher_rejects_tampered_retired_snapshot_identity(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "state-repair-tampered"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    coordination = manager.show(change_id)
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes()).model_copy(
        update={"target_sync_receipt": _legacy_target_sync_receipt(coordination)}
    )
    frontier_path = tmp_path / "state" / "changes" / change_id / "frontier.json"
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(tmp_path / "state", contract, workspace_manager=manager)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    initial = _publish(publisher, runtime, manager, change_id, "e" * 64, f"{change_id}-initial")
    valid = publisher.read_snapshot(change_id)
    assert valid is not None
    payload = valid.model_dump(mode="json")
    payload["frontier"]["target_sync_receipt"] = _legacy_nested_receipt(
        coordination.target_sync_receipt or _legacy_target_sync_receipt(coordination),
        "review_required",
    )
    payload["snapshot_id"] = ""
    payload["snapshot_id"] = hashlib.sha256(_canonical_payload(payload)).hexdigest()
    payload["snapshot_id"] = "0" * 64
    invalid_commit = _publish_raw_snapshot(publisher, initial.published_head, payload)

    inventory = publisher.read_snapshot_inventory()
    diagnostic = next(item for item in inventory.diagnostics if item.change_id == change_id)
    assert diagnostic.repairable is False

    with pytest.raises(DeliveryStatePublicationError, match="historical identity cannot be verified"):
        publisher.repair_snapshot(
            change_id=change_id,
            package_id="e" * 64,
            coordination=coordination,
            runtime=runtime,
            admission=_admission(runtime, manager, change_id),
            operation_id=f"{change_id}-repair",
            captured_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
            expected_remote_head=invalid_commit,
        )

    assert publisher._remote_head() == invalid_commit  # noqa: SLF001
    assert publisher.read_snapshot_inventory().remote_head == invalid_commit


def test_loader_defers_active_remote_descendant_drift(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-descendant"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    descendant = _commit_descendant(worktree, "descendant.txt", "active descendant")

    assert _can_defer_remote_state_reconciliation(snapshot, repository, descendant)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader._remote_branch_head",
            return_value=descendant,
        ),
        pytest.raises(_DeferredRemoteStateReconciliationError),
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)


def test_loader_keeps_local_runtime_for_remote_only_repairable_diagnostic(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-remote-repair"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    diagnostic = DeliveryHealthDiagnostic(
        source="remote-state",
        code="snapshot-identity-invalid",
        detail="Remote Delivery snapshot identity is invalid.",
        change_id=change_id,
        repairable=True,
    )

    runtimes, diagnostics = _composed_runtimes(
        tmp_path / "state",
        {change_id: contract},
        manager,
        (diagnostic,),
    )

    assert change_id in runtimes
    assert diagnostics == ()
    assert DeliveryFrontier.model_validate_json(runtime.frontier_bytes()).schema_version == 17


def test_loader_accepts_local_descendant_when_active_remote_branch_was_deleted(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-local-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    _commit_descendant(manager.show(change_id).worktree_path, "descendant.txt", "local descendant")

    with pytest.raises(
        DeliveryApplicationLoadError,
        match="remote Change branch is missing for an active Delivery snapshot",
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)

    with pytest.raises(
        DeliveryApplicationLoadError,
        match="remote Change branch is missing for an active Delivery snapshot",
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository, allow_local_branch=True)

    with pytest.raises(
        DeliveryApplicationLoadError,
        match="remote Change branch is missing for an active Delivery snapshot",
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository, allow_local_branch=True)


def test_loader_accepts_unpublished_acceptance_attention_successor(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-acceptance-attention-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    local_frontier = snapshot.frontier.model_copy(
        update={
            "change_disposition": DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION,
                change_id=change_id,
                entered_from=DeliveryChangeStage.AWAITING_MERGE,
                recorded_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
                diagnostics=("provider acceptance evidence regressed",),
                acceptance_reason=DeliveryAcceptanceAttentionReason.LATCH_REGRESSION,
            ),
        }
    )
    _commit_descendant(worktree, "acceptance-attention.txt", "acceptance attention")

    assert _is_unpublished_acceptance_attention_successor(snapshot.frontier, local_frontier)
    with patch(
        "owlbear_delivery.delivery_application_loader._remote_branch_head",
        return_value=None,
    ):
        assert _fetch_snapshot_change_head(
            snapshot,
            _startup_config(),
            repository,
            allow_local_branch=True,
            allow_local_descendant=True,
        ) == (snapshot.change_head, False)


def test_loader_accepts_unpublished_head_moved_acceptance_successor(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-head-moved-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    observed_at = datetime(2026, 8, 23, 1, tzinfo=UTC)
    operation_id = "finalize-state-head-moved-fallback"
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=operation_id,
            exact_commit=initial,
            observation_kind="snapshot-test",
            command_or_procedure="head moved acceptance fallback",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=initial,
            author_id="snapshot-head-moved-author",
            reviewer_id="snapshot-head-moved-reviewer",
            evidence=("The head-moved successor retains its invalidation authority.",),
            reviewed_at=observed_at,
        )
    )
    finalization = DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            operation_id=operation_id,
            change_id=change_id,
            exact_head=initial,
            authority_digest=runtime.authority_digest,
            result_digests=("a" * 64,),
            observations=(observation,),
            review=review,
            finalized_at=observed_at,
        )
    )
    snapshot_frontier = snapshot.frontier.model_copy(update={"finalization": finalization, "published_head": initial})
    local_frontier = snapshot_frontier.model_copy(
        update={
            "finalization": None,
            "finalization_invalidation": DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=change_id,
                    finalization_id=finalization.finalization_id,
                    expected_head=finalization.exact_head,
                    observed_head="c" * 40,
                    invalidated_at=observed_at,
                )
            ),
            "change_disposition": DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION,
                change_id=change_id,
                entered_from=DeliveryChangeStage.AWAITING_MERGE,
                recorded_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
                diagnostics=("provider pull request head differs from finalized Change head",),
                acceptance_reason=DeliveryAcceptanceAttentionReason.HEAD_MOVED,
            ),
        }
    )
    _commit_descendant(worktree, "head-moved.txt", "head moved")

    assert _is_unpublished_acceptance_attention_successor(snapshot_frontier, local_frontier)
    assert not _is_unpublished_acceptance_attention_successor(
        snapshot_frontier,
        local_frontier.model_copy(update={"finalization": finalization}),
    )
    with patch(
        "owlbear_delivery.delivery_application_loader._remote_branch_head",
        return_value=None,
    ):
        assert _fetch_snapshot_change_head(
            snapshot,
            _startup_config(),
            repository,
            allow_local_branch=True,
            allow_local_descendant=True,
        ) == (snapshot.change_head, False)


def test_loader_accepts_finalized_snapshot_when_remote_change_branch_was_deleted(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-finalized-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    observed_at = datetime(2026, 8, 23, 12, tzinfo=UTC)
    operation_id = "finalize-state-finalized-fallback"
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=operation_id,
            exact_commit=initial,
            observation_kind="snapshot-test",
            command_or_procedure="finalized snapshot target fallback",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=initial,
            author_id="snapshot-finalization-author",
            reviewer_id="snapshot-finalization-reviewer",
            evidence=("The finalized snapshot exact head is present on the target.",),
            reviewed_at=observed_at,
        )
    )
    finalization = DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            operation_id=operation_id,
            change_id=change_id,
            exact_head=initial,
            authority_digest=runtime.authority_digest,
            result_digests=("a" * 64,),
            observations=(observation,),
            review=review,
            finalized_at=observed_at,
        )
    )
    finalized_frontier = snapshot.frontier.model_copy(
        update={
            "bindings": (
                OutcomeAuthorityBinding(
                    outcome_id="OUT-001",
                    plan_scope_id="SCOPE-001",
                    stage=DeliveryStage.COMPLETED,
                ),
            ),
            "finalization": finalization,
        }
    )
    finalized_snapshot = snapshot.model_copy(update={"frontier": finalized_frontier})

    with patch(
        "owlbear_delivery.delivery_application_loader._remote_branch_head",
        return_value=None,
    ):
        assert _fetch_snapshot_change_head(finalized_snapshot, _startup_config(), repository) == (initial, False)

    assert finalized_snapshot.frontier.ready is None
    assert finalized_snapshot.frontier.change_completion is None


def test_loader_does_not_defer_completed_remote_descendant_drift(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-completed"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    completed = snapshot.model_copy(
        update={
            "frontier": snapshot.frontier.model_copy(
                update={
                    "change_completion": DeliveryChangeCompletion(
                        completion_id="a" * 64,
                        completed_at=datetime(2026, 8, 23, tzinfo=UTC),
                    )
                }
            )
        }
    )
    descendant = _commit_descendant(worktree, "completed-descendant.txt", "completed descendant")

    assert not _can_defer_remote_state_reconciliation(completed, repository, descendant)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader._remote_branch_head",
            return_value=descendant,
        ),
        pytest.raises(
            DeliveryApplicationLoadError,
            match="remote Change branch differs from Delivery-state snapshot: state-completed",
        ),
    ):
        _fetch_snapshot_change_head(completed, _startup_config(), repository)


def test_loader_rejects_divergent_remote_branch_drift(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-divergent"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    reviewed = _commit_descendant(worktree, "reviewed.txt", "reviewed state")
    manager.record_reviewed(change_id, reviewed)
    snapshot = _snapshot(runtime, manager, change_id)
    divergent = _commit_descendant(repository, "divergent.txt", "divergent state")

    assert initial != divergent
    assert not _can_defer_remote_state_reconciliation(snapshot, repository, divergent)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader._remote_branch_head",
            return_value=divergent,
        ),
        pytest.raises(
            DeliveryApplicationLoadError,
            match="remote Change branch differs from Delivery-state snapshot: state-divergent",
        ),
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)


def test_state_snapshot_rejects_legacy_adoption_receipt_schema(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "legacy-snapshot"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    adoption = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="legacy-snapshot-adoption",
        change_id=change_id,
        branch=manager.show(change_id).branch,
        expected_head="a" * 40,
        adopted_head="b" * 40,
    )
    legacy_adoption = adoption.model_dump(mode="json")
    legacy_adoption["schema_version"] = 1
    legacy_adoption.pop("provenance")
    legacy_adoption["receipt_id"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in legacy_adoption.items() if key != "receipt_id"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    payload = snapshot.model_dump(mode="json")
    payload["frontier"]["external_head_adoption_receipt"] = legacy_adoption

    payload["snapshot_id"] = ""
    payload["snapshot_id"] = hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()

    with pytest.raises(ValueError, match="schema_version"):
        DeliveryStateSnapshot.model_validate_json(json.dumps(payload))


def test_state_snapshot_rejects_legacy_target_sync_receipt_schema(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "legacy-target-sync"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    target_sync = {
        "schema_version": 1,
        "receipt_id": "a" * 64,
        "operation_id": "legacy-target-sync",
        "change_id": change_id,
        "integration_target": "main",
        "expected_target": "b" * 40,
        "target_head": "b" * 40,
        "change_head_before": "a" * 40,
        "merged_head": "c" * 40,
        "merge_commit": True,
    }
    target_sync["receipt_id"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in target_sync.items() if key != "receipt_id"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    payload = snapshot.model_dump(mode="json")
    payload["frontier"]["target_sync_receipt"] = target_sync
    payload["snapshot_id"] = ""
    payload["snapshot_id"] = hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()

    with pytest.raises(ValueError, match="schema_version"):
        DeliveryStateSnapshot.model_validate_json(json.dumps(payload))


def test_state_publisher_round_trips_and_replays_without_primary_checkout_changes(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-change")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-change", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    before = (_git(repository, "rev-parse", "HEAD"), _git(repository, "status", "--porcelain"))

    receipt = _publish(publisher, runtime, manager, "state-change", "a" * 64, "state-one")
    replayed = _publish(publisher, runtime, manager, "state-change", "a" * 64, "state-one")
    snapshots = publisher.read_snapshots()

    assert replayed == receipt
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_id == receipt.snapshot_id
    assert snapshots[0].change_id == "state-change"
    assert snapshots[0].contract == contract
    assert snapshots[0].frontier == DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    assert _git(repository, "rev-parse", "HEAD") == before[0] == initial
    assert _git(repository, "status", "--porcelain") == before[1]


def test_state_snapshot_accepts_terminal_completion_projection(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-complete"
    contract, _intent, _design = _contract(change_id)
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier_path.write_bytes(
        (
            json.dumps(
                DeliveryFrontier(
                    bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),),
                ).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
    )
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    observed_at = datetime(2026, 8, 23, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id="finalize-state-complete",
            exact_commit=initial,
            observation_kind="snapshot-test",
            command_or_procedure="terminal snapshot construction",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=initial,
            author_id="snapshot-author",
            reviewer_id="snapshot-reviewer",
            evidence=("The terminal snapshot authority is internally consistent.",),
            reviewed_at=observed_at,
        )
    )
    finalization = DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            operation_id="finalize-state-complete",
            change_id=change_id,
            exact_head=initial,
            authority_digest=runtime.authority_digest,
            result_digests=("a" * 64,),
            observations=(observation,),
            review=review,
            finalized_at=observed_at,
        )
    )
    ready_values = {
        "schema_version": 1,
        "operation_id": "ready-state-complete",
        "change_id": change_id,
        "finalization_id": finalization.finalization_id,
        "repository": "example/project",
        "number": 1,
        "node_id": "PR_node_complete",
        "head_sha": initial,
        "draft": False,
        "observed_at": observed_at,
        "provider_evidence_digest": "b" * 64,
    }
    ready_candidate = PullRequestReadyReceipt.model_construct(receipt_id="0" * 64, **ready_values)
    ready = PullRequestReadyReceipt(
        receipt_id=hashlib.sha256(
            json.dumps(
                ready_candidate.model_dump(mode="json", exclude={"receipt_id"}),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        **ready_values,
    )
    merged_at = datetime(2026, 8, 23, 12, 1, tzinfo=UTC)
    latch = DeliveryMergedPullRequestLatch(
        change_id=change_id,
        finalization_id=finalization.finalization_id,
        ready_receipt_id=ready.receipt_id,
        acceptance_observation_id="c" * 64,
        provider_evidence_digest="d" * 64,
        repository="example/project",
        number=1,
        node_id="PR_node_complete",
        base_branch="main",
        head_sha=initial,
        accepted_merge_commit="e" * 40,
        merged_at=merged_at,
    )
    completion = CompletionReceipt.create(
        CompletionEvidence(
            change_id=change_id,
            finalization_receipt_id=finalization.finalization_id,
            finalized_change_head=initial,
            repository_identity="example/project",
            pull_request_identity=CompletionPullRequestIdentity(number=1, node_id="PR_node_complete"),
            accepted_target_ref="main",
            accepted_merge_commit=latch.accepted_merge_commit,
            merged_at=merged_at,
            acceptance_observation_id=latch.acceptance_observation_id,
            review_receipt_ids=(review.review_id,),
            completed_at=datetime(2026, 8, 23, 12, 2, tzinfo=UTC),
        )
    )
    display = CompletionDisplayMetadata.create(
        change_id=change_id,
        completion_id=completion.completion_id,
        title=contract.title,
        outcome_titles=tuple(outcome.title for outcome in contract.outcomes),
        outcome_promises=tuple(outcome.promise for outcome in contract.outcomes),
    )
    completion_root = state_root / "completions" / change_id
    completion_root.mkdir(parents=True)
    (completion_root / f"{completion.completion_id}.json").write_text(
        completion.model_dump_json(),
        encoding="utf-8",
    )
    (completion_root / "display.json").write_text(display.model_dump_json(), encoding="utf-8")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
            ),
        ),
        published_head=initial,
        finalization=finalization,
        ready=ready,
        merged_pull_request_latch=latch,
        change_completion=DeliveryChangeCompletion(
            completion_id=completion.completion_id,
            completed_at=completion.completed_at,
        ),
    )
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    snapshot = DeliveryStateSnapshot.create(
        operation_id="snapshot-state-complete",
        change_id=change_id,
        package_id="f" * 64,
        coordination=coordination,
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        sequence=1,
        parent_snapshot_id=None,
        base_head=None,
        captured_at=observed_at,
    )

    assert snapshot.frontier.change_completion is not None
    assert snapshot.completion is not None
    assert snapshot.completion.receipt.change_id == change_id
    assert snapshot.completion.receipt.completion_id == snapshot.frontier.change_completion.completion_id


def test_state_publisher_rejects_active_claims_and_stale_remote_head(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-reject")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-reject", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    frontier_path = runtime._frontier_path  # noqa: SLF001
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    active = DeliveryActiveClaim(
        attempt_id="attempt",
        claim_id="claim",
        owner_id="owner",
        process_id="process",
        started_at="2026-08-23T00:00:00Z",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    frontier_path.write_bytes(
        (
            json.dumps(
                frontier.model_copy(
                    update={
                        "bindings": (
                            frontier.bindings[0].model_copy(
                                update={"active_claim": active, "stage": DeliveryStage.PLANNING}
                            ),
                        )
                    }
                ).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
    )

    with pytest.raises(DeliveryStatePublicationError, match="active Outcome claim"):
        _publish(publisher, runtime, manager, "state-reject", "b" * 64, "state-reject-one")

    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    first = _publish(publisher, runtime, manager, "state-reject", "b" * 64, "state-reject-one")

    with pytest.raises(DeliveryStateConflictError, match="branch changed"):
        _publish(
            publisher,
            runtime,
            manager,
            "state-reject",
            "c" * 64,
            "state-reject-two",
            expected_remote_head="0" * 40,
        )

    assert first.published_head != "0" * 40
    assert isinstance(publisher.read_snapshot("state-reject"), DeliveryStateSnapshot)


def test_state_publisher_exposes_response_unknown_and_replays_after_remote_push(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-response-unknown")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-response-unknown", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    with (
        patch.object(
            publisher,
            "_remote_head",
            side_effect=[None, DeliveryStatePublicationError("remote observation failed", retry_safe=True)],
        ),
        pytest.raises(DeliveryStateResponseUnknownError, match="could not be verified"),
    ):
        _publish(publisher, runtime, manager, "state-response-unknown", "d" * 64, "state-unknown")

    replayed = _publish(publisher, runtime, manager, "state-response-unknown", "d" * 64, "state-unknown")

    assert replayed.snapshot_id == publisher.read_snapshot("state-response-unknown").snapshot_id


def test_state_publisher_repairs_invalid_snapshot_and_replays_append_only(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-repair")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-repair", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    initial = _publish(publisher, runtime, manager, "state-repair", "e" * 64, "state-repair-initial")
    valid = publisher.read_snapshot("state-repair")
    assert valid is not None
    invalid = valid.model_copy(
        update={
            "snapshot_id": "0" * 64,
            "sequence": 999,
            "parent_snapshot_id": "f" * 64,
            "base_head": "e" * 40,
        }
    )
    invalid_commit = publisher._commit_snapshot(initial.published_head, invalid)  # noqa: SLF001
    publisher._push_snapshot(invalid_commit, initial.published_head)  # noqa: SLF001
    runtime.capture_publication_attention(
        datetime(2026, 8, 23, 0, 30, tzinfo=UTC),
        ("local frontier is newer than the invalid remote snapshot",),
    )

    repaired = publisher.repair_snapshot(
        change_id="state-repair",
        package_id="e" * 64,
        coordination=manager.show("state-repair"),
        runtime=runtime,
        admission=_admission(runtime, manager, "state-repair"),
        operation_id="state-repair-current-schema",
        captured_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
        expected_remote_head=invalid_commit,
    )
    replayed = publisher.repair_snapshot(
        change_id="state-repair",
        package_id="e" * 64,
        coordination=manager.show("state-repair"),
        runtime=runtime,
        admission=_admission(runtime, manager, "state-repair"),
        operation_id="state-repair-current-schema",
        captured_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
        expected_remote_head=invalid_commit,
    )

    restored = publisher.read_snapshot("state-repair")
    assert restored is not None
    assert isinstance(repaired, DeliveryStateRepairReceipt)
    assert replayed == repaired
    assert repaired.expected_remote_head == invalid_commit
    assert repaired.previous_snapshot_id == invalid.snapshot_id
    assert repaired.repaired_snapshot_id == restored.snapshot_id
    assert restored.sequence == valid.sequence + 1
    assert restored.parent_snapshot_id == invalid.snapshot_id
    assert restored.frontier.change_disposition is not None
    assert publisher.read_snapshot_inventory().diagnostics == ()


def test_state_publisher_repairs_snapshot_after_another_change_published(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract_a, _intent_a, _design_a = _contract("state-repair-a")
    runtime_a, manager_a, _worktree_a = _runtime(tmp_path, repository, "state-repair-a", contract_a)
    contract_b, _intent_b, _design_b = _contract("state-repair-b")
    runtime_b, manager_b, _worktree_b = _runtime(tmp_path, repository, "state-repair-b", contract_b)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    _first_a = _publish(publisher, runtime_a, manager_a, "state-repair-a", "a" * 64, "state-repair-a-initial")
    first_b = _publish(publisher, runtime_b, manager_b, "state-repair-b", "b" * 64, "state-repair-b-initial")
    valid_a = publisher.read_snapshot("state-repair-a")
    assert valid_a is not None
    invalid_a = valid_a.model_copy(
        update={
            "snapshot_id": "0" * 64,
            "sequence": 999,
            "parent_snapshot_id": "f" * 64,
        }
    )
    invalid_commit = publisher._commit_snapshot(first_b.published_head, invalid_a)  # noqa: SLF001
    publisher._push_snapshot(invalid_commit, first_b.published_head)  # noqa: SLF001
    runtime_a.capture_publication_attention(
        datetime(2026, 8, 23, 0, 30, tzinfo=UTC),
        ("local frontier is newer than the invalid remote snapshot",),
    )

    repaired = publisher.repair_snapshot(
        change_id="state-repair-a",
        package_id="a" * 64,
        coordination=manager_a.show("state-repair-a"),
        runtime=runtime_a,
        admission=_admission(runtime_a, manager_a, "state-repair-a"),
        operation_id="state-repair-a-current-schema",
        captured_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
        expected_remote_head=invalid_commit,
    )

    assert repaired.previous_snapshot_id == invalid_a.snapshot_id
    restored = publisher.read_snapshot("state-repair-a")
    assert restored is not None
    assert restored.sequence == valid_a.sequence + 1
    assert restored.parent_snapshot_id == invalid_a.snapshot_id


def test_remote_state_bootstrap_reconstructs_fresh_clone(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "bootstrap-change"
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_root = repository / ".owlbear/delivery/packages"
    package_store = DesignPackageStore(package_root, repository)
    package = package_store.create(change_id, intent, design)
    contract_bytes = (
        json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    package_store.publish_contract(change_id, package.package_id, contract_bytes, lambda *_content: None)
    package = package_store.read_verified(change_id)
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "bootstrap-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    state_receipt = publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="bootstrap-state",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh)

    restored = application.read_design_session(change_id)
    assert restored.package_id == package.package_id
    runtime_root = fresh / ".owlbear/delivery/runtime"
    assert (runtime_root / "changes" / change_id / "contract.json").is_file()
    assert (runtime_root / "changes" / change_id / "frontier.json").is_file()
    assert (runtime_root / "changes" / change_id / "admission.json").is_file()
    assert _git(fresh, "rev-parse", f"refs/heads/owlbear/change/{change_id}") == snapshot.snapshot_head
    assert state_receipt.published_head != "0" * 40
    assert _git(fresh / ".owlbear/delivery/worktrees" / change_id, "status", "--porcelain") == ""
    assert application.list_work_items()

    frontier_path = runtime_root / "changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
    frontier_path.write_bytes(
        (
            json.dumps(
                frontier.model_copy(update={"published_head": "1" * 40}).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
    )
    degraded = load_delivery_application(config, workspace_root=fresh)
    health = degraded.delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == change_id and diagnostic.code == "remote-state-reconciliation-required"
        for diagnostic in health.diagnostics
    )
    assert degraded.list_work_items() == ()
