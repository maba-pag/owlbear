"""IngestCoordinator Protocol — Ingest module public surface.

Module responsibility: orchestrate the full ingest pipeline from source
fetch through content ingestion, enrichment enqueuing, and deletion cascade.
Owns no tables — delegates storage to Sources, Content, Enrichment, and Graph.

Ingest is the only module that coordinates cross-module cascades. Individual
modules (Sources, Content, Enrichment, Graph) never call each other directly.

Cascade sequence on source deletion (R31):
  1. Sources.delete_source → SourceDeletionInfo
  2. Content.purge_source → ContentPurgeResult (has chunk_ids)
  3. Enrichment.discard_chunks(chunk_ids) → remove pending queue items
  4. Enrichment.purge_source → remove extraction records
  5. Graph.invalidate_evidence_by_chunks(chunk_ids) → remove evidence + orphans

Cascade sequence on content replacement (re-ingest):
  1. Content.ingest → ContentIngestResult (state=REPLACED, replaced_chunk_ids)
  2. Enrichment.discard_chunks(replaced_chunk_ids) → clean stale queue items
  3. Graph.invalidate_evidence_by_chunks(replaced_chunk_ids) → clean evidence
  4. Enrichment.enqueue_chunks(new_chunk_ids) → queue for extraction
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata
from owlbear_knowledge.protocols.content import ContentIngestResult, ContentPurgeResult  # noqa: TC001
from owlbear_knowledge.protocols.enrichment import EnrichmentPurgeResult  # noqa: TC001
from owlbear_knowledge.protocols.graph import EvidenceInvalidationResult  # noqa: TC001
from owlbear_knowledge.protocols.sources import SourceDeletionInfo  # noqa: TC001

# ---------------------------------------------------------------------------
# Request types
# ---------------------------------------------------------------------------


class IngestRequest(BoundaryModel):
    """Request to ingest content from a registered source.

    This is the primary entry point for bringing new content into the
    knowledge system.
    """

    source_id: str
    documents: tuple[IngestDocument, ...] = Field(min_length=1)
    enrich: bool = True
    metadata: Metadata = Field(default_factory=dict)


class IngestDocument(BoundaryModel):
    """A document to be ingested from a source."""

    title: str
    text: str
    uri: str | None = None
    external_id: str | None = None
    metadata: Metadata = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class IngestResult(BoundaryModel):
    """Aggregate result of an ingest operation."""

    source_id: str
    documents_processed: int = 0
    documents_created: int = 0
    documents_replaced: int = 0
    documents_unchanged: int = 0
    chunks_created: int = 0
    chunks_replaced: int = 0
    chunks_enqueued: int = 0
    content_results: tuple[ContentIngestResult, ...] = Field(default_factory=tuple)
    started_at: datetime
    completed_at: datetime


class PurgeStatus(StrEnum):
    """Outcome of a multi-step deletion cascade."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class PurgeResult(BoundaryModel):
    """Aggregate result of a source deletion cascade.

    Carries typed sub-results from each module for full audit trail.
    ``status`` indicates whether all steps completed successfully.
    ``completed_steps`` lists the steps that ran (in order).
    """

    status: PurgeStatus
    completed_steps: tuple[str, ...] = Field(default_factory=tuple)
    failed_step: str | None = None
    error: str | None = None
    source: SourceDeletionInfo
    content: ContentPurgeResult
    enrichment: EnrichmentPurgeResult
    graph: EvidenceInvalidationResult


# ---------------------------------------------------------------------------
# Refresh types
# ---------------------------------------------------------------------------


class RefreshRequest(BoundaryModel):
    """Request to refresh content from sources.

    When source_ids is empty, all refreshable sources are refreshed.
    """

    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    force: bool = False
    metadata: Metadata = Field(default_factory=dict)


class RefreshResult(BoundaryModel):
    """Aggregate result of a refresh operation."""

    sources_checked: int = 0
    sources_refreshed: int = 0
    ingest_results: tuple[IngestResult, ...] = Field(default_factory=tuple)
    errors: tuple[RefreshError, ...] = Field(default_factory=tuple)


class RefreshError(BoundaryModel):
    """Error encountered during source refresh."""

    source_id: str
    error: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class IngestStats(BoundaryModel):
    """Aggregate stats across all modules (Ingest coordinates the query)."""

    sources_total: int = 0
    sources_active: int = 0
    documents_total: int = 0
    chunks_total: int = 0
    enrichment_pending: int = 0
    graph_entities: int = 0
    graph_edges: int = 0


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class IngestCoordinator(Protocol):
    """Public contract for the Ingest coordination module.

    Storage ownership: Ingest owns no tables. It delegates writes to
    Sources, Content, Enrichment, and Graph.

    Cascade responsibility: Ingest is the sole orchestrator of cross-module
    cascades (deletion, replacement, enqueue).
    """

    async def ingest(self, request: IngestRequest) -> IngestResult:
        """Ingest documents from a source.

        Guarantees:
          - Each document is passed to Content.ingest for chunking and
            embedding.
          - For REPLACED documents: stale chunks are discarded from
            Enrichment queue and evidence is invalidated in Graph.
          - For new/replaced documents with enrich=True: new chunk IDs
            are enqueued for enrichment.
          - Source health is updated based on ingest success/failure.

        Non-guarantees:
          - Document ordering, parallelism degree, and batch sizing are
            implementation details.

        Side effects:
          - Writes via Content, Enrichment, and Graph delegates.
          - Updates source health via Sources.

        Raises:
          - ``LookupError`` if source_id does not exist.
        """
        ...

    async def delete_source(self, source_id: str, *, reason: str | None = None) -> PurgeResult:
        """Execute the full deletion cascade for a source.

        Cascade sequence:
          1. Sources.delete_source → SourceDeletionInfo
          2. Content.purge_source → ContentPurgeResult (provides chunk_ids)
          3. Enrichment.discard_chunks(chunk_ids) → remove stale queue items
          4. Enrichment.purge_source → remove extraction records
          5. Graph.invalidate_evidence_by_chunks(chunk_ids) → evidence + orphans

        Guarantees:
          - All module-owned data reachable at call time is removed in
            correct dependency order.
          - PurgeResult carries typed sub-results for full audit trail.
          - deleted_at and reason are preserved for traceability.
          - Each cascade step is idempotent: re-running delete_source on
            a partially-purged source completes the missing steps and
            returns status=COMPLETE.

        Non-guarantees:
          - Atomicity across modules is implementation-defined (saga vs
            transaction). Partial failure returns status=PARTIAL with
            completed_steps indicating progress.
          - Retry after post-step-2 partial failure cannot recover
            chunk_ids from Content; graph evidence from original chunks persists
            (chunk addressability lost).

        Side effects:
          - Writes via Sources, Content, Enrichment, and Graph delegates.

        Raises:
          - Never raises LookupError — caught internally for
            forward-recovery semantics.
        """
        ...

    async def refresh(self, request: RefreshRequest) -> RefreshResult:
        """Refresh content from one or more sources.

        Guarantees:
          - Only sources with refreshable=True are processed (unless
            force=True overrides).
          - Each refreshed source is re-ingested through the full pipeline.
          - Errors in individual sources do not abort the batch.

        Non-guarantees:
          - Fetch mechanism (HTTP, filesystem, browser) is determined by
            source FetchTransport — implementation detail.

        Side effects:
          - Writes via Sources, Content, Enrichment, and Graph delegates.

        Raises:
          - Never raises (errors are captured in RefreshResult.errors).
        """
        ...

    def stats(self) -> IngestStats:
        """Return aggregate stats from all modules.

        Guarantees:
          - Queries each module's stats() and assembles a unified view.

        Non-guarantees:
          - Consistency across modules (race conditions between stat
            queries) is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises.
        """
        ...
