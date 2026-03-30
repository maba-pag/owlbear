"""TDD RED tests for task #34: Knowledge package integration + hybrid search.

Covers the AC items not yet addressed by #205 tests:
  - KnowledgeQueryService.query_for_context() method in query_service.py
  - owlbear_knowledge.__init__ exports GraphAugmentedRetriever, RetrievalResult
  - packages/knowledge/README.md existence and required content

All tests must FAIL until the builder implements the missing AC items.
"""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock

from owlbear_knowledge.retrieval import GraphAugmentedRetriever, RetrievalResult
from owlbear_knowledge.query_service import KnowledgeQueryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = pathlib.Path(__file__).parent.parent / "packages" / "knowledge"


def _make_service(
    *,
    retriever: object | None = None,
    graph_docs: dict[str, tuple[str, str]] | None = None,
) -> KnowledgeQueryService:
    """Return a KnowledgeQueryService with mock infrastructure.

    graph_docs: mapping of {doc_id: (title, content)} for graph_store.get_document.
    """
    graph_store = MagicMock()
    docs = graph_docs or {}

    def _get_document(doc_id: str) -> MagicMock | None:
        if doc_id not in docs:
            return None
        title, content = docs[doc_id]
        doc = MagicMock()
        doc.title = title
        doc.content = content
        return doc

    graph_store.get_document.side_effect = _get_document

    return KnowledgeQueryService(
        vector_store=MagicMock(),
        graph_store=graph_store,
        embedding_provider=MagicMock(),
        retriever=retriever,
    )


def _stub_retriever(
    chunks: list[tuple[str, float]] | None = None,
    expansion_text: str = "",
    entities_found: int = 0,
) -> MagicMock:
    """Return a GraphAugmentedRetriever mock with pre-configured retrieve() return value."""
    r = MagicMock(spec=GraphAugmentedRetriever)
    r.retrieve.return_value = RetrievalResult(
        chunks=chunks if chunks is not None else [],
        expansion_text=expansion_text,
        entities_found=entities_found,
    )
    return r


# ---------------------------------------------------------------------------
# AC: query_service.py add query_for_context(prompt, *, max_tokens, top_k)
#     When GraphAugmentedRetriever provided at construction: delegates to
#     retriever for chunks + expansion.
#     Formats results as "Relevant knowledge:\n\n- Title: snippet".
#     Returns None on no results or on exception.
# ---------------------------------------------------------------------------


class TestFromAC_QueryForContextMethod:
    """Contract tests for KnowledgeQueryService.query_for_context()."""

    # -- Happy path ----------------------------------------------------------

    def test_method_exists_on_knowledge_query_service(self) -> None:
        """AC: query_for_context is a callable method on KnowledgeQueryService."""
        svc = _make_service()
        assert callable(getattr(svc, "query_for_context", None)), (
            "KnowledgeQueryService must have a callable query_for_context() method"
        )

    def test_returns_string_starting_with_relevant_knowledge(self) -> None:
        """AC: returns a string that starts with 'Relevant knowledge:'."""
        retriever = _stub_retriever(chunks=[("doc-1", 0.85)])
        svc = _make_service(
            retriever=retriever,
            graph_docs={"doc-1": ("My Topic", "Some relevant content.")},
        )

        result = svc.query_for_context("what is my topic")

        assert result is not None
        assert result.startswith("Relevant knowledge:")

    def test_formats_title_colon_snippet(self) -> None:
        """AC: formats each result as '- Title: snippet' (not markdown H2)."""
        retriever = _stub_retriever(chunks=[("doc-1", 0.9)])
        svc = _make_service(
            retriever=retriever,
            graph_docs={"doc-1": ("Knowledge Title", "Important detail here.")},
        )

        result = svc.query_for_context("search")

        assert result is not None
        # Format must be "- Title: ..." not "## Title"
        assert "Knowledge Title" in result
        assert "- Knowledge Title:" in result

    def test_includes_snippet_text_in_output(self) -> None:
        """AC: output includes document content as a snippet."""
        retriever = _stub_retriever(chunks=[("doc-1", 0.9)])
        svc = _make_service(
            retriever=retriever,
            graph_docs={"doc-1": ("T", "Unique snippet phrase xyz.")},
        )

        result = svc.query_for_context("search")

        assert result is not None
        assert "Unique snippet phrase" in result

    def test_delegates_to_injected_retriever(self) -> None:
        """AC: delegates search to the GraphAugmentedRetriever injected at construction."""
        retriever = _stub_retriever(chunks=[])
        svc = _make_service(retriever=retriever)

        svc.query_for_context("some prompt")

        retriever.retrieve.assert_called()

    def test_passes_prompt_string_to_retriever(self) -> None:
        """AC: prompt is forwarded to retriever.retrieve()."""
        retriever = _stub_retriever(chunks=[])
        svc = _make_service(retriever=retriever)

        svc.query_for_context("find the answer to everything")

        call_args = retriever.retrieve.call_args
        assert call_args is not None
        # prompt must be the first positional arg or in kwargs
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        assert any("find the answer to everything" in str(a) for a in all_args)

    # -- Error paths ---------------------------------------------------------

    def test_returns_none_when_no_retriever_at_construction(self) -> None:
        """AC: returns None when no GraphAugmentedRetriever was provided at construction."""
        svc = _make_service(retriever=None)

        result = svc.query_for_context("some query")

        assert result is None

    def test_returns_none_when_retriever_yields_no_chunks(self) -> None:
        """AC: returns None when the retriever finds no matching chunks."""
        retriever = _stub_retriever(chunks=[])
        svc = _make_service(retriever=retriever)

        result = svc.query_for_context("unmatched query")

        assert result is None

    def test_returns_none_when_chunks_unresolvable(self) -> None:
        """AC: returns None when chunks cannot be resolved to documents."""
        retriever = _stub_retriever(chunks=[("ghost-doc", 0.95)])
        svc = _make_service(retriever=retriever, graph_docs={})  # no docs registered

        result = svc.query_for_context("query")

        assert result is None

    def test_returns_none_on_retriever_exception(self) -> None:
        """AC: returns None when retriever.retrieve() raises (graceful degradation)."""
        retriever = MagicMock(spec=GraphAugmentedRetriever)
        retriever.retrieve.side_effect = RuntimeError("embedding service down")
        svc = _make_service(retriever=retriever)

        result = svc.query_for_context("any query")

        assert result is None

    def test_returns_none_on_graph_store_exception(self) -> None:
        """AC: returns None when graph_store raises during document resolution."""
        retriever = _stub_retriever(chunks=[("doc-1", 0.9)])
        # Build service manually so we can inject a crashing graph_store
        graph_store = MagicMock()
        graph_store.get_document.side_effect = OSError("disk read error")
        svc = KnowledgeQueryService(
            vector_store=MagicMock(),
            graph_store=graph_store,
            embedding_provider=MagicMock(),
            retriever=retriever,
        )

        result = svc.query_for_context("query")

        assert result is None

    # -- Boundary conditions -------------------------------------------------

    def test_respects_max_tokens_budget(self) -> None:
        """AC: output word count does not exceed max_tokens (+ small formatting overhead)."""
        long_content = " ".join(["word"] * 600)
        retriever = _stub_retriever(chunks=[("doc-1", 0.9)])
        svc = _make_service(
            retriever=retriever,
            graph_docs={"doc-1": ("Title", long_content)},
        )

        result = svc.query_for_context("q", max_tokens=20)

        assert result is not None
        assert len(result.split()) <= 25  # small overhead for header + formatting

    def test_top_k_limits_number_of_chunks_processed(self) -> None:
        """AC: top_k limits the number of results formatted into the output."""
        many_chunks = [(f"doc-{i}", 0.9 - i * 0.01) for i in range(10)]
        retriever = _stub_retriever(chunks=many_chunks)
        graph_store = MagicMock()
        doc = MagicMock()
        doc.title = "T"
        doc.content = "C."
        graph_store.get_document.return_value = doc
        svc = KnowledgeQueryService(
            vector_store=MagicMock(),
            graph_store=graph_store,
            embedding_provider=MagicMock(),
            retriever=retriever,
        )

        svc.query_for_context("q", top_k=3)

        # At most top_k documents should be resolved from graph_store
        assert graph_store.get_document.call_count <= 3

    def test_default_max_tokens_is_2000(self) -> None:
        """AC: default max_tokens=2000 allows large output without truncation."""
        content = " ".join(["word"] * 100)
        retriever = _stub_retriever(chunks=[("doc-1", 0.9)])
        svc = _make_service(
            retriever=retriever,
            graph_docs={"doc-1": ("T", content)},
        )

        result = svc.query_for_context("query")  # no max_tokens override

        assert result is not None
        # 100 content words + header should be included untruncated
        assert "word" in result


# ---------------------------------------------------------------------------
# AC: __init__.py exports GraphAugmentedRetriever, RetrievalResult
# ---------------------------------------------------------------------------


class TestFromAC_InitExports:
    """Contract tests for owlbear_knowledge top-level exports."""

    def test_exports_graph_augmented_retriever(self) -> None:
        """AC: GraphAugmentedRetriever is accessible from the owlbear_knowledge top-level."""
        import owlbear_knowledge

        assert hasattr(owlbear_knowledge, "GraphAugmentedRetriever"), (
            "owlbear_knowledge.__init__ must re-export GraphAugmentedRetriever"
        )

    def test_exports_retrieval_result(self) -> None:
        """AC: RetrievalResult is accessible from the owlbear_knowledge top-level."""
        import owlbear_knowledge

        assert hasattr(owlbear_knowledge, "RetrievalResult"), (
            "owlbear_knowledge.__init__ must re-export RetrievalResult"
        )

    def test_graph_augmented_retriever_import_is_identical_class(self) -> None:
        """AC: exported class is the same object as owlbear_knowledge.retrieval.GraphAugmentedRetriever."""
        import owlbear_knowledge
        from owlbear_knowledge.retrieval import GraphAugmentedRetriever

        assert owlbear_knowledge.GraphAugmentedRetriever is GraphAugmentedRetriever

    def test_retrieval_result_import_is_identical_class(self) -> None:
        """AC: exported class is the same object as owlbear_knowledge.retrieval.RetrievalResult."""
        import owlbear_knowledge
        from owlbear_knowledge.retrieval import RetrievalResult

        assert owlbear_knowledge.RetrievalResult is RetrievalResult


# ---------------------------------------------------------------------------
# AC: packages/knowledge/README.md with purpose, install command, optional
#     deps (qdrant, embedding), and basic usage example.
# ---------------------------------------------------------------------------


class TestFromAC_ReadmeMd:
    """Contract tests for packages/knowledge/README.md."""

    @staticmethod
    def _read_readme() -> str:
        readme = _PACKAGE_ROOT / "README.md"
        return readme.read_text(encoding="utf-8")

    def test_readme_file_exists(self) -> None:
        """AC: packages/knowledge/README.md must exist."""
        readme = _PACKAGE_ROOT / "README.md"
        assert readme.exists(), f"README.md not found at {readme}"

    def test_readme_has_install_command(self) -> None:
        """AC: README contains install command (pip install or uv pip install)."""
        content = self._read_readme()
        assert "install" in content.lower(), "README must mention an install command"
        assert "knowledge" in content.lower(), "README install command must reference the package"

    def test_readme_has_code_block_usage_example(self) -> None:
        """AC: README contains a basic usage example in a fenced code block."""
        content = self._read_readme()
        assert "```" in content, "README must contain at least one fenced code block usage example"

    def test_readme_mentions_optional_deps(self) -> None:
        """AC: README mentions optional dependencies (qdrant or embedding provider)."""
        content = self._read_readme()
        has_qdrant = "qdrant" in content.lower()
        has_embedding = "embedding" in content.lower() or "bge" in content.lower()
        assert has_qdrant or has_embedding, (
            "README must mention optional dependencies (qdrant and/or embedding provider)"
        )
