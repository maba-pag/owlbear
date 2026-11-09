"""Settings' outside-read and notice ordering in a real browser."""

from __future__ import annotations

import contextlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import httpx
import pytest
from copilot.generated import rpc
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.machine_host import app as machine_app
from owlbear_delivery_next.project_host import api, config_routes, pages
from owlbear_delivery_next.runtimes import model_choices, settings_seen
from owlbear_delivery_next.runtimes.settings_seen import NAME as SEEN
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, Store

from .test_machine_pages import _git, browsing, clone, errors, until
from .test_settings_page import Host as ProjectHost
from .test_shared_pages import serving

if TYPE_CHECKING:
    from playwright.sync_api import Page


class OutsideAnswers:
    """The actual page's controlled HTTP answers, made from the host's response producers."""

    def __init__(self, path: Path, monkeypatch) -> None:
        self.stores = {}
        self.layers = {}
        self.clients = {}
        monkeypatch.setattr(
            config_routes, "_github_rule", lambda _repo, _until: {"error": "AccountMissing: project has no origin"}
        )
        global_path = path / "global.json"
        global_path.write_text(json.dumps({"format": CONFIG_FORMAT, "agents": {"builder": {"model": "m1"}}}))
        for project, minutes in (("alpha", None), ("beta", 20)):
            store = Store(path / project, name=project)
            store.root.mkdir()
            store.global_path = global_path
            store.config_path.write_text(
                json.dumps({"format": CONFIG_FORMAT, "agents": {"builder": {"minutes": minutes}}})
            )
            self.stores[project] = store
            self.clients[project] = TestClient(
                api.create_app(store, "tok", ProjectHost()),
                base_url="http://127.0.0.1",
                headers={"authorization": "Bearer tok"},
            )
            self.layers[project] = self.layer(project)
        monkeypatch.setattr(machine_app.control, "autostarts", lambda: "off")
        monkeypatch.setattr(machine_app.versions, "legacy", list)
        self.machine = machine_app.machine_values(SimpleNamespace(paused=False))
        self.reads = settings_seen.Seen(
            read_at=datetime(2026, 1, 1, tzinfo=UTC),
            succeeded_at=datetime(2026, 1, 1, tzinfo=UTC),
        ).model_dump(mode="json", exclude={"seen"})
        self.models = self.model(3)

    @staticmethod
    def model(price: float) -> dict:
        return {"models": [model_choices.shown(offered(price))], "error": ""}

    def layer(self, project: str) -> dict:
        response = self.clients[project].get("/api/next/config")
        response.raise_for_status()
        return response.json()

    def beta(self, minutes: int) -> None:
        store = self.stores["beta"]
        store.config_path.write_text(json.dumps({"format": CONFIG_FORMAT, "agents": {"builder": {"minutes": minutes}}}))
        self.layers["beta"] = self.layer("beta")

    def at(self, second: int, *, failure: bool = False, no_date: bool = False) -> None:
        self.reads["read_at"] = None if no_date else f"2026-01-01T00:00:{second:02d}Z"
        if no_date:
            self.reads["succeeded_at"] = None
        self.reads["failures"] = (
            [
                {
                    "source": "read state" if no_date else "Impeccable releases",
                    "at": "2026-01-01T00:00:00Z",
                    "error": "could not read",
                }
            ]
            if failure
            else []
        )

    def notice(self) -> None:
        notice = settings_seen.Notice(
            id="0000000000000001", key="agents.builder.minutes", old="45", new="50", at=datetime(2026, 1, 1, tzinfo=UTC)
        )
        self.reads["notices"] = [notice.model_dump(mode="json") | {"overridden": ["beta"]}]

    def projects(self) -> dict:
        polled = {key: self.reads[key] for key in ("read_at", "succeeded_at")}
        polled |= {
            "failed": sorted({f["source"] for f in self.reads["failures"]}),
            "notices": [n["id"] for n in self.reads["notices"]],
        }
        return {
            "paused": False,
            "reads": polled,
            "projects": [
                {
                    "id": name,
                    "name": name,
                    "path": f"/{name}",
                    "state": "loaded",
                }
                for name in ("alpha", "beta")
            ],
        }

    def machine_values(self) -> dict:
        return self.machine

    def layers_for(self, project: str) -> dict:
        return self.layers[project]

    async def save(self, project: str, request: Request) -> dict:
        body = await request.json()
        self.stores[project].config_path.write_text(json.dumps(body["layer"]))
        self.layers[project] = self.layer(project) | {"unpublished": ""}
        return self.layers[project]

    def read(self) -> dict:
        return {"reads": self.reads}

    def offered_models(self) -> dict:
        return self.models

    async def dismiss(self, request: Request) -> dict:
        ids = (await request.json())["ids"]
        self.reads["notices"] = [n for n in self.reads["notices"] if n["id"] not in ids]
        return self.projects()["reads"]


@pytest.fixture
def answers(tmp_path, monkeypatch):
    return OutsideAnswers(tmp_path, monkeypatch)


def focused_app(answers):
    app = FastAPI()
    pages.assets(app)
    app.add_api_route("/config", api.fixed_page(pages.pages()["/config"]), methods=["GET"])
    app.add_api_route("/api/next/projects", answers.projects, methods=["GET"])
    app.add_api_route("/api/next/machine", answers.machine_values, methods=["GET"])
    app.add_api_route("/p/{project}/api/next/config", answers.layers_for, methods=["GET"])
    app.add_api_route("/p/{project}/api/next/config/project", answers.save, methods=["PUT"])
    app.add_api_route("/p/{project}/api/next/config/read", answers.read, methods=["GET", "POST"])
    app.add_api_route("/p/{project}/api/next/config/models", answers.offered_models, methods=["GET"])
    app.add_api_route("/api/next/settings-read/dismiss", answers.dismiss, methods=["POST"])
    return app


@contextlib.contextmanager
def focused_page(answers, pds):
    """Serve the real Settings page and its assets against controlled outside answers."""
    server, base = serving(focused_app(answers))
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except PlaywrightError as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.clock.install()
            page.add_init_script("""{
                const every = window.setInterval;
                window.setInterval = (fn, ms, ...args) => {
                    if (ms !== 5000) return every(fn, ms, ...args);
                    window.settingsPollAt = Date.now() + ms;
                    return every(() => {
                        window.settingsPollAt += ms;
                        return fn(...args);
                    }, ms);
                };
            }""")  # observe the real timer's next tick, without changing its interval or calling it ourselves
            finished = {"post": 0, "models": 0}

            def observed(response):
                if response.url.endswith("/config/read") and response.request.method == "POST":
                    finished["post"] += 1
                elif response.url.endswith("/config/models"):
                    finished["models"] += 1

            page.on("response", observed)
            page.goto(f"{base}/config?project=alpha#token=tok")
            until(page, lambda: finished["post"] and finished["models"] >= 2, READS_TIME)
            page.wait_for_load_state("networkidle")
            expect(page.locator("#reads-status")).to_contain_text("all sources")
            expect(page.get_by_role("button", name="Read again")).to_be_enabled()
            yield page, base
            browser.close()
    finally:
        server.should_exit = True


def hold_polls(page):
    page.route("**/api/next/projects", lambda _route: None)


def hold_first(page, url, method="GET", *, fetch=True):
    held = []

    def intercept(route):
        if held or route.request.method != method:
            route.fallback()
        else:
            held.append((route, route.fetch() if fetch else None))

    page.route(url, intercept)
    return held


def fail_read_state(route):
    route.fulfill(status=503, json={"detail": "the read state could not be read"})


def poll(page):
    """Run the registered five-second poll, stopping before a held GET's later five-second deadline."""
    page.clock.pause_at(page.evaluate("() => new Date(window.settingsPollAt).toISOString()"))


def start_polled_refresh(page):
    projects = hold_first(page, "**/api/next/projects", fetch=False)
    poll(page)
    until(page, lambda: projects)
    # The poll's HTTP answer arrives after its timer tick, so the subsequent GET's timeout is later than the next tick.
    page.clock.run_for(1)
    projects[0][0].continue_()


def polled_read(page, answers, *, failure=False):
    held = hold_first(page, "**/config/read")
    answers.at(1, failure=failure)
    start_polled_refresh(page)
    until(page, lambda: held)
    return held[0]


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_another_project_link_opens_in_a_new_tab_with_an_unsaved_edit(answers, pds):
    answers.notice()
    with focused_page(answers, pds) as (page, base):
        expect(page.locator("#reads-status")).to_contain_text("all sources")
        entry = page.locator("#reads-changed li")
        expect(entry).to_contain_text("Set apart by beta")
        pds.group(page, "agents")
        field = page.get_by_label("Minutes per session, builder")
        field.fill("31")
        expect(page.locator("#pending")).not_to_have_text("No unsaved edits.")
        pds.group(page, "overview")
        with page.context.expect_page() as opened:
            entry.get_by_role("link", name="beta").click(modifiers=["ControlOrMeta"])
        expect(opened.value).to_have_url(f"{base}/config?project=beta#agents")
        pds.group(page, "agents")
        expect(field).to_have_value("31")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_save_blocks_old_layers_before_its_across_read_finishes(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        read = hold_first(page, "**/config/read", "POST")
        page.get_by_role("button", name="Read again").click()
        until(page, lambda: read)
        save = hold_first(page, "**/p/alpha/api/next/config/project", "PUT", fetch=False)
        pds.group(page, "agents")
        field = page.get_by_label("Minutes per session, builder")
        field.fill("50")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        until(page, lambda: save)
        layers = hold_first(page, "**/p/alpha/api/next/config")
        read[0][0].fulfill(response=read[0][1])
        until(page, lambda: layers)
        machine = hold_first(page, "**/api/next/machine")
        save[0][0].continue_()
        until(page, lambda: machine)
        hold_polls(page)
        with page.expect_request("**/api/next/machine"):
            layers[0][0].fulfill(response=layers[0][1])
        expect(field).to_have_value("50")
        assert page.locator("#status").inner_text() == "Saving…"
        machine[0][0].fulfill(response=machine[0][1])
        expect(page.locator("#status")).to_contain_text("Saved alpha's settings")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_older_other_project_values_cannot_replace_a_newer_read(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        expect(page.locator("#across-table")).to_contain_text("beta: 20")
        beta = hold_first(page, "**/p/beta/api/next/config")
        again = page.get_by_role("button", name="Read again")
        again.click()
        until(page, lambda: beta)
        answers.beta(45)
        again.click()
        expect(page.locator("#across-table")).to_contain_text("beta: 45")
        hold_polls(page)
        with page.expect_request("**/config/models"):
            beta[0][0].fulfill(response=beta[0][1])
        expect(page.locator("#across-table")).to_contain_text("beta: 45")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_older_model_rates_cannot_replace_a_newer_read(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        models = hold_first(page, "**/config/models")
        again = page.get_by_role("button", name="Read again")
        again.click()
        until(page, lambda: models)
        answers.models = answers.model(7)
        again.click()
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 7 ")
        hold_polls(page)
        with page.expect_response("**/config/models"):
            models[0][0].fulfill(response=models[0][1])
        page.wait_for_timeout(200)
        expect(rates(page)).to_contain_text("in 7 ")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_second_read_stays_busy_when_the_first_refresh_finishes(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        layers = hold_first(page, "**/p/alpha/api/next/config", fetch=False)
        again = page.get_by_role("button", name="Read again")
        again.click()
        until(page, lambda: layers)
        second = hold_first(page, "**/config/read", "POST", fetch=False)
        again.click()
        until(page, lambda: second)
        expect(again).to_be_disabled()
        with page.expect_response("**/config/models"):
            layers[0][0].continue_()
        page.wait_for_timeout(200)
        assert again.is_disabled()
        second[0][0].continue_()
        expect(again).to_be_enabled()


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_old_layers_cannot_clear_a_newer_reload_failure(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        layers = hold_first(page, "**/p/alpha/api/next/config")
        answers.at(1)
        start_polled_refresh(page)
        until(page, lambda: layers)
        page.route(
            "**/p/alpha/api/next/config",
            lambda route: route.fulfill(status=503, json={"detail": "the layers could not be read"}),
        )
        answers.at(2)
        poll(page)
        error = page.locator("#error")
        expect(error).to_contain_text("could not be read")
        hold_polls(page)
        layers[0][0].fulfill(response=layers[0][1])
        page.wait_for_timeout(500)
        assert "could not be read" in error.inner_text()


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_unreadable_state_without_a_read_date_shows_its_failure(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        answers.at(1, failure=True, no_date=True)
        poll(page)
        expect(page.locator(".reads-failure")).to_contain_text("read state")
        expect(page.locator("#reads-status")).to_contain_text("No read is on record")


@pytest.mark.browser
@pytest.mark.timeout(120)
@pytest.mark.parametrize("old_fails", [False, True], ids=["source-failure", "old-503"])
def test_old_read_state_cannot_hide_a_newer_partial_read(answers, pds, old_fails):
    with focused_page(answers, pds) as (page, _base):
        route, response = polled_read(page, answers)
        answers.at(2, failure=True)
        page.get_by_role("button", name="Read again").click()
        failure = page.locator(".reads-failure")
        expect(failure).to_contain_text("Impeccable")
        hold_polls(page)
        with page.expect_request("**/p/alpha/api/next/config"):
            if old_fails:
                fail_read_state(route)
            else:
                route.fulfill(response=response)
        assert "Impeccable" in " ".join(failure.all_inner_texts())
        assert page.locator("#reads-error").count() == 0


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_old_read_state_keeps_data_without_clearing_a_newer_get_failure(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        route, response = polled_read(page, answers, failure=True)
        page.route("**/config/read", fail_read_state)
        poll(page)
        error = page.locator("#reads-error")
        expect(error).to_contain_text("could not be read")
        hold_polls(page)
        route.fulfill(response=response)
        expect(page.locator(".reads-failure")).to_contain_text("Impeccable")
        assert "could not be read" in error.inner_text()


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_old_read_state_cannot_clear_a_failed_manual_read(answers, pds):
    with focused_page(answers, pds) as (page, _base):
        route, response = polled_read(page, answers, failure=True)
        page.route(
            "**/config/read", lambda route: route.fulfill(status=503, json={"detail": "the read could not start"})
        )
        page.get_by_role("button", name="Read again").click()
        error = page.locator("#reads-error")
        expect(error).to_contain_text("could not start")
        hold_polls(page)
        route.fulfill(response=response)
        expect(page.locator(".reads-failure")).to_contain_text("Impeccable")
        assert "could not start" in error.inner_text()


@pytest.mark.browser
@pytest.mark.timeout(120)
@pytest.mark.parametrize("reread_fails", [False, True], ids=["dismiss-GET", "dismiss-reread-503"])
def test_a_dismissal_blocks_older_read_state_even_if_rereading_fails(answers, pds, reread_fails):
    answers.notice()
    with focused_page(answers, pds) as (page, _base):
        entries = page.locator("#reads-changed li")
        expect(entries).to_have_count(1)
        route, response = polled_read(page, answers)
        if reread_fails:
            page.route("**/config/read", fail_read_state)
        entries.first.get_by_role("button", name="Dismiss the change of builder · Minutes per session").click()
        if reread_fails:
            expect(page.locator("#reads-error")).to_contain_text("could not be read")
        expect(entries).to_have_count(0)
        hold_polls(page)
        with page.expect_request("**/p/alpha/api/next/config"):
            route.fulfill(response=response)
        assert entries.count() == 0


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_read_answered_after_dismissal_refreshes_current_notices(answers, pds):
    answers.notice()
    with focused_page(answers, pds) as (page, _base):
        entries = page.locator("#reads-changed li")
        expect(entries).to_have_count(1)
        held = hold_first(page, "**/config/read", "POST")
        page.get_by_role("button", name="Read again").click()
        until(page, lambda: held)
        entries.first.get_by_role("button", name="Dismiss the change of builder · Minutes per session").click()
        expect(entries).to_have_count(0)
        hold_polls(page)
        with page.expect_request("**/config/models"):
            held[0][0].fulfill(response=held[0][1])
        assert entries.count() == 0


def offered(price: float) -> rpc.Model:
    """A model the Copilot CLI offers, at *price* per million input tokens."""
    prices = rpc.ModelBillingTokenPrices(input_price=price, output_price=15)
    limits = rpc.ModelCapabilitiesLimits(max_context_window_tokens=200_000)
    return rpc.Model(
        id="m1",
        name="m1",
        supported_reasoning_efforts=["low", "medium"],
        default_reasoning_effort="low",
        billing=rpc.ModelBilling(token_prices=prices),
        capabilities=rpc.ModelCapabilities(limits=limits),
    )


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

        def read() -> list[rpc.Model]:
            if price is None:
                msg = "the CLI is gone"
                raise RuntimeError(msg)
            return [offered(price)]

        self.mp.setattr(model_choices, "_read", read)

    def releases(self, answer: bytes | None) -> None:
        """GitHub's releases of Impeccable answer *answer*; None: GitHub is not reached."""

        def fetch(url: str, *_args: object, **_kwargs: object) -> bytes:
            if answer is None:
                msg = f"not reached: {url}"
                raise OSError(msg)
            return answer

        self.mp.setattr(pack_files, "fetch", fetch)

    def push(self, rel: str, **fields: object) -> None:
        """Another machine sets *fields* in the layer *rel* of the shared repository, as pulled, and pushes it."""
        _git(self.other, "pull", "-q")
        path = self.other / rel
        path.parent.mkdir(exist_ok=True)
        layer = json.loads(path.read_text()) if path.exists() else {}
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


def big_enough(target) -> None:
    """WCAG 2.5.8: a control at least 24 by 24 CSS pixels."""
    box = target.bounding_box()
    assert box is not None
    assert box["width"] >= 24, box
    assert box["height"] >= 24, box


def rates(page: Page):
    """The rates the builder's model costs, as Agents shows them."""
    return page.locator("#set-agents-builder p-table-cell").nth(1)  # under the model it prices


def machine_layer(**fields: object) -> None:
    """This machine's preference layer in ~/.owlbear, written as the owner would by hand."""
    (local_home.root() / MACHINE_SETTINGS).write_text(json.dumps({"format": CONFIG_FORMAT, **fields}))


READS_TIME = 60  # a 120 s test: a read pulls the shared repository; a read the page did not start shows by its poll


def opening_read_shows_partial_sources(page, pds):
    expect(page.locator("#reads-status")).to_contain_text("last full read never", timeout=READS_TIME * 1000)
    expect(page.locator(".reads-failure")).to_contain_text("Could not read: Impeccable releases — GitHub's")
    pds.group(page, "agents")
    expect(rates(page)).to_contain_text("in 4 ")
    pds.pick(page, "Layer", "global")
    expect(page.get_by_label("Minutes per session, builder")).to_have_value("41")
    pds.pick(page, "Layer", "project")
    pds.group(page, "checks")
    expect(page.locator("#impeccable")).to_contain_text("releases upstream unknown")


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_read_again_updates_every_surface_and_keeps_drafts(tmp_path: Path, monkeypatch, pds, outside) -> None:
    """#810: Read again brings Global, this project's, another project's and this machine's layers, the models'
    rates and Impeccable's releases; a failed source is named until it reads; drafts stay."""

    a, _b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    outside.releases(None)
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        outside.push("config.json", agents={"builder": {"model": "m1", "minutes": 41}})
        outside.models(4)
        with page.expect_response(
            lambda response: response.request.method == "POST" and response.url.endswith("/config/read"),
            timeout=READS_TIME * 1000,
        ):
            page.goto(f"{base}/config?project={a.id}#token=t")
        opening_read_shows_partial_sources(page, pds)
        pds.group(page, "agents")
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
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        expect(page.locator(".reads-failure")).to_have_count(0)
        across = page.locator("#across-table")
        for value in ("45 (global)", "33", "alpha: 30", "beta: 20"):
            expect(across).to_contain_text(value)
        pds.group(page, "checks")
        expect(page.locator("#impeccable")).to_contain_text("0 releases behind")
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 5 ")
        pds.pick(page, "Layer", "project")
        pds.group(page, "agents")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("30")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("50")
        pds.pick(page, "Layer", "machine")
        pds.group(page, "this-machine")
        expect(versions).to_have_js_property("value", channel)
        assert said == []


@pytest.mark.browser
@pytest.mark.timeout(120)  # a real browser and a host pulling a shared repository: a loaded runner needs more than 30 s
def test_an_open_page_follows_reads_and_dismissals_made_elsewhere(tmp_path: Path, monkeypatch, pds, outside) -> None:
    """#810: a read the page did not start (the hourly one) and a dismissal made elsewhere show through the poll."""

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
        expect(changed).to_contain_text("builder · Minutes per session: unset → 45")  # the row's words, not its key
        dismiss = changed.get_by_role("button", name="Dismiss the change of builder · Minutes per session")
        expect(dismiss).to_have_count(1)
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

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={a.id}#token=t")
        status = page.locator("#reads-status")
        expect(status).to_contain_text("all sources", timeout=READS_TIME * 1000)
        pds.group(page, "agents")
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
        pds.group(page, "agents")
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
    open the row in Global, in This machine's layer and in the other project, on this page or in a new tab."""

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
        expect(entry).to_contain_text("builder · Minutes per session: 45 → 50", timeout=READS_TIME * 1000)
        expect(entry).to_contain_text("Set apart by this machine, alpha, beta, so it does not apply there.")
        page.context.add_init_script("sessionStorage.setItem('token', 't')")  # a new tab has no token of its own
        for name, layer in (("builder · Minutes per session", "global"), ("this machine", "machine")):
            with page.context.expect_page() as opened:  # a new tab loads the address, which names the layer
                entry.get_by_role("link", name=name).click(modifiers=["ControlOrMeta"])
            tab = opened.value
            expect(pds.select(tab, "Layer")).to_have_js_property("value", layer, timeout=READS_TIME * 1000)
            expect(tab.get_by_label("Minutes per session, builder")).to_have_value("50" if layer == "global" else "33")
            tab.close()
        expect(pds.select(page, "Layer")).to_have_js_property("value", "project")  # this page stays as it was
        entry.get_by_role("link", name="builder · Minutes per session").focus()
        page.keyboard.press("Enter")
        expect(pds.select(page, "Layer")).to_have_js_property("value", "global")
        expect(page.locator("#groups a[href='#agents']")).to_have_attribute("aria-current", "page")
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
        expect(page).to_have_url(f"{base}/config?project={b.id}#agents")
        expect(minutes).to_have_value("20")
        expect(minutes).to_be_focused()
        assert said == []


@pytest.mark.browser
@pytest.mark.timeout(180)  # a real host, two pages and more than 200 notices
@pytest.mark.usefixtures("outside")
def test_dismiss_one_in_settings_and_all_from_changes(tmp_path: Path, monkeypatch, pds) -> None:
    """#810: Settings dismisses one entry; Changes counts the rest, links to their list and dismisses every one it
    counts, on both pages, in batches of the route's limit."""

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        batches = []
        page.on(
            "request",
            lambda r: (
                batches.append(r.post_data_json["ids"])
                if r.method == "POST" and r.url.endswith("/settings-read/dismiss")
                else None
            ),
        )
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        Outside.read(base, a.id)
        path = local_home.root() / SEEN
        seen = settings_seen.Seen.model_validate_json(path.read_bytes())
        seen.notices = [
            settings_seen.Notice(id=f"{i:016x}", key="agents.builder.minutes", old="45", new="50", at=datetime.now(UTC))
            for i in range(202)
        ]
        atomic_write(path, seen.model_dump_json(indent=1) + "\n")
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
        expect(page.locator("#groups")).to_be_visible(timeout=READS_TIME * 1000)  # the list outlives the layers' load
        expect(page.locator("#reads-changed")).to_be_focused()
        expect(entries).to_have_count(n - 1)
        page.go_back()
        dismiss = banner.get_by_role("button", name="Dismiss")
        big_enough(dismiss)
        dismiss.focus()
        page.keyboard.press("Enter")
        expect(banner).to_have_count(0, timeout=READS_TIME * 1000)
        assert Outside.notices(base) == []
        assert [len(batch) for batch in batches] == [1, 200, 1]
        page.goto(f"{base}/config?project={a.id}")
        expect(page.locator("#reads-status")).to_contain_text("all sources", timeout=READS_TIME * 1000)
        expect(entries).to_have_count(0)
        assert said == []
