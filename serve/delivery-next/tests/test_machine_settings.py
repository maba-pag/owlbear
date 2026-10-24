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
    settings_carry.move(shared, MachineValues(sessions=6))  # the first machine's switch-over
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
    settings_carry.carry(shared)
    settings_carry.move(shared, MachineValues(sessions=2))
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

    assert not settings_carry.due(shared)
    settings_carry.move(shared, MachineValues(sessions=2))

    glob = read_layer(shared.global_path, GlobalLayer)
    assert (glob.machine.sessions, glob.pr_marker, glob.agents) == (2, None, {})  # nothing else comes back


@pytest.mark.usefixtures("no_base")
def test_a_move_whose_commit_failed_is_committed_before_this_machine_s_settings_are_cleared(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "publish", lambda *_a: "the commit failed")
        said = _carry(monkeypatch, shared)
    assert any("the commit failed" in line for line in said)
    assert not registry.load().settings_moved  # Global holds them, uncommitted: kept here too

    _carry(monkeypatch, shared)  # the next start: nothing left to copy, the commit made

    assert _git(shared.root, "status", "--porcelain") == ""
    assert json.loads(_git(shared.root, "show", "HEAD:config.json"))["machine"]["sessions"] == LEGACY.sessions
    assert registry.load().settings_moved


@pytest.mark.usefixtures("no_base")
def test_a_machine_starting_after_the_owner_cleared_a_global_value_never_restores_it(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    settings_carry.move(shared, MachineValues(sessions=6))  # the first machine
    cleared = read_layer(shared.global_path, GlobalLayer)
    _committed(shared, cleared.model_copy(update={"machine": cleared.machine.model_copy(update={"sessions": None})})
               .model_dump(mode="json"))  # fmt: skip
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))  # a second machine, with its own from before

    _carry(monkeypatch, shared)

    assert read_layer(shared.global_path, GlobalLayer).machine.sessions is None  # the owner's choice stands
    assert (registry.load().settings_moved, machine_settings.current().sessions) == (True, None)


@pytest.mark.usefixtures("no_base")
def test_a_global_deleted_and_committed_after_a_move_alone_is_never_carried_again(shared_repo):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))  # format 11, never carried
    settings_carry.move(shared, MachineValues(sessions=3))
    shared.global_path.unlink()
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "the owner deletes Global")
    assert not settings_carry.due(shared)


@pytest.mark.usefixtures("no_base")
def test_a_move_that_changes_nothing_is_recorded_so_a_later_machine_copies_nothing(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    full = GlobalLayer(machine=carried.MACHINE)
    shared.global_path.write_text(full.model_dump_json(indent=1))  # as a save writes it: a move changes nothing
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "the owner set every machine value before any move")
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))
    _carry(monkeypatch, shared)
    assert _git(shared.root, "log", "-1", "--format=%s") == settings_carry.MOVED  # an empty commit records it
    assert registry.load().settings_moved

    cleared = full.model_copy(update={"machine": carried.MACHINE.model_copy(update={"sessions": None})})
    _committed(shared, cleared.model_dump(mode="json"))
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))  # another machine
    _carry(monkeypatch, shared)
    assert read_layer(shared.global_path, GlobalLayer).machine.sessions is None


@pytest.mark.usefixtures("no_base")
def test_a_machine_with_a_checkout_from_before_another_s_move_takes_that_move_in(shared_repo, tmp_path, monkeypatch):
    first = DataRepo(shared_repo[0])
    _committed(first, GlobalLayer(sessions=2).model_dump(mode="json"))
    _git(first.root, "push", "-q")
    second = tmp_path / "second"  # another machine's checkout, cloned before the first machine's move
    _git(tmp_path, "clone", "-q", str(shared_repo[1]), str(second))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        _git(second, "config", key, value)
    settings_carry.move(first, MachineValues(sessions=6))  # committed and pushed
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))

    _carry(monkeypatch, DataRepo(second))

    assert _git(second, "status", "--porcelain") == ""
    assert _git(second, "rev-parse", "HEAD") == _git(first.root, "rev-parse", "HEAD")  # nothing filled again
    assert read_layer(DataRepo(second).global_path, GlobalLayer).machine.sessions == 6
    assert registry.load().settings_moved


@pytest.mark.usefixtures("no_base")
def test_a_value_the_owner_saves_before_a_failed_move_is_retried_stays_this_machine_s(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    with registry.locked():
        registry.save(registry.Machine(settings=LEGACY))
    real = settings_carry.move

    def unpushed(repo, local):
        real(repo, local)
        return "committed, but the push failed"

    with monkeypatch.context() as m:
        m.setattr(settings_carry, "move", unpushed)
        _carry(monkeypatch, shared)
    saved = registry.load().settings
    registry.configure(saved.model_copy(update={"sessions": 5}), registry.revision(saved))  # the owner, meanwhile

    _carry(monkeypatch, shared)

    after = registry.load()
    assert (after.settings, after.settings_moved, after.settings_moving) == (registry.Settings(sessions=5), True, None)
    assert read_layer(shared.global_path, GlobalLayer).machine.sessions == LEGACY.sessions  # the move's values
