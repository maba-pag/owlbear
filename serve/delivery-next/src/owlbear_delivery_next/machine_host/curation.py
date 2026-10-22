"""Automatic memory curation (item 5 slice 4; TD-292, TD-400): one curator session per memory folder.

A run binds the memory server to one project folder of the shared repository, OwlBear's own included (TD-435), with
Global memory beside it, and gives the curator role its automatic workflow. The job keeps each folder's last run, its
report and what it saw in ``~/.owlbear/curation.json``, one run at a time, each holding one of the machine's
session slots (TD-336). The Maintenance page's button starts it now. A merge starts its project's folder, and idle time
every folder, when the folder holds a pending entry no run has seen; while paused only with "Curate memory while
paused" on (the owner, 2026-10-22). An entry a run left pending starts no other run until it changes.
"""

from __future__ import annotations

import asyncio
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_memory import MemoryEngine, MemoryState
from pydantic import Field

from owlbear_delivery_next.change_contracts import memory_curation_tools, tools
from owlbear_delivery_next.change_contracts.memory_curation_tools import Judged  # noqa: TC001 - a field's type
from owlbear_delivery_next.change_contracts.models import Record, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import data_repo, local_home, processes
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.machine_host import registry
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.local_system.slots import Slots
    from owlbear_delivery_next.runtimes.session_result import Run

LABEL = "memory-curation"
STATE = "curation.json"
SLOT = "memory"  # curation's own share of the machine's slots
ALL = "all"
NO_SHARED = "no shared repository is set up, so there is no memory to curate"
LEFT = "the last curation's processes may still run; stop them before curating again"


class FolderRun(Record):
    """One folder's last run: its state, when, the curator's report and what it left as it was."""

    state: str = "never"  # waiting, running, done, failed
    started_at: datetime | None = None
    ended_at: datetime | None = None
    summary: str = ""
    reason: str = ""
    entries: list[Judged] = Field(default_factory=list)
    skipped: dict[str, str] = Field(default_factory=dict)  # entry id: its revision when the curator skipped it
    seen: dict[str, str] = Field(default_factory=dict)  # every entry still pending after the run: id to revision


class Runs(Record):
    """Every folder's last run, kept in ``~/.owlbear`` because it is this machine's work."""

    folders: dict[str, FolderRun] = Field(default_factory=dict)


def message(folder: str) -> str:
    """What one automatic run is asked: its folder, the workflow being the agent file's."""
    return (
        f"Curate: automatic. Your memory server is bound to the folder `{folder}` of the shared repository, with "
        "Global memory beside it. Curate it as your agent file says, then commit and submit your report."
    )


def folders(root: Path) -> list[str]:
    """The project folders of the shared repository that keep memory, Global's own folder never among them."""
    found = (p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and not p.name.startswith("."))
    return sorted(p.name for p in found if p.name != "memory" and (p / "memory").is_dir())


def _run(cfg: sdk_adapter.Session) -> Run:
    return asyncio.run(sdk_adapter.run(cfg))


class Curation:
    """The machine's automatic curation: a queue of folders, one session at a time."""

    def __init__(
        self,
        slots: Slots,
        shared: Callable[[], data_repo.DataRepo | None] = data_repo.locate,
        run: Callable[[sdk_adapter.Session], Run] = _run,
        fenced: Callable[[], str] = str,
    ) -> None:
        """No run yet; *run* runs one session, replaced in tests; *fenced* says why nothing may start now."""
        self.slots, self.shared, self.run, self.fenced = slots, shared, run, fenced
        self.lock, self.queue, self.worker = threading.Lock(), list[str](), None
        self.left: dict[int, float | None] = {}  # an unconfirmed run's processes, until they are seen gone

    def path(self) -> Path:
        """Where the runs are kept."""
        return local_home.root() / STATE

    def load(self) -> Runs:
        """Every folder's last run; none when the file is missing or unreadable."""
        try:
            return Runs.model_validate_json(self.path().read_text())
        except OSError, ValueError:
            return Runs()

    def _save(self, folder: str, run: FolderRun) -> None:
        with self.lock:
            runs = self.load()
            runs.folders[folder] = run
            self.path().parent.mkdir(parents=True, exist_ok=True)
            atomic_write(self.path(), runs.model_dump_json(indent=2) + "\n")

    def read(self) -> dict[str, Any]:
        """Each folder of the shared repository with its last run, and what waits."""
        shared = self.shared()
        if shared is None:
            return {"available": False, "reason": NO_SHARED, "folders": []}
        runs = self.load().folders
        listed = [{"folder": f, **runs.get(f, FolderRun()).model_dump(mode="json")} for f in folders(shared.root)]
        return {"available": True, "folders": listed, "queue": list(self.queue)}

    def working(self) -> list[str]:
        """What runs or waits, for an update or a stop when idle to wait for."""
        with self.lock:
            return [f"memory curation: {', '.join(self.queue)}"] if self.queue else []

    def due(self, folder: str) -> bool:
        """Whether *folder* holds a pending entry, or a changed one, that no finished run saw."""
        shared = self.shared()
        if shared is None:
            return False
        seen = self.load().folders.get(folder, FolderRun()).seen
        return any(seen.get(e.id) != e.revision for e in _pending(shared.root / folder / "memory"))

    def allowed(self, *, paused: bool) -> bool:
        """Whether a merge or idle time may start a run now: while paused only with the machine's switch on."""
        if not paused:
            return True
        try:
            return registry.load().settings.curate_while_paused
        except registry.RegistryError:
            return False

    def nudge(self, wanted: list[str] | None, *, paused: bool) -> list[str]:
        """Start each of *wanted* (every folder for None) that is due, when a trigger may start runs now."""
        shared = self.shared()
        if shared is None or not self.allowed(paused=paused):
            return []
        known = folders(shared.root)
        due = [f for f in (known if wanted is None else wanted) if f in known and f not in self.queue and self.due(f)]
        return [f for one in due for f in self.start(one)]

    def start(self, folder: str) -> list[str]:
        """Queue *folder*, or every folder for ``all``; a folder already waiting keeps its place."""
        shared = self.shared()
        if shared is None:
            raise ValueError(NO_SHARED)
        known = folders(shared.root)
        wanted = known if folder == ALL else [folder]
        if not set(wanted) <= set(known):
            msg = f"the shared repository has no memory folder {folder}"
            raise ValueError(msg)
        with self.lock:
            added = [f for f in wanted if f not in self.queue]
        for f in added:  # shown waiting before the worker can end its run
            self._save(f, self.load().folders.get(f, FolderRun()).model_copy(update={"state": "waiting"}))
        with self.lock:
            self.queue.extend(f for f in added if f not in self.queue)
            if self.worker is None or not self.worker.is_alive():
                self.worker = threading.Thread(target=self._work, name="memory-curation", daemon=True)
                self.worker.start()
        return added

    def _work(self) -> None:
        while True:
            with self.lock:
                if not self.queue:
                    return
                folder = self.queue[0]
            try:
                self._one(folder)
            finally:
                with self.lock:
                    self.queue.remove(folder)

    def _one(self, folder: str) -> None:
        started = datetime.now(UTC)
        shared = self.shared()
        if shared is None:
            self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=NO_SHARED))
            return
        if self.left and not processes.verdict(self.left, processes.alive).confirmed:
            self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=LEFT))
            return
        if why := self.fenced():
            self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=why))
            return
        turn, key = threading.Event(), f"curate:{folder}"
        while not self.slots.take(SLOT, key, 1, 1, wake=turn.set):
            turn.wait(5)
            turn.clear()
        try:
            self._save(folder, FolderRun(state="running", started_at=started))
            self._save(folder, self._session(shared, folder, started))
        finally:
            self.slots.give(SLOT, key)

    def _session(self, shared: data_repo.DataRepo, folder: str, started: datetime) -> FolderRun:
        settings = lookup.machine(shared)
        role = roles.chosen(settings, LABEL)
        store = shared.root / folder / "memory"
        with tempfile.TemporaryDirectory(prefix="owlbear-curation-") as empty:
            at = Path(empty)
            said = message(folder)
            cfg = sdk_adapter.Session(
                kind=StepKind.REVIEW, worktree=at, session_id=f"{LABEL}-{folder}-{uuid.uuid4().hex[:8]}",
                message=said, fresh=said, resume=False, policy=Policy(at, write=False),
                observe=lambda: tools.Worktree("", ""), checks=(), submit=memory_curation_tools.SUBMIT,
                model=role.model, effort=role.effort, context=role.context, limit=roles.limit(settings, LABEL),
                role=tools.CURATOR, job=LABEL, journal=sdk_adapter.Journal(), memory=store,
            )  # fmt: skip
            done = self.run(cfg)
        t = done.termination
        self.left = {} if t is None or t.confirmed else dict.fromkeys((*t.survivors, *t.unknown)) | done.pids
        ended = datetime.now(UTC)
        report = done.payload if isinstance(done.payload, memory_curation_tools.MemoryCurationResult) else None
        if done.ending != "result" or report is None:
            why = " ".join((done.detail or "no report was submitted").split())[:300]
            return FolderRun(state="failed", started_at=started, ended_at=ended, reason=f"ended {done.ending}: {why}")
        with shared.locked():
            notice = shared.publish([], f"memory {folder}: curation")  # push what the curator committed
        left = {e.id: e.revision for e in _pending(store)}
        skipped = {j.entry_id: left[j.entry_id] for j in report.entries if j.action == "skipped" and j.entry_id in left}
        return FolderRun(
            state="done", started_at=started, ended_at=ended, summary=report.summary, reason=notice,
            entries=report.entries, skipped=skipped, seen=left,
        )  # fmt: skip


def _pending(store: Path) -> list[Any]:
    """The folder's pending entries; none when it has no memory yet."""
    if not store.is_dir():
        return []
    return [e for e in MemoryEngine(store).get_entries() if e.state == MemoryState.PENDING]
