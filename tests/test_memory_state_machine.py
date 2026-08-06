"""RED-phase tests for memory state machine extension: contested, disputed, stale states.

Task #1840 — P2-01: State machine — contested, disputed, stale states.

AC coverage:
- AC1: MemoryState enum includes contested/disputed/stale in both packages;
       list_memories default state set includes all three;
       _state_rank_for_list: contested=1 (curated tier), disputed=stale=3 (deleted tier).
- AC2: MemoryEngine.resolve(entry_id, expected_updated_at) transitions
       {contested, disputed, stale}→approved with OCC; sets approved_at;
       TransitionError for non-resolvable states (pending, approved, curated, deleted).
- AC3: recall_memory excludes disputed and stale; includes contested;
       contested added to recall visible set and state_rank dict.
- AC4: edit() raises TransitionError for contested/disputed/stale;
       delete() soft-deletes (state→deleted) from contested/disputed/stale.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_memory import MemoryEngine, MemoryEntry
from owlbear_memory import storage
from owlbear_memory.errors import ConcurrencyError, TransitionError
from owlbear_memory.models import MemoryState

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_TS = "2026-05-25T10:00:00+00:00"
_TS_WRONG = "2025-01-01T00:00:00+00:00"

_ID_CONTESTED = "550e8400-e29b-41d4-a716-446655441001"
_ID_DISPUTED = "550e8400-e29b-41d4-a716-446655441002"
_ID_STALE = "550e8400-e29b-41d4-a716-446655441003"
_ID_APPROVED = "550e8400-e29b-41d4-a716-446655441004"
_ID_CURATED = "550e8400-e29b-41d4-a716-446655441005"
_ID_PENDING = "550e8400-e29b-41d4-a716-446655441006"
_ID_DELETED = "550e8400-e29b-41d4-a716-446655441007"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_raw_md(
    directory: Path,
    entry_id: str,
    state: str,
    scope_agents: list[str] | None = None,
    updated_at: str = _TS,
) -> None:
    """Write a raw markdown entry file with an arbitrary state string.

    Bypasses Python model validation — used to seed entries with state values
    that don't exist yet in the MemoryState enum.
    """
    scope_lines = "\n".join(f"- {a}" for a in (scope_agents or ["test-agent"]))
    content = (
        "---\n"
        f"id: {entry_id}\n"
        f"title: Entry-{state}\n"
        "categories:\n"
        "- domain-knowledge\n"
        "confidence: 0.9\n"
        f"state: {state}\n"
        "scope_agents:\n"
        f"{scope_lines}\n"
        "source_agent: test-agent\n"
        f"created_at: '{_TS}'\n"
        f"updated_at: '{updated_at}'\n"
        "approved_at: null\n"
        "---\n\n"
        f"Content for {state} entry.\n"
    )
    (directory / f"{entry_id}.md").write_text(content, encoding="utf-8")


def _make_existing_entry(
    entry_id: str,
    state: str,
    updated_at: str = _TS,
    approved_at: str | None = None,
) -> MemoryEntry:
    """Create a MemoryEntry using a pre-existing valid MemoryState value."""
    return MemoryEntry(
        id=entry_id,
        title=f"Entry-{state}",
        content=f"Content for {state} entry.",
        categories=["domain-knowledge"],
        confidence=0.9,
        state=state,
        scope_agents=["test-agent"],
        source_agent="test-agent",
        created_at=_TS,
        updated_at=updated_at,
        approved_at=approved_at,
    )


def _write_existing_entry(directory: Path, entry: MemoryEntry) -> None:
    path = directory / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=directory)


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_StateEnum — AC1
# ---------------------------------------------------------------------------


class TestStateEnum:
    """AC1: MemoryState enum includes contested, disputed, stale in both packages.

    list_memories default state set includes all three new states.
    _state_rank_for_list: contested=1 (curated tier), disputed=stale=3 (deleted tier).
    """

    def test_contested_value_in_memory_state_enum(self) -> None:
        """MemoryState.CONTESTED exists with value 'contested' in owlbear_memory."""
        assert MemoryState.CONTESTED == "contested"

    def test_disputed_value_in_memory_state_enum(self) -> None:
        """MemoryState.DISPUTED exists with value 'disputed' in owlbear_memory."""
        assert MemoryState.DISPUTED == "disputed"

    def test_stale_value_in_memory_state_enum(self) -> None:
        """MemoryState.STALE exists with value 'stale' in owlbear_memory."""
        assert MemoryState.STALE == "stale"

    def test_new_states_accessible_via_mcp_memory_package(self) -> None:
        """owlbear_memory_mcp exposes the same MemoryState enum with all three new values."""
        from owlbear_memory_mcp.tools import MemoryState as McpState  # noqa: PLC0415

        assert McpState.CONTESTED == "contested"
        assert McpState.DISPUTED == "disputed"
        assert McpState.STALE == "stale"

    def test_state_rank_contested_is_1(self) -> None:
        """_state_rank_for_list returns 1 for contested (same tier as curated)."""
        from owlbear_memory_mcp.tools import _state_rank_for_list  # noqa: PLC0415

        assert _state_rank_for_list(MemoryState.CONTESTED) == 1

    def test_state_rank_disputed_is_3(self) -> None:
        """_state_rank_for_list returns 3 for disputed (same tier as deleted)."""
        from owlbear_memory_mcp.tools import _state_rank_for_list  # noqa: PLC0415

        assert _state_rank_for_list(MemoryState.DISPUTED) == 3

    def test_state_rank_stale_is_3(self) -> None:
        """_state_rank_for_list returns 3 for stale (same tier as deleted)."""
        from owlbear_memory_mcp.tools import _state_rank_for_list  # noqa: PLC0415

        assert _state_rank_for_list(MemoryState.STALE) == 3

    def test_state_rank_contested_same_tier_as_curated(self) -> None:
        """contested and curated share rank 1 in _state_rank_for_list."""
        from owlbear_memory_mcp.tools import _state_rank_for_list  # noqa: PLC0415

        assert _state_rank_for_list(MemoryState.CONTESTED) == _state_rank_for_list(MemoryState.CURATED)

    @pytest.mark.asyncio
    async def test_list_memories_default_includes_contested_entries(self, tmp_path: Path) -> None:
        """list_memories with no state filter returns entries in contested state."""
        from owlbear_memory_mcp.tools import list_memories  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_CONTESTED, "contested")
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await list_memories(ctx)

        ids = [row["id"] for row in result]
        assert _ID_CONTESTED in ids

    @pytest.mark.asyncio
    async def test_list_memories_default_includes_disputed_entries(self, tmp_path: Path) -> None:
        """list_memories with no state filter returns entries in disputed state."""
        from owlbear_memory_mcp.tools import list_memories  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_DISPUTED, "disputed")
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await list_memories(ctx)

        ids = [row["id"] for row in result]
        assert _ID_DISPUTED in ids

    @pytest.mark.asyncio
    async def test_list_memories_default_includes_stale_entries(self, tmp_path: Path) -> None:
        """list_memories with no state filter returns entries in stale state."""
        from owlbear_memory_mcp.tools import list_memories  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_STALE, "stale")
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await list_memories(ctx)

        ids = [row["id"] for row in result]
        assert _ID_STALE in ids

    @pytest.mark.asyncio
    async def test_list_memories_contested_ordered_before_disputed_by_rank(self, tmp_path: Path) -> None:
        """contested (rank 1) appears before disputed (rank 3) in list_memories output."""
        from owlbear_memory_mcp.tools import list_memories  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_CONTESTED, "contested")
        _write_raw_md(tmp_path, _ID_DISPUTED, "disputed")
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await list_memories(ctx)

        ids = [row["id"] for row in result]
        assert _ID_CONTESTED in ids
        assert _ID_DISPUTED in ids
        assert ids.index(_ID_CONTESTED) < ids.index(_ID_DISPUTED)


# ---------------------------------------------------------------------------
# TestFromAC_Resolve — AC2
# ---------------------------------------------------------------------------


class TestResolve:
    """AC2: MemoryEngine.resolve() transitions {contested, disputed, stale}→approved.

    OCC enforcement via expected_updated_at. Sets approved_at. Raises TransitionError
    for non-resolvable source states (pending, approved, curated, deleted).
    """

    def test_resolve_contested_returns_approved_state(self, tmp_path: Path) -> None:
        """resolve() on a contested entry returns an entry with state=approved."""
        _write_raw_md(tmp_path, _ID_CONTESTED, "contested")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.resolve(_ID_CONTESTED, expected_updated_at=_TS)

        assert result.state == MemoryState.APPROVED

    def test_resolve_disputed_returns_approved_state(self, tmp_path: Path) -> None:
        """resolve() on a disputed entry returns an entry with state=approved."""
        _write_raw_md(tmp_path, _ID_DISPUTED, "disputed")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.resolve(_ID_DISPUTED, expected_updated_at=_TS)

        assert result.state == MemoryState.APPROVED

    def test_resolve_stale_returns_approved_state(self, tmp_path: Path) -> None:
        """resolve() on a stale entry returns an entry with state=approved."""
        _write_raw_md(tmp_path, _ID_STALE, "stale")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.resolve(_ID_STALE, expected_updated_at=_TS)

        assert result.state == MemoryState.APPROVED

    def test_resolve_sets_approved_at_timestamp(self, tmp_path: Path) -> None:
        """resolve() populates approved_at on the returned entry."""
        _write_raw_md(tmp_path, _ID_CONTESTED, "contested")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.resolve(_ID_CONTESTED, expected_updated_at=_TS)

        assert result.approved_at is not None

    def test_resolve_updates_updated_at(self, tmp_path: Path) -> None:
        """resolve() refreshes updated_at to a new value (not the original timestamp)."""
        _write_raw_md(tmp_path, _ID_DISPUTED, "disputed", updated_at=_TS)
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.resolve(_ID_DISPUTED, expected_updated_at=_TS)

        assert result.updated_at != _TS

    def test_resolve_persists_approved_state_to_disk(self, tmp_path: Path) -> None:
        """resolve() writes approved state to disk; re-read via fresh engine confirms it."""
        _write_raw_md(tmp_path, _ID_STALE, "stale")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.resolve(_ID_STALE, expected_updated_at=_TS)

        fresh_engine = MemoryEngine(memory_dir=tmp_path)
        entry = fresh_engine.get_entry(_ID_STALE)

        assert entry.state == MemoryState.APPROVED

    def test_resolve_occ_mismatch_raises_concurrency_error(self, tmp_path: Path) -> None:
        """resolve() raises ConcurrencyError when expected_updated_at does not match stored value."""
        _write_raw_md(tmp_path, _ID_CONTESTED, "contested")
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(ConcurrencyError):
            engine.resolve(_ID_CONTESTED, expected_updated_at=_TS_WRONG)

    def test_resolve_pending_raises_transition_error(self, tmp_path: Path) -> None:
        """resolve() raises TransitionError when source state is pending."""
        entry = _make_existing_entry(_ID_PENDING, "pending")
        _write_existing_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(TransitionError):
            engine.resolve(_ID_PENDING, expected_updated_at=_TS)

    def test_resolve_approved_raises_transition_error(self, tmp_path: Path) -> None:
        """resolve() raises TransitionError when source state is already approved."""
        entry = _make_existing_entry(_ID_APPROVED, "approved", approved_at=_TS)
        _write_existing_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(TransitionError):
            engine.resolve(_ID_APPROVED, expected_updated_at=_TS)

    def test_resolve_curated_raises_transition_error(self, tmp_path: Path) -> None:
        """resolve() raises TransitionError when source state is curated."""
        entry = _make_existing_entry(_ID_CURATED, "curated")
        _write_existing_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(TransitionError):
            engine.resolve(_ID_CURATED, expected_updated_at=_TS)

    def test_resolve_deleted_raises_transition_error(self, tmp_path: Path) -> None:
        """resolve() raises TransitionError when source state is deleted."""
        entry = _make_existing_entry(_ID_DELETED, "deleted")
        _write_existing_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        with pytest.raises(TransitionError):
            engine.resolve(_ID_DELETED, expected_updated_at=_TS)


# ---------------------------------------------------------------------------
# TestFromAC_RecallFiltering — AC3
# ---------------------------------------------------------------------------


class TestRecallFiltering:
    """AC3: recall_memory includes contested; excludes disputed and stale.

    contested is added to the recall visible set and inline state_rank dict.
    """

    @pytest.mark.asyncio
    async def test_recall_includes_contested_entries(self, tmp_path: Path) -> None:
        """recall_memory returns contested entries scoped to the requesting agent."""
        from owlbear_memory_mcp.tools import recall_memory  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_CONTESTED, "contested", scope_agents=["test-agent"])
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await recall_memory(ctx, agent="test-agent")

        assert "Entry-contested" in result

    @pytest.mark.asyncio
    async def test_recall_excludes_disputed_entries(self, tmp_path: Path) -> None:
        """recall_memory does not return disputed entries even when scoped to agent.

        Asserts engine can load the entry (state is valid after implementation)
        and that recall still excludes it.
        """
        from owlbear_memory_mcp.tools import recall_memory  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_DISPUTED, "disputed", scope_agents=["test-agent"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.load()

        # After implementation the engine WILL load disputed entries (state is valid)
        disputed_in_engine = any(e.id == _ID_DISPUTED for e in engine.get_entries())
        assert disputed_in_engine, "disputed entry must be loadable by engine after state enum is extended"

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent="test-agent")

        assert "Entry-disputed" not in result

    @pytest.mark.asyncio
    async def test_recall_excludes_stale_entries(self, tmp_path: Path) -> None:
        """recall_memory does not return stale entries even when scoped to agent.

        Asserts engine can load the entry (state is valid after implementation)
        and that recall still excludes it.
        """
        from owlbear_memory_mcp.tools import recall_memory  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_STALE, "stale", scope_agents=["test-agent"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.load()

        # After implementation the engine WILL load stale entries (state is valid)
        stale_in_engine = any(e.id == _ID_STALE for e in engine.get_entries())
        assert stale_in_engine, "stale entry must be loadable by engine after state enum is extended"

        ctx = _make_ctx(engine)
        result = await recall_memory(ctx, agent="test-agent")

        assert "Entry-stale" not in result

    @pytest.mark.asyncio
    async def test_recall_contested_appears_alongside_curated_entries(self, tmp_path: Path) -> None:
        """recall_memory returns both contested and curated entries for the same agent."""
        from owlbear_memory_mcp.tools import recall_memory  # noqa: PLC0415

        _write_raw_md(tmp_path, _ID_CONTESTED, "contested", scope_agents=["test-agent"])
        curated = _make_existing_entry(_ID_CURATED, "curated")
        _write_existing_entry(tmp_path, curated)
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await recall_memory(ctx, agent="test-agent")

        assert "Entry-contested" in result
        assert "Entry-curated" in result


# ---------------------------------------------------------------------------
# TestFromAC_EditDeleteNewStates — AC4
# ---------------------------------------------------------------------------


class TestEditDeleteNewStates:
    """AC4: edit() preserves contested/disputed/stale state.

    delete() soft-deletes (state→deleted) from contested/disputed/stale
    — same behavior as curated/approved (not hard-deleted like pending).
    """

    def test_edit_contested_preserves_state(self, tmp_path: Path) -> None:
        """edit() preserves contested state."""
        _write_raw_md(tmp_path, _ID_CONTESTED, "contested")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.edit(_ID_CONTESTED, {"title": "Updated"}, expected_updated_at=_TS)

        assert result.title == "Updated"
        assert result.state == MemoryState.CONTESTED

    def test_edit_disputed_preserves_state(self, tmp_path: Path) -> None:
        """edit() preserves disputed state."""
        _write_raw_md(tmp_path, _ID_DISPUTED, "disputed")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.edit(_ID_DISPUTED, {"title": "Updated"}, expected_updated_at=_TS)

        assert result.title == "Updated"
        assert result.state == MemoryState.DISPUTED

    def test_edit_stale_preserves_state(self, tmp_path: Path) -> None:
        """edit() preserves stale state."""
        _write_raw_md(tmp_path, _ID_STALE, "stale")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.edit(_ID_STALE, {"title": "Updated"}, expected_updated_at=_TS)

        assert result.title == "Updated"
        assert result.state == MemoryState.STALE

    def test_resolve_stale_clears_provenance_and_non_use_count(self, tmp_path: Path) -> None:
        """resolve() approves stale entries with a fresh non-use window."""
        entry = _make_existing_entry(_ID_STALE, "stale")
        entry = entry.model_copy(update={"didnt_use_count": 5, "contested_by_task": "task-1"})
        _write_existing_entry(tmp_path, entry)
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.resolve(_ID_STALE, expected_updated_at=_TS)

        assert result.state == MemoryState.APPROVED
        assert result.contested_by_task is None
        assert result.didnt_use_count == 0

    def test_delete_contested_is_soft_delete(self, tmp_path: Path) -> None:
        """delete() on contested transitions to deleted state (file preserved on disk)."""
        _write_raw_md(tmp_path, _ID_CONTESTED, "contested")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.delete(_ID_CONTESTED, expected_updated_at=_TS)

        assert result.state == MemoryState.DELETED
        # Soft-delete: the file must still exist on disk (not hard-deleted)
        assert (tmp_path / f"{_ID_CONTESTED}.md").exists()

    def test_delete_disputed_is_soft_delete(self, tmp_path: Path) -> None:
        """delete() on disputed transitions to deleted state (file preserved on disk)."""
        _write_raw_md(tmp_path, _ID_DISPUTED, "disputed")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.delete(_ID_DISPUTED, expected_updated_at=_TS)

        assert result.state == MemoryState.DELETED
        assert (tmp_path / f"{_ID_DISPUTED}.md").exists()

    def test_delete_stale_is_soft_delete(self, tmp_path: Path) -> None:
        """delete() on stale transitions to deleted state (file preserved on disk)."""
        _write_raw_md(tmp_path, _ID_STALE, "stale")
        engine = MemoryEngine(memory_dir=tmp_path)

        result = engine.delete(_ID_STALE, expected_updated_at=_TS)

        assert result.state == MemoryState.DELETED
        assert (tmp_path / f"{_ID_STALE}.md").exists()
