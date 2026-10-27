"""A clone's store moved across volumes: resumed only from what the move recorded, refused otherwise.

Every move runs the production entry points: ``prepare_clone`` before a reboot, then ``finish_clone`` after one.
The boot session and the legacy-producer list are the only synthetic witnesses; the fence, the record and the locks
are the real ones.
"""

import fcntl
import os
import shutil
import sqlite3
import subprocess

import pytest

from owlbear_delivery_next.state_store import fd_tree, legacy_family, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"


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


REAL_SYNC, REAL_SAVE = fd_tree.sync, project_move._save  # noqa: SLF001


def heal(monkeypatch):
    """Restore only the crash seams: an undo would also drop the test's HOME from conftest."""
    monkeypatch.setattr(fd_tree, "sync", REAL_SYNC)
    monkeypatch.setattr(project_move, "_save", REAL_SAVE)


def no_gaps():
    return ()


def move(repo, monkeypatch):
    """The operator's sequence: prepare once, then finish after a different boot session."""
    if not (project_home.clone_dir(repo) / offline_protocol.PREPARED).exists():
        monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
        offline_protocol.prepare_clone(repo, gaps=no_gaps)
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return offline_protocol.finish_clone(repo, gaps=no_gaps)


def crash_before_sync(monkeypatch, name):
    """Make the sync of entry *name* raise, as a crash would, before it is made durable."""
    real = fd_tree.sync

    def sync(dfd, entry):
        if entry == name:
            msg = "simulated crash"
            raise CrashError(msg)
        real(dfd, entry)

    monkeypatch.setattr(fd_tree, "sync", sync)


def crash_after_switch(monkeypatch):
    """Let the switch be recorded, then crash before anything else runs."""
    real = project_move._save  # noqa: SLF001

    def save(folder, folder_fd, rec):
        real(folder, folder_fd, rec)
        if rec["phase"] == project_move.SWITCHED:
            msg = "simulated crash"
            raise CrashError(msg)

    monkeypatch.setattr(project_move, "_save", save)


def test_a_copy_published_before_a_crash_resumes_and_the_source_stays_whole(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    crash_before_sync(monkeypatch, SOURCE_ID)  # the published target is not yet durable
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"  # the source is still there
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    heal(monkeypatch)
    assert move(repo, monkeypatch) == target
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"  # kept whole, never removed
    assert (folder / project_move.MOVE_RECORD).exists()  # the switched record stays as the receipt
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert project_home.located(repo) == target  # a repeated startup changes nothing


def test_a_copy_cut_short_keeps_the_source_and_the_next_start_finishes(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    stage = target.with_name(f".{SOURCE_ID}.staging")
    crash_before_sync(monkeypatch, "changes")
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (stage / "changes").is_dir()
    assert not target.exists()
    heal(monkeypatch)
    assert move(repo, monkeypatch) == target
    assert not stage.exists()
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_destination_nobody_recorded_is_refused_and_both_copies_are_kept(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    (target / "changes").mkdir(parents=True)
    (target / "changes" / "foreign.txt").write_text("theirs\n")
    with pytest.raises(StoreError, match=r"both exist"):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (target / "changes" / "foreign.txt").read_text() == "theirs\n"
    assert not (target / "changes" / "c1").exists()


def test_a_source_edited_after_its_copy_was_published_is_kept_and_not_removed(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    crash_before_sync(monkeypatch, SOURCE_ID)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    (folder / "changes" / "c1" / "runner.log").write_text("edited after the copy\n")
    heal(monkeypatch)
    with pytest.raises(StoreError, match=r"changed after it was copied"):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "edited after the copy\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()


def test_a_destination_swapped_for_a_link_after_publication_is_refused(clone, monkeypatch, tmp_path):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    crash_before_sync(monkeypatch, SOURCE_ID)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "runner.log").write_text("not ours\n")
    target.rename(tmp_path / "moved-aside")
    target.symlink_to(elsewhere, target_is_directory=True)
    heal(monkeypatch)
    with pytest.raises(StoreError, match=r"holds a link"):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()
    assert (tmp_path / "moved-aside" / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (elsewhere / "runner.log").read_text() == "not ours\n"


def test_a_partial_moved_aside_and_replaced_by_a_foreign_one_is_refused_and_kept(clone, monkeypatch, tmp_path):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    stage = target.with_name(f".{SOURCE_ID}.staging")
    crash_before_sync(monkeypatch, "changes")
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    stage.rename(tmp_path / "owned-aside")
    (stage / "changes").mkdir(parents=True)
    (stage / "changes" / "foreign.txt").write_text("theirs\n")
    heal(monkeypatch)
    with pytest.raises(StoreError, match=r"not from a move OwlBear recorded"):
        move(repo, monkeypatch)
    assert (stage / "changes" / "foreign.txt").read_text() == "theirs\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()


def test_a_crash_after_the_switch_keeps_the_source_and_the_next_start_admits_the_target(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    crash_after_switch(monkeypatch)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    heal(monkeypatch)
    assert project_home.current(repo) == target  # the recorded switch is the authority
    assert move(repo, monkeypatch) == target
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_target_that_is_a_link_to_a_foreign_folder_is_refused_before_anything_moves(clone, monkeypatch, tmp_path):
    repo, folder = clone
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    target = project_home.home(SOURCE_ID)
    target.parent.mkdir(parents=True)
    target.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(StoreError, match=r"holds a link"):
        move(repo, monkeypatch)
    assert list(foreign.iterdir()) == []
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists() is False


def test_a_foreign_entry_in_the_destination_refuses_the_whole_move(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    (target / "config").mkdir(parents=True)
    (target / "config" / "theirs.json").write_text("{}\n")
    (folder / "config").write_text("source config\n")
    with pytest.raises(StoreError, match=r"both exist"):
        move(repo, monkeypatch)
    assert (folder / "config").read_text() == "source config\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert project_home.current(repo) == folder


def test_a_link_in_the_clone_refuses_before_anything_moves(clone, monkeypatch, tmp_path):
    repo, folder = clone
    (folder / "escape").symlink_to(tmp_path)
    with pytest.raises(StoreError, match=r"holds a link"):
        move(repo, monkeypatch)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not (project_home.home(SOURCE_ID) / "changes").exists()


def test_a_partial_copy_nobody_recorded_is_not_deleted(clone, monkeypatch):
    repo, folder = clone
    stage = project_home.home(SOURCE_ID).with_name(f".{SOURCE_ID}.staging")
    (stage / "changes").mkdir(parents=True)
    (stage / "keep.txt").write_text("unknown owner\n")
    with pytest.raises(StoreError, match=r"not from a move OwlBear recorded"):
        move(repo, monkeypatch)
    assert (stage / "keep.txt").read_text() == "unknown owner\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_lock_replaced_by_a_link_to_a_foreign_file_refuses_and_nothing_is_touched(clone, monkeypatch, tmp_path):
    repo, folder = clone
    foreign = tmp_path / "foreign.lock"
    foreign.write_text("theirs\n")
    (folder / "changes" / "c1" / "lock").symlink_to(foreign)
    with pytest.raises(StoreError, match=r"cannot be locked"):
        move(repo, monkeypatch)
    assert foreign.read_text() == "theirs\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not project_home.home(SOURCE_ID).exists()


def test_a_projects_folder_swapped_for_a_link_before_finish_is_refused_and_kept(clone, monkeypatch, tmp_path):
    repo, folder = clone
    projects = project_home.home(SOURCE_ID).parent
    crash_before_sync(monkeypatch, SOURCE_ID)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    aside = tmp_path / "projects-aside"
    projects.rename(aside)
    projects.symlink_to(elsewhere, target_is_directory=True)
    heal(monkeypatch)
    with pytest.raises(StoreError, match=r"holds a link"):
        move(repo, monkeypatch)
    assert list(elsewhere.iterdir()) == []
    assert (aside / SOURCE_ID / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()


def test_a_projects_folder_swapped_for_a_link_during_the_move_is_reported_and_nothing_foreign_is_written(
    clone, monkeypatch, tmp_path
):
    repo, folder = clone
    projects = project_home.home(SOURCE_ID).parent
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    aside = tmp_path / "projects-aside"
    real_sync, swapped = fd_tree.sync, []

    def sync(dfd, entry):
        real_sync(dfd, entry)
        if entry == SOURCE_ID and not swapped:  # the copy is published; the parent is swapped right after
            swapped.append(entry)
            projects.rename(aside)
            projects.symlink_to(elsewhere, target_is_directory=True)

    monkeypatch.setattr(fd_tree, "sync", sync)
    with pytest.raises(StoreError, match=r"is not the copy this move published"):
        move(repo, monkeypatch)
    assert swapped == [SOURCE_ID]
    assert list(elsewhere.iterdir()) == []
    assert (aside / SOURCE_ID / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()


def test_a_database_swapped_for_a_link_during_the_copy_is_refused(clone, monkeypatch, tmp_path):
    repo, folder = clone
    writer = sqlite3.connect(folder / "delivery.db", isolation_level=None)
    writer.execute("CREATE TABLE t (v TEXT)")
    writer.close()
    original = (folder / "delivery.db").read_bytes()
    foreign = tmp_path / "foreign.db"
    foreign.write_bytes(b"foreign")
    real_copy = fd_tree.copy
    swapped: list[str] = []

    def copy(sfd, name, dfd):
        if name == "delivery.db" and not swapped:  # the source is checked clean, then swapped before its copy
            swapped.append(name)
            os.rename("delivery.db", "kept.db", src_dir_fd=sfd, dst_dir_fd=sfd)
            os.symlink(foreign, "delivery.db", dir_fd=sfd)
        real_copy(sfd, name, dfd)

    monkeypatch.setattr(fd_tree, "copy", copy)
    with pytest.raises(StoreError):
        move(repo, monkeypatch)
    assert foreign.read_bytes() == b"foreign"
    assert (folder / "kept.db").read_bytes() == original
    assert (folder / project_move.MOVE_RECORD).exists()
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not (project_home.home(SOURCE_ID) / "delivery.db").is_symlink()


def test_a_clone_folder_swapped_after_a_metadata_write_is_refused(clone, monkeypatch, tmp_path):
    repo, folder = clone
    aside, elsewhere = tmp_path / "aside", tmp_path / "elsewhere"
    elsewhere.mkdir()
    real_copy = fd_tree.copy
    swapped: list[str] = []

    def copy(sfd, name, dfd):
        real_copy(sfd, name, dfd)
        if not swapped:  # the first entry is copied and its record written; the clone folder is then swapped
            swapped.append(name)
            folder.rename(aside)
            folder.symlink_to(elsewhere, target_is_directory=True)

    monkeypatch.setattr(fd_tree, "copy", copy)
    with pytest.raises(StoreError, match=r"no longer names"):
        move(repo, monkeypatch)
    assert list(elsewhere.iterdir()) == []
    assert (aside / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (aside / project_move.MOVE_RECORD).exists()


def test_a_wal_store_moves_with_its_committed_rows(clone, monkeypatch):
    repo, folder = clone
    writer = sqlite3.connect(folder / "delivery.db", isolation_level=None)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE t (v TEXT)")
    writer.execute("INSERT INTO t VALUES ('committed')")
    assert (folder / "delivery.db-wal").exists()
    try:
        target = move(repo, monkeypatch)
    finally:
        writer.close()
    check = sqlite3.connect(target / "delivery.db")
    try:
        assert check.execute("SELECT v FROM t").fetchall() == [("committed",)]
    finally:
        check.close()


def test_a_store_operation_in_flight_is_not_moved(clone, monkeypatch):
    # Store holds migrate.lock shared for each database operation; the move's exclusive fence refuses it.
    repo, folder = clone
    writer = sqlite3.connect(folder / "delivery.db", isolation_level=None)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE t (v TEXT)")
    operation = hold(folder / "migrate.lock", shared=True)
    try:
        with pytest.raises(StoreError, match=r"held by a running process"):
            move(repo, monkeypatch)
    finally:
        os.close(operation)
        writer.close()
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not (project_home.home(SOURCE_ID) / "changes").exists()


def hold(path, *, shared=False):
    """Take *path* as a running writer would, and keep it held until the caller closes the descriptor."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0o600)
    fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
    return fd


@pytest.mark.parametrize(
    ("lock", "shared"),
    [("host.lock", False), ("changes/c1/lock", False), ("migrate.lock", True), (".profile.lock", False)],
)
def test_a_lock_a_running_writer_holds_refuses_the_move_and_moves_nothing(clone, monkeypatch, lock, shared):
    repo, folder = clone
    fd = hold(folder / lock, shared=shared)
    try:
        with pytest.raises(StoreError, match=r"held by a running process: nothing was moved"):
            move(repo, monkeypatch)
    finally:
        os.close(fd)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not project_home.home(SOURCE_ID).exists()
    assert move(repo, monkeypatch) == project_home.home(SOURCE_ID)  # released: the move completes
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"  # kept whole in the source


def test_a_lock_nobody_holds_is_retained_by_the_move_and_never_unlinked(clone, monkeypatch):
    repo, folder = clone
    (folder / "host.lock").write_text("")
    assert move(repo, monkeypatch) == project_home.home(SOURCE_ID)
    assert (folder / "host.lock").is_file()


def test_without_a_verified_offline_proof_production_refuses_and_moves_nothing(clone, current_binding, monkeypatch):
    repo, folder = clone
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    unproven = legacy_family.Binding(None, current_binding.interpreter, current_binding.package)
    monkeypatch.setattr(legacy_family, "live_binding", lambda: unproven)
    with pytest.raises(StoreError, match=r"legacy producers are not proven fenced"):
        offline_protocol.prepare_clone(repo)  # the production list is non-empty
    assert not (folder / offline_protocol.PREPARED).exists()
    with pytest.raises(StoreError, match=r"no offline proof"):
        project_home.located(repo)  # an ordinary startup never moves a store
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert not project_home.home(SOURCE_ID).exists()
    assert not (folder / project_move.MOVE_RECORD).exists()


def test_a_source_edited_before_the_switch_is_refused_and_the_target_keeps_the_copy(clone, monkeypatch):
    repo, folder = clone
    (folder / "config").write_text("source config\n")
    target = project_home.home(SOURCE_ID)
    crash_before_sync(monkeypatch, SOURCE_ID)  # the copy is published but not yet switched
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    (folder / "config").write_text("edited before the switch\n")
    heal(monkeypatch)
    with pytest.raises(StoreError, match=r"changed after it was copied"):
        move(repo, monkeypatch)
    assert (folder / "config").read_text() == "edited before the switch\n"
    assert (target / "config").read_text() == "source config\n"
    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_move.MOVE_RECORD).exists()


def test_a_quarantined_entry_refusal_leaves_a_started_move_record_unchanged(clone, monkeypatch):
    repo, folder = clone
    crash_before_sync(monkeypatch, SOURCE_ID)  # a move has begun and recorded its phase
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    assert (folder / project_move.MOVE_RECORD).exists()
    record = (folder / project_move.MOVE_RECORD).read_text()
    kept = folder / f"{fd_tree.QUARANTINE}fedcba9876543210"
    kept.write_text("foreign\n")
    heal(monkeypatch)
    with pytest.raises(StoreError, match=r"kept by an earlier failed operation"):
        move(repo, monkeypatch)
    assert (folder / project_move.MOVE_RECORD).read_text() == record
    assert kept.read_text() == "foreign\n"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


WAL_FILES = ("delivery.db", "delivery.db-wal", "delivery.db-shm")


def test_an_empty_stage_made_before_its_identity_was_recorded_is_never_adopted(clone, monkeypatch):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    stage = target.parent / project_move._stage_name(target)  # noqa: SLF001
    real = project_move._save  # noqa: SLF001

    def save(folder_arg, folder_fd, rec):
        if rec["stage_id"] is not None and rec["proof"] is None:  # the stage_id record itself: crash before it lands
            msg = "simulated crash"
            raise CrashError(msg)
        real(folder_arg, folder_fd, rec)

    monkeypatch.setattr(project_move, "_save", save)
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    before = stage.stat()
    assert stage.is_dir()
    assert not any(stage.iterdir())
    heal(monkeypatch)

    with pytest.raises(StoreError):
        move(repo, monkeypatch)
    after = stage.stat()
    assert (after.st_ino, after.st_dev) == (before.st_ino, before.st_dev), "the unrecorded stage was replaced"
    assert not any(stage.iterdir())
    retired = target.parent / ".retired"
    assert not retired.exists() or not any(retired.iterdir()), "the unrecorded stage was moved aside"
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def freeze_wal_store(folder, tmp_path):
    """Leave *folder* with an uncheckpointed WAL store and no open connection, as a crashed writer would."""
    writer = sqlite3.connect(folder / "delivery.db", isolation_level=None)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("PRAGMA wal_autocheckpoint=0")  # the committed row stays in the -wal file
    writer.execute("CREATE TABLE t (v TEXT)")
    writer.execute("INSERT INTO t VALUES ('committed')")
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    for name in WAL_FILES:
        shutil.copy2(folder / name, frozen / name)  # the image taken while the writer is open
    writer.close()  # the last close would checkpoint and delete the -wal, so the image is restored after it
    for name in WAL_FILES:
        shutil.copy2(frozen / name, folder / name)


def test_a_cold_wal_store_interrupted_mid_move_resumes_with_its_uncheckpointed_rows(clone, monkeypatch, tmp_path):
    repo, folder = clone
    target = project_home.home(SOURCE_ID)
    freeze_wal_store(folder, tmp_path)  # no connection is open from here on
    assert (folder / "delivery.db-wal").stat().st_size > 0
    crash_before_sync(monkeypatch, "changes")  # interrupted during the copy, before the switch
    with pytest.raises(CrashError):
        move(repo, monkeypatch)
    assert not target.exists()
    heal(monkeypatch)
    assert move(repo, monkeypatch) == target
    assert project_home.located(repo) == target
    check = sqlite3.connect(target / "delivery.db")
    try:
        assert check.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert check.execute("SELECT v FROM t").fetchall() == [("committed",)]
    finally:
        check.close()
