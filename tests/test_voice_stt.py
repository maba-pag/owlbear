"""Tests for STTEngine — Moonshine batch-mode rewrite (Tasks #241/#242).

All tests mock ``moonshine_voice`` so the actual package is never required.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from owlbear.voice.stt import STTEngine

# ---------------------------------------------------------------------------
# Helpers — build a fake ``moonshine_voice`` module
# ---------------------------------------------------------------------------


def _make_fake_moonshine() -> ModuleType:
    """Return a stub ``moonshine_voice`` module with mock Transcriber etc."""
    mod = ModuleType("moonshine_voice")

    # ModelArch enum mock
    model_arch = MagicMock(name="ModelArch")
    model_arch.SMALL_STREAMING = 4
    mod.ModelArch = model_arch  # type: ignore[attr-defined]

    # get_model_for_language mock
    mod.get_model_for_language = MagicMock(  # type: ignore[attr-defined]
        return_value="/models/moonshine-small-streaming-en",
    )

    # Transcriber class mock
    mock_transcriber_cls = MagicMock(name="Transcriber")
    line = MagicMock()
    line.text = "Hello world"
    transcript = MagicMock()
    transcript.lines = [line]
    mock_transcriber_cls.return_value.transcribe_without_streaming.return_value = transcript
    mod.Transcriber = mock_transcriber_cls  # type: ignore[attr-defined]

    return mod


def _pcm_audio(values: list[int] | None = None) -> bytes:
    """Create int16 PCM audio bytes from a list of sample values."""
    if values is None:
        values = [0, 100, -100, 32767, -32768]
    return np.array(values, dtype=np.int16).tobytes()


# ---------------------------------------------------------------------------
# Tests — ImportError guard
# ---------------------------------------------------------------------------


class TestSTTImportGuard:
    """STTEngine raises ImportError when moonshine-voice is absent."""

    def test_missing_moonshine_voice_raises(self) -> None:
        engine = STTEngine()
        with (
            patch.dict(sys.modules, {"moonshine_voice": None}),
            pytest.raises(ImportError, match="uv sync --extra voice"),
        ):
            engine.transcribe(_pcm_audio())

    def test_error_message_mentions_moonshine(self) -> None:
        engine = STTEngine()
        with (
            patch.dict(sys.modules, {"moonshine_voice": None}),
            pytest.raises(ImportError, match="moonshine-voice"),
        ):
            engine.transcribe(_pcm_audio())


# ---------------------------------------------------------------------------
# Tests — constructor defaults
# ---------------------------------------------------------------------------


class TestSTTEngineDefaults:
    """Constructor stores config without loading model."""

    def test_default_model_arch_is_none(self) -> None:
        engine = STTEngine()
        assert engine._model_arch_raw is None

    def test_custom_model_arch(self) -> None:
        engine = STTEngine(model_arch=2)
        assert engine._model_arch_raw == 2

    def test_transcriber_none_on_init(self) -> None:
        engine = STTEngine()
        assert engine._transcriber is None


# ---------------------------------------------------------------------------
# Tests — lazy model loading
# ---------------------------------------------------------------------------


class TestSTTLazyLoading:
    """Transcriber created on first transcribe(), not on __init__."""

    def test_model_not_loaded_on_init(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            assert engine._transcriber is None
            fake_mv.Transcriber.assert_not_called()

    def test_model_loaded_on_first_transcribe(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio())
            fake_mv.Transcriber.assert_called_once()

    def test_model_reused_on_subsequent_calls(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio())
            engine.transcribe(_pcm_audio())
            assert fake_mv.Transcriber.call_count == 1

    def test_default_model_arch_is_small_streaming(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio())
            fake_mv.get_model_for_language.assert_called_once_with(
                "en",
                model_arch=fake_mv.ModelArch.SMALL_STREAMING,
            )

    def test_custom_model_arch_used(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine(model_arch=2)
            engine.transcribe(_pcm_audio())
            fake_mv.get_model_for_language.assert_called_once_with(
                "en",
                model_arch=2,
            )

    def test_model_path_passed_to_transcriber(self) -> None:
        fake_mv = _make_fake_moonshine()
        fake_mv.get_model_for_language.return_value = "/custom/model/path"
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio())
            fake_mv.Transcriber.assert_called_once_with(
                "/custom/model/path",
                model_arch=fake_mv.ModelArch.SMALL_STREAMING,
            )


# ---------------------------------------------------------------------------
# Tests — transcribe
# ---------------------------------------------------------------------------


class TestSTTTranscribe:
    """transcribe() converts audio bytes and returns concatenated text."""

    def test_transcribe_returns_text(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            result = engine.transcribe(_pcm_audio())
            assert isinstance(result, str)
            assert result == "Hello world"

    def test_transcribe_multiple_lines(self) -> None:
        fake_mv = _make_fake_moonshine()
        line1, line2 = MagicMock(), MagicMock()
        line1.text = "Hello"
        line2.text = "world"
        transcript = MagicMock()
        transcript.lines = [line1, line2]
        fake_mv.Transcriber.return_value.transcribe_without_streaming.return_value = transcript
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            result = engine.transcribe(_pcm_audio())
            assert result == "Hello world"

    def test_transcribe_strips_whitespace(self) -> None:
        fake_mv = _make_fake_moonshine()
        line = MagicMock()
        line.text = "  Hello world  "
        transcript = MagicMock()
        transcript.lines = [line]
        fake_mv.Transcriber.return_value.transcribe_without_streaming.return_value = transcript
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            result = engine.transcribe(_pcm_audio())
            assert result == "Hello world"

    def test_transcribe_empty_lines(self) -> None:
        fake_mv = _make_fake_moonshine()
        transcript = MagicMock()
        transcript.lines = []
        fake_mv.Transcriber.return_value.transcribe_without_streaming.return_value = transcript
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            result = engine.transcribe(_pcm_audio())
            assert result == ""

    def test_transcribe_passes_language_to_model_loader(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio(), language="de")
            fake_mv.get_model_for_language.assert_called_once_with(
                "de",
                model_arch=fake_mv.ModelArch.SMALL_STREAMING,
            )

    def test_transcribe_uses_sample_rate_16000(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio())
            call_kwargs = fake_mv.Transcriber.return_value.transcribe_without_streaming.call_args
            assert call_kwargs.kwargs.get("sample_rate") == 16000


# ---------------------------------------------------------------------------
# Tests — audio conversion (int16 PCM → float32)
# ---------------------------------------------------------------------------


class TestSTTAudioConversion:
    """Audio bytes are correctly converted from int16 PCM to float32."""

    def test_audio_converted_to_float32(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            pcm = _pcm_audio([0, 16384, -16384])
            engine.transcribe(pcm)
            call_args = fake_mv.Transcriber.return_value.transcribe_without_streaming.call_args
            audio_arg = call_args[0][0]  # first positional arg
            assert audio_arg.dtype == np.float32
            np.testing.assert_allclose(audio_arg, [0.0, 0.5, -0.5], atol=1e-5)

    def test_max_int16_maps_to_near_one(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio([32767]))
            call_args = fake_mv.Transcriber.return_value.transcribe_without_streaming.call_args
            audio_arg = call_args[0][0]
            assert abs(float(audio_arg[0]) - 1.0) < 0.001

    def test_min_int16_maps_to_minus_one(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio([-32768]))
            call_args = fake_mv.Transcriber.return_value.transcribe_without_streaming.call_args
            audio_arg = call_args[0][0]
            assert abs(float(audio_arg[0]) - (-1.0)) < 0.001


# ---------------------------------------------------------------------------
# Tests — close()
# ---------------------------------------------------------------------------


class TestSTTClose:
    """close() releases Transcriber native resources (ONNX Runtime)."""

    def test_close_releases_transcriber(self) -> None:
        fake_mv = _make_fake_moonshine()
        with patch.dict(sys.modules, {"moonshine_voice": fake_mv}):
            engine = STTEngine()
            engine.transcribe(_pcm_audio())
            assert engine._transcriber is not None
            engine.close()
            assert engine._transcriber is None
            fake_mv.Transcriber.return_value.close.assert_called_once()

    def test_close_safe_when_not_loaded(self) -> None:
        """close() on a never-used engine does not raise."""
        engine = STTEngine()
        engine.close()  # should not raise
        assert engine._transcriber is None
