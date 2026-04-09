"""MCP tool implementations for owlbear-mcp-memory.

Implements 4 tools: get_knowledge, record_learning, list_entries,
mark_for_deletion; plus _apply_tool_exclusions for MEMORY_TOOLS_EXCLUDE.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from mcp.server.fastmcp import Context, FastMCP  # noqa: TC002
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_mcp_memory.server import AppContext, mcp

__all__ = [
    "_VALID_TRANSITIONS",
    "_apply_tool_exclusions",
    "get_knowledge",
    "list_entries",
    "mark_for_deletion",
    "record_learning",
    "set_approval_state",
]

_VALID_CATEGORIES = ("preference", "knowledge", "context", "behavior", "goal")
_MIN_CONFIDENCE: float = 0.7
_VALID_TRANSITIONS: frozenset[tuple[str, str]] = frozenset({
    ("pending", "approved"),
    ("pending", "deleted"),
    ("deleted", "pending"),
})


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def get_knowledge(
    ctx: Context,
    agent_id: str,
    limit: int = 50,
    categories: list[str] | None = None,
    min_confidence: float | None = None,
) -> list[dict[str, Any]]:
    """Retrieve memory entries for the given agent, sorted by scope-specificity.

    Sort order: scope tier ASC (1=most specific), approval_state (approved first),
    confidence DESC. Deleted entries are always excluded.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn
    project_name = app_ctx.project_name

    # --- Scope WHERE clause ---
    scope_params: list[Any] = [agent_id]
    if project_name is not None:
        scope_where = (
            "(scope_agent IS NULL OR scope_agent = ?) "
            "AND (scope_project IS NULL OR scope_project = ?)"
        )
        scope_params.append(project_name)
    else:
        scope_where = (
            "(scope_agent IS NULL OR scope_agent = ?) "
            "AND scope_project IS NULL"
        )

    # --- Extra conditions ---
    extra_conditions: list[str] = ["approval_state != 'deleted'"]
    extra_params: list[Any] = []
    if categories:
        placeholders = ", ".join("?" * len(categories))
        extra_conditions.append(f"category IN ({placeholders})")
        extra_params.extend(categories)
    if min_confidence is not None:
        extra_conditions.append("confidence >= ?")
        extra_params.append(min_confidence)

    where_clause = scope_where + " AND " + " AND ".join(extra_conditions)

    # --- Tier CASE expression for ORDER BY ---
    if project_name is not None:
        tier_case = (
            "CASE "
            "WHEN scope_agent = ? AND scope_project = ? THEN 1 "
            "WHEN scope_agent = ? AND scope_project IS NULL THEN 2 "
            "WHEN scope_agent IS NULL AND scope_project = ? THEN 3 "
            "WHEN scope_agent IS NULL AND scope_project IS NULL THEN 4 "
            "ELSE 5 END"
        )
        tier_params: list[Any] = [agent_id, project_name, agent_id, project_name]
    else:
        tier_case = (
            "CASE "
            "WHEN scope_agent = ? AND scope_project IS NULL THEN 2 "
            "WHEN scope_agent IS NULL AND scope_project IS NULL THEN 4 "
            "ELSE 5 END"
        )
        tier_params = [agent_id]

    sql = f"""
SELECT id, content, category, confidence, created_at, updated_at, source,
       scope_agent, scope_project, approval_state, deleted_at
FROM memory_entries
WHERE {where_clause}
ORDER BY ({tier_case}),
         CASE approval_state WHEN 'approved' THEN 0 ELSE 1 END,
         confidence DESC
LIMIT ?
"""  # noqa: S608
    # Params order matches SQL left-to-right:
    # WHERE scope_params, WHERE extra_params, ORDER BY tier_params, LIMIT
    all_params: list[Any] = scope_params + extra_params + tier_params + [limit]

    def _run_query() -> list:
        return conn.execute(sql, all_params).fetchall()

    rows = await asyncio.to_thread(_run_query)
    return [dict(row) for row in rows]


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def record_learning(  # noqa: PLR0913
    ctx: Context,
    agent_id: str,
    content: str,
    category: str,
    confidence: float,
    scope_agent: str | None = None,
    scope_project: str | None = None,
) -> str:
    """Record a new learning entry in memory.

    Returns a bare UUID string on success, or an 'error: ...' string for
    validation failures (confidence < 0.7 or invalid category).
    """
    if confidence < _MIN_CONFIDENCE:
        return f"error: confidence must be >= {_MIN_CONFIDENCE}, got {confidence}"
    if category not in _VALID_CATEGORIES:
        valid = ", ".join(_VALID_CATEGORIES)
        return f"error: invalid category '{category}'. Valid: {valid}"

    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn

    if scope_project is None:
        scope_project = app_ctx.project_name

    entry_id = str(uuid.uuid4())
    now = _now_utc()
    insert_params = (
        entry_id, content, category, confidence, now, now, agent_id,
        scope_agent, scope_project,
    )

    def _run_insert() -> None:
        conn.execute(
            """INSERT INTO memory_entries
               (id, content, category, confidence, created_at, updated_at, source,
                scope_agent, scope_project, approval_state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            insert_params,
        )
        conn.commit()

    await asyncio.to_thread(_run_insert)
    return entry_id


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_entries(
    ctx: Context,
    agent_id: str | None = None,
    category: str | None = None,
    status: str | None = None,
    *,
    include_deleted: bool = False,
) -> list[dict[str, Any]] | str:
    """List memory entries with optional filters.

    By default excludes deleted entries. Pass include_deleted=True to show them.
    Filters agent_id (scope_agent), category, and status (approval_state) are ANDed.
    Returns an empty JSON array string "[]" when no entries match, so that MCP
    callers always receive at least one TextContent item in the response (FastMCP
    1.26.x gives zero content items for empty list returns).
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn

    conditions: list[str] = []
    params: list[Any] = []

    if not include_deleted:
        conditions.append("approval_state != 'deleted'")

    if agent_id is not None:
        conditions.append("scope_agent = ?")
        params.append(agent_id)

    if category is not None:
        conditions.append("category = ?")
        params.append(category)

    if status is not None:
        conditions.append("approval_state = ?")
        params.append(status)

    where = " AND ".join(conditions) if conditions else "1=1"
    sql = f"""
SELECT id, content, category, confidence, created_at, updated_at, source,
       scope_agent, scope_project, approval_state, deleted_at
FROM memory_entries
WHERE {where}
"""  # noqa: S608

    def _run_query() -> list:
        return conn.execute(sql, params).fetchall()

    rows = await asyncio.to_thread(_run_query)
    results = [dict(row) for row in rows]
    # FastMCP 1.26.x gives zero TextContent items for empty list returns;
    # return "[]" string so MCP callers always receive content[0].
    return results or "[]"


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False, idempotentHint=False, destructiveHint=True
))
async def set_approval_state(
    ctx: Context,
    entry_id: str,
    new_state: Literal["approved", "deleted", "pending"],
) -> str:
    """Transition a memory entry to a new approval_state.

    Allowed transitions: pending→approved, pending→deleted, deleted→pending.
    Returns a success message string on success.
    Raises ToolError for disallowed transitions (including same-state and invalid states).
    Raises ToolError if the entry_id does not exist.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn

    def _get_state() -> str | None:
        r = conn.execute(
            "SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return r[0] if r is not None else None

    current_state = await asyncio.to_thread(_get_state)

    if current_state is None:
        msg = f"Entry {entry_id!r} not found"
        raise ToolError(msg)

    if (current_state, new_state) not in _VALID_TRANSITIONS:
        msg = f"transition from '{current_state}' to '{new_state}' is not allowed"
        raise ToolError(msg)

    now = _now_utc()
    deleted_at: str | None = now if new_state == "deleted" else None

    def _run_update() -> None:
        conn.execute(
            """UPDATE memory_entries
               SET approval_state = ?, updated_at = ?, deleted_at = ?
               WHERE id = ?""",
            (new_state, now, deleted_at, entry_id),
        )
        conn.commit()

    await asyncio.to_thread(_run_update)
    return f"Entry {entry_id!r} transitioned to '{new_state}'"


@mcp.tool(annotations=ToolAnnotations(idempotentHint=True, destructiveHint=True))
async def mark_for_deletion(ctx: Context, entry_id: str) -> str:
    """Soft-delete a memory entry by setting its approval_state to 'deleted'.

    Idempotent: calling on an already-deleted entry is a no-op.
    Raises ToolError if the entry_id does not exist.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    conn = app_ctx.conn

    def _get_state() -> str | None:
        r = conn.execute(
            "SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return r[0] if r is not None else None

    state = await asyncio.to_thread(_get_state)

    if state is None:
        msg = f"Entry {entry_id!r} not found"
        raise ToolError(msg)

    if state == "deleted":
        return f"Entry {entry_id!r} is already deleted (no-op)"

    now = _now_utc()

    def _run_update() -> None:
        conn.execute(
            """UPDATE memory_entries
               SET approval_state = 'deleted', deleted_at = ?, updated_at = ?
               WHERE id = ?""",
            (now, now, entry_id),
        )
        conn.commit()

    await asyncio.to_thread(_run_update)
    return f"Entry {entry_id!r} marked for deletion"


def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Read MEMORY_TOOLS_EXCLUDE env var and remove listed tools from server.

    Silently ignores unknown tool names and whitespace in the list.
    Returns the set of tool names successfully removed.
    """
    excluded: set[str] = set()
    exclude_str = os.environ.get("MEMORY_TOOLS_EXCLUDE", "")
    if not exclude_str.strip():
        return excluded
    for raw in exclude_str.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001, S110
            pass
    return excluded


_apply_tool_exclusions(mcp)
