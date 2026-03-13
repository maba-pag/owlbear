"""Tests for Bookmark model + BookmarkStore SQLite CRUD + schema v7.

TDD red-phase for tasks #398 (model + store) and #402 (tests).
Covers: Bookmark Pydantic model validation, BookmarkStore CRUD operations,
dedup by URL+scope, schema v7 migration, idempotency.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from owlbear.memory.knowledge.bookmark import Bookmark, BookmarkStore
from owlbear.memory.knowledge.schema import _SCHEMA_VERSION, init_db

# ---------------------------------------------------------------------------
# DDL — create the table directly for unit tests (schema migration tested separately)
# ---------------------------------------------------------------------------

_CREATE_BOOKMARKS = """\
CREATE TABLE IF NOT EXISTS bookmarks (
    id             TEXT PRIMARY KEY,
    url            TEXT NOT NULL,
    title          TEXT NOT NULL,
    description    TEXT,
    tags           TEXT NOT NULL DEFAULT '[]',
    relevance_score REAL NOT NULL DEFAULT 0.0,
    reason         TEXT,
    scope          TEXT NOT NULL DEFAULT 'global',
    document_id    TEXT,
    content_hash   TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    UNIQUE(url, scope)
)
"""

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory SQLite connection with the bookmarks table."""
    c = sqlite3.connect(":memory:")
    c.execute(_CREATE_BOOKMARKS)
    c.commit()
    return c


@pytest.fixture
def store(conn: sqlite3.Connection) -> BookmarkStore:
    """BookmarkStore wired to the in-memory database."""
    return BookmarkStore(conn)


def _bookmark(  # noqa: PLR0913
    *,
    url: str = "https://example.com/page",
    title: str = "Example Page",
    description: str | None = "A useful page",
    tags: list[str] | None = None,
    relevance_score: float = 0.85,
    reason: str | None = "Relevant to project",
    scope: str = "global",
    document_id: str | None = None,
    content_hash: str | None = None,
) -> Bookmark:
    """Build a Bookmark with sensible defaults."""
    now = "2026-03-01T00:00:00+00:00"
    return Bookmark(
        url=url,
        title=title,
        description=description,
        tags=tags or ["python", "docs"],
        relevance_score=relevance_score,
        reason=reason,
        scope=scope,
        document_id=document_id,
        content_hash=content_hash,
        created_at=now,
        updated_at=now,
    )


# ===========================================================================
# Bookmark model
# ===========================================================================


class TestBookmarkModel:
    """Pydantic model validation + frozen semantics."""

    def test_required_fields_present(self) -> None:
        bm = _bookmark()
        assert bm.id  # auto-generated uuid hex
        assert bm.url == "https://example.com/page"
        assert bm.title == "Example Page"
        assert bm.description == "A useful page"
        assert bm.tags == ["python", "docs"]
        assert bm.relevance_score == 0.85
        assert bm.reason == "Relevant to project"
        assert bm.scope == "global"
        assert bm.document_id is None
        assert bm.content_hash is None
        assert bm.created_at == "2026-03-01T00:00:00+00:00"
        assert bm.updated_at == "2026-03-01T00:00:00+00:00"

    def test_id_defaults_to_uuid_hex(self) -> None:
        bm = _bookmark()
        assert len(bm.id) == 32
        assert bm.id.isalnum()

    def test_frozen(self) -> None:
        bm = _bookmark()
        with pytest.raises(Exception, match="frozen"):
            bm.url = "https://other.com"  # type: ignore[misc]

    def test_defaults(self) -> None:
        """scope, tags, relevance_score have sensible defaults."""
        now = "2026-03-01T00:00:00+00:00"
        bm = Bookmark(
            url="https://example.com",
            title="Test",
            created_at=now,
            updated_at=now,
        )
        assert bm.scope == "global"
        assert bm.tags == []
        assert bm.relevance_score == 0.0
        assert bm.description is None
        assert bm.reason is None
        assert bm.document_id is None
        assert bm.content_hash is None

    def test_tags_is_list_of_str(self) -> None:
        bm = _bookmark(tags=["a", "b", "c"])
        assert isinstance(bm.tags, list)
        assert all(isinstance(t, str) for t in bm.tags)

    def test_relevance_score_ge_zero(self) -> None:
        """relevance_score must be >= 0."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            _bookmark(relevance_score=-0.1)

    def test_relevance_score_le_one(self) -> None:
        """relevance_score must be <= 1."""
        with pytest.raises(ValueError, match="less than or equal to 1"):
            _bookmark(relevance_score=1.1)

    def test_optional_fields_none(self) -> None:
        bm = _bookmark(description=None, reason=None, document_id=None, content_hash=None)
        assert bm.description is None
        assert bm.reason is None
        assert bm.document_id is None
        assert bm.content_hash is None

    def test_unique_ids(self) -> None:
        """Two bookmarks should get different auto-generated IDs."""
        bm1 = _bookmark()
        bm2 = _bookmark()
        assert bm1.id != bm2.id


# ===========================================================================
# BookmarkStore CRUD
# ===========================================================================


class TestBookmarkStoreCreate:
    """BookmarkStore.create()."""

    def test_create_returns_bookmark(self, store: BookmarkStore) -> None:
        bm = _bookmark()
        result = store.create(bm)
        assert result.id == bm.id
        assert result.url == bm.url

    def test_create_persists(self, store: BookmarkStore, conn: sqlite3.Connection) -> None:
        bm = _bookmark()
        store.create(bm)
        row = conn.execute("SELECT id, url FROM bookmarks WHERE id = ?", (bm.id,)).fetchone()
        assert row is not None
        assert row[0] == bm.id
        assert row[1] == bm.url

    def test_create_duplicate_url_scope_raises(self, store: BookmarkStore) -> None:
        """Dedup: same URL + scope raises IntegrityError."""
        bm1 = _bookmark(url="https://dup.com", scope="global")
        bm2 = _bookmark(url="https://dup.com", scope="global")
        store.create(bm1)
        with pytest.raises(sqlite3.IntegrityError):
            store.create(bm2)

    def test_create_same_url_different_scope_ok(self, store: BookmarkStore) -> None:
        """Same URL in different scopes is allowed."""
        bm1 = _bookmark(url="https://dup.com", scope="project-a")
        bm2 = _bookmark(url="https://dup.com", scope="project-b")
        store.create(bm1)
        store.create(bm2)  # should not raise

    def test_create_stores_tags_as_json(
        self,
        store: BookmarkStore,
        conn: sqlite3.Connection,
    ) -> None:
        bm = _bookmark(tags=["alpha", "beta"])
        store.create(bm)
        row = conn.execute("SELECT tags FROM bookmarks WHERE id = ?", (bm.id,)).fetchone()
        assert row is not None
        assert row[0] == '["alpha", "beta"]'


class TestBookmarkStoreGetByUrl:
    """BookmarkStore.get_by_url()."""

    def test_get_by_url_found(self, store: BookmarkStore) -> None:
        bm = _bookmark(url="https://found.com", scope="global")
        store.create(bm)
        result = store.get_by_url("https://found.com", "global")
        assert result is not None
        assert result.id == bm.id
        assert result.url == "https://found.com"

    def test_get_by_url_not_found(self, store: BookmarkStore) -> None:
        result = store.get_by_url("https://missing.com", "global")
        assert result is None

    def test_get_by_url_wrong_scope(self, store: BookmarkStore) -> None:
        bm = _bookmark(url="https://scoped.com", scope="project-x")
        store.create(bm)
        result = store.get_by_url("https://scoped.com", "global")
        assert result is None

    def test_get_by_url_reconstructs_tags(self, store: BookmarkStore) -> None:
        bm = _bookmark(url="https://tags.com", tags=["x", "y"])
        store.create(bm)
        result = store.get_by_url("https://tags.com", "global")
        assert result is not None
        assert result.tags == ["x", "y"]


class TestBookmarkStoreList:
    """BookmarkStore.list()."""

    def test_list_all(self, store: BookmarkStore) -> None:
        store.create(_bookmark(url="https://a.com"))
        store.create(_bookmark(url="https://b.com"))
        results = store.list()
        assert len(results) == 2

    def test_list_filter_by_scope(self, store: BookmarkStore) -> None:
        store.create(_bookmark(url="https://a.com", scope="proj"))
        store.create(_bookmark(url="https://b.com", scope="global"))
        results = store.list(scope="proj")
        assert len(results) == 1
        assert results[0].scope == "proj"

    def test_list_filter_by_tag(self, store: BookmarkStore) -> None:
        store.create(_bookmark(url="https://a.com", tags=["python", "docs"]))
        store.create(_bookmark(url="https://b.com", tags=["rust"]))
        results = store.list(tag="python")
        assert len(results) == 1
        assert results[0].url == "https://a.com"

    def test_list_filter_by_min_score(self, store: BookmarkStore) -> None:
        store.create(_bookmark(url="https://high.com", relevance_score=0.9))
        store.create(_bookmark(url="https://low.com", relevance_score=0.3))
        results = store.list(min_score=0.5)
        assert len(results) == 1
        assert results[0].url == "https://high.com"

    def test_list_combined_filters(self, store: BookmarkStore) -> None:
        store.create(
            _bookmark(
                url="https://match.com",
                scope="proj",
                tags=["python"],
                relevance_score=0.9,
            )
        )
        store.create(
            _bookmark(
                url="https://wrong-scope.com",
                scope="other",
                tags=["python"],
                relevance_score=0.9,
            )
        )
        store.create(
            _bookmark(
                url="https://wrong-tag.com",
                scope="proj",
                tags=["rust"],
                relevance_score=0.9,
            )
        )
        store.create(
            _bookmark(
                url="https://low-score.com",
                scope="proj",
                tags=["python"],
                relevance_score=0.1,
            )
        )
        results = store.list(scope="proj", tag="python", min_score=0.5)
        assert len(results) == 1
        assert results[0].url == "https://match.com"

    def test_list_empty(self, store: BookmarkStore) -> None:
        results = store.list()
        assert results == []


class TestBookmarkStoreUpdateTags:
    """BookmarkStore.update_tags()."""

    def test_update_tags_success(self, store: BookmarkStore) -> None:
        bm = _bookmark(url="https://tags.com", tags=["old"])
        store.create(bm)
        store.update_tags(bm.id, ["new", "updated"])
        result = store.get_by_url("https://tags.com", "global")
        assert result is not None
        assert result.tags == ["new", "updated"]

    def test_update_tags_nonexistent_raises(self, store: BookmarkStore) -> None:
        with pytest.raises(ValueError, match="not found"):
            store.update_tags("nonexistent-id", ["tag"])

    def test_update_tags_empty_list(self, store: BookmarkStore) -> None:
        bm = _bookmark(url="https://empty.com", tags=["was-here"])
        store.create(bm)
        store.update_tags(bm.id, [])
        result = store.get_by_url("https://empty.com", "global")
        assert result is not None
        assert result.tags == []


class TestBookmarkStoreDelete:
    """BookmarkStore.delete()."""

    def test_delete_existing(self, store: BookmarkStore) -> None:
        bm = _bookmark(url="https://delete.com")
        store.create(bm)
        store.delete(bm.id)
        result = store.get_by_url("https://delete.com", "global")
        assert result is None

    def test_delete_nonexistent_raises(self, store: BookmarkStore) -> None:
        with pytest.raises(ValueError, match="not found"):
            store.delete("nonexistent-id")


# ===========================================================================
# Schema v7 migration (bookmarks table)
# ===========================================================================


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Return True if *table* exists in the database."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None and row[0] > 0


def _table_columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    """Return {column_name: column_type} for *table* via PRAGMA."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1]: row[2] for row in rows}


def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    """Return True if *index_name* exists in the database."""
    row = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,),
    ).fetchone()
    return row is not None and row[0] > 0


def _create_v6_db() -> sqlite3.Connection:
    """Build a v6-schema DB *without* the v7 bookmarks table."""
    conn = sqlite3.Connection(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        "CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT, content TEXT, "
        "metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE entities (id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, "
        "description TEXT, metadata TEXT, created_at TEXT, "
        "scope TEXT DEFAULT 'global', document_id TEXT, chunk_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE edges (id TEXT PRIMARY KEY, source_id TEXT REFERENCES entities(id), "
        "target_id TEXT REFERENCES entities(id), relation TEXT, weight REAL, "
        "metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE chunks (id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id), "
        "chunk_index INTEGER, content TEXT, metadata TEXT, created_at TEXT, "
        "scope TEXT DEFAULT 'global')"
    )
    conn.execute(
        "CREATE TABLE document_status (document_id TEXT PRIMARY KEY, status TEXT, "
        "source TEXT, error TEXT, created_at TEXT, updated_at TEXT, "
        "scope TEXT DEFAULT 'global', content_hash TEXT)"
    )
    conn.execute(
        "CREATE TABLE knowledge_sources (id TEXT PRIMARY KEY, name TEXT NOT NULL, "
        "source_type TEXT NOT NULL, config TEXT NOT NULL, scope TEXT DEFAULT 'global', "
        "enabled INTEGER DEFAULT 1, priority INTEGER DEFAULT 0, "
        "last_refreshed_at TEXT, last_error TEXT, created_at TEXT NOT NULL, "
        "updated_at TEXT NOT NULL)"
    )
    conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
    conn.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (6, ?)",
        (datetime.now(tz=UTC).isoformat(),),
    )
    conn.commit()
    return conn


class TestSchemaV7FreshDB:
    """init_db on an empty database creates the bookmarks table."""

    @pytest.fixture
    def db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        return conn

    def test_schema_version_is_7(self, db: sqlite3.Connection) -> None:  # noqa: ARG002
        assert _SCHEMA_VERSION == 8

    def test_bookmarks_table_exists(self, db: sqlite3.Connection) -> None:
        assert _table_exists(db, "bookmarks")

    def test_bookmarks_has_all_columns(self, db: sqlite3.Connection) -> None:
        cols = _table_columns(db, "bookmarks")
        expected = {
            "id",
            "url",
            "title",
            "description",
            "tags",
            "relevance_score",
            "reason",
            "scope",
            "document_id",
            "content_hash",
            "created_at",
            "updated_at",
        }
        assert expected == set(cols.keys())

    def test_bookmarks_url_scope_unique_index(self, db: sqlite3.Connection) -> None:
        assert _index_exists(db, "idx_bookmarks_url_scope")

    def test_bookmarks_scope_index(self, db: sqlite3.Connection) -> None:
        assert _index_exists(db, "idx_bookmarks_scope")


class TestSchemaV7Migration:
    """v6 → v7 migration path via init_db."""

    def test_bookmarks_table_created(self) -> None:
        conn = _create_v6_db()
        init_db(conn)
        assert _table_exists(conn, "bookmarks")

    def test_bookmarks_has_all_columns(self) -> None:
        conn = _create_v6_db()
        init_db(conn)
        cols = _table_columns(conn, "bookmarks")
        expected = {
            "id",
            "url",
            "title",
            "description",
            "tags",
            "relevance_score",
            "reason",
            "scope",
            "document_id",
            "content_hash",
            "created_at",
            "updated_at",
        }
        assert expected == set(cols.keys())

    def test_bookmarks_url_scope_index_created(self) -> None:
        conn = _create_v6_db()
        init_db(conn)
        assert _index_exists(conn, "idx_bookmarks_url_scope")

    def test_bookmarks_scope_index_created(self) -> None:
        conn = _create_v6_db()
        init_db(conn)
        assert _index_exists(conn, "idx_bookmarks_scope")

    def test_version_bumped_to_7(self) -> None:
        conn = _create_v6_db()
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 8

    def test_existing_data_preserved(self) -> None:
        """Pre-existing knowledge_sources rows survive the migration."""
        conn = _create_v6_db()
        conn.execute(
            "INSERT INTO knowledge_sources (id, name, source_type, config, created_at, updated_at) "
            "VALUES ('ks1', 'test-src', 'url_list', '{}', '2026-01-01', '2026-01-01')"
        )
        conn.commit()
        init_db(conn)
        row = conn.execute("SELECT id FROM knowledge_sources WHERE id = 'ks1'").fetchone()
        assert row is not None


class TestSchemaV7Idempotent:
    """Calling init_db twice is safe — no errors, no data loss."""

    def test_double_init_no_error(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        init_db(conn)  # second call should not raise

    def test_double_init_preserves_bookmarks(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        conn.execute(
            "INSERT INTO bookmarks"
            " (id, url, title, tags, relevance_score, scope, created_at, updated_at)"
            " VALUES ('bm1', 'https://x.com', 'X', '[]', 0.5, 'global',"
            " '2026-01-01', '2026-01-01')"
        )
        conn.commit()
        init_db(conn)
        row = conn.execute("SELECT id FROM bookmarks WHERE id = 'bm1'").fetchone()
        assert row is not None
