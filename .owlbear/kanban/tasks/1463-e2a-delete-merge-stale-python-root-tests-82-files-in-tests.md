---
id: 1463
title: 'E2a: Delete/merge stale Python root tests (82 files in tests/)'
status: backlog
priority: important
created: 2026-05-09T03:32:04.142951+00:00
updated: 2026-05-09T05:24:21.612993+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- quality
parent: 1415
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Parent: #1415
Brief: .owlbear/research/1415-stale-test-cleanup.md
Research: .owlbear/research/1463-python-root-test-cleanup.md

## Acceptance Criteria
P1: 22 task-scoped files with durable equivalents merged into durables then deleted from tests/ (td:0)
P1: 21 single-file task-scoped tests renamed to drop _{id} suffix — become durable module tests (td:0)
P2: 40 multi-file groups (16 modules) merged into single durable test files (td:0)
P2: Full Python test suite passes with ≥ 3272 tests collected after cleanup (td:0)
P3: test_decisions_1218.py deleted — broken RED-phase import, security covered by _validate_decision_id (td:0)

## Scope
In scope: tests/ directory Python files only (test_*_{task_id}.py pattern)
Out of scope: serve/*/tests/, frontend tests, creating new test coverage
Retain: test_kanban_topology_1439.py (task #1439 active)

## Builder Guidance
- **File lists:** Research doc §5 has exact file-by-file tables for each batch
- **Execution order:** rename (21) → merge-then-delete (22) → merge (40/16 groups) → delete 1218 → full suite verification
- **Merge discipline:** deduplicate test function names, reconcile imports/fixtures, preserve all unique test logic — no test coverage may be lost
- **Incremental verification:** run full suite after each batch to catch regressions early
- **Baseline:** 3272 tests collected (run `uv run pytest --collect-only -q | tail -1` to verify before starting)

## Research
- Research doc: .owlbear/research/1463-python-root-test-cleanup.md
- Sources: 4 studied, 4 high-relevance (all codebase-internal)
- Recommendation: proceed as T1 autonomous cleanup (confidence: .90)

### Key Findings
1. **Count correction:** 84 task-scoped files (not 82). 83 stale, 1 active (#1439).
2. **DELETE ≠ simple delete:** 22 files with durable equivalents have significant unique tests. Must merge unique tests into durable before deleting.
3. **test_decisions_1218.py:** Dead RED-phase test — imports `_find_decision_path` which never existed. Safe to delete.
4. **Baseline:** 3272 collected tests. Suite must pass ≥ 3272 after cleanup.
5. **No naming conflicts:** All 37 rename/merge target filenames are available in tests/.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: stale test file cleanup in root tests/ |
| Interface clarity | PASS | ACs specify exact file counts, merge strategy, and numeric test baseline |
| Dependency correctness | PASS | No deps; parent #1415 depends on this task — correct |
| Module layering | N/A | No production code changes — test file rename/merge/delete only |
| TDD compliance | PASS | Gate is full suite ≥ 3272 tests; no new testable code produced |
| KISS/YAGNI | PASS | Mechanical cleanup — no new abstractions, no new code |
| Premise challenge | PASS | 84 stale files confirmed in live scan; cleanup is real maintenance need |
| Pattern consistency | PASS | Follows durable test naming convention (drop _{id} suffix) |
| Security surface | PASS | No new boundaries; 1218's security concern already covered |
| Single domain | PASS | Test infrastructure only |

### Test Depth
All AC lines: (td:0) — mechanical file operations, verified by existing suite pass
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Reason: Mechanical cleanup with no architectural decisions

### Design Diverge
- Skipped — single obvious approach (rename/merge/delete per research file lists)

### Verdict: APPROVE
### Action Taken
- Corrected P1 count 20→22 (tasks #1448/#1450 completed since original estimate)
- Clarified merge-before-delete strategy in P1 AC
- Set concrete test baseline ≥ 3272 in P2 AC
- Resolved P3 as delete (was "inspect — fix or document")
- Added Builder Guidance section with execution order and merge discipline
- Added `quality` tag for test-writer pass-through
- Verified all 37 rename/merge targets have no filename conflicts
[[2026-05-09]]
## Architecture Review

Verified all research claims against live codebase: 84 task-scoped files confirmed, all 5 durable targets exist, all 37 rename/merge target names are conflict-free. Corrected P1 count (20→22), clarified merge-before-delete strategy, set concrete ≥3272 test baseline, resolved P3 as delete. All ACs td:0 — mechanical cleanup. Added `quality` tag for test-writer pass-through and Builder Guidance section.

Verdict: APPROVE → todo
[[2026-05-09]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Task tagged `quality`; AC describes mechanical file rename/merge/delete operations in tests/ with no new testable Python interfaces.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Implementation: attempted two consolidation strategies in `tests/` and rolled back fully after regression evidence.
- Files changed: none in final workspace state for this task (all test-file edits reverted/removed).
- Baseline evidence (pre-change gate): `uv run pytest tests/ serve/ -m "not api and not e2e" --ignore=tests/test_decisions_1218.py -q --tb=line -n 0` reports `551 failed, 4686 passed, 4 skipped`.
- Baseline collect-only count: `3277 tests collected` with `--ignore=tests/test_decisions_1218.py`.
- Attempt evidence:
  - direct content merge strategy: `714 failed, 4427 passed, 4 skipped`, collect-only dropped to `3222`.
  - helper-import strategy: `656 failed, 4485 passed, 4 skipped`, collect-only `3222`.
- Conclusion: AC line requiring full Python suite pass after cleanup is not satisfiable in current branch state because the baseline suite is already red independent of task 1463 operations.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-baseline AC for #1463 to use delta-based acceptance (e.g., no additional failures + collected-count floor) or provide a known-green commit SHA as execution base. | `.owlbear/kanban/tasks/1463-e2a-delete-merge-stale-python-root-tests-82-files-in-tests.md` | Baseline gate is already red: `551 failed, 4686 passed, 4 skipped` before cleanup. |
| 2 | planner | Split #1463 into smaller merge groups with explicit verification checkpoints and conflict policy for duplicate test symbols/fixtures. | `.owlbear/research/1463-python-root-test-cleanup.md`, `tests/` | Large-batch merge attempts caused systemic regressions (`714` and `656` fails) despite rollback. |
| 3 | test-writer | Provide consolidation contract for multi-file groups: duplicate test-name handling, fixture collision policy, and expected post-merge collection count per target module. | `tests/test_*_{id}.py` merge groups in research §5b/§5c | Collection count dropped from `3277` to `3222` in both merge strategies, indicating unresolved merge semantics. |