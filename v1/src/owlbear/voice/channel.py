"""Voice channel adapter — microphone + speaker I/O for OwlBear.

Provides :class:`VoiceChannel`, an implementation of
:class:`~owlbear.channels.base.ChannelPlugin` that records audio via
*sounddevice*, transcribes it with :class:`~owlbear.voice.stt.STTEngine`,
speaks responses through :class:`~owlbear.voice.tts.TTSEngine`, and supports
open-ended brainstorming sessions via
:class:`~owlbear.voice.streaming_stt.StreamingSTT`.

Install the optional dependency group::

    uv sync --extra voice
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from owlbear.channels.base import ChannelPlugin
from owlbear.voice.stt import STTEngine
from owlbear.voice.tts import TTSEngine

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["VoiceChannel"]

logger = logging.getLogger(__name__)

# Default recording duration (seconds) when called via receive().
DEFAULT_RECORD_DURATION: float = 5.0

# Default maximum brainstorm session duration (seconds).
DEFAULT_BRAINSTORM_DURATION: float = 120.0

# Default idle timeout — session ends if no speech for this many seconds.
DEFAULT_IDLE_TIMEOUT: float = 10.0

# Module-level sounddevice import with graceful fallback.
try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None  # type: ignore[assignment]


class VoiceChannel(ChannelPlugin):
    """ChannelPlugin that uses microphone input and speaker output.

    Supports two modes:

    * **Quick mode** (:meth:`receive`): fixed-duration recording via
      *sounddevice*, batch transcription via :class:`STTEngine`.
    * **Brainstorm mode** (:meth:`brainstorm`): open-ended streaming
      session via :class:`StreamingSTT` with idle/duration timeouts.

    All components are injectable for testability.  When *None* is passed
    the channel creates sensible defaults (lazily for StreamingSTT).

    Args:
        stt: Speech-to-text engine (default: :class:`STTEngine`).
        tts: Text-to-speech engine (default: :class:`TTSEngine`).
        streaming_stt: Streaming STT engine for brainstorm mode.
            Created lazily on first :meth:`brainstorm` call if *None*.
        record_duration: Seconds to record per :meth:`receive` call.
    """

    def __init__(
        self,
        stt: STTEngine | None = None,
        tts: TTSEngine | None = None,
        streaming_stt: object | None = None,
        record_duration: float = DEFAULT_RECORD_DURATION,
    ) -> None:
        self._stt = stt if stt is not None else STTEngine()
        self._tts = tts if tts is not None else TTSEngine()
        self._streaming_stt = streaming_stt
        self._record_duration = record_duration
        self._stop_event: asyncio.Event | None = None

    # ------------------------------------------------------------------
    # ChannelPlugin interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Short identifier for this channel."""
        return "voice"

    async def send(self, message: str) -> None:
        """Speak *message* aloud via TTS."""
        await self._tts.speak(message)

    async def receive(self, *, prompt: str | None = None) -> str | None:
        """Record audio, transcribe, and return the text.

        Uses *sounddevice* for microphone capture.  If *prompt* is provided
        it is spoken via TTS before recording begins.  Returns ``None`` when
        no speech is detected (empty or whitespace-only transcription).
        """
        if prompt is not None:
            await self._tts.speak(prompt)

        audio = await self._record_sounddevice(self._record_duration)
        text = self._stt.transcribe(audio)

        if not text or not text.strip():
            return None
        return text

    # ------------------------------------------------------------------
    # Brainstorm mode
    # ------------------------------------------------------------------

    async def brainstorm(
        self,
        duration: float = DEFAULT_BRAINSTORM_DURATION,
        on_update: Callable[[str], None] | None = None,
        idle_timeout: float = DEFAULT_IDLE_TIMEOUT,
    ) -> str:
        """Open-ended brainstorm transcription session.

        Delegates to :class:`StreamingSTT` for mic capture, VAD, and
        streaming transcription.

        Args:
            duration: Maximum session length in seconds.
            on_update: Optional callback receiving partial text on each
                ``LineTextChanged`` event.
            idle_timeout: Seconds of silence (no completed lines) before
                the session ends automatically.

        Returns:
            Full transcript (all completed lines joined).
        """
        stt = self._ensure_streaming_stt()
        loop = asyncio.get_running_loop()

        activity_event = asyncio.Event()
        self._stop_event = asyncio.Event()

        def _on_text_update(text: str, _line_idx: int) -> None:
            if on_update is not None:
                on_update(text)

        def _on_line_complete(_text: str, _line_idx: int) -> None:
            activity_event.set()

        stt.start(  # type: ignore[union-attr]
            on_text_update=_on_text_update,
            on_line_complete=_on_line_complete,
            loop=loop,
        )

        try:
            await self._monitor_session(
                duration,
                idle_timeout,
                activity_event,
            )
        finally:
            transcript: str = stt.stop()  # type: ignore[union-attr]
            self._stop_event = None

        return transcript

    def stop(self) -> None:
        """Signal a running brainstorm session to end.

        Safe to call when no brainstorm session is active (no-op).
        """
        if self._stop_event is not None:
            self._stop_event.set()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _record_sounddevice(self, duration: float) -> bytes:
        """Record audio using *sounddevice*, offloaded to a thread."""
        if sd is None:
            msg = (
                "sounddevice is not installed. "
                "Install voice dependencies with: uv sync --extra voice"
            )
            raise ImportError(msg)

        frames = int(16000 * duration)
        recording = sd.rec(frames, samplerate=16000, channels=1, dtype="int16")
        sd.wait()
        return recording.tobytes()

    def _ensure_streaming_stt(self) -> object:
        """Return the StreamingSTT instance, creating it lazily if needed."""
        if self._streaming_stt is None:
            from owlbear.voice.streaming_stt import StreamingSTT  # noqa: PLC0415

            self._streaming_stt = StreamingSTT()
        return self._streaming_stt

    async def _monitor_session(
        self,
        duration: float,
        idle_timeout: float,
        activity: asyncio.Event,
    ) -> None:
        """Wait until duration expires, idle timeout fires, or stop() called."""
        assert self._stop_event is not None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + duration

        while not self._stop_event.is_set():
            remaining = deadline - loop.time()
            if remaining <= 0:
                break

            timeout = min(idle_timeout, remaining)
            activity.clear()

            wait_activity = asyncio.ensure_future(activity.wait())
            wait_stop = asyncio.ensure_future(self._stop_event.wait())

            done, pending = await asyncio.wait(
                {wait_activity, wait_stop},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if self._stop_event.is_set():
                break
            if not done:
                # Timeout with no activity → idle timeout or duration expired
                break
            # Activity happened → continue monitoring
