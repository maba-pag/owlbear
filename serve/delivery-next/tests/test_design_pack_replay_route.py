"""The design pack's replay route: this host's managed job runs it, and a running update keeps it refused."""

from __future__ import annotations

import contextlib
import json
import subprocess
import threading
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.design_packs import calibration, design_pack
from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.pack_runs import pack_candidate, pack_job, pack_replay, pack_run
from owlbear_delivery_next.project_host import pack_routes, session_slots
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.state_store.store import Store


def client(replay, lock=None):
    lock = lock or threading.Lock()
    message = "a design pack update is running"

    @contextlib.contextmanager
    def exclusive():
        if not lock.acquire(blocking=False):
            raise pack_job.Busy(message)
        try:
            yield
        finally:
            lock.release()

    counts: list[int] = []
    job = SimpleNamespace(
        lock=lock,
        exclusive=exclusive,
        keeps=lambda _path: False,
        live=SimpleNamespace(replay=replay),
        count_replay=counts.append,
        counts=counts,
    )
    app = FastAPI()
    app.include_router(pack_routes.router(object(), job))
    return TestClient(app, base_url="http://127.0.0.1"), job


def test_the_replay_is_run_by_the_jobs_managed_live_and_reports_what_the_cli_prints():
    seen = []

    def replay(_store, candidate, **kwargs):
        seen.append((candidate, kwargs["keep"]))
        return calibration.replayed([])

    http, job = client(replay)
    body = http.post("/design-pack/replay").json()
    assert body["ok"] is calibration.replayed([]).ok
    assert body["report"] == f"calibration replay: {pack_candidate.said_replay(calibration.replayed([]))}"
    assert seen == [(None, job.keeps)]
    assert job.counts == [1, -1], "the replay must count in once and out once"
    assert not job.lock.locked()


def test_a_replay_while_an_update_holds_the_job_is_refused_with_409_and_runs_nothing():
    lock = threading.Lock()
    lock.acquire()
    http, _job = client(lambda *_a, **_k: pytest.fail("the replay must not start"), lock)
    assert http.post("/design-pack/replay").status_code == 409


@pytest.mark.parametrize(
    ("error", "status"),
    [(pack_replay.ReplayError("a judge may still be running"), 409), (design_pack.PackError("no pack"), 422)],
)
def test_a_failed_replay_is_refused_with_its_reason_and_releases_the_job(error, status):
    def replay(*_a, **_k):
        raise error

    http, job = client(replay)
    assert http.post("/design-pack/replay").status_code == status
    assert job.counts == [1, -1], "a failed replay must still count out"
    assert not job.lock.locked()


def legacy_host(tmp_path, state, *, updater_dir):
    """A real project host whose store holds *state* as the last run, optionally with its pre-ledger updater."""
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)  # noqa: S607
    store = Store.open(path)
    (store.root / pack_job.FILE).write_text(json.dumps(state), encoding="utf-8")
    updater = store.root / pack_run.UPDATER
    if updater_dir:
        updater.mkdir()
    slots = Slots(lambda: 1)
    host = Host(store, tmp_path / "host", spawn=lambda _s: None, scan=lambda *_a: {}, group=lambda _g: {})
    host.slots = slots
    host.maintenance = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=lambda *_args: False)
    return host, store, updater


def replay_route(host, store, live):
    job = pack_job.Job(store, live)
    session_slots.packed(host, job)
    app = FastAPI()
    app.include_router(pack_routes.router(store, job, nullcontext, host))
    return TestClient(app, base_url="http://127.0.0.1"), job


def running_legacy(stage):
    stages = [{"name": "update", "label": "Update", "result": stage, "detail": ""}]
    return {"state": "running", "stage": "update", "stages": stages, "started_at": "2026-10-24T00:00:00+00:00",
            "ended_at": None, "reason": "", "log": [], "published": None, "run": "", "loop": None,
            "questions": [], "context": None}  # fmt: skip


def recorder(calls):
    def replay(*args, **_kwargs):
        calls.append(args)
        return calibration.replayed([])

    return replay


def test_a_manual_replay_refuses_a_legacy_running_sdk_stage_with_no_pid_and_runs_no_sdk(tmp_path):
    host, store, updater = legacy_host(tmp_path, running_legacy("running"), updater_dir=True)
    calls = []
    http, job = replay_route(host, store, pack_job.Live(replay=recorder(calls)))

    refused = http.post("/design-pack/replay")

    assert calls == []
    assert refused.status_code == 409
    assert "recover" in refused.json()["detail"].lower()
    assert updater.is_dir()
    assert host.maintenance.pending(kind="pack")
    assert not job.lock.locked()


def test_a_manual_replay_runs_normally_once_no_pack_session_is_uncertain(tmp_path):
    finished = pack_job._blank() | {"state": "up-to-date", "ended_at": "2026-10-24T01:00:00+00:00"}  # noqa: SLF001
    host, store, _updater = legacy_host(tmp_path, finished, updater_dir=False)
    calls = []
    http, _job = replay_route(host, store, pack_job.Live(replay=recorder(calls)))

    assert http.post("/design-pack/replay").status_code == 200
    assert len(calls) == 1
