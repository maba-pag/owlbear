"""MCP tool implementations for markdown-backed memory entries."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context, FastMCP  # noqa: TC002
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from owlbear_mcp_memory.models import MemoryCategory, MemoryEntry, MemoryState
from owlbear_mcp_memory.server import mcp

if TYPE_CHECKING:
    from owlbear_mcp_memory.engine import MemoryEngine
    from owlbear_mcp_memory.server import AppContext

__all__ = [
    "_apply_tool_exclusions",
    "approve_entry",
    "delete_entry",
    "query_memory",
    "store_learning",
    "update_entry",
]


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _entry_to_dict(entry: MemoryEntry) -> dict[str, Any]:
    return entry.model_dump()


def _engine_from_ctx(ctx: Context) -> MemoryEngine:
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return app_ctx.engine


def _caller_from_ctx(ctx: Context) -> str:
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return app_ctx.caller


def _require_caller(ctx: Context, *, allowed: set[str]) -> None:
    caller = _caller_from_ctx(ctx)
    if caller not in allowed:
        msg = f"Caller '{caller}' is not allowed for this operation"
        raise ToolError(msg)


def _validate_transition(current: MemoryState, target: MemoryState) -> None:
    if current == "deleted" and target != "deleted":
        msg = "Deleted entries cannot be promoted"
        raise ToolError(msg)
    if current == "pending" and target == "approved":
        msg = "pending -> approved is not allowed"
        raise ToolError(msg)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def query_memory(
    ctx: Context,
    states: list[MemoryState] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve entries with curated+approved defaults and quality-first ordering."""
    allowed_states = set(states) if states is not None else {"curated", "approved"}
    entries = [e for e in _engine_from_ctx(ctx).get_entries() if e.state in allowed_states]
    state_rank = {"approved": 0, "curated": 1, "pending": 2, "deleted": 3}
    entries.sort(key=lambda e: (state_rank[e.state], -e.confidence))
    return [_entry_to_dict(entry) for entry in entries]


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def store_learning(  # noqa: PLR0913
    ctx: Context,
    title: str,
    content: str,
    categories: list[MemoryCategory],
    confidence: float,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new memory entry in pending state."""
    now = _now_utc()
    entry = MemoryEntry(
        id=str(uuid.uuid4()),
        title=title,
        categories=categories,
        confidence=confidence,
        state="pending",
        content=content,
        scope_agents=scope_agents,
        created_at=now,
        updated_at=now,
    )
    _engine_from_ctx(ctx).write(entry)
    return _entry_to_dict(entry)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def update_entry(  # noqa: PLR0913
    ctx: Context,
    entry_id: str,
    title: str | None = None,
    content: str | None = None,
    categories: list[MemoryCategory] | None = None,
    confidence: float | None = None,
    state: MemoryState | None = None,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Update mutable entry fields and allow curator-only promotion to curated."""
    _require_caller(ctx, allowed={"curator"})
    engine = _engine_from_ctx(ctx)

    try:
        current = engine.get_entry(entry_id)
    except KeyError as exc:
        raise ToolError(str(exc)) from exc

    next_state = state if state is not None else current.state
    _validate_transition(current.state, next_state)

    now = _now_utc()
    updated = MemoryEntry(
        id=current.id,
        title=title if title is not None else current.title,
        categories=categories if categories is not None else current.categories,
        confidence=confidence if confidence is not None else current.confidence,
        state=next_state,
        content=content if content is not None else current.content,
        scope_agents=scope_agents if scope_agents is not None else current.scope_agents,
        created_at=current.created_at,
        updated_at=now,
    )
    engine.write(updated)
    return _entry_to_dict(updated)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False, idempotentHint=False, destructiveHint=True
    )
)
async def delete_entry(ctx: Context, entry_id: str) -> dict[str, Any]:
    """Mark an entry as deleted (curator only)."""
    _require_caller(ctx, allowed={"curator"})
    engine = _engine_from_ctx(ctx)

    try:
        current = engine.get_entry(entry_id)
    except KeyError as exc:
        raise ToolError(str(exc)) from exc

    _validate_transition(current.state, "deleted")

    now = _now_utc()
    updated = MemoryEntry(
        id=current.id,
        title=current.title,
        categories=current.categories,
        confidence=current.confidence,
        state="deleted",
        content=current.content,
        scope_agents=current.scope_agents,
        created_at=current.created_at,
        updated_at=now,
    )
    engine.write(updated)
    return _entry_to_dict(updated)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False, idempotentHint=False, destructiveHint=False
    )
)
async def approve_entry(ctx: Context, entry_id: str) -> dict[str, Any]:
    """Promote curated entries to approved (user only)."""
    _require_caller(ctx, allowed={"user"})
    engine = _engine_from_ctx(ctx)

    try:
        current = engine.get_entry(entry_id)
    except KeyError as exc:
        raise ToolError(str(exc)) from exc

    if current.state != "curated":
        msg = "Only curated entries can be approved"
        raise ToolError(msg)

    now = _now_utc()
    updated = MemoryEntry(
        id=current.id,
        title=current.title,
        categories=current.categories,
        confidence=current.confidence,
        state="approved",
        content=current.content,
        scope_agents=current.scope_agents,
        created_at=current.created_at,
        updated_at=now,
    )
    engine.write(updated)
    return _entry_to_dict(updated)


def _apply_tool_exclusions(server: FastMCP) -> set[str]:  # pragma: no cover
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
