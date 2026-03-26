"""Tests for DocumentStore — document CRUD extracted from IngestPipeline."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.chunker import Chunk
from owlbear.memory.knowledge.document_store import (
    DocumentStatus,
    DocumentStore,
    compute_content_hash,
)
from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.intake import IntakeResult
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.protocol import HybridEmbedding, SparseVector
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_ENTITIES = [
    Entity(name="func_a", entity_type=EntityType.FUNCTION, description="A function"),
]
SAMPLE_EDGES = [
    Edge(source_id="s1", target_id="t1", relation=RelationType.DEFINES),
]
SAMPLE_EXTRACTION = ExtractionResult(entities=SAMPLE_ENTITIES, edges=SAMPLE_EDGES)
SAMPLE_INTAKE = IntakeResult(
    content="hello world",
    source="test.txt",
    metadata={"source_type": "file"},
)
SAMPLE_CHUNKS = [
    Chunk(text="chunk one", index=0, metadata={}),
    Chunk(text="chunk two", index=1, metadata={}),
]
SAMPLE_HYBRID_EMBEDDINGS = [
    HybridEmbedding(
        dense=[0.1] * 1024,
        sparse=SparseVector(indices=[1, 2], values=[0.5, 0.3]),
    ),
    HybridEmbedding(
        dense=[0.2] * 1024,
        sparse=SparseVector(indices=[3, 4], values=[0.4, 0.2]),
    ),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.Connection(":memory:")
    init_db(c)
    return c


@pytest.fixture
def mock_graph() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_vectors() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_embedder() -> MagicMock:
    embedder = MagicMock(spec=["embed", "embed_hybrid"])
    embedder.embed_hybrid.return_value = list(SAMPLE_HYBRID_EMBEDDINGS)
    return embedder


@pytest.fixture
def store(
    conn: sqlite3.Connection,
    mock_graph: MagicMock,
    mock_vectors: MagicMock,
    mock_embedder: MagicMock,
) -> DocumentStore:
    return DocumentStore(
        conn=conn,
        graph_store=mock_graph,
        vector_store=mock_vectors,
        embedding_provider=mock_embedder,
    )


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    def test_deterministic(self) -> None:
        assert compute_content_hash("hello") == compute_content_hash("hello")

    def test_strips_whitespace(self) -> None:
        assert compute_content_hash("  hello  ") == compute_content_hash("hello")

    def test_different_content_gives_different_hash(self) -> None:
        assert compute_content_hash("a") != compute_content_hash("b")


# ---------------------------------------------------------------------------
# DocumentStatus model
# ---------------------------------------------------------------------------


class TestDocumentStatus:
    def test_frozen(self) -> None:
        ds = DocumentStatus(document_id="d1", content_hash="h1", status="indexed")
        with pytest.raises(ValidationError):
            ds.status = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DocumentStore
# ---------------------------------------------------------------------------


class TestDocumentStoreSetStatus:
    def test_insert_new(self, store: DocumentStore, conn: sqlite3.Connection) -> None:
        store.set_status("doc1", "pending", source="test.txt", scope="global")
        row = conn.execute(
            "SELECT status, source FROM document_status WHERE document_id = ?", ("doc1",)
        ).fetchone()
        assert row is not None
        assert row[0] == "pending"
        assert row[1] == "test.txt"

    def test_update_existing(self, store: DocumentStore, conn: sqlite3.Connection) -> None:
        store.set_status("doc1", "pending", source="test.txt")
        store.set_status("doc1", "processing")
        row = conn.execute(
            "SELECT status FROM document_status WHERE document_id = ?", ("doc1",)
        ).fetchone()
        assert row[0] == "processing"


class TestDocumentStoreFindStatus:
    def test_not_found(self, store: DocumentStore) -> None:
        assert store.find_status_by_source("missing") is None

    def test_found(self, store: DocumentStore) -> None:
        store.set_status("doc1", "indexed", source="test.txt")
        store.update_content_hash("doc1", "hello")
        result = store.find_status_by_source("test.txt")
        assert result is not None
        assert result.document_id == "doc1"
        assert result.status == "indexed"


class TestDocumentStoreContentChanged:
    def test_new_source(self, store: DocumentStore) -> None:
        changed, doc_id = store.check_content_changed("new.txt", "content")
        assert changed is True
        assert doc_id is None

    def test_unchanged(self, store: DocumentStore) -> None:
        store.set_status("doc1", "indexed", source="test.txt")
        store.update_content_hash("doc1", "hello")
        changed, doc_id = store.check_content_changed("test.txt", "hello")
        assert changed is False
        assert doc_id == "doc1"

    def test_changed(self, store: DocumentStore) -> None:
        store.set_status("doc1", "indexed", source="test.txt")
        store.update_content_hash("doc1", "old content")
        changed, doc_id = store.check_content_changed("test.txt", "new content")
        assert changed is True
        assert doc_id == "doc1"


class TestDocumentStoreInsertDocument:
    def test_inserts_row(self, store: DocumentStore, conn: sqlite3.Connection) -> None:
        store.insert_document("doc1", SAMPLE_INTAKE, scope="global")
        row = conn.execute(
            "SELECT title, content FROM documents WHERE id = ?", ("doc1",)
        ).fetchone()
        assert row is not None
        assert row[0] == "test.txt"
        assert row[1] == "hello world"


class TestDocumentStoreChunks:
    def test_stores_chunks_returns_ids(
        self, store: DocumentStore, conn: sqlite3.Connection
    ) -> None:
        store.insert_document("doc1", SAMPLE_INTAKE, scope="global")
        ids = store.store_chunks("doc1", SAMPLE_CHUNKS, scope="global")
        assert len(ids) == 2
        row = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", ("doc1",)
        ).fetchone()
        assert row[0] == 2


class TestDocumentStoreEmbeddings:
    def test_stores_embeddings(self, store: DocumentStore, mock_vectors: MagicMock) -> None:
        store.store_embeddings("doc1", SAMPLE_CHUNKS, SAMPLE_HYBRID_EMBEDDINGS, scope="global")
        assert mock_vectors.store_embedding.call_count == 2


class TestDocumentStoreExtractions:
    def test_stores_entities_and_edges(self, store: DocumentStore, mock_graph: MagicMock) -> None:
        results = [SAMPLE_EXTRACTION]
        e_count, ed_count = store.store_extractions(
            results, scope="global", document_id="doc1", pipeline_name="ingest"
        )
        assert e_count == 1
        assert ed_count == 1
        assert mock_graph.insert_entity.call_count == 1
        assert mock_graph.insert_edge.call_count == 1


class TestDocumentStoreEntityEmbeddings:
    def test_embeds_and_stores(
        self, store: DocumentStore, mock_vectors: MagicMock, mock_embedder: MagicMock
    ) -> None:
        # Mock returns exactly 1 embedding for the 1 entity with a description.
        mock_embedder.embed_hybrid.return_value = [SAMPLE_HYBRID_EMBEDDINGS[0]]
        store.store_entity_embeddings([SAMPLE_EXTRACTION], scope="global")
        assert mock_vectors.store_embedding.call_count == 1


class TestDocumentStoreDelete:
    def test_cascade_delete(self, store: DocumentStore, conn: sqlite3.Connection) -> None:
        store.set_status("doc1", "indexed", source="test.txt")
        store.insert_document("doc1", SAMPLE_INTAKE)
        store.store_chunks("doc1", SAMPLE_CHUNKS)
        # Insert entities and edges directly so delete_document_data exercises that branch.
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, description, document_id) "
            "VALUES (?, ?, ?, ?, ?)",
            ("e1", "func_a", "FUNCTION", "A function", "doc1"),
        )
        conn.execute(
            "INSERT INTO edges (source_id, target_id, relation) VALUES (?, ?, ?)",
            ("e1", "e1", "DEFINES"),
        )
        conn.commit()
        entity_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE document_id = ?", ("doc1",)
        ).fetchone()[0]
        assert entity_count > 0
        store.delete_document_data("doc1")
        docs = conn.execute("SELECT COUNT(*) FROM documents WHERE id = ?", ("doc1",)).fetchone()[0]
        chunks = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", ("doc1",)
        ).fetchone()[0]
        statuses = conn.execute(
            "SELECT COUNT(*) FROM document_status WHERE document_id = ?",
            ("doc1",),
        ).fetchone()[0]
        entities = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE document_id = ?", ("doc1",)
        ).fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        assert docs == 0
        assert chunks == 0
        assert statuses == 0
        assert entities == 0
        assert edges == 0


class TestDocumentStoreUpdateContentHash:
    def test_updates_hash(self, store: DocumentStore, conn: sqlite3.Connection) -> None:
        store.set_status("doc1", "indexed", source="test.txt")
        store.update_content_hash("doc1", "hello world")
        row = conn.execute(
            "SELECT content_hash FROM document_status WHERE document_id = ?", ("doc1",)
        ).fetchone()
        assert row[0] == compute_content_hash("hello world")
