"""Knowledge query service for per-turn context injection."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from owlbear_knowledge.embeddings import EmbeddingProvider
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.protocol import VectorStoreProtocol
    from owlbear_knowledge.retrieval import GraphAugmentedRetriever

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
        retriever: Optional retriever for graph-augmented retrieval. When set,
            ``_search_chunks`` delegates to it instead of embedding directly.
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
        retriever: GraphAugmentedRetriever | None = None,
        consolidation_conn: object | None = None,  # noqa: ARG002
    ) -> None:
        self._vectors = vector_store
        self._graph = graph_store
        self._embedder = embedding_provider
        self._scopes = scopes
        self._threshold = similarity_threshold
        self._retriever = retriever

    def _search_chunks(self, prompt: str, top_k: int, *, scopes: list[str] | None = None) -> list[tuple[str, float]]:
        """Return (chunk_id, score) pairs for *prompt*, delegating to the retriever when set."""
        effective_scopes = scopes if scopes is not None else self._scopes
        if self._retriever is not None:
            result = self._retriever.retrieve(prompt, top_k, effective_scopes)
            return result.chunks[:top_k]
        embeddings = self._embedder.embed([prompt])
        if not embeddings:
            return []
        query_vec = embeddings[0]
        kwargs: dict[str, object] = {}
        if effective_scopes is not None:
            kwargs["scopes"] = effective_scopes
        return self._vectors.search_similar(query_vec, top_k=top_k, **kwargs)

    async def query(
        self,
        prompt: str,
        *,
        top_k: int = 5,
        token_budget: int = 4000,  # noqa: ARG002 — reserved for future truncation
        scopes: list[str] | None = None,
    ) -> list[StructuredSearchResult]:
        """Embed *prompt*, search the knowledge base, and return structured results.

        Returns an empty list when there are no matching results above
        the similarity threshold or when documents cannot be resolved.

        Args:
            prompt: Natural-language query.
            top_k: Maximum number of results to return.
            token_budget: Reserved for future snippet truncation.
            scopes: Optional per-query scope override. When provided, overrides
                the instance-level ``self._scopes`` for this call only.
        """
        try:
            raw = self._search_chunks(prompt, top_k, scopes=scopes)
            if not raw:
                return []

            filtered = [(doc_id, score) for doc_id, score in raw if score >= self._threshold][:top_k]

            structured: list[StructuredSearchResult] = []
            for raw_id, score in filtered:
                # raw_id from the vector store is a chunk_id; resolve to document_id.
                doc_id = self._graph.get_document_id_for_chunk(raw_id) or raw_id
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

    def query_for_context(
        self,
        prompt: str,
        *,
        max_tokens: int = 2000,
        top_k: int = 5,
    ) -> str | None:
        """Query via the injected retriever and return a formatted context string.

        Returns ``None`` when no retriever is available, no results are found,
        or any exception occurs (graceful degradation).

        Args:
            prompt: Natural language query string.
            max_tokens: Maximum word count for the returned string.
            top_k: Maximum number of chunks to resolve and format.
        """
        if self._retriever is None:
            return None
        try:
            chunks = self._search_chunks(prompt, top_k)
            if not chunks:
                return None

            lines: list[str] = []
            for chunk_id, _ in chunks:
                doc = self._graph.get_document(chunk_id)
                if doc is not None:
                    lines.append(f"- {doc.title}: {doc.content}")

            if not lines:
                return None

            output = "Relevant knowledge:\n\n" + "\n".join(lines)
            words = output.split()
            if len(words) > max_tokens:
                output = " ".join(words[:max_tokens])
        except Exception:  # noqa: BLE001
            logger.warning("query_for_context failed for prompt: %s", prompt[:100], exc_info=True)
            return None
        else:
            return output
