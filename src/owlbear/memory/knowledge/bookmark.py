"""Bookmark model and SQLite CRUD store.

Follows the same pattern as :class:`~owlbear.memory.knowledge.source_store.KnowledgeSourceStore`:
constructor takes an open ``sqlite3.Connection``, JSON helpers for the
``tags`` list, and simple parameterized queries.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from owlbear.memory.knowledge.models import _uuid_hex

if TYPE_CHECKING:
    import sqlite3


# -- Model -------------------------------------------------------------------


class Bookmark(BaseModel):
    """A bookmarked URL discovered during knowledge ingestion or browsing."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_uuid_hex)
    url: str
    title: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str | None = None
    scope: str = "global"
    document_id: str | None = None
    content_hash: str | None = None
    created_at: str
    updated_at: str


# -- Store -------------------------------------------------------------------


class BookmarkStore:
    """Synchronous CRUD façade for the ``bookmarks`` table.

    Args:
        conn (sqlite3.Connection): An open :class:`sqlite3.Connection` whose schema already contains
            the ``bookmarks`` table (see ``schema.py`` / ``init_db``).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _dump_tags(tags: list[str]) -> str:
        """Serialize a tags list to a JSON string."""
        return json.dumps(tags)

    @staticmethod
    def _load_tags(raw: str | None) -> list[str]:
        """Deserialize a JSON string back to a tags list."""
        if not raw:
            return []
        return json.loads(raw)  # type: ignore[no-any-return]

    def _row_to_model(self, row: tuple[object, ...]) -> Bookmark:
        """Map a SELECT row to a :class:`Bookmark`."""
        return Bookmark(
            id=row[0],  # type: ignore[arg-type]
            url=row[1],  # type: ignore[arg-type]
            title=row[2],  # type: ignore[arg-type]
            description=row[3],  # type: ignore[arg-type]
            tags=self._load_tags(row[4]),  # type: ignore[arg-type]
            relevance_score=row[5],  # type: ignore[arg-type]
            reason=row[6],  # type: ignore[arg-type]
            scope=row[7],  # type: ignore[arg-type]
            document_id=row[8],  # type: ignore[arg-type]
            content_hash=row[9],  # type: ignore[arg-type]
            created_at=row[10],  # type: ignore[arg-type]
            updated_at=row[11],  # type: ignore[arg-type]
        )

    _SELECT_COLS = (
        "id, url, title, description, tags, relevance_score, "
        "reason, scope, document_id, content_hash, created_at, updated_at"
    )

    # -- CRUD ----------------------------------------------------------------

    def create(self, bookmark: Bookmark) -> Bookmark:
        """Insert *bookmark* into the ``bookmarks`` table.

        Returns the same bookmark on success.
        Raises :class:`sqlite3.IntegrityError` on duplicate ``(url, scope)``.
        """
        self._conn.execute(
            "INSERT INTO bookmarks"
            " (id, url, title, description, tags, relevance_score,"
            "  reason, scope, document_id, content_hash, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bookmark.id,
                bookmark.url,
                bookmark.title,
                bookmark.description,
                self._dump_tags(bookmark.tags),
                bookmark.relevance_score,
                bookmark.reason,
                bookmark.scope,
                bookmark.document_id,
                bookmark.content_hash,
                bookmark.created_at,
                bookmark.updated_at,
            ),
        )
        self._conn.commit()
        return bookmark

    def get_by_url(self, url: str, scope: str = "global") -> Bookmark | None:
        """Return the bookmark matching *url* + *scope*, or ``None``."""
        row = self._conn.execute(
            f"SELECT {self._SELECT_COLS} FROM bookmarks WHERE url = ? AND scope = ?",  # noqa: S608
            (url, scope),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def list(
        self,
        scope: str | None = None,
        tag: str | None = None,
        min_score: float | None = None,
    ) -> list[Bookmark]:
        """Return bookmarks matching the optional filters.

        Args:
            scope (str | None): Filter by scope. ``None`` returns all scopes.
            tag (str | None): Filter by tag (substring match in JSON-encoded tags column).
            min_score (float | None): Minimum relevance_score threshold.
        """
        clauses: list[str] = []
        params: list[object] = []

        if scope is not None:
            clauses.append("scope = ?")
            params.append(scope)
        if tag is not None:
            # JSON array contains the tag as a quoted string
            clauses.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        if min_score is not None:
            clauses.append("relevance_score >= ?")
            params.append(min_score)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._conn.execute(
            f"SELECT {self._SELECT_COLS} FROM bookmarks{where}",  # noqa: S608
            params,
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def update_tags(self, bookmark_id: str, tags: list[str]) -> None:
        """Replace the tags for *bookmark_id*.

        Raises :class:`ValueError` if the id is not found.
        """
        cur = self._conn.execute(
            "UPDATE bookmarks SET tags = ? WHERE id = ?",
            (self._dump_tags(tags), bookmark_id),
        )
        if cur.rowcount == 0:
            msg = f"Bookmark {bookmark_id!r} not found"
            raise ValueError(msg)
        self._conn.commit()

    def delete(self, bookmark_id: str) -> None:
        """Delete the bookmark with *bookmark_id*.

        Raises :class:`ValueError` if the id is not found.
        """
        cur = self._conn.execute(
            "DELETE FROM bookmarks WHERE id = ?",
            (bookmark_id,),
        )
        if cur.rowcount == 0:
            msg = f"Bookmark {bookmark_id!r} not found"
            raise ValueError(msg)
        self._conn.commit()
