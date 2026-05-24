"""SQLite CRUD store for knowledge sources."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from owlbear_knowledge.models import KnowledgeSource, SourceType

if TYPE_CHECKING:
    import sqlite3


class KnowledgeSourceStore:
    """Synchronous CRUD facade for the ``knowledge_sources`` table.

    Args:
        conn (sqlite3.Connection): An open :class:`sqlite3.Connection` whose schema already
            contains the ``knowledge_sources`` table
            (see :func:`~owlbear_knowledge.schema.init_db`).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _dump_config(cfg: dict[str, object]) -> str:
        """Serialize a config dict to a JSON string."""
        return json.dumps(cfg)

    @staticmethod
    def _load_config(raw: str | None) -> dict[str, object]:
        """Deserialize a JSON string back to a config dict."""
        if not raw:
            return {}
        return json.loads(raw)  # type: ignore[no-any-return]

    def _row_to_model(self, row: tuple[object, ...]) -> KnowledgeSource:
        """Map a SELECT row to a :class:`KnowledgeSource`."""
        return KnowledgeSource(
            id=row[0],  # type: ignore[arg-type]
            name=row[1],  # type: ignore[arg-type]
            source_type=SourceType(row[2]),
            fetch_method=row[3],  # type: ignore[arg-type]
            enrich=bool(row[4]),
            config=self._load_config(row[5]),  # type: ignore[arg-type]
            scope=row[6],  # type: ignore[arg-type]
            enabled=bool(row[7]),
            refreshable=bool(row[8]),
            priority=row[9],  # type: ignore[arg-type]
            last_refreshed_at=row[10],  # type: ignore[arg-type]
            last_error=row[11],  # type: ignore[arg-type]
            created_at=row[12],  # type: ignore[arg-type]
            updated_at=row[13],  # type: ignore[arg-type]
            last_checked_at=row[14],  # type: ignore[arg-type]
        )

    _SELECT_COLS = (
        "id, name, source_type, fetch_method, enrich, config, scope, enabled, refreshable, priority,"
        " last_refreshed_at, last_error, created_at, updated_at, last_checked_at"
    )

    def _select_from_sources(self) -> str:
        """Return the ``SELECT ... FROM knowledge_sources`` prefix."""
        return f"SELECT {self._SELECT_COLS} FROM knowledge_sources"  # noqa: S608

    @staticmethod
    def _configured_urls(config: dict[str, object]) -> set[str]:
        """Return singular and plural URL identities from a source config."""
        urls: set[str] = set()
        raw_urls = config.get("urls")
        if isinstance(raw_urls, list):
            urls.update(url.strip() for url in raw_urls if isinstance(url, str) and url.strip())
        elif isinstance(raw_urls, str) and raw_urls.strip():
            urls.update(url.strip() for url in raw_urls.split(",") if url.strip())

        raw_url = config.get("url")
        if isinstance(raw_url, str) and raw_url.strip():
            urls.add(raw_url.strip())
        return urls

    # -- CRUD ----------------------------------------------------------------

    def create(self, source: KnowledgeSource) -> None:
        """Insert *source* into the ``knowledge_sources`` table."""
        self._conn.execute(
            "INSERT INTO knowledge_sources"
            " (id, name, source_type, fetch_method, enrich, config, scope, enabled, refreshable, priority,"
            "  last_refreshed_at, last_error, created_at, updated_at, last_checked_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                source.id,
                source.name,
                str(source.source_type),
                source.fetch_method,
                int(source.enrich),
                self._dump_config(source.config),
                source.scope,
                int(source.enabled),
                int(source.refreshable),
                source.priority,
                source.last_refreshed_at,
                source.last_error,
                source.created_at,
                source.updated_at,
                source.last_checked_at,
            ),
        )
        self._conn.commit()

    def get(self, source_id: str) -> KnowledgeSource | None:
        """Return the source with *source_id*, or ``None``."""
        row = self._conn.execute(
            f"{self._select_from_sources()} WHERE id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def list_all(self, scope: str | None = None) -> list[KnowledgeSource]:
        """Return all sources, optionally filtered by *scope*."""
        if scope is not None:
            rows = self._conn.execute(
                f"{self._select_from_sources()} WHERE scope = ?",
                (scope,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                self._select_from_sources(),
            ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def update(self, source: KnowledgeSource) -> None:
        """Overwrite the record matching ``source.id``.

        Raises :class:`ValueError` if the id is not found.
        """
        cur = self._conn.execute(
            "UPDATE knowledge_sources SET"
            " name = ?, source_type = ?, fetch_method = ?, enrich = ?, config = ?, scope = ?,"
            " enabled = ?, refreshable = ?, priority = ?, last_refreshed_at = ?,"
            " last_error = ?, created_at = ?, updated_at = ?, last_checked_at = ?"
            " WHERE id = ?",
            (
                source.name,
                str(source.source_type),
                source.fetch_method,
                int(source.enrich),
                self._dump_config(source.config),
                source.scope,
                int(source.enabled),
                int(source.refreshable),
                source.priority,
                source.last_refreshed_at,
                source.last_error,
                source.created_at,
                source.updated_at,
                source.last_checked_at,
                source.id,
            ),
        )
        if cur.rowcount == 0:
            msg = f"KnowledgeSource {source.id!r} not found"
            raise ValueError(msg)
        self._conn.commit()

    def resolve_by_url(
        self,
        url: str,
        *,
        scope: str | None = None,
    ) -> KnowledgeSource | None:
        """Return the first source matching *url* and optional *scope*, or ``None``."""
        rows = self._conn.execute(self._select_from_sources()).fetchall()
        for row in rows:
            source = self._row_to_model(row)
            if scope is not None and source.scope != scope:
                continue
            if url not in self._configured_urls(source.config):
                continue
            return source
        return None

    def resolve_by_path(self, path: str) -> KnowledgeSource | None:
        """Return the first source whose config.path matches *path*, or ``None``."""
        rows = self._conn.execute(self._select_from_sources()).fetchall()
        for row in rows:
            source = self._row_to_model(row)
            if source.config.get("path") == path:
                return source
        return None

    def list_enabled(self, scope: str | None = None) -> list[KnowledgeSource]:
        """Return enabled sources, optionally filtered by *scope*, ordered by priority DESC."""
        if scope is not None:
            rows = self._conn.execute(
                f"{self._select_from_sources()} WHERE enabled = 1 AND scope = ?"  # noqa: S608,RUF100
                " ORDER BY priority DESC",
                (scope,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"{self._select_from_sources()} WHERE enabled = 1 ORDER BY priority DESC",  # noqa: S608,RUF100
            ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def delete(self, source_id: str) -> bool:
        """Delete the source with *source_id*. Return ``True`` if it existed."""
        cur = self._conn.execute(
            "DELETE FROM knowledge_sources WHERE id = ?",
            (source_id,),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def delete_cascade(self, source_id: str) -> bool:
        """Delete a source and all downstream data. Return ``True`` if it existed.

        Cascade chain: source → source_pages (via source_id FK)
                              → documents (via source_id FK)
                                 → entities, edges, chunks, document_status
        """
        row = self._conn.execute("SELECT id FROM knowledge_sources WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            return False

        # Collect document IDs linked to this source
        doc_rows = self._conn.execute("SELECT id FROM documents WHERE source_id = ?", (source_id,)).fetchall()

        for (doc_id,) in doc_rows:
            self._conn.execute("DELETE FROM edges WHERE document_id = ?", (doc_id,))
            # Delete edges for each entity in the document
            entity_rows = self._conn.execute("SELECT id FROM entities WHERE document_id = ?", (doc_id,)).fetchall()
            for (eid,) in entity_rows:
                self._conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (eid, eid))
            self._conn.execute("DELETE FROM entities WHERE document_id = ?", (doc_id,))
            self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            self._conn.execute("DELETE FROM document_status WHERE document_id = ?", (doc_id,))

        self._conn.execute("DELETE FROM reviewed_pairs WHERE source_a = ? OR source_b = ?", (source_id, source_id))
        self._conn.execute("DELETE FROM documents WHERE source_id = ?", (source_id,))
        self._conn.execute("DELETE FROM source_pages WHERE source_id = ?", (source_id,))
        self._conn.execute("DELETE FROM knowledge_sources WHERE id = ?", (source_id,))
        self._conn.commit()
        return True
