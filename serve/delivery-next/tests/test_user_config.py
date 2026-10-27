"""The user-config switches (D-01M5YE4P5317N1HWD0QN6N05E0): layered like any setting, no code default, unset missing."""

import json

import pytest

from owlbear_delivery_next.settings import config, migrations
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, resolve
from owlbear_delivery_next.state_store.store import StoreError, read_layer

KEYS = ("load_user_instructions", "load_user_skills")


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


@pytest.mark.usefixtures("no_base")
def test_unset_switches_are_missing_and_none_on_the_page():
    got = resolve(None, Layer())
    assert set(KEYS) <= set(got.missing)
    page = got.page()
    assert (page["load_user_instructions"], page["load_user_skills"]) == (None, None)
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


def test_a_format_16_layer_loads_with_both_switches_unset(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"format": 16, "pr_marker": False, "sessions": 2}))
    for model in (Layer, MachineLayer, GlobalLayer):
        layer = read_layer(path, model)
        assert (layer.format, layer.pr_marker, layer.sessions) == (17, False, 2)
        assert (layer.load_user_instructions, layer.load_user_skills) == (None, None)
    assert migrations.CONFIG[16] is migrations.user_config_added
    assert migrations.GLOBAL[16] is migrations.user_config_added
    assert migrations.GLOBAL[15] is migrations.credit_limits_written


def test_a_format_17_layer_keeps_its_switches_and_refuses_anything_but_a_boolean(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"format": 17, "load_user_instructions": True, "load_user_skills": False}))
    layer = read_layer(path, Layer)
    assert (layer.load_user_instructions, layer.load_user_skills) == (True, False)
    path.write_text(json.dumps({"format": 17, "load_user_skills": "yes"}))
    with pytest.raises(StoreError):
        read_layer(path, Layer)
