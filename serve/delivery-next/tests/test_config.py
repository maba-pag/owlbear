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
        agents={"reviewer": Agent(categories=["browser"], context="long", visible=True)}, runtimes={"window": False}
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
        {"agents": {"builder": {"context": 400_000}}},
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


@pytest.mark.parametrize("damaged", [b"", b'{"format": 1, "agents": {"builder": {"model": "x\xff"}}}'])
def test_an_existing_layer_that_is_empty_or_not_utf8_is_refused_not_read_as_defaults(tmp_path, damaged):
    path = tmp_path / "config.json"
    path.write_bytes(damaged)
    with pytest.raises(StoreError, match="unreadable"):
        read_layer(path, Layer)


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


def test_old_roles_fill_only_the_fields_an_existing_project_config_leaves_empty(repo):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"builder": {"model": "m-1", "effort": "low"}, "reviewer": {"model": "r-1", "effort": "max"}})
    own = Layer(agents={"builder": Agent(model="own")}, widths=[1600])
    (root / "config.json").write_text(own.model_dump_json())
    store = Store.open(repo)

    assert roles.chosen(store.settings(), StepKind.BUILD) == RoleModel(model="own", effort="low")
    assert roles.chosen(store.settings(), StepKind.REVIEW) == RoleModel(model="r-1", effort="max")
    assert store.read_config().widths == [1600]

    store.update_config(lambda _cur: Layer())  # the owner clears everything; the old profile is still on disk
    assert roles.chosen(Store.open(repo).settings(), StepKind.REVIEW) == roles.DEFAULTS["reviewer"]


def test_a_move_that_another_opener_finished_meanwhile_is_not_repeated(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real, raced = store_mod.open_lock, []

    def other_opener_first(fd, **kw):
        if kw.get("name") == f".{store_mod.ROLES_MOVED}.lock" and not raced:
            raced.append(True)  # another process moves the roles, then the owner clears them through its page
            Store(root).move_roles()
            Store(root).update_config(lambda _cur: Layer())
        return real(fd, **kw)

    monkeypatch.setattr(store_mod, "open_lock", other_opener_first)
    Store(root).move_roles()

    assert raced
    assert roles.chosen(Store(root).settings(), StepKind.REVIEW) == roles.DEFAULTS["reviewer"]


def test_a_move_whose_marker_cannot_be_written_fails_the_open(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = store_mod.atomic_write

    def no_marker(target, content):
        if target.name == store_mod.ROLES_MOVED:
            raise OSError(28, "No space left on device")
        real(target, content)

    monkeypatch.setattr(store_mod, "atomic_write", no_marker)
    with pytest.raises(OSError, match="No space"):
        Store(root).move_roles()


def test_a_merge_that_fails_after_replacing_the_config_fails_the_open(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = store_mod.atomic_write

    def replaced_then_failed(target, content):
        real(target, content)
        if target.name == store_mod.CONFIG:
            raise OSError(5, "Input/output error")  # e.g. the folder sync after the rename

    monkeypatch.setattr(store_mod, "atomic_write", replaced_then_failed)
    with pytest.raises(OSError, match="Input/output"):
        Store(root).move_roles()
    assert not (root / store_mod.ROLES_MOVED).exists()


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
