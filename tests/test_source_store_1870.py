"""Tests for SqliteSourceStore — AC-derived RED-phase suite (task #1870).

Target: ``owlbear_knowledge.stores.sources.SqliteSourceStore``
Protocol: ``owlbear_knowledge.protocols.sources.SourceStore``
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    FileGlobConfig,
    InlineConfig,
    SourceHealth,
    SourceHealthReport,
    SourceKind,
    SourceRegistration,
    SourceState,
    SourceUpdate,
    SourceWish,
    UrlListConfig,
    WishedSourceRecord,
)

# ---------------------------------------------------------------------------
# Import under test — ImportError if module doesn't exist (RED)
# ---------------------------------------------------------------------------

from owlbear_knowledge.stores.sources import SqliteSourceStore  # noqa: E402


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


def _file_registration(
    name: str = "my-docs",
    scope: str = "global",
) -> SourceRegistration:
    return SourceRegistration(
        name=name,
        kind=SourceKind.FILE_GLOB,
        fetch_method=FetchTransport.FILESYSTEM,
        config=FileGlobConfig(patterns=("**/*.md",)),
        scope=scope,
    )


def _url_registration(
    name: str = "web-source",
    scope: str = "global",
) -> SourceRegistration:
    return SourceRegistration(
        name=name,
        kind=SourceKind.URL_LIST,
        fetch_method=FetchTransport.HTTP,
        config=UrlListConfig(urls=("https://example.com",)),
        scope=scope,
    )


def _inline_registration(
    name: str = "inline-source",
    scope: str = "global",
) -> SourceRegistration:
    return SourceRegistration(
        name=name,
        kind=SourceKind.INLINE,
        fetch_method=FetchTransport.NONE,
        config=InlineConfig(),
        scope=scope,
    )


def _wish(
    name: str = "future-docs",
    scope: str = "global",
) -> SourceWish:
    return SourceWish(name=name, scope=scope)


def _now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# AC-1: register_source
# ---------------------------------------------------------------------------


class TestFromAC_RegisterSource:
    def test_returns_configured_source_record(self, store: SqliteSourceStore) -> None:
        result = store.register_source(_file_registration())
        assert isinstance(result, ConfiguredSourceRecord)

    def test_state_is_active(self, store: SqliteSourceStore) -> None:
        result = store.register_source(_file_registration())
        assert result.state == SourceState.ACTIVE

    def test_fields_match_registration(self, store: SqliteSourceStore) -> None:
        reg = _file_registration(name="my-docs", scope="project")
        result = store.register_source(reg)
        assert result.name == "my-docs"
        assert result.scope == "project"
        assert result.kind == SourceKind.FILE_GLOB
        assert result.fetch_method == FetchTransport.FILESYSTEM

    def test_config_typed_discriminated_union_file_glob(self, store: SqliteSourceStore) -> None:
        reg = _file_registration()
        result = store.register_source(reg)
        assert isinstance(result.config, FileGlobConfig)
        assert "**/*.md" in result.config.patterns

    def test_config_typed_discriminated_union_url_list(self, store: SqliteSourceStore) -> None:
        reg = _url_registration()
        result = store.register_source(reg)
        assert isinstance(result.config, UrlListConfig)
        assert "https://example.com" in result.config.urls

    def test_config_typed_discriminated_union_inline(self, store: SqliteSourceStore) -> None:
        reg = _inline_registration()
        result = store.register_source(reg)
        assert isinstance(result.config, InlineConfig)

    def test_id_assigned_and_retrievable(self, store: SqliteSourceStore) -> None:
        result = store.register_source(_file_registration())
        assert result.id
        retrieved = store.get_source(result.id)
        assert retrieved is not None
        assert retrieved.id == result.id

    def test_supersedes_wished_source_same_name_scope(self, store: SqliteSourceStore) -> None:
        wish = store.register_wish(SourceWish(name="my-docs", scope="global"))
        wish_id = wish.id
        result = store.register_source(_file_registration(name="my-docs", scope="global"))
        assert isinstance(result, ConfiguredSourceRecord)
        assert result.state == SourceState.ACTIVE
        # the old WISHED record must no longer exist as a separate entry
        old = store.get_source(wish_id)
        assert old is None or (old.id == result.id)

    def test_supersedes_wish_only_same_name_and_scope(self, store: SqliteSourceStore) -> None:
        wish = store.register_wish(SourceWish(name="my-docs", scope="other"))
        store.register_source(_file_registration(name="my-docs", scope="global"))
        # wish in different scope must survive
        surviving = store.get_source(wish.id)
        assert surviving is not None
        assert surviving.state == SourceState.WISHED

    def test_multiple_sources_different_names(self, store: SqliteSourceStore) -> None:
        a = store.register_source(_file_registration(name="a"))
        b = store.register_source(_url_registration(name="b"))
        assert a.id != b.id
        assert store.get_source(a.id) is not None
        assert store.get_source(b.id) is not None

    def test_raises_valueerror_on_kind_config_mismatch(self, store: SqliteSourceStore) -> None:
        mismatch = SourceRegistration(
            name="mismatch-source",
            kind=SourceKind.URL_LIST,
            fetch_method=FetchTransport.HTTP,
            config=FileGlobConfig(patterns=("**/*.md",)),
            scope="global",
        )
        with pytest.raises(ValueError):
            store.register_source(mismatch)

    def test_mismatch_does_not_persist(self, store: SqliteSourceStore) -> None:
        mismatch = SourceRegistration(
            name="mismatch-source",
            kind=SourceKind.URL_LIST,
            fetch_method=FetchTransport.HTTP,
            config=FileGlobConfig(patterns=("**/*.md",)),
            scope="global",
        )
        with pytest.raises(ValueError):
            store.register_source(mismatch)
        assert store.list_sources() == ()


# ---------------------------------------------------------------------------
# AC-2: register_wish
# ---------------------------------------------------------------------------


class TestFromAC_RegisterWish:
    def test_returns_wished_source_record(self, store: SqliteSourceStore) -> None:
        result = store.register_wish(_wish())
        assert isinstance(result, WishedSourceRecord)

    def test_state_is_wished(self, store: SqliteSourceStore) -> None:
        result = store.register_wish(_wish())
        assert result.state == SourceState.WISHED

    def test_fields_match_wish(self, store: SqliteSourceStore) -> None:
        w = SourceWish(name="future-docs", scope="project", reason="needed soon")
        result = store.register_wish(w)
        assert result.name == "future-docs"
        assert result.scope == "project"

    def test_expected_kind_optional_cp24(self, store: SqliteSourceStore) -> None:
        w = SourceWish(name="no-kind", expected_kind=None)
        result = store.register_wish(w)
        assert isinstance(result, WishedSourceRecord)
        assert result.expected_kind is None

    def test_expected_fetch_method_optional_cp24(self, store: SqliteSourceStore) -> None:
        w = SourceWish(name="no-method", expected_fetch_method=None)
        result = store.register_wish(w)
        assert isinstance(result, WishedSourceRecord)
        assert result.expected_fetch_method is None

    def test_expected_kind_stored_when_given(self, store: SqliteSourceStore) -> None:
        w = SourceWish(name="typed-wish", expected_kind=SourceKind.URL_LIST)
        result = store.register_wish(w)
        assert isinstance(result, WishedSourceRecord)
        assert result.expected_kind == SourceKind.URL_LIST

    def test_raises_value_error_when_active_source_same_name_scope(
        self, store: SqliteSourceStore
    ) -> None:
        store.register_source(_file_registration(name="conflict", scope="global"))
        with pytest.raises(ValueError):
            store.register_wish(SourceWish(name="conflict", scope="global"))

    def test_does_not_raise_for_inactive_source_same_name_scope(
        self, store: SqliteSourceStore
    ) -> None:
        # INACTIVE source — wish should NOT raise (only ACTIVE blocks)
        rec = store.register_source(_file_registration(name="sleeping", scope="global"))
        store.update_source(rec.id, SourceUpdate(state=SourceState.INACTIVE))
        # Should not raise
        result = store.register_wish(SourceWish(name="sleeping", scope="global"))
        assert isinstance(result, WishedSourceRecord)

    def test_different_scopes_are_independent(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration(name="data", scope="alpha"))
        # ACTIVE in "alpha" — wish in "beta" should succeed
        result = store.register_wish(SourceWish(name="data", scope="beta"))
        assert isinstance(result, WishedSourceRecord)

    def test_id_assigned_and_retrievable(self, store: SqliteSourceStore) -> None:
        result = store.register_wish(_wish())
        retrieved = store.get_source(result.id)
        assert retrieved is not None
        assert retrieved.id == result.id


# ---------------------------------------------------------------------------
# AC-3: list_sources
# ---------------------------------------------------------------------------


class TestFromAC_ListSources:
    def test_returns_empty_tuple_when_no_sources(self, store: SqliteSourceStore) -> None:
        result = store.list_sources()
        assert result == ()

    def test_returns_all_sources_without_filter(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration(name="a"))
        store.register_wish(SourceWish(name="b"))
        result = store.list_sources()
        assert len(result) == 2

    def test_returns_tuple(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration())
        result = store.list_sources()
        assert isinstance(result, tuple)

    def test_filters_by_scope(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration(name="proj", scope="project"))
        store.register_source(_url_registration(name="glob", scope="global"))
        result = store.list_sources(scope="project")
        assert len(result) == 1
        assert result[0].name == "proj"

    def test_filters_by_state_active(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration(name="active"))
        store.register_wish(SourceWish(name="wanted"))
        result = store.list_sources(state=SourceState.ACTIVE)
        assert all(r.state == SourceState.ACTIVE for r in result)
        assert len(result) == 1

    def test_filters_by_state_wished(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration(name="active"))
        store.register_wish(SourceWish(name="wanted"))
        result = store.list_sources(state=SourceState.WISHED)
        assert all(isinstance(r, WishedSourceRecord) for r in result)
        assert len(result) == 1

    def test_filters_by_scope_and_state_both(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration(name="p-active", scope="proj"))
        store.register_wish(SourceWish(name="p-wish", scope="proj"))
        store.register_source(_url_registration(name="g-active", scope="global"))
        result = store.list_sources(scope="proj", state=SourceState.ACTIVE)
        assert len(result) == 1
        assert result[0].name == "p-active"

    def test_returns_empty_when_no_match_for_filter(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration(scope="global"))
        result = store.list_sources(scope="nonexistent-scope")
        assert result == ()

    def test_includes_wished_and_configured_without_filter(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        wish = store.register_wish(SourceWish(name="future"))
        all_sources = store.list_sources()
        ids = {s.id for s in all_sources}
        assert rec.id in ids
        assert wish.id in ids


# ---------------------------------------------------------------------------
# AC-4: update_source
# ---------------------------------------------------------------------------


class TestFromAC_UpdateSource:
    def test_applies_only_nonnone_fields(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration(name="orig"))
        updated = store.update_source(rec.id, SourceUpdate(priority=99))
        assert isinstance(updated, ConfiguredSourceRecord)
        assert updated.priority == 99
        assert updated.name == "orig"  # unchanged

    def test_updated_at_refreshed_on_call(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        before = rec.updated_at
        updated = store.update_source(rec.id, SourceUpdate(priority=1))
        assert updated.updated_at >= before

    def test_metadata_shallow_merge_cp25(self, store: SqliteSourceStore) -> None:
        reg = SourceRegistration(
            name="meta-src",
            kind=SourceKind.FILE_GLOB,
            fetch_method=FetchTransport.FILESYSTEM,
            config=FileGlobConfig(patterns=("*.py",)),
            metadata={"key1": "old", "key2": "keep"},
        )
        rec = store.register_source(reg)
        updated = store.update_source(rec.id, SourceUpdate(metadata={"key1": "new", "key3": "added"}))
        assert isinstance(updated, ConfiguredSourceRecord)
        assert updated.metadata["key1"] == "new"
        assert updated.metadata["key2"] == "keep"
        assert updated.metadata["key3"] == "added"

    def test_valid_transition_active_to_inactive(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        updated = store.update_source(rec.id, SourceUpdate(state=SourceState.INACTIVE))
        assert updated.state == SourceState.INACTIVE

    def test_valid_transition_inactive_to_active(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.update_source(rec.id, SourceUpdate(state=SourceState.INACTIVE))
        updated = store.update_source(rec.id, SourceUpdate(state=SourceState.ACTIVE))
        assert updated.state == SourceState.ACTIVE

    def test_valid_transition_wished_to_active(self, store: SqliteSourceStore) -> None:
        wish = store.register_wish(_wish())
        updated = store.update_source(wish.id, SourceUpdate(state=SourceState.ACTIVE))
        assert updated.state == SourceState.ACTIVE

    def test_valid_transition_wished_to_inactive(self, store: SqliteSourceStore) -> None:
        wish = store.register_wish(_wish())
        updated = store.update_source(wish.id, SourceUpdate(state=SourceState.INACTIVE))
        assert updated.state == SourceState.INACTIVE

    def test_raises_lookup_error_on_unknown_id(self, store: SqliteSourceStore) -> None:
        with pytest.raises(LookupError):
            store.update_source("nonexistent-id", SourceUpdate(priority=1))

    def test_raises_value_error_active_to_wished(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        with pytest.raises(ValueError):
            store.update_source(rec.id, SourceUpdate(state=SourceState.WISHED))

    def test_raises_value_error_inactive_to_wished(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.update_source(rec.id, SourceUpdate(state=SourceState.INACTIVE))
        with pytest.raises(ValueError):
            store.update_source(rec.id, SourceUpdate(state=SourceState.WISHED))

    def test_update_persisted_get_source_reflects_change(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.update_source(rec.id, SourceUpdate(priority=42))
        retrieved = store.get_source(rec.id)
        assert retrieved is not None
        assert retrieved.priority == 42


# ---------------------------------------------------------------------------
# AC-5: delete_source
# ---------------------------------------------------------------------------


class TestFromAC_DeleteSource:
    def test_returns_source_deletion_info(self, store: SqliteSourceStore) -> None:
        from owlbear_knowledge.protocols.sources import SourceDeletionInfo
        rec = store.register_source(_file_registration())
        result = store.delete_source(rec.id)
        assert isinstance(result, SourceDeletionInfo)

    def test_deletion_info_preserves_source_id(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration(name="to-delete", scope="project"))
        result = store.delete_source(rec.id)
        assert result.source_id == rec.id

    def test_deletion_info_preserves_source_name(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration(name="to-delete", scope="project"))
        result = store.delete_source(rec.id)
        assert result.source_name == "to-delete"

    def test_deletion_info_preserves_scope(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration(name="to-delete", scope="project"))
        result = store.delete_source(rec.id)
        assert result.scope == "project"

    def test_deletion_info_has_deleted_at(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        result = store.delete_source(rec.id)
        assert isinstance(result.deleted_at, datetime)

    def test_deletion_info_preserves_reason(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        result = store.delete_source(rec.id, reason="decommissioned")
        assert result.reason == "decommissioned"

    def test_deletion_info_reason_none_by_default(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        result = store.delete_source(rec.id)
        assert result.reason is None

    def test_deleted_source_not_retrievable(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.delete_source(rec.id)
        assert store.get_source(rec.id) is None

    def test_deleted_source_not_in_list(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.delete_source(rec.id)
        result = store.list_sources()
        assert all(r.id != rec.id for r in result)

    def test_raises_lookup_error_on_missing_id(self, store: SqliteSourceStore) -> None:
        with pytest.raises(LookupError):
            store.delete_source("does-not-exist")


# ---------------------------------------------------------------------------
# AC-6: record_health
# ---------------------------------------------------------------------------


class TestFromAC_RecordHealth:
    def test_returns_source_record_with_updated_health(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        report = SourceHealthReport(health=SourceHealth.OK, checked_at=_now())
        result = store.record_health(rec.id, report)
        assert isinstance(result, ConfiguredSourceRecord)
        assert result.health == SourceHealth.OK

    def test_last_checked_at_updated(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        check_time = _now()
        report = SourceHealthReport(health=SourceHealth.DEGRADED, checked_at=check_time)
        store.record_health(rec.id, report)
        retrieved = store.get_source(rec.id)
        assert retrieved is not None
        assert isinstance(retrieved, ConfiguredSourceRecord)
        assert retrieved.last_checked_at is not None

    def test_health_persisted_retrievable_via_get_source(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        report = SourceHealthReport(health=SourceHealth.FAILED, checked_at=_now())
        store.record_health(rec.id, report)
        retrieved = store.get_source(rec.id)
        assert isinstance(retrieved, ConfiguredSourceRecord)
        assert retrieved.health == SourceHealth.FAILED

    def test_last_error_stored_from_message(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        report = SourceHealthReport(
            health=SourceHealth.FAILED, message="connection refused", checked_at=_now()
        )
        store.record_health(rec.id, report)
        retrieved = store.get_source(rec.id)
        assert isinstance(retrieved, ConfiguredSourceRecord)
        assert retrieved.last_error == "connection refused"

    def test_last_error_cleared_when_ok(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.record_health(rec.id, SourceHealthReport(health=SourceHealth.FAILED, message="err", checked_at=_now()))
        store.record_health(rec.id, SourceHealthReport(health=SourceHealth.OK, checked_at=_now()))
        retrieved = store.get_source(rec.id)
        assert isinstance(retrieved, ConfiguredSourceRecord)
        assert retrieved.last_error is None

    def test_raises_lookup_error_on_unknown_id(self, store: SqliteSourceStore) -> None:
        report = SourceHealthReport(health=SourceHealth.OK, checked_at=_now())
        with pytest.raises(LookupError):
            store.record_health("unknown-id", report)


# ---------------------------------------------------------------------------
# AC-7: stats
# ---------------------------------------------------------------------------


class TestFromAC_Stats:
    def test_returns_source_stats(self, store: SqliteSourceStore) -> None:
        from owlbear_knowledge.protocols.sources import SourceStats
        result = store.stats()
        assert isinstance(result, SourceStats)

    def test_all_counts_zero_on_empty_store(self, store: SqliteSourceStore) -> None:
        result = store.stats()
        assert result.total == 0
        assert result.active == 0
        assert result.inactive == 0
        assert result.wished == 0

    def test_active_count_reflects_registered_source(self, store: SqliteSourceStore) -> None:
        store.register_source(_file_registration())
        result = store.stats()
        assert result.active == 1
        assert result.total == 1

    def test_wished_count_reflects_registered_wish(self, store: SqliteSourceStore) -> None:
        store.register_wish(_wish())
        result = store.stats()
        assert result.wished == 1
        assert result.total == 1

    def test_inactive_count_after_deactivation(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.update_source(rec.id, SourceUpdate(state=SourceState.INACTIVE))
        result = store.stats()
        assert result.inactive == 1
        assert result.active == 0
        assert result.total == 1

    def test_counts_reflect_mixed_state(self, store: SqliteSourceStore) -> None:
        rec1 = store.register_source(_file_registration(name="a"))
        store.register_source(_url_registration(name="b"))
        store.update_source(rec1.id, SourceUpdate(state=SourceState.INACTIVE))
        store.register_wish(SourceWish(name="c"))
        result = store.stats()
        assert result.total == 3
        assert result.active == 1
        assert result.inactive == 1
        assert result.wished == 1

    def test_stats_decrease_after_delete(self, store: SqliteSourceStore) -> None:
        rec = store.register_source(_file_registration())
        store.delete_source(rec.id)
        result = store.stats()
        assert result.total == 0
        assert result.active == 0


# ---------------------------------------------------------------------------
# AC-8: ensure_tables / DDL
# ---------------------------------------------------------------------------


class TestFromAC_EnsureTables:
    def test_ensure_tables_creates_schema_without_error(
        self, conn: sqlite3.Connection
    ) -> None:
        s = SqliteSourceStore(conn)
        s.ensure_tables()  # must not raise

    def test_ensure_tables_is_idempotent(self, conn: sqlite3.Connection) -> None:
        s = SqliteSourceStore(conn)
        s.ensure_tables()
        s.ensure_tables()  # second call must not raise

    def test_source_registry_table_exists_after_ensure_tables(
        self, conn: sqlite3.Connection
    ) -> None:
        s = SqliteSourceStore(conn)
        s.ensure_tables()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'source_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert tables, "Expected at least one source_* table to be created"

    def test_can_register_source_after_ensure_tables(self, conn: sqlite3.Connection) -> None:
        s = SqliteSourceStore(conn)
        s.ensure_tables()
        result = s.register_source(_file_registration())
        assert isinstance(result, ConfiguredSourceRecord)
