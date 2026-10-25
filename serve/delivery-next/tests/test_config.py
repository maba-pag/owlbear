import json
import subprocess
import threading

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.profile_record import RoleModel
from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.settings import carried, roles
from owlbear_delivery_next.settings.config import Agent, GlobalLayer, Layer, resolve
from owlbear_delivery_next.state_store import offline_protocol, profile_share
from owlbear_delivery_next.state_store import store as store_mod
from owlbear_delivery_next.state_store.store import Store, StoreError, read_layer, update_layer

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"


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
    assert eff.agents["reviewer"].model == carried.MODELS["reviewer"].model
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
        {"curator_threshold": 90},
        {"colour": "red"},
        {"agents": {"builder": {"context": True}}},
        {"runtimes": {"sdk": "false"}},
        {"format": 99},
        {"agents": {"builder": {"minutes": 0}}},
        {"agents": {"builder": {"minutes": 481}}},
        {"agents": {"builder": {"minutes": "40"}}},
        {"pr_labels": ["a", "a"]},
        {"pr_labels": [""]},
        {"pr_labels": [" release:minor"]},
        {"pr_labels": ["x" * 51]},
        {"pr_marker": "off"},
    ],
)
def test_a_layer_refuses_anything_it_cannot_apply(raw):
    with pytest.raises(ValidationError):
        Layer.model_validate(raw)


def test_pull_request_labels_replace_the_global_list_and_the_marker_is_layered():
    """TD-308: a project's list replaces the global one whole, [] included; the marker line is layered like the rest,
    since code ships no defaults (2026-10-23)."""
    glob = GlobalLayer(pr_labels=["owlbear"])
    assert (resolve(None, Layer()).pr_labels, resolve(None, Layer()).pr_marker) == ([], True)
    assert resolve(glob, Layer()).pr_labels == ["owlbear"]
    mine = resolve(glob, Layer(pr_labels=["release:minor"], pr_marker=False))
    assert (mine.pr_labels, mine.pr_marker, mine.sources["pr_labels"]) == (["release:minor"], False, "project")
    assert resolve(glob, Layer(pr_labels=[])).pr_labels == []
    assert resolve(GlobalLayer(pr_marker=False), Layer()).sources["pr_marker"] == "global"


def test_the_curators_threshold_is_95_percent_at_first_and_set_only_globally():
    """TD-400 and the owner's 2026-10-22 answer: one global value, on the Settings page."""
    assert (resolve(None, Layer()).curator_threshold, resolve(None, Layer()).sources["curator_threshold"]) == (
        95, "default"
    )  # fmt: skip
    eff = resolve(GlobalLayer(curator_threshold=90), Layer())
    assert (eff.curator_threshold, eff.sources["curator_threshold"]) == (90, "global")
    for wrong in (49, 101):
        with pytest.raises(ValidationError):
            GlobalLayer(curator_threshold=wrong)


def test_session_time_limits_are_doubled_by_default_and_set_per_role_globally_or_per_project():
    """TD-286: planner 30, preparer 30, builder 40, reviewer 20 minutes; each a role setting."""
    base = resolve(None, Layer())
    assert {r: base.agents[r].minutes for r in ("planner", "preparer", "builder", "reviewer")} == {
        "planner": 30, "preparer": 30, "builder": 40, "reviewer": 20
    }  # fmt: skip
    glob = GlobalLayer(agents={"builder": Agent(minutes=60), "reviewer": Agent(minutes=25)})
    eff = resolve(glob, Layer(agents={"builder": Agent(minutes=90)}))

    assert (eff.agents["builder"].minutes, eff.agents["reviewer"].minutes) == (90, 25)
    assert (eff.sources["agents.builder.minutes"], eff.sources["agents.reviewer.minutes"]) == ("project", "global")
    assert roles.limit(eff, StepKind.BUILD) == 5400.0
    assert roles.limit(eff, "design-review") == 20 * 60.0
    assert roles.limit(eff, "plan-challenge") == 20 * 60.0


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


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def _prepare_reboot_finish(repo, boot) -> None:
    """The manual move a clone's old store needs before any Store.open: prepare, reboot, finish."""
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert cli.main(["--repo", str(repo), "finish"]) == 0


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("fmt", [1, "1"])
def test_a_format_1_profile_moves_its_roles_into_the_project_config_once(repo, boot, fmt):
    root = repo / ".git" / "owlbear-delivery"
    old = {"builder": {"model": "m-1", "effort": "low"}, "reviewer": {"model": "r-1", "effort": "max"}}
    _old_profile(root, old, fmt)
    _prepare_reboot_finish(repo, boot)
    store = Store.open(repo)
    root = store.root  # moved into ~/.owlbear (TD-334)

    assert roles.chosen(store.settings(), StepKind.BUILD) == RoleModel(model="m-1", effort="low")
    assert roles.chosen(store.settings(), StepKind.REVIEW) == RoleModel(model="r-1", effort="max")
    assert roles.chosen(store.settings(), StepKind.PLAN) == carried.MODELS["planner"]
    prof = store.read_profile()
    assert (prof.format, prof.version, prof.runtime, prof.entries["rules"].evidence) == (2, 3, "vscode", "HTTP 403")
    assert "roles" not in prof.model_dump()
    saved = (root / "config.json").read_text()
    Store.open(repo).read_profile()
    assert (root / "config.json").read_text() == saved

    store.update_config(lambda _cur: Layer())  # the owner clears the overrides
    _old_profile(root, {"builder": {"model": "m-1", "effort": "low"}})  # e.g. a crash before the profile rewrite
    assert roles.chosen(Store.open(repo).settings(), StepKind.BUILD) == carried.MODELS["builder"]


@pytest.mark.usefixtures("current_binding")
def test_old_roles_fill_only_the_fields_an_existing_project_config_leaves_empty(repo, boot):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"builder": {"model": "m-1", "effort": "low"}, "reviewer": {"model": "r-1", "effort": "max"}})
    own = Layer(agents={"builder": Agent(model="own")}, widths=[1600])
    (root / "config.json").write_text(own.model_dump_json())
    _prepare_reboot_finish(repo, boot)
    store = Store.open(repo)

    assert roles.chosen(store.settings(), StepKind.BUILD) == RoleModel(model="own", effort="low")
    assert roles.chosen(store.settings(), StepKind.REVIEW) == RoleModel(model="r-1", effort="max")
    assert store.read_config().widths == [1600]

    store.update_config(lambda _cur: Layer())  # the owner clears everything; the old profile is still on disk
    assert roles.chosen(Store.open(repo).settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]


def test_a_move_that_another_opener_finished_meanwhile_is_not_repeated(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real, raced = profile_share.open_lock, []

    def other_opener_first(fd, **kw):
        if kw.get("name") == f".{profile_share.ROLES_MOVED}.lock" and not raced:
            raced.append(True)  # another process moves the roles, then the owner clears them through its page
            profile_share.move_roles(Store(root))
            Store(root).update_config(lambda _cur: Layer())
        return real(fd, **kw)

    monkeypatch.setattr(profile_share, "open_lock", other_opener_first)
    profile_share.move_roles(Store(root))

    assert raced
    assert roles.chosen(Store(root).settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]


def test_a_move_whose_marker_cannot_be_written_fails_the_open(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = profile_share.atomic_write

    def no_marker(target, content):
        if target.name == profile_share.ROLES_MOVED:
            raise OSError(28, "No space left on device")
        real(target, content)

    monkeypatch.setattr(profile_share, "atomic_write", no_marker)
    with pytest.raises(OSError, match="No space"):
        profile_share.move_roles(Store(root))


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
        profile_share.move_roles(Store(root))
    assert not (root / profile_share.ROLES_MOVED).exists()


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
@pytest.mark.usefixtures("current_binding")
def test_invalid_old_roles_are_refused_and_never_copied(repo, boot, bad):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, bad)
    _prepare_reboot_finish(repo, boot)
    store = Store.open(repo)

    assert not (root / "config.json").exists()
    with pytest.raises(StoreError, match="cannot be migrated"):
        store.read_profile()
