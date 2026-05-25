"""GraphStore Protocol — Graph module public surface.

Module responsibility: typed entity/edge knowledge graph with evidence
tracking, alias resolution, and adjacency queries. Owns tables ``graph_*``.

Has zero dependencies on other knowledge modules.

Table ownership: only Graph writes ``graph_*`` tables.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field, model_validator

from owlbear_knowledge.protocols.common import (
    BoundaryModel,
    EntityType,
    Metadata,
    RelationType,
    canonicalize_name,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EvidenceClaimType(StrEnum):
    """Discriminator for graph evidence provenance.

    Used by claims_for_chunk and evidence invalidation to distinguish
    entity existence claims from edge relationship claims.
    """

    ENTITY = "entity"
    EDGE = "edge"


class TraversalDirection(StrEnum):
    """Direction filter for adjacency queries."""

    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


# ---------------------------------------------------------------------------
# Entity types
# ---------------------------------------------------------------------------


class EntityInput(BoundaryModel):
    """Entity upsert request accepted by GraphStore.

    Names are automatically canonicalized (lowercase, stripped, trailing
    punctuation removed) before storage.
    """

    name: str
    entity_type: EntityType
    description: str = ""
    metadata: Metadata = Field(default_factory=dict)


class EntityRecord(BoundaryModel):
    """Persisted entity record returned by GraphStore."""

    id: str
    name: str
    canonical_name: str
    entity_type: EntityType
    description: str = ""
    alias_names: tuple[str, ...] = Field(default_factory=tuple)
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------


class EdgeInput(BoundaryModel):
    """Edge upsert request accepted by GraphStore.

    Relationship types are drawn from the project-maintained vocabulary
    (RelationType enum). SAME_AS is not a valid edge type — use
    add_alias for identity merging.
    """

    source_entity_id: str
    target_entity_id: str
    relation_type: RelationType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)


class EdgeRecord(BoundaryModel):
    """Persisted edge record returned by GraphStore."""

    id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: RelationType
    weight: float = Field(ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Evidence types
# ---------------------------------------------------------------------------


class EvidenceInput(BoundaryModel):
    """Evidence claim linking a chunk to a graph element.

    Exactly one of entity_id or edge_id must be set, matching claim_type:
      - ENTITY → entity_id required, edge_id must be None
      - EDGE → edge_id required, entity_id must be None
    """

    chunk_id: str
    claim_type: EvidenceClaimType
    entity_id: str | None = None
    edge_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_claim_xor(self) -> "EvidenceInput":
        if self.claim_type == EvidenceClaimType.ENTITY:
            if not self.entity_id or self.edge_id:
                msg = "ENTITY claim requires entity_id and no edge_id"
                raise ValueError(msg)
        else:
            if not self.edge_id or self.entity_id:
                msg = "EDGE claim requires edge_id and no entity_id"
                raise ValueError(msg)
        return self


class EvidenceRecord(BoundaryModel):
    """Persisted evidence record."""

    id: str
    chunk_id: str
    claim_type: EvidenceClaimType
    entity_id: str | None = None
    edge_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime


class ChunkClaims(BoundaryModel):
    """All graph claims derived from a single chunk.

    Returned by claims_for_chunk for targeted invalidation and cascade.
    """

    chunk_id: str
    entity_ids: tuple[str, ...] = Field(default_factory=tuple)
    edge_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Alias types (R33 — Graph-owned identity merging)
# ---------------------------------------------------------------------------


class EntityAliasInput(BoundaryModel):
    """Request to register an alternate name for an entity.

    The alias is canonicalized the same way as entity names. The target
    entity must already exist.
    """

    entity_id: str
    alias_name: str


class EntityAliasRecord(BoundaryModel):
    """Persisted alias record."""

    id: str
    entity_id: str
    alias_name: str
    canonical_alias: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Query types
# ---------------------------------------------------------------------------


class EntityQuery(BoundaryModel):
    """Query to find entities by name or type.

    Name lookups use canonical matching (case-insensitive, punctuation
    stripped) and include alias resolution.
    """

    name: str | None = None
    entity_type: EntityType | None = None
    limit: int = Field(default=50, ge=1, le=500)


class AdjacencyQuery(BoundaryModel):
    """Return edges adjacent to a given entity."""

    entity_id: str
    relation_types: tuple[RelationType, ...] = Field(default_factory=tuple)
    direction: TraversalDirection = TraversalDirection.BOTH
    limit: int = Field(default=50, ge=1, le=500)


class TraversalQuery(BoundaryModel):
    """Multi-hop graph traversal from a seed entity."""

    entity_id: str
    max_hops: int = Field(default=2, ge=1, le=5)
    relation_types: tuple[RelationType, ...] = Field(default_factory=tuple)
    limit: int = Field(default=100, ge=1, le=1000)


class TraversalResult(BoundaryModel):
    """Result of a multi-hop graph traversal."""

    entities: tuple[EntityRecord, ...] = Field(default_factory=tuple)
    edges: tuple[EdgeRecord, ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Invalidation types
# ---------------------------------------------------------------------------


class EvidenceInvalidationResult(BoundaryModel):
    """Result of bulk evidence invalidation (R31)."""

    invalidated_evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    orphaned_entity_ids: tuple[str, ...] = Field(default_factory=tuple)
    orphaned_edge_ids: tuple[str, ...] = Field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class GraphStats(BoundaryModel):
    """Counts owned by the Graph module."""

    entities: int = 0
    edges: int = 0
    evidence_claims: int = 0
    aliases: int = 0


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class GraphStore(Protocol):
    """Public contract for the Graph module.

    Storage ownership: only Graph writes ``graph_*`` tables.
    Dependency rule: Graph imports no other knowledge module internals.
    """

    # --- Entity operations ---

    def upsert_entity(self, entity: EntityInput) -> EntityRecord:
        """Create or update an entity.

        Guarantees:
          - Names are canonicalized (lowercased, stripped, trailing
            punctuation removed) for duplicate detection.
          - Upsert semantic: existing entity with same canonical name +
            type is updated; otherwise a new entity is created.

        Non-guarantees:
          - Entity IDs are opaque.

        Side effects:
          - Writes only ``graph_*`` tables.

        Raises:
          - ``ValueError`` if name is empty after canonicalization.
        """
        ...

    def get_entity(self, entity_id: str) -> EntityRecord | None:
        """Return one entity by ID, or None if not found.

        Guarantees:
          - Returns the entity with its current alias_names.

        Non-guarantees:
          - None.

        Side effects:
          - None.

        Raises:
          - Never raises for unknown IDs (returns None).
        """
        ...

    def find_entities(self, query: EntityQuery) -> tuple[EntityRecord, ...]:
        """Search entities by name and/or type.

        Guarantees:
          - Name lookups are canonical (case-insensitive, punctuation-
            stripped) and include alias resolution.
          - Returns up to query.limit results.

        Non-guarantees:
          - Ordering is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises (returns empty tuple for no matches).
        """
        ...

    # --- Edge operations ---

    def upsert_edge(self, edge: EdgeInput) -> EdgeRecord:
        """Create or update an edge between two entities.

        Guarantees:
          - Upsert semantic: existing edge with same source + target +
            relation is updated; otherwise a new edge is created.
          - SAME_AS is not a valid edge type; use add_alias for identity
            merging.

        Non-guarantees:
          - Edge IDs are opaque.

        Side effects:
          - Writes only ``graph_*`` tables.

        Raises:
          - ``ValueError`` if source or target entity does not exist.
          - ``ValueError`` if relation_type is SAME_AS.
        """
        ...

    def get_adjacent(self, query: AdjacencyQuery) -> tuple[EdgeRecord, ...]:
        """Return edges adjacent to an entity.

        Guarantees:
          - Direction filtering (outgoing/incoming/both) is applied.
          - Relation type filtering is applied when non-empty.

        Non-guarantees:
          - Ordering is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises for unknown entity_id (returns empty tuple).
        """
        ...

    def traverse(self, query: TraversalQuery) -> TraversalResult:
        """Multi-hop BFS/DFS traversal from a seed entity.

        Guarantees:
          - Explores up to query.max_hops hops.
          - Total result size <= query.limit.
          - No duplicate entities or edges in the result.

        Non-guarantees:
          - Traversal algorithm (BFS vs DFS), tie-breaking, and pruning
            strategy are implementation details.

        Side effects:
          - None.

        Raises:
          - ``LookupError`` if the seed entity_id does not exist.
        """
        ...

    # --- Evidence operations ---

    def add_evidence(self, evidence: EvidenceInput) -> EvidenceRecord:
        """Record an evidence claim linking a chunk to a graph element.

        Guarantees:
          - Exactly one of entity_id or edge_id must be set (matching
            claim_type).

        Non-guarantees:
          - Evidence ID format is opaque.

        Side effects:
          - Writes only ``graph_*`` tables.

        Raises:
          - ``ValueError`` if both entity_id and edge_id are set/unset,
            or if claim_type doesn't match the set field.
        """
        ...

    def claims_for_chunk(self, chunk_id: str) -> ChunkClaims:
        """Return all graph claims derived from a chunk.

        Guarantees:
          - Returns entity IDs, edge IDs, and evidence IDs that trace
            back to the given chunk_id.
          - Returns empty ChunkClaims for unknown chunk_id.

        Non-guarantees:
          - Does not resolve whether entities/edges have other evidence.

        Side effects:
          - None.

        Raises:
          - Never raises for unknown chunk_id.
        """
        ...

    def invalidate_evidence_by_chunks(
        self,
        chunk_ids: tuple[str, ...],
    ) -> EvidenceInvalidationResult:
        """Remove evidence claims for the given chunks and clean up orphans.

        Guarantees:
          - All evidence records referencing any of the provided chunk_ids
            are deleted.
          - Entities and edges that lose ALL evidence are reported as
            orphaned (and deleted from graph_* tables).
          - Idempotent: already-absent chunk_ids are silently ignored.

        Non-guarantees:
          - Whether orphan detection is immediate or batched is
            implementation-defined.

        Side effects:
          - Writes only ``graph_*`` tables (deletions).

        Raises:
          - Never raises (idempotent).
        """
        ...

    # --- Alias operations (R33) ---

    def add_alias(self, alias: EntityAliasInput) -> EntityAliasRecord:
        """Register an alternate name for an entity.

        Guarantees:
          - The alias is canonicalized identically to entity names.
          - find_entities resolves aliases transparently.
          - Duplicate aliases (same canonical form + entity) are
            idempotent (returns existing record).

        Non-guarantees:
          - Alias IDs are opaque.

        Side effects:
          - Writes only ``graph_*`` tables.

        Raises:
          - ``LookupError`` if entity_id does not exist.
          - ``ValueError`` if alias_name is empty after canonicalization
            or conflicts with a different entity's canonical name.
        """
        ...

    # --- Stats ---

    def stats(self) -> GraphStats:
        """Return counts owned by this module.

        Guarantees:
          - Reflects current graph_* table state.

        Non-guarantees:
          - Staleness tolerance is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises.
        """
        ...
