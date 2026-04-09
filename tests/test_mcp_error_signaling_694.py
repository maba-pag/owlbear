"""Tests for task #694: Fix 3 MCP tool error signaling bugs.

TDD RED phase — all tests FAIL before builder applies fixes.

AC coverage:
  - AC1: list_sources ToolError message does not start with "error: " prefix
  - AC2: get_stats ToolError message does not start with "error: " prefix
  - AC3: set_approval_state raises ToolError for all 6 invalid transitions
         (not returns soft error string)
"""

from __future__ import annotations

import sqlite3
import uuid
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_knowledge.server import get_stats, list_sources
from owlbear_mcp_memory.server import AppContext
from owlbear_mcp_memory.tools import set_approval_state

# ---------------------------------------------------------------------------
# Helpers — mcp-knowledge context
# ---------------------------------------------------------------------------


def _make_knowledge_ctx(
    *,
    source_store: object = None,
    graph_store: object = None,
) -> MagicMock:
    mcp_ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.source_store = source_store
    app_ctx.graph_store = graph_store
    mcp_ctx.request_context.lifespan_context = app_ctx
    return mcp_ctx


# ---------------------------------------------------------------------------
# Helpers — mcp-memory context
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


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_DDL)
    conn.commit()
    return conn


def _make_memory_ctx(conn: sqlite3.Connection) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(conn=conn, project_name=None)
    return ctx


def _insert_entry(
    conn: sqlite3.Connection,
    *,
    approval_state: str = "pending",
    deleted_at: str | None = None,
) -> str:
    eid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO memory_entries
           (id, content, category, confidence, created_at, updated_at, source,
            scope_agent, scope_project, approval_state, deleted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            eid, "test content", "knowledge", 0.8,
            "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "test-agent",
            None, None, approval_state, deleted_at,
        ),
    )
    conn.commit()
    return eid


# ---------------------------------------------------------------------------
# TestFromAC_ListSourcesErrorPrefix — AC1
# ---------------------------------------------------------------------------


class TestFromAC_ListSourcesErrorPrefix:
    """AC1: list_sources ToolError message must not carry the double 'error: ' prefix."""

    @pytest.mark.asyncio
    async def test_list_sources_tool_error_message_has_no_error_prefix(self) -> None:
        """AC1: ToolError from list_sources must not start with 'error: '."""
        ctx = _make_knowledge_ctx(source_store=None)

        with pytest.raises(ToolError) as exc_info:
            await list_sources(ctx)

        msg = str(exc_info.value)
        assert not msg.startswith("error:"), (
            f"ToolError message must not carry 'error:' prefix — double-prefix anti-pattern; "
            f"got: {msg!r}"
        )

    @pytest.mark.asyncio
    async def test_list_sources_tool_error_message_is_exact(self) -> None:
        """AC1: ToolError message must be exactly 'source store not available'."""
        ctx = _make_knowledge_ctx(source_store=None)

        with pytest.raises(ToolError) as exc_info:
            await list_sources(ctx)

        msg = str(exc_info.value)
        assert msg == "source store not available", (
            f"Expected 'source store not available', got: {msg!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GetStatsErrorPrefix — AC2
# ---------------------------------------------------------------------------


class TestFromAC_GetStatsErrorPrefix:
    """AC2: get_stats ToolError message must not carry the double 'error: ' prefix."""

    @pytest.mark.asyncio
    async def test_get_stats_tool_error_message_has_no_error_prefix(self) -> None:
        """AC2: ToolError from get_stats must not start with 'error: '."""
        ctx = _make_knowledge_ctx(graph_store=None)

        with pytest.raises(ToolError) as exc_info:
            await get_stats(ctx)

        msg = str(exc_info.value)
        assert not msg.startswith("error:"), (
            f"ToolError message must not carry 'error:' prefix — double-prefix anti-pattern; "
            f"got: {msg!r}"
        )

    @pytest.mark.asyncio
    async def test_get_stats_tool_error_message_is_exact(self) -> None:
        """AC2: ToolError message must be exactly 'graph store not available'."""
        ctx = _make_knowledge_ctx(graph_store=None)

        with pytest.raises(ToolError) as exc_info:
            await get_stats(ctx)

        msg = str(exc_info.value)
        assert msg == "graph store not available", (
            f"Expected 'graph store not available', got: {msg!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SetApprovalStateRaisesToolError — AC3
# ---------------------------------------------------------------------------


class TestFromAC_SetApprovalStateRaisesToolError:
    """AC3: all 6 invalid transitions must raise ToolError, not return a soft error string."""

    @pytest.mark.asyncio
    async def test_approved_to_pending_raises_tool_error(self) -> None:
        """AC3: approved→pending must raise ToolError (not return 'error: ...' string)."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_memory_ctx(conn)

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="pending")

    @pytest.mark.asyncio
    async def test_approved_to_deleted_raises_tool_error(self) -> None:
        """AC3: approved→deleted must raise ToolError (not return 'error: ...' string)."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_memory_ctx(conn)

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="deleted")

    @pytest.mark.asyncio
    async def test_deleted_to_approved_raises_tool_error(self) -> None:
        """AC3: deleted→approved must raise ToolError (not return 'error: ...' string)."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="deleted", deleted_at="2026-01-01T00:00:00Z")
        ctx = _make_memory_ctx(conn)

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="approved")

    @pytest.mark.asyncio
    async def test_pending_to_pending_raises_tool_error(self) -> None:
        """AC3: pending→pending (same-state) must raise ToolError (not return soft error)."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_memory_ctx(conn)

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="pending")

    @pytest.mark.asyncio
    async def test_approved_to_approved_raises_tool_error(self) -> None:
        """AC3: approved→approved (same-state) must raise ToolError (not return soft error)."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_memory_ctx(conn)

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="approved")

    @pytest.mark.asyncio
    async def test_deleted_to_deleted_raises_tool_error(self) -> None:
        """AC3: deleted→deleted (same-state) must raise ToolError (not return soft error)."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="deleted", deleted_at="2026-01-01T00:00:00Z")
        ctx = _make_memory_ctx(conn)

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="deleted")

    @pytest.mark.asyncio
    async def test_invalid_transition_tool_error_references_states(self) -> None:
        """AC3: ToolError message for invalid transitions must reference the involved states."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_memory_ctx(conn)

        with pytest.raises(ToolError) as exc_info:
            await set_approval_state(ctx, entry_id=eid, new_state="pending")

        msg = str(exc_info.value)
        assert "approved" in msg or "pending" in msg, (
            f"ToolError message must reference the transition states; got: {msg!r}"
        )
