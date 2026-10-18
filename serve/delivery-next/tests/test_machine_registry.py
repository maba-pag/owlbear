import os
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import environment, registry
from owlbear_delivery_next.machine_host.registry import RegistryError
from owlbear_delivery_next.state_store.database import STORE_FORMAT


@pytest.fixture
def home():
    return local_home.root()  # the suite's own, never the machine's


def clone(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)  # noqa: S603, S607
    return path


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_registering_writes_only_the_store_and_its_id_and_keeps_the_canonical_path(tmp_path, home):
    work = clone(tmp_path / "work")
    (tmp_path / "link").symlink_to(work)
    project = registry.register(tmp_path / "link" / ".")
    store = work.resolve() / ".git" / "owlbear-delivery"
    assert (project.path, project.id) == (str(work.resolve()), (store / "clone-id").read_text().strip())
    assert (sorted(p.name for p in store.iterdir()), mode(store), mode(store / "clone-id")) == (
        ["clone-id"],
        0o700,
        0o600,
    )
    assert registry.load().projects == [project]
    assert (mode(home / "machine.json"), registry.replaced(project)) == (0o600, None)


def test_an_existing_id_is_reused_and_never_rewritten(tmp_path):
    work = clone(tmp_path / "work")
    store = work / ".git" / "owlbear-delivery"
    store.mkdir()
    (store / "clone-id").write_text("cafe\n")
    before = (store / "clone-id").stat().st_mtime_ns
    assert registry.register(work).id == "cafe"
    assert ((store / "clone-id").read_text(), (store / "clone-id").stat().st_mtime_ns) == ("cafe\n", before)


def test_one_clone_is_registered_once_by_path_and_by_id(tmp_path):
    work = clone(tmp_path / "work")
    registry.register(work)
    with pytest.raises(RegistryError, match="is registered already"):
        registry.register(work)
    moved = tmp_path / "moved"
    work.rename(moved)
    with pytest.raises(RegistryError, match=f"registered already at {work.resolve()}"):
        registry.register(moved)


def test_a_reclone_at_the_same_path_shows_as_replaced_until_adopted_or_removed(tmp_path):
    work = clone(tmp_path / "work")
    old = registry.register(work)
    subprocess.run(["rm", "-rf", str(work)], check=True)  # noqa: S603, S607
    assert registry.replaced(old) == f"{work.resolve()} is gone; Remove the project"
    clone(work)
    assert registry.replaced(old) == f"the clone at {work.resolve()} is not the one registered; Remove or Adopt it"
    new = registry.adopt(old.id)
    assert (new.id != old.id, registry.replaced(new), registry.load().projects) == (True, None, [new])
    registry.remove(new.id)
    assert (registry.load().projects, (work / ".git" / "owlbear-delivery" / "clone-id").exists()) == ([], True)


def test_a_folder_that_is_no_clone_of_the_owner_or_newer_state_is_refused(tmp_path, monkeypatch):
    (tmp_path / "plain").mkdir()
    with pytest.raises(RegistryError, match="is not a git work tree"):
        registry.register(tmp_path / "plain")
    with pytest.raises(RegistryError, match="does not exist"):
        registry.register(tmp_path / "missing")
    work = clone(tmp_path / "work")
    store = work / ".git" / "owlbear-delivery"
    store.mkdir()
    (store / "format").write_text(f"{STORE_FORMAT + 1}\n")
    with pytest.raises(RegistryError, match=f"format {STORE_FORMAT + 1}, newer than {STORE_FORMAT}"):
        registry.register(work)
    (store / "format").write_text("four\n")
    with pytest.raises(RegistryError, match="is unreadable"):
        registry.register(work)
    (store / "format").unlink()
    monkeypatch.setattr(os, "getuid", lambda: os.geteuid() + 1)
    with pytest.raises(RegistryError, match="belongs to another user"):
        registry.register(work)
    assert (registry.load().projects, (store / "clone-id").exists()) == ([], False)


def test_a_registry_from_a_newer_release_is_refused(home):
    (home / "machine.json").write_text('{"format": 2, "projects": []}')
    with pytest.raises(RegistryError, match="newer than 1"):
        registry.load()


def test_the_scrub_drops_credential_and_repository_selectors_and_keeps_transport():
    env = {
        "GH_TOKEN": "t",
        "GITHUB_TOKEN": "t",
        "GIT_DIR": "/x",
        "GIT_CONFIG_GLOBAL": "/c",
        "GIT_CONFIG_KEY_0": "k",
        "SSH_AUTH_SOCK": "/s",
        "GIT_SSH_COMMAND": "ssh -i k",
        "GIT_SSH": "ssh",
        "PATH": "/bin",
    }
    dropped = environment.scrub(env)
    assert dropped == ["GH_TOKEN", "GITHUB_TOKEN", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_KEY_0", "GIT_DIR"]
    assert env == {"SSH_AUTH_SOCK": "/s", "GIT_SSH_COMMAND": "ssh -i k", "GIT_SSH": "ssh", "PATH": "/bin"}
