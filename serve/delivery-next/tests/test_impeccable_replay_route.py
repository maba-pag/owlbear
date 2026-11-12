"""Impeccable's replay route: this host's managed job runs it, and a running update keeps it refused."""

from __future__ import annotations

import contextlib
import json
import subprocess
import threading
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.impeccable import calibration, pack_files
from owlbear_delivery_next.impeccable_runs import pack_candidate, pack_job, pack_replay, pack_run
from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import pack_routes, session_slots
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.state_store.store import Store


def client(replay, lock=None):
    lock = lock or threading.Lock()
    message = "an Impeccable update is running"

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
    store = SimpleNamespace(name="shop", root=Path("/nonexistent/shop"))  # the router names its own project
    app.include_router(pack_routes.router(store, job))
    return TestClient(app, base_url="http://127.0.0.1"), job


def test_managed_replay_and_legacy_routes_count_once_and_redirect_reads():
    seen = []

    def replay(_store, candidate, **kwargs):
        seen.append((_store.name, candidate, kwargs["keep"]))
        return calibration.replayed([])

    http, job = client(replay)
    body = http.post("/impeccable/replay").json()
    assert body["ok"] is calibration.replayed([]).ok
    assert body["report"] == f"calibration replay: {pack_candidate.said_replay(calibration.replayed([]))}"
    assert seen == [("shop", None, job.keeps)]
    assert job.counts == [1, -1], "the replay must count in once and out once"
    assert not job.lock.locked()
    seen.clear()
    job.counts.clear()
    assert http.post("/design-pack/replay").json()["ok"] is calibration.replayed([]).ok
    assert (seen, job.counts) == ([("shop", None, job.keeps)], [1, -1])
    assert not job.lock.locked()
    for old, new in (("/design-pack", "/impeccable"), ("/design-pack/update?x=1", "/impeccable/update?x=1")):
        moved = http.get(old, follow_redirects=False)
        assert (moved.status_code, moved.headers["location"]) == (307, f"http://127.0.0.1{new}")


@pytest.mark.parametrize("fails", ["busy", "replay", "pack", "noted", "command"])
def test_replay_refusals_release_job_and_preserve_whole_reason(caplog, whole_error, fails) -> None:
    if fails == "busy":
        lock = threading.Lock()
        lock.acquire()
        http, job = client(lambda *_a, **_k: pytest.fail("the replay must not start"), lock)
        try:
            assert http.post("/impeccable/replay").status_code == 409
            assert job.counts == []
        finally:
            lock.release()
        return
    status, message, trace = 422, "failed", True
    if fails in {"replay", "pack"}:
        broke = (
            pack_replay.ReplayError("a judge may still be running")
            if fails == "replay"
            else (pack_files.PackError("no pack"))
        )
        if fails == "replay":
            status, message, trace, said = 409, "refused", False, str(broke)
        else:
            said = f"PackError: {broke}"
    elif fails == "noted":
        broke = OSError(whole_error)
        broke.add_note(f"the session's teardown also failed: OSError: {whole_error}")  # as loop_owner.run adds it
        said = f"OSError: {whole_error}\nthe session's teardown also failed: OSError: {whole_error}"
    else:
        broke = subprocess.CalledProcessError(1, ["git", "worktree", "add"], "", whole_error)
        said = (
            f"CalledProcessError: Command '['git', 'worktree', 'add']' returned non-zero exit status 1.\n{whole_error}"
        )

    def replay(*_a, **_k):
        raise broke

    http, job = client(replay)
    answer = http.post("/impeccable/replay")
    assert (answer.status_code, answer.json()) == (status, {"detail": said})
    logged = [(r.levelname, r.getMessage(), bool(r.exc_info)) for r in caplog.records if r.name == pack_routes.__name__]
    assert logged == [("WARNING", f"calibration replay {message}: {said}", trace)]
    assert job.counts == [1, -1]
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
    host = Host(store, tmp_path / "host", spawn=lambda _s: None, members=lambda _ids: {})
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

    refused = http.post("/impeccable/replay")

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

    assert http.post("/impeccable/replay").status_code == 200
    assert len(calls) == 1
