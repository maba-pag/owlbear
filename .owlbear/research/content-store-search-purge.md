# ContentStore — Search & Purge Implementation

> **Owning task:** #1872 — Knowledge: ContentStore — search & purge
> **Date:** 2026-05-26 **Status:** Complete

## 1. Context and Question

Task #1872 implements the remaining ContentStore protocol methods: `search()`, `purge_source()`, and `stats()`. The protocol is defined in `serve/knowledge/src/owlbear_knowledge/protocols/content.py` and the existing implementation (from #1871) lives in `serve/knowledge/src/owlbear_knowledge/stores/content.py`.

**Key questions:**
1. How should hybrid search (vector + keyword) be combined and scored?
2. FTS5 or LIKE for the SQLite keyword component?
3. How to normalize scores to [0.0–1.0]?
4. How to handle `source_ids` filtering (not in Qdrant payload)?

## 2. Sources Studied

| Source | Relevance | Type |
|--------|-----------|------|
| `protocols/content.py` protocol definition | 1.0 | Codebase |
| `stores/content.py` existing implementation | 1.0 | Codebase |
| `qdrant.py` — QdrantVectorStore | 0.9 | Codebase |
| `retrieval.py` — GraphAugmentedRetriever | 0.8 | Codebase — existing hybrid search pattern |
| `embeddings.py` — EmbeddingProvider + BgeM3 | 0.8 | Codebase |
| `protocol.py` — VectorStoreProtocol | 0.8 | Codebase |
| Supermemory "Hybrid Search Guide" (2026) | 0.7 | Web — RRF approach |
| ParadeDB "What is RRF?" | 0.6 | Web — fusion theory |

## 3. Analysis

### 3.1 Hybrid Search Strategy

| Approach | Complexity | Accuracy | KISS fit | Notes |
|----------|-----------|----------|----------|-------|
| **A: Vector-only (use Qdrant internal hybrid)** | Low | High | Best | BgeM3 sparse vectors already do lexical matching; `search_similar` handles RRF internally |
| B: Vector + SQLite LIKE boost | Medium | Marginal gain | Fair | Adds ~20 LOC but BgeM3 sparse already covers this |
| C: Vector + SQLite FTS5 | High | Marginal gain | Poor | Requires virtual table, sync on ingest, no existing FTS5 in codebase |

**Finding:** The existing QdrantVectorStore already implements full hybrid search (dense + sparse + ColBERT reranking via RRF) when given a `HybridEmbedding`. BgeM3's sparse vectors are BM25-equivalent token weights. Adding SQLite keyword matching on top provides marginal benefit at significant complexity.

**Recommended approach (A with LIKE fallback):**
1. Embed query via `embed_hybrid` (fallback to `embed`) — mirrors `retrieval.py` line 78
2. Call `search_similar(embedding, top_k=overfetch, embedding_type="document", scopes=scopes)`
3. Post-filter via SQLite for `source_ids` (not in Qdrant payload)
4. Apply `min_score` threshold
5. Return top_k results

The SQLite LIKE fallback is only needed for the Mock/test path where `search_similar` isn't real. In production, Qdrant's internal hybrid covers both vector and keyword matching.

### 3.2 Score Normalization

Qdrant cosine similarity is already in [0.0, 1.0]. The `_hybrid_search` method in `qdrant.py` explicitly computes cosine similarity for final scores (lines 250–258). No additional normalization needed — scores pass through directly.

### 3.3 Source_ids Filtering

`ContentSearchQuery.source_ids` is not stored in the Qdrant payload. Strategy:
- Over-fetch from Qdrant (e.g., `top_k * 3`)
- Join with `content_chunks` table on chunk_id to filter by source_id
- This is efficient because SQLite lookup by primary key is O(1)

### 3.4 Scope Filtering

`ContentSearchQuery.scopes` IS in the Qdrant payload (stored as `scope` via `store_embedding`). Can be passed directly to `search_similar(scopes=list(query.scopes))`.

### 3.5 Purge Implementation

Straightforward cascade:
1. `SELECT id FROM content_chunks WHERE source_id = ?` → chunk_ids
2. `SELECT document_id FROM content_documents WHERE source_id = ?` → document_ids
3. `_delete_vectors(chunk_ids)` — removes from Qdrant
4. `DELETE FROM content_chunks WHERE source_id = ?`
5. `DELETE FROM content_documents WHERE source_id = ?`
6. Return `ContentPurgeResult(source_id, document_ids, chunk_ids, vector_ids=chunk_ids)`

Idempotency: empty SELECT → empty tuples → no deletes → zero-count result.

### 3.6 Stats Implementation

```sql
SELECT COUNT(*) FROM content_documents  -- documents
SELECT COUNT(*) FROM content_chunks     -- chunks (= vectors, 1:1 mapping)
```

### 3.7 AC/Protocol Discrepancy

AC4 says `stats() returns ContentStats with document_count, chunk_count, total_tokens` but the protocol model `ContentStats` has fields `documents`, `chunks`, `vectors`. The protocol model is committed code and is the source of truth — builder should implement against model fields.

## 4. Recommendation

**Confidence: 0.85**

Implement vector-primary search leveraging existing Qdrant hybrid internals:
- Use `embed_hybrid` → `search_similar` pipeline (proven pattern from `retrieval.py`)
- Post-filter `source_ids` via SQLite primary key lookup
- No FTS5, no separate keyword path — YAGNI; BgeM3 sparse vectors already handle lexical
- Purge: sequential cascade (chunks → documents → vectors), idempotent by design
- Stats: simple COUNT queries

Challenge: proceed — confidence in original: 0.85. The approach mirrors existing retrieval patterns, adds no new dependencies, and avoids premature abstraction.

## 5. Testing Strategy

- Mock `search_similar` return values (same pattern as #1871 tests)
- Test scope filtering, source_ids post-filtering, min_score threshold
- Test purge idempotency (purge unknown source → zero counts)
- Test purge cascade (documents + chunks + vectors all removed)
- Test stats accuracy after ingest and purge cycles
