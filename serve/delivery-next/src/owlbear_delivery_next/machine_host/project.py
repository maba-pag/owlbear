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
from owlbear_delivery_next.machine_host import registry
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, HostRecord, running
from owlbear_delivery_next.runtimes import readiness
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

    @property
    def name(self) -> str:
        """The shared-folder name, else the directory name."""
        return (self.store.name if self.store else "") or Path(self.entry.path).name

    def load(self, record: HostRecord, paused: Callable[[], bool]) -> None:
        """Open the clone's store, take its host lock and start its scheduler and readiness check."""
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
            self._start(store, record, paused)
        except ImportWaitingError as exc:
            self.stop(drain=0)
            self.state, self.reason = "failed", str(exc)
        except Exception as exc:  # noqa: BLE001 - one project's failure never stops the machine
            self.stop(drain=0)
            self.state, self.reason = "failed", f"it could not start: {type(exc).__name__}: {exc}"

    def _start(self, store: Store, record: HostRecord, paused: Callable[[], bool]) -> None:
        repo = Path(self.entry.path)
        self.store = store
        self.host = Host(store, repo, paused=lambda: paused() or not self.gate.open)
        if store.db.waiting():
            self.import_state(store, self.host)
        self.host.record = record.model_copy(update={"pid": os.getpid(), "project": self.entry.id, "ready": None})
        self._publish()
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

    def _publish(self) -> None:
        if self.store and self.host and not self.host.stopped.is_set():
            path = self.store.root / "host.json"
            atomic_write(path, self.host.record.model_dump_json())
            path.chmod(0o600)

    def _ready(self) -> None:
        if not (self.store and self.host):
            return
        checks = readiness.ready(self.store, Path(self.entry.path))
        failed = [f"{c.name}: {c.detail} · fix: {c.fix}" for c in checks if not c.ok]
        self.host.record = self.host.record.model_copy(update={"ready": failed})
        self._publish()
        self.host.say("readiness: " + ("; ".join(failed) or "ok"))

    def working(self) -> list[str]:
        """What keeps the project from being removed: live runners, check environments and admitted work."""
        if not (self.store and self.host and self.app):
            return []
        left = [f"{n} request{'s' if n > 1 else ''}" for n in [self.gate.count] if n]
        left += self.app.state.busy()
        for slug in self.store.slugs():
            rec = self.host.runner(slug)
            if rec and self.host.alive(rec.pid, rec.created) is not False:
                left.append(f"{slug}: a running step (process {rec.pid})")
            with contextlib.suppress(StoreError):
                if (env := self.store.read(slug).env) and env.pids:
                    left.append(f"{slug}: a check environment")
        return left

    def stop(self, *, drain: float = DRAIN, refuse: bool = False) -> list[str]:
        """Close the gate, wait for admitted work, then stop; with *refuse*, keep running while work is left.

        Admitted work is requests in flight and what they started in the background (a shaping chat opening, a
        design pack update). A runner outlives a machine stop and finishes on its own (TD-282); a removal is
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
        try:
            if self.scheduler and self.scheduler.ident is not None:  # one that never started has nothing to join
                self.scheduler.join(JOIN)
            if self.lock_fd is not None and self.store:  # the discovery file is ours only while we hold the lock
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
