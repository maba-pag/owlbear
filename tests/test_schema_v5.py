"""Tests for schema migration v5 — chunk_id on entities.

TDD red-phase for tasks #421 (tests) and #371 (implementation).
Covers: migration v4→v5, Entity.chunk_id field, GraphStore CRUD with
chunk_id, and IngestPipeline threading chunk_ids through extraction.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.ingest import IngestPipeline
from owlbear.memory.knowledge.models import (
    Entity,
    EntityType,
)
from owlbear.memory.knowledge.schema import (
    _SCHEMA_VERSION,
    init_db,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _table_columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    """Return {column_name: column_type} for *table* via PRAGMA."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1]: row[2] for row in rows}


def _create_v4_db() -> sqlite3.Connection:
    """Build a v4-schema DB *without* the v5 chunk_id column on entities."""
    conn = sqlite3.Connection(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        "CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT, content TEXT, "
        "metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE entities (id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, "
        "description TEXT, metadata TEXT, created_at TEXT, "
        "scope TEXT DEFAULT 'global', document_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE edges (id TEXT PRIMARY KEY, source_id TEXT REFERENCES entities(id), "
        "target_id TEXT REFERENCES entities(id), relation TEXT, weight REAL, "
        "metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE chunks (id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id), "
        "chunk_index INTEGER, content TEXT, metadata TEXT, created_at TEXT, "
        "scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE document_status (document_id TEXT PRIMARY KEY, status TEXT, "
        "source TEXT, error TEXT, created_at TEXT, updated_at TEXT, "
        "scope TEXT DEFAULT 'global', content_hash TEXT)"
    )
    conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (4, '2026-01-01T00:00:00')"
    )

    # Seed a row so we can verify NULL after migration.
    conn.execute(
        "INSERT INTO entities (id, name, entity_type) VALUES (?, ?, ?)",
        ("ent-old", "OldEntity", "concept"),
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> sqlite3.Connection:
    """Fresh in-memory database with init_db applied."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    return conn


@pytest.fixture
def graph_store(db: sqlite3.Connection) -> GraphStore:
    """GraphStore backed by a fresh in-memory database."""
    return GraphStore(db)


# ---------------------------------------------------------------------------
# Schema version constant
# ---------------------------------------------------------------------------


class TestSchemaVersionConstant:
    """_SCHEMA_VERSION must be 7 (bumped from 6 by bookmarks migration)."""

    def test_schema_version_is_6(self) -> None:
        assert _SCHEMA_VERSION == 7


# ---------------------------------------------------------------------------
# DDL — fresh database
# ---------------------------------------------------------------------------


class TestFreshDbHasChunkId:
    """A fresh init_db creates entities table with chunk_id column."""

    def test_entities_has_chunk_id_column(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "entities")
        assert "chunk_id" in cols

    def test_schema_version_is_6(self, db: sqlite3.Connection) -> None:
        row = db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 7


# ---------------------------------------------------------------------------
# v4 → v5 migration
# ---------------------------------------------------------------------------


class TestMigrateV4ToV5:
    """v4 → v5 migration adds chunk_id TEXT column to entities."""

    def test_chunk_id_column_added(self) -> None:
        conn = _create_v4_db()
        init_db(conn)
        cols = _table_columns(conn, "entities")
        assert "chunk_id" in cols

    def test_schema_version_bumped_to_6(self) -> None:
        """v4 DB migrated through v5, v6, and v7 ends at version 7."""
        conn = _create_v4_db()
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 7

    def test_existing_rows_get_null_chunk_id(self) -> None:
        conn = _create_v4_db()
        init_db(conn)
        row = conn.execute("SELECT chunk_id FROM entities WHERE id = 'ent-old'").fetchone()
        assert row is not None
        assert row[0] is None

    def test_idempotent_rerun(self) -> None:
        """Running init_db twice on a v4 DB must not raise."""
        conn = _create_v4_db()
        init_db(conn)
        init_db(conn)  # second call — must not raise
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 7

    def test_idempotent_fresh_db(self, db: sqlite3.Connection) -> None:
        """Running init_db twice on a fresh DB must not raise."""
        init_db(db)  # second call
        cols = _table_columns(db, "entities")
        assert "chunk_id" in cols


# ---------------------------------------------------------------------------
# Entity model — chunk_id field
# ---------------------------------------------------------------------------


class TestEntityChunkIdField:
    """Entity model has chunk_id: str | None = None."""

    def test_default_chunk_id_is_none(self) -> None:
        entity = Entity(name="foo", entity_type=EntityType.FUNCTION)
        assert entity.chunk_id is None

    def test_explicit_chunk_id(self) -> None:
        entity = Entity(
            name="bar",
            entity_type=EntityType.CONCEPT,
            chunk_id="chunk-abc",
        )
        assert entity.chunk_id == "chunk-abc"


# ---------------------------------------------------------------------------
# GraphStore — chunk_id in CRUD
# ---------------------------------------------------------------------------


class TestGraphStoreChunkId:
    """GraphStore CRUD operations handle chunk_id."""

    def test_insert_and_get_with_chunk_id(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="ent-1",
            name="func_a",
            entity_type=EntityType.FUNCTION,
            chunk_id="chunk-001",
        )
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("ent-1")

        assert result is not None
        assert result.chunk_id == "chunk-001"

    def test_insert_without_chunk_id_stores_none(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="ent-2",
            name="class_b",
            entity_type=EntityType.CLASS_,
        )
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("ent-2")

        assert result is not None
        assert result.chunk_id is None

    def test_list_entities_includes_chunk_id(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="e1", name="a", entity_type=EntityType.FILE, chunk_id="c1")
        e2 = Entity(id="e2", name="b", entity_type=EntityType.FUNCTION, chunk_id="c2")
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        result = graph_store.list_entities()
        chunk_ids = {e.id: e.chunk_id for e in result}
        assert chunk_ids == {"e1": "c1", "e2": "c2"}

    def test_list_entities_for_document_includes_chunk_id(self, graph_store: GraphStore) -> None:
        e1 = Entity(
            id="e1",
            name="a",
            entity_type=EntityType.FILE,
            document_id="doc-1",
            chunk_id="c1",
        )
        e2 = Entity(
            id="e2",
            name="b",
            entity_type=EntityType.FUNCTION,
            document_id="doc-1",
            chunk_id="c2",
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        result = graph_store.list_entities_for_document("doc-1")
        chunk_ids = {e.id: e.chunk_id for e in result}
        assert chunk_ids == {"e1": "c1", "e2": "c2"}


# ---------------------------------------------------------------------------
# IngestPipeline._store_chunks — returns chunk IDs
# ---------------------------------------------------------------------------


class TestStoreChunksReturnsIds:
    """IngestPipeline._store_chunks() returns list of chunk IDs."""

    @pytest.fixture
    def pipeline(self, db: sqlite3.Connection) -> IngestPipeline:
        """Pipeline with real conn + graph_store, mock everything else."""
        graph = GraphStore(db)
        return IngestPipeline(
            conn=db,
            graph_store=graph,
            vector_store=MagicMock(),
            embedding_provider=MagicMock(),
            entity_extractor=AsyncMock(),
            text_chunker=MagicMock(),
        )

    @staticmethod
    def _insert_doc(db: sqlite3.Connection, doc_id: str) -> None:
        """Insert a minimal document row to satisfy FK constraints."""
        db.execute(
            "INSERT INTO documents (id, title, content, scope) VALUES (?, ?, ?, ?)",
            (doc_id, "t", "c", "global"),
        )
        db.commit()

    def test_returns_list_of_strings(
        self, pipeline: IngestPipeline, db: sqlite3.Connection
    ) -> None:
        from owlbear.memory.knowledge.chunker import Chunk

        self._insert_doc(db, "doc-1")
        chunks = [
            Chunk(text="Hello world", index=0, metadata={}),
            Chunk(text="Goodbye world", index=1, metadata={}),
        ]
        result = pipeline._store_chunks("doc-1", chunks, scope="global")
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(cid, str) for cid in result)

    def test_ids_match_database_rows(
        self, pipeline: IngestPipeline, db: sqlite3.Connection
    ) -> None:
        from owlbear.memory.knowledge.chunker import Chunk

        self._insert_doc(db, "doc-2")
        chunks = [
            Chunk(text="AAA", index=0, metadata={}),
            Chunk(text="BBB", index=1, metadata={}),
        ]
        chunk_ids = pipeline._store_chunks("doc-2", chunks, scope="global")

        db_ids = [
            row[0]
            for row in db.execute(
                "SELECT id FROM chunks WHERE document_id = ? ORDER BY chunk_index",
                ("doc-2",),
            ).fetchall()
        ]
        assert chunk_ids == db_ids


# ---------------------------------------------------------------------------
# IngestPipeline._store_extractions — populates chunk_id
# ---------------------------------------------------------------------------


class TestStoreExtractionsChunkId:
    """_store_extractions stamps chunk_id on entities from corresponding chunk."""

    @pytest.fixture
    def pipeline(self, db: sqlite3.Connection) -> IngestPipeline:
        """Pipeline with mock graph_store to capture insert_entity calls."""
        mock_graph = MagicMock()
        return IngestPipeline(
            conn=db,
            graph_store=mock_graph,
            vector_store=MagicMock(),
            embedding_provider=MagicMock(),
            entity_extractor=AsyncMock(),
            text_chunker=MagicMock(),
        )

    def test_entities_get_chunk_id_from_corresponding_chunk(self, pipeline: IngestPipeline) -> None:
        """Each extraction result's entities get the chunk_id from the matching chunk."""
        chunk_ids = ["chunk-A", "chunk-B"]
        extractions = [
            ExtractionResult(
                entities=[
                    Entity(name="e1", entity_type=EntityType.FUNCTION, description="f1"),
                ],
                edges=[],
            ),
            ExtractionResult(
                entities=[
                    Entity(name="e2", entity_type=EntityType.CONCEPT, description="c1"),
                    Entity(name="e3", entity_type=EntityType.PATTERN, description="p1"),
                ],
                edges=[],
            ),
        ]

        pipeline._store_extractions(
            extractions, scope="global", document_id="doc-X", chunk_ids=chunk_ids
        )

        calls = pipeline._graph.insert_entity.call_args_list
        assert len(calls) == 3

        # First extraction → chunk-A
        assert calls[0][0][0].chunk_id == "chunk-A"
        # Second extraction → chunk-B
        assert calls[1][0][0].chunk_id == "chunk-B"
        assert calls[2][0][0].chunk_id == "chunk-B"

    def test_without_chunk_ids_entities_have_no_chunk_id(self, pipeline: IngestPipeline) -> None:
        """When chunk_ids is not provided, entities keep chunk_id=None (backward compat)."""
        extractions = [
            ExtractionResult(
                entities=[
                    Entity(name="e1", entity_type=EntityType.FUNCTION),
                ],
                edges=[],
            ),
        ]

        pipeline._store_extractions(extractions, scope="global", document_id="doc-Y")

        calls = pipeline._graph.insert_entity.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0].chunk_id is None
