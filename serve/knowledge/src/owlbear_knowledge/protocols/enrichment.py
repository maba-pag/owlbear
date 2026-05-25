"""EnrichmentEngine Protocol — Enrichment module public surface.

Module responsibility: per-chunk entity/edge extraction state machine and
per-document intra-doc edge inference. Owns table ``enrich_chunk_state``.

Dependencies: writes via GraphStore, reads chunks via ContentStore. Does
NOT touch ``content_*`` or ``graph_*`` tables directly.

Execution model (CP10 — agent-external LLM):
  - Agents call next_pending_batch to claim chunks.
  - The agent performs LLM extraction itself (out-of-process).
  - The agent calls store_extraction with results to persist.
  - Per-document edge inference (Phase 2) runs in-process via
    infer_intra_doc_edges once all chunks of a document are DONE.

State machine::

    PENDING ──(next_pending_batch)──> CLAIMED ──(store_extraction)──> DONE
       ↑                                 │
       │                                 ├─(store_extraction error)──> FAILED
       │                                 │
       └─(reset_failed) <────────────────┘
       ↑
       └─(claim expiry after TTL) <────── CLAIMED

    DONE ──(mark_stale, chunk replaced)──> STALE
    STALE ──(next_pending_batch)──> CLAIMED
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata
from owlbear_knowledge.protocols.graph import EdgeInput, EntityInput  # noqa: TC001


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EnrichmentState(StrEnum):
    """Extraction lifecycle states owned by Enrichment."""

    PENDING = "pending"
    CLAIMED = "claimed"
    DONE = "done"
    FAILED = "failed"
    STALE = "stale"


# ---------------------------------------------------------------------------
# Boundary types
# ---------------------------------------------------------------------------


class ClaimedChunk(BoundaryModel):
    """Chunk claimed for extraction, returned by next_pending_batch."""

    chunk_id: str
    document_id: str
    source_id: str
    text: str
    scope: str = "global"
    claim_token: str
    claimed_at: datetime
    expires_at: datetime
    attempt: int = Field(default=1, ge=1)
    metadata: Metadata = Field(default_factory=dict)


class StoreExtractionResult(BoundaryModel):
    """Result of persisting extraction output for one chunk."""

    chunk_id: str
    state: EnrichmentState
    entity_ids: tuple[str, ...] = Field(default_factory=tuple)
    edge_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    error: str | None = None


class EdgeInferenceReport(BoundaryModel):
    """Result of per-document intra-doc edge inference (Phase 2)."""

    document_id: str
    edges_created: int = 0
    edge_ids: tuple[str, ...] = Field(default_factory=tuple)


class ResetResult(BoundaryModel):
    """Result of resetting failed or stale chunks."""

    chunks_reset: int = 0
    chunk_ids: tuple[str, ...] = Field(default_factory=tuple)


class EnrichmentPurgeResult(BoundaryModel):
    """Result of purging Enrichment-owned state for a source."""

    source_id: str
    chunks_purged: int = 0
    chunk_ids: tuple[str, ...] = Field(default_factory=tuple)


class EnrichmentStats(BoundaryModel):
    """Counts owned by the Enrichment module."""

    pending: int = 0
    claimed: int = 0
    done: int = 0
    failed: int = 0
    stale: int = 0


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EnrichmentEngine(Protocol):
    """Public contract for the Enrichment module (CP10).

    No consolidation methods — canonical identity in GraphStore obviates
    the historical consolidation pipeline (CP1).

    Storage ownership: only Enrichment writes ``enrich_*`` tables.
    Enrichment writes graph facts only through the public GraphStore
    protocol and reads chunks only through the public ContentStore
    protocol.
    """

    # ----- Phase 1: per-chunk extraction (agent-driven) -------------------

    def next_pending_batch(
        self,
        *,
        limit: int = 10,
        scopes: tuple[str, ...] = (),
        claim_ttl_seconds: int = 600,
    ) -> tuple[ClaimedChunk, ...]:
        """Atomically claim up to ``limit`` chunks for extraction.

        Selects chunks in PENDING or STALE state (and any CLAIMED chunks
        whose claim has expired beyond claim_ttl_seconds). Transitions
        them to CLAIMED with a fresh claim_token and timestamps.

        Guarantees:
          - Returned chunks are mutually exclusive across concurrent calls
            (atomicity via SQLite transaction).
          - Each returned ClaimedChunk carries a non-empty claim_token.
          - If scopes is non-empty, every returned chunk's scope is in
            that tuple.
          - Returns empty tuple when no chunks are available.

        Non-guarantees:
          - Chunk ordering within the batch is implementation-defined.

        Side effects:
          - Updates ``enrich_chunk_state``: state→CLAIMED, claim_token,
            claimed_at, expires_at.

        Raises:
          - ``ValueError`` if limit < 1 or claim_ttl_seconds < 60.
        """
        ...

    def store_extraction(
        self,
        chunk_id: str,
        claim_token: str,
        entities: tuple[EntityInput, ...],
        edges: tuple[EdgeInput, ...],
    ) -> StoreExtractionResult:
        """Persist extraction results for a previously-claimed chunk.

        Sequence (transactional where possible):
          1. Verify claim_token matches the current claim.
          2. For each EntityInput: GraphStore.upsert_entity, then
             GraphStore.add_evidence with claim_type="entity".
          3. For each EdgeInput: GraphStore.upsert_edge, then
             GraphStore.add_evidence with claim_type="edge".
          4. Transition chunk state CLAIMED → DONE.

        Guarantees:
          - On success: state == DONE and every returned ID is persisted.
          - All-or-nothing: any failure leaves state in {CLAIMED, FAILED};
            no partial writes to graph_*.

        Non-guarantees:
          - Entity merge strategy during upsert is Graph's responsibility.

        Side effects:
          - Writes to ``enrich_chunk_state`` and (via GraphStore) to
            ``graph_entities``, ``graph_edges``, ``graph_evidence``.

        Raises:
          - ``PermissionError`` if claim_token does not match (expired or
            taken by another worker).
          - ``ValueError`` if any edge references an entity that is neither
            in entities nor pre-existing in Graph.
        """
        ...

    # ----- Phase 2: per-document intra-doc inference ----------------------

    def infer_intra_doc_edges(self, document_id: str) -> EdgeInferenceReport:
        """Infer structural edges between entities of a single document.

        Examines entities already extracted from document_id and infers
        edges (e.g. COMPONENT_OF, GOVERNED_BY) based on entity types and
        co-occurrence. Inferred edges carry weight=0.5 and
        metadata["source"] = "intra_doc_inference".

        Should be called after all chunks of the document are in DONE
        state. Calling earlier yields a partial report.

        Guarantees:
          - Idempotent: re-running does not duplicate edges (edge identity
            via GraphStore.upsert_edge).
          - Inferred edges always carry the marker
            metadata["source"] == "intra_doc_inference".

        Non-guarantees:
          - Inference heuristics and edge type selection are implementation
            details.

        Side effects:
          - Via GraphStore: writes ``graph_edges`` and ``graph_evidence``.

        Raises:
          - Never raises for unknown document_id (returns zero-count
            report).
        """
        ...

    # ----- Cascade & recovery ---------------------------------------------

    def mark_stale(self, chunk_ids: tuple[str, ...]) -> int:
        """Mark chunks as STALE so they will be re-extracted.

        Called by Ingest immediately after Content.ingest reports
        replaced_chunk_ids. The next next_pending_batch will pick these up.

        Guarantees:
          - Unknown or never-extracted chunk IDs are silently ignored.
          - Returns the number of chunks whose state was changed.
          - Does NOT delete previously-extracted entities/edges/evidence.

        Non-guarantees:
          - Re-extraction timing depends on next_pending_batch calls.

        Side effects:
          - Writes to ``enrich_chunk_state``.

        Raises:
          - Never raises (silently ignores unknown IDs).
        """
        ...

    def reset_failed(
        self,
        chunk_ids: tuple[str, ...] | None = None,
        *,
        limit: int | None = None,
        scopes: tuple[str, ...] = (),
    ) -> ResetResult:
        """Reset FAILED chunks back to PENDING for retry.

        If chunk_ids is given, resets exactly those (skipping non-failed).
        Otherwise resets up to limit failed chunks in scopes.

        Guarantees:
          - Cleared error field after reset.
          - Returns count and IDs of chunks reset.

        Non-guarantees:
          - Selection order when using limit is implementation-defined.

        Side effects:
          - Writes to ``enrich_chunk_state``.

        Raises:
          - ``ValueError`` if both chunk_ids and limit are None.
        """
        ...

    def purge_source(self, source_id: str) -> EnrichmentPurgeResult:
        """Remove Enrichment-owned state for a purged source.

        Cleans up enrich_chunk_state rows associated with the source.
        Does NOT delete Graph records — that is Graph's responsibility
        via purge_evidence_by_source.

        Guarantees:
          - Only enrich_* state is removed.
          - Idempotent: re-running returns zero counts.

        Non-guarantees:
          - Does not verify source existence (Sources owns that).

        Side effects:
          - Writes to ``enrich_chunk_state`` (deletion).

        Raises:
          - Never raises for unknown source_id (returns zero-count result).
        """
        ...

    # ----- Stats ----------------------------------------------------------

    def stats(self) -> EnrichmentStats:
        """Return counts owned by this module.

        Guarantees:
          - Reflects current enrich_chunk_state distribution.

        Non-guarantees:
          - Staleness tolerance is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises.
        """
        ...
