"""Ingest pipeline: text -> chunks + entity extraction -> knowledge graph."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from owlbear_knowledge.chunker import TextChunker
    from owlbear_knowledge.extractor import EntityExtractor
    from owlbear_knowledge.graph_store import GraphStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    """Result of a single ingest_text operation."""

    document_id: str
    chunk_count: int
    entity_count: int
    edge_count: int
    status: str


class DocumentStore:
    """Document persistence facade wrapping GraphStore.

    Args:
        graph_store: Underlying graph store for document persistence.
    """

    def __init__(self, graph_store: GraphStore) -> None:
        self._graph = graph_store

    def insert_document(self, doc: object) -> None:
        """Persist *doc* to the underlying graph store."""
        self._graph.insert_document(doc)  # type: ignore[arg-type]


class IngestPipeline:
    """Async pipeline for ingesting plain text into the knowledge graph.

    Args:
        document_store: Persistence layer for documents.
        entity_extractor: Entity extraction component.
        text_chunker: Text splitting component.
    """

    def __init__(
        self,
        document_store: DocumentStore,
        entity_extractor: EntityExtractor,
        text_chunker: TextChunker,
    ) -> None:
        self._docs = document_store
        self._extractor = entity_extractor
        self._chunker = text_chunker

    async def ingest_text(
        self,
        text: str,
        *,
        metadata: dict[str, object] | None = None,
        scope: str = "global",
    ) -> IngestResult:
        """Chunk *text*, extract entities, persist to graph, return IngestResult.

        On internal failure, returns IngestResult with status='failed' and
        zero counts — no exceptions are propagated.
        """
        from owlbear_knowledge.models import Document  # noqa: PLC0415

        doc_id = uuid4().hex
        try:
            _meta: dict[str, object] = dict(metadata or {})
            chunks = await asyncio.to_thread(self._chunker.chunk, text, metadata=_meta)
            chunk_count = len(chunks)

            doc = Document(
                id=doc_id,
                title=str(_meta.get("title") or doc_id),
                content=text,
                metadata=_meta,
                scope=scope,
            )
            await asyncio.to_thread(self._docs.insert_document, doc)

            extraction_results = await asyncio.gather(
                *(self._extractor.extract(chunk.text) for chunk in chunks),
                return_exceptions=True,
            )

            entity_count = 0
            edge_count = 0
            for result in extraction_results:
                if isinstance(result, BaseException):
                    continue
                entity_count += len(result.entities)
                edge_count += len(result.edges)

        except Exception:  # catch-all for unexpected ingest failures
            logger.exception("ingest_text failed for doc_id=%s", doc_id)
            return IngestResult(
                document_id=doc_id,
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="failed",
            )

        return IngestResult(
            document_id=doc_id,
            chunk_count=chunk_count,
            entity_count=entity_count,
            edge_count=edge_count,
            status="ok",
        )
