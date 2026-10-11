"""Route C+ (TD-36): a step started by ``code chat -m <agent>`` in a Copilot-harness window, then driven over AHP.

The window gives the step VS Code's tools (P6). Delivery pins the model in the folder's settings before launch,
binds only the session it launched (nonce, folder and agent; R2), cancels the window's first turn and waits for
the host to confirm it, and runs the real turn with an explicit model and effort (TD-27, TD-32). A first turn on
any other model fails closed. ``folder`` must be a Delivery-owned worktree: the settings apply to every chat in
that folder. The step's result travels through the Delivery MCP server (TD-36), not through this module.

This driver is not wired into the runner: unattended use waits for the correlated lifecycle probe and the
user's approval-policy decision (R2, TD-29).
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from owlbear_delivery_next.ahp import ROOT

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.ahp import Json, Transport

HARNESS, DEFAULT_MODEL = "chat.defaultToCopilotHarness", "chat.defaultModel"
_TERMINAL = ("chat/turnComplete", "chat/turnCancelled", "chat/error")
FOLLOW_UP_GRACE = 10.0  # seconds to wait for a steering message to start its own turn (P8)
ACK = 10.0  # seconds to wait for the host to confirm a cancel or a config change

type End = Literal[
    "complete",
    "cancelled",
    "error",
    "timeout",
    "stopped",
    "closed",
    "unbound",
    "wrong-model",
    "config-refused",
    "settings-refused",
    "cancel-unconfirmed",
    "busy",
    "user-turn",
    "steering-unrun",
]


class SettingsError(ValueError):
    """The worktree's VS Code settings cannot be updated safely."""


def write_window_settings(folder: Path, model: str) -> None:
    """Pin the Copilot harness and the step's model for the window of ``folder`` before ``code chat`` runs.

    Other keys are kept. A settings file that is not plain JSON (comments, trailing commas) is left alone and
    the step fails closed, because a rewrite would drop the user's content.
    """
    if not model.strip() or model.strip().lower() == "auto":
        raise SettingsError("the step model must be named; auto is never used (TD-32)")  # noqa: EM101, TRY003
    path = folder / ".vscode" / "settings.json"
    current: dict[str, Any] = {}
    if path.exists():
        try:
            current = json.loads(path.read_text())
        except ValueError as exc:
            raise SettingsError(f"{path} is not plain JSON; set {DEFAULT_MODEL} by hand") from exc  # noqa: EM102,TRY003
        if not isinstance(current, dict):
            raise SettingsError(f"{path} is not a JSON object")  # noqa: EM102, TRY003
    current |= {HARNESS: True, DEFAULT_MODEL: model}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2) + "\n")


@dataclass(frozen=True)
class StepSpec:
    """One VS Code step: where, which agent, which model and effort, what to do, and the session config."""

    folder: Path
    agent: str
    model: str
    effort: str
    prompt: str
    config: Json = field(default_factory=dict)  # e.g. autoApprove or sandboxEnabled; the user's choice (TD-29)
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def bootstrap(self) -> str:
        """The ``code chat`` prompt; its nonce identifies the session Delivery may act on."""
        return f"OwlBear step {self.nonce}: wait for Delivery's instructions."


@dataclass(frozen=True)
class ToolCall:
    """One tool call that waits for Delivery's confirmation."""

    name: str
    input: str
    client: str | None


@dataclass
class Control:
    """The watcher's levers while a step runs: stop it, or steer it."""

    stop: threading.Event = field(default_factory=threading.Event)
    steering: queue.Queue[str] = field(default_factory=queue.Queue)


@dataclass
class Outcome:
    """How the step ended and what it touched; the result itself arrives through the Delivery MCP server."""

    end: End
    detail: str = ""
    session: str | None = None
    chat: str | None = None
    turns: list[str] = field(default_factory=list)
    tools: dict[str, str] = field(default_factory=dict)  # tool call id -> tool name, in call order
    denied: list[str] = field(default_factory=list)
    usage: Json | None = None
    cancel_confirmed: bool | None = None  # set when Delivery cancelled a turn: did the host confirm it?


def launch_code_chat(args: list[str], cwd: Path) -> None:
    """Start ``code chat``; it returns once the window has the prompt."""
    subprocess.Popen(args, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603


def _action_in(ev: Json | None, chat: str) -> Json:
    """The action of an event on ``chat``; empty for anything else."""
    if not ev or ev.get("method") != "action" or (ev.get("params") or {}).get("channel") != chat:
        return {}
    return ev["params"].get("action") or {}


def _ended(out: Outcome, action: Json) -> None:
    kind = action.get("type")
    out.end = {"chat/turnComplete": "complete", "chat/turnCancelled": "cancelled"}.get(str(kind), "error")
    out.detail = json.dumps(action.get("part") or action.get("error") or "")[:300] if out.end == "error" else ""


@dataclass(frozen=True)
class Hooks:
    """The step's contact with the machine; tests replace them."""

    launch: Callable[[list[str], Path], None] = launch_code_chat
    clock: Callable[[], float] = time.monotonic
    settings: Callable[[Path, str], None] = write_window_settings


@dataclass(frozen=True)
class _Bound:
    session: str
    chat: str
    turn: Json
    active: bool


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

    def run(self, control: Control, limit: float, bind_limit: float = 60) -> Outcome:  # noqa: PLR0911 - one guard each
        """Pin, launch, bind, cancel the bootstrap, check the model, configure, run; act only on the bound session."""
        if control.stop.is_set():
            return Outcome("stopped", "stopped before launch")
        try:
            self.settings(self.spec.folder, self.spec.model)
        except SettingsError as exc:
            return Outcome("settings-refused", str(exc))
        before = self._sessions()
        self.launch(["code", "chat", "-m", self.spec.agent, self.spec.bootstrap], self.spec.folder)
        bound = self._bind(before, self.clock() + bind_limit)
        if bound is None:
            return Outcome("unbound", "no single session matched nonce, folder and agent")
        out = Outcome("complete", session=bound.session, chat=bound.chat)
        if bound.active and not self._cancel(out, bound.turn["id"]):
            out.end, out.detail = "cancel-unconfirmed", "the window's first turn did not stop"
            return out
        first = ((bound.turn.get("message") or {}).get("model") or {}).get("id")
        if first != self.spec.model:
            out.end, out.detail = "wrong-model", f"window started on {first}, step needs {self.spec.model}"
            return out
        if not self._configure(bound.session):
            out.end, out.detail = "config-refused", f"host did not apply {self.spec.config}"
            return out
        if control.stop.is_set():
            out.end = "stopped"
            return out
        if self._chat(bound.chat).get("activeTurn"):
            out.end, out.detail = "busy", "another turn runs in the bound chat"
            return out
        agent = (bound.turn.get("message") or {}).get("agent")
        self._turn(out, agent, control, self.clock() + limit)
        return out

    def _sessions(self) -> list[Json]:
        return self.conn.request("listSessions", {"channel": ROOT}).get("items", [])

    def _chat(self, chat: str) -> Json:
        return self.conn.request("subscribe", {"channel": chat})["snapshot"]["state"]

    def _bind(self, before: list[Json], deadline: float) -> _Bound | None:
        known = {s["resource"] for s in before}
        folder = self.spec.folder.resolve().as_uri()
        suffix = f"/{self.spec.agent}.agent.md"
        while self.clock() < deadline:
            found: list[_Bound] = []
            for s in self._sessions():
                if s["resource"] in known or folder not in (s.get("workingDirectories") or []):
                    continue
                chat = s.get("defaultChat")
                state = self.conn.request("subscribe", {"channel": chat})["snapshot"]["state"] if chat else {}
                active = state.get("activeTurn")
                turn = active or next(iter(state.get("turns") or []), None)
                msg = (turn or {}).get("message") or {}
                uri = (msg.get("agent") or {}).get("uri") or ""
                if turn and self.spec.nonce in (msg.get("text") or "") and uri.endswith(suffix):
                    found.append(_Bound(s["resource"], chat, turn, active is not None))
            if len(found) == 1:
                return found[0]
            if len(found) > 1:
                return None  # ambiguous: act on nothing (R2)
            self.conn.next_event(0.1)
        return None

    def _cancel(self, out: Outcome, turn: str) -> bool:
        """Cancel ``turn`` and wait until the host no longer runs it."""
        chat = out.chat or ""
        self.conn.dispatch(chat, {"type": "chat/turnCancelled", "turnId": turn, "duration": 0})
        deadline = self.clock() + ACK
        while self.clock() < deadline:
            if (self._chat(chat).get("activeTurn") or {}).get("id") != turn:
                out.cancel_confirmed = True
                return True
            self.conn.next_event(0.2)
        out.cancel_confirmed = False
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

    def _start(self, out: Outcome, agent: Json | None, text: str) -> None:
        turn = str(uuid.uuid4())
        message: Json = {
            "text": text,
            "origin": {"kind": "user"},
            "model": {"id": self.spec.model, "config": {"thinkingLevel": self.spec.effort}},
        }
        if agent:
            message["agent"] = agent
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        self.conn.dispatch(
            out.chat or "", {"type": "chat/turnStarted", "turnId": turn, "startedAt": stamp, "message": message}
        )
        out.turns.append(turn)

    def _turn(self, out: Outcome, agent: Json | None, control: Control, deadline: float) -> None:
        """Follow the turn and each steering follow-up; a turn Delivery did not ask for ends Delivery's part."""
        chat = out.chat or ""
        self._start(out, agent, self.spec.prompt)
        pending: list[str] = []  # steering texts sent but not yet started as a turn, oldest first
        running, grace = True, None
        while True:
            if self._halted(out, control, deadline, running=running):
                return
            pending += self._steer(chat, control)
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
        """On stop or timeout, cancel the running turn and wait for the host to confirm it."""
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

    def _steer(self, chat: str, control: Control) -> list[str]:
        sent: list[str] = []
        while not control.steering.empty():
            text = control.steering.get_nowait()
            message = {"text": text, "origin": {"kind": "user"}}
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
            out.usage = action.get("usage")
        elif kind == "chat/toolCallReady" and not action.get("confirmed"):
            call = ToolCall(
                name=out.tools.get(call_id, ""),
                input=str(action.get("toolInput") or "")[:2000],
                client=(action.get("contributor") or {}).get("clientId"),
            )
            allowed = self.approve(call)
            if not allowed:
                out.denied.append(call.name)
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
