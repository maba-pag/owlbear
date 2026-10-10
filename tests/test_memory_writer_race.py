from __future__ import annotations

import multiprocessing
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Barrier
from time import monotonic
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from owlbear_memory import ConcurrencyError, MemoryBusyError, MemoryEngine, MemoryState, storage, writer_lock
from owlbear_memory.errors import LifecycleRecoveryError
from owlbear_memory.models import MemoryEntry


def _edit_after_barrier(
    memory_dir: str,
    entry_id: str,
    content: str,
    barrier: Any,
    results: Any,
) -> None:
    engine = MemoryEngine(memory_dir)
    entry = engine.get_entry(entry_id)
    barrier.wait(timeout=15)
    try:
        engine.edit(entry_id, {"content": content}, expected_updated_at=entry.updated_at)
    except ConcurrencyError:
        results.put(("conflict", entry.updated_at, content))
    else:
        results.put(("success", entry.updated_at, content))


def _read_content(memory_dir: str, entry_id: str, results: Any) -> None:
    entry = MemoryEngine(memory_dir).get_entry(entry_id)
    results.put(entry.content)


def _hold_writer_lock(
    memory_dir: str,
    acquired: Any,
    release: Any,
    edit: tuple[str, str, str] | None = None,
) -> None:
    engine = MemoryEngine(memory_dir)
    with writer_lock(memory_dir, timeout=5):
        if edit is not None:
            entry_id, expected_updated_at, content = edit
            engine.edit(entry_id, {"content": content}, expected_updated_at=expected_updated_at)
        acquired.set()
        if not release.wait(timeout=15):
            raise TimeoutError


def _attempt_edit(
    memory_dir: str,
    edit: tuple[str, str, str],
    started: Any,
    finished: Any,
    results: Any,
) -> None:
    entry_id, expected_updated_at, content = edit
    engine = MemoryEngine(memory_dir, writer_lock_timeout=10)
    started.set()
    try:
        updated = engine.edit(entry_id, {"content": content}, expected_updated_at=expected_updated_at)
    except ConcurrencyError as error:
        results.put(("conflict", str(error), []))
    else:
        results.put(("success", updated.content, updated.scope_agents))
    finally:
        finished.set()


def _record_assessments(
    memory_dir: str,
    entry_id: str,
    calls: int,
    barrier: Any,
    results: Any,
) -> None:
    engine = MemoryEngine(memory_dir)
    barrier.wait(timeout=20)
    completed = 0
    while completed < calls:
        for _ in range(1000):
            entry = engine.get_entry(entry_id)
            try:
                engine.record_assessment(
                    entry_id, "outstanding", task_id=f"task-{uuid4()}", expected_revision=entry.revision
                )
            except ConcurrencyError:
                continue
            completed += 1
            break
        else:
            raise RuntimeError
    results.put(completed)


def _record_after_barrier(engine: MemoryEngine, entry_id: str, barrier: Barrier) -> int:
    barrier.wait(timeout=10)
    revision = engine.get_entry(entry_id).revision
    return engine.record_assessment(
        entry_id, "outstanding", task_id=f"task-{uuid4()}", expected_revision=revision
    ).entry.outstanding_count


def _pause_during_delete_agent_rollback(
    memory_dir: str,
    rollback_started: Any,
    finish_rollback: Any,
    results: Any,
) -> None:
    engine = MemoryEngine(memory_dir)
    original_write = storage.write_entry
    write_count = 0

    def fail_during_update(path: Path, entry: MemoryEntry, *, memory_dir: Path) -> None:
        nonlocal write_count
        write_count += 1
        if write_count == 2:
            raise OSError
        if write_count == 3:
            rollback_started.set()
            if not finish_rollback.wait(timeout=15):
                raise TimeoutError
        original_write(path, entry, memory_dir=memory_dir)

    with patch("owlbear_memory.engine.storage.write_entry", side_effect=fail_during_update):
        try:
            engine.delete_agent("retired-agent")
        except LifecycleRecoveryError as error:
            results.put(error.recovery_status)
        else:
            raise AssertionError


def _directory_snapshot(memory_dir: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple((path.name, path.read_bytes()) for path in sorted(memory_dir.iterdir()))


def _mutating_calls(engine: MemoryEngine, entry: MemoryEntry) -> list[Callable[[], object]]:
    return [
        lambda: engine.save(
            title="Another entry",
            content="Another content",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=[],
        ),
        lambda: engine.edit(entry.id, {"content": "Updated content"}, expected_updated_at=entry.updated_at),
        lambda: engine.approve(entry.id, expected_updated_at=entry.updated_at),
        lambda: engine.resolve(entry.id, expected_updated_at=entry.updated_at),
        lambda: engine.delete(entry.id, expected_updated_at=entry.updated_at),
        engine.purge,
        lambda: engine.record_assessment(entry.id, "outstanding", task_id="task-1", expected_revision=entry.revision),
        lambda: engine.record_factually_wrong(entry.id, "task-1", expected_revision=entry.revision),
        lambda: engine.try_stale_transition(entry),
        lambda: engine.rename_agent("test-agent", "renamed-agent"),
        lambda: engine.delete_agent("test-agent"),
    ]


def _join_processes(processes: list[multiprocessing.Process]) -> None:
    for process in processes:
        process.join(timeout=20)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
    assert all(process.exitcode == 0 for process in processes)


def test_conflicting_process_edits_accept_one_writer_and_publish_winner(tmp_path: Path) -> None:
    """Two processes using one token cannot overwrite each other's edit."""
    context = multiprocessing.get_context("spawn")
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    barrier = context.Barrier(2)
    results = context.Queue()
    contents = ["First writer", "Second writer"]
    writers = [
        context.Process(
            target=_edit_after_barrier,
            args=(str(tmp_path), entry.id, content, barrier, results),
        )
        for content in contents
    ]

    try:
        for writer in writers:
            writer.start()
        _join_processes(writers)
        outcomes = [results.get(timeout=5) for _ in writers]
        assert [outcome[0] for outcome in outcomes].count("success") == 1
        assert [outcome[0] for outcome in outcomes].count("conflict") == 1
        assert len({outcome[1] for outcome in outcomes}) == 1

        reader = context.Process(target=_read_content, args=(str(tmp_path), entry.id, results))
        reader.start()
        _join_processes([reader])
        winner = next(outcome[2] for outcome in outcomes if outcome[0] == "success")
        assert results.get(timeout=5) == winner
        assert {path.name for path in tmp_path.iterdir()} == {f"{entry.id}.md"}
    finally:
        for process in writers:
            if process.is_alive():
                process.terminate()
                process.join()
        results.close()
        results.join_thread()


@pytest.mark.parametrize("scenario", ["matching", "outdated"], ids=["matching-token", "stale-token"])
def test_process_mutation_waits_for_lock_and_rechecks_fresh_token(tmp_path: Path, scenario: str) -> None:
    """A waiting process edits only after release and checks the then-current entry."""
    make_token_stale = scenario == "outdated"
    context = multiprocessing.get_context("spawn")
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    acquired = context.Event()
    release = context.Event()
    holder = context.Process(
        target=_hold_writer_lock,
        args=(
            str(tmp_path),
            acquired,
            release,
            (entry.id, entry.updated_at, "Holder edit") if make_token_stale else None,
        ),
    )
    started = context.Event()
    finished = context.Event()
    results = context.Queue()
    contender = context.Process(
        target=_attempt_edit,
        args=(str(tmp_path), (entry.id, entry.updated_at, "Contender edit"), started, finished, results),
    )
    running: list[multiprocessing.Process] = []

    try:
        try:
            holder.start()
            running.append(holder)
            assert acquired.wait(timeout=5)
            held_snapshot = _directory_snapshot(tmp_path)

            contender.start()
            running.append(contender)
            assert started.wait(timeout=5)
            assert not finished.wait(timeout=0.15)
            assert _directory_snapshot(tmp_path) == held_snapshot
        finally:
            release.set()
            _join_processes(running)
        outcome = results.get(timeout=5)
    finally:
        results.close()
        results.join_thread()

    if make_token_stale:
        assert outcome[0] == "conflict"
        assert _directory_snapshot(tmp_path) == held_snapshot
        assert MemoryEngine(tmp_path).get_entry(entry.id).content == "Holder edit"
    else:
        assert outcome[0] == "success"
        assert MemoryEngine(tmp_path).get_entry(entry.id).content == "Contender edit"


def test_concurrent_process_assessments_preserve_every_successful_increment(tmp_path: Path) -> None:
    """Four independent engines can retry token conflicts without losing assessments."""
    context = multiprocessing.get_context("spawn")
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=["test-agent"],
    )
    entry = engine.edit(entry.id, {"scope_agents": ["test-agent"]}, expected_updated_at=entry.updated_at)
    entry = engine.approve(entry.id, expected_updated_at=entry.updated_at)
    process_count = 4
    calls_per_process = 25
    barrier = context.Barrier(process_count)
    results = context.Queue()
    workers = [
        context.Process(
            target=_record_assessments,
            args=(str(tmp_path), entry.id, calls_per_process, barrier, results),
        )
        for _ in range(process_count)
    ]

    try:
        for worker in workers:
            worker.start()
        _join_processes(workers)
        completed = [results.get(timeout=5) for _ in workers]
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join()
        results.close()
        results.join_thread()

    assert completed == [calls_per_process] * process_count
    final_entry = MemoryEngine(tmp_path).get_entry(entry.id)
    assert final_entry.outstanding_count == sum(completed)


def test_mutations_raise_busy_without_writes_when_another_process_holds_lock(tmp_path: Path) -> None:
    """Every MemoryEngine mutator times out cleanly behind a process writer."""
    context = multiprocessing.get_context("spawn")
    timeout = 0.05
    engine = MemoryEngine(tmp_path, writer_lock_timeout=timeout)
    entry = engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=["test-agent"],
    )
    acquired = context.Event()
    release = context.Event()
    holder = context.Process(target=_hold_writer_lock, args=(str(tmp_path), acquired, release))
    holder.start()

    try:
        assert acquired.wait(timeout=5)
        for operation in _mutating_calls(engine, entry):
            before = _directory_snapshot(tmp_path)
            started_at = monotonic()
            with pytest.raises(MemoryBusyError):
                operation()
            assert monotonic() - started_at < timeout + 0.25
            assert _directory_snapshot(tmp_path) == before
    finally:
        release.set()
        _join_processes([holder])


def test_mutations_raise_busy_without_writes_when_another_thread_holds_lock(tmp_path: Path) -> None:
    """Every MemoryEngine mutator times out behind a same-process writer thread."""
    timeout = 0.05
    engine = MemoryEngine(tmp_path, writer_lock_timeout=timeout)
    entry = engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=["test-agent"],
    )

    with ThreadPoolExecutor(max_workers=1) as executor, writer_lock(tmp_path, timeout=5):
        for operation in _mutating_calls(engine, entry):
            before = _directory_snapshot(tmp_path)
            started_at = monotonic()
            with pytest.raises(MemoryBusyError):
                executor.submit(operation).result(timeout=timeout + 0.25)
            assert monotonic() - started_at < timeout + 0.25
            assert _directory_snapshot(tmp_path) == before


def test_record_assessment_reenters_writer_lock_for_stale_transition(tmp_path: Path) -> None:
    """The stale auto-transition can nest its writer lock without deadlocking."""
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Stale candidate",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=["test-agent"],
    )
    entry = engine.edit(entry.id, {"scope_agents": ["test-agent"]}, expected_updated_at=entry.updated_at)
    entry = engine.approve(entry.id, expected_updated_at=entry.updated_at)
    entry = entry.model_copy(update={"didnt_use_count": 50})
    storage.write_entry(tmp_path / f"{entry.id}.md", entry, memory_dir=tmp_path)

    updated = (
        MemoryEngine(tmp_path)
        .record_assessment(entry.id, "didnt_use", task_id="task-stale", expected_revision=entry.revision)
        .entry
    )

    assert updated.didnt_use_count == 51
    assert updated.state == MemoryState.STALE


def test_multiple_engines_complete_sequential_and_threaded_mutations(tmp_path: Path) -> None:
    """Directory-scoped in-process locking coordinates distinct engine instances."""
    first_engine = MemoryEngine(tmp_path)
    second_engine = MemoryEngine(tmp_path)
    entry = first_engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=["test-agent"],
    )
    entry = first_engine.edit(entry.id, {"scope_agents": ["test-agent"]}, expected_updated_at=entry.updated_at)
    entry = first_engine.approve(entry.id, expected_updated_at=entry.updated_at)

    first_engine.record_assessment(entry.id, "outstanding", task_id="task-a", expected_revision=entry.revision)
    second_engine.record_assessment(entry.id, "outstanding", task_id="task-b", expected_revision=entry.revision)

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(_record_after_barrier, first_engine, entry.id, barrier)
        second = executor.submit(_record_after_barrier, second_engine, entry.id, barrier)
        counts = [first.result(timeout=5), second.result(timeout=5)]

    assert sorted(counts) == [3, 4]
    assert MemoryEngine(tmp_path).get_entry(entry.id).outstanding_count == 4


def test_mutation_advances_equal_clock_token_and_rejects_previous_token(tmp_path: Path) -> None:
    """A frozen clock cannot leave an edited entry with its prior OCC token."""
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    previous_time = datetime.fromisoformat(entry.updated_at)
    with patch("owlbear_memory.engine.datetime") as patched_datetime:
        patched_datetime.now.return_value = previous_time
        patched_datetime.fromisoformat.side_effect = datetime.fromisoformat
        updated = engine.edit(entry.id, {"content": "Updated content"}, expected_updated_at=entry.updated_at)

    assert updated.updated_at == (previous_time + timedelta(microseconds=1)).isoformat()
    before_stale_write = _directory_snapshot(tmp_path)
    with pytest.raises(ConcurrencyError):
        MemoryEngine(tmp_path).edit(entry.id, {"content": "Stale content"}, expected_updated_at=entry.updated_at)
    assert _directory_snapshot(tmp_path) == before_stale_write


def test_delete_agent_rollback_holds_lock_until_restored_entries_are_reloaded(tmp_path: Path) -> None:
    """A blocked writer observes restored entries after a failed lifecycle rollback."""
    context = multiprocessing.get_context("spawn")
    engine = MemoryEngine(tmp_path)
    entries = [
        engine.save(
            title=f"Entry {index}",
            content=f"Original content {index}",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
            scope_agents=["retired-agent", "surviving-agent"],
        )
        for index in range(2)
    ]
    target_entry = min(entries, key=lambda item: item.id)
    rollback_started = context.Event()
    finish_rollback = context.Event()
    recovery_results = context.Queue()
    lifecycle_worker = context.Process(
        target=_pause_during_delete_agent_rollback,
        args=(str(tmp_path), rollback_started, finish_rollback, recovery_results),
    )
    started = context.Event()
    finished = context.Event()
    contender_results = context.Queue()
    contender = context.Process(
        target=_attempt_edit,
        args=(
            str(tmp_path),
            (target_entry.id, target_entry.updated_at, "Contender content"),
            started,
            finished,
            contender_results,
        ),
    )
    running: list[multiprocessing.Process] = []
    initial_snapshot = _directory_snapshot(tmp_path)

    try:
        try:
            lifecycle_worker.start()
            running.append(lifecycle_worker)
            assert rollback_started.wait(timeout=5)
            during_rollback = _directory_snapshot(tmp_path)
            assert during_rollback != initial_snapshot

            contender.start()
            running.append(contender)
            assert started.wait(timeout=5)
            assert not finished.wait(timeout=0.15)
            assert _directory_snapshot(tmp_path) == during_rollback
        finally:
            finish_rollback.set()
            _join_processes(running)
        recovery_status = recovery_results.get(timeout=5)
        outcome = contender_results.get(timeout=5)
    finally:
        recovery_results.close()
        recovery_results.join_thread()
        contender_results.close()
        contender_results.join_thread()

    assert recovery_status == "complete"
    assert outcome == ("success", "Contender content", target_entry.scope_agents)
    fresh_engine = MemoryEngine(tmp_path)
    assert fresh_engine.get_entry(target_entry.id).content == "Contender content"
    for entry in entries:
        restored = fresh_engine.get_entry(entry.id)
        assert restored.scope_agents == ["retired-agent", "surviving-agent"]
    assert all(path.suffix == ".md" for path in tmp_path.iterdir())
