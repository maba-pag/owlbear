"""The legacy preference import recovers from owner reviews, stored values, and failed publications (R15, FND-01)."""

import contextlib
import inspect
import json
import os
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.inbox import IntentItem
from owlbear_delivery_next.change_contracts.models import Change, Exit, Question, Step, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.commands import setup
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import layers, prefs_import, profile_repair, profile_share, roles_move
from owlbear_delivery_next.state_store.store import RoleSourceError, Store, StoreError

AUTH = {"authorization": "Bearer " + "t"}
NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


class Host:
    wake = SimpleNamespace(set=lambda: None)
    maintenance = None
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def client(store: Store, global_path: Path, **kw: object) -> TestClient:
    store.global_path = global_path
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", **kw)


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


def stored(value: str, evidence: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=evidence)


@pytest.fixture
def local(tmp_path: Path, monkeypatch) -> Store:
    monkeypatch.setattr(config, "BASE", None)  # the test-only base layer would supply the unset values
    return Store(tmp_path / "store")


def clone_profile(remote: Path, tmp_path: Path, project: str = "shop-site") -> tuple[Store, Profile]:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(second), project)
    return fresh, fresh.read_profile()


# Finding 1: an explicit review or clear settles the import in the same save


def test_an_owner_clear_before_the_first_import_is_not_refilled_by_a_later_import(local, tmp_path):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    c = client(local, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    cleared = first["project"] | {"prefs": {"ci_poll_seconds": None}}
    body = {"rev": first["project_rev"], "layer": cleared, "prefs_reviewed": True}
    assert c.put("/api/next/config/project", json=body).status_code == 200
    assert local.read_config().prefs_imported is True

    prefs_import.run(local)  # a delayed first import must not resurrect the cleared legacy value
    assert local.read_config().prefs.ci_poll_seconds is None


def test_an_explicit_review_before_the_first_import_settles_it_so_a_deleted_config_stays_absent(local, tmp_path):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    c = client(local, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    body = {"rev": first["project_rev"], "layer": first["project"], "prefs_reviewed": True}
    assert c.put("/api/next/config/project", json=body).status_code == 200
    assert local.read_profile().prefs_import == "done"

    local.config_path.unlink()  # the owner deletes the config; a fresh claim must not resurrect the legacy value
    fresh = Store(tmp_path / "store")
    prefs_import.run(fresh)

    assert not fresh.config_path.exists()
    assert fresh.read_profile().prefs_import == "done"


def paused_after_claim(local: Store, monkeypatch, pause) -> Store:
    """An importer over the same root that runs *pause* once, after it read its own claim and before it fills."""
    winner = Store(local.root, local.shared, local.name)
    fill = winner.update_config

    def paused(change, what="project layer", on_written=None):
        monkeypatch.setattr(winner, "update_config", fill)
        pause()
        return fill(change, what, on_written)

    monkeypatch.setattr(winner, "update_config", paused)
    return winner


def test_a_claim_settled_and_deleted_while_paused_is_not_refilled_by_the_stale_importer(local, monkeypatch):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))

    def owner_settles() -> None:
        assert local.read_profile().prefs_import == "pending"  # the winner read its own claim first
        local.mark_prefs_import("pending", "done")  # Settings completes the import
        local.config_path.unlink(missing_ok=True)  # the owner deletes the project config

    prefs_import.run(paused_after_claim(local, monkeypatch, owner_settles))

    assert not local.config_path.exists()  # the stale fill never recreates the deleted config with legacy values
    assert local.read_profile().prefs_import == "done"


def test_a_claim_replaced_while_paused_is_not_filled_or_marked_done_by_the_stale_importer(local, monkeypatch):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))

    def newer_claim() -> None:
        local.mark_prefs_import("pending", "pending", profile_share.ABSENT, "newer")  # the only path that moves it
        local.config_path.unlink(missing_ok=True)

    prefs_import.run(paused_after_claim(local, monkeypatch, newer_claim))

    assert not local.config_path.exists()
    prof = local.read_profile()
    assert (prof.prefs_import, prof.prefs_claim) == ("pending", "newer")  # the newer claim is left to its own importer


def test_a_mark_and_an_owner_clear_during_an_unshared_claims_locked_write_wait_for_it(local, monkeypatch):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real_write = layers.atomic_write
    racers: list[threading.Thread] = []
    errors: list[BaseException] = []
    waiting: list[bool] = []

    def in_thread(action) -> threading.Thread:
        def body() -> None:
            try:
                action()
            except BaseException as exc:  # noqa: BLE001 - a worker failure must fail the test, not vanish
                errors.append(exc)

        thread = threading.Thread(target=body)
        thread.start()
        return thread

    def owner_clears() -> None:
        local.save(local.config_path, Layer, lambda cur: cur.model_copy(update={"prefs": Prefs()}), "owner", owner=True)

    def write_with_racers(target, content) -> None:
        if not racers:  # the winner's own write, under the config lock and the claim's private lock
            racers.extend(
                [
                    in_thread(lambda: Store(local.root).mark_prefs_import("pending", "done")),
                    in_thread(owner_clears),
                ]
            )
            for thread in racers:
                thread.join(0.3)
            waiting.extend(thread.is_alive() for thread in racers)
        real_write(target, content)

    monkeypatch.setattr(layers, "atomic_write", write_with_racers)
    prefs_import.run(local)
    for thread in racers:
        thread.join(10)

    assert waiting == [True, True]  # the mark and the clear waited for the write: neither landed inside it
    assert not any(thread.is_alive() for thread in racers)  # no deadlock: every racer finished
    assert errors == []
    assert local.read_config().prefs.ci_poll_seconds is None  # the owner's clear came after the import's write
    assert local.read_profile().prefs_import == "done"


def test_a_healthy_claim_still_fills_its_config_once(local):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))

    prefs_import.run(local)

    assert local.read_config().prefs.ci_poll_seconds == 45
    assert local.read_profile().prefs_import == "done"


def test_an_unreadable_profile_while_paused_is_a_visible_failure_that_writes_nothing(local, monkeypatch):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))

    def corrupt() -> None:
        profile_share.path(local).write_text("{ not json")

    with pytest.raises(StoreError, match="state of profile is unreadable"):
        prefs_import.run(paused_after_claim(local, monkeypatch, corrupt))

    assert not local.config_path.exists()


def test_an_owner_review_that_sets_a_value_keeps_it_when_the_import_runs_later(local, tmp_path):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    c = client(local, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    layer = first["project"] | {"prefs": {"ci_poll_seconds": 60}}
    body = {"rev": first["project_rev"], "layer": layer, "prefs_reviewed": True}
    assert c.put("/api/next/config/project", json=body).status_code == 200

    prefs_import.run(local)
    assert local.read_config().prefs.ci_poll_seconds == 60


def test_a_stale_page_save_cannot_lower_the_import_latch(local, tmp_path):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    prefs_import.run(local)  # the legacy value lands and the layer latches
    assert local.read_config().prefs.ci_poll_seconds == 45
    c = client(local, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    stale = first["project"] | {"prefs": {"ci_poll_seconds": None}, "prefs_imported": False}
    assert c.put("/api/next/config/project", json={"rev": first["project_rev"], "layer": stale}).status_code == 200

    assert local.read_config().prefs_imported is True
    prefs_import.run(local)
    assert local.read_config().prefs.ci_poll_seconds is None


# Finding 2: an unset ask-before-merge preference does not block Pause or Abandon


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for args in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "init"]):
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args]
        subprocess.run(git, cwd=root, check=True, capture_output=True)  # noqa: S603
    return root


def fold_intent(store: Store, intent: str):
    store.put_inbox("c1", IntentItem(at=NOW, intent=intent))
    with store.lock("c1") as lock:
        return store.fold(lock, "c1", NOW)


def test_an_abandon_folds_without_an_ask_before_merge_preference(repo, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    store = Store.open(repo)
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    change, _ = fold_intent(store, "abandon")
    assert change.intent.abandoned_at is not None


def test_a_pause_folds_without_an_ask_before_merge_preference_and_asks_nothing(repo, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    store = Store.open(repo)
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    change, _ = fold_intent(store, "pause")
    assert loop.open_question(change) is None


def test_an_explicit_no_still_closes_an_open_consent_question(repo, monkeypatch):
    monkeypatch.setattr(config, "BASE", None)
    store = Store.open(repo)
    notice = store.save(
        store.config_path,
        Layer,
        lambda cur: cur.model_copy(update={"prefs": Prefs(ask_before_merge=False)}),
        "owner",
        owner=True,
    )
    assert notice == ""
    assert store.read_config().prefs.ask_before_merge is False  # the owner's explicit No is the effective value
    asked = Question(step=StepKind.MERGE, text="merge?", cause=loop.CONSENT)
    result = StepResult(exit=Exit.ASK, question=asked)
    change = loop.apply(Change(slug="c1", step=Step(kind=StepKind.MERGE)), result, NOW)
    with store.lock("c1") as lock:
        store.write(lock, change)
    change, _ = fold_intent(store, "resume")
    assert change.questions[0].answer.option == loop.OBSOLETE


# Finding 3: stored legacy values are carried whatever their evidence says


def test_stored_default_and_allowed_legacy_values_are_carried_once(local):
    local.write_profile(
        Profile(
            entries={
                profile.POLL: stored("45", "default"),
                profile.METHOD: stored("squash", "allowed: merge, squash"),
            }
        )
    )
    prefs_import.run(local)
    got = local.read_config().prefs
    assert (got.ci_poll_seconds, got.merge_method) == (45, "squash")
    assert local.read_profile().prefs_import == "done"


def test_an_unknown_legacy_value_is_still_not_carried(local):
    local.write_profile(Profile(entries={profile.POLL: ProfileEntry(state="unknown", value="45", evidence="default")}))
    prefs_import.run(local)
    assert local.read_config().prefs.ci_poll_seconds is None


# Finding 4: a failed completion publication is retried, both automatically and from Settings


def refuse_completion_once(monkeypatch, store: Store) -> list[str]:
    """Refuse the first publication of the profile's completed marker only; the earlier steps publish."""
    real, refused = DataRepo.publish, []

    def publish(self, path, message, until=None):
        if path == profile_share.path(store) and message.endswith("import done") and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)
    return refused


def test_a_refused_completion_is_published_by_the_automatic_import_retry(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refused = refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError, match="completion was not published"):
        prefs_import.run(store)
    assert refused
    assert store.read_profile().prefs_import == "done"

    prefs_import.run(store)  # the automatic retry publishes the done marker after the current config
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45


def test_a_refused_completion_is_published_by_the_settings_settlement(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)

    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    body = {"rev": first["project_rev"], "layer": first["project"], "prefs_reviewed": True}
    saved = c.put("/api/next/config/project", json=body)
    assert saved.status_code == 200
    assert saved.json()["unpublished"] == ""
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45


# Finding 4: the owner's config deletion is published before a retried completion marker


def test_a_deleted_config_is_removed_before_the_automatic_retry_marks_done(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    store.config_path.unlink()  # the owner deletes the project config after the refused completion

    prefs_import.run(store)  # the automatic retry commits the removal, then publishes done
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert not fresh.config_path.exists()
    assert fresh.read_config().prefs is None
    assert not profile_share.unpublished(store)


def test_a_settings_retry_without_edits_keeps_a_deleted_config_absent(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    store.config_path.unlink()

    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    body = {"rev": first["project_rev"], "layer": first["project"], "prefs_reviewed": False}
    saved = c.put("/api/next/config/project", json=body)  # the page's retry: no edit, no review
    assert saved.status_code == 200
    assert saved.json()["unpublished"] == ""
    assert not store.config_path.exists()
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert not fresh.config_path.exists()


def test_an_explicit_settings_edit_after_the_deleted_config_recreates_it(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    store.config_path.unlink()

    c = client(store, tmp_path / "global" / "config.json", headers=AUTH)
    first = c.get("/api/next/config").json()
    layer = first["project"] | {"prefs": {"ci_poll_seconds": 60}}
    body = {"rev": first["project_rev"], "layer": layer, "prefs_reviewed": False}
    assert c.put("/api/next/config/project", json=body).status_code == 200
    assert store.config_path.exists()
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 60


def test_an_ordinary_profile_save_publishes_the_deleted_config_before_done(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    store.config_path.unlink()

    late = Profile(entries={profile.POLL: confirmed("45"), profile.WINDOW: confirmed("30")})
    assert store.write_profile(late) == ""  # a later ordinary save: the removal lands before done is exposed
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert got.entries[profile.WINDOW].value == "30"
    assert not fresh.config_path.exists()
    assert fresh.read_config().prefs is None
    assert not profile_share.unpublished(store)


def delete_config_before_the_shared_lock(monkeypatch, store: Store) -> list[str]:
    """Delete the project config as the retry takes the shared lock, after its existence check; returns the callers."""
    real_locked, callers = DataRepo.locked, []

    def locked(self, wait: float | None = None):
        under_publish = any(frame.function == "_publish_config" for frame in inspect.stack()[1:])
        if self == store.shared and under_publish and not callers:
            callers.append("_publish_config")
            store.config_path.unlink()
        return real_locked(self, wait)

    monkeypatch.setattr(DataRepo, "locked", locked)
    return callers


def remote_config_bytes(remote: Path, store: Store) -> bytes:
    relative = store.config_path.relative_to(store.shared.root).as_posix()
    shown = subprocess.run(  # noqa: S603 - the bare remote's branch as published
        ["git", "--git-dir", str(remote), "show", f"main:{relative}"],  # noqa: S607
        capture_output=True,
        check=False,
    )
    return shown.stdout


def test_a_config_deleted_before_the_retry_takes_the_shared_lock_stays_absent(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    callers = delete_config_before_the_shared_lock(monkeypatch, store)

    prefs_import.run(store)  # the retry publishes the owner's removal, never an empty config, then done
    assert callers == ["_publish_config"]
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert not fresh.config_path.exists()
    assert fresh.read_config().prefs is None
    assert not store.config_path.exists()
    assert not profile_share.unpublished(store)


def test_a_retry_with_a_healthy_config_publishes_its_unchanged_bytes(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    before = remote_config_bytes(remote, store)
    local = store.config_path.read_bytes()

    prefs_import.run(store)
    assert before == local
    assert remote_config_bytes(remote, store) == local  # the publication leaves the config as it was
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45


def test_an_unshared_retry_creates_no_config_once_the_owner_deleted_it(local):
    local.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    prefs_import.run(local)
    profile_share._unpublished(local, failed=True)  # noqa: SLF001 - a refused completion left the flag behind
    local.config_path.unlink()

    prefs_import.run(local)
    assert not local.config_path.exists()
    assert local.read_profile().prefs_import == "done"
    assert not profile_share.unpublished(local)


def test_a_refused_config_on_the_retry_keeps_the_flag_and_done_until_a_later_retry_publishes(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    refused = refuse_config_once(monkeypatch, store)

    with pytest.raises(StoreError, match="completion was not published"):
        prefs_import.run(store)
    assert refused
    assert profile_share.unpublished(store)
    assert store.read_profile().prefs_import == "done"
    assert store.read_config().prefs.ci_poll_seconds == 45

    prefs_import.run(store)
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45
    assert not profile_share.unpublished(store)


def refuse_config_once(monkeypatch, store: Store) -> list[str]:
    """Refuse the first publication of the project config only; the profile's own publications still land."""
    real, refused = DataRepo.publish, []

    def publish(self, path, message, until=None):
        if path == store.config_path and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)
    return refused


def test_a_refused_config_during_an_ordinary_save_keeps_new_facts_for_the_retry(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    store.config_path.unlink()  # the owner deletes the config; its removal is not yet published
    refused = refuse_config_once(monkeypatch, store)

    late = Profile(version=2, entries={profile.POLL: confirmed("45"), profile.WINDOW: confirmed("30")})
    assert store.write_profile(late)  # the config removal is refused, so the save reports it
    assert refused
    assert store.read_profile().entries[profile.WINDOW].value == "30"  # the new shared fact is kept locally
    (tmp_path / "before").mkdir()
    _, seen = clone_profile(remote, tmp_path / "before")
    assert seen.prefs_import == "pending"  # nothing new reached the remote while the removal was refused
    assert profile.WINDOW not in seen.entries

    retried = Store(tmp_path / "store", DataRepo(root), "shop-site")  # a new Store on the same clone
    prefs_import.run(retried)  # the retry removes the config, then publishes done with the new facts
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert got.version == 2
    assert got.entries[profile.WINDOW].value == "30"
    assert not fresh.config_path.exists()
    assert not profile_share.unpublished(retried)


# Setup repair of an unreadable saved profile keeps only its valid legacy guard


UNREADABLE = '{"format": 4, "prefs_import": "%s", "prefs_basis": "", "models": {}}'


def test_repair_keeps_a_done_import_guard_and_does_not_reimport(local: Store) -> None:
    local.root.mkdir(parents=True, exist_ok=True)
    (local.root / "profile.json").write_text(UNREADABLE % "done")
    local.write_profile(Profile(version=2), replace_unreadable=True)
    assert local.read_profile().prefs_import == "done"


def test_ordinary_save_refuses_an_unreadable_saved_profile(local: Store) -> None:
    local.root.mkdir(parents=True, exist_ok=True)
    (local.root / "profile.json").write_text(UNREADABLE % "done")
    before = (local.root / "profile.json").read_text()
    with pytest.raises(StoreError):
        local.write_profile(Profile(version=2))
    assert (local.root / "profile.json").read_text() == before


def test_repair_refuses_a_malformed_guard_and_keeps_the_file(local: Store) -> None:
    local.root.mkdir(parents=True, exist_ok=True)
    (local.root / "profile.json").write_text(UNREADABLE % "bogus")
    before = (local.root / "profile.json").read_text()
    with pytest.raises(StoreError):
        local.write_profile(Profile(version=2), replace_unreadable=True)
    assert (local.root / "profile.json").read_text() == before


def test_setup_repair_with_a_pending_guard_keeps_the_pending_marker(
    repo: Path, tmp_path_factory, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / "profile.json").write_text(UNREADABLE % "pending")
    with pytest.raises(StoreError, match="review the Merge and cleanup preferences"):
        setup.run(repo, [], yes=True, local_files="no")
    assert "cannot be read" in capsys.readouterr().out
    assert store.read_profile().prefs_import == "pending"
    assert not store.config_path.exists()


def test_repair_of_a_readable_profile_refuses_when_its_role_write_fails(
    repo: Path, tmp_path_factory, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(readiness, "check", lambda *_a: pytest.fail("the refusal must come before the probe"))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    raw = '{"format": 1, "roles": {"reviewer": {"model": "r-1", "effort": "max"}}}'
    (store.root / profile_share.PROFILE).write_text(raw)
    real_update = Store.update_config

    def refused_role_write(self, change, what: str = "", **kwargs):
        if what == "role overrides from the old profile":
            msg = "fetch failed"
            raise StoreError(msg)
        return real_update(self, change, what, **kwargs)

    monkeypatch.setattr(Store, "update_config", refused_role_write)
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("no profile write after a refusal"))
    with pytest.raises(StoreError, match="fetch failed"):
        setup.run(repo, [], yes=True, local_files="no")
    assert "cannot be read" not in capsys.readouterr().out
    assert (store.root / profile_share.PROFILE).read_text() == raw
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert not store.config_path.exists()


def test_declined_repair_of_an_unreadable_profile_leaves_every_file_unchanged(
    repo: Path, tmp_path_factory, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("no profile write before confirmation"))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    raw = '{"format": 1, "models": {}}'
    (store.root / profile_share.PROFILE).write_text(raw)
    assert setup.run(repo, [], yes=False, local_files="no", ask=lambda _q: "n") == 1
    out = capsys.readouterr().out
    assert "cannot be read" in out
    assert "discards the unreadable profile" in out
    assert (store.root / profile_share.PROFILE).read_text() == raw
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert not store.config_path.exists()


def test_a_confirmed_repair_of_an_unreadable_done_local_profile_keeps_the_guard(
    repo: Path, tmp_path_factory, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / profile_share.PROFILE).write_text(UNREADABLE % "done")
    assert setup.run(repo, [], yes=True, local_files="no") == 0
    saved = store.read_profile()
    assert saved.confirmed_at is not None
    assert saved.prefs_import == "done"
    assert profile_repair.pending(store) is None
    assert not (store.root / profile_repair.RECEIPT).exists()


def test_a_local_source_changed_while_the_owner_confirms_is_refused_without_overwrite(
    repo: Path, tmp_path_factory, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / profile_share.PROFILE).write_text(UNREADABLE % "done")
    newer = '{"format": 1, "roles": {"reviewer": {"model": "r-9", "effort": "max"}}}'

    def answer(_question: str) -> str:
        (store.root / profile_share.PROFILE).write_text(newer)
        return "y"

    assert setup.run(repo, [], yes=False, local_files="no", ask=answer) == 1
    assert (store.root / profile_share.PROFILE).read_text() == newer
    assert not store.config_path.exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert profile_repair.pending(store) is None


def shared_project(repo: Path, shared_repo, monkeypatch) -> Store:
    """The project *repo* in a shared repository (OWLBEAR_DATA), its clone's local folder created."""
    data, _remote = shared_repo
    monkeypatch.setenv("OWLBEAR_DATA", str(data))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    store = Store.open(repo)
    assert store.shared is not None
    store.root.mkdir(parents=True, exist_ok=True)
    return store


def test_shared_repair_declined_keeps_the_local_source_and_the_absent_target(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("no profile write before confirmation"))
    raw = '{"format": 1, "models": {}}'
    (store.root / profile_share.PROFILE).write_text(raw)
    assert not profile_share.path(store).exists()
    assert setup.run(repo, [], yes=False, local_files="no", ask=lambda _q: "n") == 1
    out = capsys.readouterr().out
    assert "cannot be read" in out
    assert "discards the unreadable profile" in out
    assert (store.root / profile_share.PROFILE).read_text() == raw
    assert not profile_share.path(store).exists()
    assert not store.config_path.exists()


def test_shared_repair_confirmed_keeps_a_valid_pending_guard_and_starts_fresh(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(UNREADABLE % "pending")
    with pytest.raises(StoreError, match="review the Merge and cleanup preferences"):
        setup.run(repo, [], yes=True, local_files="no")
    assert "discards the unreadable profile" in capsys.readouterr().out
    assert Store.open(repo).read_profile().prefs_import == "pending"
    assert not store.config_path.exists()
    assert (store.root / profile_share.PROFILE).exists()


BAD_EFFORT = '{"format": 1, "roles": {"reviewer": {"model": "r-1", "effort": "bogus"}}}'


def test_shared_repair_names_the_local_source_whose_roles_cannot_be_read(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(BAD_EFFORT)
    assert setup.run(repo, [], yes=False, local_files="no", ask=lambda _q: "n") == 1
    out = capsys.readouterr().out
    assert "cannot be read" in out
    assert str(store.root / profile_share.PROFILE) in out
    assert (store.root / profile_share.PROFILE).read_text() == BAD_EFFORT
    assert not profile_share.path(store).exists()
    assert not store.config_path.exists()


def test_shared_repair_refuses_when_the_local_source_changed_while_the_owner_answered(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    newer = '{"format": 1, "roles": {"planner": {"model": "p-2", "effort": "bogus"}}}'

    def changed_then_yes(_question: str) -> str:
        source.write_text(newer)
        return "y"

    assert setup.run(repo, [], yes=False, local_files="no", ask=changed_then_yes) == 1
    assert "changed while you answered; nothing was saved" in capsys.readouterr().out
    assert source.read_text() == newer
    assert not profile_share.path(store).exists()
    assert not store.config_path.exists()


def test_shared_repair_write_failure_keeps_the_source_and_retries_after_repair(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    raw = '{"format": 1, "models": {}}'
    source.write_text(raw)
    real_write = Store.write_profile
    failing = [True]

    def refused_write(self, *args, **kwargs):
        if failing[0]:
            msg = "fetch failed"
            raise StoreError(msg)
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(Store, "write_profile", refused_write)
    with pytest.raises(StoreError, match="fetch failed"):
        setup.run(repo, [], yes=True, local_files="no")
    assert source.read_text() == raw
    assert not profile_share.path(store).exists()
    assert not store.config_path.exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    failing[0] = False
    assert setup.run(repo, [], yes=True, local_files="no") == 0
    assert Store.open(repo).read_profile().confirmed_at is not None
    assert (store.root / profile_share.ROLES_MOVED).exists()


def test_shared_repair_refuses_a_malformed_guard_and_keeps_the_source_bytes(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    raw = UNREADABLE % "bogus"
    source.write_text(raw)
    with pytest.raises(StoreError):
        setup.run(repo, [], yes=True, local_files="no")
    assert source.read_text() == raw
    assert not profile_share.path(store).exists()
    assert not store.config_path.exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()


def test_shared_repair_success_lets_a_fresh_open_and_readiness_run_with_the_published_guard(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    raw = '{"format": 4, "prefs_import": "done", "prefs_basis": "basis-1", "prefs_claim": "nonce-1", "models": 5}'
    source.write_text(raw)
    assert setup.run(repo, [], yes=False, local_files="no", ask=lambda _q: "y") == 0
    assert "cannot be read" in capsys.readouterr().out
    real_run, carried_runs = prefs_import.run, []

    def spy_run(running):
        carried_runs.append(running)
        return real_run(running)

    monkeypatch.setattr(prefs_import, "run", spy_run)
    fresh = Store.open(repo)
    assert fresh.deferred_roles is None
    published = fresh.read_profile()
    assert published is not None
    assert published.confirmed_at is not None
    assert (published.prefs_import, published.prefs_basis, published.prefs_claim) == ("done", "basis-1", "nonce-1")
    assert source.read_text() == raw
    assert (store.root / profile_share.ROLES_MOVED).exists()
    assert not store.config_path.exists()
    # As the real detection, keep the previous profile and its guard.
    monkeypatch.setattr(setup.profile, "detect", lambda _repo, _gh, prev: prev)
    checks = readiness.ready(fresh, repo, carry=True)
    assert len(carried_runs) == 1  # the host start's legacy import ran, and it reported no failure
    assert [check for check in checks if not check.ok] == []
    after = Store.open(repo).read_profile()
    assert (after.prefs_import, after.prefs_basis, after.prefs_claim) == ("done", "basis-1", "nonce-1")
    assert not store.config_path.exists()


def test_shared_repair_of_a_readable_profile_refuses_when_its_role_write_fails_before_probe(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    raw = '{"format": 1, "roles": {"reviewer": {"model": "r-1", "effort": "max"}}}'
    source.write_text(raw)
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: pytest.fail("no probe before the role write succeeds"))
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("no profile write before the roles"))

    def refused_config(*_a: object, **_k: object) -> None:
        msg = "fetch failed"
        raise StoreError(msg)

    monkeypatch.setattr(Store, "update_config", refused_config)
    with pytest.raises(StoreError, match="fetch failed") as info:
        setup.run(repo, [], yes=True, local_files="no")
    assert not isinstance(info.value, RoleSourceError)
    assert "cannot be read" not in capsys.readouterr().out
    assert source.read_text() == raw
    assert not profile_share.path(store).exists()
    assert not store.config_path.exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()


GOOD_ROLES = '{"format": 1, "roles": {"reviewer": {"model": "r-2", "effort": "max"}}}'


def probed_repair(monkeypatch) -> list[str]:
    """Record every profile probe and profile write; a refused repair makes neither."""
    calls: list[str] = []

    def detect(*_a: object) -> Profile:
        calls.append("detect")
        return Profile(version=1)

    def write(_self, *_a: object, **_k: object) -> str:
        calls.append("write")
        return ""

    monkeypatch.setattr(setup.profile, "detect", detect)
    monkeypatch.setattr(Store, "write_profile", write)
    return calls


def test_shared_repair_source_fixed_during_the_first_read_is_inspected_again(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    calls = probed_repair(monkeypatch)
    real_read = Store.read_profile

    def fixed_then_read(self: Store) -> Profile | None:
        source.write_text(GOOD_ROLES)  # the bytes behind the captured refusal change before the digest is taken
        return real_read(self)

    monkeypatch.setattr(Store, "read_profile", fixed_then_read)
    try:
        code: object = setup.run(repo, [], yes=True, local_files="no")
    except StoreError as exc:
        code = exc
    assert "Profile v" not in capsys.readouterr().out
    assert calls == []
    assert source.read_text() == GOOD_ROLES
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert not profile_share.path(store).exists()
    assert not store.config_path.exists()
    assert code != 0


def test_shared_repair_source_changed_while_the_writer_lock_is_awaited_is_refused(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    real_writer = profile_share._writer  # noqa: SLF001 - the writer lock itself is what the probe sits in
    armed: list[bool] = []

    @contextlib.contextmanager
    def changed_at_entry(st: Store, *, create: bool = True):
        if armed:
            armed.clear()
            source.write_text(GOOD_ROLES)  # changed after the pre-save digest, before the writer lock is taken
        with real_writer(st, create=create):
            yield

    real_write = Store.write_profile

    def armed_write(self: Store, prof: Profile, **kwargs: object) -> str:
        armed.append(True)
        try:
            return real_write(self, prof, **kwargs)
        finally:
            armed.clear()

    monkeypatch.setattr(profile_share, "_writer", changed_at_entry)
    monkeypatch.setattr(Store, "write_profile", armed_write)
    try:
        code: object = setup.run(repo, [], yes=True, local_files="no")
    except StoreError as exc:
        code = exc
    assert "Profile v" not in capsys.readouterr().out
    assert source.read_text() == GOOD_ROLES
    assert not profile_share.path(store).exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert not store.config_path.exists()
    assert code != 0


def test_shared_repair_publication_refusal_is_visible_and_retires_nothing(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    notice = "saved, but not pushed: the shared repository refused the push"
    monkeypatch.setattr(DataRepo, "publish", lambda *_a, **_k: notice)
    try:
        code: object = setup.run(repo, [], yes=True, local_files="no")
    except StoreError as exc:
        code = exc
    out = capsys.readouterr().out
    assert "Profile v" not in out
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert source.read_text() == BAD_EFFORT
    assert code != 0


def shared_only_damaged(store: Store, raw: str) -> Path:
    """The shared profile, unreadable, with no profile in the clone: the only old bytes are the shared ones."""
    target = profile_share.path(store)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(raw)
    return target


def test_shared_only_damaged_target_is_repaired_with_its_guard_and_no_source_to_retire(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    shared_only_damaged(store, UNREADABLE % "done")
    assert not (store.root / profile_share.PROFILE).exists()
    assert setup.run(repo, [], yes=True, local_files="no") == 0
    assert "Profile v" in capsys.readouterr().out
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert Store.open(repo).read_profile().prefs_import == "done"


def test_shared_only_target_replaced_during_confirmation_keeps_the_newer_bytes(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    target = shared_only_damaged(store, UNREADABLE % "")
    newer = '{"format": 1, "roles": {"planner": {"model": "p-2", "effort": "max"}}}'

    def newer_then_yes(_question: str) -> str:
        target.write_text(newer)
        return "y"

    assert setup.run(repo, [], yes=False, local_files="no", ask=newer_then_yes) != 0
    assert "Profile v" not in capsys.readouterr().out
    assert target.read_text() == newer
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert not store.config_path.exists()


def test_shared_only_target_replaced_while_the_writer_lock_is_awaited_keeps_the_newer_bytes(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    target = shared_only_damaged(store, UNREADABLE % "")
    newer = '{"format": 1, "roles": {"planner": {"model": "p-2", "effort": "max"}}}'
    real_writer = profile_share._writer  # noqa: SLF001 - the writer lock itself is what the probe sits in
    armed: list[bool] = []

    @contextlib.contextmanager
    def changed_at_entry(st: Store, *, create: bool = True):
        if armed:
            armed.clear()
            target.write_text(newer)  # the shared target changes while the approval waits for the writer lock
        with real_writer(st, create=create):
            yield

    real_write = Store.write_profile

    def armed_write(self: Store, prof: Profile, **kwargs: object) -> str:
        armed.append(True)
        try:
            return real_write(self, prof, **kwargs)
        finally:
            armed.clear()

    monkeypatch.setattr(profile_share, "_writer", changed_at_entry)
    monkeypatch.setattr(Store, "write_profile", armed_write)
    assert setup.run(repo, [], yes=True, local_files="no") != 0
    assert "Profile v" not in capsys.readouterr().out
    assert target.read_text() == newer
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert not store.config_path.exists()


def test_shared_only_repair_declined_writes_nothing(repo: Path, shared_repo, monkeypatch) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    raw = UNREADABLE % ""
    target = shared_only_damaged(store, raw)
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("no profile write before confirmation"))
    assert setup.run(repo, [], yes=False, local_files="no", ask=lambda _q: "n") == 1
    assert target.read_text() == raw
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert not store.config_path.exists()


def test_shared_only_target_readable_before_observation_is_not_treated_as_the_approved_bad_source(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    target = shared_only_damaged(store, UNREADABLE % "")

    def healed_then_unreadable(_self: Store) -> Profile:
        target.write_text(GOOD_ROLES)  # the open-time error is stale: the shared file reads by the time it is observed
        msg = "the saved profile cannot be read"
        raise StoreError(msg)

    monkeypatch.setattr(Store, "read_profile", healed_then_unreadable)
    with pytest.raises(StoreError, match="can be read now"):
        setup.run(repo, [], yes=True, local_files="no")
    assert target.read_text() == GOOD_ROLES
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert not store.config_path.exists()


def test_shared_only_sync_failure_keeps_the_approved_repair_and_resumes_without_reconfirming(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    raw = UNREADABLE % ""
    target = shared_only_damaged(store, raw)
    with monkeypatch.context() as offline:
        offline.setattr(DataRepo, "pull", lambda *_a, **_k: "the shared repository could not be reached")
        assert setup.run(repo, [], yes=True, local_files="no") == 1
    receipt = json.loads((store.root / profile_repair.RECEIPT).read_text())
    assert receipt["source"] == profile_share.ABSENT
    assert target.read_text() == raw
    capsys.readouterr()
    assert setup.run(repo, [], yes=False, local_files="no", ask=lambda _q: pytest.fail("no reconfirmation")) == 0
    assert "Profile v" in capsys.readouterr().out
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()


PRIVATE_READABLE = GOOD_ROLES


def test_shared_damaged_target_is_repaired_while_the_readable_private_profile_stays_byte_for_byte(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(PRIVATE_READABLE)
    shared_only_damaged(store, UNREADABLE % "")
    assert setup.run(repo, [], yes=True, local_files="no") == 0
    assert (store.root / profile_share.PROFILE).read_text() == PRIVATE_READABLE
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert "r-2" in store.config_path.read_text()  # the ordinary open imports the readable private roles once
    assert (store.root / profile_share.ROLES_MOVED).exists()
    assert profile_share.path(store).exists()
    assert "prefs_import" in profile_share.path(store).read_text()


def test_shared_damaged_target_replaced_during_confirmation_keeps_the_owner_bytes_with_readable_private(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(PRIVATE_READABLE)
    target = shared_only_damaged(store, UNREADABLE % "")
    newer = '{"format": 1, "roles": {"planner": {"model": "p-2", "effort": "max"}}}'

    def newer_then_yes(_question: str) -> str:
        target.write_text(newer)
        return "y"

    assert setup.run(repo, [], yes=False, local_files="no", ask=newer_then_yes) != 0
    assert target.read_text() == newer
    assert (store.root / profile_share.PROFILE).read_text() == PRIVATE_READABLE
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert "r-2" in store.config_path.read_text()


def test_shared_damaged_target_replaced_while_the_writer_lock_is_awaited_keeps_the_owner_bytes_with_readable_private(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(PRIVATE_READABLE)
    target = shared_only_damaged(store, UNREADABLE % "")
    newer = '{"format": 1, "roles": {"planner": {"model": "p-2", "effort": "max"}}}'
    real_writer = profile_share._writer  # noqa: SLF001 - the writer lock is where the race is injected
    armed: list[bool] = []

    @contextlib.contextmanager
    def changed_at_entry(st: Store, *, create: bool = True):
        if armed:
            armed.clear()
            target.write_text(newer)
        with real_writer(st, create=create):
            yield

    real_write = Store.write_profile

    def armed_write(self: Store, prof: Profile, **kwargs: object) -> str:
        armed.append(True)
        try:
            return real_write(self, prof, **kwargs)
        finally:
            armed.clear()

    monkeypatch.setattr(profile_share, "_writer", changed_at_entry)
    monkeypatch.setattr(Store, "write_profile", armed_write)
    assert setup.run(repo, [], yes=True, local_files="no") != 0
    assert target.read_text() == newer
    assert (store.root / profile_share.PROFILE).read_text() == PRIVATE_READABLE
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert "r-2" in store.config_path.read_text()


def test_shared_damaged_target_repair_declined_with_readable_private_writes_nothing(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(PRIVATE_READABLE)
    raw = UNREADABLE % ""
    target = shared_only_damaged(store, raw)
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("no profile write before confirmation"))
    assert setup.run(repo, [], yes=False, local_files="no", ask=lambda _q: "n") == 1
    assert target.read_text() == raw
    assert (store.root / profile_share.PROFILE).read_text() == PRIVATE_READABLE
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert "r-2" in store.config_path.read_text()


def readable_private_repaired(repo: Path, shared_repo, monkeypatch, before_snapshot):
    """A readable private profile, imported by the ordinary open, then a confirmed shared repair.

    *before_snapshot* runs once the repair has published, right before its final observation of the old profile.
    """
    store = shared_project(repo, shared_repo, monkeypatch)
    private, marker = store.root / profile_share.PROFILE, store.root / profile_share.ROLES_MOVED
    # The damaged target is committed and pushed first, so it exists while the ordinary open imports the roles.
    target = shared_only_damaged(store, UNREADABLE % "")
    subprocess.run(["git", "-C", str(target.parent), "add", "--", target.name], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(target.parent), "commit", "-q", "-m", "damaged target"], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(target.parent), "push", "-q", "origin", "HEAD"], check=True)  # noqa: S603, S607
    private.write_text(PRIVATE_READABLE)
    assert private.read_bytes() == PRIVATE_READABLE.encode()
    Store.open(repo)
    assert private.read_bytes() == PRIVATE_READABLE.encode()
    assert marker.exists()
    config_before, marker_before = store.config_path.read_bytes(), marker.read_bytes()
    armed: list[bool] = []
    hits: list[Path] = []
    real_write, real_snapshot = Store.write_profile, roles_move.snapshot

    def armed_write(self: Store, prof: Profile, **kwargs: object) -> str:
        try:
            return real_write(self, prof, **kwargs)
        finally:
            armed.append(True)

    def observed(old: Path):
        if armed and old == private:
            armed.clear()
            hits.append(old)
            before_snapshot(private)
        return real_snapshot(old)

    monkeypatch.setattr(Store, "write_profile", armed_write)
    monkeypatch.setattr(roles_move, "snapshot", observed)
    return store, private, marker, config_before, marker_before, hits


PUBLISHED_PREFS = {
    "merge_method": None,
    "delete_remote_branch": None,
    "ci_poll_seconds": None,
    "ci_start_window_seconds": None,
    "ask_before_merge": None,
}


def test_readable_private_repair_keeps_its_config_marker_and_source_bytes(repo: Path, shared_repo, monkeypatch) -> None:
    store, private, marker, config_before, marker_before, hits = readable_private_repaired(
        repo, shared_repo, monkeypatch, lambda _p: None
    )
    assert setup.run(repo, [], yes=True, local_files="no") == 0
    assert len(hits) == 1
    assert private.read_bytes() == PRIVATE_READABLE.encode()
    before, after = json.loads(config_before), json.loads(store.config_path.read_bytes())
    assert after.pop("prefs_imported") is True
    assert after.pop("prefs") == PUBLISHED_PREFS
    assert before.pop("prefs_imported") is False
    assert before.pop("prefs") is None
    assert after == before
    assert marker.read_bytes() == marker_before
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert "prefs_import" in profile_share.path(store).read_text()


OTHER_READABLE = '{"format": 1, "roles": {"planner": {"model": "p-2", "effort": "max"}}}'


@pytest.mark.parametrize("raw", [OTHER_READABLE, UNREADABLE % ""], ids=["readable-other", "unreadable"])
def test_old_source_replaced_before_final_observation_is_never_retired(
    repo: Path, shared_repo, monkeypatch, capsys, raw: str
) -> None:
    store, private, marker, config_before, marker_before, hits = readable_private_repaired(
        repo, shared_repo, monkeypatch, lambda p: p.write_text(raw)
    )
    assert setup.run(repo, [], yes=True, local_files="no") != 0
    assert len(hits) == 1
    assert "run setup again to review it" in capsys.readouterr().out
    assert private.read_text() == raw
    assert store.config_path.read_bytes() == config_before
    assert marker.read_bytes() == marker_before
    assert (store.root / profile_repair.RECEIPT).exists()


def test_old_source_unreadable_at_final_observation_keeps_the_approved_repair(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    real_read = Path.read_bytes

    def deny_next_private_read(private: Path) -> None:
        def denied(self: Path) -> bytes:
            if self != private:
                return real_read(self)
            monkeypatch.setattr(Path, "read_bytes", real_read)
            raise PermissionError(13, "Permission denied", str(self))

        monkeypatch.setattr(Path, "read_bytes", denied)

    store, private, marker, config_before, marker_before, hits = readable_private_repaired(
        repo, shared_repo, monkeypatch, deny_next_private_read
    )
    assert setup.run(repo, [], yes=True, local_files="no") != 0
    assert len(hits) == 1
    assert "could not read the old profile" in capsys.readouterr().out
    assert store.config_path.read_bytes() == config_before
    assert private.read_bytes() == PRIVATE_READABLE.encode()
    assert marker.read_bytes() == marker_before
    assert (store.root / profile_repair.RECEIPT).exists()


def test_bad_local_overlay_never_replaces_a_readable_shared_profile(repo: Path, shared_repo, monkeypatch) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(PRIVATE_READABLE)
    shared = profile_share.path(store)
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text(GOOD_ROLES)
    overlay = store.root / profile_share.LOCAL
    overlay.write_text("{not json")
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("a readable profile is never replaced"))
    with pytest.raises(StoreError, match="reads now"):
        setup.run(repo, [], yes=True, local_files="no")
    assert shared.read_text() == GOOD_ROLES
    assert (store.root / profile_share.PROFILE).read_text() == PRIVATE_READABLE
    assert overlay.read_text() == "{not json"
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert "r-2" in store.config_path.read_text()


def test_bad_local_overlay_never_replaces_a_readable_unshared_profile(
    repo: Path, tmp_path_factory, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path_factory.mktemp("home")))
    monkeypatch.setattr(readiness, "check", lambda *_a: [])
    monkeypatch.setattr(setup.profile, "detect", lambda *_a: Profile(version=1))
    store = Store.open(repo)
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / profile_share.PROFILE).write_text(PRIVATE_READABLE)
    overlay = store.root / profile_share.LOCAL
    overlay.write_text("{not json")
    monkeypatch.setattr(Store, "write_profile", lambda *_a, **_k: pytest.fail("a readable profile is never replaced"))
    with pytest.raises(StoreError, match="reads now"):
        setup.run(repo, [], yes=True, local_files="no")
    assert (store.root / profile_share.PROFILE).read_text() == PRIVATE_READABLE
    assert overlay.read_text() == "{not json"
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert "r-2" in store.config_path.read_text()


def refuse_publish(monkeypatch) -> None:
    notice = "saved, but not pushed: the shared repository refused the push"
    monkeypatch.setattr(DataRepo, "publish", lambda *_a, **_k: notice)


def test_a_refused_repair_publication_stays_pending_and_the_next_setup_publishes_it(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    with monkeypatch.context() as refused:
        refuse_publish(refused)
        assert setup.run(repo, [], yes=True, local_files="no") == 1
    assert (store.root / profile_repair.RECEIPT).exists()
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    capsys.readouterr()
    assert setup.run(repo, [], yes=False, local_files="no") == 0  # the staged replacement is published, not asked again
    assert "Profile v" in capsys.readouterr().out
    assert not (store.root / profile_repair.RECEIPT).exists()
    assert (store.root / profile_share.ROLES_MOVED).exists()


def test_a_refused_repair_is_not_resumed_once_the_old_profile_changed(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    config_before = store.config_path.read_bytes() if store.config_path.exists() else None
    with monkeypatch.context() as refused:
        refuse_publish(refused)
        assert setup.run(repo, [], yes=True, local_files="no") == 1
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert (store.config_path.read_bytes() if store.config_path.exists() else None) == config_before
    source.write_text(GOOD_ROLES)
    capsys.readouterr()
    assert setup.run(repo, [], yes=True, local_files="no") == 1
    out = capsys.readouterr().out
    assert "changed while you answered" in out
    assert "Profile v" not in out
    assert source.read_text() == GOOD_ROLES
    assert not (store.root / profile_repair.RECEIPT).exists()
    # The second open applies the now-valid old roles through the ordinary move (fills only empty settings),
    # atomically with its receipt; the repair itself is refused and never reviewed these roles.
    merged = store.read_config()
    assert merged.roles_moved is True
    assert merged.agents["reviewer"].model == "r-2"
    assert merged.agents["reviewer"].effort == "max"
    assert (store.root / profile_share.ROLES_MOVED).exists()


def refused_repair_receipt(repo: Path, shared_repo, monkeypatch, capsys) -> tuple[Store, Path]:
    """A shared repair whose publication was refused: the replacement stays staged in the private receipt."""
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    with monkeypatch.context() as refused:
        refuse_publish(refused)
        assert setup.run(repo, [], yes=True, local_files="no") == 1
    capsys.readouterr()
    return store, store.root / profile_repair.RECEIPT


def test_a_newer_shared_profile_is_not_overwritten_by_a_staged_repair(
    repo: Path, shared_repo, monkeypatch, capsys, tmp_path
) -> None:
    _data, remote = shared_repo
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    with monkeypatch.context() as refused:
        refuse_publish(refused)
        assert setup.run(repo, [], yes=True, local_files="no") == 1
    capsys.readouterr()
    assert (store.root / profile_repair.RECEIPT).exists()
    owner, _ = clone_as(remote, tmp_path, "owner", store.name)
    newer = Profile(version=3, confirmed_at=NOW)  # distinct from the staged replacement, which is version 2
    owner.write_profile(newer)  # a newer shared profile lands while the local source is unchanged
    assert source.read_text() == BAD_EFFORT
    code: object
    try:
        code = setup.run(repo, [], yes=False, local_files="no")
    except StoreError as exc:
        code = exc
    out = capsys.readouterr().out
    assert str(store.root / profile_repair.RECEIPT) in out
    assert "remove" in out
    assert (store.root / profile_repair.RECEIPT).exists()
    _, landed = clone_profile(remote, tmp_path / "after", store.name)
    assert landed == newer
    assert code == 1


def test_a_receipt_with_an_unknown_format_is_refused_before_any_publication(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store, receipt = refused_repair_receipt(repo, shared_repo, monkeypatch, capsys)
    data = json.loads(receipt.read_text())
    data["profile"]["format"] = 999
    receipt.write_text(json.dumps(data))
    before = receipt.read_bytes()
    source_before = (store.root / profile_share.PROFILE).read_bytes()
    target_before = profile_share.path(store).read_bytes()  # the refused publication already saved it locally
    calls = probed_repair(monkeypatch)
    with pytest.raises(StoreError, match="pending profile repair"):
        setup.run(repo, [], yes=False, local_files="no")
    assert calls == []
    assert receipt.read_bytes() == before
    assert (store.root / profile_share.PROFILE).read_bytes() == source_before
    assert profile_share.path(store).read_bytes() == target_before


def test_a_receipt_without_a_confirmation_time_is_refused_before_any_publication(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store, receipt = refused_repair_receipt(repo, shared_repo, monkeypatch, capsys)
    data = json.loads(receipt.read_text())
    data["profile"]["confirmed_at"] = None
    receipt.write_text(json.dumps(data))
    before = receipt.read_bytes()
    source_before = (store.root / profile_share.PROFILE).read_bytes()
    target_before = profile_share.path(store).read_bytes()  # the refused publication already saved it locally
    calls = probed_repair(monkeypatch)
    with pytest.raises(StoreError, match="pending profile repair"):
        setup.run(repo, [], yes=False, local_files="no")
    assert calls == []
    assert receipt.read_bytes() == before
    assert (store.root / profile_share.PROFILE).read_bytes() == source_before
    assert profile_share.path(store).read_bytes() == target_before


def test_a_staged_repair_cannot_publish_into_a_different_shared_repository(
    repo: Path, shared_repo, monkeypatch, capsys, tmp_path
) -> None:
    _store, receipt = refused_repair_receipt(repo, shared_repo, monkeypatch, capsys)
    other_remote = tmp_path / "other.git"
    other_root = tmp_path / "other-data"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(other_remote)], check=True)  # noqa: S603, S607
    subprocess.run(["git", "clone", "-q", str(other_remote), str(other_root)], check=True)  # noqa: S603, S607
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        subprocess.run(["git", "-C", str(other_root), "config", key, value], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(other_root), "commit", "-q", "--allow-empty", "-m", "start"], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(other_root), "push", "-q", "-u", "origin", "HEAD"], check=True)  # noqa: S603, S607
    monkeypatch.setenv("OWLBEAR_DATA", str(other_root))
    (tmp_path / "before").mkdir()
    (tmp_path / "after").mkdir()
    _, before_landed = clone_profile(other_remote, tmp_path / "before")
    assert before_landed is None
    before = receipt.read_bytes()
    code: object
    try:
        code = setup.run(repo, [], yes=False, local_files="no")
    except StoreError as exc:
        code = exc
    _, landed = clone_profile(other_remote, tmp_path / "after")
    assert landed is None
    assert receipt.read_bytes() == before
    assert isinstance(code, StoreError)
    assert "another shared repository" in str(code)
    assert str(receipt) in str(code)


def test_a_stale_repair_receipt_does_not_clear_a_newer_pending_receipt(repo: Path, shared_repo, monkeypatch) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    digest = profile_share.config_digest(source)
    first = profile_repair.stage(store, Profile(version=1, confirmed_at=NOW), digest, "absent")
    receipt = store.root / profile_repair.RECEIPT
    newer = profile_repair.Receipt(
        format=1,
        id="b" * 32,
        scope=profile_repair.scope(store),
        source=digest,
        target="absent",
        profile=Profile(version=2, confirmed_at=NOW),
    )

    def replace_then_fail(_self: Store, _prof: Profile, **_kwargs: object) -> str:
        receipt.write_text(newer.model_dump_json())  # a newer confirmed replacement is staged while this one fails
        msg = "the old profile changed"
        raise profile_share.SourceChangedError(msg)

    monkeypatch.setattr(Store, "write_profile", replace_then_fail)
    with pytest.raises(profile_share.SourceChangedError):
        profile_repair.publish(store, first, resumed=False)
    assert receipt.read_text() == newer.model_dump_json()


def stage_confirmed(store: Store, version: int = 1) -> profile_repair.Receipt:
    """Stage a confirmed replacement against the current old profile and the absent shared profile."""
    digest = profile_share.config_digest(store.root / profile_share.PROFILE)
    return profile_repair.stage(store, Profile(version=version, confirmed_at=NOW), digest, "absent")


def test_a_failed_sync_keeps_the_confirmed_replacement_and_a_healthy_retry_publishes_it(
    repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    receipt = store.root / profile_repair.RECEIPT
    with monkeypatch.context() as offline:

        def pull_fails(*_args: object) -> str:
            msg = "fetch failed"
            raise DataRepoError(msg)

        offline.setattr(DataRepo, "pull", pull_fails)
        assert setup.run(repo, [], yes=True, local_files="no") == 1
    out = capsys.readouterr().out
    assert "could not be synced" in out
    assert str(receipt) in out
    assert "run setup again" in out
    assert receipt.exists()
    assert source.read_text() == BAD_EFFORT
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert setup.run(repo, [], yes=False, local_files="no") == 0  # healthy again: published without a new ask
    assert "Profile v" in capsys.readouterr().out
    assert not receipt.exists()
    assert (store.root / profile_share.ROLES_MOVED).exists()


def format_4_profile(**changes: object) -> dict:
    """A confirmed profile as format 4 wrote it, with the per-project runtime switch its older build kept."""
    raw = Profile(version=1, confirmed_at=NOW, prefs_import="done").model_dump(mode="json")
    return raw | {"format": 4, "runtime": "vscode"} | changes


def pending_receipt(store: Store, profile: dict) -> Path:
    """A pending repair receipt as an older build staged it: its embedded profile as given, unmigrated."""
    digest = profile_share.config_digest(store.root / profile_share.PROFILE)
    receipt = store.root / profile_repair.RECEIPT
    body = {
        "format": 1, "id": "a" * 32, "scope": profile_repair.scope(store), "source": digest, "target": "absent",
        "profile": profile,
    }  # fmt: skip
    receipt.write_text(json.dumps(body))
    return receipt


def test_a_pending_repair_receipt_written_at_format_4_with_runtime_resumes(
    repo: Path, shared_repo, monkeypatch
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(BAD_EFFORT)
    receipt = pending_receipt(store, format_4_profile())

    assert setup.run(repo, [], yes=False, local_files="no") == 0  # the owner's confirmation stands: no new ask
    assert not receipt.exists()
    published = Store.open(repo).read_profile()
    assert (published.format, published.version, published.confirmed_at) == (profile_repair.PROFILE_FORMAT, 1, NOW)
    assert (published.prefs_import, "runtime" in published.model_dump()) == ("done", False)


@pytest.mark.parametrize(
    "raw",
    [
        format_4_profile(format=6),
        format_4_profile(colour="red"),
        format_4_profile(confirmed_at=None),
        {k: v for k, v in format_4_profile().items() if k != "format"},
    ],
    ids=["future-format", "unknown-field", "unconfirmed", "no-format"],
)
def test_a_pending_repair_receipt_that_is_future_or_malformed_is_still_refused_and_kept(
    repo: Path, shared_repo, monkeypatch, raw: dict
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    (store.root / profile_share.PROFILE).write_text(BAD_EFFORT)
    receipt = pending_receipt(store, raw)
    before = receipt.read_bytes()

    with pytest.raises(StoreError, match="malformed or from another version"):
        profile_repair.pending(store)
    assert receipt.read_bytes() == before


def test_a_receipt_replaced_before_publication_refuses_the_older_one_before_any_write(
    repo: Path, shared_repo, monkeypatch, tmp_path
) -> None:
    _data, remote = shared_repo
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    first = stage_confirmed(store, version=1)
    receipt = store.root / profile_repair.RECEIPT
    newer = profile_repair.Receipt(
        format=1,
        id="b" * 32,
        scope=profile_repair.scope(store),
        source=first.source,
        target="absent",
        profile=Profile(version=2, confirmed_at=NOW),
    )
    receipt.write_text(newer.model_dump_json())
    before = receipt.read_bytes()
    real_write = Store.write_profile
    writes: list[str] = []

    def spy(self: Store, *args: object, **kwargs: object) -> str:
        writes.append("write")
        return real_write(self, *args, **kwargs)

    monkeypatch.setattr(Store, "write_profile", spy)
    with pytest.raises(StoreError, match="replaced or removed"):
        profile_repair.publish(store, first, resumed=False)
    assert writes == ["write"]
    assert receipt.read_bytes() == before
    assert source.read_text() == BAD_EFFORT
    _, landed = clone_profile(remote, tmp_path / "after", store.name)
    assert landed is None


def test_a_receipt_replaced_during_publication_is_not_retired(repo: Path, shared_repo, monkeypatch) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    first = stage_confirmed(store, version=1)
    receipt = store.root / profile_repair.RECEIPT
    newer = profile_repair.Receipt(
        format=1,
        id="c" * 32,
        scope=profile_repair.scope(store),
        source=first.source,
        target="absent",
        profile=Profile(version=2, confirmed_at=NOW),
    )
    real_write = Store.write_profile

    def replace_after_write(self: Store, *args: object, **kwargs: object) -> str:
        notice = real_write(self, *args, **kwargs)
        receipt.write_text(newer.model_dump_json())  # a newer confirmed replacement lands after this publication
        return notice

    monkeypatch.setattr(Store, "write_profile", replace_after_write)
    with pytest.raises(StoreError, match="replaced or removed"):
        profile_repair.publish(store, first, resumed=False)
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert source.read_text() == BAD_EFFORT
    assert receipt.read_text() == newer.model_dump_json()


@pytest.mark.parametrize("damage", ["fifo", "directory", "symlink", "empty_source", "bad_target", "blank_scope"])
def test_an_unreadable_or_invalid_receipt_is_refused_by_name_before_any_change(
    damage: str, repo: Path, shared_repo, monkeypatch, capsys
) -> None:
    store, receipt = refused_repair_receipt(repo, shared_repo, monkeypatch, capsys)
    if damage == "fifo":
        receipt.unlink()
        os.mkfifo(receipt)
    elif damage == "directory":
        receipt.unlink()
        receipt.mkdir()
    elif damage == "symlink":
        elsewhere = receipt.parent / "elsewhere.json"
        elsewhere.write_bytes(receipt.read_bytes())
        receipt.unlink()
        receipt.symlink_to(elsewhere)
    else:
        key, value = {"empty_source": ("source", ""), "bad_target": ("target", ""), "blank_scope": ("scope", "")}[
            damage
        ]
        data = json.loads(receipt.read_text())
        data[key] = value
        receipt.write_text(json.dumps(data))
    source_before = (store.root / profile_share.PROFILE).read_bytes()
    target_before = profile_share.path(store).read_bytes()
    calls = probed_repair(monkeypatch)
    with pytest.raises(StoreError) as info:
        setup.run(repo, [], yes=False, local_files="no")
    assert str(receipt) in str(info.value)
    assert calls == []
    assert (store.root / profile_share.PROFILE).read_bytes() == source_before
    assert profile_share.path(store).read_bytes() == target_before


# Finding 6: a legacy claim is won only by its own published nonce, never by an equal absent basis


def other_logical_store(store: Store, tmp_path: Path, name: str) -> Store:
    """A second logical shared repository (another origin, no network) on the same private root."""
    other = tmp_path / name
    subprocess.run(["git", "init", "-q", "-b", "main", str(other)], check=True)  # noqa: S603, S607
    origin = f"https://github.com/acme/{name}.git"
    subprocess.run(["git", "-C", str(other), "remote", "add", "origin", origin], check=True)  # noqa: S603, S607
    return Store(store.root, DataRepo(other), store.name)


def stage_in_thread(store: Store, digest: str) -> tuple[threading.Thread, dict[str, object]]:
    """Stage a second confirmed replacement on another thread, keeping its outcome instead of raising it."""
    outcome: dict[str, object] = {}

    def run() -> None:
        try:
            outcome["receipt"] = profile_repair.stage(store, Profile(version=2, confirmed_at=NOW), digest, "absent")
        except StoreError as exc:
            outcome["error"] = exc

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, outcome


def test_a_second_logical_repair_waits_for_the_first_stage_on_the_same_private_root(
    repo: Path, shared_repo, monkeypatch, tmp_path
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    digest = profile_share.config_digest(source)
    other = other_logical_store(store, tmp_path, "other-data")
    real_atomic_write = profile_repair.atomic_write
    seen: dict[str, object] = {}

    def stage_second_while_first_writes(path: Path, text: str) -> None:
        if "thread" not in seen:
            thread, outcome = stage_in_thread(other, digest)
            thread.join(0.5)
            seen.update(thread=thread, outcome=outcome, blocked=thread.is_alive())
        real_atomic_write(path, text)

    monkeypatch.setattr(profile_repair, "atomic_write", stage_second_while_first_writes)
    first = stage_confirmed(store, version=1)
    thread = seen["thread"]
    assert isinstance(thread, threading.Thread)
    assert seen["blocked"] is True  # the second stage waits for the first receipt's lock
    thread.join(5)
    assert not thread.is_alive()
    error = seen["outcome"]["error"]  # type: ignore[index]
    assert isinstance(error, StoreError)
    assert "already pending" in str(error)
    pending_receipt = profile_repair.pending(store)
    assert pending_receipt is not None
    assert pending_receipt.id == first.id


def test_a_second_logical_repair_waits_while_the_first_publication_finishes_on_the_same_private_root(
    repo: Path, shared_repo, monkeypatch, tmp_path
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    digest = profile_share.config_digest(source)
    first = stage_confirmed(store, version=1)
    other = other_logical_store(store, tmp_path, "other-data")
    real_retire = roles_move.retire_source
    seen: dict[str, object] = {}

    def stage_second_while_first_finishes(retiring: Store) -> None:
        thread, outcome = stage_in_thread(other, digest)
        thread.join(0.5)
        seen.update(thread=thread, outcome=outcome, blocked=thread.is_alive())
        real_retire(retiring)

    monkeypatch.setattr(roles_move, "retire_source", stage_second_while_first_finishes)
    profile_repair.publish(store, first, resumed=False)
    thread = seen["thread"]
    assert isinstance(thread, threading.Thread)
    assert seen["blocked"] is True  # the second stage waits for the first receipt's lock while it finishes
    thread.join(5)
    assert not thread.is_alive()
    assert "error" not in seen["outcome"]  # type: ignore[operator]
    second = seen["outcome"]["receipt"]  # type: ignore[index]
    assert isinstance(second, profile_repair.Receipt)
    assert second.id != first.id
    assert profile_repair.pending(other) == second  # the second logical repository sees its own receipt
    assert (store.root / profile_share.ROLES_MOVED).exists()


def test_a_same_id_receipt_whose_profile_changed_is_refused_before_any_write(
    repo: Path, shared_repo, monkeypatch, tmp_path
) -> None:
    _data, remote = shared_repo
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    first = stage_confirmed(store, version=1)
    receipt = store.root / profile_repair.RECEIPT
    receipt.write_text(first.model_copy(update={"profile": Profile(version=2, confirmed_at=NOW)}).model_dump_json())
    before = receipt.read_bytes()
    with pytest.raises(StoreError, match="replaced or removed"):
        profile_repair.publish(store, first, resumed=False)
    assert receipt.read_bytes() == before
    assert not (store.root / profile_share.ROLES_MOVED).exists()
    assert source.read_text() == BAD_EFFORT
    _fresh, landed = clone_profile(remote, tmp_path)
    assert landed is None


def test_a_receipt_without_a_format_version_is_refused_before_any_publication(
    repo: Path, shared_repo, monkeypatch, tmp_path
) -> None:
    _data, remote = shared_repo
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    stage_confirmed(store, version=1)
    receipt = store.root / profile_repair.RECEIPT
    payload = json.loads(receipt.read_text())
    del payload["format"]
    receipt.write_text(json.dumps(payload))
    before = receipt.read_bytes()
    with pytest.raises(StoreError) as caught:
        profile_repair.pending(store)
    assert str(receipt) in str(caught.value)
    assert receipt.read_bytes() == before
    _fresh, landed = clone_profile(remote, tmp_path)
    assert landed is None


@pytest.mark.parametrize("failing", ["fstat", "read"])
def test_a_receipt_read_failure_closes_its_descriptor_once_and_names_the_receipt(
    repo: Path, shared_repo, monkeypatch, failing: str
) -> None:
    store = shared_project(repo, shared_repo, monkeypatch)
    source = store.root / profile_share.PROFILE
    source.write_text(BAD_EFFORT)
    stage_confirmed(store, version=1)
    receipt = store.root / profile_repair.RECEIPT
    opened: list[int] = []
    closed: list[int] = []
    real_open, real_close = os.open, os.close

    def spy_open(path: object, *args: object, **kwargs: object) -> int:
        fd = real_open(path, *args, **kwargs)  # type: ignore[arg-type]
        if os.fspath(path) == str(receipt):  # type: ignore[arg-type]
            opened.append(fd)
        return fd

    def spy_close(fd: int) -> None:
        closed.append(fd)
        real_close(fd)

    def fault(*_args: object) -> object:
        msg = "disk fault"
        raise OSError(msg)

    monkeypatch.setattr(os, "open", spy_open)
    monkeypatch.setattr(os, "close", spy_close)
    monkeypatch.setattr(os, failing, fault)
    with pytest.raises(StoreError) as caught:
        profile_repair._read(store)  # noqa: SLF001 - the descriptor lifetime is the probe's subject
    assert str(receipt) in str(caught.value)
    assert len(opened) == 1
    assert closed.count(opened[0]) == 1


def clone_as(remote: Path, tmp_path: Path, name: str, project: str = "shop-site") -> tuple[Store, Profile]:
    """A separate checkout of *remote* named *name*, another clone of the same shared record with its own identity."""
    second = tmp_path / name
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        subprocess.run(["git", "-C", str(second), "config", key, value], check=True)  # noqa: S603, S607
    fresh = Store(tmp_path / f"{name}-store", DataRepo(second), project)
    return fresh, fresh.read_profile()


def crash_before_fill(monkeypatch) -> None:
    msg = "crash before the fill"

    def boom(*_args, **_kwargs):
        raise RuntimeError(msg)

    monkeypatch.setattr(prefs_import, "_fill", boom)


def test_a_published_absent_claim_is_not_won_by_a_stale_clone(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    a = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    a.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    b, _ = clone_as(remote, tmp_path, "b")  # B reads the profile before A claims, so B's marker is still unclaimed
    with monkeypatch.context() as m:
        crash_before_fill(m)
        with pytest.raises(RuntimeError, match="crash before the fill"):
            prefs_import.run(a)
    claimed = a.read_profile()
    assert (claimed.prefs_import, claimed.prefs_basis) == ("pending", "absent")

    with pytest.raises(StoreError, match="claim was not published") as first:
        prefs_import.run(b)  # B's own claim conflicts with A's published one and must not create the config
    assert "could not be merged with the remote" in str(first.value)
    assert not b.config_path.exists()

    with pytest.raises(StoreError, match="claim was not published"):
        prefs_import.run(b)  # the unconfirmed claim is published again, still conflicts, and never fills
    assert not b.config_path.exists()
    assert b.read_profile().prefs_import == "pending"

    fresh, got = clone_as(remote, tmp_path, "c")
    assert (got.prefs_import, got.prefs_claim) == ("pending", claimed.prefs_claim)
    assert not fresh.config_path.exists()


def test_an_unconfirmed_claim_is_published_again_and_wins_before_it_fills(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    real, refused = DataRepo.publish, []

    def publish(self, path, message, until=None):
        if path == profile_share.path(store) and message.endswith("import pending") and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", publish)
    with pytest.raises(StoreError, match="claim was not published"):
        prefs_import.run(store)
    assert refused
    assert not store.config_path.exists()
    assert profile_share.claim_unconfirmed(store, store.read_profile())

    prefs_import.run(store)  # the retry confirms the claim as the winner, and the absent basis fills once
    fresh, got = clone_as(remote, tmp_path, "fresh")
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45


def test_an_ordinary_save_keeps_the_published_claim_id_and_basis(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    with monkeypatch.context() as m:
        crash_before_fill(m)
        with pytest.raises(RuntimeError):
            prefs_import.run(store)
    claim = store.read_profile().prefs_claim
    store.write_profile(Profile(entries={profile.POLL: confirmed("30")}))  # an ordinary save omits the claim
    _, got = clone_as(remote, tmp_path, "fresh")
    assert (got.prefs_import, got.prefs_basis, got.prefs_claim) == ("pending", "absent", claim)
    assert got.entries[profile.POLL].value == "30"


def test_a_shared_winner_paused_after_its_fresh_claim_is_not_refilled_after_settlement_and_owner_delete(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    winner_store = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    settler = Store(tmp_path / "b-store", DataRepo(root), "shop-site")
    winner_store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    assert winner_store.shared is not None
    assert settler.shared is not None
    assert winner_store.config_path == settler.config_path
    assert winner_store.root != settler.root
    claimed: list[str] = []

    def settle_and_delete() -> None:
        read = winner_store.read_profile()  # the winner read its own fresh claim before it paused
        assert (read.prefs_import, read.prefs_basis) == ("pending", "absent")
        claimed.append(read.prefs_claim)
        settler.mark_prefs_import("pending", "done")  # Settings completes the import on another private root
        settler.config_path.unlink(missing_ok=True)  # the owner deletes the shared project config

    prefs_import.run(paused_after_claim(winner_store, monkeypatch, settle_and_delete))

    assert not winner_store.config_path.exists()  # the stale fill never publishes the deleted config
    fresh, got = clone_as(remote, tmp_path, "fresh")
    assert got.prefs_import == "done"
    assert got.prefs_claim == claimed[0]
    assert not fresh.config_path.exists()


def test_a_shared_claim_replaced_while_paused_is_not_filled_by_the_stale_winner(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    winner_store = Store(tmp_path / "a-store", DataRepo(root), "shop-site")
    other = Store(tmp_path / "b-store", DataRepo(root), "shop-site")
    winner_store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))

    def newer_claim() -> None:
        other.mark_prefs_import("pending", "pending", profile_share.ABSENT, "newer")  # the only path that moves it
        other.config_path.unlink(missing_ok=True)

    prefs_import.run(paused_after_claim(winner_store, monkeypatch, newer_claim))

    assert not winner_store.config_path.exists()
    fresh, got = clone_as(remote, tmp_path, "fresh")
    assert (got.prefs_import, got.prefs_claim) == ("pending", "newer")  # the newer claim is left to its own importer
    assert not fresh.config_path.exists()


def owner_publishes_then_deletes_config(store: Store) -> None:
    """The owner saves the project config, publishes it, then deletes it and publishes the deletion."""
    store.config_path.write_text(Layer().model_dump_json(indent=1))
    store.shared.publish(store.config_path, "settings: shop-site: project layer")
    store.config_path.unlink()
    store.shared.publish(store.config_path, "settings: shop-site: project layer removed")


def test_a_winner_paused_on_its_own_checkout_is_not_restored_after_another_checkout_completes_and_deletes(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    Store(tmp_path / "seed-store", DataRepo(root), "shop-site").write_profile(
        Profile(entries={profile.POLL: confirmed("45")})
    )
    winner, _ = clone_as(remote, tmp_path, "winner-checkout")
    settler, _ = clone_as(remote, tmp_path, "settler-checkout")
    assert winner.shared is not None
    assert settler.shared is not None

    def complete_and_delete_on_the_other_checkout() -> None:
        assert winner.read_profile().prefs_import == "pending"  # the winner read its own claim before it paused
        assert settler.shared.pull() == ""  # the other checkout sees the claim only after a pull
        assert settler.read_profile().prefs_import == "pending"
        settler.mark_prefs_import("pending", "done")  # Settings completes the import
        owner_publishes_then_deletes_config(settler)

    prefs_import.run(paused_after_claim(winner, monkeypatch, complete_and_delete_on_the_other_checkout))

    assert not winner.config_path.exists()  # the stale fill is not published over the owner's deletion
    fresh, got = clone_as(remote, tmp_path, "fresh-checkout")
    assert got.prefs_import == "done"
    assert not fresh.config_path.exists()
    assert fresh.read_config().prefs is None


def test_a_winner_paused_on_its_own_checkout_still_fills_after_an_unrelated_remote_advance(
    shared_repo, tmp_path, monkeypatch
):
    root, remote = shared_repo
    Store(tmp_path / "seed-store", DataRepo(root), "shop-site").write_profile(
        Profile(entries={profile.POLL: confirmed("45")})
    )
    winner, _ = clone_as(remote, tmp_path, "winner-checkout")
    other, _ = clone_as(remote, tmp_path, "other-checkout")
    assert other.shared is not None

    def unrelated_advance() -> None:
        notes = other.shared.root / "unrelated" / "notes.md"
        notes.parent.mkdir(parents=True, exist_ok=True)
        notes.write_text("an unrelated change\n")
        other.shared.publish(notes, "unrelated: notes")

    prefs_import.run(paused_after_claim(winner, monkeypatch, unrelated_advance))

    assert winner.read_config().prefs.ci_poll_seconds == 45
    fresh, got = clone_as(remote, tmp_path, "fresh-checkout")
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45


def test_a_published_fresh_claim_fills_once_and_marks_done(shared_repo, tmp_path):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    prefs_import.run(store)
    fresh, got = clone_as(remote, tmp_path, "fresh")
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45
