"""A clone's store after its copy was switched: the source is kept whole and never authoritative again.

The faults land after the switch or the rename, through the same production entry points as
``test_project_home_move.py``: ``prepare_clone`` before a reboot, then ``finish_clone`` after one.
"""

import subprocess

import pytest

from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"
REAL_SYNC = fd_tree.sync


@pytest.fixture
def clone(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)  # noqa: S607
    folder = repo / ".git" / "owlbear-delivery"
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / "clone-id").write_text(f"{SOURCE_ID}\n")
    return repo, folder


def move(repo, monkeypatch):
    if not (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists():
        monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
        offline_protocol.prepare_clone(repo, gaps=lambda: ())
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return offline_protocol.finish_clone(repo, gaps=lambda: ())


def test_a_late_foreign_file_after_the_switch_stays_in_the_retained_source_and_never_reaches_the_target(
    clone, monkeypatch
):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    real_save = project_move._save  # noqa: SLF001

    def save(clone_folder, folder_fd, rec):
        real_save(clone_folder, folder_fd, rec)
        if rec["phase"] == project_move.SWITCHED:  # a writer that missed the fence adds a file after the switch
            (folder / "late.txt").write_text("late\n")

    monkeypatch.setattr(project_move, "_save", save)
    assert move(repo, monkeypatch) == target
    assert (folder / "late.txt").read_text() == "late\n"
    assert not (target / "late.txt").exists()
    assert project_home.current(repo) == target


def test_a_completed_switch_is_recognized_on_every_new_startup_and_the_retained_source_stays_whole(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    assert move(repo, monkeypatch) == target
    for _ in range(2):  # each new startup reads the receipt, never the retained source
        assert project_home.current(repo) == target
        assert Store.open(repo).root == target
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not [p for p in folder.iterdir() if p.name.startswith(".retired-")]


def test_an_unknown_quarantined_entry_in_the_retained_source_refuses_each_startup_and_stays_put(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    assert move(repo, monkeypatch) == target
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
    clone, monkeypatch
):
    """A write after the rename and before the switch is detected: the switch is refused, both copies keep bytes."""
    repo, folder = clone
    target = project_home.home(SOURCE_ID)

    def sync(dfd, entry):
        REAL_SYNC(dfd, entry)
        if entry == SOURCE_ID:
            (folder / "changes" / "c1" / "runner.log").write_text("edited before the switch\n")

    monkeypatch.setattr(fd_tree, "sync", sync)
    with pytest.raises(
        StoreError, match=r"changed after it was copied: the copy is kept at .* the switch was not recorded"
    ):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "edited before the switch\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()


def test_a_destination_swapped_for_a_link_after_the_switch_is_refused_and_the_source_is_kept(
    clone, monkeypatch, tmp_path
):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("foreign\n")
    real_save = project_move._save  # noqa: SLF001

    def save(clone_folder, folder_fd, rec):
        real_save(clone_folder, folder_fd, rec)
        if rec["phase"] == project_move.SWITCHED:  # the published copy is renamed aside and a link takes its path
            target.rename(target.parent / "aside")
            target.symlink_to(foreign, target_is_directory=True)

    monkeypatch.setattr(project_move, "_save", save)
    with pytest.raises(StoreError, match=r"is not the copy this move published"):
        move(repo, monkeypatch)
    with pytest.raises(StoreError, match=r"is not the copy this move published"):
        project_home.current(repo)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()
    assert (foreign / "keep.txt").read_text() == "foreign\n"
    assert (target.parent / "aside" / "changes" / "c1" / "runner.log").read_text() == "ran\n"
