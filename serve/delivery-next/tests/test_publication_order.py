"""The shared config is published before a completed legacy import's marker, whichever clone writes it (R15, review 2f).

Two clone roots share one remote. Each Store only knows its own local flag, so the order must come from the shared
repository's state, and a refused or raised profile publication must leave its retry evidence in the clone that made it.
"""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.store import Store, StoreError


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


def git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout  # noqa: S603, S607


def clone(remote: Path, where: Path) -> DataRepo:
    subprocess.run(["git", "clone", "-q", str(remote), str(where)], check=True, capture_output=True)  # noqa: S603, S607
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(where, "config", key, value)
    return DataRepo(where)


def remote_subjects(remote: Path) -> list[str]:
    """Every commit subject on the remote, oldest first."""
    return git(remote, "log", "--reverse", "--format=%s", "main").splitlines()


@pytest.fixture
def no_base(monkeypatch) -> None:
    monkeypatch.setattr(config, "BASE", None)


def refuse_done_once(monkeypatch, store: Store, *, raises: bool) -> list[str]:
    """Refuse (or raise on) the first publication of the done marker only; every other publication goes through."""
    real, refused = DataRepo.publish, []

    def publish(self, path, message, until=None):
        if path == profile_share.path(store) and message.endswith("import done") and not refused:
            refused.append(message)
            if raises:
                msg = "remote unavailable"
                raise DataRepoError(msg)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)
    return refused


def refuse_config_removal_once(monkeypatch, store: Store) -> None:
    """Refuse the owner's removal of the project config the first time only."""
    real, refused = DataRepo.publish, []

    def publish(self, path, message, until=None):
        if path == store.config_path and message.endswith("project layer removed") and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)


@pytest.mark.usefixtures("no_base")
def test_a_done_marker_from_a_clone_without_the_flag_waits_for_the_refused_config_removal(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    a = Store(tmp_path / "store-a", DataRepo(root), "shop-site")
    a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_done_once(monkeypatch, a, raises=False)
    with pytest.raises(StoreError):
        prefs_import.run(a)  # the config is published, the done marker is refused; A alone holds the flag
    assert profile_share.unpublished(a)

    a.config_path.unlink()  # the owner deletes the project config in A; its removal is refused
    refuse_config_removal_once(monkeypatch, a)
    with pytest.raises(StoreError):
        prefs_import.republish(a)  # A records the unpublished removal in the shared repository

    b = Store(tmp_path / "store-b", clone(remote, tmp_path / "clone-b"), "shop-site")
    assert not profile_share.unpublished(b)  # B has no local evidence of A's refused completion
    b_profile = b.read_profile()
    assert b_profile is not None
    assert b_profile.prefs_import == "pending"
    _, notice, applied = b.mark_prefs_import("pending", "done")
    assert applied
    assert notice  # B's done marker waits for A's removal
    assert not any(s.endswith("import done") for s in remote_subjects(remote))  # no remote done yet

    prefs_import.run(a)  # A's retry publishes its removal first, then the done marker
    assert not profile_share.unpublished(a)
    fresh = Store(tmp_path / "fresh", clone(remote, tmp_path / "clone-c"), "shop-site")
    got = fresh.read_profile()
    assert got is not None
    assert got.prefs_import == "done"
    assert not fresh.config_path.exists()


@pytest.mark.usefixtures("no_base")
def test_a_refused_done_publication_stays_retryable_by_the_same_clone_after_the_config_publishes(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_done_once(monkeypatch, store, raises=True)

    with pytest.raises(StoreError):
        prefs_import.run(store)

    assert profile_share.unpublished(store)  # the failed publication is recorded before the exception left the store
    before = Store(tmp_path / "probe", clone(remote, tmp_path / "probe-clone"), "shop-site").read_profile()
    assert before is not None
    assert before.prefs_import != "done"

    fresh = Store(tmp_path / "store", DataRepo(root), "shop-site")  # a new process on the same clone root
    prefs_import.run(fresh)  # the startup retry publishes the current config, then the done marker

    assert not profile_share.unpublished(fresh)
    probe = Store(tmp_path / "probe2", clone(remote, tmp_path / "probe2-clone"), "shop-site")
    got = probe.read_profile()
    assert got is not None
    assert got.prefs_import == "done"
    assert probe.read_config().prefs.ci_poll_seconds == 45
