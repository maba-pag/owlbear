"""The Decisions tab in a real browser: list, filters, an entry, an owner's replacement and its receipt (TD-419)."""

from __future__ import annotations

import contextlib
import re
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, OwnerWords, Scope, State, new_id, write
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


class Host:
    wake = SimpleNamespace(set=lambda: None)
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


def in_force(store: Store) -> dict[str, Decision]:
    view = decision_store.load(store.shared, PROJECT).snapshot
    return {e.decision.statement: e.decision for e in view.entries if e.decision.state is State.IN_FORCE}


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
        expect(card.locator("#detail")).to_contain_text("seed")  # its file's history
        card.get_by_role("button", name="Replace").click()
        page.get_by_label("New rule").fill("Notes live in Postgres.")
        card.get_by_role("button", name="Replace").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("Then: Notes live in Postgres.")
        confirm = dialog.get_by_role("button", name="Replace")
        expect(confirm).to_be_disabled()  # a supersession says why
        dialog.get_by_label("Why it changes").fill("The notes outgrew one table.")
        confirm.click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        page.get_by_label("Search").fill("")
        page.get_by_label("Search").press("Enter")
        expect(page.locator(".entry", has_text="Notes live in Postgres.")).to_have_count(1)
        expect(page.locator(".entry", has_text="Notes live in one SQLite table.")).to_have_count(0)  # replaced, hidden
    assert in_force(store)["Notes live in Postgres."].origin is Origin.DECIDED
    assert "Why it changed: The notes outgrew one table." in in_force(store)["Notes live in Postgres."].rationale


@pytest.mark.browser
def test_a_decided_decision_is_replaced_only_once_the_owner_ticks_that_he_re_decides_it(store, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    words = (OwnerWords(text="Tags stay free.", date=AT.date()),)
    rule = make(title="Tags are free text", statement="Any tag.", origin=Origin.DECIDED, owner_words=words)
    write(rule, store.shared.root / PROJECT)
    with decisions_page(store, pds) as page:
        card = page.locator(".entry", has_text="Tags are free text")
        card.get_by_role("button", name="Open").click()
        card.get_by_role("button", name="Replace").click()
        page.get_by_label("New rule").fill("Tags come from a list.")
        card.get_by_role("button", name="Replace").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("Tags stay free.")
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
    write(make(project="owlbear", title="Lint once", statement="Linted once."), store.shared.root / "owlbear")
    with decisions_page(store, pds) as page:
        queue = page.locator("#queue")
        item = queue.locator(".queued", has_text="Exports are CSV")
        expect(item).to_contain_text("A partner asked for JSON.")
        expect(item).to_contain_text("Uncertain")
        item.get_by_role("button", name="Still right").click()
        expect(page.locator("#receipts")).to_contain_text("saved · committed · published · active")
        expect(queue.locator(".queued")).to_have_count(0)
        expect(queue).to_contain_text("No decision waits to be read back.")
        pds.pick(page, "Show", "owlbear")
        expect(page.locator(".entry", has_text="Lint once")).to_have_count(1)
        expect(page.locator(".entry", has_text="Pages are plain HTML")).to_have_count(1)
        expect(page.locator(".entry", has_text="Notes live in SQLite")).to_have_count(0)
        expect(page.locator(".entry", has_text="Lint once").locator(".scope")).to_have_text("OwlBear")
    held = in_force(store)["Exports are CSV."]
    assert (held.read_back, held.read_back_why, held.origin) == (
        datetime.now(UTC).date().isoformat(), "A partner asked for JSON.", Origin.AUTONOMOUS)  # fmt: skip
