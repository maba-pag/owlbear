"""Updating OwlBear on this machine (self-update build §3, §5): the alias, the standby, the fence and the handover.

The standby runs as a real process of this code; versions and installs are faked, so no environment is built.
"""

import hashlib
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

from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.local_system import leases, local_home, processes
from owlbear_delivery_next.machine_host import alias, app, control, handover, packs, serve, update, versions
from owlbear_delivery_next.machine_host.machine import Machine, MachineError
from owlbear_delivery_next.machine_host.versions import Choice
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import registry

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


def test_an_update_waits_for_running_work_then_goes_on_and_lifts_its_fence_for_work_that_slipped_in(
    updating, monkeypatch
):
    """TD-353: Run updates now waits for running steps; work found under the fence lifts it and it waits again."""
    m = updating.machine
    busy = [["p: c1: a running step (process 9)"], [], []]
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(m, "busy", lambda: busy.pop(0))
    monkeypatch.setattr(update, "RECHECK", 0.0)
    fences = [["p: c2: a check environment"], []]
    monkeypatch.setattr(m, "fence", lambda text: (setattr(m, "updating", text), fences.pop(0))[1])
    said = m.updater._set  # noqa: SLF001
    monkeypatch.setattr(m.updater, "_set", lambda phase, detail="", version=None: (
        seen.append((phase, detail)), said(phase, detail, version)))  # fmt: skip

    m.updater._update()  # noqa: SLF001

    assert ("waiting", "waits for p: c1: a running step (process 9)") in seen
    assert [p for p, _ in seen].count("standby") == 2  # the first standby stopped when the fence found work
    assert FakeStandby.made[0].stopped
    assert not FakeStandby.made[1].stopped
    assert updating.activated == [(updating.folder, "v0.2")]
    assert m.updater.read()["phase"] == "handing over"


def test_a_stop_when_idle_asked_for_while_an_update_waits_cancels_it(updating, monkeypatch):
    m = updating.machine

    def busy() -> list[str]:
        m.ending = True
        return ["p: c1: a running step (process 9)"]

    monkeypatch.setattr(m, "busy", busy)
    monkeypatch.setattr(update, "RECHECK", 0.0)

    m.updater._update()  # noqa: SLF001

    state = m.updater.read()
    assert (state["phase"], state["detail"]) == ("refused", "OwlBear stops once the running steps end")
    assert (m.updating, m.handover, updating.activated) == ("", None, [])


def test_a_project_is_neither_registered_adopted_nor_removed_while_the_fence_holds(updating, tmp_path):
    m = updating.machine
    m.updating = update.FENCED

    with pytest.raises(MachineError, match="OwlBear is updating"):
        m.register(tmp_path)


def test_a_standby_that_never_answers_keeps_the_running_version_and_counts_an_attempt(updating):
    FakeStandby.health = None
    m = updating.machine

    for _ in range(update.ATTEMPTS + 1):
        m.updater._update()  # noqa: SLF001

    state = m.updater.read()
    assert (state["phase"], state["detail"]) == ("failed", "v0.2 failed 3 times; a later version is tried")
    assert len(FakeStandby.made) == update.ATTEMPTS
    assert updating.activated == []


def pinned_pack(monkeypatch) -> None:
    """The running version pins a pack whose downloads come from here: ``engine`` and ``bundle``."""
    pins = design_pack.manifest()
    pins["engine"][design_pack.platform_name()] = hashlib.sha256(b"engine").hexdigest()
    pins["bundle"]["sha256"] = hashlib.sha256(b"bundle").hexdigest()
    monkeypatch.setattr(design_pack, "manifest", lambda: json.loads(json.dumps(pins)))
    monkeypatch.setattr(design_pack, "fetch", lambda url, _s=0: b"engine" if "releases" in url else b"bundle")


def test_a_version_whose_pack_failed_is_not_activated_and_every_page_offers_install_also_after_a_restart(
    updating, monkeypatch
):
    pinned_pack(monkeypatch)
    design_pack.install()  # the running version's own pack stays in place throughout

    def install(_choice: Choice) -> Path:
        msg = "v0.2's design pack could not be installed: cannot download"
        raise versions.PackInstallError(msg)

    monkeypatch.setattr(versions, "install", install)
    m = updating.machine

    m.updater._update()  # noqa: SLF001

    assert (updating.activated, m.handover, FakeStandby.made) == ([], None, [])
    failed = m.packs.read()["install"]
    assert (failed["state"], failed["version"]) == ("failed", "v0.2")
    assert "cannot download" in failed["detail"]

    restarted = Machine(m.record, paused=False)  # a new host over the same home
    assert restarted.packs.read()["install"] == failed
    packed: list[Path] = []
    monkeypatch.setattr(versions, "pack", lambda folder: packed.append(folder) or "")
    restarted.packs.install()
    restarted.packs.thread.join(10)
    assert (packed, restarted.packs.read()["install"]) == ([updating.folder], None)
    assert Machine(m.record).packs.read()["install"] is None  # ended for good

    (local_home.root() / design_pack.PACKS / packs.FAILED).write_text("{not json")
    unreadable = Machine(m.record).packs.read()["install"]
    assert (unreadable["state"], unreadable["version"]) == ("failed", "")
    assert "is unreadable" in unreadable["detail"]


def test_install_puts_a_missing_pack_in_place_with_no_newer_version(updating, monkeypatch):
    pinned_pack(monkeypatch)
    monkeypatch.setattr(versions, "target", lambda: None)
    m = updating.machine
    client = TestClient(app.create(m), base_url="http://127.0.0.1")
    auth = {"authorization": f"Bearer {TOKEN}"}
    m.updater._update()  # noqa: SLF001
    assert m.updater.read()["phase"] == "current"
    assert client.get("/api/next/projects", headers=auth).json()["pack"]["install"]["state"] == "missing"

    assert client.post("/api/next/design-pack/install", headers=auth).status_code == 200
    m.packs.thread.join(10)

    assert client.get("/api/next/design-pack", headers=auth).json()["install"] is None
    assert design_pack.installed() is not None


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

    assert leases.physical(link / "bin" / "python") == folder.resolve() / "bin" / "python"


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


@pytest.mark.timeout(120)  # two real hosts start and hand over; its own waits allow more than a loaded CI's 30 s
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


def test_a_standby_that_does_not_take_over_is_ended_and_the_version_restarts_forward_with_the_handover(
    updating, monkeypatch
):
    """§5.5, TD-305: the forward restart takes over the old address and state; never the older version."""
    started: list[list[str]] = []
    monkeypatch.setattr(serve.subprocess, "Popen", lambda argv, **_kw: started.append(argv))
    standby = SimpleNamespace(take_over=lambda: False, killed=False)
    standby.kill = lambda: setattr(standby, "killed", True)
    given = handover.Handover(port=4321, token=TOKEN, paused=False, ending=True, version="v0.2", loaded=[])

    serve._handed(updating.machine, standby, given)  # noqa: SLF001

    assert standby.killed
    python = local_home.root() / local_home.RUNTIME / ".venv" / "bin" / "python"
    assert started == [[str(python), "-m", "owlbear_delivery_next", "machine", "--takeover"]]
    assert handover.taken() == given


def test_a_process_of_an_installed_version_holds_a_lease_until_it_ends():
    folder = version("v0.2")
    python = folder / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)

    lease = leases.take(python)

    assert lease is not None
    assert lease.parent == folder / leases.LEASES
    assert leases.held(folder) == [os.getpid()]
    assert leases.take(Path(sys.executable)) is None  # a developer checkout holds none
    lease.rename(lease.with_name(f"{2**22 + 1}-1.0"))  # its process is gone
    assert leases.held(folder) == []
    assert not list((folder / leases.LEASES).iterdir())


def test_a_version_goes_once_two_newer_ones_were_active_and_no_lease_holds_it(monkeypatch):
    removed: list[str] = []
    monkeypatch.setattr(versions, "remove", lambda p: removed.append(p.name))
    for tag in ("v0.1", "v0.2", "v0.3", "v0.4"):
        (version(tag) / versions.ACTIVATED).touch()
    (local_home.root() / local_home.RUNTIME).symlink_to(local_home.root() / local_home.VERSIONS / "v0.4")
    held = local_home.root() / local_home.VERSIONS / "v0.2" / leases.LEASES
    held.mkdir()
    (held / f"{os.getpid()}-{processes.started(os.getpid())!r}").touch()

    assert versions.prune() == ["v0.1"]  # v0.2 is held; v0.3 has one newer; v0.4 runs
    assert removed == [".v0.1-removing"]  # renamed first: a process starting from it now finds nothing
    assert not (local_home.root() / local_home.VERSIONS / "v0.1").exists()


def test_the_old_runtime_is_removed_only_on_the_owners_word():
    runtime = legacy()
    alias.activate(version("v0.3"), "v0.3")
    record = HostRecord(url="http://127.0.0.1:4321/", token=TOKEN, pid=1, started_at=datetime.now(UTC), code="c")
    client = TestClient(app.create(Machine(record)), base_url="http://127.0.0.1")
    auth = {"authorization": f"Bearer {TOKEN}"}
    kept = versions.legacy()
    assert len(kept) == 1
    assert client.get("/api/next/machine", headers=auth).json()["legacy"] == [str(kept[0])]

    said = client.post("/api/next/machine/legacy/remove", headers=auth)

    assert (said.status_code, said.json()["legacy"]) == (200, [])
    assert not kept[0].exists()
    assert runtime.resolve().name == "v0.3"


def test_the_old_runtime_stays_while_a_process_still_runs_it(monkeypatch):
    legacy()
    alias.activate(version("v0.3"), "v0.3")
    monkeypatch.setattr(leases, "unpinned", lambda: [4242])
    record = HostRecord(url="http://127.0.0.1:4321/", token=TOKEN, pid=1, started_at=datetime.now(UTC), code="c")
    client = TestClient(app.create(Machine(record)), base_url="http://127.0.0.1")

    said = client.post("/api/next/machine/legacy/remove", headers={"authorization": f"Bearer {TOKEN}"})

    assert said.status_code == 409
    assert "processes 4242 still run it" in said.json()["detail"]
    assert "Stop Server" in said.json()["detail"]
    assert "reload the VS Code" not in said.json()["detail"]
    assert len(versions.legacy()) == 1


def test_a_process_started_through_the_alias_and_never_pinned_is_found():
    runtime = version("v0.3")
    (local_home.root() / local_home.RUNTIME).symlink_to(runtime)
    sleeper = local_home.root() / local_home.RUNTIME / "sleep.py"
    sleeper.write_text("import time\ntime.sleep(30)\n")
    proc = subprocess.Popen([sys.executable, str(sleeper)])  # noqa: S603 - this interpreter and a test script
    try:
        assert wait_for(lambda: proc.pid in leases.unpinned())
    finally:
        proc.kill()
        proc.wait()
    assert proc.pid not in leases.unpinned()
