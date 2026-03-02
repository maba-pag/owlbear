"""Graph-augmented retrieval — enhances vector search with graph expansion.

Embeds a query, searches for similar document chunks, resolves chunk IDs
to knowledge-graph entities, expands via neighbor traversal, and returns
results within a token budget.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear.memory.knowledge.protocol import HybridEmbedding

if TYPE_CHECKING:
    from owlbear.memory.knowledge.embeddings import EmbeddingProvider
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.models import Entity
    from owlbear.memory.knowledge.protocol import VectorStoreProtocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class RetrievalResult(BaseModel):
    """Immutable result from :meth:`GraphAugmentedRetriever.retrieve`.

    Attributes
    ----------
    chunks:
        Vector search hits as ``(id, score)`` pairs, highest score first.
    expansion_text:
        Formatted neighbor descriptions from graph expansion (may be empty).
    entities_found:
        Number of seed entities resolved from chunk IDs.
    """

    model_config = ConfigDict(frozen=True)

    chunks: list[tuple[str, float]]
    expansion_text: str
    entities_found: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _word_count(text: str) -> int:
    """Token estimate via simple word split (same heuristic as KnowledgeQueryService)."""
    return len(text.split())


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class GraphAugmentedRetriever:
    """Enhance vector search results by following knowledge-graph edges.

    Pipeline: embed query → ``search_similar`` (document chunks) → resolve
    chunk_ids to entities → ``get_neighbors`` per entity → format + budget-cap.

    Parameters
    ----------
    vector_store:
        Vector storage backend for similarity search.
    graph_store:
        Graph store for entity lookups and neighbor traversal.
    embedding_provider:
        Provider for generating query embeddings.
    expansion_depth:
        Max BFS hops for neighbor expansion (0 = no expansion).
    max_expansion_tokens:
        Word-count budget for *expansion_text*.
    max_neighbors_per_entity:
        ``max_nodes`` passed to :meth:`GraphStore.get_neighbors`.
    expansion_enabled:
        Master kill-switch — ``False`` disables all graph expansion.
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
    ) -> None:
        self._vectors = vector_store
        self._graph = graph_store
        self._embedder = embedding_provider
        self._depth = expansion_depth
        self._max_tokens = max_expansion_tokens
        self._max_neighbors = max_neighbors_per_entity
        self._enabled = expansion_enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        scopes: list[str] | None = None,
    ) -> RetrievalResult:
        """Embed *query*, search, and optionally expand via the knowledge graph.

        Parameters
        ----------
        query:
            Natural-language query to embed and search.
        top_k:
            Maximum number of vector-search results.
        scopes:
            Optional scope filter forwarded to vector store and graph store.

        Returns
        -------
        RetrievalResult:
            Vector chunks, formatted expansion text, and entity count.
        """
        embedding = self._embed(query)

        # Step 1 — vector search for document chunks.
        search_kwargs: dict[str, object] = {}
        if scopes is not None:
            search_kwargs["scopes"] = scopes
        chunks = self._vectors.search_similar(
            embedding, top_k=top_k, embedding_type="document", **search_kwargs,
        )

        if not chunks or not self._enabled or self._depth < 1:
            return RetrievalResult(
                chunks=chunks,
                expansion_text="",
                entities_found=0,
            )

        # Step 2 — resolve chunk_ids to seed entities.
        seeds = self._resolve_seeds(chunks, scopes=scopes)
        if not seeds:
            return RetrievalResult(
                chunks=chunks,
                expansion_text="",
                entities_found=0,
            )

        # Step 3 — expand via graph neighbors.
        expansion_text = self._expand(seeds, scopes=scopes)

        return RetrievalResult(
            chunks=chunks,
            expansion_text=expansion_text,
            entities_found=len(seeds),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> list[float] | HybridEmbedding:
        """Embed *text*, preferring ``embed_hybrid`` with dense fallback."""
        if hasattr(self._embedder, "embed_hybrid"):
            return self._embedder.embed_hybrid([text])[0]
        dense = self._embedder.embed([text])[0]
        return HybridEmbedding(dense=dense)

    def _resolve_seeds(
        self,
        chunks: list[tuple[str, float]],
        *,
        scopes: list[str] | None,
    ) -> list[Entity]:
        """Find entities whose ``chunk_id`` matches a vector-search result ID."""
        chunk_ids = {cid for cid, _score in chunks}
        entities = self._graph.list_entities(scopes=scopes)
        return [e for e in entities if e.chunk_id in chunk_ids]

    def _expand(
        self,
        seeds: list[Entity],
        *,
        scopes: list[str] | None,
    ) -> str:
        """Traverse neighbors for each seed entity within the token budget."""
        budget = self._max_tokens
        lines: list[str] = []

        for seed in seeds:
            neighbors = self._graph.get_neighbors(
                seed.id,
                max_depth=self._depth,
                max_nodes=self._max_neighbors,
                scopes=scopes,
            )
            for neighbor, edge in neighbors:
                desc = neighbor.description or neighbor.name
                line = f"{seed.name} --[{edge.relation}]--> {neighbor.name}: {desc}"
                cost = _word_count(line)
                if cost > budget:
                    return "\n".join(lines)
                lines.append(line)
                budget -= cost

        return "\n".join(lines)
