"""The Spotter (Improvement design §4): intake, card, looks, records with category and action, limits, the hook."""

from __future__ import annotations

import asyncio
import dataclasses
import gzip
import json
import random
import stat
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from copilot.generated.session_events import SessionEvent
from copilot.tools import ToolInvocation

from owlbear_delivery_next.change_contracts.models import Change, Plan, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.improvement import card, credit_meter, events, spotter
from owlbear_delivery_next.improvement.events import Kept
from owlbear_delivery_next.runtimes import chatlogs, sdk_adapter, spotter_look, step_decisions
from owlbear_delivery_next.settings.config import Layer, SettingsUnset, resolve
from owlbear_delivery_next.settings.improvement import CATEGORIES, Spotter
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import watched

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
    assert (rec["prompt"], rec["credits"], rec["credits_known"], rec["limit"]) == (spotter.prompt_version(), 0.25,
                                                                                   True, 0.75)  # fmt: skip
    assert (rec["stopped"], rec["stopped_by"]) == ("", "")
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


def test_looks_past_capacity_are_recorded_skipped_and_a_look_stopped_at_its_limit_says_so() -> None:
    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge(wait=0.1))
        for i in range(3):  # two run; the third finds no room
            spot.handed_off(f"c{i}", {})
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
        def handed_off(self, call_id: str, arguments: Any) -> None:
            order.append(f"look {call_id} {arguments}")
            super().handed_off(call_id, arguments)

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
            made.update(kw)
            return Session()

        async def stop(self) -> None:
            made["stopped"] = True

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    spend = meter()
    assert asyncio.run(REAL_LOOK({"step": "build"}, ctx(verbose=True), spend)) == '{"category": "none"}'
    assert (spend.report()["credits"], spend.report()["credits_known"]) == (0.2, True)
    chosen = ("available_tools", "mcp_servers", "enable_config_discovery", "model", "reasoning_effort", "timeout")
    assert [made[k] for k in chosen] == [[], {}, False, "gpt-6-luna", "medium", spotter.LOOK]
    assert "session_limits" not in made  # no SDK credit cap: a look is bounded by its deadline and teardown
    assert "rationale" in made["message"]
    assert '{"step": "build"}' in made["message"]
    assert (made["disconnected"], made["stopped"]) == (True, True)
    assert spotter.WORK.settled(5)  # the end's line is queued, not awaited
    lines = [json.loads(x) for x in (chatlogs.root() / "manifest.jsonl").read_text().splitlines()]
    assert [(x["event"], x["session"], x.get("kind")) for x in lines] == [
        ("started", "look-1", "spotter"), ("ended", "look-1", None)]  # fmt: skip


class Stalled:
    """A runtime whose session and stop never answer; ``force_stop`` ends it, unless it fails too."""

    def __init__(self, made: dict[str, Any], *, start_fails: bool = False, force_fails: bool = False) -> None:
        self.made, self.start_fails, self.force_fails = made, start_fails, force_fails

    async def start(self) -> None:
        if self.start_fails:
            raise RuntimeError(self.made.setdefault("why", "protocol mismatch"))

    async def create_session(self, **_kw: Any) -> Any:
        return SimpleNamespace(session_id="look-2", send_and_wait=self.hang, disconnect=self.hang)

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
        began = loop.time()
        look = asyncio.ensure_future(REAL_LOOK({}, ctx(), meter()))
        await asyncio.sleep(0.05)
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
    monkeypatch.setattr(spotter, "PROMPT", tmp_path / "missing.md")

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
