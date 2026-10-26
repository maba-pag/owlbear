"""Config format 13: upstream's format 12 Spotter layers and our preferences meet in one chain (merge of main)."""

import json

import pytest

from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store.store import FormatTooNewError, read_layer


def _written(tmp_path, data: dict, fmt: int) -> object:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"format": fmt, **data}))
    return path


def test_the_format_is_thirteen():
    assert config.CONFIG_FORMAT == 13


def test_a_published_format_12_layer_keeps_its_spotter_values_and_starts_without_preferences(tmp_path):
    spotter = {"mode": "learning", "steer_share": 20, "intervention_cap": 3, "verbose": "off", "looks": ["hand-off"]}
    agents = {"spotter": {"model": "gpt-6-luna", "effort": "medium"}}
    layer = read_layer(_written(tmp_path, {"spotter": spotter, "agents": agents}, 12), Layer)
    assert layer.format == 13
    assert layer.spotter is not None
    assert layer.spotter.mode == "learning"
    assert layer.spotter.steer_share == 20
    assert layer.spotter.intervention_cap == 3
    assert layer.agents["spotter"].model == "gpt-6-luna"
    assert layer.prefs is None


def test_a_format_11_watcher_layer_gets_the_spotter_and_the_preferences_slot(tmp_path):
    path = _written(tmp_path, {"watcher": False, "agents": {"watcher": {"model": "gpt-6-luna", "effort": "low"}}}, 11)
    layer = read_layer(path, Layer)
    assert layer.format == 13
    assert layer.spotter is not None
    assert layer.spotter.mode == "off"
    assert layer.agents["spotter"].model == "gpt-6-luna"
    assert "watcher" not in layer.agents
    assert layer.prefs is None


def test_an_existing_format_13_layer_is_read_unchanged(tmp_path):
    prefs = {"merge_method": "squash", "delete_remote_branch": False}
    layer = read_layer(_written(tmp_path, {"prefs": prefs, "spotter": {"mode": "off"}}, 13), Layer)
    assert layer.format == 13
    assert layer.prefs is not None
    assert layer.prefs.merge_method == "squash"
    assert layer.prefs.delete_remote_branch is False
    assert layer.spotter is not None
    assert layer.spotter.mode == "off"


def test_a_newer_format_than_13_is_refused(tmp_path):
    with pytest.raises(FormatTooNewError):
        read_layer(_written(tmp_path, {}, 14), Layer)
