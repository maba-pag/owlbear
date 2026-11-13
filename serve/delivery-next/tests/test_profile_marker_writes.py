"""An ordinary profile save keeps the legacy import marker that a dedicated transition moved (R15, FND-05)."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.profile_errors import Basis, SharedSyncError
from owlbear_delivery_next.state_store.store import Store, StoreError


def clone_profile(remote: Path, tmp_path: Path) -> tuple[Store, Profile]:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(second), "shop-site")
    return fresh, fresh.read_profile()


@pytest.fixture
def local(tmp_path: Path, monkeypatch) -> Store:
    monkeypatch.setattr(config, "BASE", None)
    return Store(tmp_path / "store")


def test_a_stale_ordinary_save_keeps_the_current_pending_claim_then_done_marker(local):
    local.write_profile(Profile())
    stale = local.read_profile()
    assert local.mark_prefs_import("", "pending", "basis-1")[2] is True

    local.write_profile(stale)  # a delayed writer holding the pre-claim snapshot

    prof = local.read_profile()
    assert (prof.prefs_import, prof.prefs_basis) == ("pending", "basis-1")

    local.mark_prefs_import("pending", "done")

    local.write_profile(stale)

    prof = local.read_profile()
    assert (prof.prefs_import, prof.prefs_basis) == ("done", "")


def shared_store(root: Path, tmp_path: Path, name: str) -> Store:
    return Store(tmp_path / name, DataRepo(root), "shop-site")


def test_a_stale_writer_preserves_another_stores_pending_then_done_markers_on_the_remote(shared_repo, tmp_path):
    root, remote = shared_repo
    late = shared_store(root, tmp_path, "late")
    late.write_profile(Profile())
    stale = late.read_profile()
    owner = shared_store(root, tmp_path, "owner")
    assert owner.mark_prefs_import("", "pending", "basis-1")[2] is True

    late.write_profile(stale)  # the late writer still holds the snapshot from before the claim

    _, got = clone_profile(remote, tmp_path / "pending")
    assert (got.prefs_import, got.prefs_basis) == ("pending", "basis-1")

    owner.mark_prefs_import("pending", "done")

    late.write_profile(stale)

    _, got = clone_profile(remote, tmp_path / "done")
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


def test_a_second_store_cannot_publish_done_while_the_config_removal_is_unpublished(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    owner = shared_store(root, tmp_path, "owner")
    owner.write_profile(Profile())
    assert owner.mark_prefs_import("", "pending", "basis-1")[2] is True
    owner.config_path.parent.mkdir(parents=True, exist_ok=True)
    owner.config_path.write_text("{}")
    owner.config_path.unlink()  # the owner removes the config; the removal is not yet published
    real = DataRepo.publish

    def refuse_config(self, path, message, until=None):
        if path == owner.config_path:
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", refuse_config)
    second = shared_store(root, tmp_path, "second")  # another clone of the repo: its own flags, no unpublished mark
    assert second.mark_prefs_import("pending", "done")[1] == "remote refused"

    _, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "pending"  # the remote never sees done ahead of the config removal

    monkeypatch.setattr(DataRepo, "publish", real)
    assert second.retry_prefs_import() == ""
    fresh, got = clone_profile(remote, tmp_path / "again")
    assert got.prefs_import == "done"
    assert not fresh.config_path.exists()


@pytest.mark.parametrize("operation", ["pull", "layer", "claim", "retry"])
def test_profile_publication_refusals_keep_the_error_and_notes(shared_repo, tmp_path, monkeypatch, operation):
    root, _remote = shared_repo
    store = shared_store(root, tmp_path, "own")
    store.write_profile(Profile(prefs_import="done" if operation == "retry" else ""))
    error = DataRepoError("publication refused")
    error.add_note("the complete refusal context")

    failed = []

    def refuse(*_args, **_kwargs):
        if not failed:
            failed.append(True)
            raise error
        return ""

    if operation == "pull":
        monkeypatch.setattr(DataRepo, "pull", refuse)
        with pytest.raises(SharedSyncError) as caught:
            store.write_profile(Profile(), basis=Basis())
        text = str(caught.value)
    elif operation == "retry":
        (store.root / profile_share.UNPUBLISHED).touch()
        monkeypatch.setattr(profile_share, "publish_config_unlocked", lambda _store: "")
        monkeypatch.setattr(DataRepo, "publish", refuse)
        text = store.retry_prefs_import()
    else:
        monkeypatch.setattr(DataRepo, "publish", refuse)
        action = (
            (lambda: profile_share.publish_layer(store, store.config_path, "test settings", 0))
            if operation == "layer"
            else lambda: store.mark_prefs_import("", "pending", "basis", "claim")
        )
        with pytest.raises(StoreError) as caught:
            action()
        text = str(caught.value)
    assert "DataRepoError: publication refused\nthe complete refusal context" in text
    if operation == "claim":
        assert (store.root / profile_share.UNCONFIRMED).read_text() == "claim"
    if operation == "retry":
        assert profile_share.unpublished(store)


@pytest.mark.parametrize("step", ["fetch", "rev-parse", "ls-tree", "show"])
def test_a_pending_record_failure_reaches_the_real_completion_retry_whole(
    shared_repo, tmp_path, monkeypatch, whole_error, step
):
    root, _remote = shared_repo
    store = shared_store(root, tmp_path, "own")
    store.write_profile(Profile(prefs_import="done"))
    (store.root / profile_share.UNPUBLISHED).touch()
    saved = profile_share.path(store).read_bytes()
    real = DataRepo.git
    out, err = f"stdout {whole_error}", f"stderr {whole_error}"

    def git(self, *args, **kwargs):
        if args[0] == step:
            return subprocess.CompletedProcess(args, 128, out, err)
        if step == "show" and args[0] == "ls-tree":
            return subprocess.CompletedProcess(args, 0, "100644 blob pending\tshop-site/config.pending", "")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", git)
    with pytest.raises(StoreError) as caught:
        prefs_import.republish(store)
    assert f"stderr:\n{err}\nstdout:\n{out}" in str(caught.value)
    assert profile_share.CONFIG_WAITING in str(caught.value)
    assert profile_share.unpublished(store)
    assert profile_share.path(store).read_bytes() == saved
