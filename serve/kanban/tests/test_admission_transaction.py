from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest
import yaml

from owlbear_kanban import (
    AdmissionConflictError,
    AdmissionEvidence,
    AdmissionPublicationError,
    JobRecord,
    JobStore,
    ReceiptStore,
    load_change,
    plan_jobs,
    validate_and_admit,
)
from owlbear_kanban.change import AdmissionMetadata
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError


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


def _snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".storage.lock"
    }


def test_validate_and_admit_persists_evidence_and_rejects_different_replay(tmp_path: Path) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()

    receipt, generation, assessment = validate_and_admit(revision, evidence, work_root, receipt_id="admission-001")
    sequence_before_replay = (work_root / "job-sequence.yaml").read_bytes()
    replayed_receipt, replayed_generation, replayed_assessment = validate_and_admit(
        revision,
        evidence,
        work_root,
        receipt_id="admission-001",
    )

    assert receipt is not None
    assert generation is not None
    assert receipt.payload["evidence"] == evidence.model_dump(mode="python")
    assert replayed_receipt == receipt
    assert replayed_generation == generation
    assert replayed_assessment == assessment
    assert (work_root / "job-sequence.yaml").read_bytes() == sequence_before_replay
    assert tuple(stored.job for stored in JobStore(work_root).list()) == tuple(
        JobRecord(schema_version=1, **job.model_dump()) for job in generation.jobs
    )
    assert JobStore(work_root).reserve_job_ids(1).job_ids == (generation.jobs[-1].job_id + 1,)

    different_evidence = evidence.model_copy(
        update={"baseline": {"commands": ("pytest", "ruff"), "digest": revision.delivery_digest}}
    )
    authority_before_conflict = _snapshot(revision.source_dir)
    work_before_conflict = _snapshot(work_root)
    with pytest.raises(AdmissionConflictError):
        validate_and_admit(revision, different_evidence, work_root, receipt_id="admission-001")
    assert _snapshot(revision.source_dir) == authority_before_conflict
    assert _snapshot(work_root) == work_before_conflict

    persisted = ReceiptStore(revision).read("admission-001")
    assert persisted.receipt == receipt


def test_non_admitted_evidence_does_not_touch_authority_or_work_roots(tmp_path: Path) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)
    work_root = tmp_path / "missing-work"
    rejected = evidence.model_copy(update={"approval": {"approved": False, "digest": revision.delivery_digest}})
    authority_before = _snapshot(revision.source_dir)

    receipt, generation, assessment = validate_and_admit(revision, rejected, work_root)

    assert receipt is None
    assert generation is None
    assert not assessment.admitted
    assert _snapshot(revision.source_dir) == authority_before
    assert not work_root.exists()


@pytest.mark.parametrize("location", ["active", "archive"])
def test_explicit_job_id_collision_fails_without_admission_publication(tmp_path: Path, location: str) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    conflicting = plan_jobs(
        revision,
        "other-admission",
        range(1, len(revision.graph.nodes) + 1),
        timestamp="2026-07-25T12:00:00Z",
    )
    store = JobStore(work_root)
    stored = store.materialize(conflicting.model_copy(update={"jobs": (conflicting.jobs[0],)}))[0]
    if location == "archive":
        store.archive(stored.job.job_id, stored.token)
    authority_before = _snapshot(revision.source_dir)
    work_before = _snapshot(work_root)

    with pytest.raises(AdmissionConflictError):
        validate_and_admit(
            revision,
            evidence,
            work_root,
            receipt_id="admission-001",
            job_ids=range(1, len(revision.graph.nodes) + 1),
        )

    assert _snapshot(revision.source_dir) == authority_before
    assert _snapshot(work_root) == work_before


def test_automatic_allocation_retries_one_stale_reservation(tmp_path: Path, monkeypatch) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    node_count = len(revision.graph.nodes)
    competing = JobStore(work_root).reserve_job_ids(node_count)
    original_commit = RuntimeTransaction.commit
    intervened = False

    def commit_after_competitor(self, *, failure=None) -> None:
        nonlocal intervened
        if not intervened and self._transaction_id.startswith("admission-"):
            intervened = True
            original_commit(RuntimeTransaction(work_root, "competing-reservation", (competing.participant,)))
        original_commit(self, failure=failure)

    monkeypatch.setattr(RuntimeTransaction, "commit", commit_after_competitor)

    receipt, generation, assessment = validate_and_admit(revision, evidence, work_root, receipt_id="admission-001")

    assert receipt is not None
    assert generation is not None
    assert assessment.admitted
    assert generation.jobs[0].job_id == node_count + 1
    assert generation.jobs[-1].job_id == node_count * 2
    assert tuple(item.job.job_id for item in JobStore(work_root).list()) == tuple(
        range(node_count + 1, node_count * 2 + 1)
    )


def test_automatic_allocation_reports_second_stale_conflict_without_publication(tmp_path: Path, monkeypatch) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    authority_before = _snapshot(revision.source_dir)
    work_before = _snapshot(work_root)
    attempts = 0

    def always_conflict(_transaction, *, failure=None) -> None:
        nonlocal attempts
        assert failure is None
        attempts += 1
        raise TransactionConflictError

    monkeypatch.setattr(RuntimeTransaction, "commit", always_conflict)

    with pytest.raises(AdmissionConflictError):
        validate_and_admit(revision, evidence, work_root, receipt_id="admission-001")

    assert attempts == 2
    assert _snapshot(revision.source_dir) == authority_before
    assert _snapshot(work_root) == work_before


@pytest.mark.parametrize("failure_stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_retry_recovers_interrupted_cross_root_admission(tmp_path: Path, failure_stage: str) -> None:
    revision, evidence = _revision_and_evidence(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()

    def interrupt(stage: str) -> None:
        if stage == failure_stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(AdmissionPublicationError) as exc_info:
        validate_and_admit(revision, evidence, work_root, receipt_id="admission-001", failure=interrupt)

    assert isinstance(exc_info.value.cause, RuntimeError)
    manifests = list((work_root / ".runtime-transactions").glob("*.yaml"))
    assert len(manifests) == 1
    manifest = yaml.safe_load(manifests[0].read_text(encoding="utf-8"))
    assert {entry["root"] for entry in manifest["participants"]} == {
        str(work_root.resolve()),
        str(revision.source_dir.resolve()),
    }

    receipt, generation, assessment = validate_and_admit(revision, evidence, work_root, receipt_id="admission-001")

    assert receipt is not None
    assert generation is not None
    assert assessment.admitted
    assert ReceiptStore(revision).read("admission-001").receipt == receipt
    assert tuple(item.job.job_id for item in JobStore(work_root).list()) == tuple(job.job_id for job in generation.jobs)
    assert not list((work_root / ".runtime-transactions").glob("*.yaml"))


def test_runtime_open_reports_malformed_pending_transaction_manifest(tmp_path: Path) -> None:
    revision, _ = _revision_and_evidence(tmp_path)
    transaction_directory = revision.source_dir / ".runtime-transactions"
    transaction_directory.mkdir()
    (transaction_directory / "pending.yaml").write_text("participants: [", encoding="utf-8")

    reopened = load_change(revision.source_dir.parent, revision.change_id)

    assert reopened.revision is None
    assert reopened.diagnostics[0].code.value == "ERR_CHANGE_SCHEMA_INVALID"
    assert reopened.diagnostics[0].detail == "pending transaction manifest is invalid"
