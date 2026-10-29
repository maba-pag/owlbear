"""A step's result budget, including RPCs that do not cooperate with cancellation."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from owlbear_delivery_next.runtimes.sdk_teardown import CALL
from owlbear_delivery_next.runtimes.step_input import reminder

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from copilot.session import CopilotSession

    from owlbear_delivery_next.runtimes.sdk_adapter import _Step


class Budget:
    """One monotonic result deadline; outstanding requests remain owned by the step's teardown."""

    def __init__(self, seconds: float, clock: Callable[[], float], st: _Step) -> None:
        self.clock, self.st, self.until = clock, st, clock() + seconds

    def remaining(self) -> float:
        """Seconds left, without restarting the budget between requests."""
        return self.until - self.clock()

    def expired(self) -> bool:
        """Whether a result can no longer be accepted."""
        return self.remaining() <= 0

    async def run[T](self, operation: Callable[[], Awaitable[T]], what: str, tick: float) -> T | None:
        """Wait only for remaining result time or the normal RPC cap, not for cancellation cooperation."""
        if self.expired():
            return None
        out: list[T] = []

        async def request() -> None:
            if self.expired():
                return
            out.append(await operation())

        def ended(task: asyncio.Task[None]) -> None:
            self.st.requests.discard(task)
            if not task.cancelled() and (error := task.exception()) is not None:
                self.st.log(event="request-failed", operation=what, error=type(error).__name__)

        task = asyncio.create_task(request())
        self.st.requests.add(task)
        task.add_done_callback(ended)
        end = min(self.until, self.clock() + CALL)
        try:
            while not task.done() and (left := end - self.clock()) > 0:
                await asyncio.wait({task}, timeout=min(left, tick))
        finally:
            if not task.done():
                task.cancel()
        if self.expired():
            return None
        if task.done():
            task.result()
            return out[0]
        msg = f"{what} did not answer within {CALL:g} s"
        raise TimeoutError(msg)


def idled(st: _Step) -> None:
    """A turn ended without a result: a wrong choice, counted as it ends so no later stop can lose it (C-28)."""
    if not (st.done or st.gate.stopped):
        st.run.count("no_result")
    st.idle = True
    st._wake()  # noqa: SLF001 - the step's own wake-up, called from its event handler


def _ended(st: _Step) -> bool:
    """Take the waiting notice of a turn that ended without a result; it was counted when it ended."""
    if not st.idle or st.done:
        return False
    st.idle = False
    return True


async def wait(st: _Step, session: CopilotSession, seconds: float, clock: Callable[[], float], tick: float) -> None:
    """Run the existing active-loop budget from wait entry; startup and cumulative resume policy stay unchanged."""
    from owlbear_delivery_next.runtimes.sdk_adapter import role_of  # noqa: PLC0415 - the adapter imports this module

    budget, reminded = Budget(seconds, clock, st), False
    st.gate.expired = budget.expired
    while not st.done:
        if budget.expired():
            st.finish("deadline", detail="step deadline")
            break
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(st.changed.wait(), min(tick, budget.remaining()))
        st.changed.clear()
        if st.done:
            break
        await st.snapshot(session, budget)
        ended = _ended(st)
        if budget.expired() and not st.done:
            st.finish("deadline", detail="step deadline")
            break
        if ended:
            if reminded:
                st.finish("no-result")
            else:
                reminded = True
                st.log(event="reminder")
                message = reminder(role_of(st.cfg), judging=st.cfg.judging)
                await budget.run(lambda message=message: session.send(message), "send", tick)


async def snapshot(st: _Step, session: CopilotSession, budget: Budget, tick: float) -> None:
    """Harvest every returned process identity inside its owned request, even when the result budget expires."""

    async def listing() -> None:
        listed = await session.rpc.tasks.list()
        st.record(*(getattr(task, "pid", None) for task in listed.tasks))

    with contextlib.suppress(Exception):  # request failures are explicitly logged by the budget's task owner
        await budget.run(listing, "tasks.list", tick)
    st.record_tree()
