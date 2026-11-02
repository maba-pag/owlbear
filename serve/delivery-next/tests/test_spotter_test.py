"""The Spotter's steered-versus-silent test (design §4): its record, and the inputs it freezes for every live look.

The looks run the real ``spotter_look.judged`` over a fake SDK client: what it is asked to create and send is what a
live look would send, on real settings files (Global's in a shared repository, read by ``settings_now`` and the
machine's lookup) and a real prompt file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from copilot.generated.session_events import SessionEvent

from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.commands import cases_cli
from owlbear_delivery_next.improvement import cases, spotter, spotter_test_run
from owlbear_delivery_next.local_system import data_place, data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import chats
from owlbear_delivery_next.runtimes import spotter_look
from owlbear_delivery_next.settings.config import Agent, GlobalLayer, MachineValues
from owlbear_delivery_next.state_store import spotter_test
from owlbear_delivery_next.state_store.layers import update_layer
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import lookup, watched

REAL_LOOK = spotter_look.judged  # taken before the suite's fixture replaces it
N = iter(range(10**9))


def records() -> list[dict[str, Any]]:
    return [json.loads(x) for f in sorted(spotter.root().glob("records-*.jsonl")) for x in f.read_text().splitlines()]


def candidate() -> int:
    """A new candidate in the Spotter cases (never shown to a look); the version it is in."""
    the_card = {"step": "build", "intent": {"task": "t", "later_requests": [], "answers": []}, "moment": {"kind": "x"}}
    cid = cases.freeze(the_card, {"source": "pilot", "family": f"session:{next(N)}"})
    entry = {"stage": "candidate", "call": "hand-off-fitness", "why": "why", "example": "", "review": None}
    return cases.commit(cases.current()["n"], {cid: entry}, "t", "add")


class Layers:
    """Global's settings file in a shared repository, the Spotter's prompt file, and each look the SDK was asked for."""

    def __init__(self, root: Path, prompt: Path) -> None:
        self.shared, self.prompt, self.sent = DataRepo(root), prompt, []

    def set(self, model: str, effort: str, context: str, text: str, enrolled: list[str] | None = None) -> None:
        """Global's Spotter role (and enrolled chats) and the prompt file's text."""

        def change(g: GlobalLayer) -> GlobalLayer:
            role = Agent(model=model, effort=effort, context=context)
            machine = g.machine if enrolled is None else MachineValues(enrolled_chats=enrolled)
            return g.model_copy(update={"agents": {**g.agents, "spotter": role}, "machine": machine})

        update_layer(self.shared.global_path, GlobalLayer, change)
        self.prompt.write_text(text)

    def looks(self, step: str) -> list[tuple[Any, ...]]:
        """Each look of *step*: what the SDK was asked for, and what its record says it sent."""
        kept = {r["sdk_sessions"][0]: r for r in records() if r["step"] == step and r["sdk_sessions"]}
        return [(kw["model"], kw["reasoning_effort"], kw["context_tier"], kw["message"].split("\n\n## The card")[0],
                 kept[kw["session_id"]]["prompt"], kept[kw["session_id"]]["cases"], kept[kw["session_id"]]["test"])
                for kw in self.sent if kw["session_id"] in kept]  # fmt: skip


@pytest.fixture
def layers(tmp_path, monkeypatch) -> Layers:
    root = tmp_path / "owlbear-data"
    root.mkdir()
    monkeypatch.setenv(data_repo.VIEW, str(root))
    out = Layers(root, tmp_path / "spotter_prompt.md")
    monkeypatch.setattr(cases, "PROMPT", out.prompt)

    class Session:
        def __init__(self, kw: dict[str, Any]) -> None:
            self.kw = kw
            self.rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=self.metrics))

        async def send_and_wait(self, message: str, **_kw: Any) -> None:
            self.kw["message"] = message
            said = {"id": str(next(N)), "timestamp": "2026-11-02T00:00:00.000Z", "type": "assistant.message",
                    "data": {"messageId": str(next(N)), "content": '{"category": "none"}'}}  # fmt: skip
            self.kw["on_event"](SessionEvent.from_dict(said))

        async def metrics(self) -> Any:
            return SimpleNamespace(total_nano_aiu=1e8)

        async def disconnect(self) -> None:
            pass

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def list_models(self) -> list[Any]:
            return []

        async def create_session(self, **kw: Any) -> Session:
            out.sent.append(kw)
            return Session(kw)

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(spotter_look, "judged", REAL_LOOK)
    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    return out


def started(layers: Layers) -> dict[str, Any]:
    spotter_test.declare("fewer reworked hand-offs", "B", "10% fewer")
    return spotter_test_run.start(lookup.machine(layers.shared))


def test_a_declaration_is_refused_once_the_test_started_and_left_as_it_was(layers) -> None:
    layers.set("gpt-6-luna", "medium", "default", "Judge the card.")
    test = started(layers)
    with pytest.raises(spotter_test.Refused, match=rf"{test['id']} \('fewer reworked hand-offs'\) started at"):
        spotter_test.declare("something else", "A", "1%")
    assert spotter_test.current() == test


def test_while_the_test_runs_no_version_changes_the_examples_and_a_candidate_is_still_added(layers) -> None:
    layers.set("gpt-6-luna", "medium", "default", "Judge the card.")
    the_card = {"step": "build", "intent": {"task": "t", "later_requests": [], "answers": []}, "moment": {"kind": "x"}}
    cid = cases.freeze(the_card, {"source": "pilot", "family": "session:one"})
    entry = {"stage": "candidate", "call": "hand-off-fitness", "why": "why", "example": "", "review": None}
    cases.commit(0, {cid: entry}, "t", "add")
    cases.commit(1, {cid: cases.edited(cid, entry, stage="test", reviewed_by="sol")}, "t", "review")
    test = started(layers)
    edits = {cid: cases.edited(cid, cases.current()["cases"][cid], stage="example", example="a moment")}
    cases.append("runs.jsonl", {"id": "r1", "kind": "regression", "result": "passed", "parent": 2,
                                "edits": cases.digest(edits)})  # fmt: skip
    with pytest.raises(cases.CaseError, match=rf"{test['id']} \('fewer reworked hand-offs'\) runs since .*version 2"):
        cases.commit(2, edits, "t", "promote", "r1")
    assert (cases.current()["n"], candidate()) == (2, 3)  # the examples stay; a candidate is written as ever


def test_a_delivery_step_whose_context_predates_the_start_looks_with_the_frozen_inputs_until_the_end(layers) -> None:
    layers.set("gpt-6-luna", "medium", "default", "Prompt A.")
    store = Store(layers.shared.root.parent / "proj", layers.shared, "proj")
    store.db.check()
    store.write(Lock("c1"), Change(slug="c1"))
    settings = store.settings()  # the step's own settings, layered: the project's over this machine's over Global's
    spot = spotter.Spotter(watched.spot(store, Lock("c1"), "build", settings, watched.needed(settings)),
                           lambda: "step-session", spotter_look.judged)  # fmt: skip

    async def looked() -> None:
        spot.handed_off(f"call-{next(N)}", {"summary": "done"})
        await asyncio.wait(set(spot.tasks), timeout=10)
        assert spotter.WORK.settled(5)

    layers.set("gpt-6.1-sol", "high", "long", "Prompt B.")
    test = started(layers)
    layers.set("gpt-6-astra", "low", "default", "Prompt C.")  # a Global change from another machine, a new prompt
    asyncio.run(looked())
    spotter_test.end()
    asyncio.run(looked())
    assert layers.looks("build") == [
        ("gpt-6.1-sol", "high", "long_context", "Prompt B.", test["frozen"]["prompt_hash"], 0, test["id"]),
        ("gpt-6-luna", "medium", None, "Prompt A.", spot.ctx.prompt.hash, 0, ""),  # ended: the step's own again
    ]


def ev(kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": kind, "id": f"e{next(N)}", "timestamp": "2026-11-02T00:00:00+00:00", "data": data or {}}


def asked(text: str) -> list[dict[str, Any]]:
    return [ev("user.message", {"content": text, "delivery": "idle"})]


def answered() -> list[dict[str, Any]]:
    """The rest of a turn: a direct final answer, its end and the checkpoint, which settle its hand-off."""
    reply = {"content": "Done.", "messageId": f"m{next(N)}", "toolRequests": [], "phase": "final_answer"}
    return [ev("assistant.turn_start", {"turnId": "0"}), ev("assistant.message", reply),
            ev("assistant.turn_end", {"turnId": "0"}), ev("session.usage_checkpoint")]  # fmt: skip


def test_a_chat_looks_with_the_frozen_inputs_in_its_turn_a_new_turn_and_after_a_restart_until_the_end(
    layers, tmp_path
) -> None:
    work, state = tmp_path / "work", tmp_path / "session-state"
    work.mkdir()
    state.mkdir()
    layers.set("gpt-6-luna", "medium", "default", "Prompt A.", enrolled=[str(work)])

    def written(events: list[dict[str, Any]]) -> None:
        folder = state / "c"
        folder.mkdir(exist_ok=True)
        (folder / "workspace.yaml").write_text(f"cwd: {work}\nclient_name: vscode-agent-host\n")
        with (folder / "events.jsonl").open("a") as out:
            out.writelines(json.dumps(d) + "\n" for d in events)

    async def passes(f: chats.Follower, n: int = 1) -> None:
        for _ in range(n):
            await f._pass()  # noqa: SLF001 - driven pass by pass, reading the real settings each pass
            tasks = {t for c in f.chats.values() if c.spot for t in c.spot.tasks} | set(f.tasks)
            if tasks:
                await asyncio.wait(tasks, timeout=10)
            assert spotter.WORK.settled(5)

    async def scenario() -> dict[str, Any]:
        f = chats.Follower(lambda: False, lambda _t: None, poll=0.01, sessions=state)
        await passes(f)  # the baseline: no chat yet
        written(asked("first"))
        await passes(f)  # the turn's own prompt is taken now: A
        layers.set("gpt-6.1-sol", "high", "long", "Prompt B.", enrolled=[str(work)])
        test = started(layers)
        layers.set("gpt-6-astra", "low", "default", "Prompt C.", enrolled=[str(work)])
        written(answered())
        await passes(f)
        candidate()  # a new cases version, shown nowhere: the test's version stays
        written([*asked("second"), *answered()])
        await passes(f, 2)
        await f._quit()  # noqa: SLF001 - the host restarts
        f = chats.Follower(lambda: False, lambda _t: None, poll=0.01, sessions=state)
        await passes(f, 2)
        written([*asked("third"), *answered()])
        await passes(f, 2)
        spotter_test.end()
        written([*asked("fourth"), *answered()])
        await passes(f, 2)
        await f._quit()  # noqa: SLF001
        return test

    test = asyncio.run(scenario())
    frozen = ("gpt-6.1-sol", "high", "long_context", "Prompt B.", test["frozen"]["prompt_hash"], 0, test["id"])
    after = cases.snapshot(verbose=False)
    assert layers.looks("chat") == [
        frozen,  # the turn began before the start, with its own prompt
        frozen,  # a new turn, with its new snapshot
        frozen,  # after the restart: a new follower, a new Spotter
        ("gpt-6-astra", "low", None, "Prompt C.", after.hash, 1, ""),  # ended: the settings and prompt in force
    ]


def test_the_command_declares_starts_shows_and_ends_the_test(layers, capsys) -> None:
    layers.set("gpt-6-luna", "medium", "long", "Judge the card.")

    def run(action: str, **kw: str) -> tuple[int, str]:
        code = cases_cli.main(argparse.Namespace(command="improvement", action="test", test=action, **kw))
        return code, capsys.readouterr().out

    assert run("start") == (1, "refused: no Spotter test is declared: declare its outcome and thresholds first\n")
    code, out = run("declare", outcome="fewer reworked hand-offs", start_threshold="B", promote_threshold="10% fewer")
    assert (code, json.loads(out)["state"], json.loads(out)["declared"]["start_threshold"]) == (0, "declared", "B")
    code, out = run("start")
    shown = json.loads(out)
    hashed = cases.render({}, 0, verbose=False).hash
    assert (code, shown["state"], shown["frozen"]) == (0, "started", {
        "model": "gpt-6-luna", "effort": "medium", "context": "long", "prompt_hash": hashed, "cases": 0})  # fmt: skip
    code, out = run("declare", outcome="x", start_threshold="A", promote_threshold="1%")
    assert (code, out.startswith(f"refused: the Spotter test {shown['id']}")) == (1, True)
    assert json.loads(run("show")[1]) == shown
    code, out = run("end")
    assert (code, json.loads(out)["state"]) == (0, "ended")


def test_the_command_refuses_to_start_while_the_shared_repository_is_not_ready(layers, monkeypatch, capsys) -> None:
    layers.set("gpt-6-luna", "medium", "long", "Judge the card.")
    test = argparse.Namespace(command="improvement", action="test", test="declare", outcome="fewer reworked hand-offs",
                              start_threshold="B", promote_threshold="10% fewer")  # fmt: skip
    assert cases_cli.main(test) == 0
    monkeypatch.delenv(data_repo.VIEW)
    data_place.pointer().parent.mkdir(parents=True, exist_ok=True)
    data_place.pointer().write_text(json.dumps({"remote": "https://github.com/o/owlbear-data"}))  # a clone not done
    capsys.readouterr()

    code = cases_cli.main(argparse.Namespace(command="improvement", action="test", test="start"))

    assert (code, capsys.readouterr().out.startswith("refused: ")) == (1, True)
