"""A pre-journal I/O error syncing the temporary entry keeps its owned bytes and never writes the target."""

import errno
import os
import stat

import pytest

from owlbear_delivery_next.state_store import fd_tree
from owlbear_delivery_next.state_store.database import StoreError

REAL_FSYNC = os.fsync


@pytest.mark.parametrize("change", ["replace", "replace-same", "inplace"])
def test_text_predicate_refuses_an_entry_changed_during_its_read(tmp_path, monkeypatch, change):
    entry = tmp_path / "receipt.json"
    entry.write_text("owned\n")
    before = entry.stat()
    real_read = os.read
    fired = []
    owner = "owned\n" if change == "replace-same" else "other\n"

    def read(fd, count):
        data = real_read(fd, count)
        if data and not fired and os.path.samestat(os.fstat(fd), before):
            fired.append(True)
            if change == "inplace":
                entry.write_text(owner)
            else:
                replacement = tmp_path / "owner-replacement"
                replacement.write_text(owner)
                replacement.replace(entry)
        return data

    monkeypatch.setattr(os, "read", read)
    dfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        assert not fd_tree.holds_text_at(dfd, entry.name, "owned\n")
    finally:
        os.close(dfd)
    assert fired == [True]
    assert entry.read_text() == owner


class HandoverAbort(BaseException):
    """A handover abort outside Exception must still close the writer's raw descriptor."""


@pytest.mark.parametrize(
    "failure",
    [OSError(errno.ENOMEM, "handover failed"), RuntimeError("handover failed"), HandoverAbort("handover failed")],
)
def test_a_failed_temporary_file_handover_closes_the_raw_descriptor_and_keeps_owner_bytes(
    tmp_path, monkeypatch, failure
):
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "meta.json").write_text("owner\n")
    dfd = os.open(folder, fd_tree.DIR_FLAGS)
    captured = []

    class HandoverOS:
        def __getattr__(self, name):
            return getattr(os, name)

        def fdopen(self, fd, *_args, **_kwargs):
            captured.append(fd)
            raise failure

    monkeypatch.setattr(fd_tree, "os", HandoverOS())
    try:
        with pytest.raises((StoreError, type(failure)), match="handover failed"):
            fd_tree.write_at(dfd, "meta.json", "candidate\n")
        assert len(captured) == 1, "the descriptor handover fault never fired"
        closed = None
        try:
            os.fstat(captured[0])
        except OSError as exc:
            closed = exc
        else:
            os.close(captured[0])  # clean up the reproduced leak before failing the control
        assert closed is not None, "fdopen failure leaked the writer's raw descriptor"
        assert closed.errno == errno.EBADF
    finally:
        os.close(dfd)
    assert (folder / "meta.json").read_text() == "owner\n"
    assert len(list(folder.iterdir())) == 2, "the failed candidate entry was lost"


def test_healthy_write_closes_its_raw_descriptor_and_fences_only_after_real_temporary_sync(tmp_path, monkeypatch):
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "meta.json").write_text("owner\n")
    dfd = os.open(folder, fd_tree.DIR_FLAGS)
    captured, events = [], []

    class WritingOS:
        def __getattr__(self, name):
            return getattr(os, name)

        def fdopen(self, fd, *args, **kwargs):
            captured.append(fd)
            assert kwargs["closefd"] is False
            return os.fdopen(fd, *args, **kwargs)

        def fsync(self, fd):
            os.fsync(fd)
            events.append("file-sync" if stat.S_ISREG(os.fstat(fd).st_mode) else "directory-sync")

        def rename(self, src, dst, *, src_dir_fd, dst_dir_fd):
            events.append("rename")
            return os.rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def fence():
        events.append("guard")
        with pytest.raises(OSError, match=f"Errno {errno.EBADF}") as exc:
            os.fstat(captured[0])
        assert exc.value.errno == errno.EBADF
        assert (folder / "meta.json").read_text() == "owner\n"
        assert next(folder.glob(".tmp-*")).read_text() == "candidate\n"

    monkeypatch.setattr(fd_tree, "os", WritingOS())
    try:
        assert fd_tree.write_at(dfd, "meta.json", "candidate\n", before_replace=fence) is None
        assert os.path.samestat(os.fstat(dfd), folder.stat())
    finally:
        os.close(dfd)
    assert events == ["file-sync", "guard", "rename", "directory-sync"]
    assert (folder / "meta.json").read_text() == "candidate\n"
    assert sorted(p.name for p in folder.iterdir()) == ["meta.json"]


def test_an_eio_syncing_the_temporary_entry_keeps_its_bytes_under_a_quarantine_name_and_never_writes_the_target(
    tmp_path, monkeypatch
):
    folder = tmp_path / "folder"
    folder.mkdir()
    dfd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)

    def fsync(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):  # the temporary file, before it is renamed into place
            raise OSError(errno.EIO, "simulated I/O error")
        REAL_FSYNC(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    try:
        with pytest.raises(StoreError, match=r"could not be written"):
            fd_tree.write_at(dfd, "meta.json", "{}\n")
    finally:
        os.close(dfd)
    assert not (folder / "meta.json").exists()
    kept = list(folder.iterdir())
    assert [p.name.startswith(fd_tree.QUARANTINE) for p in kept] == [True]
    assert [p.read_text() for p in kept] == ["{}\n"]
