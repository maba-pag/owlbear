"""BearClaw CLI — the command-line interface for OwlBear.

Entry point: ``bearclaw = bearclaw.cli:app`` (defined in pyproject.toml).
Run ``bearclaw --help`` to see available commands.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import ssl
import subprocess
import webbrowser
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import httpx
import truststore
import typer

import owlbear
from owlbear.auth.copilot import (
    derive_base_url,
    exchange_for_copilot_token,
    load_token,
    poll_for_access_token,
    request_device_code,
    save_token,
)
from owlbear.config import OwlBearSettings
from owlbear.core.errors import error_to_user_message
from owlbear.memory.session import SessionStore
from owlbear.memory.usage import UsageRecord, UsageTracker
from owlbear.tools.browser.launcher import (
    is_cdp_available,
    kill_edge,
    launch_edge_cdp,
)
from owlbear.tools.github_api import parse_git_remote

if TYPE_CHECKING:
    from owlbear.channels.cli import CLIChannel
    from owlbear.core.agent import OwlBearAgent
    from owlbear.memory.knowledge.source_store import KnowledgeSourceStore
    from owlbear.projects.store import ProjectStore

app = typer.Typer(
    name="bearclaw",
    help="BearClaw CLI — the command-line interface for OwlBear.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Auth subcommand group
# ---------------------------------------------------------------------------

auth_app = typer.Typer(
    name="auth",
    help="Manage GitHub Copilot OAuth authentication.",
    no_args_is_help=True,
)
app.add_typer(auth_app)


# ---------------------------------------------------------------------------
# Browser subcommand group
# ---------------------------------------------------------------------------

browser_app = typer.Typer(
    name="browser",
    help="Manage browser for CDP access.",
    no_args_is_help=True,
)
app.add_typer(browser_app)


# ---------------------------------------------------------------------------
# Slack subcommand group
# ---------------------------------------------------------------------------

slack_app = typer.Typer(
    name="slack",
    help="Manage Slack integration.",
    no_args_is_help=True,
)
app.add_typer(slack_app)


# ---------------------------------------------------------------------------
# Project subcommand group
# ---------------------------------------------------------------------------

project_app = typer.Typer(
    name="project",
    help="Manage OwlBear projects.",
    no_args_is_help=True,
)
app.add_typer(project_app)


def _get_project_store() -> ProjectStore:
    """Return a ProjectStore rooted at ``config_dir/projects``."""
    from owlbear.projects.store import ProjectStore  # noqa: PLC0415

    settings = OwlBearSettings()
    return ProjectStore(Path(str(settings.config_dir)) / "projects")


@project_app.command("create")
def project_create(
    name: Annotated[str, typer.Option("--name", "-n", help="Project name.")],
    workspace: Annotated[
        str,
        typer.Option(
            "--workspace",
            "-w",
            help="Workspace directory path (default: current directory).",
        ),
    ] = "",
) -> None:
    """Create a new project."""
    ws = Path(workspace) if workspace else Path.cwd()
    store = _get_project_store()
    try:
        project = store.create(name, ws)
    except ValueError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from None
    typer.echo(f"Created project '{project.name}' (id: {project.id})")


@project_app.command("list")
def project_list(
    show_all: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--all", "-a", help="Include archived projects."),
    ] = False,
) -> None:
    """List projects in a table."""
    store = _get_project_store()
    projects = store.list_all() if show_all else store.list_active()
    if not projects:
        typer.echo("No projects found.")
        return

    from rich.console import Console  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    table = Table("Name", "Workspace", "Last Active", "Status")
    for p in projects:
        table.add_row(
            p.name,
            str(p.workspace_path),
            p.last_active.strftime("%Y-%m-%d %H:%M"),
            p.status,
        )
    Console().print(table)


@project_app.command("switch")
def project_switch(
    name: Annotated[str, typer.Argument(help="Name of the project to switch to.")],
) -> None:
    """Switch the active project."""
    store = _get_project_store()
    try:
        project = store.get_by_name(name)
    except KeyError:
        typer.echo(f"Error: No project named '{name}'")
        raise typer.Exit(code=1) from None

    settings = OwlBearSettings()
    active_path = Path(str(settings.config_dir)) / "active_project"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(project.id, encoding="utf-8")
    typer.echo(f"Switched to project '{project.name}'")


@project_app.command("archive")
def project_archive(
    name: Annotated[str, typer.Argument(help="Name of the project to archive.")],
) -> None:
    """Archive a project (set status to archived)."""
    store = _get_project_store()
    try:
        project = store.get_by_name(name)
    except KeyError:
        typer.echo(f"Error: No project named '{name}'")
        raise typer.Exit(code=1) from None

    store.archive(project.id)
    typer.echo(f"Archived project '{project.name}'")


@project_app.command("new")
def project_new(
    name: Annotated[str, typer.Argument(help="Name of the new project.")],
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="Project template: bare, python-uv, python-pip, node.",
        ),
    ] = "bare",
) -> None:
    """Scaffold a new project under project_root with a template."""
    from owlbear.projects.workspace import ProjectWorkspace  # noqa: PLC0415

    settings = OwlBearSettings()
    store = _get_project_store()
    ws = ProjectWorkspace(project_root=settings.project_root, store=store)
    try:
        path = ws.create_project(name, template)
    except (ValueError, FileExistsError) as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from None
    typer.echo(str(path))


# ---------------------------------------------------------------------------
# Usage subcommand group
# ---------------------------------------------------------------------------

usage_app = typer.Typer(
    name="usage",
    help="View token usage and cost statistics.",
    invoke_without_command=True,
)
app.add_typer(usage_app)


# ---------------------------------------------------------------------------
# Voice subcommand group
# ---------------------------------------------------------------------------

voice_app = typer.Typer(
    name="voice",
    help="Voice I/O commands (requires: uv sync --extra voice).",
    no_args_is_help=True,
)
app.add_typer(voice_app)


def _make_voice_channel(duration: float = 5.0) -> object:
    """Create a VoiceChannel with the given recording duration.

    Raises:
        ImportError: If the ``[voice]`` extras are not installed.
    """
    from owlbear.voice.channel import VoiceChannel  # noqa: PLC0415

    return VoiceChannel(record_duration=duration)


@voice_app.command("listen")
def voice_listen(
    duration: Annotated[
        float,
        typer.Option("--duration", "-d", help="Recording duration in seconds."),
    ] = 5.0,
) -> None:
    """Record audio and print transcription."""
    try:
        ch = _make_voice_channel(duration)
    except ImportError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from None

    text = asyncio.run(ch.receive())  # type: ignore[union-attr]

    if text is None:
        typer.echo("No speech detected.")
    else:
        typer.echo(text)


@voice_app.command("speak")
def voice_speak(
    text: Annotated[str, typer.Argument(help="Text to speak aloud.")],
) -> None:
    """Speak the given text via TTS."""
    try:
        ch = _make_voice_channel()
    except ImportError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from None

    asyncio.run(ch.send(text))  # type: ignore[union-attr]


@voice_app.command("brainstorm")
def voice_brainstorm(
    duration: Annotated[
        float,
        typer.Option("--duration", "-d", help="Max session duration in seconds."),
    ] = 120.0,
    idle_timeout: Annotated[
        float,
        typer.Option(
            "--idle-timeout",
            "-i",
            help="End session after this many seconds of silence.",
        ),
    ] = 10.0,
) -> None:
    """Open-ended brainstorm session with live transcription."""
    try:
        ch = _make_voice_channel()
    except ImportError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from None

    def _on_update(text: str) -> None:
        typer.echo(f"\r{text}", nl=False)

    transcript = asyncio.run(
        ch.brainstorm(  # type: ignore[union-attr]
            duration=duration,
            idle_timeout=idle_timeout,
            on_update=_on_update,
        ),
    )
    typer.echo()  # newline after live updates
    typer.echo(transcript)


# ---------------------------------------------------------------------------
# Knowledge-source subcommand group
# ---------------------------------------------------------------------------

knowledge_source_app = typer.Typer(
    name="knowledge-source",
    help="Manage knowledge sources.",
    no_args_is_help=True,
)
app.add_typer(knowledge_source_app)


def _get_source_store() -> KnowledgeSourceStore:
    """Return a :class:`KnowledgeSourceStore` backed by the knowledge DB."""
    import sqlite3  # noqa: PLC0415

    from owlbear.memory.knowledge.schema import init_db  # noqa: PLC0415
    from owlbear.memory.knowledge.source_store import (  # noqa: PLC0415
        KnowledgeSourceStore,
    )

    settings = OwlBearSettings()
    settings.knowledge_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.knowledge_db_path))
    init_db(conn)
    return KnowledgeSourceStore(conn)


_VALID_SOURCE_TYPES = ("url_list", "crawl", "file_glob")


@knowledge_source_app.command("add")
def ks_add(  # noqa: PLR0913
    name: Annotated[str, typer.Option("--name", "-n", help="Source name.")],
    source_type: Annotated[
        str, typer.Option("--type", "-t", help="Source type: url_list, crawl, or file_glob.")
    ],
    urls: Annotated[str, typer.Option("--urls", help="Comma-separated URLs (for url_list).")] = "",
    seeds: Annotated[
        str, typer.Option("--seeds", help="Comma-separated seed URLs (for crawl).")
    ] = "",
    pattern: Annotated[str, typer.Option("--pattern", help="Glob pattern (for file_glob).")] = "",
    scope: Annotated[
        str, typer.Option("--scope", "-s", help="Scope (default: global).")
    ] = "global",
    max_depth: Annotated[int, typer.Option("--max-depth", help="Max crawl depth (for crawl).")] = 1,
    max_pages: Annotated[
        int, typer.Option("--max-pages", help="Max pages to crawl (for crawl).")
    ] = 50,
) -> None:
    """Add a new knowledge source."""
    from datetime import UTC, datetime  # noqa: PLC0415

    from owlbear.memory.knowledge.models import (  # noqa: PLC0415
        KnowledgeSource,
        SourceType,
    )

    if source_type not in _VALID_SOURCE_TYPES:
        valid = ", ".join(_VALID_SOURCE_TYPES)
        typer.echo(f"Error: Invalid type '{source_type}'. Must be one of: {valid}")
        raise typer.Exit(code=1)

    # Build config dict based on type
    config: dict[str, object] = {}
    if source_type == "url_list":
        if not urls:
            typer.echo("Error: --urls is required for type 'url_list'.")
            raise typer.Exit(code=1)
        config["urls"] = [u.strip() for u in urls.split(",")]
    elif source_type == "crawl":
        if not seeds:
            typer.echo("Error: --seeds is required for type 'crawl'.")
            raise typer.Exit(code=1)
        config["seeds"] = [s.strip() for s in seeds.split(",")]
        config["max_depth"] = max_depth
        config["max_pages"] = max_pages
    elif source_type == "file_glob":
        if not pattern:
            typer.echo("Error: --pattern is required for type 'file_glob'.")
            raise typer.Exit(code=1)
        config["pattern"] = pattern

    now = datetime.now(tz=UTC).isoformat()
    source = KnowledgeSource(
        name=name,
        source_type=SourceType(source_type),
        config=config,
        scope=scope,
        created_at=now,
        updated_at=now,
    )

    store = _get_source_store()
    store.create(source)
    typer.echo(f"Added knowledge source '{name}' (type: {source_type}, scope: {scope})")


@knowledge_source_app.command("list")
def ks_list(
    scope: Annotated[str, typer.Option("--scope", "-s", help="Filter by scope.")] = "",
) -> None:
    """List knowledge sources."""
    store = _get_source_store()
    scope_filter = scope or None
    sources = store.list_all(scope=scope_filter)

    if not sources:
        typer.echo("No knowledge sources found.")
        return

    from rich.console import Console  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    table = Table("Name", "Type", "Scope", "Enabled", "Last Refreshed")
    for s in sources:
        table.add_row(
            s.name,
            str(s.source_type),
            s.scope,
            "yes" if s.enabled else "no",
            s.last_refreshed_at or "never",
        )
    Console().print(table)


@knowledge_source_app.command("show")
def ks_show(
    name: Annotated[str, typer.Argument(help="Name of the source to show.")],
    scope: Annotated[str, typer.Option("--scope", "-s", help="Source scope.")] = "global",
) -> None:
    """Show details of a knowledge source."""
    import json  # noqa: PLC0415

    store = _get_source_store()
    source = store.get_by_name(name, scope=scope)
    if source is None:
        typer.echo(f"Error: No knowledge source named '{name}' (scope: {scope})")
        raise typer.Exit(code=1)

    typer.echo(f"Name:           {source.name}")
    typer.echo(f"Type:           {source.source_type}")
    typer.echo(f"Scope:          {source.scope}")
    typer.echo(f"Enabled:        {source.enabled}")
    typer.echo(f"Priority:       {source.priority}")
    typer.echo(f"Config:         {json.dumps(source.config, indent=2)}")
    typer.echo(f"Last Refreshed: {source.last_refreshed_at or 'never'}")
    typer.echo(f"Last Error:     {source.last_error or 'none'}")
    typer.echo(f"Created:        {source.created_at}")


@knowledge_source_app.command("remove")
def ks_remove(
    name: Annotated[str, typer.Argument(help="Name of the source to remove.")],
    scope: Annotated[str, typer.Option("--scope", "-s", help="Source scope.")] = "global",
) -> None:
    """Remove a knowledge source."""
    store = _get_source_store()
    source = store.get_by_name(name, scope=scope)
    if source is None:
        typer.echo(f"Error: No knowledge source named '{name}'")
        raise typer.Exit(code=1)

    store.delete(source.id)
    typer.echo(f"Removed knowledge source '{name}'")


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


@usage_app.callback(invoke_without_command=True)
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


def _slack_ssl_context() -> ssl.SSLContext:
    """Create an SSL context backed by the OS trust store."""
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _load_slack_settings() -> OwlBearSettings | None:
    """Load settings and return them if Slack is fully configured, else None."""
    settings = OwlBearSettings()
    if (
        settings.slack_app_token is None
        or settings.slack_bot_token is None
        or settings.slack_channel_id is None
    ):
        return None
    return settings


def _require_slack_settings() -> OwlBearSettings:
    """Load settings or exit with an error if Slack tokens are missing."""
    settings = _load_slack_settings()
    if settings is None:
        typer.echo(
            "Error: Slack tokens not configured. Set OWLBEAR_SLACK_APP_TOKEN, "
            "OWLBEAR_SLACK_BOT_TOKEN, OWLBEAR_SLACK_CHANNEL_ID."
        )
        raise typer.Exit(code=1)
    return settings


@slack_app.command("auth")
def slack_auth() -> None:
    """Validate Slack tokens by calling auth.test API."""
    settings = _require_slack_settings()
    bot_token = settings.slack_bot_token.get_secret_value()  # type: ignore[union-attr]
    ctx = _slack_ssl_context()
    try:
        resp = httpx.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {bot_token}"},
            verify=ctx,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        typer.echo(f"Error: Slack API request failed: {error_to_user_message(exc)}")
        raise typer.Exit(code=1) from exc

    if not data.get("ok"):
        typer.echo(f"Error: auth.test failed — {data.get('error', 'unknown error')}")
        raise typer.Exit(code=1)

    typer.echo(f"Authenticated as {data['user']} in workspace {data['team']}")


@slack_app.command("test")
def slack_test() -> None:
    """Send a test message to the configured Slack channel."""
    settings = _require_slack_settings()
    bot_token = settings.slack_bot_token.get_secret_value()  # type: ignore[union-attr]
    channel_id = settings.slack_channel_id
    ctx = _slack_ssl_context()
    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {bot_token}"},
            json={
                "channel": channel_id,
                "text": "\U0001f43b OwlBear test message — Slack integration OK",
            },
            verify=ctx,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        typer.echo(f"Error: Slack API request failed: {error_to_user_message(exc)}")
        raise typer.Exit(code=1) from exc

    if not data.get("ok"):
        typer.echo(f"Error: chat.postMessage failed — {data.get('error', 'unknown error')}")
        raise typer.Exit(code=1)

    typer.echo(f"Test message sent to channel {channel_id}")


@slack_app.command("status")
def slack_status() -> None:
    """Show Slack connection state and token configuration."""
    # Read env vars directly to report partial state without validation errors.
    app_token = os.environ.get("OWLBEAR_SLACK_APP_TOKEN")
    bot_token = os.environ.get("OWLBEAR_SLACK_BOT_TOKEN")
    channel_id = os.environ.get("OWLBEAR_SLACK_CHANNEL_ID")

    typer.echo(f"App token:  {'configured' if app_token else 'not configured'}")
    typer.echo(f"Bot token:  {'configured' if bot_token else 'not configured'}")
    typer.echo(f"Channel ID: {channel_id or 'not configured'}")

    if not (app_token and bot_token and channel_id):
        typer.echo("\nSlack is not configured.")
        return

    # All tokens present — test the connection.
    ctx = _slack_ssl_context()
    try:
        resp = httpx.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {bot_token}"},
            verify=ctx,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError:
        typer.echo("Connection: Failed (request error)")
        return

    if data.get("ok"):
        typer.echo("Connection: OK")
    else:
        typer.echo(f"Connection: Failed ({data.get('error', 'unknown error')})")


@browser_app.command()
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


@browser_app.command()
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


@browser_app.command("status")
def browser_status(
    port: Annotated[int, typer.Option(help="CDP debugging port.")] = 9222,
) -> None:
    """Check whether the CDP endpoint is responding."""
    connected = asyncio.run(is_cdp_available(port=port))
    if connected:
        typer.echo(f"CDP: Connected (port {port})")
    else:
        typer.echo(f"CDP: Not connected (port {port})")


@auth_app.command()
def login() -> None:
    """Start the Copilot OAuth device-flow login."""
    try:
        asyncio.run(_login_async())
    except Exception as exc:
        typer.echo(f"Login failed: {error_to_user_message(exc)}")
        raise typer.Exit(code=1) from exc


async def _login_async() -> None:
    """Run the full device-flow OAuth sequence."""
    device = await request_device_code()

    typer.echo(f"\nOpen {device['verification_uri']} and enter code: {device['user_code']}\n")
    webbrowser.open(device["verification_uri"])

    typer.echo("Waiting for authorization...")
    access_token = await poll_for_access_token(
        device["device_code"],
        interval=device["interval"],
        expires_in=device["expires_in"],
    )

    copilot_data = await exchange_for_copilot_token(access_token)
    save_token(copilot_data)
    typer.echo("Successfully authenticated with GitHub Copilot!")


@auth_app.command()
def status() -> None:
    """Show current authentication token status."""
    settings = OwlBearSettings()
    token_data = load_token(settings.copilot_token_path)

    if token_data is None:
        typer.echo("Status: Not authenticated (no valid token found)")
        return

    token = token_data["token"]
    base_url = derive_base_url(token)
    typer.echo("Status: Authenticated")
    typer.echo(f"Model:  {settings.chat_model}")
    typer.echo(f"API:    {base_url}")


# ---------------------------------------------------------------------------
# Chat command
# ---------------------------------------------------------------------------

_EXIT_KEYWORDS = frozenset({"exit", "quit"})


@app.command()
def chat(
    model: Annotated[str | None, typer.Option("--model", help="LLM model name.")] = None,
    session: Annotated[
        str | None,
        typer.Option("--session", help="Session name (default: auto-generated)."),
    ] = None,
    workspace: Annotated[
        str,
        typer.Option("--workspace", help="Workspace root directory."),
    ] = ".",
    project: Annotated[
        str | None,
        typer.Option("--project", help="Project name for scoped sessions."),
    ] = None,
) -> None:
    """Start an interactive chat REPL with OwlBear."""
    from pathlib import Path as _Path  # noqa: PLC0415

    ws = _Path(workspace).resolve()
    asyncio.run(
        _chat_async(model=model, session=session, workspace_root=ws, project=project),
    )


async def _read_multiline(channel: CLIChannel) -> str | None:
    """Accumulate lines until ``!end`` or EOF, return joined text."""
    lines: list[str] = []
    await channel.send("(multi-line mode — type !end to submit)")
    while True:
        ml = await channel.receive(prompt="... ")
        if ml is None or ml.strip() == "!end":
            break
        lines.append(ml)
    return "\n".join(lines) if lines else None


def _detect_github_remote(workspace_root: Path) -> tuple[str, str] | None:
    """Auto-detect GitHub owner/repo from ``git remote get-url origin``.

    Returns:
        Tuple of ``(owner, repo)`` on success, or ``None`` if detection fails.
    """
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=workspace_root,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return parse_git_remote(result.stdout.strip())
    except ValueError:
        return None


def _build_chat_session(
    settings: OwlBearSettings,
    session: str | None,
    *,
    project_id: str | None = None,
) -> tuple[str, SessionStore]:
    """Resolve session name and create a :class:`SessionStore`.

    When *project_id* is provided the session file is placed under
    ``config_dir/projects/{project_id}/sessions/``.  Otherwise the
    legacy ``config_dir/sessions/`` directory is used (backward compat).
    """
    from datetime import UTC, datetime  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    name = session or f"chat-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    base = Path(settings.config_dir)
    if project_id:
        base = base / "projects" / project_id
    path = base / "sessions" / f"{name}.jsonl"
    return name, SessionStore(path)


async def _chat_async(
    *,
    model: str | None,
    session: str | None,
    workspace_root: Path,
    project: str | None = None,
) -> None:
    """Run the interactive chat REPL loop."""
    from owlbear.bootstrap import bootstrap  # noqa: PLC0415

    settings = OwlBearSettings()
    model_name = model or settings.chat_model

    # Resolve project name → id for session scoping.
    project_id: str | None = None
    if project:
        from owlbear.projects.store import ProjectStore  # noqa: PLC0415

        store_dir = Path(settings.config_dir) / "projects"
        proj = ProjectStore(store_dir).get_by_name(project)
        project_id = proj.id

    session_name, store = _build_chat_session(settings, session, project_id=project_id)

    # Load existing history (resume previous session).
    store.load()

    # Delegate all hook/toolset/channel assembly to bootstrap().
    result = await bootstrap(settings, channel_name="cli", workspace_root=workspace_root)

    # Override session with user-specified store (chat-specific naming).
    result.agent.session = store

    # Override model if --model provided.
    if model:
        result.agent.update_model(model)

    # Banner.
    await result.channel.send(
        f"OwlBear Chat — model: {model_name}, session: {session_name}",
    )
    await result.channel.send(
        "Type !multi for multi-line input (!end to submit). Type exit or quit to leave.",
    )

    await _chat_loop(result.agent, result.channel)


async def _chat_loop(agent: OwlBearAgent, channel: CLIChannel) -> None:
    """Core receive → turn → send loop."""
    try:
        while True:
            line = await channel.receive(prompt="> ")
            if line is None:
                break

            text = line.strip()
            if text.lower() in _EXIT_KEYWORDS:
                break
            if not text:
                continue

            if text == "!multi":
                text = await _read_multiline(channel)  # type: ignore[assignment]
                if text is None:
                    continue

            try:
                response = await agent.turn(text)
                await channel.send(response)
            except Exception as exc:  # noqa: BLE001
                await channel.send(f"Error: {error_to_user_message(exc)}")
    except KeyboardInterrupt:
        pass

    await channel.send("Goodbye!")


# ---------------------------------------------------------------------------
# Daemon commands — run / stop / status
# ---------------------------------------------------------------------------


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
                    cb()

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


# ---------------------------------------------------------------------------
# Global options
# ---------------------------------------------------------------------------


def _version_callback(value: bool) -> None:  # noqa: FBT001
    """Print version and exit."""
    if value:
        typer.echo(f"owlbear {owlbear.__version__}")
        raise typer.Exit


@app.callback()
def main(
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """BearClaw — command-line interface for the OwlBear AI system."""
