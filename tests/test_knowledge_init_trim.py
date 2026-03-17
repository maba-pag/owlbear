"""Tests for knowledge __init__.py symbol trimming (task #550).

Verifies that the 23 removed symbols are no longer accessible via the
top-level ``owlbear.memory.knowledge`` package after the public-API trim.
"""

from __future__ import annotations

import pytest

# The 23 symbols that must be REMOVED from the package's public surface.
# After #550, ``getattr(owlbear.memory.knowledge, name)`` must raise
# ``AttributeError`` for each of these.
REMOVED_SYMBOLS: frozenset[str] = frozenset(
    {
        "BgeM3EmbeddingProvider",
        "Bookmark",
        "BookmarkPipeline",
        "BookmarkResult",
        "BookmarkToolset",
        "Chunk",
        "ConsolidationService",
        "DocumentStore",
        "Embedding",
        "EntityExtractor",
        "EvaluationResult",
        "ExtractionResult",
        "GraphAugmentedRetriever",
        "GraphBuildResult",
        "GraphEnricher",
        "HybridEmbedding",
        "InterDocGraphBuilder",
        "IntraDocGraphBuilder",
        "RetrievalResult",
        "SourceEvaluator",
        "SparseVector",
        "TextChunker",
        "compute_content_hash",
    }
)


class TestFromAC_RemovedSymbols:  # noqa: N801
    """AC 2: Removed symbols must not be accessible from the package."""

    @pytest.mark.parametrize("name", sorted(REMOVED_SYMBOLS))
    def test_removed_symbol_raises_attribute_error(self, name: str) -> None:
        """Each removed symbol must raise AttributeError on getattr."""
        import owlbear.memory.knowledge as pkg

        with pytest.raises(AttributeError):
            getattr(pkg, name)


class TestFromAC_TextChunkerImportFix:  # noqa: N801
    """AC 3: TextChunker must not be importable from the top-level package."""

    def test_text_chunker_not_on_package(self) -> None:
        """``owlbear.memory.knowledge.TextChunker`` must raise AttributeError."""
        import owlbear.memory.knowledge as pkg

        with pytest.raises(AttributeError):
            _ = pkg.TextChunker  # type: ignore[attr-defined]


class TestFromAC_ConsolidationImportFix:  # noqa: N801
    """AC 4: ConsolidationService must not be importable from the top-level package."""

    def test_consolidation_service_not_on_package(self) -> None:
        """``owlbear.memory.knowledge.ConsolidationService`` must raise AttributeError."""
        import owlbear.memory.knowledge as pkg

        with pytest.raises(AttributeError):
            _ = pkg.ConsolidationService  # type: ignore[attr-defined]


class TestFromAC_NoStaleImportLines:  # noqa: N801
    """AC 2: The __init__.py must not reference removed symbols at all.

    After #550, the module-level ``_LAZY_IMPORTS`` (or any successor
    mechanism) should not contain entries for the 23 removed symbols.
    We verify via ``dir()`` — only the 14 retained symbols plus standard
    module attributes should appear.
    """

    def test_dir_excludes_removed_symbols(self) -> None:
        """dir(package) must not list any removed symbol."""
        import owlbear.memory.knowledge as pkg

        public_names = {n for n in dir(pkg) if not n.startswith("_")}
        leaked = REMOVED_SYMBOLS & public_names
        assert not leaked, f"Removed symbols still visible in dir(): {leaked}"
