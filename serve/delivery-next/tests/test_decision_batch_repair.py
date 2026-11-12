"""Isolated regressions for the decision-batch journal, publish and recovery repairs; no Git server or model is used."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.state_store import decision_batch


@pytest.mark.parametrize(("code", "out", "error"), [(128, "", "fatal: not a git repository"), (0, "\n", "")])
def test_external_rebase_probe_failure_is_never_idle_git(tmp_path: Path, monkeypatch, code, out, error) -> None:
    def probe(_cwd: Path, *args: str, **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, code, out, error)

    monkeypatch.setattr(data_repo, "_git", probe)
    with pytest.raises(DataRepoError, match="cannot tell whether a rebase is in progress"):
        DataRepo(tmp_path).rebasing()


def test_replace_file_fsyncs_the_parent_after_rename_and_after_unlink(tmp_path: Path, monkeypatch) -> None:
    synced: list[os.stat_result] = []
    real_fsync = os.fsync

    def recording_fsync(descriptor: int) -> None:
        found = os.fstat(descriptor)
        if stat.S_ISDIR(found.st_mode):
            synced.append(found)
        real_fsync(descriptor)

    monkeypatch.setattr(decision_batch, "fsync_dir", synced.append)
    target = tmp_path / "decision.json"

    with monkeypatch.context() as m:
        m.setattr(os, "fsync", recording_fsync)
        decision_batch.replace_file(target, b"after")
    assert target.read_bytes() == b"after"
    assert all(isinstance(found, os.stat_result) for found in synced)  # the rename's folder, through its descriptor
    assert any(os.path.samestat(found, tmp_path.stat()) for found in synced)

    synced.clear()
    with monkeypatch.context() as m:
        m.setattr(os, "fsync", recording_fsync)
        decision_batch.replace_file(target, None)
    assert not target.exists()
    assert [os.path.samestat(found, tmp_path.stat()) for found in synced] == [True]  # the unlink's folder, too
