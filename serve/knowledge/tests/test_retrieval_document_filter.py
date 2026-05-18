"""Retrieval vector filtering regressions."""

from __future__ import annotations

from owlbear_knowledge.retrieval import GraphAugmentedRetriever


class FakeVectorStore:
    def __init__(self) -> None:
        self.embedding_type: str | None = None

    def search_similar(
        self,
        _query_embedding: object,
        top_k: int = 5,
        embedding_type: str | None = None,
        *,
        scopes: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        _ = top_k, scopes
        self.embedding_type = embedding_type
        return []


class FakeEmbeddingProvider:
    def embed(self, _queries: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3]]


class FakeGraphStore:
    pass


def test_graph_augmented_retriever_filters_to_document_embeddings() -> None:
    vector_store = FakeVectorStore()
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=FakeGraphStore(),  # type: ignore[arg-type]
        embedding_provider=FakeEmbeddingProvider(),  # type: ignore[arg-type]
    )

    retriever.retrieve("where is the doc?", top_k=3)

    assert vector_store.embedding_type == "document"
