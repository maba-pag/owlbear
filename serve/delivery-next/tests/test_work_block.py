"""The rule that no work starts for a project while a setting it reads is unset or unreadable."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import stop_routes
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import machine_settings, registry, work_block
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.state_store.work_block import UNREADABLE, Block

if TYPE_CHECKING:
    from pathlib import Path

GAP = "prefs.ci_poll_seconds"
INTERVALS = ("update_check_hours_owlbear", "update_check_hours_pds", "update_check_hours_impeccable")


@pytest.fixture
def poll_unset(monkeypatch):
    """No layer under the project sets the CI poll interval."""
    prefs = config.BASE.prefs.model_copy(update={"ci_poll_seconds": None})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"prefs": prefs}))


@pytest.fixture
def store(tmp_path: Path) -> Store:
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    return Store.open(tmp_path)


def polls(store: Store, seconds: int) -> None:
    prefs = Prefs(ci_poll_seconds=seconds)
    assert (
        store.save(store.config_path, Layer, lambda layer: layer.model_copy(update={"prefs": prefs}), "t", owner=True)
        == ""
    )


def hours(**each: int) -> None:
    with registry.locked():
        saved = registry.load()
        saved.settings = saved.settings.model_copy(update={f"update_check_hours_{n}": h for n, h in each.items()})
        registry.save(saved)


@pytest.mark.usefixtures("poll_unset", "intervals_unset")
def test_a_project_waits_for_its_own_unset_setting_and_this_machine_s_intervals_and_each_set_value_lifts_it(store):
    machine = ("machine.update_check_hours_owlbear", "machine.update_check_hours_pds",
               "machine.update_check_hours_impeccable")  # fmt: skip
    block = work_block.of_store(store)
    assert (block.keys, block.reason, bool(block)) == ((GAP, *machine), "", True)
    assert block.text() == f"settings unset: {', '.join((GAP, *machine))}; fill them in on the Settings page"
    polls(store, 20)
    assert work_block.of_store(store).keys == machine
    hours(owlbear=6, pds=3)
    assert work_block.of_store(store).keys == ("machine.update_check_hours_impeccable",)
    hours(impeccable=24)
    assert (work_block.of_store(store), work_block.of_store(store).text()) == (Block(), "")


@pytest.mark.usefixtures("poll_unset")
def test_no_shared_repository_is_no_block_but_an_unreadable_layer_blocks_with_why_first(store):
    assert work_block.machine() == Block()  # tests run without a shared repository
    store.config_path.write_text("{not json")
    block = work_block.of_store(store, Block(("machine.channel",)))
    assert (block.keys, block.text()) == (("machine.channel",), f"{UNREADABLE}state of config is unreadable")
    (local_home.root() / registry.MACHINE).write_text("{not json")
    assert work_block.machine().reason.endswith("is unreadable: Invalid JSON: key must be a string at line 1 column 2")


@pytest.mark.usefixtures("poll_unset")
def test_an_unregistered_folder_reads_global_its_own_layer_and_this_machine(tmp_path: Path, shared_repo):
    shared = DataRepo(shared_repo[0])
    assert work_block.of_folder(shared, "shop-site").keys == (GAP,)
    polls(Store(tmp_path / "shop", shared, "shop-site"), 20)
    assert work_block.of_folder(shared, "shop-site") == Block()
    assert work_block.of_folder(shared, "other-site").keys == (GAP,)


@pytest.mark.parametrize("interval", INTERVALS)
def test_each_update_check_interval_alone_blocks_every_project(store, monkeypatch, interval):
    monkeypatch.setattr(machine_settings, "BASE", machine_settings.BASE.model_copy(update={interval: None}))
    assert (store.settings().missing, work_block.of_store(store).keys) == ([], (f"machine.{interval}",))


@pytest.mark.usefixtures("poll_unset")
def test_the_rerun_texts_of_a_stop_are_unchanged(store):
    assert stop_routes.unset(store) == (
        f"Settings unset: {GAP}; fill them in on the Settings page to run the step again"
    )
    store.config_path.write_text("{not json")
    assert stop_routes.unset(store) == (
        "The settings can't be read (state of config is unreadable); "
        "fix them on the Settings page to run the step again"
    )


def test_an_unreadable_global_blocks_with_its_reason_though_this_machine_sets_all(
    tmp_path: Path, shared_repo, monkeypatch
):
    shared = DataRepo(shared_repo[0])
    monkeypatch.setattr(data_repo, "locate", lambda: shared)
    registered = Store(tmp_path / "shop", shared, "shop-site")
    assert work_block.of_folder(shared, "shop-site") == work_block.of_store(registered) == Block()
    assert work_block.of_folder(shared, "other-site") == work_block.of_settings(work_block.outside(shared))
    shared.global_path.write_text("{ not json")
    resolved = machine_settings.current()
    assert (resolved.missing, resolved.notice.startswith("the global settings are unreadable: ")) == ([], True)
    assert work_block.machine() == Block(reason=resolved.notice)
    assert work_block.of_store(registered).reason.startswith("state of config is unreadable; the global settings")
