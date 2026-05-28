"""Ingest coordinator implementation for protocol-based knowledge ingest."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_knowledge.protocols.content import (
    ContentIngestRequest,
    ContentIngestResult,
    ContentIngestState,
    ContentPurgeResult,
    ContentStore,
)
from owlbear_knowledge.protocols.enrichment import EnrichmentPurgeResult
from owlbear_knowledge.protocols.graph import EvidenceInvalidationResult
from owlbear_knowledge.protocols.ingest import (
    IngestDocument,
    IngestRequest,
    IngestResult,
    IngestStats,
    PurgeResult,
    PurgeStatus,
    RefreshError,
    RefreshRequest,
    RefreshResult,
)
from owlbear_knowledge.protocols.sources import (
    SourceDeletionInfo,
    SourceHealth,
    SourceHealthReport,
    SourceState,
    SourceStore,
    SourceUpdate,
)

if TYPE_CHECKING:
    from owlbear_knowledge.protocols.enrichment import EnrichmentStore
    from owlbear_knowledge.protocols.fetcher import SourceFetcher
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
        fetcher: SourceFetcher | None = None,
    ) -> None:
        self._sources = sources
        self._content = content
        self._enrichment = enrichment
        self._graph = graph
        self._fetcher = fetcher

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

    async def delete_source(self, source_id: str, *, reason: str | None = None) -> PurgeResult:
        """Delete a source via idempotent D63 cascade semantics.

        The 5-step cascade is deterministic and fail-fast. Per D63, rerunning after
        partial failures is safe: already-completed state is treated as idempotent
        progress and remaining steps are attempted. Non-guarantee: after a post-step-2
        partial failure, retry loses chunk addressability (Content may return empty
        chunk_ids), so graph evidence from original chunks can persist.
        """
        completed_steps: list[str] = []

        try:
            source_result = self._sources.delete_source(source_id, reason=reason)
        except LookupError:
            source_result = SourceDeletionInfo(
                source_id=source_id,
                source_name="",
                scope="",
                deleted_at=datetime.now(tz=UTC),
                reason=reason,
            )
        completed_steps.append("sources.delete")

        content_result = ContentPurgeResult(source_id=source_id)
        enrichment_result = EnrichmentPurgeResult(source_id=source_id)
        graph_result = EvidenceInvalidationResult()

        try:
            content_result = self._content.purge_source(source_id)
        except Exception as exc:  # noqa: BLE001 - partial purge returns structured failure.
            return PurgeResult(
                status=PurgeStatus.PARTIAL,
                completed_steps=tuple(completed_steps),
                failed_step="content.purge",
                error=str(exc),
                source=source_result,
                content=content_result,
                enrichment=enrichment_result,
                graph=graph_result,
            )
        completed_steps.append("content.purge")

        chunk_ids = content_result.chunk_ids
        try:
            self._enrichment.discard_chunks(chunk_ids)
        except Exception as exc:  # noqa: BLE001 - partial purge returns structured failure.
            return PurgeResult(
                status=PurgeStatus.PARTIAL,
                completed_steps=tuple(completed_steps),
                failed_step="enrichment.discard",
                error=str(exc),
                source=source_result,
                content=content_result,
                enrichment=enrichment_result,
                graph=graph_result,
            )
        completed_steps.append("enrichment.discard")

        try:
            enrichment_result = self._enrichment.purge_source(source_id)
        except Exception as exc:  # noqa: BLE001 - partial purge returns structured failure.
            return PurgeResult(
                status=PurgeStatus.PARTIAL,
                completed_steps=tuple(completed_steps),
                failed_step="enrichment.purge",
                error=str(exc),
                source=source_result,
                content=content_result,
                enrichment=enrichment_result,
                graph=graph_result,
            )
        completed_steps.append("enrichment.purge")

        try:
            graph_result = self._graph.invalidate_evidence_by_chunks(chunk_ids)
        except Exception as exc:  # noqa: BLE001 - partial purge returns structured failure.
            return PurgeResult(
                status=PurgeStatus.PARTIAL,
                completed_steps=tuple(completed_steps),
                failed_step="graph.invalidate",
                error=str(exc),
                source=source_result,
                content=content_result,
                enrichment=enrichment_result,
                graph=graph_result,
            )
        completed_steps.append("graph.invalidate")

        return PurgeResult(
            status=PurgeStatus.COMPLETE,
            completed_steps=tuple(completed_steps),
            failed_step=None,
            error=None,
            source=source_result,
            content=content_result,
            enrichment=enrichment_result,
            graph=graph_result,
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
        """Refresh ACTIVE sources using the configured fetcher and ingest pipeline."""
        if self._fetcher is None:
            return RefreshResult()

        listed_sources = self._sources.list_sources(state=SourceState.ACTIVE)
        filtered_sources = [
            source
            for source in listed_sources
            if (not request.source_ids or source.id in request.source_ids)
            and (request.force or source.refreshable)
        ]

        ingest_results: list[IngestResult] = []
        errors: list[RefreshError] = []
        sources_refreshed = 0

        for source in filtered_sources:
            try:
                fetch_result = await self._fetcher.fetch_source(source)
                errors.extend(
                    RefreshError(
                        source_id=source.id,
                        error=f"{fetch_error.uri}: {fetch_error.error}",
                        timestamp=datetime.now(tz=UTC),
                    )
                    for fetch_error in fetch_result.errors
                )
                mapped_documents = tuple(
                    IngestDocument(
                        title=document.title,
                        text=document.text,
                        uri=document.uri,
                        external_id=document.external_id,
                        metadata=dict(document.metadata),
                    )
                    for document in fetch_result.documents
                )

                if not mapped_documents and fetch_result.errors:
                    continue

                if mapped_documents:
                    ingest_result = await self.ingest(
                        IngestRequest(
                            source_id=source.id,
                            documents=mapped_documents,
                            enrich=source.enrich,
                        )
                    )
                    ingest_results.append(ingest_result)

                refreshed_at = datetime.now(tz=UTC)
                self._sources.update_source(
                    source.id,
                    SourceUpdate(last_refreshed_at=refreshed_at),
                )
                sources_refreshed += 1
            except Exception as exc:  # noqa: BLE001 - batch must continue after per-source failures.
                errors.append(
                    RefreshError(
                        source_id=source.id,
                        error=str(exc),
                        timestamp=datetime.now(tz=UTC),
                    )
                )

        return RefreshResult(
            sources_checked=len(filtered_sources),
            sources_refreshed=sources_refreshed,
            ingest_results=tuple(ingest_results),
            errors=tuple(errors),
        )

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
