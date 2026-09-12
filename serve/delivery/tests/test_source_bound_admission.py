from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery import (
    DeliveryAdmissionConflictError,
    DeliveryAdmissionRequest,
    DeliveryAuthorityRegistry,
    DeliveryBlock,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFrontier,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOutputKind,
    DeliveryOutputReference,
    DeliveryPendingCheckpoint,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestResolution,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DesignPackageManifest,
    DesignPackageStore,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.git_executable import resolve_git_executable

_GIT = resolve_git_executable()


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        (_GIT, "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    path = tmp_path / "repository"
    path.mkdir()
    _git(path, "init", "-b", "product")
    _git(path, "config", "user.name", "Source Admission Test")
    _git(path, "config", "user.email", "source-admission@example.invalid")
    (path / "product.txt").write_text("product\n", encoding="utf-8")
    _git(path, "add", "product.txt")
    _git(path, "commit", "-m", "product baseline")
    return path


def _commitment(identity: str, statement: str) -> str:
    return f"""```yaml target-contract
kind: commitment
id: {identity}
class: agreed-path
provenance: source admission test
statement: {statement}
```
"""


def _outcome(
    identity: str,
    commitment: str,
    dependencies: tuple[str, ...] = (),
) -> str:
    dependency_list = ", ".join(dependencies)
    return f"""```yaml target-contract
kind: outcome
id: {identity}
title: Result {identity}
promise: Deliver {identity}.
acceptance: [{identity} is observable.]
commitments: [{commitment}]
dependencies: [{dependency_list}]
```
"""


def _sources(*, first_statement: str = "Keep the first result stable.") -> tuple[bytes, bytes]:
    intent = "\n".join(
        (
            "# Source-Bound Change\n",
            _commitment("COM-001", first_statement),
            _commitment("COM-002", "Keep the dependent result stable."),
            _outcome("OUT-001", "COM-001"),
            _outcome("OUT-002", "COM-002", ("OUT-001",)),
        )
    )
    design = "\n".join(
        (
            "# Source-Bound Architecture\n",
            _commitment("COM-003", "Keep the independent result stable."),
            _outcome("OUT-003", "COM-003"),
        )
    )
    return intent.encode(), design.encode()


def _request(package_store: DesignPackageStore) -> DeliveryAdmissionRequest:
    package = package_store.read_verified("source-bound-change")
    authored_manifest = DesignPackageManifest.from_content(
        "source-bound-change",
        package.intent_bytes,
        package.design_bytes,
    )
    return DeliveryAdmissionRequest(
        change_id="source-bound-change",
        expected_package_id=hashlib.sha256(authored_manifest.canonical_bytes()).hexdigest(),
        active_claim_ids=(),
    )


def test_admission_rejects_stale_approved_package_before_publication(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    intent_bytes, design_bytes = _sources()
    package = package_store.create("source-bound-change", intent_bytes, design_bytes)
    package_store.revise(
        "source-bound-change",
        package.package_id,
        intent_bytes + b"\nRevised after approval.\n",
        design_bytes,
    )
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")

    with pytest.raises(DeliveryAdmissionConflictError, match="Design package changed before admission"):
        registry.admit(
            DeliveryAdmissionRequest(
                change_id="source-bound-change",
                expected_package_id=package.package_id,
                active_claim_ids=(),
            )
        )

    assert not (target_root / "changes/source-bound-change").exists()


def _canonical(model: DeliveryFrontier) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _task_result(
    result_id: str,
    change_id: str,
    authority_digest: str,
    task: DeliveryTaskDefinition,
    completed_commit: str,
) -> DeliveryTaskResult:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=task.task_id,
            exact_commit=completed_commit,
            observation_kind="pytest",
            command_or_procedure="source-bound admission fixture validation",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=completed_commit,
            author_id="Source admission test author",
            reviewer_id="Source admission test reviewer",
            evidence=("The exact fixture commit satisfies task authority.",),
            reviewed_at=observed_at,
        )
    )
    return DeliveryTaskResult(
        result_id=result_id,
        change_id=change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
        observations=(observation,),
        review=review,
    )


def test_admission_recovers_receipt_last_publication_and_replays_exact_sources(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    intent_bytes, design_bytes = _sources()
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", intent_bytes, design_bytes)

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            message = "receipt-last interruption"
            raise RuntimeError(message)

    interrupted = DeliveryAuthorityRegistry(
        target_root,
        package_store,
        integration_target="product",
        failure=interrupt,
    )
    with pytest.raises(RuntimeError, match="receipt-last interruption"):
        interrupted.admit(_request(package_store))

    delivery_root = target_root / "changes/source-bound-change"
    assert (delivery_root / "contract.json").is_file()
    assert not (delivery_root / "admission.json").exists()

    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    recovered = registry.admit(_request(package_store))
    replayed = registry.admit(_request(package_store))

    assert recovered.replayed is True
    assert replayed == recovered
    assert recovered.receipt.checkpoint_commit == _git(
        repository,
        "rev-parse",
        "refs/owlbear/packages/source-bound-change",
    )
    assert tuple(binding.outcome_id for binding in recovered.frontier.bindings) == (
        "OUT-001",
        "OUT-002",
        "OUT-003",
    )
    assert all(binding.task_ids == binding.result_ids == () for binding in recovered.frontier.bindings)
    assert not (target_root / "delivery/changes/source-bound-change").exists()


def test_admission_preserves_staged_user_checkout_outside_declared_package_path(
    repository: Path,
    user_checkout_snapshot,
) -> None:
    active_root = repository / ".owlbear/delivery/packages"
    target_root = repository / ".owlbear/delivery/runtime"
    package_store = DesignPackageStore(active_root, repository)
    intent_bytes, design_bytes = _sources()
    package_store.create("source-bound-change", intent_bytes, design_bytes)
    _git(repository, "add", ".owlbear/delivery/packages")
    _git(repository, "commit", "-m", "author source-bound package")
    (repository / "product.txt").write_text("staged user work\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    (repository / "untracked-user.txt").write_text("untracked user work\n", encoding="utf-8")
    before = user_checkout_snapshot(
        repository,
        ("refs/owlbear/packages/source-bound-change",),
        (
            ".owlbear/delivery/packages/source-bound-change",
            ".owlbear/delivery/runtime",
        ),
    )

    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    result = registry.admit(_request(package_store))
    replayed = registry.admit(_request(package_store))

    assert replayed.replayed is True
    assert result.receipt.checkpoint_commit == _git(
        repository,
        "rev-parse",
        "refs/owlbear/packages/source-bound-change",
    )
    before.assert_unchanged(repository)


def test_rejected_package_validation_cannot_publish_during_later_recovery(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    intent_bytes, design_bytes = _sources()
    store = DesignPackageStore(active_root, repository)
    created = store.create("source-bound-change", intent_bytes, design_bytes)

    def reject(_intent: bytes, _design: bytes, _contract: bytes) -> None:
        message = "contract mismatch"
        raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="contract mismatch"):
        store.publish_contract(
            "source-bound-change",
            created.package_id,
            b'{"rejected":true}\n',
            reject,
        )

    store.checkpoint("source-bound-change")
    verified = store.read_verified("source-bound-change")
    assert verified.authority_bytes == b""
    assert not list((active_root / "transactions").glob("*.yaml"))


def test_revision_preserves_unchanged_binding_and_invalidates_changed_dependents(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *_sources())
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    first = registry.admit(_request(package_store))
    populated_bindings = []
    for index, binding in enumerate(first.frontier.bindings, start=1):
        task = DeliveryTaskDefinition(
            task_id=f"TASK-{index:03}",
            outcome_id=binding.outcome_id,
            plan_scope_id=binding.plan_scope_id,
            title=f"Produce result {index}",
            result=f"Result {index}",
            commitment_ids=(),
            dependency_ids=(),
            required_outputs=("Reviewed commit",),
            maintained_surfaces=("serve/delivery",),
            constraints=(),
            exclusions=(),
            acceptance_observations=("Result is bound",),
            proof_boundaries=("Delivery runtime",),
        )
        result = _task_result(
            f"RESULT-{index:03}",
            "source-bound-change",
            first.contract_digest,
            task,
            f"{index}" * 40,
        )
        populated_bindings.append(
            OutcomeAuthorityBinding(
                outcome_id=binding.outcome_id,
                plan_scope_id=binding.plan_scope_id,
                stage=DeliveryStage.IMPLEMENTATION,
                tasks=(task,),
                results=(result,),
                output=DeliveryOutputReference(
                    output_id=f"OUTPUT-{index:03}",
                    claim_id=f"CLAIM-{index:03}",
                    stage=DeliveryStage.PLANNING,
                    kind=DeliveryOutputKind.PLANNING,
                    digest=f"{index}" * 64,
                ),
            )
        )
    pending = DeliveryPendingCheckpoint(
        head="3" * 40,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-003",
            ),
        ),
    )
    populated = DeliveryFrontier(
        bindings=tuple(populated_bindings),
        published_head="2" * 40,
        pending_checkpoint=pending,
    )
    delivery_root = target_root / "changes/source-bound-change"
    (delivery_root / "frontier.json").write_bytes(_canonical(populated))

    revised_intent, revised_design = _sources(first_statement="Change the first result behavior.")
    package_root = active_root / "source-bound-change"
    (package_root / "intent.md").write_bytes(revised_intent)
    manifest = DesignPackageManifest.from_content(
        "source-bound-change",
        revised_intent,
        revised_design,
        first.contract_bytes,
    )
    (package_root / "manifest.json").write_bytes(manifest.canonical_bytes())

    revised = registry.admit(_request(package_store))

    assert revised.carry_forward is not None
    assert revised.carry_forward.preserved_outcome_ids == ("OUT-003",)
    assert revised.carry_forward.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    bindings = {binding.outcome_id: binding for binding in revised.frontier.bindings}
    assert bindings["OUT-001"].task_ids == bindings["OUT-001"].result_ids == ()
    assert bindings["OUT-002"].task_ids == bindings["OUT-002"].result_ids == ()
    assert bindings["OUT-001"].stage == bindings["OUT-002"].stage == DeliveryStage.PLANNING
    assert bindings["OUT-001"].output is bindings["OUT-002"].output is None
    assert bindings["OUT-001"].tasks == bindings["OUT-002"].tasks == ()
    assert bindings["OUT-001"].results == bindings["OUT-002"].results == ()
    assert bindings["OUT-003"] == populated.bindings[2]
    assert revised.frontier.published_head == "2" * 40
    assert revised.frontier.pending_checkpoint is not None
    assert revised.frontier.pending_checkpoint.head is None
    assert revised.frontier.pending_checkpoint.triggers == (pending.triggers[0], pending.triggers[2])
    revision_root = delivery_root / "revisions" / first.contract_digest
    assert {path.name for path in revision_root.iterdir()} == {
        "admission.json",
        "contract.json",
        "frontier.json",
    }


def test_revision_rejects_active_claims_before_mutation(repository: Path, tmp_path: Path) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *_sources())
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    first = registry.admit(_request(package_store))
    changed_intent, changed_design = _sources(first_statement="Changed behavior.")
    package_root = active_root / "source-bound-change"
    (package_root / "intent.md").write_bytes(changed_intent)
    manifest = DesignPackageManifest.from_content(
        "source-bound-change",
        changed_intent,
        changed_design,
        first.contract_bytes,
    )
    (package_root / "manifest.json").write_bytes(manifest.canonical_bytes())

    with pytest.raises(DeliveryAdmissionConflictError, match="active claims block"):
        registry.admit(
            DeliveryAdmissionRequest(
                change_id="source-bound-change",
                expected_package_id=_request(package_store).expected_package_id,
                active_claim_ids=("active-claim",),
            )
        )

    assert (target_root / "changes/source-bound-change/contract.json").read_bytes() == first.contract_bytes


def test_revision_can_carry_forward_one_confirmed_unresolved_gate(repository: Path, tmp_path: Path) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *_sources())
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    first = registry.admit(_request(package_store))
    delivery_root = target_root / "changes/source-bound-change"
    request = DeliveryRequest(
        request_id="REQ-001",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-001",
        summary="Complete the revised pilot.",
        resolution=DeliveryRequestResolution(
            response_text="Use the approved SharePoint and Confluence targets.",
            provenance="user-confirmed",
        ),
    )
    blocked = first.frontier.bindings[0].model_copy(
        update={
            "stage": DeliveryStage.IMPLEMENTATION,
            "block": DeliveryBlock(
                block_id="BLOCK-001",
                reason="The prior Jira pilot cannot be reused.",
                unblock_condition="Complete the old Jira pilot.",
                expected_evidence=("old pilot",),
                locators=("REQ-001",),
                request_id="REQ-001",
                resolution_note="Revise the acceptance contract.",
                resolution_locators=("REQ-001",),
            ),
            "requests": (request,),
        }
    )
    frontier = first.frontier.model_copy(update={"bindings": (blocked, *first.frontier.bindings[1:])})
    frontier_bytes = _canonical(frontier)
    (delivery_root / "frontier.json").write_bytes(frontier_bytes)

    revised_intent, revised_design = _sources(first_statement="Change the first result behavior.")
    package_root = active_root / "source-bound-change"
    (package_root / "intent.md").write_bytes(revised_intent)
    manifest = DesignPackageManifest.from_content(
        "source-bound-change",
        revised_intent,
        revised_design,
        first.contract_bytes,
    )
    (package_root / "manifest.json").write_bytes(manifest.canonical_bytes())
    revised_request = _request(package_store).model_copy(
        update={
            "expected_frontier_digest": hashlib.sha256(frontier_bytes).hexdigest(),
            "preserve_unresolved_outcome_ids": ("OUT-001",),
        }
    )

    revised = registry.admit(revised_request)

    carried = {binding.outcome_id: binding for binding in revised.frontier.bindings}["OUT-001"]
    assert revised.carry_forward is not None
    assert revised.carry_forward.carried_forward_outcome_ids == ("OUT-001",)
    assert carried.stage is DeliveryStage.PLANNING
    assert carried.block is not None
    assert carried.block.resolved is False
    assert "Jira" not in carried.block.reason
    assert "Jira" not in carried.block.unblock_condition
    assert carried.requests[0].resolution is not None
    assert carried.requests[0].resolution.provenance == "user-confirmed"
    fresh_request = carried.requests[-1]
    assert fresh_request.request_id == carried.block.request_id
    assert fresh_request.resolution is None
    assert "OUT-001" not in DeliveryRuntime(target_root, revised.contract).claimable_outcome_ids()

    runtime = DeliveryRuntime(target_root, revised.contract)
    resolved = runtime.resolve_request(
        fresh_request.request_id,
        DeliveryRequestResolution(response_text="The revised pilot is complete.", provenance="user-confirmed"),
    )

    assert resolved.request_id == fresh_request.request_id
    assert runtime.show_binding("OUT-001").block is not None
    assert runtime.show_binding("OUT-001").block.resolved is True
