"""Failing tests for #1273: MCP tool layer — field validation and query limit.

AC coverage:
  AC-update: update_entry enforces curator-only access + field validation
    - update_entry must wrap invalid field values as ToolError, not silently bypass
      validators via model_copy(update={...}, validate=False) (default in Pydantic v2)
  AC-query: query_memory default excludes pending/deleted, sorts correctly
    - limit parameter restricts number of returned results (specified in scope interface)

All 6 tests FAIL (RED phase):
  2 x update_entry field validation: tool returns successfully instead of raising ToolError
    (Pydantic v2 model_copy(update=...) skips validators by default — bug in current impl)
  4 x query_memory limit: TypeError — unexpected keyword argument 'limit'
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry
from owlbear_mcp_memory.tools import query_memory, update_entry

# ---------------------------------------------------------------------------
# Helpers (copied conventions from test_mcp_memory_1266.py and 1272.py)
# ---------------------------------------------------------------------------


def _uuid(n: int) -> str:
    return f"550e8400-e29b-41d4-a716-4466554{n:05d}"


def _make_entry(**overrides: object) -> MemoryEntry:
    defaults: dict[str, object] = {
        "id": _uuid(1),
        "title": "Test entry",
        "categories": ["knowledge"],
        "confidence": 0.85,
        "state": "pending",
        "content": "Entry body text.",
        "scope_agents": None,
        "created_at": "2026-05-01T10:00:00Z",
        "updated_at": "2026-05-01T10:00:00Z",
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


def _make_ctx(engine: MemoryEngine, caller: str = "any-agent") -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    ctx.request_context.lifespan_context.caller = caller
    return ctx


def _seed(memory_dir: Path, entry: MemoryEntry) -> None:
    """Write a pre-existing entry file for test setup."""
    fm = {
        "id": entry.id,
        "title": entry.title,
        "categories": entry.categories,
        "confidence": entry.confidence,
        "state": entry.state,
        "scope_agents": entry.scope_agents,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
    slug = entry.title.lower().replace(" ", "-")[:40]
    path = memory_dir / f"{slug}-{entry.id[:6]}.md"
    path.write_text(
        f"---\n{yaml.safe_dump(fm, default_flow_style=False)}---\n\n{entry.content}\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# AC-update: update_entry must validate field values and raise ToolError
#
# Bug: current implementation uses model_copy(update={...}) without
# validate=True (Pydantic v2 default). Field validators (ge=0.7, min_length=1)
# are bypassed, allowing invalid data to be silently written to disk.
# The fix is to use model_copy(update=..., validate=True) and wrap the
# resulting ValidationError as ToolError.
# ---------------------------------------------------------------------------


class TestFromAC_UpdateEntryFieldValidation:
    """update_entry wraps invalid field values as ToolError (not silent model_copy bypass)."""

    @pytest.mark.asyncio
    async def test_update_entry_rejects_confidence_below_minimum(
        self, tmp_path: Path
    ) -> None:
        """update_entry raises ToolError when confidence is below 0.7 (ge=0.7 constraint).

        Current failure: model_copy(update={"confidence": 0.5}) bypasses the Field(ge=0.7)
        validator in Pydantic v2 (validate=False by default). The entry is silently
        written with confidence=0.5 and no ToolError is raised.
        """
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, confidence=0.5)

    @pytest.mark.asyncio
    async def test_update_entry_rejects_empty_categories_list(
        self, tmp_path: Path
    ) -> None:
        """update_entry raises ToolError when categories is set to an empty list.

        Current failure: model_copy(update={"categories": []}) bypasses the
        Field(min_length=1) constraint. The entry is silently written with no categories.
        The corrupted entry is then unreadable on next load (ValidationError at read time,
        silently skipped by MemoryEngine._load_file).
        """
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, categories=[])


# ---------------------------------------------------------------------------
# AC-query: query_memory limit parameter
#
# Scope specifies: query_memory(categories?, scope_agents?, min_confidence?, limit?)
# The limit parameter is not yet implemented. Any call with limit= raises TypeError.
# ---------------------------------------------------------------------------


class TestFromAC_QueryMemoryLimit:
    """query_memory limit parameter restricts the number of returned results."""

    @pytest.mark.asyncio
    async def test_limit_restricts_results_to_n(self, tmp_path: Path) -> None:
        """query_memory(ctx, limit=1) returns at most 1 entry even when 3 match."""
        for i in range(3):
            _seed(
                tmp_path,
                _make_entry(
                    id=_uuid(i + 10),
                    title=f"Entry {i}",
                    state="curated",
                    confidence=0.80 + i * 0.05,
                ),
            )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, limit=1)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_limit_zero_returns_empty_list(self, tmp_path: Path) -> None:
        """query_memory(ctx, limit=0) returns an empty list regardless of store contents."""
        _seed(tmp_path, _make_entry(id=_uuid(20), title="Entry A", state="approved"))
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, limit=0)

        assert results == []

    @pytest.mark.asyncio
    async def test_limit_larger_than_count_returns_all(self, tmp_path: Path) -> None:
        """query_memory(ctx, limit=100) returns all matching entries when fewer than limit exist."""
        for i in range(2):
            _seed(
                tmp_path,
                _make_entry(
                    id=_uuid(i + 30),
                    title=f"Entry {i}",
                    state="curated",
                ),
            )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, limit=100)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_limit_applied_after_state_and_category_filters(
        self, tmp_path: Path
    ) -> None:
        """limit is applied after all other filters (state, categories) are resolved."""
        for i in range(4):
            _seed(
                tmp_path,
                _make_entry(
                    id=_uuid(i + 40),
                    title=f"Knowledge entry {i}",
                    state="curated",
                    categories=["knowledge"],
                    confidence=0.70 + i * 0.05,
                ),
            )
        # Add one that won't match category filter
        _seed(
            tmp_path,
            _make_entry(
                id=_uuid(49),
                title="Pitfall entry",
                state="curated",
                categories=["pitfall"],
            ),
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, categories=["knowledge"], limit=2)

        assert len(results) == 2
        # All returned entries must satisfy the category filter
        for r in results:
            assert "knowledge" in r["categories"]
