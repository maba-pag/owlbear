import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.settings import carried, roles
from owlbear_delivery_next.settings.config import CONFIG_FORMAT as F
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import profile_share, project_home, roles_move
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}


class Host:
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store")


def client(store: Store, global_path: Path | None = None, **kw: object) -> TestClient:
    store.global_path = global_path
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", **kw)


def test_the_settings_need_the_token_and_a_local_host(store):
    assert client(store).get("/api/next/config").status_code == 401
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://example.com", headers=AUTH)
    assert c.get("/api/next/config").status_code == 403
    page = client(store).get("/config")
    assert page.status_code == 200
    assert "Settings" in page.text


def test_get_shows_each_layer_the_resolved_values_their_source_and_what_is_applied(store):
    got = client(store, headers=AUTH).get("/api/next/config").json()

    assert got["project"] == {
        "format": F, "prefs": None, "prefs_imported": False, "roles_moved": False, "agents": {}, "widths": None,
        "preparations": None, "data": None, "design_failures": None, "final_review": None, "pr_labels": None,
        "pr_marker": None, "sessions": None, "spotter": None,
    }  # fmt: skip
    assert (got["global"], got["global_location"]) == (None, False)
    assert got["settings"]["agents"]["builder"]["model"] == "claude-opus-5.5"
    assert got["settings"]["sources"]["agents.builder.model"] == "default"
    assert (got["settings"]["preparations"], got["settings"]["sources"]["preparations"]) == ([], "default")
    assert got["settings"]["data"] == {
        "data_classes": [], "unmasked": [], "keys": False, "isolation": [], "retention": "delete"
    }  # fmt: skip
    assert got["applied"] == [
        "agents.*.context", "agents.*.effort", "agents.*.model", "widths", "preparations", "data", "design_failures",
        "agents.builder.max_rounds", "agents.builder.max_findings", "agents.builder.last_round_at",
        "agents.builder.ask_owner_at", "agents.planner.max_rounds", "agents.planner.max_findings",
        "agents.planner.last_round_at", "agents.planner.ask_owner_at", "agents.shaper.max_rounds",
        "agents.shaper.max_findings", "agents.shaper.last_round_at", "agents.shaper.ask_owner_at", "final_review",
        "agents.planner.minutes", "agents.builder.minutes", "agents.reviewer.minutes", "agents.challenger.minutes",
        "agents.design-judge.minutes", "agents.preparer.minutes", "agents.updater.minutes", "agents.picker.minutes",
        "pr_labels", "pr_marker", "prefs.merge_method", "prefs.delete_remote_branch", "prefs.ci_poll_seconds",
        "prefs.ci_start_window_seconds", "prefs.ask_before_merge",
        "agents.planner.subagents", "agents.builder.subagents", "agents.reviewer.subagents",
        "agents.challenger.subagents", "agents.design-judge.subagents", "agents.preparer.subagents",
        "agents.updater.subagents", "sessions",
    ]  # fmt: skip
    assert len(got["project_rev"]) == 64


def test_a_project_save_needs_the_revision_it_was_based_on(store):
    c = client(store, headers=AUTH)
    first = c.get("/api/next/config").json()
    layer = first["project"] | {"agents": {"builder": {"effort": "low"}}}

    saved = c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": layer})
    assert saved.status_code == 200
    assert saved.json()["settings"]["agents"]["builder"]["effort"] == "low"
    assert saved.json()["settings"]["sources"]["agents.builder.effort"] == "project"
    assert store.read_config().agents["builder"].effort == "low"

    stale = c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": first["project"]})
    assert stale.status_code == 409
    assert store.read_config().agents["builder"].effort == "low"
    assert saved.json()["inherited"]["project"]["agents"]["builder"]["effort"] == "medium"


def test_the_challenge_round_values_are_saved_per_loop(store):
    c = client(store, headers=AUTH)
    first = c.get("/api/next/config").json()
    rounds = {"max_rounds": 4, "last_round_at": 2}
    layer = first["project"] | {"agents": {"builder": rounds}, "final_review": {"ask_owner_at": 5}}
    saved = c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": layer}).json()
    final, sources = saved["settings"]["final_review"], saved["settings"]["sources"]
    assert (final, sources["final_review.max_rounds"], sources["final_review.ask_owner_at"]) == (
        {"max_rounds": 4, "max_findings": 10, "last_round_at": 2, "ask_owner_at": 5},
        "builder",
        "project",
    )
    wrong = layer | {"final_review": {"last_round_at": 5, "ask_owner_at": 5}}
    assert c.put("/api/next/config/project", json={"rev": saved["project_rev"], "layer": wrong}).status_code == 422
    typed = layer | {"agents": {"builder": {"max_rounds": "three"}}}  # the page sends a non-number as typed
    assert c.put("/api/next/config/project", json={"rev": saved["project_rev"], "layer": typed}).status_code == 422


@pytest.mark.parametrize(
    "layer",
    [
        {"agents": {"builder": {"model": "auto"}}},
        {"widths": [999]},
        {"agents": {"builder": {"context": True}}},
        {"visible": True},
        {"seed": "npm run seed"},  # format 2 replaced it by declared preparation options (TD-96)
        {"preparations": [{"id": "copy", "kind": "live-copy", "cleanup": "drop", "data_classes": ["orders"]}]},
    ],
)
def test_an_invalid_project_layer_is_refused_and_nothing_changes(store, layer):
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["project_rev"]
    r = c.put("/api/next/config/project", json={"rev": rev, "layer": {"format": F, **layer}})

    assert r.status_code == 422
    assert not (store.root / "config.json").exists()


def test_the_spotter_learns_by_global_and_a_project_may_turn_it_off() -> None:
    from owlbear_delivery_next.settings import config  # noqa: PLC0415
    from owlbear_delivery_next.settings.improvement import Spotter  # noqa: PLC0415

    on = config.resolve(None, config.Layer())
    off = config.resolve(config.GlobalLayer(), config.Layer(spotter=Spotter(switch="off")))
    spotter = on.agents["spotter"]
    assert (on.spotter.switch, on.sources["spotter.switch"], spotter.model, spotter.effort) == (
        "on", "default", "gpt-6-luna", "medium")  # fmt: skip
    assert on.spotter.hand_off_fitness == "record"
    assert (on.agents["spotter"].context, off.spotter.switch, off.sources["spotter.switch"]) == (
        "default",
        "off",
        "project",
    )
    assert off.spotter.looks == ["hand-off"]  # the rest of the Spotter's settings still inherit, field by field


def test_the_page_gets_each_categorys_allowed_actions_from_the_matrix(store):
    from owlbear_delivery_next.settings.improvement import ALLOWED, CATEGORIES  # noqa: PLC0415

    got = client(store, headers=AUTH).get("/api/next/config").json()["settings"]["spotter_actions"]
    assert got == {
        "hand_off_fitness": ["record", "show-owner", "steer", "refuse-hand-off"],
        "course_and_constraints": ["record", "show-owner", "steer", "stop-and-resume", "stop-and-ask"],
        "outside_state_changes": ["record", "show-owner", "stop-and-resume", "stop-and-ask"],
        "irreversible_harm": ["record", "show-owner", "stop-and-resume", "stop-and-ask"],
    }
    assert got == {CATEGORIES[c]: list(a) for c, a in ALLOWED.items()}


def test_a_category_action_saves_survives_a_reload_and_clearing_it_inherits_the_wider_value(store, tmp_path):
    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    got = c.get("/api/next/config").json()
    wide = {"format": F, "spotter": {"hand_off_fitness": "steer", "course_and_constraints": "stop-and-ask"}}
    assert c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": wide}).status_code == 200
    got = c.get("/api/next/config").json()
    mine = {"format": F, "spotter": {"hand_off_fitness": "refuse-hand-off"}}
    assert c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": mine}).status_code == 200

    again = client(store, path, headers=AUTH).get("/api/next/config").json()  # a reload reads the files again
    spot, sources = again["settings"]["spotter"], again["settings"]["sources"]
    assert (spot["hand_off_fitness"], sources["spotter.hand_off_fitness"]) == ("refuse-hand-off", "project")
    assert (spot["course_and_constraints"], sources["spotter.course_and_constraints"]) == ("stop-and-ask", "global")

    cleared = {"format": F, "spotter": {"hand_off_fitness": None}}
    r = c.put("/api/next/config/project", json={"rev": again["project_rev"], "layer": cleared}).json()
    assert (r["settings"]["spotter"]["hand_off_fitness"], r["settings"]["sources"]["spotter.hand_off_fitness"]) == (
        "steer", "global")  # fmt: skip


@pytest.mark.parametrize(
    "spotter",
    [
        {"hand_off_fitness": "stop-and-ask"},
        {"course_and_constraints": "refuse-hand-off"},
        {"outside_state_changes": "steer"},
        {"irreversible_harm": "refuse-hand-off"},
        {"irreversible_harm": "steer"},
        {"switch": "learning"},
        {"mode": "live"},
    ],
)
def test_an_action_its_category_does_not_allow_is_refused_and_the_layer_stays(store, spotter):
    c = client(store, headers=AUTH)
    got = c.get("/api/next/config").json()
    kept = {"format": F, "spotter": {"hand_off_fitness": "record"}}
    saved = c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": kept}).json()
    before = (store.root / "config.json").read_bytes()
    r = c.put(
        "/api/next/config/project", json={"rev": saved["project_rev"], "layer": {"format": F, "spotter": spotter}}
    )
    assert r.status_code == 422
    assert (store.root / "config.json").read_bytes() == before


def test_the_global_layer_is_saved_only_where_a_location_is_configured(store, tmp_path):
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["global_rev"]
    r = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": F, "pr_marker": False}})
    assert r.status_code == 409
    assert "location" in r.json()["detail"]

    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    got = c.get("/api/next/config").json()
    assert (got["global"], got["global_location"]) == ({"format": F, "prefs": None, "prefs_imported": False,
                                                         "roles_moved": False,
                                                         "agents": {}, "widths": None,
                                                         "preparations": None, "data": None, "design_failures": None,
                                                         "final_review": None, "pr_labels": None,
                                                         "pr_marker": None, "sessions": None, "spotter": None,
                                                         "curator_threshold": None, "machine": None,
                                                         "machine_moved": None},
                                                        True)  # fmt: skip
    data = c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": {"format": F, "data": {}}})
    assert data.status_code == 422  # test preparation is a project setting (TD-96)
    layer = {"format": F, "pr_marker": False, "agents": {"builder": {"model": "g-1", "effort": "high"}}}
    r = c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": layer})
    assert r.status_code == 200
    assert json.loads(path.read_text())["pr_marker"] is False
    s = r.json()["settings"]
    assert (s["pr_marker"], s["agents"]["builder"]["model"], s["sources"]["agents.builder.model"]) == (
        False, "g-1", "global"
    )  # fmt: skip


def test_a_save_landing_while_get_reads_cannot_be_overwritten_by_that_page(store, monkeypatch):
    c = client(store, headers=AUTH)
    first = c.get("/api/next/config").json()
    a = first["project"] | {"agents": {"builder": {"effort": "low"}}}
    c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": a})
    newer = {"format": F, "agents": {"builder": {"effort": "high"}}, "widths": None}
    path, real_text, real_bytes = store.root / "config.json", Path.read_text, Path.read_bytes
    landed = []

    def concurrent(read):
        def wrapped(self: Path, *args: object, **kw: object):
            data = read(self, *args, **kw)
            if self == path and not landed:
                landed.append(True)
                path.write_text(json.dumps(newer))
            return data

        return wrapped

    monkeypatch.setattr(Path, "read_text", concurrent(real_text))
    monkeypatch.setattr(Path, "read_bytes", concurrent(real_bytes))
    seen = c.get("/api/next/config").json()
    monkeypatch.undo()

    assert seen["project"]["agents"]["builder"]["effort"] == "low"
    r = c.put("/api/next/config/project", json={"rev": seen["project_rev"], "layer": seen["project"]})
    assert r.status_code == 409
    assert store.read_config().agents["builder"].effort == "high"


def test_saves_need_the_token_and_a_local_host(store):
    body = {"rev": "x", "layer": {"format": F}}
    assert client(store).put("/api/next/config/project", json=body).status_code == 401
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://example.com", headers=AUTH)
    assert c.put("/api/next/config/project", json=body).status_code == 403
    assert not (store.root / "config.json").exists()


def test_a_stale_or_invalid_global_save_changes_nothing(store, tmp_path):
    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    rev = c.get("/api/next/config").json()["global_rev"]
    ok = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": F, "pr_marker": True}})
    assert ok.status_code == 200
    before = path.read_bytes()

    stale = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": F, "pr_marker": False}})
    bad = c.put("/api/next/config/global", json={"rev": ok.json()["global_rev"], "layer": {"widths": [100]}})

    assert (stale.status_code, bad.status_code) == (409, 422)
    assert path.read_bytes() == before


def test_global_round_values_are_valid_on_their_own_whatever_this_project_overrides(store, tmp_path):
    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    got = c.get("/api/next/config").json()
    mine = {"format": F, "agents": {"builder": {"last_round_at": 1}}}
    assert c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": mine}).status_code == 200
    hidden = {"format": F, "agents": {"builder": {"last_round_at": 8}}}  # above the default ask-owner value 7
    r = c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": hidden})
    assert (r.status_code, path.exists(), c.get("/api/next/config").status_code) == (422, False, 200)


def test_round_values_stored_out_of_fit_show_on_the_page_to_be_fixed(store, tmp_path):
    path = tmp_path / "global" / "config.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"format": 4, "agents": {"builder": {"last_round_at": 8}}}))  # e.g. edited by hand
    c = client(store, path, headers=AUTH)
    got = c.get("/api/next/config").json()
    assert got["notice"].startswith("The challenge-round values in use here do not fit together (Value error, last")
    assert got["settings"]["agents"]["builder"]["last_round_at"] == 4  # shown without them meanwhile
    fixed = {"format": F, "agents": {"builder": {"ask_owner_at": 9}}}
    saved = c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": fixed}).json()
    assert saved["settings"]["agents"]["builder"]["last_round_at"] == 8
    assert saved["notice"].startswith("The challenge-round values of the global layer and this machine do not fit")


def test_a_global_save_must_suit_every_project_sharing_it(tmp_path):
    root = tmp_path / "data"
    for name, last in (("a", None), ("b", 6)):
        (root / name).mkdir(parents=True)
        (root / name / "config.json").write_text(
            json.dumps({"format": 4, "agents": {"builder": {"last_round_at": last}}})
        )
    (root / "broken").mkdir()
    (root / "broken" / "config.json").write_text("{")  # another project's problem, never this save's
    store = Store(tmp_path / "store", data_repo.DataRepo(root), "a")
    c = client(store, root / "config.json", headers=AUTH)
    rev = c.get("/api/next/config").json()["global_rev"]
    for layer in ({"agents": {"builder": {"ask_owner_at": 6}}}, {"final_review": {"ask_owner_at": 6}}):
        r = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": F, **layer}})
        assert (r.status_code, (root / "config.json").exists()) == (422, False)  # b's last round at 6 needs more


def test_a_storage_failure_on_save_is_a_readable_error(store, monkeypatch):
    def full(*_a: object, **_k: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("owlbear_delivery_next.state_store.store.update_layer", full)
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["project_rev"]
    r = c.put("/api/next/config/project", json={"rev": rev, "layer": {"format": F}})

    assert r.status_code == 503
    assert r.json()["detail"] == "the settings could not be saved: No space left on device"


def prices(context: int | None, inp: float, out: float, long: SimpleNamespace | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        context_max=context, input_price=inp, output_price=out, cache_read_price=inp / 20, cache_price=None,
        cache_write_price=0.0, long_context=long,
    )  # fmt: skip


def offered_model(
    model_id: str, efforts: list[str] | None, policy: str | None = "enabled", tiers: SimpleNamespace | None = None
) -> SimpleNamespace:
    limits = SimpleNamespace(max_context_window_tokens=200_000)
    return SimpleNamespace(
        id=model_id, name=model_id.title(), supported_reasoning_efforts=efforts,
        default_reasoning_effort=efforts[1] if efforts else None, billing=SimpleNamespace(token_prices=tiers),
        capabilities=SimpleNamespace(limits=limits),
        policy=policy and SimpleNamespace(state=SimpleNamespace(value=policy)),
    )  # fmt: skip


def test_the_settings_offer_the_enabled_models_with_efforts_context_tiers_and_rates_read_once(store, monkeypatch):
    reads = []
    sol = prices(272_000, 200.0, 1000.0, prices(922_000, 400.0, 1500.0))

    def read() -> list[SimpleNamespace]:
        reads.append(1)
        return [offered_model("gpt-6.1-sol", ["none", "low", "medium", "high"], tiers=sol),
                offered_model("tiny", None, None), offered_model("blocked", ["low", "high"], "disabled"),
                offered_model("auto", None)]  # fmt: skip

    monkeypatch.setattr(model_choices, "_read", read)
    c = client(store, headers=AUTH)
    got = c.get("/api/next/config/models").json()
    assert got == {
        "models": [
            {"id": "gpt-6.1-sol", "name": "Gpt-6.1-Sol", "efforts": ["low", "medium", "high"],
             "default_effort": "low", "context": 272_000,
             "rates": {"input": 200.0, "output": 1000.0, "cache": 10.0, "cache_write": 0.0},
             "long": {"context": 922_000,
                      "rates": {"input": 400.0, "output": 1500.0, "cache": 20.0, "cache_write": 0.0}}},
            {"id": "tiny", "name": "Tiny", "efforts": [], "default_effort": "", "context": 200_000, "rates": None,
             "long": None},
        ],
        "error": "",
    }  # fmt: skip
    assert c.get("/api/next/config/models").json() == got
    assert len(reads) == 1  # the runtime starts once an hour at most
    unstated = SimpleNamespace(input_price=1.0, output_price=2.0, cache_read_price=None, cache_price=None,
                               cache_write_price=None)  # fmt: skip
    assert model_choices._rates(unstated)["cache"] is None  # noqa: SLF001 - shown as not known, never as free


def test_unreadable_models_leave_typing_and_are_read_again_next_time(store):
    c = client(store, headers=AUTH)
    first = c.get("/api/next/config/models").json()
    assert (first["models"], first["error"]) == ([], "OSError: offline in tests: models.list")
    assert c.get("/api/next/config/models").json() == first  # a failure is not kept: read again, still offline
    assert client(store).get("/api/next/config/models").status_code == 401


def test_this_machine_s_layer_sits_between_global_and_project_and_stays_local(store, shared_repo):
    """TD-336: built-in → global → machine → project; the machine layer lives in ~/.owlbear, never published."""
    root, remote = shared_repo
    store = Store(store.root, data_repo.DataRepo(root), "shop")
    c = client(store, store.global_path, headers=AUTH)
    got = c.get("/api/next/config").json()
    assert (got["machine"]["agents"], got["inherited"]["machine"]["agents"]["builder"]["effort"]) == ({}, "medium")
    glob = {"format": F, "agents": {"builder": {"effort": "high", "minutes": 50}, "planner": {"effort": "low"}}}
    got = c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": glob}).json()
    machine = {"format": F, "agents": {"builder": {"effort": "xhigh", "minutes": 60}}}
    saved = c.put("/api/next/config/machine", json={"rev": got["machine_rev"], "layer": machine})
    assert saved.status_code == 200
    s, sources = saved.json()["settings"], saved.json()["settings"]["sources"]
    assert (s["agents"]["builder"]["effort"], sources["agents.builder.effort"]) == ("xhigh", "machine")
    assert (s["agents"]["planner"]["effort"], sources["agents.planner.effort"]) == ("low", "global")
    assert saved.json()["inherited"]["project"]["agents"]["builder"]["minutes"] == 60  # a blank project field
    assert saved.json()["inherited"]["machine"]["agents"]["builder"]["minutes"] == 50  # a blank machine field
    project = {"format": F, "agents": {"builder": {"effort": "low"}}}
    mine = c.put("/api/next/config/project", json={"rev": saved.json()["project_rev"], "layer": project}).json()
    assert (mine["settings"]["agents"]["builder"]["effort"], mine["settings"]["sources"]["agents.builder.minutes"]) == (
        "low", "machine"
    )  # fmt: skip
    assert json.loads(store.machine_path.read_text())["agents"]["builder"]["effort"] == "xhigh"
    assert store.settings().sources["agents.builder.minutes"] == "machine"  # the runners resolve it too
    shown = subprocess.run(  # noqa: S603
        ["git", "--git-dir", str(remote), "log", "--format=%s", "main"],  # noqa: S607
        check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    assert "machine" not in shown  # never published
    assert not list(root.glob("**/settings.json"))
    stale = c.put("/api/next/config/machine", json={"rev": got["machine_rev"], "layer": {"format": F}})
    assert stale.status_code == 409


@pytest.mark.parametrize(
    "layer",
    [
        {"data": {}},
        {"visible": True},
        {"curator_threshold": 90},
        {"agents": {"builder": {"last_round_at": 8}}},
    ],
)
def test_this_machine_s_layer_refuses_project_and_global_settings_and_combinations_that_do_not_fit(store, layer):
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["machine_rev"]
    r = c.put("/api/next/config/machine", json={"rev": rev, "layer": {"format": F, **layer}})
    assert (r.status_code, store.machine_path.exists()) == (422, False)  # 8 is above the default ask-owner value 7


def test_this_machine_s_layer_must_fit_every_project_loaded_on_this_machine(store, tmp_path):
    """Sol: a project of this machine outside the shared repository is checked too, and named."""
    there = Store(tmp_path / "there")
    there.save(
        there.config_path,
        Layer,
        lambda _l: Layer.model_validate({"format": F, "agents": {"builder": {"last_round_at": 6}}}),
        "owner",
        owner=True,
    )
    host = Host()
    host.machine = lambda: [there, store]
    c = TestClient(api.create_app(store, "t", host), base_url="http://127.0.0.1", headers=AUTH)
    rev = c.get("/api/next/config").json()["machine_rev"]
    layer = {"format": F, "agents": {"builder": {"ask_owner_at": 6}}}
    refused = c.put("/api/next/config/machine", json={"rev": rev, "layer": layer})
    assert (refused.status_code, store.machine_path.exists()) == (422, False)  # fits here, not there
    assert refused.json()["detail"].startswith(f"it does not fit the project {there.root}:")
    host.machine = lambda: [store]
    assert c.put("/api/next/config/machine", json={"rev": rev, "layer": layer}).status_code == 200


def test_a_project_only_in_the_shared_repository_never_meets_this_machine_s_layer(store, shared_repo):
    """Sol: a global save is checked with this machine's layer for this machine's projects only."""
    root = shared_repo[0]
    elsewhere = {"format": F, "agents": {"builder": {"last_round_at": 6}}}  # a project of another machine
    (root / "elsewhere").mkdir()
    (root / "elsewhere" / "config.json").write_text(json.dumps(elsewhere))
    store = Store(store.root, data_repo.DataRepo(root), "shop")
    c = client(store, store.global_path, headers=AUTH)
    got = c.get("/api/next/config").json()
    machine = {"format": F, "agents": {"builder": {"ask_owner_at": 6}}}
    assert c.put("/api/next/config/machine", json={"rev": got["machine_rev"], "layer": machine}).status_code == 200
    minutes = {"format": F, "agents": {"builder": {"minutes": 50}}}
    assert c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": minutes}).status_code == 200
    got = c.get("/api/next/config").json()
    unfit = {"format": F, "agents": {"builder": {"ask_owner_at": 6}}}  # the other project's own 6 needs more
    assert c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": unfit}).status_code == 422


class _Abrupt(BaseException):
    """A stop the process cannot catch, such as a kill between the two writes."""


def _git_project(path: Path) -> Path:
    path.mkdir()
    for args in (("init", "-q"), ("remote", "add", "origin", "https://github.com/acme/shop.git")):
        subprocess.run(["git", *args], cwd=path, check=True)  # noqa: S603, S607
    return path


def _legacy_reviewer(cwd: Path) -> None:
    """A format 1 profile whose reviewer role the project config has not yet taken."""
    root = cwd / ".git" / "owlbear-delivery"
    root.mkdir(parents=True)
    raw = {
        "format": 1,
        "version": 3,
        "confirmed_at": "2026-10-01T10:00:00Z",
        "entries": {"rules": {"state": "unknown", "value": "", "evidence": "HTTP 403"}},
        "roles": {"reviewer": {"model": "r-1", "effort": "max"}},
        "runtime": "vscode",
    }
    (root / "profile.json").write_text(json.dumps(raw))


def _lose_the_marker(monkeypatch, exc: type[BaseException]) -> None:
    """Fail the first receipt-marker write: the role is applied in the config, the marker is not."""
    real, failed = roles_move.atomic_write, []

    def fails_once(target, content):
        if target.name == profile_share.ROLES_MOVED and not failed:
            failed.append(True)
            raise exc(28, "No space left on device")
        real(target, content)

    monkeypatch.setattr(roles_move, "atomic_write", fails_once)


def _store_as_opened(cwd: Path, shared: data_repo.DataRepo | None) -> Store:
    """The store ``Store.open`` returns for *cwd*, built without running the role move."""
    name = data_repo.folder(shared, cwd) if shared else ""
    return Store(project_home.located(cwd), shared, name)


def _owner_clears_after_a_lost_marker(cwd: Path, monkeypatch, exc, shared: data_repo.DataRepo | None) -> None:
    _legacy_reviewer(cwd)
    _lose_the_marker(monkeypatch, exc)
    with pytest.raises(exc):
        Store.open(cwd)  # the role is applied to the config; the receipt marker write is the one that fails
    store = _store_as_opened(cwd, shared)
    assert store.read_config().agents["reviewer"].model == "r-1"

    c = client(store, store.global_path, headers=AUTH)
    got = c.get("/api/next/config").json()
    assert got["project"]["roles_moved"] is True  # the receipt went out with the role, in the one config write
    layer = {"format": F}  # the owner clears the role: the body omits roles_moved, as the settings page does
    saved = c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": layer})
    assert saved.status_code == 200
    assert not saved.json()["unpublished"]
    cleared = store.config_path.read_bytes()
    assert store.read_config().agents == {}
    assert store.read_config().roles_moved is True

    for opened in (Store.open(cwd), Store.open(cwd)):  # a restart, then another start: the same outcome each time
        assert roles.chosen(opened.settings(), StepKind.REVIEW) == carried.MODELS["reviewer"]
        assert opened.config_path.read_bytes() == cleared
        assert (opened.root / profile_share.ROLES_MOVED).exists()


@pytest.mark.parametrize("exc", [OSError, _Abrupt], ids=["marker-fails", "abrupt-stop"])
def test_an_owner_clear_over_http_survives_a_lost_receipt_marker_unshared(tmp_path, monkeypatch, exc):
    cwd = _git_project(tmp_path / "shop")
    monkeypatch.delenv(data_repo.VIEW, raising=False)
    _owner_clears_after_a_lost_marker(cwd, monkeypatch, exc, None)


@pytest.mark.parametrize("exc", [OSError, _Abrupt], ids=["marker-fails", "abrupt-stop"])
def test_an_owner_clear_over_http_survives_a_lost_receipt_marker_shared(tmp_path, monkeypatch, shared_repo, exc):
    cwd = _git_project(tmp_path / "shop")
    monkeypatch.setenv(data_repo.VIEW, str(shared_repo[0]))
    _owner_clears_after_a_lost_marker(cwd, monkeypatch, exc, data_repo.DataRepo(shared_repo[0]))


@pytest.mark.parametrize("raw", ["{not json", '{"format": 99, "entries": {}}'], ids=["damaged", "future"])
def test_a_profile_this_build_cannot_read_is_a_repair_notice_on_settings_not_a_server_error(store, raw):
    store.root.mkdir(parents=True)
    (store.root / profile_share.PROFILE).write_text(raw)
    got = client(store, headers=AUTH).get("/api/next/config")
    assert got.status_code == 200
    assert "profile" in got.json()["notice"]
    assert "repair" in got.json()["notice"]


def test_a_machine_save_with_an_unreadable_profile_applies_and_says_so_truthfully(store):
    store.root.mkdir(parents=True)
    (store.root / profile_share.PROFILE).write_text("{not json")
    c = client(store, headers=AUTH)
    got = c.get("/api/next/config").json()
    saved = c.put(
        "/api/next/config/machine",
        json={
            "rev": got["machine_rev"],
            "layer": {"format": F, "agents": {"builder": {"effort": "high", "minutes": 50}}},
        },
    )
    assert saved.status_code == 200
    assert "profile" in saved.json()["notice"]
    assert store.machine_path.exists()


def test_a_project_save_with_an_unreadable_profile_is_refused_before_it_writes_anything(store):
    store.root.mkdir(parents=True)
    (store.root / profile_share.PROFILE).write_text("{not json")
    c = client(store, headers=AUTH)
    got = c.get("/api/next/config").json()
    refused = c.put(
        "/api/next/config/project",
        json={"rev": got["project_rev"], "layer": {"format": F, "agents": {"builder": {"effort": "high"}}}},
    )
    assert refused.status_code == 409
    assert not store.config_path.exists()
