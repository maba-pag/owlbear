"""Settings format 16 and machine.json format 8 (D-01M5XCD49YHHR1NQKKY8TQD0C3): the daily budgets go and the credit
limits are written into Global only, where it has none; every other value stays. The machine host's start saves and
publishes them once (``test_machine_settings``)."""

import json
import math

import pytest

from owlbear_delivery_next.settings import carried, migrations
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, MachineValues
from owlbear_delivery_next.settings.improvement import Spotter
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import StoreError, read_layer

LIMITS = {"look": 0.75, "retro": 20.0, "replay": 90.0}
SPOTTER = {"switch": "on", "steer_share": 0, "intervention_cap": 2, "verbose": "off", "looks": ["hand-off"],
           "hand_off_fitness": "record", "course_and_constraints": "record", "outside_state_changes": "record",
           "irreversible_harm": "record"}  # fmt: skip
MACHINE = {"channel": "minor", "sessions": 3, "spotter_budget": 50, "retro_budget": 20, "retro_verbose_cap": 5,
           "retro_after_change": "on", "enrolled_chats": ["/w"]}  # fmt: skip


def _file(tmp_path, data: dict) -> object:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    return path


def _limits(glob: GlobalLayer) -> tuple[float | None, float | None, float | None]:
    machine = glob.machine or MachineValues()
    return glob.spotter.look_credit_limit if glob.spotter else None, machine.retro_run_credit_limit, (
        machine.replay_run_credit_limit)  # fmt: skip


def test_the_written_values_are_five_times_the_assumed_costs():
    replay = 5 * 2 * 59 * 0.15  # 59 scored cases, twice, at 0.15 a look: 88.5, rounded up
    assert (carried.LOOK_CREDIT_LIMIT, carried.RETRO_RUN_CREDIT_LIMIT, carried.REPLAY_RUN_CREDIT_LIMIT) == (
        5 * 0.15, 5 * 4.0, 90.0)  # fmt: skip
    assert replay <= carried.REPLAY_RUN_CREDIT_LIMIT < replay + 5
    assert _limits(carried.layer().model_copy(update={"machine": carried.MACHINE})) == tuple(LIMITS.values())


def test_a_format_15_global_drops_its_budgets_and_gets_the_limits_keeping_every_other_value(tmp_path):
    glob = read_layer(_file(tmp_path, {"format": 15, "spotter": SPOTTER, "machine": MACHINE, "sessions": 2}),
                      GlobalLayer)  # fmt: skip
    assert glob.format == 18
    assert _limits(glob) == tuple(LIMITS.values())
    assert glob.spotter.model_dump(exclude_none=True) == SPOTTER | {"look_credit_limit": 0.75}
    kept = {k: v for k, v in MACHINE.items() if k not in migrations.DAILY}
    assert glob.machine.model_dump(exclude_none=True) == kept | {"retro_run_credit_limit": 20.0,
                                                                 "replay_run_credit_limit": 90.0}  # fmt: skip
    assert glob.sessions == 2


@pytest.mark.parametrize("sections", [{}, {"spotter": None, "machine": None}])
def test_a_global_without_the_sections_or_with_them_null_gets_them_with_the_limits_alone(tmp_path, sections):
    glob = read_layer(_file(tmp_path, {"format": 15, **sections, "curator_threshold": 90}), GlobalLayer)
    assert _limits(glob) == tuple(LIMITS.values())
    assert glob.spotter == Spotter(look_credit_limit=0.75)  # the switch and the rest stay unset
    assert glob.machine == MachineValues(retro_run_credit_limit=20.0, replay_run_credit_limit=90.0)
    assert glob.curator_threshold == 90


@pytest.mark.parametrize("sections", [{"spotter": False}, {"machine": []}, {"spotter": "on"}, {"machine": 0}])
def test_a_section_that_is_neither_a_mapping_nor_null_is_refused_never_replaced(tmp_path, sections):
    with pytest.raises(StoreError, match="cannot be migrated"):
        read_layer(_file(tmp_path, {"format": 15, **sections}), GlobalLayer)


def test_an_empty_section_gets_the_limits_in_it(tmp_path):
    glob = read_layer(_file(tmp_path, {"format": 15, "spotter": {}, "machine": {}}), GlobalLayer)
    assert _limits(glob) == tuple(LIMITS.values())


def test_an_older_global_gets_them_through_the_whole_chain(tmp_path):
    glob = read_layer(_file(tmp_path, {"format": 13, "spotter": {"mode": "learning"}}), GlobalLayer)
    spotter = glob.spotter
    assert (spotter.switch, spotter.hand_off_fitness, spotter.look_credit_limit) == ("on", "record", 0.75)


@pytest.mark.parametrize("model", [Layer, MachineLayer])
def test_a_project_or_this_machine_s_layer_gets_no_limit(tmp_path, model):
    layer = read_layer(_file(tmp_path, {"format": 15, "spotter": {"switch": "off"}}), model)
    assert (layer.format, layer.spotter) == (18, Spotter(switch="off"))


def test_a_format_16_global_whose_limits_the_owner_cleared_stays_without_them(tmp_path):
    glob = read_layer(_file(tmp_path, {"format": 16, "spotter": {"switch": "on"}, "machine": {"sessions": 2}}),
                      GlobalLayer)  # fmt: skip
    assert _limits(glob) == (None, None, None)


@pytest.mark.parametrize("bad", [-1, 1.5, "5", True, None])
def test_a_budget_the_format_never_allowed_is_refused_not_dropped(tmp_path, bad):
    path = _file(tmp_path, {"format": 15, "machine": {"retro_budget": bad}})
    if bad is None:
        assert read_layer(path, GlobalLayer).machine.retro_run_credit_limit == 20.0  # null was allowed: dropped
        return
    with pytest.raises(StoreError, match="cannot be migrated"):
        read_layer(path, GlobalLayer)


@pytest.mark.parametrize(
    ("fmt", "said"),
    [(16, r"cannot be migrated to format 18"), (18, r"unknown field machine\.spotter_budget")],
)  # a format-16 layer is migrated first, so its refusal says so; the current format names the field
def test_a_format_16_or_later_layer_naming_a_budget_is_refused(tmp_path, fmt, said):
    with pytest.raises(StoreError, match=said):
        read_layer(_file(tmp_path, {"format": fmt, "machine": {"spotter_budget": 5}}), GlobalLayer)


VALUES = [(1, True), (0.4, True), (2.5, True), (1e-9, True), (0, False), (1e-10, False), (-1, False), (True, False),
          ("0.5", False), (math.inf, False), (math.nan, False)]  # fmt: skip  # at least one nano-credit


@pytest.mark.parametrize(("value", "ok"), VALUES)
def test_a_credit_limit_is_a_finite_amount_above_zero(tmp_path, value, ok):
    for data in ({"spotter": {"look_credit_limit": value}}, {"machine": {"retro_run_credit_limit": value}},
                 {"machine": {"replay_run_credit_limit": value}}):  # fmt: skip
        path = _file(tmp_path, {"format": 16, **data})
        if ok:
            glob = read_layer(path, GlobalLayer)
            assert float(value) in _limits(glob)
        else:
            with pytest.raises(StoreError):
                read_layer(path, GlobalLayer)


def _machine_json(data: dict) -> None:
    path = registry._home() / registry.MACHINE  # noqa: SLF001
    path.write_text(json.dumps(data))


@pytest.mark.parametrize("legacy", [5, "5", 5.0, True, None])
def test_a_format_7_machine_drops_its_budgets_from_its_settings_and_a_move_s_kept_values(legacy):
    budgets = dict.fromkeys(migrations.DAILY, legacy)
    _machine_json({"format": 7, "settings": {"sessions": 2, **budgets}, "settings_moving": {"channel": "major",
                                                                                            **budgets}})  # fmt: skip
    machine = registry.load()
    assert (machine.settings, machine.settings_moving) == (registry.Settings(sessions=2),
                                                           registry.Settings(channel="major"))  # fmt: skip
    with registry.locked():
        registry.save(machine)
    assert json.loads((registry._home() / registry.MACHINE).read_text())["format"] == 9  # noqa: SLF001


@pytest.mark.parametrize("bad", [-1, 1.5, "x"])
def test_a_format_7_budget_that_format_never_allowed_is_refused(bad):
    _machine_json({"format": 7, "settings": {"retro_budget": bad}})
    with pytest.raises(registry.RegistryError):
        registry.load()


def test_a_format_8_machine_or_a_save_naming_a_budget_is_refused():
    _machine_json({"format": 8, "settings": {"spotter_budget": 5}})
    with pytest.raises(registry.RegistryError):
        registry.load()
    with pytest.raises(ValueError, match="spotter_budget"):
        registry.Settings.model_validate({"spotter_budget": 5})
    assert registry.Settings.model_validate({"retro_run_credit_limit": 3}).retro_run_credit_limit == 3.0
