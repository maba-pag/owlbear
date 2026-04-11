"""Document status tracking store.

Provides :class:`StatusStore` for tracking ingestion status and content
hashes, :class:`DocumentStatus` model, and :func:`compute_content_hash`.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    import sqlite3


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DocumentStatus(BaseModel):
    """Status record for a previously-ingested document."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    content_hash: str | None
    status: str


# ---------------------------------------------------------------------------
# Content hashing
# ---------------------------------------------------------------------------


def compute_content_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content* after normalizing whitespace.

    Leading/trailing whitespace is stripped and internal runs of whitespace are
    collapsed to a single space so cosmetic differences do not produce false
    positives in delta detection.

    Args:
        content: Raw document text.

    Returns:
        str: 64-character lowercase hex digest.
    """
    normalized = " ".join(content.split())
    return hashlib.sha256(normalized.encode()).hexdigest()


# ---------------------------------------------------------------------------
# StatusStore
# ---------------------------------------------------------------------------


class StatusStore:
    """Synchronous facade for ``document_status`` tracking in the knowledge schema.

    Args:
        conn (sqlite3.Connection): An open :class:`sqlite3.Connection` where
            :func:`~owlbear_knowledge.schema.init_db` has already been called.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def set_status(
        self,
        document_id: str,
        status: str,
        source: str | None = None,
        error: str | None = None,
        *,
        scope: str = "global",
    ) -> None:
        """Insert or update the ``document_status`` row for *document_id*."""
        now = datetime.now(tz=UTC).isoformat()
        existing = self._conn.execute(
            "SELECT document_id FROM document_status WHERE document_id = ?",
            (document_id,),
        ).fetchone()

        if existing is None:
            self._conn.execute(
                "INSERT INTO document_status "
                "(document_id, status, source, error, scope, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (document_id, status, source, error, scope, now, now),
            )
        else:
            self._conn.execute(
                "UPDATE document_status SET status = ?, error = ?, scope = ?, updated_at = ? WHERE document_id = ?",
                (status, error, scope, now, document_id),
            )
        self._conn.commit()

    def find_status_by_source(self, source: str, scope: str = "global") -> DocumentStatus | None:
        """Look up a previously-ingested document by source URI."""
        row = self._conn.execute(
            "SELECT document_id, content_hash, status FROM document_status WHERE source = ? AND scope = ?",
            (source, scope),
        ).fetchone()
        if row is None:
            return None
        return DocumentStatus(document_id=row[0], content_hash=row[1], status=row[2])

    def check_content_changed(self, source: str, content: str, scope: str = "global") -> tuple[bool, str | None]:
        """Check whether *content* differs from the previously-ingested version.

        Returns:
            tuple[bool, str | None]: ``(changed, existing_document_id)``.
        """
        new_hash = compute_content_hash(content)
        existing = self.find_status_by_source(source, scope=scope)
        if existing is None:
            return True, None
        if existing.content_hash == new_hash:
            return False, existing.document_id
        return True, existing.document_id

    def update_content_hash(self, document_id: str, content: str) -> None:
        """Store the content hash in ``document_status`` for future delta checks."""
        content_hash = compute_content_hash(content)
        self._conn.execute(
            "UPDATE document_status SET content_hash = ? WHERE document_id = ?",
            (content_hash, document_id),
        )
        self._conn.commit()
