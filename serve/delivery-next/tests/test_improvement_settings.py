"""Improvement's settings (design §4): the Spotter's switch and category actions, their migrations and validation."""

import json
from datetime import date

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, resolve
from owlbear_delivery_next.settings.improvement import ALLOWED, CATEGORIES, Spotter
from owlbear_delivery_next.state_store import machine_settings, registry, settings_carry
from owlbear_delivery_next.state_store.layers import update_layer
from owlbear_delivery_next.state_store.store import StoreError, read_layer

MATRIX = {  # D-01M5WP8Z4ADZ5FN7RJDR17RQQ5, as the owner decided it
    "hand-off-fitness": {"record", "show-owner", "steer", "refuse-hand-off"},
    "course-and-constraints": {"record", "show-owner", "steer", "stop-and-resume", "stop-and-ask"},
    "outside-state-changes": {"record", "show-owner", "stop-and-resume", "stop-and-ask"},
    "irreversible-harm": {"record", "show-owner", "stop-and-resume", "stop-and-ask"},
}
RECORD = dict.fromkeys(CATEGORIES.values(), "record")
ON = Spotter(switch="on", steer_share=0, intervention_cap=1, verbose="off", looks=["hand-off"], **RECORD)


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


def _written(tmp_path, data: dict, name: str = "config", fmt: int = 11) -> object:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"format": fmt, **data}))
    return path


@pytest.mark.parametrize(
    ("switch", "expected"), [(True, Spotter(switch="on", **RECORD)), (False, Spotter(switch="off"))]
)
def test_the_watcher_switch_becomes_the_spotter_switch_and_its_role_moves(tmp_path, switch, expected):
    path = _written(tmp_path, {"watcher": switch, "agents": {"watcher": {"model": "gpt-6-luna", "effort": "medium"}}})
    layer = read_layer(path, GlobalLayer)
    assert (layer.format, layer.spotter, layer.agents["spotter"].model) == (
        config.CONFIG_FORMAT, expected, "gpt-6-luna")  # fmt: skip
    assert "watcher" not in layer.agents
    assert layer.spotter is not None
    assert layer.spotter.looks is None  # nothing invented: the rest starts unset


def test_an_unset_watcher_switch_stays_unset_in_every_layer(tmp_path):
    for model in (GlobalLayer, MachineLayer, Layer):
        layer = read_layer(_written(tmp_path, {"watcher": None}, model.__name__), model)
        assert layer.spotter is None


def test_the_matrix_is_the_owners_and_each_category_refuses_any_other_action():
    assert {c: set(a) for c, a in ALLOWED.items()} == MATRIX
    assert set(CATEGORIES.values()) == {"hand_off_fitness", "course_and_constraints", "outside_state_changes",
                                         "irreversible_harm"}  # fmt: skip
    for category, field in CATEGORIES.items():
        for action in sorted(set().union(*MATRIX.values())):
            if action in MATRIX[category]:
                assert Spotter.model_validate({field: action}).actions() == {category: action}
            else:
                with pytest.raises(ValidationError, match=field):
                    Spotter.model_validate({field: action})


@pytest.mark.usefixtures("no_base")
@pytest.mark.parametrize("switch", [None, "off", "on"])
def test_every_unset_spotter_setting_is_listed_whatever_the_switch(switch):
    got = resolve(GlobalLayer(spotter=Spotter(switch=switch)), Layer())
    listed = [k for k in got.missing if k.startswith("spotter.")]
    required = ["switch", *CATEGORIES.values(), "steer_share", "intervention_cap", "verbose", "looks"]
    assert listed == [f"spotter.{k}" for k in required if not (k == "switch" and switch)]
    assert "spotter.verbose_until" not in listed  # optional


@pytest.mark.usefixtures("no_base")
def test_the_sample_rate_is_needed_only_when_sample_is_a_look():
    assert not [k for k in resolve(GlobalLayer(spotter=ON), Layer()).missing if k.startswith("spotter.")]
    sampled = ON.model_copy(update={"looks": ["hand-off", "sample"]})
    missing = resolve(GlobalLayer(spotter=sampled), Layer()).missing
    assert [k for k in missing if k.startswith("spotter.")] == ["spotter.sample_rate"]


def test_a_project_overrides_one_field_and_inherits_the_rest():
    glob = GlobalLayer(spotter=ON.model_copy(update={"steer_share": 10, "verbose": "on"}))
    got = resolve(glob, Layer(spotter=Spotter(switch="off", irreversible_harm="stop-and-ask")))
    assert (got.spotter.switch, got.spotter.steer_share) == ("off", 10)
    assert (got.sources["spotter.switch"], got.sources["spotter.verbose"]) == ("project", "global")
    assert got.spotter.actions() == dict.fromkeys(CATEGORIES, "record") | {"irreversible-harm": "stop-and-ask"}


@pytest.mark.parametrize(
    "bad",
    [{"looks": []}, {"looks": ["plan", "plan"]}, {"looks": ["mid-flow"]}, {"steer_share": 101},
     {"intervention_cap": 21}, {"verbose_until": "next week"}, {"switch": "learning"}, {"switch": True},
     {"mode": "off"}, {"hand_off_fitness": "interrupt"}],
)  # fmt: skip
def test_invalid_spotter_values_are_refused(bad):
    with pytest.raises(ValidationError):
        Spotter.model_validate(bad)


KEPT = {"steer_share": 20, "intervention_cap": 3, "verbose": "on", "verbose_until": "2026-12-31",
        "looks": ["hand-off", "sample"], "sample_rate": 5}  # fmt: skip


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("off", {"switch": "off"}), ("learning", {"switch": "on", **RECORD}), ("live", {"switch": "on"}),
     (None, {})],
)  # fmt: skip
@pytest.mark.parametrize("model", [GlobalLayer, MachineLayer, Layer])
def test_each_old_mode_migrates_in_every_layer_and_keeps_the_other_values(tmp_path, mode, expected, model):
    layer = read_layer(_written(tmp_path, {"spotter": {"mode": mode, **KEPT}}, model.__name__, 13), model)
    assert (layer.format, layer.spotter) == (config.CONFIG_FORMAT, Spotter(**KEPT, **expected))


@pytest.mark.parametrize("mode", ["typo", "Learning", "on", False, True, 7, 0.5, [], ["live"], {}, {"mode": "off"}])
@pytest.mark.parametrize("model", [GlobalLayer, MachineLayer, Layer])
def test_an_unknown_mode_is_refused_never_guessed_into_a_switch(tmp_path, mode, model):
    path = _written(tmp_path, {"spotter": {"mode": mode, "looks": ["plan"]}}, model.__name__, 13)
    with pytest.raises(StoreError, match="cannot be migrated to format 14"):
        read_layer(path, model)


def test_a_layer_without_a_mode_or_a_spotter_migrates_unchanged(tmp_path):
    assert read_layer(_written(tmp_path, {"spotter": {"looks": ["plan"]}}, fmt=13), Layer).spotter == Spotter(
        looks=["plan"])  # fmt: skip
    assert read_layer(_written(tmp_path, {"sessions": 2}, fmt=13), Layer).spotter is None


def _layers(tmp_path, glob: dict, machine: dict, project: dict) -> config.Settings:
    """Three layer files, each as an older or the current Delivery wrote it, read and resolved as a step does."""
    return resolve(
        read_layer(_written(tmp_path, glob, "global", glob.pop("format", 13)), GlobalLayer),
        read_layer(_written(tmp_path, project, "project", project.pop("format", 13)), Layer),
        read_layer(_written(tmp_path, machine, "machine", machine.pop("format", 13)), MachineLayer),
    )


@pytest.mark.usefixtures("no_base")
def test_a_narrower_live_layer_turns_on_and_inherits_the_actions_a_wider_learning_one_records(tmp_path):
    got = _layers(tmp_path, {"spotter": {"mode": "learning"}}, {"spotter": {"mode": "live"}}, {})
    assert (got.spotter.switch, got.sources["spotter.switch"]) == ("on", "machine")
    assert got.spotter.actions() == dict.fromkeys(CATEGORIES, "record")
    assert {got.sources[f"spotter.{f}"] for f in CATEGORIES.values()} == {"global"}
    assert not [k for k in got.missing if k.removeprefix("spotter.") in CATEGORIES.values()]


@pytest.mark.usefixtures("no_base")
def test_a_project_that_learned_records_every_category_over_wider_acting_actions(tmp_path):
    acting = {"switch": "on", "hand_off_fitness": "steer", "course_and_constraints": "stop-and-ask",
              "outside_state_changes": "show-owner", "irreversible_harm": "stop-and-resume"}  # fmt: skip
    got = _layers(tmp_path, {"format": config.CONFIG_FORMAT, "spotter": acting}, {}, {"spotter": {"mode": "learning"}})
    assert got.spotter.actions() == dict.fromkeys(CATEGORIES, "record")
    assert {got.sources[f"spotter.{f}"] for f in (*CATEGORIES.values(), "switch")} == {"project"}


@pytest.mark.usefixtures("no_base")
def test_a_project_setting_one_action_inherits_the_others(tmp_path):
    project = {"format": config.CONFIG_FORMAT, "spotter": {"hand_off_fitness": "refuse-hand-off"}}
    got = _layers(tmp_path, {"spotter": {"mode": "learning"}}, {"spotter": {"mode": "off"}}, project)
    assert (got.spotter.switch, got.sources["spotter.switch"]) == ("off", "machine")
    assert (got.spotter.hand_off_fitness, got.sources["spotter.hand_off_fitness"]) == ("refuse-hand-off", "project")
    assert {got.sources[f"spotter.{f}"] for f in CATEGORIES.values() if f != "hand_off_fitness"} == {"global"}
    assert got.spotter.irreversible_harm == "record"


@pytest.mark.usefixtures("no_base")
def test_a_fresh_carry_switches_the_spotter_on_and_leaves_every_action_unset(shared_repo):
    shared = DataRepo(shared_repo[0])
    settings_carry.carry(shared)
    glob = read_layer(shared.global_path, GlobalLayer)
    assert glob.spotter == Spotter(switch="on")
    got = resolve(glob, Layer())
    assert (got.spotter.switch, got.sources["spotter.switch"], got.spotter.actions()) == ("on", "global", {})
    assert {f"spotter.{f}" for f in CATEGORIES.values()} <= set(got.missing)


@pytest.mark.usefixtures("no_base")
def test_actions_cleared_after_the_migration_stay_cleared_and_inherit(tmp_path):
    path = _written(tmp_path, {"spotter": {"mode": "learning", "looks": ["plan"]}}, "project", 13)
    update_layer(path, Layer, lambda layer: layer.model_copy(
        update={"spotter": layer.spotter.model_copy(update=dict.fromkeys(CATEGORIES.values()))}))  # fmt: skip
    written = json.loads(path.read_text())
    assert (written["format"], "mode" in written["spotter"]) == (config.CONFIG_FORMAT, False)
    reopened = read_layer(path, Layer)
    assert reopened.spotter == Spotter(switch="on", looks=["plan"])  # no migration runs again
    glob = GlobalLayer(spotter=Spotter(hand_off_fitness="steer"))
    got = resolve(glob, reopened)
    assert (got.spotter.hand_off_fitness, got.sources["spotter.hand_off_fitness"]) == ("steer", "global")
    assert "spotter.irreversible_harm" in got.missing


def test_verbose_counts_as_off_after_its_date():
    until = Spotter(verbose="on", verbose_until="2026-10-30")
    assert (until.verbose_on(date(2026, 10, 30)), until.verbose_on(date(2026, 10, 31))) == (True, False)
    assert Spotter(verbose="on").verbose_on(date(2099, 1, 1))
    assert not Spotter(verbose="off").verbose_on(date(2026, 1, 1))


def test_the_machine_values_inherit_global_and_validate_the_enrolled_folders():
    glob = config.MachineValues(retro_budget=9, enrolled_chats=["/w"])
    got = machine_settings.resolve(registry.Settings(retro_budget=5), glob)
    assert (got.retro_budget, got.enrolled_chats, got.sources["enrolled_chats"]) == (5, ["/w"], "global")
    with pytest.raises(ValidationError):
        config.MachineValues(enrolled_chats=["relative/path"])
    with pytest.raises(ValidationError):
        config.MachineValues(enrolled_chats=["/w", "/w"])
