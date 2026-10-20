"""Domain exception types for decision files."""

from __future__ import annotations


class DecisionError(Exception):
    """Base of every refusal the decisions core raises."""


class DecisionFileError(DecisionError, ValueError):
    """A decision file cannot be read as a valid decision."""

    def __init__(self, message: str, locations: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.locations = locations


class ConcurrencyError(DecisionError):
    """The file's current revision is not the one the writer expected."""


class ImmutableError(DecisionError):
    """A write would edit the accepted wording of an in-force decision."""
