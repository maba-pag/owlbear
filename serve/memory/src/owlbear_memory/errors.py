"""Domain exception types for memory primitives."""

from __future__ import annotations


class NotFoundError(Exception):
    """Raised when a memory entry does not exist."""


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency validation fails."""


class ValidationError(Exception):
    """Raised when user input or payload validation fails."""


class TransitionError(Exception):
    """Raised when a memory state transition is not allowed."""


class LifecycleRecoveryError(RuntimeError):
    """Raised when a failed multi-entry lifecycle operation cannot be fully restored."""

    def __init__(
        self,
        operation_error: Exception,
        rollback_errors: tuple[Exception, ...],
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
            details.append("rollback failures: " + "; ".join(str(error) for error in rollback_errors))
        if cache_error is not None:
            details.append(f"cache reload failed: {cache_error}")
        super().__init__("; ".join(details))
