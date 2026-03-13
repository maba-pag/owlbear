---
id: 378
title: 'Benchmark embedding + indexing — bge-m3 into Qdrant :memory:'
status: archived
priority: needed
created: 2026-03-01T20:14:19.2384297+01:00
updated: 2026-03-02T09:17:02.6344332+01:00
started: 2026-03-01T20:22:50.8079774+01:00
completed: 2026-03-02T09:17:02.6344332+01:00
tags:
    - phase-9
    - test
    - embedding
depends_on:
    - 377
class: standard
---

From docs/research/hybrid-search-benchmark.md §3.5 (steps 2-3) and §5.3.

## Acceptance Criteria

- [ ] Function/fixture in `tests/benchmarks/` that embeds all NFCorpus docs
- [ ] Uses `BgeM3EmbeddingProvider.embed_hybrid()` — single pass produces dense (1024-d) + sparse + ColBERT per doc
- [ ] Stores all vectors in `QdrantVectorStore(location=':memory:')`
- [ ] Embeddings cached to `tests/benchmarks/.cache/embeddings.pkl` (pickle) to avoid recomputing (~10 min)
- [ ] Cache invalidated if corpus content changes (hash check on corpus keys)
- [ ] When cache exists, loads from disk and populates Qdrant in seconds
- [ ] Returns configured `QdrantVectorStore` instance ready for search
- [ ] `@pytest.mark.benchmark` marker
- [ ] ruff clean

## Patterns to follow

- `BgeM3EmbeddingProvider.embed_hybrid()` (src/owlbear/memory/knowledge/embeddings.py) — batch_size=16
- `QdrantVectorStore.store_embedding(id, embedding, 'document')` (src/owlbear/memory/knowledge/qdrant.py)

## Notes

- ~10 min CPU time for 3.6K docs on first run — cache is critical for fast re-runs.
- Same embedding pass feeds all 4 search modes in #379.
