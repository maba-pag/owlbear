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

from owlbear_delivery_next.change_contracts.models import Change, Plan, Task
from owlbear_delivery_next.improvement import card, spotter
from owlbear_delivery_next.improvement.events import Kept
from owlbear_delivery_next.runtimes import chatlogs, sdk_adapter, step_decisions
from owlbear_delivery_next.settings.config import Layer, SettingsUnset, resolve
from owlbear_delivery_next.settings.improvement import Spotter
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import watched

REAL_LOOK = spotter._judged  # noqa: SLF001 - taken before the suite's fixture replaces it


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
    assert [r["skipped"] for r in records()] == ["the step ended while the look ran"]


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
    assert [r["skipped"].split(":")[0] for r in records()] == ["capacity", "", "", "", "budget"]
    ledger = json.loads((spotter.root() / f"ledger-{spotter._today()}.json").read_text())  # noqa: SLF001
    assert ledger == {"reserved": 0.0, "spent": 0.75}


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


def test_the_submit_call_starts_the_look_before_delivery_handles_it() -> None:
    order: list[str] = []
    feed = SimpleNamespace(spotter=SimpleNamespace(handed_off=lambda cid, args: order.append(f"look {cid} {args}")))
    st = SimpleNamespace(feed=feed, _handle=lambda *_: order.append("handled") or "result")
    inv = SimpleNamespace(tool_call_id="call-3", arguments={"summary": "s"})
    assert asyncio.run(sdk_adapter._Step._submitted(st, None, inv)) == "result"  # noqa: SLF001
    assert order == ["look call-3 {'summary': 's'}", "handled"]


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
    from owlbear_delivery_next.machine_host import machine_settings  # noqa: PLC0415

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

    import copilot  # noqa: PLC0415

    from owlbear_delivery_next.runtimes import copilot_cli  # noqa: PLC0415

    monkeypatch.setattr(copilot, "CopilotClient", Client)
    monkeypatch.setattr(copilot_cli, "cli_path", lambda: "/bin/false")
    assert asyncio.run(REAL_LOOK({"step": "build"}, ctx(verbose=True))) == ('{"verdict": "silent"}', 0.2)
    chosen = ("available_tools", "mcp_servers", "enable_config_discovery", "model", "reasoning_effort", "timeout")
    assert [made[k] for k in chosen] == [[], {}, False, "gpt-6-luna", "medium", spotter.LOOK]
    assert "rationale" in made["message"]
    assert '{"step": "build"}' in made["message"]
    assert (made["disconnected"], made["stopped"]) == (True, True)
    lines = [json.loads(x) for x in (chatlogs.root() / "manifest.jsonl").read_text().splitlines()]
    assert [(x["event"], x["session"], x.get("kind")) for x in lines] == [
        ("started", "look-1", "spotter"), ("ended", "look-1", None)]  # fmt: skip
