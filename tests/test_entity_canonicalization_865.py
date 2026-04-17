"""RED-phase tests for #865: Entity name canonicalization for cross-source matching.

AC coverage:
  AC1: Entity.canonical_name derived field — lowercase, collapse whitespace,
       strip leading articles (the/a/an), strip leading/trailing punctuation
  AC2: _collect_candidates() uses canonical_name for pre-filtering alongside
       vector similarity (union semantics — canonical adds matches beyond vector)
  AC3: Conservative normalization — "Data Classification Framework" must remain
       distinct from "data classification"
  AC4: Tests verify canonicalization and pre-filter behavior (this file)

All tests FAIL until #865 adds canonical_name to Entity and canonical blocking
to _collect_candidates().
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.inter_doc_graph_builder import InterDocGraphBuilder
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Edge, Entity, EntityType
from owlbear_knowledge.protocol import StructuredExtractor, VectorStoreProtocol


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(name: str, doc_id: str = "doc1") -> Entity:
    return Entity(name=name, entity_type=EntityType.CONCEPT, scope="global", document_id=doc_id)


def _async_extractor(edges: list[Edge] | None = None) -> MagicMock:
    mock = MagicMock(spec=StructuredExtractor)
    mock.extract = AsyncMock(return_value=ExtractionResult(edges=edges or []))
    return mock


def _vector_store_no_matches() -> MagicMock:
    """Vector store that always returns empty results — forces canonical path to be the only discoverer."""
    mock = MagicMock(spec=VectorStoreProtocol)
    mock.get_embedding.return_value = [0.1] * 1024
    mock.search_similar.return_value = []
    return mock


def _mock_graph_store(existing_edges: list[Edge] | None = None) -> MagicMock:
    mock = MagicMock(spec=GraphStore)
    mock.list_edges.return_value = existing_edges or []
    return mock


# ---------------------------------------------------------------------------
# TestFromAC_CanonicalName — AC1: canonical_name derived field on Entity
# ---------------------------------------------------------------------------


class TestFromAC_CanonicalName:
    """AC1: Entity.canonical_name — lowercase, whitespace-collapsed, article/punct-stripped."""

    # --- Happy path ---

    def test_canonical_name_lowercases_mixed_case(self) -> None:
        """canonical_name converts all characters to lowercase."""
        e = _entity("Data Classification")
        assert e.canonical_name == "data classification"

    def test_canonical_name_collapses_internal_whitespace(self) -> None:
        """Multiple consecutive spaces inside the name are collapsed to one."""
        e = _entity("data  classification")
        assert e.canonical_name == "data classification"

    def test_canonical_name_strips_leading_article_the(self) -> None:
        """Leading word 'the' is stripped (case-insensitive)."""
        e = _entity("The Data Policy")
        assert e.canonical_name == "data policy"

    def test_canonical_name_strips_leading_article_a(self) -> None:
        """Leading word 'a' is stripped."""
        e = _entity("A Data Policy")
        assert e.canonical_name == "data policy"

    def test_canonical_name_strips_leading_article_an(self) -> None:
        """Leading word 'an' is stripped."""
        e = _entity("An Architecture Decision")
        assert e.canonical_name == "architecture decision"

    def test_canonical_name_strips_leading_punctuation(self) -> None:
        """Leading punctuation characters are removed."""
        e = _entity(".Data Classification")
        assert e.canonical_name == "data classification"

    def test_canonical_name_strips_trailing_punctuation(self) -> None:
        """Trailing punctuation characters are removed."""
        e = _entity("Data Classification.")
        assert e.canonical_name == "data classification"

    # --- Edge cases ---

    def test_canonical_name_article_strip_is_case_insensitive(self) -> None:
        """Article stripping works regardless of the case of the article word."""
        e = _entity("THE data policy")
        assert e.canonical_name == "data policy"

    def test_canonical_name_article_mid_string_is_preserved(self) -> None:
        """An article word that is NOT the leading word must NOT be stripped."""
        e = _entity("authenticate the user")
        assert "the" in e.canonical_name

    def test_canonical_name_already_normalized_unchanged(self) -> None:
        """A name already in canonical form is returned unchanged."""
        e = _entity("data classification")
        assert e.canonical_name == "data classification"

    def test_canonical_name_collapses_tab_whitespace(self) -> None:
        """Tabs and other whitespace are also collapsed to a single space."""
        e = _entity("data\tclassification")
        assert e.canonical_name == "data classification"

    # --- Boundary conditions ---

    def test_canonical_name_leading_and_trailing_punctuation_both_stripped(self) -> None:
        """Both leading and trailing punctuation are stripped in combination."""
        e = _entity("-data classification-")
        assert e.canonical_name == "data classification"

    def test_canonical_name_name_is_just_article_becomes_empty_or_stripped(self) -> None:
        """A name consisting only of an article collapses to empty string after strip."""
        e = _entity("The")
        # After lower → "the", strip leading article yields "" or stripped result
        assert e.canonical_name == "" or "the" not in e.canonical_name.split()

    # --- AC3: Conservative normalization — distinct names stay distinct ---

    def test_data_classification_framework_distinct_from_data_classification(self) -> None:
        """AC3: 'Data Classification Framework' and 'data classification' are NOT equal after normalization."""
        e_framework = _entity("Data Classification Framework")
        e_plain = _entity("data classification")
        assert e_framework.canonical_name != e_plain.canonical_name

    def test_suffix_word_framework_is_preserved(self) -> None:
        """Word 'framework' (non-article, non-punct) is kept — conservative normalization."""
        e = _entity("Data Classification Framework")
        assert "framework" in e.canonical_name


# ---------------------------------------------------------------------------
# TestFromAC_CanonicalPreFilter — AC2: _collect_candidates() canonical blocking
# ---------------------------------------------------------------------------


class TestFromAC_CanonicalPreFilter:
    """AC2: _collect_candidates() unites canonical-name blocking with vector similarity."""

    def _builder(self, existing_edges: list[Edge] | None = None) -> InterDocGraphBuilder:
        return InterDocGraphBuilder(
            extractor=_async_extractor(),
            vector_store=_vector_store_no_matches(),
            graph_store=_mock_graph_store(existing_edges),
        )

    def test_canonical_match_cross_doc_appears_in_candidates(self) -> None:
        """Entities sharing canonical_name but in different documents appear as candidates
        even when the vector store returns no similar results."""
        e1 = _entity("Data Classification", doc_id="doc1")
        e2 = _entity("data classification", doc_id="doc2")
        entity_by_id = {e1.id: e1, e2.id: e2}
        builder = self._builder()

        candidates = builder._collect_candidates([e1, e2], entity_by_id, set())

        pair_ids = {(a.id, b.id) for a, b in candidates}
        assert (e1.id, e2.id) in pair_ids or (e2.id, e1.id) in pair_ids

    def test_three_entities_same_canonical_different_docs_all_become_candidates(self) -> None:
        """Three entities sharing canonical_name across three separate documents
        all produce cross-doc candidate pairs."""
        e1 = _entity("Data Classification", doc_id="doc1")
        e2 = _entity("data classification", doc_id="doc2")
        e3 = _entity("DATA CLASSIFICATION", doc_id="doc3")
        entity_by_id = {e1.id: e1, e2.id: e2, e3.id: e3}
        builder = self._builder()

        candidates = builder._collect_candidates([e1, e2, e3], entity_by_id, set())

        assert len(candidates) >= 2, "Expected at least one pair per entity from canonical group"

    @pytest.mark.asyncio
    async def test_build_calls_extractor_for_canonical_matched_pair(self) -> None:
        """build() sends canonical-matched cross-doc pairs to the extractor even
        when vector store finds no similar entities."""
        e1 = _entity("Data Classification", doc_id="doc1")
        e2 = _entity("data classification", doc_id="doc2")
        extractor = _async_extractor()
        builder = InterDocGraphBuilder(
            extractor=extractor,
            vector_store=_vector_store_no_matches(),
            graph_store=_mock_graph_store(),
        )

        await builder.build([e1, e2], scope="global")

        assert extractor.extract.called, "extractor.extract must be called because (e1,e2) canonical-match across docs"


# ---------------------------------------------------------------------------
# TestBuilderDiscovered — edge cases found during GREEN phase
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered edge cases in _canonical_candidates()."""

    def _builder(self) -> InterDocGraphBuilder:
        return InterDocGraphBuilder(
            extractor=_async_extractor(),
            vector_store=_vector_store_no_matches(),
            graph_store=_mock_graph_store(),
        )

    def test_same_document_canonical_pair_excluded(self) -> None:
        """Two entities with the same canonical_name in the SAME document are NOT candidates.

        Canonical blocking must skip intra-document pairs — only cross-doc matching is intended.
        """
        e1 = _entity("Data Classification", doc_id="doc1")
        e2 = _entity("data classification", doc_id="doc1")  # same doc
        entity_by_id = {e1.id: e1, e2.id: e2}
        builder = self._builder()

        candidates = builder._collect_candidates([e1, e2], entity_by_id, set())

        assert len(candidates) == 0, "Same-document canonical pair must not be included"

    def test_canonical_pair_in_existing_pairs_excluded(self) -> None:
        """A canonical-match cross-doc pair that already has a recorded edge is NOT returned.

        Canonical blocking must respect existing_pairs to avoid re-inferring known edges.
        """
        e1 = _entity("Data Classification", doc_id="doc1")
        e2 = _entity("data classification", doc_id="doc2")
        entity_by_id = {e1.id: e1, e2.id: e2}
        existing: set[tuple[str, str]] = {(e1.id, e2.id)}
        builder = self._builder()

        candidates = builder._collect_candidates([e1, e2], entity_by_id, existing)

        assert len(candidates) == 0, "Canonical pair already in existing_pairs must be excluded"
