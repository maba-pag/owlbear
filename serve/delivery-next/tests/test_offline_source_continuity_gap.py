"""The source name is swapped after Finish verified it and before the move uses it: real folders, real identities.

No identity is faked here. The swapped-in folder has its own device and inode, so the proof's identity check is
what refuses it. The source folder is renamed aside, never deleted, and nothing is written in the foreign folder.
"""

import subprocess

import pytest

from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"
PREPARED = offline_protocol.PREPARED
FOREIGN_BYTES = "7\n"


@pytest.fixture
def prepared_source(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)  # noqa: S607
    folder = repo / ".git" / "owlbear-delivery"
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / "clone-id").write_text(f"{SOURCE_ID}\n")
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    offline_protocol.prepare_clone(repo, gaps=lambda: ())
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    proof = offline_protocol.finish(folder, gaps=lambda: ())
    return repo, folder, proof


def make_foreign(path):
    path.mkdir()
    (path / MARKER).write_text(FOREIGN_BYTES)
    (path / "clone-id").write_text("FOREIGN\n")
    return path


def snapshot(folder):
    return {p.name: p.read_bytes() for p in sorted(folder.iterdir()) if p.is_file()}


def assert_foreign_untouched_and_source_kept(aside, foreign, before_foreign):
    assert snapshot(foreign) == before_foreign
    assert not (foreign / PREPARED).exists()
    assert not (foreign / project_move.MOVE_LOCK).exists()
    assert not (foreign / project_move.MOVE_RECORD).exists()
    assert not (foreign / "changes").exists()
    assert (aside / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (aside / PREPARED).exists()


def test_a_source_name_swapped_to_a_foreign_folder_after_finish_is_refused_and_nothing_is_written(
    prepared_source, tmp_path
):
    repo, folder, proof = prepared_source
    aside = tmp_path / "source-aside"
    folder.rename(aside)
    foreign = make_foreign(folder)  # a real folder with its own identity at the logical path
    before_foreign = snapshot(foreign)
    with pytest.raises(StoreError, match="was replaced after its offline proof was issued"):
        project_home.migrated(repo, proof)
    assert_foreign_untouched_and_source_kept(aside, foreign, before_foreign)


def test_a_source_name_swapped_to_a_foreign_folder_in_flight_writes_only_the_pinned_source(
    prepared_source, tmp_path, monkeypatch
):
    repo, folder, proof = prepared_source
    aside = tmp_path / "source-aside"
    foreign = make_foreign(tmp_path / "foreign")
    before_foreign = snapshot(foreign)
    real_generation = project_home._generation_at  # noqa: SLF001 - the in-flight seam, after the pin

    def swap_after_the_pin(folder_arg, folder_fd, proof_arg):
        real_generation(folder_arg, folder_fd, proof_arg)
        folder.rename(aside)
        folder.symlink_to(foreign, target_is_directory=True)

    source_before = snapshot(folder)
    monkeypatch.setattr(project_home, "_generation_at", swap_after_the_pin)
    with pytest.raises(StoreError, match="no longer names the folder being moved"):
        project_home.migrated(repo, proof)
    assert snapshot(foreign) == before_foreign
    assert not (foreign / "changes").exists()
    assert not (foreign / project_move.MOVE_LOCK).exists()
    assert not (foreign / project_move.MOVE_RECORD).exists()
    # The lock file is created inside the pinned source by design; it holds no state.
    assert {k: v for k, v in snapshot(aside).items() if k != project_move.MOVE_LOCK} == source_before
