---
id: 250
title: Wire QdrantVectorStore + BgeM3 into IngestPipeline
status: archived
priority: needed
created: 2026-02-28T12:39:28.315463+01:00
updated: 2026-02-28T23:54:26.780184+01:00
started: 2026-02-28T16:34:31.6041872+01:00
completed: 2026-02-28T23:54:26.780184+01:00
tags:
    - phase-9
    - knowledge-graph
    - embedding
depends_on:
    - 248
    - 249
class: standard
---

## Context

Swap the embedding provider and vector store in IngestPipeline. Replace FastEmbedProvider with BgeM3EmbeddingProvider. Replace VectorStore(conn) with QdrantVectorStore(client). Update pyproject.toml knowledge extras.

## Research Answers (Architect Decisions)

### Q1: _store_embeddings() dense-only → hybrid?

Yes. `_run_embed()` should call `embed_hybrid()` when available (duck-typed `hasattr` check), else fall back to `embed()` wrapping results as dense-only `HybridEmbedding`. `_store_embeddings()` passes `HybridEmbedding` to `VectorStoreProtocol.store_embedding()`.

### Q2: _run_embed() in executor still correct?

Yes. bge-m3 encoding is CPU-bound (PyTorch inference). Keep `run_in_executor`.

### Q3: QdrantClient in test fixtures?

Tests mock `VectorStoreProtocol` — don't need real QdrantClient. Integration tests (if any) use `QdrantClient(":memory:")` alongside in-memory SQLite.

### Q4: DI pattern?

Receive via constructor (existing pattern). `IngestPipeline.__init__()` already takes `vector_store` and `embedding_provider` as params. No change to DI shape — just widen type hints.

## Acceptance Criteria

- [ ] `IngestPipeline.__init__()` type hint: `vector_store: VectorStore` → `vector_store: VectorStoreProtocol`
- [ ] Import `VectorStoreProtocol` from `protocol.py` instead of `VectorStore` from `vectors.py` in `ingest.py` TYPE_CHECKING block
- [ ] `_run_embed()` prefers `embed_hybrid()` when provider has it (`hasattr` check):
  - Has `embed_hybrid` → returns `list[HybridEmbedding]`
  - No `embed_hybrid` → calls `embed()`, wraps each `list[float]` as `HybridEmbedding(dense=vec)` → returns `list[HybridEmbedding]`
- [ ] `_store_embeddings()` passes `HybridEmbedding` (or `list[float]` for backward compat) to `store_embedding()`
- [ ] `_process_results()` type annotation updated for `embed_result: list[HybridEmbedding] | list[list[float]] | BaseException`
- [ ] Entity embeddings: after extraction, embed entity descriptions via `embed_hybrid()` and store in vector store with `embedding_type="entity"` (add `_store_entity_embeddings()` helper called from `_process_results`)
- [ ] `pyproject.toml`: `knowledge = ["qdrant-client>=1.13", "FlagEmbedding>=1.3.5"]` (drop sqlite-vec, fastembed)
- [ ] All existing ingest tests updated and passing
- [ ] Ruff clean

## TDD — tests in `tests/test_ingest.py` (update existing)

- [ ] Pipeline with mock hybrid provider: `_run_embed` calls `embed_hybrid()`, returns `list[HybridEmbedding]`
- [ ] Pipeline with mock dense-only provider: `_run_embed` falls back to `embed()`, wraps in `HybridEmbedding`
- [ ] `_store_embeddings` passes `HybridEmbedding` to mock vector store
- [ ] Entity descriptions embedded and stored with `embedding_type="entity"`
- [ ] End-to-end ingest with mocked BgeM3 + QdrantVectorStore produces correct result

## Architecture Notes

- `IngestPipeline` stays in `ingest.py` — no file move
- The TYPE_CHECKING import of `VectorStore` becomes `VectorStoreProtocol`
- `embed_hybrid` duck typing avoids changing `EmbeddingProvider` protocol (backward compat with FastEmbedProvider until #251 removes it)
- Entity embedding is new behavior: currently only chunks are embedded. After extraction, each entity's description text needs embedding + vector storage for entity-level similarity search
