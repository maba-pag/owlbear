"""TDD RED tests for query_for_context() (task #205).

All tests must FAIL until the builder implements owlbear_knowledge.retrieval.query_for_context.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from owlbear_knowledge.retrieval import GraphAugmentedRetriever, RetrievalResult, query_for_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_retriever(
    chunks: list[tuple[str, float]] | None = None,
    expansion_text: str = "",
    entities_found: int = 0,
) -> MagicMock:
    """Return a mock GraphAugmentedRetriever that returns a pre-configured RetrievalResult."""
    retriever = MagicMock(spec=GraphAugmentedRetriever)
    retriever.retrieve.return_value = RetrievalResult(
        chunks=chunks if chunks is not None else [],
        expansion_text=expansion_text,
        entities_found=entities_found,
    )
    return retriever


def _mock_graph_store(docs: dict[str, tuple[str, str]] | None = None) -> MagicMock:
    """Return a mock GraphStore resolving chunk_id → (title, content).

    docs: mapping of {doc_id: (title, content)}
    """
    graph_store = MagicMock()
    docs = docs or {}

    def get_document(doc_id: str) -> MagicMock | None:
        if doc_id not in docs:
            return None
        title, content = docs[doc_id]
        doc = MagicMock()
        doc.title = title
        doc.content = content
        doc.scope = "global"
        return doc

    graph_store.get_document.side_effect = get_document
    return graph_store


# ---------------------------------------------------------------------------
# AC: query_for_context() returns formatted string starting with
#     "Relevant knowledge:"
# ---------------------------------------------------------------------------


class TestFromAC_QueryForContext:
    """Contract tests for query_for_context()."""

    def test_returns_string_starting_with_relevant_knowledge(self) -> None:
        """AC: query_for_context() returns a string that starts with 'Relevant knowledge:'."""
        retriever = _mock_retriever(chunks=[("doc1", 0.9)])
        graph_store = _mock_graph_store({"doc1": ("Title One", "Content of doc one.")})

        result = query_for_context("test query", retriever=retriever, graph_store=graph_store)

        assert result is not None
        assert result.startswith("Relevant knowledge:")

    def test_formatted_output_includes_document_content(self) -> None:
        """AC: formatted output contains content from resolved documents."""
        retriever = _mock_retriever(chunks=[("doc1", 0.9)])
        graph_store = _mock_graph_store({"doc1": ("My Title", "Important content here.")})

        result = query_for_context("test query", retriever=retriever, graph_store=graph_store)

        assert result is not None
        assert "My Title" in result or "Important content" in result

    # ---------------------------------------------------------------------------
    # AC: query_for_context() truncates output to respect max_tokens budget.
    # ---------------------------------------------------------------------------

    def test_truncates_to_max_tokens_budget(self) -> None:
        """AC: output word count does not exceed max_tokens."""
        long_content = " ".join(["word"] * 500)
        retriever = _mock_retriever(chunks=[("doc1", 0.9)])
        graph_store = _mock_graph_store({"doc1": ("Title", long_content)})

        result = query_for_context(
            "test query",
            retriever=retriever,
            graph_store=graph_store,
            max_tokens=20,
        )

        assert result is not None
        word_count = len(result.split())
        assert word_count <= 25  # allow small overhead for header/formatting

    def test_truncation_preserves_relevant_knowledge_header(self) -> None:
        """AC: truncation does not strip the 'Relevant knowledge:' header."""
        long_content = " ".join(["dataword"] * 400)
        retriever = _mock_retriever(chunks=[("doc1", 0.9)])
        graph_store = _mock_graph_store({"doc1": ("Title", long_content)})

        result = query_for_context(
            "query",
            retriever=retriever,
            graph_store=graph_store,
            max_tokens=15,
        )

        assert result is not None
        assert "Relevant knowledge:" in result

    # ---------------------------------------------------------------------------
    # AC: query_for_context() returns None when no results above similarity
    #     threshold.
    # ---------------------------------------------------------------------------

    def test_returns_none_when_no_chunks(self) -> None:
        """AC: returns None when retriever returns empty chunks."""
        retriever = _mock_retriever(chunks=[])
        graph_store = _mock_graph_store()

        result = query_for_context("unknown query", retriever=retriever, graph_store=graph_store)

        assert result is None

    def test_returns_none_when_all_chunks_below_threshold(self) -> None:
        """AC: returns None when all chunk scores are below the similarity threshold."""
        retriever = _mock_retriever(chunks=[("doc1", 0.1), ("doc2", 0.05)])
        graph_store = _mock_graph_store(
            {"doc1": ("T1", "Content one"), "doc2": ("T2", "Content two")}
        )

        result = query_for_context(
            "irrelevant query",
            retriever=retriever,
            graph_store=graph_store,
            similarity_threshold=0.5,
        )

        assert result is None

    def test_returns_none_when_no_documents_resolved(self) -> None:
        """AC: returns None when chunk IDs cannot be resolved to documents."""
        retriever = _mock_retriever(chunks=[("missing-doc", 0.95)])
        graph_store = _mock_graph_store({})  # no docs registered

        result = query_for_context("query", retriever=retriever, graph_store=graph_store)

        assert result is None

    # ---------------------------------------------------------------------------
    # AC: query_for_context() catches exceptions and returns None (graceful
    #     degradation).
    # ---------------------------------------------------------------------------

    def test_returns_none_when_retriever_raises(self) -> None:
        """AC: returns None when retriever.retrieve() raises an exception."""
        retriever = MagicMock(spec=GraphAugmentedRetriever)
        retriever.retrieve.side_effect = RuntimeError("embedding failure")
        graph_store = _mock_graph_store()

        result = query_for_context("test query", retriever=retriever, graph_store=graph_store)

        assert result is None

    def test_returns_none_when_graph_store_raises(self) -> None:
        """AC: returns None when graph_store operations raise an exception."""
        retriever = _mock_retriever(chunks=[("doc1", 0.9)])
        graph_store = MagicMock()
        graph_store.get_document.side_effect = OSError("DB connection lost")

        result = query_for_context("test query", retriever=retriever, graph_store=graph_store)

        assert result is None

    def test_does_not_propagate_exceptions(self) -> None:
        """AC: exceptions never bubble up — function always returns str or None."""
        retriever = MagicMock(spec=GraphAugmentedRetriever)
        retriever.retrieve.side_effect = MemoryError("out of memory")
        graph_store = _mock_graph_store()

        # Must not raise
        result = query_for_context("test query", retriever=retriever, graph_store=graph_store)
        assert result is None

    # ---------------------------------------------------------------------------
    # AC: query_for_context() with injected GraphAugmentedRetriever delegates
    #     search to retriever.
    # ---------------------------------------------------------------------------

    def test_delegates_search_to_injected_retriever(self) -> None:
        """AC: retriever.retrieve() is called with the query string."""
        retriever = _mock_retriever(chunks=[])
        graph_store = _mock_graph_store()

        query_for_context("my specific query", retriever=retriever, graph_store=graph_store)

        retriever.retrieve.assert_called_once()

    def test_delegates_query_string_to_retriever(self) -> None:
        """AC: the exact query string is forwarded to retriever.retrieve()."""
        retriever = _mock_retriever(chunks=[])
        graph_store = _mock_graph_store()

        query_for_context("exact query text", retriever=retriever, graph_store=graph_store)

        call_args = retriever.retrieve.call_args
        # Query must appear as positional or keyword argument
        positional = call_args.args
        keyword = call_args.kwargs
        assert "exact query text" in positional or keyword.get("query") == "exact query text"

    def test_result_incorporates_expansion_text_when_present(self) -> None:
        """AC: expansion_text from retriever is included in formatted output."""
        retriever = _mock_retriever(
            chunks=[("doc1", 0.9)],
            expansion_text="Alpha --[related_to]--> Beta: beta desc",
        )
        graph_store = _mock_graph_store({"doc1": ("Title", "Main content.")})

        result = query_for_context("test query", retriever=retriever, graph_store=graph_store)

        # Expansion text or its content must appear in the output
        assert result is not None
        assert "Alpha" in result or "Beta" in result or "beta desc" in result
