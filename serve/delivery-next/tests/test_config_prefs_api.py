import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.config_routes import PREFS_REVIEW
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer " + "t"}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    maintenance = None
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store")


def client(store: Store, global_path: Path | None = None, **kw: object) -> TestClient:
    store.global_path = global_path
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", **kw)


def test_the_five_preferences_save_resolve_and_clear_to_unset_through_the_api(store, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)  # the test-only base layer would supply the unset values
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    layer = first["project"] | {"prefs": {"ci_poll_seconds": 45, "merge_method": "squash"}}
    raw = c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": layer})
    saved = raw.json()
    assert saved["settings"]["prefs"]["ci_poll_seconds"] == 45
    assert saved["settings"]["sources"]["prefs.ci_poll_seconds"] == "project"
    assert saved["settings"]["prefs"]["ask_before_merge"] is None
    assert "prefs.ask_before_merge" in saved["settings"]["missing"]

    cleared = {"prefs": {"ci_poll_seconds": None, "merge_method": "squash"}}
    again = c.put("/api/next/config/project", json={"rev": saved["project_rev"], "layer": layer | cleared}).json()
    assert again["settings"]["prefs"]["ci_poll_seconds"] is None
    assert "prefs.ci_poll_seconds" in again["settings"]["missing"]
    assert store.read_config().prefs.ci_poll_seconds is None


def test_an_owner_save_of_the_preferences_settles_a_pending_import_for_review(store, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    store.write_profile(Profile())
    store.mark_prefs_import("", "pending", "absent")  # a claim whose fill is unknown: the owner reviews it
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    layer = first["project"] | {"prefs": {"ci_poll_seconds": 30}}
    review = {"rev": first["project_rev"], "layer": layer, "prefs_reviewed": True}
    assert c.put("/api/next/config/project", json=review).status_code == 200
    assert store.read_profile().prefs_import == "done"
    assert store.read_config().prefs.ci_poll_seconds == 30


def _refuse_config_publication_once(monkeypatch, config_path):
    real, refused = data_repo.DataRepo.publish, []

    def refuse(self, path, message, until=None):
        if path == config_path and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(data_repo.DataRepo, "publish", refuse)


def _fresh_store(tmp_path: Path, remote: Path) -> Store:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    return Store(tmp_path / "fresh-store", data_repo.DataRepo(second), "shop-site")


def test_a_width_only_save_leaves_a_pending_import_pending_with_the_review_diagnostic(store, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    store.write_profile(Profile())
    store.mark_prefs_import("", "pending", "absent")
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    saved = c.put(
        "/api/next/config/project", json={"rev": first["project_rev"], "layer": first["project"] | {"prefs": None}}
    )
    assert saved.status_code == 200
    assert saved.json()["notice"] == PREFS_REVIEW
    assert store.read_profile().prefs_import == "pending"
    assert c.get("/api/next/config").json()["notice"] == PREFS_REVIEW


def test_an_explicit_clear_of_a_preference_settles_a_pending_import(store, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    kept = c.put(
        "/api/next/config/project",
        json={"rev": first["project_rev"], "layer": first["project"] | {"prefs": {"ci_poll_seconds": 45}}},
    ).json()
    store.write_profile(Profile())
    store.mark_prefs_import("", "pending", "absent")
    cleared = {"ci_poll_seconds": None}
    got = c.put(
        "/api/next/config/project",
        json={"rev": kept["project_rev"], "layer": kept["project"] | {"prefs": cleared}, "prefs_reviewed": True},
    )
    assert got.status_code == 200
    assert got.json()["settings"]["prefs"]["ci_poll_seconds"] is None
    assert store.read_profile().prefs_import == "done"


def test_a_refused_publication_of_an_edited_preference_stays_pending_until_published(
    shared_repo, tmp_path, monkeypatch
):
    monkeypatch.setattr(config, "BASE", None)
    root, remote = shared_repo
    store = Store(tmp_path / "store", data_repo.DataRepo(root), "shop-site")
    store.write_profile(Profile())
    store.mark_prefs_import("", "pending", "absent")
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    _refuse_config_publication_once(monkeypatch, store.config_path)
    layer = first["project"] | {"prefs": {"ci_poll_seconds": 30}}
    refused = c.put(
        "/api/next/config/project", json={"rev": first["project_rev"], "layer": layer, "prefs_reviewed": True}
    )
    assert refused.status_code == 200
    assert refused.json()["notice"]
    assert refused.json()["notice"] != PREFS_REVIEW
    assert store.read_profile().prefs_import == "pending"
    again = c.get("/api/next/config").json()
    retry = c.put(
        "/api/next/config/project", json={"rev": again["project_rev"], "layer": layer, "prefs_reviewed": True}
    )
    assert retry.status_code == 200
    assert not retry.json()["notice"]
    assert store.read_profile().prefs_import == "done"
    fresh = _fresh_store(tmp_path, remote)
    assert fresh.read_config().prefs.ci_poll_seconds == 30
    assert fresh.read_profile().prefs_import == "done"


def test_a_refused_publication_of_a_cleared_preference_stays_pending_until_published(
    shared_repo, tmp_path, monkeypatch
):
    monkeypatch.setattr(config, "BASE", None)
    root, remote = shared_repo
    store = Store(tmp_path / "store", data_repo.DataRepo(root), "shop-site")
    store.write_profile(Profile())
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    kept = c.put(
        "/api/next/config/project",
        json={"rev": first["project_rev"], "layer": first["project"] | {"prefs": {"ci_poll_seconds": 45}}},
    ).json()
    store.mark_prefs_import("", "pending", "absent")
    _refuse_config_publication_once(monkeypatch, store.config_path)
    layer = kept["project"] | {"prefs": {"ci_poll_seconds": None}}
    refused = c.put(
        "/api/next/config/project", json={"rev": kept["project_rev"], "layer": layer, "prefs_reviewed": True}
    )
    assert refused.json()["notice"]
    assert store.read_profile().prefs_import == "pending"
    again = c.get("/api/next/config").json()
    retry = c.put(
        "/api/next/config/project", json={"rev": again["project_rev"], "layer": layer, "prefs_reviewed": True}
    )
    assert not retry.json()["notice"]
    assert store.read_profile().prefs_import == "done"
    fresh = _fresh_store(tmp_path, remote)
    assert fresh.read_config().prefs.ci_poll_seconds is None
    assert fresh.read_profile().prefs_import == "done"
