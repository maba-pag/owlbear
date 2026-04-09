"""Tests for schema migration v8 — consolidation memory columns and table.

TDD red-phase for task #769 (tests) and #721 (implementation).
Covers: _SCHEMA_VERSION=8, fresh-DB DDL, v7→v8 migration, idempotency,
data preservation, and default values for existing rows.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

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


def _column_default(conn: sqlite3.Connection, table: str, column: str) -> object:
    """Return the default value for *column* in *table* via PRAGMA."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for row in rows:
        if row[1] == column:
            return row[4]  # dflt_value
    return None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Return True if *table* exists in the database."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None and row[0] > 0


def _create_v7_db() -> sqlite3.Connection:
    """Build a v7-schema DB *without* v8 consolidation columns/table.

    Replicates the full v7 schema: documents, entities (with document_id,
    chunk_id), edges, chunks, document_status (with content_hash),
    knowledge_sources, bookmarks, schema_version=7.
    """
    conn = sqlite3.Connection(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        "CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT, content TEXT, "
        "metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE entities (id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, "
        "description TEXT, metadata TEXT, created_at TEXT, "
        "scope TEXT DEFAULT 'global', document_id TEXT, chunk_id TEXT)"
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
    conn.execute(
        "CREATE TABLE knowledge_sources (id TEXT PRIMARY KEY, name TEXT NOT NULL, "
        "source_type TEXT NOT NULL, config TEXT NOT NULL, scope TEXT DEFAULT 'global', "
        "enabled INTEGER DEFAULT 1, priority INTEGER DEFAULT 0, "
        "last_refreshed_at TEXT, last_error TEXT, created_at TEXT NOT NULL, "
        "updated_at TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE bookmarks (id TEXT PRIMARY KEY, url TEXT NOT NULL, "
        "title TEXT NOT NULL, description TEXT, tags TEXT NOT NULL DEFAULT '[]', "
        "relevance_score REAL NOT NULL DEFAULT 0.0, reason TEXT, "
        "scope TEXT NOT NULL DEFAULT 'global', document_id TEXT, content_hash TEXT, "
        "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (7, ?)",
        (datetime.now(tz=UTC).isoformat(),),
    )

    # Seed data rows for preservation and default-value tests.
    conn.execute(
        "INSERT INTO documents (id, title, content, scope) VALUES (?, ?, ?, ?)",
        ("doc-1", "Test Doc", "Sample content", "global"),
    )
    conn.execute(
        "INSERT INTO entities (id, name, entity_type, document_id, chunk_id) "
        "VALUES (?, ?, ?, ?, ?)",
        ("ent-1", "OldEntity", "concept", "doc-1", "chunk-1"),
    )
    conn.execute(
        "INSERT INTO edges (id, source_id, target_id, relation, weight) VALUES (?, ?, ?, ?, ?)",
        ("edge-1", "ent-1", "ent-1", "self-ref", 1.0),
    )
    conn.execute(
        "INSERT INTO chunks (id, document_id, chunk_index, content) VALUES (?, ?, ?, ?)",
        ("chunk-1", "doc-1", 0, "chunk content"),
    )
    conn.execute(
        "INSERT INTO document_status (document_id, status, source, content_hash) "
        "VALUES (?, ?, ?, ?)",
        ("doc-1", "complete", "test", "abc123"),
    )
    conn.execute(
        "INSERT INTO knowledge_sources (id, name, source_type, config, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("ks-1", "test-src", "url_list", "{}", "2026-01-01", "2026-01-01"),
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


# ---------------------------------------------------------------------------
# Schema version constant
# ---------------------------------------------------------------------------


class TestFromAC_SchemaVersionConstant:
    """_SCHEMA_VERSION must be 8 (bumped from 7 by consolidation migration)."""

    def test_schema_version_is_8(self) -> None:
        assert _SCHEMA_VERSION == 8


# ---------------------------------------------------------------------------
# DDL — fresh database: entities.importance column
# ---------------------------------------------------------------------------


class TestFromAC_FreshDbEntitiesImportance:
    """A fresh init_db creates entities table with importance column."""

    def test_entities_has_importance_column(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "entities")
        assert "importance" in cols

    def test_entities_importance_type_is_real(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "entities")
        assert cols["importance"] == "REAL"

    def test_entities_importance_default_is_half(self, db: sqlite3.Connection) -> None:
        default = _column_default(db, "entities", "importance")
        assert default in ("0.5", 0.5)  # PRAGMA returns string or numeric


# ---------------------------------------------------------------------------
# DDL — fresh database: chunks.consolidated column
# ---------------------------------------------------------------------------


class TestFromAC_FreshDbChunksConsolidated:
    """A fresh init_db creates chunks table with consolidated column."""

    def test_chunks_has_consolidated_column(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "chunks")
        assert "consolidated" in cols

    def test_chunks_consolidated_type_is_integer(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "chunks")
        assert cols["consolidated"] == "INTEGER"

    def test_chunks_consolidated_default_is_zero(self, db: sqlite3.Connection) -> None:
        default = _column_default(db, "chunks", "consolidated")
        assert default in ("0", 0)  # PRAGMA returns string or numeric


# ---------------------------------------------------------------------------
# DDL — fresh database: consolidations table
# ---------------------------------------------------------------------------


class TestFromAC_FreshDbConsolidationsTable:
    """A fresh init_db creates the consolidations table with all columns."""

    def test_consolidations_table_exists(self, db: sqlite3.Connection) -> None:
        assert _table_exists(db, "consolidations")

    def test_consolidations_has_all_columns(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "consolidations")
        expected = {"id", "source_ids", "summary", "insight", "created_at", "scope"}
        assert set(cols.keys()) == expected

    def test_consolidations_id_is_primary_key(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "consolidations")
        assert cols["id"] == "TEXT"

    def test_consolidations_source_ids_not_null(self, db: sqlite3.Connection) -> None:
        """source_ids column must be NOT NULL."""
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO consolidations (id, summary) VALUES (?, ?)",
                ("c-1", "test"),
            )

    def test_consolidations_scope_default_global(self, db: sqlite3.Connection) -> None:
        default = _column_default(db, "consolidations", "scope")
        assert default == "'global'"

    def test_fresh_db_schema_version_is_8(self, db: sqlite3.Connection) -> None:
        row = db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 8


# ---------------------------------------------------------------------------
# v7 → v8 migration: entities.importance
# ---------------------------------------------------------------------------


class TestFromAC_MigrateV7ToV8EntitiesImportance:
    """v7 → v8 migration adds importance column to entities."""

    def test_entities_importance_added(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        cols = _table_columns(conn, "entities")
        assert "importance" in cols

    def test_entities_importance_type_after_migration(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        cols = _table_columns(conn, "entities")
        assert cols["importance"] == "REAL"


# ---------------------------------------------------------------------------
# v7 → v8 migration: chunks.consolidated
# ---------------------------------------------------------------------------


class TestFromAC_MigrateV7ToV8ChunksConsolidated:
    """v7 → v8 migration adds consolidated column to chunks."""

    def test_chunks_consolidated_added(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        cols = _table_columns(conn, "chunks")
        assert "consolidated" in cols

    def test_chunks_consolidated_type_after_migration(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        cols = _table_columns(conn, "chunks")
        assert cols["consolidated"] == "INTEGER"


# ---------------------------------------------------------------------------
# v7 → v8 migration: consolidations table
# ---------------------------------------------------------------------------


class TestFromAC_MigrateV7ToV8ConsolidationsTable:
    """v7 → v8 migration creates the consolidations table."""

    def test_consolidations_table_created(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        assert _table_exists(conn, "consolidations")

    def test_consolidations_has_all_columns_after_migration(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        cols = _table_columns(conn, "consolidations")
        expected = {"id", "source_ids", "summary", "insight", "created_at", "scope"}
        assert set(cols.keys()) == expected

    def test_schema_version_bumped_to_8(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 8


# ---------------------------------------------------------------------------
# v7 → v8 migration: data preservation
# ---------------------------------------------------------------------------


class TestFromAC_MigrateV7DataPreserved:
    """Existing v7 data rows survive the v8 migration."""

    def test_existing_documents_preserved(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        # Verify v8 migration actually ran
        ver = conn.execute("SELECT version FROM schema_version").fetchone()
        assert ver is not None
        assert ver[0] == 8
        row = conn.execute("SELECT title FROM documents WHERE id = 'doc-1'").fetchone()
        assert row is not None
        assert row[0] == "Test Doc"

    def test_existing_entities_preserved(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        # Verify v8 migration actually ran
        ver = conn.execute("SELECT version FROM schema_version").fetchone()
        assert ver is not None
        assert ver[0] == 8
        row = conn.execute("SELECT name, chunk_id FROM entities WHERE id = 'ent-1'").fetchone()
        assert row is not None
        assert row[0] == "OldEntity"
        assert row[1] == "chunk-1"

    def test_existing_edges_preserved(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        # Verify v8 migration actually ran
        ver = conn.execute("SELECT version FROM schema_version").fetchone()
        assert ver is not None
        assert ver[0] == 8
        row = conn.execute("SELECT relation FROM edges WHERE id = 'edge-1'").fetchone()
        assert row is not None
        assert row[0] == "self-ref"

    def test_existing_chunks_preserved(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        # Verify v8 migration actually ran
        ver = conn.execute("SELECT version FROM schema_version").fetchone()
        assert ver is not None
        assert ver[0] == 8
        row = conn.execute("SELECT content FROM chunks WHERE id = 'chunk-1'").fetchone()
        assert row is not None
        assert row[0] == "chunk content"

    def test_existing_document_status_preserved(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        # Verify v8 migration actually ran
        ver = conn.execute("SELECT version FROM schema_version").fetchone()
        assert ver is not None
        assert ver[0] == 8
        row = conn.execute(
            "SELECT status, content_hash FROM document_status WHERE document_id = 'doc-1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "complete"
        assert row[1] == "abc123"

    def test_existing_knowledge_sources_preserved(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        # Verify v8 migration actually ran
        ver = conn.execute("SELECT version FROM schema_version").fetchone()
        assert ver is not None
        assert ver[0] == 8
        row = conn.execute("SELECT name FROM knowledge_sources WHERE id = 'ks-1'").fetchone()
        assert row is not None
        assert row[0] == "test-src"


# ---------------------------------------------------------------------------
# v7 → v8 migration: existing rows get default values
# ---------------------------------------------------------------------------


class TestFromAC_MigrateV7DefaultValues:
    """Existing v7 entity rows get importance=0.5 and chunk rows get consolidated=0."""

    def test_existing_entity_gets_default_importance(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        row = conn.execute("SELECT importance FROM entities WHERE id = 'ent-1'").fetchone()
        assert row is not None
        assert row[0] == 0.5

    def test_existing_chunk_gets_default_consolidated(self) -> None:
        conn = _create_v7_db()
        init_db(conn)
        row = conn.execute("SELECT consolidated FROM chunks WHERE id = 'chunk-1'").fetchone()
        assert row is not None
        assert row[0] == 0


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestFromAC_Idempotency:
    """Double-calling init_db must be safe — no errors, no data loss."""

    def test_idempotent_v7_migration(self) -> None:
        """Running init_db twice on a v7 DB must not raise."""
        conn = _create_v7_db()
        init_db(conn)
        init_db(conn)  # second call — must not raise
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 8

    def test_idempotent_fresh_db(self, db: sqlite3.Connection) -> None:
        """Running init_db twice on a fresh DB must not raise."""
        init_db(db)  # second call
        assert _table_exists(db, "consolidations")
        cols = _table_columns(db, "entities")
        assert "importance" in cols
        row = db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 8

    def test_idempotent_preserves_consolidation_data(self) -> None:
        """Consolidation rows survive a second init_db call."""
        conn = _create_v7_db()
        init_db(conn)
        conn.execute(
            "INSERT INTO consolidations (id, source_ids, summary, scope) VALUES (?, ?, ?, ?)",
            ("cons-1", '["chunk-1"]', "test summary", "global"),
        )
        conn.commit()
        init_db(conn)  # second call — must not drop data
        row = conn.execute("SELECT summary FROM consolidations WHERE id = 'cons-1'").fetchone()
        assert row is not None
        assert row[0] == "test summary"

    def test_idempotent_preserves_existing_entity_importance(self) -> None:
        """Entity importance values survive a second init_db call."""
        conn = _create_v7_db()
        init_db(conn)
        init_db(conn)  # second call
        row = conn.execute("SELECT importance FROM entities WHERE id = 'ent-1'").fetchone()
        assert row is not None
        assert row[0] == 0.5
