"""The real SDK step lifecycle with synthetic clients, journals and process identities; no signals are sent."""

import asyncio
import dataclasses
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import psutil
import pytest

from owlbear_delivery_next.change_contracts.models import Brief, Change, Exit, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.runtimes import loop_owner, sdk_adapter, sdk_spend, sdk_teardown
from owlbear_delivery_next.runtimes.session_result import to_result
from owlbear_delivery_next.state_store import spend_ledger
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


def test_a_turn_cut_off_by_a_stop_is_no_wrong_choice(world, monkeypatch):
    data = SimpleNamespace(model="gpt-6-luna", parent_tool_call_id=None)
    held, release = threading.Event(), threading.Event()

    def checking(gate):  # a submitted result's check holds the gate while it reads the worktree
        with gate._lock:  # noqa: SLF001 - the lock a result check holds
            held.set()
            release.wait(2)

    async def opened(_client, st):
        world.steps.append(st)
        st.session = world.session
        return world.session

    async def disconnect():
        world.disconnects += 1
        world.steps[0].on_event(SimpleNamespace(type="session.idle", data=data))

    world.session.disconnect = disconnect
    monkeypatch.setattr(sdk_adapter, "_open", opened)

    async def scenario():
        task = asyncio.create_task(sdk_adapter.run(world.cfg))
        async with asyncio.timeout(2):
            while not world.steps:  # noqa: ASYNC110 - the open records its step; nothing signals it
                await asyncio.sleep(0.01)
        world.steps[0].on_event(SimpleNamespace(type="assistant.turn_start", data=data))
        await asyncio.sleep(0.01)
        check = threading.Thread(target=checking, args=(world.steps[0].gate,))
        check.start()
        held.wait(2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        stopped_while_checking = check.is_alive()
        release.set()
        check.join()
        return stopped_while_checking

    assert asyncio.run(scenario())  # the stop waited on no result check
    assert (world.disconnects, world.steps[0].run.wrong) == (1, {})


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


def test_cleanup_cancellation_inside_a_callers_except_handler_still_propagates(world):
    world.hold_stop = True

    async def scenario():
        caller = asyncio.current_task()
        assert caller is not None

        async def cancel_after_stop_starts():
            await world.entered_stop.wait()
            caller.cancel()
            await asyncio.sleep(0)
            world.release_stop.set()

        canceller = asyncio.create_task(cancel_after_stop_starts())

        def caller_error():
            msg = "an already-handled caller error"
            raise LookupError(msg)

        try:
            try:
                caller_error()
            except LookupError:
                with pytest.raises(asyncio.CancelledError):
                    await sdk_adapter.run(world.cfg)
        finally:
            world.release_stop.set()
            await canceller

    asyncio.run(scenario())
    assert world.stop_calls == 1
    assert world.steps[0].run.termination.confirmed


def test_tasks_journal_failure_still_disconnects_and_stops_without_confirming(world):
    world.fail_event = "tasks"
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert (world.disconnects, world.stop_calls) == (1, 1)
    assert not run.termination.confirmed
    assert "tasks log failed (OSError)" in run.termination.problems


@pytest.mark.parametrize("phase", ["usage", "proof"])
def test_usage_or_proof_error_is_preserved_when_force_journaling_also_fails(world, monkeypatch, phase):
    original = StoreError("synthetic usage storage failure")
    if phase == "usage":
        world.usage_error = original
    else:

        async def failed(*_args):
            raise original

        monkeypatch.setattr(sdk_adapter, "_proven", failed)
    world.stop_error = RuntimeError("synthetic stop failure")
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


@pytest.mark.parametrize("stage", ["list", "cancel", "disconnect", "stop"])
def test_real_sdk_teardown_progresses_past_repeatedly_cancel_resistant_rpc(tmp_path, monkeypatch, stage, request):
    if os.environ.get("OWLBEAR_TEST_OWNED_TEARDOWN") != stage:
        try:
            result = subprocess.run(  # noqa: S603 - this exact synthetic fixture, never a real SDK client
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-n",
                    "0",
                    "--tb=short",
                    "-o",
                    "faulthandler_timeout=3",
                    f"--basetemp={tmp_path / 'child'}",
                    f"{__file__}::test_real_sdk_teardown_progresses_past_repeatedly_cancel_resistant_rpc[{stage}]",
                ],
                env=os.environ | {"OWLBEAR_TEST_OWNED_TEARDOWN": stage},
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            pytest.fail(f"synthetic caller did not terminate: {error.stdout!r}\n{error.stderr!r}")
        assert result.returncode == 0, result.stdout + result.stderr
        return

    world = request.getfixturevalue("world")  # the parent must retain normal cleanup of its owned test child
    world.child = True
    cancellations = []

    async def resistant(*_args):
        if stage == "stop":
            world.stop_calls += 1
        while True:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancellations.append("cancel")

    target = (
        world.session.rpc.tasks if stage in {"list", "cancel"} else world.session if stage == "disconnect" else world
    )
    monkeypatch.setattr(target, stage, resistant)
    monkeypatch.setattr(sdk_teardown, "STOP_CALL", 0.01)
    monkeypatch.setattr(loop_owner, "SHUTDOWN", 0.02)
    monkeypatch.setattr(loop_owner, "RETRY", 0.001)
    started = time.monotonic()
    run = loop_owner.run(sdk_adapter.run(world.cfg))
    assert time.monotonic() - started < 1
    assert world.stop_calls == 1
    assert not run.termination.confirmed
    assert len(cancellations) >= 2
    assert any("failed" in problem or "pending" in problem for problem in run.termination.problems)
    assert str(ROOT) in {pid for e in world.events for pid in e.get("pids", {})}


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


def _metered(world, monkeypatch, *, hold=False):
    """The session opens and its run is metered, as ``_open`` does just before its first send; *hold* never sends."""

    async def opened(_client, st):
        world.steps.append(st)
        st.session, st.billed = world.session, {}
        sdk_spend.meter(st, "synthetic", "builder")
        if hold:
            await asyncio.Event().wait()

    monkeypatch.setattr(sdk_adapter, "_open", opened)


def _spend():
    assert spend_ledger.WRITER.settled(5)
    return spend_ledger.lines()


def test_a_finished_run_records_its_start_and_end_where_it_ran(world, monkeypatch):
    _metered(world, monkeypatch)
    used = {"credits": 1.25, "models": {"gpt-6-luna": {"credits": 1.25, "input": 9, "output": 1}}}

    async def usage(_session, _model):
        return used

    monkeypatch.setattr(sdk_adapter, "usage_read", usage)
    monkeypatch.setattr(sdk_teardown, "usage_once", usage)  # the same once its tasks settled
    place = spend_ledger.Where(project="owlbear", name="owlbear", clone="c1", change="fix-it", step="build")
    with spend_ledger.at(place):
        run = asyncio.run(sdk_adapter.run(world.cfg))
    start, end = _spend()
    assert (start["type"], start["agent"], start["model"], start["before"], start["change"]) == (
        "start", "builder", "gpt-6-luna", {}, "fix-it"
    )  # fmt: skip
    assert (end["run"], end["usage"], end["ending"], end["project"]) == (start["run"], used, run.ending, "owlbear")
    assert (end["tools"], end["wrong"]) == ({}, {})  # measured though nothing was called (C-28)


@pytest.mark.parametrize("read", ["read", "failed"])
def test_a_cancelled_run_reads_its_usage_before_the_disconnect_and_is_recorded(world, monkeypatch, read):
    _metered(world, monkeypatch, hold=True)
    order = []

    async def once(_session, _model):
        order.append("usage")
        if read == "failed":
            msg = "synthetic"
            raise RuntimeError(msg)
        return {"credits": 0.75, "models": {}}

    async def disconnect():
        order.append("disconnect")

    monkeypatch.setattr(sdk_teardown, "usage_once", once)
    world.session.disconnect = disconnect

    async def scenario():
        task = asyncio.create_task(sdk_adapter.run(world.cfg))
        async with asyncio.timeout(2):
            while not world.steps:  # noqa: ASYNC110 - the fixture's open records its step; nothing signals it
                await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert order == ["usage", "disconnect"]
    _, end = _spend()
    expected = (
        {"credits": 0.75, "models": {}, "incomplete": "interrupted"} if read == "read" else {"error": "RuntimeError"}
    )
    assert (end["ending"], end["usage"]) == (
        "interrupted",
        expected,
    )  # a call may still have been billed: a lower bound


def test_a_run_that_never_opened_a_session_records_nothing(world):
    asyncio.run(sdk_adapter.run(world.cfg))  # the fixture's session never sends: no spend is possible
    assert _spend() == []


def _used(credits_: float, model: str = "gpt-6-luna") -> dict:
    return {"credits": credits_, "models": {model: {"credits": credits_, "input": 1, "output": 1}}}


@pytest.mark.parametrize(("model", "check"), [("gpt-6-luna", "unknown"), ("other-model", "mismatch")])
def test_the_ledger_takes_the_usage_read_once_tasks_settled_before_the_disconnect(world, monkeypatch, model, check):
    """Sol's counterexample: the read came before task cancellation and was skipped once a usage existed (1, not 2).

    The step's own usage takes the later read too; another model that grew by then is a wrong model.
    """
    world.child = True  # a task still billing until it is cancelled
    _metered(world, monkeypatch)
    order = []

    async def usage(_session, _model):
        order.append("step usage")
        return _used(1.0)

    async def cancel(_request):
        order.append("cancel")

    async def once(_session, _model):
        order.append("final usage")
        return _used(2.0, model)

    async def disconnect():
        order.append("disconnect")

    monkeypatch.setattr(sdk_adapter, "usage_read", usage)
    monkeypatch.setattr(sdk_teardown, "usage_once", once)
    world.session.rpc.tasks.cancel, world.session.disconnect = cancel, disconnect
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert order == ["step usage", "cancel", "final usage", "disconnect"]
    _, end = _spend()
    assert (end["usage"]["credits"], run.usage["credits"], run.model_check) == (2.0, 2.0, check)


@pytest.mark.parametrize("stage", ["list", "cancel"])
def test_a_usage_read_after_an_unverified_task_cleanup_is_a_lower_bound(world, monkeypatch, stage):
    """Copilot's review: a failed task list or cancel still let the read stand as complete, so the log never added
    what a task billed after it."""
    world.child = True
    _metered(world, monkeypatch)

    async def failed(*_args):
        msg = "synthetic"
        raise RuntimeError(msg)

    async def once(_session, _model):
        return _used(2.0)

    monkeypatch.setattr(sdk_teardown, "usage_once", once)
    setattr(world.session.rpc.tasks, stage, failed)
    asyncio.run(sdk_adapter.run(world.cfg))
    _, end = _spend()
    assert (end["usage"]["credits"], end["usage"].get("incomplete")) == (2.0, "tasks unsettled")


REAL_OPEN = sdk_adapter._open  # noqa: SLF001 - the real one, which the fixture replaces


def test_a_session_that_cannot_be_noted_as_ours_is_never_created(world, monkeypatch):
    """Provenance (Improvement design §4): the manifest still reads, but this session's line was not written."""
    created = []

    async def create_session(**kw):
        created.append(kw)

    world.create_session = create_session
    monkeypatch.setattr(sdk_adapter, "_open", REAL_OPEN)
    monkeypatch.setattr(chatlogs, "note", lambda _event: False)
    run = asyncio.run(sdk_adapter.run(world.cfg))
    assert created == []
    assert (run.ending, run.detail) == ("error", f"UnnotedError: {chatlogs.UNNOTED}")


def test_a_new_session_is_noted_as_ours_before_it_is_created(world, monkeypatch):
    seen = []

    async def create_session(**kw):
        seen.append(kw["session_id"] in (chatlogs.own() or set()))
        msg = "stop here"
        raise RuntimeError(msg)

    world.create_session = create_session
    monkeypatch.setattr(sdk_adapter, "_open", REAL_OPEN)
    asyncio.run(sdk_adapter.run(world.cfg))
    assert seen == [True]


def test_a_replacement_session_is_noted_as_ours_naming_the_one_it_replaces_before_it_is_created(world, monkeypatch):
    seen = []

    async def missing(_sid):
        return None

    async def create_session(**kw):
        seen.append(kw["session_id"])
        msg = "stop here"
        raise RuntimeError(msg)

    world.get_session_metadata = missing
    world.create_session = create_session
    monkeypatch.setattr(sdk_adapter, "_open", REAL_OPEN)
    cfg = dataclasses.replace(world.cfg, resume=True, journal=sdk_adapter.Journal(event=world.event,
                              replaced=lambda: "synthetic-2"))  # fmt: skip
    noted = []
    real = chatlogs.note
    monkeypatch.setattr(chatlogs, "note", lambda e: noted.append(dict(e)) or real(e))

    run = asyncio.run(sdk_adapter.run(cfg))
    assert seen == ["synthetic-2"]
    assert run.session_id == "synthetic-2"
    first = next(e for e in noted if e["session"] == "synthetic-2")
    assert (first["event"], first["replaces"]) == ("started", "synthetic")
    monkeypatch.setattr(chatlogs, "note", lambda _e: False)  # a replacement that cannot be noted is never created
    seen.clear()
    cfg = dataclasses.replace(cfg, journal=sdk_adapter.Journal(event=world.event, replaced=lambda: "synthetic-3"))
    run = asyncio.run(sdk_adapter.run(cfg))
    assert seen == []
    assert (run.ending, run.detail) == ("error", f"UnnotedError: {chatlogs.UNNOTED}")
