"""The Decisions tab in a real browser: list, filters, an entry, an owner's replacement and its receipt (TD-419)."""

from __future__ import annotations

import contextlib
import json
import re
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Iterator

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
AN_ID = re.compile(r"D-[0-9A-Z]{26}")  # titles identify decisions on the page, never ids


class Host:
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    repo = None  # the impact report then says it cannot read the clone
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


@pytest.fixture
def store(tmp_path, shared_repo) -> Store:
    """A project whose data repository holds a project decision and a Global one, both published."""
    shared = DataRepo(shared_repo[0])
    shared.claim(PROJECT, "github.com/acme/shop-site")
    write(make(), shared.root / PROJECT)
    write(make(scope=Scope.GLOBAL, project="", title="Pages are plain HTML", statement="No build step."), shared.root)
    for args in (("add", "-A"), ("commit", "-qm", "seed"), ("push", "-q", "origin", "HEAD")):
        subprocess.run(["git", *args], cwd=shared.root, check=True, capture_output=True)  # noqa: S603, S607
    return Store(tmp_path / "store", shared, PROJECT)


@contextlib.contextmanager
def decisions_page(store: Store, pds: Any) -> Iterator[Any]:
    """The Decisions page in a real browser: only the test host and the PDS CDN answer."""
    import uvicorn  # noqa: PLC0415
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning"))
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
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/decisions#token=tok")
            yield page
            browser.close()
    finally:
        server.should_exit = True


def in_force(store: Store, project: str = PROJECT) -> dict[str, Decision]:
    view = decision_store.load(store.shared, project).snapshot
    return {e.decision.statement: e.decision for e in view.entries if e.decision.state is State.IN_FORCE}


def held_once(page: Any, held: list[Any]) -> Any:
    """The first request the test holds, once the page has sent it."""
    for _ in range(100):
        if held:
            return held.pop(0)
        page.wait_for_timeout(50)
    pytest.fail("the page sent no request to hold")


@pytest.mark.browser
def test_a_late_global_list_cannot_name_or_retarget_the_owlbear_list(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    write(make(project="owlbear", title="Lint once", statement="Linted once.", inherited=True),
          store.shared.root / "owlbear")  # fmt: skip
    with decisions_page(store, pds) as page:
        held: list[Any] = []
        page.route(lambda url: "/decisions?" in url and "where=global" in url,
                   lambda route, _request: held.append(route))  # fmt: skip
        pds.pick(page, "Show", "global")
        global_list = held_once(page, held)
        pds.pick(page, "Show", "owlbear")
        expect(page.locator(".entry", has_text="Lint once")).to_have_count(1)
        global_list.continue_()
        page.wait_for_load_state("networkidle")
        expect(page.locator(".entry", has_text="Lint once")).to_have_count(1)
        card = page.locator(".entry", has_text="Pages are plain HTML")
        card.get_by_role("button", name="Open").click()
        card.get_by_role("button", name="Record an exception").click()
        page.get_by_label("New rule").fill("Pages may use a build step in OwlBear.")
        card.get_by_role("button", name="Record the exception").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("for OwlBear?")
        with page.expect_request(lambda r: r.url.endswith("/exception?where=owlbear")) as sent:
            dialog.get_by_role("button", name="Record the exception").click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        body = sent.value.post_data_json
    assert body["confirmed"] is True
    assert "Pages may use a build step in OwlBear." in in_force(store, "owlbear")
    assert "Pages may use a build step in OwlBear." not in in_force(store)


@pytest.mark.browser
def test_a_form_opened_in_one_scope_stays_in_it_when_the_owner_switches_scope(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    write(make(project="owlbear", title="Lint once", statement="Linted once.", inherited=True),
          store.shared.root / "owlbear")  # fmt: skip
    with decisions_page(store, pds) as page:
        card = page.locator(".entry", has_text="Pages are plain HTML")
        card.get_by_role("button", name="Open").click()
        card.get_by_role("button", name="Record an exception").click()
        page.get_by_label("New rule").fill("Pages may use a build step here.")
        pds.pick(page, "Show", "owlbear")
        expect(page.locator(".entry", has_text="Lint once")).to_have_count(1)
        expect(page.get_by_label("New rule")).to_have_count(0)
        pds.pick(page, "Show", "all")
        expect(page.get_by_label("New rule")).to_have_count(1)
        card = page.locator(".entry", has_text="Pages are plain HTML")
        card.get_by_role("button", name="Record the exception").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("for shop-site?")
        with page.expect_request(lambda r: r.url.endswith("/exception")) as sent:
            dialog.get_by_role("button", name="Record the exception").click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        posted_to = sent.value.url
    assert "where=" not in posted_to
    assert "Pages may use a build step here." in in_force(store)
    assert "Pages may use a build step here." not in in_force(store, "owlbear")


@pytest.mark.browser
def test_a_confirmed_write_still_in_flight_keeps_the_scope_it_was_confirmed_in(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    write(make(project="owlbear", title="Lint once", statement="Linted once.", inherited=True),
          store.shared.root / "owlbear")  # fmt: skip
    with decisions_page(store, pds) as page:
        held: list[Any] = []
        page.route(lambda url: url.endswith("/exception"), lambda route, _request: held.append(route))
        card = page.locator(".entry", has_text="Pages are plain HTML")
        card.get_by_role("button", name="Open").click()
        card.get_by_role("button", name="Record an exception").click()
        page.get_by_label("New rule").fill("Pages may use a build step here.")
        card.get_by_role("button", name="Record the exception").click()
        pds.answer(page, "Record the exception")
        in_flight = held_once(page, held)
        posted_to = in_flight.request.url
        pds.pick(page, "Show", "owlbear")
        expect(page.locator(".entry", has_text="Lint once")).to_have_count(1)
        in_flight.continue_()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
    assert "where=" not in posted_to
    assert "Pages may use a build step here." in in_force(store)
    assert "Pages may use a build step here." not in in_force(store, "owlbear")


@pytest.mark.browser
def test_the_owner_filters_opens_and_replaces_a_decision_and_sees_its_receipt(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with decisions_page(store, pds) as page:
        expect(page.locator("#shown")).to_have_text("2 of 2 shown")
        expect(page.get_by_role("navigation").get_by_role("link", name="Decisions")).to_have_attribute(
            "aria-current", re.compile(r"page|true"))  # fmt: skip
        pds.pick(page, "Show", "global")
        expect(page.locator(".entry")).to_have_count(1)
        expect(page.locator(".entry")).to_contain_text("Pages are plain HTML")
        pds.pick(page, "Show", "all")
        page.get_by_label("Search").fill("sqlite")
        page.get_by_label("Search").press("Enter")
        expect(page.locator("#shown")).to_have_text("1 of 2 shown")
        card = page.locator(".entry", has_text="Notes live in SQLite")
        card.get_by_role("button", name="Open").click()
        expect(card.locator("#detail")).to_contain_text("autonomous")
        expect(card.locator("#detail")).to_contain_text("changed")  # its file's history, by action only
        expect(card.locator("#detail")).not_to_contain_text("seed")
        expect(card.locator("#detail")).not_to_contain_text(AN_ID)
        card.get_by_role("button", name="Replace").click()
        page.get_by_label("New rule").fill("Notes live in Postgres.")
        expect(page.get_by_label("Your words")).to_have_count(0)
        card.get_by_role("button", name="Replace").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("Then: Notes live in Postgres.")
        confirm = dialog.get_by_role("button", name="Replace")
        expect(confirm).to_be_disabled()  # a supersession says why
        dialog.get_by_label("Why it changes").fill("The notes outgrew one table.")
        with page.expect_request(lambda r: r.url.endswith("/replace")) as sent:
            confirm.click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        expect(page.locator("#receipts")).not_to_contain_text(AN_ID)
        page.get_by_label("Search").fill("")
        page.get_by_label("Search").press("Enter")
        successor = page.locator(".entry", has_text="Notes live in Postgres.")
        expect(successor).to_have_count(1)
        expect(successor.locator(".read-back")).to_have_text(f"Confirmed {datetime.now(UTC).date().isoformat()}")
        expect(page.locator(".entry", has_text="Notes live in one SQLite table.")).to_have_count(0)  # replaced, hidden
        body = sent.value.post_data_json
    assert (body["confirmed"], "words" in body) == (True, False)
    assert in_force(store)["Notes live in Postgres."].origin is Origin.DECIDED
    assert "Why it changed: The notes outgrew one table." in in_force(store)["Notes live in Postgres."].rationale


@pytest.mark.browser
def test_a_decided_decision_is_replaced_only_once_the_owner_ticks_that_he_re_decides_it(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    rule = make(title="Tags are free text", statement="Any tag.", origin=Origin.DECIDED, read_back="2026-10-20")
    write(rule, store.shared.root / PROJECT)
    with decisions_page(store, pds) as page:
        card = page.locator(".entry", has_text="Tags are free text")
        expect(card.locator(".read-back")).to_have_text("Confirmed 2026-10-20")
        card.get_by_role("button", name="Open").click()
        card.get_by_role("button", name="Replace").click()
        page.get_by_label("New rule").fill("Tags come from a list.")
        card.get_by_role("button", name="Replace").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("Confirmed 2026-10-20")
        confirm = dialog.get_by_role("button", name="Replace")
        expect(confirm).to_be_disabled()
        dialog.get_by_label("I re-decide this decision").check()
        expect(confirm).to_be_disabled()
        dialog.get_by_label("Why it changes").fill("A list keeps tags consistent.")
        confirm.click()
        expect(page.locator("#receipts")).to_contain_text("published")
    assert "Tags come from a list." in in_force(store)
    assert "Any tag." not in in_force(store)


@pytest.mark.browser
def test_the_owner_resolves_a_three_way_conflict_by_keeping_one(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    old = make(title="Exports", statement="Exports are CSV.", state=State.REPLACED)
    succeeding = (Link(type=LinkType.REPLACES, target=old.id),)
    write(old, store.shared.root / PROJECT)
    for n in ("JSON", "XML", "YAML"):
        write(make(title=f"Exports in {n}", statement=f"Exports are {n}.", links=succeeding, conflict=True),
              store.shared.root / PROJECT)  # fmt: skip
    with decisions_page(store, pds) as page:
        card = page.locator(".entry", has_text="Exports in XML")
        card.get_by_role("button", name="Open").click()
        expect(card.locator('p-button[variant="primary"]')).to_have_text(["Keep this one"])  # the conflict asks
        card.get_by_role("button", name="Keep this one").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("Withdrawn: Exports in JSON")
        dialog.get_by_label("Why this one stays").fill("The partner reads XML.")
        dialog.get_by_role("button", name="Keep this one").click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        expect(page.locator("#error")).to_be_hidden()
    assert sorted(in_force(store)) == ["Exports are XML.", "No build step.", "Notes live in one SQLite table."]


@pytest.mark.browser
def test_the_owner_reads_back_a_queued_decision_and_shows_owlbears_own_decisions(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    rule = make(title="Exports are CSV", statement="Exports are CSV.", read_back="pending",
                read_back_why="A partner asked for JSON.", read_back_kind="uncertain")  # fmt: skip
    write(rule, store.shared.root / PROJECT)
    write(make(project="owlbear", title="Lint once", statement="Linted once.", inherited=True),
          store.shared.root / "owlbear")  # fmt: skip
    with decisions_page(store, pds) as page:
        queue = page.locator("#queue")
        item = queue.locator(".queued", has_text="Exports are CSV")
        expect(item).to_contain_text("A partner asked for JSON.")
        expect(item).to_contain_text("Uncertain")
        item.get_by_role("button", name="Still right").click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        expect(queue.locator(".queued")).to_have_count(0)
        expect(queue).to_contain_text("No decision waits to be read back.")
        expect(page.locator(".entry", has_text="Exports are CSV").locator(".read-back")).to_have_text(
            f"Confirmed {datetime.now(UTC).date().isoformat()}")  # fmt: skip
        pds.pick(page, "Show", "owlbear")
        expect(page.locator(".entry", has_text="Lint once")).to_have_count(1)
        expect(page.locator(".entry", has_text="Lint once").locator(".read-back")).to_have_text(
            "Inherited, never read back")  # fmt: skip
        expect(page.locator(".entry", has_text="Pages are plain HTML")).to_have_count(1)
        expect(page.locator(".entry", has_text="Notes live in SQLite")).to_have_count(0)
        expect(page.locator(".entry", has_text="Lint once").locator(".scope")).to_have_text("OwlBear")
    held = in_force(store)["Exports are CSV."]
    assert (held.read_back, held.read_back_why, held.origin) == (
        datetime.now(UTC).date().isoformat(), "A partner asked for JSON.", Origin.AUTONOMOUS)  # fmt: skip


@pytest.mark.browser
def test_the_owner_marks_a_decided_decision_he_never_made_approved(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    rule = make(title="Windows stay paused", statement="Paused.", origin=Origin.DECIDED, read_back="2026-10-21")
    write(rule, store.shared.root / PROJECT)
    with decisions_page(store, pds) as page:
        card = page.locator(".entry", has_text="Windows stay paused")
        card.get_by_role("button", name="Open").click()
        card.get_by_role("button", name="Mark approved").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("an agent's proposal you accepted")
        dialog.get_by_label("Where it really came from").fill("An agent proposed it; I accepted it.")
        with page.expect_request(lambda r: r.url.endswith("/correct-origin")) as sent:
            dialog.get_by_role("button", name="Mark approved").click()
        expect(page.locator("#receipts")).to_contain_text("published")
        body = sent.value.post_data_json
    assert body == {"revision": rule.revision, "origin": "approved", "reason": "An agent proposed it; I accepted it.",
                    "confirmed": True}  # fmt: skip
    held = in_force(store)["Paused."]
    assert (held.origin, held.read_back) == (Origin.APPROVED, "2026-10-21")


@pytest.mark.browser
def test_the_read_back_queue_asks_with_one_primary_and_withdrawing_is_never_it(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    for title in ("Exports are CSV", "Builds run nightly"):
        write(make(title=title, statement=f"{title}.", read_back="pending", read_back_why="Asked again.",
                   read_back_kind="uncertain"), store.shared.root / PROJECT)  # fmt: skip
    with decisions_page(store, pds) as page:
        queue = page.locator("#queue")
        expect(queue.locator(".queued")).to_have_count(2)
        expect(queue.locator('p-button[variant="primary"]')).to_have_text(["Still right"])  # the lead's only
        expect(queue.locator(".queued").first.locator('p-button[variant="primary"]')).to_have_count(1)
        item = queue.locator(".queued").nth(1)
        failing = re.compile(r".*/decisions/D-[^/?]+(\?.*)?$")
        page.route(failing, lambda route: route.fulfill(status=503, body="down"))
        with page.expect_response(failing):
            item.get_by_role("button", name="Replace or withdraw").click()
        expect(queue.locator('p-button[variant="primary"]')).to_have_text(["Still right"])  # a failed read keeps it
        page.unroute(failing)
        item.get_by_role("button", name="Close").click()
        item.get_by_role("button", name="Replace or withdraw").click()
        expect(item.locator("#detail")).to_be_visible()
        expect(queue.locator('.queued > .row p-button[variant="primary"]')).to_have_count(0)  # its actions lead
        expect(queue.locator('p-button[variant="primary"]')).to_have_count(1)
        item.get_by_role("button", name="Withdraw").click()
        dialog = pds.modal(page)
        expect(dialog.locator('p-button[variant="primary"]')).to_have_text(["Cancel"])  # declining leads
        expect(dialog.locator("p-button", has_text="Withdraw")).to_have_attribute("variant", "secondary")
        dialog.get_by_role("button", name="Cancel").click()
        item.get_by_role("button", name="Read back").click()
        pds.modal(page).get_by_role("button", name="Confirm as it reads").click()
        expect(queue.locator(".queued")).to_have_count(1)
        expect(queue.locator('p-button[variant="primary"]')).to_have_text(["Still right"])  # the one left leads again


@pytest.mark.browser
def test_the_owner_reads_back_an_open_decision_by_confirming_it_and_sees_no_record_rows(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    rule = make(title="Exports are CSV", statement="Exports are CSV.", aliases=("TD-12",), inherited=True)
    write(rule, store.shared.root / PROJECT)
    with decisions_page(store, pds) as page:
        card = page.locator(".entry", has_text="Exports are CSV")
        card.get_by_role("button", name="Open").click()
        expect(card.locator("#detail")).to_contain_text("autonomous")
        expect(card.locator("#detail")).not_to_contain_text("TD-12")
        expect(card.locator("#detail")).not_to_contain_text("Record rows")
        expect(card.locator('p-button[variant="primary"]')).to_have_text(["Read back"])  # never Withdraw
        card.get_by_role("button", name="Read back").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("Exports are CSV.")
        with page.expect_request(lambda r: r.url.endswith("/read-back")) as sent:
            dialog.get_by_role("button", name="Confirm as it reads").click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        body = sent.value.post_data_json
    assert body == {"revision": rule.revision, "confirmed": True}
    held = in_force(store)["Exports are CSV."]
    assert (held.read_back, held.inherited) == (datetime.now(UTC).date().isoformat(), False)


@pytest.mark.browser
def test_the_owner_checks_a_replacements_impact_and_schedules_its_fixes(store, pds, github):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    old = make(title="Exports are CSV", statement="Exports are CSV.", state=State.REPLACED)
    new = make(title="Exports are JSON", statement="Exports are JSON.", links=(Link(type=LinkType.REPLACES,
               target=old.id),), rationale="Effect on existing work: it forbids existing behaviour")  # fmt: skip
    for d in (old, new):
        write(d, store.shared.root / PROJECT)
    record = {"slug": "c1", "outcome": "merged", "pr": {"url": "https://github.com/acme/shop-site/pull/7"},
              "brief": {"title": "Exports", "decisions": [{"id": old.id}]}}  # fmt: skip
    (store.shared.root / PROJECT / "changes").mkdir()
    (store.shared.root / PROJECT / "changes" / "20261020-090000-c1.json").write_text(json.dumps(record))
    with decisions_page(store, pds) as page:
        card = page.locator(".entry", has_text="Exports are JSON")
        card.get_by_role("button", name="Open").click()
        card.get_by_role("button", name="Check the impact").click()
        impact = card.locator("#impact")
        expect(impact.locator(".old")).to_contain_text("Exports are CSV.")
        expect(impact.locator(".divergence")).to_contain_text("forbids existing behaviour")
        expect(impact.locator(".impact-project")).to_contain_text("https://github.com/acme/shop-site/pull/7")
        impact.get_by_role("button", name="Schedule fixes").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("shop-site: unknown")
        dialog.get_by_role("button", name="Schedule fixes").click()
        expect(impact).to_contain_text(f"#1 Apply decision “Exports are JSON” in {PROJECT}: Exports are JSON")
        expect(card.locator("#detail")).not_to_contain_text(AN_ID)
    [issue] = github.issues.values()
    assert f"Old rule \u201c{old.title}\u201d: {old.statement}" in issue["body"]
    assert "- [ ] Change c1: Exports (https://github.com/acme/shop-site/pull/7)" in issue["body"]
