# Qdrant Local Mode for bge-m3 Hybrid Search

> **Owning task:** #236 — Research: Qdrant local mode for bge-m3 hybrid search (dense+sparse+ColBERT)
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear uses sqlite-vec (384d bge-small via FastEmbed). sqlite-vec has no sparse vector support and hybrid search (dense+sparse+ColBERT) requires heavy custom code. bge-m3 outputs all three vector types in one pass but vec0 can't store them. **Question:** Replace sqlite-vec with Qdrant local mode for native hybrid search?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Qdrant vectors docs | qdrant.tech/documentation/concepts/vectors | .95 | Named vectors, sparse, multivectors (ColBERT) |
| Qdrant hybrid queries docs | qdrant.tech/documentation/concepts/hybrid-queries | .95 | Prefetch, RRF/DBSF fusion, multi-stage queries |
| qdrant-client GitHub + PyPI | github.com/qdrant/qdrant-client | .95 | Local mode: QdrantLocal, deps, 20K threshold |
| yuniko-software/bge-m3-qdrant-sample | github.com/yuniko-software/bge-m3-qdrant-sample | .90 | Full bge-m3 + Qdrant: collection, embed, hybrid search |
| Qdrant "Hybrid Search Revamped" | qdrant.tech/articles/hybrid-search | .85 | ColBERT HNSW optimization (m=0), fusion vs reranking |
| qdrant/workshop-ultimate-hybrid-search | github.com/qdrant/workshop-ultimate-hybrid-search | .80 | Official Qdrant hybrid search evaluation workshop |
| OwlBear dual-embedding-rrf-research | docs/research/dual-embedding-rrf.md | .90 | sqlite-vec sparse storage options, RRF analysis |
| OwlBear embedding-model-shootout | docs/embedding-model-shootout.md | .90 | bge-m3 deferred to this task, RAM projections |
| OwlBear VectorStore source | src/owlbear/memory/knowledge/vectors.py | .95 | Current: bridge table, vec0, search_similar |

## 3. Analysis

### 3.1 Qdrant Local Mode Architecture

**Pure Python** — no Rust binary, no server. `QdrantClient(path="./data")` instantiates `QdrantLocal` with numpy for vector ops, JSON metadata persistence, portalocker for single-process locking.

| Aspect | Detail |
|--------|--------|
| **Engine** | `qdrant_client.local.QdrantLocal` — numpy dot products, no HNSW |
| **Init** | `QdrantClient(":memory:")` or `QdrantClient(path="./qdrant_data")` |
| **Deps** | httpx, numpy, pydantic, grpcio, protobuf, urllib3, portalocker |
| **Install** | `pip install qdrant-client` — ~5 MB wheel, no compilation |
| **Limits** | No HNSW/payload indexes (brute-force), no snapshots/sharding, single-process, warning at >20K pts |
| **API** | Same as server — migrate by changing constructor arg |

**OwlBear fit:** <10K chunks initially. Local mode brute-force is fine. Scale to Docker Qdrant by changing one line.

### 3.2 Named Vectors + Hybrid Search API

One collection stores dense+sparse+ColBERT per point. Key API patterns (from yuniko-software/bge-m3-qdrant-sample):

```python
# Collection: 3 named vector spaces
client.create_collection(
    "knowledge",
    vectors_config={
        "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
        "colbert": models.VectorParams(
            size=1024,
            distance=models.Distance.COSINE,
            multivector_config=models.MultiVectorConfig(comparator=models.MultiVectorComparator.MAX_SIM),
            hnsw_config=models.HnswConfigDiff(m=0),
        ),  # No HNSW for rerank-only vectors
    },
    sparse_vectors_config={"sparse": models.SparseVectorParams()},
)

# Upsert: all 3 vector types + payload metadata (replaces bridge table)
client.upsert(
    "knowledge",
    points=[
        models.PointStruct(
            id=chunk_id,
            payload={"entity_id": "...", "scope": "global", "type": "entity"},
            vector={
                "dense": dense_vec,
                "colbert": colbert_vecs,
                "sparse": models.SparseVector(indices=[...], values=[...]),
            },
        )
    ],
)

# Hybrid search: sparse+dense prefetch → ColBERT rerank (single API call)
results = client.query_points(
    "knowledge",
    prefetch=[
        models.Prefetch(query=sparse_vec, using="sparse", limit=20),
        models.Prefetch(query=dense_vec, using="dense", limit=20),
    ],
    query=colbert_vecs,
    using="colbert",
    limit=10,
)
```

**Fusion options:** RRF (`Fusion.RRF`), weighted RRF (`Rrf(weights=[3.0,1.0])`), DBSF, or ColBERT rerank. The ColBERT-rerank pattern (prefetch dense+sparse → rescore with max_sim) is recommended by Qdrant and the bge-m3-qdrant-sample repo.

### 3.3 bge-m3 Integration

`BGEM3FlagModel("BAAI/bge-m3", use_fp16=True).encode([text], return_dense=True, return_sparse=True, return_colbert_vecs=True)` → dense (1024d), sparse (token_id→weight dict), ColBERT (N×1024d). Sparse conversion: filter positive weights, extract indices/values → `models.SparseVector`.

| Component | RAM | Disk |
|-----------|-----|------|
| bge-m3 (FP16) | ~3.0 GB | ~1.2 GB |
| qdrant-client | ~20 MB | ~5 MB |
| Vectors (10K pts) | ~150 MB | ~200 MB |
| **Total** | **~3.2 GB** | **~1.4 GB** |

FastEmbed **cannot** do bge-m3 — FlagEmbedding (PyTorch) required. But we already have PyTorch for bge-reranker-v2-m3. Net new dep: only `qdrant-client`.

### 3.4 Migration Path

**Current:** `VectorStore(conn)` → sqlite-vec vec0 + bridge table + 384d dense only + optional cross-encoder reranker. **Proposed:** `QdrantVectorStore(client)` → named vectors (dense+sparse+colbert) + payloads for metadata. Keep SQLite for relational data (entities, edges, documents, chunks).

**Steps:** (1) Create `VectorStoreProtocol`; (2) Implement `QdrantVectorStore`; (3) Re-embed with bge-m3 (384→1024d, ~17 min for 10K chunks); (4) Move scope/type to payloads; (5) Drop bridge table + vec0 tables.

### 3.5 Comparison

| Criterion | sqlite-vec (current) | sqlite-vec + custom sparse | Qdrant local + bge-m3 |
|-----------|---------------------|---------------------------|----------------------|
| Dense | ✅ vec0 384d | ✅ vec0 | ✅ named vector 1024d |
| Sparse | ❌ | Custom + app-level scoring | ✅ native |
| ColBERT | ❌ | ❌ | ✅ multivector max_sim |
| Hybrid fusion | ❌ | Manual RRF ~50 LOC | ✅ single API call |
| New deps | None | None | qdrant-client (~5MB) |
| Embed RAM | ~80 MB | ~850 MB (dual) | ~3 GB (already present) |
| Impl LOC | ~480 (existing) | ~700 | ~200 (new) |
| Quality | Dense-only | Dense+sparse RRF | Dense+sparse+ColBERT |
| Scale path | None | None | → Qdrant server (1 line) |

**Switch trigger:** Feature-driven. Need sparse search (ISO clauses)? → now. Need ColBERT reranking? → now. Corpus >20K? → Docker Qdrant. Want ONNX-only? → defer, use SPLADE++ per #232.

## 4. Recommendation (.80 confidence)

**Adopt Qdrant local + bge-m3.** Rationale: (1) Single model, three outputs — eliminates dual-model #232 approach. (2) Native hybrid search replaces ~300 LOC custom code. (3) Net-zero heavy deps — PyTorch already present for reranker. (4) Payloads replace bridge table. (5) Scale-up: change constructor → Qdrant server.

**Risks:** bge-m3 3GB RAM (.20 — fits 11GB budget), local mode slow >20K (.15 — switch to Docker), FlagEmbedding API changes (.30 — pin version + adapter).

**Supersedes** #232 Option B (dual FastEmbed + manual RRF + custom sparse table). Qdrant+bge-m3 is simpler and higher quality.

## 5. Follow-up Tasks

1. **Create VectorStoreProtocol** — Protocol class from current VectorStore API. Both backends implement it. Priority: needed. Tags: phase-9, knowledge-graph, embedding.
2. **Implement QdrantVectorStore** — qdrant-client local, named vectors, prefetch+ColBERT rerank. TDD. Priority: needed. Tags: phase-9, knowledge-graph, embedding. Depends: 1.
3. **Implement Bge-m3 EmbeddingProvider** — Wrap BGEM3FlagModel. Dense+sparse+ColBERT from single pass. Lazy loading. TDD. Priority: needed. Tags: phase-9, embedding. Depends: 1.
4. **Wire QdrantVectorStore into pipeline** — Replace VectorStore in GraphStore/ingestion. Scope filtering, temporal boost. TDD. Priority: needed. Tags: phase-9, knowledge-graph. Depends: 2, 3.
5. **Data migration script** — Re-embed all content with bge-m3, populate Qdrant. Priority: important. Tags: phase-9, knowledge-graph. Depends: 4.
6. **Benchmark hybrid search quality** — nDCG@10 + keyword precision: bge-small vs bge-m3 hybrid. Priority: important. Tags: phase-9, test. Depends: 5.
7. **Evaluate ColBERT vs cross-encoder rerank** — If ColBERT suffices, drop FlagReranker path. Priority: nice-to-have. Tags: phase-9, embedding. Depends: 6.

## 6. Attribution

| Source | URL | What | Where Used | Date |
|--------|-----|------|------------|------|
| qdrant-client | github.com/qdrant/qdrant-client | Local mode API, QdrantLocal, deps | docs/research/qdrant-local.md | 2026-02-28 |
| Qdrant vectors docs | qdrant.tech/documentation/concepts/vectors | Named/sparse/multivectors | docs/research/qdrant-local.md | 2026-02-28 |
| Qdrant hybrid queries docs | qdrant.tech/documentation/concepts/hybrid-queries | Prefetch, RRF, DBSF | docs/research/qdrant-local.md | 2026-02-28 |
| Qdrant hybrid search article | qdrant.tech/articles/hybrid-search | ColBERT HNSW opt (m=0) | docs/research/qdrant-local.md | 2026-02-28 |
| bge-m3-qdrant-sample | github.com/yuniko-software/bge-m3-qdrant-sample | Full integration pattern | docs/research/qdrant-local.md | 2026-02-28 |
| workshop-ultimate-hybrid-search | github.com/qdrant/workshop-ultimate-hybrid-search | Evaluation workshop | docs/research/qdrant-local.md | 2026-02-28 |
