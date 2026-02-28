"""Tests for QdrantVectorStore — Qdrant-backed vector storage.

Covers all VectorStoreProtocol methods plus the extra
``delete_by_document_id`` method.  Uses QdrantClient(':memory:')
for test isolation.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from owlbear.memory.knowledge.protocol import (
    HybridEmbedding,
    SparseVector,
    VectorStoreProtocol,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIM = 1024


def _dense_vec(seed: float = 0.1) -> list[float]:
    """Return a DIM-length dense vector with a simple pattern."""
    return [seed + i * 0.001 for i in range(DIM)]


def _normalize(v: list[float]) -> list[float]:
    """L2-normalize a vector (Qdrant normalizes COSINE vectors internally)."""
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v] if norm > 0 else v


def _hybrid_embedding(seed: float = 0.1) -> HybridEmbedding:
    """Return a full hybrid embedding (dense + sparse + ColBERT)."""
    return HybridEmbedding(
        dense=_dense_vec(seed),
        sparse=SparseVector(indices=[0, 10, 100], values=[0.5, 0.8, 0.3]),
        colbert=[_dense_vec(seed + 0.01), _dense_vec(seed + 0.02)],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store():
    """Create a QdrantVectorStore backed by an in-memory client."""
    from owlbear.memory.knowledge.qdrant import QdrantVectorStore

    return QdrantVectorStore(location=":memory:")


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """QdrantVectorStore satisfies VectorStoreProtocol."""

    def test_isinstance_check(self, store) -> None:
        assert isinstance(store, VectorStoreProtocol)


# ---------------------------------------------------------------------------
# store_embedding
# ---------------------------------------------------------------------------


class TestStoreEmbedding:
    """store_embedding stores vectors correctly."""

    def test_store_dense_only(self, store) -> None:
        """Storing a list[float] embedding stores dense vector only."""
        vec = _dense_vec(0.2)
        store.store_embedding("entity-1", vec, "entity", "global")

        # Verify it's findable
        result = store.get_embedding("entity-1")
        assert result is not None
        assert len(result) == DIM

    def test_store_hybrid_all_vectors(self, store) -> None:
        """Storing a HybridEmbedding stores dense, sparse, and ColBERT."""
        hybrid = _hybrid_embedding(0.3)
        store.store_embedding("doc-1", hybrid, "document", "project-a")

        # Verify dense vector is retrievable
        result = store.get_embedding("doc-1")
        assert result is not None
        assert len(result) == DIM

    def test_store_upsert_semantics(self, store) -> None:
        """Storing the same ID twice overwrites the previous embedding."""
        vec1 = _dense_vec(0.1)
        vec2 = _dense_vec(0.9)
        store.store_embedding("e1", vec1, "entity")
        store.store_embedding("e1", vec2, "entity")

        result = store.get_embedding("e1")
        assert result is not None
        # The vector should be close to vec2, not vec1
        expected = _normalize(vec2)
        assert abs(result[0] - expected[0]) < 0.01


# ---------------------------------------------------------------------------
# search_similar — dense only
# ---------------------------------------------------------------------------


class TestSearchSimilarDense:
    """search_similar with list[float] queries uses dense search."""

    def test_returns_results_by_dense_similarity(self, store) -> None:
        vec_a = _dense_vec(0.1)
        vec_b = _dense_vec(0.5)
        vec_c = _dense_vec(0.9)
        store.store_embedding("a", vec_a, "entity")
        store.store_embedding("b", vec_b, "entity")
        store.store_embedding("c", vec_c, "entity")

        # Query close to vec_a
        results = store.search_similar(vec_a, top_k=3)
        assert len(results) >= 1
        # First result should be 'a' (exact match)
        ids = [r[0] for r in results]
        assert ids[0] == "a"

    def test_top_k_limits_results(self, store) -> None:
        for i in range(10):
            store.store_embedding(f"e{i}", _dense_vec(0.1 * i + 0.01), "entity")

        results = store.search_similar(_dense_vec(0.1), top_k=3)
        assert len(results) <= 3

    def test_filters_by_embedding_type(self, store) -> None:
        store.store_embedding("entity-1", _dense_vec(0.1), "entity")
        store.store_embedding("doc-1", _dense_vec(0.11), "document")

        # Search only entities
        results = store.search_similar(_dense_vec(0.1), top_k=5, embedding_type="entity")
        ids = [r[0] for r in results]
        assert "entity-1" in ids
        assert "doc-1" not in ids

    def test_filters_by_scope(self, store) -> None:
        store.store_embedding("e1", _dense_vec(0.1), "entity", "project-a")
        store.store_embedding("e2", _dense_vec(0.11), "entity", "project-b")

        results = store.search_similar(_dense_vec(0.1), top_k=5, scopes=["project-a"])
        ids = [r[0] for r in results]
        assert "e1" in ids
        assert "e2" not in ids


# ---------------------------------------------------------------------------
# search_similar — hybrid
# ---------------------------------------------------------------------------


class TestSearchSimilarHybrid:
    """search_similar with HybridEmbedding uses prefetch+rescore."""

    def test_returns_hybrid_scored_results(self, store) -> None:
        hybrid_a = _hybrid_embedding(0.1)
        hybrid_b = _hybrid_embedding(0.5)
        store.store_embedding("ha", hybrid_a, "entity")
        store.store_embedding("hb", hybrid_b, "entity")

        results = store.search_similar(hybrid_a, top_k=2)
        assert len(results) >= 1
        ids = [r[0] for r in results]
        assert "ha" in ids

    def test_hybrid_filters_by_scope(self, store) -> None:
        hybrid = _hybrid_embedding(0.2)
        store.store_embedding("h1", hybrid, "entity", "scope-x")
        store.store_embedding("h2", _hybrid_embedding(0.21), "entity", "scope-y")

        results = store.search_similar(hybrid, top_k=5, scopes=["scope-x"])
        ids = [r[0] for r in results]
        assert "h1" in ids
        assert "h2" not in ids


# ---------------------------------------------------------------------------
# get_embedding
# ---------------------------------------------------------------------------


class TestGetEmbedding:
    """get_embedding returns dense vector or None."""

    def test_returns_dense_vector(self, store) -> None:
        vec = _dense_vec(0.3)
        store.store_embedding("e1", vec, "entity")

        result = store.get_embedding("e1")
        assert result is not None
        assert len(result) == DIM
        # Qdrant normalizes COSINE vectors — compare normalized values
        expected = _normalize(vec)
        for got, exp in zip(result[:5], expected[:5], strict=False):
            assert abs(got - exp) < 1e-4

    def test_returns_none_for_unknown(self, store) -> None:
        result = store.get_embedding("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# delete_embedding
# ---------------------------------------------------------------------------


class TestDeleteEmbedding:
    """delete_embedding removes points and returns status."""

    def test_returns_true_for_existing(self, store) -> None:
        store.store_embedding("e1", _dense_vec(0.1), "entity")
        assert store.delete_embedding("e1") is True
        assert store.get_embedding("e1") is None

    def test_returns_false_for_unknown(self, store) -> None:
        assert store.delete_embedding("nonexistent") is False


# ---------------------------------------------------------------------------
# delete_by_document_id
# ---------------------------------------------------------------------------


class TestDeleteByDocumentId:
    """delete_by_document_id removes all points with matching document_id."""

    def test_removes_all_matching_points(self, store) -> None:
        # Store multiple embeddings referencing same document_id
        store.store_embedding("doc-1-chunk-0", _dense_vec(0.1), "document")
        store.store_embedding("doc-1-chunk-1", _dense_vec(0.2), "document")
        store.store_embedding("doc-2-chunk-0", _dense_vec(0.3), "document")

        removed = store.delete_by_document_id("doc-1")
        assert removed >= 2

        # doc-1 chunks gone
        assert store.get_embedding("doc-1-chunk-0") is None
        assert store.get_embedding("doc-1-chunk-1") is None
        # doc-2 still present
        assert store.get_embedding("doc-2-chunk-0") is not None

    def test_no_matches_returns_zero(self, store) -> None:
        store.store_embedding("e1", _dense_vec(0.1), "entity")
        assert store.delete_by_document_id("nonexistent") == 0


# ---------------------------------------------------------------------------
# Recency weight (temporal boost)
# ---------------------------------------------------------------------------


class TestRecencyWeight:
    """search_similar with recency_weight > 0 applies temporal boost."""

    def test_recency_boost_applied(self, store) -> None:
        store.store_embedding("e1", _dense_vec(0.1), "entity")
        store.store_embedding("e2", _dense_vec(0.11), "entity")

        results = store.search_similar(
            _dense_vec(0.1),
            top_k=5,
            recency_weight=0.1,
        )
        assert len(results) >= 1
        # Scores should be positive (similarity + recency boost)
        for _id, score in results:
            assert score > 0


# ---------------------------------------------------------------------------
# Hybrid search fallback (no ColBERT)
# ---------------------------------------------------------------------------


class TestHybridFallback:
    """Hybrid search falls back to dense when ColBERT is absent."""

    def test_hybrid_without_colbert(self, store) -> None:
        """HybridEmbedding with sparse but no ColBERT uses dense fallback."""
        hybrid = HybridEmbedding(
            dense=_dense_vec(0.2),
            sparse=SparseVector(indices=[0, 10], values=[0.5, 0.8]),
            colbert=None,
        )
        store.store_embedding("h1", hybrid, "entity")

        query = HybridEmbedding(
            dense=_dense_vec(0.2),
            sparse=SparseVector(indices=[0, 10], values=[0.5, 0.8]),
            colbert=None,
        )
        results = store.search_similar(query, top_k=5)
        assert len(results) >= 1
        assert results[0][0] == "h1"


# ---------------------------------------------------------------------------
# _compute_recency_score
# ---------------------------------------------------------------------------


class TestComputeRecencyScore:
    """Unit tests for _compute_recency_score helper."""

    def test_recent_item_scores_near_one(self) -> None:
        from owlbear.memory.knowledge.qdrant import _compute_recency_score

        now_iso = datetime.now(UTC).isoformat()
        score = _compute_recency_score(now_iso, decay_rate=0.001)
        assert score > 0.99

    def test_naive_datetime_handled(self) -> None:
        from owlbear.memory.knowledge.qdrant import _compute_recency_score

        # Naive datetime without timezone info
        naive_iso = "2020-01-01T00:00:00"
        score = _compute_recency_score(naive_iso, decay_rate=0.001)
        assert 0.0 <= score <= 1.0

    def test_high_importance_slows_decay(self) -> None:
        from owlbear.memory.knowledge.qdrant import _compute_recency_score

        old_iso = "2020-01-01T00:00:00+00:00"
        score_low = _compute_recency_score(old_iso, 0.001, importance=0.0)
        score_high = _compute_recency_score(old_iso, 0.001, importance=0.9)
        assert score_high > score_low


# ---------------------------------------------------------------------------
# ImportError guard
# ---------------------------------------------------------------------------


class TestImportGuard:
    """QdrantVectorStore raises ImportError when qdrant-client missing."""

    def test_raises_when_qdrant_unavailable(self) -> None:
        import unittest.mock

        with unittest.mock.patch(
            "owlbear.memory.knowledge.qdrant.QdrantClient",
            None,
        ):
            from owlbear.memory.knowledge.qdrant import QdrantVectorStore

            with pytest.raises(ImportError, match="qdrant-client"):
                QdrantVectorStore()


# ---------------------------------------------------------------------------
# Lazy collection creation
# ---------------------------------------------------------------------------


class TestLazyCollectionInit:
    """Collection is auto-created on first operation."""

    def test_collection_created_on_first_store(self) -> None:
        from owlbear.memory.knowledge.qdrant import QdrantVectorStore

        store = QdrantVectorStore(location=":memory:")
        # No operations yet — collection should not exist
        # First store should create it
        store.store_embedding("e1", _dense_vec(0.1), "entity")
        result = store.get_embedding("e1")
        assert result is not None

    def test_collection_created_on_first_search(self) -> None:
        from owlbear.memory.knowledge.qdrant import QdrantVectorStore

        store = QdrantVectorStore(location=":memory:")
        # Search on empty store should work (returns empty)
        results = store.search_similar(_dense_vec(0.1), top_k=5)
        assert results == []
