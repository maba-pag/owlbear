---
id: 1848
title: 'Consolidation test: memory voting integration'
status: archived
priority: medium
created: 2026-05-24T19:01:58.079687+02:00
updated: 2026-05-25T10:25:26.650878+02:00
tags:
  - phase-2
  - scope:memory
  - consolidation-test
parent: 1839
depends_on:
  - 1842
  - 1843
  - 1844
  - 1845
  - 1846
  - 1847
ac:
  - 'AC1: Integration test at MemoryEngine+recall_memory level: save entries, approve
    to recallable state, recall with ≥20 entries exercising 16+2+2 slot allocation
    (regular/explore/challenge). Assess via record_assessment (outstanding, unremarkable,
    didnt_use) and record_factually_wrong. Verify score=confidence+(outstanding×0.1)-(unremarkable×0.01),
    counters match submissions, recall reflects updated sort.'
  - 'AC2: State transitions verified end-to-end: (a) factually_wrong on approved →
    contested, still in recall; (b) second factually_wrong from different task_id
    → disputed, excluded from recall; (c) didnt_use > 50×max(outstanding+unremarkable,
    1) → stale via check_slot_efficiency, excluded from recall. Each verified by recall
    call confirming inclusion/exclusion.'
  - 'AC3: Migration test: seed entries with legacy frontmatter (no score/counter fields)
    → migrate_scores() → verify score=confidence, counters=0 → sort by (-score, id)
    equals sort by (-confidence, id) within same state_rank → subsequent record_assessment
    updates score per formula and recall reflects new order.'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1839

## Scope

End-to-end integration test verifying the full memory voting pipeline works across all subtask boundaries.

### In Scope
- Full lifecycle: save → recall (slot allocation) → assess → verify
- All bucket types exercised
- State transitions verified (contested, disputed, stale)
- Score computation verified end-to-end
- Migration scenario (legacy entries without score)
- Recall exclusion after state transitions

### Out of Scope
- Unit-level testing (covered by individual subtasks)
- Pipeline instruction verification (docs, not code)

## Domain
tests/

[[2026-05-25T09:23:13+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Consolidation test only — no production code |
| Interface clarity | PASS | Refined AC names concrete callables: MemoryEngine.save/record_assessment/record_factually_wrong/check_slot_efficiency/migrate_scores + recall_memory |
| Dependency correctness | PASS | All 6 deps (#1842-#1847) archived/completed |
| Module layering | PASS | Domain tests/ only, no upward imports |
| TDD compliance | PASS | Test-writer writes integration test; implementation exists from completed subtasks |
| KISS/YAGNI | PASS | Tests what was built, no speculative scenarios |
| Premise challenge | PASS | Consolidation tests validate cross-boundary integration — necessary for 9-task decomposition |
| Pattern consistency | PASS | Follows sibling patterns (test_assess_memories_1846, test_confirmation_cycle_1845): MemoryEngine + tmp_path fixture |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | tests/ only |

### Challenge Results
- Challenger: reconsider (confidence 0.42)
- Findings: AC mechanical quality failures (vague quantifiers, missing test target, create→recall state gap, externalized constants, ambiguous migration oracle)
- Architect response: accepted — refined all 3 AC lines to address every finding. Enumerated buckets, specified approve-to-recallable-state step, named concrete callables, inlined formula/thresholds, clarified migration ordering comparison scope.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC (2→3 lines, addressed challenger findings), advanced to todo.

[[2026-05-25T09:34:06+02:00]]
## Test-Writer Notes
- Test file: `tests/test_memory_voting_integration.py`
- Class names: `TestMemoryVotingLifecycle`, `TestMemoryVotingStateTransitions`, `TestMemoryVotingMigration`
- Total tests: 26, all PASS against current implementation (all 6 deps archived)
- Lint: clean (ruff exit 0)

| Category | Count | Notes |
|----------|-------|-------|
| Happy path | 14 | Full lifecycle, score formula, counters, recall sort, slot allocation |
| Edge / boundary | 3 | Explore pool, challenge pool, stale threshold boundary (50 vs 51) |
| Error / state | 9 | Contested inclusion, disputed exclusion, stale exclusion, full pipeline |

### AC Coverage

| AC | Tests |
|----|-------|
| AC1: save→approve→recall, 16+2+2 slots, score formula, counters, sort | test_recall_returns_twenty_from_twenty_two_approved, test_recall_exercises_explore_pool, test_recall_exercises_challenge_pool, test_score_formula_*, test_counters_*, test_recall_sort_*, test_record_factually_wrong_contested_entry_appears_in_recall |
| AC2: contested (included), disputed (excluded), stale (excluded) via check_slot_efficiency | test_first_factually_wrong_*, test_contested_entry_included_in_recall, test_second_factually_wrong_*, test_disputed_entry_excluded_from_recall, test_full_factually_wrong_pipeline_*, test_stale_transition_*, test_stale_entry_excluded_from_recall, test_stale_threshold_boundary_*, test_full_state_transition_pipeline_* |
| AC3: migrate_scores sets score=confidence, counters=0, sort equivalence, post-migration assessment | test_migrate_scores_returns_count_*, test_migrate_scores_sets_score_*, test_migrate_scores_sets_all_counters_*, test_migrate_scores_sort_*, test_migrate_scores_does_not_migrate_modern_*, test_post_migration_*, test_migrate_and_recall_full_round_trip |

### Direct-to-review advance
All 26 tests pass against the current implementation — expected: all 6 deps (#1842-#1847) are archived with working implementations. Builder has no code to write; reviewer confirms consolidation coverage.

[[2026-05-25T09:45:01+02:00]]
## Review Evidence
- Verdict: FAIL
- Builder evidence reviewed first: task notes reported 26 tests passing and lint clean. Independent reviewer quality-runner confirmation matched that: 26 passed, 0 failed, ruff clean, coverage overall 35%, owlbear_memory.engine 62%, owlbear_mcp_memory.tools 25%.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | The task-local consolidation test does not exercise the lifecycle promised by the task scope. It constructs approved entries and writes them straight to disk instead of driving entries through the real save plus pending-to-curated promotion plus approve path before recall. This leaves the task's full-lifecycle claim unproven in this file. | Task scope at .owlbear/kanban/tasks/1848-consolidation-test-memory-voting-integration.md:49. AC1 at .owlbear/kanban/tasks/1848-consolidation-test-memory-voting-integration.md:21. Test helper seeds approved state at tests/test_memory_voting_integration.py:62, :75, :96. AC1 setup uses that helper at tests/test_memory_voting_integration.py:172-173, :195-196, :234-246. Real lifecycle lives at serve/memory/src/owlbear_memory/engine.py:320, :176, :194, :126. Existing sibling lifecycle coverage exists in tests/test_recall_memory.py:80-118, so this is a task-local proof gap, not an implementation defect. | todo |
| 2 | AC1 | The slot-allocation proof is not strong enough to prove the exact 16 regular, 2 explore, and 2 challenge split for limit 20. The implementation uses fixed capacities, but the test only checks total count and presence of four named entries. Those assertions would still pass under several incorrect allocations. | Fixed capacities at serve/mcp-memory/src/owlbear_mcp_memory/tools.py:35-36, :290-299. Returned output drops bucket provenance at :310-312. Current assertions only check len 20 at tests/test_memory_voting_integration.py:181 and presence at :214-215 and :254-255. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Replace the AC1 setup that seeds approved files directly with a task-local lifecycle setup that drives entries through save plus pending-to-curated promotion plus approve before recall, or through the equivalent public API path already used elsewhere in the repo. | tests/test_memory_voting_integration.py | Finding 1 |
| 2 | test-writer | Strengthen AC1 slot assertions so the test fails unless recall selects exactly 16 regular entries, 2 explore entries, and 2 challenge entries at limit 20. | tests/test_memory_voting_integration.py | Finding 2 |

## Observations
- AC2 is materially covered by the full recall inclusion/exclusion pipeline at tests/test_memory_voting_integration.py:488 plus supporting state-transition assertions at :370, :434, and :450.
- AC3 is materially covered by the migration round trip at tests/test_memory_voting_integration.py:546, :581, and :670.
- Independent scoped verification: tests/test_memory_voting_integration.py passed 26 tests, lint was clean, and coverage was 35% overall. The rejection is about AC1 proof quality, not failing execution.

[[2026-05-25T09:52:29+02:00]]
## Test-Writer Notes
- Test file: tests/test_memory_voting_integration.py
- Retry: 2 new tests added to TestMemoryVotingLifecycle for reviewer gaps (Finding 1 and Finding 2)

| New Test | Targets | Finding |
|----------|---------|---------|
| test_full_lifecycle_save_edit_approve_then_recall | AC1 lifecycle proof: 22 entries driven through engine.save() + engine.edit(scope_agents=...) + engine.approve() before recall_memory; verifies PENDING→CURATED→APPROVED chain is recallable | #1 |
| test_recall_slot_allocation_exactly_16_regular_2_explore_2_challenge | AC1 slot split: 22 entries structured across 3 pools (2 zero-activity→explore, 2 zero-outstanding→challenge, 16 high-score + 2 excluded low-score→regular); asserts exact membership so any wrong pool size causes failure | #2 |

- Tests per category: 2 new (both happy-path integration, with tight negative assertions for slot test)
- Total tests: 28, all PASS against current impl (26 original + 2 new)
- Lint: ruff clean
- Direct-to-review advance: both new tests pass against current implementation (all 6 deps archived, implementation complete). Builder has no code to write; reviewer confirms coverage quality.

[[2026-05-25T10:01:14+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1848 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: task retry notes at .owlbear/kanban/tasks/1848-consolidation-test-memory-voting-integration.md:141-150 reported 2 new tests, 28 passing total, and ruff clean.
- Independent reviewer verification: quality-runner scoped check confirmed 28 passed, 0 failed, ruff clean, coverage overall 31%, owlbear_memory.engine 74%, owlbear_mcp_memory.tools 25%, no environment issues.
- Challenger cross-check: proceed, confidence 0.83, no blocking findings.
- AC evidence map:
  - AC1: lifecycle path is now proved task-locally by test_full_lifecycle_save_edit_approve_then_recall at tests/test_memory_voting_integration.py:360 using engine.save at :375, engine.edit at :383, and engine.approve at :394, matching the real control path in serve/memory/src/owlbear_memory/engine.py:320, :176, :126; recall then returns 20 entries at tests/test_memory_voting_integration.py:399. Exact slot allocation is now proved by test_recall_slot_allocation_exactly_16_regular_2_explore_2_challenge at tests/test_memory_voting_integration.py:402 with exact inclusion/exclusion assertions at :469, :473, :481 against the slot capacities in serve/mcp-memory/src/owlbear_mcp_memory/tools.py:35-36, :290-299. The remaining AC1 formula/counter/sort/factually-wrong proof is covered by tests/test_memory_voting_integration.py:266, :297, :316, :343.
  - AC2: end-to-end state transitions are proved by tests/test_memory_voting_integration.py:506, :540, :586, and the recall inclusion/exclusion pipeline at :622 with concrete recall assertions at :654-656, matching serve/memory/src/owlbear_memory/engine.py:231, :275, and the stale trigger path at :316-317.
  - AC3: migration behavior is proved by tests/test_memory_voting_integration.py:696, :734, :750, :762, :775, and the full round trip at :804 with final ordering assertions at :832, matching serve/memory/src/owlbear_memory/engine.py:350.
- Blocking findings: none.

## Observations
- The retry closes both prior AC1 proof gaps without requiring production changes.
- AC1 proof is still distributed across multiple focused tests rather than a single monolithic scenario. That is acceptable here because each required behavior is independently asserted tightly enough to fail on contract breakage.
- Non-blocking cleanup: the slot-allocation test docstring says RegularLow uses confidence 0.5 / score 1.0 at tests/test_memory_voting_integration.py:411, but the setup uses confidence 0.7 at :457. The assertions remain valid; only the comment is stale.

[[2026-05-25T10:02:38+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A — no docs impact | Only changed file: `tests/test_memory_voting_integration.py` (new test file). No `serve/{pkg}/src/` or package-interface changes. Convention mapping yields no README targets. |
| External Attribution | N/A | No external sources referenced in implementation. |
| Research Doc | N/A | No research artifact for this task. |
| Deletion Detection | N/A | No files deleted. |

### Scratch Cleanup
No `.owlbear/scratch/1848-*` files found — nothing to clean.

### Verdict
Test-only addition. No documentation impact. Gate passed.

[[2026-05-25T10:25:26+02:00]]
## Audit

### Regression Detection
Quality-runner full domain run: 246 passed, 8 failed. All 8 failures confirmed pre-existing (present without #1848 changes via git stash check). Task-scoped run: 28 passed, 0 failed. Task introduced 0 regressions.

### Intent Verification
Changed file: `tests/test_memory_voting_integration.py` — in `tests/` domain, matches task's stated domain (consolidation test). No production code changes, no extraneous scope. PASS.

### Architect Quality
AC refined after challenger review (confidence 0.42). Post-refinement AC names concrete callables, formulas, thresholds, exact slot counts. Score: 4/5 — adequate, needed one challenger round to reach specificity.

### Commit Integrity
Two commits verified:
- `2e897d7d test: add memory voting integration consolidation tests (#1848, test-writer)`
- `ee4da22a test: add retry tests for memory voting AC1 lifecycle+slot proof (#1848, test-writer)`
Both properly attributed with correct task ID.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
