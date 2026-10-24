"""The real SDK step lifecycle with synthetic clients, journals and process identities; no signals are sent."""

import asyncio
import os
import signal
from datetime import UTC, datetime
from types import SimpleNamespace

import psutil
import pytest

from owlbear_delivery_next.change_contracts.models import Brief, Change, Exit, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.runtimes import sdk_adapter, sdk_teardown
from owlbear_delivery_next.runtimes.session_result import to_result
from owlbear_delivery_next.state_store.database import StoreError

ROOT, CHILD = 4242, 4243
NOW = datetime(2026, 10, 24, tzinfo=UTC)


class _World:
    def __init__(self):
        self.live = {}
        self.births = {ROOT: 111.0, CHILD: 112.0}
        self.signals = []
        self.events = []
        self.steps = []
        self.stop_calls = self.disconnects = self.cancels = 0
        self.hold_start = self.hold_stop = self.child = self.reuse = False
        self.stop_cancelled = False
        self.has_pid = True
        self.stop_error = self.usage_error = None
        self.fail_event = None
        self.journal_error = OSError("synthetic journal failure")
        self.entered_start = asyncio.Event()
        self.entered_stop = asyncio.Event()
        self.release_start = asyncio.Event()
        self.release_stop = asyncio.Event()
        self.proc_effects = []
        self.proc = SimpleNamespace(
            pid=ROOT,
            terminate=lambda: self.proc_effects.append("terminate"),
            kill=lambda: self.proc_effects.append("kill"),
        )
        self._cli_process = None
        self.session = SimpleNamespace(
            rpc=SimpleNamespace(tasks=SimpleNamespace(list=self.tasks, cancel=self.cancel)),
            disconnect=self.disconnect,
        )

    async def start(self):
        if self.has_pid:
            self._cli_process = self.proc
            self.live[ROOT] = self.births[ROOT]
        if self.child:
            self.live[CHILD] = self.births[CHILD]
        self.entered_start.set()
        if self.hold_start:
            await self.release_start.wait()

    async def stop(self):
        self.stop_calls += 1
        self.entered_stop.set()
        if self.stop_error:
            raise self.stop_error
        if self.hold_stop:
            try:
                await self.release_stop.wait()
            except asyncio.CancelledError:
                self.stop_cancelled = True
                raise
        if self.live.get(ROOT) == self.births[ROOT]:
            self.live.pop(ROOT, None)

    async def tasks(self):
        task = SimpleNamespace(id="child", pid=CHILD, status=SimpleNamespace(value="running"))
        return SimpleNamespace(tasks=[task] if self.child else [])

    async def cancel(self, _request):
        self.cancels += 1

    async def disconnect(self):
        self.disconnects += 1

    def event(self, record):
        self.events.append(record)
        if record["event"] == self.fail_event:
            raise self.journal_error

    def alive(self, pid, created):
        if pid not in self.live:
            return False
        return None if created is None else self.live[pid] == created

    def kill(self, recorded, sig):
        targets, _ = processes.targets(recorded, self.alive, lambda _: -1, -2)
        self.signals.append((sig, targets))
        for pid in targets:
            self.live.pop(pid, None)
        return targets


@pytest.fixture
def world(tmp_path, monkeypatch):
    w = _World()
    w.cfg = sdk_adapter.Session(
        kind=StepKind.BUILD,
        worktree=tmp_path,
        session_id="synthetic",
        message="build",
        resume=False,
        policy=Policy(tmp_path),
        observe=Worktree,
        checks=(),
        model="gpt-6-luna",
        journal=sdk_adapter.Journal(event=w.event),
    )

    async def opened(_client, st):
        w.steps.append(st)
        st.session = w.session
        if w.reuse:
            w.live[ROOT] = 222.0

    async def usage(_session, _model):
        if w.usage_error:
            raise w.usage_error
        return {}

    def forbidden(*_args):
        pytest.fail("A lifecycle test must never signal a real process")

    monkeypatch.setattr(sdk_adapter, "CopilotClient", lambda **_: w)
    monkeypatch.setattr(sdk_adapter, "RuntimeConnection", SimpleNamespace(for_stdio=lambda **_: None))
    monkeypatch.setattr(sdk_adapter, "cli_path", lambda: "fake-copilot")
    monkeypatch.setattr(sdk_adapter.preload, "missing", lambda *_a, **_k: [])
    monkeypatch.setattr(sdk_adapter, "_open", opened)
    monkeypatch.setattr(sdk_adapter, "usage_read", usage)
    monkeypatch.setattr(processes, "started", lambda pid: w.births[pid])
    monkeypatch.setattr(processes, "alive", w.alive)
    monkeypatch.setattr(processes, "kill", w.kill)
    monkeypatch.setattr(psutil, "Process", lambda _: SimpleNamespace(children=lambda **_: []))
    monkeypatch.setattr(os, "kill", forbidden)
    monkeypatch.setattr(os, "killpg", forbidden)
    monkeypatch.setattr(sdk_teardown, "GRACE", 0)
    monkeypatch.setattr(sdk_teardown, "SETTLE", 0)
    return w


def test_cancellation_during_start_still_stops_the_owned_client(world):
    world.hold_start = True

    async def scenario():
        task = asyncio.create_task(sdk_adapter.run(world.cfg))
        async with asyncio.timeout(2):
            await world.entered_start.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert world.stop_calls == 1
    assert ROOT not in world.live
    assert any(str(ROOT) in event.get("pids", {}) for event in world.events)


def test_repeated_cancellation_during_stop_does_not_cancel_cleanup(world):
    world.hold_stop = True

    async def scenario():
        task = asyncio.create_task(sdk_adapter.run(world.cfg))
        async with asyncio.timeout(2):
            await world.entered_stop.wait()
        try:
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
        finally:
            world.release_stop.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert not world.stop_cancelled
    assert world.stop_calls == 1
    assert world.steps[0].run.termination.confirmed


def test_tasks_journal_failure_still_disconnects_and_stops_without_confirming(world):
    world.fail_event = "tasks"
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert (world.disconnects, world.stop_calls) == (1, 1)
    assert not run.termination.confirmed
    assert "tasks log failed (OSError)" in run.termination.problems


def test_usage_error_is_preserved_when_force_journaling_also_fails(world):
    original = StoreError("synthetic usage storage failure")
    world.usage_error, world.stop_error = original, RuntimeError("synthetic stop failure")
    world.fail_event = "force-stop"
    with pytest.raises(StoreError) as caught:
        asyncio.run(sdk_adapter.run(world.cfg))
    assert caught.value is original
    assert world.stop_calls == 1
    assert world.proc_effects == ["terminate", "kill"]
    assert [sig for sig, _ in world.signals] == [signal.SIGTERM, signal.SIGKILL]


def test_a_known_orphan_remains_a_stop_and_cannot_start_the_successor(world):
    world.child = True
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert (world.cancels, world.disconnects, world.stop_calls) == (1, 1, 1)
    assert run.termination.survivors == (CHILD,)
    result = to_result(run, StepKind.BUILD, NOW)
    assert result.exit == Exit.STOP
    c = Change(
        slug="synthetic",
        brief=Brief(version=1, challenged=1, approved_version=1),
        plan=Plan(tasks=[Task(id="t1", title="first"), Task(id="t2", title="successor")]),
        step=Step(kind=StepKind.BUILD, task="t1"),
    )
    stopped = loop.apply(c, result, NOW)
    assert not any(task.done for task in stopped.plan.tasks)
    assert loop.next_step(stopped, NOW) is None


def test_forced_cleanup_never_signals_a_reused_pid(world):
    world.reuse, world.stop_error = True, RuntimeError("synthetic stop failure")
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert world.live[ROOT] == 222.0
    assert all(not targets for _, targets in world.signals)
    assert run.termination.confirmed


def test_a_clean_lifecycle_confirms_without_signals(world):
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert run.termination.confirmed
    assert world.stop_calls == 1
    assert world.signals == []


def test_unknown_runtime_identity_cannot_be_reported_confirmed(world):
    world.has_pid = False
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert not run.termination.confirmed
    assert "runtime PID unknown" in run.termination.problems


@pytest.mark.parametrize("error", [RuntimeError("synthetic teardown failure"), asyncio.CancelledError()])
def test_escaped_teardown_failure_still_forces_and_observes_unconfirmed(world, monkeypatch, error):
    async def failed(*_args):
        raise error

    monkeypatch.setattr(sdk_teardown, "teardown", failed)
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert not run.termination.confirmed
    assert world.proc_effects == ["terminate", "kill"]
    assert ROOT not in world.live
