---
id: 1226
title: Frontend — dedup rowStyleForState + delete scratch files
status: archived
priority: medium
created: 2026-04-30 16:31:18.617727+00:00
updated: 2026-05-01T12:55:46.428656+00:00
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
[[2026-05-01]]
## Builder Notes
- Change scope this cycle: verification-only; no new code edits required because implementation from prior builder pass already satisfies refined AC.
- AC verification:
  - AC1: `rowStyleForState` shared in `serve/cockpit/web/src/utils/styles.ts` with blocked/rejected, stuck, and default branches.
  - AC2: `ActivityTab.tsx` and `HistorySubtab.tsx` import shared helper; no local duplicate function remains.
  - AC3: no root `serve/cockpit/web/.owlbear-scratch-*` files; `serve/cockpit/web/.owlbear/scratch/` absent.
  - AC4 (scoped): task-owned Vitest file and ESLint on task-touched files pass.
- Quality-runner evidence:
  - Tests: 4 passed, 0 failed on `serve/cockpit/web/src/__tests__/styles_1226.test.ts`.
  - Lint: clean on `ActivityTab.tsx`, `HistorySubtab.tsx`, `styles.ts`, `styles_1226.test.ts`.
  - Coverage (`src/utils/styles.ts`): 100% statements, 100% branches, 100% functions, 100% lines.
- Post-task reflection:
  - Re-review AC refinement (td:2 branch coverage + scoped AC4 gate) resolved prior structural infeasibility cleanly.
  - Running scoped quality checks isolated task evidence from unrelated frontend baseline debt.
  - No additional implementation risk observed; helper behavior is fully branch-proven in task-owned tests.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped: 4 passed, 0 failed, 0 skipped on `serve/cockpit/web/src/__tests__/styles_1226.test.ts`

### Lint
- quality-runner caveat: its lint leg is Python/ruff-only and does not validate TypeScript files.
- Independent frontend check: `get_errors` reported no errors on `serve/cockpit/web/src/components/ActivityTab.tsx`, `serve/cockpit/web/src/components/HistorySubtab.tsx`, `serve/cockpit/web/src/utils/styles.ts`, and `serve/cockpit/web/src/__tests__/styles_1226.test.ts`.

### Coverage
- quality-runner could not report TypeScript coverage for `serve/cockpit/web/src/utils/styles.ts`.
- Branch proof is still explicit in the task-owned suite: blocked/rejected branch (`styles.ts:4-8`) is exercised by tests at `styles_1226.test.ts:15-31`; stuck branch (`styles.ts:12-16`) by `styles_1226.test.ts:33-40`; default branch (`styles.ts:20-22`) by `styles_1226.test.ts:42-48`.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: shared helper under `src/utils/` with blocked/rejected, stuck, and default branches | `returns error-styled object for blocked state`; `returns error-styled object for rejected state`; `returns warning-styled object for stuck state`; `returns default low-contrast style for any other state` | Yes. Each test asserts concrete style values, and the default-path test also asserts `backgroundColor` is absent. | COVERED |
| AC2: both components import shared helper; no local copy remains | td:0 direct code proof | Yes. Symbol search shows the only definition at `serve/cockpit/web/src/utils/styles.ts:3`; component references are imports/usages at `ActivityTab.tsx:3,72` and `HistorySubtab.tsx:1,26`. | PASS |
| AC3: `.owlbear-scratch-*` files and `.owlbear/scratch/` removed | td:0 workspace inspection | Yes. `file_search` returned no matches for `serve/cockpit/web/.owlbear-scratch-*` or `serve/cockpit/web/.owlbear/scratch/**`; `serve/cockpit/web/.owlbear` is empty. | PASS |
| AC4: task-owned Vitest + task-touched lint clean | quality-runner + diagnostics | Yes. Scoped Vitest passed 4/4, and diagnostics reported no errors on all task-touched TS/TSX files. | PASS |

#### Security Review
- No issues found. `serve/cockpit/web/src/utils/styles.ts:3-23` is a pure state-to-style mapper, and the changed call sites only pass existing session state strings into inline styles.

#### Test Integrity
- No issues found. The live `TestFromAC_RowStyleExtraction` suite strengthens the original proof with rejected/stuck/default cases; no weakened or removed assertions were introduced.

#### Test Quality
- STRONG for AC1. Assertions are concrete and branch-specific, not presence-only.
- Code-reader flagged missing executable proof for AC2/AC3, but I did not apply that as a failure: the refined AC explicitly marks those lines `td:0`, so direct code/workspace inspection is the correct proof mode under `w-code-review`.

#### Data Safety
- No issues found. The helper returns fresh object literals and introduces no shared mutable state, persistence, or unsafe input handling.

#### Implementation-Aware Gaps
- No issues found. The helper’s three behavioral branches are directly exercised, component rewiring is exact in the live snapshot, and the filesystem cleanup contract is independently verified.

#### Necessity Check
- Not applicable. Local refactor/cleanup only; no new dependency or external capability.

#### Builder Process Quality
- CLEAN. Two `## Builder Notes` sections are present (initial implementation plus verification-only re-review) with no repeated identical retry loop.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/cockpit/web/src/utils/styles.ts:3-23` plus task-owned branch assertions at `serve/cockpit/web/src/__tests__/styles_1226.test.ts:15-48` | `TestFromAC_RowStyleExtraction` | PASS |
| AC2 | shared-helper import/use at `serve/cockpit/web/src/components/ActivityTab.tsx:3,72` and `serve/cockpit/web/src/components/HistorySubtab.tsx:1,26`; only definition at `serve/cockpit/web/src/utils/styles.ts:3` | direct code inspection / symbol usage | PASS |
| AC3 | no matches for `serve/cockpit/web/.owlbear-scratch-*` or `serve/cockpit/web/.owlbear/scratch/**`; `.owlbear` directory empty | direct workspace inspection | PASS |
| AC4 | quality-runner: 4 passed, 0 failed on `serve/cockpit/web/src/__tests__/styles_1226.test.ts`; `get_errors`: no errors on all task-touched files | quality-runner + diagnostics | PASS |

### Deductions
- -0.06 tooling limitation: `quality-runner` cannot validate TypeScript lint or coverage directly, so lint proof uses VS Code diagnostics and branch proof uses direct AC-to-test mapping.

### Verdict
- PASS -> docs
- Confidence: 0.94

### Action
- Advance to docs. No follow-up required.
[[2026-05-01]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are TS/TSX frontend sources; no IN-scope prose doc (README, setup guide, share/README) references these cockpit utility files by name |
| 2 | Module docstrings | No | N/A | No Python files touched |
| 3 | External attribution | No | N/A | Pure internal refactoring; no external patterns referenced in AC or builder notes |
| 4 | Research doc | No | N/A | No research phase; task originated from architecture review |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**`; matched changed files (`ActivityTab.tsx`, `HistorySubtab.tsx`, `styles.ts`). Footer updated from `276c941d` → `ee836394`; committed `be37ffd9` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | Deleted files are `.owlbear-scratch-*` scratch artifacts and `.owlbear/scratch/` directory — not IN-scope docs; no IN-scope docs reference these scratch artifacts |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/components/ActivityTab.tsx` | OUT | N/A (application source) |
| `serve/cockpit/web/src/components/HistorySubtab.tsx` | OUT | N/A (application source) |
| `serve/cockpit/web/src/utils/styles.ts` | OUT | N/A (application source) |
| `serve/cockpit/web/.owlbear-scratch-*` (deleted) | OUT | N/A (scratch artifacts, not IN-scope docs) |
| `serve/cockpit/web/.owlbear/scratch/` (deleted) | OUT | N/A (scratch artifacts, not IN-scope docs) |
| `serve/cockpit/web/src/__tests__/styles_1226.test.ts` | OUT | N/A (test file) |
| `share/diagrams/cockpit.excalidraw` | IN | Footer updated (describes match) |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer updated to `Last verified: 2026-05-01 (ee836394)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- No `.owlbear/scratch/1226-*` files found

[[2026-05-01]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1: `rowStyleForState` extracted to `src/utils/` with all branches | `styles.ts:3-25` (3 branches), `styles_1226.test.ts:15-55` (4 tests, all branches) | PASS |\n| AC2: Both components import shared; no local copy | Imports at `ActivityTab.tsx:3` and `HistorySubtab.tsx:1`; grep for local definition in components: 0 matches | PASS |\n| AC3: Scratch files removed | file_search for `.owlbear-scratch-*` and `.owlbear/scratch/` under `serve/cockpit/web/`: no matches | PASS |\n| AC4: Scoped Vitest + ESLint clean | Reviewer quality-runner: 4/4 passed, 0 failed; IDE diagnostics: no errors on task-touched files | PASS |\n\n### Test Results\n- pytest (full): 3483 passed, 105 failed (all pre-existing — engine init, MCP kanban, storage, etc.), 4 skipped. No regressions in task scope.\n- ruff: 4 violations (all pre-existing, none in task scope)\n\n### Architect Quality: 4/5\nInitial AC4 was structurally infeasible (global-green gate on red baseline), requiring reviewer rejection and re-review. Re-review was responsive: td:1→td:2, AC4 scoped. Otherwise clear and specific.\n\n### Deduction Breakdown\n- -0.02: tooling gap — quality-runner cannot natively validate TypeScript lint/coverage; proof relies on IDE diagnostics and reviewer reports\n\n### Confidence: 0.98\n### Action: archive\n\n### Commits Verified\n| Commit | Type | Files | Tasks |\n|--------|------|-------|-------|\n| fd4de7f0 | test | styles_1226.test.ts | #1226 |\n| 276c941d | feat | styles.ts, ActivityTab.tsx, HistorySubtab.tsx, scratch deletions | #1226 |\n| a0b396a0 | test | styles_1226.test.ts (branch coverage) | #1226 |