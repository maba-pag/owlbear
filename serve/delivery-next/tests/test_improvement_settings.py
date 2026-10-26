"""Improvement's settings (design §4): the watcher's migration to the Spotter, validation and the machine values."""

import json
from datetime import date

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.machine_host import machine_settings, registry
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, resolve
from owlbear_delivery_next.settings.improvement import Spotter
from owlbear_delivery_next.state_store.store import read_layer


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


def _written(tmp_path, data: dict, name: str = "config") -> object:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"format": 11, **data}))
    return path


@pytest.mark.parametrize(("switch", "mode"), [(True, "learning"), (False, "off")])
def test_the_watcher_switch_becomes_the_spotter_mode_and_its_role_moves(tmp_path, switch, mode):
    path = _written(tmp_path, {"watcher": switch, "agents": {"watcher": {"model": "gpt-6-luna", "effort": "medium"}}})
    layer = read_layer(path, GlobalLayer)
    assert (layer.format, layer.spotter, layer.agents["spotter"].model) == (
        config.CONFIG_FORMAT, Spotter(mode=mode), "gpt-6-luna")  # fmt: skip
    assert "watcher" not in layer.agents
    assert layer.spotter is not None
    assert layer.spotter.looks is None  # nothing invented: the rest starts unset


def test_an_unset_watcher_switch_stays_unset_in_every_layer(tmp_path):
    for model in (GlobalLayer, MachineLayer, Layer):
        layer = read_layer(_written(tmp_path, {"watcher": None}, model.__name__), model)
        assert layer.spotter is None


@pytest.mark.usefixtures("no_base")
def test_the_sample_rate_is_needed_only_when_sample_is_a_look():
    some = Spotter(mode="learning", steer_share=0, intervention_cap=1, verbose="off", looks=["hand-off"])
    assert not [k for k in resolve(GlobalLayer(spotter=some), Layer()).missing if k.startswith("spotter.")]
    sampled = some.model_copy(update={"looks": ["hand-off", "sample"]})
    missing = resolve(GlobalLayer(spotter=sampled), Layer()).missing
    assert [k for k in missing if k.startswith("spotter.")] == ["spotter.sample_rate"]


def test_a_project_overrides_one_field_and_inherits_the_rest():
    glob = GlobalLayer(spotter=Spotter(mode="learning", steer_share=10, intervention_cap=2, verbose="on",
                                       looks=["hand-off"]))  # fmt: skip
    got = resolve(glob, Layer(spotter=Spotter(mode="off")))
    assert (got.spotter.mode, got.spotter.steer_share, got.sources["spotter.mode"], got.sources["spotter.verbose"]) == (
        "off", 10, "project", "global")  # fmt: skip


@pytest.mark.parametrize(
    "bad",
    [{"looks": []}, {"looks": ["plan", "plan"]}, {"looks": ["mid-flow"]}, {"steer_share": 101},
     {"intervention_cap": 21}, {"verbose_until": "next week"}, {"mode": "on"}],
)  # fmt: skip
def test_invalid_spotter_values_are_refused(bad):
    with pytest.raises(ValidationError):
        Spotter.model_validate(bad)


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
