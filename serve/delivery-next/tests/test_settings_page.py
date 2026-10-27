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
            page.locator("#models-note").get_by_text("as this machine's Copilot offers them").wait_for()
            yield page
            browser.close()
    finally:
        server.should_exit = True


def a_look_s_credit_limit_is_typed_as_an_amount(page) -> None:
    """D-01M5XCD49YHHR1NQKKY8TQD0C3: it inherits Global's, and keystrokes keep a fraction as typed."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    look_limit = page.get_by_label("Credit limit per look", exact=True)
    expect(look_limit).to_have_attribute("placeholder", "inherit (0.75)")
    look_limit.press_sequentially("0.05")
    expect(look_limit).to_have_value("0.05")


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
        limits = page.locator("#limits")  # TD-286: each worker role's minutes; the shaper's chat has none
        expect(limits).to_contain_text("builder")
        expect(limits).not_to_contain_text("shaper")
        minutes = limits.get_by_label("Minutes per session, builder")
        expect(minutes).to_have_attribute("placeholder", "inherit (40)")
        pds.pick(page, "Model for builder", "tiny")
        expect(page.locator("#agents")).to_contain_text("tiny takes no effort setting")
        pds.pick(page, "Model for reviewer", "claude-opus-5.5")
        said = "claude-opus-5.5 does not offer effort xhigh (inherited); choose one it offers"
        message = pds.select(page, "Effort for reviewer").get_by_text(said, exact=True)
        expect(message).to_be_visible()
        page.get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_contain_text("Not saved: claude-opus-5.5 does not offer effort xhigh")
        pds.pick(page, "Effort for reviewer", "high")
        expect(message).to_have_count(0)
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
        rounds = page.get_by_label("Rounds at most, builder")
        rounds.fill("4")
        pds.pick(page, "Layer", "global")
        expect(page.locator("#pending")).to_have_text("No unsaved edits. This project: 1 more unsaved.")
        expect(rounds).to_have_value("")
        page.get_by_label("Minutes per session, builder").fill("60")
        pds.pick(page, "Layer", "project")
        expect(rounds).to_have_value("4")
        expect(page.locator("#pending")).to_have_text(
            "Unsaved: builder max rounds: inherited → 4. All projects: 1 more unsaved."
        )
        pds.pick(page, "When the design judge fails a change", "back")  # renders the page again
        expect(rounds).to_have_value("4")
        labels = page.get_by_label("Labels, comma-separated; none for no labels")
        labels.fill("inherit")  # a label may be named so: typing it never means "inherit"
        expect(labels).to_have_value("inherit")
        labels.fill("release:minor, owlbear")
        pds.pick(page, "The line Opened by OwlBear Delivery", "off")
        expect(page.locator("#spotter")).to_contain_text("inherit (on)")  # the switch, as Global sets it
        pds.pick(page, "On or off", "off")
        looks = page.get_by_label("Looks", exact=True)
        expect(looks).to_have_attribute("placeholder", "inherit (hand-off)")
        looks.fill("hand-off, sample")
        page.get_by_label("Sampled actions", exact=True).fill("5")
        a_look_s_credit_limit_is_typed_as_an_amount(page)
        at_once = page.get_by_label("Agent sessions at once in one project")  # TD-336
        expect(at_once).to_have_attribute("placeholder", "inherit (2)")
        at_once.fill("3")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        a_list_keeps_its_text_as_typed_and_counts_only_new_items(page, looks)
        pds.pick(page, "Layer", "global")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("60")
        expect(page.locator("#pr")).to_contain_text("inherit (on)")  # layered since code ships no defaults
        threshold = page.get_by_label("Curator's confidence threshold in percent (50 to 100)")  # TD-400
        expect(threshold).to_have_attribute("placeholder", "inherit (95)")
        threshold.fill("90")
        expect(page.locator("#pending")).to_contain_text("curator threshold: inherited → 90")
        pds.pick(page, "Layer", "project")
        expect(page.locator("#curation")).to_contain_text("Set for all projects")  # one value everywhere
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
        page.get_by_label("Minutes per session, reviewer").fill("25")
        save = page.get_by_role("region", name="Save settings").get_by_role("button", name="Save project settings")
        save.click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#error")).to_contain_text("kept your unsaved edits; check them and save again.")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("25")
        save.click()  # the answered confirmation may still be fading out with its own button of this name
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    saved = json.loads(store.config_path.read_text())
    assert (saved["widths"], saved["agents"]["reviewer"]["minutes"]) == ([1600], 25)


@pytest.mark.browser
def test_models_arriving_while_a_model_name_is_typed_wait_until_the_field_is_left(store, monkeypatch, pds) -> None:
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
            pds.only(page, base)
            page.goto(f"{base}/config#token=tok")
            typed = page.locator('p-input-text[label="Model for builder"]').get_by_label("Model for builder")
            typed.click()
            typed.press_sequentially("my-model")
            expect(page.locator("#models-note")).to_contain_text("Reading the models")
            time.sleep(3.5)  # the models arrived meanwhile
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
            page.get_by_label("Minutes per session, builder").fill("50")
            page.get_by_role("button", name="Save project settings").click()
            pds.answer(page, "Save project settings")
            expect(page.locator("#status")).to_have_text(
                "Saved this project's settings. They apply to the next session.", timeout=10_000
            )
            expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
            expect(pds.select(page, "Model for builder")).to_be_visible()
            browser.close()
    finally:
        server.should_exit = True
    assert saved.is_set()


@pytest.mark.browser
def test_with_no_layer_setting_anything_the_page_names_every_unset_value_and_a_save_fills_one(
    store, pds, monkeypatch
) -> None:
    """Code ships no defaults (2026-10-23): unset values are errors on the page, never filled from code."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", None)
    with settings_page(store, pds) as page:
        expect(page.locator("#unset")).to_contain_text("settings are unset")
        expect(page.locator("#unset")).to_contain_text("agents.builder.model")
        at_once = page.get_by_label("Agent sessions at once in one project")
        expect(at_once).to_have_attribute("placeholder", "inherit (unset)")
        at_once.fill("3")
        pds.pick(page, "Model for spotter", "tiny")  # one tier and no efforts: both still fillable
        expect(page.locator("#agents")).to_contain_text("no layer sets a context tier")
        page.locator("#agents").get_by_role("button", name="Use the default tier").click()
        pds.pick(page, "Effort for spotter", "medium")
        pds.pick(page, "Model for reviewer", "claude-opus-5.5")  # its effort unset: listed, never blocking the save
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        expect(page.locator("#unset")).not_to_contain_text("sessions,")
        expect(page.locator("#unset")).not_to_contain_text("agents.spotter.")
        expect(page.locator("#unset")).to_contain_text("spotter.switch")  # its settings start unset too
        expect(page.locator("#unset")).to_contain_text("spotter.irreversible_harm")
    assert store.read_config().sessions == 3
    spotter = store.settings().agent("spotter")  # a look needs only its model, effort and context
    assert (spotter.model, spotter.effort, spotter.context) == ("tiny", "medium", "default")


@pytest.mark.browser
def test_merge_and_cleanup_preferences_save_reload_and_clear_back_to_inherit(store, pds) -> None:
    """R15: the five optional preferences save into the shown layer, survive a reload, and clear to inherit."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        pds.pick(page, "Merge method", "squash")
        page.get_by_label("CI poll interval (seconds)").fill("45")
        pds.pick(page, "Ask before merging", "on")
        page.get_by_role("button", name="Save project settings").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
        page.reload()
        page.locator("#models-note").get_by_text("as this machine's Copilot offers them").wait_for()
        expect(page.get_by_label("CI poll interval (seconds)")).to_have_value("45")
        pds.pick(page, "Merge method", "inherit")  # the inherit choice clears the layer's own value
        page.get_by_role("button", name="Save project settings").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this project's settings. They apply to the next session.")
    prefs = store.read_config().prefs
    assert prefs.merge_method is None
    assert (prefs.ci_poll_seconds, prefs.ask_before_merge) == (45, True)


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
        page.locator("#models-note").get_by_text("as this machine's Copilot offers them").wait_for()
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
