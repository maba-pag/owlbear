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
    owner.failed(ident, RuntimeError("no Run returned"))
    return ident


def test_the_listing_shows_the_captured_session_and_whether_a_reboot_recovers_it(tmp_path):
    ident = failed_session(tmp_path)
    rebooted = maintenance.Maintenance(Slots(lambda: 1, closed=True), boot=lambda: 20.0)
    rebooted.slots.open()
    http = client(rebooted)
    body = http.get("/maintenance/sessions").json()
    (session,) = body["sessions"]
    assert session["id"] == ident
    assert session["state"] == "held"
    assert session["recoverable"] is True
    assert session["workspace"] == str(tmp_path)


def test_an_unconfirmed_recovery_is_refused_with_400_and_keeps_the_reservation(tmp_path):
    ident = failed_session(tmp_path)
    rebooted = maintenance.Maintenance(Slots(lambda: 1, closed=True), boot=lambda: 20.0)
    rebooted.slots.open()
    http = client(rebooted)
    response = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": False})
    assert response.status_code == 400
    assert rebooted.slots.counts("p") == (1, 1, 1)


def test_a_confirmed_reboot_recovers_the_captured_session_once(tmp_path):
    ident = failed_session(tmp_path)
    rebooted = maintenance.Maintenance(Slots(lambda: 1, closed=True), boot=lambda: 20.0)
    rebooted.slots.open()
    http = client(rebooted)
    response = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True})
    assert response.status_code == 200
    (session,) = response.json()["sessions"]
    assert session["state"] == "recovered"
    assert rebooted.slots.counts("p") == (0, 1, 0)
    assert tmp_path.exists()
    again = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True})
    assert again.status_code == 409


def test_a_recovery_without_a_rebooted_boot_or_an_unknown_id_is_refused_with_409(tmp_path):
    ident = failed_session(tmp_path)
    same_boot = maintenance.Maintenance(Slots(lambda: 1, closed=True), boot=lambda: 10.0)
    same_boot.slots.open()
    http = client(same_boot)
    assert http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True}).status_code == 409
    assert http.post("/maintenance/sessions/missing/recover", json={"rebooted": True}).status_code == 409


def test_an_unbound_host_has_no_sessions_to_read_or_recover():
    http = client(None)
    assert http.get("/maintenance/sessions").status_code == 503
    assert http.post("/maintenance/sessions/x/recover", json={"rebooted": True}).status_code == 503


def test_the_recovery_body_accepts_only_the_rebooted_confirmation(tmp_path):
    ident = failed_session(tmp_path)
    rebooted = maintenance.Maintenance(Slots(lambda: 1, closed=True), boot=lambda: 20.0)
    rebooted.slots.open()
    http = client(rebooted)
    response = http.post(f"/maintenance/sessions/{ident}/recover", json={"rebooted": True, "id": "other"})
    assert response.status_code == 422
    assert rebooted.slots.counts("p") == (1, 1, 1)
