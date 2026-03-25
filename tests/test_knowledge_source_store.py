"""Tests for KnowledgeSource model + KnowledgeSourceStore SQLite CRUD.

TDD red-phase for task #382.  Covers SourceType enum, KnowledgeSource
Pydantic model, and all KnowledgeSourceStore CRUD operations.
"""

from __future__ import annotations

import contextlib
import re
import sqlite3

import pytest

from owlbear.memory.knowledge.models import KnowledgeSource, SourceType
from owlbear.memory.knowledge.source_store import KnowledgeSourceStore

# ---------------------------------------------------------------------------
# DDL — create the table directly (schema migration is task #383)
# ---------------------------------------------------------------------------

_CREATE_KNOWLEDGE_SOURCES = """\
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    source_type       TEXT NOT NULL,
    config            TEXT NOT NULL DEFAULT '{}',
    scope             TEXT NOT NULL DEFAULT 'global',
    enabled           INTEGER NOT NULL DEFAULT 1,
    priority          INTEGER NOT NULL DEFAULT 0,
    last_refreshed_at TEXT,
    last_error        TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    UNIQUE(name, scope)
)
"""

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory SQLite connection with the knowledge_sources table."""
    c = sqlite3.connect(":memory:")
    c.execute(_CREATE_KNOWLEDGE_SOURCES)
    c.commit()
    return c


@pytest.fixture
def store(conn: sqlite3.Connection) -> KnowledgeSourceStore:
    """KnowledgeSourceStore wired to the in-memory database."""
    return KnowledgeSourceStore(conn)


def _source(  # noqa: PLR0913
    *,
    name: str = "docs",
    source_type: SourceType = SourceType.URL_LIST,
    config: dict | None = None,
    scope: str = "global",
    enabled: bool = True,
    priority: int = 0,
) -> KnowledgeSource:
    """Build a KnowledgeSource with sensible defaults."""
    now = "2026-03-01T00:00:00+00:00"
    return KnowledgeSource(
        name=name,
        source_type=source_type,
        config={"urls": ["https://example.com"]} if config is None else config,
        scope=scope,
        enabled=enabled,
        priority=priority,
        created_at=now,
        updated_at=now,
    )


# ===========================================================================
# SourceType enum
# ===========================================================================


class TestSourceType:
    """SourceType is a 3-member StrEnum."""

    def test_has_exactly_three_members(self) -> None:
        assert len(SourceType) == 3

    def test_members_are_correct(self) -> None:
        assert set(SourceType) == {
            SourceType.URL_LIST,
            SourceType.CRAWL,
            SourceType.FILE_GLOB,
        }

    def test_values_are_snake_case(self) -> None:
        assert SourceType.URL_LIST.value == "url_list"
        assert SourceType.CRAWL.value == "crawl"
        assert SourceType.FILE_GLOB.value == "file_glob"

    def test_is_str_subclass(self) -> None:
        assert isinstance(SourceType.CRAWL, str)


# ===========================================================================
# KnowledgeSource model
# ===========================================================================


class TestKnowledgeSourceModel:
    """Pydantic model validation + frozen semantics."""

    def test_required_fields_present(self) -> None:
        src = _source()
        assert src.id  # auto-generated uuid hex
        assert src.name == "docs"
        assert src.source_type == SourceType.URL_LIST
        assert src.config == {"urls": ["https://example.com"]}
        assert src.scope == "global"
        assert src.enabled is True
        assert src.priority == 0
        assert src.last_refreshed_at is None
        assert src.last_error is None
        assert src.created_at == "2026-03-01T00:00:00+00:00"
        assert src.updated_at == "2026-03-01T00:00:00+00:00"

    def test_id_defaults_to_uuid_hex(self) -> None:
        src = _source()
        assert len(src.id) == 32
        assert src.id.isalnum()

    def test_config_is_dict(self) -> None:
        src = _source(config={"pattern": "*.md", "recursive": True})
        assert isinstance(src.config, dict)
        assert src.config["recursive"] is True

    def test_frozen(self) -> None:
        src = _source()
        with pytest.raises(Exception, match="frozen"):
            src.name = "new_name"  # type: ignore[misc]

    def test_defaults(self) -> None:
        """scope, enabled, priority have sensible defaults."""
        now = "2026-03-01T00:00:00+00:00"
        src = KnowledgeSource(
            name="x",
            source_type=SourceType.CRAWL,
            config={},
            created_at=now,
            updated_at=now,
        )
        assert src.scope == "global"
        assert src.enabled is True
        assert src.priority == 0
        assert src.last_refreshed_at is None
        assert src.last_error is None


# ===========================================================================
# KnowledgeSourceStore CRUD
# ===========================================================================


class TestCreate:
    """store.create() inserts a source."""

    def test_create_and_retrieve(self, store: KnowledgeSourceStore) -> None:
        src = _source()
        store.create(src)
        got = store.get(src.id)
        assert got is not None
        assert got.id == src.id
        assert got.name == src.name

    def test_create_duplicate_name_scope_raises(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="dup"))
        with pytest.raises(sqlite3.IntegrityError):
            store.create(_source(name="dup"))

    def test_same_name_different_scope_ok(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="shared", scope="project-a"))
        store.create(_source(name="shared", scope="project-b"))
        assert store.get_by_name("shared", scope="project-a") is not None
        assert store.get_by_name("shared", scope="project-b") is not None


class TestGet:
    """store.get() / get_by_name() lookups."""

    def test_get_returns_none_for_missing(self, store: KnowledgeSourceStore) -> None:
        assert store.get("nonexistent") is None

    def test_get_by_name_returns_match(self, store: KnowledgeSourceStore) -> None:
        src = _source(name="wiki", scope="global")
        store.create(src)
        got = store.get_by_name("wiki", scope="global")
        assert got is not None
        assert got.id == src.id

    def test_get_by_name_returns_none_for_missing(self, store: KnowledgeSourceStore) -> None:
        assert store.get_by_name("nope") is None

    def test_get_by_name_scoped(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="data", scope="proj"))
        assert store.get_by_name("data", scope="proj") is not None
        assert store.get_by_name("data", scope="other") is None


class TestListAll:
    """store.list_all() with optional scope filter."""

    def test_list_all_empty(self, store: KnowledgeSourceStore) -> None:
        assert store.list_all() == []

    def test_list_all_returns_everything(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="a"))
        store.create(_source(name="b"))
        assert len(store.list_all()) == 2

    def test_list_all_filtered_by_scope(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="x", scope="alpha"))
        store.create(_source(name="y", scope="beta"))
        result = store.list_all(scope="alpha")
        assert len(result) == 1
        assert result[0].name == "x"


class TestListEnabled:
    """store.list_enabled() returns enabled=True only, ordered by priority DESC."""

    def test_excludes_disabled(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="on", enabled=True))
        store.create(_source(name="off", enabled=False))
        result = store.list_enabled()
        assert len(result) == 1
        assert result[0].name == "on"

    def test_ordered_by_priority_desc(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="low", priority=1))
        store.create(_source(name="high", priority=10))
        store.create(_source(name="mid", priority=5))
        result = store.list_enabled()
        priorities = [s.priority for s in result]
        assert priorities == [10, 5, 1]

    def test_filtered_by_scope(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="a", scope="s1"))
        store.create(_source(name="b", scope="s2"))
        result = store.list_enabled(scope="s1")
        assert len(result) == 1
        assert result[0].scope == "s1"


class TestUpdate:
    """store.update() overwrites an existing record."""

    def test_update_existing(self, store: KnowledgeSourceStore) -> None:
        src = _source(name="orig")
        store.create(src)
        updated = KnowledgeSource(
            id=src.id,
            name="renamed",
            source_type=src.source_type,
            config=src.config,
            scope=src.scope,
            enabled=src.enabled,
            priority=99,
            created_at=src.created_at,
            updated_at="2026-03-02T12:00:00+00:00",
        )
        store.update(updated)
        got = store.get(src.id)
        assert got is not None
        assert got.name == "renamed"
        assert got.priority == 99

    def test_update_missing_raises(self, store: KnowledgeSourceStore) -> None:
        src = _source(name="ghost")
        with pytest.raises(ValueError, match="not found"):
            store.update(src)


class TestDelete:
    """store.delete() removes by id."""

    def test_delete_existing_returns_true(self, store: KnowledgeSourceStore) -> None:
        src = _source()
        store.create(src)
        assert store.delete(src.id) is True
        assert store.get(src.id) is None

    def test_delete_missing_returns_false(self, store: KnowledgeSourceStore) -> None:
        assert store.delete("nonexistent") is False


class TestJsonRoundTrip:
    """config dict survives store → retrieve cycle."""

    def test_nested_config_round_trips(self, store: KnowledgeSourceStore) -> None:
        cfg = {
            "urls": ["https://a.com", "https://b.com"],
            "depth": 3,
            "options": {"follow_redirects": True, "timeout": 30},
        }
        src = _source(config=cfg)
        store.create(src)
        got = store.get(src.id)
        assert got is not None
        assert got.config == cfg
        assert got.config["options"]["follow_redirects"] is True  # type: ignore[index]

    def test_empty_config_round_trips(self, store: KnowledgeSourceStore) -> None:
        src = _source(config={})
        store.create(src)
        got = store.get(src.id)
        assert got is not None
        assert got.config == {}


# ===========================================================================
# _SELECT_COLS column-contract tests  (TDD RED — task #892)
# ===========================================================================

# Canonical 11-column list; order must stay aligned with _row_to_model().
_EXPECTED_SELECT_COLS = (
    "id, name, source_type, config, scope, enabled, priority, "
    "last_refreshed_at, last_error, created_at, updated_at"
)


def _capture_sql(conn: sqlite3.Connection) -> list[str]:
    """Install a trace callback on *conn* and return the list it accumulates."""
    executed: list[str] = []
    conn.set_trace_callback(executed.append)
    return executed


def _select_stmts_on_ks(executed: list[str]) -> list[str]:
    """Filter for knowledge_sources SELECT statements and normalise whitespace."""
    return [
        re.sub(r"\s+", " ", s.strip())
        for s in executed
        if "SELECT" in s.upper() and "knowledge_sources" in s
    ]


class TestFromAC_SelectColsAttribute:
    """AC3 + AC4: _SELECT_COLS class attribute exists with the canonical column list."""

    def test_attribute_exists_on_store_class(self) -> None:
        """KnowledgeSourceStore._SELECT_COLS must be defined as a class attribute."""
        assert hasattr(KnowledgeSourceStore, "_SELECT_COLS")

    def test_attribute_equals_canonical_column_list(self) -> None:
        """_SELECT_COLS must equal the exact 11-column ordered list required by _row_to_model."""
        assert KnowledgeSourceStore._SELECT_COLS == _EXPECTED_SELECT_COLS  # type: ignore[attr-defined]


class TestFromAC_SelectColsInReadPaths:
    """AC2 + AC3 + AC4: every read path emits SQL whose column list equals _SELECT_COLS."""

    def test_get_sql_contains_select_cols(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """get(source_id) SELECT uses the canonical column list."""
        src = _source(name="sc-get")
        store.create(src)
        executed = _capture_sql(conn)
        store.get(src.id)
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "get() emitted no SELECT on knowledge_sources"
        assert all(
            KnowledgeSourceStore._SELECT_COLS in s  # type: ignore[attr-defined]
            for s in stmts
        )

    def test_get_by_name_sql_contains_select_cols(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """get_by_name(name, scope) SELECT uses the canonical column list."""
        src = _source(name="sc-byname")
        store.create(src)
        executed = _capture_sql(conn)
        store.get_by_name(src.name, scope=src.scope)
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "get_by_name() emitted no SELECT on knowledge_sources"
        assert all(
            KnowledgeSourceStore._SELECT_COLS in s  # type: ignore[attr-defined]
            for s in stmts
        )

    def test_list_all_no_scope_sql_contains_select_cols(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """list_all() (no scope) SELECT uses the canonical column list."""
        store.create(_source(name="sc-all-unscoped"))
        executed = _capture_sql(conn)
        store.list_all()
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_all() emitted no SELECT on knowledge_sources"
        assert all(
            KnowledgeSourceStore._SELECT_COLS in s  # type: ignore[attr-defined]
            for s in stmts
        )

    def test_list_all_with_scope_sql_contains_select_cols(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """list_all(scope=...) SELECT uses the canonical column list."""
        store.create(_source(name="sc-all-scoped", scope="test-scope"))
        executed = _capture_sql(conn)
        store.list_all(scope="test-scope")
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_all(scope=...) emitted no SELECT on knowledge_sources"
        assert all(
            KnowledgeSourceStore._SELECT_COLS in s  # type: ignore[attr-defined]
            for s in stmts
        )

    def test_list_enabled_no_scope_sql_contains_select_cols(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """list_enabled() (no scope) SELECT uses the canonical column list."""
        store.create(_source(name="sc-enabled-unscoped", enabled=True))
        executed = _capture_sql(conn)
        store.list_enabled()
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_enabled() emitted no SELECT on knowledge_sources"
        assert all(
            KnowledgeSourceStore._SELECT_COLS in s  # type: ignore[attr-defined]
            for s in stmts
        )

    def test_list_enabled_with_scope_sql_contains_select_cols(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """list_enabled(scope=...) SELECT uses the canonical column list."""
        store.create(_source(name="sc-enabled-scoped", scope="x-scope", enabled=True))
        executed = _capture_sql(conn)
        store.list_enabled(scope="x-scope")
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_enabled(scope=...) emitted no SELECT on knowledge_sources"
        assert all(
            KnowledgeSourceStore._SELECT_COLS in s  # type: ignore[attr-defined]
            for s in stmts
        )


# ---------------------------------------------------------------------------
# Sentinel used to prove _SELECT_COLS is referenced dynamically, not hardcoded.
# We patch _SELECT_COLS to "id" (a valid single column) and assert the emitted
# SQL contains "SELECT id FROM" — which would only be true if the query is built
# from the class attribute at runtime.  The hardcoded queries all produce
# "SELECT id, name, ..." so "SELECT id FROM" is absent → test FAILs until the
# builder refactors to use _SELECT_COLS in the query strings.
# ---------------------------------------------------------------------------
_SENTINEL_COLS = "id"
_SENTINEL_PREFIX = f"SELECT {_SENTINEL_COLS} FROM"


class TestFromAC_SelectColsDynamicReuse:
    """AC4: each read-query path builds its SELECT clause from _SELECT_COLS at runtime.

    These tests monkeypatch _SELECT_COLS to a sentinel value ("id") and assert that
    the emitted SQL starts with "SELECT id FROM" — proving the query is constructed
    from the class attribute, not from a hardcoded literal.

    With the current implementation (hardcoded column lists), all six tests FAIL
    because the SQL contains "SELECT id, name, ..." even after patching.  After the
    GREEN refactor the tests will pass once queries use _SELECT_COLS dynamically.
    """

    def test_get_sql_built_from_select_cols(
        self,
        store: KnowledgeSourceStore,
        conn: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """get() must emit SQL containing the runtime value of _SELECT_COLS."""
        src = _source(name="dyn-get")
        store.create(src)
        monkeypatch.setattr(KnowledgeSourceStore, "_SELECT_COLS", _SENTINEL_COLS)
        executed = _capture_sql(conn)
        with contextlib.suppress(IndexError):
            store.get(src.id)
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "get() emitted no SELECT on knowledge_sources"
        assert any(_SENTINEL_PREFIX in s for s in stmts), (
            f"get() SQL did not use _SELECT_COLS dynamically; SQL was: {stmts}"
        )

    def test_get_by_name_sql_built_from_select_cols(
        self,
        store: KnowledgeSourceStore,
        conn: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """get_by_name() must emit SQL containing the runtime value of _SELECT_COLS."""
        src = _source(name="dyn-byname")
        store.create(src)
        monkeypatch.setattr(KnowledgeSourceStore, "_SELECT_COLS", _SENTINEL_COLS)
        executed = _capture_sql(conn)
        with contextlib.suppress(IndexError):
            store.get_by_name(src.name, scope=src.scope)
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "get_by_name() emitted no SELECT on knowledge_sources"
        assert any(_SENTINEL_PREFIX in s for s in stmts), (
            f"get_by_name() SQL did not use _SELECT_COLS dynamically; SQL was: {stmts}"
        )

    def test_list_all_no_scope_sql_built_from_select_cols(
        self,
        store: KnowledgeSourceStore,
        conn: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """list_all() (no scope) must emit SQL containing the runtime value of _SELECT_COLS."""
        store.create(_source(name="dyn-all"))
        monkeypatch.setattr(KnowledgeSourceStore, "_SELECT_COLS", _SENTINEL_COLS)
        executed = _capture_sql(conn)
        with contextlib.suppress(IndexError):
            store.list_all()
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_all() emitted no SELECT on knowledge_sources"
        assert any(_SENTINEL_PREFIX in s for s in stmts), (
            f"list_all() SQL did not use _SELECT_COLS dynamically; SQL was: {stmts}"
        )

    def test_list_all_with_scope_sql_built_from_select_cols(
        self,
        store: KnowledgeSourceStore,
        conn: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """list_all(scope=...) must emit SQL containing the runtime value of _SELECT_COLS."""
        store.create(_source(name="dyn-all-scoped", scope="dyn-scope"))
        monkeypatch.setattr(KnowledgeSourceStore, "_SELECT_COLS", _SENTINEL_COLS)
        executed = _capture_sql(conn)
        with contextlib.suppress(IndexError):
            store.list_all(scope="dyn-scope")
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_all(scope=...) emitted no SELECT on knowledge_sources"
        assert any(_SENTINEL_PREFIX in s for s in stmts), (
            f"list_all(scope=...) SQL did not use _SELECT_COLS dynamically; SQL was: {stmts}"
        )

    def test_list_enabled_no_scope_sql_built_from_select_cols(
        self,
        store: KnowledgeSourceStore,
        conn: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """list_enabled() (no scope) must emit SQL containing the runtime value of _SELECT_COLS."""
        store.create(_source(name="dyn-enabled", enabled=True))
        monkeypatch.setattr(KnowledgeSourceStore, "_SELECT_COLS", _SENTINEL_COLS)
        executed = _capture_sql(conn)
        with contextlib.suppress(IndexError):
            store.list_enabled()
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_enabled() emitted no SELECT on knowledge_sources"
        assert any(_SENTINEL_PREFIX in s for s in stmts), (
            f"list_enabled() SQL did not use _SELECT_COLS dynamically; SQL was: {stmts}"
        )

    def test_list_enabled_with_scope_sql_built_from_select_cols(
        self,
        store: KnowledgeSourceStore,
        conn: sqlite3.Connection,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """list_enabled(scope=...) must emit SQL containing the runtime value of _SELECT_COLS."""
        store.create(_source(name="dyn-enabled-scoped", scope="dyn-x", enabled=True))
        monkeypatch.setattr(KnowledgeSourceStore, "_SELECT_COLS", _SENTINEL_COLS)
        executed = _capture_sql(conn)
        with contextlib.suppress(IndexError):
            store.list_enabled(scope="dyn-x")
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "list_enabled(scope=...) emitted no SELECT on knowledge_sources"
        assert any(_SENTINEL_PREFIX in s for s in stmts), (
            f"list_enabled(scope=...) SQL did not use _SELECT_COLS dynamically; SQL was: {stmts}"
        )


# ===========================================================================
# AC3 predicate-level tests  (retry cycle — task #563, test-writer)
# These tests verify that get() filters strictly by id and that get_by_name()
# filters strictly by (name AND scope).  The multi-row scenarios catch mutations
# that relax the WHERE clause (e.g. "returns first row" or "scope-only filter").
# ===========================================================================


class TestFromAC_QueryBehaviorPredicates:
    """AC3: get() uses id predicate; get_by_name() uses name AND scope predicate.

    Multi-row fixtures are required so that a "first-row" or "scope-only"
    regression would produce a wrong result and cause the assertion to fail.
    """

    # -- get() id predicate --------------------------------------------------

    def test_get_discriminates_by_id_not_by_position(
        self, store: KnowledgeSourceStore
    ) -> None:
        """get(id) must return the row with that specific id, not the first row.

        Catches the mutation: fetchone() without WHERE id = ?.
        """
        src1 = _source(name="pred-get-1")
        src2 = _source(name="pred-get-2")
        store.create(src1)
        store.create(src2)

        got = store.get(src2.id)

        assert got is not None
        assert got.id == src2.id, (
            f"get(src2.id) should return src2, but returned {got.id!r}"
        )

    def test_get_returns_none_when_id_absent_but_other_rows_exist(
        self, store: KnowledgeSourceStore
    ) -> None:
        """get() must return None when id is not in db, even if other rows exist."""
        src = _source(name="pred-get-present")
        store.create(src)

        result = store.get("00000000000000000000000000000000")

        assert result is None

    def test_get_sql_where_clause_filters_by_id(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """get() SQL must contain 'WHERE id =' so any id-predicate regression
        is surfaced without running a multi-row scenario.

        Note: sqlite3 trace expands parameters to literal values, not '?'.
        """
        src = _source(name="pred-get-sql")
        store.create(src)
        executed = _capture_sql(conn)
        store.get(src.id)
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "get() emitted no SELECT on knowledge_sources"
        assert any(re.search(r"WHERE id =", s) for s in stmts), (
            f"get() SQL does not contain 'WHERE id ='; SQL was: {stmts}"
        )

    # -- get_by_name() name+scope predicate -----------------------------------

    def test_get_by_name_discriminates_by_name_within_same_scope(
        self, store: KnowledgeSourceStore
    ) -> None:
        """get_by_name(name, scope) must return the row matching name; two rows
        with the same scope but different names must not be confused.

        Catches the mutation: WHERE scope = ? (omitting name predicate).
        """
        src_alpha = _source(name="pred-alpha", scope="shared-scope")
        src_beta = _source(name="pred-beta", scope="shared-scope")
        store.create(src_alpha)
        store.create(src_beta)

        got = store.get_by_name("pred-beta", scope="shared-scope")

        assert got is not None
        assert got.id == src_beta.id, (
            f"get_by_name('pred-beta') should return src_beta but returned {got.id!r}"
        )

    def test_get_by_name_returns_none_when_name_wrong_scope_exists(
        self, store: KnowledgeSourceStore
    ) -> None:
        """get_by_name() must return None when name is absent in that scope,
        even if a row with the same scope exists under a different name."""
        store.create(_source(name="pred-real", scope="pred-scope"))

        result = store.get_by_name("pred-ghost", scope="pred-scope")

        assert result is None

    def test_get_by_name_sql_where_clause_filters_by_name_and_scope(
        self, store: KnowledgeSourceStore, conn: sqlite3.Connection
    ) -> None:
        """get_by_name() SQL must contain both 'name =' and 'scope =' so dropping
        either predicate is caught by SQL inspection.

        Note: sqlite3 trace expands parameters to literal values, not '?'.
        """
        src = _source(name="pred-gbn-sql")
        store.create(src)
        executed = _capture_sql(conn)
        store.get_by_name(src.name, scope=src.scope)
        stmts = _select_stmts_on_ks(executed)
        assert stmts, "get_by_name() emitted no SELECT on knowledge_sources"
        assert any(
            re.search(r"WHERE name =", s) and re.search(r"AND scope =", s)
            for s in stmts
        ), (
            f"get_by_name() SQL does not contain 'WHERE name = ... AND scope ='; SQL was: {stmts}"
        )
