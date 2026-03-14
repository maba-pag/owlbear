"""Board context provider for injecting kanban state into agent turns."""

from __future__ import annotations


class BoardContextProvider:
    """Provides board state context for agent turn instructions.

    Subclass and override :meth:`get_context` to supply live board summaries.
    """

    async def get_context(self) -> str:
        """Return a short board-state summary for the current turn."""
        return ""
