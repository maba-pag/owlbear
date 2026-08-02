---
id: 1329
title: 'P2-13: Tests — Phase 2 + stats tools (get_consolidation_candidates, get_stats)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.133593+00:00
updated: 2026-05-07T12:32:47.394593+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1328
blocked: false
block_reason: 'Double crash: test-writer agent returned no response twice (cycle 39).
  Likely transient infrastructure issue.'
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] Tests verify get_consolidation_candidates(ctx, limit=20): deterministic SQL (ORDER BY entity_name) finding entity names in 2+ sources (td:2)
- [ ] Tests verify candidates exclude entries with existing cross-source edges or reviewed_pairs rows (td:2)
- [ ] Tests verify candidates return list of dicts (`isinstance(item, dict)` assertion required) with keys `entity_name`, `candidate_id`, `source_a_chunk`, `source_b_chunk`; exact chunk content asserted against known fixture values per returned field — not via string serialization or duck-typing helpers (td:2)
- [ ] Tests verify store_enrichment Phase 2 mode (ctx, candidate_id, edges=[...]): writes cross-source edges when edges non-empty; assert the exact persisted edge row content — source_id, target_id, and relation fields in the edges table must match the caller-supplied values (td:2)
- [ ] Tests verify store_enrichment Phase 2 mode with empty edges=[] marks pair in reviewed_pairs (dismissal); assert the exact reviewed_pairs row written has entity_name, source_a, source_b values matching the candidate decoded from candidate_id (td:2)
- [ ] Tests verify new sources generate new candidate pairs; old dismissals in reviewed_pairs preserved (td:2)
- [ ] Tests verify get_stats returns additive result: preserves existing {documents, entities, edges} AND adds total_sources, total_chunks, chunks_enriched_ratio, consolidation_candidates_remaining (td:2)

## Scope

- **In scope:** Phase 2 consolidation tool tests, get_stats expansion tests
- **Out of scope:** Phase 1 tools (P2-11/12), agent enricher loop, existing get_stats durable suite compatibility (existing package-local tests cover legacy fields), output-schema metadata (owned by #541)

## Notes for builder

- Import `get_consolidation_candidates` from `owlbear_mcp_knowledge.server` (ImportError RED until #1330)
- Phase 2 `store_enrichment` has different signature than Phase 1 per Brief §4.4 line 97: `store_enrichment(candidate_id, edges=[...])` — test the Phase 2 entry point separately
- `get_stats` expansion: current impl uses `graph_store.get_counts()` for legacy fields; new fields (sources, chunks, enrichment ratio, candidates) are SQL-based via `conn`. Tests must mock/provide both
- Follow fixture patterns from `tests/test_mcp_knowledge_enrichment_tools_1327.py` (in-memory SQLite + init_db + MagicMock MCP ctx)
- `reviewed_pairs` table PK: `(entity_name, source_a, source_b)` — already in schema.py
- **AC3 proof requirement (cycle 2):** Tests MUST include `assert isinstance(candidate, dict)` — the existing `_get_field`/`_has_field` helpers allow objects too, which weakens the dict-shape contract
- **AC4 proof requirement (cycle 2):** After calling store_enrichment with edges, query the edges table and assert the row's source_id, target_id, and relation match the input values — row count alone is insufficient
- **AC5 proof requirement (cycle 2):** After calling store_enrichment with edges=[], query reviewed_pairs and assert the row's entity_name, source_a, source_b match the candidate's decoded fields — row count alone is insufficient

[[2026-05-05]]
## Research
- Research doc: .owlbear/research/phase2-consolidation-tests-1329.md
- Sources: 6 studied, 4 high-relevance (all internal codebase)
- Recommendation: Single test file following #1327 patterns — import get_consolidation_candidates (ImportError RED), test expanded get_stats fields, test store_enrichment Phase 2 dismissal mode (confidence: 0.88)
- Follow-up tasks created: none needed — #1330 is the builder task
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial test-structure research with no design trade-offs
- Confidence in original: 0.88
- Key findings: schema ready (reviewed_pairs, enrichment_state exist), get_stats needs expansion from 3 fields to include sources/chunks/enrichment-ratio/candidates-remaining, get_consolidation_candidates has no implementation yet (clean RED)
[[2026-05-06]]
## Architecture Review (cycle 1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for Phase 2 consolidation + stats expansion |
| Interface clarity | PASS (after refine) | Refined AC to pin Phase 2 store_enrichment signature, get_stats additive contract, deterministic ORDER BY |
| Dependency correctness | PASS | #1328 archived (Phase 1 tools complete); reviewed_pairs schema exists |
| Module layering | PASS | Tests import from owlbear_mcp_knowledge.server; no upward imports |
| TDD compliance | PASS | This IS the test task; #1330 builder depends on it |
| KISS/YAGNI | PASS | Scoped to Brief §4.4 spec; no extras |
| Premise challenge | PASS | get_consolidation_candidates doesn't exist (clean RED); get_stats expansion is brief-mandated |
| Pattern consistency | PASS | Follows #1327 test patterns: in-memory SQLite, init_db, MagicMock MCP ctx |
| Security surface | PASS | Test-only task; no new system boundaries |
| Single domain | PASS | All in knowledge/mcp-knowledge domain |

### Challenge Results
- Challenger: reconsider (confidence 0.67)
- Concerns: (1) Phase 2 store_enrichment signature ambiguity, (2) get_stats additive vs. replacement unclear, (3) dual data source for get_stats not noted
- Architect response: ACCEPTED — refined all 3 concerns into AC. AC4/5 now pin `(candidate_id, edges=[...])` signature. AC7 now explicitly states additive semantics. Builder notes explain dual data source (graph_store + conn).

### Test Depth
- Max depth: td:2
- Test-writer: SKIP (task tagged `test` — pass-through)

### Verdict: APPROVE (with AC refinement)
### Action Taken: Refined AC to resolve challenger concerns (signature, additive semantics, dual data source). Added builder notes section. Advanced to todo.
[[2026-05-06]]
## Test-Writer Notes

- **File:** `tests/test_mcp_knowledge_phase2_tools_1329.py`
- **Classes:** `TestFromAC_GetConsolidationCandidates`, `TestFromAC_StoreEnrichmentPhase2`, `TestFromAC_GetStatsExpansion`
- **Total tests:** 21 — all FAIL (RED confirmed via ImportError: `get_consolidation_candidates` not yet in `owlbear_mcp_knowledge.server`)
- **Lint:** ruff clean (0 violations)

| Category | Count |
|----------|-------|
| Happy path | 8 |
| Edge / error | 6 |
| Boundary | 7 |

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 (td:2): get_consolidation_candidates deterministic SQL, 2+ sources | 4 tests |
| AC2 (td:2): excludes cross-source edges + reviewed_pairs | 3 tests |
| AC3 (td:1): returns dicts with entity_name + chunks | 2 tests |
| AC4 (td:1): Phase 2 non-empty edges writes edge | 1 test |
| AC5 (td:1): Phase 2 empty edges dismissal → reviewed_pairs | 2 tests |
| AC6 (td:2): new source generates new pair; old dismissal preserved | 3 tests |
| AC7 (td:2): get_stats additive fields | 6 tests |

### RED Failure Details
- Module-level `from owlbear_mcp_knowledge.server import get_consolidation_candidates` → `ImportError` blocks collection
- Phase 2 `store_enrichment(ctx, candidate_id=..., edges=[...])` call → `TypeError` once import resolves
- `get_stats` assertions on `total_sources`, `total_chunks`, `chunks_enriched_ratio`, `consolidation_candidates_remaining` → `KeyError` once import resolves

### Builder Notes
- `get_consolidation_candidates(ctx, limit=20)` must return list of dicts with keys: `entity_name`, `candidate_id` (used by Phase 2 `store_enrichment`)
- Phase 2 `store_enrichment(ctx, candidate_id=..., edges=[...])` — separate from Phase 1 `(ctx, chunk_id, entities, edges)` signature
- `get_stats` must call both `graph_store.get_counts()` (legacy) and SQL queries on `conn` (new fields)
- `chunks_enriched_ratio` must return `0.0` (not error) when no chunks exist
[[2026-05-07]]
## Builder Notes
- Implementation: serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
- Added Phase 2 candidate discovery API: `get_consolidation_candidates(ctx, limit=20)` with deterministic ordering and pair-level exclusions for existing edges and reviewed dismissals.
- Extended `store_enrichment` to dual-mode behavior:
  - Phase 1 preserved: `(chunk_id, entities, edges)` updates entities/edges and marks chunk enriched.
  - Phase 2 added: `(candidate_id, edges)` inserts edges when non-empty, or records dismissal in `reviewed_pairs` when empty.
- Expanded `get_stats` additively: keeps `{documents, entities, edges}` and adds `{total_sources, total_chunks, chunks_enriched_ratio, consolidation_candidates_remaining}`.
- Added candidate-id encode/decode helpers and normalized reviewed-pair matching to handle both source orderings.

- Tests: 54 passed, 0 failed
  - `tests/test_mcp_knowledge_phase2_tools_1329.py`
  - `tests/test_mcp_knowledge_enrichment_tools_1327.py`
- Lint: ruff clean on changed source + scoped tests
- Coverage evidence (quality-runner scoped report): `owlbear_mcp_knowledge.server` at 43%
- Commit: `4ba08abc feat: implement phase-2 consolidation tools (#1329, builder)`

### Evidence Summary
- RED verified first: collection ImportError for missing `get_consolidation_candidates` in task test file.
- Initial GREEN attempt surfaced 4 failing assertions around reviewed-pair exclusion semantics.
- Applied focused fix: symmetric reviewed-pair filter and lint cleanup constant.
- Re-verify passed for task and neighboring enrichment suite, confirming Phase 2 additions without Phase 1 regression.

### Post-task Reflection
- Problem faced: reviewed-pair entries were inserted in source creation order, while candidate query canonicalized pair order; direct equality check missed dismissals.
- Workaround applied: match reviewed pairs symmetrically `(a,b)` OR `(b,a)` in SQL filter.
- Pattern discovered: dual-mode function extension is safest here because existing Phase 1 tests and callers remain unchanged while enabling Phase 2 signature.
- Quality gap: module-level coverage remains low due large legacy server module; task-scoped behavior is covered but overall module baseline is still below phase gate target.
[[2026-05-07]]
## Review Evidence (cycle 1)
### Test Results
- quality-runner scoped pass: 107 passed, 0 failed, 0 skipped
- Suites run: tests/test_mcp_knowledge_phase2_tools_1329.py, tests/test_mcp_knowledge_enrichment_tools_1327.py, serve/mcp-knowledge/tests/test_ingest_graph_tools.py

### Lint Results
- ruff clean on serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and the scoped test files

### Coverage
- quality-runner reported owlbear_mcp_knowledge.server at 55% module coverage
- This reject is not based on the module-level percentage. The failing criteria are task-owned AC proof gaps in the TestFromAC suite.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: deterministic SQL / 2+ sources | tests passed | PASS |
| AC2: excludes existing cross-source edges and reviewed_pairs rows | tests passed | PASS |
| AC3: returns entity_name plus relevant chunks from both sources inline | tests never assert items are dicts | FAIL |
| AC4: Phase 2 non-empty edges writes cross-source edge | test only proves count +1 | PASS (smoke) |
| AC5: Phase 2 empty edges marks reviewed_pairs dismissal | test only proves count +1 | PASS (smoke) |
| AC6: new sources generate new candidate pairs; old dismissals preserved | tests prove structured fields | PASS |
| AC7: additive get_stats result | fields directly checked | PASS |

### Verdict: FAIL → todo (test proof gaps in AC3, AC6, AC7)

## Test-Writer Notes (retry)
- Retry: 3 new exact-assertion tests added for reviewer gaps; all pass against current impl → direct-to-review advance.
- New tests: test_candidate_chunk_payloads_are_exact_source_content (AC3), test_exact_candidate_pairs_after_dismissal_and_new_source (AC6), test_stats_consolidation_candidates_remaining_exact_count (AC7)
- Total tests: 29 passed, 0 failed, ruff clean
- Commit: 9891cbd1 test: strengthen AC3/AC6/AC7 proof tests for phase-2 consolidation (#1329, test-writer)

## Builder Notes (cycle 2)
- No source changes required — current implementation satisfies strengthened assertions.
- Tests: 29 passed, 0 failed
- Commit: none in this cycle

## Review Evidence (cycle 2)
### Test Results
- Task-scoped: 29 passed, 0 failed, 0 skipped
- Broader regression: 141 passed, 4 failed (all in test_outputschema_541.py — outside task scope)

### AC Compliance (cycle 2)
| AC Line | Status | Gap |
|---|---|---|
| AC1 | PASS | — |
| AC2 | PASS | — |
| AC3 | FAIL | Tests still use duck-typing helper, never assert isinstance(dict) |
| AC4 | FAIL | Row-count-only assertion, no exact-row content check |
| AC5 | FAIL | Row-count-only assertion, no exact-row content check |
| AC6 | PASS | Retry test proves exact pairs |
| AC7 | PASS | Retry test proves exact count |

### Verdict: FAIL → backlog (second cycle, AC3/4/5 still under-proven)
### Required Follow-up: architect refine AC3/4/5 proof contracts; output-schema regression as separate task

[[2026-05-07]]
## Architecture Review (cycle 2)

Tightened AC3/4/5 from td:1 smoke proofs to td:2 exact-row assertions:
- AC3: Must assert `isinstance(candidate, dict)` and exact field values — duck-typing helpers insufficient
- AC4: Must assert exact persisted edge row content (source_id, target_id, relation) — not count-only
- AC5: Must assert exact reviewed_pairs row (entity_name, source_a, source_b) decoded from candidate_id — not count-only

Output-schema regression (test_outputschema_541.py) scoped out as separate follow-up — not owned by this task's AC.

Challenger: SKIPPED (mechanical refinement, no design trade-offs).
Verdict: APPROVE → todo.
[[2026-05-07]]
## Test-Writer Notes (retry cycle 2)

- **File:** `tests/test_mcp_knowledge_phase2_tools_1329.py`
- **New class:** `TestFromAC_ExactProofs` — 3 tests for AC3/AC4/AC5 cycle-2 proof gaps
- **Total tests now:** 32 passed, 0 failed — ruff clean
- **Commit:** `1b6cf0d0 test: add exact-proof tests for AC3/AC4/AC5 dict shape and row content (#1329, test-writer)`

### Retry Gaps Addressed

| AC | Gap (cycle 2 reviewer) | New Test | Result |
|----|------------------------|----------|--------|
| AC3 | No `isinstance(candidate, dict)` assertion — duck-typing helpers pass objects | `test_ac3_candidates_are_dicts_not_objects` | PASS (impl already returns dicts) |
| AC4 | Count-only assertion; no exact edge row content check | `test_ac4_exact_edge_row_content_after_phase2_store` | PASS (impl writes correct source_id/target_id/relation) |
| AC5 | Count-only assertion; no exact reviewed_pairs row content check | `test_ac5_exact_reviewed_pairs_row_content_after_dismissal` | PASS (impl writes correct entity_name/source_a/source_b) |

### Step 1b.1 — Direct-to-Review Advance

All 3 new tests PASS against current implementation. Reviewer gaps were proof-only (no implementation fixes needed). Advancing directly to `review` — builder has no work to do.
[[2026-05-07]]
## Builder Notes
- Code changes: none in this cycle (implementation already present and compatible with latest AC3/AC4/AC5 proof tests).
- Scoped verification run (quality-runner evidence):
  - `tests/test_mcp_knowledge_phase2_tools_1329.py`: 30 passed
  - `tests/test_mcp_knowledge_enrichment_tools_1327.py`: 30 passed
  - Total scoped: 60 passed, 0 failed, 0 skipped
- Lint status:
  - `ruff check serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_mcp_knowledge_phase2_tools_1329.py` => clean (0 violations)
- Regression context (non-blocking for this task): broader `serve/mcp-knowledge/tests/` slice reported 156 passed / 5 failed, with failures in pre-existing unrelated output-schema/skill-doc tests outside task 1329 AC ownership.
- Evidence summary: AC-targeted tests and adjacent enrichment regression pass; no task-owned failures detected; no implementation delta required.
- Coverage: not collected in this verification run.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 113 passed, 0 failed, 0 skipped
- Suites run: tests/test_mcp_knowledge_phase2_tools_1329.py, tests/test_mcp_knowledge_enrichment_tools_1327.py, serve/mcp-knowledge/tests/test_ingest_graph_tools.py

### Lint Results
- ruff clean on serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_mcp_knowledge_phase2_tools_1329.py

### Coverage
- quality-runner reported owlbear_mcp_knowledge.server at 55% module coverage
- This reject is not based on the module-level percentage. The blocking issues are AC-owned proof gaps in the TestFromAC suite.

### SCM / Scope Notes
- Commit presence confirmed via `.git/logs/**`: 4ba08abc (builder), 1b6cf0d0 (test-writer)
- Direct `git diff` / `git status` evidence was not available in this tool surface, so exact changed-file reconstruction and dirty-tree contamination checks could not be independently completed. Small confidence deduction applied.
- Loop-breaker applies: prior review failures already recorded in this task (`## Review Evidence (cycle 1)` and `## Review Evidence (cycle 2)`).

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: deterministic SQL / 2+ sources | Implementation orders by entity_name in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:256`; discriminating tests at `tests/test_mcp_knowledge_phase2_tools_1329.py:235`, `:253`, `:279`, `:299`; quality-runner green | PASS |
| AC2: excludes reviewed_pairs and existing cross-source edges | Forward-order exclusion is tested at `tests/test_mcp_knowledge_phase2_tools_1329.py:340`, but the implementation has a separate reversed-order reviewed_pairs branch at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:251-252` with no targeted test coverage | FAIL |
| AC3: list of dicts with exact per-field chunk content | Dict shape is asserted at `tests/test_mcp_knowledge_phase2_tools_1329.py:1004`, but the chunk proof still accepts unordered field placement at `tests/test_mcp_knowledge_phase2_tools_1329.py:485` and `:489`; a `source_a_chunk`/`source_b_chunk` swap would stay green | FAIL |
| AC4: Phase 2 non-empty edges persist exact row content | Implementation writes `source_id`, `target_id`, `relation` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:463-465`; exact-row test asserts those columns at `tests/test_mcp_knowledge_phase2_tools_1329.py:1043`, `:1051`, `:1052`, `:1053` | PASS |
| AC5: Phase 2 empty edges persist exact reviewed_pairs row content | Implementation decodes ordered values then inserts `(entity_name, source_a, source_b)` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:448` and `:476`; the cycle-2 proof test collapses `source_a`/`source_b` to a set at `tests/test_mcp_knowledge_phase2_tools_1329.py:1090` and only checks unordered equality at `:1092`, so swapped columns would stay green | FAIL |
| AC6: new sources create new pairs; old dismissals preserved | Exact structured pair-set proof at `tests/test_mcp_knowledge_phase2_tools_1329.py:733`, `:739`, `:746`; preservation proof at `:662`; quality-runner green | PASS |
| AC7: additive get_stats result | New fields produced in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:950-958`; exact value tests at `tests/test_mcp_knowledge_phase2_tools_1329.py:763`, `:775`, `:785`, `:795`, `:814`, `:835`, `:952`, `:971`; adjacent durable get_stats suite also green | PASS |

### Deductions
- -0.08 AC3 proof remains lax: unordered chunk-field assertions do not prove per-field exactness
- -0.08 AC5 proof remains lax: unordered reviewed_pairs source assertions do not prove exact column values
- -0.05 AC2 reverse-order reviewed_pairs exclusion branch is untested
- -0.04 Test quality remains WEAK for assertion specificity / mutation resistance on AC3 and AC5
- -0.03 SCM diff/status unavailable in this session; commit presence only confirmed via git logs

### Verdict
- FAIL -> backlog | confidence 0.70
- Reason: third review cycle still has td:2 proof gaps in AC2/AC3/AC5. The implementation appears stable, but the TestFromAC suite still allows false-green outcomes on ordered field/column swaps, and loop-breaker routing now applies.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC2/AC3/AC5 proof contract to require ordered field equality for `source_a_chunk`/`source_b_chunk` and `reviewed_pairs.source_a`/`source_b`, plus explicit coverage of reversed reviewed_pairs ordering | tests/test_mcp_knowledge_phase2_tools_1329.py; serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py; .owlbear/kanban/tasks/1329-p2-13-tests-phase-2-stats-tools-get-consolidation-candidates-get-stats.md | AC5 proof requirement already demands exact row values at task line 50; remaining false-green assertions at tests lines 485, 489, 1090, 1092; untested reverse-order SQL branch at server lines 251-252 |
| 2 | architect | Re-scope or replace the legacy stringification-style AC3 smoke proof so the task’s acceptance mapping no longer counts non-discriminating assertions toward td:2 coverage | tests/test_mcp_knowledge_phase2_tools_1329.py | stringification-based AC3 smoke path at tests lines 447-454 plus code-reader test-quality finding |

### Action
- Rejected to `backlog` under the reviewer loop-breaker rule. Implementation changes are not the blocker; the acceptance proof contract is still structurally too weak for a PASS gate.

[[2026-05-07]]
## Architecture Review (cycle 3)

### Context
Third review cycle returned to backlog under loop-breaker rule. Implementation is stable — the blocking issue is test proof specificity. Three false-green paths remain where unordered assertions pass despite potential column/field swaps.

### AC Refinement — Proof Contracts

**AC2 refinement (reversed reviewed_pairs coverage):**
Original: "Tests verify candidates exclude entries with existing cross-source edges or reviewed_pairs rows"
Added constraint: Tests MUST include a case where `reviewed_pairs` was inserted with source columns in reversed order relative to the candidate query's canonical order (i.e. `_insert_reviewed_pair(source_a=B, source_b=A)` where candidate would list them as `(A, B)`). This exercises the `OR (rp.source_a = pc.source_b AND rp.source_b = pc.source_a)` SQL branch.

**AC3 refinement (positional chunk assertion):**
Original: "exact chunk content asserted against known fixture values per returned field"
Added constraint: Tests MUST use positional equality assertions — `assert candidate['source_a_chunk'] == <known_a_content>` and `assert candidate['source_b_chunk'] == <known_b_content>` — where `<known_a_content>` is the fixture text inserted for source_a and `<known_b_content>` for source_b. Set/frozenset/unordered-collection comparison of chunk fields is PROHIBITED. The `_get_field` duck-typing helper is PROHIBITED for this AC (use direct dict indexing).

**AC5 refinement (positional column assertion):**
Original: "assert the exact reviewed_pairs row written has entity_name, source_a, source_b values matching the candidate decoded from candidate_id"
Added constraint: Tests MUST assert positional column equality — `assert row['source_a'] == decoded_source_a` AND `assert row['source_b'] == decoded_source_b` — where decoded values come from `json.loads(candidate_id)`. Set/unordered comparison of source_a/source_b columns is PROHIBITED. The implementation's `_decode_candidate_id` returns `(entity_name, source_a, source_b)` in insertion order; tests must prove that exact column mapping.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only proof tightening |
| Interface clarity | PASS (after refine) | Three proof contracts now mechanically unambiguous |
| Dependency correctness | PASS | #1328 done; implementation complete |
| Module layering | PASS | No change |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Minimum change — only close false-green paths |
| Premise challenge | PASS | Reviewer evidence confirms the gaps exist at specific test lines |
| Pattern consistency | PASS | Same fixture pattern as existing tests |
| Security surface | PASS | Test-only |
| Single domain | PASS | knowledge domain |

### Challenge Results
- Challenger: SKIPPED — mechanical proof refinement, no design trade-offs

### Test Depth
- Max depth: td:2
- Test-writer: SKIP (task tagged `test` — pass-through)

### Verdict: APPROVE (with AC refinement)
### Action Taken: Tightened AC2/AC3/AC5 proof contracts to require positional equality and prohibit set/unordered comparisons. Added reversed-order reviewed_pairs test requirement for AC2. Advanced to todo.

[[2026-05-07]]
Cycle 3 architecture review: refined AC2/AC3/AC5 proof contracts to close false-green paths. No design changes — implementation is stable. Positional equality mandated, set/unordered comparisons prohibited for chunk fields and reviewed_pairs columns. Reversed-order reviewed_pairs exclusion test now required for AC2.
[[2026-05-07]]
## Test-Writer Notes (retry cycle 3)

- **File:** `tests/test_mcp_knowledge_phase2_tools_1329.py`
- **New class:** `TestFromAC_Cycle3Proofs` — 3 tests for AC2/AC3/AC5 cycle-3 proof gaps
- **Total tests now:** 35 in task file, 63 total scoped — all PASS, ruff clean
- **Commit:** `783eeec5 test: add cycle-3 exact-proof tests for AC2/AC3/AC5 positional assertions (#1329, test-writer)`

### Retry Gaps Addressed

| AC | Gap (cycle 3 reviewer) | New Test | Result |
|----|------------------------|----------|--------|
| AC2 | No test with reversed source order in reviewed_pairs — OR SQL branch untested | `test_ac2_reversed_reviewed_pair_still_excludes_candidate` | PASS (impl has symmetric OR clause) |
| AC3 | Set/frozenset chunk comparison allows field swaps; `_get_field` helper prohibited | `test_ac3_source_a_chunk_and_source_b_chunk_match_positionally` | PASS (impl assigns chunks by min/max source_id) |
| AC5 | Set comparison of source_a/source_b columns allows swap; no json.loads decode | `test_ac5_reviewed_pairs_columns_match_candidate_id_decoded_positionally` | PASS (impl writes decoded values positionally) |

### Step 1b.1 — Direct-to-Review Advance

All 3 new tests PASS against current implementation. Reviewer gaps were proof-only (no implementation fixes needed). Advancing directly to `review` — builder has no work to do.
[[2026-05-07]]
## Builder Notes
- Code changes: none in this cycle (implementation already present and compatible with cycle-3 AC2/AC3/AC5 proof refinements).
- Verification run (quality-runner scoped):
  - `tests/test_mcp_knowledge_phase2_tools_1329.py`
  - `tests/test_mcp_knowledge_enrichment_tools_1327.py`
  - `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
  - Result: 116 passed, 0 failed, 0 skipped
- Lint status:
  - `ruff check serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_mcp_knowledge_phase2_tools_1329.py` => clean (0 violations)
- Coverage (scoped report):
  - `owlbear_mcp_knowledge.server`: 55%
- Evidence summary:
  - Latest test-writer cycle-3 proofs (AC2 reversed reviewed_pairs, AC3 positional chunk assertions, AC5 positional reviewed_pairs column assertions) remain green against current implementation.
  - No source delta required for this builder pass.

### Post-task Reflection
- Problem faced: builder cycle was re-entered after test-only proof tightening where implementation was already stable.
- Workaround applied: treated this as a verification-only builder pass and produced fresh quality-runner evidence instead of introducing unnecessary code churn.
- Pattern discovered: when reviewer gaps are proof-specific and test-writer lands discriminating tests, builder value is validation, not modification.
- Time sink: repeated cycle routing on a test-owned task can consume builder slots without changing implementation.
- Quality gap: module-level coverage for `owlbear_mcp_knowledge.server` remains below phase target despite task-scoped AC coverage being green.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 116 passed, 0 failed, 0 skipped
- Suites run: `tests/test_mcp_knowledge_phase2_tools_1329.py`, `tests/test_mcp_knowledge_enrichment_tools_1327.py`, `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
- code-reader audit completed; current cycle-3 proofs close the prior AC3/AC4/AC5 positional gaps

### Lint Results
- ruff clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and `tests/test_mcp_knowledge_phase2_tools_1329.py`

### Coverage
- quality-runner: `owlbear_mcp_knowledge.server` at 54.8% module coverage
- This reject is not based on the module percentage. The blocker is a task-owned AC proof gap in the TestFromAC suite.

### SCM / Scope Notes
- Commit presence confirmed via `.git/logs/**`: `4ba08abc` (builder), `1b6cf0d0` and `783eeec5` (test-writer retries)
- Direct `git diff` / `git status` evidence was not available in this tool surface, so exact changed-file diff reconstruction and dirty-tree contamination checks could not be independently completed. Small confidence deduction applied.
- Prior review failures already exist in this task (`## Review Evidence (cycle 1)`, `## Review Evidence (cycle 2)`, and the later loop-breaker reject), so any new FAIL routes to `backlog`.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: deterministic SQL / 2+ sources | `get_consolidation_candidates` orders by entity name at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:256`; proving tests at `tests/test_mcp_knowledge_phase2_tools_1329.py:235` and `:253`; scoped quality run green | PASS |
| AC2: excludes existing cross-source edges and reviewed_pairs rows | Edge exclusion SQL explicitly handles both directions at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:233-234`. Current suite proves forward-edge exclusion at `tests/test_mcp_knowledge_phase2_tools_1329.py:318` with the only inserted edge at `:329`, and proves reversed `reviewed_pairs` ordering separately at `:1109`. No scoped test proves the reverse edge-direction branch, so removing `server.py:234` would likely stay green. | FAIL |
| AC3: returns dicts with exact per-field chunk content | Direct dict-type assertion at `tests/test_mcp_knowledge_phase2_tools_1329.py:1004`; positional chunk equality proof at `:1146` | PASS |
| AC4: Phase 2 non-empty edges persist exact row content | Phase-2 edge write path in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:453-465`; exact persisted-row proof at `tests/test_mcp_knowledge_phase2_tools_1329.py:1010` | PASS |
| AC5: Phase 2 empty edges persist exact reviewed_pairs row content | Reviewed-pair insert at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:476`; exact row and positional decoded-column proofs at `tests/test_mcp_knowledge_phase2_tools_1329.py:1056` and `:1198` | PASS |
| AC6: new sources create new pairs; old dismissals preserved | Preservation proof at `tests/test_mcp_knowledge_phase2_tools_1329.py:637`; exact surviving pair-set proof at `:706` and `:746` | PASS |
| AC7: additive get_stats result | Additive return fields in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:963-969`; preserving/expanded field proofs at `tests/test_mcp_knowledge_phase2_tools_1329.py:763`, `:795`, `:814`, `:835`, `:952` | PASS |

### Deductions
- -0.07 AC2 proof gap: reverse edge-direction exclusion path at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:234` remains untested
- -0.02 TestFromAC immutability was checked from live file bodies, but not backed by a direct diff in this tool surface
- -0.01 Direct git diff/status scope checks were unavailable here

### Verdict
- FAIL -> backlog | confidence 0.88
- Reason: cycle-3 fixes close the earlier AC3/AC4/AC5 false-green paths, but AC2 still lacks a discriminating test for the reverse edge-direction exclusion branch. That is a task-owned proof gap, and loop-breaker routing now applies.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC2 so the TestFromAC suite must prove both cross-source edge directions, then return to test-writer for a reverse-edge exclusion test that would fail if `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:234` were removed | `tests/test_mcp_knowledge_phase2_tools_1329.py`; `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`; `.owlbear/kanban/tasks/1329-p2-13-tests-phase-2-stats-tools-get-consolidation-candidates-get-stats.md` | Edge exclusion SQL has two branches at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:233-234`; current edge proof only inserts the forward direction at `tests/test_mcp_knowledge_phase2_tools_1329.py:329` under `test_entity_with_cross_source_edge_excluded_from_candidates` at `:318`; no reverse-edge proof exists in the scoped suites |

### Action
- Rejected to `backlog` under the reviewer loop-breaker rule. Current implementation appears stable, but the review gate is still blocked by AC2 proof insufficiency.
[[2026-05-07]]

## Architecture Review (cycle 4)

### AC Refinement — AC2 Reverse Edge Direction

**AC2 added constraint:** Tests MUST include a case where the cross-source edge is inserted in the reverse direction relative to the candidate pair's entity ordering (i.e. `_insert_edge(source_entity_id=entity_b_id, target_entity_id=entity_a_id)` where entity_a appears first in the candidate query's join). This exercises the `OR (ed.source_id = e2.id AND ed.target_id = e1.id)` SQL branch. Removing `server.py:234` must cause this test to fail.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single proof gap closure |
| Interface clarity | PASS (after refine) | AC2 now mechanically unambiguous for both edge directions |
| Dependency correctness | PASS | #1328 done; implementation stable since cycle 1 |
| Module layering | PASS | No change |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | One test addition — minimum to close the gap |
| Premise challenge | PASS | Reviewer evidence at server.py:233-234 and test line 329 confirms gap |
| Pattern consistency | PASS | Same _insert_edge fixture pattern already used |
| Security surface | PASS | Test-only |
| Single domain | PASS | knowledge domain |

### Challenge Results
- Challenger: SKIPPED — mechanical single-test proof closure, no design trade-offs

### Test Depth
- Max depth: td:2
- Test-writer: SKIP (task tagged `test` — pass-through)

### Verdict: APPROVE (with AC2 refinement)
### Action Taken: Added reverse-edge-direction test requirement to AC2. This is the final proof gap — cycle-3 closed AC3/AC5 positional assertions and AC2 reversed reviewed_pairs; only the reverse edge direction remains. Advanced to todo.

[[2026-05-07]]
Cycle 4 architecture review: refined AC2 to require reverse-edge-direction test proving the OR branch at server.py:234. All other AC lines (AC1, AC3-AC7) have adequate proofs from prior cycles. Minimal remaining work: one new test inserting edge in reverse entity order.
[[2026-05-07]]
## Test-Writer Notes (retry cycle 4)

- **File:** `tests/test_mcp_knowledge_phase2_tools_1329.py`
- **New class:** `TestFromAC_Cycle4Proofs` — 1 test for AC2 cycle-4 proof gap
- **Total tests now:** 36 passed, 0 failed — ruff clean
- **Commit:** `c61b2907 test: add cycle-4 reverse-edge-direction proof for AC2 (#1329, test-writer)`

### Retry Gap Addressed

| AC | Gap (cycle 4 reviewer) | New Test | Result |
|----|------------------------|----------|--------|
| AC2 | No test for reverse edge direction (e2→e1); OR branch at server.py:234 untested | `test_ac2_reversed_edge_direction_still_excludes_candidate` | PASS (impl has symmetric OR clause) |

### Test Mechanics
- Two entities inserted in different sources; their IDs compared to determine e1 (smaller) and e2 (larger) per the SQL join condition `e1.id < e2.id`
- Only the reverse-direction edge `(e2_id → e1_id)` inserted — the forward branch is NOT exercised
- Removing server.py:234 would expose the candidate again, causing this test to fail

### Step 1b.1 — Direct-to-Review Advance

New test PASS against current implementation. Reviewer gap was proof-only (no implementation fix needed). Advancing directly to `review` — builder has no work to do.
[[2026-05-07]]
## Builder Notes
- Code changes: none in this cycle (implementation already satisfies cycle-4 AC2 reverse-edge-direction proof test).
- Verification run (quality-runner scoped):
  - tests/test_mcp_knowledge_phase2_tools_1329.py
  - tests/test_mcp_knowledge_enrichment_tools_1327.py
  - serve/mcp-knowledge/tests/test_ingest_graph_tools.py
  - Result: 117 passed, 0 failed, 0 skipped
- Lint status:
  - ruff check serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_mcp_knowledge_phase2_tools_1329.py => clean (0 violations)
- Coverage (scoped report):
  - owlbear_mcp_knowledge.server: 55%
- Evidence summary:
  - Latest cycle-4 test (`test_ac2_reversed_edge_direction_still_excludes_candidate`) is green against the existing implementation.
  - No implementation delta required for this builder pass.

### Post-task Reflection
- Problem faced: builder re-entry after test-only proof closure can tempt unnecessary code churn.
- Workaround applied: performed verification-only builder pass with fresh quality-runner evidence.
- Pattern discovered: when reviewer gaps are proof-specific and implementation is already green, builder value is confirmation and clean handoff.
- Quality gap: module-level coverage remains below phase target on a large legacy module despite AC-focused suite being green.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 117 passed, 0 failed, 0 skipped
- Suites run: `tests/test_mcp_knowledge_phase2_tools_1329.py`, `tests/test_mcp_knowledge_enrichment_tools_1327.py`, `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
- code-reader audit completed; live file reads matched the reported phase-2 validation gap

### Lint Results
- ruff clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and the scoped test files
- VS Code diagnostics: no errors in `server.py`, `tests/test_mcp_knowledge_phase2_tools_1329.py`, `tests/test_mcp_knowledge_enrichment_tools_1327.py`, or `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`

### Coverage
- quality-runner reported `owlbear_mcp_knowledge.server` at 55% module coverage
- This reject is not based on module-level percentage. The blocker is a phase-2 integrity/validation gap on the task-owned MCP write path.

### SCM / Scope Notes
- Commit presence confirmed via `.git/logs/**`: `4ba08abc` (builder), `1b6cf0d0`, `783eeec5`, `c61b2907` (test-writer retries)
- Direct `git diff` / `git status` evidence was not available in this tool surface, so exact dirty-tree and diff reconstruction could not be independently completed. Small confidence deduction applied.
- Prior review failures already exist in this task (`## Review Evidence (cycle 1)`, `## Review Evidence (cycle 2)`, and later loop-breaker rejects). Any new FAIL routes to `backlog`.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 deterministic query / ordering / 2+ sources | `test_entity_in_two_sources_appears_as_candidate`, `test_candidates_ordered_alphabetically_by_entity_name`, `test_limit_caps_number_of_candidates`, `test_entity_in_single_source_excluded_from_candidates` | Yes | COVERED |
| AC2 excludes reviewed pairs and existing cross-source edges in both directions | `test_entity_with_cross_source_edge_excluded_from_candidates`, `test_entity_with_reviewed_pairs_entry_excluded_from_candidates`, `test_ac2_reversed_reviewed_pair_still_excludes_candidate`, `test_ac2_reversed_edge_direction_still_excludes_candidate` | Yes | COVERED |
| AC3 dict shape + exact chunk fields | `test_ac3_candidates_are_dicts_not_objects`, `test_ac3_source_a_chunk_and_source_b_chunk_match_positionally`, downstream `candidate_id` use in AC4/AC5 exact proofs | Mostly yes | COVERED |
| AC4 phase-2 non-empty edges write the reviewed cross-source edge | `test_phase2_non_empty_edges_writes_edge_to_db`, `test_ac4_exact_edge_row_content_after_phase2_store` | No. These tests prove exact persistence of caller-supplied row values, but they do not prove the row is coherent with the reviewed `candidate_id` / source-pair contract imported from the parent brief. | LAX |
| AC5 dismissal writes exact reviewed_pairs row decoded from `candidate_id` | `test_phase2_empty_edges_inserts_reviewed_pair_dismissal`, `test_phase2_empty_edges_does_not_write_new_edges`, `test_ac5_reviewed_pairs_columns_match_candidate_id_decoded_positionally` | Yes | COVERED |
| AC6 new sources create new pairs while old dismissals persist | `test_new_source_generates_new_candidate_pair_for_same_entity`, `test_old_dismissal_preserved_in_reviewed_pairs_after_new_source`, `test_dismissed_pair_remains_excluded_after_new_source_added`, `test_exact_candidate_pairs_after_dismissal_and_new_source` | Yes | COVERED |
| AC7 additive get_stats expansion | task-local `get_stats` preserve/additive tests including exact candidate-count proof | Yes | COVERED |

#### Security Review
- No hardcoded secrets, injection, path traversal, unsafe deserialization, or shell execution issues found in the changed paths.
- The blocking boundary issue is captured under Data Safety below.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suites in `tests/test_mcp_knowledge_phase2_tools_1329.py` | Later retries added exact-proof coverage for AC2/AC3/AC4/AC5; no weakened or removed assertions were observed in the live snapshot | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Exact row/field assertions exist for AC2/AC3/AC4/AC5 in `tests/test_mcp_knowledge_phase2_tools_1329.py:1004`, `:1010`, `:1146`, `:1198`, `:1262` |
| Negative/error-path coverage | WEAK | `_decode_candidate_id` has explicit malformed-input ToolError branches at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:167-181`, reached from the phase-2 path at `:448`, but no task or adjacent suite exercises invalid `candidate_id` input |
| Manual mutation reasoning | ADEQUATE | The suite would catch reversed reviewed-pair order, reverse edge direction, and positional chunk / reviewed_pairs column swaps via `tests/test_mcp_knowledge_phase2_tools_1329.py:1109`, `:1146`, `:1198`, `:1262` |
| Test independence | STRONG | Fresh in-memory DB fixture and context factory at `tests/test_mcp_knowledge_phase2_tools_1329.py:51-79` |
| Descriptive test names | STRONG | Current retry tests are specific and behavior-focused |

#### Data Safety
- Blocking issue: the live MCP tool boundary registers `store_enrichment` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:795`.
- In the phase-2 non-empty-edge branch, the implementation decodes `candidate_id` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:447-448` and then ignores the decoded `(entity_name, source_a, source_b)` when persisting edges, blindly writing caller-supplied `source_id`, `target_id`, and `relation` at `:457-476`.
- The child task explicitly imports the parent brief at `.owlbear/kanban/tasks/1329-p2-13-tests-phase-2-stats-tools-get-consolidation-candidates-get-stats.md:24`, and the parent brief defines the phase-2 review unit as the source-pair per entity name at `.owlbear/briefs/draft-knowledge-activation/brief.md:97`.
- The architect stance additionally says the dual-schema tool must be validated server-side at `.owlbear/briefs/draft-knowledge-activation/stances/architect.md:64`.
- The underlying schema stores `edges.source_id` / `edges.target_id` as entity references at `serve/knowledge/src/owlbear_knowledge/schema.py:66-67`, but schema init disables foreign keys at `:362`, so mismatched or orphaned edge payloads can persist while the current AC4 tests stay green.

#### Implementation-Aware Gaps
- Significant untested path: malformed `candidate_id` rejection. `_decode_candidate_id` raises `ToolError` on JSON-parse failure and wrong-shape payloads at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:167-181`, but grep found no `pytest.raises(...ToolError...)` coverage for `candidate_id` in `tests/test_mcp_knowledge_phase2_tools_1329.py` or adjacent suites.

#### Builder Process Quality
| Metric | Value |
|-------|-------|
| Builder Notes sections | 5 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The durable `serve/mcp-knowledge/tests/test_ingest_graph_tools.py` coverage for `get_stats` remains legacy-smoke oriented; the new SQL-backed additive proof still lives primarily in the task-local suite. This is informational, not the rejection reason.
- Module-level coverage remains low on a large legacy file, but the current rejection is about phase-2 correctness at the boundary, not residual coverage debt.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 deterministic query / 2+ sources | Query orders by entity name and canonical source ordering at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:185-256`; discriminating task tests are green | `test_entity_in_two_sources_appears_as_candidate`, `test_candidates_ordered_alphabetically_by_entity_name` | PASS |
| AC2 excludes existing cross-source edges and reviewed_pairs rows | Both reviewed-pair and reverse-edge SQL branches are exercised; task tests at `tests/test_mcp_knowledge_phase2_tools_1329.py:1109` and `:1262` are green | `test_ac2_reversed_reviewed_pair_still_excludes_candidate`, `test_ac2_reversed_edge_direction_still_excludes_candidate` | PASS |
| AC3 returns dicts with exact per-field chunk content | Dict-type proof at `tests/test_mcp_knowledge_phase2_tools_1329.py:1004`; positional chunk proof at `:1146` | `test_ac3_candidates_are_dicts_not_objects`, `test_ac3_source_a_chunk_and_source_b_chunk_match_positionally` | PASS |
| AC4 phase-2 non-empty edges write the reviewed cross-source edge | Exact-row proof at `tests/test_mcp_knowledge_phase2_tools_1329.py:1010` is green, but the live MCP boundary does not validate that the persisted edge belongs to the reviewed `candidate_id` / source pair (`serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:447-476`) despite the imported parent brief’s source-pair review-unit contract at `.owlbear/briefs/draft-knowledge-activation/brief.md:97` | `test_phase2_non_empty_edges_writes_edge_to_db`, `test_ac4_exact_edge_row_content_after_phase2_store` | FAIL |
| AC5 phase-2 empty edges write decoded reviewed_pairs row | Candidate decode drives reviewed_pairs insert positionally at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:447-448` and `:476`; direct positional proof at `tests/test_mcp_knowledge_phase2_tools_1329.py:1198` | `test_ac5_reviewed_pairs_columns_match_candidate_id_decoded_positionally` | PASS |
| AC6 new sources create new pairs; old dismissals preserved | Structured pair-set proofs and preservation checks are green | `test_exact_candidate_pairs_after_dismissal_and_new_source` and related AC6 tests | PASS |
| AC7 additive get_stats result | Additive return at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:950-958`; exact task-local proofs are green | task-local AC7 suite including `test_stats_consolidation_candidates_remaining_exact_count` | PASS |

### Deductions
- -0.09 live phase-2 MCP write path does not enforce candidate/edge coherence against the imported brief contract
- -0.05 malformed `candidate_id` error branches are untested on a task-owned system boundary
- -0.02 direct git diff / dirty-tree checks unavailable in this tool surface

### Confidence: 0.84
### Verdict: FAIL

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the phase-2 contract so the child AC and parent brief agree on whether `store_enrichment(candidate_id, edges=[...])` must validate candidate/edge coherence before persisting non-empty edge payloads, then re-dispatch builder/test-writer from that clarified contract | `.owlbear/kanban/tasks/1329-p2-13-tests-phase-2-stats-tools-get-consolidation-candidates-get-stats.md`, `.owlbear/briefs/draft-knowledge-activation/brief.md`, `.owlbear/briefs/draft-knowledge-activation/stances/architect.md`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Task imports brief at task line 24; parent brief review-unit contract at brief line 97; architect validation requirement at architect line 64; live non-empty-edge write path ignores decoded candidate pair at `server.py:447-476` |
| 2 | architect | Add an explicit negative-path proof requirement for malformed `candidate_id` rejection on the phase-2 write path, then return to test-writer/builder with scoped follow-ups | `tests/test_mcp_knowledge_phase2_tools_1329.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | `_decode_candidate_id` error branches at `server.py:167-181` are reached from `:448`, but no task or adjacent suite exercises invalid `candidate_id` input |

### Action
- Rejected to `backlog` under the repeat-review loop-breaker rule. The scoped suite is green, but the phase-2 MCP write path still has a contract/validation gap that is not safe to approve at reviewer confidence threshold.
[[2026-05-07]]
## Architecture Review (cycle 5)

### Context
Fifth cycle. Reviewer rejected under loop-breaker citing AC4 "candidate/edge coherence" gap and untested malformed `candidate_id` paths. After reading the governing Brief (§4.4 line 97) and Architect Stance (line 64), these are not AC gaps — they are novel requirements not stated in any contract.

### Contract Analysis
- **Brief §4.4**: "`store_enrichment(candidate_id, edges=[...])` — writes cross-source edges." Describes agent workflow, not a server-side coherence enforcement mandate.
- **Architect Stance line 64**: "The schema union must be validated server-side (Phase 1 requires chunk_id + entities; Phase 2 requires candidate_id)." This is **parameter presence** validation — already satisfied by `_decode_candidate_id` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:167-181` (validates JSON parse + 3-string-list shape + raises ToolError on failure).
- **AC4 text**: "assert the exact persisted edge row content — source_id, target_id, and relation fields in the edges table must match the **caller-supplied** values" — the cycle-4 test at `tests/test_mcp_knowledge_phase2_tools_1329.py:1010` proves exactly this.

The reviewer's "coherence validation" concern (that persisted edges should be cross-validated against the candidate's source pair) is:
1. Not required by Brief §4.4 (which says "writes cross-source edges" — a description, not an enforcement rule)
2. Not required by the Architect Stance (which requires schema validation, not semantic coherence)
3. Architecturally questionable — the `candidate_id` is a review token identifying what was reviewed; the agent's findings may legitimately reference entities beyond the strict pair
4. YAGNI — internal MCP tools trust the caller (the enrichment agent); defense-in-depth validation is a separate enhancement

The "malformed candidate_id" concern is reasonable hardening but outside current AC scope.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only for Phase 2 consolidation + stats |
| Interface clarity | PASS | All 7 AC lines mechanically verifiable with existing proofs |
| Dependency correctness | PASS | #1328 done; implementation stable since cycle 1 |
| Module layering | PASS | Tests import from server module; no upward imports |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | No novel requirements added |
| Premise challenge | PASS | Reviewer's cycle-4 evidence shows all 7 AC lines satisfied (AC4 fail reason is a novel requirement) |
| Pattern consistency | PASS | Follows #1327 fixture patterns |
| Security surface | PASS | Test-only task |
| Single domain | PASS | knowledge domain |

### Challenge Results
- Challenger: SKIPPED — no design trade-offs; dispute is contract interpretation
- Architect reasoning: Brief and Stance contracts do not mandate edge-candidate coherence enforcement. The reviewer's reading conflates "review unit is source-pair per entity name" (a conceptual description of what the agent reviews) with a server-side enforcement requirement. These are distinct.

### Test Depth
- Max depth: td:2
- Test-writer: SKIP (task tagged `test` — pass-through)

### Verdict: APPROVE
### Action Taken: Advanced to todo. All 7 AC lines satisfied per reviewer's own evidence. The "coherence validation" and "malformed candidate_id" concerns are out-of-scope enhancements — if desired, they belong in separate follow-up tasks targeting the implementation, not this test task's AC.
[[2026-05-07]]
## Test-Writer Notes (retry cycle 5)

- **No new tests added.** Cycle 5 architecture review approved the task without requiring new test coverage.
- **Reviewer cycle 5 Required Follow-up addressed by architect:**
  - AC4 "candidate/edge coherence" concern → architect determined out-of-scope (Brief §4.4 describes agent workflow, not server-side enforcement; YAGNI for internal MCP tools; `_decode_candidate_id` already validates JSON parse + 3-string-list shape)
  - Malformed `candidate_id` negative-path proof → out-of-scope enhancement; belongs in a separate follow-up targeting the implementation, not this test task's AC
- **All 7 AC lines satisfied per reviewer's own evidence (cycle 5 architect's analysis)**
- **Existing test state:** 36 tests in `tests/test_mcp_knowledge_phase2_tools_1329.py`; builder cycle 4 scoped run: 117 passed, 0 failed; ruff clean
- **Step 1b.1 — Direct-to-Review:** Reviewer gaps were out-of-scope enhancements, not test-proof gaps. No implementation fixes needed. Advancing directly to `review` — builder has no work to do.
[[2026-05-07]]
## Builder Notes
- Code changes: none in this cycle (implementation already satisfies current AC contract and test-writer cycle-5 direct-to-review note).
- Verification run (quality-runner scoped):
  - `tests/test_mcp_knowledge_phase2_tools_1329.py`
  - `tests/test_mcp_knowledge_enrichment_tools_1327.py`
  - `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
  - Result: 117 passed, 0 failed, 0 skipped
- Lint status:
  - `ruff check serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py tests/test_mcp_knowledge_phase2_tools_1329.py` => clean (0 violations)
- Coverage:
  - `owlbear_mcp_knowledge.server`: 54.79%
- Evidence summary:
  - Current task-scoped and adjacent regression suites are green.
  - No implementation delta required for this builder pass.

### Post-task Reflection
- Problem faced: repeated loopback cycles on a test-owned task can re-enter builder even when source code is already stable.
- Workaround applied: performed verification-only gate via quality-runner and avoided unnecessary source churn.
- Pattern discovered: in proof-only retries, builder value is fresh evidence and clean routing to review.
- Quality gap: module-level coverage for the large server module remains below 90%, though AC-scoped behavior is fully green in this run.
[[2026-05-07]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 117 passed, 0 failed, 0 skipped
- Suites run: `tests/test_mcp_knowledge_phase2_tools_1329.py`, `tests/test_mcp_knowledge_enrichment_tools_1327.py`, `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`
- code-reader audit completed against the live workspace and current task AC

### Lint Results
- ruff clean on `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and the scoped test files
- VS Code diagnostics: no errors in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_mcp_knowledge_phase2_tools_1329.py`, `tests/test_mcp_knowledge_enrichment_tools_1327.py`, or `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`

### Coverage
- quality-runner reported `owlbear_mcp_knowledge.server` at 55% module coverage
- Not a blocker for this verdict: the task-owned changed behavior is exercised by the task suite plus adjacent phase-1 and `get_stats` regressions

### SCM / Scope Notes
- Commit presence confirmed via `.git/logs/**`: `4ba08abc` (builder), `1b6cf0d0`, `783eeec5`, `c61b2907` (test-writer retries)
- Direct `git diff` / `git status` were not available in this tool surface, so exact changed-file diff reconstruction and dirty-tree contamination checks could not be independently completed. Small confidence deduction applied.
- Review scope anchored to the live source at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` plus the task-owned and adjacent regression suites listed above

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: deterministic ordering for entities in 2+ sources | Candidate SQL orders by `entity_name`, `source_a`, `source_b` in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:256`; behavioral ordering and limit proofs are green in `tests/test_mcp_knowledge_phase2_tools_1329.py:253`, `:279`, and `:299` | `test_entity_in_two_sources_appears_as_candidate`, `test_candidates_ordered_alphabetically_by_entity_name`, `test_limit_caps_number_of_candidates`, `test_entity_in_single_source_excluded_from_candidates` | PASS |
| AC2: exclude existing cross-source edges and reviewed_pairs rows | Both edge-direction branches are present in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:233-234`; both reviewed_pairs order branches are present at `:251-252`; discriminating proofs are green at `tests/test_mcp_knowledge_phase2_tools_1329.py:318`, `:340`, `:1109`, and `:1262` | `test_entity_with_cross_source_edge_excluded_from_candidates`, `test_entity_with_reviewed_pairs_entry_excluded_from_candidates`, `test_ac2_reversed_reviewed_pair_still_excludes_candidate`, `test_ac2_reversed_edge_direction_still_excludes_candidate` | PASS |
| AC3: dict shape + exact per-field chunk payloads | Live implementation returns dict items with exact `source_a_chunk` / `source_b_chunk` fields in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:273-282`; direct dict-type and positional chunk assertions are green at `tests/test_mcp_knowledge_phase2_tools_1329.py:987`, `:1004`, and `:1146` | `test_ac3_candidates_are_dicts_not_objects`, `test_ac3_source_a_chunk_and_source_b_chunk_match_positionally` | PASS |
| AC4: phase-2 non-empty edges persist exact row content | Phase-2 edge writes occur in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:453-465`; exact persisted-row assertions for `source_id`, `target_id`, and `relation` are green at `tests/test_mcp_knowledge_phase2_tools_1329.py:1010`, `:1043`, and `:1051-1053` | `test_phase2_non_empty_edges_writes_edge_to_db`, `test_ac4_exact_edge_row_content_after_phase2_store` | PASS |
| AC5: phase-2 empty edges persist exact reviewed_pairs row | Phase-2 dismissal inserts decoded `(entity_name, source_a, source_b)` at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:447-448` and `:476`; positional decoded-column proof is green at `tests/test_mcp_knowledge_phase2_tools_1329.py:1198`, `:1221`, and `:1237-1241` | `test_phase2_empty_edges_inserts_reviewed_pair_dismissal`, `test_phase2_empty_edges_does_not_write_new_edges`, `test_ac5_reviewed_pairs_columns_match_candidate_id_decoded_positionally` | PASS |
| AC6: new sources create new pairs while old dismissals persist | Candidate regeneration and preserved reviewed-pair behavior are exercised in the live query logic at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:185-264`; structured pair-set and preservation proofs are green at `tests/test_mcp_knowledge_phase2_tools_1329.py:609`, `:637`, `:668`, and `:706` | `test_new_source_generates_new_candidate_pair_for_same_entity`, `test_old_dismissal_preserved_in_reviewed_pairs_after_new_source`, `test_dismissed_pair_remains_excluded_after_new_source_added`, `test_exact_candidate_pairs_after_dismissal_and_new_source` | PASS |
| AC7: additive `get_stats` result | Live implementation preserves legacy graph counts and adds phase-2 fields in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:950-969`; task-local exact-field proofs are green at `tests/test_mcp_knowledge_phase2_tools_1329.py:763`, `:795`, `:814`, `:835`, `:859`, `:883`, and `:952`; adjacent durable `get_stats` regressions are also green in `serve/mcp-knowledge/tests/test_ingest_graph_tools.py:487-540` and `:707-777` | task-local AC7 suite plus adjacent durable `get_stats` suites | PASS |

### Deductions
- -0.03 direct `git diff` / dirty-tree checks unavailable in this tool surface
- -0.02 TestFromAC immutability inferred from live snapshot + task-history commits rather than a direct diff
- -0.02 AC1 proof pins deterministic returned ordering and the live SQL contains `ORDER BY`, but the task suite does not independently distinguish SQL ordering from an equivalent post-query sort

### Informational
- code-reader surfaced hardening gaps around malformed `candidate_id` rejection and omitted `edges` behavior. After checking the latest cycle-5 Architecture Review in the task body and applying the reviewer scope rule, those are out-of-scope enhancement concerns for this task, not blockers for the current AC.
- The header comment in `tests/test_mcp_knowledge_phase2_tools_1329.py` still labels AC3/AC4/AC5 as td:1 even though the later retry proofs are td:2-strength. This is stale commentary only.

### Verdict
- PASS -> docs | confidence 0.93
- Reason: the current task-owned suite plus adjacent regressions give discriminating proof for all seven AC lines, scoped tests/lint are green, and the remaining concerns are informational rather than task-owned defects.

### Action
- Advanced to `docs`.
[[2026-05-07]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/mcp-knowledge/README.md` Tools table: added `get_consolidation_candidates` row, updated `get_stats` description (now includes 4 new fields), updated `store_enrichment` description (dual-mode Phase 1/2) |
| 2 | Module docstrings | Yes | N/A — adequate | `get_consolidation_candidates`: "Return unresolved cross-source consolidation candidates." `store_enrichment`: "Persist enrichment results for phase-1 chunks or phase-2 candidates." `get_stats`: "Get knowledge base summary statistics." All accurate against implementation. |
| 3 | External attribution | No | N/A | Research doc states all 4 high-relevance sources were internal codebase — no external attribution required |
| 4 | Research doc | Yes | Verified | `.owlbear/research/phase2-consolidation-tests-1329.md` exists; linked in task body; follow-up tasks noted as none needed |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` describes `serve/mcp-*/src/**` — matches changed `server.py`. Footer updated: `Last verified: 2026-05-07 (d875a5e4)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | IN (docstrings) | Docstrings verified — adequate, no edit needed |
| `tests/test_mcp_knowledge_phase2_tools_1329.py` | OUT (test file) | N/A |
| `.owlbear/research/phase2-consolidation-tests-1329.md` | IN (research doc) | Verified — exists and linked |
| `serve/mcp-knowledge/README.md` | IN (package README) | Updated — new tool row + 2 stale descriptions fixed |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `serve/mcp-knowledge/README.md` — added `get_consolidation_candidates`, updated `get_stats` and `store_enrichment` descriptions
- `share/diagrams/mcp-topology.excalidraw` — footer `Last verified: 2026-05-07 (d875a5e4)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1329-pytest-scoped.log`
- `.owlbear/scratch/1329-ruff-scoped.log`
- `.owlbear/scratch/1329-pytest.log`
- `.owlbear/scratch/1329-ruff.log`
- `.owlbear/scratch/1329-pytest.txt`
- `.owlbear/scratch/1329-ruff.txt`
- `.owlbear/scratch/1329-quality-run.json`
- `.owlbear/scratch/1329-scoped-tests.txt`

### Commit
`0e5e9c18 docs: update mcp-knowledge README and diagram for phase-2 tools (#1329, doc-writer)`
[[2026-05-07]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: deterministic SQL / 2+ sources | `server.py:256` ORDER BY; tests at `:235`, `:253`, `:279`, `:299` green | PASS |
| AC2: excludes cross-source edges + reviewed_pairs (both directions) | Forward + reverse edge tests at `:318`, `:340`, `:1109`, `:1262` green | PASS |
| AC3: dict shape + exact per-field chunk content | Dict-type at `:1004`, positional chunk at `:1146` green | PASS |
| AC4: Phase 2 non-empty edges persist exact row content | Exact source_id/target_id/relation at `:1010`, `:1043-1053` green | PASS |
| AC5: Phase 2 empty edges persist exact reviewed_pairs row | Positional decoded-column proof at `:1198`, `:1221-1241` green | PASS |
| AC6: new sources create new pairs; old dismissals preserved | Pair-set proofs at `:609`, `:637`, `:668`, `:706` green | PASS |
| AC7: additive get_stats result | Exact field proofs at `:763`, `:795`, `:814`, `:835`, `:952` green | PASS |

### Test Results
- Full suite: 4772 passed, 223 failed (all failures in unrelated domains: kanban, memory, cockpit)
- Task-scoped: 117 passed, 0 failed (test_mcp_knowledge_phase2_tools_1329 + enrichment_1327 + ingest_graph_tools)
- No cross-task regressions detected from this task

### Lint Results
- Task-scoped ruff: All checks passed (server.py + test file + README)
- Full-suite lint violations (12) in unrelated files (serve/knowledge, serve/tools)

### Commit Integrity
- 4ba08abc feat: implement phase-2 consolidation tools (#1329, builder)
- 7a3ce569 test: Phase 2 consolidation + get_stats expansion tests (#1329, test-writer)
- 9891cbd1 test: strengthen AC3/AC6/AC7 proof tests (#1329, test-writer)
- 1b6cf0d0 test: add exact-proof tests for AC3/AC4/AC5 (#1329, test-writer)
- 783eeec5 test: add cycle-3 exact-proof tests for AC2/AC3/AC5 (#1329, test-writer)
- c61b2907 test: add cycle-4 reverse-edge-direction proof for AC2 (#1329, test-writer)
- 0e5e9c18 docs: update mcp-knowledge README and diagram (#1329, doc-writer)
- Git status: clean for all task files

### Reviewer Evidence
- Cycle 5: PASS at 0.93 with detailed AC mapping, code-reader audit, and quality-runner evidence
- Correctly scoped out-of-contract concerns (candidate/edge coherence, malformed candidate_id) per cycle-5 architect analysis

### Architect Quality: 3/5
Initial AC had correct intent but proof-contract wording allowed false-green test patterns. Required 4 architect cycles to close positional-assertion and reverse-direction gaps. Implementation was stable from cycle 1 (never changed), indicating the AC clarity was the bottleneck. Score 3 = notable gaps requiring significant iteration.

### Deduction Breakdown
- -0.03: AC quality score 3/5

### Confidence: 0.97
### Action: Archive