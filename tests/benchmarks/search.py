"""4-mode search harness for IR benchmarking.

Runs all queries against a pre-populated Qdrant collection in four
isolated search modes (dense-only, sparse-only, hybrid-RRF,
hybrid+ColBERT) and produces ``ranx.Run`` objects with per-query
latency tracking.

Task: #379
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from qdrant_client import models as qmodels

from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.qdrant import _PREFETCH_MULTIPLIER

from .harness import build_run, make_latency_tracker, record_latency

if TYPE_CHECKING:
    from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider
    from owlbear.memory.knowledge.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public constants — mode identifiers
# ---------------------------------------------------------------------------

MODE_DENSE = "dense"
"""Dense-only vector search."""

MODE_SPARSE = "sparse"
"""Sparse-only (lexical) vector search."""

MODE_HYBRID_RRF = "hybrid_rrf"
"""Dense + sparse prefetch with Reciprocal Rank Fusion."""

MODE_HYBRID_COLBERT = "hybrid_colbert"
"""Full 3-stage pipeline: dense+sparse prefetch → RRF → ColBERT rescore."""

MODES = [MODE_DENSE, MODE_SPARSE, MODE_HYBRID_RRF, MODE_HYBRID_COLBERT]
"""All benchmark search modes, in execution order."""


# ---------------------------------------------------------------------------
# Public harness entry point
# ---------------------------------------------------------------------------


def run_search_benchmark(
    store: QdrantVectorStore,
    queries: dict[str, str],
    embedding_provider: BgeM3EmbeddingProvider,
    *,
    top_k: int = 10,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    """Run all queries in four search modes, recording latency.

    Embeds all queries once using *embedding_provider*, then executes
    each mode independently against the same *store*.

    Args:
        store: Pre-populated Qdrant vector store.
        queries: Mapping of ``{query_id: query_text}``.
        embedding_provider: Embedding provider (or mock) with
            ``embed_hybrid(texts)`` method.
        top_k: Maximum results per query per mode.

    Returns:
        A 2-tuple of ``(runs, latencies)`` where:

        - **runs** maps mode name → ``ranx.Run`` object.
        - **latencies** maps mode name → list of per-query elapsed
          seconds.
    """
    # Embed all queries in a single batch.
    query_ids = list(queries.keys())
    query_texts = [queries[qid] for qid in query_ids]
    query_embeddings = embedding_provider.embed_hybrid(query_texts)

    latencies = make_latency_tracker()
    runs_raw: dict[str, dict[str, dict[str, float]]] = {}

    for mode in MODES:
        logger.info("Running mode: %s (%d queries)", mode, len(query_ids))
        runs_raw[mode] = {}

        for qid, emb in zip(query_ids, query_embeddings, strict=True):
            start = time.perf_counter()
            results = _search_one(store, emb, mode, top_k)
            elapsed = time.perf_counter() - start
            record_latency(latencies, mode, elapsed)
            runs_raw[mode][qid] = dict(results)

    runs = {mode: build_run(raw) for mode, raw in runs_raw.items()}
    return runs, dict(latencies)


# ---------------------------------------------------------------------------
# Per-mode search dispatchers
# ---------------------------------------------------------------------------


def _search_one(
    store: QdrantVectorStore,
    emb: HybridEmbedding,
    mode: str,
    top_k: int,
) -> list[tuple[str, float]]:
    """Dispatch a single query to the appropriate search strategy."""
    if mode == MODE_DENSE:
        return _dense_search(store, emb.dense, top_k)
    if mode == MODE_SPARSE:
        return _sparse_search(store, emb, top_k)
    if mode == MODE_HYBRID_RRF:
        return _hybrid_rrf_search(store, emb, top_k)
    if mode == MODE_HYBRID_COLBERT:
        return _hybrid_colbert_search(store, emb, top_k)
    msg = f"Unknown search mode: {mode!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Mode 1 — Dense-only
# ---------------------------------------------------------------------------


def _dense_search(
    store: QdrantVectorStore,
    dense: list[float],
    top_k: int,
) -> list[tuple[str, float]]:
    """Plain dense vector search via ``search_similar``."""
    return store.search_similar(dense, top_k=top_k)


# ---------------------------------------------------------------------------
# Mode 2 — Sparse-only
# ---------------------------------------------------------------------------


def _sparse_search(
    store: QdrantVectorStore,
    emb: HybridEmbedding,
    top_k: int,
) -> list[tuple[str, float]]:
    """Sparse-only search using the Qdrant client directly.

    ``search_similar`` requires at least a dense vector, so this
    mode calls the Qdrant ``query_points`` API directly with a
    sparse-only query.
    """
    if emb.sparse is None:
        return []

    store._ensure_collection()
    result = store._client.query_points(
        collection_name=store._collection,
        query=qmodels.SparseVector(
            indices=emb.sparse.indices,
            values=emb.sparse.values,
        ),
        using="sparse",
        limit=top_k,
        with_payload=True,
    )

    return [
        (p.payload["entity_or_doc_id"], p.score)
        for p in result.points
        if p.payload and "entity_or_doc_id" in p.payload
    ]


# ---------------------------------------------------------------------------
# Mode 3 — Hybrid RRF (dense + sparse prefetch, fusion, no ColBERT)
# ---------------------------------------------------------------------------


def _hybrid_rrf_search(
    store: QdrantVectorStore,
    emb: HybridEmbedding,
    top_k: int,
) -> list[tuple[str, float]]:
    """Dense + sparse prefetch with Reciprocal Rank Fusion.

    Uses Qdrant's ``FusionQuery(Fusion.RRF)`` to merge dense and
    sparse prefetch results — no ColBERT rescore.
    """
    store._ensure_collection()

    prefetch: list[qmodels.Prefetch] = []

    if emb.sparse is not None:
        prefetch.append(
            qmodels.Prefetch(
                query=qmodels.SparseVector(
                    indices=emb.sparse.indices,
                    values=emb.sparse.values,
                ),
                using="sparse",
                limit=top_k * _PREFETCH_MULTIPLIER,
            ),
        )

    prefetch.append(
        qmodels.Prefetch(
            query=emb.dense,
            using="dense",
            limit=top_k * _PREFETCH_MULTIPLIER,
        ),
    )

    result = store._client.query_points(
        collection_name=store._collection,
        prefetch=prefetch,
        query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )

    return [
        (p.payload["entity_or_doc_id"], p.score)
        for p in result.points
        if p.payload and "entity_or_doc_id" in p.payload
    ]


# ---------------------------------------------------------------------------
# Mode 4 — Hybrid + ColBERT rescore
# ---------------------------------------------------------------------------


def _hybrid_colbert_search(
    store: QdrantVectorStore,
    emb: HybridEmbedding,
    top_k: int,
) -> list[tuple[str, float]]:
    """Full 3-stage pipeline: prefetch → RRF fusion → ColBERT rescore.

    Uses ``search_similar`` with a full ``HybridEmbedding`` containing
    dense, sparse, and ColBERT vectors.
    """
    return store.search_similar(emb, top_k=top_k)
