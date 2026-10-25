"""The watcher's reports (W1a): the additive table, its bounded reads, and the bounded writer thread."""

from __future__ import annotations

import contextlib
import re
import sqlite3
import subprocess
import sys
import threading
import time

import pytest

from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.state_store import database, watch_reports
from owlbear_delivery_next.state_store.database import STORE_FORMAT, BusyError
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.state_store.watch_reports import Report, Writer

OPEN_AT_ONCE = """
import sys, time
from pathlib import Path
from owlbear_delivery_next.state_store import watch_reports
from owlbear_delivery_next.state_store.store import Store
root = Path(sys.argv[1])
while not (root / "go").exists():
    time.sleep(0.005)
store = Store(root)
print(len(watch_reports.reports(store.db, "c1")), watch_reports.counts(store.db, "c1")["outside"])
"""


def report(n: int, *, targets: tuple[str, ...] = ("/elsewhere/x",), unresolved: str = "") -> Report:
    verdict = "outside write (not judged yet)" if targets else f"unresolved ({unresolved})"
    at = f"2026-10-24T10:{n // 60:02d}:{n % 60:02d}.000+00:00"
    return Report(
        "s1", f"call-{n}", at, "build", "unknown", "edit", f"edit x{n}", targets, verdict, unresolved, "start"
    )


def put(store: Store, *reports: Report) -> None:
    with store.db.write() as connection:
        for r in reports:
            watch_reports.put("c1", r)(connection)


def pre_w1(root) -> Store:
    """A store as a runtime before the watcher left it: no ``watch`` table."""
    store = Store(root)
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1"))
    raw = sqlite3.connect(root / database.DB)
    raw.execute("DROP TABLE watch")
    raw.close()
    return Store(root)  # a new process's view


@pytest.fixture
def store(tmp_path) -> Store:
    s = Store(tmp_path)
    s.db.check()
    return s


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(watch_reports, "WAIT", 0.1)


def writer(store: Store, notes: list[str], size: int = watch_reports.SIZE) -> Writer:
    return Writer(store.db, Lock("c1"), note=notes.append, size=size)


def lost(note: str) -> int:
    """How many reports a writer's log line says were failed or not written by the deadline."""
    return sum(int(n) for n in re.findall(r"(\d+) (?:not written by the deadline|failed)", note))


def summary(said: str) -> Report:
    return watch_reports.summary_row("s1", "build", said)


def threads() -> list[threading.Thread]:
    """The writer threads alive that this test started."""
    return [t for t in threading.enumerate() if t.name.startswith("watch-") and t not in BEFORE]


BEFORE: set[threading.Thread] = set()


@pytest.fixture(autouse=True)
def _baseline() -> None:
    BEFORE.clear()
    BEFORE.update(threading.enumerate())


def test_a_pre_watcher_database_is_read_by_a_new_hosts_change_page_with_no_write_between(tmp_path) -> None:
    store = pre_w1(tmp_path)
    assert (watch_reports.reports(store.db, "c1"), watch_reports.counts(store.db, "c1")) == (
        [],
        {"outside": 0, "unresolved": 0},
    )
    put(store, report(1))  # the table was added on open, so a runner writes into it
    assert [r["call_id"] for r in watch_reports.reports(Store(tmp_path).db, "c1")] == ["call-1"]
    assert (tmp_path / database.MARKER).read_text().strip() == str(STORE_FORMAT)  # older runtimes still open it
    assert Store(tmp_path).read("c1").slug == "c1"


def test_two_processes_opening_a_pre_watcher_database_at_once_both_read_it(tmp_path) -> None:
    pre_w1(tmp_path)
    procs = [
        subprocess.Popen(  # noqa: S603 - this interpreter and a fixed script
            [sys.executable, "-c", OPEN_AT_ONCE, str(tmp_path)], stdout=subprocess.PIPE, text=True
        )
        for _ in range(2)
    ]
    (tmp_path / "go").touch()
    assert [p.communicate(timeout=60)[0].strip() for p in procs] == ["0 0", "0 0"]
    assert [p.returncode for p in procs] == [0, 0]
    raw = sqlite3.connect(tmp_path / database.DB)
    found = raw.execute("SELECT name FROM sqlite_master WHERE tbl_name = 'watch' ORDER BY name").fetchall()
    raw.close()
    assert [n for (n,) in found if not n.startswith("sqlite_")] == ["watch", "watch_slug"]


def test_reports_are_one_row_per_call_never_capped_and_read_newest_first_and_bounded(store) -> None:
    put(store, *(report(n) for n in range(250)), report(7, targets=(), unresolved="shell effects not classified yet"))
    again = Store(store.root)
    shown = watch_reports.reports(again.db, "c1")
    outside = [r["call_id"] for r in shown if r["targets"]]
    assert (len(outside), outside[0], outside[-1]) == (200, "call-249", "call-50")  # bounded apart from the others
    assert [r["call_id"] for r in shown if not r["targets"]] == ["call-7"]
    assert watch_reports.counts(again.db, "c1") == {"outside": 249, "unresolved": 1}  # call-7 was replaced
    with again.db.write() as connection:
        watch_reports.drop("c1", "s1", "call-8")(connection)
    assert watch_reports.counts(again.db, "c1")["outside"] == 248
    assert watch_reports.reports(again.db, "c2") == []


def test_a_writer_persists_in_order_and_leaves_no_thread_or_summary_when_all_was_written(store) -> None:
    notes: list[str] = []
    w = writer(store, notes)
    for n in range(5):
        w.put(watch_reports.put("c1", report(n)))
    w.close(summary)
    assert not w.thread.is_alive()
    assert not threads()
    assert [r["call_id"] for r in watch_reports.reports(store.db, "c1")] == [f"call-{n}" for n in range(4, -1, -1)]
    assert notes == []


def test_a_full_queue_drops_exactly_what_it_cannot_hold_and_the_summary_row_says_so(store) -> None:
    notes, entered, release = [], threading.Event(), threading.Event()

    def held(_connection) -> None:
        entered.set()
        release.wait(10)

    w = writer(store, notes, size=2)
    w.put(held)
    assert entered.wait(5)
    for n in range(5):
        w.put(watch_reports.put("c1", report(n)))
    release.set()
    w.close(summary)
    rows = watch_reports.reports(store.db, "c1")
    assert [r["call_id"] for r in rows if r["source"] != "writer"] == ["call-1", "call-0"]
    assert [r["verdict"] for r in rows if r["source"] == "writer"] == ["not recorded: 3 reports dropped"]
    assert watch_reports.counts(store.db, "c1") == {"outside": 2, "unresolved": 0}  # the summary is no report
    assert notes == []
    w.late()  # an event after the close is counted, never written
    assert (w.dropped, len(watch_reports.reports(store.db, "c1"))) == (4, 3)


@pytest.mark.usefixtures("fast")
def test_a_migration_fence_held_through_the_deadline_stops_the_writer_and_the_log_says_what_was_lost(store) -> None:
    notes: list[str] = []
    with store.db.fenced():
        w = writer(store, notes)
        for n in range(3):
            w.put(watch_reports.put("c1", report(n)))
        until = time.monotonic() + 5
        while w.queue.qsize() > 2 and time.monotonic() < until:  # the first is the writer's, tried again and again
            time.sleep(0.01)
        started = time.monotonic()
        w.close(summary, deadline=0.3)
        assert time.monotonic() - started < 2
        assert not w.thread.is_alive()
        assert not threads()
    assert len(notes) == 1  # the one in progress at the deadline is failed or not written, whichever saw it first
    assert (notes[0].startswith("watcher c1: "), lost(notes[0])) == (True, 3)
    assert watch_reports.reports(store.db, "c1") == []  # nothing written after the deadline, the summary neither


@pytest.mark.usefixtures("fast")
def test_a_sqlite_write_lock_held_through_the_deadline_stops_the_writer_and_the_log_says_what_was_lost(store) -> None:
    notes: list[str] = []
    other = sqlite3.connect(store.db.path, isolation_level=None)
    other.execute("BEGIN IMMEDIATE")
    try:
        w = writer(store, notes)
        w.put(watch_reports.put("c1", report(0)))
        until = time.monotonic() + 5
        while w.queue.qsize() and time.monotonic() < until:
            time.sleep(0.01)
        w.close(summary, deadline=0.3)
        assert not w.thread.is_alive()
        assert not threads()
    finally:
        other.execute("ROLLBACK")
        other.close()
    assert len(notes) == 1  # the one in progress at the deadline is failed or not written, whichever saw it first
    assert (notes[0].startswith("watcher c1: "), lost(notes[0])) == (True, 1)
    assert watch_reports.reports(store.db, "c1") == []


def test_a_bounded_write_gives_up_as_busy_and_needs_an_open_database(store, tmp_path) -> None:
    with store.db.fenced(), pytest.raises(BusyError, match="being migrated"), store.db.write(wait=0.05):
        pass
    with pytest.raises(BusyError, match="not open yet"), Store(tmp_path / "new").db.write(wait=0.05):
        pass


def test_a_storage_failure_is_counted_and_told_in_the_runners_log_when_its_summary_cannot_be_written(
    store, monkeypatch
) -> None:
    notes: list[str] = []

    def broken(*_a, **_k):
        msg = "the Delivery database failed: disk I/O error"
        raise database.StoreError(msg)

    monkeypatch.setattr(store.db, "write", broken)
    w = writer(store, notes)
    w.lost("ValueError: bad event")  # a report that could not be made
    w.put(watch_reports.put("c1", report(0)))
    w.close(summary)
    assert not w.thread.is_alive()
    assert notes == ["watcher c1: 2 failed (the Delivery database failed: disk I/O error)"]


def test_a_write_that_gets_the_database_only_after_the_deadline_does_not_run(store, monkeypatch) -> None:
    notes: list[str] = []
    late = store.db.write

    @contextlib.contextmanager
    def slow(**kw):
        time.sleep(0.3)  # the database comes free only after the drain's deadline
        with late(**kw) as connection:
            yield connection

    monkeypatch.setattr(store.db, "write", slow)
    w = writer(store, notes)
    w.put(watch_reports.put("c1", report(0)))
    time.sleep(0.05)  # the writer is waiting for the database
    began = time.monotonic()
    w.close(summary, deadline=0.1)
    assert time.monotonic() - began < 1.0
    assert (w.thread.is_alive(), threads()) == (False, [])
    monkeypatch.undo()
    assert watch_reports.reports(store.db, "c1") == []
    assert notes == ["watcher c1: 1 not written by the deadline"]


def test_a_summary_row_the_deadline_skipped_is_told_in_the_log(store, monkeypatch) -> None:
    notes: list[str] = []
    w = writer(store, notes)
    w.late()  # one report dropped, so a summary row is due
    attempt = w._attempt  # noqa: SLF001

    def expired(operation):
        w._until = 0.0  # noqa: SLF001 - the deadline passed while the summary was made
        return attempt(operation)

    monkeypatch.setattr(w, "_attempt", expired)
    w.close(summary, deadline=1.0)
    assert (w.summed, notes) == (False, ["watcher c1: 1 report dropped"])
    assert watch_reports.reports(store.db, "c1") == []


def test_each_run_of_a_session_keeps_its_own_summary_and_an_outside_write_outlasts_unresolved_rows(store) -> None:
    for said in ("3 reports dropped", "1 report dropped"):  # a run, then its resumed run: the same session
        put(store, watch_reports.summary_row("s1", "build", said))
        time.sleep(0.002)  # the next run closes later
    put(store, report(0), *(report(n, targets=(), unresolved="shell effects not classified yet") for n in (1, 2, 3)))
    shown = watch_reports.reports(store.db, "c1", limit=2)
    assert [r["verdict"] for r in shown if r["source"] == "writer"] == ["not recorded: 1 report dropped",
                                                                         "not recorded: 3 reports dropped"]  # fmt: skip
    assert "call-0" in [r["call_id"] for r in shown]  # the outside write, older than every unresolved row
    assert watch_reports.counts(store.db, "c1") == {"outside": 1, "unresolved": 3}
