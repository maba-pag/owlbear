"""Tests for recall_memory scope filtering, identity-bearing content blocks,
priority ordering, wildcard block, and limit behavior.

AC coverage:
  AC1 (td:2): recall returns entries where agent name is in scope_agents
  AC2 (td:2): recall includes entries where scope_agents=["*"] (universal)
  AC3 (td:2): recall excludes entries where scope_agents=[] (unscoped)
  AC4 (td:1): recall with agent="*" is code-blocked (raises ToolError)
    AC5 (td:2): return format has title, entry ID, and content, but no other metadata
  AC6 (td:2): ordering — approved entries first, then curated entries fill remaining slots
  AC7 (td:1): limit parameter works (default 20)
  AC8 (td:0): all tests fail — RED state

Interface strategy:
  recall_memory does not exist in owlbear_mcp_memory.tools yet.
  The module-level import causes ImportError, guaranteeing RED for every test.
  Expected signature: recall_memory(ctx, *, agent, categories=None, limit=None) -> str
    Return: concatenated "## {title}\\nEntry ID: `{id}`\\n{content}" blocks.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from owlbear_memory import MemoryEngine, MemoryEntry


async def _recall(*args: object, **kwargs: object) -> str:
    """Proxy that imports recall_memory at call time — fails until implemented.

    This deferred import pattern avoids a collection error while ensuring every
    test that calls _recall fails with ImportError in RED phase.
    """
    from owlbear_mcp_memory.tools import recall_memory  # noqa: PLC0415

    return await recall_memory(*args, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid(n: int) -> str:
    return f"550e8400-e29b-41d4-a716-4466554{n:05d}"


_TS = "2026-05-04T10:00:00Z"


def _make_entry(**overrides: object) -> MemoryEntry:
    """Return a valid MemoryEntry, defaulting to curated with a named scope."""
    defaults: dict[str, object] = {
        "id": _uuid(1),
        "title": "Test entry",
        "categories": ["domain-knowledge"],
        "confidence": 0.85,
        "state": "curated",
        "content": "Entry body text.",
        "scope_agents": ["builder"],
        "source_agent": "builder",
        "created_at": _TS,
        "updated_at": _TS,
        "approved_at": None,
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    """Return a mock MCP context with engine wired up."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


def _seed_entry(engine: MemoryEngine, entry: MemoryEntry) -> MemoryEntry:
    """Seed an entry through public MemoryEngine APIs with deterministic UUID."""
    with patch("owlbear_memory.engine.uuid4", return_value=UUID(entry.id)):
        seeded = engine.save(
            title=entry.title,
            content=entry.content,
            categories=entry.categories,
            confidence=entry.confidence,
            source_agent=entry.source_agent,
            scope_agents=entry.scope_agents,
        )

    seeded_result = seeded
    if entry.state == "pending":
        return seeded_result

    promoted_scope = entry.scope_agents or [entry.source_agent]
    curated = engine.edit(
        seeded.id,
        {
            "title": entry.title,
            "content": entry.content,
            "categories": entry.categories,
            "confidence": entry.confidence,
            "scope_agents": promoted_scope,
        },
        expected_updated_at=seeded.updated_at,
    )
    seeded_result = curated

    if entry.state == "curated" and not entry.scope_agents:
        seeded_result = engine.edit(
            curated.id,
            {"scope_agents": []},
            expected_updated_at=curated.updated_at,
        )
    elif entry.state == "approved":
        approved = engine.approve(curated.id, expected_updated_at=curated.updated_at)
        seeded_result = approved
        if not entry.scope_agents:
            unscoped_curated = engine.edit(
                approved.id,
                {"scope_agents": []},
                expected_updated_at=approved.updated_at,
            )
            seeded_result = engine.approve(
                unscoped_curated.id,
                expected_updated_at=unscoped_curated.updated_at,
            )
    elif entry.state == "deleted":
        seeded_result = engine.delete(curated.id, expected_updated_at=curated.updated_at)

    return seeded_result


# ---------------------------------------------------------------------------
# AC1 (td:2): recall returns entries where agent name is in scope_agents
# ---------------------------------------------------------------------------


class TestFromAC_ScopeAgentMatch:
    """AC1: recall includes entries whose scope_agents contains the requesting agent."""

    @pytest.mark.asyncio
    async def test_entry_with_agent_in_scope_is_returned(self, tmp_path: Path) -> None:
        """Entry with scope_agents=["builder"] is returned when agent="builder"."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title in result

    @pytest.mark.asyncio
    async def test_entry_with_different_agent_not_returned(self, tmp_path: Path) -> None:
        """Entry scoped to "reviewer" is not returned when agent="builder"."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["reviewer"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title not in result

    @pytest.mark.asyncio
    async def test_entry_with_agent_among_multiple_scopes_is_returned(self, tmp_path: Path) -> None:
        """Entry with scope_agents=["builder", "reviewer"] is returned for agent="builder"."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["builder", "reviewer"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title in result


# ---------------------------------------------------------------------------
# AC2 (td:2): recall includes entries where scope_agents=["*"] (universal)
# ---------------------------------------------------------------------------


class TestFromAC_UniversalScope:
    """AC2: scope_agents=["*"] entries are returned for any requesting agent."""

    @pytest.mark.asyncio
    async def test_universal_scope_entry_returned_for_named_agent(self, tmp_path: Path) -> None:
        """Entry with scope_agents=["*"] is visible to any named agent."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["*"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title in result

    @pytest.mark.asyncio
    async def test_universal_scope_entry_returned_for_different_agent(self, tmp_path: Path) -> None:
        """Entry with scope_agents=["*"] is also visible to a different named agent."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["*"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="doc-writer")

        assert entry.title in result

    @pytest.mark.asyncio
    async def test_universal_scope_approved_entry_returned(self, tmp_path: Path) -> None:
        """Approved entry with scope_agents=["*"] is also returned."""
        entry = _make_entry(
            id=_uuid(1),
            state="approved",
            scope_agents=["*"],
            approved_at=_TS,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="architect")

        assert entry.title in result


# ---------------------------------------------------------------------------
# AC3 (td:2): recall excludes entries where scope_agents=[] (unscoped)
# ---------------------------------------------------------------------------


class TestFromAC_UnscopedExclusion:
    """AC3: entries with scope_agents=[] are excluded from recall results."""

    @pytest.mark.asyncio
    async def test_unscoped_entry_not_returned(self, tmp_path: Path) -> None:
        """Entry with scope_agents=[] is excluded regardless of requesting agent."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=[])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title not in result

    @pytest.mark.asyncio
    async def test_unscoped_approved_entry_not_returned(self, tmp_path: Path) -> None:
        """Approved entry with scope_agents=[] is also excluded."""
        entry = _make_entry(
            id=_uuid(1),
            state="approved",
            scope_agents=[],
            approved_at=_TS,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title not in result

    @pytest.mark.asyncio
    async def test_mix_unscoped_and_scoped_only_scoped_returned(self, tmp_path: Path) -> None:
        """Only scoped entries are returned when mixed with unscoped entries."""
        unscoped = _make_entry(id=_uuid(1), title="Unscoped entry", state="curated", scope_agents=[])
        scoped = _make_entry(id=_uuid(2), title="Scoped entry", state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, unscoped)
        _seed_entry(engine, scoped)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "Unscoped entry" not in result
        assert "Scoped entry" in result


# ---------------------------------------------------------------------------
# AC4 (td:1): recall with agent="*" is code-blocked (raises ToolError)
# ---------------------------------------------------------------------------


class TestFromAC_WildcardAgentBlock:
    """AC4: passing agent="*" raises ToolError (wildcard callers are disallowed)."""

    @pytest.mark.asyncio
    async def test_wildcard_agent_raises_tool_error(self, tmp_path: Path) -> None:
        """recall_memory(agent="*") is rejected with ToolError."""
        from mcp.server.fastmcp.exceptions import ToolError

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await _recall(ctx, agent="*")


# ---------------------------------------------------------------------------
# AC5 (td:2): return format has title, entry ID, and content
# ---------------------------------------------------------------------------


class TestFromAC_IdentityBearingFormat:
    """AC5: result contains identity-bearing content blocks."""

    @pytest.mark.asyncio
    async def test_result_is_a_string(self, tmp_path: Path) -> None:
        """recall_memory returns a str, not a list or dict."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_title_appears_as_h2_heading(self, tmp_path: Path) -> None:
        """Title is rendered as ## heading in the returned string."""
        entry = _make_entry(
            id=_uuid(1),
            title="My Important Entry",
            state="curated",
            scope_agents=["builder"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "## My Important Entry" in result

    @pytest.mark.asyncio
    async def test_content_appears_below_heading(self, tmp_path: Path) -> None:
        """Content follows the heading and entry ID in the returned string."""
        entry = _make_entry(
            id=_uuid(1),
            title="My Entry",
            content="This is the body content.",
            state="curated",
            scope_agents=["builder"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "This is the body content." in result
        title_pos = result.index("## My Entry")
        id_pos = result.index(f"Entry ID: `{entry.id}`")
        content_pos = result.index("This is the body content.")
        assert title_pos < id_pos < content_pos

    @pytest.mark.asyncio
    async def test_result_contains_entry_id_but_no_other_metadata(self, tmp_path: Path) -> None:
        """Entry ID appears while unrelated metadata remains absent."""
        entry = _make_entry(
            id=_uuid(1),
            title="My Entry",
            state="curated",
            scope_agents=["builder"],
            confidence=0.95,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert f"Entry ID: `{entry.id}`" in result
        assert "curated" not in result
        assert "0.95" not in result
        assert "scope_agents" not in result

    @pytest.mark.asyncio
    async def test_multiple_entries_concatenated_in_result(self, tmp_path: Path) -> None:
        """Multiple matching entries all appear in a single concatenated string."""
        e1 = _make_entry(id=_uuid(1), title="First Entry", state="curated", scope_agents=["builder"])
        e2 = _make_entry(id=_uuid(2), title="Second Entry", state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, e1)
        _seed_entry(engine, e2)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "## First Entry" in result
        assert "## Second Entry" in result

    @pytest.mark.asyncio
    async def test_exact_per_entry_format_and_other_metadata_fields_absent(self, tmp_path: Path) -> None:
        """Pin the identity-bearing format and exclude unrelated metadata."""
        entry = _make_entry(
            id=_uuid(99),
            title="Format Pin Test",
            content="Pinned body text.",
            state="curated",
            confidence=0.92,
            categories=["domain-knowledge"],
            scope_agents=["recall-scope-tester"],
            source_agent="builder",
            created_at="2026-01-15T08:30:00Z",
            updated_at="2026-02-20T14:15:00Z",
            approved_at=None,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="recall-scope-tester")

        assert result == f"## Format Pin Test\nEntry ID: `{entry.id}`\nPinned body text."
        for field_name in (
            "state",
            "confidence",
            "categories",
            "scope_agents",
            "approved_at",
            "created_at",
            "updated_at",
        ):
            assert field_name not in result, f"metadata field {field_name!r} leaked into output"
        assert "curated" not in result  # state value
        assert "0.92" not in result  # confidence value
        assert "domain-knowledge" not in result  # category value
        assert "recall-scope-tester" not in result  # scope_agents value
        assert "2026-01-15T08:30:00Z" not in result  # created_at value
        assert "2026-02-20T14:15:00Z" not in result  # updated_at value

    @pytest.mark.asyncio
    async def test_two_entries_keep_ids_paired_and_use_double_newline_separator(self, tmp_path: Path) -> None:
        """Each ID stays with its entry and complete blocks use a blank separator."""
        e1 = _make_entry(
            id=_uuid(1),
            title="Alpha Entry",
            content="Alpha content.",
            state="curated",
            scope_agents=["builder"],
        )
        e2 = _make_entry(
            id=_uuid(2),
            title="Beta Entry",
            content="Beta content.",
            state="curated",
            scope_agents=["builder"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _seed_entry(engine, e1)
        _seed_entry(engine, e2)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        expected = (
            f"## Alpha Entry\nEntry ID: `{e1.id}`\nAlpha content.\n\n## Beta Entry\nEntry ID: `{e2.id}`\nBeta content."
        )
        assert result == expected


# ---------------------------------------------------------------------------
# AC6 (td:2): ordering — approved entries first, curated entries second
# ---------------------------------------------------------------------------


class TestFromAC_LimitParameter:
    """AC7: limit caps the number of entries returned; default is 20."""

    @pytest.mark.asyncio
    async def test_limit_caps_number_of_entries_returned(self, tmp_path: Path) -> None:
        """With limit=2 and 5 matching entries, only 2 appear in the result."""
        engine = MemoryEngine(memory_dir=tmp_path)
        for i in range(1, 6):
            _seed_entry(
                engine,
                _make_entry(
                    id=_uuid(i),
                    title=f"Entry {i}",
                    state="curated",
                    scope_agents=["builder"],
                ),
            )
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder", limit=2)

        # Count how many ## headings appear
        heading_count = result.count("\n## ") + (1 if result.startswith("## ") else 0)
        assert heading_count == 2

    @pytest.mark.asyncio
    async def test_default_limit_is_20(self, tmp_path: Path) -> None:
        """Without explicit limit, at most 20 entries are returned by default."""
        engine = MemoryEngine(memory_dir=tmp_path)
        for i in range(1, 26):  # 25 entries
            _seed_entry(
                engine,
                _make_entry(
                    id=_uuid(i),
                    title=f"Entry {i:02d}",
                    state="curated",
                    scope_agents=["builder"],
                ),
            )
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        heading_count = result.count("\n## ") + (1 if result.startswith("## ") else 0)
        assert heading_count <= 20

    @pytest.mark.asyncio
    async def test_default_limit_is_exactly_20(self, tmp_path: Path) -> None:
        """Default limit returns exactly 20 entries — a broken default of 5 or 12
        must fail (AC7-fix: exact equality check, not <= 20)."""
        engine = MemoryEngine(memory_dir=tmp_path)
        for i in range(1, 26):  # 25 entries
            _seed_entry(
                engine,
                _make_entry(
                    id=_uuid(i),
                    title=f"Exact Limit Entry {i:02d}",
                    state="curated",
                    scope_agents=["builder"],
                ),
            )
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        heading_count = result.count("\n## ") + (1 if result.startswith("## ") else 0)
        assert heading_count == 20  # must be exactly 20, not just <= 20
