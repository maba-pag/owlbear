"""The brief approval view in a real browser (TD-122, TD-179): the agreement open, technical details collapsed."""

from __future__ import annotations

import contextlib
import re
import socket
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_contracts.decision_records import Pick, PickedDecision
from owlbear_delivery_next.change_contracts.round_records import RoundLoop, RoundPolicy
from owlbear_delivery_next.change_contracts.tool_use import ToolUse
from owlbear_delivery_next.change_contracts.visual_records import OwnerCriterion
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import spend_ledger
from owlbear_delivery_next.state_store.store import Lock, Store

if TYPE_CHECKING:
    from collections.abc import Iterator

NOW = datetime(2026, 10, 16, 2, tzinfo=UTC)
MINE, LEFT_TO_SHAPER = "Turns the hero 180 degrees in under 300 ms", "A second press returns the hero"


class Host:
    maintenance = None
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


@pytest.mark.browser
def test_the_changes_tool_calls_show_under_its_spend_most_called_first(page_url, pds) -> None:  # C-28 T8
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    stored = ToolUse().plus({"ask_question": {"calls": 99}})  # the page reads the ledger, never the stored tally
    store.write(Lock("used"), change().model_copy(update={"slug": "used", "tool_use": stored}))
    store.write(Lock("idle"), change().model_copy(update={"slug": "idle"}))
    ran(store, "used", {"ask_question": {"calls": 1}, "submit_result": {"calls": 3, "rejected": 1, "retries": 1}})
    ran(  # stopped: its run never reached the Change's own accounting, only the ledger
        store, "used", {"report_wrong_premise": {"calls": 4, "rejected": 1, "invalid": 1, "lint": 1, "late": 1}},
        {"denied": 2}, ending="interrupted",
    )  # fmt: skip
    ran(store, "idle", {}, {"no_result": 2})
    assert spend_ledger.WRITER.settled(10)
    with opened(base, "used", pds) as page:
        expect(page.get_by_text("Tool calls (8)")).to_be_visible()
        page.get_by_text("Tool calls (8)").click()
        expect(page.get_by_text("report_wrong_premise: 4 calls, 25% succeeded, 25% refused (1 invalid arguments), "
                                "1 lint, 1 late, 0 retries")).to_be_visible()  # fmt: skip
        expect(
            page.get_by_text("submit_result: 3 calls, 67% succeeded, 33% refused (1 not split), 1 retry")
        ).to_be_visible()
        expect(page.get_by_text("ask_question: 1 call, 100% succeeded, 0% refused, 0 retries")).to_be_visible()
        expect(page.get_by_text("Wrong tool choices: 2 denials by the guard")).to_be_visible()
    with opened(base, "idle", pds) as page:  # no call counted, yet its wrong choices show
        page.get_by_text("Tool calls (0)").click()
        expect(page.get_by_text("Wrong tool choices: 2 turns without a result")).to_be_visible()


def ran(store: Store, slug: str, tools: dict, wrong: dict | None = None, ending: str = "result") -> None:
    """One measured run of *slug* in the test home's spend ledger, as an SDK run's ``metered`` writes it."""
    run = uuid.uuid4().hex
    place = spend_ledger.Where.of(store, change=slug, step="build")  # the place the runner enters
    spend_ledger.started(run, f"s-{run}", agent="builder", job="", model="m1", before={}, place=place)
    spend_ledger.ended(run, f"s-{run}", usage={"credits": 0.1}, ending=ending, place=place, tools=tools,
                       wrong=wrong or {})  # fmt: skip


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
        form.get_by_label("It only settles how the work goes on").check()
        form.get_by_role("button", name="Answer").click()
        expect(page.locator("#detail")).not_to_contain_text("Not done")
    item = sent(store, "greet")
    assert '"option":"en"' in item.replace(" ", "")
    assert '"classed":"event"' in item.replace(" ", "")
    assert "the site is read in Canada" in item


@pytest.mark.browser
def test_a_clarification_is_sent_only_with_the_owners_confirmed_statement(page_url, pds) -> None:
    """TD-461: the owner classes his answer; a clarification carries his intent in two lines, which he confirms."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())
    with opened(base, "greet", pds) as page:
        form = page.locator("section.act", has_text="Question q1")
        form.get_by_label("English").check()
        form.get_by_label("Your answer in words").fill("english, the readers are in Canada mostly")
        expect(form.get_by_label("This statement is my intent")).to_have_count(0)
        form.get_by_label("It clarifies what the brief means", exact=False).check()
        form.get_by_label("Your intent, as this Change's decision records it", exact=False).fill(
            "The greeting is in English."
        )
        form.get_by_role("button", name="Answer").click()
        expect(page.locator("#error")).to_contain_text("Write your intent in at most two lines and confirm it.")
        with store.db.read() as db:
            assert db.execute("SELECT count(*) FROM inbox").fetchone() == (0,)  # nothing unconfirmed is sent
        form.get_by_label("This statement is my intent").check()
        form.get_by_role("button", name="Answer").click()
        expect(page.locator("#detail")).not_to_contain_text("Not done")
    item = sent(store, "greet").replace(" ", "")
    assert '"classed":"clarification"' in item
    assert '"statement":"ThegreetingisinEnglish."' in item


@pytest.mark.browser
def test_choosing_another_change_and_going_back_keeps_the_address_and_the_list(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())
    with opened(base, "flip", pds) as page:
        expect(page.locator("#detail h2")).to_have_text("Flip the hero")
        expect(page.locator("#changes")).to_contain_text("Needs you (")
        page.locator("#changes a[data-key='greet']").click()
        expect(page.locator("#detail h2")).to_have_text("greet")
        assert page.evaluate("location.search") == "?change=greet"
        page.go_back()
        expect(page.locator("#detail h2")).to_have_text("Flip the hero")
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
        offered = form.locator('p-radio-group[label="Choose an option"]').get_by_role("radio")
        expect(offered).to_have_count(len(left), timeout=10_000)
        expect(offered.and_(form.get_by_role("radio", checked=True))).to_have_count(0)
        form.get_by_label("It only settles how the work goes on").check()
        form.get_by_role("button", name="Answer").click()
        expect(page.locator("#detail")).not_to_contain_text("Not done")
    assert '"option":null' in sent(store, "greet").replace(" ", "")


@pytest.mark.browser
def test_a_card_names_the_files_its_activity_touches_without_their_paths(page_url, pds) -> None:
    """The card is a summary: a tool's path shows as its file's name; the detail keeps the whole path."""
    import json  # noqa: PLC0415
    import re  # noqa: PLC0415

    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _, base = page_url

    now = {"now": "", "progress": None, "outcome": None}

    def doing(route) -> None:
        rows = route.fetch().json()
        for row in rows if isinstance(rows, list) else [rows]:
            row.update(now)
        route.fulfill(content_type="application/json", body=json.dumps(rows))

    with opened(base, "flip", pds) as page:
        page.route(re.compile(r".*/changes(/flip)?(\?.*)?$"), doing)
        card = page.locator("#changes .card", has_text="flip")
        for said, shown in (
            ("Build 1/2 · view /Users/me/project/README.md", "view README.md"),
            ("Build · view /Users/Jane Doe/project/README.md 3m ago", "view README.md 3m ago"),
            ("Build · ran pytest src/x/test_y.py 1m ago", "ran pytest test_y.py 1m ago"),
            ("Build · stopped: CI/CD failed · 3/4 left", "CI/CD failed"),
        ):
            now["now"] = said
            page.reload()
            expect(card).to_contain_text(shown)
            expect(card).not_to_contain_text("/Users/")
            expect(card).not_to_contain_text("src/")
        expect(page.locator("#detail")).to_contain_text("CI/CD failed · 3/4 left")
        now["now"] = said = "Build · view /Users/Jane Doe/project/README.md 3m ago"
        page.reload()
        expect(page.locator("#detail")).to_contain_text(said)  # the detail keeps the whole path
        now |= {"now": "Build · submitted its result 1 min ago", "actor": "you"}
        page.reload()
        expect(card.locator("p-tag")).to_have_text("Your turn")
        expect(card).not_to_contain_text("submitted its result")  # its status and next action say it all
        expect(page.locator("#detail")).to_contain_text("submitted its result 1 min ago")


@pytest.mark.browser
def test_a_change_reads_by_its_title_and_its_slug_stands_in_while_it_has_none(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())  # no title yet
    with opened(base, "flip", pds) as page:
        flip, greet = (page.locator(f"#changes .card:has(a[data-key='{k}'])") for k in ("flip", "greet"))
        expect(flip.locator("a.open")).to_have_text("Flip the hero")
        expect(flip.locator(".meta").first).to_have_text("flip")  # the slug below it
        expect(greet.locator("a.open")).to_have_text("greet")
        expect(greet.locator(".meta", has_text="greet")).to_have_count(0)  # said once
        head = page.locator("#detail .detail-head")
        expect(head.locator("h2")).to_have_text("Flip the hero")
        expect(head).to_contain_text("flip")
        greet.locator("a.open").click()
        expect(head.locator("h2")).to_have_text("greet")
        expect(head.locator("p-text")).to_have_count(0)


@pytest.mark.browser
def test_recent_activity_reads_in_words_with_one_line_per_merge_and_repeats_counted(page_url, pds) -> None:
    """C4: the display only; the activity file keeps every event as recorded."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    events = [
        {"event": "step", "kind": "cleanup", "exit": "done", "at": "2026-10-16T00:59:00+00:00",
         "reason": "workspace kept: large ignored files (/Users/Jane Doe/.owlbear/wt/flip)"},
        {"event": "tool", "tool": "submit_result", "accepted": True, "at": "2026-10-16T01:00:00+00:00"},
        {"event": "tool", "tool": "submit_result", "accepted": True, "at": "2026-10-16T01:01:00+00:00"},
        {"event": "tool", "tool": "submit_result", "accepted": True, "at": "2026-10-16T01:02:00+00:00"},
        {"event": "prepared-end", "check": "feel", "cleanup": "ok", "at": "2026-10-16T01:03:00+00:00"},
        {"event": "merge-request", "pr": 20, "head": "abc", "status": "merged",
         "message": "Pull Request successfully merged", "at": "2026-10-16T01:04:00+00:00"},
        {"event": "merged", "pr": 20, "head": "abc", "sha": "77541c4e9", "method": "squash",
         "at": "2026-10-16T01:04:01+00:00"},
        {"event": "step", "kind": "merge", "exit": "done", "reason": "merged PR #20 as 77541c4 (squash)",
         "at": "2026-10-16T01:04:02+00:00"},
        {"event": "workspace-kept", "path": "/Users/me/.owlbear/wt/flip", "reason": "large ignored files",
         "at": "2026-10-16T01:05:00+00:00"},
        {"event": "lint", "ran": [], "skipped": ["ruff: no configuration for new.py"], "passed": True,
         "at": "2026-10-16T01:05:10+00:00"},
        {"event": "undo", "task": "t1", "attempt": 2, "error": "conflict in '/Users/me/repo/hero.css'",
         "at": "2026-10-16T01:05:20+00:00"},
        {"event": "undo", "task": "t1", "attempt": 2, "at": "2026-10-16T01:05:30+00:00"},
        {"event": "step", "kind": "cleanup", "exit": "pending", "reason": "waiting for checks",
         "at": "2026-10-16T01:06:00+00:00"},
        {"event": "lint", "ran": [{"tool": "ruff", "files": ["a.py"], "state": "passed"},
                                  {"tool": "mypy", "files": ["a.py"], "state": "broken"}],
         "skipped": [], "passed": True, "at": "2026-10-16T01:06:10+00:00"},  # a repeat break no longer blocks
        {"event": "force-stop", "reason": "stop timed out", "runtime_pid": 41, "at": "2026-10-16T01:06:20+00:00"},
    ]  # fmt: skip
    for e in events:
        store.log(Lock("flip"), "flip", e)
    with opened(base, "flip", pds) as page:
        lines = page.locator("#detail .log li")
        expect(lines).to_have_count(11)
        expect(lines.nth(0)).to_contain_text("Tried to force the session to stop: stop timed out")
        expect(lines.nth(1)).to_contain_text("Lint incomplete (ruff, mypy could not run)")
        expect(lines.nth(2)).to_contain_text("Clean-up waiting: waiting for checks")
        expect(lines.nth(3)).to_have_text(re.compile(r"Undid task t1, attempt 2$"))  # not counted with the failure
        expect(lines.nth(4)).to_contain_text("Could not undo task t1, attempt 2: conflict in 'hero.css'")
        expect(lines.nth(5)).to_contain_text("Lint not run: ruff: no configuration for new.py")
        expect(lines.nth(6)).to_contain_text("Workspace flip kept: large ignored files")
        expect(lines.nth(7)).to_contain_text("Merged PR #20 as 77541c4 (squash)")
        expect(lines.nth(8)).to_have_text(re.compile(r"Check feel ended; its cleanup ran$"))
        expect(lines.nth(9)).to_have_text(re.compile(r"Submitted its result\s*\u00d73, 3 times$"))
        kept = r"Clean-up finished: workspace kept: large ignored files \(flip\)$"  # a spaced path in parentheses
        expect(lines.nth(10)).to_have_text(re.compile(kept))
        expect(page.locator("#detail .log")).not_to_contain_text("/Users/")
        exact = page.evaluate(
            "(at) => at.map((iso) => new Date(iso).toLocaleString())", [events[1]["at"], events[3]["at"]]
        )
        expect(lines.nth(9).locator("time")).to_have_attribute("title", " to ".join(exact))  # the exact times on hover
    assert [e["event"] for e in store.events("flip")][-len(events) :] == [e["event"] for e in events]
