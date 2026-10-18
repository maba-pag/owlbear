"""The machine host's process (TD-242): one per machine, paused at start, serving every registered project.

It takes ``~/.owlbear/host.lock``, binds a free loopback port and writes ``~/.owlbear/host.json``; each project
it loads gets its own ``host.json`` with the machine's address and the project's id, so a clone's chat server and
CLI find it and no per-clone host can start beside it.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import socket
import sys
import threading
from datetime import UTC, datetime

import uvicorn

from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.machine_host import app, environment
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.api import link
from owlbear_delivery_next.project_host.host import HostRecord, running_at


def running() -> HostRecord | None:
    """The machine host's record while one runs."""
    return running_at(local_home.root())


def main(_argv: list[str] | None = None) -> int:
    """``python -m owlbear_delivery_next machine``: the process ``owlbear start`` and the login item run."""
    return serve()


def serve() -> int:
    """Run the machine host until it is stopped, or print the running one's URL and exit 0."""
    for name in environment.scrub():
        sys.stdout.write(f"dropped {name} from the environment: a project's own settings decide it\n")
    home = local_home.root()
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    dir_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock_fd = open_lock(dir_fd, blocking=False, name="host.lock")
    except BlockingIOError:
        sys.stdout.write(f"OwlBear is already running: {link(running()) or '(starting)'}\n")
        return 0
    finally:
        os.close(dir_fd)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url, token = f"http://127.0.0.1:{sock.getsockname()[1]}/", secrets.token_urlsafe(32)
    record = HostRecord(url=url, token=token, pid=os.getpid(), started_at=datetime.now(UTC), code=codebase.CURRENT)
    atomic_write(home / "host.json", record.model_dump_json())
    (home / "host.json").chmod(0o600)
    machine = Machine(record)
    machine.say(f"OwlBear {os.getpid()} on {link(record)} · paused until you press Resume")
    machine.load_all()
    threading.Thread(target=machine.retry_loop, daemon=True, name="projects").start()
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning"))
    machine.on_stop = lambda: setattr(server, "should_exit", True)
    try:
        with contextlib.suppress(KeyboardInterrupt):
            server.run(sockets=[sock])
    finally:
        machine.stop_all()
        (home / "host.json").unlink(missing_ok=True)
        os.close(lock_fd)
    return 0
