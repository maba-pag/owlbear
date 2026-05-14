"""Failing tests for task #1556: Repair knowledge ingestion source identity contract.

TDD RED phase — all 14 tests fail until the builder repairs the five confirmed bugs:
  1. ingest_text uses legacy insert_document branch → source_id dropped from document row
  2. Auto-created KnowledgeSource has wrong scope ("global") and enrich=False
  3. IngestPipeline.ingest (refresh path) never passes source_id to insert_document
  4. No transaction boundary → on failure, source/doc rows persist (AC-3)
  5. store_embeddings legacy path ignores scope → vector payloads always get scope="global"

Covers:
  AC-1: ingest_document creates source row with scope/enrich + document has source_id
  AC-2: refresh_source document has source_id + vector payloads carry source scope
  AC-3: failed ingest returns "error:" prefix + no partial persistence survives
  AC-4: get_next_batch returns source_name from linked source + excludes enrich-disabled
  AC-5: search result source.name/url from KnowledgeSource row + vector payload scope
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.schema import init_db
from owlbear_knowledge.source_store import KnowledgeSourceStore
from owlbear_mcp_knowledge.server import (
    AppContext,
    get_next_batch,
    ingest_document,
    refresh_source,
    search_knowledge,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _insert_source_direct(  # noqa: PLR0913
    conn: sqlite3.Connection,
    *,
    source_id: str,
    name: str,
    enrich: int,
    scope: str,
    url: str,
) -> None:
    """Insert a knowledge_sources row with a url_list config."""
    now = _now_iso()
    config = json.dumps({"urls": [url], "url": url})
    conn.execute(
        "INSERT INTO knowledge_sources"
        " (id, name, source_type, fetch_method, enrich, config, scope, enabled, priority,"
        "  created_at, updated_at)"
        " VALUES (?, ?, 'url_list', 'http', ?, ?, ?, 1, 0, ?, ?)",
        (source_id, name, enrich, config, scope, now, now),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """In-memory SQLite connection with schema initialised; thread-safe for asyncio.to_thread."""
    c = sqlite3.connect(":memory:", check_same_thread=False)
    init_db(c)
    return c


@pytest.fixture()
def mock_vs() -> MagicMock:
    """Mock vector store that captures store_embedding calls."""
    vs = MagicMock()
    vs.store_embedding = MagicMock()
    return vs


@pytest.fixture()
def mock_emb() -> MagicMock:
    """Mock embedder that returns stub embeddings without loading a model."""
    emb = MagicMock()
    emb.embed = MagicMock(return_value=[[0.1] * 10, [0.2] * 10])
    return emb


@pytest.fixture()
def store_components(
    conn: sqlite3.Connection, mock_vs: MagicMock, mock_emb: MagicMock
) -> dict:
    """Real storage components wired together with mock vector/embedder."""
    graph_store = GraphStore(conn)
    source_store = KnowledgeSourceStore(conn)
    doc_store = DocumentStore(conn, graph_store, mock_vs, mock_emb)
    chunker = TextChunker()
    extractor = EntityExtractor()  # no-op stub (no structured extractor)
    pipeline = IngestPipeline(
        doc_store,
        extractor,
        chunker,
        source_store=source_store,
    )
    return {
        "graph_store": graph_store,
        "source_store": source_store,
        "doc_store": doc_store,
        "pipeline": pipeline,
    }


@pytest.fixture()
def app_ctx(
    conn: sqlite3.Connection, store_components: dict
) -> AppContext:
    """AppContext with real pipeline + source store; refresh_orchestrator is non-None."""
    pc = store_components
    return AppContext(
        conn=conn,
        query_service=None,
        graph_store=pc["graph_store"],
        ingest_pipeline=pc["pipeline"],
        source_store=pc["source_store"],
        bookmark_pipeline=None,
        bookmark_store=None,
        refresh_orchestrator=MagicMock(),  # non-None so refresh_source passes the guard
    )


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Return a FastMCP-shaped Context mock backed by *app_ctx*."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_DirectIngestSourceIdentity  (AC-1)
# ---------------------------------------------------------------------------


class TestFromAC_DirectIngestSourceIdentity:
    """AC-1: ingest_document must create a source row with correct scope/enrich
    and the document row must have source_id pointing to that source."""

    @pytest.mark.asyncio
    async def test_document_row_has_source_id(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """Document row source_id must equal the auto-created KnowledgeSource.id.

        Fails because ingest_text passes a Document object to insert_document,
        which hits the legacy branch that ignores the source_id kwarg — the
        document row ends up with source_id=NULL.
        """
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="alpha beta",
            metadata={"title": "Doc A"},
            scope="team-a",
            source_url="https://example.test/a",
        )
        doc_row = conn.execute("SELECT source_id FROM documents").fetchone()
        assert doc_row is not None, "No document row was created"
        doc_source_id = doc_row[0]
        assert doc_source_id is not None, (
            "document.source_id must not be NULL — it must reference the "
            "auto-created knowledge_sources row"
        )
        source_row = conn.execute(
            "SELECT id FROM knowledge_sources WHERE id = ?", (doc_source_id,)
        ).fetchone()
        assert source_row is not None, (
            "document.source_id must reference an existing knowledge_sources row, "
            f"but no row found for id={doc_source_id!r}"
        )

    @pytest.mark.asyncio
    async def test_auto_created_source_scope_matches_ingest_scope(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """Auto-created KnowledgeSource.scope must equal the ingest scope ('team-a').

        Fails because KnowledgeSource is created without scope= argument,
        so it defaults to 'global'.
        """
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="alpha beta",
            metadata={"title": "Doc A"},
            scope="team-a",
            source_url="https://example.test/a",
        )
        row = conn.execute("SELECT scope FROM knowledge_sources").fetchone()
        assert row is not None, "No knowledge_sources row was created"
        assert row[0] == "team-a", (
            f"Auto-created source scope must be 'team-a', got {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_auto_created_source_enrich_is_enabled(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """Auto-created KnowledgeSource.enrich must be 1 (True).

        Fails because KnowledgeSource is created with enrich=False.
        """
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="alpha beta",
            metadata={"title": "Doc A"},
            scope="team-a",
            source_url="https://example.test/a",
        )
        row = conn.execute("SELECT enrich FROM knowledge_sources").fetchone()
        assert row is not None, "No knowledge_sources row was created"
        assert row[0] == 1, (
            f"Auto-created source enrich must be 1 (True), got {row[0]!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_RefreshIngestSourceIdentity  (AC-2)
# ---------------------------------------------------------------------------


class TestFromAC_RefreshIngestSourceIdentity:
    """AC-2: refresh_source must produce a document with source_id set and
    vector payloads that carry the source scope."""

    def _seed_url_list_source(self, conn: sqlite3.Connection) -> None:
        """Insert a URL-list source with id='src-a', scope='team-a'."""
        now = _now_iso()
        conn.execute(
            "INSERT INTO knowledge_sources"
            " (id, name, source_type, fetch_method, enrich, config, scope, enabled,"
            "  priority, created_at, updated_at)"
            " VALUES ('src-a', 'Source A', 'url_list', 'http', 1, ?, 'team-a', 1, 0, ?, ?)",
            (json.dumps({"urls": ["https://example.test/doc"]}), now, now),
        )
        conn.commit()

    @pytest.mark.asyncio
    async def test_refresh_document_row_has_source_id(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """After refresh, document row source_id must equal the refreshed source ID.

        Fails because IngestPipeline.ingest never receives/passes source_id to
        insert_document, leaving the document row with source_id=NULL.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="some refreshed content",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=fake_intake),
        ):
            await refresh_source(ctx, source_id="src-a")

        doc_row = conn.execute("SELECT source_id FROM documents").fetchone()
        assert doc_row is not None, "No document row created after refresh"
        assert doc_row[0] == "src-a", (
            f"Refreshed document source_id must be 'src-a', got {doc_row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_refresh_vector_payloads_carry_source_scope(
        self, conn: sqlite3.Connection, app_ctx: AppContext, mock_vs: MagicMock
    ) -> None:
        """store_embedding must be called with scope='team-a' after refresh.

        Fails because IngestPipeline.ingest calls store_embeddings without scope,
        so the legacy path calls store_embedding with the default scope='global'.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="content to embed",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=fake_intake),
        ):
            await refresh_source(ctx, source_id="src-a")

        calls = mock_vs.store_embedding.call_args_list
        assert calls, "store_embedding was never called during refresh"
        scopes_used = [
            c.kwargs.get("scope") or (c.args[3] if len(c.args) > 3 else None)
            for c in calls
        ]
        assert any(s == "team-a" for s in scopes_used), (
            "store_embedding must be called with scope='team-a' (source scope), "
            f"but got scopes: {scopes_used}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_FailedIngestAtomicCleanup  (AC-3)
# ---------------------------------------------------------------------------


class TestFromAC_FailedIngestAtomicCleanup:
    """AC-3: on persistence failure, ingest_document must return 'error:' prefix
    and leave no partial data (no source row, no document row)."""

    @pytest.mark.asyncio
    async def test_failure_response_has_error_prefix(
        self,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """ingest_document must return a string starting with 'error:' on failure.

        Fails because ingest_text catches all exceptions and returns
        IngestResult(status='failed'); the MCP tool then formats this as
        'Ingested: ... (status: failed)' instead of 'error: ...'.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch.object(
            store_components["doc_store"],
            "store_chunks",
            side_effect=sqlite3.OperationalError("forced persistence failure"),
        ):
            result = await ingest_document(
                ctx,
                text="boom",
                metadata={"title": "Broken"},
                scope="team-a",
                source_url="https://example.test/fail",
            )
        assert isinstance(result, str), "ingest_document must return a string"
        assert result.startswith("error:"), (
            f"On persistence failure, must return 'error:...', got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_failure_leaves_no_source_row(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """No knowledge_sources row must survive a failed ingest attempt.

        Fails because the source row is created BEFORE the failing store_chunks
        call, and there is no transaction rollback — the orphaned source row persists.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch.object(
            store_components["doc_store"],
            "store_chunks",
            side_effect=sqlite3.OperationalError("forced persistence failure"),
        ):
            await ingest_document(
                ctx,
                text="boom",
                metadata={"title": "Broken"},
                scope="team-a",
                source_url="https://example.test/fail",
            )
        count = conn.execute(
            "SELECT count(*) FROM knowledge_sources WHERE config LIKE ?",
            ("%example.test/fail%",),
        ).fetchone()[0]
        assert count == 0, (
            f"Failed ingest must leave no knowledge_sources row, found {count} row(s)"
        )

    @pytest.mark.asyncio
    async def test_failure_leaves_no_document_row(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """No documents row must survive a failed ingest attempt.

        Fails because insert_document (legacy branch → GraphStore) commits the
        document before store_chunks raises, and there is no rollback.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch.object(
            store_components["doc_store"],
            "store_chunks",
            side_effect=sqlite3.OperationalError("forced persistence failure"),
        ):
            await ingest_document(
                ctx,
                text="boom",
                metadata={"title": "Broken"},
                scope="team-a",
                source_url="https://example.test/fail",
            )
        count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert count == 0, (
            f"Failed ingest must leave no document rows, found {count} row(s)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_EnrichBatchSourceLinkage  (AC-4)
# ---------------------------------------------------------------------------


class TestFromAC_EnrichBatchSourceLinkage:
    """AC-4: get_next_batch must return source_name from the linked KnowledgeSource
    and must exclude chunks from enrich-disabled sources."""

    @pytest.mark.asyncio
    async def test_batch_source_name_populated_from_linked_source(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """Chunks from an enrich-enabled source must have source_name in the batch.

        Fails because ingest_document does not set source_id on the document row.
        With source_id=NULL, the LEFT JOIN to knowledge_sources returns NULL for
        ks.name — so source_name is NULL instead of the source's name.
        """
        _insert_source_direct(
            conn,
            source_id="src-enabled",
            name="Enabled Source",
            enrich=1,
            scope="team-a",
            url="https://enabled.test/",
        )
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="enabled document content",
            metadata={"title": "Enabled Doc"},
            scope="team-a",
            source_url="https://enabled.test/",
        )
        batch = await get_next_batch(ctx, limit=10)
        assert batch, "Batch must contain at least one chunk from the enabled source"
        item = batch[0]
        source_name = (
            item["source_name"] if isinstance(item, dict) else item.source_name
        )
        assert source_name == "Enabled Source", (
            f"source_name must be 'Enabled Source' (from linked KnowledgeSource), "
            f"got {source_name!r}"
        )

    @pytest.mark.asyncio
    async def test_batch_excludes_chunks_from_enrich_disabled_source(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """Chunks from an enrich-disabled source must not appear in get_next_batch.

        Fails because ingest_document does not set source_id on document rows.
        With source_id=NULL, COALESCE(ks.enrich, 1) = COALESCE(NULL, 1) = 1 for
        every document — the disabled source's chunks are incorrectly included.
        """
        _insert_source_direct(
            conn,
            source_id="src-enabled",
            name="Enabled Source",
            enrich=1,
            scope="team-a",
            url="https://enabled.test/",
        )
        _insert_source_direct(
            conn,
            source_id="src-disabled",
            name="Disabled Source",
            enrich=0,
            scope="team-a",
            url="https://disabled.test/",
        )
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="enabled document content",
            metadata={"title": "Enabled Doc"},
            scope="team-a",
            source_url="https://enabled.test/",
        )
        await ingest_document(
            ctx,
            text="disabled document content",
            metadata={"title": "Disabled Doc"},
            scope="team-a",
            source_url="https://disabled.test/",
        )
        batch = await get_next_batch(ctx, limit=10)
        source_names = [
            (item["source_name"] if isinstance(item, dict) else item.source_name)
            for item in batch
        ]
        assert "Disabled Source" not in source_names, (
            "Disabled source chunks must not appear in get_next_batch, "
            f"got source_names: {source_names}"
        )
        texts = [
            (item["text"] if isinstance(item, dict) else item.text)
            for item in batch
        ]
        disabled_texts = [t for t in texts if t and "disabled" in t.lower()]
        assert not disabled_texts, (
            "No chunk text from the disabled source must appear in batch, "
            f"got: {disabled_texts}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SearchResultProvenance  (AC-5)
# ---------------------------------------------------------------------------


class TestFromAC_SearchResultProvenance:
    """AC-5: direct ingest vector payloads must carry the source scope, and
    search_knowledge results must have source.name/url from the linked KnowledgeSource."""

    @pytest.mark.asyncio
    async def test_direct_ingest_vector_payload_carries_source_scope(
        self, app_ctx: AppContext, mock_vs: MagicMock
    ) -> None:
        """store_embedding must be called with scope='team-a' during direct ingest.

        Fails because ingest_text calls store_embeddings(chunk_ids, chunk_texts)
        without scope= — the legacy path calls store_embedding with the default
        scope='global', ignoring the ingest scope.
        """
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="scoped content for direct ingest",
            metadata={"title": "Scoped Doc"},
            scope="team-a",
            source_url="https://example.test/scoped",
        )
        calls = mock_vs.store_embedding.call_args_list
        assert calls, "store_embedding was never called during direct ingest"
        scopes_used = [
            c.kwargs.get("scope") or (c.args[3] if len(c.args) > 3 else None)
            for c in calls
        ]
        assert any(s == "team-a" for s in scopes_used), (
            "store_embedding must be called with scope='team-a' during direct ingest, "
            f"but got scopes: {scopes_used}"
        )

    @pytest.mark.asyncio
    async def test_search_result_source_name_from_knowledge_source_row(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """search_knowledge result source.name must come from the linked KnowledgeSource.

        Fails because ingest_document does not set source_id on the document row.
        With source_id=NULL, the lookup for the linked source returns None —
        _serialize_source(None) returns {"name": "", "url": ""}.
        """
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="alpha beta",
            metadata={"title": "Doc A"},
            scope="team-a",
            source_url="https://example.test/a",
        )
        # Derive source object from the document's source_id in the DB.
        # With the bug, source_id=NULL → lookup returns None → name serialises to "".
        doc_row = conn.execute("SELECT source_id FROM documents").fetchone()
        doc_source_id = doc_row[0] if doc_row else None
        source_obj = (
            store_components["source_store"].get(doc_source_id)
            if doc_source_id
            else None
        )
        mock_result = MagicMock()
        mock_result.source = source_obj  # None when source_id is NULL (the bug)
        mock_result.title = "Doc A"
        mock_result.score = 0.9
        mock_result.snippet = "alpha beta"
        mock_result.entity_type = None
        mock_result.retrieval_path = "vector"
        mock_result.entities = []
        mock_result.related_sources = []

        mock_qs = MagicMock()
        mock_qs.query = AsyncMock(return_value=[mock_result])

        search_app_ctx = MagicMock()
        search_app_ctx.query_service = mock_qs
        search_ctx = MagicMock()
        search_ctx.request_context.lifespan_context = search_app_ctx

        results = await search_knowledge(search_ctx, query="alpha")
        assert results, "search_knowledge must return results"
        source = results[0]["source"]
        assert source["name"] == "https://example.test/a", (
            "source.name must equal the auto-created KnowledgeSource.name "
            f"('https://example.test/a'), got {source['name']!r}"
        )

    @pytest.mark.asyncio
    async def test_search_result_source_url_from_knowledge_source_config(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """search_knowledge result source.url must come from KnowledgeSource config.url.

        Fails because ingest_document does not set source_id on the document row.
        With source_id=NULL, the linked source is not found — source.url is "".
        """
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="alpha beta",
            metadata={"title": "Doc A"},
            scope="team-a",
            source_url="https://example.test/a",
        )
        doc_row = conn.execute("SELECT source_id FROM documents").fetchone()
        doc_source_id = doc_row[0] if doc_row else None
        source_obj = (
            store_components["source_store"].get(doc_source_id)
            if doc_source_id
            else None
        )
        mock_result = MagicMock()
        mock_result.source = source_obj
        mock_result.title = "Doc A"
        mock_result.score = 0.9
        mock_result.snippet = "alpha beta"
        mock_result.entity_type = None
        mock_result.retrieval_path = "vector"
        mock_result.entities = []
        mock_result.related_sources = []

        mock_qs = MagicMock()
        mock_qs.query = AsyncMock(return_value=[mock_result])

        search_app_ctx = MagicMock()
        search_app_ctx.query_service = mock_qs
        search_ctx = MagicMock()
        search_ctx.request_context.lifespan_context = search_app_ctx

        results = await search_knowledge(search_ctx, query="alpha")
        assert results, "search_knowledge must return results"
        source = results[0]["source"]
        assert source["url"] == "https://example.test/a", (
            "source.url must come from KnowledgeSource config.url "
            f"('https://example.test/a'), got {source['url']!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_RefreshEntityEdgeProvenance  (AC-2 additions — retry cycle 2)
# ---------------------------------------------------------------------------


class TestFromAC_RefreshEntityEdgeProvenance:
    """AC-2 proof: refresh entity/edge provenance and return-value contract.

    Reviewer gap (cycle 2): both existing refresh tests discard the refresh_source
    return value and wire a no-op EntityExtractor, so entity/edge persistence is
    never exercised and the return contract (source_id, refreshed=1) is unproven.

    These tests wire a mock extractor that returns one entity and one edge,
    then assert the provenance stamping contract (scope, document_id, chunk_id)
    and the refresh_source return dict.
    """

    def _seed_url_list_source(self, conn: sqlite3.Connection) -> None:
        now = _now_iso()
        conn.execute(
            "INSERT INTO knowledge_sources"
            " (id, name, source_type, fetch_method, enrich, config, scope, enabled,"
            "  priority, created_at, updated_at)"
            " VALUES ('src-a', 'Source A', 'url_list', 'http', 1, ?, 'team-a', 1, 0, ?, ?)",
            (json.dumps({"urls": ["https://example.test/doc"]}), now, now),
        )
        conn.commit()

    def _make_extraction(self) -> ExtractionResult:
        """Return an ExtractionResult with two entities and one edge."""
        e1 = Entity(
            name="concept-alpha",
            entity_type=EntityType.CONCEPT,
            description="alpha concept",
        )
        e2 = Entity(
            name="concept-beta",
            entity_type=EntityType.CONCEPT,
            description="beta concept",
        )
        edge = Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)
        return ExtractionResult(entities=[e1, e2], edges=[edge])

    @pytest.mark.asyncio
    async def test_refresh_return_value_has_source_id_and_refreshed_count(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """refresh_source must return dict with source_id='src-a' and refreshed=1.

        Proof gap: both existing refresh tests discard the return value without
        asserting the source_id and refreshed fields required by AC-2.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="some refreshed content",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_knowledge.intake.read_url", new=AsyncMock(return_value=fake_intake)):
            result = await refresh_source(ctx, source_id="src-a")
        assert isinstance(result, dict), (
            f"refresh_source must return a dict on success, got {result!r}"
        )
        assert result["source_id"] == "src-a", (
            f"result['source_id'] must be 'src-a', got {result.get('source_id')!r}"
        )
        assert result["refreshed"] == 1, (
            f"result['refreshed'] must be 1 (one URL ingested), got {result.get('refreshed')!r}"
        )

    @pytest.mark.asyncio
    async def test_refresh_persisted_entity_has_source_scope_and_document_id(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
    ) -> None:
        """Entities persisted after refresh must have scope='team-a' and document_id
        matching the refresh document row.

        Proof gap: no-op extractor means no entities are ever persisted, so the
        entity provenance stamping code path (scope, document_id) was never exercised.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="content with extractable entities",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        extraction = self._make_extraction()
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch.object(EntityExtractor, "extract", new=AsyncMock(return_value=extraction)),
            patch("owlbear_knowledge.intake.read_url", new=AsyncMock(return_value=fake_intake)),
        ):
            await refresh_source(ctx, source_id="src-a")
        doc_row = conn.execute("SELECT id FROM documents").fetchone()
        assert doc_row is not None, "No document row created by refresh"
        doc_id = doc_row[0]
        entity_rows = conn.execute(
            "SELECT scope, document_id FROM entities WHERE document_id = ?", (doc_id,)
        ).fetchall()
        assert entity_rows, (
            f"No entities with document_id={doc_id!r} were persisted after refresh"
        )
        scopes = [r[0] for r in entity_rows]
        assert all(s == "team-a" for s in scopes), (
            "All persisted entities must have scope='team-a' (from source scope), "
            f"but got scopes: {scopes}"
        )

    @pytest.mark.asyncio
    async def test_refresh_persisted_entity_has_chunk_id_provenance(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
    ) -> None:
        """Entities persisted after refresh must have chunk_id referencing a chunk
        created during that refresh.

        Proof gap: no-op extractor means no entities are persisted, so chunk_id
        provenance stamping was never proven.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="content with extractable entities",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        extraction = self._make_extraction()
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch.object(EntityExtractor, "extract", new=AsyncMock(return_value=extraction)),
            patch("owlbear_knowledge.intake.read_url", new=AsyncMock(return_value=fake_intake)),
        ):
            await refresh_source(ctx, source_id="src-a")
        chunk_ids = {r[0] for r in conn.execute("SELECT id FROM chunks").fetchall()}
        assert chunk_ids, "No chunks were created by refresh"
        entity_chunk_ids = {
            r[0]
            for r in conn.execute("SELECT chunk_id FROM entities").fetchall()
            if r[0] is not None
        }
        assert entity_chunk_ids, (
            "Entities must have chunk_id set after refresh, but all chunk_ids are NULL"
        )
        assert entity_chunk_ids.issubset(chunk_ids), (
            "Entity chunk_ids must reference actual chunks created during refresh, "
            f"got entity chunk_ids {entity_chunk_ids!r} not in chunks {chunk_ids!r}"
        )

    @pytest.mark.asyncio
    async def test_refresh_persisted_edge_has_document_provenance_in_metadata(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
    ) -> None:
        """Edges persisted after refresh must have document_id, scope, and chunk_id
        provenance fields inside their metadata dict.

        Proof gap: no-op extractor means no edges are persisted, so edge provenance
        stamping (metadata.scope, metadata.document_id, metadata.chunk_id) was
        never exercised.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="content with extractable entities",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        extraction = self._make_extraction()
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch.object(EntityExtractor, "extract", new=AsyncMock(return_value=extraction)),
            patch("owlbear_knowledge.intake.read_url", new=AsyncMock(return_value=fake_intake)),
        ):
            await refresh_source(ctx, source_id="src-a")
        doc_row = conn.execute("SELECT id FROM documents").fetchone()
        assert doc_row is not None, "No document row created by refresh"
        doc_id = doc_row[0]
        edge_rows = conn.execute(
            "SELECT document_id, metadata FROM edges WHERE document_id = ?", (doc_id,)
        ).fetchall()
        assert edge_rows, (
            f"No edges with document_id={doc_id!r} were persisted after refresh"
        )
        for _row_doc_id, meta_json in edge_rows:
            meta = json.loads(meta_json) if meta_json else {}
            assert "document_id" in meta, (
                "Edge metadata must contain 'document_id' provenance field, "
                f"but got metadata: {meta!r}"
            )
            assert meta["document_id"] == doc_id, (
                f"Edge metadata['document_id'] must be {doc_id!r}, "
                f"got {meta.get('document_id')!r}"
            )
            assert "scope" in meta, (
                "Edge metadata must contain 'scope' provenance field, "
                f"but got metadata keys: {list(meta)!r}"
            )
            assert meta["scope"] == "team-a", (
                f"Edge metadata['scope'] must be 'team-a', got {meta.get('scope')!r}"
            )


# ---------------------------------------------------------------------------
# TestFromAC_LateFailureAtomicCleanup  (AC-3 additions — retry cycle 2)
# ---------------------------------------------------------------------------


class TestFromAC_LateFailureAtomicCleanup:
    """AC-3 proof: failed direct ingest cleans up chunks and vector payloads even
    when failure occurs AFTER store_embeddings has already written data.

    Reviewer gap (cycle 2): existing AC-3 tests inject failure at store_chunks
    (before embeddings), so chunks and vector payloads never exist at failure
    time — the cleanup code for those is never exercised.

    These tests inject failure at store_extractions (after store_chunks and
    store_embeddings succeed) and assert that the cleanup removes all partial
    persistence from chunks, vector payloads, entities, and edges.
    """

    @pytest.mark.asyncio
    async def test_late_failure_after_embeddings_leaves_no_chunks(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """After a failure at store_extractions, no chunks must remain in the DB.

        Injection point: store_extractions — chunks have been written by
        store_chunks and embeddings by store_embeddings before failure.
        delete_document_data must remove the orphaned chunk rows.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch.object(
            store_components["doc_store"],
            "store_extractions",
            side_effect=RuntimeError("forced late extraction failure"),
        ):
            result = await ingest_document(
                ctx,
                text="content for late-failure cleanup test",
                metadata={"title": "LateFailDoc"},
                scope="team-a",
                source_url="https://example.test/late-fail",
            )
        assert isinstance(result, str), f"ingest_document must return a string, got {result!r}"
        assert result.startswith("error:"), (
            f"Must return 'error:...' on late-stage failure, got: {result!r}"
        )
        count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        assert count == 0, (
            "Failed ingest must leave no chunk rows after late-stage cleanup "
            f"(failure at store_extractions), found {count} row(s)"
        )

    @pytest.mark.asyncio
    async def test_late_failure_after_embeddings_triggers_vector_cleanup(
        self,
        app_ctx: AppContext,
        store_components: dict,
        mock_vs: MagicMock,
    ) -> None:
        """After a failure at store_extractions, delete_chunk_embeddings must be
        called to clean up vector payloads written by store_embeddings.

        Injection point: store_extractions — vector payloads were submitted to
        mock_vs before the failure. delete_chunk_embeddings must call
        mock_vs.delete_embedding for each chunk that was embedded.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch.object(
            store_components["doc_store"],
            "store_extractions",
            side_effect=RuntimeError("forced late extraction failure"),
        ):
            await ingest_document(
                ctx,
                text="content for late-failure cleanup test",
                metadata={"title": "LateFailDoc"},
                scope="team-a",
                source_url="https://example.test/late-fail",
            )
        delete_calls = mock_vs.delete_embedding.call_args_list
        assert delete_calls, (
            "delete_embedding must be called at least once to clean up vector "
            "payloads that were written before the late-stage failure at "
            "store_extractions"
        )

    @pytest.mark.asyncio
    async def test_late_failure_after_embeddings_leaves_no_entities(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """After a failure at store_extractions, no entity rows must remain.

        Injection point: store_extractions — failure occurs before any entity
        writes, so entities never exist; delete_document_data must also cover
        any that could have been written in a partial-write scenario.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch.object(
            store_components["doc_store"],
            "store_extractions",
            side_effect=RuntimeError("forced late extraction failure"),
        ):
            await ingest_document(
                ctx,
                text="content for late-failure cleanup test",
                metadata={"title": "LateFailDoc"},
                scope="team-a",
                source_url="https://example.test/late-fail",
            )
        count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
        assert count == 0, (
            f"Failed ingest must leave no entity rows, found {count} row(s)"
        )

    @pytest.mark.asyncio
    async def test_late_failure_after_embeddings_leaves_no_edges(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """After a failure at store_extractions, no edge rows must remain.

        Injection point: store_extractions — failure occurs before any edge
        writes, so edges never exist; delete_document_data must cascade-delete
        any that could survive a partial-write scenario.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch.object(
            store_components["doc_store"],
            "store_extractions",
            side_effect=RuntimeError("forced late extraction failure"),
        ):
            await ingest_document(
                ctx,
                text="content for late-failure cleanup test",
                metadata={"title": "LateFailDoc"},
                scope="team-a",
                source_url="https://example.test/late-fail",
            )
        count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert count == 0, (
            f"Failed ingest must leave no edge rows, found {count} row(s)"
        )
