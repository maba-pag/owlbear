from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from owlbear_kanban import (
    JobDiagnosticCode,
    load_change,
    parse_job_mapping,
    plan_shape_jobs,
    project_job,
    read_job_generation,
)


@pytest.fixture
def revision():
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    return result.revision


def _planned_mapping(revision) -> dict[str, object]:
    generation = plan_shape_jobs(
        revision,
        "receipt-001",
        range(1, len(revision.graph.nodes) + 1),
        priority=7,
        timestamp="2026-07-22T12:00:00Z",
    )
    return generation.model_dump()


def _job_mapping(revision, kind: str, *, target_node_id: str | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "job_id": 1,
        "kind": kind,
        "priority": 7,
        "created_at": "2026-07-22T12:00:00Z",
        "updated_at": "2026-07-22T12:00:00Z",
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_node_id": target_node_id or revision.graph.nodes[0].id,
        "node_plan_digest": "a" * 64,
        "predecessor_job_ids": [2],
        "claim_id": "claim-001",
        "block_id": "block-001",
        "pending_request_ids": ["request-001"],
        "evidence_ids": ["evidence-001"],
        "attempt_id": "attempt-001",
        "finding_id": "finding-001",
        "receipt_id": "receipt-001",
        "superseded_by_receipt_id": "receipt-002",
        "disposition": "pending",
    }


def test_plan_shape_jobs_preserves_authored_order_and_operational_identity(revision) -> None:
    generation = plan_shape_jobs(
        revision,
        "receipt-001",
        range(1, len(revision.graph.nodes) + 1),
        priority=7,
        timestamp="2026-07-22T12:00:00Z",
    )

    assert [job.target_node_id for job in generation.jobs] == [node.id for node in revision.graph.nodes]
    assert all(job.kind == "shape" for job in generation.jobs)
    assert all(job.change_id == revision.change_id for job in generation.jobs)
    assert all(job.delivery_digest == revision.delivery_digest for job in generation.jobs)
    assert all(job.receipt_id == "receipt-001" for job in generation.jobs)
    assert all(job.priority == 7 and job.created_at == job.updated_at for job in generation.jobs)
    assert isinstance(generation.jobs, tuple)
    with pytest.raises((TypeError, ValueError)):
        generation.jobs[0].job_id = 99

    serialized = _planned_mapping(revision)
    assert not {
        "title",
        "outcome",
        "acceptance",
        "module",
        "interface",
        "risk",
        "proof",
        "claims",
        "attempts",
        "transitions",
        "invalidation",
        "supersession",
        "requests",
        "mcp",
        "http",
        "ui",
    } & set(serialized)
    assert not {
        "title",
        "outcome",
        "acceptance",
        "modules",
        "interfaces",
        "risks",
        "proof",
    } & set(serialized["jobs"][0])


@pytest.mark.parametrize("kind", ["shape", "build", "accept", "audit", "supersession"])
def test_public_job_parser_round_trips_operational_records(revision, kind: str) -> None:
    value = _job_mapping(revision, kind)

    result = parse_job_mapping(value)

    assert result.diagnostics == ()
    assert result.job is not None
    assert result.job.model_dump(mode="json") == value
    with pytest.raises((TypeError, ValueError)):
        result.job.priority = 8


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("kind", "execute", JobDiagnosticCode.WRONG_KIND),
        ("target_node_id", "", JobDiagnosticCode.UNKNOWN_TARGET),
        ("target_node_id", "REQ-001", JobDiagnosticCode.UNKNOWN_TARGET),
        ("unexpected", True, JobDiagnosticCode.UNKNOWN_FIELD),
    ],
)
def test_public_job_parser_returns_stable_diagnostics(revision, field: str, value: object, expected) -> None:
    job = _job_mapping(revision, "shape")
    job[field] = value

    result = parse_job_mapping(job)

    assert result.job is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == [expected]


def test_project_job_derives_normative_context_without_serializing_it(revision) -> None:
    result = parse_job_mapping(_job_mapping(revision, "build"))
    assert result.job is not None
    node = revision.graph.nodes[0]

    projection = project_job(result.job, revision, {"acceptance": ["packet proof"]})
    serialized = result.job.model_dump(mode="json")

    assert projection.title == node.title
    assert projection.outcome == node.outcome
    assert projection.acceptance == ("packet proof",)
    assert projection.modules == node.modules
    assert projection.proof == node.proof
    assert not {"title", "outcome", "acceptance", "modules", "interfaces", "proof"} & set(serialized)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("job_id", 1, JobDiagnosticCode.DUPLICATE_ID),
        ("target_node_id", "DN-999", JobDiagnosticCode.UNKNOWN_TARGET),
        ("kind", "execute", JobDiagnosticCode.WRONG_KIND),
        ("delivery_digest", "0" * 64, JobDiagnosticCode.DIGEST_MISMATCH),
        ("receipt_id", "receipt-999", JobDiagnosticCode.RECEIPT_MISMATCH),
    ],
)
def test_read_job_generation_reports_structured_diagnostics(revision, field, value, expected) -> None:
    serialized = _planned_mapping(revision)
    if field == "job_id":
        serialized["jobs"][1][field] = value
    else:
        serialized["jobs"][0][field] = value

    generation, diagnostics = read_job_generation(serialized, revision)

    assert generation is None
    assert expected in {diagnostic.code for diagnostic in diagnostics}


def test_read_job_generation_reports_duplicate_target(revision) -> None:
    serialized = _planned_mapping(revision)
    serialized["jobs"][1]["target_node_id"] = serialized["jobs"][0]["target_node_id"]

    generation, diagnostics = read_job_generation(serialized, revision)

    assert generation is None
    assert JobDiagnosticCode.DUPLICATE_TARGET in {diagnostic.code for diagnostic in diagnostics}


def test_read_job_generation_reports_missing_target(revision) -> None:
    serialized = _planned_mapping(revision)
    serialized["jobs"] = deepcopy(serialized["jobs"][:-1])

    generation, diagnostics = read_job_generation(serialized, revision)

    assert generation is None
    assert JobDiagnosticCode.MISSING_TARGET in {diagnostic.code for diagnostic in diagnostics}
