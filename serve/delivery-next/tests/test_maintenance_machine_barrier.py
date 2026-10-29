"""Review 4373338535: a returned but unconfirmed Impeccable session keeps the machine's update and stop waiting.

Its job is no longer busy once the SDK returns, so only the machine's ledger still knows the session: an update, an
automatic update, a stop when idle and the page's list of what is left must read it there, whether its project is
loaded, failed or removed, until its processes are positively confirmed gone or the owner recovers it after a reboot.
"""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.impeccable_runs import pack_job
from owlbear_delivery_next.local_system import codebase, processes
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import UNPROVEN_PACK, Machine
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import registry


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    return path.resolve()


@pytest.fixture
def machine(monkeypatch):
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    now = datetime.now(UTC)
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=now, code=codebase.CURRENT)  # noqa: S106
    m = Machine(record)
    m.maintenance.observe = lambda _pid, _created: True  # synthetic: the session's process is still there
    yield m
    m.stop_all()


@pytest.fixture
def http(machine):
    served = app.create(machine)
    return TestClient(served, base_url="http://127.0.0.1", headers={"authorization": served.expected.decode()})


def session(root: Path) -> sdk_adapter.Session:
    return sdk_adapter.Session(
        kind=StepKind.REVIEW,
        worktree=root,
        session_id="pack-update",
        message="Update the pack",
        resume=False,
        policy=Policy(root),
        observe=lambda: tools.Worktree("", ""),
        checks=(),
        model="synthetic-model",
    )


IDENTIFIED = Run(  # its one process is identified by PID and birth, and survived the session's end
    "synthetic",
    ending="result",
    runtime_pid=4242,
    pids={4242: 1.0},
    termination=processes.Termination(confirmed=False, survivors=(4242,)),
)
UNIDENTIFIED = Run(  # the SDK returned, but nothing proves which processes it started
    "synthetic", ending="result", termination=processes.Termination(confirmed=False, problems=("request task pending",))
)


def returned_unconfirmed(tmp_path: Path, machine: Machine, run: Run) -> registry.Project:
    """A loaded project's real pack job whose update session the SDK returned from without confirming its end."""
    entry = registry.register(clone(tmp_path / "a"))
    machine.slots.total = lambda: 2
    machine.load_all()
    loaded = machine.projects[entry.id]
    job = session_slots.packed(loaded.host, pack_job.Job(loaded.store, pack_job.Live(update=lambda _s, _cfg: run)))
    (root := tmp_path / "wt").mkdir()
    assert job.live.update(loaded.store, session(root)) is run
    assert (job.busy(), loaded.working(stopping=True)) == (False, [])  # the job and its project no longer count it
    return entry


def waiting_for(name: str) -> list[str]:
    return [f"{name}: {UNPROVEN_PACK}"]


@pytest.mark.parametrize("run", [IDENTIFIED, UNIDENTIFIED], ids=["identified", "unidentified"])
def test_a_returned_unconfirmed_pack_session_keeps_the_update_and_the_stop_waiting_after_its_project_goes(
    tmp_path, machine, http, run
):
    entry = returned_unconfirmed(tmp_path, machine, run)
    stopped: list[bool] = []
    machine.on_stop = lambda: stopped.append(True)
    assert machine.busy() == waiting_for("a")  # an update and an automatic update wait for it
    assert machine.fence("synthetic update") == waiting_for("a")
    machine.unfence()
    assert http.post("/api/next/pause-stop").json() == {"paused": True, "ending": True}
    assert http.get("/api/next/projects").json()["left"] == waiting_for("a")
    assert (machine.idle_stop(), stopped) == (False, [])

    assert http.delete(f"/api/next/projects/{entry.id}").json() == {"removed": entry.id}  # no project is loaded now
    assert (machine.projects, machine.left(), machine.busy()) == ({}, waiting_for(entry.id), waiting_for(entry.id))
    assert (machine.idle_stop(), stopped) == (False, [])

    machine.maintenance.observe = lambda _pid, _created: False  # every process it could have is gone
    if run is UNIDENTIFIED:  # absence of unidentified processes proves nothing: only a recovery after a reboot does
        assert (machine.busy(), machine.idle_stop()) == (waiting_for(entry.id), False)
        [held] = machine.maintenance.read()["sessions"]
        booted = machine.maintenance.boot
        machine.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the session
        machine.maintenance.recover(held["id"], rebooted=True)
    assert (machine.busy(), machine.left(), machine.idle_stop(), stopped) == ([], [], True, [True])
    [ended] = machine.maintenance.read()["sessions"]
    assert ended["state"] == ("released" if run is IDENTIFIED else "recovered")
