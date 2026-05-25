"""IngestPipeline Protocol — Ingest module public surface.

Module responsibility: orchestrate the write path. Fetches raw content
(via the external ContentFetcher boundary in serve/browser/), hands it to
ContentStore, cascades replacement signals to EnrichmentEngine, and
coordinates source lifecycle updates.

Owns NO tables. Pure coordinator (CP13).

Safety invariant:
  All ingested content is marked as externally-sourced (not system
  instructions) before storage. This ensures downstream agents treat
  retrieved text as data, not as trusted instructions.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field, model_validator

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata
from owlbear_knowledge.protocols.content import ContentPurgeResult  # noqa: TC001
from owlbear_knowledge.protocols.enrichment import EnrichmentPurgeResult  # noqa: TC001
from owlbear_knowledge.protocols.graph import PurgeEvidenceResult  # noqa: TC001
from owlbear_knowledge.protocols.sources import SourceDeletionInfo, SourceRecord  # noqa: TC001


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IngestStatus(StrEnum):
    """Overall write-path outcome."""

    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Boundary types — Requests
# ---------------------------------------------------------------------------


class IngestRequest(BoundaryModel):
    """Request for Ingest to accept or fetch a single document.

    Provide either ``text`` (direct) or ``uri`` (fetch via transport).
    """

    source_id: str
    title: str | None = None
    uri: str | None = None
    text: str | None = None
    scope: str = "global"
    run_enrichment: bool = True
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_uri_or_text(self) -> IngestRequest:
        """Require either a fetch target or direct text payload."""
        if self.uri is None and self.text is None:
            msg = "IngestRequest requires either uri or text"
            raise ValueError(msg)
        return self


class RefreshRequest(BoundaryModel):
    """Request to refresh all ingestable targets for a registered source."""

    source_id: str
    run_enrichment: bool = True
    force: bool = False


# ---------------------------------------------------------------------------
# Boundary types — Results
# ---------------------------------------------------------------------------


class IngestFailure(BoundaryModel):
    """One recoverable write-path failure."""

    stage: str
    message: str
    source_id: str | None = None
    uri: str | None = None


class IngestResult(BoundaryModel):
    """Write-path result for a single document ingest."""

    status: IngestStatus
    source: SourceRecord
    document_id: str | None = None
    chunk_ids: tuple[str, ...] = Field(default_factory=tuple)
    replaced_chunk_ids: tuple[str, ...] = Field(default_factory=tuple)
    failures: tuple[IngestFailure, ...] = Field(default_factory=tuple)
    completed_at: datetime


class RefreshResult(BoundaryModel):
    """Refresh result for all targets under one source."""

    status: IngestStatus
    source: SourceRecord
    ingests: tuple[IngestResult, ...] = Field(default_factory=tuple)
    failures: tuple[IngestFailure, ...] = Field(default_factory=tuple)
    completed_at: datetime


class PurgeReport(BoundaryModel):
    """Cascade purge result composed from all downstream modules."""

    source_id: str
    content: ContentPurgeResult | None = None
    enrichment: EnrichmentPurgeResult | None = None
    graph: PurgeEvidenceResult | None = None
    failures: tuple[IngestFailure, ...] = Field(default_factory=tuple)
    completed_at: datetime


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class IngestPipeline(Protocol):
    """Public contract for the Ingest module.

    Storage ownership: Ingest owns NO tables. All mutations pass through
    module protocols (Sources, Content, Enrichment, Graph).

    Dependencies: SourceStore, ContentStore, EnrichmentEngine, GraphStore,
    and an external ContentFetcher (from serve/browser/).
    """

    async def ingest(self, request: IngestRequest) -> IngestResult:
        """Fetch or accept text, write to Content, cascade to Enrichment.

        Sequence:
          1. Validate source exists via SourceStore.get_source.
          2. If request.uri: fetch via ContentFetcher (transport determined
             by source's fetch_method).
          3. Mark content as externally-sourced (safety invariant).
          4. Call ContentStore.ingest with the text.
          5. If result has replaced_chunk_ids: call
             EnrichmentEngine.mark_stale(replaced_chunk_ids).
          6. Update source health/state via SourceStore as appropriate.

        Guarantees:
          - On failure, status is FAILED and failures tuple is populated.
          - Partial-success is reflected in the result.
          - Source state is updated on both success and failure.

        Non-guarantees:
          - Fetch retry policy is implementation-defined.
          - Enrichment scheduling (when extraction actually runs) is
            agent-driven, not Ingest's concern.

        Side effects:
          - No direct table writes; all mutations through module protocols.

        Raises:
          - ``LookupError`` if source_id does not exist.
          - ``ValueError`` if IngestRequest validation fails.
        """
        ...

    async def refresh_source(self, request: RefreshRequest) -> RefreshResult:
        """Refresh every ingestable target for a registered source.

        Guarantees:
          - Only ACTIVE sources are refreshed (INACTIVE and WISHED are
            skipped with status=SKIPPED).
          - If force=False and content is unchanged, individual ingests
            return status=SKIPPED.

        Non-guarantees:
          - Target discovery order and concurrency are implementation
            details.

        Side effects:
          - No direct table writes; all mutations through module protocols.

        Raises:
          - ``LookupError`` if source_id does not exist.
        """
        ...

    async def handle_source_purge(self, info: SourceDeletionInfo) -> PurgeReport:
        """Coordinate downstream cleanup after Sources deletion.

        Sequence (must execute in this order):
          1. ContentStore.purge_source(info.source_id).
          2. EnrichmentEngine.purge_source(info.source_id).
          3. GraphStore.purge_evidence_by_source(info.source_id).

        Guarantees:
          - Uses the info payload; does not require reading the deleted
            source record.
          - Idempotent: re-running on an already-purged source returns
            zero counts in all sub-results.

        Non-guarantees:
          - Does not delete the source record itself (Sources already did).

        Side effects:
          - No direct table writes; all mutations through module protocols.

        Raises:
          - Never raises (individual module purges are idempotent).
        """
        ...
