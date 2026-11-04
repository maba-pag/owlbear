"""The brief approval view in a real browser (TD-122, TD-179): the agreement open, technical details collapsed."""

from __future__ import annotations

import contextlib
import re
import socket
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_contracts.decision_records import Pick, PickedDecision
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.round_records import RoundFinding, RoundLoop, RoundPolicy, Verdict
from owlbear_delivery_next.change_contracts.tool_use import ToolUse
from owlbear_delivery_next.change_contracts.visual_records import OwnerCriterion
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api, brief_view
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store import decision_store, machine_settings, spend_ledger, work_block
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import decision_publication

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

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
        m.BriefDecision(question="Button label", answer="Flip", origin="approved"),
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


@contextlib.contextmanager
def served(store: Store) -> Iterator[str]:
    """The project app over *store* on a free local port, with token ``tok``."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    # longer than the pages' polls: route.fetch() reuses a pooled socket, which uvicorn's 5 s default closes
    server = uvicorn.Server(
        uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning", timeout_keep_alive=60)
    )
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{sock.getsockname()[1]}"
    server.should_exit = True


@pytest.fixture
def page_url(tmp_path) -> Iterator[tuple[Store, str]]:
    store = Store(tmp_path)
    store.write(Lock("flip"), change())
    with served(store) as base:
        yield store, base


@contextlib.contextmanager
def opened(base: str, slug: str, pds: Any, *, details: bool = False) -> Iterator[Any]:
    """The Changes page on *slug* in a real browser, its details shown or not: only the test host and the PDS CDN
    answer."""
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
        page.goto(f"{base}/?change={slug}")
        yield page
        browser.close()


def big(control: Any) -> None:
    """WCAG 2.5.8: *control*, laid out, takes at least 24 by 24 CSS pixels."""
    box = control.bounding_box()
    assert box is not None
    assert (box["width"] >= 24, box["height"] >= 24) == (True, True), box


STAGES = ["Shape", "Plan", "Build", "Final review", "Publish", "Visual check", "Your checks", "Merge"]


def agreed(brief: Any) -> None:
    """The outcome comes first; the owner's decisions, the shaper's choices and what is out fold under their counts."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    expect(brief.locator(":scope > *").first).to_have_text("Visitors flip the hero image with one button.")
    folds = brief.locator(":scope > section > details > summary")
    expect(folds).to_have_text(  # the decisions picked fold too, shown with the details
        ["Your decisions (4)", "Shaper's choices (1)", "Out of scope (1)", "Decisions this work follows (1)"]
    )
    expect(brief.get_by_text("Top right of the hero")).to_be_hidden()  # folded until opened
    for fold in folds.all():
        big(fold)
        fold.click()
    yours = brief.locator("section", has_text="Your decisions")
    expect(yours.locator(".said").first.locator("li")).to_have_text([
        "Where does the button sit? Top right of the hero (you decided)",
        "Hero motion Never autoplay (you decided; lasting: applies to later Changes too)",  # C-14
        "Button label Flip (you took the shaper's recommendation)",
    ])  # fmt: skip
    expect(yours.locator("p-heading", has_text="You specified").locator("+ ul.said")).to_contain_text(MINE)
    shaper = brief.locator("section", has_text="Shaper's choices")
    expect(shaper).to_contain_text("Approving accepts these choices.Animation length")
    expect(shaper).not_to_contain_text("Flip")  # the recommendation he took is his
    expect(brief.locator("section", has_text="Out of scope")).to_contain_text("Saving the direction")
    expect(brief.locator("section", has_text="Decisions this work follows")).to_contain_text("Motion stays subtle")


@pytest.mark.browser
def test_the_agreement_keeps_details_collapsed_and_the_approved_brief_lists_the_owners_additions(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    with opened(base, "flip", pds, details=True) as page:  # the decisions picked show with the details
        expect(page.locator("ol.stepper > li > span > span:first-child")).to_have_text(STAGES)
        current = page.locator("ol.stepper > li[aria-current]")
        expect(current).to_have_count(1)
        expect(current).to_have_attribute("aria-current", "step")
        expect(current).to_contain_text("Shape")
        expect(page.locator("ol.stepper .loops")).to_have_count(0)  # no stage looped yet
        brief = page.locator(".brief").first
        agreed(brief)
        technical = brief.locator("summary", has_text="Technical details")
        expect(technical).to_contain_text("2 criteria \u00b7 1 screen \u00b7 1 check for you")
        expect(page.get_by_text(LEFT_TO_SHAPER, exact=False)).to_be_hidden()  # collapsed until opened
        page.get_by_role("button", name="Approve v2").click()
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


PROJECT = "shop-site"


def rule(title: str, scope: Scope, state: State = State.IN_FORCE) -> Decision:
    where = {Scope.GLOBAL: {}, Scope.PROJECT: {"project": PROJECT}}.get(scope, {"project": PROJECT, "change": "flip"})
    return Decision(id=new_id(), title=title, statement=f"{title}.", scope=scope, origin=Origin.DECIDED, actor="owner",
                    state=state, created_at=NOW, **where)  # fmt: skip


@pytest.fixture
def shared_url(tmp_path: Path, shared_repo) -> Iterator[tuple[Store, str, dict[str, Decision]]]:
    """Change ``flip`` picking a Global, two project (one withdrawn since), a Change and an unknown decision."""
    import subprocess  # noqa: PLC0415

    shared = DataRepo(shared_repo[0])
    shared.claim(PROJECT, "github.com/acme/shop-site")
    rules = {
        "global": rule("Pages are plain HTML", Scope.GLOBAL),
        "project": rule("Notes live in SQLite", Scope.PROJECT),
        "withdrawn": rule("Cache every read", Scope.PROJECT, State.WITHDRAWN),
        "change": rule("The flip button stays square", Scope.CHANGE),
    }
    for r in rules.values():
        folder = {Scope.GLOBAL: shared.root, Scope.PROJECT: shared.root / PROJECT}.get(r.scope)
        write(r, folder or shared.root / PROJECT / "changes" / "flip")
    for args in (("add", "-A"), ("commit", "-qm", "seed"), ("push", "-q", "origin", "HEAD")):
        subprocess.run(["git", *args], cwd=shared.root, check=True, capture_output=True)  # noqa: S603, S607
    store = Store(tmp_path / "store", shared, PROJECT)
    c = change()
    said = [PickedDecision(id=r.id, revision=r.revision, title=r.title, statement=r.statement) for r in rules.values()]
    gone = PickedDecision(id=new_id(), revision="r0", title="An old rule since moved away", statement="Gone.")
    c.brief.picked = Pick(version=2, status="ok", decisions=[*said, gone])
    store.write(Lock("flip"), c)
    with served(store) as base:
        yield store, base, rules


@pytest.mark.browser
def test_picked_decisions_group_by_scope_and_link(shared_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _store, base, rules = shared_url
    with opened(base, "flip", pds) as page:
        expect(page.get_by_text("This version follows 5 decisions.")).to_be_visible()  # details off: one line
        page.locator("#details-switch").click()
        follows = page.locator(".brief section", has_text="Decisions this work follows")
        summary = follows.locator("summary")
        expect(summary).to_have_text("Decisions this work follows (5)")
        big(summary)
        summary.click()
        expect(follows.locator("p-heading")).to_have_text(
            ["Global (1)", "This project (2)", "This Change (1)", "Not in the current decisions (1)"]
        )
        expect(follows.locator("li")).to_have_text([
            "Pages are plain HTML", "Notes live in SQLite", "Cache every read (withdrawn)",
            "The flip button stays square", "An old rule since moved away",
        ])  # fmt: skip
        expect(follows.get_by_role("link")).to_have_count(4)  # the one gone from the list has nowhere to go
        withdrawn = rules["withdrawn"]
        follows.get_by_role("link", name="Cache every read").click()
        expect(page).to_have_url(re.compile(rf"/decisions\?decision={withdrawn.id}$"))
        card = page.locator(f'.entry[data-id="{withdrawn.id}"]')
        expect(card).to_have_count(1)
        expect(card.locator(".heading")).to_have_text("Cache every read.")  # its statement, which the title cuts
        expect(card.locator("#detail")).to_be_visible()
        expect(card).to_be_in_viewport()
        expect(card.locator(".heading")).to_be_focused()
        pds.pick(page, "State", "all")  # now listed, it shows once, still open
        expect(page.locator(f'.entry[data-id="{withdrawn.id}"]')).to_have_count(1)
        expect(page.locator("#linked")).to_have_count(0)
        expect(page.locator(f'.entry[data-id="{withdrawn.id}"] #detail')).to_be_visible()


@pytest.mark.parametrize("case", ["no-shared-data", "save-in-progress"])
def test_an_unavailable_decision_list_is_said(c1, request, monkeypatch, case: str) -> None:
    """The picked decisions can't be grouped without the list; the rest of the detail answers all the same."""
    store, app = c1
    reason = "there is no shared data repository, so there are no decisions to work by"
    if case == "save-in-progress":
        reason = "a decision save is in progress; try again in a moment"

        def saving(*_args: object) -> None:
            raise decision_store.DecisionsUnavailable(reason)

        monkeypatch.setattr(brief_view.decision_store, "load", saving)
        moved = Store(store.root, DataRepo(request.getfixturevalue("shared_repo")[0]), PROJECT)
        app = api.create_app(moved, "tok", Host())
    client = TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer tok"})
    detail = client.get("/api/next/changes/c1-fixture")
    assert detail.status_code == 200, detail.text
    brief = detail.json()["brief"]
    assert (brief["picked"]["status"], len(brief["picked"]["decisions"])) == ("ok", 96)
    assert (brief["picked_items"], brief["picked_unavailable"]) == (None, reason)
    assert [v["n"] for v in brief["versions"]["versions"]] == [1, 2, 3, 4]


@pytest.mark.browser
def test_a_planned_change_folds_its_plan_with_the_current_task_outside(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    built = change().model_copy(update={"step": m.Step(kind=m.StepKind.BUILD)})
    built.brief = built.brief.model_copy(update={"approved_version": 2, "approved_at": NOW})
    titles = ["Add the flip button", "Animate the hero", "Keep the caption readable"]
    tasks = [m.Task(id=f"t{n}", title=t, done=n == 1) for n, t in enumerate(titles, 1)]
    part = m.Task(id="t4", title="Label the hero's controls", origin="review", fixes="t2")  # runs before t3
    built.plan = m.Plan(version=2, tasks=[*tasks, part])
    found = RoundFinding(id="F1", text="t2: AC-1: no timing check - fix: measure it", raised=1, state="fixed")
    verdicts = [Verdict(round=1, version=1), Verdict(round=2, version=2)]
    built.loops["plan"] = RoundLoop(subject="plan", policy=RoundPolicy(), round=2, ended="clean", findings=[found],
                                    verdicts=verdicts)  # fmt: skip
    reviewed = RoundFinding(id="F1", text="the button lacks a label - fix: name it", raised=1, state="fixed")
    built.loops["t1"] = RoundLoop(subject="t1", policy=RoundPolicy(), round=1, ended="clean", findings=[reviewed])
    store.write(Lock("flip"), built)
    with opened(base, "flip", pds) as page:
        plan = page.locator("section.info", has=page.get_by_role("heading", name="Plan", exact=True))
        now = plan.locator(":scope > ol.plan > li")
        expect(now).to_have_count(1)  # the task at work, outside the fold
        expect(now).to_contain_text("now")
        expect(now).to_contain_text("Label the hero's controls")  # the repair part the build works on
        fold = plan.locator("details", has_text="Tasks: 1 of 4 done")
        expect(fold.locator("summary")).to_have_text("Tasks: 1 of 4 done")
        expect(page.get_by_text("Keep the caption readable")).to_be_hidden()
        versions = plan.locator(".version-list > li")
        expect(versions).to_have_count(2)
        expect(versions.nth(0)).to_contain_text("v1 findings")
        expect(versions.nth(0)).to_contain_text("Challenge 1")
        expect(versions.nth(1)).to_contain_text("v2 clean, current")
        expect(versions.nth(1).locator(".dot.clean")).to_have_count(1)
        expect(plan.locator(".versions p-button")).to_have_count(0)  # the plan's versions take no action here
        pds.settled(page)
        fold.locator("summary").click()
        expect(page.get_by_text("Keep the caption readable")).to_be_visible()
        expect(plan.get_by_text("Task review")).to_have_count(0)  # its review badges show with the details
        box = fold.locator("summary").bounding_box()
        assert box is not None
        assert (box["width"] >= 24, box["height"] >= 24) == (True, True), box

        page.locator("#details-switch").click()
        first = fold.locator("li", has_text="Add the flip button")
        expect(first).to_contain_text("Task review")
        expect(first).to_contain_text("R1 \u00b7 1 unverified")


@pytest.mark.browser
def test_an_unreviewed_last_revision_is_approved_only_once_the_owner_ticks_that_he_accepts_it(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    tail = change().model_copy(update={"slug": "tail"})
    said = "AC-2: the empty state has no check, so a list that renders nothing at all would pass every check we run"
    kept = RoundFinding(id="F4", text=said, raised=3, state="rejected")
    tail.loops["brief"] = RoundLoop(
        subject="brief", policy=RoundPolicy(), round=3, ended="max", unreviewed=["v2"], findings=[kept]
    )
    store.write(Lock("tail"), tail)
    with opened(base, "tail", pds) as page:
        items = page.locator(".actions")
        expect(items).to_contain_text(f"brief challenge F4, rejection not reviewed: {said}")  # whole, never cut
        expect(items).not_to_contain_text("No review yet")  # while shaping, the line on v2 says it
        page.get_by_role("button", name="Approve v2").click()
        dialog = pds.modal(page)
        confirm = dialog.get_by_role("button", name="Approve and start")
        expect(confirm).to_be_disabled()  # TD-255
        dialog.get_by_label("no challenger reviewed that revision", exact=False).check()
        expect(confirm).to_be_enabled()
        with replied(page, "/approve-brief"):
            confirm.click()
        expect(page.get_by_role("dialog")).to_be_hidden()
    assert store.fold(Lock("tail"), "tail", NOW)[0].brief.approved_version == 2
    with opened(base, "tail", pds) as page:  # approved, the unreviewed revision is still open
        expect(page.locator(".actions")).to_contain_text(
            "No review yet of brief v2, revised after its last challenge (brief challenge)"
        )


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
    with opened(base, "used", pds, details=True) as page:  # tool calls show with the details
        expect(page.get_by_text("Tool calls (8)")).to_be_visible()
        page.get_by_text("Tool calls (8)").click()
        expect(page.get_by_text("report_wrong_premise: 4 calls, 25% succeeded, 25% refused (1 invalid arguments), "
                                "1 lint, 1 late, 0 retries")).to_be_visible()  # fmt: skip
        expect(
            page.get_by_text("submit_result: 3 calls, 67% succeeded, 33% refused (1 not split), 1 retry")
        ).to_be_visible()
        expect(page.get_by_text("ask_question: 1 call, 100% succeeded, 0% refused, 0 retries")).to_be_visible()
        expect(page.get_by_text("Wrong tool choices: 2 denials by the guard")).to_be_visible()
    with opened(base, "idle", pds, details=True) as page:  # no call counted, yet its wrong choices show
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
    """The one inbox item the page sent; the host stores it before it replies."""
    with store.db.read() as db:
        [(item,)] = db.execute("SELECT item FROM inbox WHERE slug = ?", (slug,)).fetchall()
    return item


def replied(page: Any, path: str) -> Any:
    """Wait, around a click, for the host's reply to the page's POST to *path*. The call can still be pending when the
    click returns, and every call of the page goes through a route handler that runs only while the test waits on
    Playwright: without this wait the call can still be held there when the browser closes."""
    return page.expect_response(lambda r: r.request.method == "POST" and r.url.split("?")[0].endswith(path))


def answer(page: Any, form: Any) -> None:
    """Click Answer and wait for the host's reply."""
    with replied(page, "/answers"):
        form.get_by_role("button", name="Answer").click()


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
    with opened(base, "greet", pds, details=True) as page:
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
        answer(page, form)
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
        answer(page, form)
        expect(page.locator("#detail")).not_to_contain_text("Not done")
    item = sent(store, "greet").replace(" ", "")
    assert '"classed":"clarification"' in item
    assert '"statement":"ThegreetingisinEnglish."' in item


@pytest.mark.browser
def test_a_second_answer_while_one_waits_is_refused_beside_the_form(page_url, pds) -> None:
    """#791: the page keeps the form while an answer waits for the runner; a second one is refused where it was sent."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())
    store.put_inbox("greet", AnswerItem(at=NOW, question="q1", option="de", classed="event"))
    with opened(base, "greet", pds) as page:
        form = page.locator("section.act", has_text="Question q1")
        form.get_by_label("English").check()
        form.get_by_label("It only settles how the work goes on").check()
        answer(page, form)
        expect(form.locator(".refused")).to_contain_text("question q1 already has an answer waiting to be applied")
    assert '"option":"de"' in sent(store, "greet").replace(" ", "")  # the first answer, alone in the inbox


@pytest.mark.browser
def test_an_answer_the_change_no_longer_waits_on_is_refused_and_the_reason_stays(page_url, pds) -> None:
    """#914: the page still showed the question when the Change moved on; the refusal outlives its form."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("greet"), asking())
    stale: dict[str, str] = {}

    def frozen(route) -> None:  # the detail as the page first read it, whatever the store says now
        if route.request.method != "GET":
            return route.fallback()
        stale.setdefault("body", route.fetch().text())
        return route.fulfill(content_type="application/json", body=stale["body"])

    detail = re.compile(r".*/changes/greet(\?.*)?$")
    reason = "question q1 no longer waits on an answer: its intent changed"
    with opened(base, "greet", pds) as page:
        page.route(detail, frozen)
        form = page.locator("section.act", has_text="Question q1")
        expect(form).to_contain_text("Which language?")
        for _ in range(100):  # the page's next poll freezes the question's detail before the Change moves
            if "body" in stale:
                break
            page.wait_for_timeout(100)
        assert "Which language?" in stale["body"]
        moved = asking().model_copy(update={"step": m.Step(kind=m.StepKind.SHAPE), "outcome": None})
        store.write(Lock("greet"), moved)
        form.get_by_label("English").check()
        form.get_by_label("It only settles how the work goes on").check()
        answer(page, form)
        expect(form.locator(".refused")).to_contain_text(reason)
        page.unroute(detail, frozen)
        expect(form).to_have_count(0, timeout=10_000)
        top = page.locator("#detail .refused")
        expect(top).to_be_visible()
        expect(top).to_contain_text(reason)
        paused = moved.model_copy(update={"intent": m.Intent(paused_at=NOW, pause_reason="lunch")})
        store.write(Lock("greet"), paused)  # a later change of the forms keeps it too
        expect(page.locator("#detail .status p-tag")).to_have_text("Paused", timeout=10_000)
        expect(top).to_contain_text(reason)
        page.locator("#changes a[data-key='flip']").click()
        expect(page.locator("#detail h2")).to_have_text("Flip the hero")
        expect(page.locator("#detail .refused")).to_have_count(0)
    with store.db.read() as db:
        assert db.execute("SELECT count(*) FROM inbox").fetchone() == (0,)


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
        answer(page, form)
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
def test_a_shaping_rows_next_action_says_whether_the_owner_approves_or_the_shaping_chat_continues(
    page_url, pds
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    waits = m.Outcome(exit=m.Exit.PENDING, waiting=m.Waiting.CHAT, who="you", reason="approve brief v2", at=NOW)
    store.write(Lock("flip"), change().model_copy(update={"outcome": waits}))  # v2 challenged: the owner approves it
    revises = waits.model_copy(update={"reason": "the shaper revises brief v1 for F1"})
    tidy = m.Brief(version=1, title="Tidy the footer")
    store.write(Lock("tidy"), m.Change(slug="tidy", brief=tidy, step=m.Step(kind=m.StepKind.SHAPE), outcome=revises))
    with opened(base, "flip", pds) as page:
        flip, tidy = (page.locator(f"#changes .card:has(a[data-key='{k}']) p.next") for k in ("flip", "tidy"))
        expect(flip).to_have_text("Next: Approve brief")
        expect(tidy).to_have_text("Next: Continue in the shaping chat")


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
def test_recent_activity_reads_in_words_with_one_line_per_merge_and_repeats_counted(page_url, pds, whole_error) -> None:
    """C4: the display only; the activity file keeps every event as recorded. A force-stop reason shows whole (#951)."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    stopped = f"runtime stop failed: RuntimeError: {whole_error}"
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
        {"event": "force-stop", "reason": stopped, "runtime_pid": 41, "at": "2026-10-16T01:06:20+00:00"},
    ]  # fmt: skip
    for e in events:
        store.log(Lock("flip"), "flip", e)
    with opened(base, "flip", pds, details=True) as page:  # Recent activity shows with the details
        lines = page.locator("#detail .log li")
        expect(lines).to_have_count(11)
        said = lines.nth(0).locator(":scope > span")
        assert said.text_content() == " ".join(f"Tried to force the session to stop: {stopped}".split())  # one line
        expect(lines.nth(1)).to_contain_text("Lint incomplete (ruff, mypy could not run)")
        expect(lines.nth(2)).to_contain_text("Clean-up waiting: waiting for checks")
        expect(lines.nth(3)).to_have_text(re.compile(r"Undid task t1, attempt 2$"))  # not counted with the failure
        expect(lines.nth(4)).to_contain_text("Could not undo task t1, attempt 2: conflict in '/Users/me/repo/hero.css'")
        expect(lines.nth(5)).to_contain_text("Lint not run: ruff: no configuration for new.py")
        expect(lines.nth(6)).to_contain_text("Workspace flip kept: large ignored files")
        expect(lines.nth(7)).to_contain_text("Merged PR #20 as 77541c4 (squash)")
        expect(lines.nth(8)).to_have_text(re.compile(r"Check feel ended; its cleanup ran$"))
        expect(lines.nth(9)).to_have_text(re.compile(r"Submitted its result\s*\u00d73, 3 times$"))
        kept = r"Clean-up finished: workspace kept: large ignored files \(/Users/Jane Doe/\.owlbear/wt/flip\)$"
        expect(lines.nth(10)).to_have_text(re.compile(kept))  # a recorded reason shows as recorded, spaced path whole
        expect(lines.nth(6)).not_to_contain_text("/Users/")  # the entry's own path is named by its folder
        exact = page.evaluate(
            "(at) => at.map((iso) => new Date(iso).toLocaleString())", [events[1]["at"], events[3]["at"]]
        )
        expect(lines.nth(9).locator("time")).to_have_attribute("title", " to ".join(exact))  # the exact times on hover
    assert [e["event"] for e in store.events("flip")][-len(events) :] == [e["event"] for e in events]


BROKEN = m.Stop(kind=m.ErrorKind.STATE, reason="GitHub refused the push", action="Grant the token push rights",
                resume="GitHub takes the push", at=NOW)  # fmt: skip
AFTER = "Recovery accepted: Delivery reruns the step when it can run. Existing pauses are kept."
WHEN = {
    "stopped": "Delivery runs the build step again on its next pass. While",
    "paused": "once you resume this Change",
    "cleanup-paused": "even while paused",
}


def stopped(case: str, stop: m.Stop = BROKEN) -> m.Change:
    """The approved Change stopped in its build, or its cleanup; paused by the owner, or stopped by a liveness check."""
    kind = m.StepKind.CLEANUP if case == "cleanup-paused" else m.StepKind.BUILD
    if case == "liveness":
        stop = m.Stop(kind=m.ErrorKind.LIVENESS, reason="processes still present: 7", action="End processes 7",
                      resume="The host sees none of them", at=NOW)  # fmt: skip
    c = change()
    brief = c.brief.model_copy(update={"approved_version": 2, "approved_at": NOW})
    c = c.model_copy(update={"brief": brief, "step": m.Step(kind=kind)})
    c = apply(c, StepResult(exit=m.Exit.STOP, reason=stop.reason, stop=stop), NOW)
    if case.endswith("paused"):
        c = c.model_copy(update={"intent": c.intent.model_copy(update={"paused_at": NOW})})
    return c


@contextlib.contextmanager
def launched(base: str, pds: Any) -> Iterator[Any]:
    """The Changes page on the flip Change in Chromium; a missing browser fails rather than skips."""
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw, contextlib.closing(pw.chromium.launch()) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/?change=flip")
        yield page


@pytest.mark.browser
@pytest.mark.parametrize("case", ["stopped", "paused", "cleanup-paused", "liveness", "unset"])
def test_the_owner_reruns_a_stopped_step_after_confirming_what_follows(page_url, pds, case, monkeypatch) -> None:
    """#754: the Stopped notice offers "Done: run the step again" unless a liveness check holds the stop or a setting
    is unset (D-01M61SBWK4VE4MNTD35TR0VPS8)."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    if case == "unset":
        monkeypatch.setattr(machine_settings, "BASE", None)
        monkeypatch.setattr(config, "BASE", None)
    c = stopped(case)
    store.write(Lock("flip"), c)
    with launched(base, pds) as page:
        note = page.locator("p-inline-notification[heading='Stopped']")
        expect(note).to_contain_text(f"{c.stop.reason}. What to do: {c.stop.action}.")
        if case.endswith("paused"):
            expect(page.get_by_role("region", name="Selected Change").get_by_text("Paused", exact=True)).to_be_visible()
        again = page.get_by_role("button", name="Done: run the step again")
        if case in {"liveness", "unset"}:
            if case == "unset":
                count = len(work_block.of_store(store).keys)
                expect(note).to_contain_text(
                    f"{count} settings are unset; set them on the Settings page to run the step again."
                )
                expect(note).not_to_contain_text("agents.")  # how many, never which keys
            expect(again).to_have_count(0)
            return
        posts = []
        page.on("request", lambda r: posts.append(r.post_data_json) if r.url.endswith("/recovery") else None)
        expect(again).to_be_visible()
        box = again.bounding_box()
        assert box["width"] >= 24
        assert box["height"] >= 24
        again.click()
        dialog = page.locator("p-modal.ask")
        expect(dialog.get_by_role("heading", name="Run the stopped step again?")).to_be_visible()
        for said in [f"You did what the stop asked ({c.stop.action}), so the stop clears.", WHEN[case], "AI credits",
                     "You can pause afterwards", "once the running step ends", "doesn't undo", "stops again",
                     "The Change stays stopped"]:  # fmt: skip
            expect(dialog).to_contain_text(said)
        dialog.get_by_role("button", name="Keep it stopped").click()
        expect(dialog).to_have_count(0)
        expect(again).to_be_focused()
        assert posts == []
        again.click()
        with replied(page, "/recovery") as reply:
            page.locator("p-modal.ask").get_by_role("button", name="Run it again").click()
        assert (reply.value.status, posts) == (200, [c.stop.model_dump(mode="json", include={"action", "at"})])
        assert '"kind":"recovery"' in sent(store, "flip").replace(" ", "")
        expect(page.get_by_text(AFTER)).to_be_visible()


@pytest.mark.browser
def test_a_stop_that_changed_since_the_page_showed_it_is_not_cleared(page_url, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    store, base = page_url
    store.write(Lock("flip"), stopped("stopped"))
    with launched(base, pds) as page:
        again = page.get_by_role("button", name="Done: run the step again")
        again.click()
        store.write(Lock("flip"), stopped("stopped", BROKEN.model_copy(update={"at": NOW + timedelta(minutes=5)})))
        with replied(page, "/recovery") as reply:
            page.locator("p-modal.ask").get_by_role("button", name="Run it again").click()
        assert reply.value.status == 409
        refused = page.locator(".refused")
        expect(refused).to_contain_text("Not done")
        expect(refused).to_contain_text("The stop changed since the page showed it; reload")
        with store.db.read() as db:
            assert db.execute("SELECT count(*) FROM inbox").fetchone() == (0,)


@pytest.mark.browser
def test_a_refused_approval_shows_its_whole_reason(page_url, pds, monkeypatch, whole_error) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    def unavailable(*_args, **_kwargs):
        raise decision_store.DecisionsUnavailable(whole_error)

    monkeypatch.setattr(decision_publication.decision_archive, "lasting", unavailable)
    store, base = page_url
    reason = f"{decision_publication.REFUSED}: DecisionsUnavailable: {whole_error}"
    with opened(base, "flip", pds) as page:
        page.get_by_role("button", name="Approve v2").click()
        with replied(page, "/approve-brief") as reply:
            pds.modal(page).get_by_role("button", name="Approve and start").click()
        assert (reply.value.status, reply.value.json()["detail"]) == (409, reason)
        refused = page.locator(".refused p-inline-notification")
        expect(refused).to_contain_text(reason)
    assert store.read("flip").brief.approved_version is None
    (event,) = [e for e in store.events("flip") if e.get("event") == "approval-refused"]
    assert event["reason"] == reason
