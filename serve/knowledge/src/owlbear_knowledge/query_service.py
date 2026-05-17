"""Knowledge query service for per-turn context injection."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from owlbear_knowledge.embeddings import EmbeddingProvider
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.protocol import VectorStoreProtocol
    from owlbear_knowledge.retrieval import GraphAugmentedRetriever
    from owlbear_knowledge.source_store import KnowledgeSourceStore

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
    retrieval_path: Literal["vector", "vector+graph", "graph"] = "vector"
    entities: list[dict[str, str]] = Field(default_factory=list)
    related_sources: list[dict[str, str]] = Field(default_factory=list)
    source: object | None = None


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
        source_store: Optional source store used to resolve source metadata.
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
        source_store: KnowledgeSourceStore | None = None,
        consolidation_conn: object | None = None,  # noqa: ARG002
    ) -> None:
        self._vectors = vector_store
        self._graph = graph_store
        self._embedder = embedding_provider
        self._scopes = scopes
        self._threshold = similarity_threshold
        self._retriever = retriever
        self._source_store = source_store

    def _search(
        self, prompt: str, top_k: int, *, scopes: list[str] | None = None
    ) -> tuple[list[tuple[str, float]], int]:
        """Return chunk scores and number of graph entities resolved by retriever."""
        effective_scopes = scopes if scopes is not None else self._scopes
        if self._retriever is not None:
            result = self._retriever.retrieve(prompt, top_k, effective_scopes)
            return result.chunks[:top_k], result.entities_found

        embeddings = self._embedder.embed([prompt])
        if not embeddings:
            return [], 0
        query_vec = embeddings[0]
        kwargs: dict[str, object] = {}
        if effective_scopes is not None:
            kwargs["scopes"] = effective_scopes
        return self._vectors.search_similar(query_vec, top_k=top_k, **kwargs), 0

    def _search_chunks(self, prompt: str, top_k: int, *, scopes: list[str] | None = None) -> list[tuple[str, float]]:
        """Return (chunk_id, score) pairs for *prompt*, delegating to the retriever when set."""
        chunks, _ = self._search(prompt, top_k, scopes=scopes)
        return chunks

    def _related_sources(
        self,
        *,
        doc_id: str,
        source_id: str | None,
        entities: list[object],
        scopes: list[str] | None,
    ) -> list[dict[str, str]]:
        """Resolve cross-source entity-edge relationships for a document."""
        if source_id is None or not entities:
            return []

        related_sources: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for entity in entities:
            entity_id = getattr(entity, "id", None)
            entity_name = getattr(entity, "name", None)
            if not isinstance(entity_id, str):
                continue

            edges = self._graph.list_edges(source_id=entity_id, scopes=scopes)
            edges += self._graph.list_edges(target_id=entity_id, scopes=scopes)
            for edge in edges:
                source_entity = getattr(edge, "source_id", None)
                target_entity = getattr(edge, "target_id", None)
                relation = getattr(edge, "relation", None)
                if not isinstance(source_entity, str) or not isinstance(target_entity, str):
                    continue

                peer_id = target_entity if source_entity == entity_id else source_entity
                peer = self._graph.get_entity(peer_id)
                peer_doc_id = getattr(peer, "document_id", None)
                peer_name = getattr(peer, "name", None)
                if not isinstance(peer_doc_id, str) or peer_doc_id == doc_id:
                    continue

                peer_doc = self._graph.get_document(peer_doc_id)
                peer_source_id = getattr(peer_doc, "source_id", None)
                if not isinstance(peer_source_id, str) or peer_source_id == source_id:
                    continue

                related_source_name = ""
                if self._source_store is not None:
                    related_source = self._source_store.get(peer_source_id)
                    related_source_name = related_source.name if related_source is not None else ""

                relationship = str(relation)
                entity_label = (
                    peer_name if isinstance(peer_name, str) else (entity_name if isinstance(entity_name, str) else "")
                )
                key = (related_source_name, relationship, entity_label)
                if key in seen:
                    continue
                seen.add(key)
                related_sources.append(
                    {
                        "name": related_source_name,
                        "relationship": relationship,
                        "entity": entity_label,
                    }
                )
        return related_sources

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
            raw, entities_found = self._search(prompt, top_k, scopes=scopes)
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

                # Use chunk content when available; fall back to doc content.
                snippet = doc.content[:500]
                if hasattr(self._graph, "get_chunk"):
                    chunk = self._graph.get_chunk(raw_id)
                    if isinstance(chunk, dict) and isinstance(chunk.get("content"), str):
                        chunk_index = chunk.get("chunk_index", 0)
                        total_chunks = self._graph.count_chunks_for_document(doc_id)
                        snippet = chunk["content"][:500]
                        if isinstance(total_chunks, int) and total_chunks > 1:
                            snippet = f"[chunk {chunk_index + 1}/{total_chunks}] {snippet}"

                entities = self._graph.list_entities_for_document(doc_id)
                entity_type = str(entities[0].entity_type) if entities else None
                source_id = getattr(doc, "source_id", None)
                source = None
                if self._source_store is not None and isinstance(source_id, str):
                    source = self._source_store.get(source_id)

                retrieval_path: Literal["vector", "vector+graph", "graph"] = "vector"
                if self._retriever is not None and entities_found > 0:
                    retrieval_path = "vector+graph"

                structured.append(
                    StructuredSearchResult(
                        doc_id=doc_id,
                        title=doc.title,
                        score=score,
                        snippet=snippet,
                        entity_type=entity_type,
                        scope=doc.scope,
                        retrieval_path=retrieval_path,
                        entities=[
                            {
                                "name": str(getattr(entity, "name", "")),
                                "type": str(getattr(entity, "entity_type", "")),
                            }
                            for entity in entities
                        ],
                        related_sources=self._related_sources(
                            doc_id=doc_id,
                            source_id=source_id,
                            entities=entities,
                            scopes=scopes,
                        ),
                        source=source,
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
                doc_id = self._graph.get_document_id_for_chunk(chunk_id) or chunk_id
                doc = self._graph.get_document(doc_id)
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
