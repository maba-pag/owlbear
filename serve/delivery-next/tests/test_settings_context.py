"""Settings: the context control and rates by model size (#806; D-01M6903ZDWH77QX85T0KEQBMV2,
D-01M69021X9TNY7P1H2F14FP2RJ): a switch for two sizes, a display for one, and rates and a caption that follow unsaved
model, context and effort edits."""

from __future__ import annotations

import pytest

from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Agent, Layer

from . import test_settings_page
from .test_config_api import offered_model, prices
from .test_settings_page import hold_first, settings_page

local_store = test_settings_page.local_store

ONE = "in 110 \u00b7 out 880 \u00b7 cache 11"  # a zero cache write is not shown
DEFAULT = "in 200 \u00b7 out 1,000 \u00b7 cache 20 \u00b7 cache write 250"
LONG = "in 400 \u00b7 out 1,500 \u00b7 cache 40 \u00b7 cache write 500"


@pytest.fixture
def store(local_store, monkeypatch):
    opus = prices(200_000, 200, 1000, prices(1_000_000, 400, 1500))
    opus.cache_read_price, opus.cache_write_price = 20, 250
    opus.long_context.cache_read_price, opus.long_context.cache_write_price = 40, 500
    sol = prices(272_000, 110, 880)
    sol.cache_read_price = 11
    monkeypatch.setattr(
        model_choices,
        "_read",
        lambda: [
            offered_model("claude-opus-5.5", ["low", "medium", "high"], tiers=opus),
            offered_model("gpt-6.1-sol", [], tiers=sol),
        ],
    )
    return local_store


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
def test_a_one_size_model_shows_its_size_and_rates_with_no_switch_or_select(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    errors, held = [], []

    def observe(page):
        page.on("pageerror", lambda error: errors.append(str(error)))
        held.append(hold_first(page, "**/config/models"))

    with settings_page(store, pds, wait_models=False, before_goto=observe) as page:
        pds.settled(page)
        effort = pds.select(page, "Effort for builder")
        expect(effort.locator('p-select-option[value="max"]')).to_have_count(1)
        removed = effort.locator('p-select-option[value="max"]').element_handle()
        assert removed is not None
        layer = pds.select(page, "Layer").get_by_role("combobox")
        layer.focus()
        route, response = held[0][0]
        route.fulfill(response=response)
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
        context = cells(page, "reviewer").nth(3)  # inherits gpt-6.1-sol, effort xhigh
        expect(context).to_contain_text("272k \u00b7 only tier")
        expect(context.locator("p-segmented-control")).to_have_count(0)
        expect(context.locator("p-select")).to_have_count(0)
        shows(page, "reviewer", ONE, caption("xhigh"))  # no efforts: the same caption
        assert errors == []


@pytest.mark.browser
def test_a_two_size_model_switches_between_exactly_its_sizes_and_the_rates_follow_before_save(
    store, pds, monkeypatch
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    builder = {"builder": Agent(effort="high")}
    store.save(store.config_path, Layer, lambda c: c.model_copy(update={"agents": builder}), "owner", owner=True)
    assert store.read_config().agents["builder"].effort == "high"
    before = store.config_path.read_bytes()
    judge = config.BASE.agents["design-judge"].model_copy(update={"effort": None})
    monkeypatch.setattr(
        config, "BASE", config.BASE.model_copy(update={"agents": {**config.BASE.agents, "design-judge": judge}})
    )
    with settings_page(store, pds) as page:
        shows(page, "builder", DEFAULT, caption("high"))
        pds.pick(page, "Effort for builder", "low")
        shows(page, "builder", DEFAULT, caption("low"))
        pds.pick(page, "Effort for builder", "inherit")
        shows(page, "builder", DEFAULT, caption("medium"))
        expect(page.locator("#pending")).to_contain_text("builder · Effort: high \u2192 inherited")
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
        shows(page, "design-judge", DEFAULT, caption("unset"))
        pds.pick(page, "Effort for design-judge", "medium")
        shows(page, "design-judge", DEFAULT, caption("medium"))
    assert store.config_path.read_bytes() == before
