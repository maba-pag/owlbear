"""Knowledge ingest pipeline — async orchestrator.

Provides :class:`IngestPipeline`, which coordinates the full ingestion
flow: intake → chunk → parallel(embed, extract) → store.  Tracks
document status in the ``document_status`` table.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from owlbear.memory.knowledge.intake import IntakeResult, read_file, read_text, read_url
from owlbear.memory.knowledge.protocol import HybridEmbedding

if TYPE_CHECKING:
    import sqlite3

    from owlbear.memory.knowledge.chunker import Chunk, TextChunker
    from owlbear.memory.knowledge.embeddings import EmbeddingProvider
    from owlbear.memory.knowledge.extractor import EntityExtractor, ExtractionResult
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.graph_builder import IntraDocGraphBuilder
    from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder
    from owlbear.memory.knowledge.models import Entity
    from owlbear.memory.knowledge.protocol import VectorStoreProtocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class DocumentStatus(BaseModel):
    """Status record for a previously-ingested document."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    content_hash: str | None
    status: str


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
# Content hashing
# ---------------------------------------------------------------------------


def compute_content_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content* after stripping whitespace.

    Parameters
    ----------
    content:
        Raw document text.  Leading/trailing whitespace is stripped
        before hashing so that cosmetic differences (e.g. trailing
        newlines in HTTP responses) do not produce false positives.

    Returns
    -------
    str
        64-character lowercase hex digest.
    """
    return hashlib.sha256(content.strip().encode()).hexdigest()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class IngestPipeline:
    """Async orchestrator for knowledge ingestion.

    Coordinates: intake → chunk → parallel(embed, extract) → store.
    Tracks document processing status in the ``document_status`` table.

    Parameters
    ----------
    conn:
        SQLite connection with :func:`~owlbear.memory.knowledge.schema.init_db`
        already applied.
    graph_store:
        Store for entities and edges.
    vector_store:
        Store for chunk embeddings.  Accepts any backend satisfying
        :class:`~owlbear.memory.knowledge.protocol.VectorStoreProtocol`.
    embedding_provider:
        Batch embedding provider (sync, CPU-bound).
    entity_extractor:
        LLM-based entity/relationship extractor (async, I/O-bound).
    text_chunker:
        Splits text into chunks.
    graph_builder:
        Optional intra-document graph builder.  When provided, entities
        extracted from each document are connected via structural
        relationships within the same document.
    inter_doc_builder:
        Optional inter-document graph builder.  When provided (and at
        least two documents exist in the scope), cross-document edges
        are inferred in a background task after ingest completes.
    pipeline_name:
        Label stamped into ``source_pipeline`` provenance metadata on
        every entity and edge produced by this pipeline.  Defaults to
        ``'ingest'``.
    """

    def __init__(  # noqa: PLR0913
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        vector_store: VectorStoreProtocol,
        embedding_provider: EmbeddingProvider,
        entity_extractor: EntityExtractor,
        text_chunker: TextChunker,
        graph_builder: IntraDocGraphBuilder | None = None,
        inter_doc_builder: InterDocGraphBuilder | None = None,
        pipeline_name: str = "ingest",
    ) -> None:
        self._conn = conn
        self._graph = graph_store
        self._vectors = vector_store
        self._embedder = embedding_provider
        self._extractor = entity_extractor
        self._chunker = text_chunker
        self._graph_builder = graph_builder
        self._inter_doc_builder = inter_doc_builder
        self._pipeline_name = pipeline_name
        self._background_tasks: set[asyncio.Task[None]] = set()

    # -- Public API ----------------------------------------------------------

    def find_status_by_source(self, source: str, scope: str = "global") -> DocumentStatus | None:
        """Look up a previously-ingested document by source URI.

        Parameters
        ----------
        source:
            The source string (file path or URL) used during ingestion.
        scope:
            Visibility scope to filter on (default ``'global'``).

        Returns
        -------
        DocumentStatus | None
            The matching status record, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT document_id, content_hash, status "
            "FROM document_status WHERE source = ? AND scope = ?",
            (source, scope),
        ).fetchone()
        if row is None:
            return None
        return DocumentStatus(document_id=row[0], content_hash=row[1], status=row[2])

    def check_content_changed(
        self, source: str, content: str, scope: str = "global"
    ) -> tuple[bool, str | None]:
        """Check whether *content* differs from the previously-ingested version.

        Computes the SHA-256 hash of *content* (stripped), looks up the
        existing record via :meth:`find_status_by_source`, and compares.

        Parameters
        ----------
        source:
            The source string (file path or URL) used during ingestion.
        content:
            The new/current document text.
        scope:
            Visibility scope (default ``'global'``).

        Returns
        -------
        tuple[bool, str | None]
            ``(changed, existing_document_id)`` where:

            - ``(True, None)`` — source not previously ingested (new doc).
            - ``(False, id)`` — hash matches stored record (skip).
            - ``(True, id)`` — hash differs (re-ingest needed).
        """
        new_hash = compute_content_hash(content)
        existing = self.find_status_by_source(source, scope=scope)
        if existing is None:
            return True, None
        if existing.content_hash == new_hash:
            return False, existing.document_id
        return True, existing.document_id

    def delete_document_data(self, document_id: str) -> None:
        """Cascade-delete all data for *document_id* across SQLite and Qdrant.

        Deletes in FK-safe order: chunks → edges (for affected entities) →
        entities → Qdrant points → document → document_status.

        Safe to call with a non-existent *document_id* (no-op).
        """
        # 1. Delete chunks.
        self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))

        # 2. Delete edges referencing entities that belong to this document,
        #    then delete the entities themselves.
        entity_ids = [
            row[0]
            for row in self._conn.execute(
                "SELECT id FROM entities WHERE document_id = ?", (document_id,)
            ).fetchall()
        ]
        if entity_ids:
            placeholders = ", ".join("?" for _ in entity_ids)
            self._conn.execute(
                f"DELETE FROM edges WHERE source_id IN ({placeholders}) "  # noqa: S608
                f"OR target_id IN ({placeholders})",
                [*entity_ids, *entity_ids],
            )
            self._conn.execute(
                f"DELETE FROM entities WHERE id IN ({placeholders})",  # noqa: S608
                entity_ids,
            )

        # 3. Delete Qdrant points (if the vector store supports it).
        if hasattr(self._vectors, "delete_by_document_id"):
            self._vectors.delete_by_document_id(document_id)

        # 4. Delete document row.
        self._conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

        # 5. Delete document_status row.
        self._conn.execute("DELETE FROM document_status WHERE document_id = ?", (document_id,))

        self._conn.commit()

    async def ingest(self, source: str | Path, *, scope: str = "global") -> IngestResult:
        """Ingest content from *source* through the full pipeline.

        Parameters
        ----------
        source:
            A file path (:class:`~pathlib.Path` or ``str``) or an HTTP URL.
        scope:
            Visibility scope for the ingested data (default ``'global'``).

        Returns
        -------
        IngestResult
            Summary with document_id, counts, and final status.
        """
        source_str = str(source)
        document_id: str | None = None

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

            # 3. Create new document tracking.
            document_id = uuid4().hex
            self._set_status(document_id, "pending", source=source_str, scope=scope)
            self._set_status(document_id, "processing", scope=scope)

            # 4. Chunk the content.
            chunks = self._chunker.chunk(intake_result.content, metadata=intake_result.metadata)

            # 5. Insert document record, then persist chunks.
            self._insert_document(document_id, intake_result, scope=scope)
            chunk_ids = self._store_chunks(document_id, chunks, scope=scope)

            # 6. Parallel: embed (CPU-bound) + extract (LLM I/O-bound).
            embed_result, extract_result = await asyncio.gather(
                self._run_embed(chunks),
                self._run_extract(chunks),
                return_exceptions=True,
            )

            # 7. Store successful results, determine final status.
            entity_count, edge_count, status = self._process_results(
                document_id,
                chunks,
                embed_result,
                extract_result,
                scope=scope,
                chunk_ids=chunk_ids,
            )

            self._set_status(document_id, status, scope=scope)

            # 8. Record content hash for future delta checks.
            self._update_content_hash(document_id, intake_result.content)

            # 9. Schedule graph enrichment (non-blocking).
            if not isinstance(extract_result, BaseException):
                self._schedule_graph_enrichment(document_id, extract_result, scope)

                # 9b. Schedule inter-document graph enrichment (non-blocking).
                self._schedule_inter_doc_enrichment(document_id, extract_result, scope)

            return IngestResult(
                document_id=document_id,
                chunk_count=len(chunks),
                entity_count=entity_count,
                edge_count=edge_count,
                status=status,
                source_pipeline=self._pipeline_name,
            )

        except Exception as exc:  # noqa: BLE001
            logger.warning("Ingest failed for %s", source_str, exc_info=True)
            if document_id is None:
                document_id = uuid4().hex
                self._set_status(document_id, "pending", source=source_str, scope=scope)
            self._set_status(document_id, "failed", error=str(exc), scope=scope)
            return IngestResult(
                document_id=document_id,
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="failed",
                source_pipeline=self._pipeline_name,
            )

    async def ingest_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        *,
        scope: str = "global",
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

        Returns
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
        return await self._ingest_from_intake(intake_result, scope=scope)

    # -- Private helpers -----------------------------------------------------

    async def _ingest_from_intake(
        self,
        intake_result: IntakeResult,
        *,
        scope: str = "global",
    ) -> IngestResult:
        """Run the pipeline from an already-resolved IntakeResult."""
        document_id = uuid4().hex
        self._set_status(document_id, "pending", source=intake_result.source, scope=scope)

        try:
            self._set_status(document_id, "processing", scope=scope)

            chunks = self._chunker.chunk(intake_result.content, metadata=intake_result.metadata)
            self._insert_document(document_id, intake_result, scope=scope)
            chunk_ids = self._store_chunks(document_id, chunks, scope=scope)

            embed_result, extract_result = await asyncio.gather(
                self._run_embed(chunks),
                self._run_extract(chunks),
                return_exceptions=True,
            )

            entity_count, edge_count, status = self._process_results(
                document_id,
                chunks,
                embed_result,
                extract_result,
                scope=scope,
                chunk_ids=chunk_ids,
            )
            self._set_status(document_id, status, scope=scope)

            # Record content hash for future delta checks.
            self._update_content_hash(document_id, intake_result.content)

            # Schedule graph enrichment (non-blocking).
            if not isinstance(extract_result, BaseException):
                self._schedule_graph_enrichment(document_id, extract_result, scope)

                # Schedule inter-document graph enrichment (non-blocking).
                self._schedule_inter_doc_enrichment(document_id, extract_result, scope)

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
            self._set_status(document_id, "failed", error=str(exc), scope=scope)
            return IngestResult(
                document_id=document_id,
                chunk_count=0,
                entity_count=0,
                edge_count=0,
                status="failed",
                source_pipeline=self._pipeline_name,
            )

    def _update_content_hash(self, document_id: str, content: str) -> None:
        """Store the content hash in ``document_status`` for future delta checks."""
        content_hash = compute_content_hash(content)
        self._conn.execute(
            "UPDATE document_status SET content_hash = ? WHERE document_id = ?",
            (content_hash, document_id),
        )
        self._conn.commit()

    def _schedule_graph_enrichment(
        self,
        document_id: str,
        extract_results: list[ExtractionResult],
        scope: str,
    ) -> None:
        """Schedule non-blocking graph enrichment if graph_builder is available."""
        if self._graph_builder is None:
            return
        entities = [e for r in extract_results for e in r.entities]
        if not entities:
            return
        logger.info("Scheduling graph enrichment for document %s", document_id)
        task = asyncio.create_task(self._enrich_graph(document_id, entities, scope))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _enrich_graph(
        self,
        document_id: str,
        entities: list[Entity],
        scope: str,
    ) -> None:
        """Background task: run graph builder and update status on completion."""
        try:
            # Idempotency check — skip if already enriched.
            row = self._conn.execute(
                "SELECT status FROM document_status WHERE document_id = ?",
                (document_id,),
            ).fetchone()
            if row and row[0] == "graph_enriched":
                logger.info("Document %s already graph-enriched, skipping", document_id)
                return

            result = await self._graph_builder.build(  # type: ignore[union-attr]
                entities, scope=scope, document_id=document_id
            )

            enrichment_provenance = {
                "source_pipeline": self._pipeline_name,
                "source_task": "graph_enrichment",
            }
            for edge in result.edges:
                stamped = edge.model_copy(
                    update={
                        "metadata": {**edge.metadata, **enrichment_provenance},
                    }
                )
                self._graph.insert_edge(stamped)

            self._set_status(document_id, "graph_enriched", scope=scope)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Graph enrichment failed for document %s",
                document_id,
                exc_info=True,
            )

    def _schedule_inter_doc_enrichment(
        self,
        document_id: str,
        extract_results: list[ExtractionResult],
        scope: str,
    ) -> None:
        """Schedule non-blocking inter-document graph enrichment if builder is available."""
        if self._inter_doc_builder is None:
            return
        entities = [e for r in extract_results for e in r.entities]
        if not entities:
            return

        # Skip if fewer than 2 documents exist in scope.
        doc_count = self._conn.execute(
            "SELECT COUNT(*) FROM document_status WHERE scope = ?",
            (scope,),
        ).fetchone()[0]
        _min_docs = 2
        if doc_count < _min_docs:
            return

        logger.info(
            "Scheduling inter-document graph enrichment for document %s",
            document_id,
        )
        task = asyncio.create_task(self._enrich_inter_doc_graph(document_id, entities, scope))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _enrich_inter_doc_graph(
        self,
        document_id: str,
        entities: list[Entity],
        scope: str,
    ) -> None:
        """Background task: run inter-doc graph builder and store inferred edges."""
        try:
            result = await self._inter_doc_builder.build(  # type: ignore[union-attr]
                entities, scope=scope, document_id=document_id
            )

            for edge in result.edges:
                self._graph.insert_edge(edge)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Inter-document graph enrichment failed for document %s",
                document_id,
                exc_info=True,
            )

    @staticmethod
    async def _read_source(source: str | Path) -> IntakeResult:
        """Dispatch to the appropriate intake reader."""
        if isinstance(source, Path):
            return await read_file(source)
        if str(source).startswith(("http://", "https://")):
            return await read_url(str(source))
        return await read_file(source)

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

    async def _run_extract(self, chunks: list[Chunk]) -> list[ExtractionResult]:
        """Run entity extraction per chunk (LLM I/O-bound)."""
        results = []
        for chunk in chunks:
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
            self._store_embeddings(document_id, chunks, embed_result, scope=scope)  # type: ignore[arg-type]
        else:
            logger.warning("Embedding failed for document %s: %s", document_id, embed_result)

        if extract_ok:
            entity_count, edge_count = self._store_extractions(
                extract_result,
                scope=scope,
                document_id=document_id,  # type: ignore[arg-type]
                chunk_ids=chunk_ids,
            )
            try:
                self._store_entity_embeddings(extract_result, scope=scope)  # type: ignore[arg-type]
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

    def _set_status(
        self,
        document_id: str,
        status: str,
        source: str | None = None,
        error: str | None = None,
        *,
        scope: str = "global",
    ) -> None:
        """Insert or update the ``document_status`` row."""
        now = datetime.now(tz=UTC).isoformat()
        existing = self._conn.execute(
            "SELECT document_id FROM document_status WHERE document_id = ?",
            (document_id,),
        ).fetchone()

        if existing is None:
            self._conn.execute(
                "INSERT INTO document_status "
                "(document_id, status, source, error, scope, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (document_id, status, source, error, scope, now, now),
            )
        else:
            self._conn.execute(
                "UPDATE document_status SET status = ?, error = ?, scope = ?, updated_at = ? "
                "WHERE document_id = ?",
                (status, error, scope, now, document_id),
            )
        self._conn.commit()

    def _insert_document(
        self, document_id: str, intake: IntakeResult, *, scope: str = "global"
    ) -> None:
        """Insert a document record into the ``documents`` table."""
        now = datetime.now(tz=UTC).isoformat()
        self._conn.execute(
            "INSERT INTO documents (id, title, content, metadata, scope, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                document_id,
                intake.source,
                intake.content,
                json.dumps(intake.metadata),
                scope,
                now,
            ),
        )
        self._conn.commit()

    def _store_chunks(
        self, document_id: str, chunks: list[Chunk], *, scope: str = "global"
    ) -> list[str]:
        """Insert chunks into the ``chunks`` table.

        Returns
        -------
        list[str]
            The generated chunk IDs, in the same order as *chunks*.
        """
        now = datetime.now(tz=UTC).isoformat()
        chunk_ids: list[str] = []
        for chunk in chunks:
            chunk_id = uuid4().hex
            chunk_ids.append(chunk_id)
            self._conn.execute(
                "INSERT INTO chunks "
                "(id, document_id, chunk_index, content, metadata, scope, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    chunk_id,
                    document_id,
                    chunk.index,
                    chunk.text,
                    json.dumps(chunk.metadata),
                    scope,
                    now,
                ),
            )
        self._conn.commit()
        return chunk_ids

    def _store_embeddings(
        self,
        document_id: str,
        chunks: list[Chunk],
        embeddings: list[HybridEmbedding],
        *,
        scope: str = "global",
    ) -> None:
        """Store chunk embeddings in the vector store."""
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            embed_id = f"{document_id}:chunk:{chunk.index}"
            self._vectors.store_embedding(embed_id, embedding, "document", scope=scope)

    def _store_extractions(
        self,
        results: list[ExtractionResult],
        *,
        scope: str = "global",
        document_id: str | None = None,
        chunk_ids: list[str] | None = None,
    ) -> tuple[int, int]:
        """Store entities and edges in the graph store.

        Parameters
        ----------
        chunk_ids:
            When provided, must be the same length as *results*.  Each
            extraction result's entities are stamped with the
            corresponding chunk_id.
        """
        provenance = {
            "source_pipeline": self._pipeline_name,
            "source_task": "entity_extraction",
        }
        entity_count = 0
        edge_count = 0
        for idx, result in enumerate(results):
            cid = chunk_ids[idx] if chunk_ids is not None else None
            for entity in result.entities:
                updates: dict[str, object] = {
                    "scope": scope,
                    "metadata": {**entity.metadata, **provenance},
                }
                if document_id is not None:
                    updates["document_id"] = document_id
                if cid is not None:
                    updates["chunk_id"] = cid
                scoped = entity.model_copy(update=updates)
                self._graph.insert_entity(scoped)
                entity_count += 1
            for edge in result.edges:
                scoped = edge.model_copy(
                    update={
                        "scope": scope,
                        "metadata": {**edge.metadata, **provenance},
                    }
                )
                self._graph.insert_edge(scoped)
                edge_count += 1
        return entity_count, edge_count

    def _store_entity_embeddings(
        self, results: list[ExtractionResult], *, scope: str = "global"
    ) -> None:
        """Embed entity descriptions and store with ``embedding_type='entity'``."""
        entities = [e for r in results for e in r.entities if e.description]
        if not entities:
            return
        texts = [e.description for e in entities]
        if hasattr(self._embedder, "embed_hybrid"):
            embeddings = self._embedder.embed_hybrid(texts)
        else:
            dense_vecs = self._embedder.embed(texts)
            embeddings = [HybridEmbedding(dense=v) for v in dense_vecs]
        for entity, embedding in zip(entities, embeddings, strict=True):
            self._vectors.store_embedding(entity.id, embedding, "entity", scope=scope)
