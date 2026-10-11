import json
import socket
import tempfile
import threading
from pathlib import Path

import pytest

from owlbear_delivery_next import ahp
from owlbear_delivery_next.vscode_step import (
    DEFAULT_MODEL,
    HARNESS,
    Control,
    SettingsError,
    Step,
    StepSpec,
    ToolCall,
    write_window_settings,
)

MODEL, EFFORT, AGENT = "gpt-6-luna", "max", "builder"


class FakeHost:
    """A scripted editor host: sessions appear on launch, each started turn plays its script."""

    def __init__(self, folder: Path, sessions_on_launch: list[dict], scripts: list[list[dict]]) -> None:
        self.folder, self.t = folder, 0.0
        self.items: list[dict] = []
        self.chats: dict[str, dict] = {}
        self.config: dict[str, dict] = {}
        self.on_launch, self.scripts = sessions_on_launch, scripts
        self.accept_config = True
        self.sent: list[tuple[str, dict]] = []
        self.events: list[dict] = []
        self.launched: list[list[str]] = []

    def clock(self) -> float:
        return self.t

    def launch(self, args: list[str], _cwd: Path) -> None:
        self.launched.append(args)
        nonce = args[-1].split()[2].rstrip(":")
        for spec in self.on_launch:
            self.add(nonce=nonce, **spec)

    def add(
        self,
        *,
        nonce: str,
        folder: Path | None = None,
        agent: str = AGENT,
        model: str = MODEL,
        text: str | None = None,
    ) -> str:
        n = len(self.items)
        resource, chat = f"copilotcli:/s{n}", f"ahp-chat://default/c{n}"
        msg = {
            "text": text if text is not None else f"OwlBear step {nonce}: wait for Delivery's instructions.",
            "model": {"id": model, "config": {"thinkingLevel": "high"}},
            "agent": {"uri": f"file://{folder or self.folder}/.github/agents/{agent}.agent.md"},
        }
        turn = {"id": f"boot{n}", "message": msg}
        self.items.append(
            {
                "resource": resource,
                "defaultChat": chat,
                "workingDirectories": [(folder or self.folder).resolve().as_uri()],
            }
        )
        self.chats[chat] = {"activeTurn": turn, "turns": []}
        self.config[resource] = {}
        return resource

    def request(self, method: str, params: dict, timeout: float = 60) -> dict:  # noqa: ARG002
        if method == "listSessions":
            return {"items": list(self.items)}
        channel = params["channel"]
        if channel in self.chats:
            return {"snapshot": {"state": self.chats[channel]}}
        return {"snapshot": {"state": {"config": {"values": self.config[channel]}}}}

    def dispatch(self, channel: str, action: dict) -> None:
        self.sent.append((channel, action))
        kind = action["type"]
        if kind == "session/configChanged" and self.accept_config:
            self.config[channel] |= action["config"]
        elif (
            kind == "chat/turnCancelled" and (self.chats[channel].get("activeTurn") or {}).get("id") == action["turnId"]
        ):
            self.chats[channel]["activeTurn"] = None
        elif kind == "chat/turnStarted" and self.scripts:
            self.play(channel, action["turnId"], self.scripts.pop(0))
        elif kind == "chat/pendingMessageSet" and self.scripts:
            self.play(channel, "follow-up", [{"type": "chat/turnStarted"}, *self.scripts.pop(0)])

    def play(self, chat: str, turn: str, script: list[dict]) -> None:
        for a in script:
            self.events.append({"method": "action", "params": {"channel": chat, "action": {"turnId": turn, **a}}})

    def next_event(self, timeout: float) -> dict | None:
        self.t += timeout
        return self.events.pop(0) if self.events else None

    def actions(self, kind: str) -> list[tuple[str, dict]]:
        return [(c, a) for c, a in self.sent if a["type"] == kind]


def spec(folder: Path, **kw: object) -> StepSpec:
    return StepSpec(
        folder=folder, agent=AGENT, model=MODEL, effort=EFFORT, prompt="Check the page at 390px.", nonce="n0nce", **kw
    )


def step(host: FakeHost, s: StepSpec, approve=lambda _c: True) -> Step:
    return Step(host, s, approve, launch=host.launch, clock=host.clock)


DONE = [{"type": "chat/usage", "usage": {"model": MODEL}}, {"type": "chat/turnComplete"}]


def test_step_binds_its_session_cancels_bootstrap_and_runs_named_model(tmp_path: Path) -> None:
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
    assert host.launched == [["code", "chat", "-m", AGENT, "OwlBear step n0nce: wait for Delivery's instructions."]]
    assert host.actions("chat/turnCancelled") == [
        ("ahp-chat://default/c0", {"type": "chat/turnCancelled", "turnId": "boot0", "duration": 0})
    ]
    assert host.config["copilotcli:/s0"] == {"sandboxEnabled": "on"}
    ((_, started),) = host.actions("chat/turnStarted")
    assert started["message"]["model"] == {"id": MODEL, "config": {"thinkingLevel": EFFORT}}
    assert started["message"]["agent"]["uri"].endswith("/builder.agent.md")
    assert seen == [ToolCall("openBrowserPage", "http://x", None)]
    ((_, confirm),) = host.actions("chat/toolCallConfirmed")
    assert confirm["approved"] is True
    assert out.tools == {"t1": "openBrowserPage"}
    assert out.usage == {"model": MODEL}


def test_step_never_touches_the_users_chats(tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    host = FakeHost(tmp_path, [{"text": "my own question"}, {"folder": other}, {"agent": "planner"}, {}], [DONE])
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert out.end == "complete"
    assert out.session == "copilotcli:/s3"
    assert {c for c, _ in host.sent} <= {"ahp-chat://default/c3", "copilotcli:/s3"}


def test_step_acts_on_nothing_when_two_sessions_match(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}, {}], [DONE])
    out = step(host, spec(tmp_path)).run(Control(), limit=60, bind_limit=5)

    assert out.end == "unbound"
    assert host.sent == []


def test_step_ignores_sessions_that_existed_before_launch(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [], [DONE])
    host.add(nonce="n0nce")
    out = step(host, spec(tmp_path)).run(Control(), limit=60, bind_limit=5)

    assert out.end == "unbound"
    assert host.sent == []


def test_step_fails_closed_when_window_started_on_another_model(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{"model": "auto"}], [DONE])
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert out.end == "wrong-model"
    assert "auto" in out.detail
    assert [a["type"] for _, a in host.sent] == ["chat/turnCancelled"]


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


def test_stop_cancels_the_running_turn(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [[{"type": "chat/toolCallStart", "toolCallId": "t1", "toolName": "x"}]])
    control = Control()
    control.stop.set()
    out = step(host, spec(tmp_path)).run(control, limit=60)

    assert out.end == "stopped"
    (_, cancel) = host.actions("chat/turnCancelled")[-1]
    assert cancel["turnId"] == out.turns[0]


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
    assert steer["message"]["text"] == "Also check 1280px."
    assert out.turns[-1] == "follow-up"


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


@pytest.mark.parametrize(("content", "model"), [("{ // mine\n}", MODEL), ("[]", MODEL), (None, "auto"), (None, " ")])
def test_window_settings_fail_closed(tmp_path: Path, content: str | None, model: str) -> None:
    if content is not None:
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".vscode" / "settings.json").write_text(content)
    with pytest.raises(SettingsError):
        write_window_settings(tmp_path, model)
    if content is not None:
        assert (tmp_path / ".vscode" / "settings.json").read_text() == content


def _ws_send(conn: socket.socket, obj: dict) -> None:
    data = json.dumps(obj).encode()
    conn.sendall(bytes([0x81, 126]) + len(data).to_bytes(2, "big") + data)


def _ws_recv(conn: socket.socket) -> dict:
    _, b1 = conn.recv(2)
    n = b1 & 0x7F
    if n == 126:
        n = int.from_bytes(conn.recv(2), "big")
    mask = conn.recv(4)
    data = b""
    while len(data) < n:
        data += conn.recv(n - len(data))
    return json.loads(bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def test_connection_speaks_websocket_json_rpc_over_the_local_socket() -> None:
    path = Path(tempfile.mkdtemp(dir="/tmp")) / "h.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen(1)

    def serve() -> None:
        conn, _ = server.accept()
        head = b""
        while b"\r\n\r\n" not in head:
            head += conn.recv(1)
        assert b"tkn=secret" in head
        conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\n\r\n")
        first = _ws_recv(conn)
        _ws_send(conn, {"jsonrpc": "2.0", "method": "action", "params": {"channel": "c"}})
        _ws_send(conn, {"jsonrpc": "2.0", "id": first["id"], "result": {"items": [first["method"]]}})
        second = _ws_recv(conn)
        _ws_send(conn, {"jsonrpc": "2.0", "id": second["id"], "error": {"message": "nope"}})
        conn.recv(1)

    threading.Thread(target=serve, daemon=True).start()
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        assert conn.request("listSessions", {}) == {"items": ["listSessions"]}
        assert conn.next_event(1) == {"jsonrpc": "2.0", "method": "action", "params": {"channel": "c"}}
        with pytest.raises(ahp.HostError, match="nope"):
            conn.request("subscribe", {})
    finally:
        conn.close()
        server.close()


def test_endpoint_is_none_without_a_running_editor_host(tmp_path: Path) -> None:
    assert ahp.endpoint(tmp_path / "missing") is None
    (tmp_path / "a.json").write_text('{"endpoint": {"path": "/x"}}')
    assert ahp.endpoint(tmp_path) == {"endpoint": {"path": "/x"}}
