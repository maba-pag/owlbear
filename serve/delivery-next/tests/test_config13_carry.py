"""Format 13 on the real entrypoints: legacy preferences carry once; owner saves and clears stick (R15)."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import CONFIG_FORMAT as F
from owlbear_delivery_next.settings.config import Prefs
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}
LEGACY = {
    profile.METHOD: ProfileEntry(state="known", value="squash", evidence="default"),
    profile.DELETE: ProfileEntry(state="known", value="no", evidence=f"{profile.CONFIRMED}; owner"),
    profile.POLL: ProfileEntry(state="known", value="20", evidence="allowed: 20 or 45"),
    profile.WINDOW: ProfileEntry(state="known", value="0", evidence=f"{profile.CONFIRMED}; owner"),
    profile.ASK: ProfileEntry(state="known", value="no", evidence=f"{profile.CONFIRMED}; owner"),
}  # the five legacy values: an enum, a default, false, zero, and a confirmed false
CARRIED = Prefs(
    merge_method=MergeMethod.SQUASH,
    delete_remote_branch=False,
    ci_poll_seconds=20,
    ci_start_window_seconds=0,
    ask_before_merge=False,
)
FORMAT_12 = {
    "format": 12,
    "spotter": {"mode": "learning", "steer_share": 20, "intervention_cap": 3, "verbose": "off", "looks": ["hand-off"]},
    "agents": {"spotter": {"model": "gpt-6-luna", "effort": "medium"}},
    "widths": [1600],
    "sessions": 3,
    "pr_labels": ["ready"],
    "pr_marker": True,
}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


@pytest.fixture
def no_network(monkeypatch) -> None:
    monkeypatch.setattr(config, "BASE", None)
    monkeypatch.setattr(readiness, "check", lambda *_a, **_k: [])


def reopen(root: Path, tmp_path: Path) -> Store:
    return Store(tmp_path / "store", DataRepo(root), "shop-site")


def seeded(root: Path, tmp_path: Path) -> Store:
    store = reopen(root, tmp_path)
    store.write_profile(Profile(entries=LEGACY))
    store.config_path.parent.mkdir(parents=True, exist_ok=True)
    store.config_path.write_text(json.dumps(FORMAT_12))
    return store


def started(store: Store, root: Path) -> None:
    assert not [c for c in readiness.ready(store, root, carry=True) if not c.ok]


def owner_save(store: Store, edit) -> None:
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)
    first = c.get("/api/next/config").json()
    r = c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": edit(first["project"])})
    assert r.status_code == 200, r.text


def fresh_clone(remote: Path, tmp_path: Path) -> Store:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    return Store(tmp_path / "fresh-store", DataRepo(second), "shop-site")


@pytest.mark.usefixtures("no_network")
def test_a_format_12_project_upgrades_and_carries_each_legacy_value_once(shared_repo, tmp_path):
    root, _ = shared_repo
    store = seeded(root, tmp_path)

    started(store, root)
    layer = store.read_config()

    assert layer.format == F
    assert layer.prefs == CARRIED
    assert layer.prefs_imported is True
    assert (layer.spotter.mode, layer.spotter.steer_share, layer.agents["spotter"].model) == (
        "learning",
        20,
        "gpt-6-luna",
    )
    assert (layer.widths, layer.sessions, layer.pr_labels, layer.pr_marker) == ([1600], 3, ["ready"], True)
    started(reopen(root, tmp_path), root)  # a restart fills nothing again
    assert reopen(root, tmp_path).read_config() == layer


@pytest.mark.usefixtures("no_network")
def test_an_owner_save_and_a_restart_keep_the_new_values_and_an_owner_null_stays_null(shared_repo, tmp_path):
    root, remote = shared_repo
    store = seeded(root, tmp_path)
    started(store, root)

    def edit(project: dict) -> dict:
        return project | {
            "spotter": project["spotter"] | {"mode": "off"},
            "prefs": project["prefs"] | {"ci_poll_seconds": None},
        }

    owner_save(store, edit)
    restarted = reopen(root, tmp_path)
    started(restarted, root)
    got = restarted.read_config()

    assert got.spotter.mode == "off"
    assert got.prefs == CARRIED.model_copy(update={"ci_poll_seconds": None})
    assert got.prefs_imported is True
    assert got.agents["spotter"].model == "gpt-6-luna"
    fresh = fresh_clone(remote, tmp_path).read_config()
    assert (fresh.format, fresh.spotter.mode, fresh.prefs.ci_poll_seconds) == (F, "off", None)


@pytest.mark.usefixtures("no_network")
def test_an_owner_clear_after_the_import_is_published_and_never_refilled(shared_repo, tmp_path):
    root, remote = shared_repo
    store = seeded(root, tmp_path)
    started(store, root)

    owner_save(store, lambda project: project | {"prefs": None})
    started(reopen(root, tmp_path), root)

    restarted = reopen(root, tmp_path).read_config()
    assert restarted.prefs is None
    assert restarted.prefs_imported is True
    assert fresh_clone(remote, tmp_path).read_config().prefs is None
