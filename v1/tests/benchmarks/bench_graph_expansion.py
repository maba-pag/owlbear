"""Benchmark: graph-augmented vs plain retrieval.

Compares Recall@10 with and without knowledge-graph expansion on a
synthetic cross-referencing corpus.  Runnable as a pytest test
(``@pytest.mark.benchmark``) or standalone::

    python tests/benchmarks/bench_graph_expansion.py

Task: #374
"""

from __future__ import annotations

import hashlib
import random
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.qdrant import DENSE_DIM, QdrantVectorStore
from owlbear.memory.knowledge.retrieval import GraphAugmentedRetriever, RetrievalResult
from owlbear.memory.knowledge.schema import init_db

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Synthetic corpus — 13 cross-referencing documents
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticDoc:
    """A document in the synthetic corpus."""

    id: str
    title: str
    content: str
    entity_type: EntityType = EntityType.CONCEPT


DOCS: list[SyntheticDoc] = [
    SyntheticDoc(
        "iso-27001",
        "ISO 27001",
        "ISO 27001 Information Security Management Systems standard providing "
        "requirements for establishing, implementing, maintaining and continually "
        "improving an information security management system.",
    ),
    SyntheticDoc(
        "iso-27002",
        "ISO 27002",
        "ISO 27002 Code of practice for information security controls. Provides "
        "implementation guidance for security controls referenced by ISO 27001.",
    ),
    SyntheticDoc(
        "iso-9001",
        "ISO 9001",
        "ISO 9001 Quality Management Systems requirements. Specifies requirements "
        "for organizations seeking to consistently provide products and services.",
    ),
    SyntheticDoc(
        "iso-14001",
        "ISO 14001",
        "ISO 14001 Environmental Management Systems standard. Specifies requirements "
        "for an environmental management system to enhance environmental performance.",
    ),
    SyntheticDoc(
        "iso-31000",
        "ISO 31000",
        "ISO 31000 Risk Management guidelines providing principles, framework, "
        "and process for managing risk across organizations.",
    ),
    SyntheticDoc(
        "gdpr",
        "GDPR",
        "General Data Protection Regulation. European Union regulation on data "
        "protection and privacy for individuals within the EU and EEA.",
    ),
    SyntheticDoc(
        "security-policy",
        "Security Policy",
        "Company information security policy. Establishes baseline security "
        "requirements aligned with ISO 27001 and ISO 27002 standards.",
        EntityType.PATTERN,
    ),
    SyntheticDoc(
        "data-protection-policy",
        "Data Protection Policy",
        "Data protection and privacy policy ensuring compliance with GDPR "
        "and ISO 27001 security management.",
        EntityType.PATTERN,
    ),
    SyntheticDoc(
        "quality-policy",
        "Quality Policy",
        "Company quality assurance policy aligned with ISO 9001 quality "
        "management system requirements.",
        EntityType.PATTERN,
    ),
    SyntheticDoc(
        "env-policy",
        "Environmental Policy",
        "Environmental management policy following ISO 14001 environmental "
        "management system standards.",
        EntityType.PATTERN,
    ),
    SyntheticDoc(
        "risk-policy",
        "Risk Management Policy",
        "Enterprise risk management policy based on ISO 31000 risk management "
        "guidelines and best practices.",
        EntityType.PATTERN,
    ),
    SyntheticDoc(
        "auth-service",
        "AuthService",
        "AuthService REST API documentation. Provides token-based authentication "
        "endpoints implementing the AuthBase abstract interface.",
        EntityType.CLASS_,
    ),
    SyntheticDoc(
        "auth-base",
        "AuthBase",
        "AuthBase abstract class defining the authentication interface contract "
        "for all auth service implementations.",
        EntityType.CLASS_,
    ),
]

# ---------------------------------------------------------------------------
# Graph edges — 10 cross-references
# ---------------------------------------------------------------------------

EDGES_SPEC: list[tuple[str, str, RelationType]] = [
    # Policy → Standard (GOVERNED_BY)
    ("security-policy", "iso-27001", RelationType.GOVERNED_BY),
    ("security-policy", "iso-27002", RelationType.GOVERNED_BY),
    ("data-protection-policy", "gdpr", RelationType.GOVERNED_BY),
    ("data-protection-policy", "iso-27001", RelationType.GOVERNED_BY),
    ("quality-policy", "iso-9001", RelationType.GOVERNED_BY),
    ("env-policy", "iso-14001", RelationType.GOVERNED_BY),
    ("risk-policy", "iso-31000", RelationType.GOVERNED_BY),
    # Standard ↔ Standard (RELATED_TO)
    ("iso-27001", "iso-27002", RelationType.RELATED_TO),
    ("iso-27001", "iso-31000", RelationType.RELATED_TO),
    # API → Class (IMPLEMENTS)
    ("auth-service", "auth-base", RelationType.IMPLEMENTS),
]


# ---------------------------------------------------------------------------
# Benchmark queries with hand-crafted ground truth (12 queries)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Query:
    """A benchmark query with ground truth."""

    text: str
    expected: frozenset[str]  # doc IDs that constitute a correct answer
    entry_points: tuple[str, ...]  # docs the query vector should be close to
    category: str  # "cross-ref" or "self-contained"


QUERIES: list[Query] = [
    # --- Cross-reference queries (expansion should improve recall) ---
    Query(
        "What ISO standards does the security policy reference?",
        frozenset({"security-policy", "iso-27001", "iso-27002"}),
        ("security-policy",),
        "cross-ref",
    ),
    Query(
        "Data protection regulatory compliance requirements",
        frozenset({"data-protection-policy", "gdpr", "iso-27001"}),
        ("data-protection-policy",),
        "cross-ref",
    ),
    Query(
        "Authentication service implementation class hierarchy",
        frozenset({"auth-service", "auth-base"}),
        ("auth-service",),
        "cross-ref",
    ),
    Query(
        "Quality management standards and company policy",
        frozenset({"quality-policy", "iso-9001"}),
        ("quality-policy",),
        "cross-ref",
    ),
    Query(
        "Environmental compliance standards and policy",
        frozenset({"env-policy", "iso-14001"}),
        ("env-policy",),
        "cross-ref",
    ),
    Query(
        "Risk management standards and enterprise policy",
        frozenset({"risk-policy", "iso-31000"}),
        ("risk-policy",),
        "cross-ref",
    ),
    Query(
        "Information security related standards and controls",
        frozenset({"iso-27001", "iso-27002", "iso-31000"}),
        ("iso-27001",),
        "cross-ref",
    ),
    Query(
        "Security controls referenced by data protection policy",
        frozenset({"data-protection-policy", "iso-27001", "iso-27002"}),
        ("data-protection-policy", "iso-27001"),
        "cross-ref",
    ),
    # --- Self-contained queries (expansion should have no negative impact) ---
    Query(
        "GDPR European data protection regulation details",
        frozenset({"gdpr"}),
        ("gdpr",),
        "self-contained",
    ),
    Query(
        "ISO 9001 quality management system requirements",
        frozenset({"iso-9001"}),
        ("iso-9001",),
        "self-contained",
    ),
    Query(
        "AuthBase abstract authentication interface contract",
        frozenset({"auth-base"}),
        ("auth-base",),
        "self-contained",
    ),
    Query(
        "ISO 14001 environmental management system standard",
        frozenset({"iso-14001"}),
        ("iso-14001",),
        "self-contained",
    ),
]


# ---------------------------------------------------------------------------
# Mock embedding provider (deterministic, no model download)
# ---------------------------------------------------------------------------


def _deterministic_vector(seed_str: str, dim: int = DENSE_DIM) -> list[float]:
    """Generate a reproducible unit vector from a string seed."""
    h = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(h)
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec]


def _make_query_vector(
    entry_point_ids: tuple[str, ...],
    noise_seed: int = 42,
    noise_scale: float = 0.05,
) -> list[float]:
    """Create a query vector close to the entry-point document vectors."""
    dim = DENSE_DIM
    avg = [0.0] * dim
    for doc_id in entry_point_ids:
        doc_vec = _deterministic_vector(doc_id)
        for i in range(dim):
            avg[i] += doc_vec[i]
    n = len(entry_point_ids)
    for i in range(dim):
        avg[i] /= n
    # Small noise so query isn't identical to doc vector
    rng = random.Random(noise_seed)
    for i in range(dim):
        avg[i] += rng.gauss(0, noise_scale / dim**0.5)
    # Normalize
    norm = sum(v * v for v in avg) ** 0.5
    return [v / norm for v in avg]


class MockEmbeddingProvider:
    """Deterministic embedding provider — no model download needed.

    Returns pre-computed vectors for known query texts and
    deterministic vectors for everything else.
    """

    def __init__(self, query_vectors: dict[str, list[float]]) -> None:
        self._query_vectors = query_vectors

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return dense embeddings for *texts*."""
        return [self._query_vectors.get(t, _deterministic_vector(t)) for t in texts]


# ---------------------------------------------------------------------------
# Store setup
# ---------------------------------------------------------------------------


def _setup_stores() -> tuple[GraphStore, QdrantVectorStore, dict[str, Entity]]:
    """Create in-memory stores and populate with the synthetic corpus."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    graph = GraphStore(conn)

    vectors = QdrantVectorStore(location=":memory:")

    entities: dict[str, Entity] = {}
    for doc in DOCS:
        entity = Entity(
            id=doc.id,
            name=doc.title,
            entity_type=doc.entity_type,
            description=doc.content,
            chunk_id=doc.id,
        )
        entities[doc.id] = entity
        graph.insert_entity(entity)

        embedding = HybridEmbedding(dense=_deterministic_vector(doc.id))
        vectors.store_embedding(doc.id, embedding, embedding_type="document")

    for src_id, tgt_id, relation in EDGES_SPEC:
        edge = Edge(source_id=src_id, target_id=tgt_id, relation=relation)
        graph.insert_edge(edge)

    return graph, vectors, entities


# ---------------------------------------------------------------------------
# Recall computation
# ---------------------------------------------------------------------------


def _compute_recall(
    result: RetrievalResult,
    expected: frozenset[str],
    entities: dict[str, Entity],
) -> float:
    """Fraction of *expected* doc IDs found in vector chunks or expansion text.

    A document counts as "found" if:
    - Its ID appears as a chunk_id in ``result.chunks``, OR
    - Its entity name appears in ``result.expansion_text``.
    """
    found: set[str] = set()

    # Direct vector-search hits
    for chunk_id, _score in result.chunks:
        if chunk_id in expected:
            found.add(chunk_id)

    # Entities surfaced via graph expansion
    if result.expansion_text:
        for doc_id in expected:
            entity = entities.get(doc_id)
            if entity and entity.name in result.expansion_text:
                found.add(doc_id)

    return len(found) / len(expected) if expected else 1.0


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkRow:
    """Per-query benchmark result."""

    query: str
    category: str
    recall_plain: float
    recall_expanded: float

    @property
    def delta(self) -> float:
        """Improvement from expansion (positive = better)."""
        return self.recall_expanded - self.recall_plain


def run_benchmark() -> list[BenchmarkRow]:
    """Run the full benchmark and return per-query results."""
    graph, vectors, entities = _setup_stores()

    # Pre-compute query vectors
    query_vectors: dict[str, list[float]] = {}
    for q in QUERIES:
        query_vectors[q.text] = _make_query_vector(q.entry_points)

    embedder = MockEmbeddingProvider(query_vectors)

    rows: list[BenchmarkRow] = []
    for q in QUERIES:
        # Plain retrieval (no expansion)
        plain = GraphAugmentedRetriever(
            vectors,
            graph,
            embedder,
            expansion_enabled=False,
        )
        plain_result = plain.retrieve(q.text, top_k=10)
        recall_plain = _compute_recall(plain_result, q.expected, entities)

        # Expanded retrieval
        expanded = GraphAugmentedRetriever(
            vectors,
            graph,
            embedder,
            expansion_enabled=True,
        )
        expanded_result = expanded.retrieve(q.text, top_k=10)
        recall_expanded = _compute_recall(expanded_result, q.expected, entities)

        rows.append(
            BenchmarkRow(
                query=q.text,
                category=q.category,
                recall_plain=recall_plain,
                recall_expanded=recall_expanded,
            )
        )

    return rows


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _avg(items: list[BenchmarkRow], attr: str) -> float:
    """Mean of *attr* across *items*."""
    if not items:
        return 0.0
    return sum(getattr(r, attr) for r in items) / len(items)


def format_results(rows: list[BenchmarkRow]) -> str:
    """Format benchmark results as a Markdown table."""
    lines = [
        "| Query | Category | Recall@10 Plain | Recall@10 Expanded | Delta |",
        "|-------|----------|----------------:|-------------------:|------:|",
    ]
    for r in rows:
        q = r.query[:55] + "..." if len(r.query) > 55 else r.query
        lines.append(
            f"| {q} | {r.category} "
            f"| {r.recall_plain:.2f} | {r.recall_expanded:.2f} "
            f"| {r.delta:+.2f} |",
        )

    cross_ref = [r for r in rows if r.category == "cross-ref"]
    self_cont = [r for r in rows if r.category == "self-contained"]

    lines.append("")
    lines.append("**Summary:**")
    lines.append("")
    lines.append(
        "| Category | Avg Recall@10 Plain | Avg Recall@10 Expanded | Avg Delta |",
    )
    lines.append("|----------|--------------------:|-----------------------:|----------:|")
    lines.append(
        f"| Cross-ref | {_avg(cross_ref, 'recall_plain'):.2f} "
        f"| {_avg(cross_ref, 'recall_expanded'):.2f} "
        f"| {_avg(cross_ref, 'delta'):+.2f} |",
    )
    lines.append(
        f"| Self-contained | {_avg(self_cont, 'recall_plain'):.2f} "
        f"| {_avg(self_cont, 'recall_expanded'):.2f} "
        f"| {_avg(self_cont, 'delta'):+.2f} |",
    )
    lines.append(
        f"| **Overall** | **{_avg(rows, 'recall_plain'):.2f}** "
        f"| **{_avg(rows, 'recall_expanded'):.2f}** "
        f"| **{_avg(rows, 'delta'):+.2f}** |",
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# pytest entry point
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_graph_expansion_benchmark() -> None:
    """Graph expansion should improve Recall@10 on cross-reference queries."""
    rows = run_benchmark()
    output = format_results(rows)
    print("\n" + output)

    # Cross-reference queries: expansion must improve average recall
    cross_ref = [r for r in rows if r.category == "cross-ref"]
    avg_delta_cross = _avg(cross_ref, "delta")
    assert avg_delta_cross > 0, (
        f"Expansion should improve cross-ref recall, got avg delta={avg_delta_cross:.3f}"
    )

    # Self-contained queries: expansion must not hurt recall
    self_cont = [r for r in rows if r.category == "self-contained"]
    for r in self_cont:
        assert r.delta >= 0, f"Expansion should not hurt self-contained query: {r.query}"


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


def _write_results_doc(output: str) -> Path:
    """Write results to docs/graph-expansion-benchmark-results.md."""
    # Resolve project root (two levels up from this file)
    project_root = Path(__file__).resolve().parent.parent.parent
    doc_path = project_root / "docs" / "graph-expansion-benchmark-results.md"

    header = (
        "# Graph-Augmented Retrieval Benchmark Results\n"
        "\n"
        "Generated by `tests/benchmarks/bench_graph_expansion.py` (task #374).\n"
        "\n"
        "## Setup\n"
        "\n"
        f"- **Corpus:** {len(DOCS)} synthetic documents with {len(EDGES_SPEC)} "
        "cross-reference edges\n"
        f"- **Queries:** {len(QUERIES)} hand-crafted queries "
        f"({sum(1 for q in QUERIES if q.category == 'cross-ref')} cross-ref, "
        f"{sum(1 for q in QUERIES if q.category == 'self-contained')} self-contained)\n"
        "- **Embeddings:** Mock dense vectors (dim 1024, deterministic random)\n"
        "- **Vector store:** QdrantVectorStore (in-memory)\n"
        "- **Graph store:** GraphStore (SQLite in-memory)\n"
        "- **Retriever:** GraphAugmentedRetriever (expansion_depth=1)\n"
        "\n"
        "## Edge types\n"
        "\n"
        "| Relation | Count | Example |\n"
        "|----------|------:|--------|\n"
        f"| GOVERNED_BY | "
        f"{sum(1 for _, _, r in EDGES_SPEC if r == RelationType.GOVERNED_BY)} "
        "| Security Policy → ISO 27001 |\n"
        f"| RELATED_TO | "
        f"{sum(1 for _, _, r in EDGES_SPEC if r == RelationType.RELATED_TO)} "
        "| ISO 27001 → ISO 27002 |\n"
        f"| IMPLEMENTS | "
        f"{sum(1 for _, _, r in EDGES_SPEC if r == RelationType.IMPLEMENTS)} "
        "| AuthService → AuthBase |\n"
        "\n"
        "## Results\n"
        "\n"
    )

    doc_path.write_text(header + output + "\n", encoding="utf-8")
    return doc_path


if __name__ == "__main__":
    results = run_benchmark()
    output = format_results(results)
    print(output)

    doc = _write_results_doc(output)
    print(f"\nResults written to {doc}")

    # Non-zero exit if expansion doesn't help cross-ref queries
    cross = [r for r in results if r.category == "cross-ref"]
    avg_delta = _avg(cross, "delta")
    if avg_delta <= 0:
        print(f"\nWARNING: expansion did not improve cross-ref recall (delta={avg_delta:.3f})")
        sys.exit(1)
