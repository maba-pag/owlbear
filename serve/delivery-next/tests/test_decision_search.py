"""Decision search over a snapshot (owlbear-data#16): words, prefixes, retired decisions, an uncapped answer."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_search, decision_store
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
