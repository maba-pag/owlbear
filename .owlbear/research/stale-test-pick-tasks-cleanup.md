# Stale test_pick_tasks.py cleanup — coverage overlap analysis

> **Owning task:** #848 — Clean up stale test_pick_tasks.py — 38 tests broken by kanban_bin migration
> **Date:** 2026-04-13 **Status:** Complete

## 1. Context and Question

`tests/test_pick_tasks.py` has 38 tests (consolidated from #620, #621, #628) that all fail with `TypeError: AppContext.__init__() got an unexpected keyword argument 'kanban_bin'`. The tests use the pre-Phase-2 pattern of mocking `_run_kanban` CLI calls. Phase 2 engine extraction replaced this with `KanbanEngine` and Phase 3 moved gate logic to `owlbear_kanban.dispatch.pick_dispatchable()`.

**Question:** Can these 38 tests be safely removed, or must some be updated to preserve unique coverage?

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `tests/test_pick_tasks.py` (38 tests, 8 classes) | 1.0 | Full behavioral map of stale tests |
| S2 | `tests/test_pick_dispatchable_823.py` (37 tests) | .95 | Gate logic, sort, limit, tag at engine layer |
| S3 | `tests/test_pick_dispatchable_824.py` (28 tests) | .90 | Rank constants, blocked/unclaimed exclusion |
| S4 | `tests/test_server_pick_tasks_thin_wrapper_825.py` (14 tests) | .95 | Delegation, response format, MCP contract |
| S5 | `tests/test_kanban_mcp_migration.py::TestFromAC_PickTasks` (4 tests) | .85 | Integration-level delegation + format |
| S6 | `serve/kanban/src/owlbear_kanban/dispatch.py` | .95 | Implementation: 2 gates (TDD, clarity), no atomicity gate |
| S7 | `serve/kanban/src/owlbear_kanban/models.py` L77 | .80 | `body: str = ""` — Pydantic field, null coerced by model |

## 3. Analysis — Test-by-Test Coverage Overlap

### 3.1 Coverage Matrix

| Stale class (tests) | Behavior tested | Replacement coverage | Gap? |
|---|---|---|:---:|
| BasicPick (5) | Response format: dispatch key, task_id/status, int type, multi-status, exact keys | S4 AC3 (4 tests) + S5 (2 tests) | No |
| GateFiltering (8) | Atomicity (2), TDD (2), Clarity (4) | S2 AC2 TDD (5), S2 AC3 Clarity (8). Atomicity intentionally removed from dispatch.py | No |
| Limit (4) | limit=5 caps, default=25 | S2 AC6 (4 tests) | No |
| SortOrder (3) | Priority sort, status sort, composite sort | S2 AC4 (3), S2 AC5 (4 tests) | No |
| EdgeCases (4) | Empty board, all-fail, nonzero-rc error, malformed-JSON error | S4 AC3 empty-board; rc/JSON errors obsolete (no CLI calls) | No |
| BoardFlags (6) | `--unblocked`, `--not-blocked`, `--unclaimed`, `--json`, `--archived` CLI flags | Obsolete — S3 blocked/unclaimed tests at engine layer | No |
| NullBodySafety (4) | body=None doesn't crash, fails gates correctly | Obsolete — S7: Task.body is `str=""`, filesystem reader always returns str | No |
| TagPassthrough (4) | `--tag` CLI flag position and value | Obsolete CLI pattern; S2 AC7 (5 tests) covers tag filtering at engine layer | No |

### 3.2 Summary Counts

| Category | Count | Details |
|---|:---:|---|
| Fully covered by replacement tests | 24 | Gates, sort, limit, format, tag filter |
| Obsolete (tested `_run_kanban` CLI) | 10 | BoardFlags (6), EdgeCases rc/JSON (2), TagPassthrough CLI (2) |
| Removed by design (atomicity gate dropped) | 2 | Atomicity gate not in dispatch.py |
| Obsolete (null body via JSON) | 2 | Task model enforces `body: str`, filesystem always str |
| **Total** | **38** | |

### 3.3 Net coverage impact

**Zero net reduction.** All 24 behavioral tests have direct equivalents in the replacement suite. The remaining 14 test patterns that were removed/obsoleted (CLI mocking, atomicity gate, JSON null body) are architecturally irrelevant after the engine extraction.

The replacement suite is strictly **stronger**: 93 passing tests vs. 38, using real filesystem engines instead of CLI mocks, with additional coverage for blocked exclusion, unclaimed exclusion, non-impl tag exemptions, and rank constant contracts.

## 4. Recommendation

**Remove `test_pick_tasks.py` entirely.** Confidence: **0.95**.

No behavioral test should be updated — the stale tests mock infrastructure (`_run_kanban`, `AppContext(kanban_bin=...)`) that no longer exists. Updating them to the new pattern would duplicate the 93 tests already in place.

Challenge: FALLBACK — challenger subagent not available.

## 5. Follow-up Tasks

- Follow-up #1: Delete `tests/test_pick_tasks.py` (38 broken tests, zero unique coverage).
