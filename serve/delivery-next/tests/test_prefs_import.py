"""The one-time legacy preference import keeps owner clears and never resurrects them (R15, FND-01)."""

import json
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile, ProfileEntry
from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import config, migrations, profile, roles
from owlbear_delivery_next.settings.config import CONFIG_FORMAT, Layer, Prefs
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.store import (
    FormatTooNewError,
    Store,
    StoreError,
    _parse,
    read_layer,
    update_layer,
)


@pytest.fixture(autouse=True)
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


@pytest.fixture
def legacy_store(tmp_path):
    store = Store(tmp_path / "store")
    entry = ProfileEntry(state="known", value="45", evidence=f"{profile.CONFIRMED}; owner")
    store.write_profile(Profile(entries={profile.POLL: entry}))
    store.save(store.config_path, Layer, lambda _cur: Layer(), "owner", owner=True)
    return store


def test_a_claim_is_durable_before_the_fill_so_a_config_deletion_cannot_refill(legacy_store, monkeypatch):
    store = legacy_store
    seen: list[str] = []
    original = store.update_config

    def fill_then_delete(change, what="project layer", on_written=None):
        seen.append(store.read_profile().prefs_import)
        out = original(change, what, on_written)
        store.save(store.config_path, Layer, lambda _cur: Layer(), "owner", owner=True)
        return out

    monkeypatch.setattr(store, "update_config", fill_then_delete)
    prefs_import.run(store)
    assert seen == ["pending"]
    assert store.read_profile().prefs_import == "done"
    assert store.read_config().prefs is None
    fresh = Store(store.root)
    prefs_import.run(fresh)
    assert fresh.read_config().prefs is None


@pytest.mark.parametrize("failure", [OSError("publish failed"), KeyboardInterrupt()], ids=["os-error", "interrupt"])
def test_durable_claim_restarts_before_fill_with_unchanged_config(legacy_store, monkeypatch, failure):
    store = legacy_store
    before = store.config_path.read_bytes()
    basis = profile_share.config_digest(store.config_path)

    def fail(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(store, "update_config", fail)
    with pytest.raises(type(failure)) as caught:
        prefs_import.run(store)
    if isinstance(failure, OSError):
        assert str(caught.value) == "publish failed"
    claimed = store.read_profile()
    assert (claimed.prefs_import, claimed.prefs_basis) == ("pending", basis)
    assert claimed.prefs_claim
    assert store.config_path.read_bytes() == before
    fresh = Store(store.root)
    prefs_import.run(fresh)
    assert fresh.read_config().prefs.ci_poll_seconds == 45
    assert fresh.read_profile().prefs_import == "done"


@pytest.mark.parametrize("action", ["set-30", "clear", "delete"])
def test_changed_or_deleted_claim_basis_is_not_filled(legacy_store, monkeypatch, action):
    store = legacy_store
    original = store.update_config
    before: list[bytes | None] = []

    def changed_then_fill(change, what="project layer", on_written=None):
        if action == "delete":
            store.config_path.unlink()
            before.append(None)
        else:
            value = 30 if action == "set-30" else None
            store.save(
                store.config_path,
                Layer,
                lambda _cur: Layer(prefs=Prefs(ci_poll_seconds=value)),
                "owner",
                owner=True,
            )
            before.append(store.config_path.read_bytes())
        return original(change, what, on_written)

    monkeypatch.setattr(store, "update_config", changed_then_fill)
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    fresh = Store(store.root)
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(fresh)
    assert fresh.read_profile().prefs_import == "pending"
    assert (fresh.config_path.read_bytes() if fresh.config_path.exists() else None) == before[0]
    assert fresh.read_config().prefs_imported is False
    if action != "delete":
        assert fresh.read_config().prefs.ci_poll_seconds == (30 if action == "set-30" else None)


@pytest.mark.parametrize("action", ["clear", "delete"])
def test_pending_latched_fill_keeps_owner_clear_or_refuses_deletion(legacy_store, monkeypatch, action):
    store = legacy_store
    original_mark = store.mark_prefs_import

    def crash_before_done(expect, to, basis="", claim=""):
        if to == "done":
            raise KeyboardInterrupt
        return original_mark(expect, to, basis, claim)

    monkeypatch.setattr(store, "mark_prefs_import", crash_before_done)
    with pytest.raises(KeyboardInterrupt):
        prefs_import.run(store)
    assert store.read_profile().prefs_import == "pending"
    assert store.read_config().prefs_imported is True
    if action == "delete":
        store.config_path.unlink()
    else:
        store.save(
            store.config_path,
            Layer,
            lambda _cur: Layer(prefs=Prefs(ci_poll_seconds=None), prefs_imported=True),
            "owner",
            owner=True,
        )
    fresh = Store(store.root)
    if action == "delete":
        with pytest.raises(StoreError, match="incomplete"):
            prefs_import.run(fresh)
        assert not fresh.config_path.exists()
        assert fresh.read_profile().prefs_import == "pending"
    else:
        prefs_import.run(fresh)
        assert fresh.read_config().prefs.ci_poll_seconds is None
        assert fresh.read_profile().prefs_import == "done"


def test_a_profile_format_three_claim_without_a_basis_does_not_fill_on_resume(legacy_store):
    store = legacy_store
    profile_share.path(store).write_text(json.dumps({"format": 3, "prefs_import": "pending"}))
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert store.read_config().prefs is None
    assert store.read_profile().prefs_import == "pending"


def test_a_cloned_repo_whose_config_already_carries_the_import_is_not_refilled(legacy_store):
    store = legacy_store
    store.save(
        store.config_path,
        Layer,
        lambda _cur: Layer(prefs=Prefs(ci_poll_seconds=None), prefs_imported=True),
        "owner",
        owner=True,
    )
    prefs_import.run(store)
    assert store.read_config().prefs.ci_poll_seconds is None
    assert store.read_profile().prefs_import == "done"


@pytest.mark.parametrize(
    ("raw", "marker"),
    [({"format": 3, "prefs_import": "pending"}, "pending"), ({"format": PROFILE_FORMAT - 1}, "")],
    ids=["format-3-pending", "previous-format-empty"],
)
def test_old_profile_import_markers_migrate_without_inventing_a_basis(raw, marker):
    raw = json.dumps(raw)
    old = _parse(raw, "profile", Profile, PROFILE_FORMAT, migrations.PROFILE)
    assert (old.prefs_import, old.prefs_basis) == (marker, "")


@pytest.mark.parametrize("method", list(MergeMethod))
def test_every_merge_method_round_trips_through_the_real_writer_and_reader(tmp_path, method):
    path = tmp_path / "config.json"
    update_layer(path, Layer, lambda cur: cur.model_copy(update={"prefs": Prefs(merge_method=method)}))
    assert read_layer(path, Layer).prefs.merge_method is method


def test_a_marker_write_keeps_the_latest_profile_version_and_entries(tmp_path):
    store = Store(tmp_path)
    confirmed = ProfileEntry(state="known", value="45", evidence=f"{profile.CONFIRMED}; owner")
    owner = ProfileEntry(state="known", value="--yes", evidence="owner")
    store.write_profile(Profile(version=9, entries={profile.POLL: confirmed, "setup:confirmed-by": owner}))
    stale = Profile(version=0, entries={profile.POLL: confirmed}, prefs_import="")
    real_read, snapshots = store.read_profile, [stale]
    store.read_profile = lambda: snapshots.pop() if snapshots else real_read()  # a stale decision read, then latest
    prefs_import.run(store)
    latest = profile_share.read(store)
    assert latest.prefs_import == "done"
    assert latest.version == 9
    assert latest.entries["setup:confirmed-by"] == owner
    assert store.read_config().prefs.ci_poll_seconds == 45


def test_the_marker_changes_only_when_the_expected_state_is_current(tmp_path):
    store = Store(tmp_path)
    store.write_profile(Profile(version=3, prefs_import="done"))
    state, notice, applied = store.mark_prefs_import("", "pending")
    assert (state, notice, applied) == ("done", "", False)
    assert profile_share.read(store).prefs_import == "done"
    assert profile_share.read(store).version == 3


def test_a_command_line_role_override_publishes_and_a_fresh_clone_reads_it(shared_repo, tmp_path, monkeypatch):
    root, remote = shared_repo
    monkeypatch.setattr(cli.profile, "detect", lambda _r, _g, prev: prev or Profile())
    monkeypatch.setattr(cli.profile, "provider", lambda *_a: SimpleNamespace())
    store = Store(tmp_path / "store", DataRepo(root), "shop-site")
    out = cli.show_profile(store, tmp_path, [], [roles.parse("builder=m-cli:low")])
    assert "Notice:" not in out
    clone = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(clone), "shop-site")
    assert fresh.read_config().agents["builder"].model == "m-cli"


def test_the_profile_command_refuses_a_moved_preference_cleanly_and_records_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.profile, "detect", lambda _r, _g, prev: prev or Profile())
    monkeypatch.setattr(cli.profile, "provider", lambda *_a: SimpleNamespace())
    store = Store(tmp_path)
    args = SimpleNamespace(command="profile", runtime=None, repo=tmp_path, confirm=[(profile.POLL, "99")], role=None)
    assert cli.report(store, args) == 1
    assert "Settings page" in capsys.readouterr().err
    with pytest.raises(ValueError, match="Settings page"):
        cli.show_profile(store, tmp_path, [(profile.POLL, "99")])
    with pytest.raises(ValueError, match="Settings page"):
        profile.confirm(Profile(), profile.WINDOW, "30", datetime.now(UTC))
    assert store.read_profile() is None


@pytest.mark.parametrize(
    ("model", "producer", "reader", "forward"),
    [
        (Layer, 24, 23, migrations.CONFIG),
        (Layer, 23, 22, migrations.CONFIG),
        (Profile, 6, 5, migrations.PROFILE),
        (Profile, 5, 4, migrations.PROFILE),
    ],
    ids=["config-24-reader-23", "config-23-reader-22", "profile-6-reader-5", "profile-5-reader-4"],
)
def test_newer_config_or_profile_payload_is_refused_by_version_gate(model, producer, reader, forward):
    data = Layer(prefs=Prefs(ci_poll_seconds=20)) if model is Layer else Profile()
    raw = data.model_copy(update={"format": producer}).model_dump_json()
    with pytest.raises(FormatTooNewError):
        _parse(raw, model.__name__, model, reader, forward)


def test_an_older_settings_file_keeps_its_data_when_it_migrates_forward():
    old = json.dumps({"format": CONFIG_FORMAT - 1, "widths": [1280, 1600]})
    got = _parse(old, "config", Layer, CONFIG_FORMAT, migrations.CONFIG)
    assert got.format == CONFIG_FORMAT
    assert got.widths == [1280, 1600]
    assert got.prefs is None
    assert got.prefs_imported is False


@pytest.mark.parametrize("action", ["unchanged", "owner-clear"])
def test_refused_import_config_publishes_current_bytes_on_native_retry(shared_repo, tmp_path, monkeypatch, action):
    root, remote = shared_repo
    shared = DataRepo(root)
    store = Store(tmp_path / "store", shared, "shop-site")
    confirmed = ProfileEntry(state="known", value="45", evidence=f"{profile.CONFIRMED}; owner")
    store.write_profile(Profile(entries={profile.POLL: confirmed}))
    real, refused = DataRepo.publish, []

    def refuse_the_config_once(self, path, message, until=None):
        if path == store.config_path and not refused:
            refused.append(message)
            return "remote refused"
        return real(self, path, message, until)

    monkeypatch.setattr(DataRepo, "publish", refuse_the_config_once)
    with pytest.raises(StoreError, match="not published"):
        prefs_import.run(store)
    assert refused
    assert store.read_profile().prefs_import == "pending"
    assert store.read_config().prefs.ci_poll_seconds == 45
    assert store.read_config().prefs_imported is True
    if action == "owner-clear":
        assert (
            store.save(
                store.config_path,
                Layer,
                lambda cur: cur.model_copy(update={"prefs": Prefs(ci_poll_seconds=None), "prefs_imported": True}),
                "owner",
                owner=True,
            )
            == ""
        )
    current = store.config_path.read_bytes()
    retried = Store(store.root, DataRepo(root), store.name)
    prefs_import.run(retried)
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(second), "shop-site")
    assert fresh.config_path.read_bytes() == current
    assert fresh.read_config().prefs.ci_poll_seconds == (45 if action == "unchanged" else None)
    assert fresh.read_profile().prefs_import == "done"


@pytest.mark.parametrize("action", ["blank-delete-recreate", "initially-absent"])
def test_losing_importer_uses_winning_claim_after_absent_or_recreated_config(legacy_store, monkeypatch, action):
    store = legacy_store
    if action == "initially-absent":
        store.config_path.unlink()
    real, interleaved = prefs_import.profile_share.config_digest, []  # the race needs the real digest in between

    def digest_then_a_rival_claims(path):
        seen = real(path)
        if not interleaved:
            interleaved.append(seen)
            store.config_path.unlink(missing_ok=True)
            store.mark_prefs_import("", "pending", prefs_import.ABSENT, "rival")
            if action == "blank-delete-recreate":
                store.config_path.write_text(Layer().model_dump_json(indent=1))
        return seen

    monkeypatch.setattr(prefs_import.profile_share, "config_digest", digest_then_a_rival_claims)
    with pytest.raises(StoreError, match="is incomplete"):
        prefs_import.run(store)
    assert interleaved
    assert (store.read_profile().prefs_import, store.read_profile().prefs_claim) == ("pending", "rival")
    assert store.read_config().prefs is None
    assert store.read_config().prefs_imported is False
    if action == "initially-absent":
        assert interleaved == [prefs_import.ABSENT]
        assert not store.config_path.exists()
