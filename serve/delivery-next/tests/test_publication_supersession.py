"""A clone's automatic config change waits behind another clone's pending owner intent; the DONE flag is durable."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import config_save, prefs_import, profile_share
from owlbear_delivery_next.state_store.pending_intents import pending_file, pending_intents
from owlbear_delivery_next.state_store.profile_share import CONFIG_WAITING
from owlbear_delivery_next.state_store.store import Store, StoreError

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
    """Return empty only for an absent path in a successfully read remote tree."""

    def read(*args):
        return subprocess.run(  # noqa: S603
            ["git", f"--git-dir={remote}", *args],  # noqa: S607
            check=True,
            capture_output=True,
        ).stdout

    if not read("ls-tree", "-z", "main", "--", rel):
        return b""
    return read("show", f"main:{rel}")


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


def widths(value: int):
    def change(cur: Layer) -> Layer:
        return cur.model_copy(update={"widths": [value]})

    return change


def in_place(cur: Layer) -> Layer:
    cur.widths = [1300]
    return cur


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
def broken_fetch(monkeypatch) -> list[str | None]:
    """The shared remote cannot be fetched while the switch is set: ``refused`` (a failed fetch) or ``raised``."""
    real, mode = DataRepo.git, [None]

    def git(self, *args, until=None):
        if mode[0] and args[:1] == ("fetch",):
            if mode[0] == "raised":
                msg = "simulated: remote unavailable"
                raise DataRepoError(msg)
            return subprocess.CompletedProcess(["git", *args], 1, "", "simulated: remote unreachable")
        return real(self, *args, until=until)

    monkeypatch.setattr(DataRepo, "git", git)
    return mode


@pytest.fixture
def no_network(monkeypatch) -> None:
    monkeypatch.setattr(config, "BASE", None)
    monkeypatch.setattr(profile, "detect", lambda _repo, _gh, previous: previous or Profile())
    monkeypatch.setattr(readiness, "check", lambda *_a, **_k: [])


@pytest.mark.usefixtures("no_network")
def test_an_automatic_config_change_waits_behind_another_clones_pending_owner_intent(
    shared_repo, tmp_path, refusing, config_publishes
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

    # B's automatic change is held before any write, even with a remote that would accept it: config_publishes
    # records every attempt before the remote answers, so a refused or raising remote adds nothing here
    refusing[0] = None
    config_publishes.clear()
    assert b.save(b.config_path, Layer, widths(1300), "automatic", owner=False) == CONFIG_WAITING
    for cached in (widths(1300), lambda cur: cur.model_copy(update={"widths": None}), in_place):
        assert b.update_config(cached, "automatic") == CONFIG_WAITING
    assert config_publishes == []
    assert not b.config_path.exists()
    assert remote_bytes(remote, SHARED_CONFIG) == before
    assert profile_share._shared_pending(b) == pending  # noqa: SLF001

    # An absent-local-config completion retry never publishes the config
    with b.shared.locked():
        assert profile_share.publish_config_unlocked(b) == CONFIG_WAITING
    assert config_publishes == []
    assert remote_bytes(remote, SHARED_CONFIG) == before
    assert profile_share._shared_pending(b) == pending  # noqa: SLF001

    assert b.save(b.config_path, Layer, widths(1600), "matching", owner=False) == ""
    assert profile_share._shared_pending(b) == ""  # noqa: SLF001
    assert b"1600" in remote_bytes(remote, SHARED_CONFIG)
    refusing[0] = "notice"
    assert b.save(b.config_path, Layer, widths(1650), "owner edit", owner=True)
    assert profile_share._shared_pending(b)  # noqa: SLF001
    fresh = clone(remote, tmp_path / "fresh", "fresh")
    assert pending_intents(fresh)
    refusing[0] = None
    assert b.save(b.config_path, Layer, widths(1700), "owner new value", owner=True) == ""
    assert profile_share._shared_pending(b) == ""  # noqa: SLF001
    assert b"1700" in remote_bytes(remote, SHARED_CONFIG)
    assert fresh.shared.pull() == ""
    assert pending_intents(fresh) == set()
    readiness.ready(fresh, tmp_path / "fresh-store", carry=True)
    assert fresh.read_config().widths == [1700]
    local, published = fresh.config_path.read_bytes(), remote_bytes(remote, SHARED_CONFIG)
    config_publishes.clear()
    for cached in (widths(1300), lambda cur: cur.model_copy(update={"widths": None}), in_place):
        assert fresh.update_config(cached, "automatic") == config_save.STALE
        assert fresh.config_path.read_bytes() == local
        assert remote_bytes(remote, SHARED_CONFIG) == published
        assert config_publishes == []


@pytest.mark.usefixtures("no_network")
@pytest.mark.parametrize("failure", ["returned", "raised", "stopped"])
def test_a_stop_after_the_local_done_write_is_retried_by_a_fresh_startup(shared_repo, tmp_path, monkeypatch, failure):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    if failure != "stopped":
        a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real = DataRepo.publish

    def publish(self, path, message, until=None):
        if path.name == profile_share.PROFILE and (failure == "stopped" or message.endswith("import done")):
            assert profile_share.unpublished(a)
            if failure != "stopped":
                assert b"45" in remote_bytes(remote, SHARED_CONFIG)
            if failure == "returned":
                return "remote refused"
            if failure == "raised":
                message = "remote unavailable"
                raise DataRepoError(message)
            raise Stop
        return real(self, path, message, until)

    with monkeypatch.context() as patch:
        patch.setattr(DataRepo, "publish", publish)

        def attempt():
            if failure == "stopped":
                a.write_profile(Profile(entries={profile.POLL: confirmed("45")}, prefs_import="done"))
            else:
                prefs_import.run(a)

        with pytest.raises(Stop if failure == "stopped" else StoreError):
            attempt()
    assert profile_share.unpublished(a)  # the retry flag was durable before DONE was written
    assert b'"done"' not in remote_bytes(remote, SHARED_PROFILE)  # the remote profile never got DONE

    fresh = Store(tmp_path / "a-store", DataRepo(root), "shop-site")  # a new start on the same local store
    if failure == "stopped":
        readiness.ready(fresh, tmp_path / "a-store", carry=True)
    else:
        prefs_import.run(fresh)
        assert fresh.read_config().prefs.ci_poll_seconds == 45
    assert not profile_share.unpublished(fresh)
    assert b'"done"' in remote_bytes(remote, SHARED_PROFILE)


@pytest.mark.usefixtures("no_network")
def test_a_done_marker_from_a_clone_without_the_flag_waits_for_the_refused_config_removal(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real = DataRepo.publish

    def refuse_done(self, path, message, until=None):
        if path == profile_share.path(a) and message.endswith("import done"):
            return "remote refused"
        return real(self, path, message, until)

    with monkeypatch.context() as patch:
        patch.setattr(DataRepo, "publish", refuse_done)
        with pytest.raises(StoreError):
            prefs_import.run(a)
    assert profile_share.unpublished(a)
    assert b"45" in remote_bytes(remote, SHARED_CONFIG)
    a.config_path.unlink()

    def refuse_removal(self, path, message, until=None):
        if path == a.config_path and message.endswith("project layer removed"):
            return "remote refused"
        return real(self, path, message, until)

    with monkeypatch.context() as patch:
        patch.setattr(DataRepo, "publish", refuse_removal)
        with pytest.raises(StoreError):
            prefs_import.republish(a)
    b = clone(remote, tmp_path / "b", "b")
    assert not profile_share.unpublished(b)
    assert b.read_profile().prefs_import == "pending"
    _, notice, applied = b.mark_prefs_import("pending", "done")
    assert applied
    assert notice
    assert b'"done"' not in remote_bytes(remote, SHARED_PROFILE)
    assert b"45" in remote_bytes(remote, SHARED_CONFIG)
    prefs_import.run(a)
    assert not profile_share.unpublished(a)
    fresh = clone(remote, tmp_path / "fresh", "fresh")
    assert fresh.read_profile().prefs_import == "done"
    assert not fresh.config_path.exists()
    assert remote_bytes(remote, SHARED_CONFIG) == b""


@pytest.mark.usefixtures("no_network")
@pytest.mark.parametrize("fault", ["refused", "raised"])
def test_an_unreadable_shared_pending_record_holds_every_config_write_visibly(  # noqa: PLR0913, PLR0917
    shared_repo, tmp_path, refusing, config_publishes, broken_fetch, fault
):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    refusing[0] = "notice"
    assert a.save(a.config_path, Layer, widths(1600), "owner edit", owner=True)  # pending, not published
    b = clone(remote, tmp_path / "b", "b")
    assert b.save(b.config_path, Layer, widths(1300), "setup value", owner=False) == CONFIG_WAITING  # healthy first
    b.config_path.write_text(widths(1300)(Layer()).model_dump_json(indent=1))  # B's own local value 1300
    pending = profile_share._shared_pending(b)  # noqa: SLF001
    assert pending
    local, before = b.config_path.read_bytes(), remote_bytes(remote, SHARED_CONFIG)

    # the remote's pending record cannot be read; a publish that somehow ran would now succeed and be visible
    refusing[0] = None
    broken_fetch[0] = fault
    config_publishes.clear()
    assert b.save(b.config_path, Layer, widths(1400), "automatic", owner=False)  # a visible refusal, not success
    assert config_publishes == []
    assert b.config_path.read_bytes() == local
    assert remote_bytes(remote, SHARED_CONFIG) == before
    assert profile_share._shared_pending(b) == pending  # noqa: SLF001

    # the completion retry keeps the config unpublished and says so; a removal is held the same way
    with b.shared.locked():
        notice = profile_share.publish_config_unlocked(b)
    assert notice.startswith(f"{CONFIG_WAITING}: DataRepoError:")
    assert "simulated: remote" in notice
    b.config_path.unlink()
    with b.shared.locked():
        assert profile_share.publish_config_unlocked(b) == notice
    assert config_publishes == []
    assert remote_bytes(remote, SHARED_CONFIG) == before
    assert profile_share._shared_pending(b) == pending  # noqa: SLF001

    # healthy control: once the remote is readable, the same unmatched change is held as CONFIG_WAITING
    broken_fetch[0] = None
    assert b.save(b.config_path, Layer, widths(1400), "automatic", owner=False) == CONFIG_WAITING
    assert config_publishes == []
    assert remote_bytes(remote, SHARED_CONFIG) == before


@pytest.mark.usefixtures("no_network")
def test_a_stale_automatic_payload_cannot_replace_a_newer_owner_value(
    shared_repo, tmp_path, refusing, config_publishes
):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    refusing[0] = "notice"
    assert a.save(a.config_path, Layer, widths(1600), "owner edit", owner=True)  # pending, not published
    b = clone(remote, tmp_path / "b", "b")
    basis = profile_share.config_digest(b.config_path)  # the config B's automatic payload is prepared against

    refusing[0] = None
    assert a.save(a.config_path, Layer, widths(1700), "owner new value", owner=True) == ""
    assert b.shared.pull() == ""  # B's checkout syncs the newer config, as its startup does
    readiness.ready(b, tmp_path / "b-store", carry=True)
    assert profile_share.config_digest(b.config_path) != basis

    config_publishes.clear()
    stale = config_save.Prepared(basis, widths(1300))
    assert b.save(b.config_path, Layer, stale, "automatic", owner=False) == config_save.STALE
    assert config_publishes == []
    assert b"1700" in remote_bytes(remote, SHARED_CONFIG)
    assert b"1300" not in remote_bytes(remote, SHARED_CONFIG)
    assert b"1700" in b.config_path.read_bytes()

    current = config_save.Prepared(profile_share.config_digest(b.config_path), widths(1800))
    assert b.save(b.config_path, Layer, current, "automatic", owner=False) == ""  # the current basis still publishes
    assert b"1800" in remote_bytes(remote, SHARED_CONFIG)


@pytest.mark.usefixtures("no_network")
def test_an_unknown_shared_pending_lookup_holds_the_automatic_change(shared_repo, tmp_path, refusing, config_publishes):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    refusing[0] = "notice"
    assert a.save(a.config_path, Layer, widths(1600), "owner edit", owner=True)  # pending on the remote
    b = clone(remote, tmp_path / "b", "b")
    pending_file(b).unlink()  # B's checkout has no local copy of the record
    subprocess.run(["git", "-C", str(b.shared.root), "branch", "--unset-upstream"], check=True)  # noqa: S603, S607
    before = remote_bytes(remote, SHARED_CONFIG)

    refusing[0] = None
    config_publishes.clear()
    result = b.save(b.config_path, Layer, widths(1300), "automatic", owner=False)
    assert result  # a refusal, not success
    assert config_publishes == []
    assert not b.config_path.exists()
    assert remote_bytes(remote, SHARED_CONFIG) == before


@pytest.mark.usefixtures("no_network")
def test_a_failed_shared_lookup_holds_the_automatic_change_without_a_local_copy(
    shared_repo, tmp_path, refusing, config_publishes, monkeypatch
):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    b = clone(remote, tmp_path / "b", "b")  # B's clean checkout is cloned before A's pending record exists
    real_pull, real_git, landed = DataRepo.pull, DataRepo.git, []

    def pull(self, until=None):
        pulled = real_pull(self, until)
        if self.root == b.shared.root and not landed:  # A's refused owner save lands right after B's catch-up
            refusing[0] = "notice"
            landed.append(a.save(a.config_path, Layer, widths(1600), "owner edit", owner=True))
            refusing[0] = None
            config_publishes.clear()
        return pulled

    def git(self, *args, until=None):
        if args[:1] == ("ls-tree",):
            assert not pending_file(b).exists()  # the lookup is B's only source of the record
            return subprocess.CompletedProcess(["git", *args], 128, "", "fatal: simulated lookup failure")
        return real_git(self, *args, until=until)

    monkeypatch.setattr(DataRepo, "pull", pull)
    monkeypatch.setattr(DataRepo, "git", git)
    assert b.save(b.config_path, Layer, widths(1300), "automatic", owner=False)  # refused: lookup is unknown
    assert landed[0]  # A's save was refused: its record is pending on the remote
    assert profile_share._shared_pending(a)  # noqa: SLF001
    assert config_publishes == []
    assert not b.config_path.exists()
    before = remote_bytes(remote, SHARED_CONFIG)
    assert b"1300" not in before

    # control: once the lookup works, the remote record is found and the same change is held as CONFIG_WAITING
    monkeypatch.setattr(DataRepo, "git", real_git)
    assert b.save(b.config_path, Layer, widths(1300), "automatic", owner=False) == CONFIG_WAITING
    assert config_publishes == []
    assert remote_bytes(remote, SHARED_CONFIG) == before


@pytest.mark.parametrize("kind", ["widths", "null", "in-place"])
def test_an_unshared_store_refuses_a_stale_automatic_write_after_an_owner_save(tmp_path, kind):
    store = Store(tmp_path / "store")
    assert store.update_config(config_save.Prepared(profile_share.config_digest(store.config_path), widths(1300))) == ""
    assert Store(store.root).read_config().widths == [1300]
    cached = config_save.Prepared(profile_share.config_digest(store.config_path), widths(1300))
    assert store.save(store.config_path, Layer, widths(1700), "owner", owner=True) == ""

    unprepared = {
        "widths": widths(1300),
        "null": lambda cur: cur.model_copy(update={"widths": None}),
        "in-place": in_place,
    }[kind]
    before = store.config_path.read_bytes()
    assert store.update_config(unprepared) == config_save.STALE
    assert store.update_config(cached) == config_save.STALE
    assert store.config_path.read_bytes() == before
    assert Store(store.root).read_config().widths == [1700]
