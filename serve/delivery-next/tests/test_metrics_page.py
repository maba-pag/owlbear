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
    refused = {"calls": 9, "rejected": 7, "invalid": 3, "checks": 2, "order": 1, "lint": 1, "late": 1, "retries": 6}
    spend_ledger.append([
        *run("a", now, split, shop, tools={"submit_result": {"calls": 1}}, wrong={}),
        *run("b", now + timedelta(minutes=1), spent, owlbear, stopped="reached", stopped_by="session", limit=1.0,
             tools={"submit_result": refused}, wrong={"denied": 2, "no_result": 1}),
        *run("c", now + timedelta(minutes=2), {"error": "TimeoutError"}, {"project": "", "name": "", "change": "",
                                                                           "agent": "updater"},
             stopped="unknown", stopped_by="session", limit=0.5, subagents=1,  # its spend is not split from theirs
             tools={}, wrong={"missing_pointless": 1}),
    ])  # fmt: skip


def serve() -> tuple[Machine, uvicorn.Server, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    record = HostRecord(url=f"{base}/", token="t", pid=1, started_at=datetime.now(UTC), code=codebase.CURRENT)  # noqa: S106
    machine = Machine(record)
    # longer than the pages' polls: route.fetch() reuses a pooled socket, which uvicorn's 5 s default closes
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning", timeout_keep_alive=60))
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
            tools = page.locator("#tools p-table-row")  # C-28: weighted, 1 of 1 and 0 of 9 calls accepted
            expect(tools).to_have_count(2)
            expect(tools.nth(0)).to_contain_text("submit_result")
            expect(tools.nth(1)).to_contain_text("All tools")
            for cell in ("10", "10%", "3", "2", "1"):  # calls, success, invalid, failed checks, wrong moment
                expect(tools.nth(0).locator("p-table-cell", has_text=cell).first).to_be_visible()
            expect(page.locator("#wrong")).to_contain_text("1 call at the wrong moment")
            expect(page.locator("#wrong")).to_contain_text("2 denials by the guard")
            expect(page.locator("#wrong")).to_contain_text("1 turn ended without a result")
            expect(page.locator("#wrong")).to_contain_text("1 pointless missing-tool report")
            expect(page.locator("#tool-use-coverage")).to_contain_text("Counted for 3 runs")
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
            expect(tools.nth(0)).to_contain_text("100%")

            pds.pick(page, "Agent", "updater")  # its spend shows under an unknown agent, its tool use under its own
            expect(tools).to_have_count(1)
            expect(page.locator("#wrong")).to_contain_text("1 pointless missing-tool report")
            expect(page.locator("#wrong")).to_contain_text("0 denials by the guard")

            pds.pick(page, "Agent", "")
            pds.pick(page, "Project", "owlbear")
            expect(page.locator("#total-credits")).to_contain_text("1.00 credits")
            expect(tools.nth(0)).to_contain_text("0%")
            expect(page.locator("#wrong")).to_contain_text("2 denials by the guard")
            page.locator("#stopped").click()
            expect(page.locator("#runs p-table-row")).to_have_count(1)
            pds.pick(page, "Period", "custom")
            page.locator("#from input").fill("2020-01-01")
            page.locator("#from input").press("Enter")
            page.locator("#to input").fill("2020-01-31")
            page.locator("#to input").press("Enter")
            expect(page.locator("#split-none")).to_have_text("Nothing was spent that these filters show.")
            expect(page.locator("#tool-use-none")).to_have_text("No tool use was measured for these filters.")
            page.reload()  # the filters stay in the address
            expect(page.locator("#split-none")).to_be_visible()
            expect(page.locator("#error")).to_have_count(0)
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_a_ledger_whose_step_events_list_their_models_renders(pds) -> None:
    """The owner's ledger: older step events list their models' names, and Metrics answered 500 on every read."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    at = (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="seconds")
    place = {"project": "shop", "name": "shop", "clone": "", "change": "c1", "step": "build", "job": "",
             "agent": "builder", "source": "import:activity"}  # fmt: skip
    spend_ledger.append([
        place | {"id": f"event:{n}", "type": "event", "at": at, "session": f"s{n}",
                 "usage": {"credits": spent, "model_mismatch": False, "models": names}}
        for n, (spent, names) in enumerate([(1.5, ["m1"]), (0.5, ["m1", "m2"])])
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
            page.goto(f"{base}/metrics?by=model#token=t")
            expect(page.locator("#total-credits")).to_contain_text("2.00 credits")
            rows = page.locator("#split p-table-row")
            expect(rows).to_have_count(2)
            expect(rows.nth(0)).to_contain_text("m1")
            expect(rows.nth(0)).to_contain_text("1.50")
            expect(rows.nth(1)).to_contain_text("Model unknown")
            expect(rows.nth(1)).to_contain_text("0.50")
            expect(page.locator("#runs p-table-row")).to_have_count(2)
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


@pytest.mark.browser
def test_all_projects_chosen_on_a_clones_page_stays_chosen_after_a_reload(pds) -> None:
    """Copilot's review: choosing All projects dropped ?in=, so a reload preselected the bar's clone's project again."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    now = datetime.now(UTC) - timedelta(hours=1)
    spent = {"credits": 1.0, "models": {"m1": {"credits": 1.0, "input": 10, "output": 1}}}
    shop = {"project": "shop", "name": "shop", "clone": "c-shop", "change": "c1", "agent": "builder"}
    owlbear = {"project": "owlbear", "name": "owlbear", "clone": "c-owl", "change": "c2", "agent": "reviewer"}
    spend_ledger.append([*run("a", now, spent, shop), *run("b", now, spent, owlbear)])
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(timezone_id="Europe/Berlin")
            pds.only(page, base)

            def listed(route) -> None:  # the bar serves the clone, so the page keeps ?project=
                answer = route.fetch()
                clone = {"id": "c-shop", "name": "shop", "path": "/clones/shop", "state": "loaded"}
                route.fulfill(response=answer, json=answer.json() | {"projects": [clone]})

            page.route("**/api/next/projects", listed)
            page.goto(f"{base}/metrics?project=c-shop#token=t")
            expect(page.locator("#total-credits")).to_contain_text("1.00 credits")  # the bar's clone: its project
            pds.pick(page.get_by_role("group", name="Show only"), "Project", "")  # All projects
            expect(page.locator("#total-credits")).to_contain_text("2.00 credits")
            page.reload()
            expect(page.locator("#total-credits")).to_contain_text("2.00 credits")  # still every project
            expect(page.locator("#error")).to_have_count(0)
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()
