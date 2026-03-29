"""OwlBear MCP kanban server — exposes kanban-md operations as MCP tools."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.fastmcp import Context, FastMCP

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    "AppContext",
    "_run_kanban",
    "app_lifespan",
    "board_context",
    "create_task",
    "edit_task",
    "list_tasks",
    "mcp",
    "move_task",
    "pick_task",
    "show_task",
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


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Discover kanban-md binary and yield AppContext for the MCP session.

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
    yield AppContext(kanban_bin=kanban_bin, kanban_dir=_DEFAULT_KANBAN_DIR)


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


@mcp.tool()
async def list_tasks(  # noqa: PLR0913
    ctx: Context,
    *,
    status: str = "",
    tag: str = "",
    priority: str = "",
    block_filter: str = "",
    search: str = "",
    sort: str = "",
    unclaimed: bool = False,
) -> str:
    """List kanban tasks with optional filters. Returns compact text representation."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    args: list[str] = ["list", "--compact"]
    if status:
        args += ["--status", status]
    if tag:
        args += ["--tag", tag]
    if priority:
        args += ["--priority", priority]
    if block_filter == "blocked":
        args.append("--blocked")
    elif block_filter == "not-blocked":
        args.append("--not-blocked")
    if search:
        args += ["--search", search]
    if sort:
        args += ["--sort", sort]
    if unclaimed:
        args.append("--unclaimed")
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        return f"error: {stderr.strip()}"
    return stdout


@mcp.tool()
async def show_task(ctx: Context, task_id: str) -> str:
    """Show a single task by ID with full details."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    stdout, stderr, rc = await _run_kanban(app_ctx, "show", task_id, "--json")
    if rc != 0:
        return f"error: {stderr.strip()}"
    return stdout


@mcp.tool()
async def create_task(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    priority: str = "",
    tags: str = "",
    body: str = "",
    depends_on: str = "",
    claim: str = "",
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
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        return f"error: {stderr.strip()}"
    return stdout


@mcp.tool()
async def move_task(ctx: Context, task_id: str, status: str) -> str:
    """Move a task to the specified status column."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    stdout, stderr, rc = await _run_kanban(app_ctx, "move", task_id, status)
    if rc != 0:
        return f"error: {stderr.strip()}"
    return stdout


@mcp.tool()
async def edit_task(  # noqa: PLR0913
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
) -> str:
    """Edit task fields including status, priority, body, claim, and block state."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    args: list[str] = ["edit", task_id]
    str_flags: list[tuple[str, str]] = [
        ("--body", body),
        ("--block", block),
        ("--tags", tags),
        ("--priority", priority),
        ("--claim", claim),
        ("--status", status),
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
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        return f"error: {stderr.strip()}"
    return stdout


@mcp.tool()
async def pick_task(
    ctx: Context,
    status: str = "",
    claim: str = "",
    move: str = "",
    tags: str = "",
) -> str:
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
    stdout, stderr, rc = await _run_kanban(app_ctx, *args)
    if rc != 0:
        return f"error: {stderr.strip()}"
    return stdout


@mcp.tool()
async def board_context(ctx: Context) -> str:
    """Get a compact board context snapshot showing task distribution."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    stdout, stderr, rc = await _run_kanban(app_ctx, "context")
    if rc != 0:
        return f"error: {stderr.strip()}"
    return stdout
