"""Tests for SourceStore protocol — last_refreshed_at write path (task #1884).

AC1: SourceUpdate accepts ``last_refreshed_at: datetime | None = None`` field.
AC2: SqliteSourceStore.update_source persists last_refreshed_at as ISO string when non-None.
AC3: update_source(id, SourceUpdate(last_refreshed_at=now)) returns record with matching value.
AC4: update_source with unrelated fields preserves existing last_refreshed_at (no clobber).

Target:
    owlbear_knowledge.protocols.sources.SourceUpdate
    owlbear_knowledge.stores.sources.SqliteSourceStore.update_source
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from owlbear_knowledge.protocols.sources import (
    FetchTransport,
    FileGlobConfig,
    SourceKind,
    SourceRegistration,
    SourceState,
    SourceUpdate,
)
from owlbear_knowledge.stores.sources import SqliteSourceStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


@pytest.fixture
def store(conn: sqlite3.Connection) -> SqliteSourceStore:
    s = SqliteSourceStore(conn)
    s.ensure_tables()
    return s


def _file_registration(name: str = "docs") -> SourceRegistration:
    return SourceRegistration(
        name=name,
        kind=SourceKind.FILE_GLOB,
        fetch_method=FetchTransport.FILESYSTEM,
        config=FileGlobConfig(patterns=("**/*.md",)),
    )


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# AC1: SourceUpdate model has last_refreshed_at field
# ---------------------------------------------------------------------------


class TestFromAC_SourceUpdateField:
    def test_source_update_accepts_last_refreshed_at(self) -> None:
        """SourceUpdate must accept last_refreshed_at keyword argument."""
        now = _now()
        # ValidationError if field is absent (extra="forbid" on BoundaryModel)
        update = SourceUpdate(last_refreshed_at=now)
        assert update.last_refreshed_at == now

    def test_source_update_last_refreshed_at_defaults_to_none(self) -> None:
        """Omitting last_refreshed_at yields None (field is optional)."""
        update = SourceUpdate()
        # AttributeError if the field doesn't exist on the model
        assert update.last_refreshed_at is None

    def test_source_update_accepts_none_explicitly(self) -> None:
        """Passing last_refreshed_at=None explicitly is valid and round-trips."""
        # ValidationError if field absent (extra="forbid")
        update = SourceUpdate(last_refreshed_at=None)
        assert update.last_refreshed_at is None


# ---------------------------------------------------------------------------
# AC2 + AC3: update_source persists last_refreshed_at
# ---------------------------------------------------------------------------


class TestFromAC_UpdateSourceRefreshTimestamp:
    def test_update_source_persists_last_refreshed_at(
        self, store: SqliteSourceStore
    ) -> None:
        """update_source with last_refreshed_at returns record with matching timestamp."""
        source = store.register_source(_file_registration())
        now = _now()
        result = store.update_source(source.id, SourceUpdate(last_refreshed_at=now))
        assert result.last_refreshed_at is not None
        assert result.last_refreshed_at.isoformat() == now.isoformat()

    def test_get_source_reflects_last_refreshed_at_after_update(
        self, store: SqliteSourceStore
    ) -> None:
        """Persisted last_refreshed_at survives a round-trip through get_source."""
        source = store.register_source(_file_registration())
        now = _now()
        store.update_source(source.id, SourceUpdate(last_refreshed_at=now))
        reloaded = store.get_source(source.id)
        assert reloaded is not None
        assert reloaded.last_refreshed_at is not None
        assert reloaded.last_refreshed_at.isoformat() == now.isoformat()

    def test_last_refreshed_at_overwrites_previous_value(
        self, store: SqliteSourceStore
    ) -> None:
        """A second update replaces the first last_refreshed_at value."""
        source = store.register_source(_file_registration())
        first = datetime(2026, 1, 1, tzinfo=UTC)
        second = datetime(2026, 6, 15, 12, 30, 0, tzinfo=UTC)
        store.update_source(source.id, SourceUpdate(last_refreshed_at=first))
        result = store.update_source(source.id, SourceUpdate(last_refreshed_at=second))
        assert result.last_refreshed_at is not None
        assert result.last_refreshed_at.isoformat() == second.isoformat()

    def test_last_refreshed_at_microsecond_precision_preserved(
        self, store: SqliteSourceStore
    ) -> None:
        """ISO format round-trip preserves microsecond precision."""
        source = store.register_source(_file_registration())
        ts = datetime(2026, 5, 26, 10, 30, 45, 123456, tzinfo=UTC)
        result = store.update_source(source.id, SourceUpdate(last_refreshed_at=ts))
        assert result.last_refreshed_at is not None
        assert result.last_refreshed_at == ts

    def test_update_source_returns_datetime_not_string(
        self, store: SqliteSourceStore
    ) -> None:
        """last_refreshed_at on the returned record is a datetime object, not a string."""
        source = store.register_source(_file_registration())
        now = _now()
        result = store.update_source(source.id, SourceUpdate(last_refreshed_at=now))
        assert isinstance(result.last_refreshed_at, datetime)


# ---------------------------------------------------------------------------
# AC4: update_source with unrelated fields preserves existing last_refreshed_at
# ---------------------------------------------------------------------------


class TestFromAC_NoRefreshClobber:
    def test_state_update_preserves_last_refreshed_at(
        self, store: SqliteSourceStore
    ) -> None:
        """Updating only state does not clobber an existing last_refreshed_at."""
        source = store.register_source(_file_registration())
        now = _now()
        store.update_source(source.id, SourceUpdate(last_refreshed_at=now))
        # Transition to INACTIVE — last_refreshed_at must survive
        result = store.update_source(source.id, SourceUpdate(state=SourceState.INACTIVE))
        assert result.last_refreshed_at is not None
        assert result.last_refreshed_at.isoformat() == now.isoformat()

    def test_priority_update_preserves_last_refreshed_at(
        self, store: SqliteSourceStore
    ) -> None:
        """Updating only priority does not clobber an existing last_refreshed_at."""
        source = store.register_source(_file_registration())
        now = _now()
        store.update_source(source.id, SourceUpdate(last_refreshed_at=now))
        result = store.update_source(source.id, SourceUpdate(priority=7))
        assert result.last_refreshed_at is not None
        assert result.last_refreshed_at.isoformat() == now.isoformat()

    def test_scope_update_preserves_last_refreshed_at(
        self, store: SqliteSourceStore
    ) -> None:
        """Updating only scope does not clobber an existing last_refreshed_at."""
        source = store.register_source(_file_registration())
        now = _now()
        store.update_source(source.id, SourceUpdate(last_refreshed_at=now))
        result = store.update_source(source.id, SourceUpdate(scope="team"))
        assert result.last_refreshed_at is not None
        assert result.last_refreshed_at.isoformat() == now.isoformat()

    def test_none_last_refreshed_at_does_not_clobber_existing(
        self, store: SqliteSourceStore
    ) -> None:
        """SourceUpdate with last_refreshed_at=None must not overwrite an existing timestamp."""
        source = store.register_source(_file_registration())
        now = _now()
        store.update_source(source.id, SourceUpdate(last_refreshed_at=now))
        # Explicit None — must be treated as "no change", not "clear"
        result = store.update_source(source.id, SourceUpdate(last_refreshed_at=None))
        assert result.last_refreshed_at is not None
        assert result.last_refreshed_at.isoformat() == now.isoformat()
