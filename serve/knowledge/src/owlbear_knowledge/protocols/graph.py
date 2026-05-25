"""GraphStore Protocol — Graph module public surface.

Module responsibility: typed entity/edge CRUD, evidence tracking (CP1 —
per-document provenance via EvidenceRecord), adjacency queries, and
multi-hop traversal. Owns tables ``graph_entities``, ``graph_edges``,
``graph_evidence``.

Has zero dependencies on other knowledge modules.

The Graph module does NOT decide which entities or edges to create — that
is the Enrichment module's job. Graph is a typed, query-friendly store
with canonical-identity semantics.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata


# ---------------------------------------------------------------------------
# Enums (demand-driven: only types required by current scenarios)
# ---------------------------------------------------------------------------


class EntityKind(StrEnum):
    """Stable entity categories for cross-source knowledge chains.

    Additive: new values may be added without breaking existing code.
    """

    ACCESS_RIGHT = "access_right"
    COMPONENT = "component"
    CONCEPT = "concept"
    CONTROL = "control"
    POLICY = "policy"
    PROCEDURE = "procedure"
    SERVICE = "service"
    STANDARD = "standard"
    SYSTEM = "system"
    TEAM = "team"
    TOOL = "tool"
    UI_OPTION = "ui_option"


class RelationKind(StrEnum):
    """Stable relationship categories used by traversal.

    Additive: new values may be added without breaking existing code.
    SAME_AS is intentionally excluded — canonical identity (CP1) handles
    entity deduplication without relationship-based merging.
    """

    ALIGNS_WITH = "aligns_with"
    APPROVED_BY = "approved_by"
    AVAILABLE_IN = "available_in"
    COMPONENT_OF = "component_of"
    DEFINES = "defines"
    DEPENDS_ON = "depends_on"
    GOVERNED_BY = "governed_by"
    HAS_PROCEDURE = "has_procedure"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    REQUIRES = "requires"
    REQUIRES_ACCESS_RIGHT = "requires_access_right"
    SUPPORTS = "supports"


# ---------------------------------------------------------------------------
# Boundary types — Entity
# ---------------------------------------------------------------------------


class EntityInput(BoundaryModel):
    """Entity write request accepted by Graph."""

    name: str
    kind: EntityKind
    scope: str = "global"
    description: str = ""
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)


class EntityRecord(BoundaryModel):
    """Persisted entity record returned by Graph."""

    id: str
    name: str
    canonical_name: str
    kind: EntityKind
    scope: str = "global"
    description: str = ""
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Boundary types — Edge
# ---------------------------------------------------------------------------


class EdgeInput(BoundaryModel):
    """Edge write request accepted by Graph."""

    source_entity_id: str
    target_entity_id: str
    relation: RelationKind
    scope: str = "global"
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)


class EdgeRecord(BoundaryModel):
    """Persisted edge record returned by Graph."""

    id: str
    source_entity_id: str
    target_entity_id: str
    relation: RelationKind
    scope: str = "global"
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Boundary types — Evidence (CP1: separate provenance tracking)
# ---------------------------------------------------------------------------


class EvidenceInput(BoundaryModel):
    """Evidence write request linking a graph record to a content chunk."""

    claim_type: str  # "entity" or "edge"
    claim_id: str  # entity_id or edge_id
    chunk_id: str
    source_id: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)


class EvidenceRecord(BoundaryModel):
    """Persisted evidence record."""

    id: str
    claim_type: str
    claim_id: str
    chunk_id: str
    source_id: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Metadata = Field(default_factory=dict)
    created_at: datetime


# ---------------------------------------------------------------------------
# Boundary types — Query models
# ---------------------------------------------------------------------------


class EntityQuery(BoundaryModel):
    """Entity lookup request."""

    text: str | None = None
    canonical_name: str | None = None
    kind: EntityKind | None = None
    scope: str | None = None
    source_id: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class AdjacencyQuery(BoundaryModel):
    """Direct-neighbor graph query (1-hop)."""

    entity_id: str
    relations: tuple[RelationKind, ...] = Field(default_factory=tuple)
    scope: str | None = None
    include_incoming: bool = True
    include_outgoing: bool = True
    limit: int = Field(default=50, ge=1, le=200)


class TraversalQuery(BoundaryModel):
    """Bounded multi-hop graph traversal request."""

    start_entity_ids: tuple[str, ...]
    target_entity_ids: tuple[str, ...] = Field(default_factory=tuple)
    relations: tuple[RelationKind, ...] = Field(default_factory=tuple)
    scope: str | None = None
    max_depth: int = Field(default=3, ge=1, le=6)
    limit: int = Field(default=20, ge=1, le=100)


class TraversalPath(BoundaryModel):
    """One graph path returned by traversal."""

    entities: tuple[EntityRecord, ...]
    edges: tuple[EdgeRecord, ...]
    score: float = Field(default=1.0, ge=0.0)


# ---------------------------------------------------------------------------
# Boundary types — Results
# ---------------------------------------------------------------------------


class PurgeEvidenceResult(BoundaryModel):
    """Result of evidence purge and orphan cascade."""

    source_id: str
    evidence_removed: int = 0
    entities_removed: int = 0
    edges_removed: int = 0


class GraphStats(BoundaryModel):
    """Counts owned by the Graph module."""

    entities: int = 0
    edges: int = 0
    evidence: int = 0


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class GraphStore(Protocol):
    """Public contract for the Graph module.

    Storage ownership: only Graph writes ``graph_entities``,
    ``graph_edges``, ``graph_evidence`` tables.
    Dependency rule: Graph imports no other knowledge module internals.
    """

    def upsert_entity(self, entity: EntityInput) -> EntityRecord:
        """Insert or update an entity by canonical identity (CP1).

        Identity tuple: (canonicalize_name(entity.name), entity.kind,
        entity.scope). Two inputs with the same tuple refer to the same
        entity row.

        Merge rules on existing-row update:
          - name: keep first non-empty raw form.
          - description: last-non-empty-wins.
          - importance: max(existing, input).
          - metadata: shallow union, input keys override on collision.

        Guarantees:
          - Returned EntityRecord.id is stable across upserts of the same
            identity tuple.
          - EntityRecord.canonical_name equals
            canonicalize_name(returned.name).
          - created_at is set on first insert and never changes;
            updated_at refreshes on every call.

        Non-guarantees:
          - ID format is implementation-defined.

        Side effects:
          - Writes one row in ``graph_entities``. Does NOT add evidence —
            callers MUST call add_evidence separately to record provenance.

        Raises:
          - ``ValueError`` if entity.name is empty.
        """
        ...

    def upsert_edge(self, edge: EdgeInput) -> EdgeRecord:
        """Insert or update an edge between two existing entities.

        Identity tuple: (source_entity_id, target_entity_id, relation,
        scope). Re-upserting the same tuple updates weight and metadata
        without creating a duplicate row.

        Guarantees:
          - Returned EdgeRecord.id is stable across upserts of the same
            identity tuple.

        Non-guarantees:
          - Edge ordering within a scope is implementation-defined.

        Side effects:
          - Writes one row in ``graph_edges``. Does NOT add evidence.

        Raises:
          - ``LookupError`` if either source_entity_id or target_entity_id
            does not exist in graph_entities.
          - ``ValueError`` if relation is not in RelationKind.
        """
        ...

    def add_evidence(self, evidence: EvidenceInput) -> EvidenceRecord:
        """Record provenance for an entity or edge (CP1).

        Guarantees:
          - Returns a record with a freshly generated ID.
          - source_id is denormalised for fast cascade in
            purge_evidence_by_source.
          - Idempotent on (claim_type, claim_id, chunk_id): re-adding the
            same triple updates confidence instead of inserting a duplicate.

        Non-guarantees:
          - Evidence ordering is implementation-defined.

        Side effects:
          - Writes one row in ``graph_evidence``.

        Raises:
          - ``LookupError`` if the referenced entity/edge does not exist.
        """
        ...

    def get_entity(self, entity_id: str) -> EntityRecord | None:
        """Return the entity by ID, or None if not found.

        Guarantees:
          - Returns None for unknown IDs.

        Non-guarantees:
          - ID format is opaque.

        Side effects:
          - None.

        Raises:
          - Never raises for unknown IDs (returns None).
        """
        ...

    def find_entities(self, query: EntityQuery) -> tuple[EntityRecord, ...]:
        """Find entities matching the query.

        Guarantees:
          - Filter dimensions combine with AND semantics.
          - If canonical_name is set, exact match on the canonical form.
          - Results deterministically ordered by (canonical_name, id).
          - Result count <= query.limit.

        Non-guarantees:
          - Text-based fuzzy matching strategy is implementation-defined.

        Side effects:
          - None.

        Raises:
          - Never raises (returns empty tuple for no matches).
        """
        ...

    def adjacent(self, query: AdjacencyQuery) -> tuple[EdgeRecord, ...]:
        """Return direct graph neighbours as edges (1-hop).

        Guarantees:
          - Respects direction flags (incoming/outgoing) and relation
            filters.
          - Result count <= query.limit.

        Non-guarantees:
          - Result ordering is implementation-defined.

        Side effects:
          - None.

        Raises:
          - ``LookupError`` if query.entity_id does not exist.
        """
        ...

    def traverse(self, query: TraversalQuery) -> tuple[TraversalPath, ...]:
        """Walk edges from start entities up to max_depth hops.

        Guarantees:
          - Every returned TraversalPath begins with a start entity.
          - Path length (edges) is between 1 and max_depth.
          - If relations is set, every edge in every path has a relation
            in that tuple.
          - If scope is set, all visited entities/edges share that scope.
          - Cycles are broken: no entity appears twice in a single path.
          - If target_entity_ids is set, only paths reaching a target are
            returned.
          - Result count <= query.limit.

        Non-guarantees:
          - Path ordering and completeness when results would exceed limit
            are implementation-defined.

        Side effects:
          - None.

        Raises:
          - ``LookupError`` if any start_entity_id does not exist.
        """
        ...

    def evidence_for(self, entity_id: str) -> tuple[EvidenceRecord, ...]:
        """List all evidence supporting an entity.

        Guarantees:
          - Ordered most recent first by created_at.

        Non-guarantees:
          - Evidence for edges is accessed via claim_type="edge" filter
            (implementation-defined query).

        Side effects:
          - None.

        Raises:
          - Never raises for unknown entity_id (returns empty tuple).
        """
        ...

    def purge_evidence_by_source(self, source_id: str) -> PurgeEvidenceResult:
        """Remove all evidence for a source and cascade-delete orphans.

        Cascade order:
          1. Delete graph_evidence rows matching source_id.
          2. Delete entities with zero remaining evidence (orphans).
          3. Delete edges whose endpoints were orphaned or whose own
             evidence is gone.

        Guarantees:
          - Idempotent: re-running on an already-purged source returns
            zero counts.
          - An entity with evidence from a different source survives.

        Non-guarantees:
          - Cascade timing (immediate vs deferred) is implementation-defined.

        Side effects:
          - Writes to ``graph_*`` tables (deletion). Does NOT touch
            ``content_*`` or ``enrich_*``.

        Raises:
          - Never raises for unknown source_id (returns zero-count result).
        """
        ...

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
