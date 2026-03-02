"""Tests for KnowledgeSource model + KnowledgeSourceStore SQLite CRUD.

TDD red-phase for task #382.  Covers SourceType enum, KnowledgeSource
Pydantic model, and all KnowledgeSourceStore CRUD operations.
"""

from __future__ import annotations

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

    def test_create_duplicate_name_scope_raises(
        self, store: KnowledgeSourceStore
    ) -> None:
        store.create(_source(name="dup"))
        with pytest.raises(sqlite3.IntegrityError):
            store.create(_source(name="dup"))

    def test_same_name_different_scope_ok(
        self, store: KnowledgeSourceStore
    ) -> None:
        store.create(_source(name="shared", scope="project-a"))
        store.create(_source(name="shared", scope="project-b"))
        assert store.get_by_name("shared", scope="project-a") is not None
        assert store.get_by_name("shared", scope="project-b") is not None


class TestGet:
    """store.get() / get_by_name() lookups."""

    def test_get_returns_none_for_missing(
        self, store: KnowledgeSourceStore
    ) -> None:
        assert store.get("nonexistent") is None

    def test_get_by_name_returns_match(
        self, store: KnowledgeSourceStore
    ) -> None:
        src = _source(name="wiki", scope="global")
        store.create(src)
        got = store.get_by_name("wiki", scope="global")
        assert got is not None
        assert got.id == src.id

    def test_get_by_name_returns_none_for_missing(
        self, store: KnowledgeSourceStore
    ) -> None:
        assert store.get_by_name("nope") is None

    def test_get_by_name_scoped(self, store: KnowledgeSourceStore) -> None:
        store.create(_source(name="data", scope="proj"))
        assert store.get_by_name("data", scope="proj") is not None
        assert store.get_by_name("data", scope="other") is None


class TestListAll:
    """store.list_all() with optional scope filter."""

    def test_list_all_empty(self, store: KnowledgeSourceStore) -> None:
        assert store.list_all() == []

    def test_list_all_returns_everything(
        self, store: KnowledgeSourceStore
    ) -> None:
        store.create(_source(name="a"))
        store.create(_source(name="b"))
        assert len(store.list_all()) == 2

    def test_list_all_filtered_by_scope(
        self, store: KnowledgeSourceStore
    ) -> None:
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

    def test_ordered_by_priority_desc(
        self, store: KnowledgeSourceStore
    ) -> None:
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

    def test_delete_existing_returns_true(
        self, store: KnowledgeSourceStore
    ) -> None:
        src = _source()
        store.create(src)
        assert store.delete(src.id) is True
        assert store.get(src.id) is None

    def test_delete_missing_returns_false(
        self, store: KnowledgeSourceStore
    ) -> None:
        assert store.delete("nonexistent") is False


class TestJsonRoundTrip:
    """config dict survives store → retrieve cycle."""

    def test_nested_config_round_trips(
        self, store: KnowledgeSourceStore
    ) -> None:
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

    def test_empty_config_round_trips(
        self, store: KnowledgeSourceStore
    ) -> None:
        src = _source(config={})
        store.create(src)
        got = store.get(src.id)
        assert got is not None
        assert got.config == {}
