"""The shared repository's pages across clones (TD-241): one backlog per repository, the projects an entry concerns,
the clone a Change starts in; each shared folder's memory once, beside Global memory."""

from __future__ import annotations

import json
import socket
import threading
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from owlbear_memory import MemoryCategory, MemoryEngine
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from owlbear_delivery_next.change_contracts.memory_curation_tools import MemoryCurationResult
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings.config import Agent, GlobalLayer, Layer
from owlbear_delivery_next.state_store import backlog_issues, machine_settings, registry
from owlbear_delivery_next.state_store.backlog import Backlog, Entry
from owlbear_delivery_next.state_store.store import Store, read_layer

if TYPE_CHECKING:
    from pathlib import Path

SHOP, DOCS, TWIN = "a" * 16, "b" * 16, "c" * 16  # TWIN: a second clone of the shop on this machine


class Host:
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    repo = None
    paused = staticmethod(lambda: False)
    draining = staticmethod(lambda: False)
    closed = staticmethod(lambda: False)
    updating = staticmethod(lambda: "")
    launching = threading.Lock()

    def __init__(self, project: str) -> None:
        self.record = HostRecord(
            url="http://127.0.0.1:9/",
            token="t",  # noqa: S106
            pid=1,
            started_at="2026-10-10T12:00:00Z",
            code=CURRENT,
            project=project,
        )

    def activity(self, _slug):
        return None


class Launch:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, _repo, _role, prompt):
        self.prompts.append(prompt)
        return {"state": "open"}


def machine(tmp_path: Path, shared: Path) -> tuple[Starlette, dict[str, Launch]]:
    """Two clones of one shared repository, as the machine host serves them: each project's app under /p/{id}."""
    launches, apps = {SHOP: Launch(), DOCS: Launch(), TWIN: Launch()}, {}
    for pid, name in ((SHOP, "shop-site"), (DOCS, "docs-site"), (TWIN, "shop-site")):
        store = Store(tmp_path / pid, DataRepo(shared), name)
        apps[pid] = api.create_app(store, "t", Host(pid), launch=launches[pid], which=lambda _n: "/bin/code")
    listed = [{"id": SHOP, "name": "shop-site", "path": "/s", "state": "loaded"},
              {"id": DOCS, "name": "docs-site", "path": "/d", "state": "loaded"},
              {"id": TWIN, "name": "shop-site", "path": "/s2", "state": "loaded"}]  # fmt: skip

    def projects(_request):
        return JSONResponse({"paused": False, "waiting": 0, "projects": listed})

    def values(_request):
        saved = registry.load()
        rev = registry.revision(saved.settings)
        answer = {"paused": False, "resumed_at": "2026-10-18T08:00:00Z", "login_item": "off"}
        glob, notice = machine_settings.shared_values(DataRepo(shared))
        resolved = machine_settings.resolve(saved.settings, glob, notice).model_dump(mode="json")
        mine = {"settings": saved.settings.model_dump(), "settings_rev": rev, "resolved": resolved}
        return JSONResponse(answer | mine | {"pending": saved.settings_pending})

    async def configure(request):
        body = await request.json()
        try:
            registry.configure(registry.Settings.model_validate(body["settings"]), body["rev"])
        except registry.RegistryError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=409)
        return values(request)

    report = MemoryCurationResult(summary="1 promoted, nothing left for you", entries=[])
    job = curation.Curation(
        Slots(lambda: 1), shared=lambda: DataRepo(shared),
        run=lambda cfg: Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True)),
    )  # fmt: skip

    async def curating(request):
        if request.method == "POST":
            job.start((await request.json())["folder"])
        return JSONResponse(job.read())

    routes = [Route("/api/next/projects", projects), Route("/api/next/machine", values)]
    routes += [Route("/api/next/machine/settings", configure, methods=["PUT"])]
    routes += [Route("/api/next/curation", curating, methods=["GET", "POST"])]
    routes += [Mount(f"/p/{pid}", app) for pid, app in apps.items()]
    return Starlette(routes=[*routes, Mount("/", apps[SHOP])]), launches


def serving(app: Starlette) -> tuple[uvicorn.Server, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    # longer than the pages' polls: route.fetch() reuses a pooled socket, which uvicorn's 5 s default closes
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", timeout_keep_alive=60))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server, f"http://127.0.0.1:{sock.getsockname()[1]}"


@pytest.mark.browser
@pytest.mark.usefixtures("github")
def test_one_backlog_for_both_clones_triaged_by_project_and_a_change_started_in_the_chosen_clone(
    tmp_path: Path, shared_repo, pds
) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    shop = Backlog(DataRepo(shared_repo[0]), "shop-site")
    found = shop.add("Found in the shop", source="review")[0]
    both = shop.add("Both sites", source="review")[0]
    shop.update(both.id, {"kind": "improvement", "projects": ["shop-site", "docs-site"]})
    everywhere = shop.add("Every project", source="review")[0]
    shop.update(everywhere.id, {"kind": "idea", "projects": []})
    app, launches = machine(tmp_path, shared_repo[0])
    server, base = serving(app)
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/backlog?project={DOCS}#token=t")
            entries = page.locator("li.entry")
            filters = page.locator("#filters")
            expect(entries.locator(".title p-text")).to_have_text(["Both sites"])  # the page's project's entries
            pds.pick(filters, "Projects", "all")
            page.reload()  # All stays All, though the address names a project
            expect(entries).to_have_count(3)
            page.goto(f"{base}/backlog")
            expect(entries).to_have_count(3)  # one repository: each entry once, though three clones read it
            for shown, titles in (("docs-site", ["Both sites"]), ("global", ["Every project"]),
                                  ("untriaged", ["Found in the shop"]), ("shop-site", ["Found in the shop",
                                                                                      "Both sites"])):  # fmt: skip
                pds.pick(filters, "Projects", shown)
                expect(entries.locator(".title p-text")).to_have_text(titles)
            page.reload()  # the filter is in the address
            expect(entries.locator(".title p-text")).to_have_text(["Found in the shop", "Both sites"])
            pds.pick(filters, "Projects", "all")
            card = entries.filter(has=page.locator(".title", has_text="Found in the shop"))
            card.get_by_text("Details, notes and links").click()
            card.get_by_label("docs-site").check()
            expect(card.locator(".concerns").first).to_have_text("docs-site · found in shop-site")
            assert Backlog(DataRepo(shared_repo[0])).read(fresh=True)[0][found.id].projects == ["docs-site"]
            entries.filter(has=page.locator(".title", has_text="Both sites")).get_by_label("Select Both sites").check()
            page.get_by_role("button", name="Create Change from 1").click()
            options = pds.select(page.locator("#choose"), "Shape the Change in").locator("p-select-option")
            expect(options).to_have_text(["shop-site (/s)", "docs-site", "shop-site (/s2)"])
            pds.pick(page.locator("#choose"), "Shape the Change in", DOCS)
            page.get_by_role("button", name="Continue").click()
            pds.answer(page, "Open the chat")
            expect(page.locator("#started")).to_contain_text("A chat opened in VS Code")
            assert (len(launches[DOCS].prompts), launches[SHOP].prompts) == (1, [])
            assert "Both sites" in launches[DOCS].prompts[0]
            browser.close()
    finally:
        server.should_exit = True


def curated(folder: Path, title: str) -> None:
    engine = MemoryEngine(folder)
    entry = engine.save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip
    engine.edit(entry.id, {"scope_agents": ["builder"]}, expected_revision=entry.revision)


def moves_back_only_where_it_came_from(page, pds, entries) -> None:
    """TD-292: a Global entry moves back to the project it was made global from; one without that record cannot."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pinned = entries.filter(has_text="Pin the runtime")
    expect(pinned.locator(".place")).to_have_text("Global")
    common = entries.filter(has_text="Sign every commit")
    expect(common.get_by_role("button", name="Move back to docs-site")).to_have_count(0)  # no origin recorded
    pinned.get_by_role("button", name="Move back to docs-site").click()
    pds.answer(page, "Move back")
    expect(page.locator("#status")).to_contain_text('Moved "Pin the runtime" back to docs-site')
    expect(pinned.locator(".place")).to_have_text("docs-site")
    pinned.get_by_role("button", name="Make global").click()
    pds.answer(page, "Make global")
    expect(pinned.locator(".place")).to_have_text("Global")


def recommendation_shows_while_pending(page, entries, folder: Path) -> None:
    """TD-293: the saver's recommended scope shows on a pending entry, and no longer once it is curated."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    engine = MemoryEngine(folder)
    prefer = engine.save(
        title="Prefer uv", content="Prefer uv: run tools with uv", categories=[MemoryCategory.PROCESS],
        confidence=0.8, source_agent="builder", scope_agents=[], recommended="global",
    )  # fmt: skip
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect(entries.filter(has_text="Prefer uv")).to_contain_text("recommended for Global")
    engine.edit(prefer.id, {"scope_agents": ["builder"]}, expected_revision=prefer.revision)  # curated
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    expect(entries.filter(has_text="Prefer uv")).to_contain_text("curated")
    expect(entries.filter(has_text="Prefer uv")).not_to_contain_text("recommended")


@pytest.mark.browser
def test_memory_shows_each_folder_once_beside_global_and_makes_an_entry_global(
    tmp_path: Path, shared_repo, pds
) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    root = shared_repo[0]
    curated(root / "shop-site" / "memory", "Run ruff first")
    curated(root / "docs-site" / "memory", "Pin the runtime")
    curated(root / "memory", "Sign every commit")
    server, base = serving(machine(tmp_path, root)[0])
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/memory#token=t")
            entries = page.locator("li.entry")
            expect(entries).to_have_count(3)  # the twin clones' folder once, Global once
            expect(entries.locator(".place")).to_have_text(["Global", "docs-site", "shop-site"])  # newest first
            page.goto(f"{base}/memory?project={DOCS}")
            expect(entries.locator(".place")).to_have_text(["Global", "docs-site"])
            common = entries.filter(has_text="Sign every commit")
            common.get_by_role("button", name="Approve").click()
            expect(page.locator("#status")).to_contain_text('Approved "Sign every commit"')
            entries.filter(has_text="Pin the runtime").get_by_role("button", name="Make global").click()
            pds.answer(page, "Make global")
            expect(page.locator("#status")).to_contain_text('Made "Pin the runtime" global')
            moves_back_only_where_it_came_from(page, pds, entries)
            page.goto(f"{base}/memory")
            expect(entries).to_have_count(3)
            page.route(f"**/p/{SHOP}/api/next/memory**", lambda r: r.abort())  # the shop's first clone stops answering
            curated(root / "shop-site" / "memory", "Read the twin")
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.locator("#error")).to_contain_text("shop-site")
            fresh = entries.filter(has_text="Read the twin")  # its twin answered now, so the folder is current
            fresh.get_by_role("button", name="Approve").click()  # and the action goes through the twin
            expect(page.locator("#status")).to_contain_text('Approved "Read the twin"')
            expect(fresh.get_by_role("button", name="Make global")).to_be_visible()
            recommendation_shows_while_pending(page, entries, root / "shop-site" / "memory")
            browser.close()
    finally:
        server.should_exit = True
    states = {e.title: e.state for e in MemoryEngine(root / "memory").get_entries()}
    assert states == {"Sign every commit": "approved", "Pin the runtime": "curated"}
    assert MemoryEngine(root / "docs-site" / "memory").get_entries() == []
    assert {e.title: e.state for e in MemoryEngine(root / "shop-site" / "memory").get_entries()}["Read the twin"] == (
        "approved"
    )


def test_an_older_scope_label_without_its_project_label_means_the_project_it_was_found_in():
    at = "2026-10-01T08:00:00+00:00"
    block = {"source": "run", "scope": "global", "project": "docs-site", "first_seen": at, "last_seen": at}
    issue = {"number": 7, "title": "old", "state": "open", "labels": [{"name": "scope:project"}]}
    issue["body"] = f"<!-- {backlog_issues.MARK} {json.dumps(block | {'updated_at': at})} -->"
    entry = Entry.model_validate(backlog_issues.fields(issue))  # edited on GitHub: the label wins over the block
    assert (entry.projects, entry.origin, backlog_issues.labels(entry.model_dump())) == (
        ["docs-site"], "docs-site", ["class:untriaged", "project:docs-site"]
    )  # fmt: skip


def machine_settings_are_saved_and_a_stale_save_is_refused(page, pds, shared: DataRepo) -> None:
    """TD-288, TD-300: the machine section edits the machine's own settings against the revision it read."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    save = page.get_by_role("region", name="This machine").get_by_role("button", name="Save machine settings")
    expect(save).to_be_disabled()
    pds.pick(page, "Versions this machine takes", "major")
    pds.pick(page, "Update itself while paused", "false")
    pds.pick(page, "Curate memory after a merge", "paused")  # on, not while paused, by default (owner, 2026-10-23)
    pds.pick(page, "Curate memory when idle (the Maintenance button always runs)", "off")
    page.get_by_label("Agent sessions at once on this machine, across its projects").fill("3")  # TD-336
    other = registry.load().settings  # another page saves first
    registry.configure(other.model_copy(update={"update_when_idle": False}), registry.revision(other))
    save.click()
    expect(pds.modal(page)).to_contain_text("Versions this machine takes: inherited → Major versions only")  # TD-396
    pds.answer(page, "Save machine settings")
    expect(page.locator("#error")).to_contain_text("changed since this page loaded them")
    expect(pds.select(page, "Versions this machine takes")).to_have_js_property("value", "major")
    save.click()
    pds.answer(page, "Save machine settings")
    expect(page.locator("#status")).to_have_text("Saved this machine's settings.")
    expected = registry.Settings(
        channel="major",
        update_when_idle=False,
        update_while_paused=False,
        curate_after_merge="paused",
        curate_when_idle="off",
        sessions=3,
    )
    assert registry.load().settings == expected  # the other page's change stays; only the edits land on it
    a_read_begun_during_a_save_never_undoes_it(page, pds)
    improvement_s_machine_settings_are_typed_and_saved(page, pds)
    every_machine_s_settings_are_saved_with_the_global_layer(page, pds, shared)


def improvement_s_machine_settings_are_typed_and_saved(page, pds) -> None:
    """Improvement (design §4): a credit limit as an amount, Retro's triggers as choices, chats as folders or none."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    limit = page.get_by_label("Retro: credit limit per run (credits)", exact=True)
    limit.press_sequentially("0.05")  # keystrokes: "0." and "0.0" stay as typed, never become 0
    expect(limit).to_have_value("0.05")
    limit.fill("")
    limit.press_sequentially("20")
    expect(limit).to_have_value("20")
    pds.pick(page, "Retro after a Change ends (the Improvement button always runs)", "off")
    chats = page.get_by_role("textbox", name="Enrolled chats: workspace folders")
    chats.press_sequentially("/w, /p")  # keystrokes: a comma and a space are kept
    expect(chats).to_have_value("/w, /p")
    pds_hours = "Hours between checks for a newer Porsche Design System (it also checks at launch)"
    named = page.locator("#set-machine-update_check_hours_pds > p-text").first  # GW8RT6: an unset setting's name is red
    expect(named).to_have_attribute("color", "error")
    page.get_by_label(pds_hours, exact=True).fill("3")
    page.get_by_role("region", name="This machine").get_by_role("button", name="Save machine settings").click()
    with page.expect_response(lambda r: r.request.method == "PUT"):  # the status says Saved from before already
        pds.answer(page, "Save machine settings")
    expect(page.locator("#status")).to_have_text("Saved this machine's settings.")
    mine = registry.load().settings
    folders = ["/w", "/p"]
    assert (mine.retro_run_credit_limit, mine.retro_after_change, mine.enrolled_chats) == (20.0, "off", folders)
    assert (mine.update_check_hours_pds, mine.update_check_hours_owlbear) == (3, None)
    expect(named).not_to_have_attribute("color", "error")
    chats.fill("/w,/p")  # the saved list again, written differently: no edit
    save = page.get_by_role("region", name="This machine").get_by_role("button", name="Save machine settings")
    expect(save).to_be_disabled()
    other = registry.load().settings  # another page enrols other folders: the refresh shows them, not old text
    registry.configure(other.model_copy(update={"enrolled_chats": ["/x"]}), registry.revision(other))
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
    expect(chats).to_have_value("/x")
    expect(save).to_be_disabled()
    a_saved_amount_is_edited_key_by_key(page, pds, limit, save)


def a_saved_amount_is_edited_key_by_key(page, pds, limit, save) -> None:
    """Sol: from a saved 20, "20.0" means 20 again on the way to 20.05; its text stays, never "20" then 205."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    expect(limit).to_have_value("20")
    limit.fill("")
    for typed in ("2", "20", "20.", "20.0", "20.05"):
        limit.press_sequentially(typed[-1])
        expect(limit).to_have_value(typed)
    save.click()
    with page.expect_response(lambda r: r.request.method == "PUT"):
        pds.answer(page, "Save machine settings")
    expect(save).to_be_disabled()
    assert registry.load().settings.retro_run_credit_limit == 20.05


def a_read_begun_during_a_save_never_undoes_it(page, pds) -> None:
    """Sol: a refresh of the machine's values asked for while a save runs never shows the values before it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    held, answered = [], []  # the save waits for the test; a refresh read before it is delivered after it

    def hold(route) -> None:
        if route.request.method == "GET":
            answered.append((route, route.fetch()))
        else:
            held.append(route)

    page.route("**/api/next/machine**", hold)
    pds.pick(page, "Update itself when idle", "true")
    page.get_by_role("region", name="This machine").get_by_role("button", name="Save machine settings").click()
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")  # a refresh begun before the save
    while not answered:
        page.wait_for_timeout(50)
    pds.answer(page, "Save machine settings")
    while not held:
        page.wait_for_timeout(50)
    with page.expect_response(lambda r: r.request.method == "PUT"):  # the status already says Saved from before
        held[0].continue_()
    expect(page.locator("#status")).to_have_text("Saved this machine's settings.")
    for route, before in answered:
        route.fulfill(response=before)  # the values from before the save, arriving after it
    page.wait_for_timeout(300)
    page.unroute("**/api/next/machine**")
    expect(pds.select(page, "Update itself when idle")).to_have_js_property("value", "true")
    assert registry.load().settings.update_when_idle


def every_machine_s_settings_are_saved_with_the_global_layer(page, pds, shared: DataRepo) -> None:
    """Global's machine settings (2026-10-23): edited under the global layer, saved with it; this machine inherits."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    machine = page.get_by_role("region", name="This machine")
    expect(machine).to_contain_text("in use: Major versions only (v1, v2 …), from this machine")
    pds.pick(page, "Versions this machine takes", "inherit")  # this machine follows Global's again
    machine.get_by_role("button", name="Save machine settings").click()
    pds.answer(page, "Save machine settings")
    expect(machine).to_contain_text("in use: Every minor version (v0.1, v0.2 …), from built-in default")
    pds.pick(page, "Layer", "global")
    expect(page.locator("#machine-global")).to_be_visible()
    pds.pick(page, "Every machine: Versions this machine takes", "major")
    page.get_by_label("Every machine: Agent sessions at once on this machine, across its projects").fill("5")
    page.get_by_label("Every machine: Hours between checks for a newer OwlBear (it also checks at launch)").fill("12")
    page.locator(".bar").get_by_role("button", name="Save global defaults").click()
    expect(pds.modal(page)).to_contain_text("machine channel: inherited → major")
    pds.answer(page, "Save global defaults")
    expect(page.locator("#status")).to_have_text("Saved the global settings. They apply to the next session.")
    glob = read_layer(shared.global_path, GlobalLayer).machine
    assert (glob.channel, glob.sessions, glob.update_when_idle) == ("major", 5, None)
    assert glob.update_check_hours_owlbear == 12  # a number, not a switch
    pds.pick(page, "Layer", "project")
    expect(machine).to_contain_text("in use: Major versions only (v1, v2 …), from global")
    expect(machine).to_contain_text("in use: 3, from this machine")  # its own sessions still override


def open_with_docs_needing_setup(page, base: str, path: str) -> None:
    """Open *path* with the machine's projects as Delivery answers them, but docs-site still needing setup, so the
    notes under the top row link to Projects."""

    def needs_setup(route) -> None:
        if route.request.method != "GET":
            route.fallback()
            return
        body = route.fetch().json()
        for p in body["projects"]:
            p["setup"] = p.get("setup") or ("owlbear setup" if p["id"] == DOCS else None)
        route.fulfill(json=body)

    page.route(f"{base}/api/next/projects", needs_setup)
    page.goto(f"{base}{path}")


def unsaved_edits_keep_the_page(page, here: str, pds) -> None:
    """No project choice, top-row link, menu link or link of the notes under them leaves a page with unsaved edits
    (D-01M63C8DA1D95Z7M9ZYWVYYNF7)."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.pick(page, "Layer", f"go:{SHOP}")
    expect(page.locator("#error")).to_contain_text("Save or discard your edits")
    expect(pds.select(page, "Layer")).to_have_js_property("value", "project")
    pds.pick(page.locator("#top"), "Project", SHOP)
    said = page.locator("#machine > [role=alert]")
    expect(said).to_have_text("Save or discard your edits before you leave this page.")
    expect(pds.select(page.locator("#top"), "Project")).to_have_js_property("value", DOCS)
    page.locator("#top nav").get_by_role("link", name="Backlog").click()
    page.locator("#machine").get_by_role("link", name="Open Projects").click()  # the project needs setup
    page.get_by_role("button", name="Menu").click()
    page.locator("p-drilldown").get_by_role("link", name="Projects").click()
    expect(page.locator("p-drilldown").get_by_role("link")).to_have_count(0)  # closed, so the reason shows
    expect(said).to_be_visible()
    expect(page).to_have_url(here)
    page.get_by_role("button", name="Menu").click()
    page.locator("p-drilldown").get_by_role("link", name="Agents").click()  # a group of this page: no leaving
    expect(page).to_have_url(here.replace("#runs", "#agents"))
    expect(page.locator("#agents-title")).to_be_focused()
    expect(page.locator("#groups a[href='#runs'] p-tag")).to_have_text("1 unsaved")
    pds.group(page, "runs")
    expect(page.get_by_label("Rounds at most, builder")).to_have_value("4")


def a_role_s_subagents_are_switched_off_and_saved(page, store: Store, pds) -> None:
    """TD-376: the per-role choice is saved as a switch, not as its text."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.group(page, "agents")
    pds.pick(page, "Built-in subagents, reviewer", "false")
    expect(page.locator("#pending")).to_contain_text("reviewer subagents: inherited → false")
    page.locator(".bar").get_by_role("button", name="Save project settings").click()
    pds.answer(page, "Save project settings")
    expect(page.locator("#pending")).to_have_text("No unsaved edits.")
    assert store.read_config().agents["reviewer"].subagents is False
    pds.pick(page, "Layer", "machine")  # TD-336: this machine's own preferences, kept local
    pds.group(page, "runs")
    page.get_by_label("Minutes per session, builder").fill("55")
    page.locator(".bar").get_by_role("button", name="Save this machine's preferences").click()
    expect(pds.modal(page)).to_contain_text("These apply to every project on this machine")
    pds.answer(page, "Save this machine's preferences")
    expect(page.locator("#status")).to_have_text("Saved this machine's settings. They apply to the next session.")
    assert store.settings().sources["agents.builder.minutes"] == "machine"
    pds.group(page, "overview")
    across = page.locator("#across-table p-table-row")
    minutes = across.filter(has_text="agents · builder · minutes")  # both baselines, apart
    cells = ["agents · builder · minutes", "40 (built-in default)", "55", "none"]
    expect(minutes.locator("p-table-cell")).to_have_text(cells)
    rounds = across.filter(has_text="final_review · max_rounds")  # derived from the builder's
    expect(rounds.locator("p-table-cell").nth(2)).to_have_text("same")
    pds.pick(page, "Layer", "project")


def the_overview_shows_what_projects_set_apart(page) -> Any:
    """TD-243, TD-295: the overview's table of what each project sets apart; returns it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    across = page.locator("#across-table")
    expect(across).to_contain_text("widths")
    expect(across).to_contain_text("(built-in default)")
    expect(across).to_contain_text("shop-site: 1600")  # once, though two clones of it are registered
    expect(across).not_to_contain_text("docs-site")
    expect(across).not_to_contain_text("planner · subagents")
    page.get_by_label("Show all settings").check()  # every setting, those nobody sets apart too (TD-295)
    expect(across.get_by_text("agents · planner · subagents", exact=True)).to_have_count(1)
    page.get_by_label("Show all settings").uncheck()
    expect(across).not_to_contain_text("planner · subagents")
    return across


@pytest.mark.browser
@pytest.mark.timeout(120)  # one page walks every settings group and saves several times: 32 s alone on a loaded laptop
def test_settings_show_what_each_project_sets_apart_and_ask_where_an_edit_goes(
    tmp_path: Path, shared_repo, pds
) -> None:
    """TD-243: the global value and its source beside each project's differing value; the scope names Global and
    each project; the machine's values in their own section; a save another page overtook is refused."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    shop = Store(tmp_path / SHOP, DataRepo(shared_repo[0]), "shop-site")
    assert (
        shop.save(
            shop.config_path, Layer, lambda layer: layer.model_copy(update={"widths": [1600]}), "setup", owner=True
        )
        == ""
    )
    server, base = serving(machine(tmp_path, shared_repo[0])[0])
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            open_with_docs_needing_setup(page, base, f"/config?project={DOCS}#token=t")
            across = the_overview_shows_what_projects_set_apart(page)
            pds.group(page, "this-machine")
            expect(page.locator("#machine-login")).to_contain_text("Start at login: off")
            machine_settings_are_saved_and_a_stale_save_is_refused(page, pds, DataRepo(shared_repo[0]))
            scope = pds.select(page, "Layer")
            expect(scope.locator("p-select-option")).to_have_text(
                ["Project docs-site", "This machine (its projects)", "Global (every project)", "Project shop-site (/s)",
                 "Project shop-site (/s2)"]
            )  # fmt: skip
            pds.group(page, "runs")
            page.get_by_label("Rounds at most, builder").fill("4")
            unsaved_edits_keep_the_page(page, f"{base}/config?project={DOCS}#runs", pds)
            docs = Store(tmp_path / DOCS, DataRepo(shared_repo[0]), "docs-site")
            off = {"agents": {"planner": Agent(subagents=False)}}
            assert (
                docs.save(docs.config_path, Layer, lambda layer: layer.model_copy(update=off), "setup", owner=True)
                == ""
            )  # another page saved first
            page.locator(".bar").get_by_role("button", name="Save project settings").click()
            pds.modal(page).get_by_role("button", name="Save project settings").click()
            expect(page.locator("#error")).to_contain_text("changed since this page loaded them")
            page.locator(".bar").get_by_role("button", name="Save project settings").click()
            pds.modal(page).get_by_role("button", name="Save project settings").click()
            expect(page.locator("#status")).to_have_text("Saved docs-site's settings. They apply to the next session.")
            pds.group(page, "overview")
            expect(across).to_contain_text("docs-site: no")  # the overview follows the save
            expect(across.locator("text=final_review · max_rounds")).to_have_count(1)  # the builder's rounds, inherited
            expect(across).to_contain_text("docs-site: 4")
            a_role_s_subagents_are_switched_off_and_saved(page, docs, pds)
            page.goto(f"{base}/config?project={DOCS}")
            pds.pick(page, "Layer", f"go:{SHOP}")
            expect(page).to_have_url(f"{base}/config?project={SHOP}")
            browser.close()
    finally:
        server.should_exit = True


@pytest.mark.browser
def test_with_no_machine_setting_set_anywhere_the_page_names_each_and_a_pending_move(
    tmp_path: Path, shared_repo, pds, monkeypatch
) -> None:
    """Code ships no defaults (2026-10-23): with no built-in layer, every unset machine setting is an error."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(machine_settings, "BASE", None)
    monkeypatch.setattr(config, "BASE", None)
    with registry.locked():
        registry.save(registry.Machine(settings_pending="the shared repository could not be brought current: offline"))
    server, base = serving(machine(tmp_path, shared_repo[0])[0])
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/config?project={DOCS}#token=t")
            listed = page.locator("#unset-this-machine")  # D-01M66B6GS0HKACV9C4R4QKFX7T: its count, its first three
            expect(listed).to_have_text(
                "This machine, 14 unset: machine.channel, machine.update_when_idle, "
                "machine.update_while_paused and 11 more"
            )
            expect(listed.get_by_role("link", name="and 11 more")).to_have_attribute("href", "#this-machine")
            pds.group(page, "this-machine")
            region = page.get_by_role("region", name="This machine")
            expect(page.locator("#machine-pending")).to_contain_text("offline")
            red = region.locator(".field > p-text[color='error']")  # GW8RT6: each unset setting's name is red
            expect(red).to_have_count(14)  # 3 update checks
            pds.pick(page, "Versions this machine takes", "minor")  # this machine's own: no longer unset
            region.get_by_role("button", name="Save machine settings").click()
            pds.answer(page, "Save machine settings")
            expect(region).to_contain_text("in use: Every minor version (v0.1, v0.2 …), from this machine")
            expect(red).to_have_count(13)
            browser.close()
    finally:
        server.should_exit = True


@pytest.mark.browser
def test_maintenance_curates_a_memory_folder_now_and_shows_its_report(tmp_path: Path, shared_repo, pds) -> None:
    """Item 5 slice 4: each folder of the shared repository with its last run; Curate now runs one at once."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    root = shared_repo[0]
    curated(root / "shop-site" / "memory", "Run ruff first")
    server, base = serving(machine(tmp_path, root)[0])
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/maintenance?project={SHOP}#token=t")
            folders = page.locator("#curation li")
            expect(folders).to_have_count(1)
            expect(folders.first).to_contain_text("Never curated.")
            folders.first.get_by_role("button", name="Curate shop-site now").click()
            pds.answer(page, "Curate now")
            expect(page.locator("#status")).to_contain_text("Curating shop-site")
            # a run still going when the page reads it shows its report on the page's next look, 5 s later
            expect(folders.first).to_contain_text("1 promoted, nothing left for you", timeout=15_000)
            browser.close()
    finally:
        server.should_exit = True
