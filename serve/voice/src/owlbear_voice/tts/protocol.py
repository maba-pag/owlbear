"""TTSBackend protocol — common interface for all TTS backends."""

from __future__ import annotations

from typing import Protocol

__all__ = ["TTSBackend"]


class TTSBackend(Protocol):
    """Protocol for TTS backend implementations.

    Both speak() and close() are blocking operations.
    """

    def speak(self, text: str) -> None:
        """Speak *text* aloud (blocking until audio finishes)."""
        ...

    def close(self) -> None:
        """Release any resources held by the backend."""
        ...
