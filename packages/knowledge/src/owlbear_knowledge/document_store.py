"""Document persistence facade: chunks, embeddings, extractions, and status tracking."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from owlbear_knowledge.status_store import StatusStore

if TYPE_CHECKING:
    import sqlite3

    from owlbear_knowledge.chunker import Chunk
    from owlbear_knowledge.extractor import ExtractionResult
    from owlbear_knowledge.graph_store import GraphStore
    from owlbear_knowledge.models import Document, Entity
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

    def insert_document(self, doc: Document) -> None:
        """Persist *doc* to the documents table via GraphStore."""
        self._graph.insert_document(doc)

    # ── Chunks ────────────────────────────────────────────────────────────

    def store_chunks(self, document_id: str, chunks: list[Chunk]) -> list[str]:
        """Insert chunk rows for *document_id* and return their IDs.

        Args:
            document_id: Parent document ID.
            chunks: List of :class:`~owlbear_knowledge.chunker.Chunk` objects.

        Returns:
            List of generated chunk IDs (same length as *chunks*).
        """
        now = datetime.now(tz=UTC).isoformat()
        # Ensure a minimal document row exists to satisfy FK constraint.
        self._conn.execute(
            "INSERT OR IGNORE INTO documents (id, title, content, metadata, created_at)"
            " VALUES (?, '', '', '{}', ?)",
            (document_id, now),
        )
        chunk_ids: list[str] = []
        for chunk in chunks:
            chunk_id = uuid4().hex
            self._conn.execute(
                "INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    chunk_id,
                    document_id,
                    chunk.index,
                    chunk.text,
                    json.dumps(chunk.metadata),
                    now,
                ),
            )
            chunk_ids.append(chunk_id)
        self._conn.commit()
        return chunk_ids

    # ── Embeddings ────────────────────────────────────────────────────────

    def store_embeddings(self, chunk_ids: list[str], chunk_texts: list[str]) -> None:
        """Embed *chunk_texts* and store one embedding per chunk ID.

        Args:
            chunk_ids: IDs matching *chunk_texts* positionally.
            chunk_texts: Raw text for each chunk.
        """
        if not chunk_ids:
            return
        embeddings: list[list[float]] = self._embedder.embed(chunk_texts)  # type: ignore[union-attr]
        for cid, emb in zip(chunk_ids, embeddings, strict=False):
            self._vector.store_embedding(  # type: ignore[union-attr]
                entity_or_doc_id=cid,
                embedding=emb,
                embedding_type="document",
            )

    def store_entity_embeddings(self, entities: list[Entity]) -> None:
        """Embed entity descriptions and store with embedding_type='entity'.

        Args:
            entities: Entities to embed.  Uses *description* if set, else *name*.
        """
        if not entities:
            return
        texts = [e.description or e.name for e in entities]  # type: ignore[union-attr]
        embeddings: list[list[float]] = self._embedder.embed(texts)  # type: ignore[union-attr]
        for entity, emb in zip(entities, embeddings, strict=False):
            self._vector.store_embedding(  # type: ignore[union-attr]
                entity_or_doc_id=entity.id,  # type: ignore[union-attr]
                embedding=emb,
                embedding_type="entity",
            )

    # ── Entity extractions ────────────────────────────────────────────────

    def store_extractions(self, results: list[ExtractionResult]) -> tuple[int, int]:
        """Persist entities and edges from *results* and return counts.

        Args:
            results: List of :class:`~owlbear_knowledge.extractor.ExtractionResult`.

        Returns:
            Tuple of ``(entity_count, edge_count)``.
        """
        entity_count = 0
        edge_count = 0
        for result in results:
            for entity in result.entities:  # type: ignore[union-attr]
                self._graph.insert_entity(entity)
                entity_count += 1
            for edge in result.edges:  # type: ignore[union-attr]
                self._graph.insert_edge(edge)
                edge_count += 1
        return entity_count, edge_count

    # ── Cascade delete ────────────────────────────────────────────────────

    def delete_document_data(self, document_id: str) -> None:
        """Cascade-delete all data associated with *document_id*.

        Removes rows from: entities, edges, chunks, document_status, documents.

        Args:
            document_id: The document to delete.
        """
        # Delete entities and their edges for this document
        entity_rows = self._conn.execute(
            "SELECT id FROM entities WHERE document_id = ?", (document_id,)
        ).fetchall()
        for (eid,) in entity_rows:
            self._conn.execute(
                "DELETE FROM edges WHERE source_id = ? OR target_id = ?", (eid, eid)
            )
        self._conn.execute("DELETE FROM entities WHERE document_id = ?", (document_id,))
        # Delete chunks
        self._conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        # Delete document status
        self._conn.execute(
            "DELETE FROM document_status WHERE document_id = ?", (document_id,)
        )
        # Delete document
        self._conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
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

    def find_status_by_source(
        self, source: str, scope: str = "global"
    ) -> DocumentStatus | None:
        """Look up a previously-ingested document by source URI."""
        return self._status.find_status_by_source(source, scope)

    def check_content_changed(
        self, source: str, content: str, scope: str = "global"
    ) -> tuple[bool, str | None]:
        """Check whether *content* differs from the previously-ingested version.

        Returns:
            ``(changed, existing_document_id)``
        """
        return self._status.check_content_changed(source, content, scope)

    def update_content_hash(self, document_id: str, content: str) -> None:
        """Store the content hash for *document_id* to enable future delta checks."""
        self._status.update_content_hash(document_id, content)


