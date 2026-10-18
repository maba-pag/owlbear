"""The Backlog page across clones (TD-241): one backlog per repository, the projects an entry concerns, and the
clone a Change starts in."""

from __future__ import annotations

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
from owlbear_delivery_next.state_store.backlog import Backlog
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from pathlib import Path

SHOP, DOCS = "a" * 16, "b" * 16


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
    launches, apps = {SHOP: Launch(), DOCS: Launch()}, {}
    for pid, name in ((SHOP, "shop-site"), (DOCS, "docs-site")):
        store = Store(tmp_path / name, DataRepo(shared), name)
        apps[pid] = api.create_app(store, "t", Host(pid), launch=launches[pid], which=lambda _n: "/bin/code")
    listed = [{"id": SHOP, "name": "shop-site", "path": "/s", "state": "loaded"},
              {"id": DOCS, "name": "docs-site", "path": "/d", "state": "loaded"}]  # fmt: skip

    def projects(_request):
        return JSONResponse({"paused": False, "waiting": 0, "projects": listed})

    routes = [Route("/api/next/projects", projects), *(Mount(f"/p/{pid}", app) for pid, app in apps.items())]
    return Starlette(routes=[*routes, Mount("/", apps[SHOP])]), launches


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
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/backlog#token=t")
            entries = page.locator("li.entry")
            expect(entries).to_have_count(3)  # one repository: each entry once, though two clones read it
            projects = page.locator("#filters select").first
            for shown, titles in (("docs-site", ["Both sites"]), ("global", ["Every project"]),
                                  ("untriaged", ["Found in the shop"]), ("shop-site", ["Found in the shop",
                                                                                      "Both sites"])):  # fmt: skip
                projects.select_option(shown)
                expect(entries.locator(".title p-text")).to_have_text(titles)
            projects.select_option("all")
            card = entries.filter(has=page.locator(".title", has_text="Found in the shop"))
            card.get_by_text("Details, notes and links").click()
            card.get_by_label("docs-site").check()
            expect(card.locator(".concerns").first).to_have_text("docs-site")
            assert Backlog(DataRepo(shared_repo[0])).read(fresh=True)[0][found.id].projects == ["docs-site"]
            entries.filter(has=page.locator(".title", has_text="Both sites")).get_by_label("Select Both sites").check()
            page.get_by_role("button", name="Create Change from 1").click()
            page.locator("#choose").get_by_label("Shape the Change in").select_option(DOCS)
            page.get_by_role("button", name="Continue").click()
            page.locator("dialog").get_by_role("button", name="Open the chat").click()
            expect(page.locator("#started")).to_contain_text("A chat opened in VS Code")
            assert (len(launches[DOCS].prompts), launches[SHOP].prompts) == (1, [])
            assert "Both sites" in launches[DOCS].prompts[0]
            browser.close()
    finally:
        server.should_exit = True
