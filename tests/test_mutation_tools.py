"""Failing tests for #1306: Mutation tool tests (save, list, read, curate, delete, approve).

AC coverage:
  AC1 (td:2): save_memory creates entry with state=pending, returns guidance hint
  AC2 (td:2): list_memories returns metadata without body, sorts pending-first by
              created_at, filters by state/categories/scope_agents
  AC3 (td:2): read_memory returns full entry by ID, errors on invalid/deleted IDs
  AC4 (td:2): curate_memory validates: title non-empty, content <=1024,
              confidence [0.7,1.0], categories >=1
  AC5 (td:2): curate_memory returns correct guidance hint per state transition
  AC6 (td:2): delete_memory returns correct hint for hard-delete vs soft-delete
  AC7 (td:2): approve_memory only works on curated entries, errors on other states
  AC8 (td:1): OWLBEAR_MEMORY_CALLER env var has no effect (access control removed)
  AC9 (td:1): MEMORY_TOOLS_EXCLUDE env var has no effect (access control removed)
  AC10 (td:2): validation errors return teaching messages (Brief guidance hints table)
  AC11 (td:0): all tests fail per-method, no collection-time ImportError

Structural constraint (from task): tests for save_memory, list_memories, read_memory,
and approve_memory use localized import inside each test method because those functions
do not yet exist. This avoids a collection-time ImportError that would block sibling
tests in other AC classes.

RED failure modes:
  1. save_memory, list_memories, read_memory, approve_memory don't exist → ImportError
     (converted to pytest.fail) inside each test method
  2. curate_memory / delete_memory return dicts without "hint" key → KeyError/AssertionError
  3. curate_memory requires caller="curator" via _require_role → ToolError raised
     when test expects none (AC8)
  4. _apply_tool_exclusions still present in server module (AC9)
  5. Validation error messages are raw Pydantic text, not Brief teaching messages (AC4/AC10)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryEntry
from owlbear_mcp_memory.tools import curate_memory, delete_memory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid(n: int) -> str:
    return f"550e8400-e29b-41d4-a716-4466554{n:05d}"


def _make_entry(  # noqa: PLR0913
    *,
    n: int = 1,
    state: str = "pending",
    categories: list[str] | None = None,
    scope_agents: list[str] | None = None,
    content: str = "Entry body text.",
    approved_at: str | None = None,
    **extra: object,
) -> MemoryEntry:
    """Return a valid MemoryEntry with predictable timestamps for ordering tests."""
    if scope_agents is None:
        scope_agents = [] if state == "pending" else ["builder"]
    return MemoryEntry(
        id=_uuid(n),
        title=f"Entry {n}",
        categories=categories or ["domain-knowledge"],
        confidence=0.85,
        state=state,
        content=content,
        scope_agents=scope_agents,
        source_agent="builder",
        created_at=f"2026-05-01T10:00:0{n}Z",
        updated_at=f"2026-05-01T10:00:0{n}Z",
        approved_at=approved_at,
        **extra,
    )


def _make_ctx(engine: MemoryEngine, caller: str = "curator") -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    ctx.request_context.lifespan_context.caller = caller
    return ctx


# ---------------------------------------------------------------------------
# AC1 (td:2): save_memory creates entry with state=pending, returns guidance hint
# ---------------------------------------------------------------------------


class TestFromAC_SaveMemory:
    """AC1: save_memory creates entry with state=pending and returns guidance hint."""

    @pytest.mark.asyncio
    async def test_save_memory_creates_pending_entry(self, tmp_path: Path) -> None:
        """save_memory creates an entry with state=pending.

        RED: save_memory does not exist in owlbear_mcp_memory.tools → ImportError
        converted to pytest.fail.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        result = await save_memory(
            ctx,
            title="Lesson learned",
            content="Short content body.",
            categories=["domain-knowledge"],
            confidence=0.85,
            source_agent="builder",
        )

        assert result["state"] == "pending"

    @pytest.mark.asyncio
    async def test_save_memory_returns_hint_key(self, tmp_path: Path) -> None:
        """save_memory return value must include a 'hint' guidance key.

        RED: save_memory does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        result = await save_memory(
            ctx,
            title="Lesson learned",
            content="Short content body.",
            categories=["domain-knowledge"],
            confidence=0.85,
            source_agent="builder",
        )

        assert "hint" in result, "save_memory must return a 'hint' guidance key"

    @pytest.mark.asyncio
    async def test_save_memory_persists_to_disk(self, tmp_path: Path) -> None:
        """save_memory writes the entry to disk (engine.get_entry succeeds after call).

        RED: save_memory does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        result = await save_memory(
            ctx,
            title="Lesson learned",
            content="Short content body.",
            categories=["domain-knowledge"],
            confidence=0.85,
            source_agent="builder",
        )

        loaded = engine.get_entry(result["id"])
        assert str(loaded.state) == "pending"

    @pytest.mark.asyncio
    async def test_save_memory_uses_provided_source_agent(self, tmp_path: Path) -> None:
        """save_memory records the source_agent parameter, not the ctx caller.

        RED: save_memory does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="some-other-agent")

        result = await save_memory(
            ctx,
            title="Lesson learned",
            content="Short content body.",
            categories=["domain-knowledge"],
            confidence=0.85,
            source_agent="specific-builder",
        )

        assert result["source_agent"] == "specific-builder"

    @pytest.mark.asyncio
    async def test_save_memory_hint_identifies_save_pending_guidance(self, tmp_path: Path) -> None:
        """save_memory hint contains discriminating substrings uniquely identifying save-pending guidance.

        Refined AC1: hint must mention both 'pending' state and curation action — a generic
        'OK' or 'Entry created' message cannot pass this test.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        result = await save_memory(
            ctx,
            title="Lesson learned",
            content="Short content body.",
            categories=["domain-knowledge"],
            confidence=0.85,
            source_agent="builder",
        )

        hint = result.get("hint", "")
        hint_lower = hint.lower()
        assert "pending" in hint_lower, f"save_memory hint must identify 'pending' state, got: {hint!r}"
        assert "curate" in hint_lower, f"save_memory hint must mention curation action ('curate'), got: {hint!r}"


# ---------------------------------------------------------------------------
# AC2 (td:2): list_memories returns metadata without body, pending-first, filters
# ---------------------------------------------------------------------------


class TestFromAC_ListMemories:
    """AC2: list_memories returns metadata-only (no body), pending-first sort, filters."""

    @pytest.mark.asyncio
    async def test_list_memories_omits_content_body(self, tmp_path: Path) -> None:
        """list_memories result dicts must NOT contain 'content' (body excluded).

        RED: list_memories does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import list_memories
        except ImportError as exc:
            pytest.fail(f"list_memories not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        results = await list_memories(ctx)

        assert len(results) >= 1, "expected at least one entry in results"
        for r in results:
            assert "content" not in r, "list_memories must not return body content"

    @pytest.mark.asyncio
    async def test_list_memories_pending_before_curated(self, tmp_path: Path) -> None:
        """list_memories sorts pending entries before curated entries.

        RED: list_memories does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import list_memories
        except ImportError as exc:
            pytest.fail(f"list_memories not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        curated = _make_entry(n=1, state="curated", scope_agents=["builder"])
        pending = _make_entry(n=2, state="pending", scope_agents=[])
        engine.write(curated)
        engine.write(pending)
        ctx = _make_ctx(engine)

        results = await list_memories(ctx, states=["pending", "curated"])

        states_in_order = [r["state"] for r in results]
        pending_idx = [i for i, s in enumerate(states_in_order) if s == "pending"]
        curated_idx = [i for i, s in enumerate(states_in_order) if s == "curated"]
        assert pending_idx, "pending entries must appear in results"
        assert curated_idx, "curated entries must appear in results"
        assert max(pending_idx) < min(curated_idx), (
            "pending entries must appear before curated entries in list_memories"
        )

    @pytest.mark.asyncio
    async def test_list_memories_excludes_deleted_by_default(self, tmp_path: Path) -> None:
        """list_memories default view excludes deleted entries.

        RED: list_memories does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import list_memories
        except ImportError as exc:
            pytest.fail(f"list_memories not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        curated = _make_entry(n=1, state="curated", scope_agents=["builder"])
        deleted = _make_entry(n=2, state="deleted", scope_agents=["builder"])
        engine.write(curated)
        engine.write(deleted)
        ctx = _make_ctx(engine)

        results = await list_memories(ctx)

        returned_states = {r["state"] for r in results}
        assert "deleted" not in returned_states, "deleted entries must be excluded by default"

    @pytest.mark.asyncio
    async def test_list_memories_filters_by_categories(self, tmp_path: Path) -> None:
        """list_memories filters results to only entries matching requested categories.

        RED: list_memories does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import list_memories
        except ImportError as exc:
            pytest.fail(f"list_memories not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry_dk = _make_entry(
            n=1,
            state="curated",
            categories=["domain-knowledge"],
            scope_agents=["builder"],
        )
        entry_pt = _make_entry(n=2, state="curated", categories=["pitfall"], scope_agents=["builder"])
        engine.write(entry_dk)
        engine.write(entry_pt)
        ctx = _make_ctx(engine)

        results = await list_memories(ctx, categories=["pitfall"])

        assert len(results) == 1
        assert results[0]["id"] == entry_pt.id

    @pytest.mark.asyncio
    async def test_list_memories_filters_by_scope_agents(self, tmp_path: Path) -> None:
        """list_memories filters results to only entries matching scope_agents.

        RED: list_memories does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import list_memories
        except ImportError as exc:
            pytest.fail(f"list_memories not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry_a = _make_entry(n=1, state="curated", scope_agents=["builder"])
        entry_b = _make_entry(n=2, state="curated", scope_agents=["reviewer"])
        engine.write(entry_a)
        engine.write(entry_b)
        ctx = _make_ctx(engine)

        results = await list_memories(ctx, scope_agents=["builder"])

        assert len(results) == 1
        assert results[0]["id"] == entry_a.id

    @pytest.mark.asyncio
    async def test_list_memories_same_state_ordered_by_created_at(self, tmp_path: Path) -> None:
        """Within the same state, list_memories sorts entries by created_at ascending.

        Refined AC2: 2+ pending entries with different created_at — the entry with
        the earlier created_at must appear first within the same state group.
        """
        try:
            from owlbear_mcp_memory.tools import list_memories
        except ImportError as exc:
            pytest.fail(f"list_memories not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        # n=1 → created_at=2026-05-01T10:00:01Z (earlier)
        # n=2 → created_at=2026-05-01T10:00:02Z (later)
        earlier = _make_entry(n=1, state="pending")
        later = _make_entry(n=2, state="pending")
        # Write in reverse insertion order to prove sort is by created_at, not arrival
        engine.write(later)
        engine.write(earlier)
        ctx = _make_ctx(engine)

        results = await list_memories(ctx, states=["pending"])

        pending_results = [r for r in results if r["state"] == "pending"]
        assert len(pending_results) >= 2, "expected at least 2 pending entries"
        created_ats = [r["created_at"] for r in pending_results]
        assert created_ats == sorted(created_ats), (
            f"Same-state entries must be sorted by created_at ascending. Got order: {created_ats}"
        )

    @pytest.mark.asyncio
    async def test_list_memories_explicit_states_filter_excludes_curated(self, tmp_path: Path) -> None:
        """Passing states=['pending'] explicitly excludes curated entries from results.

        Refined AC2: explicit state filter must gate output — curated entries must NOT
        appear when states=['pending'] is specified, even when curated entries exist.
        """
        try:
            from owlbear_mcp_memory.tools import list_memories
        except ImportError as exc:
            pytest.fail(f"list_memories not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        pending = _make_entry(n=1, state="pending")
        curated = _make_entry(n=2, state="curated", scope_agents=["builder"])
        engine.write(pending)
        engine.write(curated)
        ctx = _make_ctx(engine)

        results = await list_memories(ctx, states=["pending"])

        returned_states = {r["state"] for r in results}
        assert "curated" not in returned_states, (
            f"list_memories(states=['pending']) must exclude curated entries; got states: {returned_states}"
        )
        assert "pending" in returned_states, "list_memories(states=['pending']) must include pending entries"


# ---------------------------------------------------------------------------
# AC3 (td:2): read_memory returns full entry by ID, errors on invalid/deleted IDs
# ---------------------------------------------------------------------------


class TestFromAC_ReadMemory:
    """AC3: read_memory returns full entry by ID; errors on invalid/deleted IDs."""

    @pytest.mark.asyncio
    async def test_read_memory_returns_full_entry_with_content(self, tmp_path: Path) -> None:
        """read_memory returns the full entry including 'content' body.

        RED: read_memory does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import read_memory
        except ImportError as exc:
            pytest.fail(f"read_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(
            n=1,
            state="curated",
            scope_agents=["builder"],
            content="Rich body text here.",
        )
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await read_memory(ctx, entry_id=entry.id)

        assert "content" in result, "read_memory must include body content"
        assert result["content"] == "Rich body text here."

    @pytest.mark.asyncio
    async def test_read_memory_returns_all_metadata_fields(self, tmp_path: Path) -> None:
        """read_memory result includes all frontmatter metadata fields.

        RED: read_memory does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import read_memory
        except ImportError as exc:
            pytest.fail(f"read_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await read_memory(ctx, entry_id=entry.id)

        required_fields = (
            "id",
            "title",
            "categories",
            "confidence",
            "state",
            "scope_agents",
            "source_agent",
            "created_at",
            "updated_at",
        )
        for field in required_fields:
            assert field in result, f"read_memory result missing field: {field}"

    @pytest.mark.asyncio
    async def test_read_memory_raises_for_nonexistent_id(self, tmp_path: Path) -> None:
        """read_memory raises ToolError when entry ID does not exist in engine.

        RED: read_memory does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import read_memory
        except ImportError as exc:
            pytest.fail(f"read_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await read_memory(ctx, entry_id=_uuid(9))

    @pytest.mark.asyncio
    async def test_read_memory_raises_for_deleted_entry(self, tmp_path: Path) -> None:
        """read_memory raises ToolError when the entry is in deleted state.

        RED: read_memory does not exist → ImportError.
        """
        try:
            from owlbear_mcp_memory.tools import read_memory
        except ImportError as exc:
            pytest.fail(f"read_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        deleted = _make_entry(n=1, state="deleted", scope_agents=[])
        engine.write(deleted)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await read_memory(ctx, entry_id=deleted.id)


# ---------------------------------------------------------------------------
# AC4 (td:2): curate_memory validates field constraints with teaching messages
# ---------------------------------------------------------------------------


class TestFromAC_CurateMemoryValidation:
    """AC4: curate_memory raises ToolError with teaching messages for bad inputs.

    These tests assert BOTH that validation fires AND that the error message is a
    teaching message (per the Brief), not raw Pydantic output. They fail because
    current errors are raw Pydantic text — not teaching messages.
    """

    @pytest.mark.asyncio
    async def test_curate_memory_rejects_blank_title_with_teaching_message(self, tmp_path: Path) -> None:
        """curate_memory ToolError for blank title contains teaching message about title.

        RED: current error is raw Pydantic ValidationError str, not a teaching message.
        'Value should have at least 1 character' does not mention 'title' in user terms.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError) as exc_info:
            await curate_memory(ctx, entry_id=entry.id, title="")

        # Teaching message must be user-facing, not raw Pydantic
        error_text = str(exc_info.value).lower()
        # Teaching message must say "non-empty" (not Pydantic's "must not be empty")
        assert "non-empty" in error_text, f"Expected teaching message with 'non-empty', got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_curate_memory_rejects_oversized_content_with_teaching_message(self, tmp_path: Path) -> None:
        """curate_memory ToolError for content >1024 chars contains teaching message.

        RED: current error is raw Pydantic text ('String should have at most 1024 characters').
        Teaching message should say 'Content exceeds 1024-character limit...'
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError) as exc_info:
            await curate_memory(ctx, entry_id=entry.id, content="x" * 1025)

        error_text = str(exc_info.value).lower()
        # Teaching message must mention "split" (Brief: "Split into focused entries")
        # Pydantic says "String should have at most 1024 characters" — no "split"
        assert "split" in error_text or "focused" in error_text, (
            f"Expected teaching message with 'split'/'focused entries', got: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_curate_memory_rejects_confidence_below_range_with_teaching_message(self, tmp_path: Path) -> None:
        """curate_memory ToolError for confidence < 0.7 contains teaching message.

        RED: raw Pydantic error mentions 'greater than or equal to 0.7', not the
        Brief teaching message 'Confidence must be between 0.7 and 1.0'.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError) as exc_info:
            await curate_memory(ctx, entry_id=entry.id, confidence=0.5)

        error_text = str(exc_info.value).lower()
        # Teaching message must say "between" (Brief: "Confidence must be between 0.7 and 1.0")
        # Pydantic says "Input should be greater than or equal to 0.7" — no "between"
        assert "between" in error_text, f"Expected teaching message with 'between', got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_curate_memory_rejects_confidence_above_range_with_teaching_message(self, tmp_path: Path) -> None:
        """curate_memory ToolError for confidence > 1.0 contains teaching message.

        AC4 (3rd-pass refinement): BOTH bounds of [0.7, 1.0] must be proven.
        This test exercises the upper bound (confidence=1.5 > 1.0).
        The teaching message must contain 'between' per Brief.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError) as exc_info:
            await curate_memory(ctx, entry_id=entry.id, confidence=1.5)

        error_text = str(exc_info.value).lower()
        # Teaching message must say "between" (Brief: "Confidence must be between 0.7 and 1.0")
        assert "between" in error_text, (
            f"Expected teaching message with 'between' for upper bound, got: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_curate_memory_rejects_empty_categories_with_teaching_message(self, tmp_path: Path) -> None:
        """curate_memory ToolError for empty categories contains teaching message.

        RED: raw Pydantic error says 'List should have at least 1 item', not the
        Brief teaching message 'Provide at least one category from: ...'
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError) as exc_info:
            await curate_memory(ctx, entry_id=entry.id, categories=[])

        error_text = str(exc_info.value).lower()
        # Teaching message must say "provide" (Brief: "Provide at least one category from: {list}")
        # Pydantic says "List should have at least 1 item after validation" — no "provide"
        assert "provide" in error_text, f"Expected teaching message with 'provide', got: {exc_info.value}"


# ---------------------------------------------------------------------------
# AC5 (td:2): curate_memory returns correct guidance hint per state transition
# ---------------------------------------------------------------------------


class TestFromAC_CurateMemoryHint:
    """AC5: curate_memory return value includes correct guidance hint per state transition.

    RED: curate_memory → update_entry → _entry_to_dict(updated) has no 'hint' key.
    All tests fail with AssertionError on 'hint' in result.
    """

    @pytest.mark.asyncio
    async def test_curate_memory_pending_to_curated_returns_hint(self, tmp_path: Path) -> None:
        """Promoting pending→curated: hint mentions promotion and scope."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="pending", scope_agents=[])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await curate_memory(ctx, entry_id=entry.id, scope_agents=["builder"])

        assert "hint" in result, "curate_memory must return a 'hint' key"
        hint = result["hint"].lower()
        assert "promot" in hint or "curated" in hint, (
            f"Hint for pending→curated should mention promotion/curated, got: {result['hint']}"
        )

    @pytest.mark.asyncio
    async def test_curate_memory_approved_to_curated_returns_downgrade_hint(self, tmp_path: Path) -> None:
        """Auto-downgrade approved→curated: hint mentions downgrade and re-approval."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(
            n=1,
            state="approved",
            scope_agents=["builder"],
            approved_at="2026-05-01T10:00:01Z",
        )
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await curate_memory(ctx, entry_id=entry.id, title="Updated title")

        assert "hint" in result, "curate_memory must return a 'hint' key"
        hint = result["hint"].lower()
        assert "downgrad" in hint or "approv" in hint, (
            f"Hint for approved→curated should mention downgrade/re-approval, got: {result['hint']}"
        )

    @pytest.mark.asyncio
    async def test_curate_memory_curated_stays_curated_returns_update_hint(self, tmp_path: Path) -> None:
        """Editing curated→curated: hint mentions the update and curated state."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await curate_memory(ctx, entry_id=entry.id, title="Improved title")

        assert "hint" in result, "curate_memory must return a 'hint' key"
        hint = result["hint"].lower()
        assert "updat" in hint, (
            f"Hint for curated→curated must specifically mention update (not just 'curated'), got: {result['hint']}"
        )

    @pytest.mark.asyncio
    async def test_curate_memory_pending_to_curated_hint_identifies_transition(self, tmp_path: Path) -> None:
        """pending→curated hint contains discriminating phrases identifying both states.

        Refined AC5: hint must contain 'pending' or 'promot' AND 'curated' so it
        cannot be confused with the approved→curated downgrade or update-in-place hint.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="pending", scope_agents=[])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await curate_memory(ctx, entry_id=entry.id, scope_agents=["builder"])

        hint = result.get("hint", "")
        hint_lower = hint.lower()
        assert "pending" in hint_lower or "promot" in hint_lower, (
            f"pending→curated hint must identify promotion from pending, got: {hint!r}"
        )
        assert "curated" in hint_lower, f"pending→curated hint must mention curated state, got: {hint!r}"

    @pytest.mark.asyncio
    async def test_curate_memory_approved_to_curated_hint_identifies_downgrade(self, tmp_path: Path) -> None:
        """approved→curated hint contains discriminating phrase identifying a downgrade.

        Refined AC5: hint must contain 'downgrad' or 're-approv' so it cannot be
        confused with the pending→curated promotion hint or the update-in-place hint.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(
            n=1,
            state="approved",
            scope_agents=["builder"],
            approved_at="2026-05-01T10:00:01Z",
        )
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await curate_memory(ctx, entry_id=entry.id, title="Updated title")

        hint = result.get("hint", "")
        hint_lower = hint.lower()
        assert "downgrad" in hint_lower or "re-approv" in hint_lower or "re-approve" in hint_lower, (
            f"approved→curated hint must mention downgrade/re-approval to be discriminating, got: {hint!r}"
        )

    @pytest.mark.asyncio
    async def test_curate_memory_curated_update_hint_does_not_imply_transition(self, tmp_path: Path) -> None:
        """curated→curated update hint is distinct from promotion/downgrade hints.

        Refined AC5: update-in-place hint must NOT mention 'pending' (would imply
        promotion) or 'downgrad' (would imply downgrade). It must indicate a plain update.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await curate_memory(ctx, entry_id=entry.id, title="Refined title")

        hint = result.get("hint", "")
        hint_lower = hint.lower()
        assert "pending" not in hint_lower, (
            f"curated→curated hint must not mention pending (implies promotion), got: {hint!r}"
        )
        assert "downgrad" not in hint_lower, f"curated→curated hint must not mention downgrade, got: {hint!r}"
        assert "updat" in hint_lower, (
            f"curated→curated hint must specifically mention update (not just 'curated'), got: {hint!r}"
        )


# ---------------------------------------------------------------------------
# AC6 (td:2): delete_memory returns correct hint for hard-delete vs soft-delete
# ---------------------------------------------------------------------------


class TestFromAC_DeleteMemoryHint:
    """AC6: delete_memory returns guidance hint distinguishing hard-delete from soft-delete.

    RED: delete_memory → delete_entry → _entry_to_dict(updated) has no 'hint' key.
    All tests fail with AssertionError on 'hint' in result.
    """

    @pytest.mark.asyncio
    async def test_delete_memory_pending_returns_hard_delete_hint(self, tmp_path: Path) -> None:
        """Deleting a pending entry: hint indicates hard-delete, never committed."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="pending", scope_agents=[])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await delete_memory(ctx, entry_id=entry.id)

        assert "hint" in result, "delete_memory must return a 'hint' key"
        hint = result["hint"].lower()
        assert "hard" in hint or "never committed" in hint or "removed" in hint, (
            f"Hint for pending hard-delete should mention hard-delete, got: {result['hint']}"
        )

    @pytest.mark.asyncio
    async def test_delete_memory_curated_returns_soft_delete_hint(self, tmp_path: Path) -> None:
        """Deleting a curated entry: hint indicates soft-delete and file retention."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await delete_memory(ctx, entry_id=entry.id)

        assert "hint" in result, "delete_memory must return a 'hint' key"
        hint = result["hint"].lower()
        assert "soft" in hint or "retain" in hint or "audit" in hint, (
            f"Hint for curated soft-delete should mention soft-delete/retained, got: {result['hint']}"
        )

    @pytest.mark.asyncio
    async def test_delete_memory_approved_returns_soft_delete_hint(self, tmp_path: Path) -> None:
        """Deleting an approved entry: hint indicates soft-delete and file retention."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(
            n=1,
            state="approved",
            scope_agents=["builder"],
            approved_at="2026-05-01T10:00:01Z",
        )
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await delete_memory(ctx, entry_id=entry.id)

        assert "hint" in result, "delete_memory must return a 'hint' key"
        hint = result["hint"].lower()
        assert "soft" in hint or "retain" in hint or "audit" in hint, (
            f"Hint for approved soft-delete should mention soft-delete/retained, got: {result['hint']}"
        )

    @pytest.mark.asyncio
    async def test_delete_memory_pending_hint_must_contain_hard_keyword(self, tmp_path: Path) -> None:
        """Pending delete hint must contain the word 'hard' to discriminate from soft-delete.

        Refined AC6: 'hard' uniquely identifies the hard-delete branch. Accepting only
        'removed' or 'never committed' would allow a soft-delete hint to false-green
        if it happened to contain either word.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="pending", scope_agents=[])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await delete_memory(ctx, entry_id=entry.id)

        hint = result.get("hint", "")
        hint_lower = hint.lower()
        assert "hard" in hint_lower, (
            f"pending delete hint must contain 'hard' to identify hard-delete branch, got: {hint!r}"
        )

    @pytest.mark.asyncio
    async def test_delete_memory_curated_hint_must_contain_soft_keyword(self, tmp_path: Path) -> None:
        """Curated delete hint must contain the word 'soft' to discriminate from hard-delete.

        Refined AC6: 'soft' uniquely identifies the soft-delete branch. Accepting only
        'retain' or 'audit' would allow a hard-delete hint mentioning 'audit' to false-green.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await delete_memory(ctx, entry_id=entry.id)

        hint = result.get("hint", "")
        hint_lower = hint.lower()
        assert "soft" in hint_lower, (
            f"curated delete hint must contain 'soft' to identify soft-delete branch, got: {hint!r}"
        )


# ---------------------------------------------------------------------------
# AC7 (td:2): approve_memory only works on curated entries, errors on other states
# ---------------------------------------------------------------------------


class TestFromAC_ApproveMemory:
    """AC7: approve_memory only works on curated state; errors on all other states."""

    @pytest.mark.asyncio
    async def test_approve_memory_promotes_curated_to_approved(self, tmp_path: Path) -> None:
        """approve_memory sets state=approved on a curated entry."""
        try:
            from owlbear_mcp_memory.tools import approve_memory
        except ImportError as exc:
            pytest.fail(f"approve_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await approve_memory(ctx, entry_id=entry.id)

        assert result["state"] == "approved"

    @pytest.mark.asyncio
    async def test_approve_memory_sets_approved_at_timestamp(self, tmp_path: Path) -> None:
        """approve_memory sets approved_at when promoting to approved."""
        try:
            from owlbear_mcp_memory.tools import approve_memory
        except ImportError as exc:
            pytest.fail(f"approve_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        ctx = _make_ctx(engine)

        result = await approve_memory(ctx, entry_id=entry.id)

        assert result.get("approved_at") is not None, "approved_at must be set after approve_memory"

    @pytest.mark.asyncio
    async def test_approve_memory_raises_on_pending_entry(self, tmp_path: Path) -> None:
        """approve_memory raises ToolError when entry is in pending state."""
        try:
            from owlbear_mcp_memory.tools import approve_memory
        except ImportError as exc:
            pytest.fail(f"approve_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="pending", scope_agents=[])
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await approve_memory(ctx, entry_id=entry.id)

    @pytest.mark.asyncio
    async def test_approve_memory_raises_on_already_approved_entry(self, tmp_path: Path) -> None:
        """approve_memory raises ToolError when entry is already approved."""
        try:
            from owlbear_mcp_memory.tools import approve_memory
        except ImportError as exc:
            pytest.fail(f"approve_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(
            n=1,
            state="approved",
            scope_agents=["builder"],
            approved_at="2026-05-01T10:00:01Z",
        )
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await approve_memory(ctx, entry_id=entry.id)

    @pytest.mark.asyncio
    async def test_approve_memory_raises_on_deleted_entry(self, tmp_path: Path) -> None:
        """approve_memory raises ToolError when entry is in deleted state."""
        try:
            from owlbear_mcp_memory.tools import approve_memory
        except ImportError as exc:
            pytest.fail(f"approve_memory not importable from owlbear_mcp_memory.tools: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="deleted", scope_agents=[])
        engine.write(entry)
        ctx = _make_ctx(engine)

        with pytest.raises(ToolError):
            await approve_memory(ctx, entry_id=entry.id)


# ---------------------------------------------------------------------------
# AC8 (td:1): OWLBEAR_MEMORY_CALLER env var has no effect (access control removed)
# ---------------------------------------------------------------------------


class TestFromAC_CallerEnvVarNoEffect:
    """AC8: OWLBEAR_MEMORY_CALLER env var must not gate tool access.

    RED: curate_memory → update_entry calls _require_role(ctx, allowed={"curator"}).
    Passing caller="non-curator" causes ToolError before any assertion runs.
    """

    @pytest.mark.asyncio
    async def test_curate_memory_succeeds_with_any_caller_role(self, tmp_path: Path) -> None:
        """curate_memory must succeed regardless of ctx caller — no role check.

        RED: update_entry enforces _require_role({"curator"}). A ctx with
        caller="some-agent" raises ToolError currently — test fails because
        ToolError propagates unexpectedly.
        """
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)
        # caller is NOT "curator" — role-check would reject this
        ctx = _make_ctx(engine, caller="some-agent")

        # After access-control removal, this must NOT raise ToolError
        result = await curate_memory(ctx, entry_id=entry.id, title="Updated title")

        assert result["title"] == "Updated title"

    @pytest.mark.asyncio
    async def test_owlbear_memory_caller_env_var_does_not_gate_tool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Setting OWLBEAR_MEMORY_CALLER env var does not prevent tool execution.

        Refined AC8: monkeypatch sets the env var to a non-curator value; ctx is
        created with that caller (mimicking what app_lifespan does at server.py:51);
        mutation tool must still succeed — env var has no gating effect.
        """
        import os

        monkeypatch.setenv("OWLBEAR_MEMORY_CALLER", "non-curator-role")
        # Mimic app_lifespan: caller = os.environ.get("OWLBEAR_MEMORY_CALLER", "unknown")
        env_caller = os.environ.get("OWLBEAR_MEMORY_CALLER", "unknown")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller=env_caller)

        entry = _make_entry(n=1, state="curated", scope_agents=["builder"])
        engine.write(entry)

        # Must succeed — OWLBEAR_MEMORY_CALLER does not gate tool execution
        result = await curate_memory(ctx, entry_id=entry.id, title="Updated")
        assert result["title"] == "Updated", (
            "curate_memory must succeed when OWLBEAR_MEMORY_CALLER is set to non-standard role"
        )


# ---------------------------------------------------------------------------
# AC9 (td:1): MEMORY_TOOLS_EXCLUDE env var has no effect (access control removed)
# ---------------------------------------------------------------------------


class TestFromAC_ToolExcludeEnvVarNoEffect:
    """AC9: MEMORY_TOOLS_EXCLUDE env var must not gate tool availability.

    RED: _apply_tool_exclusions currently exists and is called during app_lifespan
    to remove tools when the env var is set. After access-control removal the
    function is removed. The test asserts it no longer exists.
    """

    def test_apply_tool_exclusions_removed_from_server(self) -> None:
        """_apply_tool_exclusions must not exist in server module after refactor.

        RED: the function currently EXISTS in owlbear_mcp_memory.server.
        """
        import owlbear_mcp_memory.server as server_module

        assert not hasattr(server_module, "_apply_tool_exclusions"), (
            "_apply_tool_exclusions still present in server — MEMORY_TOOLS_EXCLUDE is still active"
        )

    def test_memory_tools_exclude_string_absent_from_server_source(self) -> None:
        """'MEMORY_TOOLS_EXCLUDE' string must not appear anywhere in server module source.

        Refined AC9: proves the env var hook is completely removed — not just the
        helper function, but all textual references including conditional logic.
        README documentation is excluded because inspect.getsource reads Python only.
        """
        import inspect

        import owlbear_mcp_memory.server as server_module

        source = inspect.getsource(server_module)
        assert "MEMORY_TOOLS_EXCLUDE" not in source, (
            "Server module still references 'MEMORY_TOOLS_EXCLUDE' — "
            "env var exclusion hook not fully removed from Python source"
        )


# ---------------------------------------------------------------------------
# AC10 (td:2): validation errors return teaching messages (Brief guidance table)
# ---------------------------------------------------------------------------


class TestFromAC_ValidationTeachingMessages:
    """AC10: validation ToolErrors from save_memory must contain Brief teaching messages.

    RED: save_memory does not exist → ImportError (converted to pytest.fail).
    After save_memory exists but before teaching messages are implemented, the
    assertions about message content will fail (raw Pydantic text, not teaching).
    """

    @pytest.mark.asyncio
    async def test_save_memory_missing_categories_teaching_message(self, tmp_path: Path) -> None:
        """save_memory with empty categories raises ToolError with teaching message.

        Brief says: 'Provide at least one category from: {list}'
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        with pytest.raises(ToolError) as exc_info:
            await save_memory(
                ctx,
                title="Test",
                content="Content",
                categories=[],
                confidence=0.85,
                source_agent="builder",
            )

        error_text = str(exc_info.value).lower()
        assert "provide" in error_text, (
            f"Expected teaching message with 'provide' (Brief keyword), got: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_save_memory_content_too_long_teaching_message(self, tmp_path: Path) -> None:
        """save_memory with content >1024 chars raises ToolError with teaching message.

        Brief says: 'Content exceeds 1024-character limit. Split into focused entries.'
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        with pytest.raises(ToolError) as exc_info:
            await save_memory(
                ctx,
                title="Test",
                content="x" * 1025,
                categories=["domain-knowledge"],
                confidence=0.85,
                source_agent="builder",
            )

        error_text = str(exc_info.value).lower()
        assert "1024" in error_text or "limit" in error_text or "exceed" in error_text, (
            f"Expected teaching message about 1024-char limit, got: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_save_memory_confidence_out_of_range_teaching_message(self, tmp_path: Path) -> None:
        """save_memory with confidence outside [0.7, 1.0] raises ToolError with teaching message.

        Brief says: 'Confidence must be between 0.7 and 1.0'
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        with pytest.raises(ToolError) as exc_info:
            await save_memory(
                ctx,
                title="Test",
                content="Content",
                categories=["domain-knowledge"],
                confidence=0.5,
                source_agent="builder",
            )

        error_text = str(exc_info.value).lower()
        assert "confidence" in error_text or "0.7" in error_text, (
            f"Expected teaching message about confidence range, got: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_save_memory_blank_title_error_contains_non_empty_keyword(self, tmp_path: Path) -> None:
        """save_memory blank title error contains 'non-empty' (Brief-specified keyword).

        Refined AC10: 'non-empty' uniquely identifies the Brief teaching message;
        generic Pydantic output says 'should have at least 1 character' — no 'non-empty'.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        with pytest.raises(ToolError) as exc_info:
            await save_memory(
                ctx,
                title="",
                content="Content",
                categories=["domain-knowledge"],
                confidence=0.85,
                source_agent="builder",
            )

        assert "non-empty" in str(exc_info.value).lower(), (
            f"Title error must contain 'non-empty' (Brief keyword), got: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_save_memory_oversized_content_error_contains_split_keyword(self, tmp_path: Path) -> None:
        """save_memory oversized content error contains 'split' (Brief-specified keyword).

        Refined AC10: 'split' uniquely identifies the Brief teaching message;
        generic Pydantic output says 'String should have at most 1024 characters' — no 'split'.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        with pytest.raises(ToolError) as exc_info:
            await save_memory(
                ctx,
                title="Test",
                content="x" * 1025,
                categories=["domain-knowledge"],
                confidence=0.85,
                source_agent="builder",
            )

        assert "split" in str(exc_info.value).lower(), (
            f"Content error must contain 'split' (Brief keyword), got: {exc_info.value}"
        )

    @pytest.mark.asyncio
    async def test_save_memory_confidence_error_contains_between_keyword(self, tmp_path: Path) -> None:
        """save_memory confidence error contains 'between' (Brief-specified keyword).

        Refined AC10: 'between' uniquely identifies the Brief teaching message;
        generic Pydantic output says 'Input should be greater than or equal to 0.7' — no 'between'.
        """
        try:
            from owlbear_mcp_memory.tools import save_memory
        except ImportError as exc:
            pytest.fail(f"save_memory not importable: {exc}")

        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        with pytest.raises(ToolError) as exc_info:
            await save_memory(
                ctx,
                title="Test",
                content="Content",
                categories=["domain-knowledge"],
                confidence=0.5,
                source_agent="builder",
            )

        assert "between" in str(exc_info.value).lower(), (
            f"Confidence error must contain 'between' (Brief keyword), got: {exc_info.value}"
        )
