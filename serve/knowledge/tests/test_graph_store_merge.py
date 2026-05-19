"""GraphStore entity merge regressions."""

from __future__ import annotations

import sqlite3

from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Document, Edge, Entity, EntityType, RelationType
from owlbear_knowledge.schema import init_db


def test_merge_entities_deduplicates_colliding_edge_facts() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    graph = GraphStore(conn)
    graph.insert_document(Document(id="doc-1", title="Doc", content="content"))
    graph.insert_entity(Entity(id="canonical", name="Canonical", entity_type=EntityType.CONCEPT, document_id="doc-1"))
    graph.insert_entity(Entity(id="duplicate", name="Duplicate", entity_type=EntityType.CONCEPT, document_id="doc-1"))
    graph.insert_entity(Entity(id="neighbor", name="Neighbor", entity_type=EntityType.CONCEPT, document_id="doc-1"))
    graph.insert_edge(
        Edge(id="edge-c", source_id="canonical", target_id="neighbor", relation=RelationType.RELATED_TO),
        document_id="doc-1",
    )
    graph.insert_edge(
        Edge(id="edge-d", source_id="duplicate", target_id="neighbor", relation=RelationType.RELATED_TO),
        document_id="doc-1",
    )

    merged = graph.merge_entities("canonical", ["duplicate"], {"merged": True})

    assert merged == 1
    assert conn.execute("SELECT id FROM entities WHERE id = 'duplicate'").fetchone() is None
    assert conn.execute("SELECT source_id, target_id, relation, document_id FROM edges").fetchall() == [
        ("canonical", "neighbor", "related_to", "doc-1")
    ]


def test_merge_entities_redirects_non_colliding_edges() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    graph = GraphStore(conn)
    graph.insert_document(Document(id="doc-1", title="Doc", content="content"))
    graph.insert_entity(Entity(id="canonical", name="Canonical", entity_type=EntityType.CONCEPT, document_id="doc-1"))
    graph.insert_entity(Entity(id="duplicate", name="Duplicate", entity_type=EntityType.CONCEPT, document_id="doc-1"))
    graph.insert_entity(Entity(id="neighbor", name="Neighbor", entity_type=EntityType.CONCEPT, document_id="doc-1"))
    graph.insert_edge(
        Edge(id="edge-d", source_id="duplicate", target_id="neighbor", relation=RelationType.RELATED_TO),
        document_id="doc-1",
    )

    graph.merge_entities("canonical", ["duplicate"], {"merged": True})

    assert conn.execute("SELECT source_id, target_id, relation, document_id FROM edges").fetchall() == [
        ("canonical", "neighbor", "related_to", "doc-1")
    ]
