"""Hard result acceptance during active SDK RPCs, with only fake clocks, sessions and process identities."""

import asyncio
import dataclasses
import time
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import tool_schema, tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.runtimes import sdk_adapter, sdk_teardown
from owlbear_delivery_next.runtimes.step_budget import Budget

STEP = sdk_adapter._Step  # noqa: SLF001 - the real step and result gate are under test
PAYLOAD = tools.BuildResult(summary="No edit was needed", checks=[])


class Clock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


class Session:
    def __init__(self, listing, reminding=None):
        self.rpc = SimpleNamespace(tasks=SimpleNamespace(list=listing))
        self.reminding = reminding
        self.sent = []

    async def send(self, message):
        self.sent.append(message)
        if self.reminding is not None:
            await self.reminding()


@pytest.fixture
def clock(monkeypatch):
    fake = Clock()
    monkeypatch.setattr(sdk_adapter, "time", fake)
    monkeypatch.setattr(sdk_adapter, "POLL", 0.001)
    monkeypatch.setattr(STEP, "record_tree", lambda _self: None)
    return fake


def configured(root, limit=0.05):
    return sdk_adapter.Session(
        kind=StepKind.BUILD,
        worktree=root,
        session_id="synthetic-result-budget",
        message="Synthetic work",
        resume=False,
        policy=Policy(root),
        observe=lambda: tools.Worktree("a" * 40, "b" * 40),
        checks=(),
        model="synthetic-model",
        limit=limit,
    )


@pytest.mark.parametrize("late", [False, True])
def test_a_real_valid_result_during_snapshot_is_accepted_only_before_the_cutoff(tmp_path, clock, late):
    async def scenario():
        cfg = configured(tmp_path)
        step = STEP(cfg, asyncio.get_running_loop())
        replies = []

        async def listing():
            if late:
                clock.now += 1
            replies.append(step.gate.call(cfg.submit, PAYLOAD.model_dump()))
            return SimpleNamespace(tasks=[])

        await asyncio.wait_for(step.wait(Session(listing)), 1)
        assert [accepted for _, accepted in replies] == [not late]
        assert step.run.ending == ("deadline" if late else "result")
        assert isinstance(step.run.payload, tools.BuildResult) is (not late)

    asyncio.run(scenario())


def test_a_one_second_session_rejects_a_valid_snapshot_result_arriving_at_two_seconds(tmp_path, clock):
    async def scenario():
        cfg = configured(tmp_path, limit=1.0)
        step = STEP(cfg, asyncio.get_running_loop())
        replies = []

        async def listing():
            clock.now += 2.0
            replies.append(step.gate.call(cfg.submit, PAYLOAD.model_dump()))
            return SimpleNamespace(tasks=[])

        await asyncio.wait_for(step.wait(Session(listing)), 1)
        assert [accepted for _, accepted in replies] == [False]
        assert step.run.ending == "deadline"
        assert step.run.payload is None

    asyncio.run(scenario())


def test_validation_crossing_the_cutoff_does_not_commit_a_result(tmp_path, clock, monkeypatch):
    async def scenario():
        cfg = configured(tmp_path)
        step = STEP(cfg, asyncio.get_running_loop())
        original = step.gate._check  # noqa: SLF001 - keep real schema/worktree validation

        def checked(spec, args):
            result = original(spec, args)
            clock.now += 1
            return result

        monkeypatch.setattr(step.gate, "_check", checked)
        replies = []

        async def listing():
            replies.append(step.gate.call(cfg.submit, PAYLOAD.model_dump()))
            return SimpleNamespace(tasks=[])

        await asyncio.wait_for(step.wait(Session(listing)), 1)
        assert [ok for _, ok in replies] == [False]
        assert step.run.ending == "deadline"
        assert step.run.payload is None

    asyncio.run(scenario())


@pytest.mark.parametrize("operation", ["snapshot", "reminder"])
def test_deadline_returns_without_waiting_for_a_cancel_resistant_rpc(tmp_path, clock, operation):
    async def scenario():
        step = STEP(configured(tmp_path), asyncio.get_running_loop())
        release, cancelled = asyncio.Event(), asyncio.Event()
        if operation == "reminder":
            step.idle = True

        async def blocked():
            clock.now += 1
            try:
                await release.wait()
            except asyncio.CancelledError:
                cancelled.set()
                await release.wait()
            return SimpleNamespace(tasks=[])

        async def listed():
            return SimpleNamespace(tasks=[])

        session = Session(blocked if operation == "snapshot" else listed, blocked if operation == "reminder" else None)
        waiter = asyncio.create_task(step.wait(session))
        try:
            done, _ = await asyncio.wait({waiter}, timeout=0.5)
            assert waiter in done, "the result deadline must not await RPC cancellation cooperation"
            assert step.run.ending == "deadline"
            assert step.run.payload is None
            await asyncio.wait_for(cancelled.wait(), 0.5)
            assert step.requests
            if operation == "reminder":
                assert len(session.sent) == 1
        finally:
            release.set()
            waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
            if requests := getattr(step, "requests", ()):
                await asyncio.gather(*tuple(requests), return_exceptions=True)

    started = time.monotonic()
    asyncio.run(scenario())
    assert time.monotonic() - started < 2


def test_a_late_helper_cannot_launch_more_work_after_the_result_deadline(tmp_path, clock):
    async def scenario():
        cfg = configured(tmp_path)
        calls = []
        cfg = dataclasses.replace(cfg, helpers=((cfg.submit, lambda _args: calls.append("work") or "done"),))
        step = STEP(cfg, asyncio.get_running_loop())
        replies = []

        async def listing():
            clock.now += 1
            replies.append(step.gate.call(cfg.submit, PAYLOAD.model_dump()))
            return SimpleNamespace(tasks=[])

        await asyncio.wait_for(step.wait(Session(listing)), 1)
        assert calls == []
        assert [ok for _, ok in replies] == [False]
        assert step.run.ending == "deadline"

    asyncio.run(scenario())


@pytest.mark.parametrize("late", [False, True])
def test_helper_validation_cannot_spend_past_the_cutoff(tmp_path, clock, monkeypatch, late):
    async def scenario():
        cfg = configured(tmp_path)
        calls, replies = [], []
        cfg = dataclasses.replace(cfg, helpers=((cfg.submit, lambda _args: calls.append("work") or "done"),))
        step = STEP(cfg, asyncio.get_running_loop())
        parse = tool_schema.parse

        def validating(*args):
            parsed = parse(*args)
            if late:
                clock.now += 1
            return parsed

        monkeypatch.setattr(tool_schema, "parse", validating)

        async def listing():
            replies.append(step.gate.call(cfg.submit, PAYLOAD.model_dump()))
            clock.now += 1
            return SimpleNamespace(tasks=[])

        await asyncio.wait_for(step.wait(Session(listing)), 1)
        assert calls == ([] if late else ["work"])
        assert [ok for _, ok in replies] == [not late]
        assert step.run.ending == "deadline"

    asyncio.run(scenario())


@pytest.mark.parametrize("helper", [False, True])
def test_recording_a_tool_cannot_waive_the_result_cutoff(tmp_path, clock, monkeypatch, helper):
    async def scenario():
        cfg = configured(tmp_path)
        calls, replies = [], []
        if helper:
            cfg = dataclasses.replace(cfg, helpers=((cfg.submit, lambda _args: calls.append("work") or "done"),))
        step = STEP(cfg, asyncio.get_running_loop())
        log = step.gate.log

        def recording(**event):
            if event.get("event") == "tool" and event.get("accepted"):
                clock.now += 1
            log(**event)

        monkeypatch.setattr(step.gate, "log", recording)

        async def listing():
            replies.append(step.gate.call(cfg.submit, PAYLOAD.model_dump()))
            return SimpleNamespace(tasks=[])

        await asyncio.wait_for(step.wait(Session(listing)), 1)
        assert [ok for _, ok in replies] == [False]
        assert calls == []
        assert step.run.ending == "deadline"
        assert step.run.payload is None
        assert step.run.head is None
        assert step.run.changed == []
        assert step.run.tool_calls[cfg.submit.name]["late"] == 1
        assert step.run.tool_calls[cfg.submit.name]["calls"] == 1

    asyncio.run(scenario())


def test_model_revocation_clears_the_new_changed_path_evidence_as_well_as_the_result(tmp_path):
    async def scenario():
        step = STEP(configured(tmp_path), asyncio.get_running_loop())
        step.run.head, step.run.changed, step.run.payload = "a" * 40, ["app.py"], PAYLOAD
        step.gate.wrong_model("synthetic model mismatch")
        assert step.run.head is None
        assert step.run.changed == []
        assert step.run.payload is None
        assert step.run.model_check == "mismatch"

    asyncio.run(scenario())


def test_normal_reminder_rpc_cap_still_reports_a_named_timeout(tmp_path, clock):
    async def scenario():
        step = STEP(dataclasses.replace(configured(tmp_path), limit=100), asyncio.get_running_loop())
        step.idle = True

        async def send():
            clock.now += sdk_teardown.CALL
            await asyncio.Event().wait()

        async def listing():
            return SimpleNamespace(tasks=[])

        with pytest.raises(TimeoutError, match="send did not answer within 30 s"):
            await asyncio.wait_for(step.wait(Session(listing, send)), 1)

    asyncio.run(scenario())


def test_a_request_failure_after_cutoff_is_logged_without_replacing_the_deadline(tmp_path, clock, monkeypatch):
    async def scenario():
        step = STEP(configured(tmp_path), asyncio.get_running_loop())
        events = []
        monkeypatch.setattr(step, "log", lambda **event: events.append(event))

        async def listing():
            clock.now += 1
            msg = "synthetic late RPC failure"
            raise RuntimeError(msg)

        await asyncio.wait_for(step.wait(Session(listing)), 1)
        assert step.run.ending == "deadline"
        assert {"event": "request-failed", "operation": "tasks.list", "error": "RuntimeError"} in events

    asyncio.run(scenario())


def test_a_late_snapshot_harvests_detached_child_identity_before_its_result_is_discarded(tmp_path, clock, monkeypatch):
    async def scenario():
        events = []
        cfg = dataclasses.replace(configured(tmp_path), journal=sdk_adapter.Journal(event=events.append))
        step = STEP(cfg, asyncio.get_running_loop())
        step.run.runtime_pid, step.run.pids = 4242, {4242: 1.0}
        reads = []

        async def listing():
            reads.append("list")
            if len(reads) == 1:
                clock.now += 1
                return SimpleNamespace(tasks=[SimpleNamespace(id="detached", pid=4243, status="running")])
            return SimpleNamespace(tasks=[])

        class Client:
            async def stop(self):
                return None

        async def disconnect():
            return None

        session = Session(listing)
        session.disconnect = disconnect
        monkeypatch.setattr(step, "runtime", lambda _client: None)
        monkeypatch.setattr(processes, "started", lambda _pid: 2.0)
        monkeypatch.setattr(processes, "alive", lambda pid, _created: pid == 4243)
        monkeypatch.setattr(processes, "kill", lambda *_args: pytest.fail("no real signals in a synthetic test"))
        monkeypatch.setattr(sdk_teardown, "SETTLE", 0)
        await asyncio.wait_for(step.wait(session), 1)
        assert step.run.ending == "deadline"
        assert step.run.pids[4243] == 2.0
        assert any(e.get("pids", {}).get("4243") == 2.0 for e in events)
        termination = await sdk_teardown.teardown(Client(), session, step)
        assert len(reads) == 2
        assert not termination.confirmed
        assert termination.survivors == (4243,)

    asyncio.run(scenario())


def test_a_queued_request_rechecks_the_deadline_before_dispatch(tmp_path, clock):
    async def scenario():
        loop = asyncio.get_running_loop()
        budget = Budget(0.05, clock.monotonic, STEP(configured(tmp_path), loop))
        calls = []

        async def operation():
            calls.append("sent")
            return "late"

        loop.call_soon(setattr, clock, "now", clock.now + 1)
        assert await budget.run(operation, "send", 0.001) is None
        assert calls == []

    asyncio.run(scenario())


@pytest.mark.parametrize("lingers", [False, True])
@pytest.mark.usefixtures("clock")
def test_cleanup_confirms_no_owned_request_remains_before_releasing_termination(
    tmp_path,
    monkeypatch,
    lingers,
):
    async def scenario():
        step = STEP(configured(tmp_path), asyncio.get_running_loop())
        step.run.runtime_pid = 4242
        step.run.pids = {4242: 1.0}
        release = asyncio.Event()

        async def request():
            try:
                await release.wait()
            except asyncio.CancelledError:
                if lingers:
                    await release.wait()
                else:
                    raise

        class Client:
            async def stop(self):
                return None

        task = asyncio.create_task(request())
        step.requests.add(task)
        await asyncio.sleep(0)
        monkeypatch.setattr(step, "runtime", lambda _client: None)
        monkeypatch.setattr(processes, "alive", lambda *_args: False)
        monkeypatch.setattr(processes, "kill", lambda *_args: pytest.fail("no real signals in a synthetic test"))
        monkeypatch.setattr(sdk_teardown, "STOP_CALL", 0.01)
        monkeypatch.setattr(sdk_teardown, "SETTLE", 0.01)
        try:
            result = await sdk_teardown.teardown(Client(), None, step)
            assert result.confirmed is (not lingers)
            assert any("request task" in problem for problem in result.problems) is lingers
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(scenario())
