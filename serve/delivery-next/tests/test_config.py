import json
import subprocess
import threading

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile, RoleModel
from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import carried, roles
from owlbear_delivery_next.settings.config import CONFIG_FORMAT, Agent, GlobalLayer, Layer, resolve
from owlbear_delivery_next.state_store import layers as layers_mod
from owlbear_delivery_next.state_store import offline_protocol, profile_share, project_home, roles_move
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
    glob = GlobalLayer(agents={"builder": Agent(model="g-1", effort="high")}, widths=[1280, 1920])
    proj = Layer(agents={"builder": Agent(effort="low")})
    eff = resolve(glob, proj)

    b = eff.agents["builder"]
    assert (b.model, b.effort, b.context) == ("g-1", "low", "default")
    assert eff.widths == [1280, 1920]
    assert eff.agents["reviewer"].model == carried.MODELS["reviewer"].model
    assert eff.sources["agents.builder.model"] == "global"
    assert eff.sources["agents.builder.effort"] == "project"
    assert eff.sources["agents.reviewer.model"] == "default"
    assert resolve(None, Layer()).widths == [1280, 1920, 2400]


def test_an_empty_list_clears_false_disables_and_only_none_inherits():
    glob = GlobalLayer(agents={"reviewer": Agent(context="long")}, pr_labels=["owlbear"], pr_marker=True)
    proj = Layer(agents={"reviewer": Agent(context="default")}, pr_labels=[], pr_marker=False)
    eff = resolve(glob, proj)

    assert (eff.agents["reviewer"].context, eff.pr_labels, eff.pr_marker) == ("default", [], False)
    inherited = resolve(glob, Layer())
    assert (inherited.agents["reviewer"].context, inherited.pr_labels) == ("long", ["owlbear"])
    assert inherited.pr_marker is True


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
    first = threading.Thread(target=owner_save, args=(store, slow))
    second = threading.Thread(
        target=owner_save,
        args=(store, lambda cur: cur.model_copy(update={"agents": {"builder": Agent(effort="low")}})),
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
    owner_save(store, lambda cur: cur.model_copy(update={"widths": [1280]}))
    saved = (store.root / "config.json").read_bytes()
    for bad in ({"widths": [999]}, {"format": 99}):
        with pytest.raises(ValidationError):
            owner_save(store, lambda cur, bad=bad: cur.model_copy(update=bad))
    assert (store.root / "config.json").read_bytes() == saved


def test_the_global_layer_is_read_and_saved_where_the_caller_says(tmp_path):
    path = tmp_path / "global" / "config.json"
    assert read_layer(path, GlobalLayer) == GlobalLayer()
    update_layer(path, GlobalLayer, lambda cur: cur.model_copy(update={"pr_marker": False}))
    assert read_layer(path, GlobalLayer).pr_marker is False
    path.write_text(json.dumps({"format": 99}))
    with pytest.raises(StoreError, match="newer"):
        read_layer(path, GlobalLayer)


def test_a_stored_layer_from_before_the_window_runtime_loads_without_its_settings(tmp_path):
    path = tmp_path / "global" / "config.json"
    path.parent.mkdir(parents=True)
    old = {
        "format": 12,
        "widths": [1600],
        "runtimes": {"sdk": True, "window": False},
        "visible": True,
        "agents": {"builder": {"model": "g-1", "runtime": "window", "visible": False, "categories": ["browser"]}},
    }
    path.write_text(json.dumps(old))

    layer = read_layer(path, GlobalLayer)
    assert (layer.format, layer.widths, layer.agents["builder"]) == (CONFIG_FORMAT, [1600], Agent(model="g-1"))
    assert not {"runtimes", "visible"} & set(layer.model_dump())


@pytest.mark.parametrize(
    "retired",
    [
        {"runtimes": {"cloud": True}},
        {"visible": "yes"},
        {"agents": {"builder": {"runtime": "vscode"}}},
        {"agents": {"builder": {"categories": ["teleport"]}}},
    ],
)
def test_a_retired_window_setting_the_format_never_allowed_is_refused_not_dropped(tmp_path, retired):
    path = tmp_path / "global" / "config.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"format": 14, "widths": [1600]} | retired))

    with pytest.raises(StoreError, match=f"cannot be migrated to format {CONFIG_FORMAT}"):
        read_layer(path, GlobalLayer)


@pytest.mark.parametrize("damaged", [b"", b'{"format": 1, "agents": {"builder": {"model": "x\xff"}}}'])
def test_an_existing_layer_that_is_empty_or_not_utf8_is_refused_not_read_as_defaults(tmp_path, damaged):
    path = tmp_path / "config.json"
    path.write_bytes(damaged)
    with pytest.raises(StoreError, match="unreadable"):
        read_layer(path, Layer)


def owner_save(store: Store, change) -> str:
    """The owner's current-revision save, as the settings page makes it; automatic writes never bypass the guard."""
    return store.save(store.config_path, Layer, change, "owner", owner=True)


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


def _prepare_reboot_finish(repo, boot, *, finish_code: int = 0) -> None:
    """The manual move a clone's old store needs before any Store.open: prepare, reboot, finish."""
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert cli.main(["--repo", str(repo), "finish"]) == finish_code


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("fmt", [1])
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
    assert (prof.format, prof.version, prof.entries["rules"].evidence) == (PROFILE_FORMAT, 3, "HTTP 403")
    assert "roles" not in prof.model_dump()
    assert "runtime" not in prof.model_dump()  # the per-project runtime switch goes (format 5)
    saved = (root / "config.json").read_text()
    Store.open(repo).read_profile()
    assert (root / "config.json").read_text() == saved

    owner_save(store, lambda _cur: Layer())  # the owner clears the overrides
    _old_profile(root, {"builder": {"model": "m-1", "effort": "low"}})  # e.g. a crash before the profile rewrite
    assert roles.chosen(Store.open(repo).settings(), StepKind.BUILD) == carried.MODELS["builder"]


def test_a_format_1_profile_whose_format_is_a_string_is_refused_and_kept(repo):
    root = Store.open(repo).root
    _old_profile(root, {"builder": {"model": "m-1", "effort": "low"}}, "1")
    before = (root / "profile.json").read_bytes()
    with pytest.raises(StoreError, match=r"state of profile\.json is unreadable"):
        Store.open(repo)
    assert (root / "profile.json").read_bytes() == before


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

    owner_save(store, lambda _cur: Layer())  # the owner clears everything; the old profile is still on disk
    assert roles.chosen(Store.open(repo).settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]


def test_a_move_that_another_opener_finished_meanwhile_is_not_repeated(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real, raced = roles_move.open_lock, []

    def other_opener_first(fd, **kw):
        if kw.get("name") == f".{profile_share.ROLES_MOVED}.lock" and not raced:
            raced.append(True)  # another process moves the roles, then the owner clears them through its page
            roles_move.move_roles(Store(root))
            owner_save(Store(root), lambda _cur: Layer())
        return real(fd, **kw)

    monkeypatch.setattr(roles_move, "open_lock", other_opener_first)
    roles_move.move_roles(Store(root))

    assert raced
    assert roles.chosen(Store(root).settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]


def test_a_clone_that_read_roles_before_another_cleared_them_never_reinstates(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    _old_profile(a.root, {"reviewer": {"model": "r-1", "effort": "max"}})
    second = tmp_path / "b"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    b = Store(tmp_path / "b-store", DataRepo(second), "shop-site")
    _old_profile(b.root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real_digest, raced = roles_move.config_digest, []

    def clone_a_first(path):
        if not raced:  # clone B has read roles_moved as False; clone A imports, then the owner clears
            raced.append(True)
            roles_move.move_roles(a)
            owner_save(a, lambda _cur: Layer())
            assert read_layer(a.config_path, Layer).roles_moved  # the cleared basis B captures carries the receipt
        return real_digest(path)

    monkeypatch.setattr(roles_move, "config_digest", clone_a_first)
    roles_move.move_roles(b)

    assert raced
    assert (b.root / profile_share.ROLES_MOVED).exists()
    fresh = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(fresh)], check=True, capture_output=True)  # noqa: S603, S607
    shared = Store(tmp_path / "fresh-store", DataRepo(fresh), "shop-site")
    assert read_layer(shared.config_path, Layer).roles_moved
    assert roles.chosen(shared.settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]


def test_a_clone_on_the_same_config_that_another_cleared_never_reinstates(shared_repo, tmp_path, monkeypatch):
    root, _remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    b = Store(tmp_path / "b-store", DataRepo(root), "shop-site")
    assert a.root != b.root
    assert a.config_path == b.config_path
    _old_profile(a.root, {"reviewer": {"model": "r-1", "effort": "max"}})
    _old_profile(b.root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real_digest, real_update = roles_move.config_digest, Store.update_config
    raced, cleared, seen = [], [], []

    def a_imports_then_owner_clears(path):
        if not raced:  # B has read roles_moved as False; A imports, then the owner clears the roles
            raced.append(True)
            roles_move.move_roles(a)
            owner_save(a, lambda _cur: Layer())
            cleared.append(real_digest(a.config_path))
        return real_digest(path)

    def watch_b_callback(self, prepared, what="project layer", on_written=None):
        if self.root == b.root:  # the locked callback B's basis reaches: what it reads, not only what B stored
            inner = prepared.change

            def seen_by_callback(cur):
                seen.append((prepared.basis, cur.roles_moved))
                return inner(cur)

            prepared.change = seen_by_callback
        return real_update(self, prepared, what, on_written=on_written)

    monkeypatch.setattr(roles_move, "config_digest", a_imports_then_owner_clears)
    monkeypatch.setattr(Store, "update_config", watch_b_callback)
    roles_move.move_roles(b)

    assert raced
    assert seen == [(cleared[0], True)]  # B's basis is the cleared config, and its locked callback sees the receipt
    assert (b.root / profile_share.ROLES_MOVED).exists()
    fresh = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(_remote), str(fresh)], check=True, capture_output=True)  # noqa: S603, S607
    shared = Store(tmp_path / "fresh-store", DataRepo(fresh), "shop-site")
    assert read_layer(shared.config_path, Layer).roles_moved
    assert roles.chosen(shared.settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]


def test_a_move_whose_marker_cannot_be_written_fails_the_open(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = roles_move.atomic_write

    def no_marker(target, content):
        if target.name == profile_share.ROLES_MOVED:
            raise OSError(28, "No space left on device")
        real(target, content)

    monkeypatch.setattr(roles_move, "atomic_write", no_marker)
    with pytest.raises(OSError, match="No space"):
        roles_move.move_roles(Store(root))


def test_a_merge_that_fails_after_replacing_the_config_fails_the_open(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = layers_mod.atomic_write

    def replaced_then_failed(target, content):
        real(target, content)
        if target.name == store_mod.CONFIG:
            raise OSError(5, "Input/output error")  # e.g. the folder sync after the rename

    monkeypatch.setattr(layers_mod, "atomic_write", replaced_then_failed)
    with pytest.raises(OSError, match="Input/output"):
        roles_move.move_roles(Store(root))
    assert not (root / profile_share.ROLES_MOVED).exists()


@pytest.mark.parametrize(("mode", "reason"), [("held", "not moved"), ("raised", "fetch failed")])
def test_a_refused_or_failed_role_move_write_is_visible_and_not_marked(repo, monkeypatch, mode, reason):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = Store.update_config

    def refused(*_args, **_kwargs):
        if mode == "raised":
            msg = "simulated: fetch failed"
            raise StoreError(msg)
        return "simulated: fetch refused"

    monkeypatch.setattr(Store, "update_config", refused)
    with pytest.raises(StoreError, match=reason):
        roles_move.move_roles(Store(root))
    assert not (root / profile_share.ROLES_MOVED).exists()
    assert not Store(root).config_path.exists()
    assert (root / profile_share.PROFILE).exists()  # the source is kept for the retry

    monkeypatch.setattr(Store, "update_config", real)
    roles_move.move_roles(Store(root))
    assert (root / profile_share.ROLES_MOVED).exists()
    assert Store(root).read_config().agents["reviewer"].model == "r-1"


def test_a_role_move_applied_but_unpublished_is_marked_and_opens(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = Store.update_config

    def applied_then_refused(self, change, what="project layer", on_written=None):
        real(self, change, what, on_written)
        return "simulated: publication refused; retry in settings"

    monkeypatch.setattr(Store, "update_config", applied_then_refused)
    roles_move.move_roles(Store(root))  # applied locally: the marker caches the receipt, so the open succeeds
    assert (root / profile_share.ROLES_MOVED).exists()
    assert Store(root).read_config().agents["reviewer"].model == "r-1"


def test_a_role_move_applied_before_its_marker_fails_is_visible_and_heals_on_retry(repo, monkeypatch):
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = roles_move.atomic_write

    def marker_refused(target, content):
        if target.name == profile_share.ROLES_MOVED:
            msg = "simulated: marker write refused"
            raise StoreError(msg)
        real(target, content)

    monkeypatch.setattr(roles_move, "atomic_write", marker_refused)
    with pytest.raises(StoreError, match="marker write refused"):
        roles_move.move_roles(Store(root))
    assert not (root / profile_share.ROLES_MOVED).exists()
    assert (root / profile_share.PROFILE).exists()
    assert Store(root).read_config().agents["reviewer"].model == "r-1"  # applied with its config write

    monkeypatch.setattr(roles_move, "atomic_write", real)
    roles_move.move_roles(Store(root))
    assert (root / profile_share.ROLES_MOVED).exists()
    assert Store(root).read_config().agents["reviewer"].model == "r-1"


def test_an_owner_clear_right_after_the_roles_move_survives_a_fresh_reopen(repo, monkeypatch):
    root = Store.open(repo).root
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real = Store.update_config

    def moved_then_cleared(self, change, what="project layer", on_written=None):
        result = real(self, change, what, on_written)
        owner_save(self, lambda _cur: Layer())  # the owner clears the overrides before anything reads the move back
        return result

    monkeypatch.setattr(Store, "update_config", moved_then_cleared)
    store = Store.open(repo)  # the move is applied and marked under one lock; the owner then clears
    monkeypatch.setattr(Store, "update_config", real)
    root = store.root
    assert (root / profile_share.ROLES_MOVED).exists()
    cleared = (root / "config.json").read_bytes()

    fresh = Store.open(repo)

    assert roles.chosen(fresh.settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]
    assert (root / "config.json").read_bytes() == cleared
    assert (root / profile_share.ROLES_MOVED).exists()


class _Abrupt(BaseException):
    """A stop the process cannot catch, such as a kill between the two writes."""


@pytest.mark.parametrize("exc", [OSError, _Abrupt], ids=["marker-fails", "abrupt-stop"])
def test_an_owner_clear_after_an_applied_role_move_survives_a_lost_marker(repo, monkeypatch, exc):
    root = Store.open(repo).root
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    real, failed = roles_move.atomic_write, []

    def marker_fails_once(target, content):
        if target.name == profile_share.ROLES_MOVED and not failed:
            failed.append(True)
            raise exc(28, "No space left on device")  # the roles are applied in config.json; the marker is not
        real(target, content)

    monkeypatch.setattr(roles_move, "atomic_write", marker_fails_once)
    with pytest.raises(exc):
        Store.open(repo)  # the roles are applied to config.json; the marker write is the one that fails
    store = Store(project_home.located(repo))
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert store.read_config().agents["reviewer"].model == "r-1"

    owner_save(store, lambda _cur: Layer())  # the owner clears the role before anything retries the move
    cleared = store.config_path.read_bytes()

    first = Store.open(repo)  # a fresh open rebuilds the marker from the receipt and must not refill the role
    assert roles.chosen(first.settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]
    assert first.config_path.read_bytes() == cleared
    assert (first.root / profile_share.ROLES_MOVED).exists()

    fresh = Store.open(repo)  # restart: the same outcome, byte for byte
    assert roles.chosen(fresh.settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]
    assert fresh.config_path.read_bytes() == cleared
    assert (fresh.root / profile_share.ROLES_MOVED).exists()


@pytest.mark.parametrize("bad", [{"builder": {"model": "auto", "effort": "low"}}, None])  # a bad role, not a mapping
@pytest.mark.usefixtures("current_binding")
def test_invalid_old_roles_are_refused_and_never_copied(repo, boot, bad, capsys):
    """The manual move refuses through the same check as ``Store.open``, where the other invalid shapes are proved."""
    root = repo / ".git" / "owlbear-delivery"
    _old_profile(root, bad)
    original = (root / "profile.json").read_bytes()
    _prepare_reboot_finish(repo, boot, finish_code=1)
    error = capsys.readouterr().err
    assert any(reason in error for reason in ("role overrides", "cannot be migrated"))
    with pytest.raises(StoreError, match=r"role overrides|cannot be migrated"):
        Store.open(repo)

    target = project_home.located(repo)
    assert target != root
    assert (root / "format").read_text().strip() == "999"
    assert (root / "profile.json").read_bytes() == original
    assert (target / "profile.json").read_bytes() == original
    assert not (target / "config.json").exists()
    assert not (target / profile_share.ROLES_MOVED).exists()


def test_a_damaged_old_profile_is_not_marked_moved_and_its_roles_come_back_once_repaired(repo):
    store = Store.open(repo)  # no old profile yet: nothing to move
    own = Layer(agents={"builder": Agent(model="own")})
    owner_save(store, lambda _cur: own)  # the owner's own settings meanwhile
    root = store.root
    (root / "profile.json").write_bytes(b'{"format": 1, "roles": {"reviewer": ')  # truncated mid-write

    with pytest.raises(StoreError, match="could not be read"):
        Store.open(repo)
    assert not (root / profile_share.ROLES_MOVED).exists()

    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}, "builder": {"model": "old", "effort": "low"}})
    healthy = Store.open(repo)

    assert healthy.read_config().agents["reviewer"].model == "r-1"
    assert healthy.read_config().agents["builder"].model == "own"  # the owner's model is kept
    assert (root / profile_share.ROLES_MOVED).exists()


@pytest.mark.parametrize(
    "bad",
    [
        {"reviewer": {"model": "r-1"}},  # no effort
        {"boss": {"model": "m", "effort": "low"}},
        {"builder": {"model": "m", "effort": "low", "extra": 1}},
        [],
        False,
        0,
        "",
    ],
)
def test_an_old_profile_with_an_invalid_role_is_not_marked_moved_and_restores_once_repaired(repo, bad):
    root = Store.open(repo).root
    _old_profile(root, bad)
    original = (root / "profile.json").read_bytes()
    with pytest.raises(StoreError, match="role overrides are invalid"):
        Store.open(repo)
    root = project_home.located(repo)
    assert (root / "profile.json").read_bytes() == original
    assert not (root / profile_share.ROLES_MOVED).exists()
    assert not (root / "config.json").exists()

    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    healthy = Store.open(repo)
    assert healthy.read_config().agents["reviewer"].model == "r-1"
    assert (root / profile_share.ROLES_MOVED).exists()


def test_an_old_profile_that_cannot_be_read_is_not_marked_moved_and_restores_once_repaired(repo):
    root = Store.open(repo).root
    (root / "profile.json").mkdir()  # a directory: the read fails
    with pytest.raises(StoreError, match="could not be read"):
        Store.open(repo)
    root = project_home.located(repo)
    assert not (root / profile_share.ROLES_MOVED).exists()
    assert not (root / "config.json").exists()

    (root / "profile.json").rmdir()
    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    healthy = Store.open(repo)
    assert healthy.read_config().agents["reviewer"].model == "r-1"
    assert (root / profile_share.ROLES_MOVED).exists()


def test_an_invalid_local_role_source_in_a_shared_project_is_refused_visibly_and_stays_retryable(shared_repo):
    repo, _remote = shared_repo
    legacy = Store.open(repo).root
    _old_profile(legacy, {"reviewer": {"model": "r-1", "effort": "bogus"}})
    with pytest.raises(StoreError) as caught:
        Store.open(repo)
    assert "role overrides are invalid" in str(caught.value)
    assert "then reopen" in str(caught.value)

    root = project_home.located(repo)
    assert not (root / profile_share.ROLES_MOVED).exists()
    assert not (root / "config.json").exists()

    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    assert Store.open(repo).read_config().agents["reviewer"].model == "r-1"
    assert (root / profile_share.ROLES_MOVED).exists()


def test_a_valid_empty_old_roles_profile_counts_as_already_satisfied(repo):
    root = Store.open(repo).root
    _old_profile(root, {})
    store = Store.open(repo)

    assert (store.root / profile_share.ROLES_MOVED).exists()
    assert not (store.root / "config.json").exists()


@pytest.mark.parametrize(
    "raw",
    [
        b'{"format": 999, "roles": {"reviewer": {"model": "r-1", "effort": "max"}}}',  # a newer OwlBear wrote it
        b'[{"format": 1, "roles": {}}]',  # not a profile object
        b'{"roles": {"reviewer": {"model": "r-1", "effort": "max"}}}',  # no format at all
        b'{"format": 1, "roles": {}, "runtime": "unknown"}',
        b'{"format": 1.5, "roles": {"reviewer": {"model": "r-1", "effort": "max"}}}',
        b'{"format": true, "roles": {"reviewer": {"model": "r-1", "effort": "max"}}}',
    ],
)
def test_an_unknown_old_profile_refuses_before_any_marker_or_config_and_a_valid_one_then_imports(repo, raw):
    legacy = Store.open(repo).root
    (legacy / "profile.json").write_bytes(raw)
    with pytest.raises(StoreError):
        Store.open(repo)

    root = project_home.located(repo)
    assert not (root / profile_share.ROLES_MOVED).exists()
    assert not (root / "config.json").exists()

    _old_profile(root, {"reviewer": {"model": "r-1", "effort": "max"}})
    assert Store.open(repo).read_config().agents["reviewer"].model == "r-1"
    assert (root / profile_share.ROLES_MOVED).exists()


def test_a_validated_current_format_profile_has_no_roles_to_move_and_is_marked_once(repo):
    legacy = Store.open(repo).root
    (legacy / "profile.json").write_text(Profile().model_dump_json())
    store = Store.open(repo)

    assert (store.root / profile_share.ROLES_MOVED).exists()
    assert not (store.root / "config.json").exists()
