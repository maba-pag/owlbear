"""TTS subsystem for owlbear-voice: backend factory and selection."""

from __future__ import annotations

import logging

from owlbear_voice.tts.kokoro_backend import KokoroTTSBackend
from owlbear_voice.tts.protocol import TTSBackend
from owlbear_voice.tts.pyttsx3_backend import Pyttsx3TTSBackend

__all__ = [
    "KokoroTTSBackend",
    "Pyttsx3TTSBackend",
    "TTSBackend",
    "_kokoro_available",
    "create_tts_backend",
]

logger = logging.getLogger(__name__)

try:
    import kokoro  # noqa: F401

    _kokoro_available = True
except ImportError:
    _kokoro_available = False


def create_tts_backend(voice: str, speed: float) -> TTSBackend:
    """Create and return the appropriate TTS backend.

    Selects KokoroTTSBackend when kokoro is available, otherwise falls back to
    Pyttsx3TTSBackend. On Kokoro initialisation failure the factory logs a
    warning and returns Pyttsx3TTSBackend. This function never raises.

    Args:
        voice: Voice identifier passed as-is to the selected backend.
        speed: Normalised playback speed (1.0 = normal).

    Returns:
        A TTSBackend instance ready for use.
    """
    if _kokoro_available:
        try:
            logger.debug("Selecting Kokoro TTS backend")
            return KokoroTTSBackend(voice=voice, speed=speed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Kokoro backend init failed (%s); falling back to pyttsx3", exc)
    logger.debug("Selecting pyttsx3 TTS backend")
    return Pyttsx3TTSBackend(voice=voice, speed=speed)
