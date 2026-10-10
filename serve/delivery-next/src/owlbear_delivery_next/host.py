"""Delivery host: one per clone; scheduler, runner launcher, termination scan and check environments (D4 §3.2)."""

from __future__ import annotations

import contextlib
import fcntl
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import psutil
import uvicorn
from pydantic import ValidationError

from owlbear_delivery_next import api, loop, sdk_adapter, setup, tools
from owlbear_delivery_next.models import ErrorKind, Exit, Profile, Record, StepKind, Stop
from owlbear_delivery_next.process_probe import ProcessTableWorktreeProbe, WorktreeProcessScanError
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import check, engine, worktree
from owlbear_delivery_next.storage_io import atomic_write, open_lock
from owlbear_delivery_next.store import LockHeldError, Store, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.loop import PrState, Seen
    from owlbear_delivery_next.models import Change, Environment
    from owlbear_delivery_next.store import Lock

TICK = 30.0
PR_POLL = 20.0
FAST = 2.0  # while a runner this host did not start may still run
SLEEP_JUMP = 60.0
BURST = (5, 60.0)  # at most five runner launches per Change in this many seconds
type Found = dict[int, str]


class HostRecord(Record):
    """``host.json``: where the status view listens and the token its writes need."""

    url: str
    token: str
    pid: int
    started_at: datetime
    ready: list[str] | None = None  # failed readiness facts with their fix; None while the check runs


class RunnerRecord(Record):
    """``runner.json``: the launched runner, kept until its termination is confirmed."""

    pid: int
    created: float | None
    started_at: datetime


def running(store: Store) -> HostRecord | None:
    """Return the live host's record; None when no process holds the host lock, so Delivery is not running."""
    try:
        fd = os.open(store.root / "host.lock", os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
        with contextlib.suppress(OSError, ValidationError):
            return HostRecord.model_validate_json((store.root / "host.json").read_text())
        return HostRecord(url="(starting)", token="", pid=0, started_at=datetime.now(UTC))
    finally:
        os.close(fd)
    return None


def activity(store: Store, slug: str, host: HostRecord | None) -> Activity:
    """Observed liveness for the status line: the Change lock's holder, unless it is the host itself."""
    holder = store.holder(slug)
    runner = holder is not None and (host is None or holder.pid != host.pid)
    last = next((e["at"] for e in reversed(store.events(slug)) if "at" in e), None)
    at = datetime.fromisoformat(last) if last else None
    return Activity(
        host_up=host is not None, runner_alive=runner, holder_pid=holder.pid if runner else None, last_event_at=at
    )


def _scan(path: Path, since: datetime) -> Found:
    return dict(ProcessTableWorktreeProbe().active_processes((path,), started_after=since))


def _block(found: Found | None, now: datetime) -> Stop:
    if found is None:
        reason, action = "the process table could not be scanned", "Check that no process of this step remains"
    else:
        named = ", ".join(f"{p} ({n})" if n else str(p) for p, n in sorted(found.items()))
        reason, action = f"processes still present: {named}", f"End processes {', '.join(map(str, sorted(found)))}"
    return Stop(kind=ErrorKind.LIVENESS, reason=reason, action=action, resume="The host sees none of them", at=now)


def _unverified(c: Change) -> bool:
    return bool(c.stop and c.stop.kind == ErrorKind.LIVENESS and c.outcome and c.outcome.exit == Exit.STOP)


def disappeared(prior: Change, rec: RunnerRecord, now: datetime) -> bool:
    """Whether the runner ended without committing an exit while its step was runnable."""
    o = prior.outcome
    return not (o and o.at >= rec.started_at) and prior.env is None and loop.next_step(prior, now) is not None


def gone(kind: StepKind) -> loop.StepResult:
    """One counted liveness retry for a runner that disappeared, so a repeating startup failure escalates."""
    cause = loop.cause_key(ErrorKind.LIVENESS, kind, "runner-gone")
    return loop.StepResult(exit=Exit.RETRY, cause=cause, reason="the runner ended without recording an exit")


class Host:
    """The scheduler: observes every Change, folds inboxes and starts at most one runner per Change."""

    def __init__(  # noqa: PLR0913 - process seams the tests replace
        self,
        store: Store,
        repo: Path,
        *,
        spawn: Callable[[str], RunnerRecord] | None = None,
        scan: Callable[[Path, datetime], Found] = _scan,
        group: Callable[[int], Found] = check.members,
        alive: Callable[[int, float | None], bool | None] = sdk_adapter.alive,
    ) -> None:
        self.store, self.repo, self.scan, self.group, self.alive = store, repo, scan, group, alive
        self.spawn = spawn or self._spawn
        self.wake, self.stopped = threading.Event(), threading.Event()
        self.pr_states: dict[str, PrState] = {}
        self.pr_seen: dict[str, tuple[float, Seen]] = {}
        self.launches: dict[str, list[float]] = {}
        self.record = HostRecord(url="", token="", pid=os.getpid(), started_at=datetime.now(UTC))

    def say(self, text: str) -> None:
        """Write one line to the host's log."""
        sys.stdout.write(f"{datetime.now(UTC):%H:%M:%S} {text}\n")
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
        return activity(self.store, slug, self.record)

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
        for slug in self.store.slugs():
            try:
                if self._one(slug, now or datetime.now(UTC)) and self._launch(slug):
                    launched.append(slug)
            except LockHeldError:
                continue
            except StoreError as exc:
                self.say(f"{slug}: {exc}")
        return launched

    def _one(self, slug: str, now: datetime) -> bool:
        rec = self.runner(slug)
        if rec and self.alive(rec.pid, rec.created) is not False:
            return False  # A live runner finishes on its own; the host never kills it.
        with self.store.lock(slug) as lock:
            prior = self.store.read(slug)  # before the inbox, which may clear a committed outcome
            state, moved = self.observe_pr(slug)
            c, _ = self.store.fold(lock, slug, now, state, moved=moved)
            if moved:
                self.pr_seen.pop(slug, None)  # not applied again to the merge step's next offer
            if rec and disappeared(prior, rec, now) and c.step == prior.step:
                c = loop.apply(c, gone(c.step.kind), now)  # its outcome postdates the runner: charged once
                self.say(f"{slug}: runner {rec.pid} ended without recording an exit")
            act = self._env_action(c)
            if c.env and act in {"dispose", "settle"}:
                if (left := self._clear(c, c.env)) is None or left:
                    return self._blocked(lock, c, left, now)
                c = check.settle(c, now, check.declared(c)) if act == "settle" else c
                c.env = None
                self.say(f"{slug}: check environment disposed")
            step = loop.next_step(c, now)
            if rec or c.blocked or _unverified(c) or (step and not c.env):
                if (found := self._survivors(c, rec)) is None or found:
                    return self._blocked(lock, c, found, now)
                if _unverified(c):
                    c.stop = c.outcome = None
                c.blocked = None
                self._path(slug).unlink(missing_ok=True)
                step = loop.next_step(c, now)
            if c.env:
                c, step = self._environment(lock, c, now), None
            self.store.write(lock, c)
            return step is not None

    def _mark(self, c: Change, found: Found | None, now: datetime) -> None:
        stop = _block(found, now)
        if not (c.blocked and c.blocked.reason == stop.reason):
            c.blocked = stop
            self.say(f"{c.slug}: no writer starts: {stop.reason}")

    def _blocked(self, lock: Lock, c: Change, found: Found | None, now: datetime) -> bool:
        self._mark(c, found, now)
        self.store.write(lock, c)
        return False

    def _survivors(self, c: Change, rec: RunnerRecord | None) -> Found | None:
        """Processes of the last step still present: recorded PIDs, the runner's former group, the worktree."""
        since = rec.started_at if rec else c.step.started_at
        pids: dict[int, float | None] = {rec.pid: rec.created} if rec else {}
        for e in self.store.events(c.slug) if since else []:
            if e.get("event") == "pids" and datetime.fromisoformat(e["at"]) >= since - timedelta(seconds=1):
                pids |= {int(p): t for p, t in e["pids"].items()}
        found: Found = {p: "" for p, t in pids.items() if self.alive(p, t) is not False}
        found |= self.group(rec.pid) if rec else {}
        if c.names.worktree and Path(c.names.worktree).exists():
            try:  # Unreadable processes count only if they may have started with the step.
                found |= self.scan(Path(c.names.worktree), since or datetime.now(UTC))
            except WorktreeProcessScanError:
                return None
        return found

    def _env_action(self, c: Change) -> check.Action | None:
        e = c.env
        person = next((p for p in c.checks if e and p.id == e.check), None)
        live = bool(e and e.pids) and all(self.alive(p, t) is not False for p, t in e.pids.items())
        return check.action(c, live=live, paths=check.fingerprints(c, person) if person else {})

    def _clear(self, c: Change, e: Environment) -> Found | None:
        """Dispose of all the environment may have started; an uncertain launch is found by the worktree scan."""
        if e.launched_at and e.pgid is None and c.names.worktree:
            try:
                found = self.scan(Path(c.names.worktree), e.launched_at)
            except WorktreeProcessScanError:
                return None
            e = e.model_copy(update={"pids": e.pids | {p: check.created(p) for p in found}})
        return check.dispose(e)

    def _environment(self, lock: Lock, c: Change, now: datetime) -> Change:
        """Launch the check environment after the preparing Builder is gone; pending once it answers."""
        e = c.env
        if e is None or self._env_action(c) != "launch":
            return c
        if (left := self._clear(c, e)) is None or left:
            self._mark(c, left, now)  # never a second group beside one that may still run
            return c
        root, launch = Path(c.names.worktree), worktree.allowed(self.store.read_profile() or Profile(), StepKind.CHECK)
        recipe = tools.CheckRecipe(command=e.command, directory=e.directory, ready_url=e.ready_url, summary="host")
        errors = tools.check_recipe(recipe, tools.Worktree("", ""), launch, root)
        if errors:
            c.env = None
            self.say(f"{c.slug}: check environment failed: {'; '.join(errors)}")
            return loop.apply(c, check.failed("; ".join(errors)), now)
        c.env = e = e.model_copy(update={"pids": {}, "pgid": None, "ready_at": None, "launched_at": datetime.now(UTC)})
        self.store.write(lock, c)
        if proc := check.start(e, root, self.store.root / "changes" / c.slug / "env.log"):
            c.env = e = e.model_copy(update={"pgid": proc.pid, "pids": {proc.pid: check.created(proc.pid)}})
            self.store.write(lock, c)
        pids = check.ready(e, proc) if proc else None
        if pids is None:
            if (left := self._clear(c, e)) is None or left:
                self._mark(c, left, now)
                return c
            c.env = None
            self.say(f"{c.slug}: check environment failed: no answer at {e.ready_url}")
            return loop.apply(c, check.failed(f"no answer at {e.ready_url}"), now)
        c.env = e.model_copy(update={"pids": pids, "ready_at": datetime.now(UTC)})
        self.say(f"{c.slug}: check environment ready at {e.ready_url}, group {e.pgid}, PIDs {sorted(pids)}")
        return loop.apply(c, check.pending(c, c.env), now)

    def _launch(self, slug: str) -> bool:
        recent = [t for t in self.launches.get(slug, []) if time.monotonic() - t < BURST[1]]
        if len(recent) >= BURST[0]:
            return False  # A runner that keeps exiting at once is retried after the window, not in a spin.
        self.launches[slug] = [*recent, time.monotonic()]
        rec = self.spawn(slug)
        atomic_write(self._path(slug), rec.model_dump_json())
        self.say(f"{slug}: runner {rec.pid} started")
        return True

    def _spawn(self, slug: str) -> RunnerRecord:
        started = datetime.now(UTC)  # before the runner can commit, so its exit is later than this
        argv = [sys.executable, "-m", "owlbear_delivery_next.runner", slug, "--repo", str(self.repo)]
        with (self.store.root / "changes" / slug / "runner.log").open("ab") as out:
            proc = subprocess.Popen(  # noqa: S603 - this interpreter and a fixed module
                argv,
                cwd=self.repo,
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
            watching = any(self.runner(s) for s in self.store.slugs())
            self.wake.wait(FAST if watching else TICK)
            self.wake.clear()
            if abs((time.time() - wall) - (time.monotonic() - mono)) > SLEEP_JUMP:
                self.say("woke from sleep: observing every Change")
            wall, mono = time.time(), time.monotonic()
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - the scheduler outlives one failed pass
                self.say(f"pass failed: {type(exc).__name__}: {exc}")


def serve(repo: Path) -> int:
    """Start the one host of this clone, or print the running host's URL and exit 0."""
    store = Store.open(repo)
    dir_fd = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock_fd = open_lock(dir_fd, blocking=False, name="host.lock")
    except BlockingIOError:
        found = running(store)
        sys.stdout.write(f"Delivery is already running: {api.link(found) or '(starting)'}\n")
        return 0
    finally:
        os.close(dir_fd)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    url, token = f"http://127.0.0.1:{sock.getsockname()[1]}/", secrets.token_urlsafe(32)
    host = Host(store, repo)
    host.record = host.record.model_copy(update={"url": url, "token": token})
    atomic_write(store.root / "host.json", host.record.model_dump_json())
    (store.root / "host.json").chmod(0o600)
    host.say(f"Delivery host {os.getpid()} on {api.link(host.record)}")

    def ready() -> None:
        failed = [f"{c.name}: {c.detail} · fix: {c.fix}" for c in setup.check(repo, store.read_profile()) if not c.ok]
        host.record = host.record.model_copy(update={"ready": failed})
        if not host.stopped.is_set():
            atomic_write(store.root / "host.json", host.record.model_dump_json())
        host.say("readiness: " + ("; ".join(failed) or "ok"))

    threading.Thread(target=ready, daemon=True, name="readiness").start()
    threading.Thread(target=host.run, daemon=True, name="scheduler").start()
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, token, host), log_level="warning"))
    try:
        with contextlib.suppress(KeyboardInterrupt):
            server.run(sockets=[sock])
    finally:
        host.stopped.set()
        (store.root / "host.json").unlink(missing_ok=True)
        os.close(lock_fd)
    return 0
