from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import (
    AttemptStore,
    JobDiagnosticCode,
    JobDisposition,
    JobRecord,
    JobStore,
    NativeRuntime,
    FailJobDiagnosticCode,
    FailJobRequest,
    ReleaseJobDiagnosticCode,
    ReleaseJobRequest,
    StartJobDiagnosticCode,
    StartJobRequest,
    load_change,
    parse_job_mapping,
)


class _History:
    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return b""


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


def test_start_job_stores_claim_and_started_event_then_replays(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    _materialize(JobStore(work_root), _record(revision))
    runtime = NativeRuntime(revision, work_root, _History())

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
    runtime = NativeRuntime(revision, work_root, _History())
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
    runtime = NativeRuntime(revision, work_root, _History())
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
    runtime = NativeRuntime(revision, work_root, _History())
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
    runtime = NativeRuntime(revision, work_root, _History())
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

    result = NativeRuntime(revision, work_root, _History()).start_job(_request())

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

    result = NativeRuntime(revision, work_root, _History()).start_job(_request())

    assert result.diagnostic is not None
    assert result.diagnostic.code is code
    assert result.diagnostic.target == target
    assert store.read(1) == before


def test_job_parser_rejects_unsupported_disposition(revision) -> None:
    result = parse_job_mapping(_record(revision).model_dump() | {"disposition": "claimed"})

    assert result.job is None
    assert result.diagnostics[0].code is JobDiagnosticCode.SCHEMA_INVALID
