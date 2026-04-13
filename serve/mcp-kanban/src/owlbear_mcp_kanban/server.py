"""OwlBear MCP kanban server — exposes KanbanEngine operations as MCP tools."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BeforeValidator

from owlbear_kanban import KanbanEngine
from owlbear_kanban.dispatch import pick_dispatchable
from owlbear_kanban.models import TaskSummary
from owlbear_mcp_kanban.models import KanbanTask

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
    "_show_validated",
    "app_lifespan",
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
    activity_log = os.environ.get("KANBAN_ACTIVITY_LOG", "").strip().lower() in {"1", "true", "yes"}
    engine = KanbanEngine(kanban_dir, activity_log=activity_log)
    yield AppContext(engine=engine, kanban_dir=kanban_dir)


mcp = FastMCP("owlbear-kanban", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_tasks(  # noqa: PLR0913
    ctx: Context,
    *,
    status: str = "",
    tag: str = "",
    priority: str = "",
    search: str = "",
    sort: str = "",
    unclaimed: bool = False,
    archived: bool = False,
    limit: int = 0,
    reverse: bool = False,
    blocked: bool | None = None,
) -> list[TaskSummary]:
    """List kanban tasks with optional filters."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    records = app_ctx.engine.list_tasks(
        status=status,
        tag=tag,
        priority=priority,
        search=search,
        sort=sort,
        unclaimed=unclaimed,
        archived=archived,
        limit=limit,
        reverse=reverse,
        blocked=blocked,
    )
    return [TaskSummary.model_validate(record.model_dump()) for record in records]


# Set outputSchema for list_tasks (lean task array)
_list_tasks_tool_obj = next(
    t
    for t in mcp._tool_manager._tools.values()  # noqa: SLF001
    if t.name == "list_tasks"
)
_list_tasks_tool_obj.fn_metadata.output_schema = {
    "type": "object",
    "properties": {
        "result": {
            "type": "array",
            "items": TaskSummary.model_json_schema(),
        },
    },
    "required": ["result"],
}


def _record_to_task(record: Task) -> KanbanTask:
    """Convert a Task to a KanbanTask (claimed_by → claimed bool)."""
    return KanbanTask.model_validate(record.model_dump())


async def _show_validated(app_ctx: AppContext, task_id: str) -> KanbanTask:
    """Retrieve a task from the engine and return a validated KanbanTask."""
    try:
        record = app_ctx.engine.show_task(task_id)
    except FileNotFoundError as exc:
        msg = str(exc)
        raise ToolError(msg) from exc
    return _record_to_task(record)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def show_task(ctx: Context, task_id: StrId) -> KanbanTask:
    """Show a single task by ID with full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return await _show_validated(app_ctx, task_id)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def create_task(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    body: str = "",
    depends_on: StrId = "",
    parent: int = 0,
    priority: str = "",
    status: str = "",
    tags: str = "",
) -> KanbanTask:
    """Create a new kanban task."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    deps_list = [int(d.strip()) for d in depends_on.split(",") if d.strip()] if depends_on else []
    try:
        record = app_ctx.engine.create_task(
            title,
            body=body,
            tags=tags_list or None,
            priority=priority,
            status=status,
            parent=parent if parent > 0 else None,
            depends_on=deps_list or None,
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return _record_to_task(record)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True))
async def move_task(ctx: Context, task_id: StrId, status: str) -> KanbanTask:
    """Move a task to the specified status column, or archive it when status is "archived"."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        record = app_ctx.engine.move_task(task_id, status)
    except (FileNotFoundError, ValueError) as exc:
        msg = str(exc)
        raise ToolError(msg) from exc
    return _record_to_task(record)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
async def edit_task(  # noqa: PLR0912, PLR0913, C901
    ctx: Context,
    *,
    task_id: StrId,
    body: str = "",
    block: str = "",
    unblock: bool = False,
    tags: str = "",
    add_tag: str = "",
    remove_tag: str = "",
    priority: str = "",
    append_body: str = "",
    status: str = "",
    timestamp: bool = False,
    add_dep: StrId = "",
    remove_dep: StrId = "",
    parent: int = 0,
    title: str = "",
    depends_on: StrId = "",
) -> KanbanTask:
    """Edit task fields."""
    if depends_on:
        msg = "edit_task does not accept 'depends_on'. Use 'add_dep' or 'remove_dep' instead."
        raise ToolError(msg)
    if tags:
        msg = "edit_task does not accept 'tags'. Use 'add_tag' or 'remove_tag' instead."
        raise ToolError(msg)
    app_ctx: AppContext = ctx.request_context.lifespan_context
    kwargs: dict[str, object] = {}
    if body:
        kwargs["body"] = body
    if title:
        kwargs["title"] = title
    if priority:
        kwargs["priority"] = priority
    if status:
        kwargs["status"] = status
    if block:
        kwargs["blocked"] = True
        kwargs["block_reason"] = block
    elif unblock:
        kwargs["blocked"] = False
    if add_tag:
        kwargs["add_tags"] = [add_tag]
    if remove_tag:
        kwargs["remove_tags"] = [remove_tag]
    if add_dep:
        kwargs["add_deps"] = [int(add_dep)]
    if remove_dep:
        kwargs["remove_deps"] = [int(remove_dep)]
    if append_body:
        kwargs["append_body"] = append_body
    if timestamp:
        kwargs["timestamp"] = True
    if parent > 0:
        kwargs["parent"] = parent
    try:
        record = app_ctx.engine.edit_task(task_id, **kwargs)
    except (FileNotFoundError, ValueError) as exc:
        msg = str(exc)
        raise ToolError(msg) from exc
    return _record_to_task(record)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def start_work(ctx: Context, task_id: StrId) -> KanbanTask:
    """Claim a task and return its full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    try:
        record = app_ctx.engine.start_work(task_id)
    except (ValueError, FileNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
    return _record_to_task(record)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def end_work(  # noqa: PLR0913
    ctx: Context,
    *,
    task_id: StrId,
    note: str,
    outcome: Literal["success", "fail", "block", "reject"] = "success",
    block_reason: str = "",
    move_to: str = "research",
) -> KanbanTask:
    """Release a task: append note, advance or resolve status, release claim."""
    app_ctx: AppContext = ctx.request_context.lifespan_context

    if outcome == "block" and not block_reason:
        msg = "block_reason is required when outcome=block"
        raise ToolError(msg)

    try:
        record = app_ctx.engine.end_work(
            task_id,
            note=note,
            outcome=outcome,
            block_reason=block_reason,
            move_to=move_to,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
    return _record_to_task(record)


# ---------------------------------------------------------------------------
# pick_tasks — gate-filtered dispatch list
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def pick_tasks(ctx: Context, *, limit: int = 25, tag: str = "") -> dict:
    """Pick dispatchable tasks: gate-filtered, sorted by priority/status, capped at limit.

    Optional tag pre-filters candidates before gating (e.g. 'phase-2').
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    tasks = pick_dispatchable(app_ctx.engine, limit=limit, tag=tag)
    return {"dispatch": [{"task_id": int(t.id), "status": str(t.status)} for t in tasks]}


# Override outputSchema for tools that return KanbanTask. This ensures the
# advertised schema matches what structuredContent actually contains.
_kanbantask_schema = KanbanTask.model_json_schema()
for _tool_name in ("show_task", "move_task", "edit_task", "create_task", "start_work", "end_work"):
    _tool_obj = next(t for t in mcp._tool_manager._tools.values() if t.name == _tool_name)  # noqa: SLF001
    _tool_obj.fn_metadata.output_schema = _kanbantask_schema


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
        "blocked": {"description": "true = only blocked, false = only unblocked, null = all"},
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
        "add_dep": {"description": "Add dependency task IDs (comma-separated, e.g. '601,602')"},
        "remove_dep": {"description": "Remove dependency task IDs (comma-separated, e.g. '601,602')"},
        "parent": {"description": "Parent task ID for subtask hierarchy"},
        "depends_on": {"description": "Not supported on edit. Use add_dep / remove_dep instead."},
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
        "move_to": {"enum": _STATUSES, "description": "Target status when outcome=reject"},
    },
)
