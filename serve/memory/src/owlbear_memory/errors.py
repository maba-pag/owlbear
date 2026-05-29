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
