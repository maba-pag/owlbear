"""The Metrics page in a real browser (D-01M5XCDF6G60VG5GHTWF5QSSDE): totals, a split, drill-down and the runs."""

from __future__ import annotations

import re
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
            expect(page.locator("#runs p-table-row").nth(0)).to_contain_text("lower bound")  # its credits unreported
            expect(page.locator("#runs p-table-row").nth(0)).to_contain_text("Outside a Change")
            expect(page.locator("#runs p-table-row").nth(1)).not_to_contain_text("lower bound")
            expect(page.locator("#runs .lower")).to_have_count(1)
            expect(page.locator("#lower-bound")).to_contain_text("spent at least this")
            expect(page.locator("#exact li")).to_have_text([re.compile(r"^1 run did not report its credits")])
            expect(rows.locator(".share")).to_have_text(["57%", "29%", "14%", "0%"])  # of the 3.50 credits
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
        place | {"id": f"event:{n}", "type": "event", "at": at, "session": f"s{n}", "step": step,
                 "usage": {"credits": spent, "model_mismatch": False, "models": names}}
        for n, (spent, names, step) in enumerate([(1.5, ["m1"], "build"), (0.5, ["m1", "m2"], "amend")])
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
            fold = page.locator("#runs p-table-row")  # one builder's consecutive runs share a row that opens
            expect(fold).to_have_count(1)
            expect(fold).to_have_attribute("data-runs", "2")
            expect(fold).to_contain_text("2.00")
            expect(fold.locator("p-table-cell").nth(2)).to_have_text("c1 · 2 steps")  # one Change, not "2 Changes"
            button = fold.get_by_role("button", name="builder · 2 runs")
            expect(button).to_have_attribute("aria-expanded", "false")
            button.focus()
            page.keyboard.press("Enter")
            expect(button).to_have_attribute("aria-expanded", "true")
            expect(page.locator("#runs .member")).to_have_count(2)
            expect(page.locator("#runs .member .num")).to_have_text(["1.50", "0.50"])
            expect(page.locator("#runs .member p-table-cell:nth-child(3)")).to_have_text(["c1 · build", "c1 · amend"])
            page.keyboard.press("Enter")
            expect(page.locator("#runs .member")).to_have_count(0)
            expect(page.locator("#error")).to_have_count(0)
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_a_fold_counts_changes_by_project_apart_from_runs_outside_one_and_its_rows_name_theirs(pds) -> None:
    """Copilot's counterexamples: two projects' curation runs read as "2 Changes"; one slug in two projects read as
    "2 Changes" while the opened rows left their Change blank; and two projects sharing a name read as one Change."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    now, spent = datetime.now(UTC) - timedelta(hours=1), {"credits": 1.0, "models": {"m1": {"credits": 1.0}}}
    seeds = [("curator", "shop", "shop", ""), ("curator", "docs", "docs", ""), ("builder", "p", "web", "ch"),
             ("builder", "q", "web", "ch"),  # two projects that share a name
             ("reviewer", "shop", "shop", ""), ("reviewer", "shop", "shop", "c9")]  # fmt: skip
    spend_ledger.append([
        line for n, (agent, pid, name, change) in enumerate(seeds)
        for line in run(f"r{n}", now + timedelta(minutes=n), spent, {"project": pid, "name": name, "change": change,
                                                                     "step": "build" if change else "", "agent": agent})
    ])  # fmt: skip
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/metrics#token=t")
            folds = page.locator("#runs p-table-row.fold p-table-cell:nth-child(3)")
            expect(folds).to_have_text(["1 Change and outside a Change", "2 Changes", "Outside a Change"])
            page.get_by_role("button", name="builder · 2 runs").click()
            expect(page.locator("#runs .member p-table-cell:nth-child(3)")).to_have_text(["ch · build", "ch · build"])
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_only_a_failed_read_is_said_to_have_failed(pds) -> None:
    """#780: picker runs read while their turn ran were all said to have had their last read fail."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    now = datetime.now(UTC) - timedelta(hours=1)
    place = {"project": "owlbear", "name": "owlbear", "change": "", "agent": "picker", "job": "decision-pick"}

    def used(spent: float, **more: str) -> dict:
        return {"credits": spent, "models": {"m1": {"credits": spent, "input": 100, "output": 10}}} | more

    spend_ledger.append([
        *run("exact", now, used(9.0), place),
        *run("turn", now + timedelta(minutes=1), used(9.33, incomplete="turn running"), place),
        *run("failed", now + timedelta(minutes=2), used(9.73, incomplete="TimeoutError"), place),
    ])  # fmt: skip
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/metrics#token=t")
            said = page.locator("#exact li")
            expect(said).to_have_count(2)
            texts = said.all_inner_texts()
            assert [t.startswith("1 run ") for t in texts] == [True, True]
            assert [("failed" in t) for t in texts].count(True) == 1
            expect(page.locator("#lower-bound")).to_contain_text("spent at least this")
            expect(page.locator("#lower-bound")).not_to_contain_text("failed")
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_spend_said_apart_from_the_period_never_reads_unknown_as_zero_or_a_counted_run_as_left_out(pds) -> None:
    """Sol's and Copilot's counterexamples: a run with only its start said "0.00 more"; one carrying known credits too
    said "credits not known"; and a resumed run, counted with its own spend, was called one more run not counted."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    at = (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="seconds")
    place = {"clone": "", "step": "", "job": "", "project": "shop", "name": "shop", "change": "c1", "agent": "builder"}

    def started(rid: str, before: dict) -> dict:
        return place | {"run": rid, "session": f"s-{rid}", "id": f"start:{rid}", "type": "start", "at": at,
                        "model": "m1", "before": before}  # fmt: skip

    def used(spent: float) -> dict:
        return {"credits": spent, "models": {"m1": {"credits": spent, "input": 10, "output": 1}}}

    spend_ledger.append([started("o", {})])
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
            said = page.locator("#exact li").last
            expect(said).to_contain_text("Spend of 1 run may also lie in this period (credits not known):")
            expect(page.locator("#exact")).not_to_contain_text("0.00")
            spend_ledger.append([started("p", used(3.0))])  # a resumed run whose end is not recorded yet
            page.reload()
            expect(said).to_contain_text("Spend of 2 runs may also lie in this period (3.00 or more credits):")
            spend_ledger.append([started("r", used(3.0)), place | {  # resumed and ended: 1.00 of its own counts
                "run": "r", "session": "s-r", "id": "end:r", "type": "end", "at": at, "usage": used(4.0),
                "ending": "result", "limit": None, "stopped": ""}])  # fmt: skip
            page.reload()
            expect(page.locator("#total-runs")).to_have_text("1 run")
            expect(said).to_contain_text("Spend of 3 runs may also lie in this period (6.00 or more credits):")
            expect(said).to_contain_text("so it is not counted")
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
            expect(page.locator("#runs p-table-row")).to_have_count(1)  # the three reviewer runs fold
            expect(page.locator("#runs p-table-row")).to_have_attribute("data-runs", "3")
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
