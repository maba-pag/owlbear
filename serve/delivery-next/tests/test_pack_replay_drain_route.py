"""A calibration replay through the public route waits for a slot; a drain cancels the wait and leaves nothing."""

import contextlib
import dataclasses
import fcntl
import os
import threading
import time
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.impeccable_runs import pack_job
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import pack_routes, session_slots
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store import machine_settings
from owlbear_delivery_next.state_store.store import Store


class Replay:
    """The live replay boundary: it enters its owned run the way the real replay does, before any SDK work."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _store, _candidate, run, *, keep=None):  # noqa: ARG002 - the signature the wrapper calls
        self.calls += 1
        return run(None)  # admission refuses before the session's config is read


def make_host(store: Store, total: int) -> SimpleNamespace:
    drain = threading.Event()
    return SimpleNamespace(
        record=SimpleNamespace(project="shop"),
        store=store,
        slots=Slots(total=lambda: total),
        closed=lambda: False,
        stopped=threading.Event(),
        draining=drain.is_set,
        drain=drain,
        launching=threading.Lock(),
        maintenance=SimpleNamespace(pending=lambda **_kw: False, owns=lambda _w: False),
    )


def drain_once_the_session_waits(host: SimpleNamespace) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if any(key[1].startswith(session_slots.PACK) for key in [*host.slots.waiting, *host.slots.held]):
            host.drain.set()
            return
        time.sleep(0.005)
    host.drain.set()  # the wait never began: release the route so the test fails rather than hangs


def route_waiting_for_a_slot(tmp_path, monkeypatch, *, honours_drain: bool) -> SimpleNamespace:
    """Post a calibration replay with capacity unset and a drain mid-wait; the emergency stop is a bounded rescue."""
    monkeypatch.setattr(session_slots, "WAIT", 0.01)
    monkeypatch.setattr(config, "BASE", None)  # sessions at once is unset on this machine, as on a fresh install
    monkeypatch.setattr(machine_settings, "BASE", None)
    sdk_entries: list[object] = []
    monkeypatch.setattr(session_slots.maintained, "run_owned", lambda *a, **_kw: sdk_entries.append(a))
    store = Store(tmp_path / "store")
    store.name = "shop"
    host = make_host(store, total=5)
    if not honours_drain:
        host.draining = lambda: False  # fixture-only stand-in for a wait that ignores a drain
    assert session_slots.limit(host) == 0  # sessions at once is unset: nothing is granted

    replay = Replay()
    job = pack_job.Job(store)
    job.live = dataclasses.replace(job.live, replay=replay)
    session_slots.packed(host, job)

    app = FastAPI()
    app.include_router(pack_routes.router(store, job, contextlib.nullcontext, host))
    rescued = threading.Event()
    rescue = threading.Timer(2.0, lambda: (rescued.set(), host.stopped.set()))  # emergency: the existing stop path
    rescue.start()
    drainer = threading.Thread(target=drain_once_the_session_waits, args=(host,))
    drainer.start()
    started = time.monotonic()
    try:
        response = TestClient(app).post("/impeccable/replay")
    finally:
        rescue.cancel()
        drainer.join(10)
    elapsed = time.monotonic() - started

    probe = os.open(pack_job.local_home.root() / pack_job.MACHINE_LOCK, os.O_RDWR)
    try:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        machine_free = True
    except BlockingIOError:
        machine_free = False
    finally:
        os.close(probe)
    return SimpleNamespace(
        response=response,
        rescued=rescued.is_set(),
        elapsed=elapsed,
        replay=replay,
        sdk_entries=sdk_entries,
        job=job,
        host=host,
        machine_free=machine_free,
    )


def test_a_public_replay_waiting_for_a_slot_is_cancelled_by_a_drain_and_leaves_nothing_behind(tmp_path, monkeypatch):
    out = route_waiting_for_a_slot(tmp_path, monkeypatch, honours_drain=True)

    assert not out.rescued, "the emergency stop ended the wait: the drain did not"
    assert out.response.status_code == 422
    assert "did not get a session slot" in out.response.json()["detail"]
    assert out.elapsed < 10, "the refused wait did not end in bounded time"
    assert out.replay.calls == 1
    assert out.sdk_entries == []  # no SDK entry
    assert out.job.replays == 0  # the busy count is back to zero
    assert not out.job.busy()
    assert out.job.held is None
    assert out.host.slots.waiting == {}
    assert out.host.slots.held == {}  # the waiter's claim was cancelled
    assert out.host.slots.counts("shop")[2] == 0
    assert out.machine_free


def test_a_wait_that_ignores_a_drain_is_rescued_by_a_stop_and_still_cleans_up(tmp_path, monkeypatch):
    out = route_waiting_for_a_slot(tmp_path, monkeypatch, honours_drain=False)

    assert out.rescued, "the wait ended without the emergency stop: the drain control did not run"
    assert out.response.status_code == 422
    assert "OwlBear stops" in out.response.json()["detail"]
    assert out.elapsed < 10
    assert out.sdk_entries == []
    assert out.job.replays == 0
    assert not out.job.busy()
    assert out.host.slots.waiting == {}
    assert out.host.slots.held == {}
    assert out.host.slots.counts("shop")[2] == 0
    assert out.machine_free
