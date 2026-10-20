"""The decision index: words, retired decisions, freshness, corruption, concurrent rebuilds, a busy file (slice 3)."""

from __future__ import annotations

import fcntl
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, new_id, write
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_index
from owlbear_delivery_next.state_store.decision_store import save

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


@pytest.fixture
def indexed(shared_repo, monkeypatch) -> DataRepo:
    monkeypatch.setenv("OWLBEAR_DATA", str(shared_repo[0]))
    return DataRepo(shared_repo[0])


def ids(text: str, **options) -> set[str]:
    return {hit.id for hit in decision_index.search(text, PROJECT, **options)}


@pytest.mark.parametrize("fts", [True, False])
def test_the_index_finds_words_and_hides_retired_decisions(indexed, monkeypatch, fts) -> None:
    monkeypatch.setattr(decision_index, "FTS", fts and decision_index.FTS)
    notes = make()
    gone = make(title="Notes in files", statement="Notes live in files.", state=State.WITHDRAWN)
    lint = make(title="Lint once", statement="Code is linted at submission.", scope=Scope.GLOBAL, project="")
    other = make(project="other-site")
    for decision in (notes, gone, lint, other):
        save(indexed, decision, expected_revision=None, message="m")

    assert ids("notes") == {notes.id}
    assert ids("notes", include_retired=True) == {notes.id, gone.id}
    assert ids("SQLite table") == {notes.id}
    assert ids("lint") == {lint.id}
    assert ids("") == {notes.id, lint.id}
    assert ids("nothing_like_it") == set()
    hit = decision_index.search("table", PROJECT)[0]
    assert (hit.title, hit.statement, hit.scope, hit.state, hit.origin) == (
        notes.title, notes.statement, "project", "in_force", "autonomous"
    )  # fmt: skip


def test_the_index_follows_new_commits_and_uncommitted_files(indexed) -> None:
    indexed.claim(PROJECT, "github.com/acme/shop-site")
    assert ids("notes") == set()
    first = make()
    save(indexed, first, expected_revision=None, message="m")
    assert ids("notes") == {first.id}
    later = make(title="Notes are short")
    write(later, indexed.root / PROJECT)
    assert ids("notes") == {first.id, later.id}


def test_a_corrupt_index_is_rebuilt_never_trusted(indexed) -> None:
    decision = make()
    save(indexed, decision, expected_revision=None, message="m")
    assert ids("notes") == {decision.id}
    decision_index.path().write_bytes(b"not a database at all" * 100)
    assert ids("notes") == {decision.id}
    with sqlite3.connect(decision_index.path()) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == decision_index.FORMAT


def test_concurrent_rebuilders_wait_for_the_lock_and_leave_one_valid_index(indexed, monkeypatch) -> None:
    decision = make()
    save(indexed, decision, expected_revision=None, message="m")
    assert ids("notes") == {decision.id}
    file, garbage = decision_index.path(), b"not a database at all"
    file.write_bytes(garbage * 100)
    real, discarded = decision_index._discard, []  # noqa: SLF001 - counted
    monkeypatch.setattr(decision_index, "_discard", lambda f: (discarded.append(f), real(f)))
    lock = os.open(file.with_name(f"{file.name}.lock"), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with ThreadPoolExecutor(2) as pool:
            searches = [pool.submit(ids, "notes") for _ in range(2)]
            time.sleep(0.5)
            untouched = file.read_bytes().startswith(garbage)
            fcntl.flock(lock, fcntl.LOCK_UN)
            found = [s.result(timeout=30) for s in searches]
    finally:
        os.close(lock)
    assert untouched  # nobody replaced the file without the lock
    assert found == [{decision.id}, {decision.id}]
    assert len(discarded) == 1  # the second rebuilder saw the first one's file and kept it
    with sqlite3.connect(file) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == decision_index.FORMAT
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_a_busy_index_is_retried_then_reported_never_rebuilt(indexed, monkeypatch) -> None:
    decision = make()
    save(indexed, decision, expected_revision=None, message="m")
    assert ids("notes") == {decision.id}
    file = decision_index.path()
    before = file.stat().st_ino
    monkeypatch.setattr(decision_index, "BUSY_MS", 50)
    holder = sqlite3.connect(file, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(decision_index.IndexBusy):
            decision_index.search("notes", PROJECT)
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    assert file.stat().st_ino == before
    assert ids("notes") == {decision.id}
