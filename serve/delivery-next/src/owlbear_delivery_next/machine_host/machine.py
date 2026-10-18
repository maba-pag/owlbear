"""The machine host's state (TD-242): its record, the projects it serves and whether Delivery is paused.

Every start is paused (TD-259); only the owner's Resume in the UI unpauses it, and the Resume is recorded.
"""

from __future__ import annotations

import sys
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_flow.status import RESUME, status
from owlbear_delivery_next.machine_host import registry
from owlbear_delivery_next.machine_host.project import Project
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.project_host.host import Host, HostRecord

RETRY = 60.0  # seconds between loads of a project that failed to load


class MachineError(Exception):
    """A request about a project this machine refuses; ``status`` is the HTTP answer."""

    def __init__(self, status: int, text: str) -> None:
        """Keep the answer's status and words."""
        super().__init__(text)
        self.status, self.text = status, text


class Machine:
    """Every registered project, loaded once; requests about them are serialized by ``lock``."""

    def __init__(self, record: HostRecord) -> None:
        """Start paused, with no project loaded yet."""
        self.record, self.paused = record, True
        self.projects: dict[str, Project] = {}
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.on_stop: Callable[[], None] = lambda: None

    def say(self, text: str) -> None:
        """Write one line to the machine host's log."""
        sys.stdout.write(f"{datetime.now(UTC):%H:%M:%S} {text}\n")
        sys.stdout.flush()

    def _load(self, entry: registry.Project) -> Project:
        if self.stopping.is_set():
            raise MachineError(503, "OwlBear is stopping")
        p = self.projects[entry.id] = Project(entry)
        try:
            p.load(self.record, lambda: self.paused or self.stopping.is_set())
        except Exception as exc:  # noqa: BLE001 - one project's failure never stops the machine
            p.state, p.reason = "failed", f"it could not load: {type(exc).__name__}: {exc}"
        if p.host:
            p.host.peers = lambda: self.sharing(p)
        self.say(f"{p.name}: {p.state}" + (f": {p.reason}" if p.reason else ""))
        return p

    def sharing(self, p: Project) -> list[Host]:
        """The schedulers of the machine's other clones whose shared settings folder is *p*'s."""
        mine = p.store
        if not (mine and mine.shared):
            return []
        return [
            o.host
            for o in list(self.projects.values())
            if o is not p and o.host and o.store and o.store.shared
            and o.store.shared.root == mine.shared.root and o.store.name == mine.name
        ]  # fmt: skip

    def load_all(self) -> None:
        """Load every registered project; one that fails is listed with its reason."""
        with self.lock:
            for entry in registry.load().projects:
                self._load(entry)

    def retry(self) -> None:
        """Load again each project that failed or was replaced."""
        with self.lock:
            for p in [p for p in self.projects.values() if p.state in {"failed", "replaced"}]:
                if not self.stopping.is_set():
                    self._load(p.entry)

    def retry_loop(self) -> None:
        """Thread: retry failed projects every ``RETRY`` seconds until the machine stops."""
        while not self.stopping.wait(RETRY):
            try:
                self.retry()
            except Exception as exc:  # noqa: BLE001 - the loop outlives one failed pass
                self.say(f"loading projects again failed: {type(exc).__name__}: {exc}")

    def get(self, pid: str) -> Project:
        """The registered project *pid*."""
        if (p := self.projects.get(pid)) is None:
            raise MachineError(404, f"no project {pid} is registered")
        return p

    def register(self, path: Path) -> Project:
        """Register the clone at *path* and load it."""
        with self.lock:
            try:
                entry = registry.register(path)
            except registry.RegistryError as exc:
                raise MachineError(409, str(exc)) from exc
            return self._load(entry)

    def remove(self, pid: str) -> None:
        """Stop and forget a project; refused, naming them, while its steps or admitted work still run."""
        with self.lock:
            p = self.get(pid)
            if left := p.stop(refuse=True):
                raise MachineError(409, f"{p.name} still runs {', '.join(left)}; remove it once they end")
            registry.remove(pid)
            del self.projects[pid]
            self.say(f"{p.name}: removed")

    def adopt(self, pid: str) -> Project:
        """Let the clone now at a replaced project's path take its place."""
        with self.lock:
            p = self.get(pid)
            if p.state != "replaced":
                raise MachineError(409, f"{p.name} is {p.state}, not replaced")
            try:
                entry = registry.adopt(pid)
            except registry.RegistryError as exc:
                raise MachineError(409, str(exc)) from exc
            del self.projects[pid]
            return self._load(entry)

    def resume(self) -> None:
        """The owner's Resume: work starts again in every project."""
        registry.resumed(datetime.now(UTC))
        self.paused = False
        self.say("resumed by you")
        for p in list(self.projects.values()):
            if p.host:
                p.host.wake.set()

    def waiting(self) -> int:
        """How many Changes would continue on Resume."""
        now, n = datetime.now(UTC), 0
        for p in list(self.projects.values()):
            if not (p.store and p.host and p.state == "loaded"):
                continue
            try:
                slugs = p.store.slugs()
            except StoreError:
                continue
            for slug in slugs:
                try:
                    n += status(p.store.read(slug), p.host.activity(slug), now).action == RESUME
                except StoreError:
                    continue
        return n

    def closing(self) -> None:
        """The machine stops: every gate closes at once, so nothing is admitted or launched from now on."""
        self.stopping.set()
        for p in list(self.projects.values()):
            p.gate.close(0)

    def stop_all(self) -> None:
        """Close every gate, then stop each project; live runners finish on their own (TD-282)."""
        self.closing()
        with self.lock:  # a load in flight finishes first, so its project is stopped too
            for p in self.projects.values():
                if p.state != "stopped":
                    p.stop()
        self.say("stopped: every project closed")
