"""The offline proof is bound to the source folder's descriptor: a swap before or after it is refused, never written to.

Each swap happens at the exact seam the production code crosses: the ``gaps`` callable runs after Prepare has pinned
the folder and before it reads or writes anything; the proof is issued, then the path is swapped before the move
opens the folder. The boot session is the only synthetic witness.
"""

import subprocess

import pytest

from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"
PREPARED = offline_protocol.PREPARED


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


def no_gaps():
    return ()


def test_a_source_swapped_for_a_link_before_prepare_writes_is_refused_and_no_foreign_file_is_written(
    clone, monkeypatch, tmp_path
):
    repo, folder = clone
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / MARKER).write_text("7\n")
    aside = tmp_path / "source-aside"

    def swap_then_no_gaps():
        folder.rename(aside)
        folder.symlink_to(foreign, target_is_directory=True)
        return ()

    with pytest.raises(StoreError, match="no longer names the folder that was pinned"):
        offline_protocol.prepare_clone(repo, gaps=swap_then_no_gaps)
    assert (foreign / MARKER).read_text() == "7\n"
    assert sorted(p.name for p in foreign.iterdir()) == [MARKER]
    assert not (aside / PREPARED).exists()
    assert not (aside / MARKER).exists()


def test_a_source_replaced_by_a_foreign_folder_before_prepare_writes_is_refused_and_kept(clone, monkeypatch, tmp_path):
    repo, folder = clone
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    aside = tmp_path / "source-aside"

    def replace_then_no_gaps():
        folder.rename(aside)
        folder.mkdir()
        (folder / MARKER).write_text("7\n")
        return ()

    with pytest.raises(StoreError, match="no longer names the folder that was pinned"):
        offline_protocol.prepare_clone(repo, gaps=replace_then_no_gaps)
    assert (folder / MARKER).read_text() == "7\n"
    assert sorted(p.name for p in folder.iterdir()) == [MARKER]
    assert not (aside / PREPARED).exists()
    assert (aside / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_healthy_source_is_prepared_and_its_proof_carries_the_pinned_identity(clone, monkeypatch):
    repo, folder = clone
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    offline_protocol.prepare_clone(repo, gaps=no_gaps)
    assert (folder / MARKER).read_text() == f"{offline_protocol.FENCE}\n"
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    proof = offline_protocol.finish(folder, gaps=no_gaps)
    st = folder.stat()
    assert proof.identity == (st.st_dev, st.st_ino)
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_folder_replaced_after_its_proof_is_refused_before_anything_in_it_is_written(clone, monkeypatch, tmp_path):
    repo, folder = clone
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    offline_protocol.prepare_clone(repo, gaps=no_gaps)
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    proof = offline_protocol.finish(folder, gaps=no_gaps)
    aside = tmp_path / "source-aside"
    folder.rename(aside)
    folder.mkdir()
    (folder / "clone-id").write_text(f"{SOURCE_ID}\n")
    (folder / MARKER).write_text(f"{offline_protocol.FENCE}\n")
    (folder / PREPARED).write_bytes((aside / PREPARED).read_bytes())
    before = sorted(p.name for p in folder.iterdir())
    with pytest.raises(StoreError, match="was replaced after its offline proof was issued"):
        project_home.migrated(repo, proof)
    assert sorted(p.name for p in folder.iterdir()) == before
    assert (folder / MARKER).read_text() == f"{offline_protocol.FENCE}\n"
    assert not (folder / project_move.MOVE_RECORD).exists()
    assert (aside / "changes" / "c1" / "runner.log").read_text() == "ran\n"
