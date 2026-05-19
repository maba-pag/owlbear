"""Durable knowledge integrity regression tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from owlbear_knowledge.chunker import Chunk
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.integrity import audit_integrity
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.schema import audit_integrity as audit_integrity_via_schema
from owlbear_knowledge.schema import init_db


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _fresh_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _insert_document(conn: sqlite3.Connection, doc_id: str) -> None:
    conn.execute(
        "INSERT INTO documents (id, title, content, created_at) VALUES (?, ?, ?, ?)",
        (doc_id, "T", "C", _now()),
    )
    conn.commit()


def _insert_document_with_source(conn: sqlite3.Connection, doc_id: str, source_id: str) -> None:
    conn.execute(
        "INSERT INTO documents (id, title, content, created_at, source_id) VALUES (?, ?, ?, ?, ?)",
        (doc_id, "T", "C", _now(), source_id),
    )
    conn.commit()


def _insert_chunk(conn: sqlite3.Connection, chunk_id: str, document_id: str) -> None:
    conn.execute(
        "INSERT INTO chunks (id, document_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (chunk_id, document_id, 0, "content", _now()),
    )
    conn.commit()


def _insert_chunk_without_document(conn: sqlite3.Connection, chunk_id: str) -> None:
    conn.execute(
        "INSERT INTO chunks (id, document_id, chunk_index, content, created_at) VALUES (?, NULL, ?, ?, ?)",
        (chunk_id, 0, "content", _now()),
    )
    conn.commit()


def _insert_entity(conn: sqlite3.Connection, entity_id: str, document_id: str) -> None:
    conn.execute(
        "INSERT INTO entities (id, name, entity_type, created_at, document_id) VALUES (?, ?, ?, ?, ?)",
        (entity_id, "E", "person", _now(), document_id),
    )
    conn.commit()


def _insert_entity_with_chunk(conn: sqlite3.Connection, entity_id: str, document_id: str, chunk_id: str) -> None:
    conn.execute(
        """
        INSERT INTO entities (id, name, entity_type, created_at, document_id, chunk_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (entity_id, "E", "person", _now(), document_id, chunk_id),
    )
    conn.commit()


def _insert_edge(
    conn: sqlite3.Connection,
    edge_id: str,
    source_id: str | None,
    target_id: str | None,
    document_id: str,
) -> None:
    conn.execute(
        "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (edge_id, source_id, target_id, "rel", document_id, _now()),
    )
    conn.commit()


def _insert_document_status(conn: sqlite3.Connection, document_id: str) -> None:
    conn.execute(
        "INSERT INTO document_status (document_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (document_id, "done", _now(), _now()),
    )
    conn.commit()


def _insert_document_status_without_document(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO document_status (document_id, status, created_at, updated_at) VALUES (NULL, ?, ?, ?)",
        ("done", _now(), _now()),
    )
    conn.commit()


def _insert_source_page(conn: sqlite3.Connection, page_id: str, source_id: str) -> None:
    conn.execute(
        """
        INSERT INTO source_pages (id, source_id, url, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (page_id, source_id, "https://example.invalid", "discovered", _now(), _now()),
    )
    conn.commit()


def _insert_source_page_without_source(conn: sqlite3.Connection, page_id: str) -> None:
    conn.execute(
        """
        INSERT INTO source_pages (id, source_id, url, status, created_at, updated_at)
        VALUES (?, NULL, ?, ?, ?, ?)
        """,
        (page_id, "https://example.invalid", "discovered", _now(), _now()),
    )
    conn.commit()


class _NullVectorStore:
    def store_embedding(self, **kwargs) -> None:  # noqa: ANN003
        pass

    def delete_embedding(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass


class _NullEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 3] * len(texts)


def _make_document_store(conn: sqlite3.Connection) -> DocumentStore:
    return DocumentStore(conn, GraphStore(conn), _NullVectorStore(), _NullEmbedder())


class TestIntegrityExtractionContract:
    def test_schema_re_exports_integrity_function(self) -> None:
        assert audit_integrity_via_schema is audit_integrity


class TestIntegrityAudit:
    def test_chunks_orphaned_detects_one_orphan(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-1")
        _insert_chunk(conn, "chunk-1", "doc-1")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-1'")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 1
        assert "chunk-1" in result["chunks_orphaned"]["ids"]

    def test_chunks_orphaned_detects_null_document_id(self) -> None:
        conn = _fresh_db()
        _insert_chunk_without_document(conn, "chunk-null-doc")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 1
        assert "chunk-null-doc" in result["chunks_orphaned"]["ids"]

    def test_edges_dangling_detects_orphan_source_id(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-2")
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_edge(conn, "edge-1", "nonexistent-entity-id", None, "doc-2")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 1
        assert "edge-1" in result["edges_dangling"]["ids"]

    def test_entities_orphaned_detects_one_orphan(self) -> None:
        conn = _fresh_db()
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_entity(conn, "entity-1", "nonexistent-doc-id")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["entities_orphaned"]["count"] == 1
        assert "entity-1" in result["entities_orphaned"]["ids"]

    def test_entities_orphaned_chunks_detects_missing_chunk_id(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-entity-chunk")
        _insert_entity_with_chunk(conn, "entity-missing-chunk", "doc-entity-chunk", "missing-chunk")

        result = audit_integrity(conn)

        assert result["entities_orphaned_chunks"]["count"] == 1
        assert "entity-missing-chunk" in result["entities_orphaned_chunks"]["ids"]

    def test_status_orphaned_detects_one_orphan(self) -> None:
        conn = _fresh_db()
        _insert_document_status(conn, "nonexistent-doc-id")

        result = audit_integrity(conn)

        assert result["status_orphaned"]["count"] == 1
        assert "nonexistent-doc-id" in result["status_orphaned"]["ids"]

    def test_status_orphaned_detects_null_document_id(self) -> None:
        conn = _fresh_db()
        _insert_document_status_without_document(conn)

        result = audit_integrity(conn)

        assert result["status_orphaned"]["count"] == 1
        assert "<null>" in result["status_orphaned"]["ids"]

    def test_edges_orphaned_documents_detects_missing_document_id(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-source")
        _insert_entity(conn, "entity-src", "doc-source")
        _insert_entity(conn, "entity-tgt", "doc-source")
        _insert_edge(conn, "edge-missing-doc", "entity-src", "entity-tgt", "missing-doc")

        result = audit_integrity(conn)

        assert result["edges_orphaned_documents"]["count"] == 1
        assert "edge-missing-doc" in result["edges_orphaned_documents"]["ids"]

    def test_documents_orphaned_sources_detects_missing_source_id(self) -> None:
        conn = _fresh_db()
        _insert_document_with_source(conn, "doc-missing-source", "missing-source")

        result = audit_integrity(conn)

        assert result["documents_orphaned_sources"]["count"] == 1
        assert "doc-missing-source" in result["documents_orphaned_sources"]["ids"]

    def test_source_pages_orphaned_sources_detects_missing_source_id(self) -> None:
        conn = _fresh_db()
        _insert_source_page(conn, "page-missing-source", "missing-source")

        result = audit_integrity(conn)

        assert result["source_pages_orphaned_sources"]["count"] == 1
        assert "page-missing-source" in result["source_pages_orphaned_sources"]["ids"]

    def test_source_pages_orphaned_sources_detects_null_source_id(self) -> None:
        conn = _fresh_db()
        _insert_source_page_without_source(conn, "page-null-source")

        result = audit_integrity(conn)

        assert result["source_pages_orphaned_sources"]["count"] == 1
        assert "page-null-source" in result["source_pages_orphaned_sources"]["ids"]

    def test_clean_db_returns_all_keys_with_zero_counts(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-a")
        _insert_chunk(conn, "chunk-a", "doc-a")
        _insert_entity(conn, "entity-a", "doc-a")
        _insert_entity(conn, "entity-b", "doc-a")
        _insert_edge(conn, "edge-a", "entity-a", "entity-b", "doc-a")
        _insert_document_status(conn, "doc-a")

        result = audit_integrity(conn)

        for key in (
            "chunks_orphaned",
            "entities_orphaned",
            "entities_orphaned_chunks",
            "edges_dangling",
            "edges_orphaned_documents",
            "documents_orphaned_sources",
            "source_pages_orphaned_sources",
            "status_orphaned",
        ):
            assert key in result
            assert result[key]["count"] == 0
            assert result[key]["ids"] == []

    def test_audit_is_read_only(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-ro")
        _insert_chunk(conn, "chunk-ro", "doc-ro")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-ro'")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        before = conn.total_changes
        audit_integrity(conn)
        after = conn.total_changes

        assert before == after

    def test_edges_dangling_detects_orphan_target_id(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-3")
        _insert_entity(conn, "entity-2", "doc-3")
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_edge(conn, "edge-2", "entity-2", "nonexistent-target-id", "doc-3")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 1
        assert "edge-2" in result["edges_dangling"]["ids"]

    def test_edges_dangling_detects_null_endpoints(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-null-edge")
        _insert_edge(conn, "edge-null-endpoints", None, None, "doc-null-edge")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 1
        assert "edge-null-endpoints" in result["edges_dangling"]["ids"]

    def test_edge_with_valid_nonnull_target_id_not_flagged_as_dangling(self) -> None:
        conn = _fresh_db()
        _insert_document(conn, "doc-clean")
        _insert_entity(conn, "entity-src", "doc-clean")
        _insert_entity(conn, "entity-tgt", "doc-clean")
        _insert_edge(conn, "edge-clean", "entity-src", "entity-tgt", "doc-clean")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 0
        assert result["edges_dangling"]["ids"] == []


class TestIntegrityConsolidation:
    def test_clean_chain_returns_zero_for_all_audit_categories(self) -> None:
        conn = _fresh_db()
        store = _make_document_store(conn)
        doc_id = "doc-1589"

        store.insert_document(
            doc_id,
            IntakeResult(
                content="hello integrity",
                source="test",
                metadata={"source_type": "text"},
            ),
        )

        chunk_ids = store.store_chunks(doc_id, [Chunk(text="hello integrity", index=0)])

        entity = Entity(
            id="entity-1589",
            name="Entity",
            entity_type=EntityType.CONCEPT,
            document_id=doc_id,
            chunk_id=chunk_ids[0],
        )
        edge = Edge(
            id="edge-1589",
            source_id="entity-1589",
            target_id="entity-1589",
            relation=RelationType.RELATED_TO,
        )
        store.store_extractions(
            [ExtractionResult(entities=[entity], edges=[edge])],
            document_id=doc_id,
            chunk_ids=chunk_ids,
        )

        store.set_status(doc_id, "done")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 0
        assert result["entities_orphaned"]["count"] == 0
        assert result["edges_dangling"]["count"] == 0
        assert result["status_orphaned"]["count"] == 0

    def test_orphan_rows_are_detected_with_counts_and_ids(self) -> None:
        conn = _fresh_db()

        orphan_chunk_id = "orphan-chunk-1589"
        orphan_entity_id = "orphan-entity-1589"
        dangling_edge_id = "dangling-edge-1589"
        orphan_status_document_id = "orphan-status-doc-1589"

        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (orphan_chunk_id, "missing-doc-1589", 0, "chunk", _now()),
        )
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, created_at, document_id) VALUES (?, ?, ?, ?, ?)",
            (orphan_entity_id, "Entity", "concept", _now(), "missing-doc-1589"),
        )
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                dangling_edge_id,
                "missing-source-1589",
                "missing-target-1589",
                "related_to",
                "missing-doc-1589",
                _now(),
            ),
        )
        conn.execute(
            "INSERT INTO document_status (document_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (orphan_status_document_id, "done", _now(), _now()),
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 1
        assert orphan_chunk_id in result["chunks_orphaned"]["ids"]
        assert result["entities_orphaned"]["count"] == 1
        assert orphan_entity_id in result["entities_orphaned"]["ids"]
        assert result["edges_dangling"]["count"] == 1
        assert dangling_edge_id in result["edges_dangling"]["ids"]
        assert result["status_orphaned"]["count"] == 1
        assert orphan_status_document_id in result["status_orphaned"]["ids"]
