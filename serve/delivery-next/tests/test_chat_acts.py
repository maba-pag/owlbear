"""How the Spotter acts in a VS Code chat (#717): the chat's mapping, its acts over the agent host and their delivery.

Only VS Code's store (a temporary SQLite file shaped like ``agent-host.db``), the agent host's transport, its clock and
the bound's sleep are faked; the Spotter, its act lines and the ``ChatActor`` are real.
"""

from __future__ import annotations

import asyncio
import base64
import copy
import dataclasses
import json
import sqlite3
import threading
from typing import TYPE_CHECKING, Any

import pytest

from owlbear_delivery_next.improvement import acts, credit_meter, spotter
from owlbear_delivery_next.machine_host import chat_acts

if TYPE_CHECKING:
    from pathlib import Path

ACTIONS = {"hand-off-fitness": "refuse-hand-off", "course-and-constraints": "steer",
           "outside-state-changes": "stop-and-resume", "irreversible-harm": "stop-and-ask"}  # fmt: skip
MODEL = {"id": "claude-opus-5.5", "config": {"thinkingLevel": "high"}}


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode().rstrip("=")


ROWS = (
    ("copilotcli:/aaa", f"ahp-chat://c-a/{b64('copilotcli:/aaa')}", "s-a"),  # as VS Code's store keeps them
    ("copilotcli:/aaa", f"ahp-chat://c-ab/{b64('copilotcli:/aaa')}", "s-ab"),  # another chat in the same folder
    ("copilotcli:/bbb", f"ahp-chat://default/{b64('copilotcli:/bbb')}", "s-b"),  # a session's default chat
    ("copilotcli:/ccc", f"ahp-chat://default/{b64('copilotcli:/ccc')}", "s-c"),  # one the host lists by its uuid
)


def store(tmp_path: Path, *rows: tuple[str, str, str]) -> Path:
    """VS Code's store with one chat per (session URI, chat URI, Copilot session id)."""
    db = tmp_path / "agent-host.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE chats_v2 (chat_uri TEXT PRIMARY KEY NOT NULL, owner_session_uri TEXT NOT NULL, "
                     "provider_data TEXT, tombstoned INTEGER NOT NULL DEFAULT 0)")  # fmt: skip
        conn.executemany("INSERT INTO chats_v2 (chat_uri, owner_session_uri, provider_data) VALUES (?, ?, ?)",
                         [(chat, owner, json.dumps({"sdkSessionId": sid})) for owner, chat, sid in rows])  # fmt: skip
    return db


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


class Host:
    """The agent host as one client sees it: its listed sessions, each chat's state, and every action dispatched."""

    def __init__(self, clock: Clock, *, active: str = "t-2", holds: bool = False, runs_on: bool = False) -> None:
        self.clock, self.holds, self.runs_on = clock, holds, runs_on  # a withdrawal or a cancel the host ignores
        self.client_id = "fake"
        self.items = [
            {"resource": "ahp-session:/aaa", "chats": [{"resource": "ahp-chat:/c-a"}]},
            {"resource": "ahp-session:/bbb", "chats": [{"resource": f"ahp-chat://default/{b64('x')}"}]},
            {
                "resource": "ahp-session:/ccc",
                "defaultChat": "ahp-chat:/c-c",  # a window session, traced 2026-11-02
                "chats": [{"resource": "ahp-chat:/c-c"}, {"resource": "ahp-chat:/c-c2"}],
            },
        ]
        turn = {"id": "t-1", "message": {"text": "fix the bug", "origin": {"kind": "user"}, "model": MODEL}}
        self.chat = {"turns": [turn], "activeTurn": {"id": active, "message": {"text": "go"}} if active else None}
        self.actions: list[dict[str, Any]] = []
        self.opened = self.closed = 0

    def __call__(self) -> Host:  # the actor's ``connect``
        self.opened += 1
        return self

    def request(self, method: str, params: dict[str, Any], timeout: float = 60) -> dict[str, Any]:  # noqa: ARG002
        if method == "listSessions":
            return {"items": self.items}
        assert params["channel"] in {"ahp-chat:/c-a", f"ahp-chat://default/{b64('x')}", "ahp-chat:/c-c"}
        return {"snapshot": {"state": copy.deepcopy(self.chat)}}

    def dispatch(self, channel: str, action: dict[str, Any]) -> int:  # noqa: ARG002 - one chat
        self.actions.append(action)
        kind = action["type"]
        if kind == "chat/turnCancelled" and not self.runs_on:
            self.chat["activeTurn"] = None
        elif kind == "chat/pendingMessageSet" and action["kind"] == "steering":
            self.chat["steeringMessage"] = {"id": action["id"], "message": action["message"]}
        elif kind == "chat/pendingMessageSet":
            self.chat.setdefault("queuedMessages", []).append({"id": action["id"], "message": action["message"]})
        elif kind == "chat/pendingMessageRemoved" and not self.holds:
            self.chat.pop("steeringMessage", None)
            self.chat["queuedMessages"] = [m for m in self.chat.get("queuedMessages", []) if m["id"] != action["id"]]
        return len(self.actions)

    def next_event(self, timeout: float) -> None:
        self.clock.t += timeout

    def close(self) -> None:
        self.closed += 1


class Bound:
    """The bound's sleep: it ends only when the test lets it."""

    def __init__(self) -> None:
        self.up = asyncio.Event()

    async def sleep(self, _seconds: float) -> None:
        await self.up.wait()


def answering(category: str) -> spotter.Judge:
    async def look(_card: dict[str, Any], _ctx: spotter.Context, spend: credit_meter.Meter) -> str:
        spend.part().ended(None, confirmed=True)
        return json.dumps({"category": category, "note": "Run the tests first.", "evidence": ["e1"]})

    return look


def asked(eid: str) -> dict[str, Any]:
    return {"type": "user.message", "id": eid, "data": {"content": "fix the bug"}}


def chat(tmp_path: Path, host: Host, session: str = "s-a", category: str = "course-and-constraints",
         bound: Bound | None = None) -> chat_acts.ChatActor:  # fmt: skip
    """A chat's real Spotter in the steered arm, acting through a ``ChatActor`` on *host*; its owner's turn begun."""
    db = store(tmp_path, *ROWS)
    base = spotter.Context(project="", change="", step="chat", looks=("plan", "hand-off"), sample_rate=0,
                           verbose=False, model="m", effort="", limit=0.75, actions=ACTIONS, arm="steered",
                           cap=2)  # fmt: skip
    spot = spotter.Spotter(base, lambda: session, answering(category))
    actor = chat_acts.ChatActor(session, spot, db=db, connect=host, clock=host.clock,
                                sleep=(bound or Bound()).sleep)  # fmt: skip
    spot.ctx = dataclasses.replace(spot.ctx, act=actor)
    spot.take(asked("u-1"))
    return actor


def act_of(actor: chat_acts.ChatActor) -> acts.Act:
    """The latest act written: each scenario here acts once."""
    return list(acts.acts(actor.spot.folder).values())[-1]


async def acted(actor: chat_acts.ChatActor, look: str = "plan", category: str = "course-and-constraints",
                ) -> tuple[spotter.Record, acts.Act, asyncio.Future[None]]:  # fmt: skip
    """A finding of *category* at a *look* of the owner's turn: its act written and dispatched, as the Spotter does."""
    record = actor.spot._record(look, 1.0, {"call": "x", "turn": "u-1"}, category=category,  # noqa: SLF001
                                note="Run the tests first.")  # fmt: skip
    act = acts.decide(record, look, actor.spot.ctx, 0, {})
    acts.write(actor.spot.folder, act)
    return record, act, asyncio.ensure_future(actor(record, act))


def note(act: acts.Act) -> dict[str, Any]:
    return {"type": "user.message", "id": "u-9", "data": {"content": f"{act.token} Run the tests first."}}


async def until(test: Any) -> None:
    for _ in range(500):
        if test():
            return
        await asyncio.sleep(0.01)
    raise AssertionError


def test_only_the_one_chat_the_store_names_for_the_session_is_acted_on(tmp_path) -> None:
    async def main(session: str) -> tuple[Host, acts.Act]:
        host = Host(Clock())
        actor = chat(tmp_path / session, host, session)
        actor.spot.look("plan", 1.0, {"kind": "plan", "call": "x"})
        if session != "s-x":
            await until(lambda: host.actions)
            actor.seen(note(act_of(actor)))
        await actor.spot.drain()
        return host, act_of(actor)

    for session in ("s-a", "s-b", "s-c", "s-x"):
        (tmp_path / session).mkdir()
    assert chat_acts.chat_of("s-a", store(tmp_path, *ROWS)) == (
        "copilotcli:/aaa", f"ahp-chat://c-a/{b64('copilotcli:/aaa')}")  # never s-ab's, in the same folder  # fmt: skip
    host, act = asyncio.run(main("s-a"))
    assert (host.actions[0]["kind"], act.delivery) == ("steering", "delivered")  # on ahp-chat:/c-a, as the host lists
    host, act = asyncio.run(main("s-b"))  # a default chat, listed under the host's own session URI
    assert (host.actions[0]["kind"], act.delivery) == ("steering", "delivered")
    host, act = asyncio.run(main("s-c"))  # a default chat the host lists by its own uuid, as its session's default
    assert (host.actions[0]["kind"], act.delivery) == ("steering", "delivered")
    host, act = asyncio.run(main("s-x"))
    assert (host.opened, host.actions) == (0, [])
    assert (act.delivery, act.error) == ("failed", "ChatError: no exact chat for session s-x: 0 matches")


def test_steer_stop_and_stop_resume_cancel_the_turn_running_then_and_send_in_order(tmp_path) -> None:
    async def main(category: str) -> tuple[Host, acts.Act]:
        host = Host(Clock(), active="t-2")  # the finding saw t-1; a steer the host took shows as t-2
        actor = chat(tmp_path / category, host, category=category)
        _, act, sending = await acted(actor, "plan", category)
        if act.act != "stop-and-ask":
            await until(lambda: host.actions and host.actions[-1]["type"] == "chat/pendingMessageSet")
            actor.seen(note(act))
        await sending
        assert host.opened == host.closed == 1
        return host, act_of(actor)

    for category in ACTIONS:
        (tmp_path / category).mkdir()
    host, act = asyncio.run(main("course-and-constraints"))
    [steer] = host.actions
    assert (steer["kind"], steer["message"], act.delivery) == (
        "steering", {"text": f"{act.token} Run the tests first.", "origin": {"kind": "user"}}, "delivered")  # fmt: skip
    host, act = asyncio.run(main("outside-state-changes"))
    cancel, resume = host.actions
    assert cancel == {"type": "chat/turnCancelled", "turnId": "t-2", "duration": 0}
    assert (resume["kind"], resume["message"]["model"], act.delivery) == ("queued", MODEL, "delivered")
    host, act = asyncio.run(main("irreversible-harm"))
    assert (host.actions, act.act, acts.joined(act)["acted"]) == (
        [{"type": "chat/turnCancelled", "turnId": "t-2", "duration": 0}], "stop-and-ask", "stopped")  # fmt: skip


def test_a_stop_the_host_does_not_confirm_sends_no_note_and_stays_unconfirmed(tmp_path) -> None:
    async def main() -> tuple[Host, acts.Act]:
        host = Host(Clock(), runs_on=True)
        actor = chat(tmp_path, host, category="outside-state-changes")
        *_, sending = await acted(actor, "plan", "outside-state-changes")
        await sending
        return host, act_of(actor)

    host, act = asyncio.run(main())
    assert [a["type"] for a in host.actions] == ["chat/turnCancelled"]
    assert (act.delivery, act.error) == (
        "unconfirmed", "the host still runs turn t-2 10 s after its cancel; the note was not sent")  # fmt: skip


@pytest.mark.parametrize(("holds", "said"), [
    (False, "not taken within 60 s; withdrawn: the host no longer holds it"),
    (True, "not taken within 60 s; its withdrawal is not confirmed: the host still holds it"),
])  # fmt: skip
def test_a_steer_the_log_never_shows_is_withdrawn_and_unconfirmed(tmp_path, holds, said) -> None:
    async def main() -> tuple[Host, acts.Act]:
        host, bound = Host(Clock(), holds=holds), Bound()
        actor = chat(tmp_path, host, bound=bound)
        *_, sending = await acted(actor)
        await until(lambda: host.actions)
        assert act_of(actor).delivery == "pending"  # sent, not yet shown
        bound.up.set()
        await sending
        return host, act_of(actor)

    host, act = asyncio.run(main())
    steer, withdrawn = host.actions
    assert withdrawn == {"type": "chat/pendingMessageRemoved", "kind": "steering", "id": steer["id"]}
    assert (act.delivery, act.error) == ("unconfirmed", said)


def test_a_note_whose_turn_was_superseded_or_ended_expires_unsent(tmp_path) -> None:
    async def main(*, newer: bool) -> tuple[Host, acts.Act]:
        host = Host(Clock(), active="" if not newer else "t-2")
        actor = chat(tmp_path / str(newer), host)
        if newer:
            actor.spot.take(asked("u-2"))  # the owner wrote again before the note went
        *_, sending = await acted(actor)
        await sending
        return host, act_of(actor)

    (tmp_path / "True").mkdir()
    (tmp_path / "False").mkdir()
    host, act = asyncio.run(main(newer=True))
    assert (host.opened, act.delivery, act.error) == (0, "expired", "a newer requester message superseded its turn")
    host, act = asyncio.run(main(newer=False))
    assert (host.actions, act.delivery, act.error) == ([], "expired", "the turn had ended before the note was sent")


def test_a_discretionary_stop_and_resume_whose_turn_ended_expires_and_never_starts_a_turn(tmp_path) -> None:
    async def main() -> tuple[Host, acts.Act]:
        host = Host(Clock(), active="")  # the chat's turn ended before the slow look's act
        actor = chat(tmp_path, host, category="outside-state-changes")
        *_, sending = await acted(actor, "plan", "outside-state-changes")
        await asyncio.wait_for(sending, 1)
        return host, act_of(actor)

    host, act = asyncio.run(main())
    assert (host.actions, act.act, act.delivery) == ([], "stop-and-resume", "expired")
    assert act.error == "the turn had ended before the note was sent"


@pytest.mark.parametrize(("look", "category", "active", "kind"), [
    ("plan", "course-and-constraints", "t-2", "steering"),
    ("hand-off", "hand-off-fitness", "", "queued"),
])  # fmt: skip
def test_a_pending_note_a_newer_requester_message_supersedes_is_withdrawn_and_expires(
    tmp_path, look, category, active, kind
) -> None:
    async def main() -> tuple[Host, acts.Act]:
        host = Host(Clock(), active=active)
        actor = chat(tmp_path, host, category=category)
        *_, sending = await acted(actor, look, category)
        await until(lambda: actor.waiting)  # sent; the log has not shown it
        actor.spot.take(asked("u-2"))  # the owner wrote again, as the follower reads it
        actor.seen(asked("u-2"))
        await asyncio.wait_for(sending, 1)
        return host, act_of(actor)

    host, act = asyncio.run(main())
    sent, withdrawn = host.actions
    assert withdrawn == {"type": "chat/pendingMessageRemoved", "kind": kind, "id": sent["id"]}
    assert (act.delivery, act.error) == (
        "expired", "a newer requester message superseded its turn; withdrawn: the host no longer holds it")  # fmt: skip


def test_a_note_a_newer_requester_message_supersedes_while_it_is_sent_is_withdrawn_and_expires(tmp_path) -> None:
    class Slow(Host):
        """The host, holding the note's dispatch until the test lets it finish."""

        def __init__(self, clock: Clock) -> None:
            super().__init__(clock)
            self.sending, self.gate = threading.Event(), threading.Event()

        def dispatch(self, channel: str, action: dict[str, Any]) -> int:
            if action["type"] == "chat/pendingMessageSet":
                self.sending.set()
                self.gate.wait(5)
            return super().dispatch(channel, action)

    async def main() -> tuple[Host, acts.Act]:
        host, bound = Slow(Clock()), Bound()
        actor = chat(tmp_path, host, bound=bound)
        *_, sending = await acted(actor)
        await until(host.sending.is_set)  # the host is taking the note; its token is not waited on yet
        actor.spot.take(asked("u-2"))  # the owner wrote again, as the follower reads it
        actor.seen(asked("u-2"))
        host.gate.set()
        await asyncio.sleep(0.05)
        bound.up.set()  # the log never shows the note
        await asyncio.wait_for(sending, 1)
        return host, act_of(actor)

    host, act = asyncio.run(main())
    sent, withdrawn = host.actions
    assert withdrawn == {"type": "chat/pendingMessageRemoved", "kind": "steering", "id": sent["id"]}
    assert (act.delivery, act.error) == (
        "expired", "a newer requester message superseded its turn; withdrawn: the host no longer holds it")  # fmt: skip


def test_an_expired_note_does_not_count_toward_the_cap(tmp_path) -> None:
    async def main() -> chat_acts.ChatActor:
        actor = chat(tmp_path, Host(Clock(), active=""))  # the turn ended before the note went
        *_, sending = await acted(actor)
        await sending
        return actor

    actor = asyncio.run(main())
    act = act_of(actor)
    assert (act.delivery, acts.counts(actor.spot.folder, act.session, act.scope)[0]) == ("expired", 0)


def test_a_hand_off_note_is_queued_after_its_turn_and_delivered_once_the_log_shows_its_token(tmp_path) -> None:
    async def main() -> tuple[Host, list[str]]:
        host = Host(Clock(), active="")  # the turn ended with the reply the look judged
        actor = chat(tmp_path, host, category="hand-off-fitness")
        _, act, sending = await acted(actor, "hand-off", "hand-off-fitness")
        await until(lambda: host.actions)
        said = [act_of(actor).delivery]
        actor.seen({"type": "user.message", "data": {"content": "[OwlBear Spotter note other] Another note."}})
        await asyncio.sleep(0.05)
        said.append(act_of(actor).delivery)
        actor.seen(note(act))
        await sending
        return host, [*said, act_of(actor).delivery]

    host, said = asyncio.run(main())
    [queued] = host.actions
    assert (queued["type"], queued["kind"]) == ("chat/pendingMessageSet", "queued")
    assert said == ["pending", "pending", "delivered"]


def test_a_note_whose_wait_for_the_log_the_follower_stops_stays_unconfirmed_and_keeps_its_cap_slot(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(spotter, "DRAIN", 0.1)

    async def main() -> chat_acts.ChatActor:
        host = Host(Clock())
        actor = chat(tmp_path, host)
        actor.spot.look("plan", 1.0, {"kind": "plan", "call": "x"})
        await until(lambda: actor.waiting)  # sent; the log has not shown it
        await actor.spot.drain()  # the follower stops reading the chat
        return actor

    actor = asyncio.run(main())
    assert spotter.WORK.settled(5)
    act = act_of(actor)
    assert (act.act, act.delivery, act.error) == (
        "steer", "unconfirmed",
        "the follower stopped reading the chat before its log showed it; its withdrawal was requested")  # fmt: skip
    assert acts.counts(actor.spot.folder, act.session, act.scope)[0] == 1


def test_a_note_whose_wait_the_follower_stops_is_withdrawn_on_the_spotters_thread(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(spotter, "DRAIN", 0.1)

    async def main() -> tuple[Host, chat_acts.ChatActor]:
        host = Host(Clock())
        actor = chat(tmp_path, host)
        actor.spot.look("plan", 1.0, {"kind": "plan", "call": "x"})
        await until(lambda: actor.waiting)
        await actor.spot.drain()
        return host, actor

    host, actor = asyncio.run(main())
    assert spotter.WORK.settled(5)
    steer, withdrawn = host.actions
    assert withdrawn == {"type": "chat/pendingMessageRemoved", "kind": "steering", "id": steer["id"]}
    assert (host.opened, host.closed) == (2, 2)
    assert act_of(actor).delivery == "unconfirmed"  # never claimed withdrawn: nothing waited for the host's answer
