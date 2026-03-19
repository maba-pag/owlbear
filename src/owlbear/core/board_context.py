"""Board context provider for injecting kanban state into agent turns."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_DEFAULT_CMD: list[str] = [
    "kanban/kanban-md.exe",
    "list",
    "--compact",
    "--status",
    "in-progress",
    "--status",
    "review",
    "--status",
    "todo",
    "--no-color",
    "--dir",
    "kanban",
]


class BoardContextProvider:
    """Provides live kanban board context for agent turn instructions.

    Runs ``kanban-md list`` via :func:`asyncio.create_subprocess_exec` and
    caches the result for *ttl_seconds*.  Call :meth:`invalidate` to force a
    refresh before the TTL expires.

    Args:
        kanban_cmd: Command list to execute.  Defaults to the standard
            ``kanban-md list --compact --status ...`` invocation.
        ttl_seconds: Cache lifetime in seconds.  Defaults to 60.
        timer: Callable returning a monotonic float used for TTL bookkeeping.
            Defaults to :func:`time.monotonic`.
    """

    def __init__(
        self,
        kanban_cmd: list[str] | None = None,
        ttl_seconds: float = 60,
        timer: Callable[[], float] | None = None,
    ) -> None:
        self.kanban_cmd: list[str] = kanban_cmd if kanban_cmd is not None else list(_DEFAULT_CMD)
        self.ttl_seconds: float = ttl_seconds
        self.timer: Callable[[], float] = timer if timer is not None else time.monotonic

        self._cached: str | None = None
        self._cached_at: float | None = None

    async def get_context(self) -> str:
        """Return a short board-state summary for the current turn.

        Uses a TTL cache to avoid spawning a subprocess on every call.
        Returns an empty string when the subprocess fails.
        """
        now = self.timer()
        if (
            self._cached is not None
            and self._cached_at is not None
            and (now - self._cached_at) < self.ttl_seconds
        ):
            return self._cached

        result = await self._run()
        self._cached = result
        self._cached_at = self.timer()
        return result

    def invalidate(self) -> None:
        """Clear the cached board context, forcing a refresh on next call."""
        self._cached = None
        self._cached_at = None

    async def _run(self) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.kanban_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except OSError as exc:
            logger.warning("BoardContextProvider: subprocess error: %s", exc)
            return ""

        if proc.returncode != 0:
            logger.warning(
                "BoardContextProvider: command failed (rc=%d): %s",
                proc.returncode,
                stderr_bytes.decode("utf-8", errors="replace"),
            )
            return ""

        return stdout_bytes.decode("utf-8", errors="replace")
