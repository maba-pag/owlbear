"""Tests for query-service provenance field population (#1332).

TDD RED phase — all tests fail until KnowledgeQueryService.query() populates
retrieval_path, entities, related_sources, and source in StructuredSearchResult.

Layer: KnowledgeQueryService (owlbear_knowledge.query_service).
MCP-layer provenance serialization tested by #1331 (already green).

AC coverage:
- AC1 (td:2): source field populated from KnowledgeSource.config["url"] via source_store
- AC2 (td:2): retrieval_path determined by retriever presence + entities_found count
- AC3 (td:1): entities list from graph_store.list_entities_for_document
- AC4 (td:2): related_sources via entity edge traversal (cross-source only)
- AC5 (td:1): unenriched defaults — entities=[], related_sources=[]
- AC6 (td:1): all provenance keys always present in result shape
- AC7 (td:0): #1331 tests pass green — excluded (existing tests)
"""

from __future__ import annotations

from typing import ClassVar
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.query_service import (
    KnowledgeQueryService,
    StructuredSearchResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────────────────────


def _real_source(
    name: str = "TestSource",
    url: str = "https://source.test/",
    source_id: str = "src-1",
) -> KnowledgeSource:
    """Construct a real KnowledgeSource with config['url'] set."""
    return KnowledgeSource(
        id=source_id,
        name=name,
        source_type=SourceType.URL_LIST,
        config={"url": url},
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _mock_doc(
    doc_id: str = "doc-1",
    title: str = "Test Doc",
    content: str = "Content text here",
    scope: str = "global",
    source_id: str | None = "src-1",
) -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.title = title
    doc.content = content
    doc.scope = scope
    doc.source_id = source_id
    return doc


def _mock_entity(
    entity_id: str = "ent-1",
    name: str = "TestEntity",
    entity_type: str = "concept",
    document_id: str = "doc-1",
) -> MagicMock:
    ent = MagicMock()
    ent.id = entity_id
    ent.name = name
    ent.entity_type = entity_type
    ent.document_id = document_id
    return ent


def _mock_edge(
    edge_id: str = "edge-1",
    source_entity_id: str = "ent-1",
    target_entity_id: str = "ent-2",
    relation: str = "related_to",
) -> MagicMock:
    edge = MagicMock()
    edge.id = edge_id
    edge.source_id = source_entity_id
    edge.target_id = target_entity_id
    edge.relation = relation
    return edge


def _mock_vector_store(chunk_id: str = "chunk-1", score: float = 0.9) -> MagicMock:
    vs = MagicMock()
    vs.search_similar.return_value = [(chunk_id, score)]
    return vs


def _mock_embedding_provider() -> MagicMock:
    ep = MagicMock()
    ep.embed.return_value = [[0.1] * 10]
    return ep


def _mock_graph_store(
    doc_id: str = "doc-1",
    doc: MagicMock | None = None,
    entities: list | None = None,
    edges: list | None = None,
) -> MagicMock:
    gs = MagicMock()
    gs.get_document_id_for_chunk.return_value = doc_id
    gs.get_document.return_value = doc if doc is not None else _mock_doc(doc_id=doc_id)
    gs.list_entities_for_document.return_value = entities if entities is not None else []
    gs.list_edges.return_value = edges if edges is not None else []
    gs.get_entity.return_value = None
    return gs


def _mock_source_store(source: KnowledgeSource | None = None) -> MagicMock:
    ss = MagicMock()
    ss.get.return_value = source if source is not None else _real_source()
    return ss


def _mock_retriever(chunks: list | None = None, entities_found: int = 0) -> MagicMock:
    ret = MagicMock()
    result = MagicMock()
    result.chunks = chunks if chunks is not None else [("chunk-1", 0.9)]
    result.entities_found = entities_found
    ret.retrieve.return_value = result
    return ret


async def _query(service: KnowledgeQueryService) -> list[StructuredSearchResult]:
    return await service.query("test query", top_k=5)


# ─────────────────────────────────────────────────────────────────────────────
# AC1: source field from source_store (td:2)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_SourceFieldPopulation:
    """AC1: source field on StructuredSearchResult populated from source_store."""

    @pytest.mark.asyncio
    async def test_source_store_kwarg_accepted_by_constructor(self) -> None:
        """KnowledgeQueryService.__init__ accepts source_store keyword argument."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            embedding_provider=_mock_embedding_provider(),
            source_store=_mock_source_store(),
        )
        assert service is not None

    @pytest.mark.asyncio
    async def test_source_populated_when_source_store_provided(self) -> None:
        """result.source is not None when source_store is injected and doc has source_id."""
        ks = _real_source(name="Knowledge Base", url="https://kb.example.com/")
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(doc=_mock_doc(source_id="src-1")),
            embedding_provider=_mock_embedding_provider(),
            source_store=_mock_source_store(ks),
        )

        results = await _query(service)

        assert len(results) == 1
        assert results[0].source is not None

    @pytest.mark.asyncio
    async def test_source_name_matches_knowledge_source_name(self) -> None:
        """result.source.name equals the name on the KnowledgeSource from source_store."""
        ks = _real_source(name="Exact-KB-Name", url="https://kb.example.com/")
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(doc=_mock_doc(source_id="src-1")),
            embedding_provider=_mock_embedding_provider(),
            source_store=_mock_source_store(ks),
        )

        results = await _query(service)

        assert results[0].source.name == "Exact-KB-Name"

    @pytest.mark.asyncio
    async def test_source_url_accessible_from_config_dict(self) -> None:
        """Source URL is stored in KnowledgeSource.config['url'], per AC1 builder notes."""
        ks = _real_source(name="Docs", url="https://correct.url/path/")
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(doc=_mock_doc(source_id="src-1")),
            embedding_provider=_mock_embedding_provider(),
            source_store=_mock_source_store(ks),
        )

        results = await _query(service)

        # The stored source object exposes URL via config["url"] — not as a bare attribute
        assert results[0].source.config["url"] == "https://correct.url/path/"

    @pytest.mark.asyncio
    async def test_source_is_none_when_no_source_store(self) -> None:
        """result.source is None when source_store is not provided."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert len(results) == 1
        assert results[0].source is None


# ─────────────────────────────────────────────────────────────────────────────
# AC2: retrieval_path logic (td:2)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_RetrievalPath:
    """AC2: retrieval_path set from retriever presence and entities_found count."""

    @pytest.mark.asyncio
    async def test_retrieval_path_is_vector_without_retriever(self) -> None:
        """retrieval_path == 'vector' when no retriever is configured."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert results[0].retrieval_path == "vector"

    @pytest.mark.asyncio
    async def test_retrieval_path_is_vector_when_retriever_finds_zero_entities(
        self,
    ) -> None:
        """retrieval_path == 'vector' when retriever is used but entities_found == 0."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            embedding_provider=_mock_embedding_provider(),
            retriever=_mock_retriever(entities_found=0),
        )

        results = await _query(service)

        assert results[0].retrieval_path == "vector"

    @pytest.mark.asyncio
    async def test_retrieval_path_is_vector_plus_graph_when_entities_found(
        self,
    ) -> None:
        """retrieval_path == 'vector+graph' when retriever is used and entities_found > 0."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            embedding_provider=_mock_embedding_provider(),
            retriever=_mock_retriever(entities_found=5),
        )

        results = await _query(service)

        assert results[0].retrieval_path == "vector+graph"

    @pytest.mark.asyncio
    async def test_retrieval_path_boundary_entities_found_equals_one(self) -> None:
        """retrieval_path == 'vector+graph' at boundary entities_found=1 (minimum non-zero)."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            embedding_provider=_mock_embedding_provider(),
            retriever=_mock_retriever(entities_found=1),
        )

        results = await _query(service)

        assert results[0].retrieval_path == "vector+graph"

    @pytest.mark.asyncio
    async def test_retrieval_path_in_allowed_type_constraint(self) -> None:
        """retrieval_path value is in the allowed set: {'vector', 'vector+graph', 'graph'}."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert results[0].retrieval_path in {"vector", "vector+graph", "graph"}


# ─────────────────────────────────────────────────────────────────────────────
# AC3: entities from graph_store.list_entities_for_document (td:1)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_EntitiesPopulation:
    """AC3: entities list populated from graph_store.list_entities_for_document."""

    @pytest.mark.asyncio
    async def test_entities_populated_from_graph_store(self) -> None:
        """result.entities contains one entry per entity from list_entities_for_document."""
        ents = [
            _mock_entity("ent-1", "AuthSystem", "pattern"),
            _mock_entity("ent-2", "UserModel", "class_"),
        ]
        gs = _mock_graph_store(entities=ents)
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert len(results[0].entities) == 2
        names = {e["name"] for e in results[0].entities}
        assert "AuthSystem" in names
        assert "UserModel" in names

    @pytest.mark.asyncio
    async def test_entity_dicts_have_name_and_type_keys(self) -> None:
        """Each dict in result.entities has 'name' and 'type' keys."""
        ents = [_mock_entity("ent-1", "SomeConcept", "concept")]
        gs = _mock_graph_store(entities=ents)
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        for ent_dict in results[0].entities:
            assert "name" in ent_dict
            assert "type" in ent_dict


# ─────────────────────────────────────────────────────────────────────────────
# AC4: related_sources via entity edge traversal (td:2)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_RelatedSources:
    """AC4: related_sources populated via entity edge traversal to cross-source docs."""

    @pytest.mark.asyncio
    async def test_cross_source_edge_adds_related_source_entry(self) -> None:
        """Entity edge to a doc in a different source → related_sources non-empty."""
        primary_doc = _mock_doc("doc-1", source_id="src-1")
        target_doc = _mock_doc("doc-2", source_id="src-2")
        ent = _mock_entity("ent-1", "PrimaryEntity", "concept", "doc-1")
        tgt_ent = _mock_entity("ent-2", "TargetEntity", "pattern", "doc-2")
        edge = _mock_edge("edge-1", "ent-1", "ent-2", "related_to")

        gs = MagicMock()
        gs.get_document_id_for_chunk.return_value = "doc-1"
        doc_map_a = {"doc-1": primary_doc, "doc-2": target_doc}
        gs.get_document.side_effect = doc_map_a.get
        gs.list_entities_for_document.return_value = [ent]
        gs.list_edges.return_value = [edge]
        gs.get_entity.return_value = tgt_ent

        ks1 = _real_source("SourceA", "https://a.com/", "src-1")
        ks2 = _real_source("SourceB", "https://b.com/", "src-2")
        ss = MagicMock()
        src_map_a = {"src-1": ks1, "src-2": ks2}
        ss.get.side_effect = src_map_a.get

        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
            source_store=ss,
        )

        results = await _query(service)

        assert len(results[0].related_sources) >= 1

    @pytest.mark.asyncio
    async def test_same_source_edge_excluded_from_related_sources(self) -> None:
        """Entity edge to a doc in the same source is NOT included in related_sources."""
        primary_doc = _mock_doc("doc-1", source_id="src-1")
        same_doc = _mock_doc("doc-3", source_id="src-1")  # same source as primary
        ent = _mock_entity("ent-1", "PrimaryEntity", "concept", "doc-1")
        same_ent = _mock_entity("ent-3", "SameSrcEntity", "concept", "doc-3")
        edge = _mock_edge("edge-1", "ent-1", "ent-3", "related_to")

        gs = MagicMock()
        gs.get_document_id_for_chunk.return_value = "doc-1"
        doc_map_b = {"doc-1": primary_doc, "doc-3": same_doc}
        gs.get_document.side_effect = doc_map_b.get
        gs.list_entities_for_document.return_value = [ent]
        gs.list_edges.return_value = [edge]
        gs.get_entity.return_value = same_ent

        ks1 = _real_source("SourceA", "https://a.com/", "src-1")
        ss = MagicMock()
        ss.get.return_value = ks1

        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
            source_store=ss,
        )

        results = await _query(service)

        assert results[0].related_sources == []

    @pytest.mark.asyncio
    async def test_no_edges_yields_empty_related_sources(self) -> None:
        """No entity edges → related_sources is []."""
        ents = [_mock_entity("ent-1", "Isolated", "concept")]
        gs = _mock_graph_store(entities=ents)  # list_edges returns [] by default
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert results[0].related_sources == []

    @pytest.mark.asyncio
    async def test_related_source_item_has_required_keys(self) -> None:
        """Each item in related_sources has 'name', 'relationship', and 'entity' keys."""
        primary_doc = _mock_doc("doc-1", source_id="src-1")
        target_doc = _mock_doc("doc-2", source_id="src-2")
        ent = _mock_entity("ent-1", "OriginEntity", "concept", "doc-1")
        tgt_ent = _mock_entity("ent-2", "TargetEntity", "pattern", "doc-2")
        edge = _mock_edge("edge-1", "ent-1", "ent-2", "references")

        gs = MagicMock()
        gs.get_document_id_for_chunk.return_value = "doc-1"
        doc_map_c = {"doc-1": primary_doc, "doc-2": target_doc}
        gs.get_document.side_effect = doc_map_c.get
        gs.list_entities_for_document.return_value = [ent]
        gs.list_edges.return_value = [edge]
        gs.get_entity.return_value = tgt_ent

        ks1 = _real_source("SourceA", "https://a.com/", "src-1")
        ks2 = _real_source("SourceB", "https://b.com/", "src-2")
        ss = MagicMock()
        src_map_b = {"src-1": ks1, "src-2": ks2}
        ss.get.side_effect = src_map_b.get

        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
            source_store=ss,
        )

        results = await _query(service)

        assert len(results[0].related_sources) >= 1
        for rel in results[0].related_sources:
            assert "name" in rel
            assert "relationship" in rel
            assert "entity" in rel


# ─────────────────────────────────────────────────────────────────────────────
# AC5: unenriched defaults (td:1)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_UnenrichedDefaults:
    """AC5: entities=[], related_sources=[] when enrichment not run."""

    @pytest.mark.asyncio
    async def test_entities_empty_when_no_graph_entities(self) -> None:
        """result.entities == [] when graph_store.list_entities_for_document returns []."""
        gs = _mock_graph_store(entities=[])
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert results[0].entities == []

    @pytest.mark.asyncio
    async def test_related_sources_empty_when_no_entities(self) -> None:
        """result.related_sources == [] when graph_store.list_entities_for_document returns []."""
        gs = _mock_graph_store(entities=[])
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert results[0].related_sources == []


# ─────────────────────────────────────────────────────────────────────────────
# AC6: shape determinism (td:1)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_ShapeDeterminism:
    """AC6: all provenance attributes present on StructuredSearchResult regardless of enrichment."""

    _PROVENANCE_ATTRS: ClassVar[list[str]] = [
        "score",
        "retrieval_path",
        "entities",
        "related_sources",
        "source",
    ]

    @pytest.mark.asyncio
    async def test_all_provenance_attrs_present_unenriched(self) -> None:
        """All provenance attributes exist on result when no enrichment (empty entities)."""
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(entities=[]),
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        for attr in self._PROVENANCE_ATTRS:
            assert hasattr(results[0], attr), f"missing '{attr}' on StructuredSearchResult"

    @pytest.mark.asyncio
    async def test_all_provenance_attrs_present_enriched(self) -> None:
        """All provenance attributes exist on result when entities are present."""
        ents = [_mock_entity()]
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(entities=ents),
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        for attr in self._PROVENANCE_ATTRS:
            assert hasattr(results[0], attr), f"missing '{attr}' on StructuredSearchResult"


# ─────────────────────────────────────────────────────────────────────────────
# AC9: related_sources exact payload values (td:1)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_RelatedSourcesExactValues:
    """AC9: related_sources items pin exact name, relationship, and entity values."""

    def _build_cross_source_service(self) -> KnowledgeQueryService:
        """Build a service with one cross-source entity edge (SourceA→SourceB, 'references')."""
        primary_doc = _mock_doc("doc-1", source_id="src-1")
        target_doc = _mock_doc("doc-2", source_id="src-2")
        ent = _mock_entity("ent-1", "OriginEntity", "concept", "doc-1")
        tgt_ent = _mock_entity("ent-2", "TargetEntity", "pattern", "doc-2")
        edge = _mock_edge("edge-1", "ent-1", "ent-2", "references")

        gs = MagicMock()
        gs.get_document_id_for_chunk.return_value = "doc-1"
        doc_map: dict[str, MagicMock] = {"doc-1": primary_doc, "doc-2": target_doc}
        gs.get_document.side_effect = doc_map.get
        gs.list_entities_for_document.return_value = [ent]
        gs.list_edges.return_value = [edge]
        gs.get_entity.return_value = tgt_ent

        ks1 = _real_source("SourceA", "https://a.com/", "src-1")
        ks2 = _real_source("SourceB", "https://b.com/", "src-2")
        ss = MagicMock()
        src_map: dict[str, KnowledgeSource] = {"src-1": ks1, "src-2": ks2}
        ss.get.side_effect = src_map.get

        return KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
            source_store=ss,
        )

    @pytest.mark.asyncio
    async def test_related_source_name_is_exact_peer_source_name(self) -> None:
        """related_sources[0]['name'] matches the exact KnowledgeSource.name of the peer."""
        service = self._build_cross_source_service()

        results = await _query(service)

        assert results[0].related_sources[0]["name"] == "SourceB"

    @pytest.mark.asyncio
    async def test_related_source_relationship_is_exact_edge_relation(self) -> None:
        """related_sources[0]['relationship'] matches the exact edge.relation value."""
        service = self._build_cross_source_service()

        results = await _query(service)

        assert results[0].related_sources[0]["relationship"] == "references"

    @pytest.mark.asyncio
    async def test_related_source_entity_is_exact_peer_entity_name(self) -> None:
        """related_sources[0]['entity'] matches the exact peer entity name."""
        service = self._build_cross_source_service()

        results = await _query(service)

        assert results[0].related_sources[0]["entity"] == "TargetEntity"


# ─────────────────────────────────────────────────────────────────────────────
# AC10: entity type exact-value assertion (td:1)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_EntityTypeExactValue:
    """AC10: entities[i]['type'] must match the exact entity_type string from graph_store."""

    @pytest.mark.asyncio
    async def test_entity_type_value_matches_fixture_entity_type(self) -> None:
        """entities[0]['type'] equals the exact entity_type on the mock entity (not empty or wrong)."""
        ents = [_mock_entity("ent-1", "SomeConcept", "concept")]
        gs = _mock_graph_store(entities=ents)
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert results[0].entities[0]["type"] == "concept"

    @pytest.mark.asyncio
    async def test_entity_type_not_empty_string(self) -> None:
        """entities[0]['type'] is non-empty when entity_type is set on the fixture."""
        ents = [_mock_entity("ent-1", "RegexParser", "function")]
        gs = _mock_graph_store(entities=ents)
        service = KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
        )

        results = await _query(service)

        assert results[0].entities[0]["type"] == "function"
        assert results[0].entities[0]["type"] != ""


# ─────────────────────────────────────────────────────────────────────────────
# AC11: incoming-edge traversal (focal entity as edge target) (td:1)
# ─────────────────────────────────────────────────────────────────────────────


class TestFromAC_RelatedSourcesIncomingEdge:
    """AC11: related_sources resolves correctly when focal entity is the edge TARGET."""

    def _build_incoming_edge_service(self) -> KnowledgeQueryService:
        """Fixture: peer entity (ent-b, src-2) has an outgoing edge to focal entity (ent-a, src-1).

        Edge direction: ent-b → ent-a (focal entity is the target, not the source).
        Only list_edges(target_id="ent-a") returns the edge; list_edges(source_id="ent-a") is empty.
        """
        focal_doc = _mock_doc("doc-1", source_id="src-1")
        peer_doc = _mock_doc("doc-2", source_id="src-2")
        focal_entity = _mock_entity("ent-a", "FocalEntity", "class_", "doc-1")
        peer_entity = _mock_entity("ent-b", "PeerEntity", "function", "doc-2")
        # Edge runs FROM peer (ent-b) TO focal (ent-a) — incoming from focal's perspective
        edge = _mock_edge("edge-inc", "ent-b", "ent-a", "calls")

        def _list_edges(_source_id: str | None = None, target_id: str | None = None, **_: object) -> list:  # type: ignore[return]
            """Route list_edges calls: only the target_id='ent-a' call returns results."""
            if target_id == "ent-a":
                return [edge]
            return []

        gs = MagicMock()
        gs.get_document_id_for_chunk.return_value = "doc-1"
        doc_lookup: dict[str, MagicMock] = {"doc-1": focal_doc, "doc-2": peer_doc}
        gs.get_document.side_effect = doc_lookup.get
        gs.list_entities_for_document.return_value = [focal_entity]
        gs.list_edges.side_effect = _list_edges
        gs.get_entity.return_value = peer_entity

        ks1 = _real_source("SourceS1", "https://s1.example/", "src-1")
        ks2 = _real_source("SourceS2", "https://s2.example/", "src-2")
        ss = MagicMock()
        src_lookup: dict[str, KnowledgeSource] = {"src-1": ks1, "src-2": ks2}
        ss.get.side_effect = src_lookup.get

        return KnowledgeQueryService(
            vector_store=_mock_vector_store(),
            graph_store=gs,
            embedding_provider=_mock_embedding_provider(),
            source_store=ss,
        )

    @pytest.mark.asyncio
    async def test_incoming_edge_yields_related_source_entry(self) -> None:
        """related_sources is non-empty when the focal entity is the edge target."""
        service = self._build_incoming_edge_service()

        results = await _query(service)

        assert len(results[0].related_sources) >= 1

    @pytest.mark.asyncio
    async def test_incoming_edge_related_source_name_is_peer_source(self) -> None:
        """related_sources[0]['name'] is the peer source name (not the focal source name)."""
        service = self._build_incoming_edge_service()

        results = await _query(service)

        assert results[0].related_sources[0]["name"] == "SourceS2"

    @pytest.mark.asyncio
    async def test_incoming_edge_relationship_is_exact_edge_relation(self) -> None:
        """related_sources[0]['relationship'] matches the edge.relation of the incoming edge."""
        service = self._build_incoming_edge_service()

        results = await _query(service)

        assert results[0].related_sources[0]["relationship"] == "calls"

    @pytest.mark.asyncio
    async def test_incoming_edge_entity_is_peer_entity_name(self) -> None:
        """related_sources[0]['entity'] is the peer entity name (the edge source)."""
        service = self._build_incoming_edge_service()

        results = await _query(service)

        assert results[0].related_sources[0]["entity"] == "PeerEntity"
