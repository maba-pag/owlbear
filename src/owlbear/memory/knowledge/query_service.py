"""Knowledge query service for per-turn context injection.

Embeds a prompt, searches the vector store for relevant documents,
resolves content via the graph store, and formats results into a
context string within a token budget.

Follows the ``KnowledgeToolset._query_knowledge()`` pattern but as a
standalone, stateless service object suitable for per-turn injection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from owlbear.memory.knowledge.protocol import HybridEmbedding

if TYPE_CHECKING:
    import sqlite3

    from owlbear.memory.knowledge.embeddings import EmbeddingProvider
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.protocol import VectorStoreProtocol
    from owlbear.memory.knowledge.retrieval import GraphAugmentedRetriever

logger = logging.getLogger(__name__)


def _token_count(text: str) -> int:
    """Count tokens using a simple word-split heuristic (KISS — no tiktoken)."""
    return len(text.split())


class KnowledgeQueryService:
    """Query the knowledge base and format results for system prompt injection.

    Thin wrapper that embeds a prompt, searches for similar documents,
    filters by similarity threshold, resolves document content, and
    formats the results into a context string within a token budget.

    Args:
        vector_store: Vector storage backend for similarity search.
        graph_store: Graph store for resolving document IDs to content.
        embedding_provider: Provider for generating query embeddings.
        scopes: Optional scope filter passed to ``search_similar``.
        similarity_threshold: Minimum similarity score to include a result.
        retriever: Optional :class:`GraphAugmentedRetriever`.  When set,
            ``_query()`` delegates to the retriever instead of calling
            ``_embed()`` and ``vector_store.search_similar()`` directly.
        consolidation_conn: Optional SQLite connection to the consolidation
            database.  When set, recent insights are appended after RAG output.
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
        consolidation_conn: sqlite3.Connection | None = None,
    ) -> None:
        self._vectors = vector_store
        self._graph = graph_store
        self._embedder = embedding_provider
        self._scopes = scopes
        self._threshold = similarity_threshold
        self._retriever = retriever
        self._consolidation_conn = consolidation_conn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query_for_context(
        self,
        prompt: str,
        *,
        max_tokens: int = 2000,
        top_k: int = 5,
    ) -> str | None:
        """Embed *prompt*, search the knowledge base, and format results.

        Returns a formatted string of relevant knowledge snippets within
        the token budget, or ``None`` if no relevant results are found.

        All exceptions are caught, logged at WARNING, and ``None`` is
        returned to avoid breaking the caller.

        Args:
            prompt: Natural-language query to embed and search.
            max_tokens: Maximum word count for the output (``len(text.split())``).
            top_k: Maximum number of results to request from the vector store.
        """
        try:
            return self._query(prompt, max_tokens=max_tokens, top_k=top_k)
        except Exception:  # noqa: BLE001 — AC requires graceful degradation
            logger.warning(
                "Knowledge query failed for prompt: %s",
                prompt[:100],
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _query(self, prompt: str, *, max_tokens: int, top_k: int) -> str | None:
        """Execute the query pipeline (no exception wrapping)."""
        results, expansion_text = self._search_chunks(prompt, top_k=top_k)

        if not results:
            return None

        # Filter by similarity threshold (results already sorted desc).
        results = [(doc_id, score) for doc_id, score in results if score >= self._threshold]
        if not results:
            return None

        # Resolve documents and format within token budget.
        output, budget = self._format_docs(results, max_tokens=max_tokens)
        if output is None:
            return None

        # Append expansion text if available and budget allows.
        if expansion_text and budget > 0:
            expansion_header = "\n\nRelated concepts:\n\n"
            header_cost = _token_count(expansion_header)
            budget -= header_cost
            if budget > 0:
                words = expansion_text.split()
                trimmed = " ".join(words[:budget])
                if trimmed:
                    output += expansion_header + trimmed
                    budget -= _token_count(trimmed)

        # Append consolidation insights if available and budget allows.
        output, budget = self._append_consolidation_insights(output, budget)

        return output

    def _search_chunks(
        self, prompt: str, *, top_k: int,
    ) -> tuple[list[tuple[str, float]], str]:
        """Return (chunks, expansion_text) from retriever or direct search."""
        if self._retriever is not None:
            retrieval = self._retriever.retrieve(
                prompt, top_k=top_k, scopes=self._scopes,
            )
            return retrieval.chunks, retrieval.expansion_text

        # Legacy path: embed and search directly.
        embedding = self._embed(prompt)
        kwargs: dict[str, object] = {}
        if self._scopes is not None:
            kwargs["scopes"] = self._scopes
        results = self._vectors.search_similar(
            embedding, top_k=top_k, embedding_type="document", **kwargs
        )
        return results, ""

    def _format_docs(
        self,
        results: list[tuple[str, float]],
        *,
        max_tokens: int,
    ) -> tuple[str | None, int]:
        """Resolve documents and format within token budget.

        Returns ``(output, remaining_budget)`` or ``(None, 0)``.
        """
        header = "Relevant knowledge:"
        budget = max_tokens - _token_count(header)
        lines: list[str] = []

        for doc_id, _score in results:
            doc = self._graph.get_document(doc_id)
            if doc is None:
                continue
            snippet = doc.content[:500]
            line = f"- {doc.title}: {snippet}"
            cost = _token_count(line)
            if cost > budget:
                break
            lines.append(line)
            budget -= cost

        if not lines:
            return None, 0

        return header + "\n\n" + "\n".join(lines), budget

    def _append_consolidation_insights(
        self, output: str, budget: int,
    ) -> tuple[str, int]:
        """Append consolidation insights to *output* within *budget*.

        Queries the consolidations table for the 3 most recent insights,
        formats them as ``Consolidation insights`` header + bullet list,
        and appends within the remaining token budget.  Exceptions are
        caught and logged at WARNING so RAG output is never lost.
        """
        if self._consolidation_conn is None:
            return output, budget

        try:
            rows = self._consolidation_conn.execute(
                "SELECT insight FROM consolidations ORDER BY created_at DESC LIMIT 3",
            ).fetchall()
        except Exception:  # noqa: BLE001
            logger.warning("Consolidation insight query failed", exc_info=True)
            return output, budget

        if not rows:
            return output, budget

        header = "\n\nConsolidation insights:\n"
        header_cost = _token_count(header)
        if header_cost >= budget:
            return output, budget

        budget -= header_cost
        bullets: list[str] = []
        for (insight_text,) in rows:
            bullet = f"- {insight_text}"
            cost = _token_count(bullet)
            if cost > budget:
                # Try word-boundary truncation for partial fit.
                words = bullet.split()
                trimmed = " ".join(words[:budget])
                if trimmed and trimmed != "-":
                    bullets.append(trimmed)
                    budget -= _token_count(trimmed)
                break
            bullets.append(bullet)
            budget -= cost

        if not bullets:
            return output, budget

        return output + header + "\n".join(bullets), budget

    def _embed(self, text: str) -> list[float] | HybridEmbedding:
        """Embed text, preferring ``embed_hybrid`` with dense fallback."""
        if hasattr(self._embedder, "embed_hybrid"):
            return self._embedder.embed_hybrid([text])[0]
        dense = self._embedder.embed([text])[0]
        return HybridEmbedding(dense=dense)
