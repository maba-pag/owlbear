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
            config=self._load_config(row[3]),  # type: ignore[arg-type]
            scope=row[4],  # type: ignore[arg-type]
            enabled=bool(row[5]),
            priority=row[6],  # type: ignore[arg-type]
            last_refreshed_at=row[7],  # type: ignore[arg-type]
            last_error=row[8],  # type: ignore[arg-type]
            created_at=row[9],  # type: ignore[arg-type]
            updated_at=row[10],  # type: ignore[arg-type]
        )

    _SELECT_COLS = (
        "id, name, source_type, config, scope, enabled, priority, "
        "last_refreshed_at, last_error, created_at, updated_at"
    )

    def _select_from_sources(self) -> str:
        """Return the ``SELECT ... FROM knowledge_sources`` prefix."""
        return f"SELECT {self._SELECT_COLS} FROM knowledge_sources"  # noqa: S608

    # -- CRUD ----------------------------------------------------------------

    def create(self, source: KnowledgeSource) -> None:
        """Insert *source* into the ``knowledge_sources`` table."""
        self._conn.execute(
            "INSERT INTO knowledge_sources"
            " (id, name, source_type, config, scope, enabled, priority,"
            "  last_refreshed_at, last_error, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                source.id,
                source.name,
                str(source.source_type),
                self._dump_config(source.config),
                source.scope,
                int(source.enabled),
                source.priority,
                source.last_refreshed_at,
                source.last_error,
                source.created_at,
                source.updated_at,
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
            " name = ?, source_type = ?, config = ?, scope = ?,"
            " enabled = ?, priority = ?, last_refreshed_at = ?,"
            " last_error = ?, created_at = ?, updated_at = ?"
            " WHERE id = ?",
            (
                source.name,
                str(source.source_type),
                self._dump_config(source.config),
                source.scope,
                int(source.enabled),
                source.priority,
                source.last_refreshed_at,
                source.last_error,
                source.created_at,
                source.updated_at,
                source.id,
            ),
        )
        if cur.rowcount == 0:
            msg = f"KnowledgeSource {source.id!r} not found"
            raise ValueError(msg)
        self._conn.commit()

    def delete(self, source_id: str) -> bool:
        """Delete the source with *source_id*. Return ``True`` if it existed."""
        cur = self._conn.execute(
            "DELETE FROM knowledge_sources WHERE id = ?",
            (source_id,),
        )
        self._conn.commit()
        return cur.rowcount > 0
