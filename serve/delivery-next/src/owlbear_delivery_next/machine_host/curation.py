"""Automatic memory curation (item 5 slice 4; TD-292, TD-400): one curator session per memory folder.

A run binds the memory server to one project folder of the shared repository, OwlBear's own included (TD-435), with
Global memory beside it, and gives the curator role its automatic workflow. The job keeps each folder's last run, its
report and what it saw in ``~/.owlbear/curation.json``, one run at a time, each holding one of the machine's
session slots (TD-336). The Maintenance page's button starts it now. A merge starts its project's folder, and idle time
every folder, when the folder holds a pending entry no run has seen; while paused only with "Curate memory while
paused" on (the owner, 2026-10-22). An entry a run left pending starts no other run until it changes. A rename of a
project's folder waits until no curation of it runs or waits, and no run starts in a folder while it moves (#678).
A run works on its own worktree of the repository; only an accepted run's edits reach the shared checkout (#746).
"""

from __future__ import annotations

import logging
import threading
import uuid
from contextlib import AbstractContextManager, contextmanager, nullcontext
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from owlbear_memory import MemoryEngine, MemoryState

from owlbear_delivery_next.change_contracts import memory_curation_tools, tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import data_repo, local_home, maintenance
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.machine_host import curation_snapshots, curation_tree
from owlbear_delivery_next.runtimes import loop_owner, maintained, sdk_adapter
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.settings.config import Settings, SettingsUnset
from owlbear_delivery_next.state_store import machine_settings, registry, spend_ledger
from owlbear_delivery_next.state_store.curation_runs import STATE, FolderRun, Runs
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from owlbear_delivery_next.local_system.slots import Slots
    from owlbear_delivery_next.runtimes.session_result import Run

_log = logging.getLogger(__name__)

LABEL = "memory-curation"
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
CURATING = "memory curation of {folder} runs or waits; rename once it has finished"
LEFT_RENAME = "the last memory curation's processes may still run; rename once they are gone"
MOVED = "its folder is being renamed or is gone; curate it again under its new name"  # in curation_snapshots.REFUSALS
UNKNOWN = "its processes could not be identified, so none could be confirmed gone; check for a stray copilot process"


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
    return loop_owner.run(sdk_adapter.run(cfg))


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
        self.renaming = set[str]()  # folders a rename holds: none of them is admitted
        runs = self.load()
        self.maintenance = ownership or maintenance.Maintenance(slots)
        if runs.left_key and not self.maintenance.records(SLOT, "curation", runs.left_key, runs.left):
            runs.left_key = ""  # the lease it names does not record these PIDs, so the key proves nothing
        # A cached key counts only while the lease it names owns its row; an earlier build named a snapshot's lease in
        # its rows, which proves nothing of them, so such a row is judged again as one no lease of ours names.
        for name, r in runs.folders.items():
            if r.key and not curation_snapshots.owns_row(SLOT, self.maintenance.lease(SLOT, r.key), name, r):
                runs.folders[name] = r.model_copy(update={"key": ""})
        # Each uncertain row is its own session's evidence, held under its own lease: a snapshot's PIDs say nothing of
        # which session left them, and rows seen beside it are no proof that any of them is that session.
        behind = {n: r for n, r in runs.folders.items() if legacy_uncertain(r) or (r.state == "running" and not r.key)}
        if runs.left and not runs.left_key:
            # A snapshot no lease of ours names is a producer's own observation. Its PIDs and session evidence are
            # what that producer wrote: a lease that saw these PIDs and every session row still on file covers it in
            # any state, though refusals since overwrote some; a later session's row is held anew.
            snapshot, seen = curation_snapshots.observed(runs), curation_snapshots.sessions(runs)
            lease = self.maintenance.adopt_uncertain(
                f"{self.path()}#left", SLOT, "curation", workspace="", generation=snapshot, pids=runs.left,
                covers=curation_snapshots.same_snapshot(SLOT, snapshot, seen), observed=seen,
            )  # fmt: skip
            runs.left_key = lease.slot
        for name, r in behind.items():
            # A row's own mark finds its lease after a lost key write, in any state, so a recovered one stays so; a
            # mark counts only while that lease records this row's evidence. Each row is judged before it is rewritten
            # below, so the rewrite never erases what an older host held.
            lease = self.maintenance.adopt_uncertain(
                self._row(name, r), SLOT, "curation", workspace="", keyed=True,
                covers=curation_snapshots.recorded_row(SLOT, name, r), observed=(curation_snapshots.window(name, r),),
            )  # fmt: skip
            runs.folders[name] = r.model_copy(update={"key": lease.slot})
        for name, r in runs.folders.items():
            if r.state not in {"waiting", "running"}:
                continue
            update: dict[str, object] = {"state": "failed", "reason": INTERRUPTED}
            if r.state == "waiting" and not r.key:  # judged: no uncertain session, so its copied times go with it
                update |= {"started_at": None, "ended_at": None}
            runs.folders[name] = r.model_copy(update=update)
        self.left, self.left_key = dict(runs.left), runs.left_key
        self._write(runs)

    def path(self) -> Path:
        """Where the runs are kept."""
        return local_home.root() / STATE

    def _row(self, folder: str, run: FolderRun) -> str:
        """The ledger source of one row's generation: its folder and the times its producer stamped, as one window."""
        return f"{self.path()}#{curation_snapshots.window(folder, run)}"

    def load(self) -> Runs:
        """Every folder's last run; none when the file is missing. An unreadable one raises, naming the way out."""
        try:
            return Runs.model_validate_json(self.path().read_text())
        except FileNotFoundError:
            return Runs()
        except (OSError, ValueError) as exc:
            path = self.path()
            msg = (
                f"the memory curation ownership record {path} cannot be read:\n{exc}\n"
                "OwlBear can't tell whether a memory curation session it started still runs, so memory curation "
                "doesn't go on. Stop OwlBear if it still runs, and make sure no copilot process that memory curation "
                'started still runs: the PIDs under "left" are the ones it recorded, but a session that failed early '
                f"recorded none. Then move {path} aside, for example to {path}.broken, and start OwlBear again; the "
                "folders' last runs are forgotten and curate again when due."
            )
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
            runs.left, runs.left_key = dict(self.left), self.left_key
            self._write(runs)

    def lingering(self) -> bool:
        """Whether a run's processes may still run; the ledger alone decides, PIDs left after a recovery are history."""
        with self.lock:
            if self.maintenance.pending("curation"):
                return True
            if self.left:
                self.left, self.left_key = {}, ""
                runs = self.load()
                runs.left, runs.left_key = {}, ""
                self._write(runs)
            return False

    def working(self) -> list[str]:
        """What runs, waits or may still run, for an update or a stop when idle to wait for."""
        with self.lock:
            busy = [f"memory curation: {', '.join(self.queue)}"] if self.queue else []
        return busy + ([LINGERING] if self.lingering() else [])

    @contextmanager
    def fence(self, folder: str) -> Iterator[str]:
        """Hold *folder* against curation while it moves; yields why it cannot move now instead, else ''.

        It cannot while its run waits or runs, or while a run's processes may still run and none runs: those may be
        any folder's, while a running one's are its own, since a run starts only once none linger.
        """
        with self.lock:
            why = CURATING.format(folder=folder) if folder in self.queue else ""
            why = why or (LEFT_RENAME if not self.running and self.lingering() else "")
            if not why:
                self.renaming.add(folder)
        try:
            yield why
        finally:
            if not why:
                with self.lock:
                    self.renaming.discard(folder)

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
            key = f"curate:{folder}:{uuid.uuid4().hex}"  # one generation per admission, named on every row it writes
            refused = False
            try:
                refused = self._one(folder, started, key)
            except Exception as exc:  # noqa: BLE001 - one folder's failure never strands the others
                _log.exception("memory curation of %s failed (%s)", folder, key)
                why = f"{type(exc).__name__}: {exc}"
                failed = FolderRun(state="failed", started_at=started, ended_at=datetime.now(UTC), reason=why, key=key)
                self._save(folder, failed)  # its session, if one began, is the ledger's lease under this key
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

    def _one(self, folder: str, started: datetime, key: str) -> bool:
        """Run one folder's curation under admission *key*; True when an automatic request was refused its admission.

        Each row it writes once admitted names *key*: a session enters the SDK only after the ledger holds its lease
        under that key, so a restart finds the run by its key, never by when its row says it ran.
        """
        shared = self.shared()
        why = NO_SHARED if shared is None else LEFT if self.lingering() else self.fenced()
        why = why or _unset(lookup.machine(shared))  # checked again on the snapshot it starts with
        if shared is None or why:
            self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=why))
            return False
        turn = threading.Event()
        while True:
            turn.clear()  # cleared before the take, so a wake during it is never lost
            if self.slots.take(SLOT, key, 1, 1, wake=turn.set):
                break
            if why := self.fenced():  # an update or a stop came while it waited: it never starts
                self.slots.cancel(SLOT, key)
                self._save(folder, FolderRun(state="failed", started_at=started, ended_at=started, reason=why))
                return False
            turn.wait(5)
        try:  # from the grant on, the slot goes back however this ends, unless the ledger holds it
            with self.admission():  # the stop barrier: a stop when idle sees this run admitted, or it is refused here
                why = self.fenced()
                with self.lock:  # the automatic switches are read at the grant, not when the request was made
                    asked = self.asked.get(folder, "manual")
                    # a rename holds it, or moved it after it was queued: the run would curate a folder that is gone
                    why = why or (MOVED if folder in self.renaming or folder not in folders(shared.root) else "")
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
            self._save(folder, FolderRun(state="running", started_at=started, key=key))
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
        with curation_tree.forgetting(shared), self.maintenance.workspace("owlbear-curation-") as at:
            tree = curation_tree.seed(shared, at / "data", folders(shared.root))
            store = tree.root / folder / "memory"
            before = {e.id: e.revision for e in _pending(store)}  # what the curator can see when it starts
            said = message(folder)
            cfg = sdk_adapter.Session(
                kind=StepKind.REVIEW, worktree=at, session_id=f"{LABEL}-{folder}-{uuid.uuid4().hex[:8]}",
                message=said, fresh=said, resume=False, policy=Policy(at, write=False),
                observe=lambda: tools.Worktree("", ""), checks=(), submit=memory_curation_tools.SUBMIT,
                model=role.model, effort=role.effort, context=role.context, limit=roles.limit(settings, LABEL),
                subagents=roles.subagents(settings, LABEL), user=roles.user_config(settings),
                role=tools.CURATOR, job=LABEL, journal=sdk_adapter.Journal(event=self._pids), memory=store,
            )  # fmt: skip
            with curation_tree.holding(tree, folder, key):  # what an exception leaves stays out of the checkout
                with self.lock:
                    self.left_key = key  # persisted with the first PIDs this run records, so a restart knows whose
                place = spend_ledger.Where(project=folder, name=folder)  # a memory folder is its project's
                with spend_ledger.at(place):
                    done = maintained.run_owned(
                        self.maintenance, cfg, self.run, project=SLOT, slot=key, kind="curation"
                    )
                judged = self._judged(tree, folder, started, key, done)
        if pruned := curation_tree.prune(shared):
            judged = judged.model_copy(update={"reason": "; ".join(filter(None, (judged.reason, pruned)))})
        if judged.state != "done":
            return judged
        after = {e.id: e.revision for e in _pending(shared.root / folder / "memory")}
        seen = {i: r for i, r in after.items() if before.get(i) == r}  # one saved or changed meanwhile stays due
        skipped = {
            j.entry_id: after[j.entry_id] for j in judged.entries if j.action == "skipped" and j.entry_id in after
        }
        return judged.model_copy(update={"skipped": skipped, "seen": seen})

    def _judged(self, tree: curation_tree.Tree, folder: str, started: datetime, key: str, done: Run) -> FolderRun:
        """The run's row: a refused run's edits held, an accepted one's in the checkout and published."""
        t = done.termination
        with self.lock:
            watched = dict.fromkeys((*t.survivors, *t.unknown)) | done.pids if t is not None and not t.confirmed else {}
            self.left, self.left_key = watched, key if watched else ""
            runs = self.load()
            runs.left, runs.left_key = dict(self.left), self.left_key
            self._write(runs)
        unknown = not (t and t.confirmed)
        ended = datetime.now(UTC)
        report = done.payload if isinstance(done.payload, memory_curation_tools.MemoryCurationResult) else None
        if done.ending != "result" or report is None or unknown or done.usage_unread:
            why = " ".join((done.detail or "no report was submitted").split())
            if done.usage_unread and done.ending == "result" and report is not None:  # TD-94: its model is unproven
                why = " ".join(f"the model is unknown: {done.usage_unread}".split())
            why = f"{UNKNOWN}; {why}" if unknown else why
            reason = f"ended {done.ending}: {why}; {tree.hold(folder, key)}"
            _log.error("memory curation of %s failed (%s): %s", folder, key, reason)
            return FolderRun(
                state="failed", started_at=started, ended_at=ended, reason=reason, key=key if unknown else ""
            )
        refusal, notice = tree.accept(folder, key)
        if refusal:  # a confirmed end: "ended result: …" tells a restart its termination was judged
            return FolderRun(state="failed", started_at=started, ended_at=ended, reason=f"ended result: {refusal}")
        return FolderRun(
            state="done", started_at=started, ended_at=ended, summary=report.summary, reason=notice,
            entries=report.entries,
        )  # fmt: skip


def _pending(store: Path) -> list[Any]:
    """The folder's pending entries; none when it has no memory yet."""
    if not store.is_dir():
        return []
    return [e for e in MemoryEngine(store).get_entries() if e.state == MemoryState.PENDING]


def legacy_uncertain(run: FolderRun) -> bool:
    """A dated failed or waiting row no ledger key accounts for, whose session may have entered the SDK unproven.

    A waiting row, and the interrupted row a restart makes of it, copies an earlier row with its times, reason and
    report, so it is judged by what it still shows. Only a known shape proves no session or its proven end: a refusal
    main writes before any session; a report, which only a finished run writes and only one whose termination was
    confirmed or whose PIDs are the snapshot's; or ``ended …`` without UNKNOWN, an SDK return with its termination
    judged. A generic failure, which may be raised inside the SDK before any PID is recorded, an interrupted row,
    whose end time proves nothing, and every other reason or a state no producer writes count as uncertain.
    """
    if run.key or run.started_at is None or curation_snapshots.refused(run):
        return False
    if run.state not in curation_snapshots.STATES:
        return True
    if run.state not in {"failed", "waiting"} or run.summary:
        return False  # never and done, a finished run's copy, and running, which the caller takes on its own
    return not run.reason.startswith("ended ") or UNKNOWN in run.reason


def _unset(settings: Settings) -> str:
    """Why a run cannot start for unset settings: the curator's role, its threshold or a user-config switch; else ''."""
    try:
        agent = settings.agent(roles.SESSIONS[LABEL])
        settings.need("curator_threshold", *roles.USER_CONFIG)
    except SettingsUnset as exc:
        return str(exc)
    if agent.subagents is None:  # set per role: a run never guesses whether its subagents may start
        return f"agents.{roles.SESSIONS[LABEL]}.subagents is unset"
    return ""
