import json
import subprocess
import threading

import pytest
from pydantic import ValidationError

from owlbear_delivery_next import roles
from owlbear_delivery_next import store as store_mod
from owlbear_delivery_next.config import Agent, GlobalLayer, Layer, resolve
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.profile_record import RoleModel
from owlbear_delivery_next.store import Store, StoreError, read_layer, update_layer


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S607
    return root


def test_each_field_comes_from_the_project_else_the_global_layer_else_the_default():
    glob = GlobalLayer(visible=True, agents={"builder": Agent(model="g-1", effort="high")}, widths=[1280, 1920])
    proj = Layer(agents={"builder": Agent(effort="low")}, runtimes={"window": False})
    eff = resolve(glob, proj)

    b = eff.agents["builder"]
    assert (b.model, b.effort, b.runtime, b.visible, b.categories, b.context) == (
        "g-1", "low", "sdk", False, [], "default"
    )  # fmt: skip
    assert (eff.visible, eff.widths, eff.runtimes) == (True, [1280, 1920], {"sdk": True, "window": False})
    assert eff.agents["reviewer"].model == roles.DEFAULTS["reviewer"].model
    assert eff.sources["agents.builder.model"] == "global"
    assert eff.sources["agents.builder.effort"] == "project"
    assert eff.sources["agents.reviewer.model"] == "default"
    assert eff.sources["runtimes.window"] == "project"
    assert resolve(None, Layer()).widths == [1280, 1920, 2400]


def test_an_empty_list_clears_false_disables_and_only_none_inherits():
    glob = GlobalLayer(
        agents={"reviewer": Agent(categories=["browser"], context=400_000, visible=True)}, runtimes={"window": False}
    )
    proj = Layer(agents={"reviewer": Agent(categories=[], context="default", visible=False)})
    r = resolve(glob, proj).agents["reviewer"]

    assert (r.categories, r.context, r.visible) == ([], "default", False)
    assert resolve(glob, Layer()).agents["reviewer"].categories == ["browser"]
    assert resolve(glob, Layer()).runtimes["window"] is False


@pytest.mark.parametrize(
    "raw",
    [
        {"agents": {"builder": {"model": "auto"}}},
        {"agents": {"builder": {"model": " "}}},
        {"agents": {"boss": {"effort": "low"}}},
        {"agents": {"builder": {"effort": "extreme"}}},
        {"agents": {"builder": {"context": 0}}},
        {"agents": {"builder": {"categories": ["teleport"]}}},
        {"agents": {"builder": {"runtime": "cloud"}}},
        {"runtimes": {"cloud": True}},
        {"widths": []},
        {"widths": [1000]},
        {"widths": [2401]},
        {"visible": True},
        {"colour": "red"},
        {"agents": {"builder": {"context": True}}},
        {"runtimes": {"sdk": "false"}},
        {"format": 99},
    ],
)
def test_a_layer_refuses_anything_it_cannot_apply(raw):
    with pytest.raises(ValidationError):
        Layer.model_validate(raw)


def test_a_project_layer_round_trips_and_concurrent_saves_are_never_lost(repo, monkeypatch):
    store = Store.open(repo)
    assert store.read_config() == Layer()
    entered, other_read = threading.Event(), threading.Event()
    original = store_mod.read_layer

    def spy(path, model):
        layer = original(path, model)
        if threading.current_thread() is second:
            other_read.set()  # the second writer now holds its snapshot
        return layer

    def slow(cur: Layer) -> Layer:
        entered.set()
        other_read.wait(1)  # without the lock the other writer reads the stale layer here
        return cur.model_copy(update={"widths": [1280]})

    monkeypatch.setattr(store_mod, "read_layer", spy)
    first = threading.Thread(target=store.update_config, args=(slow,))
    second = threading.Thread(
        target=store.update_config,
        args=(lambda cur: cur.model_copy(update={"agents": {"builder": Agent(effort="low")}}),),
    )
    first.start()
    assert entered.wait(5)
    second.start()
    first.join(5)
    second.join(5)

    got = store.read_config()
    assert (got.widths, got.agents["builder"].effort) == ([1280], "low")
    assert roles.chosen(store.settings(), StepKind.BUILD).effort == "low"


def test_an_invalid_save_writes_nothing(repo):
    store = Store.open(repo)
    store.update_config(lambda cur: cur.model_copy(update={"widths": [1280]}))
    saved = (store.root / "config.json").read_bytes()
    for bad in ({"widths": [999]}, {"format": 99}):
        with pytest.raises(ValidationError):
            store.update_config(lambda cur, bad=bad: cur.model_copy(update=bad))
    assert (store.root / "config.json").read_bytes() == saved


def test_the_global_layer_is_read_and_saved_where_the_caller_says(tmp_path):
    path = tmp_path / "global" / "config.json"
    assert read_layer(path, GlobalLayer) == GlobalLayer()
    update_layer(path, GlobalLayer, lambda cur: cur.model_copy(update={"visible": True}))
    assert read_layer(path, GlobalLayer).visible is True
    path.write_text(json.dumps({"format": 99}))
    with pytest.raises(StoreError, match="newer"):
        read_layer(path, GlobalLayer)


def _old_profile(root, roles_: object, fmt: object = 1) -> None:
    root.mkdir(parents=True, exist_ok=True)
    raw = {
        "format": fmt,
        "version": 3,
        "confirmed_at": "2026-10-01T10:00:00Z",
        "entries": {"rules": {"state": "unknown", "value": "", "evidence": "HTTP 403"}},
        "roles": roles_,
        "runtime": "vscode",
    }
    (root / "profile.json").write_text(json.dumps(raw))


@pytest.mark.parametrize("fmt", [1, "1"])
def test_a_format_1_profile_moves_its_roles_into_the_project_config_once(repo, fmt):
    root = repo / ".git" / "owlbear-delivery"
    old = {"builder": {"model": "m-1", "effort": "low"}, "reviewer": {"model": "r-1", "effort": "max"}}
    _old_profile(root, old, fmt)
    store = Store.open(repo)

    assert roles.chosen(store.settings(), StepKind.BUILD) == RoleModel(model="m-1", effort="low")
    assert roles.chosen(store.settings(), StepKind.REVIEW) == RoleModel(model="r-1", effort="max")
    assert roles.chosen(store.settings(), StepKind.PLAN) == roles.DEFAULTS["planner"]
    prof = store.read_profile()
    assert (prof.format, prof.version, prof.runtime, prof.entries["rules"].evidence) == (2, 3, "vscode", "HTTP 403")
    assert "roles" not in prof.model_dump()
    saved = (root / "config.json").read_text()
    Store.open(repo).read_profile()
    assert (root / "config.json").read_text() == saved

    store.update_config(lambda _cur: Layer())  # the owner clears the overrides
    _old_profile(root, {"builder": {"model": "m-1", "effort": "low"}})  # e.g. a crash before the profile rewrite
    assert roles.chosen(Store.open(repo).settings(), StepKind.BUILD) == roles.DEFAULTS["builder"]


@pytest.mark.parametrize(
    "bad",
    [
        {"builder": {"model": "auto", "effort": "low"}},
        {"boss": {"model": "m", "effort": "low"}},
        {"builder": {"model": "m", "effort": "low", "extra": 1}},
        None,
        [],
        False,
        0,
        "",
    ],
)
def test_invalid_old_roles_are_refused_and_never_copied(repo, bad):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, bad)
    store = Store.open(repo)

    assert not (root / "config.json").exists()
    with pytest.raises(StoreError, match="cannot be migrated"):
        store.read_profile()
