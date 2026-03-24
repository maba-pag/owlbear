"""Document CRUD store — extracted from IngestPipeline.

Provides :class:`DocumentStore`, which owns all database and vector-store
operations for document status tracking, chunk storage, embedding storage,
and entity/edge persistence.  :class:`IngestPipeline` delegates to this
class for all storage concerns.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from owlbear.memory.knowledge.protocol import HybridEmbedding

if TYPE_CHECKING:
    import sqlite3

    from owlbear.memory.knowledge.chunker import Chunk
    from owlbear.memory.knowledge.embeddings import EmbeddingProvider
    from owlbear.memory.knowledge.extractor import ExtractionResult
    from owlbear.memory.knowledge.graph import GraphStore
    from owlbear.memory.knowledge.intake import IntakeResult
    from owlbear.memory.knowledge.protocol import VectorStoreProtocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DocumentStatus(BaseModel):
    """Status record for a previously-ingested document."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    content_hash: str | None
    status: str


# ---------------------------------------------------------------------------
# Content hashing
# ---------------------------------------------------------------------------


def compute_content_hash(content: str) -> str:
    """Return the SHA-256 hex digest of *content* after stripping whitespace.

    Args:
        content: Raw document text. Leading/trailing whitespace is stripped
            before hashing so that cosmetic differences (e.g. trailing
            newlines in HTTP responses) do not produce false positives.

    Returns:
        str: 64-character lowercase hex digest.
    """
    return hashlib.sha256(content.strip().encode()).hexdigest()


# ---------------------------------------------------------------------------
# DocumentStore
# ---------------------------------------------------------------------------


class DocumentStore:
    """Database and vector-store CRUD for documents, chunks, and entities.

    Args:
        conn: SQLite connection with the knowledge schema already applied.
        graph_store: Store for entities and edges.
        vector_store: Store for chunk/entity embeddings.
        embedding_provider: Batch embedding provider (for entity embeddings).
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        graph_store: GraphStore,
        vector_store: VectorStoreProtocol,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._conn = conn
        self._graph = graph_store
        self._vectors = vector_store
        self._embedder = embedding_provider

    @property
    def conn(self) -> sqlite3.Connection:
        """The underlying SQLite connection."""
        return self._conn

    @property
    def graph_store(self) -> GraphStore:
        """The graph store for entities and edges."""
        return self._graph

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """The embedding provider."""
        return self._embedder

    # -- Status tracking -----------------------------------------------------

    def find_status_by_source(self, source: str, scope: str = "global") -> DocumentStatus | None:
        """Look up a previously-ingested document by source URI."""
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

        Returns:
            tuple[bool, str | None]: ``(changed, existing_document_id)``.
        """
        new_hash = compute_content_hash(content)
        existing = self.find_status_by_source(source, scope=scope)
        if existing is None:
            return True, None
        if existing.content_hash == new_hash:
            return False, existing.document_id
        return True, existing.document_id

    def set_status(
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

    def update_content_hash(self, document_id: str, content: str) -> None:
        """Store the content hash in ``document_status`` for future delta checks."""
        content_hash = compute_content_hash(content)
        self._conn.execute(
            "UPDATE document_status SET content_hash = ? WHERE document_id = ?",
            (content_hash, document_id),
        )
        self._conn.commit()

    # -- Document / chunk CRUD -----------------------------------------------

    def insert_document(
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

    def store_chunks(
        self, document_id: str, chunks: list[Chunk], *, scope: str = "global"
    ) -> list[str]:
        """Insert chunks into the ``chunks`` table.

        Returns the generated chunk IDs in the same order as *chunks*.
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

    # -- Embedding / extraction storage --------------------------------------

    def store_embeddings(
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

    def store_extractions(
        self,
        results: list[ExtractionResult],
        *,
        scope: str = "global",
        document_id: str | None = None,
        chunk_ids: list[str] | None = None,
        pipeline_name: str = "ingest",
    ) -> tuple[int, int]:
        """Store entities and edges in the graph store.

        Args:
            results: Extraction outputs to persist into entity and edge tables.
            scope: Logical tenant scope for stored graph records.
            document_id: Optional document identifier stamped into entity metadata.
            chunk_ids: When provided, must be the same length as *results*.
                Each extraction result's entities are stamped with the
                corresponding chunk_id.
            pipeline_name: Provenance label stamped on metadata.
        """
        provenance = {
            "source_pipeline": pipeline_name,
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

    def store_entity_embeddings(
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

    # -- Deletion ------------------------------------------------------------

    def delete_document_data(self, document_id: str) -> None:
        """Cascade-delete all data for *document_id* across SQLite and Qdrant.

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
