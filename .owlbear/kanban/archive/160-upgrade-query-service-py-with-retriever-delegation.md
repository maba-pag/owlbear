---
id: 160
title: Upgrade query_service.py with retriever delegation and hybrid search
status: archived
priority: medium
created: 2026-03-29 19:37:32.420323+02:00
updated: 2026-04-02 01:32:10.064747+02:00
started: 2026-04-02 01:31:59.793029+02:00
completed: 2026-04-02 01:31:59.793029+02:00
tags:
- phase-1
- scope:knowledge
- type:build
depends_on:
- 159
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Upgrade v2 query_service.py to wire _search_chunks() retriever delegation into both query paths, and add Qdrant hybrid search (dense+sparse prefetch with RRF fusion and score normalization).

## Acceptance Criteria
- [ ] `KnowledgeQueryService` adds `_search_chunks(prompt, top_k)` method: delegates to `self._retriever.retrieve(prompt, top_k, self._scopes)` when retriever is set, otherwise embeds and calls `self._vectors.search_similar()` directly
- [ ] `query()` uses `_search_chunks()` as its vector-search path (currently ignores retriever when set)
- [ ] `query_for_context()` uses `_search_chunks()` as its search path, replacing inline retriever call; `top_k` and `self._scopes` are forwarded to the retriever
- [ ] `QdrantVectorStore.search_similar()` dispatches to `_hybrid_search()` when `query_embedding` is `HybridEmbedding` with non-None `.sparse`; falls back to dense-only search when `.sparse is None` or input is plain `list[float]`
- [ ] `_hybrid_search()` uses two `Prefetch` entries (dense + sparse, each `limit=top_k * 10`) fused with `FusionQuery(fusion=Fusion.RRF)` and propagates `query_filter` (scopes + embedding_type conditions) to the fusion query
- [ ] Hybrid search scores are normalized to [0, 1] range before return so existing `similarity_threshold` filtering in `KnowledgeQueryService.query()` (default 0.3) remains functional; raw RRF scores (~0.01--0.03) must not pass through unnormalized

## Architecture Notes
- VectorStoreProtocol.search_similar interface unchanged (HybridEmbedding input already supported)
- Score normalization is the vector store layer's responsibility. Options: min-max normalization of RRF scores, or Qdrant `Fusion.DBSF` which produces distribution-normalized scores. Builder chooses.
- Behavioral change (intentional): when retriever is set, `query()` now gets hybrid-preferring embeddings from `GraphAugmentedRetriever._embed()` instead of dense-only from `self._embedder.embed()`. The retriever's embedding strategy is authoritative.
- Two `query_for_context` implementations exist (service method + standalone in retrieval.py). Only the service method is refactored here. Standalone function remains a direct retriever caller.

## Context
Split from #34 per docs/research/knowledge-package-integration-hybrid-search.md. Depends on #159 (delivered under #205, archived). Research: docs/research/upgrade-query-service-hybrid-search.md

[[2026-04-01]] Wed 07:52
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- not research-driven (T1 autonomous: fills existing gap with proven v1 patterns)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| _search_chunks delegation | Gap confirmed: query() ignores retriever | Refined: explicit method signature, both callers |
| query() uses _search_chunks | Gap confirmed: direct embed+search only | Refined: documented behavioral change |
| query_for_context() uses _search_chunks | Partial: delegates retriever but not top_k/scopes | Refined: top_k and scopes forwarding explicit |
| hybrid search dispatch in search_similar | Main gap: dense-only extraction from HybridEmbedding | Kept: Prefetch+RRF pattern from v1 benchmark |
| _hybrid_search with Prefetch+RRF | Not implemented | Refined: filter propagation required (challenger C2) |
| Score normalization | MISSING from original AC | ADDED: challenger C1 identified critical gap (RRF ~0.01-0.03 vs threshold 0.3) |

### Architecture Notes
Changes touch two files in owlbear_knowledge package:
- qdrant.py: add _hybrid_search()/_dense_search() dispatch, score normalization
- query_service.py: add _search_chunks() delegation used by both query() and query_for_context()

VectorStoreProtocol unchanged. Module layering correct (service calls store).
Dependency #159 archived (delivered under #205). No dependency cycles.

Challenger identified critical gap: RRF fusion scores (~0.01-0.03) would be universally rejected by similarity_threshold=0.3. Added AC6 requiring score normalization at vector store layer. Builder may use min-max or Qdrant DBSF.

### Changes Made
- Rewrote body with refined AC (6 lines, all verifiable pass/fail)
- Removed redundant AC1 (query_for_context already exists)
- Removed AC6 (unit tests -- handled by TDD pipeline)
- Added score normalization AC (from challenger C1)
- Added filter propagation requirement (from challenger C2)
- Documented intentional behavioral changes in Architecture Notes

### Dependencies
- Verified: #159 archived (delivered under #205)
- No new dependencies needed

### Challenge Results
- Challenger: reconsider
- Confidence in original: .55
- Key challenges: (C1) RRF score semantics break similarity_threshold -- ACCEPTED, added AC; (C2) query_filter not propagated to hybrid Prefetch -- ACCEPTED, added to AC; (C3) query() embedding strategy changes with retriever -- ACCEPTED, documented as intentional; (C4) top_k/scopes forwarded to retriever -- ACCEPTED, explicit in AC
- Architect response: revised AC to address C1 and C2; documented C3 and C4 as intentional improvements

[[2026-04-01]] Wed 14:32
## Test-Writer Notes
- Test files: tests/test_query_service_160.py, tests/test_qdrant_hybrid_160.py
- Classes: TestFromAC_SearchChunksDelegation, TestFromAC_QueryUsesSearchChunks, TestFromAC_QueryForContextUsesSearchChunks, TestFromAC_HybridSearchDispatch, TestFromAC_HybridSearchInternals, TestFromAC_HybridScoreNormalization
- Tests per category: happy 15, edge 5, error 2, boundary 2
- Total: 24 tests, all FAIL
- ruff: clean
- AC coverage:
  AC1 _search_chunks method: test_search_chunks_method_exists, _no_retriever_calls_embed, _no_retriever_calls_vector_store, _no_retriever_returns_id_score_pairs, _with_retriever_calls_retrieve, _with_retriever_forwards_prompt, _forwards_top_k, _forwards_scopes, _none_scopes, _does_not_call_embed, _returns_retrieval_chunks (11 tests)
  AC2 query() uses _search_chunks: test_query_with_retriever_calls_retrieve_not_embed, _does_not_call_embedder_embed, _forwards_top_k_to_retrieve (3 tests)
  AC3 query_for_context forwards args: test_query_for_context_forwards_top_k_to_retriever, _forwards_scopes_to_retriever (2 tests)
  AC4 dispatch to hybrid: test_hybrid_sparse_input_uses_fusion_query (1 test)
  AC5 Prefetch+RRF+filter: test_hybrid_search_uses_exactly_two_prefetch_entries, _prefetch_limit_equals_top_k_times_ten, _uses_rrf_fusion, _query_filter_includes_scope, _query_filter_includes_embedding_type (5 tests)
  AC6 score normalization: test_hybrid_scores_max_above_similarity_threshold, _top_score_normalized_near_one (2 tests)

-t

[[2026-04-01]] Wed 18:04
## Review Evidence

### Test Results
- pytest tests/test_query_service_160.py tests/test_qdrant_hybrid_160.py: 27 passed, 0 failed
- pytest packages/knowledge/tests/test_qdrant_vector_store.py tasks/test_qdrant_hybrid_160.py: 22 passed (full qdrant suite)

### Lint Results
- ruff check packages/knowledge/src/owlbear_knowledge/qdrant.py packages/knowledge/src/owlbear_knowledge/query_service.py tests/test_query_service_160.py tests/test_qdrant_hybrid_160.py: All checks passed!

### Coverage (touched modules, combined with task #151 qdrant suite)
- qdrant.py: 94% (lines 14-16 import fallback, 51 URL path, 128 edge -- acceptable)
- query_service.py: 73% (lines 156-173: query_for_context document-formatting path untested)

### TestFromAC Integrity Check
Builder only added TestBuilderDiscovered (3 tests). No TestFromAC_* class modified. PRESERVED.

### AC4 Test-Writer Coverage Audit
AC4 states two behaviors: (1) dispatch to hybrid when HybridEmbedding.sparse is non-None; (2) falls back to dense-only when .sparse is None OR plain list[float].

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 _search_chunks delegation | 11 TestFromAC_SearchChunksDelegation tests | Yes -- both retriever and direct paths | COVERED |
| AC2 query() uses _search_chunks | 3 tests: retrieve called, embed NOT called, top_k forwarded | Yes | COVERED |
| AC3 query_for_context forwards top_k + scopes | 2 tests: top_k forwarded, scopes forwarded | Yes | COVERED |
| AC4(a) dispatch to hybrid when sparse non-None | test_hybrid_sparse_input_uses_fusion_query | Yes | COVERED |
| AC4(b) fallback to dense when HybridEmbedding.sparse is None | None | -- | **MISSING** |
| AC5 2x Prefetch, Fusion.RRF, filter propagation | 5 tests | Yes | COVERED |
| AC6 score normalization above threshold | 2 tests | Yes | COVERED |

AC4(b): The test-writer wrote 1 test for AC4 covering only the hybrid dispatch. The second half of AC4 (HybridEmbedding with sparse=None goes to dense path) has NO TestFromAC test. The plain list[float] dense path is covered by existing #151 tests (incidental), but HybridEmbedding+sparse=None is untested. No compensating TestBuilderDiscovered test exists for this path.

### Implementation-Aware Gap (Step 6.5)
query_service.py lines 156-173: query_for_context document-formatting loop is untested. When chunks are non-empty and documents are resolvable, the output format ("Relevant knowledge:\\n\\n- title: content") and max_tokens truncation are never exercised. Builder did not add TestBuilderDiscovered tests for this path.

### Security
No issues found. No hardcoded secrets, no injection, no path traversal, no unsafe deserialization.

### Builder Process Quality
CLEAN -- single commit d9082b2, no retries.

### Docstring Issue (informational)
query_service.py line 50: KnowledgeQueryService docstring says retriever is "Unused -- kept for API compatibility" -- now stale since the builder wired it into _search_chunks.

### AC Compliance Table
| AC | Evidence | Status |
|----|----------|--------|
| AC1 _search_chunks delegation | 11 TestFromAC tests pass; implementation delegates when self._retriever is not None | PASS |
| AC2 query() uses _search_chunks | 3 tests confirm retriever called, embed not called, top_k forwarded | PASS |
| AC3 query_for_context forwards top_k+scopes | 2 tests confirm forwarding; _search_chunks call visible in implementation | PASS |
| AC4 hybrid dispatch + dense fallback | hybrid path tested; HybridEmbedding+sparse=None fallback has no test | **FAIL** |
| AC5 Prefetch+RRF+filter | 5 tests confirm 2 Prefetch entries, Fusion.RRF, scope+embedding_type in query_filter | PASS |
| AC6 score normalization | 2 tests: max(scores)>0.3 and top score>0.9 confirmed | PASS |

### Verdict: FAIL -- confidence .85
AC4 has a MISSING TestFromAC test for the HybridEmbedding+sparse=None dense-only fallback path. No compensating TestBuilderDiscovered test exists. Test-writer must add test_dense_fallback_when_sparse_none (returns dense-path result, does NOT call _hybrid_search) and builder must add TestBuilderDiscovered test for query_for_context formatting output when chunks are non-empty.

[[2026-04-01]] Wed 18:04
## Review Evidence

### Test Results
- pytest tests/test_query_service_160.py tests/test_qdrant_hybrid_160.py: 27 passed, 0 failed
- pytest packages/knowledge/tests/test_qdrant_vector_store.py + test_qdrant_hybrid_160.py: 22 passed

### Lint Results
- ruff on touched files: All checks passed!

### Coverage (combined with task #151 qdrant suite)
- qdrant.py: 94% (lines 14-16 import fallback, 51 URL path, 128 edge -- acceptable)
- query_service.py: 73% (lines 156-173: query_for_context formatting path untested)

### TestFromAC Integrity
Builder only added TestBuilderDiscovered (3 tests). No TestFromAC_* class modified. PRESERVED.

### AC4 Test-Writer Coverage Audit
AC4 states two behaviors: (1) dispatch to hybrid when sparse non-None; (2) fall back to dense when sparse is None OR plain list[float].

AC4(b) -- HybridEmbedding with sparse=None uses dense path -- has NO TestFromAC test. The plain list[float] path is covered by #151 tests (incidental). No compensating TestBuilderDiscovered test exists for sparse=None case. MISSING per skill criteria.

### Implementation-Aware Gap (Step 6.5)
query_service.py lines 156-173: query_for_context document-formatting loop is untested. When chunks are non-empty and documents resolvable, the output format and max_tokens truncation are never exercised.

### Security
No issues. No hardcoded secrets, injection, path traversal, or unsafe deserialization.

### Builder Process Quality: CLEAN
Single commit d9082b2, no retries.

### Informational: Stale docstring
query_service.py line 50: retriever docstring says 'Unused' -- now stale since builder wired it into _search_chunks.

### AC Compliance
AC1: 11 tests pass, delegation impl confirmed -- PASS
AC2: 3 tests confirm retriever called, embed not called, top_k forwarded -- PASS
AC3: 2 tests confirm forwarding; _search_chunks call visible in impl -- PASS
AC4 hybrid dispatch: test_hybrid_sparse_input_uses_fusion_query passes -- PASS
AC4 dense fallback (sparse=None): No TestFromAC test exists -- FAIL
AC5: 5 tests confirm 2 Prefetch entries, Fusion.RRF, query_filter propagation -- PASS
AC6: 2 normalization tests confirm max>0.3 and top>0.9 -- PASS

### Verdict: FAIL -- confidence .85
AC4 has a MISSING TestFromAC test for HybridEmbedding+sparse=None dense-only fallback. No compensating TestBuilderDiscovered test exists. Test-writer must add test covering this path; builder must add TestBuilderDiscovered for query_for_context formatting output.

## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL cited MISSING test for AC4(b) -- HybridEmbedding+sparse=None dense path not covered
- Added: 1 new test `test_dense_fallback_when_hybrid_sparse_none` in `TestFromAC_HybridSearchDispatch`
- Preserved: 8 existing tests (all PASS) from prior cycle
- Total: 9 tests in test_qdrant_hybrid_160.py + 19 in test_query_service_160.py = 28 tests
- ruff: clean
- Note: implementation already correctly handles AC4(b); test adds contract verification
- Commit: 807289a (test: add AC4(b) dense fallback test for HybridEmbedding+sparse=None)

[[2026-04-01]] Wed 23:23
## Builder Notes (retry)\n- Files changed: tests/test_query_service_160.py, query_service.py\n- Added TestBuilderDiscovered: test_query_for_context_formats_output_correctly, test_query_for_context_truncates_output_to_max_tokens, test_query_for_context_returns_none_when_all_docs_unresolvable, test_query_returns_empty_list_when_retriever_returns_no_chunks\n- Fixed stale docstring: retriever param now says 'Optional retriever for graph-augmented retrieval'\n- Tests: 32 passed, query_service.py coverage 91%\n- Lint: ruff clean\n- Commit: 1897265\n- AC4(b) test added by test-writer: test_dense_fallback_when_hybrid_sparse_none passes\n- Reviewer gaps from first cycle fully addressed

[[2026-04-02]] Thu 01:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 _search_chunks delegation | query_service.py L68, delegates to retriever or embeds directly. 11 tests pass | PASS |
| AC2 query() uses _search_chunks | query_service.py L100 calls _search_chunks. 3 tests pass | PASS |
| AC3 query_for_context uses _search_chunks | query_service.py L153 calls _search_chunks, top_k+scopes forwarded. 2 tests pass | PASS |
| AC4 hybrid dispatch + dense fallback | qdrant.py L161 dispatches hybrid when sparse non-None; L163-177 dense fallback. Both paths tested | PASS |
| AC5 Prefetch+RRF+filter | qdrant.py L189-210: 2 Prefetch entries, Fusion.RRF, query_filter propagated. 5 tests pass | PASS |
| AC6 score normalization | qdrant.py L214-221: min-max to [0,1]. 2 tests pass | PASS |

### Test Results
- Task tests: 32 passed, 0 failed
- Full suite: 2682 passed, 302 failed (all from unrelated RED-phase tasks: #524, rename_todo, hooks, voice, infrastructure)
- Ruff: clean on all touched files

### Architect Quality
- AC Quality Score: 4/5 (adequate, one minor gap: AC4 merged two testable behaviors into one line, caught by reviewer)
- Challenger integration: good -- C1 (score normalization) and C2 (filter propagation) correctly added to AC

### Commits (upstream, verified)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| bced3b2 | test | test_query_service_160.py, test_qdrant_hybrid_160.py | #160 |
| d9082b2 | feat | qdrant.py, query_service.py | #160 |
| 807289a | test | test_qdrant_hybrid_160.py | #160 |
| 1897265 | feat | test_query_service_160.py, query_service.py | #160 |

### Deduction breakdown: no deductions -- all AC lines have evidence, lint clean, full-suite failures outside task scope, reviewer evidence present, AC quality 4/5
### Confidence: .98
### Action: archive
