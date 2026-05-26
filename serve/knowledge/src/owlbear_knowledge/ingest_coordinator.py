"""Ingest coordinator implementation for protocol-based knowledge ingest."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_knowledge.protocols.content import (
    ContentIngestRequest,
    ContentIngestResult,
    ContentIngestState,
    ContentStore,
)
from owlbear_knowledge.protocols.ingest import (
    IngestDocument,
    IngestRequest,
    IngestResult,
    IngestStats,
    RefreshRequest,
    RefreshResult,
)
from owlbear_knowledge.protocols.sources import (
    SourceHealth,
    SourceHealthReport,
    SourceStore,
)

if TYPE_CHECKING:
    from owlbear_knowledge.protocols.enrichment import EnrichmentStore
    from owlbear_knowledge.protocols.graph import GraphStore


class IngestCoordinator:
    """Coordinate ingest operations across Sources, Content, Enrichment, and Graph."""

    def __init__(
        self,
        *,
        sources: SourceStore,
        content: ContentStore,
        enrichment: EnrichmentStore,
        graph: GraphStore,
    ) -> None:
        self._sources = sources
        self._content = content
        self._enrichment = enrichment
        self._graph = graph

    async def ingest(self, request: IngestRequest) -> IngestResult:
        """Ingest a batch of documents and run per-document cascade steps."""
        if self._sources.get_source(request.source_id) is None:
            msg = f"source {request.source_id!r} not found"
            raise LookupError(msg)

        started_at = datetime.now(tz=UTC)

        documents_processed = 0
        documents_created = 0
        documents_replaced = 0
        documents_unchanged = 0
        chunks_created = 0
        chunks_replaced = 0
        chunks_enqueued = 0
        content_results: list[ContentIngestResult] = []

        for document in request.documents:
            documents_processed += 1
            outcome = await self._process_document(request, document)
            if outcome is None:
                continue

            state, content_result, created_chunks, replaced_chunks, enqueued_chunks = outcome
            chunks_created += created_chunks
            chunks_replaced += replaced_chunks
            chunks_enqueued += enqueued_chunks
            content_results.append(content_result)

            if state == ContentIngestState.CREATED:
                documents_created += 1
            elif state == ContentIngestState.REPLACED:
                documents_replaced += 1
            else:
                documents_unchanged += 1

        completed_at = datetime.now(tz=UTC)
        successes = documents_created + documents_replaced + documents_unchanged
        failures = documents_processed - successes

        if failures == 0:
            health = SourceHealth.OK
        elif successes == 0 and documents_processed > 0:
            health = SourceHealth.FAILED
        else:
            health = SourceHealth.DEGRADED

        message = (
            f"processed={documents_processed}, succeeded={successes}, failed={failures}, "
            f"created={documents_created}, replaced={documents_replaced}, unchanged={documents_unchanged}"
        )
        self._sources.record_health(
            request.source_id,
            SourceHealthReport(health=health, message=message, checked_at=completed_at),
        )

        return IngestResult(
            source_id=request.source_id,
            documents_processed=documents_processed,
            documents_created=documents_created,
            documents_replaced=documents_replaced,
            documents_unchanged=documents_unchanged,
            chunks_created=chunks_created,
            chunks_replaced=chunks_replaced,
            chunks_enqueued=chunks_enqueued,
            content_results=tuple(content_results),
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _process_document(
        self,
        request: IngestRequest,
        document: IngestDocument,
    ) -> tuple[ContentIngestState, ContentIngestResult, int, int, int] | None:
        """Run ingest and cascade actions for one document."""
        try:
            content_result = await self._content.ingest(
                ContentIngestRequest(
                    source_id=request.source_id,
                    title=document.title,
                    text=document.text,
                    uri=document.uri,
                    external_id=document.external_id,
                    metadata=dict(document.metadata),
                )
            )

            outcome: tuple[ContentIngestState, ContentIngestResult, int, int, int]
            chunks_created = len(content_result.chunk_ids)
            chunks_enqueued = 0

            if content_result.state == ContentIngestState.CREATED:
                if request.enrich:
                    chunks_enqueued = self._enrichment.enqueue_chunks(
                        content_result.chunk_ids,
                        request.source_id,
                    )
                outcome = (content_result.state, content_result, chunks_created, 0, chunks_enqueued)
            elif content_result.state == ContentIngestState.REPLACED:
                self._enrichment.discard_chunks(content_result.replaced_chunk_ids)
                self._graph.invalidate_evidence_by_chunks(content_result.replaced_chunk_ids)
                if request.enrich:
                    chunks_enqueued = self._enrichment.enqueue_chunks(
                        content_result.chunk_ids,
                        request.source_id,
                    )
                outcome = (
                    content_result.state,
                    content_result,
                    chunks_created,
                    len(content_result.replaced_chunk_ids),
                    chunks_enqueued,
                )
            else:
                outcome = (content_result.state, content_result, 0, 0, 0)
        except (RuntimeError, ValueError, LookupError, TypeError, AttributeError, KeyError):
            # Per-document failures are captured by omission from success counters.
            return None
        else:
            return outcome

    async def refresh(self, request: RefreshRequest) -> RefreshResult:
        """Refresh is intentionally deferred until dependent protocol tasks complete."""
        _ = request
        msg = "refresh() is blocked on #1884 and #1885"
        raise NotImplementedError(msg)

    def stats(self) -> IngestStats:
        """Aggregate stats from all leaf stores and never raise exceptions."""
        stats = IngestStats()

        try:
            source_stats = self._sources.stats()
        except RuntimeError:
            source_stats = None
        else:
            stats = stats.model_copy(
                update={
                    "sources_total": source_stats.total,
                    "sources_active": source_stats.active,
                }
            )

        try:
            content_stats = self._content.stats()
        except RuntimeError:
            content_stats = None
        else:
            stats = stats.model_copy(
                update={
                    "documents_total": content_stats.documents,
                    "chunks_total": content_stats.chunks,
                }
            )

        try:
            enrichment_stats = self._enrichment.stats()
        except RuntimeError:
            enrichment_stats = None
        else:
            stats = stats.model_copy(update={"enrichment_pending": enrichment_stats.pending})

        try:
            graph_stats = self._graph.stats()
        except RuntimeError:
            graph_stats = None
        else:
            stats = stats.model_copy(
                update={
                    "graph_entities": graph_stats.entities,
                    "graph_edges": graph_stats.edges,
                }
            )

        return stats
