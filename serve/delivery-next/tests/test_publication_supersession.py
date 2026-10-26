"""A clone's automatic config change waits behind another clone's pending owner intent; the DONE flag is durable."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import profile_share
from owlbear_delivery_next.state_store.pending_intents import pending_intents
from owlbear_delivery_next.state_store.profile_share import CONFIG_WAITING
from owlbear_delivery_next.state_store.store import Store

CONFIG_NAME = "config.json"
SHARED_CONFIG = "shop-site/config.json"
SHARED_PROFILE = f"shop-site/{profile_share.PROFILE}"


class Stop(BaseException):
    """A stop that is not an ordinary error: the process ends right after the local DONE write."""


def clone(remote: Path, where: Path, name: str) -> Store:
    subprocess.run(["git", "clone", "-q", str(remote), str(where)], check=True, capture_output=True)  # noqa: S603, S607
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        subprocess.run(["git", "-C", str(where), "config", key, value], check=True)  # noqa: S603, S607
    return Store(where.parent / f"{name}-store", DataRepo(where), "shop-site")


def remote_bytes(remote: Path, rel: str) -> bytes:
    """The file's bytes on the remote's main branch; empty when it is not published yet."""
    shown = subprocess.run(  # noqa: S603
        ["git", "show", f"main:{rel}"],  # noqa: S607
        cwd=remote,
        check=False,
        capture_output=True,
    )
    return shown.stdout if shown.returncode == 0 else b""


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


def widths(value: int):
    def change(cur: Layer) -> Layer:
        return cur.model_copy(update={"widths": [value]})

    return change


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
def config_publishes(monkeypatch) -> list[str]:
    """Every publication of a project config by any clone, recorded before it runs."""
    real, seen = DataRepo.publish, []

    def publish(self, path, message, until=None):
        if path.name == CONFIG_NAME:
            seen.append(message)
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)
    return seen


@pytest.fixture
def no_network(monkeypatch) -> None:
    monkeypatch.setattr(config, "BASE", None)
    monkeypatch.setattr(readiness, "check", lambda *_a, **_k: [])


@pytest.mark.usefixtures("no_network")
@pytest.mark.parametrize("automatic", ["success", "notice", "raise"])
def test_an_automatic_config_change_waits_behind_another_clones_pending_owner_intent(
    shared_repo, tmp_path, refusing, config_publishes, automatic
):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")

    refusing[0] = "notice"
    assert a.save(a.config_path, Layer, widths(1600), "owner edit", owner=True)  # refused: pending, not published
    b = clone(remote, tmp_path / "b", "b")  # B's checkout now carries the pending record
    pending = profile_share._shared_pending(a)  # noqa: SLF001
    assert pending
    before = remote_bytes(remote, SHARED_CONFIG)
    assert b"1600" not in before

    # B's automatic change is held before any write, whatever the remote would do with it
    refusing[0] = {"success": None, "notice": "notice", "raise": "raise"}[automatic]
    config_publishes.clear()
    assert b.save(b.config_path, Layer, widths(1300), "automatic", owner=False) == CONFIG_WAITING
    assert config_publishes == []
    assert not b.config_path.exists()
    assert remote_bytes(remote, SHARED_CONFIG) == before
    assert profile_share._shared_pending(b) == pending  # noqa: SLF001

    # A completion retry, with a different local value or a local removal, never publishes the config
    with b.shared.locked():
        assert profile_share.publish_config_unlocked(b) == CONFIG_WAITING
    b.config_path.unlink(missing_ok=True)
    with b.shared.locked():
        assert profile_share.publish_config_unlocked(b) == CONFIG_WAITING
    assert config_publishes == []
    assert remote_bytes(remote, SHARED_CONFIG) == before
    assert profile_share._shared_pending(b) == pending  # noqa: SLF001

    # A matching automatic change is not held: it publishes and clears the pending intent
    refusing[0] = None
    assert b.save(b.config_path, Layer, widths(1600), "matching", owner=False) == ""
    assert profile_share._shared_pending(b) == ""  # noqa: SLF001
    assert b"1600" in remote_bytes(remote, SHARED_CONFIG)


@pytest.mark.usefixtures("no_network")
def test_an_owner_value_supersedes_the_held_pending_intent_and_publishes(shared_repo, tmp_path, refusing):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    refusing[0] = "notice"
    assert a.save(a.config_path, Layer, widths(1600), "owner edit", owner=True)
    b = clone(remote, tmp_path / "b", "b")
    assert profile_share._shared_pending(a)  # noqa: SLF001

    refusing[0] = None
    assert a.save(a.config_path, Layer, widths(1700), "owner new value", owner=True) == ""
    assert profile_share._shared_pending(a) == ""  # noqa: SLF001
    assert b"1700" in remote_bytes(remote, SHARED_CONFIG)
    assert b.shared.pull() == ""  # the clone syncs as startup does; its stale pending copy is not an intent
    assert pending_intents(b) == set()


@pytest.mark.usefixtures("no_network")
def test_a_stop_after_the_local_done_write_is_retried_by_a_fresh_startup(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    real, stopped = DataRepo.publish, [True]

    def publish(self, path, message, until=None):
        if path.name == profile_share.PROFILE and stopped[0]:
            stopped[0] = False
            raise Stop
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)
    with pytest.raises(Stop):
        a.write_profile(Profile(entries={profile.POLL: confirmed("45")}, prefs_import="done"))
    assert profile_share.unpublished(a)  # the retry flag was durable before DONE was written
    assert b'"done"' not in remote_bytes(remote, SHARED_PROFILE)  # the remote profile never got DONE

    fresh = Store(tmp_path / "a-store", DataRepo(root), "shop-site")  # a new start on the same local store
    readiness.ready(fresh, tmp_path / "a-store", carry=True)
    assert not profile_share.unpublished(fresh)
    assert b'"done"' in remote_bytes(remote, SHARED_PROFILE)
