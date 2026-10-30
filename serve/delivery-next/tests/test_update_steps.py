"""An OwlBear update's ten steps and Start update now (D-01M63CCHPB2W34NM7K9NHEXFY3, D-01M63CC7CYSMN156SJEBVFAXTQ).

The updater runs the real ``versions.install`` over faked git, environment, selfcheck and pack; the standby and the
alias are faked. The takeover starts a real host through ``serve`` as the new version.
"""

import json
import socket
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import alias, app, control, handover, serve, update, update_steps, versions
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.versions import Choice
from owlbear_delivery_next.project_host.host import HostRecord

URL, TOKEN = "http://127.0.0.1:4321/", "t"  # the host's address and token
WHOLE = {"key": "looking", "label": "", "state": "done", "started_at": None, "ended_at": None, "line": ""}  # a step
RAW = "error: Failed to download `numpy==9.9`\n  Caused by: uv's own words"  # what uv says; never a step's line


class FakeStandby:
    """A standby that answers its health."""

    def __init__(self, *_args: object) -> None:
        self.stopped = False

    def healthy(self) -> dict:
        return {}

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture
def stepping(monkeypatch) -> SimpleNamespace:
    """A machine updating to v0.2 through the real install: git, uv, selfcheck and pack say what the test sets."""
    said = SimpleNamespace(check="", pack="", sync="", busy=[], activated=[])

    def git(*args: str, **_kw: object) -> str:
        if "worktree" in args and "add" in args:
            Path(args[args.index("--detach") + 1]).mkdir(parents=True)
        return ""

    def sync(folder: Path) -> None:
        if said.sync:
            msg = f"its environment could not be made: {said.sync}"
            raise versions.VersionError(msg)
        (folder / ".venv").mkdir()

    monkeypatch.setattr(versions, "_git", git)
    monkeypatch.setattr(versions, "_sync", sync)
    monkeypatch.setattr(versions, "selfcheck", lambda _f: said.check)
    monkeypatch.setattr(versions, "pack", lambda _f: said.pack)
    monkeypatch.setattr(versions, "target", lambda: Choice("v0.2", "c2c2c2c2c2c2c2c2"))
    monkeypatch.setattr(handover, "Standby", FakeStandby)
    monkeypatch.setattr(alias, "activate", lambda f, t: said.activated.append((f, t)))
    monkeypatch.setattr(update, "RECHECK", 0.0)
    record = HostRecord(url=URL, token=TOKEN, pid=1, started_at=datetime.now(UTC), code="c")
    machine = Machine(record, paused=False)
    machine.on_stop = lambda: None
    monkeypatch.setattr(machine, "busy", lambda: said.busy.pop(0) if said.busy else [])
    monkeypatch.setattr(machine, "fence", lambda text: (setattr(machine, "updating", text), [])[1])
    said.machine = machine
    return said


def states(report: dict) -> dict[str, str]:
    return {s["key"]: s["state"] for s in report["steps"]}


def kept() -> dict:
    return json.loads((local_home.root() / update_steps.RECORD).read_text())


def test_a_successful_update_reports_each_step_with_its_times_and_line_and_keeps_them_for_the_new_host(stepping):
    m = stepping.machine

    m.updater._update()  # noqa: SLF001 - the thread's work, run here

    report = m.updater.report()
    assert [s["key"] for s in report["steps"]] == [k for k, _ in update_steps.STEPS]
    assert states(report) == {k: "done" for k, _ in update_steps.STEPS} | {"handover": "running"}
    assert all(s["started_at"] and s["line"] for s in report["steps"])
    assert all(s["ended_at"] for s in report["steps"] if s["state"] == "done")
    assert report["phase"] == "handing over"  # the phases the pages read today
    assert {e["step"] for e in report["log"]} == set(states(report))
    assert (kept()["version"], kept()["steps"], kept()["log"]) == ("v0.2", report["steps"], report["log"])
    assert oct((local_home.root() / update_steps.RECORD).stat().st_mode & 0o777) == "0o600"


def test_a_failed_selfcheck_fails_its_step_with_its_last_line_and_nothing_after_it_starts(stepping):
    stepping.check = "checking the store\nits store has format 9, newer than this version's 7"
    m = stepping.machine

    m.updater._update()  # noqa: SLF001

    report = m.updater.report()
    selfcheck = next(s for s in report["steps"] if s["key"] == "selfcheck")
    assert (selfcheck["state"], selfcheck["line"]) == ("failed", "its store has format 9, newer than this version's 7")
    assert selfcheck["ended_at"]
    later = dict.fromkeys(("impeccable", "waiting", "standby", "health", "switching", "handover"), "pending")
    assert states(report) == {"looking": "done", "getting": "done", "building": "done", "selfcheck": "failed"} | later
    assert report["phase"] == "failed"
    assert stepping.activated == []


def test_a_failed_pack_install_fails_installing_its_impeccable(stepping):
    stepping.pack = "downloading the bundle\ncannot download the bundle"
    m = stepping.machine

    m.updater._update()  # noqa: SLF001

    report = m.updater.report()
    assert states(report)["selfcheck"] == "done"
    pack = next(s for s in report["steps"] if s["key"] == "impeccable")
    assert (pack["state"], pack["line"]) == ("failed", "cannot download the bundle")
    assert states(report)["waiting"] == "pending"
    assert m.impeccable.read()["install"]["state"] == "failed"  # every page still offers Install


def test_a_failed_environment_says_so_without_uvs_raw_output(stepping):
    stepping.sync = RAW
    m = stepping.machine

    m.updater._update()  # noqa: SLF001

    report = m.updater.report()
    assert states(report)["building"] == "failed"
    assert RAW.splitlines()[0] not in json.dumps(report["steps"] + report["log"])
    assert "numpy" in report["detail"]  # the phase's detail, unchanged, still names it


def test_waiting_for_running_steps_is_its_own_step_and_the_log_keeps_each_line_once(stepping):
    stepping.busy = [["p: c1: a running step (process 9)"]] * 3
    m = stepping.machine

    m.updater._update()  # noqa: SLF001

    report = m.updater.report()
    waiting = next(s for s in report["steps"] if s["key"] == "waiting")
    assert (waiting["state"], waiting["line"]) == ("done", "nothing runs")
    lines = [e["line"] for e in report["log"] if e["step"] == "waiting"]
    assert lines == ["waits for p: c1: a running step (process 9)", "nothing runs"]


def client(m: Machine) -> TestClient:
    return TestClient(app.create(m), base_url="http://127.0.0.1", headers={"authorization": f"Bearer {TOKEN}"})


def test_start_update_now_is_refused_with_its_reason_while_a_step_runs(stepping):
    m = stepping.machine
    stepping.busy = [["p: c1: a running step (process 9)"]]

    started = client(m).post("/api/next/update/start")

    said = "Work runs now: p: c1: a running step (process 9)"
    assert (started.status_code, started.json()) == (409, {"detail": said})
    assert m.updater.thread is None  # no update started, nor waits
    got = client(m).get("/api/next/update").json()  # once the step ended
    assert (got["startable"], got["reason"]) == (True, "")


def test_get_update_says_why_start_update_now_cannot_start(stepping):
    stepping.busy = [["p: c1: a check environment"]]

    got = client(stepping.machine).get("/api/next/update").json()

    assert (got["startable"], got["reason"]) == (False, "Work runs now: p: c1: a check environment")
    assert got["phase"] == "idle"


def test_work_starting_after_start_update_now_was_admitted_makes_it_wait_before_it_switches(stepping):
    m = stepping.machine
    stepping.busy = [[], ["p: c1: an Impeccable update"]]  # free at admission, busy at the update's own look

    started = client(m).post("/api/next/update/start")
    m.updater.thread.join(10)

    assert started.status_code == 200
    report = m.updater.report()
    assert "waits for p: c1: an Impeccable update" in [e["line"] for e in report["log"]]
    assert (report["phase"], len(stepping.activated)) == ("handing over", 1)


def test_run_updates_now_still_waits_for_running_steps(stepping):
    """D-01M5DW3X00A0WMHSA8WDEM9GN3: the paused bar's button is not refused; it waits."""
    m = stepping.machine
    stepping.busy = [["p: c1: a running step (process 9)"]] * 3

    ran = client(m).post("/api/next/update")
    m.updater.thread.join(10)

    assert ran.status_code == 200
    report = m.updater.report()
    assert "waits for p: c1: a running step (process 9)" in [e["line"] for e in report["log"]]
    assert report["phase"] == "handing over"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(check, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.1)
    return False


def old_host_kept(version: str) -> dict:
    """The record an old host leaves as it hands over to *version*."""
    steps = update_steps.Steps(lambda _s: None)
    steps.begin()
    steps.about(version)
    for key, _label in update_steps.STEPS[:-1]:
        steps.mark(key, "running", f"{key} began")
        steps.mark(key, "done", f"{key} ended")
    steps.mark("handover", "running", f"OwlBear hands over to {version}")
    return steps.read()


@pytest.mark.timeout(60)  # a real host starts and stops
def test_the_new_host_shows_the_old_hosts_steps_plus_its_own():
    """Through ``serve``'s start of the new host, which reads the record its old host kept about it."""
    before = old_host_kept("v0.2")
    handover.write(handover.Handover(port=free_port(), token=TOKEN, paused=True, ending=False, version="v0.2",
                                     loaded=[]))  # fmt: skip
    host = threading.Thread(target=serve.serve, kwargs={"handing": True}, daemon=True)
    host.start()
    try:
        assert wait_for(lambda: control.projects() is not None)
        got = control._api("update")  # noqa: SLF001 - the page's read, with the host's token
        assert got is not None
    finally:
        control._api("stop", "POST")  # noqa: SLF001 - the stop route: a signal would end this test's own process
        host.join(30)
    assert not host.is_alive()
    own = {"state": "done", "line": "v0.2 took over at the same address; 0 of 0 projects loaded"}
    last = got["steps"][-1]
    assert (last["key"], {k: last[k] for k in own}) == ("handover", own)
    assert got["steps"][:-1] == before["steps"][:-1]
    assert got["log"] == [*before["log"], {"at": got["log"][-1]["at"], "step": "handover", "line": own["line"]}]
    assert got["phase"] == "idle"  # the pages read no update as running


@pytest.mark.parametrize("record", ["v0.1", None])
def test_a_record_about_another_version_or_none_leaves_the_new_hosts_handover_alone(record):
    if record:
        old_host_kept(record)
    else:
        (local_home.root() / update_steps.RECORD).unlink(missing_ok=True)
    updater = update.Updater(SimpleNamespace(say=lambda _s: None, updated="v0.2", projects={}))

    updater.took_over([])  # what serve calls once the new host is up

    got = updater.read() | updater.steps.read()
    line = "v0.2 took over at the same address; 0 of 0 projects loaded"
    assert [(s["key"], s["state"], s["line"]) for s in got["steps"]] == [("handover", "done", line)]
    assert [e["line"] for e in got["log"]] == [line]
    assert got["phase"] == "idle"


@pytest.mark.parametrize(
    "malformed",
    [
        {"steps": [{"key": "handover"}]},
        {"log": [{"step": "looking"}]},
        {"steps": [{"key": "looking", "line": 7}]},
        {"steps": [WHOLE | {"key": ["handover"]}]},
        {"steps": [WHOLE | {"key": {"handover": 1}}]},
        {"log": [{"at": "2026-10-29T12:00:00+00:00", "step": "nowhere", "line": "a line"}]},
    ],
)
def test_a_malformed_record_is_read_as_absent_and_the_new_host_still_ends_its_handover(malformed):
    steps = update_steps.Steps(lambda _s: None)
    steps.begin()
    steps.about("v0.2")
    steps.mark("looking", "done", "v0.2 is newer")
    body = kept() | malformed
    (local_home.root() / update_steps.RECORD).write_text(json.dumps(body))

    steps.took_over("v0.2", "done", "v0.2 took over")

    assert [(s["key"], s["state"]) for s in steps.read()["steps"]] == [("handover", "done")]
