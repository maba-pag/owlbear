"""The C+ step's result channel in the runner: a loopback receiver that the step's MCP relay finds through an inbox.

The inbox file lives outside the worktree, belongs to one step only and is removed when the step ends, so a relay
left from an earlier step reaches nothing (TD-36).
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, Self

from owlbear_delivery_next import tool_schema

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.results import Gate

MAX_BODY = 1 << 20


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, gate: Gate, token: str) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.gate, self.token = gate, token


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002, ANN401 - the base class's signature
        """Requests are logged by the gate, not on stderr."""

    def _reply(self, code: int, body: object) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _allowed(self) -> bool:
        given = self.headers.get("Authorization", "").encode()
        if hmac.compare_digest(given, f"Bearer {self.server.token}".encode()):
            return True
        self._reply(401, {"error": "unauthorized"})
        return False

    def do_GET(self) -> None:
        """``/tools``: the step's tools with their input schemas."""
        if not self._allowed():
            return
        if self.path != "/tools":
            self._reply(404, {"error": "not found"})
            return
        specs = self.server.gate.specs
        listed = [{"name": s.name, "description": s.description, "inputSchema": tool_schema.schema(s)} for s in specs]
        self._reply(200, {"tools": listed})

    def do_POST(self) -> None:
        """``/call``: one tool call, validated by the step's gate."""
        if not self._allowed():
            return
        length = int(self.headers.get("Content-Length") or 0)
        if self.path != "/call" or not 0 < length <= MAX_BODY:
            self._reply(400, {"text": "Rejected: send one tool call as JSON.", "ok": False})
            return
        try:
            body = json.loads(self.rfile.read(length))
            name, arguments = body["name"], body.get("arguments")
        except ValueError, KeyError, TypeError:
            self._reply(400, {"text": "Rejected: send one tool call as JSON.", "ok": False})
            return
        spec = next((s for s in self.server.gate.specs if s.name == name), None)
        if spec is None:
            self._reply(404, {"text": f"Rejected: {name} is not a tool of this step.", "ok": False})
            return
        text, ok = self.server.gate.call(spec, arguments)
        self._reply(200, {"text": text, "ok": ok})


class Inbox:
    """Serve one step's result tools on loopback while the step runs; the inbox file tells the relay where."""

    def __init__(self, gate: Gate, path: Path) -> None:
        """Bind a free loopback port with a fresh token; nothing is served before ``__enter__``."""
        self.path, self.server = path, _Server(gate, secrets.token_urlsafe(32))

    def __enter__(self) -> Self:
        """Write the inbox, readable by this user only, then start serving."""
        host, port = self.server.server_address[:2]
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump({"url": f"http://{host}:{port}", "token": self.server.token}, f)
        except OSError:
            self.server.server_close()
            raise
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *_exc: object) -> None:
        """Remove the inbox, then stop serving."""
        self.path.unlink(missing_ok=True)
        self.server.shutdown()
        self.server.server_close()
