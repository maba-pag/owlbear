import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.store import Store

AUTH = {"authorization": "Bearer t"}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC))  # noqa: S106


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
        "format": 1, "agents": {}, "runtimes": {}, "widths": None, "seed": None, "design_failures": None
    }  # fmt: skip
    assert (got["global"], got["global_location"]) == (None, False)
    assert got["settings"]["agents"]["builder"]["model"] == "claude-opus-5.5"
    assert got["settings"]["sources"]["agents.builder.model"] == "default"
    assert (got["settings"]["seed"], got["settings"]["sources"]["seed"]) == ("", "default")
    assert got["applied"] == ["agents.*.effort", "agents.*.model", "widths", "seed", "design_failures"]
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


@pytest.mark.parametrize(
    "layer",
    [
        {"agents": {"builder": {"model": "auto"}}},
        {"widths": [999]},
        {"agents": {"builder": {"context": True}}},
        {"visible": True},
        {"seed": "  "},
        {"seed": "npm run 'seed"},
    ],
)
def test_an_invalid_project_layer_is_refused_and_nothing_changes(store, layer):
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["project_rev"]
    r = c.put("/api/next/config/project", json={"rev": rev, "layer": {"format": 1, **layer}})

    assert r.status_code == 422
    assert not (store.root / "config.json").exists()


def test_the_global_layer_is_saved_only_where_a_location_is_configured(store, tmp_path):
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["global_rev"]
    r = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": 1, "visible": True}})
    assert r.status_code == 409
    assert "location" in r.json()["detail"]

    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    got = c.get("/api/next/config").json()
    assert (got["global"], got["global_location"]) == ({"format": 1, "agents": {}, "runtimes": {}, "widths": None,
                                                         "seed": None, "design_failures": None, "visible": None},
                                                        True)  # fmt: skip
    seeded = c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": {"format": 1, "seed": "x"}})
    assert seeded.status_code == 422  # the seed command is a project setting (TD-65)
    layer = {"format": 1, "visible": True, "agents": {"builder": {"model": "g-1", "effort": "high"}}}
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
    newer = {"format": 1, "agents": {"builder": {"effort": "high"}}, "runtimes": {}, "widths": None}
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
    body = {"rev": "x", "layer": {"format": 1}}
    assert client(store).put("/api/next/config/project", json=body).status_code == 401
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://example.com", headers=AUTH)
    assert c.put("/api/next/config/project", json=body).status_code == 403
    assert not (store.root / "config.json").exists()


def test_a_stale_or_invalid_global_save_changes_nothing(store, tmp_path):
    path = tmp_path / "global" / "config.json"
    c = client(store, path, headers=AUTH)
    rev = c.get("/api/next/config").json()["global_rev"]
    ok = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": 1, "visible": True}})
    assert ok.status_code == 200
    before = path.read_bytes()

    stale = c.put("/api/next/config/global", json={"rev": rev, "layer": {"format": 1, "visible": False}})
    bad = c.put("/api/next/config/global", json={"rev": ok.json()["global_rev"], "layer": {"widths": [100]}})

    assert (stale.status_code, bad.status_code) == (409, 422)
    assert path.read_bytes() == before


def test_a_storage_failure_on_save_is_a_readable_error(store, monkeypatch):
    def full(*_a: object, **_k: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("owlbear_delivery_next.store.update_layer", full)
    c = client(store, headers=AUTH)
    rev = c.get("/api/next/config").json()["project_rev"]
    r = c.put("/api/next/config/project", json={"rev": rev, "layer": {"format": 1}})

    assert r.status_code == 503
    assert r.json()["detail"] == "the settings could not be saved: No space left on device"
