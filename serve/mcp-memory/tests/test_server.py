"""Per-package tests for owlbear-mcp-memory tools.

AC coverage:
  AC2: Approval state machine — all 3 valid transitions and rejection of invalid
  AC3: record_learning validation — confidence < 0.7 and invalid category
  AC4: get_knowledge scope-tiered sort order — tier 1 before tier 4
  AC5: mark_for_deletion idempotency — second call succeeds as no-op
  AC6: list_entries filter combinations — agent_id, category, status, include_deleted

All tests use in-memory SQLite — no disk files.
"""

from __future__ import annotations

import sqlite3
import uuid
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_memory.server import AppContext
from owlbear_mcp_memory.tools import (
    get_knowledge,
    list_entries,
    mark_for_deletion,
    record_learning,
    set_approval_state,
)

# ---------------------------------------------------------------------------
# DDL — mirrored from server.py for in-memory test databases
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL,
    scope_agent TEXT,
    scope_project TEXT,
    approval_state TEXT NOT NULL DEFAULT 'pending',
    deleted_at TEXT
)
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_DDL)
    conn.commit()
    return conn


def _make_app_ctx(
    conn: sqlite3.Connection,
    project_name: str | None = None,
) -> AppContext:
    return AppContext(conn=conn, project_name=project_name)


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _insert_entry(  # noqa: PLR0913
    conn: sqlite3.Connection,
    *,
    entry_id: str | None = None,
    content: str = "test content",
    category: str = "knowledge",
    confidence: float = 0.8,
    created_at: str = "2026-01-01T00:00:00Z",
    updated_at: str = "2026-01-01T00:00:00Z",
    source: str = "test-agent",
    scope_agent: str | None = None,
    scope_project: str | None = None,
    approval_state: str = "pending",
    deleted_at: str | None = None,
) -> str:
    eid = entry_id or str(uuid.uuid4())
    conn.execute(
        """INSERT INTO memory_entries
           (id, content, category, confidence, created_at, updated_at, source,
            scope_agent, scope_project, approval_state, deleted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            eid, content, category, confidence, created_at, updated_at, source,
            scope_agent, scope_project, approval_state, deleted_at,
        ),
    )
    conn.commit()
    return eid


# ---------------------------------------------------------------------------
# AC2: Approval state machine
# ---------------------------------------------------------------------------


class TestFromAC_ApprovalStateMachine:
    """AC2: All 3 valid transitions succeed; invalid transitions return an error string."""

    @pytest.mark.asyncio
    async def test_pending_to_approved_succeeds(self) -> None:
        """AC2: pending→approved is a valid transition."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await set_approval_state(ctx, entry_id=entry_id, new_state="approved")

        assert "approved" in result
        row = conn.execute(
            "SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        assert row[0] == "approved"

    @pytest.mark.asyncio
    async def test_pending_to_deleted_succeeds(self) -> None:
        """AC2: pending→deleted is a valid transition."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await set_approval_state(ctx, entry_id=entry_id, new_state="deleted")

        assert "deleted" in result
        row = conn.execute(
            "SELECT approval_state, deleted_at FROM memory_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        assert row[0] == "deleted"
        assert row[1] is not None, "deleted_at must be set on transition to deleted"

    @pytest.mark.asyncio
    async def test_deleted_to_pending_succeeds(self) -> None:
        """AC2: deleted→pending is a valid transition."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await set_approval_state(ctx, entry_id=entry_id, new_state="pending")

        assert "pending" in result
        row = conn.execute(
            "SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        assert row[0] == "pending"

    @pytest.mark.asyncio
    async def test_approved_to_pending_is_rejected(self) -> None:
        """AC2: approved→pending is not a valid transition and returns error string."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="approved")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await set_approval_state(ctx, entry_id=entry_id, new_state="pending")

        assert isinstance(result, str)
        assert result.startswith("error:")
        assert "approved" in result

    @pytest.mark.asyncio
    async def test_approved_to_deleted_is_rejected(self) -> None:
        """AC2: approved→deleted is not a valid transition and returns error string."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="approved")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await set_approval_state(ctx, entry_id=entry_id, new_state="deleted")

        assert isinstance(result, str)
        assert result.startswith("error:")

    @pytest.mark.asyncio
    async def test_same_state_transition_is_rejected(self) -> None:
        """AC2: pending→pending (same state) is not a valid transition."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await set_approval_state(ctx, entry_id=entry_id, new_state="pending")

        assert isinstance(result, str)
        assert result.startswith("error:")

    @pytest.mark.asyncio
    async def test_nonexistent_entry_raises_tool_error(self) -> None:
        """AC2: set_approval_state raises ToolError for unknown entry_id."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(
                ctx, entry_id="does-not-exist", new_state="approved"
            )


# ---------------------------------------------------------------------------
# AC3: record_learning validation
# ---------------------------------------------------------------------------


class TestFromAC_RecordLearningValidation:
    """AC3: confidence < 0.7 and invalid category both return error strings."""

    @pytest.mark.asyncio
    async def test_confidence_below_threshold_returns_error(self) -> None:
        """AC3: confidence 0.69 returns an error string."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await record_learning(
            ctx, agent_id="a", content="x", category="knowledge", confidence=0.69
        )

        assert isinstance(result, str)
        assert result.startswith("error:")
        assert "0.7" in result

    @pytest.mark.asyncio
    async def test_confidence_zero_returns_error(self) -> None:
        """AC3: confidence 0.0 returns an error string."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await record_learning(
            ctx, agent_id="a", content="x", category="knowledge", confidence=0.0
        )

        assert isinstance(result, str)
        assert result.startswith("error:")

    @pytest.mark.asyncio
    async def test_invalid_category_returns_error(self) -> None:
        """AC3: unknown category returns an error string."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await record_learning(
            ctx, agent_id="a", content="x", category="bogus", confidence=0.9
        )

        assert isinstance(result, str)
        assert result.startswith("error:")
        assert "bogus" in result

    @pytest.mark.asyncio
    async def test_confidence_at_boundary_succeeds(self) -> None:
        """AC3 boundary: confidence exactly 0.7 is accepted and returns a UUID."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await record_learning(
            ctx, agent_id="a", content="boundary test", category="knowledge",
            confidence=0.7,
        )

        assert not result.startswith("error:"), (
            "confidence == 0.7 must be accepted, not rejected"
        )
        # Result should be a valid UUID string
        uuid.UUID(result)  # raises ValueError if not a valid UUID


# ---------------------------------------------------------------------------
# AC4: get_knowledge scope-tiered sort order
# ---------------------------------------------------------------------------


class TestFromAC_GetKnowledgeSortOrder:
    """AC4: tier 1 (agent+project) entries appear before tier 4 (global) entries."""

    @pytest.mark.asyncio
    async def test_tier1_precedes_tier4(self) -> None:
        """AC4: entry scoped to agent+project appears before global entry."""
        conn = _make_conn()
        _insert_entry(conn, content="global", scope_agent=None, scope_project=None)
        _insert_entry(
            conn, content="specific", scope_agent="alice", scope_project="proj-a"
        )
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj-a"))

        results = await get_knowledge(ctx, agent_id="alice")

        assert isinstance(results, list)
        contents = [r["content"] for r in results]
        assert "specific" in contents
        assert "global" in contents
        assert contents.index("specific") < contents.index("global"), (
            "Tier 1 (agent+project) must sort before tier 4 (global)"
        )

    @pytest.mark.asyncio
    async def test_deleted_entries_excluded_from_results(self) -> None:
        """AC4 (contract): deleted entries are never returned by get_knowledge."""
        conn = _make_conn()
        _insert_entry(conn, content="alive", approval_state="pending")
        _insert_entry(conn, content="dead", approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await get_knowledge(ctx, agent_id="any")

        contents = [r["content"] for r in results]
        assert "dead" not in contents, "Deleted entries must be excluded from get_knowledge"


# ---------------------------------------------------------------------------
# AC5: mark_for_deletion idempotency
# ---------------------------------------------------------------------------


class TestFromAC_MarkForDeletion:
    """AC5: mark_for_deletion is idempotent — second call on same entry succeeds."""

    @pytest.mark.asyncio
    async def test_first_call_marks_deleted(self) -> None:
        """AC5: first mark_for_deletion sets approval_state to deleted."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await mark_for_deletion(ctx, entry_id=entry_id)

        assert "deletion" in result
        row = conn.execute(
            "SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        assert row[0] == "deleted"

    @pytest.mark.asyncio
    async def test_second_call_is_no_op(self) -> None:
        """AC5: calling mark_for_deletion twice on the same entry succeeds (no-op)."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await mark_for_deletion(ctx, entry_id=entry_id)
        second_result = await mark_for_deletion(ctx, entry_id=entry_id)

        assert isinstance(second_result, str)
        assert not second_result.startswith("error:"), (
            "Second mark_for_deletion call must succeed (idempotent)"
        )

    @pytest.mark.asyncio
    async def test_nonexistent_entry_raises_tool_error(self) -> None:
        """AC5: mark_for_deletion raises ToolError for unknown entry_id."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await mark_for_deletion(ctx, entry_id="no-such-entry")


# ---------------------------------------------------------------------------
# AC6: list_entries filter combinations
# ---------------------------------------------------------------------------


class TestFromAC_ListEntriesFilters:
    """AC6: list_entries filters by agent_id, category, status, include_deleted."""

    @pytest.mark.asyncio
    async def test_filter_by_agent_id(self) -> None:
        """AC6: agent_id filter returns only entries scoped to that agent."""
        conn = _make_conn()
        _insert_entry(conn, content="alice-entry", scope_agent="alice")
        _insert_entry(conn, content="bob-entry", scope_agent="bob")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await list_entries(ctx, agent_id="alice")

        assert isinstance(results, list)
        contents = [r["content"] for r in results]
        assert "alice-entry" in contents
        assert "bob-entry" not in contents

    @pytest.mark.asyncio
    async def test_filter_by_category(self) -> None:
        """AC6: category filter returns only entries with matching category."""
        conn = _make_conn()
        _insert_entry(conn, content="pref-entry", category="preference")
        _insert_entry(conn, content="goal-entry", category="goal")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await list_entries(ctx, category="preference")

        assert isinstance(results, list)
        contents = [r["content"] for r in results]
        assert "pref-entry" in contents
        assert "goal-entry" not in contents

    @pytest.mark.asyncio
    async def test_filter_by_status(self) -> None:
        """AC6: status filter returns only entries with matching approval_state."""
        conn = _make_conn()
        _insert_entry(conn, content="approved-entry", approval_state="approved")
        _insert_entry(conn, content="pending-entry", approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await list_entries(ctx, status="approved")

        assert isinstance(results, list)
        contents = [r["content"] for r in results]
        assert "approved-entry" in contents
        assert "pending-entry" not in contents

    @pytest.mark.asyncio
    async def test_deleted_excluded_by_default(self) -> None:
        """AC6: deleted entries are excluded unless include_deleted=True."""
        conn = _make_conn()
        _insert_entry(conn, content="live-entry", approval_state="pending")
        _insert_entry(conn, content="dead-entry", approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await list_entries(ctx)

        contents = [r["content"] for r in results]
        assert "live-entry" in contents
        assert "dead-entry" not in contents, (
            "Deleted entries must be excluded when include_deleted=False (default)"
        )

    @pytest.mark.asyncio
    async def test_include_deleted_shows_deleted_entries(self) -> None:
        """AC6: include_deleted=True shows deleted entries alongside live ones."""
        conn = _make_conn()
        _insert_entry(conn, content="live-entry", approval_state="pending")
        _insert_entry(conn, content="dead-entry", approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await list_entries(ctx, include_deleted=True)

        contents = [r["content"] for r in results]
        assert "live-entry" in contents
        assert "dead-entry" in contents

    @pytest.mark.asyncio
    async def test_multiple_filters_are_anded(self) -> None:
        """AC6: multiple filters are AND-combined."""
        conn = _make_conn()
        _insert_entry(
            conn, content="match",
            scope_agent="alice", category="preference", approval_state="approved",
        )
        _insert_entry(
            conn, content="wrong-agent",
            scope_agent="bob", category="preference", approval_state="approved",
        )
        _insert_entry(
            conn, content="wrong-category",
            scope_agent="alice", category="goal", approval_state="approved",
        )
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await list_entries(
            ctx, agent_id="alice", category="preference", status="approved"
        )

        assert isinstance(results, list)
        contents = [r["content"] for r in results]
        assert contents == ["match"], (
            "Only entries matching all three filters should be returned"
        )

    @pytest.mark.asyncio
    async def test_no_filters_returns_all_non_deleted(self) -> None:
        """AC6 edge: no filters returns all non-deleted entries."""
        conn = _make_conn()
        _insert_entry(conn, content="a", approval_state="pending")
        _insert_entry(conn, content="b", approval_state="approved")
        _insert_entry(conn, content="c", approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        results = await list_entries(ctx)

        contents = [r["content"] for r in results]
        assert "a" in contents
        assert "b" in contents
        assert "c" not in contents
