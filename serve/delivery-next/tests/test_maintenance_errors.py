"""Maintenance refusals and failed reads in real Chromium with synthetic API responses."""

from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn

from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store.store import Store

OFFER = {
    "packages": [{"path": ".", "files": 1, "lines": 1, "shares": 1}],
    "roles": {
        "test-reviewer": {"model": "reviewer", "effort": "medium"},
        "test-curator": {"model": "curator", "effort": "medium", "context": "default"},
    },
    "sessions": 1,
    "open": None,
}
pytestmark = pytest.mark.browser


@pytest.fixture
def maintenance(tmp_path, pds):
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 - optional browser runtime

    state = {"curation": 200, "tests": 200, "post": 409, "detail": "refused by host", "reads": 0}
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(Store(tmp_path), "tok", None), log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        base = f"http://127.0.0.1:{sock.getsockname()[1]}"
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page()
                pds.only(page, base)

                def curation(route):
                    if route.request.method == "POST":
                        code = state["post"]
                        route.fulfill(status=code, json={"detail": state["detail"]} if code != 200 else {})
                        return
                    state["reads"] += 1
                    if state.get("hold_next"):
                        state["hold_next"], state["held"] = False, route
                        page.evaluate("window.maintenanceReadHeld = true")
                        return
                    code = state["curation"]
                    data = {
                        "available": True,
                        "folders": [
                            {
                                "folder": name,
                                "state": "never",
                                "entries": [],
                                "summary": f"Read generation {state['reads']}",
                            }
                            for name in ("shop", "other")
                        ],
                    }
                    route.fulfill(status=code, json=data if code == 200 else {"detail": "curation read failed"})

                def tests(route):
                    code = state["tests"] if route.request.method == "GET" else state["post"]
                    data = OFFER if route.request.method == "GET" else {"handle": "c9"}
                    detail = "tests read failed" if route.request.method == "GET" else state["detail"]
                    route.fulfill(status=code, json=data if code == 200 else {"detail": detail})

                page.route("**/api/next/curation", curation)
                page.route("**/api/next/maintenance/test-review", tests)
                yield page, base, state
            finally:
                browser.close()
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()
        assert not thread.is_alive()


def start(page, pds, kind, folder="shop"):
    if kind == "curation":
        page.get_by_role("button", name=f"Curate {folder} now", exact=True).click()
        yes = "Curate now"
    else:
        page.get_by_role("button", name="Review tests", exact=True).click()
        yes = "Start the test review"
    with page.expect_response(
        lambda r: r.request.method == "GET" and r.url.endswith("/api/next/curation"),
    ) as refreshed:
        pds.modal(page).get_by_role("button", name=yes, exact=True).click()
    return refreshed.value.json()["folders"][0]["summary"]


def refresh(page):
    with page.expect_response(
        lambda r: r.request.method == "GET" and r.url.endswith("/api/next/curation"),
    ) as refreshed:
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    return refreshed.value


@pytest.mark.parametrize(
    ("kind", "status", "detail"),
    [
        ("curation", 409, "a curation is already running"),
        ("tests", 409, "Delivery is stopping"),
    ],
)
def test_post_refusals_survive_the_action_refresh_and_later_reads(maintenance, pds, kind, status, detail):
    from playwright.sync_api import expect  # noqa: PLC0415 - optional browser runtime

    page, base, state = maintenance
    state.update(post=status, detail=detail)
    page.goto(f"{base}/maintenance#token=tok")
    marker = start(page, pds, kind)
    expect(page.locator("#curation")).to_contain_text(marker)
    notice = page.locator(f"#{kind}-refused")
    expect(notice).to_contain_text(detail[0].upper() + detail[1:])
    marker = refresh(page).json()["folders"][0]["summary"]
    expect(page.locator("#curation")).to_contain_text(marker)
    expect(notice).to_be_visible()
    notice.get_by_role("button", name="Dismiss", exact=True).click()
    expect(notice).to_have_count(0)


@pytest.mark.parametrize(("kind", "status"), [("curation", 500), ("curation", 404), ("tests", 500)])
def test_failed_reads_retain_last_good_data_and_offer_a_working_retry(maintenance, kind, status):
    from playwright.sync_api import expect  # noqa: PLC0415 - optional browser runtime

    page, base, state = maintenance
    page.goto(f"{base}/maintenance#token=tok")
    expect(page.get_by_role("button", name="Review tests", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Curate shop now", exact=True)).to_be_visible()
    state[kind] = status
    refresh(page)
    notice = page.locator(f"#{kind}-error")
    expect(notice).to_contain_text("read failed")
    expect(notice).to_contain_text("last")
    expect(page.get_by_role("button", name="Review tests", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Curate shop now", exact=True)).to_be_visible()
    state[kind] = 200
    page.locator(f"#{kind}-retry").click()
    expect(notice).to_have_count(0)


def test_a_first_curation_server_failure_is_visible_not_capability_absence(maintenance):
    from playwright.sync_api import expect  # noqa: PLC0415 - optional browser runtime

    page, base, state = maintenance
    state["curation"] = 500
    page.goto(f"{base}/maintenance#token=tok")
    expect(page.locator("#curation-title")).to_be_visible()
    expect(page.locator("#curation-error")).to_contain_text("read failed")


def test_a_clone_without_the_curation_route_does_not_offer_the_capability(maintenance):
    from playwright.sync_api import expect  # noqa: PLC0415 - optional browser runtime

    page, base, state = maintenance
    state["curation"] = 404
    page.goto(f"{base}/maintenance#token=tok")
    expect(page.get_by_role("button", name="Review tests", exact=True)).to_be_visible()
    expect(page.locator("#curation-title")).to_have_count(0)
    expect(page.locator("#curation-error")).to_have_count(0)


@pytest.mark.parametrize("next_kind", ["tests", "curation"])
def test_an_unrelated_success_does_not_acknowledge_another_folders_refusal(maintenance, pds, next_kind):
    from playwright.sync_api import expect  # noqa: PLC0415 - optional browser runtime

    page, base, state = maintenance
    page.goto(f"{base}/maintenance#token=tok")
    expect(page.locator("#curation")).to_contain_text(start(page, pds, "curation"))
    expect(page.locator("#curation-refused")).to_be_visible()
    state["post"] = 200
    expect(page.locator("#curation")).to_contain_text(start(page, pds, next_kind, folder="other"))
    expect(page.locator("#curation-refused")).to_contain_text("Refused by host")


@pytest.mark.parametrize("kind", ["curation", "tests"])
def test_a_relevant_success_acknowledges_its_own_refusal(maintenance, pds, kind):
    from playwright.sync_api import expect  # noqa: PLC0415 - optional browser runtime

    page, base, state = maintenance
    page.goto(f"{base}/maintenance#token=tok")
    expect(page.locator("#curation")).to_contain_text(start(page, pds, kind))
    expect(page.locator(f"#{kind}-refused")).to_be_visible()
    state["post"] = 200
    expect(page.locator("#curation")).to_contain_text(start(page, pds, kind))
    expect(page.locator(f"#{kind}-refused")).to_have_count(0)


def test_an_older_failed_refresh_cannot_replace_a_newer_success(maintenance):
    from playwright.sync_api import expect  # noqa: PLC0415 - optional browser runtime

    page, base, state = maintenance
    page.goto(f"{base}/maintenance#token=tok")
    expect(page.get_by_role("button", name="Curate shop now", exact=True)).to_be_visible()
    before = state["reads"]
    state["hold_next"] = True
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function("window.maintenanceReadHeld === true")
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    marker = f"Read generation {before + 2}"
    expect(page.locator("#curation")).to_contain_text(marker)
    state["held"].fulfill(status=500, json={"detail": "superseded read failed"})
    page.wait_for_load_state("networkidle")
    expect(page.locator("#curation")).to_contain_text(marker)
    expect(page.locator("#curation-error")).to_have_count(0)
