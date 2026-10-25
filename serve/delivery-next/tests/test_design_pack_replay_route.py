"""The design pack's replay route: this host's managed job runs it, and a running update keeps it refused."""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.design_packs import calibration, design_pack
from owlbear_delivery_next.pack_runs import pack_candidate, pack_replay
from owlbear_delivery_next.project_host import pack_routes


def client(replay, lock=None):
    job = SimpleNamespace(lock=lock or threading.Lock(), keeps=lambda _path: False, live=SimpleNamespace(replay=replay))
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
    assert not job.lock.locked()
