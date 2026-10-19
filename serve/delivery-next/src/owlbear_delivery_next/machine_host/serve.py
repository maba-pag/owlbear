"""The machine host's process (TD-242): one per machine, serving every registered project.

It starts paused unless ``--run`` asks it to run; a start after a crash is paused all the same (TD-350). A crash is
what leaves ``host.json`` behind: a host that ends any other way removes it.

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
from typing import TYPE_CHECKING

import uvicorn

from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.machine_host import app, environment, registry
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.api import link
from owlbear_delivery_next.project_host.host import HostRecord, running_at

if TYPE_CHECKING:
    from types import FrameType


class Server(uvicorn.Server):
    """Uvicorn, closing every project's gate as soon as a stop is asked for, before requests drain."""

    def __init__(self, config: uvicorn.Config, machine: Machine) -> None:
        """Serve *config* for *machine*."""
        super().__init__(config)
        self.machine = machine

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        """A signal: close the gates, then let Uvicorn shut down (it replays the signal once it has)."""
        self.machine.closing()
        super().handle_exit(sig, frame)

    def stop(self) -> None:
        """The stop route: close the gates and shut down, with no signal to replay."""
        self.machine.closing()
        self.should_exit = True


def running() -> HostRecord | None:
    """The machine host's record while one runs."""
    return running_at(local_home.root())


def main(argv: list[str] | None = None) -> int:
    """``python -m owlbear_delivery_next machine [--run]``: the process ``owlbear start`` and the login item run."""
    return serve(run="--run" in (argv or []))


def serve(*, run: bool = False) -> int:
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
    crashed = (home / "host.json").exists()
    atomic_write(home / "host.json", record.model_dump_json())
    (home / "host.json").chmod(0o600)
    machine = Machine(record, paused=crashed or not run)
    if not machine.paused:
        with contextlib.suppress(registry.RegistryError):
            registry.resumed(record.started_at)
    said = "running" if not machine.paused else "paused until you press Resume"
    machine.say(f"OwlBear {os.getpid()} on {link(record)} · {said}" + (" (the last run crashed)" if crashed else ""))
    machine.load_all()
    threading.Thread(target=machine.retry_loop, daemon=True, name="projects").start()
    threading.Thread(target=machine.idle_loop, daemon=True, name="idle-stop").start()

    def ended() -> None:  # the discovery file goes while this process still holds the lock
        (home / "host.json").unlink(missing_ok=True)

    server = Server(uvicorn.Config(app.create(machine, ended), log_level="warning"), machine)
    machine.on_stop = server.stop
    clean = False
    try:
        with contextlib.suppress(KeyboardInterrupt):
            server.run(sockets=[sock])
        clean = True
    finally:
        machine.stop_all()
        if clean:  # an exception leaves the record behind: the next start is after a crash
            ended()
        os.close(lock_fd)
    return 0
