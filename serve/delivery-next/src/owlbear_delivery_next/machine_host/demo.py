"""``owlbear demo``: the machine host's pages on example data, for browsing only.

It serves the projects ``demo_home.seed`` registered without their schedulers or readiness checks, so no step,
runner or AI session starts; every request that is not a GET or HEAD is refused before any route runs, with one plain
sentence. Settings' outside reads answer from example state: no Copilot runtime starts. Only the demo's pages carry
the token's bootstrap, so its addresses open without ``#token=``.
"""

from __future__ import annotations

import os
import secrets
import shutil
import socket
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import uvicorn
from starlette.responses import JSONResponse

from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import app, demo_home
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.project import Project
from owlbear_delivery_next.project_host import pages
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.state_store import registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from starlette.types import ASGIApp, Receive, Scope, Send

    from owlbear_delivery_next.project_host.host import Host

REFUSED = "This is OwlBear's demo on example data: it only shows pages, so nothing here starts, answers or saves."
READS = frozenset({"GET", "HEAD"})


def _model(mid: str, name: str, context: int, rates: tuple[float, float], efforts: list[str]) -> dict[str, Any]:
    return {
        "id": mid, "name": name, "efforts": efforts, "default_effort": efforts[len(efforts) // 2] if efforts else "",
        "context": context, "long": None,
        "rates": {"input": rates[0], "output": rates[1], "cache": rates[0] / 10, "cache_write": None,
                  "cache_write_1h": None},
    }  # fmt: skip


MODELS = [
    _model("claude-opus-5.5", "Claude Opus 5.5", 952_000, (5.0, 25.0), ["low", "medium", "high", "xhigh"]),
    _model("gpt-6.1-sol", "GPT-6.1 Sol", 400_000, (1.25, 10.0), ["low", "medium", "high"]),
    _model("claude-haiku-5.5", "Claude Haiku 5.5", 200_000, (1.0, 5.0), []),
    _model("gpt-6-luna", "GPT-6 Luna", 272_000, (0.25, 2.0), ["low", "medium", "high"]),
]


class Offered(model_choices.Offered):
    """The offered models from example state, never through a Copilot runtime."""

    def __call__(self) -> dict[str, Any]:
        """The example models, read without error."""
        return {"models": MODELS, "error": ""}

    def refresh(self) -> dict[str, Any]:
        """The same example models."""
        return self()


class Browse:
    """Refuse every request that is not a GET or HEAD, before any route runs: the demo only shows pages."""

    def __init__(self, inner: ASGIApp) -> None:
        """Wrap the machine host's app."""
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass reads and the lifespan on; answer anything else with the refusal."""
        if scope["type"] == "http" and scope.get("method") not in READS:
            await JSONResponse({"detail": REFUSED}, 403)(scope, receive, send)
            return
        await self.inner(scope, receive, send)


def _seeded(token: str) -> None:
    """Each page the demo serves gets the token's bootstrap right after ``<head>``, before the page's own modules."""
    seed = f'<script>sessionStorage.setItem("token", "{token}")</script>'
    served = pages.pages
    pages.pages = lambda: {path: html.replace("<head>", "<head>" + seed, 1) for path, html in served().items()}


def _load(machine: Machine) -> None:
    """Each registered project, served without its scheduler or readiness check, bound as the machine binds it."""
    for entry in registry.load().projects:
        p = machine.projects[entry.id] = Project(entry)

        def bind(h: Host, p: Project = p) -> None:
            h.peers = lambda: machine.sharing(p)
            h.machine = machine.reads.stores
            h.reads = machine.reads
            h.draining = lambda: machine.ending
            h.closed = lambda: machine.stopping.is_set() or not p.gate.open
            h.updating = lambda: machine.updating
            h.slots = machine.slots
            h.maintenance = machine.maintenance
            h.merged = lambda: machine.curation.nudge([h.store.name], "merge")
            h.curating = machine.curation.fence

        p.scheduled = False
        p.load(machine.record, lambda: False, bind)
        machine.say(f"{p.name}: {p.state}" + (f": {p.reason}" if p.reason else ""))


def run(home: Path, port: int, say: Callable[[str], None]) -> int:
    """Serve the demo seeded in *home* on 127.0.0.1:*port* (0: a free port) until stopped, then remove *home*."""

    def gone() -> None:
        shutil.rmtree(home, ignore_errors=True)

    try:
        demo_home.seed(home)
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        base, token = f"http://127.0.0.1:{sock.getsockname()[1]}", secrets.token_urlsafe(16)
        _seeded(token)
        now = datetime.now(UTC)
        record = HostRecord(url=f"{base}/", token=token, pid=os.getpid(), started_at=now, code=codebase.CURRENT)
        machine = Machine(record, paused=False)
        machine.reads.offered = Offered()
        machine.reads.ledger.finish({}, [], unshared=False, at=now.astimezone())  # Settings shows a read, not none
        _load(machine)
        say(f"OwlBear demo on example data: {base}/#token={token}")
        say("Browse only: nothing starts, answers or saves here. Ctrl-C stops it and removes its example data.")
        sys.stdout.flush()  # the address is the recipe's ready signal, even through a pipe
        server = uvicorn.Server(uvicorn.Config(Browse(app.create(machine, gone)), log_level="warning"))
        server.run(sockets=[sock])  # its shutdown stops every project and removes HOME: a stop signal is replayed
    finally:
        gone()
    return 0
