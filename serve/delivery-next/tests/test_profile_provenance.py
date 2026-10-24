"""Observation-bound confirmations and clone-local facts, using synthetic repositories and GitHub observations."""

import contextlib
import json
import subprocess
import threading
from datetime import UTC, datetime

import pytest

from owlbear_delivery_next.change_contracts.models import Change, Names, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import brief_tools, worktree
from owlbear_delivery_next.github.merge_offer import Block, decide
from owlbear_delivery_next.github.provider import CiState, MergeMethod, PullRequest, Repository, Rules
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import briefs, profile_share
from owlbear_delivery_next.state_store.store import Lock, Store, StoreError
from owlbear_delivery_next.workflow_steps import engine, follow

NOW = datetime(2026, 10, 24, tzinfo=UTC)


class GitHub:
    """A complete typed repository/rules observation; no provider mutation or authentication."""

    def __init__(self, *, push=True, target="main", strict=False, known=True):
        self.push, self.target, self.strict, self.known = push, target, strict, known

    def read_repository(self):
        return Repository(
            repository="acme/shop-site",
            url="https://github.com/acme/shop-site",
            default_branch=self.target,
            methods=(MergeMethod.MERGE,),
            can_push=self.push,
            delete_branch_on_merge=False,
        )

    def read_rules(self, _repository, _target):
        return Rules(
            state="known" if self.known else "unknown",
            evidence="same observation label",
            allowed_methods=(MergeMethod.MERGE,),
            strict=self.strict,
        )


def git(root, *args):
    return subprocess.run(  # noqa: S603 - fixed synthetic Git test commands
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def clone(root, name):
    path = root / name
    git(root, "init", "-q", "-b", "main", str(path))
    git(path, "commit", "--allow-empty", "-qm", "base")
    git(path, "remote", "add", "origin", "git@github.com:acme/shop-site.git")
    return path


@pytest.fixture
def shared(tmp_path, monkeypatch):
    remote, root = tmp_path / "remote.git", tmp_path / "data"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    git(root, "config", "user.name", "t")
    git(root, "config", "user.email", "t@example.com")
    git(root, "commit", "--allow-empty", "-qm", "base")
    git(root, "push", "-q", "-u", "origin", "HEAD")
    monkeypatch.setenv("OWLBEAR_DATA", str(root))
    return root


def permission_block(prof):
    pr = PullRequest(
        repository="acme/shop-site",
        number=1,
        node_id="n1",
        url="https://github.com/acme/shop-site/pull/1",
        head_branch="owlbear/c1",
        head_sha="a" * 40,
        base_branch="main",
        draft=False,
        state="open",
        merged=False,
        mergeable=True,
        merge_state="clean",
    )
    return decide(
        pr,
        target="main",
        ci=CiState(passed=(), failed=(), running=(), missing=()),
        rules=Rules(state="known", evidence="rules"),
        rules_confirmed=False,
        method=MergeMethod.MERGE,
        methods=(MergeMethod.MERGE,),
        can_push=profile.value(prof, profile.PUSH) == "yes",
    ).block


def test_unchanged_observation_preserves_confirmed_intent_not_the_detected_value(tmp_path):
    repo = clone(tmp_path, "shop")
    confirmed = profile.confirm(profile.detect(repo, GitHub(), None), profile.DEFAULT, "release", NOW)
    again = profile.detect(repo, GitHub(), confirmed)
    assert again.entries[profile.DEFAULT] == confirmed.entries[profile.DEFAULT]
    assert again.version == confirmed.version
    assert profile.value(again, profile.DEFAULT) == "release"


def test_same_label_with_a_new_default_value_expires_the_old_confirmation(tmp_path):
    repo = clone(tmp_path, "shop")
    confirmed = profile.confirm(profile.detect(repo, GitHub(), None), profile.DEFAULT, "release", NOW)
    again = profile.detect(repo, GitHub(target="trunk"), confirmed)
    assert profile.value(again, profile.DEFAULT) == "trunk"
    assert not again.entries[profile.DEFAULT].evidence.startswith(profile.CONFIRMED)


@pytest.mark.parametrize("known", [False, True])
def test_same_rule_label_does_not_hide_a_changed_state_or_value(tmp_path, known):
    repo = clone(tmp_path, "shop")
    confirmed = profile.confirm(profile.detect(repo, GitHub(), None), profile.STRICT, "no", NOW)
    again = profile.detect(repo, GitHub(strict=True, known=known), confirmed)
    assert again.entries[profile.STRICT].state == ("known" if known else "unknown")
    assert profile.value(again, profile.STRICT) == ("yes" if known else "")
    diffs, _ = profile.reread(confirmed, GitHub(strict=True, known=known), "main")
    assert any(profile.STRICT in line for line in diffs)


def test_fingerprint_survives_json_and_reconfirmation_has_no_nested_evidence(tmp_path):
    repo = clone(tmp_path, "shop")
    once = profile.confirm(profile.detect(repo, GitHub(), None), profile.STRICT, "no", NOW)
    back = Profile.model_validate_json(once.model_dump_json())
    twice = profile.confirm(back, profile.STRICT, "no", NOW)
    assert twice.entries[profile.STRICT] == once.entries[profile.STRICT]
    assert len(twice.entries[profile.STRICT].observed) == 64


def test_owner_intent_without_a_detector_entry_is_not_dropped(tmp_path):
    repo = clone(tmp_path, "shop")
    once = profile.confirm(profile.detect(repo, GitHub(), None), "allow:install", "yes", NOW)
    again = profile.detect(repo, GitHub(), once)
    assert again.entries["allow:install"] == once.entries["allow:install"]


def test_a_confirmation_expires_when_its_detected_package_disappears(tmp_path, monkeypatch):
    repo = clone(tmp_path, "shop")
    entry = ProfileEntry(state="known", value="uv sync --locked", evidence="uv.lock")
    monkeypatch.setattr(profile, "package_entries", lambda _repo: {"install:.": entry})
    once = profile.confirm(profile.detect(repo, GitHub(), None), "install:.", "uv sync --locked", NOW)
    monkeypatch.setattr(profile, "package_entries", lambda _repo: {})
    again = profile.detect(repo, GitHub(), once)
    assert not profile.known(again, "install:.")


def test_two_clones_repeatedly_read_their_own_facts_after_both_first_detection_markers(shared, tmp_path, monkeypatch):
    first, second = clone(tmp_path, "shop-a"), clone(tmp_path, "shop-b")
    a, b = Store.open(first), Store.open(second)
    a.write_profile(Profile(version=1))
    monkeypatch.setattr(profile, "provider", lambda _p, repo: GitHub(push=repo == first))
    monkeypatch.setattr(
        profile,
        "package_entries",
        lambda repo: {
            "install:.": ProfileEntry(
                state="known", value="install-a" if repo == first else "install-b", evidence="same lockfile label"
            ),
        },
    )
    for store, repo, can_push, command in [(a, first, "yes", "install-a"), (b, second, "no", "install-b")] * 3:
        actual = profile_share.checked(store, repo)
        assert profile.value(actual, profile.PUSH) == can_push
        assert profile.value(actual, "install:.") == command
        assert (permission_block(actual) == Block.NO_PERMISSION) is (can_push == "no")
    raw = json.loads((shared / "shop-site" / "profile.json").read_text())
    assert profile.PUSH not in raw["entries"]
    assert profile.HOOKS not in raw["entries"]
    assert "install:." not in raw["entries"]


def test_new_change_uses_current_detected_target_and_existing_change_keeps_its_pin(tmp_path):
    repo = clone(tmp_path, "shop")
    once = profile.confirm(profile.detect(repo, GitHub(), None), profile.DEFAULT, "release", NOW)
    fresh = profile.detect(repo, GitHub(target="trunk"), once)
    draft = brief_tools.BriefDraft(
        title="Add farewell",
        outcome="The farewell function says goodbye",
        criteria=["Farewell says goodbye"],
        scope=["app.py"],
    )
    prior = Change(slug="old", handle="c1", names=Names(target="release", branch="owlbear/old"))
    assert briefs.drafted(None, draft, "new", "c2", fresh).names.target == "trunk"
    assert briefs.drafted(prior, draft, "old", "c1", fresh).names.target == "release"


def test_an_old_local_profile_keeps_its_own_facts_before_any_overlay_exists(tmp_path):
    store = Store(tmp_path)
    raw = Profile(version=1, entries={profile.PUSH: ProfileEntry(state="known", value="yes")})
    (tmp_path / profile_share.PROFILE).write_text(raw.model_dump_json())
    assert profile.value(store.read_profile(), profile.PUSH) == "yes"


def test_a_legacy_local_confirmation_is_reobserved_once_without_rechecking_current_local_profiles(
    tmp_path,
    monkeypatch,
):
    repo = clone(tmp_path, "shop")
    store = Store(tmp_path / "local-store")
    store.write_profile(
        Profile(
            version=1,
            entries={
                profile.DEFAULT: ProfileEntry(
                    state="known", value="release", evidence="owner confirmed before binding"
                ),
            },
        )
    )
    calls = []

    def provider(*_a):
        calls.append("observed")
        return GitHub(target="trunk")

    monkeypatch.setattr(profile, "provider", provider)
    assert profile.value(profile_share.checked(store, repo), profile.DEFAULT) == "trunk"
    assert profile.value(profile_share.checked(store, repo), profile.DEFAULT) == "trunk"
    assert calls == ["observed"]


def test_adoption_preserves_an_existing_own_overlay_without_publishing_it(shared, tmp_path):
    root = tmp_path / "clone-store"
    local = Store(root)
    local.write_profile(Profile(version=1, entries={profile.PUSH: ProfileEntry(state="known", value="yes")}))
    (root / profile_share.ROLES_MOVED).write_text("roles already migrated\n")
    adopted = Store(root, DataRepo(shared), "shop-site")
    profile_share.adopt(adopted)
    assert profile.value(adopted.read_profile(), profile.PUSH) == "yes"
    raw = json.loads((shared / "shop-site" / profile_share.PROFILE).read_text())
    assert profile.PUSH not in raw["entries"]
    assert (root / "profile.json.moved").exists()


def test_invalid_legacy_adoption_is_not_published_as_an_unparsed_fallback(shared, tmp_path):
    root = tmp_path / "bad-store"
    root.mkdir()
    (root / profile_share.PROFILE).write_text("{damaged")
    (root / profile_share.ROLES_MOVED).write_text("roles already migrated\n")
    with pytest.raises(StoreError):
        profile_share.adopt(Store(root, DataRepo(shared), "shop-site"))
    assert not (shared / "shop-site" / profile_share.PROFILE).exists()
    assert (root / profile_share.PROFILE).read_text() == "{damaged"


@pytest.mark.parametrize("bad", ["json", "format", "foreign", "symlink"])
def test_invalid_or_foreign_overlays_fail_visibly_without_becoming_an_empty_success(tmp_path, bad):
    store = Store(tmp_path)
    store.write_profile(Profile(version=1))
    overlay = tmp_path / profile_share.LOCAL
    if bad == "json":
        overlay.write_text("{bad")
    elif bad == "format":
        overlay.write_text('{"format":999,"entries":{}}')
    elif bad == "foreign":
        overlay.write_text(
            Profile(entries={profile.DEFAULT: ProfileEntry(state="known", value="other")}).model_dump_json()
        )
    else:
        elsewhere = tmp_path / "foreign.json"
        elsewhere.write_text(Profile().model_dump_json())
        overlay.symlink_to(elsewhere)
    with pytest.raises(StoreError):
        store.read_profile()


def test_empty_local_facts_clear_the_old_overlay_instead_of_resurrecting_it(tmp_path):
    store = Store(tmp_path)
    store.write_profile(Profile(entries={profile.PUSH: ProfileEntry(state="known", value="yes")}))
    assert (tmp_path / profile_share.LOCAL).exists()
    store.write_profile(Profile(version=1))
    assert not (tmp_path / profile_share.LOCAL).exists()
    assert profile.value(store.read_profile(), profile.PUSH) == ""


@pytest.mark.parametrize("signal", ["error", "notice"])
def test_detection_publication_failure_preserves_local_progress_and_retries_without_file_undo(
    shared,
    tmp_path,
    monkeypatch,
    signal,
):
    repo = clone(tmp_path, "shop")
    store = Store.open(repo)
    store.write_profile(Profile(version=1))
    monkeypatch.setattr(profile, "provider", lambda *_a: GitHub(push=True))
    publisher = DataRepo.publish
    calls = []

    def offline(*_a, **_kw):
        calls.append("failed")
        msg = "synthetic publication failure"
        if signal == "notice":
            return msg
        raise DataRepoError(msg)

    monkeypatch.setattr(DataRepo, "publish", offline)
    with pytest.raises(StoreError, match="could not be published"):
        profile_share.checked(store, repo)
    assert not (store.root / profile_share.DETECTED).exists()
    assert profile.value(store.read_profile(), profile.PUSH) == "yes"
    raw = json.loads((shared / "shop-site" / profile_share.PROFILE).read_text())
    assert raw["version"] == 2
    monkeypatch.setattr(DataRepo, "publish", publisher)
    assert profile.value(profile_share.checked(store, repo), profile.PUSH) == "yes"
    assert (store.root / profile_share.DETECTED).exists()
    published = git(shared, "--git-dir", str(shared.parent / "remote.git"), "show", "main:shop-site/profile.json")
    assert json.loads(published)["entries"][profile.DEFAULT]["value"] == "main"
    assert calls == ["failed"]


@pytest.mark.parametrize("reconfirm", [False, True])
def test_owner_selected_ci_checks_keep_their_workflow_digest_through_confirmation(tmp_path, reconfirm):
    repo = clone(tmp_path, "shop")
    raw = profile.detect(repo, GitHub(), None)
    chosen = profile.confirm(raw, profile.DECLARED, "lint", NOW)
    if reconfirm:
        chosen = profile.confirm(chosen, profile.DECLARED, "lint", NOW)
    head = git(repo, "rev-parse", "HEAD")
    pr = PullRequest(
        repository="acme/shop-site",
        number=1,
        node_id="n1",
        url="https://github.com/acme/shop-site/pull/1",
        head_branch="owlbear/c1",
        head_sha=head,
        base_branch="main",
        draft=False,
        state="open",
        merged=False,
    )
    c = Change(slug="c1", names=Names(worktree=str(repo), target="main", pr=1))
    ctx = engine.Ctx(Store(tmp_path / "store"), Lock("c1"), repo, chosen, GitHub(), NOW)
    declared, held = follow.declared(ctx, c, pr, StepKind.FOLLOW)
    assert held is None
    assert declared == ("lint",)
    assert profile.digest_of(chosen.entries[profile.DECLARED]) == profile.digest_of(raw.entries[profile.DECLARED])
    assert chosen.entries[profile.DECLARED].evidence.count("observed:") == 1


def _pair(default, push):
    return Profile(
        version=1,
        entries={
            profile.DEFAULT: ProfileEntry(state="known", value=default, evidence="owner"),
            profile.PUSH: ProfileEntry(state="known", value=push, evidence="owner"),
        },
    )


@pytest.mark.usefixtures("shared")
def test_overlapping_profile_saves_keep_one_writers_shared_copy_and_overlay(tmp_path, monkeypatch):
    store = Store.open(clone(tmp_path, "shop"))
    real_locked = DataRepo.locked
    entered, release = threading.Event(), threading.Event()
    errors = []

    @contextlib.contextmanager
    def latched(self, wait=None):
        if threading.current_thread().name == "first-profile-save":
            entered.set()
            assert release.wait(10)
        with real_locked(self, wait):
            yield

    def first():
        try:
            store.write_profile(_pair("first", "yes"))
        except Exception as exc:  # noqa: BLE001 - propagate the thread's failure to the test
            errors.append(exc)

    monkeypatch.setattr(DataRepo, "locked", latched)
    writer = threading.Thread(target=first, name="first-profile-save")
    writer.start()
    try:
        assert entered.wait(10)
        store.write_profile(_pair("second", "no"))
    finally:
        release.set()
        writer.join(10)
    assert not writer.is_alive()
    assert not errors
    saved = store.read_profile()
    assert profile.value(saved, profile.DEFAULT) == "first"
    assert profile.value(saved, profile.PUSH) == "yes"


@pytest.mark.parametrize("owner", ["confirm", "clear"])
@pytest.mark.parametrize("channel", ["local", "shared"])
@pytest.mark.usefixtures("shared")
def test_owner_local_edit_during_detection_survives_the_race(tmp_path, monkeypatch, owner, channel):
    repo = clone(tmp_path, "shop")
    store = Store.open(repo)
    monkeypatch.setattr(profile, "provider", lambda *_a: GitHub(push=True))
    prev = profile.detect(repo, GitHub(push=False), None)
    missing = ProfileEntry(state="unknown", evidence="install:vendor: not detected in this clone")
    store.write_profile(prev.model_copy(update={"entries": {**prev.entries, "install:vendor": missing}}))
    real_detect = profile.detect

    def detect_while_owner_edits(repo_, gh, previous):
        fresh = real_detect(repo_, gh, previous)
        base = store.read_profile()
        if owner == "confirm":
            edit = profile.confirm(base, "install:vendor", "make deps", NOW)
        else:
            edit = base.model_copy(update={"entries": {k: e for k, e in base.entries.items() if k != "install:vendor"}})
        version = base.version if channel == "local" else base.version + 1
        store.write_profile(edit.model_copy(update={"version": version, "confirmed_at": base.confirmed_at}))
        return fresh

    monkeypatch.setattr(profile, "detect", detect_while_owner_edits)
    result = profile_share.checked(store, repo)
    for kept in (result, store.read_profile()):
        assert profile.value(kept, profile.PUSH) == "yes"
        if owner == "confirm":
            assert worktree.installs(kept, ["vendor/lib.py"]) == [("vendor", "make deps")]
        else:
            assert "install:vendor" not in kept.entries
    assert not (store.root / profile_share.DETECTED).exists()
    monkeypatch.setattr(profile, "detect", real_detect)
    retried = profile_share.checked(store, repo)
    assert (store.root / profile_share.DETECTED).exists()
    assert profile.value(retried, "install:vendor") == ("make deps" if owner == "confirm" else "")


def test_a_confirmed_absent_install_survives_detection_and_reaches_the_worktree(tmp_path):
    repo = clone(tmp_path, "shop")
    chosen = profile.confirm(profile.detect(repo, GitHub(), None), "install:vendor", "make deps", NOW)
    again = profile.detect(repo, GitHub(), chosen)
    assert worktree.installs(again, ["vendor/lib.py"]) == [("vendor", "make deps")]
