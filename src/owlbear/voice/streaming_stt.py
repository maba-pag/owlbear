"""Streaming speech-to-text engine wrapping *moonshine-voice* ``MicTranscriber``.

Provides :class:`StreamingSTT` — a thin wrapper around
:class:`moonshine_voice.MicTranscriber` for open-ended brainstorming sessions
with live partial-text callbacks and VAD-based line segmentation.

Thread safety: ``MicTranscriber`` fires callbacks on the ``sounddevice`` audio
thread.  When an *asyncio* event loop is provided via the ``loop`` parameter,
callbacks are bridged using :meth:`asyncio.AbstractEventLoop.call_soon_threadsafe`.

Install the optional dependency group::

    uv sync --extra voice
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Callable

__all__ = ["StreamingSTT"]

logger = logging.getLogger(__name__)


class StreamingSTT:
    """Streaming speech-to-text engine backed by *moonshine-voice* ``MicTranscriber``.

    The underlying ``MicTranscriber`` is **lazily created** on the first call
    to :meth:`start`, not in ``__init__``.

    Args:
        model_arch: Moonshine ``ModelArch`` value (default:
            ``ModelArch.SMALL_STREAMING``).  Pass ``None`` to use the default.
        update_interval: Seconds between transcription updates (default: ``0.5``).
        language: Language code for model resolution (default: ``"en"``).
    """

    def __init__(
        self,
        *,
        model_arch: int | None = None,
        update_interval: float = 0.5,
        language: str = "en",
    ) -> None:
        self._model_arch_raw = model_arch
        self._update_interval = update_interval
        self._language = language
        self._mic: object | None = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        on_text_update: Callable[[str, int], None] | None = None,
        on_line_complete: Callable[[str, int], None] | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Begin mic capture and streaming transcription.

        Args:
            on_text_update: Called on ``LineTextChanged`` events with
                ``(text, line_idx)``.  Fires on the audio thread unless
                *loop* is provided.
            on_line_complete: Called on ``LineCompleted`` events with
                ``(text, line_idx)``.  Fires on the audio thread unless
                *loop* is provided.
            loop: Optional asyncio event loop.  When provided, callbacks are
                bridged to this loop via ``call_soon_threadsafe``.

        Raises:
            ImportError: If *moonshine-voice* is not installed.
            RuntimeError: If streaming is already running.
        """
        if self._running:
            msg = "Streaming is already running — call stop() first"
            raise RuntimeError(msg)

        mic = self._create_mic_transcriber()

        # Wire callbacks, optionally bridging to asyncio loop.
        if on_text_update is not None:
            mic.on_text_update = (  # type: ignore[union-attr]
                self._bridge(on_text_update, loop) if loop else on_text_update
            )
        else:
            mic.on_text_update = None  # type: ignore[union-attr]

        if on_line_complete is not None:
            mic.on_line_complete = (  # type: ignore[union-attr]
                self._bridge(on_line_complete, loop) if loop else on_line_complete
            )
        else:
            mic.on_line_complete = None  # type: ignore[union-attr]

        mic.start()  # type: ignore[union-attr]
        self._mic = mic
        self._running = True
        logger.info("Streaming STT started (language=%s)", self._language)

    def stop(self) -> str:
        """Stop streaming and return the full transcript as a string.

        Returns:
            Space-joined text of all completed lines.

        Raises:
            RuntimeError: If streaming has not been started.
        """
        if not self._running or self._mic is None:
            msg = "Streaming is not started — call start() first"
            raise RuntimeError(msg)

        transcript = self._mic.stop()  # type: ignore[union-attr]
        self._running = False
        full_text = " ".join(line.text for line in transcript.lines).strip()
        logger.info("Streaming STT stopped — %d lines captured", len(transcript.lines))
        return full_text

    def close(self) -> None:
        """Release MicTranscriber resources.

        Safe to call multiple times (idempotent) and before :meth:`start`.
        """
        if self._mic is not None:
            self._mic.close()  # type: ignore[union-attr]
            self._mic = None
        self._running = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_mic_transcriber(self) -> object:
        """Create and return a new ``MicTranscriber`` instance."""
        try:
            from moonshine_voice import (  # noqa: PLC0415
                MicTranscriber,
                ModelArch,
                get_model_for_language,
            )
        except ImportError:
            msg = (
                "moonshine-voice is not installed. "
                "Install voice dependencies with: uv sync --extra voice"
            )
            raise ImportError(msg) from None

        arch = (
            self._model_arch_raw if self._model_arch_raw is not None else ModelArch.SMALL_STREAMING
        )
        model_path = get_model_for_language(self._language, model_arch=arch)
        logger.info(
            "Creating MicTranscriber (arch=%s, language=%s, path=%s)",
            arch,
            self._language,
            model_path,
        )
        return MicTranscriber(
            model_path,
            model_arch=arch,
            update_interval=self._update_interval,
        )

    @staticmethod
    def _bridge(
        callback: Callable[[str, int], None],
        loop: asyncio.AbstractEventLoop,
    ) -> Callable[[str, int], None]:
        """Wrap *callback* so it is dispatched via ``call_soon_threadsafe``."""

        def _wrapper(text: str, line_idx: int) -> None:
            loop.call_soon_threadsafe(callback, text, line_idx)

        return _wrapper
