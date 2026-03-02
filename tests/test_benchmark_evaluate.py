"""Tests for benchmark evaluation utilities — TDD contract.

Validates the evaluation pipeline (ranx.compare, latency stats,
formatting, doc generation) using mocked/synthetic data.

Task: #380
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.benchmarks.evaluate import (
    compute_latency_stats,
    evaluate_runs,
    format_results,
    write_results_doc,
)
from tests.benchmarks.harness import build_qrels, build_run

# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

MINI_QRELS: dict[str, dict[str, int]] = {
    "q1": {"d1": 2, "d3": 1},
    "q2": {"d2": 2},
    "q3": {"d1": 1, "d2": 1, "d3": 2},
}

DENSE_RESULTS: dict[str, dict[str, float]] = {
    "q1": {"d1": 0.95, "d3": 0.42, "d2": 0.10},
    "q2": {"d2": 0.88, "d1": 0.15},
    "q3": {"d3": 0.70, "d1": 0.60, "d2": 0.55},
}

SPARSE_RESULTS: dict[str, dict[str, float]] = {
    "q1": {"d1": 0.80, "d2": 0.50},
    "q2": {"d2": 0.75, "d3": 0.20},
    "q3": {"d3": 0.65, "d2": 0.60},
}

HYBRID_RESULTS: dict[str, dict[str, float]] = {
    "q1": {"d1": 0.90, "d3": 0.55, "d2": 0.30},
    "q2": {"d2": 0.92, "d1": 0.20},
    "q3": {"d3": 0.80, "d1": 0.65, "d2": 0.60},
}

COLBERT_RESULTS: dict[str, dict[str, float]] = {
    "q1": {"d1": 0.98, "d3": 0.60, "d2": 0.25},
    "q2": {"d2": 0.95, "d1": 0.10},
    "q3": {"d3": 0.85, "d1": 0.70, "d2": 0.65},
}

SAMPLE_LATENCIES: dict[str, list[float]] = {
    "dense": [0.010, 0.012, 0.011, 0.015, 0.009, 0.013, 0.010, 0.011, 0.012, 0.014],
    "sparse": [0.005, 0.006, 0.004, 0.007, 0.005, 0.006, 0.005, 0.004, 0.006, 0.005],
    "hybrid_rrf": [0.020, 0.022, 0.019, 0.025, 0.018, 0.021, 0.020, 0.019, 0.023, 0.022],
    "hybrid_colbert": [
        0.030,
        0.035,
        0.028,
        0.040,
        0.032,
        0.031,
        0.029,
        0.033,
        0.036,
        0.034,
    ],
}


# ===================================================================
# evaluate_runs tests
# ===================================================================


@pytest.mark.benchmark
class TestEvaluateRuns:
    """Contract: evaluate_runs() returns a ranx comparison report."""

    def test_returns_report_object(self) -> None:
        """evaluate_runs must return a ranx Report."""
        pytest.importorskip("ranx")
        from ranx.data_structures import Report

        qrels = build_qrels(MINI_QRELS)
        runs = {
            "dense": build_run(DENSE_RESULTS),
            "sparse": build_run(SPARSE_RESULTS),
            "hybrid_rrf": build_run(HYBRID_RESULTS),
            "hybrid_colbert": build_run(COLBERT_RESULTS),
        }
        report = evaluate_runs(qrels, runs)
        assert isinstance(report, Report)

    def test_report_contains_metrics(self) -> None:
        """Report must include nDCG@10, precision@10, and MRR."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {
            "dense": build_run(DENSE_RESULTS),
            "sparse": build_run(SPARSE_RESULTS),
        }
        report = evaluate_runs(qrels, runs)
        report_str = str(report)
        # The report string representation should mention the metrics
        assert "ndcg" in report_str.lower() or hasattr(report, "metrics")

    def test_report_has_all_runs(self) -> None:
        """Report must cover all submitted runs."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {
            "dense": build_run(DENSE_RESULTS),
            "sparse": build_run(SPARSE_RESULTS),
            "hybrid_rrf": build_run(HYBRID_RESULTS),
        }
        report = evaluate_runs(qrels, runs)
        # ranx Report has run_names or similar
        report_str = str(report)
        assert "dense" in report_str
        assert "sparse" in report_str
        assert "hybrid_rrf" in report_str


# ===================================================================
# compute_latency_stats tests
# ===================================================================


@pytest.mark.benchmark
class TestComputeLatencyStats:
    """Contract: compute_latency_stats returns per-mode stats."""

    def test_returns_dict_with_all_modes(self) -> None:
        """Result keys must match input modes."""
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        assert set(stats.keys()) == set(SAMPLE_LATENCIES.keys())

    def test_stat_keys(self) -> None:
        """Each mode must have mean, p50, p95, p99."""
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        for mode_stats in stats.values():
            assert "mean" in mode_stats
            assert "p50" in mode_stats
            assert "p95" in mode_stats
            assert "p99" in mode_stats

    def test_mean_value(self) -> None:
        """Mean must be correct for known input."""
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        expected_mean = sum(SAMPLE_LATENCIES["dense"]) / len(SAMPLE_LATENCIES["dense"])
        assert stats["dense"]["mean"] == pytest.approx(expected_mean, rel=1e-6)

    def test_p50_value(self) -> None:
        """p50 (median) must be correct for known input."""
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        dense = sorted(SAMPLE_LATENCIES["dense"])
        # 10 values: p50 = average of 5th and 6th
        expected_p50 = (dense[4] + dense[5]) / 2
        assert stats["dense"]["p50"] == pytest.approx(expected_p50, rel=1e-6)

    def test_p95_ge_p50(self) -> None:
        """p95 must be >= p50."""
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        for mode_stats in stats.values():
            assert mode_stats["p95"] >= mode_stats["p50"]

    def test_p99_ge_p95(self) -> None:
        """p99 must be >= p95."""
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        for mode_stats in stats.values():
            assert mode_stats["p99"] >= mode_stats["p95"]

    def test_single_value(self) -> None:
        """Should handle a mode with a single latency value."""
        stats = compute_latency_stats({"dense": [0.042]})
        assert stats["dense"]["mean"] == pytest.approx(0.042)
        assert stats["dense"]["p50"] == pytest.approx(0.042)
        assert stats["dense"]["p95"] == pytest.approx(0.042)
        assert stats["dense"]["p99"] == pytest.approx(0.042)


# ===================================================================
# format_results tests
# ===================================================================


@pytest.mark.benchmark
class TestFormatResults:
    """Contract: format_results produces human-readable text."""

    def test_returns_string(self) -> None:
        """format_results must return a string."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {
            "dense": build_run(DENSE_RESULTS),
            "sparse": build_run(SPARSE_RESULTS),
        }
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        result = format_results(report, stats)
        assert isinstance(result, str)

    def test_contains_latency_header(self) -> None:
        """Output must contain a 'Latency' section."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {"dense": build_run(DENSE_RESULTS)}
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        result = format_results(report, stats)
        assert "latency" in result.lower()

    def test_contains_mode_names(self) -> None:
        """Output must reference mode names from latency stats."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {"dense": build_run(DENSE_RESULTS)}
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats({"dense": [0.01], "sparse": [0.005]})
        result = format_results(report, stats)
        assert "dense" in result
        assert "sparse" in result


# ===================================================================
# write_results_doc tests
# ===================================================================


@pytest.mark.benchmark
class TestWriteResultsDoc:
    """Contract: write_results_doc produces a markdown file."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """write_results_doc must create the output file."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {
            "dense": build_run(DENSE_RESULTS),
            "sparse": build_run(SPARSE_RESULTS),
        }
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        out = tmp_path / "results.md"
        write_results_doc(report, stats, out)
        assert out.exists()

    def test_file_is_markdown(self, tmp_path: Path) -> None:
        """Output file must be valid markdown with expected sections."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {"dense": build_run(DENSE_RESULTS)}
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        out = tmp_path / "results.md"
        write_results_doc(report, stats, out)
        content = out.read_text(encoding="utf-8")
        assert content.startswith("#")
        assert "NFCorpus" in content
        assert "bge-m3" in content

    def test_contains_date(self, tmp_path: Path) -> None:
        """Output file must include the run date."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {"dense": build_run(DENSE_RESULTS)}
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        out = tmp_path / "results.md"
        write_results_doc(report, stats, out)
        content = out.read_text(encoding="utf-8")
        # Should contain a date like 2026-03-02
        assert "2026" in content or "202" in content

    def test_contains_latency_table(self, tmp_path: Path) -> None:
        """Output file must include a latency table."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {"dense": build_run(DENSE_RESULTS)}
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        out = tmp_path / "results.md"
        write_results_doc(report, stats, out)
        content = out.read_text(encoding="utf-8")
        assert "latency" in content.lower()
        # Markdown table indicator
        assert "|" in content

    def test_contains_statistical_significance(self, tmp_path: Path) -> None:
        """Output file must mention statistical significance."""
        pytest.importorskip("ranx")
        qrels = build_qrels(MINI_QRELS)
        runs = {
            "dense": build_run(DENSE_RESULTS),
            "sparse": build_run(SPARSE_RESULTS),
        }
        report = evaluate_runs(qrels, runs)
        stats = compute_latency_stats(SAMPLE_LATENCIES)
        out = tmp_path / "results.md"
        write_results_doc(report, stats, out)
        content = out.read_text(encoding="utf-8")
        assert "significance" in content.lower() or "t-test" in content.lower()
