"""Agent Host Protocol 0.10.0 client over the editor's local socket (TD-34, TD-36).

The WebSocket layer is the ``websockets`` library's sync client over the Unix socket (TD-267), its limits chosen
here rather than left to defaults: one message at most ``MAX_MESSAGE`` bytes, a ping every ``KEEPALIVE`` seconds that
must be answered within as many, ``CLOSE_TIMEOUT`` seconds for the closing handshake and no compression.
A refused or broken handshake is a ``HostError``; an opening that does not finish in ``IO_TIMEOUT`` is a
``TimeoutError``. A write that does not finish in ``IO_TIMEOUT`` (a host that stopped reading) shuts the socket
down, which fails it and ends the connection; reads wait without bound, as an idle host is normal.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import queue
import socket
import threading
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from websockets.exceptions import ConnectionClosed, InvalidHandshake, WebSocketException
from websockets.sync.client import unix_connect

PROTOCOL = "0.10.0"
ROOT = "ahp-root://"
ENTRIES = Path.home() / "Library/Application Support/Code/agent-host/local-endpoint/entries"
IO_TIMEOUT = 15.0  # the opening handshake, and each write
MAX_MESSAGE = 16 * 2**20  # a session's state with its turns; anything larger is a broken host, not a message
KEEPALIVE = 20.0  # seconds between pings, and for each pong: a host that stops answering ends the connection
CLOSE_TIMEOUT = 5.0

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


def _ended(exc: BaseException) -> str:
    """Why the connection ended, in a few words."""
    if isinstance(exc, ConnectionClosed):
        return "server closed" if exc.rcvd is not None else f"closed: {exc}"
    return str(exc) or type(exc).__name__


class Connection:
    """One WebSocket connection: numbered requests, notifications on a queue."""

    def __init__(self, path: str, token: str, client_id: str) -> None:
        """Connect and upgrade; raises ``HostError`` when the host refuses, ``TimeoutError`` when it is silent."""
        self.client_id = client_id
        self._path, self._token = path, token
        try:
            self._ws = unix_connect(
                path, f"ws://localhost/?tkn={quote(token, safe='')}", open_timeout=IO_TIMEOUT, ping_interval=KEEPALIVE,
                ping_timeout=KEEPALIVE, close_timeout=CLOSE_TIMEOUT, max_size=MAX_MESSAGE, compression=None,
                user_agent_header=None, legacy=True,
            )  # fmt: skip
        except InvalidHandshake as exc:
            raise HostError(f"upgrade refused: {exc}") from exc  # noqa: EM102, TRY003
        self._ids, self._seq = itertools.count(1), itertools.count(1)
        self._pending: dict[int, queue.Queue[Json]] = {}
        self._events: queue.Queue[Json] = queue.Queue()
        self._lock = threading.Lock()
        self._closed: str | None = None
        self._stalled: str | None = None
        threading.Thread(target=self._read, daemon=True).start()

    def close(self) -> None:
        """Close the connection; the reader thread ends with a ``closed`` event."""
        with contextlib.suppress(OSError, WebSocketException):
            self._ws.close()

    def reopen(self, github_token: str) -> Connection:
        """A new, signed-in connection to this same host socket; no discovery, so it cannot reach another host."""
        entry = {"endpoint": {"path": self._path}, "connectionToken": self._token}
        return connect(entry, f"{self.client_id}-again", github_token)

    def _read(self) -> None:
        try:
            while True:
                raw = self._ws.recv()
                msg = json.loads(raw)
                if "id" in msg and ("result" in msg or "error" in msg):
                    with self._lock:
                        box = self._pending.pop(msg["id"], None)
                    if box:
                        box.put(msg)
                elif "id" in msg:  # a server request this client does not serve
                    self._send({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "unsupported"}})
                else:
                    self._events.put(msg)
        except (OSError, WebSocketException, HostError, ValueError) as exc:
            why = self._stalled or _ended(exc)
            with self._lock:
                self._closed = why
                waiting, self._pending = list(self._pending.values()), {}
            self._events.put({"method": "closed", "params": {"error": why}})
            for box in waiting:
                box.put({"error": {"message": f"connection closed: {why}"}})

    def _send(self, obj: Json) -> None:
        # The library holds its connection lock while it writes, so neither keepalive nor a close can interrupt a
        # write the host does not read; shutting the socket down from a timer can.
        watchdog = threading.Timer(IO_TIMEOUT, self._stall)
        watchdog.daemon = True
        watchdog.start()
        try:
            self._ws.send(json.dumps(obj))
        except (OSError, WebSocketException) as exc:
            raise HostError(f"connection closed: {self._stalled or _ended(exc)}") from exc  # noqa: EM102, TRY003
        finally:
            watchdog.cancel()

    def _stall(self) -> None:
        self._stalled = f"the host read nothing for {IO_TIMEOUT:g} s"
        with contextlib.suppress(OSError):
            self._ws.socket.shutdown(socket.SHUT_RDWR)

    def request(self, method: str, params: Json, timeout: float = 60) -> Json:
        """Send one request and wait for its answer; raises ``HostError`` on error, timeout or a closed connection."""
        rid, box = next(self._ids), queue.Queue[Json]()
        with self._lock:
            if self._closed is not None:
                raise HostError(f"{method}: connection closed: {self._closed}")  # noqa: EM102, TRY003
            self._pending[rid] = box
        try:
            self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
            msg = box.get(timeout=timeout)
        except HostError as exc:
            raise HostError(f"{method}: {exc}") from exc  # noqa: EM102, TRY003
        except queue.Empty:
            raise HostError(f"{method}: no answer in {timeout}s") from None  # noqa: EM102, TRY003
        finally:
            with self._lock:
                self._pending.pop(rid, None)
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
    try:
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
    except BaseException:
        conn.close()
        raise
    return conn
