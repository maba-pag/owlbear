"""Tests for KnowledgeQueryService graph expansion integration.

TDD tests for #427. Covers: retriever delegation, expansion_text output,
token budget with expansion, threshold filtering on retriever chunks,
scopes forwarding, empty results, exception handling, and bootstrap wiring.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear.memory.knowledge.models import Document
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.query_service import KnowledgeQueryService
from owlbear.memory.knowledge.retrieval import RetrievalResult

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
    provider.embed_hybrid = MagicMock(return_value=[HybridEmbedding(dense=[0.1, 0.2, 0.3])])
    provider.embed = MagicMock(return_value=[[0.1, 0.2, 0.3]])
    return provider


@pytest.fixture
def mock_retriever() -> MagicMock:
    """Mock GraphAugmentedRetriever."""
    retriever = MagicMock()
    retriever.retrieve = MagicMock(
        return_value=RetrievalResult(
            chunks=[],
            expansion_text="",
            entities_found=0,
        )
    )
    return retriever


def _make_doc(doc_id: str, title: str, content: str) -> Document:
    """Helper to create a Document with given fields."""
    return Document(id=doc_id, title=title, content=content, scope="global")


# ---------------------------------------------------------------------------
# Backward compatibility — retriever=None
# ---------------------------------------------------------------------------


class TestRetrieverNoneBackwardCompat:
    """When retriever=None (default), behavior identical to current."""

    def test_no_retriever_uses_vector_store_directly(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Without retriever, _query embeds and calls vector_store.search_similar."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
        )
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Title", "Content")

        result = svc.query_for_context("test")

        assert result is not None
        assert "Relevant knowledge:" in result
        assert "Title" in result
        mock_embedding_provider.embed_hybrid.assert_called_once()
        mock_vector_store.search_similar.assert_called_once()

    def test_no_retriever_no_expansion_section(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Without retriever, output has no 'Related concepts:' section."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
        )
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Title", "Content")

        result = svc.query_for_context("test")

        assert result is not None
        assert "Related concepts:" not in result


# ---------------------------------------------------------------------------
# Retriever delegation
# ---------------------------------------------------------------------------


class TestRetrieverDelegation:
    """When retriever is provided, _query() delegates to retriever.retrieve()."""

    def test_delegates_to_retriever(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """With retriever, retrieve() is called instead of vector_store.search_similar."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.90)],
            expansion_text="",
            entities_found=1,
        )
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Title", "Content")
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        svc.query_for_context("test query")

        mock_retriever.retrieve.assert_called_once()
        mock_vector_store.search_similar.assert_not_called()
        mock_embedding_provider.embed_hybrid.assert_not_called()

    def test_retriever_receives_top_k(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """Retriever gets the top_k from query_for_context."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[],
            expansion_text="",
            entities_found=0,
        )
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        svc.query_for_context("test", top_k=10)

        call_kwargs = mock_retriever.retrieve.call_args
        assert call_kwargs.kwargs.get("top_k") == 10

    def test_retriever_doc_resolution_still_in_service(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """Doc resolution via graph_store.get_document still happens in service."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.90)],
            expansion_text="",
            entities_found=1,
        )
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Resolved", "Doc content")
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test")

        assert result is not None
        assert "Resolved" in result
        mock_graph_store.get_document.assert_called_with("doc-1")


# ---------------------------------------------------------------------------
# Expansion text output
# ---------------------------------------------------------------------------


class TestExpansionText:
    """expansion_text from RetrievalResult appended under 'Related concepts:'."""

    def test_expansion_text_appended(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """expansion_text appears after doc snippets under 'Related concepts:'."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.90)],
            expansion_text="Entity A --[relates_to]--> Entity B: Description",
            entities_found=1,
        )
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Main Doc", "Main content")
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test", max_tokens=500)

        assert result is not None
        assert "Related concepts:" in result
        assert "Entity A --[relates_to]--> Entity B" in result
        # Expansion text should come after the doc snippets
        doc_pos = result.index("Main Doc")
        expansion_pos = result.index("Related concepts:")
        assert expansion_pos > doc_pos

    def test_empty_expansion_text_no_section(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """When expansion_text is empty string, no 'Related concepts:' section."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.90)],
            expansion_text="",
            entities_found=0,
        )
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Title", "Content")
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test")

        assert result is not None
        assert "Related concepts:" not in result


# ---------------------------------------------------------------------------
# Token budget with expansion text
# ---------------------------------------------------------------------------


class TestTokenBudgetWithExpansion:
    """Total word count of doc snippets + expansion text respects max_tokens."""

    def test_total_output_within_budget(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """Doc snippets + expansion text together stay within max_tokens."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.90)],
            expansion_text="expansion " * 50,  # 50 words of expansion
            entities_found=1,
        )
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Doc", "word " * 5)
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test", max_tokens=30)

        assert result is not None
        assert len(result.split()) <= 30

    def test_expansion_trimmed_when_budget_exhausted(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """When doc snippets consume most of the budget, expansion_text is trimmed."""
        # Doc takes ~10 words: "- DocTitle: word word word word word"
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.90)],
            expansion_text="expansion " * 100,  # 100 words
            entities_found=1,
        )
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "DocTitle", "word " * 5)
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test", max_tokens=20)

        assert result is not None
        assert len(result.split()) <= 20
        # Doc snippet should still be present
        assert "DocTitle" in result

    def test_no_expansion_when_budget_fully_exhausted_by_docs(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """When docs consume entire budget, expansion section is omitted."""
        # Doc takes ~12 words: "- BigDoc: word word word word word word word word word word"
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.90)],
            expansion_text="expansion " * 50,
            entities_found=1,
        )
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "BigDoc", "word " * 10)
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        # Very tight budget — just enough for header + 1 doc line
        result = svc.query_for_context("test", max_tokens=15)

        assert result is not None
        assert len(result.split()) <= 15


# ---------------------------------------------------------------------------
# Threshold filtering on retriever chunks
# ---------------------------------------------------------------------------


class TestThresholdOnRetrieverChunks:
    """Threshold filtering still applied to chunks returned by retriever."""

    def test_filters_below_threshold(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """Chunks below similarity_threshold are filtered out."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-good", 0.85), ("doc-bad", 0.20)],
            expansion_text="",
            entities_found=1,
        )
        mock_graph_store.get_document.side_effect = {
            "doc-good": _make_doc("doc-good", "Good", "Relevant"),
        }.get

        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test")

        assert result is not None
        assert "Good" in result
        # doc-bad should not be resolved
        mock_graph_store.get_document.assert_called_once_with("doc-good")

    def test_all_below_threshold_returns_none(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """When all retriever chunks are below threshold, returns None."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[("doc-1", 0.10), ("doc-2", 0.15)],
            expansion_text="some expansion",
            entities_found=1,
        )
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test")

        assert result is None


# ---------------------------------------------------------------------------
# Scopes forwarding
# ---------------------------------------------------------------------------


class TestScopesForwarding:
    """Scopes forwarded to retriever.retrieve(scopes=...) when set."""

    def test_scopes_forwarded_to_retriever(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """Scopes from service constructor forwarded to retriever.retrieve()."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[],
            expansion_text="",
            entities_found=0,
        )
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
            scopes=["global", "project:abc"],
        )

        svc.query_for_context("test")

        call_args = mock_retriever.retrieve.call_args
        assert call_args.kwargs.get("scopes") == ["global", "project:abc"]

    def test_no_scopes_no_kwarg_to_retriever(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """When scopes=None, retriever called without scopes kwarg."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[],
            expansion_text="",
            entities_found=0,
        )
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        svc.query_for_context("test")

        call_args = mock_retriever.retrieve.call_args
        # scopes should be None or not present
        assert call_args.kwargs.get("scopes") is None


# ---------------------------------------------------------------------------
# Empty results from retriever
# ---------------------------------------------------------------------------


class TestEmptyRetrieverResults:
    """When retriever returns empty chunks, returns None."""

    def test_empty_chunks_returns_none(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
    ) -> None:
        """Empty chunks list from retriever → None result."""
        mock_retriever.retrieve.return_value = RetrievalResult(
            chunks=[],
            expansion_text="some expansion",
            entities_found=0,
        )
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        result = svc.query_for_context("test")

        assert result is None


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------


class TestRetrieverExceptionHandling:
    """Exception in retriever.retrieve() caught, returns None with WARNING log."""

    def test_retriever_exception_caught(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
        mock_retriever: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """RuntimeError in retriever.retrieve() returns None and logs WARNING."""
        mock_retriever.retrieve.side_effect = RuntimeError("retriever exploded")
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            retriever=mock_retriever,
        )

        with caplog.at_level(logging.WARNING):
            result = svc.query_for_context("test")

        assert result is None
        assert "Knowledge query failed" in caplog.text


# ---------------------------------------------------------------------------
# Bootstrap wiring
# ---------------------------------------------------------------------------


class TestBootstrapRetrieverWiring:
    """Bootstrap creates GraphAugmentedRetriever based on config."""

    def test_creates_retriever_when_expansion_enabled(self, tmp_path: Path) -> None:
        """knowledge_graph_expansion=True → retriever created, passed to service."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(knowledge_graph_expansion=True)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path)
            assert infra is not None
            result = _build_knowledge_toolset(
                tmp_path,
                infra,
                knowledge_graph_expansion=settings.knowledge_graph_expansion,
            )

        assert result is not None
        _, service = result
        assert service._retriever is not None
        assert type(service._retriever).__name__ == "GraphAugmentedRetriever"

    def test_no_retriever_when_expansion_disabled(self, tmp_path: Path) -> None:
        """knowledge_graph_expansion=False → no retriever created."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(knowledge_graph_expansion=False)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path)
            assert infra is not None
            result = _build_knowledge_toolset(
                tmp_path,
                infra,
                knowledge_graph_expansion=settings.knowledge_graph_expansion,
            )

        assert result is not None
        _, service = result
        assert service._retriever is None

    def test_build_toolsets_passes_expansion_setting(self, tmp_path: Path) -> None:
        """build_toolsets forwards knowledge_graph_expansion to _build_knowledge_toolset."""
        from owlbear.bootstrap import build_toolsets
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookRegistry

        settings = OwlBearSettings(
            knowledge_graph_expansion=False,
            approval_policy=[],
        )
        hooks = HookRegistry()
        channel = MagicMock()
        mock_infra = MagicMock()

        with (
            patch(
                "owlbear.bootstrap._build_knowledge_infra",
                return_value=mock_infra,
            ),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
                return_value=None,
            ) as mock_build,
        ):
            build_toolsets(settings, tmp_path, hooks, channel)

        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args
        assert call_kwargs.kwargs.get("knowledge_graph_expansion") is False or (
            len(call_kwargs.args) > 2 and call_kwargs.args[2] is False
        )
