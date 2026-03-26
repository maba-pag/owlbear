"""Tests for the 4-mode search benchmark harness.

Uses a real in-memory Qdrant store with synthetic embeddings to
verify all four search modes return correctly structured results.
No real bge-m3 model is loaded — the embedding provider is mocked.

Task: #379
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from owlbear.memory.knowledge.protocol import HybridEmbedding, SparseVector
from owlbear.memory.knowledge.qdrant import DENSE_DIM, QdrantVectorStore

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NUM_DOCS = 10
_NUM_QUERIES = 3
_TOP_K = 5


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _random_dense(dim: int = DENSE_DIM) -> list[float]:
    """Generate a random dense vector."""
    return [random.gauss(0, 1) for _ in range(dim)]


def _random_sparse(max_indices: int = 50, vocab_size: int = 30_000) -> SparseVector:
    """Generate a random sparse vector."""
    n = random.randint(5, max_indices)  # noqa: S311
    indices = sorted(random.sample(range(vocab_size), n))
    values = [random.random() for _ in range(n)]  # noqa: S311
    return SparseVector(indices=indices, values=values)


def _random_colbert(n_tokens: int = 8, dim: int = DENSE_DIM) -> list[list[float]]:
    """Generate random ColBERT token vectors."""
    return [_random_dense(dim) for _ in range(n_tokens)]


def _make_hybrid_embedding() -> HybridEmbedding:
    """Create a full HybridEmbedding with dense + sparse + ColBERT."""
    return HybridEmbedding(
        dense=_random_dense(),
        sparse=_random_sparse(),
        colbert=_random_colbert(),
    )


@pytest.fixture
def populated_store() -> QdrantVectorStore:
    """In-memory Qdrant store with synthetic documents indexed."""
    store = QdrantVectorStore(location=":memory:")
    for i in range(_NUM_DOCS):
        doc_id = f"doc-{i}"
        emb = _make_hybrid_embedding()
        store.store_embedding(doc_id, emb, "document")
    return store


@pytest.fixture
def mock_provider() -> MagicMock:
    """Mock BgeM3EmbeddingProvider that returns pre-built embeddings."""
    provider = MagicMock()
    # embed_hybrid returns one HybridEmbedding per input text
    provider.embed_hybrid.side_effect = lambda texts: [
        _make_hybrid_embedding() for _ in texts
    ]
    return provider


@pytest.fixture
def queries() -> dict[str, str]:
    """Small query set for testing."""
    return {f"q{i}": f"query text {i}" for i in range(_NUM_QUERIES)}


# ===================================================================
# run_search_benchmark — integration (real Qdrant, mock embeddings)
# ===================================================================


@pytest.mark.benchmark
class TestRunSearchBenchmark:
    """Verify run_search_benchmark returns correct structure."""

    def test_returns_tuple_of_runs_and_latencies(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Return type is (runs, latencies)."""
        pytest.importorskip("ranx")

        from tests.benchmarks.search import run_search_benchmark

        runs, latencies = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        assert isinstance(runs, dict)
        assert isinstance(latencies, dict)

    def test_four_modes_present(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """All 4 search modes must appear in the results."""
        pytest.importorskip("ranx")

        from tests.benchmarks.search import MODES, run_search_benchmark

        runs, latencies = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        for mode in MODES:
            assert mode in runs, f"Missing mode {mode!r} in runs"
            assert mode in latencies, f"Missing mode {mode!r} in latencies"

    def test_runs_are_ranx_run_objects(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Each mode's run must be a ranx.Run instance."""
        ranx = pytest.importorskip("ranx")

        from tests.benchmarks.search import run_search_benchmark

        runs, _ = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        for mode, run in runs.items():
            assert isinstance(run, ranx.Run), f"{mode}: not a ranx.Run"

    def test_latencies_are_float_lists(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Latencies are list[float] per mode."""
        pytest.importorskip("ranx")

        from tests.benchmarks.search import run_search_benchmark

        _, latencies = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        for times in latencies.values():
            assert isinstance(times, list)
            assert len(times) == _NUM_QUERIES
            for t in times:
                assert isinstance(t, float)
                assert t >= 0

    def test_latencies_match_query_count(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Each mode records exactly one latency per query."""
        pytest.importorskip("ranx")

        from tests.benchmarks.search import run_search_benchmark

        _, latencies = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        for mode, times in latencies.items():
            assert len(times) == len(queries), (
                f"{mode}: expected {len(queries)} latencies, got {len(times)}"
            )

    def test_embed_hybrid_called_once(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Queries should be embedded once, not once per mode."""
        pytest.importorskip("ranx")

        from tests.benchmarks.search import run_search_benchmark

        run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        # One call with all query texts
        mock_provider.embed_hybrid.assert_called_once()
        call_args = mock_provider.embed_hybrid.call_args[0][0]
        assert len(call_args) == _NUM_QUERIES


# ===================================================================
# Individual mode tests
# ===================================================================


@pytest.mark.benchmark
class TestDenseMode:
    """Dense-only mode: uses plain dense vector search."""

    def test_dense_returns_results(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Dense mode should return results for each query."""
        ranx = pytest.importorskip("ranx")

        from tests.benchmarks.search import MODE_DENSE, run_search_benchmark

        runs, _ = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        run = runs[MODE_DENSE]
        assert isinstance(run, ranx.Run)


@pytest.mark.benchmark
class TestSparseMode:
    """Sparse-only mode: uses sparse vector search via Qdrant client."""

    def test_sparse_returns_results(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Sparse mode should return results for each query."""
        ranx = pytest.importorskip("ranx")

        from tests.benchmarks.search import MODE_SPARSE, run_search_benchmark

        runs, _ = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        run = runs[MODE_SPARSE]
        assert isinstance(run, ranx.Run)


@pytest.mark.benchmark
class TestHybridRrfMode:
    """Hybrid-RRF mode: dense+sparse prefetch with RRF fusion."""

    def test_hybrid_rrf_returns_results(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Hybrid-RRF mode should return results."""
        ranx = pytest.importorskip("ranx")

        from tests.benchmarks.search import MODE_HYBRID_RRF, run_search_benchmark

        runs, _ = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        run = runs[MODE_HYBRID_RRF]
        assert isinstance(run, ranx.Run)


@pytest.mark.benchmark
class TestHybridColbertMode:
    """Hybrid+ColBERT mode: full 3-stage pipeline."""

    def test_hybrid_colbert_returns_results(
        self,
        populated_store: QdrantVectorStore,
        queries: dict[str, str],
        mock_provider: MagicMock,
    ) -> None:
        """Hybrid+ColBERT mode should return results."""
        ranx = pytest.importorskip("ranx")

        from tests.benchmarks.search import MODE_HYBRID_COLBERT, run_search_benchmark

        runs, _ = run_search_benchmark(
            populated_store, queries, mock_provider, top_k=_TOP_K,
        )

        run = runs[MODE_HYBRID_COLBERT]
        assert isinstance(run, ranx.Run)
