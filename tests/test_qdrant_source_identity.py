"""Tests for Qdrant filesystem persistence + source identity (task #1319).

Covers:
  - AC1: QdrantVectorStore filesystem persistence via same-path recreate/retrieve (td:1)
  - AC2: SQLite file-backed persistence across close/reopen (td:1)
  - AC3: IngestPipeline registers/resolves KnowledgeSource and sets documents.source_id FK
         before storing chunks — REAL REGISTRATION CONTRACT, not just passthrough (td:2)
  - AC4: KnowledgeSource model stores all named first-class fields as top-level model fields
         and schema columns, not config keys (td:1)
  - AC5: KnowledgeSourceStore resolves source identity by URL and by file path via
         knowledge_sources.id UUID FK — not document_status.source string (td:2)
  - AC6: Per-source enrich flag (true/false) is readable on KnowledgeSource record (td:1)

Run with: uv run pytest tests/test_qdrant_source_identity_1319.py
"""

from __future__ import annotations

import json as _json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore

# ---------------------------------------------------------------------------
# Qdrant availability guard (optional dependency)
# ---------------------------------------------------------------------------

try:
    import qdrant_client as _qdrant_client  # noqa: F401

    from owlbear_knowledge.qdrant import DENSE_DIM, QdrantVectorStore

    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    DENSE_DIM = 1024  # type: ignore[assignment]
    QdrantVectorStore = None  # type: ignore[assignment,misc]

_skip_no_qdrant = pytest.mark.skipif(
    not _QDRANT_AVAILABLE,
    reason="qdrant-client not installed — uv pip install 'owlbear-knowledge[qdrant]'",
)


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
        result = await minimal_pipeline.ingest_text("Hello world content", source_id=source_id)
        assert result.status == "ok"

        # Verify insert_document was called with source_id set
        mock_docs = minimal_pipeline._docs  # type: ignore[attr-defined]
        call_kwargs = mock_docs.insert_document.call_args
        assert call_kwargs is not None, "insert_document was not called"
        # The source_id must appear either as a kwarg or be embedded in the doc
        actual_source_id = call_kwargs.kwargs.get("source_id")
        assert actual_source_id == source_id, f"Expected source_id={source_id!r} but got {actual_source_id!r}"

    @pytest.mark.asyncio
    async def test_ingest_text_resolves_same_source_id_idempotently(self, minimal_pipeline: IngestPipeline) -> None:
        """AC3 edge: two ingest_text() calls with the same source_id use the same FK.

        Idempotent resolution: the source_id FK should be identical across both
        calls rather than generating a new UUID each time.
        Currently FAILS: TypeError — source_id is not a valid parameter.
        """
        source_id = "stable-source-uuid-deadbeef"
        mock_docs = minimal_pipeline._docs  # type: ignore[attr-defined]

        await minimal_pipeline.ingest_text("First document", source_id=source_id)
        await minimal_pipeline.ingest_text("Second document", source_id=source_id)

        assert mock_docs.insert_document.call_count == 2, "Expected insert_document to be called twice"

        # Both calls must use the same source_id FK
        for call in mock_docs.insert_document.call_args_list:
            actual = call.kwargs.get("source_id")
            assert actual == source_id, f"Expected source_id={source_id!r} in both calls, got {actual!r}"


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

    def test_knowledge_source_fetch_method_round_trips_through_store(self, db_conn: sqlite3.Connection) -> None:
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

    def test_knowledge_source_enrich_round_trips_through_store(self, db_conn: sqlite3.Connection) -> None:
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

    def test_schema_knowledge_sources_table_has_fetch_method_column(self, db_conn: sqlite3.Connection) -> None:
        """AC4: knowledge_sources table has fetch_method as a schema column, not in config JSON.

        Currently FAILS: column absent from DDL / init_db() migration.
        """
        columns = [row[1] for row in db_conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()]
        assert "fetch_method" in columns, f"knowledge_sources schema must have 'fetch_method' column; found: {columns}"

    def test_schema_knowledge_sources_table_has_enrich_column(self, db_conn: sqlite3.Connection) -> None:
        """AC4: knowledge_sources table has enrich as a schema column, not in config JSON.

        Currently FAILS: column absent from DDL / init_db() migration.
        """
        columns = [row[1] for row in db_conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()]
        assert "enrich" in columns, f"knowledge_sources schema must have 'enrich' column; found: {columns}"


# ---------------------------------------------------------------------------
# AC5: KnowledgeSourceStore resolves by URL and by file path
# (td:2 — happy x2 + edge)
# ---------------------------------------------------------------------------


class TestFromAC_SourceIdentityResolution:
    def test_resolve_by_url_returns_source_with_matching_uuid_fk(self, db_conn: sqlite3.Connection) -> None:
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
        assert resolved.id == source.id, "resolve_by_url must return the source with matching knowledge_sources.id UUID"

    def test_resolve_by_path_returns_source_with_matching_uuid_fk(self, db_conn: sqlite3.Connection) -> None:
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

    def test_resolve_by_url_returns_none_when_url_not_registered(self, db_conn: sqlite3.Connection) -> None:
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
    def test_enrich_true_is_readable_on_source_record(self, db_conn: sqlite3.Connection) -> None:
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

    def test_enrich_false_is_readable_on_source_record(self, db_conn: sqlite3.Connection) -> None:
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


# ---------------------------------------------------------------------------
# AC1: QdrantVectorStore filesystem persistence (td:1)
# Tests the library primitive: store via path=, destroy, re-create, retrieve.
# ---------------------------------------------------------------------------


@_skip_no_qdrant
class TestFromAC_QdrantFilesystemPersistence:
    """AC1: QdrantVectorStore persists vectors across instance recreation via filesystem path."""

    def test_qdrant_filesystem_store_survives_instance_recreation(self, tmp_path: pytest.TempPathFactory) -> None:
        """AC1 happy: store embedding, delete instance, re-create with same path, retrieve succeeds.

        QdrantVectorStore(location=<path>) must persist data across Python instances.
        """
        path = str(tmp_path / "qdrant_persist")
        chunk_id = "persist-chunk-abc123"
        dense = [0.12] * DENSE_DIM

        store1 = QdrantVectorStore(location=path)
        store1.store_embedding(chunk_id, dense, "document", scope="global")
        del store1

        store2 = QdrantVectorStore(location=path)
        retrieved = store2.get_embedding(chunk_id)
        assert retrieved is not None, (
            "QdrantVectorStore must retrieve a vector stored by a prior instance on the same path"
        )

    def test_qdrant_different_filesystem_paths_are_isolated(self, tmp_path: pytest.TempPathFactory) -> None:
        """AC1 boundary: two different filesystem paths have separate, non-overlapping collections."""
        path_a = str(tmp_path / "qdrant_a")
        path_b = str(tmp_path / "qdrant_b")
        chunk_id = "isolated-chunk-xyz"
        dense = [0.5] * DENSE_DIM

        store_a = QdrantVectorStore(location=path_a)
        store_a.store_embedding(chunk_id, dense, "document")

        store_b = QdrantVectorStore(location=path_b)
        result = store_b.get_embedding(chunk_id)
        assert result is None, "Vector stored on path_a must NOT be visible on path_b — paths must be isolated"

    def test_qdrant_filesystem_store_retrieves_matching_vector_content(self, tmp_path: pytest.TempPathFactory) -> None:
        """AC1 content: retrieved vector must match stored vector element-wise (within 1e-6).

        Strengthens AC1 beyond presence check: a wrong or corrupted payload must fail.
        Existing test only asserts non-None; this test proves the correct payload is returned.
        """
        path = str(tmp_path / "qdrant_content_check")
        chunk_id = "content-check-chunk-001"
        # Non-uniform vector so any wrong payload is detectable
        dense = [float(i) / DENSE_DIM for i in range(DENSE_DIM)]

        store1 = QdrantVectorStore(location=path)
        store1.store_embedding(chunk_id, dense, "document", scope="global")
        del store1

        store2 = QdrantVectorStore(location=path)
        retrieved = store2.get_embedding(chunk_id)

        assert retrieved is not None, "Vector must survive instance recreation"
        assert len(retrieved) == len(dense), f"Retrieved vector length {len(retrieved)} != stored {len(dense)}"
        for i, (got, want) in enumerate(zip(retrieved, dense, strict=True)):
            assert abs(got - want) < 1e-6, (
                f"Retrieved vector[{i}] = {got!r} differs from stored {want!r} beyond tolerance 1e-6"
            )


# ---------------------------------------------------------------------------
# AC2: SQLite file-backed persistence across close/reopen (td:1)
# Tests init_db + KnowledgeSourceStore.create with a real file path.
# ---------------------------------------------------------------------------


class TestFromAC_SQLiteDiskPersistence:
    """AC2: SQLite KnowledgeSourceStore persists rows across close/reopen of a file-backed DB."""

    def test_sqlite_file_backed_source_survives_close_reopen(self, tmp_path: pytest.TempPathFactory) -> None:
        """AC2 happy: create source, close connection, reopen same file, verify row persists.

        init_db must initialise the schema on a file-path connection.
        KnowledgeSourceStore.create must flush to disk so a fresh connection can read it.
        """
        db_path = str(tmp_path / "knowledge.db")

        # Phase 1: create and close
        conn1 = sqlite3.connect(db_path)
        init_db(conn1)
        store1 = KnowledgeSourceStore(conn1)
        source = _make_source(name="Persisted Source")
        store1.create(source)
        conn1.close()

        # Phase 2: reopen and verify
        conn2 = sqlite3.connect(db_path)
        store2 = KnowledgeSourceStore(conn2)
        retrieved = store2.get(source.id)
        conn2.close()

        assert retrieved is not None, "KnowledgeSourceStore.get must find the row after connection close/reopen"
        assert retrieved.id == source.id
        assert retrieved.name == "Persisted Source"

    def test_sqlite_file_backed_multiple_sources_survive_reopen(self, tmp_path: pytest.TempPathFactory) -> None:
        """AC2 boundary: multiple rows inserted, all survive close/reopen."""
        db_path = str(tmp_path / "knowledge_multi.db")

        conn1 = sqlite3.connect(db_path)
        init_db(conn1)
        store1 = KnowledgeSourceStore(conn1)
        sources = [_make_source(name=f"Source-{i}") for i in range(3)]
        for s in sources:
            store1.create(s)
        conn1.close()

        conn2 = sqlite3.connect(db_path)
        store2 = KnowledgeSourceStore(conn2)
        all_rows = store2.list_all()
        conn2.close()

        assert len(all_rows) == 3, f"All 3 inserted sources must survive close/reopen; found {len(all_rows)}"
        persisted_ids = {r.id for r in all_rows}
        expected_ids = {s.id for s in sources}
        assert persisted_ids == expected_ids


# ---------------------------------------------------------------------------
# AC4 strengthening: all 6 named first-class fields + not-config-key constraint
# (td:1 — full named-field set + column/not-config-key proof)
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeSourceAllNamedFields:
    """AC4: all 6 named fields are top-level model fields and schema columns, not config keys."""

    @pytest.mark.parametrize("field_name", ["name", "source_type", "created_at", "updated_at"])
    def test_remaining_ac4_named_fields_are_top_level_model_fields(self, field_name: str) -> None:
        """AC4: name, source_type, created_at, updated_at are declared as top-level model fields.

        Completes AC4 field coverage alongside the fetch_method/enrich tests above.
        """
        assert field_name in KnowledgeSource.model_fields, (
            f"KnowledgeSource.model_fields must declare '{field_name}' as a top-level field, "
            "not as a key inside the config dict"
        )

    @pytest.mark.parametrize("col_name", ["name", "source_type", "created_at", "updated_at"])
    def test_remaining_ac4_named_fields_are_schema_columns(self, col_name: str, db_conn: sqlite3.Connection) -> None:
        """AC4: name, source_type, created_at, updated_at are dedicated schema columns.

        These must appear as actual columns in PRAGMA table_info, not be stored inside
        the config JSON blob.
        """
        columns = [row[1] for row in db_conn.execute("PRAGMA table_info(knowledge_sources)").fetchall()]
        assert col_name in columns, f"knowledge_sources must have a dedicated '{col_name}' column; found: {columns}"

    def test_fetch_method_and_enrich_are_not_stored_as_config_json_keys(self, db_conn: sqlite3.Connection) -> None:
        """AC4 constraint: fetch_method/enrich are separate columns, NOT encoded in the config blob.

        Reads the raw row to verify the config JSON does not contain these fields as keys.
        """
        store = KnowledgeSourceStore(db_conn)
        source = _make_source(fetch_method="rss-feed", enrich=True)
        store.create(source)

        row = db_conn.execute(
            "SELECT config, fetch_method, enrich FROM knowledge_sources WHERE id = ?",
            (source.id,),
        ).fetchone()
        assert row is not None

        config_dict = _json.loads(row[0] or "{}")
        assert "fetch_method" not in config_dict, (
            "fetch_method must be a dedicated column, not a key in the config JSON blob"
        )
        assert "enrich" not in config_dict, "enrich must be a dedicated column, not a key in the config JSON blob"
        assert row[1] == "rss-feed", f"fetch_method column must be 'rss-feed', got {row[1]!r}"
        assert bool(row[2]) is True, f"enrich column must be 1 (True), got {row[2]!r}"


# ---------------------------------------------------------------------------
# AC3 REAL CONTRACT: IngestPipeline registers/resolves KnowledgeSource via
# source_store and sets the FK before storing chunks (td:2)
#
# These tests verify the contract the reviewer flagged as missing:
#   - Pipeline must accept a source_store dependency
#   - ingest_text() must accept source_url (not just a caller-provided source_id)
#   - Pipeline calls source_store.resolve_by_url() internally
#   - Resolved source.id becomes the documents.source_id FK
#   - Resolution precedes chunk storage (ordering proof)
#
# All tests in this class FAIL until IngestPipeline is extended with
# source_store constructor param and source_url auto-resolution logic.
# ---------------------------------------------------------------------------


class TestFromAC_IngestSourceResolutionContract:
    """AC3: Pipeline resolves KnowledgeSource via source_store and sets FK before chunks."""

    def _make_pipeline_with_source_store(
        self,
        source_store: object,
        *,
        chunk_count: int = 0,
    ) -> IngestPipeline:
        """Build a pipeline with a source_store injected and minimal mock dependencies."""
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [MagicMock(text="chunk")] * chunk_count

        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(return_value=MagicMock(entities=[], edges=[]))

        mock_docs = MagicMock()
        mock_docs.insert_document.return_value = None
        mock_docs.store_chunks.return_value = ["cid"] * chunk_count
        mock_docs.store_embeddings.return_value = None
        mock_docs.store_extractions.return_value = (0, 0)

        # FAILS: IngestPipeline.__init__ does not accept source_store
        return IngestPipeline(
            document_store=mock_docs,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
            source_store=source_store,
        )

    def test_ingest_pipeline_accepts_source_store_constructor_param(self) -> None:
        """AC3: IngestPipeline.__init__ must accept a source_store keyword argument.

        FAILS: TypeError — 'source_store' is not an accepted parameter.
        """
        mock_store = MagicMock()
        pipeline = IngestPipeline(
            document_store=MagicMock(),
            entity_extractor=MagicMock(),
            text_chunker=MagicMock(),
            source_store=mock_store,
        )
        assert pipeline._source_store is mock_store  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_ingest_text_accepts_source_url_keyword_argument(self) -> None:
        """AC3: ingest_text() must accept source_url as a keyword argument without TypeError.

        FAILS: TypeError — 'source_url' is not an accepted parameter.
        """
        mock_store = MagicMock()
        mock_store.resolve_by_url.return_value = MagicMock(id="src-uuid")
        pipeline = self._make_pipeline_with_source_store(mock_store)

        result = await pipeline.ingest_text("some content", source_url="https://docs.example.com")
        assert result.status in ("ok", "failed", "skipped", "cancelled", "blocked")

    @pytest.mark.asyncio
    async def test_ingest_text_calls_resolve_by_url_on_source_store(self) -> None:
        """AC3: when source_url is given, pipeline calls source_store.resolve_by_url() internally.

        The pipeline must drive source resolution — the caller must not need to pre-resolve.
        FAILS: IngestPipeline has no source_store / no resolve_by_url call.
        """
        mock_store = MagicMock()
        mock_store.resolve_by_url.return_value = MagicMock(id="resolved-uuid-abc")
        pipeline = self._make_pipeline_with_source_store(mock_store)

        await pipeline.ingest_text("text content", source_url="https://docs.example.com")

        mock_store.resolve_by_url.assert_called_once_with("https://docs.example.com")

    @pytest.mark.asyncio
    async def test_ingest_text_passes_resolved_source_id_to_insert_document(
        self,
    ) -> None:
        """AC3: insert_document must receive source_id equal to the resolved KnowledgeSource.id.

        The FK must originate from source_store.resolve_by_url().id — not from a
        caller-supplied source_id argument.
        FAILS: no source resolution happens in current pipeline.
        """
        expected_fk = "expected-source-fk-uuid-12345"
        mock_store = MagicMock()
        mock_store.resolve_by_url.return_value = MagicMock(id=expected_fk)
        pipeline = self._make_pipeline_with_source_store(mock_store)

        await pipeline.ingest_text("document text", source_url="https://docs.example.com")

        mock_docs = pipeline._docs  # type: ignore[attr-defined]
        call_kwargs = mock_docs.insert_document.call_args.kwargs
        actual_fk = call_kwargs.get("source_id")
        assert actual_fk == expected_fk, (
            f"insert_document must receive source_id={expected_fk!r} from resolved source, got {actual_fk!r}"
        )

    @pytest.mark.asyncio
    async def test_source_resolution_precedes_chunk_storage(self) -> None:
        """AC3 ordering: source is resolved and FK is set on insert_document BEFORE store_chunks.

        Verifies the FK is established before chunk data is written, so the FK constraint
        is always satisfied.
        FAILS: IngestPipeline has no source_store and cannot demonstrate this ordering.
        """
        call_order: list[str] = []

        mock_store = MagicMock()
        mock_store.resolve_by_url.side_effect = lambda _url: (
            call_order.append("resolve_by_url") or MagicMock(id="src-uuid")
        )

        mock_docs = MagicMock()
        mock_docs.insert_document.side_effect = lambda *_a, **_kw: call_order.append("insert_document")
        mock_docs.store_chunks.side_effect = lambda *_a, **_kw: call_order.append("store_chunks") or []
        mock_docs.store_embeddings.return_value = None
        mock_docs.store_extractions.return_value = (0, 0)

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [MagicMock(text="chunk")]

        # FAILS: source_store not accepted by constructor
        pipeline = IngestPipeline(
            document_store=mock_docs,
            entity_extractor=MagicMock(),
            text_chunker=mock_chunker,
            source_store=mock_store,
        )

        await pipeline.ingest_text("text", source_url="https://docs.example.com")

        assert "resolve_by_url" in call_order, "source_store.resolve_by_url must be called"
        assert "insert_document" in call_order, "insert_document must be called"
        assert "store_chunks" in call_order, "store_chunks must be called"

        resolve_idx = call_order.index("resolve_by_url")
        insert_idx = call_order.index("insert_document")
        chunks_idx = call_order.index("store_chunks")

        assert resolve_idx < insert_idx, "source resolution must happen before document insertion"
        assert insert_idx < chunks_idx, "document insertion (with source FK) must happen before chunk storage"

    @pytest.mark.asyncio
    async def test_ingest_text_registers_source_via_real_store_contract(self) -> None:
        """AC3 get-or-create: create() is called with the real store contract (returns None).

        The real KnowledgeSourceStore.create() returns None.  The pipeline must
        handle that by falling back to a second resolve_by_url() call.  This test
        wires both sides of the real runtime contract:
          - create.return_value = None  (matches production store)
          - resolve_by_url.side_effect = [None, just_created_source]  (first=miss, second=found)

        Asserts that create() was called with a KnowledgeSource whose name matches the URL.
        """
        just_created = MagicMock(id="real-contract-uuid")
        mock_store = MagicMock()
        mock_store.resolve_by_url.side_effect = [None, just_created]  # miss, then found
        mock_store.create.return_value = None  # real store contract

        pipeline = self._make_pipeline_with_source_store(mock_store)
        target_url = "https://docs.new.example.com"

        await pipeline.ingest_text("new content", source_url=target_url)

        mock_store.create.assert_called_once()
        call_args = mock_store.create.call_args
        created_obj = call_args[0][0] if call_args[0] else call_args.kwargs.get("source")
        # The KnowledgeSource passed to create() must carry the requested URL
        assert hasattr(created_obj, "name"), "create() must receive a KnowledgeSource object with a 'name' attribute"
        assert created_obj.name == target_url, f"KnowledgeSource.name must be {target_url!r}, got {created_obj.name!r}"
        # The real resolve_by_url() keys on source.config.get("url"), not on name.
        # If the ingest path wrote a wrong config URL the resolver would not find the
        # just-created source on the fallback call, so we must pin this key.
        assert created_obj.config.get("url") == target_url, (
            f"KnowledgeSource.config['url'] must be {target_url!r} "
            f"(the key used by resolve_by_url), got {created_obj.config.get('url')!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_text_uses_second_resolve_id_as_fk_after_create(self) -> None:
        """AC3 get-or-create: insert_document receives the id from the fallback re-resolve.

        After create() returns None, the pipeline calls resolve_by_url() a second time
        to get the newly-persisted source, then forwards source.id as the FK to
        insert_document.  This test proves the real runtime fallback branch end-to-end.
        """
        expected_fk = "real-contract-fallback-fk"
        just_created = MagicMock(id=expected_fk)
        mock_store = MagicMock()
        mock_store.resolve_by_url.side_effect = [None, just_created]  # miss, then found
        mock_store.create.return_value = None  # real store contract

        pipeline = self._make_pipeline_with_source_store(mock_store)

        await pipeline.ingest_text("content to ingest", source_url="https://docs.new.example.com")

        mock_docs = pipeline._docs  # type: ignore[attr-defined]
        call_kwargs = mock_docs.insert_document.call_args.kwargs
        actual_fk = call_kwargs.get("source_id")
        assert actual_fk == expected_fk, (
            f"insert_document must receive source_id={expected_fk!r} from "
            f"the fallback re-resolve after create() returned None, got {actual_fk!r}"
        )
