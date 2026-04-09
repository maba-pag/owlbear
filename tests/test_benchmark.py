"""Tests for owlbear_knowledge.benchmark — search quality benchmark CLI.

Tests exercise main() with mock dependencies (GraphStore, QdrantVectorStore,
BgeM3EmbeddingProvider) to validate:
  - CLI argument parsing (--db-path)
  - Stats output
  - doc_count threshold enforcement
  - Per-query hybrid vs dense comparison
  - Zero-result failure path
  - Ranking difference threshold enforcement
  - Happy path exit 0
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from owlbear_knowledge.protocol import HybridEmbedding, SparseVector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dense_vec(seed: float = 0.1) -> list[float]:
    return [seed] * 1024


def _sparse(indices: list[int] | None = None, values: list[float] | None = None) -> SparseVector:
    return SparseVector(indices=indices or [10, 20], values=values or [0.9, 0.8])


def _hybrid(seed: float = 0.1) -> HybridEmbedding:
    return HybridEmbedding(dense=_dense_vec(seed), sparse=_sparse())


def _make_mocks(
    doc_count: int = 600,
    entity_count: int = 150,
    edge_count: int = 300,
    search_results: list[tuple[str, float]] | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    if search_results is None:
        search_results = [("doc-1", 0.9), ("doc-2", 0.8), ("doc-3", 0.7)]

    mock_graph = MagicMock()
    mock_graph.get_counts.return_value = (doc_count, entity_count, edge_count)

    mock_vector = MagicMock()
    mock_vector.search_similar.return_value = search_results

    mock_provider = MagicMock()
    mock_provider.embed_hybrid.return_value = [_hybrid()]

    return mock_graph, mock_vector, mock_provider


def _run_main(
    tmp_path: Any,
    mock_graph: MagicMock,
    mock_vector: MagicMock,
    mock_provider: MagicMock,
) -> int:
    from owlbear_knowledge.benchmark import main

    with (
        patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
        patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
        patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        patch("owlbear_knowledge.benchmark.sqlite3"),
    ):
        return main(["--db-path", str(tmp_path)])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBenchmarkCLI:
    def test_accepts_db_path_arg(self, tmp_path: Any) -> None:
        mock_graph, mock_vector, mock_provider = _make_mocks()
        code = _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        assert code != 2  # argparse error

    def test_prints_stats(self, tmp_path: Any, capsys: pytest.CaptureFixture[str]) -> None:
        mock_graph, mock_vector, mock_provider = _make_mocks(doc_count=750, entity_count=200, edge_count=400)
        _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        out = capsys.readouterr().out
        assert "750" in out
        assert "200" in out
        assert "400" in out

    def test_sample_queries_constant(self) -> None:
        from owlbear_knowledge.benchmark import SAMPLE_QUERIES

        assert isinstance(SAMPLE_QUERIES, list)
        assert len(SAMPLE_QUERIES) == 5
        assert all(isinstance(q, str) and q for q in SAMPLE_QUERIES)

    def test_calls_hybrid_and_dense_per_query(self, tmp_path: Any) -> None:
        from owlbear_knowledge.benchmark import SAMPLE_QUERIES

        mock_graph, mock_vector, mock_provider = _make_mocks()
        _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        assert mock_vector.search_similar.call_count >= 2 * len(SAMPLE_QUERIES)

    def test_prints_per_query_comparison(self, tmp_path: Any, capsys: pytest.CaptureFixture[str]) -> None:
        mock_graph, mock_vector, mock_provider = _make_mocks(
            search_results=[("doc-A", 0.9), ("doc-B", 0.8), ("doc-C", 0.7)],
        )
        _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        out = capsys.readouterr().out
        assert "doc-A" in out or "doc-B" in out or "doc-C" in out

    def test_prints_summary_line(self, tmp_path: Any, capsys: pytest.CaptureFixture[str]) -> None:
        mock_graph, mock_vector, mock_provider = _make_mocks()
        _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        out = capsys.readouterr().out
        assert "Hybrid differs from dense-only on" in out
        assert "/5 queries" in out

    def test_exit_1_when_doc_count_below_threshold(self, tmp_path: Any) -> None:
        mock_graph, mock_vector, mock_provider = _make_mocks(doc_count=10)
        code = _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        assert code == 1

    def test_exit_1_at_boundary_499(self, tmp_path: Any) -> None:
        mock_graph, mock_vector, mock_provider = _make_mocks(doc_count=499)
        code = _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        assert code == 1

    def test_exit_1_when_query_returns_zero_results(self, tmp_path: Any) -> None:
        mock_graph, mock_vector, mock_provider = _make_mocks(search_results=[])
        code = _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        assert code == 1

    def test_exit_1_when_insufficient_ranking_differences(self, tmp_path: Any) -> None:
        # Same results for both hybrid and dense → 0 diffs → below threshold
        mock_graph, mock_vector, mock_provider = _make_mocks(
            search_results=[("doc-X", 0.9), ("doc-Y", 0.8), ("doc-Z", 0.7)],
        )
        code = _run_main(tmp_path, mock_graph, mock_vector, mock_provider)
        assert code == 1

    def test_exit_0_when_all_pass(self, tmp_path: Any) -> None:
        mock_graph = MagicMock()
        mock_graph.get_counts.return_value = (600, 150, 300)

        # Alternate results: hybrid gets [A,B,C], dense gets [D,E,F]
        call_counter = {"n": 0}

        def side_effect_search(*_args: Any, **_kwargs: Any) -> list[tuple[str, float]]:
            call_counter["n"] += 1
            if call_counter["n"] % 2 == 1:  # hybrid call
                return [("doc-H1", 0.9), ("doc-H2", 0.8), ("doc-H3", 0.7)]
            return [("doc-D1", 0.9), ("doc-D2", 0.8), ("doc-D3", 0.7)]  # dense call

        mock_vector = MagicMock()
        mock_vector.search_similar.side_effect = side_effect_search

        mock_provider = MagicMock()
        mock_provider.embed_hybrid.return_value = [_hybrid()]

        from owlbear_knowledge.benchmark import main

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
            patch("owlbear_knowledge.benchmark.sqlite3"),
        ):
            code = main(["--db-path", str(tmp_path)])

        assert code == 0
