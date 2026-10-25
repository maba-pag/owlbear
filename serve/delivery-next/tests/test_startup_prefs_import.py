"""A host start carries the one-time legacy preference import and retries its refused completion (R15, review)."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import profile_share
from owlbear_delivery_next.state_store.store import Store


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


def clone_profile(remote: Path, tmp_path: Path) -> tuple[Store, Profile]:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(second), "shop-site")
    return fresh, fresh.read_profile()


@pytest.fixture
def no_network(monkeypatch) -> None:
    monkeypatch.setattr(config, "BASE", None)
    monkeypatch.setattr(readiness, "check", lambda *_a, **_k: [])  # the network checks are not under test here


@pytest.mark.usefixtures("no_network")
def test_a_host_start_carries_an_upgraded_projects_legacy_preference_once(shared_repo, tmp_path):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))

    checks = readiness.ready(store, root, carry=True)

    assert not [c for c in checks if not c.ok]
    assert store.read_config().prefs.ci_poll_seconds == 45
    _, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"


@pytest.mark.usefixtures("no_network")
def test_a_refused_completion_is_reported_at_start_and_published_by_the_next_start(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real, refused = DataRepo.publish, []

    def publish(self, path, message, until=None):
        if path == profile_share.path(store) and message.endswith("import done") and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)

    first = readiness.ready(store, root, carry=True)
    assert refused
    assert [c.ok for c in first if c.detail and "completion was not published" in c.detail] == [False]
    assert store.read_config().prefs.ci_poll_seconds == 45  # the import's values are kept for the retry

    monkeypatch.setattr(DataRepo, "publish", real)
    second = readiness.ready(store, root, carry=True)

    assert not [c for c in second if not c.ok]
    _, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
