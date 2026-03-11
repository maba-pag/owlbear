"""Usage subcommands — view token usage and cost statistics."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from pathlib import Path

import typer

from owlbear.config import OwlBearSettings
from owlbear.memory.usage import UsageRecord, UsageTracker

app = typer.Typer(
    name="usage",
    help="View token usage and cost statistics.",
    invoke_without_command=True,
)


def _get_usage_path() -> Path:
    """Return the usage JSONL path from settings."""
    return OwlBearSettings().usage_path


def _resolve_usage_window(
    *,
    last_hour: bool,
    last_7d: bool,
    show_all: bool,
) -> timedelta | None:
    """Map CLI flags to a time-window ``timedelta`` (``None`` = all)."""
    if last_hour:
        return timedelta(hours=1)
    if last_7d:
        return timedelta(days=7)
    if show_all:
        return None
    # Default: last 24 hours (covers --last-24h and no-flag case)
    return timedelta(hours=24)


def _aggregate_by_model(
    records: list[UsageRecord],
) -> tuple[dict[str, dict[str, float]], bool]:
    """Group *records* by model, returning ``(model_data, has_premium)``."""
    model_data: dict[str, dict[str, float]] = {}
    has_premium = False
    for r in records:
        if r.model not in model_data:
            model_data[r.model] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "premium": 0.0,
            }
        m = model_data[r.model]
        m["requests"] += r.requests
        m["input_tokens"] += r.input_tokens
        m["output_tokens"] += r.output_tokens
        m["total_tokens"] += r.total_tokens
        if r.estimated_cost_usd is not None:
            m["cost"] += r.estimated_cost_usd
        if r.provider == "copilot" and r.premium_requests is not None:
            m["premium"] += r.premium_requests
            has_premium = True
    return model_data, has_premium


def _print_usage_table(
    model_data: dict[str, dict[str, float]],
    *,
    has_premium: bool,
) -> None:
    """Format *model_data* as a table and print with a totals row."""
    from rich.console import Console  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    table = Table()
    table.add_column("Model")
    table.add_column("Requests")
    table.add_column("Input Tokens")
    table.add_column("Output Tokens")
    table.add_column("Total Tokens")
    table.add_column("Est. Cost (USD)")
    if has_premium:
        table.add_column("Premium Requests")

    def _cells(label: str, s: dict[str, float]) -> list[str]:
        cells = [
            label,
            str(int(s["requests"])),
            str(int(s["input_tokens"])),
            str(int(s["output_tokens"])),
            str(int(s["total_tokens"])),
            f"${s['cost']:.4f}",
        ]
        if has_premium:
            cells.append(str(int(s["premium"])))
        return cells

    for model in sorted(model_data):
        table.add_row(*_cells(model, model_data[model]))

    # Summary totals with section separator
    keys = next(iter(model_data.values()))
    agg: dict[str, float] = {k: sum(s[k] for s in model_data.values()) for k in keys}
    table.add_section()
    table.add_row(*_cells("TOTAL", agg))

    Console().print(table)


@app.callback(invoke_without_command=True)
def usage_show(
    last_hour: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--last-hour", help="Filter to last 1 hour."),
    ] = False,
    last_24h: Annotated[  # noqa: ARG001, FBT002
        bool,
        typer.Option("--last-24h", help="Filter to last 24 hours."),
    ] = False,
    last_7d: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--last-7d", help="Filter to last 7 days."),
    ] = False,
    show_all: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--all", help="Show all records."),
    ] = False,
) -> None:
    """Show token usage and cost statistics."""
    path = _get_usage_path()
    tracker = UsageTracker(path)
    window = _resolve_usage_window(last_hour=last_hour, last_7d=last_7d, show_all=show_all)
    records = tracker.load() if window is None else tracker.query(window)

    if not records:
        typer.echo("No usage data found for the selected time window.")
        return

    model_data, has_premium = _aggregate_by_model(records)
    _print_usage_table(model_data, has_premium=has_premium)
