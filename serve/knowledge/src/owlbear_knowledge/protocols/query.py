"""QueryService Protocol — Query module public surface.

Module responsibility: orchestrate the read path. Hybrid search via
ContentStore, optional graph augmentation via GraphStore, provenance
assembly via SourceStore, context rendering for agent consumption, and
aggregate stats composition.

Owns NO tables. Pure coordinator (CP4 + CP12).
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed by Pydantic at runtime
from typing import Protocol, runtime_checkable

from pydantic import Field

from owlbear_knowledge.protocols.common import BoundaryModel, Metadata
from owlbear_knowledge.protocols.content import ContentSearchResult, ContentStats  # noqa: TC001
from owlbear_knowledge.protocols.enrichment import EnrichmentStats  # noqa: TC001
from owlbear_knowledge.protocols.graph import EntityRecord, GraphStats, RelationKind, TraversalPath  # noqa: TC001
from owlbear_knowledge.protocols.sources import SourceRecord, SourceStats  # noqa: TC001


# ---------------------------------------------------------------------------
# Boundary types — Request
# ---------------------------------------------------------------------------


class QueryRequest(BoundaryModel):
    """Semantic search request accepted by Query."""

    text: str
    scopes: tuple[str, ...] = Field(default_factory=tuple)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    top_k: int = Field(default=5, ge=1, le=100)
    include_graph: bool = True
    max_graph_depth: int = Field(default=3, ge=1, le=6)
    metadata: Metadata = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Boundary types — Response
# ---------------------------------------------------------------------------


class Provenance(BoundaryModel):
    """Source and chunk attribution for a query result."""

    source_id: str
    source_name: str
    document_id: str
    chunk_id: str
    exact_text: str
    uri: str | None = None
    section_path: tuple[str, ...] = Field(default_factory=tuple)


class GraphContext(BoundaryModel):
    """Graph augmentation attached to one query result."""

    entities: tuple[EntityRecord, ...] = Field(default_factory=tuple)
    paths: tuple[TraversalPath, ...] = Field(default_factory=tuple)


class QueryResult(BoundaryModel):
    """One composed read-path result."""

    content: ContentSearchResult
    source: SourceRecord | None = None
    provenance: Provenance
    graph: GraphContext = Field(default_factory=GraphContext)
    score: float = Field(ge=0.0)


class QueryResponse(BoundaryModel):
    """Full read-path response."""

    request: QueryRequest
    results: tuple[QueryResult, ...]


class QueryContextRequest(BoundaryModel):
    """Request to render search results as agent prompt context."""

    response: QueryResponse
    max_chars: int = Field(default=6000, ge=500)


class QueryContext(BoundaryModel):
    """Rendered context bundle for agent consumption."""

    text: str
    results: tuple[QueryResult, ...]
    truncated: bool = False


# ---------------------------------------------------------------------------
# Boundary types — Stats
# ---------------------------------------------------------------------------


class AggregateStats(BoundaryModel):
    """Composed stats from all knowledge modules."""

    sources: SourceStats
    content: ContentStats
    graph: GraphStats
    enrichment: EnrichmentStats
    generated_at: datetime


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class QueryService(Protocol):
    """Public contract for the Query module.

    Storage ownership: Query owns NO tables. It composes Content search,
    Graph traversal, and Source attribution through their public protocols.

    Dependencies: ContentStore, GraphStore, SourceStore, EnrichmentEngine
    (stats only).
    """

    async def search(self, request: QueryRequest) -> QueryResponse:
        """Hybrid search with graph augmentation and provenance.

        Sequence:
          1. ContentStore.search for hybrid hits.
          2. For each hit, look up source_name via SourceStore.get_source
             (provenance assembly).
          3. If include_graph: for each hit, find entities whose evidence
             cites the hit's chunk and include up to max_graph_depth-hop
             neighbours via GraphStore.traverse.

        Guarantees:
          - Result text is verbatim from the stored chunk (no rewriting).
          - Every result has provenance populated with source_name.
          - If include_graph=False: graph field is empty on every result.
          - Result count <= request.top_k.

        Non-guarantees:
          - Graph augmentation strategy (hops, ranking, entity selection)
            may evolve. Callers MUST NOT depend on specific traversal
            depth or path ordering.
          - Scoring formula is implementation-defined.

        Side effects:
          - None (read-only composition).

        Raises:
          - ``ValueError`` if request.text is empty.
        """
        ...

    def traverse_from_entity(
        self,
        entity_name: str,
        *,
        relations: tuple[RelationKind, ...] = (),
        max_depth: int = 2,
        scope: str | None = None,
    ) -> tuple[TraversalPath, ...]:
        """Relationship-aware lookup starting from an entity name.

        Used for the demand scenarios (ISMS → Standards → Approvals;
        access rights → tool; PDS → CI). With canonical identity (CP1),
        name resolution is direct: looks up entity by
        canonicalize_name(entity_name) and traverses outward.

        Sequence:
          1. find_entities(EntityQuery(canonical_name=...)) via GraphStore.
          2. For each match: GraphStore.traverse with the given params.
          3. Concatenate and return paths.

        Guarantees:
          - Empty result if no entity matches.
          - Direct resolution via canonical identity (no SAME_AS chasing).

        Non-guarantees:
          - Path ordering within results is implementation-defined.

        Side effects:
          - None (read-only composition).

        Raises:
          - Never raises for unknown entity names (returns empty tuple).
        """
        ...

    def render_context(self, request: QueryContextRequest) -> QueryContext:
        """Render query results for agent prompt use.

        Guarantees:
          - Rendered context is derived only from the provided
            QueryResponse.
          - Includes provenance sufficient for audit.
          - If text exceeds max_chars, truncated=True and text is cut at
            a result boundary (no mid-result truncation).

        Non-guarantees:
          - Formatting style and truncation strategy are implementation
            details.

        Side effects:
          - None.

        Raises:
          - Never raises.
        """
        ...

    def stats(self) -> AggregateStats:
        """Compose per-module stats (serves MCP get_stats tool).

        Sequence:
          1. SourceStore.stats()
          2. ContentStore.stats()
          3. GraphStore.stats()
          4. EnrichmentEngine.stats()

        Guarantees:
          - generated_at is the wall-clock time of composition.

        Non-guarantees:
          - Implementations may tolerate a few seconds of staleness
            across the four sub-calls.

        Side effects:
          - None (read-only composition).

        Raises:
          - Never raises (sub-module stats never raise).
        """
        ...
