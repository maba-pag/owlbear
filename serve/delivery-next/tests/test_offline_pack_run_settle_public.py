"""Public Finish refuses before copying or switching when move evidence or settlement fails."""

import json
import os
import subprocess

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.impeccable_runs import pack_state
from owlbear_delivery_next.local_system import local_home, maintenance
from owlbear_delivery_next.state_store import fd_tree, offline_protocol, pack_run_record, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError

BEFORE = "AAAAAAAA-0000-4000-8000-000000000011"
AFTER = "BBBBBBBB-0000-4000-8000-000000000012"


@pytest.fixture
def prepared(tmp_path, monkeypatch, request):
    request.getfixturevalue("current_binding")
    repo = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, capture_output=True)  # noqa: S603, S607
    source = project_home.clone_dir(repo)
    source.mkdir(parents=True)
    (source / MARKER).write_text("7")
    (source / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    (source / pack_state.FILE).write_text(json.dumps(pack_state.blank() | {"state": "running", "run": "a"}))
    return repo, source


def refused(repo, source, before):
    try:
        result = cli.main(["--repo", str(repo), "finish"])
    except StoreError, maintenance.MaintenanceError:
        result = None
    assert result in (None, 1)
    assert (source / pack_state.FILE).read_bytes() == before


def test_finish_refuses_invalid_move_before_settlement(prepared):
    repo, source = prepared
    before = (source / pack_state.FILE).read_bytes()
    target = project_home.home(project_home.clone_id(source))
    assert not target.exists()
    move = source / project_move.MOVE_RECORD
    move.write_text('{"not": "a move record"}\n')
    refused(repo, source, before)
    assert move.read_text() == '{"not": "a move record"}\n'
    assert not target.exists()


@pytest.mark.parametrize("kind", ["malformed", "fifo"])
def test_finish_refuses_unreadable_ledger_before_copy(prepared, kind):
    repo, source = prepared
    before = (source / pack_state.FILE).read_bytes()
    ledger = local_home.root() / maintenance.FILE
    ledger.parent.mkdir(parents=True, exist_ok=True)
    if kind == "fifo":
        os.mkfifo(ledger)
    else:
        ledger.write_text("{not a ledger")
    refused(repo, source, before)
    assert project_move.record(source) is None
    assert project_home.current(repo) == source


def test_finish_refuses_failed_record_rewrite_before_copy(prepared, monkeypatch):
    repo, source = prepared
    before = (source / pack_state.FILE).read_bytes()
    real_write, faults = fd_tree.write_at, []

    def interrupted(dfd, name, text, **kwargs):
        if name != pack_run_record.FILE:
            return real_write(dfd, name, text, **kwargs)
        faults.append(name)
        msg = "interrupted descriptor-bound rewrite"
        raise OSError(msg)

    monkeypatch.setattr(fd_tree, "write_at", interrupted)
    refused(repo, source, before)
    assert faults == [pack_run_record.FILE]
    assert project_move.record(source) is None
    assert project_home.current(repo) == source
