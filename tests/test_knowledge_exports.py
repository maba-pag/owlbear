"""Tests for owlbear.memory.knowledge public exports (task #290, #546)."""

from __future__ import annotations

import subprocess
import sys

import owlbear.memory.knowledge as pkg


class TestFromAC_QdrantNotEagerlyLoaded:  # noqa: N801
    """Importing the knowledge package must not eagerly pull in qdrant (#546)."""

    def test_knowledge_import_does_not_load_qdrant(self) -> None:
        """After `import owlbear.memory.knowledge`, neither qdrant_client nor the
        qdrant submodule should appear in sys.modules."""
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-c",
                (
                    "import sys; import owlbear.memory.knowledge; "
                    "assert 'qdrant_client' not in sys.modules, "
                    "'qdrant_client eagerly loaded'; "
                    "assert 'owlbear.memory.knowledge.qdrant' not in sys.modules, "
                    "'qdrant submodule eagerly loaded'"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"Import side-effect check failed:\n{result.stderr}"

    def test_qdrant_vector_store_not_in_all(self) -> None:
        """QdrantVectorStore must not appear in the package __all__."""
        assert "QdrantVectorStore" not in pkg.__all__


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
            "RelationType",
            "SparseVector",
            "VectorStoreProtocol",
        ]
        for name in existing:
            assert name in pkg.__all__, f"existing symbol {name!r} missing from __all__"

    def test_all_sorted_alphabetically(self) -> None:
        assert pkg.__all__ == sorted(pkg.__all__), "__all__ is not alphabetically sorted"
