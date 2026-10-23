"""Machine settings with a Global layer (D-01M5MZKEPPVMFC9HK795MMG91B): each machine follows Global unless it sets its
own; unset in both is an error, and what needs it does not run. The switch-over moves this machine's into Global."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation, machine_settings, registry, versions
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.settings import carried
from owlbear_delivery_next.settings.config import GlobalLayer, MachineValues
from owlbear_delivery_next.state_store import settings_carry
from owlbear_delivery_next.state_store.store import read_layer

LEGACY = registry.Settings(
    channel="major", update_when_idle=False, update_while_paused=True, curate_after_merge="paused",
    curate_when_idle="off", sessions=3,
)  # fmt: skip


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(machine_settings, "BASE", None)


def _git(root, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def _committed(shared: DataRepo, layer: dict) -> None:
    shared.global_path.write_text(json.dumps(layer))
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "global")


def _carry(monkeypatch, shared: DataRepo | None) -> list[str]:
    monkeypatch.setenv(data_repo.VIEW, str(shared.root) if shared else "")
    said: list[str] = []
    Machine.carry(SimpleNamespace(say=said.append))
    return said


@pytest.mark.usefixtures("no_base")
def test_each_setting_is_this_machine_s_else_global_s_else_unset():
    got = machine_settings.resolve(registry.Settings(sessions=2), MachineValues(channel="major", sessions=6))
    assert (got.channel, got.sessions, got.update_when_idle) == ("major", 2, None)
    assert (got.sources, got.shared["sessions"]) == ({"channel": "global", "sessions": "machine"}, 6)
    assert got.missing == ["update_when_idle", "update_while_paused", "curate_after_merge", "curate_when_idle"]
    assert machine_settings.resolve(registry.Settings(), None).missing == list(machine_settings.FIELDS)


@pytest.mark.usefixtures("no_base")
def test_with_its_settings_unset_nothing_that_needs_them_runs(monkeypatch):
    monkeypatch.setenv(data_repo.VIEW, "")  # no shared repository: no Global either
    with pytest.raises(versions.VersionError, match="unset"):
        versions.target()
    job = curation.Curation(Slots(lambda: 1), shared=lambda: None)
    assert not job.allowed("merge", paused=False)
    assert not job.allowed("idle", paused=False)
    assert Machine._sessions(SimpleNamespace(total=4)) == 0  # noqa: SLF001 - no session starts


@pytest.mark.usefixtures("no_base")
def test_the_switch_over_moves_this_machine_s_settings_into_a_carried_global_and_clears_them(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    old = carried.layer().model_dump(mode="json", exclude={"machine"}) | {"format": 10, "pr_marker": None}
    _committed(shared, old)  # what #604's carry left, with a value the owner cleared since
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))

    said = _carry(monkeypatch, shared)

    glob = read_layer(shared.global_path, GlobalLayer)
    assert glob.machine == MachineValues.model_validate(LEGACY.model_dump())  # this machine's, not the built-in ones
    assert glob.pr_marker is None  # cleared before: never filled again
    assert _git(shared.root, "status", "--porcelain") == ""
    moved = registry.load()
    assert (moved.settings, moved.settings_moved) == (registry.Settings(), True)
    assert any("moved into Global" in line for line in said)
    resolved = machine_settings.current()
    assert (resolved.channel, resolved.sessions, resolved.sources["channel"]) == ("major", 3, "global")

    head = _git(shared.root, "rev-parse", "HEAD")
    assert _carry(monkeypatch, shared) == []  # once
    assert _git(shared.root, "rev-parse", "HEAD") == head


@pytest.mark.usefixtures("no_base")
def test_another_machine_follows_the_global_settings_it_finds(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    settings_carry.carry(shared, MachineValues(sessions=6))  # the first machine's switch-over
    head = _git(shared.root, "rev-parse", "HEAD")
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))  # this machine's own, from before

    _carry(monkeypatch, shared)

    assert _git(shared.root, "rev-parse", "HEAD") == head  # Global stays as it is
    assert registry.load().settings == registry.Settings()
    assert machine_settings.current().sessions == 6


def test_without_a_shared_repository_this_machine_keeps_its_own(monkeypatch):
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))
    assert _carry(monkeypatch, None) == []
    kept = registry.load()
    assert (kept.settings, kept.settings_moved) == (LEGACY, False)


@pytest.mark.usefixtures("no_base")
def test_a_fresh_global_takes_this_machine_s_values_then_the_built_in_ones(shared_repo):
    shared = DataRepo(shared_repo[0])
    settings_carry.carry(shared, MachineValues(sessions=2))
    machine = read_layer(shared.global_path, GlobalLayer).machine
    assert machine == carried.MACHINE.model_copy(update={"sessions": 2})


@pytest.mark.usefixtures("no_base")
def test_a_global_without_machine_settings_takes_this_machine_s_before_it_clears_them(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))  # format 11, no machine section
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))

    _carry(monkeypatch, shared)

    assert read_layer(shared.global_path, GlobalLayer).machine == MachineValues.model_validate(LEGACY.model_dump())
    assert _git(shared.root, "log", "-1", "--format=%s") == settings_carry.MOVED
    assert registry.load().settings_moved


@pytest.mark.usefixtures("no_base")
def test_an_unreadable_global_never_clears_this_machine_s_settings(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(machine=MachineValues(sessions=6)).model_dump(mode="json"))
    shared.global_path.write_text("{ not json")
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))

    said = _carry(monkeypatch, shared)

    kept = registry.load()
    assert (kept.settings, kept.settings_moved) == (LEGACY, False)  # moved at a later start
    assert any("failed" in line for line in said)


@pytest.mark.usefixtures("no_base")
def test_a_global_deleted_after_the_first_carry_gets_only_the_machine_settings(shared_repo):
    shared = DataRepo(shared_repo[0])
    _committed(shared, carried.layer().model_dump(mode="json", exclude={"machine"}) | {"format": 10})
    shared.global_path.unlink()  # the owner's deletion, not committed yet

    settings_carry.carry(shared, MachineValues(sessions=2))

    glob = read_layer(shared.global_path, GlobalLayer)
    assert (glob.machine.sessions, glob.pr_marker, glob.agents) == (2, None, {})  # nothing else comes back
