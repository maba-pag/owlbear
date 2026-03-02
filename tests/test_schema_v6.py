"""Tests for schema migration v6 — knowledge_sources table.

TDD red-phase for tasks #429 (tests) and #383 (implementation).
Covers: _SCHEMA_VERSION=6, fresh-DB DDL, v5→v6 migration, idempotency,
indexes, and data preservation.
"""

from __future__ import annotations

import sqlite3

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


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Return True if *table* exists in the database."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None and row[0] > 0


def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    """Return True if *index_name* exists in the database."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,),
    ).fetchone()
    return row is not None and row[0] > 0


def _create_v5_db() -> sqlite3.Connection:
    """Build a v5-schema DB *without* the v6 knowledge_sources table."""
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
        "CREATE TABLE schema_version (version INTEGER, applied_at TEXT)"
    )
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (5, '2026-01-01T00:00:00')"
    )

    # Seed rows so we can verify data preservation after migration.
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
        "INSERT INTO edges (id, source_id, target_id, relation, weight) "
        "VALUES (?, ?, ?, ?, ?)",
        ("edge-1", "ent-1", "ent-1", "self-ref", 1.0),
    )
    conn.execute(
        "INSERT INTO chunks (id, document_id, chunk_index, content) "
        "VALUES (?, ?, ?, ?)",
        ("chunk-1", "doc-1", 0, "chunk content"),
    )
    conn.execute(
        "INSERT INTO document_status (document_id, status, source, content_hash) "
        "VALUES (?, ?, ?, ?)",
        ("doc-1", "complete", "test", "abc123"),
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


class TestSchemaVersionConstant:
    """_SCHEMA_VERSION must be 6."""

    def test_schema_version_is_6(self) -> None:
        assert _SCHEMA_VERSION == 6


# ---------------------------------------------------------------------------
# DDL — fresh database
# ---------------------------------------------------------------------------


class TestFreshDbHasKnowledgeSources:
    """A fresh init_db creates knowledge_sources table with all columns."""

    def test_knowledge_sources_table_exists(self, db: sqlite3.Connection) -> None:
        assert _table_exists(db, "knowledge_sources")

    def test_knowledge_sources_has_all_columns(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "knowledge_sources")
        expected = {
            "id",
            "name",
            "source_type",
            "config",
            "scope",
            "enabled",
            "priority",
            "last_refreshed_at",
            "last_error",
            "created_at",
            "updated_at",
        }
        assert set(cols.keys()) == expected

    def test_unique_index_name_scope_exists(self, db: sqlite3.Connection) -> None:
        assert _index_exists(db, "idx_knowledge_sources_name_scope")

    def test_index_scope_exists(self, db: sqlite3.Connection) -> None:
        assert _index_exists(db, "idx_knowledge_sources_scope")

    def test_schema_version_is_6(self, db: sqlite3.Connection) -> None:
        row = db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 6


# ---------------------------------------------------------------------------
# v5 → v6 migration
# ---------------------------------------------------------------------------


class TestMigrateV5ToV6:
    """v5 → v6 migration adds knowledge_sources table and indexes."""

    def test_knowledge_sources_table_created(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        assert _table_exists(conn, "knowledge_sources")

    def test_knowledge_sources_has_all_columns(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        cols = _table_columns(conn, "knowledge_sources")
        expected = {
            "id",
            "name",
            "source_type",
            "config",
            "scope",
            "enabled",
            "priority",
            "last_refreshed_at",
            "last_error",
            "created_at",
            "updated_at",
        }
        assert set(cols.keys()) == expected

    def test_unique_index_name_scope_created(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        assert _index_exists(conn, "idx_knowledge_sources_name_scope")

    def test_index_scope_created(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        assert _index_exists(conn, "idx_knowledge_sources_scope")

    def test_schema_version_bumped_to_6(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 6

    def test_existing_documents_preserved(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        row = conn.execute(
            "SELECT title FROM documents WHERE id = 'doc-1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "Test Doc"

    def test_existing_entities_preserved(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        row = conn.execute(
            "SELECT name, chunk_id FROM entities WHERE id = 'ent-1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "OldEntity"
        assert row[1] == "chunk-1"

    def test_existing_edges_preserved(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        row = conn.execute(
            "SELECT relation FROM edges WHERE id = 'edge-1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "self-ref"

    def test_existing_chunks_preserved(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        row = conn.execute(
            "SELECT content FROM chunks WHERE id = 'chunk-1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "chunk content"

    def test_existing_document_status_preserved(self) -> None:
        conn = _create_v5_db()
        init_db(conn)
        row = conn.execute(
            "SELECT status, content_hash FROM document_status WHERE document_id = 'doc-1'"
        ).fetchone()
        assert row is not None
        assert row[0] == "complete"
        assert row[1] == "abc123"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Double-calling init_db must be safe."""

    def test_idempotent_on_v5_migration(self) -> None:
        """Running init_db twice on a v5 DB must not raise."""
        conn = _create_v5_db()
        init_db(conn)
        init_db(conn)  # second call — must not raise
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 6

    def test_idempotent_on_fresh_db(self, db: sqlite3.Connection) -> None:
        """Running init_db twice on a fresh DB must not raise."""
        init_db(db)  # second call
        assert _table_exists(db, "knowledge_sources")
        row = db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 6
