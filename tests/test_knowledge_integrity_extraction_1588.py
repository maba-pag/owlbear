"""Failing tests for task #1588: Knowledge integrity module extraction.

TDD RED phase — all tests must fail until the builder:
  1. Creates ``owlbear_knowledge/integrity.py`` containing ``audit_integrity()``.
  2. Adds a one-line re-export in ``owlbear_knowledge/schema.py``.

Covers:
  AC-1: ``owlbear_knowledge.integrity`` module exists; ``audit_integrity()``
        accepts ``conn: sqlite3.Connection`` and returns
        ``dict[str, dict[str, int | list[str]]]`` with exactly the keys
        ``chunks_orphaned``, ``entities_orphaned``, ``edges_dangling``,
        ``status_orphaned``.
  AC-2: Detection — orphan chunks (chunk.document_id not in documents),
        orphan entities (entity.document_id not in documents),
        dangling edges (source_id or target_id not in entities),
        orphan document_status (document_status.document_id not in documents).
  AC-3: Read-only — ``total_changes`` is unchanged before and after the call.
  AC-4: ``from owlbear_knowledge.schema import audit_integrity`` remains
        importable after the move (backward-compatible re-export).
"""

from __future__ import annotations

import inspect
import sqlite3
from datetime import UTC, datetime

# AC-1: This import is the primary RED trigger.
# The module does not exist until the builder creates it.
from owlbear_knowledge.integrity import audit_integrity  # noqa: E402
from owlbear_knowledge.schema import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _fresh_db() -> sqlite3.Connection:
    """Return an in-memory connection with the knowledge schema initialised."""
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
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_IntegrityExtraction:
    """Tests derived from AC-1 through AC-4 for task #1588.

    All tests import from ``owlbear_knowledge.integrity`` (the new module).
    """

    # ------------------------------------------------------------------
    # AC-1 — callable shape and return-type contract
    # ------------------------------------------------------------------

    def test_audit_integrity_is_callable(self) -> None:
        """AC-1: audit_integrity imported from integrity module is callable."""
        assert callable(audit_integrity)

    def test_signature_accepts_sqlite3_connection(self) -> None:
        """AC-1: function signature has a single parameter typed as sqlite3.Connection."""
        sig = inspect.signature(audit_integrity)
        params = list(sig.parameters.values())
        assert len(params) == 1
        param = params[0]
        assert param.name == "conn"

    def test_return_value_has_all_four_required_keys(self) -> None:
        """AC-1: return dict has exactly the four required keys."""
        conn = _fresh_db()
        result = audit_integrity(conn)
        for key in ("chunks_orphaned", "entities_orphaned", "edges_dangling", "status_orphaned"):
            assert key in result, f"Required key {key!r} missing from result"

    def test_return_value_inner_dicts_have_count_and_ids(self) -> None:
        """AC-1: each sub-dict has 'count' (int) and 'ids' (list) fields."""
        conn = _fresh_db()
        result = audit_integrity(conn)
        for key in ("chunks_orphaned", "entities_orphaned", "edges_dangling", "status_orphaned"):
            sub = result[key]
            assert "count" in sub, f"Sub-dict for {key!r} missing 'count'"
            assert "ids" in sub, f"Sub-dict for {key!r} missing 'ids'"
            assert isinstance(sub["count"], int), f"'count' for {key!r} must be int"
            assert isinstance(sub["ids"], list), f"'ids' for {key!r} must be list"

    # ------------------------------------------------------------------
    # AC-2 — detection: happy paths per orphan category
    # ------------------------------------------------------------------

    def test_clean_db_all_four_keys_count_zero_ids_empty(self) -> None:
        """AC-2 (clean case): no orphans → all four keys have count==0 and ids==[]."""
        conn = _fresh_db()
        _insert_document(conn, "doc-a")
        _insert_chunk(conn, "chunk-a", "doc-a")
        _insert_entity(conn, "entity-a", "doc-a")
        _insert_edge(conn, "edge-a", "entity-a", None, "doc-a")
        _insert_document_status(conn, "doc-a")

        result = audit_integrity(conn)

        for key in ("chunks_orphaned", "entities_orphaned", "edges_dangling", "status_orphaned"):
            assert result[key]["count"] == 0, f"{key}: expected count==0, got {result[key]['count']}"
            assert result[key]["ids"] == [], f"{key}: expected ids==[], got {result[key]['ids']}"

    def test_detects_orphan_chunk(self) -> None:
        """AC-2: chunk whose parent document was deleted appears in chunks_orphaned."""
        conn = _fresh_db()
        _insert_document(conn, "doc-1")
        _insert_chunk(conn, "chunk-1", "doc-1")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-1'")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 1
        assert "chunk-1" in result["chunks_orphaned"]["ids"]

    def test_detects_orphan_entity(self) -> None:
        """AC-2: entity whose document_id is not in documents appears in entities_orphaned."""
        conn = _fresh_db()
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_entity(conn, "entity-orphan", "nonexistent-doc")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["entities_orphaned"]["count"] == 1
        assert "entity-orphan" in result["entities_orphaned"]["ids"]

    def test_detects_dangling_edge_orphan_source_id(self) -> None:
        """AC-2: edge with source_id not in entities appears in edges_dangling."""
        conn = _fresh_db()
        _insert_document(conn, "doc-2")
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_edge(conn, "edge-bad-src", "ghost-entity-id", None, "doc-2")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 1
        assert "edge-bad-src" in result["edges_dangling"]["ids"]

    def test_detects_dangling_edge_orphan_target_id(self) -> None:
        """AC-2 (edge): edge with target_id not in entities appears in edges_dangling."""
        conn = _fresh_db()
        _insert_document(conn, "doc-3")
        _insert_entity(conn, "entity-src", "doc-3")
        conn.execute("PRAGMA foreign_keys = OFF")
        _insert_edge(conn, "edge-bad-tgt", "entity-src", "ghost-target-id", "doc-3")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 1
        assert "edge-bad-tgt" in result["edges_dangling"]["ids"]

    def test_detects_orphan_document_status(self) -> None:
        """AC-2: document_status whose document_id is not in documents appears in status_orphaned."""
        conn = _fresh_db()
        _insert_document_status(conn, "nonexistent-doc-id")

        result = audit_integrity(conn)

        assert result["status_orphaned"]["count"] == 1
        assert "nonexistent-doc-id" in result["status_orphaned"]["ids"]

    # ------------------------------------------------------------------
    # AC-2 — detection: edge cases (multiple orphans, cross-category)
    # ------------------------------------------------------------------

    def test_multiple_orphans_same_category_all_reported(self) -> None:
        """AC-2 (edge): multiple orphan chunks are all reported."""
        conn = _fresh_db()
        _insert_document(conn, "doc-bulk")
        _insert_chunk(conn, "chunk-bulk-1", "doc-bulk")
        _insert_chunk(conn, "chunk-bulk-2", "doc-bulk")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-bulk'")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] == 2
        assert "chunk-bulk-1" in result["chunks_orphaned"]["ids"]
        assert "chunk-bulk-2" in result["chunks_orphaned"]["ids"]

    def test_multiple_orphan_categories_reported_independently(self) -> None:
        """AC-2 (edge): simultaneous orphans in different categories are reported independently."""
        conn = _fresh_db()
        # Orphan chunk
        _insert_document(conn, "doc-x")
        _insert_chunk(conn, "chunk-x", "doc-x")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-x'")
        conn.commit()
        # Orphan document_status (no FK, can insert directly)
        _insert_document_status(conn, "ghost-doc-status")
        conn.execute("PRAGMA foreign_keys = ON")

        result = audit_integrity(conn)

        assert result["chunks_orphaned"]["count"] >= 1
        assert "chunk-x" in result["chunks_orphaned"]["ids"]
        assert result["status_orphaned"]["count"] >= 1
        assert "ghost-doc-status" in result["status_orphaned"]["ids"]

    def test_valid_edge_with_both_endpoints_not_flagged_as_dangling(self) -> None:
        """AC-2 (boundary): edge with valid source_id and non-null target_id is not dangling."""
        conn = _fresh_db()
        _insert_document(conn, "doc-valid")
        _insert_entity(conn, "src-entity", "doc-valid")
        _insert_entity(conn, "tgt-entity", "doc-valid")
        _insert_edge(conn, "edge-valid", "src-entity", "tgt-entity", "doc-valid")

        result = audit_integrity(conn)

        assert result["edges_dangling"]["count"] == 0
        assert result["edges_dangling"]["ids"] == []

    # ------------------------------------------------------------------
    # AC-3 — read-only guarantee
    # ------------------------------------------------------------------

    def test_read_only_total_changes_unchanged_on_clean_db(self) -> None:
        """AC-3: audit_integrity() does not modify the database (clean DB case)."""
        conn = _fresh_db()
        before = conn.total_changes
        audit_integrity(conn)
        after = conn.total_changes
        assert before == after, f"total_changes changed from {before} to {after} — audit_integrity() is not read-only"

    def test_read_only_total_changes_unchanged_with_orphans(self) -> None:
        """AC-3: audit_integrity() does not modify the database even when orphans are detected."""
        conn = _fresh_db()
        _insert_document(conn, "doc-ro")
        _insert_chunk(conn, "chunk-ro", "doc-ro")
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = 'doc-ro'")
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")

        before = conn.total_changes
        audit_integrity(conn)
        after = conn.total_changes

        assert before == after, f"total_changes changed from {before} to {after} — audit_integrity() wrote to DB"

    # ------------------------------------------------------------------
    # AC-4 — backward-compatible re-export from schema.py
    # ------------------------------------------------------------------

    def test_schema_reexport_is_importable(self) -> None:
        """AC-4: from owlbear_knowledge.schema import audit_integrity must still work."""
        from owlbear_knowledge.schema import audit_integrity as schema_fn  # noqa: PLC0415

        assert callable(schema_fn)

    def test_schema_reexport_returns_same_structure(self) -> None:
        """AC-4: re-export from schema.py returns the same result as the primary import."""
        from owlbear_knowledge.schema import audit_integrity as schema_fn  # noqa: PLC0415

        conn = _fresh_db()
        result_integrity = audit_integrity(conn)
        result_schema = schema_fn(conn)

        assert set(result_integrity.keys()) == set(result_schema.keys())
        for key in result_integrity:
            assert result_integrity[key]["count"] == result_schema[key]["count"], (
                f"Key {key!r}: count mismatch between integrity and schema imports"
            )
            assert result_integrity[key]["ids"] == result_schema[key]["ids"], (
                f"Key {key!r}: ids mismatch between integrity and schema imports"
            )
