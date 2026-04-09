"""Speech-to-text runner using Moonshine streaming transcription.

Wraps MicTranscriber for live voice-to-text with VAD, serializing
transcript events to NDJSON on stdout.
"""

from __future__ import annotations

import json
import sys
import threading
from typing import Any

# ---------------------------------------------------------------------------
# Optional base class — avoids hard import at module load time
# ---------------------------------------------------------------------------

try:
    from moonshine_voice.transcriber import TranscriptEventListener as _BaseListener
except ImportError:
    _BaseListener = object  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Listener
# ---------------------------------------------------------------------------


class TranscriptJsonListener(_BaseListener):  # type: ignore[misc, valid-type]
    """Serialize transcript events to NDJSON on stdout.

    Methods accept plain ``(line_idx, text)`` arguments so they can be unit-
    tested directly without Moonshine event objects.

    The provided ``lock`` guards every stdout write from concurrent audio-
    thread callbacks.
    """

    def __init__(self, lock: threading.Lock) -> None:
        self._lock = lock

    def _write(self, data: dict[str, Any]) -> None:
        line = (json.dumps(data, separators=(",", ":")) + "\n").encode()
        with self._lock:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()

    def emit(self, data: dict[str, Any]) -> None:
        """Public wrapper for _write — used by SttRunner to emit status events."""
        self._write(data)

    def on_line_started(self, line_idx: int, text: str = "") -> None:  # noqa: ARG002
        """Emit a partial-type message when a new line begins."""
        self._write({"type": "partial", "text": "", "line_idx": line_idx})

    def on_text_changed(self, line_idx: int, text: str) -> None:
        """Emit a partial-type message with current in-progress text."""
        self._write({"type": "partial", "text": text, "line_idx": line_idx})

    def on_line_completed(self, line_idx: int, text: str) -> None:
        """Emit a final transcript-type message when a line is complete."""
        self._write({"type": "transcript", "text": text, "line_idx": line_idx, "final": True})

    def on_error(self, exc: Exception) -> None:
        """Log error detail to stderr and emit an error-type NDJSON message."""
        sys.stderr.write(f"STT error: {exc}\n")
        self._write({"type": "error", "code": "stt_error", "message": str(exc)})

    # -----------------------------------------------------------------
    # Moonshine TranscriptEventListener bridge (called in production)
    # These forward real event objects to the plain-arg methods above.
    # -----------------------------------------------------------------

    def on_line_text_changed(self, event: Any) -> None:  # noqa: ANN401
        """Bridge from Moonshine event to on_text_changed."""
        self.on_text_changed(event.line.line_id, event.line.text)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class SttRunner:
    """STT runner with lazy MicTranscriber initialization.

    MicTranscriber (and the underlying ONNX model) is not created until
    the first call to start(), keeping __init__ fast.

    Args:
        model_arch: Moonshine ModelArch — defaults to SMALL_STREAMING at
            first start() if None.
        language: Language code for model selection (default ``"en"``).
        update_interval: Seconds between transcription updates (default 0.5).
    """

    def __init__(
        self,
        *,
        model_arch: object | None = None,
        language: str = "en",
        update_interval: float = 0.5,
    ) -> None:
        self._model_arch = model_arch
        self._language = language
        self._update_interval = update_interval
        self._lock = threading.Lock()
        self._listener = TranscriptJsonListener(self._lock)
        self._transcriber: object | None = None

    def start(self) -> None:
        """Start STT. Creates MicTranscriber lazily on the first call."""
        if self._transcriber is None:
            self._transcriber = self._create_transcriber()
            self._listener.emit({"type": "status", "state": "ready"})
        self._transcriber.start()  # type: ignore[union-attr]

    def _create_transcriber(self) -> object:
        """Instantiate and configure MicTranscriber.

        Raises:
            ImportError: If moonshine-voice is not installed.
        """
        try:
            import moonshine_voice  # noqa: PLC0415
        except ImportError as exc:
            msg = "moonshine-voice is required for STT. Install it with: pip install moonshine-voice"
            raise ImportError(msg) from exc

        model_arch = self._model_arch if self._model_arch is not None else moonshine_voice.ModelArch.SMALL_STREAMING
        model_path = moonshine_voice.get_model_for_language(self._language, model_arch)
        transcriber = moonshine_voice.MicTranscriber(
            model_path, model_arch=model_arch, update_interval=self._update_interval
        )
        transcriber.add_listener(self._listener)
        return transcriber

    def stop(self) -> None:
        """Stop transcription. Triggers LineCompleted for any active line.

        Raises:
            RuntimeError: If stop() is called before start().
        """
        if self._transcriber is None:
            msg = "stop() called before start()"
            raise RuntimeError(msg)
        self._transcriber.stop()  # type: ignore[union-attr]

    def close(self) -> None:
        """Release MicTranscriber resources. Idempotent."""
        if self._transcriber is not None:
            self._transcriber.close()  # type: ignore[union-attr]
            self._transcriber = None
