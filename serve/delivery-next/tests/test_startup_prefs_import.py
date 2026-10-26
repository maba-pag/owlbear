"""A host start carries the one-time legacy preference import and retries its refused completion (R15, review)."""

import contextlib
import inspect
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import SharedError, Store


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
def test_a_carry_whose_shared_lock_cannot_be_taken_is_a_failed_check_and_the_next_start_carries(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real_locked, blocked = DataRepo.locked, [True]
    monkeypatch.setattr(profile, "detect", lambda *_a: Profile(entries={profile.POLL: confirmed("45")}))

    @contextlib.contextmanager
    def busy_for_the_carry(self, wait=None):
        if blocked[0] and any(f.filename.endswith("/state_store/prefs_import.py") for f in inspect.stack()):
            msg = "the shared lock is held by another clone"
            raise DataRepoError(msg)
        with real_locked(self, wait):
            yield

    monkeypatch.setattr(DataRepo, "locked", busy_for_the_carry)
    failed = [c for c in readiness.ready(store, root, carry=True) if not c.ok]  # no exception escapes the start
    assert [c.name for c in failed] == ["legacy preferences"]
    assert "held by another clone" in failed[0].detail
    assert store.read_config().prefs is None  # nothing is filled while the import is unconfirmed
    assert store.read_profile().prefs_import == ""  # no claim or completion was recorded

    blocked[0] = False
    assert not [c for c in readiness.ready(store, root, carry=True) if not c.ok]
    assert store.read_config().prefs.ci_poll_seconds == 45
    _, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"


@pytest.mark.usefixtures("no_network")
def test_a_carry_whose_local_flag_cannot_be_written_is_a_failed_check_and_the_next_start_publishes_done(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real_touch, blocked = Path.touch, [True]

    def no_space_for_flag(self, *args, **kwargs):
        if blocked[0] and self.name == profile_share.UNPUBLISHED:
            raise OSError(28, "No space left on device")
        return real_touch(self, *args, **kwargs)

    monkeypatch.setattr(Path, "touch", no_space_for_flag)
    failed = [c for c in readiness.ready(store, root, carry=True) if not c.ok]  # no exception escapes the start
    assert [c.name for c in failed] == ["legacy preferences"]
    assert "No space left" in failed[0].detail
    _, before = clone_profile(remote, tmp_path / "before")
    assert before.prefs_import != "done"  # the completion never reached the shared profile

    blocked[0] = False
    assert not [c for c in readiness.ready(store, root, carry=True) if not c.ok]
    assert store.read_config().prefs.ci_poll_seconds == 45
    _, got = clone_profile(remote, tmp_path / "after")
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


def remote_subjects(remote: Path) -> list[str]:
    return subprocess.run(
        ["git", "log", "--reverse", "--format=%s", "main"],  # noqa: S607
        cwd=remote,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()


@pytest.mark.usefixtures("no_network")
@pytest.mark.parametrize("action", ["edit", "remove"])
def test_a_raised_config_refusal_keeps_the_shared_evidence_so_a_fresh_start_cannot_publish_done(
    shared_repo, tmp_path, monkeypatch, action
):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real, refused = DataRepo.publish, []

    def refuse_done(self, path, message, until=None):
        if path == profile_share.path(store) and message.endswith("import done") and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", refuse_done)
    readiness.ready(store, root, carry=True)  # the config is published; the done marker is refused in A
    assert refused

    def raise_config(self, path, message, until=None):
        if path == store.config_path and not raised:
            raised.append(message)
            msg = "remote unavailable"
            raise DataRepoError(msg)
        return refuse_done(self, path, message, until)

    raised: list[str] = []
    monkeypatch.setattr(DataRepo, "publish", raise_config)
    if action == "edit":
        with pytest.raises(SharedError):
            store.save(
                store.config_path,
                config.Layer,
                lambda cur: cur.model_copy(update={"widths": [1600]}),
                "edit",
                owner=True,
            )
    else:
        store.config_path.unlink()
        with pytest.raises(StoreError):
            prefs_import.republish(store)
    assert raised

    monkeypatch.setattr(DataRepo, "publish", real)
    fresh_b, _ = clone_profile(remote, tmp_path)
    checks = readiness.ready(fresh_b, tmp_path / "fresh", carry=True)  # a clone without A's local flag
    assert [c for c in checks if not c.ok]
    assert not any(s.endswith("import done") for s in remote_subjects(remote))

    readiness.ready(store, root, carry=True)  # A's retry publishes the config first, then the done marker
    third = tmp_path / "third"
    subprocess.run(["git", "clone", "-q", str(remote), str(third)], check=True, capture_output=True)  # noqa: S603, S607
    got = Store(tmp_path / "third-store", DataRepo(third), "shop-site")
    assert got.read_profile().prefs_import == "done"
    if action == "edit":
        assert got.read_config().widths == [1600]
    else:
        assert not got.config_path.exists()


@pytest.mark.usefixtures("no_network")
@pytest.mark.parametrize("raises", [False, True])
def test_a_refused_detection_publication_is_a_failed_readiness_check(shared_repo, tmp_path, monkeypatch, raises):
    root, _remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    monkeypatch.setattr(profile, "detect", lambda *_a: Profile(entries={profile.POLL: confirmed("60")}))
    real, refused = DataRepo.publish, []

    def refuse_detection(self, path, message, until=None):
        if path == profile_share.path(store) and message.endswith("detected in a clone") and not refused:
            refused.append(message)
            if raises:
                msg = "remote unavailable"
                raise DataRepoError(msg)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", refuse_detection)
    first = readiness.ready(store, root, carry=True)
    assert refused
    failed = [c for c in first if c.name == "profile detection"]
    assert [c.ok for c in failed] == [False], [(c.name, c.ok, c.detail) for c in first]

    monkeypatch.setattr(DataRepo, "publish", real)
    again = readiness.ready(store, root, carry=True)
    assert not [c for c in again if not c.ok]
