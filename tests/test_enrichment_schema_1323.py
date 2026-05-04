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
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
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
        assert "enrichment_state" in cols, (
            "chunks table missing enrichment_state column"
        )

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
        assert dflt == "'pending'", (
            f"enrichment_state default should be 'pending', got {dflt!r}"
        )


# ---------------------------------------------------------------------------
# AC2: enrichment_state does NOT reuse consolidated column
# ---------------------------------------------------------------------------


class TestFromAC_EnrichmentStateNotConsolidated:
    """AC2 — enrichment_state is a separate column from consolidated."""

    def test_both_columns_coexist_on_chunks(self, conn: sqlite3.Connection) -> None:
        """Both consolidated (legacy) and enrichment_state (new) must exist together."""
        cols = _column_names(conn, "chunks")
        assert "consolidated" in cols, (
            "consolidated column was removed; it must be kept for backwards compat"
        )
        assert "enrichment_state" in cols, (
            "enrichment_state column missing — must coexist with consolidated, not replace it"
        )

    def test_enrichment_state_and_consolidated_are_different_columns(
        self, conn: sqlite3.Connection
    ) -> None:
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
        assert info["consolidated"]["type"].upper() == "INTEGER", (
            "consolidated should be INTEGER"
        )
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
        assert _table_exists(conn, "reviewed_pairs"), (
            "reviewed_pairs table does not exist"
        )

    def test_reviewed_pairs_has_entity_name_column(self, conn: sqlite3.Connection) -> None:
        cols = _column_names(conn, "reviewed_pairs")
        assert "entity_name" in cols, (
            "reviewed_pairs table missing entity_name column"
        )

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
        row = conn.execute(
            "SELECT entity_name, source_a, source_b FROM reviewed_pairs"
        ).fetchone()
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
            if required.issubset(set(idx_cols)):
                found = True
                break

        assert found, (
            "No UNIQUE index on edges covering (source_id, target_id, relation, document_id). "
            f"Existing unique indexes: {[idx[1] for idx in unique_indexes]}"
        )

    def test_edges_unique_constraint_enforced(self, conn: sqlite3.Connection) -> None:
        """Inserting a duplicate (source_id, target_id, relation, document_id) must raise."""
        edge_id_1 = str(uuid.uuid4())
        edge_id_2 = str(uuid.uuid4())
        now = _now()

        common = {
            "source_id": "entity-A",
            "target_id": "entity-B",
            "relation": "RELATED_TO",
            "document_id": "doc-X",
        }

        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (edge_id_1, common["source_id"], common["target_id"],
             common["relation"], common["document_id"], now),
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (edge_id_2, common["source_id"], common["target_id"],
                 common["relation"], common["document_id"], now),
            )

    def test_edges_different_document_id_is_allowed(self, conn: sqlite3.Connection) -> None:
        """Same source/target/relation but different document_id must NOT conflict."""
        now = _now()
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "entity-A", "entity-B", "RELATED_TO", "doc-1", now),
        )
        # Must not raise — different document_id
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "entity-A", "entity-B", "RELATED_TO", "doc-2", now),
        )
        count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert count == 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# AC6: New chunks default to enrichment_state='pending'
# ---------------------------------------------------------------------------


class TestFromAC_ChunkDefaultEnrichmentState:
    """AC6 — new chunks get enrichment_state='pending' by default."""

    def test_insert_chunk_without_enrichment_state_defaults_to_pending(
        self, conn: sqlite3.Connection
    ) -> None:
        chunk_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            "INSERT INTO chunks (id, content, created_at) VALUES (?, ?, ?)",
            (chunk_id, "some content", now),
        )
        row = conn.execute(
            "SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        assert row is not None, "Chunk not found after insert"
        assert row[0] == "pending", (
            f"Expected enrichment_state='pending', got {row[0]!r}"
        )

    def test_insert_chunk_with_explicit_claimed_state(
        self, conn: sqlite3.Connection
    ) -> None:
        chunk_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            "INSERT INTO chunks (id, content, created_at, enrichment_state) VALUES (?, ?, ?, ?)",
            (chunk_id, "content", now, "claimed"),
        )
        row = conn.execute(
            "SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        assert row is not None
        assert row[0] == "claimed"

    def test_insert_chunk_with_explicit_enriched_state(
        self, conn: sqlite3.Connection
    ) -> None:
        chunk_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            "INSERT INTO chunks (id, content, created_at, enrichment_state) VALUES (?, ?, ?, ?)",
            (chunk_id, "content", now, "enriched"),
        )
        row = conn.execute(
            "SELECT enrichment_state FROM chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        assert row is not None
        assert row[0] == "enriched"
