"""GraphStore metadata hydration regressions."""

from __future__ import annotations

import sqlite3

from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.schema import init_db


def test_get_document_falls_back_for_malformed_metadata() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        ("doc-bad", "Bad", "content", "not-json", "2026-01-01T00:00:00Z", "global"),
    )

    document = GraphStore(conn).get_document("doc-bad")

    assert document is not None
    assert document.metadata == {}


def test_list_entities_falls_back_for_malformed_metadata() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        ("doc-1", "Doc", "content", "{}", "2026-01-01T00:00:00Z", "global"),
    )
    conn.execute(
        """
        INSERT INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, importance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("entity-bad", "Bad", "concept", "", "not-json", "2026-01-01T00:00:00Z", "global", "doc-1", 0.5),
    )

    entities = GraphStore(conn).list_entities()

    assert len(entities) == 1
    assert entities[0].metadata == {}


def test_list_entities_pipeline_filter_skips_malformed_metadata() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        ("doc-1", "Doc", "content", "{}", "2026-01-01T00:00:00Z", "global"),
    )
    conn.execute(
        """
        INSERT INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, importance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("entity-bad", "Bad", "concept", "", "not-json", "2026-01-01T00:00:00Z", "global", "doc-1", 0.5),
    )

    assert GraphStore(conn).list_entities(pipeline_name="ingest") == []


def test_list_edges_falls_back_for_non_object_metadata() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    graph = GraphStore(conn)
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        ("doc-1", "Doc", "content", "{}", "2026-01-01T00:00:00Z", "global"),
    )
    conn.execute(
        """
        INSERT INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, importance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("entity-a", "A", "concept", "", "{}", "2026-01-01T00:00:00Z", "global", "doc-1", 0.5),
    )
    conn.execute(
        """
        INSERT INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, importance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("entity-b", "B", "concept", "", "{}", "2026-01-01T00:00:00Z", "global", "doc-1", 0.5),
    )
    conn.execute(
        """
        INSERT INTO edges
        (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "edge-list-meta",
            "entity-a",
            "entity-b",
            "related_to",
            "doc-1",
            1.0,
            "[]",
            "2026-01-01T00:00:00Z",
            "global",
        ),
    )

    edges = graph.list_edges()

    assert len(edges) == 1
    assert edges[0].metadata == {}


def test_list_edges_pipeline_filter_skips_malformed_metadata() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        ("doc-1", "Doc", "content", "{}", "2026-01-01T00:00:00Z", "global"),
    )
    conn.execute(
        """
        INSERT INTO entities
        (id, name, entity_type, description, metadata, created_at, scope, document_id, importance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("entity-a", "A", "concept", "", "{}", "2026-01-01T00:00:00Z", "global", "doc-1", 0.5),
    )
    conn.execute(
        """
        INSERT INTO edges
        (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "edge-bad",
            "entity-a",
            "entity-a",
            "related_to",
            "doc-1",
            1.0,
            "not-json",
            "2026-01-01T00:00:00Z",
            "global",
        ),
    )

    assert GraphStore(conn).list_edges(pipeline_name="ingest") == []
