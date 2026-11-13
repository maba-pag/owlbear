"""A target renamed or replaced in the gap before its format marker is published is never written through or recreated.

Each case runs the real ``cli.main`` Prepare, a modeled reboot and Finish, so the target is a genuine SWITCHED store.
Its format marker is then removed, which makes the public admission publish it. A test hook moves the validated
target aside and plants a foreign directory at its name in the gap between validation and publication. The foreign
bytes stay untouched, the target name is not recreated, and the public Store.open refuses instead of admitting it.
"""

import json
from pathlib import Path

import pytest
from tests import publication_offline

from owlbear_delivery_next.state_store import project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.store import Store

FOREIGN_BYTES = b"foreign data\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return publication_offline.repo(tmp_path, payload=False)


@pytest.fixture
def boot(monkeypatch) -> dict:
    return publication_offline.boot(monkeypatch)


@pytest.mark.usefixtures("current_binding")
def test_a_target_replaced_before_marker_publication_is_refused_and_nothing_is_written_through(
    repo, boot, monkeypatch
) -> None:
    target = publication_offline.switched_store(repo, boot)
    (target / MARKER).unlink()
    before = {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}
    aside = target.with_name(target.name + ".aside")
    real_publish = project_home._publish_markers  # noqa: SLF001 - the gap hook wraps the real publication
    gap_taken: list[Path] = []

    def swap_in_the_gap(folder_fd, tfd, previous, *, moved, guard=None):
        target.rename(aside)
        target.mkdir()
        (target / "foreign.txt").write_bytes(FOREIGN_BYTES)
        gap_taken.append(target)
        real_publish(folder_fd, tfd, previous, moved=moved, guard=guard)

    monkeypatch.setattr(project_home, "_publish_markers", swap_in_the_gap)

    with pytest.raises(StoreError):
        Store.open(repo)

    assert gap_taken, "the gap hook never ran; the publication path did not reach the marker write"
    assert (target / "foreign.txt").read_bytes() == FOREIGN_BYTES
    assert sorted(p.name for p in target.iterdir()) == ["foreign.txt"], (
        "a marker was written into the foreign directory"
    )
    assert not (aside / MARKER).exists(), "the detached target must not gain a marker after authority is lost"
    assert {p.name: p.read_bytes() for p in aside.iterdir() if p.is_file()} == before
    record = json.loads((project_home.clone_dir(repo) / project_move.MOVE_RECORD).read_text())
    assert Path(record["target"]) == target
