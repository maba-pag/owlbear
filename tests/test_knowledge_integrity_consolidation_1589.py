"""Consolidation tests for task #1589: knowledge DB integrity hardening."""

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
from owlbear_knowledge.schema import init_db


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class _NullVectorStore:
    """Stub vector store that no-ops all calls."""

    def store_embedding(self, **kwargs) -> None:  # noqa: ANN003
        pass

    def delete_embedding(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass


class _NullEmbedder:
    """Stub embedder that returns zero vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 3] * len(texts)


def _make_document_store(conn: sqlite3.Connection) -> DocumentStore:
    return DocumentStore(conn, GraphStore(conn), _NullVectorStore(), _NullEmbedder())


def _fresh_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


class TestFromAC_KnowledgeIntegrityConsolidation1589:
    """AC consolidation tests for DocumentStore chain + audit_integrity."""

    def test_ac1_clean_chain_returns_zero_for_all_audit_categories(self) -> None:
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

        # AC-1a: row-presence proof before auditing.
        doc_row = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
        assert doc_row is not None, "insert_document() must persist the document row"

        chunk_row = conn.execute("SELECT id FROM chunks WHERE id = ?", (chunk_ids[0],)).fetchone()
        assert chunk_row is not None, "store_chunks() must persist the created chunk row"

        entity_row = conn.execute("SELECT id FROM entities WHERE id = ?", ("entity-1589",)).fetchone()
        assert entity_row is not None, "store_extractions() must persist the entity row"

        edge_row = conn.execute("SELECT id FROM edges WHERE id = ?", ("edge-1589",)).fetchone()
        assert edge_row is not None, "store_extractions() must persist the edge row"

        status_row = conn.execute("SELECT status FROM document_status WHERE document_id = ?", (doc_id,)).fetchone()
        assert status_row is not None, "set_status() must persist the document_status row"
        assert status_row[0] == "done", "set_status() must store the correct status value"

        # AC-1b: linkage/provenance fields are correct before auditing.
        chunk_link_row = conn.execute("SELECT document_id FROM chunks WHERE id = ?", (chunk_ids[0],)).fetchone()
        assert chunk_link_row is not None
        assert chunk_link_row[0] == doc_id, "chunks.document_id must reference the parent document"

        entity_link_row = conn.execute(
            "SELECT document_id, chunk_id FROM entities WHERE id = ?",
            ("entity-1589",),
        ).fetchone()
        assert entity_link_row is not None
        assert entity_link_row[0] == doc_id, "entities.document_id must reference the parent document"
        assert entity_link_row[1] == chunk_ids[0], "entities.chunk_id must reference the parent chunk"

        edge_link_row = conn.execute(
            "SELECT source_id, target_id, document_id FROM edges WHERE id = ?",
            ("edge-1589",),
        ).fetchone()
        assert edge_link_row is not None
        assert edge_link_row[0] == "entity-1589", "edges.source_id must equal the entity id"
        assert edge_link_row[1] == "entity-1589", "edges.target_id must equal the entity id"
        assert edge_link_row[2] == doc_id, "edges.document_id must reference the parent document"

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 0
        assert result["entities_orphaned"]["count"] == 0
        assert result["edges_dangling"]["count"] == 0
        assert result["status_orphaned"]["count"] == 0

    def test_ac2_orphan_rows_are_detected_with_counts_and_ids(self) -> None:
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
