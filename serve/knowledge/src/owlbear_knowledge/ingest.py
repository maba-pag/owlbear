"""Ingest pipeline: text -> chunks + entity extraction -> knowledge graph."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from owlbear_knowledge.content_safety import should_wrap, wrap_untrusted_content

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_knowledge.chunker import TextChunker
    from owlbear_knowledge.extractor import EntityExtractor
    from owlbear_knowledge.intake import IntakeResult
    from owlbear_knowledge.source_store import KnowledgeSourceStore

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
    status: Literal["ok", "failed", "skipped", "cancelled", "blocked"]


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
        injection_mode: Reserved for future pipeline-level mode override.
        source_store: Optional KnowledgeSourceStore; when supplied, ingest_text
            resolves or creates a KnowledgeSource record by URL and forwards its
            UUID as the document's source_id FK before chunk storage.
    """

    def __init__(  # noqa: PLR0913
        self,
        document_store: object,
        entity_extractor: EntityExtractor,
        text_chunker: TextChunker,
        cancel_signal: object | None = None,
        injection_mode: Literal["strict", "warn"] = "warn",
        source_store: KnowledgeSourceStore | None = None,
    ) -> None:
        self._docs = document_store
        self._extractor = entity_extractor
        self._chunker = text_chunker
        self._cancel_signal = cancel_signal
        self._injection_mode = injection_mode
        self._source_store = source_store

    def _resolve_source_by_url(
        self,
        source_url: str,
        scope: str,
    ) -> object | None:
        if self._source_store is None:
            return None
        if scope == "global":
            return self._source_store.resolve_by_url(source_url)
        return self._source_store.resolve_by_url(source_url, scope=scope)

    def _resolve_or_create_source_id(
        self,
        source_url: str,
        scope: str,
    ) -> tuple[str | None, str | None]:
        if self._source_store is None:
            return None, None

        created_source_id: str | None = None
        resolved_source = self._resolve_source_by_url(source_url, scope)
        if resolved_source is None:
            from owlbear_knowledge.models import KnowledgeSource, SourceType  # noqa: PLC0415

            now = datetime.now(tz=UTC).isoformat()
            new_source = KnowledgeSource(
                name=source_url,
                source_type=SourceType.AUTHENTICATED_WEB,
                fetch_method="url",
                enrich=True,
                config={"url": source_url},
                scope=scope,
                created_at=now,
                updated_at=now,
            )
            created_source_id = new_source.id
            created_source = self._source_store.create(new_source)
            # Store implementation returns None; test doubles may return the source.
            resolved_source = (
                created_source
                if created_source is not None
                else self._resolve_source_by_url(source_url, scope)
            )

        resolved_source_id = getattr(resolved_source, "id", None)
        return resolved_source_id, created_source_id

    async def _cleanup_failed_ingest(
        self,
        doc_id: str,
        chunk_ids: list[str],
        created_source_id: str | None,
    ) -> None:
        try:
            self._docs.delete_document_data(doc_id)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            logger.debug("cleanup of failed ingest document failed", exc_info=True)

        if chunk_ids:
            try:
                self._docs.delete_chunk_embeddings(chunk_ids)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                logger.debug(
                    "cleanup of failed ingest embeddings failed",
                    exc_info=True,
                )

        if created_source_id is not None and self._source_store is not None:
            try:
                self._source_store.delete(created_source_id)
            except Exception:  # noqa: BLE001
                logger.debug("cleanup of failed ingest source failed", exc_info=True)

    async def ingest_text(
        self,
        text: str,
        *,
        metadata: dict[str, object] | None = None,
        scope: str = "global",
        source_id: str | None = None,
        source_url: str | None = None,
    ) -> IngestResult:
        """Chunk *text*, extract entities, persist to store, return IngestResult.

        On internal failure, returns IngestResult with status='failed' and
        zero counts — no exceptions are propagated.
        """
        from owlbear_knowledge.models import Document  # noqa: PLC0415

        doc_id = uuid4().hex
        created_source_id: str | None = None
        chunk_ids: list[str] = []
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

            resolved_source_id = source_id
            if source_url is not None and self._source_store is not None:
                resolved_source_id, created_source_id = self._resolve_or_create_source_id(
                    source_url,
                    scope,
                )

            doc = Document(
                id=doc_id,
                title=str(_meta.get("title") or doc_id),
                content=text,
                metadata=_meta,
                scope=scope,
                source_id=resolved_source_id,
            )

            self._docs.insert_document(  # type: ignore[union-attr]
                doc,
                source_id=resolved_source_id,
            )

            chunk_ids = self._docs.store_chunks(  # type: ignore[union-attr]
                doc_id,
                chunks,
                scope=scope,
            )
            chunk_texts = [c.text for c in chunks]
            self._docs.store_embeddings(  # type: ignore[union-attr]
                chunk_ids,
                chunk_texts,
                scope=scope,
            )

            extraction_results = await asyncio.gather(
                *(self._extractor.extract(chunk.text) for chunk in chunks),
                return_exceptions=True,
            )
            valid_extractions = [
                r for r in extraction_results if not isinstance(r, BaseException)
            ]
            entity_count, edge_count = self._docs.store_extractions(  # type: ignore[union-attr]
                valid_extractions,
                scope=scope,
                document_id=doc_id,
                chunk_ids=chunk_ids,
            )

        except Exception:  # catch-all for unexpected ingest failures
            logger.exception("ingest_text failed for doc_id=%s", doc_id)
            await self._cleanup_failed_ingest(doc_id, chunk_ids, created_source_id)
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

    async def ingest(
        self,
        intake: IntakeResult,
        *,
        scope: str = "global",
        source_id: str | None = None,
        content_cleaner: Callable[[str], str] | None = None,
    ) -> IngestResult:
        """Ingest an IntakeResult with delta detection and cancellation support.

        **Replace-on-change semantics:** when ``check_content_changed`` returns
        ``changed=True`` with an ``existing_id``, all data for the prior document
        (entities, edges, chunks, status, and the document row itself) is deleted via
        ``delete_document_data(existing_id)`` before the new document is inserted.
        This prevents ghost documents from accumulating on repeated ingest of the
        same source with updated content.

        Untrusted-source content (determined by
        :func:`~owlbear_knowledge.content_safety.should_wrap`) is wrapped in
        ``<untrusted_web_content>`` sentinel tags before entity extraction to
        prevent prompt injection from malicious web pages.  Local/text sources
        (``file``, ``file_glob``, ``text``) and absent source types are not
        wrapped; all other source types are wrapped by default.

        Args:
            intake: Content to ingest, as produced by read_file/read_url/read_text.
            scope: Scope tag applied to all stored objects.  Defaults to ``'global'``.
            source_id: Optional source UUID to persist on the document row.
            content_cleaner: Optional callable applied to raw content before hashing.
                When provided, delta detection compares hashes of the *cleaned* output
                rather than the raw content, so cosmetic HTML changes do not trigger
                unnecessary re-ingestion.

        Returns:
            IngestResult with status: ok | skipped | cancelled | failed | blocked.
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

            content_for_hash = (
                content_cleaner(intake.content)
                if content_cleaner is not None
                else intake.content
            )
            changed, existing_id = self._docs.check_content_changed(  # type: ignore[union-attr]
                intake.source, content_for_hash, scope
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
            chunks = await asyncio.to_thread(
                self._chunker.chunk, intake.content, metadata=_meta
            )
            chunk_count = len(chunks)

            if existing_id is not None:
                self._docs.delete_document_data(existing_id)  # type: ignore[union-attr]

            self._docs.insert_document(  # type: ignore[union-attr]
                doc_id,
                intake,
                scope=scope,
                source_id=source_id,
            )

            chunk_ids: list[str] = self._docs.store_chunks(doc_id, chunks, scope=scope)  # type: ignore[union-attr]
            chunk_texts = [c.text for c in chunks]

            _should_wrap = should_wrap(_meta.get("source_type"))  # type: ignore[arg-type]

            extract_coros = [
                self._extractor.extract(
                    wrap_untrusted_content(c.text, source_url=str(intake.source))
                    if _should_wrap
                    else c.text
                )
                for c in chunks
            ]

            embed_coro = asyncio.to_thread(
                self._docs.store_embeddings,
                chunk_ids,
                chunk_texts,  # type: ignore[union-attr]
                scope=scope,
            )
            all_results = await asyncio.gather(
                embed_coro, *extract_coros, return_exceptions=True
            )
            extraction_results = [
                r for r in all_results[1:] if not isinstance(r, BaseException)
            ]
            entity_count, edge_count = self._docs.store_extractions(  # type: ignore[union-attr]
                extraction_results,
                scope=scope,
                document_id=doc_id,
                chunk_ids=chunk_ids,
            )
            self._docs.set_status(doc_id, "ok", source=intake.source, scope=scope)  # type: ignore[union-attr]
            self._docs.update_content_hash(doc_id, content_for_hash)  # type: ignore[union-attr]

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
