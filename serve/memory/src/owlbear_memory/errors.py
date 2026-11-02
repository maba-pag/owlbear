"""Domain exception types for memory primitives."""

from __future__ import annotations


class NotFoundError(Exception):
    """Raised when a memory entry does not exist."""


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency validation fails."""


class MemoryBusyError(ConcurrencyError):
    """Raised when the memory writer lock cannot be acquired before its deadline."""


class ValidationError(Exception):
    """Raised when user input or payload validation fails."""


class TransitionError(Exception):
    """Raised when a memory state transition is not allowed."""


class DuplicateEntryError(Exception):
    """Raised when duplicate entry repair cannot complete safely."""

    def __init__(self, entry_id: str, paths: tuple[str, ...]) -> None:
        self.entry_id = entry_id
        self.paths = paths
        super().__init__(f"Duplicate entry ID {entry_id} in memory paths: {', '.join(paths)}")
