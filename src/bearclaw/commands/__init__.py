from __future__ import annotations

from typing import NoReturn

import typer


def _cli_error(msg: str) -> NoReturn:
    """Write ``Error: {msg}`` to stderr and exit with code 1."""
    typer.echo(f"Error: {msg}", err=True)
    raise typer.Exit(code=1)
