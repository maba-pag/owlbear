"""The Maintenance sessions API: an unknown session stays held until its owner confirms a reboot."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import maintenance_routes

AT = datetime(2026, 10, 25, tzinfo=UTC)


def client(owner):
    app = FastAPI()
    app.include_router(maintenance_routes.router(SimpleNamespace(maintenance=owner)))
    return TestClient(app, base_url="http://127.0.0.1")


def failed_session(root):
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0)
    assert owner.slots.take("p", "pack:one", 1, 1) == 1
    ident = owner.begin("p", "pack:one", "pack", str(root), now=AT)
    owner.failed(ident, "RuntimeError: no Run returned")
    return ident


def test_only_the_owner_after_a_confirmed_reboot_recovers_the_listed_session_once(tmp_path):
    ident = failed_session(tmp_path)
    same_boot = maintenance.Maintenance(Slots(lambda: 1, closed=True), boot=lambda: 10.0)
    same_boot.slots.open()
    http = client(same_boot)
    assert http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True}).status_code == 409
    assert http.post("/maintenance/sessions/missing/recover", json={"rebooted": True}).status_code == 409
    assert same_boot.slots.counts("p") == (1, 1, 1)

    rebooted = maintenance.Maintenance(Slots(lambda: 1, closed=True), boot=lambda: 20.0)
    rebooted.slots.open()
    http = client(rebooted)
    body = http.get("/maintenance/sessions").json()
    (session,) = body["sessions"]
    assert session["id"] == ident
    assert session["state"] == "held"
    assert session["recoverable"] is True
    assert session["workspace"] == str(tmp_path)

    chat = http.post(
        f"/maintenance/sessions/{ident}/recover", json={"rebooted": True}, headers={"x-owlbear-use": "chat"}
    )
    assert chat.status_code == 403
    assert rebooted.slots.counts("p") == (1, 1, 1)
    assert http.get("/maintenance/sessions").json()["sessions"][0]["state"] == "held"
    response = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True, "id": "other"})
    assert response.status_code == 422
    assert rebooted.slots.counts("p") == (1, 1, 1)
    response = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": False})
    assert response.status_code == 400
    assert rebooted.slots.counts("p") == (1, 1, 1)

    response = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True})
    assert response.status_code == 200
    (session,) = response.json()["sessions"]
    assert session["state"] == "recovered"
    assert rebooted.slots.counts("p") == (0, 1, 0)
    assert tmp_path.exists()
    again = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True})
    assert again.status_code == 409


def test_an_unbound_host_has_no_sessions_to_read_or_recover():
    http = client(None)
    assert http.get("/maintenance/sessions").status_code == 503
    assert http.post("/maintenance/sessions/x/recover", json={"rebooted": True}).status_code == 503
