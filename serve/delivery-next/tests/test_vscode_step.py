import base64
import dataclasses
import hashlib
import json
import queue
import re
import socket
import subprocess
import tempfile
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next import ahp, sdk_adapter, session_result, step_mcp, vscode_adapter
from owlbear_delivery_next.ahp import HostError
from owlbear_delivery_next.config import Layer, resolve
from owlbear_delivery_next.models import Exit, StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.tools import Worktree
from owlbear_delivery_next.vscode_contract import Control, Hooks, Outcome, StepSpec, ToolCall
from owlbear_delivery_next.vscode_step import ACK, Step
from owlbear_delivery_next.window_files import DEFAULT_MODEL, HARNESS, SettingsError, write_window_settings

MODEL, EFFORT, AGENT = "gpt-6-luna", "max", ".github/agents/owlbear-builder.agent.md"


class FakeHost:
    """A scripted editor host: sessions appear on launch, each started turn plays its script."""

    def __init__(self, folder: Path, sessions_on_launch: list[dict], scripts: list[list[dict]]) -> None:
        self.folder, self.t = folder, 0.0
        self.items: list[dict] = []
        self.chats: dict[str, dict] = {}
        self.config: dict[str, dict] = {}
        self.on_launch, self.scripts = sessions_on_launch, scripts
        self.accept_config = True
        self.ignore_cancel = False
        self.boot_active = False  # the shell-only bootstrap turn has usually finished by binding time
        self.boot_script: list[dict] = []  # actions the bootstrap turn plays after launch
        self.models, self.models_at = [MODEL], 0.0  # models the host lists, from this clock time on
        self.schema: dict | None = None  # the listed models' configSchema
        self.reconnects, self.closed, self.twin = 0, 0, None
        self.listed = [(folder / AGENT).resolve().as_uri()]  # agent files the sessions list
        self.listed_at = 0.0  # host clock time from which the sessions list them
        self.pinned: list[tuple[Path, str]] = []
        self.sent: list[tuple[str, dict]] = []
        self.events: list[dict] = []
        self.launched: list[list[str]] = []

    def clock(self) -> float:
        return self.t

    def pin(self, folder: Path, model: str) -> None:
        write_window_settings(folder, model)
        self.pinned.append((folder, model))

    def launch(self, args: list[str], _cwd: Path) -> None:
        self.launched.append(args)
        nonce = re.search(r"OWLBEAR-(\w+)", args[-1]).group(1)
        for spec in self.on_launch:
            resource = self.add(nonce=nonce, **spec)
            if self.boot_script:
                n = resource.rsplit("s", 1)[1]
                self.play(f"ahp-chat://default/c{n}", f"boot{n}", self.boot_script)

    def reconnect(self) -> Twin:
        self.reconnects += 1
        self.twin = Twin(self)
        return self.twin

    def close(self) -> None:
        self.closed += 1

    def add(  # noqa: PLR0913 - one keyword per scripted session property
        self,
        *,
        nonce: str,
        folder: Path | None = None,
        model: str = MODEL,
        text: str | None = None,
        billed: str | None = None,
        pending: str | None = None,
    ) -> str:
        n = len(self.items)
        resource, chat = f"copilotcli:/s{n}", f"ahp-chat://default/c{n}"
        msg = {
            "text": text if text is not None else f"!echo OWLBEAR-{nonce}",
            "model": {"id": model, "config": {"thinkingLevel": "high"}},
        }
        turn = {"id": f"boot{n}", "message": msg, "usage": {"model": billed} if billed else None}
        if pending is not None:
            call = {"status": "pending-confirmation", "toolCallId": "p1", "toolInput": pending}
            turn["responseParts"] = [{"kind": "toolCall", "toolCall": call}]
        self.items.append(
            {
                "resource": resource,
                "defaultChat": chat,
                "workingDirectories": [(folder or self.folder).resolve().as_uri()],
            }
        )
        self.chats[chat] = {"activeTurn": turn if self.boot_active else None, "turns": [turn]}
        self.config[resource] = {}
        return resource

    def request(self, method: str, params: dict, timeout: float = 60) -> dict:  # noqa: ARG002
        if method == "listSessions":
            return {"items": list(self.items)}
        channel = params["channel"]
        if channel == "ahp-root://":
            listed = [{"id": m} for m in self.models] if self.t >= self.models_at else []
            listed = [m | {"configSchema": self.schema} for m in listed] if self.schema else listed
            return {"snapshot": {"state": {"agents": [{"provider": "copilotcli", "models": listed}]}}}
        if channel in self.chats:
            return {"snapshot": {"state": self.chats[channel]}}
        agents = [{"type": "agent", "uri": u} for u in self.listed] if self.t >= self.listed_at else []
        state = {
            "config": {"values": self.config[channel]},
            "customizations": [{"type": "directory", "children": agents}],
        }
        return {"snapshot": {"state": state}}

    def dispatch(self, channel: str, action: dict) -> None:
        self.sent.append((channel, action))
        kind = action["type"]
        if kind == "session/configChanged" and self.accept_config:
            self.config[channel] |= action["config"]
        elif kind == "chat/turnCancelled" and not self.ignore_cancel:
            if (self.chats[channel].get("activeTurn") or {}).get("id") == action["turnId"]:
                self.chats[channel]["activeTurn"] = None
        elif kind == "chat/turnStarted":
            self.chats[channel]["activeTurn"] = {"id": action["turnId"], "message": action["message"]}
            if self.scripts:
                self.play(channel, action["turnId"], self.scripts.pop(0))
        elif kind == "chat/toolCallConfirmed" and str(action["turnId"]).startswith("boot") and action["approved"]:
            self.chats[channel]["activeTurn"] = None  # the confirmed echo runs and the bootstrap ends
        elif kind == "chat/pendingMessageSet" and self.scripts:
            started = {"type": "chat/turnStarted", "message": action["message"]}
            self.play(channel, "follow-up", [started, *self.scripts.pop(0)])

    def play(self, chat: str, turn: str, script: list[dict]) -> None:
        for a in script:
            self.events.append({"method": "action", "params": {"channel": chat, "action": {"turnId": turn, **a}}})

    def next_event(self, timeout: float) -> dict | None:
        self.t += timeout
        if not self.events:
            return None
        ev = self.events.pop(0)
        action, chat = (ev.get("params") or {}).get("action") or {}, (ev.get("params") or {}).get("channel")
        if action.get("type") in ("chat/turnComplete", "chat/turnCancelled", "chat/error") and chat in self.chats:
            self.chats[chat]["activeTurn"] = None
        return ev

    def actions(self, kind: str) -> list[tuple[str, dict]]:
        return [(c, a) for c, a in self.sent if a["type"] == kind]


class Twin:
    """A second connection to the same fake host; it records what went through it."""

    def __init__(self, host: FakeHost) -> None:
        self.host, self.closed = host, 0
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, params: dict, timeout: float = 60) -> dict:
        self.calls.append((method, params.get("channel", "")))
        return self.host.request(method, params, timeout)

    def dispatch(self, channel: str, action: dict) -> None:
        self.calls.append((action["type"], channel))
        self.host.dispatch(channel, action)

    def next_event(self, timeout: float) -> dict | None:
        return self.host.next_event(timeout)

    def close(self) -> None:
        self.closed += 1


def spec(folder: Path, **kw: object) -> StepSpec:
    return StepSpec(
        folder=folder,
        agent=folder / AGENT,
        model=MODEL,
        effort=EFFORT,
        prompt="Check the page at 390px.",
        nonce="n0nce",
        **kw,
    )


def step(host: FakeHost, s: StepSpec, approve=lambda _c: True) -> Step:
    hooks = Hooks(launch=host.launch, clock=host.clock, settings=host.pin, reconnect=host.reconnect)
    return Step(host, s, approve, hooks=hooks)


DONE = [{"type": "chat/usage", "usage": {"model": MODEL}}, {"type": "chat/turnComplete"}]


def test_step_binds_its_session_after_a_shell_only_bootstrap_and_runs_named_model(tmp_path: Path) -> None:
    host = FakeHost(
        tmp_path,
        [{}],
        [
            [
                {"type": "chat/toolCallStart", "toolCallId": "t1", "toolName": "openBrowserPage"},
                {"type": "chat/toolCallReady", "toolCallId": "t1", "toolInput": "http://x", "confirmed": None},
                *DONE,
            ]
        ],
    )
    seen: list[ToolCall] = []
    out = step(host, spec(tmp_path, config={"sandboxEnabled": "on"}), lambda c: seen.append(c) or True).run(
        Control(), limit=60
    )

    assert out.end == "complete"
    assert host.pinned == [(tmp_path, MODEL)]
    assert json.loads((tmp_path / ".vscode" / "settings.json").read_text())[DEFAULT_MODEL] == MODEL
    assert (out.cancel_confirmed, host.reconnects) == (None, 1)
    chat = "ahp-chat://default/c0"
    calls = host.twin.calls
    assert calls.index(("subscribe", chat)) < calls.index(("chat/turnStarted", chat))
    assert (host.twin.closed, host.closed) == (1, 0)
    assert host.launched == [["code", "chat", "-m", "agent", "!echo OWLBEAR-n0nce"]]
    assert host.actions("chat/turnCancelled") == []
    assert host.config["copilotcli:/s0"] == {"sandboxEnabled": "on"}
    ((_, started),) = host.actions("chat/turnStarted")
    assert started["message"]["model"] == {"id": MODEL, "config": {"thinkingLevel": EFFORT}}
    assert started["message"]["agent"] == {"uri": (tmp_path / AGENT).resolve().as_uri()}
    assert seen == [ToolCall("openBrowserPage", "http://x", None)]
    ((_, confirm),) = host.actions("chat/toolCallConfirmed")
    assert confirm["approved"] is True
    assert out.tools == {"t1": "openBrowserPage"}
    assert out.usage == {"model": MODEL}


def test_step_sends_the_tiers_context_size_and_only_an_effort_the_model_takes(tmp_path: Path) -> None:
    sizes = {"enum": [200000, 1000000], "enumDescriptions": ["Default", "Longer sessions"], "default": 1000000}

    def config(schema: dict, context: str = "default") -> dict:
        host = FakeHost(tmp_path, [{}], [DONE])
        host.schema = schema
        step(host, spec(tmp_path, context=context)).run(Control(), limit=60)
        ((_, started),) = host.actions("chat/turnStarted")
        return started["message"]["model"]["config"]

    both = {"properties": {"thinkingLevel": {"enum": ["high", "max"]}, "contextSize": sizes}}
    assert config(both) == {"thinkingLevel": EFFORT, "contextSize": 200000}  # never the host's 1M default
    assert config(both, "long") == {"thinkingLevel": EFFORT, "contextSize": 1000000}
    assert config({"properties": {}}) == {}  # a model without efforts gets none
    assert config({}) == {"thinkingLevel": EFFORT}  # no schema listed: the effort as before


def test_step_never_touches_the_users_chats(tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    host = FakeHost(tmp_path, [{"text": "my own question"}, {"folder": other}, {}], [DONE])
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert out.end == "complete"
    assert out.session == "copilotcli:/s2"
    assert {c for c, _ in host.sent} <= {"ahp-chat://default/c2", "copilotcli:/s2"}


def test_step_acts_on_nothing_when_two_sessions_match(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}, {}], [DONE])
    out = step(host, spec(tmp_path)).run(Control(), limit=60, bind_limit=5)

    assert out.end == "unbound"
    assert host.sent == []


def test_step_ignores_sessions_that_existed_before_launch(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [], [DONE])
    host.boot_active = False
    host.add(nonce="n0nce")
    out = step(host, spec(tmp_path)).run(Control(), limit=60, bind_limit=5)

    assert out.end == "unbound"
    assert host.sent == []


def test_a_turn_billed_to_another_model_is_cancelled(tmp_path: Path) -> None:
    script = [{"type": "chat/usage", "usage": {"model": "mai-code-1.1-flash"}}, {"type": "chat/turnComplete"}]
    host = FakeHost(tmp_path, [{"model": "auto"}], [script])
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert out.end == "wrong-model"
    assert "mai-code-1.1-flash" in out.detail
    ((_, started),) = host.actions("chat/turnStarted")
    assert host.actions("chat/turnCancelled")[-1][1]["turnId"] == started["turnId"]


def test_a_bootstrap_that_called_a_model_fails_closed(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{"billed": "mai-code-1.1-flash"}], [DONE])
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert (out.end, out.detail) == ("bootstrap-model", "the window's first turn called mai-code-1.1-flash")
    assert host.actions("chat/turnStarted") == []


def test_only_the_bootstraps_own_echo_is_confirmed(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    host.boot_script = [
        {"type": "chat/toolCallReady", "toolCallId": "b1", "toolInput": "echo OWLBEAR-n0nce", "confirmed": None},
        {"type": "chat/turnComplete"},
    ]
    out = step(host, spec(tmp_path)).run(Control(), limit=60)
    ((_, confirm),) = host.actions("chat/toolCallConfirmed")[:1]
    assert (out.end, confirm["toolCallId"], confirm["approved"]) == ("complete", "b1", True)

    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    host.boot_script = [
        {"type": "chat/toolCallReady", "toolCallId": "b1", "toolInput": "rm -rf ~", "confirmed": None},
        {"type": "chat/turnComplete"},
    ]
    out = step(host, spec(tmp_path)).run(Control(), limit=60)
    ((_, confirm),) = host.actions("chat/toolCallConfirmed")
    assert (out.end, confirm["approved"], host.actions("chat/turnStarted")) == ("bootstrap-unexpected", False, [])


def test_a_pending_echo_seen_in_the_snapshot_and_as_an_event_is_confirmed_once(tmp_path: Path) -> None:
    for script in ([], [{"type": "chat/toolCallReady", "toolCallId": "p1", "toolInput": "echo OWLBEAR-n0nce"}]):
        host = FakeHost(tmp_path, [{"pending": "echo OWLBEAR-n0nce"}], [DONE])
        host.boot_active = True
        host.boot_script = script
        out = step(host, spec(tmp_path)).run(Control(), limit=60)

        confirms = [(a["turnId"], a["toolCallId"], a["approved"]) for _, a in host.actions("chat/toolCallConfirmed")]
        assert (out.end, confirms) == ("complete", [("boot0", "p1", True)])


def test_the_step_waits_until_the_host_lists_its_model_and_never_starts_without_it(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.models_at = 5.0
    out = step(host, spec(tmp_path)).run(Control(), limit=60)
    assert (out.end, len(host.actions("chat/turnStarted"))) == ("complete", 1)

    host = FakeHost(tmp_path, [{}], [DONE])
    host.models = ["mai-code-1.1-flash"]
    out = step(host, spec(tmp_path)).run(Control(), limit=60)
    assert (out.end, out.detail) == ("model-unavailable", f"the agent host does not list {MODEL}")
    assert host.actions("chat/turnStarted") == []


def test_an_agent_the_session_does_not_list_starts_no_turn(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.listed = [(Path.home() / ".copilot/agents/owlbear-builder.agent.md").as_uri()]
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert (out.end, out.detail) == ("no-agent", f"the session does not list {(tmp_path / AGENT).resolve().as_uri()}")
    assert host.actions("chat/turnCancelled") == []
    assert host.actions("chat/turnStarted") == []


def test_the_turn_waits_until_the_session_lists_the_agent(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.listed_at = 3.0
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert out.end == "complete"
    ((_, started),) = host.actions("chat/turnStarted")
    assert started["message"]["agent"] == {"uri": (tmp_path / AGENT).resolve().as_uri()}


def test_a_turn_still_running_in_the_folder_launches_nothing(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    host.add(nonce="earlier")
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert (out.end, host.launched, host.sent) == ("folder-busy", [], [])


def test_a_turn_that_ends_without_a_result_gets_one_reminder(tmp_path: Path) -> None:
    usage = {"type": "chat/usage", "usage": {"model": MODEL, "inputTokens": 100, "outputTokens": 20}}
    host = FakeHost(tmp_path, [{}], [[usage, {"type": "chat/turnComplete"}], [usage, {"type": "chat/turnComplete"}]])
    control = Control()
    out = step(host, spec(tmp_path, reminder="Call submit_result.")).run(control, limit=60)

    texts = [a["message"]["text"] for _, a in host.actions("chat/turnStarted")]
    assert texts == ["Check the page at 390px.", "Call submit_result."]
    assert (out.end, out.tokens, control.started.is_set()) == ("complete", {MODEL: 240}, True)


def test_a_stopped_turn_gets_no_reminder(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [[{"type": "chat/turnComplete"}], DONE])
    control = Control()
    original = host.next_event

    def next_event(timeout: float) -> dict | None:
        ev = original(timeout)
        if ev and ev["params"]["action"]["type"] == "chat/turnComplete":
            control.stop.set()
        return ev

    host.next_event = next_event
    step(host, spec(tmp_path, reminder="Call submit_result.")).run(control, limit=60)

    assert len(host.actions("chat/turnStarted")) == 1


def test_step_fails_closed_when_host_ignores_the_config(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.accept_config = False
    out = step(host, spec(tmp_path, config={"sandboxEnabled": "on"})).run(Control(), limit=60)

    assert out.end == "config-refused"
    assert host.actions("chat/turnStarted") == []


def test_step_denies_a_tool_call_the_policy_refuses(tmp_path: Path) -> None:
    host = FakeHost(
        tmp_path,
        [{}],
        [
            [
                {"type": "chat/toolCallStart", "toolCallId": "t1", "toolName": "bash"},
                {"type": "chat/toolCallReady", "toolCallId": "t1", "toolInput": "rm -rf /", "confirmed": None},
                {"type": "chat/toolCallReady", "toolCallId": "t2", "toolInput": "x", "confirmed": "not-needed"},
                *DONE,
            ]
        ],
    )
    out = step(host, spec(tmp_path), lambda c: c.name != "bash").run(Control(), limit=60)

    ((_, confirm),) = host.actions("chat/toolCallConfirmed")
    assert confirm["approved"] is False
    assert confirm["toolCallId"] == "t1"
    assert out.denied == ["bash"]


def test_a_stop_before_launch_launches_nothing(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    control = Control()
    control.stop.set()
    out = step(host, spec(tmp_path)).run(control, limit=60)

    assert out.end == "stopped"
    assert (host.launched, host.sent, host.pinned) == ([], [], [])


def test_auto_is_refused_before_anything_launches(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{"model": "auto"}], [DONE])
    s = StepSpec(folder=tmp_path, agent=tmp_path / AGENT, model="auto", effort=EFFORT, prompt="x", nonce="n0nce")
    out = step(host, s).run(Control(), limit=60)

    assert out.end == "settings-refused"
    assert (host.launched, host.sent) == ([], [])


def test_a_bootstrap_that_never_finishes_is_cancelled_and_starts_no_turn(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    host.ignore_cancel = True
    out = step(host, spec(tmp_path)).run(Control(), limit=60)
    assert (out.end, out.cancel_confirmed) == ("cancel-unconfirmed", False)
    assert host.actions("chat/turnStarted") == []

    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    out = step(host, spec(tmp_path)).run(Control(), limit=60)
    assert (out.end, out.cancel_confirmed) == ("bootstrap-stuck", True)
    assert host.actions("chat/turnStarted") == []


def test_a_user_turn_in_the_bound_chat_blocks_the_start(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    original = host.dispatch

    def dispatch(channel: str, action: dict) -> None:
        original(channel, action)
        if action["type"] == "session/configChanged":
            host.chats["ahp-chat://default/c0"]["activeTurn"] = {"id": "user", "message": {"text": "mine"}}

    host.dispatch = dispatch
    out = step(host, spec(tmp_path, config={"sandboxEnabled": "on"})).run(Control(), limit=60)

    assert out.end == "busy"
    assert host.actions("chat/turnStarted") == []


def test_a_turn_delivery_did_not_start_ends_delivery_s_part(tmp_path: Path) -> None:
    script = [
        {"type": "chat/turnComplete"},
        {"type": "chat/turnStarted", "turnId": "user", "message": {"text": "my own question"}},
        {"type": "chat/toolCallReady", "turnId": "user", "toolCallId": "u1", "confirmed": None},
    ]
    host = FakeHost(tmp_path, [{}], [script])
    control = Control()
    control.steering.put("Also check 1280px.")
    out = step(host, spec(tmp_path)).run(control, limit=60)

    assert out.end == "user-turn"
    assert host.actions("chat/toolCallConfirmed") == []
    assert host.actions("chat/turnCancelled") == []


def test_steering_that_never_runs_is_not_a_success(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    control = Control()
    control.steering.put("Also check 1280px.")
    out = step(host, spec(tmp_path)).run(control, limit=120)

    assert out.end == "steering-unrun"


def test_stop_cancels_the_running_turn_and_waits_for_the_host(tmp_path: Path) -> None:
    host = FakeHost(
        tmp_path,
        [{}],
        [[{"type": "chat/toolCallReady", "toolCallId": "t1", "toolInput": "x", "confirmed": None}]],
    )
    control = Control()
    out = step(host, spec(tmp_path), lambda _c: control.stop.set() or True).run(control, limit=60)

    assert out.end == "stopped"
    assert out.cancel_confirmed is True
    (_, cancel) = host.actions("chat/turnCancelled")[-1]
    assert cancel["turnId"] == out.turns[0]
    assert host.chats["ahp-chat://default/c0"]["activeTurn"] is None


def test_a_silent_turn_times_out_and_is_cancelled(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [[]])
    out = step(host, spec(tmp_path)).run(Control(), limit=30)

    assert out.end == "timeout"
    assert host.actions("chat/turnCancelled")[-1][1]["turnId"] == out.turns[0]


def test_steering_runs_as_a_follow_up_turn_that_the_step_waits_for(tmp_path: Path) -> None:
    host = FakeHost(
        tmp_path,
        [{}],
        [
            [{"type": "chat/toolCallStart", "toolCallId": "t0", "toolName": "y"}, {"type": "chat/turnComplete"}],
            [{"type": "chat/turnComplete"}],
        ],
    )
    control = Control()
    control.steering.put("Also check 1280px.")
    out = step(host, spec(tmp_path)).run(control, limit=120)

    assert out.end == "complete"
    ((_, steer),) = host.actions("chat/pendingMessageSet")
    assert steer["message"]["text"].startswith("Also check 1280px.\n\n(OwlBear steering n0nce-")
    assert steer["message"]["model"] == {"id": MODEL, "config": {"thinkingLevel": EFFORT}}
    assert steer["message"]["agent"] == {"uri": (tmp_path / AGENT).resolve().as_uri()}
    assert out.turns[-1] == "follow-up"


def test_a_user_turn_with_the_same_words_as_pending_steering_is_not_adopted(tmp_path: Path) -> None:
    script = [
        {"type": "chat/turnComplete"},
        {"type": "chat/turnStarted", "turnId": "user", "message": {"text": "continue"}},
        {"type": "chat/toolCallReady", "turnId": "user", "toolCallId": "u1", "confirmed": None},
    ]
    host = FakeHost(tmp_path, [{}], [script])
    control = Control()
    control.steering.put("continue")
    out = step(host, spec(tmp_path)).run(control, limit=60)

    assert out.end == "user-turn"
    assert host.actions("chat/toolCallConfirmed") == []


def test_a_stalled_snapshot_during_stop_ends_unconfirmed_within_the_ack_window(tmp_path: Path) -> None:
    host = FakeHost(
        tmp_path,
        [{}],
        [[{"type": "chat/toolCallReady", "toolCallId": "t1", "toolInput": "x", "confirmed": None}]],
    )
    timeouts: list[float] = []
    original = host.request

    def request(method: str, params: dict, timeout: float = 60) -> dict:
        if host.actions("chat/turnStarted") and method == "subscribe":
            timeouts.append(timeout)
            raise HostError("subscribe: no answer")  # noqa: EM101, TRY003
        return original(method, params, timeout)

    host.request = request
    control = Control()
    out = step(host, spec(tmp_path), lambda _c: control.stop.set() or True).run(control, limit=60)

    assert (out.end, out.cancel_confirmed) == ("stopped", False)
    assert timeouts
    assert all(t <= ACK for t in timeouts)


def test_closed_connection_ends_the_step(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [[]])
    host.events.append({"method": "closed", "params": {"error": "gone"}})
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert (out.end, out.detail) == ("closed", "gone")


def test_window_settings_pin_harness_and_model_and_keep_other_keys(tmp_path: Path) -> None:
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode" / "settings.json").write_text('{"editor.tabSize": 2}')
    write_window_settings(tmp_path, MODEL)

    assert json.loads((tmp_path / ".vscode" / "settings.json").read_text()) == {
        "editor.tabSize": 2,
        HARNESS: True,
        DEFAULT_MODEL: MODEL,
    }


@pytest.mark.parametrize(
    ("content", "model"),
    [
        ("[]", MODEL),
        ('{ // mine\n  "chat.defaultModel": "x",\n}', MODEL),
        ("// x\n[1,]", MODEL),
        (None, "auto"),
        (None, " "),
    ],
)
def test_window_settings_fail_closed(tmp_path: Path, content: str | None, model: str) -> None:
    if content is not None:
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".vscode" / "settings.json").write_text(content)
    with pytest.raises(SettingsError):
        write_window_settings(tmp_path, model)
    if content is not None:
        assert (tmp_path / ".vscode" / "settings.json").read_text() == content


def test_settings_with_comments_get_the_pins_after_the_opening_brace(tmp_path: Path) -> None:
    (tmp_path / ".vscode").mkdir()
    (tmp_path / ".vscode" / "settings.json").write_text('// team settings\n{ // mine\n  "a": 1,\n}\n')
    write_window_settings(tmp_path, MODEL)

    assert (tmp_path / ".vscode" / "settings.json").read_text() == (
        f'// team settings\n{{\n  "{HARNESS}": true,\n  "{DEFAULT_MODEL}": "{MODEL}", // mine\n  "a": 1,\n}}\n'
    )


def _ws_send(conn: socket.socket, obj: dict | bytes, op: int = 1) -> None:
    data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
    conn.sendall(bytes([0x80 | op, 126]) + len(data).to_bytes(2, "big") + data)


def _ws_frame(conn: socket.socket) -> tuple[int, bytes]:
    b0, b1 = conn.recv(2)
    n = b1 & 0x7F
    if n == 126:
        n = int.from_bytes(conn.recv(2), "big")
    mask = conn.recv(4)
    data = b""
    while len(data) < n:
        data += conn.recv(n - len(data))
    return b0 & 0x0F, bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def _ws_recv(conn: socket.socket) -> dict:
    return json.loads(_ws_frame(conn)[1])


def _host(
    serve: Callable[[socket.socket], None], *, valid_accept: bool = True, accepts: int = 1
) -> tuple[Path, socket.socket]:
    path = Path(tempfile.mkdtemp(dir="/tmp")) / "h.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen(accepts)

    def accept() -> None:
        for _ in range(accepts):
            conn, _ = server.accept()
            head = b""
            while b"\r\n\r\n" not in head:
                head += conn.recv(1)
            assert b"tkn=secret" in head
            key = next(
                h.split(":", 1)[1].strip() for h in head.decode().split("\r\n") if h.startswith("Sec-WebSocket-Key")
            )
            digest = hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()  # noqa: S324
            accept_key = base64.b64encode(digest).decode() if valid_accept else "wrong"
            conn.sendall(f"HTTP/1.1 101 Switching Protocols\r\nSec-WebSocket-Accept: {accept_key}\r\n\r\n".encode())
            threading.Thread(target=serve, args=(conn,), daemon=True).start()

    threading.Thread(target=accept, daemon=True).start()
    return path, server


def _sign_in(conn: socket.socket, *, refuse: bool = False) -> list[tuple[str, str | None]]:
    """Answer ``initialize`` and ``authenticate``; return the methods and tokens seen."""
    seen = []
    for _ in range(2):
        msg = _ws_recv(conn)
        seen.append((msg["method"], msg["params"].get("token")))
        failed = refuse and msg["method"] == "authenticate"
        reply = {"error": {"message": "bad token"}} if failed else {"result": {}}
        _ws_send(conn, {"jsonrpc": "2.0", "id": msg["id"], **reply})
    return seen


def test_a_reconnect_reaches_the_same_socket_and_signs_in_again() -> None:
    seen: list[list[tuple[str, str | None]]] = []

    def serve(conn: socket.socket) -> None:
        seen.append(_sign_in(conn))
        conn.recv(1)

    path, server = _host(serve, accepts=2)
    first = ahp.connect({"endpoint": {"path": str(path)}, "connectionToken": "secret"}, "c1", "gh-1")
    second = first.reopen("gh-2")
    try:
        assert second is not first
        assert seen == [
            [("initialize", None), ("authenticate", "gh-1")],
            [("initialize", None), ("authenticate", "gh-2")],
        ]
    finally:
        first.close()
        second.close()
        server.close()


def test_a_failed_sign_in_closes_the_connection() -> None:
    ended: queue.Queue[bytes] = queue.Queue()

    def serve(conn: socket.socket) -> None:
        _sign_in(conn, refuse=True)
        ended.put(conn.recv(1))

    path, server = _host(serve)
    try:
        with pytest.raises(ahp.HostError, match="bad token"):
            ahp.connect({"endpoint": {"path": str(path)}, "connectionToken": "secret"}, "c1", "gh")
        assert ended.get(timeout=5) == b""
    finally:
        server.close()


def test_connection_speaks_websocket_json_rpc_over_the_local_socket() -> None:
    pongs: list[bytes] = []

    def serve(conn: socket.socket) -> None:
        first = _ws_recv(conn)
        _ws_send(conn, b"hb", op=9)
        pongs.append(_ws_frame(conn)[1])
        _ws_send(conn, {"jsonrpc": "2.0", "method": "action", "params": {"channel": "c"}})
        _ws_send(conn, {"jsonrpc": "2.0", "id": first["id"], "result": {"items": [first["method"]]}})
        second = _ws_recv(conn)
        _ws_send(conn, {"jsonrpc": "2.0", "id": second["id"], "error": {"message": "nope"}})
        conn.recv(1)

    path, server = _host(serve)
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        assert conn.request("listSessions", {}) == {"items": ["listSessions"]}
        assert pongs == [b"hb"]
        assert conn.next_event(1) == {"jsonrpc": "2.0", "method": "action", "params": {"channel": "c"}}
        with pytest.raises(ahp.HostError, match="nope"):
            conn.request("subscribe", {})
    finally:
        conn.close()
        server.close()


def test_a_server_close_is_answered_and_later_requests_fail_at_once() -> None:
    replies: queue.Queue[tuple[int, bytes]] = queue.Queue()

    def serve(conn: socket.socket) -> None:
        _ws_recv(conn)
        _ws_send(conn, b"\x03\xe8", op=8)
        replies.put(_ws_frame(conn))

    path, server = _host(serve)
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        with pytest.raises(ahp.HostError, match="connection closed"):
            conn.request("listSessions", {}, timeout=5)
        assert replies.get(timeout=5) == (8, b"\x03\xe8")
        assert conn.next_event(1) == {"method": "closed", "params": {"error": "server closed"}}
        with pytest.raises(ahp.HostError, match="connection closed"):
            conn.request("listSessions", {}, timeout=30)
    finally:
        conn.close()
        server.close()


def test_an_upgrade_without_the_right_accept_key_is_refused() -> None:
    path, server = _host(lambda _c: None, valid_accept=False)
    try:
        with pytest.raises(ahp.HostError, match="Sec-WebSocket-Accept"):
            ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    finally:
        server.close()


def test_a_silent_upgrade_fails_within_the_io_bound_and_idle_reads_keep_waiting(monkeypatch) -> None:
    monkeypatch.setattr(ahp, "IO_TIMEOUT", 0.2)
    path = Path(tempfile.mkdtemp(dir="/tmp")) / "s.sock"
    silent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    silent.bind(str(path))
    silent.listen(1)
    try:
        with pytest.raises(TimeoutError):
            ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    finally:
        silent.close()

    def serve(conn: socket.socket) -> None:
        first = _ws_recv(conn)
        threading.Event().wait(0.6)  # idle for three read timeouts, then answer
        _ws_send(conn, {"jsonrpc": "2.0", "id": first["id"], "result": {"ok": True}})

    path, server = _host(serve)
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        assert conn.request("listSessions", {}, timeout=5) == {"ok": True}
    finally:
        conn.close()
        server.close()


def test_endpoint_is_none_without_a_running_editor_host(tmp_path: Path) -> None:
    assert ahp.endpoint(tmp_path / "missing") is None
    (tmp_path / "a.json").write_text('{"endpoint": {"path": "/x"}}')
    assert ahp.endpoint(tmp_path) == {"endpoint": {"path": "/x"}}


HEAD, BASE = "a" * 40, "b" * 40
GOOD = {"summary": "Added greet().", "changed_paths": ["src/greet.ts"], "checks": []}
USAGE = {"type": "chat/usage", "usage": {"model": MODEL, "inputTokens": 100, "outputTokens": 20}}


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def wt(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    path = tmp_path / "wt"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    (path / "README.md").write_text("x\n")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "init")
    return path


class Adapted:
    """One adapter run against the fake host; ``submit`` is what the agent sends through the relay per turn."""

    def __init__(self, folder: Path, inbox: Path, scripts: list[list[dict]], submit: list[dict | None]) -> None:
        self.host = FakeHost(folder, [{}], scripts)
        self.inbox, self.submit, self.replies = inbox, submit, []
        self.events: list[dict] = []
        self.delivered: list[int] = []
        self.files_during: list[bool] = []
        original = self.host.dispatch

        def dispatch(channel: str, action: dict) -> None:
            if action["type"] == "chat/turnStarted":
                self.files_during.append(str(inbox) in (folder / ".mcp.json").read_text())
                if self.submit and (args := self.submit.pop(0)) is not None:
                    body = {"name": "submit_result", "arguments": args}
                    self.replies.append(step_mcp.forward(inbox, "POST", "/call", body))
            original(channel, action)

        self.host.dispatch = dispatch
        journal = sdk_adapter.Journal(event=self.events.append, delivered=lambda: self.delivered.append(1))
        self.cfg = sdk_adapter.Session(
            StepKind.BUILD, folder, "s1", "Build it.", resume=False, policy=Policy(folder),
            observe=lambda: Worktree(HEAD, BASE, changed=("src/greet.ts",)), checks=(), model=MODEL, effort=EFFORT,
            journal=journal,
        )  # fmt: skip
        self.settled = Termination(confirmed=True)
        self.env = vscode_adapter.Env(
            connect=lambda _f: self.host,
            reconnect=lambda _c: self.host.reconnect(),
            launch=self.host.launch,
            clock=self.host.clock,
            settle=lambda *_a: self.settled,
            reminder="Call submit_result.",
        )

    def run(self) -> session_result.Run:
        return vscode_adapter.run(self.cfg, self.inbox, self.env)

    def texts(self) -> list[str]:
        return [a["message"]["text"] for _, a in self.host.actions("chat/turnStarted")]


def test_screenshots_go_to_the_window_as_embedded_images_with_the_first_turn_only(wt: Path, tmp_path: Path) -> None:
    done = [USAGE, {"type": "chat/turnComplete"}]
    a = Adapted(wt, tmp_path / "steps" / "1.json", [done, done], [None, GOOD])
    png = base64.b64encode(b"\x89PNG").decode()
    shot = {"type": "blob", "data": png, "mimeType": "image/png", "displayName": "home-1280.png"}
    a.cfg = dataclasses.replace(a.cfg, attachments=(shot,))
    run = a.run()

    first, reminder = (action["message"] for _, action in a.host.actions("chat/turnStarted"))
    image = {"type": "embeddedResource", "label": "home-1280.png", "displayKind": "image", "data": png}
    assert first["attachments"] == [image | {"contentType": "image/png"}]
    assert "attachments" not in reminder
    assert run.ending == "result"


def test_a_vscode_session_returns_the_gated_result_and_leaves_no_window_files(wt: Path, tmp_path: Path) -> None:
    a = Adapted(wt, tmp_path / "steps" / "1.json", [[USAGE, {"type": "chat/turnComplete"}]], [GOOD])
    run = a.run()

    assert a.replies[0]["ok"] is True
    assert a.files_during == [True]
    assert (run.ending, run.head, run.payload.summary) == ("result", HEAD, "Added greet().")
    assert run.usage == {"credits": None, "models": {MODEL: {"credits": None, "tokens": 120}}, "model_mismatch": False}
    assert (run.model_check, run.usage_unread) == ("verified", "")
    assert (run.termination.confirmed, a.delivered, a.texts()) == (True, [1], ["Build it."])
    assert a.host.config["copilotcli:/s0"] == vscode_adapter.CONFIG
    assert a.host.launched[0][:4] == ["code", "chat", "-m", "agent"]
    assert git(wt, "status", "--porcelain", "--ignored") == ""
    assert not (tmp_path / "steps" / "1.json").exists()
    assert not (wt / ".github").exists()
    assert not (wt / ".vscode").exists()
    assert session_result.to_result(run, StepKind.BUILD, datetime.now(UTC)).exit == Exit.DONE


def test_a_result_from_a_turn_billed_to_another_model_is_discarded(wt: Path, tmp_path: Path) -> None:
    other = {"type": "chat/usage", "usage": {"model": "mai-code-1.1-flash", "inputTokens": 1, "outputTokens": 1}}
    a = Adapted(wt, tmp_path / "steps" / "2.json", [[other, {"type": "chat/turnComplete"}]], [GOOD])
    run = a.run()

    assert a.replies[0]["ok"] is True
    assert (run.ending, run.payload, run.head) == ("error", None, None)
    assert "mai-code-1.1-flash" in run.detail
    assert run.usage["model_mismatch"] is True


def test_a_turn_without_a_result_is_reminded_once_then_retried(wt: Path, tmp_path: Path) -> None:
    done = [USAGE, {"type": "chat/turnComplete"}]
    a = Adapted(wt, tmp_path / "steps" / "3.json", [done, done], [None, None])
    run = a.run()

    assert a.texts() == ["Build it.", "Call submit_result."]
    assert (run.ending, run.usage["models"][MODEL]["tokens"]) == ("no-result", 240)
    assert session_result.to_result(run, StepKind.BUILD, datetime.now(UTC)).exit == Exit.RETRY


def test_an_unlisted_agent_ends_the_step_and_restores_the_users_settings(wt: Path, tmp_path: Path) -> None:
    (wt / ".vscode").mkdir()
    (wt / ".vscode" / "settings.json").write_text('{ // mine\n  "a": 1,\n}\n')
    a = Adapted(wt, tmp_path / "steps" / "4.json", [[USAGE, {"type": "chat/turnComplete"}]], [GOOD])
    a.host.listed = []
    run = a.run()

    assert len(a.host.launched) == 1
    assert [e["end"] for e in a.events if e.get("event") == "vscode-step"] == ["no-agent"]
    assert (run.ending, a.texts(), a.delivered) == ("error", [], [])
    assert (wt / ".vscode" / "settings.json").read_text() == '{ // mine\n  "a": 1,\n}\n'


def test_an_unconfirmed_bootstrap_cancel_is_a_termination_problem(wt: Path, tmp_path: Path) -> None:
    a = Adapted(wt, tmp_path / "steps" / "7.json", [], [])
    a.host.boot_active = True
    a.host.ignore_cancel = True
    run = a.run()

    assert len(a.host.launched) == 1
    assert run.ending == "error"
    assert run.termination.confirmed is False
    assert "cancel" in run.termination.problems[0]


def test_an_unreachable_editor_ends_in_a_retry_and_restores_the_files(wt: Path, tmp_path: Path) -> None:
    a = Adapted(wt, tmp_path / "steps" / "5.json", [], [])

    def refuse(_folder: Path) -> ahp.Transport:
        raise HostError("no agent host")  # noqa: EM101, TRY003

    a.env = vscode_adapter.Env(connect=refuse, settle=a.env.settle)
    run = a.run()

    assert (run.ending, run.detail) == ("error", "VS Code step error: HostError: no agent host")
    assert (run.termination.confirmed, a.delivered) == (True, [])
    assert git(wt, "status", "--porcelain", "--ignored") == ""


def test_a_process_left_in_the_worktree_stops_the_step(wt: Path, tmp_path: Path) -> None:
    a = Adapted(wt, tmp_path / "steps" / "6.json", [[USAGE, {"type": "chat/turnComplete"}]], [GOOD])
    a.settled = Termination(confirmed=False, survivors=(4242,))
    run = a.run()

    result = session_result.to_result(run, StepKind.BUILD, datetime.now(UTC))
    assert (run.ending, result.exit) == ("result", Exit.STOP)
    assert "4242" in result.reason


SHAPER = resolve(None, Layer()).agents["shaper"]
SIZES = {"enum": [200000, 1000000], "enumDescriptions": ["Default", "Longer sessions"], "default": 1000000}


def shaping_host(folder: Path) -> FakeHost:
    host = FakeHost(folder, [{}], [])
    host.models, host.listed = [SHAPER.model], []  # the chat names no agent file, so none needs listing
    host.schema = {"properties": {"thinkingLevel": {"enum": ["high", "xhigh"]}, "contextSize": SIZES}}
    return host


def shaping_env(host: FakeHost, during: Callable[[], None] = lambda: None) -> vscode_adapter.Env:
    def launch(args: list[str], cwd: Path) -> None:
        during()
        host.launch(args, cwd)

    return vscode_adapter.Env(
        connect=lambda _f: host, reconnect=lambda _c: host.reconnect(), launch=launch, clock=host.clock
    )


def shape(folder: Path, env: vscode_adapter.Env) -> tuple[Outcome, str]:
    return vscode_adapter.open_chat(folder, SHAPER, "Shape a brief with me.", env)


def untouched_git(folder: Path) -> tuple[str, str]:
    """The folder's skip-worktree marks and local excludes, which Delivery never changes in the owner's folder."""
    return git(folder, "ls-files", "-v"), (folder / ".git" / "info" / "exclude").read_text()


def test_the_shaping_chat_runs_on_the_shaper_role_and_is_left_to_the_owner(wt: Path) -> None:
    host = shaping_host(wt)
    host.add(nonce="x", text="the owner's own chat")
    host.chats["ahp-chat://default/c0"]["activeTurn"] = {"id": "theirs"}  # a busy chat does not block it
    settings, before = wt / ".vscode" / "settings.json", untouched_git(wt)
    seen: list[str] = []

    out, warning = shape(wt, shaping_env(host, lambda: seen.append(settings.read_text())))

    assert (out.end, out.session, warning) == ("started", "copilotcli:/s1", "")
    assert seen == ['{\n  "chat.defaultToCopilotHarness": true\n}\n']  # the harness only: each turn names its model
    assert not (wt / ".vscode").exists()
    [launched] = host.launched
    assert launched[:4] == ["code", "chat", "-m", "agent"]
    assert re.fullmatch(r"!echo OWLBEAR-\w{12}", launched[4])
    assert host.config["copilotcli:/s1"] == {
        "autoApprove": "autoApprove",
        "sandboxEnabled": "off",
        "mode": "interactive",
    }
    ((chat, started),) = host.actions("chat/turnStarted")
    message = started["message"]
    assert (chat, message["text"], "agent" in message) == ("ahp-chat://default/c1", "Shape a brief with me.", False)
    assert message["model"] == {"id": "claude-opus-5.5", "config": {"thinkingLevel": "medium", "contextSize": 200000}}
    assert host.chats[chat]["activeTurn"]["id"] == out.turns[0]  # still running: Delivery neither follows nor stops it
    assert host.actions("chat/turnCancelled") == []
    assert (host.twin.closed, host.closed) == (1, 1)
    assert (git(wt, "status", "--porcelain", "--ignored"), untouched_git(wt)) == ("", before)


OWNER = '// team settings\n{\n  "editor.tabSize": 2, // mine\n  "a": [1,2]\n}\n'


def test_only_the_harness_key_is_added_and_removed_and_the_owners_edits_meanwhile_stay(wt: Path) -> None:
    settings = wt / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(OWNER)
    git(wt, "add", "-A")
    git(wt, "commit", "-qm", "settings")
    before, seen = untouched_git(wt), []

    def owner_edits() -> None:
        seen.append(text := settings.read_text())
        settings.write_text(text.replace('"a": [1,2]', '"a": [1,2],\n  "b": true'))

    out, warning = shape(wt, shaping_env(shaping_host(wt), owner_edits))

    assert (out.end, warning) == ("started", "")
    assert seen == [OWNER.replace("{\n", '{\n  "chat.defaultToCopilotHarness": true,\n', 1)]
    assert settings.read_text() == OWNER.replace('"a": [1,2]', '"a": [1,2],\n  "b": true')
    assert untouched_git(wt) == before


def test_a_settings_file_delivery_made_keeps_what_the_owner_added_meanwhile(wt: Path) -> None:
    settings = wt / ".vscode" / "settings.json"

    def owner_adds() -> None:
        settings.write_text(settings.read_text().replace("true\n", 'true,\n  "a": 1\n'))

    out, warning = shape(wt, shaping_env(shaping_host(wt), owner_adds))
    assert (out.end, warning, settings.read_text()) == ("started", "", '{\n  "a": 1\n}\n')


@pytest.mark.parametrize("theirs", ['{"chat.defaultToCopilotHarness": false}', "// x\n{}\n"])
def test_the_owners_own_harness_setting_or_an_empty_object_is_kept_byte_for_byte(wt: Path, theirs: str) -> None:
    settings = wt / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(theirs)
    out, warning = shape(wt, shaping_env(shaping_host(wt)))
    assert (out.end, warning, settings.read_text()) == ("started", "", theirs)


def test_a_cleanup_failure_is_a_warning_and_the_chat_still_started(wt: Path) -> None:
    folder = wt / ".vscode"
    out, warning = shape(wt, shaping_env(shaping_host(wt), lambda: folder.chmod(0o555)))
    folder.chmod(0o755)
    assert out.end == "started"
    assert warning.startswith("could not remove chat.defaultToCopilotHarness from .vscode/settings.json")
    assert warning.endswith("remove it by hand")
    assert json.loads((folder / "settings.json").read_text()) == {HARNESS: True}


def test_settings_that_are_not_an_object_refuse_the_shaping_chat_before_launch(wt: Path) -> None:
    settings = wt / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("[]\n")
    host = shaping_host(wt)
    out, warning = shape(wt, shaping_env(host))
    assert (out.end, warning, host.launched, settings.read_text()) == ("settings-refused", "", [], "[]\n")


def test_a_shaping_turn_the_host_never_starts_is_reported(wt: Path) -> None:
    host = shaping_host(wt)
    dispatch = host.dispatch
    host.dispatch = lambda channel, action: None if action["type"] == "chat/turnStarted" else dispatch(channel, action)
    out, _ = shape(wt, shaping_env(host))
    assert (out.end, out.detail) == ("unstarted", "the host did not start the prompt's turn")


def test_an_unreachable_editor_leaves_no_shaping_files(wt: Path) -> None:
    def refuse(_folder: Path) -> ahp.Transport:
        raise HostError("VS Code published no agent host within 60 s")  # noqa: EM101, TRY003

    out, warning = shape(wt, vscode_adapter.Env(connect=refuse))
    assert (out.end, out.detail, warning) == ("error", "HostError: VS Code published no agent host within 60 s", "")
    assert git(wt, "status", "--porcelain", "--ignored") == ""
