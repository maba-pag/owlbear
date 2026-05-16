"""Tests for enrichment schema additions (task #1323).

TDD RED phase — all tests FAIL until task #1324 implements the schema changes.

Covers:
  - AC1: enrichment_state column on chunks table (values: pending, claimed, enriched)
  - AC2: enrichment_state does NOT reuse the consolidated column
  - AC3: claimed_at timestamp column on chunks table for lease tracking
  - AC4: reviewed_pairs table exists with entity_name, source_a, source_b columns
  - AC5: UNIQUE constraint on edges: UNIQUE(source_id, target_id, relation, document_id)
  - AC6: New chunks default to enrichment_state='pending'

Run with: uv run pytest tests/test_enrichment_schema_1323.py
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

import pytest

from owlbear_knowledge.schema import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """In-memory SQLite connection with schema initialized."""
    c = sqlite3.connect(":memory:")
    init_db(c)
    return c


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def _column_info(conn: sqlite3.Connection, table: str) -> dict[str, dict]:
    """Return column metadata keyed by column name."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {
        row[1]: {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": row[3],
            "dflt_value": row[4],
            "pk": row[5],
        }
        for row in rows
    }


def _index_columns(conn: sqlite3.Connection, index_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA index_info({index_name})").fetchall()
    return [row[2] for row in rows]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None and row[0] > 0


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# AC1: enrichment_state column on chunks table
# ---------------------------------------------------------------------------


class TestFromAC_EnrichmentStateColumn:
    """AC1 — chunks table has enrichment_state column."""

    def test_chunks_has_enrichment_state_column(self, conn: sqlite3.Connection) -> None:
        cols = _column_names(conn, "chunks")
        assert "enrichment_state" in cols, "chunks table missing enrichment_state column"

    def test_enrichment_state_is_text_type(self, conn: sqlite3.Connection) -> None:
        info = _column_info(conn, "chunks")
        assert "enrichment_state" in info, "chunks table missing enrichment_state column"
        assert info["enrichment_state"]["type"].upper() == "TEXT", (
            f"enrichment_state should be TEXT, got {info['enrichment_state']['type']}"
        )

    def test_enrichment_state_default_is_pending(self, conn: sqlite3.Connection) -> None:
        info = _column_info(conn, "chunks")
        assert "enrichment_state" in info, "chunks table missing enrichment_state column"
        dflt = info["enrichment_state"]["dflt_value"]
        assert dflt == "'pending'", f"enrichment_state default should be 'pending', got {dflt!r}"


# ---------------------------------------------------------------------------
# AC2: enrichment_state does NOT reuse consolidated column
# ---------------------------------------------------------------------------


class TestFromAC_EnrichmentStateNotConsolidated:
    """AC2 — enrichment_state is a separate column from consolidated."""

    def test_both_columns_coexist_on_chunks(self, conn: sqlite3.Connection) -> None:
        """Both consolidated (legacy) and enrichment_state (new) must exist together."""
        cols = _column_names(conn, "chunks")
        assert "consolidated" in cols, "consolidated column was removed; it must be kept for backwards compat"
        assert "enrichment_state" in cols, (
            "enrichment_state column missing — must coexist with consolidated, not replace it"
        )

    def test_enrichment_state_and_consolidated_are_different_columns(self, conn: sqlite3.Connection) -> None:
        info = _column_info(conn, "chunks")
        assert "enrichment_state" in info, "enrichment_state column missing"
        assert "consolidated" in info, "consolidated column missing"
        assert info["enrichment_state"]["cid"] != info["consolidated"]["cid"], (
            "enrichment_state and consolidated share the same column id — they must be distinct"
        )

    def test_enrichment_state_is_text_not_integer(self, conn: sqlite3.Connection) -> None:
        """consolidated is INTEGER; enrichment_state must be TEXT (different type)."""
        info = _column_info(conn, "chunks")
        assert "enrichment_state" in info, "enrichment_state column missing"
        assert "consolidated" in info, "consolidated column missing"
        assert info["consolidated"]["type"].upper() == "INTEGER", "consolidated should be INTEGER"
        assert info["enrichment_state"]["type"].upper() == "TEXT", (
            "enrichment_state should be TEXT (not INTEGER like consolidated)"
        )


# ---------------------------------------------------------------------------
# AC3: claimed_at timestamp column on chunks table
# ---------------------------------------------------------------------------


class TestFromAC_ClaimedAtColumn:
    """AC3 — chunks table has claimed_at column for lease tracking."""

    def test_chunks_has_claimed_at_column(self, conn: sqlite3.Connection) -> None:
        cols = _column_names(conn, "chunks")
        assert "claimed_at" in cols, "chunks table missing claimed_at column"

    def test_claimed_at_is_text_type(self, conn: sqlite3.Connection) -> None:
        info = _column_info(conn, "chunks")
        assert "claimed_at" in info, "chunks table missing claimed_at column"
        assert info["claimed_at"]["type"].upper() == "TEXT", (
            f"claimed_at should be TEXT, got {info['claimed_at']['type']}"
        )

    def test_claimed_at_defaults_to_null(self, conn: sqlite3.Connection) -> None:
        """claimed_at should be nullable (no default), representing unclaimed state."""
        info = _column_info(conn, "chunks")
        assert "claimed_at" in info, "chunks table missing claimed_at column"
        assert info["claimed_at"]["dflt_value"] is None, (
            f"claimed_at should default to NULL (unclaimed), got {info['claimed_at']['dflt_value']!r}"
        )


# ---------------------------------------------------------------------------
# AC4: reviewed_pairs table with required columns
# ---------------------------------------------------------------------------


class TestFromAC_ReviewedPairsTable:
    """AC4 — reviewed_pairs table exists with entity_name, source_a, source_b."""

    def test_reviewed_pairs_table_exists(self, conn: sqlite3.Connection) -> None:
        assert _table_exists(conn, "reviewed_pairs"), "reviewed_pairs table does not exist"

    def test_reviewed_pairs_has_entity_name_column(self, conn: sqlite3.Connection) -> None:
        cols = _column_names(conn, "reviewed_pairs")
        assert "entity_name" in cols, "reviewed_pairs table missing entity_name column"

    def test_reviewed_pairs_has_source_a_column(self, conn: sqlite3.Connection) -> None:
        cols = _column_names(conn, "reviewed_pairs")
        assert "source_a" in cols, "reviewed_pairs table missing source_a column"

    def test_reviewed_pairs_has_source_b_column(self, conn: sqlite3.Connection) -> None:
        cols = _column_names(conn, "reviewed_pairs")
        assert "source_b" in cols, "reviewed_pairs table missing source_b column"

    def test_reviewed_pairs_can_insert_row(self, conn: sqlite3.Connection) -> None:
        """Smoke test — inserting a row must not raise."""
        conn.execute(
            "INSERT INTO reviewed_pairs (entity_name, source_a, source_b) VALUES (?, ?, ?)",
            ("Alice", "doc-1", "doc-2"),
        )
        row = conn.execute("SELECT entity_name, source_a, source_b FROM reviewed_pairs").fetchone()
        assert row == ("Alice", "doc-1", "doc-2")


# ---------------------------------------------------------------------------
# AC5: UNIQUE constraint on edges UNIQUE(source_id, target_id, relation, document_id)
# ---------------------------------------------------------------------------


class TestFromAC_EdgeUniqueConstraint:
    """AC5 — edges table has D17 UNIQUE(source_id, target_id, relation, document_id)."""

    def test_edges_has_document_id_column(self, conn: sqlite3.Connection) -> None:
        """UNIQUE constraint requires document_id column to exist first."""
        cols = _column_names(conn, "edges")
        assert "document_id" in cols, "edges table missing document_id column"

    def test_edges_unique_index_exists(self, conn: sqlite3.Connection) -> None:
        """A UNIQUE index covering source_id, target_id, relation, document_id must exist."""
        indexes = conn.execute("PRAGMA index_list(edges)").fetchall()
        # indexes: (seq, name, unique, origin, partial)
        unique_indexes = [idx for idx in indexes if idx[2] == 1]
        assert unique_indexes, "No UNIQUE index found on edges table"

        found = False
        for idx in unique_indexes:
            idx_name = idx[1]
            idx_cols = _index_columns(conn, idx_name)
            required = {"source_id", "target_id", "relation", "document_id"}
            if set(idx_cols) == required:
                found = True
                break

        assert found, (
            "No UNIQUE index on edges with exactly (source_id, target_id, relation, document_id). "
            f"Existing unique indexes: {[idx[1] for idx in unique_indexes]}"
        )

    def test_edges_unique_constraint_enforced(self, conn: sqlite3.Connection) -> None:
        """Inserting a duplicate (source_id, target_id, relation, document_id) must raise."""
        edge_id_1 = str(uuid.uuid4())
        edge_id_2 = str(uuid.uuid4())
        now = _now()

        # Seed document and entities required for FK-enforced inserts.
        conn.execute(
            "INSERT INTO documents (id, created_at) VALUES (?, ?)",
            ("doc-X", now),
        )
        conn.execute(
            "INSERT INTO entities (id, document_id, created_at) VALUES (?, ?, ?)",
            ("entity-A", "doc-X", now),
        )
        conn.execute(
            "INSERT INTO entities (id, document_id, created_at) VALUES (?, ?, ?)",
            ("entity-B", "doc-X", now),
        )

        common = {
            "source_id": "entity-A",
            "target_id": "entity-B",
            "relation": "RELATED_TO",
            "document_id": "doc-X",
        }

        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                edge_id_1,
                common["source_id"],
                common["target_id"],
                common["relation"],
                common["document_id"],
                now,
            ),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    edge_id_2,
                    common["source_id"],
                    common["target_id"],
                    common["relation"],
                    common["document_id"],
                    now,
                ),
            )

    def test_edges_different_document_id_is_allowed(self, conn: sqlite3.Connection) -> None:
        """Same source/target/relation but different document_id must NOT conflict."""
        now = _now()

        # Seed documents and entities required for FK-enforced inserts.
        conn.execute(
            "INSERT INTO documents (id, created_at) VALUES (?, ?)",
            ("doc-1", now),
        )
        conn.execute(
            "INSERT INTO documents (id, created_at) VALUES (?, ?)",
            ("doc-2", now),
        )
        conn.execute(
            "INSERT INTO entities (id, document_id, created_at) VALUES (?, ?, ?)",
            ("entity-A", "doc-1", now),
        )
        conn.execute(
            "INSERT INTO entities (id, document_id, created_at) VALUES (?, ?, ?)",
            ("entity-B", "doc-1", now),
        )

        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "entity-A", "entity-B", "RELATED_TO", "doc-1", now),
        )
        # Must not raise — different document_id
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "entity-A", "entity-B", "RELATED_TO", "doc-2", now),
        )
        count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert count == 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# AC6: New chunks default to enrichment_state='pending'
# ---------------------------------------------------------------------------


class TestFromAC_ChunkDefaultEnrichmentState:
    """AC6 — new chunks get enrichment_state='pending' by default."""

    def test_insert_chunk_without_enrichment_state_defaults_to_pending(self, conn: sqlite3.Connection) -> None:
        chunk_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            "INSERT INTO chunks (id, content, created_at) VALUES (?, ?, ?)",
            (chunk_id, "some content", now),
        )
        row = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        assert row is not None, "Chunk not found after insert"
        assert row[0] == "pending", f"Expected enrichment_state='pending', got {row[0]!r}"

    def test_insert_chunk_with_explicit_claimed_state(self, conn: sqlite3.Connection) -> None:
        chunk_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            "INSERT INTO chunks (id, content, created_at, enrichment_state) VALUES (?, ?, ?, ?)",
            (chunk_id, "content", now, "claimed"),
        )
        row = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        assert row is not None
        assert row[0] == "claimed"

    def test_insert_chunk_with_explicit_enriched_state(self, conn: sqlite3.Connection) -> None:
        chunk_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            "INSERT INTO chunks (id, content, created_at, enrichment_state) VALUES (?, ?, ?, ?)",
            (chunk_id, "content", now, "enriched"),
        )
        row = conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        assert row is not None
        assert row[0] == "enriched"


# ---------------------------------------------------------------------------
# Upgrade path: v10 → v11 migration
# ---------------------------------------------------------------------------


@pytest.fixture()
def v10_conn() -> sqlite3.Connection:
    """In-memory SQLite connection simulating an existing v10 database.

    Builds the complete v10 schema manually — all columns through v10, none of
    the v11 additions (no enrichment_state/claimed_at on chunks, no document_id
    on edges, no reviewed_pairs table).  Schema version is recorded as 10.
    Calling init_db() on this connection should trigger the v10→v11 migration.
    """
    c = sqlite3.connect(":memory:")
    c.execute(
        """\
CREATE TABLE documents (
    id TEXT PRIMARY KEY, title TEXT, content TEXT, metadata TEXT,
    created_at TEXT, scope TEXT DEFAULT 'global', source_id TEXT
)"""
    )
    c.execute(
        """\
CREATE TABLE entities (
    id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, description TEXT,
    metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global',
    document_id TEXT, chunk_id TEXT, importance REAL DEFAULT 0.5
)"""
    )
    # v10 edges: no document_id column (added in v11)
    c.execute(
        """\
CREATE TABLE edges (
    id TEXT PRIMARY KEY, source_id TEXT, target_id TEXT,
    relation TEXT, weight REAL, metadata TEXT,
    created_at TEXT, scope TEXT DEFAULT 'global'
)"""
    )
    # v10 chunks: no enrichment_state, no claimed_at (both added in v11)
    c.execute(
        """\
CREATE TABLE chunks (
    id TEXT PRIMARY KEY, document_id TEXT, chunk_index INTEGER,
    content TEXT, metadata TEXT, created_at TEXT,
    scope TEXT DEFAULT 'global', consolidated INTEGER DEFAULT 0
)"""
    )
    c.execute(
        """\
CREATE TABLE document_status (
    document_id TEXT PRIMARY KEY, status TEXT, source TEXT,
    error TEXT, created_at TEXT, updated_at TEXT,
    scope TEXT DEFAULT 'global', content_hash TEXT
)"""
    )
    c.execute(
        """\
CREATE TABLE knowledge_sources (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, source_type TEXT NOT NULL,
    fetch_method TEXT NOT NULL DEFAULT '', enrich INTEGER NOT NULL DEFAULT 0,
    config TEXT NOT NULL, scope TEXT DEFAULT 'global', enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0, last_refreshed_at TEXT, last_error TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
)"""
    )
    c.execute(
        """\
CREATE TABLE bookmarks (
    id TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL,
    description TEXT, tags TEXT NOT NULL DEFAULT '[]',
    relevance_score REAL NOT NULL DEFAULT 0.0, reason TEXT,
    scope TEXT NOT NULL DEFAULT 'global', document_id TEXT,
    content_hash TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
)"""
    )
    c.execute(
        """\
CREATE TABLE consolidations (
    id TEXT PRIMARY KEY, source_ids TEXT NOT NULL, summary TEXT,
    insight TEXT, created_at TEXT, scope TEXT DEFAULT 'global'
)"""
    )
    c.execute(
        """\
CREATE TABLE source_pages (
    id TEXT PRIMARY KEY, source_id TEXT, url TEXT NOT NULL,
    status TEXT DEFAULT 'discovered', extraction_hash TEXT,
    last_extracted TEXT, scope TEXT DEFAULT 'global',
    created_at TEXT, updated_at TEXT
)"""
    )
    c.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
    c.execute("INSERT INTO schema_version VALUES (10, '2026-01-01T00:00:00+00:00')")

    # Pre-existing indexes created by earlier migrations
    c.execute("CREATE INDEX idx_document_status_source ON document_status(source)")
    c.execute("CREATE UNIQUE INDEX idx_knowledge_sources_name_scope ON knowledge_sources(name, scope)")
    c.execute("CREATE INDEX idx_knowledge_sources_scope ON knowledge_sources(scope)")
    c.execute("CREATE UNIQUE INDEX idx_bookmarks_url_scope ON bookmarks(url, scope)")
    c.execute("CREATE INDEX idx_bookmarks_scope ON bookmarks(scope)")
    c.execute("CREATE INDEX idx_source_pages_source_id ON source_pages(source_id)")
    for table in (
        "entities",
        "documents",
        "edges",
        "chunks",
        "document_status",
        "source_pages",
    ):
        c.execute(f"CREATE INDEX idx_{table}_scope ON {table}(scope)")

    c.commit()
    return c


class TestFromAC_MigrationUpgradePath:
    """Upgrade-path tests: existing v10 database migrates to v11 via init_db()."""

    def test_v10_to_v11_enrichment_state_added_to_chunks(self, v10_conn: sqlite3.Connection) -> None:
        """init_db() on a v10 DB must add enrichment_state column to chunks."""
        init_db(v10_conn)
        cols = _column_names(v10_conn, "chunks")
        assert "enrichment_state" in cols, "v10→v11 migration did not add enrichment_state to chunks"

    def test_v10_to_v11_claimed_at_added_to_chunks(self, v10_conn: sqlite3.Connection) -> None:
        """init_db() on a v10 DB must add claimed_at column to chunks."""
        init_db(v10_conn)
        cols = _column_names(v10_conn, "chunks")
        assert "claimed_at" in cols, "v10→v11 migration did not add claimed_at to chunks"

    def test_v10_to_v11_document_id_added_to_edges(self, v10_conn: sqlite3.Connection) -> None:
        """init_db() on a v10 DB must add document_id column to edges."""
        init_db(v10_conn)
        cols = _column_names(v10_conn, "edges")
        assert "document_id" in cols, "v10→v11 migration did not add document_id to edges"

    def test_v10_to_v11_reviewed_pairs_table_exists(self, v10_conn: sqlite3.Connection) -> None:
        """init_db() on a v10 DB must result in the reviewed_pairs table existing."""
        init_db(v10_conn)
        assert _table_exists(v10_conn, "reviewed_pairs"), (
            "reviewed_pairs table not present after v10→v11 upgrade via init_db()"
        )

    def test_v10_to_v11_d17_unique_index_exists(self, v10_conn: sqlite3.Connection) -> None:
        """init_db() on a v10 DB must create D17 UNIQUE index on edges."""
        init_db(v10_conn)
        indexes = v10_conn.execute("PRAGMA index_list(edges)").fetchall()
        unique_indexes = [idx for idx in indexes if idx[2] == 1]
        found = False
        for idx in unique_indexes:
            idx_cols = _index_columns(v10_conn, idx[1])
            required = {"source_id", "target_id", "relation", "document_id"}
            if set(idx_cols) == required:
                found = True
                break
        assert found, (
            "D17 UNIQUE index with exactly (source_id, target_id, relation, document_id)"
            " not present after v10→v11 upgrade via init_db()"
        )

    def test_v10_to_v13_schema_version_updated_to_v13(self, v10_conn: sqlite3.Connection) -> None:
        """init_db() on a v10 DB must update schema_version to the current terminal version (13)."""
        init_db(v10_conn)
        ver = v10_conn.execute("SELECT version FROM schema_version").fetchone()
        assert ver is not None, "schema_version table empty after migration"
        assert ver[0] == 13, f"Expected schema version 13, got {ver[0]}"  # noqa: PLR2004

    def test_v10_to_v11_enrichment_state_default_on_insert(self, v10_conn: sqlite3.Connection) -> None:
        """Post-upgrade chunk inserts must default enrichment_state to 'pending'."""
        init_db(v10_conn)
        chunk_id = str(uuid.uuid4())
        now = _now()
        v10_conn.execute(
            "INSERT INTO chunks (id, content, created_at) VALUES (?, ?, ?)",
            (chunk_id, "upgraded content", now),
        )
        row = v10_conn.execute("SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        assert row is not None, "Chunk not found after insert into upgraded DB"
        assert row[0] == "pending", f"Post-upgrade chunk insert must default enrichment_state='pending', got {row[0]!r}"


# ---------------------------------------------------------------------------
# Upgrade path: legacy reviewed_pairs 3-col PK → 5-col PK with data preserved
# ---------------------------------------------------------------------------


class TestFromAC_ReviewedPairsUpgradePath:
    """PO-5 (AC-4/AC-5): reviewed_pairs 3-col PK upgrades to 5-col PK with legacy rows intact.

    Verifies that init_db() on a DB with the old reviewed_pairs schema (entity_name,
    source_a, source_b PRIMARY KEY) rebuilds the table to the 5-col PK shape and
    preserves existing rows with entity_id_a='' and entity_id_b=''.
    """

    @pytest.fixture()
    def legacy_reviewed_pairs_conn(self) -> sqlite3.Connection:
        """In-memory DB with reviewed_pairs on the old 3-column PRIMARY KEY."""
        c = sqlite3.connect(":memory:")
        c.execute(
            """\
CREATE TABLE reviewed_pairs (
    entity_name TEXT NOT NULL,
    source_a    TEXT NOT NULL,
    source_b    TEXT NOT NULL,
    PRIMARY KEY (entity_name, source_a, source_b)
)"""
        )
        c.execute(
            "INSERT INTO reviewed_pairs (entity_name, source_a, source_b) VALUES (?, ?, ?)",
            ("E", "S1", "S2"),
        )
        c.commit()
        return c

    def test_upgrade_adds_entity_id_a_column(self, legacy_reviewed_pairs_conn: sqlite3.Connection) -> None:
        """init_db on legacy reviewed_pairs must produce entity_id_a column."""
        init_db(legacy_reviewed_pairs_conn)
        cols = _column_names(legacy_reviewed_pairs_conn, "reviewed_pairs")
        assert "entity_id_a" in cols, "init_db did not add entity_id_a column to legacy reviewed_pairs table"

    def test_upgrade_adds_entity_id_b_column(self, legacy_reviewed_pairs_conn: sqlite3.Connection) -> None:
        """init_db on legacy reviewed_pairs must produce entity_id_b column."""
        init_db(legacy_reviewed_pairs_conn)
        cols = _column_names(legacy_reviewed_pairs_conn, "reviewed_pairs")
        assert "entity_id_b" in cols, "init_db did not add entity_id_b column to legacy reviewed_pairs table"

    def test_upgrade_rebuilds_to_five_column_pk(self, legacy_reviewed_pairs_conn: sqlite3.Connection) -> None:
        """After init_db, reviewed_pairs must have the 5-col PRIMARY KEY."""
        init_db(legacy_reviewed_pairs_conn)
        pk_cols = [
            row[1]
            for row in legacy_reviewed_pairs_conn.execute("PRAGMA table_info(reviewed_pairs)").fetchall()
            if row[5] > 0
        ]
        assert pk_cols == [
            "entity_name",
            "source_a",
            "source_b",
            "entity_id_a",
            "entity_id_b",
        ], f"Expected 5-col PK after upgrade, got {pk_cols!r}"

    def test_upgrade_preserves_legacy_row(self, legacy_reviewed_pairs_conn: sqlite3.Connection) -> None:
        """Legacy row must survive the PK rebuild with empty entity_id_a/entity_id_b."""
        init_db(legacy_reviewed_pairs_conn)
        row = legacy_reviewed_pairs_conn.execute(
            "SELECT entity_name, source_a, source_b, entity_id_a, entity_id_b FROM reviewed_pairs"
        ).fetchone()
        assert row is not None, "Legacy row must be preserved after reviewed_pairs PK rebuild"
        assert row[0] == "E", f"entity_name mismatch: expected 'E', got {row[0]!r}"
        assert row[1] == "S1", f"source_a mismatch: expected 'S1', got {row[1]!r}"
        assert row[2] == "S2", f"source_b mismatch: expected 'S2', got {row[2]!r}"
        assert row[3] == "", f"entity_id_a must default to '' for legacy rows after upgrade, got {row[3]!r}"
        assert row[4] == "", f"entity_id_b must default to '' for legacy rows after upgrade, got {row[4]!r}"
