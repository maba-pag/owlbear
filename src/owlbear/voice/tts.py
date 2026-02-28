"""Text-to-speech engine wrapping *pyttsx3*.

Provides :class:`TTSEngine` — an async-friendly wrapper around
:mod:`pyttsx3` that offloads the blocking ``say()`` / ``runAndWait()``
calls to a background thread via :func:`asyncio.to_thread`.

Install the optional dependency group::

    uv sync --extra voice
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyttsx3 import Engine as _PyttsxEngine  # pragma: no cover

__all__ = ["TTSEngine"]

logger = logging.getLogger(__name__)

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None  # type: ignore[assignment]


class TTSEngine:
    """Async text-to-speech engine backed by *pyttsx3*.

    The underlying pyttsx3 engine is **lazily initialised** on the first
    call to :meth:`speak`, not in ``__init__``.

    Args:
        rate: Speech rate in words per minute.
        volume: Volume level between ``0.0`` and ``1.0``.
    """

    def __init__(self, rate: int = 200, volume: float = 1.0) -> None:
        self._rate = rate
        self._volume = volume
        self._engine: _PyttsxEngine | None = None  # type: ignore[name-defined]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def speak(self, text: str) -> None:
        """Speak *text* aloud, offloading the blocking call to a thread.

        Args:
            text: The text to synthesise.

        Raises:
            ImportError: If *pyttsx3* is not installed.
        """
        engine = self._ensure_engine()
        await asyncio.to_thread(self._speak_sync, engine, text)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_engine(self) -> _PyttsxEngine:  # type: ignore[name-defined]
        """Return the cached pyttsx3 engine, creating it on first call."""
        if pyttsx3 is None:
            msg = "pyttsx3 is not installed. Install voice dependencies with: uv sync --extra voice"
            raise ImportError(msg)

        if self._engine is None:
            logger.info(
                "Initialising pyttsx3 TTS engine (rate=%d, volume=%.1f)",
                self._rate,
                self._volume,
            )
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._volume)
        return self._engine

    @staticmethod
    def _speak_sync(engine: _PyttsxEngine, text: str) -> None:  # type: ignore[name-defined]
        """Blocking helper executed inside :func:`asyncio.to_thread`."""
        engine.say(text)
        engine.runAndWait()
