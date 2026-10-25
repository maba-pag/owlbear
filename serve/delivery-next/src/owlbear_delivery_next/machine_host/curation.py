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
import threading
import uuid
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from owlbear_memory import MemoryEngine, MemoryState
from pydantic import Field

from owlbear_delivery_next.change_contracts import memory_curation_tools, tools
from owlbear_delivery_next.change_contracts.memory_curation_tools import Judged  # noqa: TC001 - a field's type
from owlbear_delivery_next.change_contracts.models import Record, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import data_repo, local_home, maintenance
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.machine_host import machine_settings, registry
from owlbear_delivery_next.runtimes import maintained, sdk_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import Settings, SettingsUnset
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.local_system.slots import Slots
    from owlbear_delivery_next.runtimes.session_result import Run

LABEL = "memory-curation"
STATE = "curation.json"
SLOT = "memory"  # curation's own share of the machine's slots
ALL = "all"
type Trigger = Literal["merge", "idle"]  # each has its own machine setting (the owner, 2026-10-23)
type Asked = Literal["manual"] | Trigger  # "Curate now" bypasses the automatic switches and pause, never a fence
NO_SHARED = "no shared repository is set up, so there is no memory to curate"
PAUSED = "the machine is paused, and this automatic trigger does not curate while paused; it waits for a later trigger"
OFF = "this automatic trigger is off in the machine settings; it waits until it is turned on"
LEFT = "the last curation's processes may still run; stop them before curating again"
LINGERING = "memory curation: its last session's processes may still run"
INTERRUPTED = "interrupted: OwlBear stopped while it ran or waited"
UNKNOWN = "its processes could not be identified, so none could be confirmed gone; check for a stray copilot process"


class FolderRun(Record):
    """One folder's last run: its state, when, the curator's report and what it left as it was."""

    state: str = "never"  # waiting, running, done, failed
    started_at: datetime | None = None
    ended_at: datetime | None = None
    summary: str = ""
    reason: str = ""
    key: str = ""  # the ledger's source for an uncertain run; empty when an older host ended it before the ledger
    entries: list[Judged] = Field(default_factory=list)
    skipped: dict[str, str] = Field(default_factory=dict)  # entry id: its revision when the curator skipped it
    seen: dict[str, str] = Field(default_factory=dict)  # every entry still pending after the run: id to revision


class Runs(Record):
    """Every folder's last run, kept in ``~/.owlbear`` because it is this machine's work."""

    folders: dict[str, FolderRun] = Field(default_factory=dict)
    left: dict[int, float | None] = Field(default_factory=dict)  # a run's processes not yet confirmed gone


def message(folder: str) -> str:
    """What one automatic run is asked: its folder, the workflow being the agent file's."""
    return (
        f"Curate: automatic. Your memory server is bound to the folder `{folder}` of the shared repository, with "
        "Global memory beside it. Curate it as your agent file says, then commit and submit your report."
    )


def folders(root: Path) -> list[str]:
    """The project folders of the shared repository that keep memory, Global's own folder never among them."""
    found = (p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and not p.name.startswith("."))
    own = (p for p in found if p.name != "memory" and (p / "memory").is_dir() and not (p / "memory").is_symlink())
    return sorted(p.name for p in own)  # a link never leads a run to Global or out of the repository


def _run(cfg: sdk_adapter.Session) -> Run:
    return asyncio.run(sdk_adapter.run(cfg))


class Curation:
    """The machine's automatic curation: a queue of folders, one session at a time."""

    def __init__(  # noqa: PLR0913, PLR0917 - the machine's seams: the slots, its fence, pause, stop barrier and runner
        self,
        slots: Slots,
        shared: Callable[[], data_repo.DataRepo | None] = data_repo.locate,
        run: Callable[[sdk_adapter.Session], Run] = _run,
        fenced: Callable[[], str] = str,
        paused: Callable[[], bool] = lambda: False,
        admission: Callable[[], AbstractContextManager[object]] = nullcontext,
        ownership: maintenance.Maintenance | None = None,
    ) -> None:
        """Runs a restart interrupted end as failed; their processes, if any, still count until they are gone.

        *admission* is the machine's stop barrier: a run is admitted or refused under it, so a stop when idle sees
        every admitted run. It is taken before ``lock``, never after.
        """
        self.slots, self.shared, self.run, self.fenced, self.paused = slots, shared, run, fenced, paused
        self.admission = admission
        self.lock = threading.RLock()
        self.queue, self.worker, self.running = list[str](), None, ""
        self.asked: dict[str, Asked] = {}  # each queued folder's trigger, read again at its grant
        self.again: dict[str, Trigger] = {}  # a running folder's follow-up, when an automatic trigger asks for one
        runs = self.load()
        self.maintenance = ownership or maintenance.Maintenance(slots)
        self.maintenance.adopt(
            str(self.path()),
            SLOT,
            "curation",
            runs.left,
            interrupted=any(r.state == "running" for r in runs.folders.values()),
        )
        for name, r in runs.folders.items():
            # The run's ledger lease, or its one-time import; its key keeps a recovered run from being imported again.
            if legacy_uncertain(r):
                source = f"{self.path()}#{name}:{r.started_at}"
                lease = self.maintenance.adopt_uncertain(
                    source,
                    SLOT,
                    "curation",
                    workspace="",
                    covers=_same_run(name, r),
                )
                runs.folders[name] = r.model_copy(update={"key": lease.slot})
        for name, r in runs.folders.items():
            if r.state in {"waiting", "running"}:
                runs.folders[name] = r.model_copy(update={"state": "failed", "reason": INTERRUPTED})
        self.left = dict(runs.left)
        self._write(runs)

    def path(self) -> Path:
        """Where the runs are kept."""
        return local_home.root() / STATE

    def load(self) -> Runs:
        """Every folder's last run; none when the file is missing or unreadable."""
        try:
            return Runs.model_validate_json(self.path().read_text())
        except FileNotFoundError:
            return Runs()
        except (OSError, ValueError) as exc:
            msg = f"the memory curation ownership record cannot be read: {exc}"
            raise maintenance.MaintenanceError(msg) from exc

    def _write(self, runs: Runs) -> None:
        self.path().parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.path(), runs.model_dump_json(indent=2) + "\n")

    def _save(self, folder: str, run: FolderRun) -> None:
        with self.lock:
            runs = self.load()
            runs.folders[folder] = run
            runs.left = dict(self.left)
            self._write(runs)

    def read(self) -> dict[str, Any]:
        """Each folder of the shared repository with its last run, and what waits."""
        shared = self.shared()
        if shared is None:
            return {"available": False, "reason": NO_SHARED, "folders": []}
        runs = self.load().folders
        listed = [{"folder": f, **runs.get(f, FolderRun()).model_dump(mode="json")} for f in folders(shared.root)]
        return {"available": True, "folders": listed, "queue": list(self.queue)}

    def _pids(self, event: dict[str, Any]) -> None:
        """Keep the session's processes on file as it records them, so a host that stops meanwhile still knows them."""
        if event.get("event") != "pids":
            return
        with self.lock:
            self.left |= {int(p): c for p, c in event.get("pids", {}).items()}
            runs = self.load()
            runs.left = dict(self.left)
            self._write(runs)

    def lingering(self) -> bool:
        """Whether a run's processes may still run; the ledger alone decides, PIDs left after a recovery are history."""
        with self.lock:
            if self.maintenance.pending("curation"):
                return True
            if self.left:
                self.left = {}
                runs = self.load()
                runs.left = {}
                self._write(runs)
            return False

    def working(self) -> list[str]:
        """What runs, waits or may still run, for an update or a stop when idle to wait for."""
        with self.lock:
            busy = [f"memory curation: {', '.join(self.queue)}"] if self.queue else []
        return busy + ([LINGERING] if self.lingering() else [])

    def due(self, folder: str) -> bool:
        """Whether *folder* holds a pending entry, or a changed one, that no finished run saw."""
        shared = self.shared()
        if shared is None:
            return False
        seen = self.load().folders.get(folder, FolderRun()).seen
        return any(seen.get(e.id) != e.revision for e in _pending(shared.root / folder / "memory"))

    def allowed(self, trigger: Trigger) -> bool:
        """Whether a merge or idle time may start a run now: its machine setting on, and while paused set so."""
        try:
            settings = machine_settings.current()
        except registry.RegistryError:
            return False
        said = settings.curate_after_merge if trigger == "merge" else settings.curate_when_idle  # unset: no run
        return said == "paused" or (said == "on" and not self.paused())

    def _refusal(self, trigger: Trigger) -> str:
        """Why an automatic *trigger* was refused: PAUSED only when its own switch is on and the machine is paused."""
        try:
            settings = machine_settings.current()
        except registry.RegistryError:
            return OFF
        said = settings.curate_after_merge if trigger == "merge" else settings.curate_when_idle
        return PAUSED if said == "on" and self.paused() else OFF

    def nudge(self, wanted: list[str] | None, trigger: Trigger) -> list[str]:
        """Start each of *wanted* (every folder for None) that is due, when *trigger* may start runs now.

        A folder waiting for its slot already runs once with its own trigger, so it gets no second run. A folder
        already running gets one more run after it, if it is still due then.
        """
        shared = self.shared()
        if shared is None or not self.allowed(trigger):
            return []
        known = folders(shared.root)
        candidates = [f for f in (known if wanted is None else wanted) if f in known]
        with self.lock:
            self.again |= {f: trigger for f in candidates if f == self.running}
            free = [f for f in candidates if f not in self.queue]
        return [f for one in free if self.due(one) for f in self.start(one, trigger)]

    def start(self, folder: str, asked: Asked = "manual") -> list[str]:
        """Queue *folder*, or every folder for ``all``; a folder already waiting keeps its place.

        A manual request for a folder waiting (not running) for its slot takes that place over: it runs once, with
        the manual trigger, and no second run is queued.
        """
        shared = self.shared()
        if shared is None:
            raise ValueError(NO_SHARED)
        known = folders(shared.root)
        wanted = known if folder == ALL else [folder]
        if not set(wanted) <= set(known):
            msg = f"the shared repository has no memory folder {folder}"
            raise ValueError(msg)
        with self.lock:
            if asked == "manual":
                for f in wanted:
                    if f in self.queue and f != self.running:
                        self.asked[f] = "manual"
            added = [f for f in wanted if f not in self.queue]
            for f in added:  # shown waiting before the worker can end its run
                self._save(f, self.load().folders.get(f, FolderRun()).model_copy(update={"state": "waiting"}))
                self.asked[f] = asked
            self.queue.extend(added)
            if self.worker is None:  # a worker clears this under the lock as it ends, so none is ever missed
                self.worker = threading.Thread(target=self._work, name="memory-curation", daemon=True)
                self.worker.start()
        return added

    def _work(self) -> None:
        while True:
            with self.lock:
                if not self.queue:
                    self.worker = None
                    return
                folder = self.queue[0]
            started = datetime.now(UTC)
            refused = False
            try:
                refused = self._one(folder, started)
            except Exception as exc:  # noqa: BLE001 - one folder's failure never strands the others
                why = f"{type(exc).__name__}: {exc}"[:300]
                self._save(
                    folder, FolderRun(state="failed", started_at=started, ended_at=datetime.now(UTC), reason=why)
                )
            with self.lock:  # a follow-up joins before the run leaves, so the queue never looks empty between
                trigger = self.again.pop(folder, None)
                # a Curate now that landed after this automatic request was refused is not lost: it runs once
                manual = refused and self.asked.get(folder) == "manual"
                again = trigger is not None and self.due(folder)
                self.running = ""
                self.queue.remove(folder)
                self.asked.pop(folder, None)
                if manual or again:
                    self._save(
                        folder, self.load().folders.get(folder, FolderRun()).model_copy(update={"state": "waiting"})
                    )
                    self.queue.append(folder)
                    self.asked[folder] = "manual" if manual else trigger

    def _one(self, folder: str, started: datetime) -> bool:
        """Run one folder's curation; True when an automatic request was refused its admission."""
        shared = self.shared()
        why = NO_SHARED if shared is None else LEFT if self.lingering() else self.fenced()
        why = why or _unset(lookup.machine(shared))  # checked again on the snapshot it starts with
        if shared is None or why:
            self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=why))
            return False
        turn, key = threading.Event(), f"curate:{folder}:{uuid.uuid4().hex}"  # one generation per admission
        while True:
            turn.clear()  # cleared before the take, so a wake during it is never lost
            if self.slots.take(SLOT, key, 1, 1, wake=turn.set):
                break
            if why := self.fenced():  # an update or a stop came while it waited: it never starts
                self.slots.cancel(SLOT, key)
                self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=why))
                return False
            turn.wait(5)
        with self.admission():  # the stop barrier: a stop when idle sees this run admitted, or it is refused here
            why = self.fenced()
            with self.lock:  # the automatic switches are read at the grant, not when the request was made
                asked = self.asked.get(folder, "manual")
                admitted = not why and (asked == "manual" or self.allowed(asked))
                self.running = folder if admitted else ""
        if why:
            self.slots.give(SLOT, key)
            self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=why))
            return False
        if not admitted:  # the folder stays due, so a later allowed trigger runs it
            self.slots.give(SLOT, key)
            prior = self.load().folders.get(folder, FolderRun())  # keeps what the last finished run left pending
            why = self._refusal(asked)
            update = {"state": "failed", "started_at": started, "ended_at": started, "reason": why}
            self._save(folder, prior.model_copy(update=update))
            return True
        try:
            self._save(folder, FolderRun(state="running", started_at=started))
            self._save(folder, self._session(shared, folder, started, key))
        finally:
            if not self.maintenance.held(SLOT, key):
                self.slots.give(SLOT, key)
        return False

    def _session(self, shared: data_repo.DataRepo, folder: str, started: datetime, key: str) -> FolderRun:
        settings = lookup.machine(shared)
        if why := _unset(settings):  # cleared while it waited for its slot: the run never starts, its entries unseen
            return FolderRun(state="failed", started_at=started, ended_at=datetime.now(UTC), reason=why)
        role = roles.chosen(settings, LABEL)
        store = shared.root / folder / "memory"
        before = {e.id: e.revision for e in _pending(store)}  # what the curator can see when it starts
        with self.maintenance.workspace("owlbear-curation-") as at:
            said = message(folder)
            cfg = sdk_adapter.Session(
                kind=StepKind.REVIEW, worktree=at, session_id=f"{LABEL}-{folder}-{uuid.uuid4().hex[:8]}",
                message=said, fresh=said, resume=False, policy=Policy(at, write=False),
                observe=lambda: tools.Worktree("", ""), checks=(), submit=memory_curation_tools.SUBMIT,
                model=role.model, effort=role.effort, context=role.context, limit=roles.limit(settings, LABEL),
                subagents=roles.subagents(settings, LABEL),
                role=tools.CURATOR, job=LABEL, journal=sdk_adapter.Journal(event=self._pids), memory=store,
            )  # fmt: skip
            done = maintained.run_owned(self.maintenance, cfg, self.run, project=SLOT, slot=key, kind="curation")
        t = done.termination
        with self.lock:
            watched = dict.fromkeys((*t.survivors, *t.unknown)) | done.pids if t is not None and not t.confirmed else {}
            self.left = watched
            runs = self.load()
            runs.left = dict(self.left)
            self._write(runs)
        unknown = not (t and t.confirmed)
        ended = datetime.now(UTC)
        report = done.payload if isinstance(done.payload, memory_curation_tools.MemoryCurationResult) else None
        if done.ending != "result" or report is None or unknown:
            why = " ".join((done.detail or "no report was submitted").split())[:300]
            why = f"{UNKNOWN}; {why}" if unknown else why
            return FolderRun(
                state="failed",
                started_at=started,
                ended_at=ended,
                reason=f"ended {done.ending}: {why}",
                key=key if unknown else "",
            )
        with shared.locked():
            notice = shared.publish([], f"memory {folder}: curation")  # push what the curator committed
        after = {e.id: e.revision for e in _pending(store)}
        seen = {i: r for i, r in after.items() if before.get(i) == r}  # one saved or changed meanwhile stays due
        skipped = {
            j.entry_id: after[j.entry_id] for j in report.entries if j.action == "skipped" and j.entry_id in after
        }
        return FolderRun(
            state="done", started_at=started, ended_at=ended, summary=report.summary, reason=notice,
            entries=report.entries, skipped=skipped, seen=seen,
        )  # fmt: skip


def _pending(store: Path) -> list[Any]:
    """The folder's pending entries; none when it has no memory yet."""
    if not store.is_dir():
        return []
    return [e for e in MemoryEngine(store).get_entries() if e.state == MemoryState.PENDING]


def legacy_uncertain(run: FolderRun) -> bool:
    """A failed run whose termination an older host left unknown, and which the ledger has never recorded."""
    return run.state == "failed" and UNKNOWN in run.reason and not run.key


def _same_run(folder: str, run: FolderRun) -> Callable[[maintenance.Lease], bool]:
    """Whether a lease is the very generation this row records.

    It must be this folder's slot and begin inside the row's own window. The producer takes the row's start while it
    waits for a slot and begins the lease later, inside the run; a lease from an earlier or later run begins outside
    that window, whatever its state.
    """

    def covers(lease: maintenance.Lease) -> bool:
        if lease.project != SLOT or lease.kind != "curation" or not lease.slot.startswith(f"curate:{folder}:"):
            return False
        if run.started_at is None or run.ended_at is None:
            return False
        return run.started_at <= lease.started_at <= run.ended_at

    return covers


def _unset(settings: Settings) -> str:
    """Why a run cannot start for unset settings: the curator's role or its threshold; empty when both are set."""
    try:
        agent = settings.agent(roles.SESSIONS[LABEL])
        settings.need("curator_threshold")
    except SettingsUnset as exc:
        return str(exc)
    if agent.subagents is None:  # set per role: a run never guesses whether its subagents may start
        return f"agents.{roles.SESSIONS[LABEL]}.subagents is unset"
    return ""
