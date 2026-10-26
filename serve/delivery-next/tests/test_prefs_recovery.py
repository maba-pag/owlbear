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
from owlbear_delivery_next.commands import setup
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import readiness
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import Layer, Prefs
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

    late = Profile(
        version=2, runtime="vscode", entries={profile.POLL: confirmed("45"), profile.WINDOW: confirmed("30")}
    )
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
    assert got.runtime == "vscode"
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


# Finding 6: a legacy claim is won only by its own published nonce, never by an equal absent basis


def clone_as(remote: Path, tmp_path: Path, name: str) -> tuple[Store, Profile]:
    """A separate checkout of *remote* named *name*, another clone of the same shared record with its own identity."""
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


def test_a_published_fresh_claim_fills_once_and_marks_done(shared_repo, tmp_path):
    root, remote = shared_repo
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    store.write_profile(Profile(entries={profile.POLL: confirmed("45")}))
    prefs_import.run(store)
    fresh, got = clone_as(remote, tmp_path, "fresh")
    assert got.prefs_import == "done"
    assert fresh.read_config().prefs.ci_poll_seconds == 45
