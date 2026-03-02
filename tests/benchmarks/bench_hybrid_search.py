"""Benchmark: hybrid search quality — nDCG@10 evaluation.

Compares four search modes (dense-only, sparse-only, hybrid-RRF,
hybrid+ColBERT) on the NFCorpus dataset using ranx for metric
computation with statistical significance testing.

Runnable as a pytest test (``@pytest.mark.benchmark``) or standalone::

    uv run python tests/benchmarks/bench_hybrid_search.py

Task: #380
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider

from .corpus import load_nfcorpus
from .evaluate import (
    compute_latency_stats,
    evaluate_runs,
    format_results,
    write_results_doc,
)
from .harness import build_qrels
from .indexer import embed_and_index
from .search import run_search_benchmark

logger = logging.getLogger(__name__)

_RESULTS_DOC = Path(__file__).parents[2] / "docs" / "hybrid-search-benchmark-results.md"


# ---------------------------------------------------------------------------
# Benchmark orchestration
# ---------------------------------------------------------------------------


def run_benchmark() -> str:
    """Execute the full hybrid search benchmark pipeline.

    Steps:

    1. Load NFCorpus via BEIR
    2. Embed and index all documents
    3. Run 4-mode search
    4. Evaluate with ranx.compare()
    5. Compute latency stats
    6. Format and return results

    Returns:
        Formatted results string for console output.
    """
    # 1. Load corpus
    logger.info("Loading NFCorpus...")
    corpus, queries, raw_qrels = load_nfcorpus()
    logger.info("Loaded %d docs, %d queries", len(corpus), len(queries))

    # 2. Embed and index
    logger.info("Embedding and indexing corpus...")
    store = embed_and_index(corpus)

    # 3. Run 4-mode search
    logger.info("Running 4-mode search benchmark...")
    provider = BgeM3EmbeddingProvider()
    try:
        runs, latencies = run_search_benchmark(store, queries, provider)
    finally:
        provider.unload()

    # 4. Build qrels and evaluate
    logger.info("Evaluating with ranx.compare()...")
    qrels = build_qrels(raw_qrels)
    report = evaluate_runs(qrels, runs)

    # 5. Compute latency stats
    latency_stats = compute_latency_stats(latencies)

    # 6. Format results
    output = format_results(report, latency_stats)

    # 7. Write results doc
    doc_path = write_results_doc(report, latency_stats, _RESULTS_DOC)
    logger.info("Results written to %s", doc_path)

    return output


# ---------------------------------------------------------------------------
# pytest entry point
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_hybrid_search_benchmark() -> None:
    """Run the full hybrid search benchmark as a pytest test.

    This test requires:

    - bge-m3 model (~2 GB download on first run)
    - NFCorpus dataset (~3 MB download on first run)
    - ~10-15 min for embedding on CPU

    Skip with ``pytest -m 'not benchmark'`` (the project default).
    """
    output = run_benchmark()
    print(output)

    # Basic sanity: the benchmark produced output
    assert len(output) > 0
    assert "latency" in output.lower()


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    output = run_benchmark()
    print(output)
    print(f"\nResults written to {_RESULTS_DOC}")
    sys.exit(0)
