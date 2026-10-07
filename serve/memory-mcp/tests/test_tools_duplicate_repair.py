from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import DuplicateEntryError, MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_memory_mcp import tools
from owlbear_memory_mcp.server import AppContext

_DUPLICATE_ID = "550e8400-e29b-41d4-a716-446655440001"


def _entry(*, title: str, content: str, updated_at: str, **overrides: object) -> MemoryEntry:
    state = overrides.get("state", MemoryState.PENDING)
    data: dict[str, object] = {
        "id": _DUPLICATE_ID,
        "title": title,
        "content": content,
        "categories": ["domain-knowledge"],
        "confidence": 0.9,
        "state": state,
        "outstanding_count": 0,
        "unremarkable_count": 0,
        "didnt_use_count": 0,
        "score": 0.9,
        "scope_agents": ["test-agent"],
        "source_agent": "test-agent",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": updated_at,
        "approved_at": "2025-01-01T00:00:00+00:00" if state == MemoryState.APPROVED else None,
    }
    data.update(overrides)
    return MemoryEntry.model_validate(data)


def _write_duplicate_pair(
    memory_dir: Path,
    *,
    older_state: MemoryState,
    newer_state: MemoryState,
    scope_agents: list[str] | None = None,
) -> None:
    scopes = scope_agents or ["test-agent"]
    older = _entry(
        title="Older duplicate",
        content="Older duplicate content.",
        updated_at="2026-01-01T00:00:00+00:00",
        state=older_state,
        scope_agents=scopes,
    )
    newer = _entry(
        title="Newer duplicate",
        content="Newer duplicate content.",
        updated_at="2026-01-02T00:00:00+00:00",
        state=newer_state,
        scope_agents=scopes,
    )
    storage.write_entry(memory_dir / f"{_DUPLICATE_ID}.md", older, memory_dir=memory_dir)
    storage.write_entry(memory_dir / "duplicate-copy.md", newer, memory_dir=memory_dir)


def _directory_snapshot(memory_dir: Path) -> tuple[tuple[str, bytes, int], ...]:
    return tuple(
        (path.name, path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(memory_dir.iterdir())
        if path.is_file()
    )


def _directory_mode(memory_dir: Path) -> int:
    return memory_dir.stat().st_mode & 0o777


def _set_directory_mode(memory_dir: Path, mode: int) -> None:
    memory_dir.chmod(mode)


def _memory_entries(memory_dir: Path) -> list[MemoryEntry]:
    return [entry for path in memory_dir.glob("*.md") if (entry := storage.read_entry(path)) is not None]


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
    pending = _create_entry(engine, title=title)
    curated = engine.edit(
        pending.id,
        {"scope_agents": ["test-agent"]},
        expected_updated_at=pending.updated_at,
    )
    return engine.approve(curated.id, expected_updated_at=curated.updated_at)


@pytest.mark.parametrize(
    ("tool_name", "engine_method"),
    [
        ("save_memory", "save"),
        ("curate_memory", "edit"),
        ("delete_memory", "delete"),
        ("approve_memory", "approve"),
        ("rename_agent_memories", "rename_agent"),
        ("delete_agent_memories", "delete_agent"),
    ],
)
@pytest.mark.asyncio
async def test_mutation_tools_translate_duplicate_errors_to_tool_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tool_name: str,
    engine_method: str,
) -> None:
    engine = MemoryEngine(tmp_path)
    pending = _create_entry(engine, title="Pending entry")
    curated = engine.edit(
        pending.id,
        {"scope_agents": ["test-agent"]},
        expected_updated_at=pending.updated_at,
    )
    _create_entry(engine, title="Agent reference", source_agent="old-agent", scope_agents=["old-agent"])
    ctx = _tool_context(engine, tmp_path)
    error_paths = tuple(sorted((f"{_DUPLICATE_ID}.md", "duplicate-copy.md")))
    duplicate_error = DuplicateEntryError(_DUPLICATE_ID, error_paths)

    def raise_duplicate(*_args: Any, **_kwargs: Any) -> None:
        raise duplicate_error

    monkeypatch.setattr(MemoryEngine, engine_method, raise_duplicate)
    tool_calls = {
        "save_memory": lambda: tools.save_memory(
            ctx,
            title="Blocked save",
            content="Not written.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
        ),
        "curate_memory": lambda: tools.curate_memory(
            ctx,
            entry_id=pending.id,
            content="Updated content.",
            scope_agents=["test-agent"],
        ),
        "delete_memory": lambda: tools.delete_memory(ctx, entry_id=pending.id),
        "approve_memory": lambda: tools.approve_memory(ctx, entry_id=curated.id),
        "rename_agent_memories": lambda: tools.rename_agent_memories(
            ctx,
            old_name="old-agent",
            new_name="new-agent",
        ),
        "delete_agent_memories": lambda: tools.delete_agent_memories(ctx, agent="old-agent"),
    }

    with pytest.raises(ToolError) as raised:
        await tool_calls[tool_name]()

    assert str(raised.value) == str(duplicate_error)


@pytest.mark.asyncio
async def test_curate_memory_surfaces_duplicate_repair_failure_without_changes(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("real permission behavior cannot be verified as root")

    setup_engine = MemoryEngine(tmp_path)
    _create_entry(setup_engine, title="Lock file seed")
    _write_duplicate_pair(
        tmp_path,
        older_state=MemoryState.APPROVED,
        newer_state=MemoryState.APPROVED,
    )
    engine = MemoryEngine(tmp_path)
    ctx = _tool_context(engine, tmp_path)
    before = _directory_snapshot(tmp_path)
    original_mode = _directory_mode(tmp_path)

    try:
        _set_directory_mode(tmp_path, original_mode & ~0o222)
        with pytest.raises(ToolError) as raised:
            await tools.curate_memory(ctx, entry_id=_DUPLICATE_ID, content="Must not apply.")
    finally:
        _set_directory_mode(tmp_path, original_mode)

    assert _DUPLICATE_ID in str(raised.value)
    assert f"{_DUPLICATE_ID}.md" in str(raised.value)
    assert "duplicate-copy.md" in str(raised.value)
    assert _directory_snapshot(tmp_path) == before


@pytest.mark.asyncio
async def test_assess_memories_reports_duplicate_failure_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if os.geteuid() == 0:
        pytest.skip("real permission behavior cannot be verified as root")

    setup_engine = MemoryEngine(tmp_path)
    later_entry = _create_approved_entry(setup_engine, title="Later assessment")
    _write_duplicate_pair(
        tmp_path,
        older_state=MemoryState.APPROVED,
        newer_state=MemoryState.APPROVED,
    )
    engine = MemoryEngine(tmp_path)
    ctx = _tool_context(engine, tmp_path)
    before = _directory_snapshot(tmp_path)
    original_mode = _directory_mode(tmp_path)
    original_record_assessment = engine.record_assessment
    failure_snapshot: tuple[tuple[str, bytes, int], ...] | None = None

    def restore_permissions_after_failure(
        entry_id: str,
        bucket: str,
        *,
        expected_updated_at: str | None = None,
    ) -> MemoryEntry:
        nonlocal failure_snapshot
        try:
            return original_record_assessment(
                entry_id,
                bucket,
                expected_updated_at=expected_updated_at,
            )
        except DuplicateEntryError:
            failure_snapshot = _directory_snapshot(tmp_path)
            tmp_path.chmod(original_mode)
            raise

    monkeypatch.setattr(engine, "record_assessment", restore_permissions_after_failure)

    try:
        _set_directory_mode(tmp_path, original_mode & ~0o222)
        result = await tools.assess_memories(
            ctx,
            assessments=[
                {"entry_id": _DUPLICATE_ID, "bucket": "outstanding"},
                {"entry_id": later_entry.id, "bucket": "outstanding"},
            ],
            task_id="task-1",
        )
    finally:
        _set_directory_mode(tmp_path, original_mode)

    assert failure_snapshot == before
    assert result["results"][0]["entry_id"] == _DUPLICATE_ID
    assert result["results"][0]["success"] is False
    assert "duplicate-copy.md" in str(result["results"][0]["error"])
    assert result["results"][1] == {"entry_id": later_entry.id, "success": True}
    assert engine.get_entry(later_entry.id).outstanding_count == 1


@pytest.mark.asyncio
async def test_purge_keeps_repaired_copy_pending_and_out_of_recall(tmp_path: Path) -> None:
    scope_agents = ["agent-one", "agent-two"]
    approved = _entry(
        title="Approved duplicate",
        content="Preserved approved content.",
        updated_at="2025-01-01T00:00:00+00:00",
        state=MemoryState.APPROVED,
        scope_agents=scope_agents,
    )
    tombstone = _entry(
        title="Deleted duplicate",
        content="Deleted content.",
        updated_at="2025-01-02T00:00:00+00:00",
        state=MemoryState.DELETED,
        scope_agents=scope_agents,
    )
    storage.write_entry(tmp_path / f"{_DUPLICATE_ID}.md", approved, memory_dir=tmp_path)
    storage.write_entry(tmp_path / "deleted-copy.md", tombstone, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    ctx = _tool_context(engine, tmp_path)

    result = engine.purge(min_age_days=0)
    recalls = [await tools.recall_memory(ctx, agent=agent) for agent in scope_agents]
    pending_entries = await tools.list_memories(ctx, states=[MemoryState.PENDING])

    assert result.purged == 1
    assert all(approved.content not in recall for recall in recalls)
    assert len(pending_entries) == 1
    pending = pending_entries[0]
    assert pending["state"] == str(MemoryState.PENDING)
    assert pending["id"] != _DUPLICATE_ID
    assert _DUPLICATE_ID in str(pending["title"])
    restored = await tools.read_memory(ctx, entry_id=str(pending["id"]))
    assert restored["content"] == approved.content

    remaining_entries = _memory_entries(tmp_path)
    assert not any(entry.id == _DUPLICATE_ID and entry.state == MemoryState.APPROVED for entry in remaining_entries)
