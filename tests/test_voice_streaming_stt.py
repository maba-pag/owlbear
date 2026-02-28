"""Tests for StreamingSTT — Moonshine streaming mode for brainstorming (Task #243).

All tests mock ``moonshine_voice`` so the actual package is never required.
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — build a fake ``moonshine_voice`` module with MicTranscriber
# ---------------------------------------------------------------------------


def _make_fake_moonshine() -> ModuleType:
    """Return a stub ``moonshine_voice`` module with mock MicTranscriber etc."""
    mod = ModuleType("moonshine_voice")

    # ModelArch enum mock
    model_arch = MagicMock(name="ModelArch")
    model_arch.SMALL_STREAMING = 4
    model_arch.TINY_STREAMING = 2
    mod.ModelArch = model_arch  # type: ignore[attr-defined]

    # get_model_for_language mock
    mod.get_model_for_language = MagicMock(  # type: ignore[attr-defined]
        return_value="/models/moonshine-small-streaming-en",
    )

    # MicTranscriber class mock
    mock_mic_cls = MagicMock(name="MicTranscriber")
    line1 = MagicMock()
    line1.text = "Hello world"
    line2 = MagicMock()
    line2.text = "How are you"
    transcript = MagicMock()
    transcript.lines = [line1, line2]
    mock_mic_cls.return_value.stop.return_value = transcript
    mod.MicTranscriber = mock_mic_cls  # type: ignore[attr-defined]

    # Transcriber class mock (needed for close() on the underlying transcriber)
    mock_transcriber_cls = MagicMock(name="Transcriber")
    mod.Transcriber = mock_transcriber_cls  # type: ignore[attr-defined]

    return mod


def _install_fake_moonshine() -> ModuleType:
    """Insert fake moonshine_voice into sys.modules and return it."""
    mod = _make_fake_moonshine()
    sys.modules["moonshine_voice"] = mod
    return mod


# ---------------------------------------------------------------------------
# Tests — ImportError guard
# ---------------------------------------------------------------------------


class TestStreamingSTTImportGuard:
    """StreamingSTT.start() raises ImportError when moonshine-voice is absent."""

    def test_missing_moonshine_voice_raises(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        with (
            patch.dict(sys.modules, {"moonshine_voice": None}),
            pytest.raises(ImportError, match="uv sync --extra voice"),
        ):
            stt.start()

    def test_error_message_mentions_moonshine(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        with (
            patch.dict(sys.modules, {"moonshine_voice": None}),
            pytest.raises(ImportError, match="moonshine-voice"),
        ):
            stt.start()


# ---------------------------------------------------------------------------
# Tests — constructor defaults
# ---------------------------------------------------------------------------


class TestStreamingSTTDefaults:
    """Constructor stores config without loading MicTranscriber."""

    def test_default_model_arch_is_none(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        assert stt._model_arch_raw is None

    def test_custom_model_arch(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT(model_arch=2)
        assert stt._model_arch_raw == 2

    def test_default_update_interval(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        assert stt._update_interval == 0.5

    def test_custom_update_interval(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT(update_interval=1.0)
        assert stt._update_interval == 1.0

    def test_default_language(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        assert stt._language == "en"

    def test_custom_language(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT(language="fr")
        assert stt._language == "fr"

    def test_mic_transcriber_none_on_init(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        assert stt._mic is None


# ---------------------------------------------------------------------------
# Tests — start / stop lifecycle
# ---------------------------------------------------------------------------


class TestStreamingSTTLifecycle:
    """start() creates MicTranscriber and begins capture; stop() returns text."""

    def test_start_creates_mic_transcriber(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            try:
                fake.MicTranscriber.assert_called_once_with(
                    "/models/moonshine-small-streaming-en",
                    model_arch=4,
                    update_interval=0.5,
                )
                assert stt._mic is not None
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_start_calls_mic_start(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            try:
                fake.MicTranscriber.return_value.start.assert_called_once()
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_start_with_custom_arch(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT(model_arch=2, update_interval=1.0)
            stt.start()
            try:
                fake.MicTranscriber.assert_called_once_with(
                    "/models/moonshine-small-streaming-en",
                    model_arch=2,
                    update_interval=1.0,
                )
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_stop_returns_full_transcript(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            result = stt.stop()
            assert result == "Hello world How are you"
            fake.MicTranscriber.return_value.stop.assert_called_once()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_stop_with_empty_transcript(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            fake.MicTranscriber.return_value.stop.return_value.lines = []
            stt = StreamingSTT()
            stt.start()
            result = stt.stop()
            assert result == ""
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_stop_without_start_raises(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        with pytest.raises(RuntimeError, match="not started"):
            stt.stop()

    def test_start_while_running_raises(self) -> None:
        _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            try:
                with pytest.raises(RuntimeError, match="already running"):
                    stt.start()
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)


# ---------------------------------------------------------------------------
# Tests — callbacks
# ---------------------------------------------------------------------------


class TestStreamingSTTCallbacks:
    """Callbacks are wired to MicTranscriber events."""

    def test_on_text_update_callback(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            received: list[tuple[str, int]] = []
            stt = StreamingSTT()
            stt.start(on_text_update=lambda text, idx: received.append((text, idx)))
            try:
                # Simulate the MicTranscriber calling the on_text_update
                mic_instance = fake.MicTranscriber.return_value
                assert mic_instance.on_text_update is not None
                # Call the wrapped callback
                mic_instance.on_text_update("partial text", 0)
                assert ("partial text", 0) in received
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_on_line_complete_callback(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            received: list[tuple[str, int]] = []
            stt = StreamingSTT()
            stt.start(on_line_complete=lambda text, idx: received.append((text, idx)))
            try:
                mic_instance = fake.MicTranscriber.return_value
                assert mic_instance.on_line_complete is not None
                mic_instance.on_line_complete("completed line", 1)
                assert ("completed line", 1) in received
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_no_callbacks_sets_none(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            try:
                mic_instance = fake.MicTranscriber.return_value
                # When no callbacks provided, attributes should not be set
                # (MicTranscriber defaults handle this)
                assert mic_instance.on_text_update is None or callable(mic_instance.on_text_update)
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)


# ---------------------------------------------------------------------------
# Tests — asyncio thread safety
# ---------------------------------------------------------------------------


class TestStreamingSTTAsyncBridge:
    """When loop= is provided, callbacks bridge to the asyncio event loop."""

    def test_text_update_bridges_to_loop(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            loop = MagicMock(spec=asyncio.AbstractEventLoop)
            received: list[tuple[str, int]] = []

            def on_update(text: str, line_idx: int) -> None:
                received.append((text, line_idx))

            stt = StreamingSTT()
            stt.start(on_text_update=on_update, loop=loop)
            try:
                mic_instance = fake.MicTranscriber.return_value
                # Simulate audio-thread callback
                mic_instance.on_text_update("bridged text", 0)
                loop.call_soon_threadsafe.assert_called_once()
                # Verify the call passes the callback correctly
                args = loop.call_soon_threadsafe.call_args
                assert args[0][0] is on_update
                assert args[0][1] == "bridged text"
                assert args[0][2] == 0
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_line_complete_bridges_to_loop(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            loop = MagicMock(spec=asyncio.AbstractEventLoop)

            def on_complete(text: str, line_idx: int) -> None:
                pass

            stt = StreamingSTT()
            stt.start(on_line_complete=on_complete, loop=loop)
            try:
                mic_instance = fake.MicTranscriber.return_value
                mic_instance.on_line_complete("done line", 2)
                loop.call_soon_threadsafe.assert_called_once()
                args = loop.call_soon_threadsafe.call_args
                assert args[0][0] is on_complete
                assert args[0][1] == "done line"
                assert args[0][2] == 2
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_no_loop_calls_directly(self) -> None:
        """Without loop=, callbacks fire directly (on audio thread)."""
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            received: list[tuple[str, int]] = []
            stt = StreamingSTT()
            stt.start(on_text_update=lambda text, idx: received.append((text, idx)))
            try:
                mic_instance = fake.MicTranscriber.return_value
                mic_instance.on_text_update("direct", 0)
                assert ("direct", 0) in received
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)


# ---------------------------------------------------------------------------
# Tests — close() resource management
# ---------------------------------------------------------------------------


class TestStreamingSTTClose:
    """close() releases MicTranscriber resources and is idempotent."""

    def test_close_calls_mic_close(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            mic_instance = fake.MicTranscriber.return_value
            stt.close()
            mic_instance.close.assert_called_once()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_close_idempotent(self) -> None:
        _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            stt.close()
            stt.close()  # second call should not raise
            # mic.close() called once (first close), second is a no-op
            assert stt._mic is None
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_close_before_start_is_noop(self) -> None:
        from owlbear.voice.streaming_stt import StreamingSTT

        stt = StreamingSTT()
        stt.close()  # should not raise
        assert stt._mic is None

    def test_close_resets_running_flag(self) -> None:
        _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            assert stt._running is True
            stt.close()
            assert stt._running is False
        finally:
            sys.modules.pop("moonshine_voice", None)


# ---------------------------------------------------------------------------
# Tests — model resolution
# ---------------------------------------------------------------------------


class TestStreamingSTTModelResolution:
    """Model path is resolved via get_model_for_language."""

    def test_default_arch_uses_small_streaming(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT()
            stt.start()
            try:
                fake.get_model_for_language.assert_called_once_with(
                    "en",
                    model_arch=4,
                )
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)

    def test_custom_language(self) -> None:
        fake = _install_fake_moonshine()
        try:
            from owlbear.voice.streaming_stt import StreamingSTT

            stt = StreamingSTT(language="de")
            stt.start()
            try:
                fake.get_model_for_language.assert_called_once_with(
                    "de",
                    model_arch=4,
                )
            finally:
                stt.close()
        finally:
            sys.modules.pop("moonshine_voice", None)
