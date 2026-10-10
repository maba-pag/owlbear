from __future__ import annotations

import multiprocessing
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import ConcurrencyError, MemoryEngine, writer_lock
from owlbear_memory.models import MemoryEntry

from owlbear_memory_mcp import tools
from owlbear_memory_mcp.server import AppContext


def _hold_writer_lock(
    memory_dir: str,
    acquired: Any,
    release: Any,
    release_after: float | None,
) -> None:
    with writer_lock(memory_dir, timeout=5):
        acquired.set()
        if release_after is None:
            if not release.wait(timeout=10):
                raise TimeoutError
        else:
            release.wait(timeout=release_after)


def _edit_after_tool_read(
    memory_dir: str,
    entry_id: str,
    expected_updated_at: str,
    entry_read: Any,
    edit_complete: Any,
) -> None:
    if not entry_read.wait(timeout=10):
        raise TimeoutError
    MemoryEngine(memory_dir).edit(
        entry_id,
        {"content": "Concurrent process wins."},
        expected_updated_at=expected_updated_at,
    )
    edit_complete.set()


def _start_lock_holder(
    process_context: Any,
    memory_dir: Path,
    *,
    release_after: float | None = None,
) -> tuple[multiprocessing.Process, Any]:
    acquired = process_context.Event()
    release = process_context.Event()
    holder = process_context.Process(
        target=_hold_writer_lock,
        args=(str(memory_dir), acquired, release, release_after),
    )
    holder.start()
    assert acquired.wait(timeout=10)
    return holder, release


def _finish_process(process: multiprocessing.Process) -> None:
    process.join(timeout=10)
    if process.is_alive():
        process.terminate()
        process.join()
    assert process.exitcode == 0


def _finish_lock_holder(process: multiprocessing.Process, release: Any) -> None:
    release.set()
    _finish_process(process)


def _tool_context(engine: MemoryEngine, memory_dir: Path) -> SimpleNamespace:
    return SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=AppContext(engine=engine, memory_dir=memory_dir),
        ),
    )


def _create_entry(
    engine: MemoryEngine,
    *,
    title: str,
    source_agent: str = "test-agent",
    scope_agents: list[str] | None = None,
) -> MemoryEntry:
    return engine.save(
        title=title,
        content="Original content.",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent=source_agent,
        scope_agents=scope_agents or [],
    )


def _create_approved_entry(engine: MemoryEngine, *, title: str) -> MemoryEntry:
    entry = _create_entry(engine, title=title)
    curated = engine.edit(
        entry.id,
        {"scope_agents": ["test-agent"]},
        expected_updated_at=entry.updated_at,
    )
    return engine.approve(curated.id, expected_updated_at=curated.updated_at)


def _directory_snapshot(memory_dir: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple((path.name, path.read_bytes()) for path in sorted(memory_dir.iterdir()))


def _busy_message(memory_dir: Path) -> str:
    return f"Timed out acquiring the memory writer lock for {memory_dir.resolve()}"


@pytest.mark.asyncio
async def test_mutation_tools_translate_busy_errors_from_another_process(tmp_path: Path) -> None:
    process_context = multiprocessing.get_context("spawn")
    timeout = 0.05
    engine = MemoryEngine(tmp_path, writer_lock_timeout=timeout)
    ctx = _tool_context(engine, tmp_path)
    curate_entry = _create_entry(engine, title="Curate entry")
    delete_entry = _create_entry(engine, title="Delete entry")
    approve_entry = _create_approved_entry(engine, title="Approve entry")
    _create_entry(
        engine,
        title="Agent reference",
        source_agent="old-agent",
        scope_agents=["old-agent"],
    )
    before = _directory_snapshot(tmp_path)
    holder, release = _start_lock_holder(process_context, tmp_path)
    expected_message = _busy_message(tmp_path)

    try:
        operations = (
            lambda: tools.save_memory(
                ctx,
                title="Blocked save",
                content="Not written.",
                categories=["domain-knowledge"],
                confidence=0.9,
                source_agent="test-agent",
            ),
            lambda: tools.curate_memory(
                ctx, entry_id=curate_entry.id, revision=curate_entry.revision, scope_agents=["test-agent"]
            ),
            lambda: tools.delete_memory(ctx, entry_id=delete_entry.id, revision=delete_entry.revision),
            lambda: tools.approve_memory(ctx, entry_id=approve_entry.id, revision=approve_entry.revision),
            lambda: tools.rename_agent_memories(ctx, old_name="old-agent", new_name="new-agent"),
            lambda: tools.delete_agent_memories(ctx, agent="old-agent"),
        )
        for operation in operations:
            with pytest.raises(ToolError) as raised:
                await operation()
            assert str(raised.value) == expected_message
            assert _directory_snapshot(tmp_path) == before
    finally:
        _finish_lock_holder(holder, release)


@pytest.mark.asyncio
async def test_assess_memories_reports_busy_entry_and_continues(tmp_path: Path) -> None:
    process_context = multiprocessing.get_context("spawn")
    timeout = 0.25
    engine = MemoryEngine(tmp_path, writer_lock_timeout=timeout)
    ctx = _tool_context(engine, tmp_path)
    blocked_entry = _create_approved_entry(engine, title="Blocked assessment")
    later_entry = _create_approved_entry(engine, title="Later assessment")
    holder, release = _start_lock_holder(
        process_context,
        tmp_path,
        release_after=timeout * 1.8,
    )
    expected_message = _busy_message(tmp_path)

    try:
        result = await tools.assess_memories(
            ctx,
            assessments=[
                {"entry_id": blocked_entry.id, "revision": blocked_entry.revision, "bucket": "outstanding"},
                {"entry_id": later_entry.id, "revision": later_entry.revision, "bucket": "outstanding"},
            ],
            task_id="task-1",
        )
    finally:
        _finish_lock_holder(holder, release)

    assert result == {
        "results": [
            {"entry_id": blocked_entry.id, "success": False, "error": expected_message},
            {
                "entry_id": later_entry.id,
                "success": True,
                "already_applied": False,
                "recorded_bucket": "outstanding",
            },
        ],
    }
    assert engine.get_entry(blocked_entry.id).outstanding_count == 0
    assert engine.get_entry(later_entry.id).outstanding_count == 1


@pytest.mark.asyncio
async def test_curate_memory_routes_cross_process_stale_edit_to_tool_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    process_context = multiprocessing.get_context("spawn")
    engine = MemoryEngine(tmp_path, writer_lock_timeout=0.2)
    ctx = _tool_context(engine, tmp_path)
    entry = _create_entry(engine, title="Concurrent curation")
    entry_read = process_context.Event()
    edit_complete = process_context.Event()
    editor = process_context.Process(
        target=_edit_after_tool_read,
        args=(str(tmp_path), entry.id, entry.updated_at, entry_read, edit_complete),
    )
    original_load = vars(tools)["_load_entry_or_raise"]

    def load_then_wait_for_editor(current_engine: MemoryEngine, entry_id: str) -> MemoryEntry:
        current = original_load(current_engine, entry_id)
        entry_read.set()
        if not edit_complete.wait(timeout=10):
            raise TimeoutError
        return current

    monkeypatch.setattr(tools, "_load_entry_or_raise", load_then_wait_for_editor)
    editor.start()

    try:
        with pytest.raises(ToolError) as raised:
            await tools.curate_memory(
                ctx,
                entry_id=entry.id,
                revision=entry.revision,
                content="Stale curation.",
                scope_agents=["test-agent"],
            )
    finally:
        _finish_process(editor)

    with pytest.raises(ConcurrencyError) as expected:
        engine.edit(
            entry.id,
            {"content": "Another stale edit."},
            expected_revision=entry.revision,
        )
    assert str(raised.value) == str(tools._stale_revision_error(expected.value))  # noqa: SLF001
    assert MemoryEngine(tmp_path).get_entry(entry.id).content == "Concurrent process wins."
