"""Writes that reach the source around the switch, and a failed prejournal write: the source is kept, never deleted.

The source is retained whole and fenced once the target is switched. A writer that still holds a descriptor writes
into the retained source at its original path, and no retry deletes it. Every move runs the production entry points:
``prepare_clone`` before a reboot, then ``finish_clone`` after one.
"""

import errno
import os
import subprocess

import pytest

from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"
REAL_SYNC, REAL_SAVE = fd_tree.sync, project_move._save  # noqa: SLF001


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


def heal(monkeypatch):
    """Restore only the crash seams, as the move tests do."""
    monkeypatch.setattr(fd_tree, "sync", REAL_SYNC)
    monkeypatch.setattr(project_move, "_save", REAL_SAVE)


def move(repo, monkeypatch):
    """The operator's sequence: prepare once, then finish after a different boot session."""
    if not (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists():
        monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
        offline_protocol.prepare_clone(repo, gaps=lambda: ())
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return offline_protocol.finish_clone(repo, gaps=lambda: ())


def crash_after_switch(monkeypatch):
    """Let the switch be recorded, then crash before anything else runs."""

    def save(folder, folder_fd, rec, **kwargs):
        REAL_SAVE(folder, folder_fd, rec, **kwargs)
        if rec["phase"] == project_move.SWITCHED:
            msg = "simulated crash"
            raise CrashError(msg)

    monkeypatch.setattr(project_move, "_save", save)


def test_a_write_through_a_descriptor_before_the_switch_refuses_and_stays_in_the_source(clone, monkeypatch):
    """The final publication guard refuses a source edited before the SWITCHED record's durable write."""
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    runner = folder / "changes" / "c1" / "runner.log"
    writer = os.open(runner, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)

    def save(clone_folder, folder_fd, rec, **kwargs):
        if rec["phase"] == project_move.SWITCHED:  # after the digest check, before the switch is recorded
            os.write(writer, b"late owner bytes\n")
        REAL_SAVE(clone_folder, folder_fd, rec, **kwargs)

    monkeypatch.setattr(project_move, "_save", save)
    try:
        with pytest.raises(StoreError, match="changed after it was copied"):
            move(repo, monkeypatch)
    finally:
        os.close(writer)
    assert runner.read_text() == "ran\nlate owner bytes\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert project_move.record(folder)["phase"] == project_move.COPYING


def test_a_write_through_a_descriptor_after_the_switch_stays_in_the_source_at_its_path(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    runner = folder / "changes" / "c1" / "runner.log"
    writer = os.open(runner, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    crash_after_switch(monkeypatch)
    try:
        with pytest.raises(CrashError):
            move(repo, monkeypatch)
        os.write(writer, b"post-switch owner bytes\n")  # the descriptor outlives the switch
    finally:
        os.close(writer)
    heal(monkeypatch)
    assert move(repo, monkeypatch) == target
    assert runner.read_text() == "ran\npost-switch owner bytes\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert project_home.located(repo) == target


def test_a_leaf_swapped_for_a_foreign_file_before_it_is_kept_keeps_the_foreign_bytes(tmp_path):
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "leaf").write_text("owned\n")
    (folder / "foreign").write_text("foreign\n")
    dfd = os.open(folder, fd_tree.DIR_FLAGS)
    try:
        (folder / "foreign").replace(folder / "leaf")  # a foreign file takes the owned name
        held = fd_tree.keep_entry(dfd, "leaf")
    finally:
        os.close(dfd)
    assert not (folder / "leaf").exists()
    assert [p.name for p in folder.iterdir()] == [held]
    assert (folder / held).read_text() == "foreign\n"


def test_a_lock_swapped_for_a_foreign_file_after_the_switch_is_retained_and_never_deleted(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    crash_after_switch(monkeypatch)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    (folder / "foreign.lock").write_text("foreign lock\n")
    (folder / "foreign.lock").replace(folder / project_move.MOVE_LOCK)  # the lock name now names a foreign file
    heal(monkeypatch)
    assert move(repo, monkeypatch) == target
    assert (folder / project_move.MOVE_LOCK).read_text() == "foreign lock\n"


def test_an_eio_on_the_first_prejournal_write_keeps_the_entry_and_the_retry_refuses_with_the_path_unchanged(
    clone, monkeypatch
):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    real_rename = os.rename

    def failing_rename(src, dst, *args, **kwargs):
        if str(src).startswith(".tmp-") and dst == project_move.MOVE_RECORD:
            raise OSError(errno.EIO, "simulated I/O error")
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr(fd_tree.os, "rename", failing_rename)
    with pytest.raises(StoreError, match=r"could not be written"):
        move(repo, monkeypatch)
    kept = [p for p in folder.iterdir() if p.name.startswith(fd_tree.QUARANTINE)]
    assert len(kept) == 1
    before = kept[0].read_bytes()
    assert before
    assert not (folder / project_move.MOVE_RECORD).exists()
    assert not target.exists()

    monkeypatch.setattr(fd_tree.os, "rename", real_rename)
    with pytest.raises(StoreError, match=r"kept by an earlier failed operation"):
        move(repo, monkeypatch)
    assert [p.name for p in folder.iterdir() if p.name.startswith(fd_tree.QUARANTINE)] == [kept[0].name]
    assert kept[0].read_bytes() == before
    assert not (folder / project_move.MOVE_RECORD).exists()
    assert not target.exists()
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
