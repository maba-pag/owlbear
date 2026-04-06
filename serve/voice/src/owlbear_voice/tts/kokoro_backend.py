"""Kokoro TTS backend — uses KPipeline for high-quality neural TTS."""

from __future__ import annotations

import logging

import sounddevice

__all__ = ["KokoroTTSBackend"]

logger = logging.getLogger(__name__)

try:
    from kokoro import KPipeline as _KPipeline  # type: ignore[import-untyped]
except ImportError:
    _KPipeline = None  # type: ignore[assignment]


class KokoroTTSBackend:
    """TTS backend backed by the Kokoro KPipeline.

    The KPipeline is lazily initialised on the first call to :meth:`speak`.

    Args:
        voice: Kokoro voice identifier (e.g. ``"af_heart"``).
        speed: Normalised speed where 1.0 is normal pace.
        pipeline_cls: Optional KPipeline class override (for testing).
    """

    def __init__(
        self,
        voice: str,
        speed: float,
        pipeline_cls: object = None,
    ) -> None:
        self._voice = voice
        self._speed = speed
        self._pipeline_cls = pipeline_cls
        self._pipeline: object = None

    def speak(self, text: str) -> None:
        """Speak *text* using the Kokoro pipeline (blocking).

        Args:
            text: The text to synthesise and play.
        """
        pipeline = self._ensure_pipeline()
        for result in pipeline(text, voice=self._voice, speed=self._speed):  # type: ignore[operator]
            sounddevice.play(result.audio.numpy(), 24000)  # type: ignore[union-attr]
            sounddevice.wait()

    def close(self) -> None:
        """Release the pipeline and free resources."""
        self._pipeline = None

    def _ensure_pipeline(self) -> object:
        """Return the cached KPipeline, creating it on first call."""
        if self._pipeline is None:
            cls = self._pipeline_cls or _KPipeline
            self._pipeline = cls(lang_code="a")  # type: ignore[call-arg]
        return self._pipeline
