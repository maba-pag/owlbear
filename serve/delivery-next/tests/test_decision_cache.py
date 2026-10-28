"""The kept decision snapshots (owlbear-data#16): reused while HEAD and the files stay, rebuilt on any change."""

from __future__ import annotations

import os
import shutil
import threading
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import serve
from owlbear_delivery_next.state_store import decision_cache, decision_store
from owlbear_delivery_next.state_store.decision_store import DecisionsUnavailable, save

if TYPE_CHECKING:
    from collections.abc import Callable

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT, OTHER = "shop-site", "other-site"


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


class Seeded:
    def __init__(self, shared: DataRepo) -> None:
        self.shared, self.root = shared, shared.root
        self.rule = make(title="Lint once", statement="Code is linted once.", scope=Scope.GLOBAL, project="")
        self.notes = make()
        self.other = make(project=OTHER, title="Other notes")
        for decision in (self.rule, self.notes, self.other):
            assert save(shared, decision, expected_revision=None, message="decisions: seed").published


@pytest.fixture
def seeded(shared_repo, monkeypatch) -> Seeded:
    monkeypatch.setattr(decision_cache, "RACY_NS", 0)
    return Seeded(DataRepo(shared_repo[0]))


@pytest.fixture
def parses(monkeypatch) -> list[str]:
    found: list[str] = []
    real = decision_store.snapshot

    def counted(root, project):
        found.append(project)
        return real(root, project)

    monkeypatch.setattr(decision_store, "snapshot", counted)
    return found


def outcome(shared: DataRepo) -> object:
    try:
        return decision_store.load(shared, PROJECT).snapshot
    except DecisionsUnavailable as exc:
        return str(exc)


def test_a_kept_snapshot_is_reused_until_a_save_commits(seeded, parses) -> None:
    first = decision_store.load(seeded.shared, PROJECT)
    assert decision_store.load(seeded.shared, PROJECT) is not first  # a new pairing with HEAD
    assert decision_store.load(seeded.shared, PROJECT).snapshot is first.snapshot
    assert decision_store.file_snapshot(seeded.shared, PROJECT) is first.snapshot
    assert parses == [PROJECT]

    later = make(title="Notes are short")
    assert save(seeded.shared, later, expected_revision=None, message="decisions: later").published
    after = decision_store.load(seeded.shared, PROJECT)
    assert after.commit != first.commit
    assert after.snapshot.get(later.id) is not None
    assert decision_store.load(seeded.shared, PROJECT).snapshot is after.snapshot


def _edit(s: Seeded) -> None:
    write(s.notes.model_copy(update={"title": "Notes live in one table"}), s.root / PROJECT, s.notes.revision)


def _add(s: Seeded) -> None:
    write(make(scope=Scope.GLOBAL, project="", title="Ship small"), s.root, None)


def _remove(s: Seeded) -> None:
    (s.root / PROJECT / "decisions" / f"{s.notes.id}.md").unlink()


def _stray(s: Seeded) -> None:
    (s.root / PROJECT / "decisions" / "notes.txt").write_text("not a decision\n")


def _decisions_a_file(s: Seeded) -> None:
    shutil.rmtree(s.root / PROJECT / "decisions")
    (s.root / PROJECT / "decisions").write_text("not a folder\n")


def _changes_a_file(s: Seeded) -> None:
    (s.root / PROJECT / "changes").write_text("not a folder\n")


def _new_change(s: Seeded) -> None:
    held = s.root / PROJECT / "changes" / "c1"
    write(make(scope=Scope.CHANGE, change="c1", title="Change notes"), held, None)


def _foreign_replaces(s: Seeded) -> None:
    rival = make(project=OTHER, title="Lint twice", links=(Link(type=LinkType.REPLACES, target=s.rule.id),))
    write(rival, s.root / OTHER, None)


TRANSITIONS: dict[str, Callable[[Seeded], None]] = {
    "edit": _edit, "add": _add, "remove": _remove, "stray_file": _stray, "decisions_a_file": _decisions_a_file,
    "changes_a_file": _changes_a_file, "new_change": _new_change, "foreign_replaces_global": _foreign_replaces,
}  # fmt: skip


@pytest.mark.parametrize("transition", TRANSITIONS.values(), ids=TRANSITIONS.keys())
def test_an_uncommitted_change_is_read_as_an_uncached_read_sees_it(seeded, transition) -> None:
    before = outcome(seeded.shared)
    assert outcome(seeded.shared) is before  # kept

    transition(seeded)
    after = outcome(seeded.shared)
    decision_cache.clear()

    assert after != before
    assert after == outcome(seeded.shared)


@pytest.mark.skipif(os.geteuid() == 0, reason="root lists folders whatever their mode")
def test_an_unreadable_foreign_folder_is_read_every_time_until_it_is_readable(seeded, parses) -> None:
    folder = seeded.root / OTHER / "decisions"
    kept, mode = outcome(seeded.shared), folder.stat().st_mode
    folder.chmod(0)
    try:
        unreadable = outcome(seeded.shared)
        assert unreadable.outside  # still served: another project's folder is a finding, not a refusal
        assert outcome(seeded.shared) is not unreadable
        assert len(parses) == 3
    finally:
        folder.chmod(mode)
    again = outcome(seeded.shared)  # the mode change moved the folder's times, so it is read once more
    assert again == kept
    assert outcome(seeded.shared) is again
    assert len(parses) == 4


def test_a_file_changed_while_it_is_read_is_returned_but_not_kept(seeded, parses, monkeypatch) -> None:
    real, changed = decision_store._files, []  # noqa: SLF001 - the collection the change races

    def racing(shared, project):
        seen = real(shared, project)
        if not changed:
            _edit(seeded)
            changed.append(project)
        return seen

    monkeypatch.setattr(decision_store, "_files", racing)
    raced = outcome(seeded.shared)
    assert raced.get(seeded.notes.id).decision.title == seeded.notes.title
    fresh = outcome(seeded.shared)
    assert fresh.get(seeded.notes.id).decision.title == "Notes live in one table"
    assert outcome(seeded.shared) is fresh
    assert parses == [PROJECT, PROJECT]


def test_a_file_added_and_removed_while_it_is_read_is_not_kept(seeded, parses, monkeypatch) -> None:
    real, brief = decision_store._files, make(title="Here a moment")  # noqa: SLF001 - the collection the change races

    def racing(shared, project):
        write(brief, seeded.root / PROJECT, None)
        seen = real(shared, project)
        (seeded.root / PROJECT / "decisions" / f"{brief.id}.md").unlink()  # the listing is as before; the times tell
        return seen

    monkeypatch.setattr(decision_store, "_files", racing)
    assert outcome(seeded.shared).get(brief.id) is not None
    monkeypatch.setattr(decision_store, "_files", real)
    assert outcome(seeded.shared).get(brief.id) is None
    assert parses == [PROJECT, PROJECT]


def test_a_young_file_is_kept_only_once_it_was_old_when_the_read_began(seeded, parses, monkeypatch) -> None:
    monkeypatch.setattr(decision_cache, "RACY_NS", 2_000_000_000)
    _mark, newest = decision_cache.fingerprint(seeded.root, PROJECT)
    clock = [newest + 1_000_000_000]  # the newest file is a second old: too young to keep
    monkeypatch.setattr(decision_cache, "_now", lambda: clock[0])
    assert outcome(seeded.shared) is not outcome(seeded.shared)

    real = decision_store._files  # noqa: SLF001 - the collection that stalls

    def stalled(shared, project):
        clock[0] = newest + 10_000_000_000  # the read outlasts the boundary: the file is old by now, not at the start
        return real(shared, project)

    monkeypatch.setattr(decision_store, "_files", stalled)
    stale = outcome(seeded.shared)
    monkeypatch.setattr(decision_store, "_files", real)
    assert outcome(seeded.shared) is not stale  # not kept: the cutoff was fixed before the read began
    assert outcome(seeded.shared) is outcome(seeded.shared)  # began once the file was old, so kept
    assert len(parses) == 4


def test_first_readers_on_several_threads_parse_once(seeded, parses) -> None:
    gate, seen = threading.Barrier(4), []

    def read() -> None:
        gate.wait()
        seen.append(decision_store.load(seeded.shared, PROJECT).snapshot)

    threads = [threading.Thread(target=read) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert parses == [PROJECT]
    assert all(s is seen[0] for s in seen)


def test_the_host_start_keeps_each_loaded_projects_decisions_and_says_a_view_it_could_not_read(
    seeded, parses, monkeypatch
) -> None:
    said, store = [], SimpleNamespace(shared=seeded.shared, name=PROJECT)
    monkeypatch.setattr(data_repo, "locate", lambda: seeded.shared)
    decision_cache.clear()
    serve.warm(SimpleNamespace(say=said.append, projects={"p": SimpleNamespace(store=store)}))
    assert len(said) == 1
    assert said[0].startswith("decisions of owlbear not pre-loaded: the project owlbear has no folder")
    parses.clear()
    assert decision_store.load(seeded.shared, PROJECT).snapshot.project == PROJECT
    assert parses == []
