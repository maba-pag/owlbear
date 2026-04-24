"""Search quality benchmark CLI for the OwlBear knowledge base.

Compares hybrid (dense + sparse) vs. dense-only search across a set of
representative queries and asserts minimum quality thresholds.

Usage::

    python -m owlbear_knowledge.benchmark --db-path /path/to/knowledge/db
"""
# ruff: noqa: T201  -- print() is intentional in this CLI benchmark script

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.protocol import HybridEmbedding
from owlbear_knowledge.qdrant import QdrantVectorStore

SAMPLE_QUERIES: list[str] = [
    "how does the agent dispatch loop work",
    "what is the architecture of the knowledge graph",
    "how are embeddings stored and retrieved",
    "what is the TDD red-green workflow",
    "how does the orchestrator manage agent tasks",
]

_MIN_DOC_COUNT = 500
_MIN_DIFFERING_QUERIES = 3
_TOP_K = 3


def run_benchmark(db_path: Path) -> int:
    """Execute the search quality benchmark against the knowledge DB at *db_path*.

    Args:
        db_path: Directory containing ``local.db`` and a ``vectors/`` sub-directory.

    Returns:
        0 on success, 1 when any assertion fails.
    """
    conn = sqlite3.connect(str(db_path / "local.db"))
    graph = GraphStore(conn)
    vector_store = QdrantVectorStore(str(db_path / "vectors"))
    provider = BgeM3EmbeddingProvider()

    doc_count, entity_count, edge_count = graph.get_counts()
    print(f"Stats: documents={doc_count}, entities={entity_count}, edges={edge_count}")

    if doc_count < _MIN_DOC_COUNT:
        print(f"FAIL: doc_count {doc_count} < {_MIN_DOC_COUNT} (insufficient data)")
        return 1

    differing_count = 0
    for query in SAMPLE_QUERIES:
        embeddings = provider.embed_hybrid([query])
        hybrid_emb = embeddings[0]
        dense_only_emb = HybridEmbedding(dense=hybrid_emb.dense, sparse=None)

        hybrid_results = vector_store.search_similar(hybrid_emb, top_k=_TOP_K)
        dense_results = vector_store.search_similar(dense_only_emb, top_k=_TOP_K)

        hybrid_ids = [r[0] for r in hybrid_results[:_TOP_K]]
        dense_ids = [r[0] for r in dense_results[:_TOP_K]]

        print(f"Query: {query!r}")
        print(f"  Hybrid top-{_TOP_K}: {hybrid_ids}")
        print(f"  Dense-only top-{_TOP_K}: {dense_ids}")

        if len(hybrid_results) == 0:
            print("FAIL: query returned 0 results")
            return 1

        if hybrid_ids != dense_ids:
            differing_count += 1

    print(f"Hybrid differs from dense-only on {differing_count}/5 queries")

    if differing_count < _MIN_DIFFERING_QUERIES:
        n = len(SAMPLE_QUERIES)
        print(f"FAIL: only {differing_count}/{n} queries show ranking differences")
        return 1

    return 0


def main(args: list[str] | None = None) -> int:
    """Run the search quality benchmark.

    Args:
        args: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        0 on success, 1 when any assertion fails, 2 for argument parse errors.
    """
    parser = argparse.ArgumentParser(description="OwlBear search quality benchmark")
    parser.add_argument(
        "--db-path", required=True, help="Path to the knowledge DB directory"
    )
    parsed = parser.parse_args(args)

    return run_benchmark(Path(parsed.db_path))


if __name__ == "__main__":
    sys.exit(main())
