"""Speech-to-text engine wrapping *moonshine-voice*.

Provides :class:`STTEngine` — a thin wrapper around
:class:`moonshine_voice.Transcriber` with lazy model loading and
graceful handling of the missing optional dependency.

Install the optional dependency group::

    uv sync --extra voice
"""

from __future__ import annotations

import logging

__all__ = ["STTEngine"]

logger = logging.getLogger(__name__)


class STTEngine:
    """Synchronous speech-to-text engine backed by *moonshine-voice* (batch mode).

    The underlying :class:`moonshine_voice.Transcriber` is **lazily loaded**
    on the first call to :meth:`transcribe`, not in ``__init__``.

    Audio is expected as **int16 PCM bytes** and is converted to float32
    internally (``/ 32768.0``).

    Args:
        model_arch: Moonshine ``ModelArch`` value (default:
            ``ModelArch.SMALL_STREAMING``).  Pass ``None`` to use the default.
    """

    def __init__(self, *, model_arch: int | None = None) -> None:
        self._model_arch_raw = model_arch
        self._transcriber: object | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def transcribe(self, audio: bytes, *, language: str = "en") -> str:
        """Transcribe raw int16 PCM audio bytes to text.

        Args:
            audio: Int16 PCM audio data (mono, 16 kHz expected).
            language: Language code for model resolution
                (passed to ``get_model_for_language``).

        Returns:
            Concatenated, stripped transcription text.

        Raises:
            ImportError: If *moonshine-voice* is not installed.
        """
        import numpy as np  # noqa: PLC0415

        transcriber = self._ensure_transcriber(language)
        audio_f32 = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        transcript = transcriber.transcribe_without_streaming(  # type: ignore[union-attr]
            audio_f32,
            sample_rate=16000,
        )
        return " ".join(line.text.strip() for line in transcript.lines).strip()

    def close(self) -> None:
        """Release Transcriber native resources (ONNX Runtime).

        Safe to call even when the model has not been loaded.
        """
        if self._transcriber is not None:
            self._transcriber.close()  # type: ignore[union-attr]
            self._transcriber = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_transcriber(self, language: str = "en") -> object:
        """Return the cached Transcriber, creating it on first call."""
        if self._transcriber is None:
            try:
                from moonshine_voice import (  # noqa: PLC0415
                    ModelArch,
                    Transcriber,
                    get_model_for_language,
                )
            except ImportError:
                msg = (
                    "moonshine-voice is not installed. "
                    "Install voice dependencies with: uv sync --extra voice"
                )
                raise ImportError(msg) from None

            arch = (
                self._model_arch_raw
                if self._model_arch_raw is not None
                else ModelArch.SMALL_STREAMING
            )
            model_path = get_model_for_language(language, model_arch=arch)
            logger.info(
                "Loading Moonshine model (arch=%s, language=%s, path=%s)",
                arch,
                language,
                model_path,
            )
            self._transcriber = Transcriber(model_path, model_arch=arch)
        return self._transcriber
