"""The Metrics page in a real browser (D-01M5XCDF6G60VG5GHTWF5QSSDE): totals, a split, drill-down and the runs."""

from __future__ import annotations

import socket
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
import uvicorn

from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import app
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import spend_reconcile
from owlbear_delivery_next.state_store import spend_ledger


def run(rid: str, at: datetime, usage: dict, place: dict, **end: object) -> list[dict]:
    when = at.isoformat(timespec="seconds")
    common = {"run": rid, "session": f"s-{rid}", "clone": "", "step": "", "job": ""} | place
    return [
        common | {"id": f"start:{rid}", "type": "start", "at": when, "model": "m1", "before": {}},
        common | {"id": f"end:{rid}", "type": "end", "at": when, "usage": usage, "ending": "result", "limit": None,
                  "stopped": ""} | end,
    ]  # fmt: skip


def seeded() -> None:
    now = datetime.now(UTC) - timedelta(hours=1)
    split = {"credits": 2.5, "models": {}, "agents": {
        "main": {"agent": "main", "models": {"m1": {"credits": 2.0, "input": 100, "output": 10}}},
        "x1": {"agent": "explore", "models": {"m2": {"credits": 0.5, "input": 50, "output": 5}}},
    }}  # fmt: skip
    shop = {"project": "shop", "name": "shop", "change": "c1", "step": "build", "agent": "builder"}
    owlbear = {"project": "owlbear", "name": "owlbear", "change": "c2", "agent": "reviewer"}
    spent = {"credits": 1.0, "models": {"m1": {"credits": 1.0, "input": 10, "output": 1}}}
    spend_ledger.append([
        *run("a", now, split, shop),
        *run("b", now + timedelta(minutes=1), spent, owlbear, stopped="reached", stopped_by="session", limit=1.0),
        *run("c", now + timedelta(minutes=2), {"error": "TimeoutError"}, {"project": "", "name": "", "change": "",
                                                                           "agent": "updater"},
             stopped="unknown", stopped_by="session", limit=0.5),
    ])  # fmt: skip


def serve() -> tuple[Machine, uvicorn.Server, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    record = HostRecord(url=f"{base}/", token="t", pid=1, started_at=datetime.now(UTC), code=codebase.CURRENT)  # noqa: S106
    machine = Machine(record)
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return machine, server, base


@pytest.mark.browser
def test_the_metrics_page_sums_splits_drills_down_and_lists_runs_with_their_limit_stops(pds) -> None:  # noqa: PLR0915 - a journey
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    seeded()
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(timezone_id="Europe/Berlin")
            pds.only(page, base)
            page.goto(f"{base}/metrics#token=t")
            expect(page).to_have_title("OwlBear Delivery · Metrics")
            expect(page.locator("#total-credits")).to_contain_text("3.50 credits")
            expect(page.locator("#total-credits")).to_contain_text("plus 1 run whose credits were not reported")
            expect(page.locator("#total-runs")).to_have_text("3 runs")
            expect(page.locator("#total-stopped")).to_have_text("1 stopped at their credit limit, 1 more may have been")
            rows = page.locator("#split p-table-row")
            expect(rows).to_have_count(4)
            expect(rows.nth(0)).to_contain_text("builder")
            expect(rows.nth(0)).to_contain_text("2.00")
            expect(rows.nth(1)).to_contain_text("reviewer")
            expect(rows.nth(2)).to_contain_text("explore (subagent)")
            expect(rows.nth(2)).to_contain_text("0.50")
            expect(page.locator("#runs p-table-row")).to_have_count(3)
            expect(page.locator("#runs-count")).to_contain_text("All 3 runs.")
            expect(page.locator("#runs p-table-row").nth(1)).to_contain_text(
                "stopped at its credit limit of 1 (session)"
            )
            expect(page.locator("#runs p-table-row").nth(0)).to_contain_text("not all reported")
            expect(page.locator("#runs p-table-row").nth(0)).to_contain_text("may have reached its credit limit of 0.5")
            assert spend_reconcile.settled(10)
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.locator("#reconcile")).to_contain_text("Earlier records last read")

            rows.nth(0).get_by_role("button", name="Show only builder").click()  # drill down, then split by model
            expect(page.locator("#split-title")).to_have_text("By model")
            expect(rows).to_have_count(1)
            expect(rows.nth(0)).to_contain_text("m1")
            expect(page.locator("#total-credits")).to_contain_text("2.00 credits")
            assert "agent=builder" in page.url
            assert "by=model" in page.url

            pds.pick(page, "Agent", "")
            pds.pick(page, "Project", "owlbear")
            expect(page.locator("#total-credits")).to_contain_text("1.00 credits")
            page.locator("#stopped").click()
            expect(page.locator("#runs p-table-row")).to_have_count(1)
            pds.pick(page, "Period", "custom")
            page.locator("#from input").fill("2020-01-01")
            page.locator("#from input").press("Enter")
            page.locator("#to input").fill("2020-01-31")
            page.locator("#to input").press("Enter")
            expect(page.locator("#split-none")).to_have_text("Nothing was spent that these filters show.")
            page.reload()  # the filters stay in the address
            expect(page.locator("#split-none")).to_be_visible()
            expect(page.locator("#error")).to_have_count(0)
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


HOLD = """
window.__held = [];
const real = window.fetch;
window.fetch = async (...args) => {
  const answer = await real(...args);
  if (window.__hold && String(args[0]).includes("cursor=")) await new Promise((go) => window.__held.push(go));
  return answer;
};
"""


@pytest.mark.browser
def test_a_show_more_answered_after_the_filters_changed_is_dropped(pds) -> None:
    """Sol's counterexample: a pending "Show more" of the old filters appended to the new list and took its cursor."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    now = datetime.now(UTC) - timedelta(hours=1)
    shop = {"project": "shop", "name": "shop", "change": "c1", "agent": "builder"}
    owlbear = {"project": "owlbear", "name": "owlbear", "change": "c2", "agent": "reviewer"}
    spent = {"credits": 0.1, "models": {"m1": {"credits": 0.1, "input": 1, "output": 1}}}
    spend_ledger.append([
        *(x for n in range(55) for x in run(f"s{n}", now + timedelta(seconds=n), spent, shop)),
        *(x for n in range(3) for x in run(f"o{n}", now + timedelta(seconds=n), spent, owlbear)),
    ])  # fmt: skip
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(timezone_id="Europe/Berlin")
            pds.only(page, base)
            page.add_init_script(HOLD)
            page.goto(f"{base}/metrics#token=t")
            expect(page.locator("#runs-count")).to_contain_text("The newest 50 of 58 runs.")
            assert spend_reconcile.settled(10)
            expect(page.locator("#reconcile")).to_contain_text("Earlier records last read", timeout=10000)
            page.evaluate("window.__hold = true")
            page.locator("#more").click()
            page.wait_for_function("window.__held.length === 1")  # its answer is in, held back
            pds.pick(page, "Project", "owlbear")
            expect(page.locator("#runs-count")).to_contain_text("All 3 runs.")
            page.evaluate("window.__held.forEach((go) => go())")  # the old answer arrives last
            page.wait_for_timeout(500)
            expect(page.locator("#runs p-table-row")).to_have_count(3)
            expect(page.locator("#runs-count")).to_contain_text("All 3 runs.")
            expect(page.locator("#more")).to_have_count(0)
            expect(page.locator("#error")).to_have_count(0)
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_the_page_reads_again_after_a_pass_whose_worker_started_late(pds, monkeypatch) -> None:
    """Sol's counterexample: the first answer did not say the pass was running, so the page never read again."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    seeded()
    real, go = spend_reconcile.run, threading.Event()

    def late(projects: list) -> dict:
        go.wait(10)  # the worker thread is slow to begin its pass
        return real(projects)

    monkeypatch.setattr(spend_reconcile, "run", late)
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                go.set()
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(timezone_id="Europe/Berlin")
            pds.only(page, base)
            page.goto(f"{base}/metrics#token=t")
            expect(page.locator("#reconcile")).to_contain_text("Reading earlier records")
            go.set()
            expect(page.locator("#reconcile")).to_contain_text("Earlier records last read", timeout=10000)
            browser.close()
    finally:
        go.set()
        server.should_exit = True
        machine.stop_all()
