"""Failing tests for #1272: MCP tools — query filter API and ToolError wrapping.

AC coverage (failing RED tests only):
  AC-store: store_learning raises ToolError (not raw ValidationError) for:
    - confidence < 0.7
    - blank title
    - empty categories list
  AC-query: query_memory filter parameters not yet implemented:
    - categories=[...] filter
    - scope_agents=[...] filter
    - min_confidence=... filter
    - combined multi-filter

Passing tests for already-implemented behavior (covered by test_mcp_memory_1266.py):
  - store_learning creates pending entry (AC: any agent)
  - query_memory default sort order / state exclusions
  - update_entry / delete_entry / approve_entry basic ops
  - state transition enforcement
  - allowed_agents config mechanism
  All of those behaviors are green in 1266 and would pass if duplicated here — removed per
  RED-phase rule (§ w-tdd-red Step 5: "remove or make more specific").

All 11 tests in this file FAIL (RED phase):
  - 3 x ToolError wrapping: tool propagates ValidationError instead of ToolError
  - 8 x query_memory filter params: TypeError — unexpected keyword argument
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry
from owlbear_mcp_memory.tools import (
    query_memory,
    store_learning,
)

# ---------------------------------------------------------------------------
# Helpers
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
    import yaml

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
# AC-store: store_learning raises ToolError for validation failures
#
# Current behaviour: MemoryEntry ValidationError propagates from the tool
# (not wrapped).  Tool layer is expected to catch model errors and raise
# ToolError so callers receive a uniform MCP error surface.
# ---------------------------------------------------------------------------


class TestFromAC_StoreLearningValidation:
    """store_learning wraps model validation failures as ToolError."""

    @pytest.mark.asyncio
    async def test_low_confidence_raises_tool_error(self, tmp_path: Path) -> None:
        """store_learning raises ToolError when confidence is below 0.7."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")
        with pytest.raises(ToolError):
            await store_learning(
                ctx,
                title="Low confidence entry",
                content="Body.",
                categories=["pitfall"],
                confidence=0.65,
            )

    @pytest.mark.asyncio
    async def test_blank_title_raises_tool_error(self, tmp_path: Path) -> None:
        """store_learning raises ToolError when title is blank."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")
        with pytest.raises(ToolError):
            await store_learning(
                ctx,
                title="",
                content="Body.",
                categories=["knowledge"],
                confidence=0.8,
            )

    @pytest.mark.asyncio
    async def test_empty_categories_raises_tool_error(self, tmp_path: Path) -> None:
        """store_learning raises ToolError when categories list is empty."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")
        with pytest.raises(ToolError):
            await store_learning(
                ctx,
                title="Valid title",
                content="Body.",
                categories=[],
                confidence=0.8,
            )


# ---------------------------------------------------------------------------
# AC-query: query_memory filter parameters (not yet implemented)
#
# Current signature: query_memory(ctx, *, states=None)
# Required signature: query_memory(ctx, *, states=None, categories=None,
#                                  scope_agents=None, min_confidence=None)
# Calling with new kwargs raises TypeError until the parameter is added.
# ---------------------------------------------------------------------------


class TestFromAC_QueryMemoryFilters:
    """query_memory category, scope_agents, and min_confidence filter parameters."""

    @pytest.mark.asyncio
    async def test_category_filter_returns_only_matching_entries(
        self, tmp_path: Path
    ) -> None:
        """query_memory(categories=[...]) returns only entries with matching category."""
        pitfall = _make_entry(
            id=_uuid(10), title="Pitfall entry", state="curated", categories=["pitfall"]
        )
        knowledge = _make_entry(
            id=_uuid(11),
            title="Knowledge entry",
            state="curated",
            categories=["knowledge"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, pitfall)
        _seed(tmp_path, knowledge)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, categories=["pitfall"])

        ids = [r["id"] for r in results]
        assert _uuid(10) in ids
        assert _uuid(11) not in ids

    @pytest.mark.asyncio
    async def test_category_filter_empty_result_when_no_match(
        self, tmp_path: Path
    ) -> None:
        """category filter returns empty list when no entry matches."""
        entry = _make_entry(
            id=_uuid(12), title="Tool entry", state="approved", categories=["tool"]
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, entry)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, categories=["goal"])

        assert results == []

    @pytest.mark.asyncio
    async def test_scope_agents_filter_includes_matching_entries(
        self, tmp_path: Path
    ) -> None:
        """query_memory(scope_agents=[...]) returns entries scoped to the given agents."""
        scoped = _make_entry(
            id=_uuid(20),
            title="Builder-scoped",
            state="curated",
            categories=["pitfall"],
            scope_agents=["builder"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, scoped)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, scope_agents=["builder"])

        ids = [r["id"] for r in results]
        assert _uuid(20) in ids

    @pytest.mark.asyncio
    async def test_scope_agents_filter_excludes_non_matching_entries(
        self, tmp_path: Path
    ) -> None:
        """scope_agents filter excludes entries scoped to a different agent."""
        reviewer_only = _make_entry(
            id=_uuid(21),
            title="Reviewer-scoped",
            state="curated",
            categories=["process"],
            scope_agents=["reviewer"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, reviewer_only)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, scope_agents=["builder"])

        ids = [r["id"] for r in results]
        assert _uuid(21) not in ids

    @pytest.mark.asyncio
    async def test_min_confidence_filter_excludes_below_threshold(
        self, tmp_path: Path
    ) -> None:
        """query_memory(min_confidence=0.9) excludes entries below the threshold."""
        low = _make_entry(
            id=_uuid(30),
            title="Low",
            state="curated",
            categories=["knowledge"],
            confidence=0.75,
        )
        high = _make_entry(
            id=_uuid(31),
            title="High",
            state="curated",
            categories=["knowledge"],
            confidence=0.95,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, low)
        _seed(tmp_path, high)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, min_confidence=0.9)

        ids = [r["id"] for r in results]
        assert _uuid(31) in ids
        assert _uuid(30) not in ids

    @pytest.mark.asyncio
    async def test_min_confidence_boundary_is_inclusive(self, tmp_path: Path) -> None:
        """min_confidence boundary is inclusive — entry exactly at threshold is returned."""
        exact = _make_entry(
            id=_uuid(32),
            title="Exact",
            state="approved",
            categories=["process"],
            confidence=0.8,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, exact)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, min_confidence=0.8)

        ids = [r["id"] for r in results]
        assert _uuid(32) in ids

    @pytest.mark.asyncio
    async def test_combined_category_and_min_confidence_filter(
        self, tmp_path: Path
    ) -> None:
        """categories and min_confidence filters combine as AND logic."""
        match = _make_entry(
            id=_uuid(40),
            title="Match",
            state="curated",
            categories=["pitfall"],
            confidence=0.9,
        )
        wrong_cat = _make_entry(
            id=_uuid(41),
            title="Wrong cat",
            state="curated",
            categories=["knowledge"],
            confidence=0.9,
        )
        low_conf = _make_entry(
            id=_uuid(42),
            title="Low conf pitfall",
            state="curated",
            categories=["pitfall"],
            confidence=0.75,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, match)
        _seed(tmp_path, wrong_cat)
        _seed(tmp_path, low_conf)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx, categories=["pitfall"], min_confidence=0.85)

        ids = [r["id"] for r in results]
        assert _uuid(40) in ids
        assert _uuid(41) not in ids
        assert _uuid(42) not in ids

    @pytest.mark.asyncio
    async def test_all_three_filters_combined(self, tmp_path: Path) -> None:
        """categories, scope_agents, and min_confidence all applied together."""
        target = _make_entry(
            id=_uuid(50),
            title="All-filter match",
            state="approved",
            categories=["tool"],
            confidence=0.92,
            scope_agents=["builder"],
        )
        wrong_scope = _make_entry(
            id=_uuid(51),
            title="Wrong scope",
            state="approved",
            categories=["tool"],
            confidence=0.92,
            scope_agents=["reviewer"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed(tmp_path, target)
        _seed(tmp_path, wrong_scope)
        ctx = _make_ctx(engine)

        results = await query_memory(
            ctx,
            categories=["tool"],
            scope_agents=["builder"],
            min_confidence=0.9,
        )

        ids = [r["id"] for r in results]
        assert _uuid(50) in ids
        assert _uuid(51) not in ids
