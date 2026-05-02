"""MCP tool implementations for markdown-backed memory entries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_memory.models import MemoryCategory, MemoryEntry, MemoryState

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context

    from owlbear_mcp_memory.engine import MemoryEngine

__all__ = [
    "approve_entry",
    "delete_entry",
    "query_memory",
    "store_learning",
    "update_entry",
]


def _engine_from_ctx(ctx: Context) -> MemoryEngine:
    try:
        return ctx.request_context.lifespan_context.engine
    except AttributeError as exc:
        msg = "memory engine is not available in MCP context"
        raise ToolError(msg) from exc


def _caller_from_ctx(ctx: Context) -> str:
    caller = getattr(ctx.request_context.lifespan_context, "caller", "")
    return str(caller or "")


def _require_role(ctx: Context, *, allowed: set[str], tool_name: str) -> None:
    caller = _caller_from_ctx(ctx)
    if caller in allowed:
        return
    allowed_text = ", ".join(sorted(allowed))
    msg = (
        f"{tool_name} is restricted to [{allowed_text}] "
        f"but caller is {caller or 'unknown'}"
    )
    raise ToolError(msg)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _entry_to_dict(entry: MemoryEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "title": entry.title,
        "categories": list(entry.categories),
        "confidence": entry.confidence,
        "state": entry.state,
        "content": entry.content,
        "scope_agents": entry.scope_agents,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


def _load_entry_or_raise(engine: MemoryEngine, entry_id: str) -> MemoryEntry:
    try:
        return engine.get_entry(entry_id)
    except KeyError as exc:
        msg = f"entry not found: {entry_id}"
        raise ToolError(msg) from exc


def _ensure_update_transition(current: MemoryState, target: MemoryState) -> None:
    if current == target:
        return
    allowed: dict[MemoryState, set[MemoryState]] = {
        "pending": {"curated"},
        "curated": set(),
        "approved": set(),
        "deleted": set(),
    }
    if target in allowed[current]:
        return
    msg = f"invalid state transition for update_entry: {current} -> {target}"
    raise ToolError(msg)


async def store_learning(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    content: str,
    categories: list[MemoryCategory],
    confidence: float,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new pending memory entry."""
    engine = _engine_from_ctx(ctx)
    now = _now_iso()
    entry = MemoryEntry(
        id=str(uuid4()),
        title=title,
        categories=categories,
        confidence=confidence,
        state="pending",
        content=content,
        scope_agents=scope_agents,
        created_at=now,
        updated_at=now,
    )
    engine.write(entry)
    return _entry_to_dict(entry)


async def query_memory(
    ctx: Context,
    *,
    states: list[MemoryState] | None = None,
) -> list[dict[str, Any]]:
    """Return memory entries filtered by state and sorted by curation priority."""
    engine = _engine_from_ctx(ctx)
    allowed_states = set(states) if states else {"curated", "approved"}

    state_rank = {"approved": 0, "curated": 1, "pending": 2, "deleted": 3}
    entries = [e for e in engine.get_entries() if e.state in allowed_states]
    entries.sort(key=lambda e: (state_rank.get(e.state, 99), -e.confidence, e.id))
    return [_entry_to_dict(entry) for entry in entries]


async def update_entry(  # noqa: PLR0913
    ctx: Context,
    *,
    entry_id: str,
    title: str | None = None,
    content: str | None = None,
    categories: list[MemoryCategory] | None = None,
    confidence: float | None = None,
    state: MemoryState | None = None,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Update mutable fields on an existing entry (curator-only)."""
    _require_role(ctx, allowed={"curator"}, tool_name="update_entry")
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)
    target_state = state or current.state
    _ensure_update_transition(current.state, target_state)

    updated = current.model_copy(
        update={
            "title": current.title if title is None else title,
            "content": current.content if content is None else content,
            "categories": current.categories if categories is None else categories,
            "confidence": current.confidence if confidence is None else confidence,
            "state": target_state,
            "scope_agents": current.scope_agents if scope_agents is None else scope_agents,
            "updated_at": _now_iso(),
        }
    )
    engine.write(updated)
    return _entry_to_dict(updated)


async def delete_entry(ctx: Context, *, entry_id: str) -> dict[str, Any]:
    """Mark an entry as deleted (curator-only)."""
    _require_role(ctx, allowed={"curator"}, tool_name="delete_entry")
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)

    if current.state == "deleted":
        return _entry_to_dict(current)

    updated = current.model_copy(update={"state": "deleted", "updated_at": _now_iso()})
    engine.write(updated)
    return _entry_to_dict(updated)


async def approve_entry(ctx: Context, *, entry_id: str) -> dict[str, Any]:
    """Promote a curated entry to approved (user-only)."""
    _require_role(ctx, allowed={"user"}, tool_name="approve_entry")
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)

    if current.state != "curated":
        msg = f"approve_entry requires curated state, got {current.state}"
        raise ToolError(msg)

    updated = current.model_copy(update={"state": "approved", "updated_at": _now_iso()})
    engine.write(updated)
    return _entry_to_dict(updated)
