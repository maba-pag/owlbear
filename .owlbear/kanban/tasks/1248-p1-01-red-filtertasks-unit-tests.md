---
id: 1248
title: 'P1-01: RED — filterTasks unit tests'
status: review
priority: critical
created: 2026-05-01T04:34:42.374850+00:00
updated: 2026-05-01T09:11:42.060823+00:00
tags:
- phase-1
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test suite in Vitest covering filterTasks:
  - Text dimension: case-insensitive substring match on task.title; empty string passes all
  - Priority dimension: exact match on task.priority; empty string passes all
  - Tags dimension: AND semantics — task must have ALL selected tags; empty array passes all
  - Blocked dimension: when true, only blocked tasks pass; when false, all pass
  - AND combination: multiple active dimensions all apply simultaneously
  - Edge cases: task with empty tags array vs non-empty filter; task with undefined fields
- All tests fail (RED) — no filterTasks implementation exists yet
- FilterState type interface exported for downstream consumers

## In Scope
- Unit test file for filterTasks
- FilterState type definition

## Out of Scope
- filterTasks implementation (next task)
- React components
- Integration with KanbanBoard

Brief: see parent #1247
[[2026-05-01]]
## Research
- Research doc: .owlbear/research/filter-tasks-red-1248.md
- Sources: 4 studied, 2 high-relevance (Task interface, optimistic.test.ts pattern)
- Recommendation: Test file at `src/__tests__/filterTasks_1248.test.ts`, import from `../utils/filterTasks`, ~16 test cases covering all AC dimensions (confidence: 0.85)
- Follow-up tasks created: none needed (successor #1249 already exists)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial T1 task, no competing options
- Key findings: Task type already exports all needed fields; Vitest globals enabled; task-ID suffix naming convention established in codebase
[[2026-05-01]]

## Architecture Review

### Refined AC (supersedes original — test-writer follows this version)

- Test file at `src/__tests__/filterTasks_1248.test.ts` with Vitest covering filterTasks: (td:2)
  - Text dimension: case-insensitive substring match on task.title; empty string passes all
  - Priority dimension: exact match on task.priority; empty string passes all
  - Tags dimension: AND semantics — task must have ALL selected tags; empty array passes all
  - Blocked dimension: when true, only blocked tasks pass; when false, all pass
  - AND combination: multiple active dimensions all apply simultaneously
  - Edge cases: task with empty tags array vs non-empty filter; task with missing fields (e.g., tags is undefined) treated as non-matching
- All tests compile and execute (collection succeeds) but fail on assertions (td:0)
  - RED scaffolding: create stub source file `src/utils/filterTasks.ts` exporting FilterState type + filterTasks function returning empty array (stub for RED)
  - Tests import from `../utils/filterTasks` — import must resolve, assertions must fail
- FilterState type interface defined and exported from `src/utils/filterTasks.ts` for downstream consumers (td:1)
  - Shape: `{ text: string; priority: string; tags: string[]; blocked: boolean }`

#### In Scope (refined)
- Unit test file: `src/__tests__/filterTasks_1248.test.ts`
- Stub source file: `src/utils/filterTasks.ts` (FilterState type + stub filterTasks returning `[]`)

#### Out of Scope (unchanged)
- filterTasks implementation (task #1249)
- React components
- Integration with KanbanBoard

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests + type definition only; implementation deferred to #1249 |
| Interface clarity | PASS (after refine) | Locked import path to `../utils/filterTasks`, specified FilterState shape, clarified RED mechanism |
| Dependency correctness | PASS | No dependencies; first task in chain. #1249 depends on this. |
| Module layering | PASS | Pure function in `utils/`, tests in `__tests__/`. No upward imports. |
| TDD compliance | PASS | This IS the RED phase task; GREEN successor #1249 exists |
| KISS/YAGNI | PASS | ~16 test cases for 4 dimensions + AND + edges. No over-testing. |
| Premise challenge | PASS | No existing filterTasks code. ActivityTab.tsx has unrelated applyFilter helper (different domain). |
| Pattern consistency | PASS | Follows `{feature}_{taskId}.test.ts` naming, TestFromAC_ prefix, Vitest globals |
| Security surface | PASS | Pure in-memory filter. No system boundaries. |
| Single domain | PASS | cockpit-web frontend only |

### Failure Mode Map
N/A — test file and type definition; no runtime failure modes.

### Design Diverge
Skipped — single clear approach (standard Vitest test file + stub source). No competing designs.

### Challenge Results
- Challenger: reconsider (0.57)
- Key concerns: (1) collection-error RED vs assertion-failure RED, (2) FilterState deliverable location, (3) undefined-fields contract ambiguity, (4) utils/ vs lib/ path instability
- Architect response: accepted — all four concerns addressed via AC refinement. RED scaffolding stub added. Path locked to `utils/filterTasks.ts`. Undefined-fields edge case clarified as "missing fields treated as non-matching."

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC to clarify RED mechanism (executable tests with assertion failures, not collection errors), locked import path to `utils/filterTasks.ts`, added stub source file as in-scope deliverable, clarified undefined-fields edge case. Advanced to todo.
[[2026-05-01]]
Architecture review complete. Refined AC to address challenger concerns (RED mechanism, FilterState location, path lock, undefined-fields contract). All 10 criteria PASS. Advanced to todo.
[[2026-05-01]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts`
**Class:** `TestFromAC_FilterTasks`
**Commit:** ae32710d

### Tests by category (18 total)

| Category | Count | Tests |
|----------|-------|-------|
| Happy (text match, priority match, tags match) | 5 | substring match, case-insensitive, partial, exact priority, all tags |
| Boundary (empty filter pass-all) | 3 | text='', priority='', tags=[] |
| Error/Exclusion (non-matching excludes) | 4 | non-matching text/priority/tags retains other tasks |
| Blocked (boolean gate) | 2 | blocked=true only-blocked, blocked=false all-pass |
| AND combination | 2 | multi-dimension AND, all-pass default |
| Edge cases | 2 | undefined tags field, empty tags array vs filter |

**Total: 18 tests, all RED**

### AC Coverage

| AC line | Tests |
|---------|-------|
| Text: case-insensitive substring; '' passes all | 3 tests (match, case-insensitive, empty passes all, partial, non-matching excludes) |
| Priority: exact match; '' passes all | 3 tests (exact match, empty passes all, non-matching excludes) |
| Tags: AND semantics; [] passes all | 4 tests (all present, missing one excluded, empty passes all, empty-tags excluded) |
| Blocked: true=only blocked, false=all pass | 2 tests |
| AND combination | 2 tests |
| Edge: empty tags array, undefined tags | 2 tests |
| FilterState type exported | Covered by import at line 19 |

### Current failure mode

Tests currently fail at collection stage: `Failed to resolve import "../utils/filterTasks"` — stub source file does not exist.

**Builder must create stub BEFORE verifying assertion failures:**

```typescript
// serve/cockpit/web/src/utils/filterTasks.ts
import type { Task } from '../hooks/useBoard'

export interface FilterState {
  text: string
  priority: string
  tags: string[]
  blocked: boolean
}

// Stub: always returns [] — real implementation in #1249
export function filterTasks(_tasks: Task[], _filter: FilterState): Task[] {
  return []
}
```

Once stub exists, all 18 tests fail on assertions (expect non-empty result, get []).

**Path-guard constraint:** Test-writer mode blocks writes to `src/utils/` — builder creates the stub as first action.
[[2026-05-01]]
## Builder Notes
- Implementation: added [serve/cockpit/web/src/utils/filterTasks.ts](serve/cockpit/web/src/utils/filterTasks.ts) with exported `FilterState` interface and RED-phase `filterTasks` stub returning `[]`.
- RED verification (pre-change, via quality-runner): collection error due to missing module import `../utils/filterTasks` from [serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts](serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts#L19).
- RED verification (post-change, via quality-runner): 18/18 tests fail on assertions (no collection errors), confirming executable RED state.
- Lint: clean for [serve/cockpit/web/src/utils/filterTasks.ts](serve/cockpit/web/src/utils/filterTasks.ts) and [serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts](serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts) (0 violations).
- Coverage: not applicable for this scoped frontend RED run.
- Commit: `38d7d832104da4fd38fee4b687c3f3a7358510a6` with only [serve/cockpit/web/src/utils/filterTasks.ts](serve/cockpit/web/src/utils/filterTasks.ts).

### Reflection
- Problem: task started at collection-error RED because `src/utils/filterTasks.ts` was missing.
- Workaround: introduced minimal stub to shift failure mode from collection to assertion failures.
- Pattern: for RED tasks in frontend Vitest, scaffolding import targets first to ensure executable failing assertions.
- Quality gap: none observed; failure mode now fully aligned with AC for successor GREEN task #1249.
[[2026-05-01]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 0 passed, 18 failed, 0 skipped in `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts`.
- Failure mode is correct for this RED task: tests compile and execute, and fail on assertions (`expected [] to deeply equal [...]`) against the stub implementation. No collection/import failure remains.

### Lint
- quality-runner frontend lint: ESLint clean for `serve/cockpit/web/src/utils/filterTasks.ts` and `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts`.
- VS Code diagnostics: no errors in either file.

### Coverage
- Scoped Vitest coverage unavailable: provider is not configured in `serve/cockpit/web/vite.config.ts`. Treated as informational for this frontend RED review, not as a gate.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Text dimension: case-insensitive substring match; empty string passes all | Assertions at `filterTasks_1248.test.ts:45`, `:50`, `:55`, `:61`, `:68` require exact retained/excluded task arrays | Text block | PASS |
| Priority dimension: exact match on `task.priority`; empty string passes all | Assertions at `filterTasks_1248.test.ts:80`, `:86`, `:95` prove match / pass-all / obvious mismatch, but do **not** prove exactness against a case-folding or normalization bug | Priority block | FAIL |
| Tags dimension: AND semantics; empty array passes all | Assertions at `filterTasks_1248.test.ts:106`, `:112`, `:119`, `:128` prove all-tags-required and empty-filter passthrough | Tags block | PASS |
| Blocked dimension: true => only blocked pass; false => all pass | Assertions at `filterTasks_1248.test.ts:139`, `:146` prove both branches | Blocked block | PASS |
| AND combination: multiple active dimensions all apply simultaneously | Assertions at `filterTasks_1248.test.ts:157`, `:181` prove combined filtering and all-pass default | AND block | PASS |
| Edge cases: empty tags array vs non-empty filter; missing fields treated as non-matching | Assertions at `filterTasks_1248.test.ts:128`, `:191` prove both refined edge cases | Edge block | PASS |
| Tests compile/execute, import resolves, assertions fail | Import resolves at `filterTasks_1248.test.ts:19`; stub export exists at `filterTasks.ts:3-11`; quality-runner observed 18 assertion failures and no collection error | Import + stub | PASS |
| FilterState exported with required shape | `filterTasks.ts:3-7` exports `{ text, priority, tags, blocked }` | FilterState export | PASS |

#### Security Review
- No issues in `serve/cockpit/web/src/utils/filterTasks.ts`: local type export + constant stub return only.

#### Test Integrity
- No builder weakening/removal detected in the current `TestFromAC_FilterTasks` snapshot.
- Builder scope is consistent with the task note and current file state: the meaningful implementation change is the new stub source file `serve/cockpit/web/src/utils/filterTasks.ts`.

#### Test Quality
- FAIL: manual-mutation resistance is weak for the priority AC. A buggy implementation that lowercases or otherwise normalizes both sides before comparing would still satisfy all current priority tests, despite violating the AC’s explicit `exact match` wording.
- Other dimensions are strong or adequate.

#### Data Safety
- No issues. Changed code is a pure synchronous stub with no IO, shared state, or multi-step mutation.

#### Implementation-Aware Gap Analysis
- No additional gap in the changed source file. The only reachable path is `return []` at `filterTasks.ts:11`, and the RED suite exercises that path.

#### Necessity Check
- N/A. No new dependency, integration, or speculative capability added.

#### Builder Process Quality
- CLEAN. One builder pass; no loop evidence; builder correctly shifted the task from collection-error RED to assertion-failure RED.

### Deductions
-0.12: Priority-dimension proof gap. Existing tests do not distinguish exact equality from case-insensitive / normalized equality.

### Verdict
FAIL -> todo | confidence 0.88

### Required Follow-up
- Test-writer: add a focused priority test that proves `exact match` literally. Example proof shape: task priority `critical` with filter `CRITICAL` should **not** match if the AC truly requires exact string equality.
- Builder code in `serve/cockpit/web/src/utils/filterTasks.ts` does not need to change for this retry unless the strengthened test exposes a scaffolding defect.

### Reflection
- Problem: RED scaffolding is correct, but one AC word (`exact`) is not fully defended by the current TestFromAC suite.
- Workaround: used code-reader plus direct file inspection to separate a proof gap from an implementation defect.
- Pattern: for equality ACs, include at least one near-miss counterexample so normalized/case-folded comparisons cannot false-pass.
- Quality gap: frontend coverage remains unavailable in scoped review until Vitest coverage provider is configured.
[[2026-05-01]]
## Test-Writer Notes (retry)

**Test file:** `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts`
**Class:** `TestFromAC_FilterTasks`

### Change from review retry

Added one test to `priority dimension` block to close the reviewer's proof gap:

```
it('priority match is case-sensitive — uppercase variant does not match lowercase filter', ...)
```

- Two tasks: `priority: 'critical'` and `priority: 'CRITICAL'`
- Filter: `priority: 'critical'`
- Expected: only the lowercase task included → `[lower]`
- Proves: exact string equality; a case-insensitive impl would return both tasks (discriminating in GREEN)
- Against stub (`return []`): fails on `expect([]).toEqual([lower])` → RED ✓

### Test totals

| Category | Count |
|----------|-------|
| Happy (text, priority, tags match) | 5 |
| Boundary (empty filter pass-all) | 3 |
| Exclusion (non-matching excludes) | 4 |
| Blocked (boolean gate) | 2 |
| AND combination | 2 |
| Edge cases | 2 |
| Priority exact-match proof (new) | 1 |
| **Total** | **19** |

**19 tests, all FAIL (assertion failures, no collection errors)**

### AC Coverage

| AC line | Status |
|---------|--------|
| Text: case-insensitive substring; '' passes all | PASS |
| Priority: exact match (case-sensitive proven); '' passes all | PASS (new test closes gap) |
| Tags: AND semantics; [] passes all | PASS |
| Blocked: true=only blocked, false=all pass | PASS |
| AND combination | PASS |
| Edge cases: empty tags, undefined tags | PASS |
| FilterState exported | PASS |

Lint: ESLint clean (0 violations).
[[2026-05-01]]
## Builder Notes
- Implementation: no source changes required in this retry; existing RED scaffold in serve/cockpit/web/src/utils/filterTasks.ts remains valid for task scope.
- Verification (quality-runner, scoped): Vitest on serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts reports 19/19 assertion failures, 0 collection/import failures.
- Lint (quality-runner, scoped): ESLint clean for serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts and serve/cockpit/web/src/utils/filterTasks.ts.
- Coverage: not a gate for this RED-phase frontend task; verification focused on executable RED state and lint cleanliness.
- Git state: clean working tree; no builder file deliverables created in this retry, so no commit required.
- Evidence summary: reviewer-requested priority exact-match proof is now present in test-writer retry, and suite remains correctly RED (assertion-failure mode), ready for review.

### Reflection
- Problem: task re-entered builder after test-only retry despite no implementation action needed.
- Workaround: enforced scoped quality-runner verification and advanced with explicit no-change builder evidence.
- Pattern: for RED test-only retries, builder can be no-op when failure mode and lint are both correct.
- Quality gap: none observed in current task scope.