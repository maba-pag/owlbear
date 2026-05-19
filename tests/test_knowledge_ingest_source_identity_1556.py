"""Failing tests for task #1556: Repair knowledge ingestion source identity contract.

TDD RED phase — all 14 tests fail until the builder repairs the five confirmed bugs:
  1. ingest_text uses legacy insert_document branch → source_id dropped from document row
  2. Auto-created KnowledgeSource has wrong scope ("global") and enrich=False
  3. IngestPipeline.ingest (refresh path) never passes source_id to insert_document
  4. No transaction boundary → on failure, source/doc rows persist (AC-3)
  5. store_embeddings legacy path ignores scope → vector payloads always get scope="global"

Retry cycle 5 adds:
  AC-6: delete_document_data must delete vector embeddings for chunk IDs, not only relational rows
  AC-7: ingest_text must succeed with a default SQLite connection (no check_same_thread=False)

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

from owlbear_knowledge.chunker import Chunk, TextChunker
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.ingest import IngestPipeline
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.protocol import HybridEmbedding
from owlbear_knowledge.query_service import KnowledgeQueryService
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
def store_components(conn: sqlite3.Connection, mock_vs: MagicMock, mock_emb: MagicMock) -> dict:
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
def app_ctx(conn: sqlite3.Connection, store_components: dict) -> AppContext:
    """AppContext with real pipeline + source store; refresh_orchestrator is non-None."""
    pc = store_components
    return AppContext(
        conn=conn,
        query_service=None,
        graph_store=pc["graph_store"],
        ingest_pipeline=pc["pipeline"],
        source_store=pc["source_store"],
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
    async def test_document_row_has_source_id(self, conn: sqlite3.Connection, app_ctx: AppContext) -> None:
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
            "document.source_id must not be NULL — it must reference the auto-created knowledge_sources row"
        )
        source_row = conn.execute("SELECT id FROM knowledge_sources WHERE id = ?", (doc_source_id,)).fetchone()
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
        assert row[0] == "team-a", f"Auto-created source scope must be 'team-a', got {row[0]!r}"

    @pytest.mark.asyncio
    async def test_auto_created_source_enrich_is_enabled(self, conn: sqlite3.Connection, app_ctx: AppContext) -> None:
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
        assert row[0] == 1, f"Auto-created source enrich must be 1 (True), got {row[0]!r}"

    @pytest.mark.asyncio
    async def test_cross_scope_same_url_does_not_link_to_foreign_scope_source(
        self, conn: sqlite3.Connection, app_ctx: AppContext
    ) -> None:
        """Direct ingest into team-a must NOT bind to an existing team-b source
        that shares the same URL — a new team-a source must be created instead.

        Falsifies the scope-qualified URL resolution contract (AC-1): a regression
        back to URL-only resolution would link the document to the team-b row and
        leave only one knowledge_sources row, causing both assertions to fail.
        """
        # Seed a pre-existing source with the same URL but a different scope.
        _insert_source_direct(
            conn,
            source_id="src-team-b",
            name="Team B Source",
            enrich=1,
            scope="team-b",
            url="https://example.test/a",
        )
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="alpha beta",
            metadata={"title": "Doc A"},
            scope="team-a",
            source_url="https://example.test/a",
        )
        # There must now be two distinct sources — one per scope.
        source_rows = conn.execute("SELECT id, scope FROM knowledge_sources ORDER BY scope").fetchall()
        assert len(source_rows) == 2, (  # noqa: PLR2004
            f"Expected 2 knowledge_sources rows (team-a + team-b), found {len(source_rows)}: {source_rows}"
        )
        scopes = {r[1] for r in source_rows}
        assert scopes == {"team-a", "team-b"}, f"Expected scopes {{'team-a', 'team-b'}}, got {scopes}"
        # The document must link to the team-a source, not the team-b source.
        doc_source_id = conn.execute("SELECT source_id FROM documents").fetchone()[0]
        team_a_source_id = next(r[0] for r in source_rows if r[1] == "team-a")
        assert doc_source_id == team_a_source_id, (
            f"document.source_id must reference the team-a source ({team_a_source_id!r}), "
            f"but got {doc_source_id!r} (team-b id is 'src-team-b')"
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
    async def test_refresh_document_row_has_source_id(self, conn: sqlite3.Connection, app_ctx: AppContext) -> None:
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
        assert doc_row[0] == "src-a", f"Refreshed document source_id must be 'src-a', got {doc_row[0]!r}"

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
        scopes_used = [c.kwargs.get("scope") or (c.args[3] if len(c.args) > 3 else None) for c in calls]
        assert any(s == "team-a" for s in scopes_used), (
            f"store_embedding must be called with scope='team-a' (source scope), but got scopes: {scopes_used}"
        )

    @pytest.mark.asyncio
    async def test_refresh_chunks_carry_source_scope(self, conn: sqlite3.Connection, app_ctx: AppContext) -> None:
        """Chunks persisted after refresh must carry scope='team-a' (the source scope).

        Proof gap (cycle 7 review): existing refresh tests assert vector scope and
        entity scope but never query the chunks table's scope column. A regression
        that drops the scope parameter from store_chunks() would still pass all
        prior tests.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="chunk scope verification content",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=fake_intake),
        ):
            await refresh_source(ctx, source_id="src-a")

        doc_row = conn.execute("SELECT id FROM documents").fetchone()
        assert doc_row is not None, "No document row created after refresh"
        doc_id = doc_row[0]

        chunk_scopes = [
            r[0] for r in conn.execute("SELECT scope FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()
        ]
        assert chunk_scopes, (
            f"No chunks found for document {doc_id!r} after refresh — refresh must persist at least one chunk"
        )
        assert all(s == "team-a" for s in chunk_scopes), (
            "All chunks persisted by refresh must have scope='team-a' (source scope), "
            f"but got chunk scopes: {chunk_scopes}"
        )

    @pytest.mark.asyncio
    async def test_replace_on_change_preserves_source_id_and_scope(
        self,
        conn: sqlite3.Connection,
        store_components: dict,
        mock_vs: MagicMock,
    ) -> None:
        """Replace-on-change ingest (second call with different content) must preserve
        source_id='src-a' on the replacement document and stamp chunks + vector
        payloads with scope='team-a'.

        Proof gap (cycle 11 review, Finding 1): all existing refresh tests exercise
        first-time ingest only — check_content_changed returns (False, None) on the
        first call because no content hash exists yet. The replace-on-change branch
        (existing_id is not None → delete_document_data(existing_id) → insert
        replacement document) is never exercised on the success path. A regression
        breaking source_id or scope threading in that branch would still pass all
        prior tests.
        """
        self._seed_url_list_source(conn)
        pipeline: IngestPipeline = store_components["pipeline"]

        intake_v1 = IntakeResult(
            content="Version 1 content — original document for replace-on-change test",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        result_v1 = await pipeline.ingest(intake_v1, scope="team-a", source_id="src-a")
        assert result_v1.status == "ok", (
            f"First ingest must succeed for replace-on-change to fire on second call, got status={result_v1.status!r}"
        )

        # Reset so only v2 store_embedding calls are observed.
        mock_vs.store_embedding.reset_mock()

        intake_v2 = IntakeResult(
            content="Version 2 content — different to trigger replace-on-change branch",
            source="https://example.test/doc",  # same URL → check_content_changed returns (True, v1_id)
            metadata={"source_type": "url_list"},
        )
        result_v2 = await pipeline.ingest(intake_v2, scope="team-a", source_id="src-a")
        assert result_v2.status == "ok", f"Replace-on-change ingest must succeed, got status={result_v2.status!r}"

        # (a) Exactly 1 document row: old document was replaced, not doubled.
        doc_count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert doc_count == 1, (  # noqa: PLR2004
            f"Replace-on-change must leave exactly 1 document row (old replaced), found {doc_count} row(s)"
        )

        # (b) Replacement document source_id preserved as 'src-a'.
        doc_source_id = conn.execute("SELECT source_id FROM documents").fetchone()[0]
        assert doc_source_id == "src-a", (
            "Replacement document source_id must be 'src-a' (identity preserved "
            f"through replace-on-change branch), got {doc_source_id!r}"
        )

        # (c) Replacement chunks carry scope='team-a'.
        new_doc_id = conn.execute("SELECT id FROM documents").fetchone()[0]
        chunk_scopes = [
            r[0] for r in conn.execute("SELECT scope FROM chunks WHERE document_id = ?", (new_doc_id,)).fetchall()
        ]
        assert chunk_scopes, "Replace-on-change must persist at least one chunk for the replacement document"
        assert all(s == "team-a" for s in chunk_scopes), (
            f"All replacement chunks must have scope='team-a', but got chunk scopes: {chunk_scopes}"
        )

        # (d) Replacement vector payloads carry scope='team-a'.
        embed_calls = mock_vs.store_embedding.call_args_list
        assert embed_calls, (
            "store_embedding must be called for replacement document chunks after replace-on-change succeeds"
        )
        scopes_used = [c.kwargs.get("scope") or (c.args[3] if len(c.args) > 3 else None) for c in embed_calls]
        assert all(s == "team-a" for s in scopes_used), (
            "store_embedding must be called with scope='team-a' for all replacement "
            f"chunks, but got scopes: {scopes_used}"
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
        assert result.startswith("error:"), f"On persistence failure, must return 'error:...', got: {result!r}"

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
        assert count == 0, f"Failed ingest must leave no knowledge_sources row, found {count} row(s)"

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
        assert count == 0, f"Failed ingest must leave no document rows, found {count} row(s)"


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
        source_name = item["source_name"] if isinstance(item, dict) else item.source_name
        assert source_name == "Enabled Source", (
            f"source_name must be 'Enabled Source' (from linked KnowledgeSource), got {source_name!r}"
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
        source_names = [(item["source_name"] if isinstance(item, dict) else item.source_name) for item in batch]
        assert "Disabled Source" not in source_names, (
            f"Disabled source chunks must not appear in get_next_batch, got source_names: {source_names}"
        )
        texts = [(item["text"] if isinstance(item, dict) else item.text) for item in batch]
        disabled_texts = [t for t in texts if t and "disabled" in t.lower()]
        assert not disabled_texts, f"No chunk text from the disabled source must appear in batch, got: {disabled_texts}"


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
        scopes_used = [c.kwargs.get("scope") or (c.args[3] if len(c.args) > 3 else None) for c in calls]
        assert any(s == "team-a" for s in scopes_used), (
            f"store_embedding must be called with scope='team-a' during direct ingest, but got scopes: {scopes_used}"
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
        source_obj = store_components["source_store"].get(doc_source_id) if doc_source_id else None
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
        source_obj = store_components["source_store"].get(doc_source_id) if doc_source_id else None
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
            f"source.url must come from KnowledgeSource config.url ('https://example.test/a'), got {source['url']!r}"
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
        assert isinstance(result, dict), f"refresh_source must return a dict on success, got {result!r}"
        assert result["source_id"] == "src-a", f"result['source_id'] must be 'src-a', got {result.get('source_id')!r}"
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
        assert entity_rows, f"No entities with document_id={doc_id!r} were persisted after refresh"
        scopes = [r[0] for r in entity_rows]
        assert all(s == "team-a" for s in scopes), (
            f"All persisted entities must have scope='team-a' (from source scope), but got scopes: {scopes}"
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
        entity_chunk_ids = {r[0] for r in conn.execute("SELECT chunk_id FROM entities").fetchall() if r[0] is not None}
        assert entity_chunk_ids, "Entities must have chunk_id set after refresh, but all chunk_ids are NULL"
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
        edge_rows = conn.execute("SELECT document_id, metadata FROM edges WHERE document_id = ?", (doc_id,)).fetchall()
        assert edge_rows, f"No edges with document_id={doc_id!r} were persisted after refresh"
        chunk_ids = {r[0] for r in conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()}
        for _row_doc_id, meta_json in edge_rows:
            meta = json.loads(meta_json) if meta_json else {}
            assert "document_id" in meta, (
                f"Edge metadata must contain 'document_id' provenance field, but got metadata: {meta!r}"
            )
            assert meta["document_id"] == doc_id, (
                f"Edge metadata['document_id'] must be {doc_id!r}, got {meta.get('document_id')!r}"
            )
            assert "scope" in meta, (
                f"Edge metadata must contain 'scope' provenance field, but got metadata keys: {list(meta)!r}"
            )
            assert meta["scope"] == "team-a", f"Edge metadata['scope'] must be 'team-a', got {meta.get('scope')!r}"
            assert "chunk_id" in meta, (
                f"Edge metadata must contain 'chunk_id' provenance field, but got metadata keys: {list(meta)!r}"
            )
            assert isinstance(meta["chunk_id"], str), (
                f"Edge metadata['chunk_id'] must be a string, got {type(meta['chunk_id'])!r}"
            )
            assert meta["chunk_id"], f"Edge metadata['chunk_id'] must be non-empty, got {meta.get('chunk_id')!r}"
            assert meta["chunk_id"] in chunk_ids, (
                "Edge metadata['chunk_id'] must reference an actual chunk created "
                f"during this refresh, got {meta.get('chunk_id')!r} not in {chunk_ids!r}"
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
        assert result.startswith("error:"), f"Must return 'error:...' on late-stage failure, got: {result!r}"
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
        assert count == 0, f"Failed ingest must leave no entity rows, found {count} row(s)"

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
        assert count == 0, f"Failed ingest must leave no edge rows, found {count} row(s)"

    @pytest.mark.asyncio
    async def test_partial_extraction_write_leaves_no_entities_or_edges(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """Entity rows committed before edge-write failure are cleaned up by failed-ingest path.

        Reviewer gap (cycle 8): existing tests patch store_extractions itself to
        raise before any graph writes, so insert_entity is never called and the
        entity/edge cleanup assertions are vacuously true.

        This test wires a stub extractor returning 1 entity + 1 edge, patches
        GraphStore.insert_edge to raise RuntimeError on its first call (allowing
        all insert_entity calls to commit first), then asserts that:
        - insert_entity was called ≥1 time (partial-write state reached, not vacuous)
        - entities=0 and edges=0 after cleanup (delete_document_data removed them)
        - existing contract: error: prefix, no chunks, no document, no source row
        """
        entity = Entity(
            name="partial-write-entity",
            entity_type=EntityType.CONCEPT,
            description="entity committed before edge insertion fails",
        )
        edge = Edge(
            source_id=entity.id,
            target_id=entity.id,
            relation=RelationType.RELATED_TO,
        )
        extraction = ExtractionResult(entities=[entity], edges=[edge])

        entity_call_count = 0
        real_insert_entity = store_components["graph_store"].insert_entity

        def counting_insert_entity(ent: Entity) -> None:
            nonlocal entity_call_count
            entity_call_count += 1
            real_insert_entity(ent)

        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch.object(
                store_components["pipeline"]._extractor,
                "extract",
                new=AsyncMock(return_value=extraction),
            ),
            patch.object(
                store_components["graph_store"],
                "insert_entity",
                side_effect=counting_insert_entity,
            ),
            patch.object(
                store_components["graph_store"],
                "insert_edge",
                side_effect=RuntimeError("forced edge-write failure for partial-write test"),
            ),
        ):
            result = await ingest_document(
                ctx,
                text="content for partial-write cleanup test",
                metadata={"title": "PartialWriteDoc"},
                scope="team-a",
                source_url="https://example.test/partial-write",
            )

        assert isinstance(result, str), f"ingest_document must return a string, got {result!r}"
        assert result.startswith("error:"), f"Must return 'error:...' when extraction partially fails, got: {result!r}"
        assert entity_call_count >= 1, (
            "insert_entity must be called ≥1 time before edge-write failure to prove "
            f"the partial-write state was reached (got {entity_call_count} calls); "
            "if this is 0, the extractor stub or patch did not wire correctly"
        )
        entity_count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
        assert entity_count == 0, (
            "Failed ingest must leave no entity rows after partial extraction-write "
            f"cleanup via delete_document_data, found {entity_count} row(s)"
        )
        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            "Failed ingest must leave no edge rows after partial extraction-write "
            f"cleanup via delete_document_data, found {edge_count} row(s)"
        )
        chunk_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        assert chunk_count == 0, (
            f"Failed ingest must leave no chunk rows after partial extraction-write cleanup, found {chunk_count} row(s)"
        )
        doc_count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert doc_count == 0, (
            "Failed ingest must leave no document rows after partial extraction-write "
            f"cleanup, found {doc_count} row(s)"
        )
        source_count = conn.execute("SELECT count(*) FROM knowledge_sources").fetchone()[0]
        assert source_count == 0, (
            "Failed ingest must leave no source rows after partial extraction-write "
            f"cleanup, found {source_count} row(s)"
        )

    @pytest.mark.asyncio
    async def test_committed_edge_row_cleaned_up_after_second_insert_edge_failure(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
    ) -> None:
        """An edge row committed by the first insert_edge call is cleaned up when
        a second insert_edge call raises — proving edge cleanup is non-vacuous.

        Reviewer gap (cycle 9): test_partial_extraction_write_leaves_no_entities_or_edges
        patches insert_edge to raise on its FIRST call, so no edge is ever committed
        — edges=0 is vacuously true regardless of cleanup correctness.

        This test:
        1. Wires a stub extractor returning 1 entity + 2 edges.
        2. Wraps insert_edge to call the REAL insert_edge on the FIRST call
           (commits edge1 to SQLite), then raise RuntimeError on the SECOND call.
        3. Asserts edge_call_count >= 2 (proves the committed-edge state was reached,
           not vacuous — first call was a real commit, second raised).
        4. Asserts edges=0 after cleanup (delete_document_data removed the committed edge).
        5. Continues asserting the existing contract: error: prefix, entities=0,
           chunks=0, documents=0, sources=0.
        """
        entity1 = Entity(
            name="committed-edge-entity-1",
            entity_type=EntityType.CONCEPT,
            description="first entity for committed-edge cleanup test",
        )
        entity2 = Entity(
            name="committed-edge-entity-2",
            entity_type=EntityType.CONCEPT,
            description="second entity for committed-edge cleanup test",
        )
        # Two edges so the second insert_edge call is reachable after the first commits.
        edge1 = Edge(
            source_id=entity1.id,
            target_id=entity2.id,
            relation=RelationType.RELATED_TO,
        )
        edge2 = Edge(
            source_id=entity2.id,
            target_id=entity1.id,
            relation=RelationType.RELATED_TO,
        )
        extraction = ExtractionResult(entities=[entity1, entity2], edges=[edge1, edge2])

        edge_call_count = 0
        real_insert_edge = store_components["graph_store"].insert_edge

        def wrapping_insert_edge(edge: Edge, *, document_id: str | None = None) -> None:
            nonlocal edge_call_count
            edge_call_count += 1
            if edge_call_count == 1:
                # First call: real insert so edge1 is committed to SQLite.
                real_insert_edge(edge, document_id=document_id)
            else:
                # Second call: raise to simulate late partial-write failure.
                _msg = "forced second edge-write failure for committed-edge cleanup test"
                raise RuntimeError(_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch.object(
                store_components["pipeline"]._extractor,
                "extract",
                new=AsyncMock(return_value=extraction),
            ),
            patch.object(
                store_components["graph_store"],
                "insert_edge",
                side_effect=wrapping_insert_edge,
            ),
        ):
            result = await ingest_document(
                ctx,
                text="content for committed-edge cleanup test",
                metadata={"title": "CommittedEdgeDoc"},
                scope="team-a",
                source_url="https://example.test/committed-edge",
            )

        assert isinstance(result, str), f"ingest_document must return a string, got {result!r}"
        assert result.startswith("error:"), f"Must return 'error:...' when second edge insert fails, got: {result!r}"
        assert edge_call_count >= 2, (  # noqa: PLR2004
            "insert_edge must be called ≥2 times (first call commits edge1, second raises) "
            f"to prove the committed-edge state was reached (got {edge_call_count} calls); "
            "if this is 1, only one edge was produced — use 2 edges in the extraction stub"
        )
        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            "Failed ingest must leave no edge rows — delete_document_data must clean up "
            f"the committed edge row, found {edge_count} row(s)"
        )
        entity_count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
        assert entity_count == 0, f"Failed ingest must leave no entity rows after cleanup, found {entity_count} row(s)"
        chunk_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        assert chunk_count == 0, f"Failed ingest must leave no chunk rows after cleanup, found {chunk_count} row(s)"
        doc_count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert doc_count == 0, f"Failed ingest must leave no document rows after cleanup, found {doc_count} row(s)"
        source_count = conn.execute("SELECT count(*) FROM knowledge_sources").fetchone()[0]
        assert source_count == 0, f"Failed ingest must leave no source rows after cleanup, found {source_count} row(s)"


# ---------------------------------------------------------------------------
# _TrackingVectorStore — stateful stub for AC-6 tests
# ---------------------------------------------------------------------------


class _TrackingVectorStore:
    """Minimal stateful vector store stub.

    Tracks which IDs have been stored via ``store_embedding`` and reflects
    true delete semantics: ``delete_embedding`` returns True on the first
    call (embedding found and removed) and False on subsequent calls
    (embedding already gone).
    """

    def __init__(self) -> None:
        self.stored_ids: set[str] = set()

    def store_embedding(
        self,
        entity_or_doc_id: str,
        **_kwargs: object,
    ) -> None:
        self.stored_ids.add(entity_or_doc_id)

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        if entity_or_doc_id in self.stored_ids:
            self.stored_ids.discard(entity_or_doc_id)
            return True
        return False


# ---------------------------------------------------------------------------
# TestFromAC_DeleteDocumentDataVectorCleanup  (AC-6)
# ---------------------------------------------------------------------------


class TestFromAC_DeleteDocumentDataVectorCleanup:
    """AC-6: delete_document_data must delete vector embeddings for chunk IDs,
    not only relational rows (entities, edges, chunks, document_status, documents).

    Currently, delete_document_data does not call delete_chunk_embeddings, so
    vector payloads are left as orphaned Qdrant entries that search_similar
    can still return even after the document is removed from SQLite.
    """

    @pytest.mark.asyncio
    async def test_delete_document_data_calls_delete_embedding_for_each_chunk_id(
        self,
        conn: sqlite3.Connection,
        app_ctx: AppContext,
        store_components: dict,
        mock_vs: MagicMock,
    ) -> None:
        """delete_document_data must invoke delete_embedding for every chunk_id
        associated with the deleted document.

        Fails because delete_document_data only deletes relational rows and does
        NOT call delete_chunk_embeddings, leaving orphaned vector payloads.
        """
        ctx = _make_mcp_ctx(app_ctx)
        await ingest_document(
            ctx,
            text="content for vector cleanup test",
            metadata={"title": "CleanupDoc"},
            scope="team-a",
            source_url="https://example.test/cleanup",
        )
        doc_row = conn.execute("SELECT id FROM documents").fetchone()
        assert doc_row is not None, "No document row created by ingest"
        doc_id = doc_row[0]
        chunk_ids = [r[0] for r in conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()]
        assert chunk_ids, "No chunks created — cannot verify vector cleanup"

        # Reset so only calls from delete_document_data are observed.
        mock_vs.delete_embedding.reset_mock()
        store_components["doc_store"].delete_document_data(doc_id)

        called_ids = [
            c.args[0] if c.args else c.kwargs.get("entity_or_doc_id") for c in mock_vs.delete_embedding.call_args_list
        ]
        for chunk_id in chunk_ids:
            assert chunk_id in called_ids, (
                f"delete_document_data must call delete_embedding for "
                f"chunk_id={chunk_id!r}, but delete_embedding was only called "
                f"for: {called_ids!r}"
            )

    @pytest.mark.asyncio
    async def test_delete_document_data_second_delete_embedding_returns_false(self, conn: sqlite3.Connection) -> None:
        """After delete_document_data, subsequent delete_embedding calls for
        former chunk IDs must return False (embeddings were already removed).

        Uses a stateful tracking vector store so the test reflects true
        delete semantics: first call returns True (found + removed), second
        call returns False (already gone).

        Fails because delete_document_data does not call delete_chunk_embeddings,
        so embeddings remain in the tracking store and a second delete_embedding
        call still returns True.
        """
        tvs = _TrackingVectorStore()
        mock_emb = MagicMock()
        mock_emb.embed = MagicMock(return_value=[[0.1] * 10, [0.2] * 10])

        graph_store = GraphStore(conn)
        source_store = KnowledgeSourceStore(conn)
        doc_store = DocumentStore(conn, graph_store, tvs, mock_emb)
        chunker = TextChunker()
        extractor = EntityExtractor()
        pipeline = IngestPipeline(doc_store, extractor, chunker, source_store=source_store)

        result = await pipeline.ingest_text(
            text="content for tracking vector store cleanup test",
            metadata={"title": "TrackingDoc"},
            scope="team-a",
            source_url="https://example.test/tracking",
        )
        assert result.status == "ok", f"ingest_text must return status='ok', got {result.status!r}"

        doc_row = conn.execute("SELECT id FROM documents").fetchone()
        assert doc_row is not None, "No document row created"
        doc_id = doc_row[0]
        chunk_ids = [r[0] for r in conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()]
        assert chunk_ids, "No chunks created — cannot verify vector cleanup"

        stored_before = set(tvs.stored_ids)
        assert any(cid in stored_before for cid in chunk_ids), (
            "Tracking VS must have stored embeddings for chunk IDs during ingest"
        )

        # delete_document_data should call delete_chunk_embeddings internally,
        # removing chunk_ids from tvs.stored_ids.
        doc_store.delete_document_data(doc_id)

        # A second delete_embedding call must return False — embeddings gone.
        for chunk_id in chunk_ids:
            second_result = tvs.delete_embedding(chunk_id)
            assert second_result is False, (
                f"delete_embedding({chunk_id!r}) must return False after "
                "delete_document_data cleaned up the vector payloads, "
                "but it returned True (embedding was never removed)"
            )


# ---------------------------------------------------------------------------
# _SearchableVectorStore — stateful stub with search_similar for AC-5 tests
# ---------------------------------------------------------------------------


class _SearchableVectorStore(_TrackingVectorStore):
    """Stateful vector store stub that supports search_similar.

    Inherits ``store_embedding`` and ``delete_embedding`` from
    ``_TrackingVectorStore``.  Adds ``search_similar`` so that the real
    ``KnowledgeQueryService`` resolution chain can be exercised without a live
    Qdrant instance — the test focuses on chunk→document→source resolution,
    not semantic similarity.
    """

    def search_similar(
        self,
        _query_embedding: object,
        top_k: int = 5,
        _embedding_type: object = None,
        **_kwargs: object,  # absorbs scopes, recency_weight, decay_rate
    ) -> list[tuple[str, float]]:
        """Return stored chunk IDs with score 1.0 (ignores actual query similarity)."""
        ids = sorted(self.stored_ids)[:top_k]  # deterministic order
        return [(id_, 1.0) for id_ in ids]

    def get_embedding(self, _entity_or_doc_id: str) -> list[float] | None:
        return None


# ---------------------------------------------------------------------------
# TestFromAC_EndToEndSearchResolution  (AC-5 proof — retry cycle 6)
# ---------------------------------------------------------------------------


class TestFromAC_EndToEndSearchResolution:
    """AC-5 proof: real vector→chunk→document→source resolution chain.

    Reviewer gap (cycle 5): existing AC-5 tests mock query_service.query
    entirely, so the real KnowledgeQueryService resolution chain is never
    exercised. These tests wire the real KnowledgeQueryService with a
    stateful vector stub and assert the full resolution contract.

    Architect proof plan (cycle 5 return):
    - (a) Chunk IDs in chunks table match IDs stored in vector stub (ID continuity).
    - (b) Query result resolves to ingested document (title matches).
    - (c) Query result has source.name and source.config['url'] from KnowledgeSource row.
    - (d) Result carries source scope, not 'global'.
    """

    @pytest.mark.asyncio
    async def test_new_store_embeddings_api_uses_persisted_chunk_ids(self, conn: sqlite3.Connection) -> None:
        """DocumentStore.store_embeddings(document_id, chunks, embeddings) must preserve search ID continuity."""
        svs = _SearchableVectorStore()
        mock_emb_local: MagicMock = MagicMock()
        mock_emb_local.embed = MagicMock(return_value=[[0.1] * 10])

        graph_store = GraphStore(conn)
        doc_store = DocumentStore(conn, graph_store, svs, mock_emb_local)
        doc_store.insert_document(
            "doc-new-api",
            IntakeResult(
                content="new api search content",
                source="New API Doc",
                metadata={"title": "New API Doc"},
            ),
            scope="team-a",
            source_id=None,
        )
        chunks = [Chunk(text="new api searchable chunk", index=0, metadata={})]
        chunk_ids = doc_store.store_chunks("doc-new-api", chunks, scope="team-a")

        doc_store.store_embeddings(
            "doc-new-api",
            chunks,
            [HybridEmbedding(dense=[0.1] * 10)],
            scope="team-a",
        )

        assert svs.stored_ids == set(chunk_ids)

        query_service = KnowledgeQueryService(
            vector_store=svs,
            graph_store=graph_store,
            embedding_provider=mock_emb_local,
        )
        results = await query_service.query("new api", top_k=1, scopes=["team-a"])

        assert len(results) == 1
        assert results[0].doc_id == "doc-new-api"

    @pytest.mark.asyncio
    async def test_chunk_ids_in_db_match_vector_store_ids(self, conn: sqlite3.Connection) -> None:
        """Chunk IDs persisted in the chunks table must equal IDs in the vector store.

        ID continuity contract: store_chunks() generates UUID chunk IDs;
        store_embeddings() must forward those same IDs to store_embedding().
        Proves the live direct-ingest path uses actual chunk row IDs (not synthetic
        IDs from the dormant alternate-API branch).
        """
        svs = _SearchableVectorStore()
        mock_emb_local: MagicMock = MagicMock()
        mock_emb_local.embed = MagicMock(return_value=[[0.1] * 10, [0.2] * 10])

        graph_store = GraphStore(conn)
        source_store = KnowledgeSourceStore(conn)
        doc_store = DocumentStore(conn, graph_store, svs, mock_emb_local)
        pipeline = IngestPipeline(doc_store, EntityExtractor(), TextChunker(), source_store=source_store)

        result = await pipeline.ingest_text(
            text="chunk id continuity content for direct ingest path",
            metadata={"title": "ID Continuity Doc"},
            scope="team-a",
            source_url="https://example.test/id-continuity",
        )
        assert result.status == "ok", f"Ingest must succeed, got status={result.status!r}"

        db_chunk_ids = {r[0] for r in conn.execute("SELECT id FROM chunks").fetchall()}
        assert db_chunk_ids, "Ingest must create chunk rows in the database"
        assert db_chunk_ids == svs.stored_ids, (
            "Chunk IDs in the database must exactly match IDs stored in the vector "
            "store — the live ingest path must forward chunk row UUIDs to "
            "store_embedding(), not synthetic IDs. "
            f"DB chunk IDs: {db_chunk_ids!r}, vector store IDs: {svs.stored_ids!r}"
        )

    @pytest.mark.asyncio
    async def test_query_resolves_ingested_document_source_and_scope(self, conn: sqlite3.Connection) -> None:
        """KnowledgeQueryService.query() must resolve source name, URL, and scope
        for a document ingested via the live direct-ingest path.

        Exercises the full resolution chain without mocking:
        vector search → chunk_id → document_id → Document → KnowledgeSource.
        Asserts title, source.name, source.config['url'], and scope (not 'global').
        """
        svs = _SearchableVectorStore()
        mock_emb_local: MagicMock = MagicMock()
        mock_emb_local.embed = MagicMock(return_value=[[0.1] * 10, [0.2] * 10])

        graph_store = GraphStore(conn)
        source_store = KnowledgeSourceStore(conn)
        doc_store = DocumentStore(conn, graph_store, svs, mock_emb_local)
        pipeline = IngestPipeline(doc_store, EntityExtractor(), TextChunker(), source_store=source_store)

        ingest_result = await pipeline.ingest_text(
            text="end to end resolution test document content",
            metadata={"title": "E2E Resolution Doc"},
            scope="team-a",
            source_url="https://example.test/e2e",
        )
        assert ingest_result.status == "ok", (
            f"Ingest must succeed before query test, got status={ingest_result.status!r}"
        )

        query_service = KnowledgeQueryService(
            vector_store=svs,
            graph_store=graph_store,
            embedding_provider=mock_emb_local,
            source_store=source_store,
            similarity_threshold=0.3,
        )

        hits = await query_service.query("resolution test")
        assert hits, (
            "KnowledgeQueryService.query must return at least one result for a "
            "freshly ingested document when the vector store returns its chunk IDs"
        )

        hit = hits[0]

        # (b) document title resolves via chunk_id → document_id → Document
        assert hit.title == "E2E Resolution Doc", f"hit.title must be 'E2E Resolution Doc', got {hit.title!r}"

        # (c) source from linked KnowledgeSource row (not None)
        assert hit.source is not None, (
            "hit.source must be a KnowledgeSource object — the resolution chain "
            "must find the linked source via document.source_id"
        )
        assert hit.source.name == "https://example.test/e2e", (
            "hit.source.name must be 'https://example.test/e2e' (auto-created source "
            f"name equals source_url), got {hit.source.name!r}"
        )
        source_config_url = (hit.source.config or {}).get("url")
        assert source_config_url == "https://example.test/e2e", (
            f"hit.source.config['url'] must be 'https://example.test/e2e', got {source_config_url!r}"
        )

        # (d) scope must be source scope ('team-a'), not the default 'global'
        assert hit.scope == "team-a", f"hit.scope must be 'team-a' (source scope, not 'global'), got {hit.scope!r}"

    @pytest.mark.asyncio
    async def test_refresh_path_query_resolves_source_name_url_and_scope(self, conn: sqlite3.Connection) -> None:
        """KnowledgeQueryService.query() must resolve source name, URL, and scope
        for a document ingested via the refresh-equivalent path (IngestPipeline.ingest).

        Architect proof plan (cycle 7 return): both direct and refresh ingest paths
        must prove end-to-end search resolution. This test covers the refresh half.
        A pre-seeded source with config.url is used so the serializer resolves a URL;
        url_list multi-URL serialization is deferred as separate product-design debt.
        """
        svs = _SearchableVectorStore()
        mock_emb_local: MagicMock = MagicMock()
        mock_emb_local.embed = MagicMock(return_value=[[0.1] * 10, [0.2] * 10])

        graph_store = GraphStore(conn)
        source_store = KnowledgeSourceStore(conn)
        doc_store = DocumentStore(conn, graph_store, svs, mock_emb_local)
        pipeline = IngestPipeline(doc_store, EntityExtractor(), TextChunker(), source_store=source_store)

        # Pre-seed a source with config.url so the query serializer can resolve source.url.
        _insert_source_direct(
            conn,
            source_id="refresh-src-e2e",
            name="Refresh Source",
            enrich=1,
            scope="team-a",
            url="https://example.test/refresh",
        )

        # Ingest via the refresh pipeline path (ingest() not ingest_text()).
        intake = IntakeResult(
            content="refresh path end to end resolution document content",
            source="https://example.test/refresh",
            metadata={"title": "Refresh E2E Doc", "source_type": "url_list"},
        )
        ingest_result = await pipeline.ingest(
            intake,
            scope="team-a",
            source_id="refresh-src-e2e",
        )
        assert ingest_result.status == "ok", f"Refresh-path ingest must succeed, got status={ingest_result.status!r}"

        query_service = KnowledgeQueryService(
            vector_store=svs,
            graph_store=graph_store,
            embedding_provider=mock_emb_local,
            source_store=source_store,
            similarity_threshold=0.3,
        )

        hits = await query_service.query("refresh resolution")
        assert hits, (
            "KnowledgeQueryService.query must return at least one result for a "
            "document ingested via the refresh pipeline path"
        )

        hit = hits[0]

        # (b) document was found — resolve via chunk_id -> document_id -> Document.
        assert hit.title == "Refresh E2E Doc", f"hit.title must be 'Refresh E2E Doc', got {hit.title!r}"
        source_document = doc_store.get_document_by_source("https://example.test/refresh", scope="team-a")
        assert source_document is not None
        assert source_document.id == hit.doc_id
        assert source_document.metadata["intake_source"] == "https://example.test/refresh"

        # (c) source from the linked KnowledgeSource row
        assert hit.source is not None, (
            "hit.source must be a KnowledgeSource object — the refresh ingest path "
            "must link the document to its source via document.source_id"
        )
        assert hit.source.name == "Refresh Source", f"hit.source.name must be 'Refresh Source', got {hit.source.name!r}"
        source_config_url = (hit.source.config or {}).get("url")
        assert source_config_url == "https://example.test/refresh", (
            f"hit.source.config['url'] must be 'https://example.test/refresh', got {source_config_url!r}"
        )

        # (d) scope must be 'team-a', not 'global'
        assert hit.scope == "team-a", f"hit.scope must be 'team-a' (source scope, not 'global'), got {hit.scope!r}"


# ---------------------------------------------------------------------------
# TestFromAC_SQLiteThreadSafety  (AC-7)
# ---------------------------------------------------------------------------


class TestFromAC_SQLiteThreadSafety:
    """AC-7: IngestPipeline.ingest_text must succeed with a default-configured
    SQLite connection (no check_same_thread=False workaround).

    The existing conn fixture uses check_same_thread=False to mask a threading
    bug: asyncio.to_thread() moves SQLite operations onto a worker thread, but
    the connection was created on the main thread. A default sqlite3.connect()
    has check_same_thread=True, which raises ProgrammingError in this scenario.
    """

    @pytest.mark.asyncio
    async def test_ingest_text_does_not_raise_with_default_sqlite_connection(
        self,
    ) -> None:
        """ingest_text must return status='ok' when the pipeline's DocumentStore
        is backed by a connection from sqlite3.connect(path) with default threading
        parameters (check_same_thread=True by default).

        Fails because ingest_text wraps all SQLite writes in asyncio.to_thread(),
        which executes them on a worker thread. A default-configured SQLite
        connection raises ProgrammingError: "SQLite objects created in a thread
        can only be used in that same thread." The pipeline catches this and
        returns IngestResult(status='failed'), making the status assertion fail.
        """
        # Deliberate: no check_same_thread=False to match production init_db.
        default_conn = sqlite3.connect(":memory:")
        init_db(default_conn)

        mock_vs: MagicMock = MagicMock()
        mock_vs.store_embedding = MagicMock()
        mock_emb: MagicMock = MagicMock()
        mock_emb.embed = MagicMock(return_value=[[0.1] * 10])

        graph_store = GraphStore(default_conn)
        source_store = KnowledgeSourceStore(default_conn)
        doc_store = DocumentStore(default_conn, graph_store, mock_vs, mock_emb)
        chunker = TextChunker()
        extractor = EntityExtractor()
        pipeline = IngestPipeline(doc_store, extractor, chunker, source_store=source_store)

        result = await pipeline.ingest_text(
            text="t",
            metadata={"title": "T"},
            scope="s",
            source_url="https://example.test/t",
        )
        assert result.status == "ok", (
            "ingest_text must return status='ok' with a default SQLite connection "
            f"(check_same_thread=True), but got status={result.status!r}. "
            "This indicates asyncio.to_thread() operations raised ProgrammingError."
        )


# ---------------------------------------------------------------------------
# TestFromAC_RefreshEmbeddingFailurePropagation  (AC-2 retry-11)
# ---------------------------------------------------------------------------


class TestFromAC_RefreshEmbeddingFailurePropagation:
    """AC-2 (retry-11): Embedding failure inside IngestPipeline.ingest() must
    propagate as status='failed' so RefreshOrchestrator counts it as 'failed',
    not 'refreshed'.

    Bug: asyncio.gather(embed_coro, ..., return_exceptions=True) captures the
    embedding exception in all_results[0], but ingest() only checks all_results[1:]
    for extraction exceptions.  all_results[0] is never inspected.  The method
    continues to set_status('ok') and returns IngestResult(status='ok'), causing
    the refresh handler to increment refreshed += 1 even though no vectors were
    stored.
    """

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
    async def test_embedding_failure_in_ingest_yields_zero_refreshed(
        self,
        conn: sqlite3.Connection,
        store_components: dict,
        app_ctx: AppContext,
    ) -> None:
        """refresh_source must report refreshed=0, failed>=1 when store_embeddings raises.

        Fails because ingest() captures the embedding RuntimeError in all_results[0]
        via return_exceptions=True but never checks it — the call continues to
        set_status('ok') and returns IngestResult(status='ok'), so the refresh
        handler increments refreshed=1 instead of failed=1.
        """
        self._seed_url_list_source(conn)
        fake_intake = IntakeResult(
            content="content that will fail to embed",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        ctx = _make_mcp_ctx(app_ctx)

        def _embedding_explodes(*_args: object, **_kwargs: object) -> None:
            msg = "forced embedding failure"
            raise RuntimeError(msg)

        with (
            patch(
                "owlbear_knowledge.intake.read_url",
                new=AsyncMock(return_value=fake_intake),
            ),
            patch.object(
                store_components["doc_store"],
                "store_embeddings",
                side_effect=_embedding_explodes,
            ),
        ):
            result = await refresh_source(ctx, source_id="src-a")

        assert isinstance(result, dict), f"refresh_source must return a dict, got {result!r}"
        assert result.get("refreshed") == 0, (
            "refreshed must be 0 when store_embeddings raises — embedding failure "
            "must propagate as failed, not refreshed. "
            f"Got: {result}"
        )
        assert result.get("failed", 0) >= 1, f"failed must be >= 1 when store_embeddings raises. Got: {result}"


# ---------------------------------------------------------------------------
# TestFromAC_ReplaceOnChangeFailureCleanup  (AC-8 retry-11)
# ---------------------------------------------------------------------------


class TestFromAC_ReplaceOnChangeFailureCleanup:
    """AC-8 (retry-11): IngestPipeline.ingest() must clean up the partially
    written replacement document when a persistence failure occurs after
    delete_document_data(existing_id) has already executed.

    Bug: ingest() calls delete_document_data(existing_id) then insert_document()
    (which commits the replacement doc row), then store_chunks() — if store_chunks
    raises, the except Exception block returns status='failed' but performs NO
    cleanup of the committed replacement document row.  The orphaned document row
    violates the AC guarantee: 'persistence contains no document row for the
    replacement doc_id'.
    """

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
    async def test_replace_on_change_failure_leaves_no_orphaned_document(
        self,
        conn: sqlite3.Connection,
        store_components: dict,
    ) -> None:
        """Replacement document row must be cleaned up when store_chunks fails.

        Fails because ingest() commits the replacement document row via
        insert_document() before store_chunks() is called.  When store_chunks
        raises, the except Exception block returns status='failed' but does not
        call delete_document_data(replacement_doc_id) — leaving an orphaned row
        in the documents table.  AC-8: 'persistence contains no document row for
        the replacement doc_id'.
        """
        self._seed_url_list_source(conn)
        pipeline: IngestPipeline = store_components["pipeline"]

        intake_v1 = IntakeResult(
            content="Version 1 content — original document",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        # First ingest: must succeed so a content hash is recorded in document_status.
        result_v1 = await pipeline.ingest(intake_v1, scope="team-a", source_id="src-a")
        assert result_v1.status == "ok", (
            f"First ingest must succeed for replace-on-change to trigger on second "
            f"call, but got status={result_v1.status!r}"
        )
        assert conn.execute("SELECT count(*) FROM documents").fetchone()[0] == 1, (
            "Expected exactly 1 document row after first successful ingest"
        )

        intake_v2 = IntakeResult(
            content="Version 2 content — completely different to trigger replace-on-change",
            source="https://example.test/doc",  # same URL → triggers replace-on-change
            metadata={"source_type": "url_list"},
        )
        # Second ingest: check_content_changed returns (True, existing_id) because
        # content differs.  delete_document_data(v1) executes, then insert_document(v2)
        # commits, then store_chunks raises.  The except block returns 'failed' but
        # does NOT clean up the committed v2 document row.
        with patch.object(
            store_components["doc_store"],
            "store_chunks",
            side_effect=RuntimeError("forced store_chunks failure"),
        ):
            result_v2 = await pipeline.ingest(intake_v2, scope="team-a", source_id="src-a")

        assert result_v2.status == "failed", (
            f"ingest() must return status='failed' when store_chunks raises, got {result_v2.status!r}"
        )
        doc_count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert doc_count == 0, (
            "After replace-on-change failure, documents table must be empty — "
            "the original document was deleted by delete_document_data() and the "
            "replacement document row (committed by insert_document before "
            f"store_chunks raised) must be cleaned up, but found {doc_count} row(s). "
            "AC-8: 'persistence contains no document row for the replacement doc_id'."
        )

    @pytest.mark.asyncio
    async def test_replace_on_change_late_failure_leaves_no_chunks_or_vectors(
        self,
        conn: sqlite3.Connection,
        store_components: dict,
        mock_vs: MagicMock,
    ) -> None:
        """When store_extractions raises AFTER delete_document_data(v1) +
        insert_document(v2) + store_chunks(v2) + store_embeddings(v2) have all
        committed, _cleanup_failed_ingest must remove the replacement chunks and
        vector payloads.

        Reviewer gap (cycle 11, Finding 2): the existing AC-8 test injects failure at
        store_chunks (before any replacement chunks, vector payloads, entities, or
        edges can exist), so the cleanup assertions over those surfaces are vacuously
        true. This test injects failure at store_extractions so that replacement
        chunks and embeddings are committed before the failure, proving that
        _cleanup_failed_ingest handles the later failure point.

        AC-8 contract: 'persistence contains no document, chunk, vector payload,
        entity, or edge rows for the replacement doc_id'.
        """
        self._seed_url_list_source(conn)
        pipeline: IngestPipeline = store_components["pipeline"]

        intake_v1 = IntakeResult(
            content="Version 1 content for late-failure cleanup test",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        result_v1 = await pipeline.ingest(intake_v1, scope="team-a", source_id="src-a")
        assert result_v1.status == "ok", (
            f"First ingest must succeed for replace-on-change to fire on second call, got status={result_v1.status!r}"
        )

        # Reset so only v2-related mock calls are observed.
        mock_vs.delete_embedding.reset_mock()

        intake_v2 = IntakeResult(
            content="Version 2 content — different to trigger replace-on-change branch",
            source="https://example.test/doc",  # same URL triggers replace-on-change
            metadata={"source_type": "url_list"},
        )
        # Inject failure at store_extractions — AFTER the following have committed:
        #   delete_document_data(v1_id), insert_document(v2_id), store_chunks(v2_id),
        #   store_embeddings(v2_chunks). store_extractions raises before entity/edge writes.
        with patch.object(
            store_components["doc_store"],
            "store_extractions",
            side_effect=RuntimeError("forced late-stage extraction failure in replace-on-change"),
        ):
            result_v2 = await pipeline.ingest(intake_v2, scope="team-a", source_id="src-a")

        assert result_v2.status == "failed", (
            f"ingest() must return status='failed' when store_extractions raises, got {result_v2.status!r}"
        )

        # (a) documents=0: v1 deleted by replace-on-change; v2 cleaned by _cleanup_failed_ingest.
        doc_count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert doc_count == 0, (
            "After late-failure in replace-on-change, documents table must be empty — "
            "v1 was deleted by delete_document_data(existing_id) and the replacement "
            "v2 document row must be cleaned up by _cleanup_failed_ingest, "
            f"but found {doc_count} row(s). AC-8 contract."
        )

        # (b) chunks=0: v2 chunks committed by store_chunks must be cleaned up.
        chunk_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        assert chunk_count == 0, (
            "After late-failure in replace-on-change, chunks table must be empty — "
            "v2 replacement chunks (committed by store_chunks before store_extractions "
            f"raised) must be cleaned up by _cleanup_failed_ingest, found {chunk_count} row(s)"
        )

        # (c) Vector cleanup: delete_embedding called for v2 replacement chunk payloads.
        #     Note: delete_embedding is also called for v1 during the replace step itself,
        #     so call_count >= 1 is sufficient to prove vector cleanup ran.
        assert mock_vs.delete_embedding.call_count >= 1, (
            "delete_embedding must be called at least once after late-failure replace-on-change "
            "— _cleanup_failed_ingest must invoke vector cleanup for the v2 replacement "
            f"chunk IDs, got {mock_vs.delete_embedding.call_count} calls"
        )

        # (d) entities=0, edges=0: store_extractions raised before any writes.
        entity_count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
        assert entity_count == 0, (
            f"entities table must be empty after failed late-stage replace-on-change, found {entity_count} row(s)"
        )
        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            f"edges table must be empty after failed late-stage replace-on-change, found {edge_count} row(s)"
        )

    @pytest.mark.asyncio
    async def test_replace_on_change_v2_chunk_ids_specifically_deleted_from_vector_store(
        self,
        conn: sqlite3.Connection,
        store_components: dict,
        mock_vs: MagicMock,
    ) -> None:
        """_cleanup_failed_ingest must call delete_embedding for each v2 replacement
        chunk ID specifically, not just any chunk (e.g., v1 cleanup from
        delete_document_data(existing_id) also calls delete_embedding).

        Reviewer gap (cycle 12, Finding 1): the sibling test asserts
        call_count >= 1 after resetting the mock, but v1 cleanup (triggered by
        delete_document_data(existing_id) inside the replace-on-change branch)
        also calls delete_embedding — so a regression that skips v2 vector cleanup
        still satisfies call_count >= 1.

        This test captures v2 chunk IDs via a store_chunks spy and asserts that
        each appears in delete_embedding's call_args_list, falsifying any regression
        in replacement-vector cleanup.

        AC-8 contract: 'persistence contains no document, chunk, vector payload,
        entity, or edge rows for the replacement doc_id'.
        """
        self._seed_url_list_source(conn)
        pipeline: IngestPipeline = store_components["pipeline"]

        intake_v1 = IntakeResult(
            content="Version 1 content for per-chunk-id vector cleanup proof",
            source="https://example.test/doc",
            metadata={"source_type": "url_list"},
        )
        result_v1 = await pipeline.ingest(intake_v1, scope="team-a", source_id="src-a")
        assert result_v1.status == "ok", (
            f"First ingest must succeed for replace-on-change to fire on v2, got status={result_v1.status!r}"
        )

        # Spy on store_chunks to capture v2 replacement chunk IDs.
        # v1 ingest already completed, so the spy only captures v2 calls.
        v2_chunk_ids: list[str] = []
        real_store_chunks = store_components["doc_store"].store_chunks

        def _capturing_store_chunks(document_id: str, chunks: list[object], **kwargs: object) -> list[str]:
            ids = real_store_chunks(document_id, chunks, **kwargs)
            v2_chunk_ids.extend(ids)
            return ids

        intake_v2 = IntakeResult(
            content="Version 2 content — triggers replace-on-change via same URL",
            source="https://example.test/doc",  # same URL → replace-on-change branch
            metadata={"source_type": "url_list"},
        )
        # Inject failure at store_extractions AFTER v2 chunks + embeddings are committed.
        with (
            patch.object(
                store_components["doc_store"],
                "store_chunks",
                side_effect=_capturing_store_chunks,
            ),
            patch.object(
                store_components["doc_store"],
                "store_extractions",
                side_effect=RuntimeError("forced failure after v2 chunks+embeddings committed"),
            ),
        ):
            result_v2 = await pipeline.ingest(intake_v2, scope="team-a", source_id="src-a")

        assert result_v2.status == "failed", (
            f"ingest() must return status='failed' when store_extractions raises, got {result_v2.status!r}"
        )

        # Non-vacuous precondition: spy must have captured at least one v2 chunk ID.
        assert v2_chunk_ids, (
            "store_chunks spy captured no v2 chunk IDs — replace-on-change branch "
            "did not call store_chunks for v2, so per-ID assertion below is vacuous"
        )

        # Per-chunk-ID falsification: each v2 replacement chunk ID must appear in
        # delete_embedding's call_args_list.  This proves _cleanup_failed_ingest
        # cleaned up v2 replacement vector payloads specifically, not just v1 chunks.
        called_ids = {
            (c.args[0] if c.args else c.kwargs.get("entity_or_doc_id")) for c in mock_vs.delete_embedding.call_args_list
        }
        for chunk_id in v2_chunk_ids:
            assert chunk_id in called_ids, (
                f"delete_embedding must be called for v2 replacement "
                f"chunk_id={chunk_id!r} by _cleanup_failed_ingest, but was only "
                f"called for: {called_ids!r}. A regression that skips v2 vector "
                "cleanup passes 'call_count >= 1' because v1 cleanup also calls "
                "delete_embedding — this per-ID check prevents that."
            )

        # Existing AC-8 contract: no relational rows survive after failed replace-on-change.
        doc_count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        assert doc_count == 0, (
            f"documents table must be empty after failed replace-on-change, found {doc_count} row(s). AC-8 contract."
        )
        chunk_count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        assert chunk_count == 0, (
            f"chunks table must be empty after failed replace-on-change, found {chunk_count} row(s). AC-8 contract."
        )
        entity_count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
        assert entity_count == 0, (
            f"entities table must be empty after failed replace-on-change, found {entity_count} row(s). AC-8 contract."
        )
        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        assert edge_count == 0, (
            f"edges table must be empty after failed replace-on-change, found {edge_count} row(s). AC-8 contract."
        )
