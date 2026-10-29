"""Bounded SDK calls and session teardown: tasks cancelled, session disconnected, runtime stopped, else signalled."""

from __future__ import annotations

import asyncio
import contextlib
import signal
import time
from dataclasses import replace
from functools import partial
from typing import TYPE_CHECKING

from copilot.rpc import TasksCancelRequest

from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.local_system.processes import Termination, verdict
from owlbear_delivery_next.runtimes import sdk_spend
from owlbear_delivery_next.runtimes.sdk_usage import usage_once

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from copilot import CopilotClient
    from copilot.rpc import TaskInfo
    from copilot.session import CopilotSession

    from owlbear_delivery_next.local_system.processes import Pids
    from owlbear_delivery_next.runtimes.sdk_adapter import _Step

SETTLE = 10.0
CALL = 30.0  # one request while the step runs
STOP_CALL = 10.0  # one teardown request
GRACE = 5.0  # between terminate and kill


async def call[T](aw: Awaitable[T], what: str, limit: float = CALL) -> T:
    """Await one SDK request, or raise a timeout that names it."""
    try:
        return await asyncio.wait_for(aw, limit)
    except TimeoutError as exc:
        raise TimeoutError(f"{what} did not answer within {limit:.0f} s") from exc  # noqa: TRY003, EM102


async def owned_call[T](st: _Step, operation: Callable[[], Awaitable[T]], what: str) -> T:
    """Bound a teardown request independently of cancellation cooperation, retaining its pending task."""
    from owlbear_delivery_next.runtimes.step_budget import Budget  # noqa: PLC0415 - Budget uses this module's CALL

    async def requested() -> tuple[T]:
        return (await operation(),)

    answer = await Budget(STOP_CALL, time.monotonic, st).run(requested, what, STOP_CALL)
    if answer is None:
        raise TimeoutError(f"{what} did not answer within {STOP_CALL:g} s")  # noqa: TRY003, EM102
    return answer[0]


async def settle(recorded: Pids, problems: list[str], limit: float | None = None) -> Termination:
    """Wait until the recorded processes are gone, or the limit passes."""
    end = time.monotonic() + (SETTLE if limit is None else limit)
    # Polls the OS process table; there is no event to wait on.
    while (  # noqa: ASYNC110
        not (result := verdict(recorded, processes.alive, problems)).confirmed and time.monotonic() < end
    ):
        await asyncio.sleep(0.5)
    return result


def _guard(problems: list[str], what: str, stage: Callable[..., object], /, *args: object, **kwargs: object) -> None:
    try:
        stage(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - metadata failure cannot bypass physical cleanup
        problems.append(f"{what} failed ({type(exc).__name__})")


async def force(st: _Step, why: str, problems: list[str]) -> None:
    """Runtime-stop fallback: terminate, then kill the runtime (an unreaped child), recorded PIDs and their groups."""
    _guard(problems, "force-stop log", st.log, event="force-stop", reason=why, runtime_pid=st.run.runtime_pid)
    with contextlib.suppress(OSError, AttributeError):
        st.proc.terminate()
    processes.kill(st.run.pids, signal.SIGTERM)
    await settle(st.run.pids, [], GRACE)
    with contextlib.suppress(OSError, AttributeError):
        st.proc.kill()
    processes.kill(st.run.pids, signal.SIGKILL)


async def teardown(client: CopilotClient, session: CopilotSession | None, st: _Step) -> Termination:  # noqa: C901
    """(1) list, (2) cancel tasks, (3) wait, (4) disconnect, (5) stop, else signal; all bounded, then observe PIDs."""
    problems: list[str] = []
    _guard(problems, "runtime PID", st.runtime, client)
    if session is not None:
        listed: dict[int, float | None] = {}

        async def listing() -> list[TaskInfo]:
            tasks = list((await session.rpc.tasks.list()).tasks)
            for task in tasks:
                _guard(problems, "task PID record", st.record, getattr(task, "pid", None))
            return tasks

        unverified = len(problems)  # a failed list or cancel leaves the tasks' end unverified, so the usage read too
        try:
            tasks = await owned_call(st, listing, "tasks.list")
        except Exception as exc:  # noqa: BLE001 - any failure leaves termination unverified
            problems.append(f"tasks.list failed ({type(exc).__name__})")
            tasks = []
        for task in tasks:
            pid = getattr(task, "pid", None)
            if pid:
                listed[pid] = st.run.pids.get(pid)
            tid = getattr(task, "id", "?")
            try:
                if str(getattr(task.status, "value", task.status)) in {"running", "idle"}:
                    await owned_call(
                        st,
                        partial(session.rpc.tasks.cancel, TasksCancelRequest(id=task.id)),
                        "tasks.cancel",
                    )
            except Exception as exc:  # noqa: BLE001 - failed cancellation remains an unverified stage
                problems.append(f"tasks.cancel {tid} failed ({type(exc).__name__})")
        failed = any(p.startswith(("tasks.list ", "tasks.cancel ")) for p in problems[unverified:])
        _guard(problems, "task tree record", st.record_tree)
        _guard(problems, "tasks log", st.log, event="tasks", listed=sorted(listed), problems=list(problems))
        settled = (await settle(listed, [])).confirmed and not failed
        if st.metered:  # what it spent once its tasks settled: once, bounded, before the disconnect (``sdk_spend``)
            try:
                final = await owned_call(st, partial(usage_once, session, st.cfg.model), "usage read")
            except Exception as exc:  # noqa: BLE001 - an unread usage is recorded as such
                final = {"error": type(exc).__name__}
            sdk_spend.final(st, final, settled=settled)
        try:
            await owned_call(st, session.disconnect, "disconnect")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"disconnect failed ({type(exc).__name__})")
    try:
        await owned_call(st, client.stop, "runtime stop")
    except Exception as exc:  # noqa: BLE001 - errors and timeouts alike fall back to signals
        await force(st, f"runtime stop failed ({type(exc).__name__})", problems)
    rt = st.run.runtime_pid
    if rt is None:
        problems.append("runtime PID unknown")
    elif processes.alive(rt, st.run.pids.get(rt)) is not False:
        await force(st, "runtime still present after stop", problems)
    pending = await _requests(st, problems)
    await _workers(st, problems)
    observed = await settle(dict(st.run.pids), problems)
    return replace(observed, confirmed=False) if pending else observed


async def _requests(st: _Step, problems: list[str]) -> bool:
    requests = tuple(st.requests)
    if not requests:
        return False
    for task in requests:
        task.cancel()
    _, pending = await asyncio.wait(requests, timeout=STOP_CALL)
    if pending:
        problems.append(f"{len(pending)} runtime request task(s) still pending")
    return bool(pending)


async def _workers(st: _Step, problems: list[str]) -> None:
    end = time.monotonic() + STOP_CALL
    while st.workers.count() and (left := end - time.monotonic()) > 0:  # noqa: ASYNC110 - no more executor work
        await asyncio.sleep(min(0.05, left))
    if remaining := st.workers.count():
        problems.append(f"{remaining} synchronous tool worker(s) still running")


async def _wait[T](task: asyncio.Future[T]) -> bool:
    """Hold caller cancellation without passing it into the cleanup task."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            cancelled = True
    return cancelled


def _failure[T](task: asyncio.Future[T]) -> str:
    return "cancelled" if task.cancelled() else type(task.exception()).__name__


async def _protected(client: CopilotClient, st: _Step) -> tuple[Termination, bool]:
    cleanup = asyncio.create_task(teardown(client, st.session, st))
    cancelled = await _wait(cleanup)
    if not cleanup.cancelled() and cleanup.exception() is None:
        return cleanup.result(), cancelled
    problems = [f"teardown failed ({_failure(cleanup)})"]
    fallback = asyncio.create_task(force(st, "teardown failed", problems))
    cancelled |= await _wait(fallback)
    if fallback.cancelled() or fallback.exception() is not None:
        problems.append(f"force fallback failed ({_failure(fallback)})")
    observed = asyncio.create_task(settle(dict(st.run.pids), problems))
    cancelled |= await _wait(observed)
    if observed.cancelled() or observed.exception() is not None:
        problems.append(f"termination observation failed ({_failure(observed)})")
        return Termination(confirmed=False, unknown=tuple(st.run.pids), problems=tuple(problems)), cancelled
    return observed.result(), cancelled


@contextlib.asynccontextmanager
async def managed(st: _Step) -> AsyncIterator[None]:
    """Always finish owned SDK cleanup before propagating the original error or cancellation."""
    propagating = False
    try:
        yield
    except BaseException:
        propagating = True
        st.gate.stopped = True  # before teardown awaits: its idle is no wrong choice, and no gate lock is waited on
        raise
    finally:
        termination, cancelled = (
            await _protected(st.client, st) if st.client is not None else (Termination(confirmed=True), False)
        )
        st.run.termination = termination
        if cancelled and not propagating:
            raise asyncio.CancelledError
