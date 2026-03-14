"""BearClaw CLI — the command-line interface for OwlBear.

Entry point: ``bearclaw = bearclaw.cli:app`` (defined in pyproject.toml).
Run ``bearclaw --help`` to see available commands.
"""

from __future__ import annotations

from typing import Annotated

import click
import typer
from rich.traceback import install as install_rich_traceback
from typer.core import TyperGroup

import owlbear
from bearclaw.commands.auth import app as auth_app
from bearclaw.commands.browser import app as browser_app
from bearclaw.commands.chat import app as chat_app
from bearclaw.commands.daemon import app as daemon_app
from bearclaw.commands.decisions import app as decisions_app
from bearclaw.commands.knowledge_source import app as knowledge_source_app
from bearclaw.commands.project import app as project_app
from bearclaw.commands.slack import app as slack_app
from bearclaw.commands.usage import app as usage_app
from bearclaw.commands.voice import app as voice_app


class _RichGroup(TyperGroup):
    """Click Group that installs rich tracebacks before any argument processing."""

    def main(self, *args: object, **kwargs: object) -> object:  # type: ignore[override]
        install_rich_traceback(show_locals=False, suppress=[typer, click])
        return super().main(*args, **kwargs)


app = typer.Typer(
    name="bearclaw",
    cls=_RichGroup,
    help="BearClaw CLI — the command-line interface for OwlBear.",
    no_args_is_help=True,
)

# Sub-groups (named → nested commands)
app.add_typer(auth_app)
app.add_typer(browser_app)
app.add_typer(decisions_app)
app.add_typer(slack_app)
app.add_typer(project_app)
app.add_typer(usage_app)
app.add_typer(voice_app)
app.add_typer(knowledge_source_app)

# Top-level commands (unnamed → promoted to root)
app.add_typer(chat_app)
app.add_typer(daemon_app)


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
