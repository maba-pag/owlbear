"""One registered project inside the machine host: its store, scheduler, readiness, API and admission gate.

A project that fails to load is listed with its reason and loaded again later; its failure never touches
another project. Stopping one closes its gate first, so no request is admitted and no runner starts, then
waits for what was admitted, wakes and joins its scheduler, and removes its discovery file last.
"""

from __future__ import annotations

import contextlib
import os
import shlex
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from owlbear_delivery_next.commands import setup
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.project_host import api, session_slots
from owlbear_delivery_next.project_host.host import Host, HostRecord, running
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import LockHeldError, Store, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.types import ASGIApp

DRAIN = 30.0  # seconds a stop waits for admitted work
JOIN = 60.0  # seconds a stop waits for the scheduler's current pass
type State = Literal["loading", "loaded", "failed", "replaced", "stopped"]


class Gate:
    """Admission of a project's requests: counted while open; closed, nothing more is admitted."""

    def __init__(self) -> None:
        self.cond = threading.Condition()
        self.count, self.open = 0, True

    def enter(self) -> bool:
        """Admit one operation; False once the gate is closed."""
        with self.cond:
            if self.open:
                self.count += 1
            return self.open

    def leave(self) -> None:
        """End one admitted operation."""
        with self.cond:
            self.count -= 1
            self.cond.notify_all()

    def close(self, timeout: float) -> int:
        """Admit nothing more and wait up to *timeout* for admitted operations; return those still running."""
        with self.cond:
            self.open = False
            self.cond.wait_for(lambda: self.count == 0, timeout)
            return self.count

    def reopen(self) -> None:
        """Admit again, after a refused removal."""
        with self.cond:
            self.open = True


class ImportWaitingError(Exception):
    """The clone's file-format state cannot move to its database yet; loading again later retries."""


class Project:
    """A registered clone as the machine host serves it."""

    def __init__(self, entry: registry.Project) -> None:
        self.entry, self.gate = entry, Gate()
        self.state: State = "loading"
        self.reason = ""
        self.store: Store | None = None
        self.host: Host | None = None
        self.app: ASGIApp | None = None
        self.lock_fd: int | None = None
        self.scheduler: threading.Thread | None = None
        self.publish_lock = threading.Lock()  # orders the discovery file's write against its removal in stop

    @property
    def name(self) -> str:
        """The shared-folder name, else the directory name."""
        return (self.store.name if self.store else "") or Path(self.entry.path).name

    def load(
        self, record: HostRecord, paused: Callable[[], bool], bind: Callable[[Host], None] = lambda _h: None
    ) -> None:
        """Open the clone's store, take its host lock and start its scheduler and readiness check.

        *bind* gives the new scheduler the machine's guards before it starts.
        """
        repo = Path(self.entry.path)
        if why := registry.replaced(self.entry):
            self.state, self.reason = "replaced", why
            return
        try:
            store = Store.open(repo)
            fd = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY)
        except (StoreError, OSError) as exc:
            self.state, self.reason = "failed", f"its Delivery state cannot be opened: {exc}"
            return
        self.store = store  # readable even when another host serves it: this machine's layer must fit it (TD-336)
        try:
            self.lock_fd = open_lock(fd, blocking=False, name="host.lock")
        except BlockingIOError:
            other = running(store)
            self.state = "failed"
            self.reason = f"another Delivery host (process {other.pid if other else '?'}) serves it; stop that one"
            return
        except (OSError, ValueError) as exc:  # a host.lock that is a link or no file
            self.state, self.reason = "failed", f"its host lock cannot be taken: {exc}"
            return
        finally:
            os.close(fd)
        try:
            self._start(store, record, paused, bind)
        except ImportWaitingError as exc:
            self.stop(drain=0)
            self.state, self.reason = "failed", str(exc)
        except Exception as exc:  # noqa: BLE001 - one project's failure never stops the machine
            self.stop(drain=0)
            self.state, self.reason = "failed", f"it could not start: {type(exc).__name__}: {exc}"

    def _start(
        self, store: Store, record: HostRecord, paused: Callable[[], bool], bind: Callable[[Host], None]
    ) -> None:
        repo = Path(self.entry.path)
        self.store = store
        self.host = Host(store, repo, paused=lambda: paused() or not self.gate.open)
        bind(self.host)
        if store.db.waiting():
            self.import_state(store, self.host)
        self.host.record = record.model_copy(update={"pid": os.getpid(), "project": self.entry.id, "ready": None})
        session_slots.join(self.host)  # before its first pass: what its live steps hold is counted first
        self._publish(self.host)
        self.app = api.create_app(store, record.token, self.host)
        self.scheduler = threading.Thread(target=self.host.run, daemon=True, name=f"scheduler-{self.entry.id}")
        self.scheduler.start()
        threading.Thread(target=self._ready, daemon=True, name=f"readiness-{self.entry.id}").start()
        self.state, self.reason = "loaded", ""

    @staticmethod
    def import_state(store: Store, host: Host) -> None:
        """Move the clone's file state into its database (TD-265), under the host lock this project holds.

        Only once no runner of an older OwlBear is alive and with every Change lock held, so nothing writes the
        files while they are read; the database's own fence waits for operations already running.
        """
        slugs = store.db.legacy_slugs()
        if alive := [s for s in slugs if (r := host.runner(s)) and host.alive(r.pid, r.created) is not False]:
            msg = f"its state moves to the database once the running steps of {', '.join(alive)} end"
            raise ImportWaitingError(msg)
        try:
            with contextlib.ExitStack() as held:
                for slug in slugs:
                    held.enter_context(store.lock(slug))
                store.db.import_files()
        except LockHeldError as exc:
            msg = f"its state moves to the database once process {exc.holder.pid if exc.holder else '?'} ends its step"
            raise ImportWaitingError(msg) from exc
        host.say(f"moved the state of {len(slugs)} Change{'s' if len(slugs) != 1 else ''} into the database")

    def _publish(self, host: Host) -> None:
        """Write the discovery file for *host*, only while it is still this project's live, unstopped host."""
        with self.publish_lock:
            if self.store and self.host is host and not host.stopped.is_set():
                path = self.store.root / "host.json"
                atomic_write(path, host.record.model_dump_json())
                path.chmod(0o600)

    def _ready(self) -> None:
        host = self.host
        if not (self.store and host):
            return
        checks = readiness.ready(self.store, Path(self.entry.path), carry=True)
        failed = [f"{c.name}: {c.detail} · fix: {c.fix}" for c in checks if not c.ok]
        host.record = host.record.model_copy(update={"ready": failed})
        self._publish(host)
        host.say("readiness: " + ("; ".join(failed) or "ok"))

    def working(self, *, stopping: bool = False, requests: bool = True) -> list[str]:
        """What keeps the project from being removed: live runners, check environments and admitted work.

        With *stopping* (a stop when idle) also what is not yet confirmed gone: an ended step's processes, a block
        on surviving processes, and an environment whose launch left no PIDs.
        """
        if self.store and self.host and self.store.db.waiting():  # an older OwlBear's runners kept it from loading
            h = self.host
            return [f"{s}: a running step (process {r.pid})" for s in self.store.db.legacy_slugs()
                    if (r := h.runner(s)) and h.alive(r.pid, r.created) is not False]  # fmt: skip
        if not (self.store and self.host and self.app):
            return []
        left = [f"{n} request{'s' if n > 1 else ''}" for n in [self.gate.count] if n and requests]
        left += self.app.state.busy()
        for slug in self.store.slugs():
            rec = self.host.runner(slug)
            if rec and self.host.alive(rec.pid, rec.created) is not False:
                left.append(f"{slug}: a running step (process {rec.pid})")
            elif rec and (stopping or rec.sessions):  # its sessions count until the host confirms them gone
                left.append(f"{slug}: the processes of its ended step")
            with contextlib.suppress(StoreError):
                c = self.store.read(slug)
                if (env := c.env) and (env.pids or (stopping and (env.pgid or env.launched_at))):
                    left.append(f"{slug}: a check environment")
                if stopping and c.blocked and not rec:
                    left.append(f"{slug}: {c.blocked.reason}")
        return left

    def stop(self, *, drain: float = DRAIN, refuse: bool = False) -> list[str]:
        """Close the gate, wait for admitted work, then stop; with *refuse*, keep running while work is left.

        Admitted work is requests in flight and what they started in the background (a shaping chat opening, a
        Impeccable update). A runner outlives a machine stop and finishes on its own (TD-282); a removal is
        refused while one runs.
        """
        until = time.monotonic() + drain
        self.gate.close(drain)
        while self.app is not None and self.app.state.busy() and time.monotonic() < until:
            time.sleep(0.2)
        if self.host is not None:
            with self.host.launching:  # a launch checks the closed gate under this lock, so none starts after it
                if refuse and (left := self.working()):
                    self.gate.reopen()
                    return left
            self.host.stopped.set()
            self.host.wake.set()
            session_slots.leave(self.host)
        try:
            if self.scheduler and self.scheduler.ident is not None:  # one that never started has nothing to join
                self.scheduler.join(JOIN)
            if self.lock_fd is not None and self.store:  # the discovery file is ours only while we hold the lock
                with self.publish_lock:  # a publish in progress finishes first; none starts after the stop above
                    (self.store.root / "host.json").unlink(missing_ok=True)
        finally:
            if self.lock_fd is not None:
                os.close(self.lock_fd)
                self.lock_fd = None
            self.state = "stopped"
        return []

    def info(self) -> dict[str, Any]:
        """The project as the machine's project list shows it; ``setup`` is the command a clone still needs."""
        out: dict[str, Any] = {"id": self.entry.id, "name": self.name, "path": self.entry.path, "state": self.state}
        if self.reason:
            out["reason"] = self.reason
        if self.host:
            out["ready"] = self.host.record.ready
        if self.state == "loaded" and not setup.registered(Path(self.entry.path)):
            out["setup"] = f"owlbear setup --repo {shlex.quote(self.entry.path)}"
        return out
