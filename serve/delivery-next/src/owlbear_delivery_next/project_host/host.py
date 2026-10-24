"""Delivery host: one per clone; scheduler, runner launcher, termination scan and check environments (D4 §3.2).

The process that runs it, with its HTTP server, starts in ``commands/serve`` (TD-171).
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import psutil
from pydantic import BaseModel, ValidationError

from owlbear_delivery_next.change_contracts import failures
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Record, StepKind, Waiting
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import delivery_target, loop
from owlbear_delivery_next.change_flow.status import Activity, passes
from owlbear_delivery_next.local_system import codebase, data_repo, processes
from owlbear_delivery_next.local_system.process_probe import ProcessTableWorktreeProbe, WorktreeProcessScanError
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.project_host import environment, session_slots
from owlbear_delivery_next.project_host.runner_end import Found, disappeared, gone
from owlbear_delivery_next.project_host.runner_end import block as _block
from owlbear_delivery_next.project_host.runner_end import unverified as _unverified
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.store import LockHeldError, Store, StoreError
from owlbear_delivery_next.workflow_steps import before, check, disposable, engine, prepare, pullback, queue

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change, Environment
    from owlbear_delivery_next.change_flow.loop import PrState, Seen
    from owlbear_delivery_next.state_store.store import Lock

TICK = 30.0
PR_POLL = 20.0
FAST = 2.0  # while a runner this host did not start may still run
SLEEP_JUMP = 60.0
BURST = (5, 60.0)  # at most five runner launches per Change in this many seconds
PROBE = timedelta(seconds=10)  # between network probes while a Change waits on the network
PROBE_TIMEOUT = 3.0
RESTART = "Delivery's code changed since the host started; restart the host"
ENDING = "OwlBear stops once the running steps end; press Resume to cancel"


class HostRecord(Record):
    """``host.json``: where the status view listens, the token its writes need and the code it loaded."""

    url: str
    token: str
    pid: int
    started_at: datetime
    code: str
    ready: list[str] | None = None  # failed readiness facts with their fix; None while the check runs
    project: str = ""  # the project's id on the machine host, whose API it is under (TD-242)


class RunnerRecord(Record):
    """``runner.json``: the launched runner, kept until its termination is confirmed."""

    pid: int
    created: float | None
    started_at: datetime
    sessions: int = 0  # the agent sessions it was granted at once (TD-336), held until it is confirmed gone


def running(store: Store) -> HostRecord | None:
    """Return the live host's record; None when no process holds the host lock, so Delivery is not running."""
    return running_at(store.root)


def running_at[R: BaseModel](root: Path, model: type[R] = HostRecord) -> R | None:
    """The record of the host whose ``host.lock`` and ``host.json`` are in *root* as *model*, if one holds the lock."""
    try:
        fd = os.open(root / "host.lock", os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
        with contextlib.suppress(OSError, ValidationError):
            return model.model_validate_json((root / "host.json").read_text())
        return model.model_validate(
            {"url": "(starting)", "token": "", "pid": 0, "started_at": datetime.now(UTC), "code": ""}
        )
    finally:
        os.close(fd)
    return None


def stale(record: HostRecord | None) -> bool:
    """Whether the running host loaded other code than this process, so it may not read what this one writes."""
    return record is not None and record.code != codebase.CURRENT


def offline(c: Change, now: datetime) -> bool:
    """Whether *c* waits out a network failure whose pause has not ended; the network's return ends it early."""
    o = c.outcome
    if o is None or (o.exit, o.waiting) != (Exit.PENDING, Waiting.NETWORK):
        return False
    return failures.kind_of(o.cause) == ErrorKind.NETWORK and o.wake_at is not None and o.wake_at > now


def activity(store: Store, slug: str, host: HostRecord | None, *, paused: bool = False, waiting: str = "") -> Activity:
    """Observed liveness for the status line: the Change lock's holder, unless it is the host itself."""
    holder = store.holder(slug)
    runner = holder is not None and (host is None or holder.pid != host.pid)
    last = next((e["at"] for e in reversed(store.events(slug)) if "at" in e), None)
    at = datetime.fromisoformat(last) if last else None
    pid = holder.pid if runner and holder else None
    up = host is not None
    return Activity(up, runner, pid, at, paused=paused, waiting_slot="" if runner else waiting)


def _scan(path: Path, since: datetime) -> Found:
    return dict(ProcessTableWorktreeProbe().active_processes((path,), started_after=since))


class Host:
    """The scheduler: observes every Change, folds inboxes and starts at most one runner per Change.

    While ``paused`` says so (a login, post-crash or paused start until Resume, TD-350) it applies the owner's input
    (TD-283) and records ended runners, but reads no PR, runs no Pull and launches no runner or environment;
    the fold's queue barrier still takes a queued PR out when a Change leaves its merge step (TD-284).
    """

    def __init__(  # noqa: PLR0913 - process seams the tests replace
        self,
        store: Store,
        repo: Path,
        *,
        spawn: Callable[[str], RunnerRecord] | None = None,
        scan: Callable[[Path, datetime], Found] = _scan,
        group: Callable[[int], Found] = check.members,
        alive: Callable[[int, float | None], bool | None] = processes.alive,
        code: Callable[[], str] = codebase.identity,
        reach: Callable[[str], str | None] = lambda name: readiness.reach(name, timeout=PROBE_TIMEOUT),
        paused: Callable[[], bool] = lambda: False,
    ) -> None:
        self.store, self.repo, self.scan, self.group, self.alive = store, repo, scan, group, alive
        self.spawn, self.code, self.reach, self.paused = spawn or self._spawn, code, reach, paused
        self.peers: Callable[[], list[Host]] = list  # the machine's other clones sharing this folder
        self.machine: Callable[[], list[Store]] = lambda: [self.store]  # every project store on this machine (TD-336)
        self.draining: Callable[[], bool] = lambda: False  # the owner's stop when idle: environments go too
        self.closed: Callable[[], bool] = lambda: False  # the machine or this project stops: nothing starts at all
        self.updating: Callable[[], str] = lambda: ""  # the machine's update fence: why nothing starts now
        self.merged: Callable[[], None] = lambda: None  # a Change's pull request merged: the machine may curate memory
        self.passing: set[str] = set()  # Changes whose next step runs while paused (TD-287, TD-303)
        self.slots, self.wants, self.grants = Slots(lambda: session_slots.ALL), dict[str, int](), dict[str, int]()
        self.waiting, self.asked = set[str](), set[str]()  # Changes waiting for a session slot (TD-336)
        self.wake, self.stopped, self.launching = threading.Event(), threading.Event(), threading.Lock()
        self.pr_states: dict[str, PrState] = {}
        self.pr_seen: dict[str, tuple[float, Seen]] = {}
        self.launches: dict[str, list[float]] = {}
        self.reported: dict[str, tuple[str, int | None]] = {}
        self.refused: str | None = None  # why runners do not start: the code differs or cannot be read
        self.offline: set[str] = set()  # Changes last seen waiting on the network
        self.back: dict[str, datetime] = {}  # those to wake, with when the probe saw the network return
        self.down, self.probe_at, self.clock = False, 0.0, time.monotonic
        pid, started = os.getpid(), datetime.now(UTC)
        self.record = HostRecord(url="", token="", pid=pid, started_at=started, code=codebase.CURRENT)

    def say(self, text: str) -> None:
        """Write one line to the host's log; under the machine host it names the project first."""
        who = f"{self.store.name or self.repo.name}: " if self.record.project else ""
        sys.stdout.write(f"{datetime.now(UTC):%H:%M:%SZ} {who}{text}\n")
        sys.stdout.flush()

    def _path(self, slug: str) -> Path:
        return self.store.root / "changes" / slug / "runner.json"

    def runner(self, slug: str) -> RunnerRecord | None:
        """Return the recorded runner of *slug*, alive or awaiting its termination check."""
        with contextlib.suppress(OSError, ValidationError):
            return RunnerRecord.model_validate_json(self._path(slug).read_text())
        return None

    def activity(self, slug: str) -> Activity:
        """Liveness of one Change as this host sees it."""
        return activity(self.store, slug, self.record, paused=self.paused(), waiting=session_slots.waiting(self, slug))

    def observe_pr(self, slug: str) -> Seen:
        """The PR's terminal state and consent-wait news, observed before a waiting Change is skipped; once per poll."""
        if slug in self.pr_states:
            return self.pr_states[slug], False
        seen = self.pr_seen.get(slug)
        if seen is None or time.monotonic() - seen[0] > PR_POLL:
            seen = self.pr_seen[slug] = (time.monotonic(), engine.observe(self.store, self.repo, slug))
        return seen[1]

    def tick(self, now: datetime | None = None) -> list[str]:
        """One observation pass over every Change; return those a runner was launched for."""
        launched = []
        if self.store.shared:  # a rename on another machine arrives with a pull (TD-98)
            with self.launching:
                self.store.name = data_repo.folder(self.store.shared, self.repo)
        if not self.paused():
            self._probe(now or datetime.now(UTC))
        slugs = self.store.slugs()
        self.offline &= set(slugs)
        self.back = {s: t for s, t in self.back.items() if s in slugs}
        try:
            for slug in slugs:
                try:
                    if self._one(slug, now or datetime.now(UTC)) and self._launch(slug):
                        launched.append(slug)
                except LockHeldError:
                    continue
                except StoreError as exc:
                    self._unloadable(slug, str(exc))
        finally:  # who waits for a slot after this pass, even one that failed: no wait outlives its asking
            self.waiting, self.asked = self.asked, set()
            self.slots.keep(session_slots.project(self), self.waiting)
        return launched

    def interval(self) -> float:
        """Seconds until the next pass: soon while a runner runs, by the next probe while a Change waits offline."""
        wait = FAST if any(self.runner(s) for s in self.store.slugs()) else TICK
        if not self.offline or self.paused():  # no probe runs while paused, so its deadline never comes
            return wait
        return max(0.0, min(wait, self.probe_at - self.clock()))

    def _probe(self, now: datetime) -> None:
        """Probe the network while a Change waits on it, every ``PROBE`` from the last probe's start."""
        if not self.offline or self.clock() < self.probe_at:
            return
        self.probe_at = self.clock() + PROBE.total_seconds()
        try:
            name = profile.value(self.store.read_profile() or Profile(), profile.HOST, "github.com")
        except StoreError:
            name = "github.com"
        up = self.reach(name) is None
        if up and self.down:  # only a return wakes them: a probe that never failed says nothing about their failure
            self.back |= dict.fromkeys(self.offline, now)
            self.say(f"network: https://{name} answers again; waking {', '.join(sorted(self.offline))}")
        self.down = not up

    def _woken(self, c: Change, now: datetime) -> Change:
        """End a network wait that began before the probe saw the network return; otherwise note it for the probe.

        A wake stays pending until the Change is seen no longer waiting, so a locked or unwritten Change keeps it.
        """
        o, seen = c.outcome, self.back.get(c.slug)
        if o is None or not offline(c, now):
            self.offline.discard(c.slug)
            self.back.pop(c.slug, None)
        elif seen and o.at <= seen:
            c.outcome = o.model_copy(update={"wake_at": now})
        else:
            self.back.pop(c.slug, None)
            self.offline.add(c.slug)
        return c

    def _unloadable(self, slug: str, text: str) -> None:
        """Report an unloadable Change once, and again only after its record changes; not on every pass."""
        try:
            stamp = self.store.rev(slug)
        except StoreError:
            stamp = None
        if self.reported.get(slug) != (text, stamp):
            self.reported[slug] = (text, stamp)
            self.say(f"{slug}: {text}")

    def _one(self, slug: str, now: datetime) -> bool:
        self.passing.discard(slug)  # a permission holds only for the launch of this same pass
        rec = self.runner(slug)
        if rec and self.alive(rec.pid, rec.created) is not False:
            return False  # A live runner finishes on its own; the host never kills it.
        paused = self.paused()
        with self.store.lock(slug) as lock:
            c = self._folded(lock, slug, rec, now, paused=paused)
            if paused:
                if not (self.owner_runs() and passes(c, now)):
                    return self._ended(lock, c, rec, now)
                self.passing.add(slug)  # its launch passes the pause in this same pass
            act = self.env_action(c)
            if c.env and act in {"dispose", "settle"}:
                if (left := self.clear(c, c.env)) is None or left:
                    return self._blocked(lock, c, left, now)
                c = check.settle(c, now, check.declared(c)) if act == "settle" else c
                c.env = None
                self.say(f"{slug}: check environment disposed")
            step = loop.next_step(c, now)
            if rec or c.blocked or _unverified(c) or (step and not c.env):
                if not self._gone(lock, c, rec, now):
                    return False
                step = loop.next_step(c, now)
            if c.env:
                c = environment.launch(self, lock, c, now)
                runs = check.capturing(c) or before.due(c) or prepare.due(self.store, c)
                step = loop.next_step(c, now) if runs else None
            self.store.write(lock, c)
            self.wants[slug] = session_slots.wanted(c, step)
            return step is not None or bool(not c.stop and prepare.left(self.store, c))  # a gone check's end

    def _folded(self, lock: Lock, slug: str, rec: RunnerRecord | None, now: datetime, *, paused: bool) -> Change:
        """Fold the inbox with the PR's state, run an asked Pull, charge a runner gone.

        While paused only a PR's end is taken (its cleanup runs then, TD-303) and the owner's Pull runs (TD-287).
        """
        prior = self.store.read(slug)  # before the inbox, which may clear a committed outcome
        state, moved = self.observe_pr(slug)
        if paused:
            state, moved = (state if state in {"merged", "closed", "misdelivered"} else None), False
        c, _ = self.store.fold(lock, slug, now, state, moved=moved, leave=queue.barrier(self.store, self.repo))
        if state == "merged" and prior.step.kind != StepKind.CLEANUP and c.step.kind == StepKind.CLEANUP:
            self.merged()  # its project's memory may hold what the Change's agents saved (item 5 slice 4)
        if moved:
            self.pr_seen.pop(slug, None)  # not applied again to the merge step's next offer
        c = self._woken(self._pull(lock, c, now) if not paused or self.owner_runs() else c, now)
        if rec and disappeared(prior, rec, now) and c.step == prior.step:
            c = delivery_target.accounted(c, gone(c.step.kind), now)
            self.say(f"{slug}: runner {rec.pid} ended without recording an exit")
        return c

    def _ended(self, lock: Lock, c: Change, rec: RunnerRecord | None, now: datetime) -> bool:
        """While paused: confirm an ended runner and its processes gone; nothing starts.

        Before a stop when idle the check environment goes too; it launches again after the next start.
        """
        if (rec or c.blocked or _unverified(c)) and not self._gone(lock, c, rec, now):
            return False
        if self.draining() and c.env and (c.env.pids or c.env.pgid or c.env.launched_at):
            if (left := self.clear(c, c.env)) is None or left:
                return self._blocked(lock, c, left, now)
            c.env = c.env.model_copy(update={"pids": {}, "pgid": None, "ready_at": None, "launched_at": None})
            self.say(f"{c.slug}: check environment stopped before OwlBear stops")
        self.store.write(lock, c)
        return False

    def _gone(self, lock: Lock, c: Change, rec: RunnerRecord | None, now: datetime) -> bool:
        """Whether nothing of the last step remains; then its runner is forgotten and its liveness stop cleared."""
        if (found := self._survivors(c, rec)) is None or found:
            return self._blocked(lock, c, found, now)
        if _unverified(c):
            c.stop = c.outcome = None
        c.blocked = None
        self._path(c.slug).unlink(missing_ok=True)
        session_slots.release(self, c.slug)  # its sessions are confirmed gone with it (TD-336)
        disposable.settled(self.store.root / "changes" / c.slug)
        return True

    def _pull(self, lock: Lock, c: Change, now: datetime) -> Change:
        """Run pull-back again when the owner asked to Pull, and record its result."""
        if not c.pull_requested:
            return c
        c.pullback, c.pull_requested = pullback.run(self.repo, c.names.target, now), None
        self.store.log(lock, c.slug, {"event": "pullback", "at": now.isoformat(), **c.pullback.model_dump(mode="json")})
        self.say(f"{c.slug}: pull-back {c.pullback.state} {c.pullback.reason}".rstrip())
        return c

    def mark(self, c: Change, found: Found | None, now: datetime) -> None:
        """Record why no writer starts: processes of the last step remain, or could not be looked for."""
        stop = _block(found, now)
        if not (c.blocked and c.blocked.reason == stop.reason):
            c.blocked = stop
            self.say(f"{c.slug}: no writer starts: {stop.reason}")

    def _blocked(self, lock: Lock, c: Change, found: Found | None, now: datetime) -> bool:
        self.mark(c, found, now)
        self.store.write(lock, c)
        return False

    def _survivors(self, c: Change, rec: RunnerRecord | None) -> Found | None:
        """Processes of the last step still present: recorded PIDs, the runner's former group, the worktrees.

        The read-only worktree is scanned while its last session's processes are not confirmed gone.
        """
        since = rec.started_at if rec else c.step.started_at
        pids: dict[int, float | None] = {rec.pid: rec.created} if rec else {}
        for e in self.store.events(c.slug) if since else []:
            if e.get("event") == "pids" and datetime.fromisoformat(e["at"]) >= since - timedelta(seconds=1):
                pids |= {int(p): t for p, t in e["pids"].items()}
        found: Found = {p: "" for p, t in pids.items() if self.alive(p, t) is not False}
        found |= self.group(rec.pid) if rec else {}
        try:
            ro = disposable.live(self.store.root / "changes" / c.slug)
            for root in (Path(c.names.worktree) if c.names.worktree else None, ro):
                if root and root.exists():  # Unreadable processes count only if they may have started with the step.
                    found |= self.scan(root, since or datetime.now(UTC))
        except OSError, WorktreeProcessScanError:
            return None
        return {p: v for p, v in found.items() if not (c.env and check.owned(c.env, p))}

    def owner_runs(self) -> bool:
        """Whether maintenance and the owner's own requests may start while paused.

        Not while OwlBear or this project stops, nor once the owner asked to stop when idle.
        """
        return not (self.closed() or self.draining())

    def env_action(self, c: Change) -> check.Action | None:
        """What the check environment needs now: launch, dispose or settle; None to leave it."""
        e = c.env
        person = next((p for p in c.checks if e and p.id == e.check), None)
        live = bool(e and e.pids) and all(self.alive(p, t) is not False for p, t in e.pids.items())
        return check.action(c, live=live, paths=check.fingerprints(c, person) if person else {})

    def clear(self, c: Change, e: Environment) -> Found | None:
        """Dispose of all the environment may have started; an uncertain launch is found by the worktree scan."""
        if e.launched_at and e.pgid is None and c.names.worktree:
            try:
                found = self.scan(Path(c.names.worktree), e.launched_at)
            except WorktreeProcessScanError:
                return None
            e = e.model_copy(update={"pids": e.pids | {p: check.created(p) for p in found}})
        return check.dispose(e)

    def _stale(self) -> bool:
        """Whether the package differs from what this host loaded, or cannot be read; checked again on every launch."""
        code = self.code()
        if code.startswith(codebase.UNREADABLE):
            reason = f"Delivery's code cannot be read: {code.removeprefix(codebase.UNREADABLE)}"
        else:
            reason = RESTART if code != self.record.code else None
        if reason != self.refused:
            self.say(f"no runner starts: {reason}" if reason else "Delivery's code is as loaded; runners start again")
            self.refused = reason
        return reason is not None

    def _launch(self, slug: str) -> bool:
        if self._stale():
            return False  # its runners could write state this host cannot read
        recent = [t for t in self.launches.get(slug, []) if time.monotonic() - t < BURST[1]]
        if len(recent) >= BURST[0]:
            return False  # A runner that keeps exiting at once is retried after the window, not in a spin.
        with self.launching:  # a project folder rename or a project's stop waits, so no runner starts during it
            if self.updating():
                return False  # an update's fence: nothing starts until it hands over or lifts it
            if self.paused() and not (slug in self.passing and self.owner_runs()):
                return False
            if (granted := session_slots.reserve(self, slug)) is None:
                return False  # waits for a session slot (TD-336); no launch is counted
            self.launches[slug], self.grants[slug] = [*recent, time.monotonic()], granted
            try:
                rec = self.spawn(slug).model_copy(update={"sessions": granted})
            except BaseException:
                session_slots.release(self, slug)
                raise
            atomic_write(self._path(slug), rec.model_dump_json())
        self.say(f"{slug}: runner {rec.pid} started")
        return True

    def _spawn(self, slug: str) -> RunnerRecord:
        started = datetime.now(UTC)  # before the runner can commit, so its exit is later than this
        argv = [sys.executable, "-m", "owlbear_delivery_next", "run", slug, "--repo", str(self.repo)]
        argv += ["--sessions", str(self.grants.pop(slug, 1))]  # what its agent sessions may use at once (TD-336)
        with (self.store.root / "changes" / slug / "runner.log").open("ab") as out:
            proc = subprocess.Popen(  # noqa: S603 - this interpreter and a fixed module
                argv,
                cwd=self.repo,
                env={**os.environ, data_repo.VIEW: str(self.store.shared.root) if self.store.shared else ""},
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        threading.Thread(target=lambda: (proc.wait(), self.wake.set()), daemon=True).start()
        created = None
        with contextlib.suppress(psutil.Error):
            created = psutil.Process(proc.pid).create_time()
        return RunnerRecord(pid=proc.pid, created=created, started_at=started)

    def run(self) -> None:
        """Scheduler thread: wake on start, inbox items, runner exits, the timer, and after sleep."""
        wall, mono = time.time(), time.monotonic()
        self.wake.set()
        while not self.stopped.is_set():
            self.wake.wait(self.interval())
            self.wake.clear()
            if abs((time.time() - wall) - (time.monotonic() - mono)) > SLEEP_JUMP:
                self.say("woke from sleep: observing every Change")
            wall, mono = time.time(), time.monotonic()
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - the scheduler outlives one failed pass
                self.say(f"pass failed: {type(exc).__name__}: {exc}")
