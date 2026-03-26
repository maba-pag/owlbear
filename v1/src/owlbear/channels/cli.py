"""CLI channel adapter — stdin/stdout I/O for interactive terminal use."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from owlbear.channels.base import ChannelPlugin

if TYPE_CHECKING:
    from io import TextIOBase


SAFE_EXTENSIONS = frozenset(
    {
        # Images
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".bmp",
        # Text
        ".txt",
        ".md",
        ".json",
        ".csv",
        ".log",
        ".xml",
        ".yaml",
        ".yml",
        ".toml",
        # Documents
        ".html",
        ".pdf",
    }
)

logger = logging.getLogger(__name__)


class CLIChannel(ChannelPlugin):
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
        On Windows, opens the file in the default viewer via
        ``os.startfile`` only when the extension is in
        :data:`SAFE_EXTENSIONS`; blocked extensions are logged as a
        warning.  On other platforms this is a no-op beyond the
        console output.
        """
        if caption:
            self._output.write(f"[{caption}] {path}\n")
        else:
            self._output.write(f"{path}\n")
        self._output.flush()

        if sys.platform == "win32" and hasattr(os, "startfile"):
            suffix = path.suffix.lower()
            if suffix in SAFE_EXTENSIONS:
                os.startfile(path)  # noqa: S606
            else:
                logger.warning(
                    "Blocked os.startfile for non-allowlisted extension: %s",
                    suffix or "<no-extension>",
                )

    async def send_image(
        self,
        file_or_bytes: Path | bytes,
        *,
        caption: str | None = None,
    ) -> None:
        """Deliver an image to the user.

        When *file_or_bytes* is a :class:`~pathlib.Path`, delegates to
        :meth:`send_file` so the CLI prints the path and opens it on Windows.
        For raw bytes, falls back to sending the caption text.
        """
        if isinstance(file_or_bytes, Path):
            await self.send_file(file_or_bytes, caption=caption)
        else:
            await self.send(caption or "[image]")
