"""A refused automatic config write never replaces another pending intent; a refused owner save does (R15, review)."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import profile_share
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}
CONFIG_NAME = "config.json"


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


def client(store: Store) -> TestClient:
    store.global_path = None
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)


def clone(remote: Path, where: Path, name: str) -> Store:
    subprocess.run(["git", "clone", "-q", str(remote), str(where)], check=True, capture_output=True)  # noqa: S603, S607
    return Store(where.parent / f"{name}-store", DataRepo(where), "shop-site")


@pytest.fixture
def refusing(monkeypatch) -> list[str | None]:
    """The config publications of every clone are refused while the switch is set: ``notice`` or ``raise``."""
    real, mode = DataRepo.publish, [None]

    def publish(self, path, message, until=None):
        if path.name == CONFIG_NAME and mode[0]:
            if mode[0] == "raise":
                msg = "remote unavailable"
                raise DataRepoError(msg)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)
    return mode


@pytest.fixture
def no_network(monkeypatch) -> None:
    monkeypatch.setattr(config, "BASE", None)
    monkeypatch.setattr(readiness, "check", lambda *_a, **_k: [])  # the network checks are not under test here


def remote_subjects(remote: Path) -> list[str]:
    return subprocess.run(
        ["git", "log", "--reverse", "--format=%s", "main"],  # noqa: S607
        cwd=remote,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()


@pytest.mark.usefixtures("no_network")
@pytest.mark.parametrize("mode", ["notice", "raise"])
def test_a_refused_automatic_start_cannot_replace_an_owners_pending_edit_or_publish_done(
    shared_repo, tmp_path, refusing, mode
):
    root, remote = shared_repo
    a = Store(tmp_path / "store", DataRepo(root), "shop-site")
    a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    c = client(a)
    got = c.get("/api/next/config")
    assert got.status_code == 200, got.text
    original = got.json()

    refusing[0] = mode
    edited = c.put(
        "/api/next/config/project",
        json={"rev": original["project_rev"], "layer": original["project"] | {"widths": [1600]}},
    )
    assert edited.status_code == (200 if mode == "notice" else 409), edited.text
    owner_pending = profile_share._shared_pending(a)  # noqa: SLF001
    assert owner_pending  # the owner's refused edit is pending

    b = clone(remote, tmp_path / "b", "b")
    checks = readiness.ready(b, tmp_path / "b", carry=True)  # B's normal start: an automatic config write, refused
    assert [check for check in checks if not check.ok]  # the refusal is reported, not hidden
    assert profile_share._shared_pending(b) == owner_pending  # noqa: SLF001 - the owner's intent is kept
    assert not any(s.endswith("import done") for s in remote_subjects(remote))

    refusing[0] = None
    readiness.ready(b, tmp_path / "b", carry=True)  # B's retry publishes its config, but not over the owner's intent
    assert profile_share._shared_pending(b) == owner_pending  # noqa: SLF001
    assert not any(s.endswith("import done") for s in remote_subjects(remote))


@pytest.mark.usefixtures("no_network")
@pytest.mark.parametrize("mode", ["notice", "raise"])
def test_a_refused_owner_clear_supersedes_the_earlier_pending_edit(shared_repo, tmp_path, refusing, mode):
    root, _remote = shared_repo
    a = Store(tmp_path / "store", DataRepo(root), "shop-site")
    a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    c = client(a)
    original = c.get("/api/next/config").json()

    refusing[0] = "notice"
    edit = {"rev": original["project_rev"], "layer": original["project"] | {"widths": [1600]}}
    assert c.put("/api/next/config/project", json=edit).status_code == 200
    stale_intent = profile_share._shared_pending(a)  # noqa: SLF001
    assert stale_intent

    current = c.get("/api/next/config").json()
    refusing[0] = mode
    cleared = c.put(
        "/api/next/config/project",
        json={"rev": current["project_rev"], "layer": current["project"] | {"agents": {}}, "prefs_reviewed": True},
    )
    assert cleared.status_code == (200 if mode == "notice" else 409), cleared.text
    cleared_digest = profile_share.config_digest(a.config_path)
    assert profile_share._shared_pending(a) == cleared_digest  # noqa: SLF001 - the owner's clear, not the old edit
    assert profile_share._shared_pending(a) != stale_intent  # noqa: SLF001
