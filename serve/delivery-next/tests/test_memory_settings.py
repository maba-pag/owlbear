"""The memory values: Global-only settings the memory tools and Delivery read, each unset until the owner saves it."""

import json

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import (
    GlobalLayer,
    Layer,
    MachineLayer,
    MemoryValues,
    SettingsUnset,
    resolve,
)
from owlbear_delivery_next.state_store.store import read_layer

NAMES = tuple(MemoryValues.model_fields)
TODAYS = {
    "outstanding_boost": 0.1, "unremarkable_penalty": 0.01, "stale_factor": 50, "purge_days": 30,
    "preflight_cap": 5, "preflight_budget": 2000, "recall_limit": 20, "explore_slots": 2, "challenge_slots": 2,
}  # fmt: skip


def test_there_are_nine_memory_values_and_the_curator_s_threshold_stays_its_own_setting():
    assert set(NAMES) == set(TODAYS)
    assert "curator_threshold" in GlobalLayer.model_fields
    assert "curator_threshold" not in MemoryValues.model_fields


def test_each_memory_value_resolves_on_its_own_from_global():
    eff = resolve(GlobalLayer(memory=MemoryValues(stale_factor=7)), Layer())
    assert eff.memory.stale_factor == 7
    assert eff.sources["memory.stale_factor"] == "global"
    assert eff.memory.recall_limit == 20  # the tests' layer under Global holds today's values
    assert eff.sources["memory.recall_limit"] == "default"


@pytest.mark.parametrize("model", [Layer, MachineLayer])
def test_the_memory_values_are_global_only(model):
    with pytest.raises(ValidationError):
        model.model_validate({"memory": {"stale_factor": 7}})


@pytest.mark.parametrize(
    ("name", "value", "ok"),
    [
        ("outstanding_boost", 0, True), ("outstanding_boost", 0.25, True), ("outstanding_boost", -0.1, False),
        ("outstanding_boost", float("nan"), False), ("outstanding_boost", float("inf"), False),
        ("outstanding_boost", "0.1", False), ("outstanding_boost", True, False),
        ("unremarkable_penalty", 0, True), ("unremarkable_penalty", -0.01, False),
        ("stale_factor", 1, True), ("stale_factor", 0, False), ("stale_factor", 2.5, False),
        ("purge_days", 0, True), ("purge_days", 3650, True), ("purge_days", 3651, False), ("purge_days", -1, False),
        ("preflight_cap", 1, True), ("preflight_cap", 0, False),
        ("preflight_budget", 1, True), ("preflight_budget", 0, False),
        ("recall_limit", 1, True), ("recall_limit", 0, False),
        ("explore_slots", 0, True), ("explore_slots", -1, False),
        ("challenge_slots", 0, True), ("challenge_slots", -1, False),
    ],
)  # fmt: skip
def test_each_memory_value_keeps_to_its_bounds(name, value, ok):
    if ok:
        assert getattr(MemoryValues.model_validate({name: value}), name) == value
    else:
        with pytest.raises(ValidationError):
            MemoryValues.model_validate({name: value})


def test_a_memory_value_no_layer_sets_is_unset_and_listed_and_holds_what_reads_it(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    empty = resolve(None, Layer())
    assert [k for k in empty.missing if k.startswith("memory.")] == [f"memory.{n}" for n in NAMES]
    assert empty.memory == MemoryValues()
    with pytest.raises(SettingsUnset, match=r"memory\.outstanding_boost"):
        empty.need("memory.outstanding_boost")

    some = resolve(GlobalLayer(memory=MemoryValues(stale_factor=50, purge_days=0)), Layer())
    assert [k for k in some.missing if k.startswith("memory.")] == [
        f"memory.{n}" for n in NAMES if n not in {"stale_factor", "purge_days"}
    ]  # zero is a value, not an unset one
    assert some.page()["memory"]["purge_days"] == 0
    assert some.page()["memory"]["recall_limit"] is None


def test_a_published_format_20_global_gains_nine_unset_values_and_keeps_every_other_one(tmp_path, monkeypatch):
    """The upgrade as production meets it: no test layer under Global, no memory block in the stored file."""
    monkeypatch.setattr(config, "BASE", None)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"format": 20, "curator_threshold": 90, "sessions": 2}))

    glob = read_layer(path, GlobalLayer)
    eff = resolve(glob, Layer())

    assert (glob.format, glob.memory, glob.curator_threshold, glob.sessions) == (23, None, 90, 2)
    assert (eff.curator_threshold, eff.sessions) == (90, 2)
    assert [k for k in eff.missing if k.startswith("memory.")] == [f"memory.{n}" for n in NAMES]
    assert json.loads(path.read_text()) == {"format": 20, "curator_threshold": 90, "sessions": 2}  # read, not written


def test_a_global_with_every_memory_value_saved_resolves_them_all(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    eff = resolve(GlobalLayer(memory=MemoryValues.model_validate(TODAYS)), Layer())
    assert eff.memory.model_dump() == TODAYS
    assert not [k for k in eff.missing if k.startswith("memory.")]
    assert {eff.sources[f"memory.{n}"] for n in NAMES} == {"global"}
