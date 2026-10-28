"""The owner can resume a paused cleanup decision, but cannot resume an actually finished Change."""

import socket
import threading
import time
from datetime import UTC, datetime

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import Brief, Change, Exit, Option, Question, Step, StepKind
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.state_store.store import Lock, Store

NOW = datetime(2026, 10, 24, tzinfo=UTC)


@pytest.mark.browser
@pytest.mark.parametrize("abandon", [False, True])
@pytest.mark.parametrize("finished", [False, True])
def test_cleanup_resume_uses_actual_completion_not_the_displayed_done_label(  # noqa: PLR0915 - one owner journey
    tmp_path,
    pds,
    abandon,
    finished,
):
    from playwright.sync_api import expect, sync_playwright  # noqa: PLC0415 - optional browser runtime

    store = Store(tmp_path)
    c = Change(slug="c1", brief=Brief(version=1, title="Preserve remote work"),
               step=Step(kind=StepKind.CLEANUP, mode="abandon" if abandon else None))  # fmt: skip
    if abandon:
        c.intent.abandoned_at = NOW
    q = Question(
        step=StepKind.CLEANUP, text="Keep the moved remote branch?", cause="state:cleanup:branch-moved",
        options=[Option(id="keep", label="Keep", next="retry"), Option(id="pause", label="Pause", next="pause")],
    )  # fmt: skip
    c = loop.apply(c, loop.StepResult(exit=Exit.ASK, question=q), NOW)
    qid = loop.open_question(c).id
    c = loop.fold(c, [AnswerItem(at=NOW, question=qid, option="pause")], NOW)
    if finished:
        c.finished_at, c.outcome = NOW, None
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
                with page.expect_response(lambda r: r.url.endswith("/api/next/changes/c1")) as detail:
                    page.goto(f"{base}/?change=c1#token=tok")
                assert detail.value.json()["finished"] is finished
                expect(page.get_by_role("heading", name="c1", exact=True)).to_be_visible()
                expect(page.get_by_text(q.text, exact=True)).to_have_count(0)
                resume = page.get_by_role("button", name="Resume", exact=True)
                if finished:
                    expect(resume).to_have_count(0)
                    expect(page.get_by_role("button", name="Pause", exact=True)).to_have_count(0)
                else:
                    expect(resume).to_be_visible()
                    with page.expect_response(
                        lambda r: r.request.method == "POST" and r.url.endswith("/changes/c1/intent"),
                    ) as accepted:
                        resume.click()
                    assert accepted.value.status == 200
                    restored, _ = store.fold(Lock("c1"), "c1", NOW)
                    assert restored.intent.paused_at is None
                    assert restored.step.mode == ("abandon" if abandon else None)
                    assert loop.next_step(restored, NOW) is not None
            finally:
                browser.close()
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()
        assert not thread.is_alive()


@pytest.mark.browser
def test_a_resume_left_unanswered_is_not_sent_again_and_a_slow_read_is_not_called_down(tmp_path, pds):
    """A timed-out write may have been done: the page reads the Change again instead of sending it twice."""
    from playwright.sync_api import expect, sync_playwright  # noqa: PLC0415 - optional browser runtime

    store = Store(tmp_path)
    c = Change(slug="c1", brief=Brief(version=1, title="Slow host"))
    c.intent.paused_at = NOW
    store.write(Lock("c1"), c)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host(store, tmp_path)), log_level="warning"))
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
                held = []  # what Delivery takes but never answers: up, yet busy

                def hold(route) -> None:
                    held.append(route)

                page.route("**/api/next/changes/c1/intent", hold)
                page.get_by_role("button", name="Resume", exact=True).click()
                expect(page.locator("#detail .refused")).to_contain_text(
                    "Delivery did not answer within 5 s, so this may have been done or not. It was not sent again; "
                    "the page now shows Delivery's state as read again.",
                    timeout=10000,
                )
                expect(page.locator("#detail .refused p-inline-notification")).to_have_attribute("state", "warning")
                expect(page.get_by_role("button", name="Resume", exact=True)).to_be_visible()  # as read again
                page.route("**/api/next/changes**", hold)
                expect(page.locator("#error")).to_have_text(
                    "Delivery is slow to answer: no reply within 5 s. Try again in a moment.", timeout=15000
                )
                expect(page.locator("#detail")).to_have_class("stale")
                assert [r.request.method for r in held].count("POST") == 1  # never sent again
            finally:
                browser.close()
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()
        assert not thread.is_alive()
