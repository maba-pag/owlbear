"""The Change page's default view in a real browser, on c1's history: what always shows, and what the details add."""

from __future__ import annotations

import contextlib
import re
import socket
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.change_contracts.round_records import BRIEF
from owlbear_delivery_next.project_host import brief_timer
from owlbear_delivery_next.state_store.store import Lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store

SLUG = "c1-fixture"
UNREVIEWED = "v4 changed after its last challenge and no challenger read it: approve it as it is, or challenge it"


@contextlib.contextmanager
def opened(c1: tuple[Store, Any], pds: Any, edit: Callable[[Change], None] | None = None) -> Iterator[Any]:
    """The Changes page on c1, changed by *edit* first, in a real browser: only the test host and the PDS CDN answer."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    store, app = c1
    if edit:
        c = store.read(SLUG)
        edit(c)
        store.write(Lock(SLUG), c)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", timeout_keep_alive=60))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            pds.only(page, base)
            page.add_init_script("sessionStorage.setItem('token', 'tok');")
            page.goto(f"{base}/?change={SLUG}")
            yield page
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True


def big(control: Any) -> None:
    """WCAG 2.5.8: *control*, laid out, takes at least 24 by 24 CSS pixels."""
    box = control.bounding_box()
    assert box is not None
    assert (box["width"] >= 24, box["height"] >= 24) == (True, True), box


def revising(c: Change) -> None:
    """c1 back at brief v3, which the shaper revises for F5, which the owner kept, and F6, round 2's new finding."""
    lp = c.loops[BRIEF]
    c.brief.version, c.brief.challenged, c.brief.requested = 3, None, 3
    lp.ended, lp.head, lp.unreviewed = "", "3", []
    for f in lp.findings:
        f.state = {"F5": "owner-fix", "F6": "open"}.get(f.id, f.state)


@pytest.mark.browser
def test_details_off_then_on(c1, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with opened(c1, pds) as page:
        detail = page.locator("#detail")
        expect(detail.locator(".status")).to_contain_text("approve brief v4")
        expect(detail.locator(".actions")).to_contain_text(UNREVIEWED)
        expect(detail.locator(".brief").first).to_contain_text("The owner rarely opens Metrics")
        versions = detail.locator(".version-list > li")
        expect(versions).to_have_count(4)
        expect(versions.nth(0)).to_contain_text("v1 not challenged")
        for n, challenge in ((1, "Challenge 1"), (2, "Challenge 2")):
            expect(versions.nth(n)).to_contain_text(f"v{n + 1} findings")
            expect(versions.nth(n).locator(".dot.findings")).to_have_count(1)
            expect(versions.nth(n).locator("ul")).to_have_text(challenge)
        expect(versions.nth(3)).to_contain_text("v4 not challenged, current")
        expect(versions.nth(3).locator(".dot.unreviewed")).to_have_count(1)
        expect(detail.locator(".legend li")).to_have_text(
            ["challenge running", "waits for you", "findings", "clean", "not challenged"]
        )
        approve = versions.nth(3).get_by_role("button", name="Approve v4")
        expect(approve).to_be_enabled()
        expect(detail.get_by_role("button", name=re.compile(r"^Approve v[1-3]$"))).to_have_count(0)  # past versions
        for hidden in ("Review rounds", "Decisions this work follows", "Recent activity"):
            expect(detail.get_by_role("heading", name=hidden)).to_have_count(0)
        expect(detail.locator(".actions")).not_to_contain_text("No review yet")  # v4 is named once, above
        expect(detail.get_by_text("This version follows 96 decisions.")).to_be_visible()

        pds.settled(page)
        switch = detail.locator("#details-switch")
        big(switch)
        big(approve)
        switch.click()
        expect(detail.get_by_role("heading", name="Review rounds")).to_be_visible()
        follows = detail.locator("summary", has_text="Decisions this work follows (96)")
        big(follows)
        follows.click()
        unread = "They can't be grouped or linked: there is no shared data repository"
        expect(detail.get_by_text(unread)).to_be_visible()
        expect(detail.get_by_text("This version follows 96 decisions.")).to_have_count(0)
        expect(detail.get_by_role("heading", name="Recent activity")).to_be_visible()
        detail.get_by_text("Finding details of the brief challenge").click()  # its findings before approval too
        rounds = detail.locator(".rounds")
        expect(rounds).to_contain_text("F6 (fix reported, not re-reviewed)")
        expect(rounds).to_contain_text("Shaper: Both decisions govern how a brief is shaped")
        expect(versions).to_have_count(4)  # what shows without the details stays

        switch.focus()
        page.keyboard.press("Space")  # the switch works from the keyboard
        expect(detail.get_by_role("heading", name="Review rounds")).to_have_count(0)


@pytest.mark.browser
def test_the_shaper_revises_line_names_the_findings(c1, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with opened(c1, pds, revising) as page:
        items = page.locator("#detail .actions")
        expect(items).to_contain_text(
            "The shaper revises brief v3 for F5, F6: continue in the shaping chat, or open a new one"
        )
        revise = page.get_by_role("button", name="Revise the brief in a new chat")
        expect(revise).to_have_count(1)  # offered once, on its line
        expect(items.get_by_role("button", name="Revise the brief in a new chat")).to_be_visible()
        expect(page.get_by_text("Not yet: the shaper revises brief v3 for F5, F6.")).to_be_visible()
        expect(page.get_by_role("button", name="Approve v3")).to_be_disabled()
        pds.settled(page)
        big(revise)


@pytest.mark.browser
def test_a_version_that_waits_for_you_is_red_and_approve_is_off(c1, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    def disputed(c: Change) -> None:
        revising(c)
        for f in c.loops[BRIEF].findings:
            f.state = {"F5": "fixed", "F6": "escalated"}.get(f.id, f.state)

    with opened(c1, pds, disputed) as page:
        current = page.locator("#detail .version-list > li").nth(2)
        expect(current).to_contain_text("v3 waits for you, current")
        expect(current.locator(".dot.waits")).to_have_count(1)
        expect(current.get_by_role("button", name="Approve v3")).to_be_disabled()
        expect(page.get_by_text("Not yet: a finding of its challenge waits for your decision.")).to_be_visible()


@pytest.mark.browser
def test_partial_state_is_said(c1, pds) -> None:
    """Rounds counted before versions were recorded say so, and the pick still owed says Delivery picks."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    def legacy_and_owed(c: Change) -> None:
        c.loops[BRIEF].verdicts = []
        c.brief.picked = Pick(version=4)

    with opened(c1, pds, legacy_and_owed) as page:
        detail = page.locator("#detail")
        versions = detail.locator(".version-list > li")
        expect(versions).to_have_count(4)
        for n in range(3):
            expect(versions.nth(n)).to_contain_text(f"v{n + 1} not recorded")
            expect(versions.nth(n).locator(".dot.unknown")).to_have_count(1)
        expect(versions.nth(3)).to_contain_text("v4 not challenged, current")
        expect(detail).to_contain_text("Challenges 1 to 2 ran before versions were recorded per challenge.")
        expect(detail.locator(".actions")).to_contain_text("Delivery is picking the decisions this version follows")
        expect(detail.get_by_role("button", name="Approve v4")).to_be_disabled()


@pytest.mark.browser
def test_one_more_challenge_confirms_keeps_focus_and_runs(c1, pds) -> None:
    """#966: v4's revision no challenger read gets one more challenge from its line; approval waits for its verdict."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store = c1[0]
    with opened(c1, pds) as page:
        current = page.locator("#detail .version-list > li").nth(3)
        challenge = current.get_by_role("button", name="Challenge v4")
        pds.settled(page)
        big(challenge)
        challenge.click()
        expect(pds.modal(page)).to_contain_text("Challenge brief v4 once more?")
        expect(pds.modal(page)).to_contain_text("Once it runs, a pause doesn't stop it")
        pds.settled(page)
        for key in ["Shift+Tab"] * 3 + ["Tab"] * 3:  # the dialog keeps focus at both ends
            page.keyboard.press(key)
            assert page.evaluate(pds.INSIDE), key
        page.keyboard.press("Escape")
        page.wait_for_function("() => document.activeElement?.textContent?.trim() === 'Challenge v4'")
        assert store.read(SLUG).step.mode is None  # declined: nothing asked
        challenge.click()
        pds.answer(page, "Challenge it")
        expect(current).to_contain_text("v4 challenge running, current")
        expect(current.locator(".dot.running")).to_have_count(1)
        expect(current.get_by_role("button", name="Approve v4")).to_be_disabled()
        expect(current.get_by_role("button", name="Challenge v4")).to_have_count(0)
        expect(page.get_by_text("Not yet: the challenge of brief v4 is running.")).to_be_visible()
        expect(page.locator("#detail .actions")).not_to_contain_text(UNREVIEWED)
    c = store.read(SLUG)
    assert (c.step.mode, c.brief.requested, c.brief.challenged, c.loops[BRIEF].reentry) == ("challenge", 4, None, True)


@pytest.mark.browser
def test_a_version_saved_after_its_loop_ended_says_when_its_challenge_starts_and_approve_starts_it(c1, pds) -> None:
    """#986: c1's loop ended on v4; the shaper saves v5 as a chat does, sending back what it read. The page says when
    Delivery starts v5's challenge, and Approve starts it now, approving v5 once the round raises nothing."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, app = c1
    http = TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer tok"})
    said = http.get(f"/api/next/chat/brief/{SLUG}").json()
    fields = ("title", "outcome", "scope", "non_goals", "decisions", "criteria", "specified")
    held = {p.id: p for p in store.read(SLUG).checks}  # what the chat keeps of its checks beyond the read-back
    checks = [k | {"steps": held[k["name"]].steps, "expect": held[k["name"]].expect, "visual": held[k["name"]].visual}
              for k in said["person_checks"]]  # fmt: skip
    body = {k: said[k] for k in fields} | {"change": "c1", "person_checks": checks}
    assert http.post("/api/next/briefs", json=body).json()["version"] == 5
    with store.lock(SLUG) as lock:  # the host's next pass, which the save woke
        store.write(lock, brief_timer.passed(store, lock, store.read(SLUG), datetime.now(UTC), paused=False))
    at = f"{store.read(SLUG).outcome.wake_at.astimezone():%H:%M}"
    with opened(c1, pds) as page:
        row = page.locator(f"#changes .card:has(a[data-key='{SLUG}'])")
        expect(row).to_contain_text(f"brief v5's challenge starts by itself at {at}")
        expect(row.locator("p.next")).to_have_count(0)  # not "Continue in the shaping chat": Delivery acts next
        detail = page.locator("#detail")
        expect(detail).to_contain_text(
            f"Brief v5's challenge starts by itself at {at}; Approve starts it now and approves it if it is clean"
        )
        approve = detail.get_by_role("button", name="Approve v5")
        expect(approve).to_be_enabled()
        pds.settled(page)
        big(approve)
        approve.click()
        expect(pds.modal(page)).to_contain_text("Approve brief v5 once its challenge is clean?")
        expect(pds.modal(page)).to_contain_text("Nothing is approved yet")
        pds.settled(page)
        for key in ["Shift+Tab"] * 3 + ["Tab"] * 3:  # the dialog keeps focus at both ends
            page.keyboard.press(key)
            assert page.evaluate(pds.INSIDE), key
        page.keyboard.press("Escape")
        page.wait_for_function("() => document.activeElement?.textContent?.trim() === 'Approve v5'")
        assert store.read(SLUG).brief.approve_if_clean is None  # declined: nothing asked
        approve.click()
        pds.answer(page, "Challenge and approve")
        current = detail.locator(".version-list > li").nth(4)
        expect(current).to_contain_text("v5 challenge running, current")
        expect(current.locator(".dot.running")).to_have_count(1)
        expect(page.get_by_text(
            "Not yet: the challenge of brief v5 is running; your approval takes effect if it is clean."
        )).to_be_visible()  # fmt: skip
    c = store.read(SLUG)
    assert (c.brief.approve_if_clean, c.step.mode, c.brief.requested) == (5, "challenge", 5)


def failed(c: Change) -> None:
    """c1's pick of v4's decisions failed."""
    c.brief.picked = Pick(version=4, status="failed", reason="the runtime did not start")


@pytest.mark.browser
def test_pick_the_decisions_again_retries_without_a_round(c1_shared, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store = c1_shared[0]
    with opened(c1_shared, pds, failed) as page:
        items = page.locator("#detail .actions")
        expect(items).to_contain_text("Picking the decisions failed: the runtime did not start")
        expect(page.get_by_text("Not yet: the picker failed: the runtime did not start; use Pick the decisions "
                                "again under Open items.")).to_be_visible()  # fmt: skip
        expect(page.get_by_role("button", name="Approve v4")).to_be_disabled()
        expect(page.get_by_role("button", name="Challenge v4")).to_have_count(0)  # the pick goes first
        again = items.get_by_role("button", name="Pick the decisions again")
        pds.settled(page)
        big(again)
        assert again.get_attribute("variant") is None  # the panel's one primary action
        before = store.read(SLUG).loops[BRIEF].model_dump(include={"round", "extra", "verdicts"})
        again.click()
        expect(items).to_contain_text("Delivery is picking the decisions this version follows")
        expect(items.get_by_role("button", name="Pick the decisions again")).to_have_count(0)
        expect(page.get_by_role("button", name="Approve v4")).to_be_disabled()
    c = store.read(SLUG)
    assert c.brief.picked.status == "owed"
    assert c.loops[BRIEF].model_dump(include={"round", "extra", "verdicts"}) == before  # no round spent


@pytest.mark.browser
def test_a_refused_pick_again_says_why(c1_shared, pds) -> None:
    """Delivery started picking between the page's render and the click: the host refuses and the page says why."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store = c1_shared[0]

    def picking_meanwhile(route: Any) -> None:
        c = store.read(SLUG)
        c.brief.picked = Pick(version=4)
        store.write(Lock(SLUG), c)
        route.continue_()

    with opened(c1_shared, pds, failed) as page:
        page.route("**/briefs/challenge", picking_meanwhile)
        again = page.locator("#detail .actions").get_by_role("button", name="Pick the decisions again")
        pds.settled(page)
        again.click()
        expect(page.locator("#detail .refused")).to_contain_text(
            "the decisions of brief v4 are being picked; ask again after it"
        )
