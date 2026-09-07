"""Shared scope validation across memory adapters."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryEntry
from pydantic import ValidationError as PydanticValidationError

from owlbear_cockpit.routes.memory import EditRequest
from owlbear_memory_mcp.tools import curate_memory


def _entry_data(scope_agents: list[str]) -> dict[str, object]:
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Scope test",
        "content": "Content",
        "categories": ["domain-knowledge"],
        "confidence": 0.9,
        "scope_agents": scope_agents,
        "source_agent": "builder",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.mark.parametrize("scope_agents", [[], ["builder"], ["*"]])
def test_memory_entry_accepts_empty_named_and_universal_scopes(scope_agents: list[str]) -> None:
    assert MemoryEntry.model_validate(_entry_data(scope_agents)).scope_agents == scope_agents


@pytest.mark.parametrize("scope_agents", [[""], ["   "], ["builder", "\t"]])
def test_memory_entry_rejects_blank_scope_members(scope_agents: list[str]) -> None:
    with pytest.raises(PydanticValidationError, match="scope_agents"):
        MemoryEntry.model_validate(_entry_data(scope_agents))


@pytest.mark.asyncio
async def test_mcp_curate_rejects_blank_scope_before_engine_edit(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Pending",
        content="Content",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="builder",
        scope_agents=[],
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = SimpleNamespace(engine=engine)

    with pytest.raises(ToolError, match="scope_agents"):
        await curate_memory(ctx, entry_id=entry.id, scope_agents=[" "])


def test_cockpit_edit_request_rejects_blank_scope_member() -> None:
    with pytest.raises(PydanticValidationError, match="scope_agents"):
        EditRequest(expected_updated_at="2026-01-01T00:00:00+00:00", scope_agents=[""])


def test_cockpit_edit_request_allows_clearing_scope() -> None:
    request = EditRequest(expected_updated_at="2026-01-01T00:00:00+00:00", scope_agents=[])

    assert request.scope_agents == []
