"""OwlBear MCP kanban server — exposes KanbanEngine operations as MCP tools."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BeforeValidator
from pydantic import ValidationError as PydanticValidationError

from owlbear_kanban import KanbanEngine
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
    "create_request",
    "create_task",
    "edit_task",
    "end_work",
    "list_requests",
    "list_tasks",
    "mcp",
    "move_task",
    "parse_task_id",
    "pick_tasks",
    "show_request",
    "show_task",
    "start_work",
]

_DEFAULT_KANBAN_DIR = Path(".owlbear/kanban")
_UUID4_VERSION = 4
_NORM_GUIDANCE = (
    "Literal \\n sequences were normalized to actual newlines. "
    "To keep a literal \\n in files, send \\\\n in JSON input."
)


def _resolve_kanban_dir() -> Path:
    """Resolve KANBAN_DIR from the environment, defaulting to cwd/.owlbear/kanban."""
    raw_value = os.environ.get("KANBAN_DIR", "").strip()
    selected = Path(raw_value) if raw_value else _DEFAULT_KANBAN_DIR
    return selected.resolve()


def _normalize_escaped_newlines(text: str) -> tuple[str, bool]:
    r"""Protect ``\\n``, normalize ``\n`` to newlines, then restore ``\n``."""
    sentinel = "\x00OBK_NL_SENTINEL\x00"
    protected = text.replace("\\\\n", sentinel)
    normalized = protected.replace("\\n", "\n")
    restored = normalized.replace(sentinel, "\\n")
    return restored, restored != text


def _sanitize_agent_strings(kwargs: dict[str, object]) -> None:
    """Normalize common LLM string-encoding mistakes in-place.

    Detects literal ``""`` or ``''`` (two quote characters intended as empty
    string by the agent) and replaces with actual empty string so downstream
    truthiness checks work correctly.
    """
    for key, value in kwargs.items():
        if isinstance(value, str) and value in ('""', "''"):
            kwargs[key] = ""


def _append_norm_guidance(guidance: list[str] | None, *, changed: bool) -> list[str]:
    """Append normalization guidance only when newline normalization occurred."""
    merged = list(guidance or [])
    if changed:
        merged.append(_NORM_GUIDANCE)
    return merged


def _startup_error(kanban_dir: Path, detail: str) -> RuntimeError:
    """Build a startup error with board path and KANBAN_DIR remediation guidance."""
    return RuntimeError(f"{detail}: {kanban_dir}. Set KANBAN_DIR to a valid kanban board directory.")


def parse_task_id(value: str | int, *, field: str = "task_id") -> int:
    """Parse MCP task identifiers as positive base-10 integers."""
    msg = f"{field} must be a positive integer"
    payload = json.dumps({"code": "ERR_INVALID_ID", "message": msg})
    if isinstance(value, bool):
        raise ToolError(payload)
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        if not value or value != value.strip() or not value.isdecimal():
            raise ToolError(payload)
        parsed = int(value)
    else:
        raise ToolError(payload)
    if parsed <= 0:
        raise ToolError(payload)
    return parsed


def _map_kanban_error(exc: KanbanError) -> None:
    """Raise MCP ToolError with machine-readable code and human-readable message."""
    payload = json.dumps({"code": exc.code, "message": exc.user_message})
    raise ToolError(payload) from exc


def _raise_tool_error(code: str, message: str) -> None:
    """Raise MCP ToolError with normalized JSON payload fields."""
    raise ToolError(json.dumps({"code": code, "message": message}))


def _raise_param_validation(message: str) -> None:
    """Raise parameter validation errors using the MCP error envelope format."""
    _raise_tool_error("ERR_PARAM_VALIDATION", message)


def _require_uuid4(value: str, *, field: str) -> str:
    """Validate value is UUID4 text and return the original value."""
    try:
        parsed = UUID(value)
    except (TypeError, ValueError) as exc:
        _raise_param_validation(f"{field} must be a valid UUID4")
        raise AssertionError from exc
    if parsed.version != _UUID4_VERSION:
        _raise_param_validation(f"{field} must be a valid UUID4")
    return value


def _raise_not_found(message: str = "Task not found") -> None:
    """Raise not-found errors without leaking filesystem paths."""
    _raise_tool_error("ERR_NOT_FOUND", message)


def _safe_not_found_message(raw_message: str, fallback: str) -> str:
    """Preserve user-facing not-found text while hiding path-like internals."""
    text = raw_message.strip()
    if not text:
        return fallback
    if "/" in text or "\\" in text:
        return fallback
    return text


def _validate_archival_constraints(
    app_ctx: AppContext,
    *,
    task_id: int,
    current_status: str | None,
    target_status: str | None,
    archival: tuple[str | None, list[int] | None],
) -> None:
    """Validate archival constraints in one shared adapter-level path."""
    archival_reason, archival_refs = archival
    if target_status == "archived":
        config = app_ctx.engine.board_config()
        app_ctx.engine.validate_archival(
            task_id=task_id,
            can_mark_completed=(current_status == "done"),
            config=config,
            archival_reason=archival_reason,
            archival_refs=list(archival_refs or []),
        )
    elif archival_reason is not None or archival_refs is not None:
        # Non-archived cases are validated by AgentView to preserve existing behavior.
        return


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
    kanban_dir = _resolve_kanban_dir()
    _apply_tool_exclusions(_server)

    if not kanban_dir.is_dir():
        raise _startup_error(kanban_dir, "Kanban directory does not exist")

    try:
        engine = KanbanEngine(kanban_dir)
    except Exception as exc:
        raise _startup_error(kanban_dir, "Failed to initialize kanban board") from exc

    if not engine.tasks_dir.is_dir():
        raise _startup_error(kanban_dir, "Kanban tasks directory does not exist")

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
        if params.ids is not None and len(params.ids) == 0:
            return ListTasksResponse(tasks=[], guidance=[], missing_ids=None)
        resolved_status = params.status
        if resolved_status is None and params.archival_reason is not None:
            resolved_status = "archived"
        return app_ctx.engine.agent_view().list_tasks(
            status=resolved_status,
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
        _raise_param_validation(str(exc))


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


async def _show_validated(app_ctx: AppContext, task_id: int) -> KanbanTask:
    """Retrieve a task from the engine and return a validated KanbanTask."""
    try:
        record = app_ctx.engine.show_task(str(task_id))
    except FileNotFoundError as exc:
        _raise_not_found(_safe_not_found_message(str(exc), f"Task '{task_id}' not found"))
    return _record_to_task(record)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def show_task(
    ctx: Context,
    id: StrId,  # noqa: A002
    section: str | None = None,
) -> ShowTaskResponse:
    """Show a single task by ID with full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    validated_id = parse_task_id(id, field="id")
    try:
        view = app_ctx.engine.agent_view()
        return view.show_task(task_id=validated_id, section=section)
    except KanbanError as exc:
        _map_kanban_error(exc)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def create_task(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    body: str = "",
    status: str = "",
    depends_on: list[int] | None = None,
    parent: int | None = None,
    priority: str = "",
    tags: list[str] | None = None,
    ac: list[str] | None = None,
    proof_bundle: str | None = None,
) -> SingleTaskResponse:
    """Create a new kanban task."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    normalized_body, body_changed = _normalize_escaped_newlines(body)
    kwargs: dict[str, object] = {
        "title": title,
        "body": normalized_body,
        "status": status,
        "priority": priority,
        "tags": tags,
        "parent": parent,
        "depends_on": depends_on,
    }
    if ac is not None:
        kwargs["ac"] = ac
    if proof_bundle is not None:
        kwargs["proof_bundle"] = proof_bundle
    _sanitize_agent_strings(kwargs)
    try:
        response = app_ctx.engine.agent_view().create_task(**kwargs)
    except KanbanError as exc:
        _map_kanban_error(exc)
    result = _to_single_task_response(response)
    result.guidance = _append_norm_guidance(result.guidance, changed=body_changed)
    return result


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def create_request(  # noqa: PLR0913
    ctx: Context,
    task_id: str | int,
    kind: str,
    title: str,
    summary: str,
    agent: str,
    options: list[dict[str, object]] | None = None,
    body: str = "",
) -> dict[str, object]:
    """Create a pending request and return its structured payload."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    parsed_task_id = parse_task_id(task_id, field="task_id")
    normalized_body, body_changed = _normalize_escaped_newlines(body)
    try:
        created = await asyncio.to_thread(
            app_ctx.engine.create_request,
            parsed_task_id,
            kind,
            title,
            summary,
            agent,
            options=options,
            body=normalized_body,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))
    payload = created.model_dump()
    payload["guidance"] = _append_norm_guidance([], changed=body_changed)
    return payload


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_requests(
    ctx: Context,
    status: str = "pending",
    task_id: str | int | None = None,
) -> list[dict[str, object]]:
    """List request records by status and optional task filter."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    parsed_task_id = parse_task_id(task_id, field="task_id") if task_id is not None else None
    try:
        records = await asyncio.to_thread(
            app_ctx.engine.list_requests,
            status,
            task_id=parsed_task_id,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    return [record.model_dump(exclude={"body"}) for record in records]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def show_request(
    ctx: Context,
    request_id: str,
) -> dict[str, object]:
    """Show a single request record with full detail."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    validated_request_id = _require_uuid4(request_id, field="request_id")
    try:
        record = await asyncio.to_thread(app_ctx.engine.get_request, validated_request_id)
    except KanbanError as exc:
        _map_kanban_error(exc)
    return record.model_dump()


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
async def move_task(
    ctx: Context,
    id: StrId,  # noqa: A002
    status: str | None = None,
    archival_reason: str | None = None,
    archival_refs: list[int] | None = None,
) -> SingleTaskResponse:
    """Mutate task status (non-idempotent), including archival when status is "archived"."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    resolved_id = parse_task_id(id, field="id")
    if status is None:
        _raise_param_validation("status is required")

    pre_task = await _show_validated(app_ctx, resolved_id)
    try:
        _validate_archival_constraints(
            app_ctx,
            task_id=resolved_id,
            current_status=pre_task.status,
            target_status=status,
            archival=(archival_reason, archival_refs),
        )
        record = app_ctx.engine.agent_view().move_task(
            resolved_id,
            status,
            archival_reason=archival_reason,
            archival_refs=archival_refs,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    result = _to_single_task_response(record)
    with contextlib.suppress(Exception):
        if not result.guidance:
            status_names = list(app_ctx.engine.board_config().statuses)
            result.guidance = collect_guidance("move", before=pre_task, after=result, status_names=status_names)
    return result


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
async def edit_task(  # noqa: PLR0912, PLR0913, PLR0915, C901
    ctx: Context,
    *,
    id: StrId,  # noqa: A002
    title: str | None = None,
    body: str | None = None,
    append_body: str | None = None,
    timestamp: bool = False,
    priority: str | None = None,
    parent: int | None = None,
    ac: list[str] | None = None,
    add_ac: list[str] | None = None,
    remove_ac: list[str] | None = None,
    proof_bundle: str | None = None,
    add_dep: list[int] | None = None,
    remove_dep: list[int] | None = None,
    add_tag: list[str] | None = None,
    remove_tag: list[str] | None = None,
    block_reason: str | None = None,
    archival_reason: str | None = None,
    archival_refs: list[int] | None = None,
) -> SingleTaskResponse:
    """Edit task fields."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    resolved_id = parse_task_id(id, field="id")
    kwargs: dict[str, object] = {}
    body_changed = False
    append_body_changed = False
    # FastMCP maps both omitted optional params and explicit JSON null to Python None.
    # We intentionally use None defaults for tri-state fields: None=no-change,
    # empty string/value clears where supported by AgentView, non-empty sets.
    if title is not None:
        kwargs["title"] = title
    if body is not None:
        normalized_body, body_changed = _normalize_escaped_newlines(body)
        kwargs["body"] = normalized_body
    if append_body:
        normalized_append_body, append_body_changed = _normalize_escaped_newlines(append_body)
        kwargs["append_body"] = normalized_append_body
    if timestamp:
        kwargs["timestamp"] = True
    if priority is not None:
        kwargs["priority"] = priority
    if parent is not None:
        kwargs["parent"] = parent
    if ac is not None:
        kwargs["ac"] = ac
    if add_ac is not None:
        kwargs["add_ac"] = add_ac
    if remove_ac is not None:
        kwargs["remove_ac"] = remove_ac
    if proof_bundle is not None:
        kwargs["proof_bundle"] = proof_bundle
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
    if archival_reason is not None:
        kwargs["archival_reason"] = archival_reason
    if archival_refs is not None:
        kwargs["archival_refs"] = archival_refs
    _sanitize_agent_strings(kwargs)
    try:
        response = app_ctx.engine.agent_view().edit_task(resolved_id, **kwargs)
    except KanbanError as exc:
        _map_kanban_error(exc)
    result = _to_single_task_response(response)
    with contextlib.suppress(Exception):
        if not result.guidance:
            result.guidance = collect_guidance("edit_task", None, result)
    result.guidance = _append_norm_guidance(
        result.guidance,
        changed=body_changed or append_body_changed,
    )
    return result


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def start_work(
    ctx: Context,
    id: StrId,  # noqa: A002
) -> SingleTaskResponse:
    """Claim a task and return its full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    resolved_id = parse_task_id(id, field="id")

    try:
        record = app_ctx.engine.agent_view().start_work(resolved_id)
    except KanbanError as exc:
        _map_kanban_error(exc)
    except ValueError as exc:
        _raise_param_validation(str(exc))
    except FileNotFoundError:
        _raise_not_found(f"Task '{resolved_id}' not found")
    result = _to_single_task_response(record)
    with contextlib.suppress(Exception):
        if not result.guidance:
            result.guidance = collect_guidance("start_work", None, result)
    return result


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def end_work(  # noqa: PLR0913, C901
    ctx: Context,
    *,
    id: StrId,  # noqa: A002
    note: str | None = None,
    outcome: Literal["success", "fail", "reject", "block", "release"] = "success",
    block_reason: str | None = None,
    move_to: str | None = None,
    archival_reason: str | None = None,
    archival_refs: list[int] | None = None,
) -> SingleTaskResponse:
    """Release a task: append note, advance or resolve status, release claim."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    resolved_id = parse_task_id(id, field="id")
    normalized_note = note
    note_changed = False
    if note is not None:
        normalized_note, note_changed = _normalize_escaped_newlines(note)

    # Sanitize string params for common LLM encoding mistakes (e.g. '""' → "")
    ew_kwargs: dict[str, object] = {}
    if block_reason is not None:
        ew_kwargs["block_reason"] = block_reason
    if archival_reason is not None:
        ew_kwargs["archival_reason"] = archival_reason
    _sanitize_agent_strings(ew_kwargs)
    sanitized_block_reason: str | None = ew_kwargs.get("block_reason")  # type: ignore[assignment]
    sanitized_archival_reason: str | None = ew_kwargs.get("archival_reason")  # type: ignore[assignment]

    target_status: str | None = None
    if outcome in {"success", "block", "reject"}:
        target_status = move_to

    try:
        current_status: str | None = None
        if target_status == "archived":
            current_status = (await _show_validated(app_ctx, resolved_id)).status
        _validate_archival_constraints(
            app_ctx,
            task_id=resolved_id,
            current_status=current_status,
            target_status=target_status,
            archival=(archival_reason, archival_refs),
        )
        record = app_ctx.engine.agent_view().end_work(
            resolved_id,
            note=normalized_note,
            outcome=outcome,
            block_reason=sanitized_block_reason,
            move_to=move_to,
            archival_reason=sanitized_archival_reason,
            archival_refs=archival_refs,
        )
    except KanbanError as exc:
        _map_kanban_error(exc)
    except ValueError as exc:
        _raise_param_validation(str(exc))
    except FileNotFoundError:
        _raise_not_found(f"Task '{resolved_id}' not found")
    task = _to_single_task_response(record)
    if outcome in {"success", "block", "fail"}:
        with contextlib.suppress(Exception):
            if not task.guidance:
                task.guidance = collect_guidance("end_work", None, task, outcome=outcome)
    task.guidance = _append_norm_guidance(task.guidance, changed=note_changed)
    return task


# ---------------------------------------------------------------------------
# pick_tasks — gate-filtered dispatch list
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True))
async def pick_tasks(
    ctx: Context,
    *,
    wave_size: int | None = None,
    max_waves: int = 3,
) -> PickTasksResponse:
    """Task selection for dispatch planning (idempotent).

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
        _raise_param_validation(str(exc))


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
        t
        for t in mcp._tool_manager._tools.values()  # noqa: SLF001
        if t.name == _tool_name
    )
    _tool_obj.fn_metadata.output_schema = _single_task_schema


# ---------------------------------------------------------------------------
# Patch input parameter descriptions for better agent discoverability.
# FastMCP auto-generates titles from argument names but has no descriptions.
# ---------------------------------------------------------------------------
_SORT_FIELDS = ["priority", "updated", "id", "title", "status", "created"]
_NORM_PARAM_DESC = "Literal \\n is normalized to a newline; send \\\\n in JSON to preserve a literal \\n."


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
        "tag": {"description": "Filter by tag, e.g. 'phase-2'"},
        "search": {"description": "Full-text search in titles and bodies"},
        "sort": {"enum": _SORT_FIELDS},
        "blocked": {"description": "true = only blocked, false = only unblocked, null = all"},
    },
)

_patch_params(
    "create_task",
    {
        "body": {"description": f"Markdown body (objectives, AC, context). {_NORM_PARAM_DESC}"},
        "depends_on": {"description": "JSON array of dependency task IDs"},
        "parent": {"description": "Parent task ID for subtask hierarchy"},
        "tags": {"description": "JSON array of tags"},
    },
)

_patch_params(
    "move_task",
    {
        "status": {"description": "Target status name, or 'archived' to archive the task"},
    },
)

_patch_params(
    "edit_task",
    {
        "title": {"description": "Replace task title (must be non-empty)"},
        "body": {
            "description": (f"Replace task body; empty string clears, null/omitted = no change. {_NORM_PARAM_DESC}")
        },
        "append_body": {"description": f"Append to body (preserves existing content). {_NORM_PARAM_DESC}"},
        "timestamp": {"description": "Prepend [[date]] timestamp to appended body"},
        "add_dep": {"description": "Add dependency task IDs (JSON array, e.g. [601, 602])"},
        "remove_dep": {"description": "Remove dependency task IDs (JSON array, e.g. [601, 602])"},
        "parent": {"description": "Parent task ID for subtask hierarchy; use 0 to clear parent"},
    },
)

_patch_params(
    "end_work",
    {
        "note": {"description": f"Summary note appended to task body. {_NORM_PARAM_DESC}"},
        "outcome": {
            "description": (
                "success = advance, fail = record failure and release claim, "
                "reject = move back, block = mark blocked and release claim, "
                "release = release claim without changing status"
            ),
        },
        "block_reason": {"description": "Required when outcome=block"},
        "move_to": {
            "description": "Target status when outcome=reject; optional status move when outcome=success or block",
        },
    },
)
