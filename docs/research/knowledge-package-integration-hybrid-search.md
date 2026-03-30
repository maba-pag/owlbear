# Knowledge Package Integration + Hybrid Search

> **Owning task:** #34 — Knowledge package integration + hybrid search
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #34 is subtask 4/4 of knowledge engine extraction (#15→#32→#33→#34). It calls for wiring up hybrid search (graph + vector), integration tests, package installability, and a README. Much code was extracted ahead-of-schedule during #15. **Key questions:** (a) What's already extracted vs what remains? (b) How should hybrid search work in v2? (c) What's blocked by upstream #33?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| v1 retrieval.py (local) | `v1/src/owlbear/memory/knowledge/retrieval.py` | `1.0` — GraphAugmentedRetriever: dual-path search + BFS expansion |
| v1 query_service.py (local) | `v1/src/owlbear/memory/knowledge/query_service.py` | `1.0` — Full search pipeline with retriever delegation |
| v2 query_service.py (local) | `packages/knowledge/src/owlbear_knowledge/query_service.py` | `1.0` — Simplified vector-only extraction |
| graph-augmented-retrieval-impl.md (internal) | `docs/research/graph-augmented-retrieval-impl.md` | `.95` — Design for GraphAugmentedRetriever |
| dual-embedding-rrf.md (internal) | `docs/research/dual-embedding-rrf.md` | `.90` — BGE-M3 hybrid search architecture |
| MS GraphRAG v3 | `github.com/microsoft/graphrag` | `.85` — Multi-package monorepo, retrieval as separate concern |
| LightRAG (HKUDS, EMNLP 2025) | `github.com/HKUDS/LightRAG` | `.85` — "mix" mode: KG + vector search with token budgets |
| extract-vector-store-embedding-pipeline.md (internal) | `docs/research/extract-vector-store-embedding-pipeline.md` | `.90` — #32 gap analysis |
| knowledge-subpackages.md (internal) | `docs/research/knowledge-subpackages.md` | `.70` — Flat layout decision |

## 3. Analysis

### 3.1 Extraction Status — Gap Analysis

| AC Item | v2 file exists? | v1 feature parity? | Action |
|---------|----------------|---------------------|--------|
| Extract query_service.py | ✅ (119 LOC) | Partial — missing `query_for_context()`, retriever delegation, consolidation | Upgrade |
| Extract retrieval.py | ❌ Missing | N/A | Extract from v1 (228 LOC) |
| Extract chunker.py | ✅ (133 LOC) | Full | None |
| Hybrid search works | ❌ Vector-only | v1 has dual-path (vector + graph BFS) | Wire retriever |
| Full ingest-to-search test | ❌ | Requires IngestPipeline (#33) | **Blocked** |
| Package installable | ✅ Likely | Needs verification | Verify |
| Cross-module imports | ✅ Likely | Needs verification | Verify |
| README.md | ❌ Missing | N/A | Create |

### 3.2 v1 retrieval.py Architecture (228 LOC)

`GraphAugmentedRetriever` implements a 3-step pipeline:

1. **Vector search** — embed query → `search_similar(embedding_type="document")` → top-k chunks
2. **Seed resolution** — match chunk IDs to entities via `chunk_id` field → seed entities
3. **Graph expansion** — BFS via `get_neighbors()` per seed, budget-capped → expansion text

Returns `RetrievalResult(chunks, expansion_text, entities_found)`.

v1 `KnowledgeQueryService._search_chunks()` delegates to the retriever when present, falling back to direct vector search. This composition pattern is clean and matches KISS.

### 3.3 Hybrid Search — What v2 Needs (.85 confidence)

| Component | v2 status | Gap |
|-----------|----------|-----|
| Dense vector search | ✅ QdrantVectorStore.search_similar | None |
| Sparse vector storage | ✅ Qdrant collection has sparse config | None |
| Qdrant hybrid search (prefetch+RRF) | ❌ search_similar is dense-only | Need `_hybrid_search` from v1 |
| GraphAugmentedRetriever | ❌ retrieval.py missing | Extract from v1 |
| Retriever wiring in query_service | ❌ v2 lacks delegation | Upgrade query_service.py |
| ColBERT rescore | ❌ Collection lacks ColBERT vector config | Deferred (nice-to-have) |

Both LightRAG ("mix" mode) and MS GraphRAG use the same dual-path pattern: vector search for chunk relevance + graph traversal for relationship context. LightRAG's token budget system (`max_entity_tokens=6000`, `max_relation_tokens=8000`, `max_total_tokens=30000`) validates our budget-cap approach (v1 uses `max_expansion_tokens=2000`).

### 3.4 Dependency Analysis

```
#15 (archived) → #32 (backlog) → #33 (ideation) → #34 (ideation)
```

#33 owns the ingest pipeline (`IngestPipeline`, `DocumentStore`). The AC item "Full ingest-to-search cycle test" requires ingesting a document → extracting entities → building graph → embedding chunks → searching. This is impossible without #33.

**Recommendation (.85 confidence):** Split the ingest-to-search cycle test into a separate integration test task that depends on both #33 and #34. The remaining #34 AC items can proceed independently.

### 3.5 AC Refinement

| Original AC | Assessment | Refined |
|-------------|-----------|---------|
| Extract query_service.py | Already exists but incomplete | Upgrade: add `query_for_context()`, retriever delegation |
| Extract retrieval.py | Missing | Extract `GraphAugmentedRetriever` + `RetrievalResult` from v1 |
| Extract chunker.py | ✅ Done | Remove from AC (completed under #15) |
| Hybrid search works | Requires retrieval.py + Qdrant hybrid | Wire retriever into query_service, add Qdrant hybrid prefetch |
| Full ingest-to-search test | Blocked by #33 | Move to separate task dependent on #33 + #34 |
| Package installable | Needs verification only | Keep |
| Cross-module imports | Needs verification only | Keep |
| README.md | Missing | Create with setup instructions |

### 3.6 README Content Scope

Per prior research (#32, `extract-vector-store-embedding-pipeline.md`), the README should cover:
- Package purpose and module overview
- Qdrant setup (`:memory:`, local file, remote)
- BGE-M3 model download (~2.3 GB, `~/.cache/huggingface/hub/`)
- Optional dependency installation (`uv pip install 'owlbear-knowledge[full]'`)
- Quick usage example

## 4. Recommendation (.85 confidence)

**Split #34 into focused, unblockable work + a deferred integration test.** Extract retrieval.py, upgrade query_service.py with retriever delegation, add Qdrant hybrid search, create README, and verify package. Defer the ingest-to-search cycle test to a new task after #33 lands.

**Risks:**
- `GraphAugmentedRetriever._resolve_seeds()` in v1 matches entities by `chunk_id` — this requires entities to have `chunk_id` populated during ingestion (#33 scope). Until #33, the retriever's seed resolution returns empty results. Mitigation: the retriever falls back gracefully (returns vector-only results when no seeds found).
- Qdrant hybrid search (prefetch + RRF) adds ~50 LOC to `qdrant.py`. The `query_points` with prefetch API requires qdrant-client >= 1.9.0 (already specified).

## 5. Follow-up Tasks

Tasks created at `ideation` for architect gate.
