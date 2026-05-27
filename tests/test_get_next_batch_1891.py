"""Tests for knowledge_enrichment_claim_batch → EnrichmentStore.claim_batch delegation (task #1891).

Source files under test:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py

Target interface:
  knowledge_enrichment_claim_batch — refactored to delegate queue claiming to EnrichmentStore.claim_batch()
  and hydrate each item via ContentStore.get_chunk/get_document and
  source_store_v2.get_source; response shape (EnrichmentChunk TypedDict) unchanged.

AC coverage:
  AC1 — knowledge_enrichment_claim_batch calls EnrichmentStore.claim_batch(EnrichmentParams(batch_size=limit))
  AC2 — Each claimed item hydrated via ContentStore.get_chunk(chunk_id),
         ContentStore.get_document(document_id), source_store_v2.get_source(source_id);
         items where get_chunk() returns None are skipped
  AC3 — Response dict per item preserves all 10 fields with correct new derivations:
         claim_token=batch.batch_id, claimed_at=item.started_at.isoformat(),
         text/doc_title/section_path/scope from ContentChunk/ContentDocument,
         source_name from SourceRecord, chunk_id/source_id from EnrichmentQueueItem
  AC4 — Old direct SQL claiming (conn.execute BEGIN IMMEDIATE / SELECT / UPDATE)
         not called; claiming delegated entirely to EnrichmentStore
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.protocols.enrichment import (
    EnrichmentBatch,
    EnrichmentParams,
    EnrichmentQueueItem,
    EnrichmentState,
)
from owlbear_mcp_knowledge.server import knowledge_enrichment_claim_batch


# ---------------------------------------------------------------------------
# Constants — distinguish SQL (old code) values from store (new code) values
# ---------------------------------------------------------------------------

_BATCH_ID = "test-batch-1891"
_ITEM_CHUNK_ID = "item-chunk-1891"
_ITEM_SOURCE_ID = "item-source-1891"
_ITEM_STARTED_AT = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)

_STORE_TEXT = "store-chunk-text-1891"
_STORE_DOC_TITLE = "Store Doc Title 1891"
_STORE_SOURCE_NAME = "Store Source Name 1891"
_STORE_DOC_ID = "store-doc-1891"
_STORE_SCOPE = "store-scope-1891"
_STORE_SECTION_PATH: tuple[str, ...] = ("section", "subsection")

# Old SQL SELECT column order:
#   c.id, c.content, d.title, c.metadata, ks.name, d.id, d.source_id, d.scope
_SQL_CHUNK_ID = "sql-chunk-1891"
_SQL_TEXT = "sql-text-1891"
_SQL_DOC_TITLE = "SQL Doc Title 1891"
_SQL_SECTION_PATH_METADATA = '{"section_path": "sql/old/path"}'
_SQL_SOURCE_NAME = "SQL Source Name 1891"
_SQL_DOC_ID = "sql-doc-1891"
_SQL_SOURCE_ID = "sql-source-1891"  # deliberately differs from _ITEM_SOURCE_ID
_SQL_SCOPE = "sql-scope-1891"

# Fake SQL row matching old SELECT shape — values all differ from store constants.
_SQL_ROW = (
    _SQL_CHUNK_ID,
    _SQL_TEXT,
    _SQL_DOC_TITLE,
    _SQL_SECTION_PATH_METADATA,
    _SQL_SOURCE_NAME,
    _SQL_DOC_ID,
    _SQL_SOURCE_ID,
    _SQL_SCOPE,
)


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def _make_item(
    chunk_id: str = _ITEM_CHUNK_ID,
    source_id: str = _ITEM_SOURCE_ID,
    started_at: datetime = _ITEM_STARTED_AT,
) -> EnrichmentQueueItem:
    """Minimal EnrichmentQueueItem for testing."""
    return EnrichmentQueueItem(
        id=f"eq-{chunk_id}",
        chunk_id=chunk_id,
        source_id=source_id,
        state=EnrichmentState.IN_PROGRESS,
        enqueued_at=datetime(2025, 1, 1, tzinfo=UTC),
        started_at=started_at,
    )


def _make_batch(*items: EnrichmentQueueItem, batch_id: str = _BATCH_ID) -> EnrichmentBatch:
    return EnrichmentBatch(items=items, batch_id=batch_id)


def _make_chunk_mock(
    *,
    text: str = _STORE_TEXT,
    document_id: str = _STORE_DOC_ID,
    source_id: str = _ITEM_SOURCE_ID,
    scope: str = _STORE_SCOPE,
    section_path: tuple[str, ...] = _STORE_SECTION_PATH,
) -> MagicMock:
    m = MagicMock(name="ContentChunk")
    m.text = text
    m.document_id = document_id
    m.source_id = source_id
    m.scope = scope
    m.section_path = section_path
    return m


def _make_document_mock(*, title: str = _STORE_DOC_TITLE) -> MagicMock:
    m = MagicMock(name="ContentDocument")
    m.title = title
    return m


def _make_source_mock(*, name: str = _STORE_SOURCE_NAME) -> MagicMock:
    m = MagicMock(name="SourceRecord")
    m.name = name
    return m


def _make_ctx(
    *,
    batch: EnrichmentBatch | None = None,
    chunk: MagicMock | None = None,
    document: MagicMock | None = None,
    source: MagicMock | None = None,
    sql_rows: list | None = None,
) -> MagicMock:
    """Return a mock FastMCP Context with all stores and conn configured.

    ``sql_rows`` controls what the mocked conn.execute(...).fetchall() returns,
    allowing tests to control whether old SQL path would produce results.
    Default [] means old code returns an empty batch.
    """
    if batch is None:
        batch = _make_batch(_make_item())
    if chunk is None:
        chunk = _make_chunk_mock()
    if document is None:
        document = _make_document_mock()
    if source is None:
        source = _make_source_mock()
    if sql_rows is None:
        sql_rows = []

    app_ctx = MagicMock()
    app_ctx.enrichment_store.claim_batch.return_value = batch
    app_ctx.content_store.get_chunk.return_value = chunk
    app_ctx.content_store.get_document.return_value = document
    app_ctx.source_store_v2.get_source.return_value = source

    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = sql_rows
    app_ctx.conn = conn

    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# AC1 — EnrichmentStore.claim_batch delegation
# ---------------------------------------------------------------------------


class TestFromAC_ClaimBatchDelegation:
    """AC1: knowledge_enrichment_claim_batch must delegate queue claiming to EnrichmentStore.claim_batch."""

    @pytest.mark.asyncio
    async def test_claim_batch_called_with_batch_size_from_limit(self) -> None:
        """claim_batch must be called with EnrichmentParams(batch_size=limit)."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_enrichment_claim_batch(ctx, limit=5)

        app_ctx.enrichment_store.claim_batch.assert_called_once_with(
            EnrichmentParams(batch_size=5)
        )

    @pytest.mark.asyncio
    async def test_claim_batch_called_with_default_limit_10(self) -> None:
        """Default limit=10 must be forwarded as batch_size=10."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_enrichment_claim_batch(ctx)

        app_ctx.enrichment_store.claim_batch.assert_called_once_with(
            EnrichmentParams(batch_size=10)
        )

    @pytest.mark.asyncio
    async def test_claim_batch_limit_clamped_to_100(self) -> None:
        """Limit above 100 is clamped to 100 before being passed to claim_batch."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_enrichment_claim_batch(ctx, limit=9999)

        app_ctx.enrichment_store.claim_batch.assert_called_once_with(
            EnrichmentParams(batch_size=100)
        )

    @pytest.mark.asyncio
    async def test_empty_batch_returns_empty_list(self) -> None:
        """When claim_batch returns no items, result must be an empty list.

        sql_rows=[_SQL_ROW] ensures old SQL path would return a non-empty result,
        forcing this test to fail against the current implementation.
        """
        batch = _make_batch()  # no items
        ctx = _make_ctx(batch=batch, sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx, limit=10)

        assert result == []


# ---------------------------------------------------------------------------
# AC2 — Per-item hydration and None-skip
# ---------------------------------------------------------------------------


class TestFromAC_PerItemHydration:
    """AC2: Each item hydrated via get_chunk/get_document/get_source; None skips item."""

    @pytest.mark.asyncio
    async def test_get_chunk_called_with_item_chunk_id(self) -> None:
        """content_store.get_chunk must be called with item.chunk_id."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_enrichment_claim_batch(ctx)

        app_ctx.content_store.get_chunk.assert_called_once_with(_ITEM_CHUNK_ID)

    @pytest.mark.asyncio
    async def test_get_document_called_with_chunk_document_id(self) -> None:
        """content_store.get_document must be called with chunk.document_id."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_enrichment_claim_batch(ctx)

        app_ctx.content_store.get_document.assert_called_once_with(_STORE_DOC_ID)

    @pytest.mark.asyncio
    async def test_get_source_called_with_item_source_id(self) -> None:
        """source_store_v2.get_source must be called with item.source_id."""
        ctx = _make_ctx()
        app_ctx = ctx.request_context.lifespan_context

        await knowledge_enrichment_claim_batch(ctx)

        app_ctx.source_store_v2.get_source.assert_called_once_with(_ITEM_SOURCE_ID)

    @pytest.mark.asyncio
    async def test_chunk_none_item_skipped(self) -> None:
        """Item must be omitted from result when content_store.get_chunk returns None.

        sql_rows=[_SQL_ROW] ensures old SQL path would return a non-empty result,
        forcing this test to fail against the current implementation.
        """
        ctx = _make_ctx(sql_rows=[_SQL_ROW])
        ctx.request_context.lifespan_context.content_store.get_chunk.return_value = None

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result == []

    @pytest.mark.asyncio
    async def test_two_items_same_doc_get_document_called_once(self) -> None:
        """get_document must be called once when two items share a document_id (dedup cache)."""
        item_a = _make_item(chunk_id="chk-a-1891")
        item_b = _make_item(chunk_id="chk-b-1891")
        batch = _make_batch(item_a, item_b)

        chunk_a = _make_chunk_mock(document_id="shared-doc-1891")
        chunk_b = _make_chunk_mock(document_id="shared-doc-1891")

        ctx = _make_ctx(batch=batch, document=_make_document_mock())
        app_ctx = ctx.request_context.lifespan_context
        app_ctx.content_store.get_chunk.side_effect = lambda cid: (
            chunk_a if cid == "chk-a-1891" else chunk_b
        )

        await knowledge_enrichment_claim_batch(ctx)

        assert app_ctx.content_store.get_document.call_count == 1, (
            "get_document should be called exactly once for a shared document_id "
            f"(dedup cache); got {app_ctx.content_store.get_document.call_count} calls"
        )

    @pytest.mark.asyncio
    async def test_two_items_same_source_get_source_called_once(self) -> None:
        """get_source must be called once when two items share a source_id (dedup cache)."""
        item_a = _make_item(chunk_id="chk-a-1891", source_id="shared-src-1891")
        item_b = _make_item(chunk_id="chk-b-1891", source_id="shared-src-1891")
        batch = _make_batch(item_a, item_b)

        chunk_a = _make_chunk_mock(document_id="doc-a-1891", source_id="shared-src-1891")
        chunk_b = _make_chunk_mock(document_id="doc-b-1891", source_id="shared-src-1891")

        ctx = _make_ctx(batch=batch, source=_make_source_mock())
        app_ctx = ctx.request_context.lifespan_context
        app_ctx.content_store.get_chunk.side_effect = lambda cid: (
            chunk_a if cid == "chk-a-1891" else chunk_b
        )

        await knowledge_enrichment_claim_batch(ctx)

        assert app_ctx.source_store_v2.get_source.call_count == 1, (
            "get_source should be called exactly once for a shared source_id "
            f"(dedup cache); got {app_ctx.source_store_v2.get_source.call_count} calls"
        )


# ---------------------------------------------------------------------------
# AC3 — Response field mapping
# ---------------------------------------------------------------------------


class TestFromAC_ResponseFieldMapping:
    """AC3: Each response dict must derive all 10 fields from new store calls.

    All tests supply sql_rows=[_SQL_ROW] so old SQL path returns a non-empty result
    with known field values that differ from the store-mock constants, forcing each
    assertion to fail against the current implementation.
    """

    @pytest.mark.asyncio
    async def test_claim_token_is_batch_batch_id(self) -> None:
        """claim_token must be batch.batch_id, not a freshly generated UUID."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["claim_token"] == _BATCH_ID, (
            f"claim_token must be batch.batch_id={_BATCH_ID!r}; "
            f"got {result[0]['claim_token']!r} (old code generates uuid4().hex)"
        )

    @pytest.mark.asyncio
    async def test_claimed_at_is_item_started_at_isoformat(self) -> None:
        """claimed_at must be item.started_at.isoformat(), not datetime.now().isoformat()."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        expected = _ITEM_STARTED_AT.isoformat()
        assert result[0]["claimed_at"] == expected, (
            f"claimed_at must be item.started_at.isoformat()={expected!r}; "
            f"got {result[0]['claimed_at']!r} (old code uses datetime.now())"
        )

    @pytest.mark.asyncio
    async def test_chunk_id_from_item_not_sql(self) -> None:
        """chunk_id must come from EnrichmentQueueItem.chunk_id, not SQL row[0]."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["chunk_id"] == _ITEM_CHUNK_ID, (
            f"chunk_id must be item.chunk_id={_ITEM_CHUNK_ID!r}; "
            f"got {result[0]['chunk_id']!r} (old code uses SQL c.id={_SQL_CHUNK_ID!r})"
        )

    @pytest.mark.asyncio
    async def test_text_from_content_chunk(self) -> None:
        """text must come from ContentChunk.text, not SQL row c.content."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["text"] == _STORE_TEXT, (
            f"text must be chunk.text={_STORE_TEXT!r}; "
            f"got {result[0]['text']!r} (old code uses SQL c.content={_SQL_TEXT!r})"
        )

    @pytest.mark.asyncio
    async def test_doc_title_from_content_document(self) -> None:
        """doc_title must come from ContentDocument.title, not SQL row d.title."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["doc_title"] == _STORE_DOC_TITLE, (
            f"doc_title must be document.title={_STORE_DOC_TITLE!r}; "
            f"got {result[0]['doc_title']!r} (old code uses SQL d.title={_SQL_DOC_TITLE!r})"
        )

    @pytest.mark.asyncio
    async def test_section_path_joined_from_chunk_tuple(self) -> None:
        """section_path must be '/'.join(chunk.section_path) for a non-empty tuple."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])  # SQL metadata yields "sql/old/path"

        result = await knowledge_enrichment_claim_batch(ctx)

        expected = "/".join(_STORE_SECTION_PATH)  # "section/subsection"
        assert result[0]["section_path"] == expected, (
            f"section_path must be '/'.join(chunk.section_path)={expected!r}; "
            f"got {result[0]['section_path']!r} "
            f"(old code parses JSON metadata: {_SQL_SECTION_PATH_METADATA!r})"
        )

    @pytest.mark.asyncio
    async def test_section_path_none_when_empty_tuple(self) -> None:
        """section_path must be None when chunk.section_path is an empty tuple."""
        chunk = _make_chunk_mock(section_path=())
        # SQL row has non-empty section_path metadata → old code would return non-None
        ctx = _make_ctx(chunk=chunk, sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["section_path"] is None, (
            f"section_path must be None for empty tuple; "
            f"got {result[0]['section_path']!r} "
            f"(old code parses SQL metadata={_SQL_SECTION_PATH_METADATA!r})"
        )

    @pytest.mark.asyncio
    async def test_source_name_from_source_store(self) -> None:
        """source_name must come from SourceRecord.name, not SQL row ks.name."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["source_name"] == _STORE_SOURCE_NAME, (
            f"source_name must be source.name={_STORE_SOURCE_NAME!r}; "
            f"got {result[0]['source_name']!r} (old code uses SQL ks.name={_SQL_SOURCE_NAME!r})"
        )

    @pytest.mark.asyncio
    async def test_document_id_from_content_chunk(self) -> None:
        """document_id must come from ContentChunk.document_id, not SQL row d.id."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["document_id"] == _STORE_DOC_ID, (
            f"document_id must be chunk.document_id={_STORE_DOC_ID!r}; "
            f"got {result[0]['document_id']!r} (old code uses SQL d.id={_SQL_DOC_ID!r})"
        )

    @pytest.mark.asyncio
    async def test_source_id_from_item(self) -> None:
        """source_id must come from EnrichmentQueueItem.source_id, not SQL row d.source_id."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["source_id"] == _ITEM_SOURCE_ID, (
            f"source_id must be item.source_id={_ITEM_SOURCE_ID!r}; "
            f"got {result[0]['source_id']!r} (old code uses SQL d.source_id={_SQL_SOURCE_ID!r})"
        )

    @pytest.mark.asyncio
    async def test_scope_from_content_chunk(self) -> None:
        """scope must come from ContentChunk.scope, not SQL row d.scope."""
        ctx = _make_ctx(sql_rows=[_SQL_ROW])

        result = await knowledge_enrichment_claim_batch(ctx)

        assert result[0]["scope"] == _STORE_SCOPE, (
            f"scope must be chunk.scope={_STORE_SCOPE!r}; "
            f"got {result[0]['scope']!r} (old code uses SQL d.scope={_SQL_SCOPE!r})"
        )


# ---------------------------------------------------------------------------
# AC4 — Old SQL claiming path removed
# ---------------------------------------------------------------------------


class TestFromAC_OldSqlRemoved:
    """AC4: Old direct SQL claiming via conn.execute must not be invoked."""

    @pytest.mark.asyncio
    async def test_conn_execute_not_called(self) -> None:
        """conn.execute must not be called — SQL claiming delegated to EnrichmentStore."""
        ctx = _make_ctx()
        conn = ctx.request_context.lifespan_context.conn

        await knowledge_enrichment_claim_batch(ctx)

        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_conn_commit_not_called(self) -> None:
        """conn.commit must not be called — transaction handled inside EnrichmentStore."""
        ctx = _make_ctx()
        conn = ctx.request_context.lifespan_context.conn

        await knowledge_enrichment_claim_batch(ctx)

        conn.commit.assert_not_called()
