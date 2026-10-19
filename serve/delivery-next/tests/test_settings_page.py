"""The Settings page rendered by lit-html in a real browser (TD-264): drafts per layer, models and conflicts."""

from __future__ import annotations

import contextlib
import json
import socket
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api, config_routes
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

MODELS = {
    "models": [
        {"id": "claude-opus-5.5", "name": "Opus", "efforts": ["low", "medium", "high"], "default_effort": "medium",
         "context": 200_000, "rates": None, "long": {"context": 1_000_000, "rates": None}},  # the test curator's
        {"id": "gpt-6.1-sol", "name": "Sol", "efforts": ["low", "medium", "high", "xhigh"], "default_effort": "low",
         "context": 272_000, "rates": None, "long": None},
        {"id": "tiny", "name": "Tiny", "efforts": [], "default_effort": "", "context": 200_000, "rates": None,
         "long": None},
    ],
    "error": "",
}  # fmt: skip


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106
    repo = None


@pytest.fixture
def store(tmp_path: Path, monkeypatch) -> Store:
    monkeypatch.setattr(model_choices.Offered, "__call__", lambda _self: MODELS)
    s = Store(tmp_path / "store")
    s.global_path = tmp_path / "global" / "config.json"
    return s


@contextlib.contextmanager
def settings_page(store: Store) -> Iterator[Any]:
    """The Settings page in a real browser, offline: only the test host answers, so the plain controls show."""
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
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/config#token=tok")
            page.locator("#models-note").get_by_text("as this machine's Copilot offers them").wait_for()
            yield page
            browser.close()
    finally:
        server.should_exit = True


@pytest.mark.browser
def test_a_model_choice_brings_its_efforts_and_an_effort_it_lacks_blocks_the_save(store) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store) as page:
        limits = page.locator("#limits")  # TD-286: each worker role's minutes; the shaper's chat has none
        expect(limits).to_contain_text("builder")
        expect(limits).not_to_contain_text("shaper")
        minutes = limits.get_by_label("Minutes per session, builder")
        expect(minutes).to_have_attribute("placeholder", "inherit (40)")
        page.get_by_label("Model for builder").select_option("tiny")
        expect(page.locator("#agents")).to_contain_text("tiny takes no effort setting")
        page.get_by_label("Model for reviewer").select_option("claude-opus-5.5")
        message = page.locator('[id="reviewer.effort-message"]')
        expect(message).to_have_text("claude-opus-5.5 does not offer effort xhigh (inherited); choose one it offers")
        page.get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_contain_text("Not saved: claude-opus-5.5 does not offer effort xhigh")
        page.get_by_label("Effort for reviewer").select_option("high")
        expect(message).to_have_text("")
        minutes.fill("60")
        page.get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    agents = store.read_config().agents
    assert (agents["builder"].model, agents["reviewer"].model, agents["reviewer"].effort) == (
        "tiny", "claude-opus-5.5", "high"
    )  # fmt: skip
    assert agents["builder"].minutes == 60
    assert store.settings().agents["builder"].minutes == 60


@pytest.mark.browser
def test_each_layer_keeps_its_own_drafts_and_a_save_sends_only_the_shown_layer(store) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store) as page:
        rounds = page.get_by_label("Rounds at most, builder")
        rounds.fill("4")
        page.get_by_label("Layer").select_option("global")
        expect(page.locator("#pending")).to_have_text("No unsaved edits. This project: 1 more unsaved.")
        expect(rounds).to_have_value("")
        page.get_by_label("Minutes per session, builder").fill("60")
        page.get_by_label("Layer").select_option("project")
        expect(rounds).to_have_value("4")
        expect(page.locator("#pending")).to_have_text(
            "Unsaved: builder max rounds: inherited → 4. All projects: 1 more unsaved."
        )
        page.get_by_label("When the design judge fails a change").select_option("back")  # renders the page again
        expect(rounds).to_have_value("4")
        labels = page.get_by_label("Labels, comma-separated; none for no labels")
        labels.fill("inherit")  # a label may be named so: typing it never means "inherit"
        expect(labels).to_have_value("inherit")
        labels.fill("release:minor, owlbear")
        page.get_by_label("The line Opened by OwlBear Delivery").select_option("off")
        at_once = page.get_by_label("Agent sessions at once in one project")  # TD-336
        expect(at_once).to_have_attribute("placeholder", "inherit (2)")
        at_once.fill("3")
        page.get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        page.get_by_label("Layer").select_option("global")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("60")
        expect(page.locator("#pr")).to_contain_text("Set in each project")  # TD-308: the marker is per project
    project = store.read_config()
    assert (project.agents["builder"].max_rounds, project.design_failures, project.agents["builder"].minutes) == (
        4, "back", None
    )  # fmt: skip
    assert (project.pr_labels, project.pr_marker, project.sessions) == (["release:minor", "owlbear"], False, 3)
    assert not store.global_path.exists()


@pytest.mark.browser
def test_a_save_refused_by_a_newer_save_keeps_the_edits_and_the_next_save_lands(store) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store) as page:
        c = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1",
                       headers={"authorization": "Bearer t"})  # fmt: skip
        got = c.get("/api/next/config").json()
        newer = got["project"] | {"widths": [1600]}
        assert c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": newer}).status_code == 200
        page.get_by_label("Minutes per session, reviewer").fill("25")
        page.get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_contain_text("kept your unsaved edits; check them and save again.")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("25")
        page.get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    saved = json.loads(store.config_path.read_text())
    assert (saved["widths"], saved["agents"]["reviewer"]["minutes"]) == ([1600], 25)


@pytest.mark.browser
def test_models_arriving_while_a_model_name_is_typed_wait_until_the_field_is_left(store, monkeypatch) -> None:
    """Sol, TD-264: the offered models replace the typed field only once the owner leaves it."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    def slow(_self: object) -> dict[str, Any]:
        time.sleep(2.5)
        return MODELS

    monkeypatch.setattr(model_choices.Offered, "__call__", slow)
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
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/config#token=tok")
            typed = page.locator('input[aria-label="Model for builder"]')
            typed.click()
            typed.press_sequentially("my-model")
            expect(page.locator("#models-note")).to_contain_text("Reading the models")
            time.sleep(3.5)  # the models arrived meanwhile
            typed.press_sequentially("-2")
            expect(typed).to_be_focused()
            expect(typed).to_have_value("my-model-2")
            page.get_by_label("Layer").focus()  # leaving the settings lets the models in
            expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
            chosen = page.locator('select[aria-label="Model for builder"]')
            expect(chosen).to_have_value("my-model-2")
            expect(chosen.locator("option:checked")).to_have_text("my-model-2 (not offered here)")
            browser.close()
    finally:
        server.should_exit = True


@pytest.mark.browser
def test_models_arriving_during_a_save_apply_once_it_ends(store, monkeypatch) -> None:
    """Sol, TD-264: a save under way when the models arrive leaves them for its end, never for good."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    arrive, saved = threading.Event(), threading.Event()

    def slow(_self: object) -> dict[str, Any]:
        arrive.wait(10)
        return MODELS

    monkeypatch.setattr(model_choices.Offered, "__call__", slow)
    real = config_routes._save  # noqa: SLF001 - the save the route runs

    def save(*args: Any) -> str:
        arrive.set()  # the models answer while this save runs
        time.sleep(1.0)
        saved.set()
        return real(*args)

    monkeypatch.setattr(config_routes, "_save", save)
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
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/config#token=tok")
            page.get_by_label("Minutes per session, builder").fill("50")
            page.get_by_role("button", name="Save project settings").click()
            expect(page.locator("#status")).to_have_text(
                "Saved this project's settings. They apply to the next session.", timeout=10_000
            )
            expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
            expect(page.locator('select[aria-label="Model for builder"]')).to_be_visible()
            browser.close()
    finally:
        server.should_exit = True
    assert saved.is_set()
