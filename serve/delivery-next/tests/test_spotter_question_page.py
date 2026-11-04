"""The Changes page on a question the Spotter stopped a step to ask (#717), driven in a real browser.

Allowing what the Spotter stopped starts a brief amendment (TD-185): the Brief panel lists it as from his Allow it and
the question is not asked again. The page shows an answer the host refused beside the question.
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
from owlbear_delivery_next.change_contracts.round_records import FINAL, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import answer_kinds, round_flow
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
    failed = ""
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    def activity(self, _slug: str) -> Activity:
        return Activity(host_up=True)


def stopped() -> m.Change:
    """A Change whose plan the Spotter stopped to ask the owner."""
    brief = m.Brief(version=1, approved_version=1, challenged=1, outcome="The shop lists its products")
    brief.approved = [brief.model_copy(deep=True)]
    c = m.Change(slug=SLUG, brief=brief, step=m.Step(kind=m.StepKind.PLAN))
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
def opened(base: str, pds: Any, *, details: bool = False) -> Iterator[Any]:
    """The Changes page on the stopped Change in a real browser, its details shown or not: only the test host and the
    PDS CDN answer."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        if details:
            page.add_init_script("localStorage.setItem('owlbear-improvement-detail', 'on');")
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
def test_allowing_what_the_spotter_stopped_starts_an_amendment_instead_of_asking_again(page_url, pds) -> None:
    """The answer reaches the amendment path (design §8 item 7): listed from his Allow it, no question comes back."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    with opened(base, pds, details=True) as page:  # its amendment shows with the details
        first = page.locator("section.act", has_text="Question q1")
        first.get_by_label("Allow it", exact=False).check()
        assert answer(page, first).status == 200
        store.fold(Lock(SLUG), SLUG, NOW)
        listed = page.locator(".brief .amendment", has_text="A1, proposed at the plan step")
        expect(listed).to_contain_text("the owner allowed it. (from your Allow it)", timeout=10_000)
        expect(listed).to_contain_text("in progress")
        expect(page.locator("section.act", has_text="Question")).to_have_count(0)
    c = store.read(SLUG)
    assert (c.amending.id, c.amendments[0].source, c.questions[0].answer.option) == ("A1", "allow", "allow")


@pytest.mark.browser
def test_an_answer_without_an_option_is_refused_beside_the_question_at_once(page_url, pds) -> None:
    """Answer clicked on the question asked again, its options cleared: refused at once, never queued for the fold."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    with opened(base, pds) as page:
        form = page.locator("section.act", has_text="Question q1")
        assert answer(page, form).status == 422
        expect(form.locator(".refused")).to_contain_text("choose one of")
    with store.db.read() as db:
        assert db.execute("SELECT count(*) FROM inbox").fetchone() == (0,)


@pytest.mark.browser
def test_an_answer_the_fold_did_not_apply_is_shown_with_its_reason_on_the_question(page_url, pds) -> None:
    """#791's activity line, beside the question it was meant for while that question stays open."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    why = "question q1 is settled only by one of its options, a reconsideration by a note"
    store.log(Lock(SLUG), SLUG, {"event": "answer-not-applied", "at": NOW.isoformat(), "question": "q1", "reason": why})
    with opened(base, pds) as page:
        form = page.locator("section.act", has_text="Question q1")
        expect(form.locator(".refused")).to_contain_text(f"was not applied: {why}")


@pytest.mark.browser
def test_an_answer_the_fold_did_not_apply_is_shown_on_the_final_reviews_question_too(page_url, pds) -> None:
    """The final review's last-round question has its own form; a stale Rebuild the fold refused shows on it too."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    t1 = m.Task(id="t1", title="one", scope=["x.txt"])
    finding = RoundFinding(id="F1", text="x.txt:1: p - fix: f", raised=1, tasks=["t1"])
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(max_rounds=1), round=1, found=1, last=True, findings=[finding])
    lp.head = "a" * 40
    c = m.Change(slug=SLUG, plan=m.Plan(tasks=[t1]), step=m.Step(kind=m.StepKind.BUILD, task="t1"), loops={FINAL: lp})
    ask(c, round_flow.question(lp, t1), NOW)
    store.write(Lock(SLUG), c)
    why = "question q1: the page showed an earlier attempt or head; reload"
    store.log(Lock(SLUG), SLUG, {"event": "answer-not-applied", "at": NOW.isoformat(), "question": "q1", "reason": why})
    with opened(base, pds) as page:
        form = page.locator("section.act", has_text="Question q1")
        expect(form).to_contain_text("Plan tasks to rebuild")
        expect(form.locator(".refused")).to_contain_text(f"was not applied: {why}")
