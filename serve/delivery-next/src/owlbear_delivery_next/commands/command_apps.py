"""The command groups' shared parts (#679): argparse's usage line, its repeated options and its usage errors.

``project_commands`` and ``improvement_commands`` build their groups here. Loading it imports no OwlBear module, so
``owlbear --help`` and its completion stay fast (TD-263).
"""

import sys
from typing import TYPE_CHECKING, NoReturn

from cyclopts import App, Parameter
from cyclopts.help import DefaultFormatter

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions


class Usage(DefaultFormatter):
    """Cyclopts' help with argparse's lower-case ``usage:`` line."""

    def render_usage(self, console: Console, options: ConsoleOptions, usage: object) -> None:  # noqa: ARG002
        """Print ``usage: …``."""
        from rich.text import Text  # noqa: PLC0415 - only help prints it

        if usage:
            plain = usage.plain if isinstance(usage, Text) else str(usage)
            console.print(Text("usage: " + plain.removeprefix("Usage:").strip()))


LAST = Parameter(allow_repeating=True)  # a repeated option keeps its last value, as argparse did


def group(name: str | None = None, said: str | None = None) -> App:
    """A command group, or the top app, parsing as argparse did."""
    made = App(
        name=name,
        help=said,
        version_flags=[],
        result_action="return_value",
        help_formatter=Usage(),
        default_parameter=LAST,
    )
    made.default(_missing)
    return made


def _missing() -> NoReturn:
    """A group given no command: refused as argparse refused it."""
    refuse("a command is required")


def refuse(said: str) -> NoReturn:
    """A usage error: said on stderr, exit 2, before anything runs."""
    sys.stderr.write(f"owlbear-next: error: {said}\n")
    sys.exit(2)
