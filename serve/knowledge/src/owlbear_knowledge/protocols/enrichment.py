"""EnrichmentStore Protocol — Enrichment module public surface.

Module responsibility: LLM-driven entity/relation extraction from content
chunks, enrichment queue management, and intra-document edge suggestion.
Owns tables ``enrich_*``.

The LLM is external to this module — Enrichment exposes a state-machine
interface (enqueue → process → commit) without prescribing model selection,
prompt engineering, or inference hosting (CP14).

Has zero dependencies on other knowledge modules at the Protocol boundary.
Enrichment orchestration in the implementation layer may import Content and
Graph protocols for coordination.

Table ownership: only Enrichment writes ``enrich_*`` tables.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import (
    BoundaryModel,
    EntityType,
    Metadata,
    RelationType,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EnrichmentState(StrEnum):
    """Queue states for enrichment work items."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Extraction types (R30 — local_ref for agent-submitted edges)
# ---------------------------------------------------------------------------


class ExtractedEntity(BoundaryModel):
    """Entity extracted from a chunk by the LLM.

    ``local_ref`` is a transient within-batch identifier so that
    ExtractedRelation can reference entities before they have persistent
    IDs. It is NOT persisted — only meaningful within a single
    submit_extractions call.
    """

    local_ref: str
    name: str
    entity_type: EntityType
    description: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)


class ExtractedRelation(BoundaryModel):
    """Relation extracted from a chunk by the LLM.

    ``source_ref`` and ``target_ref`` use local_ref values from the
    co-submitted ExtractedEntity list, enabling the caller to express
    edges between entities that don't have persistent IDs yet.
    """

    source_ref: str
    target_ref: str
    relation_type: RelationType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)


class ExtractionResult(BoundaryModel):
    """Resolved result of submit_extractions after entity resolution."""

    chunk_id: str
    entity_ids: tuple[str, ...] = Field(default_factory=tuple)
    edge_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Queue types
# ---------------------------------------------------------------------------


class EnrichmentQueueItem(BoundaryModel):
    """A chunk waiting for or undergoing enrichment."""

    id: str
    chunk_id: str
    source_id: str
    state: EnrichmentState
    attempts: int = 0
    last_error: str | None = None
    enqueued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EnrichmentBatch(BoundaryModel):
    """A batch of queue items claimed for processing."""

    items: tuple[EnrichmentQueueItem, ...] = Field(default_factory=tuple)
    batch_id: str


# ---------------------------------------------------------------------------
# Intra-document edge suggestion (R37)
# ---------------------------------------------------------------------------


class SuggestedEdge(BoundaryModel):
    """An intra-document edge suggestion (not yet committed to Graph).

    Returned by suggest_intra_doc_edges — callers decide whether to
    commit these to Graph via upsert_edge.
    """

    source_entity_id: str
    target_entity_id: str
    relation_type: RelationType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


# ---------------------------------------------------------------------------
# Purge / discard types
# ---------------------------------------------------------------------------


class EnrichmentPurgeResult(BoundaryModel):
    """Itemised result of enrichment purge for audit and cascade."""

    source_id: str
    queue_items_removed: int = 0
    extractions_removed: int = 0


class EnrichmentDiscardResult(BoundaryModel):
    """Result of discarding specific chunks from the enrichment queue."""

    discarded_chunk_ids: tuple[str, ...] = Field(default_factory=tuple)
    queue_items_removed: int = 0


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class EnrichmentStats(BoundaryModel):
    """Counts owned by the Enrichment module."""

    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    failed: int = 0


# ---------------------------------------------------------------------------
# Enrichment parameters (R41 — no claim_ttl, system invariant)
# ---------------------------------------------------------------------------


class EnrichmentParams(BoundaryModel):
    """Configurable parameters for enrichment processing.

    claim_ttl is deliberately absent — it is a system invariant managed
    by the implementation, not a caller-tunable parameter.
    """

    batch_size: int = Field(default=10, ge=1, le=100)
    max_retries: int = Field(default=3, ge=0, le=10)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EnrichmentStore(Protocol):
    """Public contract for the Enrichment module.

    Storage ownership: only Enrichment writes ``enrich_*`` tables.
    Dependency rule: Enrichment imports no other knowledge module
    internals at the Protocol boundary.
    """

    # --- Queue management ---

    def enqueue_chunks(self, chunk_ids: tuple[str, ...], source_id: str) -> int:
        """Add chunks to the enrichment queue.

        Guarantees:
          - Returns the count of newly enqueued items (duplicates are
            silently skipped).
          - Already-completed or in-progress chunks are not re-enqueued.

        Non-guarantees:
          - Processing order is implementation-defined.

        Side effects:
          - Writes only ``enrich_*`` tables.

        Raises:
          - ``ValueError`` if chunk_ids is empty.
        """
        ...

    def discard_chunks(self, chunk_ids: tuple[str, ...]) -> EnrichmentDiscardResult:
        """Remove chunks from the enrichment queue (lifecycle cleanup).

        Guarantees:
          - Pending and failed queue items for the given chunk_ids are
            removed.
          - In-progress items are left untouched (they will fail or
            complete on their own).
          - Idempotent: already-absent chunks are silently ignored.

        Non-guarantees:
          - Does not remove graph evidence — that is Graph's
            responsibility via invalidate_evidence_by_chunks.

        Side effects:
          - Writes only ``enrich_*`` tables (deletions).

        Raises:
          - Never raises (idempotent).
        """
        ...

    def claim_batch(self, params: EnrichmentParams) -> EnrichmentBatch:
        """Claim a batch of pending items for processing.

        Guarantees:
          - Up to params.batch_size items transition to IN_PROGRESS.
          - Claimed items are not visible to concurrent claim_batch calls.

        Non-guarantees:
          - Selection order among pending items is implementation-defined.

        Side effects:
          - Writes only ``enrich_*`` tables (state transition).

        Raises:
          - Never raises (returns empty batch if queue is empty).
        """
        ...

    def submit_extractions(
        self,
        chunk_id: str,
        entities: tuple[ExtractedEntity, ...],
        relations: tuple[ExtractedRelation, ...],
    ) -> ExtractionResult:
        """Commit LLM-extracted entities and relations for a chunk.

        Guarantees:
          - Entities are resolved (deduplicated via canonical name) and
            persisted to Graph.
          - Relations are resolved using local_ref → persistent entity ID
            mapping and persisted as edges.
          - Evidence records are created linking the chunk to all produced
            entities and edges.
          - The queue item transitions to COMPLETED.

        Non-guarantees:
          - Entity deduplication strategy (exact match, fuzzy, embedding)
            is implementation-defined.

        Side effects:
          - Writes ``enrich_*`` tables AND (via Graph) ``graph_*`` tables.

        Raises:
          - ``LookupError`` if chunk_id is not in IN_PROGRESS state.
          - ``ValueError`` if local_ref values in relations don't match
            any entity in the submitted batch.
        """
        ...

    def mark_failed(self, chunk_id: str, error: str) -> EnrichmentQueueItem:
        """Record a processing failure for a chunk.

        Guarantees:
          - Increments attempts counter.
          - If attempts >= max_retries, transitions to FAILED permanently.
          - Otherwise, transitions back to PENDING for retry.

        Non-guarantees:
          - Retry backoff is implementation-defined.

        Side effects:
          - Writes only ``enrich_*`` tables.

        Raises:
          - ``LookupError`` if chunk_id is not in IN_PROGRESS state.
        """
        ...

    # --- Suggestion ---

    def suggest_intra_doc_edges(
        self,
        document_id: str,
    ) -> tuple[SuggestedEdge, ...]:
        """Suggest edges between entities found within the same document.

        Guarantees:
          - Returns suggestions only — does NOT write to Graph.
          - Suggestions are based on co-occurrence and entity proximity
            within the document's chunks.
          - Each suggestion includes a confidence score and reason.

        Non-guarantees:
          - Suggestion algorithm (co-occurrence, embedding similarity,
            LLM re-check) is implementation-defined.

        Side effects:
          - None (read-only).

        Raises:
          - ``LookupError`` if document_id is unknown.
        """
        ...

    # --- Purge ---

    def purge_source(self, source_id: str) -> EnrichmentPurgeResult:
        """Remove all Enrichment-owned data for a source.

        Guarantees:
          - Removes queue items and extraction records for the source.
          - Idempotent.

        Non-guarantees:
          - Does not remove Graph evidence — that is handled separately
            via Graph.invalidate_evidence_by_chunks.

        Side effects:
          - Writes only ``enrich_*`` tables (deletions).

        Raises:
          - Never raises for unknown source_id (returns empty result).
        """
        ...

    # --- Stats ---

    def stats(self) -> EnrichmentStats:
        """Return counts owned by this module.

        Guarantees:
          - Reflects current enrich_* table state.

        Non-guarantees:
          - Staleness tolerance is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises.
        """
        ...
