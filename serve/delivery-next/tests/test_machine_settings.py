"""Machine settings with a Global layer (D-01M5MZKEPPVMFC9HK795MMG91B): each machine follows Global unless it sets its
own; unset in both is an error, and what needs it does not run. Each machine's first start moves its own settings into
Global once (the owner, 2026-10-23: move all), on a current checkout, keeping its progress when publishing fails."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation, machine_settings, registry, versions
from owlbear_delivery_next.machine_host.auto_update import Auto
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
    assert not Auto.permitted(SimpleNamespace(machine=SimpleNamespace(paused=False)))  # never updates by itself


@pytest.mark.usefixtures("no_base")
def test_the_switch_over_moves_this_machine_s_settings_into_a_carried_global_and_clears_them(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    old = carried.layer().model_dump(mode="json", exclude={"machine", "machine_moved"}) | {"format": 10}
    _committed(shared, old | {"pr_marker": None})  # what #604's carry left, with a value the owner cleared since
    _local()

    said = _carry(monkeypatch, shared)

    glob = read_layer(shared.global_path, GlobalLayer)
    assert (glob.machine, glob.machine_moved) == (MachineValues.model_validate(LEGACY.model_dump()), True)
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
