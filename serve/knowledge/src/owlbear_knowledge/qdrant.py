"""Qdrant-backed vector storage for hybrid search."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Literal

from owlbear_knowledge.embeddings import HybridEmbedding

try:
    from qdrant_client import QdrantClient
    from qdrant_client import models as qmodels
except ImportError:
    QdrantClient = None  # type: ignore[assignment,misc]
    qmodels = None  # type: ignore[assignment]

COLLECTION_NAME = "owlbear_vectors"
DENSE_DIM = 1024


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _point_id(entity_or_doc_id: str) -> str:
    """Deterministic UUID5 string from entity/document ID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, entity_or_doc_id))


class QdrantVectorStore:
    """Qdrant-backed vector store implementing VectorStoreProtocol.

    Args:
        location: Qdrant storage location — ``':memory:'`` for in-memory
            or a filesystem path for persistent storage.
        collection_name: Name of the Qdrant collection.
    """

    def __init__(
        self,
        location: str = ":memory:",
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        if QdrantClient is None:
            msg = (
                "qdrant-client is required for QdrantVectorStore. "
                "Install with: uv pip install 'owlbear-knowledge[qdrant]'"
            )
            raise ImportError(msg)

        if location == ":memory:" or location.startswith(("http://", "https://")):
            self._client: QdrantClient = QdrantClient(location=location)  # type: ignore[misc]
        else:
            self._client: QdrantClient = QdrantClient(path=location)  # type: ignore[misc]
        self._collection = collection_name
        self._initialized = False
        self._has_colbert = False

    def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it doesn't exist yet."""
        if self._initialized:
            return
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config={
                    "dense": qmodels.VectorParams(
                        size=DENSE_DIM,
                        distance=qmodels.Distance.COSINE,
                    ),
                    "colbert": qmodels.VectorParams(
                        size=DENSE_DIM,
                        distance=qmodels.Distance.COSINE,
                        multivector_config=qmodels.MultiVectorConfig(
                            comparator=qmodels.MultiVectorComparator.MAX_SIM,
                        ),
                    ),
                },
                sparse_vectors_config={
                    "sparse": qmodels.SparseVectorParams(),
                },
            )
            self._has_colbert = True
        else:
            # Check if existing collection has the "colbert" named vector.
            info = self._client.get_collection(self._collection)
            vectors_cfg = info.config.params.vectors
            self._has_colbert = isinstance(vectors_cfg, dict) and "colbert" in vectors_cfg
        self._initialized = True

    def store_embedding(
        self,
        entity_or_doc_id: str,
        embedding: list[float] | HybridEmbedding,
        embedding_type: Literal["entity", "document"],
        scope: str = "global",
    ) -> None:
        """Store (or upsert) an embedding for the given ID."""
        self._ensure_collection()
        point_id = _point_id(entity_or_doc_id)
        now = datetime.now(UTC).isoformat()
        payload = {
            "entity_or_doc_id": entity_or_doc_id,
            "embedding_type": embedding_type,
            "scope": scope,
            "created_at": now,
        }
        if isinstance(embedding, HybridEmbedding):
            vectors: dict = {"dense": embedding.dense}
            if embedding.sparse is not None:
                vectors["sparse"] = qmodels.SparseVector(
                    indices=embedding.sparse.indices,
                    values=embedding.sparse.values,
                )
            if embedding.colbert is not None and self._has_colbert:
                vectors["colbert"] = embedding.colbert
        else:
            vectors = {"dense": embedding}

        self._client.upsert(
            collection_name=self._collection,
            points=[
                qmodels.PointStruct(
                    id=point_id,
                    vector=vectors,
                    payload=payload,
                ),
            ],
        )

    def get_embedding(self, entity_or_doc_id: str) -> list[float] | None:
        """Return the stored dense vector for *entity_or_doc_id*, or None."""
        self._ensure_collection()
        point_id = _point_id(entity_or_doc_id)
        results = self._client.retrieve(
            collection_name=self._collection,
            ids=[point_id],
            with_vectors=["dense"],
        )
        if not results:
            return None
        vector = results[0].vector
        if isinstance(vector, dict):
            dense = vector.get("dense")
            if isinstance(dense, list):
                return dense
        return None

    def search_similar(  # noqa: PLR0913
        self,
        query_embedding: list[float] | HybridEmbedding,
        top_k: int = 5,
        embedding_type: Literal["entity", "document"] | None = None,
        *,
        scopes: list[str] | None = None,
        recency_weight: float = 0.0,  # noqa: ARG002
        decay_rate: float = 0.001,  # noqa: ARG002
    ) -> list[tuple[str, float]]:
        """Find the most similar embeddings to *query_embedding*."""
        self._ensure_collection()

        must_conditions: list = []
        if embedding_type is not None:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="embedding_type",
                    match=qmodels.MatchValue(value=embedding_type),
                ),
            )
        if scopes is not None:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="scope",
                    match=qmodels.MatchAny(any=scopes),
                ),
            )
        query_filter = qmodels.Filter(must=must_conditions) if must_conditions else None

        if isinstance(query_embedding, HybridEmbedding) and query_embedding.sparse is not None:
            return self._hybrid_search(query_embedding, top_k, query_filter)

        dense_vec = query_embedding.dense if isinstance(query_embedding, HybridEmbedding) else query_embedding
        response = self._client.query_points(
            collection_name=self._collection,
            query=dense_vec,
            using="dense",
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            (point.payload["entity_or_doc_id"], point.score)  # type: ignore[index]
            for point in response.points
        ]

    def _hybrid_search(
        self,
        query_embedding: HybridEmbedding,
        top_k: int,
        query_filter: object | None,
    ) -> list[tuple[str, float]]:
        """Run Qdrant prefetch+RRF hybrid search with absolute cosine scoring.

        Results are ordered by hybrid ranking quality (RRF + optional ColBERT
        rerank) but scored by dense cosine similarity — an absolute metric
        suitable for threshold filtering.
        """
        assert query_embedding.sparse is not None  # guaranteed by caller
        dense_prefetch = qmodels.Prefetch(
            query=query_embedding.dense,
            using="dense",
            limit=top_k * 10,
        )
        sparse_prefetch = qmodels.Prefetch(
            query=qmodels.SparseVector(
                indices=query_embedding.sparse.indices,
                values=query_embedding.sparse.values,
            ),
            using="sparse",
            limit=top_k * 10,
        )

        if query_embedding.colbert is not None and self._has_colbert:
            # Two-stage: prefetch with dense+sparse via RRF, rerank with ColBERT MaxSim.
            # Filter to document embeddings only — entity embeddings lack ColBERT vectors
            # and the local Qdrant client's MaxSim fails on points without them.
            colbert_filter_conditions = [
                qmodels.FieldCondition(
                    key="embedding_type",
                    match=qmodels.MatchValue(value="document"),
                ),
            ]
            if query_filter is not None and hasattr(query_filter, "must") and query_filter.must:
                colbert_filter_conditions.extend(query_filter.must)
            colbert_filter = qmodels.Filter(must=colbert_filter_conditions)

            rrf_prefetch = qmodels.Prefetch(
                prefetch=[dense_prefetch, sparse_prefetch],
                query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
                limit=top_k * 5,
                filter=colbert_filter,
            )
            response = self._client.query_points(
                collection_name=self._collection,
                prefetch=[rrf_prefetch],
                query=query_embedding.colbert,
                using="colbert",
                limit=top_k,
                with_payload=True,
                with_vectors=["dense"],
            )
        else:
            response = self._client.query_points(
                collection_name=self._collection,
                prefetch=[dense_prefetch, sparse_prefetch],
                query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=["dense"],
            )

        # Score each result by dense cosine similarity (absolute quality metric)
        # while preserving hybrid ranking order.
        results: list[tuple[str, float]] = []
        for point in response.points:
            doc_id = point.payload["entity_or_doc_id"]  # type: ignore[index]
            stored_dense = (  # type: ignore[union-attr]
                point.vector.get("dense") if isinstance(point.vector, dict) else None
            )
            if stored_dense is not None:
                score = _cosine_similarity(query_embedding.dense, stored_dense)
            else:
                # Fallback: use normalized hybrid score if dense vector unavailable
                score = point.score if point.score is not None else 0.0
            results.append((doc_id, score))
        return results

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        """Delete the embedding for *entity_or_doc_id*.

        Returns True if found and deleted, False otherwise.
        """
        self._ensure_collection()
        point_id = _point_id(entity_or_doc_id)
        existing = self._client.retrieve(
            collection_name=self._collection,
            ids=[point_id],
        )
        if not existing:
            return False
        self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.PointIdsList(points=[point_id]),
        )
        return True
