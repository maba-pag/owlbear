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

from owlbear_delivery_next import api
from owlbear_delivery_next import models as m
from owlbear_delivery_next.codebase import CURRENT
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.round_records import RoundLoop, RoundPolicy
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.store import Lock, Store
from owlbear_delivery_next.visual_records import OwnerCriterion

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
    ]
    brief = m.Brief(
        version=2, challenged=2, title="Flip the hero", outcome="Visitors flip the hero image with one button.",
        criteria=[m.Criterion(id="AC-1", text=MINE), m.Criterion(id="AC-2", text=LEFT_TO_SHAPER)],
        visual=[m.VisualState(name="flipped", path="/", expect="The hero faces left")], ui=True,
        decisions=decisions, non_goals=["Saving the direction"], specified=["AC-1"],
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
def opened(base: str, slug: str) -> Iterator[Any]:
    """The Changes page on *slug* in a real browser, offline: only the test host answers."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/?change={slug}")
        yield page
        browser.close()


@pytest.mark.browser
def test_the_owner_approves_his_agreement_and_the_technical_details_stay_collapsed(page_url) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    with opened(base, "flip") as page:
        brief = page.locator(".brief").first
        yours = brief.locator("section", has_text="Your decisions")
        expect(yours).to_contain_text("Top right of the hero")
        expect(yours).to_contain_text(MINE)  # an owner-stated criterion is part of his agreement
        expect(brief.locator("section", has_text="Choices proposed by the shaper")).to_contain_text("250 ms")
        expect(brief.locator("section", has_text="Not in this Change")).to_contain_text("Saving the direction")
        expect(brief.locator("summary")).to_contain_text("2 criteria \u00b7 1 screen \u00b7 1 check for you")
        expect(page.get_by_text(LEFT_TO_SHAPER, exact=False)).to_be_hidden()  # collapsed until opened
        page.get_by_role("button", name="Approve brief v2").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_contain_text("including its technical details (2 criteria \u00b7 1 screen \u00b7 1 check")
        expect(dialog).to_contain_text("Do your check once the pull request's checks pass")
        page.get_by_role("button", name="Keep it waiting").click()
        expect(dialog).to_be_hidden()
    assert store.read("flip").brief.approved_version is None  # declining approves nothing


@pytest.mark.browser
def test_an_unreviewed_last_revision_is_approved_only_once_the_owner_ticks_that_he_accepts_it(page_url) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    tail = change().model_copy(update={"slug": "tail"})
    tail.loops["brief"] = RoundLoop(subject="brief", policy=RoundPolicy(), round=3, ended="max", unreviewed=["v2"])
    store.write(Lock("tail"), tail)
    with opened(base, "tail") as page:
        page.get_by_role("button", name="Approve brief v2").click()
        dialog = page.get_by_role("dialog")
        confirm = dialog.get_by_role("button", name="Approve and start")
        expect(confirm).to_be_disabled()  # TD-255
        dialog.get_by_label("no challenger reviewed that revision", exact=False).check()
        expect(confirm).to_be_enabled()
        confirm.click()
        expect(dialog).to_be_hidden()
        page.wait_for_timeout(500)
    assert store.fold(Lock("tail"), "tail", NOW)[0].brief.approved_version == 2


@pytest.mark.browser
def test_the_approved_brief_lists_what_the_owner_added_since(page_url) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    built = change().model_copy(update={"slug": "built", "step": m.Step(kind=m.StepKind.BUILD)})
    built.brief = built.brief.model_copy(update={"approved_version": 2, "approved_at": NOW})
    added = OwnerCriterion(id="O-1", text="The caption stays readable", round=1, brief_version=2, at=NOW)
    built.owner_criteria = [added]
    store.write(Lock("built"), built)
    with opened(base, "built") as page:
        since = page.locator(".brief section", has_text="Changes since you approved")
        expect(since).to_contain_text("You added in visual round 1")
        expect(since).to_contain_text("The caption stays readable")
        expect(page.locator(".brief").first).to_contain_text("Your approval accepted these choices.")
