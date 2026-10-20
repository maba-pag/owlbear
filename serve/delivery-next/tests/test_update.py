"""Updating OwlBear on this machine (self-update build §3, §5): the alias, the standby, the fence and the handover.

The standby runs as a real process of this code; versions and installs are faked, so no environment is built.
"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import alias, app, control, handover, registry, serve, update, versions
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.versions import Choice
from owlbear_delivery_next.project_host.host import HostRecord

OLD, TOKEN = "old-token", "t"  # the hosts' tokens


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    done = subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


def legacy() -> Path:
    """The runtime as deployed by hand before the first update: a folder holding a clone."""
    runtime = local_home.root() / local_home.RUNTIME
    git(local_home.root(), "init", "-q", str(runtime))
    (runtime / "f.txt").write_text("legacy\n")
    git(runtime, "add", "-A")
    git(runtime, "commit", "-qm", "legacy")
    return runtime


def version(tag: str) -> Path:
    folder = local_home.root() / local_home.VERSIONS / tag
    folder.mkdir(parents=True)
    return folder


def test_the_first_update_swaps_the_legacy_runtime_for_a_link_and_puts_it_away():
    runtime, folder = legacy(), version("v0.2")
    commit = git(runtime, "rev-parse", "--short=12", "HEAD")

    alias.activate(folder, "v0.2")

    assert runtime.is_symlink()
    assert runtime.resolve() == folder.resolve()
    kept = local_home.root() / local_home.VERSIONS / f"legacy-{commit}"
    assert (kept / "f.txt").read_text() == "legacy\n"
    assert not (local_home.root() / alias.NEW).exists()
    assert registry.load().active == "v0.2"


def test_a_later_update_renames_a_new_link_over_the_alias_and_the_mark_never_goes_down():
    legacy()
    alias.activate(version("v0.2"), "v0.2")
    alias.activate(version("v0.3"), "v0.3")

    assert (local_home.root() / local_home.RUNTIME).resolve().name == "v0.3"
    assert registry.load().active == "v0.3"
    alias._marked("v0.2")  # noqa: SLF001 - what a start of an older alias would try
    assert registry.load().active == "v0.3"


def test_every_start_completes_a_first_migration_a_crash_interrupted():
    runtime, folder = legacy(), version("v0.2")
    new = local_home.root() / alias.NEW
    new.symlink_to(folder)
    alias._swap(new, runtime)  # noqa: SLF001 - the crash comes right after the rename

    alias.complete()

    assert runtime.resolve() == folder.resolve()
    assert not new.exists()
    assert len(list((local_home.root() / local_home.VERSIONS).glob("legacy-*"))) == 1
    assert registry.load().active == "v0.2"


def test_a_link_made_but_never_renamed_is_removed_and_the_old_runtime_stays():
    runtime = legacy()
    (local_home.root() / alias.NEW).symlink_to(version("v0.2"))

    alias.complete()

    assert not runtime.is_symlink()
    assert not (local_home.root() / alias.NEW).exists()
    assert registry.load().active == ""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_a_standby_answers_its_health_and_takes_over_with_the_old_address_token_and_state():
    """§5.2, §5.4: it takes the lock, binds the old port with the old token and keeps the paused state (TD-299)."""
    given = handover.Handover(port=free_port(), token=OLD, paused=True, ending=False, version="v9.9", loaded=[])
    standby = handover.Standby(Path(sys.executable), Path.cwd(), "v9.9", local_home.root() / "host.log")
    try:
        assert standby.healthy(30) == {"version": "v9.9", "pid": standby.proc.pid}
        handover.write(given)
        assert standby.take_over()
        assert handover.watch(given, 30)
        listed = control.projects()
        assert listed is not None
        assert (listed["paused"], listed["updated"]) == (True, "v9.9")
        rec = control.serve.running()
        assert rec is not None
        assert (rec.url, rec.token, rec.pid) == (f"http://127.0.0.1:{given.port}/", OLD, standby.proc.pid)
        assert not (local_home.root() / handover.HANDOVER).exists()
    finally:
        control.stop(lambda _s: None)
        if standby.proc.poll() is None:
            standby.proc.kill()


def test_a_standby_told_to_quit_ends_and_takes_nothing_over():
    standby = handover.Standby(Path(sys.executable), Path.cwd(), "v9.9", local_home.root() / "host.log")
    assert standby.healthy(30) is not None

    standby.stop()

    assert standby.proc.returncode == 0
    assert control.serve.running() is None


class FakeStandby:
    """A standby that answers as told, recording how it was treated."""

    health: dict | None = {}  # noqa: RUF012 - the test sets it per case
    made: list = []  # noqa: RUF012

    def __init__(self, python: Path, folder: Path, tag: str, _log: Path) -> None:
        self.python, self.folder, self.tag, self.stopped = python, folder, tag, False
        FakeStandby.made.append(self)

    def healthy(self) -> dict | None:
        return FakeStandby.health

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture
def updating(monkeypatch) -> SimpleNamespace:
    """A machine whose versions, install, standby and alias are faked: v0.2 is next."""
    said = SimpleNamespace(activated=[], stopped=0, left=[])
    folder = version("v0.2")
    monkeypatch.setattr(versions, "target", lambda: Choice("v0.2", "c2"))
    monkeypatch.setattr(versions, "install", lambda _c: folder)
    monkeypatch.setattr(handover, "Standby", FakeStandby)
    monkeypatch.setattr(alias, "activate", lambda f, t: said.activated.append((f, t)))
    FakeStandby.health, FakeStandby.made = {}, []
    record = HostRecord(url="http://127.0.0.1:4321/", token=TOKEN, pid=1, started_at=datetime.now(UTC), code="c")
    machine = Machine(record, paused=False)
    machine.on_stop = lambda: setattr(said, "stopped", said.stopped + 1)
    monkeypatch.setattr(machine, "fence", lambda text: (setattr(machine, "updating", text), said.left)[1])
    said.machine, said.folder = machine, folder
    return said


def test_an_update_with_nothing_running_activates_the_version_and_hands_over(updating):
    m = updating.machine

    m.updater._update()  # noqa: SLF001 - the thread's work, run here

    assert updating.activated == [(updating.folder, "v0.2")]
    assert updating.stopped == 1
    standby, given = m.handover
    assert (standby.tag, standby.python) == ("v0.2", updating.folder / ".venv" / "bin" / "python")
    assert given == handover.Handover(port=4321, token=TOKEN, paused=False, ending=False, version="v0.2", loaded=[])
    assert m.updater.read()["phase"] == "handing over"
    assert m.updating == update.FENCED


def test_an_update_waits_for_running_work_and_lifts_its_fence(updating):
    updating.left = ["p: c1: a running step (process 9)"]
    m = updating.machine

    m.updater._update()  # noqa: SLF001

    state = m.updater.read()
    assert (state["phase"], state["detail"]) == ("waiting", "waits for p: c1: a running step (process 9)")
    assert (m.updating, m.handover, updating.activated) == ("", None, [])
    assert FakeStandby.made[0].stopped


def test_a_standby_that_never_answers_keeps_the_running_version_and_counts_an_attempt(updating):
    FakeStandby.health = None
    m = updating.machine

    for _ in range(update.ATTEMPTS + 1):
        m.updater._update()  # noqa: SLF001

    state = m.updater.read()
    assert (state["phase"], state["detail"]) == ("failed", "v0.2 failed 3 times; a later version is tried")
    assert len(FakeStandby.made) == update.ATTEMPTS
    assert updating.activated == []


def test_run_updates_now_is_refused_while_owlbear_stops_when_idle(updating):
    m = updating.machine
    m.ending = True

    assert m.updater.run_now()["phase"] == "refused"


def test_the_fence_refuses_every_change_to_a_project_and_lets_reads_through(updating):
    m = updating.machine
    m.updating = update.FENCED
    client = TestClient(app.create(m), base_url="http://127.0.0.1")
    auth = {"authorization": f"Bearer {m.record.token}"}

    said = client.post("/p/0123456789abcdef/api/next/changes", headers=auth)
    read = client.get("/p/0123456789abcdef/api/next/changes", headers=auth)

    assert (said.status_code, said.json()) == (503, {"detail": update.FENCED})
    assert read.status_code == 404  # past the fence: no such project here


def test_a_handover_file_is_read_once():
    given = handover.Handover(port=1, token=TOKEN, paused=False, ending=True, version="v0.2", loaded=["a"])
    handover.write(given)

    assert oct((local_home.root() / handover.HANDOVER).stat().st_mode & 0o777) == "0o600"
    assert handover.taken() == given
    assert handover.taken() is None


def test_a_host_started_through_the_alias_runs_on_from_its_versions_own_folder():
    folder = version("v0.2")
    (folder / "bin").mkdir()
    link = local_home.root() / local_home.RUNTIME
    link.symlink_to(folder)

    assert alias.physical(link / "bin" / "python") == folder.resolve() / "bin" / "python"


def wait_for(check, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.1)
    return False


def test_the_standby_file_names_only_a_loopback_address_and_is_the_owners_alone():
    standby = handover.Standby(Path(sys.executable), Path.cwd(), "v9.9", local_home.root() / "host.log")
    try:
        assert standby.healthy(30) is not None
        path = local_home.root() / handover.STANDBY
        assert json.loads(path.read_text())["url"].startswith("http://127.0.0.1:")
        assert oct(path.stat().st_mode & 0o777) == "0o600"
        assert os.environ.get(handover.SECRET) is None  # the secret went to the child only
    finally:
        standby.stop()
    assert wait_for(lambda: not (local_home.root() / handover.STANDBY).exists())


def test_run_updates_now_hands_a_running_host_over_to_the_new_version_end_to_end(monkeypatch):
    """§5: the old host runs here, the new version is a real process of this code; open pages keep their address."""
    folder = version("v0.2")
    python = folder / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    python.chmod(0o755)
    monkeypatch.setattr(versions, "target", lambda: Choice("v0.2", "c2"))
    monkeypatch.setattr(versions, "install", lambda _c: folder)
    old = threading.Thread(target=serve.serve, kwargs={"run": True}, daemon=True)
    old.start()
    try:
        assert wait_for(lambda: control.projects() is not None, 30)
        before = control.serve.running()
        assert before is not None

        lines: list[str] = []
        assert control.update(lines.append, wait=90) == 0

        old.join(30)
        assert not old.is_alive()
        after = control.serve.running()
        assert after is not None
        assert (after.url, after.token) == (before.url, before.token)  # open pages keep working
        assert after.pid != os.getpid()
        listed = control.projects()
        assert listed is not None
        assert (listed["paused"], listed["updated"]) == (False, "v0.2")
        assert (local_home.root() / local_home.RUNTIME).resolve() == folder.resolve()
        assert registry.load().active == "v0.2"
        assert lines[-1] == "OwlBear now runs v0.2"
    finally:
        control.stop(lambda _s: None)
