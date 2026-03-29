"""RED-phase tests for BookmarkStore extraction (#15).

Tests the contract for: Bookmark model, BookmarkStore CRUD operations,
tag serialization, filter behavior, and __init__.py exports.

All tests import from owlbear_knowledge.bookmark_store (not v1 paths)
and use :memory: SQLite.
All tests fail in RED phase — bookmark_store.py not yet extracted from v1.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from owlbear_knowledge import init_db
from owlbear_knowledge.bookmark_store import Bookmark, BookmarkStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_bookmark(
    url: str = "https://example.com",
    scope: str = "global",
    **kwargs: object,
) -> Bookmark:
    return Bookmark(  # type: ignore[arg-type]
        url=url,
        title="Test Title",
        created_at=_now(),
        updated_at=_now(),
        scope=scope,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Bookmark model — fields, defaults, immutability
# ---------------------------------------------------------------------------


class TestFromAC_BookmarkModel:  # noqa: N801
    """Bookmark is a frozen Pydantic BaseModel with correct fields and defaults."""

    def test_bookmark_id_defaults_to_32char_hex(self) -> None:
        b = _make_bookmark()
        assert isinstance(b.id, str)
        assert len(b.id) == 32
        assert b.id.isalnum()

    def test_bookmark_id_unique_per_instance(self) -> None:
        b1 = _make_bookmark()
        b2 = _make_bookmark(url="https://other.com")
        assert b1.id != b2.id

    def test_bookmark_fields_required_are_set(self) -> None:
        b = Bookmark(url="https://req.com", title="Req Test", created_at=_now(), updated_at=_now())
        assert b.url == "https://req.com"
        assert b.title == "Req Test"

    def test_bookmark_tags_default_empty_list(self) -> None:
        b = _make_bookmark()
        assert b.tags == []

    def test_bookmark_relevance_score_default_zero(self) -> None:
        b = _make_bookmark()
        assert b.relevance_score == 0.0

    def test_bookmark_scope_default_global(self) -> None:
        b = Bookmark(url="https://x.com", title="T", created_at=_now(), updated_at=_now())
        assert b.scope == "global"

    def test_bookmark_description_optional_defaults_none(self) -> None:
        b = _make_bookmark()
        assert b.description is None

    def test_bookmark_reason_optional_defaults_none(self) -> None:
        b = _make_bookmark()
        assert b.reason is None

    def test_bookmark_document_id_optional_defaults_none(self) -> None:
        b = _make_bookmark()
        assert b.document_id is None

    def test_bookmark_content_hash_optional_defaults_none(self) -> None:
        b = _make_bookmark()
        assert b.content_hash is None

    def test_bookmark_is_frozen_raises_on_assignment(self) -> None:
        b = _make_bookmark()
        with pytest.raises(ValidationError):
            b.url = "https://mutated.com"  # type: ignore[misc]

    def test_relevance_score_exactly_zero_is_valid(self) -> None:
        b = _make_bookmark(relevance_score=0.0)
        assert b.relevance_score == 0.0

    def test_relevance_score_exactly_one_is_valid(self) -> None:
        b = _make_bookmark(relevance_score=1.0)
        assert b.relevance_score == 1.0

    def test_relevance_score_below_zero_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            _make_bookmark(relevance_score=-0.01)

    def test_relevance_score_above_one_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            _make_bookmark(relevance_score=1.01)

    def test_bookmark_accepts_all_optional_fields(self) -> None:
        b = _make_bookmark(
            description="A description",
            tags=["tag1", "tag2"],
            relevance_score=0.75,
            reason="found during research",
            document_id="doc-1",
            content_hash="abc123",
        )
        assert b.description == "A description"
        assert b.tags == ["tag1", "tag2"]
        assert b.relevance_score == 0.75
        assert b.reason == "found during research"
        assert b.document_id == "doc-1"
        assert b.content_hash == "abc123"


# ---------------------------------------------------------------------------
# Import path and __init__.py exports
# ---------------------------------------------------------------------------


class TestFromAC_Exports:  # noqa: N801
    """Bookmark and BookmarkStore importable from owlbear_knowledge.bookmark_store and __all__."""

    def test_bookmark_importable_from_bookmark_store_module(self) -> None:
        from owlbear_knowledge.bookmark_store import Bookmark  # noqa: PLC0415

        assert Bookmark is not None

    def test_bookmarkstore_importable_from_bookmark_store_module(self) -> None:
        from owlbear_knowledge.bookmark_store import BookmarkStore  # noqa: PLC0415

        assert BookmarkStore is not None

    def test_bookmark_importable_from_package(self) -> None:
        from owlbear_knowledge import Bookmark  # noqa: PLC0415

        assert Bookmark is not None

    def test_bookmarkstore_importable_from_package(self) -> None:
        from owlbear_knowledge import BookmarkStore  # noqa: PLC0415

        assert BookmarkStore is not None

    def test_bookmark_in_package_all(self) -> None:
        import owlbear_knowledge  # noqa: PLC0415

        assert "Bookmark" in owlbear_knowledge.__all__

    def test_bookmarkstore_in_package_all(self) -> None:
        import owlbear_knowledge  # noqa: PLC0415

        assert "BookmarkStore" in owlbear_knowledge.__all__


# ---------------------------------------------------------------------------
# No forbidden imports
# ---------------------------------------------------------------------------


class TestFromAC_NoDeps:  # noqa: N801
    """bookmark_store.py has no PydanticAI, daemon, or hook imports; no external deps beyond pydantic."""

    def test_no_pydanticai_import(self) -> None:
        import inspect  # noqa: PLC0415

        import owlbear_knowledge.bookmark_store as bm  # noqa: PLC0415

        source = inspect.getsource(bm)
        assert "pydantic_ai" not in source
        assert "pydanticai" not in source.lower()

    def test_no_daemon_import(self) -> None:
        import inspect  # noqa: PLC0415

        import owlbear_knowledge.bookmark_store as bm  # noqa: PLC0415

        source = inspect.getsource(bm)
        assert "import daemon" not in source
        assert "from daemon" not in source

    def test_no_hook_import(self) -> None:
        import inspect  # noqa: PLC0415

        import owlbear_knowledge.bookmark_store as bm  # noqa: PLC0415

        source = inspect.getsource(bm)
        assert "import hook" not in source.lower()
        assert "from hook" not in source.lower()


# ---------------------------------------------------------------------------
# BookmarkStore — create
# ---------------------------------------------------------------------------


class TestFromAC_BookmarkStoreCreate:  # noqa: N801
    """BookmarkStore.create inserts and returns the bookmark; raises IntegrityError on duplicate."""

    def test_create_returns_same_bookmark_object(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://create.example.com")
        result = store.create(b)
        assert result is b

    def test_create_persists_row_to_db(self) -> None:
        db = _make_db()
        store = BookmarkStore(db)
        b = _make_bookmark(url="https://persist.example.com")
        store.create(b)
        row = db.execute("SELECT id FROM bookmarks WHERE url = ?", (b.url,)).fetchone()
        assert row is not None
        assert row[0] == b.id

    def test_create_duplicate_url_scope_raises_integrity_error(self) -> None:
        store = BookmarkStore(_make_db())
        b1 = _make_bookmark(url="https://dup.example.com", scope="global")
        b2 = _make_bookmark(url="https://dup.example.com", scope="global")
        store.create(b1)
        with pytest.raises(sqlite3.IntegrityError):
            store.create(b2)

    def test_create_same_url_different_scope_both_succeed(self) -> None:
        store = BookmarkStore(_make_db())
        b1 = _make_bookmark(url="https://scope.example.com", scope="global")
        b2 = _make_bookmark(url="https://scope.example.com", scope="project")
        store.create(b1)
        store.create(b2)  # must not raise

    def test_create_persists_all_optional_fields(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(
            url="https://full.example.com",
            description="desc",
            tags=["a", "b"],
            relevance_score=0.75,
            reason="from research",
            document_id="doc-1",
            content_hash="hash123",
        )
        store.create(b)
        result = store.get_by_url("https://full.example.com")
        assert result is not None
        assert result.description == "desc"
        assert result.relevance_score == 0.75
        assert result.reason == "from research"
        assert result.document_id == "doc-1"
        assert result.content_hash == "hash123"


# ---------------------------------------------------------------------------
# BookmarkStore — get_by_url
# ---------------------------------------------------------------------------


class TestFromAC_BookmarkStoreGetByUrl:  # noqa: N801
    """BookmarkStore.get_by_url returns Bookmark or None; default scope is 'global'."""

    def test_get_by_url_returns_bookmark_when_found(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://get.example.com")
        store.create(b)
        result = store.get_by_url("https://get.example.com")
        assert result is not None
        assert result.id == b.id
        assert result.url == "https://get.example.com"

    def test_get_by_url_returns_none_when_not_found(self) -> None:
        store = BookmarkStore(_make_db())
        assert store.get_by_url("https://missing.example.com") is None

    def test_get_by_url_default_scope_is_global(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://defscope.example.com", scope="global")
        store.create(b)
        result = store.get_by_url("https://defscope.example.com")  # no scope kwarg
        assert result is not None
        assert result.id == b.id

    def test_get_by_url_returns_none_with_wrong_scope(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://wrongscope.example.com", scope="project")
        store.create(b)
        result = store.get_by_url("https://wrongscope.example.com", scope="global")
        assert result is None

    def test_get_by_url_with_explicit_correct_scope(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://team.example.com", scope="team")
        store.create(b)
        result = store.get_by_url("https://team.example.com", scope="team")
        assert result is not None
        assert result.scope == "team"


# ---------------------------------------------------------------------------
# BookmarkStore — list
# ---------------------------------------------------------------------------


class TestFromAC_BookmarkStoreList:  # noqa: N801
    """BookmarkStore.list returns filtered bookmarks; all filters are optional."""

    def test_list_no_filters_returns_all(self) -> None:
        store = BookmarkStore(_make_db())
        b1 = _make_bookmark(url="https://a.com")
        b2 = _make_bookmark(url="https://b.com")
        store.create(b1)
        store.create(b2)
        results = store.list()
        ids = {b.id for b in results}
        assert b1.id in ids
        assert b2.id in ids

    def test_list_empty_db_returns_empty_list(self) -> None:
        store = BookmarkStore(_make_db())
        assert store.list() == []

    def test_list_filter_by_scope_returns_only_matching(self) -> None:
        store = BookmarkStore(_make_db())
        global_b = _make_bookmark(url="https://g.com", scope="global")
        project_b = _make_bookmark(url="https://p.com", scope="project")
        store.create(global_b)
        store.create(project_b)
        results = store.list(scope="project")
        ids = {b.id for b in results}
        assert project_b.id in ids
        assert global_b.id not in ids

    def test_list_filter_by_tag_uses_substring_match(self) -> None:
        store = BookmarkStore(_make_db())
        tagged = _make_bookmark(url="https://tagged.com", tags=["python", "tdd"])
        other = _make_bookmark(url="https://other.com", tags=["java"])
        store.create(tagged)
        store.create(other)
        results = store.list(tag="python")
        ids = {b.id for b in results}
        assert tagged.id in ids
        assert other.id not in ids

    def test_list_filter_by_min_score_excludes_below_threshold(self) -> None:
        store = BookmarkStore(_make_db())
        high = _make_bookmark(url="https://high.com", relevance_score=0.9)
        low = _make_bookmark(url="https://low.com", relevance_score=0.3)
        store.create(high)
        store.create(low)
        results = store.list(min_score=0.5)
        ids = {b.id for b in results}
        assert high.id in ids
        assert low.id not in ids

    def test_list_min_score_includes_exact_boundary(self) -> None:
        store = BookmarkStore(_make_db())
        exact = _make_bookmark(url="https://exact.com", relevance_score=0.5)
        store.create(exact)
        results = store.list(min_score=0.5)
        assert any(b.id == exact.id for b in results)

    def test_list_all_three_filters_combined(self) -> None:
        store = BookmarkStore(_make_db())
        match = _make_bookmark(
            url="https://match.com", scope="project", tags=["ml"], relevance_score=0.8
        )
        low_score = _make_bookmark(
            url="https://low.com", scope="project", tags=["ml"], relevance_score=0.2
        )
        store.create(match)
        store.create(low_score)
        results = store.list(scope="project", tag="ml", min_score=0.7)
        ids = {b.id for b in results}
        assert match.id in ids
        assert low_score.id not in ids

    def test_list_scope_filter_returns_empty_when_no_match(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://x.com", scope="global")
        store.create(b)
        assert store.list(scope="nonexistent-scope") == []


# ---------------------------------------------------------------------------
# BookmarkStore — update_tags
# ---------------------------------------------------------------------------


class TestFromAC_BookmarkStoreUpdateTags:  # noqa: N801
    """BookmarkStore.update_tags replaces tags column; raises ValueError if id not found."""

    def test_update_tags_replaces_existing_tags(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://update.com", tags=["old"])
        store.create(b)
        store.update_tags(b.id, ["new1", "new2"])
        result = store.get_by_url("https://update.com")
        assert result is not None
        assert result.tags == ["new1", "new2"]

    def test_update_tags_with_empty_list_clears_tags(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://clear.com", tags=["a", "b"])
        store.create(b)
        store.update_tags(b.id, [])
        result = store.get_by_url("https://clear.com")
        assert result is not None
        assert result.tags == []

    def test_update_tags_raises_value_error_when_id_not_found(self) -> None:
        store = BookmarkStore(_make_db())
        with pytest.raises(ValueError, match="not found"):
            store.update_tags("nonexistent-id", ["tag"])

    def test_update_tags_does_not_affect_other_bookmarks(self) -> None:
        store = BookmarkStore(_make_db())
        b1 = _make_bookmark(url="https://b1.com", tags=["orig"])
        b2 = _make_bookmark(url="https://b2.com", tags=["keep"])
        store.create(b1)
        store.create(b2)
        store.update_tags(b1.id, ["changed"])
        result2 = store.get_by_url("https://b2.com")
        assert result2 is not None
        assert result2.tags == ["keep"]


# ---------------------------------------------------------------------------
# BookmarkStore — delete
# ---------------------------------------------------------------------------


class TestFromAC_BookmarkStoreDelete:  # noqa: N801
    """BookmarkStore.delete removes bookmark row; raises ValueError if id not found."""

    def test_delete_removes_bookmark_from_db(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://delete.com")
        store.create(b)
        store.delete(b.id)
        assert store.get_by_url("https://delete.com") is None

    def test_delete_raises_value_error_when_id_not_found(self) -> None:
        store = BookmarkStore(_make_db())
        with pytest.raises(ValueError, match="not found"):
            store.delete("nonexistent-id")

    def test_delete_does_not_affect_other_bookmarks(self) -> None:
        store = BookmarkStore(_make_db())
        b1 = _make_bookmark(url="https://d1.com")
        b2 = _make_bookmark(url="https://d2.com")
        store.create(b1)
        store.create(b2)
        store.delete(b1.id)
        assert store.get_by_url("https://d2.com") is not None


# ---------------------------------------------------------------------------
# Tag serialization round-trip
# ---------------------------------------------------------------------------


class TestFromAC_TagSerialization:  # noqa: N801
    """Tags serialized as JSON string in db column; deserialized back to list[str] on read."""

    def test_tags_round_trip_from_create_to_get(self) -> None:
        store = BookmarkStore(_make_db())
        tags = ["python", "tdd", "knowledge"]
        b = _make_bookmark(url="https://tags.com", tags=tags)
        store.create(b)
        result = store.get_by_url("https://tags.com")
        assert result is not None
        assert result.tags == tags

    def test_tags_stored_as_json_string_in_raw_column(self) -> None:
        import json  # noqa: PLC0415

        db = _make_db()
        store = BookmarkStore(db)
        tags = ["alpha", "beta"]
        b = _make_bookmark(url="https://raw.com", tags=tags)
        store.create(b)
        row = db.execute("SELECT tags FROM bookmarks WHERE url = ?", (b.url,)).fetchone()
        assert row is not None
        assert json.loads(row[0]) == tags

    def test_empty_tags_round_trip(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://empty-tags.com", tags=[])
        store.create(b)
        result = store.get_by_url("https://empty-tags.com")
        assert result is not None
        assert result.tags == []

    def test_tags_round_trip_via_list(self) -> None:
        store = BookmarkStore(_make_db())
        tags = ["x", "y", "z"]
        b = _make_bookmark(url="https://list-tags.com", tags=tags)
        store.create(b)
        results = store.list(tag="y")
        assert any(r.tags == tags for r in results)

    def test_updated_tags_deserialize_correctly(self) -> None:
        store = BookmarkStore(_make_db())
        b = _make_bookmark(url="https://upd-tags.com", tags=["old"])
        store.create(b)
        new_tags = ["new1", "new2", "new3"]
        store.update_tags(b.id, new_tags)
        result = store.get_by_url("https://upd-tags.com")
        assert result is not None
        assert result.tags == new_tags
