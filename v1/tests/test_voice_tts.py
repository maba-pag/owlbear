"""Tests for TTSEngine — Task #93.

All tests mock ``pyttsx3`` so the actual package is never required.
"""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — build a fake ``pyttsx3`` module
# ---------------------------------------------------------------------------


def _make_fake_pyttsx3() -> ModuleType:
    """Return a stub ``pyttsx3`` module with a mock ``init()``."""
    mod = ModuleType("pyttsx3")
    mock_engine = MagicMock(name="pyttsx3.Engine")
    # getProperty returns current value for rate/volume
    mock_engine.getProperty.side_effect = {"rate": 200, "volume": 1.0}.get
    mod.init = MagicMock(return_value=mock_engine)  # type: ignore[attr-defined]
    return mod


# ---------------------------------------------------------------------------
# Tests — graceful ImportError when pyttsx3 is missing
# ---------------------------------------------------------------------------


class TestTTSImportGuard:
    """TTSEngine must raise ImportError when pyttsx3 is absent."""

    def test_missing_pyttsx3_raises(self) -> None:
        with patch.dict(sys.modules, {"pyttsx3": None}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]

            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine()
            with pytest.raises(ImportError, match="uv sync --extra voice"):
                asyncio.run(engine.speak("hello"))


# ---------------------------------------------------------------------------
# Tests — constructor defaults
# ---------------------------------------------------------------------------


class TestTTSEngineDefaults:
    """Verify constructor stores configuration without creating the engine."""

    def test_default_rate(self) -> None:
        with patch.dict(sys.modules, {"pyttsx3": _make_fake_pyttsx3()}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine()
            assert engine._rate == 200

    def test_default_volume(self) -> None:
        with patch.dict(sys.modules, {"pyttsx3": _make_fake_pyttsx3()}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine()
            assert engine._volume == 1.0

    def test_custom_params(self) -> None:
        with patch.dict(sys.modules, {"pyttsx3": _make_fake_pyttsx3()}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine(rate=180, volume=0.7)
            assert engine._rate == 180
            assert engine._volume == 0.7


# ---------------------------------------------------------------------------
# Tests — lazy engine initialisation
# ---------------------------------------------------------------------------


class TestTTSLazyInit:
    """pyttsx3 engine must NOT be created in __init__; only on first speak()."""

    def test_engine_not_created_on_init(self) -> None:
        fake_tts = _make_fake_pyttsx3()
        with patch.dict(sys.modules, {"pyttsx3": fake_tts}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine()
            assert engine._engine is None
            fake_tts.init.assert_not_called()

    @pytest.mark.asyncio
    async def test_engine_created_on_first_speak(self) -> None:
        fake_tts = _make_fake_pyttsx3()
        with patch.dict(sys.modules, {"pyttsx3": fake_tts}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine()
            await engine.speak("hello")
            fake_tts.init.assert_called_once()


# ---------------------------------------------------------------------------
# Tests — speak
# ---------------------------------------------------------------------------


class TestTTSSpeak:
    """speak() must call engine.say + engine.runAndWait via asyncio.to_thread."""

    @pytest.mark.asyncio
    async def test_speak_calls_say_and_run_and_wait(self) -> None:
        fake_tts = _make_fake_pyttsx3()
        with patch.dict(sys.modules, {"pyttsx3": fake_tts}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine()
            await engine.speak("test message")

            mock_engine = fake_tts.init.return_value
            mock_engine.say.assert_called_once_with("test message")
            mock_engine.runAndWait.assert_called_once()

    @pytest.mark.asyncio
    async def test_speak_sets_rate_and_volume(self) -> None:
        fake_tts = _make_fake_pyttsx3()
        with patch.dict(sys.modules, {"pyttsx3": fake_tts}):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine(rate=180, volume=0.5)
            await engine.speak("hi")

            mock_engine = fake_tts.init.return_value
            mock_engine.setProperty.assert_any_call("rate", 180)
            mock_engine.setProperty.assert_any_call("volume", 0.5)

    @pytest.mark.asyncio
    async def test_speak_uses_to_thread(self) -> None:
        """speak() must delegate the blocking pyttsx3 call to asyncio.to_thread."""
        fake_tts = _make_fake_pyttsx3()
        to_thread_mock = MagicMock(wraps=asyncio.to_thread)
        with (
            patch.dict(sys.modules, {"pyttsx3": fake_tts}),
            patch("asyncio.to_thread", new=to_thread_mock) as mock_to_thread,
        ):
            if "owlbear.voice.tts" in sys.modules:
                del sys.modules["owlbear.voice.tts"]
            from owlbear.voice.tts import TTSEngine

            engine = TTSEngine()
            await engine.speak("test")
            mock_to_thread.assert_called_once()
