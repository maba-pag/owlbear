"""Cooperative stopping on reported spend for one SDK session (D-01M5XCD49YHHR1NQKKY8TQD0C3): no SDK credit cap.

``Limit.heard`` charges each ``assistant.usage`` event to the session's share of its meter
(``improvement.credit_meter``); once the meter closes, ``turn`` aborts the running turn. What cannot be stopped: a call
already made, whose cost is reported only once it ends, and whatever the runtime bills before the abort reaches it; so
the spend may pass the limit. Every wait is bounded: the abort, the turn's end after it and the read of the session's
reported total each take at most *bound* seconds. A turn whose end could not be confirmed leaves its share unknown, and
a total read then is provisional. An answer completed before the abort is the caller's to keep.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from owlbear_delivery_next.improvement.credit_meter import Meter


async def bounded(work: Callable[[], Awaitable[Any]], seconds: float) -> tuple[bool, Any]:
    """Run *work* at most *seconds*; whether it ended well, and its result. One left over is cancelled, not awaited."""

    async def run() -> Any:  # noqa: ANN401 - the work's result; it may fail before it awaits anything
        return await work()

    task = asyncio.ensure_future(run())
    done, _ = await asyncio.wait({task}, timeout=seconds)
    if not done:
        task.cancel()
        return False, None
    if task.cancelled() or task.exception() is not None:
        return False, None
    return True, task.result()


class Limit:
    """One session's billed calls charged to *meter*, and the turn stopped once it closes."""

    def __init__(self, meter: Meter) -> None:
        self.part = meter.part()
        self.reached = asyncio.Event()
        self.loop = asyncio.get_running_loop()

    def heard(self, ev: Any) -> None:  # noqa: ANN401 - an SDK event
        """Charge one billed call; the turn is stopped once the meter closes."""
        if getattr(getattr(ev, "type", None), "value", getattr(ev, "type", None)) != "assistant.usage":
            return
        nano = getattr(getattr(getattr(ev, "data", None), "copilot_usage", None), "total_nano_aiu", None)
        cost = nano / 1e9 if isinstance(nano, int | float) and not isinstance(nano, bool) else None
        if not self.part.call(cost):
            with contextlib.suppress(RuntimeError):  # a late event after the session's loop closed: charged only
                self.loop.call_soon_threadsafe(self.reached.set)

    async def turn(self, send: Awaitable[Any], abort: Callable[[], Awaitable[Any]], bound: float) -> bool:
        """Await the turn *send* until it ends or the meter closes; whether its end is confirmed.

        The turn's own error is raised. Once the meter closes, *abort* is asked within *bound*, then the turn gets
        *bound* to end; one that does not is left unconfirmed. A cancellation stops the wait, never the turn: the
        caller's teardown ends the session.
        """
        sending, reaching = asyncio.ensure_future(send), asyncio.ensure_future(self.reached.wait())
        try:
            await asyncio.wait({sending, reaching}, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            sending.cancel()
            raise
        finally:
            reaching.cancel()
        if sending.done():
            sending.result()
            return True
        await bounded(abort, bound)
        done, _ = await asyncio.wait({sending}, timeout=bound)
        if not done:
            sending.cancel()
            return False
        with contextlib.suppress(Exception):  # the abort ends the turn with an error of its own
            sending.result()
        return not sending.cancelled()

    async def settle(self, metrics: Callable[[], Awaitable[Any]], *, confirmed: bool, bound: float) -> None:
        """Read the session's reported total within *bound* and reconcile this session's share with it."""
        read, got = await bounded(metrics, bound)
        nano = getattr(got, "total_nano_aiu", None) if read else None
        total = nano / 1e9 if isinstance(nano, int | float) and not isinstance(nano, bool) else None
        self.part.ended(total, confirmed=confirmed)
