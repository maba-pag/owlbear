from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from owlbear_kanban import (
    AttemptStore,
    DispatchDiagnostic,
    DispatchDiagnosticCode,
    DispatchOmissionReason,
    DispatchRuntime,
    FinishJobDiagnosticCode,
    FinishJobRequest,
    FinishPlanRequest,
    JobGeneration,
    JobRecord,
    JobStore,
    NativeRuntime,
    ProofCheckoutManager,
    ReceiptStore,
    RecoverExpiredClaimsRequest,
    RejectAcceptDiagnosticCode,
    ReleaseJobRequest,
    PlanJob,
    StartJobRequest,
    compute_node_plan_digest,
    load_change,
    parse_impact_closure,
)
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError

from .test_native_runtime import _active_accept_scenario, _reject_request
from .test_proof_checkout import _repository


class _History:
    changed_paths = b""

    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return self.changed_paths


class _ProofCheckouts:
    def __init__(self, job_id: int, *, fail_cleanup: bool = False) -> None:
        self._active = {job_id}
        self._fail_cleanup = fail_cleanup

    def cleanup(self, job_id: int) -> None:
        if not self._fail_cleanup:
            self._active.discard(job_id)

    def existing(self, job_id: int) -> object | None:
        return object() if job_id in self._active else None

    def snapshot(self, job_id: int) -> int | None:
        return job_id if job_id in self._active else None

    def restore(self, _job: JobRecord, snapshot: int) -> bool:
        self._active.add(snapshot)
        return True

    def is_orphan(self, path: str) -> bool:
        return int(path) in self._active


@pytest.fixture
def revision():
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    return result.revision


def _record(revision, job_id: int) -> JobRecord:
    return JobRecord(
        schema_version=1,
        job_id=job_id,
        kind="build",
        priority=7,
        created_at="2026-07-24T00:00:00Z",
        updated_at="2026-07-24T00:00:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=revision.graph.nodes[0].id,
    )


def _reader_record(revision, job_id: int, kind: str) -> JobRecord:
    return _record(revision, job_id).model_copy(update={"kind": kind})


def _materialize(store: JobStore, record: JobRecord) -> None:
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


def _request(job_id: int) -> StartJobRequest:
    return StartJobRequest(
        job_id=job_id,
        attempt_id=f"attempt-{job_id:03}",
        claim_id=f"claim-{job_id:03}",
        actor_id="agent-001",
        process_id="process-001",
        claimed_at="2026-07-24T00:01:00Z",
        candidate_revision="a" * 40,
    )


def _copied_revision(revision, tmp_path):
    changes_dir = tmp_path / "changes"
    shutil.copytree(revision.source_dir, changes_dir / revision.change_id)
    (changes_dir / revision.change_id / "plans" / "DN-001.yaml").unlink()
    result = load_change(changes_dir, revision.change_id)
    assert result.revision is not None
    return result.revision


def _plan_request(revision) -> FinishPlanRequest:
    target = revision.graph.nodes[0]
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
            "evidence_ids": ("plan-proof-001",),
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
        }
    )


def test_writer_conflict_and_release_are_atomic(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, 1))
    _materialize(store, _record(revision, 2))
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    started = runtime.start(_request(1))
    assert not isinstance(started, DispatchDiagnostic)
    coordination_path = work_root / "dispatch" / "coordination.yaml"
    before_conflict = (coordination_path.read_bytes(), store.read(2), tuple((work_root / "attempts").rglob("*.json")))

    conflict = runtime.start(_request(2))

    assert isinstance(conflict, DispatchDiagnostic)
    assert conflict.code is DispatchDiagnosticCode.WRITER_CONFLICT
    assert conflict.holder_job_ids == (1,)
    assert (
        coordination_path.read_bytes(),
        store.read(2),
        tuple((work_root / "attempts").rglob("*.json")),
    ) == before_conflict

    released = runtime.release(
        ReleaseJobRequest(
            job_id=1,
            attempt_id="attempt-001",
            claim_id="claim-001",
            actor_id="agent-001",
            process_id="process-001",
            released_at="2026-07-24T00:02:00Z",
        )
    )

    assert not isinstance(released, DispatchDiagnostic)
    assert "readers: []" in coordination_path.read_text(encoding="utf-8")


def test_readers_coexist_and_block_writer(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _reader_record(revision, 1, "accept"))
    _materialize(store, _reader_record(revision, 2, "audit"))
    _materialize(store, _record(revision, 3))
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    assert not isinstance(runtime.start(_request(1)), DispatchDiagnostic)
    assert not isinstance(runtime.start(_request(2)), DispatchDiagnostic)
    conflict = runtime.start(_request(3))

    assert isinstance(conflict, DispatchDiagnostic)
    assert conflict.code is DispatchDiagnosticCode.WRITER_CONFLICT
    assert conflict.holder_job_ids == (1, 2)


def _dispatch_accept_rejection(tmp_path: Path, *, fail_cleanup: bool = False):
    revision, work_root, native, start = _active_accept_scenario(tmp_path)
    released = native.release_job(
        ReleaseJobRequest(
            job_id=start.job_id,
            attempt_id=start.attempt_id,
            claim_id=start.claim_id,
            actor_id=start.actor_id,
            process_id=start.process_id,
            released_at="2026-07-24T00:04:30Z",
        )
    )
    assert released.diagnostic is None
    proof_checkouts = _ProofCheckouts(start.job_id, fail_cleanup=fail_cleanup)
    runtime = DispatchRuntime(native, work_root, proof_checkouts)  # type: ignore[arg-type]
    current = start.model_copy(update={"attempt_id": "attempt-014", "claim_id": "claim-014"})
    started = runtime.start(current)
    assert not isinstance(started, DispatchDiagnostic)
    assert started.diagnostic is None
    return revision, work_root, runtime, proof_checkouts, current


def test_reject_accept_releases_reader_cleans_checkout_and_replays(tmp_path: Path) -> None:
    revision, work_root, runtime, proof_checkouts, start = _dispatch_accept_rejection(tmp_path)
    request = _reject_request(revision, start)

    rejected = runtime.reject_accept(request)
    replayed = runtime.reject_accept(request)

    assert not isinstance(rejected, DispatchDiagnostic)
    assert rejected.diagnostic is None
    assert replayed == rejected
    assert "readers: []" in (work_root / "dispatch/coordination.yaml").read_text(encoding="utf-8")
    assert not proof_checkouts.is_orphan(str(start.job_id))


def test_reject_accept_cleanup_failure_preserves_all_runtime_state(tmp_path: Path) -> None:
    revision, work_root, runtime, proof_checkouts, start = _dispatch_accept_rejection(tmp_path, fail_cleanup=True)
    request = _reject_request(revision, start)
    work_before = {
        str(path.relative_to(work_root)): path.read_bytes() for path in work_root.rglob("*") if path.is_file()
    }
    receipts_before = {
        path.name: path.read_bytes() for path in (runtime._native._revision.source_dir / "receipts").glob("*.yaml")
    }

    rejected = runtime.reject_accept(request)

    assert not isinstance(rejected, DispatchDiagnostic)
    assert rejected.diagnostic is not None
    assert rejected.diagnostic.code is RejectAcceptDiagnosticCode.CLEANUP_FAILED
    assert work_before == {
        str(path.relative_to(work_root)): path.read_bytes() for path in work_root.rglob("*") if path.is_file()
    }
    assert receipts_before == {
        path.name: path.read_bytes() for path in (runtime._native._revision.source_dir / "receipts").glob("*.yaml")
    }
    assert proof_checkouts.is_orphan(str(start.job_id))


def test_reject_accept_transaction_conflict_restores_cleaned_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    revision, work_root, native, first_start = _active_accept_scenario(tmp_path)
    released = native.release_job(
        ReleaseJobRequest(
            job_id=first_start.job_id,
            attempt_id=first_start.attempt_id,
            claim_id=first_start.claim_id,
            actor_id=first_start.actor_id,
            process_id=first_start.process_id,
            released_at="2026-07-24T00:04:30Z",
        )
    )
    assert released.diagnostic is None
    repository, commit = _repository(tmp_path)
    checkouts = ProofCheckoutManager(repository, tmp_path / "proof")
    runtime = DispatchRuntime(native, work_root, checkouts)
    start = first_start.model_copy(update={"attempt_id": "attempt-014", "claim_id": "claim-014"})
    started = runtime.start(start)
    assert not isinstance(started, DispatchDiagnostic)
    assert started.diagnostic is None
    checkout = checkouts.materialize(
        JobStore(work_root).read(start.job_id).job,
        commit,
        environment={"TOOLCHAIN": "uv"},
        replacements=("temporary repository",),
    ).checkout
    assert checkout is not None
    manifest_before = checkout.manifest.read_bytes()
    work_before = {
        str(path.relative_to(work_root)): path.read_bytes() for path in work_root.rglob("*") if path.is_file()
    }
    receipts_before = {
        path.name: path.read_bytes() for path in (native._revision.source_dir / "receipts").glob("*.yaml")
    }
    original_commit = RuntimeTransaction.commit

    def fail_rejection(transaction: RuntimeTransaction, *, failure=None) -> None:
        if transaction._transaction_id.startswith("reject-"):  # noqa: SLF001 - inject after checkout cleanup.
            raise TransactionConflictError
        original_commit(transaction, failure=failure)

    monkeypatch.setattr(RuntimeTransaction, "commit", fail_rejection)

    rejected = runtime.reject_accept(_reject_request(revision, start))

    assert not isinstance(rejected, DispatchDiagnostic)
    assert rejected.diagnostic is not None
    assert rejected.diagnostic.code is RejectAcceptDiagnosticCode.IDENTITY_CONFLICT
    assert work_before == {
        str(path.relative_to(work_root)): path.read_bytes() for path in work_root.rglob("*") if path.is_file()
    }
    assert receipts_before == {
        path.name: path.read_bytes() for path in (native._revision.source_dir / "receipts").glob("*.yaml")
    }
    restored = checkouts.existing(start.job_id)
    assert restored is not None
    assert restored.commit == commit
    assert restored.manifest.read_bytes() == manifest_before


def test_expired_recovery_clears_its_writer_holder(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, 1))
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=1))
    runtime = DispatchRuntime(native, work_root)
    assert not isinstance(runtime.start(_request(1)), DispatchDiagnostic)
    request = RecoverExpiredClaimsRequest(
        recovered_at="2026-07-24T00:02:00Z",
        actor_id="recovery-agent",
        process_id="recovery-process",
    )

    at_boundary = runtime.recover_expired_claims(request.model_copy(update={"recovered_at": "2026-07-24T00:02:00Z"}))
    assert not isinstance(at_boundary, DispatchDiagnostic)
    assert at_boundary.recovered == ()

    recovered = runtime.recover_expired_claims(request.model_copy(update={"recovered_at": "2026-07-24T00:02:01Z"}))

    assert not isinstance(recovered, DispatchDiagnostic)
    assert len(recovered.recovered) == 1
    coordination = (work_root / "dispatch" / "coordination.yaml").read_text(encoding="utf-8")
    assert "readers: []" in coordination


def test_finish_plan_build_and_audit_publish_with_coordination_release(revision, tmp_path) -> None:
    revision = _copied_revision(revision, tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, 1).model_copy(update={"kind": "plan", "receipt_id": "bootstrap-001"}))
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)
    plan_request = _plan_request(revision)

    assert not isinstance(runtime.start(_request(1)), DispatchDiagnostic)
    plan = runtime.finish_plan(plan_request)
    assert plan.diagnostic is None
    assert plan.receipt is not None
    assert plan.event is not None
    assert "writer:\nreaders: []" in (work_root / "dispatch" / "coordination.yaml").read_text(encoding="utf-8")

    build_request = FinishJobRequest(
        job_id=2,
        attempt_id="attempt-002",
        claim_id="claim-002",
        actor_id="agent-001",
        process_id="process-001",
        finished_at="2026-07-24T00:03:00Z",
        receipt_id="build-001",
        code_revision="a" * 40,
        evidence=plan_request.evidence,
        evidence_ids=("build-proof-001",),
        impact_closure=parse_impact_closure(plan_request.node_plan["packets"][0]["impact_closure"]),
    )
    assert not isinstance(runtime.start(_request(2)), DispatchDiagnostic)
    build = runtime.finish_build(build_request)
    assert build.diagnostic is None
    assert build.receipt is not None
    assert build.event is not None
    assert "writer:\nreaders: []" in (work_root / "dispatch" / "coordination.yaml").read_text(encoding="utf-8")

    current_revision = native._revision  # noqa: SLF001 - plan completion replaces the active authority revision.
    _materialize(
        store,
        _reader_record(current_revision, 5, "audit").model_copy(
            update={"node_plan_digest": compute_node_plan_digest(current_revision, current_revision.graph.nodes[0].id)}
        ),
    )
    audit_request = FinishJobRequest(
        job_id=5,
        attempt_id="attempt-005",
        claim_id="claim-005",
        actor_id="agent-001",
        process_id="process-001",
        finished_at="2026-07-24T00:04:00Z",
        receipt_id="audit-001",
        code_revision="a" * 40,
        evidence=plan_request.evidence,
        evidence_ids=("audit-proof-001",),
    )
    assert not isinstance(runtime.start(_request(5)), DispatchDiagnostic)
    audit = runtime.finish_audit(audit_request)

    assert audit.diagnostic is None
    assert audit.receipt is not None
    assert audit.event is not None
    assert "readers: []" in (work_root / "dispatch" / "coordination.yaml").read_text(encoding="utf-8")
    assert tuple(event.kind for event in AttemptStore(work_root).list()) == (
        "started",
        "succeeded",
        "started",
        "succeeded",
        "started",
        "succeeded",
    )


def test_finish_diagnostics_and_coordination_occ_conflicts_publish_nothing(revision, tmp_path, monkeypatch) -> None:
    revision = _copied_revision(revision, tmp_path)
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, 1).model_copy(update={"kind": "plan", "receipt_id": "bootstrap-001"}))
    runtime = DispatchRuntime(NativeRuntime(revision, work_root, _History(), timedelta(minutes=5)), work_root)
    request = _plan_request(revision)
    coordination_path = work_root / "dispatch" / "coordination.yaml"

    assert not isinstance(runtime.start(_request(1)), DispatchDiagnostic)
    diagnostic = runtime.finish_plan(request.model_copy(update={"claim_id": "wrong-claim"}))
    assert diagnostic.diagnostic is not None
    assert diagnostic.diagnostic.code is FinishJobDiagnosticCode.NON_OWNER
    assert store.read(1).job.attempt_id == "attempt-001"
    assert AttemptStore(work_root).read("attempt-001", 2).event is None
    assert not (revision.source_dir / "receipts" / "plan-001.yaml").exists()
    assert "job_id: 1" in coordination_path.read_text(encoding="utf-8")

    original = runtime._coordination.replacement_participant  # noqa: SLF001 - create a real stale-token conflict.

    def stale_token(replacement, token):
        coordination_path.write_bytes(coordination_path.read_bytes() + b"\n")
        return original(replacement, token)

    monkeypatch.setattr(runtime._coordination, "replacement_participant", stale_token)  # noqa: SLF001
    with pytest.raises(TransactionConflictError):
        runtime.finish_plan(request)

    assert store.read(1).job.attempt_id == "attempt-001"
    assert AttemptStore(work_root).read("attempt-001", 2).event is None
    assert not (revision.source_dir / "receipts" / "plan-001.yaml").exists()
    assert "job_id: 1" in coordination_path.read_text(encoding="utf-8")


def test_pick_waves_is_deterministic_and_uses_current_job_state(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _reader_record(revision, 1, "accept"))
    _materialize(store, _record(revision, 2))
    _materialize(store, _reader_record(revision, 3, "audit"))
    blocked = store.read(3)
    store.update(blocked.job.model_copy(update={"block_id": "block-003"}), blocked.token)
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    first = runtime.pick_waves("a" * 40, size=2)
    assert [[entry.job_id for entry in wave] for wave in first.waves] == [[1], [2]]
    assert [entry.agent_profile for wave in first.waves for entry in wave] == ["acceptor", "builder"]
    assert first.omissions[0].reason is DispatchOmissionReason.BLOCKED
    assert runtime.pick_waves("a" * 40, size=2) == first

    assert not isinstance(runtime.start(_request(2)), DispatchDiagnostic)
    fresh = runtime.pick_waves("a" * 40, size=2)
    assert [[entry.job_id for entry in wave] for wave in fresh.waves] == [[1]]
    assert [(item.job_id, item.reason) for item in fresh.omissions] == [
        (2, DispatchOmissionReason.CLAIMED),
        (3, DispatchOmissionReason.BLOCKED),
    ]


def test_pick_waves_orders_plan_frontier_by_delivery_topology(revision, tmp_path, monkeypatch) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    for job_id, node_id in ((3, "DN-004"), (2, "DN-002"), (1, "DN-001")):
        _materialize(
            store,
            _record(revision, job_id).model_copy(
                update={"kind": "plan", "target_node_id": node_id, "receipt_id": "bootstrap-001"}
            ),
        )
    runtime = DispatchRuntime(NativeRuntime(revision, work_root, _History(), timedelta(minutes=5)), work_root)
    stored_jobs = runtime._jobs.list()  # noqa: SLF001 - simulate an arbitrary persistence order.
    monkeypatch.setattr(runtime._jobs, "list", lambda: tuple(reversed(stored_jobs)))  # noqa: SLF001

    plan = runtime.pick_waves("a" * 40, size=3)

    assert [[entry.job_id for entry in wave] for wave in plan.waves] == [[1], [2], [3]]
    assert [entry.agent_profile for wave in plan.waves for entry in wave] == ["planner", "planner", "planner"]


def test_pick_waves_omits_stale_node_plan_digest(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    _materialize(store, _record(revision, 1).model_copy(update={"node_plan_digest": "a" * 64}))
    runtime = DispatchRuntime(NativeRuntime(revision, work_root, _History(), timedelta(minutes=5)), work_root)

    plan = runtime.pick_waves("a" * 40, size=1)

    assert plan.waves == ()
    assert [(item.job_id, item.reason) for item in plan.omissions] == [(1, DispatchOmissionReason.AUTHORITY_STALE)]


def test_pick_waves_separates_dependent_readers(revision, tmp_path) -> None:
    changes_dir = tmp_path / "changes"
    shutil.copytree(revision.source_dir, changes_dir / revision.change_id)
    loaded = load_change(changes_dir, revision.change_id)
    assert loaded.revision is not None
    revision = loaded.revision
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    predecessor = _reader_record(revision, 1, "accept").model_copy(update={"receipt_id": "accept-001"})
    _materialize(store, predecessor)
    _materialize(store, _reader_record(revision, 2, "audit"))
    _materialize(
        store,
        _reader_record(revision, 3, "audit").model_copy(update={"predecessor_job_ids": (1,)}),
    )
    node = revision.graph.nodes[0]
    proof = revision.resolve(node.proof)
    receipt = ReceiptStore(revision).create(
        "accept-001",
        {
            "schema_version": 1,
            "kind": "accept",
            "receipt_id": "accept-001",
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "issued_at": "2026-07-24T00:00:00Z",
            "target_node_id": node.id,
            "node_plan_digest": compute_node_plan_digest(revision, node.id),
            "predecessor_receipt_ids": [],
            "evidence": {"methods": list(proof.method)},
            "code_revision": "a" * 40,
            "impact_closure": {"paths": ["serve/kanban/"], "authority_targets": [node.id, node.proof]},
        },
    )
    assert receipt.receipt is not None
    native = NativeRuntime(revision, work_root, _History(), timedelta(minutes=5))
    runtime = DispatchRuntime(native, work_root)

    plan = runtime.pick_waves("a" * 40, size=3)

    assert [[entry.job_id for entry in wave] for wave in plan.waves] == [[1, 2], [3]]
