"""Tests for IngestCoordinator — ingest & refresh (task #1877).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/ingest.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py

AC coverage:
  AC1  — ingest validates source_id; delegates to Content.ingest; catches per-doc errors
  AC2  — CREATED + enrich=True → enqueue_chunks; CREATED + enrich=False → no enqueue
  AC3  — REPLACED: discard_chunks + invalidate_evidence + enqueue if enrich=True
  AC4  — Per-document guarantee: if Content.ingest succeeds, enqueue/discard always called; errors captured
  AC5  — IngestResult fields: documents_processed, created/replaced/unchanged, content_results, timestamps
  AC6  — Source health updated: OK / DEGRADED / FAILED + message
  AC7  — stats() aggregates from all 4 stores; never raises
  AC8  — refresh() with no fetcher returns empty RefreshResult (guard for #1886 behavioral contract)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.protocols.content import (
    ContentIngestResult,
    ContentIngestState,
    ContentStats,
)
from owlbear_knowledge.protocols.enrichment import (
    EnrichmentDiscardResult,
    EnrichmentStats,
)
from owlbear_knowledge.protocols.graph import EvidenceInvalidationResult, GraphStats
from owlbear_knowledge.protocols.ingest import (
    IngestDocument,
    IngestRequest,
    IngestStats,
    RefreshRequest,
    RefreshResult,
)
from owlbear_knowledge.protocols.sources import (
    ConfiguredSourceRecord,
    FetchTransport,
    InlineConfig,
    SourceHealth,
    SourceHealthReport,
    SourceKind,
    SourceState,
    SourceStats,
)
from owlbear_knowledge.ingest_coordinator import IngestCoordinator  # greenfield — ImportError expected


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(
    source_id: str = "src-1",
    *,
    enrich: bool = True,
    docs: int = 1,
) -> IngestRequest:
    return IngestRequest(
        source_id=source_id,
        documents=tuple(
            IngestDocument(title=f"Doc {i}", text=f"Text content for document {i}.")
            for i in range(docs)
        ),
        enrich=enrich,
    )


def _make_content_result(
    *,
    source_id: str = "src-1",
    state: ContentIngestState = ContentIngestState.CREATED,
    chunk_ids: tuple[str, ...] = ("chunk-1",),
    replaced_chunk_ids: tuple[str, ...] = (),
) -> ContentIngestResult:
    return ContentIngestResult(
        document_id="doc-1",
        source_id=source_id,
        state=state,
        content_hash="abc123",
        chunk_ids=chunk_ids,
        replaced_chunk_ids=replaced_chunk_ids,
        created_at=datetime.now(tz=UTC),
    )


def _make_source_record(source_id: str = "src-1") -> ConfiguredSourceRecord:
    return ConfiguredSourceRecord(
        id=source_id,
        name="Test Source",
        state=SourceState.ACTIVE,
        kind=SourceKind.INLINE,
        fetch_method=FetchTransport.NONE,
        config=InlineConfig(),
        health=SourceHealth.UNKNOWN,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )


def _extract_health_report(mock_sources: MagicMock) -> SourceHealthReport:
    """Extract the SourceHealthReport from a record_health mock call."""
    call = mock_sources.record_health.call_args
    assert call is not None, "record_health was not called"
    # Called as record_health(source_id, report) or record_health(source_id, report=report)
    if len(call.args) > 1:
        return call.args[1]
    return call.kwargs["report"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_sources() -> MagicMock:
    s = MagicMock(name="sources")
    s.get_source.return_value = _make_source_record()
    s.record_health.return_value = _make_source_record()
    s.stats.return_value = SourceStats(total=5, active=3, inactive=1, wished=1)
    return s


@pytest.fixture()
def mock_content() -> MagicMock:
    c = MagicMock(name="content")
    c.ingest = AsyncMock(return_value=_make_content_result())
    c.stats.return_value = ContentStats(documents=10, chunks=50, vectors=50)
    return c


@pytest.fixture()
def mock_enrichment() -> MagicMock:
    e = MagicMock(name="enrichment")
    e.enqueue_chunks.return_value = 1
    e.discard_chunks.return_value = EnrichmentDiscardResult(
        discarded_chunk_ids=("chunk-old",), queue_items_removed=1
    )
    e.stats.return_value = EnrichmentStats(pending=7)
    return e


@pytest.fixture()
def mock_graph() -> MagicMock:
    g = MagicMock(name="graph")
    g.invalidate_evidence_by_chunks.return_value = EvidenceInvalidationResult()
    g.stats.return_value = GraphStats(entities=20, edges=15)
    return g


@pytest.fixture()
def coordinator(
    mock_sources: MagicMock,
    mock_content: MagicMock,
    mock_enrichment: MagicMock,
    mock_graph: MagicMock,
) -> IngestCoordinator:
    return IngestCoordinator(
        sources=mock_sources,
        content=mock_content,
        enrichment=mock_enrichment,
        graph=mock_graph,
    )


# ---------------------------------------------------------------------------
# TestFromAC_IngestCoordinator
# ---------------------------------------------------------------------------


class TestFromAC_IngestCoordinator:

    # ------------------------------------------------------------------
    # AC1 — source_id validation + per-doc delegation + per-doc error handling
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ingest_raises_lookup_error_when_source_not_found(
        self, coordinator: IngestCoordinator, mock_sources: MagicMock
    ) -> None:
        mock_sources.get_source.return_value = None
        with pytest.raises(LookupError):
            await coordinator.ingest(_make_request())

    @pytest.mark.asyncio
    async def test_ingest_calls_get_source_with_correct_source_id(
        self, coordinator: IngestCoordinator, mock_sources: MagicMock
    ) -> None:
        await coordinator.ingest(_make_request(source_id="src-abc"))
        mock_sources.get_source.assert_called_once_with("src-abc")

    @pytest.mark.asyncio
    async def test_ingest_calls_content_ingest_once_per_document(
        self, coordinator: IngestCoordinator, mock_content: MagicMock
    ) -> None:
        await coordinator.ingest(_make_request(docs=3))
        assert mock_content.ingest.call_count == 3

    @pytest.mark.asyncio
    async def test_ingest_continues_batch_when_content_ingest_raises(
        self, coordinator: IngestCoordinator, mock_content: MagicMock
    ) -> None:
        mock_content.ingest = AsyncMock(
            side_effect=[RuntimeError("store failure"), _make_content_result()]
        )
        result = await coordinator.ingest(_make_request(docs=2))
        assert result.documents_processed == 2

    @pytest.mark.asyncio
    async def test_ingest_failed_document_increments_processed_not_created(
        self, coordinator: IngestCoordinator, mock_content: MagicMock
    ) -> None:
        mock_content.ingest = AsyncMock(
            side_effect=[
                RuntimeError("err"),
                _make_content_result(state=ContentIngestState.CREATED),
            ]
        )
        result = await coordinator.ingest(_make_request(docs=2))
        assert result.documents_processed == 2
        assert result.documents_created == 1

    @pytest.mark.asyncio
    async def test_ingest_continues_batch_to_doc2_when_doc1_enqueue_raises(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        """Multi-doc: doc 1 enqueue fails; doc 2 must still be processed and counted."""
        mock_content.ingest = AsyncMock(
            side_effect=[
                _make_content_result(state=ContentIngestState.CREATED, chunk_ids=("c1",)),
                _make_content_result(state=ContentIngestState.CREATED, chunk_ids=("c2",)),
            ]
        )
        mock_enrichment.enqueue_chunks.side_effect = [
            RuntimeError("queue unavailable"),
            1,
        ]
        result = await coordinator.ingest(_make_request(docs=2, enrich=True))
        assert result.documents_processed == 2
        assert mock_content.ingest.call_count == 2
        assert result.documents_created == 1  # only doc 2 succeeded

    @pytest.mark.asyncio
    async def test_ingest_continues_batch_to_doc2_when_doc1_discard_raises(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        """Multi-doc: doc 1 discard fails; doc 2 must still be processed and counted."""
        mock_content.ingest = AsyncMock(
            side_effect=[
                _make_content_result(
                    state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-1",)
                ),
                _make_content_result(
                    state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-2",)
                ),
            ]
        )
        mock_enrichment.discard_chunks.side_effect = [
            RuntimeError("discard error"),
            EnrichmentDiscardResult(discarded_chunk_ids=("old-2",), queue_items_removed=1),
        ]
        result = await coordinator.ingest(_make_request(docs=2))
        assert result.documents_processed == 2
        assert mock_content.ingest.call_count == 2
        assert result.documents_replaced == 1  # only doc 2 succeeded

    # ------------------------------------------------------------------
    # AC2 — CREATED + enrich flag controls enqueue_chunks
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ingest_enqueues_chunks_for_created_document_with_enrich_true(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(
                state=ContentIngestState.CREATED, chunk_ids=("c1", "c2")
            )
        )
        await coordinator.ingest(_make_request(enrich=True))
        mock_enrichment.enqueue_chunks.assert_called_once_with(("c1", "c2"), "src-1")

    @pytest.mark.asyncio
    async def test_ingest_skips_enqueue_for_created_document_with_enrich_false(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(state=ContentIngestState.CREATED)
        )
        await coordinator.ingest(_make_request(enrich=False))
        mock_enrichment.enqueue_chunks.assert_not_called()

    # ------------------------------------------------------------------
    # AC3 — REPLACED: discard_chunks + invalidate_evidence_by_chunks + enqueue
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ingest_discards_old_chunks_from_enrichment_on_replaced(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(
                state=ContentIngestState.REPLACED,
                chunk_ids=("new-1",),
                replaced_chunk_ids=("old-1", "old-2"),
            )
        )
        await coordinator.ingest(_make_request())
        mock_enrichment.discard_chunks.assert_called_once_with(("old-1", "old-2"))

    @pytest.mark.asyncio
    async def test_ingest_invalidates_graph_evidence_for_replaced_chunks(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(
                state=ContentIngestState.REPLACED,
                replaced_chunk_ids=("old-1", "old-2"),
            )
        )
        await coordinator.ingest(_make_request())
        mock_graph.invalidate_evidence_by_chunks.assert_called_once_with(("old-1", "old-2"))

    @pytest.mark.asyncio
    async def test_ingest_enqueues_new_chunks_on_replaced_with_enrich_true(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(
                state=ContentIngestState.REPLACED,
                chunk_ids=("new-1", "new-2"),
                replaced_chunk_ids=("old-1",),
            )
        )
        await coordinator.ingest(_make_request(enrich=True))
        mock_enrichment.enqueue_chunks.assert_called_once_with(("new-1", "new-2"), "src-1")

    @pytest.mark.asyncio
    async def test_ingest_no_enqueue_on_replaced_with_enrich_false(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(
                state=ContentIngestState.REPLACED,
                replaced_chunk_ids=("old-1",),
            )
        )
        await coordinator.ingest(_make_request(enrich=False))
        mock_enrichment.enqueue_chunks.assert_not_called()
        # discard and invalidate are still called regardless of enrich flag
        mock_enrichment.discard_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_unchanged_document_no_enqueue_no_discard_no_invalidate(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(state=ContentIngestState.UNCHANGED)
        )
        await coordinator.ingest(_make_request(enrich=True))
        mock_enrichment.enqueue_chunks.assert_not_called()
        mock_enrichment.discard_chunks.assert_not_called()
        mock_graph.invalidate_evidence_by_chunks.assert_not_called()

    # ------------------------------------------------------------------
    # AC4 — Per-document guarantee: enqueue/discard always called if Content.ingest succeeds
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ingest_captures_per_doc_error_if_enqueue_raises_after_content_success(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(state=ContentIngestState.CREATED)
        )
        mock_enrichment.enqueue_chunks.side_effect = RuntimeError("queue unavailable")
        result = await coordinator.ingest(_make_request(enrich=True))
        # Batch must complete
        assert result.documents_processed == 1
        # Not counted as created because full pipeline did not succeed
        assert result.documents_created == 0

    @pytest.mark.asyncio
    async def test_ingest_captures_per_doc_error_if_discard_raises_after_content_success(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            return_value=_make_content_result(
                state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-1",)
            )
        )
        mock_enrichment.discard_chunks.side_effect = RuntimeError("discard error")
        result = await coordinator.ingest(_make_request())
        assert result.documents_processed == 1
        assert result.documents_replaced == 0

    @pytest.mark.asyncio
    async def test_replaced_cascade_discard_occurs_in_per_document_scope(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
    ) -> None:
        """Prove discard_chunks is called inside doc 1's scope, not after all Content.ingest calls."""
        content_call_count_at_first_discard: list[int] = []

        def track_discard(*_args: object, **_kwargs: object) -> EnrichmentDiscardResult:
            content_call_count_at_first_discard.append(mock_content.ingest.call_count)
            return EnrichmentDiscardResult(discarded_chunk_ids=("old-1",), queue_items_removed=1)

        mock_enrichment.discard_chunks.side_effect = track_discard
        mock_content.ingest = AsyncMock(
            side_effect=[
                _make_content_result(
                    state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-1",)
                ),
                _make_content_result(
                    state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-2",)
                ),
            ]
        )
        await coordinator.ingest(_make_request(docs=2))
        # discard_chunks was called for each REPLACED document
        assert mock_enrichment.discard_chunks.call_count == 2
        # When discard was first called, Content.ingest must have been called exactly once,
        # proving the cascade is inside doc 1's scope, not buffered after all content calls.
        assert content_call_count_at_first_discard[0] == 1

    @pytest.mark.asyncio
    async def test_replaced_cascade_invalidate_occurs_in_per_document_scope(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        """Prove invalidate_evidence_by_chunks is called inside doc 1's scope, not buffered."""
        content_call_count_at_first_invalidate: list[int] = []

        def track_invalidate(*_args: object, **_kwargs: object) -> EvidenceInvalidationResult:
            content_call_count_at_first_invalidate.append(mock_content.ingest.call_count)
            return EvidenceInvalidationResult()

        mock_graph.invalidate_evidence_by_chunks.side_effect = track_invalidate
        mock_content.ingest = AsyncMock(
            side_effect=[
                _make_content_result(
                    state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-a",)
                ),
                _make_content_result(
                    state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-b",)
                ),
            ]
        )
        await coordinator.ingest(_make_request(docs=2))
        assert mock_graph.invalidate_evidence_by_chunks.call_count == 2
        # When invalidate was first called, Content.ingest must have been called exactly once.
        assert content_call_count_at_first_invalidate[0] == 1

    # ------------------------------------------------------------------
    # AC5 — IngestResult fields
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ingest_result_documents_processed_equals_total_attempted(
        self, coordinator: IngestCoordinator, mock_content: MagicMock
    ) -> None:
        mock_content.ingest = AsyncMock(
            side_effect=[RuntimeError("x"), _make_content_result(), _make_content_result()]
        )
        result = await coordinator.ingest(_make_request(docs=3))
        assert result.documents_processed == 3

    @pytest.mark.asyncio
    async def test_ingest_result_state_counts_reflect_successful_outcomes(
        self,
        coordinator: IngestCoordinator,
        mock_content: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            side_effect=[
                _make_content_result(state=ContentIngestState.CREATED),
                _make_content_result(
                    state=ContentIngestState.REPLACED, replaced_chunk_ids=("old-x",)
                ),
                _make_content_result(state=ContentIngestState.UNCHANGED),
            ]
        )
        result = await coordinator.ingest(_make_request(docs=3))
        assert result.documents_created == 1
        assert result.documents_replaced == 1
        assert result.documents_unchanged == 1

    @pytest.mark.asyncio
    async def test_ingest_result_content_results_excludes_failed_documents(
        self, coordinator: IngestCoordinator, mock_content: MagicMock
    ) -> None:
        success = _make_content_result()
        mock_content.ingest = AsyncMock(side_effect=[RuntimeError("fail"), success])
        result = await coordinator.ingest(_make_request(docs=2))
        assert len(result.content_results) == 1
        assert result.content_results[0] is success

    @pytest.mark.asyncio
    async def test_ingest_result_started_at_before_or_equal_completed_at(
        self, coordinator: IngestCoordinator
    ) -> None:
        result = await coordinator.ingest(_make_request())
        assert result.started_at <= result.completed_at

    @pytest.mark.asyncio
    async def test_ingest_result_source_id_matches_request(
        self, coordinator: IngestCoordinator
    ) -> None:
        result = await coordinator.ingest(_make_request(source_id="src-xyz"))
        assert result.source_id == "src-xyz"

    # ------------------------------------------------------------------
    # AC6 — Source health updated after batch completes
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_ingest_records_health_ok_when_all_documents_succeed(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            side_effect=[
                _make_content_result(state=ContentIngestState.CREATED),
                _make_content_result(state=ContentIngestState.UNCHANGED),
            ]
        )
        await coordinator.ingest(_make_request(docs=2))
        report = _extract_health_report(mock_sources)
        assert report.health == SourceHealth.OK

    @pytest.mark.asyncio
    async def test_ingest_records_health_degraded_when_some_documents_fail(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            side_effect=[RuntimeError("fail"), _make_content_result()]
        )
        await coordinator.ingest(_make_request(docs=2))
        report = _extract_health_report(mock_sources)
        assert report.health == SourceHealth.DEGRADED

    @pytest.mark.asyncio
    async def test_ingest_records_health_failed_when_all_documents_fail(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(side_effect=RuntimeError("all fail"))
        await coordinator.ingest(_make_request(docs=1))
        report = _extract_health_report(mock_sources)
        assert report.health == SourceHealth.FAILED

    @pytest.mark.asyncio
    async def test_ingest_health_record_health_called_with_correct_source_id(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
    ) -> None:
        await coordinator.ingest(_make_request(source_id="src-check"))
        call = mock_sources.record_health.call_args
        assert call is not None
        source_id_arg = call.args[0] if call.args else call.kwargs.get("source_id")
        assert source_id_arg == "src-check"

    @pytest.mark.asyncio
    async def test_ingest_health_message_includes_count_summary(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
    ) -> None:
        mock_content.ingest = AsyncMock(
            side_effect=[RuntimeError("fail"), _make_content_result()]
        )
        await coordinator.ingest(_make_request(docs=2))
        report = _extract_health_report(mock_sources)
        assert report.message is not None
        assert any(c.isdigit() for c in report.message)

    # ------------------------------------------------------------------
    # AC7 — stats() aggregates from all 4 stores; never raises
    # ------------------------------------------------------------------

    def test_stats_sources_total_and_active_from_sources_store(
        self, coordinator: IngestCoordinator, mock_sources: MagicMock
    ) -> None:
        mock_sources.stats.return_value = SourceStats(total=8, active=6, inactive=1, wished=1)
        result = coordinator.stats()
        assert result.sources_total == 8
        assert result.sources_active == 6

    def test_stats_documents_total_and_chunks_total_from_content_store(
        self, coordinator: IngestCoordinator, mock_content: MagicMock
    ) -> None:
        mock_content.stats.return_value = ContentStats(documents=42, chunks=200, vectors=200)
        result = coordinator.stats()
        assert result.documents_total == 42
        assert result.chunks_total == 200

    def test_stats_enrichment_pending_from_enrichment_store(
        self, coordinator: IngestCoordinator, mock_enrichment: MagicMock
    ) -> None:
        mock_enrichment.stats.return_value = EnrichmentStats(pending=13)
        result = coordinator.stats()
        assert result.enrichment_pending == 13

    def test_stats_graph_entities_and_edges_from_graph_store(
        self, coordinator: IngestCoordinator, mock_graph: MagicMock
    ) -> None:
        mock_graph.stats.return_value = GraphStats(entities=99, edges=77)
        result = coordinator.stats()
        assert result.graph_entities == 99
        assert result.graph_edges == 77

    def test_stats_returns_ingest_stats_type(
        self, coordinator: IngestCoordinator
    ) -> None:
        result = coordinator.stats()
        assert isinstance(result, IngestStats)

    def test_stats_never_raises_when_stores_are_unavailable(
        self,
        coordinator: IngestCoordinator,
        mock_sources: MagicMock,
        mock_content: MagicMock,
        mock_enrichment: MagicMock,
        mock_graph: MagicMock,
    ) -> None:
        mock_sources.stats.side_effect = RuntimeError("store unavailable")
        mock_content.stats.side_effect = RuntimeError("store unavailable")
        mock_enrichment.stats.side_effect = RuntimeError("store unavailable")
        mock_graph.stats.side_effect = RuntimeError("store unavailable")
        # Must not propagate any exception
        result = coordinator.stats()
        assert isinstance(result, IngestStats)

    # ------------------------------------------------------------------
    # AC8 — refresh() with no fetcher returns empty RefreshResult
    #        (stale NotImplementedError guard replaced by #1886 behavioral contract)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_refresh_with_no_fetcher_returns_empty_refresh_result(
        self, coordinator: IngestCoordinator
    ) -> None:
        result = await coordinator.refresh(RefreshRequest())
        assert isinstance(result, RefreshResult)
        assert result.sources_checked == 0
        assert result.sources_refreshed == 0
        assert result.errors == ()
