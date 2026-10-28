"""The pages under the machine host (TD-242, TD-241): Changes of all projects or one, chosen by the bar."""

from __future__ import annotations

import re
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.models import Change, Step, StepKind
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import Store


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


@pytest.mark.browser
def test_changes_of_all_projects_or_one_and_the_bar_switches_adds_removes_and_resumes(  # noqa: PLR0915 - a journey
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
            expect(page.locator("#machine .paused")).to_contain_text("2 Changes would continue")
            expect(page.locator("#changes")).to_contain_text("Delivery is paused: continues after Resume")
            bar = page.locator("#machine")
            pds.pick(bar, "Project", b.id)
            expect(page.locator("#changes")).to_contain_text("beta-1")
            expect(page.locator("#changes")).not_to_contain_text("alpha-1")
            expect(page.get_by_role("link", name="Backlog")).to_have_attribute("href", f"/backlog?project={b.id}")
            page.locator("#changes a.open").first.click()
            expect(page).to_have_url(f"{base}/?project={b.id}&change={b.id}%2Fbeta-1")
            page.reload()
            expect(pds.select(bar, "Project")).to_have_js_property("value", b.id)
            page.get_by_role("button", name="Resume").click()
            expect(page.locator("#machine .paused")).to_have_count(0)
            assert (machine.paused, registry.load().resumed_at is not None) == (False, True)
            pause = page.get_by_role("button", name="Pause Delivery")
            tip = bar.locator("p-button", has=pause)  # the tooltip is on the PDS button, around its inner button
            expect(tip).to_have_attribute("title", re.compile("may still update"))  # TD-288
            pause.click()
            expect(page.locator("#machine .paused")).to_contain_text("Delivery is paused: 2 Changes would continue")
            stop = page.get_by_role("button", name="Pause and stop when idle")
            expect(bar.locator("p-button", has=stop)).to_have_attribute("title", re.compile("stops"))
            stop.click()
            pds.answer(page, "Pause and stop")
            expect(page.locator("#machine .paused")).to_contain_text("OwlBear stops once nothing runs")
            assert (machine.paused, machine.ending) == (True, True)
            page.get_by_role("button", name="Resume").click()
            expect(page.locator("#machine .paused")).to_have_count(0)
            assert (machine.paused, machine.ending) == (False, False)
            page.locator("#machine summary").click()
            page.get_by_label("Folder").fill(str(third))
            page.get_by_role("button", name="Add", exact=True).click()
            expect(page.locator("#changes")).to_contain_text("gamma-1")
            added = next(p for p in registry.load().projects if p.path == str(third))
            expect(page).to_have_url(f"{base}/?project={added.id}")
            page.get_by_role("button", name="Remove project").click()
            pds.answer(page, "Remove project")
            expect(page).to_have_url(f"{base}/")  # back to All
            assert [p.id for p in registry.load().projects] == [a.id, b.id]
            page.get_by_role("link", name="Backlog").click()
            expect(page).to_have_url(f"{base}/backlog")  # the backlog too shows all projects (TD-241)
            page.get_by_role("link", name="Settings").click()
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
def test_every_page_shows_the_design_pack_banners_and_install_says_refused_running_and_done(pds) -> None:
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

    machine.packs.read, machine.packs.install = (lambda: dict(state)), install
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
            expect(missing).to_contain_text("The design pack impeccable-4.8.0.1 that this OwlBear version, v0.2, pins "
                                            "is not installed on this machine")  # fmt: skip
            expect(newer).to_contain_text("OwlBear v0.3 carries a newer design pack impeccable-4.9.0.1; this version "
                                          "pins design pack impeccable-4.8.0.1. Checked ")  # fmt: skip
            page.set_viewport_size({"width": 375, "height": 800})
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
            missing.get_by_role("button", name="Install").click()
            expect(page.locator("#pack-install-said")).to_have_text(
                "Not installed now: an update runs; it installs the pack of the version it takes."
            )
            missing.get_by_role("button", name="Install").click()
            expect(missing).to_contain_text("Installing the design pack impeccable-4.8.0.1 for OwlBear v0.2…")
            state["install"] = None
            expect(page.locator("#pack-install-said")).to_have_text(
                "The design pack is installed on this machine.", timeout=12000
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

    from owlbear_delivery_next.pack_runs import pack_job, pack_rounds  # noqa: PLC0415

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
            expect(page.get_by_role("button", name="Update design pack")).to_be_disabled()
            expect(page.locator("#owlbear")).to_contain_text("Choose a project above to start one")
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()
