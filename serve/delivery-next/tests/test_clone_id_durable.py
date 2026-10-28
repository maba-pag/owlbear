"""A clone's new id is published only after its file and folder are synced, and only from the folder it names.

The fault seam classifies each ``os.fsync`` by the descriptor it is given: a folder whose identity is the clone's
store, or the id file inside it. Registry-home syncs are not counted.
"""

import errno
import os
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.state_store import fd_tree, project_home, registry
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.registry import RegistryError


@pytest.fixture
def home():
    return local_home.root()  # the suite's own, never the machine's


class Seam:
    def __init__(self, store: Path) -> None:
        self.store = store
        self.events: list[str] = []
        self.fail: str | None = None  # "file" or "dir": the next such sync raises EIO
        self.swap: str | None = None  # "dir": the next folder sync first replaces the store with another folder

    def kind(self, fd: int) -> str | None:
        st = os.fstat(fd)
        if self.store.is_dir() and fd_tree.ident(st) == fd_tree.ident(self.store.stat()):
            return "dir"
        clone_id = self.store / "clone-id"
        if (clone_id.is_symlink() or clone_id.exists()) and st.st_ino == clone_id.stat(follow_symlinks=False).st_ino:
            return "file"
        return None

    def replace_store(self) -> None:
        aside = self.store.parent / "moved-aside"
        self.store.rename(aside)
        self.store.mkdir(mode=0o700)
        (self.store / "clone-id").write_text("other\n")


def test_read_only_clone_id_rejects_a_folder_replaced_during_the_read(tmp_path, monkeypatch):
    folder, retained = tmp_path / "store", tmp_path / "retained"
    folder.mkdir()
    (folder / "clone-id").write_text("owned\n")
    real_read = fd_tree.read_at
    fired = []

    def read(dfd, name):
        text = real_read(dfd, name)
        if not fired and name == "clone-id":
            fired.append(True)
            folder.rename(retained)
            folder.mkdir()
            (folder / "clone-id").write_text("foreign-owner\n")
        return text

    monkeypatch.setattr(fd_tree, "read_at", read)
    with pytest.raises(StoreError):
        project_home.clone_id(folder)
    assert fired == [True]
    assert (folder / "clone-id").read_text() == "foreign-owner\n"
    assert (retained / "clone-id").read_text() == "owned\n"


@pytest.fixture
def seam(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    subprocess.run(["git", "init", "-q", str(work)], check=True)  # noqa: S603, S607
    state = Seam(project_home.clone_dir(work))
    real_fsync = os.fsync
    real_save = registry.save

    def fsync(fd: int) -> None:
        kind = state.kind(fd)
        if kind is not None:
            state.events.append(kind)
            if state.fail == kind:
                state.fail = None
                raise OSError(errno.EIO, "injected fsync failure")
            if state.swap == kind:
                state.swap = None
                state.replace_store()
        real_fsync(fd)

    def save(machine, *, before_replace=None) -> None:
        state.events.append("publish")
        real_save(machine, before_replace=before_replace)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(registry, "save", save)
    state.work = work
    return state


@pytest.mark.usefixtures("home")
def test_a_file_sync_failure_is_synced_again_before_the_retry_publishes(seam):
    seam.fail = "file"
    with pytest.raises(RegistryError, match="not finished"):
        registry.register(seam.work)
    assert registry.load().projects == []
    kept = (seam.store / "clone-id").read_text()
    assert kept.endswith("\n")

    seam.events.clear()
    project = registry.register(seam.work)

    assert project.id == kept.strip()
    assert seam.events.index("file") < seam.events.index("publish")
    assert seam.events.index("dir") < seam.events.index("publish")
    assert (seam.store / "clone-id").read_text() == kept


@pytest.mark.usefixtures("home")
def test_a_folder_sync_failure_is_synced_again_before_the_retry_publishes(seam):
    seam.fail = "dir"
    with pytest.raises(RegistryError, match="not finished"):
        registry.register(seam.work)
    assert registry.load().projects == []
    kept = (seam.store / "clone-id").read_text()

    seam.events.clear()
    project = registry.register(seam.work)

    assert project.id == kept.strip()
    assert seam.events.index("file") < seam.events.index("publish")
    assert seam.events.index("dir") < seam.events.index("publish")


@pytest.mark.usefixtures("home")
def test_a_folder_swapped_during_the_first_sync_publishes_nothing_and_keeps_both(seam):
    seam.swap = "dir"
    with pytest.raises(RegistryError, match="was replaced"):
        registry.register(seam.work)

    assert "publish" not in seam.events
    assert registry.load().projects == []
    aside = seam.store.parent / "moved-aside"
    assert (aside / "clone-id").read_text().endswith("\n")
    assert (aside / "clone-id").read_text() != "other\n"
    assert (seam.store / "clone-id").read_text() == "other\n"
    assert sorted(p.name for p in seam.store.iterdir()) == ["clone-id"]
