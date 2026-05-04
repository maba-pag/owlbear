"""Failing tests for Qdrant filesystem persistence + source identity (task #1319).

Covers (TDD RED phase):
  - AC3: IngestPipeline.ingest_text() registers/resolves KnowledgeSource and sets
         documents.source_id FK before storing chunks (td:2)
  - AC4: KnowledgeSource model stores fetch_method (str) and enrich (bool) as top-level
         model fields and schema columns, not config keys (td:1)
  - AC5: KnowledgeSourceStore resolves source identity by URL and by file path via
         knowledge_sources.id UUID FK — not document_status.source string (td:2)
  - AC6: Per-source enrich flag (true/false) is readable on KnowledgeSource record (td:1)

Note: AC1 (Qdrant filesystem persistence) and AC2 (SQLite disk persistence) test existing
library primitives that already work with `path=` / file-backed connections — no failing
tests are possible for them; builder adds coverage tests when implementing AC3-AC6.

All tests in this file must FAIL until task #1320 implements the required additions.
Run with: uv run pytest tests/test_qdrant_source_identity_1319.py
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_source(
    *,
    name: str = "Test Source",
    source_type: SourceType = SourceType.URL_LIST,
    fetch_method: str = "http",
    enrich: bool = False,
) -> KnowledgeSource:
    """Build a KnowledgeSource with fetch_method and enrich fields."""
    now = _now()
    return KnowledgeSource(
        name=name,
        source_type=source_type,
        fetch_method=fetch_method,
        enrich=enrich,
        created_at=now,
        updated_at=now,
    )


def _make_legacy_source(
    *,
    name: str = "Legacy Source",
    source_type: SourceType = SourceType.URL_LIST,
    source_id: str | None = None,
) -> KnowledgeSource:
    """Build a KnowledgeSource using the current model fields only (no fetch_method/enrich)."""
    now = _now()
    kwargs: dict = {
        "name": name,
        "source_type": source_type,
        "created_at": now,
        "updated_at": now,
    }
    if source_id is not None:
        kwargs["id"] = source_id
    return KnowledgeSource(**kwargs)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """In-memory SQLite connection with fully initialised schema."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


@pytest.fixture
def source_store(db_conn: sqlite3.Connection) -> KnowledgeSourceStore:
    """KnowledgeSourceStore backed by the in-memory db_conn fixture."""
    return KnowledgeSourceStore(db_conn)


@pytest.fixture
def minimal_pipeline() -> IngestPipeline:
    """IngestPipeline with all dependencies mocked for contract testing."""
    mock_chunker = MagicMock()
    mock_chunker.chunk.return_value = []  # no chunks — simplest ingest path

    mock_extractor = MagicMock()
    mock_extractor.extract = AsyncMock(return_value=MagicMock(entities=[], edges=[]))

    mock_docs = MagicMock()
    mock_docs.insert_document.return_value = None
    mock_docs.store_chunks.return_value = []
    mock_docs.store_embeddings.return_value = None
    mock_docs.store_extractions.return_value = (0, 0)

    return IngestPipeline(
        document_store=mock_docs,
        entity_extractor=mock_extractor,
        text_chunker=mock_chunker,
    )


# ---------------------------------------------------------------------------
# AC3: IngestPipeline registers/resolves source and sets documents.source_id FK
# (td:2 — happy + edge)
# ---------------------------------------------------------------------------


class TestFromAC_IngestSourceRegistration:
    @pytest.mark.asyncio
    async def test_ingest_text_with_source_id_sets_document_source_id_fk(
        self, minimal_pipeline: IngestPipeline
    ) -> None:
        """AC3 happy: ingest_text() accepts source_id and stores it as document FK.

        The method must accept source_id as a keyword argument and pass it through
        to the document store so documents.source_id is populated.
        Currently FAILS: TypeError — source_id is not a valid parameter.
        """
        source_id = "test-source-uuid-abc123"
        result = await minimal_pipeline.ingest_text(
            "Hello world content", source_id=source_id
        )
        assert result.status == "ok"

        # Verify insert_document was called with source_id set
        mock_docs = minimal_pipeline._docs  # type: ignore[attr-defined]
        call_kwargs = mock_docs.insert_document.call_args
        assert call_kwargs is not None, "insert_document was not called"
        # The source_id must appear either as a kwarg or be embedded in the doc
        actual_source_id = call_kwargs.kwargs.get("source_id")
        assert actual_source_id == source_id, (
            f"Expected source_id={source_id!r} but got {actual_source_id!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_text_resolves_same_source_id_idempotently(
        self, minimal_pipeline: IngestPipeline
    ) -> None:
        """AC3 edge: two ingest_text() calls with the same source_id use the same FK.

        Idempotent resolution: the source_id FK should be identical across both
        calls rather than generating a new UUID each time.
        Currently FAILS: TypeError — source_id is not a valid parameter.
        """
        source_id = "stable-source-uuid-deadbeef"
        mock_docs = minimal_pipeline._docs  # type: ignore[attr-defined]

        await minimal_pipeline.ingest_text("First document", source_id=source_id)
        await minimal_pipeline.ingest_text("Second document", source_id=source_id)

        assert mock_docs.insert_document.call_count == 2, (
            "Expected insert_document to be called twice"
        )

        # Both calls must use the same source_id FK
        for call in mock_docs.insert_document.call_args_list:
            actual = call.kwargs.get("source_id")
            assert actual == source_id, (
                f"Expected source_id={source_id!r} in both calls, got {actual!r}"
            )


# ---------------------------------------------------------------------------
# AC4: KnowledgeSource model and schema have fetch_method + enrich top-level
# (td:1 — model fields + schema columns)
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeSourceFields:
    def test_knowledge_source_model_has_fetch_method_as_declared_field(self) -> None:
        """AC4: fetch_method is a top-level declared model field, not a config key.

        Currently FAILS: 'fetch_method' is not in KnowledgeSource.model_fields.
        """
        assert "fetch_method" in KnowledgeSource.model_fields, (
            "KnowledgeSource.model_fields must declare 'fetch_method' as a top-level field"
        )

    def test_knowledge_source_model_has_enrich_as_declared_bool_field(self) -> None:
        """AC4: enrich is a top-level declared bool model field, not a config key.

        Currently FAILS: 'enrich' is not in KnowledgeSource.model_fields.
        """
        assert "enrich" in KnowledgeSource.model_fields, (
            "KnowledgeSource.model_fields must declare 'enrich' as a top-level bool field"
        )

    def test_knowledge_source_fetch_method_round_trips_through_store(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC4: fetch_method persists and round-trips through KnowledgeSourceStore.

        Creates a source with fetch_method='http', persists, reopens, asserts value.
        Currently FAILS: fetch_method field absent from model → AttributeError.
        """
        store = KnowledgeSourceStore(db_conn)
        source = _make_source(fetch_method="http")
        store.create(source)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.fetch_method == "http"  # type: ignore[attr-defined]

    def test_knowledge_source_enrich_round_trips_through_store(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC4: enrich flag persists and round-trips through KnowledgeSourceStore.

        Creates a source with enrich=True, persists, reopens, asserts value.
        Currently FAILS: enrich field absent from model → AttributeError.
        """
        store = KnowledgeSourceStore(db_conn)
        source = _make_source(enrich=True)
        store.create(source)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.enrich is True  # type: ignore[attr-defined]

    def test_schema_knowledge_sources_table_has_fetch_method_column(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC4: knowledge_sources table has fetch_method as a schema column, not in config JSON.

        Currently FAILS: column absent from DDL / init_db() migration.
        """
        columns = [
            row[1]
            for row in db_conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()
        ]
        assert "fetch_method" in columns, (
            f"knowledge_sources schema must have 'fetch_method' column; found: {columns}"
        )

    def test_schema_knowledge_sources_table_has_enrich_column(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC4: knowledge_sources table has enrich as a schema column, not in config JSON.

        Currently FAILS: column absent from DDL / init_db() migration.
        """
        columns = [
            row[1]
            for row in db_conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()
        ]
        assert "enrich" in columns, (
            f"knowledge_sources schema must have 'enrich' column; found: {columns}"
        )


# ---------------------------------------------------------------------------
# AC5: KnowledgeSourceStore resolves by URL and by file path
# (td:2 — happy x2 + edge)
# ---------------------------------------------------------------------------


class TestFromAC_SourceIdentityResolution:
    def test_resolve_by_url_returns_source_with_matching_uuid_fk(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC5 happy: resolve_by_url() returns the source whose config.url matches.

        Assertion targets knowledge_sources.id UUID FK — NOT document_status.source string.
        Currently FAILS: AttributeError — KnowledgeSourceStore has no resolve_by_url().
        """
        store = KnowledgeSourceStore(db_conn)
        now = _now()
        source = KnowledgeSource(
            name="Web Source",
            source_type=SourceType.URL_LIST,
            config={"url": "https://docs.example.com"},
            created_at=now,
            updated_at=now,
        )
        store.create(source)

        resolved = store.resolve_by_url("https://docs.example.com")  # type: ignore[attr-defined]
        assert resolved is not None
        assert resolved.id == source.id, (
            "resolve_by_url must return the source with matching knowledge_sources.id UUID"
        )

    def test_resolve_by_path_returns_source_with_matching_uuid_fk(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC5 happy: resolve_by_path() returns the source whose config.path matches.

        Assertion targets knowledge_sources.id UUID FK — NOT document_status.source string.
        Currently FAILS: AttributeError — KnowledgeSourceStore has no resolve_by_path().
        """
        store = KnowledgeSourceStore(db_conn)
        now = _now()
        source = KnowledgeSource(
            name="File Source",
            source_type=SourceType.FILE_GLOB,
            config={"path": "/workspace/docs/**/*.md"},
            created_at=now,
            updated_at=now,
        )
        store.create(source)

        resolved = store.resolve_by_path("/workspace/docs/**/*.md")  # type: ignore[attr-defined]
        assert resolved is not None
        assert resolved.id == source.id, (
            "resolve_by_path must return the source with matching knowledge_sources.id UUID"
        )

    def test_resolve_by_url_returns_none_when_url_not_registered(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC5 edge: resolve_by_url() returns None when the URL has no matching source.

        Currently FAILS: AttributeError — KnowledgeSourceStore has no resolve_by_url().
        """
        store = KnowledgeSourceStore(db_conn)
        resolved = store.resolve_by_url("https://unknown.example.com")  # type: ignore[attr-defined]
        assert resolved is None, "resolve_by_url must return None for unregistered URLs"


# ---------------------------------------------------------------------------
# AC6: Per-source enrich flag is readable on the KnowledgeSource record
# (td:1 — true + false boundary)
# ---------------------------------------------------------------------------


class TestFromAC_EnrichFlag:
    def test_enrich_true_is_readable_on_source_record(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC6: enrich=True is readable as a top-level attribute on a persisted record.

        Does NOT test enrichment worker/queue machinery — only the flag value on record.
        Currently FAILS: 'enrich' field does not exist on KnowledgeSource model.
        """
        store = KnowledgeSourceStore(db_conn)
        source = _make_source(enrich=True)
        store.create(source)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.enrich is True  # type: ignore[attr-defined]

    def test_enrich_false_is_readable_on_source_record(
        self, db_conn: sqlite3.Connection
    ) -> None:
        """AC6: enrich=False is readable as a top-level attribute on a persisted record.

        Does NOT test enrichment worker/queue machinery — only the flag value on record.
        Currently FAILS: 'enrich' field does not exist on KnowledgeSource model.
        """
        store = KnowledgeSourceStore(db_conn)
        source = _make_source(enrich=False)
        store.create(source)

        retrieved = store.get(source.id)
        assert retrieved is not None
        assert retrieved.enrich is False  # type: ignore[attr-defined]
