"""Public Cockpit contract tests for native work, evidence, and health reads."""

from __future__ import annotations

import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from owlbear_kanban import (
    AttemptEvent,
    AttemptStore,
    CorrectiveRouteRequest,
    DispatchRuntime,
    FindingStore,
    GitRepositoryHistory,
    InvalidationRequest,
    JobGeneration,
    JobRecord,
    JobStore,
    KanbanEngine,
    NativeRuntime,
    PlanJob,
    ProofCheckoutManager,
    ReceiptStore,
    load_change,
    plan_corrective_route,
)
from owlbear_kanban.runtime_requests import NativeRequest, NativeRequestRuntime

from owlbear_cockpit.deps import (
    NativeChangeContext,
    NativeContextCache,
    get_engine,
    get_native_context_cache,
)
from owlbear_cockpit.main import app

_CHANGE_ID = "replace-delivery-pipeline"


class _SeededCache(NativeContextCache):
    def __init__(self, context: NativeChangeContext) -> None:
        super().__init__()
        self._context = context

    def get(self, **_kwargs: object) -> NativeChangeContext:
        return self._context


def _job(revision, job_id: int, **changes: object) -> JobRecord:  # noqa: ANN001
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
                PlanJob(
                    job_id=record.job_id,
                    kind="plan",
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


def _build_receipt(revision, code_revision: str) -> dict[str, object]:  # noqa: ANN001
    node = revision.graph.nodes[0]
    return {
        "schema_version": 1,
        "kind": "build",
        "receipt_id": "build-root",
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "issued_at": "2026-07-24T00:00:00Z",
        "impact_closure": {"paths": ["serve/cockpit/"], "authority_targets": [node.id, node.proof]},
        "target_node_id": node.id,
        "node_plan_digest": "b" * 64,
        "predecessor_receipt_ids": [],
        "evidence": {"commands": ["focused proof"]},
        "code_revision": code_revision,
    }


@pytest.fixture
def work_client(
    tmp_path: Path,
    project_root: Path,
) -> tuple[TestClient, str, Path, Path]:
    ops_root = tmp_path / ".owlbear"
    work_root = ops_root / "kanban"
    work_root.mkdir(parents=True)
    (work_root / "config.yml").write_text("next_id: 1\n", encoding="utf-8")
    (work_root / "tasks").mkdir()
    (work_root / "archive").mkdir()
    source = project_root / ".owlbear" / "changes" / _CHANGE_ID
    change_dir = ops_root / "changes" / _CHANGE_ID
    shutil.copytree(source, change_dir)
    shutil.rmtree(change_dir / "receipts")
    loaded = load_change(change_dir.parent, _CHANGE_ID)
    assert loaded.revision is not None
    revision = loaded.revision
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        text=True,
    ).strip()

    receipts = ReceiptStore(revision)
    assert receipts.create("build-root", _build_receipt(revision, head)).receipt is not None
    jobs = JobStore(work_root)
    _materialize(jobs, _job(revision, 1, receipt_id="build-root"), archived=True)
    _materialize(jobs, _job(revision, 2))
    request = NativeRequest(
        request_id="request-001",
        kind="action",
        title="Provide evidence",
        summary="External evidence is required.",
        body="Provide the signed evidence.",
        agent="builder",
        created_at="2026-07-24T00:01:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
        job_ids=(2,),
        evidence=("signed evidence",),
        resume_condition="signed evidence exists",
    )
    NativeRequestRuntime(revision, work_root).create_request(request)
    attempt = AttemptEvent(
        schema_version=1,
        attempt_id="attempt-001",
        claim_id="claim-001",
        job_id=2,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
        actor_id="builder",
        process_id="process-001",
        sequence=1,
        timestamp="2026-07-24T00:01:30Z",
        kind="started",
    )
    assert AttemptStore(work_root).create(attempt).event == attempt
    finding = {
        "schema_version": 1,
        "finding_id": "finding-001",
        "source_attempt_id": "attempt-001",
        "source_job_id": 1,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_kind": "packet",
        "target_id": f"{revision.graph.nodes[0].id}-PK-001",
        "finding_class": "implementation-defect",
        "detail": "packet implementation failed",
        "created_at": "2026-07-24T00:02:00Z",
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
    proof_checkouts = ProofCheckoutManager(project_root, ops_root / "scratch" / "proof")
    runtime = NativeRuntime(
        revision,
        work_root,
        GitRepositoryHistory(project_root),
        timedelta(minutes=5),
        proof_checkouts,
    )
    invalidation = runtime.invalidate(
        InvalidationRequest(
            invalidation_id="invalidation-001",
            supersession_receipt_id="supersession-001",
            invalidated_receipt_ids=("build-root",),
            routes=(route,),
            corrective_job_ids=(20,),
            issued_at="2026-07-24T00:03:00Z",
            code_revision=head,
        )
    )
    assert invalidation.outcome is not None
    (work_root / "jobs" / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    context = NativeChangeContext(
        revision=revision,
        runtime=runtime,
        dispatch=DispatchRuntime(runtime, work_root, proof_checkouts),
    )
    engine = KanbanEngine(work_root)
    cache = _SeededCache(context)
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_native_context_cache] = lambda: cache
    try:
        yield TestClient(app), head, work_root, change_dir
    finally:
        app.dependency_overrides.clear()


def test_native_pages_preserve_core_ordering_and_cursor_contract(
    work_client: tuple[TestClient, str, Path, Path],
) -> None:
    client, head, _, _ = work_client
    jobs = client.get(f"/api/changes/{_CHANGE_ID}/jobs", params={"candidate_revision": head, "limit": 1})

    assert jobs.status_code == 200
    assert [item["job_id"] for item in jobs.json()["items"]] == [1]
    assert jobs.json()["next_cursor"] == "1"
    second = client.get(
        f"/api/changes/{_CHANGE_ID}/jobs",
        params={"candidate_revision": head, "cursor": jobs.json()["next_cursor"], "limit": 1},
    )
    assert [item["job_id"] for item in second.json()["items"]] == [2]

    for resource in ("attempts", "findings", "receipts", "requests", "activity", "health/work", "health/change"):
        response = client.get(f"/api/changes/{_CHANGE_ID}/{resource}", params={"limit": 1})
        assert response.status_code == 200, resource
        assert "next_cursor" in response.json(), resource

    stale = client.get(f"/api/changes/{_CHANGE_ID}/findings", params={"cursor": "missing"})
    stale_health = client.get(f"/api/changes/{_CHANGE_ID}/health/change", params={"cursor": "missing"})
    invalid_limit = client.get(f"/api/changes/{_CHANGE_ID}/attempts", params={"limit": 0})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "ERR_CURSOR_STALE"
    assert stale_health.status_code == 409
    assert stale_health.json()["detail"]["code"] == "ERR_CURSOR_STALE"
    assert invalid_limit.status_code == 422


def test_native_show_routes_compose_records_and_map_missing_identities(
    work_client: tuple[TestClient, str, Path, Path],
) -> None:
    client, _, _, _ = work_client

    job = client.get(f"/api/changes/{_CHANGE_ID}/jobs/1")
    finding = client.get(f"/api/changes/{_CHANGE_ID}/findings/finding-001")
    receipt = client.get(f"/api/changes/{_CHANGE_ID}/receipts/build-root")
    request = client.get(f"/api/changes/{_CHANGE_ID}/requests/request-001")

    assert job.status_code == 200
    assert job.json()["job"]["job_id"] == 1
    assert job.json()["title"]
    assert finding.json()["finding_id"] == "finding-001"
    assert receipt.json()["receipt_id"] == "build-root"
    assert request.json()["request"]["request_id"] == "request-001"

    missing = {
        "jobs/999": "ERR_JOB_NOT_FOUND",
        "findings/not-present": "ERR_FINDING_MISSING",
        "receipts/not-present": "ERR_RECEIPT_MISSING",
    }
    for resource, code in missing.items():
        response = client.get(f"/api/changes/{_CHANGE_ID}/{resource}")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == code
        assert str(Path.cwd()) not in response.text


def test_invalidation_and_health_reads_are_complete_and_non_mutating(
    work_client: tuple[TestClient, str, Path, Path],
) -> None:
    client, _, work_root, change_dir = work_client
    work_before = {path.relative_to(work_root): path.read_bytes() for path in work_root.rglob("*") if path.is_file()}
    change_before = {
        path.relative_to(change_dir): path.read_bytes() for path in change_dir.rglob("*") if path.is_file()
    }

    invalidation = client.get(f"/api/changes/{_CHANGE_ID}/invalidations/supersession-001")
    work_health = client.get(f"/api/changes/{_CHANGE_ID}/health/work", params={"limit": 100})
    change_health = client.get(f"/api/changes/{_CHANGE_ID}/health/change", params={"limit": 100})

    assert invalidation.status_code == 200
    assert invalidation.json()["invalidation_id"] == "invalidation-001"
    assert invalidation.json()["affected_receipt_ids"] == ["build-root"]
    assert invalidation.json()["corrective_finding_ids"] == ["finding-001"]
    assert invalidation.json()["corrective_job_ids"] == [20]
    assert invalidation.json()["impact_closure"]["paths"] == ["serve/cockpit/"]
    jobs = client.get(f"/api/changes/{_CHANGE_ID}/jobs", params={"candidate_revision": "HEAD"})
    assert 20 in {item["job_id"] for item in jobs.json()["items"]}
    assert work_health.status_code == 200
    assert len(work_health.json()["checked_paths"]) <= 100
    assert work_health.json()["findings"]
    assert change_health.status_code == 200
    assert len(change_health.json()["checked_paths"]) <= 100
    assert change_health.json()["findings"]

    work_after = {path.relative_to(work_root): path.read_bytes() for path in work_root.rglob("*") if path.is_file()}
    change_after = {path.relative_to(change_dir): path.read_bytes() for path in change_dir.rglob("*") if path.is_file()}
    assert work_after == work_before
    assert change_after == change_before
