from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

from owlbear_kanban import (
    CorrectiveRouteRequest,
    FindingStore,
    InvalidationRequest,
    JobGeneration,
    JobRecord,
    JobStore,
    NativeRuntime,
    ReceiptStore,
    ShapeJob,
    load_change,
    plan_corrective_route,
)
from owlbear_kanban.runtime_requests import NativeRequest, NativeRequestRuntime
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionParticipant


class _History:
    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return b""


def _revision(tmp_path: Path):
    changes = tmp_path / "changes"
    change_id = "replace-delivery-pipeline"
    shutil.copytree(Path(f".owlbear/changes/{change_id}"), changes / change_id)
    shutil.rmtree(changes / change_id / "receipts")
    result = load_change(changes, change_id)
    assert result.revision is not None
    return result.revision


def _job(revision, job_id: int, **changes: object) -> JobRecord:
    return JobRecord.model_validate(
        {
            "schema_version": 1,
            "job_id": job_id,
            "kind": "build",
            "priority": 1,
            "created_at": "2026-07-24T00:00:00Z",
            "updated_at": "2026-07-24T00:00:00Z",
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "target_node_id": revision.graph.nodes[0].id,
            **changes,
        }
    )


def _materialize(store: JobStore, record: JobRecord, *, archived: bool = False) -> None:
    generated = store.materialize(
        JobGeneration(
            schema_version=1,
            change_id=record.change_id,
            delivery_digest=record.delivery_digest,
            receipt_id=record.receipt_id or "seed-receipt",
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
                    receipt_id=record.receipt_id or "seed-receipt",
                ),
            ),
        )
    )[0]
    stored = store.update(record, generated.token)
    if archived:
        store.archive(record.job_id, stored.token)


def _receipt(revision, receipt_id: str, predecessors: tuple[str, ...]) -> dict[str, object]:
    node = revision.graph.nodes[0]
    return {
        "schema_version": 1,
        "kind": "build",
        "receipt_id": receipt_id,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "issued_at": "2026-07-24T00:00:00Z",
        "impact_closure": {"paths": ["serve/kanban/"], "authority_targets": [node.id, node.proof]},
        "target_node_id": node.id,
        "node_plan_digest": "b" * 64,
        "predecessor_receipt_ids": list(predecessors),
        "evidence": {"commands": ["focused proof"]},
        "code_revision": "a" * 40,
    }


def test_public_invalidation_refreshes_only_returned_index_closure(tmp_path: Path) -> None:
    revision = _revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    receipts = ReceiptStore(revision)
    assert receipts.create("build-root", _receipt(revision, "build-root", ())).receipt is not None
    assert receipts.create("build-child", _receipt(revision, "build-child", ("build-root",))).receipt is not None
    assert receipts.create("build-other", _receipt(revision, "build-other", ())).receipt is not None
    jobs = JobStore(work_root)
    _materialize(jobs, _job(revision, 1, receipt_id="build-root"), archived=True)
    _materialize(jobs, _job(revision, 2, receipt_id="build-child", predecessor_job_ids=(1,)), archived=True)
    _materialize(jobs, _job(revision, 3, predecessor_job_ids=(2,)))
    _materialize(jobs, _job(revision, 4, receipt_id="build-other"))
    finding = {
        "schema_version": 1,
        "finding_id": "finding-001",
        "source_attempt_id": "attempt-001",
        "source_job_id": 2,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_kind": "packet",
        "target_id": f"{revision.graph.nodes[0].id}-PK-001",
        "finding_class": "implementation-defect",
        "detail": "packet implementation failed",
        "created_at": "2026-07-24T00:01:00Z",
    }
    assert FindingStore(work_root).create("finding-001", finding).finding is not None
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id="finding-001",
            finding_class="implementation-defect",
            target="packet-implementation",
            target_node_ids=(revision.graph.nodes[0].id,),
        )
    )
    request = InvalidationRequest(
        invalidation_id="invalidation-001",
        supersession_receipt_id="supersession-001",
        invalidated_receipt_ids=("build-root",),
        routes=(route,),
        corrective_job_ids=(20,),
        issued_at="2026-07-24T00:02:00Z",
        code_revision="c" * 40,
    )
    runtime = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    before = runtime.list_jobs(candidate_revision="c" * 40, limit=25)

    result = runtime.invalidate(request)
    after = runtime.list_jobs(candidate_revision="c" * 40, limit=25)
    repeated = runtime.list_jobs(candidate_revision="c" * 40, limit=25)

    assert result.outcome is not None
    assert result.outcome.affected_job_ids == (1, 2, 3)
    assert after == repeated
    by_id = {item.job_id: item for item in after.items}
    assert by_id[1].validity is not None
    assert not by_id[1].validity.current
    assert by_id[2].validity is not None
    assert not by_id[2].validity.current
    assert by_id[3].disposition.value == "superseded"
    assert by_id[4] == next(item for item in before.items if item.job_id == 4)
    assert by_id[20].finding is not None
    assert by_id[20].finding.finding_id == "finding-001"


def test_request_projection_uses_persisted_native_records(tmp_path: Path) -> None:
    revision = _revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _job(revision, 1))
    request = NativeRequest(
        request_id="request-001",
        kind="action",
        title="Provide external evidence",
        summary="One external action is required.",
        body="Complete the named action.",
        agent="builder",
        created_at="2026-07-24T00:01:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
        job_ids=(1,),
        evidence=("signed receipt",),
        resume_condition="signed receipt exists",
    )
    NativeRequestRuntime(revision, work_root).create_request(request)
    runtime = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))

    jobs = runtime.list_jobs(candidate_revision="a" * 40, limit=10)
    requests = runtime.list_requests(limit=10)
    history = runtime.list_history(limit=10)

    assert jobs.items[0].requests[0].request == request
    assert requests.items[0].request == request
    assert next(item for item in history.items if item.kind == "request").request == requests.items[0]


def test_work_health_is_stable_bounded_and_non_mutating(tmp_path: Path) -> None:
    revision = _revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    jobs = JobStore(work_root)
    _materialize(jobs, _job(revision, 1))
    runtime = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    healthy = runtime.work_health(limit=100)

    assert healthy.findings == ()

    _materialize(jobs, _job(revision, 2, predecessor_job_ids=(999,)))
    (work_root / "jobs" / "unsafe.txt").write_text("unsafe", encoding="utf-8")
    (work_root / "findings").mkdir()
    orphan = {
        "schema_version": 1,
        "finding_id": "orphan",
        "source_attempt_id": "attempt-orphan",
        "source_job_id": 999,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_kind": "packet",
        "target_id": f"{revision.graph.nodes[0].id}-PK-001",
        "finding_class": "implementation-defect",
        "detail": "orphan finding",
        "created_at": "2026-07-24T00:01:00Z",
    }
    assert FindingStore(work_root).create("orphan", orphan).finding is not None
    runtime.list_jobs(candidate_revision="a" * 40, limit=10)
    RuntimeTransaction(
        work_root,
        "pending",
        (TransactionParticipant(work_root, Path("pending-output"), b"content"),),
    )._prepare_manifest()  # noqa: SLF001 - fixture intentionally leaves a recoverable manifest.
    job_path = work_root / "jobs" / "1.yaml"
    job_path.write_text(job_path.read_text(encoding="utf-8").replace("priority: 1", "priority: 9"), encoding="utf-8")
    before = {path: path.read_bytes() for path in work_root.rglob("*") if path.is_file()}

    pages = []
    cursor = None
    while True:
        page = runtime.work_health(cursor=cursor, limit=2)
        pages.append(page)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    repeated = runtime.work_health(limit=2)
    after = {path: path.read_bytes() for path in work_root.rglob("*") if path.is_file()}

    assert pages[0] == repeated
    assert all(0 < len(page.checked_paths) <= 2 for page in pages)
    assert before == after
    codes = {finding.code for page in pages for finding in page.findings}
    assert {
        "ERR_WORK_MANIFEST_PENDING",
        "ERR_WORK_FINDING_ORPHAN",
        "ERR_WORK_INDEX_DISAGREEMENT",
        "ERR_WORK_PREDECESSOR_MISSING",
        "ERR_WORK_PATH_UNSAFE",
    } <= codes
