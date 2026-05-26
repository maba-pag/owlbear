"""Tests for QueryFacade.search — task #1879.

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/query.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/query_facade.py

AC coverage:
  AC1 — search() constructs ContentSearchQuery from matching fields (text,
         top_k, scopes, source_ids, min_score) and awaits ContentStore.search;
         raises ValueError when request.text is empty
  AC2 — When include_graph=True and hits exist: claims_for_chunk called per
         chunk.id; traverse called for unique seeds with correct TraversalQuery
         (entity_id, max_hops=graph_hops, relation_types); results merged with
         entity/edge deduplication; LookupError from traverse silently skipped
  AC3 — graph_context is None when include_graph=False, search returns no hits,
         no entity seeds found, or all traversals raise LookupError
  AC4 — entity_types post-filters graph_context: retains only entities matching
         entity_type; removes edges where either endpoint is excluded; empty
         entity_types = no filter applied
  AC5 — Provenance per hit: chunk_id, document_id, source_id, exact_text
         (=chunk.text), title (from get_document), uri, section_path, score
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.protocols.common import EntityType, RelationType
from owlbear_knowledge.protocols.content import (
    ContentChunk,
    ContentDocument,
    ContentSearchResult,
)
from owlbear_knowledge.protocols.graph import (
    ChunkClaims,
    EdgeRecord,
    EntityRecord,
    TraversalQuery,
    TraversalResult,
)
from owlbear_knowledge.protocols.query import QueryRequest
from owlbear_knowledge.query_facade import QueryFacade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_chunk(  # noqa: PLR0913
    *,
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    source_id: str = "src-1",
    text: str = "Some chunk text",
    uri: str | None = None,
    section_path: tuple[str, ...] = (),
) -> ContentChunk:
    return ContentChunk(
        id=chunk_id,
        document_id=document_id,
        source_id=source_id,
        index=0,
        text=text,
        content_hash="abc123",
        scope="global",
        uri=uri,
        section_path=section_path,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_search_result(
    chunk: ContentChunk,
    score: float = 0.9,
) -> ContentSearchResult:
    return ContentSearchResult(chunk=chunk, score=score)


def _make_entity(
    entity_id: str,
    entity_type: EntityType = EntityType.CONCEPT,
) -> EntityRecord:
    return EntityRecord(
        id=entity_id,
        name=f"Entity {entity_id}",
        canonical_name=f"entity {entity_id}",
        entity_type=entity_type,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_edge(
    edge_id: str,
    source_entity_id: str,
    target_entity_id: str,
) -> EdgeRecord:
    return EdgeRecord(
        id=edge_id,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relation_type=RelationType.RELATED_TO,
        weight=1.0,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_traversal_result(
    entities: list[EntityRecord] | None = None,
    edges: list[EdgeRecord] | None = None,
) -> TraversalResult:
    return TraversalResult(
        entities=tuple(entities or []),
        edges=tuple(edges or []),
    )


def _make_claims(
    chunk_id: str,
    entity_ids: tuple[str, ...] = (),
) -> ChunkClaims:
    return ChunkClaims(chunk_id=chunk_id, entity_ids=entity_ids)


def _make_document(
    document_id: str = "doc-1",
    title: str = "Test Document",
    uri: str | None = None,
) -> ContentDocument:
    return ContentDocument(
        document_id=document_id,
        source_id="src-1",
        title=title,
        uri=uri,
        content_hash="abc123",
        ingested_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_content() -> MagicMock:
    """Mocked ContentStore with async search and sync get_document."""
    m = MagicMock(name="content_store")
    m.search = AsyncMock(return_value=())
    m.get_document.return_value = _make_document()
    return m


@pytest.fixture()
def mock_graph() -> MagicMock:
    """Mocked GraphStore with sync claims_for_chunk and traverse."""
    g = MagicMock(name="graph_store")
    g.claims_for_chunk.return_value = _make_claims("chunk-1")
    g.traverse.return_value = _make_traversal_result()
    return g


@pytest.fixture()
def facade(mock_content: MagicMock, mock_graph: MagicMock) -> QueryFacade:
    """QueryFacade wired with mocked dependencies."""
    return QueryFacade(content=mock_content, graph=mock_graph)


# ---------------------------------------------------------------------------
# TestFromAC_QueryFacadeSearch
# ---------------------------------------------------------------------------


class TestFromAC_QueryFacadeSearch:
    """Tests for QueryFacade.search() — covers AC1-AC5."""

    # --- AC1: ContentSearchQuery construction and ValueError ---

    @pytest.mark.asyncio
    async def test_search_passes_text_to_content_store(
        self, facade: QueryFacade, mock_content: MagicMock
    ) -> None:
        """AC1: search() passes request.text into ContentSearchQuery.text."""
        request = QueryRequest(text="hello world", include_graph=False)
        await facade.search(request)
        called_query = mock_content.search.call_args[0][0]
        assert called_query.text == "hello world"

    @pytest.mark.asyncio
    async def test_search_passes_top_k_to_content_store(
        self, facade: QueryFacade, mock_content: MagicMock
    ) -> None:
        """AC1: search() passes request.top_k into ContentSearchQuery.top_k."""
        request = QueryRequest(text="query", top_k=5, include_graph=False)
        await facade.search(request)
        called_query = mock_content.search.call_args[0][0]
        assert called_query.top_k == 5

    @pytest.mark.asyncio
    async def test_search_passes_scopes_to_content_store(
        self, facade: QueryFacade, mock_content: MagicMock
    ) -> None:
        """AC1: search() passes request.scopes into ContentSearchQuery.scopes."""
        request = QueryRequest(
            text="query", scopes=("private", "public"), include_graph=False
        )
        await facade.search(request)
        called_query = mock_content.search.call_args[0][0]
        assert called_query.scopes == ("private", "public")

    @pytest.mark.asyncio
    async def test_search_passes_source_ids_to_content_store(
        self, facade: QueryFacade, mock_content: MagicMock
    ) -> None:
        """AC1: search() passes request.source_ids into ContentSearchQuery.source_ids."""
        request = QueryRequest(
            text="query", source_ids=("src-a", "src-b"), include_graph=False
        )
        await facade.search(request)
        called_query = mock_content.search.call_args[0][0]
        assert called_query.source_ids == ("src-a", "src-b")

    @pytest.mark.asyncio
    async def test_search_passes_min_score_to_content_store(
        self, facade: QueryFacade, mock_content: MagicMock
    ) -> None:
        """AC1: search() passes request.min_score into ContentSearchQuery.min_score."""
        request = QueryRequest(text="query", min_score=0.5, include_graph=False)
        await facade.search(request)
        called_query = mock_content.search.call_args[0][0]
        assert called_query.min_score == 0.5

    @pytest.mark.asyncio
    async def test_search_includes_content_results_in_output(
        self, facade: QueryFacade, mock_content: MagicMock
    ) -> None:
        """AC1: QueryResult.search_results contains the ContentStore results."""
        chunk = _make_chunk(chunk_id="chunk-1")
        hit = _make_search_result(chunk, score=0.85)
        mock_content.search.return_value = (hit,)
        request = QueryRequest(text="query", include_graph=False)
        result = await facade.search(request)
        assert len(result.search_results) == 1
        assert result.search_results[0].score == 0.85
        assert result.search_results[0].chunk.id == "chunk-1"

    @pytest.mark.asyncio
    async def test_search_raises_value_error_on_empty_text(
        self, facade: QueryFacade
    ) -> None:
        """AC1: search() raises ValueError when request.text is empty."""
        with pytest.raises(ValueError):
            await facade.search(QueryRequest(text=""))

    # --- AC2: Graph expansion with include_graph=True ---

    @pytest.mark.asyncio
    async def test_graph_expansion_calls_claims_for_each_chunk(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: claims_for_chunk is called with each chunk.id from search results."""
        chunk_a = _make_chunk(chunk_id="chunk-a")
        chunk_b = _make_chunk(chunk_id="chunk-b")
        mock_content.search.return_value = (
            _make_search_result(chunk_a),
            _make_search_result(chunk_b),
        )
        mock_graph.claims_for_chunk.return_value = _make_claims("x")
        request = QueryRequest(text="query", include_graph=True)
        await facade.search(request)
        chunk_ids_called = {c.args[0] for c in mock_graph.claims_for_chunk.call_args_list}
        assert "chunk-a" in chunk_ids_called
        assert "chunk-b" in chunk_ids_called

    @pytest.mark.asyncio
    async def test_graph_expansion_traverses_with_correct_max_hops(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: traverse is called with max_hops == request.graph_hops."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("e1",)
        )
        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[_make_entity("e1")]
        )
        request = QueryRequest(text="query", include_graph=True, graph_hops=3)
        await facade.search(request)
        traversal_query: TraversalQuery = mock_graph.traverse.call_args[0][0]
        assert traversal_query.entity_id == "e1"
        assert traversal_query.max_hops == 3

    @pytest.mark.asyncio
    async def test_graph_expansion_passes_relation_types_to_traverse(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: traverse is called with relation_types == request.relation_types."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("e1",)
        )
        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[_make_entity("e1")]
        )
        rel_types = (RelationType.DEPENDS_ON, RelationType.IMPLEMENTS)
        request = QueryRequest(
            text="query", include_graph=True, relation_types=rel_types
        )
        await facade.search(request)
        traversal_query: TraversalQuery = mock_graph.traverse.call_args[0][0]
        assert traversal_query.relation_types == rel_types

    @pytest.mark.asyncio
    async def test_graph_expansion_deduplicates_entity_seeds(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: same entity_id appearing in multiple chunks is traversed only once."""
        chunk_a = _make_chunk(chunk_id="chunk-a")
        chunk_b = _make_chunk(chunk_id="chunk-b")
        mock_content.search.return_value = (
            _make_search_result(chunk_a),
            _make_search_result(chunk_b),
        )
        # both chunks claim the same entity
        mock_graph.claims_for_chunk.side_effect = lambda cid: _make_claims(
            cid, entity_ids=("e1",)
        )
        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[_make_entity("e1")]
        )
        request = QueryRequest(text="query", include_graph=True)
        await facade.search(request)
        assert mock_graph.traverse.call_count == 1

    @pytest.mark.asyncio
    async def test_graph_expansion_skips_lookup_error_seeds(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: LookupError from traverse is silently skipped; other seeds still produce results."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("e-bad", "e-good")
        )
        entity_ok = _make_entity("e-good")

        def _traverse_side_effect(q: TraversalQuery) -> TraversalResult:
            if q.entity_id == "e-bad":
                msg = "entity not found"
                raise LookupError(msg)
            return _make_traversal_result(entities=[entity_ok])

        mock_graph.traverse.side_effect = _traverse_side_effect
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        # no LookupError propagated; graph_context has results from e-good
        assert result.graph_context is not None
        entity_ids_in_result = {e.id for e in result.graph_context.entities}
        assert "e-good" in entity_ids_in_result

    @pytest.mark.asyncio
    async def test_graph_expansion_merges_traversal_results(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: traversal results from multiple seeds are merged into one TraversalResult."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("e1", "e2")
        )
        e1 = _make_entity("e1")
        e2 = _make_entity("e2")
        edge = _make_edge("edge-1", "e1", "e2")

        def _traverse(q: TraversalQuery) -> TraversalResult:
            if q.entity_id == "e1":
                return _make_traversal_result(entities=[e1], edges=[edge])
            return _make_traversal_result(entities=[e2])

        mock_graph.traverse.side_effect = _traverse
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.graph_context is not None
        entity_ids = {e.id for e in result.graph_context.entities}
        assert "e1" in entity_ids
        assert "e2" in entity_ids
        edge_ids = {e.id for e in result.graph_context.edges}
        assert "edge-1" in edge_ids

    @pytest.mark.asyncio
    async def test_graph_expansion_deduplicates_merged_entities(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: entities returned by multiple traversal results appear only once."""
        chunk_a = _make_chunk(chunk_id="chunk-a")
        chunk_b = _make_chunk(chunk_id="chunk-b")
        mock_content.search.return_value = (
            _make_search_result(chunk_a),
            _make_search_result(chunk_b),
        )
        mock_graph.claims_for_chunk.side_effect = lambda cid: _make_claims(
            cid, entity_ids=("e1",) if cid == "chunk-a" else ("e2",)
        )
        shared_entity = _make_entity("e-shared")

        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[shared_entity]
        )
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.graph_context is not None
        entity_ids = [e.id for e in result.graph_context.entities]
        assert entity_ids.count("e-shared") == 1

    # --- AC3: graph_context is None ---

    @pytest.mark.asyncio
    async def test_no_graph_context_when_include_graph_false(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC3: graph_context is None when include_graph=False; traverse not called."""
        chunk = _make_chunk()
        mock_content.search.return_value = (_make_search_result(chunk),)
        request = QueryRequest(text="query", include_graph=False)
        result = await facade.search(request)
        assert result.graph_context is None
        mock_graph.traverse.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_graph_context_when_search_returns_no_hits(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC3: graph_context is None when ContentStore.search returns empty results."""
        mock_content.search.return_value = ()
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.graph_context is None
        mock_graph.traverse.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_graph_context_when_no_entity_seeds(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC3: graph_context is None when claims_for_chunk yields no entity_ids."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims("chunk-1", entity_ids=())
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.graph_context is None
        mock_graph.traverse.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_graph_context_when_all_traversals_raise_lookup_error(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC3: graph_context is None when every traverse call raises LookupError."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("e1", "e2")
        )
        mock_graph.traverse.side_effect = LookupError("not found")
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.graph_context is None

    # --- AC4: entity_types post-filter ---

    @pytest.mark.asyncio
    async def test_entity_types_filter_retains_matching_entities(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC4: only entities with entity_type in request.entity_types are kept."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("seed",)
        )
        concept_entity = _make_entity("e-concept", entity_type=EntityType.CONCEPT)
        person_entity = _make_entity("e-person", entity_type=EntityType.PERSON)
        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[concept_entity, person_entity]
        )
        request = QueryRequest(
            text="query", include_graph=True, entity_types=(EntityType.CONCEPT,)
        )
        result = await facade.search(request)
        assert result.graph_context is not None
        entity_ids = {e.id for e in result.graph_context.entities}
        assert "e-concept" in entity_ids
        assert "e-person" not in entity_ids

    @pytest.mark.asyncio
    async def test_entity_types_filter_removes_edges_with_excluded_endpoints(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC4: edges removed when either source or target entity is excluded."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("seed",)
        )
        concept_entity = _make_entity("e-concept", entity_type=EntityType.CONCEPT)
        person_entity = _make_entity("e-person", entity_type=EntityType.PERSON)
        # edge spans kept ↔ excluded endpoint
        mixed_edge = _make_edge("edge-mixed", "e-concept", "e-person")
        # edge spans two kept endpoints
        concept_edge = _make_edge("edge-concepts", "e-concept", "e-concept")
        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[concept_entity, person_entity],
            edges=[mixed_edge, concept_edge],
        )
        request = QueryRequest(
            text="query", include_graph=True, entity_types=(EntityType.CONCEPT,)
        )
        result = await facade.search(request)
        assert result.graph_context is not None
        edge_ids = {e.id for e in result.graph_context.edges}
        assert "edge-mixed" not in edge_ids
        assert "edge-concepts" in edge_ids

    @pytest.mark.asyncio
    async def test_empty_entity_types_applies_no_filter(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC4: empty entity_types tuple — all entities and edges retained."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("seed",)
        )
        concept = _make_entity("e-concept", entity_type=EntityType.CONCEPT)
        person = _make_entity("e-person", entity_type=EntityType.PERSON)
        edge = _make_edge("edge-1", "e-concept", "e-person")
        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[concept, person], edges=[edge]
        )
        request = QueryRequest(text="query", include_graph=True, entity_types=())
        result = await facade.search(request)
        assert result.graph_context is not None
        entity_ids = {e.id for e in result.graph_context.entities}
        assert "e-concept" in entity_ids
        assert "e-person" in entity_ids
        edge_ids = {e.id for e in result.graph_context.edges}
        assert "edge-1" in edge_ids

    # --- AC5: Provenance assembly ---

    @pytest.mark.asyncio
    async def test_provenance_chunk_fields_and_score_populated(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: chunk_id, document_id, source_id, exact_text (=chunk.text), score."""
        chunk = _make_chunk(
            chunk_id="chunk-42",
            document_id="doc-99",
            source_id="src-7",
            text="The exact chunk text",
        )
        mock_content.search.return_value = (_make_search_result(chunk, score=0.77),)
        mock_graph.claims_for_chunk.return_value = _make_claims("chunk-42")
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert len(result.provenance) == 1
        prov = result.provenance[0]
        assert prov.chunk_id == "chunk-42"
        assert prov.document_id == "doc-99"
        assert prov.source_id == "src-7"
        assert prov.exact_text == "The exact chunk text"
        assert prov.score == 0.77

    @pytest.mark.asyncio
    async def test_provenance_title_from_get_document(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: title is fetched from get_document(chunk.document_id).title."""
        chunk = _make_chunk(chunk_id="chunk-1", document_id="doc-abc")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_content.get_document.return_value = _make_document(
            document_id="doc-abc", title="My Important Document"
        )
        mock_graph.claims_for_chunk.return_value = _make_claims("chunk-1")
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        mock_content.get_document.assert_called_with("doc-abc")
        assert result.provenance[0].title == "My Important Document"

    @pytest.mark.asyncio
    async def test_provenance_uri_propagated(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: uri is populated from chunk.uri."""
        chunk = _make_chunk(chunk_id="chunk-1", uri="https://example.com/doc")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims("chunk-1")
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.provenance[0].uri == "https://example.com/doc"

    @pytest.mark.asyncio
    async def test_provenance_uri_none_when_chunk_has_no_uri(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: uri=None in provenance when chunk.uri is None."""
        chunk = _make_chunk(chunk_id="chunk-1", uri=None)
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims("chunk-1")
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.provenance[0].uri is None

    @pytest.mark.asyncio
    async def test_provenance_section_path_propagated(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: section_path is populated from chunk.section_path."""
        chunk = _make_chunk(
            chunk_id="chunk-1", section_path=("Chapter 1", "Section 2")
        )
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims("chunk-1")
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.provenance[0].section_path == ("Chapter 1", "Section 2")

    # --- Retry gaps: reviewer Required Follow-up ---

    # Gap 1 (AC1): isinstance proof — ContentStore.search receives a real ContentSearchQuery
    @pytest.mark.asyncio
    async def test_search_forwards_content_search_query_instance(
        self, facade: QueryFacade, mock_content: MagicMock
    ) -> None:
        """AC1: ContentStore.search receives a ContentSearchQuery instance with all fields mapped."""
        request = QueryRequest(
            text="find me",
            top_k=7,
            scopes=("global",),
            source_ids=("s1",),
            min_score=0.4,
            include_graph=False,
        )
        await facade.search(request)
        called_query = mock_content.search.call_args[0][0]
        from owlbear_knowledge.protocols.content import ContentSearchQuery  # noqa: PLC0415
        assert isinstance(called_query, ContentSearchQuery)
        assert called_query.text == "find me"
        assert called_query.top_k == 7
        assert called_query.scopes == ("global",)
        assert called_query.source_ids == ("s1",)
        assert called_query.min_score == 0.4

    # Gap 2a (AC2): exact unique seed set traversed
    @pytest.mark.asyncio
    async def test_graph_expansion_traverses_exact_unique_seed_set(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: traverse is called for the exact set of unique entity_ids, no more, no less."""
        chunk_a = _make_chunk(chunk_id="chunk-a")
        chunk_b = _make_chunk(chunk_id="chunk-b")
        mock_content.search.return_value = (
            _make_search_result(chunk_a),
            _make_search_result(chunk_b),
        )
        # chunk-a claims e1 and e2; chunk-b claims e2 (duplicate) and e3
        mock_graph.claims_for_chunk.side_effect = lambda cid: _make_claims(
            cid, entity_ids=("e1", "e2") if cid == "chunk-a" else ("e2", "e3")
        )
        mock_graph.traverse.side_effect = lambda q: _make_traversal_result(
            entities=[_make_entity(q.entity_id)]
        )
        request = QueryRequest(text="query", include_graph=True)
        await facade.search(request)
        traversed_seeds = {c.args[0].entity_id for c in mock_graph.traverse.call_args_list}
        assert traversed_seeds == {"e1", "e2", "e3"}
        assert mock_graph.traverse.call_count == 3

    # Gap 2b (AC2): duplicate edge IDs from multiple traversals collapse to one
    @pytest.mark.asyncio
    async def test_graph_expansion_deduplicates_merged_edges(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC2: same edge ID returned by multiple traversals appears exactly once in graph_context."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("e1", "e2")
        )
        e1 = _make_entity("e1")
        e2 = _make_entity("e2")
        shared_edge = _make_edge("edge-shared", "e1", "e2")
        # both traversals return the same shared edge
        mock_graph.traverse.side_effect = lambda _: _make_traversal_result(
            entities=[e1, e2], edges=[shared_edge]
        )
        request = QueryRequest(text="query", include_graph=True)
        result = await facade.search(request)
        assert result.graph_context is not None
        edge_ids = [e.id for e in result.graph_context.edges]
        assert edge_ids.count("edge-shared") == 1

    # Gap 3 (AC4): edge removed when source endpoint references an excluded entity
    @pytest.mark.asyncio
    async def test_entity_types_filter_removes_edge_with_excluded_source_endpoint(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC4: edge removed when source_entity_id references an excluded entity type."""
        chunk = _make_chunk(chunk_id="chunk-1")
        mock_content.search.return_value = (_make_search_result(chunk),)
        mock_graph.claims_for_chunk.return_value = _make_claims(
            "chunk-1", entity_ids=("seed",)
        )
        concept_entity = _make_entity("e-concept", entity_type=EntityType.CONCEPT)
        person_entity = _make_entity("e-person", entity_type=EntityType.PERSON)
        # source=e-person (excluded), target=e-concept (kept) → edge must be removed
        source_excluded_edge = _make_edge("edge-src-excl", "e-person", "e-concept")
        # both endpoints kept → edge must be retained
        kept_edge = _make_edge("edge-kept", "e-concept", "e-concept")
        mock_graph.traverse.return_value = _make_traversal_result(
            entities=[concept_entity, person_entity],
            edges=[source_excluded_edge, kept_edge],
        )
        request = QueryRequest(
            text="query", include_graph=True, entity_types=(EntityType.CONCEPT,)
        )
        result = await facade.search(request)
        assert result.graph_context is not None
        edge_ids = {e.id for e in result.graph_context.edges}
        assert "edge-src-excl" not in edge_ids
        assert "edge-kept" in edge_ids

    # Gap 4 (AC5): one provenance record emitted per search hit
    @pytest.mark.asyncio
    async def test_provenance_one_record_per_search_hit(
        self,
        facade: QueryFacade,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """AC5: provenance contains exactly one record for each search result hit."""
        chunk_a = _make_chunk(chunk_id="chunk-a", document_id="doc-a", source_id="src-a", text="text a")
        chunk_b = _make_chunk(chunk_id="chunk-b", document_id="doc-b", source_id="src-b", text="text b")
        chunk_c = _make_chunk(chunk_id="chunk-c", document_id="doc-c", source_id="src-c", text="text c")
        mock_content.search.return_value = (
            _make_search_result(chunk_a, score=0.9),
            _make_search_result(chunk_b, score=0.8),
            _make_search_result(chunk_c, score=0.7),
        )
        mock_content.get_document.side_effect = lambda did: _make_document(
            document_id=did, title=f"Doc {did}"
        )
        mock_graph.claims_for_chunk.return_value = _make_claims("x")
        request = QueryRequest(text="query", include_graph=False)
        result = await facade.search(request)
        assert len(result.provenance) == 3
        chunk_ids = {p.chunk_id for p in result.provenance}
        assert chunk_ids == {"chunk-a", "chunk-b", "chunk-c"}
        scores = {p.chunk_id: p.score for p in result.provenance}
        assert scores["chunk-a"] == 0.9
        assert scores["chunk-b"] == 0.8
        assert scores["chunk-c"] == 0.7
