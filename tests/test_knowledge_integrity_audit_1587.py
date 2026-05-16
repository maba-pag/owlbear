"""Failing tests for task #1587: Knowledge integrity audit function.

TDD RED phase — all 7 tests must fail until builder task #1588 implements
``audit_integrity()`` in owlbear_knowledge.schema.

Covers:
  AC-1: chunks_orphaned — detects chunk whose parent document was deleted
  AC-2: edges_dangling — detects edge with non-existent source_id
  AC-3: entities_orphaned — detects entity with non-existent document_id
  AC-4: status_orphaned — detects document_status with non-existent document_id
  AC-5: clean DB returns all four keys with count==0 and ids==[]
  AC-6: audit_integrity() is read-only (total_changes unchanged)
  Supplementary: edges_dangling also detects orphan target_id
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from owlbear_knowledge.schema import audit_integrity, init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _fresh_db() -> sqlite3.Connection:
    """Return an in-memory connection with the knowledge schema initialized."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _insert_document(conn: sqlite3.Connection, doc_id: str) -> None:
    conn.execute(
        "INSERT INTO documents (id, title, content, created_at) VALUES (?, ?, ?, ?)",
        (doc_id, "T", "C", _now()),
    )
    conn.commit()


def _insert_chunk(conn: sqlite3.Connection, chunk_id: str, document_id: str) -> None:
    conn.execute(
        "INSERT INTO chunks (id, document_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (chunk_id, document_id, 0, "content", _now()),
    )
    conn.commit()


def _insert_entity(conn: sqlite3.Connection, entity_id: str, document_id: str) -> None:
    conn.execute(
        "INSERT INTO entities (id, name, entity_type, created_at, document_id) VALUES (?, ?, ?, ?, ?)",
        (entity_id, "E", "person", _now(), document_id),
    )
    conn.commit()


def _insert_edge(
    conn: sqlite3.Connection,
    edge_id: str,
    source_id: str | None,
    target_id: str | None,
    document_id: str,
) -> None:
    conn.execute(
        "INSERT INTO edges (id, source_id, target_id, relation, document_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (edge_id, source_id, target_id, "rel", document_id, _now()),
    )
    conn.commit()


def _insert_document_status(conn: sqlite3.Connection, document_id: str) -> None:
    conn.execute(
        "INSERT INTO document_status (document_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (document_id, "done", _now(), _now()),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# All AC tests in one class
# ---------------------------------------------------------------------------


class TestFromAC_IntegrityAudit:
    """Tests for ``audit_integrity(conn)`` covering all 6 acceptance criteria."""

    def test_chunks_orphaned_detects_one_orphan(self) -> None:
        """AC-1: chunk whose parent document was deleted is reported in chunks_orphaned."""
        conn = _fresh_db()
        _insert_document(conn, "doc-1")
        _insert_chunk(conn, "chunk-1", "doc-1")
        # Delete parent document with FK disabled to create an orphan chunk
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-1'")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 1
        assert "chunk-1" in result["chunks_orphaned"]["ids"]

    def test_edges_dangling_detects_orphan_source_id(self) -> None:
        """AC-2: edge with non-existent source_id is reported in edges_dangling."""
        conn = _fresh_db()
        _insert_document(conn, "doc-2")
        # Insert edge with FK disabled — source entity does not exist
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_edge(conn, "edge-1", "nonexistent-entity-id", None, "doc-2")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 1
        assert "edge-1" in result["edges_dangling"]["ids"]

    def test_entities_orphaned_detects_one_orphan(self) -> None:
        """AC-3: entity whose document_id is not in documents is reported in entities_orphaned."""
        conn = _fresh_db()
        # entities.document_id has no FK; disable FK defensively per AC guidance
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_entity(conn, "entity-1", "nonexistent-doc-id")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["entities_orphaned"]["count"] == 1
        assert "entity-1" in result["entities_orphaned"]["ids"]

    def test_status_orphaned_detects_one_orphan(self) -> None:
        """AC-4: document_status with non-existent document_id is reported in status_orphaned."""
        conn = _fresh_db()
        # document_status has no FK constraint; insert directly
        _insert_document_status(conn, "nonexistent-doc-id")

        result = audit_integrity(conn)

        assert result["status_orphaned"]["count"] == 1
        assert "nonexistent-doc-id" in result["status_orphaned"]["ids"]

    def test_clean_db_returns_all_keys_with_zero_counts(self) -> None:
        """AC-5: clean DB with full chain returns all four keys, each count==0 and ids==[]."""
        conn = _fresh_db()
        _insert_document(conn, "doc-a")
        _insert_chunk(conn, "chunk-a", "doc-a")
        _insert_entity(conn, "entity-a", "doc-a")
        _insert_edge(conn, "edge-a", "entity-a", None, "doc-a")
        _insert_document_status(conn, "doc-a")

        result = audit_integrity(conn)

        for key in ("chunks_orphaned", "entities_orphaned", "edges_dangling", "status_orphaned"):
            assert key in result, f"Key {key!r} missing from result"
            assert result[key]["count"] == 0, f"Expected count==0 for {key!r}, got {result[key]['count']!r}"
            assert result[key]["ids"] == [], f"Expected ids==[] for {key!r}, got {result[key]['ids']!r}"

    def test_audit_is_read_only(self) -> None:
        """AC-6: audit_integrity() must not write to the database (total_changes unchanged)."""
        conn = _fresh_db()
        _insert_document(conn, "doc-ro")
        _insert_chunk(conn, "chunk-ro", "doc-ro")
        # Create orphan chunk so the function has something to detect
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-ro'")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        before = conn.total_changes
        audit_integrity(conn)
        after = conn.total_changes

        assert before == after, f"total_changes changed from {before} to {after} — audit_integrity() is not read-only"

    def test_edges_dangling_detects_orphan_target_id(self) -> None:
        """Supplementary: edge with non-existent target_id is also detected as dangling."""
        conn = _fresh_db()
        _insert_document(conn, "doc-3")
        _insert_entity(conn, "entity-2", "doc-3")
        # Insert edge with valid source_id but non-existent target_id (FK disabled)
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_edge(conn, "edge-2", "entity-2", "nonexistent-target-id", "doc-3")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 1
        assert "edge-2" in result["edges_dangling"]["ids"]

    def test_edge_with_valid_nonnull_target_id_not_flagged_as_dangling(self) -> None:
        """AC-5 proof-gap: edge whose both source_id and target_id reference existing
        entities must NOT be flagged as dangling (guards against target-side false-positive)."""
        conn = _fresh_db()
        _insert_document(conn, "doc-clean")
        _insert_entity(conn, "entity-src", "doc-clean")
        _insert_entity(conn, "entity-tgt", "doc-clean")
        # Both source and target exist — FK enforced
        _insert_edge(conn, "edge-clean", "entity-src", "entity-tgt", "doc-clean")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 0, (
            f"Valid edge with non-null target_id incorrectly flagged as dangling: {result['edges_dangling']['ids']!r}"
        )
        assert result["edges_dangling"]["ids"] == []
