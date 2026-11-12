"""Unreadable ownership is never absence; each reader closes only the descriptors it owns."""

import json
import os
import threading
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.impeccable_runs import pack_job, pack_state
from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.state_store import pack_run_record
from owlbear_delivery_next.state_store.store import Store


@pytest.fixture
def record_fds(monkeypatch):
    opened, active, closed, files = [], set(), [], []

    def capture(path, flags, *args, **kwargs):
        fd = os.open(path, flags, *args, **kwargs)
        opened.append(fd)
        active.add(fd)
        assert flags & os.O_NOFOLLOW
        assert flags & os.O_NONBLOCK
        return fd

    def close(fd):
        assert fd in active
        os.close(fd)
        active.remove(fd)
        closed.append(fd)

    def fdopen(fd, *args, **kwargs):
        source = os.fdopen(fd, *args, **kwargs)
        assert fd in active
        active.remove(fd)
        files.append(source)
        return source

    monkeypatch.setattr(
        pack_run_record, "os", SimpleNamespace(**(vars(os) | {"open": capture, "close": close, "fdopen": fdopen}))
    )
    yield opened
    assert not active
    assert len(opened) == len(closed) + len(files)
    assert all(source.closed for source in files)


def regular(root):
    path = root / pack_state.FILE
    path.write_text(
        json.dumps(
            pack_state.blank()
            | {"state": "failed", "reason": "the pack was refused", "started_at": "2026-10-15T10:00:00+00:00"}
        )
    )
    return path


def bounded(call):
    """Only the FIFO needs a bounded worker to distinguish refusal from a blocking open."""
    outcome = []

    def run():
        try:
            call()
        except BaseException as exc:  # noqa: BLE001 - handed to the test's assertion
            outcome.append(exc)

    reader = threading.Thread(target=run, daemon=True)
    reader.start()
    reader.join(5)
    assert not reader.is_alive(), "the reader waited on the pipe"
    assert outcome == []


@pytest.mark.parametrize("kind", ["fifo", "directory", "link"])
def test_nonregular_record_is_unreadable_and_holds_work(tmp_path, record_fds, kind):
    root = tmp_path / "store"
    root.mkdir()
    path = root / pack_state.FILE
    if kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    else:
        path.symlink_to(regular(tmp_path))

    def read_and_restore():
        for read in (lambda: pack_run_record.open_record(path), lambda: pack_state.observed(root)):
            with pytest.raises((OSError, ValueError)):
                read()
        assert pack_state.read_version(path) == (pack_state.blank(), "")
        assert pack_state.last(Store(root)) is None
        job = pack_job.Job(Store(root))
        assert (job.version, job.state["state"]) == ("", "idle")
        job.maintenance = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=lambda *_a: False)
        session_slots.interrupted(job, "p")
        assert [s["state"] for s in job.maintenance.read()["sessions"]] == ["held"]
        assert job.maintenance.slots.take("other", "probe", 1, 1) == 0

    if kind == "fifo":
        bounded(read_and_restore)
    else:
        read_and_restore()
    if kind != "link":
        assert record_fds


def test_regular_missing_and_malformed_record_contracts(tmp_path):
    assert (pack_state.observed(tmp_path), pack_state.read_version(tmp_path / pack_state.FILE)[1]) == (None, "absent")
    path = regular(tmp_path)
    kept, version = pack_state.observed(tmp_path)
    assert kept["reason"] == "the pack was refused"
    assert version
    assert pack_state.last(Store(tmp_path))["started_at"] == kept["started_at"]
    path.write_text("{")
    with pytest.raises(ValueError, match="Expecting"):
        pack_state.observed(tmp_path)
    with pytest.raises(ValueError, match="Expecting"):
        pack_run_record.settle(tmp_path, receipted=lambda _d: "")
    assert pack_state.read_version(path) == (pack_state.blank(), "")
    assert path.read_text() == "{"


class Cancelled(BaseException):
    """Cancellation must propagate, unlike an ordinary read failure."""


@pytest.mark.parametrize(
    ("boundary", "error"),
    [
        ("fstat", OSError),
        ("decode", OSError),
        ("handover", OSError),
        ("handover", ValueError),
        ("handover", Cancelled),
    ],
    ids=["fstat", "decode", "handover-os", "handover-value", "handover-cancellation"],
)
@pytest.mark.usefixtures("record_fds")
def test_record_descriptor_closes_on_failure_and_cancellation(tmp_path, monkeypatch, boundary, error):
    regular(tmp_path)

    def broken(*_args, **_kwargs):
        msg = "synthetic reader failure"
        raise error(msg)

    with monkeypatch.context() as patch:
        target, name = {
            "fstat": (pack_run_record.os, "fstat"),
            "decode": (pack_run_record.json, "load"),
            "handover": (pack_run_record.os, "fdopen"),
        }[boundary]
        patch.setattr(target, name, broken)
        with pytest.raises(error, match="synthetic reader failure"):
            pack_state.observed(tmp_path)
        if error is Cancelled:
            with pytest.raises(Cancelled):
                pack_state.last(Store(tmp_path))
        else:
            assert pack_state.read_version(tmp_path / pack_state.FILE) == (pack_state.blank(), "")
            if boundary != "fstat":
                assert pack_state.last(Store(tmp_path)) is None
    assert pack_state.last(Store(tmp_path))["started_at"] == "2026-10-15T10:00:00+00:00"


def test_legacy_stages_survive_without_invented_history(tmp_path):
    results = ["passed"] * 6 + ["running"] + ["pending"] * 4
    stages = [
        {"name": n, "label": label, "result": result, "detail": ""}
        for (n, label), result in zip(pack_state.STAGES, results, strict=True)
    ]
    record = pack_state.blank() | {
        "state": "running",
        "stage": "challenger",
        "stages": stages,
        "run": "r0",
        "started_at": "2026-10-15T10:00:00+00:00",
    }
    (tmp_path / pack_state.FILE).write_text(json.dumps(record))
    state = pack_job.Job(Store(tmp_path), pack_job.Live()).read()
    assert "invocations" not in state
    assert state["progress"] == {"legacy": True, "phases": [], "now": None, "next": None}
    assert [s["result"] for s in state["stages"]] == ["passed"] * 6 + ["failed"] + ["not-reached"] * 4
