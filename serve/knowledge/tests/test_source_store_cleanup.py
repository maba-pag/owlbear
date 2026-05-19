"""Source lifecycle cleanup regressions."""

from __future__ import annotations

import sqlite3

from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore


def _insert_source(conn: sqlite3.Connection, source_id: str) -> None:
    now = "2026-01-01T00:00:00Z"
    conn.execute(
        """
        INSERT INTO knowledge_sources
        (id, name, source_type, fetch_method, enrich, enabled, config, scope, created_at, updated_at)
        VALUES (?, ?, 'url_list', 'http', 1, 1, '{}', 'global', ?, ?)
        """,
        (source_id, source_id, now, now),
    )


def test_delete_cascade_removes_document_provenance_edges_and_reviewed_pairs() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    now = "2026-01-01T00:00:00Z"
    _insert_source(conn, "src-a")
    _insert_source(conn, "src-b")
    conn.execute(
        """
        INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)
        VALUES ('doc-a', 'Doc A', 'content', '{}', ?, 'global', 'src-a')
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO documents (id, title, content, metadata, created_at, scope, source_id)
        VALUES ('doc-b', 'Doc B', 'content', '{}', ?, 'global', 'src-b')
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO entities (id, name, entity_type, metadata, created_at, scope, document_id)
        VALUES ('ent-b1', 'B1', 'concept', '{}', ?, 'global', 'doc-b')
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO entities (id, name, entity_type, metadata, created_at, scope, document_id)
        VALUES ('ent-b2', 'B2', 'concept', '{}', ?, 'global', 'doc-b')
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO edges (id, source_id, target_id, relation, document_id, weight, metadata, created_at, scope)
        VALUES ('edge-doc-a', 'ent-b1', 'ent-b2', 'related_to', 'doc-a', 1.0, '{}', ?, 'global')
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO reviewed_pairs (entity_name, source_a, source_b, entity_id_a, entity_id_b)
        VALUES ('Shared', 'src-a', 'src-b', 'ent-a', 'ent-b1')
        """,
    )
    conn.commit()

    assert KnowledgeSourceStore(conn).delete_cascade("src-a") is True

    assert conn.execute("SELECT id FROM edges").fetchall() == []
    assert conn.execute("SELECT entity_name FROM reviewed_pairs").fetchall() == []
    assert conn.execute("SELECT id FROM documents").fetchall() == [("doc-b",)]
