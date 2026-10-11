import base64
import hashlib
import json
import queue
import socket
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from owlbear_delivery_next import ahp
from owlbear_delivery_next.ahp import HostError
from owlbear_delivery_next.vscode_step import (
    ACK,
    DEFAULT_MODEL,
    HARNESS,
    Control,
    Hooks,
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
        self.ignore_cancel = False
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
        elif kind == "chat/turnCancelled" and not self.ignore_cancel:
            if (self.chats[channel].get("activeTurn") or {}).get("id") == action["turnId"]:
                self.chats[channel]["activeTurn"] = None
        elif kind == "chat/turnStarted":
            self.chats[channel]["activeTurn"] = {"id": action["turnId"], "message": action["message"]}
            if self.scripts:
                self.play(channel, action["turnId"], self.scripts.pop(0))
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


def spec(folder: Path, **kw: object) -> StepSpec:
    return StepSpec(
        folder=folder, agent=AGENT, model=MODEL, effort=EFFORT, prompt="Check the page at 390px.", nonce="n0nce", **kw
    )


def step(host: FakeHost, s: StepSpec, approve=lambda _c: True) -> Step:
    return Step(host, s, approve, hooks=Hooks(launch=host.launch, clock=host.clock, settings=host.pin))


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
    assert host.pinned == [(tmp_path, MODEL)]
    assert json.loads((tmp_path / ".vscode" / "settings.json").read_text())[DEFAULT_MODEL] == MODEL
    assert out.cancel_confirmed is True
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


def test_a_stop_before_launch_launches_nothing(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    control = Control()
    control.stop.set()
    out = step(host, spec(tmp_path)).run(control, limit=60)

    assert out.end == "stopped"
    assert (host.launched, host.sent, host.pinned) == ([], [], [])


def test_auto_is_refused_before_anything_launches(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{"model": "auto"}], [DONE])
    s = StepSpec(folder=tmp_path, agent=AGENT, model="auto", effort=EFFORT, prompt="x", nonce="n0nce")
    out = step(host, s).run(Control(), limit=60)

    assert out.end == "settings-refused"
    assert (host.launched, host.sent) == ([], [])


def test_an_unacknowledged_bootstrap_cancel_starts_no_turn(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.ignore_cancel = True
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

    assert out.end == "cancel-unconfirmed"
    assert out.cancel_confirmed is False
    assert host.actions("chat/turnStarted") == []


def test_a_user_turn_in_the_bound_chat_blocks_the_start(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    original = host.dispatch

    def dispatch(channel: str, action: dict) -> None:
        original(channel, action)
        if action["type"] == "chat/turnCancelled":
            host.chats[channel]["activeTurn"] = {"id": "user", "message": {"text": "mine"}}

    host.dispatch = dispatch
    out = step(host, spec(tmp_path)).run(Control(), limit=60)

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
    assert [a["turnId"] for _, a in host.actions("chat/turnCancelled")] == ["boot0"]


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


@pytest.mark.parametrize(("content", "model"), [("{ // mine\n}", MODEL), ("[]", MODEL), (None, "auto"), (None, " ")])
def test_window_settings_fail_closed(tmp_path: Path, content: str | None, model: str) -> None:
    if content is not None:
        (tmp_path / ".vscode").mkdir()
        (tmp_path / ".vscode" / "settings.json").write_text(content)
    with pytest.raises(SettingsError):
        write_window_settings(tmp_path, model)
    if content is not None:
        assert (tmp_path / ".vscode" / "settings.json").read_text() == content


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


def _host(serve: Callable[[socket.socket], None], *, valid_accept: bool = True) -> tuple[Path, socket.socket]:
    path = Path(tempfile.mkdtemp(dir="/tmp")) / "h.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen(1)

    def accept() -> None:
        conn, _ = server.accept()
        head = b""
        while b"\r\n\r\n" not in head:
            head += conn.recv(1)
        assert b"tkn=secret" in head
        key = next(h.split(":", 1)[1].strip() for h in head.decode().split("\r\n") if h.startswith("Sec-WebSocket-Key"))
        digest = hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()  # noqa: S324 - RFC 6455
        accept_key = base64.b64encode(digest).decode() if valid_accept else "wrong"
        conn.sendall(f"HTTP/1.1 101 Switching Protocols\r\nSec-WebSocket-Accept: {accept_key}\r\n\r\n".encode())
        serve(conn)

    threading.Thread(target=accept, daemon=True).start()
    return path, server


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


def test_endpoint_is_none_without_a_running_editor_host(tmp_path: Path) -> None:
    assert ahp.endpoint(tmp_path / "missing") is None
    (tmp_path / "a.json").write_text('{"endpoint": {"path": "/x"}}')
    assert ahp.endpoint(tmp_path) == {"endpoint": {"path": "/x"}}
