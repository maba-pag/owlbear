"""Read-only integrity audit helpers for knowledge database tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


def audit_integrity(conn: sqlite3.Connection) -> dict[str, dict[str, int | list[str]]]:
    """Return orphan/dangling-row counts and IDs for knowledge tables.

    The function is read-only and performs SELECT queries only.
    """
    chunks_orphaned_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT c.id
            FROM chunks AS c
            LEFT JOIN documents AS d ON d.id = c.document_id
            WHERE c.document_id IS NOT NULL
              AND d.id IS NULL
            """
        ).fetchall()
    ]

    entities_orphaned_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT e.id
            FROM entities AS e
            LEFT JOIN documents AS d ON d.id = e.document_id
            WHERE e.document_id IS NOT NULL
              AND d.id IS NULL
            """
        ).fetchall()
    ]

    edges_dangling_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT e.id
            FROM edges AS e
            LEFT JOIN entities AS source_entity ON source_entity.id = e.source_id
            LEFT JOIN entities AS target_entity ON target_entity.id = e.target_id
            WHERE (e.source_id IS NOT NULL AND source_entity.id IS NULL)
               OR (e.target_id IS NOT NULL AND target_entity.id IS NULL)
            """
        ).fetchall()
    ]

    status_orphaned_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT ds.document_id
            FROM document_status AS ds
            LEFT JOIN documents AS d ON d.id = ds.document_id
            WHERE ds.document_id IS NOT NULL
              AND d.id IS NULL
            """
        ).fetchall()
    ]

    return {
        "chunks_orphaned": {
            "count": len(chunks_orphaned_ids),
            "ids": chunks_orphaned_ids,
        },
        "entities_orphaned": {
            "count": len(entities_orphaned_ids),
            "ids": entities_orphaned_ids,
        },
        "edges_dangling": {
            "count": len(edges_dangling_ids),
            "ids": edges_dangling_ids,
        },
        "status_orphaned": {
            "count": len(status_orphaned_ids),
            "ids": status_orphaned_ids,
        },
    }
