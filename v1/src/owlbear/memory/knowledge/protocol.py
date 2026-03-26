"""Vector store protocol and hybrid embedding models.

Defines :class:`VectorStoreProtocol` — the minimum interface that any
vector backend (e.g. Qdrant) must satisfy — along with
:class:`SparseVector`, :class:`HybridEmbedding`, and the
:data:`Embedding` convenience alias.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel


class SparseVector(BaseModel):
    """Sparse vector representation (matches Qdrant SparseVector shape).

    Attributes:
    ----------
    indices:
        Non-zero dimension indices.
    values:
        Corresponding float weights.
    """

    indices: list[int]
    values: list[float]


class HybridEmbedding(BaseModel):
    """Multi-representation embedding for hybrid search.

    Attributes:
    ----------
    dense:
        Dense float vector (always present).
    sparse:
        Optional sparse token-weight vector for lexical matching.
    colbert:
        Optional list of per-token dense vectors for late interaction.
    """

    dense: list[float]
    sparse: SparseVector | None = None
    colbert: list[list[float]] | None = None


Embedding = list[float] | HybridEmbedding
"""Type alias: either a plain dense vector or a full hybrid embedding."""


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Minimum interface for a vector storage backend.

    Any vector backend (e.g. :class:`~owlbear.memory.knowledge.qdrant.QdrantVectorStore`)
    must satisfy this protocol.
    """

    def store_embedding(
        self,
        entity_or_doc_id: str,
        embedding: list[float] | HybridEmbedding,
        embedding_type: Literal["entity", "document"],
        scope: str = "global",
    ) -> None: ...

    def get_embedding(self, entity_or_doc_id: str) -> list[float] | None: ...

    def search_similar(  # noqa: PLR0913
        self,
        query_embedding: list[float] | HybridEmbedding,
        top_k: int = 5,
        embedding_type: Literal["entity", "document"] | None = None,
        *,
        scopes: list[str] | None = None,
        recency_weight: float = 0.0,
        decay_rate: float = 0.001,
    ) -> list[tuple[str, float]]: ...

    def delete_embedding(self, entity_or_doc_id: str) -> bool: ...
