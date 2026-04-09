"""VoiceChannel — ChannelPlugin adapter backed by VoiceProcessManager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from owlbear.voice.process import VoiceProcessError, VoiceProcessManager
from owlbear.voice.protocol import SpeakMsg, TranscriptMsg

if TYPE_CHECKING:
    from pathlib import Path


class VoiceChannel:
    """ChannelPlugin adapter that routes I/O through the voice addon.

    The underlying VoiceProcessManager is entered lazily on the first
    call to ``receive()``.  Use as an async context manager to ensure
    clean shutdown.
    """

    def __init__(self, *, manager: VoiceProcessManager) -> None:
        self._manager = manager
        self._started = False

    @property
    def name(self) -> str:
        """Channel identifier."""
        return "voice"

    # ------------------------------------------------------------------
    # Core ChannelPlugin methods
    # ------------------------------------------------------------------

    async def send(self, message: str) -> None:
        """Speak *message* through the voice addon."""
        await self._manager.send(SpeakMsg(text=message, interrupt=False))

    async def receive(self, *, prompt: str | None = None) -> str | None:
        """Wait for a final voice transcript.

        If *prompt* is given, it is spoken before listening begins.
        Returns ``None`` on ``VoiceProcessError``.
        """
        await self._ensure_started()
        if prompt is not None:
            await self.send(prompt)
        while True:
            try:
                msg = await self._manager.receive()
            except VoiceProcessError:
                return None
            if isinstance(msg, TranscriptMsg) and msg.final:
                return msg.text

    # ------------------------------------------------------------------
    # Rich ChannelPlugin methods (delegate to send())
    # ------------------------------------------------------------------

    async def send_file(self, path: Path, *, caption: str | None = None) -> None:
        """Speak the file reference (path and/or caption)."""
        text = f"[{caption}] {path}" if caption else str(path)
        await self.send(text)

    async def send_blocks(self, blocks: list[dict], text_fallback: str) -> None:  # noqa: ARG002
        """Speak the text fallback for block content."""
        await self.send(text_fallback)

    async def send_image(self, file_or_bytes: Path | bytes, *, caption: str | None = None) -> None:  # noqa: ARG002
        """Speak the caption or a placeholder for image content."""
        await self.send(caption if caption is not None else "[image]")

    # ------------------------------------------------------------------
    # Async context manager lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._started:
            await self._manager.shutdown()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_started(self) -> None:
        """Enter the manager context on the first receive() call."""
        if not self._started:
            await self._manager.__aenter__()
            self._started = True
