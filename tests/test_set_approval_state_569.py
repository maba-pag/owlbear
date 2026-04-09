"""Tests for task #569: set_approval_state MCP tool (TDD RED).

Contract-level tests for the set_approval_state tool in owlbear-mcp-memory.
Covers the full 3x3 state transition matrix, timestamps, error handling,
cross-tool interaction, ToolAnnotations, and _VALID_TRANSITIONS constant.

All tests use in-memory SQLite — no disk files.

AC coverage:
  - AC-T1:  pending → approved succeeds (approval_state = 'approved')
  - AC-T2:  pending → deleted succeeds (approval_state = 'deleted')
  - AC-T3:  deleted → pending succeeds (approval_state = 'pending')
  - AC-T4:  approved → pending returns soft error starting with "error:"
  - AC-T5:  approved → deleted returns soft error starting with "error:"
  - AC-T6:  deleted → approved returns soft error starting with "error:"
  - AC-T7:  pending → pending (same-state) returns soft error
  - AC-T8:  approved → approved (same-state) returns soft error
  - AC-T9:  deleted → deleted (same-state) returns soft error
  - AC-T10: soft error message contains "transition from" and "is not allowed"
  - AC-TS1: updated_at refreshed on every successful transition
  - AC-TS2: deleted_at set to non-null UTC ISO timestamp on → deleted
  - AC-TS3: deleted_at cleared to NULL on deleted → pending
  - AC-E1:  ToolError raised for nonexistent entry_id
  - AC-E2:  Invalid new_state (e.g. "archived") fails (ToolError or soft error)
  - AC-R1:  Successful transition returns non-empty str
  - AC-A1:  set_approval_state discoverable via mcp._tool_manager.list_tools()
  - AC-A2:  Annotations: readOnlyHint=False, idempotentHint=False, destructiveHint=True
  - AC-V1:  _VALID_TRANSITIONS is a frozenset containing exactly the 3 allowed pairs
  - AC-CC1: server.py __all__ includes "set_approval_state"
  - AC-I1:  mark_for_deletion then set_approval_state(pending) roundtrip
  - AC-I2:  set_approval_state(deleted) then mark_for_deletion is idempotent

All tests FAIL in RED phase — ImportError expected until builder adds
set_approval_state + _VALID_TRANSITIONS to owlbear_mcp_memory/tools.py (#529).
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# Import under test — ImportError until builder implements task #529
# ---------------------------------------------------------------------------
from owlbear_mcp_memory.tools import (  # type: ignore[import]
    _VALID_TRANSITIONS,
    mark_for_deletion,
    set_approval_state,
)
from owlbear_mcp_memory.server import AppContext, mcp

# ---------------------------------------------------------------------------
# DDL — mirrors server.py
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
# Helpers — mirrored from test_memory_tools_556.py
# ---------------------------------------------------------------------------


def _make_conn() -> sqlite3.Connection:
    """Create a fresh in-memory SQLite connection with the memory_entries table."""
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
    """Insert a row into memory_entries and return its id."""
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


def _fetch_entry(conn: sqlite3.Connection, entry_id: str) -> dict[str, Any] | None:
    """Fetch a single entry by id as a dict, or None if not found."""
    row = conn.execute(
        "SELECT * FROM memory_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def _get_tool_annotations(tool_name: str) -> Any | None:
    """Return ToolAnnotations for a named tool on the mcp instance, or None."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # type: ignore[union-attr]
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_ValidTransitions — AC-T1, AC-T2, AC-T3
# ---------------------------------------------------------------------------


class TestFromAC_ValidTransitions:
    """Contract tests for the 3 allowed state transitions."""

    @pytest.mark.asyncio
    async def test_pending_to_approved_succeeds(self) -> None:
        """AC-T1: pending → approved sets approval_state to 'approved' in DB."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await set_approval_state(ctx, entry_id=eid, new_state="approved")

        row = _fetch_entry(conn, eid)
        assert row is not None
        assert row["approval_state"] == "approved", (
            f"Expected 'approved' after pending→approved, got {row['approval_state']!r}"
        )

    @pytest.mark.asyncio
    async def test_pending_to_deleted_succeeds(self) -> None:
        """AC-T2: pending → deleted sets approval_state to 'deleted' in DB."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await set_approval_state(ctx, entry_id=eid, new_state="deleted")

        row = _fetch_entry(conn, eid)
        assert row is not None
        assert row["approval_state"] == "deleted", (
            f"Expected 'deleted' after pending→deleted, got {row['approval_state']!r}"
        )

    @pytest.mark.asyncio
    async def test_deleted_to_pending_succeeds(self) -> None:
        """AC-T3: deleted → pending sets approval_state to 'pending' in DB."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="deleted", deleted_at="2026-01-01T00:00:00Z")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await set_approval_state(ctx, entry_id=eid, new_state="pending")

        row = _fetch_entry(conn, eid)
        assert row is not None
        assert row["approval_state"] == "pending", (
            f"Expected 'pending' after deleted→pending, got {row['approval_state']!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_InvalidTransitions — AC-T4 through AC-T9
# ---------------------------------------------------------------------------


class TestFromAC_InvalidTransitions:
    """Contract tests for the 6 disallowed transitions (full 3x3 minus 3 valid)."""

    @pytest.mark.asyncio
    async def test_approved_to_pending_returns_soft_error(self) -> None:
        """AC-T4: approved → pending is not allowed; must raise ToolError."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="pending")

    @pytest.mark.asyncio
    async def test_approved_to_deleted_returns_soft_error(self) -> None:
        """AC-T5: approved → deleted is not allowed; must raise ToolError."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="deleted")

    @pytest.mark.asyncio
    async def test_deleted_to_approved_returns_soft_error(self) -> None:
        """AC-T6: deleted → approved is not allowed; must raise ToolError."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="deleted", deleted_at="2026-01-01T00:00:00Z")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="approved")

    @pytest.mark.asyncio
    async def test_pending_to_pending_returns_soft_error(self) -> None:
        """AC-T7: pending → pending (same-state) is not allowed; must raise ToolError."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="pending")

    @pytest.mark.asyncio
    async def test_approved_to_approved_returns_soft_error(self) -> None:
        """AC-T8: approved → approved (same-state) is not allowed; must raise ToolError."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="approved")

    @pytest.mark.asyncio
    async def test_deleted_to_deleted_returns_soft_error(self) -> None:
        """AC-T9: deleted → deleted (same-state) is not allowed; must raise ToolError."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="deleted", deleted_at="2026-01-01T00:00:00Z")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id=eid, new_state="deleted")


# ---------------------------------------------------------------------------
# TestFromAC_ErrorFormat — AC-T10
# ---------------------------------------------------------------------------


class TestFromAC_ErrorFormat:
    """Contract test for the soft error message content."""

    @pytest.mark.asyncio
    async def test_invalid_transition_message_format(self) -> None:
        """AC-T10: ToolError message must contain 'transition from' and 'is not allowed'."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="approved")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError) as exc_info:
            await set_approval_state(ctx, entry_id=eid, new_state="pending")

        msg = str(exc_info.value)
        assert "transition from" in msg.lower(), (
            f"Error message must contain 'transition from', got: {msg!r}"
        )
        assert "is not allowed" in msg.lower(), (
            f"Error message must contain 'is not allowed', got: {msg!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_Timestamps — AC-TS1, AC-TS2, AC-TS3
# ---------------------------------------------------------------------------


class TestFromAC_Timestamps:
    """Contract tests for timestamp updates on state transitions."""

    @pytest.mark.asyncio
    async def test_updated_at_refreshed_on_successful_transition(self) -> None:
        """AC-TS1: updated_at must differ from its pre-transition value after success."""
        conn = _make_conn()
        old_ts = "2020-01-01T00:00:00+00:00"
        eid = _insert_entry(conn, approval_state="pending", updated_at=old_ts)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await set_approval_state(ctx, entry_id=eid, new_state="approved")

        row = _fetch_entry(conn, eid)
        assert row is not None
        assert row["updated_at"] != old_ts, (
            f"updated_at must be refreshed on transition; still {row['updated_at']!r}"
        )

    @pytest.mark.asyncio
    async def test_deleted_at_set_on_transition_to_deleted(self) -> None:
        """AC-TS2: deleted_at must be a non-null UTC ISO string after → deleted transition."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending", deleted_at=None)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await set_approval_state(ctx, entry_id=eid, new_state="deleted")

        row = _fetch_entry(conn, eid)
        assert row is not None
        assert row["deleted_at"] is not None, (
            "deleted_at must be set to a UTC ISO timestamp after → deleted"
        )
        assert isinstance(row["deleted_at"], str), (
            f"deleted_at must be a str, got {type(row['deleted_at'])!r}"
        )
        assert len(row["deleted_at"]) > 0, (
            f"deleted_at must be non-empty, got {row['deleted_at']!r}"
        )

    @pytest.mark.asyncio
    async def test_deleted_at_cleared_on_transition_from_deleted_to_pending(self) -> None:
        """AC-TS3: deleted_at must be NULL after deleted → pending transition."""
        conn = _make_conn()
        eid = _insert_entry(
            conn, approval_state="deleted", deleted_at="2026-01-01T00:00:00+00:00"
        )
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await set_approval_state(ctx, entry_id=eid, new_state="pending")

        row = _fetch_entry(conn, eid)
        assert row is not None
        assert row["deleted_at"] is None, (
            f"deleted_at must be cleared to NULL after deleted→pending, got {row['deleted_at']!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_Errors — AC-E1, AC-E2
# ---------------------------------------------------------------------------


class TestFromAC_Errors:
    """Contract tests for error-path behaviour."""

    @pytest.mark.asyncio
    async def test_toolerror_raised_for_nonexistent_entry_id(self) -> None:
        """AC-E1: ToolError raised when entry_id does not exist in DB."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        with pytest.raises(ToolError):
            await set_approval_state(ctx, entry_id="nonexistent-id", new_state="approved")

    @pytest.mark.asyncio
    async def test_invalid_new_state_does_not_succeed_silently(self) -> None:
        """AC-E2: An unrecognised new_state (e.g. 'archived') must not silently succeed.

        Acceptable outcomes: ToolError raised, or soft error string returned.
        The approval_state in the DB must remain unchanged in either case.
        """
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        silently_succeeded = False
        try:
            result = await set_approval_state(ctx, entry_id=eid, new_state="archived")
            # If no exception: must be a soft error string
            if isinstance(result, str) and result.startswith("error:"):
                pass  # acceptable soft error
            else:
                silently_succeeded = True
        except ToolError:
            pass  # acceptable — hard error

        assert not silently_succeeded, (
            "set_approval_state must not silently accept an invalid new_state like 'archived'"
        )

        # Regardless of error type, DB must be unchanged
        row = _fetch_entry(conn, eid)
        assert row is not None
        assert row["approval_state"] == "pending", (
            f"DB approval_state must remain 'pending' after invalid transition, "
            f"got {row['approval_state']!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ReturnValue — AC-R1
# ---------------------------------------------------------------------------


class TestFromAC_ReturnValue:
    """Contract test for the successful return value."""

    @pytest.mark.asyncio
    async def test_successful_transition_returns_non_empty_str(self) -> None:
        """AC-R1: A successful transition must return a non-empty str."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await set_approval_state(ctx, entry_id=eid, new_state="approved")

        assert isinstance(result, str), (
            f"set_approval_state must return str on success, got {type(result)!r}"
        )
        assert len(result) > 0, "set_approval_state must return a non-empty string on success"


# ---------------------------------------------------------------------------
# TestFromAC_ToolAnnotations — AC-A1, AC-A2
# ---------------------------------------------------------------------------


class TestFromAC_ToolAnnotations:
    """Contract tests for ToolAnnotations on set_approval_state."""

    def test_set_approval_state_discoverable_via_tool_manager(self) -> None:
        """AC-A1: set_approval_state must be discoverable via mcp._tool_manager.list_tools()."""
        assert hasattr(mcp, "_tool_manager"), "mcp must have a _tool_manager attribute"
        tool_names = [
            getattr(t, "name", None) for t in mcp._tool_manager.list_tools()  # type: ignore[union-attr]
        ]
        assert "set_approval_state" in tool_names, (
            f"set_approval_state not found in registered tools; found: {tool_names}"
        )

    def test_set_approval_state_annotations(self) -> None:
        """AC-A2: annotations must have readOnlyHint=False, idempotentHint=False, destructiveHint=True."""
        ann = _get_tool_annotations("set_approval_state")
        assert ann is not None, (
            "set_approval_state has no ToolAnnotations; add annotations=ToolAnnotations(...)"
        )
        assert ann.readOnlyHint is False, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=False, got {ann.readOnlyHint!r}"  # type: ignore[union-attr]
        )
        assert ann.idempotentHint is False, (  # type: ignore[union-attr]
            f"Expected idempotentHint=False, got {ann.idempotentHint!r}"  # type: ignore[union-attr]
        )
        assert ann.destructiveHint is True, (  # type: ignore[union-attr]
            f"Expected destructiveHint=True, got {ann.destructiveHint!r}"  # type: ignore[union-attr]
        )


# ---------------------------------------------------------------------------
# TestFromAC_ValidTransitionsConstant — AC-V1
# ---------------------------------------------------------------------------


class TestFromAC_ValidTransitionsConstant:
    """Contract test for _VALID_TRANSITIONS constant."""

    def test_valid_transitions_is_frozenset_with_exactly_three_pairs(self) -> None:
        """AC-V1: _VALID_TRANSITIONS must be a frozenset of exactly the 3 allowed pairs."""
        expected = frozenset({
            ("pending", "approved"),
            ("pending", "deleted"),
            ("deleted", "pending"),
        })
        assert isinstance(_VALID_TRANSITIONS, frozenset), (
            f"_VALID_TRANSITIONS must be a frozenset, got {type(_VALID_TRANSITIONS)!r}"
        )
        assert expected == _VALID_TRANSITIONS, (
            f"_VALID_TRANSITIONS mismatch.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {_VALID_TRANSITIONS}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CrossCutting — AC-CC1
# ---------------------------------------------------------------------------


class TestFromAC_CrossCutting:
    """Contract test for server.py __all__ export."""

    def test_server_all_includes_set_approval_state(self) -> None:
        """AC-CC1: server.py __all__ must include 'set_approval_state'."""
        import owlbear_mcp_memory.server as srv  # type: ignore[import]
        assert hasattr(srv, "__all__"), "server.py must define __all__"
        assert "set_approval_state" in srv.__all__, (
            "'set_approval_state' not found in server.__all__; "
            "add it as a forwarded export (noqa: F822)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CrossToolInteraction — AC-I1, AC-I2
# ---------------------------------------------------------------------------


class TestFromAC_CrossToolInteraction:
    """Cross-tool contract tests — set_approval_state interacting with mark_for_deletion."""

    @pytest.mark.asyncio
    async def test_mark_for_deletion_then_set_approval_state_pending_roundtrip(self) -> None:
        """AC-I1: mark_for_deletion(entry) then set_approval_state(entry, 'pending')
        results in pending state with deleted_at=NULL."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        # Use mark_for_deletion to put entry in deleted state
        await mark_for_deletion(ctx, entry_id=eid)

        row_after_delete = _fetch_entry(conn, eid)
        assert row_after_delete is not None
        assert row_after_delete["approval_state"] == "deleted"

        # Now restore to pending via set_approval_state
        result = await set_approval_state(ctx, entry_id=eid, new_state="pending")

        assert isinstance(result, str), (
            f"set_approval_state must return str, got {type(result)!r}"
        )
        assert not result.startswith("error:"), (
            f"deleted→pending via set_approval_state must succeed, got: {result!r}"
        )

        row_after_restore = _fetch_entry(conn, eid)
        assert row_after_restore is not None
        assert row_after_restore["approval_state"] == "pending", (
            f"Entry must be pending after roundtrip, got {row_after_restore['approval_state']!r}"
        )
        assert row_after_restore["deleted_at"] is None, (
            "deleted_at must be NULL after deleted→pending restore"
        )

    @pytest.mark.asyncio
    async def test_set_approval_state_deleted_then_mark_for_deletion_is_idempotent(self) -> None:
        """AC-I2: set_approval_state(entry, 'deleted') then mark_for_deletion(entry)
        must not error — mark_for_deletion is idempotent on already-deleted entries."""
        conn = _make_conn()
        eid = _insert_entry(conn, approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        # Delete via set_approval_state
        await set_approval_state(ctx, entry_id=eid, new_state="deleted")

        row_after = _fetch_entry(conn, eid)
        assert row_after is not None
        assert row_after["approval_state"] == "deleted"

        # mark_for_deletion on already-deleted entry must not raise
        try:
            await mark_for_deletion(ctx, entry_id=eid)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(
                f"mark_for_deletion raised on already-deleted entry: {exc!r}"
            )
