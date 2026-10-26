"""Review 4375573453: the pack run record is read only as a regular file, without following a link or waiting on a pipe.

A FIFO, a directory or a link at the record's name is unreadable ownership, never an absent record: every reader returns
at once, closes its descriptor, and the restoration holds the project's pack work conservatively.
"""

import json
import os
import threading
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.pack_runs import pack_job, pack_state
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.state_store import pack_run_record
from owlbear_delivery_next.state_store.store import Store

KINDS = ["fifo", "directory", "link"]


def open_fds() -> set[str]:
    return {p.name for p in Path("/dev/fd").iterdir()}


def regular(root: Path) -> Path:
    path = root / pack_state.FILE
    path.write_text(json.dumps(pack_job._blank() | {"state": "failed", "reason": "the pack was refused"}))  # noqa: SLF001
    return path


def unsafe(root: Path, kind: str, tmp_path: Path) -> Path:
    path = root / pack_state.FILE
    if kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    else:
        path.symlink_to(regular(tmp_path))
    return path


def bounded(call) -> list[object]:
    """*call*'s outcome, or a failure if it waits: a reader that blocks on a pipe never returns."""
    outcome: list[object] = []

    def run() -> None:
        try:
            outcome.append(call())
        except BaseException as exc:  # noqa: BLE001 - handed to the test's own assertion
            outcome.append(exc)

    reader = threading.Thread(target=run, daemon=True)
    reader.start()
    reader.join(5)
    assert not reader.is_alive(), "the reader waited on the record"
    return outcome


@pytest.mark.parametrize("kind", KINDS)
def test_every_reader_refuses_a_record_that_is_not_a_regular_file_at_once_and_closes_it(tmp_path, kind):
    root = tmp_path / "store"
    root.mkdir()
    unsafe(root, kind, tmp_path)
    fds = open_fds()
    [opened] = bounded(lambda: pack_run_record.open_record(root / pack_state.FILE))
    assert isinstance(opened, (OSError, ValueError)), opened
    [seen] = bounded(lambda: pack_state.observed(root))
    assert isinstance(seen, (OSError, ValueError)), seen  # unreadable, never taken for no record
    assert bounded(lambda: pack_state.read_version(root / pack_state.FILE)) == [(pack_state.blank(), "")]
    assert bounded(lambda: pack_state.last(Store(root))) == [None]
    assert open_fds() == fds


def test_a_regular_record_still_reads_and_a_missing_one_is_absent(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    assert (pack_state.observed(root), pack_state.read_version(root / pack_state.FILE)[1]) == (None, "absent")
    regular(root)
    kept, version = pack_state.observed(root)
    assert (kept["reason"], version != "", pack_state.last(Store(root))) == ("the pack was refused", True, None)


@pytest.mark.parametrize("fault", ["fstat", "read"])
def test_a_fault_after_the_open_closes_the_descriptor(tmp_path, fault):
    root = tmp_path / "store"
    root.mkdir()
    regular(root)
    fds = open_fds()

    def broken(*_args: object, **_kwargs: object) -> None:
        msg = f"synthetic {fault} failure"
        raise OSError(msg)

    with pytest.MonkeyPatch.context() as patch:
        if fault == "fstat":
            patch.setattr(pack_run_record.os, "fstat", broken)
        else:
            patch.setattr(pack_run_record.json, "load", broken)
        with pytest.raises(OSError, match=f"synthetic {fault} failure"):
            pack_state.observed(root)
        assert pack_state.read_version(root / pack_state.FILE) == (pack_state.blank(), "")
    assert open_fds() == fds


@pytest.mark.parametrize("kind", KINDS)
def test_a_loaded_project_whose_record_is_not_a_regular_file_holds_its_pack_work(tmp_path, kind):
    store = Store(tmp_path / "store")
    store.root.mkdir(parents=True)
    unsafe(store.root, kind, tmp_path)
    [job] = bounded(lambda: pack_job.Job(store))
    assert (job.version, job.state["state"]) == ("", "idle")
    job.maintenance = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=lambda *_args: False)
    session_slots.interrupted(job, "p")
    assert [s["state"] for s in job.maintenance.read()["sessions"]] == ["held"]
    assert job.maintenance.slots.take("other", "probe", 1, 1) == 0


class Cancelled(BaseException):
    """Stands in for a cancellation: never an ordinary read failure."""


@pytest.mark.parametrize("fault", [OSError, ValueError, Cancelled])
def test_the_pages_reader_shows_a_failed_handover_as_unread_and_lets_a_cancellation_through(tmp_path, fault):
    root = tmp_path / "store"
    root.mkdir()
    (root / pack_state.FILE).write_text(json.dumps(pack_job._blank() | {"started_at": "2026-10-15T10:00:00+00:00"}))  # noqa: SLF001
    fds = open_fds()

    def handover(*_args: object, **_kwargs: object) -> None:
        msg = "synthetic handover failure"
        raise fault(msg)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pack_run_record.os, "fdopen", handover)
        if fault is Cancelled:
            with pytest.raises(Cancelled):
                pack_state.last(Store(root))
        else:
            assert pack_state.last(Store(root)) is None
    assert open_fds() == fds
    assert pack_state.last(Store(root))["started_at"] == "2026-10-15T10:00:00+00:00"  # control: it reads again
