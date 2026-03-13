"""ChannelPlugin — runtime-checkable protocol for I/O channel adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class ChannelPlugin(Protocol):
    """Minimal contract every channel adapter must satisfy.

    Channels abstract the user-facing I/O so the agent loop doesn't care
    whether input comes from a CLI, Teams webhook, or voice transcription.
    """

    @property
    def name(self) -> str:
        """Short identifier for the channel (e.g. ``"cli"``, ``"teams"``)."""
        ...

    async def send(self, message: str) -> None:
        """Push *message* to the user."""
        ...

    async def receive(self, *, prompt: str | None = None) -> str | None:
        """Wait for the next user input.

        Returns ``None`` on EOF / disconnect.  If *prompt* is given the
        channel should display it before waiting.
        """
        ...

    async def send_file(
        self,
        path: Path,
        *,
        caption: str | None = None,
    ) -> None:
        """Deliver a file reference to the user.

        Default implementation sends a text representation via :meth:`send`.
        """
        await self.send(f"[{caption}] {path}" if caption else str(path))

    async def send_blocks(
        self,
        blocks: list[dict],  # noqa: ARG002
        text_fallback: str,
    ) -> None:
        """Send structured blocks (e.g. Slack Block Kit) to the user.

        Default implementation sends *text_fallback* via :meth:`send`.
        """
        await self.send(text_fallback)

    async def send_image(
        self,
        file_or_bytes: Path | bytes,  # noqa: ARG002
        *,
        caption: str | None = None,
    ) -> None:
        """Deliver an image to the user.

        Default implementation sends *caption* (or ``'[image]'``) via
        :meth:`send`.
        """
        await self.send(caption or "[image]")
