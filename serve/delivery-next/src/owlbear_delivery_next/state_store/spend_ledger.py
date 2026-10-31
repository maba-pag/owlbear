"""Every credit OwlBear spends, in one append-only ledger on this machine (D-01M5XCDF6G60VG5GHTWF5QSSDE).

Each model session OwlBear runs writes a ``start`` line once it opens and an ``end`` line once its lifecycle ends,
finished, failed, timed out or cancelled; both carry its run id, its runtime session and where it ran. A run killed
with its process leaves its ``start`` only: it stays open until a later run of its session, or ``spend_reconcile``
reading the runtime's own log, accounts for it. ``usage`` is the session's cumulative usage as the runtime reported
it, ``before`` the same just before this run sent anything (``{}`` for a new session, None when unread);
``spend_shares`` turns them into each run's own share. ``spend_reconcile`` adds lines of its own, with deterministic
ids, for what OwlBear's other records hold.

Lines go to ``~/.owlbear/spend/spend-YYYY-MM.jsonl`` (owner-only, by the month written) through one writer thread,
never from an SDK event loop, so a step never waits for them. A line that cannot be written is kept and tried again
with the next one and at exit; one still unwritten is said on stderr, and its run then shows as open or is recovered
by ``spend_reconcile``. Metrics never limit: nothing reads this ledger to admit, stop or retry anything.
"""

from __future__ import annotations

import atexit
import contextlib
import fcntl
import json
import os
import queue
import sys
import threading
import time
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store

LOCK, GRACE, KEPT = 5.0, 2.0, 10_000  # seconds a lock is waited for; at exit; lines kept while writes fail


@dataclass(frozen=True)
class Where:
    """Where a run's spend counts: its project, Change and step; empty for machine-wide work.

    ``project`` is the canonical key: the project's folder in the shared repository, which every clone of it, its
    memory and its decisions share; the clone's id only for a clone without one. ``name`` is what a page shows and
    ``clone`` the local clone's id, kept apart from the key.
    """

    project: str = ""
    name: str = ""
    clone: str = ""
    change: str = ""
    step: str = ""
    job: str = ""  # the work it is part of when the session's own job does not say, such as a chat's lookup

    @classmethod
    def of(cls, store: Store, repo: Path | None = None, **more: str) -> Where:
        """The place of work for *store*'s project, cloned at *repo*."""
        clone = store.root.name
        return cls(project=store.name or clone, name=store.name or (repo.name if repo else clone), clone=clone, **more)


_HERE: ContextVar[Where] = ContextVar("spend_where", default=Where())  # noqa: B039 - frozen, never mutated


def where() -> Where:
    """The place this code runs for; machine-wide unless an entry point set one."""
    return _HERE.get()


def enter(place: Where) -> None:
    """Set *place* for the rest of this context: a process's entry for one Change, such as a runner."""
    _HERE.set(place)


@contextlib.contextmanager
def at(place: Where) -> Iterator[None]:
    """Set *place* while the block runs, in this thread and every task or ``to_thread`` call it starts."""
    token = _HERE.set(place)
    try:
        yield
    finally:
        _HERE.reset(token)


def folder() -> Path:
    """Where the ledger lives; nothing is created."""
    return local_home.root() / "spend"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _placed(place: Where | None, job: str = "") -> dict[str, str]:
    """The place's fields; the session's own *job* wins over the work's."""
    found = asdict(place or where())
    return found | {"job": job or found["job"]}


STOPS = ("", "reached", "unknown")  # a run's stop at its credit limit: none, reached, or not known (``credit_meter``)


def started(  # noqa: PLR0913 - the run, its session and what it is
    run: str, session: str, *, agent: str, job: str, model: str | None, before: dict[str, Any] | None,
            place: Where | None = None, look: str = "", cli: str = "", cli_error: str = "") -> None:  # fmt: skip
    """A run opened its session; *before* is its usage before the first send (None unread, ``{}`` new).

    *look* is a Spotter look's own id, the one its Spotter record carries, so the two are never counted twice.
    *cli* is the Copilot CLI version the session runs, empty with *cli_error* when it could not be read; a run that
    passes neither, such as a Spotter look, writes no ``cli``.
    """
    ran = ({"look": look} if look else {}) | ({"cli": cli} if cli or cli_error else {})
    ran |= {"cli_error": cli_error} if cli_error else {}
    put({"id": f"start:{run}", "type": "start", "run": run, "at": _now(), "session": session, "agent": agent,
         "model": model or "", "before": before, **_placed(place, job)} | ran)  # fmt: skip


def ended(  # noqa: PLR0913 - the run, its session and how it ended
    run: str, session: str, *, usage: dict[str, Any], ending: str, limit: float | None = None, stopped: str = "",
          stopped_by: str = "", subagents: int = 0, place: Where | None = None, look: str = "",
          tools: dict[str, dict[str, int]] | None = None, wrong: dict[str, int] | None = None) -> None:  # fmt: skip
    """A run's lifecycle ended: its session's cumulative *usage* (``{"error": …}`` unread), how and why it stopped.

    *stopped* is one of ``STOPS``; *stopped_by* names the limit's scope that stopped it, as the credit meter does.
    A run Delivery's gate measured carries its *tools* tally and *wrong* tool choices, even empty (C-28 T8).
    """
    measured = {"tools": tools, "wrong": wrong} if tools is not None and wrong is not None else {}
    put({"id": f"end:{run}", "type": "end", "run": run, "at": _now(), "session": session, "usage": usage,
         "ending": ending, "limit": limit, "stopped": stopped, "stopped_by": stopped_by, "subagents": subagents,
         **_placed(place)} | {"job": ""} | ({"look": look} if look else {}) | measured)  # fmt: skip


class _Writer:
    """One daemon thread appending lines in order; the process waits at most ``GRACE`` for it at exit."""

    def __init__(self) -> None:
        self.jobs: queue.Queue[dict[str, Any]] = queue.Queue()
        self.lock, self.started, self.unwritten = threading.Lock(), False, list[dict[str, Any]]()

    def put(self, line: dict[str, Any]) -> None:
        with self.lock:
            if not self.started:
                threading.Thread(target=self._serve, name="spend-ledger", daemon=True).start()
                self.started = True
        self.jobs.put(line)

    def _serve(self) -> None:
        while True:
            line = self.jobs.get()
            try:
                self.unwritten = append([*self.unwritten, line])
            finally:
                self.jobs.task_done()

    def settled(self, seconds: float) -> bool:
        """Wait at most *seconds* until every queued line was tried; whether all were."""
        until = time.monotonic() + seconds
        while self.jobs.unfinished_tasks and time.monotonic() < until:
            time.sleep(0.01)
        return not self.jobs.unfinished_tasks


WRITER = _Writer()
put = WRITER.put


def _exit() -> None:
    WRITER.settled(GRACE)
    if WRITER.unwritten and append(WRITER.unwritten):
        sys.stderr.write(f"spend ledger: {len(WRITER.unwritten)} line(s) not written\n")


atexit.register(_exit)


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        until = time.monotonic() + LOCK
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > until:
                    raise TimeoutError(path.name) from None
                time.sleep(0.02)
        yield
    finally:
        os.close(fd)


def append(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append *lines* under the ledger's lock, each to its month's file; those that could not be written."""
    if not lines:
        return []
    try:
        here = folder()
        here.mkdir(parents=True, exist_ok=True, mode=0o700)
        here.chmod(0o700)
        with _locked(here / "spend.lock"):
            name = f"spend-{datetime.now(UTC):%Y-%m}.jsonl"
            fd = os.open(here / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "a") as out:
                out.write("".join(json.dumps(line, default=str) + "\n" for line in lines))
    except (OSError, TimeoutError, ValueError) as exc:
        sys.stderr.write(f"spend ledger: {len(lines)} line(s) kept to try again ({exc})\n")
        return lines[-KEPT:]
    return []


def lines() -> list[dict[str, Any]]:
    """Every line kept, oldest file first, each id once; an unreadable line or file is skipped."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for path in sorted(folder().glob("spend-*.jsonl")) if folder().is_dir() else ():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw in text.splitlines():
            try:
                line = json.loads(raw)
            except ValueError:
                continue
            if isinstance(line, dict) and isinstance(ident := line.get("id"), str) and ident not in seen:
                seen.add(ident)
                out.append(line)
    return out


def stamp() -> tuple[tuple[str, int, int], ...]:
    """What changes whenever a line is added: each file's name, size and modification time."""
    if not folder().is_dir():
        return ()
    found = []
    for path in sorted(folder().glob("spend-*.jsonl")):
        with contextlib.suppress(OSError):
            s = path.stat()
            found.append((path.name, s.st_size, s.st_mtime_ns))
    return tuple(found)
