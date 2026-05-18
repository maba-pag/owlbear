"""Hybrid search and graph-augmented retrieval for the knowledge package."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear_knowledge.protocol import HybridEmbedding

if TYPE_CHECKING:
    from owlbear_knowledge.embeddings import EmbeddingProvider
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.models import Entity
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
    ) -> RetrievalResult:
        """Run hybrid search and return a :class:`RetrievalResult`.

        Args:
            query: Natural language query string.
            top_k: Maximum number of chunks to include in the result.
            scopes: Optional scope filter for graph operations.

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
        chunks = raw_chunks[:top_k]

        if not chunks:
            return RetrievalResult(chunks=[], expansion_text="", entities_found=0)

        seeds = self._resolve_seeds(raw_chunks, scopes=scopes)

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
        all_entities = self._graph_store.list_entities(scopes=scopes)
        return [e for e in all_entities if e.chunk_id is not None and e.chunk_id in chunk_ids]

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

            neighbors = self._graph_store.get_neighbors(seed.id, scopes=scopes)
            neighbors = neighbors[: self._max_neighbors_per_entity]

            if self._weight_by_importance:
                neighbors = sorted(neighbors, key=lambda pair: pair[0].importance, reverse=True)

            for neighbor, edge in neighbors:
                line = f"{seed.name} --[{edge.relation}]--> {neighbor.name}: {neighbor.description}"
                line_words = len(line.split())
                if words_used + line_words > self._max_expansion_tokens:
                    budget_exhausted = True
                    break
                lines.append(line)
                words_used += line_words

        return "\n".join(lines)


def query_for_context(
    query: str,
    *,
    retriever: GraphAugmentedRetriever,
    graph_store: GraphStore,
    max_tokens: int = 500,
    similarity_threshold: float = 0.0,
) -> str | None:
    """Query the knowledge base and return a formatted context string.

    Combines vector search and graph expansion results into a string
    suitable for injection into LLM prompts.  Returns ``None`` when no
    qualifying results are found or any exception occurs (graceful
    degradation).

    Args:
        query: Natural language query string.
        retriever: :class:`GraphAugmentedRetriever` to delegate search to.
        graph_store: Graph store used to resolve chunk IDs to documents.
        max_tokens: Maximum word count for the returned string.
        similarity_threshold: Minimum similarity score to include a chunk.

    Returns:
        Formatted string starting with ``"Relevant knowledge:"``, or
        ``None``.
    """
    try:
        result = retriever.retrieve(query)

        qualified = [(cid, score) for cid, score in result.chunks if score >= similarity_threshold]
        if not qualified:
            return None

        content_parts: list[str] = []
        for chunk_id, _ in qualified:
            doc_id = graph_store.get_document_id_for_chunk(chunk_id) or chunk_id
            doc = graph_store.get_document(doc_id)
            if doc is not None:
                content_parts.append(f"## {doc.title}\n{doc.content}")

        if not content_parts:
            return None

        output_parts = ["Relevant knowledge:", *content_parts]
        if result.expansion_text:
            output_parts.append(f"Graph context:\n{result.expansion_text}")

        output = "\n\n".join(output_parts)

        words = output.split()
        if len(words) > max_tokens:
            output = " ".join(words[:max_tokens])

    except Exception:  # noqa: BLE001
        logger.debug("query_for_context failed silently", exc_info=True)
        return None
    else:
        return output
