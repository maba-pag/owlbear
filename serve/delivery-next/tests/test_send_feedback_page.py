"""What a click that sends shows on the Changes page (pages/sending/feedback.mjs), driven in a real browser.

The question form's Answer goes through the page's one send path: held, refused, timed out, lost and accepted
requests show on the button, its form and a live region, while a second form of the same Change stays usable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from playwright.sync_api import expect

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import Lock, Store

from .test_approval_view import served
from .test_improvement_page import SLUG as SPOTTED
from .test_improvement_page import machine_page
from .test_machine_pages import browsing, chats, clone, shaping, until
from .test_spotter_question_page import NOW, SLUG, Host, opened, stopped

if TYPE_CHECKING:
    from collections.abc import Iterator

ANSWERS = f"**/api/next/changes/{SLUG}/answers"
# When the checkmark showed and when the question form left or its button came back, in page time (ms).
WATCH = """() => {
  window.seen = {};
  const at = (k) => { window.seen[k] ??= performance.now(); };
  new MutationObserver(() => {
    const form = [...document.querySelectorAll("section.act")].find((s) => s.textContent.includes("Question q1"));
    if (form?.querySelector(".sent-mark")) at("sent");
    if (window.seen.sent && !form) at("gone");
    if (window.seen.sent && form && !form.querySelector(".sent-mark")) at("back");
  }).observe(document.body, { subtree: true, childList: true, attributes: true });
}"""


@pytest.fixture
def page_url(tmp_path) -> Iterator[tuple[Store, str]]:
    """The Spotter's question q1, and a person check whose form the page shows beside it."""
    store = Store(tmp_path)
    c = stopped()
    c.checks = [m.PersonCheck(id="feel", steps=["Flip five times"], expect="No stutter")]
    store.write(Lock(SLUG), c)
    with served(api.create_app(store, "tok", Host())) as base:
        yield store, base


class Wire:
    """The page's requests to the test host: Answer posts recorded and answered as the test plans; the detail shows
    the check waiting; while *down* is set, every API request fails as that kind of loss does. An Answer planned as a
    loss is where that loss begins."""

    def __init__(self, page: Any) -> None:
        self.posts: list[Any] = []
        self.plan: list[str] = []
        self.held: list[Any] = []
        self.down = ""
        page.route("**/api/next/**", self.lost)
        page.route(f"**/api/next/changes/{SLUG}", self.detail)
        page.route(ANSWERS, self.answer)

    def lost(self, route: Any) -> None:
        if self.down == "abort":
            route.abort()
        elif self.down == "restarted":
            route.fulfill(status=401, json={"detail": "unknown token"})
        else:
            route.fallback()

    def detail(self, route: Any) -> None:
        if self.down:
            return self.lost(route)
        got = route.fetch()
        shown = got.json()
        for c in shown["checks"]:
            c["waiting"] = True
        return route.fulfill(response=got, json=shown)

    def answer(self, route: Any) -> None:
        self.posts.append(route.request.post_data_json)
        step = self.plan.pop(0) if self.plan else ""
        if step in {"abort", "restarted"}:
            self.down = step
        if self.down:
            self.lost(route)
        elif step == "hold":
            self.held.append(route)
        elif step == "taken":  # accepted without being recorded: the question stays open
            route.fulfill(json={"queued": True})
        else:
            route.fallback()


def answer_button(form: Any) -> Any:
    return form.locator("p-button[data-sends=Answer]")


@pytest.mark.browser
def test_check_and_local_branch_confirmations_explain_what_can_be_undone(page_url, pds) -> None:
    store, base = page_url
    c = store.read(SLUG)
    c.step = m.Step(kind=m.StepKind.CHECK, task="feel")
    c.outcome = m.Outcome(exit=m.Exit.PENDING, waiting=m.Waiting.PERSON_CHECK, who="you", at=NOW)
    c.pullback = m.Pullback(state="behind", reason="local branch is behind", at=NOW)
    store.write(Lock(SLUG), c)
    with opened(base, pds) as page:
        check = page.locator("section.act", has_text="Your check feel")
        check.get_by_label("What failed", exact=False).fill("It stutters.")
        for opener, confirm, decline, undo in [
            (
                check.get_by_role("button", name="Failed"),
                "Send to the builder",
                "Keep checking",
                "Delivery can't take back the failed result or the AI credits already used.",
            ),
            (
                page.get_by_role("button", name="Pull", exact=True),
                "Update",
                "Leave it",
                "Delivery can't undo a successful update. To go back, restore the previous local branch tip in Git.",
            ),
        ]:
            opener.click()
            dialog = pds.modal(page)
            expect(dialog.get_by_text(undo, exact=False)).to_be_visible()
            choices = [dialog.get_by_role("button", name=name, exact=True) for name in (confirm, decline)]
            for choice in choices:
                size = choice.bounding_box()
                assert size
                assert min(size["width"], size["height"]) >= 24
            for _ in range(3):
                page.keyboard.press("Tab")
                assert page.evaluate(pds.INSIDE)
            pds.answer(page, decline)
            expect(opener).to_be_focused()


@pytest.mark.browser
def test_a_refused_lost_or_unanswered_answer_unlocks_its_form_and_says_so(page_url, pds) -> None:
    """AC-1, AC-2, AC-4..AC-7, AC-9: one request per click, only the sent form locks, each outcome on the button."""

    _store, base = page_url
    with opened(base, pds) as page:
        wire = Wire(page)
        form = page.locator("section.act", has_text="Question q1")
        other = page.locator("section.act", has_text="Your check feel")
        button, said = answer_button(form), page.locator(".said-aloud[role=status]")
        words = form.get_by_label("Your answer in words")
        expect(other).to_be_visible()
        words.fill("keep this")

        wire.plan = ["hold"]
        form.get_by_role("button", name="Answer").dblclick()
        expect(button).to_have_js_property("loading", value=True)
        expect(form).to_have_class(re.compile(r"\bsending\b"))
        expect(said).to_have_text("Sending")
        assert form.evaluate("f => f.inert")  # nothing in it takes a click or a key
        expect(form.locator("p-textarea")).to_have_css("opacity", "0.4")
        assert form.evaluate("f => f.querySelectorAll('p-spinner, .overlay, [role=progressbar]').length") == 0
        button.dispatch_event("click")  # a click that reaches it anyway sends nothing more
        other.get_by_label("What failed", exact=False).fill("still usable")  # AC-7: the other form stays open
        assert not other.evaluate("f => f.inert")
        assert len(wire.posts) == 1

        wire.held.pop().fallback()  # the host refuses an answer without an option
        expect(form.get_by_role("button", name="Failed", exact=True)).to_be_visible()
        expect(button).to_have_attribute("icon", "error")
        expect(button).to_have_js_property("loading", value=False)
        expect(form.locator(".refused")).to_contain_text("Not done")
        expect(said).to_have_text("Failed")
        assert not form.evaluate("f => f.inert")
        assert words.input_value() == "keep this"
        words.fill("keep this too")  # editing the form gives the button back
        expect(form.get_by_role("button", name="Answer", exact=True)).to_be_visible()

        wire.plan = ["hold"]  # no answer within the 5 s timeout
        form.get_by_role("button", name="Answer").click()
        expect(form.get_by_role("button", name="Not confirmed", exact=True)).to_be_visible(timeout=10_000)
        expect(button).to_have_attribute("icon", "warning")
        expect(said).to_have_text("Not confirmed")
        expect(form.locator(".refused")).to_contain_text("Not confirmed")
        assert words.input_value() == "keep this too"

        for down, page_wide in [("abort", "Delivery is not running"), ("restarted", "Delivery restarted")]:
            expect(page.locator("#detail")).not_to_have_class("stale")  # shown as last read, it takes no click
            wire.plan = [down]
            button.dispatch_event("click")
            expect(form.get_by_role("button", name="Failed", exact=True)).to_be_visible()
            expect(page.locator("#error")).to_contain_text(page_wide)
            assert not form.evaluate("f => f.inert")
            wire.down = ""
        assert len(wire.posts) == 4


@pytest.mark.browser
def test_an_accepted_answer_shows_its_checkmark_for_a_second_before_the_form_changes(page_url, pds) -> None:
    """AC-1, AC-3, AC-8, AC-9: the checkmark holds the form; one that stays comes back reset, motion reduced or not."""

    store, base = page_url
    with opened(base, pds) as page:
        wire = Wire(page)
        form = page.locator("section.act", has_text="Question q1")
        button, said = answer_button(form), page.locator(".said-aloud[role=status]")
        mark = button.locator(".sent-mark")

        form.get_by_label("Your answer in words").fill("taken")
        form.get_by_label("Allow it", exact=False).check()
        page.evaluate(WATCH)
        wire.plan = ["taken"]
        form.get_by_role("button", name="Answer").click()  # the host takes it at once; the question stays open
        expect(mark).to_be_visible()
        expect(said).to_have_text("Sent")
        assert mark.evaluate("e => getComputedStyle(e).animationName") == "sent-mark"
        assert button.evaluate("e => e.textContent.trim()") == "Sent"  # said aloud only: no visible text
        button.dispatch_event("click")  # the hold sends nothing more
        expect(form).to_have_class(re.compile(r"\bsending\b"))
        expect(form.get_by_role("button", name="Answer", exact=True)).to_be_visible(timeout=5_000)
        expect(form.get_by_label("Your answer in words")).to_have_value("")  # the sent answer's draft is gone
        seen = page.evaluate("window.seen")
        assert 1_800 <= seen["back"] - seen["sent"] <= 3_000, seen
        assert len(wire.posts) == 1

        page.emulate_media(reduced_motion="reduce")
        form.get_by_label("Allow it", exact=False).check()
        page.evaluate(WATCH)
        wire.plan = ["hold"]
        form.get_by_role("button", name="Answer").click()
        wire.held.pop().fallback()
        expect(mark).to_be_visible()
        store.fold(Lock(SLUG), SLUG, NOW)  # Delivery settled it at once: the next read lacks the question
        assert mark.evaluate("e => getComputedStyle(e).animationName") == "none"
        expect(form).to_have_count(0, timeout=10_000)
        seen = page.evaluate("window.seen")
        assert seen["gone"] - seen["sent"] >= 1_000, seen
        assert len(wire.posts) == 2


@pytest.mark.browser
def test_new_change_through_the_chooser_loads_until_the_chat_opens_then_shows_its_checkmark(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """AC-10: the chooser's Continue goes at once; New Change shows the launch, which a chat that opened ends sent."""

    launched = chats(monkeypatch)
    for name in ("alpha", "beta"):
        shaping(Path(registry.register(clone(tmp_path / name, "same")).path), "A brief")
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/#token=t")
        new = page.locator("#header-actions p-button")
        said = page.locator(".said-aloud[role=status]")
        page.get_by_role("button", name="New Change").click()
        page.get_by_role("button", name="Continue").click()
        pds.answer(page, "Open the chat")
        expect(page.locator("#choose")).to_have_count(0)
        expect(new).to_have_js_property("loading", value=True)  # through the launch, not only its request
        expect(said).to_have_text("Sending")
        until(page, lambda: launched.calls)
        expect(new).to_have_js_property("loading", value=True)
        launched.release.set()
        expect(new.locator(".sent-mark")).to_be_visible()
        expect(said).to_have_text("Sent")
        expect(page.locator("#started")).to_have_text("A chat opened in VS Code to shape the new Change.")
        expect(page.get_by_role("button", name="New Change", exact=True)).to_be_visible(timeout=5_000)
        assert len(launched.calls) == 1


@pytest.mark.browser
@pytest.mark.timeout(120)  # the follow-up's own 30 s timeout runs out in a real browser
def test_a_follow_up_with_no_answer_in_30_s_is_not_confirmed_and_locks_its_row_alone(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """AC-5, AC-7, AC-10: a Change's follow-up keeps its 30 s timeout; another follow-up row stays usable."""

    with machine_page(tmp_path, monkeypatch, pds) as w:
        page, held = w.page, []

        def never(route: Any) -> None:  # Playwright cannot take a builtin method as a handler
            held.append(route)

        page.route("**/improvement/followups", never)
        page.goto(f"{w.base}/?project={w.pid}&change={w.pid}%2F{SPOTTED}#token=t")
        page.locator("#details-switch").click()
        detail = page.locator("#improvement-detail")
        row = detail.locator("#finding-f-1 .followup")
        other = detail.locator("#look-r-note .followup")
        row.get_by_role("button", name="Follow up").click()
        pds.answer(page, "Follow up")
        button = row.locator("p-button")
        expect(button).to_have_js_property("loading", value=True)
        expect(row).to_have_class(re.compile(r"\bsending\b"))
        assert not other.evaluate("r => r.inert || r.classList.contains('sending')")
        expect(other.get_by_role("button", name="Follow up")).to_be_enabled()
        page.wait_for_timeout(5_500)  # past the 5 s most actions wait: this one still waits
        expect(button).to_have_js_property("loading", value=True)
        expect(row.get_by_role("button", name="Not confirmed", exact=True)).to_be_visible(timeout=30_000)
        expect(button).to_have_attribute("icon", "warning")
        expect(page.locator(".said-aloud[role=status]")).to_have_text("Not confirmed")
        expect(detail).to_contain_text("That was not done")
        assert not row.evaluate("r => r.inert")
        assert len(held) == 1
