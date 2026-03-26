"""Benchmark harness utilities for IR evaluation.

Provides helpers for constructing ranx evaluation objects and recording
per-query latency measurements.

Tasks: #377 (build_qrels), #379 (build_run), #380 (latency)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_qrels(qrels_dict: dict[str, dict[str, int]]) -> Any:
    """Construct a ``ranx.Qrels`` object from a raw relevance dict.

    Args:
        qrels_dict: Mapping of ``{query_id: {doc_id: relevance_score}}``.

    Returns:
        A ``ranx.Qrels`` instance ready for evaluation.
    """
    from ranx import Qrels

    return Qrels.from_dict(qrels_dict)


def build_run(results: dict[str, dict[str, float]]) -> Any:
    """Construct a ``ranx.Run`` object from retrieval results.

    Args:
        results: Mapping of ``{query_id: {doc_id: score}}``.

    Returns:
        A ``ranx.Run`` instance ready for evaluation.
    """
    from ranx import Run

    # Filter out queries with no results — ranx.Run.from_dict
    # raises ValueError on empty iterables.
    non_empty = {qid: docs for qid, docs in results.items() if docs}
    if not non_empty:
        return Run()
    return Run.from_dict(non_empty)


def make_latency_tracker() -> dict[str, list[float]]:
    """Create a latency tracker dict for per-query timing.

    Returns:
        A ``defaultdict(list)`` mapping mode names to lists of elapsed times.
    """
    return defaultdict(list)


def record_latency(
    tracker: dict[str, list[float]],
    mode: str,
    elapsed: float,
) -> None:
    """Record a single latency measurement.

    Args:
        tracker: The latency tracker dict (from ``make_latency_tracker``).
        mode: The retrieval mode name (e.g. ``"dense"``, ``"sparse"``).
        elapsed: Elapsed time in seconds.
    """
    tracker[mode].append(elapsed)
