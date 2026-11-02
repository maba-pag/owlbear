"""How the Spotter acts in a Delivery step (#717): the actuator on the step's own session, faked below the SDK session.

Only the session's transport (``send``, ``abort``), the bound's clock and the look's answer are faked; the step, its
gate, the Spotter, its act lines and the loop's question are real.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from copilot.generated.session_events import SessionEvent
from copilot.session import AgentMessageSource

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import Exit, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.improvement import acts, credit_meter, spotter
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter, session_result, spotter_act

STEERED = {"hand-off-fitness": "refuse-hand-off", "course-and-constraints": "steer",
           "outside-state-changes": "stop-and-resume", "irreversible-harm": "stop-and-ask"}  # fmt: skip


def event(kind: str, data: dict[str, Any]) -> SessionEvent:
    raw = {"id": str(uuid.uuid4()), "timestamp": "2026-11-02T10:00:00.000Z", "type": kind, "data": data}
    return SessionEvent.from_dict(raw)


def message(mid: str) -> SessionEvent:
    return event("user.message", {"content": "x", "messageId": mid, "source": "agent-owlbear-spotter"})


class Session:
    """The SDK session's transport: each call kept in order; ``send`` answers the runtime's message ids in turn."""

    def __init__(self, *, fails: str = "") -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.fails, self.ids = fails, iter(f"m-{i}" for i in range(1, 9))

    async def send(self, prompt: str, **kw: Any) -> str:
        self.calls.append(("send", prompt, kw))
        if self.fails:
            raise ConnectionError(self.fails)
        return next(self.ids)

    async def abort(self) -> None:
        self.calls.append(("abort",))


class Clock:
    """The bound's sleep: it ends only when the test lets it."""

    def __init__(self) -> None:
        self.up = asyncio.Event()

    async def sleep(self, _seconds: float) -> None:
        await self.up.wait()


def answering(category: str) -> spotter.Judge:
    async def look(_card: dict[str, Any], _ctx: spotter.Context, spend: credit_meter.Meter) -> str:
        spend.part().ended(None, confirmed=True)
        return json.dumps({"category": category, "note": "Deletes the backups.", "evidence": ["e1"]})

    return look


def stepped(tmp_path: Any, session: Session, category: str, clock: Clock | None = None, **acting: str,
            ) -> sdk_adapter._Step:  # fmt: skip
    """A real step with its Spotter acting through a ``StepActor`` on *session*, as the adapter binds it."""
    cfg = sdk_adapter.Session(
        StepKind.BUILD, tmp_path, "s-1", "m", resume=False, policy=Policy(tmp_path),
        observe=lambda: tools.Worktree("a", "a"), checks=(), model="gpt-6-luna",
    )  # fmt: skip
    st = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001 - the real step and gate
    base = spotter.Context(project="p", change="c1", step="build", looks=("hand-off", "sample"), sample_rate=100,
                           verbose=False, model="m", effort="medium", limit=0.75, actions=STEERED | acting,
                           arm="steered", cap=2)  # fmt: skip
    spot = spotter.Spotter(base, lambda: "s-1", answering(category))
    st.feed = SimpleNamespace(spotter=spot, seen=lambda _kind, ev: spot.seen(ev))
    spotter_act.bind(st, session)
    if clock is not None:
        st.actor.sleep = clock.sleep
    return st


def sampled(st: sdk_adapter._Step) -> None:
    """One completed call of the step's own agent: a sample at 100 %."""
    st.on_event(event("tool.execution_start", {"toolCallId": "c-1", "toolName": "bash", "arguments": {}}))
    st.on_event(event("tool.execution_complete", {"toolCallId": "c-1", "success": True, "result": {"content": "ok"}}))


def act_of(st: sdk_adapter._Step) -> acts.Act:
    [act] = acts.acts(st.feed.spotter.folder).values()
    return act


async def until(test: Any) -> None:
    for _ in range(500):
        if test():
            return
        await asyncio.sleep(0.01)
    raise AssertionError


def test_a_steer_is_delivered_only_once_the_runtime_logs_its_message_else_unconfirmed(tmp_path) -> None:
    async def main() -> list[str]:
        session, clock = Session(), Clock()
        st = stepped(tmp_path, session, "course-and-constraints", clock)
        spot, said = st.feed.spotter, []
        record = spot._record("plan", 1.0, {"call": "c-1"}, category="course-and-constraints",  # noqa: SLF001
                              note="Run the tests first.")  # fmt: skip
        act = acts.decide(record, "plan", spot.ctx, 0, {})
        acts.write(spot.folder, act)
        sending = asyncio.ensure_future(st.actor(record, act))
        await until(lambda: session.calls)
        said.append(act_of(st).delivery)  # sent, not yet seen
        st.on_event(message("m-0"))  # another message
        await asyncio.sleep(0.05)
        said.append(act_of(st).delivery)
        st.on_event(message("m-1"))  # its own
        await sending
        said.append(act_of(st).delivery)
        again = dataclasses.replace(act, record="r-2")
        acts.write(spot.folder, again)
        sending = asyncio.ensure_future(st.actor(dataclasses.replace(record, id="r-2"), again))
        await until(lambda: len(session.calls) == 2)
        clock.up.set()  # the bound passes without its message
        await sending
        said.append(acts.acts(spot.folder)["r-2"].delivery)
        [(_, prompt, kw), _] = session.calls
        assert prompt == f"{act.token} Run the tests first."
        assert kw == {"mode": "immediate", "source": AgentMessageSource("owlbear-spotter")}
        return said

    assert asyncio.run(main()) == ["pending", "pending", "delivered", "unconfirmed"]


def test_a_message_logged_before_send_returned_still_confirms_it(tmp_path) -> None:
    class Quick(Session):
        async def send(self, prompt: str, **kw: Any) -> str:
            mid = await super().send(prompt, **kw)
            st.on_event(message(mid))  # the runtime's event came first
            return mid

    async def main() -> str:
        nonlocal st
        st = stepped(tmp_path, Quick(), "course-and-constraints", Clock())
        spot = st.feed.spotter
        record = spot._record("plan", 1.0, {"call": "c-1"}, category="course-and-constraints")  # noqa: SLF001
        act = acts.decide(record, "plan", spot.ctx, 0, {})
        acts.write(spot.folder, act)
        await asyncio.wait_for(st.actor(record, act), 1)
        return act_of(st).delivery

    st: Any = None
    assert asyncio.run(main()) == "delivered"


def test_stop_and_resume_aborts_then_sends_and_its_idle_is_neither_counted_nor_reminded(tmp_path) -> None:
    async def main() -> tuple[sdk_adapter._Step, Session]:
        session = Session()
        st = stepped(tmp_path, session, "irreversible-harm", **{"irreversible-harm": "stop-and-resume"})
        st.on_event(event("assistant.turn_start", {"turnId": "t1"}))
        sampled(st)
        await until(lambda: len(session.calls) == 2)
        st.on_event(event("session.idle", {"aborted": True}))  # the aborted turn ends
        st.on_event(message("m-1"))  # the note starts the next
        await st.feed.spotter.drain()
        return st, session

    st, session = asyncio.run(main())
    assert spotter.WORK.settled(5)
    [abort, (_, prompt, kw)] = session.calls
    assert (abort, kw) == (("abort",), {"source": AgentMessageSource("owlbear-spotter")})
    assert prompt == f"{act_of(st).token} Deletes the backups."
    assert (st.run.wrong, st.idle, st.done, st.aborted, act_of(st).delivery) == ({}, False, False, False, "delivered")


@pytest.mark.parametrize(("category", "said", "acted"), [
    ("irreversible-harm", "The Spotter stopped this step for irreversible harm: Deletes the backups.", "stopped"),
    ("course-and-constraints", "The Spotter stopped this step: Deletes the backups.", "stop-and-ask"),
])  # fmt: skip
def test_stop_and_ask_ends_the_step_with_the_owners_three_options_harm_saying_why_first(
    tmp_path, category, said, acted
) -> None:
    async def main() -> tuple[sdk_adapter._Step, Session]:
        session = Session()
        st = stepped(tmp_path, session, category, **{"course-and-constraints": "stop-and-ask"})
        if category == "irreversible-harm":
            sampled(st)  # harm acts from any look
        else:
            st.feed.spotter.look("plan", 1.0, {"kind": "plan", "call": "c-1"})
        await st.feed.spotter.drain()
        return st, session

    st, session = asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert (session.calls, st.run.ending, st.done) == ([("abort",)], "spotter-ask", True)
    st.run.termination = Termination(confirmed=True)
    result = session_result.to_result(st.run, StepKind.BUILD, datetime.now(UTC))
    assert (result.exit, result.question.text) == (Exit.ASK, said)
    assert [(o.id, o.next) for o in result.question.options] == [
        ("allow", None), ("again", "retry"), ("replan", StepKind.PLAN)]  # fmt: skip
    assert "spotter-ask" not in session_result.PROVEN
    act = act_of(st)
    assert (act.delivery, acts.joined(act)["acted"]) == ("delivered", acted)


def test_a_send_that_raises_leaves_the_act_failed_with_its_whole_error(tmp_path) -> None:
    error = "the runtime closed the connection: " + "x" * 400

    async def main() -> sdk_adapter._Step:
        st = stepped(tmp_path, Session(fails=error), "irreversible-harm", **{"irreversible-harm": "stop-and-resume"})
        sampled(st)
        await st.feed.spotter.drain()
        return st

    st = asyncio.run(main())
    assert spotter.WORK.settled(5)
    act = act_of(st)
    assert (act.act, act.delivery, act.error) == ("stop-and-resume", "failed", f"ConnectionError: {error}")


UNRESUMED = "The Spotter could not stop and resume this step: ConnectionError: refused"


@pytest.mark.parametrize(("category", "fails", "said"), [
    ("irreversible-harm", "abort", f"{spotter_act.HARM.format(note='Deletes the backups.')} {UNRESUMED}"),
    ("outside-state-changes", "send", UNRESUMED),
])  # fmt: skip
def test_a_failed_stop_and_resume_ends_the_step_with_a_question_naming_the_failure(
    tmp_path, category, fails, said
) -> None:
    class Failing(Session):
        refused = "refused"

        async def send(self, prompt: str, **kw: Any) -> str:
            self.fails = self.refused if fails == "send" else ""
            return await super().send(prompt, **kw)

        async def abort(self) -> None:
            await super().abort()
            if fails == "abort":
                raise ConnectionError(self.refused)

    async def main() -> sdk_adapter._Step:
        st = stepped(tmp_path, Failing(), category, **{category: "stop-and-resume"})
        st.feed.spotter.look("plan", 1.0, {"kind": "plan", "call": "c-1"})
        await st.feed.spotter.drain()
        return st

    st = asyncio.run(main())
    assert spotter.WORK.settled(5)
    act = act_of(st)
    assert (act.act, act.delivery, act.error) == ("stop-and-resume", "failed", "ConnectionError: refused")
    assert (st.run.ending, st.run.detail, st.done) == ("spotter-ask", said, True)


class Held(Session):
    """A transport whose *held* call never answers."""

    def __init__(self, held: str) -> None:
        super().__init__()
        self.held = held

    async def send(self, prompt: str, **kw: Any) -> str:
        mid = await super().send(prompt, **kw)
        if self.held == "send":
            await asyncio.Event().wait()
        return mid

    async def abort(self) -> None:
        await super().abort()
        if self.held == "abort":
            await asyncio.Event().wait()


def test_an_abort_held_past_the_call_bound_fails_the_act_and_its_stop_to_ask_still_ends_the_step(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(spotter_act, "CALL", 0.05)
    monkeypatch.setattr(spotter, "DRAIN", 1.0)

    async def main() -> sdk_adapter._Step:
        st = stepped(tmp_path, Held("abort"), "course-and-constraints", **{"course-and-constraints": "stop-and-ask"})
        st.feed.spotter.look("plan", 1.0, {"kind": "plan", "call": "c-1"})
        await st.feed.spotter.drain()
        return st

    st = asyncio.run(main())
    assert spotter.WORK.settled(5)
    act = act_of(st)
    assert (act.delivery, act.error) == ("failed", "TimeoutError: the Spotter's abort did not answer within 0 s")
    assert (st.run.ending, st.done, st.aborted) == ("spotter-ask", True, True)  # the mark stays: the abort may land


def test_a_steer_held_past_the_call_bound_fails_the_act(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(spotter_act, "CALL", 0.05)
    monkeypatch.setattr(spotter, "DRAIN", 1.0)

    async def main() -> sdk_adapter._Step:
        st = stepped(tmp_path, Held("send"), "course-and-constraints")
        st.feed.spotter.look("plan", 1.0, {"kind": "plan", "call": "c-1"})
        await st.feed.spotter.drain()
        return st

    st = asyncio.run(main())
    assert spotter.WORK.settled(5)
    act = act_of(st)
    assert (act.act, act.delivery) == ("steer", "failed")
    assert act.error == "TimeoutError: the Spotter's note did not answer within 0 s"
    assert not st.done


@pytest.mark.parametrize(("held", "calls", "delivery", "error"), [
    ("abort", 1, "failed", "cancelled: the Spotter's abort"),
    ("", 2, "unconfirmed", "the step ended before the runtime showed it"),
])  # fmt: skip
def test_an_act_cancelled_while_its_abort_or_its_confirmation_is_held_is_never_left_pending(
    tmp_path, held, calls, delivery, error
) -> None:
    async def main() -> sdk_adapter._Step:
        session = Held(held)
        st = stepped(tmp_path, session, "outside-state-changes", Clock())
        spot = st.feed.spotter
        record = spot._record("plan", 1.0, {"call": "c-1"}, category="outside-state-changes")  # noqa: SLF001
        act = acts.decide(record, "plan", spot.ctx, 0, {})
        acts.write(spot.folder, act)
        acting = asyncio.ensure_future(st.actor(record, act))
        await until(lambda: len(session.calls) == calls)
        await asyncio.sleep(0.01)
        acting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await acting
        return st

    st = asyncio.run(main())
    assert spotter.WORK.settled(5)
    act = act_of(st)
    assert (act.act, act.delivery, act.error) == ("stop-and-resume", delivery, error)


def test_a_spotter_stop_to_ask_keeps_the_owners_question_when_the_quota_also_ran_out() -> None:
    said = spotter_act.HARM.format(note="Deletes the backups.")
    run = session_result.Run("s-1", ending="spotter-ask", detail=said, termination=Termination(confirmed=True),
                             quota=True)  # fmt: skip
    result = session_result.to_result(run, StepKind.BUILD, datetime.now(UTC))
    assert (result.exit, result.question.text) == (Exit.ASK, said)
