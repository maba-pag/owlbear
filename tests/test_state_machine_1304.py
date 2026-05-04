"""Failing tests for #1304: State machine transitions, auto-promote,
auto-downgrade, scope gate, and deletion semantics.

AC coverage:
  AC1 (td:2): pending -> curated when curate_memory provides scope_agents (auto-promote)
  AC2 (td:2): pending curate rejected atomically when scope_agents missing (scope gate)
  AC3 (td:1): curated -> curated on any field edit (stays curated)
  AC4 (td:2): approved -> curated on any curate_memory call (auto-downgrade)
  AC5 (td:2): approved_at set on approve, cleared on downgrade
  AC6 (td:2): pending -> hard-delete (file removed from disk)
  AC7 (td:2): curated/approved -> soft-delete (file retained, state=deleted)
  AC8 (td:2): deleted is terminal (no transitions out, operations rejected)
  AC9 (td:2): invalid transitions rejected (pending->approved directly, deleted->any)
  AC10 (td:0): test suite fails — RED state; each AC class has at least one FAIL

Interface strategy (Option D from research):
  Tests import existing update_entry/delete_entry/approve_entry from tools and
  assert NEW behaviors defined in the brief. RED because:
    - update_entry on approved raises ToolError (AC4/AC5 fail)
    - No scope gate exists (AC2 fails)
    - No auto-promote on scope_agents (AC1 fails)
    - delete_entry always soft-deletes (AC6 fails)
    - delete_entry is idempotent on deleted (AC8 fails)
    - No terminal enforcement on update for deleted (AC8/AC9 fail)

  AC3 and AC7 tests target new function names (curate_memory, delete_memory)
  that do not exist yet — ImportError guarantees RED for those classes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.models import MemoryCategory, MemoryEntry, MemoryState
from owlbear_mcp_memory.tools import approve_entry, delete_entry, query_memory, store_learning, update_entry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid(n: int) -> str:
    return f"550e8400-e29b-41d4-a716-4466554{n:05d}"


_TS = "2026-05-01T10:00:00Z"


def _make_entry(**overrides: object) -> MemoryEntry:
    """Return a valid new-schema MemoryEntry (source_agent, approved_at present)."""
    defaults: dict[str, object] = {
        "id": _uuid(1),
        "title": "Test entry",
        "categories": ["domain-knowledge"],
        "confidence": 0.85,
        "state": "pending",
        "content": "Entry body text.",
        "scope_agents": [],
        "source_agent": "builder",
        "created_at": _TS,
        "updated_at": _TS,
        "approved_at": None,
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


def _make_ctx(engine: MemoryEngine, caller: str = "curator") -> MagicMock:
    """Return a mock MCP context with engine and caller role wired up."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    ctx.request_context.lifespan_context.caller = caller
    return ctx


# ---------------------------------------------------------------------------
# AC1 (td:2): Auto-promote — pending -> curated when scope_agents provided
#
# Current failure: update_entry has no auto-promote logic. Providing scope_agents
# does not change state — entry stays pending. Both tests fail on state assertion.
# ---------------------------------------------------------------------------


class TestFromAC_AutoPromote:
    """AC1: curate_memory with scope_agents promotes pending entry to curated."""

    @pytest.mark.asyncio
    async def test_pending_promotes_to_curated_when_scope_agents_provided(
        self, tmp_path: Path
    ) -> None:
        """Providing scope_agents on a pending entry triggers auto-promote to curated.

        Current failure: update_entry does not auto-promote based on scope_agents
        presence. The entry stays pending regardless. result["state"] == "curated"
        fails because result["state"] is "pending".
        """
        entry = _make_entry(state="pending", scope_agents=[])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await update_entry(ctx, entry_id=entry.id, scope_agents=["builder"])

        assert result["state"] == "curated"

    @pytest.mark.asyncio
    async def test_auto_promote_entry_retains_provided_scope_agents(
        self, tmp_path: Path
    ) -> None:
        """After auto-promote, scope_agents and state=curated must both be present.

        Current failure: state stays pending (not curated), so the combined
        assertion on state fails even though scope_agents is correctly stored.
        """
        entry = _make_entry(state="pending", scope_agents=[])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await update_entry(
            ctx, entry_id=entry.id, scope_agents=["builder", "reviewer"]
        )

        assert result["state"] == "curated"
        assert set(result["scope_agents"]) == {"builder", "reviewer"}

    @pytest.mark.asyncio
    async def test_curate_memory_pending_promotes_to_curated_when_scope_agents_provided(
        self, tmp_path: Path
    ) -> None:
        """curate_memory (public alias) with scope_agents promotes pending to curated."""
        from owlbear_mcp_memory.tools import curate_memory

        entry = _make_entry(state="pending", scope_agents=[])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await curate_memory(ctx, entry_id=entry.id, scope_agents=["builder"])

        assert result["state"] == "curated"

    @pytest.mark.asyncio
    async def test_curate_memory_auto_promote_retains_scope_agents(
        self, tmp_path: Path
    ) -> None:
        """curate_memory auto-promote sets state=curated and retains scope_agents."""
        from owlbear_mcp_memory.tools import curate_memory

        entry = _make_entry(state="pending", scope_agents=[])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await curate_memory(
            ctx, entry_id=entry.id, scope_agents=["builder", "reviewer"]
        )

        assert result["state"] == "curated"
        assert set(result["scope_agents"]) == {"builder", "reviewer"}


# ---------------------------------------------------------------------------
# AC2 (td:2): Scope gate — pending curate rejected atomically when scope_agents missing
#
# Current failure: update_entry has no scope gate validation. Calling without
# scope_agents on a pending entry silently succeeds (updates updated_at and
# writes the entry back). No ToolError is raised.
# ---------------------------------------------------------------------------


class TestFromAC_ScopeGate:
    """AC2: curate_memory on pending without scope_agents raises ToolError (scope gate)."""

    @pytest.mark.asyncio
    async def test_curate_pending_without_scope_agents_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry on pending without scope_agents must raise ToolError.

        Current failure: no scope gate exists. Call succeeds silently.
        pytest.raises(ToolError) block is never entered → test fails.
        """
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="scope_agents"):
            await update_entry(ctx, entry_id=entry.id, title="Updated title")

    @pytest.mark.asyncio
    async def test_curate_pending_scope_gate_leaves_entry_unchanged_on_disk(
        self, tmp_path: Path
    ) -> None:
        """After scope gate rejection, entry on disk must be unchanged (atomicity).

        Current failure: no ToolError raised → pytest.raises block fails before
        the atomicity assertion is ever reached.
        """
        original_title = "Original title"
        entry = _make_entry(state="pending", title=original_title)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, title="Should not apply")

        # After rejected update, title and state must be unchanged
        loaded = engine.get_entry(entry.id)
        assert loaded.title == original_title
        assert loaded.state == MemoryState.PENDING

    @pytest.mark.asyncio
    async def test_curate_pending_scope_gate_updated_at_unchanged(
        self, tmp_path: Path
    ) -> None:
        """After scope gate rejection, updated_at must be unchanged (true atomicity).

        Proves no write reached disk — updated_at would be bumped by any write path.
        """
        entry = _make_entry(state="pending", title="Atomic check", updated_at=_TS)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, title="Should not apply")

        loaded = engine.get_entry(entry.id)
        assert loaded.updated_at == _TS
        assert loaded.state == MemoryState.PENDING
        assert loaded.title == "Atomic check"


# ---------------------------------------------------------------------------
# AC3 (td:1): Curated stays curated on any field edit
#
# Current failure: tests use curate_memory (new function name from brief D108)
# which does not yet exist in tools.py. ImportError guarantees RED for this class.
# In GREEN: curate_memory is implemented; tests verify curated -> curated behavior.
# ---------------------------------------------------------------------------


class TestFromAC_CuratedStaysCurated:
    """AC3: curate_memory on curated entry returns state=curated (stays curated)."""

    @pytest.mark.asyncio
    async def test_edit_curated_title_stays_curated(self, tmp_path: Path) -> None:
        """curate_memory on curated entry with title change keeps state=curated.

        Current failure: ImportError — curate_memory not yet in tools.py.
        """
        from owlbear_mcp_memory.tools import curate_memory  # ImportError in RED

        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await curate_memory(ctx, entry_id=entry.id, title="Updated title")

        assert result["state"] == "curated"
        assert result["title"] == "Updated title"


# ---------------------------------------------------------------------------
# AC4 (td:2): Auto-downgrade — approved -> curated on any curate_memory call
#
# Current failure: update_entry raises ToolError when called on an approved entry
# ("update_entry cannot modify approved entries"). Tests expect auto-downgrade to
# curated (state=curated returned), not ToolError.
# ---------------------------------------------------------------------------


class TestFromAC_AutoDowngrade:
    """AC4: curate_memory on approved entry unconditionally downgrades to curated."""

    @pytest.mark.asyncio
    async def test_update_approved_entry_downgrades_to_curated(
        self, tmp_path: Path
    ) -> None:
        """update_entry on approved must return state=curated (auto-downgrade, D31).

        Current failure: raises ToolError("update_entry cannot modify approved entries").
        The test does NOT use pytest.raises, so the ToolError propagates and fails the
        test.
        """
        entry = _make_entry(
            state="approved",
            scope_agents=["builder"],
            approved_at=_TS,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await update_entry(ctx, entry_id=entry.id, title="Updated from approved")

        assert result["state"] == "curated"

    @pytest.mark.asyncio
    async def test_auto_downgrade_applies_field_update(
        self, tmp_path: Path
    ) -> None:
        """After auto-downgrade, the edited field is persisted alongside state=curated.

        Current failure: ToolError raised before the entry is modified at all.
        """
        entry = _make_entry(
            state="approved",
            scope_agents=["builder"],
            approved_at=_TS,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        new_title = "Post-downgrade title"
        result = await update_entry(ctx, entry_id=entry.id, title=new_title)

        assert result["state"] == "curated"
        assert result["title"] == new_title

    @pytest.mark.asyncio
    async def test_curate_memory_approved_downgrades_to_curated(
        self, tmp_path: Path
    ) -> None:
        """curate_memory (public alias) on approved entry downgrades to curated."""
        from owlbear_mcp_memory.tools import curate_memory

        entry = _make_entry(state="approved", scope_agents=["builder"], approved_at=_TS)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await curate_memory(ctx, entry_id=entry.id, title="Via curate_memory")

        assert result["state"] == "curated"

    @pytest.mark.asyncio
    async def test_curate_memory_auto_downgrade_clears_approved_at(
        self, tmp_path: Path
    ) -> None:
        """curate_memory on approved entry clears approved_at on downgrade."""
        from owlbear_mcp_memory.tools import curate_memory

        entry = _make_entry(state="approved", scope_agents=["builder"], approved_at=_TS)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await curate_memory(ctx, entry_id=entry.id)

        assert result["state"] == "curated"
        assert result["approved_at"] is None


# ---------------------------------------------------------------------------
# AC5 (td:2): approved_at lifecycle — set on approve, cleared on downgrade
#
# Current failure:
#   test 1 (approve sets approved_at): PASSES in current code — approve_entry
#     already sets approved_at. Included as regression guard.
#   test 2 (downgrade clears approved_at): update_entry on approved raises
#     ToolError. No downgrade path exists to clear approved_at.
# ---------------------------------------------------------------------------


class TestFromAC_ApprovedAtLifecycle:
    """AC5: approved_at is set when approving and cleared when downgrading."""

    @pytest.mark.asyncio
    async def test_approve_sets_approved_at(self, tmp_path: Path) -> None:
        """approve_entry on curated sets approved_at to a non-None timestamp.

        This regression guard passes in current code (approve_entry already sets
        approved_at). Paired with the downgrade test which FAILS in RED.
        """
        entry = _make_entry(state="curated", scope_agents=["builder"], approved_at=None)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        result = await approve_entry(ctx, entry_id=entry.id)

        assert result["approved_at"] is not None
        assert result["state"] == "approved"

    @pytest.mark.asyncio
    async def test_downgrade_clears_approved_at(self, tmp_path: Path) -> None:
        """update_entry on approved entry must return approved_at=None after downgrade.

        Current failure: ToolError raised ("cannot modify approved entries").
        approved_at cannot be cleared because no downgrade path exists.
        """
        entry = _make_entry(
            state="approved",
            scope_agents=["builder"],
            approved_at=_TS,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await update_entry(ctx, entry_id=entry.id, title="Post-downgrade")

        assert result["state"] == "curated"
        assert result["approved_at"] is None


# ---------------------------------------------------------------------------
# AC6 (td:2): Hard-delete pending — file removed from disk
#
# Current failure: delete_entry always soft-deletes. The file is retained on disk
# with state=deleted. Tests assert file is absent → fail because file exists.
# ---------------------------------------------------------------------------


class TestFromAC_HardDeletePending:
    """AC6: delete_memory on pending entry removes the file from disk (hard-delete)."""

    @pytest.mark.asyncio
    async def test_delete_pending_removes_file_from_disk(
        self, tmp_path: Path
    ) -> None:
        """Deleting a pending entry must remove the file from disk entirely.

        Current failure: delete_entry soft-deletes → file IS present with
        state=deleted. The assertion that no .md files exist fails.
        """
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        await delete_entry(ctx, entry_id=entry.id)

        remaining_files = list(tmp_path.glob("*.md"))  # noqa: ASYNC240
        assert remaining_files == [], (
            f"Expected no files after hard-delete, found: {remaining_files}"
        )

    @pytest.mark.asyncio
    async def test_delete_pending_entry_absent_from_get_entries(
        self, tmp_path: Path
    ) -> None:
        """After hard-deleting a pending entry, get_entries must not return it.

        Current failure: soft-delete retains the file → get_entries includes
        the entry (with state=deleted) → assertion that entry is absent fails.
        """
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        await delete_entry(ctx, entry_id=entry.id)

        all_entries = engine.get_entries()
        ids = {e.id for e in all_entries}
        assert entry.id not in ids, (
            f"Hard-deleted pending entry still returned by get_entries"
        )


# ---------------------------------------------------------------------------
# AC7 (td:2): Soft-delete curated/approved — file retained, state=deleted
#
# Current failure: tests use delete_memory (new function name from brief D141)
# which does not yet exist in tools.py. ImportError guarantees RED for this class.
# In GREEN: delete_memory is implemented; tests verify soft-delete behavior.
# ---------------------------------------------------------------------------


class TestFromAC_SoftDeleteCuratedApproved:
    """AC7: delete_memory on curated/approved retains file on disk with state=deleted."""

    @pytest.mark.asyncio
    async def test_delete_curated_sets_state_deleted_file_retained(
        self, tmp_path: Path
    ) -> None:
        """delete_memory on curated sets state=deleted and keeps file on disk.

        Current failure: ImportError — delete_memory not yet in tools.py.
        """
        from owlbear_mcp_memory.tools import delete_memory  # ImportError in RED

        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await delete_memory(ctx, entry_id=entry.id)

        assert result["state"] == "deleted"
        remaining_files = list(tmp_path.glob("*.md"))  # noqa: ASYNC240
        assert len(remaining_files) == 1, "File must be retained after soft-delete"

    @pytest.mark.asyncio
    async def test_delete_approved_sets_state_deleted_file_retained(
        self, tmp_path: Path
    ) -> None:
        """delete_memory on approved sets state=deleted and keeps file on disk.

        Current failure: ImportError — delete_memory not yet in tools.py.
        """
        from owlbear_mcp_memory.tools import delete_memory  # ImportError in RED

        entry = _make_entry(
            state="approved", scope_agents=["builder"], approved_at=_TS
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await delete_memory(ctx, entry_id=entry.id)

        assert result["state"] == "deleted"
        remaining_files = list(tmp_path.glob("*.md"))  # noqa: ASYNC240
        assert len(remaining_files) == 1, "File must be retained after soft-delete"

    @pytest.mark.asyncio
    async def test_delete_curated_state_persisted_as_deleted_on_disk(
        self, tmp_path: Path
    ) -> None:
        """delete_memory on curated: reloading from disk proves state=deleted persisted."""
        from owlbear_mcp_memory.tools import delete_memory

        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        await delete_memory(ctx, entry_id=entry.id)

        # Reload all entries from disk — file was retained, state=deleted must be written
        all_entries = engine.get_entries()
        assert len(all_entries) == 1
        assert all_entries[0].state == MemoryState.DELETED

    @pytest.mark.asyncio
    async def test_delete_approved_state_persisted_as_deleted_on_disk(
        self, tmp_path: Path
    ) -> None:
        """delete_memory on approved: reloading from disk proves state=deleted persisted."""
        from owlbear_mcp_memory.tools import delete_memory

        entry = _make_entry(state="approved", scope_agents=["builder"], approved_at=_TS)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        await delete_memory(ctx, entry_id=entry.id)

        # Reload all entries from disk — file was retained, state=deleted must be written
        all_entries = engine.get_entries()
        assert len(all_entries) == 1
        assert all_entries[0].state == MemoryState.DELETED


# ---------------------------------------------------------------------------
# AC8 (td:2): Deleted is terminal — no transitions out, operations rejected
#
# Current failure:
#   update_entry on deleted: no terminal check. target_state=deleted (same),
#     _ensure_update_transition(DELETED, DELETED) returns early (current==target).
#     No ToolError is raised → test fails.
#   delete_entry on deleted: idempotent — returns current entry without error.
#     No ToolError is raised → test fails.
# ---------------------------------------------------------------------------


class TestFromAC_DeletedTerminal:
    """AC8: deleted state is terminal — all operations must raise ToolError."""

    @pytest.mark.asyncio
    async def test_update_deleted_entry_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry on a deleted entry must raise ToolError (terminal state).

        Current failure: no terminal-state check in update_entry. When no state
        param is provided, target_state=DELETED, _ensure_update_transition(DELETED,
        DELETED) returns early (current==target). Entry is rewritten without error.
        """
        entry = _make_entry(state="deleted")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, title="Should fail")

    @pytest.mark.asyncio
    async def test_delete_deleted_entry_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """delete_entry on an already-deleted entry must raise ToolError.

        Current failure: delete_entry is idempotent for deleted entries
        (early return: `if current.state == DELETED: return _entry_to_dict(current)`).
        No ToolError is raised.
        """
        entry = _make_entry(state="deleted")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await delete_entry(ctx, entry_id=entry.id)

    @pytest.mark.asyncio
    async def test_approve_deleted_entry_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """approve_entry on a deleted entry must raise ToolError (terminal state)."""
        entry = _make_entry(state="deleted")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError):
            await approve_entry(ctx, entry_id=entry.id)


# ---------------------------------------------------------------------------
# AC9 (td:2): Invalid transitions rejected
#
# Current failure:
#   pending -> approved (explicit): already rejected by _ensure_update_transition
#     (passes in current code — included as regression guard).
#   deleted -> any via field update (no explicit state param): NOT rejected in
#     current code. Terminal check missing → no ToolError raised.
# ---------------------------------------------------------------------------


class TestFromAC_InvalidTransitions:
    """AC9: invalid state transitions must raise ToolError."""

    @pytest.mark.asyncio
    async def test_pending_to_approved_directly_rejected(
        self, tmp_path: Path
    ) -> None:
        """update_entry(state=approved) on pending raises ToolError.

        This regression guard PASSES in current code (already rejected by
        _ensure_update_transition). Paired with the deleted->any test which FAILS.
        """
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(
                ctx, entry_id=entry.id, state=MemoryState.APPROVED
            )

    @pytest.mark.asyncio
    async def test_deleted_entry_cannot_be_updated_without_explicit_state(
        self, tmp_path: Path
    ) -> None:
        """update_entry on a deleted entry (no explicit state param) must raise ToolError.

        Current failure: when no state param is passed, target_state=DELETED (same
        as current). _ensure_update_transition(DELETED, DELETED) returns early
        because current==target. No ToolError is raised and the entry is rewritten
        without the terminal-state enforcement applying.
        """
        entry = _make_entry(state="deleted")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, title="Mutating deleted entry")

    @pytest.mark.asyncio
    async def test_deleted_to_approved_via_approve_entry_rejected(
        self, tmp_path: Path
    ) -> None:
        """approve_entry on a deleted entry raises ToolError (deleted->approved invalid)."""
        entry = _make_entry(state="deleted")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError):
            await approve_entry(ctx, entry_id=entry.id)


# ---------------------------------------------------------------------------
# Coverage: store_learning -- lines 108-127 of tools.py (never called by AC tests)
# ---------------------------------------------------------------------------


class TestFromAC_StoreLearning:
    """Coverage for store_learning: creates pending entries with caller as source_agent."""

    @pytest.mark.asyncio
    async def test_store_learning_returns_pending_state(self, tmp_path: Path) -> None:
        """store_learning creates a pending entry with correct fields."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        result = await store_learning(
            ctx,
            title="Test learning",
            content="Some content.",
            categories=[MemoryCategory.DOMAIN_KNOWLEDGE],
            confidence=0.9,
        )

        assert result["state"] == "pending"
        assert result["title"] == "Test learning"
        assert result["source_agent"] == "builder"
        assert result["approved_at"] is None

    @pytest.mark.asyncio
    async def test_store_learning_with_scope_agents_preserved(self, tmp_path: Path) -> None:
        """store_learning stores provided scope_agents on the new entry."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        result = await store_learning(
            ctx,
            title="Scoped entry",
            content="Scoped content.",
            categories=[MemoryCategory.PITFALL],
            confidence=0.8,
            scope_agents=["reviewer"],
        )

        assert result["scope_agents"] == ["reviewer"]

    @pytest.mark.asyncio
    async def test_store_learning_invalid_confidence_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """Confidence below 0.7 triggers ValidationError inside store_learning → ToolError."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        with pytest.raises(ToolError):
            await store_learning(
                ctx,
                title="Bad confidence",
                content="Content.",
                categories=[MemoryCategory.PITFALL],
                confidence=0.5,  # below ge=0.7 → MemoryEntry ValidationError
            )


# ---------------------------------------------------------------------------
# Coverage: query_memory -- lines 140-169 of tools.py (never called by AC tests)
# ---------------------------------------------------------------------------


class TestFromAC_QueryMemory:
    """Coverage for query_memory filtering branches."""

    @pytest.mark.asyncio
    async def test_query_memory_default_returns_curated_and_approved_only(
        self, tmp_path: Path
    ) -> None:
        """Default query (no filters) returns only curated and approved entries."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        pending = _make_entry(id=_uuid(1), state="pending")
        curated = _make_entry(id=_uuid(2), state="curated", scope_agents=["builder"])
        approved = _make_entry(
            id=_uuid(3), state="approved", scope_agents=["builder"], approved_at=_TS
        )
        for e in [pending, curated, approved]:
            engine.write(e)

        results = await query_memory(ctx)
        result_ids = {r["id"] for r in results}

        assert _uuid(2) in result_ids
        assert _uuid(3) in result_ids
        assert _uuid(1) not in result_ids  # pending excluded by default

    @pytest.mark.asyncio
    async def test_query_memory_with_explicit_states_filter(self, tmp_path: Path) -> None:
        """Explicit states=[PENDING] returns only pending entries."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        pending = _make_entry(id=_uuid(1), state="pending")
        curated = _make_entry(id=_uuid(2), state="curated", scope_agents=["builder"])
        engine.write(pending)
        engine.write(curated)

        results = await query_memory(ctx, states=[MemoryState.PENDING])
        result_ids = {r["id"] for r in results}

        assert _uuid(1) in result_ids
        assert _uuid(2) not in result_ids

    @pytest.mark.asyncio
    async def test_query_memory_with_category_filter(self, tmp_path: Path) -> None:
        """categories filter returns only entries with matching category."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        e1 = _make_entry(
            id=_uuid(1), state="curated", scope_agents=["builder"],
            categories=["domain-knowledge"],
        )
        e2 = _make_entry(
            id=_uuid(2), state="curated", scope_agents=["builder"],
            categories=["pitfall"],
        )
        engine.write(e1)
        engine.write(e2)

        results = await query_memory(ctx, categories=["pitfall"])
        result_ids = {r["id"] for r in results}

        assert _uuid(2) in result_ids
        assert _uuid(1) not in result_ids

    @pytest.mark.asyncio
    async def test_query_memory_with_scope_agents_filter(self, tmp_path: Path) -> None:
        """scope_agents filter returns only entries with matching agent."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        e1 = _make_entry(id=_uuid(1), state="curated", scope_agents=["builder"])
        e2 = _make_entry(id=_uuid(2), state="curated", scope_agents=["reviewer"])
        engine.write(e1)
        engine.write(e2)

        results = await query_memory(ctx, scope_agents=["builder"])
        result_ids = {r["id"] for r in results}

        assert _uuid(1) in result_ids
        assert _uuid(2) not in result_ids

    @pytest.mark.asyncio
    async def test_query_memory_with_min_confidence_filter(self, tmp_path: Path) -> None:
        """min_confidence filter excludes entries below the threshold."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        low = _make_entry(id=_uuid(1), state="curated", scope_agents=["builder"], confidence=0.75)
        high = _make_entry(id=_uuid(2), state="curated", scope_agents=["builder"], confidence=0.95)
        engine.write(low)
        engine.write(high)

        results = await query_memory(ctx, min_confidence=0.9)
        result_ids = {r["id"] for r in results}

        assert _uuid(2) in result_ids
        assert _uuid(1) not in result_ids

    @pytest.mark.asyncio
    async def test_query_memory_with_limit(self, tmp_path: Path) -> None:
        """limit=1 returns at most one entry even when more exist."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        for i in range(1, 4):
            engine.write(_make_entry(id=_uuid(i), state="curated", scope_agents=["builder"]))

        results = await query_memory(ctx, limit=1)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Coverage: _require_role rejection -- lines 47-52 of tools.py
# ---------------------------------------------------------------------------


class TestFromAC_RoleGating:
    """Coverage: _require_role raises ToolError when caller is not in allowed set."""

    @pytest.mark.asyncio
    async def test_update_entry_rejects_non_curator_caller(self, tmp_path: Path) -> None:
        """update_entry with caller='user' (requires 'curator') raises ToolError."""
        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError, match="curator"):
            await update_entry(ctx, entry_id=entry.id, title="Rejected")

    @pytest.mark.asyncio
    async def test_delete_entry_rejects_non_curator_caller(self, tmp_path: Path) -> None:
        """delete_entry with caller='user' (requires 'curator') raises ToolError."""
        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError, match="curator"):
            await delete_entry(ctx, entry_id=entry.id)

    @pytest.mark.asyncio
    async def test_approve_entry_rejects_non_user_caller(self, tmp_path: Path) -> None:
        """approve_entry with caller='curator' (requires 'user') raises ToolError."""
        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="user"):
            await approve_entry(ctx, entry_id=entry.id)


# ---------------------------------------------------------------------------
# Coverage: _load_entry_or_raise not-found -- lines 78-80 of tools.py
# ---------------------------------------------------------------------------


class TestFromAC_EntryNotFound:
    """Coverage: operations on non-existent IDs raise ToolError."""

    @pytest.mark.asyncio
    async def test_update_nonexistent_entry_raises_tool_error(self, tmp_path: Path) -> None:
        """update_entry on a non-existent ID raises ToolError with 'not found' message."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="not found"):
            await update_entry(ctx, entry_id=_uuid(99), title="Ghost entry")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry_raises_tool_error(self, tmp_path: Path) -> None:
        """delete_entry on a non-existent ID raises ToolError with 'not found' message."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="not found"):
            await delete_entry(ctx, entry_id=_uuid(99))

    @pytest.mark.asyncio
    async def test_approve_nonexistent_entry_raises_tool_error(self, tmp_path: Path) -> None:
        """approve_entry on a non-existent ID raises ToolError with 'not found' message."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError, match="not found"):
            await approve_entry(ctx, entry_id=_uuid(99))


# ---------------------------------------------------------------------------
# Coverage: approve_entry non-curated error -- lines 289-290 of tools.py
# ---------------------------------------------------------------------------


class TestFromAC_ApproveNonCurated:
    """Coverage: approve_entry requires curated state; other states raise ToolError."""

    @pytest.mark.asyncio
    async def test_approve_pending_entry_raises_tool_error(self, tmp_path: Path) -> None:
        """approve_entry on a pending entry raises ToolError (must be curated)."""
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError, match="curated"):
            await approve_entry(ctx, entry_id=entry.id)

    @pytest.mark.asyncio
    async def test_approve_already_approved_entry_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """approve_entry on an approved entry raises ToolError (must be curated)."""
        entry = _make_entry(state="approved", scope_agents=["builder"], approved_at=_TS)
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError, match="curated"):
            await approve_entry(ctx, entry_id=entry.id)


# ---------------------------------------------------------------------------
# Coverage: _ensure_update_transition invalid path -- lines 94-95 of tools.py
# ---------------------------------------------------------------------------


class TestFromAC_InvalidTransitionViaEnsure:
    """Coverage: _ensure_update_transition rejects invalid transitions not caught earlier."""

    @pytest.mark.asyncio
    async def test_update_curated_to_pending_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """CURATED→PENDING is invalid; _ensure_update_transition raises ToolError."""
        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="invalid state transition"):
            await update_entry(ctx, entry_id=entry.id, state=MemoryState.PENDING)


# ---------------------------------------------------------------------------
# Coverage: engine internals -- engine.py edge cases
# ---------------------------------------------------------------------------


class TestFromAC_EngineEdgeCases:
    """Coverage for engine._slugify, _load_file skip paths, and delete KeyError."""

    def test_write_with_all_special_char_title_uses_entry_slug(
        self, tmp_path: Path
    ) -> None:
        """Title with only special chars → _slugify returns 'entry' fallback (line 28)."""
        entry = _make_entry(title="!!! ???")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        # Must be retrievable via get_entry despite special-char slug
        loaded = engine.get_entry(entry.id)
        assert loaded.title == "!!! ???"

    def test_load_skips_file_without_frontmatter_delimiters(
        self, tmp_path: Path
    ) -> None:
        """File with no --- delimiters is silently skipped by _load_file."""
        bad = tmp_path / "no-frontmatter.md"
        bad.write_text("Just plain text, no frontmatter.\n", encoding="utf-8")
        engine = MemoryEngine(memory_dir=tmp_path)
        assert engine.load() == []

    def test_load_skips_file_with_invalid_yaml_frontmatter(
        self, tmp_path: Path
    ) -> None:
        """File with malformed YAML frontmatter is silently skipped."""
        bad = tmp_path / "bad-yaml.md"
        bad.write_text("---\n: broken: yaml: {\n---\n\nContent.\n", encoding="utf-8")
        engine = MemoryEngine(memory_dir=tmp_path)
        assert engine.load() == []

    def test_load_skips_file_with_non_dict_frontmatter(self, tmp_path: Path) -> None:
        """File with scalar YAML frontmatter (not a dict) is silently skipped."""
        bad = tmp_path / "non-dict.md"
        bad.write_text("---\njust a scalar string\n---\n\nContent.\n", encoding="utf-8")
        engine = MemoryEngine(memory_dir=tmp_path)
        assert engine.load() == []

    def test_load_skips_file_with_invalid_entry_schema(self, tmp_path: Path) -> None:
        """Valid YAML dict but missing required fields → ValidationError → skipped."""
        bad = tmp_path / "missing-fields.md"
        bad.write_text(
            "---\ntitle: Only Title\nstate: pending\n---\n\nContent.\n",
            encoding="utf-8",
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        assert engine.load() == []

    def test_engine_delete_missing_entry_raises_key_error(self, tmp_path: Path) -> None:
        """engine.delete() on a non-existent ID raises KeyError."""
        engine = MemoryEngine(memory_dir=tmp_path)
        with pytest.raises(KeyError):
            engine.delete("nonexistent-id")

    def test_engine_get_entry_missing_id_raises_key_error(self, tmp_path: Path) -> None:
        """engine.get_entry() on a non-existent ID raises KeyError."""
        engine = MemoryEngine(memory_dir=tmp_path)
        with pytest.raises(KeyError):
            engine.get_entry("nonexistent-id")


# ---------------------------------------------------------------------------
# Coverage: _engine_from_ctx error -- lines 33-35 of tools.py
# ---------------------------------------------------------------------------


class TestFromAC_EngineContextError:
    """Coverage: _engine_from_ctx raises ToolError when engine not in context."""

    @pytest.mark.asyncio
    async def test_query_memory_raises_when_engine_missing_from_ctx(self) -> None:
        """query_memory raises ToolError when ctx has no engine attribute."""

        class _CtxNoEngine:
            class request_context:
                class lifespan_context:
                    pass  # no engine attribute

        with pytest.raises(ToolError, match="memory engine is not available"):
            await query_memory(_CtxNoEngine())


# ---------------------------------------------------------------------------
# Coverage: update_entry ValidationError path -- lines 223-224 of tools.py
# ---------------------------------------------------------------------------


class TestFromAC_UpdateValidationError:
    """Coverage: update_entry raises ToolError when updated payload fails validation."""

    @pytest.mark.asyncio
    async def test_update_curated_entry_with_invalid_confidence_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """Confidence 0.5 (below 0.7 minimum) triggers ValidationError → ToolError."""
        entry = _make_entry(state="curated", scope_agents=["builder"])
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, confidence=0.5)


# ---------------------------------------------------------------------------
# Coverage: engine write exception cleanup -- lines 115-118 of engine.py
# ---------------------------------------------------------------------------


class TestFromAC_EngineWriteException:
    """Coverage: engine.write() cleans up temp file when write operation fails."""

    def test_write_exception_propagates_and_cleans_up(self, tmp_path: Path) -> None:
        """Mocking Path.replace to fail exercises the except block in write()."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry()

        with (
            patch("owlbear_mcp_memory.engine.Path.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            engine.write(entry)

        # After failed write, no target file should exist
        md_files = list(tmp_path.glob("*.md"))  # noqa: ASYNC240
        assert md_files == []


# ---------------------------------------------------------------------------
# Coverage: models.py validator error branches (lines 68-69, 76-77, 92-93,
# 102-103, 108-110, 113-114) -- needed to reach 90% package total
# ---------------------------------------------------------------------------


class TestFromAC_ModelValidationPaths:
    """Coverage for MemoryEntry validator error branches in models.py."""

    def test_blank_title_raises_validation_error(self) -> None:
        """Blank title triggers _validate_title_not_blank error branch."""
        with pytest.raises(ValidationError, match="title must not be empty"):
            MemoryEntry(
                id=_uuid(1), title="   ", categories=["domain-knowledge"],
                confidence=0.8, state="pending", content="c",
                source_agent="builder", created_at=_TS, updated_at=_TS,
            )

    def test_blank_source_agent_raises_validation_error(self) -> None:
        """Blank source_agent triggers _validate_source_agent_not_blank error branch."""
        with pytest.raises(ValidationError, match="source_agent must not be empty"):
            MemoryEntry(
                id=_uuid(1), title="T", categories=["domain-knowledge"],
                confidence=0.8, state="pending", content="c",
                source_agent="  ", created_at=_TS, updated_at=_TS,
            )

    def test_invalid_uuid_format_raises_validation_error(self) -> None:
        """Non-UUIDv4 id triggers _validate_id_uuid_v4 error branch."""
        with pytest.raises(ValidationError, match="UUIDv4"):
            MemoryEntry(
                id="not-a-uuid", title="T", categories=["domain-knowledge"],
                confidence=0.8, state="pending", content="c",
                source_agent="builder", created_at=_TS, updated_at=_TS,
            )

    def test_datetime_without_time_raises_validation_error(self) -> None:
        """Date-only created_at triggers 'must include date and time' error."""
        with pytest.raises(ValidationError, match="date and time"):
            MemoryEntry(
                id=_uuid(1), title="T", categories=["domain-knowledge"],
                confidence=0.8, state="pending", content="c",
                source_agent="builder", created_at="2026-05-01", updated_at=_TS,
            )

    def test_unparseable_datetime_raises_validation_error(self) -> None:
        """Malformed datetime triggers 'valid ISO 8601' error in validator."""
        with pytest.raises(ValidationError, match="ISO 8601"):
            MemoryEntry(
                id=_uuid(1), title="T", categories=["domain-knowledge"],
                confidence=0.8, state="pending", content="c",
                source_agent="builder", created_at="2026-99-99T00:00:00Z", updated_at=_TS,
            )

    def test_datetime_without_timezone_raises_validation_error(self) -> None:
        """Timezone-naive datetime triggers 'must include timezone' error."""
        with pytest.raises(ValidationError, match="timezone"):
            MemoryEntry(
                id=_uuid(1), title="T", categories=["domain-knowledge"],
                confidence=0.8, state="pending", content="c",
                source_agent="builder", created_at="2026-05-01T10:00:00", updated_at=_TS,
            )
