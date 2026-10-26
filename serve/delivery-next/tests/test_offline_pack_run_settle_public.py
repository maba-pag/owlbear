"""A design-pack run left by an older host is settled by the public Finish before the store is copied.

Each case runs the real ``cli.main`` Prepare and Finish on a real git clone. HOME is a temporary directory, so the
maintenance ledger is real and local to the test. The reboot is modeled by changing the boot session id, and the
receipts are written by the real ``Maintenance.receipt`` writer.
"""

import errno
import json
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import local_home, maintenance
from owlbear_delivery_next.pack_runs import pack_state
from owlbear_delivery_next.state_store import offline_protocol, pack_run_record, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000011"
AFTER = "BBBBBBBB-0000-4000-8000-000000000012"
RUN_A = "run-a"
STARTED_A = "2026-01-01T00:00:00+00:00"
RUN_B = "run-b"
STARTED_B = "2026-02-01T00:00:00+00:00"


class _Slots:
    def restore_one(self, *_args) -> None:
        return None


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


def _run_record(run: str, started: str, state: str = "running", reason: str = "") -> dict:
    record = pack_state.blank()
    record |= {"state": state, "run": run, "started_at": started, "reason": reason}
    if state == "running":
        record["stage"] = "update"
        next(s for s in record["stages"] if s["name"] == "update")["result"] = "running"
    return record


def _write_run(folder: Path, record: dict) -> None:
    (folder / pack_state.FILE).write_text(json.dumps(record, indent=1) + "\n")


def _prepared(repo: Path, boot: dict) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER


def _receipt(repo: Path, generation: str, version: str | None = None) -> None:
    """Record, as the real ledger writer does, that *version* of the run file is the rewrite of *generation*."""
    folder = _source(repo)
    clone = project_home.clone_id(folder)
    assert clone is not None
    digest = pack_state.digest(version or pack_state.observed(folder)[1])
    maintenance.Maintenance(_Slots(), boot=lambda: 0.0, observe=lambda _pid, _created: True).receipt(
        clone, digest, generation
    )


def _finish_refused(repo: Path, capsys) -> bool:
    try:
        code = cli.main(["--repo", str(repo), "finish"])
    except StoreError:
        code = None
    capsys.readouterr()
    return code in (None, 1)


@pytest.mark.usefixtures("current_binding")
def test_held_run_is_settled_by_finish_and_carried_into_the_target(repo, boot, capsys):
    _prepared(repo, boot)
    _write_run(_source(repo), _run_record(RUN_A, STARTED_A))
    assert not (Path.home() / ".owlbear" / maintenance.FILE).exists(), "no ledger: the receipt lookup is empty"

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()

    carried = json.loads((Store.open(repo).root / pack_state.FILE).read_text())
    assert carried["state"] == "failed"
    assert carried["reason"] == pack_state.HOST_STOPPED
    assert carried[pack_state.REWRITTEN] == f"{RUN_A}:{STARTED_A}"
    assert carried["run"] == RUN_A
    assert carried["started_at"] == STARTED_A


@pytest.mark.usefixtures("current_binding")
def test_receipted_generation_for_the_same_bytes_wins_over_the_record(repo, boot, capsys):
    _prepared(repo, boot)
    _write_run(_source(repo), _run_record(RUN_A, STARTED_A, state="failed", reason="the updater may still be running"))
    _receipt(repo, "receipted-gen-1")

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()

    carried = json.loads((Store.open(repo).root / pack_state.FILE).read_text())
    assert carried[pack_state.REWRITTEN] == "receipted-gen-1"


@pytest.mark.usefixtures("current_binding")
def test_receipt_for_other_bytes_is_not_used_for_a_later_run(repo, boot, capsys):
    _prepared(repo, boot)
    _receipt(repo, "stale-gen", version="some-other-version")
    _write_run(_source(repo), _run_record(RUN_B, STARTED_B))

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()

    carried = json.loads((Store.open(repo).root / pack_state.FILE).read_text())
    assert carried[pack_state.REWRITTEN] == f"{RUN_B}:{STARTED_B}"


@pytest.mark.usefixtures("current_binding")
def test_unreadable_ledger_refuses_finish_before_any_copy_or_switch(repo, boot, capsys):
    _prepared(repo, boot)
    _write_run(_source(repo), _run_record(RUN_A, STARTED_A))
    record_bytes = (_source(repo) / pack_state.FILE).read_bytes()
    (local_home.root() / maintenance.FILE).write_text("{not a ledger")

    assert _finish_refused(repo, capsys), "an unreadable ledger was settled through"
    assert project_move.record(_source(repo)) is None, "a move was started before the run record was settled"
    assert (_source(repo) / pack_state.FILE).read_bytes() == record_bytes


@pytest.mark.usefixtures("current_binding")
def test_failed_rewrite_of_the_run_record_refuses_finish_before_any_copy(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)
    _write_run(_source(repo), _run_record(RUN_A, STARTED_A))
    record_bytes = (_source(repo) / pack_state.FILE).read_bytes()

    def fail_write(*_args, **_kwargs):
        msg = "injected write failure"
        raise OSError(errno.EIO, msg)

    monkeypatch.setattr(pack_run_record, "atomic_write", fail_write)

    assert _finish_refused(repo, capsys), "a failed rewrite of the run record was taken for a settled one"
    assert project_move.record(_source(repo)) is None, "a move was started before the run record was settled"
    assert (_source(repo) / pack_state.FILE).read_bytes() == record_bytes


@pytest.mark.usefixtures("current_binding")
def test_settling_again_after_a_restart_changes_nothing(repo, boot, capsys):
    _prepared(repo, boot)
    _write_run(_source(repo), _run_record(RUN_A, STARTED_A))
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    carried_bytes = (Store.open(repo).root / pack_state.FILE).read_bytes()

    assert pack_run_record.settle(Store.open(repo).root, receipted=lambda _digest: "") is False
    assert (Store.open(repo).root / pack_state.FILE).read_bytes() == carried_bytes


@pytest.mark.usefixtures("current_binding")
def test_a_settled_or_finished_record_is_left_alone_by_finish(repo, boot, capsys):
    _prepared(repo, boot)
    passed = _run_record(RUN_A, STARTED_A, state="passed")
    _write_run(_source(repo), passed)

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()

    carried = json.loads((Store.open(repo).root / pack_state.FILE).read_text())
    assert pack_state.REWRITTEN not in carried
    assert carried["state"] == "passed"
