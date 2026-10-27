"""The chats follower (Improvement design §4, "Where: Chats"): moments, provenance, tailing, admission and its lifetime.

Every chat here is a synthetic ``events.jsonl`` shaped like the runtime's own log as traced on 2026-10-27 (Copilot CLI
1.0.103): no real chat is read and no model is called.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from owlbear_delivery_next.change_contracts import watch_policy
from owlbear_delivery_next.improvement import cases, credit_meter, spotter
from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.machine_host import chat_settings, chats
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import chat_moments, chatlogs
from owlbear_delivery_next.runtimes.chat_moments import Moments, classify, shell_effects, tokens

LOOKS = ("hand-off", "plan", "state-change", "sample")
N = iter(range(10**9))


def ev(kind: str, data: dict[str, Any] | None = None, **top: Any) -> dict[str, Any]:
    """One event as the runtime logs it."""
    return {"type": kind, "id": top.pop("id", f"e{next(N)}"), "timestamp": "2026-10-27T00:00:00+00:00",
            "data": data or {}, **top}  # fmt: skip


def asked(text: str) -> dict[str, Any]:
    return ev("user.message", {"content": text, "delivery": "idle"})


def reply(text: str, tools: int = 0, **data: Any) -> dict[str, Any]:
    requests = [{"toolCallId": f"r{i}"} for i in range(tools)]
    return ev("assistant.message", {"content": text, "messageId": f"m{next(N)}", "toolRequests": requests, **data})


def call(  # noqa: PLR0913 - the call's parts, as logged
    cid: str, tool: str, args: dict[str, Any], request: dict[str, Any] | None = None, result: str = "ok",
    *, redirect: bool = False,
):  # fmt: skip
    """A call's start (its shell info: whether it redirects into a file), its permission request and completion."""
    start = {"toolCallId": cid, "toolName": tool, "arguments": args}
    if redirect:
        start["shellToolInfo"] = {"hasWriteFileRedirection": True}
    out = [ev("tool.execution_start", start)]
    if request is not None:
        out.append(ev("permission.requested", {"requestId": f"q{cid}", "permissionRequest": {"toolCallId": cid,
                                               "canOfferSessionApproval": False, **request}}))  # fmt: skip
    return [*out, ev("tool.execution_complete", {"toolCallId": cid, "success": True, "result": {"content": result}})]


def shell(command: str, *, read_only: bool, redirect: bool = False) -> dict[str, Any]:
    word = command.split(maxsplit=1)[0]
    commands = [{"identifier": word, "readOnly": read_only}]
    return {"kind": "shell", "commands": commands, "fullCommandText": command, "hasWriteFileRedirection": redirect,
            "intention": "run", "possiblePaths": [], "possibleUrls": []}  # fmt: skip


def turn(text: str = "fix the bug") -> list[dict[str, Any]]:
    """One requester turn as traced: a tool round, then the final answer, then the checkpoint."""
    return [asked(text), ev("system.message", {"content": "You are…"}), ev("assistant.turn_start", {"turnId": "0"}),
            reply("I will look at the tests first.", tools=1), *call("c1", "view", {"path": "a.py"}),
            ev("assistant.turn_end", {"turnId": "0"}), ev("assistant.turn_start", {"turnId": "1"}),
            reply("Done: the test passes.", phase="final_answer"), ev("assistant.turn_end", {"turnId": "1"}),
            ev("session.usage_checkpoint")]  # fmt: skip


def fed(m: Moments, events: list[dict[str, Any]], *, live: bool = True, now: float = 0.0) -> list[dict[str, Any]]:
    out = []
    for d in events:
        before, after = m.feed(d, live=live, now=now)
        out += before + after
    return out


def moments(tmp_path: Path) -> Moments:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return Moments(str(work), Path.home(), None)


# Moments


def test_a_tool_round_then_the_final_answer_gives_the_plan_at_once_and_one_hand_off_once_settled(tmp_path) -> None:
    m = moments(tmp_path)
    got = fed(m, turn())
    assert [g["look"] for g in got] == ["plan"]
    assert got[0]["result"] == "I will look at the tests first."
    assert got[0]["asks_for_tools"] == 1
    assert m.settle(frontier=False, now=0) == []  # bytes known unread: never settled at a batch boundary
    handed = m.settle(frontier=True, now=0)
    assert [(h["look"], h["result"], h["settled"]) for h in handed] == [
        ("hand-off", "Done: the test passes.", "a usage checkpoint after the final reply")]  # fmt: skip
    assert handed[0]["turn"] == got[0]["turn"] == m.turn
    assert m.settle(frontier=True, now=999) == []  # one hand-off per turn


def test_a_direct_answer_is_both_the_plan_and_the_hand_off(tmp_path) -> None:
    m = moments(tmp_path)
    got = fed(m, [asked("what is 2+2?"), ev("assistant.turn_start"), reply("4"), ev("assistant.turn_end"),
                  ev("session.usage_checkpoint")])  # fmt: skip
    got += m.settle(frontier=True, now=0)
    assert [g["look"] for g in got] == ["plan", "hand-off"]


def test_a_text_only_plan_before_the_tool_round_is_the_plan(tmp_path) -> None:
    m = moments(tmp_path)
    got = fed(m, [asked("fix it"), ev("assistant.turn_start"), reply("First I inspect the code, then the tests."),
                  reply("", tools=1), *call("c1", "view", {"path": "a"}), ev("assistant.turn_end")])  # fmt: skip
    assert [(g["look"], g["result"]) for g in got] == [("plan", "First I inspect the code, then the tests.")]
    assert m.settle(frontier=True, now=10**6) == []  # the reply that asked for tools is no final reply


def test_chunks_make_one_reply_and_a_later_round_supersedes_a_final_reply(tmp_path) -> None:
    m = moments(tmp_path)
    parts = [reply(t, messageId="x", chunkIndex=i, chunkCount=2) for i, t in enumerate(("Do", "ne."))]
    got = fed(m, [asked("go"), ev("assistant.turn_start"), *parts, ev("assistant.turn_end")])
    assert [(g["look"], g["result"]) for g in got] == [("plan", "Done.")]
    fed(m, [ev("assistant.turn_start"), reply("", tools=1)])  # background work woke the agent: a new round
    assert m.settle(frontier=True, now=10**6) == []
    fed(m, [*call("c2", "view", {"path": "a"}), ev("assistant.turn_end"), ev("assistant.turn_start"),
            reply("Really done."), ev("assistant.turn_end"), ev("session.usage_checkpoint")])  # fmt: skip
    assert [h["result"] for h in m.settle(frontier=True, now=0)] == ["Really done."]


def test_the_next_requester_closes_the_turn_before_it_starts_the_next_and_an_abort_drops_it(tmp_path) -> None:
    m = moments(tmp_path)
    fed(m, [asked("one"), ev("assistant.turn_start"), reply("first answer"), ev("assistant.turn_end")])
    first = m.turn
    before, after = m.feed(asked("two"), live=True, now=0)
    assert [(b["look"], b["turn"], b["settled"]) for b in before] == [("hand-off", first, "the next requester message")]
    assert after == []
    assert m.turn != first
    fed(m, [ev("assistant.turn_start"), reply("second answer"), ev("assistant.turn_end"), ev("abort")])
    assert fed(m, [asked("three")]) == []  # an aborted turn has no hand-off


def test_only_the_requester_starts_a_turn_and_only_the_chats_own_agent_counts(tmp_path) -> None:
    m = moments(tmp_path)
    fed(m, [asked("go")])
    first = m.turn
    sub = {"parentToolCallId": "t1"}
    noise = [ev("user.message", {"content": "continue", "isAutopilotContinuation": True}),
             ev("user.message", {"content": "a task finished", "source": "system"}),
             ev("assistant.message", {"content": "subagent says", **sub}), ev("assistant.message", {
                 "content": "other agent"}, agentId="a1")]  # fmt: skip
    assert fed(m, noise) == []
    assert m.turn == first
    assert not m.planned


def test_the_quiet_fallback_waits_for_open_rounds_and_calls(tmp_path) -> None:
    m = moments(tmp_path)
    fed(m, [asked("go"), ev("assistant.turn_start"), reply("answer"), ev("assistant.turn_end")], now=100.0)
    assert m.settle(frontier=True, now=100.0 + chat_moments.QUIET - 1) == []
    m.calls["bg"] = {"tool": "bash"}  # a call still running
    assert m.settle(frontier=True, now=100.0 + chat_moments.QUIET) == []
    m.calls.clear()
    assert [h["settled"] for h in m.settle(frontier=True, now=100.0 + chat_moments.QUIET)] == [
        f"{chat_moments.QUIET:.0f} seconds without an event of the agent after its final reply"]  # fmt: skip


def test_history_never_arms_a_later_look(tmp_path) -> None:
    m = moments(tmp_path)
    assert fed(m, [asked("old"), ev("assistant.turn_start"), reply("old answer"), ev("assistant.turn_end")],
               live=False) == []  # fmt: skip
    assert fed(m, [ev("session.usage_checkpoint")], now=0) == []  # a live checkpoint after a historical reply
    assert m.settle(frontier=True, now=10**6) == []
    assert fed(m, [*call("c9", "bash", {"command": "rm -rf /x"}, shell("rm -rf /x", read_only=False))],
               live=False) == []  # fmt: skip


# State changes


def classified(
    tmp_path: Path, tool: str, args: Any, request: dict[str, Any] | None = None, *, redirect: bool = False
) -> tuple[str, set, tuple]:  # fmt: skip
    m = moments(tmp_path)
    fed(m, [asked("go")])
    fed(m, call("c", tool, args, request, redirect=redirect)[:-1])
    return classify(m.calls["c"], m.own, m.places)


def test_writes_outside_the_workspace_are_state_changes_wherever_they_go(tmp_path) -> None:
    inside = str(tmp_path / "work" / "a.py")
    assert classified(tmp_path, "edit", {"path": inside})[0] == "none"
    for outside in ("/tmp/x.txt", str(Path.home() / ".cache" / "x"), str(local_home.root() / "x")):  # noqa: S108 - no exemption
        certainty, what, targets = classified(tmp_path, "edit", {"path": outside})
        assert (certainty, what) == ("identified", {"outside write"})
        assert targets
    write = {"kind": "write", "diff": "", "fileName": "/etc/hosts", "intention": "edit"}
    assert classified(tmp_path, "apply_patch", {"input": "…"}, write)[:2] == ("identified", {"outside write"})


def test_shell_calls_are_read_only_identified_or_unresolved_by_the_runtimes_evidence(tmp_path) -> None:
    assert classified(tmp_path, "bash", {"command": "ls"}, shell("ls", read_only=True))[0] == "none"
    assert classified(tmp_path, "bash", {"command": "rm -rf x"}, shell("rm -rf x", read_only=False))[:2] == (
        "identified", {"deleting"})  # fmt: skip
    assert classified(tmp_path, "bash", {"command": "uv run pytest"}, shell("uv", read_only=False))[0] == "unresolved"
    assert classified(tmp_path, "bash", {"command": "ls"})[0] == "unresolved"  # no permission request: no evidence


@pytest.mark.parametrize("command", ["git clean --dry-run", "git clean -n", "git push --dry-run", "gh pr view 3",
                                     "git config --list", "rm --help"])  # fmt: skip
def test_the_runtimes_read_only_evidence_wins_over_the_words_of_a_preview_or_query(tmp_path, command: str) -> None:
    assert classified(tmp_path, "bash", {"command": command}, shell(command, read_only=True))[0] == "none"


def test_a_redirection_into_a_file_or_a_mutating_command_is_never_read_only(tmp_path) -> None:
    clean = "git clean -fd"
    assert classified(tmp_path, "bash", {"command": clean}, shell(clean, read_only=False))[:2] == (
        "identified", {"deleting"})  # fmt: skip
    cat = "cat a > b"
    assert classified(tmp_path, "bash", {"command": cat}, shell(cat, read_only=True, redirect=True))[0] == "unresolved"
    assert classified(tmp_path, "bash", {"command": cat}, shell(cat, read_only=True), redirect=True)[0] == "unresolved"
    write = {"kind": "write", "diff": "", "fileName": "/etc/hosts", "intention": "edit"}
    assert classified(tmp_path, "bash", {"command": "ls"}, write)[:2] == ("identified", {"outside write"})


def test_tools_are_judged_by_their_names_words_and_the_runtimes_read_only_flag(tmp_path) -> None:
    assert classified(tmp_path, "github-mcp-server-create_issue", {})[:2] == (
        "identified", {"a tool that changes outside state"})  # fmt: skip
    assert classified(tmp_path, "list_assets", {})[0] == "none"  # a word, never a substring: "assets" holds "set"
    assert classified(tmp_path, "browser-click", {})[0] == "unresolved"
    mcp = {"kind": "mcp", "readOnly": True, "serverName": "s", "toolName": "t", "toolTitle": "t"}
    assert classified(tmp_path, "s-frobnicate", {}, mcp)[0] == "none"
    assert classified(tmp_path, "view", {"path": "a"})[0] == "none"
    assert tokens("saveMemory_now") == {"save", "memory", "now"}


def test_an_unreadable_permission_request_leaves_the_call_unresolved_and_old_open_calls_are_counted(tmp_path) -> None:
    m = moments(tmp_path)
    fed(m, [asked("go"), ev("tool.execution_start", {"toolCallId": "c", "toolName": "view", "arguments": {}}),
            ev("permission.requested", {"permissionRequest": {"kind": "shell", "toolCallId": "c"}})])  # fmt: skip
    assert m.calls["c"]["unread"] == 1
    got = fed(m, [ev("tool.execution_complete", {"toolCallId": "c", "result": {"content": ""}})])
    assert [(g["look"], g["certainty"]) for g in got] == [("state-change", "unresolved")]
    for i in range(chat_moments.CALLS + 3):
        fed(m, [ev("tool.execution_start", {"toolCallId": f"o{i}", "toolName": "bash", "arguments": {}})])
    assert (len(m.calls), m.forgotten) == (chat_moments.CALLS, 3)


@pytest.mark.parametrize(
    ("command", "what"),
    [
        ("git push origin main", {"publishing"}), ("git push origin --delete old", {"publishing", "deleting"}),
        ("gh pr create --fill", {"publishing"}), ("gh pr view 3", set()), ("gh api -X POST repos/x", {"publishing"}),
        ("gh api repos/x", set()), ("npm publish", {"publishing"}), ("curl -d a=1 https://x", {"publishing"}),
        ("curl https://x", set()), ("cd a && rm -f b", {"deleting"}), ("git branch -D x", {"deleting"}),
        ("git reset --hard", {"deleting"}), ("git config user.name x", {"settings"}),
        ("git config --get user.name", set()), ("defaults write a b c", {"settings"}), ("crontab -l", set()),
        ("FOO=1 sudo chmod 600 x", {"settings"}), ("gh secret set X", {"settings"}), ("pytest -q", set()),
    ],
)  # fmt: skip
def test_shell_effects_by_words(command: str, what: set[str]) -> None:
    assert shell_effects(command) == what


# The follower


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Enrolled ``work``, a runtime session folder, a recording judge and a follower driven pass by pass."""
    work = tmp_path / "work"
    work.mkdir()
    state = tmp_path / "session-state"
    state.mkdir()
    w = World(work, state)
    monkeypatch.setattr(chatlogs, "state", lambda: state)
    return w


class World:
    def __init__(self, work: Path, state: Path) -> None:
        self.work, self.state, self.cards, self.paused = work, state, [], False
        self.ctx = spotter.Context(project="", change="", step="chat", looks=LOOKS, sample_rate=0, verbose=False,
                                   model="m1", effort="", limit=0.75, gaps=(chat_settings.CHAT,))  # fmt: skip
        self.folders: tuple[str, ...] = (str(work),)
        self.plan: chat_settings.Plan | str | None = None
        self.follower = self.new()

    def new(self) -> chats.Follower:
        return chats.Follower(lambda: self.paused, lambda _t: None, read=self.read, judge=self.judge, poll=0.01,
                              sessions=self.state)  # fmt: skip

    def read(self) -> chat_settings.Plan | str:
        return self.plan if self.plan is not None else chat_settings.Plan(self.ctx, self.folders)

    async def judge(self, card: dict[str, Any], ctx: spotter.Context, meter: credit_meter.Meter) -> str:
        self.cards.append((card, ctx))
        part = meter.part()  # one billed call, as a confirmed session reports it
        part.started(f"sdk-{meter.id}")
        part.call(0.01)
        part.ended(None, confirmed=True)
        return '{"category": "none"}'

    def chat(self, sid: str, events: list[dict[str, Any]], cwd: Path | None = None) -> Path:
        folder = self.state / sid
        folder.mkdir(exist_ok=True)
        (folder / "workspace.yaml").write_text(f"cwd: {cwd or self.work}\n")
        with (folder / "events.jsonl").open("a") as out:
            out.writelines(json.dumps(d) + "\n" for d in events)
        return folder / "events.jsonl"

    async def passes(self, n: int = 1, follower: chats.Follower | None = None) -> None:
        f = follower or self.follower
        for _ in range(n):
            await f._pass()  # noqa: SLF001 - driven pass by pass
            await self.settled(f)

    async def settled(self, f: chats.Follower) -> None:
        tasks = {t for c in f.chats.values() if c.spot for t in c.spot.tasks} | set(f.tasks)
        if tasks:
            await asyncio.wait(tasks, timeout=10)
        assert spotter.WORK.settled(5)


def records() -> list[dict[str, Any]]:
    path = spotter.place() / f"records-{datetime.now(UTC).date().isoformat()}.jsonl"
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def test_a_chat_found_after_the_follower_began_is_looked_at_from_its_start_and_its_record_names_chat_and_turn(world):
    async def scenario() -> None:
        await world.passes()  # the baseline: no chat yet
        whole = turn()
        world.chat("c1", whole[:4])  # the request and the plan
        await world.passes()
        world.chat("c1", whole[4:])
        await world.passes(2)
        world.chat("c1", turn("a quick one"))  # a whole turn between two passes: its plan look is still running
        await world.passes()

    asyncio.run(scenario())
    got = [(r["look"], r["session"], r["step"], r["skipped"]) for r in records()]
    assert got[:2] == [("plan", "c1", "chat", ""), ("hand-off", "c1", "chat", "")]
    assert sorted(got[2:]) == [
        ("hand-off", "c1", "chat", "capacity: a chat look is already running"), ("plan", "c1", "chat", "")]  # fmt: skip
    assert records()[0]["turn"] == records()[1]["turn"] == turn_id(world.state / "c1")
    card = world.cards[0][0]
    assert card["step"] == "chat"
    assert chat_settings.CHAT in card["gaps"]


def turn_id(folder: Path) -> str:
    return next(json.loads(x)["id"] for x in (folder / "events.jsonl").read_text().splitlines()
                if json.loads(x)["type"] == "user.message")  # fmt: skip


def test_a_chat_that_existed_when_following_began_starts_at_its_end_and_its_past_is_context_only(world):
    world.chat("old", turn("the old task"))

    async def scenario() -> None:
        await world.passes(2)
        assert records() == []  # its past is never looked at
        world.chat("old", turn("the new task"))
        await world.passes(2)

    asyncio.run(scenario())
    assert sorted(r["look"] for r in records()) == ["hand-off", "plan"]
    card = world.cards[-1][0]
    assert card["intent"]["task"] == "the old task"
    assert card["intent"]["later_requests"] == ["the new task"]


def test_provenance_and_enrolment_come_before_any_read_and_fail_closed(world, monkeypatch, tmp_path):
    opened: list[str] = []
    real, own, unreadable = os.open, chatlogs.own, [False]
    monkeypatch.setattr(chats.os, "open", lambda p, *a, **k: opened.append(str(p)) or real(p, *a, **k))
    monkeypatch.setattr(chatlogs, "own", lambda: None if unreadable[0] else own())
    world.folders = (str(world.work), str(local_home.root()))  # OwlBear's own folder is never a chat, even enrolled

    async def scenario() -> None:
        await world.passes()
        world.chat("ours", turn())
        chatlogs.note({"event": "started", "session": "ours"})  # a Delivery or curation session
        world.chat("elsewhere", turn(), cwd=tmp_path / "workshop")  # a prefix of the enrolled folder is not in it
        world.chat("owlbear", turn(), cwd=local_home.root() / "worktrees" / "x")
        bare = world.state / "nometa"
        bare.mkdir()
        (bare / "events.jsonl").write_text(json.dumps(asked("x")) + "\n")
        await world.passes(2)
        assert not [p for p in opened if "events.jsonl" in p]
        (bare / "workspace.yaml").write_text(f"cwd: {world.work}\n")  # its metadata appears later: it is read now
        unreadable[0] = True  # the manifest cannot be read: nothing is
        await world.passes()
        assert not [p for p in opened if "events.jsonl" in p]
        unreadable[0] = False
        await world.passes()
        assert {Path(p).parent.name for p in opened if "events.jsonl" in p} == {"nometa"}
        (bare / "workspace.yaml").write_text(f"cwd: {tmp_path / 'workshop'}\n")  # it moved out of the enrolled folder
        await world.passes()
        assert "nometa" not in world.follower.chats

    asyncio.run(scenario())


def test_switched_off_or_unset_reads_nothing_and_drops_what_was_followed(world, monkeypatch):
    opened: list[str] = []
    real = os.open
    monkeypatch.setattr(chats.os, "open", lambda p, *a, **k: opened.append(str(p)) or real(p, *a, **k))

    async def scenario() -> None:
        await world.passes()
        world.chat("c1", [asked("go")])
        await world.passes()
        assert "c1" in world.follower.chats
        world.plan = "the Spotter is switched off"
        opened.clear()
        await world.passes(2)
        assert opened == []
        assert world.follower.chats == {}

    asyncio.run(scenario())


def test_a_restart_records_the_missed_bytes_as_a_gap_and_never_looks_at_them(world):
    async def scenario() -> None:
        await world.passes()
        world.chat("c1", [asked("first")])
        await world.passes()
        await world.follower._quit()  # noqa: SLF001 - the first run ends and keeps its offsets
        world.chat("c1", turn("while OwlBear was down"))  # written while no follower ran
        world.follower = world.new()
        await world.passes(2)
        assert [(r["look"], r["skipped"][:26]) for r in records()] == [("gap", "OwlBear was not following:")]
        world.chat("c1", turn("after the restart"))
        await world.passes(2)

    asyncio.run(scenario())
    assert sorted(r["look"] for r in records()) == ["gap", "hand-off", "plan"]


def test_one_chat_look_at_a_time_counting_a_running_one_and_none_while_paused_or_closed(world):
    release = asyncio.Event()

    async def slow(card: dict[str, Any], ctx: spotter.Context, meter: credit_meter.Meter) -> str:
        await release.wait()
        return await World.judge(world, card, ctx, meter)

    async def scenario() -> None:
        world.follower.judge = slow
        await world.passes()
        world.chat("a", [asked("one"), ev("assistant.turn_start"), reply("plan a", tools=1)])
        world.chat("b", [asked("two"), ev("assistant.turn_start"), reply("plan b", tools=1)])
        await world.follower._pass()  # noqa: SLF001
        await asyncio.sleep(0)
        assert world.follower.room() == "capacity: a chat look is already running"
        release.set()
        await world.settled(world.follower)
        world.paused = True
        world.chat("a", [*call("x", "bash", {"command": "rm a"}, shell("rm a", read_only=False))])
        await world.passes()
        world.paused = False
        world.follower.close()
        assert world.follower.room().startswith("stopping")  # closed: none is admitted, and no chat is read
        world.chat("b", [*call("y", "bash", {"command": "rm b"}, shell("rm b", read_only=False))])
        await world.passes()

    asyncio.run(scenario())
    got = sorted((r["look"], r["skipped"].split(":")[0]) for r in records())
    assert got == [("plan", ""), ("plan", "capacity"), ("state-change", "paused")]
    assert world.follower.chats["a"].spot.kept.n > 3  # paused, the chat is read all the same


def test_a_state_change_wins_over_a_sample_of_the_same_call(world):
    world.ctx = dataclasses.replace(world.ctx, sample_rate=100)

    async def scenario() -> None:
        await world.passes()
        world.chat("c", [asked("go"), *call("x", "bash", {"command": "git push"}, shell("git push", read_only=False))])
        await world.passes()
        assert world.follower.chats["c"].spot.crowded == {}  # no sample of it was even tried
        world.chat("c", call("y", "view", {"path": "a"}))
        await world.passes()

    asyncio.run(scenario())
    assert sorted((r["look"], r["call"]) for r in records()) == [("sample", "y"), ("state-change", "x")]


def test_a_look_keeps_the_settings_it_was_admitted_with(world):
    release = asyncio.Event()

    async def slow(card: dict[str, Any], ctx: spotter.Context, meter: credit_meter.Meter) -> str:
        await release.wait()
        return await World.judge(world, card, ctx, meter)

    async def scenario() -> None:
        world.follower.judge = slow
        await world.passes()
        world.chat("c", [asked("go"), ev("assistant.turn_start"), reply("plan", tools=1)])
        await world.follower._pass()  # noqa: SLF001
        world.ctx = dataclasses.replace(world.ctx, model="m2")
        await world.follower._pass()  # noqa: SLF001
        release.set()
        await world.settled(world.follower)

    asyncio.run(scenario())
    assert [r["model"] for r in records()] == ["m1"]
    assert world.cards[0][1].model == "m1"


def test_tailing_waits_for_a_whole_line_leaves_out_an_oversized_one_and_takes_a_replaced_log_as_context(
    world, monkeypatch
):
    monkeypatch.setattr(chats, "LINE", 500)
    monkeypatch.setattr(chats, "CHUNK", 64)

    async def scenario() -> None:
        await world.passes()
        log = world.chat("c", [asked("go")])
        with log.open("a") as out:
            out.write('{"type": "assistant.turn_start", "data"')  # still being written
        await world.passes()
        c = world.follower.chats["c"]
        at = c.offset
        assert at < log.stat().st_size
        with log.open("a") as out:
            out.write(": {}}\n" + json.dumps(reply("x" * 1000)) + "\n" + json.dumps(ev("assistant.turn_end")) + "\n")
        await world.passes(3)
        assert c.offset == log.stat().st_size
        assert any("left out" in g for g in c.gaps)
        log.unlink()
        world.chat("c", [asked("replaced")])  # shorter than what was read: replaced, whatever its inode
        await world.passes(2)
        assert records() == []  # what the replaced log held is context only
        assert any("replaced" in g for g in world.follower.chats["c"].gaps)

    asyncio.run(scenario())


def test_a_pass_reads_a_bounded_number_of_bytes(world, monkeypatch):
    monkeypatch.setattr(chats, "PASS", 200)
    monkeypatch.setattr(chats, "CHUNK", 100)

    async def scenario() -> None:
        await world.passes()
        log = world.chat("c", [asked(f"message {i}") for i in range(20)])
        await world.passes()
        assert 0 < world.follower.chats["c"].offset < log.stat().st_size
        await world.passes(20)
        assert world.follower.chats["c"].offset == log.stat().st_size

    asyncio.run(scenario())


HOLDER = """
import fcntl, os, sys, time
fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX)
print("held", flush=True)
sys.stdin.readline()
"""


def test_a_follower_reads_nothing_while_another_process_holds_the_lock_and_releases_it_only_once_ended(world):
    world.chat("c", [asked("go")])
    lock = spotter.root() / chats.LOCK
    holder = subprocess.Popen([sys.executable, "-c", HOLDER, str(lock)], stdin=subprocess.PIPE,  # noqa: S603
                              stdout=subprocess.PIPE, text=True)  # fmt: skip
    try:
        assert holder.stdout.readline().strip() == "held"
        said: list[str] = []
        f = chats.Follower(lambda: False, said.append, read=world.read, judge=world.judge, poll=0.05,
                           sessions=world.state)  # fmt: skip
        f.start()
        time.sleep(0.4)
        assert f.chats == {}
        assert said == ["chats follower: waiting for the previous one to end; no chat is read meanwhile"]
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(5)
        deadline = time.monotonic() + 5
        while "c" not in f.chats and time.monotonic() < deadline:
            time.sleep(0.02)
        assert "c" in f.chats
        f.close()
        assert f.join(10)
        assert f.ended.is_set()
    finally:
        holder.kill()
    other = subprocess.run([sys.executable, "-c", ("import fcntl, os, sys; fd = os.open(sys.argv[1], os.O_WRONLY); "  # noqa: S603
                            "fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)"), str(lock)], check=False)  # fmt: skip
    assert other.returncode == 0  # released once the follower ended


def test_a_follower_keeps_its_lock_while_its_looks_still_drain(world):
    gate = threading.Event()

    async def stuck(_card: dict[str, Any], _ctx: spotter.Context, _meter: credit_meter.Meter) -> str:
        gate.set()
        await asyncio.sleep(3600)
        return ""

    world.chat("c", [])
    f = chats.Follower(lambda: False, lambda _t: None, read=world.read, judge=stuck, poll=0.02, sessions=world.state)
    f.start()
    time.sleep(0.2)
    world.chat("c", [asked("go"), ev("assistant.turn_start"), reply("plan", tools=1)])
    assert gate.wait(5)
    f.close()
    lock = spotter.root() / chats.LOCK
    probe = [sys.executable, "-c", ("import fcntl, os, sys; fd = os.open(sys.argv[1], os.O_WRONLY); "
             "fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)"), str(lock)]  # fmt: skip
    assert subprocess.run(probe, check=False, capture_output=True).returncode != 0  # noqa: S603 - still draining
    assert f.join(chats.CLOSE)
    assert subprocess.run(probe, check=False, capture_output=True).returncode == 0  # noqa: S603
    assert [(r["look"], r["skipped"][:8]) for r in records()] == [("plan", "the step")]  # stopped looks are recorded


def test_the_machine_closes_its_follower_at_its_stop():
    now = datetime.now(UTC)
    m = Machine(HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=now, code=codebase.CURRENT))  # noqa: S106
    assert not m.chats.closed.is_set()
    m.stop_all()
    assert m.chats.closed.is_set()
    assert m.chats.thread is None


def test_places_have_no_exemptions_for_a_chat(tmp_path):
    assert moments(tmp_path).places.exempt == ()
    assert isinstance(moments(tmp_path).places, watch_policy.Places)


def test_a_session_registering_while_the_follower_discovers_is_never_read(world, monkeypatch):
    """OwlBear notes a session and creates its folder just after the follower read the manifest."""
    opened: list[str] = []
    real_open, real_own = os.open, chatlogs.own
    monkeypatch.setattr(chats.os, "open", lambda p, *a, **k: opened.append(str(p)) or real_open(p, *a, **k))

    def racing() -> set[str] | None:
        read = real_own()
        if not (world.state / "late").exists():  # registered and created right after this read
            chatlogs.note({"event": "started", "session": "late"})
            world.chat("late", turn())
        return read

    async def scenario() -> None:
        await world.passes()  # the baseline
        monkeypatch.setattr(chatlogs, "own", racing)
        await world.passes(3)

    asyncio.run(scenario())
    assert not [p for p in opened if "late" in p]
    assert records() == []


def test_a_log_that_shrinks_while_an_oversized_event_is_skipped_ends_the_read(world, tmp_path):
    log = tmp_path / "events.jsonl"
    log.write_bytes(b"x" * 10)  # measured as 100 bytes, then shrank to 10
    c = chats.Chat("c", str(world.work), skipping=True)
    fd = os.open(log, os.O_RDONLY)
    got: list[int] = []
    reading = threading.Thread(target=lambda: got.append(asyncio.run(world.follower._read(c, fd, 100, 1000))),  # noqa: SLF001
                               daemon=True)  # fmt: skip
    reading.start()
    reading.join(5)
    assert not reading.is_alive()  # it never spins on an empty read
    os.close(fd)
    assert (got, c.offset, c.skipping) == ([10], 10, True)


def test_an_idle_chat_settles_with_the_settings_in_force_then(world, monkeypatch):
    async def scenario() -> None:
        await world.passes()
        world.chat("c", [asked("go"), ev("assistant.turn_start"), reply("the answer"), ev("assistant.turn_end")])
        await world.passes()  # its plan is looked at; the hand-off waits: no checkpoint
        world.ctx = dataclasses.replace(world.ctx, model="m2")
        monkeypatch.setattr(chat_moments, "QUIET", 0.0)
        await world.passes()  # no new byte: the quiet fallback settles it

    asyncio.run(scenario())
    assert sorted((r["look"], r["model"]) for r in records()) == [("hand-off", "m2"), ("plan", "m1")]


def example(text: str) -> int:
    """An active example in the Spotter cases, made as a passed regression makes one; the version it is in."""
    the_card = {"step": "build", "intent": {"task": text, "later_requests": [], "answers": []}, "moment": {"kind": "x"}}
    cid = cases.freeze(the_card, {"source": "pilot", "reserve": False, "unscored": "", "family": f"session:{text}",
                                  "assumption": ""})  # fmt: skip
    entry = {"stage": "candidate", "call": "hand-off-fitness", "why": f"why {text}", "example": "", "review": None}
    with cases.locked():
        cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
        cases.commit(
            cases.current()["n"], {cid: cases.edited(cid, entry, stage="test", reviewed_by="sol")}, "t", "review"
        )
        cur = cases.current()
        edits = {cid: cases.edited(cid, cur["cases"][cid], stage="example", example=f"moment of {text}")}
        cases.append("runs.jsonl", {"id": f"r-{cid}", "kind": "regression", "result": "passed", "parent": cur["n"],
                                    "edits": cases.digest(edits)})  # fmt: skip
        return cases.commit(cur["n"], edits, "t", "promote", f"r-{cid}")


def test_a_chat_look_keeps_its_turns_case_snapshot_and_its_limit_whatever_changes_before_it_runs(world):
    release = asyncio.Event()

    async def slow(card: dict[str, Any], ctx: spotter.Context, meter: credit_meter.Meter) -> str:
        await release.wait()
        return await World.judge(world, card, ctx, meter)

    first = example("the agent stops with work unfinished")
    sent = cases.snapshot(verbose=False)
    assert (sent.cases, "### Example 1" in sent.text) == (first, True)

    async def scenario() -> int:
        world.follower.judge = slow
        await world.passes()
        world.chat("c", [asked("go"), ev("assistant.turn_start"), reply("I will read a.py first.", tools=1)])
        await world.follower._pass()  # noqa: SLF001 - the turn's plan look is admitted and waits
        world.ctx = dataclasses.replace(world.ctx, limit=2.0, model="m2")  # the settings change before it runs
        second = example("a hand-off with gaps")  # and so do the cases
        await world.follower._pass()  # noqa: SLF001
        release.set()
        await world.settled(world.follower)
        world.chat("c", [*call("x", "view", {"path": "a.py"}), ev("assistant.turn_end"), ev("assistant.turn_start"),
                         reply("Done.", phase="final_answer"), ev("assistant.turn_end"),
                         ev("session.usage_checkpoint")])  # fmt: skip
        await world.passes()  # the same turn's hand-off: the settings in force now, the turn's snapshot
        whole = turn("the next one")  # a new turn: a new snapshot
        world.chat("c", whole[:4])
        await world.passes()
        world.chat("c", whole[4:])
        await world.passes(2)
        return second

    second = asyncio.run(scenario())
    later = cases.snapshot(verbose=False)
    assert (later.cases, later.hash != sent.hash) == (second, True)
    turns = [json.loads(x)["id"] for x in (world.state / "c" / "events.jsonl").read_text().splitlines()
             if json.loads(x)["type"] == "user.message"]  # fmt: skip
    got = [(r["look"], r["turn"], r["cases"], r["prompt"], r["limit"], r["model"]) for r in records()]
    assert got == [
        ("plan", turns[0], first, sent.hash, 0.75, "m1"),  # admitted before the change: it never reaches it
        ("hand-off", turns[0], first, sent.hash, 2.0, "m2"),
        ("plan", turns[1], second, later.hash, 2.0, "m2"),
        ("hand-off", turns[1], second, later.hash, 2.0, "m2"),
    ]
    for r in records():  # each look's meter, as its record keeps it
        assert (r["credits"], r["credits_known"], r["stopped"], r["stopped_by"], r["sdk_sessions"], r["skipped"]) == (
            0.01, True, "", "", [f"sdk-{r['id']}"], "")  # fmt: skip
    assert world.cards[0][1].prompt == sent  # exactly the snapshot the look was admitted with
