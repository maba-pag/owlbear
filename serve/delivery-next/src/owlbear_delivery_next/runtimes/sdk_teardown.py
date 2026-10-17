"""Bounded SDK calls and session teardown: tasks cancelled, session disconnected, runtime stopped, else signalled."""

from __future__ import annotations

import asyncio
import contextlib
import signal
import time
from typing import TYPE_CHECKING

from copilot.rpc import TasksCancelRequest

from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.local_system.processes import Termination, verdict

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from copilot import CopilotClient
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


async def settle(recorded: Pids, problems: list[str], limit: float | None = None) -> Termination:
    """Wait until the recorded processes are gone, or the limit passes."""
    end = time.monotonic() + (SETTLE if limit is None else limit)
    # Polls the OS process table; there is no event to wait on.
    while (  # noqa: ASYNC110
        not (result := verdict(recorded, processes.alive, problems)).confirmed and time.monotonic() < end
    ):
        await asyncio.sleep(0.5)
    return result


async def force(st: _Step, why: str) -> None:
    """Runtime-stop fallback: terminate, then kill the runtime (an unreaped child), recorded PIDs and their groups."""
    st.log(event="force-stop", reason=why, runtime_pid=st.run.runtime_pid)
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
    st.runtime(client)
    if session is not None:
        listed: dict[int, float | None] = {}
        try:
            tasks = (await call(session.rpc.tasks.list(), "tasks.list", STOP_CALL)).tasks
        except Exception as exc:  # noqa: BLE001 - any failure leaves termination unverified
            problems.append(f"tasks.list failed ({type(exc).__name__})")
            tasks = []
        for task in tasks:
            st.record(getattr(task, "pid", None))
            if pid := getattr(task, "pid", None):
                listed[pid] = st.run.pids.get(pid)
            if str(getattr(task.status, "value", task.status)) in {"running", "idle"}:
                try:
                    await call(session.rpc.tasks.cancel(TasksCancelRequest(id=task.id)), "tasks.cancel", STOP_CALL)
                except Exception as exc:  # noqa: BLE001
                    problems.append(f"tasks.cancel {task.id} failed ({type(exc).__name__})")
        st.record_tree()
        st.log(event="tasks", listed=sorted(listed), problems=list(problems))
        await settle(listed, [])
        try:
            await call(session.disconnect(), "disconnect", STOP_CALL)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"disconnect failed ({type(exc).__name__})")
    try:
        await call(client.stop(), "runtime stop", STOP_CALL)
    except Exception as exc:  # noqa: BLE001 - errors and timeouts alike fall back to signals
        await force(st, f"runtime stop failed ({type(exc).__name__})")
    rt = st.run.runtime_pid
    if rt is None:
        problems.append("runtime PID unknown")
    elif processes.alive(rt, st.run.pids.get(rt)) is not False:
        await force(st, "runtime still present after stop")
    return await settle(dict(st.run.pids), problems)
