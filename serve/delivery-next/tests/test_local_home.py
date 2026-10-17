"""OwlBear's one local folder (TD-198): always ``~/.owlbear``, for the pointer, the design pack and the worktrees."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.design_packs import design_pack, pack_update
from owlbear_delivery_next.local_system import data_repo, local_home

if TYPE_CHECKING:
    from pathlib import Path

ROOT, DATA_ROOT = local_home.root, worktree.data_root  # the real ones; conftest replaces them in every test


@pytest.fixture
def machine(monkeypatch, tmp_path) -> Path:
    """A home folder with the real folder rule, as on a real machine."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(local_home, "root", ROOT)
    return tmp_path


def repo(at: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(at)], check=True, capture_output=True)  # noqa: S603, S607
    return at.resolve()


def test_everything_lives_in_dot_owlbear(machine) -> None:
    home = machine / ".owlbear"
    assert local_home.root() == home
    assert DATA_ROOT() == home / "worktrees"
    assert data_repo.pointer() == home / "data.json"
    assert design_pack.folder({"pack": "p1"}) == home / "design-pack" / "p1"
    assert cli.show_home() == f"OwlBear's folder: {home}"


def test_recording_a_repository_writes_the_pointer_there(machine) -> None:
    other = repo(machine / "other")
    data_repo.point(other)
    assert json.loads((machine / ".owlbear" / "data.json").read_text()) == {"repository": str(other)}
    assert data_repo.locate() == data_repo.DataRepo(other)


def test_an_offline_check_records_its_notice_there(machine) -> None:
    def offline(_url: str) -> bytes:
        msg = "offline"
        raise OSError(msg)

    assert pack_update.notice(refresh=True, fetch=offline)["behind"] is None
    assert (machine / ".owlbear" / "design-pack" / "notice.json").exists()


def test_a_process_a_test_starts_never_reaches_the_machines_folder(machine_home) -> None:
    """A test once let child processes claim folders in the owner's real shared data repository and push them."""
    code = "from owlbear_delivery_next.local_system import local_home; print(local_home.root())"
    child = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)  # noqa: S603
    assert child.stdout.strip() == str(local_home.root())
    assert not child.stdout.startswith(str(machine_home))
