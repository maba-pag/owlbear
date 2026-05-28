"""SQLite implementation of the SourceStore protocol."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import TypeAdapter

from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    InlineConfig,
    SourceConfig,
    SourceDeletionInfo,
    SourceHealth,
    SourceHealthReport,
    SourceKind,
    SourceRecord,
    SourceRegistration,
    SourceState,
    SourceStats,
    SourceStore,
    SourceUpdate,
    SourceWish,
    WishedSourceRecord,
)

_CONFIG_ADAPTER = TypeAdapter(SourceConfig)
_KIND_MISMATCH_ERROR = "config kind mismatch"
_VALID_STATE_TRANSITIONS: dict[SourceState, set[SourceState]] = {
    SourceState.WISHED: {SourceState.ACTIVE, SourceState.INACTIVE},
    SourceState.ACTIVE: {SourceState.INACTIVE},
    SourceState.INACTIVE: {SourceState.ACTIVE},
}


class SqliteSourceStore(SourceStore):
    """SQLite-backed source registry implementing SourceStore."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def ensure_tables(self) -> None:
        """Create source-owned tables if they do not yet exist."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS source_registry (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'global',
                state TEXT NOT NULL,
                kind TEXT,
                fetch_method TEXT,
                config_json TEXT,
                enrich INTEGER,
                refreshable INTEGER,
                priority INTEGER NOT NULL DEFAULT 0,
                expected_kind TEXT,
                expected_fetch_method TEXT,
                reason TEXT NOT NULL DEFAULT '',
                health TEXT NOT NULL DEFAULT 'unknown',
                last_refreshed_at TEXT,
                last_checked_at TEXT,
                last_error TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_source_registry_name_scope ON source_registry(name, scope)"
        )
        self._conn.commit()

    def register_source(self, request: SourceRegistration) -> SourceRecord:
        """Persist and return a configured source in ACTIVE state."""
        if request.kind != request.config.kind:
            raise ValueError(_KIND_MISMATCH_ERROR)

        now = self._now_iso()
        existing_wish = self._get_row_by_name_scope(request.name, request.scope, SourceState.WISHED)
        source_id = existing_wish["id"] if existing_wish is not None else uuid4().hex

        if existing_wish is not None:
            self._conn.execute("DELETE FROM source_registry WHERE id = ?", (source_id,))

        self._conn.execute(
            """
            INSERT INTO source_registry (
                id, name, scope, state, kind, fetch_method, config_json,
                enrich, refreshable, priority, expected_kind, expected_fetch_method,
                reason, health, last_refreshed_at, last_checked_at, last_error,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, '', ?, NULL, NULL, NULL, ?, ?, ?)
            """,
            (
                source_id,
                request.name,
                request.scope,
                SourceState.ACTIVE.value,
                request.kind.value,
                request.fetch_method.value,
                self._config_to_json(request.config),
                int(request.enrich),
                int(request.refreshable),
                request.priority,
                SourceHealth.UNKNOWN.value,
                json.dumps(request.metadata),
                now,
                now,
            ),
        )
        self._conn.commit()
        return self._require_source(source_id)

    def register_wish(self, request: SourceWish) -> SourceRecord:
        """Persist and return a wished source record."""
        active_conflict = self._get_row_by_name_scope(request.name, request.scope, SourceState.ACTIVE)
        if active_conflict is not None:
            msg = f"ACTIVE source already exists for {request.name!r} in scope {request.scope!r}"
            raise ValueError(msg)

        existing = self._get_row_by_name_scope_any(request.name, request.scope)
        now = self._now_iso()
        source_id = existing["id"] if existing is not None else uuid4().hex
        if existing is not None:
            self._conn.execute("DELETE FROM source_registry WHERE id = ?", (source_id,))

        self._conn.execute(
            """
            INSERT INTO source_registry (
                id, name, scope, state, kind, fetch_method, config_json,
                enrich, refreshable, priority, expected_kind, expected_fetch_method,
                reason, health, last_refreshed_at, last_checked_at, last_error,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, 0, ?, ?, ?, 'unknown', NULL, NULL, NULL, ?, ?, ?)
            """,
            (
                source_id,
                request.name,
                request.scope,
                SourceState.WISHED.value,
                request.expected_kind.value if request.expected_kind else None,
                request.expected_fetch_method.value if request.expected_fetch_method else None,
                request.reason,
                json.dumps(request.metadata),
                now,
                now,
            ),
        )
        self._conn.commit()
        return self._require_source(source_id)

    def get_source(self, source_id: str) -> SourceRecord | None:
        """Return a source by id, or None when unknown."""
        row = self._get_row_by_id(source_id)
        if row is None:
            return None
        return self._row_to_record(row)

    def list_sources(
        self,
        *,
        scope: str | None = None,
        state: SourceState | None = None,
    ) -> tuple[SourceRecord, ...]:
        """List source records, optionally filtered by scope and state."""
        where: list[str] = []
        params: list[str] = []
        if scope is not None:
            where.append("scope = ?")
            params.append(scope)
        if state is not None:
            where.append("state = ?")
            params.append(state.value)

        sql = "SELECT * FROM source_registry"
        if where:
            sql += " WHERE " + " AND ".join(where)

        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return tuple(self._row_to_record(row) for row in rows)

    def update_source(self, source_id: str, update: SourceUpdate) -> SourceRecord:  # noqa: C901,PLR0912
        """Update a source and return the persisted record."""
        row = self._get_row_by_id(source_id)
        if row is None:
            msg = f"source {source_id!r} not found"
            raise LookupError(msg)

        values = dict(row)
        next_state = SourceState(values["state"])
        if update.state is not None and update.state != next_state:
            allowed = _VALID_STATE_TRANSITIONS.get(next_state, set())
            if update.state not in allowed:
                msg = f"invalid state transition: {next_state.value} -> {update.state.value}"
                raise ValueError(msg)
            values["state"] = update.state.value
            next_state = update.state

        if update.scope is not None:
            values["scope"] = update.scope
        if update.priority is not None:
            values["priority"] = update.priority
        if update.reason is not None:
            values["reason"] = update.reason
        if update.last_refreshed_at is not None:
            values["last_refreshed_at"] = update.last_refreshed_at.isoformat()
        if update.metadata is not None:
            existing = self._metadata_from_json(values["metadata_json"])
            values["metadata_json"] = json.dumps({**existing, **update.metadata})

        if update.config is not None:
            values["config_json"] = self._config_to_json(update.config)
            values["kind"] = update.config.kind.value

        if next_state in {SourceState.ACTIVE, SourceState.INACTIVE}:
            self._ensure_configured_shape(values, update)
            if update.enrich is not None:
                values["enrich"] = int(update.enrich)
            elif values["enrich"] is None:
                values["enrich"] = 0
            if update.refreshable is not None:
                values["refreshable"] = int(update.refreshable)
            elif values["refreshable"] is None:
                values["refreshable"] = 1
            if values["health"] is None:
                values["health"] = SourceHealth.UNKNOWN.value
        else:
            # Keep wished rows shape-safe.
            values["kind"] = None
            values["fetch_method"] = None
            values["config_json"] = None
            values["enrich"] = None
            values["refreshable"] = None

        values["updated_at"] = self._now_iso()
        self._conn.execute(
            """
            UPDATE source_registry
            SET state = ?, kind = ?, fetch_method = ?, config_json = ?,
                enrich = ?, refreshable = ?, priority = ?, expected_kind = ?,
                expected_fetch_method = ?, reason = ?, health = ?,
                last_refreshed_at = ?, last_checked_at = ?, last_error = ?,
                metadata_json = ?, scope = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                values["state"],
                values["kind"],
                values["fetch_method"],
                values["config_json"],
                values["enrich"],
                values["refreshable"],
                values["priority"],
                values["expected_kind"],
                values["expected_fetch_method"],
                values["reason"],
                values["health"],
                values["last_refreshed_at"],
                values["last_checked_at"],
                values["last_error"],
                values["metadata_json"],
                values["scope"],
                values["updated_at"],
                source_id,
            ),
        )
        self._conn.commit()
        return self._require_source(source_id)

    def record_health(self, source_id: str, report: SourceHealthReport) -> SourceRecord:
        """Persist health information on the source row."""
        existing = self._get_row_by_id(source_id)
        if existing is None:
            msg = f"source {source_id!r} not found"
            raise LookupError(msg)

        self._conn.execute(
            """
            UPDATE source_registry
            SET health = ?, last_checked_at = ?, last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                report.health.value,
                report.checked_at.isoformat(),
                report.message if report.health != SourceHealth.OK else None,
                self._now_iso(),
                source_id,
            ),
        )
        self._conn.commit()
        return self._require_source(source_id)

    def delete_source(self, source_id: str, *, reason: str | None = None) -> SourceDeletionInfo:
        """Delete a source and return preserved deletion context."""
        record = self.get_source(source_id)
        if record is None:
            msg = f"source {source_id!r} not found"
            raise LookupError(msg)

        deleted_at = datetime.now(tz=UTC)
        self._conn.execute("DELETE FROM source_registry WHERE id = ?", (source_id,))
        self._conn.commit()
        return SourceDeletionInfo(
            source_id=source_id,
            source_name=record.name,
            scope=record.scope,
            deleted_at=deleted_at,
            reason=reason,
        )

    def stats(self) -> SourceStats:
        """Return aggregate source counts by state."""
        rows = self._conn.execute("SELECT state, COUNT(*) FROM source_registry GROUP BY state").fetchall()
        counts = dict(rows)
        return SourceStats(
            total=sum(counts.values()),
            active=int(counts.get(SourceState.ACTIVE.value, 0)),
            inactive=int(counts.get(SourceState.INACTIVE.value, 0)),
            wished=int(counts.get(SourceState.WISHED.value, 0)),
        )

    def _get_row_by_id(self, source_id: str) -> sqlite3.Row | None:
        self._conn.row_factory = sqlite3.Row
        return self._conn.execute(
            "SELECT * FROM source_registry WHERE id = ?",
            (source_id,),
        ).fetchone()

    def _get_row_by_name_scope(
        self,
        name: str,
        scope: str,
        state: SourceState,
    ) -> sqlite3.Row | None:
        self._conn.row_factory = sqlite3.Row
        return self._conn.execute(
            "SELECT * FROM source_registry WHERE name = ? AND scope = ? AND state = ?",
            (name, scope, state.value),
        ).fetchone()

    def _get_row_by_name_scope_any(self, name: str, scope: str) -> sqlite3.Row | None:
        self._conn.row_factory = sqlite3.Row
        return self._conn.execute(
            "SELECT * FROM source_registry WHERE name = ? AND scope = ?",
            (name, scope),
        ).fetchone()

    def _require_source(self, source_id: str) -> SourceRecord:
        record = self.get_source(source_id)
        if record is None:
            msg = f"source {source_id!r} not found"
            raise LookupError(msg)
        return record

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=UTC).isoformat()

    @staticmethod
    def _config_to_json(config: SourceConfig) -> str:
        return _CONFIG_ADAPTER.dump_json(config).decode("utf-8")

    @staticmethod
    def _metadata_from_json(raw: str | None) -> dict[str, object]:
        if not raw:
            return {}
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return {}

    @staticmethod
    def _parse_dt(raw: str | None) -> datetime | None:
        if raw is None:
            return None
        return datetime.fromisoformat(raw)

    def _row_to_record(self, row: sqlite3.Row) -> SourceRecord:
        state = SourceState(row["state"])
        metadata = self._metadata_from_json(row["metadata_json"])
        if state == SourceState.WISHED:
            return WishedSourceRecord(
                id=row["id"],
                name=row["name"],
                scope=row["scope"],
                priority=int(row["priority"]),
                state=SourceState.WISHED,
                expected_kind=SourceKind(row["expected_kind"]) if row["expected_kind"] else None,
                expected_fetch_method=(
                    FetchTransport(row["expected_fetch_method"]) if row["expected_fetch_method"] else None
                ),
                reason=row["reason"] or "",
                last_refreshed_at=self._parse_dt(row["last_refreshed_at"]),
                last_checked_at=self._parse_dt(row["last_checked_at"]),
                last_error=row["last_error"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=metadata,
            )

        config_raw = row["config_json"]
        if config_raw is None:
            msg = f"configured source {row['id']!r} missing config"
            raise ValueError(msg)

        return ConfiguredSourceRecord(
            id=row["id"],
            name=row["name"],
            scope=row["scope"],
            priority=int(row["priority"]),
            state=state,
            kind=SourceKind(row["kind"]),
            fetch_method=FetchTransport(row["fetch_method"]),
            health=SourceHealth(row["health"]),
            config=_CONFIG_ADAPTER.validate_json(config_raw),
            enrich=bool(row["enrich"]),
            refreshable=bool(row["refreshable"]),
            last_refreshed_at=self._parse_dt(row["last_refreshed_at"]),
            last_checked_at=self._parse_dt(row["last_checked_at"]),
            last_error=row["last_error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=metadata,
        )

    def _ensure_configured_shape(self, values: dict[str, object], update: SourceUpdate) -> None:
        if values["kind"] is None:
            expected_kind = values["expected_kind"]
            kind = SourceKind(expected_kind) if expected_kind else SourceKind.INLINE
            values["kind"] = kind.value
        else:
            kind = SourceKind(str(values["kind"]))

        if values["fetch_method"] is None:
            expected_method = values["expected_fetch_method"]
            method = FetchTransport(expected_method) if expected_method else FetchTransport.NONE
            values["fetch_method"] = method.value

        if values["config_json"] is None:
            config = update.config if update.config is not None else InlineConfig()
            values["config_json"] = self._config_to_json(config)
            values["kind"] = config.kind.value
