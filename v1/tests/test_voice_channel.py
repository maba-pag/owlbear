"""Tests for owlbear.voice.channel — VoiceChannel (Tasks #95, #244).

Covers both quick-mode receive (sounddevice) and brainstorm mode
(StreamingSTT delegation with idle/duration timeout and manual stop).
"""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.channels.base import ChannelPlugin
from owlbear.voice.channel import (
    DEFAULT_BRAINSTORM_DURATION,
    DEFAULT_IDLE_TIMEOUT,
    DEFAULT_RECORD_DURATION,
    VoiceChannel,
)

# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestVoiceChannelProtocol:
    """VoiceChannel must satisfy the ChannelPlugin protocol."""

    def test_isinstance_channel_plugin(self) -> None:
        channel = VoiceChannel()
        assert isinstance(channel, ChannelPlugin)


# ---------------------------------------------------------------------------
# Name property
# ---------------------------------------------------------------------------


class TestVoiceChannelName:
    """VoiceChannel.name returns 'voice'."""

    def test_name_is_voice(self) -> None:
        assert VoiceChannel().name == "voice"


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestVoiceChannelConstants:
    """Default constants are exposed at module level."""

    def test_default_record_duration(self) -> None:
        assert DEFAULT_RECORD_DURATION == 5.0

    def test_default_brainstorm_duration(self) -> None:
        assert DEFAULT_BRAINSTORM_DURATION == 120.0

    def test_default_idle_timeout(self) -> None:
        assert DEFAULT_IDLE_TIMEOUT == 10.0


# ---------------------------------------------------------------------------
# Constructor — dependency injection
# ---------------------------------------------------------------------------


class TestVoiceChannelConstructor:
    """Constructor accepts optional stt, tts, streaming_stt."""

    def test_defaults_to_none_streaming_stt(self) -> None:
        ch = VoiceChannel()
        assert ch._streaming_stt is None

    def test_injected_stt_and_tts(self) -> None:
        stt = MagicMock()
        tts = MagicMock()
        ch = VoiceChannel(stt=stt, tts=tts)
        assert ch._stt is stt
        assert ch._tts is tts

    def test_injected_streaming_stt(self) -> None:
        streaming = MagicMock()
        ch = VoiceChannel(streaming_stt=streaming)
        assert ch._streaming_stt is streaming

    def test_custom_record_duration(self) -> None:
        ch = VoiceChannel(record_duration=10.0)
        assert ch._record_duration == 10.0

    def test_no_recorder_parameter(self) -> None:
        """AudioRecorder parameter was removed — constructor rejects it."""
        with pytest.raises(TypeError):
            VoiceChannel(recorder=MagicMock())  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# send() — delegates to TTSEngine.speak
# ---------------------------------------------------------------------------


class TestVoiceChannelSend:
    """send() delegates to TTSEngine.speak()."""

    @pytest.mark.asyncio
    async def test_send_delegates_to_speak(self) -> None:
        tts = MagicMock()
        tts.speak = AsyncMock()
        ch = VoiceChannel(tts=tts)

        await ch.send("hello world")

        tts.speak.assert_awaited_once_with("hello world")

    @pytest.mark.asyncio
    async def test_send_multiple_messages(self) -> None:
        tts = MagicMock()
        tts.speak = AsyncMock()
        ch = VoiceChannel(tts=tts)

        await ch.send("first")
        await ch.send("second")

        assert tts.speak.await_count == 2


# ---------------------------------------------------------------------------
# receive() — quick mode using sounddevice
# ---------------------------------------------------------------------------


class TestVoiceChannelReceive:
    """receive() records audio via sounddevice, transcribes via STTEngine."""

    @pytest.mark.asyncio
    @patch("owlbear.voice.channel.sd")
    async def test_receive_records_via_sounddevice(self, mock_sd: MagicMock) -> None:
        mock_recording = MagicMock()
        mock_recording.tobytes.return_value = b"\x00\x01"
        mock_sd.rec.return_value = mock_recording

        stt = MagicMock()
        stt.transcribe.return_value = "hello from voice"
        ch = VoiceChannel(stt=stt, record_duration=5.0)

        result = await ch.receive()

        mock_sd.rec.assert_called_once_with(
            80000,
            samplerate=16000,
            channels=1,
            dtype="int16",
        )
        mock_sd.wait.assert_called_once()
        stt.transcribe.assert_called_once_with(b"\x00\x01")
        assert result == "hello from voice"

    @pytest.mark.asyncio
    @patch("owlbear.voice.channel.sd")
    async def test_receive_returns_none_on_empty_transcription(
        self,
        mock_sd: MagicMock,
    ) -> None:
        mock_recording = MagicMock()
        mock_recording.tobytes.return_value = b"\x00"
        mock_sd.rec.return_value = mock_recording

        stt = MagicMock()
        stt.transcribe.return_value = ""
        ch = VoiceChannel(stt=stt)

        assert await ch.receive() is None

    @pytest.mark.asyncio
    @patch("owlbear.voice.channel.sd")
    async def test_receive_returns_none_on_whitespace_only(
        self,
        mock_sd: MagicMock,
    ) -> None:
        mock_recording = MagicMock()
        mock_recording.tobytes.return_value = b"\x00"
        mock_sd.rec.return_value = mock_recording

        stt = MagicMock()
        stt.transcribe.return_value = "   "
        ch = VoiceChannel(stt=stt)

        assert await ch.receive() is None


# ---------------------------------------------------------------------------
# receive(prompt=...) — speaks prompt before recording
# ---------------------------------------------------------------------------


class TestVoiceChannelReceiveWithPrompt:
    """If prompt is provided, speaks it via TTS before recording."""

    @pytest.mark.asyncio
    @patch("owlbear.voice.channel.sd")
    async def test_prompt_spoken_before_recording(self, mock_sd: MagicMock) -> None:
        mock_recording = MagicMock()
        mock_recording.tobytes.return_value = b"\x00"
        mock_sd.rec.return_value = mock_recording

        tts = MagicMock()
        tts.speak = AsyncMock()
        stt = MagicMock()
        stt.transcribe.return_value = "user response"
        ch = VoiceChannel(stt=stt, tts=tts)

        result = await ch.receive(prompt="Say something")

        tts.speak.assert_awaited_once_with("Say something")
        assert result == "user response"

    @pytest.mark.asyncio
    @patch("owlbear.voice.channel.sd")
    async def test_no_prompt_skips_tts(self, mock_sd: MagicMock) -> None:
        mock_recording = MagicMock()
        mock_recording.tobytes.return_value = b"\x00"
        mock_sd.rec.return_value = mock_recording

        tts = MagicMock()
        tts.speak = AsyncMock()
        stt = MagicMock()
        stt.transcribe.return_value = "answer"
        ch = VoiceChannel(stt=stt, tts=tts)

        await ch.receive()

        tts.speak.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("owlbear.voice.channel.sd")
    async def test_none_prompt_skips_tts(self, mock_sd: MagicMock) -> None:
        mock_recording = MagicMock()
        mock_recording.tobytes.return_value = b"\x00"
        mock_sd.rec.return_value = mock_recording

        tts = MagicMock()
        tts.speak = AsyncMock()
        stt = MagicMock()
        stt.transcribe.return_value = "answer"
        ch = VoiceChannel(stt=stt, tts=tts)

        await ch.receive(prompt=None)

        tts.speak.assert_not_awaited()


# ---------------------------------------------------------------------------
# receive() — ImportError when sounddevice not installed
# ---------------------------------------------------------------------------


class TestVoiceChannelSounddeviceImport:
    """receive() raises ImportError when sounddevice is not available."""

    @pytest.mark.asyncio
    @patch("owlbear.voice.channel.sd", None)
    async def test_raises_import_error_without_sounddevice(self) -> None:
        ch = VoiceChannel(stt=MagicMock())
        with pytest.raises(ImportError, match="sounddevice"):
            await ch.receive()


# ---------------------------------------------------------------------------
# brainstorm() — streaming mode basics
# ---------------------------------------------------------------------------


class TestVoiceChannelBrainstorm:
    """brainstorm() delegates to StreamingSTT for open-ended sessions."""

    @pytest.mark.asyncio
    async def test_brainstorm_starts_and_stops_streaming(self) -> None:
        """brainstorm() starts StreamingSTT and stops it, returning transcript."""
        streaming = MagicMock()
        streaming.stop.return_value = "hello world transcript"

        ch = VoiceChannel(streaming_stt=streaming)
        # Short idle timeout → session ends immediately (no speech)
        result = await ch.brainstorm(duration=5.0, idle_timeout=0.05)

        streaming.start.assert_called_once()
        streaming.stop.assert_called_once()
        assert result == "hello world transcript"

    @pytest.mark.asyncio
    async def test_brainstorm_returns_full_transcript(self) -> None:
        streaming = MagicMock()
        streaming.stop.return_value = "complete transcript here"

        ch = VoiceChannel(streaming_stt=streaming)
        result = await ch.brainstorm(duration=5.0, idle_timeout=0.05)

        assert result == "complete transcript here"


# ---------------------------------------------------------------------------
# brainstorm() — on_update callback
# ---------------------------------------------------------------------------


class TestVoiceChannelBrainstormCallback:
    """on_update callback receives partial text from StreamingSTT updates."""

    @pytest.mark.asyncio
    async def test_on_update_callback_wired_to_text_update(self) -> None:
        streaming = MagicMock()
        streaming.stop.return_value = "final"

        updates: list[str] = []
        captured: dict[str, object] = {}

        def fake_start(**kwargs: object) -> None:
            captured["on_text_update"] = kwargs.get("on_text_update")
            captured["on_line_complete"] = kwargs.get("on_line_complete")

        streaming.start.side_effect = fake_start

        ch = VoiceChannel(streaming_stt=streaming)
        result = await ch.brainstorm(
            on_update=updates.append,
            duration=5.0,
            idle_timeout=0.05,
        )

        # Verify callback was wired
        assert captured.get("on_text_update") is not None
        # Fire it to verify it reaches on_update
        captured["on_text_update"]("partial text", 0)  # type: ignore[operator]
        assert updates == ["partial text"]
        assert result == "final"

    @pytest.mark.asyncio
    async def test_on_update_none_is_safe(self) -> None:
        """brainstorm with on_update=None does not crash."""
        streaming = MagicMock()
        streaming.stop.return_value = "ok"

        ch = VoiceChannel(streaming_stt=streaming)
        result = await ch.brainstorm(on_update=None, duration=5.0, idle_timeout=0.05)

        assert result == "ok"


# ---------------------------------------------------------------------------
# brainstorm() — session end conditions
# ---------------------------------------------------------------------------


class TestVoiceChannelBrainstormSessionEnd:
    """Session ends on idle timeout, duration timeout, or manual stop."""

    @pytest.mark.asyncio
    async def test_idle_timeout_ends_session(self) -> None:
        """No speech activity → idle timeout → session ends."""
        streaming = MagicMock()
        streaming.stop.return_value = "idle ended"

        ch = VoiceChannel(streaming_stt=streaming)
        result = await ch.brainstorm(duration=120.0, idle_timeout=0.05)

        assert result == "idle ended"

    @pytest.mark.asyncio
    async def test_duration_timeout_ends_session(self) -> None:
        """Duration expires even when there is speech activity."""
        streaming = MagicMock()
        streaming.stop.return_value = "duration ended"

        captured: dict[str, object] = {}

        def fake_start(**kwargs: object) -> None:
            captured["on_line_complete"] = kwargs.get("on_line_complete")

        streaming.start.side_effect = fake_start

        ch = VoiceChannel(streaming_stt=streaming)

        async def keep_active() -> None:
            """Simulate ongoing speech by firing on_line_complete."""
            await asyncio.sleep(0.01)
            for _ in range(20):
                cb = captured.get("on_line_complete")
                if cb is not None:
                    cb("text", 0)  # type: ignore[operator]
                await asyncio.sleep(0.02)

        task = asyncio.create_task(keep_active())
        try:
            result = await ch.brainstorm(duration=0.15, idle_timeout=0.5)
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        assert result == "duration ended"

    @pytest.mark.asyncio
    async def test_manual_stop_ends_session(self) -> None:
        """Calling stop() ends the brainstorm session promptly."""
        streaming = MagicMock()
        streaming.stop.return_value = "stopped early"

        ch = VoiceChannel(streaming_stt=streaming)

        async def stop_after_delay() -> None:
            await asyncio.sleep(0.05)
            ch.stop()

        task = asyncio.create_task(
            ch.brainstorm(duration=120.0, idle_timeout=120.0),
        )
        stop_task = asyncio.create_task(stop_after_delay())

        result = await task
        assert result == "stopped early"
        stop_task.cancel()

    @pytest.mark.asyncio
    async def test_activity_resets_idle_timer(self) -> None:
        """Line completions reset idle timer — session survives past idle_timeout."""
        streaming = MagicMock()
        streaming.stop.return_value = "activity kept it alive"

        captured: dict[str, object] = {}

        def fake_start(**kwargs: object) -> None:
            captured["on_line_complete"] = kwargs.get("on_line_complete")

        streaming.start.side_effect = fake_start

        ch = VoiceChannel(streaming_stt=streaming)

        async def pulse_activity() -> None:
            """Fire on_line_complete faster than idle_timeout."""
            await asyncio.sleep(0.01)
            for _ in range(8):
                cb = captured.get("on_line_complete")
                if cb is not None:
                    cb("word", 0)  # type: ignore[operator]
                await asyncio.sleep(0.02)  # 20ms between pulses

        task = asyncio.create_task(pulse_activity())
        try:
            result = await ch.brainstorm(
                duration=0.25,
                idle_timeout=0.05,
            )
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # Session must have survived past the 50ms idle_timeout
        # because activity was pulsed every 20ms
        assert result == "activity kept it alive"


# ---------------------------------------------------------------------------
# brainstorm() — lazy StreamingSTT creation
# ---------------------------------------------------------------------------


class TestVoiceChannelStreamingSTTLazy:
    """StreamingSTT is created lazily when not injected."""

    @pytest.mark.asyncio
    async def test_lazy_creation(self) -> None:
        ch = VoiceChannel()
        assert ch._streaming_stt is None

        with patch("owlbear.voice.streaming_stt.StreamingSTT") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.stop.return_value = "lazy transcript"
            mock_cls.return_value = mock_instance

            result = await ch.brainstorm(duration=5.0, idle_timeout=0.05)

        mock_cls.assert_called_once()
        assert result == "lazy transcript"


# ---------------------------------------------------------------------------
# stop() — safe when no brainstorm is running
# ---------------------------------------------------------------------------


class TestVoiceChannelStop:
    """stop() is safe to call at any time."""

    def test_stop_without_brainstorm_is_noop(self) -> None:
        ch = VoiceChannel()
        ch.stop()  # Should not raise
