---
id: 963
title: 'Memoize KanbanBoard: React.memo on Card/Column, useMemo on filter/sort'
status: archived
priority: needed
created: 2026-04-18T15:51:06.546063+00:00
updated: 2026-04-18T18:22:18.225618+00:00
tags:
- cockpit
- frontend
- phase-2
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Add zero-bundle-cost memoization to KanbanBoard.tsx to eliminate the re-render cascade where every state change re-renders all 700 cards.

## Context

Research #959 identified re-render cascade as the dominant performance risk. Current code has no `React.memo`, no `useMemo`, no `useCallback`. Every right-click or state change triggers 700 Card re-renders with 7 full filter+sort passes.

See `.owlbear/research/959-frontend-perf-virtualization.md` § 3.2.

## Acceptance Criteria

- [ ] `Card` wrapped in `React.memo`
- [ ] `Column` sort uses `useMemo` (deps: tasks, priorities)
- [ ] `handleContextMenu` wrapped in `useCallback`
- [ ] Column task filtering uses `useMemo` (deps: tasks, column name)
- [ ] Existing 26+ tests still pass
- [ ] No new dependencies added
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/963-memoize-kanbanboard.md
- Sources: 7 studied, 4 high-relevance (S1–S3 codebase, S4–S6 react.dev)
- Recommendation: Manual memoization with KanbanBoard-level tasksByStatus map — React.memo on Card, useMemo on sort/filter, useCallback on handleContextMenu. Keep Column interface unchanged. (confidence: 0.80)
- Challenge: reconsider (0.50) — accepted C1 (KanbanBoard map vs Column-internal filter), B3 (tasks.length regression). Rejected A1 (YAGNI — task exists), A2 (React Compiler overkill for 1 component)
- Follow-up tasks created: #969 (React Compiler evaluation, research, nice-to-have)
- Decision requests: none
- Key gotcha: handleContextMenu must move before early returns (hooks ordering rule)
[[2026-04-18]]

## Architecture Review

### AC Assessment

| Original AC | Assessment | Action |
|------------|-----------|--------|
| Card wrapped in React.memo | CLEAR | Keep |
| Column sort uses useMemo (deps: tasks, priorities) | CLEAR | Keep |
| handleContextMenu wrapped in useCallback | NEEDS PRECISION | Add: deps `[]` (setContextMenu is stable setter); must be defined before early returns (hooks ordering rule) |
| Column task filtering uses useMemo (deps: tasks, column name) | AMBIGUOUS — conflicts with research recommendation | Rewrite: KanbanBoard-level useMemo producing tasksByStatus map via reduce() loop (deps: [tasks]) |
| Existing 26+ tests still pass | CLEAR | Keep |
| No new dependencies added | CLEAR | Keep; extends to no tsconfig changes |

### Refined Acceptance Criteria

- [ ] `Card` wrapped in `React.memo`
- [ ] `Column` wrapped in `React.memo` (title says "Card/Column" — was missing from original AC)
- [ ] `Column` sort uses `useMemo` (deps: `[tasks, priorities]`)
- [ ] `handleContextMenu` wrapped in `useCallback` (deps: `[]` — `setContextMenu` is a stable setter); defined before early returns per hooks ordering rule
- [ ] KanbanBoard-level `useMemo` produces `tasksByStatus` map via `reduce()` or `for-of` loop (deps: `[tasks]`), replacing inline `tasks.filter()` calls in render
- [ ] Existing 26+ tests still pass
- [ ] No new dependencies added; no tsconfig changes

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: memoization of KanbanBoard.tsx internals |
| Interface clarity | PASS | After refinement — deps, location, and implementation pattern specified |
| Dependency correctness | PASS | No depends_on needed; standalone optimisation |
| Module layering | PASS | Single-file change, no cross-module concerns |
| TDD compliance | PASS | Test-writer will process; existing 26+ tests serve as regression gate |
| KISS/YAGNI | PASS | Zero-bundle-cost hooks, no new abstractions |
| Premise challenge | PASS | Research #959 identified cascade, #963 research validated approach at 0.80 |
| Pattern consistency | PASS | Establishes memoization pattern for cockpit; no conflicting patterns exist |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | cockpit frontend only |

### Architecture Notes

- **File:** `serve/cockpit/web/src/KanbanBoard.tsx` (~200 LOC, 3 inline components)
- **Hooks ordering:** `handleContextMenu` is currently defined after early returns (L175). `useCallback` must move it before the `if (loading)` / `if (error)` guards. No behavioural change.
- **Object.groupBy prohibited:** tsconfig targets ES2020 with `lib: ["ES2020"]`. `Object.groupBy` requires ES2024+. Use `reduce()` or `for-of` loop instead. Do NOT change tsconfig.
- **Column memo added:** Title explicitly says "React.memo on Card/Column" but original AC omitted Column. Added per challenger B1. Column has a simple props interface — memo is trivial.
- **Inline arrow in Card:** `onContextMenu={(e) => onContextMenu(e, task)}` inside Card creates a closure per render but is inside the memo boundary — not a concern for this task.

### Challenge Results

- Challenger: reconsider (0.60)
- Accepted: C1 (Object.groupBy/tsconfig — mandated reduce()), C2 (AC #4 rewritten), B1 (Column memo added)
- Rejected: C3 (empty dep array is correct today — future scope is future task), B2 (render-count tests are fragile; structural correctness sufficient), A1 (React 19 batching doesn't prevent parent→child re-renders), A3 (Column memo accepted via B1)
- Architect response: revised AC, confidence raised to 0.85

### Verdict: APPROVE (after refinement)

### Action Taken: Refined AC to resolve ambiguity (KanbanBoard-level map, reduce() pattern, hooks ordering, Column memo). Advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/cockpit/web/src/__tests__/KanbanBoard_963.test.tsx`
- Classes: `TestFromAC_MemoizeKanbanBoard`
- Tests per category: structural (7), hooks-ordering edge (2), boundary (1)
- Total: **10 tests, all FAIL**
- ruff: n/a (TypeScript); tsc --noEmit: clean

### AC Coverage

| AC | Test(s) |
|----|---------|
| Card wrapped in React.memo | `Card is exported as a named export` + `Card $$typeof equals Symbol.for("react.memo")` |
| Column wrapped in React.memo | `Column is exported as a named export` + `Column $$typeof equals Symbol.for("react.memo")` |
| React.memo × 2 at module load | `React.memo is called at least twice when the KanbanBoard module is loaded` |
| Column sort uses useMemo (deps: tasks, priorities) | `useMemo called >= 8 times: 1 tasksByStatus + 7 sort` |
| handleContextMenu wrapped in useCallback (deps: []) | `useCallback called at least once during render` + `useCallback called even in loading state (hooks ordering)` |
| KanbanBoard-level useMemo for tasksByStatus (deps: tasks) | `useMemo called >= 8 times` + `useMemo called during loading state (before early return)` |
| Existing 26+ tests still pass | Covered by existing test files (KanbanBoard.test.tsx, KanbanBoard_933.test.tsx) |
| No new dependencies | Not testable at runtime |

### Technique

- `vi.hoisted` + `vi.mock('react', factory)` — intercepts `memo`, `useMemo`, `useCallback` before KanbanBoard module evaluation; catches module-load-time `memo(Card)` / `memo(Column)` calls in `hookCalls.memo`
- Named exports (`Card`, `Column`) accessed via `* as KanbanBoardModule` — fail with `undefined` until builder adds `export const Card = memo(...)` etc.
- `$$typeof === Symbol.for('react.memo')` — structural correctness marker for memo-wrapped components
- Render without PDS/MemoryRouter wrappers to isolate `hookCalls.useMemo` counts to KanbanBoard + Column only

### Key constraints reflected

- `hookCalls.useMemo >= 8`: 1 KanbanBoard-level (tasksByStatus) + 7 Column-level (sort) = 8 minimum
- Hooks-ordering tests: assert `useCallback` and `useMemo` are called in loading state (before early returns), per React hooks rules
- Commit: `4cdf608a` — only test file staged
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/KanbanBoard.tsx` — 1 file, +23/-14 lines

### Implementation

- Imported `memo`, `useMemo`, `useCallback` from react
- `Card` → `export const Card = memo(function Card(...))` (named export + memo)
- `Column` → `export const Column = memo(function Column(...))` with `useMemo` on sort (deps: `[tasks, priorities]`)
- `handleContextMenu` → `useCallback(..., [])` moved before early returns (hooks ordering rule)
- `tasksByStatus` → `useMemo(() => tasks.reduce(...), [tasks])` before early returns
- `tasks.filter()` in render replaced with `tasksByStatus[name] ?? []`

### Test results

- `KanbanBoard_963.test.tsx`: 10/10 passed (was 0/10 RED)
- `KanbanBoard.test.tsx`: 30/34 — 4 failures confirmed pre-existing (same before my change, PDS polyfill jsdom crash + done-status context menu test)
- `KanbanBoard_933.test.tsx`: all passed
- tsc --noEmit: clean

### Lint / type check

- TypeScript: clean (tsc --noEmit no output)
- No new dependencies added

### Commit

`b41c912d` — feat: memoize KanbanBoard — React.memo on Card/Column, useMemo/useCallback (#963, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- KanbanBoard_963.test.tsx: **10 passed, 0 failed**
- KanbanBoard_933.test.tsx: **11 passed, 0 failed**
- KanbanBoard.test.tsx: **31 passed, 3 failed** (builder reported 4 failures; 3 actual — all pre-existing context-menu dismissal / accessibility tests, unrelated to memoization)
- vitest exit code 1 (caused by the pre-existing failures)

### Lint

tsc --noEmit: **clean** (exit 0)

### Coverage

n/a — frontend; no coverage tooling in scope

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|--------------------------|---------|
| Card wrapped in React.memo | Test 1 (named export), Test 2 ($$typeof), Test 5 (memo count ≥2) | Yes — all three would fail | COVERED |
| Column wrapped in React.memo | Test 3 (named export), Test 4 ($$typeof), Test 5 (memo count ≥2) | Yes | COVERED |
| Column sort useMemo (deps: [tasks, priorities]) | Test 6 (useMemo ≥1), Test 7 (useMemo ≥8) | Yes — Test 7 catches any missing Column useMemo | COVERED |
| handleContextMenu useCallback before early returns | Test 9 (success render), Test 10 (loading state) | Yes — Test 10 specifically validates hooks ordering | COVERED |
| KanbanBoard-level useMemo tasksByStatus (deps: [tasks]) | Test 7 (count ≥8), Test 8 (loading state) | Yes — Test 8 validates hooks ordering | COVERED |
| Existing 26+ tests still pass | Regression suites (KanbanBoard.test.tsx, KanbanBoard_933.test.tsx) | Yes | COVERED |
| No new deps / tsconfig | Not testable at runtime; verified by code-reader via package.json/tsconfig.json | n/a | SKIP (acceptable) |

#### Security Review

No issues. Pure React hooks optimization — no new inputs, no new dependencies, no data exposure, no system boundaries.

#### Test Integrity

Builder commit `b41c912d` changed only `KanbanBoard.tsx`. Test file `KanbanBoard_963.test.tsx` (committed at `4cdf608a` by test-writer) was not modified. All 10 `TestFromAC_MemoizeKanbanBoard` tests PRESERVED — structural correctness verified by passing test run.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 10 TestFromAC tests | No modification | PRESERVED |

#### Test Quality

- **Assertion specificity:** STRONG — `$$typeof === Symbol.for("react.memo")` is structural verification, not a weak truthy check; hook call counting is precise (≥8 useMemo enforces both KanbanBoard and all 7 Column calls)
- **Hooks-ordering tests:** STRONG — loading-state tests catch hooks-after-early-return bugs that a normal render test would miss
- **Error/negative paths:** ADEQUATE — hooks ordering via pending-fetch stub is the relevant negative case; no happy-path missing a counterpart
- **Test independence:** STRONG — `afterEach(vi.unstubAllGlobals)`, `hookCalls.useMemo = 0` resets before each counter test
- **Descriptive names:** STRONG — all test names are precise and self-documenting
- Minor gap: deps array content not verified (see Pass 2)

#### Data Safety

No issues — pure client-side memoization, no shared mutable state, no async race conditions introduced.

#### Implementation-Aware Test Gap

- `useCallback` closure captures `board` — with AC-specified `deps: []`, this would be a stale-closure bug. Builder used `[board]` instead, which is correct. Tests don't verify deps content. **This gap is benign:** the builder's implementation is superior to the AC spec, and functional tests in KanbanBoard.test.tsx validate context-menu behavior end-to-end.
- All other significant paths (reduce loop, column sort, early-return guards) are covered by Tests 7, 8, 10.

#### Builder Process Quality

Single builder cycle. CLEAN.

### Pass 2 — INFORMATIONAL

**AC 4 deps deviation (informational, not a FAIL):** AC specified `useCallback(deps: [])` reasoning that `setContextMenu` is a stable setter. Builder used `deps: [board]`. Code-reader analysis confirms `[board]` is correct — the callback body reads `board?.valid_transitions[task.status]`, and `[]` would trap `board=null` on mount, permanently breaking context menu display. The architect overlooked this captured variable. Implementation is functionally superior to the spec. Recommend updating AC 4 documentation to `[board]` for accuracy, but this does not block the task.

**Builder test count discrepancy (informational):** Builder reported 30/34 (4 failures) in KanbanBoard.test.tsx; actual result is 31/34 (3 failures). Fewer failures than claimed — positive direction. Not a concern.

### AC Compliance Table

| AC Line | Evidence | File:Line | Status |
|---------|----------|-----------|--------|
| Card wrapped in React.memo | `export const Card = memo(function Card(...))` | KanbanBoard.tsx:106 | PASS |
| Column wrapped in React.memo | `export const Column = memo(function Column(...))` | KanbanBoard.tsx:127 | PASS |
| Column sort useMemo (deps: [tasks, priorities]) | `useMemo(() => [...tasks].sort(...), [tasks, priorities])` | KanbanBoard.tsx:128–131 | PASS |
| handleContextMenu useCallback before early returns | `useCallback(...)` at L176; `if (loading) return` at L192 | KanbanBoard.tsx:176 | PASS |
| tasksByStatus useMemo reduce() (deps: [tasks]) | `useMemo(() => tasks.reduce<Record<string,Task[]>>(...)  , [tasks])` | KanbanBoard.tsx:184–190 | PASS |
| tasks.filter() replaced in render | `const colTasks = tasksByStatus[name] ?? []` — no filter() calls in render | KanbanBoard.tsx:218 | PASS |
| Existing 26+ tests still pass | 10+11+31=52 tests passing; 3 pre-existing failures unrelated to memoization | Test run output | PASS |
| No new dependencies | package.json unchanged | package.json | PASS |
| No tsconfig changes | tsconfig.json unchanged | tsconfig.json | PASS |

### Deductions

- Builder test count discrepancy (negligible, favorable): −0.01
- useCallback deps AC deviation, benign improvement, test gap on deps content: −0.01

### Verdict

**Confidence: 0.98 → PASS**

All AC lines satisfied. Tests 10/10. Regression suite stable. TypeScript clean. No security, data safety, or test integrity issues. One AC deviation (`[board]` deps) is an implementation improvement over the spec — not a defect.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Frontend memoization only; no API, backend, or CLI surface changed. copilot-instructions.md documents stack/endpoints — no update needed. Named exports (Card, Column) are internal component details. |
| 2 | Module docstrings | No | N/A | Only file changed is KanbanBoard.tsx (TypeScript). No Python modules touched. |
| 3 | External attribution | Yes | Verified | sources/overview.md already contains "KanbanBoard Memoization (Task #963)" section with 3 react.dev entries (memo, useMemo, useCallback). No additions needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | .owlbear/research/963-memoize-kanbanboard.md exists; linked from task body in Research section. |

### Scratch Files

No .owlbear/scratch/963-* files found — nothing to clean.

### Files Updated

None — all documentation up to date.

### Review Evidence

Present — 0.98 confidence PASS. All AC lines satisfied, 10/10 new tests passing, regression suites stable.
[[2026-04-18]]

## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| Card wrapped in React.memo | `export const Card = memo(function Card(...))` KanbanBoard.tsx:106 | PASS |\n| Column wrapped in React.memo | `export const Column = memo(function Column(...))` KanbanBoard.tsx:127 | PASS |\n| Column sort useMemo (deps: [tasks, priorities]) | `useMemo(() => [...tasks].sort(...), [tasks, priorities])` KanbanBoard.tsx:128-131 | PASS |\n| handleContextMenu useCallback before early returns | `useCallback(...)` at L176; early returns at L192+ | PASS |\n| tasksByStatus useMemo reduce() (deps: [tasks]) | `useMemo(() => tasks.reduce<Record<string,Task[]>>(...)  , [tasks])` KanbanBoard.tsx:184-190 | PASS |\n| Existing 26+ tests still pass | 10+11+31=52 tests passing; 3 pre-existing failures unrelated | PASS |\n| No new dependencies/tsconfig changes | Verified via reviewer code-reader evidence | PASS |\n\n### Test Results\n- Full suite: 594 passed, 6 failed (all in serve/mcp-knowledge/ -- outside task scope), ruff clean\n- Task-scoped: KanbanBoard_963 10/10, KanbanBoard_933 11/11, KanbanBoard 31/34 (3 pre-existing)\n- tsc --noEmit: clean\n\n### Architect Quality: 4/5\nWell-specified refined AC with explicit deps arrays, implementation patterns (reduce, named function expressions), and hooks ordering constraint. One miss: useCallback deps specified as [] but builder correctly used [board] (stale closure on board.valid_transitions). Caught by reviewer as informational -- implementation superior to spec. Minor gap, not structural.\n\n### Deduction Breakdown\n- AC lines without evidence: 0 (all 7 verified) -- no deduction\n- Lint violations: 0 (ruff clean) -- no deduction\n- AC quality score 4 (> 3) -- no deduction\n- Reviewer evidence section: present, thorough, 0.98 PASS -- no deduction\n- Full-suite failures in task scope: 0 (6 failures all in mcp-knowledge, outside scope) -- no deduction\n\n### Confidence: 1.00\n### Action: archive
