"""The Settings page rendered by lit-html in a real browser (TD-264): drafts per layer, models and conflicts."""

from __future__ import annotations

import contextlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.local_system import data_place, data_repo, leases, local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.machine_host import versions
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.runtimes import model_choices, settings_seen
from owlbear_delivery_next.settings.config import CONFIG_FORMAT
from owlbear_delivery_next.settings.improvement import ALLOWED, CATEGORIES
from owlbear_delivery_next.state_store import registry, settings_carry
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, Store

from .test_config_api import Host, offered_model, prices
from .test_machine_pages import _git, browsing, clone, errors, until

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Page

SESSIONS = "Agent sessions at once in one project"  # the row's name; its key is `sessions`
LOOKS = "Spotter · Looks (hand-off, plan, state-change, sample)"
TOKEN = {"authorization": "Bearer t"}
READS_TIME = 60


def hold_first(page, url, method="GET", *, fetch=True):
    held = []

    def intercept(route):
        if held or route.request.method != method:
            route.fallback()
        else:
            held.append((route, route.fetch() if fetch else None))

    page.route(url, intercept)
    return held


def hold_polls(page):
    page.route("**/api/next/projects", lambda _route: None)


@contextlib.contextmanager
def refresh_page(store, pds):
    with pytest.MonkeyPatch.context() as mp, browsing(mp, pds) as (page, base):
        page.clock.install()
        page.add_init_script("""{
            window.settingsReadsFinished = 0;
            const every = window.setInterval;
            window.setInterval = (fn, ms, ...args) => {
                if (ms !== 5000) return every(fn, ms, ...args);
                window.settingsPollAt = Date.now() + ms;
                return every(() => {
                    window.settingsPollAt += ms;
                    return fn(...args);
                }, ms);
            };
        }""")

        def observe(route):
            response = route.fetch()
            body = response.text()
            end = "    showIdle();\n"
            assert body.count(end) == 1
            route.fulfill(response=response, body=body.replace(end, end + "    window.settingsReadsFinished++;\n"))

        page.route("**/assets/page/config/reads.mjs", observe)
        project = next(p for p in registry.load().projects if p.id == store.root.name)
        page.goto(f"{base}/config?project={project.id}#token=t")
        until(page, lambda: page.evaluate("window.settingsReadsFinished") == 1, READS_TIME)
        yield page, base


def poll(page):
    """Run the registered poll, before the held GET's later request deadline."""
    page.clock.pause_at(page.evaluate("() => new Date(window.settingsPollAt).toISOString()"))


def start_polled_refresh(page):
    projects = hold_first(page, "**/api/next/projects", fetch=False)
    poll(page)
    until(page, lambda: projects)
    page.clock.run_for(1)
    projects[0][0].continue_()


def polled_read(page, base, *, failure=False):
    with pytest.MonkeyPatch.context() as mp:
        if failure:

            def fail(*_args, **_kwargs):
                message = "could not read"
                raise OSError(message)

            mp.setattr(pack_files, "fetch", fail)
        Outside.read(base, registry.load().projects[0].id)
    held = hold_first(page, "**/config/read")
    start_polled_refresh(page)
    until(page, lambda: held)
    return held[0]


def fail_read_state(route):
    route.fulfill(status=503, json={"detail": "the read state could not be read"})


@pytest.fixture
def store(tmp_path: Path, shared_repo, monkeypatch) -> Store:
    monkeypatch.setenv(data_repo.VIEW, str(shared_repo[0]))
    _git(shared_repo[0], "commit", "--allow-empty", "-m", settings_carry.MESSAGE)
    _git(shared_repo[0], "push")
    monkeypatch.setattr(
        model_choices,
        "_read",
        lambda: [
            offered_model(
                "claude-opus-5.5", ["low", "medium", "high"], tiers=prices(200_000, 3, 15, prices(1_000_000, 6, 30))
            ),
            offered_model("gpt-6.1-sol", ["low", "medium", "high", "xhigh"]),
            offered_model("tiny", None),
        ],
    )
    monkeypatch.setattr(pack_files, "fetch", lambda *_args, **_kwargs: b"[]")
    repo = clone(tmp_path / "this-project", origin="https://github.com/acme/this-project.git")
    registry.register(repo)
    with registry.locked():
        machine = registry.load()
        machine.settings_moved = True
        registry.save(machine)
    return Store.open(repo)


@contextlib.contextmanager
def settings_page(store: Store, pds: Any) -> Iterator[Any]:
    """Use the machine pages' native host, registered clone and real Stores."""
    with pytest.MonkeyPatch.context() as mp, browsing(mp, pds) as (page, base):
        project = next(p for p in registry.load().projects if p.id == store.root.name)
        page.goto(f"{base}/config?project={project.id}#token=t")
        opened(page, pds)
        yield page


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
    """The spotter's switch, looks, sample and credit limit, edited in the Guardrails group; returns the looks field."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    pds.group(page, "guardrails")
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
    pds.group(page, "agents")
    expect(page.get_by_label("Minutes per session, builder")).to_have_value("60")
    pds.group(page, "checks")
    expect(page.locator("#pr")).to_contain_text("Unset")  # D-01M61SEXPFT9MXZGQHYVYFQ77C: nothing under Global
    pds.group(page, "memory")  # the curation threshold moved here from Guardrails
    threshold = page.get_by_label("Curator's confidence threshold in percent (50 to 100)")
    expect(threshold).to_have_attribute("placeholder", "Unset")
    threshold.fill("90")
    expect(page.locator("#pending")).to_contain_text("Curator's confidence threshold (%): unset → 90")
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
    expect(page.locator("#pending")).to_contain_text(f"{LOOKS}: hand-off, sample → hand-off,sample, plan")
    looks.fill("hand-off, sample")


@pytest.mark.browser
def test_a_model_choice_brings_its_efforts_and_an_effort_it_lacks_blocks_the_save(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        rows = page.locator("#agents-rows")  # TD-286: a worker role's minutes; a look has none
        expect(rows.locator("#set-agents-builder-minutes")).to_be_visible()
        expect(rows.locator("#set-agents-shaper-minutes")).to_be_visible()  # its amendment sessions' (TD-185)
        expect(rows.locator("#set-agents-spotter-minutes")).to_have_count(0)
        expect(rows.locator("#set-agents-spotter")).to_contain_text("n/a")
        minutes = rows.get_by_label("Minutes per session, builder")
        expect(minutes).to_have_attribute("placeholder", "inherit (40)")
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
        minutes.fill("60")
        page.get_by_role("button", name="Save project settings").click()
        expect(pds.modal(page)).to_contain_text("These apply to this-project only")  # TD-396
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
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
        options = pds.select(page, "Layer").locator("p-select-option")
        expect(options.filter(has_text="synced to shared repository")).to_have_count(2)
        expect(page.locator("#storage-note")).to_contain_text("Save commits and pushes")
        pds.pick(page, "Layer", "machine")
        expect(page.locator("#storage-note")).to_contain_text("local files, never pushed")
        pds.pick(page, "Layer", "project")
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
            "Unsaved: Task reviews (builder) · Rounds at most: inherited → 4. All projects: 1 more unsaved."
        )
        expect(page.locator("#save")).to_have_attribute("variant", "primary")
        pds.group(page, "checks")
        pds.pick(page, "When the design judge fails a change", "back")
        pds.group(page, "agents")  # the draft stays while another group shows
        expect(rounds).to_have_value("4")
        pds.group(page, "checks")
        merge_preferences_are_edited(page, pds)
        labels = page.get_by_label("Labels, comma-separated; none for no labels")
        labels.fill("inherit")  # a label may be named so: typing it never means "inherit"
        expect(labels).to_have_value("inherit")
        pds.pick(page, "The line Opened by OwlBear Delivery", "off")
        looks = the_spotter_is_edited(page, pds)
        pds.group(page, "agents")
        at_once = page.get_by_label("Agent sessions at once in one project")  # TD-336
        expect(at_once).to_have_attribute("placeholder", "inherit (2)")
        at_once.fill("3")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        pds.group(page, "guardrails")
        a_list_keeps_its_text_as_typed_and_counts_only_new_items(page, looks)
        the_global_layer_kept_its_edit_and_takes_one_more(page, pds)
    project = store.read_config()
    assert (project.agents["builder"].max_rounds, project.design_failures, project.agents["builder"].minutes) == (
        4, "back", None
    )  # fmt: skip
    assert (project.pr_labels, project.pr_marker, project.sessions) == (["inherit"], False, 3)
    assert project.final_review.max_rounds == 5
    assert project.prefs.model_dump(mode="json") == {
        "merge_method": "squash",
        "delete_remote_branch": False,
        "ci_poll_seconds": 45,
        "ci_start_window_seconds": 320,
        "ask_before_merge": True,
    }
    assert (project.spotter.switch, project.spotter.looks, project.spotter.sample_rate) == (
        "off",
        ["hand-off", "sample"],
        5,
    )
    assert project.spotter.look_credit_limit == 0.05
    assert project.spotter.steer_share is None  # the rest still inherit
    assert not store.global_path.exists()


def merge_preferences_are_edited(page, pds) -> None:
    pds.pick(page, "Merge method", "squash")
    pds.pick(page, "Delete the remote branch after merging", "off")
    pds.pick(page, "Ask before merging", "on")
    page.get_by_label("CI poll interval (seconds)").fill("45")
    page.get_by_label("CI start window (seconds)").fill("320")
    pds.group(page, "agents")
    page.get_by_label("Rounds at most, final review").fill("5")
    expect(page.locator("#pending")).to_contain_text("Final review · Rounds at most: inherited → 5")
    expect(page.locator("#pending")).to_contain_text("CI poll interval (seconds): inherited → 45")
    pds.group(page, "checks")


@pytest.mark.browser
def test_a_save_refused_by_a_newer_save_keeps_the_edits_and_the_next_save_lands(store, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        c = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1",
                       headers={"authorization": "Bearer t"})  # fmt: skip

        def intervene(route) -> None:
            assert route.request.method == "PUT"
            got = c.get("/api/next/config").json()
            assert route.request.post_data_json["rev"] == got["project_rev"]
            newer = got["project"] | {"widths": [1600]}
            changed = c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": newer})
            assert changed.status_code == 200
            assert changed.json()["project_rev"] != got["project_rev"]
            route.continue_()

        page.route("**/api/next/config/project", intervene, times=1)
        pds.group(page, "agents")
        page.get_by_label("Minutes per session, reviewer").fill("25")
        page.get_by_label("Minutes per session, builder").fill("35")
        page.get_by_label("Rounds at most, builder").fill("4")
        pds.group(page, "guardrails")
        page.get_by_label("Steered share", exact=True).fill("10")
        pds.group(page, "checks")  # D-01M63C92B83D61XFXTRXG8JAVB: edits in several groups, each group's counted
        pds.pick(page, "Merge method", "squash")
        unsaved = page.locator("#groups p-tag")
        expect(unsaved).to_have_text(["3 unsaved", "1 unsaved", "1 unsaved"])
        expect(page.locator("#groups a[href='#agents'] p-tag")).to_have_text("3 unsaved")
        save = page.get_by_role("region", name="Save settings").get_by_role("button", name="Save project settings")
        save.click()
        with page.expect_response("**/api/next/config/project") as refused:
            pds.answer(page, "Save project settings")
        assert refused.value.status == 409
        expect(page.locator("#error")).to_contain_text("kept your unsaved edits; check them and save again.")
        expect(unsaved).to_have_text(["3 unsaved", "1 unsaved", "1 unsaved"])
        expect(pds.select(page, "Merge method")).to_have_js_property("value", "squash")
        pds.group(page, "agents")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("25")
        save.click()  # the answered confirmation may still be fading out with its own button of this name
        with page.expect_response("**/api/next/config/project") as accepted:
            pds.answer(page, "Save project settings")
        assert accepted.value.status == 200
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        expect(unsaved).to_have_count(0)
    saved = json.loads(store.config_path.read_text())
    minutes = (saved["agents"]["reviewer"]["minutes"], saved["agents"]["builder"]["minutes"])
    assert (saved["widths"], *minutes) == ([1600], 25, 35)
    assert (saved["agents"]["builder"]["max_rounds"], saved["prefs"]["merge_method"]) == (4, "squash")  # one save
    assert saved["spotter"]["steer_share"] == 10


@pytest.mark.browser
def test_an_address_opens_its_group_and_an_unset_setting_s_link_its_row(store, pds, monkeypatch) -> None:
    """Each group has an address, back and forward follow them; an old address of a section or row, or of the former
    Runs group, opens its group there, and the overview's unset list links each setting's row (GW8RT6); a group with
    three or fewer unset names them all (D-01M66B6GS0HKACV9C4R4QKFX7T)."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"sessions": None}))
    with settings_page(store, pds) as page:
        url = page.url.split("#")[0]
        pds.group(page, "overview")
        expect(page.locator("#unset-agents")).to_have_text(f"Agents and runs, 1 unset: {SESSIONS}")
        expect(page.locator("#set-sessions p-text[color='error']")).to_have_count(0)  # not shown: another group
        page.locator("#unset").get_by_role("link", name=SESSIONS, exact=True).click()
        expect(page).to_have_url(f"{url}#agents")
        at_once = page.get_by_label("Agent sessions at once in one project")
        expect(at_once).to_be_focused()
        named = page.locator("#set-sessions p-text[color='error']")
        expect(named).to_have_text("Agent sessions at once in one project")
        page.go_back()
        expect(page).to_have_url(f"{url}#overview")
        expect(page.locator("#unset")).to_be_visible()
        expect(at_once).to_have_count(0)
        page.go_forward()
        expect(page).to_have_url(f"{url}#agents")
        expect(page.locator("#agents-title")).to_be_focused()  # a switch not made in the groups' list: its heading
        for old, group, focused in (
            ("set-prefs-merge_method", "checks", pds.select(page, "Merge method").get_by_role("combobox")),
            ("folder-title", "project", page.locator("#folder-title")),
            ("machine-title", "this-machine", page.locator("#machine-title")),
            ("spotter-title", "guardrails", page.locator("#spotter-title")),
            ("curation-title", "memory", page.locator("#curation-title")),  # moved from Guardrails
            ("set-curator_threshold", "memory", page.locator("#set-curator_threshold")),  # read-only here: the row
            ("rounds-title", "agents", page.locator("#rounds-title")),
            ("set-limits-builder", "agents", page.get_by_label("Minutes per session, builder")),  # rows that were
            (
                "set-subagents-test-curator",
                "agents",
                pds.select(page, "Built-in subagents, test-curator").get_by_role("combobox"),
            ),
            ("limits-title", "agents", page.locator("#agents-title")),  # sections that were
            ("subagents-title", "agents", page.locator("#agents-title")),
        ):
            page.goto(f"{url}#{old}")
            expect(page).to_have_url(f"{url}#{group}")
            expect(page.locator(f"#groups a[href='#{group}']")).to_have_attribute("aria-current", "page")
            expect(focused).to_be_focused()
        page.goto(f"{url}#machine-title")
        expect(page.locator("#machine-title")).to_be_focused()  # the focus is elsewhere
        page.goto(f"{url}#runs")  # the group that was: its address opens Agents and runs
        expect(page).to_have_url(f"{url}#agents")
        expect(page.locator("#groups a[href='#agents']")).to_have_attribute("aria-current", "page")
        expect(page.locator("#agents-title")).to_be_focused()
        for bad in ("%", "%E0%A4%A"):  # Sol R1-1: an address that doesn't decode opens the overview, loaded or not
            page.goto(f"{url}#agents")
            page.goto(f"{url}#{bad}")
            expect(page).to_have_url(f"{url}#overview")
            expect(page.locator("#unset")).to_be_visible()
            page.goto(f"{url}#{bad}")
            page.reload()
            expect(page).to_have_url(f"{url}#overview")
            expect(page.locator("#groups a[href='#overview']")).to_have_attribute("aria-current", "page")
            expect(page.locator("#unset")).to_be_visible()


WAIT = "Challenge starts by itself after (minutes), shaper"  # the shaper's wait's cell (#986)


@pytest.mark.browser
def test_the_filter_shows_only_the_unset_set_or_unsaved_rows_and_a_link_to_a_row_shows_every_row(
    store, pds, monkeypatch
) -> None:
    """A group's rows can be narrowed to the unset ones, those the layer sets and its unsaved edits; a panel left
    without a row goes too, and a link to a row names it whatever the filter hid."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"sessions": None}))
    with settings_page(store, pds) as page:
        rows, none = page.locator("p-table-row[data-setting]:visible"), page.locator("#filter-none")
        panels = page.locator("main section.panel:visible h2")
        expect(panels).to_have_text(["Where you edit", "Agents", "Challenge rounds", "Sessions at once"])
        pds.pick(page, "Show", "unset")
        expect(rows).to_have_count(1)
        expect(page.locator("#set-sessions")).to_be_visible()
        expect(panels).to_have_text(["Where you edit", "Sessions at once"])
        expect(none).to_be_hidden()
        url = page.url.split("#")[0]
        page.goto(f"{url}#project")
        page.go_back()  # not by the groups' list: the focus goes to the Show menu, as the first panel is filtered away
        expect(page).to_have_url(f"{url}#agents")
        expect(pds.select(page, "Show").get_by_role("combobox")).to_be_focused()
        pds.group(page, "guardrails")  # the filter stays across the groups
        expect(rows).to_have_count(0)
        expect(none).to_have_text("No setting in this group is unset.")
        pds.pick(page, "Show", "all")
        expect(none).to_be_hidden()
        expect(panels).to_have_text(
            ["Where you edit", "Spotter", "Your instructions, skills and memory", "Shell guard"]
        )
        pds.group(page, "agents")
        page.get_by_label("Rounds at most, builder").fill("4")
        page.get_by_label(WAIT).fill("20")  # the shaper's row alone has the cell; the others say n/a
        assert min(page.get_by_label(WAIT).bounding_box()[side] for side in ("width", "height")) >= 24  # WCAG 2.5.8
        expect(page.locator("#set-rounds-planner")).to_contain_text("n/a")
        pds.pick(page, "Show", "unsaved")
        expect(rows).to_have_count(3)  # the final review follows the builder's rounds, so it changes too
        expect(page.locator("#set-rounds-builder, #set-rounds-final_review, #set-rounds-shaper")).to_have_count(3)
        pds.group(page, "checks")
        expect(none).to_have_text("No unsaved edits in this group.")
        pds.group(page, "agents")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        expect(rows).to_have_count(0)  # saved: no longer an edit
        pds.pick(page, "Show", "set")
        expect(rows).to_have_count(2)  # this project sets the builder's rounds and the shaper's wait, nothing else
        expect(page.locator("#set-rounds-builder, #set-rounds-shaper")).to_have_count(2)
        pds.pick(page, "Layer", "global")
        expect(rows).to_have_count(0)
        expect(none).to_have_text("This layer sets nothing in this group.")
        pds.pick(page, "Layer", "project")
        pds.group(page, "overview")
        page.locator("#unset").get_by_role("link", name=SESSIONS, exact=True).click()
        expect(page.locator("#set-sessions")).to_be_visible()
        expect(pds.select(page, "Show")).to_have_js_property("value", "all")


@pytest.mark.browser
def test_the_unsaved_filter_shows_a_row_whose_draft_is_only_spelled_differently(store, pds, monkeypatch) -> None:
    """The pending line counts "02" over a saved 2 as an unsaved edit, so the filter shows its row too."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"sessions": None}))
    with settings_page(store, pds) as page:
        sessions = page.get_by_label("Agent sessions at once in one project")
        sessions.fill("2")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        sessions.fill("02")
        expect(page.locator("#pending")).to_contain_text(f"{SESSIONS}: 2 \u2192 02")
        pds.pick(page, "Show", "unsaved")
        expect(page.locator("#set-sessions")).to_be_visible()


@pytest.mark.browser
def test_the_unsaved_filter_keeps_a_row_whose_edit_is_undone_until_the_filter_changes(store, pds, monkeypatch) -> None:
    """Backspacing the only character of a draft must not hide its row and take the focus before a replacement can be
    typed; the row goes once the filter, or a save, changes."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"sessions": None}))
    with settings_page(store, pds) as page:
        sessions, row = page.get_by_label("Agent sessions at once in one project"), page.locator("#set-sessions")
        sessions.fill("3")
        pds.pick(page, "Show", "unsaved")
        expect(row).to_be_visible()
        sessions.press("ArrowRight")  # one character; End scrolls rather than moving the caret on macOS
        sessions.press("Backspace")
        expect(page.locator("#pending")).to_have_text("No unsaved edits.")
        expect(row).to_be_visible()
        expect(sessions).to_be_focused()
        sessions.press_sequentially("5")
        expect(page.locator("#pending")).to_contain_text(f"{SESSIONS}: inherited \u2192 5")
        sessions.press("Backspace")
        pds.pick(page, "Show", "all")
        pds.pick(page, "Show", "unsaved")
        expect(row).to_be_hidden()


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
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store, pds) as page:
        scope = page.get_by_role("region", name="Where you edit")
        scope.get_by_text("How the layers combine").click()
        text = scope.locator("p-text", has_text="A blank project value")
        expect(text).to_be_visible()
        table = page.locator("p-table").first
        for width in (1280, 2400):
            page.set_viewport_size({"width": width, "height": 900})
            assert 65 <= text.evaluate(LONGEST_LINE) <= 80, width
            assert table.bounding_box()["width"] > 2 * text.bounding_box()["width"], width
        page.set_viewport_size({"width": 390, "height": 800})
        pds.pick(page, "Layer", "global")
        page.get_by_role("button", name="Use recommended", exact=True).click()
        expect(page.locator("#status")).to_contain_text("nothing has been saved")
        assert page.evaluate("document.documentElement.scrollWidth") <= 390
        assert page.locator(".bar").evaluate("e => e.getBoundingClientRect().height") < 400
        pending = page.locator("#pending")
        pending.focus()
        pending.press("End")
        page.wait_for_function("document.querySelector('#pending').scrollTop > 0")


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
        page.locator("#unset").get_by_role("link", name=SESSIONS, exact=True).click()
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
    _layered(store, monkeypatch, GLOBAL, {}, {})
    with browsing(monkeypatch, pds) as (page, base):
        page.add_init_script(MODELS_HANDLED)
        held = hold_first(page, "**/config/models")
        page.goto(f"{base}/config?project={registry.load().projects[0].id}#token=t")
        pds.group(page, "agents")
        planner = page.locator('p-input-text[label="Model for planner"]').get_by_label("Model for planner")
        pds.pick(page, "Layer", "global")
        expect(planner).to_have_attribute("placeholder", "Unset")
        expect(_option(page, pds, "Context for planner")).to_have_text("Unset")
        pds.pick(page, "Layer", "project")
        expect(planner).to_have_attribute("placeholder", "inherit (unset)")
        expect(_option(page, pds, "Context for builder")).to_have_text("inherit (long)")
        typed = page.locator('p-input-text[label="Model for builder"]').get_by_label("Model for builder")
        typed.click()
        typed.press_sequentially("my-model")
        expect(page.locator("#models-note")).to_contain_text("Reading the models")
        until(page, lambda: held)
        held[0][0].fulfill(response=held[0][1])
        page.wait_for_function("window.modelsHandled === true")
        typed.press_sequentially("-2")
        expect(typed).to_be_focused()
        expect(typed).to_have_value("my-model-2")
        pds.select(page, "Layer").get_by_role("combobox").focus()
        expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
        chosen = pds.select(page, "Model for builder")
        expect(chosen).to_have_js_property("value", "my-model-2")
        said = "my-model-2 (not offered here)"
        expect(chosen.get_by_role("option", name=said, selected=True, include_hidden=True)).to_have_count(1)
        pds.pick(page, "Model for builder", "claude-opus-5.5")
        expect(chosen.get_by_role("combobox")).to_be_focused()


@pytest.mark.browser
@pytest.mark.usefixtures("store")
def test_models_arriving_during_a_save_apply_once_it_ends(monkeypatch, pds) -> None:
    """Sol, TD-264: a save under way when the models arrive leaves them for its end, never for good."""
    with browsing(monkeypatch, pds) as (page, base):
        page.add_init_script(MODELS_HANDLED)
        models = hold_first(page, "**/config/models")
        page.goto(f"{base}/config?project={registry.load().projects[0].id}#token=t")
        pds.group(page, "agents")
        page.get_by_label("Minutes per session, builder").fill("50")
        save = hold_first(page, "**/config/project", "PUT", fetch=False)
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        until(page, lambda: save and models)
        expect(page.locator("#status")).to_have_text("Saving…")
        models[0][0].fulfill(response=models[0][1])
        page.wait_for_function("window.modelsHandled === true")
        save[0][0].continue_()
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        expect(page.locator("#models-note")).to_contain_text("as this machine's Copilot offers them")
        expect(pds.select(page, "Model for builder")).to_be_visible()


@pytest.mark.browser
def test_a_save_blocks_old_layers_before_its_across_read_finishes(store, pds) -> None:
    with refresh_page(store, pds) as (page, _base):
        read = hold_first(page, "**/config/read", "POST")
        page.get_by_role("button", name="Read again").click()
        until(page, lambda: read)
        save = hold_first(page, "**/config/project", "PUT", fetch=False)
        pds.group(page, "agents")
        field = page.get_by_label("Minutes per session, builder")
        field.fill("50")
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        until(page, lambda: save)
        layers = hold_first(page, "**/api/next/config")
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
        expect(page.locator("#status")).to_contain_text("Saved this-project's settings")


@pytest.mark.browser
def test_an_older_read_s_layers_answered_last_never_replace_a_newer_read_s(store, pds) -> None:
    """#810: two reads' refreshes overlap; the first one's layers, answered after the second's, are not shown."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with refresh_page(store, pds) as (page, _base):
        pds.group(page, "overview")
        expect(page.locator("#reads-status")).to_contain_text("Last read")
        held: list[tuple[Any, Any]] = []

        def hold(route: Any) -> None:
            if route.request.method != "GET" or held:
                route.continue_()
                return
            held.append((route, route.fetch()))  # the layers before the change below

        page.route("**/api/next/config", hold)
        page.locator("#read-again").click()
        for _ in range(400):
            if held:
                break
            page.wait_for_timeout(50)
        assert held
        store.config_path.parent.mkdir(parents=True, exist_ok=True)
        store.config_path.write_text(json.dumps({"format": CONFIG_FORMAT, "agents": {"builder": {"minutes": 45}}}))
        page.locator("#read-again").click()  # the second read's refresh shows the change
        pds.group(page, "agents")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("45")
        hold_polls(page)
        route, before = held[0]
        with page.expect_request("**/config/models"):  # the first refresh goes on past the layers it read
            route.fulfill(response=before)
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("45")


@pytest.mark.browser
@pytest.mark.parametrize("order", ["failure first", "failure last"])
def test_a_newer_read_s_failed_layers_never_discard_an_older_read_s(store, pds, order: str, whole_error) -> None:
    """#810: of two reads' refreshes, the newer one's layers fail; the older one's, answered before or after, show."""
    with refresh_page(store, pds) as (page, _base):
        pds.group(page, "overview")
        expect(page.locator("#reads-status")).to_contain_text("Last read")
        store.config_path.parent.mkdir(parents=True, exist_ok=True)
        store.config_path.write_text(json.dumps({"format": CONFIG_FORMAT, "agents": {"builder": {"minutes": 45}}}))
        held: list[tuple[Any, Any]] = []

        def hold(route: Any) -> None:
            if route.request.method != "GET" or len(held) == 2:
                route.continue_()
                return
            held.append((route, None if held else route.fetch()))  # the first brings the change

        page.route("**/api/next/config", hold)
        for count in (1, 2):
            page.locator("#read-again").click()
            for _ in range(400):
                if len(held) == count:
                    break
                page.wait_for_timeout(50)
            assert len(held) == count
        (older, found), (newer, _) = held
        hold_polls(page)
        message = f"the layers could not be read:\n{whole_error}\nreload note"
        failed = {"status": 503, "json": {"detail": message}}
        expected = "T" + message[1:]
        pds.group(page, "agents")
        minutes = page.get_by_label("Minutes per session, builder")
        error = page.locator("#error")
        if order == "failure first":
            newer.fulfill(**failed)
            expect(error).to_have_text(expected)
            assert error.text_content().strip() == expected
            older.fulfill(response=found)
        else:
            older.fulfill(response=found)
            expect(minutes).to_have_value("45")
            newer.fulfill(**failed)
        # The changed value witnesses reload's success, including its error-clearing decision, not just HTTP arrival.
        expect(minutes).to_have_value("45")
        expect(error).to_have_text(expected)
        assert error.text_content().strip() == expected


@pytest.mark.browser
def test_an_older_read_s_failed_layers_never_speak_over_a_newer_read_s(store, pds) -> None:
    """#810: of two reads' refreshes, the older one's layers fail after the newer one's showed; no error is said."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with refresh_page(store, pds) as (page, _base):
        pds.group(page, "overview")
        expect(page.locator("#reads-status")).to_contain_text("Last read")
        held: list[Any] = []

        def hold(route: Any) -> None:
            if route.request.method != "GET" or len(held) == 2:
                route.continue_()
                return
            held.append(route)

        page.route("**/api/next/config", hold)
        for count in (1, 2):
            page.locator("#read-again").click()
            for _ in range(400):
                if len(held) == count:
                    break
                page.wait_for_timeout(50)
            assert len(held) == count
        older, newer = held
        hold_polls(page)
        with page.expect_request("**/api/next/config/models"):  # the newer refresh is done with the layers
            newer.continue_()
        with page.expect_request("**/api/next/config/models"):  # asked right after the failed answer is handled
            older.fulfill(status=503, json={"detail": "the layers could not be read"})
        assert page.locator("#error").is_hidden()


@pytest.mark.browser
def test_with_no_layer_setting_anything_the_page_names_every_unset_value_and_a_save_fills_one(
    store, pds, monkeypatch
) -> None:
    """Code ships no defaults (2026-10-23): unset values are errors on the page, never filled from code."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", None)
    with settings_page(store, pds) as page:
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pds.group(page, "overview")
        expect(page.locator("#unset")).to_contain_text("settings are unset")
        agents, guardrails = _unset_count(page, "agents"), _unset_count(page, "guardrails")
        pds.group(page, "agents")
        at_once = page.get_by_label("Agent sessions at once in one project")
        expect(at_once).to_have_attribute("placeholder", "inherit (unset)")
        at_once.fill("3")
        pds.pick(page, "Model for spotter", "tiny")  # one tier and no efforts: both still fillable
        expect(page.locator("#agents-rows")).to_contain_text("no layer sets a context tier")
        page.locator("#agents-rows").get_by_role("button", name="Use the default tier").click()
        pds.pick(page, "Effort for spotter", "medium")
        pds.pick(page, "Model for reviewer", "claude-opus-5.5")  # its effort unset: listed, never blocking the save
        page.get_by_role("button", name="Save project settings").click()
        pds.answer(page, "Save project settings")
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        pds.group(page, "overview")
        expect(page.locator("#unset-agents")).to_contain_text(
            f"Agents and runs, {agents - 5} unset:"
        )  # sessions, spotter's three, a model
        expect(page.locator("#unset-guardrails")).to_contain_text(f"Guardrails, {guardrails} unset:")
        pds.group(page, "guardrails")
        for key in ("switch", "irreversible_harm"):  # its settings start unset too: their names stay red
            expect(page.locator(f"#set-spotter-{key} p-text[color='error']")).to_have_count(1)
        pds.group(page, "agents")
        expect(page.locator("#set-agents-spotter p-text[color='error']")).to_have_count(0)
        assert errors == []  # a name that stops being red keeps a valid colour
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


@pytest.mark.browser
def test_recommendations_fill_only_globals_blanks_and_keep_saved_values_and_existing_drafts(
    store, pds, monkeypatch
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415

    saved = {
        "sessions": 3, "pr_marker": False, "pr_labels": [], "load_user_memory": False,
        "spotter": {"steer_share": 0}, "agents": {"builder": {"minutes": 55}},
    }  # fmt: skip
    _layered(store, monkeypatch, saved, {"sessions": 5}, {"sessions": 6})
    paths = {"project": store.config_path, "machine": store.machine_path, "global": store.global_path}
    before = {name: path.read_bytes() for name, path in paths.items()}
    with settings_page(store, pds) as page:
        pds.pick(page, "Layer", "global")
        page.get_by_label("Minutes per session, builder").fill("66")
        page.get_by_label("Agent sessions at once in one project").fill("")  # deliberate unsaved clear
        recommended = page.get_by_role("button", name="Use recommended", exact=True)
        expect(recommended).to_have_count(1)
        recommended.click()
        expect(recommended).to_be_focused()
        box = recommended.bounding_box()
        assert box is not None
        assert box["width"] >= 24
        assert box["height"] >= 24
        expect(page.locator("#status")).to_contain_text("nothing has been saved")
        expect(page.get_by_label("Agent sessions at once in one project")).to_have_value("")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("66")
        expect(page.get_by_label("Minutes per session, auditor")).to_have_value("40")
        pending = page.locator("#pending").inner_text()
        recommended.click()
        expect(page.locator("#pending")).to_have_text(pending)
        assert {name: path.read_bytes() for name, path in paths.items()} == before
        pds.group(page, "guardrails")
        expect(pds.select(page, MEMORY)).to_have_js_property("value", "off")
        expect(page.get_by_label("Steered share", exact=True)).to_have_value("0")
        pds.group(page, "checks")
        expect(page.get_by_label(LABELS)).to_have_value("none")
        expect(pds.select(page, "The line Opened by OwlBear Delivery")).to_have_js_property("value", "off")
        for layer in ("project", "machine"):
            pds.pick(page, "Layer", layer)
            expect(recommended).to_be_disabled()
            expect(page.locator("#recommend-note")).to_contain_text("available on Global only")
        pds.pick(page, "Layer", "global")
        page.locator("#save").click()
        pds.answer(page, "Keep editing")
        assert {name: path.read_bytes() for name, path in paths.items()} == before
        pds.group(page, "agents")
        page.get_by_label("Minutes per session, auditor").fill("")
        recommended.click()
        expect(page.get_by_label("Minutes per session, auditor")).to_have_value("")
        assert {name: path.read_bytes() for name, path in paths.items()} == before


@pytest.mark.browser
def test_unshared_storage_scope(tmp_path, monkeypatch, pds) -> None:
    project = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.goto(f"{base}/config?project={project.id}#token=t")
        pds.group(page, "agents")
        expect(page.locator("#storage-note")).to_contain_text("This Mac only: project settings stay local")
        expect(pds.select(page, "Layer").locator('p-select-option[value="project"]')).to_contain_text("this Mac only")
        expect(pds.select(page, "Layer").locator('p-select-option[value="global"]')).to_have_attribute("disabled", "")
        expect(page.locator("#scope-note")).to_contain_text("No shared settings location")
        page.get_by_label("Agent sessions at once in one project").fill("3")
        page.locator("#save").click()
        expect(pds.modal(page)).to_contain_text("on this Mac only (no shared repository is set up)")
        pds.answer(page, "Keep editing")


def _option(page, pds, label: str) -> Any:
    """The option that clears the shown layer's value in the select labelled *label*."""
    return pds.select(page, label).locator('p-select-option[value="inherit"]')


WARNED = "Unset: every machine or project must then set its own"


def _in_use(page, row: str) -> Any:
    """The in-use line of the setting row *row*."""
    return page.locator(f"#{row} p-text[size='xs']").filter(has_text="in use")


@pytest.mark.browser
def test_preview_and_unset_lines_follow_the_shown_layer(store, pds, monkeypatch) -> None:
    """#809: the line under a setting says what saving the shown layer would give, from the layers as they are saved
    and that layer's own edits; another layer's edits never show there."""
    builder = {"max_rounds": 3, "last_round_at": 1, "ask_owner_at": 4}
    glob = GLOBAL | {"agents": {"builder": GLOBAL["agents"]["builder"] | builder}}
    final = {"max_rounds": 2, "last_round_at": 1, "ask_owner_at": 3}
    machine = {"sessions": 3, "pr_labels": ["m"]}
    _layered(store, monkeypatch, glob, machine, {"sessions": 4, "pr_marker": False, "final_review": final})
    with settings_page(store, pds) as page:
        sessions, line = page.get_by_label(SESSIONS), _in_use(page, "set-sessions")
        sessions.fill("")
        expect(line).to_have_text("in use: 3, from this machine")
        sessions.fill("6")
        expect(line).to_have_text("in use: 6, from this project")
        pds.pick(page, "Layer", "global")
        expect(line).to_have_text("in use: 4, from this project")
        results = page.evaluate("""async () => {
          const { state, drafts } = await import("/assets/page/config/state.mjs");
          const { preview } = await import("/assets/page/config/layers.mjs");
          const results = [];
          for (const [layer, key, value, path] of [
            ["project", "sessions", "", "sessions"],
            ["machine", "sessions", "6", "sessions"],
            ["global", "sessions", "7", "sessions"],
            ["machine", "pr_labels", "", "pr_labels"],
            ["global", "builder.max_findings", "5", "final_review.max_findings"],
            ["project", "pr_marker", "", "pr_marker"]
          ]) {
            state.layer = layer;
            drafts[layer][key] = value;
            results.push(preview(path));
            delete drafts[layer][key];
          }
          state.layer = "global";
          return results;
        }""")
        assert results == [
            {"value": 3, "from": "machine"},
            {"value": 4, "from": "project"},
            {"value": 4, "from": "project"},
            {"value": None},
            {"value": 5, "from": "builder"},
            {"value": True, "from": "global"},
        ]
        sessions.fill("")
        expect(page.locator("#set-sessions")).to_contain_text(WARNED)
        sessions.fill("2")
        expect(page.locator("#set-sessions p-text[color='warning']")).to_have_count(0)
        expect(_option(page, pds, "Model for builder")).to_have_text("Unset")
        expect(_option(page, pds, "Effort for builder")).to_have_text("Unset")
        expect(page.locator("#set-agents-builder").get_by_role("button", name="Unset")).to_be_visible()
        expect(page.locator("#set-rounds-final_review")).to_contain_text("Unset: it then takes the builder's value")
        pds.group(page, "guardrails")
        looks, sample = page.get_by_label("Looks", exact=True), page.locator("#set-spotter-sample_rate")
        expect(sample.locator("p-text[color='warning']")).to_have_count(0)
        looks.fill("hand-off, sample")
        expect(sample).to_contain_text(WARNED)
        looks.fill("hand-off")
        expect(sample.locator("p-text[color='warning']")).to_have_count(0)
        pds.group(page, "checks")
        expect(_option(page, pds, "Merge method")).to_have_text("Unset")
        expect(page.locator("#set-pr_labels")).to_contain_text(WARNED)
        for layer, placeholder in (("machine", "inherit (unset)"), ("project", "inherit (m)")):
            pds.pick(page, "Layer", layer)
            expect(page.locator("main p-text[color='warning']")).to_have_count(0)
            expect(page.get_by_label(LABELS)).to_have_attribute("placeholder", placeholder)


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
        expect(page.locator("#unset-memory")).to_contain_text("unset")
        page.goto(f"{url}#set-curator_threshold")  # an unset link's address; Memory lists only its first three
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


@pytest.mark.browser
def test_guardrail_controls_serialize(store, pds, monkeypatch) -> None:
    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update=dict.fromkeys((*USER_KEYS, "guard_level"))))
    with settings_page(store, pds) as page:
        pds.group(page, "overview")
        expect(page.locator("#unset")).to_contain_text(f"{INSTRUCTIONS}, {SKILLS}, {MEMORY}")
        expect(page.locator("#unset-guardrails")).to_contain_text("4 unset")
        pds.group(page, "guardrails")
        for key in (*USER_KEYS, "guard_level"):
            expect(page.locator(f"#set-{key} p-text[color='error']")).to_have_count(1)
        for field, label in CATEGORY_LABELS.items():
            select = pds.select(page, label)
            category = next(c for c, f in CATEGORIES.items() if f == field)
            assert select.locator("p-select-option").evaluate_all("os => os.map(o => o.value)") == [
                "inherit",
                *ALLOWED[category],
            ]
            pds.pick(page, label, ALLOWED[category][-1])
        for label, value in ((INSTRUCTIONS, "on"), (SKILLS, "off"), (MEMORY, "on"), (GUARD, "lenient")):
            pds.pick(page, label, value)
            big_enough(pds.select(page, label).get_by_role("combobox"))
        _saved_by_keyboard(page, pds, "Save project settings", "this-project's")
        expect(page.locator("#user-config p-text[color='error']")).to_have_count(0)
    saved = store.read_config()
    assert [getattr(saved, key) for key in USER_KEYS] == [True, False, True]
    assert saved.guard_level == "lenient"
    assert {field: getattr(saved.spotter, field) for field in CATEGORY_LABELS} == {
        field: ALLOWED[category][-1] for category, field in CATEGORIES.items()
    }


GUARD = "Shell guard level"


ACCOUNT = "GitHub account: a login, or repository-owner"
FALLBACK = "maba-pag (gh has no account for the owner acme)"


@pytest.mark.browser
@pytest.mark.timeout(90)  # one walk through both layers, a reload and the error state takes about 40 s
def test_the_github_account_shows_the_account_it_resolves_to_in_each_layer(store, pds, monkeypatch, fake_gh) -> None:
    """TD-402: unset until a layer sets it; repository-owner shows the account TD-402's rule gives on the origin."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415
    from owlbear_delivery_next.state_store.store import read_layer  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"github_account": None}))
    with settings_page(store, pds) as page:
        url, row = page.url.split("#")[0], page.locator("#set-github_account")
        pds.group(page, "overview")
        page.locator("#unset").get_by_role("link", name="GitHub account", exact=True).click()
        expect(page).to_have_url(f"{url}#checks")
        field = page.get_by_label(ACCOUNT)
        expect(field).to_be_focused()
        expect(row.locator("p-text[color='error']")).to_have_text("GitHub account")
        pds.pick(page, "Layer", "global")
        box = field.bounding_box()
        assert min(box["width"], box["height"]) >= 24  # WCAG 2.5.8 target size
        field.fill("repository-owner")
        expect(_in_use(page, "set-github_account")).to_have_text(f"in use: {FALLBACK}, from global")
        expect(page.locator("#pending")).to_have_text("Unsaved: GitHub account: unset → repository-owner.")
        _saved_by_keyboard(page, pds, "Save global defaults", "the global")
        pds.pick(page, "Layer", "project")
        expect(field).to_have_attribute("placeholder", "inherit (repository-owner)")
        field.fill("octo-writer")
        expect(_in_use(page, "set-github_account")).to_have_text("in use: octo-writer, from this project")
        _saved(page, pds, "Save project settings", "this-project's")

        page.reload()
        opened(page, pds, "checks")
        expect(field).to_have_value("octo-writer")
        expect(_in_use(page, "set-github_account")).to_have_text("in use: octo-writer, from this project")
        field.fill("")
        expect(_in_use(page, "set-github_account")).to_have_text(f"in use: {FALLBACK}, from global")
        _saved(page, pds, "Save project settings", "this-project's")
        expect(_in_use(page, "set-github_account")).to_have_text(f"in use: {FALLBACK}, from global")

        fake_gh.set({"github.com": {"boecht": "success"}}, {"github.com": "boecht"})
        page.reload()
        opened(page, pds, "checks")
        expect(_in_use(page, "set-github_account")).to_contain_text(
            "in use: repository-owner: AccountMissing: github account: "
            "gh holds no account acme or maba-pag on github.com"
        )
    layers = (store.read_config(), read_layer(store.global_path, config.GlobalLayer))
    assert [layer.github_account for layer in layers] == [None, "repository-owner"]


CATEGORY_LABELS = {
    "hand_off_fitness": "Hand-off fitness",
    "course_and_constraints": "Course and constraints",
    "outside_state_changes": "Outside-state changes",
    "irreversible_harm": "Irreversible harm",
}


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
def pending_shared(store) -> Store:
    """A shared project whose legacy preference import is pending: its review is what Settings must complete."""
    store.write_profile(Profile())
    store.mark_prefs_import("", "pending", "absent")
    return store


def _fresh(tmp_path: Path, remote: Path) -> Store:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    return Store(tmp_path / "fresh-store", data_repo.DataRepo(second), "this-project")


@pytest.fixture
def pending(store) -> Store:
    """An unshared project whose legacy preference import is pending: for the page's review intent alone."""
    store.write_profile(Profile())
    store.mark_prefs_import("", "pending", "absent")
    return store


@pytest.mark.browser
def test_a_refused_save_of_an_already_empty_clear_keeps_the_review_until_the_retry_publishes(
    pending, monkeypatch, pds
) -> None:
    """Clearing a preference that is already empty is still a review, and the retry must not drop it."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    real, notices = Store.save, iter(["remote refused"])

    def refuse_once(self, path, *args, **kw) -> str:
        notice = real(self, path, *args, **kw)  # the project file is written; its first publication returns a notice
        return next(notices, notice) if path == pending.config_path else notice

    monkeypatch.setattr(Store, "save", refuse_once)
    with settings_page(pending, pds) as page:
        sent = _project_puts(page)
        pds.group(page, "checks")
        pds.pick(page, "Merge method", "inherit")  # already inherited: no draft, only the review
        page.get_by_role("button", name="Save project settings").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_be_visible()
        assert pending.read_profile().prefs_import == "pending"
        page.locator("#save").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
    assert [body["prefs_reviewed"] for body in sent] == [True, True]
    assert pending.read_profile().prefs_import == "done"


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
@pytest.mark.parametrize("prior_edit", [False, True])
def test_cancelled_review_preserves_previous_intent(pending, pds, prior_edit) -> None:
    """Keep editing on the review's confirmation is no review: a later unrelated save leaves the import pending."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(pending, pds) as page:
        sent = _project_puts(page)
        if prior_edit:
            pds.group(page, "checks")
            pds.pick(page, "Merge method", "squash")
        page.get_by_role("button", name="Confirm merge preferences reviewed").click()
        pds.modal(page).get_by_role("button", name="Keep editing").click()
        expect(page.get_by_role("dialog")).to_have_count(0)  # the page takes edits again once it has closed
        pds.group(page, "agents")
        page.get_by_label("Rounds at most, builder").fill("4")
        expect(page.locator("#pending")).to_contain_text("Task reviews (builder) · Rounds at most: inherited → 4")
        page.locator("#save").click()  # the cancelled confirmation may still be fading out
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        expect(page.get_by_role("button", name="Confirm merge preferences reviewed")).to_have_count(
            0 if prior_edit else 1
        )

    assert [body["prefs_reviewed"] for body in sent] == [prior_edit]
    assert pending.read_profile().prefs_import == ("done" if prior_edit else "pending")
    assert pending.read_config().agents["builder"].max_rounds == 4
    if prior_edit:
        assert pending.read_config().prefs.merge_method == "squash"


@pytest.mark.browser
def test_explicit_review_waits_for_publication(pending_shared, tmp_path, monkeypatch, shared_repo, pds) -> None:
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
        page.get_by_role("button", name="Confirm merge preferences reviewed").click()
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        page.wait_for_function("() => document.querySelector('#save')?.loading === true")
        expect(page.locator("#status")).to_have_text("Saving…")
        expect(page.locator("#error")).to_be_hidden()  # nothing offers a retry the running save would ignore

        held[0].fallback()
        expect(page.locator("#error")).to_be_visible()
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")
        assert page.evaluate("() => document.querySelector('#save').loading") is False
        assert pending_shared.read_profile().prefs_import == "pending"

        page.locator("#save").click()  # the offered retry carries no new edit and is taken
        pds.modal(page).get_by_role("button", name="Save project settings").click()
        expect(page.locator("#error")).to_be_hidden()
        expect(page.locator("#status")).to_have_text("Saved this-project's settings. They apply to the next session.")

    assert [body["prefs_reviewed"] for body in sent] == [True, True]
    assert pending_shared.read_profile().prefs_import == "done"
    assert _fresh(tmp_path, shared_repo[1]).read_config().prefs is None


@pytest.fixture
def store_with_priced_models(store, monkeypatch):
    cache = prices(200_000, 200, 1000, prices(1_000_000, 200, 1000))
    cache.cache_write_price = cache.long_context.cache_write_price = 250
    cache.long_context.cache_read_price = 20
    opus = prices(200_000, 300, 1500, prices(1_000_000, 300, 1500, hour=800), hour=800)
    opus.cache_read_price = opus.long_context.cache_read_price = 30
    opus.cache_write_price = opus.long_context.cache_write_price = 375
    unknown = prices(200_000, 0, 0, prices(1_000_000, 0, 0))
    unknown.input_price = unknown.long_context.input_price = None
    crossing = prices(200_000, 200, 1000, prices(1_000_000, 400, 1000))
    crossing.cache_read_price, crossing.long_context.cache_read_price = 20, 10
    crossing.cache_write_price = crossing.long_context.cache_write_price = 250
    monkeypatch.setattr(
        model_choices,
        "_read",
        lambda: [
            offered_model("cache-only", ["low", "high"], tiers=cache),
            offered_model("claude-opus-5.5", ["low", "high"], tiers=opus),
            offered_model("unpriced", None, tiers=unknown),
            offered_model("crossing", None, tiers=crossing),
        ],
    )
    return store


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
def test_cost_arrows_rank_every_rate_and_leave_models_efforts_and_rates_unmarked(store_with_priced_models, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with settings_page(store_with_priced_models, pds) as page:
        row = page.locator("#set-agents-builder")
        tier = row.locator("p-segmented-control-item")
        pds.pick(page, "Model for builder", "cache-only")  # only its long tier's cache read is higher
        expect(tier.and_(page.locator("[value=long]"))).to_have_text("1M\u00a0\u2191")
        expect(tier.and_(page.locator("[value=default]"))).to_have_text("200k")
        for label in ("Model for builder", "Effort for builder"):
            options = pds.select(page, label).locator("p-select-option")
            expect(options).not_to_have_count(0)
            assert not any("\u2191" in said for said in options.all_inner_texts()), label
        rates = row.locator("p-table-cell").nth(1)  # under the model it prices
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


MEMORY_LABELS = {
    "outstanding_boost": "Points an outstanding rating adds to an entry's score",
    "unremarkable_penalty": "Points an unremarkable rating takes off an entry's score",
    "stale_factor": "Skipped ratings per other rating before an entry is stale",
    "purge_days": "Days a deleted entry waits before its file can be removed",
    "preflight_cap": "Lessons a step is told at its start, at most",
    "preflight_budget": "Character budget for a step's starting lessons",
    "recall_limit": "Entries the recall tool returns when it is given no limit",
    "explore_slots": "Recall slots for the least-rated entries",
    "challenge_slots": "Recall slots for the least-outstanding entries",
}
MEMORY_VALUES = {
    "outstanding_boost": 0.25, "unremarkable_penalty": 0.05, "stale_factor": 7, "purge_days": 14,
    "preflight_cap": 3, "preflight_budget": 1500, "recall_limit": 12, "explore_slots": 1, "challenge_slots": 3,
}  # fmt: skip


@pytest.mark.browser
def test_every_memory_value_is_saved_to_global_exactly_and_shown_again_after_a_reload(store, pds, monkeypatch) -> None:
    """The Memory group: nine values, each unset until saved on Global; decimals and zero reach the file as typed."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _layered(store, monkeypatch, GLOBAL, {}, {})
    with settings_page(store, pds) as page:
        url = page.url.split("#")[0]
        pds.pick(page, "Layer", "global")
        pds.group(page, "memory")
        for label in MEMORY_LABELS.values():
            expect(page.get_by_label(label)).to_have_attribute("placeholder", "Unset")
        for field, label in MEMORY_LABELS.items():
            page.get_by_label(label).fill(str(MEMORY_VALUES[field]))
        expect(page.locator("#groups a[href='#memory'] p-tag")).to_have_text("9 unsaved")
        expect(page.locator("#groups a[href='#guardrails'] p-tag")).to_have_count(0)
        expect(page.locator("#pending")).to_contain_text(f"{MEMORY_LABELS['stale_factor']}: unset → 7")
        _saved(page, pds, "Save global defaults", "the global")
        assert json.loads(store.global_path.read_text())["memory"] == MEMORY_VALUES

        page.goto(f"{url}&layer=global#memory")  # a reload shows what the file holds
        for field, label in MEMORY_LABELS.items():
            expect(page.get_by_label(label)).to_have_value(str(MEMORY_VALUES[field]))

        page.get_by_label(MEMORY_LABELS["purge_days"]).fill("0")  # zero is a value, not an unset one
        page.get_by_label(MEMORY_LABELS["explore_slots"]).fill("")  # blank clears it again
        expect(page.locator("#pending")).to_contain_text(f"{MEMORY_LABELS['purge_days']}: 14 → 0")
        expect(page.locator("#pending")).to_contain_text("Recall slots for the least-rated entries: 1 → unset")
        _saved(page, pds, "Save global defaults", "the global")
    assert json.loads(store.global_path.read_text())["memory"] == MEMORY_VALUES | {
        "purge_days": 0,
        "explore_slots": None,
    }


@pytest.mark.browser
def test_memory_values_are_read_only_off_global_and_the_filter_lists_the_unset_ones(store, pds, monkeypatch) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _layered(store, monkeypatch, GLOBAL | {"memory": {"stale_factor": 7}}, {}, {})
    with settings_page(store, pds) as page:
        pds.group(page, "memory")
        for layer in ("project", "machine"):
            pds.pick(page, "Layer", layer)
            stale = page.get_by_label(MEMORY_LABELS["stale_factor"])
            expect(stale).to_be_disabled()
            expect(stale).to_have_value("7")
            expect(page.locator("#set-memory-stale_factor")).to_contain_text("set on Global")
            expect(page.locator("#set-memory-purge_days")).to_contain_text("set on Global")
            expect(page.get_by_label(MEMORY_LABELS["purge_days"])).to_be_disabled()
        pds.pick(page, "Layer", "global")
        page.get_by_label(MEMORY_LABELS["stale_factor"]).fill("8")
        pds.pick(page, "Layer", "project")
        expect(page.get_by_label(MEMORY_LABELS["stale_factor"])).to_have_value("7")
        pds.pick(page, "Layer", "global")
        rows = page.locator("main p-table-row[data-setting]:visible")
        pds.pick(page, "Show", "unset")
        expect(rows).to_have_count(9)  # eight memory values and the curator's threshold; stale_factor is set
        expect(page.locator("#set-memory-stale_factor")).to_be_hidden()
        pds.pick(page, "Show", "set")
        expect(rows).to_have_count(1)
        expect(page.locator("#set-memory-stale_factor")).to_be_visible()


@pytest.mark.browser
def test_an_unset_memory_value_is_listed_by_the_overview_and_its_link_opens_the_row(store, pds, monkeypatch) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _layered(store, monkeypatch, GLOBAL, {}, {})
    with settings_page(store, pds) as page:
        url = page.url.split("#")[0]
        pds.group(page, "overview")
        assert _unset_count(page, "memory") == 10  # nine memory values and the curator's threshold
        page.locator("#unset-memory").get_by_role("link", name="Points an outstanding rating adds", exact=True).click()
        expect(page).to_have_url(f"{url}#memory")
        expect(page.locator("#set-memory-outstanding_boost p-text[color='error']")).to_have_count(1)
        expect(page.get_by_label(MEMORY_LABELS["outstanding_boost"])).to_be_disabled()  # the project layer: read-only
        expect(page.locator("#set-memory-outstanding_boost")).to_be_focused()


@pytest.mark.browser
def test_a_refused_memory_save_keeps_the_typed_values_and_says_why(store, pds, monkeypatch) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _layered(store, monkeypatch, GLOBAL, {}, {})
    before = store.global_path.read_bytes()
    with settings_page(store, pds) as page:
        pds.pick(page, "Layer", "global")
        pds.group(page, "memory")
        wrong = page.get_by_label(MEMORY_LABELS["stale_factor"])
        wrong.fill("0")  # the factor is at least 1
        page.get_by_label(MEMORY_LABELS["recall_limit"]).fill("12")
        page.locator(".bar").get_by_role("button", name="Save global defaults").click()
        pds.answer(page, "Save global defaults")
        expect(page.locator("#error")).to_be_visible()
        expect(page.locator("#error")).to_contain_text("stale_factor")
        expect(wrong).to_have_value("0")
        expect(page.get_by_label(MEMORY_LABELS["recall_limit"])).to_have_value("12")
        expect(page.locator("#groups a[href='#memory'] p-tag")).to_have_text("2 unsaved")
    assert store.global_path.read_bytes() == before


@pytest.mark.browser
def test_a_global_save_not_recorded_as_seen_says_why_whole(store, pds, monkeypatch, whole_error) -> None:
    """#971 P16: the save stands; its notice says whole why the next read may take it for a change from elsewhere."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _layered(store, monkeypatch, GLOBAL, {}, {})
    seen = local_home.root() / settings_seen.NAME
    seen.parent.mkdir(parents=True, exist_ok=True)
    seen.write_text(settings_seen.Seen(seen={}).model_dump_json())  # a read has recorded Global as found
    full = OSError(28, whole_error)
    full.add_note("NOTE-MARK")
    real = settings_seen.atomic_write

    def write(path: Path, text: str) -> None:
        if path == seen and refusing:
            raise full
        real(path, text)

    refusing: list[bool] = []
    monkeypatch.setattr(settings_seen, "atomic_write", write)
    with settings_page(store, pds) as page:
        pds.group(page, "overview")
        expect(page.locator("#reads-status")).to_contain_text("Last read")
        refusing.append(True)
        pds.pick(page, "Layer", "global")
        pds.group(page, "agents")
        page.get_by_label("Minutes per session, builder").fill("50")
        _saved(page, pds, "Save global defaults", "the global")
        said = f"The saved Global values could not be recorded as seen: OSError: [Errno 28] {whole_error}\nNOTE-MARK"
        expect(page.locator("#error")).to_be_visible()
        assert page.locator("#error").text_content().strip() == said
    assert '"minutes":50' in store.global_path.read_text().replace(" ", "")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_older_other_project_values_cannot_replace_a_newer_read(store, pds, tmp_path):
    beta = registry.register(clone(tmp_path / "beta"))
    other = Store.open(Path(beta.path))
    other.config_path.write_text(json.dumps({"format": CONFIG_FORMAT, "agents": {"builder": {"minutes": 20}}}))
    with refresh_page(store, pds) as (page, _base):
        expect(page.locator("#across-table")).to_contain_text("beta: 20")
        held = hold_first(page, f"**/p/{beta.id}/api/next/config")
        again = page.get_by_role("button", name="Read again")
        again.click()
        until(page, lambda: held)
        other.config_path.write_text(json.dumps({"format": CONFIG_FORMAT, "agents": {"builder": {"minutes": 45}}}))
        again.click()
        expect(page.locator("#across-table")).to_contain_text("beta: 45")
        hold_polls(page)
        with page.expect_request("**/config/models"):
            held[0][0].fulfill(response=held[0][1])
        expect(page.locator("#across-table")).to_contain_text("beta: 45")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_older_model_rates_cannot_replace_a_newer_read(store, pds, monkeypatch):
    with refresh_page(store, pds) as (page, _base):
        models = hold_first(page, "**/config/models")
        again = page.get_by_role("button", name="Read again")
        again.click()
        until(page, lambda: models)
        monkeypatch.setattr(
            model_choices,
            "_read",
            lambda: [offered_model("claude-opus-5.5", ["low", "medium", "high"], tiers=prices(200_000, 7, 15))],
        )
        again.click()
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 7 ")
        hold_polls(page)
        page.wait_for_function("window.settingsReadsFinished === 2")
        models[0][0].fulfill(response=models[0][1])
        page.wait_for_function("window.settingsReadsFinished === 3")
        expect(rates(page)).to_contain_text("in 7 ")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_second_read_stays_busy_when_the_first_refresh_finishes(store, pds):
    with refresh_page(store, pds) as (page, _base):
        layers = hold_first(page, "**/api/next/config", fetch=False)
        again = page.get_by_role("button", name="Read again")
        again.click()
        until(page, lambda: layers)
        second = hold_first(page, "**/config/read", "POST", fetch=False)
        again.click()
        until(page, lambda: second)
        expect(again).to_be_disabled()
        hold_polls(page)
        layers[0][0].continue_()
        page.wait_for_function("window.settingsReadsFinished === 2")
        assert again.is_disabled()
        second[0][0].continue_()
        page.wait_for_function("window.settingsReadsFinished === 3")
        expect(again).to_be_enabled()


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_unreadable_state_without_a_read_date_shows_its_failure(store, pds):
    with refresh_page(store, pds) as (page, _base):
        (local_home.root() / settings_seen.NAME).write_text("{not json")
        poll(page)
        expect(page.locator(".reads-failure")).to_contain_text("read state")
        expect(page.locator("#reads-status")).to_contain_text("No read is on record")


@pytest.mark.browser
@pytest.mark.timeout(120)
@pytest.mark.parametrize("old_fails", [False, True], ids=["source-failure", "old-503"])
def test_old_read_state_cannot_hide_a_newer_partial_read(store, pds, monkeypatch, old_fails):
    with refresh_page(store, pds) as (page, base):
        route, response = polled_read(page, base)

        def fail(*_args, **_kwargs):
            message = "could not read"
            raise OSError(message)

        monkeypatch.setattr(pack_files, "fetch", fail)
        page.get_by_role("button", name="Read again").click()
        failure = page.locator(".reads-failure")
        expect(failure).to_contain_text("Impeccable")
        hold_polls(page)
        with page.expect_request("**/api/next/config"):
            if old_fails:
                fail_read_state(route)
            else:
                route.fulfill(response=response)
        assert "Impeccable" in " ".join(failure.all_inner_texts())
        assert page.locator("#reads-error").count() == 0


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_old_read_state_keeps_data_without_clearing_a_newer_get_failure(store, pds):
    with refresh_page(store, pds) as (page, base):
        route, response = polled_read(page, base, failure=True)
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
def test_old_read_state_cannot_clear_a_failed_manual_read(store, pds):
    with refresh_page(store, pds) as (page, base):
        route, response = polled_read(page, base, failure=True)
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


def notice_on_disk() -> None:
    atomic_write(
        local_home.root() / settings_seen.NAME,
        settings_seen.Seen(
            notices=[
                settings_seen.Notice(
                    id="0000000000000001", key="agents.builder.minutes", old="45", new="50", at=datetime.now(UTC)
                )
            ]
        ).model_dump_json(),
    )


@pytest.mark.browser
@pytest.mark.timeout(120)
@pytest.mark.parametrize("reread_fails", [False, True], ids=["dismiss-GET", "dismiss-reread-503"])
def test_a_dismissal_blocks_older_read_state_even_if_rereading_fails(store, pds, reread_fails):
    notice_on_disk()
    with refresh_page(store, pds) as (page, base):
        entries = page.locator("#reads-changed li")
        expect(entries).to_have_count(1)
        route, response = polled_read(page, base)
        if reread_fails:
            page.route("**/config/read", fail_read_state)
        entries.first.get_by_role("button", name="Dismiss the change of builder · Minutes per session").click()
        if reread_fails:
            expect(page.locator("#reads-error")).to_contain_text("could not be read")
        expect(entries).to_have_count(0)
        hold_polls(page)
        with page.expect_request("**/api/next/config"):
            route.fulfill(response=response)
        assert entries.count() == 0


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_read_answered_after_dismissal_refreshes_current_notices(store, pds):
    notice_on_disk()
    with refresh_page(store, pds) as (page, _base):
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


class Outside:
    """A real shared Git remote, model-list seam and upstream release seam."""

    def __init__(self, shared_repo, tmp_path: Path, monkeypatch) -> None:
        self.root, remote = shared_repo
        self.other, self.mp = tmp_path / "other", monkeypatch
        _git(tmp_path, "clone", "-q", str(remote), str(self.other))
        monkeypatch.setenv(data_repo.VIEW, str(self.root))
        self.push("config.json", agents={"builder": {"model": "m1"}})
        _git(self.root, "pull", "-q")
        self.models(3)
        self.releases(b"[]")

    def models(self, price: float | None) -> None:
        def read():
            if price is None:
                message = "the CLI is gone"
                raise RuntimeError(message)
            return [offered_model("m1", ["low", "medium"], tiers=prices(200_000, price, 15))]

        self.mp.setattr(model_choices, "_read", read)

    def releases(self, answer: bytes | None) -> None:
        def fetch(url: str, *_args, **_kwargs) -> bytes:
            if answer is None:
                message = f"not reached: {url}"
                raise OSError(message)
            return answer

        self.mp.setattr(pack_files, "fetch", fetch)

    def push(self, rel: str, **fields: object) -> None:
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
        answer = httpx.post(f"{base}/p/{of}/api/next/config/read", headers=TOKEN, timeout=120)
        answer.raise_for_status()
        return answer.json()["reads"]

    @staticmethod
    def notices(base: str) -> list[str]:
        answer = httpx.get(f"{base}/api/next/projects", headers=TOKEN, timeout=30)
        answer.raise_for_status()
        return answer.json()["reads"]["notices"]


@pytest.fixture
def outside(shared_repo, tmp_path: Path, monkeypatch) -> Outside:
    return Outside(shared_repo, tmp_path, monkeypatch)


def big_enough(target) -> None:
    box = target.bounding_box()
    assert box is not None
    assert box["width"] >= 24, box
    assert box["height"] >= 24, box


def rates(page: Page):
    return page.locator("#set-agents-builder p-table-cell").nth(1)


def machine_layer(**fields: object) -> None:
    (local_home.root() / MACHINE_SETTINGS).write_text(json.dumps({"format": CONFIG_FORMAT, **fields}))


def opening_read_shows_partial_sources(page, pds) -> None:
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
@pytest.mark.timeout(120)
def test_read_again_updates_every_surface_and_keeps_drafts(tmp_path: Path, monkeypatch, pds, outside) -> None:
    a, _b = (registry.register(clone(tmp_path / n)) for n in ("alpha", "beta"))
    outside.releases(None)
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        outside.push("config.json", agents={"builder": {"model": "m1", "minutes": 41}})
        outside.models(4)
        page.goto(f"{base}/config?project={a.id}#token=t")
        opening_read_shows_partial_sources(page, pds)
        pds.group(page, "agents")
        page.get_by_label("Minutes per session, reviewer").fill("50")
        pds.group(page, "this-machine")
        pds.pick(page, "Layer", "machine")
        versions = pds.select(page, "Versions this machine takes")
        channel = "minor" if versions.evaluate("e => e.value") == "major" else "major"
        pds.pick(page, "Versions this machine takes", channel)
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
        for value in ("45 (global)", "33", "alpha: 30", "beta: 20"):
            expect(page.locator("#across-table")).to_contain_text(value)
        pds.group(page, "checks")
        expect(page.locator("#impeccable")).to_contain_text("0 releases behind")
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 5 ")
        pds.pick(page, "Layer", "project")
        expect(page.get_by_label("Minutes per session, builder")).to_have_value("30")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("50")
        pds.pick(page, "Layer", "machine")
        pds.group(page, "this-machine")
        expect(versions).to_have_js_property("value", channel)
        assert said == []


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_an_open_page_follows_reads_and_dismissals_made_elsewhere(tmp_path: Path, monkeypatch, pds, outside) -> None:
    import re  # noqa: PLC0415

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
        expect(changed).to_contain_text("builder · Minutes per session: unset → 45")
        expect(changed.get_by_role("button", name="Dismiss the change of builder · Minutes per session")).to_have_count(
            1
        )
        expect(page.locator(".reads-failure")).to_contain_text("Could not read: Impeccable releases")
        expect(status).to_contain_text(re.compile(rf"last full read\s+{re.escape(full)}"))
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 6 ")
        pds.group(page, "overview")
        httpx.post(
            f"{base}/api/next/settings-read/dismiss", json={"ids": Outside.notices(base)}, headers=TOKEN
        ).raise_for_status()
        expect(changed).to_have_count(0, timeout=READS_TIME * 1000)
        assert said == []


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_layer_that_does_not_read_still_shows_the_read(tmp_path: Path, monkeypatch, pds, outside) -> None:
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
        Outside.read(base, a.id)
        failure = page.locator(".reads-failure")
        pds.group(page, "overview")
        expect(failure).to_contain_text(f"Could not read: this machine's settings — {mine}", timeout=READS_TIME * 1000)
        expect(status).to_contain_text("last full read")
        pds.group(page, "agents")
        expect(rates(page)).to_contain_text("in 7 ")
        expect(page.get_by_label("Minutes per session, reviewer")).to_have_value("50")
        pds.group(page, "overview")
        page.get_by_role("button", name="Read again").click()
        expect(failure).to_contain_text(f"Could not read: this machine's settings — {mine}", timeout=READS_TIME * 1000)
        fresh = page.context.browser.new_page()
        said = errors(fresh)
        pds.only(fresh, base)
        fresh.goto(f"{base}/config?project={a.id}#token=t")
        expect(fresh.locator(".reads-failure")).to_contain_text("this machine's settings", timeout=READS_TIME * 1000)
        expect(fresh.locator("#groups")).to_have_count(0)
        mine.unlink()
        outside.models(None)
        fresh.get_by_role("button", name="Read again").click()
        expect(fresh.locator("#reads-status")).to_contain_text("last full read", timeout=READS_TIME * 1000)
        expect(fresh.locator(".reads-failure")).to_contain_text("Could not read: models")
        pds.group(fresh, "agents")
        expect(fresh.locator("#models-note")).to_contain_text("Models as last read; reading them again failed")
        expect(rates(fresh)).to_contain_text("in 7 ")
        assert [s for s in said if "409" not in s] == []


def notice_tabs_keep_the_draft(page, pds, base, alpha, beta):
    pds.group(page, "agents")
    minutes = page.get_by_label("Minutes per session, builder")
    minutes.fill("31")
    expect(page.locator("#pending")).not_to_have_text("No unsaved edits.")
    pds.group(page, "overview")
    entry = page.locator("#reads-changed li")
    page.context.add_init_script("sessionStorage.setItem('token', 't')")
    for name, layer, value in (
        ("builder · Minutes per session", "global", "50"),
        ("this machine", "machine", "33"),
        ("beta", "project", "20"),
    ):
        with page.context.expect_page() as opened:
            entry.get_by_role("link", name=name).click(modifiers=["ControlOrMeta"])
        tab = opened.value
        if name == "beta":
            expect(tab).to_have_url(f"{base}/config?project={beta.id}#agents")
        expect(pds.select(tab, "Layer")).to_have_js_property("value", layer, timeout=READS_TIME * 1000)
        expect(tab.get_by_label("Minutes per session, builder")).to_have_value(value)
        tab.close()
    expect(page).to_have_url(f"{base}/config?project={alpha.id}#overview")
    expect(page.locator("#error")).to_be_hidden()
    expect(pds.select(page, "Layer")).to_have_js_property("value", "project")
    pds.group(page, "agents")
    expect(minutes).to_have_value("31")
    expect(page.locator("#pending")).not_to_have_text("No unsaved edits.")
    minutes.fill("30")
    expect(page.locator("#pending")).to_have_text("No unsaved edits.")
    pds.group(page, "overview")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_notice_shows_old_to_new_its_overrides_and_its_link_opens_the_row(
    tmp_path: Path, monkeypatch, pds, outside
) -> None:
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
        notice_tabs_keep_the_draft(page, pds, base, a, b)
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
@pytest.mark.timeout(180)
@pytest.mark.usefixtures("outside")
def test_dismiss_one_in_settings_and_all_from_changes(tmp_path: Path, monkeypatch, pds) -> None:
    import re  # noqa: PLC0415

    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        said, batches = errors(page), []
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
        path = local_home.root() / settings_seen.NAME
        seen = settings_seen.Seen.model_validate_json(path.read_bytes())
        seen.notices = [
            settings_seen.Notice(id=f"{i:016x}", key="agents.builder.minutes", old="45", new="50", at=datetime.now(UTC))
            for i in range(202)
        ]
        atomic_write(path, seen.model_dump_json(indent=1) + "\n")
        reads = Outside.read(base, a.id)
        assert not reads["failures"], reads["failures"]
        n = len(reads["notices"])
        assert n == 202
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
        expect(page.locator("#groups")).to_be_visible(timeout=READS_TIME * 1000)
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


@pytest.mark.browser
def test_settings_say_this_machine_s_settings_could_not_be_read_and_read_them_again(
    tmp_path: Path, monkeypatch, pds
) -> None:
    a = registry.register(clone(tmp_path / "alpha"))
    with browsing(monkeypatch, pds) as (page, base):
        page.add_init_script("window.machineListenersAsked = 0; window.machineListenersDone = [];")

        def observe(route):
            response = route.fetch()
            body = response.text()
            end = "  await readMachine();\n  show();"
            assert body.count(end) == 1
            body = body.replace(
                end,
                "  const observed = ++window.machineListenersAsked;\n"
                + end
                + "\n  window.machineListenersDone.push(observed);",
            )
            route.fulfill(response=response, body=body)

        def busy(route):
            if route.request.method == "GET":
                route.fulfill(status=503, json={"detail": "the machine host is busy"})
            else:
                route.fallback()

        page.route("**/assets/page/config/main.mjs", observe)
        page.route("**/api/next/machine", busy)
        page.goto(f"{base}/config?project={a.id}#token=t")
        expect(page.locator("#unset-machine, #unset-none")).to_contain_text("could not be read")
        pds.group(page, "this-machine")
        unread = page.locator("#machine-unread")
        expect(unread).to_contain_text("Could not read this machine's settings")
        expect(unread).to_contain_text("tries again when the machine's state changes")
        page.unroute("**/api/next/machine", busy)
        page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
        expect(page.locator("#machine-login")).to_contain_text("Start at login")
        expect(unread).to_have_count(0)
        page.route("**/api/next/machine", busy)
        page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
        stale = page.locator("#machine-stale")
        expect(stale).to_contain_text("Could not read this machine's settings again")
        expect(page.locator("#machine-login")).to_contain_text("Start at login")
        machine_saved(page, pds, "major")
        expect(stale).to_have_count(0)
        page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
        expect(stale).to_be_visible()
        page.unroute("**/api/next/machine", busy)
        page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
        expect(stale).to_have_count(0)
        late_machine_read_keeps_the_save(page, pds)


def late_machine_read_keeps_the_save(page, pds) -> None:
    held = []

    def hold(route):
        if route.request.method == "GET":
            held.append(route)
        else:
            route.fallback()

    page.route("**/api/next/machine", hold)
    page.evaluate("document.dispatchEvent(new Event('owlbear-machine'))")
    until(page, lambda: held)
    observed = page.evaluate("window.machineListenersAsked")
    older = len(held)
    machine_saved(page, pds, "minor")
    for route in held[:older]:
        route.abort()
    page.unroute("**/api/next/machine", hold)
    for route in held[older:]:
        route.fallback()
    page.wait_for_function("(n) => window.machineListenersDone.includes(n)", arg=observed)
    expect(page.locator("#machine-stale")).to_have_count(0)


def machine_saved(page, pds, channel: str) -> None:
    pds.pick(page, "Layer", "machine")
    pds.pick(page, "Versions this machine takes", channel)
    page.get_by_role("region", name="This machine").get_by_role("button", name="Save machine settings").click()
    pds.answer(page, "Save machine settings")
    expect(page.locator("#status")).to_have_text("Saved this machine's settings.")


@pytest.mark.browser
def test_settings_say_a_failed_read_of_the_shared_repository_whole(
    tmp_path: Path, monkeypatch, pds, shared_repo, whole_error
) -> None:
    shared = shared_repo[0]
    monkeypatch.setenv(data_place.VIEW, str(shared))
    a = registry.register(clone(tmp_path / "alpha"))
    stderr, stdout = f"fatal: {shared / '.git' / 'index'} cannot be read\n{whole_error}", "OUT begins\nOUT ends"
    real = data_repo._git  # noqa: SLF001 - the repository's own Git calls are the boundary
    read = ("status", "--porcelain", "--", ".", f":(exclude)*/{data_repo.MEMORY}/*")

    def git(cwd, *args, until=None):
        if args[:1] != ("status",):
            return real(cwd, *args, until=until)
        return subprocess.CompletedProcess(["git", *args], 128, f"{stdout}\n", f"{stderr}\n")

    monkeypatch.setattr(data_repo, "_git", git)
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        page.goto(f"{base}/config?project={a.id}#token=t")
        notice = page.locator("#error")
        expect(notice).to_be_visible()
        failed = f"CalledProcessError: Command '{['git', *read]}' returned non-zero exit status 128."
        why = f"{failed}\nstderr:\n{stderr}\nstdout:\n{stdout}"
        assert notice.text_content().strip() == f"The shared settings repository {shared} cannot be read: {why}"
        assert said == []


@pytest.mark.browser
def test_settings_say_why_the_old_runtime_stays_whole(tmp_path: Path, monkeypatch, pds, whole_error) -> None:
    a = registry.register(clone(tmp_path / "alpha"))
    kept = local_home.root() / local_home.VERSIONS / "legacy-c1c1c1c1c1c1"
    kept.mkdir(parents=True)
    error = versions.VersionError(whole_error)
    error.add_note("a note on the failure")

    def refusing(_path):
        raise error

    monkeypatch.setattr(versions, "legacy", lambda: [kept])
    monkeypatch.setattr(leases, "unpinned", list)
    monkeypatch.setattr(versions, "keep_data", refusing)
    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        page.goto(f"{base}/config?project={a.id}#token=t")
        pds.group(page, "this-machine")
        page.get_by_role("button", name="Remove the old runtime").click()
        pds.answer(page, "Remove it")
        notice = page.locator("#error")
        expect(notice).to_be_visible()
        assert notice.text_content().strip() == f"VersionError: {whole_error}\na note on the failure"
        assert said == ["Failed to load resource: the server responded with a status of 409 (Conflict)"]
    assert kept.is_dir()


@pytest.mark.browser
def test_settings_show_a_failed_source_the_models_and_global_s_machine_settings_whole(
    tmp_path: Path, monkeypatch, pds, whole_error
) -> None:
    a = registry.register(clone(tmp_path / "alpha"))
    failed = f"RuntimeError: {whole_error}"
    unreadable = f"the global settings are unreadable: {whole_error}"

    def fail(*_args, **_kwargs):
        raise RuntimeError(whole_error)

    monkeypatch.setattr(pack_files, "fetch", fail)
    monkeypatch.setattr(model_choices, "_read", fail)

    def machine(route):
        body = route.fetch().json()
        body["resolved"]["notice"] = unreadable
        route.fulfill(json=body)

    with browsing(monkeypatch, pds) as (page, base):
        said = errors(page)
        page.route(f"{base}/api/next/machine", lambda r: machine(r) if r.request.method == "GET" else r.fallback())
        page.goto(f"{base}/config?project={a.id}#token=t")
        page.evaluate("() => import('/assets/page/config/main.mjs')")
        source = page.locator(".reads-failure").filter(has_text="Impeccable releases")
        expect(source).to_be_visible()
        assert failed in source.text_content()
        pds.group(page, "agents")
        models = page.locator("#models-note")
        expect(models).to_have_text(f"Could not read the offered models ({failed}); type a model name.")
        expect(models).to_have_js_property(
            "textContent", f"Could not read the offered models ({failed}); type a model name."
        )
        pds.group(page, "this-machine")
        notice = page.locator("#machine-notice")
        expect(notice).to_be_visible()
        assert notice.text_content() == unreadable
        assert said == []
