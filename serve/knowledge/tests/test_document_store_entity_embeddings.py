"""DocumentStore entity embedding scope regressions."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Entity, EntityType
from owlbear_knowledge.schema import init_db


class RecordingVectorStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.deleted: list[str] = []

    def store_embedding(self, **kwargs: object) -> None:
        self.calls.append(kwargs)

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        self.deleted.append(entity_or_doc_id)
        return True


class FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] for index, _ in enumerate(texts)]


def test_store_entity_embeddings_preserves_entity_scope_with_method_fallback() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    vector_store = RecordingVectorStore()
    store = DocumentStore(conn, GraphStore(conn), vector_store, FakeEmbedder())
    entities = [
        Entity(id="explicit", name="Explicit", entity_type=EntityType.CONCEPT, scope="team"),
        Entity(id="fallback", name="Fallback", entity_type=EntityType.CONCEPT),
    ]

    store.store_entity_embeddings(entities, scope="method-scope")

    assert [(call["entity_or_doc_id"], call["scope"]) for call in vector_store.calls] == [
        ("explicit", "team"),
        ("fallback", "method-scope"),
    ]


def test_delete_document_data_removes_chunk_and_entity_embeddings() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    vector_store = RecordingVectorStore()
    store = DocumentStore(conn, GraphStore(conn), vector_store, FakeEmbedder())
    conn.execute(
        "INSERT INTO documents (id, title, content, metadata, created_at, scope) VALUES (?, ?, ?, ?, ?, ?)",
        ("doc-1", "Doc", "content", "{}", "2026-01-01T00:00:00Z", "team"),
    )
    conn.execute(
        "INSERT INTO chunks (id, document_id, chunk_index, content, metadata, created_at, scope)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("chunk-1", "doc-1", 0, "chunk", "{}", "2026-01-01T00:00:00Z", "team"),
    )
    conn.execute(
        "INSERT INTO entities (id, name, entity_type, description, metadata, created_at, scope, document_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("entity-1", "Entity", "concept", "", "{}", "2026-01-01T00:00:00Z", "team", "doc-1"),
    )
    conn.commit()

    store.delete_document_data("doc-1")

    assert vector_store.deleted == ["chunk-1", "entity-1"]


def test_store_embeddings_falls_back_when_hybrid_result_not_concrete() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    vector_store = RecordingVectorStore()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1], [0.2]]
    store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

    store.store_embeddings(["chunk-a", "chunk-b"], ["a", "b"], scope="team")

    assert embedder.embed_hybrid.called
    assert embedder.embed.called
    assert [(call["entity_or_doc_id"], call["embedding"], call["scope"]) for call in vector_store.calls] == [
        ("chunk-a", [0.1], "team"),
        ("chunk-b", [0.2], "team"),
    ]


def test_store_embeddings_rejects_embedding_count_mismatch() -> None:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    vector_store = RecordingVectorStore()
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1]]
    store = DocumentStore(conn, GraphStore(conn), vector_store, embedder)

    with pytest.raises(ValueError, match="embedding count does not match chunk count"):
        store.store_embeddings(["chunk-a", "chunk-b"], ["a", "b"])

    assert vector_store.calls == []
