"""Session-memory persistence hook.

Provides :class:`SessionMemoryHook` — a ``SESSION_END`` hook that calls an
LLM summarizer to produce a compact summary of the conversation and writes
it to ``{workspace}/.owlbear/session-memory.md``.  On the next startup,
:class:`~owlbear.memory.context.ContextManager` reads the file and injects
it into the agent's system prompt.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

_SESSION_MEMORY_FILENAME = "session-memory.md"


class SessionMemoryHook:
    """``SESSION_END`` hook that persists a conversation summary.

    Args:
        workspace_root: Workspace directory (parent of ``.owlbear/``).
        summarizer: Async callable that accepts serialised message text
            and returns a structured markdown summary.
    """

    def __init__(
        self,
        workspace_root: Path,
        summarizer: Callable[[str], Awaitable[str]],
    ) -> None:
        self._workspace_root = workspace_root
        self._summarizer = summarizer

    # -- hook callback -------------------------------------------------------

    async def __call__(self, data: dict[str, Any]) -> None:
        """Extract messages, summarise, and write to disk.

        Silently returns when messages are empty or missing.  Logs a
        warning and returns on summarizer failure — never raises.
        """
        messages: list[dict[str, Any]] | None = data.get("messages")
        if not messages:
            return

        text = self._serialise_messages(messages)

        try:
            summary = await self._summarizer(text)
        except Exception:  # noqa: BLE001
            logger.warning("Session memory summarizer failed", exc_info=True)
            return

        output_dir = self._workspace_root / ".owlbear"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / _SESSION_MEMORY_FILENAME
        output_path.write_text(summary, encoding="utf-8")

    # -- registration --------------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on :pyattr:`HookEvent.SESSION_END`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.SESSION_END, self)

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _serialise_messages(messages: list[dict[str, Any]]) -> str:
        """Convert a list of message dicts to a plain-text transcript."""
        lines: list[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
