from __future__ import annotations

import contextlib
from io import StringIO
import multiprocessing
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread
from typing import Any

import pytest
import yaml

from owlbear_kanban.attempts import AttemptEvent, AttemptStore
import owlbear_kanban.jobs as jobs_module
import owlbear_kanban.runtime_transaction as transaction_module
from owlbear_kanban.jobs import JobConcurrencyError, JobDisposition, JobGeneration, JobStore, PlanJob
from owlbear_kanban.runtime_transaction import (
    MoveTransactionParticipant,
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionManifestError,
    TransactionParticipant,
    TransactionPathError,
)
from owlbear_kanban.storage_io import locked_roots
from owlbear_kanban.yaml_rt import make_yaml


def _job_store_with_record(tmp_path: Path) -> tuple[JobStore, Path, object, bytes]:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = JobStore(work_root)
    generation = JobGeneration(
        schema_version=1,
        change_id="change-001",
        delivery_digest="a" * 64,
        receipt_id="receipt-001",
        jobs=(
            PlanJob(
                job_id=1,
                kind="plan",
                priority=0,
                created_at="2026-07-23T00:00:00Z",
                updated_at="2026-07-23T00:00:00Z",
                change_id="change-001",
                delivery_digest="a" * 64,
                target_node_id="DN-001",
                receipt_id="receipt-001",
            ),
        ),
    )
    stored = store.materialize(generation)[0]
    destination = work_root / "jobs/1.yaml"
    replacement = stored.job.model_copy(update={"disposition": JobDisposition.SUPERSEDED})
    stream = StringIO()
    make_yaml(explicit_start=True).dump(replacement.model_dump(mode="json"), stream)
    return store, destination, stored, stream.getvalue().encode()


def _attempt_event(attempt_id: str) -> AttemptEvent:
    return AttemptEvent(
        schema_version=1,
        attempt_id=attempt_id,
        claim_id=f"claim-{attempt_id}",
        job_id=1,
        change_id="change-001",
        delivery_digest="a" * 64,
        target_node_id="DN-001",
        actor_id="builder",
        process_id=attempt_id,
        sequence=1,
        timestamp="2026-07-23T00:00:00Z",
        kind="started",
    )


def _commit_mixed_process(
    transaction_details: tuple[Path, Path, str, str],
    barrier: Any,
    outcomes: Any,
) -> None:
    work_root, manifest_root, disposition, attempt_id = transaction_details
    job_store = JobStore(work_root)
    stored = job_store.read(1)
    event = _attempt_event(attempt_id)
    transaction = RuntimeTransaction(
        manifest_root,
        attempt_id,
        (
            job_store.replacement_participant(
                stored.job.model_copy(update={"disposition": JobDisposition(disposition)}), stored.token
            ),
            AttemptStore(work_root).create_participant(event),
        ),
    )
    barrier.wait()
    try:
        transaction.commit()
    except TransactionConflictError:
        outcomes.put((disposition, attempt_id, TransactionConflictError.code))
    else:
        outcomes.put((disposition, attempt_id, "success"))


def test_locked_roots_rejects_symlink_roots_and_lock_files(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    symlink_root = tmp_path / "symlink-root"
    symlink_root.symlink_to(root, target_is_directory=True)

    with pytest.raises(ValueError, match="must not be a symlink"), locked_roots((symlink_root,)):
        pass

    (root / ".storage.lock").symlink_to(tmp_path / "outside")
    with pytest.raises(OSError), locked_roots((root,)):
        pass


def test_job_update_and_transaction_replacement_serialize_on_shared_root_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, destination, stored, replacement_bytes = _job_store_with_record(tmp_path)
    update_started = Event()
    release_update = Event()
    update_done = Event()
    transaction_done = Event()
    results: dict[str, BaseException | None] = {"update": None, "transaction": None}
    original_locked_roots = jobs_module.locked_roots

    @contextlib.contextmanager
    def pause_job_update(roots: object):
        with original_locked_roots(roots):  # type: ignore[arg-type]
            update_started.set()
            assert release_update.wait(timeout=2)
            yield

    monkeypatch.setattr(jobs_module, "locked_roots", pause_job_update)

    def update() -> None:
        try:
            store.update(stored.job.model_copy(update={"disposition": JobDisposition.CANCELLED}), stored.token)
        except BaseException as exc:  # noqa: BLE001 - retain thread failure for assertion.
            results["update"] = exc
        finally:
            update_done.set()

    transaction = RuntimeTransaction(
        tmp_path / "change",
        "shared-update",
        (
            ReplacementTransactionParticipant(
                destination.parents[1], Path("jobs/1.yaml"), destination.read_bytes(), replacement_bytes
            ),
        ),
    )

    def commit() -> None:
        try:
            transaction.commit()
        except BaseException as exc:  # noqa: BLE001 - retain thread failure for assertion.
            results["transaction"] = exc
        finally:
            transaction_done.set()

    update_thread = Thread(target=update)
    update_thread.start()
    assert update_started.wait(timeout=2)
    transaction_thread = Thread(target=commit)
    transaction_thread.start()
    assert not transaction_done.wait(timeout=0.1)
    release_update.set()
    assert update_done.wait(timeout=2)
    assert transaction_done.wait(timeout=2)
    update_thread.join()
    transaction_thread.join()

    assert results["update"] is None
    assert isinstance(results["transaction"], TransactionConflictError)
    assert destination.read_bytes() != replacement_bytes


def test_transaction_replacement_and_job_update_serialize_on_shared_root_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, destination, stored, replacement_bytes = _job_store_with_record(tmp_path)
    transaction_started = Event()
    release_transaction = Event()
    transaction_done = Event()
    update_done = Event()
    results: dict[str, BaseException | None] = {"update": None, "transaction": None}
    original_locked_roots = transaction_module.locked_roots

    @contextlib.contextmanager
    def pause_transaction_commit(roots: object):
        with original_locked_roots(roots):  # type: ignore[arg-type]
            transaction_started.set()
            assert release_transaction.wait(timeout=2)
            yield

    monkeypatch.setattr(transaction_module, "locked_roots", pause_transaction_commit)
    transaction = RuntimeTransaction(
        tmp_path / "change",
        "shared-transaction",
        (
            ReplacementTransactionParticipant(
                destination.parents[1], Path("jobs/1.yaml"), destination.read_bytes(), replacement_bytes
            ),
        ),
    )

    def commit() -> None:
        try:
            transaction.commit()
        except BaseException as exc:  # noqa: BLE001 - retain thread failure for assertion.
            results["transaction"] = exc
        finally:
            transaction_done.set()

    def update() -> None:
        try:
            store.update(stored.job.model_copy(update={"disposition": JobDisposition.CANCELLED}), stored.token)
        except BaseException as exc:  # noqa: BLE001 - retain thread failure for assertion.
            results["update"] = exc
        finally:
            update_done.set()

    transaction_thread = Thread(target=commit)
    transaction_thread.start()
    assert transaction_started.wait(timeout=2)
    update_thread = Thread(target=update)
    update_thread.start()
    assert not update_done.wait(timeout=0.1)
    release_transaction.set()
    assert transaction_done.wait(timeout=2)
    assert update_done.wait(timeout=2)
    transaction_thread.join()
    update_thread.join()

    assert results["transaction"] is None
    assert isinstance(results["update"], JobConcurrencyError)
    assert destination.read_bytes() == replacement_bytes


@pytest.mark.parametrize("stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_recovery_completes_lifecycle_job_and_activity_participants(tmp_path: Path, stage: str) -> None:
    change_root = tmp_path / "change"
    work_root = tmp_path / "work"
    transaction = RuntimeTransaction(
        change_root,
        "lifecycle",
        (
            TransactionParticipant(work_root, Path("jobs/plan.yaml"), b"plan"),
            TransactionParticipant(work_root, Path("activity/plan.jsonl"), b'{"event":"started"}\n'),
        ),
    )

    def interrupt(current_stage: str) -> None:
        if current_stage == stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    RuntimeTransaction.recover_all(change_root, roots=(change_root, work_root))

    assert (work_root / "jobs/plan.yaml").read_bytes() == b"plan"
    assert (work_root / "activity/plan.jsonl").read_bytes() == b'{"event":"started"}\n'
    assert not list((change_root / ".runtime-transactions").glob("*.yaml"))


def test_transaction_rejects_conflicts_and_escaped_destinations_without_mutation(tmp_path: Path) -> None:
    root = tmp_path / "work"
    destination = root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"committed")
    conflicting = RuntimeTransaction(
        tmp_path / "change",
        "conflict",
        (TransactionParticipant(root, Path("jobs/plan.yaml"), b"replacement"),),
    )
    escaped = RuntimeTransaction(
        tmp_path / "change",
        "escaped",
        (TransactionParticipant(root, Path("../outside.yaml"), b"unsafe"),),
    )

    with pytest.raises(TransactionConflictError):
        conflicting.commit()
    with pytest.raises(TransactionPathError):
        escaped.commit()

    assert destination.read_bytes() == b"committed"
    assert not (tmp_path / "outside.yaml").exists()


@pytest.mark.parametrize("stage", ["before-publication", "after-first-publication", "before-manifest-cleanup"])
def test_replacement_participant_recovers_and_replays(tmp_path: Path, stage: str) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    destination = work_root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"expected")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/plan.yaml"), b"expected", b"replacement"),),
    )

    def interrupt(current_stage: str) -> None:
        if current_stage == stage:
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))
    RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))

    assert destination.read_bytes() == b"replacement"
    assert not list((manifest_root / ".runtime-transactions").glob("*.yaml"))


def test_abort_restores_exact_prepublication_state_for_mixed_participants(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    immutable = work_root / "evidence/existing.yaml"
    replacement = work_root / "jobs/1.yaml"
    move_source = work_root / "jobs/2.yaml"
    move_destination = work_root / "archive/2.yaml"
    immutable.parent.mkdir(parents=True)
    replacement.parent.mkdir(parents=True)
    immutable.write_bytes(b"existing")
    replacement.write_bytes(b"before")
    move_source.write_bytes(b"active")
    transaction = RuntimeTransaction(
        manifest_root,
        "abort-mixed",
        (
            TransactionParticipant(work_root, Path("evidence/existing.yaml"), b"existing"),
            ReplacementTransactionParticipant(work_root, Path("jobs/1.yaml"), b"before", b"after"),
            MoveTransactionParticipant(
                work_root,
                Path("jobs/2.yaml"),
                Path("archive/2.yaml"),
                b"active",
                b"archived",
            ),
        ),
    )

    def interrupt(stage: str) -> None:
        if stage == "before-manifest-cleanup":
            message = "handled failure"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="handled failure"):
        transaction.commit(failure=interrupt)
    transaction.abort()

    assert immutable.read_bytes() == b"existing"
    assert replacement.read_bytes() == b"before"
    assert move_source.read_bytes() == b"active"
    assert not move_destination.exists()
    assert not list((manifest_root / ".runtime-transactions").glob("*.yaml"))


def test_replacement_participant_rejects_conflicts_and_invalid_recovery_manifests(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    destination = work_root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"different")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/plan.yaml"), b"expected", b"replacement"),),
    )

    with pytest.raises(TransactionConflictError):
        transaction.commit()
    assert destination.read_bytes() == b"different"

    manifest_directory = manifest_root / ".runtime-transactions"
    manifest_directory.mkdir(parents=True, exist_ok=True)
    (manifest_directory / "malformed.yaml").write_text("schema_version: 2\nparticipants: [bad]\n", encoding="utf-8")

    with pytest.raises(TransactionManifestError):
        RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))
    assert destination.read_bytes() == b"different"


@pytest.mark.parametrize("alteration", ["digest", "unsafe-root"])
def test_replacement_recovery_rejects_altered_or_unsafe_manifests(tmp_path: Path, alteration: str) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    destination = work_root / "jobs/plan.yaml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"expected")
    transaction = RuntimeTransaction(
        manifest_root,
        "replacement",
        (ReplacementTransactionParticipant(work_root, Path("jobs/plan.yaml"), b"expected", b"replacement"),),
    )

    def interrupt(current_stage: str) -> None:
        if current_stage == "before-publication":
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    manifest_path = manifest_root / ".runtime-transactions/replacement.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    participant = manifest["participants"][0]
    if alteration == "digest":
        participant["replacement_sha256"] = "0" * 64
    else:
        participant["root"] = str(tmp_path / "outside")
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    expected_error = TransactionManifestError if alteration == "digest" else TransactionPathError
    with pytest.raises(expected_error):
        RuntimeTransaction.recover_all(manifest_root, roots=(manifest_root, work_root))

    assert destination.read_bytes() == b"expected"
    assert not (tmp_path / "outside/jobs/plan.yaml").exists()


def test_concurrent_processes_publish_one_immutable_participant_set(tmp_path: Path) -> None:
    manifest_root = tmp_path / "change"
    work_root = tmp_path / "work"
    command = (
        "from pathlib import Path\n"
        "from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionParticipant\n"
        f"RuntimeTransaction(Path({str(manifest_root)!r}), 'shared', "
        f"(TransactionParticipant(Path({str(work_root)!r}), Path('jobs/plan.yaml'), b'plan'),)).commit()\n"
    )
    processes = [subprocess.Popen([sys.executable, "-c", command]) for _ in range(2)]
    for process in processes:
        process.wait()

    assert [process.returncode for process in processes] == [0, 0]
    assert (work_root / "jobs/plan.yaml").read_bytes() == b"plan"
    assert not list((manifest_root / ".runtime-transactions").glob("*.yaml"))


def test_mixed_store_participants_recover_and_replay_without_planning_mutation(tmp_path: Path) -> None:
    job_store, destination, stored, _replacement_bytes = _job_store_with_record(tmp_path)
    attempt_store = AttemptStore(destination.parents[1])
    replacement = stored.job.model_copy(update={"disposition": JobDisposition.SUPERSEDED})
    event = _attempt_event("attempt-recover")

    job_participant = job_store.replacement_participant(replacement, stored.token)
    attempt_participant = attempt_store.create_participant(event)

    assert destination.read_bytes() == job_participant.expected_content
    assert attempt_store.read(event.attempt_id, event.sequence).event is None
    with pytest.raises(JobConcurrencyError):
        job_store.replacement_participant(replacement, "stale")

    transaction = RuntimeTransaction(
        tmp_path / "change",
        "mixed-recover",
        (job_participant, attempt_participant),
    )

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            message = "interrupted"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="interrupted"):
        transaction.commit(failure=interrupt)

    RuntimeTransaction.recover_all(tmp_path / "change", roots=(tmp_path / "change", destination.parents[1]))

    assert job_store.read(1).job == replacement
    assert attempt_store.read(event.attempt_id, event.sequence).event == event
    assert not list((tmp_path / "change/.runtime-transactions").glob("*.yaml"))
    assert not list(destination.parents[1].rglob(".tmp-*"))

    replay = RuntimeTransaction(
        tmp_path / "change",
        "mixed-replay",
        (
            job_store.replacement_participant(replacement, job_store.read(1).token),
            attempt_store.create_participant(event),
        ),
    )
    replay.commit()

    assert job_store.read(1).job == replacement
    assert attempt_store.list() == (event,)
    assert not list((tmp_path / "change/.runtime-transactions").glob("*.yaml"))


def test_mixed_store_participants_serialize_competing_processes(tmp_path: Path) -> None:
    job_store, destination, _stored, _expected_bytes = _job_store_with_record(tmp_path)
    work_root = destination.parents[1]
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(2)
    outcomes = context.Queue()
    processes = [
        context.Process(
            target=_commit_mixed_process,
            args=(
                (
                    work_root,
                    tmp_path / "change",
                    ("cancelled", "superseded")[index],
                    f"attempt-race-{index}",
                ),
                barrier,
                outcomes,
            ),
        )
        for index in range(2)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=5)

    assert [process.exitcode for process in processes] == [0, 0]
    results = sorted(outcomes.get(timeout=2) for _ in processes)
    winner = next(result for result in results if result[2] == "success")
    loser = next(result for result in results if result[2] == TransactionConflictError.code)

    assert job_store.read(1).job.disposition.value == winner[0]
    assert AttemptStore(work_root).read(winner[1], 1).event == _attempt_event(winner[1])
    assert AttemptStore(work_root).read(loser[1], 1).event is None
    assert not list((tmp_path / "change/.runtime-transactions").glob("*.yaml"))
