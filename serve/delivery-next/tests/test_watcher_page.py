"""The watcher's list on a Change's page (W1a): API fields, the row's count and the list in a real browser."""

from __future__ import annotations

import contextlib
import socket
import sqlite3
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import database, watch_reports
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.state_store.watch_reports import Report

if TYPE_CHECKING:
    from collections.abc import Iterator

NOW = datetime(2026, 10, 24, 10, tzinfo=UTC)
SECRET = "/Users/me/.ssh/config"  # noqa: S105 - a path, not a password


class Host:
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    def activity(self, _slug: str) -> Activity:
        return Activity(host_up=True)


def reported(store: Store) -> None:
    store.write(Lock("flip"), m.Change(slug="flip", step=m.Step(kind=m.StepKind.BUILD)))
    rows = [
        Report("s1", "c1", "2026-10-24T10:00:01.000+00:00", "build", "explore", "edit", f"edit {SECRET}",
               (SECRET,), "outside write (not judged yet)", "", "enriched"),
        Report("s1", "c2", "2026-10-24T10:00:02.000+00:00", "build", "unknown", "bash", "ran make install", (),
               "unresolved (shell effects not classified yet)", "shell effects not classified yet", "start"),
        Report("s1", "c3", "2026-10-24T10:00:03.000+00:00", "build", "main", "bash", "ran cp a /elsewhere/z",
               ("/elsewhere/z",), "outside write (not judged yet)", "shell effects not classified yet", "enriched"),
        watch_reports.summary_row("s1", "build", "2 reports dropped"),
    ]  # fmt: skip
    with store.db.write() as connection:
        for r in rows:
            watch_reports.put("flip", r)(connection)


@pytest.fixture
def store(tmp_path) -> Store:
    s = Store(tmp_path)
    reported(s)
    return s


def test_the_changes_row_counts_its_outside_writes_and_its_page_lists_the_reports(store) -> None:
    http = TestClient(api.create_app(store, "tok", Host()), base_url="http://127.0.0.1",
                      headers={"authorization": "Bearer tok"})  # fmt: skip
    (row,) = http.get("/api/next/changes").json()
    assert row["watcher"] == {"outside": 2, "unresolved": 2}
    w = http.get("/api/next/changes/flip").json()["watcher"]
    assert (w["on"], w["outside"], w["unresolved"]) == (True, 2, 2)
    assert [(r["agent"], r["command"], r["targets"], r["verdict"]) for r in w["reports"][1:]] == [
        ("main", "ran cp a /elsewhere/z", ["/elsewhere/z"], "outside write (not judged yet)"),
        ("unknown", "ran make install", [], "unresolved (shell effects not classified yet)"),
        ("explore", f"edit {SECRET}", [SECRET], "outside write (not judged yet)"),
    ]
    assert w["reports"][0]["verdict"] == "not recorded: 2 reports dropped"
    store.update_config(lambda layer: layer.model_copy(update={"watcher": False}))
    assert http.get("/api/next/changes/flip").json()["watcher"]["on"] is False


def test_a_new_hosts_change_page_reads_a_database_an_older_runtime_made_with_no_write_between(tmp_path) -> None:
    older = Store(tmp_path)
    older.write(Lock("flip"), m.Change(slug="flip"))
    raw = sqlite3.connect(tmp_path / database.DB)
    raw.execute("DROP TABLE watch")  # as a runtime before the watcher left it
    raw.close()
    http = TestClient(api.create_app(Store(tmp_path), "tok", Host()), base_url="http://127.0.0.1",
                      headers={"authorization": "Bearer tok"})  # fmt: skip
    w = http.get("/api/next/changes/flip").json()["watcher"]
    assert (w["reports"], w["outside"], w["unresolved"]) == ([], 0, 0)
    assert http.get("/api/next/changes").json()[0]["watcher"] == {"outside": 0, "unresolved": 0}


def test_a_change_without_reports_counts_none(tmp_path) -> None:
    s = Store(tmp_path)
    s.write(Lock("quiet"), m.Change(slug="quiet"))
    assert api.watcher(s, "quiet") == {"on": True, "reports": [], "outside": 0, "unresolved": 0}
    assert Layer(watcher=False).watcher is False


@pytest.fixture
def page_url(store) -> Iterator[str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{sock.getsockname()[1]}"
    server.should_exit = True


@contextlib.contextmanager
def opened(base: str, slug: str, pds: Any) -> Iterator[Any]:
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/?change={slug}")
        yield page
        browser.close()


@pytest.mark.browser
def test_the_watcher_list_shows_observed_writes_and_unclassified_calls_apart_and_the_row_counts(page_url, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with opened(page_url, "flip", pds) as page:
        expect(page.locator("#changes").get_by_text("2 outside writes observed")).to_be_visible()
        section = page.locator("section.info").filter(has=page.get_by_role("heading", name="Watcher"))
        expect(section.get_by_text("Report only: nothing is judged or stopped yet.")).to_be_visible()
        expect(section.get_by_text("2 calls observed writing outside the worktree")).to_be_visible()
        expect(section.get_by_text(f"explore · edit {SECRET}")).to_be_visible()
        observed = f"observed a command writing to {SECRET} · outside write (not judged yet)"
        expect(section.get_by_text(observed)).to_be_visible()
        expect(section.get_by_text("ran make install")).to_be_hidden()  # collapsed apart
        section.get_by_text("Not classified yet (1)").click()  # the shell call with a known target is listed above
        expect(section.get_by_text("unknown · ran make install")).to_be_visible()
        expect(section.get_by_text("not recorded: 2 reports dropped")).to_be_visible()
