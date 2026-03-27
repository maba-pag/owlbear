"""Tests for KnowledgeQueryService.search_structured() — TDD RED phase.

All tests are expected to FAIL until #70 implements search_structured()
and StructuredSearchResult. ImportError on StructuredSearchResult is the
primary RED signal.

Owning task: #76
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from owlbear.memory.knowledge.models import Document, Entity, EntityType
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.query_service import (
    KnowledgeQueryService,
    StructuredSearchResult,  # does not exist yet — RED
)

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
    store.list_entities_for_document = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    """Mock with embed_hybrid support."""
    provider = MagicMock()
    provider.embed_hybrid = MagicMock(return_value=[HybridEmbedding(dense=[0.1, 0.2, 0.3])])
    return provider


@pytest.fixture
def service(
    mock_vector_store: MagicMock,
    mock_graph_store: MagicMock,
    mock_embedding_provider: MagicMock,
) -> KnowledgeQueryService:
    """KnowledgeQueryService under test."""
    return KnowledgeQueryService(
        vector_store=mock_vector_store,
        graph_store=mock_graph_store,
        embedding_provider=mock_embedding_provider,
    )


def _make_doc(doc_id: str, title: str, content: str, scope: str = "global") -> Document:
    """Helper to create a Document with given fields."""
    return Document(id=doc_id, title=title, content=content, scope=scope)


def _make_entity(entity_type: EntityType, doc_id: str) -> Entity:
    """Helper to create an Entity linked to a document."""
    return Entity(
        name="test-entity",
        entity_type=entity_type,
        document_id=doc_id,
    )


# ---------------------------------------------------------------------------
# TestFromAC_StructuredResults — returns correct shape
# ---------------------------------------------------------------------------


class TestFromAC_StructuredResults:
    """search_structured returns list[StructuredSearchResult] with all AC fields."""

    def test_returns_list_type(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Return value is a list."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C")

        result = service.search_structured("query")

        assert isinstance(result, list)

    def test_result_items_are_structured_search_result(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Each item is a StructuredSearchResult instance."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Title", "Content")

        result = service.search_structured("query")

        assert len(result) == 1
        assert isinstance(result[0], StructuredSearchResult)

    def test_result_has_doc_id_field(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """StructuredSearchResult has doc_id populated from vector store result."""
        mock_vector_store.search_similar.return_value = [("doc-abc", 0.85)]
        mock_graph_store.get_document.return_value = _make_doc("doc-abc", "Title", "C")

        result = service.search_structured("query")

        assert result[0].doc_id == "doc-abc"

    def test_result_has_title_field(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """StructuredSearchResult.title comes from Document.title."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "My Title", "Content")

        result = service.search_structured("query")

        assert result[0].title == "My Title"

    def test_result_has_score_field(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """StructuredSearchResult.score matches the similarity score."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.77)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C")

        result = service.search_structured("query")

        assert result[0].score == pytest.approx(0.77)

    def test_result_has_snippet_field(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """StructuredSearchResult.snippet is non-empty string from document content."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "The quick brown fox")

        result = service.search_structured("query")

        assert isinstance(result[0].snippet, str)
        assert len(result[0].snippet) > 0

    def test_snippet_equals_document_content_when_short(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Snippet equals full document content when content is at most 500 chars.

        This verifies content provenance: the snippet must come from THIS document's
        content field, not an arbitrary non-empty string.
        """
        doc_content = "Unique provenance identifier alpha-delta-check-9271"
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", doc_content)

        result = service.search_structured("query")

        assert result[0].snippet == doc_content

    def test_snippet_is_first_500_chars_of_content(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Snippet is exactly the first 500 chars when document content exceeds 500 chars."""
        doc_content = "X" * 600  # 600 chars — deliberately exceeds 500-char limit
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", doc_content)

        result = service.search_structured("query")

        assert result[0].snippet == doc_content[:500]
        assert len(result[0].snippet) == 500

    def test_result_has_scope_field(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """StructuredSearchResult.scope comes from Document.scope."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C", scope="project-x")

        result = service.search_structured("query")

        assert result[0].scope == "project-x"

    def test_multiple_results_returned(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Returns all results above threshold as structured items."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.90),
            ("doc-2", 0.80),
            ("doc-3", 0.70),
        ]
        mock_graph_store.get_document.side_effect = lambda doc_id: _make_doc(
            doc_id, f"Title-{doc_id}", "Content"
        )

        result = service.search_structured("query")

        assert len(result) == 3


# ---------------------------------------------------------------------------
# TestFromAC_StructuredEmpty — empty list cases
# ---------------------------------------------------------------------------


class TestFromAC_StructuredEmpty:
    """search_structured returns [] when no results or all below threshold."""

    def test_returns_empty_list_when_no_vector_results(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Empty list when vector store returns nothing."""
        mock_vector_store.search_similar.return_value = []

        result = service.search_structured("query")

        assert result == []

    def test_returns_empty_list_when_all_below_threshold(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Empty list when all scores are below similarity_threshold."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            similarity_threshold=0.8,
        )
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.5),
            ("doc-2", 0.6),
        ]

        result = svc.search_structured("query")

        assert result == []

    def test_returns_empty_list_at_threshold_boundary(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Score exactly at threshold is included (>= semantics)."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            similarity_threshold=0.7,
        )
        mock_vector_store.search_similar.return_value = [("doc-1", 0.7)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C")

        result = svc.search_structured("query")

        assert len(result) == 1

    def test_returns_empty_list_just_below_threshold(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Score just below threshold is excluded."""
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            similarity_threshold=0.7,
        )
        mock_vector_store.search_similar.return_value = [("doc-1", 0.699)]

        result = svc.search_structured("query")

        assert result == []


# ---------------------------------------------------------------------------
# TestFromAC_EntityResolution — entity_type from linked entities
# ---------------------------------------------------------------------------


class TestFromAC_EntityResolution:
    """search_structured resolves entity_type from linked knowledge-graph entities."""

    def test_entity_type_resolved_from_linked_entity(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """entity_type comes from linked entity when one exists."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C")
        mock_graph_store.list_entities_for_document.return_value = [
            _make_entity(EntityType.CONCEPT, "doc-1")
        ]

        result = service.search_structured("query")

        assert result[0].entity_type == EntityType.CONCEPT

    def test_entity_type_is_none_when_no_entity_linked(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """entity_type is None when no entities are linked to the document."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C")
        mock_graph_store.list_entities_for_document.return_value = []

        result = service.search_structured("query")

        assert result[0].entity_type is None

    def test_entity_type_uses_first_linked_entity(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """When multiple entities are linked, first entity's type is used."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C")
        mock_graph_store.list_entities_for_document.return_value = [
            _make_entity(EntityType.FUNCTION, "doc-1"),
            _make_entity(EntityType.CLASS_, "doc-1"),
        ]

        result = service.search_structured("query")

        assert result[0].entity_type == EntityType.FUNCTION

    def test_entity_type_checked_per_document(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """entity_type is resolved independently for each result document."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.90),
            ("doc-2", 0.80),
        ]

        def get_doc(doc_id: str) -> Document:
            return _make_doc(doc_id, f"T-{doc_id}", "C")

        def get_entities(doc_id: str) -> list[Entity]:
            if doc_id == "doc-1":
                return [_make_entity(EntityType.DECISION, doc_id)]
            return []

        mock_graph_store.get_document.side_effect = get_doc
        mock_graph_store.list_entities_for_document.side_effect = get_entities

        result = service.search_structured("query")

        assert result[0].entity_type == EntityType.DECISION
        assert result[1].entity_type is None

    def test_entity_type_field_accepts_all_entity_type_values(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """All EntityType enum values can appear as entity_type on results."""
        for etype in EntityType:
            mock_vector_store.search_similar.return_value = [("doc-x", 0.90)]
            mock_graph_store.get_document.return_value = _make_doc("doc-x", "T", "C")
            mock_graph_store.list_entities_for_document.return_value = [
                _make_entity(etype, "doc-x")
            ]

            result = service.search_structured("query")

            assert result[0].entity_type == etype


# ---------------------------------------------------------------------------
# TestFromAC_ErrorHandling — exceptions → [] with WARNING log
# ---------------------------------------------------------------------------


class TestFromAC_ErrorHandling:
    """search_structured catches exceptions and returns [] with WARNING log."""

    def test_vector_store_exception_returns_empty_list(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Exception raised by vector_store.search_similar → returns []."""
        mock_vector_store.search_similar.side_effect = RuntimeError("db failure")

        result = service.search_structured("query")

        assert result == []

    def test_exception_logs_warning(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Exception during search_structured is logged at WARNING level."""
        mock_vector_store.search_similar.side_effect = RuntimeError("oops")

        with caplog.at_level(logging.WARNING):
            service.search_structured("query")

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_graph_store_exception_returns_empty_list(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Exception raised by graph_store.get_document → returns []."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.side_effect = RuntimeError("graph error")

        result = service.search_structured("query")

        assert result == []

    def test_embedding_exception_returns_empty_list(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Exception during embedding → returns []."""
        mock_embedding_provider.embed_hybrid.side_effect = ValueError("bad embed")
        svc = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
        )

        result = svc.search_structured("query")

        assert result == []

    def test_exception_does_not_propagate(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """No exception escapes search_structured — callers get [] not a raise."""
        mock_vector_store.search_similar.side_effect = Exception("unexpected")

        try:
            result = service.search_structured("query")
        except Exception:  # noqa: BLE001
            pytest.fail("search_structured must not raise — it must return []")

        assert result == []


# ---------------------------------------------------------------------------
# TestFromAC_TopK — respects top_k parameter
# ---------------------------------------------------------------------------


class TestFromAC_TopK:
    """search_structured respects the top_k parameter."""

    def test_top_k_limits_number_of_results(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """top_k=2 returns at most 2 results even when more are available."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.90),
            ("doc-3", 0.85),
            ("doc-4", 0.80),
        ]
        mock_graph_store.get_document.side_effect = lambda d: _make_doc(d, f"T-{d}", "C")

        result = service.search_structured("query", top_k=2)

        assert len(result) <= 2

    def test_top_k_1_returns_single_result(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """top_k=1 returns exactly 1 result."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.90),
        ]
        mock_graph_store.get_document.side_effect = lambda d: _make_doc(d, f"T-{d}", "C")

        result = service.search_structured("query", top_k=1)

        assert len(result) == 1

    def test_top_k_returns_highest_scoring_results(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """top_k results are the highest-scoring ones (vector store ordering preserved)."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.90),
            ("doc-3", 0.85),
        ]
        mock_graph_store.get_document.side_effect = lambda d: _make_doc(d, f"T-{d}", "C")

        result = service.search_structured("query", top_k=2)

        scores = [r.score for r in result]
        assert sorted(scores, reverse=True) == scores

    def test_top_k_larger_than_results_returns_all(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """top_k > available results returns all results, not an error."""
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.90),
            ("doc-2", 0.80),
        ]
        mock_graph_store.get_document.side_effect = lambda d: _make_doc(d, f"T-{d}", "C")

        result = service.search_structured("query", top_k=100)

        assert len(result) == 2

    def test_top_k_zero_returns_empty_list(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """top_k=0 returns empty list."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "T", "C")

        result = service.search_structured("query", top_k=0)

        assert result == []

    def test_top_k_returns_exact_count_not_at_most(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """top_k=2 returns exactly 2 results when 4 are above threshold, not fewer.

        Strengthens the existing <= 2 assertion to pin the exact count.
        """
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.90),
            ("doc-3", 0.85),
            ("doc-4", 0.80),
        ]
        mock_graph_store.get_document.side_effect = lambda d: _make_doc(d, f"T-{d}", "C")

        result = service.search_structured("query", top_k=2)

        assert len(result) == 2

    def test_top_k_returns_exact_highest_scoring_doc_ids(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """top_k=2 returns exactly the two highest-scoring docs identified by doc_id.

        Pins exact membership: an implementation that drops the best hit or returns
        any two descending results would fail this test.
        """
        mock_vector_store.search_similar.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.90),
            ("doc-3", 0.85),
            ("doc-4", 0.80),
        ]
        mock_graph_store.get_document.side_effect = lambda d: _make_doc(d, f"T-{d}", "C")

        result = service.search_structured("query", top_k=2)

        returned_ids = [r.doc_id for r in result]
        assert returned_ids == ["doc-1", "doc-2"]

    def test_top_k_excludes_lower_scoring_docs(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Documents outside the top_k window are excluded from results."""
        mock_vector_store.search_similar.return_value = [
            ("doc-best", 0.95),
            ("doc-second", 0.88),
            ("doc-third", 0.82),
        ]
        mock_graph_store.get_document.side_effect = lambda d: _make_doc(d, f"T-{d}", "C")

        result = service.search_structured("query", top_k=2)

        returned_ids = {r.doc_id for r in result}
        assert "doc-third" not in returned_ids
        assert "doc-best" in returned_ids
        assert "doc-second" in returned_ids
