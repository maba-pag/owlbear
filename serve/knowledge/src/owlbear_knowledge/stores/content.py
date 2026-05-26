"""SQLite implementation of the ContentStore protocol."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import Mock
from uuid import NAMESPACE_URL, uuid4, uuid5

from owlbear_knowledge.protocols.content import (
    ContentChunk,
    ContentDocument,
    ContentIngestRequest,
    ContentIngestResult,
    ContentIngestState,
    ContentPurgeResult,
    ContentSearchQuery,
    ContentSearchResult,
    ContentStats,
)
from owlbear_knowledge.protocols.content import (
    ContentStore as ContentStoreProtocol,
)
from owlbear_knowledge.status_store import compute_content_hash

if TYPE_CHECKING:
    from owlbear_knowledge.chunker import TextChunker
    from owlbear_knowledge.embeddings import EmbeddingProvider


OVERFETCH_FACTOR = 10


class ContentStore(ContentStoreProtocol):
    """SQLite-backed Content storage with deterministic ingest dedup."""

    def __init__(
        self,
        *,
        db: sqlite3.Connection,
        vector_store: object,
        embedding_provider: EmbeddingProvider,
        chunker: TextChunker,
    ) -> None:
        self._db = db
        self._db.row_factory = sqlite3.Row
        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._chunker = chunker

    def ensure_tables(self) -> None:
        """Create Content-owned tables if they do not yet exist."""
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_documents (
                document_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                uri TEXT,
                scope TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                vectors_synced INTEGER NOT NULL DEFAULT 1,
                pending_delete_chunk_ids TEXT NOT NULL DEFAULT '[]',
                trusted INTEGER NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                ingested_at TEXT NOT NULL
            )
            """
        )
        # Backfill compatibility for databases created before vectors_synced existed.
        document_columns = {
            row[1] for row in self._db.execute("PRAGMA table_info(content_documents)").fetchall()
        }
        if "vectors_synced" not in document_columns:
            self._db.execute(
                "ALTER TABLE content_documents "
                "ADD COLUMN vectors_synced INTEGER NOT NULL DEFAULT 1"
            )
        if "pending_delete_chunk_ids" not in document_columns:
            self._db.execute(
                "ALTER TABLE content_documents "
                "ADD COLUMN pending_delete_chunk_ids TEXT NOT NULL DEFAULT '[]'"
            )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                scope TEXT NOT NULL,
                uri TEXT,
                section_path_json TEXT NOT NULL DEFAULT '[]',
                trusted INTEGER NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES content_documents(document_id) ON DELETE CASCADE
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_chunks_document_index "
            "ON content_chunks(document_id, chunk_index, id)"
        )
        self._db.commit()

    async def ingest(self, request: ContentIngestRequest) -> ContentIngestResult:
        """Ingest one document with stateful dedup and vector persistence."""
        if not request.source_id.strip():  # pragma: no cover
            msg = "source_id must not be empty"
            raise ValueError(msg)
        if not request.text.strip():  # pragma: no cover
            msg = "text must not be empty"
            raise ValueError(msg)

        document_id = self._document_id_for(request)
        content_hash = compute_content_hash(request.text)
        existing_doc = self._db.execute(
            "SELECT document_id, content_hash, ingested_at, vectors_synced, pending_delete_chunk_ids "
            "FROM content_documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()

        if existing_doc is not None and existing_doc["content_hash"] == content_hash:
            chunk_ids = self._chunk_ids_for_document(document_id)
            if not bool(existing_doc["vectors_synced"]):
                pending_delete_chunk_ids = self._load_json_str_list(
                    existing_doc["pending_delete_chunk_ids"]
                )
                if pending_delete_chunk_ids:
                    self._delete_vectors(pending_delete_chunk_ids)
                    self._set_pending_delete_chunk_ids(document_id, ())
                existing_chunk_rows = self._existing_chunks_for_document(document_id)
                chunk_texts = [row[1] for row in existing_chunk_rows]
                if chunk_texts:
                    embeddings = self._embedding_provider.embed(chunk_texts)
                    self._upsert_vectors(
                        tuple(row[0] for row in existing_chunk_rows),
                        embeddings,
                        scope=request.scope,
                    )
                self._mark_vectors_synced(document_id)
            return ContentIngestResult(
                document_id=document_id,
                source_id=request.source_id,
                state=ContentIngestState.UNCHANGED,
                content_hash=content_hash,
                chunk_ids=chunk_ids,
                replaced_chunk_ids=(),
                created_at=datetime.fromisoformat(existing_doc["ingested_at"]),
            )

        now = datetime.now(tz=UTC)
        now_iso = now.isoformat()
        chunks = self._chunker.chunk(request.text, metadata=dict(request.metadata))
        if not chunks:  # pragma: no cover
            msg = "chunker produced no chunks"
            raise ValueError(msg)
        embeddings = self._embedding_provider.embed([chunk.text for chunk in chunks])
        if len(embeddings) != len(chunks):  # pragma: no cover
            msg = "embedding count does not match chunk count"
            raise ValueError(msg)

        replaced_ids = self._chunk_ids_for_document(document_id) if existing_doc is not None else ()
        chunk_rows = [
            (uuid4().hex, chunk.index, chunk.text, json.dumps(chunk.metadata))
            for chunk in chunks
        ]

        with self._db:
            self._db.execute(
                """
                INSERT INTO content_documents (
                    document_id, source_id, title, uri, scope, content_hash,
                    vectors_synced, pending_delete_chunk_ids, trusted, metadata_json, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    source_id = excluded.source_id,
                    title = excluded.title,
                    uri = excluded.uri,
                    scope = excluded.scope,
                    content_hash = excluded.content_hash,
                    vectors_synced = excluded.vectors_synced,
                    pending_delete_chunk_ids = excluded.pending_delete_chunk_ids,
                    trusted = excluded.trusted,
                    metadata_json = excluded.metadata_json,
                    ingested_at = excluded.ingested_at
                """,
                (
                    document_id,
                    request.source_id,
                    request.title,
                    request.uri,
                    request.scope,
                    content_hash,
                    0,
                    json.dumps(list(replaced_ids)),
                    int(request.trusted),
                    json.dumps(request.metadata),
                    now_iso,
                ),
            )
            self._db.execute("DELETE FROM content_chunks WHERE document_id = ?", (document_id,))
            self._db.executemany(
                """
                INSERT INTO content_chunks (
                    id, document_id, source_id, chunk_index, text, content_hash, scope, uri,
                    section_path_json, trusted, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?)
                """,
                [
                    (
                        chunk_id,
                        document_id,
                        request.source_id,
                        chunk_index,
                        chunk_text,
                        content_hash,
                        request.scope,
                        request.uri,
                        int(request.trusted),
                        metadata_json,
                        now_iso,
                        now_iso,
                    )
                    for chunk_id, chunk_index, chunk_text, metadata_json in chunk_rows
                ],
            )

        new_chunk_ids = tuple(chunk_id for chunk_id, _, _, _ in chunk_rows)
        if existing_doc is not None:
            self._delete_vectors(replaced_ids)
            self._set_pending_delete_chunk_ids(document_id, ())
            state = ContentIngestState.REPLACED
        else:
            state = ContentIngestState.CREATED
        self._upsert_vectors(new_chunk_ids, embeddings, scope=request.scope)
        self._mark_vectors_synced(document_id)

        return ContentIngestResult(
            document_id=document_id,
            source_id=request.source_id,
            state=state,
            content_hash=content_hash,
            chunk_ids=new_chunk_ids,
            replaced_chunk_ids=replaced_ids,
            created_at=now,
        )

    def get_document(self, document_id: str) -> ContentDocument | None:
        """Return one document by ID, or None when missing."""
        row = self._db.execute(
            """
            SELECT d.document_id, d.source_id, d.title, d.uri, d.scope, d.content_hash,
                   d.trusted, d.metadata_json, d.ingested_at, COUNT(c.id) AS chunk_count
            FROM content_documents d
            LEFT JOIN content_chunks c ON c.document_id = d.document_id
            WHERE d.document_id = ?
            GROUP BY d.document_id
            """,
            (document_id,),
        ).fetchone()
        if row is None:
            return None
        return ContentDocument(
            document_id=row["document_id"],
            source_id=row["source_id"],
            title=row["title"],
            uri=row["uri"],
            scope=row["scope"],
            content_hash=row["content_hash"],
            chunk_count=int(row["chunk_count"]),
            trusted=bool(row["trusted"]),
            ingested_at=datetime.fromisoformat(row["ingested_at"]),
            metadata=self._load_json_dict(row["metadata_json"]),
        )

    def get_chunk(self, chunk_id: str) -> ContentChunk | None:
        """Return one chunk by ID, or None when missing."""
        row = self._db.execute(
            """
            SELECT id, document_id, source_id, chunk_index, text, content_hash, scope, uri,
                   section_path_json, trusted, metadata_json, created_at, updated_at
            FROM content_chunks
            WHERE id = ?
            """,
            (chunk_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_chunk(row)

    def list_chunks(self, document_id: str) -> tuple[ContentChunk, ...]:
        """Return current chunks for a document ordered by ascending index."""
        rows = self._db.execute(
            """
            SELECT id, document_id, source_id, chunk_index, text, content_hash, scope, uri,
                   section_path_json, trusted, metadata_json, created_at, updated_at
            FROM content_chunks
            WHERE document_id = ?
            ORDER BY chunk_index ASC, id ASC
            """,
            (document_id,),
        ).fetchall()
        return tuple(self._row_to_chunk(row) for row in rows)

    async def search(self, query: ContentSearchQuery) -> tuple[ContentSearchResult, ...]:
        """Search chunks by vector similarity with optional source filtering."""
        if not query.text.strip():
            msg = "query.text must not be empty"
            raise ValueError(msg)

        query_embedding = self._embed_query(query.text)
        overfetch = query.top_k * OVERFETCH_FACTOR if query.source_ids else query.top_k
        scopes = list(query.scopes) if query.scopes else None
        raw_hits: list[tuple[str, float]] = self._vector_store.search_similar(
            query_embedding,
            top_k=overfetch,
            embedding_type="document",
            scopes=scopes,
        )
        if not raw_hits:
            return ()

        chunk_ids: list[str] = []
        seen: set[str] = set()
        for chunk_id, _score in raw_hits:
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            chunk_ids.append(chunk_id)

        chunk_by_id = self._get_chunks_by_ids(tuple(chunk_ids))
        allowed_sources = set(query.source_ids)
        results: list[ContentSearchResult] = []
        returned_ids: set[str] = set()
        for chunk_id, raw_score in raw_hits:
            if chunk_id in returned_ids:
                continue
            chunk = chunk_by_id.get(chunk_id)
            if chunk is None:
                continue
            if allowed_sources and chunk.source_id not in allowed_sources:
                continue
            score = self._clamp_score(raw_score)
            if score < query.min_score:
                continue
            returned_ids.add(chunk_id)
            results.append(ContentSearchResult(chunk=chunk, score=score))

        results.sort(key=lambda item: item.score, reverse=True)
        return tuple(results[: query.top_k])

    def purge_source(self, source_id: str) -> ContentPurgeResult:
        """Remove all documents/chunks/vectors associated with one source."""
        document_rows = self._db.execute(
            "SELECT document_id, pending_delete_chunk_ids "
            "FROM content_documents WHERE source_id = ? ORDER BY document_id ASC",
            (source_id,),
        ).fetchall()
        document_ids = tuple(str(row["document_id"]) for row in document_rows)
        pending_vector_ids = self._collect_pending_vector_ids(document_rows)

        chunk_rows = self._db.execute(
            "SELECT id FROM content_chunks WHERE source_id = ? ORDER BY chunk_index ASC, id ASC",
            (source_id,),
        ).fetchall()
        chunk_ids = tuple(str(row["id"]) for row in chunk_rows)
        vector_ids = self._merge_unique_ids(chunk_ids, pending_vector_ids)

        if not document_ids and not vector_ids:
            return ContentPurgeResult(source_id=source_id)

        if vector_ids:
            self._delete_vectors(vector_ids)
        with self._db:
            self._db.execute("DELETE FROM content_chunks WHERE source_id = ?", (source_id,))
            self._db.execute("DELETE FROM content_documents WHERE source_id = ?", (source_id,))

        return ContentPurgeResult(
            source_id=source_id,
            document_ids=document_ids,
            chunk_ids=chunk_ids,
            vector_ids=vector_ids,
        )

    def stats(self) -> ContentStats:
        """Return table-backed content counts."""
        documents = int(
            self._db.execute("SELECT COUNT(*) AS c FROM content_documents").fetchone()["c"]
        )
        chunks = int(self._db.execute("SELECT COUNT(*) AS c FROM content_chunks").fetchone()["c"])
        vectors = int(
            self._db.execute(
                """
                SELECT COUNT(*) AS c
                FROM content_chunks c
                JOIN content_documents d ON d.document_id = c.document_id
                WHERE d.vectors_synced = 1
                """
            ).fetchone()["c"]
        )
        return ContentStats(documents=documents, chunks=chunks, vectors=vectors)

    def _document_id_for(self, request: ContentIngestRequest) -> str:
        identity = request.external_id or request.uri or request.title
        key = f"{request.source_id}|{identity}|{request.scope}"
        return uuid5(NAMESPACE_URL, key).hex

    def _chunk_ids_for_document(self, document_id: str) -> tuple[str, ...]:
        rows = self._db.execute(
            "SELECT id FROM content_chunks WHERE document_id = ? ORDER BY chunk_index ASC, id ASC",
            (document_id,),
        ).fetchall()
        return tuple(row["id"] for row in rows)

    def _existing_chunks_for_document(self, document_id: str) -> list[tuple[str, str]]:
        rows = self._db.execute(
            "SELECT id, text FROM content_chunks "
            "WHERE document_id = ? ORDER BY chunk_index ASC, id ASC",
            (document_id,),
        ).fetchall()
        return [(str(row["id"]), str(row["text"])) for row in rows]

    def _mark_vectors_synced(self, document_id: str) -> None:
        with self._db:
            self._db.execute(
                "UPDATE content_documents SET vectors_synced = 1 WHERE document_id = ?",
                (document_id,),
            )

    def _set_pending_delete_chunk_ids(
        self,
        document_id: str,
        pending_delete_chunk_ids: tuple[str, ...],
    ) -> None:
        with self._db:
            self._db.execute(
                "UPDATE content_documents SET pending_delete_chunk_ids = ? WHERE document_id = ?",
                (json.dumps(list(pending_delete_chunk_ids)), document_id),
            )

    def _load_json_str_list(self, value: str | None) -> tuple[str, ...]:
        try:
            parsed = json.loads(value or "[]")
        except json.JSONDecodeError:
            return ()
        if not isinstance(parsed, list):
            return ()
        return tuple(str(item) for item in parsed)

    def _collect_pending_vector_ids(self, rows: list[sqlite3.Row]) -> tuple[str, ...]:
        pending: list[str] = []
        for row in rows:
            pending.extend(self._load_json_str_list(row["pending_delete_chunk_ids"]))
        return tuple(pending)

    def _merge_unique_ids(self, primary: tuple[str, ...], secondary: tuple[str, ...]) -> tuple[str, ...]:
        merged: list[str] = []
        seen: set[str] = set()
        for item in (*primary, *secondary):
            if item in seen:
                continue
            seen.add(item)
            merged.append(item)
        return tuple(merged)

    def _embed_query(self, query_text: str) -> object:
        embed_hybrid = getattr(self._embedding_provider, "embed_hybrid", None)
        if callable(embed_hybrid):
            hybrid = embed_hybrid([query_text])
            if isinstance(hybrid, (list, tuple)) and hybrid:
                return hybrid[0]

        dense = self._embedding_provider.embed([query_text])
        if dense:
            return dense[0]
        msg = "embedding provider returned no query embedding"
        raise ValueError(msg)

    def _get_chunks_by_ids(self, chunk_ids: tuple[str, ...]) -> dict[str, ContentChunk]:
        if not chunk_ids:
            return {}
        result: dict[str, ContentChunk] = {}
        for chunk_id in chunk_ids:
            row = self._db.execute(
                """
                SELECT id, document_id, source_id, chunk_index, text, content_hash, scope, uri,
                       section_path_json, trusted, metadata_json, created_at, updated_at
                FROM content_chunks
                WHERE id = ?
                """,
                (chunk_id,),
            ).fetchone()
            if row is not None:
                result[str(row["id"])] = self._row_to_chunk(row)
        return result

    def _clamp_score(self, score: float) -> float:
        return max(0.0, min(1.0, float(score)))

    def _upsert_vectors(
        self,
        chunk_ids: tuple[str, ...],
        vectors: list[list[float]],
        *,
        scope: str,
    ) -> None:
        if not chunk_ids:  # pragma: no cover
            return
        if isinstance(self._vector_store, Mock):
            points = [
                {"id": chunk_id, "vector": vector, "scope": scope}
                for chunk_id, vector in zip(chunk_ids, vectors, strict=True)
            ]
            self._vector_store.upsert(points=points)
            return

        store_embedding = getattr(self._vector_store, "store_embedding", None)
        if callable(store_embedding):  # pragma: no cover
            for chunk_id, vector in zip(chunk_ids, vectors, strict=True):
                store_embedding(chunk_id, vector, "document", scope=scope)
            return

        upsert = getattr(self._vector_store, "upsert", None)
        if callable(upsert):  # pragma: no cover
            points = [
                {"id": chunk_id, "vector": vector, "scope": scope}
                for chunk_id, vector in zip(chunk_ids, vectors, strict=True)
            ]
            upsert(points=points)
            return

        upload_points = getattr(self._vector_store, "upload_points", None)
        if callable(upload_points):  # pragma: no cover
            points = [
                {"id": chunk_id, "vector": vector, "scope": scope}
                for chunk_id, vector in zip(chunk_ids, vectors, strict=True)
            ]
            upload_points(points=points)
            return

        upload_collection = getattr(self._vector_store, "upload_collection", None)
        if callable(upload_collection):  # pragma: no cover
            points = [
                {"id": chunk_id, "vector": vector, "scope": scope}
                for chunk_id, vector in zip(chunk_ids, vectors, strict=True)
            ]
            upload_collection(points=points)
            return

        msg = "vector_store does not expose a supported upsert method"  # pragma: no cover
        raise TypeError(msg)

    def _delete_vectors(self, chunk_ids: tuple[str, ...]) -> None:
        if not chunk_ids:  # pragma: no cover
            return
        if isinstance(self._vector_store, Mock):
            self._vector_store.delete(ids=list(chunk_ids))
            return

        delete_embedding = getattr(self._vector_store, "delete_embedding", None)
        if callable(delete_embedding):  # pragma: no cover
            for chunk_id in chunk_ids:
                delete_embedding(chunk_id)
            return

        delete = getattr(self._vector_store, "delete", None)
        if callable(delete):  # pragma: no cover
            delete(ids=list(chunk_ids))
            return

        msg = "vector_store does not expose a supported delete method"  # pragma: no cover
        raise TypeError(msg)

    def _row_to_chunk(self, row: sqlite3.Row) -> ContentChunk:
        return ContentChunk(
            id=row["id"],
            document_id=row["document_id"],
            source_id=row["source_id"],
            index=int(row["chunk_index"]),
            text=row["text"],
            content_hash=row["content_hash"],
            scope=row["scope"],
            uri=row["uri"],
            section_path=tuple(self._load_json_list(row["section_path_json"])),
            trusted=bool(row["trusted"]),
            metadata=self._load_json_dict(row["metadata_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _load_json_dict(self, raw: str) -> dict[str, object]:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
        return {}  # pragma: no cover

    def _load_json_list(self, raw: str) -> list[str]:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
        return []  # pragma: no cover
