"""Knowledge ingest pipeline — async orchestrator.

Provides :class:`IngestPipeline`, which coordinates the full ingestion
flow: intake → chunk → parallel(embed, extract) → store.  Delegates all
document CRUD to :class:`~owlbear.memory.knowledge.document_store.DocumentStore`.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from owlbear.memory.knowledge.document_store import (  # noqa: F401, TC001  # re-export
    DocumentStatus,
    compute_content_hash,
)
from owlbear.memory.knowledge.intake import IntakeResult, read_file, read_text, read_url
from owlbear.memory.knowledge.protocol import HybridEmbedding

if TYPE_CHECKING:
    from owlbear.memory.knowledge.chunker import Chunk, TextChunker
    from owlbear.memory.knowledge.document_store import DocumentStore
    from owlbear.memory.knowledge.enrichment import GraphEnricher
    from owlbear.memory.knowledge.extractor import EntityExtractor, ExtractionResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class IngestResult(BaseModel):
    """Result of ingesting a document through the knowledge pipeline."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    chunk_count: int
    entity_count: int
    edge_count: int
    status: str
    skipped: bool = False
    source_pipeline: str = "ingest"
    source_task: str = "full_pipeline"


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class IngestPipeline:
    """Async orchestrator for knowledge ingestion.

    Coordinates: intake → chunk → parallel(embed, extract) → store.
    Delegates all document CRUD to :class:`DocumentStore`.

    Parameters
    ----------
    store:
        Document CRUD store for status tracking, chunks, embeddings,
        and entity/edge persistence.
    entity_extractor:
        LLM-based entity/relationship extractor (async, I/O-bound).
    text_chunker:
        Splits text into chunks.
    workspace_root:
        Workspace root directory for path-confinement checks.
    enricher:
        Optional :class:`~owlbear.memory.knowledge.enrichment.GraphEnricher`
        for background graph enrichment scheduling.  When ``None``,
        enrichment calls are silently skipped.
    pipeline_name:
        Label stamped into ``source_pipeline`` provenance metadata.
        Defaults to ``'ingest'``.
    """

    def __init__(  # noqa: PLR0913
        self,
        store: DocumentStore,
        entity_extractor: EntityExtractor,
        text_chunker: TextChunker,
        workspace_root: Path,
        enricher: GraphEnricher | None = None,
        pipeline_name: str = "ingest",
    ) -> None:
        self._store = store
        self._conn = store.conn
        self._graph = store.graph_store
        self._embedder = store.embedding_provider
        self._extractor = entity_extractor
        self._chunker = text_chunker
        self._enricher = enricher
        self._pipeline_name = pipeline_name
        self._workspace_root = workspace_root

    # -- Public API ----------------------------------------------------------

    def find_status_by_source(self, source: str, scope: str = "global") -> DocumentStatus | None:
        """Look up a previously-ingested document by source URI."""
        return self._store.find_status_by_source(source, scope=scope)

    def check_content_changed(
        self, source: str, content: str, scope: str = "global"
    ) -> tuple[bool, str | None]:
        """Check whether *content* differs from the previously-ingested version."""
        return self._store.check_content_changed(source, content, scope=scope)

    def delete_document_data(self, document_id: str) -> None:
        """Cascade-delete all data for *document_id*."""
        self._store.delete_document_data(document_id)

    async def ingest(self, source: str | Path, *, scope: str = "global") -> IngestResult:
        """Ingest content from *source* through the full pipeline.

        Parameters
        ----------
        source:
            A file path (:class:`~pathlib.Path` or ``str``) or an HTTP URL.
        scope:
            Visibility scope for the ingested data (default ``'global'``).

        Returns:
        -------
        IngestResult
            Summary with document_id, counts, and final status.
        """
        source_str = str(source)

        try:
            # 1. Intake — read content from source.
            intake_result = await self._read_source(source)

            # 2. Delta check — skip if content unchanged.
            changed, existing_doc_id = self.check_content_changed(
                source_str, intake_result.content, scope
            )
            if not changed:
                logger.info("Skipping unchanged source %s", source_str)
                return IngestResult(
                    document_id=existing_doc_id or "",
                    chunk_count=0,
                    entity_count=0,
                    edge_count=0,
                    status="skipped",
                    skipped=True,
                    source_pipeline=self._pipeline_name,
                )

            if existing_doc_id is not None:
                logger.info(
                    "Re-ingesting changed source %s (old doc %s)",
                    source_str,
                    existing_doc_id,
                )
                self.delete_document_data(existing_doc_id)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Ingest failed for %s", source_str, exc_info=True)
            document_id = uuid4().hex
            self._store.set_status(document_id, "pending", source=source_str, scope=scope)
            self._store.set_status(document_id, "failed", error=str(exc), scope=scope)
            return IngestResult(
                document_id=document_id,
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="failed",
                source_pipeline=self._pipeline_name,
            )

        # 3-9. Delegate remaining pipeline steps.
        return await self._ingest_from_intake(intake_result, scope=scope)

    async def ingest_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        *,
        scope: str = "global",
        cancel: asyncio.Event | None = None,
    ) -> IngestResult:
        """Ingest raw text through the full pipeline.

        Unlike :meth:`ingest`, this accepts text directly instead of a
        file path or URL.  Useful for crawled page content or other
        in-memory text.

        Parameters
        ----------
        text:
            The raw text content to ingest.
        metadata:
            Optional metadata dict (e.g. ``{"url": ..., "source_type": "crawl"}``).
            Merged into the :class:`IntakeResult` metadata.

        Returns:
        -------
        IngestResult
            Summary with document_id, counts, and final status.
        """
        source_label = str((metadata or {}).get("url", "inline"))

        # Delta check — skip if content unchanged.
        changed, existing_doc_id = self.check_content_changed(source_label, text, scope)
        if not changed:
            logger.info("Skipping unchanged source %s", source_label)
            return IngestResult(
                document_id=existing_doc_id or "",
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="skipped",
                skipped=True,
                source_pipeline=self._pipeline_name,
            )

        if existing_doc_id is not None:
            logger.info(
                "Re-ingesting changed source %s (old doc %s)",
                source_label,
                existing_doc_id,
            )
            self.delete_document_data(existing_doc_id)

        intake_result = read_text(text, source=source_label)
        if metadata:
            intake_result = IntakeResult(
                content=intake_result.content,
                source=intake_result.source,
                metadata={**intake_result.metadata, **metadata},
            )
        return await self._ingest_from_intake(intake_result, scope=scope, cancel=cancel)

    # -- Private helpers -----------------------------------------------------

    async def _ingest_from_intake(
        self,
        intake_result: IntakeResult,
        *,
        scope: str = "global",
        cancel: asyncio.Event | None = None,
    ) -> IngestResult:
        """Run the pipeline from an already-resolved IntakeResult."""
        document_id = uuid4().hex
        self._store.set_status(document_id, "pending", source=intake_result.source, scope=scope)

        try:
            self._store.set_status(document_id, "processing", scope=scope)

            chunks = self._chunker.chunk(intake_result.content, metadata=intake_result.metadata)
            self._store.insert_document(document_id, intake_result, scope=scope)
            chunk_ids = self._store.store_chunks(document_id, chunks, scope=scope)

            embed_result, extract_result = await asyncio.gather(
                self._run_embed(chunks),
                self._run_extract(chunks, cancel=cancel),
                return_exceptions=True,
            )
            if isinstance(extract_result, asyncio.CancelledError):
                raise extract_result  # noqa: TRY301

            entity_count, edge_count, status = self._process_results(
                document_id,
                chunks,
                embed_result,
                extract_result,
                scope=scope,
                chunk_ids=chunk_ids,
            )
            self._store.set_status(document_id, status, scope=scope)

            # Record content hash for future delta checks.
            self._store.update_content_hash(document_id, intake_result.content)

            # Schedule graph enrichment (non-blocking).
            if not isinstance(extract_result, BaseException) and self._enricher is not None:
                self._enricher.schedule_graph_enrichment(document_id, extract_result, scope)
                self._enricher.schedule_inter_doc_enrichment(document_id, extract_result, scope)

            return IngestResult(
                document_id=document_id,
                chunk_count=len(chunks),
                entity_count=entity_count,
                edge_count=edge_count,
                status=status,
                source_pipeline=self._pipeline_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ingest failed for %s", intake_result.source, exc_info=True)
            self._store.set_status(document_id, "failed", error=str(exc), scope=scope)
            return IngestResult(
                document_id=document_id,
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="failed",
                source_pipeline=self._pipeline_name,
            )

    async def _read_source(self, source: str | Path) -> IntakeResult:
        """Dispatch to the appropriate intake reader."""
        if isinstance(source, Path):
            return await read_file(source, workspace_root=self._workspace_root)
        if str(source).startswith(("http://", "https://")):
            return await read_url(str(source))
        return await read_file(source, workspace_root=self._workspace_root)

    async def _run_embed(self, chunks: list[Chunk]) -> list[HybridEmbedding]:
        """Run embedding in a thread (CPU-bound).

        Prefers :meth:`embed_hybrid` when the provider supports it;
        falls back to :meth:`embed` and wraps each dense vector in
        :class:`HybridEmbedding`.
        """
        texts = [c.text for c in chunks]
        loop = asyncio.get_running_loop()
        if hasattr(self._embedder, "embed_hybrid"):
            return await loop.run_in_executor(None, self._embedder.embed_hybrid, texts)
        # Fallback for dense-only providers.
        dense_vecs = await loop.run_in_executor(None, self._embedder.embed, texts)
        return [HybridEmbedding(dense=v) for v in dense_vecs]

    async def _run_extract(
        self,
        chunks: list[Chunk],
        *,
        cancel: asyncio.Event | None = None,
    ) -> list[ExtractionResult]:
        """Run entity extraction per chunk (LLM I/O-bound)."""
        results = []
        for chunk in chunks:
            if cancel is not None and cancel.is_set():
                break
            r = await self._extractor.extract(chunk.text, chunk.metadata)
            results.append(r)
        return results

    def _process_results(  # noqa: PLR0913
        self,
        document_id: str,
        chunks: list[Chunk],
        embed_result: list[HybridEmbedding] | list[list[float]] | BaseException,
        extract_result: list[ExtractionResult] | BaseException,
        *,
        scope: str = "global",
        chunk_ids: list[str] | None = None,
    ) -> tuple[int, int, str]:
        """Store successful results and determine final status."""
        embed_ok = not isinstance(embed_result, BaseException)
        extract_ok = not isinstance(extract_result, BaseException)

        entity_count = 0
        edge_count = 0

        if embed_ok:
            self._store.store_embeddings(document_id, chunks, embed_result, scope=scope)  # type: ignore[arg-type]
        else:
            logger.warning("Embedding failed for document %s: %s", document_id, embed_result)

        if extract_ok:
            entity_count, edge_count = self._store.store_extractions(
                extract_result,  # type: ignore[arg-type]
                scope=scope,
                document_id=document_id,
                chunk_ids=chunk_ids,
                pipeline_name=self._pipeline_name,
            )
            try:
                self._store.store_entity_embeddings(extract_result, scope=scope)  # type: ignore[arg-type]
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Entity embedding failed for document %s", document_id, exc_info=True
                )
        else:
            logger.warning("Extraction failed for document %s: %s", document_id, extract_result)

        if embed_ok and extract_ok:
            status = "indexed"
        elif embed_ok or extract_ok:
            status = "partial"
        else:
            status = "failed"

        return entity_count, edge_count, status
