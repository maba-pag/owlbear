---
id: 151
title: 'Test: Vector store and embedding pipeline'
status: archived
priority: medium
created: 2026-03-29 19:13:47.482802+02:00
updated: 2026-03-30 17:08:09.887528+02:00
started: 2026-03-30 17:07:45.910311+02:00
completed: 2026-03-30 17:07:45.910311+02:00
tags:
- phase-1
- scope:knowledge
- test
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-30]] Mon 14:21
## Test-Writer Notes
- This task IS a test-writing task (tagged test). No separate TW pass needed — the task itself is TW output.
- Architect approved atomicity: "Both modules live in same package, single test task appropriate."
- Retroactively added by manual triage (2026-03-30) to unblock Gate 4.

[[2026-03-30]] Mon 14:37
## Builder Notes
- Test-writing task: deliverable is the test files themselves (source code already exists from #15).
- Files: packages/knowledge/tests/test_qdrant_vector_store.py, packages/knowledge/tests/test_embedding_provider.py
- Tests: 23 passed (15 qdrant + 8 embedding provider tests)
- Coverage: full AC coverage, all 16 AC lines exercised
- Lint: ruff clean
- Committed: 1dd9d42
- No source code changes needed (implementation was from #15)

[[2026-03-30]] Mon 15:12
## Review Evidence

### Test Results
- pytest 23 passed (14 qdrant + 9 embedding), 0 failed
- knowledge package full suite: 33 passed, 0 failed

### Lint Results
- ruff: All checks passed

### Pass 1 -- CRITICAL

#### AC Coverage (test-writing task -- test files are the deliverable)

All 16 AC lines COVERED:
- test_qdrant_vector_store.py: file exists, store_embedding dense+hybrid, get_embedding retrieve+None, search_similar top-k sorted+type-filter+scopes-filter, delete_embedding True+False, _ensure_collection lazy+idempotent, in-memory Qdrant verified, ImportError match='qdrant-client'
- test_embedding_provider.py: file exists, embed() list[list[float]]+empty=[], embed_hybrid() HybridEmbedding dense+sparse+colbert, lazy loading None+loaded, unload() _model None+timer None, ImportError match='FlagEmbedding', FlagEmbedding fully mocked, all imports from owlbear_knowledge

#### Security Review
No issues: no secrets, no subprocess, no path traversal, no deserialization, no new production deps

#### Test Quality
- Assertion specificity: ADEQUATE (strict is True/False for delete; match= for ImportError; exact ID match in search; dimension+type checks for retrieval)
- Negative paths: STRONG (missing ID, ImportError both modules, empty input embed/embed_hybrid)
- Mutation reasoning: ADEQUATE (sorted scores, type/scope filters, upsert-overwrites, lazy-init, timer-cancelled all change-sensitive)
- Test independence: STRONG (fresh fixture per test, no shared mutable state)
- Test names: STRONG

#### Data Safety
No issues -- mocks and in-memory storage only

### Verdict: PASS -- confidence .93

[[2026-03-30]] Mon 17:08
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c38c03b | chore | kanban/tasks/151-*.md | #151 |
