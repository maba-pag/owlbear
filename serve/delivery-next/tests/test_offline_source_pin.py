"""The offline proof is bound to the source folder's descriptor: a swap before or after it is refused, never written to.

Each swap happens at the exact seam the production code crosses: the ``gaps`` callable runs after Prepare has pinned
the folder and before it reads or writes anything; the proof is issued, then the path is swapped before the move
opens the folder. The boot session is the only synthetic witness.
"""

import subprocess

import pytest

from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"
PREPARED = offline_protocol.PREPARED


def make_clone(root):
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)  # noqa: S607
    folder = project_home.clone_dir(repo)
    folder.mkdir()
    return repo, folder


def seed_retained_log(folder):
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / "clone-id").write_text(f"{SOURCE_ID}\n")


@pytest.fixture
def clone(tmp_path):
    repo, folder = make_clone(tmp_path)
    seed_retained_log(folder)
    return repo, folder


def no_gaps():
    return ()


@pytest.mark.parametrize("replacement", ["link", "directory"])
def test_prepare_refuses_source_name_changes_before_writes(clone, monkeypatch, tmp_path, replacement):
    repo, folder = clone
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    foreign = tmp_path / "foreign"
    if replacement == "link":
        foreign.mkdir()
        (foreign / MARKER).write_text("7\n")
    aside = tmp_path / "source-aside"

    def swap_then_no_gaps():
        folder.rename(aside)
        if replacement == "link":
            folder.symlink_to(foreign, target_is_directory=True)
        else:
            folder.mkdir()
            (folder / MARKER).write_text("7\n")
        return ()

    with pytest.raises(StoreError, match="no longer names the folder that was pinned"):
        offline_protocol.prepare_clone(repo, gaps=swap_then_no_gaps)
    held_foreign = foreign if replacement == "link" else folder
    assert (held_foreign / MARKER).read_text() == "7\n"
    assert sorted(p.name for p in held_foreign.iterdir()) == [MARKER]
    assert not (aside / PREPARED).exists()
    if replacement == "link":
        assert not (aside / MARKER).exists()
    else:
        assert (aside / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def foreign_preparation(tmp_path, monkeypatch):
    other_root = tmp_path / "other"
    other_root.mkdir()
    other, folder = make_clone(other_root)
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: "CCCCCCCC-0000-4000-8000-000000000003")
    offline_protocol.prepare_clone(other, gaps=no_gaps)
    return (folder / PREPARED).read_bytes()


@pytest.mark.parametrize("generation", ["unprepared", "other-boot"])
def test_mover_requires_preparation_generation_even_with_matching_identity(clone, monkeypatch, tmp_path, generation):
    repo, folder = clone
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    offline_protocol.prepare_clone(repo, gaps=no_gaps)
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    proof = offline_protocol.finish(folder, gaps=no_gaps)
    foreign_prepared = foreign_preparation(tmp_path, monkeypatch) if generation == "other-boot" else None
    aside = tmp_path / "source-aside"
    folder.rename(aside)
    folder.mkdir()
    (folder / MARKER).write_text("7\n" if generation == "unprepared" else f"{offline_protocol.FENCE}\n")
    if foreign_prepared is not None:
        (folder / PREPARED).write_bytes(foreign_prepared)
    (folder / "clone-id").write_text("FOREIGN\n")
    monkeypatch.setattr(fd_tree, "ident", lambda _st: list(proof.identity))
    with pytest.raises(StoreError):
        project_home.migrated(repo, proof)
    if generation == "unprepared":
        assert sorted(p.name for p in folder.iterdir()) == sorted([MARKER, "clone-id"])
        assert (folder / MARKER).read_text() == "7\n"
    else:
        assert (folder / PREPARED).read_bytes() == foreign_prepared
    assert (folder / "clone-id").read_text() == "FOREIGN\n"
    assert not (folder / project_move.MOVE_LOCK).exists()
    assert not (folder / project_move.MOVE_RECORD).exists()


def test_prepare_refuses_a_foreign_prepared_record_with_an_unfenced_marker_and_keeps_it(clone, monkeypatch, tmp_path):
    repo, folder = clone
    foreign_prepared = foreign_preparation(tmp_path, monkeypatch)
    (folder / PREPARED).write_bytes(foreign_prepared)
    (folder / MARKER).write_text("7\n")
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    with pytest.raises(StoreError):
        offline_protocol.prepare_clone(repo, gaps=no_gaps)
    assert (folder / PREPARED).read_bytes() == foreign_prepared
    assert (folder / MARKER).read_text() == "7\n"
