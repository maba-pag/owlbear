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

app = typer.Typer()

_KANBAN_BIN = Path("kanban/kanban-md.exe")
_KANBAN_CONFIG = Path("kanban/config.yml")

console = Console()


def _read_status_order() -> list[str]:
    """Return status names from kanban/config.yml in configured order."""
    config = yaml.safe_load(_KANBAN_CONFIG.read_text(encoding="utf-8"))
    return [s["name"] for s in config.get("statuses", [])]


def _get_tasks() -> list[dict[str, Any]]:
    """Invoke ``kanban-md list --json`` and return parsed task list."""
    result = subprocess.run(  # noqa: S603
        [str(_KANBAN_BIN), "list", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return json.loads(result.stdout)  # type: ignore[return-value]


def _get_log_entries() -> list[dict[str, Any]]:
    """Invoke ``kanban-md log --action move --json`` and return parsed entries."""
    result = subprocess.run(  # noqa: S603
        [str(_KANBAN_BIN), "log", "--action", "move", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return json.loads(result.stdout)  # type: ignore[return-value]


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
    tasks = _get_tasks()

    if not tasks:
        typer.echo("No tasks on the board.")
        return

    status_order = _read_status_order()
    log_entries = _get_log_entries()

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
