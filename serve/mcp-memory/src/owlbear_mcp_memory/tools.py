"""MCP tool implementations for markdown-backed memory entries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from owlbear_mcp_memory.models import MemoryCategory, MemoryEntry, MemoryState

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context

    from owlbear_mcp_memory.engine import MemoryEngine

__all__ = [
    "approve_memory",
    "curate_memory",
    "delete_memory",
    "list_memories",
    "read_memory",
    "recall_memory",
    "save_memory",
]


def _engine_from_ctx(ctx: Context) -> MemoryEngine:
    try:
        return ctx.request_context.lifespan_context.engine
    except AttributeError as exc:
        msg = "memory engine is not available in MCP context"
        raise ToolError(msg) from exc


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _allowed_category_values() -> str:
    return ", ".join(str(category) for category in MemoryCategory)


def _allowed_state_values() -> str:
    return ", ".join(str(state) for state in MemoryState)


def _coerce_categories(
    categories: list[MemoryCategory | str] | None,
) -> list[MemoryCategory] | None:
    if categories is None:
        return None
    coerced: list[MemoryCategory] = []
    for category in categories:
        try:
            coerced.append(MemoryCategory(str(category)))
        except ValueError as exc:
            msg = f"Unknown category {category!r}. Use one of: {_allowed_category_values()}."
            raise ToolError(msg) from exc
    return coerced


def _coerce_states(states: list[MemoryState | str] | None) -> list[MemoryState] | None:
    if states is None:
        return None
    coerced: list[MemoryState] = []
    for state in states:
        try:
            coerced.append(MemoryState(str(state)))
        except ValueError as exc:
            msg = f"Unknown state {state!r}. Use one of: {_allowed_state_values()}."
            raise ToolError(msg) from exc
    return coerced


def _validate_limit(limit: int | None) -> int | None:
    if limit is not None and limit < 0:
        msg = "Limit must be zero or greater."
        raise ToolError(msg)
    return limit


def _entry_to_dict(entry: MemoryEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "title": entry.title,
        "categories": [str(category) for category in entry.categories],
        "confidence": entry.confidence,
        "state": str(entry.state),
        "content": entry.content,
        "scope_agents": entry.scope_agents,
        "source_agent": entry.source_agent,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "approved_at": entry.approved_at,
    }


def _load_entry_or_raise(engine: MemoryEngine, entry_id: str) -> MemoryEntry:
    try:
        return engine.get_entry(entry_id)
    except KeyError as exc:
        msg = f"entry not found: {entry_id}"
        raise ToolError(msg) from exc


def _metadata_dict(entry: MemoryEntry) -> dict[str, object]:
    data = _entry_to_dict(entry)
    data.pop("content", None)
    return data


def _state_rank_for_list(state: MemoryState) -> int:
    if state == MemoryState.PENDING:
        return 0
    if state == MemoryState.CURATED:
        return 1
    if state == MemoryState.APPROVED:
        return 2
    return 3


def _teaching_validation_message(exc: ValidationError) -> str:
    for err in exc.errors():
        location = err.get("loc", ())
        field = str(location[-1]) if location else ""
        if field == "title":
            return "Title must be non-empty."
        if field == "content":
            return "Content exceeds 1024-character limit. Split into focused entries."
        if field == "confidence":
            return "Confidence must be between 0.7 and 1.0."
        if "categories" in location:
            return f"Provide at least one category from: {_allowed_category_values()}."
        if field == "source_agent":
            return "Source agent must be non-empty."
    return str(exc)


def _with_hint(data: dict[str, Any], hint: str) -> dict[str, Any]:
    return {**data, "hint": hint}


def _ensure_update_transition(current: MemoryState, target: MemoryState) -> None:
    if current == target:
        return
    allowed: dict[MemoryState, set[MemoryState]] = {
        MemoryState.PENDING: {MemoryState.CURATED},
        MemoryState.CURATED: set(),
        MemoryState.APPROVED: {MemoryState.CURATED},
        MemoryState.DELETED: set(),
    }
    if target in allowed[current]:
        return
    msg = f"invalid state transition for curate_memory: {current} -> {target}"
    raise ToolError(msg)


async def save_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    content: str,
    categories: list[MemoryCategory | str],
    confidence: float,
    source_agent: str,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Create a pending memory entry with explicit source_agent."""
    engine = _engine_from_ctx(ctx)
    now = _now_iso()
    coerced_categories = _coerce_categories(categories)
    initial_scope = scope_agents if scope_agents is not None else [source_agent]
    try:
        entry = MemoryEntry(
            id=str(uuid4()),
            title=title,
            categories=coerced_categories,
            confidence=confidence,
            state=MemoryState.PENDING,
            content=content,
            scope_agents=initial_scope,
            source_agent=source_agent,
            created_at=now,
            updated_at=now,
            approved_at=None,
        )
    except ValidationError as exc:
        raise ToolError(_teaching_validation_message(exc)) from exc
    engine.write(entry)
    hint = (
        "Saved as pending."
        f" Scoped to {initial_scope}."
        " Curate to promote to curated and adjust scope if needed."
    )
    return _with_hint(_entry_to_dict(entry), hint)


async def list_memories(
    ctx: Context,
    *,
    states: list[MemoryState | str] | None = None,
    categories: list[MemoryCategory | str] | None = None,
    scope_agents: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return metadata-only entries with pending-first ordering."""
    engine = _engine_from_ctx(ctx)
    coerced_states = _coerce_states(states)
    coerced_categories = _coerce_categories(categories)
    allowed_states = (
        set(coerced_states)
        if coerced_states
        else {
            MemoryState.PENDING,
            MemoryState.CURATED,
            MemoryState.APPROVED,
        }
    )
    category_filter = set(coerced_categories or [])
    scope_filter = set(scope_agents or [])

    entries = [entry for entry in engine.get_entries() if entry.state in allowed_states]
    if category_filter:
        entries = [
            entry
            for entry in entries
            if bool(category_filter.intersection(set(entry.categories)))
        ]
    if scope_filter:
        entries = [
            entry
            for entry in entries
            if entry.scope_agents
            and bool(
                scope_filter.intersection(set(entry.scope_agents))
                or "*" in entry.scope_agents
            )
        ]

    entries.sort(
        key=lambda entry: (
            _state_rank_for_list(entry.state),
            entry.created_at,
            entry.id,
        )
    )
    return [_metadata_dict(entry) for entry in entries]


async def read_memory(ctx: Context, *, entry_id: str) -> dict[str, Any]:
    """Return a full entry by ID, excluding deleted state."""
    engine = _engine_from_ctx(ctx)
    entry = _load_entry_or_raise(engine, entry_id)
    if entry.state == MemoryState.DELETED:
        msg = f"entry is deleted: {entry_id}"
        raise ToolError(msg)
    return _entry_to_dict(entry)


async def recall_memory(
    ctx: Context,
    *,
    agent: str,
    categories: list[MemoryCategory | str] | None = None,
    limit: int | None = None,
) -> str:
    """Return body-only recall text for a single scoped agent.

    Output format: concatenated markdown blocks using "## {title}" headings
    followed by each entry body.
    """
    if agent == "*":
        msg = 'wildcard agent "*" is not allowed for recall_memory'
        raise ToolError(msg)
    if not agent.strip():
        msg = "Agent must be non-empty."
        raise ToolError(msg)

    engine = _engine_from_ctx(ctx)
    category_filter = set(_coerce_categories(categories) or [])
    capped_limit = 20 if limit is None else _validate_limit(limit)

    state_rank = {
        MemoryState.APPROVED: 0,
        MemoryState.CURATED: 1,
    }
    entries = [
        entry
        for entry in engine.get_entries()
        if entry.state in {MemoryState.APPROVED, MemoryState.CURATED}
    ]
    entries = [
        entry
        for entry in entries
        if entry.scope_agents
        and (agent in entry.scope_agents or "*" in entry.scope_agents)
    ]
    if category_filter:
        entries = [
            entry
            for entry in entries
            if bool(category_filter.intersection(set(entry.categories)))
        ]
    entries.sort(
        key=lambda entry: (state_rank[entry.state], -entry.confidence, entry.id)
    )
    entries = entries[:capped_limit]

    return "\n\n".join(f"## {entry.title}\n{entry.content}" for entry in entries)


async def _update_entry(  # noqa: PLR0913
    ctx: Context,
    *,
    current: MemoryEntry,
    title: str | None = None,
    content: str | None = None,
    categories: list[MemoryCategory | str] | None = None,
    confidence: float | None = None,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Update mutable fields on an existing entry.

    Auto-promotes pending→curated when ``scope_agents`` are provided and
    auto-downgrades approved→curated.
    """
    engine = _engine_from_ctx(ctx)
    coerced_categories = _coerce_categories(categories)

    if current.state == MemoryState.DELETED:
        msg = "update_entry cannot modify deleted entries"
        raise ToolError(msg)

    next_scope_agents = current.scope_agents if scope_agents is None else scope_agents
    if current.state == MemoryState.PENDING and not next_scope_agents:
        msg = "scope_agents are required when curating pending entries"
        raise ToolError(msg)
    if (
        current.state != MemoryState.PENDING
        and scope_agents is not None
        and not scope_agents
    ):
        msg = "scope_agents cannot be blanked on curated or approved entries"
        raise ToolError(msg)

    if current.state == MemoryState.APPROVED or (
        current.state == MemoryState.PENDING and bool(next_scope_agents)
    ):
        target_state = MemoryState.CURATED
    else:
        target_state = current.state

    _ensure_update_transition(current.state, target_state)

    payload = {
        "id": current.id,
        "title": current.title if title is None else title,
        "content": current.content if content is None else content,
        "categories": current.categories if categories is None else coerced_categories,
        "confidence": current.confidence if confidence is None else confidence,
        "state": target_state,
        "scope_agents": next_scope_agents,
        "source_agent": current.source_agent,
        "created_at": current.created_at,
        "updated_at": _now_iso(),
        "approved_at": None
        if current.state == MemoryState.APPROVED
        else current.approved_at,
    }
    try:
        updated = MemoryEntry.model_validate(payload)
    except ValidationError as exc:
        raise ToolError(_teaching_validation_message(exc)) from exc
    engine.write(updated)
    return _entry_to_dict(updated)


async def _delete_entry(ctx: Context, *, entry_id: str) -> dict[str, Any]:
    """Delete an entry.

    Pending entries are hard-deleted from disk; curated and approved entries
    are soft-deleted to deleted state.
    """
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)

    if current.state == MemoryState.DELETED:
        msg = "delete_memory cannot delete an entry that is already deleted"
        raise ToolError(msg)

    if current.state == MemoryState.PENDING:
        engine.delete(current.id)
        deleted = current.model_copy(
            update={
                "state": MemoryState.DELETED,
                "updated_at": _now_iso(),
                "approved_at": None,
            }
        )
        return _entry_to_dict(deleted)

    updated = current.model_copy(
        update={
            "state": MemoryState.DELETED,
            "updated_at": _now_iso(),
            "approved_at": None,
        }
    )
    engine.write(updated)
    return _entry_to_dict(updated)


async def curate_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    entry_id: str,
    title: str | None = None,
    content: str | None = None,
    categories: list[MemoryCategory | str] | None = None,
    confidence: float | None = None,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:
    """Curate entries using code-managed lifecycle transitions."""
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)
    updated = await _update_entry(
        ctx,
        current=current,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        scope_agents=scope_agents,
    )
    if current.state == MemoryState.PENDING and updated["state"] == str(
        MemoryState.CURATED
    ):
        hint = "Promoted from pending to curated with explicit scope."
    elif current.state == MemoryState.APPROVED and updated["state"] == str(
        MemoryState.CURATED
    ):
        hint = "Downgraded from approved to curated; re-approve after review."
    else:
        hint = "Curated entry updated."
    return _with_hint(updated, hint)


async def delete_memory(ctx: Context, *, entry_id: str) -> dict[str, Any]:
    """Compatibility alias for delete semantics."""
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)
    deleted = await _delete_entry(ctx, entry_id=entry_id)
    if current.state == MemoryState.PENDING:
        hint = "Hard-delete applied: pending entry removed and never committed."
    else:
        hint = "Soft-delete applied: entry retained for audit history."
    return _with_hint(deleted, hint)


async def _approve_entry(ctx: Context, *, entry_id: str) -> dict[str, Any]:
    """Promote a curated entry to approved."""
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)

    if current.state != MemoryState.CURATED:
        msg = f"approve_memory requires curated state, got {current.state}"
        raise ToolError(msg)

    updated = current.model_copy(
        update={
            "state": MemoryState.APPROVED,
            "updated_at": _now_iso(),
            "approved_at": _now_iso(),
        }
    )
    engine.write(updated)
    return _entry_to_dict(updated)


async def approve_memory(ctx: Context, *, entry_id: str) -> dict[str, Any]:
    """Compatibility alias for approving curated memory entries."""
    approved = await _approve_entry(ctx, entry_id=entry_id)
    return _with_hint(approved, "Entry approved. Now visible to scoped agents.")
