from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest

from owlbear_kanban import (
    AdmissionEvidence,
    JobRecord,
    JobStore,
    evaluate_admission,
    load_change,
    validate_and_admit,
)

_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "historical-admission"
_DEFECTIVE_CASES = (
    ("r1-browser-defective", frozenset({"DV-004"})),
    ("r2-workspace-defective", frozenset({"DV-004", "DV-006"})),
    ("r3-memory-purge-defective", frozenset({"DV-007"})),
    ("r4-memory-lifecycle-defective", frozenset({"DV-004", "DV-007"})),
)
_CORRECTED_CASES = tuple(name.replace("-defective", "-corrected") for name, _ in _DEFECTIVE_CASES)
_ALL_CASES = tuple(name for name, _ in _DEFECTIVE_CASES) + _CORRECTED_CASES


def _copy_revision(tmp_path: Path, fixture_name: str):
    changes_dir = tmp_path / "changes"
    copytree(_FIXTURE_ROOT / fixture_name, changes_dir / fixture_name)
    result = load_change(changes_dir, fixture_name)

    assert result.diagnostics == ()
    assert result.revision is not None
    return result.revision


def _evidence(revision):
    assert revision.graph.admission is not None
    challenge = {
        entity.id: {"disposition": "pass", "evidence": entity.id}
        for section in ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
        for entity in getattr(revision.graph, section)
    }
    return AdmissionEvidence(
        digest=revision.delivery_digest,
        challenge=challenge,
        baseline={"commands": ("pytest",), "digest": revision.delivery_digest},
        approval={"approved": True, "digest": revision.delivery_digest},
        limits=revision.graph.admission.limits,
    )


@pytest.mark.parametrize("fixture_name", _ALL_CASES)
def test_historical_packages_use_joined_modular_authority(fixture_name: str) -> None:
    change_dir = _FIXTURE_ROOT / fixture_name

    assert not (change_dir / "graph.yaml").exists()
    assert {path.name for path in (change_dir / "delivery").iterdir()} == {
        "contracts.yaml",
        "nodes.yaml",
        "obligations.yaml",
    }

    result = load_change(_FIXTURE_ROOT, fixture_name)

    assert result.diagnostics == ()
    assert result.revision is not None
    assert result.revision.intent
    assert result.revision.design
    assert result.revision.decisions.decisions
    assert result.revision.graph.requirements
    assert result.revision.graph.interfaces
    assert result.revision.graph.nodes


@pytest.mark.parametrize(("fixture_name", "expected_codes"), _DEFECTIVE_CASES)
def test_historical_defects_fail_without_admission_publication(
    tmp_path: Path,
    fixture_name: str,
    expected_codes: frozenset[str],
) -> None:
    revision = _copy_revision(tmp_path, fixture_name)
    evidence = _evidence(revision)

    validation = evaluate_admission(revision, evidence)
    receipt, generation, admission = validate_and_admit(revision, evidence, tmp_path / "work")

    assert {finding.code for finding in validation.errors} == expected_codes
    assert {finding.code for finding in admission.errors} == expected_codes
    assert receipt is None
    assert generation is None
    assert not (revision.source_dir / "receipts").exists()
    assert not (revision.source_dir / "jobs").exists()
    assert not (tmp_path / "work").exists()


@pytest.mark.parametrize("fixture_name", _CORRECTED_CASES)
def test_corrected_historical_admission_replays_without_duplication(tmp_path: Path, fixture_name: str) -> None:
    revision = _copy_revision(tmp_path, fixture_name)
    evidence = _evidence(revision)
    work_root = tmp_path / "work"
    work_root.mkdir()

    validation = evaluate_admission(revision, evidence)
    receipt, generation, admission = validate_and_admit(
        revision,
        evidence,
        work_root,
        receipt_id="admission-historical",
    )
    replayed_receipt, replayed_generation, replayed_admission = validate_and_admit(
        revision,
        evidence,
        work_root,
        receipt_id="admission-historical",
    )

    assert validation.findings == ()
    assert admission.findings == ()
    assert receipt is not None
    assert receipt.delivery_digest == revision.delivery_digest
    assert generation is not None
    assert len(generation.jobs) == len(revision.graph.nodes)
    assert replayed_receipt == receipt
    assert replayed_generation == generation
    assert replayed_admission == admission
    assert len(tuple((revision.source_dir / "receipts").glob("*.yaml"))) == 1
    assert len(tuple((revision.source_dir / "jobs").glob("*.yaml"))) == 1
    assert tuple(stored.job for stored in JobStore(work_root).list()) == tuple(
        JobRecord(schema_version=1, **job.model_dump()) for job in generation.jobs
    )
