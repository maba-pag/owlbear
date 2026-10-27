"""Boundary regressions for the cross-volume move: the names it publishes, removes and locks.

Each test reproduces one reviewed defect with a synthetic filesystem fault at the point where it can hurt, and asserts
that the refusal is explicit and that nothing unknown was overwritten or deleted.
"""

import errno
import os
import subprocess

import pytest

from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"
REAL_SAVE, REAL_SYNC, REAL_OWNED = project_move._save, fd_tree.sync, project_move._owned  # noqa: SLF001


def after_copy(monkeypatch, action):
    """Run *action* once the staging copy is complete and before its digests are checked."""
    done = []

    def owned(pfd, stage_name, rec, *, complete):
        REAL_OWNED(pfd, stage_name, rec, complete=complete)
        if complete and not done:
            done.append(stage_name)
            action()

    monkeypatch.setattr(project_move, "_owned", owned)


class CrashError(OSError):
    """An interruption part-way through a cross-volume move."""


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


def heal(monkeypatch):
    """Restore the real seams; an undo would also drop the test's HOME from conftest."""
    monkeypatch.setattr(project_move, "_save", REAL_SAVE)
    monkeypatch.setattr(fd_tree, "sync", REAL_SYNC)
    monkeypatch.setattr(project_move, "_owned", REAL_OWNED)


def test_the_published_name_is_durable_in_its_parent_before_the_switch_is_recorded(clone, monkeypatch):
    repo, _ = clone
    target = project_home.home(SOURCE_ID)
    events = []
    real_fsync = os.fsync

    def fsync(fd):
        st = os.fstat(fd)
        events.append(("sync", st.st_dev, st.st_ino))
        real_fsync(fd)

    def save(folder, folder_fd, rec):
        if rec["phase"] == project_move.SWITCHED:
            events.append(("switch",))
        REAL_SAVE(folder, folder_fd, rec)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(project_move, "_save", save)
    assert move(repo, monkeypatch) == target
    before = events[: events.index(("switch",))]
    for folder in (target.parent, target.parent.parent):  # the projects folder and the folder that holds it
        st = folder.stat()
        assert ("sync", st.st_dev, st.st_ino) in before, f"{folder} was not synced before the switch"


def test_an_ancestor_swapped_after_the_switch_refuses_and_keeps_the_source_and_record(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    aside = target.parent.parent / "projects-aside"

    def save(clone_folder, folder_fd, rec):
        REAL_SAVE(clone_folder, folder_fd, rec)
        if rec["phase"] == project_move.SWITCHED:
            target.parent.rename(aside)  # the path that named the published copy now names another folder
            target.parent.mkdir()

    monkeypatch.setattr(project_move, "_save", save)
    with pytest.raises(StoreError, match=r"is not the copy this move published"):
        move(repo, monkeypatch)
    with pytest.raises(StoreError, match=r"is not the copy this move published"):
        project_home.current(repo)  # the path still names another folder: nothing is admitted
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()
    assert (aside / SOURCE_ID / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    heal(monkeypatch)
    target.parent.rmdir()
    aside.rename(target.parent)
    assert move(repo, monkeypatch) == target


def interrupted_copy(monkeypatch):
    """Stop a move after the first entry's copy, while the stage holds an owned partial of it."""

    def sync(dfd, entry):
        if entry == "changes":
            msg = "simulated crash"
            raise CrashError(msg)
        REAL_SYNC(dfd, entry)

    monkeypatch.setattr(fd_tree, "sync", sync)


def test_a_foreign_file_in_an_interrupted_staging_copy_is_refused_and_stays_where_it_is(clone, monkeypatch):
    """A pending staging entry that is not a prefix of its source is foreign: refused in place, never adopted."""
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    stage = target.parent / f".{SOURCE_ID}.staging"
    interrupted_copy(monkeypatch)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    foreign = stage / "changes" / "c1" / "foreign.txt"
    foreign.write_text("foreign\n")
    heal(monkeypatch)
    with pytest.raises(StoreError, match=r"is not from a move OwlBear recorded: nothing was moved"):
        move(repo, monkeypatch)
    assert foreign.read_text() == "foreign\n"  # still at the stage path, with its bytes
    assert stage.exists()
    assert not target.exists()
    assert not [p for p in target.parent.iterdir() if p.name.startswith(".retired-")]
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"  # the source is whole


def test_an_owned_partial_of_an_interrupted_staging_copy_resumes_and_is_kept_not_reused(clone, monkeypatch):
    """A pending entry that is a prefix of its source is our own partial copy: kept aside and copied again."""
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    stage = target.parent / f".{SOURCE_ID}.staging"
    interrupted_copy(monkeypatch)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    assert (stage / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    heal(monkeypatch)
    assert move(repo, monkeypatch) == target
    kept = [p for p in target.parent.iterdir() if p.name.startswith(".retired-")]
    assert len(kept) == 1
    assert not stage.exists()
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_file_inserted_after_the_copy_is_refused_and_kept_in_the_source(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    planted = folder / "changes" / "c1" / "unknown.txt"
    after_copy(monkeypatch, lambda: planted.write_text("unknown\n"))
    with pytest.raises(StoreError, match=r"changed while it was copied"):
        move(repo, monkeypatch)
    assert planted.read_text() == "unknown\n"
    assert not (target / "changes" / "c1" / "unknown.txt").exists()
    assert not target.exists()


def test_a_hard_link_at_the_temporary_name_is_never_written_through(clone, monkeypatch, tmp_path):
    repo, _ = clone
    target = project_home.home(SOURCE_ID)
    foreign = tmp_path / "foreign.txt"
    foreign.write_text("foreign\n")
    os.link(foreign, clone[1] / ".tmp-move.json")
    assert move(repo, monkeypatch) == target
    assert foreign.read_text() == "foreign\n"


def test_a_lock_file_replaced_after_the_switch_is_kept_and_the_replacement_untouched(clone, monkeypatch):
    repo, folder = clone
    (folder / "host.lock").write_text("")

    def sync(dfd, entry):
        REAL_SYNC(dfd, entry)
        if entry == SOURCE_ID:  # after the switch, a foreign file takes the name of the lock this open holds
            (folder / "host.lock").rename(folder.parent / "host.lock.aside")
            (folder / "host.lock").write_text("foreign\n")

    monkeypatch.setattr(fd_tree, "sync", sync)
    assert move(repo, monkeypatch) == project_home.home(SOURCE_ID)
    assert (folder / "host.lock").read_text() == "foreign\n"


def test_bytes_edited_after_the_copy_are_refused_and_kept_in_the_source(clone, monkeypatch):
    repo, folder = clone
    after_copy(monkeypatch, lambda: (folder / "changes" / "c1" / "runner.log").write_text("ran\nedited\n"))
    with pytest.raises(StoreError, match=r"changed while it was copied"):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\nedited\n"
    assert not project_home.home(SOURCE_ID).exists()


def test_a_writer_holding_the_source_after_the_switch_writes_into_the_kept_source(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    writers = []
    after_copy(
        monkeypatch,
        lambda: writers.append(os.open(folder / "changes" / "c1" / "runner.log", os.O_WRONLY | os.O_APPEND)),
    )
    assert move(repo, monkeypatch) == target
    os.write(writers[0], b"late\n")  # an fd held across the switch still reaches the source file
    os.close(writers[0])
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\nlate\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert project_home.current(repo) == target
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_resumed_move_syncs_the_published_name_before_it_switches(clone, monkeypatch):
    repo, _ = clone
    target = project_home.home(SOURCE_ID)
    events, failed = [], []
    real_fsync = os.fsync

    def fsync(fd):
        st = os.fstat(fd)
        if not failed and target.parent.exists() and (st.st_dev, st.st_ino) == _id(target.parent):
            failed.append(True)  # the first sync of the parent, after the rename, fails
            msg = "the parent folder could not be synced"
            raise CrashError(msg)
        events.append(("sync", st.st_dev, st.st_ino))
        real_fsync(fd)

    def save(folder, folder_fd, rec):
        if rec["phase"] == project_move.SWITCHED:
            events.append(("switch",))
        REAL_SAVE(folder, folder_fd, rec)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(project_move, "_save", save)
    with pytest.raises(StoreError, match=r"was not made durable"):
        move(repo, monkeypatch)
    assert move(repo, monkeypatch) == target
    before = events[: events.index(("switch",))]
    for folder in (target.parent, target.parent.parent):
        assert ("sync", *_id(folder)) in before, f"{folder} was not synced before the switch"


def _id(path):
    st = path.stat()
    return st.st_dev, st.st_ino


def test_a_failed_metadata_write_never_deletes_a_foreign_entry_at_its_temporary_name(tmp_path, monkeypatch):
    folder = tmp_path / "folder"
    folder.mkdir()
    dfd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    real_rename, swapped = os.rename, []

    def rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        if not swapped and str(src).startswith(".tmp-"):
            swapped.append(src)
            real_rename(src, "moved-aside", src_dir_fd=src_dir_fd, dst_dir_fd=src_dir_fd)  # ours moves aside
            (folder / src).write_text("foreign\n")  # a foreign entry takes the temporary name
            raise OSError(errno.EIO, "injected rename failure")
        return real_rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(os, "rename", rename)
    try:
        with pytest.raises(StoreError, match=r"kept"):
            fd_tree.write_at(dfd, "meta.json", "{}\n")
    finally:
        os.close(dfd)
    assert [p.read_text() for p in folder.iterdir() if p.name.startswith(".retired-")] == ["foreign\n"]


def test_a_quarantined_entry_refuses_the_next_start_and_is_never_adopted_or_deleted(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    kept = folder / f"{fd_tree.QUARANTINE}0123456789abcdef"  # what a failed metadata write leaves behind
    kept.write_text("foreign\n")
    with pytest.raises(StoreError, match=r"kept by an earlier failed operation"):
        move(repo, monkeypatch)
    assert kept.read_text() == "foreign\n"
    assert not target.exists()
    assert not (folder / project_move.MOVE_RECORD).exists()
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_failed_metadata_write_keeps_its_own_temporary_entry_under_a_retired_name(tmp_path, monkeypatch):
    folder = tmp_path / "folder"
    folder.mkdir()
    dfd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    real_rename, failed = os.rename, []

    def rename(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        if not failed and str(src).startswith(".tmp-"):
            failed.append(src)
            raise OSError(errno.EIO, "injected rename failure")
        return real_rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(os, "rename", rename)
    try:
        with pytest.raises(StoreError, match=r"kept"):
            fd_tree.write_at(dfd, "meta.json", "{}\n")
    finally:
        os.close(dfd)
    kept = list(folder.iterdir())
    assert [p.name.startswith(fd_tree.QUARANTINE) for p in kept] == [True]
    assert [p.read_text() for p in kept] == ["{}\n"]


def test_a_lock_file_is_retained_and_never_unlinked_by_a_move(clone, monkeypatch):
    repo, folder = clone
    (folder / "host.lock").write_text("")
    assert move(repo, monkeypatch) == project_home.home(SOURCE_ID)
    assert (folder / "host.lock").is_file()


def test_an_unedited_source_entry_stays_whole_in_place_after_the_switch(clone, monkeypatch):
    repo, folder = clone
    assert move(repo, monkeypatch) == project_home.home(SOURCE_ID)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not list(folder.glob(".retained-*"))
    assert (project_home.home(SOURCE_ID) / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_source_leaf_replaced_after_its_copy_is_refused_and_the_replacement_is_kept_in_place(clone, monkeypatch):
    repo, folder = clone

    def swap():
        (folder / "changes" / "c1" / "runner.log").unlink()
        (folder / "changes" / "c1" / "runner.log").write_text("foreign\n")

    after_copy(monkeypatch, swap)
    with pytest.raises(StoreError, match=r"changed while it was copied"):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "foreign\n"
    assert not project_home.home(SOURCE_ID).exists()
