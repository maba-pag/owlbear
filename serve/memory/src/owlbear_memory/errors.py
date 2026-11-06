"""Domain exception types for memory primitives."""

from __future__ import annotations


def diagnostic(error: BaseException) -> str:
    """Keep the type, message and notes of an operational or already-safe validation error."""
    return "\n".join([f"{type(error).__name__}: {error}", *getattr(error, "__notes__", ())])


def read_warning(read_errors: dict[str, str]) -> str:
    """Label omissions without confusing them with readable memory entries."""
    if not read_errors:
        return ""
    return "Memory read warnings (only readable entries were considered):\n" + "\n".join(
        f"- {path}: {detail}" for path, detail in read_errors.items()
    )


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
