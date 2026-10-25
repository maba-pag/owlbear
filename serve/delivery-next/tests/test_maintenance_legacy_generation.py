"""A pre-ledger pack run is held once per its proven identity; a restart after recovery never holds it again."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import project, registry
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.pack_runs import pack_job, pack_run
from owlbear_delivery_next.project_host.host import Host, HostRecord
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
