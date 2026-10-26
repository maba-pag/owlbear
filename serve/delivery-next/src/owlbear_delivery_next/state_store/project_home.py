"""Where a project's live Delivery state lives (TD-334): ``~/.owlbear/projects/<id>/``, one folder per project.

The clone keeps only ``<git common dir>/owlbear-delivery/``, holding the project's id (``clone-id``) and a format
marker every older runtime refuses, so a moved or renamed clone keeps its project and a re-clone gets a new one.
A store still in the clone moves to its folder once, on first open; a move cut short resumes on the next.
"""

from __future__ import annotations

import errno
import json
import os
import secrets
import shutil
from pathlib import Path

from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, FormatTooNewError, StoreError

STORE_DIR = "owlbear-delivery"
PROJECTS = "projects"
MACHINE = "machine.json"  # the registry (``state_store.registry``); read here only to tell a project from leftovers
CLONE_ID = "clone-id"
MOVE_LOCK = "move.lock"
KEPT = frozenset({CLONE_ID, MARKER, MOVE_LOCK})  # what stays in the clone


def clone_dir(cwd: Path) -> Path:
    """The clone's own Delivery folder: its id and the marker."""
    return git_common_dir(cwd) / STORE_DIR


def clone_id(folder: Path) -> str | None:
    """The id written into the clone's folder, or None when there is none."""
    try:
        return (folder / CLONE_ID).read_text().strip() or None
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        msg = f"{folder / CLONE_ID} is unreadable"
        raise StoreError(msg) from exc


def ensure_id(folder: Path) -> str:
    """The clone's id: reused when present, else created once, whole, by a hard link; never rewritten."""
    folder.mkdir(mode=0o700, exist_ok=True)
    if found := clone_id(folder):
        return found
    new = secrets.token_hex(8)
    draft = folder / f".tmp-{CLONE_ID}-{new}"
    atomic_write(draft, new + "\n")
    try:
        os.link(draft, folder / CLONE_ID)  # appears with its content, or not at all
    except FileExistsError:
        pass  # another opener's id came first
    finally:
        draft.unlink()
    if found := clone_id(folder):
        return found
    msg = f"{folder / CLONE_ID} is empty: remove it, then start again"
    raise StoreError(msg)


def home(pid: str) -> Path:
    """The project's folder in ``~/.owlbear``."""
    return local_home.root() / PROJECTS / pid


def checkout(pid: str) -> Path | None:
    """The clone the machine's registry lists for project *pid*; None when it lists none or cannot be read."""
    try:
        machine = json.loads((local_home.root() / MACHINE).read_text())
    except OSError, ValueError:
        return None
    projects = machine.get("projects") if isinstance(machine, dict) else None
    found = [p.get("path") for p in projects or () if isinstance(p, dict) and p.get("id") == pid]
    return Path(found[0]) if found and isinstance(found[0], str) else None


def registered(pid: str) -> bool | None:
    """Whether the machine's registry lists project *pid*; None when it cannot be read. Creates nothing."""
    try:
        machine = json.loads((local_home.root() / MACHINE).read_text())
    except FileNotFoundError:
        return False
    except OSError, ValueError:
        return None
    projects = machine.get("projects") if isinstance(machine, dict) else None
    if not isinstance(projects, list):
        return None
    return any(isinstance(p, dict) and p.get("id") == pid for p in projects)


def _left(folder: Path) -> list[Path]:
    """What of a store still lies in the clone's folder."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.name not in KEPT and not p.name.startswith(".tmp-"))


def current(cwd: Path) -> Path | None:
    """The project's store as it lies now, without moving or creating anything; None for a clone with none."""
    folder = clone_dir(cwd)
    if _left(folder):
        return folder  # not moved yet: an older host may run on it
    pid = clone_id(folder)
    return home(pid) if pid else None


def _sync(path: Path) -> None:
    """Flush *path* to disk: a file, or a folder with everything in it."""
    paths = [path] if not path.is_dir() else [path, *path.rglob("*")]
    for p in paths:
        if p.is_symlink():
            continue
        fd = os.open(p, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _move(path: Path, to: Path) -> None:
    """Move *path* to *to*: a rename on one volume; across volumes a flushed copy first, then the source goes."""
    try:
        path.rename(to)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        part = to.with_name(f"{to.name}.partial")
        if part.is_dir():
            shutil.rmtree(part)
        part.unlink(missing_ok=True)
        if path.is_dir():
            shutil.copytree(path, part, symlinks=True)
        else:
            shutil.copy2(path, part)
        _sync(part)
        part.rename(to)
        _sync(to.parent)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    _sync(to.parent)


def located(cwd: Path) -> Path:
    """The project's store folder, created when new; a store still in the clone moves there first.

    Raises:
        FormatTooNewError: A newer runtime marked the clone's folder.
    """
    folder = clone_dir(cwd)
    pid = ensure_id(folder)
    try:
        found = int((folder / MARKER).read_text()) if (folder / MARKER).exists() else 0
    except (OSError, ValueError) as exc:
        msg = "store format marker is unreadable"
        raise StoreError(msg) from exc
    if found > STORE_FORMAT:
        msg = f"store format {found} is newer than {STORE_FORMAT}"
        raise FormatTooNewError(msg)
    target = home(pid)
    dir_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock = open_lock(dir_fd, blocking=True, name=MOVE_LOCK)
    finally:
        os.close(dir_fd)
    try:
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        for path in _left(folder):
            if path.name.endswith(".lock") and path.is_file():
                path.unlink()  # a lock holds no state; an older process may have made it again
            elif (target / path.name).exists():
                msg = (
                    f"{path} and {target / path.name} both exist: an older OwlBear process may still use the clone; "
                    f"stop it (a chat's server: {codebase.STOP}), move one of them away, then start it again"
                )
                raise StoreError(msg)
            else:
                _move(path, target / path.name)
        if (folder / MARKER).exists() and not (target / MARKER).exists():
            shutil.copy2(folder / MARKER, target / MARKER)
        atomic_write(folder / MARKER, f"{STORE_FORMAT}\n")  # an older runtime refuses the clone's folder
    finally:
        os.close(lock)
    return target
