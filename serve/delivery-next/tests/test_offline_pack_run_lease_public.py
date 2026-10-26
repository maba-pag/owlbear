"""A held or recovered design-pack run is carried through the public Prepare and Finish move with exactly one lease.

Each case registers a real git clone, holds the legacy run with the real ``Machine`` loader while its store will not
open, then runs the real ``cli.main`` Prepare and Finish. The reboot is modeled by changing the boot session ids. Every
restart is a fresh ``Machine``, so each check reads the lease ledger again.
"""

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import codebase, local_home, maintenance
from owlbear_delivery_next.machine_host import project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.pack_runs import pack_job, pack_run, pack_state
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move, registry
from owlbear_delivery_next.state_store.database import MARKER
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000011"
AFTER = "BBBBBBBB-0000-4000-8000-000000000012"
RUN_A = "run-a"
STARTED_A = "2026-01-01T00:00:00+00:00"
RUN_B = "run-b"
STARTED_B = "2026-02-01T00:00:00+00:00"
ENDED_B = "2026-02-01T01:00:00+00:00"
TOO_NEW = "99\n"
SENTINEL = "retained-sentinel.txt"


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    return path


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


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


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    return path.resolve()


def head_of(repo: Path) -> str:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), "rev-parse", "HEAD"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = clone(tmp_path / "shop")
    folder = project_home.clone_dir(path)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / MARKER).write_text("7")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    return path


def _run_record(run: str, started: str, state: str = "running") -> dict:
    """A run record; with no run id and no start, its identity is its file, as a legacy record without identity is."""
    record = pack_state.blank()
    record |= {"state": state, "run": run, "started_at": started, "reason": ""}
    if state == "running":
        record["stage"] = "update"
        next(s for s in record["stages"] if s["name"] == "update")["result"] = "running"
    return record


def _write_run(folder: Path, record: dict) -> None:
    (folder / pack_state.FILE).write_text(json.dumps(record, indent=1) + "\n")
    (folder / pack_run.UPDATER).mkdir(exist_ok=True)


def sessions_of(machine: Machine, project_id: str) -> list[tuple[str, str]]:
    return [(s["id"], s["state"]) for s in machine.maintenance.read()["sessions"] if s["project"] == project_id]


def held_of(machine: Machine, project_id: str) -> list[dict]:
    return [s for s in machine.maintenance.read()["sessions"] if s["project"] == project_id and s["state"] == "held"]


def reboot_then_recover(machine: Machine, ident: str) -> None:
    booted = machine.maintenance.boot
    machine.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the hold
    machine.maintenance.recover(ident, rebooted=True)


def _store(repo: Path) -> Path:
    """The moved store as it lies now, read without opening (and so without touching) the database."""
    root = project_home.current(repo)
    assert root is not None, "the project's store is not named"
    return root


def lease_record(lease_id: str) -> dict:
    """One lease as the ledger file holds it; no manager runs, so no sweep or save can change the bytes checked."""
    ledger = json.loads((local_home.root() / maintenance.FILE).read_bytes())
    [lease] = [s for s in ledger["sessions"] if s["id"] == lease_id]
    return lease


def workspaces_of(machine: Machine, project_id: str) -> dict[str, str]:
    return {s["id"]: s["workspace"] for s in machine.maintenance.read()["sessions"] if s["project"] == project_id}


def _keep_workspace(lease_id: str) -> tuple[str, Path, bytes]:
    """A held run's ledger workspace before the move: its folder exists and holds a sentinel the move must not touch."""
    recorded = lease_record(lease_id)["workspace"]
    workspace = Path(recorded)
    assert workspace.is_dir(), "the held run's workspace is absent before the move"
    sentinel = workspace / SENTINEL
    sentinel.write_text("kept\n")
    return recorded, sentinel, sentinel.read_bytes()


def _assert_workspace_kept(lease_id: str, kept: tuple[str, Path, bytes], target: Path) -> None:
    """The lease still names its original workspace, which is not rebound into the target root, and that
    workspace's original sentinel is unchanged. A copy of the folder in the target is not a failure."""
    recorded, sentinel, content = kept
    assert lease_record(lease_id)["workspace"] == recorded
    assert not Path(recorded).is_relative_to(target), "the lease was rebound to a copy in the target root"
    assert Path(recorded).is_dir(), "the held run's workspace was removed"
    assert sentinel.read_bytes() == content, "the workspace sentinel changed"


def _hold_a(machines, repo: Path, *, recovered: bool, identified: bool = True) -> tuple[str, str]:
    """The legacy run A held by the real loader while its store will not open, then recovered when asked."""
    entry = registry.register(repo)
    folder = project_home.clone_dir(repo)
    (folder / MARKER).write_text(TOO_NEW)
    _write_run(folder, _run_record(RUN_A, STARTED_A) if identified else _run_record("", ""))
    first = machines()
    first.load_all()
    [a] = [s for s in first.maintenance.read()["sessions"] if s["project"] == entry.id]
    if recovered:
        reboot_then_recover(first, a["id"])
    first.stop_all()
    (folder / MARKER).write_text("7")
    return entry.id, a["id"]


def _state(*, recovered: bool) -> str:
    return "recovered" if recovered else "held"


def main_stage_failure(folder: Path, stage: str, reason: str, run: str) -> None:
    """The R04 owner's fixture shape (test_maintenance_legacy_generation): what main leaves when one stage's work
    raised. It writes the record main's ``_finish`` leaves; it is not a live producer call."""
    ended = {"state": "failed", "run": run, "started_at": STARTED_B, "ended_at": ENDED_B, "reason": reason}
    body = pack_job._blank() | ended  # noqa: SLF001
    body["stages"] = [s | {"result": "failed", "detail": reason} if s["name"] == stage else s for s in body["stages"]]
    (folder / pack_job.FILE).write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8")
    shutil.rmtree(folder / pack_run.UPDATER, ignore_errors=True)


def _prepared(repo: Path, boot: dict) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER


def _move_held_a(  # noqa: PLR0913
    machines, repo: Path, boot: dict, capsys, *, recovered: bool, identified: bool
) -> tuple[str, str, dict, tuple[str, Path, bytes], bytes]:
    """Hold A, then run the public Prepare and Finish; return the project id, A's id, the carried run record, A's
    kept workspace and the source run record as Finish settled it (its bytes are stable from here on)."""
    project_id, a_id = _hold_a(machines, repo, recovered=recovered, identified=identified)
    source = project_home.clone_dir(repo)
    source_inode = (source / pack_state.FILE).stat().st_ino
    kept = _keep_workspace(a_id)
    head = head_of(repo)
    _prepared(repo, boot)
    ledger = local_home.root() / maintenance.FILE
    ledger_before = ledger.read_bytes()

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    assert ledger.read_bytes() == ledger_before
    settled = (source / pack_state.FILE).read_bytes()

    target = _store(repo)
    assert target != source
    carried_path = target / pack_state.FILE
    assert carried_path.stat().st_ino != source_inode
    assert (source / pack_state.FILE).is_file(), "the source run record was lost"
    assert head_of(repo) == head
    _assert_workspace_kept(a_id, kept, target)
    return project_id, a_id, json.loads(carried_path.read_text()), kept, settled


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("identified", [True, False], ids=["identified", "unidentified"])
@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
def test_a_held_or_recovered_run_moves_into_a_new_root_and_two_fresh_managers_find_exactly_one_lease(  # noqa: PLR0913, PLR0917
    repo, boot, machines, recovered, identified, capsys
):
    project_id, a_id, carried, kept, settled = _move_held_a(
        machines, repo, boot, capsys, recovered=recovered, identified=identified
    )
    if identified:
        assert carried[pack_state.REWRITTEN] == f"{RUN_A}:{STARTED_A}"
    else:
        assert carried.get(pack_state.REWRITTEN), "the unidentified run was carried without its generation"

    for _ in range(2):
        again = machines()
        again.load_all()
        assert sessions_of(again, project_id) == [(a_id, _state(recovered=recovered))]
        assert workspaces_of(again, project_id) == {a_id: kept[0]}
        _assert_workspace_kept(a_id, kept, _store(repo))
        assert (project_home.clone_dir(repo) / pack_state.FILE).read_bytes() == settled
        again.stop_all()


@pytest.mark.usefixtures("current_binding")
def test_meta_without_the_settle_hook_the_unidentified_run_is_carried_unstamped(
    repo, boot, machines, capsys, monkeypatch
):
    """Meta-negative control, not acceptance: the settle hook is replaced by an in-memory no-op. The carried record
    then has no generation, which is the omission the unidentified acceptance case above must catch."""
    monkeypatch.setattr(offline_protocol, "_settle_pack_run", lambda _folder: None)
    _, _, carried, _, _ = _move_held_a(machines, repo, boot, capsys, recovered=False, identified=False)
    assert pack_state.REWRITTEN not in carried


def _adopt_under_receipt_fault(machine: Machine, folder: Path, key: str, *, saved: bool, monkeypatch) -> None:
    """The production adopter on the carried run at its store folder, with the first receipt-noting save faulted.

    A raw ``Store`` and ``Job`` are built directly, so no full host load runs before the move's proof.
    """
    job = pack_job.Job(Store(folder))
    job.maintenance = machine.maintenance
    failed: list[bool] = []
    real_save = maintenance.Maintenance._save  # noqa: SLF001

    def fault_receipt(self, ledger) -> None:
        if failed or not any(":receipt:" in m for m in ledger.imported):
            real_save(self, ledger)
            return
        failed.append(True)
        if saved:
            real_save(self, ledger)
        msg = "synthetic fault noting the receipt"
        raise maintenance.MaintenanceError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(maintenance.Maintenance, "_save", fault_receipt)
        with pytest.raises(maintenance.MaintenanceError, match="synthetic fault noting the receipt"):
            session_slots.interrupted(job, key)
    assert failed, "the receipt fault never fired"


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("saved", [False, True], ids=["before-save", "after-save"])
@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
def test_a_receipt_fault_during_the_legacy_adoption_keeps_one_lease_through_the_public_move(  # noqa: PLR0913, PLR0917
    repo, boot, machines, recovered, saved, capsys, monkeypatch
):
    project_id, a_id = _hold_a(machines, repo, recovered=recovered, identified=False)
    source = project_home.clone_dir(repo)
    kept = _keep_workspace(a_id)
    adopter = machines()
    _adopt_under_receipt_fault(adopter, source, project_id, saved=saved, monkeypatch=monkeypatch)
    adopter.stop_all()
    _prepared(repo, boot)
    ledger = local_home.root() / maintenance.FILE
    ledger_before = ledger.read_bytes()

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    assert ledger.read_bytes() == ledger_before
    settled = (source / pack_state.FILE).read_bytes()
    _assert_workspace_kept(a_id, kept, _store(repo))

    for _ in range(2):
        again = machines()
        again.load_all()
        assert sessions_of(again, project_id) == [(a_id, _state(recovered=recovered))]
        assert workspaces_of(again, project_id) == {a_id: kept[0]}
        _assert_workspace_kept(a_id, kept, _store(repo))
        assert (source / pack_state.FILE).read_bytes() == settled
        again.stop_all()


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
def test_a_later_genuine_run_is_held_on_its_own_and_blocks_admission_even_after_a_was_recovered(  # noqa: PLR0913, PLR0917
    repo, boot, machines, recovered, capsys, tmp_path
):
    """B is a MODELED input: the R04 owner's stage-failure record shape and its slot proof, not a live producer call."""
    project_id, a_id = _hold_a(machines, repo, recovered=recovered)
    _prepared(repo, boot)
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    other = registry.register(clone(tmp_path / "other"))
    main_stage_failure(_store(repo), "update", "update: RuntimeError: synthetic SDK failure", run=RUN_B)

    later = machines()
    later.load_all()
    [b] = [s for s in held_of(later, project_id) if s["id"] != a_id]
    assert b["id"] != a_id
    assert sessions_of(later, project_id) == [(a_id, _state(recovered=recovered)), (b["id"], "held")]
    assert (later.slots.take(other.id, "probe", 1, 1), later.maintenance.pending("pack")) == (0, True)
    later.stop_all()


@pytest.mark.usefixtures("current_binding")
def test_finish_resumes_a_copy_in_progress_without_settling_the_run_record(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)
    source = project_home.clone_dir(repo)
    _write_run(source, _run_record(RUN_A, STARTED_A))

    settled: list[object] = []
    monkeypatch.setattr(pack_state, "settle", lambda *args, **_kwargs: settled.append(args) or False)

    def interrupt(*_args, **_kwargs) -> None:
        msg = "synthetic interruption after the copy began"
        raise OSError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(project_move, "_copy_each", interrupt)  # after the stage proof is recorded, before any copy
        with pytest.raises(OSError, match="synthetic interruption after the copy began"):
            cli.main(["--repo", str(repo), "finish"])
    capsys.readouterr()
    assert project_move.record(source) is not None, "the copy was not left in progress"
    assert len(settled) == 1, "the first Finish did not settle the run before copying"
    settled.clear()

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    assert settled == [], "Finish settled the run record while a copy was in progress"


@pytest.mark.usefixtures("current_binding")
def test_a_receipt_for_an_unregistered_project_is_used_by_clone_id(repo, boot, capsys):
    folder = project_home.clone_dir(repo)
    _write_run(folder, _run_record(RUN_A, STARTED_A))
    clone_id = project_home.ensure_id(folder)
    digest = pack_state.digest(pack_state.observed(folder)[1])
    maintenance.Maintenance(
        type("Slots", (), {"restore_one": lambda *_a: None})(),
        boot=lambda: 0.0,
        observe=lambda _pid, _created: True,
    ).receipt(clone_id, digest, "receipted-gen-1")
    _prepared(repo, boot)

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    carried = json.loads((_store(repo) / pack_state.FILE).read_text())
    assert carried[pack_state.REWRITTEN] == "receipted-gen-1"
