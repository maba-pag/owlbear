"""Route C+ (TD-36): a step started by ``code chat`` in its folder's Copilot-harness window, then driven over AHP.

``code chat`` opens or reuses the window on its working directory, which gives the step VS Code's tools (P6).
Delivery pins the model in the folder's settings before launch and binds only the session it launched (nonce and
folder; R2). The window's first turn is a shell-only ``!echo`` that calls no model (TD-48); Delivery confirms only
that echo, waits for it to end, signs in again over a new connection and waits until the host lists the step's
model, since a new window may start with none and resolve Auto (P14). The real turn, each reminder and each steering
message carry an explicit model, effort and agent file (TD-27, TD-32). The host ignores an agent it does not list,
so the step fails closed unless the session lists the agent file. A turn billed to any other model fails closed.
``folder`` must be a Delivery-owned worktree: the settings apply to every chat in that folder. The step's result
travels through the step's MCP relay (TD-36), not through this module.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import unquote

from owlbear_delivery_next.ahp import ROOT, HostError
from owlbear_delivery_next.vscode_contract import Control, End, Hooks, Outcome, StepSpec, ToolCall
from owlbear_delivery_next.window_files import SettingsError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.ahp import Json, Transport

_TERMINAL = ("chat/turnComplete", "chat/turnCancelled", "chat/error")
_UNSTOPPED: tuple[End, str] = ("cancel-unconfirmed", "the window's first turn did not stop")
FOLLOW_UP_GRACE = 10.0  # seconds to wait for a steering message to start its own turn (P8)
ACK = 10.0  # seconds to wait for the host to confirm a cancel or a config change
LISTED = 10.0  # seconds to wait for the session to list the step's agent file; the host took 0.4 s live
BOOT = 30.0  # seconds to wait for the shell-only first turn to end
MODELS = 30.0  # seconds to wait, after signing in again, until the host lists the step's model (P14)


def _action_in(ev: Json | None, chat: str) -> Json:
    """The action of an event on ``chat``; empty for anything else."""
    if not ev or ev.get("method") != "action" or (ev.get("params") or {}).get("channel") != chat:
        return {}
    return ev["params"].get("action") or {}


def _ended(out: Outcome, action: Json) -> None:
    kind = action.get("type")
    out.end = {"chat/turnComplete": "complete", "chat/turnCancelled": "cancelled"}.get(str(kind), "error")
    out.detail = json.dumps(action.get("part") or action.get("error") or "")[:300] if out.end == "error" else ""


def _command(tool_input: object) -> str:
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
    """Run one C+ step to its end; every host action targets only the bound session."""

    def __init__(
        self,
        conn: Transport,
        spec: StepSpec,
        approve: Callable[[ToolCall], bool],
        *,
        hooks: Hooks | None = None,
    ) -> None:
        """Keep the connection, the step and the approval policy for each unconfirmed tool call."""
        self.conn, self.spec, self.approve = conn, spec, approve
        hooks = hooks or Hooks()
        self.launch, self.clock, self.settings = hooks.launch, hooks.clock, hooks.settings
        self.reconnect = hooks.reconnect
        self.opened: list[Transport] = []  # connections this step opened; it closes them when it ends

    def run(self, control: Control, limit: float, bind_limit: float = 60) -> Outcome:
        """Pin, launch, bind, let the bootstrap end, sign in again, check the model, configure, run."""
        try:
            out, bound = self._open(control, bind_limit)
            if bound is None or not self._ready(out, bound, control):
                return out
            agent = {"uri": self.spec.agent_uri}
            deadline = self.clock() + limit
            self._turn(out, agent, control, deadline, self.spec.prompt, attachments=self.spec.attachments)
            if out.end == "complete" and self.spec.reminder and not (control.stop.is_set() or control.settled.is_set()):
                self._turn(out, agent, control, deadline, self.spec.reminder)
            return out
        finally:
            for conn in self.opened:
                if close := getattr(conn, "close", None):
                    close()

    def _open(self, control: Control, bind_limit: float) -> tuple[Outcome, _Bound | None]:
        if control.stop.is_set():
            return Outcome("stopped", "stopped before launch"), None
        try:
            self.settings(self.spec.folder, self.spec.model)
        except SettingsError as exc:
            return Outcome("settings-refused", str(exc)), None
        before = self._sessions()
        if busy := self._busy(before):
            return Outcome("folder-busy", f"session {busy} still runs a turn in this folder"), None
        self.launch(["code", "chat", "-m", "agent", self.spec.bootstrap], self.spec.folder)
        bound = self._bind(before, self.clock() + bind_limit)
        if bound is None:
            return Outcome("unbound", "no single session matched nonce and folder"), None
        return Outcome("complete", session=bound.session, chat=bound.chat), bound

    def _ready(self, out: Outcome, bound: _Bound, control: Control) -> bool:  # noqa: PLR0911 - one guard each
        if not self._booted(out, bound):
            return False
        if self.reconnect:
            self.conn = self.reconnect()
            self.opened.append(self.conn)
        if not self._model_listed():
            out.end, out.detail = "model-unavailable", f"the agent host does not list {self.spec.model}"
            return False
        if not self._configure(bound.session):
            out.end, out.detail = "config-refused", f"host did not apply {self.spec.config}"
            return False
        if not self._listed(bound.session):
            out.end, out.detail = "no-agent", f"the session does not list {self.spec.agent_uri}"
            return False
        if control.stop.is_set():
            out.end = "stopped"
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
                mine = _command(command) == f"echo {self.spec.marker}"
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
        """Wait, at most ``MODELS`` seconds, until the host lists the step's model for Copilot sessions."""
        deadline = self.clock() + MODELS
        while True:
            root = self.conn.request("subscribe", {"channel": ROOT})["snapshot"]["state"]
            agents = (a for a in root.get("agents") or [] if a.get("provider") == "copilotcli")
            if any(m.get("id") == self.spec.model for a in agents for m in a.get("models") or []):
                return True
            if self.clock() >= deadline:
                return False
            self.conn.next_event(0.5)

    def _listed(self, session: str) -> bool:
        """Wait, at most ``LISTED`` seconds, until the session's customizations list the step's agent file."""
        deadline = self.clock() + LISTED
        while True:
            state = self.conn.request("subscribe", {"channel": session})["snapshot"]["state"]
            kids = (k for c in state.get("customizations") or [] for k in c.get("children") or [])
            if any(
                k.get("type") == "agent" and unquote(k.get("uri", "")) == unquote(self.spec.agent_uri) for k in kids
            ):
                return True
            if self.clock() >= deadline:
                return False
            self.conn.next_event(0.2)

    def _busy(self, sessions: list[Json]) -> str | None:
        """A session in this folder that still runs a turn, e.g. an earlier step whose runner died."""
        folder = self.spec.folder.resolve().as_uri()
        for s in sessions:
            chat = s.get("defaultChat")
            if chat and folder in (s.get("workingDirectories") or []) and self._chat(chat).get("activeTurn"):
                return s["resource"]
        return None

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

    def _configure(self, session: str) -> bool:
        if not self.spec.config:
            return True
        self.conn.dispatch(session, {"type": "session/configChanged", "config": self.spec.config})
        deadline = self.clock() + ACK
        while self.clock() < deadline:
            values = self._chat(session).get("config") or {}
            if all((values.get("values") or {}).get(k) == v for k, v in self.spec.config.items()):
                return True
            self.conn.next_event(0.2)
        return False

    def _message(self, text: str, agent: Json | None, attachments: tuple[Json, ...] = ()) -> Json:
        """Every message Delivery sends names the step's model, effort and agent, so none falls back to Auto."""
        message: Json = {
            "text": text,
            "origin": {"kind": "user"},
            "model": {"id": self.spec.model, "config": {"thinkingLevel": self.spec.effort}},
        }
        if agent:
            message["agent"] = agent
        if attachments:
            message["attachments"] = list(attachments)
        return message

    def _start(self, out: Outcome, agent: Json | None, text: str, attachments: tuple[Json, ...] = ()) -> None:
        turn = str(uuid.uuid4())
        message = self._message(text, agent, attachments)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        self.conn.dispatch(
            out.chat or "", {"type": "chat/turnStarted", "turnId": turn, "startedAt": stamp, "message": message}
        )
        out.turns.append(turn)

    def _turn(  # noqa: PLR0913 - the prompt's turn carries the step's attachments
        self,
        out: Outcome,
        agent: Json | None,
        control: Control,
        deadline: float,
        text: str,
        *,
        attachments: tuple[Json, ...] = (),
    ) -> None:
        """Follow the turn and each steering follow-up; a turn Delivery did not ask for ends Delivery's part."""
        chat = out.chat or ""
        self._start(out, agent, text, attachments)
        control.started.set()
        pending: list[str] = []  # steering texts sent but not yet started as a turn, oldest first
        running, grace = True, None
        while True:
            if self._halted(out, control, deadline, running=running):
                return
            pending += self._steer(chat, agent, control)
            if grace is not None and self.clock() >= grace:
                out.end, out.detail = "steering-unrun", f"{len(pending)} steering message(s) never ran"
                return
            ev = self.conn.next_event(0.5)
            if ev and ev.get("method") == "closed":
                out.end, out.detail = "closed", str((ev.get("params") or {}).get("error", ""))
                return
            action = _action_in(ev, chat)
            kind, turn = action.get("type"), action.get("turnId")
            if kind == "chat/turnStarted" and turn not in out.turns:
                if not self._adopt(out, action, pending):
                    return
                running, grace = True, None
            elif not kind or turn != out.turns[-1]:
                continue
            elif kind in _TERMINAL:
                _ended(out, action)
                running = False
                if not pending:
                    return
                grace = self.clock() + FOLLOW_UP_GRACE
            else:
                self._observe(out, chat, action)

    def _halted(self, out: Outcome, control: Control, deadline: float, *, running: bool) -> bool:
        """On stop, timeout or a turn billed to another model, cancel the running turn and wait for the host."""
        if out.end == "wrong-model":
            self._cancel(out, out.turns[-1])
            return True
        if not control.stop.is_set() and self.clock() < deadline:
            return False
        out.end = "stopped" if control.stop.is_set() else "timeout"
        if running:
            self._cancel(out, out.turns[-1])
        return True

    @staticmethod
    def _adopt(out: Outcome, action: Json, pending: list[str]) -> bool:
        """Follow a turn only if it is the oldest pending steering message (P8); any other turn is the user's."""
        if not pending or (action.get("message") or {}).get("text") != pending[0]:
            out.end, out.detail = "user-turn", "a turn Delivery did not start began in the bound chat"
            return False
        pending.pop(0)
        out.turns.append(action["turnId"])
        return True

    def _steer(self, chat: str, agent: Json | None, control: Control) -> list[str]:
        """Send queued steering; each text carries a step-unique tag so a user's identical text never matches."""
        sent: list[str] = []
        while not control.steering.empty():
            tag = uuid.uuid4().hex[:8]
            text = f"{control.steering.get_nowait()}\n\n(OwlBear steering {self.spec.nonce}-{tag})"
            message = self._message(text, agent)
            self.conn.dispatch(
                chat,
                {"type": "chat/pendingMessageSet", "kind": "steering", "id": str(uuid.uuid4()), "message": message},
            )
            sent.append(text)
        return sent

    def _observe(self, out: Outcome, chat: str, action: Json) -> None:
        kind = action.get("type")
        call_id = str(action.get("toolCallId"))
        if kind == "chat/toolCallStart":
            out.tools[call_id] = str(action.get("toolName"))
        elif kind == "chat/usage":
            out.usage = action.get("usage") or {}
            billed = out.usage.get("model")
            if billed:
                spent = int(out.usage.get("inputTokens") or 0) + int(out.usage.get("outputTokens") or 0)
                out.tokens[billed] = out.tokens.get(billed, 0) + spent
            if billed and billed != self.spec.model:  # the message's model field is no proof (live probe)
                out.end, out.detail = "wrong-model", f"the turn was billed to {billed}, step needs {self.spec.model}"
        elif kind == "chat/toolCallReady" and not action.get("confirmed"):
            call = ToolCall(
                name=out.tools.get(call_id, ""),
                input=str(action.get("toolInput") or "")[:2000],
                client=(action.get("contributor") or {}).get("clientId"),
            )
            allowed = self.approve(call)
            if not allowed:
                out.denied.append(call.name)
            self._confirm(chat, action, allowed=allowed)

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
            else {"reason": "denied", "reasonMessage": "Delivery policy: not allowed in this step"}
        )
        self.conn.dispatch(chat, confirm)
