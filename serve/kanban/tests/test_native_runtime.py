from __future__ import annotations

import shutil
from collections import Counter
from datetime import timedelta
from pathlib import Path

import pytest

from owlbear_kanban import (
    AttemptEvent,
    AttemptStore,
    CorrectiveRouteRequest,
    Finding,
    FindingStore,
    FinishAcceptRequest,
    FinishJobDiagnosticCode,
    FinishJobRequest,
    FinishPlanRequest,
    InvalidationRequest,
    JobDiagnosticCode,
    JobDisposition,
    JobRecord,
    JobStore,
    NativeRuntime,
    FailJobDiagnosticCode,
    FailJobRequest,
    RecoverExpiredClaimsRequest,
    RecoveryDiagnosticCode,
    RejectAcceptDiagnosticCode,
    RejectAcceptRequest,
    ReceiptStore,
    ReleaseJobDiagnosticCode,
    ReleaseJobRequest,
    StartJobDiagnosticCode,
    StartJobRequest,
    compute_node_plan_digest,
    load_change,
    parse_impact_closure,
    parse_job_mapping,
    plan_corrective_route,
)
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError


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


def _record(revision, **changes: object) -> JobRecord:
    return JobRecord.model_validate(
        {
            "schema_version": 1,
            "job_id": 1,
            "kind": "build",
            "priority": 7,
            "created_at": "2026-07-24T00:00:00Z",
            "updated_at": "2026-07-24T00:00:00Z",
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "target_node_id": revision.graph.nodes[0].id,
            **changes,
        }
    )


def _materialize(store: JobStore, record: JobRecord) -> None:
    from owlbear_kanban import JobGeneration, PlanJob

    stored = store.materialize(
        JobGeneration(
            schema_version=1,
            change_id=record.change_id,
            delivery_digest=record.delivery_digest,
            receipt_id="receipt-001",
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
                    receipt_id="receipt-001",
                ),
            ),
        )
    )
    store.update(record, stored[0].token)


def _request() -> StartJobRequest:
    return StartJobRequest(
        job_id=1,
        attempt_id="attempt-001",
        claim_id="claim-001",
        actor_id="agent-001",
        process_id="process-001",
        claimed_at="2026-07-24T00:01:00Z",
        candidate_revision="a" * 40,
    )


def _runtime(revision, work_root: Path, *, claim_expiry: timedelta = timedelta(minutes=5)) -> NativeRuntime:
    return NativeRuntime(revision, work_root, _History(), claim_expiry)


def _copied_revision(tmp_path: Path, *, clean_receipts: bool = False):
    changes_dir = tmp_path / "changes"
    change_id = "replace-delivery-pipeline"
    shutil.copytree(Path(f".owlbear/changes/{change_id}"), changes_dir / change_id)
    (changes_dir / change_id / "plans" / "DN-001.yaml").unlink()
    if clean_receipts:
        shutil.rmtree(changes_dir / change_id / "receipts")
    result = load_change(changes_dir, change_id)
    assert result.revision is not None
    return result.revision


def _plan_request(revision, *, target_node_id: str = "DN-001", **changes: object) -> FinishPlanRequest:
    target = revision.resolve(target_node_id)
    proof = revision.resolve(target.proof)
    closure = {"paths": ["serve/kanban/"], "authority_targets": [target.id, target.proof]}
    return FinishPlanRequest.model_validate(
        {
            "job_id": 1,
            "attempt_id": "attempt-001",
            "claim_id": "claim-001",
            "actor_id": "agent-001",
            "process_id": "process-001",
            "finished_at": "2026-07-24T00:02:00Z",
            "receipt_id": "plan-001",
            "code_revision": "a" * 40,
            "evidence": {"methods": list(proof.method)},
            "evidence_ids": ("plan-review-001",),
            "node_plan": {
                "packets": [
                    {"id": f"{target.id}-PK-001", "dependencies": [], "impact_closure": closure},
                    {
                        "id": f"{target.id}-PK-002",
                        "dependencies": [f"{target.id}-PK-001"],
                        "impact_closure": closure,
                    },
                ]
            },
            "build_job_ids": (2, 3),
            "accept_job_id": 4,
            **changes,
        }
    )


def _release_request(job_id: int, attempt_id: str, claim_id: str) -> ReleaseJobRequest:
    return ReleaseJobRequest(
        job_id=job_id,
        attempt_id=attempt_id,
        claim_id=claim_id,
        actor_id="agent-001",
        process_id="process-001",
        released_at="2026-07-24T00:10:00Z",
    )


def _snapshot(work_root: Path) -> tuple[dict[str, bytes], tuple[AttemptEvent, ...]]:
    return (
        {str(path.relative_to(work_root)): path.read_bytes() for path in work_root.rglob("*") if path.is_file()},
        AttemptStore(work_root).list(),
    )


def _active_accept_scenario(tmp_path: Path):  # noqa: PLR0915 - assembles the public lifecycle under proof.
    revision = _copied_revision(tmp_path, clean_receipts=True)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    plan = _plan_request(revision)
    assert runtime.finish_plan(plan).diagnostic is None
    packet_closures = tuple(parse_impact_closure(packet["impact_closure"]) for packet in plan.node_plan["packets"])
    for job_id, closure in ((2, packet_closures[0]), (3, packet_closures[1])):
        attempt_id = f"attempt-{job_id:03d}"
        claim_id = f"claim-{job_id:03d}"
        start = _request().model_copy(update={"job_id": job_id, "attempt_id": attempt_id, "claim_id": claim_id})
        assert runtime.start_job(start).diagnostic is None
        result = runtime.finish_build(
            FinishJobRequest(
                job_id=job_id,
                attempt_id=attempt_id,
                claim_id=claim_id,
                actor_id=start.actor_id,
                process_id=start.process_id,
                finished_at=f"2026-07-24T00:0{job_id + 1}:00Z",
                receipt_id=f"build-{job_id - 1:03d}",
                code_revision="a" * 40,
                evidence=plan.evidence,
                evidence_ids=(f"build-proof-{job_id}",),
                impact_closure=closure,
            )
        )
        assert result.diagnostic is None
    start = _request().model_copy(update={"job_id": 4, "attempt_id": "attempt-004", "claim_id": "claim-004"})
    assert runtime.start_job(start).diagnostic is None
    return revision, work_root, runtime, start


def _reject_request(revision, start: StartJobRequest) -> RejectAcceptRequest:
    finding = Finding(
        schema_version=1,
        finding_id="finding-accept-001",
        source_attempt_id=start.attempt_id,
        source_job_id=start.job_id,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind="packet",
        target_id="DN-001-PK-001",
        finding_class="implementation-defect",
        detail="packet proof does not satisfy admitted behavior",
        created_at="2026-07-24T00:05:00Z",
    )
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target="packet-implementation",
            target_node_ids=("DN-001",),
        )
    )
    return RejectAcceptRequest(
        job_id=start.job_id,
        attempt_id=start.attempt_id,
        claim_id=start.claim_id,
        actor_id=start.actor_id,
        process_id=start.process_id,
        rejected_at="2026-07-24T00:05:00Z",
        detail="acceptance found an implementation defect",
        evidence_ids=("accept-proof-001",),
        findings=(finding,),
        invalidation=InvalidationRequest(
            invalidation_id="invalidation-accept-001",
            supersession_receipt_id="supersession-accept-001",
            invalidated_receipt_ids=("build-001",),
            routes=(route,),
            corrective_job_ids=(20,),
            issued_at="2026-07-24T00:05:00Z",
            code_revision="a" * 40,
            priority=9,
        ),
    )


def test_reject_accept_atomically_publishes_minimum_correction_and_replays(tmp_path: Path) -> None:
    revision, work_root, runtime, start = _active_accept_scenario(tmp_path)
    request = _reject_request(revision, start)

    rejected = runtime.reject_accept(request)
    replayed = runtime.reject_accept(request)
    changed = runtime.reject_accept(request.model_copy(update={"detail": "changed rejection"}))

    assert rejected.diagnostic is None
    assert replayed == rejected
    assert rejected.job is not None
    assert rejected.job.job.disposition is JobDisposition.SUPERSEDED
    assert rejected.job.job.superseded_by_receipt_id == "supersession-accept-001"
    assert rejected.event is not None
    assert rejected.event.kind == "failed"
    assert rejected.findings == request.findings
    assert rejected.invalidation is not None
    assert rejected.invalidation.affected_receipt_ids == ("build-001", "build-002")
    assert tuple(item.job.job_id for item in rejected.invalidation.corrective_jobs) == (20,)
    assert FindingStore(work_root).read("finding-accept-001").finding == request.findings[0]
    assert AttemptStore(work_root).read(start.attempt_id, 2).event == rejected.event
    assert changed.diagnostic is not None
    assert changed.diagnostic.code is RejectAcceptDiagnosticCode.IDENTITY_CONFLICT


@pytest.mark.parametrize(
    ("case", "expected_code"),
    [
        ("stale-finding-target", RejectAcceptDiagnosticCode.INVALIDATION_INVALID),
        ("stale-finding-authority", RejectAcceptDiagnosticCode.FINDING_INVALID),
        ("missing-receipt", RejectAcceptDiagnosticCode.INVALIDATION_INVALID),
        ("route-mismatch", RejectAcceptDiagnosticCode.INVALIDATION_INVALID),
        ("non-owner", RejectAcceptDiagnosticCode.NON_OWNER),
        ("missing-job", RejectAcceptDiagnosticCode.AUTHORITY_STALE),
    ],
)
def test_reject_accept_invalid_identity_publishes_nothing(
    tmp_path: Path,
    case: str,
    expected_code: RejectAcceptDiagnosticCode,
) -> None:
    revision, work_root, runtime, start = _active_accept_scenario(tmp_path)
    request = _reject_request(revision, start)
    if case == "stale-finding-target":
        request = request.model_copy(
            update={"findings": (request.findings[0].model_copy(update={"target_id": "DN-001-PK-999"}),)}
        )
    elif case == "stale-finding-authority":
        request = request.model_copy(
            update={"findings": (request.findings[0].model_copy(update={"delivery_digest": "f" * 64}),)}
        )
    elif case == "missing-receipt":
        request = request.model_copy(
            update={
                "invalidation": request.invalidation.model_copy(update={"invalidated_receipt_ids": ("build-missing",)})
            }
        )
    elif case == "route-mismatch":
        route = request.invalidation.routes[0].model_copy(update={"finding_class": "planning-omission"})
        request = request.model_copy(
            update={"invalidation": request.invalidation.model_copy(update={"routes": (route,)})}
        )
    elif case == "non-owner":
        request = request.model_copy(update={"claim_id": "claim-other"})
    else:
        request = request.model_copy(update={"job_id": 999})
    work_before = _snapshot(work_root)
    receipt_before = {path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")}

    rejected = runtime.reject_accept(request)

    assert rejected.diagnostic is not None
    assert rejected.diagnostic.code is expected_code
    assert _snapshot(work_root) == work_before
    assert receipt_before == {
        path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")
    }


@pytest.mark.parametrize("stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_reject_accept_failure_aborts_all_corrective_state(tmp_path: Path, stage: str) -> None:
    revision, work_root, runtime, start = _active_accept_scenario(tmp_path)
    request = _reject_request(revision, start)
    work_before = _snapshot(work_root)
    receipt_before = {path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")}

    def fail(current_stage: str) -> None:
        if current_stage == stage:
            message = "injected rejection failure"
            raise RuntimeError(message)

    rejected = runtime._reject_accept(request, failure=fail)  # noqa: SLF001 - exercise atomic failure seam.

    assert rejected.diagnostic is not None
    assert rejected.diagnostic.code is RejectAcceptDiagnosticCode.ABORTED
    assert _snapshot(work_root) == work_before
    assert receipt_before == {
        path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")
    }


def test_finish_plan_publishes_one_complete_outcome_and_replays(revision, tmp_path) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(
        JobStore(work_root),
        _record(revision, kind="plan", receipt_id="bootstrap-001"),
    )
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    request = _plan_request(revision)

    result = runtime.finish_plan(request)
    replay = runtime.finish_plan(request)
    changed_receipt_replay = runtime.finish_plan(
        request.model_copy(update={"code_revision": "b" * 40, "evidence": {"methods": ["changed"]}})
    )
    changed_plan = request.node_plan | {
        "packets": [
            request.node_plan["packets"][0],
            request.node_plan["packets"][1] | {"dependencies": []},
        ]
    }
    changed_plan_replay = runtime.finish_plan(request.model_copy(update={"node_plan": changed_plan}))
    changed_jobs_replay = runtime.finish_plan(request.model_copy(update={"build_job_ids": (2, 5)}))
    changed_receipt_id_replay = runtime.finish_plan(request.model_copy(update={"receipt_id": "plan-002"}))
    changed_attempt_replay = runtime.finish_plan(request.model_copy(update={"attempt_id": "attempt-002"}))

    assert result.diagnostic is None
    assert result.receipt is not None
    assert result.event is not None
    assert result.event.kind == "succeeded"
    assert result.receipt.payload["node_plan_digest"] == compute_node_plan_digest(
        runtime._revision,  # noqa: SLF001 - assert runtime adopted its published authority revision.
        revision.graph.nodes[0].id,
    )
    assert tuple(job.kind for job in result.created_jobs) == ("build", "build", "accept")
    assert JobStore(work_root).read(1, archived=True).job.receipt_id == request.receipt_id
    assert tuple(item.job.kind for item in JobStore(work_root).list()) == ("build", "build", "accept")
    assert tuple(event.kind for event in AttemptStore(work_root).list()) == ("started", "succeeded")
    assert replay.receipt == result.receipt
    assert replay.event == result.event
    assert replay.created_jobs == ()
    assert changed_receipt_replay.diagnostic is not None
    assert changed_receipt_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT
    assert changed_plan_replay.diagnostic is not None
    assert changed_plan_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT
    assert changed_jobs_replay.diagnostic is not None
    assert changed_jobs_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT
    assert changed_receipt_id_replay.diagnostic is not None
    assert changed_receipt_id_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT
    assert changed_attempt_replay.diagnostic is not None
    assert changed_attempt_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT
    assert tuple(event.kind for event in AttemptStore(work_root).list()) == ("started", "succeeded")


@pytest.mark.parametrize(
    "node_plan",
    [
        {"packets": [{"id": "DN-001-PK-001", "dependencies": []}]},
        {
            "packets": [
                {
                    "id": "DN-001-PK-001",
                    "dependencies": [],
                    "impact_closure": {"paths": ["serve/"], "authority_targets": ["DN-014"]},
                }
            ]
        },
    ],
)
def test_finish_plan_rejects_invalid_packet_authority_without_publication(tmp_path, node_plan) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    plan_path = revision.source_dir / "plans" / "DN-001.yaml"

    result = runtime.finish_plan(_plan_request(revision, node_plan=node_plan, build_job_ids=(2,)))

    assert result.diagnostic is not None
    assert result.diagnostic.code is FinishJobDiagnosticCode.NODE_PLAN_INVALID
    assert not plan_path.exists()
    assert tuple(item.job.job_id for item in store.list()) == (1,)
    assert store.list(archived=True) == ()
    assert AttemptStore(work_root).read("attempt-001", 2).event is None


def test_finish_plan_transaction_failure_publishes_nothing(tmp_path, monkeypatch) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    plan_path = revision.source_dir / "plans" / "DN-001.yaml"

    def reject_transaction(_transaction) -> None:
        raise TransactionConflictError

    monkeypatch.setattr(RuntimeTransaction, "commit", reject_transaction)

    with pytest.raises(TransactionConflictError):
        runtime.finish_plan(_plan_request(revision))

    assert not plan_path.exists()
    assert tuple(item.job.job_id for item in store.list()) == (1,)
    assert store.list(archived=True) == ()
    assert AttemptStore(work_root).read("attempt-001", 2).event is None
    assert not (revision.source_dir / "receipts/plan-001.yaml").exists()


def test_finish_build_accept_and_audit_publish_complete_outcomes(tmp_path) -> None:  # noqa: PLR0915
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    plan = _plan_request(revision)
    assert runtime.finish_plan(plan).diagnostic is None

    packet_closures = tuple(parse_impact_closure(packet["impact_closure"]) for packet in plan.node_plan["packets"])
    finish_methods = plan.evidence
    for job_id, predecessor_receipt_id, closure in (
        (2, "plan-001", packet_closures[0]),
        (3, "build-001", packet_closures[1]),
    ):
        attempt = f"attempt-{job_id:03d}"
        claim = f"claim-{job_id:03d}"
        start = _request().model_copy(update={"job_id": job_id, "attempt_id": attempt, "claim_id": claim})
        assert runtime.start_job(start).diagnostic is None
        request = FinishJobRequest(
            job_id=job_id,
            attempt_id=attempt,
            claim_id=claim,
            actor_id=start.actor_id,
            process_id=start.process_id,
            finished_at=f"2026-07-24T00:0{job_id + 1}:00Z",
            receipt_id=f"build-{job_id - 1:03d}",
            code_revision="a" * 40,
            evidence=finish_methods,
            evidence_ids=(f"build-proof-{job_id}",),
            impact_closure=closure,
        )
        result = runtime.finish_build(request)
        assert result.diagnostic is None
        assert result.receipt is not None
        assert result.receipt.payload["predecessor_receipt_ids"][-1] == predecessor_receipt_id
        assert result.event is not None
        assert result.event.kind == "succeeded"
        replay = runtime.finish_build(request)
        assert replay.receipt == result.receipt
        assert replay.event == result.event
        changed_closure = closure.model_copy(update={"paths": ("serve/tools/",)})
        changed_replay = runtime.finish_build(request.model_copy(update={"impact_closure": changed_closure}))
        assert changed_replay.diagnostic is not None
        assert changed_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT

    accept_start = _request().model_copy(update={"job_id": 4, "attempt_id": "attempt-004", "claim_id": "claim-004"})
    assert runtime.start_job(accept_start).diagnostic is None
    accept_request = FinishAcceptRequest(
        job_id=4,
        attempt_id=accept_start.attempt_id,
        claim_id=accept_start.claim_id,
        actor_id=accept_start.actor_id,
        process_id=accept_start.process_id,
        finished_at="2026-07-24T00:05:00Z",
        receipt_id="accept-001",
        code_revision="a" * 40,
        evidence=finish_methods,
        evidence_ids=("accept-proof-001",),
        reconciliation_plan_job_ids=(6, 7),
    )
    accept = runtime.finish_accept(accept_request)
    assert accept.diagnostic is None
    assert accept.receipt is not None
    assert accept.receipt.payload["predecessor_receipt_ids"] == ("build-001", "build-002")
    assert accept.event is not None
    assert accept.event.kind == "succeeded"
    assert tuple(
        (item.job.job_id, item.job.target_node_id, item.job.predecessor_job_ids)
        for item in store.list()
        if item.job.kind == "plan"
    ) == ((6, "DN-002", (4,)), (7, "DN-003", (4,)))
    assert runtime.finish_accept(accept_request).receipt == accept.receipt
    changed_reconciliation_replay = runtime.finish_accept(
        accept_request.model_copy(update={"reconciliation_plan_job_ids": (8, 9)})
    )
    assert changed_reconciliation_replay.diagnostic is not None
    assert changed_reconciliation_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT

    target = runtime._revision.graph.nodes[0]  # noqa: SLF001 - arrange a same-authority audit job.
    audit_job = _record(
        runtime._revision,  # noqa: SLF001 - use the node-plan authority published by finish_plan.
        job_id=5,
        kind="audit",
        node_plan_digest=compute_node_plan_digest(runtime._revision, target.id),  # noqa: SLF001
        predecessor_job_ids=(4,),
    )
    RuntimeTransaction(work_root, "audit-job", (store.create_participant(audit_job),)).commit()
    audit_start = _request().model_copy(update={"job_id": 5, "attempt_id": "attempt-005", "claim_id": "claim-005"})
    assert runtime.start_job(audit_start).diagnostic is None
    audit_request = FinishJobRequest(
        job_id=5,
        attempt_id=audit_start.attempt_id,
        claim_id=audit_start.claim_id,
        actor_id=audit_start.actor_id,
        process_id=audit_start.process_id,
        finished_at="2026-07-24T00:06:00Z",
        receipt_id="audit-001",
        code_revision="a" * 40,
        evidence=finish_methods,
        evidence_ids=("audit-proof-001",),
    )
    audit = runtime.finish_audit(audit_request)
    assert audit.diagnostic is None
    assert audit.receipt is not None
    assert audit.receipt.payload["predecessor_receipt_ids"] == ("accept-001",)
    assert audit.event is not None
    assert audit.event.kind == "succeeded"
    assert runtime.finish_audit(audit_request).receipt == audit.receipt
    assert runtime.finish_plan(plan).receipt is not None
    assert tuple(item.job.job_id for item in store.list(archived=True)) == (1, 2, 3, 4, 5)
    assert tuple(event.kind for event in AttemptStore(work_root).list()) == (
        "started",
        "succeeded",
        "started",
        "succeeded",
        "started",
        "succeeded",
        "started",
        "succeeded",
        "started",
        "succeeded",
    )


def test_finish_build_refuses_stale_predecessor_and_keeps_job_active(tmp_path) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    history = _History()
    runtime = NativeRuntime(revision, work_root, history, timedelta(minutes=5))
    runtime.start_job(_request())
    plan = _plan_request(revision)
    plan_result = runtime.finish_plan(plan)
    assert plan_result.diagnostic is None
    runtime.start_job(_request().model_copy(update={"job_id": 2, "attempt_id": "attempt-002", "claim_id": "claim-002"}))
    history.changed_paths = b"M\0serve/kanban/src/owlbear_kanban/native_runtime.py\0"
    packet = plan.node_plan["packets"][0]
    request = FinishJobRequest(
        job_id=2,
        attempt_id="attempt-002",
        claim_id="claim-002",
        actor_id="agent-001",
        process_id="process-001",
        finished_at="2026-07-24T00:03:00Z",
        receipt_id="build-001",
        code_revision="b" * 40,
        evidence=plan.evidence,
        impact_closure=parse_impact_closure(packet["impact_closure"]),
    )

    result = runtime.finish_build(request)

    assert result.diagnostic is not None
    assert result.diagnostic.code is FinishJobDiagnosticCode.PREDECESSOR_INVALID
    assert result.diagnostic.lower_code == "ERR_RECEIPT_CODE_PATH_STALE"
    assert store.read(2).job.attempt_id == "attempt-002"
    assert AttemptStore(work_root).read("attempt-002", 2).event is None
    assert store.list(archived=True)[0].job.job_id == 1


def test_build_start_reconciliation_gates_are_mutation_free(tmp_path) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    assert runtime.start_job(_request()).diagnostic is None
    plan = _plan_request(revision)
    assert runtime.finish_plan(plan).diagnostic is None
    for job_id, predecessor_receipt_id, packet in (
        (2, "plan-001", plan.node_plan["packets"][0]),
        (3, "build-001", plan.node_plan["packets"][1]),
    ):
        attempt_id = f"attempt-{job_id:03d}"
        claim_id = f"claim-{job_id:03d}"
        assert (
            runtime.start_job(
                _request().model_copy(update={"job_id": job_id, "attempt_id": attempt_id, "claim_id": claim_id})
            ).diagnostic
            is None
        )
        result = runtime.finish_build(
            FinishJobRequest(
                job_id=job_id,
                attempt_id=attempt_id,
                claim_id=claim_id,
                actor_id="agent-001",
                process_id="process-001",
                finished_at=f"2026-07-24T00:0{job_id + 1}:00Z",
                receipt_id=f"build-{job_id - 1:03d}",
                code_revision="a" * 40,
                evidence=plan.evidence,
                impact_closure=parse_impact_closure(packet["impact_closure"]),
            )
        )
        assert result.diagnostic is None
        assert result.receipt is not None
        assert result.receipt.payload["predecessor_receipt_ids"][-1] == predecessor_receipt_id
    accept_start = _request().model_copy(update={"job_id": 4, "attempt_id": "attempt-004", "claim_id": "claim-004"})
    assert runtime.start_job(accept_start).diagnostic is None
    assert (
        runtime.finish_accept(
            FinishAcceptRequest(
                job_id=4,
                attempt_id=accept_start.attempt_id,
                claim_id=accept_start.claim_id,
                actor_id=accept_start.actor_id,
                process_id=accept_start.process_id,
                finished_at="2026-07-24T00:05:00Z",
                receipt_id="accept-001",
                code_revision="a" * 40,
                evidence=plan.evidence,
                reconciliation_plan_job_ids=(6, 7),
            )
        ).diagnostic
        is None
    )

    current_digest = compute_node_plan_digest(revision, "DN-002")
    _materialize(
        store,
        _record(revision, job_id=5, target_node_id="DN-002", node_plan_digest="a" * 64),
    )
    _materialize(
        store,
        _record(revision, job_id=8, target_node_id="DN-002", node_plan_digest=current_digest),
    )
    stale_request = _request().model_copy(update={"job_id": 5, "attempt_id": "attempt-005", "claim_id": "claim-005"})
    active_plan_request = _request().model_copy(
        update={"job_id": 8, "attempt_id": "attempt-008", "claim_id": "claim-008"}
    )

    for request, expected in (
        (stale_request, StartJobDiagnosticCode.AUTHORITY_STALE),
        (active_plan_request, StartJobDiagnosticCode.PREDECESSOR_INVALID),
    ):
        before = _snapshot(work_root)
        result = runtime.start_job(request)

        assert result.diagnostic is not None
        assert result.diagnostic.code is expected
        assert _snapshot(work_root) == before

    assert (
        runtime.start_job(
            _request().model_copy(update={"job_id": 6, "attempt_id": "attempt-006", "claim_id": "claim-006"})
        ).diagnostic
        is None
    )
    released = runtime.release_job(_release_request(6, "attempt-006", "claim-006"))

    assert released.diagnostic is None
    assert released.event is not None
    assert released.event.kind == "released"


def test_build_start_rejects_missing_and_ambiguous_predecessor_accepts_without_mutation(tmp_path) -> None:
    missing_revision = _copied_revision(tmp_path / "missing")
    missing_work_root = tmp_path / "missing" / "work"
    missing_work_root.mkdir()
    _materialize(
        JobStore(missing_work_root),
        _record(missing_revision, kind="plan", target_node_id="DN-002", receipt_id="bootstrap-002"),
    )
    missing_runtime = _runtime(missing_revision, missing_work_root)
    assert missing_runtime.start_job(_request()).diagnostic is None
    missing_plan = _plan_request(missing_revision, target_node_id="DN-002")
    assert missing_runtime.finish_plan(missing_plan).diagnostic is None
    missing_start = _request().model_copy(
        update={"job_id": 2, "attempt_id": "attempt-missing", "claim_id": "claim-missing"}
    )
    missing_before = _snapshot(missing_work_root)

    missing = missing_runtime.start_job(missing_start)

    assert missing.diagnostic is not None
    assert missing.diagnostic.code is StartJobDiagnosticCode.PREDECESSOR_INVALID
    assert _snapshot(missing_work_root) == missing_before

    ambiguous_revision = _copied_revision(tmp_path / "ambiguous")
    ambiguous_work_root = tmp_path / "ambiguous" / "work"
    ambiguous_work_root.mkdir()
    ambiguous_store = JobStore(ambiguous_work_root)
    _materialize(ambiguous_store, _record(ambiguous_revision, kind="plan", receipt_id="bootstrap-001"))
    ambiguous_runtime = _runtime(ambiguous_revision, ambiguous_work_root)
    assert ambiguous_runtime.start_job(_request()).diagnostic is None
    predecessor_plan = _plan_request(ambiguous_revision)
    predecessor_result = ambiguous_runtime.finish_plan(predecessor_plan)
    assert predecessor_result.diagnostic is None
    assert predecessor_result.receipt is not None
    predecessor_digest = predecessor_result.receipt.payload["node_plan_digest"]
    receipt_store = ReceiptStore(ambiguous_revision)
    for job_id, receipt_id in ((11, "accept-011"), (12, "accept-012")):
        value = {
            "schema_version": 1,
            "kind": "accept",
            "receipt_id": receipt_id,
            "change_id": ambiguous_revision.change_id,
            "delivery_digest": ambiguous_revision.delivery_digest,
            "issued_at": f"2026-07-24T00:{job_id:02d}:00Z",
            "impact_closure": predecessor_result.receipt.impact_closure.model_dump(mode="json"),
            "target_node_id": "DN-001",
            "node_plan_digest": predecessor_digest,
            "predecessor_receipt_ids": [],
            "evidence": predecessor_plan.evidence,
            "code_revision": "a" * 40,
        }
        assert receipt_store.create(receipt_id, value).receipt is not None
        _materialize(
            ambiguous_store,
            _record(
                ambiguous_revision,
                job_id=job_id,
                kind="accept",
                target_node_id="DN-001",
                node_plan_digest=predecessor_digest,
                receipt_id=receipt_id,
            ),
        )
        stored = ambiguous_store.read(job_id)
        ambiguous_store.archive(job_id, stored.token)
    _materialize(
        ambiguous_store,
        _record(
            ambiguous_revision,
            job_id=20,
            kind="plan",
            target_node_id="DN-002",
            receipt_id="bootstrap-002",
        ),
    )
    ambiguous_plan_start = _request().model_copy(
        update={"job_id": 20, "attempt_id": "attempt-020", "claim_id": "claim-020"}
    )
    assert ambiguous_runtime.start_job(ambiguous_plan_start).diagnostic is None
    ambiguous_plan = _plan_request(
        ambiguous_revision,
        target_node_id="DN-002",
        job_id=20,
        attempt_id="attempt-020",
        claim_id="claim-020",
        receipt_id="plan-002",
        build_job_ids=(21, 22),
        accept_job_id=23,
    )
    assert ambiguous_runtime.finish_plan(ambiguous_plan).diagnostic is None
    ambiguous_start = _request().model_copy(update={"job_id": 21, "attempt_id": "attempt-021", "claim_id": "claim-021"})
    ambiguous_before = _snapshot(ambiguous_work_root)

    ambiguous = ambiguous_runtime.start_job(ambiguous_start)

    assert ambiguous.diagnostic is not None
    assert ambiguous.diagnostic.code is StartJobDiagnosticCode.PREDECESSOR_INVALID
    assert _snapshot(ambiguous_work_root) == ambiguous_before


def test_three_node_fold_in_occ_updates_same_plan_job_after_two_accepts(tmp_path) -> None:  # noqa: PLR0915
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    assert runtime.start_job(_request()).diagnostic is None
    first_plan = _plan_request(revision)
    assert runtime.finish_plan(first_plan).diagnostic is None
    for job_id, predecessor_receipt_id, packet in (
        (2, "plan-001", first_plan.node_plan["packets"][0]),
        (3, "build-001", first_plan.node_plan["packets"][1]),
    ):
        attempt_id = f"attempt-{job_id:03d}"
        claim_id = f"claim-{job_id:03d}"
        assert (
            runtime.start_job(
                _request().model_copy(update={"job_id": job_id, "attempt_id": attempt_id, "claim_id": claim_id})
            ).diagnostic
            is None
        )
        result = runtime.finish_build(
            FinishJobRequest(
                job_id=job_id,
                attempt_id=attempt_id,
                claim_id=claim_id,
                actor_id="agent-001",
                process_id="process-001",
                finished_at=f"2026-07-24T00:0{job_id + 1}:00Z",
                receipt_id=f"build-{job_id - 1:03d}",
                code_revision="a" * 40,
                evidence=first_plan.evidence,
                impact_closure=parse_impact_closure(packet["impact_closure"]),
            )
        )
        assert result.diagnostic is None
        assert result.receipt is not None
        assert result.receipt.payload["predecessor_receipt_ids"][-1] == predecessor_receipt_id
    first_accept_start = _request().model_copy(
        update={"job_id": 4, "attempt_id": "attempt-004", "claim_id": "claim-004"}
    )
    assert runtime.start_job(first_accept_start).diagnostic is None
    first_accept = FinishAcceptRequest(
        job_id=4,
        attempt_id="attempt-004",
        claim_id="claim-004",
        actor_id="agent-001",
        process_id="process-001",
        finished_at="2026-07-24T00:05:00Z",
        receipt_id="accept-001",
        code_revision="a" * 40,
        evidence=first_plan.evidence,
        reconciliation_plan_job_ids=(6, 7),
    )
    assert runtime.finish_accept(first_accept).diagnostic is None

    second_plan_start = _request().model_copy(
        update={"job_id": 6, "attempt_id": "attempt-006", "claim_id": "claim-006"}
    )
    assert runtime.start_job(second_plan_start).diagnostic is None
    second_plan = _plan_request(
        revision,
        target_node_id="DN-002",
        job_id=6,
        attempt_id="attempt-006",
        claim_id="claim-006",
        receipt_id="plan-002",
        build_job_ids=(8, 9),
        accept_job_id=10,
    )
    assert runtime.finish_plan(second_plan).diagnostic is None
    for job_id, _predecessor_receipt_id, packet in (
        (8, "plan-002", second_plan.node_plan["packets"][0]),
        (9, "build-007", second_plan.node_plan["packets"][1]),
    ):
        attempt_id = f"attempt-{job_id:03d}"
        claim_id = f"claim-{job_id:03d}"
        assert (
            runtime.start_job(
                _request().model_copy(update={"job_id": job_id, "attempt_id": attempt_id, "claim_id": claim_id})
            ).diagnostic
            is None
        )
        assert (
            runtime.finish_build(
                FinishJobRequest(
                    job_id=job_id,
                    attempt_id=attempt_id,
                    claim_id=claim_id,
                    actor_id="agent-001",
                    process_id="process-001",
                    finished_at=f"2026-07-24T00:{job_id:02d}:00Z",
                    receipt_id=f"build-{job_id - 1:03d}",
                    code_revision="a" * 40,
                    evidence=second_plan.evidence,
                    impact_closure=parse_impact_closure(packet["impact_closure"]),
                )
            ).diagnostic
            is None
        )
    second_accept_start = _request().model_copy(
        update={"job_id": 10, "attempt_id": "attempt-010", "claim_id": "claim-010"}
    )
    assert runtime.start_job(second_accept_start).diagnostic is None
    second_accept = FinishAcceptRequest(
        job_id=10,
        attempt_id="attempt-010",
        claim_id="claim-010",
        actor_id="agent-001",
        process_id="process-001",
        finished_at="2026-07-24T00:10:00Z",
        receipt_id="accept-002",
        code_revision="a" * 40,
        evidence=second_plan.evidence,
        reconciliation_plan_job_ids=(7, 11, 12),
    )
    assert runtime.finish_accept(second_accept).diagnostic is None
    before_conflict = _snapshot(work_root)
    conflict = runtime.finish_accept(second_accept.model_copy(update={"reconciliation_plan_job_ids": (13, 11, 12)}))

    assert store.read(7).job.predecessor_job_ids == (4, 10)
    assert conflict.diagnostic is not None
    assert conflict.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT
    assert _snapshot(work_root) == before_conflict


def test_reconciliation_finish_releases_new_build_and_invalidation_closure(tmp_path) -> None:  # noqa: PLR0915
    revision = _copied_revision(tmp_path, clean_receipts=True)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="plan", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    assert runtime.start_job(_request()).diagnostic is None
    predecessor_plan = _plan_request(revision)
    assert runtime.finish_plan(predecessor_plan).diagnostic is None
    for job_id, packet in zip((2, 3), predecessor_plan.node_plan["packets"], strict=True):
        attempt_id = f"attempt-{job_id:03d}"
        claim_id = f"claim-{job_id:03d}"
        assert (
            runtime.start_job(
                _request().model_copy(update={"job_id": job_id, "attempt_id": attempt_id, "claim_id": claim_id})
            ).diagnostic
            is None
        )
        assert (
            runtime.finish_build(
                FinishJobRequest(
                    job_id=job_id,
                    attempt_id=attempt_id,
                    claim_id=claim_id,
                    actor_id="agent-001",
                    process_id="process-001",
                    finished_at=f"2026-07-24T00:0{job_id + 1}:00Z",
                    receipt_id=f"build-{job_id - 1:03d}",
                    code_revision="a" * 40,
                    evidence=predecessor_plan.evidence,
                    impact_closure=parse_impact_closure(packet["impact_closure"]),
                )
            ).diagnostic
            is None
        )
    accept_start = _request().model_copy(update={"job_id": 4, "attempt_id": "attempt-004", "claim_id": "claim-004"})
    assert runtime.start_job(accept_start).diagnostic is None
    accept = runtime.finish_accept(
        FinishAcceptRequest(
            job_id=4,
            attempt_id="attempt-004",
            claim_id="claim-004",
            actor_id="agent-001",
            process_id="process-001",
            finished_at="2026-07-24T00:05:00Z",
            receipt_id="accept-001",
            code_revision="a" * 40,
            evidence=predecessor_plan.evidence,
            reconciliation_plan_job_ids=(6, 7),
        )
    )
    assert accept.diagnostic is None

    old_digest = "a" * 64
    _materialize(
        store,
        _record(
            revision,
            job_id=5,
            target_node_id="DN-002",
            node_plan_digest=old_digest,
            predecessor_job_ids=(4,),
        ),
    )
    old_build_start = _request().model_copy(update={"job_id": 5, "attempt_id": "attempt-005", "claim_id": "claim-005"})
    blocked_before_plan = runtime.start_job(old_build_start)
    assert blocked_before_plan.diagnostic is not None
    assert blocked_before_plan.diagnostic.code is StartJobDiagnosticCode.AUTHORITY_STALE

    reconciliation_start = _request().model_copy(
        update={"job_id": 6, "attempt_id": "attempt-006", "claim_id": "claim-006"}
    )
    assert runtime.start_job(reconciliation_start).diagnostic is None
    reconciliation_plan = _plan_request(
        revision,
        target_node_id="DN-002",
        job_id=6,
        attempt_id="attempt-006",
        claim_id="claim-006",
        receipt_id="plan-002",
        build_job_ids=(8, 9),
        accept_job_id=10,
        finished_at="2026-07-24T00:06:00Z",
    )
    reconciled = runtime.finish_plan(reconciliation_plan)

    assert reconciled.diagnostic is None
    assert reconciled.receipt is not None
    assert reconciled.receipt.payload["predecessor_receipt_ids"] == ("accept-001",)
    new_digest = reconciled.receipt.payload["node_plan_digest"]
    assert new_digest != old_digest
    stale = runtime.start_job(old_build_start)
    assert stale.diagnostic is not None
    assert stale.diagnostic.code is StartJobDiagnosticCode.AUTHORITY_STALE
    new_build_start = _request().model_copy(update={"job_id": 8, "attempt_id": "attempt-008", "claim_id": "claim-008"})
    assert runtime.start_job(new_build_start).diagnostic is None
    assert runtime.release_job(_release_request(8, "attempt-008", "claim-008")).diagnostic is None

    _materialize(
        store,
        _record(revision, job_id=20, kind="plan", target_node_id="DN-004", receipt_id="bootstrap-disjoint"),
    )
    disjoint_start = _request().model_copy(update={"job_id": 20, "attempt_id": "attempt-020", "claim_id": "claim-020"})
    assert runtime.start_job(disjoint_start).diagnostic is None
    disjoint_plan = _plan_request(
        revision,
        target_node_id="DN-004",
        job_id=20,
        attempt_id="attempt-020",
        claim_id="claim-020",
        receipt_id="plan-disjoint",
        build_job_ids=(21, 22),
        accept_job_id=23,
        finished_at="2026-07-24T00:07:00Z",
    )
    assert runtime.finish_plan(disjoint_plan).diagnostic is None
    disjoint_plan_path = revision.source_dir / "plans" / "DN-004.yaml"
    disjoint_plan_bytes = disjoint_plan_path.read_bytes()

    finding = {
        "schema_version": 1,
        "finding_id": "finding-reconciliation",
        "source_attempt_id": "attempt-004",
        "source_job_id": 4,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_kind": "packet",
        "target_id": "DN-001-PK-001",
        "finding_class": "implementation-defect",
        "detail": "predecessor acceptance requires correction",
        "created_at": "2026-07-24T00:08:00Z",
    }
    assert FindingStore(work_root).create("finding-reconciliation", finding).finding is not None
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id="finding-reconciliation",
            finding_class="implementation-defect",
            target="packet-implementation",
            target_node_ids=("DN-001",),
        )
    )
    request = InvalidationRequest(
        invalidation_id="invalidation-reconciliation",
        supersession_receipt_id="supersession-reconciliation",
        invalidated_receipt_ids=("accept-001",),
        routes=(route,),
        corrective_job_ids=(30,),
        issued_at="2026-07-24T00:09:00Z",
        code_revision="a" * 40,
    )
    before = {item.job_id: item for item in runtime.list_jobs(candidate_revision="a" * 40).items}
    invalidated = runtime.invalidate(request)
    after = {item.job_id: item for item in runtime.list_jobs(candidate_revision="a" * 40).items}

    assert invalidated.outcome is not None
    assert invalidated.outcome.affected_receipt_ids == ("accept-001", "plan-002")
    assert {4, 6, 8, 9, 10}.issubset(invalidated.outcome.affected_job_ids)
    assert after[6].validity is not None
    assert not after[6].validity.current
    assert 20 not in invalidated.outcome.affected_job_ids
    assert after[20] == before[20]
    assert after[20].validity is not None
    assert after[20].validity.current
    assert disjoint_plan_path.read_bytes() == disjoint_plan_bytes
    assert runtime.work_health(limit=100).findings == ()
    non_current_start = _request().model_copy(
        update={"job_id": 8, "attempt_id": "attempt-non-current", "claim_id": "claim-non-current"}
    )
    non_current_before = _snapshot(work_root)

    non_current = runtime.start_job(non_current_start)

    assert non_current.diagnostic is not None
    assert non_current.diagnostic.code is StartJobDiagnosticCode.PREDECESSOR_INVALID
    assert _snapshot(work_root) == non_current_before


def test_start_job_stores_claim_and_started_event_then_replays(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision))
    runtime = _runtime(revision, work_root)

    started = runtime.start_job(_request())
    replayed = runtime.start_job(_request())

    assert started.diagnostic is None
    assert started.job is not None
    assert started.event is not None
    assert started.job.job.claim_id == "claim-001"
    assert started.job.job.attempt_id == "attempt-001"
    assert started.job.job.updated_at == "2026-07-24T00:01:00Z"
    assert started.event.kind == "started"
    assert started.event.claim_id == "claim-001"
    assert started.event.sequence == 1
    assert replayed.job == started.job
    assert replayed.event == started.event
    conflict = runtime.start_job(_request().model_copy(update={"actor_id": "agent-002"}))
    assert conflict.diagnostic is not None
    assert conflict.diagnostic.code is StartJobDiagnosticCode.IDENTITY_CONFLICT
    claim_conflict = runtime.start_job(_request().model_copy(update={"claim_id": "other-claim"}))
    assert claim_conflict.diagnostic is not None
    assert claim_conflict.diagnostic.code is StartJobDiagnosticCode.ACTIVE_CLAIM
    timestamp_conflict = runtime.start_job(_request().model_copy(update={"claimed_at": "2026-07-24T00:02:00Z"}))
    assert timestamp_conflict.diagnostic is not None
    assert timestamp_conflict.diagnostic.code is StartJobDiagnosticCode.IDENTITY_CONFLICT


def test_runtime_queries_project_orthogonal_state_and_deterministic_history(revision, tmp_path) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, job_id=2, predecessor_job_ids=(1,)))
    _materialize(store, _record(revision, job_id=1))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())

    first = runtime.list_jobs(candidate_revision="a" * 40, limit=1)
    repeated = runtime.list_jobs(candidate_revision="a" * 40, limit=1)
    second = runtime.list_jobs(candidate_revision="a" * 40, cursor=first.next_cursor, limit=1)
    attempts = runtime.list_attempts(limit=1)
    history = runtime.list_history(limit=1)

    assert first == repeated
    assert first.next_cursor == "1"
    assert first.items[0].kind == "build"
    assert first.items[0].claim_id == "claim-001"
    assert first.items[0].attempt is not None
    assert first.items[0].attempt.kind == "started"
    assert first.items[0].disposition is JobDisposition.PENDING
    assert first.items[0].title == revision.graph.nodes[0].title
    assert second.items[0].job_id == 2
    assert second.items[0].dependency_ready is False
    assert attempts.items[0] == first.items[0].attempt
    assert history.items[0].identity == "attempt:attempt-001/1"


def test_runtime_queries_bound_scale_pages_and_reuse_indexes(revision, tmp_path, monkeypatch) -> None:
    node = revision.graph.nodes[0]
    nodes = tuple(node.model_copy(update={"id": f"DN-{index:03d}"}) for index in range(1, 501))
    revision = revision.model_copy(update={"graph": revision.graph.model_copy(update={"nodes": nodes})})
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    for job_id in range(1, 501):
        _materialize(store, _record(revision, job_id=job_id, target_node_id=f"DN-{job_id:03d}"))
    attempts = AttemptStore(work_root)
    for job_id in range(1, 501):
        for sequence in range(1, 5):
            attempts.create(
                AttemptEvent(
                    schema_version=1,
                    attempt_id=f"attempt-{job_id:03d}",
                    claim_id=f"claim-{job_id:03d}",
                    job_id=job_id,
                    change_id=revision.change_id,
                    delivery_digest=revision.delivery_digest,
                    target_node_id=f"DN-{job_id:03d}",
                    actor_id="agent-001",
                    process_id="process-001",
                    sequence=sequence,
                    timestamp=f"2026-07-24T00:{sequence:02d}:00Z",
                    kind="started" if sequence == 1 else "failed",
                )
            )

    calls: Counter[str] = Counter()
    original_jobs = JobStore.list
    original_attempts = AttemptStore.list

    def count_jobs(self, *, archived=False):
        calls["jobs"] += 1
        return original_jobs(self, archived=archived)

    def count_attempts(self):
        calls["attempts"] += 1
        return original_attempts(self)

    monkeypatch.setattr(JobStore, "list", count_jobs)
    monkeypatch.setattr(AttemptStore, "list", count_attempts)
    runtime = _runtime(revision, work_root)

    first = runtime.list_jobs(candidate_revision="a" * 40, limit=25)
    second = runtime.list_jobs(candidate_revision="a" * 40, cursor=first.next_cursor, limit=25)
    repeated = runtime.list_jobs(candidate_revision="a" * 40, limit=25)
    attempt_page = runtime.list_attempts(limit=25)

    assert first == repeated
    assert tuple(item.job_id for item in first.items) == tuple(range(1, 26))
    assert tuple(item.job_id for item in second.items) == tuple(range(26, 51))
    assert len(attempt_page.items) == 25
    assert attempt_page.items[0].attempt_id == "attempt-001"
    assert attempt_page.items[-1].attempt_id == "attempt-007"
    assert attempt_page.next_cursor == "attempt-007/1"
    assert calls == Counter({"jobs": 2, "attempts": 1})


def test_release_and_fail_only_finalize_the_owning_attempt(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())

    release = ReleaseJobRequest(
        job_id=1,
        attempt_id="attempt-001",
        claim_id="claim-001",
        actor_id="agent-001",
        process_id="process-001",
        released_at="2026-07-24T00:02:00Z",
    )
    released = runtime.release_job(release)
    replayed_release = runtime.release_job(release)

    assert released.job is not None
    assert released.event is not None
    assert released.job.job.claim_id is None
    assert released.job.job.attempt_id is None
    assert released.job.job.disposition is JobDisposition.PENDING
    assert released.event.kind == "released"
    assert released.event.claim_id == "claim-001"
    assert released.event.sequence == 2
    assert replayed_release == released

    runtime.start_job(_request().model_copy(update={"attempt_id": "attempt-002", "claim_id": "claim-002"}))
    non_owner = runtime.release_job(
        release.model_copy(update={"attempt_id": "attempt-002", "claim_id": "claim-002", "actor_id": "agent-002"})
    )

    assert non_owner.diagnostic is not None
    assert non_owner.diagnostic.code is ReleaseJobDiagnosticCode.NON_OWNER

    failure = FailJobRequest(
        job_id=1,
        attempt_id="attempt-002",
        claim_id="claim-002",
        actor_id="agent-001",
        process_id="process-001",
        failed_at="2026-07-24T00:03:00Z",
        detail="unit test failure",
        evidence_ids=("evidence-001",),
    )
    failed = runtime.fail_job(failure)
    replayed_failure = runtime.fail_job(failure)

    assert failed.job is not None
    assert failed.event is not None
    assert failed.job.job.claim_id is None
    assert failed.job.job.attempt_id is None
    assert failed.event.kind == "failed"
    assert failed.event.claim_id == "claim-002"
    assert failed.event.sequence == 2
    assert failed.event.detail == "unit test failure"
    assert failed.event.evidence_ids == ("evidence-001",)
    preserved_started = AttemptStore(work_root).read("attempt-002", 1).event
    assert preserved_started is not None
    assert preserved_started.kind == "started"
    assert replayed_failure == failed

    no_active_claim = runtime.release_job(
        release.model_copy(update={"attempt_id": "attempt-003", "claim_id": "claim-003"})
    )

    assert no_active_claim.diagnostic is not None
    assert no_active_claim.diagnostic.code is ReleaseJobDiagnosticCode.NO_ACTIVE_CLAIM

    no_active_failure = runtime.fail_job(
        failure.model_copy(update={"attempt_id": "attempt-003", "claim_id": "claim-003"})
    )

    assert no_active_failure.diagnostic is not None
    assert no_active_failure.diagnostic.code is FailJobDiagnosticCode.NO_ACTIVE_CLAIM


def test_completed_claim_mismatch_returns_non_owner_without_mutation(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    release = ReleaseJobRequest(
        job_id=1,
        attempt_id="attempt-001",
        claim_id="claim-001",
        actor_id="agent-001",
        process_id="process-001",
        released_at="2026-07-24T00:02:00Z",
    )
    runtime.release_job(release)
    release_before_mismatch = JobStore(work_root).read(1)

    release_mismatch = runtime.release_job(release.model_copy(update={"claim_id": "other-claim"}))

    assert release_mismatch.diagnostic is not None
    assert release_mismatch.diagnostic.code is ReleaseJobDiagnosticCode.NON_OWNER
    assert JobStore(work_root).read(1) == release_before_mismatch


def test_completed_failure_claim_mismatch_returns_non_owner_without_mutation(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    failure = FailJobRequest(
        job_id=1,
        attempt_id="attempt-001",
        claim_id="claim-001",
        actor_id="agent-001",
        process_id="process-001",
        failed_at="2026-07-24T00:02:00Z",
        detail="unit test failure",
        evidence_ids=("evidence-001",),
    )
    runtime.fail_job(failure)
    failure_before_mismatch = JobStore(work_root).read(1)

    failure_mismatch = runtime.fail_job(failure.model_copy(update={"claim_id": "other-claim"}))

    assert failure_mismatch.diagnostic is not None
    assert failure_mismatch.diagnostic.code is FailJobDiagnosticCode.NON_OWNER
    assert JobStore(work_root).read(1) == failure_before_mismatch


def test_release_replay_for_another_job_does_not_return_or_mutate_the_original_outcome(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision))
    _materialize(store, _record(revision, job_id=2))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    release = ReleaseJobRequest(
        job_id=1,
        attempt_id="attempt-001",
        claim_id="claim-001",
        actor_id="agent-001",
        process_id="process-001",
        released_at="2026-07-24T00:02:00Z",
    )
    released = runtime.release_job(release)
    job_one_before = store.read(1)
    job_two_before = store.read(2)

    replay_for_other_job = runtime.release_job(release.model_copy(update={"job_id": 2}))

    assert released.event is not None
    assert replay_for_other_job.diagnostic is not None
    assert replay_for_other_job.diagnostic.code is ReleaseJobDiagnosticCode.NO_ACTIVE_CLAIM
    assert store.read(1) == job_one_before
    assert store.read(2) == job_two_before
    assert AttemptStore(work_root).read("attempt-001", 2).event == released.event


@pytest.mark.parametrize("disposition", [JobDisposition.CANCELLED, JobDisposition.SUPERSEDED])
def test_start_job_rejects_terminal_dispositions(revision, tmp_path, disposition) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision, disposition=disposition))

    result = _runtime(revision, work_root).start_job(_request())

    assert result.diagnostic is not None
    assert result.diagnostic.code is StartJobDiagnosticCode.TERMINAL
    assert result.diagnostic.target == disposition.value


@pytest.mark.parametrize(
    ("changes", "code", "target"),
    [
        ({"change_id": "other-change"}, StartJobDiagnosticCode.AUTHORITY_STALE, "1"),
        ({"node_plan_digest": "a" * 64}, StartJobDiagnosticCode.AUTHORITY_STALE, "DN-001"),
        ({"predecessor_job_ids": (2,)}, StartJobDiagnosticCode.PREDECESSOR_INVALID, "2"),
        ({"pending_request_ids": ("request-001",)}, StartJobDiagnosticCode.REQUEST_PENDING, "request-001"),
        ({"claim_id": "claim-001"}, StartJobDiagnosticCode.ACTIVE_CLAIM, None),
        (
            {"claim_id": "other-claim", "attempt_id": "other-attempt"},
            StartJobDiagnosticCode.ACTIVE_CLAIM,
            None,
        ),
    ],
)
def test_start_job_rejects_ineligible_jobs(revision, tmp_path, changes, code, target) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, **changes))
    before = store.read(1)

    result = _runtime(revision, work_root).start_job(_request())

    assert result.diagnostic is not None
    assert result.diagnostic.code is code
    assert result.diagnostic.target == target
    assert store.read(1) == before


def test_job_parser_rejects_unsupported_disposition(revision) -> None:
    result = parse_job_mapping(_record(revision).model_dump() | {"disposition": "claimed"})

    assert result.job is None
    assert result.diagnostics[0].code is JobDiagnosticCode.SCHEMA_INVALID


def test_recovery_uses_strict_expiry_boundary_and_replays_from_storage(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())

    before_expiry = RecoverExpiredClaimsRequest(
        recovered_at="2026-07-24T00:05:59Z",
        actor_id="recovery-agent",
        process_id="recovery-process",
    )
    at_expiry = before_expiry.model_copy(update={"recovered_at": "2026-07-24T00:06:00Z"})
    after_expiry = before_expiry.model_copy(update={"recovered_at": "2026-07-24T00:06:01Z"})
    before = JobStore(work_root).read(1)

    assert runtime.recover_expired_claims(before_expiry).recovered == ()
    assert runtime.recover_expired_claims(at_expiry).recovered == ()
    assert JobStore(work_root).read(1) == before

    recovered = runtime.recover_expired_claims(after_expiry)
    replayed = runtime.recover_expired_claims(after_expiry)
    reopened = _runtime(revision, work_root).recover_expired_claims(after_expiry)

    assert recovered.diagnostics == ()
    assert len(recovered.recovered) == 1
    assert replayed == recovered
    assert reopened == recovered
    outcome = recovered.recovered[0]
    assert outcome.job.job.claim_id is None
    assert outcome.job.job.attempt_id is None
    assert outcome.job.job.disposition is JobDisposition.PENDING
    assert outcome.job.job.updated_at == after_expiry.recovered_at
    assert outcome.event.kind == "crashed"
    assert outcome.event.sequence == 2
    assert outcome.event.job_id == 1
    assert outcome.event.attempt_id == "attempt-001"
    assert outcome.event.claim_id == "claim-001"
    assert outcome.event.actor_id == "recovery-agent"
    assert outcome.event.process_id == "recovery-process"
    assert outcome.event.timestamp == after_expiry.recovered_at
    assert outcome.event.detail == "claim expired"
    assert outcome.event.evidence_ids == ()
    assert tuple(event.kind for event in AttemptStore(work_root).list()) == ("started", "crashed")


def test_recovery_rejects_invalid_policy_and_timestamp(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()

    with pytest.raises(ValueError, match="claim expiry must be positive"):
        NativeRuntime(revision, work_root, _History(), timedelta(0))
    with pytest.raises(ValueError, match="claim expiry must be positive"):
        NativeRuntime(revision, work_root, _History(), timedelta(seconds=-1))
    with pytest.raises(ValueError, match="valid ISO 8601"):
        RecoverExpiredClaimsRequest(
            recovered_at="not-a-timestamp",
            actor_id="recovery-agent",
            process_id="recovery-process",
        )
    with pytest.raises(ValueError, match="include a timezone"):
        RecoverExpiredClaimsRequest(
            recovered_at="2026-07-24T00:06:01",
            actor_id="recovery-agent",
            process_id="recovery-process",
        )


def test_recovery_orders_jobs_and_isolates_identity_and_transaction_conflicts(revision, tmp_path, monkeypatch) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, job_id=3))
    _materialize(store, _record(revision, job_id=1, claim_id="orphaned-claim"))
    _materialize(store, _record(revision, job_id=2))
    runtime = _runtime(revision, work_root, claim_expiry=timedelta(minutes=1))
    runtime.start_job(_request().model_copy(update={"job_id": 2, "attempt_id": "attempt-002"}))
    runtime.start_job(_request().model_copy(update={"job_id": 3, "attempt_id": "attempt-003"}))
    original_commit = RuntimeTransaction.commit
    commit_calls = 0

    def conflict_first_recovery(self, *, failure=None) -> None:
        nonlocal commit_calls
        commit_calls += 1
        if commit_calls == 1:
            raise TransactionConflictError
        original_commit(self, failure=failure)

    monkeypatch.setattr(RuntimeTransaction, "commit", conflict_first_recovery)
    request = RecoverExpiredClaimsRequest(
        recovered_at="2026-07-24T00:02:01Z",
        actor_id="recovery-agent",
        process_id="recovery-process",
    )

    result = runtime.recover_expired_claims(request)

    assert tuple(item.job.job.job_id for item in result.recovered) == (3,)
    assert tuple(item.job_id for item in result.diagnostics) == (1, 2)
    assert tuple(item.code for item in result.diagnostics) == (
        RecoveryDiagnosticCode.IDENTITY_INVALID,
        RecoveryDiagnosticCode.CONFLICT,
    )
    assert store.read(2).job.claim_id == "claim-001"
    assert store.read(3).job.claim_id is None


def test_older_recovery_request_does_not_replay_across_a_later_attempt(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision))
    runtime = _runtime(revision, work_root, claim_expiry=timedelta(minutes=1))
    runtime.start_job(_request())
    recovery = RecoverExpiredClaimsRequest(
        recovered_at="2026-07-24T00:02:01Z",
        actor_id="recovery-agent",
        process_id="recovery-process",
    )
    assert len(runtime.recover_expired_claims(recovery).recovered) == 1
    second_request = _request().model_copy(
        update={
            "attempt_id": "attempt-002",
            "claim_id": "claim-002",
            "claimed_at": recovery.recovered_at,
        }
    )
    runtime.start_job(second_request)
    before = JobStore(work_root).read(1)

    repeated = runtime.recover_expired_claims(recovery)

    assert repeated.recovered == ()
    assert repeated.diagnostics == ()
    assert JobStore(work_root).read(1) == before
    assert before.job.attempt_id == "attempt-002"
    assert AttemptStore(work_root).read("attempt-002", 2).event is None

    runtime.release_job(
        ReleaseJobRequest(
            job_id=1,
            attempt_id=second_request.attempt_id,
            claim_id=second_request.claim_id,
            actor_id=second_request.actor_id,
            process_id=second_request.process_id,
            released_at=recovery.recovered_at,
        )
    )

    resolved_repeat = runtime.recover_expired_claims(recovery)

    assert resolved_repeat.recovered == ()
    assert resolved_repeat.diagnostics == ()
