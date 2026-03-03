"""CLI channel adapter — stdin/stdout I/O for interactive terminal use."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from io import TextIOBase
    from pathlib import Path


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

    async def send_file(self, path: Path, *, caption: str | None = None) -> None:
        """Deliver a file path to the user.

        Prints *path* (and optional *caption*) to the output stream.
        On Windows, also opens the file in the default viewer via
        ``os.startfile``.  On other platforms this is a no-op beyond
        the console output.
        """
        if caption:
            self._output.write(f"[{caption}] {path}\n")
        else:
            self._output.write(f"{path}\n")
        self._output.flush()

        if sys.platform == "win32" and hasattr(os, "startfile"):
            os.startfile(path)  # noqa: S606
