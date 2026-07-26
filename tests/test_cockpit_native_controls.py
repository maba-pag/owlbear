"""Public Cockpit contract tests for native request and release controls."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from owlbear_kanban import (
    AttemptStore,
    DispatchDiagnostic,
    DispatchRuntime,
    GitRepositoryHistory,
    JobDisposition,
    JobGeneration,
    JobRecord,
    JobStore,
    KanbanEngine,
    NativeRuntime,
    PlanJob,
    ProofCheckoutManager,
    StartJobRequest,
    load_change,
)
from owlbear_kanban.runtime_requests import NativeRequest, NativeRequestRuntime
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError

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


@dataclass(frozen=True)
class _ControlHarness:
    client: TestClient
    context: NativeChangeContext
    work_root: Path
    proof_root: Path
    checkouts: ProofCheckoutManager
    head: str


def _job(revision, job_id: int, kind: str) -> JobRecord:  # noqa: ANN001
    return JobRecord(
        schema_version=1,
        job_id=job_id,
        kind=kind,
        priority=1,
        created_at="2026-07-24T00:00:00Z",
        updated_at="2026-07-24T00:00:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
    )


def _materialize(store: JobStore, record: JobRecord) -> None:
    generated = store.materialize(
        JobGeneration(
            schema_version=1,
            change_id=record.change_id,
            delivery_digest=record.delivery_digest,
            receipt_id="seed-receipt",
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
                    receipt_id="seed-receipt",
                ),
            ),
        )
    )[0]
    store.update(record, generated.token)


def _request(revision) -> NativeRequest:  # noqa: ANN001
    return NativeRequest(
        request_id="request-001",
        kind="action",
        title="Provide signed evidence",
        summary="A linked job needs external evidence.",
        body="Return the signed evidence value.",
        agent="builder",
        created_at="2026-07-24T00:01:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
        job_ids=(2,),
        evidence=("signature=abc123",),
        resume_condition="The signature is supplied.",
    )


@pytest.fixture
def control_harness(tmp_path: Path, project_root: Path) -> _ControlHarness:
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
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project_root, text=True).strip()

    jobs = JobStore(work_root)
    _materialize(jobs, _job(revision, 1, "accept"))
    _materialize(jobs, _job(revision, 2, "build"))
    _materialize(jobs, _job(revision, 3, "build"))
    _materialize(jobs, _job(revision, 4, "build"))
    _materialize(jobs, _job(revision, 5, "build"))
    NativeRequestRuntime(revision, work_root).create_request(_request(revision))

    proof_root = ops_root / "scratch" / "proof"
    checkouts = ProofCheckoutManager(project_root, proof_root)
    runtime = NativeRuntime(
        revision,
        work_root,
        GitRepositoryHistory(project_root),
        timedelta(minutes=5),
        checkouts,
    )
    dispatch = DispatchRuntime(runtime, work_root, checkouts)
    start = StartJobRequest(
        job_id=1,
        attempt_id="attempt-001",
        claim_id="claim-001",
        actor_id="acceptor",
        process_id="process-001",
        claimed_at="2026-07-24T00:02:00Z",
        candidate_revision=head,
    )
    started, checkout = dispatch.start_with_checkout(start)
    assert not isinstance(started, DispatchDiagnostic)
    assert started.diagnostic is None
    assert checkout is not None
    active = StartJobRequest(
        job_id=5,
        attempt_id="attempt-005",
        claim_id="claim-005",
        actor_id="builder",
        process_id="process-005",
        claimed_at="2026-07-24T00:02:30Z",
        candidate_revision=head,
    )
    assert runtime.start_job(active).diagnostic is None

    context = NativeChangeContext(revision=revision, runtime=runtime, dispatch=dispatch)
    engine = KanbanEngine(work_root)
    cache = _SeededCache(context)
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_native_context_cache] = lambda: cache
    harness = _ControlHarness(
        client=TestClient(app),
        context=context,
        work_root=work_root,
        proof_root=proof_root,
        checkouts=checkouts,
        head=head,
    )
    try:
        yield harness
    finally:
        checkouts.cleanup(1)
        app.dependency_overrides.clear()


def _resolution_body(harness: _ControlHarness, disposition: str = "local") -> dict[str, object]:
    return {
        "delivery_digest": harness.context.revision.delivery_digest,
        "disposition": disposition,
        "resolved_at": "2026-07-24T00:03:00Z",
        "resolved_by": "user",
        "response": "signature=abc123",
        "rationale": "The required evidence was supplied.",
    }


def _release_body(harness: _ControlHarness) -> dict[str, object]:
    return {
        "delivery_digest": harness.context.revision.delivery_digest,
        "attempt_id": "attempt-001",
        "claim_id": "claim-001",
        "actor_id": "acceptor",
        "process_id": "process-001",
        "released_at": "2026-07-24T00:04:00Z",
    }


def _store_state(*roots: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (f"{index}/{path.relative_to(root)}", path.read_bytes())
            for index, root in enumerate(roots)
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def _priority_body(harness: _ControlHarness, job_id: int = 3) -> dict[str, object]:
    stored = JobStore(harness.work_root).read(job_id)
    return {
        "job_id": job_id,
        "delivery_digest": harness.context.revision.delivery_digest,
        "expected_token": stored.token,
        "priority": 9,
        "updated_at": "2026-07-24T00:05:00Z",
    }


def _cancel_body(harness: _ControlHarness, job_id: int = 4) -> dict[str, object]:
    stored = JobStore(harness.work_root).read(job_id)
    return {
        "job_id": job_id,
        "delivery_digest": harness.context.revision.delivery_digest,
        "expected_token": stored.token,
        "cancelled_at": "2026-07-24T00:06:00Z",
    }


def test_request_resolution_replays_and_changed_identity_returns_current_authority(
    control_harness: _ControlHarness,
) -> None:
    harness = control_harness
    path = f"/api/changes/{_CHANGE_ID}/requests/request-001/resolve"
    body = _resolution_body(harness)

    resolved = harness.client.post(path, json=body)
    replayed = harness.client.post(path, json=body)
    changed = harness.client.post(path, json=body | {"rationale": "A different rationale."})

    assert resolved.status_code == 200
    assert replayed.json() == resolved.json()
    assert resolved.json()["resume"]["job_ids"] == [2]
    assert resolved.json()["resumed_jobs"][0]["job"]["pending_request_ids"] == []
    assert resolved.json()["design_reentry"] is None
    assert changed.status_code == 409
    conflict = changed.json()["detail"]
    assert conflict["code"] == "ERR_NATIVE_REQUEST_CONFLICT"
    assert conflict["target"] == "request-001"
    assert conflict["current_delivery_digest"] == harness.context.revision.delivery_digest
    assert conflict["current"]["resolution"]["rationale"] == body["rationale"]


def test_material_request_resolution_returns_design_reentry(control_harness: _ControlHarness) -> None:
    harness = control_harness
    response = harness.client.post(
        f"/api/changes/{_CHANGE_ID}/requests/request-001/resolve",
        json=_resolution_body(harness, "material"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["resume"] is None
    assert payload["resumed_jobs"] == []
    assert payload["design_reentry"] == {
        "disposition": "design-reentry",
        "request_id": "request-001",
        "change_id": _CHANGE_ID,
        "delivery_digest": harness.context.revision.delivery_digest,
        "target_node_id": harness.context.revision.graph.nodes[0].id,
        "job_ids": [2],
    }
    assert JobStore(harness.work_root).read(2).job.pending_request_ids == ("request-001",)


def test_release_replays_one_event_and_clears_coordination_and_checkout(
    control_harness: _ControlHarness,
) -> None:
    harness = control_harness
    path = f"/api/changes/{_CHANGE_ID}/jobs/1/release"
    body = _release_body(harness)

    released = harness.client.post(path, json=body)
    replayed = harness.client.post(path, json=body)

    assert released.status_code == 200
    assert replayed.json() == released.json()
    assert released.json()["event"]["kind"] == "released"
    assert [event.kind for event in AttemptStore(harness.work_root).list() if event.job_id == 1] == [
        "started",
        "released",
    ]
    assert "readers: []" in (harness.work_root / "dispatch" / "coordination.yaml").read_text(encoding="utf-8")
    assert harness.checkouts.existing(1) is None


def test_priority_and_cancel_succeed_replay_and_refresh_job_tokens(control_harness: _ControlHarness) -> None:
    harness = control_harness
    priority_body = _priority_body(harness)
    cancel_body = _cancel_body(harness)

    priority = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/3/priority", json=priority_body)
    priority_replay = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/3/priority", json=priority_body)
    cancelled = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/4/cancel", json=cancel_body)
    cancel_replay = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/4/cancel", json=cancel_body)
    detail = harness.client.get(f"/api/changes/{_CHANGE_ID}/jobs/3")

    assert priority.status_code == priority_replay.status_code == 200
    assert priority.json() == priority_replay.json()
    assert priority.json()["job"]["job"]["priority"] == 9
    assert priority.json()["job"]["token"] != priority_body["expected_token"]
    assert cancelled.status_code == cancel_replay.status_code == 200
    assert cancelled.json() == cancel_replay.json()
    assert cancelled.json()["job"]["job"]["disposition"] == "cancelled"
    assert cancelled.json()["job"]["token"] != cancel_body["expected_token"]
    assert detail.status_code == 200
    assert detail.json()["token"] == priority.json()["job"]["token"]


@pytest.mark.parametrize(
    ("path_job_id", "body_mutation", "expected_code"),
    [
        (3, {"delivery_digest": "f" * 64}, "ERR_JOB_ADMIN_AUTHORITY_STALE"),
        (3, {"expected_token": "stale-token"}, "ERR_JOB_ADMIN_OCC_STALE"),
        (5, {"job_id": 5}, "ERR_JOB_ADMIN_ACTIVE_CLAIM"),
        (3, {"job_id": 999}, "ERR_JOB_ID_CONFLICT"),
    ],
)
def test_priority_conflicts_return_current_authority_without_mutation(
    control_harness: _ControlHarness,
    path_job_id: int,
    body_mutation: dict[str, object],
    expected_code: str,
) -> None:
    harness = control_harness
    body = _priority_body(harness, path_job_id) | body_mutation
    before = _store_state(harness.work_root, harness.proof_root)

    response = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/{path_job_id}/priority", json=body)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == expected_code
    assert detail["target"] == str(path_job_id)
    assert detail["current_delivery_digest"] == harness.context.revision.delivery_digest
    if expected_code.startswith("ERR_JOB_ADMIN"):
        assert detail["current"]["job"]["job_id"] == path_job_id
        assert detail["current"]["token"] == JobStore(harness.work_root).read(path_job_id).token
    assert _store_state(harness.work_root, harness.proof_root) == before


def test_cancel_terminal_and_strict_payload_fail_before_mutation(control_harness: _ControlHarness) -> None:
    harness = control_harness
    body = _cancel_body(harness)
    first = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/4/cancel", json=body)
    assert first.status_code == 200
    terminal_body = body | {
        "expected_token": first.json()["job"]["token"],
        "cancelled_at": "2026-07-24T00:07:00Z",
    }
    before = _store_state(harness.work_root, harness.proof_root)

    terminal = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/4/cancel", json=terminal_body)
    malformed = harness.client.post(
        f"/api/changes/{_CHANGE_ID}/jobs/3/priority",
        json=_priority_body(harness) | {"status": "build"},
    )

    assert terminal.status_code == 409
    assert terminal.json()["detail"]["code"] == "ERR_JOB_ADMIN_TERMINAL"
    assert terminal.json()["detail"]["current"]["job"]["disposition"] == "cancelled"
    assert malformed.status_code == 422
    assert _store_state(harness.work_root, harness.proof_root) == before


def test_priority_rejects_obsolete_request_and_stored_digest_against_current_context(
    control_harness: _ControlHarness,
) -> None:
    harness = control_harness
    jobs = JobStore(harness.work_root)
    stored = jobs.read(3)
    obsolete_digest = "a" * 64
    obsolete = jobs.update(stored.job.model_copy(update={"delivery_digest": obsolete_digest}), stored.token)
    before = _store_state(harness.work_root, harness.proof_root)

    response = harness.client.post(
        f"/api/changes/{_CHANGE_ID}/jobs/3/priority",
        json={
            "job_id": 3,
            "delivery_digest": obsolete_digest,
            "expected_token": obsolete.token,
            "priority": 9,
            "updated_at": "2026-07-24T00:08:00Z",
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "ERR_JOB_ADMIN_AUTHORITY_STALE"
    assert detail["current_delivery_digest"] == harness.context.revision.delivery_digest
    assert detail["current"]["job"]["delivery_digest"] == obsolete_digest
    assert detail["current"]["token"] == obsolete.token
    assert _store_state(harness.work_root, harness.proof_root) == before


@pytest.mark.parametrize(
    ("mode", "expected_code"),
    [
        ("non-owner", "ERR_RELEASE_NON_OWNER"),
        ("terminal", "ERR_RELEASE_TERMINAL"),
        ("stale", "ERR_DISPATCH_LEASE_STALE"),
    ],
)
def test_release_conflicts_preserve_complete_state(
    control_harness: _ControlHarness,
    mode: str,
    expected_code: str,
) -> None:
    harness = control_harness
    body = _release_body(harness)
    jobs = JobStore(harness.work_root)
    if mode == "non-owner":
        body["actor_id"] = "other-acceptor"
    else:
        stored = jobs.read(1)
        update = (
            {"disposition": JobDisposition.CANCELLED} if mode == "terminal" else {"updated_at": "2026-07-24T00:02:01Z"}
        )
        jobs.update(stored.job.model_copy(update=update), stored.token)
    before = _store_state(harness.work_root, harness.proof_root)

    response = harness.client.post(f"/api/changes/{_CHANGE_ID}/jobs/1/release", json=body)

    assert response.status_code == 409
    conflict = response.json()["detail"]
    assert conflict["code"] == expected_code
    assert conflict["detail"]
    assert conflict["target"] == "1"
    assert conflict["current_delivery_digest"] == harness.context.revision.delivery_digest
    if mode == "stale":
        assert conflict["holder_job_ids"] == [1]
    assert _store_state(harness.work_root, harness.proof_root) == before
    assert harness.checkouts.existing(1) is not None


def test_release_transaction_conflict_preserves_all_participants(
    control_harness: _ControlHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = control_harness
    before = _store_state(harness.work_root, harness.proof_root)

    def fail_commit(_transaction: RuntimeTransaction, *, failure=None) -> None:  # noqa: ANN001, ARG001
        raise TransactionConflictError

    monkeypatch.setattr(RuntimeTransaction, "commit", fail_commit)
    response = harness.client.post(
        f"/api/changes/{_CHANGE_ID}/jobs/1/release",
        json=_release_body(harness),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "ERR_CONTROL_TRANSACTION_CONFLICT",
        "detail": "release transaction did not commit",
        "current_delivery_digest": harness.context.revision.delivery_digest,
        "lower_code": "ERR_TRANSACTION_CONFLICT",
        "target": "1",
    }
    assert _store_state(harness.work_root, harness.proof_root) == before
    assert harness.checkouts.existing(1) is not None


def test_malformed_controls_return_422_without_runtime_mutation(control_harness: _ControlHarness) -> None:
    harness = control_harness
    before = _store_state(harness.work_root, harness.proof_root)
    invalid_resolution = _resolution_body(harness)
    invalid_resolution.pop("response")
    invalid_release = _release_body(harness)
    invalid_release["unexpected"] = True

    resolution = harness.client.post(
        f"/api/changes/{_CHANGE_ID}/requests/request-001/resolve",
        json=invalid_resolution,
    )
    release = harness.client.post(
        f"/api/changes/{_CHANGE_ID}/jobs/1/release",
        json=invalid_release,
    )

    assert resolution.status_code == 422
    assert release.status_code == 422
    assert _store_state(harness.work_root, harness.proof_root) == before
