"""The Spotter (Improvement design §4): intake, card, looks, records with category and action, limits, the hook."""

from __future__ import annotations

import asyncio
import dataclasses
import gzip
import json
import random
import re
import stat
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar

import pytest
from copilot.generated.session_events import SessionEvent
from copilot.tools import ToolInvocation

from owlbear_delivery_next.change_contracts import pick_tools
from owlbear_delivery_next.change_contracts.models import Brief, Change, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import ReviewResult, Worktree
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.improvement import (
    acts,
    card,
    cases,
    chatlogs,
    credit_meter,
    events,
    improvement_view,
    retro_units,
    spotter,
)
from owlbear_delivery_next.improvement.events import Kept
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter, spend_reconcile, spotter_look, step_decisions, step_tools
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings.config import Layer, SettingsUnset, resolve
from owlbear_delivery_next.settings.improvement import CATEGORIES, Spotter
from owlbear_delivery_next.state_store import spend_ledger, spend_shares, spotter_arms
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import lookup, pending_child, sessions, watched

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.state_store.spend_ledger import Where

REAL_LOOK = spotter_look.judged  # taken before the suite's fixture replaces it


def event(kind: str, data: dict[str, Any], *, second: int = 0, agent: str | None = None) -> SessionEvent:
    raw = {"id": str(uuid.uuid4()), "timestamp": f"2026-10-26T10:{second // 60:02d}:{second % 60:02d}.000Z",
           "type": kind, "data": data}  # fmt: skip
    return SessionEvent.from_dict(raw | ({"agentId": agent} if agent else {}))


def asked(text: str, second: int = 0) -> SessionEvent:
    return event("user.message", {"content": text}, second=second)


def said(text: str, second: int = 0) -> SessionEvent:
    return event("assistant.message", {"messageId": str(uuid.uuid4()), "content": text}, second=second)


def started(cid: str, tool: str, args: dict[str, Any], second: int = 0, **kw: Any) -> SessionEvent:
    return event("tool.execution_start", {"toolCallId": cid, "toolName": tool, "arguments": args} | kw, second=second)


def done(cid: str, result: str, *, ok: bool = True, second: int = 0) -> SessionEvent:
    data = {"toolCallId": cid, "success": ok}
    data |= {"result": {"content": result}} if ok else {"error": {"message": result}}
    return event("tool.execution_complete", data, second=second)


ACTIONS = {"hand-off-fitness": "steer", "course-and-constraints": "record", "outside-state-changes": "show-owner",
           "irreversible-harm": "stop-and-ask"}  # fmt: skip


def ctx(**kw: Any) -> spotter.Context:
    base = spotter.Context(project="p", change="c1", step="build", looks=("hand-off",), sample_rate=0, verbose=False,
                           model="gpt-6-luna", effort="medium", limit=0.75, actions=ACTIONS)  # fmt: skip
    return dataclasses.replace(base, **kw)


def records() -> list[dict[str, Any]]:
    return [json.loads(x) for f in sorted(spotter.root().glob("records-*.jsonl")) for x in f.read_text().splitlines()]


def meter(limit: float = 0.75) -> credit_meter.Meter:
    return credit_meter.Meter(limit, "look")


def judge(
    answer: str = '{"category": "none"}',
    *,
    wait: float = 0.0,
    seen: list | None = None,
    reached: asyncio.Event | None = None,
    cost: float = 0.25,
) -> spotter.Judge:
    """A look that bills one call of *cost* credits and answers *answer*, as a confirmed session."""

    async def look(the_card: dict[str, Any], _ctx: spotter.Context, spend: credit_meter.Meter) -> str:
        if seen is not None:
            seen.append(the_card)
        if reached is not None:
            reached.set()
        await asyncio.sleep(wait)
        part = spend.part()
        part.started(f"sdk-{spend.id}")
        part.call(cost)
        part.ended(None, confirmed=True)
        return answer

    return look


def test_the_intake_reads_sdk_events_keeps_the_main_agent_only_and_freezes_a_snapshot() -> None:
    kept = Kept()
    for ev in (
        asked("Build greet()."),
        said("I will edit a.py, then test."),
        started("c1", "bash", {"command": "uv run pytest"}, second=5),
        started("s1", "bash", {"command": "rm -rf x"}, second=6, parentToolCallId="task-1"),
        event("tool.execution_start", {"toolCallId": "s2", "toolName": "view", "arguments": {}}, agent="sub"),
    ):
        kept.add(ev)  # fmt: skip
    frozen = kept.snapshot()
    kept.add(done("c1", "1 passed", second=9))
    assert frozen["task"] == "Build greet()."
    assert [a["id"] for a in frozen["actions"]] == ["c1"]  # neither subagent call
    assert "result" not in frozen["actions"][0]  # completed after the snapshot
    assert kept.snapshot()["actions"][0]["result"] == "1 passed"


def test_an_answer_written_by_a_stop_is_no_answer_and_a_real_one_is_kept() -> None:
    kept = Kept()
    kept.add(started("q1", "ask_user", {"question": "Which file?"}))
    kept.add(done("q1", "a.py"))
    kept.add(started("q2", "ask_user", {"question": "Go on?"}))
    kept.add(event("abort", {"reason": "user_abort"}))
    kept.add(done("q2", "The user cancelled the request."))
    assert [a["answer"] for a in kept.snapshot()["answers"]] == ["a.py"]


def test_the_card_holds_intent_superseding_requests_edits_failures_and_the_runners_context() -> None:
    kept = Kept()
    for ev in (
        asked("Build greet() and test it."),
        said("Plan: edit a.py, run pytest."),
        started("e1", "edit", {"path": "/Users/x/work/a.py", "old_str": "a", "new_str": "b"}, second=10),
        done("e1", "ok", second=11),
        started("t1", "bash", {"command": "uv run pytest -q"}, second=20),
        done("t1", "1 failed", ok=False, second=40),
        asked("Keep the old name too.", second=50),
    ):
        kept.add(ev)  # fmt: skip
    runner = {"step": "build", "open_work": ["t2: docs"], "decisions": ["## Decisions in force", "- D1"]}
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00", "kind": "hand-off"}, runner)
    assert built["intent"]["task"] == "Build greet() and test it."
    assert built["intent"]["later_requests"] == ["Keep the old name too."]
    whys = {e["why"]: e for e in built["evidence"]}
    assert whys["failed"]["output"].startswith('{"message": "1 failed"')
    assert '"new_str": "b"' in whys["edit"]["output"]  # an edit's evidence is the change itself
    assert "/Users/x/work/a.py" in whys["edit"]["args"]  # a path is no secret
    assert (built["open_work"], built["decisions"], built["timing"]["minutes_since_edit"]) == (
        ["t2: docs"], "## Decisions in force\n- D1", 1)  # fmt: skip


def test_the_card_drops_emails_keeps_credentials_as_the_agent_saw_them_and_is_bounded() -> None:
    kept = Kept()
    token = "ghp_" + "a" * 36
    kept.add(asked(f"Use token={token} and mail owner@example.com. " + "x" * 9000))
    for i in range(60):
        kept.add(started(f"c{i}", "bash", {"command": f"uv run pytest -k t{i} " + "y" * 3000}, second=i))
        kept.add(done(f"c{i}", "z" * 5000, ok=False, second=i))
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00"}, {"decisions": ["d" * 20000]})
    text = json.dumps(built, ensure_ascii=False)
    assert token in text  # not masked: the owner's choice, the look sees what the agent saw
    assert "owner@example.com" not in text
    assert len(text) <= card.BOUND


def test_a_hand_off_starts_a_look_without_waiting_and_records_it_owner_only() -> None:
    async def main() -> float:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge(wait=0.2))
        spot.seen(asked("Build greet()."))
        loop = asyncio.get_running_loop()
        began = loop.time()
        spot.handed_off("call-9", {"summary": "done"})
        returned = loop.time() - began
        assert len(spot.tasks) == 1
        await spot.drain()
        return returned

    returned = asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert returned < 0.05
    [rec] = records()
    assert (rec["look"], rec["category"], rec["action"], rec["session"], rec["skipped"]) == (
        "hand-off", "none", "", "s-1", "")  # fmt: skip
    assert "mode" not in rec
    assert "verdict" not in rec
    sent = cases.snapshot(verbose=False)
    assert (rec["prompt"], rec["cases"], rec["credits"], rec["credits_known"], rec["limit"]) == (
        sent.hash, 0, 0.25, True, 0.75)  # fmt: skip
    assert (rec["stopped"], rec["stopped_by"]) == ("", "")
    assert rec["sdk_sessions"] == [f"sdk-{rec['id']}"]  # the look's meter carries the record's own id
    folder = spotter.root()
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert stat.S_IMODE((folder / f"records-{spotter._today()}.jsonl").stat().st_mode) == 0o600  # noqa: SLF001
    saved = folder / "cards" / f"{rec['id']}.json.gz"
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    with gzip.open(saved, "rt") as f:
        assert json.load(f)["moment"]["call"] == "call-9"


def test_a_look_still_running_at_the_steps_end_is_recorded_skipped(monkeypatch) -> None:
    monkeypatch.setattr(spotter, "DRAIN", 0.05)

    async def main() -> None:
        entered, never = asyncio.Event(), asyncio.Event()

        async def pending_until_cancelled(_card: dict[str, Any], _ctx: spotter.Context, spend: Any) -> str:
            part = spend.part()
            entered.set()  # the look's model call has begun: its card is done
            try:
                await never.wait()  # never set: only the step's end, cancelling the look, ends it
            finally:
                part.ended(None, confirmed=False)  # as the real look: a turn stopped waiting for is unconfirmed
            return '{"verdict": "silent"}'

        spot = spotter.Spotter(ctx(), lambda: "s-1", pending_until_cancelled)
        spot.handed_off("call-1", {})
        await asyncio.wait_for(entered.wait(), timeout=30)  # running when the step ends, not merely queued
        await spot.drain()
        assert not spot.tasks

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert [(r["skipped"], r["credits"], r["credits_known"]) for r in records()] == [
        ("the step ended while the look ran", 0.0, False)]  # fmt: skip  # its spend is unknown, never estimated


def test_a_look_past_its_time_is_skipped_and_a_wrong_answer_fails_never_silent(monkeypatch) -> None:
    monkeypatch.setattr(spotter, "LOOK", 0.05)

    async def main() -> None:
        for answer, wait in (('{"category": "none"}', 1.0), ("I think it is fine.", 0.0)):
            spot = spotter.Spotter(ctx(), lambda: "s-1", judge(answer, wait=wait))
            spot.handed_off("c", {})
            await asyncio.gather(*spot.tasks)

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert [(r["category"], r["action"], r["skipped"][:4]) for r in records()] == [("", "", "time"), ("failed", "", "")]


def test_a_freeze_read_that_raises_says_so_and_leaks_no_admission(monkeypatch) -> None:
    """The chats' admission (*room*, *left*) is taken only once the look's frozen settings are read."""
    admitted, reads = [], iter([OSError("test file unreadable"), None])

    def active() -> None:
        if isinstance(read := next(reads), Exception):
            raise read

    def room() -> str:
        if admitted:
            return "a chat look is running"
        admitted.append(1)
        return ""

    monkeypatch.setattr(spotter.spotter_test, "active", active)

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s1", judge(), room=room, left=admitted.pop)
        with pytest.raises(OSError, match="test file unreadable"):
            spot.look("plan", 1.0, {"kind": "plan"})
        spot.look("plan", 1.0, {"kind": "plan"})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert [(r["look"], r["skipped"]) for r in records()] == [("plan", "")]
    assert admitted == []


def test_looks_past_capacity_are_recorded_skipped_and_a_look_stopped_at_its_limit_says_so() -> None:
    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge(wait=0.1))
        for i in range(2):  # two run; a third look other than a hand-off finds no room
            spot.handed_off(f"c{i}", {})
        spot.look("plan", 1.0, {"kind": "plan", "call": "c2"})
        await asyncio.wait(set(spot.tasks))
        stopped = spotter.Spotter(ctx(), lambda: "s-2", judge("", cost=0.9))  # aborted before it answered
        stopped.handed_off("c3", {})
        passed = spotter.Spotter(ctx(), lambda: "s-3", judge(cost=0.9))  # its one call passed the limit, answered
        passed.handed_off("c4", {})
        for spot_ in (spot, stopped, passed):
            await spot_.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    got = {r["session"] + r["call"]: r for r in records()}
    assert sorted(r["skipped"].split(":")[0] for r in got.values()) == ["", "", "", "capacity", "credit limit"]
    assert got["s-2c3"]["skipped"] == "credit limit: reached (look) before an answer"
    assert (got["s-2c3"]["category"], got["s-2c3"]["credits"], got["s-2c3"]["stopped"]) == ("", 0.9, "reached")
    assert (got["s-3c4"]["category"], got["s-3c4"]["stopped"], got["s-3c4"]["stopped_by"]) == ("none", "reached",
                                                                                              "look")  # fmt: skip
    assert got["s-1c0"]["stopped"] == ""  # 0.25 of 0.75: within its limit


def test_samples_follow_the_seeded_rate_and_a_state_change_is_preliminary() -> None:
    answer = (
        '{"category": "outside-state-changes", "note": "Ask first.", "evidence": ["e1"], '
        '"state_change": "pushes the branch"}'
    )

    async def main() -> int:
        seeded = random.Random(7)  # noqa: S311
        spot = spotter.Spotter(ctx(looks=("sample",), sample_rate=30), lambda: "s-1", judge(answer), seeded)
        for i in range(20):
            spot.seen(started(f"c{i}", "bash", {"command": "ls"}))
            spot.seen(done(f"c{i}", "ok"))
            while spot.tasks:  # each look, record and settlement end before the next action
                await asyncio.wait(set(spot.tasks))
        await spot.drain()
        rng = random.Random(7)  # noqa: S311
        return sum(rng.random() * 100 < 30 for _ in range(20))

    expected = asyncio.run(main())
    assert spotter.WORK.settled(5)
    got = records()
    assert 0 < len(got) == expected
    assert {(r["look"], r["probability"], r["preliminary"], r["category"], r["action"], r["skipped"]) for r in got} == {
        ("sample", 0.3, True, "outside-state-changes", "show-owner", "")}  # fmt: skip


def test_an_acting_action_is_only_recorded_and_a_hand_off_is_not_looked_at_unless_chosen() -> None:
    answer = '{"category": "hand-off-fitness", "note": "Criterion 2 is unmet: its test fails.", "evidence": ["e4"]}'

    async def main() -> None:
        live = spotter.Spotter(ctx(), lambda: "s-1", judge(answer))
        live.handed_off("c", {})
        await live.drain()
        quiet = spotter.Spotter(ctx(looks=("sample",)), lambda: "s-1", judge())
        quiet.handed_off("c", {})
        assert not quiet.tasks

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert [(r["category"], r["action"], r["note"]) for r in records()] == [
        ("hand-off-fitness", "steer", "Criterion 2 is unmet: its test fails.")]  # fmt: skip


def test_the_submit_tool_starts_the_look_before_delivery_handles_it_and_keeps_its_outcome(tmp_path) -> None:
    order: list[str] = []

    class Seen(spotter.Spotter):
        def handed_off(self, call_id: str, arguments: Any, **kw: Any) -> Any:
            order.append(f"look {call_id} {arguments}")
            return super().handed_off(call_id, arguments, **kw)

    async def main() -> Any:
        cfg = sdk_adapter.Session(
            StepKind.BUILD, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path),
            observe=lambda: Worktree("a", "a"), checks=(), subagents=True, model="gpt-6-luna",
        )  # fmt: skip
        st = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001
        st.gate.call = lambda _spec, _args: (order.append("handled"), ("rejected: criteria unmet", False))[1]
        st.feed = SimpleNamespace(spotter=Seen(ctx(), lambda: "s1", judge()), watching=SimpleNamespace(slug="c1"))
        (tool,) = [t for t in st.tools() if t.name == cfg.submit.name]
        inv = ToolInvocation(session_id="s1", tool_call_id="call-3", tool_name=tool.name, arguments={"summary": "s"})
        result = await tool.handler(inv)
        await st.feed.spotter.drain()
        return result

    assert asyncio.run(main()).result_type == "failure"
    assert spotter.WORK.settled(5)
    assert order == ["look call-3 {'summary': 's'}", "handled"]
    [rec] = records()
    assert (rec["call"], rec["look"], rec["cutoff"]) == ("call-3", "hand-off", 0)
    outcomes = spotter.root() / f"outcomes-{spotter._today()}.jsonl"  # noqa: SLF001
    [outcome] = [json.loads(x) for x in outcomes.read_text().splitlines()]
    assert (outcome["call"], outcome["outcome"]) == ("call-3", "failure")


def test_the_runner_gives_the_look_its_settings_open_work_and_decisions(tmp_path, monkeypatch) -> None:
    store = Store(tmp_path / "proj")
    store.db.check()
    plan = Plan(tasks=[Task(id="t1", title="one", done=True), Task(id="t2", title="two")])
    store.write(Lock("c1"), Change(slug="c1", plan=plan))
    settings = resolve(None, Layer())
    with step_decisions.using(["## Decisions in force", "- D1: keep it"]):
        got = watched.spot(store, Lock("c1"), "build", settings, watched.needed(settings))
    assert (got.project, got.change, got.looks, got.limit, got.model, got.open_work) == (
        "proj", "c1", ("hand-off",), 0.75, settings.agents["spotter"].model, ("two",))  # fmt: skip
    assert got.decisions == ("## Decisions in force", "- D1: keep it")
    assert got.prompt == cases.snapshot(verbose=got.verbose)  # frozen once for the step's looks
    assert got.actions == dict.fromkeys(CATEGORIES, "record")  # the conftest's Global layer records every one
    unset = resolve(None, Layer(spotter=Spotter(switch="on")))
    unset.missing.append("spotter.looks")
    with pytest.raises(SettingsUnset, match=r"spotter\.looks"):
        watched.needed(unset)
    from owlbear_delivery_next.state_store import machine_settings  # noqa: PLC0415

    monkeypatch.setattr(machine_settings, "BASE", None)  # no machine setting is read: there is no daily budget
    assert watched.needed(settings) == 0.75
    no_limit = resolve(None, Layer())
    no_limit.missing.append("spotter.look_credit_limit")
    with pytest.raises(SettingsUnset, match=r"spotter\.look_credit_limit"):
        watched.needed(no_limit)  # required while the Spotter is on


def test_a_look_is_one_toolless_session_noted_in_the_chatlogs_manifest(monkeypatch) -> None:
    made: dict[str, Any] = {}

    class Session:
        session_id = "look-1"
        rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=None))

        async def send_and_wait(self, message: str, **kw: Any) -> None:
            made["message"], made["timeout"] = message, kw["timeout"]
            made["on_event"](said('{"category": "none"}'))

        async def disconnect(self) -> None:
            made["disconnected"] = True

    async def metrics() -> Any:
        return SimpleNamespace(total_nano_aiu=2e8)

    Session.rpc.usage.get_metrics = metrics

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **kw: Any) -> Session:
            made.update(kw, noted=kw["session_id"] in (chatlogs.own() or set()))  # noted before it exists
            return Session()

        async def stop(self) -> None:
            made["stopped"] = True

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    spend = meter()
    assert asyncio.run(REAL_LOOK({"step": "build"}, ctx(verbose=True), spend)) == '{"category": "none"}'
    assert (spend.report()["credits"], spend.report()["credits_known"]) == (0.2, True)
    sid = made["session_id"]
    assert made["noted"]
    assert spend.report()["sdk_sessions"] == [sid]
    assert Path(made["working_directory"]).parent == spotter.place() / "looks"  # in OwlBear's own folder: never a chat
    chosen = (
        "available_tools", "mcp_servers", "enable_config_discovery", "memory", "model", "reasoning_effort", "timeout"
    )  # fmt: skip
    assert [made[k] for k in chosen] == [[], {}, False, {"enabled": False}, "gpt-6-luna", "medium", spotter.LOOK]
    assert "session_limits" not in made  # no SDK credit cap: a look is bounded by its deadline and teardown
    assert "rationale" in made["message"]
    assert made["message"].startswith(cases.snapshot(verbose=True).text + "\n\n## The card")  # exactly the bytes hashed
    assert '{"step": "build"}' in made["message"]
    assert (made["disconnected"], made["stopped"]) == (True, True)
    assert spotter.WORK.settled(5)  # the end's line is queued, not awaited
    lines = [json.loads(x) for x in (chatlogs.root() / "manifest.jsonl").read_text().splitlines()]
    assert [(x["event"], x["session"], x.get("kind")) for x in lines] == [
        ("started", sid, "spotter"), ("ended", sid, None)]  # fmt: skip
    assert spend_ledger.WRITER.settled(5)
    start, end = spend_ledger.lines()  # the look's own spend, as read, in the spend ledger
    assert (start["session"], start["agent"], start["job"], start["model"], start["before"]) == (
        sid, "spotter", "look", "gpt-6-luna", {}
    )  # fmt: skip
    assert (end["run"], end["ending"], end["usage"]["credits"]) == (start["run"], "finished", 0.2)
    assert start["look"] == end["look"] == spend.id  # the look's record carries the same id


def test_a_look_that_cannot_be_noted_as_ours_never_creates_its_session(monkeypatch) -> None:
    created = []

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **kw: Any) -> None:
            created.append(kw)

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    monkeypatch.setattr(chatlogs, "note", lambda _event: False)  # the write fails; the manifest still reads
    with pytest.raises(RuntimeError, match="could not be noted"):
        asyncio.run(REAL_LOOK({"step": "build"}, ctx(), meter()))
    assert created == []


class Stalled:
    """A runtime whose session and stop never answer; ``force_stop`` ends it, unless it fails too."""

    def __init__(self, made: dict[str, Any], *, start_fails: bool = False, force_fails: bool = False) -> None:
        self.made, self.start_fails, self.force_fails = made, start_fails, force_fails

    async def start(self) -> None:
        if self.start_fails:
            self.begun()
            raise RuntimeError(self.made.setdefault("why", "protocol mismatch"))

    async def create_session(self, **_kw: Any) -> Any:
        return SimpleNamespace(session_id="look-2", send_and_wait=self.asked, disconnect=self.hang)

    async def asked(self, *_a: Any, **_kw: Any) -> None:
        self.begun()
        await self.hang()

    def begun(self) -> None:
        """Tell a test that waits that the look's turn began, or its start failed: what it tears down is in place."""
        if (it := self.made.get("begun")) is not None:
            it.set()

    async def hang(self, *_a: Any, **_kw: Any) -> None:
        await asyncio.sleep(30)

    async def stop(self) -> None:
        self.made["stop"] = True
        await asyncio.sleep(30)

    async def force_stop(self) -> None:
        self.made["forced"] = True
        if self.force_fails:
            raise OSError(self.made.setdefault("left", "the runtime would not die"))


ENDS = [(False, False, [False]), (False, True, [True]), (True, False, [])]  # an unconfirmed end is provisional


@pytest.mark.parametrize(("start_fails", "force_fails", "ends"), ENDS)
def test_a_stalled_or_failed_runtime_is_torn_down_within_its_bounds(
    monkeypatch, start_fails, force_fails, ends
) -> None:
    made: dict[str, Any] = {}
    monkeypatch.setattr(spotter_look, "CopilotClient", lambda **_kw: Stalled(made, start_fails=start_fails,
                                                                               force_fails=force_fails))  # fmt: skip
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    monkeypatch.setattr(spotter, "TEARDOWN", 0.05)

    async def main() -> float:
        loop = asyncio.get_running_loop()
        made["begun"] = asyncio.Event()
        look = asyncio.ensure_future(REAL_LOOK({}, ctx(), meter()))
        await asyncio.wait_for(made["begun"].wait(), 5)  # its turn waits, or its failed start is being torn down
        began = loop.time()
        for _ in range(2):  # cancelled twice while it tears down
            look.cancel()
            await asyncio.sleep(0.01)
        await asyncio.wait({look})
        return loop.time() - began

    assert asyncio.run(main()) < 1
    assert made.get("forced") is True  # the graceful stop hung
    assert spotter.WORK.settled(5)  # the end's line is queued, not awaited
    manifest = chatlogs.root() / "manifest.jsonl"
    lines = [json.loads(x) for x in manifest.read_text().splitlines()] if manifest.exists() else []
    assert [x["provisional"] for x in lines if x["event"] == "ended"] == ends  # unconfirmed when the force failed
    assert spend_ledger.WRITER.settled(5)
    spent = [(x["type"], x.get("ending"), x.get("usage")) for x in spend_ledger.lines()]
    cut = [("start", None, None), ("end", "unconfirmed", {"error": "not read"})]
    assert spent == ([] if start_fails else cut)


def test_a_drain_ends_within_its_bound_even_when_a_look_resists(monkeypatch) -> None:
    monkeypatch.setattr(spotter, "DRAIN", 0.05)
    monkeypatch.setattr(spotter, "TEARDOWN", 0.05)

    async def stubborn(_card: dict[str, Any], _ctx: spotter.Context, _spend: Any) -> str:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            await asyncio.sleep(30)  # its cleanup hangs
        return ""

    async def main() -> float:
        spot = spotter.Spotter(ctx(), lambda: "s-1", stubborn)
        spot.handed_off("c", {})
        await asyncio.sleep(0.05)
        loop = asyncio.get_running_loop()
        began = loop.time()
        await spot.drain()
        took = loop.time() - began
        for task in spot.tasks:
            task.cancel()
        return took

    assert asyncio.run(main()) < 0.5


def test_a_limit_the_meter_refuses_still_records_the_look_as_failed() -> None:
    async def main() -> None:
        spot = spotter.Spotter(ctx(limit=1e-10), lambda: "s-1", judge())  # rounds to no nano-credit at all
        spot.handed_off("c", {})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    [rec] = records()
    assert (rec["category"], rec["skipped"][:28], rec["credits_known"], rec["sdk_sessions"]) == (
        "failed", "ValueError: a credit limit i", False, [])  # fmt: skip


def test_a_card_that_fails_is_recorded_failed_and_spends_nothing(monkeypatch) -> None:
    monkeypatch.setattr(card, "build", lambda *_a: 1 / 0)

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        spot.handed_off("c", {})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert [(r["category"], r["skipped"][:17], r["credits"], r["credits_known"]) for r in records()] == [
        ("failed", "ZeroDivisionError", 0.0, True)]  # fmt: skip


def test_cut_browser_context_is_dropped_whole() -> None:
    assert events.no_browser("secret page</browser_context> after") == events.OMITTED + " after"
    assert events.no_browser("before <browser_context>secret page") == "before " + events.OMITTED
    kept = Kept()
    kept.add(asked("x" * 2000 + "<browser_context>" + "secret " * 1500 + "</browser_context> the task"))
    assert "secret" not in json.dumps(kept.snapshot())


def test_the_card_keeps_its_bound_whatever_its_shape() -> None:
    kept = Kept()
    kept.add(asked("Build it."))
    many = [f"t{i}: " + "word " * 60 for i in range(200)]
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00", "kind": "hand-off", "result": "r" * 9000},
                       {"open_work": many, "decisions": ["d" * 40000]})  # fmt: skip
    assert len(json.dumps(built, ensure_ascii=False)) <= card.BOUND
    assert built["open_work"][-1] == f"and {200 - card.KEEP_OPEN + 1} more unfinished tasks"


def test_the_task_and_plan_anchors_survive_the_rings_and_what_they_drop_is_a_gap() -> None:
    kept = Kept()
    kept.add(asked("The task."))
    for i in range(1, 6):
        kept.add(asked(f"Request {i}."))
    kept.add(said("PLAN: first this, then that."))
    for i in range(13):
        kept.add(said(f"Progress {i}."))
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00"}, {})
    assert built["intent"]["task"] == "The task."
    assert built["intent"]["later_requests"] == [f"Request {i}." for i in range(2, 6)]
    assert [(p["role"], p["text"]) for p in built["plan"]] == [
        ("first reply to the latest request", "PLAN: first this, then that."),
        ("latest message", "Progress 12."),
    ]
    assert "dropped from the intake: 2 earlier requests, 2 earlier messages" in built["gaps"]


def test_a_resumed_session_gets_its_history_without_looks_and_subagent_completions_are_never_sampled() -> None:
    async def main() -> spotter.Spotter:
        spot = spotter.Spotter(ctx(looks=("sample",), sample_rate=100), lambda: "s-1", judge())
        spot.history([asked("The original task."), said("My plan."), started("h1", "bash", {"command": "ls"}),
                      done("h1", "ok")])  # fmt: skip
        spot.seen(asked("Continue."))
        spot.seen(started("p1", "bash", {"command": "ls"}, parentToolCallId="task-1"))
        spot.seen(event("tool.execution_complete", {"toolCallId": "p1", "success": True, "parentToolCallId": "task-1",
                                                    "result": {"content": "ok"}}))  # fmt: skip
        assert not spot.tasks
        return spot

    snapshot = asyncio.run(main()).kept.snapshot()
    assert (snapshot["task"], [a["id"] for a in snapshot["actions"]]) == ("The original task.", ["h1"])


def test_a_long_task_on_an_oversized_card_still_ends_within_the_bound() -> None:
    kept = Kept()
    kept.add(asked("t" * 6000))
    for i in range(4):
        kept.add(asked(f"later {i} " + "word " * 1200))
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00", "result": "word " * 600},
                       {"open_work": ["word " * 400] * 12, "decisions": ["d " * 3000]})  # fmt: skip
    assert len(json.dumps(built, ensure_ascii=False)) <= card.BOUND
    assert all(len(events.clip("x" * 900, n)) <= n for n in (1, 7, 8, 50, 500))


def test_through_passes_on_a_cancellation_that_races_the_tasks_end() -> None:
    async def main() -> None:
        child = asyncio.get_running_loop().create_future()
        waiting = asyncio.ensure_future(spotter.through(child))
        await asyncio.sleep(0)
        child.set_result(None)
        waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting

    asyncio.run(main())


def test_a_look_cancelled_twice_before_its_card_is_built_still_records(monkeypatch) -> None:
    import time  # noqa: PLC0415

    real = card.build
    monkeypatch.setattr(card, "build", lambda *a: (time.sleep(0.2), real(*a))[1])

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        spot.handed_off("c", {})
        [task] = spot.tasks
        for _ in range(2):
            await asyncio.sleep(0.02)
            task.cancel()
        await asyncio.wait({task})

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    for _ in range(100):  # the record's write goes on after the step's loop
        if records():
            break
        time.sleep(0.02)
    assert [(r["skipped"], r["credits"], r["credits_known"]) for r in records()] == [
        ("the step ended before the look began", 0.0, True)]  # fmt: skip


def test_the_steps_loop_ends_without_waiting_for_the_spotters_writes(monkeypatch) -> None:
    import threading  # noqa: PLC0415
    import time  # noqa: PLC0415

    monkeypatch.setattr(spotter, "DRAIN", 0.02)
    monkeypatch.setattr(spotter, "TEARDOWN", 0.02)
    written = threading.Event()
    monkeypatch.setattr(spotter, "store", lambda *_a: (time.sleep(0.5), written.set()))

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        spot.handed_off("c", {})
        await spot.drain()

    began = time.monotonic()
    asyncio.run(main())  # leftovers are cancelled by asyncio.run itself
    took = time.monotonic() - began
    written.wait(5)
    assert spotter.WORK.settled(5)
    assert took < 0.3


def test_a_burst_of_samples_while_looks_run_is_counted_once_not_queued() -> None:
    async def main() -> int:
        spot = spotter.Spotter(ctx(looks=("sample",), sample_rate=100), lambda: "s-1", judge(wait=0.2))
        for i in range(300):
            spot.seen(started(f"c{i}", "bash", {"command": "ls"}))
            spot.seen(done(f"c{i}", "ok"))
        most = len(spot.tasks)
        await spot.drain()
        return most

    assert asyncio.run(main()) == 2
    assert spotter.WORK.settled(5)
    got = records()
    assert sorted(r["skipped"][:30] for r in got) == ["", "", "capacity: 298 sampled looks sk"]

    async def paused() -> None:  # a summary for another why, and one look skipped on its own
        spot = spotter.Spotter(ctx(looks=("sample",), sample_rate=100), lambda: "s-2", judge(),
                               room=lambda: "paused: the machine is paused")  # fmt: skip
        for i in range(4):
            spot.seen(started(f"p{i}", "bash", {"command": "ls"}))
            spot.seen(done(f"p{i}", "ok"))
        spot.skip("plan", 1.0, {"kind": "plan"}, "capacity: looks already running")
        await spot.drain()

    asyncio.run(paused())
    assert spotter.WORK.settled(5)
    spent = improvement_view.spotter({}, records(), datetime.now(UTC))["spend"]["p"]
    assert spent == {"looks": 2, "credits": pytest.approx(0.5), "unknown": 0, "stopped": 0, "skipped": 298 + 4 + 1}


def test_a_spotter_writes_where_it_started_whatever_changes_later(monkeypatch, tmp_path) -> None:
    async def main() -> spotter.Spotter:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        from owlbear_delivery_next.local_system import local_home  # noqa: PLC0415

        monkeypatch.setattr(local_home, "root", lambda: tmp_path / "elsewhere")
        spot.handed_off("c", {})
        await spot.drain()
        return spot

    started_in = asyncio.run(main()).folder
    assert spotter.WORK.settled(5)
    assert (started_in / f"records-{spotter._today()}.jsonl").exists()  # noqa: SLF001
    assert not (tmp_path / "elsewhere").exists()


def test_the_process_exits_within_the_grace_though_spotter_work_is_still_queued(tmp_path) -> None:
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415
    import time  # noqa: PLC0415

    script = (
        "import time\n"
        "from owlbear_delivery_next.improvement import spotter\n"
        "spotter.WORK.submit(time.sleep, 30)\n"
        "print(time.monotonic(), flush=True)\n"
    )
    proc = subprocess.run(  # noqa: S603 - this interpreter and a fixed script
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=20, cwd=tmp_path, check=True
    )
    ended = time.monotonic()
    assert ended - float(proc.stdout.strip()) < spotter.GRACE + 1.5


def test_a_hand_off_skipped_for_capacity_keeps_the_events_seen_as_its_cutoff() -> None:
    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge(wait=0.1))
        for ev in (asked("Build it."), said("Plan."), said("Done.")):
            spot.seen(ev)
        for i in range(3):
            spot.handed_off(f"c{i}", {})
        await spot.drain()

    asyncio.run(main())
    assert sorted((r["skipped"][:8], r["cutoff"]) for r in records()) == [("", 3), ("", 3), ("capacity", 3)]


def test_a_hand_off_look_waiting_for_a_slot_judges_its_own_turn_though_the_next_one_is_taken_in_meanwhile() -> None:
    release, judged, cards = asyncio.Event(), asyncio.Event(), []

    async def look(the_card: dict[str, Any], _ctx: spotter.Context, spend: credit_meter.Meter) -> str:
        cards.append(the_card)
        if the_card["moment"]["call"] == "h":
            judged.set()
        await release.wait()
        spend.part().ended(None, confirmed=True)
        return '{"category": "none"}'

    async def main() -> str:
        spot = spotter.Spotter(ctx(), lambda: "s-1", look)
        for ev in (asked("Build it."), said("Plan."), said("Done.")):
            spot.seen(ev)
        turn = spot.kept.turn
        for i in range(2):
            spot.look("plan", 1.0, {"kind": "a running look", "call": f"p{i}"})
        spot.handed_off("h", {})  # it waits: neither running look gives its slot
        for ev in (asked("Now the farewell."), said("Next plan.")):
            spot.seen(ev)
        await asyncio.sleep(0.1)
        release.set()
        await asyncio.wait_for(judged.wait(), 3)  # the slot frees and the hand-off's look begins
        await spot.drain()
        return turn

    turn = asyncio.run(main())
    assert spotter.WORK.settled(5)
    handed = cards[-1]["moment"]
    assert (handed["call"], handed["turn"], handed["cutoff"], cards[-1]["intent"]["later_requests"]) == (
        "h", turn, 3, [])  # fmt: skip
    [record] = [r for r in records() if r["call"] == "h"]
    assert (record["turn"], record["cutoff"], record["skipped"]) == (turn, 3, "")


def usage(nano: float | None, second: int = 0) -> SessionEvent:
    """One billed call as the runtime reports it; None: without its cost."""
    data: dict[str, Any] = {"model": "gpt-6-luna"}
    if nano is not None:
        data["copilotUsage"] = {"totalNanoAiu": nano, "tokenDetails": []}
    return event("assistant.usage", data, second=second)


@pytest.mark.parametrize(("calls", "known"), [([1.5e8], True), ([], False), ([None], False)])
def test_an_unread_total_keeps_the_answer_and_its_spend_is_the_calls_reported(monkeypatch, calls, known) -> None:
    made: dict[str, Any] = {}

    class Session:
        session_id = "look-3"

        async def send_and_wait(self, *_a: Any, **_kw: Any) -> None:
            for nano in calls:
                made["on_event"](usage(nano))
            made["on_event"](said('{"category": "course-and-constraints", "note": "Run the tests."}'))

        async def disconnect(self) -> None:
            pass

        @property
        def rpc(self) -> Any:
            raise ConnectionError(made.setdefault("why", "usage unread"))

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **kw: Any) -> Session:
            made.update(kw)
            return Session()

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    spend = meter()
    text = asyncio.run(REAL_LOOK({}, ctx(), spend))
    assert spotter.parse(text)["category"] == "course-and-constraints"
    reported = spend.report()
    assert (reported["credits"], reported["credits_known"]) == (0.15 if calls == [1.5e8] else 0.0, known)
    assert reported["stopped"] == ("" if known else "unknown")  # an unknown spend closes the look's meter
    assert spend_ledger.WRITER.settled(5)
    [end] = [x for x in spend_ledger.lines() if x["type"] == "end"]  # this session's own calls, a lower bound
    assert end["usage"] == (
        {"credits": 0.15, "models": {"gpt-6-luna": {"credits": 0.15}}, "incomplete": "not read"}
        if calls == [1.5e8] else {"credits": 0.0, "models": {"gpt-6-luna": {"credits": 0.0}}, "incomplete": "not read"}
        if calls else {"error": "not read"}
    )  # fmt: skip


def test_a_drain_that_stops_waiting_never_drops_queued_writes(monkeypatch) -> None:
    import threading  # noqa: PLC0415

    monkeypatch.setattr(spotter, "DRAIN", 0.02)
    monkeypatch.setattr(spotter, "TEARDOWN", 0.02)
    release = threading.Event()
    for _ in range(2):  # both of the Spotter's threads are busy
        spotter.WORK.submit(release.wait, 5)

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        spot.answered("call-7", "success")
        await spot.drain()

    asyncio.run(main())
    release.set()
    assert spotter.WORK.settled(5)
    outcomes = spotter.root() / f"outcomes-{spotter._today()}.jsonl"  # noqa: SLF001
    assert [json.loads(x)["call"] for x in outcomes.read_text().splitlines()] == ["call-7"]


def test_a_look_the_runtime_reports_as_free_costs_nothing(monkeypatch) -> None:
    made: dict[str, Any] = {}

    class Session:
        session_id = "look-4"
        rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=None))

        async def send_and_wait(self, *_a: Any, **_kw: Any) -> None:
            made["on_event"](said('{"category": "none"}'))

        async def disconnect(self) -> None:
            pass

    async def metrics() -> Any:
        return SimpleNamespace(total_nano_aiu=0)

    Session.rpc.usage.get_metrics = metrics

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **kw: Any) -> Session:
            made.update(kw)
            return Session()

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    spend = meter()
    assert asyncio.run(REAL_LOOK({}, ctx(), spend)) == '{"category": "none"}'
    assert (spend.report()["credits"], spend.report()["credits_known"]) == (0.0, True)


SHAPES = ["d", "a.", "a@", "x@y.", "<browser_context>", "</browser_context>", "<browser_context>x</browser_context>"]


@pytest.mark.parametrize("unit", SHAPES)
def test_cleaning_the_largest_text_takes_linear_time_whatever_its_shape(unit: str) -> None:
    import time  # noqa: PLC0415

    text = (unit * (events.RAW // len(unit) + 1))[: events.RAW]
    began = time.monotonic()
    events.kept_text(text, events.RESULT)
    assert time.monotonic() - began < 1  # milliseconds here; a quadratic pattern took seconds


def test_an_edit_mentioning_tests_keeps_its_change() -> None:
    kept = Kept()
    change = {"path": "/Users/x/t.py", "old_str": "def test_a():", "new_str": "@pytest.mark.skip\ndef test_a():"}
    kept.add(started("e1", "edit", change))
    kept.add(done("e1", "ok"))
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00"}, {})
    [edit] = [e for e in built["evidence"] if e["tool"] == "edit"]
    assert (edit["why"], "@pytest.mark.skip" in edit["output"]) == ("edit", True)


MALFORMED = [
    '{"category": "none", "evidence": "e1"}',
    '{"category": "course-and-constraints", "note": 3}',
    '{"category": "course-and-constraints", "evidence": ["a", 2]}',
    '{"category": "hand-off-fitness", "note": null}',
    '{"category": "irreversible-harm", "note": "  "}',
    '{"category": "hand-off-fitness"}',
    '{"category": "scope-creep", "note": "n"}',
    '{"category": null, "note": ""}',
    '{"note": "n"}',
    '{"verdict": "note", "note": "an answer in the shape before the categories"}',
    '{"verdict": "silent"}',
]


@pytest.mark.parametrize("answer", MALFORMED)
def test_an_answer_without_a_known_category_or_with_malformed_fields_is_failed(answer: str) -> None:
    assert spotter.parse(answer)["category"] == "failed"


@pytest.mark.parametrize("category", [*CATEGORIES, "none", "insufficient-context"])
def test_each_category_and_the_two_answers_without_a_finding_are_taken(category: str) -> None:
    note = "" if category in {"none", "insufficient-context"} else "n"
    answer = json.dumps({"category": category, "note": note, "evidence": ["e"], "state_change": None})
    assert spotter.parse(f"Here it is: {answer}")["category"] == category


@pytest.mark.parametrize(
    ("answer", "category", "action"),
    [
        ('{"category": "irreversible-harm", "note": "Stop: this mails real customers."}', "irreversible-harm",
         "stop-and-ask"),
        ('{"category": "course-and-constraints", "note": "The same test failed six times."}',
         "course-and-constraints", "record"),
        ('{"category": "insufficient-context"}', "insufficient-context", ""),
        ('{"category": "none"}', "none", ""),
    ],
)  # fmt: skip
def test_a_record_keeps_the_category_and_the_action_the_settings_give_it(answer, category, action) -> None:
    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge(answer))
        spot.handed_off("c", {})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert [(r["category"], r["action"]) for r in records()] == [(category, action)]


def test_the_prompt_names_every_category_and_asks_for_a_category_never_a_verdict() -> None:
    text = spotter.PROMPT.read_text()
    assert all(f"`{c}`" in text for c in CATEGORIES)
    assert '"category": "none"' in text
    assert "insufficient-context" in text
    assert "verdict" not in text
    assert not any(a in text for a in ("show-owner", "refuse-hand-off", "stop-and-ask"))  # the actions stay out


def test_answers_the_ring_drops_are_a_gap() -> None:
    kept = Kept()
    for i in range(5):
        kept.add(started(f"q{i}", "ask_user", {"question": f"Which {i}?"}))
        kept.add(done(f"q{i}", f"answer {i}"))
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00"}, {})
    assert any("2 earlier answers" in g for g in built["gaps"])


def test_an_unterminated_browser_context_crossing_the_size_cut_is_still_dropped() -> None:
    text = "a" * (events.RAW // 2 - 5) + "<browser_context>" + "secret " * 20000
    assert "secret" not in events.kept_text(text, events.RESULT)


def test_the_card_stays_within_its_bound_at_the_shortening_edge() -> None:
    snapshot = Kept().snapshot()
    for k in range(1180, 1290, 3):  # gaps the cuts never trim, around the bound
        built = card.build(snapshot, {"at": "2026-10-26T10:01:00+00:00"}, {"gaps": ["g" * 20] * k})
        assert len(json.dumps(built, ensure_ascii=False)) <= card.BOUND, k


def test_no_look_starts_once_the_drain_began_and_a_slow_write_never_holds_the_end(monkeypatch) -> None:
    import time  # noqa: PLC0415

    monkeypatch.setattr(spotter, "LOCK", 0.05)
    real = spotter.store
    monkeypatch.setattr(spotter, "store", lambda *a: (time.sleep(0.6), real(*a)))

    async def main() -> tuple[float, int]:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge(wait=0.05))
        spot.handed_off("c1", {})
        loop = asyncio.get_running_loop()
        began = loop.time()
        draining = asyncio.ensure_future(spot.drain())
        await asyncio.sleep(0)
        spot.handed_off("c2", {})  # a late hand-off after the drain began
        late = len(spot.tasks)
        await draining
        return loop.time() - began, late

    took, late = asyncio.run(main())
    assert late == 1
    assert took < 0.5  # the write goes on; the step's end does not wait for it
    assert spotter.WORK.settled(5)
    assert [r["call"] for r in records()] == ["c1"]


def test_a_cancelled_submit_handler_still_keeps_delivery_s_answer(tmp_path) -> None:
    import time  # noqa: PLC0415

    async def main() -> None:
        cfg = sdk_adapter.Session(
            StepKind.BUILD, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path),
            observe=lambda: Worktree("a", "a"), checks=(), subagents=True, model="gpt-6-luna",
        )  # fmt: skip
        st = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001
        st.gate.call = lambda _spec, _args: (time.sleep(0.3), ("accepted", True))[1]
        st.feed = SimpleNamespace(spotter=spotter.Spotter(ctx(looks=()), lambda: "s1", judge()),
                                  watching=SimpleNamespace(slug="c1"))  # fmt: skip
        (tool,) = [t for t in st.tools() if t.name == cfg.submit.name]
        handling = asyncio.ensure_future(tool.handler(ToolInvocation(tool_call_id="call-9", arguments={})))
        await asyncio.sleep(0.05)
        handling.cancel()  # the step ends while Delivery still checks the hand-off
        await asyncio.wait({handling})
        await asyncio.sleep(0.5)

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    outcomes = spotter.root() / f"outcomes-{spotter._today()}.jsonl"  # noqa: SLF001
    assert [json.loads(x)["outcome"] for x in outcomes.read_text().splitlines()] == ["success"]


def test_an_unreadable_prompt_still_records_the_look_and_its_spend(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cases, "PROMPT", tmp_path / "missing.md")

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        spot.handed_off("c", {})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert [(r["prompt"], r["credits"]) for r in records()] == [("unreadable", 0.25)]


def test_a_slow_manifest_write_never_holds_a_looks_teardown(monkeypatch) -> None:
    import threading  # noqa: PLC0415
    import time  # noqa: PLC0415

    released = threading.Event()
    real = chatlogs.note

    def note(event: dict[str, Any]) -> None:
        if event["event"] == "ended":
            released.wait(5)
        real(event)

    class Session:
        session_id = "look-5"
        rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=None))

        async def send_and_wait(self, *_a: Any, **_kw: Any) -> None:
            pass

        async def disconnect(self) -> None:
            pass

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **_kw: Any) -> Session:
            return Session()

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    monkeypatch.setattr(spotter_look.chatlogs, "note", note)
    began = time.monotonic()
    asyncio.run(REAL_LOOK({}, ctx(), meter()))
    took = time.monotonic() - began
    released.set()
    assert spotter.WORK.settled(5)
    assert took < 1


class TwoSessions:
    """A runtime whose looks open one session each, in turn; each bills one call and reports its own total."""

    def __init__(self, spends: dict[str, float]) -> None:
        self.spends, self.made, self.hear = spends, iter(spends), None
        self.ids: dict[str, str] = {}  # each spend's name: the session id the look chose and noted

    async def start(self) -> None:
        pass

    async def create_session(self, **kw: Any) -> Billed:
        self.hear, name = kw["on_event"], next(self.made)
        self.ids[name] = kw["session_id"]
        return Billed(kw["session_id"], self.spends[name], self)

    async def stop(self) -> None:
        pass


class Billed:
    """One of ``TwoSessions``' sessions."""

    def __init__(self, sid: str, spend: float, runtime: TwoSessions) -> None:
        self.session_id, self.spend, self.runtime = sid, spend, runtime
        self.rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=self.metrics))

    async def metrics(self) -> Any:
        return SimpleNamespace(total_nano_aiu=self.spend, model_metrics={})

    async def send_and_wait(self, _message: str, **_kw: Any) -> None:
        self.runtime.hear(usage(self.spend))
        self.runtime.hear(said('{"category": "none"}'))

    async def disconnect(self) -> None:
        pass


def test_a_retry_runs_two_sdk_sessions_under_one_look_each_its_own_ledger_run(monkeypatch) -> None:
    """Each invocation is its own run in the spend ledger, its own session's usage, linked to the look by its meter's
    id; the look's record lists both sessions, so reconciling imports nothing and each session counts once."""

    async def retried(the_card: dict[str, Any], given: spotter.Context, spend: credit_meter.Meter) -> str:
        await REAL_LOOK(the_card, given, spend)  # its answer was unusable: the look tries again on the same meter
        return await REAL_LOOK(the_card, given, spend)

    async def main() -> None:
        spot = spotter.Spotter(ctx(effort="", limit=5.0), lambda: "s-1", retried)
        spot.handed_off("call-1", {})
        await spot.drain()

    runtime = TwoSessions({"look-a": 1e8, "look-b": 3e8})
    monkeypatch.setattr(spotter_look, "CopilotClient", lambda **_kw: runtime)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert spend_ledger.WRITER.settled(5)
    [rec] = records()
    a, b = runtime.ids["look-a"], runtime.ids["look-b"]
    assert (rec["sdk_sessions"], rec["credits"], rec["credits_known"], rec["stopped"]) == (
        [a, b], 0.4, True, ""
    )  # fmt: skip
    lines = spend_ledger.lines()
    ends = [x for x in lines if x["type"] == "end"]
    assert [(x["session"], x["look"], x["usage"]["credits"], x["limit"]) for x in ends] == [
        (a, rec["id"], 0.1, 5.0), (b, rec["id"], 0.3, 5.0)
    ]  # fmt: skip
    assert len({x["run"] for x in ends} | {rec["id"]}) == 3  # a run id per invocation, never the look's id
    assert spend_reconcile._looks(lines, {}) == []  # noqa: SLF001 - the record adds nothing the lines lack
    pieces = spend_shares.derive(lines)
    assert sorted((p["session"], round(p["credits"], 6)) for p in pieces) == sorted([(a, 0.1), (b, 0.3)])
    kept = [x for x in lines if x["session"] == a]  # look-b's lines were lost: the record holds the rest
    imported = spend_reconcile._looks(kept, {})  # noqa: SLF001
    assert [x["sdk_sessions"] for x in imported] == [[a, b]]
    one_lost = spend_shares.derive([*kept, *imported])
    assert sorted(round(p["credits"], 6) for p in one_lost) == [0.1, 0.3]


# Acting (#717): the real Spotter, its act lines and the arms; only the judge's answers and the delivery are faked

STEERED = {"hand-off-fitness": "refuse-hand-off", "course-and-constraints": "steer",
           "outside-state-changes": "stop-and-resume", "irreversible-harm": "stop-and-ask"}  # fmt: skip


def finding(category: str) -> str:
    return json.dumps({"category": category, "note": f"About {category}.", "evidence": ["e1"]})


def answers(queue: list[str]) -> spotter.Judge:
    """A judge answering each look in turn with the next of *queue*."""

    async def look(_card: dict[str, Any], _ctx: spotter.Context, spend: credit_meter.Meter) -> str:
        spend.part().ended(None, confirmed=True)
        return queue.pop(0)

    return look


class Delivered:
    """The actuator's transport faked: every act it is given is delivered, as the runtime's log would confirm."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def __call__(self, record: spotter.Record, act: acts.Act) -> None:
        self.sent.append((act.act, act.category, act.look))
        acts.update(spotter.place(), record.id, delivery="delivered")


def test_unreadable_kept_arms_are_said_with_their_path_and_the_parser_s_whole_error() -> None:
    kept = local_home.root() / "spotter" / spotter_arms.FILE
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text("{")
    try:
        json.loads("{")
    except ValueError as exc:
        whole = f"the Spotter's arms in {kept} cannot be read: {failure(exc)}"
    with pytest.raises(ValueError, match=rf"^{re.escape(whole)}\Z"):
        spotter_arms.arm("chat:s-1", 100)
    assert kept.read_text() == "{"


def test_acting_follows_arms_the_cap_per_owner_turn_repeats_and_a_rebuilt_spotter_keeps_its_counts() -> None:
    silent, steered = spotter_arms.arm("chat:s-quiet", 0), spotter_arms.arm("chat:s-1", 100)
    deliver, queue = Delivered(), []

    def chat(session: str, arm: str) -> spotter.Spotter:
        base = ctx(project="", change="", step="chat", actions=STEERED, arm=arm, cap=2, act=deliver)
        return spotter.Spotter(base, lambda: session, answers(queue))

    async def look(spot: spotter.Spotter, kind: str, category: str) -> None:
        queue.append(finding(category))
        spot.look(kind, 1.0, {"kind": kind, "call": "c"})
        while spot.tasks:
            await asyncio.wait(set(spot.tasks))

    async def main() -> list[str]:
        quiet = chat("s-quiet", silent)
        quiet.take(asked("Fix the bug."))
        await look(quiet, "plan", "course-and-constraints")  # discretionary: recorded in the silent arm
        await look(quiet, "hand-off", "irreversible-harm")  # harm acts in both arms
        spot, owner = chat("s-1", steered), asked("Fix the bug.")
        spot.take(owner)
        await look(spot, "plan", "course-and-constraints")  # note 1
        await look(spot, "hand-off", "course-and-constraints")  # note 2: another look kind is no repeat
        spot.take(asked(acts.TOKEN.format(id="r0") + " Run the tests first."))  # OwlBear's note: no new turn
        spot.take(event("user.message", {"content": "Steer.", "source": "owlbear-spotter"}))  # an agent source
        await look(spot, "hand-off", "outside-state-changes")  # a third note: over the cap
        await look(spot, "hand-off", "hand-off-fitness")  # refusals are never capped
        await look(spot, "hand-off", "irreversible-harm")  # nor harm
        await look(spot, "plan", "course-and-constraints")  # a delivered note's finding again: the owner is asked
        await look(spot, "plan", "course-and-constraints")  # once
        again = chat("s-1", steered)  # a restart within the turn: its requester message read again from the log
        again.take(owner)
        await look(again, "plan", "outside-state-changes")  # still over the cap
        again.take(asked("Now the docs."))  # the owner's next turn
        await look(again, "plan", "outside-state-changes")
        await quiet.drain()
        await again.drain()
        return [r["id"] for r in records()]

    ids = asyncio.run(main())
    assert spotter.WORK.settled(5)
    done = acts.acts(spotter.root())
    assert [(done[i].session, done[i].act, done[i].why) for i in ids] == [
        ("s-quiet", "none", "arm"), ("s-quiet", "stop-and-ask", "setting"),
        ("s-1", "steer", "setting"), ("s-1", "steer", "setting"), ("s-1", "none", "cap"),
        ("s-1", "refuse-hand-off", "setting"), ("s-1", "stop-and-ask", "setting"), ("s-1", "ask", "repeat"),
        ("s-1", "none", "asked"), ("s-1", "none", "cap"), ("s-1", "stop-and-resume", "setting"),
    ]  # fmt: skip
    assert [a for a, _c, _l in deliver.sent] == ["stop-and-ask", "steer", "steer", "refuse-hand-off", "stop-and-ask",
                                                 "ask", "stop-and-resume"]  # fmt: skip
    assert {done[i].arm for i in ids[:2]} == {"silent"}
    assert {done[i].arm for i in ids[2:]} == {"steered"}
    assert done[ids[0]].unit == "chat:s-quiet"
    assert done[ids[0]].delivery == ""  # nothing was sent
    assert {done[i].delivery for i in ids[2:4]} == {"delivered"}


def test_an_act_is_written_before_it_is_dispatched_and_a_failed_dispatch_keeps_its_whole_error(whole_error) -> None:
    seen: list[acts.Act | None] = []

    async def dispatch(record: spotter.Record, _act: acts.Act) -> None:
        seen.append(acts.acts(spotter.root()).get(record.id))
        if len(seen) == 2:
            exc = RuntimeError(whole_error)
            exc.add_note("the runtime refused the note")
            raise exc

    async def main() -> None:
        for session in ("s-1", "s-2"):
            spot = spotter.Spotter(ctx(actions=STEERED, arm="steered", cap=2, act=dispatch), lambda s=session: s,
                                   judge(finding("hand-off-fitness")))  # fmt: skip
            spot.handed_off("call-1", {})
            await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    first, second = seen
    assert first is not None
    assert (first.act, first.delivery, first.look, first.category, first.scope) == (
        "refuse-hand-off", "pending", "hand-off", "hand-off-fitness", "build")  # fmt: skip
    assert first.token == acts.TOKEN.format(id=first.record)
    assert first.note == "About hand-off-fitness."
    failed = acts.acts(spotter.root())[second.record]
    assert (failed.delivery, failed.error) == ("failed", f"RuntimeError: {whole_error}\nthe runtime refused the note")
    assert acts.acts(spotter.root())[first.record].delivery == "pending"  # the actuator's own log confirms it


@pytest.mark.parametrize("fails", [False, True], ids=["answers", "fails"])
def test_a_state_change_finding_asks_the_conflict_check_after_acting_and_its_answer_lands_on_the_act(
    fails, whole_error
) -> None:
    order: list[str] = []

    async def dispatch(_record: spotter.Record, act: acts.Act) -> None:
        order.append(f"act {act.act}")

    def conflicts(change: str) -> str:
        order.append(f"check {change}")
        if fails:
            exc = RuntimeError(whole_error)
            exc.add_note("the decisions lookup ended early")
            raise exc
        return json.dumps({"decisions": [{"id": "D-1", "conflict": "none"}]})

    answer = json.dumps({"category": "irreversible-harm", "note": "Deletes the backups.", "evidence": ["e1"],
                         "state_change": "rm -rf ~/backups"})  # fmt: skip

    async def main() -> None:
        spot = spotter.Spotter(ctx(looks=("hand-off",), actions=STEERED, arm="silent", cap=2, act=dispatch,
                                   conflicts=conflicts), lambda: "s-1", judge(answer))  # fmt: skip
        spot.handed_off("call-1", {})
        await spot.drain()

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert order == ["act stop-and-ask", "check rm -rf ~/backups"]
    [act] = acts.acts(spotter.root()).values()
    failed = {"failed": f"RuntimeError: {whole_error}\nthe decisions lookup ended early"}
    assert json.loads(act.conflict) == (failed if fails else {"decisions": [{"id": "D-1", "conflict": "none"}]})
    assert act.harm


class Transport:
    """The SDK session below the step's actuator: nothing is sent at a hand-off; its answer is the submit's."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def send(self, prompt: str, **_kw: Any) -> str:
        self.calls.append(prompt)
        return "m-1"

    async def abort(self) -> None:
        self.calls.append("abort")


def handing_off(tmp_path: Path, spot: spotter.Spotter, transport: Transport | None = None) -> sdk_adapter._Step:
    """A real step and gate whose Spotter acts through its ``StepActor``, as the adapter binds it."""
    from owlbear_delivery_next.runtimes import spotter_act  # noqa: PLC0415 - #717's actuator, bound as the adapter does

    cfg = sdk_adapter.Session(
        StepKind.BUILD, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path),
        observe=lambda: Worktree("a" * 40, "b" * 40), checks=(), model="gpt-6-luna",
    )  # fmt: skip
    st = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001
    st.feed = SimpleNamespace(spotter=spot, watching=SimpleNamespace(slug="c1"), seen=lambda _k, ev: spot.seen(ev))
    spotter_act.bind(st, transport or Transport())
    return st


async def submitted(st: sdk_adapter._Step, call: str) -> Any:
    (tool,) = [t for t in st.tools() if t.name == st.cfg.submit.name]
    payload = {"summary": "Added the farewell", "checks": []}
    result = await tool.handler(ToolInvocation(session_id="s1", tool_call_id=call, tool_name=tool.name,
                                               arguments=payload))  # fmt: skip
    st.on_event(done(call, result.text_result_for_llm, ok=result.result_type == "success"))  # the runtime logs it
    return result


def test_a_hand_off_waits_for_its_look_whose_steer_or_refusal_answers_it_and_the_next_one_is_looked_at_again(
    tmp_path,
) -> None:
    queue = [finding("hand-off-fitness"), finding("course-and-constraints"), '{"category": "none"}']
    release = asyncio.Event()

    async def held(the_card: dict[str, Any], c: spotter.Context, spend: credit_meter.Meter) -> str:
        await release.wait()
        return await answers(queue)(the_card, c, spend)

    async def main() -> tuple[sdk_adapter._Step, list[Any]]:
        spot = spotter.Spotter(ctx(actions=STEERED, arm="steered", cap=2), lambda: "s1", held)
        st = handing_off(tmp_path, spot)
        first = asyncio.ensure_future(submitted(st, "call-1"))
        await asyncio.sleep(0.1)
        waited = not first.done()  # the hand-off is held while its look runs
        release.set()
        said = [waited, await first]
        said += [await submitted(st, "call-2"), await submitted(st, "call-3")]
        await spot.drain()
        return st, said

    st, (waited, refused, steered, accepted) = asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert waited
    assert [(r.result_type, r.text_result_for_llm.split("] ", 1)[1]) for r in (refused, steered)] == [
        ("failure", "About hand-off-fitness."), ("failure", "About course-and-constraints.")]  # fmt: skip
    assert (accepted.result_type, st.run.ending, st.run.invalid) == ("success", "result", 0)
    assert st.run.tool_calls[st.cfg.submit.name] == {"calls": 3, "spotter": 2}  # never rejected
    done_ = acts.acts(spotter.root())
    by_call = {r["call"]: done_[r["id"]] for r in records() if r["id"] in done_}
    assert [(by_call[c].act, by_call[c].delivery) for c in ("call-1", "call-2")] == [
        ("refuse-hand-off", "delivered"), ("steer", "delivered")]  # fmt: skip
    assert "call-3" not in by_call  # a silent look acts on nothing
    assert st.actor.session.calls == []  # a hand-off's note is the submit's answer, never a message


def test_a_hand_off_waits_for_a_look_that_could_stop_to_ask_and_the_step_ends_with_its_question(tmp_path) -> None:
    """Any category acting at a hand-off holds the submit: here course and constraints asks, in the silent arm."""
    asking = {"hand-off-fitness": "record", "course-and-constraints": "stop-and-ask",
              "outside-state-changes": "show-owner", "irreversible-harm": "record"}  # fmt: skip
    release = asyncio.Event()

    async def held(the_card: dict[str, Any], c: spotter.Context, spend: credit_meter.Meter) -> str:
        await release.wait()
        return await answers([finding("course-and-constraints")])(the_card, c, spend)

    async def main() -> tuple[sdk_adapter._Step, Any]:
        spot = spotter.Spotter(ctx(actions=asking, arm="silent", cap=2), lambda: "s1", held)
        st = handing_off(tmp_path, spot)
        first = asyncio.ensure_future(submitted(st, "call-1"))
        await asyncio.sleep(0.1)  # past the moment an unheld submission is accepted
        release.set()
        result = await first
        await spot.drain()
        return st, result

    st, result = asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert result.result_type != "success"
    assert st.run.ending == "spotter-ask"
    assert st.run.detail == "The Spotter stopped this step: About course-and-constraints."


def test_a_stop_to_ask_at_a_hand_off_whose_abort_outlasts_the_submits_wait_still_ends_the_step_with_its_question(
    tmp_path, monkeypatch
) -> None:
    from owlbear_delivery_next.runtimes import spotter_act, step_tools  # noqa: PLC0415 - #717's actuator and submit

    monkeypatch.setattr(step_tools, "wait", lambda: 0.1)
    monkeypatch.setattr(spotter_act, "CALL", 0.5)  # the abort answers only after the submit stopped waiting
    asking = dict.fromkeys(CATEGORIES, "record") | {"course-and-constraints": "stop-and-ask"}

    class Held(Transport):
        async def abort(self) -> None:
            await super().abort()
            await asyncio.Event().wait()

    async def main() -> tuple[sdk_adapter._Step, Any]:
        spot = spotter.Spotter(ctx(actions=asking, arm="silent", cap=2), lambda: "s1",
                               answers([finding("course-and-constraints")]))  # fmt: skip
        st = handing_off(tmp_path, spot, Held())
        result = await submitted(st, "call-1")
        await spot.drain()
        return st, result

    st, result = asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert (result.result_type, st.run.ending, st.done) == ("rejected", "spotter-ask", True)
    assert st.run.detail == "The Spotter stopped this step: About course-and-constraints."
    [act] = acts.acts(spotter.root()).values()
    assert (act.act, act.delivery) == ("stop-and-ask", "failed")


def test_a_hand_off_whose_look_times_out_is_accepted_and_its_act_says_why(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(spotter, "LOOK", 0.05)

    async def main() -> Any:
        spot = spotter.Spotter(ctx(actions=STEERED, arm="steered", cap=2), lambda: "s1", judge(wait=5))
        st = handing_off(tmp_path, spot)
        result = await submitted(st, "call-1")
        await spot.drain()
        return result

    assert asyncio.run(main()).result_type == "success"
    assert spotter.WORK.settled(5)
    [act] = acts.acts(spotter.root()).values()
    assert (act.act, act.why) == ("none", "the hand-off was accepted: time: the look took over 0 seconds")


def test_a_hand_off_whose_look_hits_its_credit_limit_is_accepted_and_its_act_says_why(tmp_path) -> None:
    async def main() -> Any:
        spot = spotter.Spotter(ctx(actions=STEERED, arm="steered", cap=2), lambda: "s1", judge("", cost=0.9))
        st = handing_off(tmp_path, spot)
        result = await submitted(st, "call-1")
        await spot.drain()
        return result

    assert asyncio.run(main()).result_type == "success"
    assert spotter.WORK.settled(5)
    [act] = acts.acts(spotter.root()).values()
    assert (act.act, act.why) == ("none", "the hand-off was accepted: credit limit: reached (look) before an answer")


@pytest.mark.parametrize("busy", [False, True], ids=["answered", "busy"])
def test_a_state_change_is_checked_by_the_steps_own_lookup_through_the_runners_context(tmp_path, monkeypatch, busy):
    """#717: the runner's ``watched.spot`` context asks its step's ``lookup.Asked``; only the picker is faked."""
    store = Store(tmp_path / "proj")
    store.db.check()
    store.write(Lock("c1"), Change(slug="c1"))
    picked = {"decisions": [{"id": "D-1", "title": "No force-push", "note": "It governs this push."}]}
    ran, logged, questions = object(), [], []

    def worker(_store: Store, _lock: Lock, _change: Any, question: str) -> tuple[dict[str, Any], Any]:
        questions.append(question)
        return picked, ran

    monkeypatch.setattr(lookup, "worker", worker)
    monkeypatch.setattr(
        lookup.sessions, "logged", lambda _s, _l, change, done, fields: logged.append((change, done, fields))
    )
    asked = lookup.Asked(store, Lock("c1"), lambda: "the held Change")
    settings = resolve(None, Layer())
    got = watched.spot(store, Lock("c1"), "build", settings, watched.needed(settings), asked)
    assert got.arm == spotter_arms.arm("chg:proj/c1", 100) == "silent"  # drawn at the conftest's share 0, kept

    async def dispatch(_record: spotter.Record, _act: acts.Act) -> None:
        raise AssertionError  # every category records: nothing is sent

    answer = json.dumps({"category": "outside-state-changes", "note": "Pushed to main.", "evidence": ["e1"],
                         "state_change": "git push origin main"})  # fmt: skip

    async def main() -> None:
        spot = spotter.Spotter(dataclasses.replace(got, act=dispatch), lambda: "s1", judge(answer))
        asked.admitted = int(busy)  # the worker's own lookup is running
        spot.handed_off("call-1", {})
        await spot.drain()
        asked.admitted = 0

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    asked.settled(lambda: None)  # the step settles: the lookup's run is counted on the Change the runner holds
    [act] = acts.acts(spotter.root()).values()
    [record] = retro_units.records()
    if busy:
        assert (json.loads(act.conflict), questions, logged) == ({"failed": lookup.BUSY}, [], [])
    else:
        assert json.loads(act.conflict) == picked
        assert "git push origin main" in questions[0]
        assert logged == [("the held Change", ran, {"kind": lookup.LABEL, "exit": "ok"})]
    assert retro_units.grade(record, "rev", "useful")["preliminary"] is busy


def test_a_hand_off_look_at_full_capacity_takes_a_state_change_looks_slot_and_holds_the_submit() -> None:
    deliver = Delivered()

    async def look(the_card: dict[str, Any], _ctx: spotter.Context, spend: credit_meter.Meter) -> str:
        changing = the_card["moment"]["kind"] == "a state change"
        await asyncio.sleep(1 if changing else 0.05)  # the state changes' looks still run when the hand-off comes
        spend.part().ended(None, confirmed=True)
        return '{"category": "none"}' if changing else finding("irreversible-harm")

    async def main() -> tuple[str | None, list[tuple[str, str, str]]]:
        spot = spotter.Spotter(ctx(looks=("hand-off", "state-change"), act=deliver), lambda: "s-1", look)
        for i in range(2):
            spot.look("state-change", 1.0, {"kind": "a state change", "call": f"w{i}"})
        await asyncio.sleep(0.05)
        held = spot.handed_off("h", {"summary": "done"}, held=acts.could_act(spot.ctx))
        assert held is not None
        note = await asyncio.wait_for(held, 3)
        sent = list(deliver.sent)  # what the hand-off's look did before the submit went on
        await spot.drain()
        return note, sent

    note, sent = asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert (note, sent) == (None, [("stop-and-ask", "irreversible-harm", "hand-off")])
    got = sorted((r["look"], r["skipped"]) for r in records())
    assert got[0] == ("hand-off", "")
    assert got.count(("state-change", spotter.GAVE)) == 1


def test_a_submit_waits_for_a_hand_off_look_that_first_waited_for_a_slot_and_takes_its_refusal(
    tmp_path, monkeypatch
) -> None:
    """One budget holds the submit: the look's wait for a slot, its answer and a teardown stage (#919)."""
    monkeypatch.setattr(spotter, "LOOK", 0.5)
    monkeypatch.setattr(spotter, "TEARDOWN", 0.05)
    ready, release, judged = asyncio.Barrier(3), asyncio.Event(), asyncio.Event()
    budgets: list[float] = []
    real_wait = step_tools.wait

    def wait() -> float:
        seconds = real_wait()
        budgets.append(seconds)
        return seconds

    monkeypatch.setattr(step_tools, "wait", wait)

    async def look(the_card: dict[str, Any], _ctx: spotter.Context, spend: credit_meter.Meter) -> str:
        if the_card["moment"]["call"] == "call-1":
            judged.set()
        else:
            await ready.wait()
            await release.wait()
        spend.part().ended(None, confirmed=True)
        return finding("hand-off-fitness") if the_card["moment"]["call"] == "call-1" else '{"category": "none"}'

    async def main() -> Any:
        spot = spotter.Spotter(ctx(actions=STEERED, arm="steered", cap=2), lambda: "s1", look)
        st = handing_off(tmp_path, spot)
        for i in range(2):
            spot.look("plan", 1.0, {"kind": "a running look", "call": f"p{i}"})  # neither gives its slot
        await ready.wait()
        submitting = asyncio.create_task(submitted(st, "call-1"))
        await asyncio.sleep(0)
        assert not submitting.done()
        assert not judged.is_set()
        release.set()
        result = await submitting
        await spot.drain()
        return result

    result = asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert budgets == [pytest.approx(2 * spotter.LOOK + spotter.TEARDOWN)]
    assert (result.result_type, result.text_result_for_llm.endswith("] About hand-off-fitness.")) == ("failure", True)


class _Round:
    """#925: a judges round's real ``lookup.Asked`` with the picker faked below it, and a judge whose Spotter finds a
    state change. The fake picker waits until the round settles, so its answer lands after the judge has returned."""

    PUSH = json.dumps({"category": "outside-state-changes", "note": "Pushed to main.", "evidence": ["e1"],
                       "state_change": "git push origin main"})  # fmt: skip
    USAGE: ClassVar[dict[str, Any]] = {"credits": 6.0, "models": {"gpt-6.1-sol": {"credits": 6.0, "tokens": 900}}}

    def __init__(self, monkeypatch: pytest.MonkeyPatch, said: dict[str, Any], judged: Run) -> None:
        self.owners: list[lookup.Asked] = []
        self.entered, self.seen = threading.Event(), []
        self.said, self.judged = said, judged
        owners = self.owners

        class Recorded(lookup.Asked):
            def __init__(self, *a: Any) -> None:
                super().__init__(*a)
                owners.append(self)

        monkeypatch.setattr(lookup, "Asked", Recorded)
        monkeypatch.setattr(lookup, "worker", self.worker)
        monkeypatch.setattr(sessions.sdk_adapter, "run", self.run)
        monkeypatch.setattr(spotter, "DRAIN", 0.2)

    def worker(self, _store: Store, _lock: Lock, _c: Change, question: str) -> tuple[dict[str, Any], Run]:
        self.seen.append((question, spend_ledger.where(), threading.current_thread().name))
        self.entered.set()
        deadline = time.monotonic() + 5
        while self.owners[0].open and time.monotonic() < deadline:  # admitted; answers once the round settles
            time.sleep(0.01)
        done = Termination(confirmed=True)
        return self.said, Run("c1-decision-lookup-1", "result", usage=self.USAGE, termination=done)

    async def run(self, cfg: sdk_adapter.Session) -> Run:
        assert all(spec.name != pick_tools.LOOKUP.name for spec, _ in cfg.helpers)  # a judge gets no lookup tool

        async def recorded(_record: spotter.Record, _act: acts.Act) -> None:
            raise AssertionError  # every category records: nothing is sent

        ctx = dataclasses.replace(cfg.watch.spot, act=recorded)
        spot = spotter.Spotter(ctx, lambda: cfg.session_id, judge(self.PUSH))
        spot.handed_off("call-1", {})
        assert await asyncio.to_thread(self.entered.wait, 5), "the judge's state change got no decision-conflict check"
        await spot.drain()
        return dataclasses.replace(self.judged, session_id=cfg.session_id)

    def finding(self) -> tuple[acts.Act, dict[str, Any]]:
        assert acts.CHECKS.settled(5)  # the round's settlement precedes the act's answer
        assert spotter.WORK.settled(5)
        [act] = acts.acts(spotter.root()).values()
        [record] = [r for r in retro_units.records() if r.get("state_change")]
        return act, record


def _judged(store: Store) -> tuple[Change, Callable[[Path], sdk_adapter.Session], Where]:
    change = Change(slug="c1", brief=Brief(version=1), step=Step(kind=StepKind.PLAN))
    store.write(Lock("c1"), change)

    def made(at: Path) -> sdk_adapter.Session:
        return sdk_adapter.Session(
            kind=StepKind.REVIEW, worktree=at, session_id="", message="challenge the plan", resume=False,
            policy=Policy(at, write=False), observe=Worktree, checks=(),
        )  # fmt: skip

    return change, made, spend_ledger.Where.of(store, change="c1", step="plan")


def test_a_judges_state_change_is_checked_by_its_rounds_lookup_and_counted_beside_an_unread_gate(
    tmp_path, change_repo, monkeypatch
):
    store = Store(tmp_path / "store")
    change, made, place = _judged(store)
    picked = {"decisions": [{"id": "D-1", "title": "No force-push"}]}
    unread = Run("", "result", ReviewResult(verdict="pass"), usage_unread="the usage could not be read (RuntimeError)",
                 termination=Termination(confirmed=True))  # fmt: skip
    fake = _Round(monkeypatch, picked, unread)

    def start(keep: sessions.Keep) -> pending_child.Judged:
        return sessions.review_run(store, Lock("c1"), change, change_repo, made, "plan-challenge", keep=keep)

    with spend_ledger.at(place), pytest.raises(sessions.UsageUnreadError):
        pending_child.child(store, Lock("c1"), change, ("plan-challenge", "1"), start)

    act, record = fake.finding()
    assert json.loads(act.conflict) == picked
    assert retro_units.grade(record, "rev", "useful")["preliminary"] is False
    [(question, where, thread)] = fake.seen
    assert "git push origin main" in question
    assert (where, thread.startswith("spotter-")) == (place, True)  # the Change's place, on the Spotter's thread
    looked = [e for e in store.events("c1") if e.get("kind") == lookup.LABEL]
    assert [e["exit"] for e in looked] == ["ok"]
    c = store.read("c1")
    assert [o.id for o in loop.open_question(c).options] == ["retry"]  # the judge's own unread gate stays
    assert [s.split("-", 2)[:2] for s in c.spend.unread] == [["c1", "plan"]]
    assert c.spend.credits == pytest.approx(6.0)  # the picker's, counted with the gate


def test_a_judges_failed_conflict_lookup_stays_a_recorded_failure_and_its_spend_counts(
    tmp_path, change_repo, monkeypatch
):
    store = Store(tmp_path / "store")
    change, made, place = _judged(store)
    failed = {"failed": "its session ended error: the model call failed"}
    known = Run("", "result", ReviewResult(verdict="pass"), usage={"credits": 2.0, "models": {"m": {"credits": 2.0}}},
                termination=Termination(confirmed=True))  # fmt: skip
    fake = _Round(monkeypatch, failed, known)

    with spend_ledger.at(place):
        sessions.review_run(store, Lock("c1"), change, change_repo, made, "plan-challenge")

    act, record = fake.finding()
    assert json.loads(act.conflict) == failed  # never an empty answer
    assert retro_units.grade(record, "rev", "useful")["preliminary"] is True
    events_ = store.events("c1")
    assert [e["reason"] for e in events_ if e.get("event") == "lookup-failed"] == [failed["failed"]]
    assert [e["exit"] for e in events_ if e.get("kind") == lookup.LABEL] == ["failed"]
    assert store.read("c1").spend.credits == pytest.approx(2.0 + 6.0)  # the judge's and the failed picker's
