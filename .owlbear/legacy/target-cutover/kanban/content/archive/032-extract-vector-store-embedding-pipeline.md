---
id: 32
title: Extract vector store + embedding pipeline
status: archived
priority: medium
created: 2026-03-26 18:33:43.753881+01:00
updated: 2026-03-30 20:26:32.096869+02:00
started: 2026-03-30 20:25:18.650288+02:00
completed: 2026-03-30 20:25:18.650288+02:00
tags:
- phase-1
- scope:knowledge
- type:build
depends_on:
- 15
- 151
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-30]] Mon 17:40
## Test-Writer Notes\n- Test file: tests/test_knowledge_vector_pipeline_32.py\n- Classes: TestFromAC_ProtocolDefinitions, TestFromAC_QdrantProtocolConformance, TestFromAC_QdrantInitModes, TestFromAC_BgeM3ProtocolConformance, TestFromAC_BgeM3IdleTimeout, TestFromAC_NoPydanticAiImports, TestFromAC_OptionalDependencies\n- Tests per category: happy 10, edge 6, error 4, boundary 8\n- Total: 28 tests, all PASS (implementation pre-existing from #15)\n- ruff: clean\n- Note: TDD pair #151 (archived) covers detailed unit tests. This file covers AC lines unique to #32: AC1 protocol isinstance, AC2 init routing modes, AC3 EmbeddingProvider isinstance, AC4 configurable idle_timeout + timer fires, AC5 zero pydantic_ai/daemon imports AST scan, AC6 pyproject.toml dep versions, AC7 protocol.py type exports.\n- Committed: 00bf6bd

[[2026-03-30]] Mon 17:48
## Builder Notes
- Files changed: None (implementation pre-existing from #15; test file committed by test-writer at 00bf6bd)
- Tests: 28 passed (test_knowledge_vector_pipeline_32.py); 61 passed including #151 package tests
- Coverage: qdrant.py 95%, embeddings.py 99%, protocol.py 100% (all well above 90%)
- Lint: ruff clean (packages/knowledge/src/ + test file)
- Evidence: 28 passed in 1.40s; ruff: All checks passed!
- Fixes applied: None required

[[2026-03-30]] Mon 19:15
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Existing 'Knowledge engine (graph + vector)' entry accurate; no convention change |
| 2 | Docstrings complete | Yes | Pass | qdrant.py: module, QdrantVectorStore, 5 public methods. embeddings.py: EmbeddingProvider, BgeM3EmbeddingProvider, embed/embed_hybrid/unload. protocol.py: all 4 types + VectorStoreProtocol |
| 3 | docs/sources/overview.md | Yes | Pass | Task 32 section present: Qdrant client, BGE-M3 model card, Qdrant quickstart attributed |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research doc linked | Yes | Pass | docs/research/extract-vector-store-embedding-pipeline.md exists, linked in task; follow-ups created |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 20:25
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| qdrant.py with QdrantVectorStore implementing VectorStoreProtocol | qdrant.py L29, 195 LOC, all 4 protocol methods present | PASS |
| __init__ accepts :memory:, path, HTTP/HTTPS | qdrant.py L53-56, three-branch constructor | PASS |
| embeddings.py with BgeM3EmbeddingProvider implementing EmbeddingProvider | embeddings.py L25, EmbeddingProvider protocol L16 runtime_checkable | PASS |
| Lazy loading + idle unload (configurable idle_timeout) | _ensure_model() L47 lazy load; _reset_timer() L79 with configurable idle_timeout | PASS |
| Zero PydanticAI/daemon imports | grep zero matches; only hit is _timer.daemon attribute (threading, not import) | PASS |
| qdrant-client>=1.9.0 in qdrant; FlagEmbedding>=1.2.0 in embedding | pyproject.toml L10-11 exact match | PASS |
| protocol.py defines VectorStoreProtocol, HybridEmbedding, SparseVector, Embedding | protocol.py: VectorStoreProtocol L56, HybridEmbedding L38, SparseVector L15, Embedding L52 | PASS |
| All tests pass; ruff clean | 159 passed, 9 unrelated failures (agent tools tests), ruff All checks passed | PASS |

### Test Results
- pytest: 159 passed, 9 failed (all in test_agent_port_v2.py, unrelated agent tools tests), 5 collection errors (unrelated modules)
- ruff: All checks passed (knowledge src + test file)

### AC Quality Score: 5
Precise, complete, verifiable. No builder improvisation needed.

### Deduction breakdown
-.02 missing Review Evidence section in task body (reviewer did not write structured evidence)

### Confidence: .98
### Action: archive

[[2026-03-30]] Mon 20:26
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| eaf0182 | chore | kanban/tasks/032-*.md | #32 |
