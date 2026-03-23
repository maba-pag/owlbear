"""Board command — display the kanban board grouped by status."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.table import Table

from bearclaw.commands import _cli_error

app = typer.Typer()

_KANBAN_BIN = Path("kanban/kanban-md.exe")
_KANBAN_CONFIG = Path("kanban/config.yml")

console = Console()


def _read_status_order() -> list[str]:
    """Return status names from kanban/config.yml in configured order."""
    config = yaml.safe_load(_KANBAN_CONFIG.read_text(encoding="utf-8"))
    return [s["name"] for s in config.get("statuses", [])]


def _run_kanban(stage: str, args: list[str]) -> list[dict[str, Any]]:
    """Invoke a kanban-md subcommand and return the parsed JSON output.

    Calls ``_cli_error`` (NoReturn) on any failure so callers never see
    exceptions from this function.

    Args:
        stage: Human-readable stage name used in error messages
               (e.g. ``"task-list"`` or ``"move-log"``).
        args:  Full argument list including the binary path.
    """
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)  # noqa: S603
    except FileNotFoundError:
        _cli_error("kanban-md not found — is the binary installed?")

    if result.returncode != 0:
        _cli_error(f"kanban-md {stage} command failed (exit {result.returncode})")

    try:
        return json.loads(result.stdout) if result.stdout.strip() else []  # type: ignore[return-value]
    except json.JSONDecodeError as exc:
        _cli_error(f"kanban-md {stage} returned invalid JSON: {exc}")


def _assignee_display(task: dict[str, Any]) -> str:
    """Return the best available assignee string: ``assignee`` > ``claimed_by`` > ``--``."""
    return task.get("assignee") or task.get("claimed_by") or "--"


def _destination_status(detail: str) -> str:
    """Extract the destination status from a move detail string ``'from -> to'``."""
    if " -> " in detail:
        return detail.split(" -> ", 1)[1].strip()
    return ""


def _age_in_status(task: dict[str, Any], log_entries: list[dict[str, Any]]) -> str:
    """Return human-readable age: days since latest matching move or task creation."""
    today = datetime.now(tz=UTC).date()
    task_id = task["id"]
    current_status = task["status"]

    matching = [
        e
        for e in log_entries
        if (
            e.get("task_id") == task_id
            and e.get("action") == "move"
            and _destination_status(str(e.get("detail", ""))) == current_status
        )
    ]

    if matching:
        latest = max(matching, key=lambda e: e["timestamp"])
        ref_date = datetime.fromisoformat(latest["timestamp"]).date()
    else:
        ref_date = datetime.fromisoformat(task["created"]).date()

    return f"{(today - ref_date).days}d"


@app.command()
def board() -> None:
    """Display the kanban board grouped by status."""
    tasks = _run_kanban("task-list", [str(_KANBAN_BIN), "list", "--json"])

    if not tasks:
        typer.echo("No tasks on the board.")
        return

    status_order = _read_status_order()
    log_entries = _run_kanban("move-log", [str(_KANBAN_BIN), "log", "--action", "move", "--json"])

    by_status: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        s = task.get("status", "unknown")
        by_status.setdefault(s, []).append(task)

    ordered = [s for s in status_order if s in by_status]
    remaining = [s for s in by_status if s not in status_order]

    for status_name in ordered + remaining:
        status_tasks = by_status[status_name]
        typer.echo(f"\n{status_name}")

        table = Table(show_header=True, box=None)
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Assignee")
        table.add_column("Age")
        table.add_column("Tags")

        for t in status_tasks:
            table.add_row(
                str(t.get("id", "")),
                t.get("title", ""),
                _assignee_display(t),
                _age_in_status(t, log_entries),
                ", ".join(t.get("tags", [])),
            )

        console.print(table)
