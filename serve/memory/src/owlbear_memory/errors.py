"""Domain exception types for memory primitives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class NotFoundError(Exception):
    """Raised when a memory entry does not exist."""


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency validation fails."""


class ValidationError(Exception):
    """Raised when user input or payload validation fails."""


class TransitionError(Exception):
    """Raised when a memory state transition is not allowed."""


@dataclass(frozen=True, slots=True)
class LifecycleRollbackFailure:
    """Describe a failed rollback for one affected memory entry."""

    entry_id: str
    path: Path
    error: Exception


class LifecycleRecoveryError(RuntimeError):
    """Raised when a failed multi-entry lifecycle operation needs recovery diagnostics.

    Recovery can be reported as complete when reloading verifies the original entries
    despite a rollback call failure.
    """

    def __init__(
        self,
        operation_error: Exception,
        rollback_errors: tuple[LifecycleRollbackFailure, ...],
        cache_error: Exception | None,
        recovery_status: str,
    ) -> None:
        self.operation_error = operation_error
        self.rollback_errors = rollback_errors
        self.cache_error = cache_error
        self.recovery_status = recovery_status
        details = [
            f"memory lifecycle operation failed ({recovery_status} recovery): {operation_error}",
        ]
        if rollback_errors:
            details.append(
                "rollback failures: "
                + "; ".join(
                    f"entry {failure.entry_id} at {failure.path}: {failure.error}" for failure in rollback_errors
                )
            )
        if cache_error is not None:
            details.append(f"cache reload failed: {cache_error}")
        super().__init__("; ".join(details))
