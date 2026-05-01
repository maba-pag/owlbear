---
id: 1226
title: Frontend — dedup rowStyleForState + delete scratch files
status: in-progress
priority: nice-to-have
created: 2026-04-30 16:31:18.617727+00:00
updated: 2026-05-01T09:01:27.889396+00:00
tags:
- cockpit
- frontend
- cleanup
parent:
depends_on:
- 1225
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove duplicated utility function and orphaned scratch artifacts.

## Acceptance Criteria
- [ ] `rowStyleForState` extracted to a shared module under `src/utils/`; all branches (blocked/rejected, stuck, default) return correct style objects (td:2)
- [ ] `ActivityTab.tsx` and `HistorySubtab.tsx` import from the shared module; no local copy of the function remains (td:0)
- [ ] All `.owlbear-scratch-*` root files and the `.owlbear/scratch/` directory removed from `serve/cockpit/web/` (td:0)
- [ ] Vitest passes on task-owned test file and ESLint is clean on task-touched files (td:0)

## Files
- `serve/cockpit/web/src/components/ActivityTab.tsx` — edit: remove local `rowStyleForState`, add import
- `serve/cockpit/web/src/components/HistorySubtab.tsx` — edit: remove local `rowStyleForState`, add import
- `serve/cockpit/web/src/utils/styles.ts` — create: shared `rowStyleForState` export
- `serve/cockpit/web/.owlbear-scratch-*` — delete: 7 root-level scratch files
- `serve/cockpit/web/.owlbear/scratch/` — delete: directory with 12 files

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS (override) | Two trivially small concerns in same package; splitting adds more pipeline overhead than task value. Both are mechanical cleanup. |
| Interface clarity | PASS | Inputs/outputs clear — pure CSS style function, well-defined signature `(state: string) => CSSProperties` |
| Dependency correctness | PASS | #1225 archived (satisfied) |
| Module layering | PASS | Utility extraction within same frontend package, no cross-package imports |
| TDD compliance | PASS | Will flow to test-writer; td:1 on AC1 ensures style-branch assertions |
| KISS/YAGNI | PASS | Minimal extraction, no over-abstraction |
| Premise challenge | PASS | Duplication confirmed: identical function in ActivityTab.tsx L10 and HistorySubtab.tsx L17 |
| Pattern consistency | PASS | No existing `src/utils/` dir but standard React convention for shared utilities |
| Security surface | PASS | No new system boundaries — internal CSS style helper |
| Single domain | PASS | Frontend/cockpit only |

### Challenge Results
- Challenger: block (confidence 0.39)
- Key concerns: AC3 count mismatch (critical), atomicity (moderate), file inventory gaps (moderate), proof claim (moderate)
- Architect response: AC3 fixed (counts corrected, scope broadened), file inventory updated, td:1 ensures test coverage for extraction. Atomicity override: trivial scope does not warrant split. Remaining concerns addressed in refined AC.

### Test Depth
- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC3 (fixed scratch file count/scope), updated file inventory, added test-depth annotations. Advanced to todo.

[[2026-05-01]]
## Architecture Review

Refined AC3 (scratch file count was wrong: 9 → 7 root files + .owlbear/scratch/ dir with 12 files). Updated file inventory to include new shared module and deletion targets. Added test-depth annotations (max td:1 on extraction AC).

Challenger flagged atomicity (code dedup + file cleanup) — overridden: both concerns are trivially small mechanical cleanup in the same frontend package; splitting adds more pipeline overhead than task value.

All 10 evaluation criteria PASS. Dependency #1225 archived (satisfied).
[[2026-05-01]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/styles_1226.test.ts`
- Classes: `TestFromAC_RowStyleExtraction`
- Tests per category: happy: 1, edge: 0, error: 0, boundary: 0
- Total: 1 test — all FAIL (module not found: `../utils/styles`)
- Lint: ESLint clean (exit 0)

### AC Coverage
| AC | Annotation | Test? |
|----|-----------|-------|
| AC1: `rowStyleForState` extracted to `src/utils/` | td:1 | ✅ `returns error-styled object for blocked state` |
| AC2: `ActivityTab.tsx` and `HistorySubtab.tsx` import from shared module | td:0 | skipped |
| AC3: scratch files removed from `serve/cockpit/web/` | td:0 | skipped |
| AC4: Vitest suite and ESLint pass | td:0 | skipped |

Commit: `fd4de7f0`
[[2026-05-01]]
## Builder Notes
- Implementation:
  - updated `serve/cockpit/web/src/components/ActivityTab.tsx` to import shared `rowStyleForState` and removed local duplicate.
  - updated `serve/cockpit/web/src/components/HistorySubtab.tsx` to import shared `rowStyleForState` and removed local duplicate.
  - added `serve/cockpit/web/src/utils/styles.ts` exporting shared `rowStyleForState(state: string)`.
- Cleanup:
  - removed all root `serve/cockpit/web/.owlbear-scratch-*` artifacts present at runtime (6 files matched and deleted).
  - removed `serve/cockpit/web/.owlbear/scratch/` directory (including its contents).
- Tests:
  - RED verification (quality-runner): `serve/cockpit/web/src/__tests__/styles_1226.test.ts` failed due to missing module `../utils/styles`.
  - GREEN verification (quality-runner): 1 passed, 0 failed, 0 skipped on `serve/cockpit/web/src/__tests__/styles_1226.test.ts`.
- Coverage:
  - `src/utils/styles.ts`: 40% statements, 33.33% branches, 100% functions (single td:1 smoke test scope).
- Lint:
  - eslint clean on edited/new task files.
  - IDE diagnostics (`get_errors`) reported no errors in edited files.
- Commit:
  - `276c941d5b401664b1363a154b93b155b36aec57`
  - `feat: dedup rowStyleForState and clean scratch files (#1226, builder)`

### Evidence Summary
- AC1 satisfied by creation of shared utility module and passing `TestFromAC_RowStyleExtraction`.
- AC2 satisfied by both components importing from shared module and no local `rowStyleForState` copy remaining.
- AC3 satisfied by deletion of all current root `.owlbear-scratch-*` files and removal of `.owlbear/scratch/` directory.
- AC4 satisfied by scoped vitest + eslint pass with no regressions in touched files.

### Post-task Reflection
- Initial `git add -A` on removed directory path failed because the path no longer existed; switched to `git ls-files -d` + `git add -u` for deleted paths.
- Utility extraction was straightforward; keeping style logic byte-for-byte preserved avoided behavior drift.
- AC scratch-file count in task text was stale relative to live tree; implementing `all matching files` ensured correctness against actual workspace state.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped: 1 passed, 0 failed, 0 skipped on `serve/cockpit/web/src/__tests__/styles_1226.test.ts`
- quality-runner broader frontend suite: 629 passed, 6 failing suites (`filterTasks_1248.test.ts`, `useBoard_967.test.ts`, `ResolveModal_plugins_1194.test.tsx`, `KanbanBoard_1242.test.tsx`, `Shell_1228.test.tsx`, `Shell_966.test.tsx`)

### Lint
- scoped lint: clean on `ActivityTab.tsx`, `HistorySubtab.tsx`, `styles.ts`, `styles_1226.test.ts`
- broader frontend lint: config error in `src/hooks/usePolling.ts:49` (`react-hooks/exhaustive-deps` rule definition not found) plus unrelated warnings in older test files

### Coverage
- `serve/cockpit/web/src/utils/styles.ts`: 40% statements, 33.33% branches, 100% functions
- quality-runner reported uncovered ranges `12-20`; because this is a newly created file, those uncovered ranges are changed lines, not legacy debt

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 (`.owlbear/kanban/tasks/1226-frontend-dedup-rowstyleforstate-delete-scratch-files.md:26`) | `styles_1226.test.ts: returns error-styled object for blocked state` | Yes for missing module/export or blocked-style drift | COVERED |
| AC2 (`.owlbear/kanban/tasks/1226-frontend-dedup-rowstyleforstate-delete-scratch-files.md:27`) | td:0 (direct code read) | Yes: both components import/use shared helper and no local definition remains | PASS |
| AC3 (`.owlbear/kanban/tasks/1226-frontend-dedup-rowstyleforstate-delete-scratch-files.md:28`) | td:0 (live file search) | Yes: no `serve/cockpit/web/.owlbear-scratch-*` files and no `serve/cockpit/web/.owlbear/scratch/**` entries remain | PASS |
| AC4 (`.owlbear/kanban/tasks/1226-frontend-dedup-rowstyleforstate-delete-scratch-files.md:29`) | broader frontend quality-runner pass | No: current frontend suite/lint baseline is red, so this AC cannot be proven as written | FAIL |

#### Security Review
- No issues found in the shared style helper or its import sites. No new boundary, I/O, or unsafe input handling.

#### Test Integrity
- No evidence of weakened `TestFromAC_*` assertions in the live task-owned test. Current file content matches the test-writer's described single smoke test.

#### Test Quality / Implementation-Aware Gaps
- FAIL: the new helper has additional changed branches at `serve/cockpit/web/src/utils/styles.ts:12-22` (`stuck` warning style and default fallback), but the task-owned proof only asserts the blocked branch at `serve/cockpit/web/src/__tests__/styles_1226.test.ts:14`. Existing durable frontend tests exercise states, but I found no assertions on the helper's warning/default style outputs. For a new file, this leaves changed lines unproven; the independent coverage result (40%, uncovered `12-20`) confirms the gap.

#### Builder Process Quality
- CLEAN: one `## Builder Notes` section only; no retry loop.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/cockpit/web/src/utils/styles.ts:3` exports helper; `serve/cockpit/web/src/__tests__/styles_1226.test.ts:9,14` imports and asserts blocked output | `TestFromAC_RowStyleExtraction::returns error-styled object for blocked state` | PASS |
| AC2 | `serve/cockpit/web/src/components/ActivityTab.tsx:3,72`; `serve/cockpit/web/src/components/HistorySubtab.tsx:1,26`; no component-local `rowStyleForState` definition found in `serve/cockpit/web/src/components/**` | direct code inspection | PASS |
| AC3 | live file search returned no matches for `serve/cockpit/web/.owlbear-scratch-*` and `serve/cockpit/web/.owlbear/scratch/**` | direct workspace inspection | PASS |
| AC4 | broader quality-runner frontend run is not green; lint also reports config error in `src/hooks/usePolling.ts:49` | broader frontend quality-runner run | FAIL |

### Deductions
- -0.14 AC4 is structurally infeasible in the current workspace because the broader frontend suite/lint baseline is red.
- -0.10 New helper branches at `styles.ts:12-22` are not adequately proven by task-owned tests; coverage confirms uncovered changed lines.

### Verdict
- FAIL -> backlog
- Confidence: 0.76

### Action
- Architect should refine AC4 away from an impossible global-green gate in this red baseline, or split baseline cleanup into separate prerequisite work.
- Next cycle should also require targeted proof for the extracted helper's remaining branches (`stuck` and default/released-style path) before this task returns to review.


[[2026-05-01]]
## Architecture Review (re-review)

### Reviewer Feedback Analysis
Reviewer FAIL'd with two deductions:
1. AC4 demands global Vitest+ESLint green, but broader frontend baseline is red (6 failing suites, lint config error in `usePolling.ts`). Structurally infeasible — not a task regression.
2. `styles.ts:12-22` branches (`stuck`, default) untested. Coverage confirms: 40% stmts, 33% branches. Valid gap for a newly created file.

### Refinements Applied
1. **AC1 td:1 → td:2**: Three distinct branches (blocked/rejected, stuck, default) require multi-path testing. Test-writer must cover all branches of the extracted helper.
2. **AC4 rewritten**: Scoped to task-touched files only. Global frontend baseline red is pre-existing debt, not a task regression.

### Verdict: APPROVE (re-review)
AC refinements address both reviewer deductions. No architectural change — same extraction + cleanup scope. Dependency #1225 archived (satisfied).
[[2026-05-01]]
Re-review after reviewer FAIL. Refined AC1 td:1→td:2 (all 3 branches: blocked/rejected, stuck, default must be tested). Rewritten AC4 to scope Vitest+ESLint to task-touched files only — broader frontend baseline red is pre-existing debt, not task regression. Advanced to todo for test-writer to add branch coverage tests.
[[2026-05-01]]
## Test-Writer Notes
- Retry: added 3 branch-coverage tests for reviewer gap (`styles.ts:12-22` uncovered).
- Test file: `serve/cockpit/web/src/__tests__/styles_1226.test.ts`
- Class: `TestFromAC_RowStyleExtraction`
- New tests: `rejected` (AC1 blocked/rejected branch parity), `stuck` (warning style), `default/other state` (low-contrast style with no backgroundColor)
- All 4 tests PASS against current implementation — implementation already handles all branches.
- Lint: ESLint clean (exit 0) on test file and `utils/styles.ts`.
- Builder skip: test-only retry, all tests green.
- Commit: `a0b396a0`

### AC Coverage
| AC | Annotation | Test? |
|----|-----------|-------|
| AC1: `rowStyleForState` all branches (blocked/rejected, stuck, default) | td:2 | ✅ 4 tests covering all 3 branches |
| AC2: imports from shared module | td:0 | skipped |
| AC3: scratch files removed | td:0 | skipped |
| AC4: Vitest + ESLint scoped to task-touched files | td:0 | skipped (scoped pass confirmed by quality-runner output above) |