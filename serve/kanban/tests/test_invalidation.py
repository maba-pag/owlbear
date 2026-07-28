from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from owlbear_kanban import (
    CorrectiveRouteRequest,
    FindingStore,
    InvalidationDiagnosticCode,
    InvalidationRequest,
    InvalidationRuntime,
    JobDisposition,
    JobGeneration,
    JobRecord,
    JobStore,
    ReceiptStore,
    PlanJob,
    compute_node_plan_digest,
    load_change,
    plan_corrective_route,
)


@pytest.mark.parametrize(
    ("target", "route", "job_kinds", "design_reentry", "through_shape"),
    [
        ("packet-implementation", "build-repair", ("build",), False, (False,)),
        ("packet-local-proof", "build-repair", ("build",), False, (False,)),
        ("packet-plan", "node-plan-revision", ("plan",), False, (False,)),
        ("packet-dependency", "node-plan-revision", ("plan",), False, (False,)),
        ("packet-proof-plan", "node-plan-revision", ("plan",), False, (False,)),
        ("admitted-design-authority", "design-reentry", (), True, ()),
        ("node-integration", "node-integration-repair", ("plan",), False, (True,)),
        (
            "whole-change-integration",
            "affected-node-correction",
            ("plan", "plan"),
            False,
            (True, True),
        ),
    ],
)
@pytest.mark.parametrize(
    "finding_class",
    ["implementation-defect", "unforeseeable-discovery", "planning-omission", "scope-change"],
)
def test_corrective_route_matrix_preserves_late_work_class(  # noqa: PLR0913
    target: str,
    route: str,
    job_kinds: tuple[str, ...],
    design_reentry: bool,  # noqa: FBT001 - parametrized expected value.
    through_shape: tuple[bool, ...],
    finding_class: str,
) -> None:
    node_ids = ("DN-003", "DN-004") if target == "whole-change-integration" else ("DN-003",)

    planned = plan_corrective_route(
        CorrectiveRouteRequest.model_validate(
            {
                "finding_id": "finding-001",
                "finding_class": finding_class,
                "target": target,
                "target_node_ids": node_ids,
            }
        )
    )

    assert planned.finding_class == finding_class
    assert planned.route == route
    assert planned.design_reentry is design_reentry
    assert tuple(job.kind for job in planned.jobs) == job_kinds
    assert tuple(job.through_plan_correction for job in planned.jobs) == through_shape


def _copied_revision(tmp_path: Path):
    changes_dir = tmp_path / "changes"
    change_id = "replace-delivery-pipeline"
    shutil.copytree(Path(f".owlbear/changes/{change_id}"), changes_dir / change_id)
    shutil.rmtree(changes_dir / change_id / "receipts")
    result = load_change(changes_dir, change_id)
    assert result.revision is not None
    return result.revision


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


def _scenario(tmp_path: Path):
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    receipts = ReceiptStore(revision)
    assert receipts.create("build-root", _receipt(revision, "build-root", ())).receipt is not None
    assert receipts.create("build-child", _receipt(revision, "build-child", ("build-root",))).receipt is not None
    assert receipts.create("build-unrelated", _receipt(revision, "build-unrelated", ())).receipt is not None
    node = revision.graph.nodes[0]
    base = {
        "schema_version": 1,
        "kind": "build",
        "priority": 7,
        "created_at": "2026-07-24T00:00:00Z",
        "updated_at": "2026-07-24T00:00:00Z",
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_node_id": node.id,
        "node_plan_digest": "b" * 64,
    }
    jobs = JobStore(work_root)
    _materialize(jobs, JobRecord.model_validate({**base, "job_id": 1, "receipt_id": "build-root"}), archived=True)
    _materialize(
        jobs,
        JobRecord.model_validate({**base, "job_id": 2, "receipt_id": "build-child", "predecessor_job_ids": (1,)}),
        archived=True,
    )
    _materialize(jobs, JobRecord.model_validate({**base, "job_id": 3, "predecessor_job_ids": (2,)}))
    _materialize(
        jobs,
        JobRecord.model_validate({**base, "job_id": 4, "receipt_id": "build-unrelated"}),
    )
    finding_value = {
        "schema_version": 1,
        "finding_id": "finding-001",
        "source_attempt_id": "attempt-001",
        "source_job_id": 2,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_kind": "packet",
        "target_id": f"{node.id}-PK-001",
        "finding_class": "implementation-defect",
        "detail": "packet implementation does not satisfy its admitted proof",
        "created_at": "2026-07-24T00:01:00Z",
    }
    assert FindingStore(work_root).create("finding-001", finding_value).finding is not None
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id="finding-001",
            finding_class="implementation-defect",
            target="packet-implementation",
            target_node_ids=(node.id,),
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
        priority=9,
    )
    return revision, work_root, request


def test_invalidation_applies_minimum_closure_and_replays_without_rewriting_history(tmp_path: Path) -> None:
    revision, work_root, request = _scenario(tmp_path)
    jobs = JobStore(work_root)
    related_terminal = jobs.read(4).job.model_copy(
        update={"job_id": 5, "receipt_id": "build-root", "disposition": JobDisposition.CANCELLED}
    )
    _materialize(jobs, related_terminal)
    terminal_before = (work_root / "jobs/5.yaml").read_bytes()
    archived_before = {path.name: path.read_bytes() for path in (work_root / "archive").glob("*.yaml")}
    receipt_before = {
        path.name: path.read_bytes()
        for path in (revision.source_dir / "receipts").glob("*.yaml")
        if path.name != "supersession-001.yaml"
    }
    runtime = InvalidationRuntime(revision, work_root)

    applied = runtime.apply(request)
    replayed = runtime.apply(request)
    conflict = runtime.apply(request.model_copy(update={"invalidated_receipt_ids": ("build-child",)}))

    assert applied.outcome is not None
    assert replayed == applied
    assert applied.outcome.affected_receipt_ids == ("build-child", "build-root")
    assert applied.outcome.affected_job_ids == (1, 2, 3, 5)
    assert tuple(item.job.job_id for item in applied.outcome.superseded_jobs) == (3,)
    assert applied.outcome.superseded_jobs[0].job.disposition is JobDisposition.SUPERSEDED
    assert tuple(item.job.job_id for item in applied.outcome.corrective_jobs) == (20,)
    assert applied.outcome.corrective_jobs[0].job.node_plan_digest == compute_node_plan_digest(
        revision, applied.outcome.corrective_jobs[0].job.target_node_id
    )
    assert JobStore(work_root).read(4).job.disposition is JobDisposition.PENDING
    assert (work_root / "jobs/5.yaml").read_bytes() == terminal_before
    assert conflict.diagnostic is not None
    assert conflict.diagnostic.code is InvalidationDiagnosticCode.CONFLICT
    assert archived_before == {path.name: path.read_bytes() for path in (work_root / "archive").glob("*.yaml")}
    assert receipt_before == {
        path.name: path.read_bytes()
        for path in (revision.source_dir / "receipts").glob("*.yaml")
        if path.name != "supersession-001.yaml"
    }


def test_invalidation_leaves_corrective_plan_without_node_plan_digest(tmp_path: Path) -> None:
    revision, work_root, request = _scenario(tmp_path)
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id="finding-001",
            finding_class="implementation-defect",
            target="packet-plan",
            target_node_ids=(revision.graph.nodes[0].id,),
        )
    )

    result = InvalidationRuntime(revision, work_root).apply(request.model_copy(update={"routes": (route,)}))

    assert result.outcome is not None
    assert result.outcome.corrective_jobs[0].job.kind == "plan"
    assert result.outcome.corrective_jobs[0].job.node_plan_digest is None


@pytest.mark.parametrize("stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_invalidation_failure_aborts_without_partial_corrective_work(tmp_path: Path, stage: str) -> None:
    revision, work_root, request = _scenario(tmp_path)
    job_before = {path.name: path.read_bytes() for path in (work_root / "jobs").glob("*.yaml")}

    def fail(current_stage: str) -> None:
        if current_stage == stage:
            message = "injected write failure"
            raise RuntimeError(message)

    result = InvalidationRuntime(revision, work_root).apply(request, failure=fail)

    assert result.diagnostic is not None
    assert result.diagnostic.code is InvalidationDiagnosticCode.ABORTED
    assert not (revision.source_dir / "receipts/supersession-001.yaml").exists()
    assert not (work_root / "jobs/20.yaml").exists()
    assert job_before == {path.name: path.read_bytes() for path in (work_root / "jobs").glob("*.yaml")}
    assert not list((work_root / ".runtime-transactions").glob("*.yaml"))
