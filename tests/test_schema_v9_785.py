"""RED-phase tests for Schema v9 — fresh-init path and column contracts (#785).

AC mapping (revised AC from #785 architecture review):
  AC1  - schema.py SCHEMA_VERSION = 9
  AC2  - _migrate_v8_to_v9() creates source_pages table with correct columns and
         defaults (url NOT NULL, source_id nullable, status DEFAULT 'discovered',
         scope DEFAULT 'global')
  AC3  - _migrate_v8_to_v9() adds source_id TEXT to documents (NULL default)
  AC4  - _migrate_v8_to_v9() creates idx_source_pages_source_id
  AC5  - _SCOPE_TABLES includes source_pages

test_schema_v9_775.py (#780) covers the migration path for AC1-AC5.
This file covers the *fresh-init path* (complementary coverage) plus column
constraint contracts not asserted by #780.

Failing test: test_fresh_init_creates_idx_source_pages_source_id
  idx_source_pages_source_id is created only in _migrate_v8_to_v9(); init_db
  has no explicit CREATE INDEX for it on the fresh-init path.  A fresh
  installation will be missing this index.
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear_knowledge import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_db() -> sqlite3.Connection:
    """Return a fully initialised in-memory database via fresh init_db."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _index_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    return {row[0] for row in rows}


# ===========================================================================
# AC1 — SCHEMA_VERSION = 9 (fresh-init path)
# ===========================================================================


class TestFromAC_SchemaV9FreshInit:  # noqa: N801
    """Fresh init_db stores version 9 and creates a consistent v9 schema."""

    def test_fresh_init_schema_version_table_records_9(self) -> None:
        """schema_version table records version=9 immediately after fresh init_db."""
        conn = _fresh_db()
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 9  # noqa: PLR2004

    # ===========================================================================
    # AC2 — source_pages table columns and constraints (fresh-init path)
    # ===========================================================================

    def test_fresh_init_source_pages_table_exists(self) -> None:
        """source_pages table is present after fresh init_db."""
        conn = _fresh_db()
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_pages'").fetchone()
        assert row is not None

    def test_fresh_init_source_pages_url_is_not_null(self) -> None:
        """url column is NOT NULL — inserting a row without url raises IntegrityError."""
        conn = _fresh_db()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO source_pages (id, source_id, status, scope) VALUES (?, ?, ?, ?)",
                ("sp-1", None, "discovered", "global"),
            )

    def test_fresh_init_source_pages_source_id_nullable(self) -> None:
        """source_id column is nullable — inserting NULL source_id must not raise."""
        conn = _fresh_db()
        conn.execute(
            "INSERT INTO source_pages (id, url, status, scope) VALUES (?, ?, ?, ?)",
            ("sp-2", "https://example.com", "discovered", "global"),
        )
        conn.commit()
        row = conn.execute("SELECT source_id FROM source_pages WHERE id='sp-2'").fetchone()
        assert row is not None
        assert row[0] is None

    def test_fresh_init_source_pages_status_defaults_to_discovered(self) -> None:
        """status column defaults to 'discovered' when omitted on insert."""
        conn = _fresh_db()
        conn.execute(
            "INSERT INTO source_pages (id, url, scope) VALUES (?, ?, ?)",
            ("sp-3", "https://example.com", "global"),
        )
        conn.commit()
        row = conn.execute("SELECT status FROM source_pages WHERE id='sp-3'").fetchone()
        assert row is not None
        assert row[0] == "discovered"

    def test_fresh_init_source_pages_scope_defaults_to_global(self) -> None:
        """scope column defaults to 'global' when omitted on insert."""
        conn = _fresh_db()
        conn.execute(
            "INSERT INTO source_pages (id, url, status) VALUES (?, ?, ?)",
            ("sp-4", "https://example.com", "discovered"),
        )
        conn.commit()
        row = conn.execute("SELECT scope FROM source_pages WHERE id='sp-4'").fetchone()
        assert row is not None
        assert row[0] == "global"

    # ===========================================================================
    # AC3 — documents.source_id present on fresh-init path
    # ===========================================================================

    def test_fresh_init_documents_has_source_id_column(self) -> None:
        """documents table has source_id column after fresh init_db."""
        conn = _fresh_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
        assert "source_id" in cols

    # ===========================================================================
    # AC4 — idx_source_pages_source_id on fresh-init path  [FAILS]
    # ===========================================================================

    def test_fresh_init_creates_idx_source_pages_source_id(self) -> None:
        """idx_source_pages_source_id must exist after fresh init_db.

        FAILS: the index is created only in _migrate_v8_to_v9(); init_db does
        not create it on the fresh-init path, leaving new installations without
        this index.
        """
        conn = _fresh_db()
        assert "idx_source_pages_source_id" in _index_names(conn)

    # ===========================================================================
    # AC5 — _SCOPE_TABLES includes source_pages (fresh-init path)
    # ===========================================================================

    def test_fresh_init_creates_idx_source_pages_scope(self) -> None:
        """idx_source_pages_scope is created by init_db scope-index loop (fresh init)."""
        conn = _fresh_db()
        assert "idx_source_pages_scope" in _index_names(conn)

    def test_fresh_init_idx_source_pages_scope_bound_to_source_pages(self) -> None:
        """idx_source_pages_scope is bound to the source_pages table."""
        conn = _fresh_db()
        row = conn.execute(
            "SELECT tbl_name FROM sqlite_master WHERE type='index' AND name='idx_source_pages_scope'"
        ).fetchone()
        assert row is not None, "idx_source_pages_scope index missing"
        assert row[0] == "source_pages"
        assert row[0] == "source_pages"
