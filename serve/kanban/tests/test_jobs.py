from __future__ import annotations

from copy import deepcopy
from multiprocessing import get_context
from pathlib import Path

import pytest

from owlbear_kanban import (
    JobConcurrencyError,
    JobConflictError,
    JobDiagnosticCode,
    JobDisposition,
    JobSequenceError,
    JobStore,
    JobStorePathError,
    load_change,
    parse_job_mapping,
    plan_jobs,
    project_job,
    read_job_generation,
)
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError


def _update_from_process(work_root: str, job: object, token: str, queue: object) -> None:
    store = JobStore(Path(work_root))
    try:
        store.update(job.model_copy(update={"disposition": JobDisposition.CANCELLED}), token)  # type: ignore[attr-defined]
    except JobConcurrencyError:
        queue.put("stale")  # type: ignore[attr-defined]
    else:
        queue.put("updated")  # type: ignore[attr-defined]


@pytest.fixture
def revision():
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    return result.revision


def _planned_mapping(revision) -> dict[str, object]:
    generation = plan_jobs(
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
        "packet_id": f"{target_node_id or revision.graph.nodes[0].id}-PK-001" if kind == "build" else None,
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


def test_plan_jobs_preserves_authored_order_and_operational_identity(revision) -> None:
    generation = plan_jobs(
        revision,
        "receipt-001",
        range(1, len(revision.graph.nodes) + 1),
        priority=7,
        timestamp="2026-07-22T12:00:00Z",
    )

    assert [job.target_node_id for job in generation.jobs] == [node.id for node in revision.graph.nodes]
    assert all(job.kind == "plan" for job in generation.jobs)
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


@pytest.mark.parametrize("kind", ["plan", "build", "accept", "audit", "supersession"])
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
    job = _job_mapping(revision, "plan")
    job[field] = value

    result = parse_job_mapping(job)

    assert result.job is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == [expected]


@pytest.mark.parametrize(
    ("kind", "packet_id"),
    [
        ("build", None),
        ("plan", "DN-001-PK-001"),
        ("accept", "DN-001-PK-001"),
        ("audit", "DN-001-PK-001"),
    ],
)
def test_public_job_parser_enforces_build_only_packet_authority(revision, kind: str, packet_id: str | None) -> None:
    value = _job_mapping(revision, kind)
    value["packet_id"] = packet_id

    result = parse_job_mapping(value)

    assert result.job is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == [JobDiagnosticCode.SCHEMA_INVALID]


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


def test_job_store_materializes_generations_idempotently_and_rejects_conflicts(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    generation = plan_jobs(
        revision,
        "receipt-001",
        range(1, len(revision.graph.nodes) + 1),
        priority=7,
        timestamp="2026-07-22T12:00:00Z",
    )

    created = store.materialize(generation)
    replayed = store.materialize(generation)

    assert replayed == created
    assert store.list() == created
    assert [item.job.job_id for item in created] == list(range(1, len(created) + 1))
    conflicting = generation.model_copy(
        update={"jobs": (generation.jobs[0].model_copy(update={"priority": 8}), *generation.jobs[1:])}
    )
    with pytest.raises(JobConflictError) as exc_info:
        store.materialize(conflicting)
    assert exc_info.value.code == "ERR_JOB_CONFLICT"
    partial_root = tmp_path / "partial-work"
    partial_root.mkdir()
    partial_store = JobStore(partial_root)
    partial_store.materialize(generation.model_copy(update={"jobs": (generation.jobs[1],)}))
    conflicting_later = generation.model_copy(
        update={
            "jobs": (*generation.jobs[:1], generation.jobs[1].model_copy(update={"priority": 8}), *generation.jobs[2:])
        }
    )
    with pytest.raises(JobConflictError):
        partial_store.materialize(conflicting_later)
    assert [item.job.job_id for item in partial_store.list()] == [generation.jobs[1].job_id]


def test_job_store_uses_occ_for_updates_and_archives(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    generation = plan_jobs(
        revision,
        "receipt-001",
        range(1, len(revision.graph.nodes) + 1),
        timestamp="2026-07-22T12:00:00Z",
    )
    stored = store.materialize(generation)[0]

    updated = store.update(stored.job.model_copy(update={"disposition": JobDisposition.CANCELLED}), stored.token)

    assert updated.job.disposition is JobDisposition.CANCELLED
    assert updated.token != stored.token
    with pytest.raises(JobConcurrencyError) as exc_info:
        store.update(stored.job, stored.token)
    assert exc_info.value.code == "ERR_JOB_OCC_STALE"
    archived = store.archive(updated.job.job_id, updated.token)
    assert archived == store.read(updated.job.job_id, archived=True)
    assert store.list(archived=True) == (archived,)
    with pytest.raises(FileNotFoundError):
        store.read(updated.job.job_id)


@pytest.mark.filterwarnings("ignore:This process.*use of fork.*:DeprecationWarning")
def test_job_store_allows_only_one_process_to_update_a_token(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    generation = plan_jobs(
        revision,
        "receipt-001",
        range(1, len(revision.graph.nodes) + 1),
        timestamp="2026-07-22T12:00:00Z",
    )
    stored = store.materialize(generation)[0]
    context = get_context("fork")
    queue = context.Queue()
    processes = [
        context.Process(target=_update_from_process, args=(str(work_root), stored.job, stored.token, queue))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()

    assert [process.exitcode for process in processes] == [0, 0]
    assert sorted(queue.get() for _ in processes) == ["stale", "updated"]
    assert store.read(stored.job.job_id).job.disposition is JobDisposition.CANCELLED


def test_job_store_does_not_follow_substituted_job_symlink(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("outside bytes", encoding="utf-8")
    store = JobStore(work_root)
    generation = plan_jobs(
        revision,
        "receipt-001",
        range(1, len(revision.graph.nodes) + 1),
        timestamp="2026-07-22T12:00:00Z",
    )
    stored = store.materialize(generation)[0]
    job_path = work_root / "jobs" / f"{stored.job.job_id}.yaml"
    job_path.unlink()
    job_path.symlink_to(outside)

    with pytest.raises(OSError):
        store.read(stored.job.job_id)

    assert outside.read_text(encoding="utf-8") == "outside bytes"


def test_job_store_reserves_contiguous_ids_and_rejects_stale_competitors(tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)

    first = store.reserve_job_ids(3)
    competing = store.reserve_job_ids(3)

    assert first.job_ids == (1, 2, 3)
    assert competing.job_ids == first.job_ids
    RuntimeTransaction(work_root, "reserve-first", (first.participant,)).commit()
    with pytest.raises(TransactionConflictError):
        RuntimeTransaction(work_root, "reserve-competing", (competing.participant,)).commit()

    following = store.reserve_job_ids(2)
    competing_replacement = store.reserve_job_ids(2)
    assert following.job_ids == (4, 5)
    assert competing_replacement.job_ids == following.job_ids
    RuntimeTransaction(work_root, "reserve-following", (following.participant,)).commit()
    with pytest.raises(TransactionConflictError):
        RuntimeTransaction(work_root, "reserve-competing-replacement", (competing_replacement.participant,)).commit()
    assert store.reserve_job_ids(1).job_ids == (6,)


def test_job_store_reservation_never_reuses_active_or_archived_ids(revision, tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    generation = plan_jobs(
        revision,
        "receipt-001",
        range(10, 10 + len(revision.graph.nodes)),
        timestamp="2026-07-22T12:00:00Z",
    )
    created = store.materialize(generation)
    store.archive(created[-1].job.job_id, created[-1].token)

    reservation = store.reserve_job_ids(2)

    assert reservation.job_ids == (created[-1].job.job_id + 1, created[-1].job.job_id + 2)
    RuntimeTransaction(work_root, "reserve-after-archive", (reservation.participant,)).commit()
    assert store.reserve_job_ids(1).job_ids == (reservation.job_ids[-1] + 1,)


@pytest.mark.parametrize(
    "sequence_text",
    [
        "---\nsequence: [unterminated\n",
        "---\nschema_version: 1\nlast_job_id: 0\nreservation_id: 0123456789abcdef0123456789abcdef\n",
    ],
)
def test_job_store_reservation_rejects_invalid_sequence_without_mutation(tmp_path, sequence_text: str) -> None:
    work_root = tmp_path / "work"
    (work_root / "jobs").mkdir(parents=True)
    (work_root / "archive").mkdir()
    sequence_path = work_root / "job-sequence.yaml"
    active_path = work_root / "jobs" / "1.yaml"
    archived_path = work_root / "archive" / "2.yaml"
    sequence_path.write_text(sequence_text, encoding="utf-8")
    active_path.write_bytes(b"active bytes")
    archived_path.write_bytes(b"archive bytes")
    before = (sequence_path.read_bytes(), active_path.read_bytes(), archived_path.read_bytes())

    with pytest.raises(JobSequenceError) as exc_info:
        JobStore(work_root).reserve_job_ids(1)

    assert exc_info.value.code == "ERR_JOB_SEQUENCE_INVALID"
    assert (sequence_path.read_bytes(), active_path.read_bytes(), archived_path.read_bytes()) == before


def test_job_store_reservation_rejects_unsafe_root_without_mutation(tmp_path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    sentinel = work_root / "sentinel"
    sentinel.write_bytes(b"existing bytes")

    unsafe_root = tmp_path / "unsafe-work"
    unsafe_root.symlink_to(work_root, target_is_directory=True)
    with pytest.raises(JobStorePathError) as path_exc_info:
        JobStore(unsafe_root).reserve_job_ids(1)
    assert path_exc_info.value.code == "ERR_JOB_PATH_UNSAFE"
    assert sentinel.read_bytes() == b"existing bytes"
    assert tuple(work_root.iterdir()) == (sentinel,)
