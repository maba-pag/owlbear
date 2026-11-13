"""The source name is swapped after Finish verified it and before the move uses it: real folders, real identities.

No identity is faked here. The swapped-in folder has its own device and inode, so the proof's identity check is
what refuses it. The source folder is renamed aside, never deleted, and nothing is written in the foreign folder.
"""

import pytest

from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError

from . import test_offline_source_pin as sources

PREPARED = offline_protocol.PREPARED
FOREIGN_BYTES = "7\n"


@pytest.fixture
def prepared_source(tmp_path, monkeypatch):
    repo, folder = sources.make_clone(tmp_path)
    sources.seed_retained_log(folder)
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: sources.BEFORE)
    offline_protocol.prepare_clone(repo, gaps=lambda: ())
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: sources.AFTER)
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


@pytest.mark.parametrize("generation", ["unprepared", "copied-witnesses"])
def test_mover_refuses_a_different_source_after_proof(prepared_source, tmp_path, generation):
    repo, folder, proof = prepared_source
    aside = tmp_path / "source-aside"
    folder.rename(aside)
    foreign = make_foreign(folder)  # a real folder with its own identity at the logical path
    if generation == "copied-witnesses":
        (foreign / "clone-id").write_text(f"{sources.SOURCE_ID}\n")
        (foreign / MARKER).write_text(f"{offline_protocol.FENCE}\n")
        (foreign / PREPARED).write_bytes((aside / PREPARED).read_bytes())
    before_foreign = snapshot(foreign)
    with pytest.raises(StoreError, match="was replaced after its offline proof was issued"):
        project_home.migrated(repo, proof)
    if generation == "unprepared":
        assert_foreign_untouched_and_source_kept(aside, foreign, before_foreign)
    else:
        assert snapshot(foreign) == before_foreign
        assert sorted(p.name for p in foreign.iterdir()) == sorted(before_foreign)
        assert (foreign / MARKER).read_text() == f"{offline_protocol.FENCE}\n"
        assert not (foreign / project_move.MOVE_RECORD).exists()
        assert (aside / "changes" / "c1" / "runner.log").read_text() == "ran\n"


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
