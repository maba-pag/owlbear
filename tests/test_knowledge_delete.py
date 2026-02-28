"""Tests for IngestPipeline.delete_document_data() — cascade delete."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.ingest import IngestPipeline
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory SQLite database with knowledge schema."""
    c = sqlite3.Connection(":memory:")
    init_db(c)
    return c


@pytest.fixture
def graph_store(conn: sqlite3.Connection) -> GraphStore:
    """Real GraphStore backed by the in-memory DB."""
    return GraphStore(conn)


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock VectorStore with delete_by_document_id."""
    vs = MagicMock()
    vs.delete_by_document_id = MagicMock(return_value=3)
    return vs


@pytest.fixture
def pipeline(
    conn: sqlite3.Connection,
    graph_store: GraphStore,
    mock_vector_store: MagicMock,
) -> IngestPipeline:
    """IngestPipeline with real DB and mock embedder/extractor/chunker."""
    return IngestPipeline(
        conn=conn,
        graph_store=graph_store,
        vector_store=mock_vector_store,
        embedding_provider=MagicMock(spec=["embed"]),
        entity_extractor=MagicMock(),
        text_chunker=MagicMock(),
    )


def _seed_document(conn: sqlite3.Connection, doc_id: str, graph: GraphStore) -> None:
    """Insert a document with chunks, entities, edges, and document_status."""
    conn.execute(
        "INSERT INTO documents (id, title, content, scope, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (doc_id, "Test Doc", "content", "global", "2026-01-01T00:00:00"),
    )
    conn.execute(
        "INSERT INTO document_status (document_id, status, scope, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (doc_id, "indexed", "global", "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
    )
    for i in range(3):
        conn.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content, scope, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (f"chunk-{doc_id}-{i}", doc_id, i, f"chunk {i}", "global", "2026-01-01T00:00:00"),
        )

    # Entities linked to this document via document_id column.
    e1 = Entity(id=f"ent-{doc_id}-1", name="foo", entity_type=EntityType.FUNCTION)
    e2 = Entity(id=f"ent-{doc_id}-2", name="bar", entity_type=EntityType.CLASS_)
    graph.insert_entity(e1)
    graph.insert_entity(e2)
    # Set document_id on entities (column exists in schema v4).
    conn.execute("UPDATE entities SET document_id = ? WHERE id = ?", (doc_id, e1.id))
    conn.execute("UPDATE entities SET document_id = ? WHERE id = ?", (doc_id, e2.id))

    # Edge between the two entities.
    edge = Edge(
        id=f"edge-{doc_id}-1",
        source_id=e1.id,
        target_id=e2.id,
        relation=RelationType.DEFINES,
    )
    graph.insert_edge(edge)
    conn.commit()


def _count(conn: sqlite3.Connection, table: str, doc_id: str) -> int:
    """Count rows related to *doc_id* in *table*."""
    if table == "documents":
        return conn.execute("SELECT count(*) FROM documents WHERE id = ?", (doc_id,)).fetchone()[0]
    if table == "document_status":
        return conn.execute(
            "SELECT count(*) FROM document_status WHERE document_id = ?", (doc_id,)
        ).fetchone()[0]
    if table == "chunks":
        return conn.execute(
            "SELECT count(*) FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchone()[0]
    if table == "entities":
        return conn.execute(
            "SELECT count(*) FROM entities WHERE document_id = ?", (doc_id,)
        ).fetchone()[0]
    msg = f"Unknown table: {table}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeleteDocumentData:
    """Cascade-delete all data for a single document."""

    def test_chunks_deleted(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        pipeline: IngestPipeline,
    ) -> None:
        """Chunks linked to the document are removed."""
        _seed_document(conn, "doc-1", graph_store)
        assert _count(conn, "chunks", "doc-1") == 3

        pipeline.delete_document_data("doc-1")

        assert _count(conn, "chunks", "doc-1") == 0

    def test_entities_deleted(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        pipeline: IngestPipeline,
    ) -> None:
        """Entities with matching document_id are removed."""
        _seed_document(conn, "doc-1", graph_store)
        assert _count(conn, "entities", "doc-1") == 2

        pipeline.delete_document_data("doc-1")

        assert _count(conn, "entities", "doc-1") == 0

    def test_edges_deleted(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        pipeline: IngestPipeline,
    ) -> None:
        """Edges referencing deleted entities are removed."""
        _seed_document(conn, "doc-1", graph_store)
        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert edge_count == 1

        pipeline.delete_document_data("doc-1")

        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert edge_count == 0

    def test_document_row_deleted(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        pipeline: IngestPipeline,
    ) -> None:
        """The documents table row is removed."""
        _seed_document(conn, "doc-1", graph_store)
        assert _count(conn, "documents", "doc-1") == 1

        pipeline.delete_document_data("doc-1")

        assert _count(conn, "documents", "doc-1") == 0

    def test_document_status_deleted(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        pipeline: IngestPipeline,
    ) -> None:
        """The document_status row is removed."""
        _seed_document(conn, "doc-1", graph_store)
        assert _count(conn, "document_status", "doc-1") == 1

        pipeline.delete_document_data("doc-1")

        assert _count(conn, "document_status", "doc-1") == 0

    def test_qdrant_points_removed(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        mock_vector_store: MagicMock,
        pipeline: IngestPipeline,
    ) -> None:
        """Qdrant delete_by_document_id is called with the document ID."""
        _seed_document(conn, "doc-1", graph_store)

        pipeline.delete_document_data("doc-1")

        mock_vector_store.delete_by_document_id.assert_called_once_with("doc-1")

    def test_no_orphan_rows_after_delete(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        pipeline: IngestPipeline,
    ) -> None:
        """All 4 tables are clean — no rows reference the deleted document."""
        _seed_document(conn, "doc-1", graph_store)

        pipeline.delete_document_data("doc-1")

        for table in ("chunks", "entities", "documents", "document_status"):
            assert _count(conn, table, "doc-1") == 0, f"Orphan rows in {table}"
        assert conn.execute("SELECT count(*) FROM edges").fetchone()[0] == 0

    def test_other_documents_untouched(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        pipeline: IngestPipeline,
    ) -> None:
        """Deleting doc-1 does not affect doc-2."""
        _seed_document(conn, "doc-1", graph_store)
        _seed_document(conn, "doc-2", graph_store)

        pipeline.delete_document_data("doc-1")

        # doc-2 is untouched.
        assert _count(conn, "chunks", "doc-2") == 3
        assert _count(conn, "entities", "doc-2") == 2
        assert _count(conn, "documents", "doc-2") == 1
        assert _count(conn, "document_status", "doc-2") == 1

    def test_delete_nonexistent_document_is_noop(
        self,
        mock_vector_store: MagicMock,
        pipeline: IngestPipeline,
    ) -> None:
        """Deleting a non-existent document does not raise."""
        pipeline.delete_document_data("no-such-doc")

        mock_vector_store.delete_by_document_id.assert_called_once_with("no-such-doc")

    def test_vector_store_without_delete_method(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
    ) -> None:
        """Pipeline works with a vector store lacking delete_by_document_id."""
        plain_vs = MagicMock(spec=["store_embedding", "get_embedding", "search_similar"])
        pipe = IngestPipeline(
            conn=conn,
            graph_store=graph_store,
            vector_store=plain_vs,
            embedding_provider=MagicMock(spec=["embed"]),
            entity_extractor=MagicMock(),
            text_chunker=MagicMock(),
        )
        _seed_document(conn, "doc-1", graph_store)

        pipe.delete_document_data("doc-1")

        # SQLite rows still cleaned.
        assert _count(conn, "chunks", "doc-1") == 0
        assert _count(conn, "documents", "doc-1") == 0
