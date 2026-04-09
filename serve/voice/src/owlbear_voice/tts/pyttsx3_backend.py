"""pyttsx3 TTS backend — offline fallback using the system TTS engine."""

from __future__ import annotations

import logging

import pyttsx3

__all__ = ["Pyttsx3TTSBackend"]

logger = logging.getLogger(__name__)


class Pyttsx3TTSBackend:
    """TTS backend backed by pyttsx3.

    The pyttsx3 engine is lazily initialised on the first call to
    :meth:`speak`, mirroring the v1 TTSEngine lazy-init pattern.

    Args:
        voice: Voice name substring used to select from available voices.
        speed: Normalised speed; mapped to pyttsx3 rate as ``int(speed * 200)``.
    """

    def __init__(self, voice: str, speed: float) -> None:
        self._voice = voice
        self._speed = speed
        self._engine: object = None

    def speak(self, text: str) -> None:
        """Speak *text* using the pyttsx3 engine (blocking).

        Args:
            text: The text to synthesise and play.
        """
        engine = self._ensure_engine()
        engine.say(text)  # type: ignore[union-attr]
        engine.runAndWait()  # type: ignore[union-attr]

    def close(self) -> None:
        """Release engine resources."""
        self._engine = None

    def _ensure_engine(self) -> object:
        """Return the cached pyttsx3 engine, creating it on first call."""
        if self._engine is None:
            engine = pyttsx3.init()
            engine.setProperty("rate", int(self._speed * 200))
            self._set_voice(engine)
            self._engine = engine
        return self._engine

    def _set_voice(self, engine: object) -> None:  # type: ignore[override]
        """Select the best matching voice by substring on the engine."""
        voices = engine.getProperty("voices")  # type: ignore[union-attr]
        needle = self._voice.upper()
        for voice in voices:
            if needle in voice.id.upper():
                engine.setProperty("voice", voice.id)  # type: ignore[union-attr]
                return
        # No match found — keep the engine default without raising.
