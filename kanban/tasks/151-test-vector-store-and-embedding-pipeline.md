---
id: 151
title: 'Test: Vector store and embedding pipeline'
status: in-progress
priority: needed
created: 2026-03-29T19:13:47.4828015+02:00
updated: 2026-03-29T20:35:25.0071639+02:00
tags:
    - phase-1
    - scope:knowledge
    - test
class: standard
---

## Objective

Write tests for QdrantVectorStore and BgeM3EmbeddingProvider modules in packages/knowledge/.

## Acceptance Criteria

- [ ] Test file packages/knowledge/tests/test_qdrant_vector_store.py created
- [ ] Tests for store_embedding: dense vector, HybridEmbedding (dense + sparse)
- [ ] Tests for get_embedding: retrieves stored vector, returns None for missing ID
- [ ] Tests for search_similar: top-k results sorted by score, embedding_type filter, scopes filter
- [ ] Tests for delete_embedding: returns True for existing, False for missing
- [ ] Tests for _ensure_collection: collection created lazily on first op, idempotent on repeat
- [ ] All QdrantVectorStore tests use in-memory Qdrant (no Docker, no filesystem)
- [ ] Test file packages/knowledge/tests/test_embedding_provider.py created
- [ ] Tests for embed(): returns list[list[float]], empty input returns empty list
- [ ] Tests for embed_hybrid(): returns list[HybridEmbedding] with dense, sparse, colbert fields
- [ ] Tests for lazy loading: _model is None before first call, loaded after
- [ ] Tests for unload(): _model set to None, timer cancelled
- [ ] Tests for ImportError: QdrantVectorStore and BgeM3EmbeddingProvider raise ImportError with actionable message when optional deps missing
- [ ] BGE-M3 model calls mocked via unittest.mock (no 3GB download in CI)
- [ ] All tests import from owlbear_knowledge package
- [ ] ruff clean on test files

## Context

TDD pair for #32 (vector store + embedding pipeline). Code already extracted under #15; tests verify the extraction is correct and catch edge-case gaps.

[[2026-03-29]] Sun 19:55
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| test_qdrant_vector_store.py created | File existence check | Keep |
| store_embedding: dense, HybridEmbedding | Maps to qdrant.py L85-115 two paths | Keep |
| get_embedding: retrieve, None for missing | Maps to qdrant.py L117-133 | Keep |
| search_similar: top-k, embedding_type, scopes | Maps to qdrant.py L135-177 filter logic | Keep |
| delete_embedding: True/False | Maps to qdrant.py L179-196 | Keep |
| _ensure_collection: lazy, idempotent | Maps to qdrant.py L60-76, _initialized flag | Keep |
| In-memory Qdrant (no Docker) | :memory: constructor, matches existing test pattern | Keep |
| test_embedding_provider.py created | File existence check | Keep |
| embed(): list[list[float]], empty=[] | Maps to embeddings.py L92-101 | Keep |
| embed_hybrid(): HybridEmbedding fields | Maps to embeddings.py L103-123 | Keep |
| Lazy loading: _model None/loaded | Maps to embeddings.py L52-74 | Keep |
| unload(): _model None, timer cancelled | Maps to embeddings.py L125-132 | Keep |
| ImportError with actionable message | Both modules use try/ImportError pattern | Keep |
| BGE-M3 mocked (no 3GB download) | Correct constraint for CI | Keep |
| Import from owlbear_knowledge package | Matches existing test convention | Keep |
| ruff clean | Standard gate | Keep |

### Architecture Notes
All 16 AC lines are precise, testable, and map 1:1 to actual method signatures in qdrant.py and embeddings.py. Both modules live in the same package (owlbear_knowledge) and share protocol.py, making a single test task appropriate. Existing test pattern in test_graph_store_counts.py (pytest fixtures, in-memory backends, class-based grouping) provides the template. No layering concerns (tests only).

### Dependencies
- Verified: #32 depends_on #151 (correct TDD ordering)
- No missing dependencies

### Changes Made
- Approved task, moved to todo
