"""GraphStore pipeline-name filter regressions."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.schema import init_db


def test_pipeline_name_filters_match_stored_extraction_metadata() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    graph = GraphStore(conn)
    docs = DocumentStore(conn, graph, MagicMock(), MagicMock())
    extraction = ExtractionResult(
        entities=[Entity(id="entity-a", name="A", entity_type=EntityType.CONCEPT)],
        edges=[Edge(id="edge-a", source_id="entity-a", target_id="entity-a", relation=RelationType.RELATED_TO)],
    )

    docs.store_extractions(
        [extraction],
        document_id="doc-1",
        chunk_ids=["chunk-1"],
        pipeline_name="ingest",
    )

    assert [entity.id for entity in graph.list_entities(pipeline_name="ingest")] == ["entity-a"]
    assert [edge.id for edge in graph.list_edges(pipeline_name="ingest")] == ["edge-a"]
    assert graph.list_entities(pipeline_name="other") == []
    assert graph.list_edges(pipeline_name="other") == []


def test_store_extractions_ignores_duplicate_edge_facts() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    graph = GraphStore(conn)
    docs = DocumentStore(conn, graph, MagicMock(), MagicMock())
    extraction = ExtractionResult(
        entities=[
            Entity(id="entity-a", name="A", entity_type=EntityType.CONCEPT),
            Entity(id="entity-b", name="B", entity_type=EntityType.CONCEPT),
        ],
        edges=[
            Edge(id="edge-a", source_id="entity-a", target_id="entity-b", relation=RelationType.RELATED_TO),
            Edge(id="edge-b", source_id="entity-a", target_id="entity-b", relation=RelationType.RELATED_TO),
        ],
    )

    entity_count, edge_count = docs.store_extractions(
        [extraction],
        document_id="doc-1",
        chunk_ids=["chunk-1"],
        pipeline_name="ingest",
    )

    assert entity_count == 2
    assert edge_count == 1
    assert conn.execute("SELECT COUNT(*) FROM edges").fetchone() == (1,)
