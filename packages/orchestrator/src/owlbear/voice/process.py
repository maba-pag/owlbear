"""VoiceProcessManager — manages the voice addon subprocess lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from owlbear.voice.protocol import VoiceOutMessage


class VoiceProcessError(Exception):
    """Raised when the voice addon process encounters a fatal error."""


class VoiceProcessManager:
    """Manages the voice addon subprocess and NDJSON message exchange.

    Used as an async context manager; the subprocess is launched on entry
    and terminated on exit.
    """

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.shutdown()

    async def send(self, msg: object) -> None:
        """Send a message to the voice addon."""
        raise NotImplementedError

    async def receive(self) -> VoiceOutMessage:
        """Receive the next message from the voice addon.

        Raises:
            VoiceProcessError: if the process dies or produces an unrecoverable error.
        """
        raise NotImplementedError

    async def shutdown(self) -> None:
        """Gracefully shut down the voice addon process."""
        raise NotImplementedError
