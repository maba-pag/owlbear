"""Board command — display the kanban board grouped by status."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.text import Text

from bearclaw.commands import _cli_error

app = typer.Typer()

_KANBAN_BIN = Path("kanban/kanban-md.exe")
_KANBAN_CONFIG = Path("kanban/config.yml")
_DURATION_UNITS: dict[str, float] = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0}


def _load_config() -> dict[str, Any] | None:
    """Load and parse kanban/config.yml. Returns None on any read or parse error."""
    try:
        raw = _KANBAN_CONFIG.read_text(encoding="utf-8")
        config = yaml.safe_load(raw)
        return config if isinstance(config, dict) else None
    except (OSError, yaml.YAMLError):
        return None


def _read_status_order(config: dict[str, Any] | None) -> list[str]:
    """Return status names from parsed config in configured order."""
    if not isinstance(config, dict):
        return []
    return [s["name"] for s in config.get("statuses", [])]


def _parse_duration_seconds(duration: str) -> float:
    """Parse a duration string like '0s', '1h', '24h', '1d' to seconds.

    Raises ValueError for unrecognised formats.
    """
    duration = duration.strip()
    if not duration:
        msg = "Empty duration string"
        raise ValueError(msg)
    unit = duration[-1].lower()
    if unit not in _DURATION_UNITS:
        msg = f"Unknown duration unit: {unit!r}"
        raise ValueError(msg)
    return float(duration[:-1]) * _DURATION_UNITS[unit]


def _validated_style(color: str) -> str | None:
    """Return 'color(N)' for a valid 256-color index (0-255), else None."""
    if not color.isdigit():
        return None
    n = int(color)
    if n > 255:  # noqa: PLR2004
        return None
    return f"color({n})"


def _parse_threshold_entry(entry: object) -> tuple[float, str]:
    """Parse one tui.age_thresholds entry dict. Raises ValueError/TypeError if invalid."""
    if not isinstance(entry, dict):
        msg = "threshold entry must be a dict"
        raise TypeError(msg)
    after = entry.get("after")
    color = entry.get("color")
    if after is None or color is None:
        msg = "threshold entry missing 'after' or 'color'"
        raise ValueError(msg)
    secs = _parse_duration_seconds(str(after))
    style_str = _validated_style(str(color))
    if style_str is None:
        msg = f"invalid threshold color: {color!r}"
        raise ValueError(msg)
    return secs, style_str


def _read_age_thresholds(
    config: dict[str, Any] | None,
) -> list[tuple[float, str]] | None:
    """Parse tui.age_thresholds -> sorted [(seconds, style_str), ...] or None on error.

    Returns None if the config is absent, the tui section is missing, the list
    is absent or not a list, or any single entry has an invalid duration or color.
    All-or-nothing: one invalid entry discards the whole threshold list.
    """
    if not isinstance(config, dict):
        return None
    tui = config.get("tui")
    if not isinstance(tui, dict):
        return None
    raw = tui.get("age_thresholds")
    if not isinstance(raw, list):
        return None
    try:
        result = [_parse_threshold_entry(e) for e in raw]
    except (ValueError, TypeError):
        return None
    result.sort(key=lambda x: x[0], reverse=True)
    return result or None


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


def _age_in_status(
    task: dict[str, Any], log_entries: list[dict[str, Any]]
) -> tuple[str, float]:
    """Return (display_age, raw_seconds) since the task entered its current status."""
    now = datetime.now(tz=UTC)
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
        ref_dt = datetime.fromisoformat(latest["timestamp"])
    else:
        ref_dt = datetime.fromisoformat(task["created"])

    ref_dt = ref_dt.replace(tzinfo=UTC) if ref_dt.tzinfo is None else ref_dt.astimezone(UTC)

    days = (now.date() - ref_dt.date()).days
    seconds = max(0.0, (now - ref_dt).total_seconds())
    return f"{days}d", seconds


def _apply_age_style(
    display: str,
    seconds: float,
    thresholds: list[tuple[float, str]] | None,
) -> Text | str:
    """Return a styled Rich Text for the age cell, or plain string if no thresholds apply."""
    if not thresholds:
        return display
    for threshold_secs, style_str in thresholds:
        if seconds >= threshold_secs:
            return Text(display, style=style_str)
    return display


@app.command()
def board() -> None:
    """Display the kanban board grouped by status."""
    tasks = _run_kanban("task-list", [str(_KANBAN_BIN), "list", "--json"])

    if not tasks:
        typer.echo("No tasks on the board.")
        return

    config = _load_config()
    status_order = _read_status_order(config)
    thresholds = _read_age_thresholds(config)
    log_entries = _run_kanban("move-log", [str(_KANBAN_BIN), "log", "--action", "move", "--json"])

    by_status: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        s = task.get("status", "unknown")
        by_status.setdefault(s, []).append(task)

    ordered = [s for s in status_order if s in by_status]
    remaining = [s for s in by_status if s not in status_order]

    _force_colors = bool(os.environ.get("FORCE_COLOR"))
    _console = Console(
        force_terminal=True if _force_colors else None,
        color_system="256" if _force_colors else None,
    )

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
            age_display, age_seconds = _age_in_status(t, log_entries)
            age_cell = _apply_age_style(age_display, age_seconds, thresholds)
            table.add_row(
                str(t.get("id", "")),
                t.get("title", ""),
                _assignee_display(t),
                age_cell,
                ", ".join(t.get("tags", [])),
            )

        _console.print(table)
