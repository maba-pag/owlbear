from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from owlbear_kanban import JobGeneration, JobStore, PlanJob, load_change
from owlbear_kanban.runtime_requests import (
    NativeRequest,
    NativeRequestRuntime,
    RequestConflictError,
    RequestOption,
    RequestReferenceError,
    RequestResolution,
    RequestStatus,
)


@pytest.fixture
def revision():
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    return result.revision


def _materialize_jobs(revision, work_root: Path) -> None:
    store = JobStore(work_root)
    nodes = revision.graph.nodes[:2]
    generation = JobGeneration(
        schema_version=1,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        receipt_id="receipt-001",
        jobs=tuple(
            PlanJob(
                job_id=index,
                kind="plan",
                priority=0,
                created_at="2026-07-24T00:00:00Z",
                updated_at="2026-07-24T00:00:00Z",
                change_id=revision.change_id,
                delivery_digest=revision.delivery_digest,
                target_node_id=node.id,
                receipt_id="receipt-001",
            )
            for index, node in enumerate(nodes, start=1)
        ),
    )
    store.materialize(generation)


def _decision(revision, **changes: object) -> NativeRequest:
    payload = {
        "request_id": "request-001",
        "kind": "decision",
        "title": "Choose implementation",
        "summary": "One runtime choice is required.",
        "body": "Full decision context.",
        "agent": "builder",
        "created_at": "2026-07-24T00:01:00Z",
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_node_id": revision.graph.nodes[0].id,
        "job_ids": (1,),
        "options": (
            RequestOption(
                option_id="local-fix",
                label="Apply local fix",
                pros=("Contained",),
                cons=("Narrow",),
                risks=("Missed authority impact",),
                recommended=True,
                confidence=0.9,
                rationale="The issue is implementation-local.",
            ),
            RequestOption(
                option_id="redesign",
                label="Re-enter design",
                pros=("Revisits authority",),
                cons=("Interrupts delivery",),
                risks=("Broader delay",),
                recommended=False,
                confidence=0.7,
                rationale="Use when authority must change.",
            ),
        ),
        **changes,
    }
    return NativeRequest.model_validate(payload)


def _resolution(disposition: str = "local", **changes: object) -> RequestResolution:
    return RequestResolution.model_validate(
        {
            "request_id": "request-001",
            "disposition": disposition,
            "resolved_at": "2026-07-24T00:02:00Z",
            "resolved_by": "user",
            "selected_option_id": "local-fix" if disposition == "local" else "redesign",
            "rationale": "Resolved with current evidence.",
            **changes,
        }
    )


def _action(revision) -> NativeRequest:
    return NativeRequest(
        request_id="action-001",
        kind="action",
        title="Provide deployment evidence",
        summary="External evidence is required.",
        body="Return the exact signed release result.",
        agent="builder",
        created_at="2026-07-24T00:01:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        evidence=("release-id=42", "signature=abc123"),
        resume_condition="Both evidence values are present and verified.",
    )


def test_create_replays_one_identity_and_blocks_only_valid_linked_jobs(revision, tmp_path: Path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize_jobs(revision, work_root)
    runtime = NativeRequestRuntime(revision, work_root)
    request = _decision(revision)

    created = runtime.create_request(request)
    replayed = runtime.create_request(request)

    assert replayed == created
    assert runtime.list_requests(RequestStatus.PENDING) == (created,)
    assert JobStore(work_root).read(1).job.pending_request_ids == ("request-001",)
    assert JobStore(work_root).read(2).job.pending_request_ids == ()
    assert created.request.options[0].pros == ("Contained",)
    assert created.request.options[0].cons == ("Narrow",)
    assert created.request.options[0].risks == ("Missed authority impact",)
    assert created.request.options[0].confidence == 0.9
    assert created.request.options[0].rationale == "The issue is implementation-local."

    with pytest.raises(RequestReferenceError):
        NativeRequestRuntime(revision, work_root).create_request(
            _decision(revision, request_id="request-bad", job_ids=(99,))
        )

    assert not (work_root / "requests/pending/request-bad.yaml").exists()
    assert JobStore(work_root).read(1).job.pending_request_ids == ("request-001",)

    action = runtime.create_request(_action(revision))
    assert action.request.evidence == ("release-id=42", "signature=abc123")
    assert action.request.resume_condition == "Both evidence values are present and verified."


def test_local_and_material_resolution_are_atomic_immutable_and_scoped(revision, tmp_path: Path) -> None:
    local_root = tmp_path / "local"
    local_root.mkdir()
    _materialize_jobs(revision, local_root)
    local_runtime = NativeRequestRuntime(revision, local_root)
    local_runtime.create_request(_decision(revision))

    with pytest.raises(RuntimeError, match="interrupted"):
        local_runtime.resolve_request(
            _resolution(),
            failure=lambda stage: (
                (_ for _ in ()).throw(RuntimeError("interrupted")) if stage == "after-first-publication" else None
            ),
        )

    recovered = NativeRequestRuntime(revision, local_root).resolve_request(_resolution())

    assert recovered.resume is not None
    assert recovered.resume.job_ids == (1,)
    assert recovered.design_reentry is None
    assert recovered.resumed_jobs[0].job.pending_request_ids == ()
    assert local_runtime.list_requests(RequestStatus.RESOLVED) == (recovered.request,)
    assert local_runtime.create_request(_decision(revision)) == recovered.request
    assert JobStore(local_root).read(1).job.pending_request_ids == ()

    material_root = tmp_path / "material"
    material_root.mkdir()
    _materialize_jobs(revision, material_root)
    material_runtime = NativeRequestRuntime(revision, material_root)
    material_runtime.create_request(_decision(revision))
    material = _resolution("material")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(material_runtime.resolve_request, (material, material)))

    assert results[0] == results[1]
    assert results[0].design_reentry is not None
    assert results[0].design_reentry.delivery_digest == revision.delivery_digest
    assert results[0].resume is None
    assert JobStore(material_root).read(1).job.pending_request_ids == ("request-001",)
    with pytest.raises(RequestConflictError):
        material_runtime.resolve_request(material.model_copy(update={"rationale": "Changed after resolution."}))
