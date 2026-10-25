"""An ordinary profile save keeps the legacy import marker that a dedicated transition moved (R15, FND-05)."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store import prefs_import
from owlbear_delivery_next.state_store.store import Store


def clone_profile(remote: Path, tmp_path: Path) -> tuple[Store, Profile]:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(second), "shop-site")
    return fresh, fresh.read_profile()


@pytest.fixture
def local(tmp_path: Path, monkeypatch) -> Store:
    monkeypatch.setattr(config, "BASE", None)
    return Store(tmp_path / "store")


def test_a_stale_ordinary_save_keeps_a_pending_claim_and_its_basis(local):
    local.write_profile(Profile())
    stale = local.read_profile()
    assert local.mark_prefs_import("", "pending", "basis-1")[2] is True

    local.write_profile(stale)  # a delayed writer holding the pre-claim snapshot

    prof = local.read_profile()
    assert (prof.prefs_import, prof.prefs_basis) == ("pending", "basis-1")


def test_a_stale_ordinary_save_keeps_a_done_marker(local):
    local.write_profile(Profile())
    stale = local.read_profile()
    local.mark_prefs_import("", "pending", "basis-1")
    local.mark_prefs_import("pending", "done")

    local.write_profile(stale)

    prof = local.read_profile()
    assert (prof.prefs_import, prof.prefs_basis) == ("done", "")


def test_an_ordinary_save_keeps_its_other_new_facts(local):
    local.write_profile(Profile())
    stale = local.read_profile()
    local.mark_prefs_import("", "done")
    stale = stale.model_copy(update={"runtime": "vscode"})

    local.write_profile(stale)

    prof = local.read_profile()
    assert prof.prefs_import == "done"
    assert prof.runtime == "vscode"


def shared_store(root: Path, tmp_path: Path, name: str) -> Store:
    return Store(tmp_path / name, DataRepo(root), "shop-site")


def test_a_stale_writer_keeps_a_claim_another_store_made_on_the_shared_repo(shared_repo, tmp_path):
    root, remote = shared_repo
    late = shared_store(root, tmp_path, "late")
    late.write_profile(Profile())
    stale = late.read_profile()
    owner = shared_store(root, tmp_path, "owner")
    assert owner.mark_prefs_import("", "pending", "basis-1")[2] is True

    late.write_profile(stale)  # the late writer still holds the snapshot from before the claim

    _, got = clone_profile(remote, tmp_path)
    assert (got.prefs_import, got.prefs_basis) == ("pending", "basis-1")


def test_a_stale_writer_keeps_a_done_marker_another_store_made_on_the_shared_repo(shared_repo, tmp_path):
    root, remote = shared_repo
    late = shared_store(root, tmp_path, "late")
    late.write_profile(Profile())
    stale = late.read_profile()
    owner = shared_store(root, tmp_path, "owner")
    owner.mark_prefs_import("", "pending", "basis-1")
    owner.mark_prefs_import("pending", "done")

    late.write_profile(stale)

    _, got = clone_profile(remote, tmp_path)
    assert (got.prefs_import, got.prefs_basis) == ("done", "")


def test_a_stale_writer_after_an_owner_clear_does_not_reopen_the_claim(shared_repo, tmp_path):
    root, remote = shared_repo
    late = shared_store(root, tmp_path, "late")
    late.write_profile(Profile())
    stale = late.read_profile()
    owner = shared_store(root, tmp_path, "owner")
    owner.mark_prefs_import("", "done")

    late.write_profile(stale)

    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    prefs_import.run(fresh)  # the importer must not reclaim or refill after the owner's clear
    assert fresh.read_profile().prefs_import == "done"
    assert not fresh.config_path.exists()
