"""Tests for the search quality benchmark CLI and sources manifest — AC coverage for task #178.

Tests the contract of:
  - packages/knowledge/src/owlbear_knowledge/benchmark.py  (built during task #534)
  - data/knowledge/general/sources.yaml                     (header comment — remaining deliverable)

Benchmark CLI contract:
  - main(args) accepts --db-path and returns an integer exit code
  - SAMPLE_QUERIES constant with exactly 5 string entries
  - get_counts() output (doc/entity/edge counts) appears in stdout
  - Each query searched in both hybrid and dense modes
  - Per-query hybrid vs dense top-3 comparison printed to stdout
  - Summary line "Hybrid differs from dense-only on N/5 queries" in stdout
  - exit 1 when doc_count < 500
  - exit 1 when any query returns 0 results
  - exit 1 when fewer than 3/5 queries show different hybrid vs dense-only top-3
  - exit 0 when all assertions pass (>= 3/5 differing rankings)

Sources manifest contract (task #178 remaining deliverable):
  - sources.yaml has a header comment block at the top of the file
  - Header comment documents corpus size: ~548 documents (~520 research, 23 skills, 5 instructions)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.protocol import HybridEmbedding, SparseVector

# Root of the project, two levels above this test file (tests/ → project root)
_PROJECT_ROOT = Path(__file__).parent.parent
_SOURCES_YAML = _PROJECT_ROOT / "data" / "knowledge" / "general" / "sources.yaml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dense_vec(seed: float = 0.1) -> list[float]:
    """Return a 1024-d dense vector filled with *seed*."""
    return [seed] * 1024


def _sparse(indices: list[int], values: list[float]) -> SparseVector:
    return SparseVector(indices=indices, values=values)


def _hybrid(seed: float = 0.1) -> HybridEmbedding:
    """Build a HybridEmbedding with a sparse vector."""
    return HybridEmbedding(dense=_dense_vec(seed), sparse=_sparse([10, 20], [0.9, 0.8]))


def _make_mocks(
    doc_count: int = 600,
    entity_count: int = 150,
    edge_count: int = 300,
    search_results: list[tuple[str, float]] | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Return (mock_graph, mock_vector, mock_provider) with default happy-path values."""
    if search_results is None:
        search_results = [("doc-1", 0.9), ("doc-2", 0.8), ("doc-3", 0.7)]

    mock_graph = MagicMock()
    mock_graph.get_counts.return_value = (doc_count, entity_count, edge_count)

    mock_vector = MagicMock()
    mock_vector.search_similar.return_value = search_results

    mock_provider = MagicMock()
    mock_provider.embed_hybrid.return_value = [_hybrid()]

    return mock_graph, mock_vector, mock_provider


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_BenchmarkCLI:
    # ---------------------------------------------------------------- Happy path

    def test_benchmark_cli_accepts_db_path_arg(self, tmp_path: Any) -> None:
        """CLI parses --db-path correctly; does not raise SystemExit from argparse."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        mock_graph, mock_vector, mock_provider = _make_mocks()

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            code = main(["--db-path", str(tmp_path)])

        # A valid db-path should not produce code 2 (argparse error)
        assert code != 2

    def test_benchmark_prints_stats_output(
        self, tmp_path: Any, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """get_stats() document/entity/edge counts appear in stdout."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        mock_graph, mock_vector, mock_provider = _make_mocks(
            doc_count=750, entity_count=200, edge_count=400
        )

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            main(["--db-path", str(tmp_path)])

        captured = capsys.readouterr()
        assert "750" in captured.out
        assert "200" in captured.out
        assert "400" in captured.out

    def test_benchmark_defines_five_sample_queries(self) -> None:
        """Module has SAMPLE_QUERIES constant with exactly 5 non-empty string entries."""
        from owlbear_knowledge.benchmark import SAMPLE_QUERIES

        assert isinstance(SAMPLE_QUERIES, (list, tuple))
        assert len(SAMPLE_QUERIES) == 5
        for q in SAMPLE_QUERIES:
            assert isinstance(q, str)
            assert len(q) > 0

    def test_benchmark_runs_hybrid_and_dense_comparison(self, tmp_path: Any) -> None:
        """Each of the 5 queries is searched in both hybrid and dense-only modes."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import SAMPLE_QUERIES, main

        mock_graph, mock_vector, mock_provider = _make_mocks()

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            main(["--db-path", str(tmp_path)])

        # search_similar must be called at least twice per query (hybrid + dense-only)
        call_count = mock_vector.search_similar.call_count
        assert call_count >= 2 * len(SAMPLE_QUERIES)

    def test_benchmark_prints_per_query_comparison(
        self, tmp_path: Any, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Hybrid vs dense top-3 doc IDs are printed for each query."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import SAMPLE_QUERIES, main

        mock_graph, mock_vector, mock_provider = _make_mocks(
            search_results=[("doc-ALPHA", 0.9), ("doc-BETA", 0.8), ("doc-GAMMA", 0.7)]
        )

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            main(["--db-path", str(tmp_path)])

        captured = capsys.readouterr()
        # At least one top-3 doc ID must appear in per-query comparison output
        assert (
            "doc-ALPHA" in captured.out
            or "doc-BETA" in captured.out
            or "doc-GAMMA" in captured.out
        )
        # Output should have at least one line per query
        assert captured.out.count("\n") >= len(SAMPLE_QUERIES)

    def test_benchmark_prints_summary_line(
        self, tmp_path: Any, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Stdout contains 'Hybrid differs from dense-only on N/5 queries'."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        mock_graph, mock_vector, mock_provider = _make_mocks()

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            main(["--db-path", str(tmp_path)])

        captured = capsys.readouterr()
        assert "Hybrid differs from dense-only on" in captured.out
        assert "/5 queries" in captured.out

    # ---------------------------------------------------------------- Error paths

    def test_benchmark_asserts_document_count_fails_on_empty_db(
        self, tmp_path: Any
    ) -> None:
        """Exit 1 when doc_count < 500 (insufficient data in the database)."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        # doc_count=10, well below the 500 threshold
        mock_graph, mock_vector, mock_provider = _make_mocks(doc_count=10)

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            code = main(["--db-path", str(tmp_path)])

        assert code == 1

    def test_benchmark_asserts_document_count_boundary_499_fails(
        self, tmp_path: Any
    ) -> None:
        """Exit 1 when doc_count == 499 (just below the 500 threshold)."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        mock_graph, mock_vector, mock_provider = _make_mocks(doc_count=499)

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            code = main(["--db-path", str(tmp_path)])

        assert code == 1

    def test_benchmark_asserts_query_returns_results(self, tmp_path: Any) -> None:
        """Exit 1 when any query returns 0 results."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        # doc_count passes (600 >= 500), but all queries return empty result lists
        mock_graph, mock_vector, mock_provider = _make_mocks(search_results=[])

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            code = main(["--db-path", str(tmp_path)])

        assert code == 1

    def test_benchmark_asserts_ranking_difference_fails_when_insufficient(
        self, tmp_path: Any
    ) -> None:
        """Exit 1 when fewer than 3/5 queries show different hybrid vs dense-only top-3."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        # doc_count passes; queries return results; but hybrid==dense for all queries
        mock_graph, mock_vector, mock_provider = _make_mocks(
            search_results=[("doc-X", 0.9), ("doc-Y", 0.8), ("doc-Z", 0.7)]
        )

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            code = main(["--db-path", str(tmp_path)])

        # 0/5 differ (identical results for both modes) → fails ranking-diff assertion
        assert code == 1

    # ---------------------------------------------------------------- Boundary / Full happy path

    def test_benchmark_exit_0_when_all_pass(self, tmp_path: Any) -> None:
        """Exit 0 when all assertions met: doc_count >= 500, results non-empty,
        and >= 3/5 queries show different hybrid vs dense-only top-3 rankings."""
        from unittest.mock import patch

        from owlbear_knowledge.benchmark import main

        mock_graph = MagicMock()
        mock_graph.get_counts.return_value = (600, 150, 300)

        # Alternating results: odd-numbered calls return [A,B,C], even return [D,E,F]
        # Assuming benchmark calls hybrid first then dense per query,
        # this produces 5/5 differing rankings (satisfies >= 3/5 threshold).
        call_counter: list[int] = [0]

        def _alternating_results(*_args: Any, **_kwargs: Any) -> list[tuple[str, float]]:
            call_counter[0] += 1
            if call_counter[0] % 2 == 1:
                return [("doc-A", 0.95), ("doc-B", 0.85), ("doc-C", 0.75)]
            return [("doc-D", 0.90), ("doc-E", 0.80), ("doc-F", 0.70)]

        mock_vector = MagicMock()
        mock_vector.search_similar.side_effect = _alternating_results

        mock_provider = MagicMock()
        mock_provider.embed_hybrid.return_value = [
            HybridEmbedding(
                dense=_dense_vec(),
                sparse=_sparse([10, 20], [0.9, 0.8]),
            )
        ]

        with (
            patch("owlbear_knowledge.benchmark.GraphStore", return_value=mock_graph),
            patch("owlbear_knowledge.benchmark.QdrantVectorStore", return_value=mock_vector),
            patch("owlbear_knowledge.benchmark.BgeM3EmbeddingProvider", return_value=mock_provider),
        ):
            code = main(["--db-path", str(tmp_path)])

        assert code == 0


class TestFromAC_SourcesManifest:
    """Tests for the sources.yaml header comment — remaining deliverable for task #178."""

    # ---------------------------------------------------------------- Happy path

    def test_sources_yaml_has_header_comment(self) -> None:
        """sources.yaml must start with at least one YAML comment line (#)."""
        raw = _SOURCES_YAML.read_text(encoding="utf-8")
        first_non_blank = next(
            (line for line in raw.splitlines() if line.strip()), ""
        )
        assert first_non_blank.startswith("#"), (
            "sources.yaml must begin with a header comment (# ...) but first "
            f"non-blank line is: {first_non_blank!r}"
        )

    def test_sources_yaml_header_documents_total_count(self) -> None:
        """Header comment must mention the approximate total document count (~548)."""
        raw = _SOURCES_YAML.read_text(encoding="utf-8")
        comment_block = "\n".join(
            line for line in raw.splitlines() if line.strip().startswith("#")
        )
        # Accept 548 or nearby approximation (540-560), file counts drift over time
        found = any(str(n) in comment_block for n in range(540, 561))
        assert found, (
            "sources.yaml header comment must mention the approximate total corpus "
            "size (e.g. 548) but no number in range 540-560 was found in comment lines."
        )

    def test_sources_yaml_header_documents_research_count(self) -> None:
        """Header comment must mention the research document count (~520)."""
        raw = _SOURCES_YAML.read_text(encoding="utf-8")
        comment_block = "\n".join(
            line for line in raw.splitlines() if line.strip().startswith("#")
        )
        assert "520" in comment_block, (
            "sources.yaml header comment must mention ~520 research documents."
        )

    def test_sources_yaml_header_documents_skills_count(self) -> None:
        """Header comment must mention the skills count (23)."""
        raw = _SOURCES_YAML.read_text(encoding="utf-8")
        comment_block = "\n".join(
            line for line in raw.splitlines() if line.strip().startswith("#")
        )
        assert "23" in comment_block, (
            "sources.yaml header comment must mention 23 skills."
        )

    def test_sources_yaml_header_documents_instructions_count(self) -> None:
        """Header comment must mention the instructions count (5)."""
        raw = _SOURCES_YAML.read_text(encoding="utf-8")
        comment_block = "\n".join(
            line for line in raw.splitlines() if line.strip().startswith("#")
        )
        assert "5" in comment_block, (
            "sources.yaml header comment must mention 5 instruction files."
        )
        assert "instruction" in comment_block.lower(), (
            "sources.yaml header comment must mention 'instruction' files."
        )
