"""ChannelPlugin — runtime-checkable protocol for I/O channel adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


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
