"""The watcher's reports (W1a, design §3.6): one row per observed call that may write outside its session's folder.

Rows live in the database's ``watch`` table, never capped, one per Change, session and tool call: a later look at
the same call replaces its row, and one found inside after all removes it. Each session's reports go through its own
writer thread in order, from a bounded queue the event callback never waits on. Closing it drains the queue for at
most ``DRAIN`` seconds, then stops it; what was dropped or not written is one summary row, or a line in the runner's
log when the database cannot take it in time. A report says a command was observed writing somewhere, never that the
write happened.
"""

from __future__ import annotations

import json
import queue
import sqlite3
import threading
import time
from dataclasses import astuple, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.state_store.database import RETRY, BusyError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.state_store.database import Database
    from owlbear_delivery_next.state_store.store import Lock

SHOWN = 200  # the newest reports a page reads
SIZE = 1000  # operations a session's queue holds; more are dropped and counted
WAIT = 2.0  # seconds one write may wait for the fence or SQLite's lock before it is tried again
DRAIN = 10.0  # seconds the close waits for the queue to empty
SUMMARY = "(not recorded)"  # the call id of a session's summary row
FIELDS = ("session", "call_id", "at", "step", "agent", "tool", "command", "targets", "verdict", "unresolved", "source")
PUT = (
    "INSERT INTO watch(slug, session, call_id, at, step, agent, tool, command, targets, verdict, unresolved, source) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(slug, session, call_id) DO UPDATE SET at = excluded.at, "
    "step = excluded.step, agent = excluded.agent, tool = excluded.tool, command = excluded.command, "
    "targets = excluded.targets, verdict = excluded.verdict, unresolved = excluded.unresolved, source = excluded.source"
)
READ = (
    "SELECT session, call_id, at, step, agent, tool, command, targets, verdict, unresolved, source FROM watch "
    "WHERE slug = ? ORDER BY at DESC, id DESC LIMIT ?"
)

type Operation = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class Report:
    """One observed call as its row holds it; ``targets`` are canonical paths outside."""

    session: str
    call_id: str
    at: str
    step: str
    agent: str
    tool: str
    command: str
    targets: tuple[str, ...]
    verdict: str
    unresolved: str  # what may have been written that the watcher cannot see yet; empty when nothing
    source: str  # "start", "enriched" (a permission request added to it), "permission" (no start yet) or "writer"


def put(slug: str, report: Report) -> Operation:
    """The upsert of one call's row; its id, and so its place among the Change's reports, stays."""
    values = (slug, *astuple(report)[:7], json.dumps(list(report.targets)), *astuple(report)[8:])

    def operation(connection: sqlite3.Connection) -> None:
        connection.execute(PUT, values)

    return operation


def drop(slug: str, session: str, call_id: str) -> Operation:
    """The removal of a call's row, once it is found inside after all."""

    def operation(connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM watch WHERE slug = ? AND session = ? AND call_id = ?", (slug, session, call_id))

    return operation


def reports(db: Database, slug: str, limit: int = SHOWN) -> list[dict[str, Any]]:
    """The Change's newest reports, newest first."""
    with db.read() as connection:
        rows = connection.execute(READ, (slug, limit)).fetchall()
    found = [dict(zip(FIELDS, row, strict=True)) for row in rows]
    return [r | {"targets": json.loads(r["targets"] or "[]")} for r in found]


def counts(db: Database, slug: str) -> dict[str, int]:
    """How many of the Change's observed calls write outside, and how many have effects not classified yet."""
    with db.read() as connection:
        row = connection.execute(
            "SELECT count(*) FILTER (WHERE targets != '[]'), count(*) FILTER (WHERE unresolved != '') FROM watch "
            "WHERE slug = ? AND call_id != ?",
            (slug, SUMMARY),
        ).fetchone()
    return {"outside": row[0], "unresolved": row[1]}


class Writer:
    """One session's report writer: a thread that persists queued operations in order, each within ``WAIT``."""

    def __init__(self, db: Database, lock: Lock, *, note: Callable[[str], None], size: int = SIZE) -> None:
        """*note* writes a line to the runner's log, where what the database could not take is told."""
        self.db, self.lock, self.note = db, lock, note
        self.queue: queue.Queue[Operation] = queue.Queue(maxsize=size)
        self.dropped = self.failed = 0  # operations refused (queue full or intake closed); writes that gave up
        self.error = ""  # the last storage failure
        self.open = True
        self._counted = threading.Lock()
        self._stopping = threading.Event()
        self.thread = threading.Thread(target=self._work, name=f"watch-{lock.slug}", daemon=True)
        self.thread.start()

    def put(self, operation: Operation) -> None:
        """Queue one operation without waiting; a full queue or a closed intake counts it as dropped."""
        try:
            if self.open:
                self.queue.put_nowait(operation)
                return
        except queue.Full:
            pass
        self.late()

    def late(self) -> None:
        """Count one operation as dropped: the queue was full or the intake had closed."""
        with self._counted:
            self.dropped += 1

    def lost(self, error: str) -> None:
        """Count one report that could not be made or written."""
        with self._counted:
            self.failed, self.error = self.failed + 1, error

    def close(self, summary: Callable[[str], Report], deadline: float = DRAIN) -> None:
        """Close the intake, drain within *deadline*, stop the thread, then tell what was not recorded.

        *summary* makes the summary row from its text; it is written only when the queue drained in time.
        """
        self.open = False
        until = time.monotonic() + deadline
        drained = self._drained(until)
        told, row, failed = "", None, self.failed
        if drained and (said := self._said(0)):
            row = put(self.lock.slug, summary(said))
            self.queue.put_nowait(row)
            told = said if self._drained(until) and self.failed == failed else ""
        self._stopping.set()
        self.thread.join()  # each write gives up within WAIT and none starts once stopping
        undrained = 0
        while not self.queue.empty():
            undrained += self.queue.get_nowait() is not row
        if row is not None:
            self.failed = failed  # the summary row is no report: its own failure is not counted
        if (said := self._said(undrained)) and said != told:
            self.note(f"watcher {self.lock.slug}: {said}")

    def _said(self, undrained: int) -> str:
        parts = [f"{self.dropped} report{'s' if self.dropped != 1 else ''} dropped"] if self.dropped else []
        parts += [f"{undrained} not written by the deadline"] if undrained else []
        parts += [f"{self.failed} failed ({self.error})"] if self.failed else []
        return "; ".join(parts)

    def _drained(self, until: float) -> bool:
        with self.queue.all_tasks_done:
            while self.queue.unfinished_tasks:
                if (left := until - time.monotonic()) <= 0:
                    return False
                self.queue.all_tasks_done.wait(left)
        return True

    def _work(self) -> None:
        while not self._stopping.is_set():
            try:
                operation = self.queue.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                self._write(operation)
            finally:
                self.queue.task_done()

    def _write(self, operation: Operation) -> None:
        while True:
            try:
                self.lock.check(self.lock.slug)
                with self.db.write(wait=WAIT) as connection:
                    operation(connection)
            except BusyError as exc:
                if not self._stopping.wait(RETRY):
                    continue
                self.lost(str(exc))
            except (StoreError, RuntimeError, sqlite3.Error, OSError) as exc:
                self.lost(str(exc) or type(exc).__name__)
            return


def summary_row(session: str, step: str, said: str) -> Report:
    """A session's summary row: what its writer did not record."""
    at = datetime.now(UTC).isoformat(timespec="milliseconds")
    return Report(session, SUMMARY, at, step, "", "", "", (), f"not recorded: {said}", "", "writer")
