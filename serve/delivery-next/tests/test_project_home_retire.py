"""A clone's store after its copy was switched: the source is kept whole and never authoritative again.

The faults land after the switch or the rename, through the same production entry points as
``test_project_home_move.py``: ``prepare_clone`` before a reboot, then ``finish_clone`` after one.
"""

import os

import pytest

from owlbear_delivery_next.state_store import fd_tree, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

from .test_project_home_boundary import after_copy

SOURCE_ID = "abc123"
REAL_SYNC = fd_tree.sync


def test_a_late_foreign_file_after_the_switch_stays_in_the_retained_source_and_never_reaches_the_target(
    legacy_project_clone, offline_move, monkeypatch
):
    repo, folder = legacy_project_clone
    target = project_home.home(SOURCE_ID)
    real_save = project_move._save  # noqa: SLF001

    def save(clone_folder, folder_fd, rec, **kwargs):
        real_save(clone_folder, folder_fd, rec, **kwargs)
        if rec["phase"] == project_move.SWITCHED:  # a writer that missed the fence adds a file after the switch
            (folder / "late.txt").write_text("late\n")

    monkeypatch.setattr(project_move, "_save", save)
    assert offline_move(repo) == target
    assert (folder / "late.txt").read_text() == "late\n"
    assert not (target / "late.txt").exists()
    assert project_home.current(repo) == target


def test_a_completed_switch_is_recognized_on_every_new_startup_and_the_retained_source_stays_whole(
    legacy_project_clone, offline_move, monkeypatch
):
    repo, folder = legacy_project_clone
    target = project_home.home(SOURCE_ID)
    runner = folder / "changes" / "c1" / "runner.log"
    (folder / "host.lock").write_text("")
    writers = []
    after_copy(monkeypatch, lambda: writers.append(os.open(runner, os.O_WRONLY | os.O_APPEND)))
    try:
        assert offline_move(repo) == target
        assert runner.read_text() == "ran\n"
        assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
        assert (folder / "host.lock").is_file()
        assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE
        assert not list(folder.glob(".retained-*"))
        assert not list(folder.glob(".retired-*"))
        os.write(writers[0], b"late\n")
    finally:
        for writer in writers:
            os.close(writer)
    assert runner.read_text() == "ran\nlate\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    for _ in range(2):  # each new startup reads the receipt, never the retained source
        assert project_home.current(repo) == target
        assert project_home.located(repo) == target
        assert Store.open(repo).root == target
        assert runner.read_text() == "ran\nlate\n"
        assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
        assert (folder / "host.lock").is_file()
    assert not list(folder.glob(".retained-*"))
    assert not [p for p in folder.iterdir() if p.name.startswith(".retired-")]


def test_an_unknown_quarantined_entry_in_the_retained_source_refuses_each_startup_and_stays_put(
    legacy_project_clone, offline_move
):
    repo, folder = legacy_project_clone
    target = project_home.home(SOURCE_ID)
    assert offline_move(repo) == target
    kept = folder / ".retired-deadbeef"
    kept.mkdir()
    (kept / "foreign.txt").write_text("foreign\n")
    for _ in range(2):
        with pytest.raises(StoreError, match=r"kept by an earlier failed operation \(\.retired-deadbeef\)"):
            project_home.located(repo)  # the admission every startup runs; current() only reads the receipt
        with pytest.raises(StoreError, match=r"kept by an earlier failed operation"):
            Store.open(repo)
    assert (kept / "foreign.txt").read_text() == "foreign\n"  # not adopted, not moved
    assert not (target / ".retired-deadbeef").exists()


def test_a_source_edited_after_the_rename_is_refused_before_the_switch_and_the_source_keeps_the_edit(
    legacy_project_clone, offline_move, monkeypatch
):
    """A write after the rename and before the switch is detected: the switch is refused, both copies keep bytes."""
    repo, folder = legacy_project_clone
    target = project_home.home(SOURCE_ID)

    def sync(dfd, entry):
        REAL_SYNC(dfd, entry)
        if entry == SOURCE_ID:
            (folder / "changes" / "c1" / "runner.log").write_text("edited before the switch\n")

    monkeypatch.setattr(fd_tree, "sync", sync)
    with pytest.raises(
        StoreError, match=r"changed after it was copied: the copy is kept at .* the switch was not recorded"
    ):
        offline_move(repo)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "edited before the switch\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()


def test_a_destination_swapped_for_a_link_after_the_switch_is_refused_and_the_source_is_kept(
    legacy_project_clone, offline_move, monkeypatch, tmp_path
):
    repo, folder = legacy_project_clone
    target = project_home.home(SOURCE_ID)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("foreign\n")
    real_save = project_move._save  # noqa: SLF001

    def save(clone_folder, folder_fd, rec, **kwargs):
        real_save(clone_folder, folder_fd, rec, **kwargs)
        if rec["phase"] == project_move.SWITCHED:  # the published copy is renamed aside and a link takes its path
            target.rename(target.parent / "aside")
            target.symlink_to(foreign, target_is_directory=True)

    monkeypatch.setattr(project_move, "_save", save)
    with pytest.raises(StoreError, match=r"is not the copy this move published"):
        offline_move(repo)
    with pytest.raises(StoreError, match=r"is not the copy this move published"):
        project_home.current(repo)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()
    assert (foreign / "keep.txt").read_text() == "foreign\n"
    assert (target.parent / "aside" / "changes" / "c1" / "runner.log").read_text() == "ran\n"
