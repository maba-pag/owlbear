"""Failing tests for task #1585: Knowledge schema constraint enforcement.

TDD RED phase — all 8 tests must fail until builder implements migration v12:
  1. init_db() currently sets PRAGMA foreign_keys = OFF (AC-1 fails)
  2. chunks.document_id FK not enforced because FK is OFF (AC-2a fails)
  3. edges.source_id FK not enforced because FK is OFF (AC-2b fails)
  4. edges.target_id FK not enforced because FK is OFF (AC-2c fails)
  5. entities.document_id is nullable — no NOT NULL constraint (AC-3a fails)
  6. edges.document_id is nullable — no NOT NULL constraint (AC-3b fails)
  7-8. Valid write path test checks FK=1 first — fails because FK is currently OFF (AC-4)

Covers:
  AC-1: init_db() enables PRAGMA foreign_keys = 1
  AC-2: FK violations on chunks.document_id, edges.source_id, edges.target_id raise IntegrityError
  AC-3: NULL in entities.document_id and edges.document_id raises IntegrityError
  AC-4: Valid documents/chunks/entities/edges inserts succeed under FK enforcement
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from owlbear_knowledge.schema import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_db() -> sqlite3.Connection:
    """Return an in-memory connection with the knowledge schema initialized."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _insert_document(conn: sqlite3.Connection, doc_id: str, source_id: str) -> None:
    conn.execute(
        "INSERT INTO documents (id, title, content, created_at, source_id)"
        " VALUES (?, ?, ?, ?, ?)",
        (doc_id, "T", "C", _now(), source_id),
    )
    conn.commit()


def _insert_entity(
    conn: sqlite3.Connection,
    entity_id: str,
    document_id: str | None,
) -> None:
    conn.execute(
        "INSERT INTO entities (id, name, entity_type, created_at, document_id)"
        " VALUES (?, ?, ?, ?, ?)",
        (entity_id, "E", "person", _now(), document_id),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# AC-1: PRAGMA foreign_keys enabled after init_db
# ---------------------------------------------------------------------------


class TestFromAC_ForeignKeysEnabled:
    """init_db() must leave PRAGMA foreign_keys = 1 on the connection."""

    def test_pragma_foreign_keys_is_1_after_init_db(self) -> None:
        """PRAGMA foreign_keys must equal 1 after a fresh init_db() call."""
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        result = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert result == 1, f"Expected foreign_keys=1, got {result!r}"

    def test_pragma_foreign_keys_is_1_after_second_init_db_call(self) -> None:
        """Idempotent init_db() must still leave FK enforcement enabled."""
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        init_db(conn)  # second call must not turn FK off
        result = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert result == 1, f"Expected foreign_keys=1 after second call, got {result!r}"


# ---------------------------------------------------------------------------
# AC-2: FK violations raise IntegrityError
# ---------------------------------------------------------------------------


class TestFromAC_ForeignKeyViolations:
    """Inserting orphan rows that violate FK constraints must raise IntegrityError."""

    def test_chunk_with_nonexistent_document_id_raises(self) -> None:
        """INSERT into chunks with unknown document_id must raise IntegrityError."""
        conn = _fresh_db()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO chunks (id, document_id, chunk_index, created_at)"
                " VALUES (?, ?, ?, ?)",
                ("chunk-1", "nonexistent-doc", 0, _now()),
            )

    def test_edge_with_nonexistent_source_entity_raises(self) -> None:
        """INSERT into edges with unknown source_id must raise IntegrityError."""
        conn = _fresh_db()
        # Insert a real document and entity so target_id is valid.
        _insert_document(conn, "doc-1", "src-1")
        _insert_entity(conn, "entity-target", "doc-1")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (id, source_id, target_id, relation, document_id,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("edge-1", "nonexistent-entity", "entity-target", "relates_to",
                 "doc-1", _now()),
            )

    def test_edge_with_nonexistent_target_entity_raises(self) -> None:
        """INSERT into edges with unknown target_id must raise IntegrityError."""
        conn = _fresh_db()
        _insert_document(conn, "doc-1", "src-1")
        _insert_entity(conn, "entity-source", "doc-1")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (id, source_id, target_id, relation, document_id,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("edge-2", "entity-source", "nonexistent-entity", "relates_to",
                 "doc-1", _now()),
            )


# ---------------------------------------------------------------------------
# AC-3: NOT NULL on provenance columns
# ---------------------------------------------------------------------------


class TestFromAC_NotNullProvenanceColumns:
    """entities.document_id and edges.document_id must not accept NULL."""

    def test_entity_with_null_document_id_raises(self) -> None:
        """INSERT entity with document_id=NULL must raise IntegrityError."""
        conn = _fresh_db()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO entities (id, name, entity_type, created_at, document_id)"
                " VALUES (?, ?, ?, ?, ?)",
                ("entity-1", "Alice", "person", _now(), None),
            )

    def test_edge_with_null_document_id_raises(self) -> None:
        """INSERT edge with document_id=NULL must raise IntegrityError."""
        conn = _fresh_db()
        _insert_document(conn, "doc-1", "src-1")
        _insert_entity(conn, "entity-a", "doc-1")
        _insert_entity(conn, "entity-b", "doc-1")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (id, source_id, target_id, relation, document_id,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("edge-1", "entity-a", "entity-b", "relates_to", None, _now()),
            )


# ---------------------------------------------------------------------------
# AC-4: Valid write path accepted under FK enforcement
# ---------------------------------------------------------------------------


class TestFromAC_ValidWritePathAccepted:
    """Valid rows inserting correct FKs and non-NULL provenance must not raise."""

    def test_valid_write_path_accepted_with_fk_enforced(self) -> None:
        """Full positive write path must succeed with FK enforcement active.

        Pre-condition: FK enforcement must be ON (fails currently because
        init_db() sets PRAGMA foreign_keys = OFF).  After builder implements
        migration v12 this becomes 1 and all inserts complete without error.
        """
        conn = sqlite3.connect(":memory:")
        init_db(conn)

        # Pre-condition: FK enforcement must be enabled for the test to be meaningful.
        fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_status == 1, (
            f"PRAGMA foreign_keys must be 1 (enabled) after init_db(), got {fk_status!r}"
        )

        # Valid documents row.
        conn.execute(
            "INSERT INTO documents (id, title, content, created_at, source_id)"
            " VALUES (?, ?, ?, ?, ?)",
            ("doc-v", "Valid Doc", "content", _now(), "src-v"),
        )

        # Valid chunks row referencing the document.
        conn.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, created_at)"
            " VALUES (?, ?, ?, ?)",
            ("chunk-v", "doc-v", 0, _now()),
        )

        # Valid entities row with non-NULL document_id.
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, created_at, document_id)"
            " VALUES (?, ?, ?, ?, ?)",
            ("entity-v1", "Alpha", "concept", _now(), "doc-v"),
        )
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, created_at, document_id)"
            " VALUES (?, ?, ?, ?, ?)",
            ("entity-v2", "Beta", "concept", _now(), "doc-v"),
        )

        # Valid edges row with existing source_id, target_id, and non-NULL document_id.
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("edge-v", "entity-v1", "entity-v2", "relates_to", "doc-v", _now()),
        )

        conn.commit()
