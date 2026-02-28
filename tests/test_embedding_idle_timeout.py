"""Tests for BgeM3 idle-timeout model unloading (task #287).

TDD tests for the idle-timeout feature that will be added to
BgeM3EmbeddingProvider in task #261.  These tests are expected to FAIL
until the implementation is complete.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from owlbear.config import OwlBearSettings
from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider

# -- Helpers -----------------------------------------------------------------


def _make_bge_encode_output(texts: list[str], dim: int = 1024) -> dict[str, object]:
    """Build a fake BGEM3FlagModel.encode() return dict."""
    n = len(texts)
    rng = np.random.default_rng(42)
    dense_vecs = rng.random((n, dim)).astype(np.float32)
    lexical_weights: list[dict[str, float]] = [
        {"101": 0.5, "202": 0.3} for _ in range(n)
    ]
    colbert_vecs: list[np.ndarray] = [
        rng.random((5, dim)).astype(np.float32) for _ in range(n)
    ]
    return {
        "dense_vecs": dense_vecs,
        "lexical_weights": lexical_weights,
        "colbert_vecs": colbert_vecs,
    }


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture
def mock_flag_module() -> Generator[MagicMock, None, None]:
    """Inject a mock FlagEmbedding module into sys.modules.

    Configures BGEM3FlagModel to return realistic encode() output so
    that embed() and embed_hybrid() work without the real model.
    """
    mock_module = MagicMock()
    mock_instance = MagicMock()
    mock_instance.encode.side_effect = _make_bge_encode_output
    mock_module.BGEM3FlagModel.return_value = mock_instance

    with patch.dict(sys.modules, {"FlagEmbedding": mock_module}):
        yield mock_module


@pytest.fixture
def provider(mock_flag_module: MagicMock) -> Generator[BgeM3EmbeddingProvider, None, None]:
    """Create a BgeM3EmbeddingProvider with a short idle timeout (0.1s).

    Cleans up any pending timer after each test to prevent leaking
    background threads.
    """
    _ = mock_flag_module  # fixture dependency — patches sys.modules
    p = BgeM3EmbeddingProvider(idle_timeout=0.1)
    yield p
    # Cleanup: cancel any pending timer
    if hasattr(p, "_timer") and p._timer is not None:
        p._timer.cancel()


# -- Config ------------------------------------------------------------------


class TestEmbeddingIdleTimeoutConfig:
    """OwlBearSettings has an embedding_idle_timeout field."""

    def test_default_value_is_600(self) -> None:
        """Default idle timeout is 600 seconds."""
        settings = OwlBearSettings()
        assert settings.embedding_idle_timeout == 600

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Can be overridden via OWLBEAR_EMBEDDING_IDLE_TIMEOUT env var."""
        monkeypatch.setenv("OWLBEAR_EMBEDDING_IDLE_TIMEOUT", "300")
        settings = OwlBearSettings()
        assert settings.embedding_idle_timeout == 300


# -- Constructor -------------------------------------------------------------


@pytest.mark.usefixtures("mock_flag_module")
class TestIdleTimeoutConstructor:
    """BgeM3EmbeddingProvider accepts idle_timeout parameter."""

    def test_accepts_idle_timeout_parameter(self) -> None:
        """No error when constructing with idle_timeout."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0.1)
        assert provider.idle_timeout == 0.1

    def test_default_idle_timeout(self) -> None:
        """Default idle_timeout is 600.0 seconds."""
        provider = BgeM3EmbeddingProvider()
        assert provider.idle_timeout == 600.0

    def test_has_last_used_attribute(self) -> None:
        """Provider has _last_used attribute initialized to 0.0."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0.1)
        assert provider._last_used == 0.0

    def test_has_timer_attribute(self) -> None:
        """Provider has _timer attribute initialized to None."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0.1)
        assert provider._timer is None

    def test_has_lock_attribute(self) -> None:
        """Provider has _lock attribute that is a threading.Lock."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0.1)
        assert isinstance(provider._lock, type(threading.Lock()))


# -- _last_used timestamp updates -------------------------------------------


class TestLastUsedTimestamp:
    """embed() and embed_hybrid() update _last_used timestamp."""

    def test_embed_updates_last_used(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """embed() sets _last_used to current monotonic time."""
        before = time.monotonic()
        provider.embed(["hello"])
        after = time.monotonic()
        assert before <= provider._last_used <= after

    def test_embed_hybrid_updates_last_used(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """embed_hybrid() sets _last_used to current monotonic time."""
        before = time.monotonic()
        provider.embed_hybrid(["hello"])
        after = time.monotonic()
        assert before <= provider._last_used <= after

    def test_successive_calls_advance_last_used(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """Each embed() call updates _last_used to a newer timestamp."""
        provider.embed(["first"])
        first_ts = provider._last_used
        time.sleep(0.01)
        provider.embed(["second"])
        assert provider._last_used > first_ts


# -- Timer fires unload after idle_timeout ----------------------------------


class TestTimerFiresUnload:
    """Timer triggers unload() after idle_timeout expires."""

    def test_model_unloaded_after_timeout(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """Model is set to None after idle_timeout (0.1s) expires."""
        provider.embed(["trigger model load"])
        assert provider._model is not None
        # Wait for timer to fire (idle_timeout=0.1s + generous margin)
        time.sleep(0.3)
        assert provider._model is None

    def test_timer_is_alive_after_embed(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """A timer is running after embed() call."""
        provider.embed(["hello"])
        assert provider._timer is not None
        assert provider._timer.is_alive()

    def test_timer_is_alive_after_embed_hybrid(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """A timer is running after embed_hybrid() call."""
        provider.embed_hybrid(["hello"])
        assert provider._timer is not None
        assert provider._timer.is_alive()


# -- unload() after timeout ------------------------------------------------


class TestUnloadAfterTimeout:
    """unload() correctly clears model when timer fires."""

    def test_unload_sets_model_none(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """After timeout, _model is None."""
        provider.embed(["load model"])
        assert provider._model is not None
        time.sleep(0.3)
        assert provider._model is None

    def test_gc_collect_called_on_idle_unload(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """gc.collect() is called when the idle timer fires unload."""
        provider.embed(["load model"])
        with patch("owlbear.memory.knowledge.embeddings.gc.collect") as mock_gc:
            time.sleep(0.3)
            mock_gc.assert_called()


# -- Re-initialization after timeout ----------------------------------------


class TestReinitAfterTimeout:
    """embed() after timeout transparently re-initializes model."""

    def test_embed_after_timeout_returns_results(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """embed() returns valid results after model was unloaded by timer."""
        result1 = provider.embed(["first call"])
        assert len(result1) == 1

        # Wait for idle unload
        time.sleep(0.3)
        assert provider._model is None

        # Should transparently re-init and produce results
        result2 = provider.embed(["second call"])
        assert len(result2) == 1

    def test_model_constructor_called_again_after_timeout(
        self, provider: BgeM3EmbeddingProvider, mock_flag_module: MagicMock
    ) -> None:
        """BGEM3FlagModel is constructed again after timeout + re-use."""
        provider.embed(["first"])
        time.sleep(0.3)
        assert provider._model is None

        provider.embed(["second"])
        # Model class should have been called twice (initial + reload)
        assert mock_flag_module.BGEM3FlagModel.call_count == 2


# -- Timer reset on activity ------------------------------------------------


class TestTimerReset:
    """Timer resets when embed() is called before timeout expires."""

    def test_activity_before_timeout_keeps_model_loaded(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """Calling embed() before timeout resets the timer, keeping model alive."""
        provider.embed(["first"])
        time.sleep(0.05)  # Well before 0.1s timeout
        provider.embed(["second"])
        # After another 0.08s (total 0.13s from first, but only 0.08s from second)
        # model should still be loaded because timer was reset
        time.sleep(0.08)
        assert provider._model is not None

    def test_old_timer_cancelled_on_new_embed(
        self, provider: BgeM3EmbeddingProvider
    ) -> None:
        """Previous timer is cancelled when a new embed() call resets it."""
        provider.embed(["first"])
        first_timer = provider._timer
        provider.embed(["second"])
        second_timer = provider._timer
        # First and second timer should be different objects
        assert first_timer is not second_timer


# -- No timer when idle_timeout is 0 (disabled) -----------------------------


@pytest.mark.usefixtures("mock_flag_module")
class TestIdleTimeoutDisabled:
    """When idle_timeout=0, no timer is started."""

    def test_no_timer_when_disabled(self) -> None:
        """With idle_timeout=0, embed() does not start a timer."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        provider.embed(["hello"])
        assert provider._timer is None

    def test_model_stays_loaded_when_disabled(self) -> None:
        """With idle_timeout=0, model is never unloaded by timer."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        provider.embed(["hello"])
        assert provider._model is not None
        time.sleep(0.2)
        assert provider._model is not None
