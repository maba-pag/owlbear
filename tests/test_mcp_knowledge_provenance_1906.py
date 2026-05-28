"""MCP provenance serialization contract — task #1906 retry.

Restores durable proof for _serialize_query_facade_results output fields:
  retrieval_path, graph_context, entities, related_sources, source

Reviewer required follow-up: "Restore durable proof for MCP provenance
serialization on the v2 QueryFacade path by adding tests that call
knowledge_search (or otherwise exercise _serialize_query_facade_results
through the production adapter path) and assert retrieval_path,
graph_context, entities, related_sources, and source."

Target:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
  _serialize_query_facade_results(app_ctx, result) -> list[SearchResult]
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.protocols.common import EntityType, RelationType
from owlbear_knowledge.protocols.content import ContentChunk, ContentSearchResult
from owlbear_knowledge.protocols.graph import EdgeRecord, EntityRecord, TraversalResult
from owlbear_knowledge.protocols.query import Provenance, QueryResult
from owlbear_mcp_knowledge.server import AppContext, _serialize_query_facade_results

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(
    chunk_id: str = "c1",
    source_id: str = "src-1",
    text: str = "Some chunk text",
) -> ContentChunk:
    return ContentChunk(
        id=chunk_id,
        document_id="doc-1",
        source_id=source_id,
        index=0,
        text=text,
        content_hash="abc123",
        scope="global",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _hit(chunk: ContentChunk, score: float = 0.9) -> ContentSearchResult:
    return ContentSearchResult(chunk=chunk, score=score)


def _prov(
    chunk_id: str,
    *,
    source_id: str = "src-1",
    title: str = "Test Document",
    uri: str | None = None,
) -> Provenance:
    return Provenance(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id=source_id,
        title=title,
        uri=uri,
        exact_text="Some chunk text",
        score=0.9,
    )


def _entity(eid: str, name: str, etype: EntityType = EntityType.CONCEPT) -> EntityRecord:
    return EntityRecord(
        id=eid,
        name=name,
        canonical_name=name.lower(),
        entity_type=etype,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _edge(eid: str, src: str, tgt: str) -> EdgeRecord:
    return EdgeRecord(
        id=eid,
        source_entity_id=src,
        target_entity_id=tgt,
        relation_type=RelationType.RELATED_TO,
        weight=1.0,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _ctx(source_store_v2: object = None) -> AppContext:
    return AppContext(conn=MagicMock(), source_store_v2=source_store_v2)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestFromAC_ProvenanceRetrieval
# Happy path: retrieval_path, graph_context, entities fields
# ---------------------------------------------------------------------------


class TestFromAC_ProvenanceRetrieval:
    """retrieval_path, graph_context, entities — populated from QueryResult."""

    def test_retrieval_path_is_vector_when_no_graph_context(self) -> None:
        chunk = _chunk()
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["retrieval_path"] == "vector"

    def test_retrieval_path_is_vector_plus_graph_when_traversal_present(self) -> None:
        chunk = _chunk()
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=TraversalResult(entities=(), edges=()),
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["retrieval_path"] == "vector+graph"

    def test_graph_context_is_empty_string_when_no_traversal(self) -> None:
        chunk = _chunk()
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["graph_context"] == ""

    def test_graph_context_shows_entity_and_edge_counts(self) -> None:
        chunk = _chunk()
        e1 = _entity("e1", "Alpha")
        e2 = _entity("e2", "Beta")
        edge = _edge("ed1", "e1", "e2")
        traversal = TraversalResult(entities=(e1, e2), edges=(edge,))
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=traversal,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["graph_context"] == "graph expansion: 2 entities, 1 edges"

    def test_entities_is_empty_list_when_no_graph_context(self) -> None:
        chunk = _chunk()
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["entities"] == []

    def test_entities_populated_from_traversal_entities(self) -> None:
        chunk = _chunk()
        e1 = _entity("e1", "Alpha", EntityType.CONCEPT)
        e2 = _entity("e2", "Beta", EntityType.PERSON)
        traversal = TraversalResult(entities=(e1, e2), edges=())
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=traversal,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        entities = items[0]["entities"]
        assert len(entities) == 2
        assert entities[0]["name"] == "Alpha"
        assert entities[0]["type"] == "concept"
        assert entities[1]["name"] == "Beta"
        assert entities[1]["type"] == "person"

    def test_empty_search_results_returns_empty_list(self) -> None:
        result = QueryResult(search_results=(), graph_context=None, provenance=())
        items = _serialize_query_facade_results(_ctx(), result)
        assert items == []

    def test_snippet_set_from_chunk_text(self) -> None:
        chunk = _chunk(text="The quick brown fox jumps over the lazy dog")
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["snippet"] == "The quick brown fox jumps over the lazy dog"

    def test_title_set_from_provenance(self) -> None:
        chunk = _chunk()
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(_prov(chunk.id, title="My Reference Document"),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["title"] == "My Reference Document"

    def test_score_preserved_from_search_result(self) -> None:
        chunk = _chunk()
        result = QueryResult(
            search_results=(ContentSearchResult(chunk=chunk, score=0.753),),
            graph_context=None,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["score"] == pytest.approx(0.753)


# ---------------------------------------------------------------------------
# TestFromAC_ProvenanceSource
# source field — from provenance or source_store_v2
# ---------------------------------------------------------------------------


class TestFromAC_ProvenanceSource:
    """source {name, url} — sourced from provenance or source_store_v2."""

    def test_source_name_from_provenance_source_id_when_no_store(self) -> None:
        chunk = _chunk()
        prov = _prov(chunk.id, source_id="my-kb-source")
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(prov,),
        )
        items = _serialize_query_facade_results(_ctx(source_store_v2=None), result)
        assert items[0]["source"]["name"] == "my-kb-source"

    def test_source_url_from_provenance_uri_when_no_store(self) -> None:
        chunk = _chunk()
        prov = _prov(chunk.id, uri="https://example.com/doc")
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(prov,),
        )
        items = _serialize_query_facade_results(_ctx(source_store_v2=None), result)
        assert items[0]["source"]["url"] == "https://example.com/doc"

    def test_source_url_empty_when_provenance_uri_is_none_and_no_store(self) -> None:
        chunk = _chunk()
        prov = _prov(chunk.id, uri=None)
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(prov,),
        )
        items = _serialize_query_facade_results(_ctx(source_store_v2=None), result)
        assert items[0]["source"]["url"] == ""

    def test_source_from_source_store_v2_when_record_found(self) -> None:
        # Use a non-SimpleNamespace object so the code preserves its .url
        # (the serializer only overwrites .url when source_obj is a SimpleNamespace,
        # which is the fallback sentinel — real store records are typed objects).
        class _FakeSourceRecord:
            name = "My KB Source"
            url = "https://kb.example.com/"

        chunk = _chunk()
        prov = _prov(chunk.id, source_id="src-lookup")
        mock_store = MagicMock()
        mock_store.get_source.return_value = _FakeSourceRecord()
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(prov,),
        )
        items = _serialize_query_facade_results(_ctx(source_store_v2=mock_store), result)
        assert items[0]["source"]["name"] == "My KB Source"
        assert items[0]["source"]["url"] == "https://kb.example.com/"
        mock_store.get_source.assert_called_once_with("src-lookup")

    def test_source_falls_back_to_provenance_when_store_returns_none(self) -> None:
        chunk = _chunk()
        prov = _prov(chunk.id, source_id="fallback-src", uri="https://fallback.example.com/")
        mock_store = MagicMock()
        mock_store.get_source.return_value = None
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(prov,),
        )
        items = _serialize_query_facade_results(_ctx(source_store_v2=mock_store), result)
        assert items[0]["source"]["name"] == "fallback-src"
        assert items[0]["source"]["url"] == "https://fallback.example.com/"

    def test_source_config_url_used_when_direct_url_blank(self) -> None:
        """_serialize_source: config['url'] dict branch covers pre-existing gap."""
        chunk = _chunk()
        prov = _prov(chunk.id)
        config_source = SimpleNamespace(
            name="Config Source",
            url="",
            config={"url": "https://config.example.com/"},
        )
        mock_store = MagicMock()
        mock_store.get_source.return_value = config_source
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(prov,),
        )
        items = _serialize_query_facade_results(_ctx(source_store_v2=mock_store), result)
        assert items[0]["source"]["url"] == "https://config.example.com/"

    def test_source_config_urls_list_first_entry_used_when_url_blank(self) -> None:
        """_serialize_source: config['urls'] list branch covers pre-existing gap."""
        chunk = _chunk()
        prov = _prov(chunk.id)
        config_source = SimpleNamespace(
            name="List Source",
            url="",
            config={"urls": ["https://list-first.example.com/", "https://list-second.example.com/"]},
        )
        mock_store = MagicMock()
        mock_store.get_source.return_value = config_source
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(prov,),
        )
        items = _serialize_query_facade_results(_ctx(source_store_v2=mock_store), result)
        assert items[0]["source"]["url"] == "https://list-first.example.com/"

    def test_source_name_and_url_empty_when_no_provenance_for_chunk(self) -> None:
        """No matching provenance for a chunk — source defaults to empty strings."""
        chunk = _chunk("orphan-chunk")
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(),  # no provenance record for this chunk
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["source"]["name"] == ""
        assert items[0]["source"]["url"] == ""


# ---------------------------------------------------------------------------
# TestFromAC_ProvenanceRelatedSources
# related_sources field — populated from other provenance items
# ---------------------------------------------------------------------------


class TestFromAC_ProvenanceRelatedSources:
    """related_sources {name, relationship, entity} — cross-chunk provenance."""

    def test_related_sources_empty_when_single_result(self) -> None:
        chunk = _chunk("c1")
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=None,
            provenance=(_prov("c1", title="Only Doc"),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["related_sources"] == []

    def test_related_sources_populated_for_second_result(self) -> None:
        c1, c2 = _chunk("c1"), _chunk("c2")
        result = QueryResult(
            search_results=(_hit(c1), _hit(c2)),
            graph_context=None,
            provenance=(_prov("c1", title="Doc A"), _prov("c2", title="Doc B")),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        related_c1 = items[0]["related_sources"]
        assert len(related_c1) == 1
        assert related_c1[0]["name"] == "Doc B"
        assert related_c1[0]["relationship"] == "related"

    def test_related_sources_relationship_field_is_related(self) -> None:
        c1, c2 = _chunk("c1"), _chunk("c2")
        result = QueryResult(
            search_results=(_hit(c1), _hit(c2)),
            graph_context=None,
            provenance=(_prov("c1", title="Doc A"), _prov("c2", title="Doc B")),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[1]["related_sources"][0]["relationship"] == "related"

    def test_related_sources_uses_source_id_when_title_empty(self) -> None:
        c1, c2 = _chunk("c1"), _chunk("c2", source_id="src-for-c2")
        result = QueryResult(
            search_results=(_hit(c1), _hit(c2)),
            graph_context=None,
            provenance=(
                _prov("c1", title="Doc A"),
                _prov("c2", title="", source_id="src-for-c2"),
            ),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        related_c1 = items[0]["related_sources"]
        assert len(related_c1) == 1
        assert related_c1[0]["name"] == "src-for-c2"


# ---------------------------------------------------------------------------
# TestFromAC_ProvenanceBoundary
# Boundary: graph context with zero entities/edges; edge cases
# ---------------------------------------------------------------------------


class TestFromAC_ProvenanceBoundary:
    """Boundary cases: zero-entity traversal, missing provenance."""

    def test_graph_context_with_zero_entities_and_zero_edges(self) -> None:
        chunk = _chunk()
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=TraversalResult(entities=(), edges=()),
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["retrieval_path"] == "vector+graph"
        assert items[0]["graph_context"] == "graph expansion: 0 entities, 0 edges"
        assert items[0]["entities"] == []

    def test_multiple_results_each_has_correct_snippet(self) -> None:
        c1 = _chunk("c1", text="First result text")
        c2 = _chunk("c2", text="Second result text")
        result = QueryResult(
            search_results=(_hit(c1), _hit(c2)),
            graph_context=None,
            provenance=(_prov("c1"), _prov("c2")),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["snippet"] == "First result text"
        assert items[1]["snippet"] == "Second result text"

    def test_result_count_matches_search_results_length(self) -> None:
        chunks = [_chunk(f"c{i}") for i in range(3)]
        result = QueryResult(
            search_results=tuple(_hit(c) for c in chunks),
            graph_context=None,
            provenance=tuple(_prov(c.id) for c in chunks),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert len(items) == 3

    def test_entity_type_serialized_as_lowercase_string(self) -> None:
        chunk = _chunk()
        e1 = _entity("e1", "MyTech", EntityType.TECHNOLOGY)
        traversal = TraversalResult(entities=(e1,), edges=())
        result = QueryResult(
            search_results=(_hit(chunk),),
            graph_context=traversal,
            provenance=(_prov(chunk.id),),
        )
        items = _serialize_query_facade_results(_ctx(), result)
        assert items[0]["entities"][0]["type"] == "technology"
