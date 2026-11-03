"""#718 on the Changes page: a running step's shown stage follows the events its sessions log, for two roles."""

from __future__ import annotations

import socket
import threading
import time
from datetime import UTC, datetime

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.models import Change, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api, host
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store.store import Lock, Store

PLAN = Plan(tasks=[Task(id="t1", title="greet")])


class Host:
    """The project host's seam over the real store: its activity is the real ``host.activity``."""

    maintenance = None
    wake = type("W", (), {"set": staticmethod(lambda: None)})()

    def __init__(self, store: Store) -> None:
        self.store = store
        self.record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC),  # noqa: S106
                                 code=CURRENT)  # fmt: skip

    def activity(self, slug: str) -> Activity:
        return host.activity(self.store, slug, self.record)


def logged(store: Store, lock: Lock, sid: str, role: str, event: str, **more: object) -> None:
    """One event as the SDK runtime journals it for an opened session."""
    at = datetime.now(UTC).isoformat(timespec="seconds")
    store.log(lock, "c1", {"at": at, "session": sid, "role": role, "event": event, **more})


def served(store: Store) -> tuple[uvicorn.Server, str]:
    """The project host's pages and API over *store*, on a free port."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host(store)), log_level="warning",
                                           timeout_keep_alive=60))  # fmt: skip
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server, f"http://127.0.0.1:{sock.getsockname()[1]}"


@pytest.mark.browser
@pytest.mark.timeout(120)  # a journey through 13 polled stages; it took 29 s alone and timed out on a loaded laptop
def test_the_shown_stage_follows_a_builders_and_a_reviewers_events(tmp_path, pds) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    store = Store(tmp_path)
    store.write(Lock("c1"), Change(slug="c1", plan=PLAN, step=Step(kind=StepKind.BUILD, task="t1",
                                                                  started_at=datetime.now(UTC))))  # fmt: skip
    server, base = served(store)
    machine_list = f"{base}/api/next/projects"  # served by the machine host, which this project host runs without
    errors: list[str] = []
    with sync_playwright() as pw, store.lock("c1") as lock:  # the runner holds the Change: its step runs
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        page.on("console", lambda m: m.type == "error" and m.location["url"] != machine_list and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/?change=c1")
        detail, card = page.locator("#detail .row.status"), page.locator("#changes .card")

        def shows(said: str) -> None:
            expect(detail).to_contain_text(f"Build 1/1 \u00b7 {said}", timeout=15_000)  # the page's poll brings it
            expect(card).to_contain_text(said, timeout=15_000)  # the card shows its step apart

        shows("starting: greet")
        logged(store, lock, "b1", "builder", "session", id="b1", resumed=False)
        shows("implementing: greet")
        logged(store, lock, "b1", "builder", "tool", tool="submit_result", accepted=False, errors=["ruff: F401"])
        shows("fixing its refused result: greet")
        logged(store, lock, "b1", "builder", "tool", tool="submit_result", accepted=True, errors=[])
        shows("handing in its result: greet")
        logged(store, lock, "b1", "builder", "ended", ending="result")
        shows("recording the result: greet")

        time.sleep(1)  # the review starts in a later second than the build's session opened
        store.write(lock, Change(slug="c1", plan=PLAN, step=Step(kind=StepKind.REVIEW, task="t1",
                                                                started_at=datetime.now(UTC))))  # fmt: skip
        shows("starting: greet")
        logged(store, lock, "r1", "reviewer", "session", id="r1", resumed=False)
        shows("reviewing: greet")
        logged(store, lock, "r1", "reviewer", "tool", tool="lookup_decisions", accepted=True, errors=[])
        logged(store, lock, "p1", "picker", "session", id="p1", resumed=False)
        shows("checking decisions: greet")
        logged(store, lock, "p1", "picker", "tool", tool="submit_result", accepted=True, errors=[])  # the picker's own
        logged(store, lock, "p1", "picker", "ended", ending="result")
        shows("reviewing: greet")
        logged(store, lock, "r1", "reviewer", "tool", tool="submit_result", accepted=True, errors=[])
        shows("handing in its verdict: greet")
        assert errors == []
        browser.close()
    server.should_exit = True
