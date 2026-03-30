"""Cancellation signal protocol and composition utilities."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CancelSignal(Protocol):
    """Sync cancellation signal protocol.

    Any object exposing :meth:`is_set` satisfies this protocol.
    """

    def is_set(self) -> bool:
        """Return ``True`` when cancellation has been requested."""
        ...


class LinkedCancelSignal:
    """Composite :class:`CancelSignal` that is set when *any* source is set.

    Parameters
    ----------
    *sources:
        Zero or more :class:`CancelSignal` sources to compose.
    """

    def __init__(self, *sources: CancelSignal) -> None:
        self._sources = sources

    def is_set(self) -> bool:
        """Return ``True`` if any source signal is set."""
        return any(s.is_set() for s in self._sources)
