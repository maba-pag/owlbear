"""Cross-process writer lock for a memory directory."""

from __future__ import annotations

import errno
import fcntl
import math
import os
import threading
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_memory.errors import MemoryBusyError

if TYPE_CHECKING:
    from collections.abc import Iterator


class _DirectoryLock:
    def __init__(self) -> None:
        self.thread_lock: Any = threading.RLock()
        self.descriptor: int | None = None
        self.depth = 0


_registry: dict[Path, _DirectoryLock] = {}
_registry_lock = threading.Lock()


def _validate_timeout(timeout: float) -> None:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
        msg = "timeout must be a finite non-negative number"
        raise ValueError(msg)


def _acquire_descriptor(resolved_dir: Path, deadline: float) -> int:
    descriptor = os.open(resolved_dir, os.O_RDONLY)
    backoff = 0.001
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    msg = f"Timed out acquiring the memory writer lock for {resolved_dir}"
                    raise MemoryBusyError(msg) from error
                time.sleep(min(backoff, remaining))
                backoff = min(backoff * 2, 0.05)
            else:
                return descriptor
    except BaseException:
        with suppress(OSError):
            os.close(descriptor)
        raise


def _release_descriptor(descriptor: int) -> None:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


@contextmanager
def writer_lock(memory_dir: Path | str, timeout: float = 30.0) -> Iterator[None]:
    """Exclusively lock a resolved memory directory for a bounded duration."""
    _validate_timeout(timeout)
    resolved_dir = Path(memory_dir).resolve()
    deadline = time.monotonic() + timeout
    with _registry_lock:
        state = _registry.setdefault(resolved_dir, _DirectoryLock())

    remaining = max(0.0, deadline - time.monotonic())
    if not state.thread_lock.acquire(timeout=remaining):
        msg = f"Timed out acquiring the memory writer lock for {resolved_dir}"
        raise MemoryBusyError(msg)

    try:
        if state.depth == 0:
            state.descriptor = _acquire_descriptor(resolved_dir, deadline)

        state.depth += 1
        try:
            yield
        finally:
            state.depth -= 1
            if state.depth == 0:
                descriptor = state.descriptor
                state.descriptor = None
                if descriptor is not None:
                    _release_descriptor(descriptor)
    finally:
        state.thread_lock.release()
