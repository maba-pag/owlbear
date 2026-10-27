"""Prepare keeps its marker and preparation observations through real id and temporary-file syncs."""

import json
import os
import stat
import subprocess

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
OWNER_BOOT = "CCCCCCCC-0000-4000-8000-000000000003"
pytestmark = pytest.mark.usefixtures("current_binding")


@pytest.fixture
def source(tmp_path, monkeypatch):
    repo = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(repo)
    folder.mkdir()
    (folder / MARKER).write_text("7")
    (folder / project_home.CLONE_ID).write_text("owned\n")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    return repo, folder


def snapshot(folder):
    return {
        p.name: p.read_bytes()
        for p in folder.iterdir()
        if p.is_file() and not p.name.startswith((".tmp-", fd_tree.QUARANTINE))
    }


def owner_preparation(folder):
    identity = folder.stat()
    return json.dumps({"boot": OWNER_BOOT, "folder": [identity.st_dev, identity.st_ino], "marker": "7"}) + "\n"


def assert_no_move():
    assert not (local_home.root() / project_home.PROJECTS).exists()


def change_source(folder, aside, change):
    if change == "source":
        folder.rename(aside)
        folder.mkdir()
        (folder / "owner").write_text("foreign source\n")
    elif change in {"new-preparation", "old-preparation"}:
        (folder / offline_protocol.PREPARED).write_text(owner_preparation(folder) + " ")
    elif change == "absent":
        (folder / MARKER).unlink()
    else:
        (folder / MARKER).write_text({"marker": "6\n", "future": "8\n", "blank": ""}[change])


def prepare(repo, public):
    if public == "cli":
        return cli.main(["--repo", str(repo), "prepare"]) == 1
    try:
        offline_protocol.prepare_clone(repo)
    except StoreError:
        return True
    return False


@pytest.mark.parametrize("public", ["cli", "prepare-clone"])
@pytest.mark.parametrize("marker", ["8", "998", "1000", "", " \n", "6\n", "7\n", None])
def test_prepare_refuses_a_marker_changed_during_the_first_real_id_sync(source, monkeypatch, public, marker):
    repo, folder = source
    fired, expected = [], {}

    class SyncingOS:
        def __getattr__(self, name):
            return getattr(os, name)

        def fsync(self, fd):
            os.fsync(fd)
            if fired or not stat.S_ISREG(os.fstat(fd).st_mode):
                return
            assert os.path.samestat(os.fstat(fd), (folder / project_home.CLONE_ID).stat())
            fired.append(True)
            if marker is None:
                (folder / MARKER).unlink()
            else:
                (folder / MARKER).write_text(marker)
            expected.update(snapshot(folder))

    monkeypatch.setattr(project_home, "os", SyncingOS())
    refused = prepare(repo, public)

    assert fired == [True], "the real ensure_pinned file sync was not reached"
    assert refused, "Prepare admitted a marker changed during the real clone-id sync"
    assert snapshot(folder) == expected
    assert not (folder / offline_protocol.PREPARED).exists()
    assert not (folder / project_move.MOVE_RECORD).exists()
    assert_no_move()


@pytest.mark.parametrize("when", ["id", "preparation", "fence"])
@pytest.mark.parametrize(
    "change", ["marker", "future", "blank", "absent", "new-preparation", "old-preparation", "source"]
)
def test_prepare_rechecks_its_snapshot_after_blocking_writes_before_each_publication(source, monkeypatch, when, change):
    repo, folder = source
    prepared = folder / offline_protocol.PREPARED
    if change == "old-preparation":
        prepared.write_text(owner_preparation(folder))
    aside = folder.with_name("original")
    original = {}
    fired, expected = [], {}

    class SyncingOS:
        def __getattr__(self, name):
            return getattr(os, name)

        def fsync(self, fd):
            os.fsync(fd)
            if fired or not stat.S_ISREG(os.fstat(fd).st_mode):
                return
            if when == "id":
                path = folder / project_home.CLONE_ID
            else:
                name = offline_protocol.PREPARED if when == "preparation" else MARKER
                path = next(folder.glob(f".tmp-{name}-*"), None)
            if path is None or not os.path.samestat(os.fstat(fd), path.stat()):
                return
            fired.append(True)
            original.update(snapshot(folder))
            change_source(folder, aside, change)
            expected.update(snapshot(folder))

    monkeypatch.setattr(project_home if when == "id" else fd_tree, "os", SyncingOS())
    refused = prepare(repo, "prepare-clone")

    assert fired == [True], f"the real {when} file sync was not reached"
    assert refused, "Prepare admitted a source changed during a real file sync"
    assert snapshot(folder) == expected, "Prepare overwrote the owner's marker or preparation"
    if change == "source":
        assert snapshot(aside) == original
    assert not (folder / project_move.MOVE_RECORD).exists()
    assert_no_move()


def test_repeated_prepare_preserves_the_original_valid_witness(source, monkeypatch):
    repo, folder = source
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    before = snapshot(folder)
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: OWNER_BOOT)

    assert cli.main(["--repo", str(repo), "prepare"]) == 0

    assert snapshot(folder) == before
    assert json.loads((folder / offline_protocol.PREPARED).read_text())["boot"] == BEFORE
    assert_no_move()


def test_an_unfenced_interrupted_prepare_can_resume_its_own_witness(source):
    repo, folder = source
    (folder / offline_protocol.PREPARED).write_text(owner_preparation(folder))

    assert cli.main(["--repo", str(repo), "prepare"]) == 0

    record = json.loads((folder / offline_protocol.PREPARED).read_text())
    assert record["boot"] == BEFORE
    assert record["marker"] == "7"
    assert (folder / MARKER).read_text() == f"{project_move.FENCE}\n"
    assert_no_move()
