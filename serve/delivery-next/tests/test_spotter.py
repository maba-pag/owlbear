"""The Spotter in learning mode (Improvement design §4): intake, card, looks, records, limits and the hand-off hook."""

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
from owlbear_delivery_next.improvement import card, events, spotter
from owlbear_delivery_next.improvement.events import Kept
from owlbear_delivery_next.runtimes import chatlogs, sdk_adapter, spotter_look, step_decisions
from owlbear_delivery_next.settings.config import Layer, SettingsUnset, resolve
from owlbear_delivery_next.settings.improvement import Spotter
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


def ctx(**kw: Any) -> spotter.Context:
    base = spotter.Context(project="p", change="c1", step="build", looks=("hand-off",), sample_rate=0, verbose=False,
                           model="gpt-6-luna", effort="medium", budget=50)  # fmt: skip
    return dataclasses.replace(base, **kw)


def records() -> list[dict[str, Any]]:
    return [json.loads(x) for f in sorted(spotter.root().glob("records-*.jsonl")) for x in f.read_text().splitlines()]


def ledger() -> dict[str, Any]:
    return json.loads((spotter.root() / f"ledger-{spotter._today()}.json").read_text())  # noqa: SLF001


def judge(answer: str = '{"verdict": "silent"}', *, wait: float = 0.0, seen: list | None = None) -> spotter.Judge:
    async def look(the_card: dict[str, Any], _ctx: spotter.Context) -> tuple[str, float]:
        if seen is not None:
            seen.append(the_card)
        await asyncio.sleep(wait)
        return answer, 0.25

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


def test_the_card_is_redacted_and_bounded() -> None:
    kept = Kept()
    kept.add(asked("Use token=ghp_" + "a" * 36 + " and mail owner@example.com. " + "x" * 9000))
    for i in range(60):
        kept.add(started(f"c{i}", "bash", {"command": f"uv run pytest -k t{i} " + "y" * 3000}, second=i))
        kept.add(done(f"c{i}", "z" * 5000, ok=False, second=i))
    built = card.build(kept.snapshot(), {"at": "2026-10-26T10:01:00+00:00"}, {"decisions": ["d" * 20000]})
    text = json.dumps(built, ensure_ascii=False)
    assert "ghp_" + "a" * 36 not in text
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

    assert asyncio.run(main()) < 0.05
    [rec] = records()
    assert (rec["look"], rec["verdict"], rec["session"], rec["mode"], rec["skipped"]) == (
        "hand-off", "silent", "s-1", "learning", "")  # fmt: skip
    assert (rec["prompt"], rec["credits"]) == (spotter.prompt_version(), 0.25)
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
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge(wait=5))
        spot.handed_off("call-1", {})
        await spot.drain()
        assert not spot.tasks

    asyncio.run(main())
    assert [(r["skipped"], r["credits"]) for r in records()] == [("the step ended while the look ran", 0.5)]
    assert ledger() == {"reserved": {}, "spent": 0.5}  # an unknown spend counts as the look's credit limit


def test_a_look_past_its_time_is_skipped_and_a_wrong_answer_fails_never_silent(monkeypatch) -> None:
    monkeypatch.setattr(spotter, "LOOK", 0.05)

    async def main() -> None:
        for answer, wait in (('{"verdict": "silent"}', 1.0), ("I think it is fine.", 0.0)):
            spot = spotter.Spotter(ctx(), lambda: "s-1", judge(answer, wait=wait))
            spot.handed_off("c", {})
            await asyncio.gather(*spot.tasks)

    asyncio.run(main())
    assert [(r["verdict"], r["skipped"][:4]) for r in records()] == [("", "time"), ("failed", "")]


def test_looks_past_capacity_or_budget_are_recorded_skipped_and_the_ledger_settles() -> None:
    async def main() -> None:
        spot = spotter.Spotter(ctx(budget=1), lambda: "s-1", judge(wait=0.1))
        for i in range(3):  # two run; the third finds no room
            spot.handed_off(f"c{i}", {})
        await spot.drain()
        spot.handed_off("c3", {})  # 0.5 spent and 0.5 reserved: within the budget
        await spot.drain()
        spot.handed_off("c4", {})  # now 0.75 spent: another estimate passes the budget
        await spot.drain()

    asyncio.run(main())
    assert sorted(r["skipped"].split(":")[0] for r in records()) == ["", "", "", "budget", "capacity"]
    assert ledger() == {"reserved": {}, "spent": 0.75}


def test_samples_follow_the_seeded_rate_and_a_state_change_is_preliminary() -> None:
    answer = '{"verdict": "note", "note": "Run the tests.", "evidence": ["e1"], "state_change": "pushes the branch"}'

    async def main() -> int:
        seeded = random.Random(7)  # noqa: S311
        spot = spotter.Spotter(ctx(looks=("sample",), sample_rate=30), lambda: "s-1", judge(answer), seeded)
        for i in range(20):
            spot.seen(started(f"c{i}", "bash", {"command": "ls"}))
            spot.seen(done(f"c{i}", "ok"))
            await asyncio.sleep(0.01)  # each look ends before the next action
        await spot.drain()
        rng = random.Random(7)  # noqa: S311
        return sum(rng.random() * 100 < 30 for _ in range(20))

    expected = asyncio.run(main())
    got = records()
    assert 0 < len(got) == expected
    assert {(r["look"], r["probability"], r["preliminary"], r["verdict"], r["skipped"]) for r in got} == {
        ("sample", 0.3, True, "note", "")}  # fmt: skip


def test_live_mode_still_only_records_and_a_hand_off_is_not_looked_at_unless_chosen() -> None:
    async def main() -> None:
        spotter.Spotter(ctx(mode="live"), lambda: "s-1", judge()).handed_off("c", {})
        await asyncio.sleep(0.05)
        quiet = spotter.Spotter(ctx(looks=("sample",)), lambda: "s-1", judge())
        quiet.handed_off("c", {})
        assert not quiet.tasks

    asyncio.run(main())
    assert [r["mode"] for r in records()] == ["live"]


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
        got = watched.spot(store, Lock("c1"), "build", settings)
    assert (got.project, got.change, got.looks, got.budget, got.model, got.open_work) == (
        "proj", "c1", ("hand-off",), 50, settings.agents["spotter"].model, ("two",))  # fmt: skip
    assert got.decisions == ("## Decisions in force", "- D1: keep it")
    unset = resolve(None, Layer(spotter=Spotter(mode="learning")))
    unset.missing.append("spotter.looks")
    with pytest.raises(SettingsUnset, match=r"spotter\.looks"):
        watched.spot(store, Lock("c1"), "build", unset)
    from owlbear_delivery_next.state_store import machine_settings  # noqa: PLC0415

    monkeypatch.setattr(machine_settings, "BASE", None)
    with pytest.raises(SettingsUnset, match="spotter_budget"):
        watched.spot(store, Lock("c1"), "build", settings)


def test_a_look_is_one_toolless_session_noted_in_the_chatlogs_manifest(monkeypatch) -> None:
    made: dict[str, Any] = {}

    class Session:
        session_id = "look-1"
        rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=None))

        async def send_and_wait(self, message: str, **kw: Any) -> None:
            made["message"], made["timeout"] = message, kw["timeout"]
            made["on_event"](said('{"verdict": "silent"}'))

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
    assert asyncio.run(REAL_LOOK({"step": "build"}, ctx(verbose=True))) == ('{"verdict": "silent"}', 0.2)
    chosen = ("available_tools", "mcp_servers", "enable_config_discovery", "model", "reasoning_effort", "timeout")
    assert [made[k] for k in chosen] == [[], {}, False, "gpt-6-luna", "medium", spotter.LOOK]
    assert "rationale" in made["message"]
    assert '{"step": "build"}' in made["message"]
    assert (made["disconnected"], made["stopped"]) == (True, True)
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
        look = asyncio.ensure_future(REAL_LOOK({}, ctx()))
        await asyncio.sleep(0.05)
        for _ in range(2):  # cancelled twice while it tears down
            look.cancel()
            await asyncio.sleep(0.01)
        await asyncio.wait({look})
        return loop.time() - began

    assert asyncio.run(main()) < 1
    assert made.get("forced") is True  # the graceful stop hung
    manifest = chatlogs.root() / "manifest.jsonl"
    lines = [json.loads(x) for x in manifest.read_text().splitlines()] if manifest.exists() else []
    assert [x["provisional"] for x in lines if x["event"] == "ended"] == ends  # unconfirmed when the force failed


def test_a_drain_ends_within_its_bound_even_when_a_look_resists(monkeypatch) -> None:
    monkeypatch.setattr(spotter, "DRAIN", 0.05)
    monkeypatch.setattr(spotter, "TEARDOWN", 0.05)

    async def stubborn(_card: dict[str, Any], _ctx: spotter.Context) -> tuple[str, float]:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            await asyncio.sleep(30)  # its cleanup hangs
        return "", 0.0

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


def test_a_held_ledger_never_stalls_the_steps_loop() -> None:
    import threading  # noqa: PLC0415

    held, release = threading.Event(), threading.Event()

    def hold() -> None:
        with spotter._locked(spotter.root() / "ledger.lock"):  # noqa: SLF001 - another process's long write
            held.set()
            release.wait(5)

    holder = threading.Thread(target=hold)
    holder.start()
    held.wait(5)

    async def main() -> tuple[float, int]:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        loop = asyncio.get_running_loop()
        began = loop.time()
        spot.handed_off("c", {})
        returned, ticks = loop.time() - began, 0
        while loop.time() - began < 0.3:
            await asyncio.sleep(0.01)
            ticks += 1
        release.set()
        await spot.drain()
        return returned, ticks

    returned, ticks = asyncio.run(main())
    holder.join()
    assert returned < 0.02
    assert ticks >= 15  # the loop went on while the look waited for the ledger
    assert [r["verdict"] for r in records()] == ["silent"]


def test_a_card_that_fails_settles_its_reservation_and_is_recorded_failed(monkeypatch) -> None:
    monkeypatch.setattr(card, "build", lambda *_a: 1 / 0)

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        spot.handed_off("c", {})
        await spot.drain()

    asyncio.run(main())
    assert [(r["verdict"], r["skipped"][:17], r["credits"]) for r in records()] == [
        ("failed", "ZeroDivisionError", 0.0)]  # fmt: skip
    assert ledger() == {"reserved": {}, "spent": 0.0}


def test_a_reservation_settles_on_its_own_day_and_an_unreadable_ledger_skips(monkeypatch) -> None:
    monkeypatch.setattr(spotter, "_today", lambda: "2026-10-26")
    token = spotter.reserve(spotter.root(), 10)
    monkeypatch.setattr(spotter, "_today", lambda: "2026-10-27")
    spotter.settle(spotter.root(), token, 0.2)
    assert json.loads((spotter.root() / "ledger-2026-10-26.json").read_text()) == {"reserved": {}, "spent": 0.2}
    assert not (spotter.root() / "ledger-2026-10-27.json").exists()
    (spotter.root() / "ledger-2026-10-27.json").write_text('{"reserved": ')

    async def main() -> None:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        spot.handed_off("c", {})
        await spot.drain()

    asyncio.run(main())
    assert [r["skipped"][:26] for r in records()] == ["budget: the ledger failed:"]


def test_no_rule_spares_a_credential_inside_a_path_and_cut_browser_context_is_dropped() -> None:
    token = "ghp_" + "a" * 36
    assert token not in card.clean(f"cat /tmp/{token}/x")
    assert "/Users/x/" + "b" * 40 + "/f.py" in card.clean("see: /Users/x/" + "b" * 40 + "/f.py")
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


def test_a_credential_is_cleaned_before_a_clip_could_cut_it_from_its_label() -> None:
    secret = "Q1w2E3r4" * 8
    kept = Kept()
    kept.add(asked("a" * 5000 + " password=" + secret + " " + "b" * (events.TEXT // 2 - 80)))
    assert "Q1w2E3r4" not in json.dumps(kept.snapshot())


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


def test_a_look_cancelled_twice_while_reserving_still_settles_and_records(monkeypatch) -> None:
    import time  # noqa: PLC0415

    real = spotter.reserve
    monkeypatch.setattr(spotter, "reserve", lambda *a: (time.sleep(0.2), real(*a))[1])

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
    for _ in range(100):  # the finishing work goes on after the step's loop
        if records():
            break
        time.sleep(0.02)
    assert [r["skipped"] for r in records()] == ["the step ended before the look began"]
    assert ledger() == {"reserved": {}, "spent": 0.0}


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
    got = records()
    assert sorted(r["skipped"][:30] for r in got) == ["", "", "capacity: 298 sampled looks sk"]


@pytest.mark.parametrize("at", ["head", "tail"])
def test_a_text_too_long_to_clean_is_omitted_and_counted_whatever_it_quotes(at: str) -> None:
    quoted = "pass" + 'word="Q1w2 E3r4 ' + "secret words " * 20 + '"'
    filler = "a " * (events.RAW // 2)
    text = filler + quoted + filler if at == "head" else filler + filler + quoted
    kept = Kept()
    kept.add(asked(text))
    snapshot = kept.snapshot()
    assert snapshot["task"] == events.omitted(len(text))
    assert snapshot["dropped"]["texts too long to clean"] == 1
    assert "Q1w2" not in json.dumps(snapshot)
    assert "1 earlier texts too long to clean" in card.build(snapshot, {}, {})["gaps"][-1]


def test_a_spotter_writes_where_it_started_whatever_changes_later(monkeypatch, tmp_path) -> None:
    async def main() -> spotter.Spotter:
        spot = spotter.Spotter(ctx(), lambda: "s-1", judge())
        from owlbear_delivery_next.local_system import local_home  # noqa: PLC0415

        monkeypatch.setattr(local_home, "root", lambda: tmp_path / "elsewhere")
        spot.handed_off("c", {})
        await spot.drain()
        return spot

    started_in = asyncio.run(main()).folder
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


def test_structured_arguments_and_decisions_are_cleaned_before_they_are_encoded_or_clipped() -> None:
    secret = "Q1w2 E3r4 secret"  # noqa: S105 - a synthetic credential
    nested = {"command": "curl -d '{\"pass" + 'word": "' + secret + "\"}' x", "api_token": "plain-value-123"}
    kept = Kept()
    kept.add(started("c1", "bash", nested))
    args = kept.snapshot()["actions"][0]["args"]
    assert "Q1w2" not in args
    assert "plain-value-123" not in args
    decisions = ["x" * 9000 + " pass" + 'word="' + secret + '" ' + "y" * 2978]  # the clip's tail starts at its quote
    assert "Q1w2" not in json.dumps(card.build(Kept().snapshot(), {}, {"decisions": decisions}))


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
