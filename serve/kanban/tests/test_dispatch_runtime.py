from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from owlbear_kanban import (
    DispatchDiagnostic,
    DispatchDiagnosticCode,
    DispatchOmissionReason,
    DispatchRuntime,
    JobGeneration,
    JobRecord,
    JobStore,
    NativeRuntime,
    ReceiptStore,
    RecoverExpiredClaimsRequest,
    ReleaseJobRequest,
    ShapeJob,
    StartJobRequest,
    compute_node_plan_digest,
    load_change,
)


class _History:
    changed_paths = b""

    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return self.changed_paths


@pytest.fixture
def revision():
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    return result.revision


def _record(revision, job_id: int) -> JobRecord:
    return JobRecord(
        schema_version=1,
        job_id=job_id,
        kind="build",
        priority=7,
        created_at="2026-07-24T00:00:00Z",
        updated_at="2026-07-24T00:00:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
    )


def _reader_record(revision, job_id: int, kind: str) -> JobRecord:
    return _record(revision, job_id).model_copy(update={"kind": kind})


def _materialize(store: JobStore, record: JobRecord) -> None:
    stored = store.materialize(
        JobGeneration(
            schema_version=1,
            change_id=record.change_id,
            delivery_digest=record.delivery_digest,
            receipt_id="receipt-001",
            jobs=(
                ShapeJob(
                    job_id=record.job_id,
                    kind="shape",
                    priority=record.priority,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    change_id=record.change_id,
                    delivery_digest=record.delivery_digest,
                    target_node_id=record.target_node_id,
                    receipt_id="receipt-001",
                ),
            ),
        )
    )
    store.update(record, stored[0].token)


def _request(job_id: int) -> StartJobRequest:
    return StartJobRequest(
        job_id=job_id,
        attempt_id=f"attempt-{job_id:03}",
        claim_id=f"claim-{job_id:03}",
        actor_id="agent-001",
        process_id="process-001",
        claimed_at="2026-07-24T00:01:00Z",
        candidate_revision="a" * 40,
    )


def test_writer_conflict_and_release_are_atomic(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, 1))
    _materialize(store, _record(revision, 2))
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    started = runtime.start(_request(1))
    assert not isinstance(started, DispatchDiagnostic)
    coordination_path = work_root / "dispatch" / "coordination.yaml"
    before_conflict = (coordination_path.read_bytes(), store.read(2), tuple((work_root / "attempts").rglob("*.json")))

    conflict = runtime.start(_request(2))

    assert isinstance(conflict, DispatchDiagnostic)
    assert conflict.code is DispatchDiagnosticCode.WRITER_CONFLICT
    assert conflict.holder_job_ids == (1,)
    assert (
        coordination_path.read_bytes(),
        store.read(2),
        tuple((work_root / "attempts").rglob("*.json")),
    ) == before_conflict

    released = runtime.release(
        ReleaseJobRequest(
            job_id=1,
            attempt_id="attempt-001",
            claim_id="claim-001",
            actor_id="agent-001",
            process_id="process-001",
            released_at="2026-07-24T00:02:00Z",
        )
    )

    assert not isinstance(released, DispatchDiagnostic)
    assert "readers: []" in coordination_path.read_text(encoding="utf-8")


def test_readers_coexist_and_block_writer(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _reader_record(revision, 1, "accept"))
    _materialize(store, _reader_record(revision, 2, "audit"))
    _materialize(store, _record(revision, 3))
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    assert not isinstance(runtime.start(_request(1)), DispatchDiagnostic)
    assert not isinstance(runtime.start(_request(2)), DispatchDiagnostic)
    conflict = runtime.start(_request(3))

    assert isinstance(conflict, DispatchDiagnostic)
    assert conflict.code is DispatchDiagnosticCode.WRITER_CONFLICT
    assert conflict.holder_job_ids == (1, 2)


def test_expired_recovery_clears_its_writer_holder(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, 1))
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=1))
    runtime = DispatchRuntime(native, work_root)
    assert not isinstance(runtime.start(_request(1)), DispatchDiagnostic)
    request = RecoverExpiredClaimsRequest(
        recovered_at="2026-07-24T00:02:00Z",
        actor_id="recovery-agent",
        process_id="recovery-process",
    )

    at_boundary = runtime.recover_expired_claims(request.model_copy(update={"recovered_at": "2026-07-24T00:02:00Z"}))
    assert not isinstance(at_boundary, DispatchDiagnostic)
    assert at_boundary.recovered == ()

    recovered = runtime.recover_expired_claims(request.model_copy(update={"recovered_at": "2026-07-24T00:02:01Z"}))

    assert not isinstance(recovered, DispatchDiagnostic)
    assert len(recovered.recovered) == 1
    coordination = (work_root / "dispatch" / "coordination.yaml").read_text(encoding="utf-8")
    assert "readers: []" in coordination


def test_pick_waves_is_deterministic_and_uses_current_job_state(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _reader_record(revision, 1, "accept"))
    _materialize(store, _record(revision, 2))
    _materialize(store, _reader_record(revision, 3, "audit"))
    blocked = store.read(3)
    store.update(blocked.job.model_copy(update={"block_id": "block-003"}), blocked.token)
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    first = runtime.pick_waves("a" * 40, size=2)
    assert [[entry.job_id for entry in wave] for wave in first.waves] == [[1], [2]]
    assert [entry.agent_profile for wave in first.waves for entry in wave] == ["acceptor", "builder"]
    assert first.omissions[0].reason is DispatchOmissionReason.BLOCKED
    assert runtime.pick_waves("a" * 40, size=2) == first

    assert not isinstance(runtime.start(_request(2)), DispatchDiagnostic)
    fresh = runtime.pick_waves("a" * 40, size=2)
    assert [[entry.job_id for entry in wave] for wave in fresh.waves] == [[1]]
    assert [(item.job_id, item.reason) for item in fresh.omissions] == [
        (2, DispatchOmissionReason.CLAIMED),
        (3, DispatchOmissionReason.BLOCKED),
    ]


def test_pick_waves_separates_dependent_readers(revision, tmp_path) -> None:
    changes_dir = tmp_path / "changes"
    shutil.copytree(revision.source_dir, changes_dir / revision.change_id)
    loaded = load_change(changes_dir, revision.change_id)
    assert loaded.revision is not None
    revision = loaded.revision
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    predecessor = _reader_record(revision, 1, "accept").model_copy(update={"receipt_id": "accept-001"})
    _materialize(store, predecessor)
    _materialize(store, _reader_record(revision, 2, "audit"))
    _materialize(
        store,
        _reader_record(revision, 3, "audit").model_copy(update={"predecessor_job_ids": (1,)}),
    )
    node = revision.graph.nodes[0]
    proof = revision.resolve(node.proof)
    receipt = ReceiptStore(revision).create(
        "accept-001",
        {
            "schema_version": 1,
            "kind": "accept",
            "receipt_id": "accept-001",
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "issued_at": "2026-07-24T00:00:00Z",
            "target_node_id": node.id,
            "node_plan_digest": compute_node_plan_digest(revision, node.id),
            "predecessor_receipt_ids": [],
            "evidence": {"methods": list(proof.method)},
            "code_revision": "a" * 40,
            "impact_closure": {"paths": ["serve/kanban/"], "authority_targets": [node.id, node.proof]},
        },
    )
    assert receipt.receipt is not None
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    plan = runtime.pick_waves("a" * 40, size=3)

    assert [[entry.job_id for entry in wave] for wave in plan.waves] == [[1, 2], [3]]
