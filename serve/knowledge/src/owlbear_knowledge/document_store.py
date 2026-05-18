"""Document persistence facade: chunks, embeddings, extractions, and status tracking."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from owlbear_knowledge.status_store import StatusStore

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import sqlite3

    from owlbear_knowledge.chunker import Chunk
    from owlbear_knowledge.extractor import ExtractionResult
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.intake import IntakeResult
    from owlbear_knowledge.models import Document, Entity
    from owlbear_knowledge.protocol import HybridEmbedding
    from owlbear_knowledge.status_store import DocumentStatus


class DocumentStore:
    """Persistence facade for documents, chunks, embeddings, and entity extractions.

    Args:
        conn: Open SQLite connection with schema already initialised.
        graph_store: GraphStore for document and entity-graph operations.
        vector_store: VectorStoreProtocol implementation for embedding storage.
        embedder: EmbeddingProvider for generating text embeddings.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        vector_store: object,
        embedder: object,
    ) -> None:
        self._conn = conn
        self._graph = graph_store
        self._vector = vector_store
        self._embedder = embedder
        self._status = StatusStore(conn)

    # ── Documents ─────────────────────────────────────────────────────────

    def insert_document(
        self,
        document_id_or_doc: str | Document,
        intake: IntakeResult | None = None,
        *,
        scope: str = "global",
        source_id: str | None = None,
    ) -> None:
        """Persist a document to the documents table.

        Supports two calling conventions:

        - New API: ``insert_document(document_id, intake, *, scope, source_id)``
        - Legacy API: ``insert_document(doc)``  — accepts a Document object.
        """
        if isinstance(document_id_or_doc, str):
            now = datetime.now(tz=UTC).isoformat()
            self._conn.execute(
                "INSERT OR REPLACE INTO documents"
                " (id, title, content, metadata, created_at, scope, source_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    document_id_or_doc,
                    intake.source if intake else "",
                    intake.content if intake else "",
                    json.dumps(dict(intake.metadata)) if intake else "{}",
                    now,
                    scope,
                    source_id,
                ),
            )
            self._conn.commit()
        else:
            # Legacy API: insert_document(doc: Document)
            self._graph.insert_document(document_id_or_doc)

    # ── Chunks ────────────────────────────────────────────────────────────

    def store_chunks(self, document_id: str, chunks: list[Chunk], *, scope: str = "global") -> list[str]:
        """Insert chunk rows for *document_id* and return their IDs.

        Args:
            document_id: Parent document ID.
            chunks: List of :class:`~owlbear_knowledge.chunker.Chunk` objects.
            scope: Scope tag for the chunk rows.  Defaults to ``'global'``.

        Returns:
            List of generated chunk IDs (same length as *chunks*).
        """
        now = datetime.now(tz=UTC).isoformat()
        # Ensure a minimal document row exists to satisfy FK constraint.
        self._conn.execute(
            "INSERT OR IGNORE INTO documents (id, title, content, metadata, created_at) VALUES (?, '', '', '{}', ?)",
            (document_id, now),
        )
        chunk_ids: list[str] = []
        for chunk in chunks:
            chunk_id = uuid4().hex
            self._conn.execute(
                "INSERT INTO chunks"
                " (id, document_id, chunk_index, content, metadata, created_at, scope)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    chunk_id,
                    document_id,
                    chunk.index,
                    chunk.text,
                    json.dumps(chunk.metadata),
                    now,
                    scope,
                ),
            )
            chunk_ids.append(chunk_id)
        self._conn.commit()
        return chunk_ids

    # ── Embeddings ────────────────────────────────────────────────────────

    def store_embeddings(
        self,
        document_id_or_chunk_ids: str | list[str],
        chunks_or_texts: list[Chunk] | list[str],
        embeddings: list[HybridEmbedding] | None = None,
        *,
        scope: str = "global",
    ) -> None:
        """Store embeddings for document chunks.

        Supports two calling conventions:

        - New API: ``store_embeddings(document_id, chunks, embeddings, *, scope)``
          — stores pre-computed :class:`~owlbear_knowledge.protocol.HybridEmbedding` objects.
        - Legacy API: ``store_embeddings(chunk_ids, chunk_texts)``
          — embeds *chunk_texts* internally and stores one embedding per chunk ID.
        """
        if isinstance(document_id_or_chunk_ids, str):
            # New API
            if not embeddings:
                return
            for chunk, embedding in zip(chunks_or_texts, embeddings, strict=False):
                self._vector.store_embedding(  # type: ignore[union-attr]
                    entity_or_doc_id=f"{document_id_or_chunk_ids}_{chunk.index}",  # type: ignore[union-attr]
                    embedding=embedding,
                    embedding_type="document",
                    scope=scope,
                )
        else:
            # Legacy API: (chunk_ids, chunk_texts)
            chunk_ids = document_id_or_chunk_ids
            chunk_texts = chunks_or_texts
            if not chunk_ids:
                return
            # Prefer hybrid embeddings (dense+sparse+ColBERT) when available
            if hasattr(self._embedder, "embed_hybrid"):
                hybrid_embs = self._embedder.embed_hybrid(chunk_texts)  # type: ignore[union-attr]
                for cid, emb in zip(chunk_ids, hybrid_embs, strict=False):
                    self._vector.store_embedding(  # type: ignore[union-attr]
                        entity_or_doc_id=cid,
                        embedding=emb,
                        embedding_type="document",
                        scope=scope,
                    )
            else:
                computed: list[list[float]] = self._embedder.embed(chunk_texts)  # type: ignore[union-attr]
                for cid, emb in zip(chunk_ids, computed, strict=False):
                    self._vector.store_embedding(  # type: ignore[union-attr]
                        entity_or_doc_id=cid,
                        embedding=emb,
                        embedding_type="document",
                        scope=scope,
                    )

    def store_entity_embeddings(
        self,
        entities_or_results: list[Entity] | list[ExtractionResult] | None = None,
        *,
        results: list[ExtractionResult] | None = None,
        scope: str = "global",
    ) -> None:
        """Embed entity descriptions and store with embedding_type='entity'.

        Supports two calling conventions:

        - New API: ``store_entity_embeddings(results=[...], scope=...)``
          — extracts entities from :class:`~owlbear_knowledge.extractor.ExtractionResult` list.
        - Legacy API: ``store_entity_embeddings(entities)``
          — accepts a list of :class:`~owlbear_knowledge.models.Entity` objects.

                Entity objects with an explicitly set ``scope`` keep that scope;
                otherwise the method-level ``scope`` is used for vector provenance.
        """
        if results is not None:
            # New API: extract entities from ExtractionResult list
            entities: list[Entity] = [e for r in results for e in (r.entities or [])]  # type: ignore[union-attr,misc]
        else:
            entities = entities_or_results or []  # type: ignore[assignment]
        if not entities:
            return
        texts = [e.description or e.name for e in entities]  # type: ignore[union-attr]
        computed: list[list[float]] = self._embedder.embed(texts)  # type: ignore[union-attr]
        for entity, emb in zip(entities, computed, strict=False):
            fields_set = getattr(entity, "model_fields_set", set())
            entity_scope = getattr(entity, "scope", None) if "scope" in fields_set else None
            vector_scope = entity_scope if isinstance(entity_scope, str) and entity_scope else scope
            self._vector.store_embedding(  # type: ignore[union-attr]
                entity_or_doc_id=entity.id,  # type: ignore[union-attr]
                embedding=emb,
                embedding_type="entity",
                scope=vector_scope,
            )

    # ── Entity extractions ────────────────────────────────────────────────

    def store_extractions(
        self,
        results: list[ExtractionResult],
        *,
        scope: str = "global",
        document_id: str = "",
        chunk_ids: list[str] | None = None,
        pipeline_name: str = "ingest",
    ) -> tuple[int, int]:
        """Persist entities and edges from *results* and return counts.

        Args:
            results: List of :class:`~owlbear_knowledge.extractor.ExtractionResult`.
            scope: Scope tag for provenance metadata.
            document_id: Source document ID for provenance stamping.
            chunk_ids: Source chunk IDs for provenance stamping.
            pipeline_name: Pipeline name for provenance metadata.  Defaults to ``'ingest'``.

        Returns:
            Tuple of ``(entity_count, edge_count)``.
        """
        entity_count = 0
        edge_count = 0
        for i, result in enumerate(results):
            assigned_chunk_id = chunk_ids[i] if chunk_ids and i < len(chunk_ids) else None
            for entity in result.entities:  # type: ignore[union-attr]
                stamped = entity.model_copy(
                    update={
                        "scope": scope,
                        "document_id": document_id,
                        "chunk_id": assigned_chunk_id,
                        "metadata": {**entity.metadata, "pipeline_name": pipeline_name},
                    }
                )
                self._graph.insert_entity(stamped)
                entity_count += 1
            for edge in result.edges:  # type: ignore[union-attr]
                stamped_edge = edge.model_copy(
                    update={
                        "scope": scope,
                        "metadata": {
                            **edge.metadata,
                            "pipeline_name": pipeline_name,
                            "document_id": document_id,
                            "scope": scope,
                            "chunk_id": assigned_chunk_id,
                        },
                    }
                )
                self._graph.insert_edge(stamped_edge, document_id=document_id)
                edge_count += 1
        return entity_count, edge_count

    def delete_chunk_embeddings(self, chunk_ids: list[str]) -> None:
        """Best-effort deletion of vector payloads for chunk IDs."""
        if not chunk_ids:
            return
        for chunk_id in chunk_ids:
            try:
                self._vector.delete_embedding(chunk_id)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                logger.debug("chunk embedding cleanup failed", exc_info=True)

    # ── Cascade delete ────────────────────────────────────────────────────

    def delete_document_data(self, document_id: str) -> None:
        """Cascade-delete all data associated with *document_id*.

        Removes rows from: entities, edges, chunks, document_status, documents.

        Args:
            document_id: The document to delete.
        """
        chunk_rows = self._conn.execute("SELECT id FROM chunks WHERE document_id = ?", (document_id,)).fetchall()
        chunk_ids = [row[0] for row in chunk_rows]
        self.delete_chunk_embeddings(chunk_ids)

        # Delete entities and their edges for this document
        entity_rows = self._conn.execute("SELECT id FROM entities WHERE document_id = ?", (document_id,)).fetchall()
        for (eid,) in entity_rows:
            self._conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (eid, eid))
        self._conn.execute("DELETE FROM entities WHERE document_id = ?", (document_id,))
        # Delete chunks
        self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        # Delete document status
        self._conn.execute("DELETE FROM document_status WHERE document_id = ?", (document_id,))
        # Delete document
        self._conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        self._conn.commit()

    def delete_source_cascade(self, source_id: str) -> None:
        """Cascade-delete all data associated with *source_id*.

        Removes rows from: source_pages, documents (and their downstream
        entities, edges, chunks, document_status) for the given source_id.

        Args:
            source_id: The knowledge source ID to delete.
        """
        doc_rows = self._conn.execute("SELECT id FROM documents WHERE source_id = ?", (source_id,)).fetchall()
        for (doc_id,) in doc_rows:
            self.delete_document_data(doc_id)
        self._conn.execute("DELETE FROM source_pages WHERE source_id = ?", (source_id,))
        self._conn.commit()

    # ── Status ────────────────────────────────────────────────────────────

    def set_status(
        self,
        document_id: str,
        status: str,
        source: str | None = None,
        error: str | None = None,
        *,
        scope: str = "global",
    ) -> None:
        """Insert or update the document_status row for *document_id*."""
        self._status.set_status(document_id, status, source=source, error=error, scope=scope)

    def find_status_by_source(self, source: str, scope: str = "global") -> DocumentStatus | None:
        """Look up a previously-ingested document by source URI."""
        return self._status.find_status_by_source(source, scope)

    def check_content_changed(self, source: str, content: str, scope: str = "global") -> tuple[bool, str | None]:
        """Check whether *content* differs from the previously-ingested version.

        Returns:
            ``(changed, existing_document_id)``
        """
        return self._status.check_content_changed(source, content, scope)

    def update_content_hash(self, document_id: str, content: str) -> None:
        """Store the content hash for *document_id* to enable future delta checks."""
        self._status.update_content_hash(document_id, content)
