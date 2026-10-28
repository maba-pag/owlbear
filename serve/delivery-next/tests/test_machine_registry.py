import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import environment
from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move, registry
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT
from owlbear_delivery_next.state_store.registry import RegistryError


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
    (home / "machine.json").write_text(f'{{"format": {registry.MACHINE_FORMAT + 1}, "projects": []}}')
    with pytest.raises(RegistryError, match=f"newer than {registry.MACHINE_FORMAT}"):
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


def test_a_format_1_registry_gets_the_default_machine_settings_and_a_save_writes_format_2(home):
    """TD-243, TD-288, TD-300: the machine's own settings; a page's save names the revision it read."""
    (home / registry.MACHINE).write_text('{"format": 1, "projects": [], "resumed_at": null}')
    loaded = registry.load()
    assert (loaded.format, loaded.settings) == (1, registry.Settings())
    rev = registry.revision(loaded.settings)
    chosen = registry.Settings(channel="major", update_while_paused=False)
    registry.configure(chosen, rev)
    with pytest.raises(RegistryError, match="changed since this page loaded them"):
        registry.configure(registry.Settings(), rev)
    assert (registry.load().format, registry.load().settings) == (registry.MACHINE_FORMAT, chosen)


def test_paths_outside_owlbear_name_the_runtime_alias_so_a_later_version_serves_them(home, tmp_path):
    """The self-update build, section 3: what setup, install and the login item write survives an update."""
    version = home / local_home.VERSIONS / "v0.2" / ".venv" / "bin"
    version.mkdir(parents=True)
    (home / local_home.RUNTIME).symlink_to(home / local_home.VERSIONS / "v0.2")
    elsewhere = tmp_path / "checkout" / ".venv" / "bin" / "python"
    alias = home / local_home.RUNTIME / ".venv" / "bin"
    assert local_home.stable(version / "python") == alias / "python"
    assert local_home.stable(alias / "owlbear") == alias / "owlbear"
    assert local_home.stable(elsewhere) == elsewhere  # a developer checkout keeps its own path


def _change_registration_owner(store, damage):
    if damage == "work-path":
        work = store.parent.parent
        moved = work.with_name("owner-work")
        work.rename(moved)
        work.mkdir()
        (work / "owner").write_text("owner's replacement folder\n")
        return work, moved
    if damage == "git-common-dir":
        work = store.parent.parent
        other = clone(work.with_name("owner-other"))
        other_store = project_home.clone_dir(other)
        other_store.mkdir()
        (other_store / "clone-id").write_text("owned\n")
        store.parent.rename(work / "owner-git")
        (work / ".git").write_text(f"gitdir: {other / '.git'}\n")
        return work, other
    if damage == "missing-id":
        (store / "clone-id").unlink()
    elif damage == "future-format":
        (store / MARKER).write_text("1000\n")
    else:
        (store / "clone-id").write_text("foreign-owner\n")
        if damage == "clone-id-and-deleted-config":
            (store / "config.json").unlink()
    return (store,)


def _owner_files(folders):
    return {p: p.read_bytes() for folder in folders for p in folder.rglob("*") if p.is_file()}


@pytest.mark.parametrize("action", ["register", "adopt"])
@pytest.mark.parametrize("field", [project_move.CLONE_ID, project_move.MOVE_RECORD])
@pytest.mark.parametrize("alias", [False, True], ids=["gitfile", "directory-alias"])
def test_registry_publication_refuses_a_git_mapping_changed_during_final_source_reads(
    tmp_path, monkeypatch, action, field, alias
):
    work, other = tmp_path / "work", tmp_path / "other"
    first, second = tmp_path / "first-git", tmp_path / "second-git"
    for path, gitdir in ((work, first), (other, second)):
        subprocess.run(["git", "init", "-q", "--separate-git-dir", str(gitdir), str(path)], check=True)  # noqa: S603, S607
    link = tmp_path / "git-alias"
    if alias:
        link.symlink_to(first, target_is_directory=True)
        (work / ".git").write_text(f"gitdir: {link}\n")
    store = first / project_home.STORE_DIR
    store.mkdir()
    (store / MARKER).write_text("7\n")
    (store / "clone-id").write_text("old\n" if action == "adopt" else "owned\n")
    assert registry.canonical(work) == (work.resolve(), store.resolve())
    if action == "adopt":
        old = registry.register(work)
        (store / "clone-id").write_text("owned\n")
    source_before = _owner_files((store,))
    machine = local_home.root() / registry.MACHINE
    before = machine.read_bytes() if machine.exists() else None
    real_sync, real_read = os.fsync, fd_tree.read_at
    enabled, fired = [], []
    mapping = f"gitdir: {second}\n"

    def synced(fd):
        real_sync(fd)
        if not enabled and any(
            os.path.samestat(temporary.stat(), os.fstat(fd)) for temporary in local_home.root().glob(".tmp-*.tmp")
        ):
            enabled.append(True)

    def read(dfd, name):
        value = real_read(dfd, name)
        if enabled and not fired and name == field:
            fired.append(True)
            if alias:
                link.unlink()
                link.symlink_to(second, target_is_directory=True)
            else:
                (work / ".git").write_text(mapping)
        return value

    monkeypatch.setattr(os, "fsync", synced)
    monkeypatch.setattr(fd_tree, "read_at", read)
    call = (lambda: registry.register(work)) if action == "register" else (lambda: registry.adopt(old.id))
    with pytest.raises(registry.RegistryError):
        call()
    assert fired == [True]
    assert (work / ".git").read_text() == (f"gitdir: {link}\n" if alias else mapping)
    assert project_home.clone_dir(work) == second / project_home.STORE_DIR
    assert _owner_files((store,)) == source_before
    assert (machine.read_bytes() if machine.exists() else None) == before


@pytest.mark.parametrize("referent", [False, True], ids=["control-file", "symlink-referent"])
def test_registry_publication_refuses_a_linked_worktree_common_dir_redirect_during_source_reads(
    tmp_path, monkeypatch, referent
):
    first, second = clone(tmp_path / "first"), clone(tmp_path / "second")
    git = shutil.which("git")
    assert git is not None
    subprocess.run(  # noqa: S603 - synthetic repository and identity
        [
            git,
            "-C",
            str(first),
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        check=True,
    )
    work = tmp_path / "linked"
    subprocess.run([git, "-C", str(first), "worktree", "add", "-q", "-b", "linked", str(work)], check=True)  # noqa: S603
    gitdir = registry._git(work, "rev-parse", "--absolute-git-dir")  # noqa: SLF001 - real linked-worktree metadata
    store = project_home.clone_dir(work)
    control = gitdir / "commondir"
    if referent:
        pointer = tmp_path / "common-pointer"
        pointer.write_bytes(control.read_bytes())
        control.unlink()
        control.symlink_to(pointer)
        control = pointer
    store.mkdir()
    (store / MARKER).write_text("7\n")
    (store / "clone-id").write_text("owned\n")
    assert registry.canonical(work) == (work.resolve(), store.resolve())
    machine = local_home.root() / registry.MACHINE
    before = machine.read_bytes() if machine.exists() else None
    real_sync, real_read = os.fsync, fd_tree.read_at
    enabled, fired = [], []
    mapping = f"{second / '.git'}\n"

    def synced(fd):
        real_sync(fd)
        if not enabled and any(
            os.path.samestat(temporary.stat(), os.fstat(fd)) for temporary in local_home.root().glob(".tmp-*.tmp")
        ):
            enabled.append(True)

    def read(dfd, name):
        value = real_read(dfd, name)
        if enabled and not fired and name == project_move.MOVE_RECORD:
            fired.append(True)
            control.write_text(mapping)
        return value

    monkeypatch.setattr(os, "fsync", synced)
    monkeypatch.setattr(fd_tree, "read_at", read)
    with pytest.raises(registry.RegistryError):
        registry.register(work)
    assert fired == [True]
    assert control.read_text() == mapping
    assert not referent or (gitdir / "commondir").is_symlink()
    assert project_home.clone_dir(work) == second / ".git" / project_home.STORE_DIR
    assert (machine.read_bytes() if machine.exists() else None) == before


@pytest.mark.parametrize("action", ["register", "adopt"])
@pytest.mark.parametrize("field", [project_move.CLONE_ID, project_move.MOVE_RECORD])
def test_registry_publication_keeps_a_newer_ordinary_marker_installed_during_later_reads(
    tmp_path, monkeypatch, action, field
):
    work = clone(tmp_path / "work")
    store = project_home.clone_dir(work)
    store.mkdir()
    (store / MARKER).write_text("7\n")
    (store / "clone-id").write_text("old\n" if action == "adopt" else "owned\n")
    if action == "adopt":
        old = registry.register(work)
        (store / "clone-id").write_text("owned\n")
    machine = local_home.root() / registry.MACHINE
    before = machine.read_bytes() if machine.exists() else None
    real_sync, real_read = os.fsync, fd_tree.read_at
    enabled, fired = [], []

    def synced(fd):
        real_sync(fd)
        if not enabled and any(
            os.path.samestat(temporary.stat(), os.fstat(fd)) for temporary in local_home.root().glob(".tmp-*.tmp")
        ):
            enabled.append(True)

    def read(dfd, name):
        text = real_read(dfd, name)
        if enabled and not fired and name == field:
            fired.append(True)
            (store / MARKER).write_text("1000\n")
        return text

    monkeypatch.setattr(os, "fsync", synced)
    monkeypatch.setattr(fd_tree, "read_at", read)
    call = (lambda: registry.register(work)) if action == "register" else (lambda: registry.adopt(old.id))
    with pytest.raises(registry.RegistryError):
        call()
    assert fired == [True]
    assert (store / MARKER).read_text() == "1000\n"
    assert (machine.read_bytes() if machine.exists() else None) == before


@pytest.mark.parametrize("action", ["register", "adopt"])
def test_registry_publication_rechecks_id_after_an_absent_receipt_lookup(tmp_path, monkeypatch, action):
    work = clone(tmp_path / "work")
    store = project_home.clone_dir(work)
    store.mkdir()
    (store / "clone-id").write_text("old\n" if action == "adopt" else "owned\n")
    if action == "adopt":
        old = registry.register(work)
        (store / "clone-id").write_text("owned\n")
    machine = local_home.root() / registry.MACHINE
    before = machine.read_bytes() if machine.exists() else None
    real_sync, real_read = os.fsync, fd_tree.read_at
    enabled, fired = [], []

    def synced(fd):
        real_sync(fd)
        if not enabled and any(
            os.path.samestat(temporary.stat(), os.fstat(fd)) for temporary in local_home.root().glob(".tmp-*.tmp")
        ):
            enabled.append(True)

    def read(dfd, name):
        text = real_read(dfd, name)
        if enabled and not fired and name == project_move.MOVE_RECORD:
            fired.append(True)
            replacement = store / "owner-id"
            replacement.write_text("foreign-owner\n")
            replacement.replace(store / "clone-id")
        return text

    monkeypatch.setattr(os, "fsync", synced)
    monkeypatch.setattr(fd_tree, "read_at", read)
    call = (lambda: registry.register(work)) if action == "register" else (lambda: registry.adopt(old.id))
    failure = None
    try:
        call()
    except RegistryError as exc:
        failure = exc
    assert enabled == fired == [True]
    assert isinstance(failure, RegistryError)
    assert (store / "clone-id").read_text() == "foreign-owner\n"
    assert (machine.read_bytes() if machine.exists() else None) == before
    assert registry.load().projects == ([old] if action == "adopt" else [])


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("switched", [False, True], ids=["ordinary", "real-prepare-finish"])
@pytest.mark.parametrize("action", ["register", "adopt"])
@pytest.mark.parametrize(
    "damage", ["clone-id", "missing-id", "future-format", "clone-id-and-deleted-config", "work-path", "git-common-dir"]
)
def test_registration_rechecks_the_admitted_clone_after_the_registry_temporary_is_synced(
    tmp_path, monkeypatch, switched, action, damage
):
    home = local_home.root()
    work = clone(tmp_path / "work")
    store = project_home.clone_dir(work)
    store.mkdir()
    (store / "clone-id").write_text("owned\n")
    (store / MARKER).write_text("7\n")
    (store / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    if action == "adopt":
        (store / "clone-id").write_text("old\n")
        old = registry.register(work)
        (store / "clone-id").write_text("owned\n")
    if switched:
        monkeypatch.setattr(offline_protocol, "boot_session", lambda: "AAAAAAAA-0000-4000-8000-000000000001")
        assert cli.main(["--repo", str(work), "prepare"]) == 0
        monkeypatch.setattr(offline_protocol, "boot_session", lambda: "BBBBBBBB-0000-4000-8000-000000000002")
        assert cli.main(["--repo", str(work), "finish"]) == 0
    assert registry.canonical(work) == (work, store)
    machine = home / registry.MACHINE
    before = machine.read_bytes() if machine.exists() else None
    real_fsync, fired = os.fsync, []
    owner_before = {}
    owner_folders = []

    def owner_changes_id(fd):
        real_fsync(fd)
        if fired:
            return
        for temporary in home.glob(".tmp-*.tmp"):
            if os.path.samestat(temporary.stat(), os.fstat(fd)):
                pending = json.loads(temporary.read_text())
                assert pending["projects"][-1]["id"] == "owned"
                fired.append(True)
                owner_folders.extend(_change_registration_owner(store, damage))
                owner_before.update(_owner_files(owner_folders))

    monkeypatch.setattr(os, "fsync", owner_changes_id)
    error, returned = None, None
    try:
        returned = registry.register(work) if action == "register" else registry.adopt(old.id)
    except RegistryError as exc:
        error = exc

    assert fired == [True], "the real machine.json temporary fsync was not reached"
    assert _owner_files(owner_folders) == owner_before
    assert (machine.read_bytes() if machine.exists() else None) == before, (
        f"{action} published a stale registration: returned {returned!r}, error {error!r}"
    )
    assert isinstance(error, RegistryError), f"{action} returned {returned!r} instead of refusing"
    assert "nothing was registered" in str(error)
    assert not list(home.glob(".tmp-*.tmp"))
    if action == "adopt":
        assert registry.load().projects == [old]
