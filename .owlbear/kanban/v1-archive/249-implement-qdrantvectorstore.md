---
id: 249
title: Implement QdrantVectorStore
status: archived
priority: needed
created: 2026-02-28T12:39:16.5506035+01:00
updated: 2026-02-28T23:54:26.1472726+01:00
started: 2026-02-28T16:34:31.0155477+01:00
completed: 2026-02-28T23:54:26.1472726+01:00
tags:
    - phase-9
    - knowledge-graph
    - embedding
depends_on:
    - 247
class: standard
---

## Context

Wrap qdrant-client local mode. 3 named vectors (dense 1024d COSINE, sparse learned lexical, ColBERT multivector MAX_SIM). Prefetch+fusion+ColBERT rescore in single API call.

## Research Done

- docs/research/qdrant-local.md — collection schema, API patterns, ~200 LOC estimate
- docs/research/qdrant-local-features.md — all 7 features verified in source code
- docs/research/colbert-vs-crossencoder.md — prefetch->ColBERT rescore pattern
- Collection config: dense + sparse + colbert (hnsw m=0)
- Payloads replace bridge table: {chunk_id, document_id, entity_id, scope, type, created_at}
- Local: QdrantClient(path='./data/qdrant'), pure Python, numpy, no HNSW

## Research Answers (Architect Decisions)

### Q1: Point ID strategy?

Use `uuid.uuid5(NAMESPACE_URL, entity_or_doc_id)` — deterministic UUID from the string ID. Enables upsert by ID. Handles any input format (hex, "docid:chunk:0", etc.).

### Q2: Same collection or separate?

Single "knowledge" collection. Distinguish entity vs document via `embedding_type` payload field + payload filter. Simpler, matches research doc §3.2.

### Q3: Temporal boost?

Python post-processing after Qdrant query. Query Qdrant payloads for `created_at`, compute recency score in Python. Same formula as existing `_compute_recency_score()` in `vectors.py`. No SQLite dependency needed — all data in Qdrant payloads.

### Q4: Corruption recovery?

Out of scope (YAGNI). Re-ingest if data corrupts. Qdrant local uses portalocker for single-process safety.

### Q5: delete_by_document_id?

Qdrant `scroll()` + `delete()` with `FieldCondition(key="document_id", match=MatchValue(value=doc_id))`. Confirmed from Qdrant API.

## Acceptance Criteria

- [ ] `QdrantVectorStore` class in `src/owlbear/memory/knowledge/qdrant.py` (new file)
- [ ] Implements `VectorStoreProtocol` (`isinstance` check passes)
- [ ] Constructor: `path: str | Path` (Qdrant local storage), `collection_name: str = "knowledge"`
- [ ] Collection created on first operation (lazy init) with 3 named vectors:
  - `"dense"`: `VectorParams(size=1024, distance=COSINE)`
  - `"sparse"`: `SparseVectorParams()`
  - `"colbert"`: `VectorParams(size=1024, distance=COSINE, multivector_config=MultiVectorConfig(comparator=MAX_SIM), hnsw_config=HnswConfigDiff(m=0))`
- [ ] `store_embedding(entity_or_doc_id, embedding, embedding_type, scope)`:
  - Point ID: `uuid5(NAMESPACE_URL, entity_or_doc_id)` — deterministic
  - Payload: `{entity_or_doc_id, embedding_type, scope, created_at}` (ISO-8601 now)
  - `HybridEmbedding` input → stores all 3 named vectors
  - `list[float]` input → stores dense only (sparse/colbert omitted in vector dict)
  - Upsert semantics (Qdrant `upsert()` overwrites existing point)
- [ ] `get_embedding(entity_or_doc_id) -> list[float] | None` — retrieve dense vector from point payload
- [ ] `search_similar(query_embedding, top_k, embedding_type, *, scopes, recency_weight, decay_rate)`:
  - `HybridEmbedding` input: `prefetch(sparse limit=top_k*3, dense limit=top_k*3)` → ColBERT rescore → `top_k`
  - `list[float]` input: dense-only search, `limit=top_k`
  - `scopes` filter: `FieldCondition(key="scope", match=MatchAny(any=scopes))`
  - `embedding_type` filter: `FieldCondition(key="embedding_type", match=MatchValue(value=...))` when not `None`
  - `recency_weight > 0`: post-process in Python — read `created_at` from result payloads, apply `_compute_recency_score()` formula
- [ ] `delete_embedding(entity_or_doc_id) -> bool` — delete point by uuid5 ID, return `True` if found
- [ ] `delete_by_document_id(document_id: str) -> int` — scroll+delete all points with payload `document_id` match, return count deleted (NOT in VectorStoreProtocol — extra method)
- [ ] `ImportError` guard when `qdrant-client` not installed
- [ ] Persistence: `QdrantClient(path=...)` survives process restart

## TDD — tests in `tests/test_qdrant_store.py` (new file)

- [ ] `QdrantVectorStore` satisfies `VectorStoreProtocol` (`isinstance` check)
- [ ] Store + get roundtrip (dense-only `list[float]`)
- [ ] Store hybrid + get returns dense vector
- [ ] Search returns results ordered by relevance
- [ ] Search with `HybridEmbedding` input uses prefetch+rescore
- [ ] Search with scope filter excludes out-of-scope points
- [ ] Search with `embedding_type` filter
- [ ] `delete_embedding` returns `True` when found, `False` when not
- [ ] `delete_by_document_id` removes correct points, returns count
- [ ] Collection created on first operation (lazy init verified)
- [ ] Empty collection returns empty search results
- [ ] Use `QdrantClient(":memory:")` in tests for isolation — no disk fixture needed

## Architecture Notes

- Import `SparseVector`, `HybridEmbedding` from `owlbear.memory.knowledge.protocol`
- Convert `protocol.SparseVector` → `qdrant_client.models.SparseVector(indices, values)`
- Temporal boost formula: reuse `_compute_recency_score()` logic — extract into a shared utility or inline (resolve when #251 deletes `vectors.py`)
- `IMPORTANCE_BY_TYPE` dict from `vectors.py` also needed — extract or inline in qdrant.py
- ~200 LOC estimate (research doc §3.4)
