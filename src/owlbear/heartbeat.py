"""HeartbeatRunner — proactive agent wakeups via HEARTBEAT.md.

Periodically reads a heartbeat prompt file and sends it to the agent.
If the agent responds with ``HEARTBEAT_OK`` (case-insensitive), the
result is suppressed.  Otherwise the findings are forwarded to the
channel for user attention.

The runner respects an active-hours window (UTC) and exits cleanly
when the shared *shutdown_event* is set.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.channels.base import ChannelPlugin
    from owlbear.core.agent import OwlBearAgent

logger = logging.getLogger(__name__)


def _utc_hour() -> int:
    """Return the current UTC hour (0-23).  Extracted for test patching."""
    return datetime.now(UTC).hour


def _is_active_hour(hour: int, active_hours: tuple[int, int]) -> bool:
    """Return *True* if *hour* falls inside the *active_hours* window.

    Supports overnight wrap-around: ``(22, 6)`` means 22-23 and 0-5.
    """
    start, end = active_hours
    if start < end:
        return start <= hour < end
    # Overnight wrap-around
    return hour >= start or hour < end


class HeartbeatRunner:
    """Periodic agent wakeup driven by a HEARTBEAT.md prompt file.

    Args:
        agent: The :class:`~owlbear.core.agent.OwlBearAgent` to invoke each tick.
        channel: Channel to forward non-OK findings to the user.
        interval_seconds: Seconds between heartbeat ticks.
        active_hours: ``(start, end)`` UTC hours. Ticks outside this window are
            skipped.
        shutdown_event: Shared event; setting it causes the run loop to exit.
        heartbeat_path: Path to the HEARTBEAT.md prompt file.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        agent: OwlBearAgent,
        channel: ChannelPlugin,
        interval_seconds: float,
        active_hours: tuple[int, int],
        shutdown_event: asyncio.Event,
        heartbeat_path: Path,
    ) -> None:
        self._agent = agent
        self._channel = channel
        self._interval = interval_seconds
        self._active_hours = active_hours
        self._shutdown = shutdown_event
        self._heartbeat_path = heartbeat_path

    async def run(self) -> None:
        """Main loop: tick → sleep → repeat until shutdown."""
        while not self._shutdown.is_set():
            await self._tick()

            # Interruptible sleep — exits early when shutdown is set
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self._shutdown.wait(),
                    timeout=self._interval,
                )

    async def _tick(self) -> None:
        """Execute a single heartbeat tick."""
        # Active hours gate
        if not _is_active_hour(_utc_hour(), self._active_hours):
            return

        # Read heartbeat prompt
        if not self._heartbeat_path.exists():
            logger.debug("Heartbeat file missing: %s — skipping tick", self._heartbeat_path)
            return

        prompt = self._heartbeat_path.read_text()

        # Call agent
        try:
            response = await self._agent.turn(prompt)
        except Exception:
            logger.exception("Heartbeat agent.turn() failed")
            return

        # HEARTBEAT_OK suppresses channel delivery
        if "heartbeat_ok" in response.lower():
            return

        await self._channel.send(response)
