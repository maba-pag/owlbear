"""OwlBear MCP kanban server — exposes kanban-md operations as MCP tools."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from owlbear_mcp_kanban.models import KanbanTask

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    "AppContext",
    "_apply_tool_exclusions",
    "_run_kanban",
    "app_lifespan",
    "create_task",
    "edit_task",
    "end_work",
    "list_tasks",
    "mcp",
    "move_task",
    "pick_task",
    "show_task",
    "start_work",
]

_DEFAULT_KANBAN_DIR = Path("kanban")
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
            "Set KANBAN_BIN or place binary at kanban/kanban-md.exe."
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
    """List kanban tasks with optional filters. Returns lean task array."""
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
    _strip = {"body", "file", "created", "updated"}
    try:
        tasks = json.loads(stdout)
        return [{k: v for k, v in task.items() if k not in _strip} for task in tasks]
    except (json.JSONDecodeError, AttributeError) as exc:
        msg = f"Invalid task JSON: {stdout[:200]}"
        raise ToolError(msg) from exc


# Set outputSchema for list_tasks (lean task array)
_list_tasks_tool_obj = next(
    t for t in mcp._tool_manager._tools.values() if t.name == "list_tasks"  # noqa: SLF001
)
_list_tasks_tool_obj.fn_metadata.output_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "status": {"type": "string"},
            "priority": {"type": "string"},
            "class": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "blocked": {"type": "boolean"},
            "block_reason": {"type": ["string", "null"]},
            "claimed_by": {"type": ["string", "null"]},
            "claimed_at": {"type": ["string", "null"]},
            "started": {"type": ["string", "null"]},
            "completed": {"type": ["string", "null"]},
            "assignee": {"type": ["string", "null"]},
            "due": {"type": ["string", "null"]},
            "estimate": {"type": ["string", "null"]},
            "parent": {"type": ["integer", "null"]},
            "depends_on": {"type": "array", "items": {"type": "integer"}},
        },
    },
}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def show_task(ctx: Context, task_id: str) -> KanbanTask:
    """Show a single task by ID with full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    stdout, stderr, rc = await _run_kanban(app_ctx, "show", task_id, "--json")
    if rc != 0:
        msg = stderr.strip()
        raise ToolError(msg)
    try:
        return KanbanTask.model_validate_json(stdout)
    except ValidationError as exc:
        msg = f"Invalid task JSON: {exc}"
        raise ToolError(msg) from exc


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def create_task(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    body: str = "",
    claim: str = "",
    depends_on: str = "",
    parent: int = 0,
    priority: str = "",
    status: str = "",
    tags: str = "",
) -> str:
    """Create a new kanban task with the given title and optional metadata."""
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
    if claim:
        args += ["--claim", claim]
    if status:
        args += ["--status", status]
    if parent > 0:
        args += ["--parent", str(parent)]
    args.append("--json")
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        return f"error: {stderr.strip() or stdout.strip()}"
    return stdout


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=True))
async def move_task(ctx: Context, task_id: str, status: str) -> KanbanTask:
    """Move a task to the specified status column."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    stdout, stderr, rc = await _run_kanban(app_ctx, "move", task_id, status, "--json")
    if rc != 0:
        msg = stderr.strip()
        raise ToolError(msg)
    try:
        return KanbanTask.model_validate_json(stdout)
    except ValidationError as exc:
        msg = f"Invalid task JSON: {exc}"
        raise ToolError(msg) from exc


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False, idempotentHint=False))
async def edit_task(  # noqa: PLR0913, C901
    ctx: Context,
    *,
    task_id: str,
    body: str = "",
    block: str = "",
    unblock: bool = False,
    tags: str = "",
    priority: str = "",
    append_body: str = "",
    claim: str = "",
    release: bool = False,
    status: str = "",
    timestamp: bool = False,
    add_dep: int = 0,
    remove_dep: int = 0,
    parent: int = 0,
    title: str = "",
) -> KanbanTask:
    """Edit task fields: status, priority, body, claim, block state, deps, parent, and title."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    args: list[str] = ["edit", task_id]
    str_flags: list[tuple[str, str]] = [
        ("--body", body),
        ("--block", block),
        ("--tags", tags),
        ("--priority", priority),
        ("--claim", claim),
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
    if release:
        args.append("--release")
    if timestamp:
        args.append("--timestamp")
    if add_dep > 0:
        args += ["--add-dep", str(add_dep)]
    if remove_dep > 0:
        args += ["--remove-dep", str(remove_dep)]
    if parent > 0:
        args += ["--parent", str(parent)]
    args.append("--json")
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        msg = stderr.strip()
        raise ToolError(msg)
    try:
        return KanbanTask.model_validate_json(stdout)
    except ValidationError as exc:
        msg = f"Invalid task JSON: {exc}"
        raise ToolError(msg) from exc


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def pick_task(
    ctx: Context,
    status: str = "",
    claim: str = "",
    move: str = "",
    tags: str = "",
) -> KanbanTask:
    """Pick the next available unclaimed task matching the given filters."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    args: list[str] = ["pick"]
    if status:
        args += ["--status", status]
    if claim:
        args += ["--claim", claim]
    if move:
        args += ["--move", move]
    if tags:
        args += ["--tags", tags]
    args.append("--json")
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        msg = stderr.strip()
        raise ToolError(msg)
    try:
        return KanbanTask.model_validate_json(stdout)
    except ValidationError as exc:
        msg = f"Invalid task JSON: {exc}"
        raise ToolError(msg) from exc


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def start_work(ctx: Context, task_id: str, claim: str = "") -> str:
    """Claim a task and return its full details as JSON with injected claim_name.

    Compound operation: replaces separate claim + show_task calls with a single call.
    If no claim is provided, auto-generates one via kanban-md agent-name.
    The task remains at its current status — no status change is made.
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context

    # Step 1: resolve claim name
    if claim:
        claim_name = claim
    else:
        stdout, stderr, rc = await _run_kanban(app_ctx, "agent-name")
        if rc != 0:
            return f"error: {stderr.strip() or stdout.strip()}"
        claim_name = stdout.strip()

    # Step 2: claim the task (no --status: stays at current status)
    stdout, stderr, rc = await _run_kanban(app_ctx, "edit", task_id, "--claim", claim_name)
    if rc != 0:
        return f"error: {stderr.strip() or stdout.strip()}"

    # Step 3: fetch task details
    stdout, stderr, rc = await _run_kanban(app_ctx, "show", task_id, "--json")
    if rc != 0:
        return f"error: {stderr.strip() or stdout.strip()}"

    # Step 4: inject claim_name and return merged JSON
    data: dict = json.loads(stdout)
    data["claim_name"] = claim_name
    return json.dumps(data)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def end_work(  # noqa: PLR0911, PLR0912, PLR0913, C901
    ctx: Context,
    *,
    task_id: str,
    note: str,
    outcome: Literal["success", "fail", "block", "reject"] = "success",
    block_reason: str = "",
    move_to: str = "ideation",
    claim: str = "",
) -> str:
    """Compound operation: append note, optionally advance status, release claim.

    Outcomes:
    - success: advance to next status (or archive if already at last status)
    - fail: keep current status, release claim
    - block: mark blocked with block_reason, release claim
    - reject: move to move_to status (default: ideation), release claim
    """
    app_ctx: AppContext = ctx.request_context.lifespan_context

    if outcome == "block" and not block_reason:
        return "error: block_reason is required when outcome=block"

    claim_to_use = claim
    current_status = ""

    # show is needed for success (to derive next status) or when claim not provided
    if outcome == "success" or not claim_to_use:
        stdout, stderr, rc = await _run_kanban(app_ctx, "show", task_id, "--json")
        if rc != 0:
            return f"error: show failed: {stderr.strip() or stdout.strip()}"
        task_data: dict = json.loads(stdout)
        current_status = task_data.get("status", "")
        if not claim_to_use:
            claim_to_use = task_data.get("claimed_by", "")

    edit_args: list[str] = ["edit", task_id, "-a", note, "--timestamp", "--release"]
    if claim_to_use:
        edit_args += ["--claim", claim_to_use]

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
            return f"error: edit failed: {stderr.strip() or stdout.strip()}"
        if is_last:
            arc_out, arc_err, arc_rc = await _run_kanban(app_ctx, "archive", task_id)
            if arc_rc != 0:
                return f"error: archive failed: {arc_err.strip() or arc_out.strip()}"
            return arc_out
        return stdout

    if outcome == "fail":
        edit_args.append("--json")
        stdout, stderr, rc = await _run_kanban(app_ctx, *edit_args)
        if rc != 0:
            return f"error: edit failed: {stderr.strip() or stdout.strip()}"
        return stdout

    if outcome == "block":
        edit_args += ["--block", block_reason]
        edit_args.append("--json")
        stdout, stderr, rc = await _run_kanban(app_ctx, *edit_args)
        if rc != 0:
            return f"error: edit failed: {stderr.strip() or stdout.strip()}"
        return stdout

    if outcome == "reject":
        edit_args += ["--status", move_to]
        edit_args.append("--json")
        stdout, stderr, rc = await _run_kanban(app_ctx, *edit_args)
        if rc != 0:
            return f"error: edit failed: {stderr.strip() or stdout.strip()}"
        return stdout

    return f"error: unknown outcome {outcome!r}"


# Set outputSchema for show_task, move_task, pick_task to KanbanTask with alias keys
# (field name `class_` maps to alias `class`; must use by_alias=True to match MCP spec).
# This overrides FastMCP's auto-generated schema (which uses Python field names) before
# tool.output_schema cached_property is first accessed.
_kanbantask_schema = KanbanTask.model_json_schema(by_alias=True)
for _tool_name in ("show_task", "move_task", "pick_task", "edit_task"):
    _tool_obj = next(t for t in mcp._tool_manager._tools.values() if t.name == _tool_name)  # noqa: SLF001
    _tool_obj.fn_metadata.output_schema = _kanbantask_schema
