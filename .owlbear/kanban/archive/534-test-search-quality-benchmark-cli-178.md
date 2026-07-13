---
id: 534
title: 'Test: search quality benchmark CLI (#178)'
status: archived
priority: medium
created: 2026-04-02 01:43:22.634970+02:00
updated: 2026-04-02 04:31:25.664120+02:00
started: 2026-04-02 04:31:25.108111+02:00
completed: 2026-04-02 04:31:25.108111+02:00
tags:
- phase-2
- scope:knowledge
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
TDD RED phase tests for the search quality benchmark CLI (packages/knowledge/src/owlbear_knowledge/benchmark.py).

## Acceptance Criteria
- [ ] Test file: tests/test_kb_benchmark_178.py
- [ ] Tests use a mock object satisfying the `embed_hybrid()` interface (returns deterministic HybridEmbedding with both dense and sparse components). Do NOT mock via the EmbeddingProvider protocol (it lacks `embed_hybrid`); mock the concrete BgeM3EmbeddingProvider or an equivalent duck-typed object.
- [ ] test_benchmark_cli_accepts_db_path_arg: CLI parses --db-path correctly
- [ ] test_benchmark_prints_stats_output: get_stats() document/entity/edge counts appear in stdout
- [ ] test_benchmark_defines_five_sample_queries: module has SAMPLE_QUERIES constant with exactly 5 entries
- [ ] test_benchmark_runs_hybrid_and_dense_comparison: each query searched in both modes
- [ ] test_benchmark_prints_per_query_comparison: hybrid vs dense top-3 doc IDs printed
- [ ] test_benchmark_prints_summary_line: "Hybrid differs from dense-only on N/5 queries" in output
- [ ] test_benchmark_asserts_document_count_fails_on_empty_db: exit 1 when doc_count < 500
- [ ] test_benchmark_asserts_query_returns_results: exit 1 when any query returns 0 results
- [ ] test_benchmark_asserts_ranking_difference_fails_when_insufficient: exit 1 when fewer than 3/5 queries show different hybrid vs dense-only top-3 rankings
- [ ] test_benchmark_exit_0_when_all_pass: returns 0 when all assertions met (mocks must produce differing rankings for >= 3/5 queries to exercise the full happy path)
- [ ] All tests FAIL (RED phase)
- [ ] ruff clean

## Context
Test task for #178 (search quality benchmark CLI). See #178 AC for full specification.

### Mock design notes
- `BgeM3EmbeddingProvider.embed_hybrid()` returns `list[HybridEmbedding]` with dense, sparse, and colbert fields (see packages/knowledge/src/owlbear_knowledge/embeddings.py:92).
- `HybridEmbedding(dense=vec, sparse=None)` triggers the dense-only fallback path in `QdrantVectorStore.search_similar()` (see packages/knowledge/src/owlbear_knowledge/qdrant.py:160-165).
- To produce different rankings between hybrid and dense, mock data must yield distinct sparse weights that alter the RRF fusion order. See test_embedding_provider.py for existing mock patterns.
- `GraphStore.get_counts()` at graph_store.py:440 returns `(doc_count, entity_count, edge_count)` — the benchmark's get_stats output should use this.

[[2026-04-02]] Thu 02:25
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- test task derived from #178 architect review (T1 autonomous)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Test file location | Follows convention (test_kb_loader_176.py) | Keep |
| Mock EmbeddingProvider | Protocol lacks embed_hybrid() | Refined: specify embed_hybrid() mock |
| 9 named test functions | All verifiable with specific behaviors | Keep |
| Missing ranking-diff failure test | Parent #178 has 3 assertions, only 2 covered | Added: test_benchmark_asserts_ranking_difference_fails_when_insufficient |
| Happy-path exit 0 | Did not require differing rankings | Refined: mock must produce >= 3/5 different rankings |
| All tests FAIL (RED) | Standard TDD gate | Keep |
| ruff clean | Standard quality gate | Keep |

### Architecture Notes
All infrastructure exists: GraphStore.get_counts() at graph_store.py:440, QdrantVectorStore dense fallback at qdrant.py:160-165, BgeM3EmbeddingProvider.embed_hybrid() at embeddings.py:92. Test follows root-level test_kb_* naming convention. Mock design notes added to guide test-writer on hybrid-vs-dense differentiation.

### Changes Made
- Refined AC line 2: mock specification changed from EmbeddingProvider protocol to embed_hybrid() interface
- Added AC line: test_benchmark_asserts_ranking_difference_fails_when_insufficient (covers 3rd parent assertion)
- Refined happy-path AC: mock data must produce differing rankings
- Added Mock design notes section with pointers to relevant code

### Dependencies
- Verified: no depends_on needed (standalone test task)
- Parent #178 depends_on includes #534

### Challenge Results
- Challenger: reconsider (confidence 0.68)
- Key challenges: (C1) missing ranking-diff failure test, (C2) EmbeddingProvider protocol mismatch
- Architect response: accepted C1 and C2; rebutted C3 (diagnostic output is test design detail) and C4 (minor mock concern). Refined AC accordingly.

[[2026-04-02]] Thu 03:05
## Test-Writer Notes
- Test file: tests/test_kb_benchmark_178.py
- Classes: TestFromAC_BenchmarkCLI
- Tests per category: happy 6, edge 0, error 3, boundary 2
- Total: 11 tests, all FAIL
- ruff: clean
- AC coverage: all 10 named AC tests covered + boundary test for doc_count=499
- Mock patches: GraphStore, QdrantVectorStore, BgeM3EmbeddingProvider at owlbear_knowledge.benchmark.*
- Alternating side_effect in exit-0 test produces 5/5 differing rankings (satisfies >=3/5)
- Commit: 4232a8e

## Builder Notes
- Files: packages/knowledge/src/owlbear_knowledge/benchmark.py (new, 97 lines)
- Tests: 11 passed, coverage 98% on benchmark.py
- Lint: ruff clean
- Commit: c65c9b1

[[2026-04-02]] Thu 04:08
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal benchmark CLI; no behavior/API/convention change affecting agents |
| 2 | Docstrings | Yes | Pass | benchmark.py: module docstring present with usage; main() has Args + Returns; no other public symbols |
| 3 | docs/sources/overview.md | No | N/A | Builder notes cite no external patterns; implementation uses stdlib argparse + project-internal modules only |
| 4 | README.md | No | N/A | benchmark.py is a developer diagnostic tool (requires 500+ indexed docs); not a user-facing command |
| 5 | Research doc | No | N/A | type:test task; no research phase |
| 6 | Scratch files | No | Pass | No docs/scratch/534-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None
