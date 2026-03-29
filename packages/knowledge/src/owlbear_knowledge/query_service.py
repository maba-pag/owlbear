"""Knowledge query service for per-turn context injection."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from owlbear_knowledge.embeddings import EmbeddingProvider
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.protocol import VectorStoreProtocol

logger = logging.getLogger(__name__)


class StructuredSearchResult(BaseModel):
    """Structured knowledge hit for consumers that need raw retrieval fields."""

    model_config = ConfigDict(frozen=True)

    doc_id: str
    title: str
    score: float
    snippet: str
    entity_type: str | None
    scope: str


class KnowledgeQueryService:
    """Query the knowledge base and return structured results.

    Embeds a prompt, searches the vector store for similar documents,
    filters by similarity threshold, resolves document content from the
    graph store, and returns structured results.

    Args:
        vector_store: Vector storage backend for similarity search.
        graph_store: Graph store for resolving document IDs to content.
        embedding_provider: Provider for generating query embeddings.
        scopes: Optional scope filter passed to ``search_similar``.
        similarity_threshold: Minimum similarity score to include a result.
        retriever: Unused — kept for API compatibility.
        consolidation_conn: Unused — kept for API compatibility.
    """

    def __init__(  # noqa: PLR0913
        self,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStore,
        embedding_provider: EmbeddingProvider,
        *,
        scopes: list[str] | None = None,
        similarity_threshold: float = 0.3,
        retriever: object | None = None,  # noqa: ARG002
        consolidation_conn: object | None = None,  # noqa: ARG002
    ) -> None:
        self._vectors = vector_store
        self._graph = graph_store
        self._embedder = embedding_provider
        self._scopes = scopes
        self._threshold = similarity_threshold

    async def query(
        self,
        prompt: str,
        *,
        top_k: int = 5,
        token_budget: int = 4000,  # noqa: ARG002 — reserved for future truncation
    ) -> list[StructuredSearchResult]:
        """Embed *prompt*, search the knowledge base, and return structured results.

        Returns an empty list when there are no matching results above
        the similarity threshold or when documents cannot be resolved.

        Args:
            prompt: Natural-language query.
            top_k: Maximum number of results to return.
            token_budget: Reserved for future snippet truncation.
        """
        try:
            embeddings = self._embedder.embed([prompt])
            if not embeddings:
                return []

            query_vec = embeddings[0]
            kwargs: dict[str, object] = {}
            if self._scopes is not None:
                kwargs["scopes"] = self._scopes
            raw = self._vectors.search_similar(query_vec, top_k=top_k, **kwargs)

            filtered = [
                (doc_id, score) for doc_id, score in raw if score >= self._threshold
            ][:top_k]

            structured: list[StructuredSearchResult] = []
            for doc_id, score in filtered:
                doc = self._graph.get_document(doc_id)
                if doc is None:
                    continue
                entities = self._graph.list_entities_for_document(doc_id)
                entity_type = str(entities[0].entity_type) if entities else None
                structured.append(
                    StructuredSearchResult(
                        doc_id=doc_id,
                        title=doc.title,
                        score=score,
                        snippet=doc.content[:500],
                        entity_type=entity_type,
                        scope=doc.scope,
                    )
                )
        except Exception:  # noqa: BLE001
            logger.warning("Knowledge query failed for prompt: %s", prompt[:100], exc_info=True)
            return []
        else:
            return structured
