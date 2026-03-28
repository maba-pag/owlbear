"""Contract tests for task #70: StructuredSearchResult model, export, and AC coverage.

Complements test_knowledge_query_service_structured.py (owning task: #76) by covering
the AC lines that file does not explicitly address:

- AC line 1  — StructuredSearchResult is a *frozen* Pydantic BaseModel
- AC line 7  — query_for_context() behavior is unchanged after adding search_structured
- AC line 8  — StructuredSearchResult is exported via the lazy-import map in __init__.py

Owning task: #70
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.models import Document
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.query_service import (
    KnowledgeQueryService,
    StructuredSearchResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(doc_id: str, title: str, content: str, scope: str = "global") -> Document:
    return Document(id=doc_id, title=title, content=content, scope=scope)


def _make_service(
    mock_vector_store: MagicMock,
    mock_graph_store: MagicMock,
    mock_embedding_provider: MagicMock,
    **kwargs: object,
) -> KnowledgeQueryService:
    return KnowledgeQueryService(
        vector_store=mock_vector_store,
        graph_store=mock_graph_store,
        embedding_provider=mock_embedding_provider,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vector_store() -> MagicMock:
    store = MagicMock()
    store.search_similar = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_graph_store() -> MagicMock:
    store = MagicMock()
    store.get_document = MagicMock(return_value=None)
    store.list_entities_for_document = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    provider = MagicMock()
    provider.embed_hybrid = MagicMock(return_value=[HybridEmbedding(dense=[0.1, 0.2, 0.3])])
    return provider


@pytest.fixture
def service(
    mock_vector_store: MagicMock,
    mock_graph_store: MagicMock,
    mock_embedding_provider: MagicMock,
) -> KnowledgeQueryService:
    return _make_service(mock_vector_store, mock_graph_store, mock_embedding_provider)


# ---------------------------------------------------------------------------
# TestFromAC_ModelImmutability — AC line 1: frozen Pydantic BaseModel
# ---------------------------------------------------------------------------


class TestFromAC_ModelImmutability:
    """StructuredSearchResult is a *frozen* Pydantic BaseModel (AC line 1).

    Frozen means instances are immutable after construction — no in-place mutation.
    This is required so consumers can safely cache or hash result objects.
    """

    def test_model_raises_on_field_assignment(self) -> None:
        """Assigning to a field after construction raises ValidationError (frozen=True)."""
        result = StructuredSearchResult(
            doc_id="doc-1",
            title="Title",
            score=0.9,
            snippet="Content snippet",
            entity_type=None,
            scope="global",
        )
        with pytest.raises(ValidationError):
            result.doc_id = "mutated"  # type: ignore[misc]

    def test_model_raises_on_score_assignment(self) -> None:
        """Assigning to score after construction raises ValidationError."""
        result = StructuredSearchResult(
            doc_id="doc-1",
            title="T",
            score=0.5,
            snippet="S",
            entity_type=None,
            scope="g",
        )
        with pytest.raises(ValidationError):
            result.score = 0.99  # type: ignore[misc]

    def test_model_instance_is_hashable(self) -> None:
        """A frozen model must be hashable (suitable for sets and dict keys)."""
        result = StructuredSearchResult(
            doc_id="doc-1",
            title="Title",
            score=0.9,
            snippet="Content",
            entity_type=None,
            scope="global",
        )
        # Raises TypeError if not hashable — test would fail
        _ = hash(result)

    def test_equal_instances_have_equal_hash(self) -> None:
        """Two identical frozen instances hash equally."""
        make = lambda: StructuredSearchResult(  # noqa: E731
            doc_id="x", title="T", score=0.5, snippet="S", entity_type=None, scope="g"
        )
        assert hash(make()) == hash(make())

    def test_unequal_instances_have_different_hash_or_compare_unequal(self) -> None:
        """Two instances that differ in doc_id compare as not equal."""
        r1 = StructuredSearchResult(
            doc_id="doc-a", title="T", score=0.9, snippet="S", entity_type=None, scope="g"
        )
        r2 = StructuredSearchResult(
            doc_id="doc-b", title="T", score=0.9, snippet="S", entity_type=None, scope="g"
        )
        assert r1 != r2


# ---------------------------------------------------------------------------
# TestFromAC_PackageExport — AC line 8: exported via lazy-import map
# ---------------------------------------------------------------------------


class TestFromAC_PackageExport:
    """StructuredSearchResult is exported from owlbear.memory.knowledge (AC line 8).

    The lazy-import map in __init__.py must include the symbol so callers can
    do ``from owlbear.memory.knowledge import StructuredSearchResult`` without
    importing the full query_service module directly.
    """

    def test_structured_search_result_importable_from_package(self) -> None:
        """Direct import from the top-level package succeeds."""
        from owlbear.memory.knowledge import StructuredSearchResult

        assert StructuredSearchResult is not None

    def test_structured_search_result_in_package_all(self) -> None:
        """__all__ lists StructuredSearchResult so it appears in public API."""
        import owlbear.memory.knowledge as pkg

        assert "StructuredSearchResult" in pkg.__all__

    def test_lazy_import_returns_same_class_as_direct_import(self) -> None:
        """Lazy-import via package __getattr__ resolves to the same class object."""
        import owlbear.memory.knowledge as pkg
        from owlbear.memory.knowledge.query_service import (
            StructuredSearchResult as SSR_direct,
        )

        assert pkg.StructuredSearchResult is SSR_direct

    def test_structured_search_result_is_pydantic_model(self) -> None:
        """StructuredSearchResult is a Pydantic BaseModel subclass (AC field contract)."""
        from pydantic import BaseModel

        from owlbear.memory.knowledge import StructuredSearchResult as KnowledgeSSR

        assert issubclass(KnowledgeSSR, BaseModel)


# ---------------------------------------------------------------------------
# TestFromAC_QueryForContextUnchanged — AC line 7: no modification to existing API
# ---------------------------------------------------------------------------


class TestFromAC_QueryForContextUnchanged:
    """query_for_context() behavior is unchanged by the addition of search_structured.

    AC line 7 states that the existing public API and internal methods must not be
    modified. These tests confirm the signature, return type, and error behaviour
    remain as before.
    """

    def test_query_for_context_signature_has_required_params(self) -> None:
        """query_for_context(prompt, *, max_tokens, top_k) signature preserved."""
        sig = inspect.signature(KnowledgeQueryService.query_for_context)
        params = set(sig.parameters)
        assert "prompt" in params
        assert "max_tokens" in params
        assert "top_k" in params

    def test_query_for_context_max_tokens_default_is_2000(self) -> None:
        """Default max_tokens value is 2000 (unchanged from original contract)."""
        sig = inspect.signature(KnowledgeQueryService.query_for_context)
        assert sig.parameters["max_tokens"].default == 2000

    def test_query_for_context_top_k_default_is_5(self) -> None:
        """Default top_k value is 5 (unchanged from original contract)."""
        sig = inspect.signature(KnowledgeQueryService.query_for_context)
        assert sig.parameters["top_k"].default == 5

    def test_query_for_context_returns_none_when_no_results(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """query_for_context returns None when no documents are above threshold."""
        mock_vector_store.search_similar.return_value = []

        result = service.query_for_context("query with no matches")

        assert result is None

    def test_query_for_context_returns_string_when_results_above_threshold(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """query_for_context returns a non-empty string when relevant docs are found."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Title", "Content text")

        result = service.query_for_context("query")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_query_for_context_returns_none_on_exception(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
    ) -> None:
        """query_for_context catches all exceptions and returns None (graceful degradation)."""
        mock_vector_store.search_similar.side_effect = RuntimeError("store unavailable")

        result = service.query_for_context("failing query")

        assert result is None

    def test_search_structured_does_not_affect_query_for_context_output(
        self,
        service: KnowledgeQueryService,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        """Calling search_structured before query_for_context does not alter the result."""
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        mock_graph_store.get_document.return_value = _make_doc("doc-1", "Title", "Content text")
        mock_graph_store.list_entities_for_document.return_value = []

        # Call search_structured first
        _ = service.search_structured("prewarming call")

        # Then refresh mocks to simulate a fresh query_for_context call
        mock_vector_store.search_similar.return_value = [("doc-1", 0.90)]
        result = service.query_for_context("query")

        assert isinstance(result, str)
        assert len(result) > 0
