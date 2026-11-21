"""An ordinary profile save keeps the legacy import marker that a dedicated transition moved (R15, FND-05)."""

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.merge_records import CiBasis
from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry, ProjectCiConsent
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.settings import ci_consent, config, profile
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.profile_errors import Basis, SharedSyncError, TargetChangedError
from owlbear_delivery_next.state_store.store import Lock, Store, StoreError
from owlbear_delivery_next.workflow_steps import ci_basis


def clone_profile(remote: Path, tmp_path: Path) -> tuple[Store, Profile]:
    second = tmp_path / "fresh"
    subprocess.run(  # noqa: S603 - Fixture Git clone argv with remote/second operands; no shell.
        [resolve_git_executable(), "clone", "-q", str(remote), str(second)], check=True, capture_output=True
    )
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


def test_project_ci_authority_survives_stale_saves_but_not_explicit_revocation(shared_repo, tmp_path, monkeypatch):
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@example.com")
    root, remote = shared_repo
    late = shared_store(root, tmp_path, "late")
    raw = Profile(
        entries={
            profile.REPO: ProfileEntry(state="known", value="o/r"),
            profile.DEFAULT: ProfileEntry(state="known", value="main"),
            profile.DECLARED: ProfileEntry(state="unknown", value="none", evidence="jobs"),
            profile.REQUIRED: ProfileEntry(state="known", value="CI"),
        }
    )
    late.write_profile(raw)
    stale = late.read_profile()
    owner, old = clone_profile(remote, tmp_path / "owner")
    now = datetime(2026, 11, 21, tzinfo=UTC)
    consent = ProjectCiConsent(repository="o/r", target="main", at=now, basis=CiBasis(declared=(), required=("CI",)))
    approved = profile.confirm(old, profile.DECLARED, "none", now, consent=consent)
    assert owner.write_profile(approved, previous=old) == ""
    late.write_profile(profile.confirm(stale, "allow:install", "yes", now), previous=stale)
    current = late.read_profile()
    assert current.entries[profile.DECLARED].ci_consent == consent
    pinned = ci_consent.confirm_ci(current, "lint", now + timedelta(seconds=1), consent, ("lint",))
    late.write_profile(pinned, previous=current)
    refreshed = ci_basis.acquire(late, Lock("plain"), Change(slug="plain"), current)
    assert refreshed.entries[profile.DECLARED].ci_named == ("lint",)
    with pytest.raises(TargetChangedError, match="current profile"):
        late.write_profile(
            ci_consent.confirm_ci(current, "scan", now + timedelta(seconds=2), consent, ("scan",)),
            previous=current,
        )
    current = late.read_profile()
    with pytest.raises(TargetChangedError, match="current profile"):
        late.write_profile(profile.confirm(stale, profile.DECLARED, "lint", now), previous=stale)
    withdrawn = profile.withdraw(current, profile.DECLARED, raw.entries[profile.DECLARED])
    late.write_profile(withdrawn, previous=current)
    late.write_profile(approved)  # even an old writer without previous evidence cannot restore authority.
    assert late.read_profile().entries[profile.DECLARED].ci_consent.basis is None
    revoked = late.read_profile()
    source = _renewal_after_withdrawal(revoked.entries[profile.DECLARED].ci_consent.at)
    assert ci_basis.acquire(late, Lock("c1"), source, revoked).entries[profile.DECLARED].ci_consent.basis is None
    before = profile_share.path(late).read_bytes()
    current = late.read_profile()
    monkeypatch.setattr(DataRepo, "pull", lambda _self: "cannot fetch shared current authority")
    with pytest.raises(SharedSyncError, match="cannot fetch"):
        late.write_profile(current, previous=current)
    assert profile_share.path(late).read_bytes() == before


def _renewal_after_withdrawal(at):
    return Change.model_validate(
        {
            "slug": "c1",
            "names": {"target": "main"},
            "questions": [
                {
                    "id": "q1",
                    "step": "follow",
                    "text": "Required plus started?",
                    "cause": "gate:follow:declared-old",
                    "ci_basis": {"declared": [], "required": ["CI"]},
                    "answer": {"option": "yes", "at": at - timedelta(seconds=2)},
                },
                {
                    "id": "q2",
                    "step": "publish",
                    "text": "Require CI and scan?",
                    "cause": "gate:publish:rules-later",
                    "ci_basis": {"required": ["CI", "scan"]},
                    "answer": {"option": "yes", "at": at + timedelta(seconds=1)},
                },
            ],
        }
    )


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
