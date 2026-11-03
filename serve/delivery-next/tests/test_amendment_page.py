"""The Brief panel's amendments and the owner's amendment question in a real browser (TD-185, design §8 item 13)."""

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
from owlbear_delivery_next.change_contracts.amend_tools import CandidateItem, CandidateResult, VerdictResult
from owlbear_delivery_next.change_contracts.amendment_records import AmendedItem
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
from owlbear_delivery_next.change_flow import amending, loop
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store.store import Lock, Store

if TYPE_CHECKING:
    from collections.abc import Iterator

NOW = datetime(2026, 11, 4, 9, tzinfo=UTC)
SLUG = "greet"
DECLINED = "Newlines must stay trimmed too"


class Host:
    maintenance = None
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    def activity(self, _slug: str) -> Activity:
        return Activity(host_up=True)


def approved() -> m.Change:
    """Brief v3 approved and building: AC-1 generated, AC-2 the owner's."""
    brief = m.Brief(
        version=3, approved_version=3, challenged=3, approved_at=NOW, title="Greet", outcome="greet(name) greets",
        scope=["packages/app"], specified=["AC-2"],
        criteria=[m.Criterion(id="AC-1", text="greet() trims the name"), m.Criterion(id="AC-2", text="Says Hallo")],
    )  # fmt: skip
    plan = m.Plan(tasks=[m.Task(id="t1", title="one", scope=["a.txt"])])
    c = m.Change(slug=SLUG, brief=brief, plan=plan, step=m.Step(kind=m.StepKind.BUILD, task="t1"))
    brief.approved = [brief.model_copy(deep=True)]
    return c


def proposed(c: m.Change, key: str, text: str, reason: str, **said: Any) -> None:
    """A worker's amendment of criterion *key* to *text*, prepared and judged in one clean round."""
    amending.start(c, "worker", reason=reason, now=NOW)
    amending.prepared(c, CandidateResult(items=[CandidateItem(field="criterion", key=key, text=text, why=reason)]),
                      RoundPolicy(), NOW)  # fmt: skip
    amending.judged(c, VerdictResult(**{"verdict": "equivalent", "reasons": "AC-3 covers it"} | said), "ch", NOW)


def answered(c: m.Change, option: str, text: str = "") -> None:
    q = loop.open_question(c)
    assert q is not None
    assert amending.answered(c, AnswerItem(question=q.id, option=option, text=text, at=NOW), NOW, [])


def applied_and_declined() -> m.Change:
    """A1 applied alone as v4; A2, a weaker one, declined with his reason."""
    c = approved()
    proposed(c, "AC-1", "greet() trims spaces", "AC-1 is over-specific", qualifies=True)
    proposed(c, "AC-1", "greet() trims spaces and tabs", "tabs are spaces too", verdict="weaker",
             reasons="drops the trim of newlines")  # fmt: skip
    answered(c, "within", DECLINED)
    return c


def tightening_asked() -> m.Change:
    """A3, a tightening of the owner's AC-2, waits on his question."""
    c = applied_and_declined()
    proposed(c, "AC-2", "Says Hallo in bold", "the design asks for bold",
             tightening="AC-2 now also checks the weight: one more visual state, about 2 credits")  # fmt: skip
    return c


@pytest.fixture
def page_url(tmp_path) -> Iterator[tuple[Store, str]]:
    store = Store(tmp_path)
    store.write(Lock(SLUG), approved())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    # longer than the pages' polls: route.fetch() reuses a pooled socket, which uvicorn's 5 s default closes
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


def big_enough(target: Any) -> None:
    """WCAG 2.5.8: a control at least 24 by 24 CSS pixels."""
    box = target.bounding_box()
    assert box is not None
    assert (box["width"] >= 24, box["height"] >= 24) == (True, True), box


def posted(page: Any, path: str) -> Any:
    return page.expect_response(lambda r: r.request.method == "POST" and r.url.split("?")[0].endswith(path))


@pytest.mark.browser
def test_the_brief_panel_lists_each_amendment_and_takes_an_objection_to_an_applied_one(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    with opened(base, pds) as page:
        part = page.locator(".brief section").filter(has=page.get_by_role("heading", name="Amendments", exact=True))
        expect(part).to_contain_text("Current version v3; reference version v3, from which the challenger judges")
        expect(part).to_contain_text("None.")  # none yet: the part says so instead of an empty list

        c = applied_and_declined()
        c.amendments[1].unreviewed = True  # its final wording was revised after its last round
        c.amendments[0].items.append(AmendedItem(field="check", key="check-1", old="it greets", new="it greets twice",
                                                 steps=["open /"], covers=["AC-1"]))  # fmt: skip
        store.write(Lock(SLUG), c)
        page.reload()
        expect(part).to_contain_text("Current version v4; reference version v3")
        expect(part).to_contain_text("Earlier versions, kept unchanged: v3")
        first = part.locator(".amendment", has_text="A1, proposed at the build step")
        for said in ["criterion AC-1", "greet() trims the name → greet() trims spaces",
                     "AC-1 is over-specific (from a worker)", "session ch: equivalent: AC-3 covers it",
                     "applied, made v4, applied by Delivery alone",
                     "it greets → it greets twice (steps: open /) (covers AC-1)"]:  # fmt: skip
            expect(first).to_contain_text(said)
        second = part.locator(".amendment", has_text="A2, proposed at the build step")
        for said in ["greet() trims spaces → greet() trims spaces and tabs",
                     "weaker (on an earlier wording): drops the trim", "declined", "Your reason",
                     DECLINED]:  # fmt: skip
            expect(second).to_contain_text(said)
        expect(second.get_by_role("button", name="Object")).to_have_count(0)  # only an applied one takes it

        obj = first.get_by_role("button", name="Object")
        big_enough(obj)
        obj.click()
        dialog = page.locator("p-modal.ask")
        expect(dialog.get_by_role("heading", name="Object to amendment A1?")).to_be_visible()
        for said in ["Work that depends on it pauses once the running step ends", "revert it as a new brief version",
                     "merged or published work can't be undone", "The amendment stays applied"]:  # fmt: skip
            expect(dialog).to_contain_text(said)
        dialog.get_by_role("button", name="Keep it as it is").click()
        expect(dialog).to_have_count(0)
        expect(obj).to_be_focused()  # focus returns where it came from
        obj.click()
        with posted(page, "/amendments/A1/objection") as reply:
            page.locator("p-modal.ask").get_by_role("button", name="Object", exact=True).click()
        assert reply.value.status == 200
        with store.db.read() as db:
            assert '"amendment":"A1"' in db.execute("SELECT item FROM inbox").fetchone()[0].replace(" ", "")


@pytest.mark.browser
def test_the_question_on_a_tightening_says_what_it_sets_off_and_its_one_primary_action_is_answer(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock(SLUG), tightening_asked())
    with opened(base, pds) as page:
        first = page.locator(".brief .amendment", has_text="A1, proposed at the build step")
        expect(first).to_contain_text("Object: not now, an amendment runs now; object after it ends.")
        expect(page.locator(".brief .amendment", has_text="A3, proposed")).to_contain_text("in progress")

        form = page.locator("section.act", has_text="Amend the approved brief v4 (A3, from a worker)?")
        for said in ["criterion AC-2: 'Says Hallo' -> 'Says Hallo in bold'", "Reason: the design asks for bold",
                     "Challenger: equivalent - AC-3 covers it",
                     "Tightening, its scope and cost: AC-2 now also checks the weight: one more visual state",
                     "Redone after it: the final review."]:  # fmt: skip
            expect(form).to_contain_text(said)
        labels = form.locator("p-radio-group-option")
        expect(labels).to_have_count(4)
        assert [labels.nth(i).get_attribute("label") for i in range(4)] == [
            "Yes: apply it",
            "No: work on within the approved brief (your reason goes to the work)",
            "Reshape the brief with the shaper",
            "Stop the Change",
        ]
        actions = form.locator("p-button")
        expect(actions).to_have_count(1)  # one primary action, and it is never Stop
        expect(actions).to_have_text("Answer")
        go = form.get_by_role("button", name="Answer")
        big_enough(go)

        form.get_by_label("Yes: apply it").check()
        go.click()
        dialog = page.locator("p-modal.ask")
        expect(dialog.get_by_role("heading", name="Yes: apply it?")).to_be_visible()
        for said in ["applies as a new brief version, as approved by you; earlier versions stay unchanged",
                     "Evidence it touches no longer counts", "the final review and the checks it affects run again",
                     "This uses AI credits", "You can object to it later on the Brief panel"]:  # fmt: skip
            expect(dialog).to_contain_text(said)
        dialog.get_by_role("button", name="Back to the options").click()
        expect(dialog).to_have_count(0)
        expect(go).to_be_focused()
        go.click()
        with posted(page, "/answers") as reply:
            page.locator("p-modal.ask").get_by_role("button", name="Yes: apply it").click()
        assert reply.value.status == 200
