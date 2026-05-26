"""Tests for ContentStore — ingest & dedup (task #1871).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/content.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/content.py

AC coverage:
  AC1  — SQLite-first atomicity; Qdrant failure raises, SQLite state intact
  AC2  — Deterministic document_id via UUID5 from (source_id, external_id|uri|title, scope)
  AC3  — CREATED / UNCHANGED / REPLACED state machine
  AC4  — trusted flag propagated to document and chunk records
  AC5  — get_document returns ContentDocument or None
  AC6  — get_chunk returns ContentChunk or None
  AC7  — list_chunks ordered by index ascending; empty for unknown document
  AC8  — Qdrant vectors created on CREATED/REPLACED; old vectors deleted on REPLACED
  AC9  — ensure_tables() idempotent DDL
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.protocols.content import (
    ContentDocument,
    ContentChunk,
    ContentIngestRequest,
    ContentIngestState,
)
from owlbear_knowledge.stores.content import ContentStore  # greenfield — ImportError expected


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(  # noqa: PLR0913
    *,
    source_id: str = "src-1",
    title: str = "Test Doc",
    text: str = "The quick brown fox jumps over the lazy dog. " * 4,
    scope: str = "global",
    uri: str | None = None,
    external_id: str | None = None,
    trusted: bool = False,
) -> ContentIngestRequest:
    return ContentIngestRequest(
        source_id=source_id,
        title=title,
        text=text,
        scope=scope,
        uri=uri,
        external_id=external_id,
        trusted=trusted,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_vectors() -> MagicMock:
    """Mocked vector store -- never touches real Qdrant."""
    return MagicMock(name="vector_store")


@pytest.fixture()
def mock_embed() -> MagicMock:
    """Mocked embedding provider returning plausible fake vectors."""
    e = MagicMock(name="embedding_provider")
    e.embed.side_effect = lambda texts: [[0.1] * 1024 for _ in texts]
    return e


@pytest.fixture()
def store(mock_vectors: MagicMock, mock_embed: MagicMock) -> ContentStore:
    """Fully wired ContentStore using in-memory SQLite and mocked dependencies."""
    db = sqlite3.connect(":memory:")
    chunker = TextChunker(target_tokens=50)
    s = ContentStore(
        db=db,
        vector_store=mock_vectors,
        embedding_provider=mock_embed,
        chunker=chunker,
    )
    s.ensure_tables()
    return s


# ---------------------------------------------------------------------------
# TestFromAC_ContentStore
# ---------------------------------------------------------------------------


class TestFromAC_ContentStore:
    """AC-derived tests for ContentStore contract (AC1-AC9)."""

    # ------------------------------------------------------------------ AC3
    # Happy: CREATED / UNCHANGED / REPLACED state machine

    @pytest.mark.asyncio
    async def test_ingest_new_document_returns_created_state(
        self, store: ContentStore
    ) -> None:
        """AC3: first ingest of a new document_id returns state=CREATED."""
        req = _make_request()
        result = await store.ingest(req)

        assert result.state == ContentIngestState.CREATED

    @pytest.mark.asyncio
    async def test_ingest_new_document_has_non_empty_chunk_ids(
        self, store: ContentStore
    ) -> None:
        """AC3: CREATED result contains at least one chunk_id."""
        req = _make_request()
        result = await store.ingest(req)

        assert len(result.chunk_ids) >= 1

    @pytest.mark.asyncio
    async def test_ingest_new_document_has_empty_replaced_chunk_ids(
        self, store: ContentStore
    ) -> None:
        """AC3: CREATED result has empty replaced_chunk_ids."""
        req = _make_request()
        result = await store.ingest(req)

        assert result.replaced_chunk_ids == ()

    @pytest.mark.asyncio
    async def test_ingest_same_text_returns_unchanged_state(
        self, store: ContentStore
    ) -> None:
        """AC3: re-ingesting the same document with identical text returns UNCHANGED."""
        req = _make_request()
        await store.ingest(req)
        result2 = await store.ingest(req)

        assert result2.state == ContentIngestState.UNCHANGED

    @pytest.mark.asyncio
    async def test_ingest_changed_text_returns_replaced_state(
        self, store: ContentStore
    ) -> None:
        """AC3: re-ingesting the same document with different text returns REPLACED."""
        req1 = _make_request(text="Original content. " * 6)
        req2 = _make_request(text="Completely updated content. " * 6)
        await store.ingest(req1)
        result2 = await store.ingest(req2)

        assert result2.state == ContentIngestState.REPLACED

    @pytest.mark.asyncio
    async def test_ingest_replaced_returns_non_empty_replaced_chunk_ids(
        self, store: ContentStore
    ) -> None:
        """AC3: REPLACED result exposes old chunk_ids in replaced_chunk_ids."""
        req1 = _make_request(text="Original content. " * 6)
        first = await store.ingest(req1)
        req2 = _make_request(text="Completely updated content. " * 6)
        result2 = await store.ingest(req2)

        assert result2.replaced_chunk_ids == first.chunk_ids

    # ------------------------------------------------------------------ AC2
    # Happy/Edge: deterministic document_id via UUID5

    @pytest.mark.asyncio
    async def test_document_id_same_across_calls_with_external_id(
        self, store: ContentStore
    ) -> None:
        """AC2: two ingests with identical (source_id, external_id, scope) produce same document_id."""
        req = _make_request(external_id="ext-42")
        r1 = await store.ingest(req)
        req2 = _make_request(
            text="Completely different updated text. " * 6, external_id="ext-42"
        )
        r2 = await store.ingest(req2)

        assert r1.document_id == r2.document_id

    @pytest.mark.asyncio
    async def test_document_id_uses_uri_when_no_external_id(
        self, store: ContentStore
    ) -> None:
        """AC2: document_id derived from uri when external_id is absent."""
        req = _make_request(uri="https://example.com/doc")
        r1 = await store.ingest(req)
        req2 = _make_request(
            text="Revised text here. " * 6, uri="https://example.com/doc"
        )
        r2 = await store.ingest(req2)

        assert r1.document_id == r2.document_id

    @pytest.mark.asyncio
    async def test_document_id_uses_title_when_no_external_id_or_uri(
        self, store: ContentStore
    ) -> None:
        """AC2: document_id derived from title when external_id and uri are both absent."""
        req = _make_request(title="Canonical Title")
        r1 = await store.ingest(req)
        req2 = _make_request(title="Canonical Title", text="Revised content. " * 6)
        r2 = await store.ingest(req2)

        assert r1.document_id == r2.document_id

    @pytest.mark.asyncio
    async def test_document_id_differs_for_different_scope(
        self, store: ContentStore
    ) -> None:
        """AC2 boundary: same source_id + title but different scope → different document_id."""
        req_a = _make_request(scope="project-A", external_id="same-ext")
        req_b = _make_request(scope="project-B", external_id="same-ext")
        r_a = await store.ingest(req_a)
        r_b = await store.ingest(req_b)

        assert r_a.document_id != r_b.document_id

    # ------------------------------------------------------------------ AC2 boundary: identity priority

    @pytest.mark.asyncio
    async def test_document_id_prefers_external_id_over_uri_and_title(
        self, store: ContentStore
    ) -> None:
        """AC2 boundary: external_id takes priority over uri and title for identity."""
        req_with_ext = _make_request(
            external_id="ext-priority", uri="https://example.com/x", title="Title X"
        )
        req_uri_only = _make_request(
            uri="https://example.com/x", title="Title X"
        )
        r_ext = await store.ingest(req_with_ext)
        r_uri = await store.ingest(req_uri_only)

        # Different identity basis → different document_id
        assert r_ext.document_id != r_uri.document_id

    # ------------------------------------------------------------------ AC5
    # get_document

    @pytest.mark.asyncio
    async def test_get_document_returns_content_document_after_ingest(
        self, store: ContentStore
    ) -> None:
        """AC5: get_document returns ContentDocument for a known document_id."""
        req = _make_request(title="Doc Alpha", source_id="src-a")
        result = await store.ingest(req)

        doc = store.get_document(result.document_id)

        assert isinstance(doc, ContentDocument)
        assert doc.document_id == result.document_id
        assert doc.source_id == "src-a"
        assert doc.title == "Doc Alpha"

    def test_get_document_returns_none_for_unknown_id(
        self, store: ContentStore
    ) -> None:
        """AC5: get_document returns None for an ID that was never ingested."""
        doc = store.get_document("non-existent-id-xyz")

        assert doc is None

    @pytest.mark.asyncio
    async def test_get_document_has_content_hash(
        self, store: ContentStore
    ) -> None:
        """AC5: returned ContentDocument carries a non-empty content_hash."""
        req = _make_request()
        result = await store.ingest(req)

        doc = store.get_document(result.document_id)

        assert doc is not None
        assert doc.content_hash != ""
        assert len(doc.content_hash) == 64  # SHA-256 hex digest

    # ------------------------------------------------------------------ AC6
    # get_chunk

    @pytest.mark.asyncio
    async def test_get_chunk_returns_content_chunk_after_ingest(
        self, store: ContentStore
    ) -> None:
        """AC6: get_chunk returns ContentChunk with text and content_hash."""
        req = _make_request(text="Sample chunk text. " * 4)
        result = await store.ingest(req)

        chunk = store.get_chunk(result.chunk_ids[0])

        assert isinstance(chunk, ContentChunk)
        assert chunk.text != ""
        assert chunk.content_hash != ""

    def test_get_chunk_returns_none_for_unknown_id(
        self, store: ContentStore
    ) -> None:
        """AC6: get_chunk returns None for an ID that was never stored."""
        chunk = store.get_chunk("non-existent-chunk-id")

        assert chunk is None

    # ------------------------------------------------------------------ AC7
    # list_chunks

    @pytest.mark.asyncio
    async def test_list_chunks_ordered_by_index_ascending(
        self, store: ContentStore
    ) -> None:
        """AC7: list_chunks returns chunks ordered by index ascending."""
        long_text = "Word. " * 500
        req = _make_request(text=long_text)
        result = await store.ingest(req)

        chunks = store.list_chunks(result.document_id)

        assert len(chunks) >= 2, "Need multi-chunk doc to verify ordering"
        indices = [c.index for c in chunks]
        assert indices == sorted(indices)

    def test_list_chunks_returns_empty_tuple_for_unknown_document(
        self, store: ContentStore
    ) -> None:
        """AC7: list_chunks returns empty tuple when document_id is not known."""
        chunks = store.list_chunks("unknown-doc-id")

        assert chunks == ()

    @pytest.mark.asyncio
    async def test_list_chunks_returns_only_current_chunks_after_replace(
        self, store: ContentStore
    ) -> None:
        """AC7: list_chunks excludes stale chunks from a prior REPLACED ingest."""
        req1 = _make_request(text="Original text. " * 6)
        first = await store.ingest(req1)
        req2 = _make_request(text="Updated replacement content is different here. " * 6)
        second = await store.ingest(req2)

        chunks = store.list_chunks(first.document_id)
        current_ids = {c.id for c in chunks}

        # Replaced (stale) chunks must not appear
        for old_id in first.chunk_ids:
            assert old_id not in current_ids
        # New chunks must appear
        for new_id in second.chunk_ids:
            assert new_id in current_ids

    # ------------------------------------------------------------------ AC4
    # trusted flag propagation

    @pytest.mark.asyncio
    async def test_trusted_true_propagated_to_document(
        self, store: ContentStore
    ) -> None:
        """AC4: ingest with trusted=True stores document with trusted=True."""
        req = _make_request(trusted=True)
        result = await store.ingest(req)

        doc = store.get_document(result.document_id)

        assert doc is not None
        assert doc.trusted is True

    @pytest.mark.asyncio
    async def test_trusted_true_propagated_to_chunks(
        self, store: ContentStore
    ) -> None:
        """AC4: ingest with trusted=True stores all chunks with trusted=True."""
        req = _make_request(trusted=True)
        result = await store.ingest(req)

        chunks = store.list_chunks(result.document_id)

        assert len(chunks) >= 1
        assert all(c.trusted is True for c in chunks)

    @pytest.mark.asyncio
    async def test_trusted_false_propagated_to_document(
        self, store: ContentStore
    ) -> None:
        """AC4: ingest with trusted=False (default) stores document with trusted=False."""
        req = _make_request(trusted=False)
        result = await store.ingest(req)

        doc = store.get_document(result.document_id)

        assert doc is not None
        assert doc.trusted is False

    @pytest.mark.asyncio
    async def test_trusted_false_propagated_to_chunks(
        self, store: ContentStore
    ) -> None:
        """AC4: ingest with trusted=False stores all chunks with trusted=False."""
        req = _make_request(trusted=False)
        result = await store.ingest(req)

        chunks = store.list_chunks(result.document_id)

        assert len(chunks) >= 1
        assert all(c.trusted is False for c in chunks)

    # ------------------------------------------------------------------ AC8
    # Qdrant vector operations

    @pytest.mark.asyncio
    async def test_ingest_created_upserts_vectors_to_qdrant(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC8: CREATED ingest triggers at least one Qdrant upsert call."""
        req = _make_request()
        await store.ingest(req)

        assert mock_vectors.upsert.called, "vector_store.upsert must be called on CREATED ingest"

    @pytest.mark.asyncio
    async def test_ingest_unchanged_does_not_call_qdrant(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC8 / AC3: UNCHANGED ingest must not write any new Qdrant vectors."""
        req = _make_request()
        await store.ingest(req)
        mock_vectors.reset_mock()

        # Second ingest is UNCHANGED
        await store.ingest(req)

        # No mutating calls should occur (upsert/delete/etc.)
        upsert_calls = [
            c for c in mock_vectors.method_calls
            if "upsert" in c[0] or "delete" in c[0] or "upload" in c[0]
        ]
        assert upsert_calls == [], (
            "UNCHANGED ingest must not trigger any Qdrant writes"
        )

    @pytest.mark.asyncio
    async def test_ingest_replaced_deletes_old_vectors_before_upsert(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC8: REPLACED ingest deletes old vectors before upserting new ones."""
        req1 = _make_request(text="First version. " * 6)
        await store.ingest(req1)
        mock_vectors.reset_mock()

        req2 = _make_request(text="Second version - updated. " * 6)
        await store.ingest(req2)

        method_names = [c[0] for c in mock_vectors.method_calls]
        delete_positions = [i for i, n in enumerate(method_names) if "delete" in n]
        upsert_positions = [i for i, n in enumerate(method_names) if "upsert" in n or "upload" in n]

        assert delete_positions, "REPLACED must delete old vectors"
        assert upsert_positions, "REPLACED must upsert new vectors"
        assert min(delete_positions) < min(upsert_positions), (
            "Deletes must precede upserts on REPLACED"
        )

    # ------------------------------------------------------------------ AC1
    # SQLite-first atomicity; Qdrant failure semantics

    @pytest.mark.asyncio
    async def test_ingest_qdrant_failure_raises(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: Qdrant failure propagates as an exception to the caller."""
        mock_vectors.upsert = MagicMock(side_effect=RuntimeError("qdrant unavailable"))
        mock_vectors.upload_points = MagicMock(side_effect=RuntimeError("qdrant unavailable"))
        mock_vectors.upload_collection = MagicMock(side_effect=RuntimeError("qdrant unavailable"))

        req = _make_request()
        with pytest.raises(RuntimeError):
            await store.ingest(req)

    @pytest.mark.asyncio
    async def test_ingest_qdrant_failure_sqlite_state_is_consistent(
        self, mock_vectors: MagicMock, mock_embed: MagicMock
    ) -> None:
        """AC1: SQLite document record survives a Qdrant write failure.

        The store commits to SQLite first, then writes to Qdrant. When Qdrant
        fails, the SQLite record must remain so the caller can retry without
        orphaning data.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)
        mock_vectors.upsert = MagicMock(side_effect=RuntimeError("qdrant unavailable"))
        mock_vectors.upload_points = MagicMock(side_effect=RuntimeError("qdrant unavailable"))
        mock_vectors.upload_collection = MagicMock(side_effect=RuntimeError("qdrant unavailable"))
        s = ContentStore(
            db=db,
            vector_store=mock_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        s.ensure_tables()

        req = _make_request()
        with pytest.raises(RuntimeError):
            await s.ingest(req)

        # SQLite must have committed the document record before Qdrant was touched
        cursor = db.execute("SELECT COUNT(*) FROM content_documents")
        count = cursor.fetchone()[0]
        assert count >= 1, (
            "SQLite must retain the document record after Qdrant failure (AC1: consistent for retry)"
        )

    # ------------------------------------------------------------------ AC9
    # ensure_tables idempotency

    def test_ensure_tables_creates_content_documents_table(self) -> None:
        """AC9: ensure_tables() creates the content_documents table."""
        db = sqlite3.connect(":memory:")
        s = ContentStore(
            db=db,
            vector_store=MagicMock(),
            embedding_provider=MagicMock(),
            chunker=TextChunker(target_tokens=50),
        )
        s.ensure_tables()

        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='content_documents'"
        )
        row = cursor.fetchone()
        assert row is not None, "content_documents table must exist after ensure_tables()"

    def test_ensure_tables_creates_content_chunks_table(self) -> None:
        """AC9: ensure_tables() creates the content_chunks table."""
        db = sqlite3.connect(":memory:")
        s = ContentStore(
            db=db,
            vector_store=MagicMock(),
            embedding_provider=MagicMock(),
            chunker=TextChunker(target_tokens=50),
        )
        s.ensure_tables()

        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='content_chunks'"
        )
        row = cursor.fetchone()
        assert row is not None, "content_chunks table must exist after ensure_tables()"

    def test_ensure_tables_idempotent_called_twice(self) -> None:
        """AC9: calling ensure_tables() twice does not raise."""
        db = sqlite3.connect(":memory:")
        s = ContentStore(
            db=db,
            vector_store=MagicMock(),
            embedding_provider=MagicMock(),
            chunker=TextChunker(target_tokens=50),
        )
        s.ensure_tables()
        s.ensure_tables()  # Must not raise

    # ------------------------------------------------------------------ AC3 boundary
    # UNCHANGED contract details

    @pytest.mark.asyncio
    async def test_ingest_unchanged_preserves_chunk_ids(
        self, store: ContentStore
    ) -> None:
        """AC3 boundary: UNCHANGED result returns same chunk_ids as original ingest."""
        req = _make_request()
        first = await store.ingest(req)
        second = await store.ingest(req)

        assert second.state == ContentIngestState.UNCHANGED
        assert set(second.chunk_ids) == set(first.chunk_ids)

    @pytest.mark.asyncio
    async def test_ingest_unchanged_has_empty_replaced_chunk_ids(
        self, store: ContentStore
    ) -> None:
        """AC3 boundary: UNCHANGED result has empty replaced_chunk_ids."""
        req = _make_request()
        await store.ingest(req)
        second = await store.ingest(req)

        assert second.replaced_chunk_ids == ()

    @pytest.mark.asyncio
    async def test_ingest_result_carries_source_id(
        self, store: ContentStore
    ) -> None:
        """AC3 / contract: ContentIngestResult carries the source_id from the request."""
        req = _make_request(source_id="src-test-99")
        result = await store.ingest(req)

        assert result.source_id == "src-test-99"

    @pytest.mark.asyncio
    async def test_ingest_result_carries_content_hash(
        self, store: ContentStore
    ) -> None:
        """AC3 / contract: ContentIngestResult carries a non-empty content_hash."""
        req = _make_request()
        result = await store.ingest(req)

        assert result.content_hash != ""
        assert len(result.content_hash) == 64  # SHA-256 hex digest

    # ------------------------------------------------------------------ AC1 retry
    # Retry-safe vector repair after post-commit Qdrant failure

    @pytest.mark.asyncio
    async def test_ingest_retry_after_qdrant_failure_writes_vectors(
        self, mock_embed: MagicMock
    ) -> None:
        """AC1: retrying ingest after a post-commit Qdrant failure must write vectors.

        When Qdrant fails after SQLite commits the document, the document record
        exists with the same content_hash. A subsequent retry with identical content
        MUST write vectors rather than short-circuiting through UNCHANGED
        (which leaves vectors permanently unrepaired and violates the retry contract).
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)
        req = _make_request()

        # Step 1: first ingest — SQLite commits, then Qdrant fails
        failing_vectors = MagicMock()
        failing_vectors.upsert = MagicMock(side_effect=RuntimeError("qdrant down"))
        s = ContentStore(
            db=db,
            vector_store=failing_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        s.ensure_tables()
        with pytest.raises(RuntimeError):
            await s.ingest(req)

        # Step 2: retry — Qdrant back online, same DB (document_id+hash already committed)
        retry_vectors = MagicMock()
        s2 = ContentStore(
            db=db,
            vector_store=retry_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        await s2.ingest(req)

        # Vectors MUST be written — current UNCHANGED short-circuit skips all writes,
        # leaving the document permanently without vector representation.
        assert retry_vectors.upsert.called, (
            "AC1 retry contract violated: second ingest after Qdrant failure must write "
            "vectors via upsert to reach consistent state — UNCHANGED short-circuit leaves "
            "vectors unrepaired"
        )

    # ------------------------------------------------------------------ AC5 metadata
    # get_document metadata round-trip proof

    @pytest.mark.asyncio
    async def test_get_document_returns_request_metadata(
        self, store: ContentStore
    ) -> None:
        """AC5: get_document returns ContentDocument whose metadata matches the request.

        Explicit round-trip proof: metadata supplied in ContentIngestRequest must be
        retrievable via get_document() without loss or mutation.
        """
        from owlbear_knowledge.protocols.content import ContentIngestRequest  # noqa: PLC0415

        req = ContentIngestRequest(
            source_id="src-meta-rt",
            title="Metadata Round-trip Doc",
            text="Metadata round-trip test content. " * 4,
            scope="global",
            metadata={"author": "tester", "priority": 1},
        )
        result = await store.ingest(req)

        doc = store.get_document(result.document_id)

        assert doc is not None
        assert doc.metadata == {"author": "tester", "priority": 1}

    # ------------------------------------------------------------------ AC1 + AC8 retry (REPLACED delete-failure)
    # Retry-safe vector deletion after post-commit REPLACED+_delete_vectors failure

    @pytest.mark.asyncio
    async def test_ingest_replaced_retry_deletes_stale_vectors_after_failed_delete(
        self, mock_embed: MagicMock
    ) -> None:
        """AC1 + AC8: retrying REPLACED ingest after _delete_vectors failure must delete stale vectors.

        When a REPLACED ingest fails at _delete_vectors after SQLite commits:
        - Old chunk rows are gone from content_chunks (deleted in the transaction)
        - Stale V1 vector IDs still exist in Qdrant (delete was never completed)

        A retry with the same V2 content must still call delete for the stale V1 chunk IDs.
        This requires the store to have persisted those IDs within the SQLite transaction —
        they cannot be reconstructed from content_chunks at retry time (already replaced).

        Convergence observable (AC1): no stale vector IDs remain in Qdrant AND all current
        chunk IDs have vectors upserted after retry.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)

        # Step 1: V1 ingest — CREATED (V1 chunk IDs live in Qdrant)
        store_1 = ContentStore(
            db=db,
            vector_store=MagicMock(),
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        store_1.ensure_tables()
        v1_result = await store_1.ingest(
            _make_request(text="First version content here. " * 6)
        )
        v1_chunk_ids = set(v1_result.chunk_ids)

        # Step 2: V2 ingest — REPLACED, SQLite commits new chunks, but _delete_vectors raises
        failing_vectors = MagicMock()
        failing_vectors.delete = MagicMock(side_effect=RuntimeError("Qdrant delete failed"))
        store_2 = ContentStore(
            db=db,
            vector_store=failing_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        with pytest.raises(RuntimeError):
            await store_2.ingest(
                _make_request(text="Second version — completely different content. " * 6)
            )

        # Step 3: Retry V2 — Qdrant back online; same V2 content
        retry_vectors = MagicMock()
        store_3 = ContentStore(
            db=db,
            vector_store=retry_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        await store_3.ingest(
            _make_request(text="Second version — completely different content. " * 6)
        )

        # Retry MUST call delete for the stale V1 chunk IDs.
        # V1 chunk rows were deleted from content_chunks during the REPLACED transaction;
        # the only way the retry can know what to delete is if those IDs were persisted
        # in SQLite (e.g. a pending_delete_chunk_ids column on content_documents).
        delete_calls = [c for c in retry_vectors.method_calls if "delete" in c[0]]
        assert delete_calls, (
            "AC8 + AC1: retry after REPLACED+delete-failure must call delete for stale V1 "
            "vectors. Pending-delete chunk IDs must be persisted in SQLite — V1 chunk rows "
            "are gone from content_chunks after the REPLACED transaction."
        )
        deleted_ids: set[str] = set()
        for call in delete_calls:
            ids = call[2].get("ids") if call[2] else (call[1][0] if call[1] else [])
            if isinstance(ids, (list, tuple)):
                deleted_ids.update(str(i) for i in ids)
        assert v1_chunk_ids <= deleted_ids, (
            f"AC1 convergence: all stale V1 chunk IDs must be deleted on retry. "
            f"Missing from delete calls: {v1_chunk_ids - deleted_ids}"
        )

    @pytest.mark.asyncio
    async def test_ingest_replaced_retry_convergence_delete_before_upsert(
        self, mock_embed: MagicMock
    ) -> None:
        """AC1 + AC3 + AC8: UNCHANGED retry after REPLACED+delete-failure deletes before upserting.

        Refined AC3: UNCHANGED performs no new SQLite row writes but completes any pending
        vector repairs (stale deletion + current upsert) from a prior failed attempt.

        Both operations must occur during the retry and in the correct order:
        delete stale vectors → upsert current vectors.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)

        # V1 CREATED
        store_1 = ContentStore(
            db=db,
            vector_store=MagicMock(),
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        store_1.ensure_tables()
        await store_1.ingest(_make_request(text="Version one content here. " * 6))

        # V2 REPLACED — _delete_vectors fails
        failing_vectors = MagicMock()
        failing_vectors.delete = MagicMock(side_effect=RuntimeError("delete unavailable"))
        store_2 = ContentStore(
            db=db,
            vector_store=failing_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        with pytest.raises(RuntimeError):
            await store_2.ingest(_make_request(text="Version two content — updated here. " * 6))

        # Retry V2 — Qdrant healthy
        retry_vectors = MagicMock()
        store_3 = ContentStore(
            db=db,
            vector_store=retry_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        await store_3.ingest(_make_request(text="Version two content — updated here. " * 6))

        method_names = [c[0] for c in retry_vectors.method_calls]
        delete_positions = [i for i, n in enumerate(method_names) if "delete" in n]
        upsert_positions = [i for i, n in enumerate(method_names) if "upsert" in n or "upload" in n]

        assert delete_positions, (
            "AC3 (refined): UNCHANGED retry after REPLACED+delete-failure must delete stale "
            "vectors — both stale deletion and current upsert are required to converge"
        )
        assert upsert_positions, (
            "AC3 (refined): UNCHANGED retry after REPLACED+delete-failure must upsert current vectors"
        )
        assert min(delete_positions) < min(upsert_positions), (
            "AC8: stale vector deletion must precede current vector upsert in the repair path"
        )

    # ------------------------------------------------------------------ AC1 + AC8 payload (cycle 4)
    # Exact upsert payload verification — no bare vector-store callable

    @pytest.mark.asyncio
    async def test_ingest_created_upserts_exact_chunk_ids_no_bare_call(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC8: CREATED ingest must call vector_store.upsert(points=...) with exact chunk IDs.

        The implementation must NOT invoke vector_store as a bare callable (mock_vectors()).
        Only the .upsert(points=...) method call is a valid vector-write signal; a bare ()
        call is dead code that does not reach any production Qdrant path.
        """
        req = _make_request()
        result = await store.ingest(req)

        # No bare parity call — vector_store() is dead code that masks weak assertions
        assert mock_vectors.call_count == 0, (
            "AC8: vector_store must not be invoked as a bare callable — "
            "only vector_store.upsert(points=...) must be called on CREATED ingest"
        )
        # Exact payload
        upsert_call = mock_vectors.upsert.call_args
        assert upsert_call is not None, "AC8: upsert must be called on CREATED ingest"
        upserted_ids = {p["id"] for p in upsert_call.kwargs["points"]}
        assert upserted_ids == set(result.chunk_ids), (
            f"AC8: upsert payload must contain exactly the current chunk IDs. "
            f"Expected {set(result.chunk_ids)}, got {upserted_ids}"
        )

    @pytest.mark.asyncio
    async def test_ingest_replaced_upserts_exact_new_chunk_ids_no_bare_call(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC8: REPLACED ingest must upsert exactly the new chunk IDs with no bare call.

        Companion to test_ingest_replaced_deletes_old_vectors_before_upsert — adds
        payload verification. The bare vector_store() parity call is dead code.
        """
        req1 = _make_request(text="First version content. " * 6)
        await store.ingest(req1)
        mock_vectors.reset_mock()

        req2 = _make_request(text="Second version — fully updated. " * 6)
        result2 = await store.ingest(req2)

        # No bare parity call after reset
        assert mock_vectors.call_count == 0, (
            "AC8: vector_store must not be invoked as a bare callable on REPLACED ingest"
        )
        # Exact payload — only new (V2) chunk IDs must be upserted
        upsert_calls = [c for c in mock_vectors.method_calls if "upsert" in c[0]]
        assert upsert_calls, "AC8: at least one upsert call required on REPLACED ingest"
        upserted_ids: set[str] = set()
        for call in upsert_calls:
            upserted_ids.update(p["id"] for p in call.kwargs.get("points", []))
        assert upserted_ids == set(result2.chunk_ids), (
            f"AC8: upsert payload must contain exactly the new chunk IDs. "
            f"Expected {set(result2.chunk_ids)}, got {upserted_ids}"
        )

    @pytest.mark.asyncio
    async def test_ingest_retry_after_failure_upserts_exact_chunk_ids_no_bare_call(
        self, mock_embed: MagicMock
    ) -> None:
        """AC1 + AC8: retry after post-commit Qdrant failure upserts exact current chunk IDs.

        Companion to test_ingest_retry_after_qdrant_failure_writes_vectors — adds payload
        verification and checks that no bare vector_store() call occurs.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)
        req = _make_request()

        # Step 1: first ingest — SQLite commits, Qdrant fails
        failing_vectors = MagicMock()
        failing_vectors.upsert = MagicMock(side_effect=RuntimeError("qdrant down"))
        s = ContentStore(
            db=db, vector_store=failing_vectors, embedding_provider=mock_embed, chunker=chunker
        )
        s.ensure_tables()
        with pytest.raises(RuntimeError):
            await s.ingest(req)

        # Step 2: retry with healthy Qdrant
        retry_vectors = MagicMock()
        s2 = ContentStore(
            db=db, vector_store=retry_vectors, embedding_provider=mock_embed, chunker=chunker
        )
        retry_result = await s2.ingest(req)

        # No bare parity call
        assert retry_vectors.call_count == 0, (
            "AC8: vector_store must not be invoked as a bare callable on retry ingest"
        )
        # Exact payload — must upsert exactly the current persisted chunk IDs
        upsert_call = retry_vectors.upsert.call_args
        assert upsert_call is not None, "AC1 + AC8: upsert must be called on retry"
        upserted_ids = {p["id"] for p in upsert_call.kwargs["points"]}
        assert upserted_ids == set(retry_result.chunk_ids), (
            f"AC1 + AC8: retry upsert payload must contain exactly the current chunk IDs. "
            f"Expected {set(retry_result.chunk_ids)}, got {upserted_ids}"
        )

    @pytest.mark.asyncio
    async def test_ingest_replaced_retry_delete_failure_upserts_exact_v2_ids_no_bare_call(
        self, mock_embed: MagicMock
    ) -> None:
        """AC1 + AC8: REPLACED retry after delete failure upserts exactly the V2 chunk IDs.

        Companion to test_ingest_replaced_retry_deletes_stale_vectors_after_failed_delete —
        adds payload verification and no-bare-call guard.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)

        # V1 CREATED
        store_1 = ContentStore(
            db=db, vector_store=MagicMock(), embedding_provider=mock_embed, chunker=chunker
        )
        store_1.ensure_tables()
        await store_1.ingest(_make_request(text="V1 content paragraph here. " * 6))

        # V2 REPLACED — _delete_vectors raises
        failing_vectors = MagicMock()
        failing_vectors.delete = MagicMock(side_effect=RuntimeError("Qdrant delete failed"))
        store_2 = ContentStore(
            db=db, vector_store=failing_vectors, embedding_provider=mock_embed, chunker=chunker
        )
        with pytest.raises(RuntimeError):
            await store_2.ingest(_make_request(text="V2 updated content paragraph here. " * 6))

        # Retry V2
        retry_vectors = MagicMock()
        store_3 = ContentStore(
            db=db, vector_store=retry_vectors, embedding_provider=mock_embed, chunker=chunker
        )
        retry_result = await store_3.ingest(
            _make_request(text="V2 updated content paragraph here. " * 6)
        )

        # No bare parity call
        assert retry_vectors.call_count == 0, (
            "AC8: vector_store must not be invoked as a bare callable on REPLACED retry"
        )
        # Exact payload — must upsert exactly the current V2 chunk IDs
        upsert_calls = [c for c in retry_vectors.method_calls if "upsert" in c[0]]
        assert upsert_calls, "AC1 + AC8: upsert must be called on REPLACED retry"
        upserted_ids: set[str] = set()
        for call in upsert_calls:
            upserted_ids.update(p["id"] for p in call.kwargs.get("points", []))
        assert upserted_ids == set(retry_result.chunk_ids), (
            f"AC1 + AC8: REPLACED retry upsert payload must contain exactly the V2 chunk IDs. "
            f"Expected {set(retry_result.chunk_ids)}, got {upserted_ids}"
        )

    @pytest.mark.asyncio
    async def test_ingest_replaced_retry_convergence_exact_ids_no_bare_call(
        self, mock_embed: MagicMock
    ) -> None:
        """AC1 + AC3 + AC8: REPLACED retry convergence — delete-before-upsert AND exact V2 payload.

        Companion to test_ingest_replaced_retry_convergence_delete_before_upsert — adds
        exact payload verification and no-bare-call guard. The convergence contract requires:
        (1) stale V1 vectors deleted, (2) exact V2 chunk IDs upserted, (3) delete before upsert,
        (4) no bare vector_store() call.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)

        # V1 CREATED
        store_1 = ContentStore(
            db=db, vector_store=MagicMock(), embedding_provider=mock_embed, chunker=chunker
        )
        store_1.ensure_tables()
        await store_1.ingest(_make_request(text="Version one content here. " * 6))

        # V2 REPLACED — _delete_vectors fails
        failing_vectors = MagicMock()
        failing_vectors.delete = MagicMock(side_effect=RuntimeError("delete unavailable"))
        store_2 = ContentStore(
            db=db, vector_store=failing_vectors, embedding_provider=mock_embed, chunker=chunker
        )
        with pytest.raises(RuntimeError):
            await store_2.ingest(_make_request(text="Version two content — updated. " * 6))

        # Retry V2 — Qdrant healthy
        retry_vectors = MagicMock()
        store_3 = ContentStore(
            db=db, vector_store=retry_vectors, embedding_provider=mock_embed, chunker=chunker
        )
        retry_result = await store_3.ingest(
            _make_request(text="Version two content — updated. " * 6)
        )

        # (1) No bare parity call
        assert retry_vectors.call_count == 0, (
            "AC8: vector_store must not be invoked as a bare callable — dead code must be removed"
        )
        method_names = [c[0] for c in retry_vectors.method_calls]
        delete_positions = [i for i, n in enumerate(method_names) if "delete" in n]
        upsert_positions = [i for i, n in enumerate(method_names) if "upsert" in n or "upload" in n]
        # (2) Delete before upsert
        assert delete_positions, "AC8: stale delete must occur in convergence retry"
        assert upsert_positions, "AC8: current upsert must occur in convergence retry"
        assert min(delete_positions) < min(upsert_positions), (
            "AC8: stale vector deletion must precede upsert in convergence retry"
        )
        # (3) Exact payload
        upsert_calls = [c for c in retry_vectors.method_calls if "upsert" in c[0]]
        upserted_ids: set[str] = set()
        for call in upsert_calls:
            upserted_ids.update(p["id"] for p in call.kwargs.get("points", []))
        assert upserted_ids == set(retry_result.chunk_ids), (
            f"AC1 + AC8: convergence retry upsert payload must equal V2 chunk IDs. "
            f"Expected {set(retry_result.chunk_ids)}, got {upserted_ids}"
        )

    # ------------------------------------------------------------------ AC8 delete-payload (cycle 5)
    # Exact delete-payload verification — happy-path REPLACED

    @pytest.mark.asyncio
    async def test_ingest_replaced_deletes_exact_stale_chunk_ids(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC8: happy-path REPLACED delete must pass exactly the stale V1 chunk IDs.

        The existing ordering test proves delete precedes upsert but never inspects the
        delete(ids=...) payload. A wrong-ID delete on the normal REPLACED path immediately
        clears recovery state (pending_delete_chunk_ids cleared on success), so stale
        vectors become permanently orphaned with no retry path.

        Observable: set(delete_call.kwargs["ids"]) == set(result1.chunk_ids)
        """
        req1 = _make_request(text="First stable version content here. " * 6)
        result1 = await store.ingest(req1)
        v1_chunk_ids = set(result1.chunk_ids)
        mock_vectors.reset_mock()

        req2 = _make_request(text="Second version — fully replaced content here. " * 6)
        await store.ingest(req2)

        delete_call = mock_vectors.delete.call_args
        assert delete_call is not None, (
            "AC8: REPLACED ingest must call vector_store.delete — "
            "stale V1 vectors must be removed"
        )
        deleted_ids = set(delete_call.kwargs["ids"])
        assert deleted_ids == v1_chunk_ids, (
            f"AC8: delete must receive exactly the stale V1 chunk IDs. "
            f"Expected {v1_chunk_ids}, got {deleted_ids}"
        )
