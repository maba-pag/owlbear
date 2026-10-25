"""``make_dirs`` retries must re-sync the deepest existing boundary's parent link before creating descendants."""

from __future__ import annotations

import errno
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import storage_io

REAL_FSYNC = storage_io.fsync_dir
REAL_MKDIR = Path.mkdir


def _interrupt_on_fsync_of(folder: Path, call) -> None:
    """Run *call* with the fsync of *folder*'s entry failing, simulating an interrupted earlier attempt."""

    def failing(target: Path) -> None:
        if target == folder:
            raise OSError(errno.EIO, "injected parent fsync failure", str(target))
        REAL_FSYNC(target)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(storage_io, "fsync_dir", failing)
        with pytest.raises(OSError, match="injected parent fsync failure"):
            call()


def _traced_make_dirs(target: Path) -> list[tuple[str, Path]]:
    log: list[tuple[str, Path]] = []

    def fsync(folder: Path) -> None:
        log.append(("fsync", folder))
        REAL_FSYNC(folder)

    def mkdir(self: Path, *args: object, **kwargs: object) -> None:
        log.append(("mkdir", self))
        REAL_MKDIR(self, *args, **kwargs)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(storage_io, "fsync_dir", fsync)
        m.setattr(Path, "mkdir", mkdir)
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

    def always_failing(folder: Path) -> None:
        if folder == base:
            raise OSError(errno.EIO, "injected boundary fsync failure", str(folder))
        REAL_FSYNC(folder)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(storage_io, "fsync_dir", always_failing)
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
