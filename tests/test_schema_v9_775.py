"""RED-phase tests for schema v9 migration path (#780, parent #775).

Tests the v8→v9 migration path specifically — unique coverage not provided
by the fresh-init tests in #754 and #757.

AC mapping:
  AC1  - Migration runs without error on a v8 baseline database
  AC2  - source_pages table has all required columns after migration
         (also verifies idx_source_pages_scope index)
  AC3  - documents gains source_id column; legacy rows have NULL
  AC4  - schema_version reports version = 9 after migration

Note: The _migrate_v8_to_v9() implementation pre-exists this test task.
      All AC-derived migration-path tests pass (regression coverage).
      idx_source_pages_scope passes because #785 landed source_pages in _SCOPE_TABLES.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from owlbear_knowledge.schema import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_v8_db() -> sqlite3.Connection:
    """Build an in-memory SQLite database at schema version 8.

    Represents the state just before the v9 migration: documents table
    without source_id, schema_version=8, no source_pages table.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "CREATE TABLE documents ("
        "id         TEXT PRIMARY KEY, "
        "title      TEXT, "
        "content    TEXT, "
        "metadata   TEXT, "
        "created_at TEXT, "
        "scope      TEXT DEFAULT 'global'"
        ")"
    )
    conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (8, ?)",
        (_now(),),
    )
    conn.commit()
    return conn


# ===========================================================================
# AC 1 — v8→v9 migration runs without error
# ===========================================================================


class TestFromAC_V8ToV9MigrationRuns:
    """AC1: init_db on a v8 database completes without error and preserves data."""

    def test_migration_runs_without_error(self) -> None:
        """init_db on a v8 database raises no exception."""
        conn = _make_v8_db()
        init_db(conn)  # must not raise

    def test_migration_preserves_existing_document_rows(self) -> None:
        """Document rows inserted before migration are intact after migration."""
        conn = _make_v8_db()
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
            ("legacy-doc-1", "Legacy Doc", "body text", "{}", _now(), "global"),
        )
        conn.commit()
        init_db(conn)
        row = conn.execute("SELECT id, title FROM documents WHERE id='legacy-doc-1'").fetchone()
        assert row is not None
        assert row[0] == "legacy-doc-1"
        assert row[1] == "Legacy Doc"

    def test_migration_does_not_duplicate_schema_version_rows(self) -> None:
        """Migration updates the schema_version row; it does not insert a new one."""
        conn = _make_v8_db()
        init_db(conn)
        count = conn.execute("SELECT count(*) FROM schema_version").fetchone()[0]
        assert count == 1


# ===========================================================================
# AC 2 — source_pages table with all required columns after migration
# ===========================================================================


class TestFromAC_SourcePagesAfterMigration:
    """AC2: source_pages table exists with all required columns and indexes after migration."""

    def test_source_pages_table_exists_after_migration(self) -> None:
        """source_pages table is present after v8→v9 migration."""
        conn = _make_v8_db()
        init_db(conn)
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_pages'").fetchone()
        assert row is not None

    @pytest.mark.parametrize(
        "column",
        [
            "id",
            "source_id",
            "url",
            "status",
            "extraction_hash",
            "last_extracted",
            "scope",
            "created_at",
            "updated_at",
        ],
    )
    def test_source_pages_has_column(self, column: str) -> None:
        """source_pages table has every required column after v8→v9 migration."""
        conn = _make_v8_db()
        init_db(conn)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(source_pages)").fetchall()}
        assert column in cols

    def test_source_pages_source_id_index_exists_after_migration(self) -> None:
        """idx_source_pages_source_id index is created by _migrate_v8_to_v9."""
        conn = _make_v8_db()
        init_db(conn)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_source_pages_source_id'"
        ).fetchone()
        assert row is not None

    def test_source_pages_scope_index_exists_after_migration(self) -> None:
        """idx_source_pages_scope exists after migration (source_pages in _SCOPE_TABLES since #785)."""
        conn = _make_v8_db()
        init_db(conn)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_source_pages_scope'"
        ).fetchone()
        assert row is not None


# ===========================================================================
# AC 3 — documents.source_id is nullable; legacy rows have NULL
# ===========================================================================


class TestFromAC_DocumentsSourceIdAfterMigration:
    """AC3: documents gains a nullable source_id column; legacy rows have NULL."""

    def test_documents_has_source_id_column_after_migration(self) -> None:
        """documents table has source_id column after v8→v9 migration."""
        conn = _make_v8_db()
        init_db(conn)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
        assert "source_id" in cols

    def test_legacy_document_source_id_is_null_after_migration(self) -> None:
        """Document inserted before migration has source_id = NULL after migration."""
        conn = _make_v8_db()
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
            ("legacy-2", "Legacy Pre-V9", "text", "{}", _now(), "global"),
        )
        conn.commit()
        init_db(conn)
        row = conn.execute("SELECT source_id FROM documents WHERE id='legacy-2'").fetchone()
        assert row is not None
        assert row[0] is None

    def test_documents_source_id_column_is_nullable(self) -> None:
        """PRAGMA table_info reports source_id as nullable (notnull=0) after migration."""
        conn = _make_v8_db()
        init_db(conn)
        col_info = next(
            (row for row in conn.execute("PRAGMA table_info(documents)").fetchall() if row[1] == "source_id"),
            None,
        )
        assert col_info is not None
        assert col_info[3] == 0  # notnull == 0 → nullable  # noqa: PLR2004


# ===========================================================================
# AC 4 — schema_version is 9 after migration
# ===========================================================================


class TestFromAC_SchemaVersion9AfterMigration:
    """AC4: querying schema_version returns version=9 after v8→v9 migration."""

    def test_schema_version_is_9_after_v8_migration(self) -> None:
        """SELECT version FROM schema_version returns 9 after migrating from v8."""
        conn = _make_v8_db()
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 9  # noqa: PLR2004

    def test_schema_version_applied_at_is_updated_after_migration(self) -> None:
        """applied_at is updated to a valid ISO timestamp by the v8→v9 migration."""
        conn = _make_v8_db()
        init_db(conn)
        row = conn.execute("SELECT applied_at FROM schema_version").fetchone()
        assert row is not None
        assert row[0] is not None
        datetime.fromisoformat(row[0])  # raises ValueError if not a valid ISO string

    def test_schema_version_is_not_lower_than_9_after_migration(self) -> None:
        """schema_version is not below 9 after running init_db on a v8 database."""
        conn = _make_v8_db()
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] >= 9  # noqa: PLR2004
