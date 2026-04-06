"""OwlBear MCP kanban server — exposes kanban-md operations as MCP tools."""

from __future__ import annotations

import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BeforeValidator, ValidationError

from owlbear_mcp_kanban.models import KanbanTask

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


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
    "_parse_task_json",
    "_run_kanban",
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
_DEFAULT_KANBAN_BIN = _DEFAULT_KANBAN_DIR / "kanban-md.exe"


class _ForwardSlashPath(Path):
    """Path subclass whose ``__str__`` always uses forward slashes.

    On Windows, ``pathlib.Path`` normalises forward slashes to backslashes in
    ``__str__``.  When an env-var path such as ``KANBAN_BIN=/usr/bin/kanban``
    is stored as a plain ``Path``, ``str(path)`` would return the
    backslash-separated form and break equality checks against the original
    string.  This subclass preserves the user-supplied separator, enabling
    cross-platform env-var round-trips.
    """

    def __str__(self) -> str:
        return super().__str__().replace(os.sep, "/")


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    kanban_bin: Path
    kanban_dir: Path
    statuses: list[str] = field(default_factory=list)

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
    """Discover kanban-md binary, load board statuses, yield AppContext for the MCP session.

    Raises:
        FileNotFoundError: When the kanban-md binary cannot be found.
    """
    bin_env = os.environ.get("KANBAN_BIN")
    kanban_bin: Path = _ForwardSlashPath(bin_env) if bin_env else _DEFAULT_KANBAN_BIN
    if not kanban_bin.exists():  # noqa: ASYNC240
        msg = (
            f"kanban-md binary not found: {kanban_bin!r}. "
            "Set KANBAN_BIN or place binary at .owlbear/kanban/kanban-md.exe."
        )
        raise FileNotFoundError(msg)
    _apply_tool_exclusions(_server)
    # Load board statuses once at startup from config --json
    _boot = AppContext(kanban_bin=kanban_bin, kanban_dir=_DEFAULT_KANBAN_DIR)
    statuses: list[str] = []
    try:
        _cfg_out, _cfg_err, _cfg_rc = await _run_kanban(_boot, "config", "--json")
        if _cfg_rc == 0:
            _cfg_data = json.loads(_cfg_out)
            statuses = _cfg_data.get("statuses", [])
    except Exception:  # noqa: BLE001, S110
        pass
    yield AppContext(kanban_bin=kanban_bin, kanban_dir=_DEFAULT_KANBAN_DIR, statuses=statuses)


mcp = FastMCP("owlbear-kanban", lifespan=app_lifespan)


async def _run_kanban(ctx: AppContext, *args: str) -> tuple[str, str, int]:
    """Run kanban-md with the given args plus ``--no-color --dir`` flags.

    Returns:
        A ``(stdout, stderr, returncode)`` tuple.
    """
    full_args = (*args, "--no-color", "--dir", str(ctx.kanban_dir))
    proc = await asyncio.create_subprocess_exec(
        str(ctx.kanban_bin),
        *full_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    return (
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
        proc.returncode or 0,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_tasks(  # noqa: PLR0912, PLR0913, C901
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
) -> list[dict]:
    """List kanban tasks with optional filters."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    args: list[str] = ["list", "--json"]
    if status:
        args += ["--status", status]
    if tag:
        args += ["--tag", tag]
    if priority:
        args += ["--priority", priority]
    if search:
        args += ["--search", search]
    if sort:
        args += ["--sort", sort]
    if unclaimed:
        args.append("--unclaimed")
    if archived:
        args.append("--archived")
    if limit > 0:
        args += ["--limit", str(limit)]
    if reverse:
        args.append("--reverse")
    if blocked is True:
        args.append("--blocked")
    elif blocked is False:
        args.append("--not-blocked")
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        msg = stderr.strip() or stdout.strip()
        raise ToolError(msg)
    _strip = {
        "body", "file", "created", "updated",
        "class", "started", "completed", "assignee", "claimed_by", "claimed_at",
        "due", "estimate",
    }
    try:
        tasks = json.loads(stdout)
        lean = []
        for task in tasks:
            row = {k: v for k, v in task.items() if k not in _strip}
            row["claimed"] = task.get("claimed_by") is not None
            lean.append(row)
    except (json.JSONDecodeError, AttributeError) as exc:
        msg = f"Invalid task JSON: {stdout[:200]}"
        raise ToolError(msg) from exc
    else:
        return lean


# Set outputSchema for list_tasks (lean task array)
_list_tasks_tool_obj = next(
    t for t in mcp._tool_manager._tools.values() if t.name == "list_tasks"  # noqa: SLF001
)
_list_tasks_tool_obj.fn_metadata.output_schema = {
    "type": "object",
    "properties": {
        "result": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "status": {"type": "string"},
                    "priority": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "blocked": {"type": "boolean"},
                    "block_reason": {"type": ["string", "null"]},
                    "claimed": {"type": "boolean"},
                    "parent": {"type": ["integer", "null"]},
                    "depends_on": {"type": "array", "items": {"type": "integer"}},
                },
            },
        },
    },
    "required": ["result"],
}


async def _show_validated(app_ctx: AppContext, task_id: str) -> KanbanTask:
    """Run ``show <id> --json`` and return a validated KanbanTask."""
    stdout, stderr, rc = await _run_kanban(app_ctx, "show", task_id, "--json")
    if rc != 0:
        msg = stderr.strip()
        raise ToolError(msg)
    try:
        return KanbanTask.model_validate_json(stdout)
    except ValidationError as exc:
        msg = f"Invalid task JSON: {exc}"
        raise ToolError(msg) from exc


async def _parse_task_json(stdout: str) -> KanbanTask:
    """Parse raw ``--json`` output into a validated KanbanTask."""
    try:
        return KanbanTask.model_validate_json(stdout)
    except ValidationError as exc:
        msg = f"Invalid task JSON: {exc}"
        raise ToolError(msg) from exc


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
    args: list[str] = ["create", title]
    if priority:
        args += ["--priority", priority]
    if tags:
        args += ["--tags", tags]
    if body:
        args += ["--body", body]
    if depends_on:
        args += ["--depends-on", depends_on]
    if status:
        args += ["--status", status]
    if parent > 0:
        args += ["--parent", str(parent)]
    args.append("--json")
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        msg = stderr.strip() or stdout.strip()
        raise ToolError(msg)
    return await _parse_task_json(stdout)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True))
async def move_task(ctx: Context, task_id: StrId, status: str) -> KanbanTask:
    """Move a task to the specified status column, or archive it when status is "archived"."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    if status == "archived":
        stdout, stderr, rc = await _run_kanban(app_ctx, "archive", task_id, "--json")
        if rc != 0:
            msg = stderr.strip()
            raise ToolError(msg)
        return await _parse_task_json(stdout)
    stdout, stderr, rc = await _run_kanban(app_ctx, "move", task_id, status, "--json")
    if rc != 0:
        msg = stderr.strip()
        raise ToolError(msg)
    return await _parse_task_json(stdout)


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
    args: list[str] = ["edit", task_id]
    str_flags: list[tuple[str, str]] = [
        ("--body", body),
        ("--block", block),
        ("--priority", priority),
        ("--status", status),
        ("--title", title),
    ]
    for flag, value in str_flags:
        if value:
            args += [flag, value]
    if append_body:
        args += ["-a", append_body]
    if unblock:
        args.append("--unblock")
    if timestamp:
        args.append("--timestamp")
    if add_tag:
        args += ["--add-tag", add_tag]
    if remove_tag:
        args += ["--remove-tag", remove_tag]
    if add_dep:
        args += ["--add-dep", add_dep]
    if remove_dep:
        args += ["--remove-dep", remove_dep]
    if parent > 0:
        args += ["--parent", str(parent)]
    args.append("--json")
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        errmsg = stderr.strip() or stdout.strip()
        # Auto-retry with --claim when the task is claimed by this agent
        if "TASK_CLAIMED" in errmsg or "is claimed by" in errmsg:
            name_out, name_err, name_rc = await _run_kanban(app_ctx, "agent-name")
            if name_rc == 0:
                claim_name = name_out.strip()
                if claim_name and claim_name in errmsg:
                    retry_args = [*args, "--claim", claim_name]
                    stdout, stderr, rc = await _run_kanban(app_ctx, *retry_args)
                    if rc != 0:
                        msg = stderr.strip() or stdout.strip()
                        raise ToolError(msg)
                else:
                    raise ToolError(errmsg)
            else:
                raise ToolError(errmsg)
        else:
            raise ToolError(errmsg)
    try:
        return KanbanTask.model_validate_json(stdout)
    except ValidationError as exc:
        msg = f"Invalid task JSON: {exc}"
        raise ToolError(msg) from exc


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def start_work(ctx: Context, task_id: StrId) -> KanbanTask:
    """Claim a task and return its full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context

    # Step 1: blocked guard — reject if task is blocked
    task = await _show_validated(app_ctx, task_id)
    if task.blocked:
        reason = task.block_reason or "unknown"
        msg = f"task {task_id} is blocked: {reason}"
        raise ToolError(msg)

    # Step 2: auto-generate claim name
    stdout, stderr, rc = await _run_kanban(app_ctx, "agent-name")
    if rc != 0:
        msg = stderr.strip() or stdout.strip()
        raise ToolError(msg)
    claim_name = stdout.strip()

    # Step 3: claim the task
    stdout, stderr, rc = await _run_kanban(app_ctx, "edit", task_id, "--claim", claim_name)
    if rc != 0:
        msg = stderr.strip() or stdout.strip()
        raise ToolError(msg)

    # Step 4: return validated task details (re-fetch after claim)
    return await _show_validated(app_ctx, task_id)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def end_work(  # noqa: PLR0912, PLR0913, C901
    ctx: Context,
    *,
    task_id: StrId,
    note: str,
    outcome: Literal["success", "fail", "block", "reject"] = "success",
    block_reason: str = "",
    move_to: str = "ideation",
) -> KanbanTask:
    """Release a task: append note, advance or resolve status, release claim."""
    app_ctx: AppContext = ctx.request_context.lifespan_context

    if outcome == "block" and not block_reason:
        msg = "block_reason is required when outcome=block"
        raise ToolError(msg)

    current_status = ""

    # show is needed for success to derive next status
    if outcome == "success":
        task = await _show_validated(app_ctx, task_id)
        current_status = task.status

    edit_args: list[str] = ["edit", task_id, "-a", note, "--timestamp", "--release"]

    if outcome == "success":
        statuses = app_ctx.statuses
        is_last = bool(statuses) and current_status == statuses[-1]
        if not is_last:
            idx = statuses.index(current_status) if current_status in statuses else -1
            if idx >= 0 and idx + 1 < len(statuses):
                edit_args += ["--status", statuses[idx + 1]]
        edit_args.append("--json")
        stdout, stderr, rc = await _run_kanban(app_ctx, *edit_args)
        if rc != 0:
            msg = f"edit failed: {stderr.strip() or stdout.strip()}"
            raise ToolError(msg)
        if is_last:
            arc_out, arc_err, arc_rc = await _run_kanban(app_ctx, "archive", task_id, "--json")
            if arc_rc != 0:
                msg = f"archive failed: {arc_err.strip() or arc_out.strip()}"
                raise ToolError(msg)
            return await _parse_task_json(arc_out)
        return await _parse_task_json(stdout)

    if outcome == "fail":
        edit_args.append("--json")
        stdout, stderr, rc = await _run_kanban(app_ctx, *edit_args)
        if rc != 0:
            msg = f"edit failed: {stderr.strip() or stdout.strip()}"
            raise ToolError(msg)
        return await _parse_task_json(stdout)

    if outcome == "block":
        edit_args += ["--block", block_reason]
        edit_args.append("--json")
        stdout, stderr, rc = await _run_kanban(app_ctx, *edit_args)
        if rc != 0:
            msg = f"edit failed: {stderr.strip() or stdout.strip()}"
            raise ToolError(msg)
        return await _parse_task_json(stdout)

    if outcome == "reject":
        edit_args += ["--status", move_to]
        edit_args.append("--json")
        stdout, stderr, rc = await _run_kanban(app_ctx, *edit_args)
        if rc != 0:
            msg = f"edit failed: {stderr.strip() or stdout.strip()}"
            raise ToolError(msg)
        return await _parse_task_json(stdout)

    msg = f"unknown outcome {outcome!r}"
    raise ToolError(msg)


# ---------------------------------------------------------------------------
# pick_tasks — gate-filtered dispatch list
# ---------------------------------------------------------------------------

_PICK_AND_PATTERN = re.compile(r"\band\b", re.IGNORECASE)
_PICK_AC_PATTERN = re.compile(r"(?m)^\s*(-\s|\d+\.\s)")
_PICK_CLARITY_STATUSES = frozenset({"todo", "in-progress", "review", "docs", "done"})
_PICK_NON_IMPL_TAGS = frozenset(
    {"research", "docs", "type:config", "type:docs", "test", "type:test", "agent", "quality"}
)

_PICK_PRIORITY_RANK: dict[str, int] = {
    "critical": 0,
    "needed": 1,
    "important": 2,
    "nice-to-have": 3,
    "someday": 4,
}
_PICK_STATUS_RANK: dict[str, int] = {
    "done": 0,
    "docs": 1,
    "review": 2,
    "in-progress": 3,
    "todo": 4,
    "backlog": 5,
    "ideation": 6,
}
_PICK_MAX_PRIORITY_RANK = max(_PICK_PRIORITY_RANK.values())
_PICK_MAX_STATUS_RANK = max(_PICK_STATUS_RANK.values())


def _check_pick_gates(task: dict) -> bool:
    """Return True if task passes atomicity, TDD, and clarity gates."""
    title: str = task.get("title", "")
    status: str = task.get("status", "")
    body: str = task.get("body") or ""

    if _PICK_AND_PATTERN.search(title):
        return False
    if status == "in-progress" and "## Test-Writer Notes" not in body:
        tags: list[str] = task.get("tags") or []
        if not _PICK_NON_IMPL_TAGS.intersection(tags):
            return False
    return not (status in _PICK_CLARITY_STATUSES and not _PICK_AC_PATTERN.search(body))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def pick_tasks(ctx: Context, *, limit: int = 25, tag: str = "") -> dict:
    """Pick dispatchable tasks: gate-filtered, sorted by priority/status, capped at limit.

    Optional tag pre-filters candidates before gating (e.g. 'phase-2').
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context
    args: list[str] = ["list", "--json", "--unblocked", "--not-blocked", "--unclaimed"]
    if tag:
        args += ["--tag", tag]
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        msg = stderr.strip() or stdout.strip()
        raise ToolError(msg)
    try:
        tasks: list[dict] = json.loads(stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        msg = f"Invalid task JSON: {stdout[:200]}"
        raise ToolError(msg) from exc

    passing = [t for t in tasks if _check_pick_gates(t)]

    def _sort_key(task: dict) -> tuple[int, int]:
        prank = _PICK_PRIORITY_RANK.get(task.get("priority", ""), _PICK_MAX_PRIORITY_RANK + 1)
        srank = _PICK_STATUS_RANK.get(task.get("status", ""), _PICK_MAX_STATUS_RANK + 1)
        return (prank, srank)

    passing.sort(key=_sort_key)
    capped = passing[:limit]
    return {
        "dispatch": [{"task_id": int(t["id"]), "status": str(t["status"])} for t in capped]
    }


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
_STATUSES = ["ideation", "backlog", "todo", "in-progress", "review", "docs", "done"]
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


_patch_params("list_tasks", {
    "status": {"enum": _STATUSES},
    "tag": {"description": "Filter by tag, e.g. 'phase-2'"},
    "priority": {"enum": _PRIORITIES},
    "search": {"description": "Full-text search in titles and bodies"},
    "sort": {"enum": _SORT_FIELDS},
    "blocked": {"description": "true = only blocked, false = only unblocked, null = all"},
})

_patch_params("create_task", {
    "body": {"description": "Markdown body (objectives, AC, context)"},
    "depends_on": {"description": "Comma-separated dependency task IDs"},
    "parent": {"description": "Parent task ID for subtask hierarchy"},
    "priority": {"enum": _PRIORITIES},
    "status": {"enum": _STATUSES},
    "tags": {"description": "Comma-separated tags"},
})

_patch_params("move_task", {
    "status": {"enum": [*_STATUSES, "archived"]},
})

_patch_params("edit_task", {
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
})

_patch_params("end_work", {
    "note": {"description": "Summary note appended to task body"},
    "outcome": {
        "description": "success = advance, fail = stay, block = mark blocked, reject = move back",
    },
    "block_reason": {"description": "Required when outcome=block"},
    "move_to": {"enum": _STATUSES, "description": "Target status when outcome=reject"},
})
