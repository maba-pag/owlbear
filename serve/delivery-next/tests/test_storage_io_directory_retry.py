"""``make_dirs`` retries must re-sync the deepest existing boundary's parent link before creating descendants."""

from __future__ import annotations

import errno
import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.local_system import storage_io

REAL_SYNC = storage_io._sync_held  # noqa: SLF001 - make_dirs' own sync of a held folder
REAL_MKDIR = storage_io._mkdir_at  # noqa: SLF001 - make_dirs' own creation inside a held folder


def _interrupt_on_fsync_of(folder: Path, call) -> None:
    """Run *call* with the fsync of *folder*'s entry failing, simulating an interrupted earlier attempt."""

    def failing(fd: int, target: Path) -> None:
        if target == folder:
            raise OSError(errno.EIO, "injected parent fsync failure", str(target))
        REAL_SYNC(fd, target)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(storage_io, "_sync_held", failing)
        with pytest.raises(OSError, match="injected parent fsync failure"):
            call()


def _traced_make_dirs(target: Path) -> list[tuple[str, Path]]:
    log: list[tuple[str, Path]] = []

    def fsync(fd: int, folder: Path) -> None:
        log.append(("fsync", folder))
        REAL_SYNC(fd, folder)

    def mkdir(parent: int, name: str, path: Path) -> None:
        log.append(("mkdir", path))
        REAL_MKDIR(parent, name, path)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(storage_io, "_sync_held", fsync)
        m.setattr(storage_io, "_mkdir_at", mkdir)
        storage_io.make_dirs(target)
    return log


def test_retry_resyncs_deepest_boundary_before_creating_descendants(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    boundary = base / "a"
    _interrupt_on_fsync_of(base, lambda: storage_io.make_dirs(boundary / "b"))
    assert boundary.is_dir()
    assert not (boundary / "b").exists()

    log = _traced_make_dirs(boundary / "b" / "c")

    assert (boundary / "b" / "c").is_dir()
    assert log == [
        ("fsync", base),
        ("mkdir", boundary / "b"),
        ("fsync", boundary),
        ("mkdir", boundary / "b" / "c"),
        ("fsync", boundary / "b"),
    ]


def test_retry_on_existing_final_directory_resyncs_its_parent_link(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    final = base / "a"
    _interrupt_on_fsync_of(base, lambda: storage_io.make_dirs(final))
    assert final.is_dir()

    log = _traced_make_dirs(final)

    assert log == [("fsync", base)]


def test_boundary_resync_failure_is_raised_before_any_descendant_is_created(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    boundary = base / "a"
    _interrupt_on_fsync_of(base, lambda: storage_io.make_dirs(boundary / "b"))

    def always_failing(fd: int, folder: Path) -> None:
        if folder == base:
            raise OSError(errno.EIO, "injected boundary fsync failure", str(folder))
        REAL_SYNC(fd, folder)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(storage_io, "_sync_held", always_failing)
        with pytest.raises(OSError, match="injected boundary fsync failure"):
            storage_io.make_dirs(boundary / "b" / "c")

    assert not (boundary / "b").exists()


def test_existing_ordinary_directory_creates_nothing(tmp_path: Path) -> None:
    ready = tmp_path / "ready"
    ready.mkdir()

    log = _traced_make_dirs(ready)

    assert ready.is_dir()
    assert not [entry for entry in log if entry[0] == "mkdir"]


def test_fresh_multi_level_create_syncs_each_new_parent_in_order(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()

    log = _traced_make_dirs(base / "x" / "y" / "z")

    assert (base / "x" / "y" / "z").is_dir()
    assert log == [
        ("fsync", tmp_path),
        ("mkdir", base / "x"),
        ("fsync", base),
        ("mkdir", base / "x" / "y"),
        ("fsync", base / "x"),
        ("mkdir", base / "x" / "y" / "z"),
        ("fsync", base / "x" / "y"),
    ]


def _entries_below(folder: Path) -> dict[str, bytes | None]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() if p.is_file() and not p.is_symlink() else None
        for p in sorted(folder.rglob("*"))
    }


@pytest.fixture
def descriptors(monkeypatch):
    reader = threading.current_thread()
    opened, active, strays = [], set(), []
    real_open, real_close = os.open, os.close

    def acquire(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        if threading.current_thread() is reader:
            opened.append(fd)
            active.add(fd)
        return fd

    def close(fd):
        if threading.current_thread() is reader:
            if fd in active:
                active.remove(fd)
            else:
                strays.append(fd)
        real_close(fd)

    monkeypatch.setattr(storage_io, "os", SimpleNamespace(**(vars(os) | {"open": acquire, "close": close})))
    yield active
    assert opened
    assert not active
    assert not strays


@pytest.mark.parametrize("folder", ["existing", "made-here"])
def test_a_folder_linked_away_as_its_parent_is_synced_gets_nothing_made_through_it(
    tmp_path: Path, folder: str, descriptors
) -> None:
    """``base/x/y/z`` is made with ``x`` already there, or made by this call. At the real sync of ``base``, the owner
    moves ``x`` aside and links its name to a foreign folder: nothing is made in the foreign folder or in the moved
    ``x``, the call raises, and every descriptor it opened is closed."""
    base, foreign, moved = tmp_path / "base", tmp_path / "foreign", tmp_path / "moved"
    base.mkdir()
    foreign.mkdir()
    (foreign / "keep.txt").write_text("the foreign folder's own file\n")
    if folder == "existing":
        (base / "x").mkdir()
    theirs, synced, real_fsync, fired = _entries_below(foreign), base.stat(), os.fsync, []

    def fsync(fd: int) -> None:
        real_fsync(fd)
        if not fired and os.path.samestat(os.fstat(fd), synced) and (base / "x").exists():
            fired.append(True)
            (base / "x").rename(moved)
            (base / "x").symlink_to(foreign, target_is_directory=True)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(storage_io.os, "fsync", fsync)
        with pytest.raises(OSError):  # noqa: PT011 - any refusal; what matters is what was made where
            storage_io.make_dirs(base / "x" / "y" / "z")

    assert fired, "base was never synced with x in it"
    assert _entries_below(foreign) == theirs  # first: nothing was made in the foreign folder
    assert _entries_below(moved) == {}  # nor below the owner's x, moved aside
    assert not descriptors


def test_making_folders_or_refusing_a_pipe_in_their_way_closes_every_descriptor(tmp_path: Path, descriptors) -> None:
    storage_io.make_dirs(tmp_path / "a" / "b" / "c")
    assert (tmp_path / "a" / "b" / "c").is_dir()
    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(NotADirectoryError):
        storage_io.make_dirs(tmp_path / "pipe" / "x")
    assert not (tmp_path / "pipe" / "x").exists()
    assert not descriptors
