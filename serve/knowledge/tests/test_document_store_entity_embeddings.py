"""DocumentStore entity embedding scope regressions."""

from __future__ import annotations

import sqlite3

from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Entity, EntityType
from owlbear_knowledge.schema import init_db


class RecordingVectorStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def store_embedding(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


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
