"""A terminal delivery mismatch has a usable owner choice, including while paused."""

import socket
import threading
import time
from datetime import UTC, datetime

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.models import Change, Names, Step, StepKind
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.state_store.store import Lock, Store

NOW = datetime(2026, 10, 24, tzinfo=UTC)


@pytest.mark.browser
@pytest.mark.parametrize("paused", [False, True])
def test_the_owner_can_abandon_a_wrong_delivery_without_approving_it(tmp_path, pds, paused):
    from playwright.sync_api import expect, sync_playwright  # noqa: PLC0415 - optional browser runtime

    store = Store(tmp_path)
    c = Change(slug="c1", step=Step(kind=StepKind.MERGE), names=Names(pr=7, branch="owlbear/c1", target="release"))
    if paused:
        c.intent.paused_at = NOW
    c, ready = loop.schedule(c, [], NOW, "misdelivered")
    assert ready is None
    store.write(Lock("c1"), c)
    host = Host(store, tmp_path)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", host), log_level="warning"))
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
                page.goto(f"{base}/?change=c1#token=tok")
                expect(page.get_by_text("Delivery has not fulfilled", exact=False).first).to_be_visible()
                page.get_by_label("Abandon without delivery credit", exact=True).check()
                page.get_by_role("button", name="Answer", exact=True).click()
                modal = pds.modal(page)
                expect(modal).to_contain_text("marked abandoned")
                with page.expect_response(
                    lambda r: r.request.method == "POST" and r.url.endswith("/changes/c1/answers"),
                ) as accepted:
                    modal.get_by_role("button", name="Abandon", exact=True).click()
                assert accepted.value.status == 200
                after, _ = store.fold(Lock("c1"), "c1", NOW, "misdelivered")
                assert after.step.kind is StepKind.CLEANUP
                assert after.step.mode == "abandon"
                assert after.finished_at is None
                assert after.stop is None
                assert loop.next_step(after, NOW) is not None
            finally:
                browser.close()
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()
        assert not thread.is_alive()
