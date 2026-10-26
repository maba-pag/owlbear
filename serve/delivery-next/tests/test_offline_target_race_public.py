"""A target renamed or replaced in the gap before its format marker is published is never written through or recreated.

Each case runs the real ``cli.main`` Prepare, a modeled reboot and Finish, so the target is a genuine SWITCHED store.
Its format marker is then removed, which makes the public admission publish it. A test hook moves the validated
target aside and plants a foreign directory at its name in the gap between validation and publication. The foreign
bytes stay untouched, the target name is not recreated, and the public Store.open refuses instead of admitting it.
"""

import json
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
FOREIGN_BYTES = b"foreign data\n"


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


def _switched_store(repo: Path, boot: dict, capsys) -> Path:
    """Real Prepare, a modeled reboot and real Finish; returns the SWITCHED target with its marker removed."""
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    target = Store.open(repo).root
    (target / MARKER).unlink()
    return target


@pytest.mark.usefixtures("current_binding")
def test_a_target_replaced_before_marker_publication_is_refused_and_nothing_is_written_through(
    repo, boot, capsys, monkeypatch
) -> None:
    target = _switched_store(repo, boot, capsys)
    aside = target.with_name(target.name + ".aside")
    real_publish = project_home._publish_markers  # noqa: SLF001 - the gap hook wraps the real publication
    gap_taken: list[Path] = []

    def swap_in_the_gap(folder_fd, tfd, previous, *, moved):
        target.rename(aside)
        target.mkdir()
        (target / "foreign.txt").write_bytes(FOREIGN_BYTES)
        gap_taken.append(target)
        real_publish(folder_fd, tfd, previous, moved=moved)

    monkeypatch.setattr(project_home, "_publish_markers", swap_in_the_gap)

    with pytest.raises(StoreError):
        Store.open(repo)

    assert gap_taken, "the gap hook never ran; the publication path did not reach the marker write"
    assert (target / "foreign.txt").read_bytes() == FOREIGN_BYTES
    assert sorted(p.name for p in target.iterdir()) == ["foreign.txt"], (
        "a marker was written into the foreign directory"
    )
    assert (aside / MARKER).read_text().strip() == str(STORE_FORMAT), "the validated inode kept its own publication"
    record = json.loads((project_home.clone_dir(repo) / project_move.MOVE_RECORD).read_text())
    assert Path(record["target"]) == target
