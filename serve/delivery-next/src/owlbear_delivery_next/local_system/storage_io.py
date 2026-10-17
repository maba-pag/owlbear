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


def atomic_write(target: Path, content: str) -> None:
    """Write *content* to *target* atomically via a fsynced sibling ``.tmp-*`` file and ``os.replace``.

    Raises:
        OSError: Any I/O failure; the temp file is cleaned up before raising.
    """
    fd, tmp_path = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        Path(tmp_path).replace(target)
        # POSIX: fsync parent directory so the rename survives a power loss
        dir_fd = os.open(str(target.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        with contextlib.suppress(OSError):
            Path(tmp_path).unlink()
        raise
