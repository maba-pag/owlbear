---
id: 247
title: Create VectorStoreProtocol
status: archived
priority: needed
created: 2026-02-28T12:38:43.4097674+01:00
updated: 2026-02-28T23:54:24.8584787+01:00
started: 2026-02-28T15:07:22.3600279+01:00
completed: 2026-02-28T23:54:24.8584787+01:00
tags:
    - phase-9
    - knowledge-graph
    - embedding
class: standard
---

## Context
Extract a Protocol class from current VectorStore API. Both sqlite-vec (current) and Qdrant (new) implement it. Clean swap point for the migration.

## Research Done
- docs/research/qdrant-local.md section 3.4 defines the migration steps
- docs/research/knowledge-pipeline.md confirms custom pipeline approach
- Current VectorStore API: store_embedding(), get_embedding(), search_similar(), delete_embedding()
- New protocol must also support hybrid embeddings (dense+sparse+ColBERT)

## Research Answers (Architect Decisions)

### Q1: Should the protocol expose hybrid search (prefetch+rescore) or unified search_similar()?
**Decision: Unified search_similar().** The protocol consumer should not care whether the backend uses
prefetch+rescore (Qdrant) or dense-only (sqlite-vec). The implementation decides the search strategy.
search_similar() takes a query embedding (which may be HybridEmbedding or list[float]) and returns
results. The HybridEmbedding input signals to the backend what vectors are available for search.
Fallback: if backend only supports dense and receives HybridEmbedding, it uses the .dense field.

### Q2: How do scope filtering and temporal boost map across backends?
**Decision: Protocol parameters, implementation-specific execution.**
- search_similar() accepts scopes: list[str] | None and recency_weight: float parameters
- sqlite-vec: post-filters via bridge table (current behavior)
- Qdrant: uses payload filters natively (more efficient)
- Temporal boost: sqlite-vec computes in Python (current), Qdrant can use payload scoring
- The protocol defines the interface; the optimization strategy is backend-specific

### Q3: HybridEmbedding data class design?
**Decision: Pydantic BaseModel with optional fields.**
- dense: list[float] (always present — backward compatible with existing list[float] usage)
- sparse: SparseVector | None = None (token_id->weight pairs, optional)
- colbert: list[list[float]] | None = None (multi-vector, optional)
- SparseVector: BaseModel with indices: list[int] and values: list[float]
- store_embedding() accepts list[float] | HybridEmbedding (backward compatible)
- For list[float] input, treated as dense-only (wraps in HybridEmbedding internally)

## Acceptance Criteria
- [ ] src/owlbear/memory/knowledge/protocol.py (new file)
- [ ] VectorStoreProtocol (Protocol, runtime_checkable) with 4 methods:
  - store_embedding(id: str, embedding: list[float] | HybridEmbedding, embedding_type: Literal['entity', 'document'], scope: str = 'global') -> None
  - get_embedding(id: str) -> list[float] | None
  - search_similar(query_embedding: list[float] | HybridEmbedding, top_k: int = 5, embedding_type: Literal['entity', 'document'] | None = None, *, scopes: list[str] | None = None, recency_weight: float = 0.0, decay_rate: float = 0.001) -> list[tuple[str, float]]
  - delete_embedding(id: str) -> bool
- [ ] SparseVector model: BaseModel with indices: list[int], values: list[float]
- [ ] HybridEmbedding model: BaseModel with dense: list[float], sparse: SparseVector | None = None, colbert: list[list[float]] | None = None
- [ ] Current VectorStore in vectors.py satisfies VectorStoreProtocol (isinstance check passes)
  - VectorStore only handles list[float] for now — HybridEmbedding support comes with QdrantVectorStore
  - store_embedding already accepts the right params; search_similar signature matches
- [ ] Type alias: Embedding = list[float] | HybridEmbedding for convenience
- [ ] Unit test: protocol shape (methods exist with correct signatures)
- [ ] Unit test: isinstance(VectorStore(conn), VectorStoreProtocol) passes
- [ ] Unit test: SparseVector and HybridEmbedding construction and serialization
- [ ] Unit test: HybridEmbedding.dense field is always present
- [ ] ~60 LOC for protocol.py, ~50 LOC for tests

## Architecture Notes
- Protocol is minimal — no reranker param in protocol (reranking is an implementation detail, not a protocol concern)
- get_embedding returns list[float] | None (not HybridEmbedding) — we only need to check existence, not reconstruct hybrid
- Current VectorStore satisfies protocol via duck typing (its store_embedding ignores HybridEmbedding — just takes list[float])
- Future QdrantVectorStore (#249) will fully leverage HybridEmbedding
- SparseVector matches Qdrant's models.SparseVector shape for easy conversion

## TDD
Tests included in AC. Test file: tests/test_vector_protocol.py

## Depends on
Nothing — first in knowledge chain. #248 and #249 depend on this.
