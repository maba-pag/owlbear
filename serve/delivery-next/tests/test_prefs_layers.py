"""Profile preferences (R15, FND-01): layered without code defaults, imported once from the legacy profile."""

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, MachineLayer, Prefs, SettingsUnset, resolve
from owlbear_delivery_next.settings.prefs_import import legacy_values, plan


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


def _owned(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; set by the owner")


def _legacy(**values: str) -> Profile:
    keys = {
        "merge_method": profile.METHOD,
        "delete_remote_branch": profile.DELETE,
        "ci_poll_seconds": profile.POLL,
        "ci_start_window_seconds": profile.WINDOW,
        "ask_before_merge": profile.ASK,
    }
    return Profile(entries={keys[k]: _owned(v) for k, v in values.items()})


@pytest.mark.usefixtures("no_base")
def test_unset_preferences_are_listed_and_refused_never_filled_from_code():
    empty = resolve(None, Layer())
    assert empty.prefs == Prefs()
    assert {f"prefs.{k}" for k in Prefs.model_fields} <= set(empty.missing)
    with pytest.raises(SettingsUnset, match=r"prefs\.merge_method"):
        empty.need("prefs.merge_method")


@pytest.mark.usefixtures("no_base")
def test_project_over_machine_over_global_per_preference():
    glob = GlobalLayer(prefs=Prefs(merge_method=MergeMethod.REBASE, ci_poll_seconds=30, ask_before_merge=False))
    here = MachineLayer(prefs=Prefs(ci_poll_seconds=45))
    project = Layer(prefs=Prefs(merge_method=MergeMethod.SQUASH))
    out = resolve(glob, project, here)
    assert out.prefs == Prefs(
        merge_method=MergeMethod.SQUASH, ci_poll_seconds=45, ask_before_merge=False, delete_remote_branch=None
    )
    assert out.sources["prefs.merge_method"] == "project"
    assert out.sources["prefs.ci_poll_seconds"] == "machine"
    assert out.sources["prefs.ask_before_merge"] == "global"
    assert "prefs.delete_remote_branch" in out.missing
    assert "prefs.ci_poll_seconds" not in out.missing


def test_legacy_import_takes_every_usable_stored_value_whatever_its_evidence():
    prof = _legacy(merge_method="squash", ci_poll_seconds="45")
    prof.entries[profile.DELETE] = ProfileEntry(state="known", value="no", evidence="default")
    got = legacy_values(prof)
    assert got == Prefs(merge_method=MergeMethod.SQUASH, ci_poll_seconds=45, delete_remote_branch=False)


def test_legacy_import_rejects_unusable_values():
    got = legacy_values(_legacy(merge_method="fast-forward", ci_poll_seconds="soon", ask_before_merge="yes"))
    assert got == Prefs(ask_before_merge=True)


def test_plan_fills_only_unset_project_fields_and_new_values_win():
    project = Layer(prefs=Prefs(merge_method=MergeMethod.REBASE))
    filled = plan(project, _legacy(merge_method="squash", delete_remote_branch="yes"))
    assert filled.prefs == Prefs(merge_method=MergeMethod.REBASE, delete_remote_branch=True)


def test_plan_is_empty_without_legacy_confirmations():
    assert plan(Layer(), Profile()).prefs == Prefs()
