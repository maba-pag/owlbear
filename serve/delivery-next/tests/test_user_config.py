"""The user-config settings: layered like any setting, no code default, unset missing.

D-01M5YE4P5317N1HWD0QN6N05E0, D-01M69EBRBBW97001KZ43C0BJM1, D-01M6DX04FRP680Z4GGHK5B9VRC.
"""

import json

import pytest

from owlbear_delivery_next.settings import config, migrations
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, resolve
from owlbear_delivery_next.state_store.store import StoreError, read_layer

KEYS = ("load_user_instructions", "load_user_skills", "load_user_memory")


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


@pytest.mark.usefixtures("no_base")
def test_unset_switches_are_missing_and_none_on_the_page():
    got = resolve(None, Layer())
    assert set(KEYS) <= set(got.missing)
    page = got.page()
    assert [page[key] for key in KEYS] == [None, None, None]
    assert not set(KEYS) & set(got.sources)


@pytest.mark.usefixtures("no_base")
@pytest.mark.parametrize("key", KEYS)
def test_an_explicit_false_is_set_not_missing(key):
    got = resolve(GlobalLayer(**{key: False}), Layer())
    assert (getattr(got, key), got.sources[key], key in got.missing) == (False, "global", False)
    assert got.page()[key] is False


@pytest.mark.usefixtures("no_base")
@pytest.mark.parametrize("key", KEYS)
@pytest.mark.parametrize(
    ("layers", "value", "source"),  # each layer's value: Global, this machine, the project; None inherits
    [
        ((False, None, None), False, "global"),
        ((True, None, None), True, "global"),
        ((False, True, None), True, "machine"),
        ((True, False, None), False, "machine"),
        ((False, True, False), False, "project"),
        ((False, None, True), True, "project"),
        ((None, None, True), True, "project"),
        ((None, False, None), False, "machine"),
    ],
)
def test_each_layer_sets_or_inherits_and_the_project_wins(key, layers, value, source):
    glob, machine, project = layers
    got = resolve(GlobalLayer(**{key: glob}), Layer(**{key: project}), MachineLayer(**{key: machine}))
    assert (getattr(got, key), got.sources[key], key in got.missing) == (value, source, False)
    assert got.page()[key] is value


def test_a_format_16_layer_loads_with_every_switch_unset(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"format": 16, "pr_marker": False, "sessions": 2}))
    for model in (Layer, MachineLayer, GlobalLayer):
        layer = read_layer(path, model)
        assert (layer.format, layer.pr_marker, layer.sessions) == (config.CONFIG_FORMAT, False, 2)
        assert [getattr(layer, key) for key in KEYS] == [None, None, None]
    assert migrations.CONFIG[16] is migrations.user_config_added
    assert migrations.GLOBAL[16] is migrations.user_config_added
    assert migrations.GLOBAL[15] is migrations.credit_limits_written


@pytest.mark.parametrize("version", [17, 18])
def test_a_format_17_or_18_layer_keeps_its_switches_leaves_memory_unset_and_refuses_anything_but_a_boolean(
    tmp_path, version
):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"format": version, "load_user_instructions": True, "load_user_skills": False}))
    for model in (Layer, MachineLayer, GlobalLayer):
        layer = read_layer(path, model)
        assert layer.format == config.CONFIG_FORMAT
        assert [getattr(layer, key) for key in KEYS] == [True, False, None]
    path.write_text(json.dumps({"format": version, "load_user_skills": "yes"}))
    with pytest.raises(StoreError):
        read_layer(path, Layer)


@pytest.mark.usefixtures("no_base")
def test_the_guard_level_is_unset_until_a_layer_sets_it_and_the_project_wins():
    got = resolve(None, Layer())
    assert ("guard_level" in got.missing, got.page()["guard_level"]) == (True, None)
    got = resolve(GlobalLayer(guard_level="standard"), Layer(), MachineLayer(guard_level="off"))
    assert (got.guard_level, got.sources["guard_level"]) == ("off", "machine")
    got = resolve(GlobalLayer(guard_level="standard"), Layer(guard_level="lenient"), MachineLayer(guard_level="off"))
    assert (got.guard_level, got.sources["guard_level"], got.page()["guard_level"]) == ("lenient", "project", "lenient")


def test_a_format_19_layer_loads_with_the_guard_level_unset_and_refuses_an_unknown_level(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"format": 19, "load_user_memory": True}))
    for model in (Layer, MachineLayer, GlobalLayer):
        layer = read_layer(path, model)
        assert (layer.format, layer.load_user_memory, layer.guard_level) == (config.CONFIG_FORMAT, True, None)
    assert migrations.CONFIG[19] is migrations.guard_level_added
    path.write_text(json.dumps({"format": 20, "guard_level": "loose"}))
    with pytest.raises(StoreError):
        read_layer(path, Layer)
