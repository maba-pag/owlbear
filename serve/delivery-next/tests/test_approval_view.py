"""The brief approval view in a real browser (TD-122, TD-179): the agreement open, technical details collapsed."""

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
from owlbear_delivery_next.change_contracts.decision_records import Pick, PickedDecision
from owlbear_delivery_next.change_contracts.round_records import RoundLoop, RoundPolicy
from owlbear_delivery_next.change_contracts.visual_records import OwnerCriterion
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store.store import Lock, Store

if TYPE_CHECKING:
    from collections.abc import Iterator

NOW = datetime(2026, 10, 16, 2, tzinfo=UTC)
MINE, LEFT_TO_SHAPER = "Turns the hero 180 degrees in under 300 ms", "A second press returns the hero"


class Host:
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    def activity(self, _slug: str) -> Activity:
        return Activity(host_up=True)


def change() -> m.Change:
    decisions = [
        m.BriefDecision(question="Where does the button sit?", answer="Top right of the hero", origin="decided"),
        m.BriefDecision(question="Animation length", answer="250 ms ease-out", origin="autonomous"),
        m.BriefDecision(question="Hero motion", answer="Never autoplay", origin="decided", scope="project"),
    ]
    brief = m.Brief(
        version=2, challenged=2, title="Flip the hero", outcome="Visitors flip the hero image with one button.",
        criteria=[m.Criterion(id="AC-1", text=MINE), m.Criterion(id="AC-2", text=LEFT_TO_SHAPER)],
        visual=[m.VisualState(name="flipped", path="/", expect="The hero faces left")], ui=True,
        decisions=decisions, non_goals=["Saving the direction"], specified=["AC-1"],
        picked=Pick(version=2, status="ok", decisions=[
            PickedDecision(id="D-1", revision="r1", title="Motion stays subtle", statement="No motion over 300 ms."),
        ]),
    )  # fmt: skip
    checks = [m.PersonCheck(id="feel", steps=["Flip five times"], expect="No stutter")]
    return m.Change(slug="flip", brief=brief, checks=checks, step=m.Step(kind=m.StepKind.SHAPE))


@pytest.fixture
def page_url(tmp_path) -> Iterator[tuple[Store, str]]:
    store = Store(tmp_path)
    store.write(Lock("flip"), change())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    yield store, f"http://127.0.0.1:{sock.getsockname()[1]}"
    server.should_exit = True


@contextlib.contextmanager
def opened(base: str, slug: str, pds: Any) -> Iterator[Any]:
    """The Changes page on *slug* in a real browser: only the test host and the PDS CDN answer."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/?change={slug}")
        yield page
        browser.close()


STAGES = ["Shape", "Plan", "Build", "Final review", "Publish", "Visual check", "Your checks", "Merge"]


@pytest.mark.browser
def test_the_agreement_keeps_details_collapsed_and_the_approved_brief_lists_the_owners_additions(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    with opened(base, "flip", pds) as page:
        expect(page.locator("ol.stepper > li > span > span:first-child")).to_have_text(STAGES)
        current = page.locator("ol.stepper > li[aria-current]")
        expect(current).to_have_count(1)
        expect(current).to_have_attribute("aria-current", "step")
        expect(current).to_contain_text("Shape")
        expect(page.locator("ol.stepper .loops")).to_have_count(0)  # no stage looped yet
        brief = page.locator(".brief").first
        yours = brief.locator("section", has_text="Your decisions")
        expect(yours).to_contain_text("Top right of the hero")
        expect(yours).to_contain_text("Never autoplay (lasting: applies to later Changes too)")  # C-14
        expect(yours.get_by_text("Top right of the hero (lasting", exact=False)).to_have_count(0)
        expect(yours).to_contain_text(MINE)  # an owner-stated criterion is part of his agreement
        expect(brief.locator("section", has_text="Choices proposed by the shaper")).to_contain_text("250 ms")
        expect(brief.locator("section", has_text="Not in this Change")).to_contain_text("Saving the direction")
        expect(brief.locator("section", has_text="Decisions this work follows")).to_contain_text("Motion stays subtle")
        expect(brief.locator("summary")).to_contain_text("2 criteria \u00b7 1 screen \u00b7 1 check for you")
        expect(page.get_by_text(LEFT_TO_SHAPER, exact=False)).to_be_hidden()  # collapsed until opened
        page.get_by_role("button", name="Approve brief v2").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        said = pds.modal(page)
        expect(said).to_contain_text("including its technical details (2 criteria \u00b7 1 screen \u00b7 1 check")
        expect(said).to_contain_text("Do your check once the pull request's checks pass")
        page.get_by_role("button", name="Keep it waiting").click()
        expect(dialog).to_be_hidden()
        assert store.read("flip").brief.approved_version is None  # declining approves nothing

        built = change().model_copy(update={"step": m.Step(kind=m.StepKind.BUILD)})
        built.brief = built.brief.model_copy(update={"approved_version": 2, "approved_at": NOW})
        added = OwnerCriterion(id="O-1", text="The caption stays readable", round=1, brief_version=2, at=NOW)
        built.owner_criteria = [added]
        built.budgets.loops["scope:src/a"] = 2  # two task reviews sent the build back: its third round
        store.write(Lock("flip"), built)
        page.reload()
        since = page.locator(".brief section", has_text="Changes since you approved")
        expect(since).to_contain_text("You added in visual round 1")
        expect(since).to_contain_text("The caption stays readable")
        expect(page.locator(".brief").first).to_contain_text("Your approval accepted these choices.")
        expect(current).to_contain_text("Build")
        expect(current.locator(".loops [aria-hidden=true]")).to_have_text("\u00d73")
        expect(current.locator(".loops .sr")).to_have_text("3 rounds")
        expect(page.locator("ol.stepper .loops")).to_have_count(1)


@pytest.mark.browser
def test_an_unreviewed_last_revision_is_approved_only_once_the_owner_ticks_that_he_accepts_it(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    tail = change().model_copy(update={"slug": "tail"})
    tail.loops["brief"] = RoundLoop(subject="brief", policy=RoundPolicy(), round=3, ended="max", unreviewed=["v2"])
    store.write(Lock("tail"), tail)
    with opened(base, "tail", pds) as page:
        page.get_by_role("button", name="Approve brief v2").click()
        dialog = pds.modal(page)
        confirm = dialog.get_by_role("button", name="Approve and start")
        expect(confirm).to_be_disabled()  # TD-255
        dialog.get_by_label("no challenger reviewed that revision", exact=False).check()
        expect(confirm).to_be_enabled()
        confirm.click()
        expect(page.get_by_role("dialog")).to_be_hidden()
        page.wait_for_timeout(500)
    assert store.fold(Lock("tail"), "tail", NOW)[0].brief.approved_version == 2


def sent(store: Store, slug: str) -> str:
    """The one inbox item the page sent; the answer may still be on its way when the page shows it."""
    until = time.monotonic() + 5
    while True:
        with store.db.read() as db:
            rows = db.execute("SELECT item FROM inbox WHERE slug = ?", (slug,)).fetchall()
        if rows or time.monotonic() > until:
            [(item,)] = rows
            return item
        time.sleep(0.05)


def asking() -> m.Change:
    """A Change waiting on the owner's answer to an ordinary build question."""
    options = [m.Option(id="de", label="German"), m.Option(id="en", label="English")]
    question = m.Question(id="q1", step=m.StepKind.BUILD, text="Which language?", options=options)
    outcome = m.Outcome(exit=m.Exit.ASK, question="q1", reason="Which language?", who="you", at=NOW)
    return m.Change(slug="greet", questions=[question], outcome=outcome, step=m.Step(kind=m.StepKind.BUILD))


@pytest.mark.browser
def test_an_answer_being_typed_survives_polls_that_bring_new_activity_and_is_sent(page_url, pds) -> None:
    """TD-264: the answer's draft lives in page state; a poll with new data renders the detail again around it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())
    with opened(base, "greet", pds) as page:
        form = page.locator("section.act", has_text="Question q1")
        expect(form).to_contain_text("Which language?")
        form.get_by_label("English").check()
        words = form.get_by_label("Your answer in words")
        words.fill("the site is read in Canada")
        store.log(Lock("greet"), "greet", {"event": "brief", "version": 9, "at": NOW.isoformat()})
        expect(page.locator(".log")).to_contain_text("Brief v9 saved", timeout=10_000)  # a poll rendered it again
        expect(words).to_have_value("the site is read in Canada")
        expect(form.get_by_label("English")).to_be_checked()
        expect(page.locator("#changes .card.current")).to_contain_text("greet")
        form.get_by_role("button", name="Answer").click()
        expect(page.locator("#detail")).not_to_contain_text("Not done")
    item = sent(store, "greet")
    assert '"option":"en"' in item.replace(" ", "")
    assert "the site is read in Canada" in item


@pytest.mark.browser
def test_choosing_another_change_and_going_back_keeps_the_address_and_the_list(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())
    with opened(base, "flip", pds) as page:
        expect(page.locator("#detail h2")).to_have_text("flip")
        expect(page.locator("#changes")).to_contain_text("Needs you (")
        page.locator("#changes a[data-key='greet']").click()
        expect(page.locator("#detail h2")).to_have_text("greet")
        assert page.evaluate("location.search") == "?change=greet"
        page.go_back()
        expect(page.locator("#detail h2")).to_have_text("flip")
        page.get_by_role("button", name="All Changes").click()
        expect(page.locator("#board")).not_to_have_class("open")
        assert page.evaluate("location.search") == ""


@pytest.mark.parametrize("left", [["de", "fr"], []])
@pytest.mark.browser
def test_an_option_the_question_no_longer_offers_is_not_sent(page_url, left, pds) -> None:
    """Sol, TD-264: a choice dropped from the question by a later poll leaves the draft too, even with none left."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())
    with opened(base, "greet", pds) as page:
        form = page.locator("section.act", has_text="Question q1")
        form.get_by_label("English").check()
        changed = asking()
        labels = {"de": "German", "fr": "French"}
        changed.questions[0].options = [m.Option(id=o, label=labels[o]) for o in left]
        store.write(Lock("greet"), changed)
        expect(form.get_by_role("radio")).to_have_count(len(left), timeout=10_000)
        expect(form.get_by_role("radio", checked=True)).to_have_count(0)
        form.get_by_role("button", name="Answer").click()
        expect(page.locator("#detail")).not_to_contain_text("Not done")
    assert '"option":null' in sent(store, "greet").replace(" ", "")
