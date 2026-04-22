"""Tests for QdrantVectorStore — AC coverage for task #151.

Verifies the contract described in the acceptance criteria:
  - store_embedding: dense vector, HybridEmbedding
  - get_embedding: retrieves stored vector, None for missing ID
  - search_similar: top-k sorted by score, embedding_type filter, scopes filter
  - delete_embedding: True for existing, False for missing
  - _ensure_collection: lazy on first op, idempotent on repeat
  - ImportError with actionable message when qdrant-client missing

All tests use in-memory Qdrant (no Docker, no filesystem).
Run with: uv pip install 'owlbear-knowledge[qdrant]'
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

try:
    import qdrant_client as _qdrant_client  # noqa: F401
except ImportError:
    pytest.skip(
        "qdrant-client not installed — run: uv pip install 'owlbear-knowledge[qdrant]'",
        allow_module_level=True,
    )

from owlbear_knowledge.protocol import HybridEmbedding, SparseVector
from owlbear_knowledge.qdrant import DENSE_DIM, QdrantVectorStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dense(value: float = 0.1) -> list[float]:
    """Return a DENSE_DIM-dimensional dense vector filled with *value*."""
    return [value] * DENSE_DIM


def _hybrid(dense_value: float = 0.1) -> HybridEmbedding:
    """Return a HybridEmbedding with dense, sparse, and no colbert."""
    return HybridEmbedding(
        dense=_dense(dense_value),
        sparse=SparseVector(indices=[0, 1, 2], values=[0.5, 0.3, 0.2]),
        colbert=None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> QdrantVectorStore:
    """Fresh in-memory QdrantVectorStore for each test."""
    return QdrantVectorStore(location=":memory:")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_QdrantVectorStore:
    # ---------------------------------------------------------------- Happy

    def test_store_embedding_dense_and_retrieve(self, store: QdrantVectorStore) -> None:
        """store_embedding with a plain dense list; get_embedding returns the stored vector."""
        vec = _dense()
        store.store_embedding("doc1", vec, "document")
        result = store.get_embedding("doc1")
        assert result is not None
        assert len(result) == DENSE_DIM
        assert all(isinstance(v, float) for v in result)

    def test_store_embedding_hybrid_and_retrieve_dense(
        self, store: QdrantVectorStore
    ) -> None:
        """store_embedding with HybridEmbedding; get_embedding retrieves the dense component."""
        h = _hybrid()
        store.store_embedding("ent1", h, "entity")
        result = store.get_embedding("ent1")
        assert result is not None
        assert len(result) == DENSE_DIM

    def test_search_similar_returns_top_k_sorted_by_score(
        self, store: QdrantVectorStore
    ) -> None:
        """search_similar returns ≤ top_k results; results are sorted descending by score."""
        for i in range(5):
            store.store_embedding(f"doc{i}", _dense(0.1 * (i + 1)), "document")
        results = store.search_similar(_dense(), top_k=3)
        assert len(results) <= 3
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_similar_result_shape(self, store: QdrantVectorStore) -> None:
        """search_similar result tuples contain (entity_or_doc_id: str, score: float)."""
        store.store_embedding("my-doc", _dense(), "document")
        results = store.search_similar(_dense(), top_k=1)
        assert len(results) >= 1
        id_, score = results[0]
        assert id_ == "my-doc"
        assert isinstance(score, float)

    def test_delete_embedding_existing_returns_true(
        self, store: QdrantVectorStore
    ) -> None:
        """delete_embedding returns True for an ID that was successfully deleted."""
        store.store_embedding("doc1", _dense(), "document")
        assert store.delete_embedding("doc1") is True

    # ----------------------------------------------------------------- Edge

    def test_get_embedding_missing_id_returns_none(
        self, store: QdrantVectorStore
    ) -> None:
        """get_embedding returns None when the ID has never been stored."""
        assert store.get_embedding("nonexistent") is None

    def test_delete_embedding_missing_id_returns_false(
        self, store: QdrantVectorStore
    ) -> None:
        """delete_embedding returns False when the ID does not exist."""
        assert store.delete_embedding("ghost") is False

    def test_store_embedding_upsert_overwrites(self, store: QdrantVectorStore) -> None:
        """Re-storing the same ID replaces the previous vector (upsert semantics).

        Uses vectors with mass in different dimensions so the stored value is
        distinguishable after Qdrant's cosine normalisation.
          v1: first dim = 1, rest = 0  →  normalised result[0] ≈ 1, result[-1] ≈ 0
          v2: last  dim = 1, rest = 0  →  normalised result[0] ≈ 0, result[-1] ≈ 1
        """
        v1 = [1.0] + [0.0] * (DENSE_DIM - 1)
        v2 = [0.0] * (DENSE_DIM - 1) + [1.0]
        store.store_embedding("doc1", v1, "document")
        store.store_embedding("doc1", v2, "document")  # upsert
        result = store.get_embedding("doc1")
        assert result is not None
        # v2 was stored last: last component should be dominant
        assert result[-1] > 0.5, "expected v2 to overwrite v1; last dim should be high"
        # upsert must not duplicate: only one point per ID
        results = store.search_similar(v2, top_k=10)
        assert [id_ for id_, _ in results].count("doc1") == 1

    def test_search_similar_embedding_type_filter(
        self, store: QdrantVectorStore
    ) -> None:
        """search_similar with embedding_type='document' excludes entity embeddings."""
        store.store_embedding("doc1", _dense(), "document")
        store.store_embedding("ent1", _dense(), "entity")
        results = store.search_similar(_dense(), embedding_type="document")
        ids = [id_ for id_, _ in results]
        assert "doc1" in ids
        assert "ent1" not in ids

    def test_search_similar_scopes_filter(self, store: QdrantVectorStore) -> None:
        """search_similar with scopes=['global'] excludes embeddings in other scopes."""
        store.store_embedding("doc-global", _dense(), "document", scope="global")
        store.store_embedding("doc-private", _dense(), "document", scope="private")
        results = store.search_similar(_dense(), scopes=["global"])
        ids = [id_ for id_, _ in results]
        assert "doc-global" in ids
        assert "doc-private" not in ids

    # ----------------------------------------------------------------- Error

    def test_importerror_when_qdrant_client_missing(self) -> None:
        """QdrantVectorStore raises ImportError with actionable message when qdrant-client absent."""
        with (
            patch("owlbear_knowledge.qdrant.QdrantClient", None),
            pytest.raises(ImportError, match="qdrant-client"),
        ):
            QdrantVectorStore()

    # --------------------------------------------------------------- Boundary

    def test_ensure_collection_not_initialized_before_first_op(self) -> None:
        """_initialized is False on a fresh store — collection is created lazily."""
        fresh_store = QdrantVectorStore(location=":memory:")
        assert fresh_store._initialized is False  # noqa: SLF001

    def test_ensure_collection_initialized_after_store_embedding(
        self, store: QdrantVectorStore
    ) -> None:
        """_initialized becomes True after the first store_embedding call."""
        store.store_embedding("doc1", _dense(), "document")
        assert store._initialized is True  # noqa: SLF001

    def test_ensure_collection_idempotent_multiple_ops(
        self, store: QdrantVectorStore
    ) -> None:
        """Repeated store_embedding calls do not fail due to collection already existing."""
        for i in range(4):
            store.store_embedding(f"doc{i}", _dense(), "document")  # must not raise
        assert store.get_embedding("doc0") is not None
        assert store.get_embedding("doc3") is not None
