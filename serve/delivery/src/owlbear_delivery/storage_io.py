"""Crash-safe atomic text write utility.

Provides ``atomic_write(target, content)`` to persist text by writing to a
temporary sibling file and then replacing the destination path atomically.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_LOCK_FLAGS = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW


def _open_lock(root_fd: int) -> int:
    try:
        lock_fd = os.open(".storage.lock", _LOCK_FLAGS, 0o600, dir_fd=root_fd)
    except FileNotFoundError:
        lock_fd = os.open(".storage.lock", _LOCK_FLAGS, 0o600, dir_fd=root_fd)
    if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
        msg = "storage lock must be a regular file"
        raise ValueError(msg)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    return lock_fd


@contextlib.contextmanager
def locked_roots(roots: Sequence[Path]) -> Iterator[None]:
    """Hold exclusive descriptor-backed locks for canonical storage roots."""
    descriptors: list[tuple[int, int]] = []
    resolved_roots: dict[Path, Path] = {}
    for root in roots:
        if root.is_symlink():
            msg = "storage root must not be a symlink"
            raise ValueError(msg)
        root.mkdir(parents=True, exist_ok=True)
        resolved_roots[root.resolve()] = root
    try:
        for canonical_root in sorted(resolved_roots):
            root_fd = os.open(canonical_root, _DIRECTORY_FLAGS)
            try:
                lock_fd = _open_lock(root_fd)
            except Exception:
                os.close(root_fd)
                raise
            descriptors.append((root_fd, lock_fd))
        yield
    finally:
        for root_fd, lock_fd in reversed(descriptors):
            os.close(lock_fd)
            os.close(root_fd)


def atomic_write(target: Path, content: str) -> None:
    """Write *content* to *target* atomically via a sibling .tmp-* file.

    Sequence:
    1. ``mkstemp`` creates a ``.tmp-{random}.md`` in the same directory.
    2. Write *content* to the temp file descriptor (UTF-8, LF line endings).
    3. ``fsync`` the file fd.
    4. ``os.replace(tmp, target)`` — atomic rename.
    5. On POSIX: ``fsync`` the parent directory fd.
    6. On any error after step 1: delete the temp file, then re-raise.

    Args:
        target:  Destination path.
        content: UTF-8 text to write.

    Raises:
        OSError: Any I/O failure; the temp file is cleaned up before raising.
    """
    fd, tmp_path = tempfile.mkstemp(
        dir=target.parent,
        prefix=".tmp-",
        suffix=".md",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        Path(tmp_path).replace(target)
        # POSIX: fsync parent directory so the rename survives a power loss
        if hasattr(os, "O_DIRECTORY"):
            dir_fd = os.open(str(target.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except Exception:
        with contextlib.suppress(OSError):
            Path(tmp_path).unlink()
        raise
