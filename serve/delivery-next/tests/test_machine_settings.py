"""Machine settings with a Global layer (D-01M5MZKEPPVMFC9HK795MMG91B): each machine follows Global unless it sets its
own; unset in both is an error, and what needs it does not run. Each machine's first start moves its own settings into
Global once (the owner, 2026-10-23: move all), on a current checkout, keeping its progress when publishing fails."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation, versions
from owlbear_delivery_next.machine_host.auto_update import Auto
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.settings import carried
from owlbear_delivery_next.settings.config import GlobalLayer, MachineValues
from owlbear_delivery_next.state_store import machine_settings, registry, settings_carry
from owlbear_delivery_next.state_store.store import read_layer

LEGACY = registry.Settings(
    channel="major", update_when_idle=False, update_while_paused=True, curate_after_merge="paused",
    curate_when_idle="off", sessions=3,
)  # fmt: skip


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(machine_settings, "BASE", None)


def _git(root, *args: str) -> str:
    if (Path(root) / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def _committed(shared: DataRepo, layer: dict, *, push: bool = True) -> None:
    shared.global_path.write_text(json.dumps(layer))
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "global")
    if push:
        _git(shared.root, "push", "-q")


def _clone(tmp_path, shared_repo) -> DataRepo:
    """Another machine's checkout of the shared repository."""
    second = tmp_path / "second"
    _git(tmp_path, "clone", "-q", str(shared_repo[1]), str(second))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        _git(second, "config", key, value)
    return DataRepo(second)


def _staged_only(repo: DataRepo, path, _message: str, _until: float | None = None) -> str:
    """``DataRepo.commit`` failing after it staged the file."""
    _git(repo.root, "add", "--", path.relative_to(repo.root).as_posix())
    return "the commit failed"


def _local(settings: registry.Settings = LEGACY) -> None:
    with registry.locked():
        registry.save(registry.Machine(settings=settings))


def _carry(monkeypatch, shared: DataRepo | None) -> list[str]:
    """One machine host start's carry; what it said."""
    monkeypatch.setenv(data_repo.VIEW, str(shared.root) if shared else "")
    said: list[str] = []
    host = SimpleNamespace(say=said.append)
    host._pending = lambda why: Machine._pending(host, why)  # noqa: SLF001
    Machine.carry(host)
    return said


def _done() -> bool:
    machine = registry.load()
    return machine.settings_moved and not machine.settings_pending


@pytest.mark.usefixtures("no_base")
def test_each_setting_is_this_machine_s_else_global_s_else_unset():
    got = machine_settings.resolve(registry.Settings(sessions=2), MachineValues(channel="major", sessions=6))
    assert (got.channel, got.sessions, got.update_when_idle) == ("major", 2, None)
    assert (got.sources, got.shared["sessions"]) == ({"channel": "global", "sessions": "machine"}, 6)
    assert got.missing == ["update_when_idle", "update_while_paused", "curate_after_merge", "curate_when_idle",
                           "retro_run_credit_limit", "replay_run_credit_limit", "retro_after_change",
                           "retro_when_idle", "enrolled_chats", "update_check_hours_owlbear", "update_check_hours_pds",
                           "update_check_hours_impeccable"]  # fmt: skip
    chats = machine_settings.resolve(registry.Settings(enrolled_chats=[]), None)
    assert (chats.enrolled_chats, "enrolled_chats" in chats.missing) == ([], False)  # none enrolled is set, not unset
    assert machine_settings.resolve(registry.Settings(), None).missing == list(machine_settings.FIELDS)


@pytest.mark.usefixtures("no_base")
def test_each_update_check_interval_resolves_on_its_own_and_an_unset_one_is_listed():
    """D-01M63CCVRK8ZKFENY9F4A2K11A: three intervals, each this machine's else Global's; none set is unset."""
    hours = ("update_check_hours_owlbear", "update_check_hours_pds", "update_check_hours_impeccable")
    glob = MachineValues(update_check_hours_owlbear=6, update_check_hours_pds=12, update_check_hours_impeccable=24)
    got = machine_settings.resolve(registry.Settings(update_check_hours_pds=3), glob)
    assert [getattr(got, h) for h in hours] == [6, 3, 24]
    assert [got.sources[h] for h in hours] == ["global", "machine", "global"]
    assert not set(hours) & set(got.missing)
    partial = machine_settings.resolve(registry.Settings(), MachineValues(update_check_hours_pds=12))
    assert ([h for h in hours if h in partial.missing], partial.update_check_hours_pds) == ([hours[0], hours[2]], 12)


@pytest.mark.usefixtures("no_base")
def test_with_its_settings_unset_nothing_that_needs_them_runs(monkeypatch):
    monkeypatch.setenv(data_repo.VIEW, "")  # no shared repository: no Global either
    with pytest.raises(versions.VersionError, match="unset"):
        versions.target()
    job = curation.Curation(Slots(lambda: 1), shared=lambda: None, paused=lambda: False)
    assert not job.allowed("merge")
    assert not job.allowed("idle")
    assert Machine._sessions(SimpleNamespace(total=4)) == 0  # noqa: SLF001 - no session starts
    assert not Auto.permitted(SimpleNamespace(machine=SimpleNamespace(paused=False)))  # never updates by itself


@pytest.mark.usefixtures("no_base")
def test_the_switch_over_moves_this_machine_s_settings_into_a_carried_global_and_clears_them(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    old = carried.layer().model_dump(mode="json", exclude={"machine", "machine_moved"}) | {"format": 10}
    _committed(shared, old | {"pr_marker": None})  # what #604's carry left, with a value the owner cleared since
    _local()

    said = _carry(monkeypatch, shared)

    glob = read_layer(shared.global_path, GlobalLayer)
    limits = {"retro_run_credit_limit": 20.0, "replay_run_credit_limit": 90.0}  # format 16's, written into Global
    assert (glob.machine, glob.machine_moved) == (MachineValues.model_validate(LEGACY.model_dump() | limits), True)
    assert glob.pr_marker is None  # cleared before: never filled again
    assert _git(shared.root, "status", "--porcelain") == ""
    assert _git(shared.root, "rev-parse", "HEAD") == _git(shared_repo[1], "rev-parse", "HEAD")  # published
    assert (registry.load().settings, _done()) == (registry.Settings(), True)
    assert any("moved into Global" in line for line in said)
    resolved = machine_settings.current()
    assert (resolved.channel, resolved.sessions, resolved.sources["channel"]) == ("major", 3, "global")

    head = _git(shared.root, "rev-parse", "HEAD")
    assert _carry(monkeypatch, shared) == []  # once
    assert _git(shared.root, "rev-parse", "HEAD") == head


@pytest.mark.usefixtures("no_base")
def test_a_later_machine_copies_nothing_and_a_value_the_owner_cleared_stays_cleared(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _local(registry.Settings(sessions=6))
    _carry(monkeypatch, shared)  # the first machine
    glob = read_layer(shared.global_path, GlobalLayer)
    cleared = glob.model_copy(update={"machine": glob.machine.model_copy(update={"sessions": None})})
    _committed(shared, cleared.model_dump(mode="json"))  # the owner clears it on the Settings page
    head = _git(shared.root, "rev-parse", "HEAD")
    _local()  # another machine, with its own from before

    _carry(monkeypatch, shared)

    assert _git(shared.root, "rev-parse", "HEAD") == head  # Global stays as it is
    assert (registry.load().settings, _done(), machine_settings.current().sessions) == (registry.Settings(), True, None)


def test_without_a_shared_repository_this_machine_keeps_its_own(monkeypatch):
    _local()
    assert _carry(monkeypatch, None) == []
    kept = registry.load()
    assert (kept.settings, kept.settings_moved) == (LEGACY, False)


@pytest.mark.usefixtures("no_base")
def test_a_fresh_global_takes_this_machine_s_values_then_the_built_in_ones(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _local(registry.Settings(sessions=2))
    _carry(monkeypatch, shared)
    glob = read_layer(shared.global_path, GlobalLayer)
    assert glob.machine == carried.MACHINE.model_copy(update={"sessions": 2})
    assert glob.agents  # #604's carry ran first
    assert _done()


@pytest.mark.usefixtures("no_base")
def test_an_unreadable_global_never_counts_as_moved_and_the_page_says_why(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(machine=MachineValues(sessions=6)).model_dump(mode="json"))
    shared.global_path.write_text("{ not json")
    _local()

    _carry(monkeypatch, shared)

    kept = registry.load()
    assert (kept.settings, kept.settings_moved) == (LEGACY, False)  # moved at a later start
    assert "not saved" in kept.settings_pending  # an edit the owner has not saved: his to save or undo


@pytest.mark.usefixtures("no_base")
def test_a_move_keeps_its_progress_when_its_commit_fails_and_publishes_it_at_the_next_start(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))
    (shared.root / "elsewhere.txt").write_text("the owner's")
    _git(shared.root, "add", "elsewhere.txt")  # unrelated staged work
    _local()
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", _staged_only)
        _carry(monkeypatch, shared)
    assert "the commit failed" in registry.load().settings_pending
    assert not registry.load().settings_moved  # its own values stay until the move is published
    assert read_layer(shared.global_path, GlobalLayer).machine_moved  # filled and marked: never filled again
    glob = read_layer(shared.global_path, GlobalLayer)
    shared.global_path.write_text(glob.model_copy(update={"machine": glob.machine.model_copy(
        update={"sessions": None})}).model_dump_json())  # fmt: skip
    assert not shared.commit(shared.global_path, "settings: global")  # the owner clears one with a Settings save

    _carry(monkeypatch, shared)

    assert _done()
    assert json.loads(_git(shared.root, "show", "HEAD:config.json"))["machine"]["sessions"] is None
    assert _git(shared.root, "status", "--porcelain") == "A  elsewhere.txt"  # the owner's staged work, untouched
    assert _git(shared.root, "show", "--name-only", "--format=", "HEAD") == "config.json"  # the move commits Global


@pytest.mark.usefixtures("no_base")
def test_a_move_whose_push_fails_keeps_its_commit_and_pushes_it_at_the_next_start(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))
    _local()
    _git(shared.root, "remote", "set-url", "--push", "origin", str(shared.root / "nowhere"))
    _carry(monkeypatch, shared)
    assert registry.load().settings_pending
    assert not registry.load().settings_moved
    assert _git(shared.root, "log", "-1", "--format=%s") == settings_carry.MOVED  # kept, not undone
    saved = registry.load().settings
    registry.configure(saved.model_copy(update={"sessions": 5}), registry.revision(saved))  # the owner, meanwhile
    _git(shared.root, "remote", "set-url", "--push", "origin", str(shared_repo[1]))

    _carry(monkeypatch, shared)

    assert _git(shared.root, "rev-parse", "HEAD") == _git(shared_repo[1], "rev-parse", "HEAD")
    assert (registry.load().settings, _done()) == (registry.Settings(sessions=5), True)  # his own value stays
    assert read_layer(shared.global_path, GlobalLayer).machine.sessions == LEGACY.sessions  # the move's values


@pytest.mark.usefixtures("no_base")
def test_an_owner_edit_never_gives_way(shared_repo, tmp_path, monkeypatch):
    first = DataRepo(shared_repo[0])
    _committed(first, GlobalLayer(sessions=2).model_dump(mode="json"))
    second = _clone(tmp_path, shared_repo)
    settings_carry.move(first, MachineValues(sessions=6))
    edited = GlobalLayer(sessions=9).model_dump_json()
    second.global_path.write_text(edited)  # the owner's unsaved edit in the stale checkout
    _local()

    _carry(monkeypatch, second)

    assert second.global_path.read_text() == edited
    assert "not saved" in registry.load().settings_pending
    assert not registry.load().settings_moved


@pytest.mark.usefixtures("no_base")
def test_a_failed_git_probe_never_counts_as_done(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))
    _local()
    head = _git(shared.root, "rev-parse", "HEAD")
    real = DataRepo.git
    for probe in ("fetch", "status", "rev-list"):
        with monkeypatch.context() as m:
            m.setattr(DataRepo, "git", lambda self, *a, until=None, p=probe: real(self, *a, until=until)
                      if a[0] != p else subprocess.CompletedProcess(a, 128, "", "broken"))  # fmt: skip
            _carry(monkeypatch, shared)
        assert (registry.load().settings_moved, _git(shared.root, "rev-parse", "HEAD")) == (False, head), probe
        assert "broken" in registry.load().settings_pending, probe


@pytest.mark.usefixtures("no_base")
def test_a_failed_sync_stops_the_carry_before_it_writes(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, {"format": 2, "agents": {}, "runtimes": {}})  # the carry is due
    _local()
    _git(shared.root, "remote", "set-url", "origin", str(shared.root / "nowhere"))  # fetch fails
    _carry(monkeypatch, shared)
    assert json.loads(shared.global_path.read_text())["format"] == 2
    assert "git fetch failed" in registry.load().settings_pending


@pytest.mark.usefixtures("no_base")
def test_a_checkout_with_a_remote_but_no_upstream_keeps_everything_pending(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _git(shared.root, "branch", "--unset-upstream")
    _local()
    _carry(monkeypatch, shared)
    assert "tracks no upstream" in registry.load().settings_pending
    assert (registry.load().settings_moved, shared.global_path.exists()) == (False, False)


@pytest.mark.usefixtures("no_base")
def test_a_global_deleted_after_a_move_stays_deleted_and_an_uncommitted_deletion_waits(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _local(registry.Settings(sessions=3))
    _carry(monkeypatch, shared)  # carried and moved
    shared.global_path.unlink()  # the owner deletes Global, not committed yet
    assert not settings_carry.due(shared)
    assert "not saved" in settings_carry.move(shared, MachineValues(sessions=2))
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "the owner deletes Global")
    _git(shared.root, "push", "-q")
    _local(registry.Settings(sessions=4))  # another machine
    _carry(monkeypatch, shared)
    assert (shared.global_path.exists(), _done()) == (False, True)


@pytest.mark.usefixtures("no_base")
def test_a_checkout_from_before_another_machine_s_carry_takes_it_in_before_writing(shared_repo, tmp_path, monkeypatch):
    first = DataRepo(shared_repo[0])
    _committed(first, {"format": 2, "agents": {}, "runtimes": {}})  # an old Global
    second = _clone(tmp_path, shared_repo)
    _local()
    _carry(monkeypatch, first)  # the first machine's carry and move, pushed
    _local()

    said = _carry(monkeypatch, second)

    assert not any("carried into Global" in line for line in said)  # it took the first's in: no carry of its own
    assert _git(second.root, "rev-parse", "HEAD") == _git(first.root, "rev-parse", "HEAD")
    assert (_git(second.root, "status", "--porcelain"), _done()) == ("", True)


@pytest.mark.usefixtures("no_base")
def test_a_global_deleted_after_an_unpushed_move_stays_pending_until_both_are_pushed(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))
    _local()
    _git(shared.root, "remote", "set-url", "--push", "origin", str(shared.root / "nowhere"))
    _carry(monkeypatch, shared)  # the move commits, its push fails
    shared.global_path.unlink()
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "the owner deletes Global")

    _carry(monkeypatch, shared)  # still no push
    assert (shared.global_path.exists(), registry.load().settings, _done()) == (False, LEGACY, False)

    _git(shared.root, "remote", "set-url", "--push", "origin", str(shared_repo[1]))
    _carry(monkeypatch, shared)
    assert _git(shared.root, "rev-parse", "HEAD") == _git(shared_repo[1], "rev-parse", "HEAD")
    assert (shared.global_path.exists(), _done()) == (False, True)


@pytest.mark.usefixtures("no_base")
@pytest.mark.parametrize("moved", [False, True])
def test_an_unsaved_owner_edit_of_global_is_never_published_by_the_carry_or_the_move(moved, shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    layer = GlobalLayer(machine=carried.MACHINE, machine_moved=True) if moved else GlobalLayer.model_construct()
    _committed(shared, layer.model_dump(mode="json") if moved else {"format": 2, "agents": {}, "runtimes": {}})
    head = _git(shared.root, "rev-parse", "HEAD")
    edited = shared.global_path.read_text().replace('"format"', '"widths": [1440], "format"')
    shared.global_path.write_text(edited)  # the owner's edit, not saved
    _local()

    _carry(monkeypatch, shared)

    assert (_git(shared.root, "rev-parse", "HEAD"), shared.global_path.read_text()) == (head, edited)
    assert "not saved" in registry.load().settings_pending
    assert not registry.load().settings_moved


@pytest.mark.usefixtures("no_base")
def test_a_failed_carry_probe_keeps_everything_pending(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])  # no Global yet: the carry would create it
    _local()
    real = DataRepo.git
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", lambda self, *a, until=None: real(self, *a, until=until)
                  if a[0] != "ls-tree" else subprocess.CompletedProcess(a, 128, "", "broken"))  # fmt: skip
        _carry(monkeypatch, shared)
    assert (shared.global_path.exists(), registry.load().settings_moved) == (False, False)
    assert "broken" in registry.load().settings_pending


@pytest.mark.usefixtures("no_base")
def test_a_global_the_owner_remade_after_a_move_is_never_filled_again(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _local()
    _carry(monkeypatch, shared)  # carried and moved
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))  # deleted, then remade by a Settings save
    _local()  # another machine
    _carry(monkeypatch, shared)
    assert read_layer(shared.global_path, GlobalLayer).machine is None  # what the owner left unset stays unset
    assert _done()


@pytest.mark.usefixtures("no_base")
def test_an_owner_edit_staged_over_a_failed_move_never_gives_way(shared_repo, tmp_path, monkeypatch):
    first = DataRepo(shared_repo[0])
    _committed(first, GlobalLayer(sessions=2).model_dump(mode="json"))
    second = _clone(tmp_path, shared_repo)
    _local()
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", _staged_only)
        _carry(monkeypatch, second)  # the move is staged, its commit fails
    moved = second.global_path.read_bytes()
    owners = GlobalLayer(sessions=7).model_dump_json()
    second.global_path.write_text(owners)
    _git(second.root, "add", "config.json")  # the owner stages his own edit
    second.global_path.write_bytes(moved)  # and leaves the move's bytes in the file
    its_own = registry.load()
    settings_carry.move(first, MachineValues(sessions=6))
    with registry.locked():
        registry.save(its_own)

    _carry(monkeypatch, second)

    assert _git(second.root, "show", ":config.json") == owners  # his staged edit is kept
    assert "not saved" in registry.load().settings_pending


@pytest.mark.usefixtures("no_base")
@pytest.mark.parametrize("failed", ["commit", "push", "stage"])
def test_an_unpublished_carry_or_move_that_meets_another_machine_s_is_kept_and_pending(
    failed, shared_repo, tmp_path, monkeypatch
):
    first = DataRepo(shared_repo[0])
    if failed != "stage":
        _committed(first, GlobalLayer(sessions=2).model_dump(mode="json"))  # else the carry creates Global
    second = _clone(tmp_path, shared_repo)
    _local()
    with monkeypatch.context() as m:
        if failed == "commit":
            m.setattr(DataRepo, "commit", _staged_only)
        elif failed == "stage":
            m.setattr(DataRepo, "commit", lambda *_a, **_k: "git add failed")
        else:
            _git(second.root, "remote", "set-url", "--push", "origin", str(tmp_path / "nowhere"))
        _carry(monkeypatch, second)  # its carry or move, not published
    _git(second.root, "remote", "set-url", "--push", "origin", str(shared_repo[1]))
    kept = (_git(second.root, "rev-parse", "HEAD"), _git(second.root, "status", "--porcelain"),
            second.global_path.read_bytes())  # fmt: skip
    its_own = registry.load()
    _local(registry.Settings(sessions=6))  # the first machine's own differ: else both write the very same commit
    _carry(monkeypatch, first)  # meanwhile the first machine's carry and move are published
    with registry.locked():
        registry.save(its_own)

    _carry(monkeypatch, second)

    assert (_git(second.root, "rev-parse", "HEAD"), _git(second.root, "status", "--porcelain"),
            second.global_path.read_bytes()) == kept  # fmt: skip  # nothing undone automatically
    assert "another machine changed the global settings" in registry.load().settings_pending
    assert not registry.load().settings_moved


@pytest.mark.usefixtures("no_base")
def test_a_global_deleted_after_the_earlier_carry_is_not_remade_by_the_move(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    settings_carry.carry(shared)  # #604's carry, published
    shared.global_path.unlink()
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "the owner deletes Global")
    _git(shared.root, "push", "-q")
    head = _git(shared.root, "rev-parse", "HEAD")
    _local()

    _carry(monkeypatch, shared)

    assert (shared.global_path.exists(), _git(shared.root, "rev-parse", "HEAD"), _done()) == (False, head, True)


@pytest.mark.usefixtures("no_base")
def test_an_owner_s_staged_deletion_of_global_is_never_undone(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))
    _local()
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", _staged_only)
        _carry(monkeypatch, shared)  # the move is staged, its commit fails
    _git(shared.root, "rm", "-q", "--cached", "config.json")  # the owner stages Global's deletion, keeping the file

    _carry(monkeypatch, shared)

    assert _git(shared.root, "status", "--porcelain").splitlines() == ["D  config.json", "?? config.json"]
    assert "not saved" in registry.load().settings_pending


@pytest.mark.usefixtures("no_base")
def test_an_older_global_the_owner_restores_after_the_carry_is_never_filled_again(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _local()
    _carry(monkeypatch, shared)  # carried and moved
    _committed(shared, {"format": 9, "agents": {}, "runtimes": {}})  # the owner restores an older Global

    _local(registry.Settings())
    with registry.locked():
        machine = registry.load()
        machine.settings_moved = True
        registry.save(machine)
    head = _git(shared.root, "rev-parse", "HEAD")
    _carry(monkeypatch, shared)

    assert (_git(shared.root, "rev-parse", "HEAD"), settings_carry.due(shared)) == (head, False)
    assert read_layer(shared.global_path, GlobalLayer).agents == {}


@pytest.mark.usefixtures("no_base")
def test_a_move_a_settings_save_committed_counts_as_done_for_a_later_machine(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))
    _local()
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", _staged_only)
        _carry(monkeypatch, shared)  # the move is written and marked, its commit fails
    assert not shared.publish(shared.global_path, "settings: global")  # a Settings save commits it with the mark
    _carry(monkeypatch, shared)
    assert _done()
    assert settings_carry.MOVED not in _git(shared.root, "log", "--format=%s")  # no commit of its own
    _committed(shared, GlobalLayer(sessions=2).model_dump(mode="json"))  # the owner remakes Global without it

    _local()  # a later machine
    _carry(monkeypatch, shared)

    assert read_layer(shared.global_path, GlobalLayer).machine is None
    assert _done()


@pytest.mark.usefixtures("no_base")
def test_every_start_takes_in_what_another_machine_changed_in_global(shared_repo, tmp_path, monkeypatch):
    first = DataRepo(shared_repo[0])
    _local()
    _carry(monkeypatch, first)  # carried and moved
    second = _clone(tmp_path, shared_repo)
    _carry(monkeypatch, second)  # this machine is done too
    glob = read_layer(first.global_path, GlobalLayer)
    cleared = glob.model_copy(update={"machine": glob.machine.model_copy(update={"sessions": None})})
    _committed(first, cleared.model_dump(mode="json"))  # the owner clears it on the other machine

    _carry(monkeypatch, second)  # this machine restarts

    monkeypatch.setenv(data_repo.VIEW, str(second.root))
    assert machine_settings.current().sessions is None  # no stale value from before
    assert _done()


# The credit limits' upgrade (D-01M5XCD49YHHR1NQKKY8TQD0C3): a start saves Global in format 16 with the limits its
# migration wrote, and publishes it once; nothing else is filled, and the owner's later changes stay his.
LIMITS = (carried.LOOK_CREDIT_LIMIT, carried.RETRO_RUN_CREDIT_LIMIT, carried.REPLAY_RUN_CREDIT_LIMIT)
OLD_MACHINE = {"channel": "minor", "sessions": 3, "spotter_budget": 50, "retro_budget": 20, "retro_verbose_cap": 5}


def _limits(glob: GlobalLayer) -> tuple[float | None, float | None, float | None]:
    machine = glob.machine or MachineValues()
    return glob.spotter.look_credit_limit if glob.spotter else None, machine.retro_run_credit_limit, (
        machine.replay_run_credit_limit)  # fmt: skip


def _moved_global(shared: DataRepo, **extra) -> None:
    """A Global the carry and the move filled before format 16, published; this machine has moved."""
    old = carried.layer().model_dump(mode="json", exclude={"machine", "machine_moved", "format"})
    old["spotter"] = {k: v for k, v in old["spotter"].items() if k != "look_credit_limit"}
    _committed(shared, {"format": 15, **old, "machine": OLD_MACHINE, "machine_moved": True, **extra})
    _local(registry.Settings())
    with registry.locked():
        machine = registry.load()
        machine.settings_moved = True
        registry.save(machine)


def _published(shared: DataRepo, remote) -> bool:
    return _git(shared.root, "rev-parse", "HEAD") == _git(remote, "rev-parse", "HEAD") and not _git(
        shared.root, "status", "--porcelain")  # fmt: skip


@pytest.mark.usefixtures("no_base")
def test_a_start_writes_the_limits_into_global_and_publishes_them_once(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _moved_global(shared, pr_marker=None)
    assert settings_carry.limits_due(shared)

    _carry(monkeypatch, shared)

    raw = json.loads(shared.global_path.read_text())
    assert raw["format"] == 19
    assert (raw["spotter"]["look_credit_limit"], raw["machine"]["retro_run_credit_limit"],
            raw["machine"]["replay_run_credit_limit"]) == LIMITS  # fmt: skip
    assert not set(registry.DAILY) & set(raw["machine"])
    assert (raw["pr_marker"], raw["machine"]["sessions"]) == (None, 3)  # nothing else filled or lost
    assert _git(shared.root, "log", "-1", "--format=%s") == settings_carry.LIMITS
    assert _published(shared, shared_repo[1])
    assert not registry.load().settings_pending
    head = _git(shared.root, "rev-parse", "HEAD")
    assert _carry(monkeypatch, shared) == []  # once
    assert _git(shared.root, "rev-parse", "HEAD") == head


@pytest.mark.usefixtures("no_base")
def test_a_limit_the_owner_clears_after_the_upgrade_stays_cleared(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _moved_global(shared)
    _carry(monkeypatch, shared)
    glob = read_layer(shared.global_path, GlobalLayer)
    cleared = glob.model_copy(update={"spotter": glob.spotter.model_copy(update={"look_credit_limit": None})})
    _committed(shared, cleared.model_dump(mode="json"))  # the owner clears it on the Settings page
    head = _git(shared.root, "rev-parse", "HEAD")

    _carry(monkeypatch, shared)

    assert _git(shared.root, "rev-parse", "HEAD") == head
    assert read_layer(shared.global_path, GlobalLayer).spotter.look_credit_limit is None


@pytest.mark.usefixtures("no_base")
def test_an_older_global_the_owner_restores_after_the_upgrade_is_not_written_again(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _moved_global(shared)
    _carry(monkeypatch, shared)
    _committed(shared, {"format": 15, "sessions": 2})  # the owner restores an older Global
    head = _git(shared.root, "rev-parse", "HEAD")

    _carry(monkeypatch, shared)

    assert (_git(shared.root, "rev-parse", "HEAD"), settings_carry.limits_due(shared)) == (head, False)
    assert json.loads(shared.global_path.read_text())["format"] == 15  # his; a read still gets the limits
    assert _limits(read_layer(shared.global_path, GlobalLayer)) == LIMITS


@pytest.mark.usefixtures("no_base")
def test_a_failed_commit_keeps_the_written_global_and_the_next_start_only_publishes_it(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _moved_global(shared)
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", _staged_only)
        _carry(monkeypatch, shared)
    assert "the commit failed" in registry.load().settings_pending
    written = shared.global_path.read_text()
    assert json.loads(written)["format"] == 19
    assert settings_carry.limits_due(shared)

    _carry(monkeypatch, shared)

    assert shared.global_path.read_text() == written  # published as it was written, not written again
    assert _git(shared.root, "log", "-1", "--format=%s") == settings_carry.LIMITS
    assert _published(shared, shared_repo[1])
    assert not registry.load().settings_pending


def _failed_upgrade_commit(shared: DataRepo, monkeypatch) -> str:
    """A start whose upgrade wrote Global in format 16 and could not commit it; what it wrote."""
    _moved_global(shared)
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", _staged_only)
        _carry(monkeypatch, shared)
    assert registry.load().global_written  # this machine knows the write as its own
    return shared.global_path.read_text()


@pytest.mark.usefixtures("no_base")
@pytest.mark.parametrize("retry", [False, True])
def test_an_owner_edit_made_after_the_sync_is_never_published_by_the_upgrade(shared_repo, monkeypatch, retry):
    shared = DataRepo(shared_repo[0])
    if retry:  # the format-16 write is already there, only its publication is left
        _failed_upgrade_commit(shared, monkeypatch)
    else:
        _moved_global(shared)
    head, real = _git(shared.root, "rev-parse", "HEAD"), settings_carry.sync
    edited: list[str] = []

    def sync_then_edit(repo: DataRepo, written) -> str:
        why = real(repo, written)  # the checkout is current and Global is this machine's or committed
        text = repo.global_path.read_text().replace('"format"', '"widths": [1440], "format"', 1)
        repo.global_path.write_text(text)  # the owner saves an edit by hand meanwhile
        edited.append(text)
        return why

    monkeypatch.setattr(settings_carry, "sync", sync_then_edit)
    _carry(monkeypatch, shared)

    assert (_git(shared.root, "rev-parse", "HEAD"), shared.global_path.read_text()) == (head, edited[0])
    assert settings_carry.LIMITS not in _git(shared.root, "log", "--format=%s")
    assert "not saved" in registry.load().settings_pending


@pytest.mark.usefixtures("no_base")
def test_a_failed_probe_after_a_failed_upgrade_commit_keeps_it_pending_and_its_write_known(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    written = _failed_upgrade_commit(shared, monkeypatch)
    digest = registry.load().global_written
    real = DataRepo.git
    probe = f"-G{settings_carry.REACHED}"
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "git", lambda self, *a, until=None: real(self, *a, until=until)
                  if probe not in a else subprocess.CompletedProcess(a, 128, "", "broken"))  # fmt: skip
        _carry(monkeypatch, shared)
    machine = registry.load()
    assert "broken" in machine.settings_pending  # unknown is never taken for done
    assert machine.global_written == digest  # still known as this machine's own write

    _carry(monkeypatch, shared)

    assert shared.global_path.read_text() == written
    assert _git(shared.root, "log", "-1", "--format=%s") == settings_carry.LIMITS
    assert _published(shared, shared_repo[1])
    assert not registry.load().settings_pending


@pytest.mark.usefixtures("no_base")
def test_another_machine_s_format_16_never_clears_this_machine_s_unpublished_upgrade(
    shared_repo, tmp_path, monkeypatch
):
    shared = DataRepo(shared_repo[0])
    written = _failed_upgrade_commit(shared, monkeypatch)
    digest = registry.load().global_written
    other = _clone(tmp_path, shared_repo)  # another machine publishes its own format-16 Global meanwhile
    glob = read_layer(other.global_path, GlobalLayer)
    _committed(other, glob.model_copy(update={"sessions": 7}).model_dump(mode="json"))

    _carry(monkeypatch, shared)

    machine = registry.load()
    assert "another machine changed the global settings" in machine.settings_pending  # the owner reconciles
    assert machine.global_written == digest  # still known as this machine's own write
    assert shared.global_path.read_text() == written  # nothing undone


@pytest.mark.usefixtures("no_base")
def test_a_failed_push_keeps_the_commit_and_the_next_start_pushes_it(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _moved_global(shared)
    _git(shared.root, "remote", "set-url", "--push", "origin", str(shared.root / "nowhere"))
    _carry(monkeypatch, shared)
    assert registry.load().settings_pending
    assert _git(shared.root, "log", "-1", "--format=%s") == settings_carry.LIMITS  # kept, not undone
    assert settings_carry.limits_due(shared)
    _git(shared.root, "remote", "set-url", "--push", "origin", str(shared_repo[1]))

    _carry(monkeypatch, shared)

    assert _published(shared, shared_repo[1])
    assert (registry.load().settings_pending, settings_carry.limits_due(shared)) == ("", False)
    assert _git(shared.root, "log", "--format=%s").count(settings_carry.LIMITS) == 1


@pytest.mark.usefixtures("no_base")
def test_an_unsaved_owner_edit_of_an_older_global_is_never_published(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _moved_global(shared)
    head = _git(shared.root, "rev-parse", "HEAD")
    edited = shared.global_path.read_text().replace('"format"', '"widths": [1440], "format"')
    shared.global_path.write_text(edited)  # the owner's edit, not saved

    _carry(monkeypatch, shared)

    assert (_git(shared.root, "rev-parse", "HEAD"), shared.global_path.read_text()) == (head, edited)
    assert "not saved" in registry.load().settings_pending


@pytest.mark.usefixtures("no_base")
def test_a_fresh_install_carries_the_limits_with_the_built_in_values(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    _local()

    _carry(monkeypatch, shared)

    assert _limits(read_layer(shared.global_path, GlobalLayer)) == LIMITS
    assert not settings_carry.limits_due(shared)
    assert settings_carry.LIMITS not in _git(shared.root, "log", "--format=%s")  # the carry wrote format 16 itself
