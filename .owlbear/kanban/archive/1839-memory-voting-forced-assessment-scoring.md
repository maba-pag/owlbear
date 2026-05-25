---
id: 1839
title: Memory voting — forced assessment scoring
status: archived
priority: needed
created: 2026-05-24T18:57:20.675933+02:00
updated: 2026-05-25T11:42:00.425598+02:00
tags:
  - feature
  - memory
  - phase-2
parent:
depends_on:
  - 1848
ac:
  - 'AC1: Memory entries have `score` float field. Score = initial_confidence + (outstanding_count
    × 0.1) - (unremarkable_count × 0.01). Recall sorts by (state_rank, -score, id).
    X=0.1, Y=0.01 are named constants.'
  - 'AC2: `assess_memories` MCP tool accepts [{entry_id, bucket}] where bucket ∈ {outstanding,
    unremarkable, didnt_use, factually_wrong}. Updates counters + score atomically.
    Returns success/failure per entry. Validates: entry exists, voteable state (approved/curated/contested),
    valid bucket.'
  - 'AC3: `recall_memory` returns limit entries (default 20): limit-4 highest-score
    in scope, 2 lowest total assessments, 2 lowest outstanding_count. Dedup priority:
    explore > challenge > regular. Fewer entries than limit → return all.'
  - 'AC4: After assess_memories, check: if didnt_use_count > 50 × max(outstanding_count
    + unremarkable_count, 1) → state transitions to stale. Stale excluded from recall.'
  - 'AC5: First factually_wrong → state contested (still recalled). Second factually_wrong
    from different task → state disputed (excluded from recall).'
  - 'AC6: States contested, disputed, stale added. Contested: normal recall. Disputed
    + stale: excluded from recall. All resolvable by curator.'
  - 'AC7: Migration: existing entries get score=confidence, counters=0, state unchanged.
    Idempotent. Ordering identical pre-migration.'
  - 'AC8: Pipeline end_work protocol includes assessment instruction with opaque bucket
    framing (no scoring explanation).'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Replace static confidence-based recall ordering with self-improving forced assessment scoring. Agents categorize all recalled entries at end-of-task into quality buckets; scores update on evidence only.

## Brief

Full brief: `.owlbear/briefs/draft-memory-voting/brief.md`

## Core Mechanism

1. Recall delivers 20 entries: 16 by score + 2 explore (lowest total assessments) + 2 challenge (lowest outstanding)
2. End-of-task: agent categorizes all 20 → outstanding (+X), unremarkable (-Y), didn't-use (0), factually-wrong (→ contested)
3. Score replaces confidence as sort key
4. Slot-efficiency block at 50× threshold → stale
5. Confirmation cycle: contested → disputed after second agent confirms

## Key Properties

- No time-based decay — moves only on assessment evidence
- Quality over popularity — outstanding is a quality judgment, not exposure count
- Opaque bucketing — agents don't know scoring mechanics
- Proven mediocrity sinks; unknown stays neutral

## Scope

- Model fields: outstanding_count, unremarkable_count, didnt_use_count, score
- States: contested, disputed, stale
- Score: initial_confidence + (outstanding × 0.1) - (unremarkable × 0.01)
- Recall: sort by (state_rank, -score, id) with 16+2+2 reserved slots
- MCP tool: assess_memories (batch entry_id→bucket)
- Slot-efficiency: didnt_use > 50 × max(outstanding + unremarkable, 1) → stale
- Confirmation: first factually_wrong → contested; second from different task → disputed
- Migration: score = confidence, counters = 0
- Instruction update: assessment framing in end_work protocol

## Constants

- X = 0.1 (outstanding boost)
- Y = 0.01 (unremarkable penalty)
- Stale threshold = 50×
- Slot allocation: 16 regular + 2 explore + 2 challenge = 20

## Out of Scope

- Cockpit UI (follow-on)
- Magnitude tuning (follow-on after 2-4 weeks live)
- Confidence deprecation (follow-on after 4-8 weeks)
- Per-agent score variants
- Assessment analytics

[[2026-05-24T19:02:22+02:00]]
## Planning
### Decomposition: Memory voting — forced assessment scoring
- Tasks created: 9
- Dependency layers: 4
- Phase: 2

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| 1840 | P2-01: State machine — contested, disputed, stale states | critical | — | phase-2, scope:memory, feature |
| 1841 | P2-02: Model fields — assessment counters and score computation | critical | — | phase-2, scope:memory, feature |
| 1842 | P2-03: Migration — score initialization from confidence | needed | 1841 | phase-2, scope:memory, migration |
| 1843 | P2-04: Recall — reserved explore and challenge slots | needed | 1840, 1841 | phase-2, scope:memory, feature |
| 1844 | P2-05: Slot-efficiency — auto-stale transition | needed | 1840, 1841 | phase-2, scope:memory, feature |
| 1845 | P2-06: Confirmation cycle — factually-wrong to contested/disputed | needed | 1840, 1841 | phase-2, scope:memory, feature |
| 1846 | P2-07: assess_memories MCP tool | needed | 1841, 1844, 1845 | phase-2, scope:memory, feature |
| 1847 | P2-08: Pipeline instruction — assessment protocol | needed | 1846 | phase-2, scope:memory, docs |
| 1848 | Consolidation test: memory voting integration | important | 1842-1847 | phase-2, scope:memory, consolidation-test |

### Dependency Graph
```mermaid
graph TD
  1840[\"#1840 State machine\"] 
  1841[\"#1841 Model + score\"]
  1842[\"#1842 Migration\"] --> 1841
  1843[\"#1843 Recall slots\"] --> 1840 & 1841
  1844[\"#1844 Slot-efficiency\"] --> 1840 & 1841
  1845[\"#1845 Confirmation\"] --> 1840 & 1841
  1846[\"#1846 assess_memories\"] --> 1841 & 1844 & 1845
  1847[\"#1847 Instructions\"] --> 1846
  1848[\"#1848 Consolidation\"] --> 1842 & 1843 & 1844 & 1845 & 1846 & 1847
  1839[\"#1839 Parent\"] --> 1848
```

[[2026-05-25T10:47:57+02:00]]
## Test-Writer Notes
- Test file: `tests/test_memory_voting_scoring_1839.py`
- Classes: `TestFromAC_ScoringAndConstants`, `TestFromAC_AssessMemoriesContract`, `TestFromAC_RecallSlotAllocation`, `TestFromAC_SlotEfficiencyStale`, `TestFromAC_FactuallyWrongProtocol`, `TestFromAC_StateRecallContract`, `TestFromAC_MigrationContract`
- Tests per category: happy 24, edge 7, error 7, boundary 2
- Total: 40 tests
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC1: score field, named constants, compute_score formula, recall sort | test_outstanding_boost_constant_is_0_1, test_unremarkable_penalty_constant_is_0_01, test_stale_threshold_constant_is_50, test_score_field_exists_on_memory_entry, test_score_initialized_to_confidence_on_save, test_compute_score_outstanding_increases_score, test_compute_score_unremarkable_decreases_score, test_compute_score_full_formula, test_recall_sorts_higher_score_first |
| AC2: assess_memories batch contract, per-entry success/failure, validation | test_batch_result_structure_has_results_key, test_success_result_has_entry_id_and_success_true, test_failure_result_has_entry_id_success_false_and_error, test_batch_continues_after_per_entry_failure, test_empty_assessments_raises_tool_error, test_empty_task_id_raises_tool_error, test_invalid_bucket_raises_tool_error, test_assess_outstanding_increments_counter_and_updates_score, test_contested_entry_is_voteable_state |
| AC3: recall slots, default limit, fewer-than-limit, dedup | test_recall_returns_string, test_default_limit_is_20, test_fewer_entries_than_limit_returns_all, test_slot_constants_explore_plus_challenge_equals_four, test_explore_dedup_excludes_entry_from_challenge_pool |
| AC4: slot-efficiency predicate, stale exclusion | test_stale_fires_when_didnt_use_exceeds_threshold, test_stale_does_not_fire_at_exact_threshold, test_stale_denominator_uses_max_with_one_when_both_counters_zero, test_stale_entry_excluded_from_recall |
| AC5: factually_wrong → contested/disputed, same-task idempotence | test_first_factually_wrong_transitions_approved_to_contested, test_first_factually_wrong_stores_contested_by_task, test_second_factually_wrong_different_task_transitions_to_disputed, test_same_task_id_on_contested_does_not_escalate |
| AC6: state recall inclusion/exclusion, curator resolve | test_contested_entry_appears_in_recall, test_disputed_entry_excluded_from_recall, test_resolve_disputed_entry_returns_it_to_recall, test_resolve_stale_entry_returns_it_to_recall, test_resolve_contested_entry_returns_it_to_regular_recall |
| AC7: migration score, counters, idempotence, sort order | test_migrate_sets_score_equal_to_confidence, test_migrate_sets_all_counters_to_zero, test_migrate_is_idempotent, test_migrate_sort_order_identical_pre_and_post |
| AC8: pipeline instruction (docs) | Non-impl — no testable Python interface; covered by #1847 docs task. |

### Note: All 40 tests pass against current implementation
Expected — all 9 subtasks (#1840-#1848) are archived with complete implementations. Builder has no new code to write; reviewer confirms parent-task AC contract coverage.

[[2026-05-25T10:49:41+02:00]]
## Builder Notes
- Implementation: no code changes (pass-through; parent contract already implemented by archived subtasks #1840-#1848)
- Files changed: none
- Tests: 40/40 passed in `tests/test_memory_voting_scoring_1839.py` via quality-runner
- Coverage: 16% overall in scoped run (`owlbear_mcp_memory.tools` 36%, `owlbear_mcp_memory` 100%)
- ruff: clean
- Evidence summary: Test-writer notes indicated full AC contract already implemented and this parent task has no new implementation delta; quality-runner confirmed green + lint-clean status before advancement.

[[2026-05-25T11:21:47+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1839 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: task notes reported no implementation delta, 40/40 passing in `tests/test_memory_voting_scoring_1839.py`, and ruff clean. That local proof is not sufficient on its own for the full parent contract, so review also checked the archived reviewed child proof surface that this roll-up explicitly depends on.
- AC evidence map:
  - AC1 maps to `serve/memory/src/owlbear_memory/models.py` score/counter fields and `serve/memory/src/owlbear_memory/engine.py` constants + `compute_score`; recall ordering is implemented in `serve/mcp-memory/src/owlbear_mcp_memory/tools.py`. Parent tests cover constants/formula/basic ordering, and archived integration proof in `tests/test_memory_voting_integration.py` confirms the shipped lifecycle and exact ordering behavior.
  - AC2 maps to `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:462-508` with counter/score updates in `serve/memory/src/owlbear_memory/engine.py:275-317` and factually-wrong delegation in `serve/memory/src/owlbear_memory/engine.py:231-272`. Stronger proof for malformed-item validation, MCP registration, all four buckets, per-entry failure handling, and atomic write path is already archived and reviewed in task #1846 (`tests/test_assess_memories_1846.py`; review evidence in archived #1846).
  - AC3 maps to reserved-slot recall in `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:251-312`. The parent-local dedup test is weak in isolation, but archived reviewed child proof closes that gap: `tests/test_recall_slots_1843.py:653` proves explore > challenge dedup and `tests/test_memory_voting_integration.py:402` proves exact 16+2+2 allocation. Archived #1843 and #1848 both passed review.
  - AC4 maps to `STALE_THRESHOLD`, `check_slot_efficiency`, and post-assessment stale transition in `serve/memory/src/owlbear_memory/engine.py`; parent tests plus archived integration coverage prove threshold behavior and stale recall exclusion.
  - AC5/AC6 map to confirmation-cycle and resolve paths in `serve/memory/src/owlbear_memory/engine.py` plus recallable-state filtering in `serve/mcp-memory/src/owlbear_mcp_memory/tools.py`; parent tests and archived integration coverage prove contested inclusion, disputed/stale exclusion, and resolve-to-approved behavior.
  - AC7 maps to `serve/memory/src/owlbear_memory/engine.py:350-383`; parent tests prove score backfill, zeroed counters, idempotence, and preserved ordering, with archived integration coverage reinforcing post-migration recall behavior.
  - AC8 is directly present in `share/instructions/pipeline-agents.instructions.md:12-20` and `share/skills/r-pipeline-protocol/SKILL.md:279-289`; archived docs task #1847 already reviewed PASS on exact framing and opaque-bucketing wording.
- Cross-checks: code-reader adversarial review found no blocking implementation or proof gap once the archived child tasks were treated as the parent roll-up proof surface. Challenger review attempted to overturn PASS and concluded the strongest attack fails for the same reason.
- Blocking findings: none.

## Observations
- The parent suite `tests/test_memory_voting_scoring_1839.py` should be read as a summary suite, not the sole proof surface for every AC. AC2 and especially AC3 rely on stronger archived child-task proof.
- There is still durable legacy debt in `tests/test_recall_memory.py:583`, which encodes the older pre-slot expectation noted during archived #1843 review. That is non-blocking here because later task-local and integration proof matches the shipped reserved-slot contract.
- No independent quality-runner rerun was needed for this review because the parent task has no code delta and the child tasks it depends on already carry reviewed executable proof.

[[2026-05-25T11:24:29+02:00]]
## Docs Gate

### Item 1: README Verification
- `serve/memory/README.md` — verified complete: all new fields (`outstanding_count`, `unremarkable_count`, `didnt_use_count`, `score`, `contested_by_task`), new states (`contested`, `disputed`, `stale`), scoring constants (`OUTSTANDING_BOOST`, `UNREMARKABLE_PENALTY`, `STALE_THRESHOLD`), `compute_score`, `check_slot_efficiency`, `record_assessment`, `record_factually_wrong`, `try_stale_transition`, `migrate_scores`, full state-machine table, and `memory-migrate` CLI command — all accurate. No drift.
- `serve/mcp-memory/README.md` — verified complete: `assess_memories` tool row present with correct description; `recall_memory` description updated with three-pool slot allocation, `SLOT_EXPLORE=2`, `SLOT_CHALLENGE=2`, final sort `(state_rank, -score, id)`, default limit 20; all new fields in Entry Schema; state model updated with `contested`, `disputed`, `stale` and their recall semantics. No drift.
- `share/README.md` — instruction and skill counts unchanged (7 / 35); no new files added by this feature. No update needed.
- `README.md` / `README-consumer.md` — individual MCP tools are not listed at root level; no impact.

### Item 2: External Attribution
N/A — no external sources referenced. Original OwlBear design.

### Item 3: Research Doc
N/A — no `.owlbear/research/` artifact; feature brief at `.owlbear/briefs/draft-memory-voting/brief.md` (referenced in task body).

### Item 4: Deletion Detection
N/A — builder notes confirm no code delta at parent level; subtasks added new functionality only. No files deleted, no orphaned references.

### Scratch Cleanup
No `.owlbear/scratch/1839-*` files created for this task.

### Verdict
DONE #1839 -> done | docs gate passed

[[2026-05-25T11:42:00+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 5241 passed, 20 failed, 14 skipped
- All 20 failures are pre-existing in unrelated domains (test_cockpit_view.py: stale file references; test_server.py: NoneType errors in kanban server) — none in memory domain
- All 40 parent-task tests pass; memory-domain tests clean
- regression verdict: PASS (no new regressions from this task)

### Intent Verification
- scope alignment: PASS (all changed files in serve/memory/, serve/mcp-memory/, share/instructions/, share/skills/ — memory domain only)
- purpose match: PASS (forced assessment scoring, state machine, recall slots, migration — all match stated objective)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
- AC specificity: excellent — 8 lines with exact formulas (X=0.1, Y=0.01, threshold=50x), slot allocations (16+2+2), state transition rules, and validation constraints
- Edge case coverage: addressed (idempotent migration, same-task dedup, threshold boundary behavior)
- Design direction: brief reference provided clear implementation path
- No AC gaps requiring builder improvisation

### Commit Integrity
- upstream commit presence: PASS (subtask builder commits visible for #1840-#1847 in git log; test-writer commit 3faa18e2 for #1839; integration test commits for #1848)
- kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
- No deductions. Pre-existing failures in unrelated domains do not constitute regressions. Lint violations in serve/knowledge/ are unrelated. Reviewer evidence is detailed with PASS verdict. AC quality is 5/5.

### Confidence: 1.00
### Action: archive
