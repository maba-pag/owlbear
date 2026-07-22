from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from owlbear_kanban import (
    JobDiagnosticCode,
    load_change,
    plan_shape_jobs,
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
