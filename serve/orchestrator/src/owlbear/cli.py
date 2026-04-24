"""OwlBear CLI — trigger commands for orchestrator dispatch."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from owlbear.planner.board import read_board
from owlbear.planner.selector import select_tasks
from owlbear_orchestrator.acp_client import AcpClient, AcpClientError

if TYPE_CHECKING:
    from owlbear.planner.models import DispatchEntry

app = typer.Typer()

_KANBAN_BIN = Path("kanban/kanban-md")
_KANBAN_DIR = Path("kanban")
_COPILOT_CMD = "gh"


def _check_copilot() -> None:
    """Verify Copilot CLI is installed; print install hint to stderr and exit 1 if not."""
    if shutil.which(_COPILOT_CMD) is None:
        typer.echo(
            "Copilot CLI not found. Install: gh extension install github/gh-copilot",
            err=True,
        )
        raise typer.Exit(code=1)


async def _do_dispatch(entry: DispatchEntry) -> None:
    """Dispatch one entry via ACP. Raises AcpClientError on connection failure."""
    _session_name = f"owlbear-{entry.agent}-{entry.task_id}"
    async with AcpClient(None) as client:  # type: ignore[arg-type]
        coro = client.new_session(cwd=str(Path.cwd()))
        if asyncio.iscoroutine(coro):
            await coro


@app.command()
def dispatch(task_id: int) -> None:
    """Dispatch a specific task to its agent via ACP."""
    _check_copilot()

    async def _impl() -> tuple[int, str]:
        tasks = await read_board(_KANBAN_BIN, _KANBAN_DIR)
        task = next((t for t in tasks if t.id == task_id), None)
        if task is None:
            typer.echo(f"Task #{task_id} not found.", err=True)
            raise typer.Exit(code=1)
        if task.claimed_by is not None:
            typer.echo(
                f"Task #{task_id} is already claimed by {task.claimed_by}.",
                err=True,
            )
            raise typer.Exit(code=1)
        plan = select_tasks([task])
        if not plan.entries:
            typer.echo(f"Task #{task_id} not found.", err=True)
            raise typer.Exit(code=1)
        entry = plan.entries[0]
        await _do_dispatch(entry)
        return entry.task_id, entry.agent

    try:
        dispatched_id, agent = asyncio.run(_impl())
    except AcpClientError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Dispatched #{dispatched_id} to {agent}")


@app.command()
def run(
    *,
    run_all: Annotated[
        bool, typer.Option("--all", help="Loop until board is empty.")
    ] = False,
) -> None:
    """Dispatch the top-priority task; use --all to loop until the board is empty."""
    _check_copilot()

    async def _once() -> tuple[int, str] | None:
        tasks = await read_board(_KANBAN_BIN, _KANBAN_DIR)
        plan = select_tasks(tasks)
        if not plan.entries:
            return None
        entry = plan.entries[0]
        await _do_dispatch(entry)
        return entry.task_id, entry.agent

    def _run_once() -> tuple[int, str] | None:
        try:
            return asyncio.run(_once())
        except AcpClientError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc

    if not run_all:
        result = _run_once()
        if result is None:
            typer.echo("No actionable tasks on the board.")
        else:
            t_id, agent = result
            typer.echo(f"Dispatched #{t_id} to {agent}")
    else:
        while True:
            result = _run_once()
            if result is None:
                break
            t_id, agent = result
            typer.echo(f"Dispatched #{t_id} to {agent}")


@app.command()
def status() -> None:
    """Print task counts per status column and any blocked tasks."""
    result = subprocess.run(  # noqa: S603
        [str(_KANBAN_BIN), "list", "--json", "--dir", str(_KANBAN_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    tasks: list[dict] = json.loads(result.stdout or "[]")
    counts: Counter[str] = Counter(t["status"] for t in tasks)
    if counts:
        typer.echo(" | ".join(f"{s}: {c}" for s, c in sorted(counts.items())))
    for task in tasks:
        if task.get("blocked"):
            typer.echo(f"BLOCKED #{task['id']} {task['title']}: {task['blocked']}")
