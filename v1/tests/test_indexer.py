"""Tests for benchmarks.indexer — embedding + indexing pipeline.

Verifies cache logic, hash computation, and store population without
loading the real bge-m3 model (all heavy deps are mocked).

Task: #378
"""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

from owlbear.memory.knowledge.protocol import HybridEmbedding, SparseVector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_corpus(n: int = 3) -> dict[str, str]:
    """Build a tiny corpus dict for testing."""
    return {f"doc-{i}": f"Text for document {i}." for i in range(n)}


def _make_embedding(dim: int = 1024) -> HybridEmbedding:
    """Create a minimal HybridEmbedding stub."""
    return HybridEmbedding(
        dense=[0.1] * dim,
        sparse=SparseVector(indices=[1, 2], values=[0.5, 0.3]),
        colbert=[[0.1] * dim],
    )


def _expected_hash(corpus: dict[str, str]) -> str:
    """Reproduce the expected corpus-key hash."""
    key_str = "\n".join(sorted(corpus.keys()))
    return hashlib.sha256(key_str.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCorpusHash:
    """Unit tests for the corpus hash helper."""

    def test_deterministic(self) -> None:
        """Same corpus produces the same hash on repeated calls."""
        from tests.benchmarks.indexer import _corpus_hash

        corpus = _make_corpus()
        assert _corpus_hash(corpus) == _corpus_hash(corpus)

    def test_changes_with_different_keys(self) -> None:
        """Different corpus keys produce a different hash."""
        from tests.benchmarks.indexer import _corpus_hash

        c1 = _make_corpus(3)
        c2 = _make_corpus(5)
        assert _corpus_hash(c1) != _corpus_hash(c2)

    def test_matches_expected_algorithm(self) -> None:
        """Hash matches sha256 of sorted keys joined by newlines."""
        from tests.benchmarks.indexer import _corpus_hash

        corpus = _make_corpus(4)
        assert _corpus_hash(corpus) == _expected_hash(corpus)


class TestEmbedAndIndex:
    """Unit tests for embed_and_index with mocked dependencies."""

    @patch("tests.benchmarks.indexer.QdrantVectorStore")
    @patch("tests.benchmarks.indexer.BgeM3EmbeddingProvider")
    def test_cache_miss_embeds_and_stores(
        self,
        mock_provider_cls: MagicMock,
        mock_store_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """On cache miss, embeds corpus and writes cache file."""
        from tests.benchmarks.indexer import embed_and_index

        corpus = _make_corpus(3)
        embeddings = [_make_embedding() for _ in corpus]

        mock_provider = MagicMock()
        mock_provider.embed_hybrid.return_value = embeddings
        mock_provider_cls.return_value = mock_provider

        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        result = embed_and_index(corpus, cache_dir=tmp_path)

        # Provider was called with all doc texts
        mock_provider.embed_hybrid.assert_called_once_with(list(corpus.values()))
        # Store received one call per doc
        assert mock_store.store_embedding.call_count == len(corpus)
        # Cache file was created
        assert (tmp_path / "embeddings.pkl").exists()
        # Returns the store
        assert result is mock_store

    @patch("tests.benchmarks.indexer.QdrantVectorStore")
    @patch("tests.benchmarks.indexer.BgeM3EmbeddingProvider")
    def test_cache_hit_skips_embedding(
        self,
        mock_provider_cls: MagicMock,
        mock_store_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When valid cache exists, skips embedding and loads from disk."""
        from tests.benchmarks.indexer import _corpus_hash, embed_and_index

        corpus = _make_corpus(3)
        doc_ids = list(corpus.keys())
        embeddings = [_make_embedding() for _ in corpus]
        cache_data = {
            "hash": _corpus_hash(corpus),
            "embeddings": dict(zip(doc_ids, embeddings, strict=True)),
        }

        cache_file = tmp_path / "embeddings.pkl"
        with cache_file.open("wb") as f:
            pickle.dump(cache_data, f)

        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        result = embed_and_index(corpus, cache_dir=tmp_path)

        # Provider never instantiated since cache hit
        mock_provider_cls.assert_not_called()
        # Store still receives embeddings from cache
        assert mock_store.store_embedding.call_count == len(corpus)
        assert result is mock_store

    @patch("tests.benchmarks.indexer.QdrantVectorStore")
    @patch("tests.benchmarks.indexer.BgeM3EmbeddingProvider")
    def test_cache_invalidation_on_hash_mismatch(
        self,
        mock_provider_cls: MagicMock,
        mock_store_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Stale cache (wrong hash) triggers re-embedding."""
        from tests.benchmarks.indexer import embed_and_index

        corpus = _make_corpus(3)
        embeddings = [_make_embedding() for _ in corpus]

        # Write cache with wrong hash
        stale_cache = {
            "hash": "stale-hash-value",
            "embeddings": {"old-doc": _make_embedding()},
        }
        cache_file = tmp_path / "embeddings.pkl"
        with cache_file.open("wb") as f:
            pickle.dump(stale_cache, f)

        mock_provider = MagicMock()
        mock_provider.embed_hybrid.return_value = embeddings
        mock_provider_cls.return_value = mock_provider

        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        embed_and_index(corpus, cache_dir=tmp_path)

        # Provider was called because cache was stale
        mock_provider.embed_hybrid.assert_called_once()

    @patch("tests.benchmarks.indexer.QdrantVectorStore")
    @patch("tests.benchmarks.indexer.BgeM3EmbeddingProvider")
    def test_creates_cache_dir(
        self,
        mock_provider_cls: MagicMock,
        mock_store_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Creates the cache directory if it doesn't exist."""
        from tests.benchmarks.indexer import embed_and_index

        corpus = _make_corpus(2)
        embeddings = [_make_embedding() for _ in corpus]

        mock_provider = MagicMock()
        mock_provider.embed_hybrid.return_value = embeddings
        mock_provider_cls.return_value = mock_provider
        mock_store_cls.return_value = MagicMock()

        nested = tmp_path / "sub" / "dir"
        embed_and_index(corpus, cache_dir=nested)

        assert nested.exists()
        assert (nested / "embeddings.pkl").exists()

    @patch("tests.benchmarks.indexer.QdrantVectorStore")
    @patch("tests.benchmarks.indexer.BgeM3EmbeddingProvider")
    def test_store_embedding_called_with_correct_args(
        self,
        mock_provider_cls: MagicMock,
        mock_store_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Each doc embedding is stored with doc_id, embedding, 'document'."""
        from tests.benchmarks.indexer import embed_and_index

        corpus = {"d1": "text 1", "d2": "text 2"}
        emb1, emb2 = _make_embedding(), _make_embedding()

        mock_provider = MagicMock()
        mock_provider.embed_hybrid.return_value = [emb1, emb2]
        mock_provider_cls.return_value = mock_provider

        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        embed_and_index(corpus, cache_dir=tmp_path)

        calls = mock_store.store_embedding.call_args_list
        assert len(calls) == 2
        # Check first call positional args
        for call in calls:
            assert call[0][2] == "document"  # embedding_type

    @patch("tests.benchmarks.indexer.QdrantVectorStore")
    @patch("tests.benchmarks.indexer.BgeM3EmbeddingProvider")
    def test_provider_unloaded_after_embedding(
        self,
        mock_provider_cls: MagicMock,
        mock_store_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Provider.unload() is called after embedding to free memory."""
        from tests.benchmarks.indexer import embed_and_index

        corpus = _make_corpus(2)
        embeddings = [_make_embedding() for _ in corpus]

        mock_provider = MagicMock()
        mock_provider.embed_hybrid.return_value = embeddings
        mock_provider_cls.return_value = mock_provider
        mock_store_cls.return_value = MagicMock()

        embed_and_index(corpus, cache_dir=tmp_path)

        mock_provider.unload.assert_called_once()
