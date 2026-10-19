"""Where a project's live Delivery state lives (TD-334): ``~/.owlbear/projects/<id>/``, one folder per project.

The clone keeps only ``<git common dir>/owlbear-delivery/``, holding the project's id (``clone-id``) and a format
marker every older runtime refuses, so a moved or renamed clone keeps its project and a re-clone gets a new one.
A store still in the clone moves to its folder once, on first open; a move cut short resumes on the next.
"""

from __future__ import annotations

import os
import secrets
import shutil
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, FormatTooNewError, StoreError

if TYPE_CHECKING:
    from pathlib import Path

STORE_DIR = "owlbear-delivery"
PROJECTS = "projects"
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
    """The clone's id: reused when present, else created once with ``O_EXCL``; never rewritten."""
    folder.mkdir(mode=0o700, exist_ok=True)
    if found := clone_id(folder):
        return found
    new = secrets.token_hex(8)
    try:
        fd = os.open(folder / CLONE_ID, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:  # another process created it first
        return clone_id(folder) or new
    with os.fdopen(fd, "w") as out:
        out.write(new + "\n")
        out.flush()
        os.fsync(out.fileno())
    return new


def home(pid: str) -> Path:
    """The project's folder in ``~/.owlbear``."""
    return local_home.root() / PROJECTS / pid


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
            if (target / path.name).exists():
                msg = f"{path} and {target / path.name} both exist: move one away, then start again"
                raise StoreError(msg)
            shutil.move(path, target / path.name)
        if (folder / MARKER).exists() and not (target / MARKER).exists():
            shutil.copy2(folder / MARKER, target / MARKER)
        atomic_write(folder / MARKER, f"{STORE_FORMAT}\n")  # an older runtime refuses the clone's folder
    finally:
        os.close(lock)
    return target
