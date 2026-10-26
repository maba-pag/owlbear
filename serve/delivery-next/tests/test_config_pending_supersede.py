import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import profile_share
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    maintenance = None
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def client(store: Store) -> TestClient:
    store.global_path = None
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)


def fresh_config(remote: Path, tmp_path: Path) -> Store:
    where = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(where)], check=True, capture_output=True)  # noqa: S603, S607
    return Store(tmp_path / "fresh-store", DataRepo(where), "shop")


def refuse_config_once(monkeypatch, store: Store) -> None:
    real, refused = DataRepo.publish, []

    def refuse(self, path, message, until=None):
        if path == store.config_path and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", refuse)


def test_an_owner_clear_supersedes_a_refused_config_edit_and_a_stale_write_cannot_replace_it(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop")
    c = client(store)
    original = c.get("/api/next/config").json()
    refuse_config_once(monkeypatch, store)

    edited = c.put(
        "/api/next/config/project",
        json={
            "rev": original["project_rev"],
            "layer": original["project"] | {"agents": {"builder": {"effort": "low"}}},
        },
    )
    assert edited.status_code == 200
    pending = profile_share._shared_pending(store)  # noqa: SLF001
    assert pending  # the refused edit is recorded as pending, by its digest

    stale = c.put("/api/next/config/project", json={"rev": original["project_rev"], "layer": original["project"]})
    assert stale.status_code == 409
    assert profile_share._shared_pending(store) == pending  # noqa: SLF001

    store.update_config(lambda cur: cur.model_copy(update={"prefs_imported": True}), "automatic carry")
    # an automatic write that is not the owner's cannot replace the pending intent
    assert profile_share._shared_pending(store) == pending  # noqa: SLF001

    current = c.get("/api/next/config").json()
    cleared = c.put(
        "/api/next/config/project",
        json={"rev": current["project_rev"], "layer": current["project"] | {"agents": {}}, "prefs_reviewed": True},
    )
    assert cleared.status_code == 200
    assert profile_share._shared_pending(store) == ""  # noqa: SLF001

    fresh = fresh_config(remote, tmp_path)
    assert fresh.read_config().agents == {}
    assert fresh.read_config().prefs_imported is True
