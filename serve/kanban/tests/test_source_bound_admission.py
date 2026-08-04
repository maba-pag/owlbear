from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from owlbear_kanban import (
    DeliveryAdmissionConflictError,
    DeliveryAdmissionRequest,
    DeliveryAuthorityRegistry,
    DeliveryFrontier,
    DeliveryOutputKind,
    DeliveryOutputReference,
    DeliveryStage,
    DesignPackageManifest,
    DesignPackageStore,
    OutcomeAuthorityBinding,
)

_GIT = "/usr/bin/git"


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
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


def _request() -> DeliveryAdmissionRequest:
    return DeliveryAdmissionRequest(change_id="source-bound-change", active_claim_ids=())


def _canonical(model: DeliveryFrontier) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


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
        interrupted.admit(_request())

    delivery_root = target_root / "delivery/changes/source-bound-change"
    assert (delivery_root / "contract.json").is_file()
    assert not (delivery_root / "admission.json").exists()

    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    recovered = registry.admit(_request())
    replayed = registry.admit(_request())

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
    assert not (target_root / "changes/source-bound-change").exists()


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
    assert not list((active_root / ".runtime-transactions").glob("*.yaml"))


def test_revision_preserves_unchanged_binding_and_invalidates_changed_dependents(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *_sources())
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    first = registry.admit(_request())
    populated = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=binding.outcome_id,
                plan_scope_id=binding.plan_scope_id,
                stage=DeliveryStage.IMPLEMENTATION,
                assembly_required=True,
                task_ids=(f"TASK-{index:03}",),
                result_ids=(f"RESULT-{index:03}",),
                output=DeliveryOutputReference(
                    output_id=f"OUTPUT-{index:03}",
                    claim_id=f"CLAIM-{index:03}",
                    stage=DeliveryStage.PLANNING,
                    kind=DeliveryOutputKind.PLANNING,
                    digest=f"{index}" * 64,
                ),
            )
            for index, binding in enumerate(first.frontier.bindings, start=1)
        )
    )
    delivery_root = target_root / "delivery/changes/source-bound-change"
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

    revised = registry.admit(_request())

    assert revised.carry_forward is not None
    assert revised.carry_forward.preserved_outcome_ids == ("OUT-003",)
    assert revised.carry_forward.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    bindings = {binding.outcome_id: binding for binding in revised.frontier.bindings}
    assert bindings["OUT-001"].task_ids == bindings["OUT-001"].result_ids == ()
    assert bindings["OUT-002"].task_ids == bindings["OUT-002"].result_ids == ()
    assert bindings["OUT-001"].stage == bindings["OUT-002"].stage == DeliveryStage.PLANNING
    assert bindings["OUT-001"].output is bindings["OUT-002"].output is None
    assert bindings["OUT-003"] == populated.bindings[2]
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
    first = registry.admit(_request())
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
                active_claim_ids=("active-claim",),
            )
        )

    assert (target_root / "delivery/changes/source-bound-change/contract.json").read_bytes() == first.contract_bytes
