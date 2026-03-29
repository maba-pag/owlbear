"""Failing RED-phase tests for task #51: Voice addon TTS with Kokoro and pyttsx3 fallback.

Covers:
- TTSBackend protocol: speak(text) and close() signatures (AC1)
- KokoroTTSBackend: lazy KPipeline init, chunk iteration, sounddevice.play+wait (AC2)
- Pyttsx3TTSBackend: lazy pyttsx3.init, say/runAndWait pattern (AC3)
- Import-time _kokoro_available flag in factory module (AC4)
- create_tts_backend() factory: returns correct backend, logs selection (AC5)
- Speed mapping: float 1.0=normal → Kokoro direct, pyttsx3 int(speed*200) (AC6)
- Voice mapping: string to Kokoro voice param, substring match for pyttsx3 (AC7)
- Kokoro init failure falls back to pyttsx3, factory never raises (AC8)

All tests fail on current HEAD because owlbear_voice/tts/ does not yet exist.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from owlbear_voice.tts import create_tts_backend
from owlbear_voice.tts import _kokoro_available
from owlbear_voice.tts.kokoro_backend import KokoroTTSBackend
from owlbear_voice.tts.protocol import TTSBackend
from owlbear_voice.tts.pyttsx3_backend import Pyttsx3TTSBackend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kokoro_result(audio_array: Any = None) -> MagicMock:
    """Build a mock Kokoro Result with a .audio attribute."""
    result = MagicMock()
    result.audio = MagicMock()
    result.audio.numpy.return_value = audio_array or [0.0, 0.1, 0.2]
    return result


def _make_pyttsx3_engine() -> MagicMock:
    """Build a mock pyttsx3 engine."""
    engine = MagicMock()
    voice1 = MagicMock()
    voice1.id = "HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_ZIRA_11.0"
    voice2 = MagicMock()
    voice2.id = "HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-US_DAVID_11.0"
    engine.getProperty.return_value = [voice1, voice2]
    return engine


# ---------------------------------------------------------------------------
# AC1: TTSBackend protocol — speak(text: str) -> None, close() -> None
# ---------------------------------------------------------------------------


class TestFromAC_TTSBackendProtocol:
    """TTSBackend must be a typing.Protocol with speak() and close() methods."""

    def test_protocol_is_importable(self) -> None:
        """AC1: TTSBackend must be importable from owlbear_voice.tts.protocol."""
        assert TTSBackend is not None

    def test_speak_method_in_protocol(self) -> None:
        """AC1: TTSBackend protocol must define speak() method."""
        assert hasattr(TTSBackend, "speak")

    def test_close_method_in_protocol(self) -> None:
        """AC1: TTSBackend protocol must define close() method."""
        assert hasattr(TTSBackend, "close")

    def test_speak_signature_text_param(self) -> None:
        """AC1: speak(text: str) -> None — text parameter must be present."""
        import inspect
        sig = inspect.signature(TTSBackend.speak)
        assert "text" in sig.parameters

    def test_close_no_params(self) -> None:
        """AC1: close() -> None — no parameters beyond self."""
        import inspect
        sig = inspect.signature(TTSBackend.close)
        params = [p for p in sig.parameters if p != "self"]
        assert params == []

    def test_kokoro_backend_satisfies_protocol(self) -> None:
        """AC1: KokoroTTSBackend must satisfy the TTSBackend protocol."""
        assert isinstance(KokoroTTSBackend, type)
        assert hasattr(KokoroTTSBackend, "speak")
        assert hasattr(KokoroTTSBackend, "close")

    def test_pyttsx3_backend_satisfies_protocol(self) -> None:
        """AC1: Pyttsx3TTSBackend must satisfy the TTSBackend protocol."""
        assert isinstance(Pyttsx3TTSBackend, type)
        assert hasattr(Pyttsx3TTSBackend, "speak")
        assert hasattr(Pyttsx3TTSBackend, "close")


# ---------------------------------------------------------------------------
# AC2: KokoroTTSBackend — lazy KPipeline init, chunk iteration, sounddevice
# ---------------------------------------------------------------------------


class TestFromAC_KokoroTTSBackend:
    """KokoroTTSBackend must use lazy init, iterate generator, play via sounddevice."""

    def _make_backend(self, mock_pipeline_cls: MagicMock, voice: str = "af_heart", speed: float = 1.0) -> KokoroTTSBackend:
        """Instantiate backend with injected mock KPipeline class."""
        return KokoroTTSBackend(voice=voice, speed=speed, pipeline_cls=mock_pipeline_cls)

    def test_kpipeline_not_called_at_init(self) -> None:
        """AC2: KPipeline must NOT be instantiated until the first speak() call."""
        mock_pipeline_cls = MagicMock()
        _backend = self._make_backend(mock_pipeline_cls)
        mock_pipeline_cls.assert_not_called()

    def test_kpipeline_called_on_first_speak(self) -> None:
        """AC2: KPipeline must be instantiated on the first speak() call."""
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        mock_pipeline.return_value = iter([_make_kokoro_result()])

        backend = self._make_backend(mock_pipeline_cls)
        with patch("sounddevice.play"), patch("sounddevice.wait"):
            backend.speak("hello")

        mock_pipeline_cls.assert_called_once()

    def test_kpipeline_called_only_once_across_multiple_speaks(self) -> None:
        """AC2: KPipeline must be instantiated only once (lazy, not per-call)."""
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        mock_pipeline.return_value = iter([_make_kokoro_result()])

        backend = self._make_backend(mock_pipeline_cls)
        with patch("sounddevice.play"), patch("sounddevice.wait"):
            backend.speak("first")
            mock_pipeline.return_value = iter([_make_kokoro_result()])
            backend.speak("second")

        mock_pipeline_cls.assert_called_once()

    def test_sounddevice_play_called_with_audio_array_and_24000(self) -> None:
        """AC2: sounddevice.play(result.audio.numpy(), 24000) for each chunk."""
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        audio_data = [0.1, 0.2, 0.3]
        result = _make_kokoro_result(audio_data)
        mock_pipeline.return_value = iter([result])

        backend = self._make_backend(mock_pipeline_cls)
        with patch("sounddevice.play") as mock_play, patch("sounddevice.wait"):
            backend.speak("hello")

        mock_play.assert_called_once_with(audio_data, 24000)

    def test_sounddevice_wait_called_after_each_chunk(self) -> None:
        """AC2: sd.wait() must be called after each sounddevice.play()."""
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        chunks = [_make_kokoro_result(), _make_kokoro_result()]
        mock_pipeline.return_value = iter(chunks)

        backend = self._make_backend(mock_pipeline_cls)
        with patch("sounddevice.play"), patch("sounddevice.wait") as mock_wait:
            backend.speak("two chunks")

        assert mock_wait.call_count == 2

    def test_all_chunks_in_generator_are_played(self) -> None:
        """AC2: Every chunk yielded by the generator must be played."""
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        chunks = [_make_kokoro_result([i * 0.1]) for i in range(3)]
        mock_pipeline.return_value = iter(chunks)

        backend = self._make_backend(mock_pipeline_cls)
        with patch("sounddevice.play") as mock_play, patch("sounddevice.wait"):
            backend.speak("three chunks")

        assert mock_play.call_count == 3

    def test_close_method_exists_and_callable(self) -> None:
        """AC2: close() must exist and be callable on KokoroTTSBackend."""
        mock_pipeline_cls = MagicMock()
        backend = self._make_backend(mock_pipeline_cls)
        assert callable(getattr(backend, "close", None))

    def test_close_before_first_speak_does_not_raise(self) -> None:
        """AC2: close() before first speak (no pipeline init) must not raise."""
        mock_pipeline_cls = MagicMock()
        backend = self._make_backend(mock_pipeline_cls)
        backend.close()  # must not raise


# ---------------------------------------------------------------------------
# AC3: Pyttsx3TTSBackend — lazy pyttsx3.init, say/runAndWait
# ---------------------------------------------------------------------------


class TestFromAC_Pyttsx3TTSBackend:
    """Pyttsx3TTSBackend must use lazy init, call say/runAndWait, mirror v1 pattern."""

    def test_pyttsx3_init_not_called_at_backend_init(self) -> None:
        """AC3: pyttsx3.init() must NOT be called until the first speak()."""
        with patch("pyttsx3.init") as mock_init:
            Pyttsx3TTSBackend(voice="zira", speed=1.0)
            mock_init.assert_not_called()

    def test_pyttsx3_init_called_on_first_speak(self) -> None:
        """AC3: pyttsx3.init() must be called on the first speak()."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine) as mock_init:
            backend = Pyttsx3TTSBackend(voice="zira", speed=1.0)
            backend.speak("hello")
        mock_init.assert_called_once()

    def test_pyttsx3_init_called_only_once(self) -> None:
        """AC3: pyttsx3.init() must be called only once across multiple speaks (lazy)."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine) as mock_init:
            backend = Pyttsx3TTSBackend(voice="zira", speed=1.0)
            backend.speak("first")
            backend.speak("second")
        mock_init.assert_called_once()

    def test_engine_say_called_with_text(self) -> None:
        """AC3: engine.say(text) must be called with the provided text."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="zira", speed=1.0)
            backend.speak("say this")
        engine.say.assert_called_once_with("say this")

    def test_engine_run_and_wait_called_after_say(self) -> None:
        """AC3: engine.runAndWait() must be called after engine.say()."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="zira", speed=1.0)
            backend.speak("say this")
        engine.runAndWait.assert_called_once()

    def test_say_called_before_run_and_wait(self) -> None:
        """AC3: say() must be called before runAndWait() — correct ordering."""
        engine = _make_pyttsx3_engine()
        call_order: list[str] = []
        engine.say.side_effect = lambda _t: call_order.append("say")
        engine.runAndWait.side_effect = lambda: call_order.append("runAndWait")
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="zira", speed=1.0)
            backend.speak("ordered")
        assert call_order == ["say", "runAndWait"]

    def test_close_method_exists(self) -> None:
        """AC3: close() must exist and be callable on Pyttsx3TTSBackend."""
        backend = Pyttsx3TTSBackend(voice="zira", speed=1.0)
        assert callable(getattr(backend, "close", None))


# ---------------------------------------------------------------------------
# AC4: Import-time _kokoro_available flag
# ---------------------------------------------------------------------------


class TestFromAC_ImportTimeFlag:
    """_kokoro_available must be a bool set at module import time."""

    def test_kokoro_available_flag_is_bool(self) -> None:
        """AC4: _kokoro_available must be a bool, not None or other type."""
        assert isinstance(_kokoro_available, bool)

    def test_kokoro_available_is_module_level(self) -> None:
        """AC4: _kokoro_available must be accessible directly from owlbear_voice.tts."""
        import owlbear_voice.tts as tts_module
        assert hasattr(tts_module, "_kokoro_available")

    def test_kokoro_available_false_when_kokoro_not_installed(self) -> None:
        """AC4: if kokoro is not importable, _kokoro_available must be False."""
        import sys
        import importlib

        # Remove kokoro from sys.modules if present and reload tts
        saved = sys.modules.pop("kokoro", None)
        sys.modules["kokoro"] = None  # type: ignore[assignment]  # block import
        try:
            import owlbear_voice.tts as tts_mod
            importlib.reload(tts_mod)
            assert tts_mod._kokoro_available is False
        finally:
            if saved is None:
                sys.modules.pop("kokoro", None)
            else:
                sys.modules["kokoro"] = saved


# ---------------------------------------------------------------------------
# AC5 & AC8: create_tts_backend() factory — selection, logging, init failure
# ---------------------------------------------------------------------------


class TestFromAC_Factory:
    """create_tts_backend() must select the right backend, log choice, never raise."""

    def test_factory_returns_kokoro_when_available(self) -> None:
        """AC5: factory returns KokoroTTSBackend when _kokoro_available is True."""
        with patch("owlbear_voice.tts._kokoro_available", new=True):
            backend = create_tts_backend(voice="af_heart", speed=1.0)
        assert isinstance(backend, KokoroTTSBackend)

    def test_factory_returns_pyttsx3_when_kokoro_unavailable(self) -> None:
        """AC5: factory returns Pyttsx3TTSBackend when _kokoro_available is False."""
        with patch("owlbear_voice.tts._kokoro_available", new=False):
            backend = create_tts_backend(voice="zira", speed=1.0)
        assert isinstance(backend, Pyttsx3TTSBackend)

    def test_factory_logs_kokoro_selection(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC5: factory must log which backend was selected (kokoro)."""
        with patch("owlbear_voice.tts._kokoro_available", new=True), caplog.at_level(logging.DEBUG):
            create_tts_backend(voice="af_heart", speed=1.0)
        assert any("kokoro" in record.message.lower() for record in caplog.records)

    def test_factory_logs_pyttsx3_selection(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC5: factory must log which backend was selected (pyttsx3)."""
        with patch("owlbear_voice.tts._kokoro_available", new=False), caplog.at_level(logging.DEBUG):
            create_tts_backend(voice="zira", speed=1.0)
        assert any("pyttsx3" in record.message.lower() for record in caplog.records)

    def test_factory_never_raises_on_backend_selection(self) -> None:
        """AC8: factory must never raise on backend selection — non-critical subsystem."""
        with (
            patch("owlbear_voice.tts._kokoro_available", new=True),
            patch(
                "owlbear_voice.tts.KokoroTTSBackend",
                side_effect=RuntimeError("espeak-ng not found"),
            ),
        ):
            # Must not propagate the RuntimeError
            backend = create_tts_backend(voice="af_heart", speed=1.0)

        # Fell back to pyttsx3
        assert isinstance(backend, Pyttsx3TTSBackend)

    def test_factory_falls_back_on_kokoro_init_error(self) -> None:
        """AC8: when Kokoro init raises, factory must return Pyttsx3TTSBackend."""
        with (
            patch("owlbear_voice.tts._kokoro_available", new=True),
            patch(
                "owlbear_voice.tts.KokoroTTSBackend",
                side_effect=Exception("model download failed"),
            ),
        ):
            backend = create_tts_backend(voice="af_heart", speed=1.0)

        assert isinstance(backend, Pyttsx3TTSBackend)

    def test_factory_logs_warning_on_kokoro_init_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC8: when Kokoro init fails, factory must emit a warning log."""
        with (
            patch("owlbear_voice.tts._kokoro_available", new=True),
            patch(
                "owlbear_voice.tts.KokoroTTSBackend",
                side_effect=RuntimeError("espeak-ng not found"),
            ),
            caplog.at_level(logging.WARNING),
        ):
            create_tts_backend(voice="af_heart", speed=1.0)

        assert any(
            record.levelno >= logging.WARNING
            for record in caplog.records
        )

    def test_factory_accepts_voice_and_speed_params(self) -> None:
        """AC5: create_tts_backend(voice, speed) must accept both parameters."""
        import inspect
        sig = inspect.signature(create_tts_backend)
        assert "voice" in sig.parameters
        assert "speed" in sig.parameters


# ---------------------------------------------------------------------------
# AC6: Speed mapping — float 1.0=normal → Kokoro direct, pyttsx3 int(speed*200)
# ---------------------------------------------------------------------------


class TestFromAC_SpeedMapping:
    """Speed float must be passed to Kokoro directly and to pyttsx3 as int(speed*200)."""

    def test_kokoro_receives_speed_directly(self) -> None:
        """AC6: speed float must be passed directly to Kokoro pipeline, not converted."""
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        result = _make_kokoro_result()
        mock_pipeline.return_value = iter([result])

        backend = KokoroTTSBackend(voice="af_heart", speed=1.5, pipeline_cls=mock_pipeline_cls)
        with patch("sounddevice.play"), patch("sounddevice.wait"):
            backend.speak("fast")

        # Pipeline call must include speed=1.5
        call_kwargs = mock_pipeline.call_args
        # speed param can be positional or keyword — check in args or kwargs
        assert call_kwargs is not None
        all_args = list(call_kwargs.args) + list(call_kwargs.kwargs.values())
        assert 1.5 in all_args or call_kwargs.kwargs.get("speed") == 1.5

    def test_pyttsx3_rate_is_int_speed_times_200(self) -> None:
        """AC6: pyttsx3 rate must be set to int(speed * 200)."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="zira", speed=1.5)
            backend.speak("rate test")

        # Expect setProperty('rate', 300) — int(1.5 * 200)
        engine.setProperty.assert_any_call("rate", 300)

    def test_pyttsx3_normal_speed_is_200(self) -> None:
        """AC6: speed=1.0 must map to pyttsx3 rate=200 (normal WPM)."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="zira", speed=1.0)
            backend.speak("normal speed")

        engine.setProperty.assert_any_call("rate", 200)

    def test_pyttsx3_half_speed_is_100(self) -> None:
        """AC6 boundary: speed=0.5 must map to pyttsx3 rate=100."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="zira", speed=0.5)
            backend.speak("slow")

        engine.setProperty.assert_any_call("rate", 100)


# ---------------------------------------------------------------------------
# AC7: Voice mapping — string to Kokoro voice param, substring match for pyttsx3
# ---------------------------------------------------------------------------


class TestFromAC_VoiceMapping:
    """Voice string must be passed to Kokoro and used for substring match in pyttsx3."""

    def test_kokoro_voice_string_passed_as_voice_param(self) -> None:
        """AC7: voice string must be passed to Kokoro pipeline as voice param."""
        mock_pipeline_cls = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline
        result = _make_kokoro_result()
        mock_pipeline.return_value = iter([result])

        backend = KokoroTTSBackend(voice="af_bella", speed=1.0, pipeline_cls=mock_pipeline_cls)
        with patch("sounddevice.play"), patch("sounddevice.wait"):
            backend.speak("voice test")

        call_kwargs = mock_pipeline.call_args
        all_args = list(call_kwargs.args) + list(call_kwargs.kwargs.values())
        assert "af_bella" in all_args or call_kwargs.kwargs.get("voice") == "af_bella"

    def test_pyttsx3_voice_substring_match_selects_voice(self) -> None:
        """AC7: voice string must be used as substring match against engine voice IDs."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="ZIRA", speed=1.0)
            backend.speak("voice select")

        # Should have called setProperty('voice', <matched id>)
        set_calls = engine.setProperty.call_args_list
        voice_calls = [c for c in set_calls if c.args[0] == "voice"]
        assert len(voice_calls) == 1
        # The matched voice ID must contain the substring "ZIRA" (case-insensitive)
        matched_id: str = voice_calls[0].args[1]
        assert "ZIRA" in matched_id.upper()

    def test_pyttsx3_no_match_does_not_crash(self) -> None:
        """AC7 edge: if no voice ID matches the substring, speak must not raise."""
        engine = _make_pyttsx3_engine()
        with patch("pyttsx3.init", return_value=engine):
            backend = Pyttsx3TTSBackend(voice="nonexistent_voice_xyz", speed=1.0)
            backend.speak("fallback voice")  # must not raise
