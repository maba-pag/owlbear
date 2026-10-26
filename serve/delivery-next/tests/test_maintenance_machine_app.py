"""The machine's maintenance sessions stay visible and recoverable by its owner when no project store can serve them."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import app, curation, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import registry

CHAT_USE = {chat_contract.HEADER: str(chat_contract.CHAT), "x-owlbear-use": "chat"}


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    return path.resolve()


@pytest.fixture
def machine(monkeypatch):
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    record = HostRecord(
        url="http://127.0.0.1:9/",
        token="t",  # noqa: S106
        pid=1,
        started_at=datetime.now(UTC),
        code=codebase.CURRENT,
    )
    m = Machine(record)
    yield m
    m.stop_all()


@pytest.fixture
def http(machine):
    served = app.create(machine)  # the machine's own app, whose owner token is the Dispatcher's expected value
    return TestClient(served, base_url="http://127.0.0.1", headers={"authorization": served.expected.decode()})


def global_curation_hold(machine):
    """The machine-wide curation run an older host left uncertain: a lease under the curation slot, no project."""
    return machine.maintenance.adopt_uncertain("curation:legacy-run", curation.SLOT, "curation", workspace="")


def assert_recoverable_by_its_owner_only(machine, http, lease) -> None:
    sessions = http.get("/api/next/maintenance/sessions")
    assert sessions.status_code == 200, sessions.text
    assert [(s["id"], s["state"]) for s in sessions.json()["sessions"]] == [(lease.id, "held")]

    path = f"/api/next/maintenance/sessions/{lease.id}/recover"
    assert http.post(path, json={"rebooted": True}, headers={**dict(http.headers), **CHAT_USE}).status_code == 403
    assert http.post(path, json={"rebooted": False}).status_code == 400
    assert http.post(path, json={"rebooted": True}).status_code == 409  # no reboot since the hold: refused
    assert http.get("/api/next/maintenance/sessions").json()["sessions"][0]["state"] == "held"

    booted = machine.maintenance.boot
    machine.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the hold
    answer = http.post(path, json={"rebooted": True})
    assert answer.status_code == 200, answer.text
    assert [(s["id"], s["state"]) for s in http.get("/api/next/maintenance/sessions").json()["sessions"]] == [
        (lease.id, "recovered")
    ]


def test_a_machine_with_no_projects_shows_and_recovers_its_global_curation_hold_to_its_owner(machine, http):
    machine.load_all()
    listed = http.get("/api/next/projects")
    assert (listed.status_code, listed.json().get("projects")) == (200, []), listed.text
    assert_recoverable_by_its_owner_only(machine, http, global_curation_hold(machine))


def test_a_machine_whose_every_project_store_fails_still_shows_and_recovers_its_global_curation_hold(
    tmp_path, machine, http
):
    bad = registry.register(clone(tmp_path / "bad"))
    (Path(bad.path) / ".git" / "owlbear-delivery" / "format").write_text("99\n")
    machine.load_all()
    shown = http.get("/api/next/projects").json()["projects"]
    assert [p["state"] for p in shown] == ["failed"]
    assert_recoverable_by_its_owner_only(machine, http, global_curation_hold(machine))
