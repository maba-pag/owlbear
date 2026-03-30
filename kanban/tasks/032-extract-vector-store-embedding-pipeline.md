---
id: 32
title: Extract vector store + embedding pipeline
status: todo
priority: needed
created: 2026-03-26T18:33:43.753881+01:00
updated: 2026-03-30T07:58:47.0011686+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 15
    - 151
class: standard
---

## Objective

Verify and finalize the vector store (Qdrant) and embedding pipeline (BGE-M3) extraction into packages/knowledge/, which was completed ahead-of-schedule during #15.

## Acceptance Criteria

- [ ] `qdrant.py` exists with `QdrantVectorStore` class implementing `VectorStoreProtocol`
- [ ] `QdrantVectorStore.__init__` accepts `:memory:`, filesystem path, and HTTP/HTTPS URL
- [ ] `embeddings.py` exists with `BgeM3EmbeddingProvider` class implementing `EmbeddingProvider` protocol
- [ ] `BgeM3EmbeddingProvider` has lazy loading (model loaded on first `embed()` call) and idle unload (configurable `idle_timeout`)
- [ ] Zero PydanticAI or daemon imports in qdrant.py and embeddings.py (verified by grep)
- [ ] `qdrant-client>=1.9.0` in `[project.optional-dependencies].qdrant`; `FlagEmbedding>=1.2.0` in `[project.optional-dependencies].embedding`
- [ ] `protocol.py` defines `VectorStoreProtocol`, `HybridEmbedding`, `SparseVector`, `Embedding` alias shared with graph store
- [ ] All tests from preceding test task pass; ruff clean

## Context

Depends on #15 (graph store foundation, archived). Extraction was completed ahead-of-schedule under #15. Builder work is verification plus any fixes found by tests.
Subtask 2/4 of knowledge engine extraction. v1 modules: qdrant.py, embeddings.py.

## Research
Doc: docs/research/extract-vector-store-embedding-pipeline.md

[[2026-03-29]] Sun 19:15
## Architecture Review
**Verdict:** REFINE

### AC Assessment
- Extract qdrant.py: Verified (196 LOC, implements VectorStoreProtocol). Kept, tightened.
- Extract embeddings.py: Verified (131 LOC, implements EmbeddingProvider). Kept, tightened.
- Remove PydanticAI/daemon imports: Verified zero hits. Kept.
- Qdrant local file-based mode: Verified (path= constructor, line 54). Kept.
- BGE-M3 cache documentation: Research correctly defers to #34 README AC. Removed from #32.
- Add sentence-transformers to deps: INACCURATE. Code uses FlagEmbedding. pyproject.toml already correct. Fixed.
- Unit tests: ZERO test files for qdrant.py or embeddings.py in entire repo. Created test task #151.
- Integration with graph store: Verified (shared protocol.py). Kept.

### Architecture Notes
Module layering is clean. No upward deps. Optional-dep pattern (try/ImportError) matches convention. recency_weight/decay_rate are intentional no-ops per VectorStoreProtocol contract, deferred to #34. Research doc missed zero-test-coverage gap.

### Changes Made
- Rewrote AC: 8 precise lines replacing 8 vague originals
- Fixed dependency name: sentence-transformers to FlagEmbedding
- Removed BGE-M3 cache doc AC (deferred to #34)
- Created #151 (Test: Vector store and embedding pipeline) at backlog
- Added depends_on #151 to #32

### Dependencies
- Verified: #15 (archived)
- Added: #151 (preceding test task)
- Downstream: #33, #34 depend on #32

[[2026-03-30]] Mon 07:58
## Architecture Review (2nd pass)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| qdrant.py with QdrantVectorStore implementing VectorStoreProtocol | Verified: 195 LOC, duck-type Protocol match confirmed | Keep |
| __init__ accepts :memory:, path, HTTP/HTTPS | Verified: lines 51-55, three-branch constructor | Keep |
| embeddings.py with BgeM3EmbeddingProvider implementing EmbeddingProvider | Verified: 126 LOC, duck-type Protocol match | Keep |
| Lazy loading + idle unload (configurable idle_timeout) | Verified: _ensure_model() lazy, 600s timer with threading.Timer | Keep |
| Zero PydanticAI/daemon imports | Verified: grep returns zero matches in both files | Keep |
| qdrant-client>=1.9.0 in qdrant; FlagEmbedding>=1.2.0 in embedding | Verified: pyproject.toml lines 11-12 match exactly | Keep |
| protocol.py defines VectorStoreProtocol, HybridEmbedding, SparseVector, Embedding | Verified: all 4 types present in protocol.py (78 LOC) | Keep |
| All tests pass; ruff clean | Builder gate condition, verifiable | Keep |

### Architecture Notes
All 8 AC lines are precise and map directly to existing code. Module layering is clean: qdrant.py and embeddings.py import only from protocol.py (same package) and optional external deps (qdrant_client, FlagEmbedding) behind try/ImportError guards. No upward imports. recency_weight/decay_rate are intentional no-ops (ARG002) deferred to #34 per research doc. Code was extracted ahead-of-schedule under #15; builder work is verification plus any fixes surfaced by #151 tests.

### Dependencies
- Verified: #15 (archived, done)
- Verified: #151 (TDD pair, in-progress, depends_on enforces sequencing)
- Downstream: #33, #34 depend on #32

### Changes Made
- Approved task, moved to todo
