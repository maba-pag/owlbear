"""The machine host's process (TD-242): one per machine, serving every registered project.

It starts paused unless ``--run`` asks it to run; a start after a crash is paused all the same (TD-350). A crash is
what leaves ``host.json`` behind: a host that ends any other way removes it, unless it hands over to a new version,
which starts with the old one's address, token and state instead (self-update §5.4).

It takes ``~/.owlbear/host.lock``, binds a free loopback port and writes ``~/.owlbear/host.json``; each project
it loads gets its own ``host.json`` with the machine's address and the project's id, so a clone's chat server and
CLI find it and no per-clone host can start beside it.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import uvicorn

from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.machine_host import alias, app, environment, handover, registry, versions
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.api import link
from owlbear_delivery_next.project_host.host import HostRecord, running_at

if TYPE_CHECKING:
    from pathlib import Path
    from types import FrameType


class Server(uvicorn.Server):
    """Uvicorn, closing every project's gate as soon as a stop is asked for, before requests drain."""

    def __init__(self, config: uvicorn.Config, machine: Machine) -> None:
        """Serve *config* for *machine*."""
        super().__init__(config)
        self.machine = machine

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        """A signal: close the gates, then let Uvicorn shut down (it replays the signal once it has)."""
        self.machine.say(f"stopping: {signal.Signals(sig).name} received")
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
    """``python -m owlbear_delivery_next machine [--run | --standby]``: ``owlbear start``, the login item, an update.

    The dispatcher re-executed a host started through the runtime alias from its version's own folder, so a later
    switch of the alias never changes the code it loads (self-update §3).
    """
    args = argv or []
    if "--standby" in args:  # an update's new version: it takes over once the old host says so (§5.2)
        version = args[args.index("--standby") + 1] if len(args) > args.index("--standby") + 1 else ""
        return serve(handing=True) if handover.standby(version) else 0
    if "--takeover" in args:  # an update's forward restart: the handover file still names the old address (§5.5)
        return serve(handing=True)
    return serve(run="--run" in args)


def _lock(home: Path, *, wait: float) -> int | None:
    """``host.lock`` held, waiting up to *wait* seconds for the host handing over to release it; None when held."""
    deadline = time.monotonic() + wait
    while True:
        dir_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
        try:
            return open_lock(dir_fd, blocking=False, name="host.lock")
        except BlockingIOError:
            if time.monotonic() >= deadline:
                return None
        finally:
            os.close(dir_fd)
        time.sleep(0.2)


def _bind(port: int) -> socket.socket:
    """The loopback socket: *port* when handed over (its old host just closed it), else a free one."""
    deadline = time.monotonic() + (10 if port else 0)
    while True:
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            sock.close()
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)
            continue
        return sock


def serve(*, run: bool = False, handing: bool = False) -> int:
    """Run the machine host until it is stopped, or print the running one's URL and exit 0.

    *handing*: this new version takes over from the host that started it as its standby (§5.4).
    """
    for name in environment.scrub():
        sys.stdout.write(f"dropped {name} from the environment: a project's own settings decide it\n")
    home = local_home.root()
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_fd = _lock(home, wait=handover.HEALTH if handing else 0)
    if lock_fd is None:
        sys.stdout.write(f"OwlBear is already running: {link(running()) or '(starting)'}\n")
        return 0
    given = handover.taken() if handing else None
    alias.complete()  # before any store opens: a half-done first migration, and the mark (§3, §4)
    pruned = _pruned()
    sock = _bind(given.port if given else 0)
    machine = _machine(home, sock, given, run=run)
    if pruned:
        machine.say(f"removed old versions: {', '.join(pruned)}")
    machine.load_all()
    threading.Thread(target=machine.retry_loop, daemon=True, name="projects").start()
    threading.Thread(target=machine.idle_loop, daemon=True, name="idle-stop").start()
    threading.Thread(target=machine.auto.loop, daemon=True, name="idle-update").start()

    def ended() -> None:  # the discovery file goes while this process still holds the lock; a handover keeps it
        if machine.handover is None:
            (home / "host.json").unlink(missing_ok=True)

    server = Server(uvicorn.Config(app.create(machine, ended), log_level="warning"), machine)
    machine.on_stop = server.stop
    clean = False
    try:
        with contextlib.suppress(KeyboardInterrupt):
            server.run(sockets=[sock])
        clean = True
    finally:
        if not clean:
            machine.say("stopping: the server failed (its error follows)")
        machine.stop_all()
        if clean:  # an exception leaves the record behind: the next start is after a crash
            ended()
        os.close(lock_fd)
    if machine.handover is not None:
        _handed(machine, *machine.handover)
    return 0


def _pruned() -> list[str]:
    """The old versions removed at this start (§3); a failure is said, never fatal."""
    try:
        return versions.prune()
    except (OSError, versions.VersionError) as exc:
        return [f"none: {exc}"]


def _machine(home: Path, sock: socket.socket, given: handover.Handover | None, *, run: bool) -> Machine:
    """The machine with its record written: the old host's address, token and state when handed over (TD-299)."""
    url = f"http://127.0.0.1:{sock.getsockname()[1]}/"
    token = given.token if given else secrets.token_urlsafe(32)
    record = HostRecord(url=url, token=token, pid=os.getpid(), started_at=datetime.now(UTC), code=codebase.CURRENT)
    crashed = given is None and (home / "host.json").exists()
    atomic_write(home / "host.json", record.model_dump_json())
    (home / "host.json").chmod(0o600)
    machine = Machine(record, paused=given.paused if given else crashed or not run)
    if given:
        machine.ending, machine.updated = given.ending, given.version
    elif not machine.paused:
        with contextlib.suppress(registry.RegistryError):
            registry.resumed(record.started_at)
    said = "running" if not machine.paused else "paused until you press Resume"
    now = f" · now {given.version}" if given else " (the last run crashed)" if crashed else ""
    machine.say(f"OwlBear {os.getpid()} on {link(record)} · {said}{now}")
    return machine


def _handed(machine: Machine, standby: handover.Standby, given: handover.Handover) -> None:
    """After the old host let go (§5.4, §5.5): the standby takes over.

    Without every project loaded in time the new version is started once more from the alias, never the older one
    (TD-305).
    """
    handover.write(given)
    if standby.take_over() and handover.watch(given):
        machine.say(f"handed over to {given.version}")
        return
    machine.say(f"{given.version} did not take over within {handover.HEALTH:.0f} s; starting it again from the alias")
    standby.kill()  # a candidate that holds the lock but serves nothing must not keep it
    handover.write(given)  # it may have read the file: the forward restart takes over the same address and state
    python = local_home.root() / local_home.RUNTIME / ".venv" / "bin" / "python"
    with (local_home.root() / "host.log").open("ab") as out:
        subprocess.Popen(  # noqa: S603 - the alias's interpreter and a fixed module
            [str(python), "-m", "owlbear_delivery_next", "machine", "--takeover"],
            cwd=local_home.root(), stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
            start_new_session=True,
        )  # fmt: skip
