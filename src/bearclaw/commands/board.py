"""Board command — display the kanban board grouped by status."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.table import Table
from rich.text import Text

from bearclaw.commands import _cli_error

app = typer.Typer()

_KANBAN_BIN = Path("kanban/kanban-md.exe")
_KANBAN_CONFIG = Path("kanban/config.yml")

_DURATION_RE = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>[smhd])$")


def _load_board_config() -> dict[str, Any]:
    """Return parsed board config or an empty mapping when unavailable/invalid."""
    try:
        raw_config = _KANBAN_CONFIG.read_text(encoding="utf-8")
    except OSError:
        return {}

    try:
        loaded = yaml.safe_load(raw_config)
    except yaml.YAMLError:
        return {}

    return loaded if isinstance(loaded, dict) else {}


def _read_status_order(config: dict[str, Any]) -> list[str]:
    """Return status names from config in configured order."""
    statuses = config.get("statuses")
    if not isinstance(statuses, list):
        return []

    ordered: list[str] = []
    for status in statuses:
        if isinstance(status, dict):
            name = status.get("name")
            if isinstance(name, str) and name:
                ordered.append(name)
    return ordered


def _parse_duration_seconds(value: object) -> float | None:
    """Parse compact durations such as ``0s``/``1h``/``24h`` into seconds."""
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None

    if not isinstance(value, str):
        return None

    match = _DURATION_RE.fullmatch(value.strip().lower())
    if match is None:
        return None

    duration_value = float(match.group("value"))
    multiplier = {
        "s": 1.0,
        "m": 60.0,
        "h": 3600.0,
        "d": 86400.0,
    }[match.group("unit")]
    return duration_value * multiplier


def _normalize_age_style(color: object) -> str | None:
    """Normalize configured threshold color values into a Rich-valid style string."""
    raw_color: str
    if isinstance(color, int):
        raw_color = str(color)
    elif isinstance(color, str):
        raw_color = color.strip()
    else:
        return None

    if not raw_color:
        return None

    style = f"color({raw_color})" if raw_color.isdigit() else raw_color
    try:
        Style.parse(style)
    except StyleSyntaxError:
        return None
    return style


def _read_age_thresholds(config: dict[str, Any]) -> list[tuple[float, str]]:
    """Return validated age thresholds or ``[]`` when config is absent/invalid."""
    tui = config.get("tui")
    raw_thresholds = tui.get("age_thresholds") if isinstance(tui, dict) else None
    if raw_thresholds is None:
        return []
    if not isinstance(raw_thresholds, list):
        return []

    parsed: list[tuple[float, str]] = []
    invalid_thresholds = False
    for threshold in raw_thresholds:
        if not isinstance(threshold, dict):
            invalid_thresholds = True
            break

        after_value = threshold.get("after")
        color_value = threshold.get("color")
        if after_value is None or color_value is None:
            invalid_thresholds = True
            break

        after_seconds = _parse_duration_seconds(after_value)
        style = _normalize_age_style(color_value)
        if after_seconds is None or style is None:
            invalid_thresholds = True
            break
        parsed.append((after_seconds, style))

    if invalid_thresholds:
        return []

    parsed.sort(key=lambda item: item[0])
    return parsed


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


def _age_reference_datetime(
    task: dict[str, Any],
    log_entries: list[dict[str, Any]],
) -> datetime:
    """Return the timestamp used as the start of the task's current status age."""
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
        return datetime.fromisoformat(str(latest["timestamp"]))

    return datetime.fromisoformat(str(task["created"]))


def _age_display_and_seconds(
    task: dict[str, Any],
    log_entries: list[dict[str, Any]],
) -> tuple[str, float]:
    """Return display label and raw age seconds for threshold evaluation."""
    reference = _age_reference_datetime(task, log_entries)
    now = datetime.now(tz=UTC)

    display = f"{(now.date() - reference.date()).days}d"
    age_seconds = max((now - reference.astimezone(UTC)).total_seconds(), 0.0)
    return display, age_seconds


def _age_style_for_seconds(
    age_seconds: float,
    thresholds: list[tuple[float, str]],
) -> str | None:
    """Return the style for the highest threshold crossed by ``age_seconds``."""
    matched_style: str | None = None
    for after_seconds, style in thresholds:
        if age_seconds >= after_seconds:
            matched_style = style
        else:
            break
    return matched_style


def _age_in_status(task: dict[str, Any], log_entries: list[dict[str, Any]]) -> str:
    """Return human-readable age: days since latest matching move or task creation."""
    display, _ = _age_display_and_seconds(task, log_entries)
    return display


@app.command()
def board() -> None:
    """Display the kanban board grouped by status."""
    tasks = _run_kanban("task-list", [str(_KANBAN_BIN), "list", "--json"])

    if not tasks:
        typer.echo("No tasks on the board.")
        return

    config = _load_board_config()
    status_order = _read_status_order(config)
    age_thresholds = _read_age_thresholds(config)
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
            age_display, age_seconds = _age_display_and_seconds(t, log_entries)
            age_style = _age_style_for_seconds(age_seconds, age_thresholds)
            age_cell: str | Text = age_display
            if age_style is not None:
                age_cell = Text(age_display, style=age_style)

            table.add_row(
                str(t.get("id", "")),
                t.get("title", ""),
                _assignee_display(t),
                age_cell,
                ", ".join(t.get("tags", [])),
            )

        Console(color_system="256").print(table)
