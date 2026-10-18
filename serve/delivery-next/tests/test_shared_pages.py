"""The shared repository's pages across clones (TD-241): one backlog per repository, the projects an entry concerns,
the clone a Change starts in; each shared folder's memory once, beside Global memory."""

from __future__ import annotations

import json
import socket
import threading
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
import uvicorn
from owlbear_memory import MemoryCategory, MemoryEngine
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import registry
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import backlog_issues
from owlbear_delivery_next.state_store.backlog import Backlog, Entry
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from pathlib import Path

SHOP, DOCS, TWIN = "a" * 16, "b" * 16, "c" * 16  # TWIN: a second clone of the shop on this machine


class Host:
    wake = SimpleNamespace(set=lambda: None)
    repo = None
    paused = staticmethod(lambda: False)

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
        return JSONResponse(answer | {"settings": saved.settings.model_dump(), "settings_rev": rev})

    async def configure(request):
        body = await request.json()
        try:
            registry.configure(registry.Settings.model_validate(body["settings"]), body["rev"])
        except registry.RegistryError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=409)
        return values(request)

    routes = [Route("/api/next/projects", projects), Route("/api/next/machine", values)]
    routes += [Route("/api/next/machine/settings", configure, methods=["PUT"])]
    routes += [Mount(f"/p/{pid}", app) for pid, app in apps.items()]
    return Starlette(routes=[*routes, Mount("/", apps[SHOP])]), launches


def serving(app: Starlette) -> tuple[uvicorn.Server, str]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server, f"http://127.0.0.1:{sock.getsockname()[1]}"


@pytest.mark.browser
@pytest.mark.usefixtures("github")
def test_one_backlog_for_both_clones_triaged_by_project_and_a_change_started_in_the_chosen_clone(
    tmp_path: Path, shared_repo
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
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/backlog?project={DOCS}#token=t")
            entries = page.locator("li.entry")
            expect(entries.locator(".title p-text")).to_have_text(["Both sites"])  # the page's project's entries
            page.locator("#filters select").first.select_option("all")
            page.reload()  # All stays All, though the address names a project
            expect(entries).to_have_count(3)
            page.goto(f"{base}/backlog")
            expect(entries).to_have_count(3)  # one repository: each entry once, though three clones read it
            projects = page.locator("#filters select").first
            for shown, titles in (("docs-site", ["Both sites"]), ("global", ["Every project"]),
                                  ("untriaged", ["Found in the shop"]), ("shop-site", ["Found in the shop",
                                                                                      "Both sites"])):  # fmt: skip
                projects.select_option(shown)
                expect(entries.locator(".title p-text")).to_have_text(titles)
            page.reload()  # the filter is in the address
            expect(entries.locator(".title p-text")).to_have_text(["Found in the shop", "Both sites"])
            projects.select_option("all")
            card = entries.filter(has=page.locator(".title", has_text="Found in the shop"))
            card.get_by_text("Details, notes and links").click()
            card.get_by_label("docs-site").check()
            expect(card.locator(".concerns").first).to_have_text("docs-site · found in shop-site")
            assert Backlog(DataRepo(shared_repo[0])).read(fresh=True)[0][found.id].projects == ["docs-site"]
            entries.filter(has=page.locator(".title", has_text="Both sites")).get_by_label("Select Both sites").check()
            page.get_by_role("button", name="Create Change from 1").click()
            chooser = page.locator("#choose select")
            expect(chooser.locator("option")).to_have_text(["shop-site (/s)", "docs-site", "shop-site (/s2)"])
            chooser.select_option(DOCS)
            page.get_by_role("button", name="Continue").click()
            page.locator("dialog").get_by_role("button", name="Open the chat").click()
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


@pytest.mark.browser
def test_memory_shows_each_folder_once_beside_global_and_makes_an_entry_global(tmp_path: Path, shared_repo) -> None:
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
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
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
            page.locator("dialog").get_by_role("button", name="Make global").click()
            expect(page.locator("#status")).to_contain_text('Made "Pin the runtime" global')
            expect(entries.filter(has_text="Pin the runtime").locator(".place")).to_have_text("Global")
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


def machine_settings_are_saved_and_a_stale_save_is_refused(page) -> None:
    """TD-288, TD-300: the machine section edits the machine's own settings against the revision it read."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    save = page.get_by_role("button", name="Save machine settings")
    expect(save).to_be_disabled()
    page.get_by_label("Versions this machine takes").select_option("major")
    page.get_by_label("Update itself while paused").uncheck()
    other = registry.load().settings  # another page saves first
    registry.configure(other.model_copy(update={"update_when_idle": False}), registry.revision(other))
    save.click()
    expect(page.locator("#error")).to_contain_text("changed since this page loaded them")
    expect(page.get_by_label("Versions this machine takes")).to_have_value("major")
    save.click()
    expect(page.locator("#status")).to_have_text("Saved this machine's settings.")
    expected = registry.Settings(channel="major", update_when_idle=False, update_while_paused=False)
    assert registry.load().settings == expected  # the other page's change stays; only the edits land on it
    a_read_begun_during_a_save_never_undoes_it(page)


def a_read_begun_during_a_save_never_undoes_it(page) -> None:
    """Sol: a refresh of the machine's values asked for while a save runs never shows the values before it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    held, answered = [], []  # the save waits for the test; a refresh is answered by the server at once, delivered late

    def hold(route) -> None:
        if route.request.method == "GET":
            answered.append((route, route.fetch()))
        else:
            held.append(route)

    page.route("**/api/next/machine**", hold)
    page.get_by_label("Update itself when idle").check()
    page.get_by_role("button", name="Save machine settings").click()
    while not held:
        page.wait_for_timeout(50)
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")  # a refresh while the save runs
    page.wait_for_timeout(300)
    held[0].continue_()
    expect(page.locator("#status")).to_have_text("Saved this machine's settings.")
    for route, before in answered:
        route.fulfill(response=before)  # the values from before the save, arriving after it
    page.wait_for_timeout(300)
    page.unroute("**/api/next/machine**")
    expect(page.get_by_label("Update itself when idle")).to_be_checked()
    assert registry.load().settings.update_when_idle


def unsaved_edits_keep_the_page(page, here: str) -> None:
    """No project choice, removal or addition leaves a page with unsaved edits."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page.get_by_label("Layer").select_option(f"go:{SHOP}")
    expect(page.locator("#error")).to_contain_text("Save or discard your edits")
    expect(page.get_by_label("Layer")).to_have_value("project")
    page.locator("#machine select").select_option(SHOP)
    expect(page.locator("#machine [role=alert]")).to_contain_text("Save or discard your edits")
    page.locator("#machine").get_by_role("button", name="Remove project").click()
    expect(page.locator("dialog")).to_have_count(0)
    page.locator("#machine summary").click()
    page.locator("#machine").get_by_label("Folder").fill("/elsewhere")
    page.locator("#machine").get_by_role("button", name="Add").click()
    expect(page).to_have_url(here)
    expect(page.get_by_label("Rounds at most, builder")).to_have_value("4")


@pytest.mark.browser
def test_settings_show_what_each_project_sets_apart_and_ask_where_an_edit_goes(tmp_path: Path, shared_repo) -> None:
    """TD-243: the global value and its source beside each project's differing value; the scope names Global and
    each project; the machine's values in their own section; a save another page overtook is refused."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    shop = Store(tmp_path / SHOP, DataRepo(shared_repo[0]), "shop-site")
    shop.update_config(lambda layer: layer.model_copy(update={"widths": [1600]}))
    server, base = serving(machine(tmp_path, shared_repo[0])[0])
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/config?project={DOCS}#token=t")
            across = page.locator("#across-table")
            expect(across).to_contain_text("widths")
            expect(across).to_contain_text("(built-in default)")
            expect(across).to_contain_text("shop-site: 1600")  # once, though two clones of it are registered
            expect(across).not_to_contain_text("docs-site")
            expect(across).not_to_contain_text("explore")
            page.get_by_label("Show all settings").check()  # every setting, those nobody sets apart too (TD-295)
            expect(across.get_by_text("explore", exact=True)).to_have_count(1)
            page.get_by_label("Show all settings").uncheck()
            expect(across).not_to_contain_text("explore")
            expect(page.locator("#machine-login")).to_contain_text("Start at login: off")
            machine_settings_are_saved_and_a_stale_save_is_refused(page)
            scope = page.get_by_label("Layer")
            expect(scope.locator("option")).to_have_text(
                ["Project docs-site", "Global (every project)", "Project shop-site (/s)", "Project shop-site (/s2)"]
            )
            page.get_by_label("Rounds at most, builder").fill("4")
            unsaved_edits_keep_the_page(page, f"{base}/config?project={DOCS}")
            docs = Store(tmp_path / DOCS, DataRepo(shared_repo[0]), "docs-site")
            docs.update_config(lambda layer: layer.model_copy(update={"explore": True}))  # another page saved first
            page.get_by_role("button", name="Save project settings").click()
            expect(page.locator("#error")).to_contain_text("changed since this page loaded them")
            page.get_by_role("button", name="Save project settings").click()
            expect(page.locator("#status")).to_have_text("Saved docs-site's settings. They apply to the next session.")
            expect(across).to_contain_text("docs-site: yes")  # the overview follows the save
            expect(across.locator("text=final_review · max_rounds")).to_have_count(1)  # the builder's rounds, inherited
            expect(across).to_contain_text("docs-site: 4")
            page.goto(f"{base}/config?project={DOCS}")
            scope.select_option(f"go:{SHOP}")
            expect(page).to_have_url(f"{base}/config?project={SHOP}")
            browser.close()
    finally:
        server.should_exit = True
