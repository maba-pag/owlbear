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
                        WHERE c.document_id IS NULL
                             OR d.id IS NULL
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

    entities_orphaned_chunk_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT e.id
            FROM entities AS e
            LEFT JOIN chunks AS c ON c.id = e.chunk_id
            WHERE e.chunk_id IS NOT NULL
              AND c.id IS NULL
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
                WHERE e.source_id IS NULL
                    OR source_entity.id IS NULL
                    OR e.target_id IS NULL
                    OR target_entity.id IS NULL
            """
        ).fetchall()
    ]

    edges_orphaned_document_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT e.id
            FROM edges AS e
            LEFT JOIN documents AS d ON d.id = e.document_id
            WHERE e.document_id IS NOT NULL
              AND d.id IS NULL
            """
        ).fetchall()
    ]

    documents_orphaned_source_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT d.id
            FROM documents AS d
            LEFT JOIN knowledge_sources AS ks ON ks.id = d.source_id
            WHERE d.source_id IS NOT NULL
              AND ks.id IS NULL
            """
        ).fetchall()
    ]

    source_pages_orphaned_source_ids = [
        row[0]
        for row in conn.execute(
            """
            SELECT sp.id
            FROM source_pages AS sp
            LEFT JOIN knowledge_sources AS ks ON ks.id = sp.source_id
                        WHERE sp.source_id IS NULL
                             OR ks.id IS NULL
            """
        ).fetchall()
    ]

    status_orphaned_ids = [
        row[0]
        for row in conn.execute(
            """
                        SELECT COALESCE(ds.document_id, '<null>')
            FROM document_status AS ds
            LEFT JOIN documents AS d ON d.id = ds.document_id
                        WHERE ds.document_id IS NULL
                             OR d.id IS NULL
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
        "entities_orphaned_chunks": {
            "count": len(entities_orphaned_chunk_ids),
            "ids": entities_orphaned_chunk_ids,
        },
        "edges_dangling": {
            "count": len(edges_dangling_ids),
            "ids": edges_dangling_ids,
        },
        "edges_orphaned_documents": {
            "count": len(edges_orphaned_document_ids),
            "ids": edges_orphaned_document_ids,
        },
        "documents_orphaned_sources": {
            "count": len(documents_orphaned_source_ids),
            "ids": documents_orphaned_source_ids,
        },
        "source_pages_orphaned_sources": {
            "count": len(source_pages_orphaned_source_ids),
            "ids": source_pages_orphaned_source_ids,
        },
        "status_orphaned": {
            "count": len(status_orphaned_ids),
            "ids": status_orphaned_ids,
        },
    }
