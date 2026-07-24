from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from owlbear_kanban import (
    AttemptStore,
    FinishJobDiagnosticCode,
    FinishJobRequest,
    FinishShapeRequest,
    JobDiagnosticCode,
    JobDisposition,
    JobRecord,
    JobStore,
    NativeRuntime,
    FailJobDiagnosticCode,
    FailJobRequest,
    RecoverExpiredClaimsRequest,
    RecoveryDiagnosticCode,
    ReleaseJobDiagnosticCode,
    ReleaseJobRequest,
    StartJobDiagnosticCode,
    StartJobRequest,
    compute_node_plan_digest,
    load_change,
    parse_impact_closure,
    parse_job_mapping,
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
    from owlbear_kanban import JobGeneration, ShapeJob

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


def _copied_revision(tmp_path: Path):
    changes_dir = tmp_path / "changes"
    change_id = "replace-delivery-pipeline"
    shutil.copytree(Path(f".owlbear/changes/{change_id}"), changes_dir / change_id)
    result = load_change(changes_dir, change_id)
    assert result.revision is not None
    return result.revision


def _shape_request(revision, **changes: object) -> FinishShapeRequest:
    target = revision.graph.nodes[0]
    proof = revision.resolve(target.proof)
    closure = {"paths": ["serve/kanban/"], "authority_targets": [target.id, target.proof]}
    return FinishShapeRequest.model_validate(
        {
            "job_id": 1,
            "attempt_id": "attempt-001",
            "claim_id": "claim-001",
            "actor_id": "agent-001",
            "process_id": "process-001",
            "finished_at": "2026-07-24T00:02:00Z",
            "receipt_id": "shape-001",
            "code_revision": "a" * 40,
            "evidence": {"methods": list(proof.method)},
            "evidence_ids": ("shape-review-001",),
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


def test_finish_shape_publishes_one_complete_outcome_and_replays(revision, tmp_path) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(
        JobStore(work_root),
        _record(revision, kind="shape", receipt_id="bootstrap-001"),
    )
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    request = _shape_request(revision)

    result = runtime.finish_shape(request)
    replay = runtime.finish_shape(request)
    changed_replay = runtime.finish_shape(
        request.model_copy(update={"code_revision": "b" * 40, "evidence": {"methods": ["changed"]}})
    )

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
    assert changed_replay.diagnostic is not None
    assert changed_replay.diagnostic.code is FinishJobDiagnosticCode.IDENTITY_CONFLICT
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
def test_finish_shape_rejects_invalid_packet_authority_without_publication(tmp_path, node_plan) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="shape", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    graph_before = (revision.source_dir / "graph.yaml").read_bytes()

    result = runtime.finish_shape(_shape_request(revision, node_plan=node_plan, build_job_ids=(2,)))

    assert result.diagnostic is not None
    assert result.diagnostic.code is FinishJobDiagnosticCode.NODE_PLAN_INVALID
    assert (revision.source_dir / "graph.yaml").read_bytes() == graph_before
    assert tuple(item.job.job_id for item in store.list()) == (1,)
    assert store.list(archived=True) == ()
    assert AttemptStore(work_root).read("attempt-001", 2).event is None


def test_finish_shape_transaction_failure_publishes_nothing(tmp_path, monkeypatch) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="shape", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    graph_before = (revision.source_dir / "graph.yaml").read_bytes()

    def reject_transaction(_transaction) -> None:
        raise TransactionConflictError

    monkeypatch.setattr(RuntimeTransaction, "commit", reject_transaction)

    with pytest.raises(TransactionConflictError):
        runtime.finish_shape(_shape_request(revision))

    assert (revision.source_dir / "graph.yaml").read_bytes() == graph_before
    assert tuple(item.job.job_id for item in store.list()) == (1,)
    assert store.list(archived=True) == ()
    assert AttemptStore(work_root).read("attempt-001", 2).event is None
    assert not (revision.source_dir / "receipts/shape-001.yaml").exists()


def test_finish_build_accept_and_audit_publish_complete_outcomes(tmp_path) -> None:
    revision = _copied_revision(tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, kind="shape", receipt_id="bootstrap-001"))
    runtime = _runtime(revision, work_root)
    runtime.start_job(_request())
    shape = _shape_request(revision)
    assert runtime.finish_shape(shape).diagnostic is None

    packet_closures = tuple(parse_impact_closure(packet["impact_closure"]) for packet in shape.node_plan["packets"])
    finish_methods = shape.evidence
    for job_id, predecessor_receipt_id, closure in (
        (2, "shape-001", packet_closures[0]),
        (3, "build-001", packet_closures[1]),
    ):
        attempt = f"attempt-{job_id:03d}"
        claim = f"claim-{job_id:03d}"
        start = _request().model_copy(update={"job_id": job_id, "attempt_id": attempt, "claim_id": claim})
        assert runtime.start_job(start).diagnostic is None
        result = runtime.finish_build(
            FinishJobRequest(
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
        )
        assert result.diagnostic is None
        assert result.receipt is not None
        assert result.receipt.payload["predecessor_receipt_ids"][-1] == predecessor_receipt_id
        assert result.event is not None
        assert result.event.kind == "succeeded"

    accept_start = _request().model_copy(update={"job_id": 4, "attempt_id": "attempt-004", "claim_id": "claim-004"})
    assert runtime.start_job(accept_start).diagnostic is None
    accept = runtime.finish_accept(
        FinishJobRequest(
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
        )
    )
    assert accept.diagnostic is None
    assert accept.receipt is not None
    assert accept.receipt.payload["predecessor_receipt_ids"] == ("build-001", "build-002")
    assert accept.event is not None
    assert accept.event.kind == "succeeded"

    target = runtime._revision.graph.nodes[0]  # noqa: SLF001 - arrange a same-authority audit job.
    audit_job = _record(
        runtime._revision,  # noqa: SLF001 - use the node-plan authority published by finish_shape.
        job_id=5,
        kind="audit",
        node_plan_digest=compute_node_plan_digest(runtime._revision, target.id),  # noqa: SLF001
        predecessor_job_ids=(4,),
    )
    RuntimeTransaction(work_root, "audit-job", (store.create_participant(audit_job),)).commit()
    audit_start = _request().model_copy(update={"job_id": 5, "attempt_id": "attempt-005", "claim_id": "claim-005"})
    assert runtime.start_job(audit_start).diagnostic is None
    audit = runtime.finish_audit(
        FinishJobRequest(
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
    )
    assert audit.diagnostic is None
    assert audit.receipt is not None
    assert audit.receipt.payload["predecessor_receipt_ids"] == ("accept-001",)
    assert audit.event is not None
    assert audit.event.kind == "succeeded"
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
    _materialize(store, _record(revision, kind="shape", receipt_id="bootstrap-001"))
    history = _History()
    runtime = NativeRuntime(revision, work_root, history, timedelta(minutes=5))
    runtime.start_job(_request())
    shape = _shape_request(revision)
    shape_result = runtime.finish_shape(shape)
    assert shape_result.diagnostic is None
    runtime.start_job(_request().model_copy(update={"job_id": 2, "attempt_id": "attempt-002", "claim_id": "claim-002"}))
    history.changed_paths = b"M\0serve/kanban/src/owlbear_kanban/native_runtime.py\0"
    packet = shape.node_plan["packets"][0]
    request = FinishJobRequest(
        job_id=2,
        attempt_id="attempt-002",
        claim_id="claim-002",
        actor_id="agent-001",
        process_id="process-001",
        finished_at="2026-07-24T00:03:00Z",
        receipt_id="build-001",
        code_revision="b" * 40,
        evidence=shape.evidence,
        impact_closure=parse_impact_closure(packet["impact_closure"]),
    )

    result = runtime.finish_build(request)

    assert result.diagnostic is not None
    assert result.diagnostic.code is FinishJobDiagnosticCode.PREDECESSOR_INVALID
    assert result.diagnostic.lower_code == "ERR_RECEIPT_CODE_PATH_STALE"
    assert store.read(2).job.attempt_id == "attempt-002"
    assert AttemptStore(work_root).read("attempt-002", 2).event is None
    assert store.list(archived=True)[0].job.job_id == 1


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
