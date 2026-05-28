"""QueryFacade Protocol — Query module public surface.

Module responsibility: unified read-only entry point combining semantic
search, graph traversal, and context rendering. Owns no tables — reads
from Content and Graph.

The Query module does NOT exist as a writable store. It is a read facade
that assembles results from Content.search, Graph.traverse, and
Graph.find_entities into user-facing responses with provenance.

``QueryRequest.graph_hops`` is a facade hint that Query translates into
``TraversalQuery.max_hops`` on GraphStore. Query does not own a separate
depth concept (CP16).

``QueryRequest.scopes`` filters Content search hits only. Graph expansion
is scope-unaware by design — entities are global (CP1, D53).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import Field, model_validator

from owlbear_knowledge.protocols.common import BoundaryModel, EntityType, RelationType
from owlbear_knowledge.protocols.content import ContentChunk, ContentSearchResult
from owlbear_knowledge.protocols.graph import EntityRecord, TraversalResult

# ---------------------------------------------------------------------------
# Request types
# ---------------------------------------------------------------------------


class QueryRequest(BoundaryModel):
    """Combined search + traversal request.

    ``graph_hops`` is a facade hint translated to
    ``TraversalQuery.max_hops`` on GraphStore (CP16).
    ``scopes`` filters Content search only; graph expansion is global.
    """

    text: str
    top_k: int = Field(default=10, ge=1, le=100)
    scopes: tuple[str, ...] = Field(default_factory=tuple)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    include_graph: bool = True
    graph_hops: int = Field(default=2, ge=1, le=5)
    entity_types: tuple[EntityType, ...] = Field(default_factory=tuple)
    relation_types: tuple[RelationType, ...] = Field(default_factory=tuple)


class EntityLookupRequest(BoundaryModel):
    """Direct entity lookup + neighbourhood expansion.

    Exactly one of ``entity_id`` or ``entity_name`` must be provided.
    When using ``entity_name``, optionally supply ``entity_type`` to
    disambiguate homonyms.
    """

    entity_id: str | None = None
    entity_name: str | None = None
    entity_type: EntityType | None = None
    expand_hops: int = Field(default=1, ge=0, le=5)
    relation_types: tuple[RelationType, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _check_id_or_name(self) -> EntityLookupRequest:
        if self.entity_id and self.entity_name:
            msg = "Provide exactly one of entity_id or entity_name, not both"
            raise ValueError(msg)
        if not self.entity_id and not self.entity_name:
            msg = "Provide exactly one of entity_id or entity_name"
            raise ValueError(msg)
        return self


class ContextRenderRequest(BoundaryModel):
    """Request to render LLM context from a query result.

    max_chars controls output budget — see ARCHITECTURE.md for policy.
    """

    query_result: QueryResult | None = None
    entity_result: EntityLookupResult | None = None
    max_chars: int = Field(default=8000, ge=100, le=100_000)
    include_provenance: bool = True


# ---------------------------------------------------------------------------
# Provenance types
# ---------------------------------------------------------------------------


class Provenance(BoundaryModel):
    """Provenance record linking a search result to its source.

    ``exact_text`` is derived from the chunk's text field — it is NOT a
    separately stored matched_text column (R44). Implementations populate
    it from ContentChunk.text at query time.
    """

    chunk_id: str
    document_id: str
    source_id: str
    title: str
    uri: str | None = None
    exact_text: str
    section_path: tuple[str, ...] = Field(default_factory=tuple)
    score: float = Field(default=0.0, ge=0.0)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class QueryResult(BoundaryModel):
    """Combined result from search + optional graph expansion."""

    search_results: tuple[ContentSearchResult, ...] = Field(default_factory=tuple)
    graph_context: TraversalResult | None = None
    provenance: tuple[Provenance, ...] = Field(default_factory=tuple)


class EntityLookupResult(BoundaryModel):
    """Result of a direct entity lookup with neighbourhood."""

    entity: EntityRecord | None = None
    neighbourhood: TraversalResult | None = None
    related_chunks: tuple[ContentChunk, ...] = Field(default_factory=tuple)


class RenderedContext(BoundaryModel):
    """Pre-formatted context string ready for LLM consumption."""

    text: str
    char_count: int = 0
    chunk_count: int = 0
    entity_count: int = 0
    truncated: bool = False


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class QueryFacade(Protocol):
    """Public contract for the Query facade.

    Storage ownership: Query owns no tables. It reads from Content and
    Graph to assemble results.
    """

    async def search(self, request: QueryRequest) -> QueryResult:
        """Execute semantic search with optional graph expansion.

        Guarantees:
          - Semantic search results are returned with normalised scores.
          - When include_graph=True, entities mentioned in search results
            are expanded via graph traversal (up to graph_hops).
          - Provenance records link each result to source/document/chunk
            with exact_text derived from chunk.text (not a separate column).
          - entity_types and relation_types filter graph expansion.

        Non-guarantees:
          - Graph expansion strategy (seed selection, traversal order) is
            implementation-defined.
          - Score normalisation method is implementation-defined.

        Side effects:
          - None (read-only).

        Raises:
          - ``ValueError`` if request.text is empty.
        """
        ...

    def lookup_entity(self, request: EntityLookupRequest) -> EntityLookupResult:
        """Look up an entity by ID or name and expand its neighbourhood.

        Guarantees:
          - Resolves entity by ID (direct) or name (canonical lookup
            via Graph.find_entities, disambiguated by entity_type).
          - Returns the entity record with its aliases.
          - When expand_hops > 0, expands via graph traversal.
          - Related chunks are returned for provenance linking.

        Non-guarantees:
          - Chunk selection for related_chunks is implementation-defined.
          - When multiple entities match a name without entity_type
            filter, selection strategy is implementation-defined.

        Side effects:
          - None (read-only).

        Raises:
          - ``LookupError`` if entity_id does not exist or entity_name
            resolves to no known entity.
        """
        ...

    def render_context(self, request: ContextRenderRequest) -> RenderedContext:
        """Render a query or entity result as LLM-ready text.

        Guarantees:
          - Output respects max_chars budget (truncates with flag).
          - When include_provenance=True, source attribution is included.
          - Text is formatted for direct insertion into an LLM prompt.

        Non-guarantees:
          - Formatting style, section ordering, and truncation strategy
            are implementation details.

        Side effects:
          - None (read-only).

        Raises:
          - ``ValueError`` if neither query_result nor entity_result is
            provided in the request.
        """
        ...
