"""The legacy preference import recovers from owner reviews, stored values, and failed publications (R15, FND-01)."""

import subprocess
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
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api, config_routes
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import Prefs
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.store import Store, StoreError

AUTH = {"authorization": "Bearer " + "t"}
NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


class Host:
    wake = SimpleNamespace(set=lambda: None)
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


def clone_profile(remote: Path, tmp_path: Path) -> tuple[Store, Profile]:
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(second), "shop-site")
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
    store.update_config(lambda cur: cur.model_copy(update={"prefs": Prefs(ask_before_merge=False)}), "test")
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


def test_a_deleted_config_stays_absent_through_the_settings_retry(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    refuse_completion_once(monkeypatch, store)
    with pytest.raises(StoreError):
        prefs_import.run(store)
    store.config_path.unlink()

    config_routes._settle_prefs_import(store, reviewed=False)  # noqa: SLF001 - the Settings save's own settlement, no page
    fresh, got = clone_profile(remote, tmp_path)
    assert got.prefs_import == "done"
    assert not fresh.config_path.exists()
    assert not store.config_path.exists()
