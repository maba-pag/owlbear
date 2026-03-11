"""Daemon commands — run / stop / status."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import os
from pathlib import Path
from typing import Annotated

import typer

from owlbear.config import OwlBearSettings

app = typer.Typer()


def _get_config_dir() -> Path:
    """Return the config_dir from settings."""
    from pathlib import Path as _Path  # noqa: PLC0415

    return _Path(OwlBearSettings().config_dir)


def _is_process_alive(pid: int) -> bool:
    """Check whether *pid* refers to a running process."""
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    else:
        return True


def _poll_pid_removal(pid_path: Path, *, timeout: float = 5.0) -> bool:
    """Poll for PID file removal, returning True if removed within timeout."""
    import time  # noqa: PLC0415

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not pid_path.exists():
            return True
        time.sleep(0.2)
    return False


@app.command(name="run")
def run_cmd(
    channel: Annotated[
        str,
        typer.Option("--channel", help="Channel to use: cli or slack."),
    ] = "cli",
    model: Annotated[
        str | None,
        typer.Option("--model", help="LLM model name."),
    ] = None,
) -> None:
    """Start the OwlBear daemon."""
    from pathlib import Path as _Path  # noqa: PLC0415

    from owlbear.bootstrap import bootstrap  # noqa: PLC0415
    from owlbear.daemon import PidFile, run_daemon, setup_logging  # noqa: PLC0415

    settings = OwlBearSettings()
    config_dir = _Path(settings.config_dir)

    # Set up logging
    setup_logging(config_dir / "owlbear.log")

    async def _run() -> None:
        result = await bootstrap(settings, channel_name=channel, workspace_root=_Path.cwd())
        if model:
            result.agent.update_model(model)
        try:
            if result.mcp_registry:
                await result.mcp_registry.__aenter__()
            await run_daemon(
                channel=result.channel,
                agent=result.agent,
                config_dir=config_dir,
                settings=settings,
                error_journal=result.error_journal,
            )
        finally:
            if result.mcp_registry:
                await result.mcp_registry.__aexit__(None, None, None)
            for cb in result.cleanup:
                with contextlib.suppress(Exception):
                    rv = cb()
                    if inspect.isawaitable(rv):
                        await rv

    pid_path = config_dir / "owlbear.pid"
    with PidFile(pid_path):
        asyncio.run(_run())


def _daemon_stop() -> None:
    """Stop the running OwlBear daemon."""
    config_dir = _get_config_dir()
    pid_path = config_dir / "owlbear.pid"

    if not pid_path.exists():
        typer.echo("Daemon is not running (no PID file found).")
        return

    pid = int(pid_path.read_text().strip())
    sentinel = config_dir / "owlbear.stop"

    # Create sentinel to request graceful shutdown
    sentinel.touch()
    typer.echo(f"Sent stop signal to daemon (PID {pid}).")

    # Poll for PID file removal (daemon removes it on exit)
    if _poll_pid_removal(pid_path):
        typer.echo("Daemon stopped gracefully.")
        sentinel.unlink(missing_ok=True)
        return

    # Fallback: force kill
    import contextlib  # noqa: PLC0415

    typer.echo("Daemon did not stop in time — force killing.")
    with contextlib.suppress(OSError):
        os.kill(pid, 9)  # SIGKILL / TerminateProcess

    pid_path.unlink(missing_ok=True)
    sentinel.unlink(missing_ok=True)


@app.command(name="stop")
def stop_cmd() -> None:
    """Stop the running OwlBear daemon."""
    _daemon_stop()


def _daemon_status(*, detail: bool = False) -> None:
    """Report daemon status using a rich Panel."""
    import time  # noqa: PLC0415

    from rich.console import Console  # noqa: PLC0415
    from rich.panel import Panel  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    settings = OwlBearSettings()
    config_dir = Path(str(settings.config_dir))
    pid_path = config_dir / "owlbear.pid"

    # Determine state
    pid: int | None = None
    if pid_path.exists():
        pid = int(pid_path.read_text().strip())
        alive = _is_process_alive(pid)
        state, border = ("Running", "green") if alive else ("Stale", "red")
    else:
        alive = False
        state, border = "Stopped", "red"

    # Build table (headerless key-value rows)
    table = Table(show_header=False, box=None)
    table.add_row("Status", state)
    table.add_row("PID", str(pid) if pid is not None else "\u2014")

    # Uptime (only when running)
    if alive:
        elapsed = int(time.time() - pid_path.stat().st_mtime)
        days, rem = divmod(elapsed, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        uptime = f"{days}d {hours}h" if days else f"{hours}h {minutes}m"
        table.add_row("Uptime", uptime)

    # Active project
    active_path = config_dir / "active_project"
    project_name = "None"
    if active_path.exists():
        text = active_path.read_text(encoding="utf-8").strip()
        if text:
            project_name = text
    table.add_row("Project", project_name)

    # Detail rows
    if detail:
        table.add_row("Model", settings.chat_model)
        table.add_row("Autonomous", "on" if settings.autonomous_mode else "off")
        if settings.heartbeat_enabled:
            table.add_row("Heartbeat", f"enabled ({settings.heartbeat_interval}s)")
        else:
            table.add_row("Heartbeat", "disabled")
        table.add_row(
            "Slack Channel",
            settings.slack_channel_id or "\u2014",
        )

    panel = Panel.fit(table, title="OwlBear Status", border_style=border)
    Console().print(panel)


@app.command(name="status")
def status_cmd(
    detail: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--detail", help="Show detailed configuration info."),
    ] = False,
) -> None:
    """Show OwlBear daemon status."""
    _daemon_status(detail=detail)
