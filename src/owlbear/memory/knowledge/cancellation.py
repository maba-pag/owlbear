"""Cancellation signal protocol and adapters for knowledge pipelines."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CancelSignal(Protocol):
    """Minimal cooperative cancellation signal.

    Implementations expose only :meth:`is_set`, which allows knowledge-layer
    code to stay decoupled from concrete runtime event types.
    """

    def is_set(self) -> bool:
        """Return ``True`` when cancellation has been requested."""


class LinkedCancelSignal:
    """Compose multiple cancel signals into one live-linked signal."""

    def __init__(self, *sources: CancelSignal) -> None:
        self._sources = sources

    def is_set(self) -> bool:
        """Return ``True`` when any linked source reports cancellation."""
        return any(source.is_set() for source in self._sources)
