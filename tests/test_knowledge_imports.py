"""RED-phase tests for knowledge package __init__.py re-exports (#161).

Tests the contract for:
- KnowledgeQueryService and StructuredSearchResult accessible from owlbear_knowledge top-level
- Both names listed in owlbear_knowledge.__all__
- import owlbear_knowledge succeeds without optional deps installed

AC4 tests fail in RED phase — re-exports not yet added to __init__.py.
AC3 (20-module smoke test content) is a builder deliverable per arch review.
"""

from __future__ import annotations

import owlbear_knowledge


class TestFromAC_KnowledgeReExports:
    """Contract tests for AC4: KnowledgeQueryService and StructuredSearchResult re-exports."""

    # -- __all__ membership --------------------------------------------------

    def test_knowledge_query_service_in_all(self) -> None:
        """KnowledgeQueryService must appear in owlbear_knowledge.__all__."""
        assert "KnowledgeQueryService" in owlbear_knowledge.__all__

    def test_structured_search_result_in_all(self) -> None:
        """StructuredSearchResult must appear in owlbear_knowledge.__all__."""
        assert "StructuredSearchResult" in owlbear_knowledge.__all__

    # -- direct importability ------------------------------------------------

    def test_knowledge_query_service_importable_from_top_level(self) -> None:
        """KnowledgeQueryService must be directly importable from owlbear_knowledge."""
        from owlbear_knowledge import KnowledgeQueryService  # type: ignore[attr-defined]

        assert KnowledgeQueryService is not None

    def test_structured_search_result_importable_from_top_level(self) -> None:
        """StructuredSearchResult must be directly importable from owlbear_knowledge."""
        from owlbear_knowledge import StructuredSearchResult  # type: ignore[attr-defined]

        assert StructuredSearchResult is not None

    # -- attribute presence on the module object -----------------------------

    def test_knowledge_query_service_is_class(self) -> None:
        """KnowledgeQueryService attribute on owlbear_knowledge must be a class."""
        kqs = getattr(owlbear_knowledge, "KnowledgeQueryService", None)
        assert kqs is not None, "KnowledgeQueryService not found as attribute of owlbear_knowledge"
        assert isinstance(kqs, type), "KnowledgeQueryService should be a class"

    def test_structured_search_result_is_class(self) -> None:
        """StructuredSearchResult attribute on owlbear_knowledge must be a class."""
        ssr = getattr(owlbear_knowledge, "StructuredSearchResult", None)
        assert ssr is not None, "StructuredSearchResult not found as attribute of owlbear_knowledge"
        assert isinstance(ssr, type), "StructuredSearchResult should be a class"

    # -- boundary: no duplicate / no accidental removal of existing exports --

    def test_existing_exports_preserved_after_re_export_addition(self) -> None:
        """Adding re-exports must not remove existing __all__ entries."""
        pre_existing = {
            "Bookmark",
            "BookmarkStore",
            "CancelSignal",
            "ConsolidationInsight",
            "ConsolidationService",
            "DocumentStatus",
            "DocumentStore",
            "EvaluationResult",
            "GraphAugmentedRetriever",
            "GraphStore",
            "IngestPipeline",
            "IngestResult",
            "IntakeResult",
            "KnowledgeSourceStore",
            "LinkedCancelSignal",
            "RetrievalResult",
            "SourceEvaluator",
            "StatusStore",
            "compute_content_hash",
            "init_db",
            # NEW — must also be present after builder's change:
            "KnowledgeQueryService",
            "StructuredSearchResult",
        }
        missing = pre_existing - set(owlbear_knowledge.__all__)
        assert not missing, f"Missing from __all__: {missing}"


class TestBuilderDiscovered:
    """AC3: smoke-import all public modules — no ImportError at module load time.

    Optional-dep modules (qdrant, embeddings, intake) use try/except or
    TYPE_CHECKING guards and must load successfully without the optional
    packages installed.
    """

    PUBLIC_MODULES = (
        "owlbear_knowledge.bookmark_store",
        "owlbear_knowledge.cancellation",
        "owlbear_knowledge.chunker",
        "owlbear_knowledge.consolidation",
        "owlbear_knowledge.document_store",
        "owlbear_knowledge.embeddings",
        "owlbear_knowledge.evaluator",
        "owlbear_knowledge.extractor",
        "owlbear_knowledge.graph_builder",
        "owlbear_knowledge.graph_store",
        "owlbear_knowledge.ingest",
        "owlbear_knowledge.intake",
        "owlbear_knowledge.inter_doc_graph_builder",
        "owlbear_knowledge.loader",
        "owlbear_knowledge.models",
        "owlbear_knowledge.protocol",
        "owlbear_knowledge.qdrant",
        "owlbear_knowledge.query_service",
        "owlbear_knowledge.retrieval",
        "owlbear_knowledge.schema",
        "owlbear_knowledge.source_store",
        "owlbear_knowledge.status_store",
    )

    def test_all_public_modules_importable_without_optional_deps(self) -> None:
        """All public modules must import without raising ImportError."""
        import importlib

        failed: list[str] = []
        for mod_name in self.PUBLIC_MODULES:
            try:
                importlib.import_module(mod_name)
            except ImportError as exc:
                failed.append(f"{mod_name}: {exc}")

        assert not failed, "Module-level ImportError(s):\n" + "\n".join(failed)
