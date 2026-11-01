"""The pages show which projects' work waits for their settings and hold the buttons that would start it (#808).

A real machine host serves two registered clones, alpha and beta, in Chromium; only the PDS CDN answers besides it.
Alpha leaves the CI poll interval unset, beta sets it in its own layer. The Maintenance and Backlog tests add the
shared repository, with a memory folder for each project, and a fake GitHub holding the backlog.
"""

from __future__ import annotations

import re
import socket
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_contracts.merge_records import Pullback
from owlbear_delivery_next.change_contracts.visual_records import OwnerCriterion
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import machine_settings, registry
from owlbear_delivery_next.state_store.backlog import Backlog
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 1, 1, tzinfo=UTC)
GAP = "prefs.ci_poll_seconds"
UNSET = f"settings unset: {GAP}; fill them in on the Settings page"
EVERY = "No work can be done until the unset settings are set."
NONE_OPEN = "every project's settings are unset or can't be read"
NO_FOLDER = "every folder's settings are unset or can't be read"
WAIT = 15_000  # ms: the machine's poll comes every 5 s, the Changes list's every 3 s


def asking() -> m.Change:
    """A Change asking the owner, with a visual criterion of his and a local target behind the merged one."""
    options = [m.Option(id="de", label="German"), m.Option(id="en", label="English")]
    question = m.Question(id="q1", step=m.StepKind.BUILD, text="Which language?", options=options)
    outcome = m.Outcome(exit=m.Exit.ASK, question="q1", reason="Which language?", who="you", at=NOW)
    kept = OwnerCriterion(id="K1", text="The hero stays centred", round=1, brief_version=1, at=NOW)
    behind = Pullback(state="behind", reason="local commits", at=NOW)
    step = m.Step(kind=m.StepKind.BUILD)
    return m.Change(
        slug="greet", questions=[question], outcome=outcome, step=step, owner_criteria=[kept], pullback=behind
    )


def clone(path: Path) -> Store:
    """A clone whose ``main`` holds one package of tests, with a Change that asks and one the owner paused."""
    (path / "tests").mkdir(parents=True)
    (path / "pyproject.toml").write_text("")
    (path / "tests" / "test_a.py").write_text("a\n" * 3)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=path, check=True,  # noqa: S603, S607
                       capture_output=True)  # fmt: skip
    store = Store.open(path)
    held = m.Change(slug="held", step=m.Step(kind=m.StepKind.BUILD), intent=m.Intent(paused_at=NOW))
    for change in (asking(), held):
        with store.lock(change.slug) as lock:
            store.write(lock, change)
    return store


def poll_interval(store: Store, seconds: int | None) -> None:
    """The project's own layer sets the CI poll interval, or leaves it to the layers under it (unset)."""
    prefs = Prefs(ci_poll_seconds=seconds)
    assert (
        store.save(store.config_path, Layer, lambda la: la.model_copy(update={"prefs": prefs}), "t", owner=True) == ""
    )


@dataclass
class Host2:
    """The browser page on the machine host, its address and the two projects' ids and stores."""

    page: Any
    base: str
    ids: dict[str, str]
    stores: dict[str, Store]
    errors: list[str] = field(default_factory=list)


@contextmanager
def _served(machine: Machine) -> Iterator[str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    # longer than the pages' polls: route.fetch() reuses a pooled socket, which uvicorn's 5 s default closes
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning", timeout_keep_alive=60))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    try:
        yield f"http://127.0.0.1:{sock.getsockname()[1]}"
    finally:
        server.should_exit = True


@pytest.fixture
def data(monkeypatch, shared_repo) -> Path:
    """The shared repository, alpha's and beta's folders keeping memory; asked for, it comes before the clones."""
    root = shared_repo[0]
    monkeypatch.setenv("OWLBEAR_DATA", str(root))
    for name in ("alpha", "beta"):
        (root / name / "memory").mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def host(tmp_path: Path, monkeypatch, pds, request) -> Iterator[Host2]:
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    if "data" in request.fixturenames:
        request.getfixturevalue("data")

    prefs = config.BASE.prefs.model_copy(update={"ci_poll_seconds": None})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"prefs": prefs}))
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)  # the scheduler runs; no runner starts
    stores = {name: clone(tmp_path / name) for name in ("alpha", "beta")}
    ids = {name: registry.register((tmp_path / name).resolve()).id for name in stores}
    poll_interval(stores["alpha"], None)  # alpha has its own layer, with the gap
    poll_interval(stores["beta"], 20)
    missing = (stores["alpha"].settings().missing, stores["beta"].settings().missing)
    assert (missing, machine_settings.current().missing) == (([GAP], []), [])
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=NOW, code=codebase.CURRENT)  # noqa: S106
    machine = Machine(record)
    machine.load_all()
    try:
        with _served(machine) as base, sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            pds.only(page, base)
            h = Host2(page, base, ids, stores)
            page.on("pageerror", lambda e: h.errors.append(str(e)))
            page.on("console", lambda msg: h.errors.append(msg.text) if msg.type == "error" else None)
            yield h
            browser.close()
            assert h.errors == []
    finally:
        machine.stop_all()


def held_with(scope: Any, name: str, why: str | re.Pattern[str]) -> None:
    """The button *name* in *scope* is there, its native button disabled, and its PDS button says why."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    button = scope.get_by_role("button", name=name, exact=True)
    expect(button).to_have_count(1)
    expect(button).to_be_disabled(timeout=WAIT)
    expect(scope.locator("p-button", has=scope.page.get_by_role("button", name=name, exact=True))).to_have_attribute(
        "title", why
    )


@pytest.mark.browser
def test_the_changes_page_names_the_blocked_project_and_holds_only_its_starting_buttons(host) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page, base, a, b = host.page, host.base, host.ids["alpha"], host.ids["beta"]
    page.goto(f"{base}/#token=t")
    banner = page.locator("#blocked")
    expect(banner).to_have_attribute("state", "warning", timeout=WAIT)
    expect(banner).to_have_attribute("heading", "alpha can't start work until its settings are set.")
    expect(banner.locator("li")).to_have_text([f"alpha: {UNSET}"])
    expect(banner.get_by_role("link", name="alpha")).to_have_attribute("href", f"/config?project={a}")
    for shown in (a, b):  # the banner is machine-wide, whichever project the page shows
        page.goto(f"{base}/?project={shown}")
        expect(page.locator("#blocked li")).to_have_text([f"alpha: {UNSET}"], timeout=WAIT)

    page.goto(f"{base}/?change={a}%2Fheld")
    detail = page.locator("#detail")
    held_with(detail, "Resume", UNSET)
    page.goto(f"{base}/?change={a}%2Fgreet")
    form = detail.locator("section.act", has_text="Question q1")
    held_with(form, "Answer", UNSET)
    for usable in ("Pause", "Withdraw", "Pull"):  # what starts no work stays usable
        expect(detail.get_by_role("button", name=usable)).to_be_enabled()
    words = form.get_by_label("Your answer in words")
    words.fill("the site is read in Canada")
    poll_interval(host.stores["alpha"], 30)  # the owner sets the gap: alpha's work may start
    expect(form.get_by_role("button", name="Answer")).to_be_enabled(timeout=WAIT)
    expect(banner).to_have_count(0)
    expect(words).to_have_value("the site is read in Canada")
    poll_interval(host.stores["alpha"], None)
    expect(form.get_by_role("button", name="Answer")).to_be_disabled(timeout=WAIT)
    expect(words).to_have_value("the site is read in Canada")

    page.goto(f"{base}/?change={b}%2Fgreet")
    expect(detail.locator("section.act").get_by_role("button", name="Answer")).to_be_enabled(timeout=WAIT)
    expect(detail.get_by_role("button", name="Pause")).to_be_enabled()


@pytest.mark.browser
def test_new_change_offers_only_projects_whose_work_may_start_and_follows_the_poll(host, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page, base, b = host.page, host.base, host.ids["beta"]
    page.goto(f"{base}/#token=t")
    expect(page.locator("#blocked")).to_have_attribute("state", "warning", timeout=WAIT)
    page.get_by_role("button", name="New Change").click()
    chooser = page.locator("#choose")
    select = pds.select(chooser, "Shape the new Change in")
    expect(select.locator("p-select-option")).to_have_text(["beta"])
    expect(select).to_have_js_property("value", b)
    go = chooser.get_by_role("button", name="Continue")
    expect(go).to_be_enabled()

    poll_interval(host.stores["beta"], None)  # beta is blocked as well: no project may start work
    expect(page.locator("#blocked")).to_have_attribute("state", "error", timeout=WAIT)
    expect(page.locator("#blocked")).to_have_attribute("heading", EVERY)
    held_with(chooser, "Continue", NONE_OPEN)
    held_with(page.locator("#header-actions"), "New Change", NONE_OPEN)
    poll_interval(host.stores["beta"], 20)
    expect(go).to_be_enabled(timeout=WAIT)
    expect(select).to_have_js_property("value", b)
    expect(page.locator("#blocked")).to_have_attribute("state", "warning")


@pytest.mark.browser
def test_an_unreadable_layer_is_named_with_its_reason_and_an_unset_interval_blocks_every_project(host, request) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page, base = host.page, host.base
    host.stores["alpha"].config_path.write_text("{")
    page.goto(f"{base}/#token=t")
    banner = page.locator("#blocked")
    expect(banner.locator("li")).to_have_text(["alpha: settings can't be read: state of config is unreadable"],
                                              timeout=WAIT)  # fmt: skip

    request.getfixturevalue("intervals_unset")  # this machine's update checks: every project waits
    expect(banner).to_have_attribute("state", "error", timeout=WAIT)
    expect(banner).to_have_attribute("heading", EVERY)
    expect(banner.locator("li")).to_have_count(2)
    expect(banner.locator("li").nth(1)).to_contain_text("beta: settings unset: machine.update_check_hours_")
    expect(page.get_by_role("button", name="New Change")).to_be_disabled()


@pytest.mark.browser
@pytest.mark.timeout(180)  # five settings changes, each seen at the machine's next 5 s poll
@pytest.mark.usefixtures("data")
def test_maintenance_holds_curation_and_a_test_review_only_where_work_may_not_start(host) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page, base, a = host.page, host.base, host.ids["alpha"]
    page.goto(f"{base}/#token=t")
    page.goto(f"{base}/maintenance?project={a}")
    rows, body = page.locator("#curation li"), page.locator("body")
    expect(rows.locator("h3")).to_have_text(["alpha", "beta"], timeout=WAIT)
    held_with(rows.nth(0), "Curate alpha now", UNSET)
    expect(rows.nth(0).locator("p-text.blocked")).to_have_text(f"S{UNSET[1:]}.")
    expect(rows.nth(1).get_by_role("button", name="Curate beta now")).to_be_enabled()
    expect(page.get_by_role("button", name="Curate all now")).to_be_enabled()
    held_with(page.locator("#tests"), "Review tests", UNSET)
    expect(page.locator("#tests-blocked")).to_have_text(f"S{UNSET[1:]}.")

    poll_interval(host.stores["beta"], None)  # every folder waits now: the open page follows the machine's poll
    held_with(body, "Curate all now", NO_FOLDER)
    held_with(rows.nth(1), "Curate beta now", UNSET)
    poll_interval(host.stores["beta"], 20)
    expect(page.get_by_role("button", name="Curate all now")).to_be_enabled(timeout=WAIT)
    poll_interval(host.stores["alpha"], 30)
    expect(page.get_by_role("button", name="Review tests")).to_be_enabled(timeout=WAIT)
    expect(page.locator("#tests-blocked")).to_have_count(0)


@pytest.mark.browser
@pytest.mark.timeout(180)  # five settings changes, each seen at the machine's next 5 s poll
@pytest.mark.usefixtures("github")
def test_the_backlog_holds_create_change_where_work_may_not_start_and_follows_the_poll(data, host, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page, base, b = host.page, host.base, host.ids["beta"]
    for title, kind, projects in (("Alpha only", "improvement", ["alpha"]), ("Every project", "idea", [])):
        backlog = Backlog(DataRepo(data), "alpha")
        backlog.update(backlog.add(title)[0].id, {"kind": kind, "projects": projects})
    page.goto(f"{base}/#token=t")
    page.goto(f"{base}/backlog?project={b}&show=all")
    selection, create = page.locator("#selection"), "Create Change from 1"
    expect(page.locator("li.entry")).to_have_count(2, timeout=WAIT)
    page.get_by_label("Select Alpha only").check()
    held_with(selection, create, UNSET)  # alpha's own entry: its clone may not start work
    page.get_by_label("Select Alpha only").uncheck()
    page.get_by_label("Select Every project").check()
    expect(page.get_by_role("button", name=create)).to_be_enabled()
    poll_interval(host.stores["beta"], None)  # no clone may start work now: no reload, the machine's poll shows it
    held_with(selection, create, NONE_OPEN)
    expect(page.get_by_label("Select Every project")).to_be_checked()
    poll_interval(host.stores["beta"], 20)
    expect(page.get_by_role("button", name=create)).to_be_enabled(timeout=WAIT)

    page.get_by_role("button", name=create).click()
    chooser = page.locator("#choose")
    select = pds.select(chooser, "Shape the Change in")
    expect(select.locator("p-select-option")).to_have_text(["beta"])  # alpha's clone is not offered
    expect(select).to_have_js_property("value", b)
    poll_interval(host.stores["beta"], None)
    held_with(chooser, "Continue", NONE_OPEN)
    poll_interval(host.stores["beta"], 20)
    expect(chooser.get_by_role("button", name="Continue")).to_be_enabled(timeout=WAIT)
    expect(select).to_have_js_property("value", b)
    expect(page.get_by_label("Select Every project")).to_be_checked()
