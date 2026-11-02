"""Behavioral tests for memory-derived agent identity."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_memory_mcp.tools import (
    _recognized_agent_names,
    curate_memory,
    read_memory,
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

    assert _recognized_agent_names(engine.get_entries()) == ["GitHub Copilot", "builder", "verifier"]


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
        where="project",
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
            where="project",
            scope_agents=["builder"],  # type: ignore[call-arg]
        )


@pytest.mark.asyncio
async def test_scope_syntax_accepts_mixed_values_and_rejects_blank_members(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / ".owlbear/memory")
    entry_id = _save(engine, source="writer", scope=[])
    ctx = _make_ctx(engine)
    ctx.request_context.lifespan_context.agents = frozenset({"builder"})
    revision = (await read_memory(ctx, entry_id=entry_id))["revision"]

    updated = await curate_memory(
        ctx,
        entry_id=entry_id,
        revision=revision,
        scope_agents=["builder", "*"],
    )

    assert updated["scope_agents"] == ["builder", "*"]
    revision = (await read_memory(ctx, entry_id=entry_id))["revision"]
    with pytest.raises(ToolError, match="non-empty strings"):
        await curate_memory(ctx, entry_id=entry_id, revision=revision, scope_agents=[""])
