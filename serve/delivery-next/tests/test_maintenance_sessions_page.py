"""The held maintenance session is released only after the owner confirms a reboot, by its captured identity."""

from __future__ import annotations

import socket
import threading
import time
from typing import TYPE_CHECKING

import pytest
import uvicorn

from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from pathlib import Path

HELD = {
    "sessions": [
        {
            "id": "s-1",
            "project": "p",
            "kind": "pack",
            "started_at": "2026-10-25T00:00:00+00:00",
            "workspace": "/w/s-1",
            "reason": "no Run returned",
            "state": "held",
            "recoverable": True,
        },
    ],
}


@pytest.mark.browser
def test_a_held_session_is_released_only_after_a_confirmed_reboot_by_its_captured_id(tmp_path: Path, pds) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(Store(tmp_path), "tok", None), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    posted: list[tuple[str, str | None]] = []
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)

            def sessions(route) -> None:
                if route.request.method == "POST":
                    posted.append((route.request.url, route.request.post_data))
                    route.fulfill(status=409, json={"detail": "this maintenance session is no longer held"})
                    return
                route.fulfill(json=HELD)

            page.route("**/maintenance/sessions**", sessions)
            page.goto(f"{base}/maintenance#token=tok")
            expect(page.locator("#sessions > li")).to_have_count(1)
            release = page.get_by_role("button", name="Release this session")
            expect(release).to_be_disabled()
            page.get_by_label("The computer has rebooted since this session failed").check()
            expect(release).to_be_enabled()
            release.click()
            page.get_by_role("button", name="Release", exact=True).click()
            expect(page.locator("#sessions")).to_contain_text("no longer held")
            assert len(posted) == 1
            url, body = posted[0]
            assert url.endswith("/maintenance/sessions/s-1/recover")
            assert body is not None
            assert '"rebooted":true' in body.replace(" ", "")
            browser.close()
    finally:
        server.should_exit = True
