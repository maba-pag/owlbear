"""Browser subcommands — CDP browser lifecycle management."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from owlbear.config import OwlBearSettings
from owlbear.tools.browser.launcher import (
    is_cdp_available,
    kill_edge,
    launch_edge_cdp,
)

app = typer.Typer(
    name="browser",
    help="Manage browser for CDP access.",
    no_args_is_help=True,
)


@app.command()
def start(
    port: Annotated[int, typer.Option(help="CDP debugging port.")] = 9222,
) -> None:
    """Launch Edge with Chrome DevTools Protocol enabled."""
    settings = OwlBearSettings()
    try:
        pid = launch_edge_cdp(port=port)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc

    pid_file = settings.config_dir / "browser.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))
    typer.echo(f"Edge started on port {port} (PID {pid})")


@app.command()
def stop() -> None:
    """Stop the Edge browser started by 'bearclaw browser start'."""
    settings = OwlBearSettings()
    pid_file = settings.config_dir / "browser.pid"

    if not pid_file.exists():
        typer.echo("Error: browser not running (no PID file)")
        raise typer.Exit(code=1)

    pid = int(pid_file.read_text().strip())
    kill_edge(pid)
    pid_file.unlink()
    typer.echo("Edge stopped")


@app.command("status")
def browser_status(
    port: Annotated[int, typer.Option(help="CDP debugging port.")] = 9222,
) -> None:
    """Check whether the CDP endpoint is responding."""
    connected = asyncio.run(is_cdp_available(port=port))
    if connected:
        typer.echo(f"CDP: Connected (port {port})")
    else:
        typer.echo(f"CDP: Not connected (port {port})")
