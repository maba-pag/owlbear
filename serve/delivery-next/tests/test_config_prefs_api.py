import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.project_host.config_routes import PREFS_REVIEW
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store.store import Store

from .test_config_api import client
from .test_prefs_recovery import refuse_config_once

AUTH = {"authorization": "Bearer " + "t"}


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store")


def test_the_five_preferences_save_resolve_and_clear_to_unset_through_the_api(store, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)  # the test-only base layer would supply the unset values
    store.write_profile(Profile())
    store.mark_prefs_import("", "pending", "absent")
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    layer = first["project"] | {"prefs": {"ci_poll_seconds": 45, "merge_method": "squash"}}
    raw = c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": layer, "prefs_reviewed": True})
    assert raw.status_code == 200
    saved = raw.json()
    assert store.read_profile().prefs_import == "done"
    assert store.read_config().prefs.ci_poll_seconds == 45
    assert saved["settings"]["prefs"]["ci_poll_seconds"] == 45
    assert saved["settings"]["sources"]["prefs.ci_poll_seconds"] == "project"
    assert saved["settings"]["prefs"]["ask_before_merge"] is None
    assert "prefs.ask_before_merge" in saved["settings"]["missing"]

    store.mark_prefs_import("done", "pending", "absent")
    cleared = {"prefs": {"ci_poll_seconds": None, "merge_method": "squash"}}
    response = c.put(
        "/api/next/config/project", json={"rev": saved["project_rev"], "layer": layer | cleared, "prefs_reviewed": True}
    )
    assert response.status_code == 200
    again = response.json()
    assert again["settings"]["prefs"]["ci_poll_seconds"] is None
    assert again["settings"]["prefs"]["merge_method"] == "squash"
    assert "prefs.ci_poll_seconds" in again["settings"]["missing"]
    assert store.read_config().prefs.ci_poll_seconds is None
    assert store.read_profile().prefs_import == "done"


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


@pytest.mark.parametrize("clearing", [False, True], ids=["edit", "clear"])
def test_a_refused_publication_of_an_edited_preference_stays_pending_until_published(
    shared_repo, tmp_path, monkeypatch, clearing
):
    monkeypatch.setattr(config, "BASE", None)
    root, remote = shared_repo
    store = Store(tmp_path / "store", data_repo.DataRepo(root), "shop-site")
    store.write_profile(Profile())
    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    if clearing:
        response = c.put(
            "/api/next/config/project",
            json={"rev": first["project_rev"], "layer": first["project"] | {"prefs": {"ci_poll_seconds": 45}}},
        )
        assert response.status_code == 200
        first = response.json()
    store.mark_prefs_import("", "pending", "absent")
    refuse_config_once(monkeypatch, store)
    poll = None if clearing else 30
    layer = first["project"] | {"prefs": {"ci_poll_seconds": poll}}
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
    assert fresh.read_config().prefs.ci_poll_seconds == poll
    assert fresh.read_profile().prefs_import == "done"
