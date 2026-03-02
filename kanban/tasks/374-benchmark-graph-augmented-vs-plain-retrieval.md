---
id: 374
title: 'Benchmark: graph-augmented vs plain retrieval'
status: archived
priority: important
created: 2026-03-01T20:13:43.1298831+01:00
updated: 2026-03-02T09:16:57.0288632+01:00
started: 2026-03-01T20:22:44.8020767+01:00
completed: 2026-03-02T09:16:57.0288632+01:00
tags:
    - phase-9
    - test
    - knowledge-graph
depends_on:
    - 258
    - 373
class: standard
---

From docs/graph-augmented-retrieval-impl-research.md §3.5 (quality assessment) and §5.5 (follow-up).

## Acceptance Criteria

- [ ] Benchmark script at `tests/benchmarks/bench_graph_expansion.py`
- [ ] Synthetic test corpus: 10+ cross-referencing documents:
  - ISO norm A references ISO norm B (`RELATED_TO` edges)
  - API doc references class doc (`IMPLEMENTS` edges)
  - Policy doc references regulation doc (`GOVERNED_BY` edges)
- [ ] 10+ cross-reference queries with known relevant docs (hand-crafted ground truth):
  - e.g., 'What ISO standards does security policy reference?' expects norm A, norm B
- [ ] Corpus ingested into in-memory `GraphStore` (SQLite `:memory:`) + `QdrantVectorStore(location=':memory:')`
- [ ] Entities and edges manually inserted via `GraphStore.insert_entity()` / `insert_edge()` (no LLM needed)
- [ ] Embeddings generated via `BgeM3EmbeddingProvider` or mocked dense vectors (builder decides based on runtime)
- [ ] Recall@10 measured per query: with expansion (`expansion_enabled=True`) vs without (`expansion_enabled=False`)
- [ ] Uses existing `GraphAugmentedRetriever` class (src/owlbear/memory/knowledge/retrieval.py)
- [ ] Comparison table output: `query | Recall@10-plain | Recall@10-expanded | delta`
- [ ] Results documented in `docs/graph-expansion-benchmark-results.md`
- [ ] `@pytest.mark.benchmark` marker — skipped in normal test runs
- [ ] ruff clean

## Patterns to follow

- `GraphAugmentedRetriever(vector_store, graph_store, embedding_provider, expansion_enabled=…)`
- `RetrievalResult` model (retrieval.py) — chunks, expansion_text, entities_found
- `GraphStore.insert_entity()` / `insert_edge()` for synthetic graph setup
- `QdrantVectorStore(location=':memory:')` for ephemeral vector store

## Notes

- Dependencies #258 (research) and #373 (integration) are both done.
- Synthetic corpus avoids BEIR/ranx dependency — simpler, faster, targeted.
- Key question: does graph expansion improve Recall@10 on cross-reference queries?
- Expected: expansion significantly improves recall for cross-reference queries, minimal impact on self-contained queries.
