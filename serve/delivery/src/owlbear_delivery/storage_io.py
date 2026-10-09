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
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_LOCK_FLAGS = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
_READ_ONLY: ContextVar[bool] = ContextVar("owlbear_delivery_read_only_state", default=False)


class ReadOnlyStateError(RuntimeError):
    """A Delivery record write was attempted inside a read-only state scope."""

    code = "ERR_DELIVERY_STATE_READ_ONLY"


@contextlib.contextmanager
def read_only_state() -> Iterator[None]:
    """Refuse every transaction and atomic record write in this context, before any byte changes."""
    token = _READ_ONLY.set(True)
    try:
        yield
    finally:
        _READ_ONLY.reset(token)


def state_is_read_only() -> bool:
    """Return whether the current context forbids Delivery record writes."""
    return _READ_ONLY.get()


def refuse_read_only_write() -> None:
    """Raise ``ReadOnlyStateError`` inside a read-only scope."""
    if _READ_ONLY.get():
        msg = "Delivery state is read-only in this context"
        raise ReadOnlyStateError(msg)


def _open_lock(root_fd: int, *, blocking: bool, shared: bool = False, name: str = ".storage.lock") -> int:
    try:
        lock_fd = os.open(name, _LOCK_FLAGS, 0o600, dir_fd=root_fd)
    except FileNotFoundError:
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


class ControllerFencedError(BlockingIOError):
    """Another process holds the workspace controller lock in a conflicting mode."""


class ControllerLock:
    """One held workspace controller lock; shared for controllers, exclusive for migration and upgrade."""

    __slots__ = ("_fd", "exclusive")

    def __init__(self, fd: int, *, exclusive: bool) -> None:
        self._fd: int | None = fd
        self.exclusive = exclusive

    @property
    def held(self) -> bool:
        """Return whether this handle still holds its lock."""
        return self._fd is not None

    def release(self) -> None:
        """Release the lock once; later calls are no-ops."""
        fd, self._fd = self._fd, None
        if fd is not None:
            os.close(fd)


CONTROLLER_LOCK_NAME = "controller.lock"


def acquire_controller_lock(runtime_root: Path, *, exclusive: bool = False) -> ControllerLock:
    """Take ``runtime/controller.lock`` without blocking, or raise ``ControllerFencedError``."""
    if runtime_root.is_symlink():
        msg = "storage root must not be a symlink"
        raise ValueError(msg)
    runtime_root.mkdir(parents=True, exist_ok=True)
    root_fd = os.open(runtime_root, _DIRECTORY_FLAGS)
    try:
        lock_fd = _open_lock(root_fd, blocking=False, shared=not exclusive, name=CONTROLLER_LOCK_NAME)
    except BlockingIOError as exc:
        mode = "exclusively" if exclusive else "shared"
        msg = f"workspace controller lock cannot be taken {mode}; another Delivery process fences it"
        raise ControllerFencedError(exc.errno, msg) from exc
    finally:
        os.close(root_fd)
    return ControllerLock(lock_fd, exclusive=exclusive)


@contextlib.contextmanager
def locked_roots(roots: Sequence[Path], *, blocking: bool = True, shared: bool = False) -> Iterator[None]:
    """Hold descriptor-backed locks (exclusive unless ``shared``) for canonical storage roots."""
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
                lock_fd = _open_lock(root_fd, blocking=blocking, shared=shared)
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
    refuse_read_only_write()
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
