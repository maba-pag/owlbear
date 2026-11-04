"""Settings: the context control and rates by model size (#806; D-01M6903ZDWH77QX85T0KEQBMV2,
D-01M69021X9TNY7P1H2F14FP2RJ): a switch for two sizes, a display for one, and rates and a caption that follow unsaved
model, context and effort edits."""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Agent, Layer
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path


def _rates(inp: float, out: float, cache: float, write: float) -> dict[str, float | None]:
    return {"input": inp, "output": out, "cache": cache, "cache_write": write, "cache_write_1h": None}


MODELS = {
    "models": [
        {"id": "claude-opus-5.5", "name": "Opus", "efforts": ["low", "medium", "high"], "default_effort": "medium",
         "context": 200_000, "rates": _rates(200, 1000, 20, 250),
         "long": {"context": 1_000_000, "rates": _rates(400, 1500, 40, 500)}},
        {"id": "gpt-6.1-sol", "name": "Sol", "efforts": [], "default_effort": "", "context": 272_000,
         "rates": _rates(110, 880, 11, 0), "long": None},
    ],
    "error": "",
}  # fmt: skip
ONE = "in 110 \u00b7 out 880 \u00b7 cache 11"  # a zero cache write is not shown
DEFAULT = "in 200 \u00b7 out 1,000 \u00b7 cache 20 \u00b7 cache write 250"
LONG = "in 400 \u00b7 out 1,500 \u00b7 cache 40 \u00b7 cache write 500"


class Host:
    maintenance = None
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
def settings_page(
    store: Store, pds: Any, *, wait_models: bool = True, before_goto: Callable[[Any], None] | None = None
) -> Iterator[Any]:
    """Settings ▸ Agents in a real browser, once the offered models are read unless *wait_models* is false."""
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
            pds.only(page, base)
            if before_goto:
                before_goto(page)
            page.goto(f"{base}/config#token=tok")
            pds.group(page, "agents")  # the page opens on Overview and renders only the shown group
            if wait_models:
                page.locator("#models-note").get_by_text("as this machine's Copilot offers them").wait_for()
            else:
                page.locator("#agents-rows").wait_for()
            yield page
            browser.close()
    finally:
        server.should_exit = True


def cells(page, role: str):
    """The role's row cells: agent, model (with its rates), effort, context, subagents, minutes."""
    return page.locator(f"#set-agents-{role}").locator("p-table-cell")


def caption(effort: str) -> str:
    return f"effort {effort}: same rates at every effort"


def shows(page, role: str, line: str, said: str) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    model = cells(page, role).nth(1)  # the rates and their caption sit under the model
    expect(model.locator("p-text", has_text="AI credits per 1M tokens")).to_have_text(
        f"AI credits per 1M tokens: {line}"
    )
    expect(model.locator("p-text", has_text="same rates at every effort")).to_have_text(said)


def switch(page, role: str):
    return cells(page, role).nth(3).locator("p-segmented-control")


@pytest.mark.browser
def test_arriving_models_shrink_hydrated_effort_options_without_page_errors(store, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    arrive = threading.Event()

    def offered(_self):
        arrive.wait()
        return MODELS

    monkeypatch.setattr(model_choices.Offered, "__call__", offered)
    errors = []

    def observe(page):
        page.on("pageerror", lambda error: errors.append(str(error)))

    try:
        with settings_page(store, pds, wait_models=False, before_goto=observe) as page:
            pds.settled(page)
            effort = pds.select(page, "Effort for builder")
            expect(effort.locator('p-select-option[value="max"]')).to_have_count(1)
            removed = effort.locator('p-select-option[value="max"]').element_handle()
            assert removed is not None
            layer = pds.select(page, "Layer").get_by_role("combobox")
            layer.focus()
            arrive.set()
            expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
            pds.settled(page)
            assert effort.locator("p-select-option").evaluate_all("(items) => items.map((item) => item.value)") == [
                "inherit",
                "low",
                "medium",
                "high",
            ]
            expect(effort).to_have_js_property("value", "inherit")
            expect(layer).to_be_focused()
            # A slotchange queued while this option was mounted can arrive after the offered efforts replace it.
            removed.evaluate("e => e.shadowRoot.querySelector('slot').dispatchEvent(new Event('slotchange'))")
            assert errors == []
    finally:
        arrive.set()


@pytest.mark.browser
def test_a_one_size_model_shows_its_size_and_rates_with_no_switch_or_select(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        context = cells(page, "reviewer").nth(3)  # inherits gpt-6.1-sol, effort xhigh
        expect(context).to_contain_text("272k \u00b7 only tier")
        expect(context.locator("p-segmented-control")).to_have_count(0)
        expect(context.locator("p-select")).to_have_count(0)
        shows(page, "reviewer", ONE, caption("xhigh"))  # no efforts: the same caption


@pytest.mark.browser
def test_a_two_size_model_switches_between_exactly_its_sizes_and_the_rates_follow_before_save(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        items = switch(page, "builder").locator("p-segmented-control-item")  # inherits claude-opus-5.5, medium
        expect(switch(page, "builder")).to_have_count(1)
        expect(items).to_have_count(2)
        assert [items.nth(i).get_attribute("value") for i in range(2)] == ["default", "long"]
        expect(items.nth(0).get_by_role("button")).to_have_accessible_name("200k, default context")
        expect(items.nth(1).get_by_role("button")).to_have_accessible_name("1M, long context, higher rates per token")
        shows(page, "builder", DEFAULT, caption("medium"))
        items.nth(1).click()
        shows(page, "builder", LONG, caption("medium"))
        expect(page.locator("#pending")).to_contain_text("builder · Context: inherited \u2192 long")
        items.nth(0).click()
        shows(page, "builder", DEFAULT, caption("medium"))
        expect(page.locator("#pending")).to_contain_text("builder · Context: inherited \u2192 default")
        shows(page, "test-curator", LONG, caption("high"))  # inherits the long tier
    assert not store.config_path.exists()


@pytest.mark.browser
def test_an_unsaved_model_edit_turns_the_switch_into_the_new_models_display_and_rates(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        expect(switch(page, "test-curator")).to_have_count(1)
        pds.pick(page, "Model for test-curator", "gpt-6.1-sol")
        context = cells(page, "test-curator").nth(3)
        expect(switch(page, "test-curator")).to_have_count(0)
        expect(context).to_contain_text("272k \u00b7 only tier")
        wrong = "gpt-6.1-sol has no long context (inherited); choose its default"
        expect(context).to_contain_text(wrong)
        shows(page, "test-curator", ONE, caption("high"))
        context.get_by_role("button", name="Use the default tier").click()
        expect(context).not_to_contain_text(wrong)
        shows(page, "test-curator", ONE, caption("high"))
        expect(switch(page, "reviewer")).to_have_count(0)
        pds.pick(page, "Model for reviewer", "claude-opus-5.5")
        expect(switch(page, "reviewer").locator("p-segmented-control-item")).to_have_count(2)
        shows(page, "reviewer", DEFAULT, caption("xhigh"))


@pytest.mark.browser
def test_the_rates_caption_names_the_effort_in_use_and_the_rates_never_move_with_it(store, pds, monkeypatch) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    builder = {"builder": Agent(effort="high")}
    store.save(store.config_path, Layer, lambda c: c.model_copy(update={"agents": builder}), "owner", owner=True)
    assert store.read_config().agents["builder"].effort == "high"
    judge = config.BASE.agents["design-judge"].model_copy(update={"effort": None})
    monkeypatch.setattr(
        config, "BASE", config.BASE.model_copy(update={"agents": {**config.BASE.agents, "design-judge": judge}})
    )
    with settings_page(store, pds) as page:
        shows(page, "builder", DEFAULT, caption("high"))  # saved
        pds.pick(page, "Effort for builder", "low")
        shows(page, "builder", DEFAULT, caption("low"))  # drafted
        pds.pick(page, "Effort for builder", "inherit")
        shows(page, "builder", DEFAULT, caption("medium"))  # cleared: inherited
        expect(page.locator("#pending")).to_contain_text("builder · Effort: high \u2192 inherited")
        switch(page, "builder").locator("p-segmented-control-item[value=long]").click()
        shows(page, "builder", LONG, caption("medium"))
        shows(page, "design-judge", DEFAULT, caption("unset"))
        pds.pick(page, "Effort for design-judge", "medium")
        shows(page, "design-judge", DEFAULT, caption("medium"))
    assert store.read_config().agents["builder"].effort == "high"
