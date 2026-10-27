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
from owlbear_delivery_next.local_system.maintenance import Maintenance, MaintenanceError
from owlbear_delivery_next.local_system.storage_io import open_lock
from owlbear_delivery_next.state_store import fd_tree, format_marker, pack_run_record, project_move, project_switch
from owlbear_delivery_next.state_store.database import (
    MARKER,
    MIGRATE,
    STORE_FORMAT,
    FormatTooNewError,
    StoreError,
)
from owlbear_delivery_next.state_store.offline_proof import OfflineProof, require_identity, require_proof

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
        msg = f"{folder / project_move.CLONE_ID} is unreadable: {exc}; nothing was changed"
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


def _durable_id(folder: Path, folder_fd: int) -> str | None:
    """The id on disk, adopted only once its file and folder are synced and the file is still the one read.

    Complete bytes alone prove nothing: a file whose sync failed reads the same, so it is synced again first.
    """
    path = folder / project_move.CLONE_ID
    try:
        fd = os.open(project_move.CLONE_ID, fd_tree.FILE_FLAGS | os.O_NONBLOCK, dir_fd=folder_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = f"{path} is unreadable: {exc}; nothing was changed"
        raise StoreError(msg) from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            msg = f"{path} is unreadable: it is not a regular file; nothing was changed"
            raise StoreError(msg)
        held = fd_tree.ident(os.fstat(fd))
        try:
            text = b"".join(iter(lambda: os.read(fd, 1 << 16), b"")).decode()
            os.fsync(fd)
            os.fsync(folder_fd)
        except (OSError, ValueError) as exc:
            msg = f"{path} could not be made durable ({exc}): nothing was registered; it is kept"
            raise StoreError(msg) from exc
    finally:
        os.close(fd)
    now = fd_tree.stat_at(folder_fd, project_move.CLONE_ID)
    if now is None or fd_tree.ident(now) != held:
        msg = f"{path} was replaced while its id was made durable: nothing was registered; both are kept"
        raise StoreError(msg)
    if text and not text.endswith("\n"):
        msg = f"{path} is incomplete: its write was cut short; nothing was changed"
        raise StoreError(msg)
    return text.strip() or None


def _ensure_at(folder: Path, folder_fd: int) -> str:
    """The clone's id: reused when present, else created once, exclusively; never rewritten or replaced."""
    if found := _durable_id(folder, folder_fd):
        return found
    with contextlib.suppress(FileExistsError):  # another opener's id came first; it is read below
        fd_tree.create_at(folder_fd, project_move.CLONE_ID, secrets.token_hex(8) + "\n")
    if found := _durable_id(folder, folder_fd):
        return found
    msg = f"{folder / project_move.CLONE_ID} is empty: remove it, then start again"
    raise StoreError(msg)


def _same_folder(folder: Path, folder_fd: int) -> None:
    """Refuse unless the logical folder still names the pinned one: its id is not this clone's otherwise."""
    try:
        now = folder.stat(follow_symlinks=False)
    except OSError:
        now = None
    if now is None or fd_tree.ident(now) != fd_tree.ident(os.fstat(folder_fd)):
        msg = f"{folder} was replaced while its id was made durable: nothing was registered; both are kept"
        raise StoreError(msg)


def ensure_id(folder: Path) -> str:
    """The clone's id, created once when missing; see ``_ensure_at``, and refused if the folder was swapped."""
    folder.mkdir(mode=0o700, exist_ok=True)
    fd = _pin(folder)
    try:
        found = _ensure_at(folder, fd)
        _same_folder(folder, fd)
        return found
    finally:
        os.close(fd)


def ensure_pinned(folder: Path, folder_fd: int) -> str:
    """The clone's id, made on the descriptor the caller already pinned to *folder*; refused if the path moved."""
    found = _ensure_at(folder, folder_fd)
    _same_folder(folder, folder_fd)
    return found


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


def _switched_to(target: Path, rec: dict) -> None:
    """Refuse a SWITCHED receipt that names a store other than *target*, the one the project's id lays out."""
    if rec["target"] != str(target):
        msg = f"{target.parent} switched to {rec['target']}, not {target}: nothing was changed; check the receipt"
        raise StoreError(msg)


def current(cwd: Path) -> Path | None:
    """The project's store as it lies now, without moving or creating anything; None for a clone with none.

    A switched store is named only while the target still is the copy the switch recorded.
    """
    folder = clone_dir(cwd)
    folder_fd = project_move.pin(folder)
    if folder_fd is None:
        return None
    try:
        rec = project_move.record_at(folder, folder_fd)
        if project_move.left_at(folder_fd) and not (rec and rec["phase"] == project_move.SWITCHED):
            return folder  # not moved yet, or its copy is not yet the authority
        if rec and rec["phase"] == project_move.SWITCHED:
            project_switch.prepared_prior(folder_fd)
        pid = _clone_id_at(folder, folder_fd)
        _same_folder(folder, folder_fd)
    finally:
        os.close(folder_fd)
    if not pid:
        return None
    target = home(pid)
    if rec and rec["phase"] == project_move.SWITCHED:
        _switched_to(target, rec)
        project_switch.named_switched(target, rec)
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
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CREAT, 0o600, dir_fd=dfd)
    except OSError as exc:
        msg = f"{path} cannot be locked ({exc.strerror}): nothing was moved"
        raise StoreError(msg) from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):  # a special file would block a lock or a read: refused, untouched
        os.close(fd)
        msg = f"{path} is not a regular file: nothing was moved"
        raise StoreError(msg)
    held.append(fd)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        msg = f"{path} is held by a running process: nothing was moved"
        raise StoreError(msg) from exc


def _has_locks(folder_fd: int) -> bool:
    return any(_is_lock(n) and n != project_move.MOVE_LOCK for n in os.listdir(folder_fd))


def _publish_markers(folder_fd: int, tfd: int, previous: int, *, moved: bool) -> None:
    """Write the target's format through the descriptor already validated: the name is never reopened here."""
    format_marker.ensure_target(tfd, previous)
    # a moved clone keeps the fence: its retained source must not be opened again as a store by an older runtime
    fd_tree.write_at(folder_fd, MARKER, f"{project_move.FENCE if moved else STORE_FORMAT}\n")


def _publish_proven(folder_fd: int, pfd: int, target: Path, rec: dict, previous: int) -> None:
    """Publish the switched target's format through the folder the switch validated, then recheck its name."""
    tfd = project_switch.check_switched(target, pfd, rec)
    try:
        _publish_markers(folder_fd, tfd, previous, moved=True)
        project_switch.named_switched(target, rec)  # the name still reaches the descriptor written through
    finally:
        os.close(tfd)


def located(cwd: Path) -> Path:
    """The project's store folder, created when new; a store still in the clone moves there first.

    Raises:
        FormatTooNewError: A newer runtime marked the clone's folder.
        StoreError: The clone's store must move and no offline proof exists, or a lock is held.
    """
    return _open(cwd, None)


def migrated(cwd: Path, proof: OfflineProof) -> Path:
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


def _format_at(folder_fd: int, proof: OfflineProof | None) -> int:
    """The store's format for this open: the prior format a proof names, else the clone's own marker, unfenced."""
    if proof is not None:
        return format_marker.prior_format(proof.previous)
    found = _marker_at(folder_fd)
    if found > STORE_FORMAT:
        msg = f"store format {found} is newer than {STORE_FORMAT}"
        raise FormatTooNewError(msg)
    return found


def _generation_at(folder: Path, folder_fd: int, proof: OfflineProof) -> None:
    """Refuse unless the pinned folder still holds the exact preparation and the fence that finish verified."""
    try:
        prepared = fd_tree.read_at(folder_fd, project_move.PREPARED)
        marker = fd_tree.read_at(folder_fd, MARKER)
    except (OSError, ValueError) as exc:
        msg = f"{folder} holds an unexpected entry where its preparation belongs: nothing was changed"
        raise StoreError(msg) from exc
    if prepared != proof.prepared or marker is None or marker.strip() != project_move.FENCE:
        msg = f"{folder} is not the folder finish verified as prepared and fenced: nothing was changed; start again"
        raise StoreError(msg)


def _settle_pack_run(folder: Path, folder_fd: int, proof: OfflineProof | None) -> None:
    """Settle through the held source only; receipt lookup is read-only and precedes the final custody check."""
    if project_move.record_at(folder, folder_fd) is not None:
        return
    clone = _clone_id_at(folder, folder_fd)

    def receipted(digest: str) -> str:
        if clone is None:
            msg = f"{folder} has no clone id to read its design-pack receipt by: nothing was moved"
            raise StoreError(msg)
        return Maintenance.lookup_receipt(clone, digest)

    def guard() -> None:
        _same_folder(folder, folder_fd)
        if proof is not None:
            require_identity(folder, folder_fd, proof)
            _generation_at(folder, folder_fd, proof)
        if _clone_id_at(folder, folder_fd) != clone:
            msg = f"{folder} changed its clone id during receipt lookup: nothing was changed"
            raise StoreError(msg)

    try:
        pack_run_record.settle(folder, receipted=receipted, folder_fd=folder_fd, guard=guard)
    except (OSError, ValueError, MaintenanceError) as exc:
        msg = f"the design-pack run record in {folder} could not be settled: {exc}; nothing was moved"
        raise StoreError(msg) from exc


def _open(cwd: Path, proof: OfflineProof | None) -> Path:
    folder = clone_dir(cwd)
    folder.mkdir(mode=0o700, exist_ok=True)
    folder_fd = _pin(folder)
    try:
        if proof is not None:
            # Both checks run before anything in the folder is read for admission or written.
            require_identity(folder, folder_fd, proof)
            _generation_at(folder, folder_fd, proof)  # the verified preparation and fence, not a reused inode
            fd_tree.refuse_quarantined(folder_fd, folder)
            _settle_pack_run(folder, folder_fd, proof)
            require_identity(folder, folder_fd, proof)
            _generation_at(folder, folder_fd, proof)
        rec = project_move.record_at(folder, folder_fd)
        if rec and rec["phase"] == project_move.SWITCHED:
            project_switch.prepared_prior(folder_fd)  # before even the clone id is synced or repaired
        pid = _ensure_at(folder, folder_fd)
        target = home(pid)
        lock = open_lock(folder_fd, blocking=True, name=project_move.MOVE_LOCK)
        try:
            rec = project_move.record_at(folder, folder_fd)
            fd_tree.refuse_quarantined(folder_fd, folder)  # before anything is recorded, fenced or moved
            if rec is not None and rec["phase"] == project_move.SWITCHED:
                _open_switched(folder_fd, target, rec, project_switch.prepared_prior(folder_fd))
                return target
            found = _format_at(folder_fd, proof)
            left = project_move.left_at(folder_fd)
            _refuse_links(folder, folder_fd, left)
            pending = bool(left) or rec is not None
            if pending:
                require_proof(folder, folder_fd, target, proof)  # refused before anything is fenced or moved
            held = _fence(folder_fd) if pending or _has_locks(folder_fd) else []  # nothing to fence otherwise
            try:
                _move_and_publish(folder, folder_fd, target, proof, rec, found, pending=pending)
            finally:
                for fd in held:
                    os.close(fd)
        finally:
            os.close(lock)
    finally:
        os.close(folder_fd)
    return target


def _move_and_publish(  # noqa: PLR0913, PLR0917
    folder: Path,
    folder_fd: int,
    target: Path,
    proof: OfflineProof | None,
    rec: dict | None,
    found: int,
    *,
    pending: bool,
) -> None:
    """Move the store into *target* when pending, then publish its markers, re-pinning the parent after the move."""
    pfd = project_move.pin_parent(target)
    try:
        if pending:
            project_move.relocate(folder, folder_fd, target, pfd, rec, proof, found)
    finally:
        os.close(pfd)
    pfd = project_move.pin_parent(target)  # re-pinned: the path may have been swapped during the move
    try:
        if pending:
            _publish_proven(folder_fd, pfd, target, project_move.record_at(folder, folder_fd), found)
        else:
            project_move.make_dir(pfd, target.name)
            tfd = fd_tree.open_dir(pfd, target.name)
            try:
                _publish_markers(folder_fd, tfd, found, moved=proof is not None)
            finally:
                os.close(tfd)
    finally:
        os.close(pfd)


def _switched_source_at(folder_fd: int) -> None:
    """Refuse a switched source whose marker is not the fence or a readable older format; nothing is written."""
    try:
        text = fd_tree.read_at(folder_fd, MARKER)
    except OSError as exc:
        msg = "the switched source's format marker is unreadable: nothing was changed"
        raise StoreError(msg) from exc
    value = text.strip() if text is not None else ""
    if not value.isdigit():
        msg = "the switched source has no readable format marker: nothing was changed"
        raise StoreError(msg)
    found = int(value)
    if found == int(project_move.FENCE) or 1 <= found <= STORE_FORMAT:
        return
    if found > STORE_FORMAT:
        msg = f"switched source format {found} is newer than {STORE_FORMAT}: nothing was changed"
        raise FormatTooNewError(msg)
    msg = f"switched source format {found} is not a known format: nothing was changed"
    raise StoreError(msg)


def _open_switched(folder_fd: int, target: Path, rec: dict, previous: int) -> None:
    """Admit the switched target by identity, keeping the source fenced; the source is never read or moved again."""
    _switched_source_at(folder_fd)  # before the receipt is trusted, the source marker must be ours or known
    _switched_to(target, rec)
    held = _fence(folder_fd)  # the old path stays locked for as long as this process runs
    try:
        pfd = project_move.pin_parent(target)
        try:
            _publish_proven(folder_fd, pfd, target, rec, previous)
        finally:
            os.close(pfd)
    finally:
        for fd in held:
            os.close(fd)
