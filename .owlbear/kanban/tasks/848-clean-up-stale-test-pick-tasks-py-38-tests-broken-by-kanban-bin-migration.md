---
id: 848
title: Clean up stale test_pick_tasks.py — 38 tests broken by kanban_bin migration
status: done
priority: nice-to-have
created: '2026-04-12T12:13:32.236167+00:00'
updated: '2026-04-15T01:12:02.223520+00:00'
tags:
- phase-3
- type:test
- scope:mcp-kanban
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: clear-blade
claimed_at: '2026-04-15T01:12:02.223520+00:00'
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
[[2026-04-14]]
## Builder Notes

### Action Taken
- Deleted `tests/test_pick_tasks.py` (38 stale tests, 100% fail rate)

### RED Verification
- `uv run pytest tests/test_pick_tasks.py`: **38 failed** — all tests failed with `TypeError: AppContext.__init__() got an unexpected keyword argument 'kanban_bin'`

### Coverage Verification
- Replacement suite (4 files): **141 passed, 0 failed**
  - `test_pick_dispatchable_823.py`: 37 tests
  - `test_pick_dispatchable_824.py`: 38 tests
  - `test_server_pick_tasks_thin_wrapper_825.py`: 14 tests
  - `test_kanban_mcp_migration.py`: 52 tests
- Coverage matrix from research doc confirms zero behavioral gaps

### Files Changed
- `tests/test_pick_tasks.py` — deleted (1 file, -38 broken tests)

### AC Verification
- ✅ All 38 stale tests removed (intentional, research-backed)
- ✅ Gate/sort/limit coverage verified in 4 replacement files (141 tests)
- ✅ No net reduction in pick_tasks behavioral coverage — net gain of 103 tests

### Lint
- No production code changed — ruff N/A
[[2026-04-14]]
## Review Evidence

### Source Control Changes
- `tests/test_pick_tasks.py` — **deleted** (only file in scope for #848)
- Several unrelated files also present in diff (task kanban files, research docs, tests for #879–#885) — all belong to other active tasks, not part of this review scope

### File Deletion Verification
- `file_search("tests/test_pick_tasks.py")` → **no results** ✅
- `get_changed_files` diff confirms full deletion of 544-line file ✅

### Test Results (independent run)
```
pytest tests/test_pick_dispatchable_823.py tests/test_pick_dispatchable_824.py
      tests/test_server_pick_tasks_thin_wrapper_825.py tests/test_kanban_mcp_migration.py
141 passed, 0 failed ✅
```

### Coverage
- `owlbear_kanban.dispatch`: **100%** — the exact module `pick_tasks` routes through ✅
- `owlbear_mcp_kanban.server`: **92%** — adequate for MCP wrapper ✅

### Lint
- E501 in `serve/kanban/src/owlbear_kanban/engine.py:472` — **pre-existing**, not introduced by this task (task only deleted a test file, touched zero production code). Not counted as a deduction.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: All 38 tests pass or intentionally removed | File deleted; all 38 confirmed 100% fail (kanban_bin TypeError) before deletion; research doc backs removal decision | ✅ COVERED |
| AC2: gate/sort/limit coverage verified in #823, #825, migration | test_pick_dispatchable_823.py confirmed has `tdd_gate`, `limit_caps_results`, `default_limit_is_25`, `tag_filter`, `clarity_gate` tests; 141 pass | ✅ COVERED |
| AC3: No net reduction in pick_tasks behavioral coverage | 141 replacement tests vs 38 stale (0 functional) — net gain of 141 working tests | ✅ COVERED |

### TestFromAC_* Audit
No `TestFromAC_*` classes were weakened or removed by the builder. The entire file was deleted as the correct action for 100% pre-existing failures — this is the architecture-approved resolution, not a test integrity violation.

### Security Review
No production code was changed. No system boundary changes. No security concerns.

### Deductions
0 deductions.

### Verdict
**PASS #848 → docs | confidence .97**
[[2026-04-15]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Task deleted a broken test file only; zero production code changed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Internal cleanup; no external patterns used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/stale-test-pick-tasks-cleanup.md` exists and is linked in task body; follow-up #867 created (deleted a second stale file `test_pick_tasks_620.py` — distinct from `test_pick_tasks.py` deleted by #848) |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/848-*` files found)