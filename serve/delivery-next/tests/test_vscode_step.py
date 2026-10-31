import base64
import hashlib
import json
import logging
import queue
import re
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from owlbear_delivery_next.runtimes import ahp, readiness, vscode_adapter
from owlbear_delivery_next.runtimes.ahp import HostError
from owlbear_delivery_next.runtimes.vscode_contract import Hooks, Outcome, StepSpec
from owlbear_delivery_next.runtimes.vscode_step import Step
from owlbear_delivery_next.runtimes.window_files import HARNESS
from owlbear_delivery_next.settings import carried

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
        self.sent: list[tuple[str, dict]] = []
        self.events: list[dict] = []
        self.launched: list[list[str]] = []

    def clock(self) -> float:
        return self.t

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

    def add(
        self,
        *,
        nonce: str,
        folder: Path | None = None,
        text: str | None = None,
        billed: str | None = None,
        pending: str | None = None,
    ) -> str:
        n = len(self.items)
        resource, chat = f"copilotcli:/s{n}", f"ahp-chat://default/c{n}"
        msg = {
            "text": text if text is not None else f"!echo OWLBEAR-{nonce}",
            "model": {"id": MODEL, "config": {"thinkingLevel": "high"}},
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
    """A second connection to the same fake host."""

    def __init__(self, host: FakeHost) -> None:
        self.host, self.closed = host, 0

    def request(self, method: str, params: dict, timeout: float = 60) -> dict:
        return self.host.request(method, params, timeout)

    def dispatch(self, channel: str, action: dict) -> None:
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


def step(host: FakeHost, s: StepSpec) -> Step:
    hooks = Hooks(launch=host.launch, clock=host.clock, settings=lambda _f, _m: None, reconnect=host.reconnect)
    return Step(host, s, hooks)


DONE = [{"type": "chat/usage", "usage": {"model": MODEL}}, {"type": "chat/turnComplete"}]


def test_step_sends_the_tiers_context_size_and_only_an_effort_the_model_takes(tmp_path: Path) -> None:
    sizes = {"enum": [200000, 1000000], "enumDescriptions": ["Default", "Longer sessions"], "default": 1000000}

    def config(schema: dict, context: str = "default") -> dict:
        host = FakeHost(tmp_path, [{}], [DONE])
        host.schema = schema
        step(host, spec(tmp_path, context=context)).open()
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
    out = step(host, spec(tmp_path)).open()

    assert out.end == "started"
    assert out.session == "copilotcli:/s2"
    assert {c for c, _ in host.sent} <= {"ahp-chat://default/c2", "copilotcli:/s2"}


def test_step_acts_on_nothing_when_two_sessions_match(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}, {}], [DONE])
    out = step(host, spec(tmp_path)).open(bind_limit=5)

    assert out.end == "unbound"
    assert host.sent == []


def test_step_ignores_sessions_that_existed_before_launch(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [], [DONE])
    host.boot_active = False
    host.add(nonce="n0nce")
    out = step(host, spec(tmp_path)).open(bind_limit=5)

    assert out.end == "unbound"
    assert host.sent == []


def test_a_bootstrap_that_called_a_model_fails_closed(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{"billed": "mai-code-1.1-flash"}], [DONE])
    out = step(host, spec(tmp_path)).open()

    assert (out.end, out.detail) == ("bootstrap-model", "the window's first turn called mai-code-1.1-flash")
    assert host.actions("chat/turnStarted") == []


def test_only_the_bootstraps_own_echo_is_confirmed(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    host.boot_script = [
        {"type": "chat/toolCallReady", "toolCallId": "b1", "toolInput": "echo OWLBEAR-n0nce", "confirmed": None},
        {"type": "chat/turnComplete"},
    ]
    out = step(host, spec(tmp_path)).open()
    ((_, confirm),) = host.actions("chat/toolCallConfirmed")[:1]
    assert (out.end, confirm["toolCallId"], confirm["approved"]) == ("started", "b1", True)

    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    host.boot_script = [
        {"type": "chat/toolCallReady", "toolCallId": "b1", "toolInput": "rm -rf ~", "confirmed": None},
        {"type": "chat/turnComplete"},
    ]
    out = step(host, spec(tmp_path)).open()
    ((_, confirm),) = host.actions("chat/toolCallConfirmed")
    assert (out.end, confirm["approved"], host.actions("chat/turnStarted")) == ("bootstrap-unexpected", False, [])


def test_a_pending_echo_seen_in_the_snapshot_and_as_an_event_is_confirmed_once(tmp_path: Path) -> None:
    for script in ([], [{"type": "chat/toolCallReady", "toolCallId": "p1", "toolInput": "echo OWLBEAR-n0nce"}]):
        host = FakeHost(tmp_path, [{"pending": "echo OWLBEAR-n0nce"}], [DONE])
        host.boot_active = True
        host.boot_script = script
        out = step(host, spec(tmp_path)).open()

        confirms = [(a["turnId"], a["toolCallId"], a["approved"]) for _, a in host.actions("chat/toolCallConfirmed")]
        assert (out.end, confirms) == ("started", [("boot0", "p1", True)])


def test_the_step_waits_until_the_host_lists_its_model_and_never_starts_without_it(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.models_at = 5.0
    out = step(host, spec(tmp_path)).open()
    assert (out.end, len(host.actions("chat/turnStarted"))) == ("started", 1)

    host = FakeHost(tmp_path, [{}], [DONE])
    host.models = ["mai-code-1.1-flash"]
    out = step(host, spec(tmp_path)).open()
    assert (out.end, out.detail) == ("model-unavailable", f"the agent host does not list {MODEL}")
    assert host.actions("chat/turnStarted") == []


def test_an_agent_the_session_does_not_list_starts_no_turn(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.listed = [(Path.home() / ".copilot/agents/owlbear-builder.agent.md").as_uri()]
    out = step(host, spec(tmp_path)).open()

    assert (out.end, out.detail) == ("no-agent", f"the session does not list {(tmp_path / AGENT).resolve().as_uri()}")
    assert host.actions("chat/turnCancelled") == []
    assert host.actions("chat/turnStarted") == []


def test_the_turn_waits_until_the_session_lists_the_agent(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.listed_at = 3.0
    out = step(host, spec(tmp_path)).open()

    assert out.end == "started"
    ((_, started),) = host.actions("chat/turnStarted")
    assert started["message"]["agent"] == {"uri": (tmp_path / AGENT).resolve().as_uri()}


def test_step_fails_closed_when_host_ignores_the_config(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.accept_config = False
    out = step(host, spec(tmp_path, config={"sandboxEnabled": "on"})).open()

    assert out.end == "config-refused"
    assert host.actions("chat/turnStarted") == []


def test_a_bootstrap_that_never_finishes_is_cancelled_and_starts_no_turn(tmp_path: Path) -> None:
    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    host.ignore_cancel = True
    out = step(host, spec(tmp_path)).open()
    assert (out.end, out.cancel_confirmed) == ("cancel-unconfirmed", False)
    assert host.actions("chat/turnStarted") == []

    host = FakeHost(tmp_path, [{}], [DONE])
    host.boot_active = True
    out = step(host, spec(tmp_path)).open()
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
    out = step(host, spec(tmp_path, config={"sandboxEnabled": "on"})).open()

    assert out.end == "busy"
    assert host.actions("chat/turnStarted") == []


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
            assert b"User-Agent" not in head
            assert b"permessage-deflate" not in head
            key = next(
                h.split(":", 1)[1].strip() for h in head.decode().split("\r\n") if h.startswith("Sec-WebSocket-Key")
            )
            digest = hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()  # noqa: S324
            accept_key = base64.b64encode(digest).decode() if valid_accept else "wrong"
            conn.sendall(
                b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                + f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n".encode()
            )
            threading.Thread(target=serve, args=(conn,), daemon=True).start()

    threading.Thread(target=accept, daemon=True).start()
    return path, server


def _answer_close(conn: socket.socket) -> bytes:
    """Wait for the client's close frame, echo it and close the socket as the host does; return the payload."""
    op, data = _ws_frame(conn)
    while op != 8:
        op, data = _ws_frame(conn)
    _ws_send(conn, data, op=8)
    conn.close()
    return data


def _sign_in(
    conn: socket.socket,
    *,
    refuse: bool = False,
    seen: list | None = None,
    version: str = ahp.PROTOCOL,
    offered: list | None = None,
) -> list[tuple[str, str | None]]:
    """Answer ``initialize`` with ``version``, then ``authenticate``; each method and token is noted before its reply.

    A refused ``authenticate`` gets the spec's AuthRequired error with a long detail; ``offered`` collects the versions
    each ``initialize`` offered. A client that did not offer ``version`` sends no ``authenticate``.
    """
    seen = [] if seen is None else seen
    for _ in range(2):
        msg = _ws_recv(conn)
        seen.append((msg["method"], msg["params"].get("token")))
        if msg["method"] == "initialize" and offered is not None:
            offered.append(msg["params"]["protocolVersions"])
        if refuse and msg["method"] == "authenticate":
            reply = {"error": {"code": -32007, "message": "bad token", "data": {"detail": "x" * 400}}}
        elif msg["method"] == "initialize":
            reply = {"result": {"protocolVersion": version}}
        else:
            reply = {"result": {}}
        _ws_send(conn, {"jsonrpc": "2.0", "id": msg["id"], **reply})
        if version != ahp.PROTOCOL:
            break
    return seen


def test_a_reconnect_reaches_the_same_socket_and_signs_in_again() -> None:
    seen: list[list[tuple[str, str | None]]] = []
    offered: list[list[str]] = []

    def serve(conn: socket.socket) -> None:
        seen.append([])
        _sign_in(conn, seen=seen[-1], offered=offered)  # noted before the reply, so the client cannot return first
        _answer_close(conn)

    path, server = _host(serve, accepts=2)
    first = ahp.connect({"endpoint": {"path": str(path)}, "connectionToken": "secret"}, "c1", "gh-1")
    second = first.reopen("gh-2")
    try:
        assert second is not first
        assert seen == [
            [("initialize", None), ("authenticate", "gh-1")],
            [("initialize", None), ("authenticate", "gh-2")],
        ]
        assert offered == [[ahp.PROTOCOL], [ahp.PROTOCOL]]
        assert first.protocol == second.protocol == "1.0.0"
    finally:
        first.close()
        second.close()
        server.close()


def test_a_failed_sign_in_closes_the_connection() -> None:
    ended: queue.Queue[bytes] = queue.Queue()

    def serve(conn: socket.socket) -> None:
        _sign_in(conn, refuse=True)
        ended.put(_answer_close(conn))

    path, server = _host(serve)
    try:
        with pytest.raises(ahp.HostRefusedError) as refused:
            ahp.connect({"endpoint": {"path": str(path)}, "connectionToken": "secret"}, "c1", "gh")
        got = refused.value
        assert (got.method, got.code, got.message, got.data) == (
            "authenticate",
            -32007,
            "bad token",
            {"detail": "x" * 400},
        )
        assert "x" * 400 in str(got)
        assert ended.get(timeout=5) == b"\x03\xe8"  # a normal close
    finally:
        server.close()


def test_a_version_the_client_did_not_offer_ends_the_sign_in_before_authenticate() -> None:
    ended: queue.Queue[bytes] = queue.Queue()
    seen: list[tuple[str, str | None]] = []

    def serve(conn: socket.socket) -> None:
        _sign_in(conn, seen=seen, version="0.9.0")
        ended.put(_answer_close(conn))

    path, server = _host(serve)
    try:
        with pytest.raises(
            ahp.HostRefusedError, match=r"chose protocol '0\.9\.0', which OwlBear did not offer \(1\.0\.0\)"
        ):
            ahp.connect({"endpoint": {"path": str(path)}, "connectionToken": "secret"}, "c1", "gh")
        assert ended.get(timeout=5) == b"\x03\xe8"
        assert seen == [("initialize", None)]
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
        seqs.extend(_ws_recv(conn)["params"]["clientSeq"] for _ in range(2))
        _answer_close(conn)

    seqs: list[int] = []
    path, server = _host(serve)
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        assert conn.request("listSessions", {}) == {"items": ["listSessions"]}
        assert pongs == [b"hb"]
        assert conn.next_event(1) == {"jsonrpc": "2.0", "method": "action", "params": {"channel": "c"}}
        with pytest.raises(ahp.HostError, match="nope"):
            conn.request("subscribe", {})
        assert [conn.dispatch("c", {"type": "a"}), conn.dispatch("c", {"type": "b"})] == [1, 2]
        conn.close()
        assert seqs == [1, 2]  # the returned seq is the one on the wire
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
        with pytest.raises(ahp.HostError, match="connection closed") as closed:
            conn.request("listSessions", {}, timeout=5)
        assert type(closed.value) is ahp.HostError  # a disconnect is not the host's answer
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
        threading.Event().wait(0.6)  # idle for three opening timeouts, then answer
        _ws_send(conn, {"jsonrpc": "2.0", "id": first["id"], "result": {"ok": True}})
        _answer_close(conn)

    path, server = _host(serve)
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        assert conn.request("listSessions", {}, timeout=5) == {"ok": True}
    finally:
        conn.close()
        server.close()


def test_a_message_over_the_size_limit_ends_the_connection(monkeypatch) -> None:
    monkeypatch.setattr(ahp, "MAX_MESSAGE", 64)
    closes: queue.Queue[bytes] = queue.Queue()

    def serve(conn: socket.socket) -> None:
        _ws_send(conn, {"jsonrpc": "2.0", "method": "action", "params": {"text": "x" * 100}})
        closes.put(_answer_close(conn))

    path, server = _host(serve)
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        event = conn.next_event(5)
        assert event is not None
        assert event["method"] == "closed"
        assert "message too big" in event["params"]["error"]
        assert closes.get(timeout=5)[:2] == (1009).to_bytes(2, "big")
    finally:
        conn.close()
        server.close()


def test_a_host_that_stops_answering_pings_ends_the_connection(monkeypatch) -> None:
    monkeypatch.setattr(ahp, "KEEPALIVE", 0.2)
    monkeypatch.setattr(ahp, "CLOSE_TIMEOUT", 0.2)
    pings: queue.Queue[int] = queue.Queue()

    def serve(conn: socket.socket) -> None:
        pings.put(_ws_frame(conn)[0])
        while conn.recv(4096):  # never answers, reads until the client drops the socket
            pass

    path, server = _host(serve)
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        assert pings.get(timeout=5) == 9
        event = conn.next_event(10)
        assert event is not None
        assert event["method"] == "closed"
        assert "keepalive ping timeout" in event["params"]["error"]
        with pytest.raises(ahp.HostError, match="connection closed"):
            conn.request("listSessions", {}, timeout=5)
    finally:
        conn.close()
        server.close()


def test_a_write_the_host_never_reads_fails_within_the_io_bound(monkeypatch) -> None:
    monkeypatch.setattr(ahp, "IO_TIMEOUT", 0.5)
    release = threading.Event()
    path, server = _host(lambda _conn: release.wait(10))  # upgraded, then reads nothing
    conn = ahp.Connection(str(path), "secret", "owlbear-delivery-test")
    try:
        with pytest.raises(ahp.HostError, match=r"read nothing for 0\.5 s"):
            conn.request("send", {"text": "x" * 2**23}, timeout=30)
        event = conn.next_event(5)
        assert event == {"method": "closed", "params": {"error": "the host read nothing for 0.5 s"}}
    finally:
        release.set()
        conn.close()
        server.close()


def test_endpoint_is_none_without_a_running_editor_host(tmp_path: Path) -> None:
    assert ahp.endpoint(tmp_path / "missing") is None
    (tmp_path / "a.json").write_text('{"endpoint": {"path": "/x"}}')
    assert ahp.endpoint(tmp_path) == {"endpoint": {"path": "/x"}}


def test_connect_uses_a_running_host_without_opening_a_window(tmp_path: Path, monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(ahp, "endpoint", lambda: "entry")
    monkeypatch.setattr(ahp, "connect", lambda entry, _client, _token: calls.append(("connect", entry)) or "conn")
    monkeypatch.setattr(vscode_adapter, "_token", lambda: "t")
    monkeypatch.setattr(vscode_adapter, "launch_code_chat", lambda args, cwd: calls.append(("open", args, cwd)))

    assert vscode_adapter.connect(tmp_path) == "conn"
    assert calls == [("connect", "entry")]


def _entry(path: Path) -> dict:
    return {"endpoint": {"path": str(path)}, "connectionToken": "secret"}


def _gone() -> dict:
    """An endpoint whose editor is gone: its socket file no longer exists."""
    return _entry(Path(tempfile.mkdtemp(dir="/tmp")) / "gone.sock")


def _no_waiting(monkeypatch, sleep: Callable[[float], None]) -> None:
    """Replace the adapter's clock module, so a patched sleep cannot reach the socket threads."""
    monkeypatch.setattr(vscode_adapter, "time", type("Clock", (), {"monotonic": time.monotonic, "sleep": sleep}))


def _refuse_initialize(conn: socket.socket) -> None:
    msg = _ws_recv(conn)
    data = {"supportedVersions": ["0.9.0"], "detail": "x" * 400}
    _ws_send(conn, {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32005, "message": "no", "data": data}})
    _answer_close(conn)


def _refuse_authenticate(conn: socket.socket) -> None:
    _sign_in(conn, refuse=True)
    _answer_close(conn)


@pytest.mark.parametrize(("serve", "code"), [(_refuse_initialize, -32005), (_refuse_authenticate, -32007)])
def test_a_host_refusal_reaches_the_shaping_outcome_whole_without_a_relaunch(
    plain: Path, monkeypatch, caplog, serve: Callable[[socket.socket], None], code: int
) -> None:
    path, server = _host(serve)
    launched: list[list[str]] = []

    def no_sleep(_s: float) -> None:
        pytest.fail("a refusal must not wait for another editor")

    monkeypatch.setattr(ahp, "endpoint", lambda: _entry(path))
    monkeypatch.setattr(vscode_adapter, "_token", lambda: "gh")
    monkeypatch.setattr(readiness, "shaper_path", lambda _home: None)
    monkeypatch.setattr(vscode_adapter, "launch_code_chat", lambda args, _cwd: launched.append(args))
    _no_waiting(monkeypatch, no_sleep)
    try:
        out, warning = vscode_adapter.open_chat(plain, SHAPER, "Shape a brief with me.")
    finally:
        server.close()

    assert (out.end, warning, launched) == ("error", "", [])
    assert out.detail.startswith("HostRefusedError: ")
    assert f"(code {code})" in out.detail
    assert "x" * 400 in out.detail
    assert any(r.name == vscode_adapter.__name__ and r.levelno >= logging.WARNING for r in caplog.records)


def _close_on_initialize(conn: socket.socket) -> None:
    _ws_recv(conn)
    _ws_send(conn, b"\x03\xe8", op=8)
    _ws_frame(conn)


@pytest.mark.parametrize("stale", ["dead socket", "closes while initialize waits"])
def test_a_stale_endpoint_still_starts_vscode_and_connects_to_the_fresh_one(
    tmp_path: Path, monkeypatch, caplog, stale: str
) -> None:
    servers = []
    if stale == "dead socket":
        old = _gone()
    else:
        old_path, old_server = _host(_close_on_initialize)
        old, servers = _entry(old_path), [old_server]

    def serve(conn: socket.socket) -> None:
        _sign_in(conn)
        _answer_close(conn)

    path, server = _host(serve)
    launched: list[list[str]] = []
    monkeypatch.setattr(ahp, "endpoint", lambda: _entry(path) if launched else old)
    monkeypatch.setattr(vscode_adapter, "_token", lambda: "gh")
    monkeypatch.setattr(vscode_adapter, "launch_code_chat", lambda args, _cwd: launched.append(args))
    _no_waiting(monkeypatch, lambda _s: None)
    try:
        conn = vscode_adapter.connect(tmp_path)
        conn.close()
    finally:
        for each in [server, *servers]:
            each.close()

    assert (conn.protocol, launched) == ("1.0.0", [["code", str(tmp_path)]])
    warned = [r.getMessage() for r in caplog.records if r.name == vscode_adapter.__name__ and r.levelname == "WARNING"]
    assert len(warned) == 1
    assert "the published agent host failed: " in warned[0]


def test_without_a_fresh_endpoint_the_timeout_names_why_the_published_one_failed(tmp_path: Path, monkeypatch) -> None:
    gone = _gone()
    monkeypatch.setattr(ahp, "endpoint", lambda: gone)
    monkeypatch.setattr(vscode_adapter, "_token", lambda: "gh")
    monkeypatch.setattr(vscode_adapter, "launch_code_chat", lambda _args, _cwd: None)
    monkeypatch.setattr(vscode_adapter, "START", 0.0)

    with pytest.raises(ahp.HostError) as failed:
        vscode_adapter.connect(tmp_path)
    assert str(failed.value).startswith(
        "VS Code published no agent host within 0 s; before that, the published agent host failed: "
    )
    assert "FileNotFoundError" in str(failed.value)


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


@pytest.fixture
def plain(tmp_path: Path) -> Path:
    """An owner's folder for a step that runs no Git in it."""
    path = tmp_path / "wt"
    path.mkdir()
    return path


SHAPER = carried.layer().agents["shaper"]  # module level runs before the carried-settings fixture
SIZES = {"enum": [200000, 1000000], "enumDescriptions": ["Default", "Longer sessions"], "default": 1000000}


def shaping_host(folder: Path) -> FakeHost:
    host = FakeHost(folder, [{}], [])
    host.models, host.listed = [SHAPER.model], []  # the chat names no agent file, so none needs listing
    host.schema = {"properties": {"thinkingLevel": {"enum": ["high", "xhigh"]}, "contextSize": SIZES}}
    return host


def shaping_env(
    host: FakeHost, during: Callable[[], None] = lambda: None, shaper: Path | None = None
) -> vscode_adapter.Env:
    def launch(args: list[str], cwd: Path) -> None:
        during()
        host.launch(args, cwd)

    return vscode_adapter.Env(
        connect=lambda _f: host, reconnect=lambda _c: host.reconnect(), launch=launch, clock=host.clock, shaper=shaper
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


def test_a_symlinked_shaper_is_selected_by_the_link_path_the_session_lists(plain: Path, tmp_path: Path) -> None:
    target = tmp_path / "runtime" / "owlbear-shaper.agent.md"
    target.parent.mkdir()
    target.write_text("---\nname: owlbear-shaper\n---\n")
    agent = readiness.shaper_path(tmp_path)
    agent.parent.mkdir(parents=True)
    agent.symlink_to(target)  # TD-165: ~/.copilot/agents links into the runtime checkout
    host = shaping_host(plain)
    host.listed = [agent.as_uri()]  # the host lists the link, not its target

    out, warning = shape(plain, shaping_env(host, shaper=agent))

    assert (out.end, warning) == ("started", "")
    ((_, started),) = host.actions("chat/turnStarted")
    assert started["message"]["agent"] == {"uri": agent.as_uri()}
    assert host.launched[0][:4] == ["code", "chat", "-m", "owlbear-shaper"]  # typed messages keep the shaper
    assert not (plain / ".github").exists()  # no project agent file


def test_a_shaper_agent_the_session_does_not_list_starts_no_turn(plain: Path, tmp_path: Path) -> None:
    agent = readiness.shaper_path(tmp_path)
    agent.parent.mkdir(parents=True)
    agent.write_text("---\nname: owlbear-shaper\n---\n")
    host = shaping_host(plain)

    out, _ = shape(plain, shaping_env(host, shaper=agent))

    assert (out.end, out.detail) == ("no-agent", f"the session does not list {agent.resolve().as_uri()}")
    assert host.actions("chat/turnStarted") == []


def test_without_the_installed_shaper_agent_the_chat_never_opens_with_every_tool(plain: Path, tmp_path: Path) -> None:
    host = shaping_host(plain)
    out, warning = shape(plain, shaping_env(host, shaper=readiness.shaper_path(tmp_path)))
    assert (out.end, warning) == ("no-agent", "")
    assert out.detail.startswith("the shaper agent is not installed at")
    assert out.detail.endswith("run `owlbear install`")
    assert host.actions("chat/turnStarted") == []  # nothing launched: an agentless chat would have every tool


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


def test_a_settings_file_delivery_made_keeps_what_the_owner_added_meanwhile(plain: Path) -> None:
    settings = plain / ".vscode" / "settings.json"

    def owner_adds() -> None:
        settings.write_text(settings.read_text().replace("true\n", 'true,\n  "a": 1\n'))

    out, warning = shape(plain, shaping_env(shaping_host(plain), owner_adds))
    assert (out.end, warning, settings.read_text()) == ("started", "", '{\n  "a": 1\n}\n')


@pytest.mark.parametrize("theirs", ['{"chat.defaultToCopilotHarness": false}', "// x\n{}\n"])
def test_the_owners_own_harness_setting_or_an_empty_object_is_kept_byte_for_byte(plain: Path, theirs: str) -> None:
    settings = plain / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(theirs)
    out, warning = shape(plain, shaping_env(shaping_host(plain)))
    assert (out.end, warning, settings.read_text()) == ("started", "", theirs)


def test_a_cleanup_failure_is_a_warning_and_the_chat_still_started(plain: Path) -> None:
    folder = plain / ".vscode"
    out, warning = shape(plain, shaping_env(shaping_host(plain), lambda: folder.chmod(0o555)))
    folder.chmod(0o755)
    assert out.end == "started"
    assert warning.startswith("could not remove chat.defaultToCopilotHarness from .vscode/settings.json")
    assert warning.endswith("remove it by hand")
    assert json.loads((folder / "settings.json").read_text()) == {HARNESS: True}


def test_settings_that_are_not_an_object_refuse_the_shaping_chat_before_launch(plain: Path) -> None:
    settings = plain / ".vscode" / "settings.json"
    settings.parent.mkdir()
    settings.write_text("[]\n")
    host = shaping_host(plain)
    out, warning = shape(plain, shaping_env(host))
    assert (out.end, warning, host.launched, settings.read_text()) == ("settings-refused", "", [], "[]\n")


def test_a_shaping_turn_the_host_never_starts_is_reported(plain: Path) -> None:
    host = shaping_host(plain)
    dispatch = host.dispatch
    host.dispatch = lambda channel, action: None if action["type"] == "chat/turnStarted" else dispatch(channel, action)
    out, _ = shape(plain, shaping_env(host))
    assert (out.end, out.detail) == ("unstarted", "the host did not start the prompt's turn")


def test_an_unreachable_editor_leaves_no_shaping_files(wt: Path) -> None:
    def refuse(_folder: Path) -> ahp.Transport:
        raise HostError("VS Code published no agent host within 60 s")  # noqa: EM101, TRY003

    out, warning = shape(wt, vscode_adapter.Env(connect=refuse, shaper=None))
    assert (out.end, out.detail, warning) == ("error", "HostError: VS Code published no agent host within 60 s", "")
    assert git(wt, "status", "--porcelain", "--ignored") == ""
