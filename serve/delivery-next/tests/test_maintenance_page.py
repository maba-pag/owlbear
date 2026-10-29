"""The Maintenance page rendered by lit-html in a real browser (TD-264)."""

from __future__ import annotations

import socket
import subprocess
import threading
import time
from typing import TYPE_CHECKING

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.models import Brief, Change, StepKind
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.state_store.store import Lock, Store

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.browser
def test_the_maintenance_page_lists_each_action_and_says_when_delivery_stops(tmp_path: Path, pds) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    store = Store(tmp_path)
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", None), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/maintenance#token=tok")
            actions = page.locator("#actions > li")
            expect(actions).to_have_count(5)
            expect(actions.nth(1)).to_contain_text("Impeccable update")
            expect(page.get_by_role("link", name="Open Memory curation in Memory")).to_have_attribute("href", "/memory")
            expect(actions.nth(2)).to_contain_text("No run record kept.")
            expect(page.locator("#use-none")).to_have_text("No step has run in this project yet.")
            store.write(Lock("a"), Change(slug="a", brief=Brief(version=1)))
            ran = [{"agent": "explore", "credits": 1.25, "credits_known": True}]
            store.log(Lock("a"), "a", {"event": "step", "session": "s1", "kind": "build", "subagents": ran})
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.locator("#use p-table-cell")).to_have_text(["builder", "1", "1", "1", "1.25", "explore 1"])
            expect(page.locator("#error")).to_be_hidden()
            assert page.evaluate("location.hash") == ""  # the token left the address bar
            held = []  # what Delivery takes but never answers: up, yet busy

            def hold(route) -> None:
                held.append(route)

            page.route("**/api/next/maintenance/subagents", hold)
            page.route("**/api/next/project", lambda r: r.abort("connectionrefused"))
            caught = page.evaluate("""async () => {
              const ui = await import("/assets/ui.mjs"), caught = [];
              for (const [path, method] of [["/maintenance/subagents", "GET"], ["/maintenance/subagents", "POST"],
                ["/project", "GET"]]) {
                await ui.call(path, { method, timeout: 200 }).catch((e) => caught.push({ slow: e instanceof ui.Slow,
                  down: e instanceof ui.HostDown, sent: e.sent ?? null, said: e.message }));
              }
              return caught;
            }""")
            unsure = "Delivery did not answer within 0.2 s, so this may have been done or not. It was not sent again;"
            assert caught == [
                {"slow": True, "down": False, "sent": False,
                 "said": "Delivery is slow to answer: no reply within 0.2 s. Try again in a moment."},
                {"slow": True, "down": False, "sent": True,
                 "said": f"{unsure} reload the page to see which before you try again."},
                {"slow": False, "down": True, "sent": None,
                 "said": "Delivery is not running. Start it, then reload this page."},
            ]  # fmt: skip
            assert [r.request.method for r in held].count("POST") == 1  # a timed-out write is never sent again
            page.route("**/api/next/**", lambda r: r.abort())
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.locator("#error")).to_have_text("Delivery is not running. Start it, then reload this page.")
            expect(actions).to_have_count(5)  # what it showed stays
            browser.close()
    finally:
        server.should_exit = True


@pytest.mark.browser
def test_the_test_review_starts_from_the_chosen_packages_once_confirmed(tmp_path: Path, pds) -> None:
    """TD-370, TD-390: every package is chosen, the dialog says what runs, and the Start opens one Change."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    work = tmp_path / "work"
    for name in ("pyproject.toml", "tests/test_a.py", "web/package.json", "web/src/b.test.ts"):
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text("x\n")
    who = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run([*who, *args], cwd=work, check=True, capture_output=True)  # noqa: S603
    store = Store.open(work)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host(store, work)), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/maintenance#token=tok")
            tests = page.locator("#tests")
            expect(tests.get_by_role("checkbox")).to_have_count(2)
            expect(page.locator("#tests-runs")).to_contain_text("2 reviewer sessions on gpt-6.1-sol at medium effort")
            tests.get_by_label("the repository's root: 1 files, 1 lines, 1 share").uncheck()
            expect(page.locator("#tests-runs")).to_contain_text("1 reviewer session on")
            page.get_by_role("button", name="Review tests").click()
            expect(page.get_by_role("dialog", name="Review the tests?")).to_be_visible()
            expect(pds.modal(page)).to_contain_text("which your Start approves")
            pds.answer(page, "Cancel")
            expect(page.get_by_role("dialog")).to_be_hidden()
            assert store.slugs() == []  # declined: nothing starts
            page.get_by_role("button", name="Review tests").click()
            pds.answer(page, "Start the test review")
            expect(page.locator("#status")).to_contain_text("Started test review c1")
            expect(tests).to_contain_text("Test review c1 has not finished")
            c = store.read(store.slugs()[0])
            assert (c.step.kind, c.tests.packages) == (StepKind.TESTS, ["web"])
            browser.close()
    finally:
        server.should_exit = True
