"""Decisions in the shared data repository: load, save receipts, two checkouts at once (TD-419 slice 3)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, snapshot, write
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.state_store import (
    decision_actions,
    decision_batch,
    decision_index,
    decision_store,
    decision_sync,
)
from owlbear_delivery_next.state_store.decision_store import (
    READ,
    SET_UP_PROJECT,
    DecisionsUnavailable,
    load,
    refresh,
    save,
)

if TYPE_CHECKING:
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def checkout(path: Path, remote: Path | None = None) -> DataRepo:
    """A data repository checkout with one commit: a clone of *remote*, or a repository with no remote."""
    if remote is None:
        git(path.parent, "init", "-q", "-b", "main", str(path))
    else:
        git(path.parent, "clone", "-q", str(remote), str(path))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(path, "config", key, value)
    if remote is None:
        git(path, "commit", "-q", "--allow-empty", "-m", "start")
    return DataRepo(path)


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def replacing(old: Decision, **changes) -> Decision:
    return make(links=(Link(type=LinkType.REPLACES, target=old.id),), **changes)


def flagged(decision: Decision) -> Decision:
    return decision.model_copy(update={"conflict": True})


def set_up(shared: DataRepo) -> DataRepo:
    shared.claim(PROJECT, "github.com/acme/shop-site")
    return shared


@pytest.fixture
def shared(shared_repo) -> DataRepo:
    return DataRepo(shared_repo[0])


def held(shared: DataRepo, remote: Path, path: Path) -> tuple[Decision, DataRepo]:
    """A published decision, and a second checkout of the remote cloned after it."""
    decision = make(rationale="First line.\n\nSecond line.\n\nThird line.")
    assert save(shared, decision, expected_revision=None, message="decisions: held").published
    return decision, checkout(path, remote)


def test_no_data_repository_stops_instead_of_giving_no_decisions() -> None:
    with pytest.raises(DecisionsUnavailable, match="no shared data repository"):
        load(None, PROJECT)
    with pytest.raises(DecisionsUnavailable, match="no shared data repository"):
        save(None, make(), expected_revision=None, message="m")
    with pytest.raises(DecisionsUnavailable, match="no shared data repository"):
        decision_index.search("notes", PROJECT)


@pytest.mark.parametrize("where", ["decisions", f"{PROJECT}/decisions", PROJECT])
def test_a_decisions_path_that_is_a_file_stops_loading(shared, where) -> None:
    if where != PROJECT:
        set_up(shared)
    (shared.root / where).write_text("not a folder\n")
    with pytest.raises(DecisionsUnavailable, match="not a folder") as raised:
        load(shared, PROJECT)
    assert raised.value.action == READ


def test_a_project_without_its_folder_stops_loading_one_without_decisions_has_none(shared) -> None:
    with pytest.raises(DecisionsUnavailable, match="has no folder") as raised:
        load(shared, PROJECT)
    assert raised.value.action == SET_UP_PROJECT
    assert load(set_up(shared), PROJECT).snapshot.entries == ()


def test_a_checkout_git_cannot_read_stops_loading(shared, tmp_path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(DecisionsUnavailable, match="Git cannot read"):
        load(DataRepo(plain), PROJECT)
    (shared.root / ".git" / "HEAD").write_text("garbage\n")
    with pytest.raises(DecisionsUnavailable, match="Git cannot read") as raised:
        load(shared, PROJECT)
    assert raised.value.stop(AT).kind == "state"


@pytest.mark.parametrize("locked", [f"{PROJECT}/decisions", PROJECT])
def test_an_unreadable_decisions_folder_stops_loading(shared, locked) -> None:
    assert save(shared, make(), expected_revision=None, message="m").saved
    folder = shared.root / locked
    folder.chmod(0)
    try:
        with pytest.raises(DecisionsUnavailable, match="cannot be read"):
            load(shared, PROJECT)
    finally:
        folder.chmod(0o755)


@pytest.mark.parametrize("broken", ["invalid", "unreadable"])
def test_an_unusable_decision_file_stops_loading_and_searching(indexed, broken) -> None:
    kept, bad = make(), make()
    for decision in (kept, bad):
        save(indexed, decision, expected_revision=None, message="m")
    path = indexed.root / PROJECT / "decisions" / f"{bad.id}.md"
    if broken == "invalid":
        path.write_text("nothing\n")
    else:
        path.chmod(0)
    try:
        with pytest.raises(DecisionsUnavailable, match=f"{bad.id}.md: ") as raised:
            load(indexed, PROJECT)
        assert raised.value.action == READ
        with pytest.raises(DecisionsUnavailable, match=f"{bad.id}.md: "):
            decision_index.search("notes", PROJECT)
        seen = snapshot(indexed.root, PROJECT)  # the diagnostic view keeps what it could not use
        assert [e.decision.id for e in seen.entries] == [kept.id]
        assert ([f.rule for f in seen.findings], seen.complete) == (["schema"], False)
        assert load(indexed, "").snapshot.complete  # this project's file does not stop the Global view
    finally:
        path.chmod(0o644)


def test_a_save_reports_saved_committed_published_and_active(shared_repo, shared) -> None:
    decision = make()
    said = save(shared, decision, expected_revision=None, message="decisions: notes")
    assert (said.saved, said.committed, said.published, said.active, said.conflict) == (True, True, True, True, False)
    assert (said.revision, said.notice) == (decision.revision, "")
    assert said.commit == git(shared.root, "rev-parse", "HEAD") == git(shared_repo[1], "rev-parse", "main")

    draft = make(state=State.DRAFT)
    said = save(shared, draft, expected_revision=None, message="decisions: a draft")
    assert (said.saved, said.published, said.active) == (True, True, False)


def test_a_failed_push_is_saved_and_committed_but_not_published(tmp_path) -> None:
    local = checkout(tmp_path / "local")
    said = save(local, make(), expected_revision=None, message="decisions: notes")
    assert (said.saved, said.committed, said.published, said.active) == (True, True, False, True)
    assert "push" in said.notice


def test_a_stale_expected_revision_is_refused_without_writing(shared) -> None:
    decision = make()
    save(shared, decision, expected_revision=None, message="m")
    path, head = shared.root / PROJECT / "decisions" / f"{decision.id}.md", git(shared.root, "rev-parse", "HEAD")
    text = path.read_text()
    withdrawn = decision.model_copy(update={"state": State.WITHDRAWN})
    for expected in ("0" * 64, None):
        said = save(shared, withdrawn, expected_revision=expected, message="m")
        assert (said.saved, said.committed, said.published, said.active) == (False, False, False, False)
        assert decision.revision in said.notice
    assert path.read_text() == text
    assert git(shared.root, "rev-parse", "HEAD") == head
    said = save(shared, withdrawn, expected_revision=decision.revision, message="decisions: withdrawn")
    assert (said.saved, said.published, said.active) == (True, True, False)


EDITED = "First line.\n\nSecond line.\n\nThird line, edited."


def test_an_expected_revision_is_checked_against_the_remotes_file(shared_repo, shared, tmp_path) -> None:
    decision, second = held(shared, shared_repo[1], tmp_path / "second")
    withdrawn = decision.model_copy(update={"state": State.WITHDRAWN})
    assert save(shared, withdrawn, expected_revision=decision.revision, message="decisions: withdrawn").published

    edited = decision.model_copy(update={"rationale": EDITED})
    said = save(second, edited, expected_revision=decision.revision, message="decisions: edited")

    assert (said.saved, said.committed, said.published, said.active) == (False, False, False, False)
    assert withdrawn.revision in said.notice
    assert git(second.root, "rev-parse", "HEAD") == git(shared_repo[1], "rev-parse", "main")
    assert load(second, PROJECT).snapshot.get(decision.id).decision == withdrawn


def test_a_save_the_remote_overtook_is_taken_back_never_merged(shared_repo, shared, tmp_path, monkeypatch) -> None:
    decision, second = held(shared, shared_repo[1], tmp_path / "second")
    withdrawn = decision.model_copy(update={"state": State.WITHDRAWN})
    assert save(shared, withdrawn, expected_revision=decision.revision, message="decisions: withdrawn").published
    monkeypatch.setattr(decision_sync, "catch_up", lambda *_: "")  # the remote moves after the check

    edited = decision.model_copy(update={"rationale": EDITED})
    said = save(second, edited, expected_revision=decision.revision, message="decisions: edited")

    assert (said.saved, said.committed, said.published, said.active) == (False, False, False, False)
    assert f"changed {decision.id} first" in said.notice
    # Accepted policy: the stale commit stays unpublished in Git, nothing is taken back, and the batch is interrupted.
    assert git(second.root, "log", "-1", "--format=%s") == "decisions: edited"
    assert git(second.root, "rev-parse", "HEAD") != git(shared_repo[1], "rev-parse", "main")
    assert git(second.root, "status", "--porcelain") == ""
    assert decision_batch.pending(second) is not None
    with pytest.raises(DecisionsUnavailable):  # authority reads are refused while the batch is in flight
        load(second, PROJECT)


@pytest.mark.parametrize("moved", ["before", "during"])
def test_a_save_of_several_files_writes_all_or_none(shared_repo, shared, tmp_path, monkeypatch, moved) -> None:
    decision, second = held(shared, shared_repo[1], tmp_path / "second")
    withdrawn = decision.model_copy(update={"state": State.WITHDRAWN})
    assert save(shared, withdrawn, expected_revision=decision.revision, message="decisions: withdrawn").published
    if moved == "during":  # the remote moves after the check: the push is rejected and the commit taken back whole
        monkeypatch.setattr(decision_sync, "catch_up", lambda *_: "")
    successor = replacing(decision)
    retired = decision.model_copy(update={"state": State.REPLACED})

    said = decision_store.save_all(
        second, [(successor, None), (retired, decision.revision)], message="decisions: replace"
    )

    assert [(r.id, r.saved, r.committed, r.published) for r in said] == [
        (successor.id, False, False, False), (decision.id, False, False, False)]  # fmt: skip
    assert git(second.root, "status", "--porcelain", "--untracked-files=all") == ""
    if moved == "before":
        assert git(second.root, "rev-parse", "HEAD") == git(shared_repo[1], "rev-parse", "main")
        seen = load(second, PROJECT).snapshot
        assert [e.decision for e in seen.entries] == [withdrawn]  # no successor, the remote's version kept
    else:  # accepted policy: the local commit stays unpublished and HEAD is not restored behind the owner
        assert git(second.root, "rev-parse", "HEAD") != git(shared_repo[1], "rev-parse", "main")
        pending = decision_batch.pending(second)
        assert pending is not None
        assert set(pending.ids) == {successor.id, decision.id}  # all before/after evidence is retained
        with pytest.raises(DecisionsUnavailable):  # no partial settled authority is read
            load(second, PROJECT)


def test_a_replacement_whose_predecessor_changed_remotely_writes_neither_file(shared_repo, shared, tmp_path) -> None:
    decision, second = held(shared, shared_repo[1], tmp_path / "second")
    edited = decision.model_copy(update={"rationale": EDITED})
    assert save(shared, edited, expected_revision=decision.revision, message="decisions: edited").published
    remote = git(shared_repo[1], "rev-parse", "main")

    said = decision_actions.replace(second, PROJECT, decision.id, decision.revision, title="", statement="Postgres.",
                                    rationale="", reason="It grew.", redecided=False)  # fmt: skip

    assert [r.saved for r in said] == [False, False]
    assert git(shared_repo[1], "rev-parse", "main") == remote  # nothing published
    assert [e.decision for e in load(second, PROJECT).snapshot.entries] == [edited]  # no successor, edit kept
    assert git(second.root, "status", "--porcelain", "--untracked-files=all") == ""


def test_a_write_that_fails_midway_puts_back_every_file_of_the_batch(shared, monkeypatch) -> None:
    decision = make()
    assert save(set_up(shared), decision, expected_revision=None, message="m").published
    real, calls = decision_store.write, []

    def failing(d, folder, expected, **fence):
        calls.append(d.id)
        if len(calls) == 2:
            real(d, folder, expected, **fence)  # the rename lands, then the fsync fails
            raise OSError(5, "I/O error")
        return real(d, folder, expected, **fence)

    monkeypatch.setattr(decision_store, "write", failing)
    successor, retired = replacing(decision), decision.model_copy(update={"state": State.REPLACED})
    with pytest.raises(DecisionsUnavailable):
        decision_store.save_all(shared, [(successor, None), (retired, decision.revision)], message="m")

    assert [e.decision for e in load(shared, PROJECT).snapshot.entries] == [decision]  # neither change stays
    assert git(shared.root, "status", "--porcelain", "--untracked-files=all", "--", f"{PROJECT}/decisions") == ""


def test_a_competitor_outside_the_saving_view_is_flagged_and_resolved(shared) -> None:
    source = make(state=State.REPLACED)
    rival = replacing(source, title="Narrow")
    set_up(shared)
    for decision in (source, rival):
        assert save(shared, decision, expected_revision=None, message="m").published
    promoted = make(scope=Scope.GLOBAL, project="", title="Wide", links=(Link(type=LinkType.PROMOTED_FROM,
                                                                              target=source.id),))  # fmt: skip

    said = save(shared, promoted, expected_revision=None, message="decisions: promoted")  # a Global-only view

    assert (said.conflict, said.active) == (True, False)
    assert load(shared, PROJECT).snapshot.get(rival.id).decision.conflict  # flagged though outside that view
    view = load(shared, "")
    assert [d.id for d in decision_actions.rivals(view, promoted, shared)] == [rival.id]


def test_two_promotions_of_one_source_are_a_conflict_the_owner_resolves(shared) -> None:
    source = make(state=State.REPLACED)
    promoted = (Link(type=LinkType.PROMOTED_FROM, target=source.id),)
    first, second = (make(scope=Scope.GLOBAL, project="", title=t, links=promoted) for t in ("Wide", "Wider"))
    set_up(shared)
    for decision in (source, first):
        assert save(shared, decision, expected_revision=None, message="m").published

    said = save(shared, second, expected_revision=None, message="decisions: a second promotion")
    view = load(shared, PROJECT)
    rivals = decision_actions.rivals(view, view.snapshot.get(second.id).decision)
    shown = {d.id: d.revision for d in (view.snapshot.get(second.id).decision, *rivals)}
    kept = decision_actions.keep(shared, PROJECT, second.id, shown, reason="Wider reads better.")

    assert (said.saved, said.conflict, said.active) == (True, True, False)
    assert [d.id for d in rivals] == [first.id]
    assert [r.saved for r in kept] == [True, True]
    seen = load(shared, PROJECT).snapshot
    assert (seen.get(first.id).decision.state, seen.active(second.id)) == (State.WITHDRAWN, True)


def test_the_receipt_is_read_back_under_the_lock(shared, monkeypatch) -> None:
    real, held_lock = decision_store._receipt, []  # noqa: SLF001 - spied on

    def spy(repo, *args, **options):
        with pytest.raises(DataRepoError), repo.locked(wait=0):
            pass
        held_lock.append(True)
        return real(repo, *args, **options)

    monkeypatch.setattr(decision_store, "_receipt", spy)
    assert save(shared, make(), expected_revision=None, message="m").published
    assert held_lock == [True]


@pytest.mark.parametrize("race", [False, True])
def test_two_checkouts_replacing_one_decision_both_end_flagged_as_a_conflict(
    shared_repo, shared, tmp_path, monkeypatch, race
) -> None:
    remote = shared_repo[1]
    old, second = held(shared, remote, tmp_path / "second")
    one, two = replacing(old, title="Notes in one table"), replacing(old, title="Notes in two tables")

    first_said = save(shared, one, expected_revision=None, message="decisions: one")
    with monkeypatch.context() as patched:
        if race:  # the second checkout misses the first one's push until its own push is rejected
            patched.setattr(decision_sync, "catch_up", lambda *_: "")
        second_said = save(second, two, expected_revision=None, message="decisions: two")

    assert (first_said.active, first_said.conflict) == (True, False)
    assert (second_said.saved, second_said.committed, second_said.published) == (True, True, True)
    assert (second_said.active, second_said.conflict, second_said.revision) == (False, True, flagged(two).revision)
    assert second_said.commit == git(remote, "rev-parse", "main")
    assert "conflict" in second_said.notice
    subjects = git(remote, "log", "--format=%s", "main").splitlines()
    assert subjects[:3] == [f"decisions: conflict on {', '.join(sorted([one.id, two.id]))}", "decisions: two",
                            "decisions: one"]  # fmt: skip
    assert load(shared, PROJECT).snapshot.findings == ()  # the first checkout has not pulled yet
    assert refresh(shared) == ""
    for repo in (shared, second):
        seen = load(repo, PROJECT).snapshot
        assert {f.rule for f in seen.findings} == {"two-successors"}
        assert {e.decision.id for e in seen.entries if e.decision.conflict} == {one.id, two.id}
        assert not seen.active(one.id)
        assert not seen.active(two.id)

    withdrawn = flagged(one).model_copy(update={"state": State.WITHDRAWN})
    said = save(shared, withdrawn, expected_revision=flagged(one).revision, message="decisions: one withdrawn")
    assert (said.saved, said.published, said.active) == (True, True, False)
    seen = load(shared, PROJECT).snapshot
    assert seen.findings == ()
    assert not seen.active(two.id)  # its flag holds until the owner clears it


def test_conflict_flags_reach_a_competitor_that_arrives_while_they_publish(
    shared_repo, shared, tmp_path, monkeypatch
) -> None:
    old, third = held(shared, shared_repo[1], tmp_path / "third")
    other = make()
    unrelated = [other, replacing(other), replacing(other)]  # a conflict of its own, written past `save`
    for decision in unrelated:
        write(decision, shared.root / PROJECT)
    git(shared.root, "add", "-A")
    git(shared.root, "commit", "-qm", "decisions: unrelated")
    one, two, three = (replacing(old, title=f"Notes in {n} tables") for n in ("one", "two", "three"))
    assert save(shared, one, expected_revision=None, message="decisions: one").active
    real, arrived = decision_sync.publish, []

    def racing(repo, paths, message, until, head):
        if message.startswith("decisions: conflict") and not arrived:
            arrived.append(three)
            git(third.root, "pull", "-q", "--rebase")
            write(three, third.root / PROJECT)
            git(third.root, "add", "-A")
            git(third.root, "commit", "-qm", "decisions: three")
            git(third.root, "push", "-q")
        return real(repo, paths, message, until, head)

    monkeypatch.setattr(decision_sync, "publish", racing)
    said = save(shared, two, expected_revision=None, message="decisions: two")

    assert arrived
    assert (said.published, said.conflict, said.active) == (True, True, False)
    assert refresh(third) == ""
    seen = load(third, PROJECT).snapshot
    assert {e.decision.id for e in seen.entries if e.decision.conflict} == {one.id, two.id, three.id}
    assert not any(seen.get(d.id).decision.conflict for d in unrelated)  # flags only what the save involves
    assert all(seen.get(d.id).decision.state is State.IN_FORCE for d in (one, two, three))


def test_a_conflict_left_unflagged_fails_closed(shared, monkeypatch) -> None:
    old = make()
    for decision in (old, replacing(old)):
        save(shared, decision, expected_revision=None, message="m")
    monkeypatch.setattr(decision_store, "ROUNDS", 0)
    said = save(shared, replacing(old), expected_revision=None, message="m")
    assert (said.saved, said.published, said.active, said.conflict) == (True, True, False, True)
    assert "still unflagged" in said.notice


def test_an_ambiguous_conflict_flag_publish_stays_interrupted(shared, monkeypatch) -> None:
    old = make()
    for decision in (old, replacing(old)):
        save(shared, decision, expected_revision=None, message="m")
    real_publish = decision_sync.publish

    def unknown_flags(repo, paths, message, until, head):
        if message.startswith("decisions: conflict on"):
            return decision_sync.Sent(ambiguous=True, notice="not provably its own commit")
        return real_publish(repo, paths, message, until, head)

    monkeypatch.setattr(decision_sync, "publish", unknown_flags)
    said = save(shared, replacing(old), expected_revision=None, message="m")
    assert "interrupted batch" in said.notice
    assert decision_batch.pending(shared) is not None
    with pytest.raises(DecisionsUnavailable, match="interrupted decision batch"):
        load(shared, PROJECT)


def test_refresh_reports_uncommitted_work_instead_of_pulling(shared) -> None:
    decision = make()
    save(shared, decision, expected_revision=None, message="m")
    (shared.root / PROJECT / "decisions" / f"{decision.id}.md").write_text("edited\n")
    assert refresh(shared).startswith("not refreshed: 1 uncommitted file(s)")


@pytest.fixture
def indexed(shared, monkeypatch) -> DataRepo:
    monkeypatch.setenv("OWLBEAR_DATA", str(shared.root))
    return shared


def test_a_commit_a_hook_added_is_never_taken_back(shared_repo, shared, tmp_path, monkeypatch) -> None:
    decision, second = held(shared, shared_repo[1], tmp_path / "second")
    withdrawn = decision.model_copy(update={"state": State.WITHDRAWN})
    assert save(shared, withdrawn, expected_revision=decision.revision, message="decisions: withdrawn").published
    hook = second.root / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\n[ -f .git/hooked ] && exit 0\ntouch .git/hooked\ngit commit -q --allow-empty -m hook\n")
    hook.chmod(0o755)
    monkeypatch.setattr(decision_sync, "catch_up", lambda *_: "")

    edited = decision.model_copy(update={"rationale": EDITED})
    said = save(second, edited, expected_revision=decision.revision, message="decisions: edited")

    assert (said.saved and said.published, "not provably its own" in said.notice) == (False, True), said.notice
    assert git(second.root, "log", "-2", "--format=%s").splitlines() == ["hook", "decisions: edited"]


def test_no_rebase_of_the_checkout_combines_two_versions_of_a_decision(shared_repo, shared, tmp_path) -> None:
    decision, second = held(shared, shared_repo[1], tmp_path / "second")
    path = second.root / PROJECT / "decisions" / f"{decision.id}.md"
    edited = decision.model_copy(update={"rationale": EDITED})
    with second.locked():
        write(edited, second.root / PROJECT, expected_revision=decision.revision)
        assert second.commit(path, "decisions: edited offline") == ""  # committed here, never pushed
    withdrawn = decision.model_copy(update={"state": State.WITHDRAWN})
    assert save(shared, withdrawn, expected_revision=decision.revision, message="decisions: withdrawn").published

    settings = second.root / PROJECT / "config.json"
    settings.write_text("{}\n")
    with second.locked():
        notice = second.publish(settings, "settings: a save of something else")

    assert "could not be merged" in notice
    rel = path.relative_to(second.root).as_posix()
    assert decision_sync.revision_at(second, "HEAD", rel, 5) == decision_sync.revision_at(shared, "HEAD", rel, 5)
    assert decision_sync.revision_at(second, "HEAD", rel, 5) != edited.revision
    assert (second.root / ".git" / "rebase-merge").is_dir()


@pytest.mark.parametrize("broken", ["file", "symlink"])
def test_a_changes_path_that_is_not_a_real_folder_stops_loading(shared, tmp_path, broken) -> None:
    set_up(shared)
    changes = shared.root / PROJECT / "changes"
    if broken == "file":
        changes.write_text("not a folder\n")
    else:
        elsewhere = tmp_path / "elsewhere" / "decisions"
        elsewhere.mkdir(parents=True)
        changes.mkdir()
        (changes / "20261021-090000-notes").symlink_to(elsewhere.parent)
    with pytest.raises(DecisionsUnavailable):
        load(shared, PROJECT)


def test_a_data_repository_path_with_spaces_loads_and_saves(tmp_path) -> None:
    local = set_up(checkout(tmp_path / "owlbear data"))
    said = save(local, make(), expected_revision=None, message="decisions: notes")
    assert (said.saved, said.committed) == (True, True)
    assert len(load(local, PROJECT).snapshot.entries) == 1


def test_a_lock_that_cannot_be_opened_makes_refresh_unavailable_not_a_crash(shared, monkeypatch) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(DataRepo, "locked", broken)
    with pytest.raises(DecisionsUnavailable, match="Permission denied"):
        refresh(set_up(shared))
