"""Decision search over a snapshot (owlbear-data#16): words, prefixes, retired decisions, an uncapped answer."""

from __future__ import annotations

import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_cache, decision_search, decision_store
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


@pytest.mark.parametrize("fts", [True, False], ids=["fts5", "like"])
def test_search_finds_every_word_and_hides_retired_decisions(shared_repo, monkeypatch, fts) -> None:
    monkeypatch.setattr(decision_search, "FTS", fts and decision_search.FTS)
    shared = DataRepo(shared_repo[0])
    notes = make()
    gone = make(title="Notes in files", statement="Notes live in files.", state=State.WITHDRAWN)
    lint = make(title="Lint once", statement="Code is linted at submission.", scope=Scope.GLOBAL, project="")
    other = make(project="other-site")
    for decision in (notes, gone, lint, other):
        save(shared, decision, expected_revision=None, message="m")
    index = decision_search.Index(decision_store.load(shared, PROJECT).snapshot)
    assert index.fts is (fts and decision_search.FTS)

    def ids(text: str, *, include_retired: bool = False) -> frozenset[str]:
        return index.matching(text, include_retired=include_retired)

    assert ids("notes") == {notes.id}
    assert ids("notes", include_retired=True) == {notes.id, gone.id}
    assert ids("SQLite table") == {notes.id}
    assert ids("SQL tab") == {notes.id}  # each word a prefix
    assert ids("SQLite files", include_retired=True) == set()  # every word, in one decision
    assert ids("lint") == {lint.id}
    assert ids("") == ids("  ?! ") == {notes.id, lint.id}
    assert ids("", include_retired=True) == {notes.id, gone.id, lint.id}
    assert ids("nothing_like_it") == set()


@pytest.mark.parametrize("fts", [True, False], ids=["fts5", "like"])
def test_search_answers_every_match_however_many(monkeypatch, fts) -> None:
    monkeypatch.setattr(decision_search, "FTS", fts and decision_search.FTS)
    entries = [
        SimpleNamespace(decision=SimpleNamespace(id=f"D-{n:05}", title="Same words", statement="s", state="in_force"))
        for n in range(1500)
    ]
    index = decision_search.Index(SimpleNamespace(entries=entries))
    assert len(index.matching("same", include_retired=False)) == 1500  # the old index stopped at its limit


def _builds(monkeypatch) -> list[object]:
    built, real = [], decision_search.Index
    monkeypatch.setattr(decision_search, "Index", lambda snapshot: (built.append(snapshot), real(snapshot))[1])
    return built


def test_a_snapshot_kept_on_one_thread_is_searched_from_another_with_its_index(shared_repo, monkeypatch) -> None:
    monkeypatch.setattr(decision_cache, "RACY_NS", 0)
    shared, notes = DataRepo(shared_repo[0]), make()
    save(shared, notes, expected_revision=None, message="m")
    decision_cache.clear()
    built = _builds(monkeypatch)
    with ThreadPoolExecutor(1) as one:
        view = one.submit(decision_store.load, shared, PROJECT).result()
    assert built == [view.snapshot]  # kept, with its index, on the loading thread
    with ThreadPoolExecutor(4) as many:
        found = list(many.map(lambda _: decision_cache.search(view.snapshot, "notes", include_retired=False), range(8)))
    assert found == [{notes.id}] * 8
    assert built == [view.snapshot]  # every thread used the kept index


def test_searches_answer_their_own_snapshot_while_a_save_publishes_the_next(shared_repo, monkeypatch) -> None:
    monkeypatch.setattr(decision_cache, "RACY_NS", 0)
    shared, notes = DataRepo(shared_repo[0]), make()
    save(shared, notes, expected_revision=None, message="m")
    old = decision_store.load(shared, PROJECT)
    stop, answers = threading.Event(), []

    def searching() -> None:
        while not stop.is_set():
            answers.append(decision_cache.search(old.snapshot, "notes", include_retired=False))

    with ThreadPoolExecutor(3) as pool:
        running = [pool.submit(searching) for _ in range(3)]
        added = make(title="Notes have tags")
        save(shared, added, expected_revision=None, message="m")
        new = decision_store.load(shared, PROJECT)
        stop.set()
        for run in running:
            run.result()
    built = _builds(monkeypatch)
    assert answers
    assert set(answers) == {frozenset({notes.id})}
    assert decision_cache.search(new.snapshot, "notes", include_retired=False) == {notes.id, added.id}
    assert built == []  # the new snapshot is the kept one
    assert decision_cache.search(old.snapshot, "notes", include_retired=False) == {notes.id}
    assert built == [old.snapshot]  # the replaced one answers from an index of its own


CHILD = """
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import decision_routes
shared = DataRepo(Path(sys.argv[1]))
app = FastAPI()
app.include_router(decision_routes.router(lambda: shared, lambda: sys.argv[2], list))
got = TestClient(app).get("/decisions", params={"text": sys.argv[3], "where": "project"}).json()
print(" ".join(sorted(d["id"] for d in got["decisions"])))
"""


def test_a_restarted_process_finds_the_committed_text_and_leaves_no_index_file(shared_repo) -> None:
    shared, notes = DataRepo(shared_repo[0]), make()
    save(shared, notes, expected_revision=None, message="m")

    def found(text: str) -> set[str]:
        args = [sys.executable, "-c", CHILD, str(shared.root), PROJECT, text]
        return set(subprocess.run(args, check=True, capture_output=True, text=True).stdout.split())  # noqa: S603

    assert (found("notes"), found("tags")) == ({notes.id}, set())
    tags = make(title="Tags are free text", statement="Any tag.")
    save(shared, tags, expected_revision=None, message="m")
    assert (found("notes"), found("tags")) == ({notes.id}, {tags.id})
    assert list(local_home.root().parent.glob("**/decisions.sqlite*")) == []
