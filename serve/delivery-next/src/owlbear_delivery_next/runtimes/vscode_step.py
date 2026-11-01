"""The owner's shaping chat in a VS Code window, driven over AHP (TD-36, TD-48, TD-83).

``code chat`` opens or reuses the window on its working directory. Delivery pins the model in the folder's settings
before launch and binds only the session it launched (nonce and folder; R2). The window's first turn is a shell-only
``!echo`` that calls no model (TD-48); Delivery confirms only that echo, waits for it to end and waits until the host
lists the chat's model, since a new window may start with none and resolve Auto (P14). The first turn names an explicit
model, effort and agent file (TD-27, TD-32); the host ignores an agent it does not list, so the chat starts no turn
unless its session lists the agent file. Nothing follows that turn or cancels it: the owner takes the chat from there.
Delivery steps never run in a window (D-01M5WG8RGCBKADW6XPGP0E2FAP). When the host rejects the chat's own settings or
first turn, matched by client id and sequence, the chat ends at once with its reason.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import unquote

from owlbear_delivery_next.runtimes.ahp import ROOT, HostError
from owlbear_delivery_next.runtimes.vscode_contract import End, Hooks, Outcome, StepSpec
from owlbear_delivery_next.runtimes.window_files import SettingsError

if TYPE_CHECKING:
    from owlbear_delivery_next.runtimes.ahp import Json, Transport

_UNSTOPPED: tuple[End, str] = ("cancel-unconfirmed", "the window's first turn did not stop")
_UNBEGUN: tuple[End, str] = ("unstarted", "the host did not start the prompt's turn")
ACK = 10.0  # seconds to wait for the host to confirm a cancel or a config change
LISTED = 10.0  # seconds to wait for the session to list the agent file; the host took 0.4 s live
BOOT = 30.0  # seconds to wait for the shell-only first turn to end
MODELS = 30.0  # seconds to wait until the host lists the chat's model; VS Code's windows sign it in (P14, #890)


def _action_in(ev: Json | None, chat: str) -> Json:
    """The action of an event on ``chat``; empty for anything else."""
    if not ev or ev.get("method") != "action" or (ev.get("params") or {}).get("channel") != chat:
        return {}
    return ev["params"].get("action") or {}


def _rejection(ev: Json | None, client: str, seq: int) -> str | None:
    """The host's reason when ``ev`` rejects the action ``client`` sent as ``seq``; None for anything else."""
    if not ev or ev.get("method") != "action":
        return None
    params = ev.get("params") or {}
    origin = params.get("origin") or {}
    if "rejectionReason" not in params or (origin.get("clientId"), origin.get("clientSeq")) != (client, seq):
        return None
    return str(params["rejectionReason"]) or "no reason given"


def shell_command(tool_input: object) -> str:
    """The shell command of a terminal tool call, whether the host sends it as text or as JSON with ``command``."""
    text = str(tool_input or "").strip()
    try:
        parsed = json.loads(text)
    except ValueError:
        return text
    return str(parsed.get("command") or "").strip() if isinstance(parsed, dict) else text


def _asks(active: Json, action: Json, boot: str) -> list[tuple[str, object]]:
    """The bootstrap's calls awaiting confirmation, from its snapshot and from the latest event.

    The snapshot matters because a request sent before Delivery subscribed is not replayed as an event.
    """
    calls = [p.get("toolCall") or p for p in active.get("responseParts") or []]
    asks = [(str(c.get("toolCallId")), c.get("toolInput")) for c in calls if c.get("status") == "pending-confirmation"]
    if action.get("turnId") == boot and action.get("type") == "chat/toolCallReady" and not action.get("confirmed"):
        asks.append((str(action.get("toolCallId")), action.get("toolInput")))
    return asks


@dataclass(frozen=True)
class _Bound:
    session: str
    chat: str
    turn: Json


class Step:
    """Open one shaping chat in its window and bind the session it launched; every host action targets that session."""

    def __init__(self, conn: Transport, spec: StepSpec, hooks: Hooks) -> None:
        """Keep the connection, the chat's spec and the machine hooks."""
        self.conn, self.spec = conn, spec
        self.launch, self.clock, self.settings = hooks.launch, hooks.clock, hooks.settings
        self.schema: Json | None = None  # the model's config properties as the host lists them
        self.agent_uri = ""  # the agent file as the session lists it; the turns name it so

    def open(self, bind_limit: float = 60) -> Outcome:
        """Start the prompt's turn in a new interactive session and leave it to the user: no following, no cancel."""
        out, bound = self._open(bind_limit)
        if bound is None or not self._ready(out, bound):
            return out
        seq = self._start(out, {"uri": self.agent_uri} if self.spec.agent else None, self.spec.prompt)
        out.end, out.detail = self._began(bound.chat, out.turns[-1], seq)
        return out

    def _began(self, chat: str, turn: str, seq: int) -> tuple[End, str]:
        """Wait, at most ``ACK`` seconds, until the chat runs or has run ``turn``, or the host rejects it."""
        deadline = self.clock() + ACK
        while True:
            state = self._chat(chat)
            ids = [(state.get("activeTurn") or {}).get("id"), *(t.get("id") for t in state.get("turns") or [])]
            if turn in ids:
                return "started", ""
            if self.clock() >= deadline:
                return _UNBEGUN
            if (why := _rejection(self.conn.next_event(0.2), self.conn.client_id, seq)) is not None:
                return "unstarted", f"the host refused the prompt's turn: {why}"

    def _open(self, bind_limit: float) -> tuple[Outcome, _Bound | None]:
        try:
            self.settings(self.spec.folder, self.spec.model)
        except SettingsError as exc:
            return Outcome("settings-refused", str(exc)), None
        before = self._sessions()
        self.launch(["code", "chat", "-m", self.spec.picker, self.spec.bootstrap], self.spec.folder)
        bound = self._bind(before, self.clock() + bind_limit)
        if bound is None:
            return Outcome("unbound", "no single session matched nonce and folder"), None
        return Outcome("complete", session=bound.session, chat=bound.chat), bound

    def _ready(self, out: Outcome, bound: _Bound) -> bool:
        if not self._booted(out, bound):
            return False
        if not self._model_listed():
            out.end, out.detail = "model-unavailable", f"the agent host does not list {self.spec.model}"
            return False
        if why := self._configure(bound.session):
            out.end, out.detail = "config-refused", why
            return False
        if not self._listed(bound.session):
            out.end, out.detail = "no-agent", f"the session does not list {self.spec.agent_uris[0]}"
            return False
        if self._chat(bound.chat).get("activeTurn"):
            out.end, out.detail = "busy", "another turn runs in the bound chat"
            return False
        return True

    def _sessions(self) -> list[Json]:
        return self.conn.request("listSessions", {"channel": ROOT}).get("items", [])

    def _chat(self, chat: str) -> Json:
        return self.conn.request("subscribe", {"channel": chat})["snapshot"]["state"]

    def _booted(self, out: Outcome, bound: _Bound) -> bool:
        """Wait for the shell-only first turn to end, confirming only its own echo; it must have billed no model."""
        boot, chat = bound.turn["id"], bound.chat
        deadline, handled = self.clock() + BOOT, set[str]()
        while (active := self._chat(chat).get("activeTurn") or {}).get("id") == boot:
            if self.clock() >= deadline:
                stuck = ("bootstrap-stuck", f"the window's first turn did not end within {BOOT:.0f} s")
                out.end, out.detail = stuck if self._cancel(out, boot) else _UNSTOPPED
                return False
            for call, command in _asks(active, _action_in(self.conn.next_event(0.2), chat), boot):
                if call in handled:
                    continue
                handled.add(call)
                mine = shell_command(command) == f"echo {self.spec.marker}"
                self._confirm(chat, {"turnId": boot, "toolCallId": call}, allowed=mine)
                if not mine:
                    other = ("bootstrap-unexpected", "the window's first turn asked to run something else")
                    out.end, out.detail = other if self._cancel(out, boot) else _UNSTOPPED
                    return False
        done = next((t for t in self._chat(chat).get("turns") or [] if t.get("id") == boot), None)
        if done is None:
            out.end, out.detail = "bootstrap-unexpected", "the window's first turn is missing from its chat"
            return False
        if billed := (done.get("usage") or {}).get("model"):
            out.end, out.detail = "bootstrap-model", f"the window's first turn called {billed}"
            return False
        return True

    def _model_listed(self) -> bool:
        """Wait, at most ``MODELS`` seconds, until the host lists the chat's model for Copilot sessions."""
        deadline = self.clock() + MODELS
        while True:
            root = self.conn.request("subscribe", {"channel": ROOT})["snapshot"]["state"]
            agents = (a for a in root.get("agents") or [] if a.get("provider") == "copilotcli")
            if found := next(
                (m for a in agents for m in a.get("models") or [] if m.get("id") == self.spec.model), None
            ):
                self.schema = (found.get("configSchema") or {}).get("properties")
                return True
            if self.clock() >= deadline:
                return False
            self.conn.next_event(0.5)

    def _listed(self, session: str) -> bool:
        """Wait, at most ``LISTED`` seconds, until the session's customizations list the chat's agent file."""
        if self.spec.agent is None:
            return True
        uris = {unquote(u) for u in self.spec.agent_uris}
        deadline = self.clock() + LISTED
        while True:
            state = self.conn.request("subscribe", {"channel": session})["snapshot"]["state"]
            kids = (k for c in state.get("customizations") or [] for k in c.get("children") or [])
            if found := next((k for k in kids if k.get("type") == "agent" and unquote(k.get("uri", "")) in uris), None):
                self.agent_uri = found["uri"]
                return True
            if self.clock() >= deadline:
                return False
            self.conn.next_event(0.2)

    def _bind(self, before: list[Json], deadline: float) -> _Bound | None:
        """The one new session in this folder whose first turn has the nonce."""
        known = {s["resource"] for s in before}
        folder = self.spec.folder.resolve().as_uri()
        while self.clock() < deadline:
            found: list[_Bound] = []
            for s in self._sessions():
                if s["resource"] in known or folder not in (s.get("workingDirectories") or []):
                    continue
                chat = s.get("defaultChat")
                state = self.conn.request("subscribe", {"channel": chat})["snapshot"]["state"] if chat else {}
                turn = state.get("activeTurn") or next(iter(state.get("turns") or []), None)
                if turn and self.spec.nonce in ((turn.get("message") or {}).get("text") or ""):
                    found.append(_Bound(s["resource"], chat, turn))
            if len(found) == 1:
                return found[0]
            if len(found) > 1:
                return None  # ambiguous: act on nothing (R2)
            self.conn.next_event(0.1)
        return None

    def _cancel(self, out: Outcome, turn: str) -> bool:
        """Cancel ``turn`` and wait, at most ``ACK`` seconds, until the host no longer runs it."""
        chat = out.chat or ""
        out.cancel_confirmed = False
        deadline = self.clock() + ACK
        try:
            self.conn.dispatch(chat, {"type": "chat/turnCancelled", "turnId": turn, "duration": 0})
            while (left := deadline - self.clock()) > 0:
                state = self.conn.request("subscribe", {"channel": chat}, timeout=left)["snapshot"]["state"]
                if (state.get("activeTurn") or {}).get("id") != turn:
                    out.cancel_confirmed = True
                    return True
                self.conn.next_event(0.2)
        except HostError:
            return False
        return False

    def _configure(self, session: str) -> str:
        """Apply the session's settings: '' once the host shows them, else why not."""
        if not self.spec.config:
            return ""
        # subscribe before dispatching: the host sends a rejection only to the channel's subscribers
        values = (self._chat(session).get("config") or {}).get("values") or {}
        if all(values.get(k) == v for k, v in self.spec.config.items()):
            return ""  # nothing to change, so no action whose rejection could go unread
        seq = self.conn.dispatch(session, {"type": "session/configChanged", "config": self.spec.config})
        deadline, asked = self.clock() + ACK, json.dumps(self.spec.config, sort_keys=True)
        while self.clock() < deadline:
            values = (self._chat(session).get("config") or {}).get("values") or {}
            if all(values.get(k) == v for k, v in self.spec.config.items()):
                return ""
            if (why := _rejection(self.conn.next_event(0.2), self.conn.client_id, seq)) is not None:
                return f"the host refused the settings {asked}: {why}; applied: {json.dumps(values, sort_keys=True)}"
        return (
            f"the host did not apply the settings {asked} within {ACK:.0f} s; "
            f"applied: {json.dumps(values, sort_keys=True)}; "
            "a managed policy that forces the Copilot harness or blocks Allow All may be why"
        )

    def _config(self) -> Json:
        """The effort, unless the listed model takes none, and its context size: the default tier unless long.

        The host's own default can be the long tier (1M for Claude Opus 5.5, live), so the size is always sent.
        """
        props = self.schema
        config: Json = {} if props is not None and "thinkingLevel" not in props else {"thinkingLevel": self.spec.effort}
        sizes = ((props or {}).get("contextSize") or {}).get("enum") or []
        if sizes:
            labels = (props or {})["contextSize"].get("enumDescriptions") or []
            default = next((s for s, d in zip(sizes, labels, strict=False) if d == "Default"), min(sizes))
            config["contextSize"] = max(sizes) if self.spec.context == "long" else default
        return config

    def _message(self, text: str, agent: Json | None) -> Json:
        """Every message Delivery sends names the chat's model, effort and agent, so none falls back to Auto."""
        message: Json = {
            "text": text,
            "origin": {"kind": "user"},
            "model": {"id": self.spec.model, "config": self._config()},
        }
        if agent:
            message["agent"] = agent
        return message

    def _start(self, out: Outcome, agent: Json | None, text: str) -> int:
        turn = str(uuid.uuid4())
        message = self._message(text, agent)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        seq = self.conn.dispatch(
            out.chat or "", {"type": "chat/turnStarted", "turnId": turn, "startedAt": stamp, "message": message}
        )
        out.turns.append(turn)
        return seq

    def _confirm(self, chat: str, action: Json, *, allowed: bool) -> None:
        confirm: Json = {
            "type": "chat/toolCallConfirmed",
            "turnId": action.get("turnId"),
            "toolCallId": action.get("toolCallId"),
            "approved": allowed,
        }
        confirm |= (
            {"confirmed": "user-action"}
            if allowed
            else {"reason": "denied", "reasonMessage": "Delivery policy: not allowed in the shaping chat's first turn"}
        )
        self.conn.dispatch(chat, confirm)
