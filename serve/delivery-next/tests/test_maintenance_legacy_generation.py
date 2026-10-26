"""A pre-ledger pack run is held once per its proven identity; a restart after recovery never holds it again."""

import fcntl
import json
import os
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import codebase, maintenance
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.machine_host import project
from owlbear_delivery_next.machine_host.machine import UNPROVEN_PACK, Machine
from owlbear_delivery_next.pack_runs import pack_job, pack_run, pack_state
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import project_home, registry
from owlbear_delivery_next.state_store.store import Store

REPLAY_UNCERTAIN = (
    "replay: ReplayError: the replay judge replay-0123abcd may still be running; stop it before replaying again"
)
STARTED = "2026-10-25T00:00:00+00:00"
UNPROVABLE = [{}, {"run": "legacy-run"}, {"started_at": STARTED}]  # the identity a historical record may lack


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    return path.resolve()


@pytest.fixture
def machines(monkeypatch):
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    made: list[Machine] = []

    def make() -> Machine:
        record = HostRecord(
            url="http://127.0.0.1:9/",
            token="t",  # noqa: S106
            pid=1,
            started_at=datetime.now(UTC),
            code=codebase.CURRENT,
        )
        m = Machine(record)
        m.slots.total = lambda: 1
        made.append(m)
        return m

    yield make
    for m in made:
        m.stop_all()


def store_too_new(tmp_path: Path, name: str):
    """A registered project whose store will not open, so its pack record is read without opening the store."""
    entry = registry.register(clone(tmp_path / name))
    folder = Path(entry.path) / ".git" / "owlbear-delivery"
    (folder / "format").write_text("99\n")
    return entry, folder


def write_pack(folder: Path, record: dict[str, object]) -> Path:
    """The last pack record a host left, with its updater directory still present."""
    stage = {"name": "update", "label": "Update", "result": "failed", "detail": ""}
    body = pack_job._blank() | {"state": "failed", "stages": [stage], "reason": REPLAY_UNCERTAIN} | record  # noqa: SLF001
    (folder / pack_job.FILE).write_text(json.dumps(body), encoding="utf-8")
    (folder / pack_run.UPDATER).mkdir(exist_ok=True)
    return folder / pack_run.UPDATER


def sessions_of(machine: Machine, project_id: str) -> list[dict[str, object]]:
    return [s for s in machine.maintenance.read()["sessions"] if s["project"] == project_id]


def held(machine: Machine, project_id: str) -> list[dict[str, object]]:
    return [s for s in sessions_of(machine, project_id) if s["state"] == "held"]


def reboot_then_recover(machine: Machine, ident: str) -> None:
    booted = machine.maintenance.boot
    machine.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the hold
    machine.maintenance.recover(ident, rebooted=True)


@pytest.mark.parametrize("identity", UNPROVABLE)
def test_a_legacy_run_without_its_proven_identity_holds_once_and_a_restart_after_recovery_does_not_resurrect_it(
    tmp_path, machines, identity
):
    bad, folder = store_too_new(tmp_path, "bad")
    write_pack(folder, identity)
    first = machines()
    first.load_all()
    assert len(held(first, bad.id)) == 1, sessions_of(first, bad.id)
    reboot_then_recover(first, held(first, bad.id)[0]["id"])

    restarted = machines()
    restarted.load_all()
    assert held(restarted, bad.id) == [], "a restart re-held a legacy run its owner already recovered"
    assert len(sessions_of(restarted, bad.id)) == 1, "a restart duplicated a recovered legacy run"


def test_a_later_different_legacy_run_with_a_proven_identity_gets_its_own_hold_and_the_recovered_one_stays_recovered(
    tmp_path, machines
):
    bad, folder = store_too_new(tmp_path, "bad")
    write_pack(folder, {})
    first = machines()
    first.load_all()
    reboot_then_recover(first, held(first, bad.id)[0]["id"])

    write_pack(folder, {"run": "later-run", "started_at": "2026-10-26T00:00:00+00:00"})
    later = machines()
    later.load_all()
    assert [s["state"] for s in sessions_of(later, bad.id)] == ["recovered", "held"]


def test_a_legacy_run_with_its_full_identity_holds_once_and_a_restart_after_recovery_does_not_resurrect_it(
    tmp_path, machines
):
    bad, folder = store_too_new(tmp_path, "bad")
    write_pack(folder, {"run": "legacy-run", "started_at": STARTED})
    first = machines()
    first.load_all()
    reboot_then_recover(first, held(first, bad.id)[0]["id"])

    restarted = machines()
    restarted.load_all()
    assert [s["state"] for s in sessions_of(restarted, bad.id)] == ["recovered"]


def open_project(tmp_path: Path, shared, name: str):
    """A registered project whose store opens, so its pack record is read by the loaded project."""
    repo = clone(tmp_path / name)
    Store(repo, DataRepo(shared), name)
    entry = registry.register(repo)
    return entry, Path(entry.path) / ".git" / "owlbear-delivery"


def test_a_loaded_project_legacy_run_without_its_proven_identity_is_held_once_and_not_resurrected_on_restart(
    tmp_path, machines, shared_repo
):
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {})
    first = machines()
    first.load_all()
    assert len(held(first, good.id)) == 1, sessions_of(first, good.id)
    reboot_then_recover(first, held(first, good.id)[0]["id"])

    restarted = machines()
    restarted.load_all()
    assert held(restarted, good.id) == [], "a restart re-held a loaded legacy run its owner already recovered"
    assert len(sessions_of(restarted, good.id)) == 1


def test_a_loaded_project_later_different_legacy_run_gets_its_own_hold_after_the_recovered_one(
    tmp_path, machines, shared_repo
):
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {})
    first = machines()
    first.load_all()
    reboot_then_recover(first, held(first, good.id)[0]["id"])

    write_pack(folder, {"reason": "a later run's own reason"})
    later = machines()
    later.load_all()
    assert [s["state"] for s in sessions_of(later, good.id)] == ["recovered", "held"]


def test_a_modern_running_run_whose_workspace_the_ledger_owns_adds_no_second_hold_on_restart(tmp_path, machines):
    bad, folder = store_too_new(tmp_path, "bad")
    workspace = folder / "modern-workspace"
    workspace.mkdir()
    write_pack(
        folder,
        {"state": "running", "run": "modern-run", "started_at": STARTED, "workspace": str(workspace)},
    )
    first = machines()
    first.load_all()
    assert len(sessions_of(first, bad.id)) == 1

    restarted = machines()
    restarted.load_all()
    assert len(sessions_of(restarted, bad.id)) == 1, "a restart held a modern run the ledger already owned"


def project_with_legacy_run(tmp_path: Path, shared, *, loaded: bool):
    """A project whose legacy record a loaded project reads, or whose folder is read if its store will not open."""
    if loaded:
        return open_project(tmp_path, shared, "bad")
    return store_too_new(tmp_path, "bad")


def live_folder(entry, folder: Path, *, loaded: bool) -> Path:
    """Where the record lives once a loaded store has moved it out of the clone; an unopened clone keeps it."""
    return project_home.home(entry.id) if loaded else folder


@pytest.mark.parametrize("loaded", [False, True])
def test_a_same_bytes_atomic_replacement_of_an_untouched_legacy_run_is_a_new_run_and_gets_a_new_hold(
    tmp_path, machines, shared_repo, loaded
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_pack(folder, {})
    first = machines()
    first.load_all()
    assert len(held(first, entry.id)) == 1, sessions_of(first, entry.id)
    reboot_then_recover(first, held(first, entry.id)[0]["id"])
    first.stop_all()
    folder = live_folder(entry, folder, loaded=loaded)

    untouched = machines()
    untouched.load_all()
    assert held(untouched, entry.id) == [], "an untouched recovered legacy run was held again"
    untouched.stop_all()

    record = folder / pack_job.FILE
    before = record.stat().st_ino
    atomic_write(record, record.read_text(encoding="utf-8"))
    assert record.stat().st_ino != before, "the replacement kept the file's identity, so the test proves nothing"

    replaced = machines()
    replaced.load_all()
    assert [s["state"] for s in sessions_of(replaced, entry.id)] == ["recovered", "held"]


@pytest.mark.parametrize("loaded", [False, True])
def test_an_in_place_rewrite_with_its_mtime_restored_is_a_new_run_while_an_untouched_read_is_stable(
    tmp_path, machines, shared_repo, loaded
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_pack(folder, {})
    first = machines()
    first.load_all()
    reboot_then_recover(first, held(first, entry.id)[0]["id"])
    first.stop_all()
    folder = live_folder(entry, folder, loaded=loaded)
    record = folder / pack_job.FILE

    version = pack_state.observed(folder)[1]
    assert pack_state.observed(folder)[1] == version, "an untouched record read changed its version"
    untouched = machines()
    untouched.load_all()
    assert held(untouched, entry.id) == [], "an untouched recovered legacy run was held again"
    untouched.stop_all()

    before = record.stat()
    with record.open("r+b") as f:
        data = f.read()
        f.seek(0)
        f.write(data)
    os.utime(record, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = record.stat()
    assert after.st_ino == before.st_ino
    assert after.st_size == before.st_size
    assert after.st_mtime_ns == before.st_mtime_ns, "the test did not restore the mtime"
    assert after.st_ctime_ns != before.st_ctime_ns, "the in-place write did not move the ctime"

    replaced = machines()
    replaced.load_all()
    assert [s["state"] for s in sessions_of(replaced, entry.id)] == ["recovered", "held"]


@pytest.mark.parametrize("loaded", [False, True])
def test_an_unreadable_legacy_run_record_is_held_conservatively_and_is_never_borrowed_from_a_recovered_one(
    tmp_path, machines, shared_repo, loaded
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_pack(folder, {})
    first = machines()
    first.load_all()
    reboot_then_recover(first, held(first, entry.id)[0]["id"])
    first.stop_all()
    folder = live_folder(entry, folder, loaded=loaded)
    (folder / pack_job.FILE).write_text("{not a run", encoding="utf-8")

    unreadable = machines()
    unreadable.load_all()
    assert [s["state"] for s in sessions_of(unreadable, entry.id)] == ["recovered", "held"]


class NoFstat:
    """The real os module, except that a descriptor's metadata cannot be read."""

    def __init__(self, real) -> None:
        self._real = real

    def fstat(self, _fd):
        """Refuse the descriptor's metadata."""
        msg = "fstat unavailable"
        raise OSError(msg)

    def __getattr__(self, name):
        return getattr(self._real, name)


@pytest.mark.parametrize("loaded", [False, True])
def test_a_legacy_run_whose_metadata_cannot_be_read_is_held_again_after_a_real_replacement_once_recovered(
    tmp_path, machines, shared_repo, monkeypatch, loaded
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_pack(folder, {})
    monkeypatch.setattr(pack_state, "os", NoFstat(os))
    first = machines()
    first.load_all()
    assert len(held(first, entry.id)) == 1, sessions_of(first, entry.id)
    reboot_then_recover(first, held(first, entry.id)[0]["id"])
    monkeypatch.setattr(pack_state, "os", os)
    first.stop_all()
    folder = live_folder(entry, folder, loaded=loaded)

    record = folder / pack_job.FILE
    atomic_write(record, record.read_text(encoding="utf-8"))

    monkeypatch.setattr(pack_state, "os", NoFstat(os))
    replaced = machines()
    replaced.load_all()
    assert [s["state"] for s in sessions_of(replaced, entry.id)] == ["recovered", "held"]
    replaced.stop_all()

    again = machines()
    again.load_all()
    assert [s["state"] for s in sessions_of(again, entry.id)] == ["recovered", "held"], (
        "a reconstruction with an active hold duplicated it"
    )


PARTIAL = {"state": "running", "run": "partial-run", "started_at": STARTED}  # no stages or log: a damaged record


def write_bare(folder: Path, body: dict[str, object]) -> None:
    """A record a host left with no updater directory beside it."""
    (folder / pack_job.FILE).write_text(json.dumps(body), encoding="utf-8")


def test_the_reader_names_a_partial_record_unreadable_and_a_valid_idle_record_readable(tmp_path):
    path = tmp_path / pack_job.FILE
    assert pack_state.read_version(path)[1] == "absent"
    path.write_text(json.dumps(PARTIAL), encoding="utf-8")
    assert pack_state.read_version(path)[1] == "", "a partial running record was read as a readable run"
    path.write_text(json.dumps(pack_job._blank()), encoding="utf-8")  # noqa: SLF001
    assert pack_state.read_version(path)[1] != "", "a valid idle record was read as unreadable"


@pytest.mark.parametrize("loaded", [False, True])
def test_a_partial_running_record_is_held_once_and_is_held_again_after_recovery_while_still_unreadable(
    tmp_path, machines, shared_repo, loaded
):
    """Recovery covers the receipt, not bytes still unreadable: an unreadable current record stays conservative."""
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_bare(folder, PARTIAL)
    first = machines()
    first.load_all()
    assert len(held(first, entry.id)) == 1, sessions_of(first, entry.id)
    reboot_then_recover(first, held(first, entry.id)[0]["id"])
    first.stop_all()

    restarted = machines()
    restarted.load_all()
    assert [s["state"] for s in sessions_of(restarted, entry.id)] == ["recovered", "held"]
    restarted.stop_all()


@pytest.mark.parametrize("loaded", [False, True])
def test_an_active_partial_record_hold_is_not_duplicated_when_the_project_is_reconstructed(
    tmp_path, machines, shared_repo, loaded
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_bare(folder, PARTIAL)
    first = machines()
    first.load_all()
    assert len(held(first, entry.id)) == 1, sessions_of(first, entry.id)
    first.stop_all()

    restarted = machines()
    restarted.load_all()
    assert len(held(restarted, entry.id)) == 1, "reconstruction duplicated an active partial-record hold"
    assert len(sessions_of(restarted, entry.id)) == 1


@pytest.mark.parametrize("loaded", [False, True])
def test_a_fresh_partial_record_after_recovery_gets_its_own_hold(tmp_path, machines, shared_repo, loaded):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_bare(folder, PARTIAL)
    first = machines()
    first.load_all()
    reboot_then_recover(first, held(first, entry.id)[0]["id"])
    first.stop_all()
    folder = live_folder(entry, folder, loaded=loaded)

    write_bare(folder, PARTIAL | {"run": "later-run", "started_at": "2026-10-26T00:00:00+00:00"})
    later = machines()
    later.load_all()
    assert [s["state"] for s in sessions_of(later, entry.id)] == ["recovered", "held"]


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize(
    "body",
    [
        pytest.param(None, id="absent"),
        pytest.param(pack_job._blank(), id="valid-idle"),  # noqa: SLF001
        pytest.param(pack_job._blank() | {"state": "failed", "reason": "the pack was refused"}, id="definitive"),  # noqa: SLF001
    ],
)
def test_an_absent_valid_idle_or_definitively_failed_record_holds_nothing(
    tmp_path, machines, shared_repo, loaded, body
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    if body is not None:
        write_bare(folder, body)
    loaded_machine = machines()
    loaded_machine.load_all()
    assert held(loaded_machine, entry.id) == [], sessions_of(loaded_machine, entry.id)
    loaded_machine.stop_all()


MALFORMED = [
    pytest.param({"state": None}, id="state-null"),
    pytest.param({"state": "unknown"}, id="state-unknown"),
    pytest.param({"state": 7}, id="state-number"),
    pytest.param({"state": ["running"]}, id="state-list"),
    pytest.param({"stages": None}, id="stages-null"),
    pytest.param({"stages": "running"}, id="stages-text"),
    pytest.param({"log": None}, id="log-null"),
    pytest.param({"log": "a line"}, id="log-text"),
]


@pytest.mark.parametrize("damage", MALFORMED)
def test_the_reader_names_a_misshapen_required_field_unreadable(tmp_path, damage):
    path = tmp_path / pack_job.FILE
    path.write_text(json.dumps(pack_job._blank() | damage), encoding="utf-8")  # noqa: SLF001
    assert pack_state.read_version(path)[1] == "", f"{damage} was read as a readable run"


@pytest.mark.parametrize("state", sorted(pack_state.STATES))
def test_every_state_job_writes_with_its_stages_and_log_is_readable(tmp_path, state):
    path = tmp_path / pack_job.FILE
    path.write_text(json.dumps(pack_job._blank() | {"state": state}), encoding="utf-8")  # noqa: SLF001
    assert pack_state.read_version(path)[1] != "", f"a {state} record was read as unreadable"


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize("damage", MALFORMED)
def test_a_misshapen_legacy_record_with_no_workspace_is_held_once_and_not_duplicated_on_restart(
    tmp_path, machines, shared_repo, loaded, damage
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_bare(folder, pack_job._blank() | damage)  # noqa: SLF001
    first = machines()
    first.load_all()
    assert len(held(first, entry.id)) == 1, sessions_of(first, entry.id)
    first.stop_all()

    restarted = machines()
    restarted.load_all()
    assert len(held(restarted, entry.id)) == 1, "reconstruction duplicated a misshapen-record hold"
    restarted.stop_all()


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize("state", ["passed", "up-to-date", "discarded"])
def test_a_valid_definitive_outcome_without_a_workspace_holds_nothing_on_load(
    tmp_path, machines, shared_repo, loaded, state
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_bare(folder, pack_job._blank() | {"state": state, "reason": "the pack was already current"})  # noqa: SLF001
    loaded_machine = machines()
    loaded_machine.load_all()
    assert held(loaded_machine, entry.id) == [], sessions_of(loaded_machine, entry.id)
    loaded_machine.stop_all()


@pytest.mark.parametrize("loaded", [False, True])
def test_an_incomplete_running_record_replaced_after_recovery_gets_a_new_hold_and_is_not_resurrected_untouched(
    tmp_path, machines, shared_repo, loaded
):
    shared, _remote = shared_repo
    bad, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    write_pack(folder, {"state": "running"})
    first = machines()
    first.load_all()
    assert len(held(first, bad.id)) == 1, sessions_of(first, bad.id)
    reboot_then_recover(first, held(first, bad.id)[0]["id"])

    untouched = machines()
    untouched.load_all()
    assert held(untouched, bad.id) == [], "an untouched recovered record was held again"

    write_pack(folder, {"state": "running"})  # a real replacement of the same incomplete record
    replaced = machines()
    replaced.load_all()
    assert len(held(replaced, bad.id)) == 1, "a replaced incomplete run reused the recovered hold"


def test_a_running_legacy_record_rewritten_by_its_own_constructor_keeps_one_generation_across_restarts(
    tmp_path, machines, shared_repo
):
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {"state": "running"})
    first = machines()
    first.load_all()
    assert len(held(first, good.id)) == 1, sessions_of(first, good.id)
    reboot_then_recover(first, held(first, good.id)[0]["id"])

    restarted = machines()
    restarted.load_all()
    assert len(sessions_of(restarted, good.id)) == 1, "the constructor's rewrite duplicated the reservation"

    write_pack(folder, {"state": "running"})  # a later historical replacement is a different run
    later = machines()
    later.load_all()
    assert len(held(later, good.id)) == 1, "a later replacement of the rewritten record was not held"


def test_a_project_whose_host_lock_another_host_holds_leaves_that_hosts_record_bytes_unchanged(
    tmp_path, machines, shared_repo
):
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {"state": "running", "run": "other-run", "started_at": STARTED, "workspace": ""})
    record = folder / pack_job.FILE
    before = record.read_bytes()
    fd = os.open(project_home.located(Path(good.path)) / "host.lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        machines().load_all()
        # The store moves the record to the project home before the lock; the move must keep its bytes.
        moved = project_home.located(Path(good.path)) / pack_job.FILE
        assert moved.read_bytes() == before, "a host that did not own the project rewrote its running record"
    finally:
        os.close(fd)


def test_a_foreign_replacement_landing_after_the_constructors_own_rewrite_gets_its_own_hold(
    tmp_path, machines, shared_repo, monkeypatch
):
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {"state": "running"})
    original = (folder / pack_job.FILE).read_text(encoding="utf-8")
    record = live_folder(good, folder, loaded=True) / pack_job.FILE  # the loaded store moves it before the constructor
    real_write, seams = pack_job.atomic_write, []

    def replace_after_own_rewrite(path, text):
        own = real_write(path, text)
        if path == record and not seams and '"failed"' in text:
            seams.append(path)
            real_write(path, original)  # a foreign writer puts back the same bytes as a new file
        return own

    monkeypatch.setattr(pack_job, "atomic_write", replace_after_own_rewrite)
    first = machines()
    first.load_all()
    assert seams, "the constructor's own rewrite never ran"
    assert len(held(first, good.id)) == 1, sessions_of(first, good.id)
    reboot_then_recover(first, held(first, good.id)[0]["id"])
    first.stop_all()
    monkeypatch.setattr(pack_job, "atomic_write", real_write)

    restarted = machines()
    restarted.load_all()
    assert [s["state"] for s in sessions_of(restarted, good.id)] == ["recovered", "held"], (
        "a foreign replacement after the constructor's own rewrite was bound to the old run"
    )
    restarted.stop_all()

    again = machines()
    again.load_all()
    assert [s["state"] for s in sessions_of(again, good.id)] == ["recovered", "held"], (
        "the constructor's own rewrite duplicated the foreign reservation on restart"
    )


def test_an_unlocated_hold_once_recovered_gets_fresh_uncertain_ownership_when_location_fails_again(
    tmp_path, machines, monkeypatch
):
    bad, _folder = store_too_new(tmp_path, "bad")
    locate, unlocatable = project_home.current, [True]

    def current(repo):
        if unlocatable[0]:
            msg = "the project folder cannot be located"
            raise OSError(msg)
        return locate(repo)

    monkeypatch.setattr(project_home, "current", current)
    first = machines()
    first.load_all()
    assert len(held(first, bad.id)) == 1, sessions_of(first, bad.id)
    reboot_then_recover(first, held(first, bad.id)[0]["id"])
    first.stop_all()

    later = machines()
    later.load_all()
    assert [s["state"] for s in sessions_of(later, bad.id)] == ["recovered", "held"], (
        "a later location failure reused the recovered unlocated hold"
    )
    later.stop_all()

    again = machines()
    again.load_all()
    assert [s["state"] for s in sessions_of(again, bad.id)] == ["recovered", "held"], (
        "reconstruction with an active unlocated hold duplicated it"
    )


ENDED, LATER = "2026-10-25T01:00:00+00:00", "2026-10-25T02:00:00+00:00"


def historical_finish(ended: str, reason: str = pack_state.HOST_STOPPED) -> str:
    """The record an older host's _finish left: no run identity and no workspace key, the directory may be gone."""
    body = {
        "state": "failed",
        "stage": "",
        "stages": [],
        "log": [],
        "started_at": STARTED,
        "ended_at": ended,
        "reason": reason,
        "questions": [],
        "context": None,
    }
    return json.dumps(body, indent=1) + "\n"


@pytest.mark.parametrize("loaded", [False, True])
def test_a_host_stopped_record_without_its_directory_is_held_once_and_a_later_rewrite_is_held_again(
    tmp_path, machines, shared_repo, loaded
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    (folder / pack_job.FILE).write_text(historical_finish(ENDED), encoding="utf-8")
    first = machines()
    first.load_all()
    assert len(held(first, entry.id)) == 1, sessions_of(first, entry.id)
    reboot_then_recover(first, held(first, entry.id)[0]["id"])
    first.stop_all()
    folder = live_folder(entry, folder, loaded=loaded)

    untouched = machines()
    untouched.load_all()
    assert held(untouched, entry.id) == [], "a recovered host-stopped record was held again"
    untouched.stop_all()

    atomic_write(folder / pack_job.FILE, historical_finish(LATER))
    replaced = machines()
    replaced.load_all()
    assert [s["state"] for s in sessions_of(replaced, entry.id)] == ["recovered", "held"], (
        "a historical host-stopped rewrite after recovery was not held"
    )


def test_a_historical_finish_landing_after_the_constructors_own_rewrite_gets_its_own_hold(
    tmp_path, machines, shared_repo, monkeypatch
):
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {"state": "running"})
    record = live_folder(good, folder, loaded=True) / pack_job.FILE  # the loaded store moves it before the constructor
    real_write, seams = pack_job.atomic_write, []

    def historical_finish_after_own_rewrite(path, text):
        own = real_write(path, text)
        if path == record and not seams and '"failed"' in text:
            seams.append(path)
            shutil.rmtree(path.parent / pack_run.UPDATER, ignore_errors=True)  # the old _finish removed the workspace
            real_write(path, historical_finish(LATER))
        return own

    monkeypatch.setattr(pack_job, "atomic_write", historical_finish_after_own_rewrite)
    first = machines()
    first.load_all()
    assert seams, "the constructor's own rewrite never ran"
    assert len(held(first, good.id)) == 1, sessions_of(first, good.id)
    reboot_then_recover(first, held(first, good.id)[0]["id"])
    first.stop_all()
    monkeypatch.setattr(pack_job, "atomic_write", real_write)

    restarted = machines()
    restarted.load_all()
    assert [s["state"] for s in sessions_of(restarted, good.id)] == ["recovered", "held"], (
        "a historical finish after the constructor's own rewrite was not held"
    )
    restarted.stop_all()

    again = machines()
    again.load_all()
    assert [s["state"] for s in sessions_of(again, good.id)] == ["recovered", "held"], (
        "reconstruction with the foreign historical hold active duplicated it"
    )


@pytest.mark.parametrize("loaded", [False, True])
def test_an_ordinary_definitive_failure_without_a_workspace_is_not_held(tmp_path, machines, shared_repo, loaded):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    reason = "the candidate could not be downloaded"
    (folder / pack_job.FILE).write_text(historical_finish(ENDED, reason=reason), encoding="utf-8")
    m = machines()
    m.load_all()
    assert sessions_of(m, entry.id) == [], "a definitive failure was held as uncertain"


def main_stage_failure(folder: Path, stage: str, reason: str, run: str = "main-run") -> None:
    """What main's ``_finish`` leaves when one stage's work raised: the stage failed, the reason prefixed by its name
    unless it ended with a stage verdict, the updater folder removed, and no workspace or PIDs."""
    ended = {"state": "failed", "run": run, "started_at": STARTED, "ended_at": ENDED, "reason": reason}
    body = pack_job._blank() | ended  # noqa: SLF001
    body["stages"] = [s | {"result": "failed", "detail": reason} if s["name"] == stage else s for s in body["stages"]]
    (folder / pack_job.FILE).write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8")
    shutil.rmtree(folder / pack_run.UPDATER, ignore_errors=True)


SDK_RAISED = [
    ("update", "update: RuntimeError: synthetic SDK failure"),
    ("replay", "replay: RuntimeError: synthetic SDK failure"),
    ("challenger", "challenger: RuntimeError: synthetic SDK failure"),
    ("update", "update: PackError: the updater could not be configured"),  # no text proves the session never began
]


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize("failure", SDK_RAISED)
def test_a_main_sdk_stage_failure_with_its_folder_removed_is_held_and_starts_nothing_until_recovered(
    tmp_path, machines, shared_repo, loaded, failure
):
    """Review 4373927946: an exception from an SDK stage proves nothing about its session, whatever its folder."""
    shared, _remote = shared_repo
    stage, reason = failure
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    main_stage_failure(folder, stage, reason)
    other = registry.register(clone(tmp_path / "other"))
    first = machines()
    first.load_all()
    [hold] = held(first, entry.id)
    assert (first.slots.take(other.id, "probe", 1, 1), first.maintenance.pending("pack")) == (0, True)
    assert any(UNPROVEN_PACK in w for w in first.busy()), first.busy()
    reboot_then_recover(first, hold["id"])
    first.stop_all()
    restarted = machines()
    restarted.load_all()
    assert (held(restarted, entry.id), len(sessions_of(restarted, entry.id))) == ([], 1), "recovery was resurrected"
    restarted.stop_all()
    main_stage_failure(live_folder(entry, folder, loaded=loaded), stage, reason, run="main-run-b")
    later = machines()
    later.load_all()
    assert len(held(later, entry.id)) == 1, "a later run's failure was not held as its own generation"


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize(
    "failure",
    [
        ("update", "update: PackError: the updater ended with error: no result"),
        ("update", "update: PackError: the updater asks the owner: the premise is wrong (evidence)"),
        ("challenger", "challenger: PackError: the challenger ended with error: no verdict"),
        ("replay", "calibration replay: 1 of 3 calibration rounds judged as expected"),
        ("candidate", "candidate: RuntimeError: the download failed"),
        ("golden", "golden: RuntimeError: the golden pages could not be rendered"),
    ],
)
def test_a_main_failure_after_a_confirmed_session_or_outside_any_session_holds_nothing(
    tmp_path, machines, shared_repo, loaded, failure
):
    shared, _remote = shared_repo
    entry, folder = project_with_legacy_run(tmp_path, shared, loaded=loaded)
    main_stage_failure(folder, *failure)
    m = machines()
    m.load_all()
    assert (sessions_of(m, entry.id), m.maintenance.pending("pack")) == ([], False)


def test_a_running_record_without_identity_keeps_one_lease_when_its_hold_is_interrupted_by_a_crash(
    tmp_path, machines, shared_repo
):
    """Review 4373927978: the hold and the receipt for the constructor's own rewrite are one ledger save.

    A crash right after that save, or a failed save, leaves exactly one lease across restarts; after its recovery none
    is held, and a later running record is held anew.
    """
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {"state": "running"})  # no run id and no start: its identity is its file
    first = machines()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Slots, "restore_one", crash_once(Slots.restore_one))  # the process dies after the save
        first.load_all()
    assert (first.projects[good.id].state, len(sessions_of(first, good.id))) == ("failed", 1)
    first.stop_all()
    for _ in range(2):
        again = machines()
        again.load_all()
        assert (again.projects[good.id].state, len(sessions_of(again, good.id))) == ("loaded", 1)
        again.stop_all()
    [lease] = held(again, good.id)
    reboot_then_recover(again, lease["id"])
    after = machines()
    after.load_all()
    assert (held(after, good.id), len(sessions_of(after, good.id))) == ([], 1)
    after.stop_all()
    write_pack(project_home.home(good.id), {"state": "running"})  # a later run, again without identity
    later = machines()
    later.load_all()
    assert (len(held(later, good.id)), len(sessions_of(later, good.id))) == (1, 2)


def test_a_failed_hold_save_after_the_constructors_rewrite_leaves_no_lease_and_the_next_start_holds_once(
    tmp_path, machines, shared_repo
):
    shared, _remote = shared_repo
    good, folder = open_project(tmp_path, shared, "good")
    write_pack(folder, {"state": "running"})
    first = machines()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(maintenance.Maintenance, "_save", fail_save_once(maintenance.Maintenance._save))  # noqa: SLF001
        first.load_all()
    first.stop_all()
    for _ in range(2):
        again = machines()
        again.load_all()
        assert (len(held(again, good.id)), len(sessions_of(again, good.id))) == (1, 1)
        again.stop_all()


def crash_once(real):
    crashed: list[bool] = []

    def restore_one(self, project_id: str, key: str, count: int) -> None:
        if key.startswith("pack:legacy-") and not crashed:
            crashed.append(True)
            msg = "synthetic crash after the hold was saved"
            raise RuntimeError(msg)
        real(self, project_id, key, count)

    return restore_one


def fail_save_once(real):
    failed: list[bool] = []

    def save(self, ledger) -> None:
        if any(s.kind == "pack" for s in ledger.sessions) and not failed:
            failed.append(True)
            msg = "synthetic: the ledger could not be saved"
            raise maintenance.MaintenanceError(msg)
        real(self, ledger)

    return save


def receipt_fault_once(real, *, saved: bool):
    """The first ledger save that notes a rewrite's receipt fails: before it is written, or once it was."""
    failed: list[bool] = []

    def save(self, ledger) -> None:
        if failed or not any(":receipt:" in m for m in ledger.imported):
            real(self, ledger)
            return
        failed.append(True)
        if saved:
            real(self, ledger)
        msg = "synthetic fault noting the receipt"
        raise maintenance.MaintenanceError(msg)

    return save


@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
@pytest.mark.parametrize("saved", [False, True], ids=["before-save", "after-save"])
def test_an_existing_hold_keeps_its_one_lease_when_the_receipt_for_the_constructors_rewrite_fails(
    tmp_path, machines, shared_repo, recovered, saved
):
    """Review on 8dfa: the rewrite carries its run's generation, so the lease survives a failed receipt either way.

    The project's store first could not open, so its running record without identity was held read-only as A. Once it
    opens, its Job rewrites that record and the receipt fails: the project falls back to the read-only path, and every
    later start still finds A alone, held or recovered. A later running record is held anew.
    """
    shared, _remote = shared_repo
    good, _clone_folder = open_project(tmp_path, shared, "good")
    other = registry.register(clone(tmp_path / "other"))
    settled = machines()
    settled.load_all()  # the store moves to its home folder, where every later read finds this record
    settled.stop_all()
    live = project_home.current(Path(good.path))
    fmt = live / "format"
    opens = fmt.read_text()
    fmt.write_text("99\n")  # this store will not open for now
    write_pack(live, {"state": "running"})  # no run id and no start: its identity is its file
    first = machines()
    first.load_all()
    [a] = held(first, good.id)
    assert first.projects[good.id].state == "failed"
    if recovered:
        reboot_then_recover(first, a["id"])
    first.stop_all()
    fmt.write_text(opens)

    faulted = machines()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(maintenance.Maintenance, "_save", receipt_fault_once(maintenance.Maintenance._save, saved=saved))  # noqa: SLF001
        faulted.load_all()
    rewritten = json.loads((live / pack_job.FILE).read_text())
    assert (faulted.projects[good.id].state, rewritten["state"], rewritten["reason"]) == (
        "failed", "failed", pack_state.HOST_STOPPED,
    )  # fmt: skip
    state = "recovered" if recovered else "held"
    assert [(s["id"], s["state"]) for s in sessions_of(faulted, good.id)] == [(a["id"], state)]
    faulted.stop_all()
    for _ in range(2):
        again = machines()
        again.load_all()
        assert [(s["id"], s["state"]) for s in sessions_of(again, good.id)] == [(a["id"], state)]
        assert (again.slots.take(other.id, "probe", 1, 1), again.maintenance.pending("pack")) == (
            (1, False) if recovered else (0, True)
        )
        again.slots.give(other.id, "probe")
        again.stop_all()
    write_pack(live, {"state": "running"})  # a later run, again without identity
    later = machines()
    later.load_all()
    assert [s["state"] for s in sessions_of(later, good.id)] == [state, "held"]


def test_the_carried_generation_counts_only_in_the_shape_of_this_hosts_own_rewrite():
    """A replacement in any other shape is judged by its own identity, so it can never borrow the carried run's."""
    carried = {"state": "failed", "reason": pack_state.HOST_STOPPED, pack_state.REWRITTEN: "observed:a"}
    assert pack_state.generation(carried, "v1")[0] == "observed:a"
    for other in ({"state": "running"}, {"reason": "candidate: RuntimeError: x"}, {"workspace": "/w"}):
        assert pack_state.generation(carried | other, "v1")[0] != "observed:a"


def test_a_failed_projects_pack_record_that_is_a_fifo_is_held_at_once_and_another_project_waits(tmp_path, machines):
    """Review 4375573453: restoring a project whose store cannot open never waits on a pipe at its record's name.

    The machine loads within a bound, holds that project's pack work as unreadable, and admits no other session.
    """
    bad, folder = store_too_new(tmp_path, "bad")
    os.mkfifo(folder / pack_job.FILE)
    other = registry.register(clone(tmp_path / "other"))
    m = machines()
    loading = threading.Thread(target=m.load_all, daemon=True)
    loading.start()
    loading.join(10)
    assert not loading.is_alive(), "loading the machine waited on the pack record"
    assert (m.projects[bad.id].state, [s["state"] for s in sessions_of(m, bad.id)]) == ("failed", ["held"])
    assert (m.slots.take(other.id, "probe", 1, 1), m.maintenance.pending("pack")) == (0, True)
