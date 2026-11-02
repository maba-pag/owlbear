"""The Changes page on a question the Spotter stopped a step to ask (#717), driven in a real browser.

Allowing what the Spotter stopped is held: the answer is kept and the same question is asked again. The page says so
on the question asked again, and shows an answer the host refused beside the question.
"""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_flow import answer_kinds
from owlbear_delivery_next.change_flow.moves import ask
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store.store import Lock, Store

if TYPE_CHECKING:
    from collections.abc import Iterator

NOW = datetime(2026, 11, 2, 9, 55, tzinfo=UTC)
STOPPED = "The Spotter stopped this step for irreversible harm: it would force-push over main."
SLUG = "steer"


class Host:
    maintenance = None
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    def activity(self, _slug: str) -> Activity:
        return Activity(host_up=True)


def stopped() -> m.Change:
    """A Change whose plan the Spotter stopped to ask the owner."""
    c = m.Change(slug=SLUG, step=m.Step(kind=m.StepKind.PLAN))
    ask(c, answer_kinds.spotter(m.StepKind.PLAN, STOPPED), NOW)
    return c


@pytest.fixture
def page_url(tmp_path) -> Iterator[tuple[Store, str]]:
    store = Store(tmp_path)
    store.write(Lock(SLUG), stopped())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(
        uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning", timeout_keep_alive=60)
    )
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    yield store, f"http://127.0.0.1:{sock.getsockname()[1]}"
    server.should_exit = True


@contextlib.contextmanager
def opened(base: str, pds: Any) -> Iterator[Any]:
    """The Changes page on the stopped Change in a real browser: only the test host and the PDS CDN answer."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/?change={SLUG}")
        yield page
        browser.close()


def answer(page: Any, form: Any) -> Any:
    """Click Answer and wait for the host's reply to it."""
    posted = page.expect_response(lambda r: r.request.method == "POST" and r.url.split("?")[0].endswith("/answers"))
    with posted as reply:
        form.get_by_role("button", name="Answer").click()
    return reply.value


@pytest.mark.browser
def test_allowing_what_the_spotter_stopped_shows_on_the_question_asked_again(page_url, pds) -> None:
    """The answer is held, so the question comes back; it says when he allowed it and why it is asked again."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    with opened(base, pds) as page:
        first = page.locator("section.act", has_text="Question q1")
        expect(first).not_to_contain_text("You chose Allow it")
        first.get_by_label("Allow it", exact=False).check()
        assert answer(page, first).status == 200
        store.fold(Lock(SLUG), SLUG, NOW)
        again = page.locator("section.act", has_text="Question q2")
        expect(again).to_contain_text("You chose Allow it at ", timeout=10_000)
        expect(again).to_contain_text("it needs a brief amendment, which isn't built yet (item 16), so the step "
                                      "stays stopped and the question is asked again")  # fmt: skip
