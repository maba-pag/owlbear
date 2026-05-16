"""Smoke tests for task #1583 — drop bookmarks/consolidations from schema.

One test per AC line. Proof bundle: smoke.
All tests must FAIL against current code (pre-builder).
"""

from __future__ import annotations

import sqlite3

import owlbear_knowledge.schema as schema_mod
from owlbear_knowledge.schema import _migrate_v11_to_v12, init_db


class TestFromAC_SchemaBookmarkConsolidationDrop:
    """AC coverage for #1583 — schema cleanup of bookmarks and consolidations."""

    # AC-1: _CREATE_BOOKMARKS and _CREATE_CONSOLIDATIONS DDL constants deleted
    def test_ac1_ddl_constants_removed(self) -> None:
        assert not hasattr(schema_mod, "_CREATE_BOOKMARKS"), (
            "_CREATE_BOOKMARKS DDL constant must be deleted from schema.py"
        )
        assert not hasattr(schema_mod, "_CREATE_CONSOLIDATIONS"), (
            "_CREATE_CONSOLIDATIONS DDL constant must be deleted from schema.py"
        )

    # AC-2: init_db no longer creates bookmark indexes
    def test_ac2_init_db_no_bookmark_indexes(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            init_db(conn)
            index_names = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
            }
            assert "idx_bookmarks_url_scope" not in index_names, (
                "idx_bookmarks_url_scope must not be created by init_db"
            )
            assert "idx_bookmarks_scope" not in index_names, "idx_bookmarks_scope must not be created by init_db"
        finally:
            conn.close()

    # AC-3: _migrate_v11_to_v12 executes DROP TABLE for both tables and is registered
    def test_ac3_migration_v11_to_v12_drops_tables(self) -> None:
        assert hasattr(schema_mod, "_migrate_v11_to_v12"), "_migrate_v11_to_v12 must exist in schema module"
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE TABLE bookmarks (id TEXT PRIMARY KEY)")
            conn.execute("CREATE TABLE consolidations (id TEXT PRIMARY KEY)")
            conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
            conn.execute("INSERT INTO schema_version VALUES (11, '2024-01-01')")
            schema_mod._migrate_v11_to_v12(conn)
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "bookmarks" not in tables, "bookmarks must be dropped by v12 migration"
            assert "consolidations" not in tables, "consolidations must be dropped by v12 migration"
        finally:
            conn.close()

    # AC-4: _SCHEMA_VERSION is at least 12 (later tasks own higher versions)
    def test_ac4_schema_version_at_least_12(self) -> None:
        assert schema_mod._SCHEMA_VERSION >= 12, (
            f"_SCHEMA_VERSION must be at least 12, got {schema_mod._SCHEMA_VERSION}"
        )

    # AC-5: Module docstring no longer references bookmarks or consolidations
    def test_ac5_docstring_excludes_retired_tables(self) -> None:
        doc = (schema_mod.__doc__ or "").lower()
        assert "bookmarks" not in doc, "Module docstring must not mention bookmarks"
        assert "consolidations" not in doc, "Module docstring must not mention consolidations"

    # AC-6: Fresh DB — init_db creates no bookmarks or consolidations table
    def test_ac6_fresh_db_no_retired_tables(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            init_db(conn)
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "bookmarks" not in tables, "init_db must not create bookmarks table in fresh database"
            assert "consolidations" not in tables, "init_db must not create consolidations table in fresh database"
        finally:
            conn.close()

    # AC-7: v11 DB with both tables — _migrate_v11_to_v12 directly drops both and bumps version to 12
    def test_ac7_migration_from_v11_drops_retired_tables(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            # Simulate a v11 database that has both retired tables
            conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
            conn.execute("INSERT INTO schema_version VALUES (11, '2024-01-01T00:00:00')")
            conn.execute(
                "CREATE TABLE bookmarks ("
                "id TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL,"
                " created_at TEXT NOT NULL, updated_at TEXT NOT NULL"
                ")"
            )
            conn.execute("CREATE TABLE consolidations (id TEXT PRIMARY KEY, source_ids TEXT NOT NULL)")
            _migrate_v11_to_v12(conn)
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "bookmarks" not in tables, "_migrate_v11_to_v12 must drop the bookmarks table"
            assert "consolidations" not in tables, "_migrate_v11_to_v12 must drop the consolidations table"
            ver = conn.execute("SELECT version FROM schema_version").fetchone()
            assert ver is not None, "schema_version must not be empty after _migrate_v11_to_v12"
            assert ver[0] == 12, f"_migrate_v11_to_v12 must advance schema_version to 12, got {ver[0]}"
        finally:
            conn.close()
