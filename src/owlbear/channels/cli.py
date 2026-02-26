"""CLI channel adapter — stdin/stdout I/O for interactive terminal use."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from io import TextIOBase


class CLIChannel:
    """Synchronous stdin/stdout channel for local CLI sessions.

    Accepts optional *input* / *output* streams for testing.  Defaults to
    ``sys.stdin`` / ``sys.stdout`` when not provided.
    """

    def __init__(
        self,
        input: TextIO | TextIOBase | None = None,  # noqa: A002
        output: TextIO | TextIOBase | None = None,
    ) -> None:
        self._input = input or sys.stdin
        self._output = output or sys.stdout

    @property
    def name(self) -> str:
        return "cli"

    async def send(self, message: str) -> None:
        """Write *message* to the output stream, followed by a newline."""
        self._output.write(message + "\n")
        self._output.flush()

    async def receive(self, *, prompt: str | None = None) -> str | None:
        """Read one line from the input stream.

        Returns ``None`` on EOF (empty string from ``readline``).
        """
        if prompt is not None:
            self._output.write(prompt)
            self._output.flush()
        line = self._input.readline()
        if not line:
            return None
        return line.rstrip("\n")
