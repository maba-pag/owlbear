"""The offline receipt lookup reads the ledger as a host does, without a host: nothing restored, inspected or saved."""

import io
import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.local_system import local_home, maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots


def ledger_path() -> Path:
    return local_home.root() / maintenance.FILE


def receipted_ledger() -> None:
    """A ledger a host wrote with one receipt: record version ``d0`` of project ``p`` is the rewrite of run G0."""
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=lambda *_args: False)
    owner.receipt("p", "d0", "G0")


class LookupDescriptors:
    """Only the lookup thread's acquisitions count; each fdopen transfer is tracked by its native file."""

    def __init__(self) -> None:
        self.reader = threading.current_thread()
        self.opened, self.active, self.closed, self.files, self.strays = [], set(), [], [], []
        self.real_open, self.real_close, self.real_fdopen = os.open, os.close, os.fdopen
        self.real_lock = maintenance.open_lock

    def open(self, *args, **kwargs):
        return self.owned(self.real_open(*args, **kwargs))

    def lock(self, *args, **kwargs):
        return self.owned(self.real_lock(*args, **kwargs))

    def owned(self, fd: int) -> int:
        if threading.current_thread() is self.reader:
            self.opened.append(fd)
            self.active.add(fd)
        return fd

    def close(self, fd: int) -> None:
        if threading.current_thread() is not self.reader:
            self.real_close(fd)
            return
        if fd in self.active:
            self.active.remove(fd)
            self.closed.append(fd)
        else:
            self.strays.append(fd)
        self.real_close(fd)

    def fdopen(self, fd: int, *args, **kwargs):
        source = self.real_fdopen(fd, *args, **kwargs)
        if threading.current_thread() is not self.reader:
            return source
        assert fd in self.active
        self.active.remove(fd)
        self.files.append(source)
        return source

    def patch(self, patch: pytest.MonkeyPatch) -> None:
        patch.setattr(maintenance, "open_lock", self.lock)
        patch.setattr(
            maintenance,
            "os",
            SimpleNamespace(
                **(
                    vars(os)
                    | {
                        "open": self.open,
                        "close": self.close,
                        "fdopen": self.fdopen,
                    }
                )
            ),
        )

    def all_closed(self) -> bool:
        return (
            bool(self.opened)
            and not self.active
            and not self.strays
            and len(self.opened) == len(self.closed) + len(self.files)
            and all(source.closed for source in self.files)
        )


def test_the_lookup_finds_a_known_receipt_and_nothing_for_another_version_without_a_host(monkeypatch):
    receipted_ledger()
    before = ledger_path().read_bytes()
    with monkeypatch.context() as patch:
        no_host(patch)
        assert maintenance.Maintenance.lookup_receipt("p", "d0") == "G0"
        assert maintenance.Maintenance.lookup_receipt("p", "d1") == ""
        assert maintenance.Maintenance.lookup_receipt("q", "d0") == ""  # another project's receipt is not this one's
    assert ledger_path().read_bytes() == before


def test_a_missing_ledger_holds_no_receipt_and_is_not_created(monkeypatch):
    with monkeypatch.context() as patch:
        no_host(patch)
        assert maintenance.Maintenance.lookup_receipt("p", "d0") == ""
    assert not ledger_path().exists()


def no_host(patch: pytest.MonkeyPatch) -> None:
    """Every part of a host the lookup must not touch fails the test if it is reached."""

    def reached(*_args: object, **_kwargs: object) -> None:
        pytest.fail("the lookup reached a host-only step")

    for owner, name in (
        (maintenance.Maintenance, "__init__"),
        (maintenance.Maintenance, "_save"),
        (maintenance.psutil, "boot_time"),
        (processes, "alive"),
        (Slots, "restore_one"),
    ):
        patch.setattr(owner, name, reached)


@pytest.mark.parametrize(
    "body",
    [
        '{"format": 1, "imported": []}',  # sessions missing: never an empty ledger
        '{"format": 1, "sessions": []}',  # imported missing
        '{"format": 2, "sessions": [], "imported": []}',  # a later format
        '{"format": 1, "sessions": [], "imported": [], "later": 1}',  # a field this host does not know
        "{",
    ],
    ids=["no-sessions", "no-imported", "future-format", "unknown-field", "damaged"],
)
def test_a_ledger_that_cannot_be_read_whole_is_refused_not_taken_for_empty(monkeypatch, body):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    descriptors = LookupDescriptors()
    with monkeypatch.context() as patch:
        descriptors.patch(patch)
        no_host(patch)
        with pytest.raises(maintenance.MaintenanceError, match="could not be read"):
            maintenance.Maintenance.lookup_receipt("p", "d0")
    assert path.read_text() == body
    assert descriptors.all_closed()


@pytest.mark.parametrize("kind", ["fifo", "directory", "link"])
def test_a_ledger_that_is_not_a_regular_file_is_refused_at_once_and_its_descriptor_closed(monkeypatch, tmp_path, kind):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    else:
        whole = tmp_path / "elsewhere.json"
        whole.write_text(json.dumps({"format": 1, "sessions": [], "imported": ["p:receipt:d0:G0"]}))
        path.symlink_to(whole)
    descriptors = LookupDescriptors()
    outcome: list[BaseException] = []

    def look() -> None:
        try:
            maintenance.Maintenance.lookup_receipt("p", "d0")
        except BaseException as exc:  # noqa: BLE001 - handed to the test's own assertion
            outcome.append(exc)

    with monkeypatch.context() as patch:
        descriptors.patch(patch)
        no_host(patch)
        reader = threading.Thread(target=look, daemon=True)
        descriptors.reader = reader
        reader.start()
        reader.join(5)
    assert not reader.is_alive(), "the lookup waited on the ledger"
    assert [type(e) for e in outcome] == [maintenance.MaintenanceError]
    assert descriptors.all_closed()


def test_the_lookup_descriptor_oracle_ignores_unrelated_reuse_and_detects_a_stray_close():
    descriptors, closed = LookupDescriptors(), []
    descriptors.real_open = lambda *_args: 17
    descriptors.real_close = closed.append
    fd = descriptors.open("owned", os.O_RDONLY)
    descriptors.close(fd)
    assert descriptors.all_closed()
    unrelated = descriptors.real_open("unrelated", os.O_RDONLY)
    assert unrelated == fd  # a modeled allocator deliberately reuses the released number
    descriptors.real_close(unrelated)
    assert descriptors.all_closed()
    descriptors.close(unrelated)
    assert not descriptors.all_closed()
    assert descriptors.strays == [unrelated]


def test_the_lookup_descriptor_oracle_detects_raw_and_transferred_file_leaks():
    descriptors = LookupDescriptors()
    descriptors.real_open = lambda *_args: 17
    descriptors.real_close = lambda _fd: None
    descriptors.real_fdopen = lambda _fd: io.StringIO("ledger")
    fd = descriptors.open("owned", os.O_RDONLY)
    assert not descriptors.all_closed()
    descriptors.close(fd)
    assert descriptors.all_closed()
    source = descriptors.fdopen(descriptors.open("owned-again", os.O_RDONLY))
    assert not descriptors.all_closed()
    source.close()
    assert descriptors.all_closed()


def test_an_unrelated_descriptor_closed_during_lookup_does_not_change_its_ownership_proof(tmp_path, monkeypatch):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{")
    other = tmp_path / "unrelated"
    other.write_text("another reader")
    fd, closed, descriptors, real_read = os.open(other, os.O_RDONLY), [], LookupDescriptors(), maintenance._read  # noqa: SLF001

    def read_after_unrelated_close(target):
        closed.append(fd)
        os.close(fd)
        return real_read(target)

    try:
        with monkeypatch.context() as patch:
            descriptors.patch(patch)
            no_host(patch)
            patch.setattr(maintenance, "_read", read_after_unrelated_close)
            with pytest.raises(maintenance.MaintenanceError, match="could not be read"):
                maintenance.Maintenance.lookup_receipt("p", "d0")
    finally:
        if not closed:
            os.close(fd)
    assert closed == [fd]
    assert descriptors.all_closed()
    assert path.read_text() == "{"


def test_another_threads_maintenance_descriptor_is_not_owned_by_this_lookup(tmp_path, monkeypatch):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{")
    other = tmp_path / "other-reader"
    other.write_text("another reader")
    acquired, release, descriptors = threading.Event(), threading.Event(), LookupDescriptors()

    def other_reader():
        fd = maintenance.os.open(other, os.O_RDONLY)
        try:
            acquired.set()
            assert release.wait(5)
        finally:
            maintenance.os.close(fd)

    with monkeypatch.context() as patch:
        descriptors.patch(patch)
        no_host(patch)
        reader = threading.Thread(target=other_reader, daemon=True)
        reader.start()
        try:
            assert acquired.wait(5)
            with pytest.raises(maintenance.MaintenanceError, match="could not be read"):
                maintenance.Maintenance.lookup_receipt("p", "d0")
            assert descriptors.all_closed()
        finally:
            release.set()
            reader.join(5)
        assert not reader.is_alive()


def test_a_host_still_finds_the_same_receipt_through_its_own_ledger():
    receipted_ledger()
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=lambda *_args: False)
    assert (owner.receipted("p", "d0"), owner.receipted("p", "d1")) == ("G0", "")
