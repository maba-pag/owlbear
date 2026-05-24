"""Tests for task #1651: two-field timestamp model (last_checked_at).

AC-1: KnowledgeSource model field, DDL, schema version, migration, store CRUD.
AC-2: _update_source_record refreshed/partial > 0 → bumps both timestamps.
AC-3: _update_source_record skipped/failed only → last_checked_at only, preserves last_refreshed_at.
AC-4: _update_source_record all counters zero → no store update.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


def _make_source(**overrides: object) -> KnowledgeSource:
    """Build a minimal KnowledgeSource with sensible defaults."""
    base: dict[str, object] = {
        "id": "src-test",
        "name": "Test Source",
        "source_type": SourceType.URL_LIST,
        "fetch_method": "http",
        "config": {},
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return KnowledgeSource(**base)


class _SpyStore:
    """Minimal store stub that records update() calls."""

    def __init__(self) -> None:
        self.updated: KnowledgeSource | None = None
        self.update_call_count: int = 0

    def update(self, source: KnowledgeSource) -> None:
        self.updated = source
        self.update_call_count += 1


class _StubPipeline:
    """Empty pipeline stub — _update_source_record does not call pipeline."""


class _AsyncIngestPipeline:
    """Async pipeline stub that records refresh intake calls."""

    def __init__(self) -> None:
        self.calls: list[object] = []

    async def ingest(self, intake_result: object, *, scope: str, source_id: str | None = None) -> object:
        self.calls.append((intake_result, scope, source_id))
        return SimpleNamespace(status="ok", document_id="doc-test")


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(conn)
    return conn


def _v13_conn() -> sqlite3.Connection:
    """Return a raw v13-schema DB without last_checked_at column."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE knowledge_sources (
            id                TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            source_type       TEXT NOT NULL,
            fetch_method      TEXT NOT NULL DEFAULT '',
            enrich            INTEGER NOT NULL DEFAULT 0,
            config            TEXT NOT NULL,
            scope             TEXT DEFAULT 'global',
            enabled           INTEGER DEFAULT 1,
            priority          INTEGER DEFAULT 0,
            last_refreshed_at TEXT,
            last_error        TEXT,
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
    conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (13, '2026-01-01')")
    return conn


# ---------------------------------------------------------------------------
# AC-1: Model field, DDL, schema version, migration, store CRUD
# ---------------------------------------------------------------------------


class TestFromAC_SchemaAndModel:
    def test_model_has_last_checked_at_field_default_none(self) -> None:
        """KnowledgeSource.last_checked_at exists and defaults to None."""
        source = _make_source()
        assert source.last_checked_at is None  # AttributeError until field added

    def test_model_accepts_last_checked_at_timestamp_value(self) -> None:
        """KnowledgeSource accepts a non-None last_checked_at string."""
        ts = "2026-05-01T12:00:00+00:00"
        source = _make_source(last_checked_at=ts)  # ValidationError until field added
        assert source.last_checked_at == ts

    def test_ddl_includes_last_checked_at_column(self) -> None:
        """Fresh init_db creates knowledge_sources with last_checked_at column."""
        conn = _make_db()
        columns = [row[1] for row in conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()]
        assert "last_checked_at" in columns

    def test_schema_version_is_14(self) -> None:
        """_SCHEMA_VERSION constant is bumped to 15."""
        import owlbear_knowledge.schema as _schema  # noqa: PLC0415

        assert _schema._SCHEMA_VERSION == 15  # noqa: SLF001

    def test_migrate_v13_to_v14_is_defined(self) -> None:
        """_migrate_v13_to_v14 function exists on the schema module."""
        import owlbear_knowledge.schema as _schema  # noqa: PLC0415

        assert hasattr(_schema, "_migrate_v13_to_v14")  # AttributeError until defined

    def test_migrate_v13_to_v14_adds_last_checked_at_column(self) -> None:
        """_migrate_v13_to_v14 ALTERs existing table to add last_checked_at TEXT."""
        import owlbear_knowledge.schema as _schema  # noqa: PLC0415

        migrate = _schema._migrate_v13_to_v14  # AttributeError until defined  # noqa: SLF001
        conn = _v13_conn()

        migrate(conn)

        cols = [row[1] for row in conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()]
        assert "last_checked_at" in cols

    def test_migrate_v13_to_v14_updates_schema_version_to_14(self) -> None:
        """_migrate_v13_to_v14 writes version=14 to schema_version table."""
        import owlbear_knowledge.schema as _schema  # noqa: PLC0415

        migrate = _schema._migrate_v13_to_v14  # noqa: SLF001
        conn = _v13_conn()

        migrate(conn)

        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        assert version == 14

    def test_apply_migrations_runs_v14_migration_from_v13(self) -> None:
        """_apply_migrations(conn, current=13) applies _migrate_v13_to_v14."""
        import owlbear_knowledge.schema as _schema  # noqa: PLC0415

        conn = _v13_conn()
        _schema._apply_migrations(conn, current=13)  # noqa: SLF001

        cols = [row[1] for row in conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()]
        assert "last_checked_at" in cols

    def test_select_cols_contains_last_checked_at(self) -> None:
        """_SELECT_COLS string includes last_checked_at."""
        assert "last_checked_at" in KnowledgeSourceStore._SELECT_COLS  # noqa: SLF001

    def test_select_cols_last_checked_at_at_index_13(self) -> None:
        """last_checked_at is at column index 14 after refreshable was added."""
        cols = [c.strip() for c in KnowledgeSourceStore._SELECT_COLS.split(",")]  # noqa: SLF001
        assert len(cols) >= 15
        assert cols[14] == "last_checked_at"

    def test_store_create_persists_last_checked_at_value(self) -> None:
        """create() writes last_checked_at to the DB."""
        conn = _make_db()
        store = KnowledgeSourceStore(conn)
        ts = "2026-05-01T12:00:00+00:00"
        source = _make_source(last_checked_at=ts)  # ValidationError until field added
        store.create(source)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.last_checked_at == ts

    def test_store_create_persists_last_checked_at_none(self) -> None:
        """create() persists last_checked_at=None (NULL in DB)."""
        conn = _make_db()
        store = KnowledgeSourceStore(conn)
        source = _make_source()
        store.create(source)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.last_checked_at is None  # AttributeError until field mapped in _row_to_model

    def test_store_update_persists_last_checked_at(self) -> None:
        """update() writes a changed last_checked_at to the DB."""
        conn = _make_db()
        store = KnowledgeSourceStore(conn)
        source = _make_source()
        store.create(source)

        ts = "2026-05-02T08:00:00+00:00"
        updated = source.model_copy(  # fails until last_checked_at field exists
            update={"last_checked_at": ts, "updated_at": "2026-05-02T08:00:00+00:00"}
        )
        store.update(updated)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.last_checked_at == ts

    def test_store_get_round_trips_last_checked_at(self) -> None:
        """get() maps the last_checked_at column (index 13) back to the model field."""
        conn = _make_db()
        store = KnowledgeSourceStore(conn)
        ts = "2026-05-03T10:00:00+00:00"
        source = _make_source(last_checked_at=ts)  # fails until field exists
        store.create(source)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.last_checked_at == ts


# ---------------------------------------------------------------------------
# AC-2: refreshed > 0 OR partial > 0 → bumps both timestamps + last_error
# ---------------------------------------------------------------------------


class TestFromAC_UpdateSourceRecordRefreshed:
    def _orch(self, spy: _SpyStore) -> RefreshOrchestrator:
        return RefreshOrchestrator(store=spy, pipeline=_StubPipeline())

    def test_refreshed_positive_bumps_last_checked_at(self) -> None:
        """refreshed=1 → last_checked_at is set to a recent UTC timestamp."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(source_id="src-test", refreshed=1, skipped=0, failed=0)

        before = datetime.now(tz=UTC)
        orch._update_source_record(source, result)  # noqa: SLF001
        after = datetime.now(tz=UTC)

        assert spy.updated is not None
        checked = datetime.fromisoformat(spy.updated.last_checked_at)  # AttributeError until field added
        assert before <= checked <= after

    def test_refreshed_positive_bumps_last_refreshed_at(self) -> None:
        """refreshed=1 → last_refreshed_at is bumped to a recent UTC timestamp."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(source_id="src-test", refreshed=1, skipped=0, failed=0)

        before = datetime.now(tz=UTC)
        orch._update_source_record(source, result)  # noqa: SLF001
        after = datetime.now(tz=UTC)

        # Also verify last_checked_at is set (AC-2 requires both)
        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        refreshed = datetime.fromisoformat(spy.updated.last_refreshed_at)
        assert before <= refreshed <= after

    def test_partial_positive_bumps_last_checked_at(self) -> None:
        """partial=1, refreshed=0 → last_checked_at bumped (AC-2 path)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(source_id="src-test", refreshed=0, partial=1, skipped=0, failed=0)

        before = datetime.now(tz=UTC)
        orch._update_source_record(source, result)  # noqa: SLF001
        after = datetime.now(tz=UTC)

        assert spy.updated is not None
        checked = datetime.fromisoformat(spy.updated.last_checked_at)  # AttributeError until field added
        assert before <= checked <= after

    def test_partial_positive_bumps_last_refreshed_at(self) -> None:
        """partial=1, refreshed=0 → last_refreshed_at is also bumped (AC-2 path)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(source_id="src-test", refreshed=0, partial=1, skipped=0, failed=0)

        before = datetime.now(tz=UTC)
        orch._update_source_record(source, result)  # noqa: SLF001
        after = datetime.now(tz=UTC)

        # last_checked_at must also be set (ensures both are bumped)
        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        refreshed = datetime.fromisoformat(spy.updated.last_refreshed_at)
        assert before <= refreshed <= after

    def test_partial_positive_clears_last_error_when_no_messages(self) -> None:
        """partial=1, no errors or warnings → last_error cleared to None (AC-2 path)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00+00:00",
            last_error="stale error",
        )
        result = RefreshResult(source_id="src-test", refreshed=0, partial=1, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated is not None
        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error is None

    def test_partial_positive_sets_last_error_from_errors_and_warnings(self) -> None:
        """partial=1, errors=['e1'] warnings=['w1'] → last_error = 'e1; w1' (AC-2 path)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(
            source_id="src-test",
            refreshed=0,
            partial=1,
            skipped=0,
            failed=0,
            errors=["e1"],
            warnings=["w1"],
        )

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated is not None
        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error == "e1; w1"

    def test_refreshed_clears_last_error_when_no_messages(self) -> None:
        """refreshed=1 with no errors or warnings → last_error cleared to None."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00+00:00",
            last_error="old error",
        )
        result = RefreshResult(source_id="src-test", refreshed=1, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated is not None
        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error is None

    def test_refreshed_sets_last_error_from_errors_and_warnings(self) -> None:
        """refreshed=1 with errors and warnings → last_error = joined by '; '."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(
            source_id="src-test",
            refreshed=1,
            skipped=0,
            failed=0,
            errors=["err1"],
            warnings=["warn1"],
        )

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error == "err1; warn1"

    def test_refreshed_sets_last_error_errors_only(self) -> None:
        """refreshed > 0 with multiple errors and no warnings → joined by '; '."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(
            source_id="src-test",
            refreshed=2,
            skipped=0,
            failed=0,
            errors=["e1", "e2"],
        )

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error == "e1; e2"

    def test_refreshed_sets_last_error_warnings_only(self) -> None:
        """refreshed=1 with only warnings → last_error includes warnings."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(
            source_id="src-test",
            refreshed=1,
            skipped=0,
            failed=0,
            warnings=["w1", "w2"],
        )

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error == "w1; w2"

    def test_refreshed_with_skipped_nonzero_still_takes_ac2_path(self) -> None:
        """refreshed=1, skipped=1 → AC-2 path; both timestamps bumped."""
        spy = _SpyStore()
        orch = self._orch(spy)
        old_ts = "2026-01-01T00:00:00+00:00"
        source = _make_source(last_refreshed_at=old_ts)
        result = RefreshResult(source_id="src-test", refreshed=1, skipped=1, failed=0)

        before = datetime.now(tz=UTC)
        orch._update_source_record(source, result)  # noqa: SLF001
        after = datetime.now(tz=UTC)

        assert spy.updated is not None
        checked = datetime.fromisoformat(spy.updated.last_checked_at)  # AttributeError until field added
        assert before <= checked <= after
        refreshed = datetime.fromisoformat(spy.updated.last_refreshed_at)
        assert before <= refreshed <= after


# ---------------------------------------------------------------------------
# AC-3: skipped > 0 OR failed > 0 (zero refreshed and partial)
#        → bumps last_checked_at only; preserves last_refreshed_at
# ---------------------------------------------------------------------------


class TestFromAC_UpdateSourceRecordSkippedFailed:
    def _orch(self, spy: _SpyStore) -> RefreshOrchestrator:
        return RefreshOrchestrator(store=spy, pipeline=_StubPipeline())

    def test_skipped_bumps_last_checked_at(self) -> None:
        """skipped=1, refreshed=0, partial=0 → last_checked_at bumped."""
        spy = _SpyStore()
        orch = self._orch(spy)
        old_ts = "2026-01-01T00:00:00+00:00"
        source = _make_source(last_refreshed_at=old_ts)
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=1, failed=0)

        before = datetime.now(tz=UTC)
        orch._update_source_record(source, result)  # noqa: SLF001
        after = datetime.now(tz=UTC)

        assert spy.updated is not None
        checked = datetime.fromisoformat(spy.updated.last_checked_at)  # AttributeError until field added
        assert before <= checked <= after

    def test_skipped_preserves_last_refreshed_at(self) -> None:
        """skipped=1, refreshed=0, partial=0 → last_refreshed_at is NOT changed."""
        spy = _SpyStore()
        orch = self._orch(spy)
        old_ts = "2026-01-01T00:00:00+00:00"
        source = _make_source(last_refreshed_at=old_ts)
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=1, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        # Current impl unconditionally bumps — fails until conditional logic added
        assert spy.updated.last_refreshed_at == old_ts

    def test_failed_bumps_last_checked_at(self) -> None:
        """failed=1, refreshed=0, partial=0 → last_checked_at bumped."""
        spy = _SpyStore()
        orch = self._orch(spy)
        old_ts = "2026-01-01T00:00:00+00:00"
        source = _make_source(last_refreshed_at=old_ts)
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=1, errors=["fetch error"])

        before = datetime.now(tz=UTC)
        orch._update_source_record(source, result)  # noqa: SLF001
        after = datetime.now(tz=UTC)

        assert spy.updated is not None
        checked = datetime.fromisoformat(spy.updated.last_checked_at)  # AttributeError until field added
        assert before <= checked <= after

    def test_failed_preserves_last_refreshed_at(self) -> None:
        """failed=1, refreshed=0, partial=0 → last_refreshed_at is NOT changed."""
        spy = _SpyStore()
        orch = self._orch(spy)
        old_ts = "2026-01-01T00:00:00+00:00"
        source = _make_source(last_refreshed_at=old_ts)
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=1, errors=["err"])

        orch._update_source_record(source, result)  # noqa: SLF001

        # Current impl unconditionally bumps — fails until conditional logic added
        assert spy.updated.last_refreshed_at == old_ts

    def test_failed_sets_last_error_from_errors_only(self) -> None:
        """failed=1 → last_error uses errors list only (not errors + warnings)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(
            source_id="src-test",
            refreshed=0,
            skipped=0,
            failed=1,
            errors=["network timeout", "dns error"],
        )

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error == "network timeout; dns error"

    def test_failed_excludes_warnings_from_last_error(self) -> None:
        """failed=1 with warnings → last_error contains only errors (AC-3 differs from AC-2)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(
            source_id="src-test",
            refreshed=0,
            skipped=0,
            failed=1,
            errors=["err1"],
            warnings=["warn1"],  # must NOT be included for AC-3
        )

        orch._update_source_record(source, result)  # noqa: SLF001

        # Currently impl includes warnings → last_error == "err1; warn1" — fails
        assert spy.updated.last_error == "err1"

    def test_skipped_only_clears_last_error(self) -> None:
        """skipped=1, failed=0, no errors → last_error cleared to None."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00+00:00",
            last_error="previous error",
        )
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=1, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated is not None
        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error is None

    def test_failed_without_errors_clears_last_error(self) -> None:
        """Boundary: failed=1 but errors=[] → last_error is None (no join)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00+00:00",
            last_error="stale error",
        )
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=1, errors=[])

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.updated is not None
        assert spy.updated.last_checked_at is not None  # AttributeError until field added
        assert spy.updated.last_error is None

    def test_skipped_and_failed_both_nonzero_is_ac3_path(self) -> None:
        """skipped=1, failed=1, refreshed=0, partial=0 → AC-3 path, preserves last_refreshed_at."""
        spy = _SpyStore()
        orch = self._orch(spy)
        old_ts = "2026-01-01T00:00:00+00:00"
        source = _make_source(last_refreshed_at=old_ts)
        result = RefreshResult(
            source_id="src-test",
            refreshed=0,
            skipped=1,
            failed=1,
            errors=["err"],
        )

        orch._update_source_record(source, result)  # noqa: SLF001

        # AC-3: last_refreshed_at preserved; last_checked_at bumped
        assert spy.updated.last_refreshed_at == old_ts  # fails until conditional logic added
        assert spy.updated.last_checked_at is not None  # fails until field added


# ---------------------------------------------------------------------------
# AC-4: all counters zero → no store update whatsoever
# ---------------------------------------------------------------------------


class TestFromAC_UpdateSourceRecordAllZero:
    def _orch(self, spy: _SpyStore) -> RefreshOrchestrator:
        return RefreshOrchestrator(store=spy, pipeline=_StubPipeline())

    def test_all_zero_performs_no_store_update(self) -> None:
        """All counters zero → store.update() is never called."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00+00:00",
            last_error="old error",
        )
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        # Currently always calls update — fails until conditional logic added
        assert spy.update_call_count == 0

    def test_all_zero_last_checked_at_unchanged(self) -> None:
        """All counters zero → last_checked_at is not written."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.update_call_count == 0  # fails until logic added
        assert spy.updated is None

    def test_all_zero_last_refreshed_at_unchanged(self) -> None:
        """All counters zero → last_refreshed_at is not written."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.update_call_count == 0  # fails until logic added
        assert spy.updated is None

    def test_all_zero_last_error_unchanged(self) -> None:
        """All counters zero → last_error is not written (even if non-None on source)."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00+00:00",
            last_error="pre-existing error",
        )
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.update_call_count == 0  # fails until logic added
        assert spy.updated is None

    def test_all_zero_updated_at_unchanged(self) -> None:
        """All counters zero → updated_at is not written."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(
            last_refreshed_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        result = RefreshResult(source_id="src-test", refreshed=0, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.update_call_count == 0  # fails until logic added
        assert spy.updated is None

    def test_all_zero_with_partial_zero_explicit(self) -> None:
        """Boundary: partial=0 explicit alongside all other zeros → still no update."""
        spy = _SpyStore()
        orch = self._orch(spy)
        source = _make_source(last_refreshed_at="2026-01-01T00:00:00+00:00")
        result = RefreshResult(source_id="src-test", refreshed=0, partial=0, skipped=0, failed=0)

        orch._update_source_record(source, result)  # noqa: SLF001

        assert spy.update_call_count == 0  # fails until logic added


# ---------------------------------------------------------------------------
# URL configuration compatibility
# ---------------------------------------------------------------------------


class TestFromAC_RefreshUrlConfig:
    def test_refresh_accepts_comma_separated_urls_string(self) -> None:
        """Refresh should parse persisted config.urls strings the same way source lookup does."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.md"
            second = root / "second.md"
            first.write_text("# First\n")
            second.write_text("# Second\n")

            pipeline = _AsyncIngestPipeline()
            spy = _SpyStore()
            source = _make_source(
                source_type=SourceType.AUTHENTICATED_WEB,
                fetch_method="browser",
                config={"urls": f"{first}, {second}"},
            )
            result = asyncio.run(
                RefreshOrchestrator(
                    store=spy,
                    pipeline=pipeline,
                    workspace_root=root,
                ).refresh(source)
            )

        assert result.refreshed == 2
        assert result.failed == 0
        assert result.errors == []
        assert len(pipeline.calls) == 2
        assert spy.updated is not None
        assert spy.updated.last_checked_at is not None


class TestFromAC_RefreshFileGlobConfig:
    def test_refresh_reports_missing_file_glob_pattern(self) -> None:
        """Refresh should fail malformed file_glob sources instead of broadening to '*'."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs_dir = root / "docs"
            docs_dir.mkdir()
            (docs_dir / "one.md").write_text("# One\n")
            (docs_dir / "two.txt").write_text("Two\n")

            pipeline = _AsyncIngestPipeline()
            spy = _SpyStore()
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                fetch_method="file",
                config={"base_dir": "docs"},
            )
            result = asyncio.run(
                RefreshOrchestrator(
                    store=spy,
                    pipeline=pipeline,
                    workspace_root=root,
                ).refresh(source)
            )

        assert result.refreshed == 0
        assert result.failed == 1
        assert result.errors == ["source has no glob pattern configured"]
        assert pipeline.calls == []
        assert spy.updated is not None
        assert spy.updated.last_error == "source has no glob pattern configured"
