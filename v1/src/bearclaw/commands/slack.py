"""Slack subcommands — manage Slack integration."""

from __future__ import annotations

import os
import ssl
from typing import TYPE_CHECKING

import httpx
import truststore
import typer

from bearclaw.commands import _cli_error
from owlbear.config import get_settings
from owlbear.core.errors import error_to_user_message

if TYPE_CHECKING:
    from owlbear.config import OwlBearSettings

app = typer.Typer(
    name="slack",
    help="Manage Slack integration.",
    no_args_is_help=True,
)


def _slack_ssl_context() -> ssl.SSLContext:
    """Create an SSL context backed by the OS trust store."""
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _load_slack_settings() -> OwlBearSettings | None:
    """Load settings and return them if Slack is fully configured, else None."""
    settings = get_settings()
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
        _cli_error(
            "Slack tokens not configured. Set OWLBEAR_SLACK_APP_TOKEN, "
            "OWLBEAR_SLACK_BOT_TOKEN, OWLBEAR_SLACK_CHANNEL_ID."
        )
    return settings


@app.command("auth")
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
        _cli_error(f"Slack API request failed: {error_to_user_message(exc)}")

    if not data.get("ok"):
        _cli_error(f"auth.test failed — {data.get('error', 'unknown error')}")

    typer.echo(f"Authenticated as {data['user']} in workspace {data['team']}")


@app.command("test")
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
        _cli_error(f"Slack API request failed: {error_to_user_message(exc)}")

    if not data.get("ok"):
        _cli_error(f"chat.postMessage failed — {data.get('error', 'unknown error')}")

    typer.echo(f"Test message sent to channel {channel_id}")


@app.command("status")
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
