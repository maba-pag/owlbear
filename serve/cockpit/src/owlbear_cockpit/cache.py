"""Mtime-scan cache for the cockpit tasks directory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class MtimeScanCache:
    """Scans a directory and returns the max ``st_mtime_ns`` across all files.

    Returns 0 when the directory contains no files.
    """

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir

    def scan(self) -> int:
        """Return max ``st_mtime_ns`` across all files in the directory.

        Returns:
            Maximum mtime in nanoseconds, or 0 if the directory is empty.
        """
        return max(
            (e.stat().st_mtime_ns for e in os.scandir(self._tasks_dir) if e.is_file()),
            default=0,
        )
