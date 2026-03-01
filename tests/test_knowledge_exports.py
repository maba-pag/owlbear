"""Tests for owlbear.memory.knowledge public exports (task #290)."""

from __future__ import annotations

import owlbear.memory.knowledge as pkg


class TestPhase9Exports:
    """All 11 new phase-9 symbols must be importable from the package."""

    def test_new_symbols_importable(self) -> None:
        new_symbols = [
            "BgeM3EmbeddingProvider",
            "Chunk",
            "DocumentStatus",
            "EmbeddingProvider",
            "GraphBuildResult",
            "IngestPipeline",
            "IngestResult",
            "IntraDocGraphBuilder",
            "TextChunker",
            "compute_content_hash",
            "init_db",
        ]
        for name in new_symbols:
            assert hasattr(pkg, name), f"{name!r} not importable from owlbear.memory.knowledge"

    def test_new_symbols_in_all(self) -> None:
        new_symbols = {
            "BgeM3EmbeddingProvider",
            "Chunk",
            "DocumentStatus",
            "EmbeddingProvider",
            "GraphBuildResult",
            "IngestPipeline",
            "IngestResult",
            "IntraDocGraphBuilder",
            "TextChunker",
            "compute_content_hash",
            "init_db",
        }
        assert new_symbols.issubset(set(pkg.__all__))

    def test_existing_symbols_preserved(self) -> None:
        existing = [
            "Document",
            "Edge",
            "Embedding",
            "Entity",
            "EntityExtractor",
            "EntityType",
            "ExtractionResult",
            "GraphStore",
            "HybridEmbedding",
            "QdrantVectorStore",
            "RelationType",
            "SparseVector",
            "VectorStoreProtocol",
        ]
        for name in existing:
            assert name in pkg.__all__, f"existing symbol {name!r} missing from __all__"

    def test_all_sorted_alphabetically(self) -> None:
        assert pkg.__all__ == sorted(pkg.__all__), "__all__ is not alphabetically sorted"
