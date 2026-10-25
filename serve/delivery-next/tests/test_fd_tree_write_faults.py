"""A pre-journal I/O error syncing the temporary entry keeps its owned bytes and never writes the target."""

import errno
import os
import stat

import pytest

from owlbear_delivery_next.state_store import fd_tree
from owlbear_delivery_next.state_store.database import StoreError

REAL_FSYNC = os.fsync


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
