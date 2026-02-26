"""BearClaw CLI — the command-line interface for OwlBear.

Entry point: ``bearclaw = bearclaw.cli:app`` (defined in pyproject.toml).
Run ``bearclaw --help`` to see available commands.
"""

from __future__ import annotations

import asyncio
import webbrowser
from typing import Annotated

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


@auth_app.command()
def login() -> None:
    """Start the Copilot OAuth device-flow login."""
    try:
        asyncio.run(_login_async())
    except Exception as exc:
        typer.echo(f"Login failed: {exc}")
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
