"""ProgressReporter — periodic progress updates via a ChannelPlugin.

Sends heartbeat messages to a channel at a configurable interval so the
user knows the agent is still working.  An *activity gate* prevents
redundant messages when no tools have been invoked since the last update.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import TYPE_CHECKING, Literal

from owlbear.core.hooks import PostToolUseData  # noqa: TC001

if TYPE_CHECKING:
    from owlbear.channels.base import ChannelPlugin
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)


class ProgressReporter:
    """Periodically report agent progress to a channel.

    Args:
        channel (ChannelPlugin): Any object satisfying
            :class:`~owlbear.channels.base.ChannelPlugin`.
        interval (float): Seconds between heartbeat ticks.
        detail (Literal['brief', 'detailed']): ``"brief"`` for a short status
            line, ``"detailed"`` for full
            tool-arg / session info.
        agent_name (str | None): Optional agent identifier included in detailed messages.
        session_id (str | None): Optional session identifier included in detailed messages.
    """

    def __init__(
        self,
        *,
        channel: ChannelPlugin,
        interval: float,
        detail: Literal["brief", "detailed"] = "brief",
        agent_name: str | None = None,
        session_id: str | None = None,
    ) -> None:
        self._channel = channel
        self._interval = interval
        self._detail = detail
        self._agent_name = agent_name
        self._session_id = session_id

        # Mutable state — reset on each start()
        self._tool_count: int = 0
        self._last_tool: str | None = None
        self._last_tool_args: dict[str, object] = {}
        self._last_reported_count: int = 0
        self._start_time: float = time.monotonic()
        self._timer_task: asyncio.Task[None] | None = None

    # -- public properties ---------------------------------------------------

    @property
    def tool_count(self) -> int:
        """Total number of tool completions recorded."""
        return self._tool_count

    @property
    def last_tool(self) -> str | None:
        """Name of the most recently completed tool."""
        return self._last_tool

    @property
    def last_tool_args(self) -> dict[str, object]:
        """Arguments of the most recently completed tool."""
        return self._last_tool_args

    # -- hook callback -------------------------------------------------------

    def on_tool_complete(self, data: PostToolUseData) -> None:
        """Record a tool completion event.

        Expected *data* shape: ``{"tool_name": str, "args": dict}``.
        """
        self._tool_count += 1
        self._last_tool = data.get("tool_name")
        self._last_tool_args = data.get("args", {})

    # -- message formatting --------------------------------------------------

    def format_message(self) -> str:
        """Build a progress string based on the current detail level."""
        elapsed = int(time.monotonic() - self._start_time)
        tool = self._last_tool or "none"

        if self._detail == "detailed":
            return self._format_detailed(tool, elapsed)
        return self._format_brief(tool, elapsed)

    def _format_brief(self, tool: str, elapsed: int) -> str:
        return (
            f"Working on task... ({self._tool_count} tools called, "
            f"last: {tool}, {elapsed}s elapsed)"
        )

    def _format_detailed(self, tool: str, elapsed: int) -> str:
        parts = [
            f"Progress: {self._tool_count} tools in {elapsed}s",
            f"Last: {tool} (args: {self._last_tool_args})",
        ]
        if self._agent_name:
            parts.append(f"Agent: {self._agent_name}")
        if self._session_id:
            parts.append(f"Session: {self._session_id}")
        return " | ".join(parts)

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Spawn the background timer task and reset state."""
        self._tool_count = 0
        self._last_tool = None
        self._last_tool_args = {}
        self._last_reported_count = 0
        self._start_time = time.monotonic()
        self._timer_task = asyncio.create_task(self._run_timer())

    async def stop(self) -> None:
        """Cancel the background timer task (idempotent, safe before start)."""
        if self._timer_task is None:
            return
        self._timer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._timer_task
        self._timer_task = None

    # -- hook registration ---------------------------------------------------

    def register(self, hooks: HookRegistry) -> None:
        """Register :meth:`on_tool_complete` on ``POST_TOOL_USE``."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        hooks.register(HookEvent.POST_TOOL_USE, self.on_tool_complete)

    # -- internals -----------------------------------------------------------

    async def _run_timer(self) -> None:
        """Wake every *interval* seconds and send an update if activity occurred."""
        while True:
            await asyncio.sleep(self._interval)
            if self._tool_count == self._last_reported_count:
                continue  # activity gate — nothing new
            self._last_reported_count = self._tool_count
            message = self.format_message()
            try:
                await self._channel.send(message)
            except Exception:  # noqa: BLE001 — must swallow all channel errors
                logger.warning("Failed to send progress update via channel", exc_info=True)
