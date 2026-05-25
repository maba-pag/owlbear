"""Hybrid search and graph-augmented retrieval for the knowledge package."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear_knowledge.protocol import HybridEmbedding

if TYPE_CHECKING:
    from owlbear_knowledge.embeddings import EmbeddingProvider
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.models import Edge, Entity
    from owlbear_knowledge.protocol import VectorStoreProtocol

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    """Result of a hybrid knowledge retrieval operation."""

    model_config = ConfigDict(frozen=True)

    chunks: list[tuple[str, float]]
    """Vector search results as (chunk_id, similarity_score) pairs."""

    expansion_text: str
    """Formatted graph-expansion text from seed entity neighbors."""

    entities_found: int
    """Number of seed entities resolved from vector search results."""


class GraphAugmentedRetriever:
    """Retrieves knowledge by combining vector search with graph expansion.

    Embeds a query, searches the vector store, resolves matched chunks to
    graph entities (seeds), expands to neighbors, and returns a
    :class:`RetrievalResult` with chunks and formatted expansion text.
    """

    def __init__(  # noqa: PLR0913
        self,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStore,
        embedding_provider: EmbeddingProvider,
        *,
        expansion_depth: int = 1,
        max_expansion_tokens: int = 2000,
        max_neighbors_per_entity: int = 10,
        expansion_enabled: bool = True,
        weight_by_importance: bool = False,
    ) -> None:
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._embedding_provider = embedding_provider
        self._expansion_depth = expansion_depth
        self._max_expansion_tokens = max_expansion_tokens
        self._max_neighbors_per_entity = max_neighbors_per_entity
        self._expansion_enabled = expansion_enabled
        self._weight_by_importance = weight_by_importance

    def _embed(self, query: str) -> list[float] | HybridEmbedding:
        """Embed a query, preferring hybrid embedding with dense fallback.

        Uses ``embed_hybrid`` when available on the embedding provider and
        it returns a concrete list or tuple (not a mock); otherwise falls
        back to ``embed``.

        Args:
            query: Natural language query string.

        Returns:
            Dense vector or full hybrid embedding for the query.
        """
        if hasattr(self._embedding_provider, "embed_hybrid"):
            result = self._embedding_provider.embed_hybrid([query])
            if isinstance(result, (list, tuple)) and result:
                first = result[0]
                if isinstance(first, (HybridEmbedding, list)):
                    return first
        return self._embedding_provider.embed([query])[0]

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        scopes: list[str] | None = None,
        similarity_threshold: float = 0.0,
    ) -> RetrievalResult:
        """Run hybrid search and return a :class:`RetrievalResult`.

        Args:
            query: Natural language query string.
            top_k: Maximum number of chunks to include in the result.
            scopes: Optional scope filter for graph operations.
            similarity_threshold: Minimum vector score to include in chunks and graph expansion.

        Returns:
            :class:`RetrievalResult` with vector chunks and graph expansion.
        """
        embedding = self._embed(query)
        raw_chunks: list[tuple[str, float]] = self._vector_store.search_similar(
            embedding,
            top_k=top_k,
            embedding_type="document",
            scopes=scopes,
        )
        chunks = [(chunk_id, score) for chunk_id, score in raw_chunks if score >= similarity_threshold][:top_k]

        if not chunks:
            return RetrievalResult(chunks=[], expansion_text="", entities_found=0)

        seeds = self._resolve_seeds(chunks, scopes=scopes)

        expansion_text = self._expand(seeds, scopes=scopes) if self._expansion_enabled else ""

        return RetrievalResult(
            chunks=chunks,
            expansion_text=expansion_text,
            entities_found=len(seeds),
        )

    def _resolve_seeds(
        self,
        chunks: list[tuple[str, float]],
        scopes: list[str] | None = None,
    ) -> list[Entity]:
        """Find graph entities whose chunk_id matches a vector search result.

        Args:
            chunks: Vector search result (chunk_id, score) pairs.
            scopes: Optional scope filter.

        Returns:
            Matching :class:`Entity` objects.
        """
        chunk_ids = {chunk_id for chunk_id, _ in chunks}
        return self._graph_store.get_entities_by_chunk_ids(chunk_ids, scopes=scopes)

    def _resolve_endpoint_entity(self, entity_id: str, seed: Entity, neighbor: Entity) -> Entity | None:
        """Resolve an edge endpoint from the known traversal entities or graph store."""
        if entity_id == seed.id:
            return seed
        if entity_id == neighbor.id:
            return neighbor
        get_entity = getattr(self._graph_store, "get_entity", None)
        if not callable(get_entity):
            return None
        entity = get_entity(entity_id)
        return entity if entity is not None else None

    def _format_expansion_line(self, seed: Entity, neighbor: Entity, edge: Edge) -> str:
        """Format a graph-context line using the edge's stored direction."""
        source = self._resolve_endpoint_entity(edge.source_id, seed, neighbor)
        target = self._resolve_endpoint_entity(edge.target_id, seed, neighbor)
        source_name = source.name if source is not None else edge.source_id
        target_name = target.name if target is not None else edge.target_id
        target_description = target.description if target is not None else ""
        return f"{source_name} --[{edge.relation}]--> {target_name}: {target_description}"

    def _expand(
        self,
        seeds: list[Entity],
        scopes: list[str] | None = None,
    ) -> str:
        """Expand seed entities to their graph neighbors, respecting a token budget.

        Each line has the format::

            {seed_name} --[{relation}]--> {neighbor_name}: {description}

        Lines are added until the cumulative word count would exceed
        :attr:`_max_expansion_tokens`.

        Args:
            seeds: Seed entities from vector search resolution.
            scopes: Optional scope filter for neighbor lookup.

        Returns:
            Formatted multi-line string, or an empty string when the budget
            is zero or no neighbors exist.
        """
        if self._max_expansion_tokens == 0:
            return ""

        lines: list[str] = []
        words_used = 0
        budget_exhausted = False

        for seed in seeds:
            if budget_exhausted:
                break

            neighbors = self._graph_store.get_neighbors(
                seed.id,
                max_depth=self._expansion_depth,
                scopes=scopes,
            )

            if self._weight_by_importance:
                neighbors = sorted(neighbors, key=lambda pair: pair[0].importance, reverse=True)
            neighbors = neighbors[: self._max_neighbors_per_entity]

            for neighbor, edge in neighbors:
                line = self._format_expansion_line(seed, neighbor, edge)
                line_words = len(line.split())
                if words_used + line_words > self._max_expansion_tokens:
                    budget_exhausted = True
                    break
                lines.append(line)
                words_used += line_words

        return "\n".join(lines)
