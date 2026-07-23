from __future__ import annotations

from shutil import copytree
from pathlib import Path

import pytest

from owlbear_kanban import (
    AdmissionConflictError,
    AdmissionEvidence,
    AdmissionPublicationError,
    ReceiptStore,
    load_change,
    validate_and_admit,
)
from owlbear_kanban.change import AdmissionMetadata


def _revision_and_evidence(tmp_path: Path):
    changes_dir = tmp_path / "changes"
    copytree(Path(".owlbear/changes/replace-delivery-pipeline"), changes_dir / "replace-delivery-pipeline")
    result = load_change(changes_dir, "replace-delivery-pipeline")
    assert result.revision is not None
    revision = result.revision.model_copy(
        update={
            "graph": result.revision.graph.model_copy(
                update={
                    "admission": AdmissionMetadata(
                        state="admitted",
                        delivery_digest=result.revision.delivery_digest,
                        receipt="admission-001",
                        limits=("bootstrap",),
                    )
                }
            )
        }
    )
    challenge = {
        entity.id: {"disposition": "pass", "evidence": entity.id}
        for section in ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
        for entity in getattr(revision.graph, section)
    }
    return revision, AdmissionEvidence(
        digest=revision.delivery_digest,
        challenge=challenge,
        baseline={"commands": ("pytest",), "digest": revision.delivery_digest},
        approval={"approved": True, "digest": revision.delivery_digest},
        limits=("bootstrap",),
    )


def test_validate_and_admit_persists_evidence_and_rejects_different_replay(tmp_path: Path) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)

    receipt, generation, assessment = validate_and_admit(revision, evidence, receipt_id="admission-001")
    replayed_receipt, replayed_generation, replayed_assessment = validate_and_admit(
        revision,
        evidence,
        receipt_id="admission-001",
    )

    assert receipt is not None
    assert generation is not None
    assert receipt.payload["evidence"] == evidence.model_dump(mode="python")
    assert replayed_receipt == receipt
    assert replayed_generation == generation
    assert replayed_assessment == assessment

    different_evidence = evidence.model_copy(
        update={"baseline": {"commands": ("pytest", "ruff"), "digest": revision.delivery_digest}}
    )
    with pytest.raises(AdmissionConflictError):
        validate_and_admit(revision, different_evidence, receipt_id="admission-001")

    persisted = ReceiptStore(revision).read("admission-001")
    assert persisted.receipt == receipt


def test_runtime_open_recovers_interrupted_admission_participant_publication(tmp_path: Path) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(AdmissionPublicationError) as exc_info:
        validate_and_admit(revision, evidence, receipt_id="admission-001", failure=interrupt)

    generation_path = revision.source_dir / "jobs" / "admission-001.yaml"
    assert isinstance(exc_info.value.cause, RuntimeError)
    assert list((revision.source_dir / ".runtime-transactions").glob("*.yaml"))

    reopened = load_change(revision.source_dir.parent, revision.change_id)
    assert reopened.revision is not None
    recovered_receipt = ReceiptStore(reopened.revision).read("admission-001")

    assert recovered_receipt.receipt is not None
    assert recovered_receipt.receipt.receipt_id == "admission-001"
    assert recovered_receipt.receipt.payload["evidence"] == evidence.model_dump(mode="python")
    assert generation_path.exists()
    assert not list((revision.source_dir / ".runtime-transactions").glob("*.yaml"))


def test_runtime_open_reports_malformed_pending_transaction_manifest(tmp_path: Path) -> None:
    revision, _ = _revision_and_evidence(tmp_path)
    transaction_directory = revision.source_dir / ".runtime-transactions"
    transaction_directory.mkdir()
    (transaction_directory / "pending.yaml").write_text("participants: [", encoding="utf-8")

    reopened = load_change(revision.source_dir.parent, revision.change_id)

    assert reopened.revision is None
    assert reopened.diagnostics[0].code.value == "ERR_CHANGE_SCHEMA_INVALID"
    assert reopened.diagnostics[0].detail == "pending transaction manifest is invalid"
