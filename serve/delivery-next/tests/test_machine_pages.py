"""The pages under the machine host (TD-242): one project at a time, chosen by the bar under the tabs."""

from __future__ import annotations

import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.models import Change, Step, StepKind
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import app, project, registry
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from pathlib import Path


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    store = Store.open(path)
    with store.lock(f"{path.name}-1") as lock:
        store.write(lock, Change(slug=f"{path.name}-1", step=Step(kind=StepKind.BUILD)))
    return path.resolve()


def serve() -> tuple[Machine, uvicorn.Server, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    now = datetime.now(UTC)
    machine = Machine(HostRecord(url=f"{base}/", token="t", pid=1, started_at=now, code=codebase.CURRENT))  # noqa: S106
    machine.load_all()
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return machine, server, base


@pytest.mark.browser
def test_each_page_shows_one_project_the_bar_switches_adds_removes_and_resumes(tmp_path: Path, monkeypatch) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)  # the scheduler runs; no runner starts
    a, b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    third = clone(tmp_path / "gamma")
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/#token=t")
            expect(page).to_have_url(f"{base}/?project={a.id}")  # a link without a project opens the first
            expect(page.locator("#changes")).to_contain_text("alpha-1")
            expect(page.locator("#machine .paused")).to_contain_text("2 Changes would continue")
            expect(page.locator("#changes")).to_contain_text("Delivery is paused: continues after Resume")
            page.locator("#machine select").select_option(b.id)
            expect(page.locator("#changes")).to_contain_text("beta-1")
            expect(page.get_by_role("link", name="Backlog")).to_have_attribute("href", f"/backlog?project={b.id}")
            page.locator("#changes a.open").first.click()
            expect(page).to_have_url(f"{base}/?project={b.id}&change=beta-1")
            page.reload()
            expect(page.locator("#machine select")).to_have_value(b.id)
            page.get_by_role("button", name="Resume").click()
            expect(page.locator("#machine .paused")).to_have_count(0)
            assert (machine.paused, registry.load().resumed_at is not None) == (False, True)
            page.locator("#machine summary").click()
            page.get_by_label("Folder").fill(str(third))
            page.get_by_role("button", name="Add", exact=True).click()
            expect(page.locator("#changes")).to_contain_text("gamma-1")
            added = next(p for p in registry.load().projects if p.path == str(third))
            expect(page).to_have_url(f"{base}/?project={added.id}")
            page.get_by_role("button", name="Remove project").click()
            page.locator("dialog").get_by_role("button", name="Remove project").click()
            expect(page).to_have_url(f"{base}/?project={a.id}")
            assert [p.id for p in registry.load().projects] == [a.id, b.id]
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()
