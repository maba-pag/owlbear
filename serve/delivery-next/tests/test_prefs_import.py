"""The one-time legacy preference import keeps owner clears and never resurrects them (R15, FND-01)."""

import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile, ProfileEntry
from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import config, migrations, profile
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


class FakeStore:
    """The store calls the import makes over a real config file; a publication notice is returned, a failure raised.

    Assigning ``layer`` is an owner edit: it rewrites the file, so the claim's digest no longer matches.
    """

    def __init__(self, marker: str = "", layer: Layer | None = None, *, exists: bool = True) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.config_path = self.root / "config.json"
        self.prof = Profile(
            entries={profile.POLL: ProfileEntry(state="known", value="45", evidence=f"{profile.CONFIRMED}; owner")},
            prefs_import=marker,
        )
        self._layer = Layer()
        if exists or layer is not None:
            self.layer = layer if layer is not None else Layer()
        self.fills = 0
        self.publishes = 0
        self.stale_layer: Layer | None = None  # what a read taken before the owner's clear returns
        self.notices: list[str] = []  # queued publication notices, one per call
        self.raise_next = False

    @property
    def layer(self) -> Layer:
        return self._layer

    @layer.setter
    def layer(self, value: Layer) -> None:
        self._layer = value
        self.config_path.write_text(value.model_dump_json(indent=1))

    def delete_config(self) -> None:
        self.config_path.unlink(missing_ok=True)
        self._layer = Layer()

    def read_profile(self) -> Profile:
        return self.prof

    def write_profile(self, prof: Profile) -> str:
        self.prof = prof
        return self.notices.pop(0) if self.notices else ""

    def mark_prefs_import(self, expect: str, to: str, basis: str = "") -> tuple[str, str, bool]:
        if self.prof.prefs_import != expect:
            return self.prof.prefs_import, "", False
        update = {"prefs_import": to, "prefs_basis": basis if to == "pending" else ""}
        self.prof = self.prof.model_copy(update=update)
        return to, self.notices.pop(0) if self.notices else "", True

    def read_config(self) -> Layer:
        return self.stale_layer if self.stale_layer is not None else self.layer

    def update_config(self, change, what: str = "") -> str:  # noqa: ARG002 - the store's signature
        if self.raise_next:
            self.raise_next = False
            msg = "publish failed"
            raise OSError(msg)
        self.layer = change(self.layer)
        self.fills += 1
        self.publishes += 1
        return self.notices.pop(0) if self.notices else ""


@pytest.fixture(autouse=True)
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


def test_the_import_runs_once_and_marks_the_profile_done():
    store = FakeStore()
    prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds == 45
    assert store.layer.prefs_imported is True
    assert store.prof.prefs_import == "done"
    prefs_import.run(store)
    assert store.fills == 1


def test_a_claim_is_durable_before_the_fill_so_a_config_deletion_cannot_refill():
    store = FakeStore()
    seen: list[str] = []
    original = store.update_config

    def fill_then_delete(change, what=""):
        seen.append(store.prof.prefs_import)  # the claim must already be on disk
        out = original(change, what)
        store.layer = Layer()  # the owner deletes the config between fill and completion
        return out

    store.update_config = fill_then_delete
    prefs_import.run(store)
    assert seen == ["pending"]
    assert store.prof.prefs_import == "done"
    assert store.layer.prefs is None  # the deleted config is not refilled on the next run
    prefs_import.run(store)
    assert store.layer.prefs is None


def test_a_failed_publication_notice_raises_and_a_retry_publishes_without_refilling_clears():
    store = FakeStore()
    store.notices = ["", "remote refused"]  # the claim publishes; the fill's publication is refused
    with pytest.raises(StoreError, match="not published"):
        prefs_import.run(store)
    assert store.prof.prefs_import == "pending"  # the local fill stays; the retry must not refill it
    store.layer = store.layer.model_copy(update={"prefs": Prefs(ci_poll_seconds=None), "prefs_imported": True})
    prefs_import.run(store)  # the owner cleared the value before the retry
    assert store.layer.prefs.ci_poll_seconds is None
    assert store.prof.prefs_import == "done"


def test_a_raised_fill_failure_keeps_the_claim_so_a_retry_fills_only_the_unchanged_config():
    store = FakeStore()
    store.raise_next = True
    with pytest.raises(OSError, match="publish failed"):
        prefs_import.run(store)
    assert store.prof.prefs_import == "pending"
    assert store.prof.prefs_basis != ""
    prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds == 45
    assert store.prof.prefs_import == "done"


def test_a_crash_after_the_claim_and_before_the_fill_resumes_when_the_config_is_unchanged():
    store = FakeStore()
    store.update_config = _crash
    with pytest.raises(KeyboardInterrupt):
        prefs_import.run(store)
    assert store.prof.prefs_import == "pending"
    assert store.prof.prefs_basis != ""
    del store.update_config  # the next process has the real store again
    prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds == 45
    assert store.prof.prefs_import == "done"


def _crash(*_args, **_kwargs):
    raise KeyboardInterrupt  # stands in for the process dying mid-step


def test_a_crash_after_the_claim_with_an_owner_edit_stays_pending_and_is_not_refilled():
    store = FakeStore()
    store.update_config = _crash
    with pytest.raises(KeyboardInterrupt):
        prefs_import.run(store)
    del store.update_config
    store.layer = Layer(prefs=Prefs(ci_poll_seconds=30))  # the owner edited the project layer before the resume
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert store.prof.prefs_import == "pending"
    assert store.layer.prefs.ci_poll_seconds == 30
    assert store.layer.prefs_imported is False


def test_a_crash_after_the_claim_with_no_config_at_claim_stays_pending_and_creates_nothing():
    store = FakeStore(exists=False)
    store.update_config = _crash
    with pytest.raises(KeyboardInterrupt):
        prefs_import.run(store)
    del store.update_config
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert store.prof.prefs_import == "pending"
    assert not store.config_path.exists()


def test_a_config_deleted_between_the_claim_and_the_fill_is_not_recreated_and_stays_pending():
    store = FakeStore()
    original = store.update_config

    def delete_then_fill(change, what=""):
        store.delete_config()  # the owner deletes the config in the claim-to-fill window
        return original(change, what)

    store.update_config = delete_then_fill
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert not store.config_path.exists()
    assert store.prof.prefs_import == "pending"
    del store.update_config
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert not store.config_path.exists()


def test_an_owner_clear_between_the_claim_and_the_fill_is_not_refilled():
    store = FakeStore()
    original = store.update_config

    def clear_then_fill(change, what=""):
        store.layer = Layer(prefs=Prefs(ci_poll_seconds=None))  # the owner clears it before the fill
        return original(change, what)

    store.update_config = clear_then_fill
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds is None
    assert store.prof.prefs_import == "pending"


def test_a_crash_after_the_fill_landed_completes_without_refilling_an_owner_clear():
    store = FakeStore()
    original_mark = store.mark_prefs_import

    def crash_before_done(expect, to, basis=""):
        if to == "done":
            raise KeyboardInterrupt
        return original_mark(expect, to, basis)

    store.mark_prefs_import = crash_before_done
    with pytest.raises(KeyboardInterrupt):
        prefs_import.run(store)
    assert store.prof.prefs_import == "pending"
    assert store.layer.prefs_imported is True
    del store.mark_prefs_import
    store.layer = Layer(prefs=Prefs(ci_poll_seconds=None), prefs_imported=True)  # the owner clear survives
    prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds is None
    assert store.prof.prefs_import == "done"


def test_a_profile_format_three_claim_without_a_basis_does_not_fill_on_resume():
    store = FakeStore(marker="pending")
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert store.layer.prefs is None
    assert store.prof.prefs_import == "pending"


def test_a_cloned_repo_whose_config_already_carries_the_import_is_not_refilled():
    store = FakeStore(layer=Layer(prefs=Prefs(ci_poll_seconds=None), prefs_imported=True))
    prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds is None  # the cleared value stays cleared
    assert store.prof.prefs_import == "done"


def test_the_source_profile_entries_are_kept_after_the_import():
    store = FakeStore()
    prefs_import.run(store)
    assert profile.POLL in store.prof.entries


def test_an_older_settings_file_migrates_forward_with_every_preference_unset():
    import json  # noqa: PLC0415

    from owlbear_delivery_next.settings import migrations  # noqa: PLC0415
    from owlbear_delivery_next.settings.config import CONFIG_FORMAT  # noqa: PLC0415
    from owlbear_delivery_next.state_store.store import _parse  # noqa: PLC0415

    old = json.dumps({"format": CONFIG_FORMAT - 1})
    got = _parse(old, "config", Layer, CONFIG_FORMAT, migrations.CONFIG)
    assert got.format == CONFIG_FORMAT
    assert got.prefs is None
    assert got.prefs_imported is False


def test_a_newer_settings_file_is_refused_not_read():
    import json  # noqa: PLC0415

    from owlbear_delivery_next.settings import migrations  # noqa: PLC0415
    from owlbear_delivery_next.settings.config import CONFIG_FORMAT  # noqa: PLC0415
    from owlbear_delivery_next.state_store.database import FormatTooNewError  # noqa: PLC0415
    from owlbear_delivery_next.state_store.store import _parse  # noqa: PLC0415

    with pytest.raises(FormatTooNewError):
        _parse(json.dumps({"format": CONFIG_FORMAT + 1}), "config", Layer, CONFIG_FORMAT, migrations.CONFIG)


def test_an_older_profile_migrates_forward_unmarked():
    import json  # noqa: PLC0415

    from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT  # noqa: PLC0415
    from owlbear_delivery_next.settings import migrations  # noqa: PLC0415
    from owlbear_delivery_next.state_store.store import _parse  # noqa: PLC0415

    got = _parse(json.dumps({"format": PROFILE_FORMAT - 1}), "profile", Profile, PROFILE_FORMAT, migrations.PROFILE)
    assert got.prefs_import == ""


def test_a_format_three_claim_migrates_without_a_basis_and_a_newer_profile_is_refused():
    raw = json.dumps({"format": 3, "prefs_import": "pending"})
    old = _parse(raw, "profile", Profile, PROFILE_FORMAT, migrations.PROFILE)
    assert (old.prefs_import, old.prefs_basis) == ("pending", "")
    with pytest.raises(FormatTooNewError):
        _parse(json.dumps({"format": PROFILE_FORMAT + 1}), "profile", Profile, PROFILE_FORMAT, migrations.PROFILE)


@pytest.mark.parametrize("method", list(MergeMethod))
def test_every_merge_method_round_trips_through_the_real_writer_and_reader(tmp_path, method):
    path = tmp_path / "config.json"
    update_layer(path, Layer, lambda cur: cur.model_copy(update={"prefs": Prefs(merge_method=method)}))
    assert read_layer(path, Layer).prefs.merge_method is method


@pytest.mark.parametrize("method", list(MergeMethod))
def test_every_merge_method_parses_from_the_written_json(method):
    raw = Layer(prefs=Prefs(merge_method=method)).model_dump_json()
    got = _parse(raw, "config", Layer, CONFIG_FORMAT, migrations.CONFIG)
    assert got.prefs.merge_method is method


def test_a_retry_after_a_failed_config_publication_publishes_the_current_config():
    store = FakeStore()
    store.notices = ["", "remote refused", ""]  # claim published; config publication refused, then accepted
    with pytest.raises(StoreError, match="not published"):
        prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds == 45  # applied locally
    prefs_import.run(store)
    assert store.publishes == 2  # the retry publishes the config again, not only the marker
    assert store.prof.prefs_import == "done"


def test_a_delayed_import_that_read_a_stale_layer_cannot_restore_a_cleared_value():
    store = FakeStore(layer=Layer(prefs=Prefs(ci_poll_seconds=None), prefs_imported=True))
    store.stale_layer = Layer()  # the import's earlier check saw an unimported layer
    prefs_import.run(store)
    assert store.layer.prefs.ci_poll_seconds is None
    assert store.prof.prefs_import == "done"


def test_a_config_deleted_after_a_pending_fill_is_not_refilled_on_retry():
    store = FakeStore()
    store.notices = ["", "remote refused"]
    with pytest.raises(StoreError, match="not published"):
        prefs_import.run(store)
    store.delete_config()  # the owner deletes the settings file before the retry
    with pytest.raises(StoreError, match="incomplete"):
        prefs_import.run(store)
    assert store.layer.prefs is None
    assert store.prof.prefs_import == "pending"


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


def test_a_moved_preference_cannot_be_confirmed_on_the_command_line(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.profile, "detect", lambda _r, _g, prev: prev or Profile())
    monkeypatch.setattr(cli.profile, "provider", lambda *_a: SimpleNamespace())
    store = Store(tmp_path)
    with pytest.raises(ValueError, match="Settings page"):
        cli.show_profile(store, tmp_path, [(profile.POLL, "99")])
    with pytest.raises(ValueError, match="Settings page"):
        profile.confirm(Profile(), profile.WINDOW, "30", datetime.now(UTC))


def test_the_profile_command_refuses_a_moved_preference_cleanly_and_records_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.profile, "detect", lambda _r, _g, prev: prev or Profile())
    monkeypatch.setattr(cli.profile, "provider", lambda *_a: SimpleNamespace())
    store = Store(tmp_path)
    args = SimpleNamespace(command="profile", runtime=None, repo=tmp_path, confirm=[(profile.POLL, "99")], role=None)
    assert cli.report(store, args) == 1
    assert "Settings page" in capsys.readouterr().err
    assert store.read_profile() is None


def test_a_newer_settings_or_profile_format_is_refused_by_the_previous_reader():
    raw = Layer(prefs=Prefs(ci_poll_seconds=20)).model_dump_json()
    with pytest.raises(FormatTooNewError):
        _parse(raw, "config", Layer, CONFIG_FORMAT - 1, migrations.CONFIG)
    with pytest.raises(FormatTooNewError):
        _parse(Profile().model_dump_json(), "profile", Profile, PROFILE_FORMAT - 1, migrations.PROFILE)


def test_an_older_settings_file_keeps_its_data_when_it_migrates_forward():
    old = json.dumps({"format": CONFIG_FORMAT - 1, "widths": [1280, 1600]})
    got = _parse(old, "config", Layer, CONFIG_FORMAT, migrations.CONFIG)
    assert got.widths == [1280, 1600]
    assert got.prefs is None


def test_a_refused_config_publication_is_published_on_retry_so_a_fresh_clone_gets_the_import(
    shared_repo, tmp_path, monkeypatch
):
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
    prefs_import.run(store)  # the retry republishes the config the claim left local
    second = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(remote), str(second)], check=True, capture_output=True)  # noqa: S603, S607
    fresh = Store(tmp_path / "fresh-store", DataRepo(second), "shop-site")
    assert fresh.read_config().prefs.ci_poll_seconds == 45
    assert fresh.read_profile().prefs_import == "done"


def test_a_losing_importer_whose_digest_predates_a_delete_and_recreate_resumes_only_from_the_winning_claim(monkeypatch):
    store = FakeStore(layer=Layer())
    real, interleaved = prefs_import.profile_share.config_digest, []  # the race needs the real digest in between

    def digest_then_a_rival_claims(path):
        seen = real(path)
        if not interleaved:
            interleaved.append(seen)
            store.delete_config()
            store.mark_prefs_import("", "pending", prefs_import.ABSENT)  # the rival claims, then crashes
            store.layer = Layer()  # the owner recreates a blank config
        return seen

    monkeypatch.setattr(prefs_import.profile_share, "config_digest", digest_then_a_rival_claims)
    with pytest.raises(StoreError, match="is incomplete"):
        prefs_import.run(store)
    assert interleaved
    assert store.read_profile().prefs_import == "pending"
    assert store.fills == 0
    assert store.layer.prefs is None


def test_two_importers_on_an_absent_config_the_loser_leaves_it_pending_and_never_creates_it(monkeypatch):
    store = FakeStore(exists=False)
    real, interleaved = prefs_import.profile_share.config_digest, []  # the race needs the real digest in between

    def digest_then_the_winner_claims_and_crashes(path):
        seen = real(path)
        if not interleaved:
            interleaved.append(seen)
            store.mark_prefs_import("", "pending", prefs_import.ABSENT)  # the winner claims, then crashes before fill
        return seen

    monkeypatch.setattr(prefs_import.profile_share, "config_digest", digest_then_the_winner_claims_and_crashes)
    with pytest.raises(StoreError, match="is incomplete"):
        prefs_import.run(store)
    assert interleaved == [prefs_import.ABSENT]
    assert store.read_profile().prefs_import == "pending"
    assert not store.config_path.exists()
    assert store.fills == 0
