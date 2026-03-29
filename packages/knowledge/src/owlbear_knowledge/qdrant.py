"""Qdrant-backed vector storage — stub, not yet implemented (#15)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from owlbear_knowledge.protocol import HybridEmbedding

COLLECTION_NAME = "owlbear_vectors"
DENSE_DIM = 1024

_NOT_IMPL = "QdrantVectorStore not yet extracted from v1"


class QdrantVectorStore:
    """Stub — raises NotImplementedError until extracted from v1."""

    def __init__(
        self,
        location: str = ":memory:",
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        raise NotImplementedError(_NOT_IMPL)

    def store_embedding(
        self,
        entity_or_doc_id: str,
        embedding: list[float] | HybridEmbedding,
        embedding_type: Literal["entity", "document"],
        scope: str = "global",
    ) -> None:
        raise NotImplementedError

    def get_embedding(self, entity_or_doc_id: str) -> list[float] | None:
        raise NotImplementedError

    def search_similar(  # noqa: PLR0913
        self,
        query_embedding: list[float] | HybridEmbedding,
        top_k: int = 5,
        embedding_type: Literal["entity", "document"] | None = None,
        *,
        scopes: list[str] | None = None,
        recency_weight: float = 0.0,
        decay_rate: float = 0.001,
    ) -> list[tuple[str, float]]:
        raise NotImplementedError

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        raise NotImplementedError
