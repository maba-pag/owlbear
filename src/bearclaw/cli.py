"""BearClaw CLI — the command-line interface for OwlBear.

Entry point: ``bearclaw = bearclaw.cli:app`` (defined in pyproject.toml).
Run ``bearclaw --help`` to see available commands.
"""

from __future__ import annotations

from typing import Annotated

import typer

import owlbear

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
    typer.echo("Not yet implemented — will start Copilot OAuth device flow")


@auth_app.command()
def status() -> None:
    """Show current authentication token status."""
    typer.echo("Not yet implemented — will show token status")


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
