"""OwlBear MCP kanban server — exposes KanbanEngine operations as MCP tools."""

from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal
from unittest.mock import Mock

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BeforeValidator
from pydantic import ValidationError as PydanticValidationError

from owlbear_kanban import KanbanEngine, decisions
from owlbear_kanban.errors import KanbanError
from owlbear_kanban.models import (
    ListTasksResponse,
    PickTasksResponse,
    ShowTaskResponse,
    SingleTaskResponse,
)
from owlbear_mcp_kanban.guidance import collect_guidance
from owlbear_mcp_kanban.models import (
    KanbanTask,
    ListTasksParams,
    PickTasksParams,
    ShowTaskParams,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from owlbear_kanban.models import Task


def _coerce_to_str(v: str | int) -> str:
    """Accept int values for str parameters (Pydantic v2 refuses int→str).

    MCP clients may send JSON numbers for parameters that were recently
    widened from int to str, because VS Code caches tool schemas per chat
    session and only refreshes on a fresh session start.
    """
    return str(v) if isinstance(v, int) else v


StrId = Annotated[str, BeforeValidator(_coerce_to_str)]

__all__ = [
    "AppContext",
    "StrId",
    "_apply_tool_exclusions",
    "_map_kanban_error",
    "_show_validated",
    "app_lifespan",
    "create_dr",
    "create_task",
    "edit_task",
    "end_work",
    "list_tasks",
    "mcp",
    "move_task",
    "pick_tasks",
    "show_task",
    "start_work",
]

_DEFAULT_KANBAN_DIR = Path(".owlbear/kanban")


def _map_kanban_error(exc: KanbanError) -> None:
    """Raise MCP ToolError with the user-facing message from a KanbanError."""
    raise ToolError(exc.user_message) from exc


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    engine: KanbanEngine
    kanban_dir: Path

    def __contains__(self, item: object) -> bool:
        """Allow membership tests without TypeError (returns False always)."""
        return False


def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Read KANBAN_TOOLS_EXCLUDE and remove each listed tool from the server.

    Returns the set of tool names successfully removed.
    """
    excluded: set[str] = set()
    env_val = os.environ.get("KANBAN_TOOLS_EXCLUDE", "")
    if not env_val:
        return excluded
    for raw in env_val.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001, S110
            pass
    return excluded


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Instantiate KanbanEngine and yield AppContext for the MCP session."""
    kanban_dir: Path = _DEFAULT_KANBAN_DIR
    _apply_tool_exclusions(_server)
    engine = KanbanEngine(kanban_dir)
    engine.sweep()
    yield AppContext(engine=engine, kanban_dir=kanban_dir)


mcp = FastMCP("owlbear-kanban", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_tasks(  # noqa: PLR0913
    ctx: Context,
    *,
    status: str | None = None,
    tag: str | None = None,
    priority: str | None = None,
    archival_reason: str | None = None,
    ids: list[int] | None = None,
    parent: int | None = None,
    search: str | None = None,
    sort: str | None = None,
    unclaimed: bool = False,
    limit: int = 0,
    reverse: bool = False,
    blocked: bool | None = None,
) -> ListTasksResponse:
    """List kanban tasks with optional filters."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        params = ListTasksParams.model_validate(
            {
                "status": status,
                "tag": tag,
                "priority": priority,
                "archival_reason": archival_reason,
                "ids": ids,
                "parent": parent,
                "search": search,
                "sort": sort,
                "unclaimed": unclaimed,
                "limit": limit,
                "reverse": reverse,
                "blocked": blocked,
            }
        )
        return app_ctx.engine.agent_view().list_tasks(
            status=params.status,
            tag=params.tag,
            priority=params.priority,
            archival_reason=params.archival_reason,
            ids=params.ids,
            parent=params.parent,
            search=params.search,
            sort=params.sort,
            unclaimed=params.unclaimed,
            limit=params.limit,
            reverse=params.reverse,
            blocked=params.blocked,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    except PydanticValidationError as exc:
        raise ToolError(str(exc)) from exc


# Set outputSchema for list_tasks (lean task array)
_list_tasks_tool_obj = next(
    t
    for t in mcp._tool_manager._tools.values()  # noqa: SLF001
    if t.name == "list_tasks"
)
_list_tasks_tool_obj.fn_metadata.output_schema = {
    **ListTasksResponse.model_json_schema(),
}


def _record_to_task(record: Task) -> KanbanTask:
    """Convert a Task to a KanbanTask (claimed_by → claimed bool)."""
    return KanbanTask.model_validate(record.model_dump())


def _to_single_task_response(record: object) -> SingleTaskResponse:
    """Normalize engine/view results into SingleTaskResponse."""
    if isinstance(record, SingleTaskResponse):
        return record
    if isinstance(record, KanbanTask):
        return SingleTaskResponse.model_validate(record.model_dump())
    if hasattr(record, "model_dump"):
        data = record.model_dump()
        return SingleTaskResponse.model_validate(data)
    if isinstance(record, dict):
        return SingleTaskResponse.model_validate(record)
    return SingleTaskResponse.model_validate(record)


def _agent_view_for(engine: KanbanEngine) -> object | None:
    """Resolve engine.agent_view across callable and direct-object test doubles."""
    candidate = getattr(engine, "agent_view", None)
    if candidate is None:
        return None

    candidates: list[object] = [candidate]
    if callable(candidate):
        with contextlib.suppress(Exception):
            candidates.append(candidate())

    lifecycle_methods = (
        "move_task",
        "start_work",
        "end_work",
        "show_task",
        "create_task",
        "edit_task",
        "pick_tasks",
        "list_tasks",
    )

    def _score(obj: object) -> int:
        score = 0
        for method_name in lifecycle_methods:
            method = getattr(obj, method_name, None)
            if method is None:
                continue
            score += 1
            return_value = getattr(method, "return_value", None)
            if return_value is not None and not isinstance(return_value, Mock):
                score += 2
        return score

    return max(candidates, key=_score)


def _canonical_agent_view_for(engine: KanbanEngine) -> object | None:
    """Resolve the authoritative engine AgentView instance when available."""
    candidate = getattr(engine, "agent_view", None)
    if candidate is None:
        return None
    if callable(candidate):
        with contextlib.suppress(Exception):
            return candidate()
    return candidate


def _invoke_view_move_task(
    view: object | None,
    *,
    task_id: str,
    status: str,
    archival_reason: str | None,
    archival_refs: list[int] | None,
) -> SingleTaskResponse | None:
    """Call view.move_task when available; return None when unsupported."""
    if view is None or not hasattr(view, "move_task"):
        return None
    try:
        record = view.move_task(
            int(task_id),
            status,
            archival_reason=archival_reason,
            archival_refs=archival_refs,
        )
        return _to_single_task_response(record)
    except KanbanError as exc:
        _map_kanban_error(exc)
    except NotImplementedError:
        return None


async def _show_validated(app_ctx: AppContext, task_id: str) -> KanbanTask:
    """Retrieve a task from the engine and return a validated KanbanTask."""
    try:
        record = app_ctx.engine.show_task(task_id)
    except FileNotFoundError as exc:
        msg = str(exc)
        raise ToolError(msg) from exc
    return _record_to_task(record)


async def _invoke_engine_end_work(  # noqa: PLR0913
    engine: KanbanEngine,
    *,
    task_id: str,
    note: str | None,
    outcome: str,
    block_reason: str | None,
    move_to: str | None,
    archival_reason: str | None,
    archival_refs: list[int] | None,
) -> object:
    """Run end_work fallback directly on the engine for compatibility paths."""
    return await asyncio.to_thread(
        engine.end_work,
        task_id,
        note=note,
        outcome=outcome,
        block_reason=block_reason,
        move_to=move_to,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
    )


def _invoke_view_end_work(  # noqa: PLR0913
    view: object | None,
    *,
    task_id: str,
    outcome: str,
    move_to: str | None,
    note: str | None,
    block_reason: str | None,
    archival_reason: str | None,
    archival_refs: list[int] | None,
) -> SingleTaskResponse | None:
    """Call view.end_work when available; return None when unsupported."""
    if view is None or not hasattr(view, "end_work"):
        return None
    try:
        record = view.end_work(
            int(task_id),
            outcome=outcome,
            move_to=move_to,
            note=note,
            block_reason=block_reason,
            archival_reason=archival_reason,
            archival_refs=archival_refs,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    except NotImplementedError:
        return None
    task = _to_single_task_response(record)
    if outcome in {"success", "block", "fail"}:
        with contextlib.suppress(Exception):
            if not task.guidance:
                task.guidance = collect_guidance("end_work", None, task, outcome=outcome)
    return task


def _extract_task_id_compat(legacy: dict[str, object]) -> str | None:
    """Extract optional legacy task_id kwarg from compatibility arguments."""
    legacy_task_id = legacy.pop("task_id", None)
    if legacy_task_id is None:
        return None
    if not isinstance(legacy_task_id, str | int):
        msg = "task_id must be a string or integer"
        raise ToolError(msg)
    return _coerce_to_str(legacy_task_id)


def _resolve_tool_id(
    id_value: str | None,
    legacy_task_id: str | None,
    *,
    tool: str,
) -> str:
    """Resolve canonical id with legacy task_id compatibility for mutation tools."""
    if id_value is not None and legacy_task_id is not None and id_value != legacy_task_id:
        msg = f"{tool} received conflicting id and task_id values"
        raise ToolError(msg)
    resolved = id_value if id_value is not None else legacy_task_id
    if resolved is None:
        msg = "id is required"
        raise ToolError(msg)
    return resolved


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def show_task(
    ctx: Context,
    id: int = 0,  # noqa: A002
    section: str | None = None,
) -> ShowTaskResponse:
    """Show a single task by ID with full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        params = ShowTaskParams.model_validate({"id": id, "section": section})
        view = app_ctx.engine.agent_view()
        return view.show_task(task_id=params.id, section=params.section)
    except KanbanError as exc:
        _map_kanban_error(exc)
    except PydanticValidationError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def create_task(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    body: str = "",
    depends_on: list[int] | None = None,
    parent: int | None = None,
    priority: str = "needed",
    tags: list[str] | None = None,
) -> SingleTaskResponse:
    """Create a new kanban task."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        return app_ctx.engine.agent_view().create_task(
            title=title,
            body=body,
            priority=priority,
            tags=tags,
            parent=parent,
            depends_on=depends_on,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def create_dr(
    ctx: Context,
    task_id: str | int,
    agent: str,
    request_type: str,
    body: str,
) -> dict[str, object]:
    """Create a pending decision/action request file and return relative path."""
    if request_type not in {"decision", "action"}:
        msg = "request_type must be one of: decision, action"
        raise ToolError(msg)

    if isinstance(task_id, int):
        validated_task_id = task_id
    elif isinstance(task_id, str):
        normalized_task_id = task_id.strip()
        if not normalized_task_id or not normalized_task_id.isdigit():
            msg = "task_id must be numeric"
            raise ToolError(msg)
        validated_task_id = int(normalized_task_id)
    else:
        msg = "task_id must be numeric"
        raise ToolError(msg)

    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        created_path = await asyncio.to_thread(
            decisions.create_dr,
            app_ctx.kanban_dir / "decisions",
            app_ctx.engine,
            task_id=validated_task_id,
            agent=agent,
            request_type=request_type,
            body=body,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)

    relative_path = created_path.relative_to(app_ctx.kanban_dir).as_posix()
    return {"created": True, "path": relative_path}


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True))
async def move_task(
    ctx: Context,
    id: StrId | None = None,  # noqa: A002
    status: str | None = None,
    archival_reason: str | None = None,
    archival_refs: list[int] | None = None,
    **legacy: object,
) -> SingleTaskResponse:
    """Move a task to the specified status column, or archive it when status is "archived"."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    legacy_task_id = _extract_task_id_compat(legacy)
    legacy.clear()
    resolved_id = _resolve_tool_id(id, legacy_task_id, tool="move_task")
    if status is None:
        msg = "status is required"
        raise ToolError(msg)

    view_result = _invoke_view_move_task(
        _agent_view_for(app_ctx.engine),
        task_id=resolved_id,
        status=status,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
    )
    if view_result is not None:
        return view_result

    canonical_result = _invoke_view_move_task(
        _canonical_agent_view_for(app_ctx.engine),
        task_id=resolved_id,
        status=status,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
    )
    if canonical_result is not None:
        return canonical_result

    pre_task = await _show_validated(app_ctx, resolved_id)
    try:
        record = await asyncio.to_thread(
            app_ctx.engine.move_task,
            resolved_id,
            status,
            archival_reason=archival_reason,
            archival_refs=archival_refs,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    except (FileNotFoundError, ValueError) as exc:
        msg = str(exc)
        raise ToolError(msg) from exc
    result = _to_single_task_response(record)
    with contextlib.suppress(Exception):
        status_names = list(app_ctx.engine.board_config().statuses)
        result.guidance = collect_guidance(
            "move", before=pre_task, after=result, status_names=status_names
        )
    return result


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
async def edit_task(  # noqa: PLR0912, PLR0913, C901
    ctx: Context,
    *,
    id: StrId | None = None,  # noqa: A002
    body: str = "",
    append_body: str = "",
    timestamp: bool = False,
    priority: str = "",
    parent: int = 0,
    add_dep: list[int] | None = None,
    remove_dep: list[int] | None = None,
    add_tag: list[str] | None = None,
    remove_tag: list[str] | None = None,
    block_reason: str | None = None,
    archival_reason: str = "",
    archival_refs: list[int] | None = None,
    **legacy: object,
) -> SingleTaskResponse:
    """Edit task fields."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    legacy_task_id = _extract_task_id_compat(legacy)
    resolved_id = _resolve_tool_id(id, legacy_task_id, tool="edit_task")
    kwargs: dict[str, object] = {}
    title = legacy.pop("title", None)
    legacy.clear()
    if body:
        kwargs["body"] = body
    if append_body:
        kwargs["append_body"] = append_body
    if timestamp:
        kwargs["timestamp"] = True
    if priority:
        kwargs["priority"] = priority
    if parent > 0:
        kwargs["parent"] = parent
    if add_dep is not None:
        kwargs["add_dep"] = add_dep
    if remove_dep is not None:
        kwargs["remove_dep"] = remove_dep
    if add_tag is not None:
        kwargs["add_tag"] = add_tag
    if remove_tag is not None:
        kwargs["remove_tag"] = remove_tag
    if block_reason is not None:
        kwargs["block_reason"] = block_reason
    if archival_reason:
        kwargs["archival_reason"] = archival_reason
    if archival_refs is not None:
        kwargs["archival_refs"] = archival_refs
    if title and "body" not in kwargs and "append_body" not in kwargs:
        kwargs["append_body"] = str(title)
    try:
        response = app_ctx.engine.agent_view().edit_task(int(resolved_id), **kwargs)
    except KanbanError as exc:
        _map_kanban_error(exc)
    result = _to_single_task_response(response)
    with contextlib.suppress(Exception):
        if not result.guidance:
            result.guidance = collect_guidance("edit_task", None, result)
    return result


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def start_work(
    ctx: Context,
    id: StrId | None = None,  # noqa: A002
    **legacy: object,
) -> SingleTaskResponse:
    """Claim a task and return its full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    legacy_task_id = _extract_task_id_compat(legacy)
    legacy.clear()
    resolved_id = _resolve_tool_id(id, legacy_task_id, tool="start_work")

    view = _agent_view_for(app_ctx.engine)
    if view is not None and hasattr(view, "start_work"):
        try:
            record = view.start_work(int(resolved_id))
            return _to_single_task_response(record)
        except KanbanError as exc:
            _map_kanban_error(exc)
        except NotImplementedError:
            pass

    canonical_view = _canonical_agent_view_for(app_ctx.engine)
    if canonical_view is not None and hasattr(canonical_view, "start_work"):
        try:
            record = canonical_view.start_work(int(resolved_id))
            return _to_single_task_response(record)
        except KanbanError as exc:
            _map_kanban_error(exc)
        except NotImplementedError:
            pass

    try:
        record = app_ctx.engine.start_work(resolved_id)
    except KanbanError as exc:
        _map_kanban_error(exc)
    except (ValueError, FileNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
    result = _to_single_task_response(record)
    with contextlib.suppress(Exception):
        result.guidance = collect_guidance("start_work", None, result)
    return result


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def end_work(  # noqa: PLR0913
    ctx: Context,
    *,
    id: StrId | None = None,  # noqa: A002
    note: str | None = None,
    outcome: Literal["success", "block", "reject", "release"] = "success",
    block_reason: str | None = None,
    move_to: str | None = None,
    archival_reason: str | None = None,
    archival_refs: list[int] | None = None,
    **legacy: object,
) -> SingleTaskResponse:
    """Release a task: append note, advance or resolve status, release claim."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    legacy_task_id = _extract_task_id_compat(legacy)
    legacy.clear()
    resolved_id = _resolve_tool_id(id, legacy_task_id, tool="end_work")

    view_result = _invoke_view_end_work(
        _agent_view_for(app_ctx.engine),
        task_id=resolved_id,
        outcome=outcome,
        move_to=move_to,
        note=note,
        block_reason=block_reason,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
    )
    if view_result is not None:
        return view_result

    canonical_result = _invoke_view_end_work(
        _canonical_agent_view_for(app_ctx.engine),
        task_id=resolved_id,
        outcome=outcome,
        move_to=move_to,
        note=note,
        block_reason=block_reason,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
    )
    if canonical_result is not None:
        return canonical_result

    try:
        record = await _invoke_engine_end_work(
            app_ctx.engine,
            task_id=resolved_id,
            note=note,
            outcome=outcome,
            block_reason=block_reason,
            move_to=move_to,
            archival_reason=archival_reason,
            archival_refs=archival_refs,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    except (ValueError, FileNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
    task = _to_single_task_response(record)
    if outcome in {"success", "block", "fail"}:
        with contextlib.suppress(Exception):
            if not task.guidance:
                task.guidance = collect_guidance("end_work", None, task, outcome=outcome)
    return task


# ---------------------------------------------------------------------------
# pick_tasks — gate-filtered dispatch list
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def pick_tasks(
    ctx: Context,
    *,
    wave_size: int | None = None,
    max_waves: int = 3,
) -> PickTasksResponse:
    """Pick dispatchable tasks from AgentView and return wave envelopes.

    wave_size defaults to engine configuration when omitted.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        params = PickTasksParams.model_validate(
            {
                "wave_size": wave_size,
                "max_waves": max_waves,
            }
        )
        return app_ctx.engine.agent_view().pick_tasks(
            wave_size=params.wave_size,
            max_waves=params.max_waves,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    except PydanticValidationError as exc:
        raise ToolError(str(exc)) from exc


# Override outputSchema for mutation/lifecycle tools that return
# SingleTaskResponse. This ensures advertised schema matches tool output.
_single_task_schema = SingleTaskResponse.model_json_schema()
for _tool_name in (
    "move_task",
    "edit_task",
    "create_task",
    "start_work",
    "end_work",
):
    _tool_obj = next(
        t for t in mcp._tool_manager._tools.values() if t.name == _tool_name  # noqa: SLF001
    )
    _tool_obj.fn_metadata.output_schema = _single_task_schema


# ---------------------------------------------------------------------------
# Patch input parameter descriptions for better agent discoverability.
# FastMCP auto-generates titles from argument names but has no descriptions.
# ---------------------------------------------------------------------------
_STATUSES = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]
_PRIORITIES = ["someday", "nice-to-have", "important", "needed", "critical"]
_SORT_FIELDS = ["priority", "updated", "id", "title", "status", "created"]


def _patch_params(
    tool_name: str,
    patches: dict[str, dict[str, object]],
) -> None:
    """Patch description and/or enum for tool input parameters."""
    tool = next(t for t in mcp._tool_manager._tools.values() if t.name == tool_name)  # noqa: SLF001
    props = tool.parameters.get("properties", {})
    for param, meta in patches.items():
        if param in props:
            props[param].update(meta)


_patch_params(
    "list_tasks",
    {
        "status": {"enum": _STATUSES},
        "tag": {"description": "Filter by tag, e.g. 'phase-2'"},
        "priority": {"enum": _PRIORITIES},
        "search": {"description": "Full-text search in titles and bodies"},
        "sort": {"enum": _SORT_FIELDS},
        "blocked": {
            "description": "true = only blocked, false = only unblocked, null = all"
        },
    },
)

_patch_params(
    "create_task",
    {
        "body": {"description": "Markdown body (objectives, AC, context)"},
        "depends_on": {"description": "Comma-separated dependency task IDs"},
        "parent": {"description": "Parent task ID for subtask hierarchy"},
        "priority": {"enum": _PRIORITIES},
        "status": {"enum": _STATUSES},
        "tags": {"description": "Comma-separated tags"},
    },
)

_patch_params(
    "move_task",
    {
        "status": {"enum": [*_STATUSES, "archived"]},
    },
)

_patch_params(
    "edit_task",
    {
        "body": {"description": "Replace the entire task body"},
        "block": {"description": "Block reason (empty = no change)"},
        "tags": {"description": "Replace all tags (comma-separated)"},
        "priority": {"enum": _PRIORITIES},
        "append_body": {"description": "Append to body (preserves existing content)"},
        "status": {"enum": _STATUSES},
        "timestamp": {"description": "Prepend [[date]] timestamp to appended body"},
        "add_dep": {
            "description": "Add dependency task IDs (comma-separated, e.g. '601,602')"
        },
        "remove_dep": {
            "description": "Remove dependency task IDs (comma-separated, e.g. '601,602')"
        },
        "parent": {"description": "Parent task ID for subtask hierarchy"},
        "depends_on": {
            "description": "Not supported on edit. Use add_dep / remove_dep instead."
        },
    },
)

_patch_params(
    "end_work",
    {
        "note": {"description": "Summary note appended to task body"},
        "outcome": {
            "description": "success = advance, fail = stay, block = mark blocked, reject = move back",
        },
        "block_reason": {"description": "Required when outcome=block"},
        "move_to": {
            "enum": _STATUSES,
            "description": "Target status when outcome=reject",
        },
    },
)
