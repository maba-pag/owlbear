"""Mtime-scan cache for the cockpit tasks directory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class MtimeScanCache:
    """Scans a directory, tracks mtime changes, and caches associated task data.

    Returns 0 when the directory contains no files.
    ``has_changed()`` detects whether the tasks directory has been modified
    since the last check and updates the internal mtime state.
    """

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._last_mtime: int = -1  # -1 = never scanned
        self._cached_tasks: list[Any] = []
        self._has_cached_tasks = False

    def scan(self) -> int:
        """Return max ``st_mtime_ns`` across all files in the directory.

        Stateless: does not update internal mtime state.

        Returns:
            Maximum mtime in nanoseconds, or 0 if the directory is empty.
        """
        return max(
            (e.stat().st_mtime_ns for e in os.scandir(self._tasks_dir) if e.is_file()),
            default=0,
        )

    def has_changed(self) -> bool:
        """Return True if the directory mtime has changed since the last call.

        Updates ``_last_mtime`` when a change is detected so that subsequent
        calls with no further file modifications return False.
        """
        current = self.scan()
        if current != self._last_mtime:
            self._last_mtime = current
            return True
        return False

    @property
    def last_mtime(self) -> int:
        """Return the last recorded mtime (0 when never scanned or empty dir)."""
        return max(self._last_mtime, 0)

    @property
    def tasks(self) -> list[Any]:
        """Return the cached task summary list."""
        return self._cached_tasks

    @tasks.setter
    def tasks(self, value: list[Any]) -> None:
        self._cached_tasks = value
        self._has_cached_tasks = True

    @property
    def has_cached_tasks(self) -> bool:
        """Return whether tasks have been cached at least once."""
        return self._has_cached_tasks
