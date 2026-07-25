"""PROOF-015: assembled graph-aware Cockpit backend contract."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest
import uvicorn
from owlbear_kanban import (
    CorrectiveRouteRequest,
    DispatchDiagnostic,
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
    StartJobRequest,
    load_change,
    plan_corrective_route,
)
from owlbear_kanban.runtime_requests import NativeRequest, NativeRequestRuntime

from owlbear_cockpit.deps import get_engine, get_native_context_cache
from owlbear_cockpit.main import app

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_CHANGE_ID = "replace-delivery-pipeline"


@dataclass(frozen=True)
class _Harness:
    repository: Path
    work_root: Path
    change_dir: Path
    engine: KanbanEngine
    revision: object
    head: str
    checkouts: ProofCheckoutManager


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repository, text=True).strip()


def _job(revision, job_id: int, kind: str, **changes: object) -> JobRecord:  # noqa: ANN001
    return JobRecord.model_validate(
        {
            "schema_version": 1,
            "job_id": job_id,
            "kind": kind,
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
        "evidence": {"commands": ["assembled proof"]},
        "code_revision": code_revision,
    }


def _native_request(revision) -> NativeRequest:  # noqa: ANN001
    return NativeRequest(
        request_id="request-integration",
        kind="action",
        title="Provide signed evidence",
        summary="A linked job needs external evidence.",
        body="Return the signed evidence value.",
        agent="builder",
        created_at="2026-07-24T00:01:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
        job_ids=(3,),
        evidence=("signature=abc123",),
        resume_condition="The signature is supplied.",
    )


@pytest.fixture
def assembled_harness(tmp_path: Path, project_root: Path) -> Iterator[_Harness]:
    repository = tmp_path / "repository"
    change_dir = repository / ".owlbear" / "changes" / _CHANGE_ID
    change_dir.parent.mkdir(parents=True)
    shutil.copytree(project_root / ".owlbear" / "changes" / _CHANGE_ID, change_dir)
    receipts_dir = change_dir / "receipts"
    if receipts_dir.exists():
        shutil.rmtree(receipts_dir)
    work_root = repository / ".owlbear" / "kanban"
    (work_root / "tasks").mkdir(parents=True)
    (work_root / "archive").mkdir()
    _git(repository, "init", "-q")
    _git(repository, "add", ".")
    _git(
        repository,
        "-c",
        "user.name=OwlBear Test",
        "-c",
        "user.email=owlbear@example.invalid",
        "commit",
        "-qm",
        "fixture",
    )
    head = _git(repository, "rev-parse", "HEAD")
    loaded = load_change(change_dir.parent, _CHANGE_ID)
    assert loaded.revision is not None
    revision = loaded.revision

    receipts = ReceiptStore(revision)
    assert receipts.create("build-root", _build_receipt(revision, head)).receipt is not None
    jobs = JobStore(work_root)
    _materialize(jobs, _job(revision, 1, "build", receipt_id="build-root"), archived=True)
    _materialize(jobs, _job(revision, 2, "accept"))
    _materialize(jobs, _job(revision, 3, "build"))
    NativeRequestRuntime(revision, work_root).create_request(_native_request(revision))

    finding = {
        "schema_version": 1,
        "finding_id": "finding-integration",
        "source_attempt_id": "attempt-build-root",
        "source_job_id": 1,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_kind": "packet",
        "target_id": f"{revision.graph.nodes[0].id}-PK-001",
        "finding_class": "implementation-defect",
        "detail": "assembled proof fixture finding",
        "created_at": "2026-07-24T00:02:00Z",
    }
    assert FindingStore(work_root).create("finding-integration", finding).finding is not None
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id="finding-integration",
            finding_class="implementation-defect",
            target="packet-implementation",
            target_node_ids=(revision.graph.nodes[0].id,),
        )
    )
    checkouts = ProofCheckoutManager(repository, repository / ".owlbear" / "scratch" / "proof")
    runtime = NativeRuntime(
        revision,
        work_root,
        GitRepositoryHistory(repository),
        timedelta(minutes=5),
        checkouts,
    )
    invalidation = runtime.invalidate(
        InvalidationRequest(
            invalidation_id="invalidation-integration",
            supersession_receipt_id="supersession-integration",
            invalidated_receipt_ids=("build-root",),
            routes=(route,),
            corrective_job_ids=(20,),
            issued_at="2026-07-24T00:03:00Z",
            code_revision=head,
        )
    )
    assert invalidation.outcome is not None
    dispatch = DispatchRuntime(runtime, work_root, checkouts)
    start = StartJobRequest(
        job_id=2,
        attempt_id="attempt-integration",
        claim_id="claim-integration",
        actor_id="acceptor",
        process_id="process-integration",
        claimed_at="2026-07-24T00:04:00Z",
        candidate_revision=head,
    )
    started, checkout = dispatch.start_with_checkout(start)
    assert not isinstance(started, DispatchDiagnostic)
    assert started.diagnostic is None
    assert checkout is not None

    engine = KanbanEngine(work_root)
    legacy_task = engine.create_task("Legacy integration task", status="build", priority="high")
    engine.create_request(
        legacy_task.id,
        "action",
        "Legacy evidence",
        "Return one legacy value.",
        "builder",
    )
    harness = _Harness(repository, work_root, change_dir, engine, revision, head, checkouts)
    try:
        yield harness
    finally:
        checkouts.cleanup(2)
        app.dependency_overrides.clear()


def _state(*roots: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (f"{index}/{path.relative_to(root)}", path.read_bytes())
            for index, root in enumerate(roots)
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def _schema(schemas: dict[str, object], suffix: str) -> dict[str, object]:
    matches = [value for key, value in schemas.items() if key == suffix or key.endswith(f"__{suffix}")]
    assert len(matches) == 1
    return matches[0]  # type: ignore[return-value]


def test_assembled_native_resource_journey_is_bounded_strict_and_non_mutating(
    assembled_harness: _Harness,
) -> None:
    harness = assembled_harness
    app.dependency_overrides[get_engine] = lambda: harness.engine
    assert get_native_context_cache not in app.dependency_overrides
    before = _state(harness.work_root, harness.change_dir)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    with TestClient(app) as client:
        change = client.get(f"/api/changes/{_CHANGE_ID}")
        graph = client.get(f"/api/changes/{_CHANGE_ID}/graph")
        jobs = client.get(
            f"/api/changes/{_CHANGE_ID}/jobs",
            params={"candidate_revision": harness.head, "limit": 1},
        )
        resources = {
            "request": client.get(f"/api/changes/{_CHANGE_ID}/requests/request-integration"),
            "attempts": client.get(f"/api/changes/{_CHANGE_ID}/attempts", params={"limit": 1}),
            "finding": client.get(f"/api/changes/{_CHANGE_ID}/findings/finding-integration"),
            "receipt": client.get(f"/api/changes/{_CHANGE_ID}/receipts/supersession-integration"),
            "invalidation": client.get(f"/api/changes/{_CHANGE_ID}/invalidations/supersession-integration"),
            "activity": client.get(f"/api/changes/{_CHANGE_ID}/activity", params={"limit": 1}),
            "work_health": client.get(f"/api/changes/{_CHANGE_ID}/health/work", params={"limit": 1}),
            "change_health": client.get(f"/api/changes/{_CHANGE_ID}/health/change", params={"limit": 1}),
            "legacy": client.get("/api/legacy", params={"limit": 1}),
        }
        malformed = client.get(
            f"/api/changes/{_CHANGE_ID}/jobs",
            params={"candidate_revision": harness.head, "limit": 101},
        )
        missing = client.get(f"/api/changes/{_CHANGE_ID}/jobs/999")
        stale = client.get(f"/api/changes/{_CHANGE_ID}/attempts", params={"cursor": "not-current"})

    assert change.status_code == graph.status_code == jobs.status_code == 200
    assert change.json()["delivery_digest"] == harness.revision.delivery_digest
    assert graph.json()["plans"]["DN-001"]["packets"]
    assert len(jobs.json()["items"]) == 1
    assert jobs.json()["next_cursor"] is not None
    assert all(response.status_code == 200 for response in resources.values())
    assert resources["request"].json()["request"]["request_id"] == "request-integration"
    assert resources["attempts"].json()["items"]
    assert "next_cursor" in resources["attempts"].json()
    assert resources["finding"].json()["finding_id"] == "finding-integration"
    assert resources["receipt"].json()["receipt_id"] == "supersession-integration"
    assert resources["invalidation"].json()["corrective_job_ids"] == [20]
    assert resources["activity"].json()["items"]
    assert resources["work_health"].json()["checked_paths"]
    assert resources["change_health"].json()["checked_paths"]
    assert resources["legacy"].json()["tasks"][0]["provenance"] == "tasks"
    assert malformed.status_code == 422
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "ERR_JOB_NOT_FOUND"
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "ERR_CURSOR_STALE"
    assert _state(harness.work_root, harness.change_dir) == before

    schema = app.openapi()
    assert _schema(schema["components"]["schemas"], "ResolveRequestBody")["additionalProperties"] is False
    assert _schema(schema["components"]["schemas"], "ReleaseJobBody")["additionalProperties"] is False
    assert _schema(schema["components"]["schemas"], "LegacyInventoryResponse")["additionalProperties"] is False
    assert schema["paths"][f"/api/changes/{{change_id}}/jobs"]["get"]["parameters"][-1]["schema"]["maximum"] == 100


def test_core_context_failure_has_stable_envelope_without_partial_mutation(
    assembled_harness: _Harness,
) -> None:
    harness = assembled_harness
    transaction_dir = harness.work_root / ".runtime-transactions"
    transaction_dir.mkdir(exist_ok=True)
    (transaction_dir / "malformed.yaml").write_text(
        "schema_version: 2\nparticipants: [bad]\n",
        encoding="utf-8",
    )
    before = _state(harness.work_root, harness.change_dir)
    app.dependency_overrides[get_engine] = lambda: harness.engine
    assert get_native_context_cache not in app.dependency_overrides
    from fastapi.testclient import TestClient  # noqa: PLC0415

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/changes/{_CHANGE_ID}")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "ERR_NATIVE_CONTEXT_UNAVAILABLE",
        "message": "native context assembly failed",
    }
    assert _state(harness.work_root, harness.change_dir) == before


@contextmanager
def _live_server(engine: KanbanEngine) -> Iterator[str]:
    app.dependency_overrides[get_engine] = lambda: engine
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    base_url = f"http://127.0.0.1:{port}"
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/health/live", timeout=0.2).status_code == 200:
                break
        except httpx.TransportError:
            continue
    else:
        message = "uvicorn did not start"
        raise AssertionError(message)
    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        app.dependency_overrides.clear()


def _with_native_event(
    base_url: str,
    harness: _Harness,
    desired: str,
    action: Callable[[], httpx.Response],
) -> tuple[httpx.Response, dict[str, object]]:
    connected = threading.Event()
    probe_seen = threading.Event()
    done = threading.Event()
    stop = threading.Event()
    captured: list[dict[str, object]] = []
    probe = harness.work_root / "findings" / f"probe-{desired}.json"

    def read_events() -> None:
        with httpx.stream("GET", f"{base_url}/api/events", timeout=15) as response:
            assert response.status_code == 200
            connected.set()
            for line in response.iter_lines():
                if stop.is_set():
                    return
                if not line.startswith("data: "):
                    continue
                payload = json.loads(line.removeprefix("data: "))
                resources = payload["resources"]
                if "findings" in resources and not probe_seen.is_set():
                    probe_seen.set()
                    continue
                if desired in resources:
                    captured.append(payload)
                    done.set()
                    return

    thread = threading.Thread(target=read_events, daemon=True)
    thread.start()
    assert connected.wait(5)
    deadline = time.monotonic() + 5
    probe.parent.mkdir(parents=True, exist_ok=True)
    while not probe_seen.is_set() and time.monotonic() < deadline:
        probe.write_text(str(time.time_ns()), encoding="utf-8")
        probe_seen.wait(0.05)
    assert probe_seen.is_set()
    response = action()
    assert done.wait(10)
    stop.set()
    thread.join(timeout=2)
    probe.unlink(missing_ok=True)
    assert captured
    return response, captured[0]


def _resolution_body(harness: _Harness) -> dict[str, object]:
    return {
        "delivery_digest": harness.revision.delivery_digest,
        "disposition": "local",
        "resolved_at": "2026-07-24T00:05:00Z",
        "resolved_by": "user",
        "response": "signature=abc123",
        "rationale": "The required evidence was supplied.",
    }


def _release_body(harness: _Harness) -> dict[str, object]:
    return {
        "delivery_digest": harness.revision.delivery_digest,
        "attempt_id": "attempt-integration",
        "claim_id": "claim-integration",
        "actor_id": "acceptor",
        "process_id": "process-integration",
        "released_at": "2026-07-24T00:06:00Z",
    }


def test_http_controls_emit_native_sse_and_preserve_replay_conflicts(
    assembled_harness: _Harness,
) -> None:
    harness = assembled_harness
    with _live_server(harness.engine) as base_url, httpx.Client(base_url=base_url, timeout=10) as client:
        assert get_native_context_cache not in app.dependency_overrides
        resolution_path = f"/api/changes/{_CHANGE_ID}/requests/request-integration/resolve"
        release_path = f"/api/changes/{_CHANGE_ID}/jobs/2/release"
        resolution_body = _resolution_body(harness)
        release_body = _release_body(harness)

        malformed_before = _state(harness.work_root, harness.change_dir)
        malformed = client.post(resolution_path, json=resolution_body | {"unexpected": True})
        non_owner = client.post(release_path, json=release_body | {"actor_id": "other"})
        assert malformed.status_code == 422
        assert non_owner.status_code == 409
        assert non_owner.json()["detail"]["code"] == "ERR_RELEASE_NON_OWNER"
        assert _state(harness.work_root, harness.change_dir) == malformed_before

        resolved, request_event = _with_native_event(
            base_url,
            harness,
            "requests",
            lambda: client.post(resolution_path, json=resolution_body),
        )
        assert resolved.status_code == 200
        assert "requests" in request_event["resources"]
        replayed_resolution = client.post(resolution_path, json=resolution_body)
        resolution_before_conflict = _state(harness.work_root, harness.change_dir)
        changed_resolution = client.post(
            resolution_path,
            json=resolution_body | {"rationale": "Different immutable identity."},
        )
        assert replayed_resolution.json() == resolved.json()
        assert changed_resolution.status_code == 409
        assert changed_resolution.json()["detail"]["current_delivery_digest"] == harness.revision.delivery_digest
        assert _state(harness.work_root, harness.change_dir) == resolution_before_conflict

        released, release_event = _with_native_event(
            base_url,
            harness,
            "attempts",
            lambda: client.post(release_path, json=release_body),
        )
        assert released.status_code == 200
        assert set(release_event["resources"]).intersection({"attempts", "jobs"})
        replayed_release = client.post(release_path, json=release_body)
        release_before_conflict = _state(harness.work_root, harness.change_dir)
        changed_release = client.post(release_path, json=release_body | {"claim_id": "other"})
        assert replayed_release.json() == released.json()
        assert changed_release.status_code == 409
        assert changed_release.json()["detail"]["code"] == "ERR_RELEASE_NON_OWNER"
        assert _state(harness.work_root, harness.change_dir) == release_before_conflict

        for path in (
            "/api/board",
            "/api/tasks",
            "/api/tasks/1/activity",
            "/api/sessions",
            "/api/requests/pending",
        ):
            assert client.get(path).status_code == 404
        assert client.post("/api/tasks/1/release", json={}).status_code == 404
