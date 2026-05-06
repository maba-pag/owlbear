"""Mtime-scan cache for the cockpit tasks directory."""

from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class MtimeScanCache:
    """Scans a directory, tracks directory-signature changes, and caches task data.

    Returns 0 when the directory contains no task files.
    ``has_changed()`` detects whether the directory signature has changed
    since the last check and updates the internal signature state.
    """

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._last_signature: int = -1  # -1 = never scanned
        self._cached_tasks: list[Any] = []
        self._has_cached_tasks = False

    def scan(self) -> int:
        """Return a directory signature for direct child task markdown files.

        Stateless: does not update internal mtime state.

        Returns:
            Deterministic positive integer signature, or 0 if no task files exist.
        """
        digest = hashlib.blake2b(digest_size=8)
        found = False

        try:
            entries = sorted(os.scandir(self._tasks_dir), key=lambda entry: entry.name)
        except FileNotFoundError:
            return 0

        for entry in entries:
            if not entry.is_file():
                continue
            name = entry.name
            if name.startswith((".", ".tmp-")):
                continue
            if not name.endswith(".md"):
                continue

            found = True
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(entry.stat().st_mtime_ns.to_bytes(8, "big", signed=False))

        if not found:
            return 0
        return int.from_bytes(digest.digest(), "big")

    def has_changed(self) -> bool:
        """Return True if the directory signature has changed since the last call.

        Updates ``_last_signature`` when a change is detected so that subsequent
        calls with no further file modifications return False.
        """
        return self.has_changed_at(self.scan())

    def has_changed_at(self, signature: int) -> bool:
        """Return True when ``signature`` differs from the last seen value.

        This enables callers to scan once and make an atomic change decision.
        """
        if self.changed_since(signature):
            self.commit_signature(signature)
            return True
        return False

    def changed_since(self, signature: int) -> bool:
        """Return True when ``signature`` differs from the last committed value."""
        return signature != self._last_signature

    def commit_signature(self, signature: int) -> None:
        """Record ``signature`` as the last committed directory signature."""
        self._last_signature = signature

    @property
    def last_mtime(self) -> int:
        """Return the last recorded signature (0 when never scanned)."""
        return max(self._last_signature, 0)

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
