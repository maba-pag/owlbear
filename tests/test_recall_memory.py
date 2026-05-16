"""Failing tests for #1308: recall_memory tool — scope filtering, body-only
format, priority ordering, wildcard block, and limit parameter.

AC coverage:
  AC1 (td:2): recall returns entries where agent name is in scope_agents
  AC2 (td:2): recall includes entries where scope_agents=["*"] (universal)
  AC3 (td:2): recall excludes entries where scope_agents=[] (unscoped)
  AC4 (td:1): recall with agent="*" is code-blocked (raises ToolError)
  AC5 (td:2): return format is body-only: title as ## heading, content below, no metadata
  AC6 (td:2): ordering — approved entries first, then curated entries fill remaining slots
  AC7 (td:1): limit parameter works (default 20)
  AC8 (td:0): all tests fail — RED state

Interface strategy:
  recall_memory does not exist in owlbear_mcp_memory.tools yet.
  The module-level import causes ImportError, guaranteeing RED for every test.
  Expected signature: recall_memory(ctx, *, agent, categories=None, limit=None) -> str
  Return: concatenated "## {title}\\n{content}" blocks, approved before curated.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry


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
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title in result

    @pytest.mark.asyncio
    async def test_entry_with_different_agent_not_returned(self, tmp_path: Path) -> None:
        """Entry scoped to "reviewer" is not returned when agent="builder"."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["reviewer"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title not in result

    @pytest.mark.asyncio
    async def test_entry_with_agent_among_multiple_scopes_is_returned(self, tmp_path: Path) -> None:
        """Entry with scope_agents=["builder", "reviewer"] is returned for agent="builder"."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["builder", "reviewer"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
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
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title in result

    @pytest.mark.asyncio
    async def test_universal_scope_entry_returned_for_different_agent(self, tmp_path: Path) -> None:
        """Entry with scope_agents=["*"] is also visible to a different named agent."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["*"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
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
        engine.write(entry)
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
        engine.write(entry)
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
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert entry.title not in result

    @pytest.mark.asyncio
    async def test_mix_unscoped_and_scoped_only_scoped_returned(self, tmp_path: Path) -> None:
        """Only scoped entries are returned when mixed with unscoped entries."""
        unscoped = _make_entry(id=_uuid(1), title="Unscoped entry", state="curated", scope_agents=[])
        scoped = _make_entry(id=_uuid(2), title="Scoped entry", state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(unscoped)
        engine.write(scoped)
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
# AC5 (td:2): return format is body-only: title as ## heading, content below
# ---------------------------------------------------------------------------


class TestFromAC_BodyOnlyFormat:
    """AC5: result is a plain string with ## title and content — no metadata."""

    @pytest.mark.asyncio
    async def test_result_is_a_string(self, tmp_path: Path) -> None:
        """recall_memory returns a str, not a list or dict."""
        entry = _make_entry(id=_uuid(1), state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
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
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "## My Important Entry" in result

    @pytest.mark.asyncio
    async def test_content_appears_below_heading(self, tmp_path: Path) -> None:
        """Content follows the ## heading in the returned string."""
        entry = _make_entry(
            id=_uuid(1),
            title="My Entry",
            content="This is the body content.",
            state="curated",
            scope_agents=["builder"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "This is the body content." in result
        # Title heading must precede content
        title_pos = result.index("## My Entry")
        content_pos = result.index("This is the body content.")
        assert title_pos < content_pos

    @pytest.mark.asyncio
    async def test_result_contains_no_metadata_fields(self, tmp_path: Path) -> None:
        """Metadata fields (id, state, confidence, etc.) do not appear in the result."""
        entry = _make_entry(
            id=_uuid(1),
            title="My Entry",
            state="curated",
            scope_agents=["builder"],
            confidence=0.95,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "curated" not in result
        assert "0.95" not in result
        assert entry.id not in result
        assert "scope_agents" not in result

    @pytest.mark.asyncio
    async def test_multiple_entries_concatenated_in_result(self, tmp_path: Path) -> None:
        """Multiple matching entries all appear in a single concatenated string."""
        e1 = _make_entry(id=_uuid(1), title="First Entry", state="curated", scope_agents=["builder"])
        e2 = _make_entry(id=_uuid(2), title="Second Entry", state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(e1)
        engine.write(e2)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "## First Entry" in result
        assert "## Second Entry" in result

    @pytest.mark.asyncio
    async def test_exact_per_entry_format_and_all_metadata_fields_absent(self, tmp_path: Path) -> None:
        """Pins exact output format and asserts ALL metadata field names and values
        are absent from the returned string (AC5-fix: discriminating check)."""
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
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="recall-scope-tester")

        # Pin exact per-entry format: "## {title}\n{content}"
        assert result == "## Format Pin Test\nPinned body text."
        # Assert ALL metadata field names absent
        for field_name in (
            "id",
            "state",
            "confidence",
            "categories",
            "scope_agents",
            "approved_at",
            "created_at",
            "updated_at",
        ):
            assert field_name not in result, f"metadata field {field_name!r} leaked into output"
        # Assert metadata values absent
        assert _uuid(99) not in result  # id value
        assert "curated" not in result  # state value
        assert "0.92" not in result  # confidence value
        assert "domain-knowledge" not in result  # category value
        assert "recall-scope-tester" not in result  # scope_agents value
        assert "2026-01-15T08:30:00Z" not in result  # created_at value
        assert "2026-02-20T14:15:00Z" not in result  # updated_at value

    @pytest.mark.asyncio
    async def test_two_entries_joined_with_double_newline_separator(self, tmp_path: Path) -> None:
        """Two matching entries are joined by '\\n\\n' — exact per-entry format pinned
        (AC5-fix: separator proof)."""
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
        engine.write(e1)
        engine.write(e2)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        # _uuid(1) < _uuid(2): same state+confidence, alpha sorts first by id
        expected = "## Alpha Entry\nAlpha content.\n\n## Beta Entry\nBeta content."
        assert result == expected


# ---------------------------------------------------------------------------
# AC6 (td:2): ordering — approved entries first, curated entries second
# ---------------------------------------------------------------------------


class TestFromAC_PriorityOrdering:
    """AC6: approved entries appear before curated entries in the output."""

    @pytest.mark.asyncio
    async def test_approved_entry_appears_before_curated_in_result(self, tmp_path: Path) -> None:
        """When both approved and curated entries match, approved comes first."""
        curated = _make_entry(
            id=_uuid(1),
            title="Curated Entry",
            state="curated",
            scope_agents=["builder"],
        )
        approved = _make_entry(
            id=_uuid(2),
            title="Approved Entry",
            state="approved",
            scope_agents=["builder"],
            approved_at=_TS,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        # Write curated first to test that order is not by insertion
        engine.write(curated)
        engine.write(approved)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        approved_pos = result.index("## Approved Entry")
        curated_pos = result.index("## Curated Entry")
        assert approved_pos < curated_pos

    @pytest.mark.asyncio
    async def test_multiple_approved_entries_all_precede_curated_entries(self, tmp_path: Path) -> None:
        """All approved entries appear before any curated entry in the output."""
        c1 = _make_entry(
            id=_uuid(1),
            title="Curated One",
            state="curated",
            scope_agents=["builder"],
        )
        a1 = _make_entry(
            id=_uuid(2),
            title="Approved One",
            state="approved",
            scope_agents=["builder"],
            approved_at=_TS,
        )
        a2 = _make_entry(
            id=_uuid(3),
            title="Approved Two",
            state="approved",
            scope_agents=["builder"],
            approved_at=_TS,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(c1)
        engine.write(a1)
        engine.write(a2)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        curated_pos = result.index("## Curated One")
        approved1_pos = result.index("## Approved One")
        approved2_pos = result.index("## Approved Two")
        assert approved1_pos < curated_pos
        assert approved2_pos < curated_pos

    @pytest.mark.asyncio
    async def test_pending_entries_are_excluded_from_results(self, tmp_path: Path) -> None:
        """Pending entries are not included even if scope_agents matches."""
        pending = _make_entry(
            id=_uuid(1),
            title="Pending Entry",
            state="pending",
            scope_agents=["builder"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(pending)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "## Pending Entry" not in result

    @pytest.mark.asyncio
    async def test_deleted_entries_are_excluded_from_results(self, tmp_path: Path) -> None:
        """Deleted entries are not included even if scope_agents matches."""
        deleted = _make_entry(
            id=_uuid(1),
            title="Deleted Entry",
            state="deleted",
            scope_agents=["builder"],
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(deleted)
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        assert "## Deleted Entry" not in result

    @pytest.mark.asyncio
    async def test_sort_then_slice_approved_fills_before_curated(self, tmp_path: Path) -> None:
        """With 3 approved + 3 curated entries and limit=4, all 3 approved survive
        and exactly 1 curated fills the remaining slot.

        Non-cooperative fixture: curated titles begin with "Aaa" and approved
        titles begin with "Zzz". Disk load (sorted filenames) therefore returns
        curated entries first. recall_memory's .sort() must reorder them so that
        approved appears before curated before slicing. A slice-before-sort bug
        would produce curated-first results and fail at least one of the assertions
        below. (AC6-fix v2: discriminating sort-then-slice proof)
        """
        # "Aaa Curated ..." slugs sort alphabetically BEFORE "Zzz Approved ..." slugs.
        # Engine.load() returns entries in filename order → curated loads first.
        curated_titles = [
            "Aaa Curated One",
            "Aaa Curated Three",
            "Aaa Curated Two",
        ]
        approved_titles = [
            "Zzz Approved One",
            "Zzz Approved Three",
            "Zzz Approved Two",
        ]

        engine = MemoryEngine(memory_dir=tmp_path)
        for i, title in enumerate(curated_titles, start=10):
            engine.write(
                _make_entry(
                    id=_uuid(i),
                    title=title,
                    state="curated",
                    scope_agents=["builder"],
                )
            )
        for i, title in enumerate(approved_titles, start=20):
            engine.write(
                _make_entry(
                    id=_uuid(i),
                    title=title,
                    state="approved",
                    scope_agents=["builder"],
                    approved_at=_TS,
                )
            )
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder", limit=4)

        heading_count = result.count("\n## ") + (1 if result.startswith("## ") else 0)
        assert heading_count == 4  # exactly limit entries returned
        # All 3 approved entries must survive the sort-then-slice (a slice-before-sort
        # bug would keep 3 curated + 1 approved instead)
        for title in approved_titles:
            assert f"## {title}" in result, f"approved entry '{title}' missing — sort-then-slice may be broken"
        # Exactly 1 curated entry fills the remaining slot
        curated_in_result = sum(1 for t in curated_titles if f"## {t}" in result)
        assert curated_in_result == 1, f"expected 1 curated entry in result, got {curated_in_result}"


# ---------------------------------------------------------------------------
# AC7 (td:1): limit parameter works (default 20)
# ---------------------------------------------------------------------------


class TestFromAC_LimitParameter:
    """AC7: limit caps the number of entries returned; default is 20."""

    @pytest.mark.asyncio
    async def test_limit_caps_number_of_entries_returned(self, tmp_path: Path) -> None:
        """With limit=2 and 5 matching entries, only 2 appear in the result."""
        engine = MemoryEngine(memory_dir=tmp_path)
        for i in range(1, 6):
            engine.write(
                _make_entry(
                    id=_uuid(i),
                    title=f"Entry {i}",
                    state="curated",
                    scope_agents=["builder"],
                )
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
            engine.write(
                _make_entry(
                    id=_uuid(i),
                    title=f"Entry {i:02d}",
                    state="curated",
                    scope_agents=["builder"],
                )
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
            engine.write(
                _make_entry(
                    id=_uuid(i),
                    title=f"Exact Limit Entry {i:02d}",
                    state="curated",
                    scope_agents=["builder"],
                )
            )
        ctx = _make_ctx(engine)

        result = await _recall(ctx, agent="builder")

        heading_count = result.count("\n## ") + (1 if result.startswith("## ") else 0)
        assert heading_count == 20  # must be exactly 20, not just <= 20
