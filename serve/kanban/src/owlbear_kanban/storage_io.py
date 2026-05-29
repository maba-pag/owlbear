"""Crash-safe atomic text write utility.

Provides ``atomic_write(target, content)`` to persist text by writing to a
temporary sibling file and then replacing the destination path atomically.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


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
    # Resolve to absolute path to prevent path traversal attacks
    target = target.resolve()
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
