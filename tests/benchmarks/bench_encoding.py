"""Benchmark: bge-m3 encoding throughput and memory on Ryzen 8840U.

Measures dense-only (``embed``) and hybrid (``embed_hybrid``) encoding
across batch sizes 4, 8, 16, and 32 on a synthetic 128-chunk corpus.

Runnable as a pytest test (``@pytest.mark.benchmark``) or standalone::

    uv run python tests/benchmarks/bench_encoding.py

Task: #433
"""

from __future__ import annotations

import os
import platform
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psutil
import pytest

from owlbear.memory.knowledge.embeddings import BgeM3EmbeddingProvider

# ---------------------------------------------------------------------------
# Synthetic corpus — 128 deterministic technical chunks (~200 tokens each)
# ---------------------------------------------------------------------------

_WORD_POOL: list[str] = [
    "algorithm",
    "architecture",
    "asynchronous",
    "authentication",
    "authorization",
    "bandwidth",
    "benchmark",
    "binary",
    "buffer",
    "cache",
    "callback",
    "cluster",
    "compiler",
    "concurrency",
    "configuration",
    "container",
    "database",
    "debugging",
    "dependency",
    "deployment",
    "distributed",
    "encryption",
    "endpoint",
    "exception",
    "execution",
    "framework",
    "function",
    "gateway",
    "generation",
    "gradient",
    "handler",
    "hashmap",
    "hyperparameter",
    "implementation",
    "indexing",
    "inference",
    "initialization",
    "integration",
    "interface",
    "iterator",
    "kernel",
    "latency",
    "lifecycle",
    "linearization",
    "logging",
    "marshalling",
    "memory",
    "microservice",
    "middleware",
    "migration",
    "module",
    "monitoring",
    "mutex",
    "namespace",
    "neural",
    "normalization",
    "optimization",
    "orchestration",
    "pagination",
    "parallelism",
    "parameter",
    "parser",
    "partition",
    "payload",
    "pipeline",
    "pointer",
    "polymorphism",
    "preprocessing",
    "profiling",
    "protocol",
    "provisioning",
    "quantization",
    "query",
    "queueing",
    "recursion",
    "refactoring",
    "registry",
    "replication",
    "repository",
    "resolution",
    "retrieval",
    "runtime",
    "scheduler",
    "schema",
    "serialization",
    "service",
    "singleton",
    "snapshot",
    "socket",
    "specification",
    "streaming",
    "synchronization",
    "telemetry",
    "template",
    "tensor",
    "throughput",
    "tokenization",
    "topology",
    "transaction",
    "transformation",
    "validation",
    "vectorization",
    "virtualization",
    "webhook",
    "workflow",
]

_CONNECTORS: list[str] = [
    "enables",
    "requires",
    "provides",
    "supports",
    "handles",
    "manages",
    "processes",
    "coordinates",
    "facilitates",
    "integrates with",
    "depends on",
    "extends",
    "implements",
    "wraps",
    "delegates to",
]


def _generate_corpus(n_chunks: int = 128, target_tokens: int = 200, seed: int = 42) -> list[str]:
    """Generate *n_chunks* deterministic pseudo-technical paragraphs.

    Each chunk is approximately *target_tokens* whitespace-delimited
    tokens long.  Uses a fixed *seed* for reproducibility.
    """
    rng = random.Random(seed)
    chunks: list[str] = []

    for _ in range(n_chunks):
        words: list[str] = []
        while len(words) < target_tokens:
            subject = rng.choice(_WORD_POOL)
            connector = rng.choice(_CONNECTORS)
            obj = rng.choice(_WORD_POOL)
            detail = rng.choice(_WORD_POOL)
            sentence = (
                f"The {subject} {connector} {obj} through advanced {detail} "
                f"mechanisms that ensure reliable operation under load."
            )
            words.extend(sentence.split())
        chunks.append(" ".join(words[:target_tokens]))

    return chunks


# ---------------------------------------------------------------------------
# Benchmark parameters
# ---------------------------------------------------------------------------

BATCH_SIZES: list[int] = [4, 8, 16, 32]
MODES: list[str] = ["dense", "hybrid"]
CORPUS_SIZE = 128
TARGET_TOKENS = 200
SEED = 42

# ---------------------------------------------------------------------------
# Result data
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Metrics for a single (batch_size, mode) combination."""

    batch_size: int
    mode: str
    model_load_seconds: float
    encoding_seconds: float
    chunks_per_second: float
    rss_before_model: int
    rss_after_model: int
    rss_after_encode: int
    peak_rss_delta: int


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _measure_rss() -> int:
    """Return current RSS in bytes for this process."""
    return psutil.Process(os.getpid()).memory_info().rss


def _run_single(batch_size: int, mode: str, corpus: list[str]) -> BenchmarkResult:
    """Run one benchmark configuration and return metrics."""
    rss_before_model = _measure_rss()

    # Model load (timed separately)
    t0 = time.perf_counter()
    provider = BgeM3EmbeddingProvider(batch_size=batch_size)
    provider._ensure_model()
    model_load_seconds = time.perf_counter() - t0

    rss_after_model = _measure_rss()

    # Encoding (timed)
    t0 = time.perf_counter()
    if mode == "dense":
        provider.embed(corpus)
    else:
        provider.embed_hybrid(corpus)
    encoding_seconds = time.perf_counter() - t0

    rss_after_encode = _measure_rss()

    chunks_per_second = len(corpus) / encoding_seconds if encoding_seconds > 0 else 0.0

    # Peak RSS delta: max of (after_model - before) and (after_encode - before)
    peak_rss_delta = max(rss_after_model - rss_before_model, rss_after_encode - rss_before_model)

    # Cleanup
    provider.unload()

    return BenchmarkResult(
        batch_size=batch_size,
        mode=mode,
        model_load_seconds=model_load_seconds,
        encoding_seconds=encoding_seconds,
        chunks_per_second=chunks_per_second,
        rss_before_model=rss_before_model,
        rss_after_model=rss_after_model,
        rss_after_encode=rss_after_encode,
        peak_rss_delta=peak_rss_delta,
    )


def run_benchmark() -> list[BenchmarkResult]:
    """Execute the full encoding benchmark across all configurations.

    Returns:
        List of :class:`BenchmarkResult`, one per (batch_size, mode) pair.
    """
    corpus = _generate_corpus(n_chunks=CORPUS_SIZE, target_tokens=TARGET_TOKENS, seed=SEED)
    results: list[BenchmarkResult] = []

    for batch_size in BATCH_SIZES:
        for mode in MODES:
            print(f"  batch_size={batch_size:>2}, mode={mode:<6} ... ", end="", flush=True)
            result = _run_single(batch_size, mode, corpus)
            print(
                f"done  ({result.chunks_per_second:.1f} chunks/s, "
                f"{result.peak_rss_delta / 1024 / 1024:.0f} MB RSS delta)"
            )
            results.append(result)

    return results


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _human_bytes(n: int) -> str:
    """Format byte count as human-readable MB string."""
    return f"{n / 1024 / 1024:.0f} MB"


def format_results(results: list[BenchmarkResult]) -> str:
    """Format benchmark results as a Markdown table."""
    lines = [
        "| Batch Size | Mode | Model Load (s) | Encode (s) | Chunks/s "
        "| Peak RSS Delta | RSS Before | RSS After Load | RSS After Encode |",
        "|------------|------|---------------:|----------:|---------:"
        "|---------------:|-----------:|---------------:|-----------------:|",
    ]
    lines.extend(
        f"| {r.batch_size:>10} | {r.mode:<6} "
        f"| {r.model_load_seconds:>14.2f} | {r.encoding_seconds:>10.2f} "
        f"| {r.chunks_per_second:>8.1f} "
        f"| {_human_bytes(r.peak_rss_delta):>14} "
        f"| {_human_bytes(r.rss_before_model):>10} "
        f"| {_human_bytes(r.rss_after_model):>14} "
        f"| {_human_bytes(r.rss_after_encode):>16} |"
        for r in results
    )

    return "\n".join(lines)


def _hardware_header() -> str:
    """Build a Markdown header with hardware and software info."""
    try:
        import FlagEmbedding

        flag_version = getattr(FlagEmbedding, "__version__", "unknown")
    except ImportError:
        flag_version = "not installed"

    mem = psutil.virtual_memory()
    return (
        "# BGE-M3 Encoding Benchmark Results\n"
        "\n"
        f"Generated by `tests/benchmarks/bench_encoding.py` (task #433).\n"
        "\n"
        "## Hardware\n"
        "\n"
        f"- **CPU:** {platform.processor() or platform.machine()}\n"
        f"- **RAM:** {mem.total / 1024 / 1024 / 1024:.1f} GB\n"
        f"- **OS:** {platform.system()} {platform.release()}\n"
        f"- **Python:** {platform.python_version()}\n"
        f"- **FlagEmbedding:** {flag_version}\n"
        "\n"
        "## Parameters\n"
        "\n"
        f"- **Corpus:** {CORPUS_SIZE} synthetic chunks, ~{TARGET_TOKENS} tokens each\n"
        f"- **Batch sizes:** {', '.join(str(b) for b in BATCH_SIZES)}\n"
        f"- **Modes:** dense (`embed`), hybrid (`embed_hybrid`)\n"
        f"- **Seed:** {SEED}\n"
        "\n"
        "## Results\n"
        "\n"
    )


def write_results_doc(results: list[BenchmarkResult]) -> Path:
    """Write results to ``docs/bge-m3-encoding-benchmark-results.md``."""
    project_root = Path(__file__).resolve().parent.parent.parent
    doc_path = project_root / "docs" / "bge-m3-encoding-benchmark-results.md"

    content = _hardware_header() + format_results(results) + "\n"
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


# ---------------------------------------------------------------------------
# pytest entry point
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_encoding_benchmark() -> None:
    """Run the full encoding benchmark as a pytest test.

    Requires:

    - bge-m3 model (~3 GB RAM)
    - psutil

    Skip with ``pytest -m 'not benchmark'`` (the project default).
    """
    print("\nRunning BGE-M3 encoding benchmark...")
    results = run_benchmark()
    output = format_results(results)
    print("\n" + output)

    doc_path = write_results_doc(results)
    print(f"\nResults written to {doc_path}")

    # Sanity: we got results for all configurations
    assert len(results) == len(BATCH_SIZES) * len(MODES)

    # Sanity: all throughputs are positive
    for r in results:
        assert r.chunks_per_second > 0, (
            f"Zero throughput for batch_size={r.batch_size}, mode={r.mode}"
        )


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    print("BGE-M3 Encoding Benchmark")
    print("=" * 40)
    print(f"Corpus: {CORPUS_SIZE} chunks, ~{TARGET_TOKENS} tokens each")
    print(f"Batch sizes: {BATCH_SIZES}")
    print(f"Modes: {MODES}")
    print()

    bench_results = run_benchmark()
    output = format_results(bench_results)
    print("\n" + output)

    doc = write_results_doc(bench_results)
    print(f"\nResults written to {doc}")
    sys.exit(0)
