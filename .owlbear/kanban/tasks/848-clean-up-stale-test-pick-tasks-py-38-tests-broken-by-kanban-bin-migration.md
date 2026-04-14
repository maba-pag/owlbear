---
id: 848
title: Clean up stale test_pick_tasks.py — 38 tests broken by kanban_bin migration
status: in-progress
priority: nice-to-have
created: '2026-04-12T12:13:32.236167+00:00'
updated: '2026-04-14T15:03:03.420477+00:00'
tags:
- phase-3
- type:test
- scope:mcp-kanban
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- All 38 tests in `tests/test_pick_tasks.py` either pass or are intentionally removed/archived
- If tests are updated: replace stale `kanban_bin` AppContext with engine-based pattern
- If tests are removed: gate/sort/limit coverage is verified to exist in other test files (#823, #825, test_kanban_mcp_migration.py)
- No net reduction in pick_tasks behavioral coverage

## Context

`test_pick_tasks.py` (consolidated from #620, #621, #628) uses the pre-Phase-2 `AppContext(kanban_bin=...)` pattern. All 38 tests fail with `TypeError: AppContext.__init__() got an unexpected keyword argument 'kanban_bin'`. This was broken by Phase 2 engine extraction, not by #826.

The tests cover gate logic, sort order, limit capping, edge cases, null-body safety, and tag passthrough. Most of this coverage is now duplicated across `test_pick_dispatchable_823.py`, `test_pick_dispatchable_824.py`, `test_server_pick_tasks_thin_wrapper_825.py`, and `test_kanban_mcp_migration.py`.

**Research needed:** verify coverage overlap before deciding update vs. remove.

Source: `.owlbear/research/slim-server-pick-tasks.md` §3.4
[[2026-04-13]]
## Research

Verified coverage overlap between 38 stale tests in `test_pick_tasks.py` and replacement suite (93 tests across 4 files).

**Key findings:**
- 24/38 tests have direct behavioral equivalents in #823/#824/#825/migration tests
- 10/38 test `_run_kanban` CLI patterns that no longer exist (engine extraction)
- 2/38 test atomicity gate intentionally dropped from `dispatch.py`
- 2/38 test JSON null-body scenario made impossible by Pydantic `body: str=""` model

**Trade-off matrix:** Update vs. Remove → Remove wins at .95 confidence. Updating would duplicate 93 existing tests using obsolete mock patterns.

**Follow-up:** #867 — delete `test_pick_tasks.py` (backlog, trivial file deletion)
**Doc:** `.owlbear/research/stale-test-pick-tasks-cleanup.md`

[[2026-04-14]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: clean up one stale test file |
| Interface clarity | PASS | AC clearly specifies update-or-remove decision; research resolved to "remove" |
| Dependency correctness | PASS | No dependencies; replacement tests (#823/#824/#825/migration) all exist and pass |
| Module layering | N/A | Test file deletion, no module imports affected |
| TDD compliance | PASS | Tagged `type:test` (non-impl pass-through) |
| KISS/YAGNI | PASS | Trivial file deletion, no over-engineering |
| Premise challenge | PASS | 38 broken tests (100% fail rate) confirm cleanup is warranted |
| Pattern consistency | PASS | Removing obsolete `kanban_bin`/`_run_kanban` mock patterns aligns with engine-based architecture |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Codebase Verification

- `tests/test_pick_tasks.py`: 38 test functions confirmed (8 classes). All use `AppContext(kanban_bin=...)` which no longer exists.
- Replacement test files verified (141 total tests): test_pick_dispatchable_823.py (37), test_pick_dispatchable_824.py (38), test_server_pick_tasks_thin_wrapper_825.py (14), test_kanban_mcp_migration.py (52).
- Research doc `.owlbear/research/stale-test-pick-tasks-cleanup.md` provides complete test-by-test coverage matrix with zero gaps.
- `serve/kanban/src/owlbear_kanban/dispatch.py` confirmed: 5 gates (blocked, claimed, tag, TDD, clarity). No atomicity gate — 2 stale atomicity tests test deleted code.

### Challenge Results
- Challenger: BLOCK (confidence 0.0) — cited atomicity gate removal, #867 redundancy, AC hedging, test count discrepancy
- Architect response: REBUTTED
  - Atomicity gate: Not in current dispatch.py. Tests for nonexistent code are correctly removed. Re-adding the gate is a separate task, not a blocker for cleanup.
  - #867 redundancy: Valid concern. **#867 should be archived/closed as duplicate of #848.** Both tasks delete the same file.
  - AC hedging: Immaterial — research resolved the decision to "remove." Builder follows the clear recommendation and research doc.
  - Test count: Research cited 93; current count is 141. Higher count strengthens the coverage argument.
- Final: Override challenger BLOCK → APPROVE (confidence 0.92)

### Redundancy Note
Follow-up #867 ("Delete stale test_pick_tasks.py") is a near-duplicate of this task. Both result in deleting `tests/test_pick_tasks.py`. Recommend the orchestrator archive #867 to avoid duplicate pipeline work.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder should delete `tests/test_pick_tasks.py` and verify all remaining tests pass.
[[2026-04-14]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no tests applicable.
- Task consists entirely of deleting `tests/test_pick_tasks.py` and verifying existing replacement coverage (141 tests across 4 files).
- No new Python interfaces introduced — nothing to write failing tests for.
- Passing through to builder.