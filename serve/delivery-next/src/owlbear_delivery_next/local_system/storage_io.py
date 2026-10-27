# Copied from serve/delivery/src/owlbear_delivery/storage_io.py at ab9cfc6cb; trimmed to the helpers used here.
"""Crash-safe atomic text write and descriptor-backed ``flock`` helpers."""

from __future__ import annotations

import contextlib
import fcntl
import os
import stat
import tempfile
from pathlib import Path

_LOCK_FLAGS = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK


def open_lock(root_fd: int, *, blocking: bool, shared: bool = False, name: str = ".storage.lock") -> int:
    """Open *name* under *root_fd* without following symlinks and ``flock`` it; return the descriptor."""
    lock_fd = os.open(name, _LOCK_FLAGS, 0o600, dir_fd=root_fd)
    if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
        os.close(lock_fd)
        msg = "storage lock must be a regular file"
        raise ValueError(msg)
    flags = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
    if not blocking:
        flags |= fcntl.LOCK_NB
    try:
        fcntl.flock(lock_fd, flags)
    except BaseException:
        os.close(lock_fd)
        raise
    return lock_fd


def atomic_write(target: Path, content: str) -> os.stat_result:
    """Write *content* to *target* atomically via a fsynced sibling ``.tmp-*`` file and ``os.replace``.

    Returns the identity of the inode this call wrote, taken from its own descriptor after the rename, so a later
    replacement of *target* by another writer cannot be mistaken for this write.

    Raises:
        OSError: Any I/O failure; an unrenamed temporary is cleaned up before raising. After a successful rename,
            its old name is no longer owned by this call and is never unlinked.
    """
    fd, tmp_path = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=".tmp")
    renamed = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
            Path(tmp_path).replace(target)
            renamed = True
            written = os.fstat(fh.fileno())
        fsync_dir(target.parent)  # POSIX: so the rename survives a power loss; a pipe or link there raises, never waits
    except Exception:
        if not renamed:
            with contextlib.suppress(OSError):
                Path(tmp_path).unlink()
        raise
    return written


def fsync_dir(folder: Path) -> None:
    """Make the entries of *folder* durable: a rename or unlink in it survives power loss only after this.

    *folder* is opened as a folder only, without following a link at its name or waiting on a pipe: anything else
    there raises, so a pipe swapped in for a moved folder never blocks and a link is never synced through.
    """
    dir_fd = os.open(str(folder), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


class NotRegularError(OSError):
    """A name holds something other than a regular file: a pipe, a folder or a device, so it is never read."""


def read_regular(path: Path) -> bytes | None:
    """*path*'s bytes, from a regular file only; None only when no entry has its name.

    It is opened without following a link and without waiting on a pipe: a link raises `OSError`, any other kind of
    file `NotRegularError`, and every other failure its `OSError`, never an empty or missing answer. The descriptor
    is closed on every path.
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            msg = f"{path.name} is not a regular file"
            raise NotRegularError(msg)
        chunks = []
        while chunk := os.read(fd, 1 << 16):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


_FOLDER = os.O_RDONLY | os.O_DIRECTORY | os.O_NONBLOCK | os.O_CLOEXEC


def _sync_held(fd: int, folder: Path) -> None:
    """Make the entries of *folder* durable through the descriptor held for it; a failure names *folder*."""
    try:
        os.fsync(fd)
    except OSError as exc:
        raise OSError(exc.errno, exc.strerror, str(folder)) from exc


def _mkdir_at(parent: int, name: str, path: Path) -> None:
    """Make the folder *name* inside the folder held open as *parent*, never through a path; a failure names *path*."""
    try:
        os.mkdir(name, 0o777, dir_fd=parent)
    except OSError as exc:  # the same kind of error, e.g. `FileExistsError`, now naming the whole path
        raise OSError(exc.errno, exc.strerror, str(path)) from exc


def _folder_entries(folder: Path) -> list[tuple[Path, os.stat_result]]:
    logical, physical = folder.absolute(), folder.resolve(strict=True)
    paths = dict.fromkeys((logical, *logical.parents, physical, *physical.parents))
    return [(path, path.lstat()) for path in paths]


def _unchanged(held: list[tuple[Path, int]], entries: list[tuple[Path, os.stat_result]]) -> None:
    """Revalidate both the original entries/aliases and the folders held open, after each blocking sync."""
    for path, before in entries:
        try:
            same = os.path.samestat(path.lstat(), before)
        except OSError as exc:
            msg = f"{path} changed while its folders were made, so nothing more is made there"
            raise OSError(msg) from exc
        if not same:
            msg = f"{path} changed while its folders were made, so nothing more is made there"
            raise OSError(msg)
    for path, fd in held:
        if not os.path.samestat(path.stat(), os.fstat(fd)):
            msg = f"{path} changed while its folders were made, so nothing more is made there"
            raise OSError(msg)


def make_dirs(folder: Path) -> None:
    """Create *folder* and its missing ancestors, syncing each new folder's parent so the new entry is durable.

    The deepest existing ancestor's parent link is re-synced before anything is created: an interrupted earlier call
    may have made that folder without confirming its entry. That ancestor and its parent are opened before that sync
    and every new folder is made and opened inside the folder held open above it, never through a path, without
    waiting on a pipe and without following a link at a new folder's name. After every sync, before anything more is
    made, each path must still name the folder held for it and its original directory entries and ancestor aliases
    must be unchanged. Existing aliases remain supported; a new link back to the same moved folder is refused too.
    The descriptors are closed on every path.
    """
    missing: list[Path] = []
    for candidate in (folder, *folder.parents):
        if candidate.exists():
            break
        missing.append(candidate)
    entries = _folder_entries(candidate)
    held: list[tuple[Path, int]] = []
    try:
        top = candidate.parent if candidate.parent != candidate else None
        if top is not None:  # the existing folders are held open before any blocking sync
            held.append((top, os.open(top, _FOLDER)))
        if missing:
            held.append((candidate, os.open(candidate, _FOLDER)))
        if top is not None:
            _sync_held(held[0][1], top)
        for created in reversed(missing):
            _unchanged(held, entries)
            outer = held[-1][1]
            _mkdir_at(outer, created.name, created)
            held.append((created, os.open(created.name, _FOLDER | os.O_NOFOLLOW, dir_fd=outer)))
            entries.append((created, os.fstat(held[-1][1])))
            _sync_held(outer, created.parent)
        _unchanged(held, entries)
    finally:
        for _, fd in held:
            os.close(fd)
