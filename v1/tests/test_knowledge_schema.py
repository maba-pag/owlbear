"""Tests for owlbear.memory.knowledge.schema — DDL and init_db.

TDD red-phase: these tests define the contract for task #107.
All imports from owlbear.memory.knowledge.schema will fail until
that module is implemented.
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _table_columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    """Return {column_name: column_type} for a regular table via PRAGMA."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    # PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
    return {row[1]: row[2] for row in rows}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check whether *table* exists in sqlite_master."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
        (table,),
    ).fetchone()
    return bool(row and row[0])


def _foreign_keys(conn: sqlite3.Connection, table: str) -> list[dict[str, str]]:
    """Return foreign key definitions for *table*."""
    rows = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    # (id, seq, table, from, to, on_update, on_delete, match)
    return [{"from": r[3], "table": r[2], "to": r[4]} for r in rows]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> sqlite3.Connection:
    """In-memory SQLite connection with init_db applied."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    return conn


# ---------------------------------------------------------------------------
# EMBEDDING_DIM constant removed (was 384, now handled by Qdrant)
# ---------------------------------------------------------------------------


class TestEmbeddingDimRemoved:
    """EMBEDDING_DIM constant no longer exists in schema module."""

    def test_embedding_dim_not_in_schema(self) -> None:
        from owlbear.memory.knowledge import schema

        assert not hasattr(schema, "EMBEDDING_DIM")


# ---------------------------------------------------------------------------
# documents table
# ---------------------------------------------------------------------------


class TestDocumentsTable:
    """init_db creates the documents table with expected columns."""

    def test_documents_table_exists(self, db: sqlite3.Connection) -> None:
        assert _table_exists(db, "documents")

    def test_documents_columns(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "documents")
        assert "id" in cols
        assert "title" in cols
        assert "content" in cols
        assert "metadata" in cols

    def test_documents_id_is_primary_key(self, db: sqlite3.Connection) -> None:
        rows = db.execute("PRAGMA table_info(documents)").fetchall()
        pk_cols = [r[1] for r in rows if r[5]]  # r[5] = pk flag
        assert "id" in pk_cols


# ---------------------------------------------------------------------------
# entities table
# ---------------------------------------------------------------------------


class TestEntitiesTable:
    """init_db creates the entities table with expected columns."""

    def test_entities_table_exists(self, db: sqlite3.Connection) -> None:
        assert _table_exists(db, "entities")

    def test_entities_columns(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "entities")
        assert "id" in cols
        assert "name" in cols
        assert "entity_type" in cols
        assert "description" in cols
        assert "metadata" in cols

    def test_entities_id_is_primary_key(self, db: sqlite3.Connection) -> None:
        rows = db.execute("PRAGMA table_info(entities)").fetchall()
        pk_cols = [r[1] for r in rows if r[5]]
        assert "id" in pk_cols


# ---------------------------------------------------------------------------
# edges table
# ---------------------------------------------------------------------------


class TestEdgesTable:
    """init_db creates the edges table with expected columns and FKs."""

    def test_edges_table_exists(self, db: sqlite3.Connection) -> None:
        assert _table_exists(db, "edges")

    def test_edges_columns(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "edges")
        assert "id" in cols
        assert "source_id" in cols
        assert "target_id" in cols
        assert "relation" in cols
        assert "weight" in cols
        assert "metadata" in cols

    def test_edges_id_is_primary_key(self, db: sqlite3.Connection) -> None:
        rows = db.execute("PRAGMA table_info(edges)").fetchall()
        pk_cols = [r[1] for r in rows if r[5]]
        assert "id" in pk_cols

    def test_edges_foreign_key_source(self, db: sqlite3.Connection) -> None:
        fks = _foreign_keys(db, "edges")
        source_fk = [fk for fk in fks if fk["from"] == "source_id"]
        assert len(source_fk) == 1
        assert source_fk[0]["table"] == "entities"
        assert source_fk[0]["to"] == "id"

    def test_edges_foreign_key_target(self, db: sqlite3.Connection) -> None:
        fks = _foreign_keys(db, "edges")
        target_fk = [fk for fk in fks if fk["from"] == "target_id"]
        assert len(target_fk) == 1
        assert target_fk[0]["table"] == "entities"
        assert target_fk[0]["to"] == "id"


# ---------------------------------------------------------------------------
# vec0 virtual tables removed (vector storage now in Qdrant)
# ---------------------------------------------------------------------------


class TestVec0TablesRemoved:
    """sqlite-vec virtual tables are no longer created by init_db."""

    def test_entity_embeddings_not_created(self, db: sqlite3.Connection) -> None:
        """entity_embeddings vec0 table must NOT exist."""
        assert not _table_exists(db, "entity_embeddings")

    def test_document_embeddings_not_created(self, db: sqlite3.Connection) -> None:
        """document_embeddings vec0 table must NOT exist."""
        assert not _table_exists(db, "document_embeddings")


# ---------------------------------------------------------------------------
# embedding_rowid_map bridge table removed
# ---------------------------------------------------------------------------


class TestEmbeddingRowidMapRemoved:
    """embedding_rowid_map bridge table is no longer created by init_db."""

    def test_embedding_rowid_map_not_created(self, db: sqlite3.Connection) -> None:
        """embedding_rowid_map table must NOT exist."""
        assert not _table_exists(db, "embedding_rowid_map")


# ---------------------------------------------------------------------------
# schema_version table
# ---------------------------------------------------------------------------


class TestSchemaVersionTable:
    """init_db creates a schema_version table with a version entry."""

    def test_schema_version_table_exists(self, db: sqlite3.Connection) -> None:
        assert _table_exists(db, "schema_version")

    def test_schema_version_has_entry(self, db: sqlite3.Connection) -> None:
        row = db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert isinstance(row[0], int)
        assert row[0] >= 1


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Calling init_db twice must not raise."""

    def test_init_db_twice_no_error(self) -> None:
        conn = sqlite3.Connection(":memory:")
        init_db(conn)
        init_db(conn)  # should not raise

    def test_init_db_twice_preserves_version(self) -> None:
        conn = sqlite3.Connection(":memory:")
        init_db(conn)
        row_before = conn.execute("SELECT version FROM schema_version").fetchone()
        init_db(conn)
        row_after = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row_before == row_after


# ---------------------------------------------------------------------------
# In-memory SQLite
# ---------------------------------------------------------------------------


class TestInMemoryDb:
    """init_db works with :memory: databases."""

    def test_in_memory_creates_all_tables(self) -> None:
        conn = sqlite3.Connection(":memory:")
        init_db(conn)
        expected = {
            "documents",
            "entities",
            "edges",
            "chunks",
            "document_status",
            "schema_version",
        }
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        ).fetchall()
        actual = {r[0] for r in rows}
        assert expected.issubset(actual), f"Missing tables: {expected - actual}"
        # Verify removed tables are NOT present
        removed = {"entity_embeddings", "document_embeddings", "embedding_rowid_map"}
        assert not removed & actual, f"Removed tables still present: {removed & actual}"


# ---------------------------------------------------------------------------
# Foreign key enforcement
# ---------------------------------------------------------------------------


class TestForeignKeyEnforcement:
    """Foreign keys are enforced — inserting an edge with nonexistent
    source or target entity must raise an IntegrityError."""

    def test_edge_with_nonexistent_source_raises(self, db: sqlite3.Connection) -> None:
        # Insert a valid target entity but no source
        db.execute(
            "INSERT INTO entities (id, name, entity_type) VALUES (?, ?, ?)",
            ("target-1", "target_entity", "file"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO edges (id, source_id, target_id, relation) VALUES (?, ?, ?, ?)",
                ("edge-1", "nonexistent-source", "target-1", "depends_on"),
            )

    def test_edge_with_nonexistent_target_raises(self, db: sqlite3.Connection) -> None:
        db.execute(
            "INSERT INTO entities (id, name, entity_type) VALUES (?, ?, ?)",
            ("source-1", "source_entity", "file"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO edges (id, source_id, target_id, relation) VALUES (?, ?, ?, ?)",
                ("edge-1", "source-1", "nonexistent-target", "depends_on"),
            )

    def test_valid_edge_succeeds(self, db: sqlite3.Connection) -> None:
        db.execute(
            "INSERT INTO entities (id, name, entity_type) VALUES (?, ?, ?)",
            ("src", "source", "file"),
        )
        db.execute(
            "INSERT INTO entities (id, name, entity_type) VALUES (?, ?, ?)",
            ("tgt", "target", "function"),
        )
        db.execute(
            "INSERT INTO edges (id, source_id, target_id, relation) VALUES (?, ?, ?, ?)",
            ("e1", "src", "tgt", "defines"),
        )
        row = db.execute("SELECT id FROM edges WHERE id = 'e1'").fetchone()
        assert row is not None


# ---------------------------------------------------------------------------
# v3 → v4 migration
# ---------------------------------------------------------------------------


def _create_v3_db() -> sqlite3.Connection:
    """Build a v3-schema DB without the v4 columns/indexes."""
    conn = sqlite3.Connection(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    # Core v3 tables (no content_hash on document_status, no document_id on entities)
    conn.execute(
        "CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT, content TEXT, "
        "metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE entities (id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, "
        "description TEXT, metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
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
        "scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE schema_version (version INTEGER, applied_at TEXT)"
    )
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (3, '2026-01-01T00:00:00')"
    )

    # Insert a row in document_status and entities so we can verify NULLs after migration
    conn.execute(
        "INSERT INTO document_status (document_id, status, source) VALUES (?, ?, ?)",
        ("doc-1", "indexed", "/some/path"),
    )
    conn.execute(
        "INSERT INTO entities (id, name, entity_type) VALUES (?, ?, ?)",
        ("ent-1", "MyClass", "class"),
    )
    conn.commit()
    return conn


class TestMigrateV3ToV4:
    """v3 → v4 migration adds content_hash, document_id, and source index."""

    def test_content_hash_column_added_to_document_status(self) -> None:
        conn = _create_v3_db()
        init_db(conn)
        cols = _table_columns(conn, "document_status")
        assert "content_hash" in cols

    def test_document_id_column_added_to_entities(self) -> None:
        conn = _create_v3_db()
        init_db(conn)
        cols = _table_columns(conn, "entities")
        assert "document_id" in cols

    def test_source_index_created(self) -> None:
        conn = _create_v3_db()
        init_db(conn)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' "
            "AND name = 'idx_document_status_source'"
        ).fetchall()
        assert len(rows) == 1

    def test_schema_version_bumped_to_4(self) -> None:
        conn = _create_v3_db()
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] >= 4

    def test_existing_rows_get_null_for_new_columns(self) -> None:
        conn = _create_v3_db()
        init_db(conn)
        # document_status row should have NULL content_hash
        ds_row = conn.execute(
            "SELECT content_hash FROM document_status WHERE document_id = 'doc-1'"
        ).fetchone()
        assert ds_row is not None
        assert ds_row[0] is None

        # entities row should have NULL document_id
        ent_row = conn.execute(
            "SELECT document_id FROM entities WHERE id = 'ent-1'"
        ).fetchone()
        assert ent_row is not None
        assert ent_row[0] is None

    def test_idempotent_rerun(self) -> None:
        """Running init_db twice on a v3 DB must not raise."""
        conn = _create_v3_db()
        init_db(conn)
        init_db(conn)  # second call — must not raise
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] >= 4

    def test_fresh_db_has_v4_columns(self) -> None:
        """A fresh init_db creates tables with v4 columns already present."""
        conn = sqlite3.Connection(":memory:")
        init_db(conn)
        ds_cols = _table_columns(conn, "document_status")
        ent_cols = _table_columns(conn, "entities")
        assert "content_hash" in ds_cols
        assert "document_id" in ent_cols
