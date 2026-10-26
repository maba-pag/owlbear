"""Own an SDK loop through bounded asynchronous shutdown without losing its returned run or accounting."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes.sdk_teardown import STOP_CALL
from owlbear_delivery_next.runtimes.session_result import Run

if TYPE_CHECKING:
    from collections.abc import Coroutine

SHUTDOWN = STOP_CALL
RETRY = 0.25
LOG = logging.getLogger(__name__)


def _live() -> set[asyncio.Task[object]]:
    current = asyncio.current_task()
    return {task for task in asyncio.all_tasks() if task is not current and not task.done()}


async def _stop(end: float, problems: list[str]) -> set[asyncio.Task[object]]:
    loop = asyncio.get_running_loop()
    while (live := _live()) and (left := end - loop.time()) > 0:
        for task in live:
            task.cancel()
        done, _ = await asyncio.wait(live, timeout=min(left, RETRY))
        problems.extend(
            f"asynchronous shutdown task failed ({type(error).__name__})"
            for task in done
            if not task.cancelled() and (error := task.exception()) is not None
        )
    return _live()


async def _drain(seconds: float) -> tuple[str, ...]:
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    problems: list[str] = []
    live = await _stop(end, problems)
    if not live:
        closing = asyncio.create_task(loop.shutdown_asyncgens(), name="sdk-async-generator-shutdown")
        done, _ = await asyncio.wait({closing}, timeout=max(0.0, end - loop.time()))
        if closing in done and not closing.cancelled() and (error := closing.exception()) is not None:
            problems.append(f"asynchronous shutdown of generators failed ({type(error).__name__})")
        live = await _stop(end, problems)
    if live:
        names = ", ".join(sorted(task.get_name() for task in live))
        problems.append(f"asynchronous shutdown left {len(live)} task(s) pending: {names}")
    return tuple(problems)


def _shutdown(loop: asyncio.AbstractEventLoop) -> tuple[str, ...]:
    problems: list[str] = []
    loop.run_until_complete(_stop(loop.time() + SHUTDOWN, problems))
    # Cancelling a to_thread waiter does not stop its tool; keep its caller's locks until executor work settles.
    loop.run_until_complete(loop.shutdown_default_executor())
    problems.extend(loop.run_until_complete(_drain(SHUTDOWN)))
    if problems:
        LOG.warning("SDK %s", "; ".join(problems))
    return problems


def run[T: Run | list[Run]](main: Coroutine[object, object, T]) -> T:
    """Run an SDK boundary; preserve its value and mark termination unconfirmed if asynchronous shutdown fails."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        main.close()
        msg = "an SDK session cannot run inside another event loop"
        raise RuntimeError(msg)
    runner = asyncio.Runner()
    loop = runner.get_loop()
    try:
        try:
            value = runner.run(main)
        except BaseException as primary:
            try:
                problems = _shutdown(loop)
            except BaseException as cleanup:
                primary.add_note(f"asynchronous shutdown failed ({type(cleanup).__name__})")
                raise primary from cleanup
            for problem in problems:
                primary.add_note(problem)
            raise
        problems = _shutdown(loop)
        if problems:
            for done in [value] if isinstance(value, Run) else value:
                previous = done.termination or Termination(confirmed=False, unknown=tuple(sorted(done.pids)))
                done.termination = replace(previous, confirmed=False, problems=(*previous.problems, *problems))
        return value
    finally:
        # Runner.close() gathers resistant tasks without a deadline; a closed loop cannot dispatch them again.
        asyncio.set_event_loop(None)
        loop.close()
