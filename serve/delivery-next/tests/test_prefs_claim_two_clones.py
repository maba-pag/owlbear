"""Two real checkouts of one bare remote: a stale clone's ordinary fact save never takes over a published claim."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import prefs_import
from owlbear_delivery_next.state_store.store import Store, StoreError


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


def clone_as(remote: Path, tmp_path: Path, name: str) -> tuple[Store, Profile]:
    second = tmp_path / name
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        subprocess.run(["git", "-C", str(second), "config", key, value], check=True)  # noqa: S603, S607
    fresh = Store(tmp_path / f"{name}-store", DataRepo(second), "shop-site")
    return fresh, fresh.read_profile()


def crash_before_fill(monkeypatch) -> None:
    msg = "crash before the fill"

    def boom(*_args, **_kwargs):
        raise RuntimeError(msg)

    monkeypatch.setattr(prefs_import, "_fill", boom)


def test_a_stale_clones_ordinary_save_keeps_the_published_claim(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    b, stale = clone_as(remote, tmp_path, "b")  # B's copy predates A's claim: no claim, absent basis
    assert stale.prefs_claim is None

    with monkeypatch.context() as m:
        crash_before_fill(m)
        with pytest.raises(RuntimeError, match="crash before the fill"):
            prefs_import.run(a)
    published = a.read_profile()
    assert (published.prefs_import, published.prefs_basis) == ("pending", "absent")
    assert published.prefs_claim

    b.write_profile(stale.model_copy(update={"entries": {profile.POLL: confirmed("30")}}))  # stale ordinary fact save

    shared, got = clone_as(remote, tmp_path, "shared")
    assert (got.prefs_import, got.prefs_basis, got.prefs_claim) == ("pending", "absent", published.prefs_claim)
    assert got.entries[profile.POLL].value == "30"
    assert not shared.config_path.exists()
    assert not b.config_path.exists()


def test_absent_basis_owner_retry_stays_pending_after_a_stale_save(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    b, stale = clone_as(remote, tmp_path, "b")
    with monkeypatch.context() as m:
        crash_before_fill(m)
        with pytest.raises(RuntimeError, match="crash before the fill"):
            prefs_import.run(a)
    b.write_profile(stale.model_copy(update={"entries": {profile.POLL: confirmed("30")}}))

    with pytest.raises(StoreError, match="legacy preference import is incomplete"):
        prefs_import.run(b)  # B cannot take A's published claim, so it does not fill or mark done
    assert not b.config_path.exists()
    _, after_refusal = clone_as(remote, tmp_path, "after-refusal")
    assert after_refusal.prefs_import == "pending"
    assert after_refusal.prefs_claim == a.read_profile().prefs_claim

    with pytest.raises(StoreError, match="legacy preference import is incomplete"):
        prefs_import.run(a)  # an absent-basis claim that crashed before its fill never resumes blindly: owner review
    shared, got = clone_as(remote, tmp_path, "shared")
    assert (got.prefs_import, got.prefs_claim) == ("pending", a.read_profile().prefs_claim)
    assert not shared.config_path.exists()
    assert not a.config_path.exists()
