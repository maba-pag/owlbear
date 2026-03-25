"""Qdrant-backed vector storage for hybrid search.

Provides :class:`QdrantVectorStore` — a
:class:`~owlbear.memory.knowledge.protocol.VectorStoreProtocol`
implementation backed by qdrant-client.  Supports dense, sparse,
and ColBERT multi-vector storage with prefetch+rescore hybrid
retrieval.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from owlbear.memory.knowledge.models import EntityType
from owlbear.memory.knowledge.protocol import HybridEmbedding

try:
    from qdrant_client import QdrantClient
    from qdrant_client import models as qmodels
except ImportError:
    QdrantClient = None  # type: ignore[assignment,misc]
    qmodels = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLLECTION_NAME = "owlbear_vectors"
"""Single Qdrant collection for all embeddings, discriminated by payload."""

DENSE_DIM = 1024
"""Dimensionality of the dense embedding vectors."""

IMPORTANCE_BY_TYPE: dict[EntityType, float] = {
    EntityType.DECISION: 0.9,
    EntityType.PATTERN: 0.8,
    EntityType.CONCEPT: 0.7,
    EntityType.CLASS_: 0.5,
    EntityType.FUNCTION: 0.4,
    EntityType.FILE: 0.3,
}
"""Maps entity type values to importance weights for temporal decay."""

_PREFETCH_MULTIPLIER = 10
"""Over-fetch factor for prefetch stage — 10x candidates gives rescore enough material."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _point_id(entity_or_doc_id: str) -> str:
    """Deterministic UUID5 string from entity/document ID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, entity_or_doc_id))


def _compute_recency_score(
    created_at_iso: str,
    decay_rate: float,
    importance: float = 0.5,
) -> float:
    """Compute a temporal recency score in ``[0, 1]``.

    Score decays exponentially with importance-based resistance:
    ``(1 - decay_rate * (1 - importance)) ** hours_since_created``.

    Args:
        created_at_iso (str): ISO-8601 datetime string for when the item was created.
        decay_rate (float): Base hourly decay rate.
        importance (float): Importance weight in ``[0, 1]`` that dampens decay.
    """
    created = datetime.fromisoformat(created_at_iso)
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    hours = max((datetime.now(UTC) - created).total_seconds() / 3600, 0.0)
    effective_decay = decay_rate * (1.0 - importance)
    return (1.0 - effective_decay) ** hours


# ---------------------------------------------------------------------------
# QdrantVectorStore
# ---------------------------------------------------------------------------


class QdrantVectorStore:
    """Qdrant-backed vector store implementing :class:`VectorStoreProtocol`.

    Stores dense, sparse, and ColBERT multi-vector embeddings in a single
    Qdrant collection with payload-based discrimination.

    Args:
        location (str): Qdrant storage location — ``':memory:'`` for in-memory or a
            filesystem path for persistent storage.
        collection_name (str): Name of the Qdrant collection (default ``'owlbear_vectors'``).
    """

    def __init__(
        self,
        location: str = ":memory:",
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        if QdrantClient is None:
            msg = (
                "qdrant-client is required for QdrantVectorStore. "
                "Install with: uv pip install 'owlbear[knowledge]'"
            )
            raise ImportError(msg)

        # ``location=`` interprets drive letters (``C:``) as URL schemes on
        # Windows.  Use ``path=`` for on-disk storage so Qdrant opens the
        # local directory correctly.
        if location == ":memory:" or location.startswith(("http://", "https://")):
            self._client: QdrantClient = QdrantClient(location=location)  # type: ignore[misc]
        else:
            self._client: QdrantClient = QdrantClient(path=location)  # type: ignore[misc]
        self._collection = collection_name
        self._initialized = False

    # -- lazy init ----------------------------------------------------------

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist yet."""
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
                        hnsw_config=qmodels.HnswConfigDiff(m=0),
                        quantization_config=qmodels.ScalarQuantization(
                            scalar=qmodels.ScalarQuantizationConfig(
                                type=qmodels.ScalarType.INT8,
                                quantile=0.99,
                                always_ram=True,
                            ),
                        ),
                    ),
                },
                sparse_vectors_config={
                    "sparse": qmodels.SparseVectorParams(),
                },
            )

        self._initialized = True

    # -- public API ---------------------------------------------------------

    def store_embedding(
        self,
        entity_or_doc_id: str,
        embedding: list[float] | HybridEmbedding,
        embedding_type: Literal["entity", "document"],
        scope: str = "global",
    ) -> None:
        """Store (or upsert) an embedding for the given ID.

        Args:
            entity_or_doc_id (str): Unique string identifier for the entity or document.
            embedding (list[float] | HybridEmbedding): Dense vector
                (``list[float]``) or full hybrid embedding.
            embedding_type (Literal['entity', 'document']): Whether this is an
                ``'entity'`` or ``'document'`` embedding.
            scope (str): Visibility scope stored in payload (default ``'global'``).
        """
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
            if embedding.colbert is not None:
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
        """Return the stored dense vector for *entity_or_doc_id*, or ``None``."""
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
        recency_weight: float = 0.0,
        decay_rate: float = 0.001,
    ) -> list[tuple[str, float]]:
        """Find the most similar embeddings to *query_embedding*.

        For ``list[float]`` queries, performs a plain dense search.
        For :class:`HybridEmbedding` queries, uses prefetch (sparse + dense)
        with ColBERT rescore when all vectors are available.

        Args:
            query_embedding (list[float] | HybridEmbedding): Dense vector or full hybrid embedding.
            top_k (int): Maximum number of results.
            embedding_type (Literal['entity', 'document'] | None): Restrict to
                ``'entity'`` or ``'document'`` only.
            scopes (list[str] | None): Filter by scope payload field.
            recency_weight (float): Blend weight for temporal freshness boost.
            decay_rate (float): Hourly exponential decay rate for recency scoring.
        """
        self._ensure_collection()

        # Build filter conditions.
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

        if isinstance(query_embedding, HybridEmbedding):
            results = self._hybrid_search(query_embedding, top_k, query_filter)
        else:
            results = self._dense_search(query_embedding, top_k, query_filter)

        if recency_weight > 0 and results:
            results = self._apply_temporal_boost(
                results,
                recency_weight,
                decay_rate,
            )

        return results[:top_k]

    def delete_embedding(self, entity_or_doc_id: str) -> bool:
        """Delete the embedding for *entity_or_doc_id*.

        Returns ``True`` if found and deleted, ``False`` otherwise.
        """
        self._ensure_collection()

        point_id = _point_id(entity_or_doc_id)

        # Check if point exists.
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

    def delete_by_document_id(self, document_id: str) -> int:
        """Delete all points whose ``entity_or_doc_id`` contains *document_id*.

        Uses scroll+delete to find and remove all matching points.
        This is NOT part of the protocol — it's an extra convenience
        method.

        Returns the number of deleted points.
        """
        self._ensure_collection()

        scroll_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="entity_or_doc_id",
                    match=qmodels.MatchText(text=document_id),
                ),
            ],
        )

        points, _next_offset = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=scroll_filter,
            limit=10_000,
        )

        if not points:
            return 0

        ids = [p.id for p in points]
        self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.PointIdsList(points=ids),
        )
        return len(ids)

    # -- private search methods ---------------------------------------------

    def _dense_search(
        self,
        query: list[float],
        top_k: int,
        query_filter: qmodels.Filter | None,
    ) -> list[tuple[str, float]]:
        """Plain dense vector search."""
        result = self._client.query_points(
            collection_name=self._collection,
            query=query,
            using="dense",
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            (p.payload["entity_or_doc_id"], p.score)
            for p in result.points
            if p.payload and "entity_or_doc_id" in p.payload
        ]

    def _hybrid_search(
        self,
        query: HybridEmbedding,
        top_k: int,
        query_filter: qmodels.Filter | None,
    ) -> list[tuple[str, float]]:
        """Prefetch (sparse + dense) with ColBERT rescore."""
        prefetch: list = []

        # Add sparse prefetch if available.
        if query.sparse is not None:
            prefetch.append(
                qmodels.Prefetch(
                    query=qmodels.SparseVector(
                        indices=query.sparse.indices,
                        values=query.sparse.values,
                    ),
                    using="sparse",
                    limit=top_k * _PREFETCH_MULTIPLIER,
                    filter=query_filter,
                ),
            )

        # Always add dense prefetch.
        prefetch.append(
            qmodels.Prefetch(
                query=query.dense,
                using="dense",
                limit=top_k * _PREFETCH_MULTIPLIER,
                filter=query_filter,
            ),
        )

        # ColBERT rescore when available.
        if query.colbert is not None and prefetch:
            result = self._client.query_points(
                collection_name=self._collection,
                prefetch=prefetch,
                query=query.colbert,
                using="colbert",
                limit=top_k,
                with_payload=True,
            )
        else:
            # Fallback to dense-only search.
            result = self._client.query_points(
                collection_name=self._collection,
                query=query.dense,
                using="dense",
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )

        return [
            (p.payload["entity_or_doc_id"], p.score)
            for p in result.points
            if p.payload and "entity_or_doc_id" in p.payload
        ]

    def _apply_temporal_boost(
        self,
        results: list[tuple[str, float]],
        recency_weight: float,
        decay_rate: float,
    ) -> list[tuple[str, float]]:
        """Re-score results using temporal freshness (higher = better)."""
        if not results:
            return []

        # Batch-retrieve all points in a single call
        ids = [_point_id(rid) for rid, _ in results]
        points = self._client.retrieve(
            collection_name=self._collection,
            ids=ids,
            with_payload=True,
        )

        # Build lookup keyed by str(point.id)
        lookup: dict[str, dict] = {}
        for p in points:
            if p.payload:
                lookup[str(p.id)] = p.payload

        adjusted: list[tuple[str, float]] = []
        for rid, score in results:
            payload = lookup.get(str(_point_id(rid)))
            if payload:
                created_at = payload.get("created_at")
                if created_at:
                    recency = _compute_recency_score(created_at, decay_rate)
                    adjusted.append((rid, score + recency_weight * recency))
                    continue
            adjusted.append((rid, score))

        adjusted.sort(key=lambda r: r[1], reverse=True)
        return adjusted
