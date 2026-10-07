"""Cross-process contention tests for Cockpit memory routes."""

from __future__ import annotations

import multiprocessing
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_memory import MemoryEngine, writer_lock
from owlbear_memory.models import MemoryEntry

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _save_entry(engine: MemoryEngine) -> MemoryEntry:
    return engine.save(
        title="Shared entry",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )


def _edit_in_process(memory_dir: str, entry_id: str, expected_updated_at: str, content: str) -> None:
    MemoryEngine(memory_dir).edit(entry_id, {"content": content}, expected_updated_at=expected_updated_at)


def _hold_writer_lock(memory_dir: str, acquired: Any, release: Any) -> None:
    with writer_lock(memory_dir, timeout=10):
        acquired.set()
        if not release.wait(timeout=15):
            raise TimeoutError


def _finish_process(process: multiprocessing.Process) -> None:
    process.join(timeout=15)
    if process.is_alive():
        process.terminate()
        process.join()
    assert process.exitcode == 0


def _assert_only_entry_file(memory_dir: Path, entry_id: str) -> None:
    entries = list(memory_dir.iterdir())
    assert len(entries) == 1
    assert entries[0].name == f"{entry_id}.md"
    assert entries[0].is_file()


@contextmanager
def _client_for_engine(engine: MemoryEngine) -> Iterator[TestClient]:
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_memory_engine  # noqa: PLC0415
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides[get_memory_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_memory_engine, None)


def test_stale_cross_process_edit_returns_conflict_and_preserves_winner(tmp_path: Path) -> None:
    """A Cockpit edit with a token made stale by another process returns MEM_CONFLICT."""
    context = multiprocessing.get_context("spawn")
    engine = MemoryEngine(tmp_path)
    entry = _save_entry(engine)
    writer = context.Process(
        target=_edit_in_process,
        args=(str(tmp_path), entry.id, entry.updated_at, "Process winner"),
    )
    writer.start()
    _finish_process(writer)

    with _client_for_engine(engine) as client:
        response = client.post(
            f"/api/memories/{entry.id}/edit",
            json={"expected_updated_at": entry.updated_at, "content": "Stale Cockpit edit"},
        )

    assert response.status_code == 409
    assert response.json()["code"] == "MEM_CONFLICT"
    assert MemoryEngine(tmp_path).get_entry(entry.id).content == "Process winner"
    _assert_only_entry_file(tmp_path, entry.id)


def test_busy_cross_process_lock_returns_conflict(tmp_path: Path) -> None:
    """A Cockpit edit blocked by another process's writer lock returns MEM_CONFLICT."""
    context = multiprocessing.get_context("spawn")
    engine = MemoryEngine(tmp_path, writer_lock_timeout=0.05)
    entry = _save_entry(engine)
    acquired = context.Event()
    release = context.Event()
    holder = context.Process(target=_hold_writer_lock, args=(str(tmp_path), acquired, release))
    holder.start()

    try:
        assert acquired.wait(timeout=10)
        with _client_for_engine(engine) as client:
            response = client.post(
                f"/api/memories/{entry.id}/edit",
                json={"expected_updated_at": entry.updated_at, "content": "Blocked Cockpit edit"},
            )
        assert holder.is_alive()
    finally:
        release.set()
        _finish_process(holder)

    assert response.status_code == 409
    assert response.json()["code"] == "MEM_CONFLICT"
    assert MemoryEngine(tmp_path).get_entry(entry.id).content == "Original content"
    _assert_only_entry_file(tmp_path, entry.id)
