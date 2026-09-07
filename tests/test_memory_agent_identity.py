"""Behavioral tests for memory-derived agent identity and lifecycle validation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import LifecycleRecoveryError, LifecycleRollbackFailure, MemoryCategory, MemoryEngine

from owlbear_memory_mcp.tools import (
    _recognized_agent_names,
    curate_memory,
    delete_agent_memories,
    rename_agent_memories,
    save_memory,
)


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = SimpleNamespace(engine=engine)
    return ctx


def _save(engine: MemoryEngine, *, source: str, scope: list[str]) -> str:
    entry = engine.save(
        title=f"Lesson from {source}",
        content="Specific reusable lesson.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent=source,
        scope_agents=scope,
    )
    return entry.id


def test_recognized_names_derive_from_live_provenance_and_scope(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    _save(engine, source="GitHub Copilot", scope=["builder", "verifier", "*"])
    deleted_id = _save(engine, source="retired", scope=["deleted-only"])
    deleted = engine.get_entry(deleted_id)
    engine.delete(deleted_id, expected_updated_at=deleted.updated_at)

    assert _recognized_agent_names(engine) == ["GitHub Copilot", "builder", "verifier"]


@pytest.mark.asyncio
async def test_save_accepts_nonblank_provenance_and_defaults_to_unscoped(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    ctx = _make_ctx(engine)

    result = await save_memory(
        ctx,
        title="External provenance",
        content="Curator decides the audience.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="GitHub Copilot",
    )

    assert result["scope_agents"] == []
    assert result["source_agent"] == "GitHub Copilot"
    assert len(engine.get_entries()) == 1

    with pytest.raises(TypeError, match="scope_agents"):
        await save_memory(
            ctx,
            title="Producer-assigned scope",
            content="Writers cannot select an audience.",
            categories=[MemoryCategory.PROCESS],
            confidence=0.8,
            source_agent="builder",
            scope_agents=["builder"],  # type: ignore[call-arg]
        )


@pytest.mark.asyncio
async def test_rename_agent_rewrites_sources_and_scopes(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    _save(engine, source="verifier", scope=["verifier", "builder"])
    _save(engine, source="builder", scope=["verifier"])

    result = await rename_agent_memories(
        _make_ctx(engine),
        old_name="verifier",
        new_name="build-reviewer",
    )

    assert result == {"entries_updated": 2, "sources_updated": 1, "scopes_updated": 2}
    entries = engine.get_entries()
    assert {entry.source_agent for entry in entries} == {"build-reviewer", "builder"}
    assert all("verifier" not in entry.scope_agents for entry in entries)


@pytest.mark.asyncio
async def test_delete_agent_preserves_sourced_memories_with_surviving_audiences(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    sourced_id = _save(engine, source="verifier", scope=["builder"])
    universal_id = _save(engine, source="verifier", scope=["*"])
    orphaned_id = _save(engine, source="builder", scope=["verifier"])
    retained_id = _save(engine, source="builder", scope=["builder", "verifier"])

    result = await delete_agent_memories(
        _make_ctx(engine),
        agent="verifier",
    )

    assert result == {"entries_deleted": 1, "scopes_updated": 1}
    entries = {entry.id: entry for entry in engine.get_entries()}
    assert entries[sourced_id].source_agent == "verifier"
    assert entries[universal_id].scope_agents == ["*"]
    assert orphaned_id not in entries
    assert entries[retained_id].scope_agents == ["builder"]


@pytest.mark.asyncio
async def test_scope_syntax_accepts_mixed_values_and_rejects_blank_members(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    entry_id = _save(engine, source="writer", scope=[])

    updated = await curate_memory(
        _make_ctx(engine),
        entry_id=entry_id,
        scope_agents=["builder", "*"],
    )

    assert updated["scope_agents"] == ["builder", "*"]
    with pytest.raises(ToolError, match="non-empty strings"):
        await curate_memory(_make_ctx(engine), entry_id=entry_id, scope_agents=[""])


@pytest.mark.asyncio
async def test_rename_and_delete_reject_wildcard_names(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    ctx = _make_ctx(engine)

    with pytest.raises(ToolError, match="non-wildcard"):
        await rename_agent_memories(ctx, old_name="*", new_name="builder")
    with pytest.raises(ToolError, match="non-wildcard"):
        await delete_agent_memories(ctx, agent="*")


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["rename_agent", "delete_agent"])
async def test_lifecycle_recovery_diagnostics_are_exposed_as_tool_errors(
    tmp_path: Path,
    operation: str,
) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    rollback_error = OSError("rollback write failed")
    diagnostic = LifecycleRecoveryError(
        OSError("initial write failed"),
        (LifecycleRollbackFailure("entry-id", tmp_path / "entry.md", rollback_error),),
        None,
        "partial",
    )
    ctx = _make_ctx(engine)

    with patch.object(engine, operation, side_effect=diagnostic), pytest.raises(ToolError) as exc_info:
        if operation == "rename_agent":
            await rename_agent_memories(ctx, old_name="verifier", new_name="builder")
        else:
            await delete_agent_memories(ctx, agent="verifier")

    assert str(exc_info.value) == str(diagnostic)
