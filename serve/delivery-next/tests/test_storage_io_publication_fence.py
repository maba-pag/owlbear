import os
import stat
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import storage_io


def test_atomic_write_revalidates_after_real_temporary_sync_and_before_replacement(tmp_path, monkeypatch):
    target = tmp_path / "record.json"
    target.write_text("owner\n")
    events = []
    real_fsync, real_replace = os.fsync, Path.replace

    def synced(fd):
        real_fsync(fd)
        events.append("file-sync" if stat.S_ISREG(os.fstat(fd).st_mode) else "directory-sync")

    def guard():
        events.append("guard")
        assert target.read_text() == "owner\n"
        assert next(tmp_path.glob(".tmp-*.tmp")).read_text() == "candidate\n"

    def replaced(source, destination):
        events.append("replace")
        return real_replace(source, destination)

    monkeypatch.setattr(os, "fsync", synced)
    monkeypatch.setattr(Path, "replace", replaced)
    written = storage_io.atomic_write(target, "candidate\n", before_replace=guard)

    assert events == ["file-sync", "guard", "replace", "directory-sync"]
    assert os.path.samestat(written, target.stat())
    assert target.read_text() == "candidate\n"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure", [OSError("I/O fence"), RuntimeError("authority fence")])
def test_atomic_write_propagates_callback_errors_without_publication_or_leaked_temporary(tmp_path, existing, failure):
    target = tmp_path / "record.json"
    if existing:
        target.write_text("owner\n")

    def refuse():
        raise failure

    with pytest.raises(type(failure)) as caught:
        storage_io.atomic_write(target, "candidate\n", before_replace=refuse)

    assert caught.value is failure
    assert (target.read_text() if target.exists() else None) == ("owner\n" if existing else None)
    assert not list(tmp_path.glob(".tmp-*.tmp"))
