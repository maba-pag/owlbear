"""A manual replay waits for the last slot outside the launch lock, so a shared host's tick can observe the exit."""

import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import (
    Change,
    Exit,
    Names,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.impeccable_runs import pack_job, pack_replay
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import PACK, Slots
from owlbear_delivery_next.project_host import pack_routes, session_slots
from owlbear_delivery_next.project_host.admission import admitted
from owlbear_delivery_next.project_host.host import Host, RunnerRecord
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
WAIT = 5


class Fake:
    """Process seams: a spawned runner stays alive until the test ends it."""

    def __init__(self, store, repo, tmp_path):
        self.live, self.pid = set(), 100
        (tmp_path / "wt").mkdir(exist_ok=True)
        self.worktree = str(tmp_path / "wt")
        self.host = Host(store, repo, spawn=self.spawn, members=lambda _ids: {})
        self.host.alive = lambda pid, _created: pid in self.live

    def spawn(self, _slug):
        self.pid += 1
        self.live.add(self.pid)
        return RunnerRecord(pid=self.pid, created=1.0, started_at=NOW)


def asking(fake):
    plan = Plan(tasks=[Task(id="t1", title="greet", checks=["npm test"])])
    c = Change(slug="c1", plan=plan, step=Step(kind=StepKind.BUILD, task="t1"), names=Names(worktree=fake.worktree))
    return apply(c, StepResult(exit=Exit.ASK, question=Question(step=StepKind.BUILD, text="language?")), NOW)


def session(root):
    return sdk_adapter.Session(
        kind=StepKind.REVIEW,
        worktree=root,
        session_id="pack-replay",
        message="Replay the pack",
        resume=False,
        policy=Policy(root),
        observe=lambda: tools.Worktree("", ""),
        checks=(),
        model="synthetic-model",
    )


def wait_for(predicate) -> bool:
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def init_repo(path: Path) -> Path:
    path.mkdir()
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)  # noqa: S603, S607
    return path


def test_a_replay_waits_for_the_last_slot_and_a_shared_tick_observes_the_runner_exit(
    tmp_path, shared_repo, monkeypatch
):
    shared, _remote = shared_repo
    repo = init_repo(tmp_path / "proj")
    store = Store(repo, DataRepo(shared), "proj")
    fake = Fake(store, repo, tmp_path)
    host, slots = fake.host, Slots(lambda: 1)
    host.slots = slots
    host.maintenance = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=lambda *_a: False)
    project = session_slots.project(host)

    with store.lock("c1") as lock:
        store.write(lock, asking(fake).model_copy(update={"outcome": None}))
    assert host.tick(NOW) == ["c1"]  # the ordinary runner holds the project's last slot
    assert sum(slots.held.values()) == 1

    entered, release = [], threading.Event()

    def fake_sdk(cfg):  # the SDK boundary: the only seam replaced
        entered.append(cfg)
        assert release.wait(WAIT)
        return Run("synthetic", termination=processes.Termination(confirmed=True, problems=()))

    monkeypatch.setattr(pack_replay, "sdk_run", fake_sdk)

    def replay(_store, _candidate, run=None, **_options):  # the wrapped replay: its owned run admits and runs fake_sdk
        result = run(session(fake.worktree))
        assert result.termination.confirmed
        return SimpleNamespace(ok=True, advisory=False, rounds=3, left_out=0, before=0.5, after=0.6, pack="")

    job = pack_job.Job(store, pack_job.Live(replay=replay))
    session_slots.packed(host, job)
    http = TestClient(FastAPI())
    http.app.include_router(pack_routes.router(store, job, lambda: admitted(host), host))

    result: dict[str, object] = {}
    post = threading.Thread(target=lambda: result.update(r=http.post("/impeccable/replay")))
    post.start()
    try:
        assert wait_for(lambda: any(k[0] == project and k[1].startswith(PACK) for k in slots.waiting)), (
            "the replay did not queue for a session slot"
        )
        assert not entered

        fake.live.clear()  # the runner exits; the shared host's tick must observe it and let go of the slot
        ticked: dict[str, object] = {}
        tick = threading.Thread(target=lambda: ticked.update(launched=host.tick(NOW)))
        tick.start()
        tick.join(WAIT)
        assert not tick.is_alive(), "the shared host's tick could not observe the exit while the replay waited"
        assert not any(k[1] == "c1" for k in slots.held), "the exited runner still holds the slot"

        assert wait_for(lambda: len(entered) == 1), "the replay did not enter the SDK once its slot was free"
        assert job.busy()
        assert host.launching.acquire(timeout=2), "the replay held the launch lock while its session ran"
        host.launching.release()
    finally:
        release.set()
        post.join(WAIT)
    assert result["r"].status_code == 200
    assert len(entered) == 1
    assert not job.busy()
    assert sum(slots.held.values()) == 0


def test_a_replay_granted_its_slot_as_a_stop_begins_enters_no_sdk_and_gives_the_slot_back(
    tmp_path, shared_repo, monkeypatch
):
    shared, _remote = shared_repo
    repo = init_repo(tmp_path / "proj")
    store = Store(repo, DataRepo(shared), "proj")
    fake = Fake(store, repo, tmp_path)
    host, slots = fake.host, Slots(lambda: 1)
    host.slots = slots
    host.maintenance = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=lambda *_a: False)
    stopping = threading.Event()
    host.draining = stopping.is_set
    entered = []
    monkeypatch.setattr(pack_replay, "sdk_run", entered.append)

    take = slots.take

    def take_then_stop(*args, **kwargs):  # the stop begins right after the grant, as Machine.pause_stop does
        got = take(*args, **kwargs)
        if got:
            stopping.set()
        return got

    slots.take = take_then_stop

    def replay(_store, _candidate, run=None, **_options):
        run(session(fake.worktree))
        return SimpleNamespace(ok=True, advisory=False, rounds=3, left_out=0, before=0.5, after=0.6, pack="")

    job = pack_job.Job(store, pack_job.Live(replay=replay))
    session_slots.packed(host, job)
    http = TestClient(FastAPI())
    http.app.include_router(pack_routes.router(store, job, lambda: admitted(host), host))

    response = http.post("/impeccable/replay")

    assert stopping.is_set()
    assert response.status_code != 200, "a replay granted its slot after the stop began still ran"
    assert entered == [], "the SDK was entered after the stop began"
    assert sum(slots.held.values()) == 0, "the refused replay kept its slot"
    assert not job.busy()
