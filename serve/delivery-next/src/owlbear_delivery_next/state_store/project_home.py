"""Where a project's live Delivery state lives (TD-334): ``~/.owlbear/projects/<id>/``, one folder per project.

The clone keeps only ``<git common dir>/owlbear-delivery/``, holding the project's id (``clone-id``) and a format
marker every older runtime refuses, so a moved or renamed clone keeps its project and a re-clone gets a new one.
A store still in the clone moves to its folder once, on first open, by ``project_move``; a move cut short resumes
on the next open only when its record proves it. Before any move, every lock file in the clone is taken exclusively
without waiting; a held one refuses the move, so a running writer cannot update the old path while it moves.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import secrets
import stat
from pathlib import Path

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.local_system.storage_io import open_lock
from owlbear_delivery_next.state_store import fd_tree, project_move
from owlbear_delivery_next.state_store.database import (
    MARKER,
    MIGRATE,
    STORE_FORMAT,
    FormatTooNewError,
    StoreError,
)

STORE_DIR = "owlbear-delivery"
PROJECTS = "projects"
MACHINE = "machine.json"  # the registry (``machine_host.registry``); read here only to tell a project from leftovers


def clone_dir(cwd: Path) -> Path:
    """The clone's own Delivery folder: its id and the marker."""
    return git_common_dir(cwd) / STORE_DIR


def clone_id(folder: Path) -> str | None:
    """The id written into the clone's folder, or None when there is none."""
    fd = project_move.pin(folder)
    if fd is None:
        return None
    try:
        return _clone_id_at(folder, fd)
    finally:
        os.close(fd)


def _clone_id_at(folder: Path, folder_fd: int) -> str | None:
    try:
        text = fd_tree.read_at(folder_fd, project_move.CLONE_ID)
    except OSError as exc:
        msg = f"{folder / project_move.CLONE_ID} is unreadable"
        raise StoreError(msg) from exc
    if text and not text.endswith("\n"):  # the id is written with its newline last, so this one was cut short
        msg = f"{folder / project_move.CLONE_ID} is incomplete: its write was cut short; nothing was changed"
        raise StoreError(msg)
    return (text or "").strip() or None


def _pin(folder: Path) -> int:
    fd = project_move.pin(folder)
    if fd is None:
        msg = f"{folder} is missing: nothing was moved"
        raise StoreError(msg)
    return fd


def _ensure_at(folder: Path, folder_fd: int) -> str:
    """The clone's id: reused when present, else created once, exclusively; never rewritten or replaced."""
    if found := _clone_id_at(folder, folder_fd):
        return found
    with contextlib.suppress(FileExistsError):  # another opener's id came first; it is read below
        fd_tree.create_at(folder_fd, project_move.CLONE_ID, secrets.token_hex(8) + "\n")
    if found := _clone_id_at(folder, folder_fd):
        return found
    msg = f"{folder / project_move.CLONE_ID} is empty: remove it, then start again"
    raise StoreError(msg)


def ensure_id(folder: Path) -> str:
    """The clone's id, created once when missing; see ``_ensure_at``."""
    folder.mkdir(mode=0o700, exist_ok=True)
    fd = _pin(folder)
    try:
        return _ensure_at(folder, fd)
    finally:
        os.close(fd)


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


def current(cwd: Path) -> Path | None:
    """The project's store as it lies now, without moving or creating anything; None for a clone with none.

    A switched store is named only while the target still is the copy the switch recorded.
    """
    folder = clone_dir(cwd)
    rec = project_move.record(folder)
    if project_move.left(folder) and not (rec and rec["phase"] == project_move.SWITCHED):
        return folder  # not moved yet, or its copy is not yet the authority: an older host may run on it
    pid = clone_id(folder)
    if not pid:
        return None
    target = home(pid)
    if rec and rec["phase"] == project_move.SWITCHED:
        project_move.named_switched(target, rec)
    return target


def _is_lock(name: str) -> bool:
    return name == "lock" or name.endswith(".lock") or name == MIGRATE


def _fence(folder_fd: int) -> list[int]:
    """Hold every lock file in the clone exclusively, without waiting; a busy one refuses the move.

    A live host, a change's writer, a profile writer or a database operation (``migrate.lock`` shared) each hold
    their lock, so none can write to the old path while it moves. The walk is by descriptor and never follows a
    link; the descriptors stay open through the move.
    """
    held: list[int] = []
    try:
        _hold(folder_fd, "", held)
    except BaseException:
        for fd in held:
            os.close(fd)
        raise
    return held


def _hold(dfd: int, rel: str, held: list[int]) -> None:
    names = set(os.listdir(dfd))
    if not rel:
        names.add(MIGRATE)  # always fenced: created when missing, as the database's shared lock needs it
    for name in sorted(names):
        if name == project_move.MOVE_LOCK:
            continue
        if _is_lock(name):
            _lock_at(dfd, name, rel + name, held)
            continue
        st = fd_tree.stat_at(dfd, name)
        if st is not None and stat.S_ISDIR(st.st_mode):
            sub = fd_tree.open_dir(dfd, name)
            try:
                _hold(sub, f"{rel}{name}/", held)
            finally:
                os.close(sub)


def _lock_at(dfd: int, name: str, path: str, held: list[int]) -> None:
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CREAT, 0o600, dir_fd=dfd)
    except OSError as exc:
        msg = f"{path} cannot be locked ({exc.strerror}): nothing was moved"
        raise StoreError(msg) from exc
    held.append(fd)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        msg = f"{path} is held by a running process: nothing was moved"
        raise StoreError(msg) from exc


def _has_locks(folder_fd: int) -> bool:
    return any(_is_lock(n) and n != project_move.MOVE_LOCK for n in os.listdir(folder_fd))


def _publish_markers(folder_fd: int, pfd: int, target: Path, previous: int, *, moved: bool) -> None:
    project_move.make_dir(pfd, target.name)
    tfd = fd_tree.open_dir(pfd, target.name)
    try:
        if fd_tree.stat_at(tfd, MARKER) is None:
            fd_tree.write_at(tfd, MARKER, f"{previous or STORE_FORMAT}\n")  # keeps the format it was written in
    finally:
        os.close(tfd)
    # a moved clone keeps the fence: its retained source must not be opened again as a store by an older runtime
    fd_tree.write_at(folder_fd, MARKER, f"{project_move.FENCE if moved else STORE_FORMAT}\n")


def located(cwd: Path) -> Path:
    """The project's store folder, created when new; a store still in the clone moves there first.

    Raises:
        FormatTooNewError: A newer runtime marked the clone's folder.
        StoreError: The clone's store must move and no offline proof exists, or a lock is held.
    """
    return _open(cwd, None)


def migrated(cwd: Path, proof: project_move.OfflineProof) -> Path:
    """Prepared-and-finished move entry: the store moves to its folder under *proof*, which only ``finish`` issues."""
    return _open(cwd, proof)


def _marker_at(folder_fd: int) -> int:
    try:
        text = fd_tree.read_at(folder_fd, MARKER)
        return 0 if text is None else int(text)
    except (OSError, ValueError) as exc:
        msg = "store format marker is unreadable"
        raise StoreError(msg) from exc


def _refuse_links(folder: Path, folder_fd: int, names: list[str]) -> None:
    for name in names:
        st = fd_tree.stat_at(folder_fd, name)
        if st is not None and stat.S_ISLNK(st.st_mode):
            msg = f"{folder / name} holds a link: refusing to move it; nothing was moved"
            raise StoreError(msg)


def _prior(text: str | None) -> int:
    """A format the store held before its offline move; the fence itself is never a prior format."""
    value = int(text) if text and text.strip() else 0
    if value >= int(project_move.FENCE):
        msg = "the preparation recorded the fence as the prior format: refusing the offline move"
        raise StoreError(msg)
    return value


def _format_at(folder_fd: int, proof: project_move.OfflineProof | None) -> int:
    """The store's format for this open: the prior format a proof names, else the clone's own marker, unfenced."""
    if proof is not None:
        return _prior(proof.previous)
    found = _marker_at(folder_fd)
    if found > STORE_FORMAT:
        msg = f"store format {found} is newer than {STORE_FORMAT}"
        raise FormatTooNewError(msg)
    return found


def _previous_at(folder_fd: int) -> int:
    """The prior format the preparation recorded for a switched move; 0 when no preparation exists."""
    try:
        text = fd_tree.read_at(folder_fd, project_move.PREPARED)
        found = json.loads(text) if text else {}
        marker = found.get("marker") if isinstance(found, dict) else None
    except (OSError, ValueError) as exc:
        msg = f"{project_move.PREPARED} is unreadable: refusing to admit the moved store"
        raise StoreError(msg) from exc
    return _prior(marker)


def _open(cwd: Path, proof: project_move.OfflineProof | None) -> Path:
    folder = clone_dir(cwd)
    folder.mkdir(mode=0o700, exist_ok=True)
    folder_fd = _pin(folder)
    try:
        pid = _ensure_at(folder, folder_fd)
        target = home(pid)
        lock = open_lock(folder_fd, blocking=True, name=project_move.MOVE_LOCK)
        try:
            rec = project_move.record_at(folder, folder_fd)
            fd_tree.refuse_quarantined(folder_fd, folder)  # before anything is recorded, fenced or moved
            if rec is not None and rec["phase"] == project_move.SWITCHED:
                _open_switched(folder_fd, target, rec, _previous_at(folder_fd))  # the fence is ours: check it first
                return target
            found = _format_at(folder_fd, proof)
            left = project_move.left_at(folder_fd)
            _refuse_links(folder, folder_fd, left)
            pending = bool(left) or rec is not None
            if pending:
                project_move.require_proof(
                    folder, folder_fd, target, proof
                )  # refused before anything is fenced or moved
            held = _fence(folder_fd) if pending or _has_locks(folder_fd) else []  # nothing to fence otherwise
            try:
                pfd = project_move.pin_parent(target)
                try:
                    if pending:
                        project_move.relocate(folder, folder_fd, target, pfd, rec, proof)
                finally:
                    os.close(pfd)
                pfd = project_move.pin_parent(target)  # re-pinned: the path may have been swapped during the move
                try:
                    if pending:
                        project_move.check_switched(target, pfd, project_move.record_at(folder, folder_fd))
                    _publish_markers(folder_fd, pfd, target, found, moved=pending or proof is not None)
                finally:
                    os.close(pfd)
            finally:
                for fd in held:
                    os.close(fd)
        finally:
            os.close(lock)
    finally:
        os.close(folder_fd)
    return target


def _open_switched(folder_fd: int, target: Path, rec: dict, previous: int) -> None:
    """Admit the switched target by identity, keeping the source fenced; the source is never read or moved again."""
    held = _fence(folder_fd)  # the old path stays locked for as long as this process runs
    try:
        pfd = project_move.pin_parent(target)
        try:
            project_move.check_switched(target, pfd, rec)
            _publish_markers(folder_fd, pfd, target, previous, moved=True)
        finally:
            os.close(pfd)
    finally:
        for fd in held:
            os.close(fd)
