"""Tests for knowledge-graph schema v2 migration.

Covers: fresh v2 init, v1→v2 migration, idempotency, data preservation,
and correct column definitions for chunks and document_status.

Task #188 — Test knowledge schema v2
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


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check whether *table* exists in sqlite_master."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table,),
    ).fetchone()
    return bool(row and row[0])


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the set of column names for *table*."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _pk_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return names of primary-key columns for *table*."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows if r[5]]


def _foreign_keys(conn: sqlite3.Connection, table: str) -> list[dict[str, str]]:
    """Return foreign key definitions for *table*."""
    rows = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    return [{"from": r[3], "table": r[2], "to": r[4]} for r in rows]


def _create_v1_database(conn: sqlite3.Connection) -> None:
    """Set up a v1 schema manually — no chunks, no document_status."""
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        "CREATE TABLE IF NOT EXISTS documents ("
        "id TEXT PRIMARY KEY, title TEXT, content TEXT, "
        "metadata TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS entities ("
        "id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, "
        "description TEXT, metadata TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS edges ("
        "id TEXT PRIMARY KEY, "
        "source_id TEXT REFERENCES entities(id), "
        "target_id TEXT REFERENCES entities(id), "
        "relation TEXT, weight REAL, metadata TEXT, created_at TEXT)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER, applied_at TEXT)")
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (1, '2026-01-01T00:00:00+00:00')"
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_db() -> sqlite3.Connection:
    """In-memory connection with a fresh init_db (v2)."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    return conn


@pytest.fixture
def v1_db() -> sqlite3.Connection:
    """In-memory connection with v1 schema (pre-migration)."""
    conn = sqlite3.Connection(":memory:")
    _create_v1_database(conn)
    return conn


# ---------------------------------------------------------------------------
# _SCHEMA_VERSION constant
# ---------------------------------------------------------------------------


class TestSchemaVersionConstant:
    """_SCHEMA_VERSION must be at least 2 (v2 baseline)."""

    def test_schema_version_is_at_least_2(self) -> None:
        assert _SCHEMA_VERSION >= 2


# ---------------------------------------------------------------------------
# Fresh init creates v2 schema
# ---------------------------------------------------------------------------


class TestFreshV2Init:
    """init_db on a blank database creates all v2 tables directly."""

    def test_chunks_table_exists(self, fresh_db: sqlite3.Connection) -> None:
        assert _table_exists(fresh_db, "chunks")

    def test_document_status_table_exists(self, fresh_db: sqlite3.Connection) -> None:
        assert _table_exists(fresh_db, "document_status")

    def test_schema_version_is_current(self, fresh_db: sqlite3.Connection) -> None:
        row = fresh_db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == _SCHEMA_VERSION

    def test_v1_tables_still_present(self, fresh_db: sqlite3.Connection) -> None:
        for table in ("documents", "entities", "edges"):
            assert _table_exists(fresh_db, table), f"Missing table: {table}"


# ---------------------------------------------------------------------------
# chunks table columns
# ---------------------------------------------------------------------------


class TestChunksTableColumns:
    """The chunks table has the correct columns, PK, and FK."""

    def test_has_id(self, fresh_db: sqlite3.Connection) -> None:
        assert "id" in _column_names(fresh_db, "chunks")

    def test_has_document_id(self, fresh_db: sqlite3.Connection) -> None:
        assert "document_id" in _column_names(fresh_db, "chunks")

    def test_has_chunk_index(self, fresh_db: sqlite3.Connection) -> None:
        assert "chunk_index" in _column_names(fresh_db, "chunks")

    def test_has_content(self, fresh_db: sqlite3.Connection) -> None:
        assert "content" in _column_names(fresh_db, "chunks")

    def test_has_metadata(self, fresh_db: sqlite3.Connection) -> None:
        assert "metadata" in _column_names(fresh_db, "chunks")

    def test_has_created_at(self, fresh_db: sqlite3.Connection) -> None:
        assert "created_at" in _column_names(fresh_db, "chunks")

    def test_id_is_primary_key(self, fresh_db: sqlite3.Connection) -> None:
        assert "id" in _pk_columns(fresh_db, "chunks")

    def test_document_id_fk_to_documents(self, fresh_db: sqlite3.Connection) -> None:
        fks = _foreign_keys(fresh_db, "chunks")
        doc_fk = [fk for fk in fks if fk["from"] == "document_id"]
        assert len(doc_fk) == 1
        assert doc_fk[0]["table"] == "documents"
        assert doc_fk[0]["to"] == "id"


# ---------------------------------------------------------------------------
# document_status table columns
# ---------------------------------------------------------------------------


class TestDocumentStatusTableColumns:
    """The document_status table has the correct columns and PK."""

    def test_has_document_id(self, fresh_db: sqlite3.Connection) -> None:
        assert "document_id" in _column_names(fresh_db, "document_status")

    def test_has_status(self, fresh_db: sqlite3.Connection) -> None:
        assert "status" in _column_names(fresh_db, "document_status")

    def test_has_source(self, fresh_db: sqlite3.Connection) -> None:
        assert "source" in _column_names(fresh_db, "document_status")

    def test_has_error(self, fresh_db: sqlite3.Connection) -> None:
        assert "error" in _column_names(fresh_db, "document_status")

    def test_has_created_at(self, fresh_db: sqlite3.Connection) -> None:
        assert "created_at" in _column_names(fresh_db, "document_status")

    def test_has_updated_at(self, fresh_db: sqlite3.Connection) -> None:
        assert "updated_at" in _column_names(fresh_db, "document_status")

    def test_document_id_is_primary_key(self, fresh_db: sqlite3.Connection) -> None:
        assert "document_id" in _pk_columns(fresh_db, "document_status")


# ---------------------------------------------------------------------------
# v1 → v2 migration
# ---------------------------------------------------------------------------


class TestV1ToV2Migration:
    """Calling init_db on a v1 database migrates it to v2."""

    def test_v1_has_no_chunks_table(self, v1_db: sqlite3.Connection) -> None:
        """Precondition: v1 database lacks the chunks table."""
        assert not _table_exists(v1_db, "chunks")

    def test_v1_has_no_document_status_table(self, v1_db: sqlite3.Connection) -> None:
        """Precondition: v1 database lacks the document_status table."""
        assert not _table_exists(v1_db, "document_status")

    def test_migration_creates_chunks_table(self, v1_db: sqlite3.Connection) -> None:
        init_db(v1_db)
        assert _table_exists(v1_db, "chunks")

    def test_migration_creates_document_status_table(self, v1_db: sqlite3.Connection) -> None:
        init_db(v1_db)
        assert _table_exists(v1_db, "document_status")

    def test_migration_updates_version(self, v1_db: sqlite3.Connection) -> None:
        row = v1_db.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] == 1
        init_db(v1_db)
        row = v1_db.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] == _SCHEMA_VERSION

    def test_existing_v1_data_preserved(self, v1_db: sqlite3.Connection) -> None:
        """V1 data in documents, entities, edges survives migration."""
        v1_db.execute(
            "INSERT INTO documents (id, title, content) VALUES ('d1', 'Doc 1', 'hello world')"
        )
        v1_db.execute(
            "INSERT INTO entities (id, name, entity_type) VALUES ('e1', 'Entity 1', 'concept')"
        )
        v1_db.execute(
            "INSERT INTO edges (id, source_id, target_id, relation) "
            "VALUES ('eg1', 'e1', 'e1', 'self')"
        )
        v1_db.commit()

        init_db(v1_db)

        assert v1_db.execute("SELECT id FROM documents WHERE id='d1'").fetchone() is not None
        assert v1_db.execute("SELECT id FROM entities WHERE id='e1'").fetchone() is not None
        assert v1_db.execute("SELECT id FROM edges WHERE id='eg1'").fetchone() is not None


# ---------------------------------------------------------------------------
# Double-migration idempotency
# ---------------------------------------------------------------------------


class TestMigrationIdempotency:
    """Running migration twice must not raise or corrupt data."""

    def test_double_migration_is_safe(self, v1_db: sqlite3.Connection) -> None:
        init_db(v1_db)
        init_db(v1_db)  # must not raise

    def test_double_migration_version_is_current(self, v1_db: sqlite3.Connection) -> None:
        init_db(v1_db)
        init_db(v1_db)
        row = v1_db.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] == _SCHEMA_VERSION

    def test_double_migration_single_version_row(self, v1_db: sqlite3.Connection) -> None:
        init_db(v1_db)
        init_db(v1_db)
        count = v1_db.execute("SELECT count(*) FROM schema_version").fetchone()[0]
        assert count == 1

    def test_double_fresh_init_is_safe(self) -> None:
        conn = sqlite3.Connection(":memory:")
        init_db(conn)
        init_db(conn)  # must not raise
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] == _SCHEMA_VERSION
