import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import model_choices
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}


class Host:
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
        "format": 5, "agents": {}, "runtimes": {}, "widths": None, "preparations": None, "data": None,
        "design_failures": None, "explore": None, "final_review": None, "pr_labels": None, "pr_marker": None,
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
        "agents.design-judge.minutes", "agents.preparer.minutes", "agents.updater.minutes", "pr_labels", "pr_marker",
    ]  # fmt: skip
    assert len(got["project_rev"]) == 64


def test_get_describes_each_runtime_and_where_a_tool_category_lives(store):
    got = client(store, headers=AUTH).get("/api/next/config").json()
    rows = {r["runtime"]: r for r in got["catalogue"]["runtimes"]}

    assert set(rows) == {"sdk", "window"}
    assert rows["sdk"]["outside_writes"].startswith("Delivery's hard guard")
    assert rows["window"]["live_view"] == "yes"
    browser = got["catalogue"]["categories"]["browser"]
    assert browser["runtime"] == "window"
    assert {"openBrowserPage", "screenshotPage"} <= set(browser["tools"])


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
    r = c.put("/api/next/config/project", json={"rev": rev, "layer": {"format": 5, **layer}})

    assert r.status_code == 422
    assert not (store.root / "config.json").exists()


def test_the_global_layer_is_saved_only_where_a_location_is_configured(store, tmp_path):
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["global_rev"]
    r = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": 5, "visible": True}})
    assert r.status_code == 409
    assert "location" in r.json()["detail"]

    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    got = c.get("/api/next/config").json()
    assert (got["global"], got["global_location"]) == ({"format": 5, "agents": {}, "runtimes": {}, "widths": None,
                                                         "preparations": None, "data": None, "design_failures": None,
                                                         "explore": None, "final_review": None, "pr_labels": None,
                                                         "pr_marker": None, "visible": None},
                                                        True)  # fmt: skip
    data = c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": {"format": 5, "data": {}}})
    assert data.status_code == 422  # test preparation is a project setting (TD-96)
    layer = {"format": 5, "visible": True, "agents": {"builder": {"model": "g-1", "effort": "high"}}}
    r = c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": layer})
    assert r.status_code == 200
    assert json.loads(path.read_text())["visible"] is True
    s = r.json()["settings"]
    assert (s["visible"], s["agents"]["builder"]["model"], s["sources"]["agents.builder.model"]) == (
        True, "g-1", "global"
    )  # fmt: skip


def test_a_save_landing_while_get_reads_cannot_be_overwritten_by_that_page(store, monkeypatch):
    c = client(store, headers=AUTH)
    first = c.get("/api/next/config").json()
    a = first["project"] | {"agents": {"builder": {"effort": "low"}}}
    c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": a})
    newer = {"format": 5, "agents": {"builder": {"effort": "high"}}, "runtimes": {}, "widths": None}
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
    body = {"rev": "x", "layer": {"format": 5}}
    assert client(store).put("/api/next/config/project", json=body).status_code == 401
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://example.com", headers=AUTH)
    assert c.put("/api/next/config/project", json=body).status_code == 403
    assert not (store.root / "config.json").exists()


def test_a_stale_or_invalid_global_save_changes_nothing(store, tmp_path):
    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    rev = c.get("/api/next/config").json()["global_rev"]
    ok = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": 5, "visible": True}})
    assert ok.status_code == 200
    before = path.read_bytes()

    stale = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": 5, "visible": False}})
    bad = c.put("/api/next/config/global", json={"rev": ok.json()["global_rev"], "layer": {"widths": [100]}})

    assert (stale.status_code, bad.status_code) == (409, 422)
    assert path.read_bytes() == before


def test_global_round_values_are_valid_on_their_own_whatever_this_project_overrides(store, tmp_path):
    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    got = c.get("/api/next/config").json()
    mine = {"format": 5, "agents": {"builder": {"last_round_at": 1}}}
    assert c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": mine}).status_code == 200
    hidden = {"format": 5, "agents": {"builder": {"last_round_at": 8}}}  # above the default ask-owner value 7
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
    fixed = {"format": 5, "agents": {"builder": {"ask_owner_at": 9}}}
    saved = c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": fixed}).json()
    assert saved["settings"]["agents"]["builder"]["last_round_at"] == 8
    assert saved["notice"].startswith("The global challenge-round values do not fit together on their own")


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
        r = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": 5, **layer}})
        assert (r.status_code, (root / "config.json").exists()) == (422, False)  # b's last round at 6 needs more


def test_a_storage_failure_on_save_is_a_readable_error(store, monkeypatch):
    def full(*_a: object, **_k: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("owlbear_delivery_next.state_store.store.update_layer", full)
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["project_rev"]
    r = c.put("/api/next/config/project", json={"rev": rev, "layer": {"format": 5}})

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
