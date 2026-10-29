"""A manual calibration replay holds the launch lock only at admission, so a host tick can still observe its exit."""

import contextlib
import threading
from types import SimpleNamespace

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.impeccable_runs import pack_candidate
from owlbear_delivery_next.project_host import pack_routes


def test_a_replay_runs_outside_the_launch_lock_so_a_tick_can_take_it_meanwhile(monkeypatch) -> None:
    launching = threading.Lock()
    running, release = threading.Event(), threading.Event()
    counts: list[int] = []

    @contextlib.contextmanager
    def admitted():
        with launching:
            yield

    class Live:
        def replay(self, *_args, **_kwargs):
            running.set()
            assert release.wait(5)
            return SimpleNamespace(ok=True)

    job = SimpleNamespace(
        exclusive=contextlib.nullcontext,
        count_replay=counts.append,
        live=Live(),
        keeps=None,
    )
    monkeypatch.setattr(pack_candidate, "said_replay", lambda _r: "replayed")
    routes = APIRouter()
    pack_routes._replay(routes, None, job, admitted)  # noqa: SLF001 - the route is built by the router; this is its admission
    http = TestClient(FastAPI())
    http.app.include_router(routes)

    result: dict[str, object] = {}
    worker = threading.Thread(target=lambda: result.update(r=http.post("/impeccable/replay")))
    worker.start()
    try:
        assert running.wait(5)
        assert launching.acquire(timeout=2), "a tick could not take the launch lock while the replay ran"
        launching.release()
    finally:
        release.set()
        worker.join(5)
    assert result["r"].status_code == 200
    assert counts == [1, -1]
