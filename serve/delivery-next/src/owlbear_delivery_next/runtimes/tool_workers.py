"""Own synchronous tool work even when cancellation ends its asynchronous waiter first."""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

LOG = logging.getLogger(__name__)


@dataclass(eq=False, slots=True)
class _Call:
    started: bool = False
    cancelled: bool = False


class Workers:
    """Queued and running tool calls whose executor threads must not be mistaken for completed work."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.calls: set[_Call] = set()

    def count(self) -> int:
        """How many operations can still run, including cancelled waiters whose operation already started."""
        with self.lock:
            return len(self.calls)

    async def call[T](self, operation: Callable[[], T]) -> T:
        """Run a tool off-loop; revoke a cancelled queue entry or retain ownership until running work finishes."""
        ticket = _Call()
        with self.lock:
            self.calls.add(ticket)

        def invoke() -> T:
            with self.lock:
                if ticket.cancelled:
                    raise asyncio.CancelledError
                ticket.started = True
            try:
                return operation()
            except BaseException:
                LOG.exception("SDK tool worker failed")
                raise
            finally:
                with self.lock:
                    self.calls.discard(ticket)

        try:
            return await asyncio.to_thread(invoke)
        except BaseException:
            with self.lock:
                if not ticket.started:
                    ticket.cancelled = True
                    self.calls.discard(ticket)
            raise
