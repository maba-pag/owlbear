"""Ingest pipeline: text -> chunks + entity extraction -> knowledge graph."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from owlbear_knowledge.content_safety import wrap_untrusted_content

if TYPE_CHECKING:
    from owlbear_knowledge.chunker import TextChunker
    from owlbear_knowledge.extractor import EntityExtractor
    from owlbear_knowledge.intake import IntakeResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class IngestResult(BaseModel):
    """Result of a single ingest operation."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    chunk_count: int
    entity_count: int
    edge_count: int
    status: Literal["ok", "failed", "skipped", "cancelled"]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class IngestPipeline:
    """Async pipeline for ingesting content into the knowledge graph.

    Args:
        document_store: Persistence layer for documents, chunks, and embeddings.
        entity_extractor: Entity extraction component.
        text_chunker: Text splitting component.
        cancel_signal: Optional threading.Event; if set, ingest returns cancelled.
    """

    def __init__(
        self,
        document_store: object,
        entity_extractor: EntityExtractor,
        text_chunker: TextChunker,
        cancel_signal: object | None = None,
    ) -> None:
        self._docs = document_store
        self._extractor = entity_extractor
        self._chunker = text_chunker
        self._cancel_signal = cancel_signal

    async def ingest_text(
        self,
        text: str,
        *,
        metadata: dict[str, object] | None = None,
        scope: str = "global",
    ) -> IngestResult:
        """Chunk *text*, extract entities, persist to store, return IngestResult.

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
            await asyncio.to_thread(self._docs.insert_document, doc)  # type: ignore[union-attr]

            chunk_ids: list[str] = await asyncio.to_thread(
                self._docs.store_chunks,
                doc_id,
                chunks,  # type: ignore[union-attr]
            )
            chunk_texts = [c.text for c in chunks]
            await asyncio.to_thread(
                self._docs.store_embeddings,
                chunk_ids,
                chunk_texts,  # type: ignore[union-attr]
            )

            extraction_results = await asyncio.gather(
                *(self._extractor.extract(chunk.text) for chunk in chunks),
                return_exceptions=True,
            )
            valid_extractions = [r for r in extraction_results if not isinstance(r, BaseException)]
            entity_count, edge_count = self._docs.store_extractions(valid_extractions)  # type: ignore[union-attr]

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

    async def ingest(self, intake: IntakeResult, *, scope: str = "global") -> IngestResult:
        """Ingest an IntakeResult with delta detection and cancellation support.

        URL-sourced content (``source_type == "url"``) is wrapped in
        ``<untrusted_web_content>`` sentinel tags before entity extraction to
        prevent prompt injection from malicious web pages.

        Args:
            intake: Content to ingest, as produced by read_file/read_url/read_text.
            scope: Scope tag applied to all stored objects.  Defaults to ``'global'``.

        Returns:
            IngestResult with status: ok | skipped | cancelled | failed.
        """
        doc_id = uuid4().hex
        try:
            if self._cancel_signal is not None and self._cancel_signal.is_set():  # type: ignore[union-attr]
                return IngestResult(
                    document_id=doc_id,
                    chunk_count=0,
                    entity_count=0,
                    edge_count=0,
                    status="cancelled",
                )

            changed, existing_id = self._docs.check_content_changed(  # type: ignore[union-attr]
                intake.source, intake.content, scope
            )
            if not changed:
                return IngestResult(
                    document_id=existing_id or doc_id,
                    chunk_count=0,
                    entity_count=0,
                    edge_count=0,
                    status="skipped",
                )

            _meta: dict[str, object] = dict(intake.metadata)
            chunks = await asyncio.to_thread(self._chunker.chunk, intake.content, metadata=_meta)
            chunk_count = len(chunks)

            self._docs.insert_document(doc_id, intake, scope=scope)  # type: ignore[union-attr]

            chunk_ids: list[str] = self._docs.store_chunks(doc_id, chunks, scope=scope)  # type: ignore[union-attr]
            chunk_texts = [c.text for c in chunks]

            embed_coro = asyncio.to_thread(
                self._docs.store_embeddings,
                chunk_ids,
                chunk_texts,  # type: ignore[union-attr]
            )
            _is_url = _meta.get("source_type") in {"url", "authenticated_web"}
            extract_coros = [
                self._extractor.extract(
                    wrap_untrusted_content(c.text, source_url=str(intake.source))
                    if _is_url
                    else c.text
                )
                for c in chunks
            ]

            all_results = await asyncio.gather(embed_coro, *extract_coros, return_exceptions=True)
            extraction_results = [r for r in all_results[1:] if not isinstance(r, BaseException)]
            entity_count, edge_count = self._docs.store_extractions(  # type: ignore[union-attr]
                extraction_results,
                scope=scope,
                document_id=doc_id,
                chunk_ids=chunk_ids,
            )
            self._docs.update_content_hash(doc_id, intake.content)  # type: ignore[union-attr]

        except Exception:
            logger.exception("ingest failed for doc_id=%s", doc_id)
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
