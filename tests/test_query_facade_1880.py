"""Tests for QueryFacade.lookup_entity + render_context — task #1880.

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/query.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/query_facade.py

AC coverage:
  AC1 — lookup_entity resolves entity by ID (get_entity) or name
         (find_entities + optional entity_type filter); raises LookupError
         when entity not found by either path
  AC2 — EntityLookupResult populates entity record, neighbourhood
         (traverse within expand_hops; None when expand_hops=0), and
         related_chunks (chunk_ids_for_entity → get_chunk; empty when
         no evidence)
  AC3 — render_context formats QueryResult and/or EntityLookupResult as
         structured text within max_chars; raises ValueError when neither
         result is provided in request
  AC4 — render sets RenderedContext.truncated=True when budget exceeded;
         includes source attribution when include_provenance=True;
         populates char_count, chunk_count, entity_count from rendered
         content
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.protocols.common import EntityType, RelationType
from owlbear_knowledge.protocols.content import ContentChunk
from owlbear_knowledge.protocols.graph import (
    EdgeRecord,
    EntityQuery,
    EntityRecord,
    TraversalQuery,
    TraversalResult,
)
from owlbear_knowledge.protocols.query import (
    ContextRenderRequest,
    EntityLookupRequest,
    EntityLookupResult,
    QueryResult,
    RenderedContext,
)
from owlbear_knowledge.query_facade import QueryFacade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_entity(
    entity_id: str = "ent-1",
    name: str = "Alice",
    entity_type: EntityType = EntityType.PERSON,
) -> EntityRecord:
    return EntityRecord(
        id=entity_id,
        name=name,
        canonical_name=name.lower(),
        entity_type=entity_type,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_chunk(
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    source_id: str = "src-1",
    text: str = "Some relevant text",
) -> ContentChunk:
    return ContentChunk(
        id=chunk_id,
        document_id=document_id,
        source_id=source_id,
        index=0,
        text=text,
        content_hash="hash123",
        scope="global",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_edge(
    edge_id: str = "edge-1",
    source_entity_id: str = "ent-1",
    target_entity_id: str = "ent-2",
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


def _make_traversal(
    entities: list[EntityRecord] | None = None,
    edges: list[EdgeRecord] | None = None,
) -> TraversalResult:
    return TraversalResult(
        entities=tuple(entities or []),
        edges=tuple(edges or []),
    )


def _make_query_result(
    search_results: tuple = (),
    graph_context: TraversalResult | None = None,
) -> QueryResult:
    return QueryResult(
        search_results=search_results,
        graph_context=graph_context,
        provenance=(),
    )


def _make_entity_lookup_result(
    entity: EntityRecord | None = None,
    neighbourhood: TraversalResult | None = None,
    related_chunks: tuple = (),
) -> EntityLookupResult:
    return EntityLookupResult(
        entity=entity,
        neighbourhood=neighbourhood,
        related_chunks=related_chunks,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_content() -> MagicMock:
    """Mocked ContentStore with sync get_chunk."""
    m = MagicMock(name="content_store")
    m.get_chunk.return_value = None
    m.get_document.return_value = None
    return m


@pytest.fixture()
def mock_graph() -> MagicMock:
    """Mocked GraphStore with sync entity and traversal operations."""
    g = MagicMock(name="graph_store")
    g.get_entity.return_value = _make_entity()
    g.find_entities.return_value = (_make_entity(),)
    g.traverse.return_value = _make_traversal()
    g.chunk_ids_for_entity.return_value = ()
    return g


@pytest.fixture()
def facade(mock_content: MagicMock, mock_graph: MagicMock) -> QueryFacade:
    """QueryFacade wired with mocked dependencies."""
    return QueryFacade(content=mock_content, graph=mock_graph)


# ---------------------------------------------------------------------------
# TestFromAC_LookupEntity
# ---------------------------------------------------------------------------


class TestFromAC_LookupEntity:
    """Tests for QueryFacade.lookup_entity() — covers AC1 and AC2."""

    # --- AC1: resolve by entity_id ---

    def test_lookup_by_id_calls_get_entity(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC1: lookup by entity_id calls graph.get_entity with that ID."""
        request = EntityLookupRequest(entity_id="ent-42")
        facade.lookup_entity(request)
        mock_graph.get_entity.assert_called_once_with("ent-42")

    def test_lookup_by_id_returns_entity_in_result(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC1: entity field in result matches resolved entity record."""
        entity = _make_entity(entity_id="ent-7")
        mock_graph.get_entity.return_value = entity
        request = EntityLookupRequest(entity_id="ent-7")
        result = facade.lookup_entity(request)
        assert result.entity == entity

    def test_lookup_by_id_not_found_raises_lookup_error(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC1: get_entity returns None → LookupError raised."""
        mock_graph.get_entity.return_value = None
        request = EntityLookupRequest(entity_id="missing-id")
        with pytest.raises(LookupError):
            facade.lookup_entity(request)

    # --- AC1: resolve by entity_name ---

    def test_lookup_by_name_calls_find_entities(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC1: lookup by entity_name calls graph.find_entities with the name."""
        request = EntityLookupRequest(entity_name="Alice")
        facade.lookup_entity(request)
        mock_graph.find_entities.assert_called_once()
        called_query = mock_graph.find_entities.call_args[0][0]
        assert isinstance(called_query, EntityQuery)
        assert called_query.name == "Alice"

    def test_lookup_by_name_uses_entity_type_filter(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC1: entity_type from request is passed to find_entities for disambiguation."""
        request = EntityLookupRequest(entity_name="Alice", entity_type=EntityType.PERSON)
        facade.lookup_entity(request)
        called_query = mock_graph.find_entities.call_args[0][0]
        assert called_query.entity_type == EntityType.PERSON

    def test_lookup_by_name_not_found_raises_lookup_error(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC1: find_entities returns empty tuple → LookupError raised."""
        mock_graph.find_entities.return_value = ()
        request = EntityLookupRequest(entity_name="Unknown")
        with pytest.raises(LookupError):
            facade.lookup_entity(request)

    def test_lookup_by_id_does_not_call_find_entities(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC1: ID path uses get_entity only, not find_entities."""
        request = EntityLookupRequest(entity_id="ent-1")
        facade.lookup_entity(request)
        mock_graph.find_entities.assert_not_called()

    # --- AC2: EntityLookupResult fields ---

    def test_result_neighbourhood_set_when_expand_hops_positive(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC2: neighbourhood is populated from traverse when expand_hops > 0."""
        traversal = _make_traversal(entities=[_make_entity("ent-2")])
        mock_graph.traverse.return_value = traversal
        request = EntityLookupRequest(entity_id="ent-1", expand_hops=2)
        result = facade.lookup_entity(request)
        assert result.neighbourhood == traversal

    def test_result_traverse_called_with_correct_hops(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC2: traverse uses expand_hops as max_hops in TraversalQuery."""
        entity = _make_entity("ent-1")
        mock_graph.get_entity.return_value = entity
        request = EntityLookupRequest(entity_id="ent-1", expand_hops=3)
        facade.lookup_entity(request)
        mock_graph.traverse.assert_called_once()
        called_query = mock_graph.traverse.call_args[0][0]
        assert isinstance(called_query, TraversalQuery)
        assert called_query.entity_id == "ent-1"
        assert called_query.max_hops == 3

    def test_result_neighbourhood_is_none_when_expand_hops_zero(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC2: neighbourhood is None when expand_hops=0."""
        request = EntityLookupRequest(entity_id="ent-1", expand_hops=0)
        result = facade.lookup_entity(request)
        assert result.neighbourhood is None
        mock_graph.traverse.assert_not_called()

    def test_result_related_chunks_populated_from_chunk_ids(
        self, facade: QueryFacade, mock_graph: MagicMock, mock_content: MagicMock
    ) -> None:
        """AC2: chunk_ids_for_entity is called and get_chunk returns ContentChunk objects."""
        entity = _make_entity("ent-1")
        chunk = _make_chunk("chunk-99")
        mock_graph.get_entity.return_value = entity
        mock_graph.chunk_ids_for_entity.return_value = ("chunk-99",)
        mock_content.get_chunk.return_value = chunk
        request = EntityLookupRequest(entity_id="ent-1")
        result = facade.lookup_entity(request)
        mock_graph.chunk_ids_for_entity.assert_called_once_with("ent-1")
        mock_content.get_chunk.assert_called_once_with("chunk-99")
        assert chunk in result.related_chunks

    def test_result_related_chunks_empty_when_no_evidence(
        self, facade: QueryFacade, mock_graph: MagicMock
    ) -> None:
        """AC2: related_chunks is empty tuple when chunk_ids_for_entity returns ()."""
        mock_graph.chunk_ids_for_entity.return_value = ()
        request = EntityLookupRequest(entity_id="ent-1")
        result = facade.lookup_entity(request)
        assert result.related_chunks == ()

    def test_result_related_chunks_skips_none_chunks(
        self, facade: QueryFacade, mock_graph: MagicMock, mock_content: MagicMock
    ) -> None:
        """AC2: get_chunk returning None for a chunk_id is gracefully skipped."""
        mock_graph.chunk_ids_for_entity.return_value = ("stale-chunk",)
        mock_content.get_chunk.return_value = None
        request = EntityLookupRequest(entity_id="ent-1")
        result = facade.lookup_entity(request)
        assert result.related_chunks == ()


# ---------------------------------------------------------------------------
# TestFromAC_RenderContext
# ---------------------------------------------------------------------------


class TestFromAC_RenderContext:
    """Tests for QueryFacade.render_context() — covers AC3 and AC4."""

    # --- AC3: renders results as structured text ---

    def test_render_context_with_query_result_returns_rendered_context(
        self, facade: QueryFacade
    ) -> None:
        """AC3: render_context with query_result returns a RenderedContext."""
        query_result = _make_query_result()
        request = ContextRenderRequest(query_result=query_result)
        result = facade.render_context(request)
        assert isinstance(result, RenderedContext)
        assert isinstance(result.text, str)

    def test_render_context_with_entity_result_returns_rendered_context(
        self, facade: QueryFacade
    ) -> None:
        """AC3: render_context with entity_result returns a RenderedContext."""
        entity_result = _make_entity_lookup_result(entity=_make_entity())
        request = ContextRenderRequest(entity_result=entity_result)
        result = facade.render_context(request)
        assert isinstance(result, RenderedContext)
        assert isinstance(result.text, str)

    def test_render_context_with_both_results_returns_rendered_context(
        self, facade: QueryFacade
    ) -> None:
        """AC3: render_context with both query_result and entity_result succeeds."""
        query_result = _make_query_result()
        entity_result = _make_entity_lookup_result(entity=_make_entity())
        request = ContextRenderRequest(
            query_result=query_result,
            entity_result=entity_result,
        )
        result = facade.render_context(request)
        assert isinstance(result, RenderedContext)

    def test_render_context_raises_value_error_when_neither_result(
        self, facade: QueryFacade
    ) -> None:
        """AC3: raises ValueError when neither query_result nor entity_result provided."""
        request = ContextRenderRequest(query_result=None, entity_result=None)
        with pytest.raises(ValueError):
            facade.render_context(request)

    def test_render_context_text_within_max_chars_budget(
        self, facade: QueryFacade
    ) -> None:
        """AC3: output text length does not exceed max_chars."""
        entity_result = _make_entity_lookup_result(entity=_make_entity())
        request = ContextRenderRequest(entity_result=entity_result, max_chars=500)
        result = facade.render_context(request)
        assert len(result.text) <= 500

    # --- AC4: metadata fields and truncation ---

    def test_render_context_truncated_false_when_content_fits(
        self, facade: QueryFacade
    ) -> None:
        """AC4: truncated=False when content fits within max_chars budget."""
        entity_result = _make_entity_lookup_result(entity=_make_entity())
        request = ContextRenderRequest(entity_result=entity_result, max_chars=10_000)
        result = facade.render_context(request)
        assert result.truncated is False

    def test_render_context_truncated_true_when_budget_exceeded(
        self, facade: QueryFacade
    ) -> None:
        """AC4: truncated=True when max_chars is smaller than natural output."""
        # Build a result with enough content to exceed a 100-char budget.
        entity = _make_entity("ent-big", name="Verylongentitynamethataddsupquickly")
        entity_result = EntityLookupResult(
            entity=entity,
            neighbourhood=_make_traversal(
                entities=[_make_entity(f"ent-{i}", name=f"Entity{i}" * 10) for i in range(20)]
            ),
            related_chunks=tuple(
                _make_chunk(f"c-{i}", text="x" * 200) for i in range(10)
            ),
        )
        request = ContextRenderRequest(entity_result=entity_result, max_chars=100)
        result = facade.render_context(request)
        assert result.truncated is True

    def test_render_context_char_count_equals_text_length(
        self, facade: QueryFacade
    ) -> None:
        """AC4: char_count matches len(result.text)."""
        entity_result = _make_entity_lookup_result(entity=_make_entity())
        request = ContextRenderRequest(entity_result=entity_result)
        result = facade.render_context(request)
        assert result.char_count == len(result.text)

    def test_render_context_include_provenance_true_includes_attribution(
        self, facade: QueryFacade
    ) -> None:
        """AC4: include_provenance=True includes source attribution in text."""
        chunk = _make_chunk(source_id="my-source-id")
        entity_result = EntityLookupResult(
            entity=_make_entity(),
            neighbourhood=None,
            related_chunks=(chunk,),
        )
        with_prov = facade.render_context(
            ContextRenderRequest(entity_result=entity_result, include_provenance=True)
        )
        without_prov = facade.render_context(
            ContextRenderRequest(entity_result=entity_result, include_provenance=False)
        )
        # Provenance adds content; text with provenance must differ from without.
        assert with_prov.text != without_prov.text

    def test_render_context_entity_count_reflects_entities_rendered(
        self, facade: QueryFacade
    ) -> None:
        """AC4: entity_count is populated from entities present in the rendered result."""
        entities = [_make_entity(f"ent-{i}") for i in range(3)]
        entity_result = EntityLookupResult(
            entity=entities[0],
            neighbourhood=_make_traversal(entities=entities[1:]),
            related_chunks=(),
        )
        request = ContextRenderRequest(entity_result=entity_result, max_chars=100_000)
        result = facade.render_context(request)
        assert result.entity_count >= 1

    def test_render_context_chunk_count_reflects_chunks_rendered(
        self, facade: QueryFacade
    ) -> None:
        """AC4: chunk_count is populated from chunks present in the rendered result."""
        chunks = tuple(_make_chunk(f"c-{i}", text=f"Chunk text {i}") for i in range(3))
        entity_result = EntityLookupResult(
            entity=_make_entity(),
            neighbourhood=None,
            related_chunks=chunks,
        )
        request = ContextRenderRequest(entity_result=entity_result, max_chars=100_000)
        result = facade.render_context(request)
        assert result.chunk_count >= 1
