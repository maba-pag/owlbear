"""Tests for task #556: memory-mcp tool implementations (TDD RED).

Contract-level tests for all 4 tools: get_knowledge, record_learning,
list_entries, mark_for_deletion, and _apply_tool_exclusions.

All tests use in-memory SQLite — no disk files (see _make_conn helper).

AC coverage:
  - AC1:  get_knowledge returns entries sorted by scope-specificity,
          approval_state (approved before pending), then confidence DESC
  - AC2:  get_knowledge respects 4-tier scope union
          (agent+project, agent-only, project-only, general)
  - AC3:  get_knowledge excludes deleted entries
  - AC4:  get_knowledge limit param defaults to 50
  - AC5:  get_knowledge filters by categories and min_confidence when provided
  - AC6:  record_learning rejects confidence < 0.7 with soft error string
  - AC7:  record_learning rejects invalid category with soft error string
  - AC8:  record_learning generates UUID, sets timestamps,
          source=agent_id, approval_state=pending
  - AC9:  record_learning defaults scope_project to AppContext.project_name when None
  - AC10: record_learning returns bare UUID string on success
  - AC11: list_entries filters by agent_id, category, status
  - AC12: list_entries excludes deleted unless include_deleted=True
  - AC13: mark_for_deletion sets approval_state=deleted and deleted_at+updated_at
  - AC14: mark_for_deletion is idempotent (no-op if already deleted)
  - AC15: mark_for_deletion raises ToolError for nonexistent entry_id
  - AC16: _apply_tool_exclusions reads MEMORY_TOOLS_EXCLUDE and removes tools
  - AC17: ToolAnnotations correct for each tool (readOnly, idempotent, destructive hints)
  - AC18: All tests use in-memory SQLite (no disk files)

All tests FAIL in RED phase — ImportError expected until builder creates
owlbear_mcp_memory/tools.py (#525).
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# Import tools — will raise ImportError until builder creates
# owlbear_mcp_memory/tools.py for task #525 (RED phase).
# ---------------------------------------------------------------------------
from owlbear_mcp_memory.tools import (  # type: ignore[import]
    _apply_tool_exclusions,
    get_knowledge,
    list_entries,
    mark_for_deletion,
    record_learning,
)
from owlbear_mcp_memory.server import AppContext, mcp

# ---------------------------------------------------------------------------
# DDL — mirrored from server.py to set up in-memory test databases
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
# Helpers — in-memory SQLite + context factories
# ---------------------------------------------------------------------------


def _make_conn() -> sqlite3.Connection:
    """Create a fresh in-memory SQLite connection with the memory_entries table.

    AC18: all tests use in-memory SQLite — no disk files.
    check_same_thread=False required for asyncio.to_thread usage in tools.
    """
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
            eid,
            content,
            category,
            confidence,
            created_at,
            updated_at,
            source,
            scope_agent,
            scope_project,
            approval_state,
            deleted_at,
        ),
    )
    conn.commit()
    return eid


# ---------------------------------------------------------------------------
# TestFromAC_GetKnowledge -- AC1-AC5
# ---------------------------------------------------------------------------


class TestFromAC_GetKnowledge:
    """Contract tests for get_knowledge — sort order, scope union, filters, limit."""

    # AC1 + AC2: Tier 1 (agent+project) precedes Tier 4 (general)
    @pytest.mark.asyncio
    async def test_tier1_precedes_tier4_in_sort(self) -> None:
        """AC1+AC2: entries matching agent+project scope come before general entries."""
        conn = _make_conn()
        _insert_entry(conn, content="general", scope_agent=None, scope_project=None)
        _insert_entry(conn, content="specific", scope_agent="bob", scope_project="proj-x")
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj-x"))

        result = await get_knowledge(ctx, agent_id="bob")

        assert isinstance(result, list), "get_knowledge must return a list"
        assert len(result) == 2
        contents = [r["content"] for r in result]
        assert contents.index("specific") < contents.index("general"), (
            "Tier 1 (agent+project) must precede Tier 4 (general) in sort order"
        )

    # AC2: all 4 tiers returned in correct scope order
    @pytest.mark.asyncio
    async def test_all_four_tiers_returned_in_scope_order(self) -> None:
        """AC2: 4-tier union returns entries from all tiers, most specific first."""
        conn = _make_conn()
        _insert_entry(conn, content="t4", scope_agent=None, scope_project=None)
        _insert_entry(conn, content="t3", scope_agent=None, scope_project="p")
        _insert_entry(conn, content="t2", scope_agent="a", scope_project=None)
        _insert_entry(conn, content="t1", scope_agent="a", scope_project="p")
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="p"))

        result = await get_knowledge(ctx, agent_id="a")

        assert len(result) == 4
        contents = [r["content"] for r in result]
        assert contents.index("t1") < contents.index("t2"), "Tier 1 must precede Tier 2"
        assert contents.index("t2") < contents.index("t3"), "Tier 2 must precede Tier 3"
        assert contents.index("t3") < contents.index("t4"), "Tier 3 must precede Tier 4"

    # AC2: entries NOT in the scope union are excluded
    @pytest.mark.asyncio
    async def test_entries_outside_scope_union_excluded(self) -> None:
        """AC2: entry belonging to a different agent and different project is excluded."""
        conn = _make_conn()
        _insert_entry(conn, content="mine", scope_agent="alice", scope_project="my-proj")
        _insert_entry(conn, content="theirs", scope_agent="bob", scope_project="other-proj")
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="my-proj"))

        result = await get_knowledge(ctx, agent_id="alice")

        contents = [r["content"] for r in result]
        assert "mine" in contents
        assert "theirs" not in contents, "Entry scoped to another agent+project must not appear in results"

    # AC1: within same scope tier, approved before pending
    @pytest.mark.asyncio
    async def test_within_same_tier_approved_before_pending(self) -> None:
        """AC1: approved entries come before pending entries within the same scope tier."""
        conn = _make_conn()
        _insert_entry(
            conn,
            content="pending",
            scope_agent=None,
            scope_project=None,
            approval_state="pending",
            confidence=0.9,
        )
        _insert_entry(
            conn,
            content="approved",
            scope_agent=None,
            scope_project=None,
            approval_state="approved",
            confidence=0.9,
        )
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any")

        assert len(result) == 2
        assert result[0]["content"] == "approved"
        assert result[1]["content"] == "pending"

    # AC1: within same scope + state, higher confidence first (DESC)
    @pytest.mark.asyncio
    async def test_within_same_tier_and_state_higher_confidence_first(self) -> None:
        """AC1: entries with higher confidence appear first within same scope and state."""
        conn = _make_conn()
        _insert_entry(
            conn,
            content="low",
            scope_agent=None,
            scope_project=None,
            approval_state="pending",
            confidence=0.75,
        )
        _insert_entry(
            conn,
            content="high",
            scope_agent=None,
            scope_project=None,
            approval_state="pending",
            confidence=0.95,
        )
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any")

        assert len(result) == 2
        assert result[0]["content"] == "high"
        assert result[1]["content"] == "low"

    # AC3: deleted entries are excluded
    @pytest.mark.asyncio
    async def test_excludes_deleted_entries(self) -> None:
        """AC3: entries with approval_state='deleted' are never returned."""
        conn = _make_conn()
        _insert_entry(conn, content="active", scope_agent=None, scope_project=None, approval_state="pending")
        _insert_entry(conn, content="removed", scope_agent=None, scope_project=None, approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any")

        contents = [r["content"] for r in result]
        assert "active" in contents
        assert "removed" not in contents, "Deleted entries must be excluded from get_knowledge"

    # AC4: default limit is 50
    @pytest.mark.asyncio
    async def test_limit_defaults_to_50(self) -> None:
        """AC4: when limit is not specified, at most 50 entries are returned."""
        conn = _make_conn()
        for i in range(55):
            _insert_entry(conn, content=f"entry-{i}", scope_agent=None, scope_project=None)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any")

        assert len(result) <= 50, f"Default limit must be 50, got {len(result)}"

    # AC4: boundary — exactly 50 entries with limit default
    @pytest.mark.asyncio
    async def test_limit_default_returns_exactly_50_when_available(self) -> None:
        """AC4: exactly 50 entries returned (not fewer) when 50+ entries exist."""
        conn = _make_conn()
        for i in range(55):
            _insert_entry(conn, content=f"entry-{i}", scope_agent=None, scope_project=None)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any")

        assert len(result) == 50, f"Expected exactly 50 entries, got {len(result)}"

    # AC4: explicit limit parameter overrides default
    @pytest.mark.asyncio
    async def test_explicit_limit_caps_result_count(self) -> None:
        """AC4: explicit limit parameter caps result to the given number."""
        conn = _make_conn()
        for i in range(10):
            _insert_entry(conn, content=f"entry-{i}", scope_agent=None, scope_project=None)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any", limit=3)

        assert len(result) == 3, f"Expected 3 results with limit=3, got {len(result)}"

    # AC5: filter by single category
    @pytest.mark.asyncio
    async def test_filter_by_single_category(self) -> None:
        """AC5: categories filter returns only entries matching the given category."""
        conn = _make_conn()
        _insert_entry(conn, content="know", category="knowledge", scope_agent=None, scope_project=None)
        _insert_entry(conn, content="pref", category="preference", scope_agent=None, scope_project=None)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any", categories=["knowledge"])

        contents = [r["content"] for r in result]
        assert "know" in contents
        assert "pref" not in contents

    # AC5: filter by multiple categories (OR condition)
    @pytest.mark.asyncio
    async def test_filter_by_multiple_categories(self) -> None:
        """AC5: multiple categories returns entries matching any of them."""
        conn = _make_conn()
        _insert_entry(conn, content="know", category="knowledge", scope_agent=None, scope_project=None)
        _insert_entry(conn, content="pref", category="preference", scope_agent=None, scope_project=None)
        _insert_entry(conn, content="ctx", category="context", scope_agent=None, scope_project=None)
        mcp_ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(mcp_ctx, agent_id="any", categories=["knowledge", "preference"])

        contents = [r["content"] for r in result]
        assert "know" in contents
        assert "pref" in contents
        assert "ctx" not in contents

    # AC5: filter by min_confidence
    @pytest.mark.asyncio
    async def test_filter_by_min_confidence(self) -> None:
        """AC5: min_confidence filter excludes entries below the threshold."""
        conn = _make_conn()
        _insert_entry(conn, content="above", confidence=0.90, scope_agent=None, scope_project=None)
        _insert_entry(conn, content="below", confidence=0.75, scope_agent=None, scope_project=None)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await get_knowledge(ctx, agent_id="any", min_confidence=0.85)

        contents = [r["content"] for r in result]
        assert "above" in contents
        assert "below" not in contents, "Entries below min_confidence must be excluded"


# ---------------------------------------------------------------------------
# TestFromAC_RecordLearning -- AC6-AC10
# ---------------------------------------------------------------------------


class TestFromAC_RecordLearning:
    """Contract tests for record_learning — validation, storage, return value."""

    # AC6: confidence < 0.7 returns soft error string
    @pytest.mark.asyncio
    async def test_rejects_confidence_below_0_7_with_soft_error(self) -> None:
        """AC6: confidence < 0.7 returns an error string, does not raise an exception."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test",
            category="knowledge",
            confidence=0.69,
        )

        assert isinstance(result, str), "record_learning must return str for validation failure"
        assert result.startswith("error:"), f"Expected soft error string starting with 'error:', got {result!r}"

    # AC6: boundary — confidence=0.0 is also below threshold
    @pytest.mark.asyncio
    async def test_rejects_zero_confidence_with_soft_error(self) -> None:
        """AC6: confidence=0.0 is also below 0.7 and must return an error string."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test",
            category="knowledge",
            confidence=0.0,
        )

        assert isinstance(result, str), "confidence=0.0 rejection must return str"
        assert result.startswith("error:"), f"confidence=0.0 must be rejected with soft error, got {result!r}"

    # AC6: boundary — confidence=0.7 is exactly at threshold, must be accepted
    @pytest.mark.asyncio
    async def test_confidence_exactly_0_7_is_accepted(self) -> None:
        """AC6: confidence=0.7 must NOT be rejected (threshold is strictly < 0.7)."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test",
            category="knowledge",
            confidence=0.70,
        )

        assert not (isinstance(result, str) and result.startswith("error:")), (
            f"confidence=0.7 must be accepted, but got an error response: {result!r}"
        )

    # AC7: invalid category returns soft error string
    @pytest.mark.asyncio
    async def test_rejects_invalid_category_with_soft_error(self) -> None:
        """AC7: invalid category returns an error string, does not raise an exception."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test",
            category="invalid_category",
            confidence=0.8,
        )

        assert isinstance(result, str)
        assert result.startswith("error:"), f"Expected soft error string for invalid category, got {result!r}"

    # AC7: all 5 valid categories are accepted
    @pytest.mark.asyncio
    async def test_accepts_all_five_valid_categories(self) -> None:
        """AC7: all 5 valid categories produce a success response."""
        valid_categories = ["preference", "knowledge", "context", "behavior", "goal"]
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        for cat in valid_categories:
            result = await record_learning(
                ctx,
                agent_id="agent1",
                content=f"test-{cat}",
                category=cat,
                confidence=0.8,
            )
            assert not (isinstance(result, str) and result.startswith("error:")), (
                f"Category '{cat}' must be valid, but got error: {result!r}"
            )

    # AC10: success returns bare UUID string
    @pytest.mark.asyncio
    async def test_returns_bare_uuid_string_on_success(self) -> None:
        """AC10: on success, record_learning returns a bare UUID string only."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test",
            category="knowledge",
            confidence=0.8,
        )

        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"
        try:
            parsed = uuid.UUID(result.strip())
        except ValueError:
            pytest.fail(f"Expected bare UUID, got: {result!r}")
        assert str(parsed) == result.strip(), (
            "Returned value must be the UUID string only — no prefix, no JSON wrapping"
        )

    # AC8: returned UUID corresponds to the stored entry
    @pytest.mark.asyncio
    async def test_returned_uuid_matches_stored_entry(self) -> None:
        """AC8: the returned UUID is the id of the entry stored in the database."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        entry_id = await record_learning(
            ctx,
            agent_id="agent1",
            content="stored test",
            category="knowledge",
            confidence=0.8,
        )

        row = conn.execute("SELECT id FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None, f"Entry {entry_id!r} not found in database"

    # AC8: timestamps are set on the new entry
    @pytest.mark.asyncio
    async def test_sets_created_at_and_updated_at(self) -> None:
        """AC8: created_at and updated_at are stored as non-null, non-empty values."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        entry_id = await record_learning(
            ctx,
            agent_id="agent1",
            content="ts test",
            category="knowledge",
            confidence=0.8,
        )

        row = conn.execute(
            "SELECT created_at, updated_at FROM memory_entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        assert row is not None
        assert row[0] not in (None, ""), "created_at must be set"
        assert row[1] not in (None, ""), "updated_at must be set"

    # AC8: source is set to agent_id
    @pytest.mark.asyncio
    async def test_sets_source_to_agent_id(self) -> None:
        """AC8: source field in the stored entry equals the provided agent_id."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        entry_id = await record_learning(
            ctx,
            agent_id="my-agent-007",
            content="src test",
            category="knowledge",
            confidence=0.8,
        )

        row = conn.execute("SELECT source FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None
        assert row[0] == "my-agent-007", f"Expected source='my-agent-007', got {row[0]!r}"

    # AC8: approval_state is 'pending'
    @pytest.mark.asyncio
    async def test_sets_approval_state_pending(self) -> None:
        """AC8: all newly recorded entries are stored with approval_state='pending'."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="proj"))

        entry_id = await record_learning(
            ctx,
            agent_id="agent1",
            content="state test",
            category="knowledge",
            confidence=0.8,
        )

        row = conn.execute("SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None
        assert row[0] == "pending", f"Expected approval_state='pending', got {row[0]!r}"

    # AC9: scope_project defaults to AppContext.project_name when not provided
    @pytest.mark.asyncio
    async def test_defaults_scope_project_from_app_context(self) -> None:
        """AC9: when scope_project is None, AppContext.project_name is used."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="owlbear-default"))

        entry_id = await record_learning(
            ctx,
            agent_id="agent1",
            content="proj test",
            category="knowledge",
            confidence=0.8,
            # scope_project intentionally omitted
        )

        row = conn.execute("SELECT scope_project FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None
        assert row[0] == "owlbear-default", f"Expected scope_project='owlbear-default' from AppContext, got {row[0]!r}"

    # AC9: explicit scope_project overrides AppContext.project_name
    @pytest.mark.asyncio
    async def test_explicit_scope_project_overrides_context(self) -> None:
        """AC9: explicit scope_project takes precedence over AppContext.project_name."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn, project_name="default-proj"))

        entry_id = await record_learning(
            ctx,
            agent_id="agent1",
            content="override test",
            category="knowledge",
            confidence=0.8,
            scope_project="override-proj",
        )

        row = conn.execute("SELECT scope_project FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None
        assert row[0] == "override-proj", f"Expected scope_project='override-proj', got {row[0]!r}"


# ---------------------------------------------------------------------------
# TestFromAC_ListEntries -- AC11-AC12
# ---------------------------------------------------------------------------


class TestFromAC_ListEntries:
    """Contract tests for list_entries — filtering and deleted-entry exclusion."""

    # AC11: filter by agent_id
    @pytest.mark.asyncio
    async def test_filter_by_agent_id(self) -> None:
        """AC11: agent_id filter returns only entries scoped to that agent."""
        conn = _make_conn()
        _insert_entry(conn, content="agent-a", scope_agent="agent-a")
        _insert_entry(conn, content="agent-b", scope_agent="agent-b")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await list_entries(ctx, agent_id="agent-a")

        assert isinstance(result, list)
        contents = [r["content"] for r in result]
        assert "agent-a" in contents
        assert "agent-b" not in contents

    # AC11: filter by category
    @pytest.mark.asyncio
    async def test_filter_by_category(self) -> None:
        """AC11: category filter returns only entries with that category value."""
        conn = _make_conn()
        _insert_entry(conn, content="know", category="knowledge")
        _insert_entry(conn, content="pref", category="preference")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await list_entries(ctx, category="knowledge")

        contents = [r["content"] for r in result]
        assert "know" in contents
        assert "pref" not in contents

    # AC11: filter by status (approval_state)
    @pytest.mark.asyncio
    async def test_filter_by_status_approved(self) -> None:
        """AC11: status='approved' filter returns only approved entries."""
        conn = _make_conn()
        _insert_entry(conn, content="approved-entry", approval_state="approved")
        _insert_entry(conn, content="pending-entry", approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await list_entries(ctx, status="approved")

        contents = [r["content"] for r in result]
        assert "approved-entry" in contents
        assert "pending-entry" not in contents

    # AC11: multiple filters applied together (AND semantics)
    @pytest.mark.asyncio
    async def test_combined_filters_are_and_conditions(self) -> None:
        """AC11: multiple filters are ANDed — only entries matching all criteria returned."""
        conn = _make_conn()
        _insert_entry(conn, content="match", scope_agent="agent1", category="knowledge", approval_state="approved")
        _insert_entry(
            conn, content="wrong-category", scope_agent="agent1", category="preference", approval_state="approved"
        )
        _insert_entry(
            conn, content="wrong-agent", scope_agent="agent2", category="knowledge", approval_state="approved"
        )
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await list_entries(ctx, agent_id="agent1", category="knowledge", status="approved")

        contents = [r["content"] for r in result]
        assert "match" in contents
        assert "wrong-category" not in contents
        assert "wrong-agent" not in contents

    # AC12: deleted excluded by default
    @pytest.mark.asyncio
    async def test_excludes_deleted_entries_by_default(self) -> None:
        """AC12: entries with approval_state='deleted' are excluded from default results."""
        conn = _make_conn()
        _insert_entry(conn, content="active", approval_state="pending")
        _insert_entry(conn, content="dead", approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await list_entries(ctx)

        contents = [r["content"] for r in result]
        assert "active" in contents
        assert "dead" not in contents, "Deleted entries must be excluded by default"

    # AC12: include_deleted=True includes deleted entries
    @pytest.mark.asyncio
    async def test_includes_deleted_when_flag_set(self) -> None:
        """AC12: include_deleted=True causes deleted entries to appear in results."""
        conn = _make_conn()
        _insert_entry(conn, content="active", approval_state="pending")
        _insert_entry(conn, content="dead", approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await list_entries(ctx, include_deleted=True)

        contents = [r["content"] for r in result]
        assert "active" in contents
        assert "dead" in contents, "Deleted entries must appear when include_deleted=True"

    # AC12: no filters returns all non-deleted
    @pytest.mark.asyncio
    async def test_no_filters_returns_all_non_deleted_entries(self) -> None:
        """AC12: with no arguments, list_entries returns all non-deleted entries."""
        conn = _make_conn()
        for i in range(5):
            _insert_entry(conn, content=f"entry-{i}", approval_state="pending")
        _insert_entry(conn, content="deleted", approval_state="deleted")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        result = await list_entries(ctx)

        assert len(result) == 5, f"Expected 5 non-deleted entries, got {len(result)}"


# ---------------------------------------------------------------------------
# TestFromAC_MarkForDeletion -- AC13-AC15
# ---------------------------------------------------------------------------


class TestFromAC_MarkForDeletion:
    """Contract tests for mark_for_deletion — state transition, idempotence, error."""

    # AC13: approval_state set to 'deleted'
    @pytest.mark.asyncio
    async def test_sets_approval_state_to_deleted(self) -> None:
        """AC13: mark_for_deletion sets the entry's approval_state to 'deleted'."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, content="to delete", approval_state="pending")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await mark_for_deletion(ctx, entry_id=entry_id)

        row = conn.execute("SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None
        assert row[0] == "deleted", f"Expected approval_state='deleted', got {row[0]!r}"

    # AC13: deleted_at is set to a non-null timestamp
    @pytest.mark.asyncio
    async def test_sets_deleted_at_timestamp(self) -> None:
        """AC13: mark_for_deletion sets deleted_at to a non-null timestamp."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, content="to delete", deleted_at=None)
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await mark_for_deletion(ctx, entry_id=entry_id)

        row = conn.execute("SELECT deleted_at FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None
        assert row[0] not in (None, ""), "deleted_at must be set to a non-null timestamp"

    # AC13: updated_at is refreshed
    @pytest.mark.asyncio
    async def test_updates_updated_at_timestamp(self) -> None:
        """AC13: mark_for_deletion refreshes updated_at."""
        conn = _make_conn()
        entry_id = _insert_entry(conn, content="update me", updated_at="2026-01-01T00:00:00Z")
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        await mark_for_deletion(ctx, entry_id=entry_id)

        row = conn.execute("SELECT updated_at FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row is not None
        assert row[0] != "2026-01-01T00:00:00Z", "updated_at must be refreshed by mark_for_deletion"

    # AC14: idempotent — no error on re-deletion
    @pytest.mark.asyncio
    async def test_is_idempotent_when_already_deleted(self) -> None:
        """AC14: calling mark_for_deletion on an already-deleted entry does not raise."""
        conn = _make_conn()
        entry_id = _insert_entry(
            conn,
            content="already gone",
            approval_state="deleted",
            deleted_at="2026-01-01T00:00:00Z",
        )
        ctx = _make_mcp_ctx(_make_app_ctx(conn))

        # Must not raise — second call is a no-op
        await mark_for_deletion(ctx, entry_id=entry_id)

        row = conn.execute("SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)).fetchone()
        assert row[0] == "deleted"

    # AC15: ToolError for nonexistent entry_id
    @pytest.mark.asyncio
    async def test_raises_tool_error_for_nonexistent_entry_id(self) -> None:
        """AC15: ToolError is raised when entry_id does not exist in the database."""
        conn = _make_conn()
        ctx = _make_mcp_ctx(_make_app_ctx(conn))
        nonexistent_id = str(uuid.uuid4())

        with pytest.raises(ToolError):
            await mark_for_deletion(ctx, entry_id=nonexistent_id)


# ---------------------------------------------------------------------------
# TestFromAC_ApplyToolExclusions — AC16
# ---------------------------------------------------------------------------


class TestFromAC_ApplyToolExclusions:
    """Contract tests for _apply_tool_exclusions — reads MEMORY_TOOLS_EXCLUDE."""

    def _make_server(self) -> MagicMock:
        server = MagicMock()
        server.remove_tool = MagicMock()
        return server

    # AC16: reads MEMORY_TOOLS_EXCLUDE and removes listed tools
    def test_reads_memory_tools_exclude_env_var(self) -> None:
        """AC16: _apply_tool_exclusions reads MEMORY_TOOLS_EXCLUDE and calls remove_tool."""
        server = self._make_server()
        with patch.dict(os.environ, {"MEMORY_TOOLS_EXCLUDE": "get_knowledge"}):
            _apply_tool_exclusions(server)
        server.remove_tool.assert_called_once_with("get_knowledge")

    # AC16: comma-separated list — remove_tool called for each name
    def test_excludes_multiple_comma_separated_tools(self) -> None:
        """AC16: comma-separated list causes remove_tool to be called for each name."""
        server = self._make_server()
        with patch.dict(
            os.environ,
            {"MEMORY_TOOLS_EXCLUDE": "get_knowledge,record_learning"},
        ):
            _apply_tool_exclusions(server)

        assert server.remove_tool.call_count == 2
        called = {c.args[0] for c in server.remove_tool.call_args_list}
        assert called == {"get_knowledge", "record_learning"}

    # AC16: no-op when env var is not set
    def test_no_op_when_env_var_not_set(self) -> None:
        """AC16: when MEMORY_TOOLS_EXCLUDE is absent, remove_tool is never called."""
        server = self._make_server()
        env_without = {k: v for k, v in os.environ.items() if k != "MEMORY_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            _apply_tool_exclusions(server)
        server.remove_tool.assert_not_called()

    # AC16: empty env var is a no-op
    def test_no_op_when_env_var_empty(self) -> None:
        """AC16: MEMORY_TOOLS_EXCLUDE='' does not call remove_tool."""
        server = self._make_server()
        with patch.dict(os.environ, {"MEMORY_TOOLS_EXCLUDE": ""}):
            _apply_tool_exclusions(server)
        server.remove_tool.assert_not_called()

    # AC16: silently ignores unknown tool names
    def test_silently_ignores_unknown_tool_names(self) -> None:
        """AC16: exception from remove_tool for an unknown name is swallowed."""
        server = self._make_server()
        server.remove_tool.side_effect = Exception("no such tool: nonexistent_tool")
        with patch.dict(os.environ, {"MEMORY_TOOLS_EXCLUDE": "nonexistent_tool"}):
            _apply_tool_exclusions(server)  # must not propagate

    # AC16: whitespace is stripped from each tool name
    def test_whitespace_stripped_from_each_name(self) -> None:
        """AC16: leading/trailing whitespace around each tool name is stripped."""
        server = self._make_server()
        with patch.dict(
            os.environ,
            {"MEMORY_TOOLS_EXCLUDE": " get_knowledge , record_learning "},
        ):
            _apply_tool_exclusions(server)

        called = {c.args[0] for c in server.remove_tool.call_args_list}
        assert "get_knowledge" in called
        assert "record_learning" in called
        assert not any(" " in n for n in called), "Tool names passed to remove_tool must have no surrounding whitespace"

    # AC16: valid + invalid names — valid ones still excluded
    def test_valid_names_still_excluded_when_mixed_with_invalid(self) -> None:
        """AC16: even when one name is invalid, valid names are still removed."""
        log: list[str] = []

        def _selective_remove(name: str) -> None:
            if name == "no_such_tool":
                msg = "unknown tool"
                raise ValueError(msg)
            log.append(name)

        server = self._make_server()
        server.remove_tool.side_effect = _selective_remove
        with patch.dict(
            os.environ,
            {"MEMORY_TOOLS_EXCLUDE": "get_knowledge,no_such_tool,list_entries"},
        ):
            _apply_tool_exclusions(server)

        assert "get_knowledge" in log
        assert "list_entries" in log


# ---------------------------------------------------------------------------
# TestFromAC_ToolAnnotations — AC17
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> Any | None:
    """Return the ToolAnnotations for a named tool on the mcp instance, or None."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # type: ignore[union-attr]
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


class TestFromAC_ToolAnnotations:
    """Contract tests verifying ToolAnnotations are registered on all 4 memory tools."""

    # AC17: all 4 tools have annotations (not None)
    @pytest.mark.parametrize(
        "tool_name",
        ["get_knowledge", "record_learning", "list_entries", "mark_for_deletion"],
    )
    def test_tool_has_annotations(self, tool_name: str) -> None:
        """AC17: every memory-mcp tool must have ToolAnnotations registered."""
        ann = _get_tool_annotations(tool_name)
        assert ann is not None, (
            f"Tool '{tool_name}' has no ToolAnnotations; "
            "add annotations=ToolAnnotations(...) to its @mcp.tool() decorator"
        )

    # AC17: get_knowledge — readOnlyHint=True
    def test_get_knowledge_is_read_only(self) -> None:
        """AC17: get_knowledge is a read-only query — readOnlyHint must be True."""
        ann = _get_tool_annotations("get_knowledge")
        assert ann is not None, "get_knowledge has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for get_knowledge, got {ann.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    # AC17: get_knowledge — idempotentHint=True
    def test_get_knowledge_is_idempotent(self) -> None:
        """AC17: get_knowledge produces no side-effects — idempotentHint must be True."""
        ann = _get_tool_annotations("get_knowledge")
        assert ann is not None, "get_knowledge has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for get_knowledge, got {ann.idempotentHint!r}"  # type: ignore[union-attr]
        )

    # AC17: list_entries — readOnlyHint=True
    def test_list_entries_is_read_only(self) -> None:
        """AC17: list_entries is a read-only query — readOnlyHint must be True."""
        ann = _get_tool_annotations("list_entries")
        assert ann is not None, "list_entries has no ToolAnnotations"
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for list_entries, got {ann.readOnlyHint!r}"  # type: ignore[union-attr]
        )

    # AC17: list_entries — idempotentHint=True
    def test_list_entries_is_idempotent(self) -> None:
        """AC17: list_entries produces no side-effects — idempotentHint must be True."""
        ann = _get_tool_annotations("list_entries")
        assert ann is not None, "list_entries has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for list_entries, got {ann.idempotentHint!r}"  # type: ignore[union-attr]
        )

    # AC17: record_learning — destructiveHint=False (creates data, not destructive)
    def test_record_learning_is_not_destructive(self) -> None:
        """AC17: record_learning creates new data — destructiveHint must be False."""
        ann = _get_tool_annotations("record_learning")
        assert ann is not None, "record_learning has no ToolAnnotations"
        assert ann.destructiveHint is False, (  # type: ignore[union-attr]
            f"Expected destructiveHint=False for record_learning, got {ann.destructiveHint!r}"  # type: ignore[union-attr]
        )

    # AC17: mark_for_deletion — destructiveHint=True (soft-deletes data)
    def test_mark_for_deletion_is_destructive(self) -> None:
        """AC17: mark_for_deletion removes data — destructiveHint must be True."""
        ann = _get_tool_annotations("mark_for_deletion")
        assert ann is not None, "mark_for_deletion has no ToolAnnotations"
        assert ann.destructiveHint is True, (  # type: ignore[union-attr]
            f"Expected destructiveHint=True for mark_for_deletion, got {ann.destructiveHint!r}"  # type: ignore[union-attr]
        )

    # AC17: mark_for_deletion — idempotentHint=True (safe to call twice)
    def test_mark_for_deletion_is_idempotent(self) -> None:
        """AC17: mark_for_deletion is idempotent — idempotentHint must be True.

        The AC specifies readOnlyHint=False, idempotentHint=True, destructiveHint=True.
        Calling mark_for_deletion twice on the same entry_id is a no-op on the second
        call (already-deleted entries are skipped), so idempotentHint=True is correct.
        Current implementation uses ToolAnnotations(destructiveHint=True) only —
        idempotentHint defaults to None, not True.
        """
        ann = _get_tool_annotations("mark_for_deletion")
        assert ann is not None, "mark_for_deletion has no ToolAnnotations"
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for mark_for_deletion, got {ann.idempotentHint!r}. "  # type: ignore[union-attr]
            "AC requires ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=True). "
            "Fix: change @mcp.tool decorator to include idempotentHint=True."
        )
