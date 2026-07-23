from __future__ import annotations

from shutil import copytree
from pathlib import Path

import pytest

from owlbear_kanban import AdmissionEvidence, AdmissionPublicationError, load_change, validate_and_admit


def _revision_and_evidence(tmp_path: Path):
    changes_dir = tmp_path / "changes"
    copytree(Path(".owlbear/changes/replace-delivery-pipeline"), changes_dir / "replace-delivery-pipeline")
    result = load_change(changes_dir, "replace-delivery-pipeline")
    assert result.revision is not None
    revision = result.revision
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


def test_admission_replay_recovers_interrupted_participant_publication(tmp_path: Path) -> None:
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

    receipt, generation, assessment = validate_and_admit(revision, evidence, receipt_id="admission-001")

    assert assessment.admitted
    assert receipt is not None
    assert receipt.receipt_id == "admission-001"
    assert generation is not None
    assert generation.receipt_id == "admission-001"
    assert generation_path.exists()
    assert not list((revision.source_dir / ".runtime-transactions").glob("*.yaml"))
