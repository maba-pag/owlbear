"""The Backlog page across clones (TD-241): one backlog per repository, the projects an entry concerns, and the
clone a Change starts in."""

from __future__ import annotations

import json
import socket
import threading
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
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

    routes = [Route("/api/next/projects", projects), *(Mount(f"/p/{pid}", app) for pid, app in apps.items())]
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


def test_an_older_scope_label_without_its_project_label_means_the_project_it_was_found_in():
    at = "2026-10-01T08:00:00+00:00"
    block = {"source": "run", "scope": "global", "project": "docs-site", "first_seen": at, "last_seen": at}
    issue = {"number": 7, "title": "old", "state": "open", "labels": [{"name": "scope:project"}]}
    issue["body"] = f"<!-- {backlog_issues.MARK} {json.dumps(block | {'updated_at': at})} -->"
    entry = Entry.model_validate(backlog_issues.fields(issue))  # edited on GitHub: the label wins over the block
    assert (entry.projects, entry.origin, backlog_issues.labels(entry.model_dump())) == (
        ["docs-site"], "docs-site", ["class:untriaged", "project:docs-site"]
    )  # fmt: skip
