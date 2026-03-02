"""Tests for knowledge-graph schema v3 migration — scope columns.

Covers: fresh init with scope columns, v2→v3 migration, idempotency,
data preservation with default 'global' scope, index creation, and
model scope fields on Entity/Edge/Document.

NOTE: _SCHEMA_VERSION is now 4 (v4 added document_id columns in #251/#278).
The v3 migration behaviour is still tested; the constant reflects the latest.

Task #220 — Test knowledge schema v3
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear.memory.knowledge.models import Document, Edge, Entity, EntityType, RelationType
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


def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    """Check whether *index_name* exists in sqlite_master."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='index' AND name = ?",
        (index_name,),
    ).fetchone()
    return bool(row and row[0])


def _create_v2_database(conn: sqlite3.Connection) -> None:
    """Set up a v2 schema manually — no scope columns."""
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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunks ("
        "id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id), "
        "chunk_index INTEGER, content TEXT, metadata TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS document_status ("
        "document_id TEXT PRIMARY KEY, status TEXT, source TEXT, "
        "error TEXT, created_at TEXT, updated_at TEXT)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER, applied_at TEXT)")
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (2, '2026-01-15T00:00:00+00:00')"
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_db() -> sqlite3.Connection:
    """In-memory connection with a fresh init_db (v3)."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    return conn


@pytest.fixture
def v2_db() -> sqlite3.Connection:
    """In-memory connection with v2 schema (pre-migration)."""
    conn = sqlite3.Connection(":memory:")
    _create_v2_database(conn)
    return conn


# ---------------------------------------------------------------------------
# _SCHEMA_VERSION constant
# ---------------------------------------------------------------------------


class TestSchemaVersionConstant:
    """_SCHEMA_VERSION must reflect the latest schema (v5 after #371)."""

    def test_schema_version_is_current(self) -> None:
        assert _SCHEMA_VERSION >= 4


# ---------------------------------------------------------------------------
# Fresh init creates v3 schema with scope columns in all 5 tables
# ---------------------------------------------------------------------------

_SCOPE_TABLES = ("entities", "documents", "edges", "chunks", "document_status")


class TestFreshV3Init:
    """init_db on a blank database creates all tables with scope columns."""

    @pytest.mark.parametrize("table", _SCOPE_TABLES)
    def test_scope_column_exists(self, fresh_db: sqlite3.Connection, table: str) -> None:
        assert "scope" in _column_names(fresh_db, table)

    def test_schema_version_is_current(self, fresh_db: sqlite3.Connection) -> None:
        row = fresh_db.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] >= 4

    def test_all_v2_tables_still_present(self, fresh_db: sqlite3.Connection) -> None:
        for table in (
            "documents",
            "entities",
            "edges",
            "chunks",
            "document_status",
        ):
            assert _table_exists(fresh_db, table), f"Missing table: {table}"


# ---------------------------------------------------------------------------
# v2 → v3 migration adds scope columns (idempotent)
# ---------------------------------------------------------------------------


class TestV2ToV3Migration:
    """Calling init_db on a v2 database migrates it to v3."""

    @pytest.mark.parametrize("table", _SCOPE_TABLES)
    def test_v2_has_no_scope_column(self, v2_db: sqlite3.Connection, table: str) -> None:
        """Precondition: v2 database lacks scope columns."""
        assert "scope" not in _column_names(v2_db, table)

    @pytest.mark.parametrize("table", _SCOPE_TABLES)
    def test_migration_adds_scope_column(self, v2_db: sqlite3.Connection, table: str) -> None:
        init_db(v2_db)
        assert "scope" in _column_names(v2_db, table)

    def test_migration_updates_version_to_current(self, v2_db: sqlite3.Connection) -> None:
        row = v2_db.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] == 2
        init_db(v2_db)
        row = v2_db.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] >= 4


# ---------------------------------------------------------------------------
# Existing data preserved with default 'global' scope
# ---------------------------------------------------------------------------


class TestDataPreservation:
    """Existing v2 data survives migration and gets default 'global' scope."""

    def test_existing_data_preserved(self, v2_db: sqlite3.Connection) -> None:
        v2_db.execute("INSERT INTO documents (id, title, content) VALUES ('d1', 'Doc 1', 'hello')")
        v2_db.execute(
            "INSERT INTO entities (id, name, entity_type) VALUES ('e1', 'Entity 1', 'concept')"
        )
        v2_db.execute(
            "INSERT INTO edges (id, source_id, target_id, relation) "
            "VALUES ('eg1', 'e1', 'e1', 'self')"
        )
        v2_db.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content) "
            "VALUES ('c1', 'd1', 0, 'chunk-text')"
        )
        v2_db.commit()

        init_db(v2_db)

        assert v2_db.execute("SELECT id FROM documents WHERE id='d1'").fetchone() is not None
        assert v2_db.execute("SELECT id FROM entities WHERE id='e1'").fetchone() is not None
        assert v2_db.execute("SELECT id FROM edges WHERE id='eg1'").fetchone() is not None
        assert v2_db.execute("SELECT id FROM chunks WHERE id='c1'").fetchone() is not None

    def test_scope_defaults_to_global(self, v2_db: sqlite3.Connection) -> None:
        v2_db.execute("INSERT INTO documents (id, title, content) VALUES ('d1', 'Doc', 'text')")
        v2_db.execute(
            "INSERT INTO entities (id, name, entity_type) VALUES ('e1', 'Ent', 'concept')"
        )
        v2_db.execute(
            "INSERT INTO edges (id, source_id, target_id, relation) "
            "VALUES ('eg1', 'e1', 'e1', 'self')"
        )
        v2_db.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content) "
            "VALUES ('c1', 'd1', 0, 'chunk')"
        )
        v2_db.commit()

        init_db(v2_db)

        for table in ("documents", "entities", "edges", "chunks"):
            row = v2_db.execute(f"SELECT scope FROM {table}").fetchone()  # noqa: S608
            assert row[0] == "global", f"Expected 'global' scope in {table}, got {row[0]}"


# ---------------------------------------------------------------------------
# Double-migration idempotency
# ---------------------------------------------------------------------------


class TestV3MigrationIdempotency:
    """Running v2→v3 migration twice must not raise or corrupt data."""

    def test_double_migration_is_safe(self, v2_db: sqlite3.Connection) -> None:
        init_db(v2_db)
        init_db(v2_db)  # must not raise

    def test_double_migration_version_still_current(self, v2_db: sqlite3.Connection) -> None:
        init_db(v2_db)
        init_db(v2_db)
        row = v2_db.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] >= 4

    def test_double_migration_single_version_row(self, v2_db: sqlite3.Connection) -> None:
        init_db(v2_db)
        init_db(v2_db)
        count = v2_db.execute("SELECT count(*) FROM schema_version").fetchone()[0]
        assert count == 1

    def test_double_fresh_init_is_safe(self) -> None:
        conn = sqlite3.Connection(":memory:")
        init_db(conn)
        init_db(conn)  # must not raise
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row[0] >= 4


# ---------------------------------------------------------------------------
# Index creation on scope columns
# ---------------------------------------------------------------------------


class TestScopeIndexes:
    """CREATE INDEX IF NOT EXISTS creates indexes on scope columns."""

    @pytest.mark.parametrize("table", _SCOPE_TABLES)
    def test_scope_index_exists_fresh(self, fresh_db: sqlite3.Connection, table: str) -> None:
        assert _index_exists(fresh_db, f"idx_{table}_scope")

    @pytest.mark.parametrize("table", _SCOPE_TABLES)
    def test_migration_creates_scope_index(self, v2_db: sqlite3.Connection, table: str) -> None:
        init_db(v2_db)
        assert _index_exists(v2_db, f"idx_{table}_scope")


# ---------------------------------------------------------------------------
# Model scope fields
# ---------------------------------------------------------------------------


class TestModelScopeFields:
    """Entity, Edge, Document models have scope: str = 'global'."""

    def test_entity_has_scope_default_global(self) -> None:
        e = Entity(name="test", entity_type=EntityType.CONCEPT)
        assert e.scope == "global"

    def test_entity_accepts_custom_scope(self) -> None:
        e = Entity(name="test", entity_type=EntityType.CONCEPT, scope="project:owlbear")
        assert e.scope == "project:owlbear"

    def test_edge_has_scope_default_global(self) -> None:
        e = Edge(source_id="a", target_id="b", relation=RelationType.RELATED_TO)
        assert e.scope == "global"

    def test_edge_accepts_custom_scope(self) -> None:
        e = Edge(
            source_id="a",
            target_id="b",
            relation=RelationType.RELATED_TO,
            scope="agent:builder",
        )
        assert e.scope == "agent:builder"

    def test_document_has_scope_default_global(self) -> None:
        d = Document(title="t", content="c")
        assert d.scope == "global"

    def test_document_accepts_custom_scope(self) -> None:
        d = Document(title="t", content="c", scope="project:owlbear")
        assert d.scope == "project:owlbear"


# ---------------------------------------------------------------------------
# Model serialization includes scope
# ---------------------------------------------------------------------------


class TestModelSerialization:
    """model_dump output includes scope field."""

    def test_entity_dump_includes_scope(self) -> None:
        e = Entity(name="n", entity_type=EntityType.CONCEPT)
        data = e.model_dump()
        assert "scope" in data
        assert data["scope"] == "global"

    def test_edge_dump_includes_scope(self) -> None:
        e = Edge(source_id="a", target_id="b", relation=RelationType.RELATED_TO)
        data = e.model_dump()
        assert "scope" in data
        assert data["scope"] == "global"

    def test_document_dump_includes_scope(self) -> None:
        d = Document(title="t", content="c")
        data = d.model_dump()
        assert "scope" in data
        assert data["scope"] == "global"
