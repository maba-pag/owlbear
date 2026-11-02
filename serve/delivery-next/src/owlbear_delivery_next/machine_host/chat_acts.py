"""How the Spotter acts in a VS Code chat (Improvement design §4, "Live delivery"; #717), over VS Code's agent host.

The chats follower (``machine_host.chats``) follows only chats VS Code's agent host runs (``client_name`` ``VSCODE``
in the session's ``workspace.yaml``): a terminal ``copilot`` session has no host OwlBear can reach. Each followed chat's
Spotter acts through a ``ChatActor``:

- the chat is the one VS Code's own store (``agent-host.db``, read-only) names for the Copilot session, and only when
  exactly one does (``chat_of``); its channel is the one the host lists for it then (``channel``: the store keeps
  another form of its URI);
- ``steer``: a ``steering`` pending message, which the host injects into the running turn;
- ``stop-and-resume``: the turn running at that moment is cancelled (a steer the host took shows as a new turn, so
  never the turn the finding saw) and, once the host no longer runs it, the note is ``queued``: it starts the next; a
  discretionary one whose turn had already ended expires, as an idle steer does, so no look restarts a finished chat;
- ``stop-and-ask`` (and ``ask``, a repeat's escalation): that turn is cancelled; the act line carries the question
  for the Improvement page;
- at a hand-off the turn has ended, so any other note is ``queued``.

Every note starts with its act's token (``acts.TOKEN``), so no reader takes it for the owner's. A discretionary note
(``acts.DISCRETIONARY``) whose requester turn a newer requester message superseded, or whose turn has ended (a
hand-off's note excepted), is not sent: ``expired``. A sent note is ``delivered`` once the follower reads its
``user.message`` in the chat's log (``seen``); one the log does not show within ``BOUND`` seconds is withdrawn while
the host still holds it, and recorded ``unconfirmed``, saying whether the host's state shows it gone. A newer requester
message read while a discretionary or hand-off note is sent or waits supersedes it the same way: withdrawn, it is
``expired``, never delivered into the new turn; one the host had taken or still holds stays ``unconfirmed``. A note
whose wait the follower stops (it ends, or stops following the chat) is ``unconfirmed``: its withdrawal goes to the
Spotter's own threads, and nothing waits to say whether it took. A stop is
delivered once the host no longer runs the cancelled turn, else ``unconfirmed``. What raises (no exact chat, no
agent host) goes to the Spotter, which keeps it on the act as ``failed``.

The host's calls block, so they run on a worker thread, never on the follower's loop, each phase on a connection of
its own, closed at its end: a connection kept open would queue every action of the owner's chat unread.
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from owlbear_delivery_next.commands import chat_client
from owlbear_delivery_next.improvement import acts, chatlogs, spotter
from owlbear_delivery_next.improvement.events import NOTE, main_agent, requester
from owlbear_delivery_next.runtimes import ahp
from owlbear_delivery_next.workflow_steps.watched import CONFLICT

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from owlbear_delivery_next.runtimes.ahp import Json, Transport

VSCODE = "vscode-agent-host"  # ``client_name`` of a chat VS Code's agent host runs
TERMINAL = frozenset({"github/cli", "github/autopilot"})  # the ``copilot`` command's sessions
BOUND = 60.0  # seconds a note may take to show in the chat's log
ACK = 10.0  # seconds the host may take to show a cancel or a withdrawal
GONE = "VS Code's agent host is not running"
ASKS = frozenset({"stop-and-ask", "ask"})
SUPERSEDED = "a newer requester message superseded its turn"
CHATS = "SELECT owner_session_uri, chat_uri, provider_data FROM chats_v2 WHERE tombstoned = 0 AND provider_data LIKE ?"


def store() -> Path:
    """VS Code's agent-host store, where it keeps each chat's Copilot session."""
    return Path.home() / "Library/Application Support/Code/User/globalStorage/agent-host.db"


class ChatError(RuntimeError):
    """The chat to act on is not known for certain."""


def why_not(client: str) -> str:
    """Why a chat whose ``client_name`` is *client* is not followed."""
    if client in TERMINAL:
        return "not followed: terminal chat"
    return f"not followed: its client is {client or 'not named'}, not VS Code's agent host"


class Metadata:
    """Each session's ``workspace.yaml`` as last read: its folder and client, read again whenever the file changes."""

    def __init__(self) -> None:
        self.kept: dict[str, tuple[tuple[int, ...], str, str]] = {}  # a session: its file's stamp, folder, client

    def workspace(self, folder: Path) -> str:
        """``chatlogs.workspace``, read again whenever the file or its metadata changes; never kept when unreadable."""
        try:
            st = (folder / "workspace.yaml").stat()
        except OSError:
            self.kept.pop(folder.name, None)
            return ""
        stamp = (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)  # ctime: its permissions changed too
        if (kept := self.kept.get(folder.name)) is not None and kept[0] == stamp:
            return kept[1]
        data = chatlogs.metadata(folder)
        if isinstance(cwd := data.get("cwd"), str) and cwd:
            self.kept[folder.name] = (stamp, cwd, str(data.get("client_name") or ""))
            return cwd
        self.kept.pop(folder.name, None)
        return ""

    def client(self, session: str) -> str:
        """The ``client_name`` of *session*, whose folder ``workspace`` read."""
        return self.kept[session][2]


def chat_of(session: str, db: Path | None = None) -> tuple[str, str]:
    """The host's session and chat URIs, as VS Code's store keeps them, of the Copilot session *session*.

    The store's ``chats_v2`` holds every chat, a session's default one too (its older ``session_chats`` misses those);
    it is opened read-only. Raises ``ChatError`` unless exactly one chat names the session, and ``sqlite3.Error`` when
    the store cannot be read.
    """
    path = db or store()
    with contextlib.closing(sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)) as conn:
        rows = conn.execute(CHATS, (f"%{session}%",)).fetchall()
    found = {(owner, chat) for owner, chat, data in rows if _sdk(data) == session}
    if len(found) != 1:
        msg = f"no exact chat for session {session}: {len(found)} matches"
        raise ChatError(msg)
    return found.pop()


def _sdk(data: str | None) -> str:
    try:
        said = json.loads(data or "")
    except ValueError:
        return ""
    return str(said.get("sdkSessionId") or "") if isinstance(said, dict) else ""


def channel(conn: Transport, owner: str, chat: str) -> str:
    """The channel the host lists now for the store's *chat* of session *owner*.

    The store keeps ``ahp-chat://<id>/<session>`` and ``ahp-chat://default/<session>``; the host lists a chat as
    ``ahp-chat:/<id>``, and a default chat under the session's own URI, which may differ from the store's (traced
    2026-11-02).
    """
    sid = owner.split(":/", 1)[-1]
    head = chat.removeprefix("ahp-chat://").split("/", 1)[0]
    items = conn.request("listSessions", {"channel": ahp.ROOT}).get("items") or []
    listed = [c.get("resource", "") for s in items if s.get("resource", "").split(":/", 1)[-1] == sid
              for c in s.get("chats") or []]  # fmt: skip
    found = [c for c in listed if (c.startswith("ahp-chat://default/") if head == "default" else
                                   c in {chat, f"ahp-chat:/{head}"})]  # fmt: skip
    if len(found) != 1:
        msg = f"the agent host lists {len(found)} chats for {chat} of session {owner}, not one"
        raise ChatError(msg)
    return found[0]


def opened() -> Transport:
    """A connection to VS Code's running agent host; VS Code is never started for it."""
    if (entry := ahp.endpoint()) is None:
        raise ahp.HostError(GONE)
    try:
        return ahp.connect(entry, f"owlbear-spotter-{uuid.uuid4().hex[:8]}")
    except OSError as exc:  # an endpoint left behind by a VS Code that quit
        msg = f"{GONE}: its published endpoint failed: {type(exc).__name__}: {exc}"
        raise ahp.HostError(msg) from exc


def conflicts(workspace: str, change: str) -> str:
    """The decision-conflict check of a chat's state *change*, by the host's lookup for *workspace*'s clone, as JSON.

    It goes through the running host's ``/decisions/lookup``, whose coordinator admits one lookup at a time and
    accounts its run; a busy, failed or refused lookup is kept as ``failed``, so the record stays preliminary.
    """
    question = CONFLICT.format(change=" ".join(change.split())[:800])
    said = chat_client.workspace(Path(workspace)).lookup_decisions(question)
    if "error" in said and "failed" not in said:
        said = {"failed": str(said["error"])}
    return json.dumps(said)


class ChatActor:
    """The Spotter's actuator in one VS Code chat; the follower confirms its notes (``seen``)."""

    def __init__(  # noqa: PLR0913 - the chat, its Spotter, and the seams a test fakes
        self,
        session: str,
        spot: spotter.Spotter,
        *,
        db: Path | None = None,
        connect: Callable[[], Transport] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        """Bind the Copilot session *session* and its Spotter (where acts are written); *sleep* waits ``BOUND``."""
        self.session, self.spot, self.db, self.connect = session, spot, db, connect
        self.clock, self.sleep = clock, sleep
        self.chat = ""  # the chat's channel, once resolved
        self.waiting: dict[str, asyncio.Future[str]] = {}  # a note's token: ``seen``, or ``superseded``
        self.yielding: set[str] = set()  # waiting tokens a newer requester message withdraws
        self.logged: set[str] = set()  # tokens the log showed before their sender waited

    async def __call__(self, record: spotter.Record, act: acts.Act) -> None:
        """Dispatch *act*, the finding of *record*; wait for the chat's log to show the note (bounded)."""
        discretionary = act.act in acts.DISCRETIONARY and not act.harm
        if discretionary and self.spot.kept.turn != record.turn:
            await self._update(record, delivery="expired", error="a newer requester message superseded its turn")
            return
        note = f"{act.token} {act.note}"
        if act.act in ASKS:
            outcome = await self._host(self._stop)
        elif record.look == "hand-off":
            outcome = await self._host(self._send, note, "queued")
        elif act.act == "stop-and-resume":
            outcome = await self._host(functools.partial(self._stop, idle=not discretionary), note)
        else:
            outcome = await self._host(functools.partial(self._send, idle=not discretionary), note, "steering")
        if isinstance(outcome, dict):
            await self._update(record, **outcome)
        else:
            await self._confirmed(record, act.token, *outcome, yields=discretionary or record.look == "hand-off")

    def seen(self, d: dict[str, Any]) -> None:
        """An event the follower read live: a note's ``user.message`` confirms it; a requester's supersedes some."""
        if requester(d) and main_agent(d):
            for token in self.yielding:
                if not (waiter := self.waiting[token]).done():
                    waiter.set_result("superseded")
            return
        content = str((d.get("data") or {}).get("content") or "")
        if d.get("type") != "user.message" or not content.startswith(NOTE) or "]" not in content:
            return
        token = content[: content.index("]") + 1]
        waiter = self.waiting.get(token)
        if waiter is None:
            self.logged.add(token)
        elif not waiter.done():
            waiter.set_result("seen")

    async def _host[T](self, work: Callable[..., T], *args: Any) -> T:  # noqa: ANN401 - the work's arguments
        """*work* on a connection of its own to the host, the chat resolved, on a worker thread."""
        return await asyncio.to_thread(self._on_host, work, *args)

    def _on_host[T](self, work: Callable[..., T], *args: Any) -> T:  # noqa: ANN401 - the work's arguments
        stored = chat_of(self.session, self.db) if not self.chat else ("", "")  # the store before any connection
        with contextlib.closing((self.connect or opened)()) as conn:
            self.chat = self.chat or channel(conn, *stored)
            return work(conn, *args)

    def _state(self, conn: Transport) -> Json:
        return conn.request("subscribe", {"channel": self.chat})["snapshot"]["state"]

    def _send(self, conn: Transport, note: str, kind: str, *, idle: bool = False) -> tuple[str, str] | dict[str, str]:
        """The note as a pending message of *kind*; a steer needs a running turn, else it is queued (*idle*) or expires.

        The turn a queued note starts keeps the chat's model, never Auto.
        """
        state = self._state(conn)
        if kind == "steering" and not state.get("activeTurn"):
            if not idle:
                return {"delivery": "expired", "error": "the turn had ended before the note was sent"}
            kind = "queued"
        mid = str(uuid.uuid4())
        message: Json = {"text": note, "origin": {"kind": "user"}}
        if kind == "queued" and (model := _model(state)):
            message["model"] = model
        conn.dispatch(self.chat, {"type": "chat/pendingMessageSet", "kind": kind, "id": mid, "message": message})
        return kind, mid

    def _stop(self, conn: Transport, note: str = "", *, idle: bool = False) -> tuple[str, str] | dict[str, str]:
        """Cancel the turn running now; once the host no longer runs it, queue *note* if there is one.

        With no turn running, *note* is queued only when *idle* allows it (harm's); else it expires, as a steer does.
        """
        turn = str((self._state(conn).get("activeTurn") or {}).get("id") or "")
        if not turn:
            if note and idle:
                return self._send(conn, note, "queued")
            if note:
                return {"delivery": "expired", "error": "the turn had ended before the note was sent"}
            return {"delivery": "expired", "error": "no turn was running to stop"}
        conn.dispatch(self.chat, {"type": "chat/turnCancelled", "turnId": turn, "duration": 0})
        deadline = self.clock() + ACK
        while (self._state(conn).get("activeTurn") or {}).get("id") == turn:
            if self.clock() >= deadline:
                left = f"the host still runs turn {turn} {ACK:.0f} s after its cancel"
                return {"delivery": "unconfirmed", "error": left + ("; the note was not sent" if note else "")}
            conn.next_event(0.2)
        return self._send(conn, note, "queued") if note else {"delivery": "delivered"}

    def _withdraw(self, conn: Transport, kind: str, mid: str) -> str:
        """Remove the pending message *mid* if the host still holds it: ``taken``, ``withdrawn`` or ``held`` then."""
        if mid not in _pending(self._state(conn)):
            return "taken"
        conn.dispatch(self.chat, {"type": "chat/pendingMessageRemoved", "kind": kind, "id": mid})
        deadline = self.clock() + ACK
        while mid in _pending(self._state(conn)):
            if self.clock() >= deadline:
                return "held"
            conn.next_event(0.2)
        return "withdrawn"

    async def _confirmed(self, record: spotter.Record, token: str, kind: str, mid: str, *, yields: bool) -> None:
        waiter = self.waiting.setdefault(token, asyncio.get_running_loop().create_future())
        if token in self.logged:
            self.logged.discard(token)
            waiter.set_result("seen")
        if yields:
            self.yielding.add(token)
            if self.spot.kept.turn != record.turn and not waiter.done():  # a newer one read while the note was sent
                waiter.set_result("superseded")
        bound = asyncio.ensure_future(self.sleep(BOUND))
        try:
            await asyncio.wait({waiter, bound}, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:  # the follower ends, or stops following the chat: never left pending
            spotter.WORK.submit(self._on_host, self._withdraw, kind, mid)  # never awaited: the cancellation goes on
            why = "the follower stopped reading the chat before its log showed it; its withdrawal was requested"
            unseen = functools.partial(acts.update, delivery="unconfirmed", error=why)
            spotter.WORK.submit(unseen, self.spot.folder, record.id)
            raise
        finally:
            bound.cancel()
            self.waiting.pop(token, None)
            self.yielding.discard(token)
        if waiter.done() and waiter.result() == "seen":
            await self._update(record, delivery="delivered")
            return
        superseded = waiter.done()
        head = SUPERSEDED if superseded else f"not taken within {BOUND:.0f} s"
        try:
            gone = await self._host(self._withdraw, kind, mid)
        except (ahp.HostError, OSError) as exc:
            await self._update(record, delivery="unconfirmed",
                               error=f"{head}; its withdrawal failed: {type(exc).__name__}: {exc}")  # fmt: skip
            return
        why = {
            "taken": f"{SUPERSEDED}, but the host had taken it already" if superseded else
                     f"the host took it, but the chat's log did not show it within {BOUND:.0f} s",
            "withdrawn": f"{head}; withdrawn: the host no longer holds it",
            "held": f"{head}; its withdrawal is not confirmed: the host still holds it",
        }[gone]  # fmt: skip
        expired = superseded and gone == "withdrawn"
        await self._update(record, delivery="expired" if expired else "unconfirmed", error=why)

    async def _update(self, record: spotter.Record, **fields: str) -> None:
        await spotter.offload(functools.partial(acts.update, self.spot.folder, record.id, **fields))


def _model(state: Json) -> Json | None:
    """The model of the chat's latest turn, as its message named it."""
    turns = [*(state.get("turns") or []), *([state["activeTurn"]] if state.get("activeTurn") else [])]
    return next((m for t in reversed(turns) if (m := (t.get("message") or {}).get("model"))), None)


def _pending(state: Json) -> set[str]:
    """The ids of the chat's pending messages: the steering one (protocol 1.0.0) and the list (1.1.0)."""
    listed = [state.get("steeringMessage") or {}, *(state.get("queuedMessages") or [])]
    return {str(m.get("id")) for m in listed if m.get("id")}
