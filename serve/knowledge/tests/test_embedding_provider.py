"""Tests for BgeM3EmbeddingProvider — AC coverage for task #151.

Verifies the contract described in the acceptance criteria:
  - embed(): returns list[list[float]], empty input returns []
  - embed_hybrid(): returns list[HybridEmbedding] with dense, sparse, colbert fields
  - Lazy loading: _model is None before first call, loaded after
  - unload(): _model set to None, timer cancelled
  - ImportError with actionable message when FlagEmbedding missing

BGE-M3 model is fully mocked via unittest.mock — no 3 GB download.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.protocol import HybridEmbedding

DENSE_DIM = 1024

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_flag(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace FlagEmbedding with a lightweight mock for the life of each test.

    Returns the mock model *instance* so tests can inspect calls if needed.
    """
    dense_mock = MagicMock()
    dense_mock.tolist.return_value = [0.1] * DENSE_DIM

    colbert_mock = MagicMock()
    colbert_mock.tolist.return_value = [[0.01] * 8] * 4  # 4 token vecs of dim 8

    fake_model_instance = MagicMock()
    fake_model_instance.encode.return_value = {
        "dense_vecs": [dense_mock],
        "lexical_weights": [{"42": 0.5, "100": 0.3}],
        "colbert_vecs": [colbert_mock],
    }

    fake_flag_module = MagicMock()
    fake_flag_module.BGEM3FlagModel.return_value = fake_model_instance

    monkeypatch.setitem(sys.modules, "FlagEmbedding", fake_flag_module)
    return fake_model_instance


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mock_flag")
class TestFromAC_BgeM3EmbeddingProvider:
    # ---------------------------------------------------------------- Happy

    def test_embed_returns_list_of_float_lists(self) -> None:
        """embed() returns list[list[float]] — one inner list per input text."""
        provider = BgeM3EmbeddingProvider()
        result = provider.embed(["hello world"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert all(isinstance(v, float) for v in result[0])

    def test_embed_hybrid_returns_hybrid_embeddings_with_all_fields(self) -> None:
        """embed_hybrid() returns list[HybridEmbedding] with dense, sparse, and colbert."""
        provider = BgeM3EmbeddingProvider()
        results = provider.embed_hybrid(["hello world"])
        assert isinstance(results, list)
        assert len(results) == 1
        emb = results[0]
        assert isinstance(emb, HybridEmbedding)
        assert isinstance(emb.dense, list)
        assert emb.sparse is not None
        assert isinstance(emb.sparse.indices, list)
        assert isinstance(emb.sparse.values, list)
        assert emb.colbert is not None
        assert isinstance(emb.colbert, list)

    # ------------------------------------------------------------------ Edge

    def test_embed_empty_input_returns_empty_list(self) -> None:
        """embed([]) returns an empty list — no model loaded."""
        provider = BgeM3EmbeddingProvider()
        result = provider.embed([])
        assert result == []

    def test_embed_hybrid_empty_input_returns_empty_list(self) -> None:
        """embed_hybrid([]) returns an empty list — no model loaded."""
        provider = BgeM3EmbeddingProvider()
        result = provider.embed_hybrid([])
        assert result == []

    # ----------------------------------------------------------------- Error

    def test_importerror_when_flag_embedding_missing(self) -> None:
        """embed() raises ImportError with actionable message when FlagEmbedding absent."""
        provider = BgeM3EmbeddingProvider()
        with patch.dict(sys.modules, {"FlagEmbedding": None}):
            provider._model = None  # force re-load  # noqa: SLF001
            with pytest.raises(ImportError, match="FlagEmbedding"):
                provider.embed(["test"])

    # --------------------------------------------------------------- Boundary

    def test_model_none_before_first_call(self) -> None:
        """_model is None immediately after construction — lazy loading not yet triggered."""
        provider = BgeM3EmbeddingProvider()
        assert provider._model is None  # noqa: SLF001

    def test_model_loaded_after_embed_call(self) -> None:
        """_model is not None after embed() is called — lazy loading succeeded."""
        provider = BgeM3EmbeddingProvider()
        assert provider._model is None  # noqa: SLF001
        provider.embed(["trigger load"])
        assert provider._model is not None  # noqa: SLF001

    def test_unload_sets_model_to_none(self) -> None:
        """unload() sets _model back to None, releasing the model reference."""
        provider = BgeM3EmbeddingProvider()
        provider.embed(["load model"])
        assert provider._model is not None  # noqa: SLF001
        provider.unload()
        assert provider._model is None  # noqa: SLF001

    def test_timer_cancelled_on_unload(self) -> None:
        """unload() cancels the idle-expiry timer and sets _timer to None."""
        provider = BgeM3EmbeddingProvider(idle_timeout=60.0)
        provider.embed(["load model"])
        assert provider._timer is not None  # noqa: SLF001
        provider.unload()
        assert provider._timer is None  # noqa: SLF001
