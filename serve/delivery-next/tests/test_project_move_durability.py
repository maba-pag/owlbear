"""A move publishes its copy durably before the switch, and its proof is the nonce the record issued.

Faults are injected into the public ``prepare_clone``/``finish_clone`` calls on a synthetic repository. The source
keeps every byte in each case, and a foreign entry is refused, never adopted or removed.
"""

import errno
import json
import os
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"


@pytest.fixture
def clone(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)  # noqa: S607
    folder = repo / ".git" / "owlbear-delivery"
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / "clone-id").write_text(f"{SOURCE_ID}\n")
    return repo, folder


def prepare(repo, monkeypatch):
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    offline_protocol.prepare_clone(repo, gaps=lambda: ())


def finish(repo, monkeypatch):
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return offline_protocol.finish_clone(repo, gaps=lambda: ())


def record(folder):
    return json.loads((folder / project_move.MOVE_RECORD).read_text())


def assert_source_whole(folder):
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / "clone-id").read_text() == f"{SOURCE_ID}\n"


def crash_once(monkeypatch, name, real):
    """Make the named fd_tree helper raise once, as a crash at that point would, then behave normally."""
    state = {"armed": True}

    def helper(*args, **kwargs):
        if state["armed"]:
            state["armed"] = False
            msg = "injected crash"
            raise RuntimeError(msg)
        return real(*args, **kwargs)

    monkeypatch.setattr(fd_tree, name, helper)


def test_a_failed_target_sync_leaves_the_copy_unswitched_and_the_retry_resyncs_it(clone, monkeypatch):
    repo, folder = clone
    prepare(repo, monkeypatch)
    real_sync_published = project_move._sync_published  # noqa: SLF001
    real_fsync = os.fsync
    runs = []
    state = {"inside": False, "failed": False}

    def sync_published(pfd, target, tfd):
        runs.append(0)
        state["inside"] = True
        try:
            real_sync_published(pfd, target, tfd)
        finally:
            state["inside"] = False

    def fsync(fd):
        if state["inside"]:
            runs[-1] += 1
            if not state["failed"]:
                state["failed"] = True
                raise OSError(errno.EIO, "injected target sync failure")
        real_fsync(fd)

    monkeypatch.setattr(project_move, "_sync_published", sync_published)
    monkeypatch.setattr(os, "fsync", fsync)

    with pytest.raises(StoreError, match="was not made durable"):
        finish(repo, monkeypatch)

    target = Path(record(folder)["target"])
    assert record(folder)["phase"] == project_move.COPYING
    assert target.is_dir()
    assert_source_whole(folder)

    finish(repo, monkeypatch)

    assert len(runs) == 2  # the retry ran the target sync again before it switched
    assert runs[1] > 0
    assert record(folder)["phase"] == project_move.SWITCHED
    assert project_home.located(repo) == target
    assert_source_whole(folder)


def test_a_crash_after_the_nonce_is_recorded_resumes_with_that_same_nonce(clone, monkeypatch):
    repo, folder = clone
    prepare(repo, monkeypatch)
    crash_once(monkeypatch, "create_verified_at", fd_tree.create_verified_at)

    with pytest.raises(RuntimeError, match="injected crash"):
        finish(repo, monkeypatch)

    nonce = record(folder)["proof"]
    assert nonce is not None
    assert not (Path(record(folder)["stage"]) / project_move.MOVE_PROOF).exists()

    finish(repo, monkeypatch)

    target = Path(record(folder)["target"])
    assert record(folder)["phase"] == project_move.SWITCHED
    assert (target / project_move.MOVE_PROOF).read_text() == f"{nonce}\n"
    assert_source_whole(folder)


def test_a_crash_mid_copy_keeps_the_partial_stage_and_restarts_with_a_fresh_nonce(clone, monkeypatch):
    repo, folder = clone
    prepare(repo, monkeypatch)
    crash_once(monkeypatch, "copy", fd_tree.copy)

    with pytest.raises(RuntimeError, match="injected crash"):
        finish(repo, monkeypatch)

    old_nonce = record(folder)["proof"]
    stage = Path(record(folder)["stage"])
    assert record(folder)["pending"] is not None
    assert (stage / project_move.MOVE_PROOF).read_text() == f"{old_nonce}\n"

    finish(repo, monkeypatch)

    kept = sorted(stage.parent.glob(f"{fd_tree.QUARANTINE}*"))
    assert len(kept) == 1, [p.name for p in kept]
    assert (kept[0] / project_move.MOVE_PROOF).read_text() == f"{old_nonce}\n"
    assert record(folder)["proof"] != old_nonce
    target = Path(record(folder)["target"])
    assert (target / project_move.MOVE_PROOF).read_text() == f"{record(folder)['proof']}\n"
    assert_source_whole(folder)


@pytest.mark.parametrize("kind", ["regular", "symlink"])
def test_a_foreign_proof_entry_after_a_crash_before_its_file_is_refused_and_kept(clone, monkeypatch, tmp_path, kind):
    repo, folder = clone
    prepare(repo, monkeypatch)
    crash_once(monkeypatch, "create_verified_at", fd_tree.create_verified_at)
    with pytest.raises(RuntimeError, match="injected crash"):
        finish(repo, monkeypatch)
    stage = Path(record(folder)["stage"])
    proof = stage / project_move.MOVE_PROOF
    foreign = tmp_path / "foreign-target"
    foreign.write_text("foreign\n")
    if kind == "regular":
        proof.write_text("foreign\n")
    else:
        proof.symlink_to(foreign)

    with pytest.raises(StoreError):
        finish(repo, monkeypatch)

    assert not Path(record(folder)["target"]).exists()
    if kind == "regular":
        assert proof.read_text() == "foreign\n"
    else:
        assert proof.is_symlink()
        assert proof.readlink() == foreign
    assert foreign.read_text() == "foreign\n"
    assert_source_whole(folder)
