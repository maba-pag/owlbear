"""Agent Host Protocol 0.10.0 client over the editor's local socket; stdlib only (TD-34, TD-36)."""

from __future__ import annotations

import base64
import itertools
import json
import os
import queue
import socket
import struct
import threading
from pathlib import Path
from typing import Any, Protocol

PROTOCOL = "0.10.0"
ROOT = "ahp-root://"
ENTRIES = Path.home() / "Library/Application Support/Code/agent-host/local-endpoint/entries"
_CLOSE, _PING, _PONG = 8, 9, 10

type Json = dict[str, Any]


class Transport(Protocol):
    """What the step driver needs from a host connection; tests supply a fake."""

    def request(self, method: str, params: Json, timeout: float = 60) -> Json: ...  # noqa: D102
    def dispatch(self, channel: str, action: Json) -> None: ...  # noqa: D102
    def next_event(self, timeout: float) -> Json | None: ...  # noqa: D102


def endpoint(entries: Path = ENTRIES) -> Json | None:
    """The newest editor agent-host registry entry, or None when no editor host runs."""
    files = sorted(entries.glob("*.json"), key=lambda p: p.stat().st_mtime) if entries.is_dir() else []
    return json.loads(files[-1].read_text()) if files else None


class HostError(RuntimeError):
    """The host refused a request or the connection ended."""


class Connection:
    """One WebSocket connection: numbered requests, notifications on a queue."""

    def __init__(self, path: str, token: str, client_id: str) -> None:
        """Connect and upgrade; raises ``HostError`` when the host refuses."""
        self.client_id = client_id
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(path)
        key = base64.b64encode(os.urandom(16)).decode()
        self._sock.sendall(
            (
                f"GET /?tkn={token} HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self._sock.recv(1)
            if not chunk:
                raise HostError("closed during upgrade")  # noqa: EM101, TRY003
            head += chunk
        status = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise HostError(status.decode(errors="replace"))
        self._ids, self._seq = itertools.count(1), itertools.count(1)
        self._pending: dict[int, queue.Queue[Json]] = {}
        self._events: queue.Queue[Json] = queue.Queue()
        self._lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def close(self) -> None:
        """Close the socket; the reader thread ends with a ``closed`` event."""
        self._sock.close()

    def _exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise HostError("closed")  # noqa: EM101
            buf += chunk
        return buf

    def _frame(self) -> Json:
        parts = b""
        while True:
            b0, b1 = self._exact(2)
            op, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:  # noqa: PLR2004 - WebSocket 16-bit length marker
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:  # noqa: PLR2004 - WebSocket 64-bit length marker
                n = struct.unpack(">Q", self._exact(8))[0]
            payload = self._exact(n)
            if op == _CLOSE:
                raise HostError("server closed")  # noqa: EM101, TRY003
            if op in (_PING, _PONG):
                continue
            parts += payload
            if b0 & 0x80:
                return json.loads(parts)

    def _read(self) -> None:
        try:
            while True:
                msg = self._frame()
                if "id" in msg and ("result" in msg or "error" in msg):
                    box = self._pending.pop(msg["id"], None)
                    if box:
                        box.put(msg)
                elif "id" in msg:  # a server request this client does not serve
                    self._send({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "unsupported"}})
                else:
                    self._events.put(msg)
        except (OSError, HostError, ValueError) as exc:
            self._events.put({"method": "closed", "params": {"error": str(exc)}})
            for box in list(self._pending.values()):
                box.put({"error": {"message": f"connection closed: {exc}"}})

    def _send(self, obj: Json) -> None:
        data, mask = json.dumps(obj).encode(), os.urandom(4)
        n = len(data)
        if n < 126:  # noqa: PLR2004 - WebSocket 7-bit length
            head = bytes([0x81, 0x80 | n])
        elif n < 65536:  # noqa: PLR2004 - WebSocket 16-bit length
            head = bytes([0x81, 0x80 | 126]) + struct.pack(">H", n)
        else:
            head = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", n)
        with self._lock:
            self._sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def request(self, method: str, params: Json, timeout: float = 60) -> Json:
        """Send one request and wait for its answer; raises ``HostError`` on error or timeout."""
        rid, box = next(self._ids), queue.Queue[Json]()
        self._pending[rid] = box
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        try:
            msg = box.get(timeout=timeout)
        except queue.Empty:
            self._pending.pop(rid, None)
            raise HostError(f"{method}: no answer in {timeout}s") from None  # noqa: EM102, TRY003
        if "error" in msg:
            raise HostError(f"{method}: {msg['error'].get('message', msg['error'])}")  # noqa: EM102, TRY003
        return msg["result"]

    def dispatch(self, channel: str, action: Json) -> None:
        """Send one action; the host answers with an action notification or a rejection."""
        self._send(
            {
                "jsonrpc": "2.0",
                "method": "dispatchAction",
                "params": {"channel": channel, "clientSeq": next(self._seq), "action": action},
            }
        )

    def next_event(self, timeout: float) -> Json | None:
        """The next notification, or None after ``timeout`` seconds."""
        try:
            return self._events.get(timeout=timeout)
        except queue.Empty:
            return None


def connect(entry: Json, client_id: str, github_token: str) -> Connection:
    """Connect, initialize and authenticate; the model list fills only after ``authenticate`` (P3)."""
    conn = Connection(entry["endpoint"]["path"], entry["connectionToken"], client_id)
    conn.request(
        "initialize",
        {
            "channel": ROOT,
            "protocolVersions": [PROTOCOL],
            "clientId": client_id,
            "clientInfo": {"name": "owlbear-delivery"},
            "initialSubscriptions": [ROOT],
        },
    )
    conn.request("authenticate", {"channel": ROOT, "resource": "https://api.github.com", "token": github_token})
    return conn
