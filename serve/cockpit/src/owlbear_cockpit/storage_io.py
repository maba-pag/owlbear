"""Atomic file writes for Cockpit-owned files."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


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
