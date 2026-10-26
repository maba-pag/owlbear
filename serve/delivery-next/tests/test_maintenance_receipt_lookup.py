"""The offline receipt lookup reads the ledger as a host does, without a host: nothing restored, inspected or saved."""

import json
import os
import threading
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import local_home, maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots


def ledger_path() -> Path:
    return local_home.root() / maintenance.FILE


def receipted_ledger() -> None:
    """A ledger a host wrote with one receipt: record version ``d0`` of project ``p`` is the rewrite of run G0."""
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=lambda *_args: False)
    owner.receipt("p", "d0", "G0")


def open_fds() -> set[str]:
    return {p.name for p in Path("/dev/fd").iterdir()}


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
def test_a_ledger_that_cannot_be_read_whole_is_refused_not_taken_for_empty(monkeypatch, body, steady_descriptors):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    with steady_descriptors():
        fds = open_fds()
        with monkeypatch.context() as patch:
            no_host(patch)
            with pytest.raises(maintenance.MaintenanceError, match="could not be read"):
                maintenance.Maintenance.lookup_receipt("p", "d0")
        assert (path.read_text(), open_fds()) == (body, fds)


@pytest.mark.parametrize("kind", ["fifo", "directory", "link"])
def test_a_ledger_that_is_not_a_regular_file_is_refused_at_once_and_its_descriptor_closed(
    monkeypatch, tmp_path, kind, steady_descriptors
):
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
    outcome: list[BaseException] = []

    def look() -> None:
        try:
            maintenance.Maintenance.lookup_receipt("p", "d0")
        except BaseException as exc:  # noqa: BLE001 - handed to the test's own assertion
            outcome.append(exc)

    with steady_descriptors():
        fds = open_fds()
        with monkeypatch.context() as patch:
            no_host(patch)
            reader = threading.Thread(target=look, daemon=True)
            reader.start()
            reader.join(5)
        assert not reader.is_alive(), "the lookup waited on the ledger"
        assert [type(e) for e in outcome] == [maintenance.MaintenanceError]
        assert open_fds() == fds


def test_a_host_still_finds_the_same_receipt_through_its_own_ledger():
    receipted_ledger()
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=lambda *_args: False)
    assert (owner.receipted("p", "d0"), owner.receipted("p", "d1")) == ("G0", "")
