"""Tests for QdrantVectorStore hybrid search dispatch and score normalization — task #160.

AC coverage:
- AC4: search_similar() dispatches to _hybrid_search() when HybridEmbedding.sparse is non-None
- AC5: _hybrid_search() uses 2 Prefetch entries (dense+sparse, limit=top_k*10),
       FusionQuery(Fusion.RRF), and propagates query_filter
- AC6: Hybrid scores are normalized to [0,1] so similarity_threshold=0.3 filtering remains
       functional; raw RRF scores (~0.01-0.03) must not pass through unnormalized

All tests mock the Qdrant client and do not require a running Qdrant instance.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

try:
    import qdrant_client as _qdrant_client  # noqa: F401
    from qdrant_client import models as qmodels
except ImportError:
    pytest.skip(
        "qdrant-client not installed — run: uv pip install 'owlbear-knowledge[qdrant]'",
        allow_module_level=True,
    )

from owlbear_knowledge.protocol import HybridEmbedding, SparseVector
from owlbear_knowledge.qdrant import DENSE_DIM, QdrantVectorStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dense(v: float = 0.1) -> list[float]:
    return [v] * DENSE_DIM


def _sparse() -> SparseVector:
    return SparseVector(indices=[0, 1, 2], values=[0.5, 0.3, 0.2])


def _hybrid_with_sparse() -> HybridEmbedding:
    return HybridEmbedding(dense=_dense(), sparse=_sparse())


def _mock_pt(entity_id: str, score: float) -> MagicMock:
    pt = MagicMock()
    pt.payload = {"entity_or_doc_id": entity_id}
    pt.score = score
    return pt


def _mock_qresponse(*pairs: tuple[str, float]) -> MagicMock:
    resp = MagicMock()
    resp.points = [_mock_pt(pid, s) for pid, s in pairs]
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> QdrantVectorStore:
    """Fresh in-memory store with the collection pre-initialized."""
    s = QdrantVectorStore(location=":memory:")
    s._ensure_collection()
    return s


# ---------------------------------------------------------------------------
# AC4 — search_similar dispatch
# ---------------------------------------------------------------------------


class TestFromAC_HybridSearchDispatch:

    def test_hybrid_sparse_input_uses_fusion_query(self, store: QdrantVectorStore) -> None:
        """search_similar with HybridEmbedding.sparse set must pass FusionQuery to query_points."""
        mock_resp = _mock_qresponse(("doc1", 0.01), ("doc2", 0.02))
        with patch.object(store._client, "query_points", return_value=mock_resp) as mock_qp:
            store.search_similar(_hybrid_with_sparse(), top_k=5)
            call_kw = mock_qp.call_args.kwargs
            query_arg = call_kw.get("query")
            assert isinstance(query_arg, qmodels.FusionQuery), (
                f"Expected FusionQuery for HybridEmbedding+sparse input, got {type(query_arg)}"
            )


# ---------------------------------------------------------------------------
# AC5 — _hybrid_search internals: 2x Prefetch, RRF fusion, query_filter
# ---------------------------------------------------------------------------


class TestFromAC_HybridSearchInternals:

    def test_hybrid_search_uses_exactly_two_prefetch_entries(
        self, store: QdrantVectorStore
    ) -> None:
        """_hybrid_search must build exactly two Prefetch entries (one dense, one sparse)."""
        mock_resp = _mock_qresponse(("doc1", 0.01))
        with patch.object(store._client, "query_points", return_value=mock_resp) as mock_qp:
            store.search_similar(_hybrid_with_sparse(), top_k=5)
            call_kw = mock_qp.call_args.kwargs
            prefetch = call_kw.get("prefetch")
            assert prefetch is not None, "No 'prefetch' kwarg found in query_points call"
            assert len(prefetch) == 2, f"Expected 2 Prefetch entries, got {len(prefetch)}"

    def test_hybrid_search_prefetch_limit_equals_top_k_times_ten(
        self, store: QdrantVectorStore
    ) -> None:
        """Each Prefetch entry must use limit = top_k * 10 for over-retrieval before fusion."""
        top_k = 3
        mock_resp = _mock_qresponse()
        with patch.object(store._client, "query_points", return_value=mock_resp) as mock_qp:
            store.search_similar(_hybrid_with_sparse(), top_k=top_k)
            call_kw = mock_qp.call_args.kwargs
            prefetch = call_kw.get("prefetch", [])
            assert len(prefetch) == 2
            for entry in prefetch:
                assert entry.limit == top_k * 10, (
                    f"Prefetch limit must be top_k * 10 = {top_k * 10}, got {entry.limit}"
                )

    def test_hybrid_search_uses_rrf_fusion(self, store: QdrantVectorStore) -> None:
        """_hybrid_search must fuse with FusionQuery(fusion=Fusion.RRF)."""
        mock_resp = _mock_qresponse(("doc1", 0.01))
        with patch.object(store._client, "query_points", return_value=mock_resp) as mock_qp:
            store.search_similar(_hybrid_with_sparse(), top_k=5)
            call_kw = mock_qp.call_args.kwargs
            query_arg = call_kw.get("query")
            assert isinstance(query_arg, qmodels.FusionQuery)
            assert query_arg.fusion == qmodels.Fusion.RRF, (
                f"Expected Fusion.RRF, got {query_arg.fusion}"
            )

    def test_hybrid_search_query_filter_includes_scope(
        self, store: QdrantVectorStore
    ) -> None:
        """_hybrid_search must propagate scope conditions in query_filter to the fusion query."""
        mock_resp = _mock_qresponse(("doc1", 0.01))
        with patch.object(store._client, "query_points", return_value=mock_resp) as mock_qp:
            store.search_similar(_hybrid_with_sparse(), top_k=5, scopes=["myScope"])
            call_kw = mock_qp.call_args.kwargs
            # Verify the call is a fusion query (not dense-only; this would fail currently)
            assert isinstance(call_kw.get("query"), qmodels.FusionQuery), (
                "Expected FusionQuery for hybrid input; dense path passes no FusionQuery"
            )
            qf = call_kw.get("query_filter")
            assert qf is not None, "query_filter must not be None when scopes are provided"
            assert "myScope" in str(qf), "Scope 'myScope' not found in query_filter"

    def test_hybrid_search_query_filter_includes_embedding_type(
        self, store: QdrantVectorStore
    ) -> None:
        """_hybrid_search must propagate embedding_type conditions in query_filter."""
        mock_resp = _mock_qresponse(("doc1", 0.01))
        with patch.object(store._client, "query_points", return_value=mock_resp) as mock_qp:
            store.search_similar(
                _hybrid_with_sparse(), top_k=5, embedding_type="document"
            )
            call_kw = mock_qp.call_args.kwargs
            # Verify hybrid path (fusion query)
            assert isinstance(call_kw.get("query"), qmodels.FusionQuery), (
                "Expected FusionQuery for hybrid input"
            )
            qf = call_kw.get("query_filter")
            assert qf is not None, "query_filter must not be None when embedding_type is set"
            assert "document" in str(qf), "Embedding type 'document' not in query_filter"


# ---------------------------------------------------------------------------
# AC6 — Score normalization: raw RRF scores must be normalized to [0, 1]
# ---------------------------------------------------------------------------


class TestFromAC_HybridScoreNormalization:

    def test_hybrid_scores_max_above_similarity_threshold(
        self, store: QdrantVectorStore
    ) -> None:
        """Raw RRF scores (~0.01-0.03) must be normalized so max score > 0.3 threshold.

        Without normalization, the default similarity_threshold=0.3 rejects all hybrid
        results because 0.03 < 0.3. After min-max or DBSF normalization the top score
        should reach close to 1.0, well above the threshold.
        """
        mock_resp = _mock_qresponse(("doc1", 0.01), ("doc2", 0.02), ("doc3", 0.03))
        with patch.object(store._client, "query_points", return_value=mock_resp):
            results = store.search_similar(_hybrid_with_sparse(), top_k=5)
        scores = [s for _, s in results]
        assert len(scores) > 0, "Expected results from hybrid search"
        assert max(scores) > 0.3, (
            f"Hybrid scores {scores} look unnormalized; "
            "raw RRF scores ~0.01-0.03 must not pass through unchanged"
        )

    def test_hybrid_top_score_normalized_near_one(
        self, store: QdrantVectorStore
    ) -> None:
        """After min-max or DBSF normalization, the highest score must approach 1.0."""
        mock_resp = _mock_qresponse(("doc1", 0.01), ("doc2", 0.02), ("doc3", 0.03))
        with patch.object(store._client, "query_points", return_value=mock_resp):
            results = store.search_similar(_hybrid_with_sparse(), top_k=5)
        scores = sorted([s for _, s in results], reverse=True)
        assert len(scores) > 0
        assert scores[0] > 0.9, (
            f"Top normalized hybrid score must be close to 1.0, got {scores[0]}; "
            "unnormalized RRF max would be ~0.03"
        )
