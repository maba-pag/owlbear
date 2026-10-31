"""The machine host's state (TD-242): its record, the projects it serves and whether Delivery is paused.

A login start, a start after a crash and a start asked for paused are paused; any other start runs, and a restart
keeps the state it had (TD-350). The owner's Resume in the UI unpauses it and is recorded. The owner pauses again with
Pause, or with Pause and stop when idle (TD-288), which stops OwlBear once nothing runs.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_flow.status import RESUME, status
from owlbear_delivery_next.local_system import data_repo, maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import cases_job, chats
from owlbear_delivery_next.machine_host.cases_job import CasesJob
from owlbear_delivery_next.machine_host.curation import Curation
from owlbear_delivery_next.machine_host.project import Project
from owlbear_delivery_next.machine_host.retro_job import DRAIN, RetroJob
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.project_host.host import RunnerRecord
from owlbear_delivery_next.state_store import machine_settings, project_home, registry, settings_carry
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.project_host.host import Host, HostRecord

RETRY = 60.0  # seconds between loads of a project that failed to load
IDLE = 2.0  # seconds between looks whether a stop when idle may stop OwlBear
CURATE_EVERY = 60.0  # seconds between looks whether idle time may curate memory (item 5 slice 4)
UNPROVEN_PACK = "an Impeccable session not confirmed ended; the Maintenance page shows it"


class MachineError(Exception):
    """A request about a project this machine refuses; ``status`` is the HTTP answer."""

    def __init__(self, status: int, text: str) -> None:
        """Keep the answer's status and words."""
        super().__init__(text)
        self.status, self.text = status, text


def recorded(repo: Path) -> dict[str, int]:
    """The sessions a project's runners hold, read from their records while no host serves it (TD-336).

    A record goes only once a host confirms its runner and processes gone, so each one counts; a project whose
    records cannot be read counts none.
    """
    held = {}
    with contextlib.suppress(OSError, subprocess.CalledProcessError, StoreError):
        found = project_home.current(repo)
        for path in (found / "changes").glob("*/runner.json") if found else []:
            with contextlib.suppress(OSError, ValueError):
                if sessions := RunnerRecord.model_validate_json(path.read_text()).sessions:
                    held[path.parent.name] = sessions
    return held


class Machine:
    """Every registered project, loaded once; requests about them are serialized by ``lock``."""

    def __init__(self, record: HostRecord, *, paused: bool = True) -> None:
        """Start paused or running, with no project loaded yet."""
        self.record, self.paused = record, paused
        self.ending = False  # the owner's stop when idle; held in memory, so a restart never stops again
        self.updating = ""  # the update's fence (self-update §5.3): why nothing starts now
        self.handover: tuple[Any, Any] | None = None  # the standby and what it takes over, once the alias names it
        self.updated = ""  # the version this host took over as, said once on the pages (TD-299)
        self.projects: dict[str, Project] = {}
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.on_stop: Callable[[], None] = lambda: None
        self.total = 0  # until the machine's total is read; unset, no session starts (2026-10-23)
        self.slots = Slots(self._sessions, closed=True)  # opened once every project's live steps are counted
        self.maintenance = maintenance.Maintenance(self.slots)
        from owlbear_delivery_next.machine_host.auto_update import Auto  # noqa: PLC0415 - it names this class
        from owlbear_delivery_next.machine_host.impeccable import Impeccable  # noqa: PLC0415 - it names this class
        from owlbear_delivery_next.machine_host.update import Updater  # noqa: PLC0415 - it names this class
        from owlbear_delivery_next.machine_host.update_checks import Checks  # noqa: PLC0415 - it names this class

        self.updater = Updater(self)
        self.auto = Auto(self)
        self.impeccable = Impeccable(self)
        self.checks = Checks(self)  # OwlBear's, PDS's and Impeccable's update checks (D-01M63CCVRK8ZKFENY9F4A2K11A)
        self.curation = Curation(
            self.slots,
            fenced=self._curation_fence,
            paused=lambda: self.paused,
            admission=lambda: self.lock,  # the stop barrier pause_stop and idle_stop already use
            ownership=self.maintenance,
        )
        self.cases = CasesJob(  # the Spotter cases' replays, checks and publication, on a slot of their own
            self.slots,
            fenced=self._curation_fence,
            paused=lambda: self.paused,
            admission=lambda: self.lock,
            say=self.say,
            ownership=self.maintenance,
        )
        self.chats = chats.Follower(  # started by ``serve``; each look admitted and leased like the cases job's runs
            paused=lambda: self.paused,
            say=self.say,
            ownership=self.maintenance,
            fenced=self._curation_fence,
            admission=lambda: self.lock,
        )
        self.retro = RetroJob.attach(self, self._curation_fence)  # Retro's runs, each paid call admitted and leased

    def _curation_fence(self) -> str:
        """Why no memory curation starts now: an update's fence, a stop, or a stop when idle, which starts nothing."""
        if self.updating:
            return self.updating
        if self.stopping.is_set():
            return "stopping"
        return "OwlBear stops once nothing runs: no memory curation starts" if self.ending else ""

    def _sessions(self) -> int:
        """The machine's sessions at once, read at each grant; the last one read while machine.json is unreadable."""
        with contextlib.suppress(registry.RegistryError):
            self.total = machine_settings.current().sessions or 0
        return self.total

    def carry(self) -> None:
        """Carry today's built-in settings into Global once, then move this machine's own settings and clear them here.

        The first machine's move fills Global's machine settings; so every machine follows Global (the owner,
        2026-10-23). Both run on a current checkout. Until they are done, why is kept for the Settings page and the
        next start tries again; this machine keeps its own values meanwhile.
        """
        try:
            why = _switched(self.say)
        except Exception as exc:  # noqa: BLE001 - the projects load either way; their steps say what is unset
            why = f"the settings carry failed: {type(exc).__name__}: {exc}"
        if why:
            self._pending(why)
        else:
            _pending("")

    def _pending(self, why: str) -> None:
        """Keep why the carry or the move is not done, and say it; tried again at the next start."""
        _pending(why)
        self.say(f"settings: {why}; tried again at the next start")

    def say(self, text: str) -> None:
        """Write one line to the machine host's log."""
        sys.stdout.write(f"{datetime.now(UTC):%H:%M:%SZ} {text}\n")
        sys.stdout.flush()

    def _load(self, entry: registry.Project) -> Project:
        if self.stopping.is_set():
            raise MachineError(503, "OwlBear is stopping")
        p = self.projects[entry.id] = Project(entry)

        def bind(h: Host) -> None:  # before its scheduler's first pass
            h.peers = lambda: self.sharing(p)
            h.machine = lambda: [o.store for o in list(self.projects.values()) if o.store]  # a failed host's too
            h.draining = lambda: self.ending
            h.closed = lambda: self.stopping.is_set() or not p.gate.open
            h.updating = lambda: self.updating
            h.slots = self.slots
            h.maintenance = self.maintenance
            h.merged = lambda: self.curation.nudge([h.store.name], "merge")
            h.curating = self.curation.fence

        try:
            p.load(self.record, lambda: self.paused or self.stopping.is_set(), bind)
        except Exception as exc:  # noqa: BLE001 - one project's failure never stops the machine
            p.state, p.reason = "failed", f"it could not load: {type(exc).__name__}: {exc}"
        if p.state == "failed":
            self.slots.restore(entry.id, recorded(Path(entry.path)))  # its runners may live on without a host
            # read from its folder, never through a Job: the store may belong to another host that still runs (TD-242)
            session_slots.unloaded(self.maintenance, entry.id, Path(entry.path))
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
        """Load every registered project; one that fails is listed with its reason.

        First, once, today's built-in settings go into the shared repository's Global layer (2026-10-23).
        """
        self.carry()
        with self.lock:
            for entry in registry.load().projects:
                self._load(entry)
        self.slots.open()  # a project that failed to load counts its live steps once it loads

    def retry(self) -> None:
        """Load again each project that failed or was replaced; not while an update's fence holds."""
        with self.lock:
            for p in [p for p in self.projects.values() if p.state in {"failed", "replaced"}]:
                if not (self.stopping.is_set() or self.updating):
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
            self.fenced()
            try:
                entry = registry.register(path)
            except registry.RegistryError as exc:
                raise MachineError(409, str(exc)) from exc
            return self._load(entry)

    def remove(self, pid: str) -> None:
        """Stop and forget a project; refused, naming them, while its steps or admitted work still run."""
        with self.lock:
            self.fenced()
            p = self.get(pid)
            if p.state == "failed" and (live := recorded(Path(p.entry.path))):  # no host confirms them gone (TD-336)
                msg = f"{p.name} has steps of {', '.join(live)} not confirmed ended; it must load again to check them"
                raise MachineError(409, msg)
            if left := p.stop(refuse=True):
                raise MachineError(409, f"{p.name} still runs {', '.join(left)}; remove it once they end")
            registry.remove(pid)
            del self.projects[pid]
            self.slots.restore(pid, {})
            self.say(f"{p.name}: removed")

    def adopt(self, pid: str) -> Project:
        """Let the clone now at a replaced project's path take its place."""
        with self.lock:
            self.fenced()
            p = self.get(pid)
            if p.state != "replaced":
                raise MachineError(409, f"{p.name} is {p.state}, not replaced")
            try:
                entry = registry.adopt(pid)
            except registry.RegistryError as exc:
                raise MachineError(409, str(exc)) from exc
            del self.projects[pid]
            p = self._load(entry)
            self.slots.leave(pid)  # only once the clone now at its path counts its own runners: never a gap
            self.slots.restore(pid, {})
            return p

    def resume(self) -> None:
        """The owner's Resume: work starts again in every project; a stop when idle is cancelled."""
        registry.resumed(datetime.now(UTC))
        with self.lock:
            self.paused = self.ending = False
        self.say("resumed by you")
        self._wake()

    def pause(self) -> None:
        """The owner's Pause: no automatic step starts until Resume; running steps finish (TD-282, TD-287)."""
        self.paused = True
        self.say("paused by you")

    def pause_stop(self) -> None:
        """Pause and stop when idle (TD-288): nothing starts, check environments go, then OwlBear stops."""
        with self.lock:  # idle_stop waits for the barrier too, so nothing admitted before it goes uncounted
            self.paused = self.ending = True
            for p in list(self.projects.values()):
                if p.host:
                    with p.host.launching:  # a launch admitted before the intent is counted from now on
                        pass
        self.say("paused by you: OwlBear stops once nothing runs")
        self._wake()

    def _wake(self) -> None:
        for p in list(self.projects.values()):
            if p.host:
                p.host.wake.set()

    def _unproven_packs(self) -> list[str]:
        """Each project whose pack session the ledger holds, loaded or not: its job is idle once the SDK returns."""
        names = {pid: p.name for pid, p in list(self.projects.items())}
        return [f"{names.get(key, key)}: {UNPROVEN_PACK}" for key in self.maintenance.holding("pack")]

    def left(self) -> list[str]:
        """What a stop when idle still waits for: each project's running steps, environments and admitted work."""
        return (
            [f"{p.name}: {w}" for p in list(self.projects.values()) for w in p.working(stopping=True)]
            + self.curation.working()
            + self.cases.working()
            + self.chats.working()
            + self.retro.working()
            + self._unproven_packs()
        )

    def fence(self, text: str) -> list[str]:
        """An update's fence (self-update §5.3): nothing starts from now on; what still runs, which lifts it."""
        with self.lock:
            self.updating = text
            for p in list(self.projects.values()):
                if p.host:
                    with p.host.launching:  # a launch admitted before the fence is counted from now on
                        pass
        return self.busy()

    def busy(self) -> list[str]:
        """What an update waits for: each project's running steps, environments and admitted work."""
        projects = list(self.projects.values())
        return (
            [f"{p.name}: {w}" for p in projects for w in p.working(stopping=True, requests=False)]
            + self.curation.working()
            + self.cases.working()
            + self.chats.working()
            + self.retro.working()
            + self._unproven_packs()
        )

    def fenced(self) -> None:
        """Refuse a project change while an update's fence holds.

        Raises:
            MachineError: The fence holds.
        """
        if self.updating:
            raise MachineError(503, self.updating)

    def unfence(self) -> None:
        """Lift the fence: the update waits, and work starts again."""
        self.updating = ""
        self._wake()

    def idle_stop(self) -> bool:
        """Stop OwlBear when a stop when idle is asked for and nothing runs; whether it stopped."""
        with self.lock:  # a Resume in between cancels it
            if not self.ending or self.stopping.is_set() or self.left():
                return False
            self.say("stopping: nothing runs")
            self.on_stop()
            return True

    def curation_loop(self) -> None:
        """Thread: once OwlBear is idle, curate each memory folder holding pending entries no run has seen."""
        from owlbear_delivery_next.machine_host.auto_update import IDLE_FOR  # noqa: PLC0415 - it names this class

        while not self.stopping.wait(CURATE_EVERY):
            try:
                idle = self.auto.mono() - self.auto.last_use >= IDLE_FOR
                if idle and not (self.updating or self.ending or self.busy()):
                    self.curation.nudge(None, "idle")
            except Exception as exc:  # noqa: BLE001 - the loop outlives one failed look
                self.say(f"looking whether to curate memory failed: {type(exc).__name__}: {exc}")

    def idle_loop(self) -> None:
        """Thread: look every ``IDLE`` seconds whether a stop when idle may stop OwlBear."""
        while not self.stopping.wait(IDLE):
            try:
                self.idle_stop()
            except Exception as exc:  # noqa: BLE001 - the loop outlives one failed look
                self.say(f"looking whether OwlBear may stop failed: {type(exc).__name__}: {exc}")

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
        self.cases.stop()
        self.retro.stop()
        self.chats.close()  # no chat look is admitted from now on
        for p in list(self.projects.values()):
            p.gate.close(0)

    def stop_all(self) -> None:
        """Close every gate, then stop each project; live runners finish on their own (TD-282)."""
        self.closing()
        with self.lock:  # a load in flight finishes first, so its project is stopped too
            for p in self.projects.values():
                if p.state != "stopped":
                    p.stop()
        if not self.cases.drain():  # its running session cancelled, so its result and spend are kept before the exit
            self.say(f"the Spotter cases job did not end within {cases_job.DRAIN:.0f} s")
        if not self.retro.drain():
            self.say(f"Retro did not end within {DRAIN:.0f} s")
        if not self.chats.join(chats.CLOSE):  # outside the lock; the follower keeps its own lock until it ends
            self.say("the chats follower is still ending; no other follower starts until it has")
        self.checks.drain()  # says itself when a check did not end
        self.say("stopped: every project closed")


def _moving() -> registry.Settings:
    """The values this machine's move takes: chosen at its first try, kept until it is done."""
    with registry.locked():
        machine = registry.load()
        if machine.settings_moving is None:
            machine.settings_moving = machine.settings
            registry.save(machine)
        return machine.settings_moving


def _switched(say: Callable[[str], None]) -> str:
    """The carry, this machine's move and the credit limits' upgrade, each once and silently; why not, else ''.

    D-01M5MZKEPWNASF6X3CNF4FEWZH for the carry and the move; D-01M5XCD49YHHR1NQKKY8TQD0C3 for the limits.
    """
    shared, state = data_repo.locate(), registry.load()
    if shared is None:
        return ""  # without Global this machine keeps its own values
    why = settings_carry.sync(shared, state.global_written)  # every start: Global as the other machines left it
    settled = state.settings_moved and not state.global_written  # no write of this machine's waits to be reconciled
    if settled and not settings_carry.due(shared) and not settings_carry.limits_due(shared):
        if why:
            say(f"settings: the shared repository could not be brought current: {why}")
        return ""
    if why:
        return f"the shared repository could not be brought current: {why}"
    if settings_carry.due(shared) and (notice := settings_carry.carry(shared, _written)):
        return f"carrying the built-in values into Global: {notice}"
    if not state.settings_moved and (notice := _move(shared, say)):
        return notice
    return _limits(shared)


def _limits(shared: data_repo.DataRepo) -> str:
    """Save and publish Global in the credit limits' format once (D-01M5XCD49YHHR1NQKKY8TQD0C3); why not, else ''.

    A git probe that fails raises, here and in ``limits_due``: the start keeps its pending reason and this machine's
    last write, so the next start knows that write as its own and tries again.
    """
    notice = settings_carry.limits(shared, registry.load().global_written, _written)
    return f"writing the credit limits into Global: {notice}" if notice else ""


def _move(shared: data_repo.DataRepo, say: Callable[[str], None]) -> str:
    """Move this machine's settings into Global, then clear those still as they were; why not, else ''."""
    local = _moving()
    if notice := settings_carry.move(shared, local, _written):
        return f"moving this machine's settings into Global: {notice}"
    with registry.locked():
        machine = registry.load()
        since = {k: v for k, v in machine.settings.model_dump().items() if v != getattr(local, k)}
        machine.settings = registry.Settings.model_validate(since)  # what the owner saved since stays
        machine.settings_moved, machine.settings_moving = True, None
        registry.save(machine)
    say("settings: this machine's settings moved into Global; it follows Global's from now on")
    return ""


def _pending(why: str) -> None:
    """Keep why the carry or the move is not done for the Settings page; empty once both are."""
    with registry.locked():
        machine = registry.load()
        if machine.settings_pending != why or (not why and machine.global_written):
            machine.settings_pending, machine.global_written = why, machine.global_written if why else []
            registry.save(machine)


def _written(digest: str) -> None:
    """Keep the digest of what the carry or the move wrote to Global, so a later start knows that write as its own."""
    with registry.locked():
        machine = registry.load()
        machine.global_written = [digest]  # the last write: what an unsaved Global may hold as this machine's own
        registry.save(machine)
