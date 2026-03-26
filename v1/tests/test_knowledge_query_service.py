"""Tests for KnowledgeQueryService — per-turn context injection.

TDD tests for #406. Covers: query format, threshold filtering, token budget,
scopes passthrough, embed_hybrid fallback, exception handling.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from owlbear.memory.knowledge.models import Document
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.query_service import KnowledgeQueryService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock satisfying VectorStoreProtocol."""
    store = MagicMock()
    store.search_similar = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_graph_store() -> MagicMock:
    """Mock satisfying GraphStore interface."""
    store = MagicMock()
    store.get_document = MagicMock(return_value=None)
    return store


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    """Mock with embed_hybrid support."""
    provider = MagicMock()
    provider.embed_hybrid = MagicMock(
        return_value=[HybridEmbedding(dense=[0.1, 0.2, 0.3])]
    )
    provider.embed = MagicMock(return_value=[[0.1, 0.2, 0.3]])
    return provider


@pytest.fixture
def service(
    mock_vector_store: MagicMock,
    mock_graph_store: MagicMock,
    mock_embedding_provider: MagicMock,
) -> KnowledgeQueryService:
    """Default KnowledgeQueryService with mocked dependencies."""
    return KnowledgeQueryService(
        vector_store=mock_vector_store,
        graph_store=mock_graph_store,
        embedding_provider=mock_embedding_provider,
    )


def _make_doc(doc_id: str, title: str, content: str) -> Document:
    """Helper to create a Document with given fields."""
    return Document(id=doc_id, title=title, content=content, scope="global")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQueryForContext:
    """Core query_for_context behavior."""

    def test_returns_formatted_results(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Happy path: results above threshold formatted as context string."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.80),
        ]
        mock_graph_store.get_document.side_effect = lambda doc_id: {
            "doc-1": _make_doc("doc-1", "Design Patterns", "Observer pattern details"),
            "doc-2": _make_doc("doc-2", "API Reference", "REST endpoints docs"),
        }[doc_id]

        result = service.query_for_context("design patterns")

        assert result is not None
        assert result.startswith("Relevant knowledge:\n\n")
        assert "- Design Patterns: Observer pattern details" in result
        assert "- API Reference: REST endpoints docs" in result

    def test_returns_none_when_no_results(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Returns None when vector store has no results."""
        mock_vector_store.search_similar.return_value = []

        result = service.query_for_context("unknown topic")

        assert result is None

    def test_returns_none_when_all_below_threshold(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Returns None when all results are below similarity threshold (0.3)."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.25),
            ("doc-2", 0.10),
        ]

        result = service.query_for_context("irrelevant query")

        assert result is None


class TestThresholdFiltering:
    """Similarity threshold filtering."""

    def test_filters_below_threshold(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Only results >= threshold (0.3) are included."""
        mock_vector_store.search_similar.return_value = [
            ("doc-good", 0.85),
            ("doc-bad", 0.20),
        ]
        mock_graph_store.get_document.side_effect = {
            "doc-good": _make_doc("doc-good", "Good Doc", "Relevant content"),
        }.get

        result = service.query_for_context("test")

        assert result is not None
        assert "Good Doc" in result
        assert "doc-bad" not in result

    def test_custom_threshold(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Custom similarity_threshold filters differently."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            similarity_threshold=0.5,
        )
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.45),  # below 0.5
            ("doc-2", 0.60),  # above 0.5
        ]
        mock_graph_store.get_document.side_effect = {
            "doc-2": _make_doc("doc-2", "High Score", "Content"),
        }.get

        result = svc.query_for_context("test")

        assert result is not None
        assert "High Score" in result
        assert "doc-1" not in (result or "")


class TestTokenBudget:
    """Token budget enforcement."""

    def test_respects_max_tokens(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Output never exceeds max_tokens words."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
        )
        # Each doc has ~10 words of content
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.90),
            ("doc-2", 0.85),
            ("doc-3", 0.80),
        ]
        mock_graph_store.get_document.side_effect = lambda doc_id: {
            "doc-1": _make_doc("doc-1", "Doc A", "word " * 10),
            "doc-2": _make_doc("doc-2", "Doc B", "word " * 10),
            "doc-3": _make_doc("doc-3", "Doc C", "word " * 10),
        }[doc_id]

        result = svc.query_for_context("test", max_tokens=20)

        assert result is not None
        assert len(result.split()) <= 20

    def test_drops_lowest_scored_first_when_over_budget(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Results are sorted by score descending; lowest dropped when budget exceeded."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
        )
        # Results already sorted desc from search_similar
        mock_vector_store.search_similar.return_value = [
            ("doc-high", 0.95),
            ("doc-mid", 0.70),
            ("doc-low", 0.40),
        ]
        mock_graph_store.get_document.side_effect = lambda doc_id: {
            "doc-high": _make_doc("doc-high", "High", "important " * 8),
            "doc-mid": _make_doc("doc-mid", "Mid", "moderate " * 8),
            "doc-low": _make_doc("doc-low", "Low", "marginal " * 8),
        }[doc_id]

        # Budget only fits header + ~1-2 results
        result = svc.query_for_context("test", max_tokens=15)

        assert result is not None
        assert "High" in result
        # Low-scored result should be excluded due to budget
        # (we can't fit all three in 15 words)


class TestScopes:
    """Scopes passthrough to search_similar."""

    def test_no_scopes_by_default(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Without scopes, search_similar called without scopes kwarg."""
        mock_vector_store.search_similar.return_value = []

        service.query_for_context("test")

        mock_vector_store.search_similar.assert_called_once()
        call_kwargs = mock_vector_store.search_similar.call_args
        # No scopes kwarg when scopes is None
        assert "scopes" not in call_kwargs.kwargs

    def test_scopes_passed_to_search(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """With scopes set, search_similar receives scopes kwarg."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            scopes=["global", "project:abc"],
        )
        mock_vector_store.search_similar.return_value = []

        svc.query_for_context("scoped query")

        mock_vector_store.search_similar.assert_called_once()
        call_kwargs = mock_vector_store.search_similar.call_args
        assert call_kwargs.kwargs["scopes"] == ["global", "project:abc"]


class TestEmbedding:
    """Embedding provider interaction."""

    def test_uses_embed_hybrid_when_available(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Prefers embed_hybrid over embed when available."""
        hybrid = HybridEmbedding(dense=[0.1, 0.2, 0.3])
        mock_embedding_provider.embed_hybrid.return_value = [hybrid]
        mock_vector_store.search_similar.return_value = []

        service.query_for_context("test")

        mock_embedding_provider.embed_hybrid.assert_called_once_with(["test"])
        mock_embedding_provider.embed.assert_not_called()
        mock_vector_store.search_similar.assert_called_once()
        # Verify the hybrid embedding was passed to search
        call_args = mock_vector_store.search_similar.call_args
        assert call_args[0][0] is hybrid

    def test_falls_back_to_embed(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Falls back to embed() + HybridEmbedding wrapper when embed_hybrid missing."""
        provider = MagicMock(spec=["embed"])  # No embed_hybrid
        provider.embed.return_value = [[0.4, 0.5, 0.6]]
        mock_vector_store.search_similar.return_value = []

        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=provider,
        )
        svc.query_for_context("test")

        provider.embed.assert_called_once_with(["test"])
        call_args = mock_vector_store.search_similar.call_args
        embedding = call_args[0][0]
        assert isinstance(embedding, HybridEmbedding)
        assert embedding.dense == [0.4, 0.5, 0.6]


class TestDocumentResolution:
    """Document resolution via graph_store."""

    def test_skips_missing_documents(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Skips results where graph_store.get_document returns None."""
        mock_vector_store.search_similar.return_value = [
            ("doc-exists", 0.90),
            ("doc-gone", 0.80),
        ]
        mock_graph_store.get_document.side_effect = {
            "doc-exists": _make_doc("doc-exists", "Existing", "Real content"),
        }.get

        result = service.query_for_context("test")

        assert result is not None
        assert "Existing" in result
        assert "doc-gone" not in result

    def test_returns_none_when_all_documents_missing(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Returns None when all resolved documents are None."""
        mock_vector_store.search_similar.return_value = [("doc-gone", 0.90)]
        mock_graph_store.get_document.return_value = None

        result = service.query_for_context("test")

        assert result is None


class TestErrorHandling:
    """Graceful degradation on exceptions."""

    def test_catches_embedding_error(
        self,
        service: KnowledgeQueryService,
        mock_embedding_provider: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and logs WARNING when embedding fails."""
        mock_embedding_provider.embed_hybrid.side_effect = RuntimeError("model crash")

        with caplog.at_level(logging.WARNING):
            result = service.query_for_context("test")

        assert result is None
        assert "Knowledge query failed" in caplog.text

    def test_catches_search_error(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and logs WARNING when search_similar fails."""
        mock_vector_store.search_similar.side_effect = RuntimeError("qdrant down")

        with caplog.at_level(logging.WARNING):
            result = service.query_for_context("test")

        assert result is None
        assert "Knowledge query failed" in caplog.text

    def test_catches_graph_store_error(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Returns None and logs WARNING when graph_store.get_document fails."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.side_effect = RuntimeError("db locked")

        with caplog.at_level(logging.WARNING):
            result = service.query_for_context("test")

        assert result is None
        assert "Knowledge query failed" in caplog.text
