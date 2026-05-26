"""Tests for ContentStore — search, purge_source, stats (task #1872).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/content.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/content.py

AC coverage:
  AC1 — search returns ContentSearchResult tuples ordered by descending score;
         scores clamped to [0.0, 1.0]; count ≤ top_k; min_score filter applied;
         scopes and source_ids filters applied (D53)
  AC2 — search() raises ValueError when query.text is empty
  AC3 — purge_source removes documents, chunks, and Qdrant vectors; returns
         ContentPurgeResult with document_ids, chunk_ids, vector_ids tuples
  AC4 — stats() returns ContentStats with documents, chunks, and vectors counts
         (vectors = chunks whose parent document has vectors_synced=1)
  AC5 — purge is idempotent — unknown source_id returns empty tuples, no error
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.protocols.content import (
    ContentIngestRequest,
    ContentPurgeResult,
    ContentSearchQuery,
    ContentStats,
)
from owlbear_knowledge.stores.content import ContentStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LONG_TEXT = "The quick brown fox jumps over the lazy dog. " * 15


def _make_request(
    *,
    source_id: str = "src-1",
    title: str = "Test Doc",
    text: str = _LONG_TEXT,
    scope: str = "global",
) -> ContentIngestRequest:
    return ContentIngestRequest(
        source_id=source_id,
        title=title,
        text=text,
        scope=scope,
    )


def _make_query(
    *,
    text: str = "quick brown fox",
    top_k: int = 10,
    min_score: float = 0.0,
    scopes: tuple[str, ...] = (),
    source_ids: tuple[str, ...] = (),
) -> ContentSearchQuery:
    return ContentSearchQuery(
        text=text,
        top_k=top_k,
        min_score=min_score,
        scopes=scopes,
        source_ids=source_ids,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_vectors() -> MagicMock:
    """Mocked vector store — never touches real Qdrant."""
    m = MagicMock(name="vector_store")
    m.search_similar.return_value = []
    return m


@pytest.fixture()
def mock_embed() -> MagicMock:
    """Mocked embedding provider returning plausible fake dense vectors."""
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
# TestFromAC_ContentStoreSearch  (AC1, AC2)
# ---------------------------------------------------------------------------


class TestFromAC_ContentStoreSearch:
    """AC-derived tests for ContentStore.search() — AC1 and AC2."""

    # ------------------------------------------------------------------ AC2
    # Error: ValueError on empty / whitespace-only text

    @pytest.mark.asyncio
    async def test_search_raises_value_error_on_empty_text(
        self, store: ContentStore
    ) -> None:
        """AC2: empty query.text raises ValueError."""
        with pytest.raises(ValueError):
            await store.search(_make_query(text=""))

    @pytest.mark.asyncio
    async def test_search_raises_value_error_on_whitespace_only_text(
        self, store: ContentStore
    ) -> None:
        """AC2: whitespace-only query.text raises ValueError."""
        with pytest.raises(ValueError):
            await store.search(_make_query(text="   "))

    # ------------------------------------------------------------------ AC1
    # Happy: return type and basic contract

    @pytest.mark.asyncio
    async def test_search_returns_tuple(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: search returns a tuple (not list or generator)."""
        req = _make_request()
        result = await store.ingest(req)
        mock_vectors.search_similar.return_value = [(result.chunk_ids[0], 0.8)]

        results = await store.search(_make_query())
        assert isinstance(results, tuple)

    @pytest.mark.asyncio
    async def test_search_empty_vector_results_returns_empty_tuple(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: when vector_store returns no hits, search returns ()."""
        mock_vectors.search_similar.return_value = []
        results = await store.search(_make_query())
        assert results == ()

    # ------------------------------------------------------------------ AC1
    # Happy: ordering by descending score

    @pytest.mark.asyncio
    async def test_search_results_ordered_by_descending_score(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: results are ordered highest score first."""
        req = _make_request()
        result = await store.ingest(req)
        chunk_ids = list(result.chunk_ids)
        # Return chunks with non-monotone raw scores to test sorting
        pairs = [(cid, 0.3 + (len(chunk_ids) - i) * 0.1) for i, cid in enumerate(chunk_ids)]
        mock_vectors.search_similar.return_value = pairs

        results = await store.search(_make_query(top_k=100))
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    # ------------------------------------------------------------------ AC1
    # Boundary: top_k cap

    @pytest.mark.asyncio
    async def test_search_result_count_does_not_exceed_top_k(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: len(results) ≤ query.top_k even when vector_store returns more."""
        req = _make_request()
        result = await store.ingest(req)
        chunk_ids = list(result.chunk_ids)
        # Feed more hits than top_k=2
        mock_vectors.search_similar.return_value = [
            (cid, 0.9 - i * 0.05) for i, cid in enumerate(chunk_ids)
        ]

        results = await store.search(_make_query(top_k=2))
        assert len(results) <= 2

    # ------------------------------------------------------------------ AC1
    # Boundary: min_score filter

    @pytest.mark.asyncio
    async def test_search_excludes_results_below_min_score(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: results whose score < min_score are not returned."""
        req = _make_request()
        result = await store.ingest(req)
        chunk_ids = list(result.chunk_ids)
        # First chunk above threshold, rest below
        mock_vectors.search_similar.return_value = [
            (chunk_ids[0], 0.8),
        ] + [(cid, 0.2) for cid in chunk_ids[1:]]

        results = await store.search(_make_query(min_score=0.5))
        for r in results:
            assert r.score >= 0.5

    @pytest.mark.asyncio
    async def test_search_includes_result_at_exact_min_score_boundary(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: a result whose score == min_score is included (inclusive boundary)."""
        req = _make_request()
        result = await store.ingest(req)
        mock_vectors.search_similar.return_value = [(result.chunk_ids[0], 0.5)]

        results = await store.search(_make_query(min_score=0.5))
        assert len(results) >= 1

    # ------------------------------------------------------------------ AC1
    # Boundary: score clamping

    @pytest.mark.asyncio
    async def test_search_clamps_score_above_one_to_one(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: score > 1.0 from vector_store is clamped to 1.0."""
        req = _make_request()
        result = await store.ingest(req)
        mock_vectors.search_similar.return_value = [(result.chunk_ids[0], 1.5)]

        results = await store.search(_make_query())
        assert len(results) == 1
        assert results[0].score <= 1.0

    @pytest.mark.asyncio
    async def test_search_clamps_negative_score_to_zero(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: negative score from vector_store is clamped to 0.0."""
        req = _make_request()
        result = await store.ingest(req)
        mock_vectors.search_similar.return_value = [(result.chunk_ids[0], -0.3)]

        results = await store.search(_make_query())
        assert len(results) == 1
        assert results[0].score >= 0.0

    # ------------------------------------------------------------------ AC1
    # Edge: source_ids filter (D53)

    @pytest.mark.asyncio
    async def test_search_source_ids_filter_excludes_other_sources(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: source_ids filter restricts returned chunks to matching source."""
        r1 = await store.ingest(_make_request(source_id="src-A", title="Doc A"))
        r2 = await store.ingest(_make_request(source_id="src-B", title="Doc B"))
        cid_a = r1.chunk_ids[0]
        cid_b = r2.chunk_ids[0]
        # Vector store returns chunks from both sources
        mock_vectors.search_similar.return_value = [(cid_a, 0.9), (cid_b, 0.8)]

        results = await store.search(_make_query(source_ids=("src-A",)))
        assert len(results) >= 1
        for r in results:
            assert r.chunk.source_id == "src-A"

    @pytest.mark.asyncio
    async def test_search_with_no_matching_source_id_returns_empty(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: source_ids filter that matches nothing returns empty tuple."""
        r = await store.ingest(_make_request(source_id="src-1"))
        mock_vectors.search_similar.return_value = [(r.chunk_ids[0], 0.9)]

        results = await store.search(_make_query(source_ids=("src-other",)))
        assert results == ()

    # ------------------------------------------------------------------ AC1
    # Edge: scopes filter forwarded to vector store

    @pytest.mark.asyncio
    async def test_search_scopes_forwarded_to_vector_store(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: scopes from query are passed through to vector_store.search_similar."""
        mock_vectors.search_similar.return_value = []
        query = _make_query(scopes=("wiki", "docs"))
        await store.search(query)

        assert mock_vectors.search_similar.called
        call_args = mock_vectors.search_similar.call_args
        forwarded_scopes = call_args.kwargs.get("scopes")
        assert forwarded_scopes == ["wiki", "docs"]  # PO-2: exact scopes, not just non-null

    # ------------------------------------------------------------------ AC1
    # Happy: chunk text preserved in result

    @pytest.mark.asyncio
    async def test_search_result_chunk_preserves_exact_text(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC1: ContentChunk returned in result has non-empty preserved text."""
        req = _make_request()
        result = await store.ingest(req)
        chunk_id = result.chunk_ids[0]
        original_chunk = store.get_chunk(chunk_id)
        assert original_chunk is not None

        mock_vectors.search_similar.return_value = [(chunk_id, 0.9)]
        results = await store.search(_make_query())

        assert len(results) == 1
        assert results[0].chunk.text == original_chunk.text


# ---------------------------------------------------------------------------
# TestFromAC_ContentStorePurge  (AC3, AC5)
# ---------------------------------------------------------------------------


class TestFromAC_ContentStorePurge:
    """AC-derived tests for ContentStore.purge_source() — AC3 and AC5."""

    # ------------------------------------------------------------------ AC5
    # Edge/Error: idempotent for unknown source

    def test_purge_unknown_source_does_not_raise(self, store: ContentStore) -> None:
        """AC5: purge_source on an unknown source_id completes without error."""
        result = store.purge_source("nonexistent-source")
        assert result is not None

    def test_purge_unknown_source_returns_empty_document_ids(
        self, store: ContentStore
    ) -> None:
        """AC5: document_ids tuple is empty for unknown source."""
        result = store.purge_source("nonexistent-source")
        assert result.document_ids == ()

    def test_purge_unknown_source_returns_empty_chunk_ids(
        self, store: ContentStore
    ) -> None:
        """AC5: chunk_ids tuple is empty for unknown source."""
        result = store.purge_source("nonexistent-source")
        assert result.chunk_ids == ()

    def test_purge_unknown_source_returns_empty_vector_ids(
        self, store: ContentStore
    ) -> None:
        """AC5: vector_ids tuple is empty for unknown source."""
        result = store.purge_source("nonexistent-source")
        assert result.vector_ids == ()

    # ------------------------------------------------------------------ AC3
    # Happy: purge returns ContentPurgeResult

    @pytest.mark.asyncio
    async def test_purge_source_returns_content_purge_result_type(
        self, store: ContentStore
    ) -> None:
        """AC3: purge_source returns a ContentPurgeResult."""
        await store.ingest(_make_request(source_id="src-purge"))
        result = store.purge_source("src-purge")
        assert isinstance(result, ContentPurgeResult)

    @pytest.mark.asyncio
    async def test_purge_source_document_ids_contains_ingested_doc(
        self, store: ContentStore
    ) -> None:
        """AC3: returned document_ids contains the document_id of the purged document."""
        r = await store.ingest(_make_request(source_id="src-purge"))
        purge = store.purge_source("src-purge")
        assert r.document_id in purge.document_ids

    @pytest.mark.asyncio
    async def test_purge_source_chunk_ids_contains_ingested_chunks(
        self, store: ContentStore
    ) -> None:
        """AC3: returned chunk_ids contains all chunk IDs of the purged document."""
        r = await store.ingest(_make_request(source_id="src-purge"))
        purge = store.purge_source("src-purge")
        assert set(r.chunk_ids).issubset(set(purge.chunk_ids))

    @pytest.mark.asyncio
    async def test_purge_source_vector_ids_match_chunk_ids(
        self, store: ContentStore
    ) -> None:
        """AC3: vector_ids equals chunk_ids (1:1 mapping between chunks and vectors)."""
        await store.ingest(_make_request(source_id="src-purge"))
        purge = store.purge_source("src-purge")
        assert set(purge.vector_ids) == set(purge.chunk_ids)

    @pytest.mark.asyncio
    async def test_purge_source_removes_document_from_store(
        self, store: ContentStore
    ) -> None:
        """AC3: document is no longer retrievable via get_document after purge."""
        r = await store.ingest(_make_request(source_id="src-purge"))
        store.purge_source("src-purge")
        assert store.get_document(r.document_id) is None

    @pytest.mark.asyncio
    async def test_purge_source_removes_chunks_from_store(
        self, store: ContentStore
    ) -> None:
        """AC3: all chunks are no longer retrievable via get_chunk after purge."""
        r = await store.ingest(_make_request(source_id="src-purge"))
        chunk_ids = r.chunk_ids
        store.purge_source("src-purge")
        for cid in chunk_ids:
            assert store.get_chunk(cid) is None

    @pytest.mark.asyncio
    async def test_purge_source_deletes_vectors_from_vector_store(
        self, store: ContentStore, mock_vectors: MagicMock
    ) -> None:
        """AC3: vector_store.delete is called for the purged chunk IDs."""
        await store.ingest(_make_request(source_id="src-purge"))
        mock_vectors.delete.reset_mock()
        store.purge_source("src-purge")
        mock_vectors.delete.assert_called()

    @pytest.mark.asyncio
    async def test_purge_only_removes_target_source_not_others(
        self, store: ContentStore
    ) -> None:
        """AC3: purging one source_id does not remove documents from other sources."""
        await store.ingest(_make_request(source_id="src-1", title="Doc 1"))
        r2 = await store.ingest(_make_request(source_id="src-2", title="Doc 2"))
        store.purge_source("src-1")
        # src-2 document must still exist
        assert store.get_document(r2.document_id) is not None

    # ------------------------------------------------------------------ AC5
    # Edge: idempotent — second purge returns empty tuples

    @pytest.mark.asyncio
    async def test_purge_second_call_returns_empty_tuples(
        self, store: ContentStore
    ) -> None:
        """AC5: second purge_source on already-purged source returns empty tuples."""
        await store.ingest(_make_request(source_id="src-purge"))
        store.purge_source("src-purge")
        second = store.purge_source("src-purge")
        assert second.document_ids == ()
        assert second.chunk_ids == ()
        assert second.vector_ids == ()

    # ------------------------------------------------------------------ AC3 PO-1
    # Regression: purge deletes stale vector IDs from REPLACED+delete-failure state

    @pytest.mark.asyncio
    async def test_purge_source_includes_stale_pending_vector_ids(
        self, mock_embed: MagicMock
    ) -> None:
        """AC3 PO-1: purge_source deletes stale V1 vector IDs persisted after REPLACED+delete-failure.

        Scenario:
        1. V1 ingest creates chunk IDs (now in Qdrant).
        2. V2 REPLACED ingest: SQLite commits V2 chunks but _delete_vectors raises →
           pending_delete_chunk_ids column retains V1 IDs, vectors_synced=0.
        3. purge_source must delete BOTH V1 (stale, from pending_delete_chunk_ids)
           and V2 (current) IDs; purge_result.vector_ids must include both sets.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)

        # Step 1: V1 ingest
        store_1 = ContentStore(
            db=db,
            vector_store=MagicMock(),
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        store_1.ensure_tables()
        v1_result = await store_1.ingest(
            _make_request(source_id="src-stale", text="First version content here. " * 6)
        )
        v1_chunk_ids = set(v1_result.chunk_ids)

        # Step 2: V2 REPLACED — SQLite commits, _delete_vectors raises
        failing_vectors = MagicMock()
        failing_vectors.delete = MagicMock(side_effect=RuntimeError("Qdrant offline"))
        store_2 = ContentStore(
            db=db,
            vector_store=failing_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        with pytest.raises(RuntimeError):
            await store_2.ingest(
                _make_request(
                    source_id="src-stale",
                    text="Second version, completely different content. " * 6,
                )
            )

        # Capture current V2 chunk IDs that remain in SQLite after failed vector delete.
        v2_rows = db.execute(
            "SELECT id FROM content_chunks WHERE source_id = ?",
            ("src-stale",),
        ).fetchall()
        v2_chunk_ids = {str(row[0]) for row in v2_rows}
        assert len(v2_chunk_ids) > 0, "V2 chunks must exist after REPLACED ingest failure"

        # Step 3: purge_source with working vector store
        purge_vectors = MagicMock()
        store_3 = ContentStore(
            db=db,
            vector_store=purge_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        purge_result = store_3.purge_source("src-stale")

        # delete must be called
        assert purge_vectors.delete.called, (
            "purge_source must call vector_store.delete for stale+current IDs"
        )
        # Collect all IDs passed to delete
        deleted_ids: set[str] = set()
        for call in purge_vectors.delete.call_args_list:
            ids = call.kwargs.get("ids") or (call.args[0] if call.args else [])
            if isinstance(ids, (list, tuple)):
                deleted_ids.update(str(i) for i in ids)
        assert v1_chunk_ids <= deleted_ids, (
            f"delete payload must include stale V1 IDs; missing: {v1_chunk_ids - deleted_ids}"
        )
        assert v2_chunk_ids <= deleted_ids, (
            f"delete payload must include current V2 IDs; missing: {v2_chunk_ids - deleted_ids}"
        )
        # purge_result.vector_ids must include stale V1 IDs
        assert v1_chunk_ids <= set(purge_result.vector_ids), (
            f"purge_result.vector_ids must include stale V1 IDs; "
            f"missing: {v1_chunk_ids - set(purge_result.vector_ids)}"
        )
        assert v2_chunk_ids <= set(purge_result.vector_ids), (
            f"purge_result.vector_ids must include current V2 IDs; "
            f"missing: {v2_chunk_ids - set(purge_result.vector_ids)}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ContentStoreStats  (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_ContentStoreStats:
    """AC-derived tests for ContentStore.stats() — AC4."""

    # Happy: empty store baseline

    def test_stats_returns_content_stats_type(self, store: ContentStore) -> None:
        """AC4: stats() returns a ContentStats instance."""
        s = store.stats()
        assert isinstance(s, ContentStats)

    def test_stats_empty_store_has_zero_documents(self, store: ContentStore) -> None:
        """AC4: empty store → documents == 0."""
        assert store.stats().documents == 0

    def test_stats_empty_store_has_zero_chunks(self, store: ContentStore) -> None:
        """AC4: empty store → chunks == 0."""
        assert store.stats().chunks == 0

    def test_stats_empty_store_has_zero_vectors(self, store: ContentStore) -> None:
        """AC4: empty store → vectors == 0."""
        assert store.stats().vectors == 0

    # Happy: after ingest

    @pytest.mark.asyncio
    async def test_stats_document_count_increments_after_ingest(
        self, store: ContentStore
    ) -> None:
        """AC4: documents count equals number of ingested documents."""
        await store.ingest(_make_request(source_id="src-1", title="Doc 1"))
        await store.ingest(_make_request(source_id="src-2", title="Doc 2"))
        assert store.stats().documents == 2

    @pytest.mark.asyncio
    async def test_stats_chunk_count_matches_ingested_chunks(
        self, store: ContentStore
    ) -> None:
        """AC4: chunks count equals total chunks across all documents."""
        r = await store.ingest(_make_request())
        assert store.stats().chunks == len(r.chunk_ids)

    @pytest.mark.asyncio
    async def test_stats_vectors_equals_chunks_when_all_synced(
        self, store: ContentStore
    ) -> None:
        """AC4: vectors = chunk count when all parent documents have vectors_synced=1."""
        r = await store.ingest(_make_request())
        s = store.stats()
        assert s.vectors == len(r.chunk_ids)

    # Boundary: after purge

    @pytest.mark.asyncio
    async def test_stats_document_count_decrements_after_purge(
        self, store: ContentStore
    ) -> None:
        """AC4: documents count decreases after purge_source."""
        await store.ingest(_make_request(source_id="src-1", title="Doc 1"))
        await store.ingest(_make_request(source_id="src-2", title="Doc 2"))
        store.purge_source("src-1")
        assert store.stats().documents == 1

    @pytest.mark.asyncio
    async def test_stats_chunk_count_decrements_after_purge(
        self, store: ContentStore
    ) -> None:
        """AC4: chunks count decreases after purge_source."""
        await store.ingest(_make_request(source_id="src-1", title="Doc 1"))
        r2 = await store.ingest(_make_request(source_id="src-2", title="Doc 2"))
        store.purge_source("src-1")
        s = store.stats()
        assert s.chunks == len(r2.chunk_ids)

    @pytest.mark.asyncio
    async def test_stats_vectors_count_decrements_after_purge(
        self, store: ContentStore
    ) -> None:
        """AC4: vectors count decreases after purge_source."""
        await store.ingest(_make_request(source_id="src-1", title="Doc 1"))
        r2 = await store.ingest(_make_request(source_id="src-2", title="Doc 2"))
        store.purge_source("src-1")
        s = store.stats()
        assert s.vectors == len(r2.chunk_ids)

    # ------------------------------------------------------------------ AC4 PO-3
    # Boundary: stats().vectors excludes chunks of unsynced parent documents

    @pytest.mark.asyncio
    async def test_stats_vectors_excludes_chunks_with_unsynced_parent(
        self, mock_embed: MagicMock, mock_vectors: MagicMock
    ) -> None:
        """AC4 PO-3: stats().vectors is 0 when all parent documents have vectors_synced=0.

        The vectors count uses a JOIN predicate (WHERE d.vectors_synced = 1). This test
        directly exercises that predicate by forcing vectors_synced=0 and verifying that
        existing chunks are excluded from the vectors count.
        """
        db = sqlite3.connect(":memory:")
        chunker = TextChunker(target_tokens=50)
        s = ContentStore(
            db=db,
            vector_store=mock_vectors,
            embedding_provider=mock_embed,
            chunker=chunker,
        )
        s.ensure_tables()

        # Ingest doc 1 — vectors_synced=1 by default after successful ingest
        r1 = await s.ingest(_make_request(source_id="src-1", title="Doc 1"))
        assert s.stats().vectors == len(r1.chunk_ids)  # baseline: synced

        # Directly set vectors_synced=0 to simulate the unsynced state
        db.execute(
            "UPDATE content_documents SET vectors_synced = 0 WHERE document_id = ?",
            (r1.document_id,),
        )
        db.commit()

        # Chunks still exist, but parent is unsynced — vectors must be 0
        assert s.stats().chunks == len(r1.chunk_ids)
        assert s.stats().vectors == 0, (
            "stats().vectors must exclude chunks whose parent document has vectors_synced=0"
        )

        # Ingest a second doc (synced) — only its chunks count toward vectors
        r2 = await s.ingest(_make_request(source_id="src-2", title="Doc 2"))
        assert s.stats().vectors == len(r2.chunk_ids)
