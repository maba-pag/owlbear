"""The pages under the machine host (TD-242, TD-241): Changes of all projects or one, chosen in the top row."""

from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import uvicorn
from copilot.generated import rpc

from owlbear_delivery_next.change_contracts.models import Brief, Change, Step, StepKind
from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import codebase, data_repo, local_home
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, Store

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
    # longer than the pages' polls: route.fetch() reuses a pooled socket, which uvicorn's 5 s default closes
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning", timeout_keep_alive=60))
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
            page.locator("p-drilldown").get_by_role("button", name="Settings").click()
            page.locator("p-drilldown").get_by_role("link", name="Overview").click()
            expect(page).to_have_url(f"{base}/config?project={a.id}#overview")  # a project page opens the first project
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


class Chats:
    """The shaping chat's launcher in every project: each call's folder and prompt, held until released."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []
        self.release, self.ending = threading.Event(), {"state": "open"}

    def __call__(self, repo: Path, _role: object, prompt: str) -> dict[str, str]:
        self.calls.append((repo, prompt))
        assert self.release.wait(30)
        return self.ending


def chats(monkeypatch) -> Chats:
    """Every project host the machine host starts opens its chats on one recorder, with no gap between launches."""
    chats = Chats()
    monkeypatch.setattr(api, "LAUNCH_GAP", 0)
    monkeypatch.setattr(api, "create_app", partial(api.create_app, launch=chats, which=lambda _n: "/bin/code"))
    return chats


def shaping(path: Path, title: str, slug: str = "same", **update: object) -> None:
    """Write *slug*, handle c1, shaping brief v1 called *title*; *update* changes the Change."""
    store = Store.open(path)
    brief = Brief(version=1, title=title, outcome=f"{title}: what the Change gives.")
    with store.lock(slug) as lock:
        c = Change(slug=slug, handle="c1", brief=brief, step=Step(kind=StepKind.SHAPE))
        store.write(lock, c.model_copy(update=update))


def opened(page: Page, base: str, of: str, slug: str = "same") -> None:
    page.goto(f"{base}/#token=t")
    page.goto(f"{base}/?change={of}%2F{slug}")


REVISE = "Revise the brief in a new chat"
# A native modal dialog: past either end focus leaves for the browser's own controls (body), never the page behind.
INSIDE = """() => document.activeElement === document.body
    || [...document.querySelectorAll('p-modal')].some((m) => m.open && m.contains(document.activeElement))"""


@pytest.mark.browser
@pytest.mark.timeout(90)  # a real browser's journey through three launches; a loaded runner needs more than 30 s
def test_the_brief_offers_a_new_shaping_chat_and_says_how_it_went(tmp_path: Path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    launched = chats(monkeypatch)
    alpha = registry.register(clone(tmp_path / "alpha", "same"))
    shaping(Path(alpha.path), "Alpha brief")
    with browsing(monkeypatch, pds) as (page, base):
        opened(page, base, alpha.id)
        revise = page.locator("#detail").get_by_role("button", name=REVISE)
        expect(revise).to_be_visible()
        pds.settled(page)
        box = revise.bounding_box()
        assert box and box["width"] >= 24 and box["height"] >= 24  # noqa: PT018 - one target size
        revise.click()
        expect(pds.modal(page)).to_contain_text("Revise brief v1 in a new chat?")
        pds.settled(page)
        for key in ["Shift+Tab"] * 3 + ["Tab"] * 3:  # the dialog keeps focus at both ends
            page.keyboard.press(key)
            assert page.evaluate(INSIDE), key
        pds.answer(page, "Not now")
        assert REVISE in page.evaluate("document.activeElement?.textContent ?? ''")  # focus back on the button
        assert launched.calls == []
        revise.click()
        pds.answer(page, "Open the chat")
        expect(page.locator("#started")).to_have_text("Opening the shaping chat…")
        expect(page.locator("#detail p-button", has_text=REVISE)).to_have_js_property("loading", value=True)
        until(page, lambda: launched.calls)
        launched.release.set()
        expect(page.locator("#started")).to_have_text("A chat opened in VS Code to revise c1.")

        approved = Brief(version=1, approved_version=1, title="Alpha brief", outcome="Alpha brief: back to shaping.")
        shaping(Path(alpha.path), "Alpha brief", brief=approved)  # approved, then sent back to its brief
        launched.ending = {"state": "failed", "reason": "the Copilot chat did not start (unbound: x)"}
        again = page.locator("#detail section.info").get_by_role("button", name=REVISE)
        expect(again).to_be_visible(timeout=15000)
        again.click()
        pds.answer(page, "Open the chat")
        expect(page.locator("#started")).to_contain_text(
            "Could not open the chat to revise c1: the Copilot chat did not"
        )
        expect(page.locator("#started code")).to_contain_text("code chat -m")

        unset = {k: v for k, v in config.BASE.agents.items() if k != "shaper"}
        monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"agents": unset}))
        # the project's work now waits for its settings (#808): the button is held and says why
        expect(again).to_be_disabled(timeout=15000)
        expect(page.locator("#detail section.info p-button", has_text=REVISE)).to_have_attribute(
            "title", re.compile("shaper")
        )
        assert len(launched.calls) == 2


@pytest.mark.browser
def test_a_brief_that_cannot_take_a_revision_shows_no_button(tmp_path: Path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    alpha = registry.register(clone(tmp_path / "alpha", "planned"))
    approved = Brief(version=1, approved_version=1, title="Planned brief", outcome="Planned: approved and planned.")
    shaping(Path(alpha.path), "Planned brief", "planned", brief=approved, step=Step(kind=StepKind.PLAN))
    shaping(Path(alpha.path), "Challenged brief", "challenged", step=Step(kind=StepKind.SHAPE, mode="challenge"))
    with browsing(monkeypatch, pds) as (page, base):
        for slug, title in [("planned", "Planned brief"), ("challenged", "Challenged brief")]:
            opened(page, base, alpha.id, slug)
            expect(page.locator("#detail")).to_contain_text(title)
            pds.settled(page)
            expect(page.locator("#detail").get_by_role("button", name=REVISE)).to_have_count(0)


@pytest.mark.browser
def test_two_projects_whose_changes_share_a_handle_revise_the_one_clicked(tmp_path: Path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    launched = chats(monkeypatch)
    a, b = (registry.register(clone(tmp_path / n, "same")) for n in ("alpha", "beta"))
    for p, title in [(a, "Alpha brief"), (b, "Beta brief")]:
        shaping(Path(p.path), title)
    with browsing(monkeypatch, pds) as (page, base):
        opened(page, base, b.id)
        expect(page.locator("#detail")).to_contain_text("in beta")
        page.get_by_role("button", name="New Change").click()  # its project chooser is left open
        expect(page.locator("#choose")).to_have_count(1)
        page.locator("#detail").get_by_role("button", name=REVISE).click()
        pds.answer(page, "Open the chat")
        expect(page.locator("#choose")).to_have_count(0)
        until(page, lambda: launched.calls)
        page.locator(f'#changes a[data-key="{a.id}/same"]').click()  # another c1 chosen while beta's chat opens
        expect(page.locator("#detail")).to_contain_text("in alpha")
        launched.release.set()
        expect(page.locator("#started")).to_have_text("A chat opened in VS Code to revise c1 in beta.")
        [(repo, prompt)] = launched.calls
        said = prompt.split(" in this project")[0]
        assert (Path(repo), said) == (Path(b.path), 'Continue Delivery Change c1 ("Beta brief")')
        page.goto(f"{base}/")
        page.get_by_role("button", name="New Change").click()
        expect(pds.select(page.locator("#choose"), "Shape the new Change in")).to_have_js_property("value", a.id)
        page.get_by_role("button", name="Continue").click()
        pds.answer(page, "Open the chat")
        expect(page.locator("#started")).to_have_text("A chat opened in VS Code to shape the new Change.")
        assert [(Path(r), p.startswith(api.START_PROMPT)) for r, p in launched.calls[1:]] == [(Path(a.path), True)]


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
            expect(newer.get_by_role("link")).to_have_text("Updates → OwlBear")  # the pages' one separator
            newer.get_by_role("button", name="Update now").click()
            expect(pds.modal(page)).to_contain_text("Run updates now?")
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
def test_updates_impeccable_with_no_project_answers_a_loaded_projects_run_with_its_project_named(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """D-01M63C5VGFVT3DVCC888B78K2A: the page is the same in every project; on the machine host a run whose project is
    loaded is answered from All projects too, while starting one still needs a project."""
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
    unread = {"state": "unknown", "version": "", "pack": "", "running_pack": "impeccable-4.8.0.1", "checked_at": None,
              "detail": "GitHub did not answer"}  # fmt: skip
    machine.impeccable.read = lambda: {"install": failed, "release": unread}  # a newer version's pack
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/updates/impeccable#token=t")
            assert "project=" not in page.url  # no project picked for the owner
            expect(page.locator("#pack-project")).to_contain_text("Started in alpha")
            expect(page.locator("#pack-project")).not_to_contain_text("choose a project above")
            expect(page.locator("#pack-questions .pack-question")).to_have_count(1)  # shown,
            expect(page.locator("#pack p-button", has_text="Activate")).to_have_count(1)  # and answerable here
            expect(page.get_by_role("button", name="Update Impeccable")).to_be_disabled()
            expect(page.locator("#pack")).to_contain_text("Choose a project above to start one")
            expect(page.locator("#pack-install-state")).to_have_text(
                "Impeccable of OwlBear v0.3 failed to install on this machine: cannot download."
            )
            expect(page.locator("#pack-release")).to_have_text("Not known yet: GitHub did not answer.")
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
def test_settings_say_this_machine_s_settings_could_not_be_read_and_read_them_again(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """Partial state: the rest of Settings shows while this machine's settings cannot be read, the overview and This
    machine say why, and the machine's next change reads them again."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):

        def busy(route) -> None:
            if route.request.method == "GET":
                route.fulfill(status=503, json={"detail": "the machine host is busy"})
            else:
                route.fallback()

        page.route("**/api/next/machine", busy)
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#unset-machine, #unset-none")).to_contain_text("could not be read")
        pds.group(page, "this-machine")
        unread = page.locator("#machine-unread")
        expect(unread).to_contain_text("Could not read this machine's settings")
        expect(unread).to_contain_text("tries again when the machine's state changes")
        page.unroute("**/api/next/machine", busy)
        page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
        expect(page.locator("#machine-login")).to_contain_text("Start at login")
        expect(unread).to_have_count(0)
        this_machine_says_a_later_failed_read_until_one_succeeds(page, pds, busy)
        a_read_failing_after_a_save_during_it_leaves_the_save_s_answer_unwarned(page, pds)


def machine_saved(page, pds, channel: str) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.pick(page, "Layer", "machine")  # #809: this machine's own values are set with it chosen
    pds.pick(page, "Versions this machine takes", channel)
    page.get_by_role("region", name="This machine").get_by_role("button", name="Save machine settings").click()
    pds.answer(page, "Save machine settings")
    expect(page.locator("#status")).to_have_text("Saved this machine's settings.")


def this_machine_says_a_later_failed_read_until_one_succeeds(page, pds, busy) -> None:
    """CodeRabbit on #813: a later failed read keeps what was read, saying so; Copilot on #813: a save's answer is
    read, not stale."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page.route("**/api/next/machine", busy)
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
    stale = page.locator("#machine-stale")
    expect(stale).to_contain_text("Could not read this machine's settings again")
    expect(page.locator("#machine-login")).to_contain_text("Start at login")
    machine_saved(page, pds, "major")
    expect(stale).to_have_count(0)
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
    expect(stale).to_be_visible()  # a failed read after the save warns again
    page.unroute("**/api/next/machine", busy)
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
    expect(stale).to_have_count(0)


def a_read_failing_after_a_save_during_it_leaves_the_save_s_answer_unwarned(page, pds) -> None:
    """Copilot on #813: a read that a save overtook says nothing about the save's answer, even when it fails."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    held = []

    def hold(route) -> None:
        if route.request.method == "GET":
            held.append(route)
        else:
            route.fallback()

    page.route("**/api/next/machine", hold)
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
    until(page, lambda: held)
    older = len(held)
    machine_saved(page, pds, "minor")
    for route in held[:older]:
        route.abort()
    page.unroute("**/api/next/machine", hold)
    for route in held[older:]:
        route.fallback()
    page.wait_for_timeout(500)  # the aborted read's failure has been handled by now
    expect(page.locator("#machine-stale")).to_have_count(0)


def a_group_of_the_shown_page_opens_on_it(page, here: str) -> None:
    """D-01M63C8QQMANY46N8GMNNKH1V9: a Settings group's link, followed from Settings, shows it with the menu closed;
    the menu then opens on that group."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    burger, menu = page.get_by_role("button", name="Menu"), page.locator("p-drilldown")
    menu.get_by_role("link", name="Agents").click()
    expect(menu.get_by_role("link")).to_have_count(0)
    expect(page).to_have_url(f"{here}#agents")
    expect(page.locator("#agents-title")).to_be_focused()
    burger.click()
    expect(menu.get_by_role("link", name="Agents")).to_be_focused()
    expect(menu.get_by_role("link", name="Agents")).to_have_attribute("aria-current", "page")


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
        overview = menu.get_by_role("link", name="Overview")  # Settings' group shown, in Settings' level
        expect(overview).to_be_focused()
        expect(overview).to_have_attribute("aria-current", "page")
        served = ["/", "/backlog", "/memory", "/decisions", "/metrics", "/projects", "/maintenance"]
        served += ["/updates/owlbear", "/updates/pds", "/updates/impeccable"]
        groups = ["overview", "agents", "runs", "checks", "project", "this-machine"]  # D-01M63C8QQMANY46N8GMNNKH1V9
        hrefs = menu.locator("a").evaluate_all("as => as.map(a => a.getAttribute('href'))")
        assert sorted(hrefs) == sorted([f"{path}?project={a.id}" for path in served]
                                       + [f"/config?project={a.id}#{group}" for group in groups])  # fmt: skip
        a_group_of_the_shown_page_opens_on_it(page, f"{base}/config?project={a.id}")
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
@pytest.mark.parametrize("first", ["older read settles", "newer read fails"])
def test_a_newer_read_that_fails_keeps_what_an_older_one_read_in_the_meantime(
    tmp_path: Path, monkeypatch, pds, first: str
) -> None:
    """A read that starts while Remove's reread is under way and fails leaves the list Remove's reread found, marked as
    possibly out of date, whichever settles first: the failure says nothing about what the older read found."""
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
        alert = page.locator("#page > [role=alert]")
        if first == "newer read fails":
            held[-1].abort()
            expect(alert).to_be_visible()
        for route in held[:-1]:
            route.fulfill(response=route.fetch())  # the list without beta
        expect(page.get_by_role("listitem")).to_have_count(1)
        if first == "older read settles":
            held[-1].abort()
        expect(alert).to_have_text(
            "This list may be out of date: Delivery is not running. Start it, then reload this page."
        )
        expect(page.get_by_role("listitem")).to_have_count(1)


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


def checked(name: str, state: str, current: str, latest: str = "", **more) -> dict:
    """One update as ``GET /updates`` shows it, last checked successfully on 17 October."""
    return {"name": name, "title": name, "actionable": name != "pds", "state": state,
            "available": state == "newer" and name != "pds",
            "current": current, "latest": latest or current, "detail": "", "checked_at": "2026-10-17T04:00:00+00:00",
            "attempted_at": "2026-10-17T04:00:00+00:00", "failures": 0, "reason": "", "checking": False, "hours": 24,
            "next_at": "2026-10-18T04:00:00+00:00"} | more  # fmt: skip


@pytest.mark.browser
def test_updates_owlbear_marks_the_menu_refuses_start_while_work_runs_and_the_mark_clears_once_applied(  # noqa: PLR0915 - a journey
    monkeypatch, pds
) -> None:
    """D-01M63CDFXCN5SSCNNYWV2FVFVA, D-01M63CC7CYSMN156SJEBVFAXTQ, D-01M63CBWYPQZF3WBZ915YY3Q28: an available update
    marks the menu; Start update now refuses with its reason while work runs, also when work started after the page
    read; a check's failure shows once two came in a row; the mark clears once the update is applied."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.machine_host import update_checks, update_steps  # noqa: PLC0415
    from owlbear_delivery_next.machine_host.update import Updater  # noqa: PLC0415

    found = {"updates": [checked("owlbear", "newer", "v0.2", "v0.3"),
                         checked("pds", "failed", "4.10.1", "4.11.0", failures=2, reason="npm did not answer"),
                         checked("impeccable", "current", "4.8.0.1")], "available": 1}  # fmt: skip
    work, searched, started = [""], [], []
    steps = [{"key": k, "label": label, "state": "done" if k == "looking" else "pending", "started_at": None,
              "ended_at": None, "line": ""} for k, label in update_steps.STEPS]  # fmt: skip
    log = [{"at": "2026-10-17T04:00:00+00:00", "step": "looking", "line": "v0.3 is the newest"}]
    monkeypatch.setattr(update_checks.Checks, "read", lambda _self: found)
    monkeypatch.setattr(update_checks.Checks, "start", lambda _self, name: searched.append(name) or True)
    monkeypatch.setattr(Updater, "unstartable", lambda _self: work[0])
    monkeypatch.setattr(Updater, "report", lambda _self: {"phase": "current", "detail": "", "version": "", "at": None,
                                                          "steps": steps, "log": log, "startable": not work[0],
                                                          "reason": work[0]})  # fmt: skip
    monkeypatch.setattr(Updater, "run_now", lambda _self: started.append(True) or {})
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/updates/owlbear#token=t")
        burger = page.get_by_role("button", name="Menu, updates available")
        expect(burger).to_be_visible()
        expect(page.locator("#menu-dot")).to_be_visible()
        expect(page.locator("#check-state")).to_have_text("newer version")
        expect(page.locator("#check-current")).to_have_text("v0.2")
        expect(page.locator("#check-latest")).to_have_text("v0.3")
        expect(page.locator("#check-failure")).to_have_count(0)
        expect(page.locator("#owlbear-steps > li")).to_have_count(10)
        expect(page.locator("#owlbear-log-box summary")).to_have_text("Log of the update (1 line)")
        expect(page.locator("#owlbear-log")).to_be_hidden()  # folded
        expect(page.locator("#check-settings").get_by_role("link")).to_have_text("Settings → This machine")
        page.get_by_role("button", name="Search for updates").click()
        until(page, lambda: searched == ["owlbear"])
        assert targets(page.locator("#page p-button, #page a, #page summary")) == []

        posts = []
        page.on("request", lambda r: r.method == "POST" and "/update/start" in r.url and posts.append(r.url))
        page.locator("#owlbear-start").click()
        expect(pds.modal(page)).to_contain_text("Once switched there is no undo")  # D-01M5DW3X0084A25NSE99H3H6QM
        inside = "document.activeElement?.closest('p-modal') !== null"
        assert page.evaluate(inside)
        where = []
        for _ in range(6):  # the page behind is inert
            page.keyboard.press("Tab")
            where.append(page.evaluate(f"{inside} ? 'dialog' : document.activeElement === document.body ? '' : 'page'"))
        assert "page" not in where
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)
        page.wait_for_function("document.activeElement?.id === 'owlbear-start'", timeout=5000)
        assert (posts, started) == ([], [])  # Escape sent nothing

        page.get_by_role("button", name="Start update now").click()
        expect(pds.modal(page)).to_contain_text("Start the OwlBear update now?")
        work[0] = "Work runs now: alpha: alpha-1: a running step"  # started after the page read
        pds.answer(page, "Start update now")
        expect(page.locator("#owlbear-error")).to_have_text(
            "Not started: Work runs now: alpha: alpha-1: a running step."
        )
        expect(page.get_by_role("button", name="Start update now")).to_be_disabled()
        expect(page.locator("#owlbear-refused")).to_have_text("Not now: Work runs now: alpha: alpha-1: a running step.")
        refused = page.request.post(f"{base}/api/next/update/start", headers={"Authorization": "Bearer t"})
        assert (refused.status, refused.json()["detail"]) == (409, work[0])
        assert started == []

        burger.click()
        menu = page.locator("p-drilldown")
        expect(menu.get_by_role("link", name="OwlBear")).to_be_focused()  # opened at the Updates level
        expect(page.locator('p-drilldown-item[identifier="updates"]')).to_have_attribute(
            "label", "Updates, 1 available"
        )
        expect(menu.get_by_role("link", name="OwlBear").locator("p-tag")).to_have_text(["Available"])
        expect(menu.get_by_role("link", name="Porsche Design System").locator("p-tag")).to_have_text(["Failed"])
        expect(menu.get_by_role("link", name="Impeccable").locator("p-tag")).to_have_count(0)
        page.keyboard.press("Escape")
        expect(burger).to_be_focused()  # back on the burger

        found["updates"][0] = checked("owlbear", "current", "v0.3")  # applied
        found["available"] = 0
        expect(page.locator("#menu-dot")).to_have_count(0, timeout=12000)  # the next poll
        expect(page.get_by_role("button", name="Menu", exact=True)).to_be_visible()
        expect(page.locator("#check-state")).to_have_text("up to date")
        page.goto(f"{base}/updates/pds")
        expect(page.locator("#check-failure")).to_contain_text("The last 2 checks failed")
        expect(page.locator("#check-failure")).to_contain_text("npm did not answer.")
        expect(page.locator("#check-latest")).to_have_text("4.11.0, found by the last successful check")
        found["updates"][2] = checked("impeccable", "current", "4.8.0.1", failures=2, reason="GitHub answered 503")
        page.goto(f"{base}/updates/impeccable")
        expect(page.locator("#check-failure")).to_contain_text("GitHub answered 503")
        expect(page.locator("#check-state")).to_have_text("check failed")  # a shown failure is never up to date
        expect(page.locator("#check-latest")).to_have_text("not known yet")


@pytest.mark.browser
def test_a_run_started_in_one_project_is_answered_from_another_and_from_all_projects(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """D-01M63C5VGFVT3DVCC888B78K2A: Updates ▸ Impeccable is the same in every project: a run alpha started waits for
    the owner on beta's page, on a replaced project's page and under All projects, and his answer goes to alpha."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.impeccable_runs import pack_job, pack_rounds  # noqa: PLC0415

    alpha = registry.register(clone(tmp_path / "alpha"))
    beta = registry.register(clone(tmp_path / "beta"))
    old = replaced(tmp_path / "delta")  # not loaded: its own API answers nothing
    job = pack_job.Job(Store.open(Path(alpha.path)), pack_job.Live())
    question = pack_rounds.question("r1:end:1", "end", "The rounds ended.", ["activate", "discard"])
    job.state = pack_job._blank() | {  # noqa: SLF001 - a run waiting for the owner
        "state": "waiting", "started_at": datetime.now(UTC).isoformat(), "run": "r1", "questions": [question],
    }  # fmt: skip
    job._save()  # noqa: SLF001
    answered: list[tuple[str, dict]] = []

    def answering(route) -> None:
        answered.append((route.request.url, route.request.post_data_json))
        route.fulfill(json={})

    with browsing(monkeypatch, pds) as (page, base):
        page.route("**/impeccable/update/answer", answering)
        for shown in (f"?project={beta.id}", f"?project={old.id}", ""):
            answered.clear()
            page.goto(f"{base}/updates/impeccable{shown}#token=t")
            expect(page.locator("#pack-project")).to_contain_text("Started in alpha")
            page.get_by_role("button", name="Menu").click()
            impeccable = page.locator("p-drilldown").get_by_role("link", name="Impeccable")
            expect(impeccable.locator("p-tag")).to_have_text(["Waiting for you"])
            expect(impeccable).to_have_accessible_name("Impeccable Waiting for you")
            text = "a => [...a.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('')"
            assert impeccable.evaluate(text) == "Impeccable"  # no space after it for the current item's underline
            page.keyboard.press("Escape")
            page.locator("#pack").get_by_role("button", name="Activate").click()
            pds.answer(page, "Activate")
            until(page, lambda: answered)
            [(url, body)] = answered
            assert url == f"{base}/p/{alpha.id}/api/next/impeccable/update/answer"
            assert body == {"question": "r1:end:1", "option": "activate", "note": ""}

        def stopped(route) -> None:  # alpha's host stopped while it ran
            run = route.fetch().json()["run"] | {"state": "running", "interrupted": True}
            route.fulfill(json={"run": run})

        page.route("**/maintenance/pack/runs", stopped)
        page.get_by_role("button", name="Menu").click()
        impeccable = page.locator("p-drilldown").get_by_role("link", name="Impeccable")
        expect(impeccable.locator("p-tag")).to_have_text(["Host stopped"])


@pytest.mark.browser
@pytest.mark.parametrize("options", [["activate", "discard"], None], ids=["answered", "alone"])
def test_a_discard_confirmed_after_its_project_unloaded_never_goes_to_the_shown_project(
    tmp_path: Path, monkeypatch, pds, options
) -> None:
    """Discard's destination is fixed before its dialog: alpha unloading while it is open sends the confirmed discard
    to alpha, which answers for itself, never to beta, the project the page shows, whose run it is not."""
    from owlbear_delivery_next.impeccable_runs import pack_job, pack_rounds  # noqa: PLC0415

    alpha = registry.register(clone(tmp_path / "alpha"))
    beta = registry.register(clone(tmp_path / "beta"))
    job = pack_job.Job(Store.open(Path(alpha.path)), pack_job.Live())
    questions = [pack_rounds.question("r1:end:1", "end", "The rounds ended.", options)] if options else []
    job.state = pack_job._blank() | {  # noqa: SLF001 - a run waiting for the owner
        "state": "waiting", "started_at": datetime.now(UTC).isoformat(), "run": "r1", "questions": questions,
    }  # fmt: skip
    job._save()  # noqa: SLF001
    sent: list[str] = []

    def sending(route) -> None:
        sent.append(route.request.url)
        route.fulfill(json={})

    with browsing(monkeypatch, pds) as (page, base):
        page.route(re.compile(r".*/impeccable/update/(answer|discard)$"), sending)
        page.goto(f"{base}/updates/impeccable?project={beta.id}#token=t")
        label = page.locator("#pack-discard").inner_text()
        page.locator("#pack-discard").click()
        pds.modal(page).wait_for()
        unload = "async id => (await import('/assets/ui.mjs')).machineState().projects.find(p => p.id === id).state"
        page.evaluate(f"{unload} = 'failed'", alpha.id)  # what the next poll shows once alpha's host fails
        pds.answer(page, label)
        until(page, lambda: sent)
    end = "answer" if options else "discard"
    assert sent == [f"{base}/p/{alpha.id}/api/next/impeccable/update/{end}"]


@pytest.mark.browser
def test_old_update_addresses_open_the_updates_pages_and_back_and_reload_keep_them(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """D-01M63C5VGFWJ709X2GA0CE8Q5B: Maintenance's OwlBear section and Settings' Impeccable section moved to Menu ▸
    Updates; their old addresses open the new pages, with the project kept, and replace themselves in the history.
    A page whose checks cannot be read says so and still shows the rest."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/memory?project={a.id}#token=t")
        page.goto(f"{base}/maintenance?project={a.id}#owlbear")
        expect(page).to_have_url(f"{base}/updates/owlbear?project={a.id}")
        expect(page.get_by_role("heading", level=1)).to_have_text("OwlBear update")
        page.reload()
        expect(page).to_have_url(f"{base}/updates/owlbear?project={a.id}")
        expect(page.locator("#check-title, #check-unread")).to_have_count(1)
        page.go_back()
        expect(page).to_have_url(f"{base}/memory?project={a.id}")  # the old address left no entry
        page.go_forward()
        expect(page).to_have_url(f"{base}/updates/owlbear?project={a.id}")
        page.goto(f"{base}/config#pack")
        expect(page).to_have_url(f"{base}/updates/impeccable")
        expect(page.get_by_role("heading", level=1)).to_have_text("Impeccable update")
        page.goto(f"{base}/config?project={a.id}#pack")
        expect(page).to_have_url(f"{base}/updates/impeccable?project={a.id}")
        page.goto(f"{base}/config#machine-title")  # a project page names its project; the section opens its group
        expect(page).to_have_url(f"{base}/config?project={a.id}#this-machine")
        expect(page.locator("#machine-title")).to_be_focused()
        page.evaluate("location.hash = 'pack'")  # only the fragment changes: the page is not loaded again
        expect(page).to_have_url(f"{base}/updates/impeccable?project={a.id}")
        page.goto(f"{base}/maintenance?project={a.id}")
        expect(page.get_by_role("heading", level=1)).to_have_text("Maintenance")
        page.evaluate("location.hash = 'owlbear'")
        expect(page).to_have_url(f"{base}/updates/owlbear?project={a.id}")

        page.route("**/api/next/updates", lambda route: route.abort())
        page.goto(f"{base}/updates/pds?project={a.id}")
        expect(page.locator("#check-unread")).to_contain_text("Could not read the update checks")
        expect(page.locator("#pds-later")).to_be_visible()


def decided(shared: Path, folder: str, *statements: str, **more) -> None:
    """In force in *folder* of the shared repository (Global's when empty), committed and published; *more* sets other
    fields."""
    from owlbear_decisions import Decision, Origin, Scope, State, new_id, write  # noqa: PLC0415 - the decisions' own

    scope = Scope.PROJECT if folder else Scope.GLOBAL
    for said in statements:
        write(Decision(id=new_id(), title=said, statement=said, scope=scope, project=folder, origin=Origin.AUTONOMOUS,
                       actor="shaper", created_at=datetime.now(UTC), **{"state": State.IN_FORCE} | more),
              shared / folder if folder else shared)  # fmt: skip
    for args in (("add", "-A"), ("commit", "-qm", "seed"), ("push", "-q", "origin", "HEAD")):
        subprocess.run(["git", *args], cwd=shared, check=True, capture_output=True)  # noqa: S603, S607


@pytest.mark.browser
def test_decisions_under_all_projects_sum_up_each_scope_and_open_its_view_even_with_a_project_unread(
    tmp_path: Path, monkeypatch, pds, shared_repo
) -> None:
    """D-01M63C6PMT4FX370W6B2VS9HAM, D-01M5ZGHDMEG897N2SD1XNEXYNQ: All projects shows Global, OwlBear and one summary
    per project, each opening its view; a project that cannot be read says why, never left out, the rest still
    showing as each is read."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_decisions import State  # noqa: PLC0415 - the decisions' own
    from owlbear_delivery_next.local_system import data_place  # noqa: PLC0415

    shared = shared_repo[0]
    monkeypatch.setenv(data_place.VIEW, str(shared))
    a, b, gone = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta", "gone"))
    shutil.rmtree(tmp_path / "gone")
    decided(shared, "", "Pages are plain HTML.")
    decided(shared, "", "Every page has one primary.", read_back="pending", read_back_why="Asked again.",
            read_back_kind="uncertain")  # fmt: skip
    decided(shared, "owlbear", "Lint once.")
    decided(shared, "alpha", "Notes live in SQLite.")
    decided(shared, "alpha", "Notes sync nightly.", state=State.DRAFT)
    with browsing(monkeypatch, pds, 390) as (page, base):
        held: list = []

        def hold(route) -> None:  # a builtin's bound method cannot be a Playwright handler
            held.append(route)

        page.route(f"**/p/{b.id}/api/next/decisions?*", hold)
        page.goto(f"{base}/decisions#token=t")
        expect(page).to_have_url(f"{base}/decisions")  # no project is chosen for the owner
        rows = page.locator("#scopes .scope")
        expect(rows.locator("h3")).to_have_text(["Global", "OwlBear", "alpha", "beta", "gone"])
        row = {
            key: page.locator(f'#scopes .scope[data-key="{key}"]') for key in ("global", "owlbear", a.id, b.id, gone.id)
        }
        expect(row[a.id]).to_contain_text("1 in force · 1 draft")  # read while beta's read is held
        expect(row[b.id]).to_have_attribute("aria-busy", "true")
        expect(row[b.id]).to_contain_text("Reading…")
        expect(row["global"]).to_contain_text("2 in force · 0 drafts")
        expect(row["global"]).to_contain_text("1 read-back waiting")
        expect(row["owlbear"]).to_contain_text("1 in force · 0 drafts")
        expect(row[gone.id]).to_contain_text("gone is replaced: ")
        expect(row[gone.id].get_by_role("link", name="Open Projects")).to_have_attribute("href", "/projects")
        until(page, lambda: held)
        held.pop().fulfill(status=503, json={"detail": "beta's host is busy"})
        expect(row[b.id]).to_contain_text("Could not read it: beta's host is busy")
        expect(row[b.id]).to_have_attribute("aria-busy", "false")
        row[b.id].get_by_role("button", name="Read beta again").click()
        until(page, lambda: held)
        held.pop().fulfill(json={"available": False, "reason": "beta's data is behind", "decisions": []})
        expect(row[b.id]).to_contain_text("Could not read it: beta's data is behind")  # answered, yet unread: retried
        page.unroute(f"**/p/{b.id}/api/next/decisions?*")
        row[b.id].get_by_role("button", name="Read beta again").click()
        expect(row[b.id]).to_contain_text("0 in force · 0 drafts")
        assert targets(page.locator("#scopes a, #scopes button")) == []
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        each_scope_opens_its_view_and_leads_back(page, pds, base, row, a)


@pytest.mark.browser
def test_a_view_that_cannot_be_read_says_why_without_widening_a_phone(tmp_path: Path, monkeypatch, pds) -> None:
    """A long path in a notice's reason wraps: the page never scrolls sideways at 390 pixels."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    registry.register(clone(tmp_path / "alpha"))
    reason = (
        "the project owlbear has no folder in /private/var/folders/8w/3kzhj2010nz0gn9k7hz3byp/T/tmp.x/.owlbear/data"
    )
    with browsing(monkeypatch, pds, 390) as (page, base):
        page.route("**/owlbear/decisions?*", lambda route: route.fulfill(json={
            "available": False, "reason": reason, "decisions": [], "topics": [], "total": 0}))  # fmt: skip
        page.goto(f"{base}/decisions?view=global#token=t")
        expect(page.locator("#unavailable")).to_contain_text(reason)
        assert page.evaluate("document.documentElement.scrollWidth") <= 390


def each_scope_opens_its_view_and_leads_back(page, pds, base: str, row: dict, a: registry.Project) -> None:
    """Global's and OwlBear's views hold only theirs and lead back; a project's opens its page; an unlisted project
    opens the overview."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    row["global"].get_by_role("link", name="Global").click()
    expect(page).to_have_url(f"{base}/decisions?view=global")
    expect(page.locator("#shown")).to_have_text("Global · 2 shown")
    expect(page.locator(".entry")).to_have_count(2)
    expect(pds.select(page, "Show")).to_have_count(0)
    page.locator(".entry", has_text="Pages are plain HTML.").locator("summary").click()
    expect(page.locator("#detail")).to_contain_text("Origin")
    expect(page.get_by_role("button", name="Record an exception")).to_have_count(0)  # no project to own one
    queued = page.locator("#queue .queued")
    expect(queued.get_by_role("button", name="Still right")).to_have_count(1)
    expect(queued.get_by_role("button", name="Ignore for now")).to_have_count(0)  # its mark lives in a project's store
    page.get_by_role("link", name="All projects").click()
    expect(page).to_have_url(f"{base}/decisions")
    row["owlbear"].get_by_role("link", name="OwlBear").click()
    expect(page.locator("#shown")).to_have_text("OwlBear · 1 shown")
    expect(page.locator(".entry")).to_have_text([re.compile("Lint once")])
    page.goto(f"{base}/decisions")
    row[a.id].get_by_role("link", name="alpha").click()
    expect(page).to_have_url(f"{base}/decisions?project={a.id}")
    expect(page.locator(".entry", has_text="Notes live in SQLite.")).to_have_count(1)
    expect(page.locator("#queue .queued").get_by_role("button", name="Ignore for now")).to_have_count(1)
    page.goto(f"{base}/decisions?project=nobody")  # a project no longer listed opens the overview
    expect(page).to_have_url(f"{base}/decisions")


@pytest.mark.browser
def test_maintenance_under_all_projects_sums_up_each_project_and_opens_it_even_with_a_project_unread(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """D-01M63C6PMT4FX370W6B2VS9HAM: All projects shows one maintenance summary per project, each opening it; a
    project that cannot be read says why and the rest still shows."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a, b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    with browsing(monkeypatch, pds) as (page, base):
        page.route(f"**/p/{b.id}/api/next/maintenance", lambda route: route.abort())
        page.goto(f"{base}/maintenance#token=t")
        row = {p.id: page.locator(f'#projects .scope[data-key="{p.id}"]') for p in (a, b)}
        expect(page.locator("#projects h3")).to_have_text(["alpha", "beta"])
        expect(row[a.id]).to_contain_text("Memory curation: never run")
        expect(row[b.id]).to_contain_text("Could not read it: Delivery is not running")
        expect(row[b.id].get_by_role("button", name="Read beta again")).to_be_visible()
        expect(page.locator("#curation-title, #curation-error")).not_to_have_count(0)  # the machine's parts stay
        assert targets(page.locator("#projects a, #projects button")) == []
        alpha_answers_while_curation_runs(page, row[a.id], a)
        alpha_says_who_ran_memory_curation_last(page, row[a.id], a)
        row[a.id].get_by_role("link", name="alpha").click()
        expect(page).to_have_url(f"{base}/maintenance?project={a.id}")
        expect(page.locator("#actions")).to_contain_text("Memory curation")


def telling(last: dict):
    """A route handler answering with the real maintenance actions, Memory curation's last run replaced by *last*."""

    def told(route) -> None:  # one parameter: Playwright hands a two-parameter handler the request too
        body = route.fetch().json()
        route.fulfill(json=[x | {"last": last} if x["name"] == "Memory curation" else x for x in body])

    return told


def alpha_says_who_ran_memory_curation_last(page, row, a: registry.Project) -> None:
    """N1 (D-01M63CF1XKCCF6TP60734BTMWD): the summary says whether the curator or the owner ran Memory curation."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    at = "2026-01-02T03:04:05+00:00"
    for last, said in [
        ({"by": "curation", "state": "done", "started_at": None, "ended_at": at, "reason": ""},
         "Memory curation (memory curator): done, "),
        ({"by": "owner", "state": "done", "action": "approve Run ruff first", "ended_at": at},
         "Memory curation (your memory action): approve Run ruff first, "),
        ({"by": "owner", "state": "done", "action": "approve Run ruff first", "ended_at": at,
          "reason": "memory curation's runs could not be read, so they are not counted: bad JSON"},
         " — memory curation's runs could not be read, so they are not counted: bad JSON"),  # a qualification stays
    ]:  # fmt: skip
        page.route(f"**/p/{a.id}/api/next/maintenance", telling(last))
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        expect(row).to_contain_text(said)
        page.unroute(f"**/p/{a.id}/api/next/maintenance")


def alpha_answers_while_curation_runs(page, row, a: registry.Project) -> None:
    """While curation runs the page looks again every five seconds; a project read slower than that still shows."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    running = {"available": True, "folders": [{"folder": "alpha", "state": "running", "entries": []}]}
    page.route("**/api/next/curation", lambda route: route.fulfill(json=running))
    held: list = []

    def hold(route) -> None:  # a builtin's bound method cannot be a Playwright handler
        held.append(route)

    page.route(f"**/p/{a.id}/api/next/maintenance", hold)
    with page.expect_request("**/api/next/curation"):
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")  # reads all again, curation running
    until(page, lambda: held)
    with page.expect_request("**/api/next/curation", timeout=10000):
        pass  # the look again five seconds later
    held[0].continue_()
    expect(row).to_contain_text("Memory curation: never run")
    expect(row).to_have_attribute("aria-busy", "false")
    page.unroute(f"**/p/{a.id}/api/next/maintenance")
    page.unroute("**/api/next/curation")


def _git(cwd: Path, *args: str) -> None:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True)  # noqa: S603, S607


def offered(model_id: str, price: float) -> rpc.Model:
    """A model the Copilot CLI offers, at *price* per million input tokens."""
    prices = rpc.ModelBillingTokenPrices(input_price=price, output_price=15)
    limits = rpc.ModelCapabilitiesLimits(max_context_window_tokens=200_000)
    return rpc.Model(id=model_id, name=model_id, supported_reasoning_efforts=["low", "medium"],
                     default_reasoning_effort="low", billing=rpc.ModelBilling(token_prices=prices),
                     capabilities=rpc.ModelCapabilities(limits=limits))  # fmt: skip


class Outside:
    """What a machine host reads from outside (#810): a shared repository another machine pushes to, the models this
    machine's Copilot offers (m1, Global's builder model) and Impeccable's releases, each answering until told
    not to."""

    def __init__(self, shared_repo: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root, remote = shared_repo
        self.other, self.mp = tmp_path / "other", monkeypatch
        _git(tmp_path, "clone", "-q", str(remote), str(self.other))
        monkeypatch.setenv(data_repo.VIEW, str(self.root))
        self.push("config.json", agents={"builder": {"model": "m1"}})
        _git(self.root, "pull", "-q")
        self.models(3)
        self.releases(b"[]")

    def models(self, price: float | None) -> None:
        """Offer m1 at *price*; None: the model list cannot be read."""

        def read() -> list[SimpleNamespace]:
            if price is None:
                msg = "the CLI is gone"
                raise RuntimeError(msg)
            return [offered("m1", price)]

        self.mp.setattr(model_choices, "_read", read)

    def releases(self, answer: bytes | None) -> None:
        """GitHub's releases of Impeccable answer *answer*; None: GitHub is not reached."""

        def fetch(url: str, *_args: object, **_kwargs: object) -> bytes:
            if answer is None:
                msg = f"not reached: {url}"
                raise OSError(msg)
            return answer

        self.mp.setattr(pack_files, "fetch", fetch)

    def push(self, rel: str, *, whole: bool = False, **fields: object) -> None:
        """Another machine sets *fields* in the layer *rel* of the shared repository, as pulled, and pushes it; *whole*:
        the layer becomes *fields* alone, every other setting unset."""
        _git(self.other, "pull", "-q")
        path = self.other / rel
        path.parent.mkdir(exist_ok=True)
        layer = {} if whole or not path.exists() else json.loads(path.read_text())
        path.write_text(json.dumps(layer | {"format": CONFIG_FORMAT, **fields}))
        _git(self.other, "add", rel)
        _git(self.other, "commit", "-q", "-m", f"elsewhere: {rel}")
        _git(self.other, "push", "-q")

    @staticmethod
    def read(base: str, of: str) -> dict:
        """A read the page did not start, as the hourly one: the same read, through the project's route."""
        answer = httpx.post(f"{base}/p/{of}/api/next/config/read", headers=TOKEN, timeout=120)
        answer.raise_for_status()
        return answer.json()["reads"]

    @staticmethod
    def notices(base: str) -> list[str]:
        """The notices' ids, as every page's poll reads them."""
        return httpx.get(f"{base}/api/next/projects", headers=TOKEN, timeout=30).json()["reads"]["notices"]


TOKEN = {"authorization": "Bearer t"}


@pytest.fixture
def outside(shared_repo, tmp_path: Path, monkeypatch) -> Outside:
    return Outside(shared_repo, tmp_path, monkeypatch)


def errors(page: Page) -> list[str]:
    """The console errors *page* logs from now on."""
    said: list[str] = []
    page.on("console", lambda m: said.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: said.append(str(e)))
    return said


def big_enough(target) -> None:
    """WCAG 2.5.8: a control at least 24 by 24 CSS pixels."""
    box = target.bounding_box()
    assert box is not None
    assert box["width"] >= 24, box
    assert box["height"] >= 24, box


def rates(page: Page):
    """The rates the builder's model costs, as Agents shows them."""
    return page.locator("#set-agents-builder p-table-cell").last


def machine_layer(**fields: object) -> None:
    """This machine's preference layer in ~/.owlbear, written as the owner would by hand."""
    (local_home.root() / MACHINE_SETTINGS).write_text(json.dumps({"format": CONFIG_FORMAT, **fields}))


READS_TIME = 60  # a 120 s test: a read pulls the shared repository; a read the page did not start shows by its poll


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_opening_settings_reads_without_a_click(tmp_path: Path, monkeypatch, pds, outside) -> None:
    """#810: opening Settings reads every outside source, so what changed outside shows without a click."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        outside.push("config.json", agents={"builder": {"model": "m1", "minutes": 45}})
        outside.models(4)
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 4 ")
        pds.pick(page, "Layer", "global")
        pds.group(page, "runs")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("45")
        assert said == []


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_read_again_updates_every_surface_and_keeps_drafts(tmp_path: Path, monkeypatch, pds, outside) -> None:
    """#810: Read again brings Global, this project's, another project's and this machine's layers, the models'
    rates and Impeccable's releases; a failed source is named until it reads; drafts stay."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a, _b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    outside.releases(None)
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        page.goto(f"{base}/config?project={a.id}#token=t")
        status = page.locator("#reads-status")
        expect(status).to_contain_text("last full read never", timeout=READS_TIME * 1000)
        expect(page.locator(".reads-failure")).to_contain_text("Could not read: Impeccable releases — GitHub's")
        pds.group(page, "checks")
        expect(page.locator("#impeccable")).to_contain_text("releases upstream unknown")
        pds.group(page, "runs")
        page.get_by_label("Minutes per session, reviewer").fill("50")  # a draft of this project's layer
        pds.group(page, "this-machine")
        pds.pick(page, "Layer", "machine")  # #809: this machine's own values are set with it chosen
        versions = pds.select(page, "Versions this machine takes")
        channel = "minor" if versions.evaluate("e => e.value") == "major" else "major"
        pds.pick(page, "Versions this machine takes", channel)  # a draft of This machine
        outside.push("config.json", agents={"builder": {"model": "m1", "minutes": 45}})
        outside.push("alpha/config.json", agents={"builder": {"minutes": 30}})
        outside.push("beta/config.json", agents={"builder": {"minutes": 20}})
        machine_layer(agents={"builder": {"minutes": 33}})
        outside.models(5)
        outside.releases(b"[]")
        pds.group(page, "overview")
        again = page.get_by_role("button", name="Read again")
        big_enough(again)
        again.focus()
        page.keyboard.press("Enter")
        expect(status).to_contain_text("all sources", timeout=READS_TIME * 1000)
        expect(page.locator(".reads-failure")).to_have_count(0)
        across = page.locator("#across-table")
        for value in ("45 (global)", "33", "alpha: 30", "beta: 20"):
            expect(across).to_contain_text(value)
        pds.group(page, "checks")
        expect(page.locator("#impeccable")).to_contain_text("0 releases behind")
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 5 ")
        pds.pick(page, "Layer", "project")
        pds.group(page, "runs")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("30")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("50")
        pds.pick(page, "Layer", "machine")
        pds.group(page, "this-machine")
        expect(versions).to_have_js_property("value", channel)
        assert said == []


@pytest.mark.browser
@pytest.mark.usefixtures("outside")  # every source reads
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_a_read_s_layers_answered_while_a_save_reads_across_never_replace_the_saved(
    tmp_path: Path, monkeypatch, pds
) -> None:
    """#810: a read's refresh begun while a save runs, its layers answered after the save's but before the save has
    read the machine and the other projects, never shows the older layers."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        held: dict[str, Any] = {}

        def hold(name: str, method: str = "GET") -> Callable[[Any], None]:
            def handle(route: Any) -> None:
                if name in held or route.request.method != method:
                    route.continue_()
                    return
                held[name] = (route, None if method == "PUT" else route.fetch())  # a held save is not yet made

            return handle

        page.route("**/api/next/config/read", hold("read", "POST"))
        pds.group(page, "overview")
        page.locator("#read-again").click()
        until(page, lambda: "read" in held, READS_TIME)
        page.route(f"**/p/{a.id}/api/next/config/project", hold("save", "PUT"))
        pds.group(page, "runs")
        page.get_by_label("Minutes per session, builder").fill("50")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        until(page, lambda: "save" in held)  # the save has started; the host has not written it yet
        page.route(f"**/p/{a.id}/api/next/config", hold("layers"))
        route, answer = held["read"]
        route.fulfill(response=answer)
        until(page, lambda: "layers" in held)  # the layers as they are before the save writes
        page.route("**/api/next/machine", hold("machine"))
        held["save"][0].continue_()
        until(page, lambda: "machine" in held)  # the save is answered and now reads across
        route, before = held["layers"]
        with page.expect_request("**/api/next/machine"):  # the read's refresh goes on past the layers it read
            route.fulfill(response=before)
        route, machine = held["machine"]
        route.fulfill(response=machine)
        expect(page.locator("#status")).to_contain_text("Saved alpha's settings")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("50")


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_an_older_read_s_other_projects_answered_last_never_replace_a_newer_read_s(
    tmp_path: Path, monkeypatch, pds, outside
) -> None:
    """#810: two reads' refreshes overlap; another project's settings as the first one read them, answered after the
    second's, are not shown."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a, b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    outside.push("beta/config.json", agents={"builder": {"minutes": 20}})
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        pds.group(page, "overview")
        across = page.locator("#across-table")
        expect(across).to_contain_text("beta: 20")
        held: list[tuple[Any, Any]] = []

        def hold(route: Any) -> None:
            if held or route.request.method != "GET":
                route.continue_()
                return
            held.append((route, route.fetch()))  # beta's settings as the first read's refresh has them

        page.route(f"**/p/{b.id}/api/next/config", hold)
        page.locator("#read-again").click()
        until(page, lambda: held, READS_TIME)
        outside.push("beta/config.json", agents={"builder": {"minutes": 45}})
        with page.expect_request("**/config/models", timeout=READS_TIME * 1000):  # the second refresh has shown all
            page.locator("#read-again").click()
        expect(across).to_contain_text("beta: 45")
        route, before = held[0]
        with page.expect_request("**/config/models"):  # the first refresh goes on past what it read
            route.fulfill(response=before)
        expect(across).to_contain_text("beta: 45")


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_an_older_read_s_models_answered_last_never_replace_a_newer_read_s(tmp_path: Path, monkeypatch, pds, outside):
    """#810: two reads' refreshes overlap; the models' rates as the first one read them, answered after the second's,
    are not shown."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        held: list[tuple[Any, Any]] = []

        def hold(route: Any) -> None:
            if held or route.request.method != "GET":
                route.continue_()
                return
            held.append((route, route.fetch()))  # the models at 3, as the first read's refresh has them

        page.route("**/config/models", hold)
        pds.group(page, "overview")
        page.get_by_role("button", name="Read again").click()
        until(page, lambda: held, READS_TIME)
        outside.models(7)
        with page.expect_response("**/config/models", timeout=READS_TIME * 1000):
            page.get_by_role("button", name="Read again").click()
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 7 ")
        route, before = held[0]
        with page.expect_response("**/config/models"):
            route.fulfill(response=before)
        page.wait_for_timeout(200)  # the answer's handler has run
        expect(rates(page)).to_contain_text("in 7 ")


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_an_older_read_state_answered_last_never_hides_a_newer_read_s_failure(
    tmp_path: Path, monkeypatch, pds, outside
) -> None:
    """#810: the page follows a read made elsewhere while its own Read again finds a failure; the state of the earlier
    read, answered last, does not replace the newer one."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        held: list[tuple[Any, Any]] = []

        def hold(route: Any) -> None:
            if held or route.request.method != "GET":
                route.continue_()
                return
            held.append((route, route.fetch()))  # the read made elsewhere, every source read

        page.route("**/config/read", hold)
        Outside.read(base, a.id)  # the page learns of it by its poll and asks for it
        until(page, lambda: held, READS_TIME)
        outside.releases(None)
        pds.group(page, "overview")
        failure = page.locator(".reads-failure")
        page.get_by_role("button", name="Read again").click()
        expect(failure).to_contain_text("Impeccable", timeout=READS_TIME * 1000)
        route, before = held[0]
        with page.expect_request(f"**/p/{a.id}/api/next/config"):  # sent right after the state is applied and shown
            route.fulfill(response=before)
        assert "Impeccable" in " ".join(failure.all_inner_texts())  # at once: the next poll would repair it


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_an_open_page_follows_reads_and_dismissals_made_elsewhere(tmp_path: Path, monkeypatch, pds, outside) -> None:
    """#810: a read the page did not start (the hourly one) and a dismissal made elsewhere show through the poll."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        page.goto(f"{base}/config?project={a.id}#token=t")
        status = page.locator("#reads-status")
        expect(status).to_contain_text("all sources", timeout=READS_TIME * 1000)
        full = re.search(r"Last read (.+), all sources", status.inner_text()).group(1)
        outside.push("config.json", agents={"builder": {"model": "m1", "minutes": 45}})
        outside.releases(None)
        outside.models(6)
        Outside.read(base, a.id)
        changed = page.locator("#reads-changed li")
        expect(changed).to_have_count(1, timeout=READS_TIME * 1000)
        expect(changed).to_contain_text("agents.builder.minutes: unset → 45")
        expect(page.locator(".reads-failure")).to_contain_text("Could not read: Impeccable releases")
        expect(status).to_contain_text(re.compile(rf"last full read\s+{re.escape(full)}"))
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 6 ")
        pds.group(page, "overview")
        ids = Outside.notices(base)
        httpx.post(f"{base}/api/next/settings-read/dismiss", json={"ids": ids}, headers=TOKEN).raise_for_status()
        expect(changed).to_have_count(0, timeout=READS_TIME * 1000)
        assert said == []


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_a_layer_that_does_not_read_still_shows_the_read(tmp_path: Path, monkeypatch, pds, outside) -> None:
    """#810: with this machine's layer unreadable, the read still runs and says so, drafts stay, and a page opened
    then shows the failure and Read again; models kept from an earlier read say a later read of them failed."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={a.id}#token=t")
        status = page.locator("#reads-status")
        expect(status).to_contain_text("all sources", timeout=READS_TIME * 1000)
        pds.group(page, "runs")
        page.get_by_label("Minutes per session, reviewer").fill("50")
        mine = local_home.root() / MACHINE_SETTINGS
        mine.write_text("{not json")
        outside.models(7)
        Outside.read(base, a.id)  # not from the page: it learns of it by its poll
        failure = page.locator(".reads-failure")
        pds.group(page, "overview")
        expect(failure).to_contain_text(f"Could not read: this machine's settings — {mine}", timeout=READS_TIME * 1000)
        expect(status).to_contain_text("last full read")
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 7 ")
        pds.group(page, "runs")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("50")
        pds.group(page, "overview")
        page.get_by_role("button", name="Read again").click()
        expect(failure).to_contain_text(f"Could not read: this machine's settings — {mine}", timeout=READS_TIME * 1000)

        fresh = page.context.browser.new_page()  # the first keeps its draft; this one opens on the unreadable layer
        said = errors(fresh)
        pds.only(fresh, base)
        fresh.goto(f"{base}/config?project={a.id}#token=t")
        expect(fresh.locator(".reads-failure")).to_contain_text("this machine's settings", timeout=READS_TIME * 1000)
        expect(fresh.locator("#groups")).to_have_count(0)  # no layer read
        mine.unlink()
        outside.models(None)
        fresh.get_by_role("button", name="Read again").click()
        expect(fresh.locator("#reads-status")).to_contain_text("last full read", timeout=READS_TIME * 1000)
        expect(fresh.locator(".reads-failure")).to_contain_text("Could not read: models")
        pds.group(fresh, "agents")
        expect(fresh.locator("#models-note")).to_contain_text("Models as last read; reading them again failed")
        expect(rates(fresh)).to_contain_text("in 7 ")
        assert [s for s in said if "409" not in s] == []  # the opening read of the layer is refused, as said


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_a_notice_shows_old_to_new_its_overrides_and_its_link_opens_the_row(
    tmp_path: Path, monkeypatch, pds, outside
) -> None:
    """#810: a Global change from elsewhere is listed old → new, with where this machine sets the key apart; its links
    open the row in Global, in This machine's layer and in the other project."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a, b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        outside.push("config.json", agents={"builder": {"model": "m1", "minutes": 45}})
        outside.push("alpha/config.json", agents={"builder": {"minutes": 30}})
        outside.push("beta/config.json", agents={"builder": {"minutes": 20}})
        machine_layer(agents={"builder": {"minutes": 33}})
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        outside.push("config.json", agents={"builder": {"model": "m1", "minutes": 50}})
        page.get_by_role("button", name="Read again").click()
        entry = page.locator("#reads-changed li")
        expect(entry).to_contain_text("agents.builder.minutes: 45 → 50", timeout=READS_TIME * 1000)
        expect(entry).to_contain_text("Set apart by this machine, alpha, beta, so it does not apply there.")
        entry.get_by_role("link", name="agents.builder.minutes").focus()
        page.keyboard.press("Enter")
        expect(pds.select(page, "Layer")).to_have_js_property("value", "global")
        expect(page.locator("#groups a[href='#runs']")).to_have_attribute("aria-current", "page")
        minutes = page.get_by_label("Minutes per session, builder")
        expect(minutes).to_be_focused()
        expect(minutes).to_be_in_viewport()
        expect(minutes).to_have_value("50")
        pds.group(page, "overview")
        entry.get_by_role("link", name="this machine").click()
        expect(pds.select(page, "Layer")).to_have_js_property("value", "machine")
        expect(minutes).to_have_value("33")
        pds.group(page, "overview")
        entry.get_by_role("link", name="alpha").click()
        expect(pds.select(page, "Layer")).to_have_js_property("value", "project")
        expect(minutes).to_have_value("30")
        pds.group(page, "overview")
        entry.get_by_role("link", name="beta").click()
        expect(page).to_have_url(f"{base}/config?project={b.id}#runs")
        expect(minutes).to_have_value("20")
        expect(minutes).to_be_focused()
        assert said == []


@pytest.mark.browser
@pytest.mark.timeout(180)  # two reads of 300 changes and two pages: a loaded runner needs more than 30 s
def test_dismiss_one_in_settings_and_all_from_changes(tmp_path: Path, monkeypatch, pds, outside) -> None:
    """#810: Settings dismisses one entry; Changes counts the rest, links to their list and dismisses every one it
    counts, on both pages, in batches of the route's limit."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    a = registry.register(clone(tmp_path / "alpha"))
    whole = {k: v for k, v in config.BASE.model_dump(mode="json", exclude_none=True).items() if k != "format"}
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        outside.push("config.json", **whole)  # every Global setting set elsewhere
        Outside.read(base, a.id)
        outside.push("config.json", whole=True)  # and every one unset again
        reads = Outside.read(base, a.id)
        assert not reads["failures"], reads["failures"]
        n = len(reads["notices"])
        assert n > 200, n  # more than one batch
        entries = page.locator("#reads-changed li")
        expect(entries).to_have_count(n, timeout=READS_TIME * 1000)
        one = entries.first.get_by_role("button", name=re.compile(r"^Dismiss the change of "))
        big_enough(one)
        one.focus()
        page.keyboard.press("Enter")
        expect(entries).to_have_count(n - 1)
        assert len(Outside.notices(base)) == n - 1

        page.goto(f"{base}/?project={a.id}")
        banner = page.locator("#elsewhere")
        expect(banner).to_contain_text(f"{n - 1} Global settings changed elsewhere", timeout=READS_TIME * 1000)
        banner.get_by_role("link", name="Show in Settings").click()
        expect(page).to_have_url(f"{base}/config?project={a.id}#overview")
        expect(page.locator("#reads-changed")).to_be_focused(timeout=READS_TIME * 1000)
        expect(entries).to_have_count(n - 1)
        page.go_back()
        dismiss = banner.get_by_role("button", name="Dismiss")
        big_enough(dismiss)
        dismiss.focus()
        page.keyboard.press("Enter")
        expect(banner).to_have_count(0, timeout=READS_TIME * 1000)
        assert Outside.notices(base) == []
        page.goto(f"{base}/config?project={a.id}")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        expect(entries).to_have_count(0)
        assert said == []
