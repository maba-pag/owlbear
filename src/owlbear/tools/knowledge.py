"""KnowledgeToolset — FunctionToolset exposing query, ingest, and list tools.

Provides ``query_knowledge``, ``ingest_document``, and
``list_knowledge_sources`` — bridging the agent layer with the
knowledge-graph subsystem.

Usage::

    from owlbear.tools.knowledge import KnowledgeToolset

    toolset = KnowledgeToolset(
        workspace_root=workspace,
        vector_store=qdrant,
        graph_store=graph,
        embedding_provider=embedder,
        ingest_pipeline=pipeline,
    )
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from pathlib import Path
    from typing import ClassVar

    from owlbear.memory.knowledge.embeddings import EmbeddingProvider
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.ingest import IngestPipeline
    from owlbear.memory.knowledge.protocol import VectorStoreProtocol

__all__ = ["KnowledgeToolset"]

logger = logging.getLogger(__name__)


class KnowledgeToolset(FunctionToolset):
    """FunctionToolset subclass exposing 3 knowledge tools.

    All file paths used in ``ingest_document(doc_type='file')`` are
    sandboxed to *workspace_root* via :meth:`_safe_path`.

    Args:
        workspace_root: Root directory for file-path sandbox checks.
        vector_store: Backend satisfying :class:`VectorStoreProtocol`.
        graph_store: :class:`GraphStore` for document/entity queries.
        embedding_provider: :class:`EmbeddingProvider` for query embedding.
        ingest_pipeline: :class:`IngestPipeline` for document ingestion.
        project_scope: Optional project ID. When set, queries are filtered
            to ``["global", "project:{id}"]`` scopes.
    """

    tool_alias: ClassVar[str] = "knowledge"

    def __init__(  # noqa: PLR0913
        self,
        workspace_root: Path,
        vector_store: VectorStoreProtocol,
        graph_store: GraphStore,
        embedding_provider: EmbeddingProvider,
        ingest_pipeline: IngestPipeline,
        project_scope: str | None = None,
    ) -> None:
        super().__init__()
        self._root = workspace_root.resolve()
        self._vectors = vector_store
        self._graph = graph_store
        self._embedder = embedding_provider
        self._pipeline = ingest_pipeline
        self._scopes: list[str] | None = (
            ["global", f"project:{project_scope}"] if project_scope else None
        )
        self._register_tools()

    def update_workspace(self, workspace: Path) -> None:
        """Set the workspace root to *workspace* (stored resolved)."""
        self._root = workspace.resolve()

    # ------------------------------------------------------------------
    # Path traversal guard (reuses FileToolset pattern)
    # ------------------------------------------------------------------

    def _safe_path(self, user_path: str) -> Path:
        """Resolve *user_path* against workspace root with traversal guard.

        Returns the resolved absolute ``Path``.

        Raises:
            PermissionError: If the resolved path escapes the workspace.
        """
        if "\x00" in user_path:
            msg = f"Path outside workspace: {user_path!r}"
            raise PermissionError(msg)

        resolved = (self._root / user_path).resolve()
        if not resolved.is_relative_to(self._root):
            msg = f"Path outside workspace: {user_path}"
            raise PermissionError(msg)
        return resolved

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all 3 knowledge tools on this toolset."""
        self.add_function(
            self._query_knowledge,
            name="query_knowledge",
            description=(
                "Search the knowledge base for information relevant to a query. "
                "Returns the top-k most similar results with similarity scores."
            ),
        )
        self.add_function(
            self._ingest_document,
            name="ingest_document",
            description=(
                "Ingest a document into the knowledge base. "
                "Accepts raw text (doc_type='text'), a workspace-relative "
                "file path (doc_type='file'), or a URL (doc_type='url')."
            ),
        )
        self.add_function(
            self._list_knowledge_sources,
            name="list_knowledge_sources",
            description="List all documents currently stored in the knowledge base.",
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _query_knowledge(self, query: str, top_k: int = 5) -> str:
        """Embed *query* and search the vector store for similar results.

        Args:
            query: Natural-language search query.
            top_k: Maximum number of results to return.

        Returns:
            Formatted numbered list with title, score, and content
            snippet, or ``"No results found"`` when the store returns
            nothing.
        """
        embeddings = self._embedder.embed([query])
        query_embedding = embeddings[0]
        kwargs: dict[str, object] = {}
        if self._scopes is not None:
            kwargs["scopes"] = self._scopes
        results = self._vectors.search_similar(
            query_embedding, top_k=top_k, embedding_type="document", **kwargs
        )

        if not results:
            return "No results found"

        lines: list[str] = []
        for i, (doc_id, score) in enumerate(results, 1):
            doc = self._graph.get_document(doc_id)
            if doc is None:
                continue
            snippet = doc.content[:500]
            lines.append(f"{i}. [{doc.title}] (score: {score})\n{snippet}")

        if not lines:
            return "No results found"

        return "\n\n".join(lines)

    async def _ingest_document(self, source: str, doc_type: str = "text") -> str:
        """Ingest a document into the knowledge pipeline.

        Args:
            source: Raw text content (when *doc_type* is ``'text'``), a
                workspace-relative file path (when *doc_type* is ``'file'``),
                or a URL (when *doc_type* is ``'url'``).
            doc_type: One of ``'text'``, ``'file'``, or ``'url'``.

        Returns:
            Summary string with the resulting document ID and counts.

        Raises:
            ValueError: If *doc_type* is not ``'text'``, ``'file'``, or
                ``'url'``.
            PermissionError: If *doc_type* is ``'file'`` and the path
                escapes the workspace.
        """
        if doc_type == "text":
            result = await self._pipeline.ingest_text(source, scope="global")
        elif doc_type == "file":
            safe = self._safe_path(source)
            result = await self._pipeline.ingest(safe, scope="global")
        elif doc_type == "url":
            result = await self._pipeline.ingest(source, scope="global")
        else:
            msg = f"Unsupported doc_type: {doc_type!r}. Use 'text', 'file', or 'url'."
            raise ValueError(msg)

        return (
            f"Ingested document {result.document_id}: "
            f"{result.chunk_count} chunks, "
            f"{result.entity_count} entities, "
            f"{result.edge_count} edges "
            f"(status: {result.status})"
        )

    def _list_knowledge_sources(self) -> str:
        """Query the graph store for all documents and format as a list.

        Returns:
            Formatted document list, or ``"No documents ingested."``
            when empty.
        """
        documents = self._graph.list_documents()

        if not documents:
            return "No documents ingested."

        lines = [f"- [{doc.id}] {doc.title} (scope: {doc.scope})" for doc in documents]
        return "\n".join(lines)
