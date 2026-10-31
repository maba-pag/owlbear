"""The Settings page rendered by lit-html in a real browser (TD-264): drafts per layer, models and conflicts."""

from __future__ import annotations

import contextlib
import json
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api, config_routes
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.settings.improvement import ALLOWED, CATEGORIES
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
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
def settings_page(store: Store, pds: Any) -> Iterator[Any]:
    """The Settings page in a real browser: only the test host and the PDS CDN answer."""
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
            page.goto(f"{base}/config#token=tok")
            opened(page, pds)
            yield page
            browser.close()
    finally:
        server.should_exit = True


def opened(page, pds, group: str = "agents") -> None:
    """Settings once this machine's models are read, showing *group*."""
    pds.group(page, "agents")
    page.locator("#models-note").get_by_text("as this machine's Copilot offers them").wait_for()
    if group != "agents":
        pds.group(page, group)


def _unset_count(page, group: str) -> int:
    """How many settings the overview's unset list counts in *group* ("Agents, 70 unset: …")."""
    page.locator(f"#unset-{group}").wait_for()
    return int(page.locator(f"#unset-{group}").inner_text().split(", ", 1)[1].split(" ", 1)[0])


def a_look_s_credit_limit_is_typed_as_an_amount(page) -> None:
    """D-01M5XCD49YHHR1NQKKY8TQD0C3: it inherits Global's, and keystrokes keep a fraction as typed."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    look_limit = page.get_by_label("Credit limit per look", exact=True)
    expect(look_limit).to_have_attribute("placeholder", "inherit (0.75)")
    look_limit.press_sequentially("0.05")
    expect(look_limit).to_have_value("0.05")


def the_spotter_is_edited(page, pds) -> Any:
    """The spotter's switch, looks, sample and credit limit, edited in the Agents group; returns the looks field."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.group(page, "agents")
    expect(page.locator("#spotter")).to_contain_text("inherit (on)")  # the switch, as Global sets it
    pds.pick(page, "On or off", "off")
    looks = page.get_by_label("Looks", exact=True)
    expect(looks).to_have_attribute("placeholder", "inherit (hand-off)")
    looks.fill("hand-off, sample")
    page.get_by_label("Sampled actions", exact=True).fill("5")
    a_look_s_credit_limit_is_typed_as_an_amount(page)
    return looks


def the_global_layer_kept_its_edit_and_takes_one_more(page, pds) -> None:
    """Global's draft stays through a project save; the curator's threshold is Global's alone (TD-400)."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.pick(page, "Layer", "global")
    pds.group(page, "runs")
    expect(page.get_by_label("Minutes per session, builder")).to_have_value("60")
    pds.group(page, "checks")
    expect(page.locator("#pr")).to_contain_text("Unset")  # D-01M61SEXPFT9MXZGQHYVYFQ77C: nothing under Global
    pds.group(page, "runs")
    threshold = page.get_by_label("Curator's confidence threshold in percent (50 to 100)")
    expect(threshold).to_have_attribute("placeholder", "Unset")
    threshold.fill("90")
    expect(page.locator("#pending")).to_contain_text("curator threshold: unset → 90")
    pds.pick(page, "Layer", "project")
    held = page.locator("#set-curator_threshold")  # #809: one value everywhere, shown read-only as saved
    expect(held).to_contain_text("set on Global")
    expect(threshold).to_be_disabled()
    expect(threshold).to_have_value("95")


def a_list_keeps_its_text_as_typed_and_counts_only_new_items(page, looks) -> None:
    """Copilot, #662: a saved list written differently is no edit; extending it by keyboard keeps the comma."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    looks.fill("hand-off,sample")
    expect(page.locator("#pending")).to_contain_text("No unsaved edits.")  # the global edit stays apart
    looks.press_sequentially(",")
    expect(looks).to_have_value("hand-off,sample,")
    looks.press_sequentially(" plan")
    expect(page.locator("#pending")).to_contain_text("spot looks: hand-off, sample → hand-off,sample, plan")
    looks.fill("hand-off, sample")


@pytest.mark.browser
def test_a_model_choice_brings_its_efforts_and_an_effort_it_lacks_blocks_the_save(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        pds.group(page, "runs")
        limits = page.locator("#limits")  # TD-286: each worker role's minutes; the shaper's chat has none
        expect(limits).to_contain_text("builder")
        expect(limits).not_to_contain_text("shaper")
        minutes = limits.get_by_label("Minutes per session, builder")
        expect(minutes).to_have_attribute("placeholder", "inherit (40)")
        pds.group(page, "agents")
        pds.pick(page, "Model for builder", "tiny")
        expect(page.locator("#agents-rows")).to_contain_text("tiny takes no effort setting")
        pds.pick(page, "Model for reviewer", "claude-opus-5.5")
        said = "claude-opus-5.5 does not offer effort xhigh (inherited); choose one it offers"
        message = pds.select(page, "Effort for reviewer").get_by_text(said, exact=True)
        expect(message).to_be_visible()
        page.get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_contain_text("Not saved: claude-opus-5.5 does not offer effort xhigh")
        pds.pick(page, "Effort for reviewer", "high")
        expect(message).to_have_count(0)
        pds.group(page, "runs")
        minutes.fill("60")
        page.get_by_role("button", name="Save project settings").click()
        expect(pds.modal(page)).to_contain_text("These apply to this project only")  # TD-396
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    agents = store.read_config().agents
    assert (agents["builder"].model, agents["reviewer"].model, agents["reviewer"].effort) == (
        "tiny", "claude-opus-5.5", "high"
    )  # fmt: skip
    assert agents["builder"].minutes == 60
    assert store.settings().agents["builder"].minutes == 60


@pytest.mark.browser
def test_each_layer_keeps_its_own_drafts_and_a_save_sends_only_the_shown_layer(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        pds.group(page, "runs")
        rounds = page.get_by_label("Rounds at most, builder")
        rounds.fill("4")
        pds.pick(page, "Layer", "global")
        expect(page.locator("#pending")).to_have_text("No unsaved edits. This project: 1 more unsaved.")
        expect(page.locator("#save")).to_have_attribute("variant", "secondary")  # nothing of this layer to save
        expect(rounds).to_have_value("")
        page.get_by_label("Minutes per session, builder").fill("60")
        pds.pick(page, "Layer", "project")
        expect(rounds).to_have_value("4")
        expect(page.locator("#pending")).to_have_text(
            "Unsaved: builder max rounds: inherited → 4. All projects: 1 more unsaved."
        )
        expect(page.locator("#save")).to_have_attribute("variant", "primary")
        pds.group(page, "checks")
        pds.pick(page, "When the design judge fails a change", "back")
        pds.group(page, "runs")  # the draft stays while another group shows
        expect(rounds).to_have_value("4")
        pds.group(page, "checks")
        labels = page.get_by_label("Labels, comma-separated; none for no labels")
        labels.fill("inherit")  # a label may be named so: typing it never means "inherit"
        expect(labels).to_have_value("inherit")
        labels.fill("release:minor, owlbear")
        pds.pick(page, "The line Opened by OwlBear Delivery", "off")
        looks = the_spotter_is_edited(page, pds)
        pds.group(page, "runs")
        at_once = page.get_by_label("Agent sessions at once in one project")  # TD-336
        expect(at_once).to_have_attribute("placeholder", "inherit (2)")
        at_once.fill("3")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        pds.group(page, "agents")
        a_list_keeps_its_text_as_typed_and_counts_only_new_items(page, looks)
        the_global_layer_kept_its_edit_and_takes_one_more(page, pds)
    project = store.read_config()
    assert (project.agents["builder"].max_rounds, project.design_failures, project.agents["builder"].minutes) == (
        4, "back", None
    )  # fmt: skip
    assert (project.pr_labels, project.pr_marker, project.sessions) == (["release:minor", "owlbear"], False, 3)
    assert (project.spotter.switch, project.spotter.looks, project.spotter.sample_rate) == (
        "off",
        ["hand-off", "sample"],
        5,
    )
    assert project.spotter.look_credit_limit == 0.05
    assert project.spotter.steer_share is None  # the rest still inherit
    assert not store.global_path.exists()


@pytest.mark.browser
def test_a_save_refused_by_a_newer_save_keeps_the_edits_and_the_next_save_lands(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        c = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1",
                       headers={"authorization": "Bearer t"})  # fmt: skip
        got = c.get("/api/next/config").json()
        newer = got["project"] | {"widths": [1600]}
        assert c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": newer}).status_code == 200
        pds.group(page, "runs")
        page.get_by_label("Minutes per session, reviewer").fill("25")
        page.get_by_label("Rounds at most, builder").fill("4")
        pds.group(page, "checks")  # D-01M63C92B83D61XFXTRXG8JAVB: edits in several groups, each group's counted
        pds.pick(page, "Merge method", "squash")
        unsaved = page.locator("#groups p-tag")
        expect(unsaved).to_have_text(["2 unsaved", "1 unsaved"])
        expect(page.locator("#groups a[href='#runs'] p-tag")).to_have_text("2 unsaved")
        save = page.get_by_role("region", name="Save settings").get_by_role("button", name="Save project settings")
        save.click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#error")).to_contain_text("kept your unsaved edits; check them and save again.")
        expect(unsaved).to_have_text(["2 unsaved", "1 unsaved"])
        expect(pds.select(page, "Merge method")).to_have_js_property("value", "squash")
        pds.group(page, "runs")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("25")
        save.click()  # the answered confirmation may still be fading out with its own button of this name
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        expect(unsaved).to_have_count(0)
    saved = json.loads(store.config_path.read_text())
    assert (saved["widths"], saved["agents"]["reviewer"]["minutes"]) == ([1600], 25)
    assert (saved["agents"]["builder"]["max_rounds"], saved["prefs"]["merge_method"]) == (4, "squash")  # one save


@pytest.mark.browser
def test_an_address_opens_its_group_and_an_unset_setting_s_link_its_row(store, pds, monkeypatch) -> None:
    """D-01M63C8QQMANY46N8GMNNKH1V9: each group has an address, back and forward follow them; an old address of a
    section or row opens its group there, and the overview's unset list links each setting's row (GW8RT6); a group
    with three or fewer unset names them all (D-01M66B6GS0HKACV9C4R4QKFX7T)."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"sessions": None}))
    with settings_page(store, pds) as page:
        url = page.url.split("#")[0]
        pds.group(page, "overview")
        expect(page.locator("#unset-runs")).to_have_text("Runs, 1 unset: sessions")
        expect(page.locator("#set-sessions p-text[color='error']")).to_have_count(0)  # not shown: another group
        page.locator("#unset").get_by_role("link", name="sessions", exact=True).click()
        expect(page).to_have_url(f"{url}#runs")
        at_once = page.get_by_label("Agent sessions at once in one project")
        expect(at_once).to_be_focused()
        named = page.locator("#set-sessions p-text[color='error']")
        expect(named).to_have_text("Agent sessions at once in one project")
        page.go_back()
        expect(page).to_have_url(f"{url}#overview")
        expect(page.locator("#unset")).to_be_visible()
        expect(at_once).to_have_count(0)
        page.go_forward()
        expect(page).to_have_url(f"{url}#runs")
        expect(page.locator("#rounds-title")).to_be_focused()  # a switch not made in the groups' list: its heading
        for old, group, focused in (
            ("set-prefs-merge_method", "checks", pds.select(page, "Merge method").get_by_role("combobox")),
            ("folder-title", "project", page.locator("#folder-title")),
            ("machine-title", "this-machine", page.locator("#machine-title")),
            ("spotter-title", "agents", page.locator("#spotter-title")),
        ):
            page.goto(f"{url}#{old}")
            expect(page).to_have_url(f"{url}#{group}")
            expect(page.locator(f"#groups a[href='#{group}']")).to_have_attribute("aria-current", "page")
            expect(focused).to_be_focused()
        for bad in ("%", "%E0%A4%A"):  # Sol R1-1: an address that doesn't decode opens the overview, loaded or not
            page.goto(f"{url}#runs")
            page.goto(f"{url}#{bad}")
            expect(page).to_have_url(f"{url}#overview")
            expect(page.locator("#unset")).to_be_visible()
            page.goto(f"{url}#{bad}")
            page.reload()
            expect(page).to_have_url(f"{url}#overview")
            expect(page.locator("#groups a[href='#overview']")).to_have_attribute("aria-current", "page")
            expect(page.locator("#unset")).to_be_visible()


@pytest.mark.browser
def test_the_overview_counts_each_group_s_unset_names_its_first_three_and_opens_the_group_for_more(
    store, pds, monkeypatch
) -> None:
    """D-01M66B6GS0HKACV9C4R4QKFX7T: the unset settings by group, each with its count and its first three, each linking
    its row, then "and N more" opening the group; a group with none is left out."""
    import re  # noqa: PLC0415

    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", None)
    with settings_page(store, pds) as page:
        url = page.url.split("#")[0]
        pds.group(page, "overview")
        groups = page.locator("#unset-groups > li")
        expect(groups).to_have_count(3)  # this machine's are set; the project's folder needs no setting
        expect(page.locator("#unset-project, #unset-this-machine, #unset-overview")).to_have_count(0)
        agents = page.locator("#unset-agents")
        expect(agents).to_have_text(
            re.compile(
                r"^Agents, (\d+) unset: agents\.planner\.model, agents\.planner\.effort, "
                r"agents\.planner\.context and \d+ more$"
            )
        )
        total = sum(_unset_count(page, group) for group in ("agents", "runs", "checks"))
        expect(page.locator("#unset > p-text").first).to_contain_text(f"{total} settings are unset.")
        for group in ("agents", "runs", "checks"):
            links = page.locator(f"#unset-{group} a")
            expect(links).to_have_count(4)
            expect(links.last).to_have_text(f"and {_unset_count(page, group) - 3} more")
            expect(links.last).to_have_attribute("href", f"#{group}")
        expect(agents.locator("a").first).to_have_attribute("href", "#set-agents-planner")
        page.locator("#unset-runs").get_by_role("link", name=re.compile(r"^and \d+ more$")).click()
        expect(page).to_have_url(f"{url}#runs")
        expect(page.locator("#groups a[href='#runs']")).to_have_attribute("aria-current", "page")
        expect(page.locator("#rounds-title")).to_be_focused()
        expect(page.locator("#set-sessions p-text[color='error']")).to_have_count(1)  # the group names every one red


# The most characters on one rendered line of an element's text, counted one character at a time.
LONGEST_LINE = """(el) => {
  const lines = new Map(), range = document.createRange(), walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    for (let i = 0; i < n.length; i++) {
      range.setStart(n, i);
      range.setEnd(n, i + 1);
      const r = range.getClientRects()[0];
      if (r && r.height > 1) lines.set(Math.round(r.top), (lines.get(Math.round(r.top)) ?? 0) + 1);
    }
  }
  return Math.max(...lines.values());
}"""


@pytest.mark.browser
def test_running_text_stops_at_about_75_characters_a_line_and_a_table_keeps_its_width(store, pds) -> None:
    """D-01M66D205WV75ZGAPVVYHCTADY: on a wide window a paragraph wraps at about 75 characters; a table does not."""
    with settings_page(store, pds) as page:
        text = page.get_by_role("region", name="Where you edit").locator("p-text", has_text="A blank project value")
        table = page.locator("p-table").first
        for width in (1280, 2400):
            page.set_viewport_size({"width": width, "height": 900})
            assert 65 <= text.evaluate(LONGEST_LINE) <= 80, width
            assert table.bounding_box()["width"] > 2 * text.bounding_box()["width"], width


@pytest.mark.browser
def test_the_owner_s_own_tab_after_an_unset_link_keeps_its_focus(store, pds, monkeypatch) -> None:
    """Copilot review of #813: the focus put on a linked row's control is never put back after the owner moves it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"sessions": None}))
    with settings_page(store, pds) as page:
        pds.group(page, "overview")
        # slow frames widen the time the page keeps the focus on the control, so a Tab lands inside it
        page.evaluate("window.requestAnimationFrame = (f) => setTimeout(() => f(performance.now()), 100)")
        page.locator("#unset").get_by_role("link", name="sessions", exact=True).click()
        at_once = page.get_by_label("Agent sessions at once in one project")
        expect(at_once).to_be_focused()
        page.keyboard.press("Tab")
        page.wait_for_timeout(1500)  # past every frame the page could still put the focus back in
        expect(at_once).not_to_be_focused()


# Set one task after the page read the offered models' body: its own handling of them, a chain of microtasks, has run.
MODELS_HANDLED = """
const json = Response.prototype.json;
Response.prototype.json = function () {
  const read = json.call(this);
  if (this.url.includes("/config/models")) read.then(() => setTimeout(() => { window.modelsHandled = true; }));
  return read;
};
"""


@pytest.mark.browser
def test_models_arriving_while_a_model_name_is_typed_wait_until_the_field_is_left(store, monkeypatch, pds) -> None:
    """Sol, TD-264: the offered models replace the typed field only once the owner leaves it."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    arrive = threading.Event()

    def slow(_self: object) -> dict[str, Any]:
        arrive.wait()  # released by the test once the field is in use, or by its cleanup
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
            page.add_init_script(MODELS_HANDLED)
            pds.only(page, base)
            page.goto(f"{base}/config#token=tok")
            pds.group(page, "agents")
            typed = page.locator('p-input-text[label="Model for builder"]').get_by_label("Model for builder")
            typed.click()
            typed.press_sequentially("my-model")
            expect(page.locator("#models-note")).to_contain_text("Reading the models")
            arrive.set()
            page.wait_for_function("window.modelsHandled === true")  # the models arrived while the field is in use
            typed.press_sequentially("-2")
            expect(typed).to_be_focused()
            expect(typed).to_have_value("my-model-2")
            pds.select(page, "Layer").get_by_role("combobox").focus()  # leaving the settings lets the models in
            expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
            chosen = pds.select(page, "Model for builder")
            expect(chosen).to_have_js_property("value", "my-model-2")
            said = "my-model-2 (not offered here)"
            expect(chosen.get_by_role("option", name=said, selected=True, include_hidden=True)).to_have_count(1)
            browser.close()
    finally:
        arrive.set()
        server.should_exit = True


@pytest.mark.browser
def test_models_arriving_during_a_save_apply_once_it_ends(store, monkeypatch, pds) -> None:
    """Sol, TD-264: a save under way when the models arrive leaves them for its end, never for good."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    arrive, saved = threading.Event(), threading.Event()

    def slow(_self: object) -> dict[str, Any]:
        arrive.wait(10)
        return MODELS

    monkeypatch.setattr(model_choices.Offered, "__call__", slow)
    real = config_routes._save  # noqa: SLF001 - the save the route runs

    def save(*args: Any, **kwargs: Any) -> str:
        arrive.set()  # the models answer while this save runs
        time.sleep(1.0)
        saved.set()
        return real(*args, **kwargs)

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
            pds.only(page, base)
            page.goto(f"{base}/config#token=tok")
            pds.group(page, "runs")
            page.get_by_label("Minutes per session, builder").fill("50")
            page.get_by_role("button", name="Save project settings").click()
            pds.answer(page, "Save project settings")
            expect(page.locator("#status")).to_have_text(
                "Saved this project's settings. They apply to the next session.", timeout=10_000
            )
            pds.group(page, "agents")
            expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
            expect(pds.select(page, "Model for builder")).to_be_visible()
            browser.close()
    finally:
        server.should_exit = True
    assert saved.is_set()


@pytest.mark.browser
def test_a_refresh_answered_after_a_save_keeps_the_saved_values(store, pds) -> None:
    """#810: a read's refresh that the host answered before a save, arriving after it, never shows the older layers."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        pds.group(page, "overview")
        expect(page.locator("#reads-status")).to_contain_text("Last read")
        held: list[tuple[Any, Any]] = []

        def hold(route: Any) -> None:
            if route.request.method != "GET" or held:
                route.continue_()
                return
            held.append((route, route.fetch()))  # the layers as they are before the save

        page.route("**/api/next/config", hold)
        page.locator("#read-again").click()
        for _ in range(200):  # the old layers are in hand before the save starts
            if held:
                break
            page.wait_for_timeout(50)
        assert held
        pds.group(page, "runs")
        page.get_by_label("Minutes per session, builder").fill("50")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        route, before = held[0]
        with page.expect_response("**/config/models"):  # the refresh goes on past the layers it read
            route.fulfill(response=before)
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("50")


@pytest.mark.browser
def test_a_refresh_begun_during_a_save_keeps_the_saved_values(store, pds, monkeypatch) -> None:
    """#810: a read answered while a save runs reloads the layers then; that older answer never replaces the save's."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    go = threading.Event()
    real = config_routes._save  # noqa: SLF001 - the save the route runs

    def save(*args: Any, **kwargs: Any) -> str:
        go.wait(30)
        return real(*args, **kwargs)

    monkeypatch.setattr(config_routes, "_save", save)
    with settings_page(store, pds) as page:
        pds.group(page, "overview")
        expect(page.locator("#reads-status")).to_contain_text("Last read")
        read: list[tuple[Any, Any]] = []
        layers: list[tuple[Any, Any]] = []

        def hold(into: list[tuple[Any, Any]], method: str) -> Callable[[Any], None]:
            def handle(route: Any) -> None:
                if route.request.method != method or into:
                    route.continue_()
                    return
                into.append((route, route.fetch()))

            return handle

        def held(into: list[tuple[Any, Any]]) -> tuple[Any, Any]:
            for _ in range(400):
                if into:
                    return into[0]
                page.wait_for_timeout(50)
            pytest.fail("the request never came")

        page.route("**/api/next/config/read", hold(read, "POST"))
        page.locator("#read-again").click()
        route, answer = held(read)
        pds.group(page, "runs")
        page.get_by_label("Minutes per session, builder").fill("50")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saving…")
        page.route("**/api/next/config", hold(layers, "GET"))
        route.fulfill(response=answer)  # the read's refresh starts while the save runs
        route, before = held(layers)  # the layers as they are before the save writes
        go.set()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        with page.expect_response("**/config/models"):  # the refresh goes on past the layers it read
            route.fulfill(response=before)
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("50")


@pytest.mark.browser
def test_with_no_layer_setting_anything_the_page_names_every_unset_value_and_a_save_fills_one(
    store, pds, monkeypatch
) -> None:
    """Code ships no defaults (2026-10-23): unset values are errors on the page, never filled from code."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", None)
    with settings_page(store, pds) as page:
        pds.group(page, "overview")
        expect(page.locator("#unset")).to_contain_text("settings are unset")
        agents, runs = _unset_count(page, "agents"), _unset_count(page, "runs")
        pds.group(page, "runs")
        at_once = page.get_by_label("Agent sessions at once in one project")
        expect(at_once).to_have_attribute("placeholder", "inherit (unset)")
        at_once.fill("3")
        pds.group(page, "agents")
        pds.pick(page, "Model for spotter", "tiny")  # one tier and no efforts: both still fillable
        expect(page.locator("#agents-rows")).to_contain_text("no layer sets a context tier")
        page.locator("#agents-rows").get_by_role("button", name="Use the default tier").click()
        pds.pick(page, "Effort for spotter", "medium")
        pds.pick(page, "Model for reviewer", "claude-opus-5.5")  # its effort unset: listed, never blocking the save
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        pds.group(page, "overview")
        expect(page.locator("#unset-runs")).to_contain_text(f"Runs, {runs - 1} unset:")  # sessions
        expect(page.locator("#unset-agents")).to_contain_text(
            f"Agents, {agents - 4} unset:"
        )  # spotter's three, a model
        pds.group(page, "agents")
        for key in ("switch", "irreversible_harm"):  # its settings start unset too: their names stay red
            expect(page.locator(f"#set-spotter-{key} p-text[color='error']")).to_have_count(1)
        expect(page.locator("#set-agents-spotter p-text[color='error']")).to_have_count(0)
    assert store.read_config().sessions == 3
    spotter = store.settings().agent("spotter")  # a look needs only its model, effort and context
    assert (spotter.model, spotter.effort, spotter.context) == ("tiny", "medium", "default")


def _layered(store: Store, monkeypatch, glob: dict, machine: dict, project: dict) -> None:
    """Only these three layers set anything: no built-in layer under Global."""
    from owlbear_delivery_next.settings import config  # noqa: PLC0415
    from owlbear_delivery_next.state_store import machine_settings  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", None)
    monkeypatch.setattr(machine_settings, "BASE", None)
    for path, model, values in ((store.global_path, config.GlobalLayer, glob),
                                (store.machine_path, config.MachineLayer, machine),
                                (store.config_path, config.Layer, project)):  # fmt: skip
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_validate(values).model_dump_json())


GLOBAL = {
    "sessions": 2,
    "pr_marker": True,
    "spotter": {"looks": ["hand-off"]},
    "agents": {"builder": {"model": "claude-opus-5.5", "effort": "high", "context": "long", "minutes": 40}},
}


def _option(page, pds, label: str) -> Any:
    """The option that clears the shown layer's value in the select labelled *label*."""
    return pds.select(page, label).locator('p-select-option[value="inherit"]')


WARNED = "Unset: every machine or project must then set its own"


def global_s_agents_clear_to_unset_and_warn_where_needed(page, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.pick(page, "Layer", "global")
    expect(_option(page, pds, "Model for builder")).to_have_text("Unset")
    expect(_option(page, pds, "Effort for builder")).to_have_text("Unset")
    builder = page.locator("#set-agents-builder")
    expect(builder.get_by_role("button", name="Unset")).to_be_visible()  # its own long context
    expect(builder.locator("p-text[color='warning']")).to_have_count(0)
    expect(page.locator("#set-agents-planner")).to_contain_text(WARNED)
    expect(_option(page, pds, "Built-in subagents, builder")).to_have_text("Unset")
    expect(_option(page, pds, "On or off")).to_have_text("Unset")  # the Spotter's switch
    expect(page.locator("#set-spotter-switch")).to_contain_text(WARNED)
    expect(page.get_by_label("Looks", exact=True)).to_have_value("hand-off")
    for unneeded in ("verbose_until", "sample_rate"):  # never needed; needed only for a sample look
        expect(page.locator(f"#set-spotter-{unneeded} p-text[color='warning']")).to_have_count(0)
    expect(_option(page, pds, INSTRUCTIONS)).to_have_text("Unset")


def global_s_runs_and_checks_clear_to_unset_and_warn_where_needed(page, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.group(page, "runs")
    expect(page.get_by_label("Rounds at most, final review")).to_have_attribute("placeholder", "Unset")
    expect(page.locator("#set-rounds-final_review")).to_contain_text("Unset: it then takes the builder's value")
    threshold = page.get_by_label("Curator's confidence threshold in percent (50 to 100)")
    expect(threshold).to_have_attribute("placeholder", "Unset")
    expect(page.locator("#set-curator_threshold")).to_contain_text(
        "Unset: no machine or project can set it, so it stays unset"
    )
    at_once = page.get_by_label("Agent sessions at once in one project")
    expect(at_once).to_have_attribute("placeholder", "Unset")
    expect(page.locator("#set-sessions p-text[color='warning']")).to_have_count(0)
    at_once.fill("")  # the warning follows the edit, before any save
    expect(page.locator("#set-sessions")).to_contain_text(WARNED)
    expect(page.locator("#pending")).to_contain_text("sessions: 2 → unset")
    at_once.fill("2")
    expect(page.locator("#set-sessions p-text[color='warning']")).to_have_count(0)
    pds.group(page, "checks")
    widths = page.get_by_label("Screenshot widths in px, comma-separated (1280 to 2400)")
    expect(widths).to_have_attribute("placeholder", "Unset")
    expect(_option(page, pds, "When the design judge fails a change")).to_have_text("Unset")
    expect(_option(page, pds, "Merge method")).to_have_text("Unset")
    expect(page.get_by_label("CI poll interval (seconds)")).to_have_attribute("placeholder", "Unset")
    expect(page.get_by_label(LABELS)).to_have_attribute("placeholder", "Unset")
    expect(page.locator("#set-pr_labels")).to_contain_text(WARNED)
    expect(_option(page, pds, "The line Opened by OwlBear Delivery")).to_have_text("Unset")
    expect(page.locator("#set-pr_marker p-text[color='warning']")).to_have_count(0)


def the_machine_and_the_project_inherit_and_never_warn(page, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    warnings, labels = page.locator("main p-text[color='warning']"), page.get_by_label(LABELS)
    at_once = page.get_by_label("Agent sessions at once in one project")
    pds.pick(page, "Layer", "machine")
    expect(warnings).to_have_count(0)
    expect(labels).to_have_attribute("placeholder", "inherit (unset)")
    expect(_option(page, pds, "The line Opened by OwlBear Delivery")).to_have_text("inherit (on)")
    pds.group(page, "runs")
    expect(at_once).to_have_attribute("placeholder", "inherit (2)")
    pds.pick(page, "Layer", "project")
    expect(warnings).to_have_count(0)
    expect(at_once).to_have_attribute("placeholder", "inherit (3)")
    pds.group(page, "checks")
    expect(labels).to_have_attribute("placeholder", "inherit (m)")
    pds.group(page, "agents")
    expect(_option(page, pds, "Model for builder")).to_have_text("inherit (claude-opus-5.5)")
    page.locator("#set-agents-builder p-segmented-control-item[value=default]").click()
    expect(page.locator("#set-agents-builder").get_by_role("button", name="Use inherited")).to_be_visible()


def with_the_models_unread_a_typed_name_and_a_chosen_tier_clear_alike(page, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    held = []

    def hold(route) -> None:
        held.append(route)  # this machine's models stay unread: typed names, chosen tiers

    page.route("**/config/models", hold)
    page.reload()
    pds.pick(page, "Layer", "global")
    typed = page.locator('p-input-text[label="Model for planner"]').get_by_label("Model for planner")
    expect(typed).to_have_attribute("placeholder", "Unset")
    expect(_option(page, pds, "Context for planner")).to_have_text("Unset")
    pds.pick(page, "Layer", "project")
    expect(typed).to_have_attribute("placeholder", "inherit (unset)")
    expect(_option(page, pds, "Context for builder")).to_have_text("inherit (long)")
    expect(page.locator("main p-text[color='warning']")).to_have_count(0)


@pytest.mark.browser
def test_global_s_clear_option_is_unset_and_warns_while_the_other_layers_inherit(store, pds, monkeypatch) -> None:
    """D-01M61SEXPFT9MXZGQHYVYFQ77C: nothing lies under Global, so clearing its value leaves it unset, which each
    needed setting warns about; a machine or a project clears to what it inherits and never warns."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _layered(store, monkeypatch, GLOBAL, {"sessions": 3, "pr_labels": ["m"]}, {"sessions": 4})
    with settings_page(store, pds) as page:
        expect(page.locator("main p-text[color='warning']")).to_have_count(0)  # This project
        global_s_agents_clear_to_unset_and_warn_where_needed(page, pds)
        global_s_runs_and_checks_clear_to_unset_and_warn_where_needed(page, pds)
        the_machine_and_the_project_inherit_and_never_warn(page, pds)
        with_the_models_unread_a_typed_name_and_a_chosen_tier_clear_alike(page, pds)


def _in_use(page, row: str) -> Any:
    """The in-use line of the setting row *row*."""
    return page.locator(f"#{row} p-text[size='xs']").filter(has_text="in use")


def the_project_s_edit_shows_what_its_save_would_give(page, pds) -> None:
    """Each layer below the project in turn, then the project's own value again once the edit is undone."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.group(page, "runs")
    at_once, line = page.get_by_label("Agent sessions at once in one project"), _in_use(page, "set-sessions")
    expect(line).to_have_text("in use: 4, from this project")
    at_once.fill("")
    expect(line).to_have_text("in use: 3, from this machine")  # the machine's, not Global's 2
    at_once.fill("6")
    expect(line).to_have_text("in use: 6, from this project")
    pds.pick(page, "Layer", "global")  # another layer's draft is no edit of the shown one
    expect(line).to_have_text("in use: 4, from this project")
    pds.pick(page, "Layer", "project")
    at_once.fill("4")
    expect(line).to_have_text("in use: 4, from this project")
    expect(page.locator("#pending")).to_have_text("No unsaved edits.")
    final = _in_use(page, "set-rounds-final_review")
    rounds = page.get_by_label("Rounds at most, final review")
    rounds.fill("")
    expect(final.first).to_have_text("in use: 3, from the builder's value")
    rounds.fill("2")
    expect(final.first).to_have_text("in use: 2, from this project")
    pds.group(page, "checks")
    marker = _in_use(page, "set-pr_marker")
    expect(marker).to_have_text("in use: no, from this project")
    pds.pick(page, "The line Opened by OwlBear Delivery", "inherit")
    expect(marker).to_have_text("in use: yes, from global")
    pds.pick(page, "The line Opened by OwlBear Delivery", "off")
    expect(marker).to_have_text("in use: no, from this project")


def the_machine_s_edit_shows_what_its_save_would_give(page, pds) -> None:
    """A machine edit shows where no project value masks it; the project's line never counts the machine's draft."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.pick(page, "Layer", "machine")
    pds.group(page, "checks")
    labels, line = page.get_by_label(LABELS), _in_use(page, "set-pr_labels")
    expect(line).to_have_text("in use: m, from this machine")
    labels.fill("")
    expect(line).to_have_text("in use: unset")  # Global sets none
    labels.fill("a")
    expect(line).to_have_text("in use: a, from this machine")
    labels.fill("m")
    expect(line).to_have_text("in use: m, from this machine")
    pds.group(page, "runs")
    at_once, sessions = page.get_by_label("Agent sessions at once in one project"), _in_use(page, "set-sessions")
    at_once.fill("6")
    expect(sessions).to_have_text("in use: 4, from this project")  # the project's own masks it
    pds.pick(page, "Layer", "project")
    at_once.fill("")
    expect(sessions).to_have_text("in use: 3, from this machine")  # the machine's saved 3, not its unsaved 6
    at_once.fill("4")
    pds.pick(page, "Layer", "machine")
    at_once.fill("3")
    expect(page.locator("#pending")).to_have_text("No unsaved edits.")


def global_s_edit_shows_what_its_save_would_give(page, pds) -> None:
    """A builder's value fills the final review's unset one; the curator's threshold; the Spotter's sample rate is
    needed only while the looks include a sample."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.pick(page, "Layer", "global")
    pds.group(page, "runs")
    findings = page.get_by_label("New findings per round at most, builder")
    final = page.locator("#set-rounds-final_review")
    expect(final.get_by_text("in use", exact=False)).to_have_count(3)  # its findings: unset, the builder's too
    findings.fill("5")
    expect(final).to_contain_text("in use: 5, from the builder's value")
    findings.fill("")
    expect(final.get_by_text("in use", exact=False)).to_have_count(3)
    threshold = page.get_by_label("Curator's confidence threshold in percent (50 to 100)")
    line = _in_use(page, "set-curator_threshold")
    expect(line).to_have_count(0)
    threshold.fill("90")
    expect(line).to_have_text("in use: 90, from global")
    threshold.fill("")
    expect(line).to_have_count(0)
    pds.group(page, "agents")
    looks, sample = page.get_by_label("Looks", exact=True), page.locator("#set-spotter-sample_rate")
    expect(sample.locator("p-text[color='warning']")).to_have_count(0)
    looks.fill("hand-off, sample")
    expect(_in_use(page, "set-spotter-looks")).to_have_text("in use: hand-off, sample, from global")
    expect(sample).to_contain_text("Unset: every machine or project must then set its own")
    looks.fill("hand-off")
    expect(sample.locator("p-text[color='warning']")).to_have_count(0)
    builder = page.locator("#set-agents-builder")
    pds.pick(page, "Effort for builder", "low")  # no lower layer sets it
    expect(builder).to_contain_text("in use: low, from global")
    pds.pick(page, "Effort for builder", "inherit")
    expect(builder).to_contain_text("in use: unset")
    pds.pick(page, "Effort for builder", "high")
    expect(builder).not_to_contain_text("in use: unset")
    expect(page.locator("#pending")).to_have_text("No unsaved edits.")


@pytest.mark.browser
def test_the_in_use_line_follows_an_unsaved_edit_and_returns_once_it_is_undone(store, pds, monkeypatch) -> None:
    """#809: the line under a setting says what saving the shown layer would give, from the layers as they are saved
    and that layer's own edits; another layer's edits never show there."""
    builder = {"max_rounds": 3, "last_round_at": 1, "ask_owner_at": 4}
    glob = GLOBAL | {"agents": {"builder": GLOBAL["agents"]["builder"] | builder}}
    final = {"max_rounds": 2, "last_round_at": 1, "ask_owner_at": 3}
    machine = {"sessions": 3, "pr_labels": ["m"]}
    _layered(store, monkeypatch, glob, machine, {"sessions": 4, "pr_marker": False, "final_review": final})
    with settings_page(store, pds) as page:
        the_project_s_edit_shows_what_its_save_would_give(page, pds)
        the_machine_s_edit_shows_what_its_save_would_give(page, pds)
        global_s_edit_shows_what_its_save_would_give(page, pds)


@pytest.mark.browser
def test_the_curator_threshold_shows_read_only_with_its_value_off_global(store, pds, monkeypatch) -> None:
    """#809: every layer shows the curator's threshold; one that can't hold it shows the saved value read-only, with
    its in-use line and where it is set; its unset link focuses the row; Global's unsaved edit stays Global's."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _layered(store, monkeypatch, GLOBAL, {}, {})
    with settings_page(store, pds) as page:
        threshold = page.get_by_label("Curator's confidence threshold in percent (50 to 100)")
        row, line = page.locator("#set-curator_threshold"), _in_use(page, "set-curator_threshold")
        url = page.url.split("#")[0]
        pds.group(page, "overview")
        expect(page.locator("#unset-runs")).to_contain_text("unset")
        page.goto(f"{url}#set-curator_threshold")  # an unset link's address; Runs lists only its first three
        expect(row).to_be_focused()  # the disabled field can't take the focus
        expect(threshold).to_be_disabled()
        expect(threshold).to_have_attribute("placeholder", "unset")
        expect(row).to_contain_text("set on Global")
        pds.pick(page, "Layer", "global")
        expect(threshold).to_be_enabled()
        expect(row).not_to_contain_text("set on Global")
        threshold.fill("90")
        _saved(page, pds, "Save global defaults", "the global")
        for layer in ("project", "machine"):
            pds.pick(page, "Layer", layer)
            expect(threshold).to_be_disabled()
            expect(threshold).to_have_value("90")
            expect(line).to_have_text("in use: 90, from global")
            expect(row).to_contain_text("set on Global")
        pds.pick(page, "Layer", "global")
        threshold.fill("95")
        expect(line).to_have_text("in use: 95, from global")
        pds.pick(page, "Layer", "project")
        expect(threshold).to_have_value("90")
        expect(line).to_have_text("in use: 90, from global")
        expect(page.locator("#pending")).to_contain_text("All projects: 1 more unsaved")  # Global's edit is kept


@pytest.mark.browser
def test_merge_and_cleanup_preferences_save_reload_and_clear_back_to_inherit(store, pds) -> None:
    """R15: the five optional preferences save into the shown layer, survive a reload, and clear to inherit."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        pds.group(page, "checks")
        pds.pick(page, "Merge method", "squash")
        page.get_by_label("CI poll interval (seconds)").fill("45")
        pds.pick(page, "Ask before merging", "on")
        page.get_by_role("button", name="Save project settings").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        page.reload()
        opened(page, pds, "checks")
        expect(page.get_by_label("CI poll interval (seconds)")).to_have_value("45")
        pds.pick(page, "Merge method", "inherit")  # the inherit choice clears the layer's own value
        page.get_by_role("button", name="Save project settings").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    prefs = store.read_config().prefs
    assert prefs.merge_method is None
    assert (prefs.ci_poll_seconds, prefs.ask_before_merge) == (45, True)


INSTRUCTIONS, SKILLS = "Your instructions in Delivery steps", "Your skills in Delivery steps"
LABELS = "Labels, comma-separated; none for no labels"
MEMORY = "Copilot Memory in Delivery sessions"
USER_KEYS = ("load_user_instructions", "load_user_skills", "load_user_memory")


def _saved(page, pds, button: str, whose: str) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page.locator(".bar").get_by_role("button", name=button).click()
    pds.answer(page, button)
    expect(page.locator("#status")).to_have_text(f"Saved {whose} settings. They apply to the next session.")


def _saved_by_keyboard(page, pds, button: str, whose: str) -> None:
    """As _saved, and the save's dialog holds the keyboard focus until it closes, then gives it back to the bar."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page.locator(".bar").get_by_role("button", name=button).click()
    expect(pds.modal(page)).to_be_visible()
    inside = "document.activeElement?.closest('p-modal') !== null"
    page.wait_for_function(inside, timeout=5000)
    for _ in range(6):  # the page behind is inert
        page.keyboard.press("Tab")
        assert page.evaluate(f"{inside} || document.activeElement === document.body")
    pds.answer(page, button)
    expect(page.locator("#status")).to_have_text(f"Saved {whose} settings. They apply to the next session.")
    page.wait_for_function("document.activeElement?.closest('.bar') !== null", timeout=5000)


def _user_layers(store: Store) -> tuple[list[list[bool | None]], list[tuple[bool, str]]]:
    """Each layer's own user-config values, and each value in use with the layer it comes from."""
    from owlbear_delivery_next.settings import config  # noqa: PLC0415
    from owlbear_delivery_next.state_store.store import read_layer  # noqa: PLC0415

    layers = (store.read_config(), read_layer(store.machine_path, config.MachineLayer),
              read_layer(store.global_path, config.GlobalLayer))  # fmt: skip
    resolved = store.settings()
    return [[getattr(layer, k) for k in USER_KEYS] for layer in layers], [
        (getattr(resolved, k), resolved.sources[k]) for k in USER_KEYS
    ]


@pytest.mark.browser
def test_the_user_config_switches_save_in_each_layer_reload_and_clear_back_to_inherit(store, pds, monkeypatch) -> None:
    """D-01M5YE4P5317N1HWD0QN6N05E0, D-01M69EBRBBW97001KZ43C0BJM1: no default; Global, this machine and the project
    set them; the project wins."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update=dict.fromkeys(USER_KEYS)))
    with settings_page(store, pds) as page:
        shown = page.locator("#user-config")
        pds.group(page, "overview")
        expect(page.locator("#unset")).to_contain_text(", ".join(USER_KEYS))
        pds.group(page, "agents")
        for key in USER_KEYS:  # GW8RT6: a red name, no line saying it is unset
            expect(page.locator(f"#set-{key} p-text[color='error']")).to_have_count(1)
        expect(shown).not_to_contain_text("unset: set it here")
        pds.pick(page, "Layer", "global")
        expect(shown).to_contain_text("Unset")
        pds.pick(page, INSTRUCTIONS, "off")
        pds.pick(page, SKILLS, "off")
        pds.pick(page, MEMORY, "off")
        box = pds.select(page, MEMORY).get_by_role("combobox").bounding_box()
        assert min(box["width"], box["height"]) >= 24  # WCAG 2.5.8 target size
        _saved_by_keyboard(page, pds, "Save global defaults", "the global")
        pds.pick(page, "Layer", "machine")
        expect(pds.select(page, INSTRUCTIONS)).to_have_js_property("value", "inherit")
        expect(shown).to_contain_text("inherit (off)")
        pds.pick(page, INSTRUCTIONS, "on")
        pds.pick(page, MEMORY, "on")
        _saved(page, pds, "Save this machine's preferences", "this machine's")
        pds.pick(page, "Layer", "project")
        pds.pick(page, SKILLS, "on")
        _saved(page, pds, "Save project settings", "this project's")
        expect(page.locator("#user-config p-text[color='error']")).to_have_count(0)
        pds.group(page, "overview")
        expect(page.locator("#unset")).to_have_count(0)
        expect(page.locator("#unset-none")).to_be_visible()

        page.reload()
        opened(page, pds)
        expect(pds.select(page, INSTRUCTIONS)).to_have_js_property("value", "inherit")
        expect(pds.select(page, SKILLS)).to_have_js_property("value", "on")
        expect(pds.select(page, MEMORY)).to_have_js_property("value", "inherit")
        expect(page.locator("#set-load_user_memory")).to_contain_text("in use: on, from this machine")
        expect(shown).to_contain_text("in use: on, from this machine")
        expect(shown).to_contain_text("in use: on, from this project")
        pds.pick(page, SKILLS, "inherit")  # the project's own value is cleared: Global's off applies again
        _saved(page, pds, "Save project settings", "this project's")
        expect(shown).to_contain_text("in use: off, from global")
        pds.pick(page, "Layer", "machine")
        pds.pick(page, MEMORY, "inherit")  # the machine's own value is cleared: Global's off applies again
        _saved(page, pds, "Save this machine's preferences", "this machine's")
        expect(page.locator("#set-load_user_memory")).to_contain_text("in use: off, from global")
    assert _user_layers(store) == (
        [[None, None, None], [True, None, None], [False, False, False]],  # project, this machine, Global
        [(True, "machine"), (False, "global"), (False, "global")],  # in use, and from where
    )


CATEGORY_LABELS = {
    "hand_off_fitness": "Hand-off fitness",
    "course_and_constraints": "Course and constraints",
    "outside_state_changes": "Outside-state changes",
    "irreversible_harm": "Irreversible harm",
}


@pytest.mark.browser
def test_each_category_offers_its_allowed_actions_saves_reloads_and_clears_to_the_wider_value(store, pds) -> None:
    """The four categories' actions (D-01M5WP8Z4ADZ5FN7RJDR17RQQ5): the server's matrix, layered field by field."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        for field, label in CATEGORY_LABELS.items():
            select = pds.select(page, label)
            expect(select).to_have_count(1)
            offered = select.locator("p-select-option").evaluate_all("os => os.map((o) => o.value)")
            category = next(c for c, f in CATEGORIES.items() if f == field)
            assert offered == ["inherit", *ALLOWED[category]], field
        pds.pick(page, "Hand-off fitness", "refuse-hand-off")
        pds.pick(page, "Irreversible harm", "stop-and-ask")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        page.reload()
        opened(page, pds)
        expect(page.locator("#spotter")).to_contain_text("in use: refuse-hand-off, from this project")
        expect(page.locator("#spotter")).to_contain_text("in use: stop-and-ask, from this project")
        pds.pick(page, "Hand-off fitness", "inherit")  # clears the project's own value
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    project = store.read_config().spotter
    assert (project.hand_off_fitness, project.irreversible_harm) == (None, "stop-and-ask")
    resolved = store.settings()
    assert (resolved.spotter.hand_off_fitness, resolved.sources["spotter.hand_off_fitness"]) == ("record", "default")
    assert (resolved.spotter.irreversible_harm, resolved.sources["spotter.irreversible_harm"]) == (
        "stop-and-ask", "project")  # fmt: skip


def _refuse_config_once(monkeypatch, config_path: Path) -> None:
    """The remote refuses the first publication of the project settings file; later ones are real."""
    real, refused = data_repo.DataRepo.publish, []

    def refuse(self, path, message, until=None):
        if path == config_path and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(data_repo.DataRepo, "publish", refuse)


@pytest.fixture
def pending_shared(tmp_path: Path, monkeypatch, shared_repo) -> Store:
    """A shared project whose legacy preference import is pending: its review is what Settings must complete."""
    monkeypatch.setattr(model_choices.Offered, "__call__", lambda _self: MODELS)
    root, _remote = shared_repo
    s = Store(tmp_path / "store", data_repo.DataRepo(root), "shop-site")
    s.global_path = tmp_path / "global" / "config.json"
    s.write_profile(Profile())
    s.mark_prefs_import("", "pending", "absent")
    return s


def _fresh(tmp_path: Path, remote: Path) -> Store:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    return Store(tmp_path / "fresh-store", data_repo.DataRepo(second), "shop-site")


@pytest.mark.browser
def test_a_refused_save_of_an_edited_preference_keeps_the_review_until_the_retry_publishes(
    pending_shared, tmp_path, monkeypatch, shared_repo, pds
) -> None:
    """A failed publication notice keeps the owner's review intent, so the plain retry settles the import."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _refuse_config_once(monkeypatch, pending_shared.config_path)
    with settings_page(pending_shared, pds) as page:
        pds.group(page, "checks")
        pds.pick(page, "Merge method", "squash")
        page.get_by_role("button", name="Save project settings").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_be_visible()
        assert pending_shared.read_profile().prefs_import == "pending"
        page.locator("#save").click()  # the retry carries no new edit
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    assert pending_shared.read_profile().prefs_import == "done"
    assert _fresh(tmp_path, shared_repo[1]).read_config().prefs.merge_method == "squash"


@pytest.mark.browser
def test_a_refused_save_of_an_already_empty_clear_keeps_the_review_until_the_retry_publishes(
    pending_shared, tmp_path, monkeypatch, shared_repo, pds
) -> None:
    """Clearing a preference that is already empty is still a review, and the retry must not drop it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _refuse_config_once(monkeypatch, pending_shared.config_path)
    with settings_page(pending_shared, pds) as page:
        pds.group(page, "checks")
        pds.pick(page, "Merge method", "inherit")  # already inherited: no draft, only the review
        page.get_by_role("button", name="Save project settings").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_be_visible()
        assert pending_shared.read_profile().prefs_import == "pending"
        page.locator("#save").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    assert pending_shared.read_profile().prefs_import == "done"
    assert _fresh(tmp_path, shared_repo[1]).read_profile().prefs_import == "done"


@pytest.mark.browser
def test_a_pending_import_is_settled_by_the_explicit_review_action_without_inventing_a_value(
    pending_shared, tmp_path, monkeypatch, shared_repo, pds
) -> None:
    """With no edit, the review button settles a pending import; a refused publication keeps it until a retry."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _refuse_config_once(monkeypatch, pending_shared.config_path)
    with settings_page(pending_shared, pds) as page:
        review = page.get_by_role("button", name="Confirm merge preferences reviewed")
        expect(review).to_be_visible()
        review.click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_be_visible()
        assert pending_shared.read_profile().prefs_import == "pending"
        review.click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(review).to_have_count(0)
    assert pending_shared.read_profile().prefs_import == "done"
    assert _fresh(tmp_path, shared_repo[1]).read_config().prefs is None


def _project_puts(page) -> list[dict]:
    """Every project settings save the page sends, as its JSON body."""
    sent: list[dict] = []
    page.on(
        "request",
        lambda r: (
            sent.append(json.loads(r.post_data)) if r.method == "PUT" and r.url.endswith("/config/project") else None
        ),
    )
    return sent


@pytest.mark.browser
def test_a_cancelled_review_is_not_sent_with_a_later_unrelated_save(pending_shared, pds) -> None:
    """Keep editing on the review's confirmation is no review: a later unrelated save leaves the import pending."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(pending_shared, pds) as page:
        sent = _project_puts(page)
        page.get_by_role("button", name="Confirm merge preferences reviewed").click()
        pds.modal(page).get_by_role("button", name="Keep editing").click()
        expect(page.get_by_role("dialog")).to_have_count(0)  # the page takes edits again once it has closed
        pds.group(page, "runs")
        page.get_by_label("Rounds at most, builder").fill("4")
        expect(page.locator("#pending")).to_contain_text("builder max rounds: inherited → 4")
        page.locator("#save").click()  # the cancelled confirmation may still be fading out
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        expect(page.get_by_role("button", name="Confirm merge preferences reviewed")).to_be_visible()

    assert [body["prefs_reviewed"] for body in sent] == [False]
    assert pending_shared.read_profile().prefs_import == "pending"
    assert pending_shared.read_config().agents["builder"].max_rounds == 4


@pytest.mark.browser
def test_an_earlier_preference_edit_stays_a_review_after_a_cancelled_review_button(pending_shared, pds) -> None:
    """Cancelling the review button never drops an earlier preference edit's review: its save still settles."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(pending_shared, pds) as page:
        sent = _project_puts(page)
        pds.group(page, "checks")
        pds.pick(page, "Merge method", "squash")
        page.get_by_role("button", name="Confirm merge preferences reviewed").click()
        pds.modal(page).get_by_role("button", name="Keep editing").click()
        expect(page.get_by_role("dialog")).to_have_count(0)  # the page takes edits again once it has closed
        page.locator("#save").click()  # the cancelled confirmation may still be fading out
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")

    assert [body["prefs_reviewed"] for body in sent] == [True]
    assert pending_shared.read_profile().prefs_import == "done"
    assert pending_shared.read_config().prefs.merge_method == "squash"


@pytest.mark.browser
def test_a_refused_save_offers_its_retry_only_once_it_has_settled(pending_shared, monkeypatch, pds) -> None:
    """While a save runs, no earlier notice stands as its outcome; once it settles, the offered retry is taken."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _refuse_config_once(monkeypatch, pending_shared.config_path)
    with settings_page(pending_shared, pds) as page:
        sent, held = _project_puts(page), []

        def hold_first_put(route) -> None:
            if route.request.method == "PUT" and not held:
                held.append(route)  # the refused save stays in flight until the test lets it go
            else:
                route.fallback()

        page.route("**/api/next/config/project", hold_first_put)
        expect(page.locator("#error")).to_be_visible()  # the page's standing notice of the pending import
        pds.group(page, "checks")
        pds.pick(page, "Merge method", "squash")
        page.locator("#save").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        page.wait_for_function("() => document.querySelector('#save')?.loading === true")
        expect(page.locator("#status")).to_have_text("Saving…")
        expect(page.locator("#error")).to_be_hidden()  # nothing offers a retry the running save would ignore

        held[0].fallback()
        expect(page.locator("#error")).to_be_visible()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        assert page.evaluate("() => document.querySelector('#save').loading") is False
        assert pending_shared.read_profile().prefs_import == "pending"

        page.locator("#save").click()  # the offered retry carries no new edit and is taken
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_be_hidden()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")

    assert [body["prefs_reviewed"] for body in sent] == [True, True]
    assert pending_shared.read_profile().prefs_import == "done"


def _rates(inp: float, out: float, cache: float, write: float, hour: float | None = None) -> dict[str, float | None]:
    return {"input": inp, "output": out, "cache": cache, "cache_write": write, "cache_write_1h": hour}


PRICED = {
    "models": [
        {"id": "cache-only", "name": "Cache", "efforts": ["low", "high"], "default_effort": "low", "context": 200_000,
         "rates": _rates(200, 1000, 10, 250), "long": {"context": 1_000_000, "rates": _rates(200, 1000, 20, 250)}},
        {"id": "claude-opus-5.5", "name": "Opus", "efforts": ["low", "high"], "default_effort": "low",
         "context": 200_000, "rates": _rates(300, 1500, 30, 375, 800),
         "long": {"context": 1_000_000, "rates": _rates(300, 1500, 30, 375, 800)}},
        {"id": "unpriced", "name": "Unpriced", "efforts": [], "default_effort": "", "context": 200_000, "rates": None,
         "long": {"context": 1_000_000, "rates": None}},
        {"id": "crossing", "name": "Crossing", "efforts": [], "default_effort": "", "context": 200_000,
         "rates": _rates(200, 1000, 20, 250), "long": {"context": 1_000_000, "rates": _rates(400, 1000, 10, 250)}},
    ],
    "error": "",
}  # fmt: skip
RANKS = """async () => {
  const { levels, arrows } = await import("/assets/page/config/cost.mjs");
  const base = { input: 2, output: 8, cache: 1, cache_write: 3, cache_write_1h: 4 };
  const up = (key) => ({ ...base, [key]: base[key] + 1 });
  const [cheap, middle, dear] = [base, up("output"), { ...base, input: 9, output: 9 }];
  return {
    equal: levels([base, { ...base }]),
    single: ["cache", "cache_write", "cache_write_1h"].map((key) => levels([base, up(key)])),
    three: levels([middle, dear, cheap]),
    repeated: levels([cheap, { ...cheap }, middle]),
    unknown: levels([null, cheap, middle]),
    crossing: levels([{ ...base, input: 2, output: 1 }, { ...base, input: 1, output: 2 }]),
    arrows: [0, 1, 2].map(arrows),
  };
}"""


@pytest.mark.browser
def test_cost_arrows_rank_every_rate_and_leave_models_efforts_and_rates_unmarked(store, pds, monkeypatch) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setattr(model_choices.Offered, "__call__", lambda _self: PRICED)
    with settings_page(store, pds) as page:
        row = page.locator("#set-agents-builder")
        tier = row.locator("p-segmented-control-item")
        pds.pick(page, "Model for builder", "cache-only")  # only its long tier's cache read is higher
        expect(tier.and_(page.locator("[value=long]"))).to_have_text("1M\u00a0\u2191")
        expect(tier.and_(page.locator("[value=default]"))).to_have_text("200k")
        for label in ("Model for builder", "Effort for builder"):
            options = pds.select(page, label).locator("p-select-option")
            expect(options).not_to_have_count(0)
            assert not any("\u2191" in said for said in options.all_inner_texts()), label
        rates = row.locator("p-table-cell").last
        expect(rates).to_contain_text("in 200 \u00b7 out 1,000 \u00b7 cache 10 \u00b7 cache write 250")
        expect(rates).not_to_contain_text("\u2191")
        pds.pick(page, "Model for builder", "claude-opus-5.5")  # its tiers are priced equally
        expect(tier).to_have_text(["200k", "1M"])
        expect(row).not_to_contain_text("\u2191")
        pds.pick(page, "Model for builder", "unpriced")
        expect(tier).to_have_text(["200k", "1M"])
        expect(row).not_to_contain_text("\u2191")
        expect(rates).to_contain_text("not known")
        pds.pick(page, "Model for builder", "crossing")  # each tier is higher in one rate
        expect(tier).to_have_text(["200k\u00a0\u2191", "1M\u00a0\u2191"])
        ranks = page.evaluate(RANKS)
    assert ranks == {
        "equal": [0, 0], "single": [[0, 1]] * 3, "three": [1, 2, 0], "repeated": [0, 0, 1], "unknown": [0, 0, 1],
        "crossing": [1, 1], "arrows": ["", "\u00a0\u2191", "\u00a0\u2191\u2191"],
    }  # fmt: skip
