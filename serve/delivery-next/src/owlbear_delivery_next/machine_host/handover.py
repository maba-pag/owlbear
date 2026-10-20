"""The handover between two versions' hosts (self-update build §5.2, §5.4, §5.5; TD-296, TD-299, TD-305).

The new version first runs as a **standby**: started from its own folder, it takes no lock, binds a private loopback
port and answers ``GET /health`` with its version, so the old host knows it starts. Once the alias names it, the old
host closes every gate and project, writes ``handover.json`` (its port, token and state), releases the machine's lock
and tells the standby to take over: the standby takes the lock, binds the old port with the old token, so open pages
keep working, and loads the projects as they were. The old process then watches for every project to load; without
that in 60 s it starts the new version once more from the alias, never the older one.
"""

from __future__ import annotations

import contextlib
import hmac
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from pathlib import Path

HANDOVER, STANDBY = "handover.json", "standby.json"
SECRET = "OWLBEAR_STANDBY"  # noqa: S105 - the name of the variable that passes the standby's secret, never written
HEALTH = 60.0  # seconds a standby has to answer, and the new host to load every project (§5.2, §5.5)
IDLE_STANDBY = 900.0  # seconds a standby waits for its takeover before it ends
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Handover(BaseModel):
    """What the old host passes on: its address and token, Delivery's state and the projects it had loaded."""

    model_config = ConfigDict(extra="forbid")

    port: int
    token: str
    paused: bool
    ending: bool  # a stop when idle the owner asked for carries over (§6)
    version: str  # the version taking over, said once on the pages (TD-299)
    loaded: list[str]


def write(handover: Handover) -> None:
    """``~/.owlbear/handover.json``, readable only by the owner."""
    path = local_home.root() / HANDOVER
    atomic_write(path, handover.model_dump_json())
    path.chmod(0o600)


def taken() -> Handover | None:
    """The handover a new host starts from, removed as it is read; None for an ordinary start."""
    path = local_home.root() / HANDOVER
    try:
        found = Handover.model_validate_json(path.read_text())
    except OSError, ValueError:
        return None
    path.unlink(missing_ok=True)
    return found


def _call(url: str, secret: str, method: str = "GET") -> dict[str, Any] | None:
    request = urllib.request.Request(url, method=method, headers={"X-Standby": secret})  # noqa: S310 - loopback
    try:
        with _LOCAL.open(request, timeout=5) as response:
            return json.load(response)
    except OSError, ValueError:
        return None


class Standby:
    """The old host's handle on a standby it started: its process, its address and its secret."""

    def __init__(self, python: Path, folder: Path, version: str, log: Path) -> None:
        """Start the standby of *version* from its own folder, with a fresh secret."""
        self.secret, self.url = os.urandom(24).hex(), ""
        self.file = local_home.root() / STANDBY
        self.file.unlink(missing_ok=True)
        with log.open("ab") as out:
            self.proc = subprocess.Popen(  # noqa: S603 - the version's own interpreter and a fixed module
                [str(python), "-m", "owlbear_delivery_next", "machine", "--standby", version], cwd=folder,
                env={**os.environ, SECRET: self.secret}, stdin=subprocess.DEVNULL, stdout=out,
                stderr=subprocess.STDOUT, start_new_session=True,
            )  # fmt: skip

    def healthy(self, timeout: float = HEALTH) -> dict[str, Any] | None:
        """Its health once it answers within *timeout*; None when it ended or never answered."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and self.proc.poll() is None:
            with contextlib.suppress(OSError, ValueError, KeyError):
                self.url = self.url or json.loads(self.file.read_text())["url"]
            if self.url and (said := _call(f"{self.url}health", self.secret)) is not None:
                return said
            time.sleep(0.2)
        return None

    def take_over(self) -> bool:
        """Tell it to take over now; whether it said it would."""
        return bool(self.url) and _call(f"{self.url}takeover", self.secret, "POST") is not None

    def stop(self) -> None:
        """End it: the update waits for another time."""
        if self.url:
            _call(f"{self.url}quit", self.secret, "POST")
        with contextlib.suppress(subprocess.TimeoutExpired):
            self.proc.wait(10)
        if self.proc.poll() is None:
            self.proc.kill()
        self.file.unlink(missing_ok=True)

    def kill(self) -> None:
        """End the process whatever it does now, a host that took over included; its steps run on (TD-282)."""
        with contextlib.suppress(ProcessLookupError):
            os.kill(self.proc.pid, signal.SIGTERM)
        with contextlib.suppress(subprocess.TimeoutExpired):
            self.proc.wait(30)
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(10)
        self.file.unlink(missing_ok=True)


def standby(version: str) -> bool:
    """Run as a standby until the old host says to take over (True) or to quit, or nobody does (False)."""
    secret = os.environ.pop(SECRET, "")
    told: list[bool] = []

    class Handler(BaseHTTPRequestHandler):
        def _answer(self, body: dict[str, Any]) -> None:
            if not hmac.compare_digest(self.headers.get("X-Standby", ""), secret) or not secret:
                self.send_error(401)
                return
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._answer({"version": version, "pid": os.getpid()})
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            if self.path in {"/takeover", "/quit"} and hmac.compare_digest(self.headers.get("X-Standby", ""), secret):
                told.append(self.path == "/takeover")
                self._answer({"ok": True})
                threading.Thread(target=server.shutdown, daemon=True).start()
            else:
                self.send_error(404)

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    path = local_home.root() / STANDBY
    atomic_write(path, json.dumps({"url": f"http://127.0.0.1:{server.server_address[1]}/", "pid": os.getpid()}))
    path.chmod(0o600)
    timer = threading.Timer(IDLE_STANDBY, server.shutdown)
    timer.start()
    sys.stdout.write(f"standby for {version} on port {server.server_address[1]}\n")
    sys.stdout.flush()
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        timer.cancel()
        server.server_close()
        path.unlink(missing_ok=True)
    return bool(told and told[0])


def watch(handover: Handover, timeout: float = HEALTH) -> bool:
    """Whether the new host serves every project the old one had loaded, loaded, within *timeout*."""
    url = f"http://127.0.0.1:{handover.port}/api/next/projects"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {handover.token}"})
        with contextlib.suppress(OSError, ValueError, KeyError):
            with _LOCAL.open(request, timeout=5) as response:
                listed = {p["id"]: p["state"] for p in json.load(response)["projects"]}
            if all(listed.get(pid) == "loaded" for pid in handover.loaded):
                return True
        time.sleep(0.5)
    return False
