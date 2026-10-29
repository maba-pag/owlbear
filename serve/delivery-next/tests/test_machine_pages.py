"""The pages under the machine host (TD-242, TD-241): Changes of all projects or one, chosen in the top row."""

from __future__ import annotations

import re
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.models import Change, Step, StepKind
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from playwright.sync_api import Page


def clone(path: Path, slug: str = "") -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    store = Store.open(path)
    slug = slug or f"{path.name}-1"
    with store.lock(slug) as lock:
        store.write(lock, Change(slug=slug, step=Step(kind=StepKind.BUILD)))
    return path.resolve()


def serve() -> tuple[Machine, uvicorn.Server, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    now = datetime.now(UTC)
    machine = Machine(HostRecord(url=f"{base}/", token="t", pid=1, started_at=now, code=codebase.CURRENT))  # noqa: S106
    machine.load_all()
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return machine, server, base


@contextmanager
def browsing(monkeypatch, pds, width: int = 1280) -> Iterator[tuple[Page, str]]:
    """A Chromium page at *width* that reaches only a machine host serving the registered projects and the PDS CDN, and
    the host's address; the scheduler runs, no runner starts."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(viewport={"width": width, "height": 800})
            pds.only(page, base)
            yield page, base
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


def until(page: Page, done: Callable[[], object], seconds: float = 8) -> None:
    """Let *page* run, its routes included, until *done* holds; within *seconds*."""
    end = time.monotonic() + seconds
    while not done():
        assert time.monotonic() < end, "never happened"
        page.wait_for_timeout(100)


def replaced(path: Path) -> registry.Project:
    """A project whose clone at *path* was deleted and cloned again: the registered one, now replaced."""
    old = registry.register(clone(path))
    shutil.rmtree(path)
    clone(path)
    return old


@pytest.mark.browser
def test_changes_of_all_projects_or_one_the_top_row_switches_and_resumes_and_projects_adds_and_removes(  # noqa: PLR0915 - a journey
    tmp_path: Path, monkeypatch, pds
) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)  # the scheduler runs; no runner starts
    a, b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    third = clone(tmp_path / "gamma")
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/#token=t")
            expect(page.locator("#changes")).to_contain_text("alpha-1")  # All: every project's Changes
            expect(page.locator("#changes")).to_contain_text("beta-1")
            expect(page).to_have_url(f"{base}/")
            expect(page.locator("#changes .project")).to_have_text(["alpha", "beta"])
            head = page.locator("#changes .card .top").first  # a card's header is not styled as the top row
            assert head.evaluate("e => getComputedStyle(e).borderBottomStyle") == "none"
            expect(page.locator("#machine .paused")).to_contain_text("2 Changes would continue")
            expect(page.locator("#changes")).to_contain_text("Delivery is paused: continues after Resume")
            top = page.locator("#top")  # the project and Pause; the pause banner sits under it
            pds.pick(top, "Project", b.id)
            expect(page.locator("#changes")).to_contain_text("beta-1")
            expect(page.locator("#changes")).not_to_contain_text("alpha-1")
            expect(page.get_by_role("link", name="Backlog")).to_have_attribute("href", f"/backlog?project={b.id}")
            page.locator("#changes a.open").first.click()
            expect(page).to_have_url(f"{base}/?project={b.id}&change={b.id}%2Fbeta-1")
            page.reload()
            expect(pds.select(top, "Project")).to_have_js_property("value", b.id)
            page.get_by_role("button", name="Resume").click()
            expect(page.locator("#machine .paused")).to_have_count(0)
            assert (machine.paused, registry.load().resumed_at is not None) == (False, True)
            pause = page.get_by_role("button", name="Pause Delivery")
            tip = top.locator("p-button", has=pause)  # the tooltip is on the PDS button, around its inner button
            expect(tip).to_have_attribute("title", re.compile("may still update"))  # TD-288
            pause.click()
            expect(page.locator("#machine .paused")).to_contain_text("Delivery is paused: 2 Changes would continue")
            stop = page.get_by_role("button", name="Pause and stop when idle")
            expect(page.locator("#machine p-button", has=stop)).to_have_attribute("title", re.compile("stops"))
            stop.click()
            pds.answer(page, "Pause and stop")
            expect(page.locator("#machine .paused")).to_contain_text("OwlBear stops once nothing runs")
            assert (machine.paused, machine.ending) == (True, True)
            page.get_by_role("button", name="Resume").click()
            expect(page.locator("#machine .paused")).to_have_count(0)
            assert (machine.paused, machine.ending) == (False, False)
            page.get_by_role("button", name="Menu").click()  # Projects adds and removes (D-01M63C8DA1D95Z7M9ZYWVYYNF7)
            page.locator("p-drilldown").get_by_role("link", name="Projects").click()
            expect(page).to_have_url(f"{base}/projects?project={b.id}")
            page.get_by_label("Folder").fill(str(third))
            page.get_by_role("button", name="Add", exact=True).click()
            expect(page.locator("#page > [role=status]")).to_have_text("Added gamma.")
            added = next(p for p in registry.load().projects if p.path == str(third))
            expect(pds.select(top, "Project").locator(f'p-select-option[value="{added.id}"]')).to_have_text("gamma")
            pds.pick(top, "Project", added.id)
            expect(page).to_have_url(f"{base}/projects?project={added.id}")
            gamma = page.get_by_role("listitem", name="gamma")
            expect(gamma.locator("p-tag")).to_have_text("shown now")
            gamma.get_by_role("button", name="Remove project").click()
            expect(pds.modal(page)).to_contain_text("nothing is deleted")
            pds.answer(page, "Remove project")
            expect(page).to_have_url(f"{base}/projects")  # back to All
            assert [p.id for p in registry.load().projects] == [a.id, b.id]
            expect(page.locator("#projects > li")).to_have_count(2)
            page.locator("#top").get_by_role("link", name="Backlog").click()
            expect(page).to_have_url(f"{base}/backlog")  # the backlog too shows all projects (TD-241)
            page.get_by_role("button", name="Menu").click()
            page.locator("p-drilldown").get_by_role("link", name="Settings").click()
            expect(page).to_have_url(f"{base}/config?project={a.id}")  # a project page opens the first project
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_two_projects_with_one_slug_stay_apart_in_list_detail_actions_and_links(
    tmp_path: Path, monkeypatch, pds
) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)
    a, b = (registry.register(clone(tmp_path / n, "same")) for n in ("alpha", "beta"))
    machine, server, base = serve()
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/#token=t")
            cards = page.locator("#changes li.card")
            expect(cards).to_have_count(2)
            cards.filter(has_text="beta").locator("a.open").click()
            expect(page).to_have_url(f"{base}/?change={b.id}%2Fsame")
            expect(page.locator("#detail")).to_contain_text("in beta")
            page.reload()
            expect(page.locator("#detail")).to_contain_text("in beta")
            page.locator("#detail").get_by_role("button", name="Pause").click()
            expect(page.locator("#started")).to_contain_text("Pause requested")
            paused = {Path(p.path).name: Store.open(Path(p.path)).read("same").intent.paused_at for p in (a, b)}
            assert (paused["alpha"], paused["beta"] is not None) == (None, True)  # only beta's Change
            page.go_back()
            expect(page).to_have_url(f"{base}/")
            page.get_by_role("button", name="New Change").click()
            chooser = pds.select(page.locator("#choose"), "Shape the new Change in")
            expect(chooser).to_have_js_property("value", a.id)
            page.get_by_role("button", name="Cancel").click()
            expect(page.locator("#choose")).to_have_count(0)
            page.get_by_role("button", name="New Change").click()
            pds.pick(page.locator("#choose"), "Shape the new Change in", b.id)
            page.get_by_role("button", name="Continue").click()
            pds.answer(page, "Not now")
            expect(page.locator("#choose")).to_have_count(0)  # declined: nothing is left to click
            _alpha_does_not_answer(page, base, a.id, expect)
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


def _alpha_does_not_answer(page, base: str, alpha: str, expect) -> None:
    changes = f"**/p/{alpha}/api/next/changes"
    page.route(changes, lambda r: r.fulfill(status=503, json={"detail": "stopping"}))
    expect(page.locator("#notes")).to_contain_text("alpha: not read just now (stopping)")
    expect(page.locator("#changes li.card")).to_have_count(2)  # its Changes stay as last read; beta's go on
    page.goto(f"{base}/?change={alpha}%2Fsame")  # a link into the project that does not answer just now
    expect(page.locator("#notes")).to_contain_text("alpha: not read just now")
    page.unroute(changes)
    expect(page.locator("#detail")).to_contain_text("in alpha")  # kept, and opened once it answers
    assert page.evaluate("location.search") == f"?change={alpha}%2Fsame"
    page.route(changes, lambda _r: None)  # up, yet never answers
    expect(page.locator("#error")).to_contain_text("slow to answer", timeout=30000)
    expect(page.locator("#detail")).to_have_class("stale")  # not shown as freshly read


@pytest.mark.browser
def test_a_paused_page_runs_updates_now_shows_the_update_and_says_once_which_version_runs(pds) -> None:
    """TD-288, TD-352, TD-299: Run updates now on the paused bar; the version taken is said once."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    machine, server, base = serve()
    machine.updated = "v0.2"
    asked: list[bool] = []

    def run_now() -> dict:
        asked.append(True)
        machine.updater.state |= {"phase": "waiting", "detail": "waits for p: c1: a running step", "version": "v0.3"}
        return machine.updater.read()

    machine.updater.run_now = run_now
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/#token=t")
            expect(page.locator("#update-done")).to_contain_text("OwlBear now runs v0.2")
            page.locator("#update-done").get_by_role("button", name="OK").click()
            expect(page.locator("#update-done")).to_have_count(0)
            page.get_by_role("button", name="Run updates now").click()
            pds.answer(page, "Run updates now")
            expect(page.locator("#update-state")).to_contain_text(
                "Update to v0.3: waiting · waits for p: c1: a running step"
            )
            assert asked == [True]
            page.reload()
            expect(page.locator("#update-state")).to_be_visible()
            expect(page.locator("#update-done")).to_have_count(0)  # told once
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_an_announced_update_counts_down_on_every_page_and_postpone_cancels_it(pds) -> None:
    """TD-301: open pages announce it 2 minutes ahead with Postpone; Postpone is use."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    machine, server, base = serve()
    machine.auto.target, machine.auto.deadline = "v0.3", machine.auto.mono() + 105
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/#token=t")
            expect(page.locator("#update-announce")).to_contain_text("OwlBear updates to v0.3 in 1:4")
            page.locator("#update-announce").get_by_role("button", name="Postpone").click()
            expect(page.locator("#update-announce")).to_have_count(0)
            assert machine.auto.deadline is None
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


PACK = {
    "install": {"state": "missing", "version": "v0.2", "pack": "impeccable-4.8.0.1", "detail": "", "at": None},
    "release": {"state": "newer", "version": "v0.3", "pack": "impeccable-4.9.0.1", "running_pack": "impeccable-4.8.0.1",
                "checked_at": "2026-10-17T04:00:00+00:00", "detail": ""},
}  # fmt: skip


@pytest.mark.browser
def test_every_page_shows_the_impeccable_banners_and_install_says_refused_running_and_done(pds) -> None:
    """D-01M61GW2EAHFFRFHF014A14K98: Install while this version's pack is missing; Update now for a newer one."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    machine, server, base = serve()
    state = {"install": dict(PACK["install"]), "release": dict(PACK["release"])}
    answers = iter([{"refused": "an update runs; it installs the pack of the version it takes"}, {}])

    def install() -> dict:
        said = next(answers)
        if not said:
            state["install"] = state["install"] | {"state": "installing"}
        return dict(state) | said

    machine.impeccable.read, machine.impeccable.install = (lambda: dict(state)), install
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/#token=t")
            missing, newer = page.locator("#pack-install-banner"), page.locator("#pack-release-banner")
            expect(missing).to_contain_text("Impeccable (impeccable-4.8.0.1) that this OwlBear version, v0.2, pins "
                                            "is not installed on this machine")  # fmt: skip
            expect(newer).to_contain_text("OwlBear v0.3 carries a newer Impeccable (impeccable-4.9.0.1); this version "
                                          "pins Impeccable (impeccable-4.8.0.1). Checked ")  # fmt: skip
            page.set_viewport_size({"width": 375, "height": 800})
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
            missing.get_by_role("button", name="Install").click()
            expect(page.locator("#pack-install-said")).to_have_text(
                "Not installed now: an update runs; it installs the pack of the version it takes."
            )
            missing.get_by_role("button", name="Install").click()
            expect(missing).to_contain_text("Installing Impeccable (impeccable-4.8.0.1) for OwlBear v0.2…")
            state["install"] = None
            expect(page.locator("#pack-install-said")).to_have_text(
                "Impeccable is installed on this machine.", timeout=12000
            )  # the poll saw it end
            expect(missing).to_have_count(0)
            state["release"] = state["release"] | {"checked_at": None}
            page.goto(f"{base}/memory#token=t")  # every page
            expect(newer).to_contain_text("When it was checked is unknown.")
            newer.get_by_role("button", name="Update now").click()
            expect(pds.modal(page)).to_contain_text("Run updates now?")
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_maintenance_with_no_project_shows_the_machines_update_read_only_with_its_project_named(
    tmp_path: Path, monkeypatch, pds
) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.impeccable_runs import pack_job, pack_rounds  # noqa: PLC0415

    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)
    path = clone(tmp_path / "alpha")
    registry.register(path)
    job = pack_job.Job(Store.open(path), pack_job.Live())
    question = pack_rounds.question("r1:end:1", "end", "The rounds ended.", ["activate", "discard"])
    job.state = pack_job._blank() | {  # noqa: SLF001 - a run waiting for the owner
        "state": "waiting", "started_at": datetime.now(UTC).isoformat(), "run": "r1", "questions": [question],
    }  # fmt: skip
    job._save()  # noqa: SLF001
    machine, server, base = serve()
    failed = {"state": "failed", "version": "v0.3", "pack": "", "detail": "cannot download", "at": None}
    machine.impeccable.read = lambda: {"install": failed, "release": None}  # a newer version's pack
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/maintenance#token=t")
            assert "project=" not in page.url  # no project picked for the owner
            expect(page.locator("#pack-project")).to_contain_text("Started in alpha")
            expect(page.locator("#pack-project")).to_contain_text("choose a project above to act on it")
            expect(page.locator("#pack-questions .pack-question")).to_have_count(1)  # shown,
            expect(page.locator("#owlbear p-button", has_text="Activate")).to_have_count(0)  # but not answerable
            expect(page.locator("#pack-discard")).to_have_count(0)
            expect(page.get_by_role("button", name="Update Impeccable")).to_be_disabled()
            expect(page.locator("#owlbear")).to_contain_text("Choose a project above to start one")
            expect(page.locator("#pack-install-state")).to_have_text(
                "Impeccable of OwlBear v0.3 failed to install on this machine: cannot download."
            )
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


def targets(scope) -> list[str]:
    """WCAG 2.5.8: each shown control in *scope* still smaller than 24 by 24 pixels once the design system has laid it
    out (under load that takes a moment), by its text."""
    small = []
    for _ in range(20):
        small = scope.evaluate_all(
            "els => els.filter(e => e.checkVisibility()).filter(e => { const r = e.getBoundingClientRect();"
            " return r.width < 24 || r.height < 24 })"
            ".map(e => e.textContent.trim() || e.outerHTML.slice(0, 60))"
        )
        if not small:
            break
        scope.page.wait_for_timeout(250)
    return list(small)


@pytest.mark.browser
def test_the_menu_reaches_every_page_moves_focus_into_each_level_and_back_to_the_burger(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """D-01M63C8375KV9WA6NH8K2MB8PN: the burger's drilldown holds every page; the top row holds the work pages but on
    a phone; focus moves into each level, and Escape returns it to the burger. Old links keep working."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a, b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={a.id}#token=t")
        burger, menu = page.get_by_role("button", name="Menu"), page.locator("p-drilldown")
        work = ["Changes", "Backlog", "Memory", "Decisions", "Metrics"]
        expect(page.locator("#top nav a")).to_have_text(work)
        expect(burger).to_have_attribute("aria-haspopup", "dialog")
        assert targets(page.locator("#top nav a, #top .brand, #menu > p-button-pure, #controls > *")) == []
        burger.click()
        expect(menu.get_by_role("link", name="Settings")).to_be_focused()  # this page's link, in its level
        expect(menu.get_by_role("link", name="Settings")).to_have_attribute("aria-current", "page")
        served = ["/", "/backlog", "/memory", "/decisions", "/metrics", "/projects", "/config", "/maintenance"]
        hrefs = menu.locator("a").evaluate_all("as => as.map(a => a.getAttribute('href'))")
        assert sorted(hrefs) == sorted(f"{path}?project={a.id}" for path in served)
        menu.get_by_role("button", name="Work").click()
        expect(menu.get_by_role("link", name="Changes")).to_be_focused()  # into the level it opened
        assert targets(menu.get_by_role("link")) == []
        page.keyboard.press("Escape")
        expect(menu.get_by_role("link")).to_have_count(0)
        expect(burger).to_be_focused()
        burger.click()
        menu.get_by_role("link", name="Maintenance").click()
        expect(page).to_have_url(f"{base}/maintenance?project={a.id}")

        page.set_viewport_size({"width": 390, "height": 800})  # a phone: the work pages are in the menu only
        page.goto(f"{base}/?project={b.id}&change={b.id}%2Fbeta-1")  # an old link into one Change
        expect(page.locator("#detail")).to_contain_text("beta-1")
        expect(page.locator("#top nav")).to_be_hidden()
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        burger.click()
        expect(menu.get_by_role("link", name="Changes")).to_be_focused()  # opened at the work level
        expect(menu.get_by_role("link", name="Projects")).to_be_hidden()
        menu.get_by_role("button", name="Back").click()
        expect(menu.locator("p-drilldown-item").get_by_role("button", name="Work")).to_be_focused()
        expect(menu.get_by_role("link", name="Projects")).to_be_visible()
        page.keyboard.press("Escape")
        expect(burger).to_be_focused()
        burger.click()  # it opens at the work level again
        menu.get_by_role("link", name="Backlog").click()
        expect(page).to_have_url(f"{base}/backlog?project={b.id}")
        page.goto(f"{base}/config")  # an old link without a project opens the first one, as before
        expect(page).to_have_url(f"{base}/config?project={a.id}")


@pytest.mark.browser
def test_projects_shows_each_clone_s_state_and_setup_and_adopting_the_shown_one_shows_the_adopted_one(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """D-01M63C8DA1D95Z7M9ZYWVYYNF7: Projects holds the setup notes; a replaced clone shows beside a loaded one, and
    another page says where to fix it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    old = replaced(tmp_path / "delta")
    with browsing(monkeypatch, pds, width=390) as (page, base):
        page.goto(f"{base}/?project={old.id}#token=t")  # another page says what is wrong and where to fix it
        trouble = page.locator("#machine > [role=status]").first
        expect(trouble).to_contain_text("delta is replaced: the clone at")
        trouble.get_by_role("link", name="Open Projects").click()
        expect(page).to_have_url(f"{base}/projects?project={old.id}")
        alpha, delta = page.get_by_role("listitem", name="alpha"), page.get_by_role("listitem", name="delta")
        expect(alpha.locator("p-tag")).to_have_count(0)  # loaded
        expect(alpha.locator("p-inline-notification")).to_contain_text(f"owlbear setup --repo {a.path}")
        expect(delta.locator("p-tag")).to_have_text(["replaced", "shown now"])
        expect(delta).to_contain_text("is not the one registered; Remove or Adopt it")
        expect(alpha.get_by_role("button", name="Adopt the new clone")).to_have_count(0)
        assert targets(page.locator("#page p-button, #page p-input-text input")) == []
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        delta.get_by_role("button", name="Adopt the new clone").click()
        expect(page).not_to_have_url(f"{base}/projects?project={old.id}")
        adopted = next(p for p in registry.load().projects if p.path == old.path and p.id != old.id)
        expect(page).to_have_url(f"{base}/projects?project={adopted.id}")
        expect(page.get_by_role("listitem", name="delta").locator("p-tag")).to_have_text("shown now")


@pytest.mark.browser
def test_projects_adopts_removes_and_adds_keeping_focus_and_the_next_folder(tmp_path: Path, monkeypatch, pds) -> None:
    """D-01M63C8DA1D95Z7M9ZYWVYYNF7: with no project shown each action stays on Projects, and focus stays on it; one
    action runs at a time; with no project left, the top row offers Add project."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    replaced(tmp_path / "delta")
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/projects#token=t")  # all projects: none is shown
        page.get_by_role("listitem", name="delta").get_by_role("button", name="Adopt the new clone").click()
        expect(page.locator("#page > [role=status]")).to_contain_text("delta now serves the clone at")
        delta = page.get_by_role("listitem", name="delta")
        expect(delta.get_by_role("button", name="Remove project")).to_be_focused()  # its Adopt went with it
        assert "project=" not in page.url
        delta.get_by_role("button", name="Remove project").click()
        pds.answer(page, "Remove project")
        alpha = page.get_by_role("listitem", name="alpha")
        expect(alpha.get_by_role("button", name="Remove project")).to_be_focused()  # delta's went with it
        alpha.get_by_role("button", name="Remove project").click()
        pds.answer(page, "Remove project")
        expect(page.get_by_label("Folder")).to_be_focused()
        expect(page.locator("#page")).to_contain_text("No project yet")
        assert registry.load().projects == []
        add = page.locator("#top").get_by_role("link", name="Add project")
        expect(add).to_have_attribute("href", "#add")  # Projects is where it leads, so it goes to the form
        page.get_by_role("button", name="Add", exact=True).click()
        expect(page.locator("#page > [role=alert]")).to_have_text("Name the folder of a clone first.")
        posted = []
        page.route(
            f"{base}/api/next/projects", lambda r: posted.append(r) if r.request.method == "POST" else r.fallback()
        )
        page.get_by_label("Folder").fill(a.path)
        page.locator("#add p-input-text").evaluate(  # Enter twice before Delivery answers adds it once
            "e => { for (const _ of [1, 2]) e.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter'})) }"
        )
        until(page, lambda: posted)
        page.get_by_label("Folder").fill("~/Projects/next")  # typed while Delivery adds the first
        posted[0].fallback()
        expect(page.locator("#page > [role=status]")).to_have_text("Added alpha.")
        expect(page.locator("#page > [role=alert]")).to_have_count(0)
        expect(page.get_by_label("Folder")).to_have_value("~/Projects/next")
        assert len(posted) == 1
        expect(add).to_have_count(0)
        expect(pds.select(page.locator("#top"), "Project")).to_be_visible()
        page.goto(f"{base}/backlog")
        expect(page.locator("#top").get_by_role("link", name="Add project")).to_have_count(0)


@pytest.mark.browser
def test_projects_says_when_the_machine_does_not_answer_and_that_the_list_may_be_out_of_date(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """A failed read of the machine's projects is said as such, never as a project's own host; after an action whose
    reread failed, the list shown says it may be out of date until a read succeeds again."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    registry.register(clone(tmp_path / "beta"))

    def refused(route) -> None:
        if route.request.method == "GET":
            route.fulfill(status=503, json={"detail": "busy"})
        else:
            route.fallback()

    with browsing(monkeypatch, pds) as (page, base):
        listing = f"{base}/api/next/projects"
        page.route(listing, refused)
        page.goto(f"{base}/projects#token=t")
        expect(page.locator("#page p-inline-notification")).to_contain_text("busy")
        expect(page.locator("#page")).not_to_contain_text("one project's own host")
        page.unroute(listing)
        page.get_by_role("button", name="Reload").click()
        expect(page.get_by_role("listitem")).to_have_count(2)
        page.route(  # Remove reaches the machine; reading its projects again finds no host at all
            listing, lambda r: r.abort() if r.request.method == "GET" else r.fallback()
        )
        page.get_by_role("listitem", name="beta").get_by_role("button", name="Remove project").click()
        pds.answer(page, "Remove project")
        expect(page.locator("#page > [role=status]")).to_contain_text("Removed beta")
        expect(page.locator("#page > [role=alert]")).to_have_text(
            "This list may be out of date: Delivery is not running. Start it, then reload this page."
        )
        expect(page.get_by_role("listitem")).to_have_count(2)  # the last list read, kept
        assert registry.load().projects == [a]
        page.unroute(listing)  # the next poll reads it again
        expect(page.locator("#page > [role=alert]")).to_have_count(0, timeout=8000)
        expect(page.get_by_role("listitem")).to_have_count(1)


@pytest.mark.browser
def test_an_older_read_of_the_machine_never_replaces_a_newer_one(tmp_path: Path, monkeypatch, pds) -> None:
    """A poll that started before Remove and is answered after Remove's reread leaves the list Remove left."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    registry.register(clone(tmp_path / "alpha"))
    registry.register(clone(tmp_path / "beta"))
    held = []

    def hold_one_read(route) -> None:  # the next poll's read, answered later with the list as it is now
        if route.request.method == "GET" and not held:
            held.append((route, route.fetch()))
        else:
            route.fallback()

    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/projects#token=t")
        expect(page.get_by_role("listitem")).to_have_count(2)
        page.route(f"{base}/api/next/projects", hold_one_read)
        page.get_by_role("listitem", name="beta").get_by_role("button", name="Remove project").click()
        until(page, lambda: held)  # a poll is under way while Remove is asked
        pds.answer(page, "Remove project")
        expect(page.locator("#page > [role=status]")).to_contain_text("Removed beta")
        expect(page.get_by_role("listitem")).to_have_count(1)
        page.evaluate("() => { window.polled = new Promise(r => document.addEventListener('owlbear-polled', r)); }")
        route, answer = held[0]
        route.fulfill(response=answer)  # within the read's 5 s: the list before Remove
        page.evaluate("window.polled")
        assert page.get_by_role("listitem").count() == 1, page.locator("#page").inner_text()
        assert page.locator("#page > [role=alert]").count() == 0


@pytest.mark.browser
def test_a_newer_read_that_fails_keeps_what_an_older_one_read_in_the_meantime(tmp_path: Path, monkeypatch, pds) -> None:
    """A read that starts while Remove's reread is under way and fails after it leaves the list Remove left, marked as
    possibly out of date: the failure says nothing about what the older read found."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    registry.register(clone(tmp_path / "alpha"))
    registry.register(clone(tmp_path / "beta"))
    held = []

    def hold(route) -> None:
        if route.request.method == "GET":
            held.append(route)
        else:
            route.fallback()

    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/projects#token=t")
        expect(page.get_by_role("listitem")).to_have_count(2)
        page.get_by_role("listitem", name="beta").get_by_role("button", name="Remove project").click()
        page.route(f"{base}/api/next/projects", hold)
        pds.answer(page, "Remove project")
        until(page, lambda: held)  # Remove's reread
        older = len(held)
        page.evaluate("() => { import('/assets/ui.mjs').then((ui) => ui.reread()); }")  # the page's own module
        until(page, lambda: len(held) > older)
        for route in held[:-1]:
            route.fulfill(response=route.fetch())  # the list without beta
        held[-1].abort()
        expect(page.locator("#page > [role=alert]")).to_have_text(
            "This list may be out of date: Delivery is not running. Start it, then reload this page."
        )
        assert page.get_by_role("listitem").count() == 1, page.locator("#page").inner_text()


@pytest.mark.browser
def test_focus_goes_to_the_same_place_after_remove_and_stays_where_the_owner_moved_it(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """Removing the last project focuses the Remove before it; Adopt leaves focus where the owner put it meanwhile."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    replaced(tmp_path / "epsilon")
    for name in ("alpha", "beta", "gamma"):
        registry.register(clone(tmp_path / name))
    held = []

    def hold(route) -> None:  # Adopt, answered once the owner has moved on
        held.append(route)

    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/projects#token=t")
        items = page.get_by_role("listitem")
        expect(items).to_have_count(4)
        assert items.last.get_attribute("aria-labelledby") == f"p-{registry.load().projects[-1].id}"
        last = page.get_by_role("listitem", name="gamma")
        last.get_by_role("button", name="Remove project").click()
        pds.answer(page, "Remove project")
        expect(page.get_by_role("listitem", name="beta").get_by_role("button", name="Remove project")).to_be_focused()
        page.route(f"{base}/api/next/projects/*/adopt", hold)
        page.get_by_role("listitem", name="epsilon").get_by_role("button", name="Adopt the new clone").click()
        until(page, lambda: held)
        page.get_by_label("Folder").focus()  # the owner moves on while Delivery adopts it
        held[0].fallback()
        expect(page.locator("#page > [role=status]")).to_contain_text("epsilon now serves the clone at")
        expect(page.get_by_label("Folder")).to_be_focused()


@pytest.mark.browser
def test_a_focused_remove_stays_with_its_project_when_the_list_changes_under_it(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """When the focused Remove's project goes away elsewhere, the next project's Remove does not take its place."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    alpha = registry.register(clone(tmp_path / "alpha"))
    registry.register(clone(tmp_path / "beta"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/projects#token=t")
        page.get_by_role("listitem", name="alpha").get_by_role("button", name="Remove project").focus()
        gone = page.request.delete(f"{base}/api/next/projects/{alpha.id}", headers={"Authorization": "Bearer t"})
        assert gone.ok, gone.text()  # another tab removes it
        page.evaluate("() => { import('/assets/ui.mjs').then((ui) => ui.reread()); }")
        expect(page.get_by_role("listitem")).to_have_count(1)
        expect(
            page.get_by_role("listitem", name="beta").get_by_role("button", name="Remove project")
        ).not_to_be_focused()
