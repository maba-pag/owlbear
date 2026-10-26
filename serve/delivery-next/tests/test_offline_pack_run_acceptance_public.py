"""A held design-pack run survives the public Prepare and Finish move, and Finish never writes the ledger.

Each case runs the real ``cli.main`` Prepare and Finish on a real git clone with a temporary HOME. The reboot is
modeled by changing the boot session id. The Finish move copies the store into a different target root, so the
carried run record must be a different file on a different inode.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import local_home, maintenance
from owlbear_delivery_next.pack_runs import pack_state
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000011"
AFTER = "BBBBBBBB-0000-4000-8000-000000000012"
RUN_A = "run-a"
STARTED_A = "2026-01-01T00:00:00+00:00"


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(path)
    folder.mkdir(parents=True)
    (folder / MARKER).write_text("7")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    return path


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def _source(repo: Path) -> Path:
    return project_home.clone_dir(repo)


def _run_record(run: str, started: str, state: str = "running") -> dict:
    record = pack_state.blank()
    record |= {"state": state, "run": run, "started_at": started, "reason": ""}
    if state == "running":
        record["stage"] = "update"
        next(s for s in record["stages"] if s["name"] == "update")["result"] = "running"
    return record


def _write_run(folder: Path, record: dict) -> None:
    (folder / pack_state.FILE).write_text(json.dumps(record, indent=1) + "\n")


def _prepared(repo: Path, boot: dict) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER


def _refused(repo: Path, capsys) -> bool:
    try:
        code = cli.main(["--repo", str(repo), "finish"])
    except StoreError, maintenance.MaintenanceError:
        code = None
    capsys.readouterr()
    return code in (None, 1)


@pytest.mark.usefixtures("current_binding")
def test_a_held_run_survives_the_public_move_into_a_new_root_and_two_restarts(repo, boot, capsys):
    _prepared(repo, boot)
    source = _source(repo)
    _write_run(source, _run_record(RUN_A, STARTED_A))
    source_inode = (source / pack_state.FILE).stat().st_ino

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()

    target = Store.open(repo).root
    assert target != source
    carried_path = target / pack_state.FILE
    assert carried_path.stat().st_ino != source_inode, "the run record was not copied into the new root"
    carried = json.loads(carried_path.read_text())
    assert carried["state"] == "failed"
    assert carried["reason"] == pack_state.HOST_STOPPED
    assert carried[pack_state.REWRITTEN] == f"{RUN_A}:{STARTED_A}"
    assert carried["run"] == RUN_A
    assert carried["started_at"] == STARTED_A
    assert json.loads((source / pack_state.FILE).read_text())["run"] == RUN_A, "the source record was lost"

    first = carried_path.read_bytes()
    assert Store.open(repo).root == target
    assert carried_path.read_bytes() == first, "the first restart changed the carried run record"
    assert Store.open(repo).root == target
    assert carried_path.read_bytes() == first, "the second restart changed the carried run record"


@pytest.mark.usefixtures("current_binding")
def test_finish_reads_the_ledger_statically_and_writes_nothing_to_it(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)
    _write_run(_source(repo), _run_record(RUN_A, STARTED_A))
    ledger = local_home.root() / maintenance.FILE
    assert not ledger.exists(), "a missing ledger is the empty ledger, so this case starts without one"

    constructed: list[object] = []
    original_init = maintenance.Maintenance.__init__

    def spy_init(self, *args, **kwargs):
        constructed.append(args)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(maintenance.Maintenance, "__init__", spy_init)

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()

    assert constructed == [], "Finish constructed Maintenance, which is not host-free"
    assert not ledger.exists(), "Finish created the ledger"
    assert json.loads((Store.open(repo).root / pack_state.FILE).read_text())[pack_state.REWRITTEN] == (
        f"{RUN_A}:{STARTED_A}"
    )


@pytest.mark.usefixtures("current_binding")
def test_a_malformed_move_record_refuses_before_the_source_record_is_settled_or_copied(repo, boot, capsys):
    _prepared(repo, boot)
    source = _source(repo)
    _write_run(source, _run_record(RUN_A, STARTED_A))
    run_bytes = (source / pack_state.FILE).read_bytes()
    (source / project_move.MOVE_RECORD).write_text('{"not": "a move record"}\n')

    assert _refused(repo, capsys), "a malformed move record was taken for no move record"
    assert (source / pack_state.FILE).read_bytes() == run_bytes, "the run record was settled before the refusal"
    assert (source / project_move.MOVE_RECORD).read_text() == '{"not": "a move record"}\n'


@pytest.mark.usefixtures("current_binding")
def test_a_fifo_ledger_refuses_finish_before_any_copy_and_leaves_the_store_in_place(repo, boot, capsys):
    _prepared(repo, boot)
    source = _source(repo)
    _write_run(source, _run_record(RUN_A, STARTED_A))
    run_bytes = (source / pack_state.FILE).read_bytes()
    ledger = local_home.root() / maintenance.FILE
    ledger.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(ledger)

    assert _refused(repo, capsys), "a FIFO ledger was read as an empty or valid one"
    assert project_move.record(source) is None, "a move was started before the ledger was read"
    assert (source / pack_state.FILE).read_bytes() == run_bytes
