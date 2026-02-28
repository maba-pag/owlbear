"""Tests for owlbear.memory.knowledge.embeddings."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from owlbear.memory.knowledge.embeddings import (
    BgeM3EmbeddingProvider,
    EmbeddingProvider,
)
from owlbear.memory.knowledge.protocol import HybridEmbedding, SparseVector

# -- EmbeddingProvider protocol ----------------------------------------------


class TestEmbeddingProvider:
    """EmbeddingProvider is a runtime-checkable Protocol with embed()."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """isinstance() works on EmbeddingProvider (runtime_checkable)."""
        assert isinstance(BgeM3EmbeddingProvider(), EmbeddingProvider)

    def test_protocol_defines_embed_method(self) -> None:
        """Protocol has an 'embed' callable attribute."""
        assert hasattr(EmbeddingProvider, "embed")

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """An object without embed() is not an EmbeddingProvider."""

        class NotAProvider:
            pass

        assert not isinstance(NotAProvider(), EmbeddingProvider)


class TestOldSymbolsRemoved:
    """FastEmbedProvider, DEFAULT_MODEL, DEFAULT_DIMENSION no longer exist."""

    def test_no_fast_embed_provider(self) -> None:
        """FastEmbedProvider class is deleted from the module."""
        from owlbear.memory.knowledge import embeddings

        assert not hasattr(embeddings, "FastEmbedProvider")

    def test_no_default_model(self) -> None:
        """DEFAULT_MODEL constant is deleted from the module."""
        from owlbear.memory.knowledge import embeddings

        assert not hasattr(embeddings, "DEFAULT_MODEL")

    def test_no_default_dimension(self) -> None:
        """DEFAULT_DIMENSION constant is deleted from the module."""
        from owlbear.memory.knowledge import embeddings

        assert not hasattr(embeddings, "DEFAULT_DIMENSION")


# -- BgeM3EmbeddingProvider helpers ------------------------------------------


def _make_bge_encode_output(texts: list[str], dim: int = 1024) -> dict[str, object]:
    """Build a fake BGEM3FlagModel.encode() return dict."""
    n = len(texts)
    rng = np.random.default_rng(42)
    dense_vecs = rng.random((n, dim)).astype(np.float32)
    lexical_weights: list[dict[str, float]] = [{"101": 0.5, "202": 0.3} for _ in range(n)]
    colbert_vecs: list[np.ndarray] = [rng.random((5, dim)).astype(np.float32) for _ in range(n)]
    return {
        "dense_vecs": dense_vecs,
        "lexical_weights": lexical_weights,
        "colbert_vecs": colbert_vecs,
    }


@pytest.fixture
def mock_flag_module():
    """Inject a mock FlagEmbedding module into sys.modules.

    FlagEmbedding is an optional dependency not installed in the test
    environment, so we mock the entire module.
    """
    mock_module = MagicMock()
    with patch.dict(sys.modules, {"FlagEmbedding": mock_module}):
        yield mock_module


# -- BgeM3EmbeddingProvider protocol conformance -----------------------------


class TestBgeM3ProviderProtocol:
    """BgeM3EmbeddingProvider satisfies the EmbeddingProvider protocol."""

    def test_isinstance_embedding_provider(self) -> None:
        provider = BgeM3EmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)


# -- BgeM3EmbeddingProvider defaults -----------------------------------------


class TestBgeM3ProviderDefaults:
    """BgeM3EmbeddingProvider default construction."""

    def test_default_model_name(self) -> None:
        provider = BgeM3EmbeddingProvider()
        assert provider.model_name == "BAAI/bge-m3"

    def test_default_batch_size(self) -> None:
        provider = BgeM3EmbeddingProvider()
        assert provider.batch_size == 16

    def test_custom_model_name(self) -> None:
        provider = BgeM3EmbeddingProvider(model_name="custom/m3")
        assert provider.model_name == "custom/m3"

    def test_custom_batch_size(self) -> None:
        provider = BgeM3EmbeddingProvider(batch_size=32)
        assert provider.batch_size == 32


# -- BgeM3EmbeddingProvider.embed() ------------------------------------------


class TestBgeM3ProviderEmbed:
    """BgeM3EmbeddingProvider.embed() returns dense vectors only."""

    def test_embed_empty_returns_empty(self, mock_flag_module: MagicMock) -> None:
        provider = BgeM3EmbeddingProvider()
        result = provider.embed([])
        assert result == []
        mock_flag_module.BGEM3FlagModel.assert_not_called()

    def test_embed_single_text(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed(["hello"])

        assert len(result) == 1
        assert len(result[0]) == 1024
        assert all(isinstance(v, float) for v in result[0])

    def test_embed_multiple_texts(self, mock_flag_module: MagicMock) -> None:
        texts = ["hello", "world", "test"]
        output = _make_bge_encode_output(texts)
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed(texts)

        assert len(result) == 3
        for vec in result:
            assert len(vec) == 1024
            assert all(isinstance(v, float) for v in vec)

    def test_embed_returns_plain_lists(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["test"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed(["test"])

        assert isinstance(result, list)
        assert isinstance(result[0], list)


# -- BgeM3EmbeddingProvider.embed_hybrid() -----------------------------------


class TestBgeM3ProviderEmbedHybrid:
    """embed_hybrid() returns HybridEmbedding with dense, sparse, colbert."""

    def test_embed_hybrid_empty_returns_empty(self, mock_flag_module: MagicMock) -> None:
        provider = BgeM3EmbeddingProvider()
        result = provider.embed_hybrid([])
        assert result == []
        mock_flag_module.BGEM3FlagModel.assert_not_called()

    def test_embed_hybrid_single_text(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed_hybrid(["hello"])

        assert len(result) == 1
        emb = result[0]
        assert isinstance(emb, HybridEmbedding)

    def test_embed_hybrid_dense_field(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed_hybrid(["hello"])
        emb = result[0]

        assert len(emb.dense) == 1024
        assert all(isinstance(v, float) for v in emb.dense)

    def test_embed_hybrid_sparse_field(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed_hybrid(["hello"])
        emb = result[0]

        assert emb.sparse is not None
        assert isinstance(emb.sparse, SparseVector)
        assert emb.sparse.indices == [101, 202]
        assert emb.sparse.values == [0.5, 0.3]

    def test_embed_hybrid_colbert_field(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed_hybrid(["hello"])
        emb = result[0]

        assert emb.colbert is not None
        assert len(emb.colbert) == 5  # T-1 tokens
        assert all(len(row) == 1024 for row in emb.colbert)

    def test_embed_hybrid_multiple_texts(self, mock_flag_module: MagicMock) -> None:
        texts = ["a", "b"]
        output = _make_bge_encode_output(texts)
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        result = provider.embed_hybrid(texts)

        assert len(result) == 2
        for emb in result:
            assert isinstance(emb, HybridEmbedding)
            assert emb.sparse is not None
            assert emb.colbert is not None


# -- BgeM3EmbeddingProvider lazy loading -------------------------------------


class TestBgeM3ProviderLazyLoading:
    """Model is only created on first embed()/embed_hybrid() call."""

    def test_model_is_none_after_construction(self) -> None:
        provider = BgeM3EmbeddingProvider()
        assert provider._model is None

    def test_model_created_on_first_embed(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        mock_flag_module.BGEM3FlagModel.assert_not_called()

        provider.embed(["hello"])
        mock_flag_module.BGEM3FlagModel.assert_called_once()

    def test_model_created_on_first_embed_hybrid(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        mock_flag_module.BGEM3FlagModel.assert_not_called()

        provider.embed_hybrid(["hello"])
        mock_flag_module.BGEM3FlagModel.assert_called_once()

    def test_model_reused_on_subsequent_calls(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["a"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        provider.embed(["a"])
        mock_instance.encode.return_value = _make_bge_encode_output(["b"])
        provider.embed(["b"])

        mock_flag_module.BGEM3FlagModel.assert_called_once()


# -- BgeM3EmbeddingProvider.unload() -----------------------------------------


class TestBgeM3ProviderUnload:
    """unload() releases the model and frees memory."""

    def test_unload_sets_model_to_none(self, mock_flag_module: MagicMock) -> None:
        output = _make_bge_encode_output(["hello"])
        mock_instance = MagicMock()
        mock_instance.encode.return_value = output
        mock_flag_module.BGEM3FlagModel.return_value = mock_instance

        provider = BgeM3EmbeddingProvider()
        provider.embed(["hello"])
        assert provider._model is not None

        provider.unload()
        assert provider._model is None

    def test_unload_on_fresh_provider_is_safe(self) -> None:
        """unload() on a never-used provider doesn't raise."""
        provider = BgeM3EmbeddingProvider()
        provider.unload()  # should not raise
        assert provider._model is None


# -- BgeM3EmbeddingProvider ImportError --------------------------------------


class TestBgeM3ProviderImportError:
    """ImportError when FlagEmbedding is not installed."""

    def test_import_error_on_embed(self) -> None:
        """embed() raises ImportError with helpful message when FlagEmbedding missing."""
        provider = BgeM3EmbeddingProvider()
        # Ensure FlagEmbedding is NOT in sys.modules (it shouldn't be in CI)
        with (
            patch.dict(sys.modules, {"FlagEmbedding": None}),
            pytest.raises(ImportError, match="FlagEmbedding"),
        ):
            provider.embed(["hello"])

    def test_import_error_on_embed_hybrid(self) -> None:
        """embed_hybrid() raises ImportError with helpful message when FlagEmbedding missing."""
        provider = BgeM3EmbeddingProvider()
        with (
            patch.dict(sys.modules, {"FlagEmbedding": None}),
            pytest.raises(ImportError, match="FlagEmbedding"),
        ):
            provider.embed_hybrid(["hello"])
