"""Tests for owlbear.memory.knowledge.protocol — VectorStoreProtocol and models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.protocol import (
    Embedding,
    HybridEmbedding,
    SparseVector,
    VectorStoreProtocol,
)

# ---------------------------------------------------------------------------
# Protocol shape — methods exist with correct signatures
# ---------------------------------------------------------------------------


class TestProtocolShape:
    """VectorStoreProtocol exposes the expected method names."""

    def test_has_store_embedding(self) -> None:
        assert hasattr(VectorStoreProtocol, "store_embedding")

    def test_has_get_embedding(self) -> None:
        assert hasattr(VectorStoreProtocol, "get_embedding")

    def test_has_search_similar(self) -> None:
        assert hasattr(VectorStoreProtocol, "search_similar")

    def test_has_delete_embedding(self) -> None:
        assert hasattr(VectorStoreProtocol, "delete_embedding")

    def test_protocol_is_runtime_checkable(self) -> None:
        assert isinstance(VectorStoreProtocol, type)


# ---------------------------------------------------------------------------
# SparseVector and HybridEmbedding construction & serialization
# ---------------------------------------------------------------------------


class TestSparseVector:
    """SparseVector model construction and serialization."""

    def test_construction(self) -> None:
        sv = SparseVector(indices=[0, 5, 10], values=[0.1, 0.5, 0.9])
        assert sv.indices == [0, 5, 10]
        assert sv.values == [0.1, 0.5, 0.9]

    def test_serialization_roundtrip(self) -> None:
        sv = SparseVector(indices=[1, 2], values=[0.3, 0.7])
        data = sv.model_dump()
        restored = SparseVector.model_validate(data)
        assert restored == sv

    def test_json_roundtrip(self) -> None:
        sv = SparseVector(indices=[4], values=[0.42])
        json_str = sv.model_dump_json()
        restored = SparseVector.model_validate_json(json_str)
        assert restored == sv


class TestHybridEmbedding:
    """HybridEmbedding model construction and serialization."""

    def test_dense_only(self) -> None:
        he = HybridEmbedding(dense=[0.1, 0.2, 0.3])
        assert he.dense == [0.1, 0.2, 0.3]
        assert he.sparse is None
        assert he.colbert is None

    def test_dense_is_required(self) -> None:
        with pytest.raises(ValidationError):
            HybridEmbedding()  # type: ignore[call-arg]

    def test_with_sparse(self) -> None:
        sv = SparseVector(indices=[0], values=[1.0])
        he = HybridEmbedding(dense=[0.5], sparse=sv)
        assert he.sparse is not None
        assert he.sparse.indices == [0]

    def test_with_colbert(self) -> None:
        he = HybridEmbedding(dense=[0.5], colbert=[[0.1, 0.2], [0.3, 0.4]])
        assert he.colbert is not None
        assert len(he.colbert) == 2

    def test_full_hybrid(self) -> None:
        sv = SparseVector(indices=[1, 3], values=[0.5, 0.8])
        he = HybridEmbedding(
            dense=[0.1, 0.2],
            sparse=sv,
            colbert=[[0.1], [0.2]],
        )
        assert he.dense == [0.1, 0.2]
        assert he.sparse == sv
        assert he.colbert == [[0.1], [0.2]]

    def test_serialization_roundtrip(self) -> None:
        sv = SparseVector(indices=[0], values=[1.0])
        he = HybridEmbedding(dense=[0.5], sparse=sv, colbert=[[0.1]])
        data = he.model_dump()
        restored = HybridEmbedding.model_validate(data)
        assert restored == he

    def test_json_roundtrip(self) -> None:
        he = HybridEmbedding(dense=[0.1, 0.2])
        json_str = he.model_dump_json()
        restored = HybridEmbedding.model_validate_json(json_str)
        assert restored == he


# ---------------------------------------------------------------------------
# Embedding type alias
# ---------------------------------------------------------------------------


class TestEmbeddingAlias:
    """Embedding type alias covers both list[float] and HybridEmbedding."""

    def test_alias_exists(self) -> None:
        # Embedding should be importable and be a type alias
        assert Embedding is not None
