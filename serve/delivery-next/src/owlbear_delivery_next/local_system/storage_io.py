# Copied from serve/delivery/src/owlbear_delivery/storage_io.py at ab9cfc6cb; trimmed to the helpers used here.
"""Crash-safe atomic text write and descriptor-backed ``flock`` helpers."""

from __future__ import annotations

import contextlib
import fcntl
import os
import stat
import tempfile
from pathlib import Path

_LOCK_FLAGS = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW


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


def make_dirs(folder: Path) -> None:
    """Create *folder* and its missing ancestors, fsyncing each new folder's parent so the new entry is durable.

    The deepest existing ancestor's parent link is re-synced before anything is created: an interrupted earlier call
    may have made that folder without confirming its entry.
    """
    missing: list[Path] = []
    for candidate in (folder, *folder.parents):
        if candidate.exists():
            if candidate.parent != candidate:
                fsync_dir(candidate.parent)
            break
        missing.append(candidate)
    for created in reversed(missing):
        created.mkdir()
        fsync_dir(created.parent)
