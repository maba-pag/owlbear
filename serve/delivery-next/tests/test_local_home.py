"""OwlBear's one local folder (TD-139, TD-161): new paths win, old ``~/.owlbear`` files are read until moved."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

from owlbear_delivery_next import cli, data_repo, design_pack, local_home
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from pathlib import Path

DATA_ROOT = worktree.data_root  # the real one; conftest replaces it in every test


@pytest.fixture
def machine(monkeypatch, tmp_path) -> Path:
    """A home folder without ``OWLBEAR_HOME``, as on a real machine."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("OWLBEAR_HOME", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    return tmp_path


def repo(at: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(at)], check=True, capture_output=True)  # noqa: S603, S607
    return at.resolve()


def test_owlbear_home_moves_the_whole_tree_and_reads_nothing_old(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OWLBEAR_HOME", str(tmp_path / "home"))
    (tmp_path / ".owlbear").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".owlbear" / "data.json").write_text("{}")
    assert local_home.root() == tmp_path / "home"
    assert DATA_ROOT() == tmp_path / "home" / "worktrees"
    assert local_home.found("data.json") == tmp_path / "home" / "data.json"
    assert local_home.plan() == []


def test_old_files_are_read_until_moved_and_new_writes_win(machine) -> None:
    old, new = machine / ".owlbear", local_home.root()
    shared = repo(machine / "owlbear-data")
    old.mkdir()
    (old / "data.json").write_text(json.dumps({"repository": str(shared)}))
    (old / "design-pack" / "p1").mkdir(parents=True)
    assert data_repo.pointer() == old / "data.json"
    assert data_repo.locate() == data_repo.DataRepo(shared)
    assert design_pack.folder({"pack": "p1"}) == old / "design-pack" / "p1"
    assert design_pack.folder({"pack": "p1"}, writing=True) == new / "design-pack" / "p1"
    assert [o for o, _n in local_home.plan()] == [old / "data.json", old / "design-pack"]

    assert "still read from the old folder" in cli.show_home(move=False)
    moved = cli.show_home(move=True)
    assert moved.count("the old copy stays as a backup") == 2
    assert (old / "data.json").exists()
    assert (new / "data.json").read_text() == (old / "data.json").read_text()
    assert data_repo.pointer() == new / "data.json"
    assert design_pack.folder({"pack": "p1"}) == new / "design-pack" / "p1"
    assert local_home.plan() == []


def test_recording_a_repository_writes_only_the_new_folder(machine) -> None:
    old, other = machine / ".owlbear", repo(machine / "other")
    old.mkdir()
    (old / "data.json").write_text(json.dumps({"repository": "/elsewhere"}))
    data_repo.point(other)
    assert json.loads((local_home.root() / "data.json").read_text()) == {"repository": str(other)}
    assert json.loads((old / "data.json").read_text()) == {"repository": "/elsewhere"}  # the backup is untouched
    assert data_repo.locate() == data_repo.DataRepo(other)


@pytest.mark.usefixtures("machine")
def test_worktrees_live_in_owlbears_folder() -> None:
    assert DATA_ROOT() == local_home.root() / "worktrees"
    assert local_home.root().name in {"OwlBear", "owlbear"}
