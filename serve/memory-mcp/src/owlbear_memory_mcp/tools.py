"""MCP tool implementations for markdown-backed memory entries."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Annotated, Any, Literal, cast

from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import (
    ConcurrencyError,
    DuplicateEntryError,
    LifecycleRecoveryError,
    MemoryBusyError,
    MemoryCategory,
    MemoryEngine,
    MemoryEntry,
    MemoryState,
    NotFoundError,
    TransitionError,
    Where,
    selection,
    storage,
    validate_scope_agents,
    writer_lock,
)
from owlbear_memory import (
    ValidationError as MemoryValidationError,
)
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator

from owlbear_memory_mcp.git import commit_batch, commit_move, format_git_failure, repo_locked

if TYPE_CHECKING:
    from mcp.server.mcpserver import Context

__all__ = [
    "SLOT_CHALLENGE",
    "SLOT_EXPLORE",
    "approve_memory",
    "assess_memories",
    "commit_memory_batch",
    "curate_memory",
    "curation_threshold",
    "delete_agent_memories",
    "delete_memory",
    "list_memories",
    "make_global",
    "read_memory",
    "recall_memory",
    "rename_agent_memories",
    "save_memory",
]

SLOT_EXPLORE = 2
SLOT_CHALLENGE = 2
GLOBAL = "memory"  # Global memory: the shared repository's own memory folder (TD-241)
FOLDER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")  # a project folder's name in the shared repository
CONFIG = "config.json"  # the global settings, which hold the curator's threshold (TD-400)
UNSET_THRESHOLD = "the curator's confidence threshold is unset; the owner sets it on the Settings page"
_WITNESSES = frozenset({MemoryState.CURATED, MemoryState.APPROVED})  # entries whose scope vouches for a named agent
AssessmentTaskId = Annotated[StrictStr, Field(pattern=r"^[\x21-\x7e]{1,128}$")]


class AssessmentItem(BaseModel):
    """Strict input shape for one revision-bound assessment."""

    model_config = ConfigDict(extra="forbid", strict=True)

    entry_id: StrictStr
    revision: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{16}$")]
    bucket: Literal["outstanding", "unremarkable", "didnt_use", "factually_wrong"]


class _AssessmentBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    assessments: list[AssessmentItem] = Field(min_length=1)
    task_id: AssessmentTaskId

    @field_validator("task_id")
    @classmethod
    def _validate_task_id(cls, value: str) -> str:
        if any(not "!" <= character <= "~" for character in value):
            msg = "task_id must be 1-128 printable ASCII characters without whitespace"
            raise ValueError(msg)
        return value


_LOGGER = logging.getLogger(__name__)


def _engine_from_ctx(ctx: Context) -> MemoryEngine:
    try:
        return ctx.request_context.lifespan_context.engine
    except AttributeError as exc:
        msg = "memory engine is not available in MCP context"
        raise ToolError(msg) from exc


def _global_engine(ctx: Context) -> MemoryEngine | None:
    """Global memory's engine, opened once its folder exists: the owner's first Make global may create it later."""
    context = ctx.request_context.lifespan_context
    engine, folder = getattr(context, "global_engine", None), getattr(context, "global_dir", None)
    if engine is None and folder is not None and folder.is_dir():
        engine = context.global_engine = MemoryEngine(folder)
    return engine


def _readable(ctx: Context) -> list[MemoryEntry]:
    """The store's entries, then Global memory's ones it does not hold: what agents read (TD-241)."""
    entries = _engine_from_ctx(ctx).get_entries()
    shared = _global_engine(ctx)
    if shared is None:
        return entries
    mine = {entry.id for entry in entries}
    return entries + [entry for entry in shared.get_entries() if entry.id not in mine]


def _shared_root(ctx: Context) -> Path | None:
    """The shared repository whose project folder this server is bound to, beside its Global memory (TD-72, TD-241)."""
    common = getattr(ctx.request_context.lifespan_context, "global_dir", None)
    root = _memory_dir_from_ctx(ctx).parent.parent
    return root if common is not None and Path(common) == root / GLOBAL else None


def _in_folder(ctx: Context, folder: str | None) -> Context:
    """The context of another project folder of the shared repository, for the curator; the bound one for None."""
    if folder is None:
        return ctx
    root = _shared_root(ctx)
    if root is None:
        msg = "this memory server is bound to no shared repository: it works on its own folder only"
        raise ToolError(msg)
    if not FOLDER.fullmatch(folder) or folder == GLOBAL:
        msg = f"{folder!r} is no project folder of the shared repository; Global memory changes only by make_global"
        raise ToolError(msg)
    path = root / folder / "memory"
    real = path.resolve() if path.is_dir() and not (path.is_symlink() or path.parent.is_symlink()) else None
    if real is None or real.parent.parent != root.resolve() or real == (root / GLOBAL).resolve():
        msg = f"the shared repository has no memory folder for {folder}"  # links never lead to Global or elsewhere
        raise ToolError(msg)
    base = ctx.request_context.lifespan_context
    swapped = SimpleNamespace(
        engine=MemoryEngine(path), memory_dir=path, global_dir=base.global_dir,
        global_engine=getattr(base, "global_engine", None), agents=getattr(base, "agents", frozenset()),
    )  # fmt: skip
    return cast("Context", SimpleNamespace(request_context=SimpleNamespace(lifespan_context=swapped)))


def _memory_dir_from_ctx(ctx: Context) -> Path:
    try:
        memory_dir = ctx.request_context.lifespan_context.memory_dir
    except AttributeError as exc:
        msg = "memory directory is not available in MCP context"
        raise ToolError(msg) from exc
    if not isinstance(memory_dir, Path):
        msg = "memory directory is not available in MCP context"
        raise ToolError(msg)
    return memory_dir


def _validate_scope(agents: list[str]) -> None:
    """Validate nonblank named and universal scope values."""
    try:
        validate_scope_agents(agents)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def _uncorroborated(ctx: Context, current: MemoryEntry, scope: list[str]) -> list[str]:
    """Named members a pending entry's scope keeps, or a reviewed entry's scope adds, that nothing vouches for.

    A member is vouched for by the server's known agents or by another curated or approved entry, here or in Global
    memory, that has it in scope; provenance never vouches, and neither does a pending or exceptional entry.
    """
    named = {agent for agent in scope if agent != "*"}
    if current.state != MemoryState.PENDING:
        named -= set(current.scope_agents)
    if not named:
        return []
    known = getattr(ctx.request_context.lifespan_context, "agents", frozenset())
    vouched = {
        agent
        for entry in _readable(ctx)
        if entry.state in _WITNESSES and entry.id != current.id
        for agent in entry.scope_agents
    }
    return sorted(named - known - vouched)


def _recognized_agent_names(entries: list[MemoryEntry]) -> list[str]:
    """Return sorted non-universal provenance and scope names on live memories."""
    return sorted(
        {
            name
            for entry in entries
            if entry.state != MemoryState.DELETED
            for name in [entry.source_agent, *entry.scope_agents]
            if name and name != "*"
        }
    )


def _recall_fallback(known_agents: list[str]) -> str:
    """Render the universal-only guidance for an unrecognized caller."""
    names = ", ".join(known_agents) or "none discovered"
    return (
        f"This recall_memory caller is not recognized from stored memory data. Known agents: {names}. "
        "It receives only memories scoped to all agents (*); recognition is relevance scoping, "
        "not write authorization."
    )


def _recall_block(entry: MemoryEntry) -> str:
    """Render one recall block with challenge context when required."""
    lines = [f"## {entry.title}", f"Entry ID: `{entry.id}`", f"Revision: `{entry.revision}`"]
    if entry.state == MemoryState.CONTESTED:
        lines.append("State: contested")
        lines.extend(f"Challenge task: `{challenge.task_id}`" for challenge in entry.challenges)
    lines.append(entry.content)
    return "\n".join(lines)


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


def _challenges(entry: MemoryEntry) -> dict[str, object]:
    """The entry's challenge history, or nothing when no task has challenged it."""
    if not entry.challenges:
        return {}
    return {"challenges": [challenge.model_dump(mode="json") for challenge in entry.challenges]}


def _entry_to_dict(entry: MemoryEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "revision": entry.revision,
        "title": entry.title,
        "categories": [str(category) for category in entry.categories],
        "confidence": entry.confidence,
        "state": str(entry.state),
        "content": entry.content,
        "outstanding_count": entry.outstanding_count,
        "unremarkable_count": entry.unremarkable_count,
        "didnt_use_count": entry.didnt_use_count,
        "score": entry.score,
        "scope_agents": entry.scope_agents,
        "source_agent": entry.source_agent,
        "recommended": entry.recommended,
        "origin": entry.origin,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "approved_at": entry.approved_at,
        **_challenges(entry),
    }


def _load_entry_or_raise(engine: MemoryEngine, entry_id: str) -> MemoryEntry:
    try:
        return engine.get_entry(entry_id)
    except NotFoundError as exc:
        msg = f"entry not found: {entry_id}"
        raise ToolError(msg) from exc


def _stale_revision_error(exc: ConcurrencyError) -> ToolError:
    return ToolError(f"Entry changed since it was read: {exc}. Re-read before retrying.")


def _metadata_dict(entry: MemoryEntry) -> dict[str, object]:
    data = _entry_to_dict(entry)
    data.pop("content", None)
    return data


def _state_rank_for_list(state: MemoryState) -> int:
    if state == MemoryState.PENDING:
        return 0
    if state in {MemoryState.CURATED, MemoryState.CONTESTED}:
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


async def save_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    content: str,
    categories: list[MemoryCategory | str],
    confidence: float,
    source_agent: str,
    where: Where,
) -> dict[str, Any]:
    """Create a pending memory entry with explicit source_agent and the saver's recommended scope."""
    engine = _engine_from_ctx(ctx)
    coerced_categories = _coerce_categories(categories)
    try:
        entry = engine.save(
            title=title,
            content=content,
            categories=coerced_categories,
            confidence=confidence,
            scope_agents=[],
            source_agent=source_agent,
            recommended=where,
        )
    except (DuplicateEntryError, ConcurrencyError) as exc:
        raise ToolError(str(exc)) from exc
    except ValidationError as exc:
        raise ToolError(_teaching_validation_message(exc)) from exc
    hint = (
        f"Saved as pending and unscoped in this project, recommended {where}. "
        "The memory curator decides its scope and assigns relevance before promotion."
    )
    return _with_hint(_entry_to_dict(entry), hint)


async def commit_memory_batch(ctx: Context, *, session_type: str, folder: str | None = None) -> dict[str, Any]:
    """Commit non-pending memory entries through the state-aware Git helper."""
    memory_dir = _memory_dir_from_ctx(_in_folder(ctx, folder))
    try:
        result = commit_batch(memory_dir, session_type=session_type)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except subprocess.CalledProcessError as exc:
        detail = format_git_failure(exc)
        _LOGGER.exception("Memory batch commit failed: %s", detail)
        msg = (
            f"memory batch commit failed: {detail}. "
            "Memory paths may remain staged after this failure; inspect Git staging before retrying."
        )
        raise ToolError(msg) from exc
    except OSError as exc:
        detail = f"{type(exc).__name__}: {exc}"
        _LOGGER.exception("Memory batch commit failed: %s", detail)
        msg = f"memory batch commit failed: {detail}"
        raise ToolError(msg) from exc

    committed = result.commit_sha is not None
    hint = "Reviewed memory changes committed." if committed else "No memory changes to commit."
    deferred_deletions = list(result.deferred_deletions)
    if deferred_deletions:
        hint += " Curate the surviving pending entry before retrying the batch commit."
    return {
        "session_type": session_type,
        "commit_sha": result.commit_sha,
        "committed": committed,
        "deferred_deletions": deferred_deletions,
        "hint": hint,
    }


async def list_memories(
    ctx: Context,
    *,
    states: list[MemoryState | str] | None = None,
    categories: list[MemoryCategory | str] | None = None,
    scope_agents: list[str] | None = None,
    folder: str | None = None,
) -> list[dict[str, Any]]:
    """Return metadata-only entries with pending-first ordering."""
    ctx = _in_folder(ctx, folder)
    coerced_states = _coerce_states(states)
    coerced_categories = _coerce_categories(categories)
    allowed_states = (
        set(coerced_states)
        if coerced_states
        else {
            MemoryState.PENDING,
            MemoryState.CURATED,
            MemoryState.APPROVED,
            MemoryState.CONTESTED,
            MemoryState.DISPUTED,
            MemoryState.STALE,
        }
    )
    category_filter = set(coerced_categories or [])
    scope_filter = set(scope_agents or [])
    _validate_scope(list(scope_filter))

    entries = [entry for entry in _readable(ctx) if entry.state in allowed_states]
    if category_filter:
        entries = [entry for entry in entries if bool(category_filter.intersection(set(entry.categories)))]
    if scope_filter:
        entries = [
            entry
            for entry in entries
            if entry.scope_agents
            and bool(scope_filter.intersection(set(entry.scope_agents)) or "*" in entry.scope_agents)
        ]

    entries.sort(
        key=lambda entry: (
            _state_rank_for_list(entry.state),
            entry.created_at,
            entry.id,
        )
    )
    own = {entry.id for entry in _engine_from_ctx(ctx).get_entries()}  # the rest is Global memory, read beside it
    return [_metadata_dict(entry) | {"where": "project" if entry.id in own else "global"} for entry in entries]


async def read_memory(ctx: Context, *, entry_id: str, folder: str | None = None) -> dict[str, Any]:
    """Return a full entry by ID, excluding deleted state."""
    ctx = _in_folder(ctx, folder)
    engine = _engine_from_ctx(ctx)
    shared = _global_engine(ctx)
    where = "project"
    try:
        entry = engine.get_entry(entry_id)
    except NotFoundError:
        entry, where = _load_entry_or_raise(shared or engine, entry_id), "global"  # Global memory, read only
    if entry.state == MemoryState.DELETED:
        msg = f"entry is deleted: {entry_id}"
        raise ToolError(msg)
    return _entry_to_dict(entry) | {"where": where}


async def recall_memory(
    ctx: Context,
    *,
    agent: str | int | None,
    categories: list[MemoryCategory | str] | None = None,
    limit: int | None = None,
) -> str:
    """Return identity-bearing recall text for a single scoped agent.

    Output format: concatenated markdown blocks using "## {title}" headings,
    followed by the entry ID, revision, and body. Contested entries add a state
    marker and one `Challenge task:` line per record between the revision and body.
    """
    category_filter = set(_coerce_categories(categories) or [])
    capped_limit = 20 if limit is None else _validate_limit(limit)
    readable = _readable(ctx)
    known_agents = _recognized_agent_names(readable)
    recognized = isinstance(agent, str) and bool(agent.strip()) and agent != "*" and agent in known_agents

    state_rank = {
        MemoryState.APPROVED: 0,
        MemoryState.CURATED: 1,
        MemoryState.CONTESTED: 1,
    }
    caller = agent if recognized and isinstance(agent, str) else None  # unrecognised: only memories for every agent
    entries = [entry for entry in readable if selection.eligible(entry, caller)]
    if category_filter:
        entries = [entry for entry in entries if bool(category_filter.intersection(set(entry.categories)))]

    explore_capacity = min(SLOT_EXPLORE, capped_limit)
    regular_capacity = max(0, capped_limit - SLOT_EXPLORE - SLOT_CHALLENGE)

    def _explore_metric(entry: MemoryEntry) -> int:
        return entry.outstanding_count + entry.unremarkable_count + entry.didnt_use_count

    explore_pool = sorted(entries, key=lambda entry: (_explore_metric(entry), entry.id))[:explore_capacity]
    selected_ids = {entry.id for entry in explore_pool}

    challenge_capacity = min(SLOT_CHALLENGE, max(0, capped_limit - len(explore_pool)))
    challenge_candidates = [entry for entry in entries if entry.id not in selected_ids]
    challenge_pool = sorted(challenge_candidates, key=lambda entry: (entry.outstanding_count, entry.id))[
        :challenge_capacity
    ]
    selected_ids.update(entry.id for entry in challenge_pool)

    regular_candidates = [entry for entry in entries if entry.id not in selected_ids]
    regular_pool = sorted(regular_candidates, key=lambda entry: (-entry.score, entry.id))[:regular_capacity]

    selected_entries = explore_pool + challenge_pool + regular_pool
    selected_entries.sort(key=lambda entry: (state_rank[entry.state], -entry.score, entry.id))

    blocks = "\n\n".join(_recall_block(entry) for entry in selected_entries)
    if recognized:
        return blocks
    guidance = _recall_fallback(known_agents)
    return f"{guidance}\n\n{blocks}" if blocks else guidance


async def _update_entry(  # noqa: C901, PLR0912, PLR0913
    ctx: Context,
    *,
    current: MemoryEntry,
    revision: str,
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
    if current.state in {MemoryState.CONTESTED, MemoryState.DISPUTED, MemoryState.STALE}:
        msg = f"update_entry cannot modify exceptional entry in state {current.state}"
        raise ToolError(msg)

    next_scope_agents = current.scope_agents if scope_agents is None else scope_agents
    if scope_agents is not None:
        _validate_scope(scope_agents)
    if current.state == MemoryState.PENDING and not next_scope_agents:
        msg = "scope_agents are required when curating pending entries"
        raise ToolError(msg)
    if current.state != MemoryState.PENDING and scope_agents is not None and not scope_agents:
        msg = "scope_agents cannot be blanked on curated or approved entries"
        raise ToolError(msg)
    if missing := _uncorroborated(ctx, current, next_scope_agents):
        names = ", ".join(repr(agent) for agent in missing)
        msg = (
            f"No agent this memory server knows and no other curated or approved entry here or in Global memory has "
            f"{names} in scope; scope the entry to known agents or '*', or skip it. Nothing was changed."
        )
        raise ToolError(msg)

    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if content is not None:
        payload["content"] = content
    if categories is not None:
        payload["categories"] = coerced_categories
    if confidence is not None:
        payload["confidence"] = confidence
    if scope_agents is not None:
        payload["scope_agents"] = scope_agents
    if current.state == MemoryState.PENDING and "scope_agents" not in payload:
        payload["scope_agents"] = next_scope_agents

    try:
        updated = engine.edit(
            current.id,
            payload,
            expected_revision=revision,
        )
    except MemoryBusyError as exc:
        raise ToolError(str(exc)) from exc
    except ConcurrencyError as exc:
        raise _stale_revision_error(exc) from exc
    except (TransitionError, NotFoundError, DuplicateEntryError) as exc:
        raise ToolError(str(exc)) from exc
    except ValidationError as exc:
        raise ToolError(_teaching_validation_message(exc)) from exc
    return _entry_to_dict(updated)


async def _delete_entry(ctx: Context, *, entry_id: str, revision: str) -> dict[str, Any]:
    """Delete an entry.

    Pending entries are hard-deleted from disk; curated and approved entries
    are soft-deleted to deleted state.
    """
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)

    if current.state == MemoryState.DELETED:
        msg = "delete_memory cannot delete an entry that is already deleted"
        raise ToolError(msg)

    try:
        deleted = engine.delete(current.id, expected_revision=revision)
    except MemoryBusyError as exc:
        raise ToolError(str(exc)) from exc
    except ConcurrencyError as exc:
        raise _stale_revision_error(exc) from exc
    except (TransitionError, NotFoundError, DuplicateEntryError) as exc:
        raise ToolError(str(exc)) from exc

    if current.state == MemoryState.PENDING:
        deleted = current.model_copy(
            update={
                "state": MemoryState.DELETED,
            }
        )

    return _entry_to_dict(deleted)


async def curate_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    entry_id: str,
    revision: str,
    title: str | None = None,
    content: str | None = None,
    categories: list[MemoryCategory | str] | None = None,
    confidence: float | None = None,
    scope_agents: list[str] | None = None,
    folder: str | None = None,
) -> dict[str, Any]:
    """Curate entries using code-managed lifecycle transitions."""
    ctx = _in_folder(ctx, folder)
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)
    updated = await _update_entry(
        ctx,
        current=current,
        revision=revision,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        scope_agents=scope_agents,
    )
    if current.state == MemoryState.PENDING and updated["state"] == str(MemoryState.CURATED):
        hint = "Promoted from pending to curated with explicit scope."
    elif current.state == MemoryState.APPROVED and updated["state"] == str(MemoryState.CURATED):
        hint = "Downgraded from approved to curated; re-approve after review."
    else:
        hint = "Curated entry updated."
    return _with_hint(updated, hint)


async def delete_memory(ctx: Context, *, entry_id: str, revision: str, folder: str | None = None) -> dict[str, Any]:
    """Compatibility alias for delete semantics."""
    ctx = _in_folder(ctx, folder)
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)
    deleted = await _delete_entry(ctx, entry_id=entry_id, revision=revision)
    if current.state == MemoryState.PENDING:
        hint = "Hard-delete applied: pending entry removed and never committed."
    else:
        hint = "Soft-delete applied: entry retained for audit history."
    return _with_hint(deleted, hint)


async def rename_agent_memories(ctx: Context, *, old_name: str, new_name: str) -> dict[str, int]:
    """Rewrite all memory references after an agent definition is renamed."""
    if not old_name.strip() or not new_name.strip() or "*" in {old_name, new_name}:
        msg = "old_name and new_name must be distinct non-empty non-wildcard agent names"
        raise ToolError(msg)
    engine = _engine_from_ctx(ctx)
    try:
        result = engine.rename_agent(old_name, new_name)
    except (ConcurrencyError, DuplicateEntryError, LifecycleRecoveryError, ValidationError) as exc:
        raise ToolError(str(exc)) from exc
    if result["entries_updated"] == 0:
        msg = f"No memory references found for agent {old_name!r}."
        raise ToolError(msg)
    return dict(result)


async def delete_agent_memories(ctx: Context, *, agent: str) -> dict[str, int]:
    """Remove a deleted agent from scopes while preserving source provenance."""
    if not agent.strip() or agent == "*":
        msg = "agent must be a non-empty non-wildcard name"
        raise ToolError(msg)
    engine = _engine_from_ctx(ctx)
    try:
        result = engine.delete_agent(agent)
    except (ConcurrencyError, DuplicateEntryError, LifecycleRecoveryError, ValidationError) as exc:
        raise ToolError(str(exc)) from exc
    if result["entries_deleted"] == 0 and result["scopes_updated"] == 0:
        msg = f"No memory references found for agent {agent!r}."
        raise ToolError(msg)
    return dict(result)


async def _approve_entry(ctx: Context, *, entry_id: str, revision: str) -> dict[str, Any]:
    """Promote a curated entry to approved."""
    engine = _engine_from_ctx(ctx)
    current = _load_entry_or_raise(engine, entry_id)

    try:
        updated = engine.approve(current.id, expected_revision=revision)
    except MemoryBusyError as exc:
        raise ToolError(str(exc)) from exc
    except ConcurrencyError as exc:
        raise _stale_revision_error(exc) from exc
    except (TransitionError, NotFoundError, DuplicateEntryError) as exc:
        raise ToolError(str(exc)) from exc

    return _entry_to_dict(updated)


async def approve_memory(ctx: Context, *, entry_id: str, revision: str) -> dict[str, Any]:
    """Compatibility alias for approving curated memory entries."""
    approved = await _approve_entry(ctx, entry_id=entry_id, revision=revision)
    return _with_hint(approved, "Entry approved. Now visible to scoped agents.")


async def assess_memories(
    ctx: Context,
    *,
    assessments: list[AssessmentItem],
    task_id: str,
) -> dict[str, list[dict[str, object]]]:
    """Process batch assessment submissions with per-entry success/failure results."""
    try:
        batch = _AssessmentBatch.model_validate({"assessments": assessments, "task_id": task_id})
    except ValidationError as exc:
        msg = (
            "Invalid assessment batch. Each item requires entry_id, revision, and a supported bucket "
            "(outstanding, unremarkable, didnt_use, factually_wrong); "
            "task_id must be 1-128 printable ASCII characters without whitespace."
        )
        raise ToolError(msg) from exc

    engine = _engine_from_ctx(ctx)
    results: list[dict[str, object]] = []

    for assessment in batch.assessments:
        entry_id = assessment.entry_id
        bucket = assessment.bucket
        try:
            if bucket == "factually_wrong":
                outcome = engine.record_factually_wrong(
                    entry_id,
                    batch.task_id,
                    expected_revision=assessment.revision,
                )
            else:
                outcome = engine.record_assessment(
                    entry_id,
                    bucket,
                    task_id=batch.task_id,
                    expected_revision=assessment.revision,
                )
            results.append(
                {
                    "entry_id": entry_id,
                    "success": True,
                    "already_applied": outcome.already_applied,
                    "recorded_bucket": outcome.recorded_bucket,
                    **({"state": str(outcome.entry.state)} if outcome.entry.challenges else {}),
                    **_challenges(outcome.entry),
                }
            )
        except (
            NotFoundError,
            TransitionError,
            ConcurrencyError,
            DuplicateEntryError,
            MemoryValidationError,
            ValidationError,
        ) as exc:
            results.append({"entry_id": entry_id, "success": False, "error": str(exc)})

    return {"results": results}


async def make_global(ctx: Context, *, entry_id: str, revision: str, folder: str | None = None) -> dict[str, Any]:
    """Move one entry of a project's memory into Global, recording the project (TD-292), and commit both paths."""
    ctx = _in_folder(ctx, folder)
    root = _shared_root(ctx)
    if root is None:
        msg = "this memory server is bound to no shared repository, so it has no Global memory"
        raise ToolError(msg)
    source, target = _memory_dir_from_ctx(ctx), root / GLOBAL
    project = source.parent.name
    if target.is_symlink() or (target.exists() and target.resolve().parent != root.resolve()):
        msg = "Global memory is a link out of the shared repository: nothing moves"
        raise ToolError(msg)
    target.mkdir(exist_ok=True)
    try:
        with repo_locked(root), writer_lock(source), writer_lock(target):  # the repository lock first, as the page
            found = [(p, e) for p in sorted(source.glob("*.md")) if (e := storage.read_entry(p)) and e.id == entry_id]
            if len(found) != 1:
                msg = f"entry not found: {entry_id}"
                raise ToolError(msg)
            path, entry = found[0]
            if entry.revision != revision:
                msg = f"Entry changed since it was read: {entry_id}. Re-read before retrying."
                raise ToolError(msg)
            if entry.state not in {MemoryState.CURATED, MemoryState.APPROVED}:  # the owner resolves the others first
                msg = f"{entry.title} is {entry.state}: only a curated or approved entry goes global"
                raise ToolError(msg)
            moved = target / path.name
            if moved.exists() or any(getattr(storage.read_entry(p), "id", "") == entry_id for p in target.glob("*.md")):
                msg = f"Global memory holds {entry.title} already"
                raise ToolError(msg)
            moving = entry.model_copy(update={"origin": project})
            storage.write_entry(path, moving, memory_dir=source)  # rewritten in place, then moved whole
            try:
                path.replace(moved)
            except OSError as exc:
                storage.write_entry(path, entry, memory_dir=source)  # as it was, so it can be tried again
                msg = f"{entry.title} could not move: {exc.strerror or exc}; try again"
                raise ToolError(msg) from exc
            try:
                # Not the Memory page's "memory <project>: " subject: Maintenance reads that as the owner's action.
                sha = commit_move([path, moved], f"chore: memory make global {entry.title} from {project} (memory-mcp)")
            except subprocess.CalledProcessError as exc:
                moved.replace(path)
                storage.write_entry(path, entry, memory_dir=source)  # back where it was, so it can be tried again
                msg = f"{entry.title} stays in {project}: the commit failed: {format_git_failure(exc)}"
                raise ToolError(msg) from exc
    except (MemoryBusyError, TimeoutError) as exc:
        raise ToolError(str(exc)) from exc
    hint = f"Moved into Global memory and committed; the owner can move it back to {project} on the Memory page."
    return _with_hint(_entry_to_dict(moving) | {"commit_sha": sha}, hint)


async def curation_threshold(ctx: Context) -> dict[str, Any]:
    """The curator's confidence threshold in percent from the global settings (TD-400); unset when they hold none.

    Code ships no default (the owner, 2026-10-23): unset, the curator acts on nothing alone.
    """
    root = _shared_root(ctx)
    try:
        value = json.loads((root / CONFIG).read_text(encoding="utf-8")).get("curator_threshold") if root else None
    except OSError, ValueError, AttributeError:
        value = None
    if isinstance(value, int) and not isinstance(value, bool) and 50 <= value <= 100:  # noqa: PLR2004
        return {"threshold": value, "source": "global"}
    return {"threshold": None, "source": "unset", "error": UNSET_THRESHOLD}
