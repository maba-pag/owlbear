"""Evaluation utilities for IR benchmarks.

Provides wrappers around ``ranx.compare()`` for metric evaluation and
latency statistics computation for benchmark reporting.

Task: #380
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def evaluate_runs(
    qrels: Any,
    runs: dict[str, Any],
    *,
    metrics: list[str] | None = None,
) -> Any:
    """Evaluate multiple retrieval runs against ground truth qrels.

    Uses ``ranx.compare()`` to produce a comparison report with
    statistical significance testing (paired t-test).

    Args:
        qrels: A ``ranx.Qrels`` instance with ground truth relevance.
        runs: Mapping of ``{mode_name: ranx.Run}``.
        metrics: Metrics to compute. Defaults to
            ``["ndcg@10", "precision@10", "mrr"]``.

    Returns:
        A ``ranx.Report`` object containing the comparison table
        with statistical significance indicators.
    """
    from ranx import compare

    if metrics is None:
        metrics = ["ndcg@10", "precision@10", "mrr"]

    run_names = list(runs.keys())
    run_list = [runs[name] for name in run_names]

    # Set run names so ranx labels them in the report.
    for name, run in zip(run_names, run_list, strict=True):
        run.name = name

    return compare(
        qrels=qrels,
        runs=run_list,
        metrics=metrics,
        stat_test="student",
    )


def compute_latency_stats(
    latencies: dict[str, list[float]],
) -> dict[str, dict[str, float]]:
    """Compute per-mode latency statistics from raw timings.

    Args:
        latencies: Mapping of ``{mode_name: [elapsed_seconds, ...]}``.

    Returns:
        Mapping of ``{mode_name: {"mean": float, "p50": float,
        "p95": float, "p99": float}}``.
    """
    result: dict[str, dict[str, float]] = {}
    for mode, times in latencies.items():
        sorted_times = sorted(times)
        n = len(sorted_times)
        result[mode] = {
            "mean": statistics.mean(sorted_times),
            "p50": _percentile(sorted_times, n, 50),
            "p95": _percentile(sorted_times, n, 95),
            "p99": _percentile(sorted_times, n, 99),
        }
    return result


def _percentile(sorted_vals: list[float], n: int, pct: int) -> float:
    """Compute a percentile from pre-sorted values.

    Uses linear interpolation (same as ``numpy.percentile`` default).

    Args:
        sorted_vals: Pre-sorted list of values.
        n: Length of the list.
        pct: Percentile to compute (0-100).

    Returns:
        The interpolated percentile value.
    """
    if n == 1:
        return sorted_vals[0]
    # 0-based index for pct-th percentile
    k = (pct / 100) * (n - 1)
    f = int(k)
    c = f + 1
    if c >= n:
        return sorted_vals[-1]
    d = k - f
    return sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f])


def format_results(
    report: Any,
    latency_stats: dict[str, dict[str, float]],
) -> str:
    """Format evaluation results as a human-readable string.

    Args:
        report: A ``ranx.Report`` from ``evaluate_runs()``.
        latency_stats: Output from ``compute_latency_stats()``.

    Returns:
        A formatted string with the comparison table and latency table.
    """
    lines: list[str] = []

    # --- Metric comparison table ---
    lines.append("=" * 60)
    lines.append("  Retrieval Quality Comparison")
    lines.append("=" * 60)
    lines.append("")
    lines.append(str(report))
    lines.append("")

    # --- Latency table ---
    lines.append("=" * 60)
    lines.append("  Latency Statistics (seconds)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"{'Mode':<20} {'Mean':>10} {'p50':>10} {'p95':>10} {'p99':>10}")
    lines.append("-" * 60)
    for mode, stats in latency_stats.items():
        lines.append(
            f"{mode:<20} {stats['mean']:>10.4f} {stats['p50']:>10.4f} "
            f"{stats['p95']:>10.4f} {stats['p99']:>10.4f}"
        )
    lines.append("")

    return "\n".join(lines)


def write_results_doc(
    report: Any,
    latency_stats: dict[str, dict[str, float]],
    output_path: Path,
) -> Path:
    """Write benchmark results to a markdown document.

    The document includes:

    - Comparison table with all metrics across all modes
    - Latency table (mean, p50, p95, p99)
    - Statistical significance indicators
    - Date, corpus name (NFCorpus), model version (bge-m3)

    Args:
        report: A ``ranx.Report`` from ``evaluate_runs()``.
        latency_stats: Output from ``compute_latency_stats()``.
        output_path: Where to write the markdown file.

    Returns:
        The path to the written file.
    """
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    md: list[str] = []
    md.append("# Hybrid Search Benchmark Results")
    md.append("")
    md.append(f"> **Date:** {now}")
    md.append("> **Corpus:** NFCorpus (BEIR) — 3,633 docs, 323 queries")
    md.append("> **Model:** bge-m3 (1024d dense + sparse + ColBERT)")
    md.append("> **Statistical test:** Paired t-test (student)")
    md.append("")

    # --- Metric comparison ---
    md.append("## Retrieval Quality")
    md.append("")
    md.append("Comparison via `ranx.compare()` with statistical significance "
              "(paired t-test).")
    md.append("")
    md.append("```")
    md.append(str(report))
    md.append("```")
    md.append("")

    # --- Statistical significance note ---
    md.append("### Statistical Significance")
    md.append("")
    md.append("Superscript letters in the table above indicate statistically "
              "significant differences (paired t-test, p < 0.05) between runs. "
              "Runs sharing the same letter are not significantly different.")
    md.append("")

    # --- Latency table ---
    md.append("## Latency")
    md.append("")
    md.append("Per-query latency statistics across all search modes.")
    md.append("")
    md.append("| Mode | Mean (s) | p50 (s) | p95 (s) | p99 (s) |")
    md.append("|------|----------|---------|---------|---------|")
    for mode, stats in latency_stats.items():
        md.append(
            f"| {mode} "
            f"| {stats['mean']:.4f} "
            f"| {stats['p50']:.4f} "
            f"| {stats['p95']:.4f} "
            f"| {stats['p99']:.4f} |"
        )
    md.append("")

    # --- Interpretation ---
    md.append("## Interpretation")
    md.append("")
    md.append("Expected ordering from bge-m3 paper benchmarks:")
    md.append("")
    md.append("- hybrid+ColBERT > hybrid-RRF > dense-only > sparse-only")
    md.append("")
    md.append("See `docs/hybrid-search-benchmark-research.md` for methodology details.")
    md.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md), encoding="utf-8")
    return output_path
